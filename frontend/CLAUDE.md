# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ROSETTA 前端是基于 **Astro 7.1** + **Svelte 5** + **Tailwind CSS v4** 构建的功能丰富的博客主题,fork 自 [Fuwari](https://github.com/saicaca/fuwari) 并大幅扩展。通过与 **FastAPI 后端**(`http://localhost:8000`)对接获得动态能力:JWT 认证、动态配置(音乐/壁纸/Bing 壁纸)、后台管理、评论、相册、微博式动态等。主要语言为简体中文,i18n 支持 `zh_CN`、`zh_TW`、`en`、`ja`、`ko`、`ru` 六种语言。

## Commands

| Command | Purpose |
|---|---|
| `pnpm dev` / `pnpm start` | Dev server at `localhost:4321`,Vite 代理 `/api/*` 与 `/media` 到后端 |
| `pnpm build` | 生产构建四步流水线:LQIPs → Astro build → 字体子集化 → Pagefind 索引 |
| `pnpm preview` | 本地预览生产构建 |
| `pnpm check` | `astro check` 类型与错误检查 |
| `pnpm type-check` | `tsc --noEmit --isolatedDeclarations` |
| `pnpm lint` | Biome 2.5 检查 + 安全修复 `src` |
| `pnpm format` | Biome 格式化 `src` |
| `pnpm new-post` | 脚手架新博客文章 |
| `pnpm new-dynamic` / `pnpm new-d` | 脚手架新动态条目 |
| `pnpm lqips` | 重新生成 LQIP 数据到 `src/constants/lqips.json` |

包管理器 **pnpm**(`preinstall` 通过 `only-allow` 强制),Node.js >= 22,TypeScript 6.0,Biome 2.5.5。

## Architecture

### Astro + Svelte 混合架构

- `.astro` 组件用于静态内容与布局,在构建时渲染
- `.svelte` 组件用于交互 UI(Search、DisplaySettings、LightDarkSwitch、ClientPagination、AdvancedSearch、DynamicFeed、SharePoster、AnimeGrid、BangumiGrid 等),通过 `client:load` 或 `client:visible` 挂载为岛屿
- **Swup.js**(`@swup/astro`)处理 SPA 式页面过渡,支持多容器切换目标
- **Tailwind CSS v4** 通过 `@tailwindcss/vite` 插件集成,配合 `@tailwindcss/typography`
- **Astro Expressive Code** 提供代码高亮,启用 collapsible sections、line numbers、language badge、language logo 插件

### 三层布局系统

- `Layout.astro` — 基础 HTML 外壳:head、body、主题初始化、分析脚本、Swup 钩子、全局特性组件(MusicManager、SakuraEffect、CodeGroupManager、FancyboxManager、FontSetup、ConfigCarrier)
- `MainGridLayout.astro` — 主页/文章网格布局:Navbar、SideBar(左/右/双侧)、Banner、BackgroundPlayer、TypewriterText、CategoryBar、Footer、FloatingControls、ScrollDownIndicator、Live2DWidget、SpineModel
- `admin.astro` — 后台管理布局

### 配置驱动

所有特性通过 `src/config/` 下的 TypeScript 文件开关/配置,经 `src/config/index.ts` barrel 统一导出。关键配置:

- `siteConfig.ts` — 站点标题、URL、描述、关键词、主题色(hue)、页面宽度、favicon、卡片样式、文章设置(rehype callouts 主题等)
- `sidebarConfig.ts` — 侧边栏布局(left/right/both、widget 排序)
- `navBarConfig.ts` — 导航栏与搜索配置
- `musicConfig.ts` — 音乐播放器(meting/local 模式、音量、播放模式、歌词显示)
- `backgroundWallpaper.ts` — 壁纸模式(banner/fullscreen/overlay/none)、Bing 壁纸、dim opacity、home title
- `profileConfig.ts`、`commentConfig.ts`、`analyticsConfig.ts`、`fontConfig.ts`、`displaySettingsConfig.ts`、`effectsConfig.ts`(樱花)、`expressiveCodeConfig.ts`、`footerConfig.ts`、`friendsConfig.ts`、`galleryConfig.ts`、`licenseConfig.ts`、`mermaidConfig.ts`、`plantumlConfig.ts`、`pioConfig.ts`(Live2D/Spine 看板娘)、`sponsorConfig.ts`、`announcementConfig.ts`、`coverImageConfig.ts`、`dynamicConfig.ts`

`src/types/` 与 `src/config/` 一一对应,提供 TypeScript 类型定义。

### 内容集合

在 `src/content.config.ts` 中定义,使用 Astro 7 的 `glob` loader:

- `posts` — 博客文章(`src/content/posts/**/*.md`/`*.mdx`),frontmatter:title、published、updated、draft、description、image、tags、category、lang、pinned、author、sourceLink、licenseName/Url、comment、password、passwordHint、prevTitle/Slug、nextTitle/Slug
- `spec` — 独立页面(`src/content/spec/`),如 about、friends、guestbook
- `dynamic` — 微博式动态(`src/content/dynamic/*.md`),frontmatter:published、pinned、location

### 后端 API 集成

- **API 客户端**(`src/api/client.ts`):封装 `apiFetch`/`apiGet`/`apiPost`/`apiPut`/`apiDelete`/`apiUpload`,自动注入 JWT Bearer token,401 时清除 token 并跳转 `/login/`。基址由 `import.meta.env.ROSETTA_API_BASE` 或默认 `http://localhost:8000/api` 决定。每次请求自动附加 `lang` 参数(从 `siteConfig.lang` 映射到后端语言码,如 `zh_CN` → `zh`)
- **模块拆分**:`auth.ts`、`users.ts`、`blog.ts`、`pages.ts`、`comments.ts`、`content.ts`、`site.ts`、`admin.ts`
- **Vite 代理**(`astro.config.mjs`):dev 模式将 `/api/(blog|core|users|media|guestbook|voting|notifications|favorites|admin|webhooks|seo|monitoring|toc|captcha|messages|translate|announcement|activity|hero|post_series|post_encryption|scheduled_posts|comment_reactions|ranking|performance|bing|advanced|import_export)` 与 `/media` 转发到 `process.env.API_BASE_URL || "http://localhost:8000"`
- **动态配置**(`src/utils/dynamic-config.ts`):通过 `/api/config` 加载后端站点配置,转换前端 `MusicPlayerConfig` 与 `BackgroundWallpaperConfig`,带内存缓存与失败回退到 `src/config/` 默认值。`ConfigCarrier.astro` 在页面加载时调用并应用(壁纸模式、dim opacity、壁纸图片、home title、primary color),同时触发 `rosetta:config-loaded` 事件与音乐管理器 `reloadWithConfig()`

### Markdown 处理管线

`astro.config.mjs` 配置 15+ remark/rehype 插件链:

- **remark**:`remark-directive`(指令)、`remark-directive-rehype`(自定义指令渲染)、`remark-math` + `rehype-katex`(数学公式)、`remark-mermaid`/`remark-plantuml`(图表)、`remark-reading-time`(阅读时间)、`remark-wiki-link`(`[[wiki links]]`)、`remark-excerpt`(摘要)、`remark-image-grid`(图片网格)、`remark-sectionize`、`remark-admonition-to-blockquote-callout`
- **rehype**:`rehype-slug`、`rehype-autolink-headings`(锚点)、`rehype-external-links`(外链)、`rehype-figure`(图组)、`rehype-image-referrerpolicy`、`rehype-email-protection`(邮箱混淆)、`rehype-mermaid`/`rehype-plantuml`(图表渲染)、`rehype-diagram-panzoom`(图表缩放)、`rehype-component-github-card`(GitHub 卡片)、`rehype-code-group`(Tab 代码块)、`rehype-callouts`(提示框)

### 关键目录

- `src/components/` — 按领域组织:`analytics/`、`comment/`、`common/`、`controls/`、`features/`、`layout/`、`misc/`、`pages/`(anime/bangumi/dynamic/gallery 子组件)、`widget/`
- `src/plugins/` — 自定义 remark/rehype 插件与 PlantUML 编码器、图表 pan-zoom 脚本
- `src/i18n/` — `i18nKey.ts`(键定义)、`translation.ts`(查找)、`languages/` 下 6 种语言文件
- `src/utils/` — 内容排序、加密、日期、LQIP、TOC、字体、响应式、URL 等 22 个工具模块
- `src/pages/` — Astro 文件路由,含 `/admin/*` 后台管理(15+ 子页面)与 `/api/` 端点(`allPostMeta.json.ts`、`dynamic.json.ts`)
- `src/workers/` — `sakura.worker.ts` Web Worker(樱花粒子离线计算)
- `scripts/` — 构建期工具:`generate-lqips.ts`、`subset-fonts.ts`、`new-post.js`、`new-dynamic.js`、`generate-favicon.cjs`、`quarantine-bad-posts.mjs`

### 路径别名(tsconfig.json)

`@components/*`、`@assets/*`、`@constants/*`、`@utils/*`、`@i18n/*`、`@layouts/*`、`@api/*` → `./src/<dir>/*`;`@/*` → `./src/*`。扩展自 `astro/tsconfigs/base`,启用 `strictNullChecks`、`isolatedDeclarations`、`@astrojs/ts-plugin`。

## Code Style

- **Biome 2.5** 强制:tab 缩进、双引号、recommended 规则集
- `biome.json` 强化 `style` 规则:`noParameterAssign`、`useAsConstAssertion`、`useDefaultParameterLast`、`useEnumInitializers`、`useSelfClosingElements`、`useSingleVarDeclarator`、`noUnusedTemplateLiteral`、`useNumberNamespace`、`noInferrableTypes`、`noUselessElse` 均为 `error`
- `.svelte`/`.astro`/`.vue` 文件放宽:`useConst`、`useImportType`、`noUnusedVariables`、`noUnusedImports` 关闭
- 忽略 `src/**/*.css`、`src/public/**`、`dist/**`、`node_modules/**`、`src/constants/icons-data.json`、`src/constants/lqips.json`
- 提交约定:**Conventional Commits**(`feat:`、`fix:`、`chore:`、`docs:`、`refactor:`、`perf:`)

## Build Pipeline

四步流水线(`pnpm build`):

1. `scripts/generate-lqips.ts` — 为 `src/content/posts/` 与 `src/content/spec/` 下的图片生成 LQIP(Low Quality Image Placeholder)数据到 `src/constants/lqips.json`
2. `astro build` — Astro 构建,esbuild 压缩,移除 `debugger` 与 `console.log`/`console.debug`(保留 `console.warn`/`console.error`)
3. `scripts/subset-fonts.ts` — 字体子集化,仅保留实际使用的字符
4. `pagefind --site dist` — 生成静态搜索索引

LQIP 数据提交到仓库,改图后用 `pnpm lqips` 重新生成。图标数据 `src/constants/icons-data.json` 由 Biome 忽略,被 `src/components/common/Icon.svelte` 消费,无生成脚本。

## Frontend-Backend Integration

前端通过 Vite 代理与 FastAPI 后端对接,关键集成点:

- **认证**:JWT token 存于 localStorage(`rosetta_token`、`rosetta_refresh_token`),`src/api/client.ts` 自动注入 `Authorization: Bearer` 头,401 时清除并跳转 `/login/`
- **动态配置**:`/api/config` 返回站点配置(含 `music_*`、`wallpaper_*`、`site_*` 字段),`src/utils/dynamic-config.ts` 转换并缓存,`ConfigCarrier.astro` 在页面加载时应用到 DOM
- **语言映射**:前端 `zh_CN` → 后端 `zh`,`zh_TW` → `zh_Hant`,`en` → `en`,`ja` → `ja`(见 `src/api/client.ts` 的 `LANG_MAP_FRONTEND_TO_BACKEND`)
- **媒体**:`/media` 路径代理到后端,媒体文件由后端 `media/` 目录服务
- **后台管理**:`/admin/*` 页面通过 `src/api/admin.ts` 调用后端管理接口

## Deployment

- **Vercel**(默认,`vercel.json`)
- **Cloudflare Workers**(`wrangler.jsonc`,设置 `CF_WORKERS` 环境变量启用 `@astrojs/cloudflare` 适配器,`prerenderEnvironment: "node"`)
- 静态产物输出到 `dist/`,Pagefind 搜索索引在构建末尾生成
- CI 通过 `.github/workflows/`:`biome.yml`(lint)、`build.yml`(构建验证)、`deploy.yml`(部署)
