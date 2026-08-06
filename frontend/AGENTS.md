# Repository Guidelines

## Project Structure & Module Organization

ROSETTA 前端是基于 **Astro 7** + **Svelte 5** 的现代化博客主题,通过 Vite 代理与 FastAPI 后端(`http://localhost:8000`)对接。源码组织如下:

- `src/pages/` — Astro 文件路由。包含前台页面(`[...page].astro`、`posts/[...slug].astro`、`categories/`、`tags/`、`archive.astro`、`search.astro`、`friends.astro`、`guestbook.astro`、`about.astro`、`anime.astro`、`bangumi.astro`、`gallery/`、`dynamic/`、`login.astro`、`sponsor.astro`、`rss.*`、`robots.txt.ts`、`og/[...slug].ts`、`403/404/500.astro`)与后台管理(`/admin/*` 下含 posts、users、categories、tags、comments、friends、gallery、albums、announcements、banners、dynamics、nav、pages、monitor、settings、profile)
- `src/layouts/` — 三个布局:`Layout.astro`(基础 HTML 外壳)、`MainGridLayout.astro`(主页/文章网格布局)、`admin.astro`(后台布局)
- `src/components/` — 按领域分组:`analytics/`(GA/Umami/Clarity/51La)、`comment/`(Artalk/Disqus/Giscus/Twikoo/Waline)、`common/`(Button/CoverImage/Icon/Pagination/WidgetLayout 等通用件)、`controls/`(Search/TOC/LightDarkSwitch/DisplaySettings/FloatingControls)、`features/`(MusicPlayer/MusicManager/SakuraEffect/Live2DWidget/SpineModel/CodeGroupManager/FancyboxManager/KatexManager/FontSetup/EncryptedPost/BackgroundPlayer/TypewriterText)、`layout/`(Navbar/SideBar/Footer/PostCard/PostPage/CategoryBar/ConfigCarrier/NavMenuPanel/DropdownMenu/PostMeta/PostStats)、`misc/`(License/RecommendedPost/SharePoster)、`pages/`(anime/bangumi/dynamic/gallery 子组件 + AdvancedSearch)、`widget/`(Profile/Announcement/Categories/Tags/Calendar/SiteInfo/SiteStats/Music/Dynamic/SidebarTOC/Advertisement/SpineModel)
- `src/config/` — TypeScript 配置模块,通过 `index.ts` barrel 统一导出。包含 `siteConfig.ts`、`sidebarConfig.ts`、`navBarConfig.ts`、`profileConfig.ts`、`musicConfig.ts`、`backgroundWallpaper.ts`、`commentConfig.ts`、`analyticsConfig.ts`、`fontConfig.ts`、`displaySettingsConfig.ts`、`effectsConfig.ts`(樱花)、`expressiveCodeConfig.ts`、`footerConfig.ts`、`friendsConfig.ts`、`galleryConfig.ts`、`licenseConfig.ts`、`mermaidConfig.ts`、`plantumlConfig.ts`、`pioConfig.ts`(Live2D/Spine 看板娘)、`sponsorConfig.ts`、`announcementConfig.ts`、`coverImageConfig.ts`、`dynamicConfig.ts`。优先从 `@/config` 导入
- `src/types/` — 与 `src/config/` 一一对应的类型定义(`*Config.ts`),外加 `config.ts`(综合)、`anime.ts`、`bangumi.ts`、`sakura-worker.ts`、`iconify-svelte-offline.d.ts`
- `src/api/` — 后端 API 客户端层。`client.ts` 封装 `apiFetch/apiGet/apiPost/apiPut/apiDelete/apiUpload` 与 JWT token 管理(localStorage key `rosetta_token`/`rosetta_refresh_token`),通过 `ROSETTA_API_BASE` 环境变量或默认 `http://localhost:8000/api` 寻址。按模块拆分:`auth.ts`、`users.ts`、`blog.ts`、`pages.ts`、`comments.ts`、`content.ts`、`site.ts`、`admin.ts`
- `src/plugins/` — 15+ 自定义 remark/rehype 插件:`rehype-mermaid.mjs`、`rehype-plantuml.mjs`、`rehype-component-github-card.mjs`、`rehype-email-protection.mjs`、`rehype-external-links.mjs`、`rehype-figure.mjs`、`rehype-image-referrerpolicy.mjs`、`rehype-diagram-panzoom.mjs`、`remark-directive-rehype.js`、`remark-excerpt.js`、`remark-image-grid.js`、`remark-mermaid.js`、`remark-plantuml.js`、`remark-reading-time.mjs`、`remark-wiki-link.js`,以及 PlantUML 编码器与图表 pan-zoom 脚本
- `src/utils/` — `content-utils.ts`(内容排序/分页)、`crypto-utils.ts`(加密文章)、`date-utils.ts`、`dynamic-config.ts`(从后端加载音乐/壁纸/站点配置)、`fetch-dedup.ts`(请求去重)、`fontHelper.ts`、`gallery-utils.ts`、`image-utils.ts`/`lqip-utils.ts`(LQIP 生成)、`language-utils.ts`、`layout-utils.ts`(banner/壁纸判断)、`markdown-renderer.ts`、`navigation-utils.ts`、`responsive-utils.ts`(侧边栏响应式)、`setting-utils.ts`、`toc-utils.ts`/`toc-shared.ts`(目录生成)、`url-utils.ts`、`memos-adapter.ts`、`build-platform.ts`、`dynamic-utils.ts`、`icon-loader.ts`
- `src/i18n/` — `i18nKey.ts`(键定义)、`translation.ts`(查找)、`languages/` 下 6 种语言:`zh_CN.ts`、`zh_TW.ts`、`en.ts`、`ja.ts`、`ko.ts`、`ru.ts`
- `src/styles/` — CSS 与 Styl:`main.css`、`markdown.css`、`layout-styles.css`、`navbar.css`、`toc.css`、`gallery.css`、`categories.css`、`tags.css`、`dynamic.css`、`anime-bangumi.css`、`banner-title.css`、`expressive-code.css`、`fancybox-custom.css`、`photoswipe.css`、`scrollbar.css`、`custom-scrollbar.css`、`display-settings.css`、`transition.css`、`waves.css`、`widget-responsive.css`、`variables.styl`、`markdown-extend.styl`
- `src/content/` — 内容集合:`posts/`(博客文章 `.md`/`.mdx`,含 `images/` 与 `guide/`)、`spec/`(独立页面 about/friends/guestbook)、`dynamic/`(微博式动态 `.md`)
- `src/workers/` — Web Worker:`sakura.worker.ts`(樱花粒子特效离线计算)
- `src/constants/` — `constants.ts`(BANNER_HEIGHT/PAGE_WIDTH 等常量)、`icon.ts`(favicon 配置)、`lqips.json`(生成的 LQIP 数据)、`icons-data.json`(图标数据)
- `src/assets/` — 源码管理的图片:`images/DesktopWallpaper/`、`images/MobileWallpaper/`、`images/logo/`、`avatar.avif`
- `public/` — 静态资源:`favicon/`、`assets/`(css/fonts/images/js/music)、`gallery/`、`pio/`(Live2D 与 Spine 模型)、`anime-list.json`
- `scripts/` — 构建期工具:`generate-lqips.ts`(LQIP 生成)、`subset-fonts.ts`(字体子集化)、`new-post.js`(新建文章)、`new-dynamic.js`(新建动态)、`generate-favicon.cjs`、`quarantine-bad-posts.mjs`
- `docs/` — `README.ja.md`、`README.zh-TW.md`
- `.github/workflows/` — CI:`biome.yml`、`build.yml`、`deploy.yml`

## Build, Test, and Development Commands

包管理器强制使用 **pnpm**(`preinstall` 脚本通过 `only-allow` 拦截 npm/yarn)。Node.js >= 22 必需。

- `pnpm dev` / `pnpm start`:启动 Astro dev server,默认 `localhost:4321`,Vite 代理将 `/api/(blog|core|users|media|...)` 与 `/media` 转发到 `API_BASE_URL`(默认 `http://localhost:8000`)
- `pnpm check`:运行 `astro check` 类型与错误检查
- `pnpm type-check`:运行 `tsc --noEmit --isolatedDeclarations`
- `pnpm format`:Biome 格式化 `src`
- `pnpm lint`:Biome 检查并安全修复 `src`
- `pnpm build`:四步流水线 — `generate-lqips.ts` → `astro build` → `subset-fonts.ts` → `pagefind --site dist`
- `pnpm preview`:本地预览生产构建
- `pnpm new-post`:脚手架新博客文章
- `pnpm new-dynamic` / `pnpm new-d`:脚手架新动态条目
- `pnpm lqips`:单独重新生成 LQIP 数据到 `src/constants/lqips.json`

## Coding Style & Naming Conventions

**Biome 2.5** 是格式化与 lint 工具,配置见 `biome.json`:

- 缩进使用 **tab**,JavaScript/TypeScript 字符串使用 **双引号**
- 启用 `recommended` 规则集,并强化 `style` 规则:`noParameterAssign`、`useAsConstAssertion`、`useDefaultParameterLast`、`useEnumInitializers`、`useSelfClosingElements`、`useSingleVarDeclarator`、`noUnusedTemplateLiteral`、`useNumberNamespace`、`noInferrableTypes`、`noUselessElse` 均为 `error`
- `.svelte`/`.astro`/`.vue` 文件放宽:`useConst`、`useImportType`、`noUnusedVariables`、`noUnusedImports` 关闭
- 忽略 `src/**/*.css`、`src/public/**`、`dist/**`、`node_modules/**`、`src/constants/icons-data.json`、`src/constants/lqips.json`

命名约定:Astro/Svelte 组件用 `PascalCase`(`PostCard.astro`、`Search.svelte`);配置模块用 `camelCase` 并以 `Config.ts` 结尾(`siteConfig.ts`);工具用描述性 kebab-case(`date-utils.ts`、`crypto-utils.ts`);插件用 `remark-*`/`rehype-*` 前缀 + kebab-case。保持 `src/types` 与 `src/config` 一一对应。避免无关格式变动。

## Testing Guidelines

未配置专门的单元测试框架。提交前根据改动类型运行:

- 渲染/内容/生成资源相关:`pnpm check` + `pnpm type-check` + `pnpm build`
- 视觉/交互相关:用 `pnpm dev` 或 `pnpm preview` 验证,在 PR 中附截图
- 后端 API 对接:确保 FastAPI 后端运行在 `localhost:8000`,检查 `/api/config` 返回含 `music_*`/`wallpaper_*` 字段

未来添加测试时,放在对应特性附近,以本地文件名为 stem 命名。

## Commit & Pull Request Guidelines

使用 **Conventional Commits**,与现有历史一致:`feat: ...`、`fix: ...`、`chore: ...`、`docs: ...`、`refactor: ...`、`perf: ...`。提交和 PR 聚焦单一关注点。PR 应包含:简洁摘要、关联 issue、已运行的验证命令、UI 改动截图。重大功能或设计变更需先在 issue 或 discussion 中讨论。

## Security & Configuration Tips

- 不在配置文件中提交 secrets、tokens、service keys
- 部署相关设置放在目标平台环境变量中:`API_BASE_URL`(后端地址)、`ROSETTA_API_BASE`(前端 API 客户端基址)、`CF_WORKERS`(切换 Cloudflare Workers 适配器)
- 审查生成文件后再提交:`dist/`、`src/constants/lqips.json`、`src/constants/icons-data.json`、`.astro/`
- JWT token 存于 localStorage(`rosetta_token`、`rosetta_refresh_token`),401 响应自动清除并跳转 `/login/`
- 加密文章使用 `crypto-utils.ts` 客户端解密,密码不落库
- `rehype-email-protection.mjs` 对邮箱做混淆防爬取

## Deployment

- **Vercel**(默认,`vercel.json`)
- **Cloudflare Workers**(`wrangler.jsonc`,设置 `CF_WORKERS` 环境变量启用 `@astrojs/cloudflare` 适配器)
- 静态产物输出到 `dist/`,Pagefind 搜索索引在构建末尾生成
