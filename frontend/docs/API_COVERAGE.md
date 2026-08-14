# Rosetta API 覆盖度报告

> 生成时间：2026-08-14  
> 数据源：后端 `api_reference.md` + `backend/api/*.py` 路由扫描 + 前端 `composables/` 导出函数对照

## 总览

| 模块 | 后端 API 数 | 前端已实现 | 覆盖率 |
|------|------------|------------|--------|
| 用户模块 (users) | 21 | 11 | 52% |
| 博客模块 (blog) | 21 | 13 | 62% |
| 核心模块 (core) | 18 | 6 | 33% |
| 媒体模块 (media) | 13 | 0 | 0% |
| 评论模块 (comments) | 8 | 2 | 25% |
| OOBE 模块 | 17 | 7 | 41% |
| 后台管理 (admin) | 25 | 0 | 0% |
| 收藏模块 (favorites) | 12 | 0 | 0% |
| 通知模块 (notifications) | 7 | 0 | 0% |
| 私信模块 (messages) | 6 | 0 | 0% |
| 留言板 (guestbook) | 10 | 0 | 0% |
| 翻译模块 (translate) | 1 | 0 | 0% |
| SEO 模块 | 7 | 0 | 0% |
| 网站动态 (activity) | 8 | 0 | 0% |
| Hero 轮播 | 6 | 0 | 0% |
| 公告模块 (announcement) | 6 | 0 | 0% |
| 文章系列 (series) | 8 | 0 | 0% |
| 相册模块 (gallery) | 10 | 0 | 0% |
| 投票模块 (voting) | 5 | 0 | 0% |
| 热门排行 (ranking) | 1 | 0 | 0% |
| Webhook 模块 | 9 | 0 | 0% |
| 导入导出 | 7 | 0 | 0% |
| 高级管理 (advanced) | 11 | 0 | 0% |
| 监控模块 (monitoring) | 8 | 0 | 0% |
| 内容加密 (encryption) | 7 | 0 | 0% |
| 定时发布 | 3 | 0 | 0% |
| 评论表情反应 | 3 | 0 | 0% |
| 称号系统 (title) | 8 | 0 | 0% |
| 性能监控 (performance) | 4 | 0 | 0% |
| TOC 目录生成 | 3 | 0 | 0% |
| 验证码 (captcha) | 2 | 0 | 0% |
| Bing 壁纸 | 2 | 0 | 0% |
| 头像代理 | 1 | 0 | 0% |
| 系统设置分组 (settings_groups) | 3 | 0 | 0% |
| **合计** | **274** | **39** | **14%** |

---

## 一、用户模块 `/api/users`

| # | HTTP 方法 | 路径 | 功能 | 前端 Composable | 覆盖状态 |
|---|-----------|------|------|-----------------|----------|
| 1 | POST | `/register` | 用户注册 | stores/auth.ts → register() | ✅ 已实现 |
| 2 | POST | `/login` | 用户登录 | stores/auth.ts → login() | ✅ 已实现 |
| 3 | POST | `/refresh` | 刷新令牌 | stores/auth.ts → refreshAccessToken() | ✅ 已实现 |
| 4 | POST | `/password-reset-request` | 请求密码重置 | - | ❌ 未实现 |
| 5 | POST | `/password-reset` | 重置密码（验证码+新密码） | - | ❌ 未实现 |
| 6 | POST | `/logout` | 用户登出 | stores/auth.ts → logout() | ✅ 已实现 |
| 7 | GET | `/me` | 获取当前用户 | stores/auth.ts → fetchUser() | ✅ 已实现 |
| 8 | PUT | `/me` | 更新个人信息 | - | ❌ 未实现 |
| 9 | POST | `/me/password` | 修改密码（新路径） | - | ❌ 未实现 |
| 10 | POST | `/me/change-password` | 修改密码（旧路径） | - | ❌ 未实现 |
| 11 | GET | `/me/preferences` | 获取个人偏好 | - | ❌ 未实现 |
| 12 | PUT | `/me/preferences` | 更新个人偏好 | - | ❌ 未实现 |
| 13 | GET | `/{user_id}` | 获取指定用户信息 | useUsers.ts → getUser() | ✅ 已实现 |
| 14 | GET | `/username/{username}` | 通过用户名获取用户 | useUsers.ts → getUserByUsername() | ✅ 已实现 |
| 15 | GET | `/username/{username}/preferences` | 获取用户隐私设置（公开） | - | ❌ 未实现 |
| 16 | GET | `/` | 用户列表（分页+搜索） | - | ❌ 未实现 |
| 17 | DELETE | `/me` | 注销账户（需密码） | - | ❌ 未实现 |
| 18 | PUT | `/me/avatar` | 更新头像 URL | - | ❌ 未实现 |
| 19 | PUT | `/me/cover` | 更新封面图 URL | - | ❌ 未实现 |
| 20 | GET | `/{user_id}/posts` | 用户文章列表 | useUsers.ts → getUserPosts() | ✅ 已实现 |
| 21 | GET | `/{user_id}/comments` | 用户评论列表 | useUsers.ts → getUserComments() | ✅ 已实现 |
| 22 | GET | `/{user_id}/stats` | 用户统计信息 | useUsers.ts → getUserStats() | ✅ 已实现 |

---

## 二、博客模块 `/api/blog`

| # | HTTP 方法 | 路径 | 功能 | 前端 Composable | 覆盖状态 |
|---|-----------|------|------|-----------------|----------|
| 1 | GET | `/posts` | 文章列表（分页/分类/标签/搜索/lang） | usePosts.ts → getPosts() / fetchPosts() | ✅ 已实现 |
| 2 | GET | `/posts/recommended` | 推荐文章列表 | usePosts.ts → getRecommendedPosts() | ✅ 已实现 |
| 3 | GET | `/posts/{post_id}/similar` | 相似文章推荐 | usePosts.ts → getSimilarPosts() | ✅ 已实现 |
| 4 | GET | `/posts/{slug}` | 文章详情（slug + lang + password） | usePosts.ts → getPost() / fetchPost() | ✅ 已实现 |
| 5 | POST | `/posts` | 创建文章 | usePosts.ts → createPost() | ✅ 已实现 |
| 6 | PUT | `/posts/{post_id}` | 更新文章 | usePosts.ts → updatePost() | ✅ 已实现 |
| 7 | DELETE | `/posts/{post_id}` | 删除文章 | usePosts.ts → deletePost() | ✅ 已实现 |
| 8 | POST | `/posts/{post_id}/like` | 点赞/取消点赞 | usePosts.ts → likePost() | ✅ 已实现 |
| 9 | GET | `/categories` | 分类列表 | useCore.ts → useCategories().getCategories() | ✅ 已实现 |
| 10 | GET | `/categories/slug/{slug}` | 分类详情 | useCore.ts → useCategories().getCategory() | ✅ 已实现 |
| 11 | POST | `/categories` | 创建分类（管理员） | - | ❌ 未实现 |
| 12 | PUT | `/categories/{category_id}` | 更新分类（管理员） | - | ❌ 未实现 |
| 13 | DELETE | `/categories/{category_id}` | 删除分类（管理员） | - | ❌ 未实现 |
| 14 | GET | `/tags` | 标签列表 | useCore.ts → useTags().getTags() | ✅ 已实现 |
| 15 | GET | `/tags/slug/{slug}` | 标签详情 | useCore.ts → useTags().getTag() | ✅ 已实现 |
| 16 | POST | `/tags` | 创建标签（管理员） | - | ❌ 未实现 |
| 17 | PUT | `/tags/{tag_id}` | 更新标签（管理员） | - | ❌ 未实现 |
| 18 | DELETE | `/tags/{tag_id}` | 删除标签（管理员） | - | ❌ 未实现 |
| 19 | GET | `/archive` | 文章归档（按年月分组） | useCore.ts → useArchive().getArchive() | ✅ 已实现 |
| 20 | GET | `/archive/stats` | 归档统计 | useCore.ts → useArchive().getArchiveStats() | ✅ 已实现 |
| 21 | GET | `/archive/{year}` | 按年份获取归档 | useCore.ts → useArchive().getArchiveByYear() | ✅ 已实现 |
| 22 | GET | `/archive/{year}/{month}` | 按年月获取归档（分页） | useCore.ts → useArchive().getArchiveByMonth() | ✅ 已实现 |
| 23 | GET | `/site-stats` | 站点公开统计（字数/文章/分类/标签数） | useCore.ts → useSiteStats().getSiteStats() | ✅ 已实现 |
| 24 | GET | `/posts/{post_id}/comments` | 评论列表 | useUsers.ts → useComments().getComments() / fetchComments() | ✅ 已实现 |
| 25 | POST | `/posts/{post_id}/comments` | 发表评论 | useUsers.ts → useComments().createComment() | ✅ 已实现 |
| 26 | GET | `/rss` | RSS 订阅 | - | ❌ 未实现 |
| 27 | GET | `/sitemap.xml` | 站点地图 | - | ❌ 未实现 |

---

## 三、核心模块 `/api`

| # | HTTP 方法 | 路径 | 功能 | 前端 Composable | 覆盖状态 |
|---|-----------|------|------|-----------------|----------|
| 1 | GET | `/pages` | 页面列表（分页） | - | ❌ 未实现 |
| 2 | GET | `/pages/{slug}` | 页面详情 | - | ❌ 未实现 |
| 3 | POST | `/pages` | 创建页面（管理员） | - | ❌ 未实现 |
| 4 | PUT | `/pages/{page_id}` | 更新页面（管理员） | - | ❌ 未实现 |
| 5 | DELETE | `/pages/{page_id}` | 删除页面（管理员） | - | ❌ 未实现 |
| 6 | GET | `/navigations` | 导航列表（按 location 过滤） | useCore.ts → useNavigations().getNavigations() | ✅ 已实现 |
| 7 | POST | `/navigations` | 创建导航（管理员） | - | ❌ 未实现 |
| 8 | PUT | `/navigations/{nav_id}` | 更新导航（管理员） | - | ❌ 未实现 |
| 9 | DELETE | `/navigations/{nav_id}` | 删除导航（管理员） | - | ❌ 未实现 |
| 10 | GET | `/admin/navigations` | 管理员获取所有导航 | - | ❌ 未实现 |
| 11 | GET | `/friend-links` | 友链列表 | useCore.ts → useFriendLinks().getFriendLinks() | ✅ 已实现 |
| 12 | POST | `/friend-links` | 创建友链（管理员） | - | ❌ 未实现 |
| 13 | PUT | `/friend-links/{link_id}` | 更新友链（管理员） | - | ❌ 未实现 |
| 14 | DELETE | `/friend-links/{link_id}` | 删除友链（管理员） | - | ❌ 未实现 |
| 15 | GET | `/sponsors` | 打赏者列表 | - | ❌ 未实现 |
| 16 | GET | `/search-placeholders` | 搜索占位符文本 | - | ❌ 未实现 |
| 17 | GET | `/config` | 站点公开配置 | useCore.ts → useSiteConfig().getSiteConfig() | ✅ 已实现 |
| 18 | GET | `/config/full` | 完整站点配置（管理员，分组形式） | - | ❌ 未实现 |
| 19 | POST | `/admin/settings` | 更新站点设置（管理员） | - | ❌ 未实现 |
| 20 | GET | `/translate` | 翻译文本（POST 端点在独立路由） | - | ❌ 未实现 |

---

## 四、媒体模块 `/api/media`

| # | HTTP 方法 | 路径 | 功能 | 前端 Composable | 覆盖状态 |
|---|-----------|------|------|-----------------|----------|
| 1 | POST | `/upload` | 上传图片（multipart） | - | ❌ **高优未实现** |
| 2 | POST | `/upload/stream` | 流式上传（大文件） | - | ❌ 未实现 |
| 3 | POST | `/avatar` | 上传头像文件 | - | ❌ **高优未实现** |
| 4 | POST | `/cover` | 上传封面图文件 | - | ❌ **高优未实现** |
| 5 | GET | `/library` | 媒体库列表（分页/搜索/筛选） | - | ❌ 未实现 |
| 6 | GET | `/library/stats` | 媒体库统计 | - | ❌ 未实现 |
| 7 | POST | `/library/upload` | 上传到媒体库（支持多类型） | - | ❌ 未实现 |
| 8 | GET | `/library/{media_id}` | 媒体详情 | - | ❌ 未实现 |
| 9 | PUT | `/library/{media_id}` | 更新媒体信息（标题/描述/alt） | - | ❌ 未实现 |
| 10 | DELETE | `/library/{media_id}` | 删除单个媒体 | - | ❌ 未实现 |
| 11 | DELETE | `/library/batch` | 批量删除媒体 | - | ❌ 未实现 |
| 12 | GET | `/{category}/{filename}` | 获取图片文件（静态资源） | - | 浏览器直接访问 |
| 13 | DELETE | `/{category}/{filename}` | 删除图片文件 | - | ❌ 未实现 |
| 14 | GET | `/bing-wallpaper` | Bing 每日壁纸代理（批量） | - | ❌ 未实现 |
| 15 | GET | `/media/avatar` | 头像代理（QQ/GH 等） | - | 浏览器直接访问 |

---

## 五、评论模块 `/api` + `/api/admin/comments`

| # | HTTP 方法 | 路径 | 功能 | 前端 Composable | 覆盖状态 |
|---|-----------|------|------|-----------------|----------|
| 1 | GET | `/posts/{post_id_or_slug}/comments` | 获取文章根评论分页（含前3条回复） | - | ⚠️ 路径不一致（现有实现无 blog 前缀） |
| 2 | GET | `/comments/{comment_id}/replies` | 获取根评论的全部回复分页 | - | ❌ 未实现 |
| 3 | POST | `/posts/{post_id_or_slug}/comments` | 发表评论 | - | ⚠️ 路径不一致 |
| 4 | POST | `/comments/{comment_id}/like` | 给评论点赞（允许匿名） | - | ❌ 未实现 |
| 5 | POST | `/admin/comments/{comment_id}/approve` | 【管理员】批准评论 | - | ❌ 未实现 |
| 6 | POST | `/admin/comments/{comment_id}/reject` | 【管理员】拒绝评论 | - | ❌ 未实现 |
| 7 | POST | `/admin/comments/{comment_id}/spam` | 【管理员】标记垃圾评论 | - | ❌ 未实现 |
| 8 | POST | `/admin/comments/batch` | 【管理员】批量操作评论 | - | ❌ 未实现 |
| 9 | POST | `/comments/{comment_id}/reactions` | 添加评论表情反应 | - | ❌ 未实现 |
| 10 | DELETE | `/comments/{comment_id}/reactions/{emoji}` | 取消评论表情反应 | - | ❌ 未实现 |
| 11 | GET | `/comments/{comment_id}/reactions` | 获取评论表情反应统计 | - | ❌ 未实现 |

---

## 六、OOBE 模块 `/api/oobe`

| # | HTTP 方法 | 路径 | 功能 | 前端 Composable | 覆盖状态 |
|---|-----------|------|------|-----------------|----------|
| 1 | GET | `/status` | 获取 OOBE 状态 | useOOBE.ts → getOOBEStatus() | ✅ 已实现 |
| 2 | GET | `/state` | 获取当前 OOBE 详细状态 | - | ❌ 未实现 |
| 3 | GET | `/check` | OOBE 环境检测 | useOOBE.ts → checkEnvironment() / checkSystem() | ✅ 已实现 |
| 4 | GET | `/system-info` | 获取系统信息 | useOOBE.ts → getSystemInfo() | ✅ 已实现 |
| 5 | GET | `/dependencies` | 检查系统依赖状态 | useOOBE.ts → checkDependencies() | ✅ 已实现 |
| 6 | POST | `/install-dependencies` | 安装缺失的依赖 | useOOBE.ts → installDependencies() | ✅ 已实现 |
| 7 | POST | `/environment` | 保存环境选择（旧分步式兼容） | - | ❌ 未实现 |
| 8 | GET | `/install/stream` | OOBE 安装进度 SSE 流 | useOOBE.ts → getInstallStream() | ✅ 已实现 |
| 9 | POST | `/install` | OOBE 一键安装 | useOOBE.ts → install() / finishOOBE() | ✅ 已实现 |
| 10 | POST | `/database-config` | 保存数据库配置（旧分步式兼容） | - | ❌ 未实现 |
| 11 | GET | `/test-database` | 测试数据库连接 | - | ❌ 未实现 |
| 12 | POST | `/site-config` | 保存站点配置（旧分步式兼容） | - | ❌ 未实现 |
| 13 | GET | `/check-username` | 检查用户名是否可用 | - | ❌ **高优未实现** |
| 14 | POST | `/admin-account` | 保存管理员账户（旧分步式兼容） | - | ❌ 未实现 |
| 15 | POST | `/complete` | 完成 OOBE 配置（旧分步式兼容） | - | ❌ 未实现 |
| 16 | POST | `/reset` | 重置 OOBE 状态（测试用） | - | ❌ 未实现 |

---

## 七、后台管理 `/api/admin`

| # | HTTP 方法 | 路径 | 功能 | 前端 Composable | 覆盖状态 |
|---|-----------|------|------|-----------------|----------|
| 1 | GET | `/stats` | 仪表盘统计（posts/views/comments/users） | - | ❌ **高优未实现** |
| 2 | GET | `/view-trends` | 访问趋势（按天） | - | ❌ **高优未实现** |
| 3 | GET | `/category-stats` | 分类统计 | - | ❌ 未实现 |
| 4 | GET | `/users` | 用户列表（分页+搜索+筛选） | - | ❌ **高优未实现** |
| 5 | POST | `/users` | 创建用户（管理员） | - | ❌ 未实现 |
| 6 | GET | `/users/{user_id}` | 获取用户详情（管理员） | - | ❌ 未实现 |
| 7 | PUT | `/users/{user_id}` | 更新用户（管理员） | - | ❌ 未实现 |
| 8 | PATCH | `/users/{user_id}` | 部分更新用户（管理员） | - | ❌ 未实现 |
| 9 | POST | `/users/{user_id}/reset-password` | 重置用户密码 | - | ❌ 未实现 |
| 10 | DELETE | `/users/{user_id}` | 删除用户 | - | ❌ 未实现 |
| 11 | POST | `/users/{user_id}/activate` | 激活用户 | - | ❌ 未实现 |
| 12 | POST | `/users/{user_id}/ban` | 封禁用户 | - | ❌ 未实现 |
| 13 | POST | `/users/{user_id}/unban` | 解封用户 | - | ❌ 未实现 |
| 14 | GET | `/comments` | 评论列表（管理） | - | ❌ 未实现 |
| 15 | PATCH | `/comments/{comment_id}` | 更新评论状态（active） | - | ❌ 未实现 |
| 16 | DELETE | `/comments/{comment_id}` | 删除评论（管理员） | - | ❌ 未实现 |
| 17 | POST | `/tools/mock-data` | 生成模拟数据 | - | ❌ 未实现 |
| 18 | GET | `/tools/unused-images` | 列出未使用图片 | - | ❌ 未实现 |
| 19 | POST | `/tools/clean-unused-images` | 清理未使用图片 | - | ❌ 未实现 |
| 20 | GET | `/export/posts` | 导出文章 | - | ❌ 未实现 |
| 21 | GET | `/export/markdown` | 导出为 Markdown | - | ❌ 未实现 |
| 22 | POST | `/import/posts` | 导入文章 | - | ❌ 未实现 |
| 23 | POST | `/import/markdown` | 导入 Markdown | - | ❌ 未实现 |
| 24 | GET | `/backup/info` | 备份信息 | - | ❌ 未实现 |
| 25 | GET | `/backup/full` | 全站备份 | - | ❌ 未实现 |
| 26 | POST | `/backup/restore` | 全站恢复 | - | ❌ 未实现 |

---

## 八、收藏模块 `/api/favorites`

| # | HTTP 方法 | 路径 | 功能 | 前端 Composable | 覆盖状态 |
|---|-----------|------|------|-----------------|----------|
| 1 | GET | `/folders` | 我的收藏夹列表 | - | ❌ 未实现 |
| 2 | POST | `/folders` | 创建收藏夹 | - | ❌ 未实现 |
| 3 | PUT | `/folders/{folder_id}` | 更新收藏夹 | - | ❌ 未实现 |
| 4 | DELETE | `/folders/{folder_id}` | 删除收藏夹 | - | ❌ 未实现 |
| 5 | GET | `` (根路径) | 我的收藏列表（分页） | - | ❌ 未实现 |
| 6 | POST | `` (根路径) | 收藏文章 | - | ❌ 未实现 |
| 7 | PUT | `/{favorite_id}` | 更新收藏（移动夹/备注） | - | ❌ 未实现 |
| 8 | DELETE | `/{favorite_id}` | 取消收藏 | - | ❌ 未实现 |
| 9 | DELETE | `/post/{post_id}` | 按文章 ID 取消收藏 | - | ❌ 未实现 |
| 10 | PATCH | `/post/{post_id}/folder` | 按文章 ID 移动收藏夹 | - | ❌ 未实现 |
| 11 | PATCH | `/post/{post_id}/note` | 按文章 ID 更新备注 | - | ❌ 未实现 |
| 12 | POST | `/check` | 检查多篇文章收藏状态 | - | ❌ 未实现 |

---

## 九、通知模块 `/api/notifications`

| # | HTTP 方法 | 路径 | 功能 | 前端 Composable | 覆盖状态 |
|---|-----------|------|------|-----------------|----------|
| 1 | GET | `` (根路径) | 通知列表（分页） | - | ❌ 未实现 |
| 2 | GET | `/unread-count` | 未读通知数 | - | ❌ 未实现 |
| 3 | GET | `/stats` | 通知统计 | - | ❌ 未实现 |
| 4 | POST | `/{notification_id}/read` | 标记单条已读 | - | ❌ 未实现 |
| 5 | POST | `/read-all` | 全部标记已读 | - | ❌ 未实现 |
| 6 | DELETE | `/{notification_id}` | 删除单条通知 | - | ❌ 未实现 |
| 7 | DELETE | `` (根路径) | 清空通知（或已读通知） | - | ❌ 未实现 |

---

## 十、私信模块 `/api/messages`

| # | HTTP 方法 | 路径 | 功能 | 前端 Composable | 覆盖状态 |
|---|-----------|------|------|-----------------|----------|
| 1 | GET | `/conversations` | 会话列表 | - | ❌ 未实现 |
| 2 | GET | `/unread/count` | 未读消息总数 | - | ❌ 未实现 |
| 3 | GET | `/{user_id}` | 与指定用户的会话（分页） | - | ❌ 未实现 |
| 4 | POST | `` (根路径) | 发送私信 | - | ❌ 未实现 |
| 5 | PUT | `/{message_id}/read` | 标记单条消息已读 | - | ❌ 未实现 |
| 6 | PUT | `/read-all/{user_id}` | 标记与某用户的全部消息已读 | - | ❌ 未实现 |

---

## 十一、留言板 `/api/guestbook`

| # | HTTP 方法 | 路径 | 功能 | 前端 Composable | 覆盖状态 |
|---|-----------|------|------|-----------------|----------|
| 1 | GET | `/guestbook` | 留言板分页列表 | - | ❌ **高优未实现** |
| 2 | POST | `/guestbook` | 发表留言 | - | ❌ **高优未实现** |
| 3 | POST | `/guestbook/{entry_id}/like` | 给留言点赞 | - | ❌ 未实现 |
| 4 | GET | `/admin/guestbook` | 【管理员】留言板列表（含筛选） | - | ❌ 未实现 |
| 5 | POST | `/admin/guestbook/{entry_id}/pin` | 切换留言置顶 | - | ❌ 未实现 |
| 6 | POST | `/admin/guestbook/{entry_id}/feature` | 切换留言精华 | - | ❌ 未实现 |
| 7 | POST | `/admin/guestbook/{entry_id}/approve` | 批准留言 | - | ❌ 未实现 |
| 8 | POST | `/admin/guestbook/{entry_id}/reject` | 拒绝留言 | - | ❌ 未实现 |
| 9 | POST | `/admin/guestbook/{entry_id}/spam` | 标记垃圾留言 | - | ❌ 未实现 |
| 10 | POST | `/admin/guestbook/batch` | 批量操作留言 | - | ❌ 未实现 |

---

## 十二、其他重要模块（节选）

### 12.1 翻译 `/api/translate`

| # | HTTP 方法 | 路径 | 功能 | 状态 |
|---|-----------|------|------|------|
| 1 | POST | `/translate` | 翻译文本（多目标语言） | ❌ 未实现 |

### 12.2 SEO `/api/seo`

| # | HTTP 方法 | 路径 | 功能 | 状态 |
|---|-----------|------|------|------|
| 1 | GET | `/seo/config` | 获取 SEO 配置 | ❌ 未实现 |
| 2 | PUT | `/seo/config` | 更新 SEO 配置（管理员） | ❌ 未实现 |
| 3 | POST | `/seo/sitemap/generate` | 强制重新生成 sitemap | ❌ 未实现 |
| 4 | GET | `/seo/sitemap.xml` | sitemap.xml（同 blog 下） | ❌ 未实现 |
| 5 | GET | `/seo/robots.txt` | 动态 robots.txt | ❌ 未实现 |
| 6 | GET | `/seo/schema/{type}/{id}` | JSON-LD 结构化数据 | ❌ 未实现 |
| 7 | GET | `/seo/open-graph/{type}/{id}` | Open Graph 元数据 | ❌ 未实现 |

### 12.3 网站动态 `/api/activities`

| # | HTTP 方法 | 路径 | 功能 | 状态 |
|---|-----------|------|------|------|
| 1 | GET | `/activities` | 动态列表（已发布） | ❌ 未实现 |
| 2 | POST | `/activities` | 发布动态 | ❌ 未实现 |
| 3 | POST | `/activities/{id}/like` | 给动态点赞 | ❌ 未实现 |
| 4-8 | CRUD | `/admin/activities/*` | 管理员管理动态 | ❌ 未实现 |

### 12.4 Hero 轮播 `/api/hero/slides`

| # | HTTP 方法 | 路径 | 功能 | 状态 |
|---|-----------|------|------|------|
| 1 | GET | `/hero/slides` | 获取活跃 Hero 幻灯片 | ❌ 未实现 |
| 2-6 | CRUD | `/admin/hero/slides/*` | 管理员管理 Hero | ❌ 未实现 |

### 12.5 公告 `/api/announcements`

| # | HTTP 方法 | 路径 | 功能 | 状态 |
|---|-----------|------|------|------|
| 1 | GET | `/announcements` | 获取活跃公告 | ❌ 未实现 |
| 2-6 | CRUD | `/admin/announcements/*` | 管理员管理公告 | ❌ 未实现 |

### 12.6 文章系列 `/api/series`

| # | HTTP 方法 | 路径 | 功能 | 状态 |
|---|-----------|------|------|------|
| 1 | GET | `/series` | 系列列表 | ❌ 未实现 |
| 2 | GET | `/series/{slug}` | 系列详情（含文章列表） | ❌ 未实现 |
| 3-7 | CRUD | `/admin/series/*` | 管理员管理系列 | ❌ 未实现 |
| 8 | POST | `/post_series/complete` | 编辑器 autocomplete 同系列 | ❌ 未实现 |

### 12.7 相册 `/api/albums` + `/api/photos`

| # | HTTP 方法 | 路径 | 功能 | 状态 |
|---|-----------|------|------|------|
| 1 | GET | `/albums` | 公开相册列表 | ❌ 未实现 |
| 2 | GET | `/albums/{id}` | 相册详情及照片 | ❌ 未实现 |
| 3-10 | CRUD | `/admin/albums/*`, `/admin/photos/*` | 管理员管理相册照片 | ❌ 未实现 |

### 12.8 投票 `/api/voting/polls`

| # | HTTP 方法 | 路径 | 功能 | 状态 |
|---|-----------|------|------|------|
| 1 | GET | `/voting/polls` | 投票列表 | ❌ 未实现 |
| 2 | GET | `/voting/polls/{id}` | 投票详情 | ❌ 未实现 |
| 3 | POST | `/voting/polls` | 创建投票 | ❌ 未实现 |
| 4 | POST | `/voting/polls/{id}/vote` | 参与投票 | ❌ 未实现 |
| 5 | DELETE | `/voting/polls/{id}` | 删除投票 | ❌ 未实现 |

### 12.9 热门排行 `/api/ranking`

| # | HTTP 方法 | 路径 | 功能 | 状态 |
|---|-----------|------|------|------|
| 1 | GET | `/ranking/posts` | 热门文章排行榜 | ❌ 未实现 |

### 12.10 Bing 壁纸 + 验证码 + TOC

| # | HTTP 方法 | 路径 | 功能 | 状态 |
|---|-----------|------|------|------|
| 1 | GET | `/wallpaper` | 获取每日 Bing 壁纸 | ❌ 未实现 |
| 2 | GET | `/captcha` | 获取验证码图片 | ❌ 未实现 |
| 3 | POST | `/captcha/verify` | 验证验证码 | ❌ 未实现 |
| 4 | POST | `/toc/generate` | 生成目录 | ❌ 未实现 |
| 5 | POST | `/toc/extract` | 提取标题 | ❌ 未实现 |
| 6 | POST | `/toc/add-ids` | 添加标题 ID | ❌ 未实现 |

### 12.11 用户称号 `/api/admin/titles`

| # | HTTP 方法 | 路径 | 功能 | 状态 |
|---|-----------|------|------|------|
| 1-8 | CRUD + 分配 | `/admin/titles/*`, `/admin/users/{id}/title` | 称号管理与分配 | ❌ 未实现 |

### 12.12 Webhook `/api/webhooks`

| # | HTTP 方法 | 路径 | 功能 | 状态 |
|---|-----------|------|------|------|
| 1 | GET | `/webhooks` | Webhook 列表 | ❌ 未实现 |
| 2 | GET | `/webhooks/events` | 支持的事件类型 | ❌ 未实现 |
| 3 | POST | `/webhooks` | 创建 Webhook | ❌ 未实现 |
| 4 | PUT | `/webhooks/{id}` | 更新 Webhook | ❌ 未实现 |
| 5 | DELETE | `/webhooks/{id}` | 删除 Webhook | ❌ 未实现 |
| 6 | GET | `/webhooks/{id}/deliveries` | 投递记录 | ❌ 未实现 |
| 7 | POST | `/webhooks/{id}/test` | 测试 Webhook | ❌ 未实现 |
| 8 | POST | `/webhooks/{id}/regenerate-secret` | 重新生成密钥 | ❌ 未实现 |
| 9 | POST | `/webhooks/deliveries/{id}/retry` | 重试投递 | ❌ 未实现 |

### 12.13 高级管理（回收站/修订/日志）

| # | HTTP 方法 | 路径 | 功能 | 状态 |
|---|-----------|------|------|------|
| 1 | GET | `/trash` | 回收站列表 | ❌ 未实现 |
| 2 | POST | `/trash/{id}/restore` | 恢复项目 | ❌ 未实现 |
| 3 | DELETE | `/trash/{id}` | 永久删除 | ❌ 未实现 |
| 4 | DELETE | `/trash` | 清空回收站 | ❌ 未实现 |
| 5 | POST | `/posts/batch` | 批量操作文章 | ❌ 未实现 |
| 6 | GET | `/posts/{id}/revisions` | 文章修订历史 | ❌ 未实现 |
| 7 | GET | `/posts/{id}/revisions/{rid}` | 修订版本详情 | ❌ 未实现 |
| 8 | POST | `/posts/{id}/revisions/{rid}/restore` | 恢复到指定版本 | ❌ 未实现 |
| 9 | GET | `/posts/{id}/revisions/compare` | 比较修订版本差异 | ❌ 未实现 |
| 10 | GET | `/logs` | 操作日志列表 | ❌ 未实现 |
| 11 | GET | `/logs/export` | 导出操作日志 | ❌ 未实现 |

### 12.14 内容加密 + 定时发布

| # | HTTP 方法 | 路径 | 功能 | 状态 |
|---|-----------|------|------|------|
| 1 | POST | `/posts/{id}/decrypt` | 解密文章内容 | ❌ 未实现 |
| 2 | POST | `/admin/posts/{id}/encrypt` | 设置文章加密 | ❌ 未实现 |
| 3 | PUT | `/admin/posts/{id}/encrypt` | 更新文章加密 | ❌ 未实现 |
| 4 | DELETE | `/admin/posts/{id}/encrypt` | 关闭加密 | ❌ 未实现 |
| 5 | POST | `/post_crypto/derive_keys` | 派生加密元数据 | ❌ 未实现 |
| 6 | POST | `/post_crypto/verify_access` | 验证访问密码 | ❌ 未实现 |
| 7 | GET | `/post_crypto/encrypted/{id}/preview` | 加密文章预览 | ❌ 未实现 |
| 8 | GET | `/admin/posts/scheduled` | 定时发布文章列表 | ❌ 未实现 |
| 9 | PUT | `/admin/posts/{id}/schedule` | 设置定时发布 | ❌ 未实现 |
| 10 | DELETE | `/admin/posts/{id}/schedule` | 取消定时发布 | ❌ 未实现 |

### 12.15 监控 + 性能 + 系统设置分组

| # | HTTP 方法 | 路径 | 功能 | 状态 |
|---|-----------|------|------|------|
| 1 | GET | `/monitoring/health` | 组件健康检查 | ❌ 未实现 |
| 2 | GET | `/monitoring/stats` | 系统运行统计 | ❌ 未实现 |
| 3 | GET | `/monitoring/visits/summary` | 访问量汇总 | ❌ 未实现 |
| 4 | GET | `/monitoring/performance/summary` | 性能概览 | ❌ 未实现 |
| 5 | GET | `/monitoring/performance` | 性能指标 | ❌ 未实现 |
| 6 | GET | `/monitoring/database` | 数据库监控 | ❌ 未实现 |
| 7 | GET | `/monitoring/cache` | 缓存监控 | ❌ 未实现 |
| 8 | GET | `/monitoring/trends` | 趋势数据 | ❌ 未实现 |
| 9 | GET | `/admin/performance/summary` | 性能统计摘要 | ❌ 未实现 |
| 10 | GET | `/admin/performance/slow` | 最慢请求 | ❌ 未实现 |
| 11 | GET | `/admin/performance/storage` | 性能数据存储统计 | ❌ 未实现 |
| 12 | DELETE | `/admin/performance/cleanup` | 清理性能旧数据 | ❌ 未实现 |
| 13 | GET | `/settings-groups` | 获取所有设置分组 | ❌ 未实现 |
| 14 | GET | `/settings-groups/{group}` | 获取单个分组设置 | ❌ 未实现 |
| 15 | PATCH | `/settings-groups/{group}` | 更新分组设置 | ❌ 未实现 |

---

## 附录：前端 composables 现有导出清单

### `composables/usePosts.ts` → `usePosts()`
| 导出函数 | 调用的 API 端点 |
|----------|----------------|
| `getPosts(params)` | GET `/blog/posts?lang=&...` |
| `fetchPosts(params)` | （有状态包装）同上 |
| `getPost(slug, password?)` | GET `/blog/posts/{slug}?lang=&password=` |
| `fetchPost(slug, password?)` | （有状态包装）同上 |
| `getRecommendedPosts(page, pageSize)` | GET `/blog/posts/recommended?lang=&page=&page_size=` |
| `getSimilarPosts(postId, limit)` | GET `/blog/posts/{postId}/similar?lang=&limit=` |
| `likePost(postId)` | POST `/blog/posts/{postId}/like` |
| `createPost(postData)` | POST `/blog/posts?lang=` |
| `updatePost(postId, postData)` | PUT `/blog/posts/{postId}?lang=` |
| `deletePost(postId)` | DELETE `/blog/posts/{postId}` |

### `composables/useUsers.ts` → 导出两个组合式
#### `useComments()`
| 导出函数 | 调用的 API 端点 |
|----------|----------------|
| `getComments(postId)` | GET `/posts/{postId}/comments` ⚠️ 路径缺 `/blog` 前缀 |
| `fetchComments(postId)` | （有状态包装）同上 |
| `createComment(postId, comment)` | POST `/posts/{postId}/comments` ⚠️ 路径缺 `/blog` 前缀 |

#### `useUsers()`
| 导出函数 | 调用的 API 端点 |
|----------|----------------|
| `getUser(userId)` | GET `/users/{userId}` |
| `getUserByUsername(username)` | GET `/users/username/{username}` |
| `getUserPosts(userId, page, pageSize)` | GET `/users/{userId}/posts?lang=&page=&page_size=` |
| `getUserComments(userId, page, pageSize)` | GET `/users/{userId}/comments?lang=&page=&page_size=` |
| `getUserStats(userId)` | GET `/users/{userId}/stats` |

### `stores/auth.ts` → Pinia Store
| 导出方法 | 调用的 API 端点 |
|----------|----------------|
| `login(username, password)` | POST `/users/login` |
| `register(username, email, password, nickname?)` | POST `/users/register` |
| `logout()` | POST `/users/logout` |
| `refreshAccessToken()` | POST `/users/refresh` |
| `fetchUser()` | GET `/users/me`（通过 useFetch 直连，未用 useAPI） |

### `composables/useOOBE.ts` → `useOOBE()`
| 导出函数 | 调用的 API 端点 |
|----------|----------------|
| `getOOBEStatus()` | GET `/oobe/status` |
| `checkEnvironment()` | GET `/oobe/check` |
| `getSystemInfo()` | GET `/oobe/system-info` |
| `checkDependencies()` | GET `/oobe/dependencies` |
| `installDependencies()` | POST `/oobe/install-dependencies` |
| `install(data)` | POST `/oobe/install` |
| `getInstallStream(sid)` | SSE EventSource `/oobe/install/stream?sid=` |
| `checkSystem()` | （UI 包装）checkEnvironment + 合并状态 |
| `createAdmin(payload)` | （仅本地状态，未发 API）⚠️ 假实现 |
| `saveSiteSettings(settings)` | （仅本地状态，未发 API）⚠️ 假实现 |
| `finishOOBE()` | （调用 install() 一键完成） |

### `composables/useCore.ts` → 导出 7 个组合式
#### `useCategories()`
| 导出函数 | 调用的 API 端点 |
|----------|----------------|
| `getCategories()` | GET `/blog/categories?lang=` |
| `getCategory(slug)` | GET `/blog/categories/slug/{slug}?lang=` |

#### `useTags()`
| 导出函数 | 调用的 API 端点 |
|----------|----------------|
| `getTags()` | GET `/blog/tags?lang=` |
| `getTag(slug)` | GET `/blog/tags/slug/{slug}?lang=` |

#### `useSiteConfig()`
| 导出函数 | 调用的 API 端点 |
|----------|----------------|
| `getSiteConfig()` | GET `/config` |

#### `useNavigations()`
| 导出函数 | 调用的 API 端点 |
|----------|----------------|
| `getNavigations(location?)` | GET `/navigations?location=` |

#### `useFriendLinks()`
| 导出函数 | 调用的 API 端点 |
|----------|----------------|
| `getFriendLinks()` | GET `/friend-links` |

#### `useArchive()`
| 导出函数 | 调用的 API 端点 |
|----------|----------------|
| `getArchive(limitPerMonth)` | GET `/blog/archive?lang=&limit_per_month=` |
| `getArchiveByYear(year)` | GET `/blog/archive/{year}?lang=` |
| `getArchiveByMonth(year, month, page, pageSize)` | GET `/blog/archive/{year}/{month}?lang=&page=&page_size=` |
| `getArchiveStats()` | GET `/blog/archive/stats` |

#### `useSiteStats()`
| 导出函数 | 调用的 API 端点 |
|----------|----------------|
| `getSiteStats()` | GET `/blog/site-stats` |

---

## 标记说明

| 标记 | 含义 |
|------|------|
| ✅ 已实现 | 前端 composable 中存在对应函数调用 |
| ❌ 未实现 | 后端有路由，前端无对应实现 |
| ❌ **高优未实现** | 建议优先补上的核心功能 |
| ⚠️ 路径不一致 | 前端路径与后端路由前缀不匹配（可能导致 404） |
