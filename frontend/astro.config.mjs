import { setMaxListeners } from "node:events";
import path, { resolve as _resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const _src = _resolve(__dirname, "src");

import cloudflare from "@astrojs/cloudflare";
import { unified } from "@astrojs/markdown-remark";
import mdx from "@astrojs/mdx";
import sitemap from "@astrojs/sitemap";
import svelte from "@astrojs/svelte";
import { pluginCollapsibleSections } from "@expressive-code/plugin-collapsible-sections";
import { pluginLineNumbers } from "@expressive-code/plugin-line-numbers";
import swup from "@swup/astro";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig, fontProviders } from "astro/config";
import icon from "astro-icon";
import { pluginLanguageLogo } from "ec-lang-logo"; /* Language Logo */
import { pluginCollapsible } from "expressive-code-collapsible"; /* Collapsible */
import { pluginLanguageBadge } from "expressive-code-language-badge"; /* Language Badge */
import katex from "katex";
import "katex/dist/contrib/mhchem.mjs"; // 加载 mhchem 扩展
import rehypeAutolinkHeadings from "rehype-autolink-headings";
import rehypeCallouts from "rehype-callouts";
import rehypeCodeGroup from "rehype-code-group"; /* Tab 代码块 */
import rehypeComponents from "rehype-components"; /* Render the custom directive content */
import rehypeExpressiveCode from "rehype-expressive-code";
import rehypeKatex from "rehype-katex";
import rehypeSlug from "rehype-slug";
import remarkAdmonitionToBlockquoteCallout from "remark-admonition-to-blockquote-callout";
import remarkDirective from "remark-directive"; /* Handle directives */
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import remarkSectionize from "remark-sectionize";
import {
	expressiveCodeConfig,
	fontConfig,
	fontsList,
	mermaidConfig,
	plantumlConfig,
	siteConfig,
} from "./src/config";
import I18nKey from "./src/i18n/i18nKey";
import { i18n } from "./src/i18n/translation";
import { GithubCardComponent } from "./src/plugins/rehype-component-github-card.mjs";
import { rehypeDiagramPanZoom } from "./src/plugins/rehype-diagram-panzoom.mjs";
import rehypeEmailProtection from "./src/plugins/rehype-email-protection.mjs";
import rehypeExternalLinks from "./src/plugins/rehype-external-links.mjs";
import rehypeFigure from "./src/plugins/rehype-figure.mjs";
import rehypeImageReferrerPolicy from "./src/plugins/rehype-image-referrerpolicy.mjs";
import { rehypeMermaid } from "./src/plugins/rehype-mermaid.mjs";
import { rehypePlantuml } from "./src/plugins/rehype-plantuml.mjs";
import { parseDirectiveNode } from "./src/plugins/remark-directive-rehype.js";
import { remarkExcerpt } from "./src/plugins/remark-excerpt.js";
import { remarkImageGrid } from "./src/plugins/remark-image-grid.js";
import { remarkMermaid } from "./src/plugins/remark-mermaid.js";
import { remarkPlantuml } from "./src/plugins/remark-plantuml.js";
import { remarkReadingTime } from "./src/plugins/remark-reading-time.mjs";
import { remarkWikiLink } from "./src/plugins/remark-wiki-link.js";
import { collectUsedFontCssVars } from "./src/utils/fontHelper";

if (process.env.NODE_ENV === "development") {
	setMaxListeners(20);
}

// Astro SSR 适配器：统一使用 Cloudflare（cloudflare pages/platform 兼容性最佳）。
// 如需本地 Node 运行，可改用 @astrojs/node：
//   import node from "@astrojs/node"; adapter: node({ mode: "standalone" })
const adapter = cloudflare({
	prerenderEnvironment: "node",
});

// https://astro.build/config
export default defineConfig({
	site: siteConfig.site_url,

	base: "/",
	trailingSlash: "always",

	// Astro v7: output: "static" 默认（等同老的 hybrid）—— 页面默认 prerender 为静态 HTML，
	// 需 SSR 的页面前置 `export const prerender = false` 即可走 Cloudflare adapter 的函数执行。
	// 这样 Pagefind / SEO / 首屏速度最佳，同时保留 admin/oobe 的鉴权逻辑。
	output: "static",

	// HTML 压缩：生产默认 true，显式声明便于审计；关闭属性引号去除避免意外
	compressHTML: true,

	// Scoped 样式策略：:where() 包裹 scoped 选择器，零额外特异性，
	// 解决 [astro-xxx] 属性策略导致的 Tailwind 类名被 scoped 权重覆盖问题。
	// 参考 https://docs.astro.build/en/reference/configuration-reference/#scopedstylestrategy
	scopedStyleStrategy: "where",

	// 预取：保持默认 true，可显式指定策略；
	// 目前 Swup 内置 preload 已开启，Astro 原生 prefetch 用于 Swup 未覆盖的普通链接
	prefetch: {
		defaultStrategy: "hover",
	},

	// Dev 模式下显示工具栏
	devToolbar: {
		enabled: true,
	},

	// 安全：SSR 模式下 POST/表单提交校验 Origin
	security: {
		checkOrigin: true,
	},

	// 字体配置 - 只加载实际使用的字体，跳过未引用的以加快构建
	fonts: (() => {
		// 禁用字体功能时直接返回空数组，跳过 Astro Font API 集成
		if (!fontConfig.enable) return [];

		const used = collectUsedFontCssVars(fontConfig);
		return fontsList
			.filter((f) => used.has(f.cssVariable))
			.map((f) => {
				let provider;
				switch (f.provider) {
					case "google":
						provider = fontProviders.google();
						break;
					case "fontsource":
						provider = fontProviders.fontsource();
						break;
					case "local":
						provider = fontProviders.local();
						break;
					case "bunny":
						provider = fontProviders.bunny();
						break;
					case "fontshare":
						provider = fontProviders.fontshare();
						break;
					case "npm":
						provider = fontProviders.npm();
						break;
					default:
						provider = f.provider;
				}
				return { ...f, provider };
			});
	})(),

	adapter,

	// 图像优化配置
	image: {
		// 组件可自行传入 layout/widths；这里只控制 Markdown 正文图片
		layout: "none",
	},

	integrations: [
		swup({
			theme: false,
			animationClass: "transition-swup-", // see https://swup.js.org/options/#animationselector
			// the default value `transition-` cause transition delay
			// when the Tailwind class `transition-all` is used
			//
			// NOTE: 只保留 1 个核心容器 `#swup-container` 参与 Swup 切换：
			//   前台(MainGridLayout)、后台(admin.astro)、登录页(login.astro)、404 等
			//   所有页面都保证有该容器；其它 banner / sidebar / toc 容器只在前台有，
			//   若作为 Swup containers 会造成前台↔后台切页时触发
			//   "Container mismatch, aborting" 错误，回退到整页刷新。
			//   非核心容器改为在 Swup `content:replace` 钩子中由各自组件/布局
			//   监听 `content:replace` 自行重新初始化即可。
			containers: [
				"#swup-container",
			],
			smoothScrolling: false,
			cache: true,
			preload: true,
			accessibility: true,
			updateHead: true,
			updateBodyClass: false,
			globalInstance: true,
			// 滚动相关配置优化
			resolveUrl: (url) => url,
			animateHistoryBrowsing: false,
			skipPopStateHandling: (event) => {
				// 跳过锚点链接的处理，让浏览器原生处理
				return event.state?.url?.includes("#");
			},
		}),
		icon({
			include: {
				"material-symbols": ["*"],
				"fa7-brands": ["*"],
				"fa7-regular": ["*"],
				"fa7-solid": ["*"],
				"simple-icons": ["*"],
				mdi: ["*"],
				mingcute: ["*"],
				heroicons: ["*"],
				"heroicons-outline": ["*"],
				"heroicons-solid": ["*"],
			},
		}),
		svelte(),
		sitemap({
			filter: (page) => {
				// 根据页面开关配置过滤sitemap
				const url = new URL(page);
				const pathname = url.pathname;
				if (pathname === "/dynamic/" && !siteConfig.pages.dynamic) {
					return false;
				}
				if (pathname === "/friends/" && !siteConfig.pages.friends) {
					return false;
				}
				if (pathname === "/sponsor/" && !siteConfig.pages.sponsor) {
					return false;
				}
				if (pathname === "/guestbook/" && !siteConfig.pages.guestbook) {
					return false;
				}
				if (pathname === "/bangumi/" && !siteConfig.pages.bangumi) {
					return false;
				}
				if (pathname === "/gallery/" && !siteConfig.pages.gallery) {
					return false;
				}
				if (pathname === "/anime/" && !siteConfig.pages.anime) {
					return false;
				}

				return true;
			},
		}),
		mdx(),
	],
	markdown: {
		processor: unified({
			remarkPlugins: [
				remarkGfm,
				...(siteConfig.post.rehypeCallouts.enablePythonMarkdownAdmonitions !== false
					? [remarkAdmonitionToBlockquoteCallout]
					: []),
				remarkMath,
				remarkReadingTime,
				remarkWikiLink,
				remarkImageGrid,
				remarkExcerpt,
				remarkDirective,
				remarkSectionize,
				parseDirectiveNode,
				remarkMermaid,
				[remarkPlantuml, plantumlConfig],
			],
			rehypePlugins: [
				[rehypeKatex, { katex }],
				[rehypeCallouts, { theme: siteConfig.post.rehypeCallouts.theme }],
				rehypeSlug,
				rehypeCodeGroup,
				[rehypeMermaid, mermaidConfig],
				rehypePlantuml,
				rehypeDiagramPanZoom,
				rehypeFigure,
				[
					rehypeImageReferrerPolicy,
					{ domains: siteConfig.imageOptimization?.noReferrerDomains || [] },
				],
				[rehypeExternalLinks, { siteUrl: siteConfig.site_url }],
				[rehypeEmailProtection, { method: "base64" }], // 邮箱保护插件，支持 'base64' 或 'rot13'
				[
					rehypeComponents,
					{
						components: {
							github: GithubCardComponent,
						},
					},
				],
				[
					rehypeAutolinkHeadings,
					{
						behavior: "append",
						properties: {
							className: ["anchor"],
						},
						content: {
							type: "element",
							tagName: "span",
							properties: {
								className: ["anchor-icon"],
								"data-pagefind-ignore": true,
							},
							children: [
								{
									type: "text",
									value: "#",
								},
							],
						},
					},
				],
				// Expressive Code（成熟的代码高亮 + 复制按钮 + 行号 + 折叠 + 语言徽标 + 双主题）
				// 必须放在 rehype 管道末尾，在其它插件完成对 pre/code 的处理后再渲染
				[
					rehypeExpressiveCode,
					{
						themes: [expressiveCodeConfig.darkTheme, expressiveCodeConfig.lightTheme],
						useDarkModeMediaQuery: false,
						// 与站点 <html data-theme="one-light/one-dark-pro"> 同步切换
						themeCssSelector: (theme) => `[data-theme='${theme.name}']`,
						plugins: [
							// pluginLanguageBadge 配置 - 从expressiveCodeConfig读取设置
							...(expressiveCodeConfig.pluginLanguageBadge?.enable === true
								? [pluginLanguageBadge()]
								: []),
							// pluginLanguageLogo 配置 - 从expressiveCodeConfig读取设置
							...(expressiveCodeConfig.pluginLanguageLogo?.enable === true
								? [
										pluginLanguageLogo({
											color: expressiveCodeConfig.pluginLanguageLogo.color ?? "mono",
											excludedLangs:
												expressiveCodeConfig.pluginLanguageLogo.excludedLangs ?? [],
										}),
									]
								: []),
							pluginCollapsibleSections(),
							pluginLineNumbers(),
							// pluginCollapsible 配置 - 从expressiveCodeConfig读取设置，使用i18n文本
							...(expressiveCodeConfig.pluginCollapsible?.enable === true
								? [
										pluginCollapsible({
											lineThreshold:
												expressiveCodeConfig.pluginCollapsible.lineThreshold || 15,
											previewLines:
												expressiveCodeConfig.pluginCollapsible.previewLines || 8,
											defaultCollapsed:
												expressiveCodeConfig.pluginCollapsible.defaultCollapsed ??
												true,
											expandButtonText: i18n(I18nKey.codeCollapsibleShowMore),
											collapseButtonText: i18n(I18nKey.codeCollapsibleShowLess),
											expandedAnnouncement: i18n(I18nKey.codeCollapsibleExpanded),
											collapsedAnnouncement: i18n(I18nKey.codeCollapsibleCollapsed),
										}),
									]
								: []),
						],
						defaultProps: {
							wrap: false,
							overridesByLang: {
								shellsession: {
									showLineNumbers: false,
								},
							},
						},
						styleOverrides: {
							borderRadius: "0.75rem",
							codeFontSize: "0.875rem",
							codeFontFamily:
								"var(--font-jetbrains-mono), ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
							codeLineHeight: "1.5rem",
							frames: {},
							textMarkers: {
								delHue: 0,
								insHue: 180,
								markHue: 250,
							},
							languageBadge: {
								fontSize: "0.75rem",
								fontWeight: "bold",
								borderRadius: "0.25rem",
								opacity: "1",
								borderWidth: "0px",
								borderColor: "transparent",
							},
						},
						frames: {
							// 保留原生复制按钮，外观由 src/styles/expressive-code.css 覆盖成主题风格
							showCopyToClipboardButton: true,
						},
					},
				],
			],
		}),
	},
	vite: {
		define: {
			// 在 SSR / 客户端两侧直接可见的常量，避免页面通过相对路径跨目录 import package.json。
			// 用法：直接引用全局 __ROSETTA_PKG_VERSION__ 字符串（TS 中需要在 env.d.ts 声明）。
			__ROSETTA_PKG_VERSION__: JSON.stringify(
				process.env.npm_package_version || "2.0.0",
			),
		},
		optimizeDeps: {
			// 显式预构建 @swup/astro 的客户端模块，避免 dev 模式下
			// 动态 import 时出现 net::ERR_ABORTED（Vite 依赖优化未及时完成）
			include: [
				"@swup/astro/client/Swup",
				"@swup/astro/client/SwupA11yPlugin",
				"@swup/astro/client/SwupBodyClassPlugin",
				"@swup/astro/client/SwupHeadPlugin",
				"@swup/astro/client/SwupPreloadPlugin",
				"@swup/astro/client/SwupScriptsPlugin",
				"@swup/astro/client/SwupScrollPlugin",
				"@swup/astro/serialise",
				"@swup/astro/idle",
			],
		},
		plugins: [
			tailwindcss(),
			{
				name: "rosetta-trailing-slash-dev",
				/**
				 * Dev server 专用的尾斜杠跳转中间件。
				 * ---------------------------------------------------------
				 * 生产构建使用 trailingSlash: "always"，产物形如 /posts/index.html。
				 * 因此访问 /posts/（带尾 /）时静态服务器可直接命中，而访问 /posts
				 * （不带 /）需要在真实托管端（Nginx / Cloudflare Pages 规则等）
				 * 做 301。这里用 Vite 的 configureServer 在 dev 阶段补齐 307，
				 * 使开发时的行为与线上一致，避免浏览器出现 404。
				 */
				configureServer(server) {
					const needsSlash = new Set([
						"/posts",
						"/archive",
						"/categories",
						"/tags",
						"/about",
						"/friends",
						"/guestbook",
						"/dynamic",
						"/gallery",
						"/anime",
						"/bangumi",
						"/search",
						"/sponsor",
						"/admin",
						"/login",
						"/oobe",
						"/notifications",
					]);
					const extRe = /\.[a-zA-Z0-9]{1,6}$/;
					/**
					 * 注意：直接用 server.middlewares.use(fn) 会把中间件加到 Vite 内部
					 * 中间件列表的「尾部」—— Astero/vite 的路由 404 先执行，导致我们
					 * 的 307 永远轮不到。这里强制 stack.unshift 插到最前面，保证所有
					 * 内部中间件前先执行尾斜杠重写。
					 */
					const handler = function rosettaTrailingSlash(req, res, next) {
						const raw = req.url || "/";
						try {
							const u = new URL(raw, "http://x");
							const path = u.pathname;
							if (!path || path.endsWith("/") || extRe.test(path)) {
								return next();
							}
							if (!needsSlash.has(path)) {
								return next();
							}
							const rest = (u.search || "") + (u.hash || "");
							res.statusCode = 307;
							res.setHeader("Location", `${path}/${rest}`);
							res.setHeader("Cache-Control", "no-store");
							res.end();
						} catch (_) {
							next();
						}
					};
					// 立即插入一次（当前 stack 可能已有部分中间件）
					server.middlewares.stack.unshift({ route: "", handle: handler });
					// 用 post 钩子保证 Vite 注册完所有内部中间件后，仍然被我们插在最前面
					return () => {
						// 去重：确保 stack 里只有一个 handler
						const stack = server.middlewares.stack;
						let inserted = false;
						for (let i = 0; i < stack.length; i++) {
							if (stack[i].handle === handler) {
								inserted = true;
								stack.splice(i, 1);
								i--;
							}
						}
						stack.unshift({ route: "", handle: handler });
					};
				},
			},
		],
		server: {
			watch: {
				ignored: ["**/package/**", "**/ROSETTA-docs/**"],
			},
			proxy: {
				// 所有 /api/* 请求代理到后端，同源开发免 CORS
				// 默认 127.0.0.1 避免 Windows localhost 解析 IPv6 [::1] 导致 vite 代理偶发 404
				"/api": {
					target: process.env.API_BASE_URL || "http://127.0.0.1:8000",
					changeOrigin: true,
					secure: false,
					/**
					 * Bypass 规则：部分 /api/... 是 Astro pages 路由（本地 pages/api/*.ts），
					 * 不能被代理给后端，否则触发 ERR_ABORTED / 404 / 503（OOBE 未完成时）。
					 *  - pages/api/allPostMeta.json.ts → /api/allPostMeta.json
					 *  - pages/api/dynamic.json.ts   → /api/dynamic.json
					 *  - pages/og/[...slug].ts       → /api/og/* 是 pages 路由（非后端 API）
					 * bypass(req): return 非 null/undefined 字符串 → 走 Vite 本地（不代理），
					 *              return undefined/null → 正常走代理到后端
					 */
					bypass(req) {
						const path = (req && req.url) || "/";
						const file = path.split("?")[0];
						if (!file || file.startsWith("/api")) {
							// 白名单：这几个 /api/xxx 是 Astro 本地 pages API，不代理
							if (
								file === "/api/allPostMeta.json" ||
								file === "/api/dynamic.json" ||
								file.startsWith("/api/og/")
							) {
								return file; // 返回本地路径 → Vite 处理
							}
						}
						return undefined; // 其它 /api/* 正常代理到后端
					},
				},
				"/media": {
					target: process.env.API_BASE_URL || "http://127.0.0.1:8000",
					changeOrigin: true,
					secure: false,
				},
			},
		},
		resolve: {
			alias: {
				"@rehype-callouts-theme": `rehype-callouts/theme/${siteConfig.post.rehypeCallouts.theme}`,
				"@components": `${_src}/components`,
				"@assets": `${_src}/assets`,
				"@constants": `${_src}/constants`,
				"@utils": `${_src}/utils`,
				"@i18n": `${_src}/i18n`,
				"@layouts": `${_src}/layouts`,
				"@api": `${_src}/api`,
				"@": _src,
			},
		},
		build: {
			minify: "esbuild",
			esbuildOptions: {
				minify: true,
				// 删除 debugger 语句；console.log / console.debug 无副作用，未使用返回值时会被 dead code elimination 移除，
				// console.warn / console.error 保留，确保生产环境出错时仍有日志可查
				drop: ["debugger"],
				pure: ["console.log", "console.debug"],
			},
			rollupOptions: {
				onwarn(warning, warn) {
					// temporarily suppress this warning
					if (
						warning.message.includes("is dynamically imported by") &&
						warning.message.includes("but also statically imported by")
					) {
						return;
					}
					warn(warning);
				},
			},
			// Rolldown 兼容（Vite 8 + Astro 7 底层 Rolldown 不按 Node 条件 exports 解析 wasm）
			// satteri/browser.js 运行时会根据环境动态加载 wasm，这里 external 避免构建时报
			// "Rolldown failed to resolve import @bruits/satteri-wasm32-wasi"。
			rolldownOptions: {
				external: [
					"@bruits/satteri-wasm32-wasi",
					"@bruits/satteri-wasm32-wasi/satteri_wasm.wasm",
				],
			},
			// CSS 优化
			cssCodeSplit: true,
			cssMinify: "esbuild",
			assetsInlineLimit: 4096,
		},
	},
});
