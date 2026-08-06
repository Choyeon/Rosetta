/**
 * 扫描 src 目录所有 svelte/astro/ts/js，提取 material-symbols:xxx 图标名
 * 从 node_modules/@iconify-json/material-symbols/icons.json 中抽取对应 body
 * 生成符合 src/constants/icons-data.json 结构的文件
 * 保留 fa7-solid/mdi/svg-spinners 原封不动
 *
 * 运行: node scripts/sync-material-icons.cjs
 */
const fs = require("fs");
const path = require("path");

const FRONTEND_ROOT = path.resolve(__dirname, "..");
const SRC_DIR = path.join(FRONTEND_ROOT, "src");
const ICONS_DATA_PATH = path.join(FRONTEND_ROOT, "src", "constants", "icons-data.json");
const MATERIAL_SOURCE_PATH = path.join(
  FRONTEND_ROOT,
  "node_modules",
  "@iconify-json",
  "material-symbols",
  "icons.json"
);

// ------------------ Step 1: 扫描提取所有 icon ------------------
const EXTS = new Set([".svelte", ".astro", ".ts", ".js"]);
const found = new Set();

function walk(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full);
    } else if (entry.isFile() && EXTS.has(path.extname(entry.name))) {
      const content = fs.readFileSync(full, "utf8");
      const re = /material-symbols:([a-zA-Z0-9_-]+)/g;
      let m;
      while ((m = re.exec(content)) !== null) found.add(m[1]);
    }
  }
}

walk(SRC_DIR);

console.log(`[sync-material-icons] Found ${found.size} unique material-symbols icons in src/`);

// ------------------ Step 2: 读取源 material-symbols 图标库 ------------------
const materialSource = JSON.parse(fs.readFileSync(MATERIAL_SOURCE_PATH, "utf8"));

const missing = [];
const builtIcons = {};

function resolveBody(name, visited = new Set()) {
  if (visited.has(name)) return undefined; // 防止 parent 循环
  visited.add(name);
  const entry = materialSource.icons[name];
  if (!entry) return undefined;
  if (entry.body) return entry.body;
  if (entry.parent) return resolveBody(entry.parent, visited);
  return undefined;
}

for (const name of found) {
  const entry = materialSource.icons[name];
  if (!entry) {
    missing.push(name);
    continue;
  }
  const body = entry.body || resolveBody(name);
  if (body) {
    builtIcons[name] = { body };
  } else if (entry.parent) {
    // alias-only 条目（保留 parent 引用给 iconify 解析）
    builtIcons[name] = { parent: entry.parent };
  } else {
    missing.push(name);
  }
}

if (missing.length > 0) {
  console.warn(
    `[sync-material-icons] WARNING: ${missing.length} icons not found in @iconify-json/material-symbols:\n  - ${missing.join("\n  - ")}`
  );
}

// ------------------ Step 3: 合并入 icons-data.json（保留其他集合） ------------------
const iconsData = JSON.parse(fs.readFileSync(ICONS_DATA_PATH, "utf8"));

// 保留原有的 material-symbols 里可能手动维护的 其他 icon（如果不在扫描里 不删除 只是 补充）
// 但 user 需求 是 我们 实际 扫到 的 才 要，并且 原有 已经 有 2 个 icon 我们 肯定 还在 用，所以 直接 用 builtIcons 覆盖
iconsData["material-symbols"] = {
  prefix: "material-symbols",
  icons: {
    // 保留原有的 （万一 某些 icon 是 运行时 动态拼名字 没扫到）
    ...((iconsData["material-symbols"] && iconsData["material-symbols"].icons) || {}),
    // 扫到的 覆盖/补充 进去
    ...builtIcons,
  },
  width: 24,
  height: 24,
};

// 保存
fs.writeFileSync(ICONS_DATA_PATH, JSON.stringify(iconsData, null, "\t") + "\n", "utf8");
console.log(
  `[sync-material-icons] OK! Written ${Object.keys(iconsData["material-symbols"].icons).length} material-symbols icons to src/constants/icons-data.json`
);
if (missing.length > 0) process.exit(1);
