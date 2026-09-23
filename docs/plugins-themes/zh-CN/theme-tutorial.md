# Rosetta 主题开发教程

> 版本：2.0.0 · 最后更新：2026-09-22 · 语言：zh-CN

Rosetta 的主题系统遵循 WordPress 风格：**一个主题 = 一个文件夹 + 一份 `rosetta-theme.json` 清单 + `style.css` + 截图**。
后端核心负责「清单扫描 → DB 同步 → 互斥激活 → mods 键值存储 → 僵尸清理」；视觉呈现由前端
`useFrontendTheme` 注入 `<html>` 属性与 `<link>`，主题 CSS 靠**作用域守卫选择器**生效——
不引入任何构建链路，也不允许主题之间存在或越界影响到 Admin 的样式耦合。

本文以 **`astro-paper-inspired`（极简主题）** 为例，展示一个符合规范的主题从零到激活的全部细节。

---

## 1. 目录规范

所有主题位于 `frontend/themes/<slug>/`：

```
frontend/themes/
  astro-paper-inspired/
    rosetta-theme.json   ← 必填：主题清单（唯一元数据来源）
    style.css            ← 必填：入口 CSS（每条规则必须带作用域守卫，见 §3）
    screenshot.svg       ← 推荐：封面截图（.png / .svg）
    README.md            ← 可选：作者说明
```

> **slug 命名约束**（由 `RosettaThemeManifest` 校验）：正则 `^[a-z0-9-]{3,64}$`，且须与目录名一致。
> **version 约束**：语义化版本 `^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?$`，例：`0.1.0`。

激活主题后，前端会给 **`<html>`**（不是 `<body>`）写入：

| 属性 / class | 值 | 用途 |
| --- | --- | --- |
| `data-rosetta-theme` | `<slug>` | Rosetta 专用主题属性（不与明暗模式的 `data-theme="light|dark"` 冲突） |
| `data-theme` | `<slug>` | 旧约定兼容，两套属性同时写入 |
| `class` | `theme-<slug>` | 需要 class 钩子时使用 |
| `data-layout-scope` | `frontend` / `admin` / `public-auth` | 页面上下文，由全局中间件写入（见 §3） |

---

## 2. rosetta-theme.json 字段详解

清单由 Pydantic 模型 `RosettaThemeManifest` 校验（`backend/schemas/manifest.py`），
**未知字段静默忽略**（`extra="ignore"`）——历史清单里的 `id` / `type` / `entry_css` / `screenshot`
等字段属于这类，不会被消费。真实生效的字段：

| 字段 | 类型 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | string | ✅ | — | 主题显示名（后台卡片、前台展示） |
| `slug` | string | ✅ | — | `^[a-z0-9-]{3,64}$`，与目录名一致 |
| `version` | string | ✅ | — | 语义化版本；同时用于资源 URL 的 `?v=` 缓存 bust（§3.3） |
| `manifest_version` | string | — | `"1.0"` | 清单结构版本 |
| `requires_rosetta` | string | — | `">=1.0.0"` | 兼容性声明 |
| `description` / `description_i18n` | string / object | — | — | 一句话描述；i18n dict 优先 |
| `author` / `author_name` | object / string | — | — | `author` 为 `{name, uri}` 结构 |
| `theme_uri` / `author_uri` | string | — | — | 主题主页 / 作者主页 |
| `textdomain` | string | — | 取 slug | 预留的 i18n 域 |
| `tags` | string[] | — | `[]` | 关键词，WordPress 风格命名（`color:mono`、`layout:single-column`…） |
| `parent_theme` | string | — | null | 子主题继承声明（占位，UI 暂未展开继承逻辑） |
| `mods_schema` | object | — | `{}` | JSON Schema Draft-07，驱动 Customizer 动态表单 + 服务端校验（§2.1） |
| `screenshot_urls` | string[] | — | `[]` | 相对文件名（`screenshot.svg`）或绝对 URL；相对路径按 `/themes/<slug>/<file>` 解析 |
| `stylesheet` | string | — | `"style.css"` | 入口 CSS 文件名 |
| `template` | string | — | null | 预留 |
| `features` | string[] | — | `[]` | 能力标签（`customizer`、`custom-header`…），仅展示用 |
| `color_palette` | object[] | — | null | 主题推荐色板（`{name, slug, color}`），展示 / 取色用 |

### 2.1 mods_schema

`mods_schema` 声明「主题自定义项」，一个作用两份职责：

1. **后台 Customizer 动态表单**：`string` → 文本框、`string+enum` → 下拉、`boolean` → 开关、
   `integer/number` → 数字框（支持 `minimum/maximum`）、`format:"color"` → 颜色选择器、
   `format:"textarea"` → 多行文本。
2. **服务端写入校验与清洗**（`ThemeManager.set_mods`）：
   - 类型 / 范围 / enum 违例 → 整次拒绝，返回 `400 MODS_SCHEMA_VIOLATION`；
   - **schema 未声明的键 → 静默丢弃**（WordPress `sanitize_theme_mods` 语义），不会落库。

mods 值以 JSON 存在 SiteConfig KV `theme_mods:<slug>` 下；读取时永远做
「schema 默认值 ⊕ 已存值」合并，因此升级新增字段无需数据迁移。

`PUT /mods` = 全量替换（先重置为默认再写入，未提交的键回默认）；
`PATCH /mods` = 增量合并。两者共用同一套校验清洗。

推荐显式书写 `"additionalProperties": false`，让 schema 自文档化清洗行为。

---

## 3. CSS 作用域守卫（硬性红线）

Rosetta 全站（含 Admin）共用一套 Tailwind + shadcn 组件。主题 CSS 与后台**零耦合**是
不可协商的约束，实现手段是每条选择器都带完整作用域守卫。

### 3.1 标准守卫前缀

```
$P ≡ :is([data-theme="<slug>"],[data-rosetta-theme="<slug>"])[data-layout-scope="frontend"]
```

**逗号分隔的选择器列表里，每一项都必须携带完整前缀**（`:is()` 只在复合选择器内部起作用，
不能替你守卫逗号后的其它顶层选择器）：

```css
/* ✅ 正确 */
:is([data-theme="astro-paper-inspired"],[data-rosetta-theme="astro-paper-inspired"])[data-layout-scope="frontend"] .post-card {
  border-bottom: 1px solid hsl(var(--border) / 0.55);
  border-radius: 0;
  box-shadow: none;
}
:is([data-theme="astro-paper-inspired"],[data-rosetta-theme="astro-paper-inspired"])[data-layout-scope="frontend"] .post-list {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* ❌ 错误：逗号第二项没有守卫，会泄漏到 Admin */
:is(...)[data-layout-scope="frontend"] .post-card,
.post-card--legacy { ... }
```

### 3.2 三个 layout scope

| scope | 路径 | 主题 CSS 行为 |
| --- | --- | --- |
| `frontend` | 其余全部前台页 | 正常生效（上文 `$P`） |
| `public-auth` | `/login` `/register` | 主题属性与 `<link>` 会注入，但 `$P` 不命中；想定制认证页必须**显式**写 `[data-layout-scope="public-auth"]` 段落（仍需带主题 slug 前缀） |
| `admin` | `/admin/**` `/oobe` | 运行时层保证不注入主题属性 / `<link>`，主题文件根本不出现在后台 DOM |

禁止的写法：blanket 通用选择器（`body` / `a` / `h1` / `.btn` 裸写，不带 `$P`）、
重写 `.card-surface`（`main.css` 的全站共享类，Admin 同用）、给 Admin 卡片加任何主题样式。

### 3.3 资源 URL 与缓存

`/themes/**` 在 nuxt.config routeRules 中是 `max-age=31536000, immutable` 强缓存。
前端统一通过 `lib/rosetta-themes.ts` 的 `resolveThemeAssetPath` + `bustThemeAssetCache`
给 `style.css` 与截图追加 `?v=<version>`——**主题发布新版本时必须 bump 清单 `version`**，
否则访客与后台永远命中旧缓存。

### 3.4 mods ↔ CSS 联动

核心自动写入的颜色变量（`applyThemeColorTokens`，仅当前台非排除路径）：

| mod 键 | 写入的 CSS 变量（`<html style>`） |
| --- | --- |
| `accent_color` | `--theme-accent-hue` / `--theme-accent-sat` / `--theme-accent-light` |
| `primary_color` | `--primary`、`--ring`（并打 `data-rosetta-color-tokens` 标记供回收） |

其余 mods（如 `posts_per_row`、`layout_width`、`show_sidebar`）由前台组件通过
`useFrontendTheme().mods` 在 JS/模板层消费（如首页网格列数 class）。**新增 mod 若希望前台
生效，需要在前端补对应消费逻辑**（`ThemeModsRuntime` + `MODS_DEFAULTS` + 组件读取），
后端不会替你把它变成 CSS 变量。

---

## 4. 安装与切换

### 4.1 通过后台（推荐）

1. 将主题目录放到 `frontend/themes/<slug>/`；
2. 登录后台 → 主题管理 → 「扫描本地」：新增 / 刷新磁盘主题，并清理"磁盘已不存在
   的非激活主题"的僵尸 DB 记录（含其 mods）；
3. 目标主题卡片 → 「启用」（互斥切换，同时立即刷新前台主题状态）；
   可先点「预览」在新标签页以 `/?rosetta_theme_preview=<slug>` 试看，不影响真实激活；
4. 「自定义」打开 Customizer 表单，保存即 PATCH mods；若主题处于激活状态，前台立刻重取。

内建主题（`lib/rosetta-themes.ts` 的 `KNOWN_ROSETTA_THEMES`）随代码仓库分发，
后台禁止删除；激活中的主题删除返回 409。删除仅移除 DB 记录与 mods，磁盘文件保留，
下次扫描会重新登记（mods 回到 schema 默认值）。

### 4.2 通过 REST API

```bash
# 1) 扫描同步磁盘 ↔ DB（返回 added / refreshed / removed）
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  "https://example.com/api/admin/themes/scan"

# 2) 激活
curl -X PUT -H "Authorization: Bearer <TOKEN>" \
  "https://example.com/api/admin/themes/astro-paper-inspired/activate"

# 3) 增量修改 mods（未声明键会被丢弃）
curl -X PATCH -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  "https://example.com/api/admin/themes/astro-paper-inspired/mods" \
  -d '{ "accent_color": "#6d28d9", "posts_per_row": 2 }'
```

前台读取当前激活主题走公开接口 `GET /api/themes/active`。
ZIP 上传 / 远程安装 / 市场安装参见《REST API 参考》第 3 节。

---

## 5. 完整示例（astro-paper-inspired 清单）

`frontend/themes/astro-paper-inspired/rosetta-theme.json`（节选自实际内建主题）：

```json
{
  "manifest_version": "1.0",
  "name": "极简主题",
  "slug": "astro-paper-inspired",
  "version": "0.1.0",
  "requires_rosetta": ">=1.0.0",
  "description": "极简印刷风格：760px 窄栏居中、无大图 Hero、竖排列表、极细分割线。",
  "author_name": "Rosetta Themes",
  "author": { "name": "Rosetta Themes", "uri": "https://rosetta.dev/themes" },
  "theme_uri": "https://rosetta.dev/themes/astro-paper-inspired",
  "textdomain": "astro-paper-inspired",
  "tags": ["color:mono", "layout:single-column", "subject:blog", "feature:customizer"],
  "parent_theme": null,
  "screenshot_urls": ["screenshot.svg"],
  "features": ["single-column", "customizer"],
  "mods_schema": {
    "$schema": "https://json-schema.org/draft-07/schema",
    "type": "object",
    "additionalProperties": false,
    "properties": {
      "posts_per_row": { "type": "integer", "default": 1, "enum": [1, 2], "title": "首页每行文章数" },
      "show_avatar":   { "type": "boolean", "default": true, "title": "显示作者头像" },
      "accent_color":  { "type": "string",  "default": "#4f46e5", "format": "color", "title": "强调色" },
      "layout_width":  { "type": "integer", "default": 760, "minimum": 640, "maximum": 960, "title": "内容区域宽度 (px)" },
      "footer_text":   { "type": "string",  "default": "© 2026 Rosetta · Built with the Minimal Paper theme.", "title": "页脚版权文字" }
    }
  },
  "color_palette": [
    { "name": "Ink", "slug": "fg", "color": "#111827" },
    { "name": "Accent", "slug": "accent", "color": "#4f46e5" }
  ]
}
```

---

## 6. 交付前自检清单

- [ ] 目录名 = `slug`，匹配 `^[a-z0-9-]{3,64}$`；`version` 为合法 semver
- [ ] `style.css` 每条规则（含逗号每一项）带完整 `$P` 守卫；定制登录/注册页另写 public-auth 段落
- [ ] 未触碰 `.card-surface`、未裸写 `body/a/h1/.btn` 等 blanket 选择器
- [ ] 修改过样式则已 bump `version`（否则 immutable 缓存不生效）
- [ ] `mods_schema` 声明了全部自定义项并给出合理 `default`（升级零迁移依赖它）
- [ ] 后台「扫描 → 预览 → 激活 → 自定义」全流程走通，Admin 视觉无任何变化
