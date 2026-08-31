# Rosetta 主题开发教程

> 版本：1.0.0 · 最后更新：2026-08-28 · 语言：zh-CN

Rosetta 的主题系统遵循 WordPress / Ghost 风格：**一个主题 = 一个文件夹 + 一份 `rosetta-theme.json` 清单 + 若干 CSS / 截图资源**。
Rosetta 核心负责「主题扫描 → DB 同步 → 互斥激活 → mods 键值存储」；而视觉呈现完全交给前端 `<body data-theme="<slug>">` 下的 CSS 作用域覆盖，即「CSS 变量 + 前缀选择器」模式，避免引入新的构建链路。

本文以 **`astro-paper-inspired`** 主题为例，完整展示从零构建一个主题的全部细节。

---

## 1. 目录规范

所有主题位于 `frontend/themes/<slug>/`，目录结构如下：

```
frontend/themes/
  astro-paper-inspired/
    rosetta-theme.json   ← 必填：主题清单
    style.css            ← 必填：入口 CSS（与 entry_css 对应）
    screenshot.svg       ← 推荐：封面截图（也可以是 .png）
    README.md            ← 可选：作者说明
```

> **slug 命名约束**：小写字母开头，仅允许 `a-z / 0-9 / -`，长度 2~50，正则 `^[a-z][a-z0-9\-]{1,48}$`。

激活主题后，Rosetta 前端会给 `<html>` 或 `<body>` 写入 `data-theme="<slug>"` 属性；因此所有自定义 CSS 都必须加此前缀，避免破坏 Rosetta 默认的 shadcn 主题体系。

---

## 2. rosetta-theme.json 字段详解

`rosetta-theme.json` 是主题的唯一入口清单，由 Pydantic 模型 `RosettaThemeManifest` 严格校验（见 `backend/schemas/manifest.py`）。完整字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | string | ✅ | 反向域名式唯一 ID，例：`io.github.rosetta.astro-paper-inspired` |
| `slug` | string | ✅ | 与目录名一致；必须匹配 `^[a-z][a-z0-9\-]{1,48}$` |
| `name` | string | ✅ | 主题显示名，例：`Astro Paper Inspired` |
| `version` | string | ✅ | 语义化版本，例：`0.1.0` |
| `type` | string | ✅ | 主题类型，目前允许：`blog / portfolio / docs / magazine / other` |
| `description` | string | ✅ | 一句话描述（显示在市场和后台列表） |
| `author` | string | ✅ | 作者名或组织 |
| `license` | string | ✅ | SPDX 协议名，例：`MIT` |
| `entry_css` | string | ✅ | 入口 CSS 文件名，相对于主题目录，例：`style.css` |
| `screenshot` | string | 可选 | 截图文件名；SVG / PNG 均可，例：`screenshot.svg` |
| `homepage` | string | 可选 | 主题官网 URL |
| `repository` | string | 可选 | Git 仓库 URL |
| `tags` | string[] | 可选 | 关键词数组，例：`["minimal","paper","narrow"]` |
| `compatibility` | object | 可选 | `{ min_rosetta: "1.0.0", max_rosetta: "2.0.0" }` |
| `mods_schema` | object | ✅ | JSON Schema Draft-07 对象，描述「主题自定义项（Mods）」的结构，详见下文 |
| `mods_default` | object | 可选 | 默认 mods 值；为空时使用 schema 里的 `default` 聚合 |

### 2.1 mods_schema 字段

`mods_schema` 用于驱动后台 **Customizer 动态表单** 和 **服务端写入校验**。
Mods 只支持 JSON 值类型：`string / number / integer / boolean / array / object`。推荐用 4 类最常用属性：

| JSON Schema type | 前端 Customizer 控件 | 典型字段 |
| --- | --- | --- |
| `type: "string"` + 无 `enum` | `<Input>` 文本框 | `accent_color`、`site_subtitle` |
| `type: "string"` + `enum: [...]` | `<Select>` 选择器 | `header_style`、`font_family` |
| `type: "boolean"` | `<Switch>` 开关 | `show_avatar`、`enable_toc` |
| `type: "integer"` / `type: "number"` | `<Input type=number>` | `posts_per_row`、`narrow_px` |

还可以用 `format: "color"`、`minimum / maximum` 等扩展 schema 字段（后端校验走 `jsonschema.validate`，前端 Customizer 会按 `format` 输出颜色选择器）。

---

## 3. CSS 作用域：`[data-theme="<slug>"]` 前缀

Rosetta 全站默认使用 shadcn 风格的 CSS 变量（`--background / --foreground / --primary / --muted ...`）。
主题的 `style.css` **必须**把所有自定义选择器挂在 `[data-theme="<slug>"]` 前缀之下，否则会污染其它主题。

最小骨架：

```css
[data-theme="astro-paper-inspired"] {
  /* 1) 覆盖 CSS 变量 → 颜色、圆角、阴影等基础风格 */
  --background: 42 55% 99%;
  --foreground: 222 20% 15%;
  --primary: 245 65% 50%;
  --radius: 0.35rem;

  /* 2) 主题特有变量，Customizer 通过内联 style 改写 */
  --ap-accent: #4f46e5;
  --ap-narrow-px: 760px;
  --ap-posts-per-row: 1;
}

[data-theme="astro-paper-inspired"] .site-container {
  max-width: var(--ap-narrow-px);
  margin: 0 auto;
  padding: 0 1.25rem;
}

[data-theme="astro-paper-inspired"] .post-list {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

[data-theme="astro-paper-inspired"] .post-card {
  border-bottom: 1px solid hsl(var(--border));
  padding-bottom: 1.25rem;
  background: transparent;
  border-radius: 0;
  box-shadow: none;
}
```

> **主题变量 mods ↔ CSS 的联动**：前端 `useFrontendTheme().applyMods()` 会把 mods 中的
> 颜色 / 尺寸字段转换为 CSS 变量（如 `accent_color` → `--ap-accent`）后写入 `<body style>`，
> 因此主题 CSS 中只要读取对应的 `--xxx` 变量即可实现「后台改一个开关 → 前台立刻生效」。

---

## 4. 安装与切换

### 4.1 通过后台安装

1. 将主题目录放到 `frontend/themes/<slug>/`；
2. 登录后台 → 系统 → 主题平台 → 点击「扫描」；
3. 目标主题卡片 → 点击「激活」，系统互斥切换为该主题并写入 mods_default。

### 4.2 通过 REST API 安装 + 激活

```bash
# 1) 扫描
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  "https://example.com/api/admin/themes/_scan"

# 2) 激活
curl -X PUT -H "Authorization: Bearer <TOKEN>" \
  "https://example.com/api/admin/themes/astro-paper-inspired/activate"

# 3) 自定义 mods
curl -X PATCH -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  "https://example.com/api/admin/themes/astro-paper-inspired/mods" \
  -d '{ "accent_color": "#6d28d9", "posts_per_row": 2 }'
```

ZIP 上传 / 官方市场安装参见《REST API 参考》第 3 节。

---

## 5. 完整示例（astro-paper-inspired）

### 5.1 rosetta-theme.json

```json
{
  "id": "io.github.rosetta.astro-paper-inspired",
  "slug": "astro-paper-inspired",
  "name": "Astro Paper Inspired",
  "version": "0.1.0",
  "type": "blog",
  "description": "Astro Paper 风格：760px 窄栏居中、无大图 Hero、竖排列表、极细分割线。",
  "author": "Rosetta",
  "license": "MIT",
  "entry_css": "style.css",
  "screenshot": "screenshot.svg",
  "homepage": "https://rosetta.dev/themes/astro-paper-inspired",
  "tags": ["minimal", "paper", "narrow", "reading"],
  "mods_schema": {
    "type": "object",
    "additionalProperties": false,
    "properties": {
      "posts_per_row": {
        "type": "integer",
        "title": "每行文章数",
        "default": 1,
        "enum": [1, 2],
        "description": "首页文章列表栅格密度，2 列仅在 ≥ 1024px 宽度生效。"
      },
      "show_avatar": {
        "type": "boolean",
        "title": "显示作者头像",
        "default": true,
        "description": "文章卡片左侧是否展示作者头像。"
      },
      "accent_color": {
        "type": "string",
        "title": "主题强调色",
        "default": "#4f46e5",
        "format": "color",
        "description": "用于链接、按钮、标签的主色。"
      },
      "narrow_px": {
        "type": "integer",
        "title": "正文栏宽度(px)",
        "default": 760,
        "minimum": 560,
        "maximum": 1040
      },
      "site_subtitle": {
        "type": "string",
        "title": "站点副标题",
        "default": "写作 · 思考 · 分享"
      },
      "header_style": {
        "type": "string",
        "title": "顶部导航风格",
        "default": "centered",
        "enum": ["centered", "left-aligned", "hidden"]
      }
    },
    "required": ["posts_per_row", "show_avatar", "accent_color"]
  }
}
```

### 5.2 style.css 关键片段

```css
[data-theme="astro-paper-inspired"] {
  --background: 40 40% 99%;
  --foreground: 220 15% 16%;
  --muted: 40 18% 94%;
  --muted-foreground: 220 10% 40%;
  --card: 0 0% 100%;
  --border: 220 14% 90%;
  --primary: 245 58% 52%;
  --radius: 0.3rem;

  --ap-accent: #4f46e5;
  --ap-narrow: 760px;
}

[data-theme="astro-paper-inspired"] body {
  font-family: "Inter", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  letter-spacing: 0.005em;
}

[data-theme="astro-paper-inspired"] .site-container,
[data-theme="astro-paper-inspired"] .post-article {
  max-width: var(--ap-narrow);
  margin: 0 auto;
  padding: 0 1.25rem;
}

[data-theme="astro-paper-inspired"] .post-card {
  padding: 1.5rem 0;
  border-bottom: 1px solid hsl(var(--border));
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

[data-theme="astro-paper-inspired"] .post-card:last-child {
  border-bottom: none;
}

[data-theme="astro-paper-inspired"] .post-title {
  font-size: 1.35rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  transition: color 160ms ease;
}

[data-theme="astro-paper-inspired"] .post-title:hover {
  color: var(--ap-accent);
}

[data-theme="astro-paper-inspired"] a {
  color: var(--ap-accent);
  text-decoration: none;
  background-image: linear-gradient(currentColor, currentColor);
  background-size: 0% 1px;
  background-repeat: no-repeat;
  background-position: 0 100%;
  transition: background-size 200ms ease;
}

[data-theme="astro-paper-inspired"] a:hover {
  background-size: 100% 1px;
}

/* 响应式：posts_per_row = 2 时，使用栅格 */
@media (min-width: 1024px) {
  [data-theme="astro-paper-inspired"][style*="--ap-ppr:2"] .post-list,
  [data-ap-posts-per-row="2"][data-theme="astro-paper-inspired"] .post-list {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem 2rem;
  }
  [data-theme="astro-paper-inspired"][style*="--ap-ppr:2"] .post-card {
    border-bottom: none;
    padding: 0;
  }
}
```

> 以上两个 CSS 文件即可完成一个符合 Rosetta 规范的完整主题。把它们保存为
> `frontend/themes/astro-paper-inspired/rosetta-theme.json` 与 `style.css` 后，
> 在后台主题平台点击「扫描 → 激活」，即可立即生效。
