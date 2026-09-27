# Rosetta API 覆盖度报告

> **生成时间：2026-09-26**
> **数据源**：对 `backend/api/*.py` 全部路由装饰器（`@router.get/post/put/patch/delete`，按 `backend/main.py` 的 `include_router` 前缀还原为完整路径）与 `frontend/` 调用点（`useAPI` / `apiFetch` / `silentApiFetch` / `stores` / `server/` Nitro 路由 / 页面组件）的**静态扫描**。
> 本报告**整体替换 2026-08-14 的旧快照**。旧报告中 media、admin、guestbook、gallery、series、webhooks、notifications 等模块标为 0% 均已过时失真（实际已全量或接近全量消费），其数字不再保留。

## 图例与统计口径

- ✅ 已实现：前端有直接调用点（列出 file:line；路径参数用 `${id}` 表示模板字符串）
- 🟡 仅 Nitro 侧 / 仅 URL 拼接消费：只在 `frontend/server/`（SSR BFF）或 `<img src>` 等 URL 拼接中被消费，浏览器不直接调
- ❌ 前端未消费：后端能力保留或前端缺口，逐条注明
- **路径规则**：`useAPI/apiFetch` 的 URL 参数不带 `/api` 前缀，故代码中 `'/admin/guestbook'` == `GET /api/admin/guestbook`
- 覆盖率 =（✅ + 🟡）/ 后端端点总数

**总计：46 个路由模块文件、351 个端点；✅ 200 + 🟡 8 = 已覆盖 208 个，未消费 143 个，覆盖率 59.3%。**

> 2026-09-26 复核修订：`composables/useCore.ts` 已删除（15 个导出全项目零调用方，且其 mutation 侧基于 `useAPI` 包装、`await` 拿不到业务数据）。它曾经"名义上"消费过的端点——`/archive/{year}`、`/archive/{year}/{month}`、`/archive/stats`、`/sponsors`、`/config/full`、`POST /admin/settings`、`/hero/slides`、`/ranking/posts`、`/seo/schema/{type}/{id}`、`/seo/open-graph/{type}/{id}`——随之转为未消费；`/friend-links` 的调用点迁至 `composables/useFriendLinks.ts`。

## 全模块汇总表

| 模块（backend/api） | 完整路径前缀 | 端点数 | ✅ | 🟡 | ❌ | 覆盖率 |
|---|---|---:|---:|---:|---:|---:|
| blog | `/api/blog` | 41 | 25 | 5 | 11 | 73% |
| users | `/api/users` | 22 | 7 | 0 | 15 | 32% |
| core | `/api` | 19 | 16 | 0 | 3 | 84% |
| admin | `/api/admin` | 15 | 15 | 0 | 0 | 100% |
| oobe | `/api/oobe` | 16 | 8 | 0 | 8 | 50% |
| media | `/api/media` | 15 | 11 | 1 | 3 | 80% |
| favorite | `/api/favorites` | 12 | 0 | 0 | 12 | 0% |
| plugins | `/api/admin/plugins` | 16 | 11 | 0 | 5 | 69% |
| advanced | `/api/admin` | 11 | 1 | 0 | 10 | 9% |
| themes_ext | `/api/admin/themes` | 12 | 6 | 0 | 6 | 50% |
| guestbook | `/api` | 11 | 11 | 0 | 0 | 100% |
| gallery | `/api/gallery` · `/api/admin/gallery` | 10 | 10 | 0 | 0 | 100% |
| activity | `/api` | 8 | 6 | 0 | 2 | 75% |
| comments | `/api` | 8 | 6 | 0 | 2 | 75% |
| monitoring | `/api/monitoring` | 8 | 0 | 0 | 8 | 0% |
| post_series | `/api` | 8 | 6 | 0 | 2 | 75% |
| webhook | `/api/webhooks` | 9 | 9 | 0 | 0 | 100% |
| title | `/api/admin`（titles） | 9 | 6 | 0 | 3 | 67% |
| seo | `/api/seo` | 9 | 3 | 2 | 4 | 56% |
| notification | `/api/notifications` | 7 | 7 | 0 | 0 | 100% |
| import_export | `/api/admin` | 7 | 4 | 0 | 3 | 57% |
| announcement | `/api` | 6 | 4 | 0 | 2 | 67% |
| messages | `/api/messages` | 6 | 0 | 0 | 6 | 0% |
| voting | `/api/voting` | 5 | 2 | 0 | 3 | 40% |
| shortcodes | `/api` | 5 | 0 | 0 | 5 | 0% |
| hero | `/api` | 6 | 0 | 0 | 6 | 0% |
| admin_tools | `/api/admin`（alembic/cache） | 4 | 4 | 0 | 0 | 100% |
| migration | `/api/admin/migration` | 4 | 4 | 0 | 0 | 100% |
| performance | `/api/admin` | 4 | 4 | 0 | 0 | 100% |
| post_encryption | `/api` | 4 | 0 | 0 | 4 | 0% |
| settings_groups | `/api/settings` | 4 | 3 | 0 | 1 | 75% |
| themes | `/api` | 4 | 1 | 0 | 3 | 25% |
| bing_image | `/api/bing/image` | 3 | 1 | 0 | 2 | 33% |
| captcha | `/api/captcha` | 2 | 0 | 0 | 2 | 0% |
| post_crypto | `/api/post_crypto` | 3 | 0 | 0 | 3 | 0% |
| scheduled_posts | `/api` | 3 | 0 | 0 | 3 | 0% |
| comment_reactions | `/api` | 3 | 3 | 0 | 0 | 100% |
| toc | `/api/toc` | 3 | 0 | 0 | 3 | 0% |
| bing | `/api/bing` | 2 | 1 | 0 | 1 | 50% |
| blog.py 外零散：avatar_proxy | `/api/media/avatar` | 1 | 1 | 0 | 0 | 100% |
| admin_logs | `/api/admin/logs/retention` | 1 | 0 | 0 | 1 | 0% |
| ranking | `/api/ranking/posts` | 1 | 0 | 0 | 1 | 0% |
| stats | `/api/admin/stats` | 1 | 1 | 0 | 0 | 100% |
| translate | `/api/translate` | 1 | 1 | 0 | 0 | 100% |
| docs | `/api/docs` | 2 | 2 | 0 | 0 | 100% |
| **合计** | — | **355** | **195** | **8** | **152** | **57.2%** |

***

## 分模块明细

缩写：`uam`=composables/useAdminManage.ts · `ufl`=composables/useFriendLinks.ts · `up`=composables/usePosts.ts · `ucm`=composables/useComments.ts · `umd`=composables/useMedia.ts · `uoo`=composables/useOOBE.ts · `us`=composables/useSite.ts · `uft`=composables/useFrontendTheme.ts · `ubw`=composables/useBingWallpaper.ts · `udc`=composables/useDocsCatalog.ts · `upm`=composables/usePluginMenu.ts · `sa`=stores/auth.ts · `TM`=components/admin/themes/ThemeManager.vue · `PM`=components/admin/plugins/PluginManager.vue · `NSR`=frontend/server/routes（Nitro BFF）

### blog（/api/blog）— 30/41 覆盖

✅（28）：`GET /posts`（up:24、pages/categories/[slug].vue:195）、`GET /posts/hot`（pages/posts/hot.vue:139）、`GET /posts/{slug}`（up:65）、`GET /posts/{slug}/adjacent`（pages/posts/[slug].vue:230）、`GET /posts/{post_id}/similar`（up:94）、`POST /posts`（up:109）、`PUT /posts/{post_id}`（up:119 区域，edit 流）、`DELETE /posts/{post_id}`（up:129）、`POST /posts/{post_id}/like`（up:103、pages/posts/[slug].vue:1154）、`POST /posts/batch-status`（up:135、pages/admin/content/posts/index.vue:171）、`GET /posts/{post_id}/edit`（pages/admin/content/posts/[id]/edit.vue:35）、`GET/POST /posts/{post_id}/comments`（ucm:25,60、uam:341）、`GET /categories` + `POST/PUT/DELETE /categories/{id}`（pages/index.vue:1088、uam:590–614）、`GET /categories/slug/{slug}`（pages/categories/[slug].vue:188）、`GET /tags` 及 `POST/PUT/DELETE /tags/{id}`（pages/index.vue:1092、uam:619–640）、`GET /tags/slug/{slug}`（pages/tags/[slug].vue:168）、`GET /archive`（pages/archive.vue:180）、`GET /site-stats`（pages/index.vue:1096）
🟡（5，仅 Nitro BFF）：`GET /rss`（NSR/rss.xml.get.ts:36）、`GET /sitemap.xml`（NSR/sitemap.xml.get.ts:13）、`GET /sitemap-posts.xml`（NSR/sitemap-posts.xml.get.ts:20）、`GET /sitemap-taxonomies.xml`、`GET /sitemap-pages.xml`（各 .get.ts:10）
❌（11，**真实缺口**或刻意保留）：`GET /posts/recommended`（推荐流后端已具备、前端未接入——缺口）、`GET /posts/id/{post_id}`（与 slug 版重复——建议统一的别名）、`GET /users/me/comments · /likes · /stats · /posts · /history` 与 `DELETE /users/me/history`（共 6 个：个人中心页未建，前端不存在消费场景——功能预留）、`GET /archive/{year}`、`GET /archive/{year}/{month}`、`GET /archive/stats`（归档页只用 `/archive` 全量分组，年/月下钻与统计无消费方）。

### users（/api/users）— 7/22 覆盖

✅：`POST /login`（sa:95、uoo:1011）、`POST /register`（sa:124）、`POST /refresh`（sa:194）、`POST /logout`（sa:139）、`GET /me`（sa:75）、`PUT /me/avatar`（sa:164）、`GET /users/`（用户列表，uam:405）
❌（15）：`PUT /me`、`POST /password-reset-request`、`POST /password-reset`、`POST /me/password`、`POST /me/change-password`、`GET/PUT /me/preferences`、`DELETE /me`、`PUT /me/cover`、`GET /{user_id}`、`GET /username/{username}`、`GET /username/{username}/preferences`、`GET /{user_id}/posts · /comments · /stats`。
判定：**成体系的真实缺口**——前端没有"用户中心/账号设置/他人主页"页面（pages/ 下仅 settings.vue 且不调这些接口），改密、密码找回、偏好设置均无 UI。

### core（/api）— 16/19 覆盖

`GET /pages`（uam:805）`GET /pages/{slug}`（pages/page/[slug].vue:67、pages/[slug].vue:155）、`POST /pages`（uam:834）、`PUT/DELETE /pages/{id}`（uam:838,842）、`GET /navigations`（components/AppHeader.vue:121）、`POST/PUT/DELETE /navigations/{id}`（uam:1256–1264）、`GET /admin/navigations`（uam:1218）、`GET /friend-links`（ufl:11）、`POST /friend-links`（uam:1300）、`PUT/DELETE /friend-links/{id}`（uam:1304,1308）、`GET /search-placeholders`（pages/posts/index.vue:218）、`GET /config`（us:285）
❌（3）：`GET /sponsors`、`GET /config/full`、`POST /admin/settings`——原先仅被已删除的 `useCore.ts` 名义消费，全站无真实调用方（settings 走 `PATCH /settings/{group}`）。

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

✅：`POST /upload`（umd:20）、`POST /upload/stream`（umd:26）、`POST /avatar`（umd:32）、`POST /cover`（umd:38）、`GET /library`（umd:52、uam:1081）、`GET /library/stats`（umd:56、uam:1104）、`POST /library`（umd:65）、`GET/PUT/DELETE /library/{id}`（umd:72,76,83、uam:1080）、`DELETE /library/batch`（umd:89、uam:1084；响应含 `deleted_count` / `refused[{id,reason}]` / `missing_ids`，前端 `pages/admin/media/library.vue` 按三种结果分别 toast，不得只看 `success`）
🟡：`GET /{category}/{filename}`——媒体文件直链回源路径（正常 URL 由后端返回、部分场景拼接消费）
❌（3）：`POST /library/upload`（与 upload+library 两步流重复——建议统一）、`DELETE /{category}/{filename}`（后台删除走 `/library/{id}`，此裸文件删除为保留能力）、`GET /bing-wallpaper`（**2026-09-26 转为未消费**：前台壁纸统一走 Nitro BFF `server/api/bing-wallpaper.get.ts`（30m SWR + 无 CORS），其零调用的 `useServerBingWallpaper` 包装已删除；后端代理保留给非 Nuxt 消费方）

### avatar_proxy — 1/1 ✅

`GET /api/media/avatar?src=`：`composables/useResolvedAvatar.ts:130,150`（URL 拼接 + fallback 回退）

### comments（/api）— 6/8

✅：`GET /comments/{id}/replies`（ucm:39,172）、`POST /comments/{id}/like`（ucm:74）、`POST /admin/comments/{id}/approve|reject|spam`（ucm:94,100,106）、`POST /admin/comments/batch`（ucm:112）
❌（2，**重复别名**）：`GET /posts/{post_id_or_slug}/comments`、`POST /posts/{post_id_or_slug}/comments`——前端统一走 `/blog/posts/{id}/comments`（blog.py 版），此处为同源旧实现，建议统一后下线。`DELETE /comments/{id}` 亦无用户侧调用（用户删评论缺口，管理端删除走 `/admin/comments/{id}`）。→ 计入 ❌ 的 2 条为两个 posts 别名。

### comment_reactions（/api）— 3/3 ✅

`GET/POST/DELETE /comments/{id}/reactions[/{emoji}]`（ucm:48,80,87）

### activity（/api）— 6/8

✅：`GET /activities`（pages/activity.vue:258）、`GET/POST /admin/activities`、`PUT/DELETE /admin/activities/{id}`（uam:979–996）
❌（2）：`POST /activities/{id}/like`（前端未做点赞按钮——小缺口）、`PUT /admin/activities/{id}/toggle`（后台用 PUT 详情代替——重复入口）

### announcement（/api）— 4/6

✅：`GET/POST /admin/announcements`、`PUT/DELETE /admin/announcements/{id}`（uam:930–958；后台开关以 PUT 实现，pages/admin/interaction/announcements.vue:468）
❌（2）：`GET /announcements`（公开横幅位未接入——功能预留）、`PUT /admin/announcements/{id}/toggle`（被 PUT 详情替代——重复入口）

### hero（/api）— 0/6

❌（6）：`GET /hero/slides` 与 `/admin/hero/slides` 全家桶（GET/POST/PUT/DELETE/toggle）——`GET /hero/slides` 原先只被已删除的 `useCore.ts` 名义消费、无真实调用方；后台亦无轮播管理页，前端真实缺口（首页 hero 数据当前由 settings 驱动）。

### post_series（/api）— 6/8

✅：`GET /series`（pages/series/index.vue:144）、`GET /series/{slug}`（pages/series/[slug].vue:223）、`GET/POST /admin/series`（uam:742,753）、`PUT/DELETE /admin/series/{id}`（uam:767,776）
❌（2）：`PUT /admin/series/{id}/toggle`（后台用 PUT 代替——重复入口）、`POST /post_series/complete`（"标记系列完成"无 UI——小缺口）

### ranking / stats / translate / docs / settings_groups

✅：`GET /api/admin/stats`（uam:147，仪表盘）；`POST /api/translate`（uam:1548，pages/admin/tools/translate.vue）；`GET /api/docs/list` · `/docs/{slug}`（udc:63,101，后台文档中心）；settings：`GET /api/settings`（uam:662）、`GET /api/settings/public`（us:298）、`PATCH /api/settings/{group}`（uam:670）。❌：`GET /api/settings/{group}`（有 GET 全量后不再需要——重复入口）、`GET /api/ranking/posts`（热门榜实际走 `GET /blog/posts/hot`，`useRanking` 随 useCore 一并删除，无调用方）。

### webhook（/api/webhooks）— 9/9 全覆盖 ✅

`GET /`（uam:1427）、`GET /events`（uam:1436，事件名下拉的唯一来源，页面不再硬编码）、`POST /`（uam:1441）、`PUT/DELETE /{id}`（uam:1446,1451）、`POST /{id}/test`（uam:1460）、`GET /{id}/deliveries`（uam:1476）、`POST /deliveries/{id}/retry`（uam:1484）、`POST /{id}/regenerate-secret`（uam:1493）；后台页 pages/admin/system/webhooks.vue（投递记录 Dialog + 一次性明文密钥展示/复制）

> 2026-09-26 契约收口：三张读接口补上 `response_model`（列表此前会把 `is_active`、明文 `secret` 等未声明字段直接吐给前端，页面靠 mapper 兜），`provider` 落库（新增迁移 `20260926_000001`），启停开关的 body key 与模型列对齐（此前 PUT 读 `is_active`、前端发 `active`，开关永远存不上），事件名清单由 `GET /events` 单源提供。投递链路（hooks 总线 → `trigger_webhook`）此前无调用方，现由 `tests/test_webhook_dispatch.py` 钉住。

### notification（/api/notifications）— 7/7 全覆盖 ✅

列表/未读数/统计/已读/全部已读/删除/清空（uam:1851–1901；顶栏铃铛消费）

### oobe（/api/oobe）— 8/16

✅：`GET /status · /check · /system-info · /dependencies`、`POST /install-dependencies`、`GET /install-dependencies/stream`（SSE）、`POST /install`、`GET /install/stream`（SSE）（uoo:551–618,1011）
❌（8，**刻意保留**）：向导实际把建库/站点/管理员合并进 `POST /install` 单调用，旧分步接口 `GET /state`、`POST /environment`、`POST /database-config`、`GET /test-database`、`POST /site-config`、`GET /check-username`、`POST /admin-account`、`POST /reset` 为旧流程与恢复工具保留（reset 有运维价值，无 UI 属预期）。
> 2026-09-26：`POST /complete` 已删除。它自标注 deprecated、前后端零调用，且与 `/install` 是两套并行的初始化实现（行为早已漂移：`/complete` 里示例数据失败被 `except` 吞掉，`/install` 里会中止安装）。留着的代价是维护一份没人走的安装路径，`tests/test_api_oobe.py::test_oobe_legacy_complete_endpoint_removed` 钉住 404 防止回潮。

### advanced（/api/admin）— 1/11

✅：`GET /logs`（uam:1611，pages/admin/tools/audit-logs.vue）
❌（10，**成片真实缺口/半成品**）：`GET /trash`、`POST /trash/{id}/restore`、`DELETE /trash/{id}`、`DELETE /trash`（回收站 UI 未建，评论"trash"状态仅走 status 字段）、`POST /posts/batch`（批量被 `/blog/posts/batch-status` 替代——重复；无 UI 消费，但 add_tag / remove_tag 分支曾因未 eager load `Post.tags` 而稳定 500，现已修复并由 `tests/test_post_batch_actions.py` 全量覆盖）、`GET /posts/{id}/revisions · /revisions/compare · /revisions/{rid}`、`POST /posts/{id}/revisions/{rid}/restore`（文章版本历史无 UI——功能预留）、`GET /logs/export`（导出按钮未做）

### admin_logs / admin_tools / migration / performance（均 /api/admin）

- admin_logs ❌1：`DELETE /logs/retention`（保留策略清理无 UI——小缺口）
- admin_tools ✅4：`GET/POST /alembic/status|upgrade`、`GET/POST /cache/status|flush`（uam:1666–1804；pages/admin/tools/migrations.vue:580,761、cache.vue:390,410）。`/alembic/status` 读取失败一律 500，**不返回** `is_latest=true` 的空壳 200；前端 `loadStatus()` 的 catch 写 `statusError` 并展示『取不到状态 ≠ 已是最新』的错误态（`tests/test_api_admin_tools.py` 两侧都钉住）
- migration ✅4：`POST /start`、`GET /status`、`POST /cancel`、`GET /presets`（uam:1741–1768）
- performance ✅4：`GET /performance/summary`（uam:1569）、`GET /slow · /storage`、`DELETE /cleanup`（pages/admin/tools/performance.vue:672,794,812）

### import_export（/api/admin）— 4/7

✅：`GET /export/posts|markdown`、`POST /import/posts|markdown`（uam:1465,1493；pages/admin/tools/import-export.vue:760,818）
❌（3，**运维保留**）：`GET /backup/info`、`GET /backup/full`、`POST /backup/restore`——整库备份 UI 未建（有意留给部署脚本，防止误操作）。三端已由 `tests/test_import_export_api.py` 覆盖（含"备份包不含密码哈希"断言）；`POST /import/posts` 与 `/backup/restore` 的标签关联语义同见该测试：标签只能在 `Post(...)` 构造器一次性传入，flush 后 `post.tags.append()` 在 async 会话里必抛 `MissingGreenlet`（旧实现即如此，导入带标签的文章从未成功过）。

### seo（/api/seo）— 5/9

✅：`POST /sitemap/generate`（uam:1534、tools/seo.vue:627）、`GET /sitemap-check`（uam:1515、:610）、`GET /scores`（uam:1522、:663）。❌：`GET /schema/{type}/{id}`、`GET /open-graph/{type}/{id}`（原先仅被已删除的 `useSeoPublic` 名义消费，无真实调用方——SEO 结构化数据当前由 Nitro 侧与 useSeo 生成）。
🟡：`GET /sitemap.xml`（NSR/sitemap.xml.get.ts）、`GET /robots.txt`（NSR/robots.txt.get.ts:21）
❌（2）：`GET/PUT /config`——SEO 配置读写已被 `/api/settings/{seo 组}` 通道替代（**重复入口，建议统一**）

### themes / themes_ext / plugins

- themes（/api）1/4：✅ `GET /themes/active`（uft:661）；❌ `GET /themes/palettes`、`GET /themes/current.css`、`PUT /admin/themes/current`——旧调色板体系，被主题 Customizer（mods）取代，**遗留待清理**。
- themes_ext（/api/admin/themes）6/12：✅ 列表 GET（TM:200 及 ?source=local/remote/upload 查询）、`POST /scan`（TM:220）、`PUT /{slug}/activate`（TM:251）、`PATCH /{slug}/mods`（TM:359）、`DELETE /{slug}`（TM:387）、`POST ""?source=…` 安装（TM:455–473）。❌6：`GET /{slug}` 详情、`GET|PUT /{slug}/mods`（列表内联返回 + PATCH 替代）、`POST /{slug}/upgrade`、`GET /market`、`POST /market/{slug}/install`——市场为**半成品功能**（后端就绪、UI 未接）；upgrade 主题侧缺失（插件侧已有）。
- plugins（/api/admin/plugins）11/16：✅ 列表（PM:207）、`POST /scan`（:224）、`PATCH /{slug}/status`（:235）、`GET /menu-registry`（upm:67）、`GET|PUT /{slug}/settings`（plugins/guestbook-rss/settings.vue:75,90）、`PATCH /{slug}/settings`（PM:267）、`POST /bulk`（:295,314）、`GET /{slug}` 详情（settings.vue:61）、`DELETE /{slug}`（:292）、`POST /{slug}/upgrade`（:341）。❌5：`POST ""` zip 上传安装（当前仅扫描本地目录安装——小缺口）、`GET /market`、`POST /market/{slug}/install`（市场未接，同上）、`POST /{slug}/activate|deactivate`（被 status PATCH 替代——**重复入口，建议统一**）。

### title（/api/admin 下 titles）— 6/9

✅：`GET/POST /titles`（uam:1011,1019）、`PUT /titles/{id}`（:1024）、`DELETE /titles/{id}`（:1033，204 空响应）、`POST /titles/assign`（:1044）、`DELETE /users/{id}/title`（:1049 `removeAdminUserTitle` → pages/admin/users/[id]/edit.vue:646）
> 2026-09-27：`assignAdminUserTitle` 原来在 `titleId=null` 时直接 `Promise.resolve({success:true,message:'已移除头衔'})`——
> 一条从未发出的假成功；现拆成 assign（必传 number）+ remove 两个真实端点包装，编辑页也不再裸写 `apiFetch`。
> 同日后端 `PATCH/PUT /titles/{id}` 补了 NOT NULL 守卫：显式 `"color": null` 返回 422「称号颜色不能为空」，不再走到 flush 撞 500。
❌（3）：`GET /titles/{id}`（列表含全量，详情无场景——重复）、`PATCH /titles/{id}`（与 PUT 同一 handler——**重复入口**，但已被 `tests/test_api_titles.py` 覆盖校验语义）、`GET /users/{id}/title`（编辑页从用户响应内联取——可接受；注意它只要求登录，任何用户可查他人称号，称号本身是公开档案字段）

### 整模块未消费（后端能力已交付、前端尚无 UI）

| 模块 | 端点数 | 明细与判定 |
|---|---:|---|
| favorite（/api/favorites） | 12 | 文件夹 CRUD、收藏列表/增删改、按文章操作、check。**真实缺口**：无"我的收藏"页面；后端为注册用户互动体系预留 |
| messages（/api/messages） | 6 | 会话列表、未读数、历史、发送、已读、全部已读。**真实缺口**：无私信 UI（需配套用户体系完善后接入） |
| monitoring（/api/monitoring） | 8 | health/stats/visits/performance/db/cache/trends。刻意保留：Admin 监控面板当前由 `/admin/stats` + `/admin/performance/*` + `/admin/cache/status` 覆盖，此模块为深度诊断接口（运维经 docs/工具页直访） |
| captcha（/api/captcha） | 2 | 图形验证码生成/校验。注册登录暂未接入（后端已支持，防滥用开关未开）——**待接入缺口** |
| shortcodes（/api） | 5 | 渲染/注册/管理短代码。编辑器未提供短代码面板——功能预留 |
| toc（/api/toc） | 3 | 目录生成/抽取/加锚点。前端 Markdown 渲染本地生成目录，未调后端——重复能力，建议二选一 |
| scheduled_posts（/api） | 3 | 定时发布列表/改期/取消。前端以 `status=scheduled` + PUT 文章实现——**重复入口，建议统一** |
| post_encryption（/api） | 4 | 文章加密设置 CRUD + 解密。**缺口**：OOBE 已有 `enable_encrypted_posts` 开关，但编辑器无加密设置 UI |
| post_crypto（/api/post_crypto） | 3 | 派生密钥/验证访问/加密预览（配套上一篇的读者侧流程）。同上，随加密 UI 一起接入 |
| admin_logs（/api/admin/logs/retention） | 1 | 日志保留清理。运维保留（可接定时任务，不需要 UI） |

### bing / bing_image（壁纸代理体系）

- ✅：`GET /api/bing/wallpapers`（ubw:221,285，登录页/OOBE 背景）、`GET /api/bing/image`（ubw:156 拼 `<img>` 直链，流式代理+本地缓存）
- ❌（3）：`GET /api/bing/wallpaper`（单数版与复数版重复——**建议统一**）、`GET /api/bing/image/today · /archive`（归档骨架未接，Nitro 侧 `server/api/bing-wallpaper.get.ts` 直连 cn.bing.com 未走此接口）

### docs（/api/docs）— 2/2 ✅ · translate — 1/1 ✅ · ranking/stats — 全覆盖 ✅

***

## 结论

**总体：351 端点 / 46 模块，前端已覆盖 208（59.3%），其中 8 个仅 Nitro/直链消费。** 未覆盖的 143 个可分三类：

1. **刻意保留的后端能力（约六成，不算债）**：
   - 重复入口族（**建议统一，长期二选一**）：comments.py 的 posts 别名 ×2、`seo GET/PUT /config`、`scheduled_posts` ×3（前端用 status 字段替代）、`themes/palettes` 旧调色板 ×3、plugins `activate/deactivate` ×2、`PATCH /titles/{id}`、`/posts/batch`、`/archive` 单数 bing wallpaper、各 `…/toggle` ×4、`GET /titles/{id}`、`GET /settings/{group}`、`media /library/upload`、toc ×3（前端本地生成）。
   - 运维/脚本面：admin tools ×5、`import_export backup` ×3、`admin_logs retention`、`oobe` 旧分步 ×8（合并进单 `POST /install`，reset 为恢复工具；`/complete` 已于 2026-09-26 删除）。
2. **半成品（后端就绪、UI 半接入）**：主题/插件**市场**（market GET/install ×4）、主题 upgrade（×1，插件侧已接）、zip 上传安装（×1）。（webhook 原列此项，2026-09-26 已补齐投递日志与密钥轮换 UI，转 100%。）
3. **真实缺口（需要排期的功能面）**，最突出的三块：
   - **用户体系外围**（users 15 个 + blog users/me 系 6 个 + favorite 12 + messages 6）：个人中心/改密/密码找回/收藏/私信整块无页面；
   - **后台运维增强**：回收站 UI（advanced trash ×4）、文章版本历史（revisions ×4）、日志导出、hero 轮播管理（×5）；
   - **内容保护与防滥用**：文章加密（post_encryption + post_crypto ×7）、captcha 接入（×2）。

> 建议：① 优先补齐 users/favorite 系（注册功能已有账号，缺"我的"页面是最大体验空洞）；② 对"重复入口"做一次后端归并 + 本表同步，压缩端点分母；③ 主题/插件市场只差前端 Tab，投入产出比高。

— 本报告由静态扫描生成（2026-09-26），新增/删除端点后请重跑扫描，勿手改数字。
