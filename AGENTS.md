# Rosetta 项目开发规范（v2026.09）

> 面向 AI 编程助手与人类工程师的项目级速查卡。开始工作前先读本文件，
> 再按子目录进入 `backend/AGENTS.md` 与 `frontend/AGENTS.md`。
> **本文档为唯一权威来源，所有与代码现状冲突的旧约束以本版为准。**

***

## 0. 元信息

| 项目        | 值                                                                            |
| --------- | ---------------------------------------------------------------------------- |
| 名称/版本     | Rosetta Blog `v2.1.1`（`pyproject.toml:3`）                                    |
| 定位        | 前后端分离博客平台（多主题、插件、i18n 四语、OOBE 向导、SEO）                                        |
| 前端目录      | `frontend/`（Nuxt 4.5 + Vue 3 + TS + Pinia + shadcn-vue + Tailwind v4）        |
| 后端目录      | `backend/`（FastAPI + SQLAlchemy 2.0 async + Pydantic v2 + Alembic + Aiohttp） |
| 包管理（后端）   | `uv`（根目录 `pyproject.toml` + `uv.lock`）`python>=3.10`                         |
| 包管理（前端）   | `pnpm@11.20`（`frontend/package.json` packageManager 锁版本）                     |
| Nitro BFF | `frontend/server/`（RSS / Sitemap / Robots / Bing 壁纸）                |
| 运行端口约定    | 后端 `127.0.0.1:8000`、前端 Nuxt `3000`、Nginx/NAT 对外 `80/443`                     |
| 统一入口（推荐）  | 项目根：`.\dev.ps1`（Windows PowerShell）并发启前后端                                    |

***

## 1. 架构（已固定，不讨论）

```
              ┌────────────────────────────────────────────────┐
              │                    Browser                       │
              └──────────────────────┬─────────────────────────┘
                                     │ https://domain (Nginx:80)
                                     ▼
              ┌────────────────────────────────────────────────┐
              │   Nginx (deploy/nginx-site.conf)                 │
              │   /api  ──► rosetta_backend upstream :8000      │
              │   /     ──► rosetta_frontend upstream :3000     │
              └─────┬──────────────────────────────────────────┘
                    │                                   │
                    ▼                                   ▼
         FastAPI :8000 (backend/)                 Nuxt SSR :3000 (frontend/)
          - Auth/JWT + CSRF + rate-limit         - SSR 公开页 / SPA 后台页
          - SQLAlchemy 2.0 async (PG/SQLite)     - composables: useAPI / apiFetch
          - Alembic 迁移                         - Pinia auth（skipHydrate）
          - OOBE 锁 + 插件钩子 + 主题管理          - i18n @nuxtjs/i18n 10.x
          - RSS/SEO/Bing 代理接口                 - Nitro BFF: rss/sitemap/robots/bing
```

| 层级        | 技术栈                                                                                                          | 代码位置                                                                                      |
| --------- | ------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| Web 前端    | Nuxt `4.5.2` + Vue 3 + TypeScript + Tailwind CSS v4 + shadcn-vue + Pinia 4 + @nuxtjs/i18n + zod/vee-validate | `frontend/`                                                                               |
| Nitro BFF | h3 + ohmyfetch（API 代理 · RSS/Sitemap/Robots 服务端聚合 · Bing 壁纸无 CORS 代理）                                         | `frontend/server/`                                                                        |
| 后端 API    | FastAPI `[standard]` + uvicorn `[standard]` + asyncpg / aiosqlite + Pydantic Settings                        | `backend/`                                                                                |
| ORM / 迁移  | SQLAlchemy 2.0 `[asyncio]` + Alembic `1.13+`（`backend/migrations/`）                                          | `backend/models/*` · `backend/migrations/*`                                               |
| 缓存        | Redis 8 + Memory 双后端；分布式锁 / 预热器                                                                              | `backend/core/cache*.py` · `cache_warmer.py` · `distributed_lock.py`                      |
| 认证        | PyJWT 2.10+ + argon2-cffi 24+ + bcrypt 5+ + cryptography 45+                                                 | `backend/core/auth.py` / `stores/auth.ts`                                                 |
| 国际化 i18n  | 固定四语：`zh` · `en` · `ja` · `zh_Hant`（fallbackLocale=`en`）                                                     | `frontend/i18n.config.ts` · `frontend/i18n/locales/*.json` + `frontend/i18n/index.ts` 双加载 |
| 管理端 UI    | shadcn-vue（reka-ui / radix-vue）+ Pinia + 46 个 admin 子页（`/admin/**`）                                          | `frontend/pages/admin/*` · `frontend/components/admin/*` · `frontend/components/ui/*`     |
| 测试        | 后端 pytest-asyncio 自动模式 + pytest-cov 45% fail\_under；前端 vitest 单测 happy-dom                                   | `tests/test_*.py` · `frontend/tests/unit/*.spec.ts`                                       |
| CI        | GitHub Actions（`.github/workflows/ci.yml`、`frontend/.github/workflows/ci.yml`）                                          | lint + typecheck + pytest + coverage 底线                                                   |

### 1.1 已落地的扩展系统

1. **主题系统**（WordPress 风格，2 套内建）：`frontend/themes/{editorial-wp-style,astro-paper-inspired}/`，必需 `rosetta-theme.json` + `style.css`（必须带作用域守卫）+ `screenshot.png|svg`；Customizer 字段在 `rosetta-theme.json` 内以 `mods_schema`（JSON Schema Draft-07）内联声明，mods 值存 SiteConfig KV `theme_mods:<slug>`。磁盘 ↔ DB 由「扫描」同步：非激活且磁盘已不存在的主题会被清为僵尸记录，激活主题升级前必须磁盘文件存在。主题皮肤完全自包含：默认主题的装饰层也在自己的 `style.css` 内（main.css 无皮肤）；无激活主题时前台回退加载默认主题（`useFrontendTheme` 的 `DEFAULT_THEME_*`），渲染路径上永远恰好一个完整主题。
2. **插件系统**（FastAPI 侧 Hook Engine，Bus 模式）：`backend/core/plugin_loader.py`（load/unload、运行时 settings 快照）+ `backend/core/plugin_bus.py`（钩子总线）+ `backend/core/hooks.py`（do_action / add_action 原语）；启动经 `backend/core/extensions.py::bootstrap_extensions` 扫描对齐，运行时插件路由经 `core/routing_registry.py` 统一挂载，三内建插件 `hello-rosetta` · `guestbook-rss` · `seo-toolkit`。短代码子系统集成点在 `core/shortcodes.py`（引擎 + `_MAX_NESTING_DEPTH` 深度闸门 + `_ALLOWED_TAGS` 输出白名单）与 `core/extensions.py`（API 方式注册的模板短代码落 KV `shortcode_templates`，启动/列表两处重放）；Admin 面板 `frontend/pages/admin/system/shortcodes.vue` 已消费其中 4 条（列表 / 管理员预览 / 注册模板 / 注销），公开口 `POST /api/shortcodes/render` 刻意不给编辑器用——预览需要上下文时走管理员口（见 `frontend/docs/API_COVERAGE.md`）。
3. **头像代理 / 解析器**：`/api/media/avatar?src=<base64>`，白名单 302 直跳 → 非白名单流式代理 → DiceBear SVG 兜底；前端 `useResolvedAvatar`。
4. **OOBE 安装向导**：锁文件 `backend/.oobe_complete`，缺则非白名单接口返回 `503 OOBE_REQUIRED`。
5. **SEO 服务端生成**：RSS 2.0 / Sitemap（索引 + pages/posts/taxonomies 子图）/ Robots / llms.txt / `.well-known/security.txt` 五条 Nitro Server-Route，口径见 §2.3.4。
6. **Bing 每日壁纸**：Nitro BFF `frontend/server/api/bing-wallpaper.get.ts`（30m SWR cache）+ 后端 `backend/api/bing_image.py`（今日图 / 最近 N 天归档 / 图片流式代理 `/api/bing/image?src=<base64>`）。公开消费方是 SSR 页 `frontend/pages/wallpapers.vue`（`GET /api/bing/image/archive` 的唯一读取者），页脚入口按同一个开关收起。四条口径：① **归档的日期只认上游 `startdate`**，不按 `date.today() - timedelta(idx)` 反推（服务器时区与 Bing 市场日界不同）；上游自己只保留 `UPSTREAM_RETENTION_DAYS`（线上实测 8）天，越过窗口 `idx` 会重复返回最旧那张图，所以一次批量 `n=` 取回 + 按 `urlbase` 去重，`count` 上限就是 `min(days, 8)`。② **非空结果进服务端缓存 3600s，空结果不写**——一次上游故障把空归档钉住一小时，等于把公开页缓存成空白。③ **图片一律走站内代理**（`frontend/lib/bing-image.ts::bingProxyUrl`，SSR 与客户端同一个纯函数产出 `<img src>`，否则每个卡片一次 hydration mismatch），把 `cn.bing.com` 原链挂进图片标签会绕开本站 30 天 immutable 落盘缓存与兜底 SVG。④ **「这页该不该存在」的判据单源**在 `backend/services/site_settings.py::bing_wallpaper_enabled`（扁平键 `ENABLE_BING_WALLPAPER` → `features` 组同名 bool 覆盖，两层都要读），前端 `publicConfig.enable_bing_wallpaper`、页脚入口、`noindex` 与后端 sitemap 收录（`blog.py::generate_pages_sitemap(include_wallpapers=…)`）四面共用它；`/api/config` 的投影由 `tests/test_bing_wallpaper_archive.py` 六状态对账钉住。新增顶层公开页还要同步 `frontend/lib/top-level-routes.ts` ↔ 后端 `_TOP_LEVEL_ROUTE_SLUGS` ↔ routeRules（见 `pageAliasTopLevelRoutes.spec.ts`）。
7. **Webhook 外发**：`backend/api/webhook.py` 把 hooks 总线事件投递到外部端点。事件名唯一清单是 `GET /api/webhooks/events`（= `WEBHOOK_EVENTS` = 总线 `do_action` 名），前端订阅 UI 必须消费该接口、不得自有一套命名；`main.py` startup 调 `register_webhook_listeners()` 挂接。投递请求头固定 `X-Rosetta-Event: <event.type>` + `X-Rosetta-Signature: sha256=<hmac_sha256(secret, 实际发出的 JSON 字节)>`；URL 每次发送前重过 SSRF 护栏（`core/net_guard.py` + `settings.webhook_allow_private_targets`）。`provider` 只是分类标签，签名/载荷格式对所有类型一致。**任何写路径（含批量入口 `POST /blog/posts/batch-status`、`POST /admin/posts/batch`）都必须与单篇路径同构地 `do_action`**——批量分支漏发钩子的表现是「用户改用多选后 Webhook 与插件监听静默失聪」，回归见 `tests/test_post_batch_hooks.py`。密钥明文仅在 `POST /{id}/regenerate-secret` 一次性返回，`WebhookOut` 只给 `has_secret`。回归测试：`tests/test_webhook_dispatch.py`。
8. **页面浏览边缘上报**：nginx 只把 `/api`、`/media` 转给 FastAPI，HTML 全部由 Nitro 自己渲染直接回浏览器——后端**从来没见过**那次页面请求，所以 `visit_logs` 本身只是"API 请求明细"（批次 #53 上线实测：经 nginx 打页面路径的两次访问在后端零记录，只有打 `/api/**` 的留下了行）。"谁在浏览这个站点"由 `frontend/server/middleware/09-pageview-report.ts` 在 `res` 的 `finish` 事件后 `POST /api/monitoring/pageviews` 补齐。四条口径：①只认 `Accept` 含 `text/html`/`application/xhtml+xml` 的 GET 文档请求，跳过 `/api`、`/media`、`/themes`、`/_nuxt`、`/_rosetta`、`/@*`、`/.well-known`、`/robots.txt`、`/rss.xml`、`/feed`、`/sitemap*`、`/placeholder-covers` 与一切带扩展名的路径——把机器面当"页面浏览量"会让读数失去意义；②IP 取 `x-forwarded-for` 第一跳（nginx `$proxy_add_x_forwarded_for` 写进去的那一跳），没有转发头才退回 socket 对端，绝不从 Host/x-forwarded-host 推导；③**Cookie 只发名字、不发值**（值是会话凭证，不该为遥测多走一跳），后端 `_cookie_names_from_raw` 落库前还会重导一次名称，这条红线不依赖调用方的自觉；④鉴权复用已有共享密钥对 `NUXT_PURGE_SECRET`（`frontend/.panel.env`）↔ `FRONTEND_PURGE_SECRET`（根 `.env`）、头名 `x-rosetta-purge-secret`，**不新增配置项**——任一侧为空即整条链静默关闭（前端拿到空串连请求都不发，后端 `hmac.compare_digest` 恒 403），表现是访客记录页只剩 API 行而**一个错都不报**，排查从这里开始。上报 fire-and-forget、刻意不 `await`、失败静默丢弃：后端不可达不能变成访客看到的 500。后端 `PageviewReport` 带 `extra="forbid"`，两侧字段一旦漂移＝每一条上报 422 且静默，由 `frontend/tests/unit/pageviewReport.spec.ts` 按「载荷键集合 ⇔ 后端字段集合」相等钉住，`tests/test_pageview_reporting.py` 钉住 403/202、队列满回 202 `recorded:false`（不 500）与 cookie 值不入库。消费侧口径：一次"读文章"= 1 条页面行 + N 条 API 行；页面行 `user_id` 恒为 null（JWT 在 localStorage，文档请求不带身份），所以详情标签是「匿名/未识别」而非「未登录」。

***

## 2. SSR 策略 & 混合渲染

### 2.1 基线

**全局 `ssr: true` + 精准反选 `ssr: false`。** 公开内容页全站 SSR 已验收。如需单页切回 SPA，写 `definePageMeta({ ssr: false })`。

### 2.2 精准反选表（Nitro routeRules）

| 路由                                            | SSR     | Cache               | 原因                               |
| --------------------------------------------- | ------- | ------------------- | -------------------------------- |
| `/admin/**` · `/admin`                         | ❌ false | `no-store, private` | 登录态 + 重交互 + localStorage       |
| `/login` · `/register` · `/forgot-password` | ❌ false | `no-store, private` | 表单状态、敏感输入                        |
| `/oobe`                                       | ✅ 继承全局 | `no-store, private` | 安装完成后 `oobe.global` 要走 SSR 级 302，`ssr:false` 会让它吐空壳并白屏 |
| `/admin/docs/**`                              | ❌ false | `no-store, private` | 内嵌 Markdown 编辑器与执行工具             |
| `/search/**`                                  | ❌ false | `no-store`          | 实时查询 + 高频率                      |
| `/account` · `/account/**`                        | ❌ false | `no-store, private` | 逐登录用户内容 + SSR 期无 token（auth store 是 skipHydrate） |
| `/settings`                                    | ❌ 页面级（routeRules 不重复写 ssr） | `no-store, private` | 主题偏好在 localStorage，onMounted 才读；routeRules 这条只补 HTTP 口径 |
| Vite 虚拟文件：`/@vite/**` · `/@id/**` · `/@fs/**` | ❌ false | `no-store`          | 防 HMR 404 被 spa-fallback 拦截      |

上表 8 行覆盖 14 条 routeRules 键，镜像关系由 `frontend/tests/unit/routeRulesSsr.spec.ts` 断言（`ssr:false` 集合精确相等 + `/oobe` 必须保留 SSR + 反选页必须 `no-store`）——改配置不改测试会直接红。

**`/settings` 是这套口径里唯一的"两套开关"页，也是它曾经漏配的原因**：SPA 反选写在页面里
（`definePageMeta({ ssr: false })`），routeRules 里没有这条，于是它静默落进 `'/**': { swr: 600 }`
的通配 —— 线上实测 `curl -I /settings` 与 `/en/settings` 都回
`public, max-age=0, s-maxage=600, stale-while-revalidate=86400`，一份 noindex 空壳被 CDN 缓存一整天。
"ssr:false 集合精确相等"那条断言看不见这类页（它只清点 routeRules 的键），所以同文件另有一条
**从 `pages/` 反向扫**的守卫：凡 `definePageMeta` 里出现 `ssr: false` 的页，其路径前缀必须有
一条 `cache: false` + `no-store` 的规则。新增页面级 SPA 页不需要再动 routeRules 的 ssr，但必须补这条缓存规则。

### 2.2.1 i18n URL 前缀（`prefix_except_default`）

`nuxt.config.i18n.strategy = 'prefix_except_default'`，`defaultLocale = 'zh'`：

| 语言 | 首页 | 文章详情 |
| ---- | ---- | -------- |
| zh（默认，裸路径） | `/` | `/posts/xxx` |
| en | `/en` | `/en/posts/xxx` |
| ja | `/ja` | `/ja/posts/xxx` |
| zh_Hant | `/zh_Hant` | `/zh_Hant/posts/xxx` |

关键约束：

1. **routeRules 自动镜像**：`nuxt.config.ts::expandLocaleRouteRules()` 会把上表每一条非 Vite/静态资源规则复制成 `/en/xxx`、`/ja/xxx`、`/zh_Hant/xxx` 三份。新增公开页 SSR/缓存规则只需写默认形态；漏写镜像不会报错，但带前缀页面会静默落回 SSR/无缓存。Vite 虚拟文件、`/_nuxt/**`、`/themes/**`、`/api` 前缀、`/rss.xml`、`/sitemap.xml`、`/robots.txt` 不镜像。
2. **SPA 反选白名单同步**：`server/plugins/spa-serverrendered-zero.nitro.ts` 的 `isSpa()` 会先剥 `/en /ja /zh_Hant` 前缀，再匹配 `/login /register /search /admin`；新增 SPA 前缀要两处一起写。
3. **canonical + hreflang**：都由 `composables/useSeo.ts` 单源产出，走纯字符串 helper
   `applyLocalePrefix(中性路径, locale)`（口径与禁令见 §2.3.3 第 1 条，**不要**再回到
   `useLocalePath()`）。`opts.url` 传"默认语言下的路径"（如 `/posts/xxx`）；带前缀形态会被
   `stripLocalePrefix` 剥掉再重挂。省略 `opts.url` 时按当前路由派生，noindex 页不产出 hreflang 集群。
4. **JSON-LD url/mainEntityOfPage**：`useArticleJsonLd` / `useBreadcrumbJsonLd` 同样走
   `applyLocalePrefix`，避免英文页面的 JSON-LD 声明中文 canonical。
5. **语言切换**：`components/LocaleSwitcher.vue` 与 `components/AppFooter.vue` 必须
   `setLocale(code)` 之后跳 `applyLocalePrefix(route.fullPath, code)` 得到的同页 URL；
   仅 `setLocale` 只换 i18n 内部状态、URL 留在旧前缀，等于内容与地址栏的语言互相判逆。
6. **`<meta property=og:locale>`**：`useSeo.ts::OG_LOCALE_MAP` 输出 `zh_CN/en_US/ja_JP/zh_TW`，`og:locale:alternate` 自动列出其它三语。
7. **Sitemap**：`backend/api/blog.py::_sitemap_url` 给每个内容输出 **4 条 `<url>`**
   （zh 裸路径 + `/en` `/ja` `/zh_Hant`），每条自带 5 个 `<xhtml:link rel=alternate>`
   （4 语 + `x-default`）。Google 要求带 hreflang 标注的每个 URL 都出现在 sitemap 里，
   只提交默认语言那条会让三个语言变体只剩"页面内 hreflang"这一个发现入口。
   守卫见 `tests/test_api_seo.py::test_sitemap_children_have_no_duplicate_loc`。
   **RSS** 仍是单语言（默认语言）源，语言入口靠 sitemap 与页面 hreflang，不重复挂 `<xhtml:link>`。

### 2.3 公开页 SWR / Cache 头

首页/文章列表 `/posts` swr 300s · 归档/关于/友情/系列 swr 3600s · 活动/图库 swr 600s · 分类/标签/作者主页/文章详情/独立页 swr 600s · 热门榜 `/posts/hot` swr 60s · 留言板 swr 60s。常规页附带 `Cache-Control: public, max-age=0, s-maxage=<T>, stale-while-revalidate=86400`；高频实时页（`/posts/hot` · `/guestbook`）用较短的 `stale-while-revalidate=600`。
静态资源 `/_nuxt/**` 与 `/themes/**` 使用强缓存 immutable（31536000s）。

**这条口径不是 routeRules 写下去就自动成立的**：Nitro 的 swr 缓存处理器会在响应阶段把
`Cache-Control` **整条覆写**成 `s-maxage=<T>, stale-while-revalidate`（丢掉 `public, max-age=0`，
也丢掉 swr 的秒值）。只剩 `s-maxage` 时浏览器私有缓存没有显式新鲜期，退化成 HTTP 启发式新鲜期
（`(Date − Last-Modified)` 的 10%），实测表现是"后台改了站点设置、Nitro 页面缓存已清、curl 立刻拿到新值，
但回访访客的 Chrome 直接用磁盘里的旧 HTML"（`navigation[0].transferSize === 0`）——而站点设置是 SSR 时
烘进 `__NUXT_DATA__` payload 的，`useSite` 客户端见 `loaded=true` 就不再拉 `/api/settings/public`。
裸的 `stale-while-revalidate` 还不合 RFC 5861（必须带 delta-seconds），可能被整条忽略。
口径由 `frontend/server/plugins/ssr-html-revalidate.nitro.ts`（`render:response` + `beforeResponse` 双跑，
归一函数幂等）+ `frontend/server/utils/ssrHtmlCacheControl.ts` 补回，只补 `public, max-age=0`
并按本页 `s-maxage` 档回填 swr 秒值（`SWR_BY_SMAXAGE`，默认 86400）——**新增带其它 swr 窗口的公开页时，
除 routeRules 外还要在该映射里登记一条**。两个坑踩过：①只改钩子 payload 里的 `headers` 袋无效，
线上那份头真正写在 Node `ServerResponse` / h3 `outHeaders` 上（`ssrHtmlCacheControl.spec.ts` 有接线断言）；
②无条件补 86400 会把 60s 热榜的软过期窗口撑成一整天。`no-store` 的后台/登录/搜索页与强缓存静态资源
必须原样不动。

**3xx 的 HTML 由同一个钩子强制 `no-store`**（`redirectHtmlCacheControl`，301/302/303/307/308；
304 刻意排除）。这条是 2026-10-30 线上实测补上的：越界页码闸门在 `app:rendered` 里写的 `no-store`
会被响应阶段的 routeRules 处理器整条覆写，`/posts?page=9999` 与 `/authors?page=9999` 实际回的是
`public, max-age=0, s-maxage=…`——§2.2.2 承诺的"301 必须 no-store"此前在头这一层从未成立。
页面侧改不动（它先跑），所以只能在最后一道 `beforeResponse` 归一里按状态码兜住；
新增任何依赖"跳转不得被缓存"的页面时，不要再指望页面里的 `setHeader`。

### 2.3.1 动态子路由必须用目录式父页

`pages/x.vue` 与 `pages/x/[id].vue` **不能并存**：前者会变成没有 `<NuxtPage>` outlet 的父路由，
子路由 URL（`/x/2026`）会**静默渲染父组件并返回 HTTP 200**——不报错、不 404，看起来"有内容"，
实则新页面从未执行。要给 `/x` 加 `/x/{id}`，必须先把父页挪成 `pages/x/index.vue`。
实例与反向断言见 `frontend/pages/archive/index.vue` + `frontend/pages/archive/[year].vue`
与 `frontend/tests/unit/archiveYearRoute.spec.ts`。

### 2.3.2 HTTP 状态码闸门只能放路由中间件

公开页（尤其是带 `swr` 的 SEO 页）需要"这个 URL 不存在"时，**不要**在页面 `<script setup>` 里
`throw createError({ statusCode: 404 })`：实测它会把 `error.vue` 渲染出来但**响应仍是 HTTP 200**，
并且这个 200 会按该路由的 `swr` 被缓存成一个可复用的"正常页"——对爬虫与 SEO 等于承认页面存在。
正确做法是命名路由中间件（不进全局链）里 `return abortNavigation(createError({ statusCode: 404, … }))`，
这与 Nuxt 自身未命中路由的行为同轨（浏览器 `Accept: text/html` 下同样渲染 error.vue + 真 404，
`cache-control: no-cache`）。实例见 `frontend/middleware/archive-year.ts` + `pages/archive/[year].vue`
的 `definePageMeta({ middleware: 'archive-year' })`，契约见 `archiveYearRoute.spec.ts`。
附带收益：垃圾参数不会走到 `useAPI`，后端也就拿不到机会返回 422。

**依赖异步数据的 404 判定**（内容详情页：文章 / 分类 / 标签 / 独立页 / 系列 / 作者 / 归档月）另有三条坑，
实测踩过，口径见 `frontend/composables/useContentStatus.ts`：

1. `useFetch / useAsyncData` 的 payload 是 Nuxt 在渲染前才 await 落值的——**setup 同步期
   `data.value` 还是 null**，在那儿判"内容为空"会把每一个真实页面一起判成 404。判定必须
   推迟到 `app:rendered`（`renderToString` 之后、响应发出之前，状态码还改得动）。
2. `useRequestEvent()` 必须在 setup 同步期取好、闭包带走：异步回调里再取会拿到 `undefined`
   （本仓未开 `nitroAsyncContext`），闸门会静默失效、页面全回 200。
3. 只有后端明确 404、或请求成功但对象为空才改状态码；网络故障 / 5xx 一律不动——
   把一次临时故障写成 404，搜索引擎会当成永久删除而掉索引，比 200 更难恢复。
4. **`<title>` / robots / canonical 必须与状态码同口径**：404 响应配一个"看起来正常"的标题（`系列 · 系列`、
   `2026-09 归档`）等于给搜索引擎两份互相矛盾的信号。判定共用导出的
   `isContentMissing()`，页面侧不要再写一套 `!data`。
   实测另一半：闸门回了 404，`useSeo` 仍默认输出 `index, follow, max-image-preview:large…`
   并自带一条指向自己的 canonical + hreflang 集群——爬虫挑哪份信号不可控。口径是把
   `isContentMissing` 提成页面自己的 `*NotFound` 计算属性，同时喂给标题、
   `useSeo({ noindex: *NotFound })`、JSON-LD 三处（noindex 内部已抑制 canonical/hreflang，
   不要给常量 `noindex: true`，那会把有内容的这一页一起禁索引）；契约见
   `contentNotFoundStatus.spec.ts`。独立页口（顶级 catchall）的 Article JSON-LD 走
   `useArticleJsonLd({ path })`，`/page/<slug>` 兼容口同理，缺内容时传空串 = 不输出。
5. **`useSeo` 里"支持 Ref 的入参"一律用 `'value' in obj` 解包，不得用 `hasOwnProperty`**：
   Vue 3.5 的 `computed()` 是 class 实例，`value` 是原型链上的 getter，`hasOwnProperty`
   看不到它 → 整个 ComputedRef 被当裸字符串交给 `applyLocalePrefix` → `.startsWith` 抛
   TypeError，而这段跑在 `useHead` 求值路径上 = 整页 500（实测独立页口）。同一坑的
   另一种表现见 §2.3.3 第 1 条，`seoLocaleUrl.spec.ts` 钉住解包写法。

清单由 `frontend/tests/unit/contentNotFoundStatus.spec.ts` 递归清点 `pages/` 下带动态段的
公开页来兜：新增一页若没接闸门（也没挂 `archive-year` 这类命名中间件），测试直接红。
系列详情页就是手写清单漏掉的那一条——渲染了"系列不存在"，HTTP 仍是 200，还被
`/series/**` 的 swr 3600 缓存成可复用页面。

独立页有两个入口：`pages/page/[slug].vue` 只做兼容重定向，**顶级 catchall `pages/[slug].vue`
才是真实落地路由**——它接住每一条形如 `/任意单段` 的 URL，所以 404 闸门与
`useContentStatus` 必须接在它上面（自愈 301 跳走的那条要排除在外，否则 301 会被改成 404）。

### 2.3.3 语言前缀下的 URL 单源（SEO 与链接图）

i18n 走 `prefix_except_default`（zh 裸路径，en/ja/zh_Hant 挂前缀）且**没有** per-locale 自定义
路由路径，所以"某页在某语言下的 URL"就是一道纯字符串算术。五条口径：

1. canonical / hreflang / og:url / JSON-LD 的 URL 一律走 `applyLocalePrefix(中性路径, locale)`
   （`frontend/composables/useSeo.ts`）。**禁止** `localePath()` / `switchLocalePath()`：它们按
   **路由名**解析传入字符串，`/posts/{中文 slug}` 在 SSR 期产出过非字符串，`asAbsolute` 于是在
   `path.startsWith` 上抛 TypeError，而这段跑在 `useHead` 求值路径上 → **每一篇文章详情页整页 500**。
   旧构建因 `siteUrl` 为空串提前 return，把这个坑藏了整整一轮。
2. 模板里爬虫能读到的站内链接一律 `:to="localeHref(path)"`（`frontend/composables/useLocaleLink.ts`，
   与 SEO 侧同一个 helper）。SSR 里的 href 是爬虫看到的**唯一**链接图，不挂前缀等于把站内权重
   全推给默认语言版本。`localeHref` 对外链 / 锚点 / `//host` 原样透传（后台配置的导航与 CTA 可能是
   外链，硬挂前缀会产出 `/enhttps://…` 死链）。`middleware/locale-prefix.global.client.ts` 只是
   客户端兜底重写，**不能**当作爬虫面。
3. 全站每个页面只有一条 canonical，由 `useSeo` 产出：缺省 `url` 时按当前路由派生，查询串白名单
   只有 `page`（`CANONICAL_QUERY_KEYS`）——`search` / `category` / `sort` 是同一份列表的视图变体，
   写进规范地址等于向搜索引擎声明每个筛选组合都是独立页面。**不得**在页面里再拼一份
   `rel: 'canonical'`，尤其不能用 `useRequestURL()` / 请求 Host 拼地址：Nitro 的 swr 缓存按路径分键、
   不含 Host，一次请求的 Host 会被固化成 TTL 内所有访客看到的规范地址（缓存投毒面）。站点根单源是
   `usePublicSiteUrl()`，生产只接受 `NUXT_PUBLIC_SITE_URL`，仅回环 Host 允许推导（`LOOPBACK_HOST_RE`）。
4. robots.txt 只挡"根本不该被抓"的机器面（`/api/`、`/admin/`）。`/login` · `/register` ·
   `/forgot-password` · `/account` · `/search` · `/oobe` 改为页面自带
   `<meta name="robots" content="noindex, follow">`（`useNoindexPage()`）并**从 Disallow 移出**——
   Disallow 挡的是抓取，抓不到就读不到 noindex，Google 反而会按已发现的链接生成"无摘要索引条目"。
   **但这条交易只在"meta 真的出现在原始 HTML 里"时成立**：ssr:false 反选页的 `useNoindexPage()`
   只在 hydration 后写 `<head>`，curl 拿到的空壳一行 robots 都没有，不执行 JS 的抓取器读不到。
   所以服务端必须补这一行——`frontend/server/utils/noindex-shell.ts`（路径前缀唯一清单，
   含三种语言前缀形态）+ `frontend/server/plugins/noindex-shell-meta.nitro.ts`（`render:html`
   注入，检测到已有 robots 就跳过，SSR 页不会出两条规范）。新增 noindex 页只改 .vue 不登记名单
   =静默失效，由 `frontend/tests/unit/noindexShellMeta.spec.ts` 递归扫 `pages/` 双向钉住
   （声明了 noindex 却没进名单、进了名单却无对应页、ssr:false 路径漏覆盖，都会红）。
   全仓只允许一种写法：`noindex, follow`（单源常量 `useSeo.ts` 的 `NOINDEX_ROBOTS`）；
   写 `noindex, nofollow` 等于一边声明"允许抓取"一边掐断这些页面上所有内链的抓取。
   robots 的模式是纯前缀匹配、没有语言概念，剩下每条 Disallow 必须 ×4 语言前缀，且
   `frontend/server/routes/robots.txt.get.ts`（回退）与 `backend/api/seo.py`（真源）两段同口径。
5. 任何用 `startsWith` / 前缀判定路径归属的地方必须先过 `stripLocalePathPrefix()`
   （`frontend/lib/rosetta-themes.ts`，语言前缀唯一清单是同文件的 `I18N_URL_PREFIXES`，
   消费方不得再自己拼 `(en|ja|zh_Hant)` 正则）。漏一处的表现：`/en/admin` 被当成前台页、
   英文页导航整条不亮、`/en/posts` 落回无缓存 SSR（`nuxt.config.ts::expandLocaleRouteRules`
   负责 routeRules 那一侧的镜像）；后台外壳的两个实例是 `components/admin/AdminHeader.vue`
   的面包屑（`findMenuItem/findMenuGroup` 的键是 `/admin/xxx` 形态）与
   `components/admin/AdminSidebar.vue` 的菜单高亮。
6. **语言真相只有 URL 前缀**：`i18n.detectBrowserLanguage` 必须是 `false`。开着它（`redirectOn: 'root'`）
   时 Googlebot 带的 `Accept-Language: en` 会让 `GET /` 跳到 `/en`，中文首页与它自指的 canonical
   就对不上（Google 官方口径也是"给候选、由用户点选，不要按 Accept-Language 重定向"）。
   回访保序靠 `rosetta_lang` cookie + `middleware/locale-prefix.global.client.ts`，且该中间件
   **不改写裸 `/`**（它是默认语言首页、也是 `x-default` 指的位置）；语言入口是顶栏与页脚切换器，
   两者都必须 `setLocale` 后跳到前缀化的同页 URL，只 `setLocale` 等于内容与地址栏的语言互相判逆。

契约分别钉在 `seoLocaleUrl.spec.ts` · `archiveYearRoute.spec.ts` · `routeRulesSsr.spec.ts` ·
`contentNotFoundStatus.spec.ts`；窄屏外壳与首页 hero 另有 `mobileShellLayout.spec.ts` ·
`heroMobileLayout.spec.ts`（口径见 `frontend/AGENTS.md`「窄屏外壳单源口径」）。

### 2.2.2 顶级 catchall 的 `/**` 通配缓存（三条硬约束）

独立页 `/privacy` 这类单段 URL 由 `pages/[slug].vue` 接住，靠 `'/**': { swr: 600 }` 获得与其它
公开页一致的 SWR（此前这条真实落地路由没有任何规则，每访客每页都重渲染 + 打后端）。
**Nitro 的页面缓存是按「渲染器路由」套的，不是按请求路径**——这条通配规则会给整条渲染器 handler
套上 `cachedEventHandler`，于是三条约束必须同时满足（每条都实测踩过）：

1. **所有 `ssr:false` / `no-store` 路由必须显式写 `cache: false`**（`/admin/**` · `/login` ·
   `/register` · `/forgot-password` · `/search/**` · `/account/**` · `/settings` · `/oobe` · Vite 虚拟文件）。
   否则它们自己的 `Cache-Control: no-store` 会被缓存处理器覆写成 `s-maxage=600`——实测 `/login`
   一度变成"可公开缓存 10 分钟"。`swr: false` **不足以退出**：routeRules 用 defu 合并，通配层的
   `cache` 会被合并回来；只有 `cache: false` 在规范化阶段把 cache 整条置空。
2. **内部端点同样 `cache: false`**：`/_rosetta/**`（后端调用的清缓存入口是 POST，被缓存后第二次
   调用直接回放上次响应、真正的清缓存不再执行——表现就是"改了内容前台不更新"）与 `/api/**`
   （Nitro 侧只有 Bing 壁纸，它自带 30m `defineCachedEventHandler`，再套一层＝双份缓存）。
3. **`/**` 只写 `swr`、不写 `headers`**：`routeRules.headers` 由 `createRouteRulesHandler` 按路径
   匹配后无条件 `setHeaders`，在 `/**` 上挂 `Cache-Control: public` 会把代理响应与静态资源一起
   盖成可缓存。缓存头由 Nitro swr 处理器 + `ssr-html-revalidate` 补齐（见 §2.3）。

404 不会被这套缓存固化：渲染器抛错时 `cachedFunction` 拿到 rejected promise、不写缓存，`error.vue`
仍按 `no-store` 输出——实测同一垃圾 URL 连请两次都是 ~60ms + `no-store`，而命中缓存的正常页 4–5ms。

守卫：`frontend/tests/unit/routeRulesSsr.spec.ts`（SPA 路由必须 `cache: false`、内部端点必须
`cache: false`、`/**` 只能是裸 swr）。

### 2.2.3 页面缓存清除（`POST /_rosetta/purge-cache`）的两条实现约束

后端 `purge_frontend_page_cache()` 是 fire-and-forget、失败只记日志，所以这条链路的两处实现细节
都属于"错了也看不出来"的那一类：

1. **请求头必须跨 event 形态读取**：Nitro 2.13 的路由处理器拿到 web 形态 event，随包打入的
   `getRequestHeader` 走 `event.node.req.headers`——实测该对象是**空对象**，于是即使前后端密钥一致
   也恒被 403，主题切换/独立页改动在整个 SWR 窗口内都不生效。`server/utils/purgeSecret.ts` 依次尝试
   h3 API → web `Headers` → `node.req.headers` → **`node.req.rawHeaders`**（实测唯一有值的地方）。
2. **键名匹配不能写死前缀**：同一份产物里边页面缓存键出现过 `cache:nitro:routes:_:…`（默认 storage）
   与 `nitro:routes:_:…`（`cache` 挂载点）两种形态。写死 `useStorage('cache').getKeys('nitro:routes')`
   的结果是"只清掉 server-routes 那几条、页面 HTML 一条不清"。现在按 `/nitro[/:]routes/` 扫两个
   storage 的全部键。

实测闭环（本机 build + 真实 DB）：`GET /独立页` 83ms → 5ms（SWR 命中）；后台改正文 → 后端
fire-and-forget purge → 再 GET 立刻是新内容。回归 `tests/test_page_cache_purge.py`（写路径三次各清
一次、读路径一次不清）与 `frontend/tests/unit/purgeSecretHeader.spec.ts`（四种 event 形态）。

### 2.3.4 SEO/GEO 投递面单源（纯文本口 · 兜底图 · @graph）

1. **纯文本口与 rss/sitemap/robots 同轨**：`server/routes/{llms.txt,robots.txt,rss.xml,sitemap*.xml}.get.ts`
   与 `server/routes/.well-known/security.txt.get.ts` 的站点根只认 `resolvePublicSiteOrigin`（配置单源），
   **绝不**从请求 Host 推导——这些路由带 `s-maxage`，一次 Host 伪造会被缓存固化给所有访客。
   连后端一律走 `resolveBackendEndpoint`，且**上游全挂时必须降级成 200 的最小文本**（500/503 对抓取器
   不可接受），不得 `createError`。
   **每条 feed 路由都必须在 `nuxt.config.ts::routeRules` 里显式登记**，不能靠 `'/**': { swr: 600 }` 兜：routeRules 是按
   「路由处理器」套缓存的，通配规则同样包住 `server/routes` 下的静态路由——2026-10-30 线上实测
   子 sitemap 回了 600s 前的旧正文（后端已含新增 `/authors`，Nitro 仍在发旧副本）。
   登记口径是 `swr: <handler 的 s-maxage>` +（有软过期时）`cache: { staleMaxAge: <handler 的
   stale-while-revalidate> }`；**不要在 routeRules 里写 `Cache-Control`**——swr 缓存处理器写回响应时
   会用 `s-maxage=<maxAge>[, stale-while-revalidate=<staleMaxAge>]` 整条覆写（与 §2.3 那条 HTML 被覆写同源），
   写在 headers 里的完整串线上不落地。守卫 `frontend/tests/unit/feedRouteCacheRules.spec.ts` 按目录反扫
   （handler 集合 ⇔ routeRules 键集合）+ 逐条对账这两个数与 Content-Type。
2. **security.txt 只有一条生成路径**：`server/routes/.well-known/security.txt.get.ts`。nitropack
   `scanDir` 的 globby 带 `dot:true`，点目录会被收录，所以**不要**再补 `server/routes/security.txt.get.ts`
   或 `/.well-known` 别名中间件（两条口会让正文分叉，`geoDeliveryRoutes.spec.ts` 反向断言它们不存在）。
   带语言前缀的 `/en/.well-known/security.txt` 不是路由。正文不公开任何邮箱：`Contact` 指向 `/about`
   与 `/guestbook`，`Expires` 由 `Date.now()` 生成（写死的历史日期等于长期失效）。
3. **文章兜底封面单源** `lib/post-cover.ts`，展示面与分享面分开取值：
   **展示面**（列表卡片 / 详情页头图 / 首页兜底轮播）无 `cover_image` 时回落
   `https://picsum.photos/seed/<seed>/<w>/<h>` 随机图（seed→FNV-1a 派生，SSR 与 hydrate 同图，
   后端 `api/hero.py::_display_cover` 同口径），`<img @error>` 经 `handlePostCoverError`
   切站内 6 槽渐变 SVG `/placeholder-covers/<n>.svg`（同 seed 同槽位）兜底，外链被墙也不碎图；
   尺寸对是 `POST_COVER_CARD`(640×427) 与 `POST_COVER_DETAIL`(1200×800)。
   **分享面**（og:image / twitter:image / JSON-LD ImageObject）走 `postShareImage`，
   无封面是站内 `public/og-default.png`，**绝不**拿 picsum 外链或占位 SVG
   （外部服务限流即无图、社交爬虫不渲染 SVG）。槽位数改动必须同步 `public/placeholder-covers/`
   的文件数，`postCover.spec.ts` 会逐个 `existsSync`。
4. **一篇文章只有一个 `@graph`**：`useArticleJsonLd`（`composables/useSeo.ts`）一次产出
   BlogPosting / Person / Organization / BreadcrumbList / ImageObject，靠稳定 `@id` 互链；
   `WebSite + SearchAction` 是首页专用的 `useWebsiteJsonLd`，不要塞进文章页。
   页面里**不得**再单独调 `useBreadcrumbJsonLd`（两份 BreadcrumbList 等于让爬虫自己挑一份，
   独立页 `pages/[slug].vue` 与 `pages/page/[slug].vue` 已删掉那一条）。面包屑首项名走 `t('nav.home')`，
   写死 `Home` 会让中文页的面包屑是英文。后端侧同口径的公开口是
   `/api/seo/schema/{resource_type}/{resource_id}` 与 `/api/seo/open-graph/{resource_type}/{resource_id}`
   （文章分支产 `og:image` 时用 `post.cover_image or 站点默认分享图`，绝不产出 picsum 之类外链）。
   这两条口在后台的消费方是 `pages/admin/tools/seo.vue` 的「爬虫预览」标签，三条契约不得改：
   **无 `{success,data}` 信封**（裸对象）、**不可见资源回 HTTP 200 且只剩 `error` 键**（不是 404，
   承认存在即可按 id 枚举草稿/定时/隐藏主页，所以 `200 ≠ 有内容`，页面必须判 `error` 走警告分支）、
   **不读调用方身份**（内部固定按 `post_is_publicly_visible(post, None)` 判定，管理员登录态不会让预览
   "解锁"出爬虫看不到的东西——后台看到的警告就是爬虫的真相）。守卫 `seoCrawlerPreviewWired.spec.ts`
   按"后端 `@router.get` 声明集 ⇔ helper 请求集"与"后端 `og:*/article:*/twitter:*` 键集 ⇔
   `AdminSeoOpenGraph` + `OG_ROW_KEYS`"双向对账：后端加一个 og 键而前端清单没登记＝抓取器读得到、
   后台永远看不到。
5. **sitemap 索引的 `<lastmod>` 取分组真实 `max(updated_at)`**（`backend/api/blog.py::_sitemap_*_lastmod`），
   空表省略该标签；全站同一个"生成时间"会被搜索引擎判成站点长期未更新。
   **RSS 的 `<lastBuildDate>` 用构建时间**且不得早于任何一条 `pubDate`。
6. **IndexNow 是可选投递面**：`seo.indexnow_enabled` 默认 `false`，密钥由运营者提供，
   **不得**写死、打印或提交。seo 是 `PUBLIC_SETTING_GROUPS` 成员（匿名可读 + 300s 缓存），
   所以组内任何凭据形态都必须被 `_SENSITIVE_KEY_RE` 命中（该正则含 `_key$`，
   而 `keywords` 这类 SEO 可见文案不结尾于 `_key` 才不会被误掩码）；
   回归 `tests/test_indexnow.py::test_public_projection_masks_indexnow_key`。
   开关关闭 / key 为空 / site_url 无主机名 → 不发请求且不报错。

契约钉在 `geoDeliveryRoutes.spec.ts` · `articleJsonLdGraph.spec.ts` · `postCover.spec.ts` ·
`canonicalSingleSource.spec.ts` · `heroLcpAttributes.spec.ts` · `postsPaginationLinks.spec.ts`，
后端侧见 `tests/test_api_seo.py` · `tests/test_indexnow.py`。

### 2.4 SSR 安全守则（违反必出 Hydrate 错）

1. 组件 `setup()` 顶层禁止直接读 `window / document / localStorage / navigator / matchMedia`；必须包 `if (import.meta.client) { … }` 或 `onMounted`
2. `useHead` / `useState` / `useRoute` / `useRuntimeConfig` 由 **Nuxt 自动导入**；不得从 `@unhead/vue`、`vue`、`vue-router` 导入同名函数
3. 首渲染字节级一致：`ref()` 初始值两端相同；客户端独有状态在 `onMounted` 赋值或用 `useState` 序列化
4. Pinia token/user：`auth.ts` 使用 `skipHydrate`，仅在客户端写 localStorage
5. 明/暗主题首渲染：`useTheme.ts` 首帧 useState 恒为 light；`plugins/theme.client.ts` Hydrate 后才真正应用

***

## 3. 主题样式 ↔ Admin UI 解耦（三层 CSS + 四层防御）

**永远不能让前台主题样式影响后台（shadcn Card / Button / Input）。**

【2026-09 解耦架构】CSS 分三层，职责互斥：
- `assets/css/main.css` = 主题中性基础设施（Tailwind、令牌、prose、toast、
  `.card-surface` **中性基座版**：素色+1px 细边框）。不含任何"皮肤"。
- `assets/css/admin-ui.css` = Admin 冻结设计系统（装饰版玻璃卡/彗星发光描边/
  lift-hover），全部选择器锁死 `html[data-layout-scope="admin"]`——后台观感
  与主题包零依赖，升主题永不影响 Admin。
- `themes/<slug>/style.css` = 前台主题完整皮肤。默认主题 editorial-wp-style
  自带全套 Editorial 装饰层（作用于 frontend + public-auth 段落）；
  「无激活主题」时 `useFrontendTheme` 回退加载该默认主题（DEFAULT_THEME_*），
  保证渲染路径上永远恰好一个完整主题 CSS——"默认主题闪帧"在架构上不存在。

| 层 | 机制 | 位置 |
| - | --- | --- |
| 1 | 运行时路径检测：进入 `/admin/**` / `/oobe` 时 `clearThemeVisual`，反之 `applyThemeVisual`；`/login` / `/register`（scope=`public-auth`）允许注入主题属性/链接，frontend 守卫规则在认证页不命中 | `composables/useFrontendTheme.ts` |
| 2 | 布局主动清理：`layouts/admin.vue` 与 `layouts/default.vue` 在 `onMounted` + `watch(route)` 双节点清理 | `frontend/layouts/*.vue` |
| 3 | 全局中间件兜底：`layout-scope.global.ts` 向 `<html>` 写 `data-layout-scope="frontend"|"admin"|"public-auth"`（`/oobe` 与 `/admin/**` 同按 admin 处理，判定共用 lib `isThemeVisualExcluded`） | `frontend/middleware/layout-scope.global.ts` |
| 4 | CSS 选择器作用域守卫：主题 `style.css` 通用选择器必须最前带 `:is([data-theme="..."],[data-rosetta-theme="..."])[data-layout-scope="..."]` | `frontend/themes/*/style.css` |

硬红线：
- `.card-surface` 在 main.css 只有**中性基座版**；主题要装饰它必须带完整双守卫（主题属性 + layout-scope），禁止无守卫覆写
- Admin 装饰样式只允许写在 `admin-ui.css`（`html[data-layout-scope="admin"]` 前缀），**禁止**把新装饰加回 main.css
- Admin 保留 shadcn 原生 Tailwind 原子类，禁止为"视觉统一"套主题自定义
- 禁止给 Admin 卡片加左侧彩条 `.border-l-4 border-primary/…`

***

## 4. BaseURL 双端单源（不可散落改写）

### 4.1 环境变量别名链（优先级由高到低）

```
SSR / Nitro 侧私有：  SSR_API_BASE_URL  >  NUXT_API_BASE  >  ROSETTA_API_BASE  >  BACKEND_HOST+BACKEND_PORT  >  (开发默认 http://127.0.0.1:8000/api)
浏览器端公开：        API_BASE_URL      (同源 / 跨域填完整域名)
                         ↓ 注入为
                    runtimeConfig.public.apiBase
```

生产必须在 `.env` 中显式提供三选一或 `BACKEND_HOST+PORT`；开发缺失自动回退到 `127.0.0.1:8000/api`。

### 4.2 代码侧单源调用

| 场景 | 该用的函数/Composable | 不该用的写法 |
| ---- | ------------------- | ----------- |
| 页面/组件 setup 期数据获取（SSR 友好） | `useAPI<T>(url, { query, method, … })` | 裸 `$fetch` + `onMounted` 调（首屏白屏） |
| 用户交互/提交 | `apiFetch<T>(url, { method, body })` | 硬写 `/api/xxx` + 手写 baseURL 拼接 |
| 后台静默刷新（无 toast） | `silentApiFetch<T>(url)` | 直接 `$fetch`（401 不会自动刷新 token） |
| Nitro Server-Route 连 FastAPI | `resolveBackendEndpoint(runtime, '/blog/rss')` from `server/utils/ssr.ts` | 写死 `'http://127.0.0.1:8000/api'` 字面量 |

**路径书写铁律：** `useAPI / apiFetch / silentApiFetch / resolveBackendEndpoint` 的 URL 参数**永远不带 `/api` 前缀**；baseURL 已自带。

### 4.3 实现位置

- 浏览器侧：`frontend/composables/useApi.ts`（`resolveApiBase` · `useAPI` · `apiFetch` · `silentApiFetch`）
- Server-Route 侧：`frontend/server/utils/ssr.ts`（`resolveSsrBackendBase` · `resolveBackendEndpoint`）

***

## 5. 目录结构

```
Rosetta/
├─ backend/                          FastAPI 后端
│  ├─ main.py                        入口；中间件链（由外到内：CORS → 安全头 → 维护模式 → 限流 →
│  │                                 TrustedHost(生产条件启用) → i18n → OOBE → 租户 → 请求日志 → 性能）。
│  │                                 注意：CSRF 不是中间件，是 per-route 依赖 core/csrf.py::require_csrf
│  ├─ api/                           46 个模块文件（activity … webhook；含共享 helper `_user_response_helper.py`）
│  ├─ core/                          基础设施（config / database / auth / cache / csrf / rate_limit / exceptions /
│  │                                 plugin_loader + plugin_bus + hooks（插件引擎）…）
│  ├─ models/                        SQLAlchemy 2.0 DeclarativeBase（blog / user / gallery / site …）
│  ├─ schemas/                       Pydantic v2 请求/响应模型（多语言 dict 的真源在 core/i18n.py）
│  ├─ repositories/                  Repository 层（base / post / user）
│  ├─ services/                      业务层（user_service / media_service / email_service / avatar_resolver / recommendation …）
│  ├─ migrations/                       Alembic 版本化迁移（4 个历史文件名含中文，git ls-files
│  │                                 会把它们显示成带引号的八进制路径，易被误判为垃圾文件；
│  │                                 新迁移一律 ASCII + revision 前缀）
│  ├─ scripts/                       mock_data / auto_oobe / reset_admin_password …
│  ├─ plugins/                       hello-rosetta / guestbook-rss / seo-toolkit
│  └─ data/                          四语 seed_content + 市场缓存
│
├─ frontend/                         Nuxt 4.5 前端（srcDir = 根 `frontend/`，无 app/ 目录）
│  ├─ pages/                          80 个页面文件 = 30 个前台公开页（SSR，含 /login /register /forgot-password /settings 四条 SPA 反选与 /oobe）+ 4 个登录态个人中心（`/account` + `/account/settings` + `/account/messages` + `/account/notifications`，SPA）+ 46 个 admin 子页（SPA）
│  ├─ components/                    共享组件 + admin/ + ui/（shadcn-vue 31 种原子组件）
│  ├─ composables/                   32 个文件（useXxx 组合函数 + i18n/图标常量等非 composable 辅助）
│  ├─ layouts/                       default.vue（前台）· admin.vue（后台）
│  ├─ stores/                        Pinia：auth.ts（skipHydrate）
│  ├─ middleware/                    admin.global · layout-scope.global · oobe.global · locale-prefix.global.client（全局）+ archive-year · auth-required（命名，仅挂在与文件名）
│  ├─ plugins/                       01-site-bootstrap.global / 02-hydration-safety.global.client /
│  │                                 06-font-stylesheet.client / debug.client / echarts.client /
│  │                                 error-handler.client / site-title.global / theme.client
│  ├─ server/                        Nitro BFF（routes/ + api/ + utils/ssr.ts + plugins/spa-serverrendered-zero.nitro.ts）
│  ├─ themes/                        editorial-wp-style · astro-paper-inspired
│  ├─ i18n/locales/                  {zh,en,ja,zh_Hant}.json + .ts 工厂（唯一生效目录）
│  ├─ assets/css/main.css            主题中性基础设施（Tailwind 入口 + 令牌 + .card-surface 中性基座）
│  ├─ assets/css/admin-ui.css        Admin 冻结设计系统（data-layout-scope="admin" 专属装饰层）
│  ├─ nuxt.config.ts                 SSR · runtimeConfig · routeRules · i18n · vite 补丁插件
│  └─ package.json                   pnpm 11.20 packageManager 锁
│
├─ tests/                            Pytest（本机 2026-10-29 全量：2363 passed + 23 skipped + 2 xfailed + 2 xpassed + 0 failed，覆盖率 72.83%（须先删 .coverage，见 §8），fail_under=45%；另有 test_coverage_main_and_middleware 两条**顺序性**假失败，见 §8.4）
├─ deploy/                           生产部署脚本（linux-install.sh / windows-start.ps1 / nginx-site.conf）
├─ docker/                           backend-entrypoint.sh · nginx.conf
├─ .github/workflows/ci.yml          根级 CI
├─ dev.ps1 · dev.bat                 并发启前后端
├─ start.ps1 · stop.bat · stop.ps1   与 dev.* 同族的服务入口/清理脚本
├─ rosetta.json                      站点单源配置文件（backend/core/paths.py::CONFIG_FILE）；运行期生成、已 .gitignore，勿提交
├─ media/                            上传与派生媒体的落盘目录；运行期生成、已 .gitignore
├─ static/ · logo/                   对外静态资源与品牌图源（logo/ 已追踪，供 favicon / OG 生成参考）
├─ design.qa.yaml                    design-review 插件的 Design QA 配置（非运行时依赖，只被 QA 工具消费）
├─ .env.example · .env.production · .env.docker
├─ pyproject.toml / uv.lock
├─ docker-compose.yml · Dockerfile
└─ AGENTS.md                         本文件
```

***

## 6. 环境变量模板

| 位置 | 用途 | 必备 SSR 变量 | 必备浏览器变量 |
| ---- | ---- | ------------ | ------------- |
| `.env.example`（根） | 开发模板 | `NUXT_API_BASE=http://127.0.0.1:8000/api` · `SSR_API_BASE_URL=…` · `BACKEND_HOST/PORT` | `API_BASE_URL=/api` · `NUXT_PUBLIC_API_BASE=/api` |
| `.env.production`（根） | 生产部署 | 同三条写死 | `API_BASE_URL=/api` · `SITE_URL=https://…` |
| `.env.docker`（根） | Docker compose | `NUXT_API_BASE=http://backend:8000/api` · `SSR_API_BASE_URL=http://backend:8000/api` | `NUXT_PUBLIC_API_BASE=/api` |
| `frontend/.env.example` | 纯前端子目录 | 三别名 + 默认 127.0.0.1:8000/api | `API_BASE_URL=/api` |

后端可选变量（不写就走默认值，`.env.example` 已示例）：

| 变量 | 默认 | 作用 |
| ---- | ---- | ---- |
| `CACHE_WARMUP_ENABLED` | `true` | 启动时预热热点响应缓存（站点配置/导航/分类/标签/友链），并挂后台定时刷新任务 |
| `CACHE_REFRESH_INTERVAL` | `3600`（下限 60） | 上述定时刷新的间隔（秒） |
| `LOG_RETENTION_DAYS` | `7`（1–3650） | 只增日志表（`visit_logs` / `performance_metrics` / `operation_logs`）的保留天数，后台循环按此批量删除更早的行 |
| `LOG_RETENTION_INTERVAL_HOURS` | `6`（1–168） | 上述保留扫描的间隔（小时）。**先睡后删**：进程启动首轮不删，短生命周期进程（含测试）不会误删数据 |
| `TRUSTED_PROXY_IPS` | `[]`（空＝不采信任何转发头） | 受信反代地址列表。只有直连对端在里面时 `get_client_ip` 才读 `X-Forwarded-For` / `X-Real-IP`，且 `is_internal_request`（限流绕行 + 访客记录跳过）只会对"受信对端且不带转发头"成立。**nginx 同机反代必须配 `["127.0.0.1"]`**，否则访客记录整站 IP 是回环（独立访客读成 1），Nitro SSR 打 `127.0.0.1:8000` 的内部调用还会和真实访客共用同一个限流桶 |

**列表型设置项（`cors_origins` / `cors_allow_methods` / `cors_allow_headers` / `trusted_proxy_ips` / `allowed_extensions` / `supported_languages`）三种写法都接受**：JSON 数组、逗号分隔、单值。这不是糖——pydantic-settings 对 `list[str]` 的默认解码是**严格 JSON**，`TRUSTED_PROXY_IPS=127.0.0.1` 这种最自然的写法会在 `Settings()` 构造期抛 `SettingsError`，即**进程直接起不来**（2026-10-29 实测，而字段描述与后台告警文案都教运营者这么写）。收口点是 `core/config.py::_decode_env_lists`（配 `Annotated[list[str], NoDecode]`），新增列表设置项必须同批进它的字段清单，由 `tests/test_config_env_list_parsing.py::test_every_list_setting_is_covered` 双向钉住；坏 JSON 仍然报错，不会被当成一个元素静默收下。

日志保留刻意不用分布式锁——该锁要求启用 Redis，单机/内存缓存部署会直接抛错；删除以 id 集合为条件、幂等，多 worker 各跑各的安全。口径副作用：默认 7 天窗口会把 `GET /api/monitoring/visits/summary` 的 `month`（30 天窗口）截短成保留窗口本身，所以该端点响应自带 `retention_days` + `data_since`（现存最早一条日志的时间），消费方必须据此把被截短的窗口标成下界、不得当全量读数；要真实覆盖 30 天就把 `LOG_RETENTION_DAYS` 设 ≥31。`/visits/summary` 由仪表盘页消费，明细口 `GET /api/monitoring/visits` 由 `pages/admin/tools/visits.vue` 消费（同一族两个页面各取一段，集合相等由 `frontend/tests/unit/monitoringEndpointsWired.spec.ts` 对账）。

这两个开关与 `REDIS_ENABLED` **无关**：Memory 后端同样是有效的响应缓存，而单机部署进程重启即冷启动，预热收益反而更大。

***

## 7. API 响应契约

### 7.1 HTTP 成功（2xx）

```jsonc
{
  "success": true,
  "data": { /* Pydantic response_model 序列化结果 */ },
  "message": "可选人类可读提示"
}
```

### 7.2 HTTP 失败（4xx / 5xx）

```jsonc
{
  "success": false,
  "error_code": "INVALID_CREDENTIALS | OOBE_REQUIRED | VALIDATION_FAILED | THEME_MODS_INVALID | PLUGIN_ZIP_BAD_MANIFEST | …",
  "message": "人类可读错误描述",
  "errors": [ { "field": "password", "message": "密码至少 8 位", "type": "value_error" } ]
}
```

- `401` → apiFetch 自动 `refreshAccessToken`；刷新失败 → 清 login 态 → 跳 `/login`
- **`401` 只表示「身份凭证失效」**。已登录业务端点的校验失败（旧密码错、二次确认错）必须用 `400`；
  用 `401` 等于让前端把这次操作判成登录过期——用户只是打错一个字符就被整站登出。回归见
  `tests/test_api_user_management.py::test_change_password_v2_wrong_current_is_not_401`
- `503 OOBE_REQUIRED` → 前端跳 `/oobe`
- 失败**一律** toast 给用户，"静默失败"是 bug

### 7.3 i18n 字段类型规范

- 管理模块 `name / title / description` 类 i18n 字段：后端必须返回完整 dict `{zh, en, ja, zh_Hant}`，不得返回单个字符串或缺失 key
- UGC 通知（留言、评论）的 title/message：明文字符串存，禁止自动翻译

### 7.4 响应体文档（OpenAPI）规范

全仓 JSON 端点的响应 schema 已补齐（缺口 166 → 0），由 `tests/test_api_docs_baseline.py` 钉在 **0**：新增端点不声明响应体就是 CI 失败。补文档时**只允许**下面两种手法：

| 手法 | 运行时影响 | 用途 |
| ---- | ---------- | ---- |
| `responses={200: {"model": M}}` | **无**（只产出 `$ref`） | 返回裸 dict / 已被 handler 自行构造模型的所有 JSON 端点 |
| `responses=raw_content_response(media, desc, binary=…)` + `response_class=Response` | 无 | RSS / sitemap / robots / 图片 / zip 等非 JSON 端点，声明真实媒体类型 |

禁止的手法（都会**改变运行时行为**，不是文档）：

1. ❌ 给返回裸 dict 的端点加 `response_model=M`——Pydantic 会**静默丢弃**模型里没写的键（SSR 页面正在读 `data` / `total` / `page`）。
   例外：handler 本身就 `return M(...)` 时可以加；提交前用 `model.model_fields` 与 handler `return` 的键集做一次差分，`会被丢弃=[] 必填但缺失=[]` 才算安全。
   反向同理：**不挂 response_model 时也不要把裸 ORM 实例 `return` 出去**赌编码器兜得住。`jsonable_encoder` 对 SQLAlchemy 对象走「内省已加载属性」——`_sa_instance_state` 会被正确跳过，但没落进 `__dict__` 的列**整键消失**（实测未设 `created_at` 的实例编码后只剩 5 个键）。响应形态因此取决于这一刻对象加载了什么，而不是 `responses={200: {"model": …}}` 承诺了什么；要么按 §9.1 回读一次，要么在 handler 侧显式构造字典（口径见 `api/favorite.py::_favorite_row`）。
2. ❌ 用 `-> Any` / `-> dict[str, Any]` / `-> list[dict[str, Any]]` 注解"凑"文档——本仓 FastAPI 会把它**派生成真实 response_model**：
   实测端点返回裸 ORM 实例时直接 **500**，而 OpenAPI 里只多出一行 `"title": "Response Xyz…"` 噪声，连 `$ref` 都不产出。守卫见同文件的 `test_no_useless_any_annotations_on_routes`。
3. ✅ `-> Response` / `-> StreamingResponse` 注解安全（FastAPI 对已是 Response 的返回值短路，不校验）。
4. ❌ 静态核对文档缺口**不要**读 `app.routes`：本 FastAPI 版本把 `include_router()` 的结果懒挂载成 `_IncludedRouter`，`route.path` 也不带 prefix，按路由属性检查会**假通过**（曾把 166 个缺口误报成 5 个）。要么静态扫 AST，要么读 `app.openapi()["paths"]`。

文档层面另有一道 `tests/test_openapi_doc_completeness.py`，直接对**生成后的文档**断言：操作数下限 340（当前实测 284 paths / 355 operations，router 掉线会立刻跌破）、每个操作至少有 `summary` 或 `description`、每个响应码都带 `description`。AST 检查看不见"整条路由消失了"，这一层才看得见。

***

## 8. 命令

### 8.1 项目根（后端 / 统一启动）

```bash
uv sync                                              # 依赖安装
pwsh -File dev.ps1                                   # 推荐：并发 FastAPI(8000) + Nuxt(3000)
./dev.ps1 -NoFrontend ; ./dev.ps1 -NoBackend         # 仅后端 / 仅前端
./stop.ps1                                           # 清理子进程
uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
uv run python -m backend.migrations status|upgrade|revision -m "msg" --autogenerate
uv run python -m backend.scripts.mock_data           # 示例数据
uv run python -m backend.scripts.auto_oobe           # 静默 OOBE（需 ADMIN_PASSWORD）
uv run pytest                                        # 本机 2026-10-29 全量：2363 passed + 23 skipped + 2 xfailed + 2 xpassed、0 failed，覆盖率 72.83%（生产机同口径见 §8 的第四十三场；§8.4 那两条顺序性假失败只在生产机全量里挂，本机 0 failed）
uv run ruff check backend tests ; uv run ruff format --check backend tests
PYTHONPATH=. python backend/scripts/gen_api_coverage.py --write   # 重算 frontend/docs/API_COVERAGE.md 的覆盖度汇总表
```

**缺口清单只认扫描器**：`frontend/docs/API_COVERAGE.md` 的汇总表由
`backend/scripts/gen_api_coverage.py` 生成在 `<!-- COVERAGE-AUTO -->` 区块里，漂移由
`tests/test_api_coverage_scanner.py` 挡（改了接口或接线没重算即 CI 红，修复动作是跑 `--write`）。
2026-09-26 那版手工快照之后按族手累过三轮增量，模块行与合计行长期对不上（`messages` 行写 0 ✅
而明细写「已接入 5 条」），照着它排下一轮接线会去接一条早就接完的口子。扫描器的两处盲区写在
该文档开头：①看不见"封装存在但没人点"；②看不见变量拼出来的 URL
（`` `${apiBase}/media/avatar` `` 会落进 ❌，`avatar_proxy` 即是）。

**覆盖率读数的口径（必读）**：`addopts` 里带 `--cov-append`，所以 `.coverage` 会跨多次运行**按行号合并**。一旦中间改过代码（加测试、反证实验回退、ruff format 移行），陈旧行号的数据就会把现在没跑到的行标成"已覆盖"，读数是**虚高且不可复现**的。要一个可比数字必须先删：`rm -f .coverage && uv run pytest`。按此口径实测两轮独立全量得到**完全相同**的 14039 stmts / 4450 missing / **68.30%**（第二轮直接追加在第一轮数据上、missing 一条没少，证明单轮已跑满），该值才是 CI 看到的数（第三十三场同口径复测：14044 stmts / 4448 missing / 68.33%；第三十四场收藏 PATCH 序列化收口后：14045 stmts / 4447 missing / 68.34%；第三十五场收藏重复行 500 收口后：14046 stmts / 4440 missing / 68.39%；第三十六场投票查重收口：同 14046 / 4440 / 68.39%，用例 +2；第三十七场评论可读性闸门收口：14081 stmts / 4446 missing / 68.43%，用例 +7；第三十八场 robots 缓存键 + noindex 闸门收口：**68.55%** / 1302 passed，本轮只采到总百分比，stmts 待复测；第三十九场收藏 / 评论反应 / 私信三族落地收口：14390 stmts / 4522 missing / **68.58%** / 1345 passed，同口径复算补上 stmts；第四十场站点设置数值区间闸门 + `/api/config` 单组容错收口：14606 stmts / 4510 missing / **69.12%** / 1476 passed；第四十一场密码重置反馈 + 站点设置页/用户中心收口（批次 #69–#72）：14492 stmts / 4388 missing / **69.72%** / 1509 passed，生产机 2026-10-23 同口径复测；第四十二场 SEO/GEO 批次（P0-1…P2-4 + `indexnow_key` 掩码）收口后：14593 stmts / 4400 missing / **69.85%** / 1523 passed（生产机 2026-10-26，`rm -f .coverage` 起算，40 分钟全量，含 §8.4 两条顺序性假失败）。历史文档里出现过的 87%–88% 系列是未清 `.coverage` 的合并产物，勿再引用。

**CI 覆盖面 ≠ 全部门禁**：`.github/workflows/ci.yml` 后端只有 ruff check + ruff format --check + pytest，前端只有 `nuxi prepare` + typecheck + lint。**`pnpm test`（vitest）与 `pnpm build` 不在 CI 里**，只在生产机串行跑得到。表现是"CI 全绿的提交上 vitest 是红的"（产物字符串断言 `5000`→`5e3` 那类、以及只有 build 期才暴露的 SSR 问题）——推完 CI 绿不等于收口，这两步补跑才算。

### 8.2 frontend/ 目录

```bash
cd frontend
pnpm install
pnpm dev                      # Nuxt 3000
pnpm build ; pnpm preview --host --port 3000
pnpm lint                     # 0 error；warnings == 7（vue/no-v-html 固定基线；2026-09 移除称号图标 v-html 分支后由 8 降为 7）
pnpm typecheck                # 0 TS error
pnpm test                     # Vitest 单测（tests/unit/ 108 个 spec；1762 用例，2026-10-29 本机全绿）
                              # 生产机 lint/typecheck/test/build **必须串行**：3.9 GB 内存下并行会让 eslint
                              # 被 OOM 杀掉（exit 137），而 `pnpm lint; echo $?` 仍回 0——只信 "✖ N problems" 那行
```

### 8.4 已知测试噪声（不是回归，别照着它改代码）

`tests/test_coverage_main_and_middleware.py` 在全量跑里稳定挂 2 条
（`TestMainTopRoutes::test_health_route`、
`TestPerformanceMiddleware::test_slow_request_triggers_should_record_with_except_fallback`），
单独跑这个文件时挂的却是**另一条**，报错都是 `attached to a different loop` 一类的事件循环串台。
判定口径：挂的集合随运行范围变化 ⇒ 是用例间共享 fixture 的隔离问题，与被测代码无关；
确认方法是单点跑那一条用例（`uv run pytest tests/...py::TestMainTopRoutes::test_health_route`），单点绿即噪声。
**同一族的噪声不止这一个文件**：2026-10-16 全量跑（1332 passed / 2 failed）另挂
`tests/test_market_index.py::test_plugin_market_route_registered`，报错在
`TestClient(app).__enter__` 的 lifespan 启动处（不是断言处），单点跑绿——判据同样是"前面用例把
连接/事件循环弄脏了"。看到新的挂点先按这条流程判（单点跑），别去改被测代码。
修它要重排相关文件的 fixture 作用域，是独立工程，勿与功能改动混做。

**本机（Windows）全量基线会漂移，登记噪声要实测两轮**：2026-10-27 连跑两轮，第一轮挂
`tests/test_core_rate_limit_contract.py` 两条（该文件单点跑 10 passed、`-k` 子集跑 20 passed），
第二轮 **1581 passed / 0 failed**。所以"稳定挂 2 条"是生产机口径，不是本机的：本机门禁判据只能是
"挂的集合是否落在已单点验证过的噪声名单里"，出现新挂点先单点跑绿再登记，未验证前按回归对待。

**这两条噪声会让全量 pytest 的退出码变成 1**，所以门禁脚本不能把 `pytest EXIT=1` 直接当回归：判据是
`short test summary info` 里挂的集合是否**恰好**这两条（生产机 2026-10-26 全量实测 `2 failed, 1523 passed`，
`FAILED` 行只有 `test_coverage_main_and_middleware.py` 的两个用例）。另：生产机上 `uv run pytest` 会
`Failed to spawn: pytest`（uv 环境里没有该入口），必须用 `.venv/bin/python -m pytest -q`；覆盖率同口径
用 `.venv/bin/python -m coverage report --fail-under=45`。

### 8.3 部署

```bash
docker compose up -d                          # Docker
sudo bash deploy/linux-install.sh             # Linux 原生
powershell -ExecutionPolicy Bypass -File deploy/windows-start.ps1  # Windows
```

***

## 9. 验证清单

### 9.1 后端

```bash
uv run python -c "from backend.main import app"    # 模块导入无错
uv run python -m backend.migrations status         # 'head' == 当前版本
uv run pytest                                      # 覆盖率 ≥ fail_under=45%（读数口径见 §8：先 rm -f .coverage）
curl http://127.0.0.1:8000/health                  # {"status":"healthy"}
```

- **派生资源必须复用文章本体的可读性判据**：文章的 status / 定时发布 / 访问密码三重判定原先只内联在文章详情端点里，评论的三张读口 + 两张写口各自 `select(Post)` 便放行，表现是"正文已按密码藏好，同一篇文章的评论（常直接引用正文）却匿名全公开"，草稿 id 与 comment_id 还能枚举。判据现在抽在 `backend/services/post_access.py`（`post_is_publicly_visible` + `post_content_unlocked`），评论口一律走它（`CommentService.get_readable_post` / blog.py 的列表口）——**新增任何以 post_id/slug 定位的读或写口，不要再自己查 Post**，那道判据漏一处即成泄漏。不可见时列表口回空、详情型口回 404（不回 403：承认存在即可枚举）。回归 `tests/test_comment_post_access_gate.py`；反证要点：把 `post_is_publicly_visible` 的 status 判据与密码判据**分两轮**变异，混在同一轮里会互相遮蔽（密码变异会让所有未加密文章被判成锁上，草稿泄漏那条反而假绿）。
- **「标记」与「裁决」是两张表的两件事，别把历史与待办混在一个字段里。** 评论举报（批次 #234）拆成 `comment_reports` 明细（谁、什么理由、谁在何时裁决）与 `comments.reported_at` 标记（只要还剩一条 open 举报就非空）。后台评论列表的「仅看被举报」查的是**单表单列标记**（不用 EXISTS 子查询），裁决口每改一条举报都要在同一事务里重数 open 数——`await db.flush()` 必须排在计数之前，否则 autoflush 时序一歪，`reported_at` 就永远清不掉（表现为"举报都处理完了，列表里还挂着红点"）。重复举报回 200 + `duplicate=true` 而不是 409：前端据此说"你已经举报过了"，不必为冲突单写分支。举报**不改变公开面**（不改可见性、不动缓存），真正下架仍走 `PATCH /api/admin/comments/{id}` 的 status。可读性闸门与表情反应同源（`services/comment_access.readable_comment_or_404`）——写口不带闸门等于让匿名按 comment_id 确认"草稿文章的评论存在"。四段守卫：`tests/test_comment_reports.py`（写口/去重/自举报/裁决清标记/`reported_only` 列表）与 `frontend/tests/unit/commentReportWiring.spec.ts`（原因枚举三处相等 + 每条通道都有消费方 + 四语文案齐全）。
- **文章 `visibility="private"` 有两种判据形态，缺一个方向就漏一半**：对象口用 `post_is_publicly_visible`（作者与 staff 短路），集合口用 `private_posts_excluded()` 这条能进 SQL 的谓词（`COALESCE(visibility,'public') != 'private'`，身份盲）——SQL 带不动"作者本人可见"这层语义，所以集合口一律按最保守的匿名视角排除，登录作者找回私密稿走作者范围的 `GET /blog/users/me/posts`（本就按 `author_id` 圈定、含草稿）与 staff 的 `GET /blog/posts?status=all`。每条以 `Post.status == "published"` 圈定"对外存在"的查询都必须叠它，包括**`cache_warmer._warmup_categories` 这类预热口**：预热写的是匿名请求会直接回放的键位，读侧加了排除而预热没加，访客看到的分类计数就在整个 TTL 内稳定地多算一篇。状态与可见性是两条正交的轴（「已发布 + 私密」是合法组合），后台列表因此分两个徽标显示，列表项必须带出 `visibility`。回归 `tests/test_post_visibility_private.py`（预热那条的反证要点：期望值必须是独立算出来的绝对数，不能拿读侧接口返回值当期望——那条口读的就是同一个缓存键，怎么变异都不会红）。
- **多语言 dict 字段有两种出口形态，后台只准接其中一种。** 文章的 `title/content/excerpt/subtitle/meta_*` 在库里是 `{zh,en,ja,zh_Hant}` dict：公开读口（详情 / 列表项 / 相似 / 热榜 / RSS）与**写口响应体**都按请求语言解析成**字符串**（`get_i18n_value`，缺失语言回落 zh），只有 staff 的 `GET /blog/posts/{id}/edit`（`PostEditResponse`）回完整 dict。所以后台编辑器必须走 `/edit` 取数——接公开口时表单把单语言字符串当 zh 重组 dict，一次"改个分类"就把其余三种语言整批抹掉；反过来把 `/edit` 改成按语言解析也是事故（dict 字段收到字符串要么 500 要么静默只留一语）。可选 i18n 字段的清空口径：PUT 是 `exclude_unset` 增量语义，**省略键 = 不动它**，所以"删掉副标题"只有发显式 `null` 才落得了库。五个可清空字段（`subtitle` / `excerpt` / `meta_title` / `meta_description` / `meta_keywords`）在 `buildPayload` 里**每一个都必须写成 `toI18nPayload(form.x) ?? null`**——`toI18nPayload` 对全空 dict 返回 `undefined`，键整个不在请求体里，表现是"作者删掉摘要、后台提示保存成功、再打开还是旧值，RSS 与 og:description 继续播旧摘要"，而接口层一个错都不报。连带口径：`types/api.ts` 的读写两侧与**消费方 props**（`PostCard.vue` 的 `excerpt` 是第一条会红的地方）都要允许 `| null`；typecheck 因此报错时**只能往宽处修**，把消费方类型收窄成 `undefined` 等于把"清空"这个操作重新变成类型层面写不出来的东西。读侧同理：清空后库里是 JSON null 而不是 SQL NULL，`normalizeI18nDict` 必须接住 null，否则下次编辑 v-model 崩。**这四个字段的真实消费面各不相同，探针必须逐一对上形态，否则会同时得到"假 FAIL"和"假 PASS"**：`<title>` 用 meta_title、`og:description` 用 meta_description、RSS 的 `<description>` 用 excerpt（空则回落正文前 200 字），而 `meta_keywords` 只进 **JSON-LD `BlogPosting.keywords`**（`pages/posts/[slug].vue::seoKeywords` = meta_keywords 拆分 + 标签名去重）——前台**没有** `<meta name="keywords">`（Google 早已忽略该标签，`useSeo` 也就不产出）：按那条标签断言拿到的是恒空字符串，写侧接通了也会判成"没接通"，清空侧又会判成"清干净了"。回归 `tests/test_post_subtitle_roundtrip.py`、`tests/test_post_i18n_clear_roundtrip.py`、`frontend/tests/unit/postClearableI18nFields.spec.ts`（两种出口形态与"省略键真的不动它"都钉在里面，后一条是 `?? null` 存在的理由，不要当冗余断言删掉）。
- **缓存里只存 id 的读口，判据必须落在"回源那一次 SELECT"上**。热榜 / 首页推荐 / 相似文章把排序结果缓存成 **id 名单**（ORM 实例进不了 Redis，见 `RecommendationService._rebuild_posts_by_ids` 的说明），命中时用名单回源。名单的新鲜度和文章的实时可见性是两件事：`invalidate_pattern` 只清当前进程的 L1 + Redis，生产跑 `--workers 2`，另一个 worker 的 L1 收不到广播，所以"名单比文章状态旧"是设计内的常态而不是 bug。生产实测症状：把一篇文章从 private 翻成 public 后，同一个 `hotv2:{limit}:{days}` 键位仍返回它，换一个从未用过的 `days` 键位立刻缺席。**只在冷路径加过滤等于没加**——收敛点是回源，且命中路径不回写名单（名单活到 TTL 结束）。集合判据单源是 `services/post_access.py::publicly_listable_posts()`（status + 私密档 + `published_at <= now()` 三条一起给；第三条修的是"推荐位点进去 404"：`status=published` 是定时发布落库时的写法，详情口早就判 404，漏判的只有派生集合口）。**新增按 id 集合回源的口一律带上它**；staff 后台的批量口（如 `POST /posts/batch-status`）不在此列，它本来就要拿到草稿。回归 `tests/test_recommendation_visibility_rebuild.py`（暖缓存 → 只改库不清缓存 → 断言响应已无它而名单里还在，`test_hot_endpoint_never_links_to_a_404_detail` 逐个回访真实状态码）。
- **没有唯一约束就没有"单行"的保证**：按 `(user_id, post_id)` 这类业务键取行时，`scalar_one_or_none()` 在重复行存在时抛 `MultipleResultsFound`（未捕获 ⇒ 500），而"先 SELECT 再 INSERT"的查重挡得住顺序请求、挡不住并发与重试。要么给表加唯一索引，要么按集合处理（`select(...).order_by(...)` 取全部行 + 显式锚点，删除/更新覆盖全部行）——口径见 `api/favorite.py::_post_favorites`。
- 新建/更新接口：`db.flush()` 之后服务端生成的列（`created_at` / `updated_at` 这类 onupdate）处于过期状态，直接序列化会在事件循环里触发隐式 IO（异步下表现为 `MissingGreenlet`）。必须回读一次——`await db.refresh(entity)` 与"一条带 `selectinload` 的 SELECT"**二选一**；`refresh` 本身就会连关系一起重载，两条都做等于白发一次往返。
- **响应缓存的载荷里不得放会话绑定的 ORM 实例。** 缓存跨请求复用，而实例属于"第一次那次请求"的会话：那次请求结束、会话 commit/close 后 `expire_on_commit` 会把它的属性全部标成过期，下一个命中缓存的请求再读任何一个字段就是 `DetachedInstanceError` → HTTP 500（实测表现：作者主页第一次正常，TTL 内刷新即报错）。要么在写缓存前 `make_transient` 摘成只读快照（见 `user_service._detach_for_cache`），要么直接存 `model_dump(mode="json")`（本仓多数接口已是后者）。同一条规则的另一面：**给后台写路径取实体的 getter 一律不能带缓存**（`get_user_by_id` 曾带 300s 缓存，六个调用点全是写操作——读属性 500、写属性落在脱离会话的对象上，接口回 200 而库里没变）。守卫见 `tests/test_author_archive_filter.py::TestCachedProfilePayloadIsReusable`。
- **用户隐私开关只有两种语义，新增读取面必须选边并过同一道闸门。** `public_profile=False`＝这个主页对外**不存在**：主文档与它的全部子资源（`/{id}/posts`、`/{id}/comments`、`/{id}/stats`、`/username/{u}/preferences`）一律 404，判定唯一入口是 `api/users.py::_profile_is_hidden`（403/401 等于承认账号存在＝账号枚举面；把整组开关摊给匿名方也是）。`show_posts / show_comments / show_stats=False`＝**隐藏即空**：200 + 空页/全零计数，别改成 404，那是"这个人有内容但不给看"的另一回事。本人和 staff 越过两层；无偏好行按可见处理。可见性判定结果会被缓存（作者列表键 `posts:*a<username>` + Nitro swr 页面），所以写开关处必须同时 `_invalidate_author_post_caches` 与 `purge_frontend_page_cache`（见 `user_service.update_preferences`）。回归 `tests/test_author_archive_filter.py::TestHiddenProfileSubResources`。
- **隐私开关的判据不得来自响应缓存。** 线上实测（批次 #227）：作者关掉 `show_social_links` 后 SSR 页面已经藏了链接、`/username/{u}/preferences` 也回 False，但同一时刻匿名 `GET /api/users/username/{u}` 仍原样回显 website 与 GitHub。原因是 `get_user_profile` 把 `UserPreference` 实例连同用户行一起放进了 `user_profile:{id}` 载荷，而**含 ORM 实例的载荷进不了 Redis**（`cache_v2.set` 对不支持的类型告警并跳过），于是它只活在第一个服务过它的 worker 的进程内 L1；写口的 `invalidate_user_cache` 同样只清"执行它的那个进程"。生产按 `--workers N` 跑 ⇒ 其余 worker 带着旧开关服务到整个 300s TTL，最重的是 `public_profile` 关掉后主页对外仍存活五分钟。口径：`user_service.get_user_profile` 的缓存载荷只放展示字段（user / title / 计数），`preferences` 一律每次现查（`{**raw, "preferences": …}` 不可就地写回缓存字典——那会把会话绑定实例塞进跨请求载荷，重新引入 `DetachedInstanceError`）。同一条判断适用于**任何"读侧判据 + 缓存载荷"的组合**：判据要跨进程立刻生效，就不能存在缓存里；展示字段可以慢。回归 `tests/test_privacy_switches_are_not_cached.py`（三条闸门各钉一次 + 一条"缓存确实热了"的前置，防止恒真假绿）与 `tests/test_author_archive_filter.py::TestCachedProfilePayloadIsReusable`（载荷键集不得含 preferences）。
- **匿名集合口只准走 `services/post_access.py::publicly_listable_posts()`，不得再手写 `Post.status == "published", private_posts_excluded()` 那一对。** `status == "published"` 是**定时发布落库时的写法**（status 先转 published、`published_at` 给未来时间），它不等于"已经公开"：只圈 status 的口会在到点前就发卡片，而详情端点判 404——表现是"列表里有、点进去 404"，落在 sitemap / RSS 上更糟（爬虫按 404 收一次 URL）。同一谓词还管分类/作者的**计数**（`func.count(Post.id).filter(...)`、归档统计），漏掉的那一处会让计数比页面多。唯一清单由 `tests/test_future_scheduled_collection_surfaces.py` 静态钉住，新增手写点直接红；里面那几处例外各有正当理由（上下篇比的是 `published_key` 排序键、`favorite.py` 用 Python 侧 naive `now` 以避开方言差异），不要因为"看起来能统一"就顺手改掉。同文件的反向闸门钉住"收紧只针对匿名视角"：后台 `?status=all` 仍必须列出定时稿。**缓存层有两套，别按其中一套推另一套**：`core/cache.py::CacheService` 是**二选一**后端（生产启 Redis 时没有进程内层，`invalidate_cache` 跨 worker 立即生效）；`services/cache_service.py`（推荐/热榜/相似那一族）带进程内 L1，`invalidate_pattern` 不广播，另一 worker 的 L1 只能等 TTL——所以写线上探针时，"到点后应立刻在场"这类断言必须落在没被暖过的键位上（用本轮随机 slug 派生 `page_size` / `limit`），不能指望重试。回归 `tests/test_future_scheduled_collection_surfaces.py`、`tests/test_recommendation_visibility_rebuild.py`。
- **响应缓存的键必须带齐查询侧真正使用的判别位。** 凡是进了 SQL `WHERE` 的请求参数，就必须进缓存键（或让该请求跳过缓存）：`post_type` 曾"过滤但不进键"，匿名访客就能用 `?post_type=<不存在的值>` 把空列表写进首页/列表共用的键位，在 TTL 内对全站投毒。同理，**改变内容可见性的写操作（加/去访问密码、转草稿）必须显式清详情缓存**——`GET /blog/posts/{slug}` 的缓存命中在密码判定之前，不清键等于密码门在 TTL 内形同虚设（`invalidate_post_detail_cache` 的说明即此口径；`post:{slug}:{lang}` 不在 `posts` 前缀下，`invalidate_cache("posts")` 命中不了它）。同一资源族的权限档位也不得有孤立缺口（媒体库详情曾只要求登录，而列表/改/删要求 staff）。回归 `tests/test_read_surface_discriminators.py`。
- **读口的派生字段只准覆写响应对象，并且要按"展示字段"的时效对待。** 相册照片的 `thumbnail_url` 不是 `photos` 表的列：它是读取时按 `Media.file == Photo.url` 从媒体库 `sizes` 现算的缩略档（口径同相册封面的 `_fallback_cover_map`）。两条红线：① **绝不 `setattr` 到 ORM 实例**——非映射属性会留在 identity map 里，autoflush 与 `apply_partial_update` 都会把它当成库里的值（`tests/test_partial_update_guard.py` 就是拦这个），正确写法是 `response.model_copy(update={...})`；② 派生值一旦进了响应缓存就随 TTL 一起变旧，这是**可接受的滞后**（媒体库重算缩略档不影响 `url` 这条真值），但**判据字段永远不许这样缓存**（见上面「隐私开关的判据不得来自响应缓存」）。对齐另需两点：整页一次 `WHERE file IN (...)`，不要循环查库；`media.file` 无唯一约束，重复登记时按 `id` 升序取第一条，否则页面显示哪一档取决于数据库返回顺序。消费方面：网格用 `thumb || url`、灯箱/封面/文件名一律用 `url`——`frontend/pages/gallery.vue` 的 `data-original` 只有配上 Viewer 构造参数 `url: 'data-original'` 才会被读到（viewerjs 的 `DEFAULTS.url` 是 `'src'`），漏掉那一条等于把 150px 小图放大到全屏。回归 `tests/test_gallery_photo_thumbnails.py`（投影两面 + 回落链 + 脏 `sizes` 形状 + 单查询 + 缓存滞后 + ORM 实例不脏）与 `frontend/tests/unit/galleryPhotoThumbnails.spec.ts`。
- **归属/可见性的边界条件必须写在"决定返回哪一行"的那一层。** 私信会话列表曾把 `between_us` 只放进"算每个对端最近时间"的子查询，外层用时间等值 join 取正文时没有再过滤，于是"朋友在同一秒还给陌生人发过消息"会命中我的会话行——第三方正文泄漏 + 同一对端重复成行。两条通用口径：**时间戳等值 join 不算可靠去重**（SQLite `created_at` 只到秒、PG 同事务时间戳相同，取"最新一条"要用 `max(id)` 或带 `id` 的 tiebreaker）；**分组/聚合的 WHERE 不会自动传导到下游 join**，跨用户资源族的每个出口都得重过一遍归属谓词（收藏的 `total` 同型：计数用未筛选的总数算 `total_pages`，按文件夹过滤时就宣称还有下一页、拉过去是空的）。**对象级也要守同一条**：按 id 操作他人资源一律 404，不要 403——主键连续自增时 403 是在替攻击者数"这条存在"（`PUT /messages/{id}/read` 曾回 403，通知/收藏同族本就 404）。回归 `tests/test_private_surface_boundaries.py`。
- **WebSocket 与 query string 是两条独立的红线。** handshake 只能 `accept()` 一次（内层 manager 再 accept 会破坏 ASGI 协议）；WS 鉴权必须走与 HTTP 同轨的 `core/auth.py::validate_token`（`type=="access"` + 存在 + `is_active` + 未 `is_banned`），不能只看 token 能否解码——refresh token 与封禁账号都能凭旧实现拿到推送通道。顺带：`async def` 的注册调用漏 `await` 不会报错，只会静默不登记。用户正文/隐私字段一律走请求体，不走 query string（nginx access log 会明文落盘，且长正文撞 414）。
- **运行期可变的注册表必须持久化，公开渲染口不得接受调用方自备的上下文。** 短代码注册表是模块级内存 dict，而生产用 `--workers 4` 跑：只写进"处理这次请求的那个 worker"的注册表，下一次列表请求就可能看不到它、进程重启即全丢。口径：写入侧同时落 SiteConfig KV（`shortcode_templates`），启动侧（`bootstrap_extensions`）与读取侧（admin 列表）各重放一次，且重放必须让**插件自带的同名 tag 优先**——运营期数据覆盖代码，等于让"插件升级换了 `[tag]` 实现却不生效"无从排查。同族另三条红线：handler 必须遵循引擎调用约定 `fn(**attrs, content=, _content=, ctx=)`，签名不匹配的表现为正文里冒出 `<!-- shortcode-error -->` 注释而不是接口报错；`POST /api/shortcodes/render` 是**无鉴权公开口**，绝不能收 `context`（插件 handler 靠 ctx 读文章/用户，访客自备 ctx 就是越权渲染），唯一能带 ctx 的入口是管理员预览；纯 CPU + 无鉴权的公开口必须有专属限流规则，且**必须排在 `"/api"` catch-all 之前**（`_get_rule_for_path` 按插入顺序 `startswith` 首命中即返回，写在 catch-all 后面就是一条永远不会命中的死规则）。对不可信文本做递归展开必须有深度闸门；改注册表后必须走 `_invalidate_rendered_content`（`post:` / `posts` / `archive` + 前端页面缓存），漏清的表现是"已删除的短代码仍在旧正文里渲染"。回归 `tests/test_shortcode_registry_api.py`。
- **函数体里的 `import` 只能是已声明的依赖。** `import numpy as np` 曾藏在监控聚合函数里，`pyproject.toml` 从未声明 numpy：窗口内一旦有访问日志就 `ModuleNotFoundError` → 后台性能页 500（空窗口提前 return，所以既有套件从未暴露）。同类面还有一条口径：**分位数/统计的分母必须是"窗口内全部请求数"**，只按慢请求子集算 `error_rate` 会把快速失败的 4xx 放大成虚高错误率；扫描原始日志也必须带 `order_by(desc) + limit` 上限，不能全表进内存。
- JSON 多语言列（`title` / `content` / `excerpt` / `meta_*`）写入 Python `None` 时落库是 **JSON null 而不是 SQL NULL**（SQLAlchemy JSON 默认 `none_as_null=False`），所以 `col.is_(None)` 在 SQL 里筛不出"没有内容"的行；判定口径见 `backend/api/admin.py::_missing_i18n_json`。
- **"写口收键、读口不回吐"是一种缺陷，不是未完成**。`Post.encryption_hint` 曾同时满足三种"看起来在做"的状态：列在模型上、`PostCreate`/`PostUpdate` 都收、前台闸门页也在读 `detail.encryption_hint`，但详情响应模型不带这个键、编辑器表单从不发送——表现是运营者填了提示、锁屏上永远只有默认文案。同一形状的另一端是整族僵尸端点（2026-10-28 退役的调色板一族：写进去的 `theme_palette` 没有任何读取方）。口径：**一个新字段落地必须同批完成「写口 → 存储 → 响应模型 → 消费方」四段**，缺任何一段要么补齐要么整族删除；守卫分别是 `tests/test_post_encryption_hint.py`（四段往返）与 `tests/test_retired_palette_family_is_gone.py`（负向清点）。
- **能力开关的"清单"不是实现，OOBE 装完即落库的键必须有人在判**。2026-10-31 退役的一对幽灵开关（`enable_pagefind_search` 站内搜索、`enable_music_player` 背景音乐，外加硬写 `"false"` 种进 SiteConfig 的 `enable_pio` 看板娘）走完了「向导开关 → 请求字段 → `.env` + SiteConfig → `/api/config` 投影」四段，唯独没有第五段：**全仓没有一处读它**。用户关掉与打开看到同一个站点，而文档与后台界面都在声称这项能力存在。同批删掉 `core/oobe_constants.py` 的 `FEATURE_FLAGS` / `FEATURE_FLAG_DEFAULTS`（十三个键、零引用）——一张没人消费的清单挡不住任何漂移，只会让下一个照着它接线的人去接一条后端根本不存在的口子。口径：**能力开关的唯一清单是 `settings_groups._default_features()`**（逐键由 `tests/test_settings_group_consumers.py` 钉消费点），新增开关必须与它的执行点同批落地；OOBE 向导只保留四把真有实现的（评论 / 注册 / RSS / Bing 壁纸，`FEATURE_FLAG_DB_KEY_MAP` 因 RSS 改名映射仍在用而保留）。守卫 `tests/test_retired_oobe_ghost_flags_are_gone.py` 两侧都钉：幽灵不得回潮（后端六文件 + OpenAPI + 前端的驼峰与四语 key），活路径不得被一起删掉（四把开关的三段往返 + 壁纸开关在登录/注册页的真实闸门）。
- **比「值有、判据无」更坏的一档是「假装保存」：写口声明的键如果不在转译表里，接口回 200 而库里一行不增**。2026-10-31 退役的第三方评论配置族（`comment_system_type` + twikoo / waline / artalk / giscus / disqus 各自的参数键，共 26 个）三段全断：`SiteConfigUpdate` 收下它们，但 `PUT /api/config` 的 `config_map` 从不转译，处理器 `if not key: continue` 静默丢弃；`/api/config` 又用 `get_str("COMMENT_TWIKOO_ENV_ID")` 把默认值投影给访客（那是匿名可读 + 缓存的公开口）；而 `frontend/` 里没有任何 provider 渲染器，翻那个开关评论区渲染的仍是站内组件。判定口径：新增一个配置键必须同时进「请求模型 → 写口转译表（或分组 PATCH）→ 投影 → 真实消费点」四处，缺任何一处要么补齐要么整族删除；只补前两处 = 对管理员撒谎，只补第三处 = 对访客撒谎。本站评论的单源是 `settings_groups._default_comments()`（开关 `enable`，执行点 `CommentService.create_comment` 的 COMMENTS_DISABLED 闸门）+ `/api/posts/{id}/comments` 写口 + `SiteConfigResponse.enable_comments` 这条由分组投影来的镜像（镜像不是幽灵）。守卫 `tests/test_retired_third_party_comment_config_is_gone.py` 两侧都钉：假配置不得回潮（模型字段 + 后端源码 + ENV 名 + OpenAPI + 前端源码全仓扫描），活评论系统不得被一起删掉（分组键集合相等 + config_map 四条真落库的旧键往返 + 评论接口族仍在文档里）。
  「旧清单里的名字」不等于「那个功能不存在」：友链页 / 相册页 / 公告条本身是活的（各自有管理模块与公开口），被删的只是三个凭空出现的开关名——要把它们做成可关的能力，做法照捐助页批次 #83/#210（features 组加键 + 公开面加强制点），不是照旧清单补一条空口。
- **「存得进、没人读」的整族死配置比单键幽灵更难发现：它在四个地方各自"看起来完整"，只有第五段（渲染器）不存在。** 2026-10-31 退役的五族扁平键（`music_*` 11 / `wallpaper_*` 10 / `sidebar_show_*`+`sidebar_widget_order` 11 / `sakura_*` 7 / `pio_spine_*` 7，共 46 键）同时具备「OOBE 默认值 + 两个模型字段 + `config_map` 转译 + `/api/config` 投影」，前四段全都成立，所以按"接线是否完整"扫永远扫不出问题；`frontend/` 全量源码里这些键零命中，也没有 APlayer / MetingJS / 樱花 canvas / Spine 运行时的一行代码，后台设置口 `/api/settings` 更没有这五组（sidebar 分组早已删：侧边栏显隐归主题 Customizer mods，导航位置归 `navigation.location`）——运营者找不到开关，访客却在 SSR 页面里读到"本站有音乐播放器"。判定口径与上一条同源但方向相反：**四段齐全 + 第五段（真实消费点）为零 = 整族删；只要第五段存在一个渲染器就属于活功能**，删前要逐族确认。同名前缀里藏着活功能，不能顺手删：`wallpaper_*` 死的是旧 Banner 体系，`enable_bing_wallpaper` + `site_settings.bing_wallpaper_enabled` + `/api/bing/wallpaper` + 公开 `/wallpapers` 是另一套；首页轮播是 `hero_slides` 表 + `/api/hero/*`，从来不在扁平配置里；`sidebar` 这个词还同时是导航菜单的一个 `location` 取值。守卫 `tests/test_retired_flat_config_families_are_gone.py`（模型字段 / ENV 名 / `config_map` / `/config/full` 分组声明 / 前端运行时名 / OpenAPI 六面清点 + 三条活路径 + 一条**存量库行**用例：往 `site_configs` 种 `MUSIC_ENABLED` / `WALLPAPER_MODE` / `SIDEBAR` 后 `GET /api/config` 必须无视它们而不是重新投影出来——生产 PG 今天就躺着这类行，删键不删这条回读路径等于给下一任改回来留门）。
- **扁平站点配置的最后 59 个零消费方键退役：四段齐全不等于有实现，收尾要按「谁在判」清点。** 2026-10-31 批次 #112 把 `/api/config` 这一族收干净：`SiteConfigResponse` 147 → **88** 字段、`SiteConfigUpdate` 136 → **77**。两种缺陷各占一半——**「存得进、没人读」17 个**（`about_content`、`friends_page_*`+`friends_apply_html`、`dynamic_page_*`、`sponsor_page_*`+`sponsor_methods_json`+`sponsor_show_sponsors_list`、`site_start_date`：进 `config_map`、落库、原样投影给匿名访客，前台零渲染器）与**「假装保存」42 个**（`post_list_*`、`cover_*`、`license_*`、`bangumi_*`、`anime_*`、`page_*_enabled`、`mermaid_*`+`plantuml_server_url`、`image_opt_*`、`pagination_posts_per_page`、`category_bar_enabled`、`archive_fold_old_articles`、`post_show_last_modified`、`post_outdated_threshold_days`、`post_enable_share_poster`、`post_generate_og_images`：只被请求模型声明，`config_map` 从不转译）。**这一批的决策是"删"而不是"接"，判据是每族都已经有一个在工作的单源**：友链/动态/捐助页标题走 i18n（`t('friends.title')`、`t('activity.title')`）与 `donate.title`，捐助正文与名单走 `donate.methods/sponsors/description/show_sponsors_list`，关于页正文走 `basic.about_page_html`，留言板与捐助页的开关走 `features.enable_guestbook` 与 `donate.enable`（批次 #83/#210 的公开面收起），每页条数走 `reading.posts_per_page`，封面走 `lib/post-cover.ts` 的展示/分享两档，「更新于」按 `updated > published` 判定（按值不按开关）；`bangumi_*`/`anime_*` 连页面都不存在（`frontend/pages/` 没有 bangumi/anime，后端无对应 router），`mermaid_*`/`plantuml_server_url`/`image_opt_*`/`license_*`/`post_generate_og_images` 前端零实现。把扁平键"接通"的结果是同一件事出现两个配置源，运营者改一个、渲染读另一个。**退役的写面行为也因此从"静默"变成"明确"**：`strict_config.apply_strict_extra_forbid` 给配置模型统一 `extra="forbid"`，带退役键的 `POST /api/admin/settings` 现在回 422（退役前是 200 + 库里什么都不做）。守卫 `tests/test_retired_flat_config_keys_are_gone.py`：59 键在两个模型 / `core.py` 三个区域（OOBE 默认值、公开投影、`config_map`）/ ENV 名 / OpenAPI / 前后端源码六面零命中，另钉三种"删过头"与"空转"的反证——种 6 行存量 UPPERCASE 库数据后 `/api/config` 必须无视、三个区域必须还带着 `site_name` 这类活键、写口对活键（`footer_text`）仍能 200 落库并回读。
- **一篇文章只允许一个密码真相源。** 访问密码门单源是 `Post.password`（写口哈希落值，判据 `services/post_access.py::post_content_unlocked`，解锁后详情口直接返回明文 `Post.content`，提示走 `encryption_hint`）。2026-10-31 整族退役的是**第二套并行设计**：`encryption_enabled` + `encrypted_content` 密文 + salt/verifier/algorithm 四个写口字段 + 7 条端点（`/posts/{id}/decrypt`、`/admin/posts/{id}/encrypt` ×3、`/post_crypto/*` ×3）+ `core/crypto.py`——详情响应模型从不带密文，所以访客路径永远拿不到它，前端零调用，`verify_access` 铸的 `scope=post_access` JWT 也没有任何端点认。退役边界是**接口与写口，不是表结构**：5 个列、四处 `defer(Post.encrypted_content)` 读侧护栏、ZIP 导出/导入对密文的原样往返全部保留（历史备份里可能有密文，删表是另一项独立工程），删前用只读探针证明 `encryption_enabled=true` 与密文非空行数为 0。守卫 `tests/test_retired_post_crypto_family_is_gone.py`（除负向清点外，还钉住"活路径不得被一起删掉"那一侧）。
- **自定义内容类型（ACF）的四段里，读侧必须比写侧宽一档。** 定义 CRUD（`api/content_type.py`）→ 写口闸门（`content_type_service.resolve_post_type_and_meta`：未知类型 422、缺必填 422、类型不符归一化后仍不可解析就丢键）→ 详情响应带 `post_type` + `meta_fields`（`schemas/post.py` 与 `api/blog.py` 三处出口）→ 公开文章页 `visibleMetaFields` 消费。第四段不能按定义重校验：定义可以在有文章之后被改（删字段、改必填、换类型），历史 `meta_fields` 里必然留着定义之外的键——把写侧的严格搬到读侧，一次定义调整就会让一批详情页 500。口径是展示侧只渲染"定义里存在且值非空"的键，脏 `meta_fields`（非 dict / 非对象值）在后端就直接按"没有扩展字段"下发。另外三条：① **换类型整体清空并按新定义 default 预填**（`PostForm.onContentTypeChange`），把上一类型的值留在表单里等于把 `unknown_key` 提交进闸门后被静默丢弃；② `datetime` 存的是 `astimezone(UTC).isoformat()`，是**纯数据不是本地墙钟**（`_coerce_value` 的注释即此口径），展示侧只能做确定性字符串裁剪（`slice(0,16).replace('T',' ')` / `slice(0,10)`），用 `toLocaleString` 会在 SSR 与 hydrate 之间产出两种时间；③ 定义写口改变的是 SSR 页面上的字段卡片，所以必须连带 `purge_frontend_page_cache`，只清后端响应缓存等于让旧卡片在整个 swr 窗口内继续对外。守卫 `tests/test_content_types.py` + `frontend/tests/unit/contentTypeWiring.spec.ts`（按"后端 `FIELD_TYPES` ⇔ 前端 `CONTENT_FIELD_TYPES`"集合相等，并清点四段每段的存在）。
- **集合口的缺省筛选必须与消费方实际发什么参数对齐，"不传就只看标准类型"等于把一整族内容对外隐藏。** 文章列表口曾同时满足三件事：`?post_type=` 被写进 SQL、自定义类型文章的详情页/RSS/sitemap 全都正常、而**没有任何一个消费方传过这个参数**——于是缺省 `Post.post_type == "post"` 让自定义类型文章从列表、首页、作者主页、后台文章列表里集体消失，且运营者在界面上看不出"内容存在但被筛掉了"（详情口不看类型，所以只有直接拿到 slug 才看得见）。口径三条：① 读侧缺省一律是**最宽的、与详情页可见集合一致**的视角（不传 = 全部类型），收窄只能靠显式参数；② **响应缓存键的缺省段必须与查询侧同口径**（`f"pt{post_type or 'all'}"`）——缺省段写成某个具体类型，"全部类型"和"只看标准文章"就会共用同一个键位，谁先到谁被对方污染整个 TTL；③ 缺省放开后必须有**消费方侧的筛选入口**接住，否则列表页会被自定义类型淹没（前台 `/posts` 的类型下拉 + `?post_type=` 进 URL，后台文章列表同一族；两处的 `'all'` 哨兵都不能发给后端，`undefined` 才是"不筛"）。列表项的 `post_type` 因此是**必填且刻意不给默认值**的投影字段：带默认值时漏传的那一处不会报错，只会在界面上一直显示"标准文章"。作者归档分组与 sitemap-taxonomies 的 `lastmod` 也各有一条同族的硬过滤，放开读侧时必须同批检查（只改了列表口，作者页计数与 sitemap 的 `<lastmod>` 仍会漏掉自定义类型那几篇）。守卫 `tests/test_content_types.py::TestListVisibility`（缺省含每型 / 显式收窄 / 后台 `?status=all` / 缓存键互不相等且以 `ptall` 结尾 / 作者归档含每型 / 只有自定义类型的作者也进 sitemap 清单且 lastmod 取到那篇 / 垃圾类型参数不得把默认列表打空）与 `frontend/tests/unit/contentTypeWiring.spec.ts`（数 `Post.post_type ==` 出现次数==1、缓存缺省段字面量、前后台接线与 `'all'` 归一、四语文案齐全）。**静态守卫要数出现次数而不是判字面量**：`not.toContain('Post.post_type == "post"')` 挡不住 `== (post_type or "post")` 这种换个写法的回归。
- **跨字段的「类型 ↔ 地址」判据必须在两个写口都合并库里现值再判，且媒体源的第二半是 CSP。** 首页轮播的 `media_type`（image/video/youtube）+ `media_url` 是一对跨字段判据：schema 的 `model_validator` 只看得到 CREATE 的整份载荷，PUT 走 `exclude_unset`，只提交 `media_type` 或只换地址时另一半不在模型里——所以端点在 `apply_partial_update` 之前必须用 `update_data.get(k, slide.k)` 合并现值再跑 `validate_media_pair`，否则"创建时拦住、改一下就有"，落库后首页是一块空白 iframe 或一片黑。`video` 档必须是站内路径（CSP `media-src` 只有 `'self' blob: data:`，外链会被浏览器直接拦掉），`youtube` 档必须解析得出 11 位 ID（地址由前端 `lib/hero-media.ts` 固定拼 `youtube-nocookie.com/embed/<id>`，**绝不**把库里的原始串拼进 `iframe src`）。这条功能还多一处**两份声明**：iframe 能加载取决于 `frame-src`，它写在 `backend/core/security_middleware.py::CSP_FRAME_SRCS`（`/api` 响应）与 `deploy/nginx-site.conf` 的 HTML CSP（SSR 页面）**两处**，新增任何站外嵌入源必须同改，漏一处的表现是接口全绿、页面上那块永远是空白。守卫 `tests/test_hero_media_types.py`（ID 解析 / 搭配校验 / 两个写口 / 公开口字段 / CSP 两处）与 `frontend/tests/unit/heroMedia.spec.ts`。
- **写口的取值约束（`ge=` / `le=` / `Literal` / `max_length`）不得挂在响应模型继承的基类上。** `HeroSlideResponse` 原样继承 `HeroSlideBase` 的 `sort_order: ge=0` / `overlay_opacity: le=100` / `media_type: Literal[...]`，而公开口 `GET /api/hero/slides` 会把 `hero_slides` **已有的行**直接 `model_validate` 出去：库里一条 `sort_order=-1000`（直连 SQL / 导 ZIP / 探针写入）就让整条公开口回 500、首页横幅一起消失，而写口本身一条 422 都不少（2026-10-30 线上探针实测踩到）。口径：约束只挂 `HeroSlideCreate` / `HeroSlideUpdate`，响应模型把同一组字段**重新声明成裸类型**，读侧降级交给消费方（`safeHeroHref` / 兜底图）。守卫 `tests/test_hero_media_types.py::TestPublicReadPathToleratesStoredValues`（脏值下发 200 + 写口 422 一条不少 + "响应模型不得再带 metadata 约束"的反向清点）。新增带约束的列时，响应模型要同批放宽，否则 500 面又长回来。
- **文章级音视频（`Post.audio` / `video` / `video_url`）走的是 URL 策略的第四档：不是「必须绝对」，是「必须相对到站内」。** 2026-10-31 批次 #118 补齐这四段时，缺的是**创建口**（`api/blog.py` 手写的 `Post(...)` 字段清单没这三列，PUT 靠 `model_dump(exclude_unset)` 透传所以看起来"功能在做"）与**三个响应模型**（`PostResponse`/`PostEditResponse`/`PostLocalizedResponse` 不带键 ⇒ 前台播放器永远拿不到地址）。三条口径：① `audio`/`video` 只收站内路径（`schemas/_url_policy.py::require_internal_media_path`）——CSP `media-src` 只有 `'self' blob: data:`，外链写入口不拒，作者看到的就是「保存成功、前台一个播放器都没有」；`video_url` 必须解析得出 11 位 YouTube ID（`schemas/_youtube.py::extract_youtube_id`，与 hero 同一份，别再复制一遍），渲染侧**只用这个 ID** 拼 `youtube-nocookie.com/embed/<id>`，绝不把库里的原始串放进 `iframe src`（ZIP 导入与直连 SQL 都能塞任意地址＝把站外页面嵌进访客文章页）。② 约束只挂 `PostCreate`/`PostUpdate`，三个响应模型把同组字段重声明成裸 `str | None`（上一条的同一族）：库里躺着外链脏值时详情口必须仍回 200 并原样带出，由消费方决定不渲染。③ 密码未解锁时这三列由后端投影成 `null`（与 `content` 同源判定），所以前端播放器块**不需要**再判 `needPassword`——判据只写一处。④ **播放器按「读文章」的代价加载**（批次 #119）：`audio`/`video` 一律 `preload="metadata"` 且**不得** `autoplay`（一进页面就下整条媒体＝把首屏带宽花在一个可能根本不播的元素上，article 页的阅读上下文也不是媒体首页），`video` 必须带 `playsinline`（iOS Safari 没有它会弹成全屏播放器），YouTube `iframe` 保持 `loading="lazy"`。断言只作用于播放器块（`v-if="postAudioSrc || postVideoSrc || postEmbedSrc"` 到该 `</div>`），全站其它地方出现 `autoplay` 不算。守卫 `tests/test_post_media_fields.py`（写口往返/空串清空 vs 省略键不动/两档 422/脏值容错/闸门投影）与 `frontend/tests/unit/postMediaFieldsWired.spec.ts`（含反向断言：`:src` 不得直接吃 `post.value.audio`、不得出现 `srcdoc`、播放器块内不得有 `autoplay`）。
- **列表面只投影「有没有媒体」，不投影地址。** 批次 #118 接通详情页播放器后，读者在列表里看不出哪篇带音频（长文朗读稿因此失去"值得点进去"的提示），所以 `PostListItemLocalized` 新增 `has_audio` / `has_video` / `has_embed` 三位（批次 #120）。三条口径：① **只带存在性**——地址仍只有详情口回，列表载荷被更多缓存键位与更多消费方复用，带上路径等于把媒体文件名摊开（`postMediaBadgeWired.spec.ts` 有反向断言：组件不得读 `post.audio` / `post.video_url`）。② **三个键一律带默认值 `False`**——列表载荷是进响应缓存的，新增**必填**字段等于让 TTL 内的旧载荷 `model_validate` 整口 500（就是本文件上面「新增必填字段是反向同一条路」那条）。③ 值由 `services/post_access.py` **一处**产出：`post_media_flags(post)` 收 ORM 行、`media_flags(*, audio, video, video_url)` 收列投影的三个值——归档那一族不实例化 Post，两种形态都要产出同一组键就不能只给一种入口。它落在 services 层而不是某个 api 模块，是因为 `repositories/post.py` 的归档投影也要用它，而 repository 反向 import `api/blog.py` 会成环。六个手写产出点（主列表/搜索、`/posts/recommended`、`/posts/{id}/similar`、`/posts/hot` 四个模型构造点 + 归档年页与归档月页两个裸 dict 构造点）共用；blog.py 里 `**post_media_flags(post),` 的出现次数 == `PostListItemLocalized(...)` 构造点数 + 2 由前端守卫按源码对账，因为"三个变体里挂了两个"和"四个构造点补了三个"是同一类不会有人报的缺陷。`has_video` 在消费侧与 `has_embed` 合并成一个"含视频"徽标（YouTube 嵌入对读者的预期就是视频）。④ **还有一条列表口根本不走这个模型**：`GET /api/ranking/posts`（`api/ranking.py`，热门页日/周/月/总榜四个页签的数据源）自己拼裸 dict，而 `pages/posts/hot.vue` 把条目"补齐成 PostCard 认得的形状"再交给同一套卡片渲染——它漏三位时的表现是"综合榜有徽标、切到周期榜整排消失"，接口一个错都不报。口径是它也 `from backend.services.post_access import post_media_flags` 并 `**post_media_flags(p),`（批次 #121 的初稿是让 ranking.py 反向 import `api/blog.py` 的私有 helper，#122 把产出点下沉到 services 层后那条先例不再需要），榜单裸 dict 的 OpenAPI 文档模型 `HotPostItemDoc` 同批声明三键并**给默认值**（60s 响应缓存里躺着旧载荷）。⑤ **归档三面与系列目录同样不走那个模型**（批次 #122）：`/blog/archive` 走 `PostRepository.get_archive_data` 的**列投影**（不实例化 Post，所以要在 select 里点名取 `Post.audio / Post.video / Post.video_url` 再调 `media_flags`），`/blog/archive/{year}` 与 `/{year}/{month}` 走 ORM 行调 `post_media_flags`，`/series/{slug}` 的章节目录是另一条列投影。文档模型 `ArchivePostItem`（`schemas/blog_reads.py`）与 `SeriesPostItemDoc`（`api/post_series.py`）同批声明三键并**给默认值**——两条口的载荷都进缓存。前端四处共用同一个 `PostMediaFlags`（归档首页/年页/月页的元信息行 + 系列目录的章行），漏一处的表现是"列表页有徽标、归档页没有"。守卫 `tests/test_post_media_list_flags.py`（逐口 True + 载荷里不得出现 `audio`/`video`/`video_url` 键 + 清空媒体后回落 False + PUT 只改一列时另两列不动 + 旧载荷仍 validates + 榜单两条 period 路径各自带三位且 plain 稿全 False + 归档首页/年页/月页与系列目录逐口 True、同族 plain 稿全 False + 三个文档模型三键非必填）与 `frontend/tests/unit/postMediaBadgeWired.spec.ts`（PostCard 三个变体各挂一次 + 四语 `post.hasAudio`/`hasVideo` 齐全 + 榜单口复用 helper 而非另写字段清单 + hot.vue 映射透传三位 + 归档/系列的 select 里点名取了那三列 + 四个渲染页都不读媒体地址）。
- **退役一个响应模型字段之前，必须先想清楚「存量缓存载荷」这一层：读侧要按当前声明投影，不能让旧载荷把公开口打挂。** `site_config` 的载荷存在 Redis（TTL 3600，跨进程、跨重启存活），批次 #108 把 OOBE 幽灵开关从 `SiteConfigResponse` 删掉后，线上 `GET /api/config` 稳定 500 到整个 TTL：旧载荷多带那个键，而 `backend/schemas/strict_config.py::apply_strict_extra_forbid` 给包内**所有**模型补了 `extra="forbid"`（本意是拦请求体多带字段），`SiteConfigResponse(**cached)` 于是抛 ValidationError。更糟的是 `cache_warmer._warmup_site_config` 委托的正是同一个端点函数，**重启也救不回来**，而 SSR 页面仍回 200（配置口被兜底吞掉），所以症状是「站点活着、配置驱动的功能静默退化」而不是「站点挂了」。口径：把「缓存命中」定义成「还能按当前模型解出来」（`api/core.py::_site_config_from_cached`：多带键或解不出就回 None → 重算 → 返回前覆写，漂移只发生一次请求），**模型本身的 forbid 一律不放宽**（写口那半边门禁照旧）。同一条判断适用于任何「跨重启的缓存载荷 + 会被退役的字段」组合；新增必填字段是反向同一条路（旧载荷少带键）。守卫 `tests/test_site_config_cache_shape_drift.py`（陈旧键 200 + 载荷被覆写成当前形状 + 形状相符仍走命中 + 缺必填键重算 + 模型仍 forbid 五条），反证过：只按 `model_fields` 过滤后直接构造而「不许重算」会让缺键那条红。
- **同一批列的另一面：值可能根本不是 dict 而是裸字符串**（导入工具、早期写入路径、直接写库都会留下 `content="正文"`）。
  汇聚点是 `core/i18n.py::get_i18n_value`（60+ 个读取口共用），收口前只会 `data.get(...)`，
  于是**一条脏数据就让文章详情、相邻文章、公开列表整口 500**（`Post.__repr__` 同型：它出现在日志与
  断言输出里，踩一次等于把"记一条日志"变成 500）。口径：`isinstance(data, str)` 原样返回＝"整段当默认语言"，
  而不是把接口打挂。
  **但光修汇聚点不够**——第一轮收口后复查，仍有七处绕过 helper 自己 `col.get(lang, col.get("zh"))`：
  归档年/月两条公开口（`api/blog.py`，前台 SSR 页直接打）、`PostRepository` 的归档映射、
  Markdown 导出（title/content/category/tags 四列一次摊进 frontmatter）、系列 autocomplete、
  `seo.py` 的 `articleSection`、以及七个模型 `__repr__`。口径是**新增读取面一律走 `get_i18n_value`，
  不要在调用点再写一遍 isinstance**；`seo.py::_pick` 是本文件同语义的等价 helper，可继续用。
  回归 `tests/test_i18n_value_shapes.py`（纯函数三形 + 详情/相邻/列表/归档年/归档月/SEO schema/
  系列 autocomplete/Markdown 导出八口 + repr 两例；反证过：去掉 isinstance 分支红 4 条、
  回退这七处红 6 条）。造已发布的历史行时 `published_at` 必须用 **naive** datetime——归档口按
  `extract("year", published_at)` 过滤，SQLite 把 aware 值存成带 `+00:00` 后缀的字符串，
  `strftime('%Y')` 取不出年份，这条会被 WHERE 静默滤掉、用例假绿；同理 `post.tags = [...]` 只能在构造时传，
  commit 之后赋值会先懒加载旧集合而异步会话属性懒加载就是 `MissingGreenlet`。
- **SQLite 上"发布时间已到今天"的谓词会静默筛空列表**：匿名列表口用 `Post.published_at <= func.now()`，
  而 SQLite 把 aware datetime 存成带 `+00:00` 后缀的字符串、与 `CURRENT_TIMESTAMP` 做**字符串**比较，
  刚写入的行一律判成"在未来"。测试造已发布行时把 `published_at` 留 `NULL`（谓词是 `IS NULL OR <= now()`），
  别指望 PG 的语义；这个坑与 §11 的方言守卫同源，读到空页先怀疑这里而不是查询写错。
- **归档的时间边界一律用 UTC 区间，不用 `extract("year"/"month", published_at)`。** `extract` 按**数据库会话时区**求值（生产 PG 会话是 Asia/Shanghai），而本仓其它分组都在 Python 里读 asyncpg 返回的 UTC 值——同一篇文章会被月页算进 9 月、年度页分组到 8 月（线上实测：2026-08-31T23:09Z 的两篇，`/archive/2026/09` 说 23 篇而 `/archive/2026` 的 9 月块说 21 篇）。口径收敛在 `backend/repositories/post.py` 的 `utc_year_range` / `utc_month_range` / `utc_year_month`，四条归档面（`/blog/archive/{year}`、`/{year}/{month}`、`/archive/stats`、`sitemap-pages.xml`）与前端年份分组（`getUTCFullYear`）和「月日」渲染（`formatMonthDayText` 取 `getUTC*`）同源。SQLite 复现不出这个分歧（它把 aware 值存成字符串、`strftime` 与 `extract` 都不随会话时区变），所以守卫 `tests/test_archive_utc_boundaries.py` 一半是源码断言（四份文件里不得再出现 `extract("year"/"month", Post.published_at)`），一半是半开区间与归一化的纯函数用例。
- **归档空年份/空月份是"URL 不存在"，不是"存在但没发文章"。** 页面先判 `yearNotFound` / `monthNotFound`（`useContentStatus` + pending 守卫），面板只给文案与两条出口，页头（h1 + 「共 N 篇文章」）整段收进 `v-else`；请求失败另有独立分支，不得复用空态文案。契约见 `frontend/tests/unit/archiveNotFoundShell.spec.ts`。
- **回收站的「可恢复类型」以写手清单为准，不是以 UI 标签为准。** 删除侧唯一入口是 `backend/services/trash.py::snapshot_to_trash` + 一个 `<type>_trash_payload()`；当前三个写手是文章（`blog.py` 单删、`advanced.py` 批删）、独立页（`core.py::delete_page`）、评论（`admin.py` 单删、`comment_service.py::admin_batch` 批删）。两条红线：① **新增可恢复资源时同时改三处**——写手、`advanced.py::restore_trash_item` 的分支、`pages/admin/content/trash.vue` 的 `typeFilters`，漏一处的表现是"筛选永远为空"或"恢复时撞 NOT NULL/外键 500"（评论的旧恢复分支只重建 4 列，而 `author_name`/`status` 是 NOT NULL，那段代码从未成立过）；② 恢复的前置条件必须回 400 而不是让约束报错——slug 唯一（文章/页面）、`comments.post_id` 是 NOT NULL+CASCADE 所以原文章已删时评论无处可回。保留期由 `prune_expired_trash` 兑现（挂在 `main.py::_log_retention_loop`，与日志同批、同样先睡后删）：快照里存着**整篇正文**，不清等于把"保留 30 天"做成永久保留。契约测试 `tests/test_trash_recover_surfaces.py` + `frontend/tests/unit/trashRecoverableTypes.spec.ts`（后者断言筛选器集合与后端写手集合精确相等）。
- **删除语义变了，前台文案必须跟着改。** 独立页与评论现在删除后回显「已移入回收站」，而留言板仍是物理删除；`CommentListContent.vue` 是两种语义共用的组件，确认文案必须按 `isGuestbook` 分叉，写死「删除后无法恢复」等于对管理员撒谎（反过来提示"可恢复"给真删不掉的留言板也一样）。提示语优先用后端返回的 `message`，不要在组件里另写一套。
- 新 API 路径必须用 `useAPI` 或 `apiFetch` 包装，不得裸写 `$fetch`

### 9.2 前端

```bash
pnpm lint          # 0 error，warnings == 7
pnpm typecheck     # 0 TS error
pnpm build         # Σ Total size 3.96 MB（gzip 992 kB），2026-10-27 本机实测（图标/高亮瘦身后）
pnpm test          # 全绿（108 个 spec 文件；1762 用例，2026-10-29 本机实测）
```

构建日志零命中：`Hydration node mismatch` · `Failed to fetch` · `/api/api` · `CORS`

- **后台 UI 的每一项声明都必须有后端写手或执行者**（回收站批次踩全的三类）：筛选枚举/标签/承诺只是文案时，
  接口永远不会满足它。口径是「UI `typeFilters` 的键集合 ⇔ 后端 `resource_type="…"` 的写入点」**集合相等**，
  由 `frontend/tests/unit/trashRecoverableTypes.spec.ts` 双向对账；新增一个可恢复类型要同时改写手、恢复分支、
  UI 筛选。恢复前置条件不满足回 **400**（`Page.slug` 唯一、`comments.post_id` NOT NULL+CASCADE），不要赌 500。
  「保留 30 天」这类倒计时必须有执行者（`TRASH_RETENTION_DAYS` 挂在 `main.py::_log_retention_loop`），
  只在 `TrashItem.auto_delete_at` 写时间戳等于永远不删。改了删除语义还要拖着 UI 文案走，
  留言板和文章不能共用一句"可恢复"（判据在 `isGuestbook` 分支，或直接采用服务端 `message`）。
- **只读指标端点也要有消费方**：`/api/monitoring/*` 曾八条全部零消费者——后端一直在算，后台一个都看不到。
  接线口径由 `frontend/tests/unit/monitoringEndpointsWired.spec.ts` 按「后端 `@router.get` 声明集 ⇔ 页面
  `section()` 请求集」集合相等钉住。三条该接口族特有的读数诚信（写进 `pages/admin/tools/monitoring.vue` 头注释）：
  ① `/performance` 是**进程内环形缓冲**（重启即空、无样本时不回 `sample_count` 键，必须按键存在性区分"没样本"
  与"0ms"），与 `/performance/summary` 的**访问日志窗口**（跨重启）不能混算也不能同一个标题混排；
  ② `visit_logs` 受 `LOG_RETENTION_DAYS` 清理，`retention_days < 窗口天数` 时读数只是**下界**，
  必须同时用 `retention_days` 与 `data_since` 标注；③ `/database` 的 `database_url` 是掩码连接串，
  **掩码不等于可公开**，不得上屏（守卫只查 `<template>` 区，文件头注释可以提它）。
- **取数失败按段隔离**：多端点页面用 `Promise.all` + 每段自己的 `silentToast: true` 错误串，
  一段挂掉不清空整页读数（`apiFetch` 不静默就会与页内 banner 双报）。取数函数带泛型实参
  （`section<LatencyShape>(…)`）：不传时 `T` 推断成 `unknown`，赋给 typed ref 就是整排 TS2322。
- **`@stylistic/member-delimiter-style` 在本仓的实际口径**：多行 type/interface 字面量的成员**不写任何分隔符**
  （`delimiter: "none"`，`;` 和 `,` 都会红），单行内联对象才用 `,`。`eslint --fix` 修不了这一条，只能手写。
- **"同路径多 verb" 的路由族不能只按路径集合对账**：定时发布的 `PUT` 与 `DELETE` 共用
  `/admin/posts/{post_id}/schedule`，所以「后端声明路径集 ⇔ 页面请求路径集」相等**看不出漏掉的 verb**——
  守卫必须额外断言路由条数并逐个 `method:` 实参（`tests/unit/scheduledQueueWired.spec.ts`）。
  该接口族另外四条口径（写进 `pages/admin/content/scheduled.vue` 头注释）：① `GET /admin/posts/scheduled`
  **读之前先把到期文章推进成 published**（有写副作用），页面不得静默轮询，多开一个标签页就是替管理员
  多触发一次发布时机；② `scheduled_at` ↔ `<input type="datetime-local">` 只能过 `lib/datetime` 换算
  （输入框是本地墙钟、库里是 UTC，手裁 ISO 会让东八区的"10:00 发布"在 18:00 生效）；③ 后端对
  "不晚于现在"的时间是**就地发布而不是 400**，改期表单必须先过 `scheduledAtError` 并把错误显示在字段上；
  ④ 取消一条 `scheduled` 会连带回到 `draft`（否则留下"等待发布但没有计划时间"的死状态），
  提示语必须直接用服务端的 `message`，页面自己写死"定时发布已取消"就是在撒谎。
  服务端侧的配套约束：等待态有两种（`status="scheduled"` 与历史的 `published` + 未来 `scheduled_at`），
  `publish_due_posts` 与 `main.py::_scheduled_publish_loop` **必须共用同一个谓词与同一份失效动作**——
  循环里内联一份只改状态不清缓存的查询，表现就是"后台队列空了、前台仍看不到"。

### 9.3 产品验收

- 明/暗主题切换：前台 2 套 + Admin 原生均 OK；Admin 不被前台 CSS 污染
- 四语切换：zh / en / ja / zh_Hant 无 404
- SSR 关键页 `Ctrl+U`：首页、文章详情、分类、留言板有真实 HTML
- SSR 反选页：`/admin/*` · `/login` · `/register` · `/forgot-password` · `/search/*` · `/account` 是空壳 SPA（`/oobe` 不在此列，它保留 SSR 只禁缓存）；该口径由 `tests/unit/routeRulesSsr.spec.ts` 静态锁定，不必开浏览器复核

***

## 10. shadcn-vue 硬性规范

1. **Button SVG Icon**：`buttonVariants` 已声明 `[&_svg]:size-4`，Button 子树 lucide icon 不再写 `w-4 h-4 / size-*`
2. **Lucide icon 数据属性**：Label / Button / Tab / DropdownItem 中的图标必须写 `data-icon="inline-start"` 或 `data-icon="inline-end"`
3. **Gap 代替 Space**：`flex / grid` 容器用 `gap-*`，禁止 `space-x-* / space-y-*`
4. **reka-ui 绑定**：reka-ui 2.10.x 的 Switch/Checkbox 受控 prop/事件是 `modelValue` / `@update:model-value`（1.x 的 `checked`/`@update:checked` 命名已不适用，误用会导致开关状态不显示/不回写）
5. **shadcn Forms + Zod**：`useForm` 与 `FormItem / FormMessage` 配对，错误不要 toast + FormMessage 双报
6. **Admin 扁平化**：禁止给 Card / 表格行加左侧彩条

***

## 11. 编码风格 / 命名

| 对象 | 约定 |
| ---- | ---- |
| Vue 组件 | PascalCase，目录 kebab-case（`components/admin/StatCard.vue`） |
| Composable | `useXxx.ts`，导出 `useXxx()` 同名函数 |
| Pinia store | `stores/xxx.ts`；`defineStore('xxx', () => …)` setup 语法 |
| 页面路由 | `pages/**` kebab-case；动态参数 `[param].vue` / catchall `[...catchall].vue` |
| Python 模块/变量 | snake_case；类名 PascalCase；`Annotated[T, Depends(…)]` DI |
| Pydantic 字段 | 双引号；`Field(…, min_length=, max_length=, pattern=)` 显式约束 |
| SQLAlchemy model | `__tablename__ = "snake_case"`；JSON 字段用 `MutableList/MutableDict` |

Python 细节：双引号字符串；I/O 全 `async/await`；插件注册入口是**同步** `register()`。

### Conventional Commits

```
feat/fix/refactor/perf/i18n/chore/docs: 描述
```
PR 标题：`{scope}: {message}`，例如 `feat(frontend): SSR 留言板 apiFetch 化`

***

## 12. 安全红线（零容忍）

1. 密钥 / JWT `SECRET_KEY` / DB 连接串 / 邮箱密码 / GitHub PAT 必须通过 `.env`，严禁硬编码
2. SSR 顶层 setup 不得直接使用 `window / document / localStorage / navigator / matchMedia`
3. 主题 `style.css` 禁止 blanket 通用选择器（`main / header / a / h1 / .btn`），必须带作用域守卫
4. ~~`.card-surface` 共享类禁止主题重写~~（2026-09 解除：main.css 内已是中性基座版；主题可在**双守卫作用域内**装饰它，见 §3）
5. 不得把 JWT / admin 资料以 `useState` 序列化到 HTML，用 Pinia `skipHydrate` + localStorage
6. CSP / 安全头只能更严不能更松
7. 用户上传文件：`MAX_UPLOAD_SIZE` + `ALLOWED_EXTENSIONS` 双校验；图片 Pillow verify；头像代理 SSRF 白名单
8. 会渲染到访客页面上的短字符串字段（称号图标 `user_titles.icon` 等）：写入侧必须用 Pydantic `pattern` 拒掉标记语言（`^[^<>]*$` + `max_length`），渲染侧不得对其 `v-html`。只守渲染侧不算守——DB 里躺着脏数据时，换一个消费点就中招

***

## 13. 不做清单（Hard Constraints）

1. ❌ 后端不迁移到 Nitro / Node.js
2. ❌ i18n 不新增 zh/en/ja/zh_Hant 以外的语言
3. ❌ SSR 不回退到全局 SPA（仅 routeRules 精准反选）
4. ❌ 不创建 `frontend/app/pages/` 与 `frontend/pages/` 双目录并存
5. ❌ 不在 Admin 页面注入前台主题 CSS 作用域
6. ❌ 不应用 Alembic autogenerate "drop all tables" 文件（立即删除，检查 env.py target_metadata）
7. ❌ 不给 Admin 卡片加彩色左侧条

***

## 14. 维护者补充

- 本文档随代码演进。发现规范与实际冲突时，修改代码或修改本规范二选一，不得长期不一致。
- 新增内建主题：`frontend/themes/{slug}/` 创建 `rosetta-theme.json + style.css + screenshot`，`style.css` 必须满足 §3 CSS 守卫；`mods_schema.properties` 是 Customizer 控件的唯一清单（后端只接受已声明键，前端只消费有真实消费点的键）。若新主题需要**独立的 DOM 骨架**（首页/页脚/登录注册/错误页结构分支），还必须在 `frontend/lib/rosetta-themes.ts` 的 `MINIMAL_THEME_SLUGS` 登记；只换皮肤的主题不登记，自动落回默认骨架 —— 详见 `frontend/AGENTS.md`「主题变体契约」。
- 新增插件：`backend/plugins/{slug}/` 创建 `rosetta-plugin.json + plugin.py`，注册入口是同步 `register(app, ctx)`。
- 新增语言：必须先在 §13.2 去掉禁止，然后同步补 `i18n.config.ts` · `i18n/locales/xx.json` · `backend/core/i18n.py`（`SUPPORTED_LANGUAGES` / `LANGUAGE_CODES`，语言清单唯一真源）· site_settings 默认值全链路。
- **安全响应头分两层，各管一半，叠不得**：`/api/` 与 `/media/` 的 6 个头由 `backend/core/security_middleware.py` 发（CSP 带 per-request nonce）；HTML / `/_nuxt/**` / `rss` / `sitemap` / `robots` 由 nginx 反代 Nitro 的那个 `location` 发（Nitro 自己一个头都不发）。两条 nginx 陷阱：**① `add_header` 不继承**——某个 location 一旦自己写了 `add_header`，server 层的同名声明全部失效，所以安全头必须写在具体 location 里，写在 server 层等于给没声明头的 location 兜不住；**② `add_header` 是追加不是替换**——nginx 若也管 `/api/` 就会产出两条 CSP（浏览器按交集同时强制，等于两条都生效）与重复 HSTS。HTML 侧 CSP 逐条对齐 `_build_csp()`，只把 `nonce` 换成 `'unsafe-inline'`（Nitro 的 HTML 有内联 script + `<script type="importmap">`，反代层拿不到 nonce）；**新增第三方源时两处必须同改**，否则后台与前台策略分叉。HSTS 只在 443 块有效，80 块配了等于没配（浏览器拿到 HTML 的是 443）。口径与逐条理由见 `deploy/nginx-site.conf` 注释。
- **换站点域名要动四个源，少一个就是"canonical 与新域名一致、其余口径仍旧"**：根 `.env SITE_URL`（sitemap / OpenAPI servers / 邮件）、DB `basic.site_url`（RSS channel 与 `/api/config` 的权威覆写源，改法是 `PATCH /api/settings/basic`，它顺带清 `settings_public` / `site_config` 缓存并通知 Nitro 清页面缓存）、`frontend/.panel.env NUXT_PUBLIC_SITE_URL`（canonical / hreflang / og:url / JSON-LD）、以及**最容易被漏的** `NUXT_SITE_URL`（私有 `runtimeConfig.siteUrl`，Nitro `server/routes/robots.txt.get.ts::resolveConfiguredOrigin` 先读它——只改前三个时 robots 的 `Sitemap:` 行会长期吐旧域名）。改完重启前后端：Redis 是跨进程的缓存后端，`seo:robots_txt` 这类 TTL 缓存在进程重启后仍在，必须显式 `delete_pattern("seo*")`；Nitro 的 routeRules swr 条目活在进程内，再重启一次前端才会重取上游。nginx 侧的配套约束见 `deploy/nginx-site.conf` 注释（多 SAN、别名独立 443 块 301、`ipv6only=on` 全文只能出现一次）。

— 本文件 v2026.09 由 Rosetta 项目组维护，对应代码基线 v2.1.1 —
