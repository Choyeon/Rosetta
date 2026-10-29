# Rosetta API 覆盖度报告

> **汇总表自 2026-10-28 起由扫描器生成**：`backend/scripts/gen_api_coverage.py`。
> 数据源是生成后的 `app.openapi()["paths"]`（352 条 operation，按 `backend/main.py` 的
> `include_router` 前缀归到 `backend/api/*.py` 模块）× `frontend/**` 源码里的 URL 字面量
> （`useAPI` / `apiFetch` / `silentApiFetch` / 项目自己的请求封装 / `<img src>` 与 `href` 拼接 /
> `frontend/server/` Nitro 路由）。改接口或接线后执行
> `PYTHONPATH=. python backend/scripts/gen_api_coverage.py --write` 重算，**不要手改表中的数字**。
> 本报告**整体替换 2026-08-14 的旧快照**。旧报告中 media、admin、guestbook、gallery、series、webhooks、notifications 等模块标为 0% 均已过时失真（实际已全量或接近全量消费），其数字不再保留。

## 图例与统计口径

- ✅ 已消费：前端源码里有这条路径字面量且处在**请求参数位**（真发请求）
- 🟡 仅 URL 拼接 / 仅 Nitro 侧消费：只出现在 `<img src>`、`href` 或 `frontend/server/`（SSR BFF）里，浏览器不直接调
- ❌ 未消费：后端能力保留或前端缺口，汇总表下方「未消费清单」逐条列出
- **路径规则**：`useAPI/apiFetch` 的 URL 参数不带 `/api` 前缀，故代码中 `'/admin/guestbook'` == `GET /api/admin/guestbook`
- 覆盖率 =（✅ + 🟡）/ 后端端点总数

### 扫描器的两处已知盲区（读表前先记住）

1. **看不见"封装存在但没人点"**：判定只看代码里有没有这条 URL 字面量，不看这个封装有没有 UI 消费点。实例：`comment_reactions` 三条口与 `useFavorites` 删除前的 `getFavorites`（导出一个未定义的名字）都曾被计成 ✅，而界面上从未发过这些请求。已确认并落地的例子见下面 `comment_reactions` 一节（2026-10-16 真正接进 `CommentItem.vue`）。
2. **看不见变量拼出来的 URL**：字面量必须以 `/` 开头才算路径，所以 `` `${apiBase}/media/avatar?src=…` `` 这类拼接形态会落进 ❌（`avatar_proxy` 即是，真实消费点在 `composables/useResolvedAvatar.ts`）。宁少计不多计——把没有请求点的端点算成已覆盖，比留一条假缺口危害大得多。
   > 2026-10-28 补：「先赋给变量再传给封装」这一族已经认了——`const path = isMd ? '/admin/export/markdown' : …`、`const listUrl = computed(() => …)`、以及三元/对象属性位，前提是后文能找到这个名字确实出现在 `apiFetch/useAPI/…` 的实参位上（动词仍从使用点读回，所以 `PUT /api/favorites/{id}` 不会因为同文件有个 GET 收藏口就变绿）。纯字符串拼接仍然不算。

因此**某一条端点到底有没有真实调用方，以下面「分模块明细」与接线契约测试（`tests/unit/*Wired.spec.ts`、`tests/test_*_frontend_contract.py`）为准**；汇总表用于排优先级，不用于下结论。反过来，明细小节标题里手写的 `— N/M 覆盖` 是写就当时的快照，**计数以汇总表为准**（历史上门口数字漂移过：`messages` 行写 0 ✅，明细写「已接入 5 条」）。

漂移由 `tests/test_api_coverage_scanner.py` 挡住：改了接口或接线却没跑 `--write`，汇总表与源码就不一致，CI 直接红。

> 历史口径备忘：2026-09-26 那一版是手工快照，之后 2026-10-16 又按 favorite / messages / activity 三轮增量手累过 ✅（各自记了一个"等价数字"），模块行与合计行从此长期对不上（模块行里 `messages` 仍写 0 ✅，而明细写的是「已接入 5 条」）。这些增量**已被本轮扫描器重算取代**，不要再在任何手工数字上加一遍。同期另有一次独立扫描得 295/357 ≈ 82.6%，与 214/352 的差在分母与"仅 URL 拼接消费"的计入方式，同样作废。

> 2026-09-26 复核修订：`composables/useCore.ts` 已删除（15 个导出全项目零调用方，且其 mutation 侧基于 `useAPI` 包装、`await` 拿不到业务数据）。它曾经"名义上"消费过的端点——`/archive/{year}`、`/archive/{year}/{month}`、`/archive/stats`、`/sponsors`、`/config/full`、`POST /admin/settings`、`/hero/slides`、`/ranking/posts`、`/seo/schema/{type}/{id}`、`/seo/open-graph/{type}/{id}`——随之转为未消费；`/friend-links` 的调用点迁至 `composables/useFriendLinks.ts`。**注**：其中 `/archive/{year}` 的这条判定在 2026-10 已失真（`pages/archive/[year].vue` + `middleware/archive-year.ts` 就是它的消费点）；这正是不要手改本表的原因——下一次扫描会重算。`/ranking/posts` 是同一条注的第二个实例（2026-10-29 起失真：热榜页早已接上它，只是扫描器判不出"带泛型的 getter + 括号三元"这种实参形态，见 §ranking 小节）。

## 全模块汇总表
<!-- COVERAGE-AUTO:BEGIN 由 backend/scripts/gen_api_coverage.py 生成，勿手改 -->
> 本区块由 `backend/scripts/gen_api_coverage.py` 扫描生成（后端 361 条 operation × 前端 `frontend/**` 字面量）。**勿手改**：改接口或接线后执行 `PYTHONPATH=. python backend/scripts/gen_api_coverage.py --write` 重算。

**总计：361 个端点操作；✅ 300 + 🟡 6 = 已消费 306 个，未消费 55 个，覆盖率 84.8%。**

> 归不到 `backend/api/*.py` 模块的 3 条挂在 `app` 上（根级路由）：`GET /`、`GET /api/health`、`GET /health`

| 模块（backend/api） | 端点数 | ✅ | 🟡 | ❌ | 覆盖率 |
|---|---:|---:|---:|---:|---:|
| blog | 41 | 36 | 5 | 0 | 100% |
| core | 23 | 20 | 0 | 3 | 87% |
| users | 22 | 18 | 0 | 4 | 82% |
| oobe | 18 | 9 | 0 | 9 | 50% |
| plugins | 16 | 14 | 0 | 2 | 88% |
| admin | 15 | 15 | 0 | 0 | 100% |
| media | 15 | 12 | 0 | 3 | 80% |
| favorite | 12 | 11 | 0 | 1 | 92% |
| themes_ext | 12 | 10 | 0 | 2 | 83% |
| advanced | 11 | 11 | 0 | 0 | 100% |
| gallery | 11 | 11 | 0 | 0 | 100% |
| guestbook | 11 | 11 | 0 | 0 | 100% |
| monitoring | 10 | 9 | 0 | 1 | 90% |
| comments | 9 | 8 | 0 | 1 | 89% |
| seo | 9 | 5 | 1 | 3 | 67% |
| title | 9 | 6 | 0 | 3 | 67% |
| webhook | 9 | 9 | 0 | 0 | 100% |
| activity | 8 | 7 | 0 | 1 | 88% |
| post_series | 8 | 8 | 0 | 0 | 100% |
| import_export | 7 | 7 | 0 | 0 | 100% |
| announcement | 6 | 5 | 0 | 1 | 83% |
| hero | 6 | 6 | 0 | 0 | 100% |
| messages | 6 | 6 | 0 | 0 | 100% |
| notification | 6 | 6 | 0 | 0 | 100% |
| voting | 6 | 5 | 0 | 1 | 83% |
| shortcodes | 5 | 3 | 0 | 2 | 60% |
| admin_tools | 4 | 4 | 0 | 0 | 100% |
| migration | 4 | 4 | 0 | 0 | 100% |
| performance | 4 | 4 | 0 | 0 | 100% |
| post_encryption | 4 | 0 | 0 | 4 | 0% |
| settings_groups | 4 | 4 | 0 | 0 | 100% |
| app | 3 | 1 | 0 | 2 | 33% |
| bing_image | 3 | 0 | 0 | 3 | 0% |
| comment_reactions | 3 | 3 | 0 | 0 | 100% |
| post_crypto | 3 | 0 | 0 | 3 | 0% |
| scheduled_posts | 3 | 3 | 0 | 0 | 100% |
| toc | 3 | 0 | 0 | 3 | 0% |
| bing | 2 | 1 | 0 | 1 | 50% |
| captcha | 2 | 1 | 0 | 1 | 50% |
| docs | 2 | 2 | 0 | 0 | 100% |
| admin_logs | 1 | 1 | 0 | 0 | 100% |
| avatar_proxy | 1 | 0 | 0 | 1 | 0% |
| ranking | 1 | 1 | 0 | 0 | 100% |
| stats | 1 | 1 | 0 | 0 | 100% |
| themes | 1 | 1 | 0 | 0 | 100% |
| translate | 1 | 1 | 0 | 0 | 100% |

## 未消费清单（自动生成，共 55 条）

> 判据是「前端源码里没有这条 URL 字面量」。接线前逐条人工确认它是不是
> 刻意不消费（后台口、内部口、被别的口覆盖），确认后在对应模块小节写一句理由。
- **activity**（1）：`PUT /api/admin/activities/{activity_id}/toggle`
- **announcement**（1）：`PUT /api/admin/announcements/{announcement_id}/toggle`
- **app**（2）：`GET /`、`GET /health`
- **avatar_proxy**（1）：`GET /api/media/avatar`
- **bing**（1）：`GET /api/bing/wallpaper`
- **bing_image**（3）：`GET /api/bing/image`、`GET /api/bing/image/archive`、`GET /api/bing/image/today`
- **captcha**（1）：`POST /api/captcha/verify`
- **comments**（1）：`GET /api/posts/{post_id_or_slug}/comments`
- **core**（3）：`POST /api/admin/settings`、`GET /api/config/full`、`GET /api/sponsors`
- **favorite**（1）：`PUT /api/favorites/{favorite_id}`
- **media**（3）：`GET /api/media/bing-wallpaper`、`POST /api/media/library/upload`、`POST /api/media/upload/stream`
- **monitoring**（1）：`POST /api/monitoring/pageviews`
- **oobe**（9）：`POST /api/oobe/admin-account`、`POST /api/oobe/database-config`、`POST /api/oobe/environment`、`GET /api/oobe/install-dependencies/stream`、`GET /api/oobe/install/stream`、`POST /api/oobe/reset`、`POST /api/oobe/site-config`、`GET /api/oobe/state`、`GET /api/oobe/test-database`
- **plugins**（2）：`POST /api/admin/plugins/{slug}/activate`、`POST /api/admin/plugins/{slug}/deactivate`
- **post_crypto**（3）：`POST /api/post_crypto/derive_keys`、`GET /api/post_crypto/encrypted/{post_id}/preview`、`POST /api/post_crypto/verify_access`
- **post_encryption**（4）：`DELETE /api/admin/posts/{post_id}/encrypt`、`POST /api/admin/posts/{post_id}/encrypt`、`PUT /api/admin/posts/{post_id}/encrypt`、`POST /api/posts/{post_id}/decrypt`
- **seo**（3）：`GET /api/seo/config`、`PUT /api/seo/config`、`GET /api/seo/sitemap.xml`
- **shortcodes**（2）：`DELETE /api/admin/shortcodes/{tag}`、`POST /api/shortcodes/render`
- **themes_ext**（2）：`GET /api/admin/themes/{slug}/mods`、`PUT /api/admin/themes/{slug}/mods`
- **title**（3）：`GET /api/admin/titles/{title_id}`、`PATCH /api/admin/titles/{title_id}`、`GET /api/admin/users/{user_id}/title`
- **toc**（3）：`POST /api/toc/add-ids`、`POST /api/toc/extract`、`POST /api/toc/generate`
- **users**（4）：`PUT /api/users/me/avatar`、`POST /api/users/me/change-password`、`PUT /api/users/me/cover`、`GET /api/users/username/{username}/preferences`
- **voting**（1）：`GET /api/voting/polls/{poll_id}`
<!-- COVERAGE-AUTO:END -->

## 分模块明细

缩写：`uam`=composables/useAdminManage.ts · `ufl`=composables/useFriendLinks.ts · `up`=composables/usePosts.ts · `ucm`=composables/useComments.ts · `umd`=composables/useMedia.ts · `uoo`=composables/useOOBE.ts · `us`=composables/useSite.ts · `uft`=composables/useFrontendTheme.ts · `ubw`=composables/useBingWallpaper.ts · `udc`=composables/useDocsCatalog.ts · `upm`=composables/usePluginMenu.ts · `sa`=stores/auth.ts · `TM`=components/admin/themes/ThemeManager.vue · `PM`=components/admin/plugins/PluginManager.vue · `NSR`=frontend/server/routes（Nitro BFF）

### blog（/api/blog）— 40/41 覆盖

✅（35）：`GET /posts`（up:24、pages/categories/[slug].vue:195）、`GET /posts/hot`（pages/posts/hot.vue:139）、`GET /posts/recommended`（pages/index.vue 首页「推荐阅读」区）、`GET /posts/{slug}`（up:65）、`GET /posts/{slug}/adjacent`（pages/posts/[slug].vue:230）、`GET /posts/{post_id}/similar`（up:94）、`POST /posts`（up:109）、`PUT /posts/{post_id}`（up:119 区域，edit 流）、`DELETE /posts/{post_id}`（up:129）、`POST /posts/{post_id}/like`（up:103、pages/posts/[slug].vue:1154）、`POST /posts/batch-status`（up:135、pages/admin/content/posts/index.vue:171）、`GET /posts/{post_id}/edit`（pages/admin/content/posts/[id]/edit.vue:35）、`GET/POST /posts/{post_id}/comments`（ucm:25,60、uam:341）、`GET /categories` + `POST/PUT/DELETE /categories/{id}`（pages/index.vue:1123、uam:590–614）、`GET /categories/slug/{slug}`（pages/categories/[slug].vue:188）、`GET /tags` 及 `POST/PUT/DELETE /tags/{id}`（pages/index.vue:1127、uam:619–640）、`GET /tags/slug/{slug}`（pages/tags/[slug].vue:168）、`GET /archive`（pages/archive/index.vue:180）、`GET /site-stats`（pages/index.vue:1131）、`GET /users/me/{stats,posts,comments,likes,history}` + `DELETE /users/me/history`（共 6 个：pages/account/index.vue 个人中心，四档列表共用一个响应式请求）
🟡（5，仅 Nitro BFF）：`GET /rss`（NSR/rss.xml.get.ts:36）、`GET /sitemap.xml`（NSR/sitemap.xml.get.ts:13）、`GET /sitemap-posts.xml`（NSR/sitemap-posts.xml.get.ts:20）、`GET /sitemap-taxonomies.xml`、`GET /sitemap-pages.xml`（各 .get.ts:10）
❌（1，**重复别名**）：`GET /posts/id/{post_id}`（与 slug 版重复——建议统一的别名）。

> 2026-09-28 口径：归档下钻已接入——新增路由 `pages/archive/[year].vue` 消费 `GET /archive/{year}`，`/archive` 页头部接 `GET /archive/stats` 读数、年份标题改为可点链接（否则新路由不可达）。两条约束写进 `tests/unit/archiveYearRoute.spec.ts`：非法年份参数由命名中间件 `middleware/archive-year.ts` 在进入页面前 `abortNavigation(createError(404))`（页面 setup 里 throw 只渲染 error.vue 但响应仍是 HTTP 200，还会被 swr 缓存成一个可复用的 200 页；闸门放中间件才能真正返回 404，也不把垃圾值发给后端换 422）、日期渲染钉死 `timeZone: UTC` + 固定 locale（两端时区分歧会被 swr 3600 缓存固化，是 /archive 的老 bug 型）。routeRules 同步加 `/archive/**` 同档缓存。
> 2026-09-28 口径（续）：`GET /archive/{year}/{month}` 也已接入——`pages/archive/[year]/[month].vue` 消费该端点做分页月页，父页按 Nuxt 目录式路由移到 `pages/archive/[year]/index.vue`（写成 `[year].vue` 时子路由会静默渲染没有 `<NuxtPage>` outlet 的父组件），年页的月份标题同时改成链向月页。中间件闸门扩到月份：只有 4 位年 + 1–12 月放行，其余（含 `/2026-13`、`/2026-0`、`/2026-007`）在服务端 `abortNavigation` 真 404，不放垃圾参数给 FastAPI 换 400/422；空月份与越界页由 `useContentStatus` 判真 404（WordPress no-such-date 口径）。

> 2026-09-28 口径：blog `users/me` 系 6 个端点全部接入——新建 `pages/account/index.vue`（个人中心，WordPress「我的账户」同款：统计读数 + 我的文章/评论/点赞/阅读足迹四档），入口在顶栏用户菜单（桌面下拉 + 移动抽屉）。四条约束：① 本页走 `ssr:false`（写进 routeRules，与 `/admin` 同档 `no-store, private`）——内容逐登录用户不同，而 auth store 是 `skipHydrate` + localStorage，SSR 期根本没有 token，走 SSR 只会渲染未登录骨架并逼着缓存公开化；② 登录闸门在命名中间件 `middleware/auth-required.ts`（不进全局链，先 `await authStore.initialize()` 再判，否则已登录用户会被 localStorage 未回填误踢）；③ 取消点赞复用后端 `POST /posts/{id}/like` 的 toggle 语义，不另造 DELETE 端点；清空阅读足迹是不可撤销写操作，必须过 `AlertDialog` 二次确认；④ tab/page 全进 query，可分享、前进后退可用。回归见 `tests/unit/accountPage.spec.ts`。

> 2026-09-28 口径：`GET /posts/recommended` 从缺口转为已接入——首页 editorial 分支在「最新文章」与 CTA 之间新增「推荐阅读」区块（`pages/index.vue` 第 5 个并行 `useAPI`，缓存键 `home:recommended:<locale>`，语言切换随其余请求一起 refresh）。三点约束：① 推荐条目先按本页已展示的 slug 去重，去重后不足 2 条整段不渲染，宁缺不凑数；② 极简主题分支按主题变体契约本就不渲染 sidebar/CTA，推荐区同样只在 editorial 分支出现，不是遗漏；③ 该端点走 `RecommendationService` 的加权算法（浏览 30%/点赞 20%/评论 15%/时间衰减 25%/标签匹配 10%），登录用户的浏览历史才启用标签匹配项，访客态退化为热度加权，因此首页对访客也始终有内容。回归见 `tests/unit/homeRecommendedSection.spec.ts`。

> 2026-09-28 口径：内容详情页的「不存在」此前只渲染兜底 UI、HTTP 仍是 200，且带 swr 会被缓存成可索引的空壳（生产实例实测四类页面 × 不存在 slug 全 200，而后端对这些路径明确回 404）。新增 `composables/useContentStatus.ts`，在 `app:rendered` 时点把真实 404 写回 SSR 响应，四类详情页（`pages/posts/[slug] · categories/[slug] · tags/[slug] · page/[slug]`）全部接线；网络故障与 5xx 不改状态码（临时故障判成永久删除会掉索引）。两条时序约束（payload 落值前判定=全站误判 404；异步回调里取 event=闸门静默失效）记在 AGENTS §2.3.2，回归见 `tests/unit/contentNotFoundStatus.spec.ts`。~~残留观感项：这类 404 页的 `<title>` 仍由 slug 人性化生成~~ —— 同轮已收口：四类详情页标题在「取不到内容且非加载中」时统一用 `error.notFoundTitle`（四语齐），加载中仍留空只显站点名，避免好页面闪一下"页面不存在"。WordPress 的 404 页标题就是「页面不存在」口径，不再由 slug 编出一个假装存在的文章/分类名。生产实例实测：四类不存在 slug 均为 `404 + 标题「页面不存在 …」`，真实文章（含中文 slug）/分类/标签/独立页与首页、列表、年归档标题逐条无变化。

> 2026-09-28 口径：`public_profile=False` 的隐私闸门此前只挡 `GET /username/{username}` 主文档，`/{user_id}/posts · /comments · /stats` 与 `/{username}/preferences` 仍照常吐数据——等于关掉的只是"目录页"，绕过它直接打子资源就把整个主页内容读走。现这些读取面统一过 `users.py::_profile_is_hidden`：**关主页 = 主文档与全部子资源一律 404**（403/401 等于承认账号存在，会被拿来做存在性枚举）；而 `show_posts/show_comments/show_stats=False` 是"隐藏即空"，返回 200 + 空页/全零计数，两者语义不同不可混。本人和 staff 越过两层。开关写入侧联动清作者归档列表缓存 + `purge_frontend_page_cache`（Nitro SWR 页面上还挂着旧归档）。回归 `tests/test_author_archive_filter.py::TestHiddenProfileSubResources`（5 例，含"改开关必须把已缓存的作者列表键清掉"）。

### users（/api/users）— 14/22 覆盖

✅：`POST /login`（sa:95、uoo:1011）、`POST /register`（sa:124）、`POST /refresh`（sa:194）、`POST /logout`（sa:139）、`GET /me`（sa:75）、`PUT /me/avatar`（sa:164）、`PUT /me`（accs:38）、`POST /me/password`（accs:66）、`GET /me/preferences`（accs:43）、`PUT /me/preferences`（accs:57）、`DELETE /me`（accs:763，注销危险区）、`POST /password-reset-request`（fp:141）、`POST /password-reset`（fp:163）、`GET /users/`（用户列表，uam:405）、`GET /username/{username}`（作者主页，aup:214）
❌（7）：`POST /me/change-password`（旧路径，已被 /me/password 取代，刻意不接）、`PUT /me/cover`（与 `PUT /me` 的 `cover_image` 字段是同一次写入的两种入口，账户设置页只保留一个写入口）、`GET /{user_id}`（ID 形态，公开页统一走用户名）、`GET /username/{username}/preferences`、`GET /{user_id}/posts · /comments · /stats`（作者主页改用 `GET /blog/posts?author=<username>` 取列表，保留 id 形态给后台/其他消费方）。
> `DELETE /api/users/me`（2026-10-29 接入 `pages/account/settings.vue` 危险区）的口径三条，界面必须照实说：① **软删除**——只把账号停用（`is_active=False`）并撤销全部令牌，文章/评论正文一律不动，所以提示写「账号停用后无法再登录」而不是「内容将被删除」；② **必须验密码 + 勾选确认**，缺任一项不发请求（后端对空密码回 400「密码错误」，用户看不出是自己没填）；③ **超管不能注销自己**（后端在任何写库之前直接 403），界面按 `is_superuser` 换成说明文案而不是给一张注定失败的表单。密码走请求体不走查询串（AGENTS §12）。回归：`tests/unit/accountSettingsPage.spec.ts` 钉请求体与「成功即清登录态并离开本页」，`tests/test_api_user_management.py::TestUserAccountDeletion` 钉 400/403 与 403 之后账号仍可用。
判定：**剩余是真缺口但已不再是"成体系空白"** —— 个人中心 `/account` 接了读自己内容的 6 个端点，账户设置 `/account/settings` 接了改资料/偏好/改密 4 个写端点（accs = `pages/account/settings.vue`），`/forgot-password` 接了自助找回 2 个端点并替换掉 /login 上"忘记密码功能暂未开放"的禁用占位（fp = `pages/forgot-password.vue`）；作者主页 `/authors/[username]`（aup = `pages/authors/[username].vue`）接上了 `GET /username/{username}`，列表侧不再另开 id 依赖链而是给 `GET /blog/posts` 加了 `author=<username>` 过滤（缓存键含作者段，隐私闸门与 `/users/{id}/posts` 同口径）；注销账户刻意不做入口（软删除但无恢复路径，WordPress 后台同样不开放给用户）。

### core（/api）— 16/19 覆盖

`GET /pages`（uam:805）`GET /pages/{slug}`（pages/page/[slug].vue:67、pages/[slug].vue:155）、`POST /pages`（uam:834）、`PUT/DELETE /pages/{id}`（uam:838,842）、`GET /navigations`（components/AppHeader.vue:121）、`POST/PUT/DELETE /navigations/{id}`（uam:1256–1264）、`GET /admin/navigations`（uam:1218）、`GET /friend-links`（ufl:11）、`POST /friend-links`（uam:1300）、`PUT/DELETE /friend-links/{id}`（uam:1304,1308）、`GET /search-placeholders`（pages/posts/index.vue:218）、`GET /config`（us:285）
❌（3）：`GET /sponsors`、`GET /config/full`、`POST /admin/settings`——原先仅被已删除的 `useCore.ts` 名义消费，全站无真实调用方（settings 走 `PATCH /settings/{group}`）。
> 2026-10-18 补充（捐助口径）：打赏/收款面已改由 **`donate` 设置分组**单源驱动——后台站点设置
> 「捐助」分组可上传多张支付宝/微信等收款码图片，前台 `pages/sponsor.vue` 直接消费
> `useSite().donate`。`GET /sponsors`（读 SiteConfig `SPONSORS` 的打赏者名单）与
> `sponsor_page_title` / `sponsor_methods_json` 等 `sponsor_*` 旧字段因此是**第二套真相源且零消费点**：
> 保留它们只是为了不改动 `SiteFullConfig` 的输出形状，任何新界面**不得**再接它们；
> 彻底下线属独立工程（删 schema 字段 + `core.py` 读写映射 + 相应夹具），不属于"补前端消费点"。

### admin（/api/admin）— 15/15 全覆盖 ✅

✅：用户管理全套 `GET/POST /users`、`GET/PUT/PATCH/DELETE /users/{id}`、`POST /users/{id}/reset-password · /activate · /ban · /unban`（uam:436–516）；`GET /comments`、`PATCH/DELETE /comments/{id}`（uam:293,301,309）
> `PUT /admin/users/{id}` 的请求体 `AdminUserUpdateFull` 现含 `qq` / `avatar_source`（编辑页「基本资料」卡已可填写），
> 且 `extra="forbid"` 已真正生效——多传字段返回 422，不再静默忽略。头衔与超管标记不经此端点（分别走 `titles/assign` 与 `role`）。
✅（2，2026-09-27 接线）：`GET /tools/search-stats`（uam:1636 `fetchAdminSearchStats`）、`POST /tools/optimize-search`（uam:1670 `runAdminSearchOptimize`）——挂载在 pages/admin/tools/seo.vue「内容体检」页的检索字段卡；响应是各自独立的 `response_model`（不是 `success/data/message` 信封），前端按裸对象解包并逐字段兜底。
> `POST /tools/mock-data`、`GET /tools/unused-images`、`POST /tools/clean-unused-images` 已于 2026-09-26 删除：
> 造数只有 CLI 正道（`uv run python -m backend.scripts.mock_data`），后台一键清库属高危；
> 图片清理器的引用扫描漏了 `SiteConfig.logo`/`Album.cover`/`Photo.url`，会误删在用图。
> 现在这三个路径固定 404（守卫见 `tests/test_coverage_api.py`）。

### guestbook（/api）— 11/11 全覆盖 ✅

`GET /guestbook`（pages/guestbook.vue:353）、`POST /guestbook`（:497）、`POST /guestbook/{id}/like`（:540）、`GET /admin/guestbook`（uam:875）、`POST /admin/guestbook/{id}/pin|feature`（uam:889,893）、`/approve|/reject|/spam`（uam:884 以 action 变量透传）、`POST /admin/guestbook/batch`（uam:905）、`DELETE /admin/guestbook/{id}`（uam:898）；后台页 pages/admin/interaction/guestbook.vue

### gallery（/api/gallery + /api/admin/gallery）— 10/10 全覆盖 ✅

`GET /gallery/albums`（pages/gallery.vue:243）、`GET /gallery/albums/{id}`（:282）、`GET/POST /admin/gallery/albums`（uam:1136,1142）、`PUT/DELETE /admin/gallery/albums/{id}`（uam:1147,1152）、`GET /admin/gallery/albums/{id}/photos`（uam:1168）、`POST /admin/gallery/photos`（uam:1189）、`PUT/DELETE /admin/gallery/photos/{id}`（uam:1193,1198）、`DELETE /admin/gallery/photos/batch`（uam:1217，响应含 `deleted_count` / `missing_ids`，前端不得只看 `success`；必须注册在 `/photos/{photo_id}` 之前）；后台页 pages/admin/media/gallery.vue

### media（/api/media）— 12/15

✅：`POST /upload`（umd:20）、`POST /upload/stream`（umd:26）、`POST /avatar`（umd:32）、`POST /cover`（umd:38）、`GET /library`（umd:52、uam:1081）、`GET /library/stats`（umd:56、uam:1104）、`POST /library`（umd:65）、`GET/PUT/DELETE /library/{id}`（umd:72,76,83、uam:1080；三者同为 `CurrentStaff` 档——详情读过去误挂在 `CurrentUser` 上，普通登录用户可逐 id 翻库内任意媒体元数据，2026-09-28 与 PUT/DELETE 对齐；前端无 GET 消费方，后台列表一次取整页）、`DELETE /library/batch`（umd:89、uam:1084；响应含 `deleted_count` / `refused[{id,reason}]` / `missing_ids`，前端 `pages/admin/media/library.vue` 按三种结果分别 toast，不得只看 `success`）
🟡：`GET /{category}/{filename}`——媒体文件直链回源路径（正常 URL 由后端返回、部分场景拼接消费）
❌（3）：`POST /library/upload`（与 upload+library 两步流重复——建议统一）、`DELETE /{category}/{filename}`（后台删除走 `/library/{id}`，此裸文件删除为保留能力）、`GET /bing-wallpaper`（**2026-09-26 转为未消费**：前台壁纸统一走 Nitro BFF `server/api/bing-wallpaper.get.ts`（30m SWR + 无 CORS），其零调用的 `useServerBingWallpaper` 包装已删除；后端代理保留给非 Nuxt 消费方）

### avatar_proxy — 1/1 ✅

`GET /api/media/avatar?src=`：`composables/useResolvedAvatar.ts:130,150`（URL 拼接 + fallback 回退）

### comments（/api）— 8/9

✅：`GET /comments/{id}/replies`（ucm:39,172）、`POST /comments/{id}/like`（ucm:74）、`DELETE /comments/{id}`（ucm:158 → `components/CommentItem.vue` 的删除按钮 + `pages/posts/[slug].vue` 的归属判定）、`POST /admin/comments/{id}/approve|reject|spam`（ucm:94,100,106）、`POST /admin/comments/batch`（ucm:112）
❌（1）：`GET /posts/{post_id_or_slug}/comments`——前端统一走 `GET /blog/posts/{id}/comments`（blog.py 版），此处为同源旧实现。**`POST /posts/{post_id_or_slug}/comments` 这条重复写口已删除 blog.py 版实现**（它不读 comments 分组的长度/嵌套开关，也不过 CSRF 与 IP 频控），现在评论写入只有 comments.py 一条口，前台表单与后台审核回复都走它。两套读口的可读性判据统一在 `backend/services/post_access.py`：草稿/待审/定时未到/加密未解锁文章的评论树对无权观看者一律不可见（列表口回空、写口与 slug 版读口 404）。用户侧删除走 `DELETE /comments/{id}`：归属判据进 SELECT 的 WHERE，「不存在」与「是别人的」回同一个 404（403 在替攻击者数评论 id），删前落回收站快照、删后照发 `comment.deleted` 钩子并清文章缓存 + 前台页面缓存；管理员删别人的评论仍走 `/admin/comments/{id}`。

### comment_reactions（/api）— 3/3 ✅

`GET/POST/DELETE /comments/{id}/reactions[/{emoji}]`（`composables/useComments.ts` 的
`loadCommentReactions` / `addCommentReaction` / `removeCommentReaction`）

> 2026-09 版把这一族记成 ✅ 是**名义覆盖**：封装存在但全项目没有 UI 调用点，界面从未发过这些请求。
> 2026-10-16 真正落到 `components/CommentItem.vue` 的反应条（点开面板才拉统计：后端没有批量反应口，
> 逐条预取就是 N+1；每次 toggle 后以 GET 结果为真源，本地不自增计数）。
> 同批给 `GET`/`POST` 两个口补上文章可读性闸门（`backend/api/comment_reactions.py::_readable_comment`）：
> 此前它们只按 `Comment.id` 查存在与否，草稿/加密文章的评论即使正文被评论口挡住，它的**表情计数**
> 仍能按 comment_id 枚举，且任何登录用户能往看不见的评论上写反应。`DELETE` 刻意不接闸门
> （只删调用者自己的行，两种情况都回同样的 404）。契约见 `tests/test_comment_reaction_gate.py`
> 与 `tests/test_comment_reactions_frontend_contract.py`、前端侧 `tests/unit/commentReactions.spec.ts`。
> emoji 必须放在 DELETE 的**路径**上——放 body 会命中集合路径的 405，表现为"点亮了取消不掉"。

### activity（/api）— 7/8

✅：`GET /activities`（pages/activity.vue 的 `useAPI('/activities')` + components/ActivitySidebarCard.vue 首页侧栏）、`POST /activities`（同页发布框 `publishActivity`）、`POST /activities/{id}/like`（同页 `likeActivity`）、`GET/POST /admin/activities`、`PUT/DELETE /admin/activities/{id}`（composables/useAdminManage.ts:1029–1048）
❌（1，**重复入口**）：`PUT /api/admin/activities/{activity_id}/toggle`（后台用 PUT 详情提交 `is_published`——再造一个按钮就是第二个真相来源）
> 2026-10-29 补记：后台列表原本**没有**行内上下线开关，翻状态要"打开编辑弹窗 → 翻开关 → 保存"，
> 而弹窗那次 PUT 必须把四语 `content` 原样带上（`ActivityBase.content` 必填）。批次 #49 给每一行补了
> `Switch`，载荷是 partial update（只带 `is_published`，`ActivityUpdate` 三字段全可空 + `exclude_unset`，
> 未提交的正文/类型保持原值）。这条口**仍然**不接：翻转在重试、双击、两个管理员并发时不收敛，
> 显式写值幂等——幂等性与"只翻状态不写没正文"由 `tests/test_admin_activity_crud.py` 两条行为断言钉住，
> 接线形状由 `tests/test_activity_frontend_contract.py::test_admin_row_switch_writes_the_explicit_value_not_the_flip` 钉住。
> 2026-10-16 口径：点赞后端**只增不减、允许匿名**，与评论点赞同语义，所以按钮不做取消态、
> 计数以 `refresh()` 拉服务端权威值（本页 swr 600 共享缓存，本地 +1 会与其它访客读数长期不一致）。
> 发布框整块包 `<ClientOnly>`：`/activity` 是公开 SSR 缓存页，auth store 是 skipHydrate，
> 服务端渲染出的登录态外壳会把某一个访客的登录状态冻进共享 HTML。
> 正文上限 `MAX_ACTIVITY_CONTENT_CHARS = 1000`（每种语言各计），是 `POST /activities` 这个
> 公开写口的唯一闸门；前端 `maxlength` 只是提前提示，不是边界。
> 契约见 `tests/test_activity_frontend_contract.py`、`tests/test_admin_activity_crud.py`。

### announcement（/api）— 5/6

✅：`GET/POST /admin/announcements`、`PUT/DELETE /admin/announcements/{id}`（uam:930–958；后台开关以 PUT 实现，pages/admin/interaction/announcements.vue:468）、`GET /announcements`（前台公告条：layouts/default.vue + composables/useAnnouncementBar.ts）
❌（1，**重复入口**）：`PUT /admin/announcements/{id}/toggle`（被 PUT 详情替代——重复入口）
> 2026-09-28 口径：公告条是**两个来源合一**——公告表（多条、带生效时间窗）与设置页 `notice` 分组（全站置顶单条）。后者此前属于"能存能读却无人渲染"的死配置，现由 `useSite().notice` → `noticeToRow()` 接入，`sticky=false` 时排在表格公告之后。两处正文都允许写 Markdown，而横幅是单行纯文本位，统一由 `stripInlineMarkdown()` 剥标记（不为此引入公共页 v-html）。回归见 `tests/unit/announcementBar.spec.ts`。

### hero（/api）— 6/6

✅（6）：`GET /hero/slides` —— `pages/index.vue` 首页横幅轮播（六路并行 useAPI 之一，缓存键带 locale）。
`GET/POST /admin/hero/slides`、`PUT/DELETE /admin/hero/slides/{id}`、`PUT /admin/hero/slides/{id}/toggle` ——
`pages/admin/content/hero.vue`（侧栏「内容 › 首页轮播」）+ `composables/useAdminManage.ts` 五个 wrapper。

> 2026-10-18 口径反转：首页横幅的内容源已从「Bing 每日壁纸」改为「/hero/slides」，
> 于是 hero 分组不再是与首页并行的第二套真相——`hero` 分组的 `bg_image`/`bg_gradient`
> 退为"站长显式覆盖轮播图"的兜底，settings 的 `hero.title/subtitle/cta_*` 退为"没有幻灯片时"的兜底文案。
> 后端 `list_active_hero_slides` 的兜底也同步改为高热度文章（不再委托 bing 侧抓取），
> Bing 壁纸现在只服务登录/注册/OOBE 三个页面。
> 旧回归 `tests/test_hero_bing_fetch_dedup.py` 钉的是"委托 bing 抓取"这条已反转的契约，随之下线；
> 新回归 `tests/test_hero_hot_posts_fallback.py`（含"hero.py 不得出现自有抓取"的源码门禁 +
> "兜底项用负 ID 且本地化随 lang 变化"）。
> 2026-10-18 补充（覆盖谁的问题已在管理页文档头写死）：DB 有生效行时优先用之，一行都没有才落回热榜兜底；
> 后台只有 `media_type: image`（首页仅背景图层，选 video 会存进去却永不渲染＝静默失效），
> `start_time/end_time` 排期窗与 `cta_secondary_*` 次按钮**都已在管理页开放**（2026-10-28 收口）：
> 排期窗含"两端留空＝长期生效"、提交前的倒挂提示，以及"显式 `null` 清除排期"——
> 因为 `exclude_unset` 下只有显式 null 才表达"清空"；时间串按「朴素即 UTC」入库（生产机曾实测偏 8 小时）。
> 判据与消费点由 `tests/unit/apiCoverageClaims.spec.ts` 钉回代码，不再靠表格记忆。


### post_series（/api）— 8/8

✅：`GET /series`（pages/series/index.vue:144）、`GET /series/{slug}`（pages/series/[slug].vue:223）、`GET/POST /admin/series`（uam:742,753）、`PUT/DELETE /admin/series/{id}`（uam:767,776）
✅（补记 2026-10-29，批次 #50）：`POST /post_series/complete` —— 它是**编辑器"同系列文章" autocomplete**（按关键词返回最多 8 条同系列文章，`post_series.py::series_complete`），不是"标记系列完成"；旧判定把名字读成了状态机动作，属误标，而"编辑器没有这一面"的零消费现状已经补上：`components/admin/PostForm.vue` 在选中系列后显示「同系列文章」候选框（默认关键词＝系列名，350ms 防抖），点一条把 `[标题](/语言前缀/posts/slug)` 经 `I18nTabsEditor.insertIntoActiveMarkdown` 插进**当前语言页签**正文的光标处。四条口径：① 候选只含公开可见文章（每个分支都过 `publicly_listable_posts()`），所以插不出指向草稿/定时未到的内链；② `title` 是后端 `get_i18n_value(..., "zh")` 取出的单条中文字符串，插进英文/日文页签时锚文本仍是中文，由作者改写，前端不伪造机器译文；③ 地址按当前 tab 走 `applyLocalePrefix`（AGENTS §2.3.3 第 2 条：正文是 SSR 里爬虫读得到的站内链接图），本仓文章正由 slugify 产出、不含空格与 `?#`，故 slug 原样拼；④ 失败只就地显示一行、走 `silentToast`，不再叠全局 toast。守卫：`tests/unit/apiCoverageClaims.spec.ts`（消费面）+ `tests/test_series_complete_visibility_guard.py`（草稿不入选 / 空白与超长关键词的返回形态）。
✅（补记 2026-10-29）：`PUT /admin/series/{id}/toggle` 已由 `pages/admin/content/series.vue` 的启用徽标消费（`toggleAdminSeries`）——旧判定「后台用 PUT 代替——重复入口」已作废；toggle 口翻的是库里当前值而不是"设成 X"，所以后台只在拿到 200 后回读，不用本地取反。

### ranking / stats / translate / docs / settings_groups

✅：`GET /api/admin/stats`（uam:147，仪表盘）；`POST /api/translate`（uam:1548，pages/admin/tools/translate.vue）；`GET /api/docs/list` · `/docs/{slug}`（udc:63,101，后台文档中心）；settings：`GET /api/settings`（uam:662）、`GET /api/settings/public`（us:298）、`PATCH /api/settings/{group}`（uam:670）；`GET /api/ranking/posts`（pages/posts/hot.vue:213，热榜页切到日/周/月/总榜时走它，`hot` 档才走 `/blog/posts/hot`）。❌：`GET /api/settings/{group}`（有 GET 全量后不再需要——重复入口）。

> `GET /api/ranking/posts` 曾被本表判成"无调用方"（`useRanking` 随 useCore 删除后没人接），
> 而 2026-10 热榜页接上它之后本表仍报 ❌——那是扫描器的盲区，不是没接：URL 写成
> `useAPI<联合类型>(() => (cond ? '/a' : '/b'), {…})`，字面量的最近一层括号是三元自己的 `(`，
> 而回退时"找最近未闭合括号"会一路越过带泛型的 `useAPI<…>(`。口径修在
> `_request_callee_before`（形态③），回归 `tests/test_api_coverage_scanner.py::test_generic_getter_with_parenthesized_ternary_is_consumed`。
> **这条修的是"少计"，不是"多计"**：同一次重扫全站只动了这一行（✅ 292→293）。

### webhook（/api/webhooks）— 9/9 全覆盖 ✅

`GET /`（uam:1427）、`GET /events`（uam:1436，事件名下拉的唯一来源，页面不再硬编码）、`POST /`（uam:1441）、`PUT/DELETE /{id}`（uam:1446,1451）、`POST /{id}/test`（uam:1460）、`GET /{id}/deliveries`（uam:1476）、`POST /deliveries/{id}/retry`（uam:1484）、`POST /{id}/regenerate-secret`（uam:1493）；后台页 pages/admin/system/webhooks.vue（投递记录 Dialog + 一次性明文密钥展示/复制）

> 2026-09-26 契约收口：三张读接口补上 `response_model`（列表此前会把 `is_active`、明文 `secret` 等未声明字段直接吐给前端，页面靠 mapper 兜），`provider` 落库（新增迁移 `20260926_000001`），启停开关的 body key 与模型列对齐（此前 PUT 读 `is_active`、前端发 `active`，开关永远存不上），事件名清单由 `GET /events` 单源提供。投递链路（hooks 总线 → `trigger_webhook`）此前无调用方，现由 `tests/test_webhook_dispatch.py` 钉住。

### notification（/api/notifications）— 6/6 全覆盖 ✅

列表/统计/已读/全部已读/删除/清空（uam:1851–1901；顶栏铃铛消费）

> 2026-10-28 退役：`GET /api/notifications/unread-count` 已删除。它与此前的 6/6 一起被记成「7/7 全覆盖」，
> 但前端从未调用过它——角标走 `GET /stats`（经 `fetchNotificationStats` 把 `{unread}` 归一成 `unread_count`），
> 下拉列表走列表口自带的 `unread_count`，WS 推送则做增量。三条口都覆盖同一件事时，
> 多一条"专用轮询口"只是文档上的覆盖率和代码里的第二份 SQL 实现。
> 守卫见 `tests/test_retired_notification_unread_count.py`（不在 OpenAPI、旧 URL 不再回 200、`/stats` 活路径仍在）。

### oobe（/api/oobe）— 8/16

✅：`GET /status · /check · /system-info · /dependencies`、`POST /install-dependencies`、`GET /install-dependencies/stream`（SSE）、`POST /install`、`GET /install/stream`（SSE）（uoo:551–618,1011）
❌（8，**刻意保留**）：向导实际把建库/站点/管理员合并进 `POST /install` 单调用，旧分步接口 `GET /state`、`POST /environment`、`POST /database-config`、`GET /test-database`、`POST /site-config`、`GET /check-username`、`POST /admin-account`、`POST /reset` 为旧流程与恢复工具保留（reset 有运维价值，无 UI 属预期）。
> 2026-09-26：`POST /complete` 已删除。它自标注 deprecated、前后端零调用，且与 `/install` 是两套并行的初始化实现（行为早已漂移：`/complete` 里示例数据失败被 `except` 吞掉，`/install` 里会中止安装）。留着的代价是维护一份没人走的安装路径，`tests/test_api_oobe.py::test_oobe_legacy_complete_endpoint_removed` 钉住 404 防止回潮。

### advanced（/api/admin）— 11/11

✅：`GET /logs`（uam:1611，pages/admin/tools/audit-logs.vue）、`GET /logs/export`（uam exportAdminAuditLogs，同页「导出 CSV/JSON」）、`GET /trash`、`POST /trash/{id}/restore`、`DELETE /trash/{id}`、`DELETE /trash`（uam 回收站段，pages/admin/content/trash.vue；单删文章也已与批删同构落回收站，回归见 `tests/test_trash_flow.py`）、`POST /posts/batch`（uam batchAdminPosts，pages/admin/content/posts/index.vue 的「批量删除/批量置顶/取消置顶」——批量删除从逐条 N 次 DELETE 改为一次请求，软删除口径与单删一致；`add_tag`/`remove_tag` 分支曾因未 eager load `Post.tags` 而稳定 500，现已修复并由 `tests/test_post_batch_actions.py` 全量覆盖）
> 与 `/blog/posts/batch-status` 的分工（2026-09-27 定稿）：状态切换（含 `scheduled`）走 batch-status，`{success,data}` 双层信封；删除/置顶等其余动作走 `/admin/posts/batch`，`affected_count` 平铺。publish/draft 仍只在 batch-status 侧，不再重复接入。

### admin_logs / admin_tools / migration / performance（均 /api/admin）

- admin_logs ✅（补记 2026-10-29）：`DELETE /logs/retention` 已接——`pages/admin/tools/audit-logs.vue` 的「清理旧日志」走 `composables/useAdminManage.ts` 的 wrapper（`days` 限 1-3650）。旧判定「保留策略清理无 UI——小缺口」已作废。口径：它只删**操作留痕**（`operation_logs`），访问日志/性能指标由服务端按 `LOG_RETENTION_DAYS` 的保留循环清理，不是这条口的职责。
- admin_tools ✅4：`GET/POST /alembic/status|upgrade`、`GET/POST /cache/status|flush`（uam:1666–1804；pages/admin/tools/migrations.vue:580,761、cache.vue:390,410）。`/alembic/status` 读取失败一律 500，**不返回** `is_latest=true` 的空壳 200；前端 `loadStatus()` 的 catch 写 `statusError` 并展示『取不到状态 ≠ 已是最新』的错误态（`tests/test_api_admin_tools.py` 两侧都钉住）
- migration ✅4：`POST /start`、`GET /status`、`POST /cancel`、`GET /presets`（uam:1741–1768）
- performance ✅4：`GET /performance/summary`（uam:1569）、`GET /slow · /storage`、`DELETE /cleanup`（pages/admin/tools/performance.vue:672,794,812）

### import_export（/api/admin）— 4/7

✅：`GET /export/posts|markdown`、`POST /import/posts|markdown`（uam:1465,1493；pages/admin/tools/import-export.vue:760,818）
❌（3，**运维保留**）：`GET /backup/info`、`GET /backup/full`、`POST /backup/restore`——整库备份 UI 未建（有意留给部署脚本，防止误操作）。三端已由 `tests/test_import_export_api.py` 覆盖（含"备份包不含密码哈希"断言）；`POST /import/posts` 与 `/backup/restore` 的标签关联语义同见该测试：标签只能在 `Post(...)` 构造器一次性传入，flush 后 `post.tags.append()` 在 async 会话里必抛 `MissingGreenlet`（旧实现即如此，导入带标签的文章从未成功过）。

### seo（/api/seo）— 7/9

✅：`POST /sitemap/generate`（uam、tools/seo.vue）、`GET /sitemap-check`（uam、tools/seo.vue）、`GET /scores`（uam、tools/seo.vue——同一份响应既喂评分表也喂「爬虫预览」的文章选择器）。**2026-10-28 补 2 条**：`GET /open-graph/{type}/{id}` 与 `GET /schema/{type}/{id}` 由 `pages/admin/tools/seo.vue` 的「爬虫预览」标签消费（出口 `useAdminManage.fetchAdminSeoOpenGraph/fetchAdminSeoJsonLd`，契约见 `tests/unit/seoCrawlerPreviewWired.spec.ts` + 根 `AGENTS.md` §2.3.4 第 4 条：两条口**无 `{success,data}` 信封**、不可见资源回 **200 + 只剩 `error` 键**（不是 404，避免按 id 枚举草稿）、**不读调用方身份**，所以管理员预览与爬虫看到的完全一致）。原先这两条仅被已删除的 `useSeoPublic` 名义消费，无真实调用方。
🟡：`GET /sitemap.xml`（NSR/sitemap.xml.get.ts）、`GET /robots.txt`（NSR/robots.txt.get.ts）
❌（2）：`GET/PUT /config`——SEO 配置读写已被 `/api/settings/{seo 组}` 通道替代（**重复入口，建议统一**）

### themes / themes_ext / plugins

- themes（/api）1/1 ✅（**2026-10-28 退役清理**）：`GET /themes/active`（uft:661）是仅存的一条。旧调色板一族的三条端点（清单 / 编译 CSS / 管理员设默认值）**已从后端删除**：它们写的 SiteConfig KV 没有任何读取方，配套的 `html.palette-*` CSS 块也从未生效——挂那个 class 的 `composables/useThemePalette.ts` 在主题解耦那轮（f0c195c1）就删了，剩下的是"后台改了但什么都不发生"的假开关。站点主色的活路径：主题 mods 的 `primary_color` > `settings.appearance.primary_color`，两者都由 `useFrontendTheme.ts` 写进 `:root --primary`。守卫 `tests/test_retired_palette_family_is_gone.py`。
- themes_ext（/api/admin/themes）9/12：✅ 列表 GET（TM:200 及 ?source=local/remote/upload 查询）、`POST /scan`（TM:220）、`PUT /{slug}/activate`（TM:251）、`PATCH /{slug}/mods`（TM:359）、`DELETE /{slug}`（TM:387）、`POST ""?source=…` 安装（TM:455–473）、`POST /{slug}/upgrade`（TM `upgradeTheme()`，卡片「可升级」Badge + 升级按钮）、`GET /market`＋`POST /market/{slug}/install`（2026-09-27 接入安装弹窗第四来源「市场索引」：TM `loadMarket()/installFromMarket()`，条目列表 + 已安装置灰 + force 刷新）。❌3：`GET /{slug}` 详情、`GET|PUT /{slug}/mods`（列表内联返回 + PATCH 替代）。两侧列表/详情的 `update_available` 均由磁盘清单版本计算（2026-09-27 前恒 false＝升级入口在 UI 上永久锁死），口径由 `tests/test_extension_update_available.py` 钉住。
- plugins（/api/admin/plugins）14/16：✅ 列表（PM:207）、`POST /scan`（:224）、`PATCH /{slug}/status`（:235）、`GET /menu-registry`（upm:67）、`GET|PUT /{slug}/settings`（plugins/guestbook-rss/settings.vue:75,90）、`PATCH /{slug}/settings`（PM:267）、`POST /bulk`（:295,314）、`GET /{slug}` 详情（settings.vue:61）、`DELETE /{slug}`（:292）、`POST /{slug}/upgrade`（:341）、`POST ""?source=local|remote|upload` 安装（PM:412–430，与主题侧同构，zip 校验走 PACKAGE_*/PLUGIN_ZIP_BAD_MANIFEST）、`GET /market`＋`POST /market/{slug}/install`（2026-09-27 接入安装弹窗「市场索引」来源，与主题侧同构）。`update_available` 由后端按磁盘清单版本 vs DB 版本计算（2026-09-27 前恒 false，等于「可升级」Badge 与升级按钮永久锁死，upgrade 端点虽已实现却无入口），现由 `tests/test_extension_update_available.py` 钉住列表/详情/升级后归位三段口径。❌2：`POST /{slug}/activate|deactivate`（被 status PATCH 替代——**重复入口，建议统一**）。

### title（/api/admin 下 titles）— 6/9

✅：`GET/POST /titles`（uam:1011,1019）、`PUT /titles/{id}`（:1024）、`DELETE /titles/{id}`（:1033，204 空响应）、`POST /titles/assign`（:1044）、`DELETE /users/{id}/title`（:1049 `removeAdminUserTitle` → pages/admin/users/[id]/edit.vue:646）
> 2026-09-27：`assignAdminUserTitle` 原来在 `titleId=null` 时直接 `Promise.resolve({success:true,message:'已移除头衔'})`——
> 一条从未发出的假成功；现拆成 assign（必传 number）+ remove 两个真实端点包装，编辑页也不再裸写 `apiFetch`。
> 同日后端 `PATCH/PUT /titles/{id}` 补了 NOT NULL 守卫：显式 `"color": null` 返回 422「称号颜色不能为空」，不再走到 flush 撞 500。
❌（3）：`GET /titles/{id}`（列表含全量，详情无场景——重复）、`PATCH /titles/{id}`（与 PUT 同一 handler——**重复入口**，但已被 `tests/test_api_titles.py` 覆盖校验语义）、`GET /users/{id}/title`（编辑页从用户响应内联取——可接受；注意它只要求登录，任何用户可查他人称号，称号本身是公开档案字段）

### 整模块未消费（后端能力已交付、前端尚无 UI）

| 模块 | 端点数 | 明细与判定 |
|---|---:|---|
| favorite（/api/favorites） | 12 | **2026-10-16 已接入 11 条**：文章详情页收藏钮（`POST /favorites/check` 先取状态 → 收藏/取消）+ 个人中心 `/account` 的「我的收藏」档位（`GET /favorites` 带 `folder_id` 翻页、`DELETE /favorites/post/{id}` 取消、`PATCH /favorites/post/{id}/{folder,note}` 移夹与备注、`GET/POST /favorites/folders` 与 `PUT/DELETE /favorites/folders/{id}` 管理）。前端唯一出口是 `composables/useFavorites.ts`，路径契约由 `frontend/tests/unit/favoritesLanding.spec.ts` + `tests/test_favorites_frontend_contract.py`（对表生成后的 OpenAPI）钉住。**2026-10-23 补**：`DELETE /api/favorites/{favorite_id}`（按收藏行 ID）已接入，但**只用于孤儿行**（`post: null`，历史脏数据没有 post_id，by-post 变体无从下手）；正常行仍走 by-post（删该 (user, post) 的全部行，避免「取消没生效」）。**仍未消费的 1 条是决定不是缺口**：`PUT /api/favorites/{favorite_id}` 按收藏行 ID 整体改写，而 `favorites` 表**至今没有** `(user_id, post_id)` 唯一约束（历史脏数据 + 先 SELECT 再 INSERT 的查重挡不住并发），按行改只改一条重复行、界面表现为「改了但没全改」；by-post 变体改/删全部行，故前端只用 by-post。契约（2026-09-28 修）：`GET /favorites` 的 `total` / `total_pages` 与 `folder_id` 筛选同口径，可直接用 `total_pages` 翻页；两个 by-post PATCH 显式构造响应字典，键集恒为 `FavoriteRecordOut` 的 6 个字段；重复收藏不再让三个「按文章 ID」端点抛 `MultipleResultsFound` → 500。**已知缺口**：根治要加 `(user_id, post_id)` 唯一索引 + 先去重历史行。另：`FolderCreate/FolderUpdate.name` 现声明 `min_length=1, max_length=100`（列宽 `String(100)`），超长名此前直穿到 SQL 在 PostgreSQL 上报 StringDataRightTruncation ⇒ 500，空名则建出标签为空、界面无法定位的收藏夹 |
| messages（/api/messages） | 6 | **2026-10-16 已接入 5 条**：`/account/messages`（登录态私有页，`ssr:false` 走 `/account/**` routeRules 反选）= 会话列表 `GET /messages/conversations`（每对端一行、`?page=` 翻页）+ 会话正文 `GET /messages/{user_id}` + 发送 `POST /messages` + 整段标已读 `PUT /messages/read-all/{user_id}` + 未读角标 `GET /messages/unread/count`；两个入口：顶栏登录菜单（桌面下拉与移动抽屉各一条）与作者主页 `pages/authors/[username].vue` 的「发私信」（`?to=<用户 id>`，包在 `ClientOnly` 里——SSR 期 auth store 是 skipHydrate 拿不到 token，不包就是节点级 hydration mismatch）。前端唯一出口是 `composables/useMessages.ts`，契约由 `frontend/tests/unit/messagesLanding.spec.ts` + `tests/test_messages_frontend_contract.py`（对表生成后的 OpenAPI）钉住。**仍未消费的 1 条是决定不是缺口**：`PUT /api/messages/{message_id}/read` 按单条标已读，而读正文那条已经带副作用把整个会话置为已读，界面不存在「同一会话里只有某几条未读」可展示的状态，包了就是一个无人调的 wrapper 冒充覆盖。契约（2026-09-28 修，2026-10-16 核对路径）：发送的参数走 JSON 请求体（`{recipient_id, content}`，正文 1–5000；文档旧写法 `POST /send` 实为 `POST /api/messages`），不接受 query string——正文进 URL 会被 nginx access log 明文落盘；会话列表保证「每个对端一行」且只含本人的消息；按 id 标记已读对他人消息一律 404（不再用 403 承认私信 id 存在） |
| monitoring（/api/monitoring） | 9 | **2026-10-28 全部接入，2026-10-29 补第 9 条**：`pages/admin/tools/monitoring.vue` 消费八条指标口（health / stats / visits/summary / performance / performance/summary / database / cache / trends?days=），`pages/admin/tools/visits.vue`（访客记录）消费明细口 `GET /visits`——同一族接口两个页面各取一段，集合相等由 `tests/unit/monitoringEndpointsWired.spec.ts` 按「后端 `@router.get` 声明集 ⇔ 两个页面 `section()` 请求集」双向对账钉住。原判定「刻意保留（运维经工具页直访）」已作废——后端一直在算指标，后台一个都看不到才是问题。四条读数口径记在页面头注释与 spec：`database` 的 `database_url` 是掩码串但**不得上屏**；`performance` 环形缓冲无样本时不回 `sample_count` 键（按键存在性区分「没样本」与 0ms）；`visit_logs` 受 `LOG_RETENTION_DAYS` 清理，`retention_days <` 窗口天数时读数只能标成下界并给 `data_since`；`/visits` 的 IP 只有配了 `TRUSTED_PROXY_IPS` 才是真实访客 IP（否则 nginx 反代下全是回环，页面会显式警告），UA 解析在服务端读取时算，cookie 只落**名称**不落值（值是会话凭证）。第 10 条 `POST /api/monitoring/pageviews`（批次 #59 边缘上报）落在 ❌ 是**盲区 2 的实例、不是死口**：消费方是 `frontend/server/middleware/09-pageview-report.ts`，路径写成常量 `PAGEVIEW_PATH = '/monitoring/pageviews'` 后交给 `resolveBackendEndpoint(...)` 拼 baseURL 再 `fetch`，字面量不在请求调用的紧邻位置（扫描器只认 `apiFetch/useAPI/…` 实参位与紧邻 fetch 的字面量）。它有没有真的发出去，线上判据见 `tests/test_pageview_reporting.py` 与 `frontend/tests/unit/pageviewReport.spec.ts`（后者把「载荷键集合 ⇔ 后端 `PageviewReport` 字段集合」钉成相等） |
| captcha（/api/captcha） | 2 | ✅ `GET /captcha` 由 `components/CaptchaField.vue` 消费（留言板写入口，开关 `features.enable_captcha`）。❌ `POST /captcha/verify` 刻意不接：写入侧闸门 `services/captcha_service.ensure_captcha_for_guest` 已经在同一次请求里校验，前端再预校验一次是第二个真相源，且"预校验通过→提交"之间有竞态（答案一次性消费）。 |
| shortcodes（/api） | 5 | 渲染/注册/管理短代码。管理面板已接入 `pages/admin/system/shortcodes.vue`（列表 / 注册模板 / 删除 / 预览四个消费点）；`POST /api/shortcodes/render` 仍无前端消费者——编辑器预览刻意走管理员口，因为公开口不接受 `context`。契约（2026-09-28 修）：`POST /api/shortcodes/render` 公开无鉴权、带 20/min/IP 专属限流、正文上限 200000 字符、**请求体不接受 `context`**（唯一能带 ctx 的入口是管理员预览 `POST /api/admin/shortcodes`）；插件自带 tag 归插件所有，运行时注册/删除一律 409 `SHORTCODE_PLUGIN_OWNED`；API 方式注册的模板短代码落 KV `shortcode_templates` 并在启动/列表时重放（多 worker 与重启后仍可见），但插件页语义不变——插件代码仍是同名 tag 的权威；改注册表会同步抹掉 `post:` / `posts` / `archive` 与前端页面缓存 |
| toc（/api/toc） | 3 | 目录生成/抽取/加锚点。前端 Markdown 渲染本地生成目录，未调后端——重复能力，建议二选一 |
| scheduled_posts（/api） | 3 | **2026-10-28 全部接入**：`pages/admin/content/scheduled.vue`（待发布队列）是唯一消费方——`GET /admin/posts/scheduled` 列表、`PUT /admin/posts/{id}/schedule` 改期/重新排队、`DELETE /admin/posts/{id}/schedule` 取消（取消即回 `draft`，不是停在 `scheduled`）。原判定「前端以 `status=scheduled` + PUT 文章实现，重复入口」**已作废**：状态机口径（`scheduled` 必须带未来 `published_at`、`draft` 不接受定时、到点由调度器发布）由该页与 `tests/unit/scheduledQueueWired.spec.ts` + `tests/test_post_batch_hooks.py` 钉住，生产机探针 2026-10-28 逐条验过（排队→改期→取消回草稿→草稿被 400 拒）。注意 `GET /admin/posts/scheduled` **有写副作用**（顺带发布到期文章），运维脚本不要把它当纯读口轮询 |
| post_encryption（/api） | 4 | 另一套并行设计（独立表 + 独立 CRUD）。**不是"待接 UI 的缺口"**：真正在用的密码门是 `Post.password` 列 + `visibility=password`，编辑器（`components/admin/PostForm.vue`）与读者侧（`X-Post-Password`，正文与评论树同闸门）都已上线并有回归；下面 352 行那条「这两族不接 UI」才是当前口径，本行旧判定「编辑器无加密设置 UI」已作废。这 4 条属**退役候选**（同 2026-10-28 的旧调色板族），删不删由运营决策，不再当作待办 |
| post_crypto（/api/post_crypto） | 3 | 配套上一行的读者侧流程（派生密钥 / 验证访问 / 加密预览）。同上：并行设计、零消费方、退役候选，不是待接入的缺口 |
| admin_logs（/api/admin/logs/retention） | 1 | 手动清理早于 N 天的**操作留痕**（`operation_logs`）。已接：`pages/admin/tools/audit-logs.vue`。`visit_logs` / `performance_metrics` 不在这条口的职责里——它们由服务端按 `LOG_RETENTION_DAYS` 的保留循环清理（先睡后删，短生命周期进程不会误删） |

### bing / bing_image（壁纸代理体系）

- ✅：`GET /api/bing/wallpapers`（ubw:221,285，登录页/OOBE 背景）、`GET /api/bing/image`（ubw:156 拼 `<img>` 直链，流式代理+本地缓存）
- ❌（3）：`GET /api/bing/wallpaper`（单数版与复数版重复——**建议统一**）、`GET /api/bing/image/today · /archive`（归档骨架未接，Nitro 侧 `server/api/bing-wallpaper.get.ts` 直连 cn.bing.com 未走此接口）

### docs（/api/docs）— 2/2 ✅ · translate — 1/1 ✅ · ranking/stats — 全覆盖 ✅

***

## 结论

**总体：352 端点 / 46 模块，前端已覆盖 222（63.1%；= 上表 ✅214 + 🟡8，🟡 是仅 Nitro/直链消费），未覆盖 130。**（本行与上表同源；未覆盖数从 133 降到 130 是删掉了 3 条僵尸端点，不是新接了 3 条。上一版写的 351/208 是漏了后来新增的端点，已按表重算。）未覆盖的 130 个可分三类：

1. **刻意保留的后端能力（约六成，不算债）**：
   - 重复入口族（**建议统一，长期二选一**）：comments.py 的 posts 别名 ×2、`seo GET/PUT /config`、plugins `activate/deactivate` ×2、`PATCH /titles/{id}`、`/archive` 单数 bing wallpaper、`…/{id}/toggle` 里未被消费的 `announcements` 与 `activities` 两条、`GET /titles/{id}`、`GET /settings/{group}`、`media /library/upload`、toc ×3（前端本地生成）、`users` 的 `PUT /me/avatar` · `PUT /me/cover`（与 `PUT /me` 的 `avatar` / `cover_image` 是同一次写入的两个入口）、`POST /me/change-password`（`POST /me/password` 的旧路径别名，同一 service、同为 400、同踢下线）、`GET /voting/polls/{poll_id}`（列表口 `GET /voting/polls` 已内嵌 choices 与票数，前台卡片直接从列表取票，详情口没有第二个消费方）。原列在此处的**旧调色板 ×3 已不再是待选项**：2026-10-28 直接删除（它连"另一个入口"都算不上——写进去的键没有任何读取方）。
   - `…/{id}/toggle` 一族要分两半看，不能整族判成"刻意不用"。后端共 4 条 `PUT …/{id}/toggle`：`hero/slides` 与 `series` 已接（`toggleAdminHeroSlide` / `toggleAdminSeries`，卡片状态徽标点一下就翻值并清前台页面缓存，拿到 200 后回读、不用本地取反）；`announcements` 与 `activities` 那两条刻意不接——列表里的开关是"写成我看到的目标值"，而翻转在重试、双击、两个管理员并发时不收敛（一次重放就得到相反状态），显式写值幂等。两侧都走同一个 service + 同一组缓存失效与 `do_action` 钩子，所以未接的两条不是功能缺口，是入口收敛。（`scheduled_posts` ×3 已从本项移除：2026-10-28 待发布队列页面把它们全部接成真实消费方。）
   - 运维/脚本面：admin tools ×5、`import_export backup` ×3、`oobe` 旧分步 ×8（合并进单 `POST /install`，reset 为恢复工具；`/complete` 已于 2026-09-26 删除）。（原列在此处的 `admin_logs retention` 已于 2026-10-29 移出：`pages/admin/tools/audit-logs.vue` 接了手动清理入口。）
2. **半成品（后端就绪、UI 半接入）**：（主题/插件市场 market UI 2026-09-27 已接入两侧安装弹窗「市场索引」来源，移出此项；主题 upgrade 便捷壳 2026-09-27 已接进主题卡片，移出此项。）（webhook 原列此项，2026-09-26 已补齐投递日志与密钥轮换 UI，转 100%；主题/插件 zip 上传安装 2026-09-27 复核确认两侧 UI 均已接入，移出此项。）
3. **真实缺口（需要排期的功能面）**，最突出的三块：
   - **用户体系外围**（users 15 个 + messages 6；favorite 12 条已于 2026-10-16 接入 10 条，剩下 2 条按收藏行 ID 的变体属「刻意不消费」，见上表 favorite 行；messages 6 条已于同日接入 5 条，见上表 messages 行）。（原列的 `PUT /me`、`GET/PUT /me/preferences`、`POST /me/password` 已在 `pages/account/settings.vue` 落地并由 `tests/unit/accountSettingsPage.spec.ts` 钉住，本项**不再是缺口**；2026-10-29 又接上 `DELETE /api/users/me`（同一页的注销危险区，口径见上表 users 段）；users 一族剩下的 7 条见上表 ❌ 行的逐条判定，全部是**重复入口、旧别名或形态变体**而不是缺功能——`PUT /me/cover` 与 `PUT /me` 的 `cover_image` 是同一次写入的两个入口，只保留一个写入口）

   - **写入口缺唯一性护栏**（voting / favorite 同族）：`POST /api/voting/polls/{id}/vote` 现对登录用户补了「每人一票」（重复 409），`favorites` 的三个 by-post 端点改成容忍重复行（不再 500），但**两张表都还没有** DB 级唯一索引（`votes.poll_id+user_id` / `favorites.user_id+post_id`）：根治要先去重历史行，且 `user_id` 可空（匿名票）使唯一约束不能直接照抄。接入这些域的 UI 前请补这条。**状态（2026-10-16）**：favorite 的 UI 已接入，靠的是「读全部行 + 写全部行」的容忍口径（不是唯一索引），所以界面暂时不会出现「取消没生效」；投票的全局 MVP 也已接入（2026-10-28 补齐另两半：`Poll.post_id` 绑定文章，前台按当前文章取票，投票不再无条件挂在每篇文章下方；`PUT /voting/polls/{id}` 让管理员结束/重新开启与改标题，不再只能连票数一起删）。DB 级唯一索引仍是待办，补上后可以把 by-row 那两个变体一并删掉。   - **后台运维增强**：~~hero 轮播管理（×5）~~（2026-10-18 已落地 `pages/admin/content/hero.vue`，本项不再是缺口）；
   - **内容保护与防滥用**：文章加密（post_encryption + post_crypto ×7）、~~captcha 接入（×2）~~（2026-10-18 留言板写入口已接，见上 captcha 行；评论侧只有服务端闸门）。
     **2026-10-16 判定：加密这两族不接 UI。** 真实在用的加密链路是 `Post.password` 列 +
     `GET /blog/posts/{slug}` 的 `X-Post-Password` 头（`backend/api/blog.py:1238-1252`，
     前端密码门已上线并有回归），而 post_encryption / post_crypto 是另一套并行设计（独立表 + 独立接口）。
     给第二个真相源做界面，等于让"同一篇文章有两个密码来源、改一个另一个不生效"变成用户可见的 bug；
     要收敛应该先在后端二选一并删表，那是一项独立工程，不属于"补前端消费点"。

> 建议：① 优先补齐 users/favorite 系（注册功能已有账号，缺"我的"页面是最大体验空洞）（① 已部分完成：2026-09-28 个人中心 /account 接上 blog users/me 系，users 模块自身的改密/偏好设置仍无 UI）；② 对"重复入口"做一次后端归并 + 本表同步，压缩端点分母；③ ~~主题/插件市场只差前端 Tab~~（2026-09-27 已接入，本项完成）。

— 本报告由静态扫描生成（2026-09-26），新增/删除端点后请重跑扫描，勿手改数字。
