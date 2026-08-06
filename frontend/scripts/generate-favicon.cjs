/**
 * 生成 favicon.ico + 多种尺寸 PNG
 * 输入: 项目 src/assets/images/logo/rosetta-primary-icon.png (用户指定路径)
 * 输出:
 *   - public/favicon/favicon.ico
 *   - public/favicon.ico  (浏览器根路径默认查找, 防 /favicon.ico 404)
 *   - public/favicon/rosetta-32.png, rosetta-180.png, rosetta-192.png, rosetta-256.png
 *   - public/favicon/rosetta-icon.png (32px 别名，供 siteConfig 默认引用)
 *   - public/favicon/rosetta-primary-icon.png (拷贝源尺寸版本, 供 admin.astro / logo 引用)
 *
 * 工具链:
 *   - sharp (Node.js 图片处理库, 已在 package.json dependencies 中安装)
 *   - 原生 Buffer 手写 ICO 文件头 (Modern ICO = 内嵌 256x256 PNG; 所有主流浏览器支持)
 */

const sharp = require("sharp");
const fs = require("fs");
const path = require("path");

// 本脚本在 frontend/scripts/ 目录
const SCRIPT_DIR = __dirname;

// 用户指定的输入路径: frontend/src/assets/images/logo/rosetta-primary-icon.png
const inputPath = path.join(
	SCRIPT_DIR,
	"..",
	"src",
	"assets",
	"images",
	"logo",
	"rosetta-primary-icon.png",
);

// 目标输出目录
const publicFaviconDir = path.join(SCRIPT_DIR, "..", "public", "favicon");
const publicRootDir = path.join(SCRIPT_DIR, "..", "public");

console.log(`[favicon] Input logo : ${inputPath}`);
console.log(`[favicon] Output dir : ${publicFaviconDir}`);
console.log(`[favicon] Root dir   : ${publicRootDir}`);

if (!fs.existsSync(inputPath)) {
	console.error(`[favicon] ❌ Logo file not found: ${inputPath}`);
	process.exit(1);
}

fs.mkdirSync(publicFaviconDir, { recursive: true });

// ICO 文件常量（标准 Windows ICO 容器格式）
const ICONDIR_SIZE = 6; // 2B Reserved + 2B Type + 2B Count
const ICONDIRENTRY_SIZE = 16; // 16 bytes per entry

/**
 * 写入指定尺寸的 PNG
 * @param {number} size
 * @returns {Promise<string>} 生成的 png 路径
 */
async function writePng(size) {
	const out = path.join(publicFaviconDir, `rosetta-${size}.png`);
	await sharp(inputPath)
		.resize(size, size, {
			fit: "contain",
			background: { r: 0, g: 0, b: 0, alpha: 0 },
		})
		.png({ compressionLevel: 9, palette: false })
		.toFile(out);
	console.log(`[favicon] ✔ rosetta-${size}.png (${size}x${size})`);
	return out;
}

/**
 * 将单张 PNG Buffer 封装为 .ico 容器
 * 现代浏览器支持直接嵌入 PNG as-is，无需 BMP/DIB 转码
 * @param {Buffer} pngBuf 256x256 PNG Buffer
 */
function pngToIcoContainer(pngBuf) {
	const numImages = 1;

	const header = Buffer.alloc(ICONDIR_SIZE);
	header.writeUInt16LE(0, 0); // Reserved, 必须为 0
	header.writeUInt16LE(1, 2); // Type: 1 = ICO (2 = CUR)
	header.writeUInt16LE(numImages, 4); // Number of images

	const entry = Buffer.alloc(ICONDIRENTRY_SIZE);
	// Width/Height 取值 0 表示 256 像素 (8bit 字段)
	entry.writeUInt8(0, 0);
	entry.writeUInt8(0, 1);
	entry.writeUInt8(0, 2); // Color palette count (0 = no palette)
	entry.writeUInt8(0, 3); // Reserved, must be 0
	entry.writeUInt16LE(1, 4); // Color planes
	entry.writeUInt16LE(32, 6); // Bits per pixel (ARGB = 32)
	entry.writeUInt32LE(pngBuf.length, 8); // Size of image data (bytes)
	entry.writeUInt32LE(ICONDIR_SIZE + ICONDIRENTRY_SIZE * numImages, 12); // Offset from start of ICO to image data

	return Buffer.concat([header, entry, pngBuf]);
}

async function main() {
	// Step 1: 生成所有尺寸的 PNG
	const sizes = [32, 180, 192, 256];
	await Promise.all(sizes.map((s) => writePng(s)));

	// Step 2: 生成 rosetta-icon.png 别名 (32x32, siteConfig 默认引用)
	const icon32Path = path.join(publicFaviconDir, "rosetta-icon.png");
	await sharp(inputPath)
		.resize(32, 32, {
			fit: "contain",
			background: { r: 0, g: 0, b: 0, alpha: 0 },
		})
		.png({ compressionLevel: 9 })
		.toFile(icon32Path);
	console.log(`[favicon] ✔ rosetta-icon.png (32x32 alias)`);

	// Step 3: 同步拷贝 rosetta-primary-icon.png (原尺寸, 供 admin.astro 等引用)
	const primaryDest = path.join(publicFaviconDir, "rosetta-primary-icon.png");
	fs.copyFileSync(inputPath, primaryDest);
	console.log(`[favicon] ✔ rosetta-primary-icon.png (copied from src/assets)`);

	// Step 4: 构造 favicon.ico (内含 256x256 PNG → 现代浏览器原生识别)
	const png256 = fs.readFileSync(path.join(publicFaviconDir, "rosetta-256.png"));
	const icoBuf = pngToIcoContainer(png256);

	const icoSubdir = path.join(publicFaviconDir, "favicon.ico");
	fs.writeFileSync(icoSubdir, icoBuf);
	console.log(
		`[favicon] ✔ public/favicon/favicon.ico (${Math.round(icoBuf.length / 1024)} KB, PNG embedded, valid ICO container)`,
	);

	// Step 5: 同步到 public/ 根目录（避免某些服务器/浏览器直接请求 /favicon.ico 导致 404）
	const icoRoot = path.join(publicRootDir, "favicon.ico");
	fs.writeFileSync(icoRoot, icoBuf);
	console.log(`[favicon] ✔ public/favicon.ico (root fallback for /favicon.ico)`);

	console.log("\n[favicon] 🎉 All favicon assets generated successfully.");
	console.log(
		`           - siteConfig default 引用 /favicon/favicon.ico + /favicon/rosetta-icon.png ✅`,
	);
	console.log(`           - 根路径 /favicon.ico 也已同步，无 404 风险 ✅`);
}

main().catch((err) => {
	console.error("[favicon] ❌ Failed to generate favicons:", err);
	process.exit(1);
});
