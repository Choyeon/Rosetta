# Rosetta Admin 全量重建 Spec

> Status: ALIGNED
> Author: ChuyuChoyeon
> Last updated: 2026-08-18

## Background
现有 Rosetta Admin 仅 8 页面骨架，后端 37 API 模块 ~180 端点覆盖率不足 40%，前台 11 页面对应功能（友链、相册、动态、独立页面、公告、导航、Webhook、导入导出、SEO、翻译、性能监控、操作日志）均无管理入口。UI 风格未对齐 Editorial Warm Stone（赭石/胡桃木/竹青/靛青）暖色调。

## In scope
- 删除现有 `frontend/pages/admin/*`（8 页面）、`frontend/components/{AdminHeader,AdminSidebar,AdminAvatarCropper}.vue`、`frontend/components/admin/*`、`frontend/layouts/admin.vue`
- 重建统一 admin 骨架：layouts/admin.vue + AdminHeader.vue + AdminSidebar.vue + composables/useAdminManage.ts（统一 API 层）
- 按 7 功能分组重建 22 个页面（所有页面 definePageMeta({ ssr: false }) SPA 模式）
- 严格对齐后端 37 模块 API 端点契约（{success,data} 包装）
- UI 统一 Editorial Warm Stone + iOS26 风格：暖色调 CSS 变量、flat 卡片（无左色条）、iOS26 圆角按钮（12px）、极简标签胶囊、不做 ThemePaletteSwitcher（已删）
- i18n 同步 4 语言包（zh/en/ja/zh_Hant）admin.* 键名，统一嵌套结构

功能分组与页面清单（22 页）：
1. 仪表盘组：/admin/index.vue（统计卡片+趋势图+TOP榜+系统健康）
2. 内容管理组（7）：/admin/content/posts/index.vue, /admin/content/posts/new.vue, /admin/content/posts/[id]/edit.vue, /admin/content/categories.vue, /admin/content/tags.vue, /admin/content/series.vue, /admin/content/pages.vue
3. 互动管理组（4）：/admin/interaction/comments.vue, /admin/interaction/guestbook.vue, /admin/interaction/announcements.vue, /admin/interaction/activities.vue
4. 用户与权限组（3）：/admin/users/index.vue, /admin/users/[id]/edit.vue, /admin/users/titles.vue
5. 媒体资源组（2）：/admin/media/library.vue, /admin/media/gallery.vue
6. 系统配置组（4）：/admin/system/settings.vue, /admin/system/navigation.vue, /admin/system/friendlinks.vue, /admin/system/webhooks.vue
7. 工具与运维组（7）：/admin/tools/import-export.vue, /admin/tools/seo.vue, /admin/tools/translate.vue, /admin/tools/performance.vue, /admin/tools/audit-logs.vue, /admin/tools/migrations.vue, /admin/tools/cache.vue

## Out of scope
- 不做后端 API 改动（如缺失端点先用 toast 提示接口未实现占位，不影响导航可达）
- 不做 SSR 开启（/admin/* 全程 SPA）
- 不新增 ru/ko 语言包（仅 zh/en/ja/zh_Hant）
- 不做 navbar ThemePaletteSwitcher（永久移除）
- 不实现 Electron 打包（本 spec 仅 Web Admin）

## Assumptions
- 后端 FastAPI 服务已在 localhost:8000 运行，mock_data.py 已注入 admin123 管理员账号
- 现有 composables/useApi.ts 的 401 refresh + 503 OOBE 跳转逻辑正确
- 现有 stores/auth.ts 的 admin 判定（is_staff || is_superuser）正确
- shadcn-vue 组件（components/ui/*）齐全可用
- 4 个 i18n 语言包加载器在 i18n.config.ts / i18n/index.ts 中正确配置

## Solution
### 目录结构
```
frontend/
├── layouts/admin.vue                    统一骨架（SidebarProvider + SidebarInset + AdminHeader + slot）
├── components/
│   ├── admin/
│   │   ├── AdminSidebar.vue             侧边栏 7 组菜单
│   │   ├── AdminHeader.vue              顶栏（面包屑+搜索+通知+主题切换+用户菜单，无调色板）
│   │   ├── AdminAvatarCropper.vue       头像裁剪
│   │   ├── MarkdownEditor.vue           Markdown 编辑器（粘图+全屏+3模式）
│   │   ├── PostForm.vue                 文章表单（多语言+草稿+预览）
│   │   ├── DataTable.vue                通用分页表格（筛选+批量+搜索）
│   │   └── StatCard.vue                 仪表盘统计卡片（8 种语义色）
├── composables/useAdminManage.ts        统一 API 层（22 模块，apiFetch + {success,data} 解包）
├── pages/admin/
│   ├── index.vue                        仪表盘
│   ├── content/
│   │   ├── posts/index.vue, posts/new.vue, posts/[id]/edit.vue
│   │   ├── categories.vue, tags.vue, series.vue, pages.vue
│   ├── interaction/
│   │   ├── comments.vue, guestbook.vue, announcements.vue, activities.vue
│   ├── users/
│   │   ├── index.vue, [id]/edit.vue, titles.vue
│   ├── media/
│   │   ├── library.vue, gallery.vue
│   ├── system/
│   │   ├── settings.vue, navigation.vue, friendlinks.vue, webhooks.vue
│   └── tools/
│       ├── import-export.vue, seo.vue, translate.vue, performance.vue
│       ├── audit-logs.vue, migrations.vue, cache.vue
```

### UI 规范（Editorial Warm Stone）
通过 `main.css` 的 `--ochre-* / --walnut-* / --sage-* / --indigo-*` 语义变量覆盖 shadcn 默认色：
- Light bg: radial-gradient(#fdfaf0 → #f7f1e1) + linear-gradient(#f7f1e1 → #f3ecda)
- Dark bg: #13130f → #181612
- accent: linear-gradient(135deg,#d4a373,#b3763c 48%,#6b8e7f)
- 卡片：border: 1px solid var(--border-ochre-100), box-shadow: 0 1px 2px rgba(0,0,0,.04)
- 按钮：border-radius: 12px，hover 背景暗化 6%，active 暗化 12%，translateY(0)
- Badge 标签：10% 原色 + 90% 白 bg，原色文字，0.85rem 500w，border: 0，hover 背景 +8%

## Edge cases & risks
| Category | Notes | Mitigation |
|---|---|---|
| API 缺失端点 | 后端 37 模块中部分接口可能未实现 | 所有 API 调用 try/catch，失败时 toast.error(msg) + loading=false，页面不崩 |
| 401 token 过期竞态 | useApi.ts 已处理 refresh 队列 | 严格走 apiFetch / useAPI，不裸写 $fetch |
| 导航 404 | 22 页面多，易漏路由 | 侧边栏菜单点击前先 navigateTo 失败回退提示 |
| i18n 缺键 | 4 语言包同步难 | 缺失键显示英文 fallback，不影响功能 |
| 暗色模式样式 | 大量表格/表单易漏 dark 样式 | 统一 CSS 变量，不写 hardcode 颜色值 |

## Acceptance criteria
- AC-1 侧边栏 7 组菜单全部可点击导航，无 404（/admin → /admin/tools/cache 全覆盖）
- AC-2 每个列表页：分页、搜索、筛选、CRUD 按钮存在且点击无红屏（接口未实现时仅 toast）
- AC-3 表单页：必填校验、提交 loading、成功/失败 toast 反馈
- AC-4 仪表盘 8 个 StatCard 无报错渲染，趋势图容器（ECharts/Recharts）已占位
- AC-5 pnpm typecheck (frontend/) 通过，0 TS 错误
- AC-6 pnpm lint (frontend/) 通过，0 ESLint error
- AC-7 明/暗主题切换后，所有页面文字对比度 ≥ 4.5:1（无看不清的浅色文字）
- AC-8 中间件 admin.global.ts 拦截 /admin/* 有效：未登录 → /login，非 admin → /

## Open questions
None. 自动执行模式，全部按 spec 默认实现。

## Core entities (ontology)
| Entity | Type | Key fields | Relationship |
|---|---|---|---|
| Post | Content | id, slug, title(i18n), content(i18n), status, category_id, tags[] | N:1 Category, N:M Tag, N:1 Author(User) |
| Category / Tag | Content Taxonomy | id, name(i18n), slug, color, icon, posts_count | 1:N Post |
| Series | Content Group | id, name(i18n), description, cover, sort_order | N:M Post via series_posts |
| Comment / Guestbook | Interaction | id, post_id(null=留言板), author, content, status, parent_id | N:1 Post, 1:N Self(replies) |
| Announcement / Activity | Interaction | id, type, title, content(i18n), is_pinned, created_at | 独立展示 |
| User / UserTitle | Auth | id, username, email, role(staff/superuser), title_id | 1:1 Title |
| Media / Album / Photo | Media | id, url, mime, size, album_id, uploaded_by | Album 1:N Photo |
| SiteConfig (17 groups) | System | group_key (basic|reading|...|footer), value(JSON) | 全局单例 per group |
| OperationLog | Audit | id, user_id, action, target, ip, created_at | N:1 User |
| PerformanceMetric | Observability | id, path, method, duration_ms, status_code, created_at | 时序记录 |
