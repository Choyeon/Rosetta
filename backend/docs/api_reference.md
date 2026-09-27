# Rosetta API 参考文档

## 概述

Rosetta API 是一个现代化的博客平台后端服务，提供完整的博客管理功能。

- **基础 URL**: `http://localhost:8000/api`
- **认证方式**: Bearer Token (JWT)
- **内容类型**: `application/json`

## 认证

### 获取令牌

登录成功后，API 返回 `access_token` 和 `refresh_token`：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 使用令牌

在请求头中添加 Authorization：

```
Authorization: Bearer <access_token>
```

---

## 用户 API (`/api/users`)

### 用户注册

```http
POST /api/users/register
Content-Type: application/json

{
  "username": "testuser",
  "email": "test@example.com",
  "password": "SecurePass123",
  "nickname": "测试用户"
}
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 用户登录

```http
POST /api/users/login
Content-Type: application/json

{
  "username": "testuser",
  "password": "SecurePass123"
}
```

**响应**: 同注册

### 刷新令牌

```http
POST /api/users/refresh?refresh_token=eyJhbGciOiJIUzI1NiIs...
```

### 用户登出

```http
POST /api/users/logout
Authorization: Bearer <access_token>
```

### 获取当前用户

```http
GET /api/users/me
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "nickname": "测试用户",
  "avatar": null,
  "bio": null,
  "is_active": true,
  "is_staff": false,
  "is_superuser": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### 更新个人信息

```http
PUT /api/users/me
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "nickname": "新昵称",
  "bio": "个人简介",
  "website": "https://example.com",
  "github": "https://github.com/testuser"
}
```

### 获取用户偏好

```http
GET /api/users/me/preferences
Authorization: Bearer <access_token>
```

### 更新用户偏好

```http
PUT /api/users/me/preferences
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "public_profile": true,
  "theme": "dark"
}
```

### 获取用户列表

```http
GET /api/users/?page=1&page_size=20&search=test
```

### 获取指定用户

```http
GET /api/users/{user_id}
```

### 修改密码

```http
POST /api/users/me/change-password
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "current_password": "OldPass123",
  "new_password": "NewSecure456"
}
```

**响应**:
```json
{
  "success": true,
  "message": "密码修改成功"
}
```

### 注销账户

```http
DELETE /api/users/me?password=CurrentPass123
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "success": true,
  "message": "账户已注销"
}
```

### 更新头像

```http
PUT /api/users/me/avatar?avatar=/media/avatars/new_avatar.jpg
Authorization: Bearer <access_token>
```

### 更新封面图

```http
PUT /api/users/me/cover?cover_image=/media/covers/new_cover.jpg
Authorization: Bearer <access_token>
```

---

## 博客 API (`/api/blog`)

### 文章列表

```http
GET /api/blog/posts?page=1&page_size=12&category=tech&tag=python&lang=zh
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码，默认 1 |
| page_size | int | 每页数量，默认 12，最大 1000 |
| category | string | 分类 slug |
| tag | string | 标签 slug |
| search | string | 搜索关键词 |
| lang | string | 语言代码 (zh/en/ja/zh_Hant) |

**响应**:
```json
{
  "items": [
    {
      "id": 1,
      "title": "文章标题",
      "subtitle": "副标题",
      "slug": "article-slug",
      "excerpt": "文章摘要...",
      "cover_image": "/media/covers/cover.jpg",
      "author": {
        "id": 1,
        "username": "author",
        "nickname": "作者"
      },
      "category": {
        "id": 1,
        "name": "技术",
        "slug": "tech"
      },
      "tags": [
        {"id": 1, "name": "Python", "slug": "python"}
      ],
      "status": "published",
      "views": 100,
      "likes_count": 10,
      "comments_count": 5,
      "is_pinned": false,
      "created_at": "2024-01-01T00:00:00Z",
      "published_at": "2024-01-01T00:00:00Z",
      "reading_time": 5
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 12,
  "total_pages": 9
}
```

### 文章详情

```http
GET /api/blog/posts/{slug}?lang=zh&password=optional
```

### 创建文章

```http
POST /api/blog/posts
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "title": {
    "zh": "中文标题",
    "en": "English Title"
  },
  "content": {
    "zh": "中文内容...",
    "en": "English content..."
  },
  "excerpt": {
    "zh": "摘要..."
  },
  "cover_image": "/media/covers/cover.jpg",
  "category_id": 1,
  "tag_ids": [1, 2, 3],
  "status": "published",
  "is_pinned": false,
  "allow_comments": true
}
```

### 更新文章

```http
PUT /api/blog/posts/{post_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "title": {"zh": "新标题"},
  "status": "published"
}
```

### 删除文章

```http
DELETE /api/blog/posts/{post_id}
Authorization: Bearer <access_token>
```

### 点赞/取消点赞

```http
POST /api/blog/posts/{post_id}/like
Authorization: Bearer <access_token>
```

---

### 文章归档

```http
GET /api/blog/archive
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| lang | string | 语言代码：zh/en/ja/zh_Hant |
| limit_per_month | int | 每月最多返回的文章数（默认 50） |

**响应**:
```json
[
  {
    "year": 2025,
    "month": 2,
    "count": 15,
    "posts": [
      {
        "id": 1,
        "title": "文章标题",
        "slug": "post-slug",
        "created_at": "2025-02-18T10:00:00Z",
        "category": {
          "id": 1,
          "name": "分类名",
          "color": "#3B82F6"
        },
        "views": 100
      }
    ]
  }
]
```

### 归档统计

```http
GET /api/blog/archive/stats
```

**响应**:
```json
{
  "total_posts": 100,
  "total_years": 3,
  "years": [2025, 2024, 2023],
  "year_stats": {
    "2025": 50,
    "2024": 30,
    "2023": 20
  }
}
```

### 按年份获取归档

```http
GET /api/blog/archive/{year}
```

**响应**: 返回该年份按月份分组的文章列表

### 按年月获取归档

```http
GET /api/blog/archive/{year}/{month}
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码 |
| page_size | int | 每页数量 |

**响应**:
```json
{
  "year": 2025,
  "month": 2,
  "count": 15,
  "page": 1,
  "page_size": 20,
  "total_pages": 1,
  "posts": [...]
}
```

### 分类列表

```http
GET /api/blog/categories?lang=zh
```

**响应**:
```json
[
  {
    "id": 1,
    "name": "技术",
    "slug": "tech",
    "description": "技术相关文章",
    "icon": "code",
    "color": "#3B82F6",
    "post_count": 50
  }
]
```

### 分类详情

```http
GET /api/blog/categories/slug/{slug}?lang=zh
```

### 创建分类

```http
POST /api/blog/categories
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": {
    "zh": "新分类",
    "en": "New Category"
  },
  "slug": "new-category",
  "description": {
    "zh": "分类描述"
  },
  "icon": "folder",
  "color": "#10B981"
}
```

### 更新分类

```http
PUT /api/blog/categories/{category_id}
Authorization: Bearer <access_token>
```

### 删除分类

```http
DELETE /api/blog/categories/{category_id}
Authorization: Bearer <access_token>
```

### 标签列表

```http
GET /api/blog/tags?lang=zh
```

### 标签详情

```http
GET /api/blog/tags/slug/{slug}?lang=zh
```

### 创建标签

```http
POST /api/blog/tags
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": {
    "zh": "Python",
    "en": "Python"
  },
  "slug": "python",
  "color": "#3776AB"
}
```

### 更新标签

```http
PUT /api/blog/tags/{tag_id}
Authorization: Bearer <access_token>
```

### 删除标签

```http
DELETE /api/blog/tags/{tag_id}
Authorization: Bearer <access_token>
```

### 评论列表

```http
GET /api/blog/posts/{post_id}/comments
```

**响应**:
```json
[
  {
    "id": 1,
    "post_id": 1,
    "user": {
      "id": 1,
      "username": "commenter",
      "nickname": "评论者"
    },
    "parent_id": null,
    "content": "这是一条评论",
    "active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "replies": [
      {
        "id": 2,
        "parent_id": 1,
        "content": "回复内容",
        "replies": []
      }
    ]
  }
]
```

### 发表评论

```http
POST /api/blog/posts/{post_id}/comments
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "content": "这是一条评论",
  "parent_id": null
}
```

### RSS 订阅

```http
GET /api/blog/rss?lang=zh&limit=20
```

### 站点地图

```http
GET /api/blog/sitemap.xml
```

---

## 核心 API (`/api`)

### 页面列表

```http
GET /api/pages?page=1&page_size=20
```

### 页面详情

```http
GET /api/pages/{slug}
```

### 创建页面

```http
POST /api/pages
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "title": {"zh": "关于我们"},
  "slug": "about",
  "content": {"zh": "页面内容..."},
  "status": "published"
}
```

### 更新页面

```http
PUT /api/pages/{page_id}
Authorization: Bearer <access_token>
```

### 删除页面

```http
DELETE /api/pages/{page_id}
Authorization: Bearer <access_token>
```

### 导航列表

```http
GET /api/navigations?location=header
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| location | string | 位置: header/footer/sidebar |

**响应**:
```json
[
  {
    "id": 1,
    "title": {"zh": "首页", "en": "Home"},
    "url": "/",
    "location": "header",
    "order": 0,
    "is_active": true,
    "target_blank": false
  }
]
```

### 创建导航

```http
POST /api/navigations
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "title": {"zh": "新导航"},
  "url": "/new-page",
  "location": "header",
  "order": 0,
  "is_active": true
}
```

### 删除导航

```http
DELETE /api/navigations/{nav_id}
Authorization: Bearer <access_token>
```

### 友链列表

```http
GET /api/friend-links?all=false
```

### 创建友链

```http
POST /api/friend-links
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": {"zh": "友站名称"},
  "url": "https://friend.site",
  "description": {"zh": "友站描述"},
  "logo": "/media/logos/friend.png",
  "order": 0,
  "is_active": true
}
```

### 更新友链

```http
PUT /api/friend-links/{link_id}
Authorization: Bearer <access_token>
```

### 删除友链

```http
DELETE /api/friend-links/{link_id}
Authorization: Bearer <access_token>
```

### 站点配置

```http
GET /api/config
```

**响应**:
```json
{
  "site_name": "Rosetta Blog",
  "site_description": "Rosetta开源博客系统",
  "site_keywords": "Rosetta, FastAPI, Astro, Blog",
  "site_author": "Rosetta Team",
  "site_email": "contact@rosetta.dev",
  "site_logo": "/media/logo.png",
  "site_favicon": "/media/favicon.ico",
  "site_icon": "/media/icon.png",
  "footer_text": "Powered by Rosetta",
  "footer_slogan": "Share knowledge, inspire creativity",
  "copyright_text": "© 2024 Rosetta",
  "icp_number": "京ICP备XXXXXXXX号",
  "police_icp_number": "京公网安备 XXXXXXXXXXX号",
  "github_url": "https://github.com/rosetta",
  "x_url": "https://x.com/rosetta",
  "bilibili_url": "https://space.bilibili.com/xxxxx",
  "weibo_url": "https://weibo.com/rosetta",
  "zhihu_url": "https://zhihu.com/people/rosetta",
  "youtube_url": "https://youtube.com/@rosetta",
  "linkedin_url": "https://linkedin.com/company/rosetta",
  "telegram_url": "https://t.me/rosetta",
  "contact_email": "contact@rosetta.dev",
  "contact_qq": "123456789",
  "contact_wechat": "rosetta_blog",
  "enable_comments": true,
  "enable_registration": true,
  "enable_rss_feed": true,
  "enable_search": true,
  "enable_sitemap": true,
  "enable_guestbook": true,
  "enable_dark_mode": true,
  "enable_reading_time": true,
  "enable_word_count": true,
  "enable_like_button": true,
  "enable_share_buttons": true,
  "enable_toc": true,
  "pagination_page_size": 12,
  "pagination_max_page_size": 100,
  "code_theme": "github",
  "code_theme_dark": "github-dark",
  "default_theme": "system",
  "primary_color": "#3B82F6",
  "font_family": null,
  "maintenance_mode": false,
  "maintenance_message": "Site is under maintenance",
  "maintenance_end_time": null,
  "default_post_cover": "/media/default/cover.jpg",
  "default_avatar": "/media/default/avatar.png",
  "default_category_cover": "/media/default/category.jpg",
  "google_analytics_id": "G-XXXXXXXXXX",
  "baidu_analytics_id": "xxxxxxxxxx",
  "google_site_verification": "xxxxx",
  "baidu_site_verification": "xxxxx",
  "robots_txt": "User-agent: *\nAllow: /",
  "require_email_verification": false,
  "allow_password_reset": true,
  "session_timeout": 3600,
  "max_login_attempts": 5,
  "login_lockout_duration": 1800,
  "email_configured": false,
  "email_from": "noreply@rosetta.dev",
  "email_from_name": "Rosetta Blog",
  "max_upload_size": 10485760,
  "allowed_image_types": "jpg,jpeg,png,gif,webp,svg",
  "allowed_file_types": "pdf,doc,docx,xls,xlsx,ppt,pptx,zip,rar",
  "comment_require_approval": false,
  "comment_allow_guest": false,
  "comment_max_length": 1000,
  "comment_antispam": true,
  "custom_header_code": null,
  "custom_footer_code": null,
  "custom_css": null,
  "custom_js": null
}
```

### 完整站点配置（管理员）

```http
GET /api/config/full
Authorization: Bearer <access_token>
```

**响应**: 返回分组形式的配置，便于前端构建设置页面

### 更新站点设置

```http
POST /api/admin/settings
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "site_name": "新站点名称",
  "enable_comments": true,
  "default_post_cover": "/media/covers/default.jpg",
  "primary_color": "#10B981"
}
```

**支持的配置项分组**:

| 分组 | 配置项 |
|------|--------|
| 基础设置 | site_name, site_description, site_keywords, site_author, site_email, site_logo, site_favicon, site_icon |
| 页脚设置 | footer_text, footer_slogan, copyright_text, icp_number, police_icp_number |
| 社交媒体 | github_url, x_url, bilibili_url, weibo_url, zhihu_url, youtube_url, linkedin_url, telegram_url |
| 联系方式 | contact_email, contact_qq, contact_wechat |
| 功能开关 | enable_comments, enable_registration, enable_rss_feed, enable_search, enable_sitemap, enable_guestbook, enable_dark_mode, enable_reading_time, enable_word_count, enable_like_button, enable_share_buttons, enable_toc |
| 分页设置 | pagination_page_size, pagination_max_page_size |
| 外观设置 | code_theme, code_theme_dark, default_theme, primary_color, font_family |
| 维护模式 | maintenance_mode, maintenance_message, maintenance_end_time |
| 默认图片 | default_post_cover, default_avatar, default_category_cover |
| SEO设置 | google_analytics_id, baidu_analytics_id, google_site_verification, baidu_site_verification, robots_txt |
| 安全设置 | require_email_verification, allow_password_reset, session_timeout, max_login_attempts, login_lockout_duration |
| 上传设置 | max_upload_size, allowed_image_types, allowed_file_types |
| 评论设置 | comment_require_approval, comment_allow_guest, comment_max_length, comment_antispam |
| 自定义代码 | custom_header_code, custom_footer_code, custom_css, custom_js |

**写入语义（`SiteConfig.value` 是字符串 KV）**：请求走 `exclude_unset` 局部更新。
- 省略某字段 → 不改动它。
- **显式传 `null` → 清空该项，落库为空串 `""`**（历史 bug：曾把 `str(None)` 存成字面量 `"None"`，前台读回 author_bio / site_url 等会渲染出 "None"，已修复）。
- 布尔项（`enable_*` 等）统一小写存储为 `"true"` / `"false"`，与读取侧 `.lower()=='true'` 对齐。
- 整数 / 字符串按其字符串形式入库；全部写完后失效 `site_config` 缓存并后台预热。

**读写面（双存储键，务必注意）**：本端点只写 `site_configs` 的扁平 UPPERCASE 键（如 `ICP_NUMBER`）。
17 个设置分组（`basic` / `seo` / `footer` / `appearance` 等）并不是独立的表，而是同一张
`site_configs` 里 key 为小写分组名的整段 JSON 行，由 `PATCH /api/settings/{group}` 写入。
`GET /api/config` 合并时**分组 JSON 优先于扁平键且覆写无条件**——`basic.icp_number=""`
会把刚写入的扁平 `ICP_NUMBER` 覆写成 `null`。因此与分组键有交集的项
（site_name / site_description / icp_number / footer 系列等）**必须走分组接口才会出现在
`/api/config`**；前台设置页已全量使用分组接口，本端点面向程序化 / 兼容场景。

---

## 媒体 API (`/api/media`)

### 上传图片

```http
POST /api/media/upload
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file: <图片文件>
```

**响应**:
```json
{
  "url": "/media/uploads/20240101120000_abc123.jpg",
  "filename": "20240101120000_abc123.jpg",
  "width": 1920,
  "height": 1080,
  "size": 500000
}
```

### 上传头像

```http
POST /api/media/avatar
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file: <图片文件>
```

### 上传封面

```http
POST /api/media/cover
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file: <图片文件>
```

### 流式上传（大文件）

```http
POST /api/media/upload/stream
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file: <大文件>
chunk_size: 65536
```

### 获取图片

```http
GET /api/media/{category}/{filename}
```

### 删除图片

```http
DELETE /api/media/{category}/{filename}
Authorization: Bearer <access_token>
```

---

## 媒体库 API (`/api/media/library`)

### 媒体库列表

```http
GET /api/media/library
Authorization: Bearer <access_token>
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码 |
| page_size | int | 每页数量 |
| file_type | string | 文件类型：image/video/audio/other |
| search | string | 搜索关键词 |
| sort_by | string | 排序字段：created_at/file_size/filename |
| sort_order | string | 排序方向：asc/desc |

**响应**:
```json
{
  "items": [
    {
      "id": 1,
      "file": "/media/uploads/image/20240101_abc123.jpg",
      "filename": "example.jpg",
      "file_type": "image",
      "file_size": 500000,
      "title": "图片标题",
      "alt_text": "替代文本",
      "description": "描述",
      "uploaded_by": {
        "id": 1,
        "username": "admin",
        "nickname": "管理员"
      },
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

### 媒体详情

```http
GET /api/media/library/{media_id}
Authorization: Bearer <access_token>
```

### 更新媒体信息

```http
PUT /api/media/library/{media_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "title": "新标题",
  "alt_text": "替代文本",
  "description": "描述"
}
```

### 上传到媒体库

```http
POST /api/media/library/upload
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file: <文件>
title: 标题（可选）
alt_text: 替代文本（可选）
description: 描述（可选）
```

**支持的文件类型**:
| 类型 | 扩展名 |
|------|--------|
| 图片 | jpg, jpeg, png, gif, webp, svg |
| 视频 | mp4, webm, mov |
| 音频 | mp3, wav, ogg |
| 文档 | pdf, doc, docx, xls, xlsx |

### 批量删除媒体

```http
DELETE /api/media/library/batch
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "media_ids": [1, 2, 3]
}
```

### 媒体库统计

```http
GET /api/media/library/stats
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "total_count": 100,
  "total_size": 524288000,
  "total_size_formatted": "500.00 MB",
  "type_stats": {
    "image": {"count": 80, "size": 419430400},
    "video": {"count": 10, "size": 104857600},
    "document": {"count": 10, "size": 0}
  }
}
```

---

## 用户主页 API (`/api/users/{user_id}`)

### 用户文章列表

```http
GET /api/users/{user_id}/posts
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码 |
| page_size | int | 每页数量 |

**响应**:
```json
{
  "items": [
    {
      "id": 1,
      "title": "文章标题",
      "slug": "post-slug",
      "excerpt": "摘要",
      "cover_image": "/media/covers/cover.jpg",
      "views": 100,
      "category": {"id": 1, "name": "分类", "color": "#3B82F6"},
      "tags": [{"id": 1, "name": "标签", "color": "#10B981"}],
      "published_at": "2024-01-01T00:00:00Z",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 10,
  "total_pages": 5
}
```

### 用户评论列表

```http
GET /api/users/{user_id}/comments
```

**响应**:
```json
{
  "items": [
    {
      "id": 1,
      "content": "评论内容...",
      "post": {
        "id": 1,
        "title": "文章标题",
        "slug": "post-slug"
      },
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 30,
  "page": 1,
  "page_size": 10,
  "total_pages": 3
}
```

### 用户统计信息

```http
GET /api/users/{user_id}/stats
```

**响应**:
```json
{
  "user_id": 1,
  "posts_count": 50,
  "comments_count": 100,
  "total_views": 10000,
  "total_likes": 500,
  "joined_at": "2024-01-01T00:00:00Z"
}
```

---

## 后台管理 API (`/api/admin`)

### 仪表盘统计

```http
GET /api/admin/stats?range=7d
Authorization: Bearer <access_token>
```

**查询参数**: `range` 取 `7d`（默认）或 `30d`，其它值一律按 7 天处理。

**响应**（`success/data/message` 信封；口径以 OpenAPI 的 `AdminStatsDataDoc` 为准）:

```json
{
  "success": true,
  "data": {
    "timeseries": {
      "labels": ["2026-09-21", "2026-09-22"],
      "datasets": [
        { "key": "pv", "values": [120, 98] },
        { "key": "uv", "values": [70, 61] },
        { "key": "comments", "values": [5, 2] },
        { "key": "posts", "values": [3, 1] },
        { "key": "users", "values": [2, 0] }
      ]
    },
    "top_articles": [{ "id": 1, "title": "示例文章", "views": 420, "comments_count": 12 }],
    "active_commenters": [
      { "name": "活跃读者", "avatar": null, "comments_count": 15, "title": "常客" }
    ],
    "system_health": {
      "cpu_percent": 12.4,
      "memory_percent": 61.2,
      "db_rtt_ms": 1.35,
      "cache_hit_percent": 87.5,
      "health_score": 90.3,
      "metric_scores": { "cpu": 95.0, "memory": 78.0, "db": 100.0, "cache": 87.5 }
    },
    "summary": {
      "total_posts": 100,
      "total_drafts": 12,
      "total_published": 88,
      "total_comments": 500,
      "total_pending_comments": 3,
      "total_users": 50,
      "total_views_today": 340,
      "total_comments_today": 7
    }
  },
  "message": "获取仪表盘统计成功"
}
```

读法要点：

- 没有真实数据时计数为 `0`、数组为空，后端**绝不回填演示数据**，空状态由前端渲染。
- `summary.total_views_today` 与 PV 曲线同源于 `visit_logs`（请求中间件批量落库），
  不是 `Post.views` 之和；`visit_logs` 受 `LOG_RETENTION_DAYS`（默认 7 天）清理，
  所以 `range=30d` 在默认配置下只能得到保留窗口内的曲线，需要更长窗口要调大保留天数。
- `system_health.health_score` 为 `null` 表示"一轴都没测到"（未知），不是 0 分；
  只有 DB 探活失败才直接记 0。探针不可用时对应指标也是 `null`。

> 旧版本文档在此处列出的 `GET /api/admin/view-trends` 与 `GET /api/admin/category-stats`
> 已经删除（见 `backend/api/admin.py` 统计区块注释，仪表盘统一走 `GET /api/admin/stats`）。
> 需要更细粒度的运行指标看监控 API：`GET /api/monitoring/visits/summary`（访问量汇总，
> 响应自带 `retention_days` + `data_since` 口径字段）、`GET /api/monitoring/performance/summary`、
> `GET /api/monitoring/stats`。

---

### 用户管理 API

#### 用户列表（管理员）

```http
GET /api/admin/users?page=1&page_size=20&search=test&is_staff=false&is_active=true
Authorization: Bearer <access_token>
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码 |
| page_size | int | 每页数量 |
| search | string | 搜索关键词 |
| is_staff | bool | 筛选管理员 |
| is_active | bool | 筛选激活状态 |
| is_banned | bool | 筛选封禁状态 |

#### 创建用户（管理员）

```http
POST /api/admin/users
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "SecurePass123",
  "nickname": "新用户",
  "bio": "个人简介",
  "is_staff": false,
  "is_active": true
}
```

#### 获取用户详情（管理员）

```http
GET /api/admin/users/{user_id}
Authorization: Bearer <access_token>
```

#### 更新用户（管理员）

```http
PUT /api/admin/users/{user_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "nickname": "新昵称",
  "bio": "新简介",
  "is_staff": true,
  "is_active": true,
  "is_banned": false
}
```

#### 重置用户密码（管理员）

```http
POST /api/admin/users/{user_id}/reset-password
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "new_password": "NewSecurePass123"
}
```

**响应**:
```json
{
  "success": true,
  "message": "密码已重置"
}
```

#### 删除用户（管理员）

```http
DELETE /api/admin/users/{user_id}
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "success": true,
  "message": "用户已删除"
}
```

#### 激活用户

```http
POST /api/admin/users/{user_id}/activate
Authorization: Bearer <access_token>
```

#### 封禁用户

```http
POST /api/admin/users/{user_id}/ban
Authorization: Bearer <access_token>
```

#### 解封用户

```http
POST /api/admin/users/{user_id}/unban
Authorization: Bearer <access_token>
```

---

### 评论管理 API

#### 评论列表（管理）

```http
GET /api/admin/comments?page=1&page_size=20
Authorization: Bearer <access_token>
```

#### 更新评论状态

```http
PATCH /api/admin/comments/{comment_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "active": true
}
```

#### 删除评论

```http
DELETE /api/admin/comments/{comment_id}
Authorization: Bearer <access_token>
```

### 用户称号管理 (`/api/admin/titles`)

> 实现：`backend/api/title.py`（`title.router` 挂在 `/api/admin`）。
> 全部响应为**裸 `response_model` 对象**（不是 `success/data/message` 信封）；`users_count` 由单次 `GROUP BY` 聚合得出，无 N+1。
> 权限：CRUD 与 assign/remove 要求 staff；`GET /api/admin/users/{user_id}/title` 仅要求登录（称号是公开档案字段）。
> 消费方：`frontend/pages/admin/users/titles.vue`（称号库）与 `frontend/pages/admin/users/[id]/edit.vue`（给用户戴/摘称号）。

#### 称号列表

```http
GET /api/admin/titles
Authorization: Bearer <staff_access_token>
```

```json
[
  {
    "id": 1,
    "name": { "zh": "常驻读者", "en": "Resident Reader", "ja": "常連", "zh_Hant": "常駐讀者" },
    "color": "#3B82F6",
    "icon": "crown",
    "description": { "zh": "长期活跃的用户", "en": "Long-term active user" },
    "created_at": "2026-09-01T00:00:00",
    "users_count": 7
  }
]
```

#### 称号详情

```http
GET /api/admin/titles/{title_id}
Authorization: Bearer <staff_access_token>
```

返回单个 `UserTitleResponse`（字段同上，`users_count` 为实时 count）。不存在 → `404 称号不存在`。
后台 UI 不调用它——列表接口已返回全量字段，此端点留给外部集成。

#### 创建 / 更新称号

```http
POST /api/admin/titles
Content-Type: application/json

{ "name": { "zh": "常驻读者" }, "color": "#3B82F6", "icon": "crown", "description": { "zh": "长期活跃的用户" } }
```

```http
PUT  /api/admin/titles/{title_id}
PATCH /api/admin/titles/{title_id}
Content-Type: application/json

{ "color": "#8B5CF6" }
```

字段约束（写入侧，`UserTitleCreate` / `UserTitleUpdate`）：

| 字段 | 约束 | 违规后果 |
|---|---|---|
| `name` | 必填多语言 dict；任一语言去掉空白后非空，且与既有称号**任一语言**都不完全同名 | 空 → `422 称号名称不能为空`；重名 → `400 称号名称已存在`（大小写/前后空白归一后精确比对，不做子串匹配，`VIP` 不会被 `VIP Pro` 判重） |
| `color` | `str`，≤20（与 `String(20)` 列宽一致）+ 十六进制正则 `^#(?:[0-9a-fA-F]{3,4}\|[0-9a-fA-F]{6}\|[0-9a-fA-F]{8})$`；DB 列 NOT NULL | 非 hex / 超长 → Pydantic `422`；`POST` 传 `null` → `422`；`PUT/PATCH` 显式 `null` → `422 称号颜色不能为空`（否则会 setattr 后 flush 撞 IntegrityError 变 500）。想"不改颜色"就省略该 key（PATCH 走 `exclude_unset`） |
| `icon` | `str \| null`，≤50，正则 `^[^<>]*$` | 含 `<` `>`（HTML/SVG 片段）→ `422`。**这是 XSS 红线**：`icon` 会被前台 `TitleIconSvg.vue` 渲染到每个访客页面，历史版本还允许其直接落 `v-html` |
| `description` | 可空多语言 dict | — |

校验失败时事务由 `get_db` 回滚，脏值不会半写入。

#### 删除称号

```http
DELETE /api/admin/titles/{title_id}
Authorization: Bearer <staff_access_token>
```

返回 **`204 No Content`**（本服务唯一一个 204 端点，无响应体）。删除前会逐个把持有该称号的用户摘干净
（写 `user.title = None` 关系而非裸 bulk UPDATE，避免同 session 内的关系缓存读到已删行），因此不会留下孤儿外键。

#### 给用户分配 / 移除称号

```http
POST /api/admin/titles/assign
Content-Type: application/json

{ "user_id": 12, "title_id": 1 }
```

```json
{ "message": "称号分配成功", "user_id": 12, "title_id": 1 }
```

```http
DELETE /api/admin/users/{user_id}/title
```

```json
{ "message": "称号已移除", "user_id": 12 }
```

用户或称号不存在时均为 `404`（`detail` 分别为「用户不存在」/「称号不存在」）。这两个入口彼此独立——
`assign` 只负责"戴上"，"摘下"必须调 `DELETE`；前端曾把 `assign(titleId=null)` 短路成假成功，已拆分为
`assignAdminUserTitle` / `removeAdminUserTitle` 两个真实包装。

#### 查询某用户的称号

```http
GET /api/admin/users/{user_id}/title
Authorization: Bearer <access_token>
```

```json
{ "user_id": 12, "title": { "id": 1, "name": { "zh": "常驻读者" }, "color": "#3B82F6", "icon": "crown", "description": null } }
```

未设置称号时返回 `{ "user_id": 12, "title": null }`；用户不存在 → `404`。

### 检索字段工具 (`/api/admin/tools`)

> 这两个端点返回**各自独立的 `response_model`**（裸对象），不是全局 `success/data/message` 信封。
> 消费方：`frontend/pages/admin/tools/seo.vue`「内容体检」页 → `fetchAdminSearchStats()` / `runAdminSearchOptimize()`。

#### 检索字段体检

```http
GET /api/admin/tools/search-stats
Authorization: Bearer <staff_access_token>
```

**响应**（`SearchStatsResponse`）：

```json
{
  "total_posts": 128,
  "total_categories": 12,
  "posts_without_excerpt": 3,
  "posts_without_slug": 0,
  "posts_without_tags": 7,
  "avg_slug_length": 24.6,
  "avg_excerpt_length": 118.4,
  "recommendations": [
    { "type": "excerpt", "count": 3, "message": "有 3 篇文章缺少摘要" },
    { "type": "tags", "count": 7, "message": "有 7 篇文章未设置标签" }
  ]
}
```

- 口径是**整库内容完整度**（本站检索走 LIKE，没有全文索引可查），与 `GET /api/seo/sitemap-check`（只看已发布文章的标题/摘要/封面）互补。
- `recommendations` **只包含 count > 0 的缺口**（示例里没有 `slug` 那条，因为 `posts_without_slug=0`）；前端据此区分"字段完整"空态与建议列表。
- `posts_without_*` 的"空"含三种形态：SQL NULL、空串、JSON `null`。多语言列是 JSON 且 SQLAlchemy 默认 `none_as_null=False`，写 `None` 会落成字符串 `"null"`，只判 `IS NULL` 会恒为 0。
- 聚合为 1 条 `COUNT(...) FILTER (WHERE ...)` 条件计数 + 1 条分类计数；`recommendations[*].count` 与顶层计数同源，不会互相矛盾。

#### 补全缺失字段

```http
POST /api/admin/tools/optimize-search
Authorization: Bearer <staff_access_token>
```

**响应**（`OptimizeSearchResponse`）：

```json
{
  "success": true,
  "scanned_count": 5,
  "slug_filled_count": 2,
  "excerpt_filled_count": 4,
  "message": "扫描 5 篇：补 slug 2 篇、补摘要 4 篇"
}
```

- slug 复用建文流程同一个 `generate_slug`（中文转拼音 + 特殊字符清洗 + 100 字符截断 + 空结果 uuid 兜底），并在库内逐个校验唯一，冲突时追加 `-2`/`-3`。
- 摘要按**每种语言各自的正文**生成，不会把 zh 文本复制进 en。
- 幂等：第二次调用 `slug_filled_count` / `excerpt_filled_count` 均为 0。
- 只补缺失，不覆写已有值；整批在同一事务内，冲突或异常时由 `get_db` 回滚并向调用方抛 500（不会返回"已优化 N 篇"的假成功）。


---

## 翻译 API (`/api/translate`)

### 翻译文本

```http
POST /api/translate
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "text": "博客",
  "source_lang": "zh",
  "target_langs": ["en", "ja", "zh_Hant"]
}
```

**响应**:
```json
{
  "translations": {
    "en": "Blog",
    "ja": "ブログ",
    "zh_Hant": "部落格"
  }
}
```

---

## 系统端点

### 健康检查

```http
GET /health
```

**响应**:
```json
{
  "status": "healthy",
  "app_name": "Rosetta API",
  "version": "1.0.0",
  "environment": "development",
  "database": "connected"
}
```

### API 根路径

```http
GET /
```

---

## 限流说明

API 实现了请求限流保护：

| 路径 | 限制 |
|------|------|
| `/api/users/login` | 5 次/15 分钟 |
| `/api/users/register` | 3 次/小时 |
| `/api/media/upload` | 10 次/分钟 |
| `/api/*` | 100 次/分钟 |

超出限制时返回 **429 Too Many Requests**：

```json
{
  "success": false,
  "message": "请求过于频繁，请稍后再试",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

> `error_code` 恒为语义化字符串（见 AGENTS.md §7.2），绝不用数字状态码填充；
> 429 全站唯一对外码即 `RATE_LIMIT_EXCEEDED`（回归见
> `tests/test_core_rate_limit_contract.py`）。

---

## 端点总索引

<!-- BEGIN AUTO-GENERATED:ENDPOINT_INDEX 由 backend/scripts/gen_api_index.py 生成，请勿手改 -->

## 端点总索引（自动生成）

本区块由 `backend/scripts/gen_api_index.py` 从运行时 `app.openapi()` 生成，共 **355 个操作 / 284 条路径**。
上面各章节是手写的重点说明（请求体、响应口径、坑），本区块是完整清单；两者互补，字段级契约以 `/openapi.json` 为准。

- 插件自带的路由（tag 为 `Plugin:*` / `Plugin-Public:*`）不在本清单内：它们只在对应插件启用后存在，需要实时清单就看 `/docs` 或 `/openapi.json`。
- 改动接口后请跑 `uv run python -m backend.scripts.gen_api_index --write`，否则 `tests/test_docs_api_index_sync.py` 会失败。

### 系统（3）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/` | API 根路径 |
| `GET` | `/api/health` | 健康检查 (/api 前缀别名) |
| `GET` | `/health` | 健康检查 |

### 用户（22）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/users/` | 用户列表 |
| `POST` | `/api/users/login` | 用户登录 |
| `POST` | `/api/users/logout` | 用户登出 |
| `GET` | `/api/users/me` | 获取当前用户 |
| `PUT` | `/api/users/me` | 更新个人信息 |
| `DELETE` | `/api/users/me` | 注销账户 |
| `PUT` | `/api/users/me/avatar` | 更新头像 |
| `POST` | `/api/users/me/change-password` | 修改密码（旧路径） |
| `PUT` | `/api/users/me/cover` | 更新封面图 |
| `POST` | `/api/users/me/password` | 修改密码 |
| `GET` | `/api/users/me/preferences` | 获取个人偏好 |
| `PUT` | `/api/users/me/preferences` | 更新个人偏好 |
| `POST` | `/api/users/password-reset` | 重置密码（验证码 + 新密码） |
| `POST` | `/api/users/password-reset-request` | 请求密码重置 |
| `POST` | `/api/users/refresh` | 刷新令牌 |
| `POST` | `/api/users/register` | 用户注册 |
| `GET` | `/api/users/username/{username}` | 通过用户名获取用户 |
| `GET` | `/api/users/username/{username}/preferences` | 获取用户隐私设置 |
| `GET` | `/api/users/{user_id}` | 获取用户信息 |
| `GET` | `/api/users/{user_id}/comments` | 用户评论列表 |
| `GET` | `/api/users/{user_id}/posts` | 用户文章列表 |
| `GET` | `/api/users/{user_id}/stats` | 用户统计信息 |

### 博客（41）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/blog/archive` | 文章归档 |
| `GET` | `/api/blog/archive/stats` | 归档统计 |
| `GET` | `/api/blog/archive/{year}` | 按年份获取归档 |
| `GET` | `/api/blog/archive/{year}/{month}` | 按年月获取归档 |
| `GET` | `/api/blog/categories` | 分类列表 |
| `POST` | `/api/blog/categories` | 创建分类 |
| `GET` | `/api/blog/categories/slug/{slug}` | 获取分类详情 |
| `PUT` | `/api/blog/categories/{category_id}` | 更新分类 |
| `DELETE` | `/api/blog/categories/{category_id}` | 删除分类 |
| `GET` | `/api/blog/posts` | 文章列表 |
| `POST` | `/api/blog/posts` | 创建文章 |
| `POST` | `/api/blog/posts/batch-status` | 批量更新文章状态 |
| `GET` | `/api/blog/posts/hot` | 热门文章（HackerNews 风格热榜） |
| `GET` | `/api/blog/posts/id/{post_id}` | 按ID获取文章 |
| `GET` | `/api/blog/posts/recommended` | 推荐文章列表 |
| `PUT` | `/api/blog/posts/{post_id}` | 更新文章 |
| `DELETE` | `/api/blog/posts/{post_id}` | 删除文章 |
| `GET` | `/api/blog/posts/{post_id}/comments` | 评论列表 |
| `POST` | `/api/blog/posts/{post_id}/comments` | 发表评论 |
| `GET` | `/api/blog/posts/{post_id}/edit` | 获取文章用于编辑 |
| `POST` | `/api/blog/posts/{post_id}/like` | 点赞/取消点赞 |
| `GET` | `/api/blog/posts/{post_id}/similar` | 相似文章推荐 |
| `GET` | `/api/blog/posts/{slug}` | 文章详情 |
| `GET` | `/api/blog/posts/{slug}/adjacent` | 上一篇/下一篇 |
| `GET` | `/api/blog/rss` | RSS 订阅 |
| `GET` | `/api/blog/site-stats` | 站点统计 |
| `GET` | `/api/blog/sitemap-pages.xml` | 静态路由 / 独立页面 Sitemap |
| `GET` | `/api/blog/sitemap-posts.xml` | 文章 Sitemap（分页） |
| `GET` | `/api/blog/sitemap-taxonomies.xml` | 分类 / 标签 / 系列 Sitemap |
| `GET` | `/api/blog/sitemap.xml` | Sitemap 索引 |
| `GET` | `/api/blog/tags` | 标签列表 |
| `POST` | `/api/blog/tags` | 创建标签 |
| `GET` | `/api/blog/tags/slug/{slug}` | 获取标签详情 |
| `PUT` | `/api/blog/tags/{tag_id}` | 更新标签 |
| `DELETE` | `/api/blog/tags/{tag_id}` | 删除标签 |
| `GET` | `/api/blog/users/me/comments` | 获取我的评论 |
| `GET` | `/api/blog/users/me/history` | 获取阅读历史 |
| `DELETE` | `/api/blog/users/me/history` | 清空阅读历史 |
| `GET` | `/api/blog/users/me/likes` | 获取我的点赞 |
| `GET` | `/api/blog/users/me/posts` | 获取我的文章 |
| `GET` | `/api/blog/users/me/stats` | 获取我的统计 |

### 核心（19）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/admin/navigations` | 管理员获取所有导航 |
| `POST` | `/api/admin/settings` | 更新站点设置 |
| `GET` | `/api/config` | 站点配置 |
| `GET` | `/api/config/full` | 完整站点配置（管理员） |
| `GET` | `/api/friend-links` | 友链列表 |
| `POST` | `/api/friend-links` | 创建友链 |
| `PUT` | `/api/friend-links/{link_id}` | 更新友链 |
| `DELETE` | `/api/friend-links/{link_id}` | 删除友链 |
| `GET` | `/api/navigations` | 导航列表 |
| `POST` | `/api/navigations` | 创建导航 |
| `PUT` | `/api/navigations/{nav_id}` | 更新导航 |
| `DELETE` | `/api/navigations/{nav_id}` | 删除导航 |
| `GET` | `/api/pages` | 页面列表 |
| `POST` | `/api/pages` | 创建页面 |
| `PUT` | `/api/pages/{page_id}` | 更新页面 |
| `DELETE` | `/api/pages/{page_id}` | 删除页面 |
| `GET` | `/api/pages/{slug}` | 页面详情 |
| `GET` | `/api/search-placeholders` | 搜索占位符 |
| `GET` | `/api/sponsors` | 打赏者列表 |

### 媒体（16）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/media/avatar` | 头像代理 |
| `POST` | `/api/media/avatar` | 上传头像 |
| `GET` | `/api/media/bing-wallpaper` | Bing 每日壁纸代理（支持批量） |
| `POST` | `/api/media/cover` | 上传封面图 |
| `GET` | `/api/media/library` | 媒体库列表 |
| `POST` | `/api/media/library` | 上传到媒体库（REST 主路径） |
| `DELETE` | `/api/media/library/batch` | 批量删除媒体 |
| `GET` | `/api/media/library/stats` | 媒体库统计 |
| `POST` | `/api/media/library/upload` | 上传到媒体库（别名路径） |
| `GET` | `/api/media/library/{media_id}` | 媒体详情 |
| `PUT` | `/api/media/library/{media_id}` | 更新媒体信息 |
| `DELETE` | `/api/media/library/{media_id}` | 删除单个媒体 |
| `POST` | `/api/media/upload` | 上传图片 |
| `POST` | `/api/media/upload/stream` | 流式上传图片 |
| `GET` | `/api/media/{category}/{filename}` | 获取图片 |
| `DELETE` | `/api/media/{category}/{filename}` | 删除图片 |

### 数据库迁移（4）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `POST` | `/api/admin/migration/cancel` | 取消当前运行中的迁移任务 |
| `GET` | `/api/admin/migration/presets` | 获取常用连接预设 |
| `POST` | `/api/admin/migration/start` | 发起跨库迁移任务 |
| `GET` | `/api/admin/migration/status` | 查询最新迁移任务状态 |

### 留言板（11）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/admin/guestbook` | 【管理员】留言板列表（含审核状态过滤/回收站/搜索） |
| `POST` | `/api/admin/guestbook/batch` | 【管理员】批量操作留言（approve/reject/spam/pin/feature/trash/restore/delete） |
| `DELETE` | `/api/admin/guestbook/{entry_id}` | 【管理员】单条删除留言 |
| `POST` | `/api/admin/guestbook/{entry_id}/approve` | 【管理员】批准留言 |
| `POST` | `/api/admin/guestbook/{entry_id}/feature` | 【管理员】切换留言精华 |
| `POST` | `/api/admin/guestbook/{entry_id}/pin` | 【管理员】切换留言置顶 |
| `POST` | `/api/admin/guestbook/{entry_id}/reject` | 【管理员】拒绝留言 |
| `POST` | `/api/admin/guestbook/{entry_id}/spam` | 【管理员】标记为垃圾留言 |
| `GET` | `/api/guestbook` | 获取留言板分页列表 |
| `POST` | `/api/guestbook` | 发表留言（游客或登录用户均可） |
| `POST` | `/api/guestbook/{entry_id}/like` | 给留言点赞（简单计数，允许匿名） |

### 投票（5）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/voting/polls` | 投票列表 |
| `POST` | `/api/voting/polls` | 创建投票 |
| `GET` | `/api/voting/polls/{poll_id}` | 投票详情 |
| `DELETE` | `/api/voting/polls/{poll_id}` | 删除投票 |
| `POST` | `/api/voting/polls/{poll_id}/vote` | 参与投票 |

### 通知（7）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/notifications` | 通知列表 |
| `DELETE` | `/api/notifications` | 清空通知 |
| `POST` | `/api/notifications/read-all` | 全部已读 |
| `GET` | `/api/notifications/stats` | 通知统计 |
| `GET` | `/api/notifications/unread-count` | 未读通知数 |
| `DELETE` | `/api/notifications/{notification_id}` | 删除通知 |
| `POST` | `/api/notifications/{notification_id}/read` | 标记已读 |

### 收藏（12）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/favorites` | 我的收藏列表 |
| `POST` | `/api/favorites` | 收藏文章 |
| `POST` | `/api/favorites/check` | 检查收藏状态 |
| `GET` | `/api/favorites/folders` | 我的收藏夹列表 |
| `POST` | `/api/favorites/folders` | 创建收藏夹 |
| `PUT` | `/api/favorites/folders/{folder_id}` | 更新收藏夹 |
| `DELETE` | `/api/favorites/folders/{folder_id}` | 删除收藏夹 |
| `DELETE` | `/api/favorites/post/{post_id}` | 按文章ID取消收藏 |
| `PATCH` | `/api/favorites/post/{post_id}/folder` | 按文章ID移动收藏夹 |
| `PATCH` | `/api/favorites/post/{post_id}/note` | 按文章ID更新备注 |
| `PUT` | `/api/favorites/{favorite_id}` | 更新收藏 |
| `DELETE` | `/api/favorites/{favorite_id}` | 取消收藏 |

### 后台管理（15）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/admin/comments` | 评论列表（管理员） |
| `PATCH` | `/api/admin/comments/{comment_id}` | 更新评论（管理员） |
| `DELETE` | `/api/admin/comments/{comment_id}` | 删除评论（管理员） |
| `POST` | `/api/admin/tools/optimize-search` | 补全检索字段 |
| `GET` | `/api/admin/tools/search-stats` | 检索字段体检 |
| `GET` | `/api/admin/users` | 用户列表（管理员） |
| `POST` | `/api/admin/users` | 创建用户（管理员） |
| `GET` | `/api/admin/users/{user_id}` | 获取用户详情（管理员） |
| `PUT` | `/api/admin/users/{user_id}` | 更新用户（管理员） |
| `PATCH` | `/api/admin/users/{user_id}` | 部分更新用户（管理员） |
| `DELETE` | `/api/admin/users/{user_id}` | 删除用户（管理员） |
| `POST` | `/api/admin/users/{user_id}/activate` | 激活用户（管理员） |
| `POST` | `/api/admin/users/{user_id}/ban` | 封禁用户（管理员） |
| `POST` | `/api/admin/users/{user_id}/reset-password` | 重置用户密码（管理员） |
| `POST` | `/api/admin/users/{user_id}/unban` | 解封用户（管理员） |

### Webhook（9）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/webhooks` | Webhook 列表 |
| `POST` | `/api/webhooks` | 创建 Webhook |
| `POST` | `/api/webhooks/deliveries/{delivery_id}/retry` | 重试投递 |
| `GET` | `/api/webhooks/events` | 支持的事件类型 |
| `PUT` | `/api/webhooks/{webhook_id}` | 更新 Webhook |
| `DELETE` | `/api/webhooks/{webhook_id}` | 删除 Webhook |
| `GET` | `/api/webhooks/{webhook_id}/deliveries` | 投递记录 |
| `POST` | `/api/webhooks/{webhook_id}/regenerate-secret` | 重新生成密钥 |
| `POST` | `/api/webhooks/{webhook_id}/test` | 测试 Webhook |

### 导入导出（7）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/admin/backup/full` | 全站备份 |
| `GET` | `/api/admin/backup/info` | 备份信息 |
| `POST` | `/api/admin/backup/restore` | 全站恢复 |
| `GET` | `/api/admin/export/markdown` | 导出为 Markdown |
| `GET` | `/api/admin/export/posts` | 导出文章 |
| `POST` | `/api/admin/import/markdown` | 导入 Markdown |
| `POST` | `/api/admin/import/posts` | 导入文章 |

### SEO（9）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/seo/config` | 获取 SEO 配置 |
| `PUT` | `/api/seo/config` | 【管理员】更新 SEO 配置 |
| `GET` | `/api/seo/open-graph/{resource_type}/{resource_id}` | Open Graph 数据 |
| `GET` | `/api/seo/robots.txt` | robots.txt |
| `GET` | `/api/seo/schema/{resource_type}/{resource_id}` | 结构化数据 |
| `GET` | `/api/seo/scores` | 【管理员】文章 SEO 评分 |
| `GET` | `/api/seo/sitemap-check` | 【管理员】校验 Sitemap 健康度 |
| `GET` | `/api/seo/sitemap.xml` | SEO sitemap.xml（同 /api/blog/sitemap.xml） |
| `POST` | `/api/seo/sitemap/generate` | 【管理员】强制重新生成 sitemap 缓存 |

### 高级管理（11）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/admin/logs` | 操作日志列表 |
| `GET` | `/api/admin/logs/export` | 导出操作日志 |
| `POST` | `/api/admin/posts/batch` | 批量操作文章 |
| `GET` | `/api/admin/posts/{post_id}/revisions` | 文章修订历史 |
| `GET` | `/api/admin/posts/{post_id}/revisions/compare` | 比较修订版本 |
| `GET` | `/api/admin/posts/{post_id}/revisions/{revision_id}` | 修订版本详情 |
| `POST` | `/api/admin/posts/{post_id}/revisions/{revision_id}/restore` | 恢复到指定版本 |
| `GET` | `/api/admin/trash` | 回收站列表 |
| `DELETE` | `/api/admin/trash` | 清空回收站 |
| `DELETE` | `/api/admin/trash/{trash_id}` | 永久删除 |
| `POST` | `/api/admin/trash/{trash_id}/restore` | 恢复项目 |

### 监控（8）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/monitoring/cache` | 缓存监控 |
| `GET` | `/api/monitoring/database` | 数据库监控 |
| `GET` | `/api/monitoring/health` | 健康检查 |
| `GET` | `/api/monitoring/performance` | 性能指标 |
| `GET` | `/api/monitoring/performance/summary` | 性能概览 |
| `GET` | `/api/monitoring/stats` | 系统统计 |
| `GET` | `/api/monitoring/trends` | 趋势数据 |
| `GET` | `/api/monitoring/visits/summary` | 访问量汇总 |

### TOC（3）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `POST` | `/api/toc/add-ids` | 添加标题 ID |
| `POST` | `/api/toc/extract` | 提取标题 |
| `POST` | `/api/toc/generate` | 生成目录 |

### 短代码（5）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/admin/shortcodes` | 列出所有已注册短代码（管理员） |
| `POST` | `/api/admin/shortcodes` | 预览短代码渲染结果（管理员） |
| `POST` | `/api/admin/shortcodes/register` | 注册简单模板式短代码（管理员） |
| `DELETE` | `/api/admin/shortcodes/{tag}` | 注销运行时已注册的短代码（管理员） |
| `POST` | `/api/shortcodes/render` | 渲染内容中的短代码 |

### 用户称号（9）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/admin/titles` | 称号列表 |
| `POST` | `/api/admin/titles` | 创建称号 |
| `POST` | `/api/admin/titles/assign` | 分配称号 |
| `GET` | `/api/admin/titles/{title_id}` | 称号详情 |
| `PUT` | `/api/admin/titles/{title_id}` | 更新称号 |
| `PATCH` | `/api/admin/titles/{title_id}` | 更新称号 |
| `DELETE` | `/api/admin/titles/{title_id}` | 删除称号 |
| `GET` | `/api/admin/users/{user_id}/title` | 获取用户称号 |
| `DELETE` | `/api/admin/users/{user_id}/title` | 移除用户称号 |

### 验证码（2）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/captcha` | 获取验证码 |
| `POST` | `/api/captcha/verify` | 验证验证码 |

### 私信（6）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `POST` | `/api/messages` | 发送私信 |
| `GET` | `/api/messages/conversations` | 获取会话列表 |
| `PUT` | `/api/messages/read-all/{user_id}` | 标记某会话全部已读 |
| `GET` | `/api/messages/unread/count` | 获取未读消息数 |
| `PUT` | `/api/messages/{message_id}/read` | 标记单条消息已读 |
| `GET` | `/api/messages/{user_id}` | 获取与某用户的会话 |

### 翻译（1）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `POST` | `/api/translate` | 翻译文本 |

### OOBE（16）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `POST` | `/api/oobe/admin-account` | 保存管理员账户信息（已废弃） |
| `GET` | `/api/oobe/check` | 环境检测 |
| `GET` | `/api/oobe/check-username` | 检查用户名是否可用 |
| `POST` | `/api/oobe/database-config` | 保存数据库配置（已废弃） |
| `GET` | `/api/oobe/dependencies` | 检查系统依赖 |
| `POST` | `/api/oobe/environment` | 保存环境选择（已废弃） |
| `POST` | `/api/oobe/install` | OOBE 一键安装 |
| `POST` | `/api/oobe/install-dependencies` | 一键安装缺失依赖 |
| `GET` | `/api/oobe/install-dependencies/stream` | 依赖安装进度 SSE 流 |
| `GET` | `/api/oobe/install/stream` | 一键安装进度 SSE 流 |
| `POST` | `/api/oobe/reset` | 重置 OOBE 状态 |
| `POST` | `/api/oobe/site-config` | 保存站点配置（已废弃） |
| `GET` | `/api/oobe/state` | 获取向导断点状态 |
| `GET` | `/api/oobe/status` | 获取 OOBE 状态 |
| `GET` | `/api/oobe/system-info` | 获取系统信息 |
| `GET` | `/api/oobe/test-database` | 测试数据库连接 |

### 公告（6）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/admin/announcements` | 管理员获取所有公告 |
| `POST` | `/api/admin/announcements` | 创建公告 |
| `PUT` | `/api/admin/announcements/{announcement_id}` | 更新公告 |
| `DELETE` | `/api/admin/announcements/{announcement_id}` | 删除公告 |
| `PUT` | `/api/admin/announcements/{announcement_id}/toggle` | 切换公告激活状态 |
| `GET` | `/api/announcements` | 获取当前活跃公告 |

### 网站动态（8）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/activities` | 获取已发布动态列表 |
| `POST` | `/api/activities` | 创建动态（登录用户可发布公开说说） |
| `POST` | `/api/activities/{activity_id}/like` | 给动态点赞 |
| `GET` | `/api/admin/activities` | 管理员获取所有动态 |
| `POST` | `/api/admin/activities` | 创建动态 |
| `PUT` | `/api/admin/activities/{activity_id}` | 更新动态 |
| `DELETE` | `/api/admin/activities/{activity_id}` | 删除动态 |
| `PUT` | `/api/admin/activities/{activity_id}/toggle` | 切换动态发布状态 |

### Hero轮播（6）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/admin/hero/slides` | 管理员获取所有 Hero 幻灯片 |
| `POST` | `/api/admin/hero/slides` | 创建 Hero 幻灯片 |
| `PUT` | `/api/admin/hero/slides/{slide_id}` | 更新 Hero 幻灯片 |
| `DELETE` | `/api/admin/hero/slides/{slide_id}` | 删除 Hero 幻灯片 |
| `PUT` | `/api/admin/hero/slides/{slide_id}/toggle` | 切换 Hero 幻灯片激活状态 |
| `GET` | `/api/hero/slides` | 获取当前活跃 Hero 幻灯片 |

### 文章系列（8）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/admin/series` | 管理员获取所有系列 |
| `POST` | `/api/admin/series` | 创建系列 |
| `PUT` | `/api/admin/series/{series_id}` | 更新系列 |
| `DELETE` | `/api/admin/series/{series_id}` | 删除系列 |
| `PUT` | `/api/admin/series/{series_id}/toggle` | 切换系列激活状态 |
| `POST` | `/api/post_series/complete` | 编辑器 autocomplete 同系列文章 |
| `GET` | `/api/series` | 获取文章系列列表 |
| `GET` | `/api/series/{slug}` | 获取系列详情 |

### 内容加密（4）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `POST` | `/api/admin/posts/{post_id}/encrypt` | 设置文章加密内容 |
| `PUT` | `/api/admin/posts/{post_id}/encrypt` | 更新文章加密内容（换密码/内容） |
| `DELETE` | `/api/admin/posts/{post_id}/encrypt` | 关闭文章内容加密 |
| `POST` | `/api/posts/{post_id}/decrypt` | 解密文章内容 |

### 文章加密工具（3）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `POST` | `/api/post_crypto/derive_keys` | 派生加密元数据 |
| `GET` | `/api/post_crypto/encrypted/{post_id}/preview` | 后台预览加密文章摘要 |
| `POST` | `/api/post_crypto/verify_access` | 验证文章访问密码 |

### 定时发布（3）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/admin/posts/scheduled` | 获取定时发布文章列表 |
| `PUT` | `/api/admin/posts/{post_id}/schedule` | 设置定时发布 |
| `DELETE` | `/api/admin/posts/{post_id}/schedule` | 取消定时发布 |

### 评论表情反应（3）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/comments/{comment_id}/reactions` | 获取评论表情反应统计 |
| `POST` | `/api/comments/{comment_id}/reactions` | 添加评论表情反应 |
| `DELETE` | `/api/comments/{comment_id}/reactions/{emoji}` | 取消评论表情反应 |

### 热门排行（1）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/ranking/posts` | 热门文章排行榜 |

### 性能监控（4）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `DELETE` | `/api/admin/performance/cleanup` | 清理性能监控旧数据 |
| `GET` | `/api/admin/performance/slow` | 最慢的请求 |
| `GET` | `/api/admin/performance/storage` | 性能数据存储统计 |
| `GET` | `/api/admin/performance/summary` | 性能统计摘要 |

### 仪表盘（1）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/admin/stats` | 管理后台统计数据 |

### 操作日志（1）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `DELETE` | `/api/admin/logs/retention` | 清理旧日志 |

### Admin 工具（4）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/admin/alembic/status` | 查看 Alembic 迁移状态 |
| `POST` | `/api/admin/alembic/upgrade` | 执行 Alembic schema 升级（upgrade head） |
| `POST` | `/api/admin/cache/flush` | 刷新缓存 |
| `GET` | `/api/admin/cache/status` | 查看缓存状态 |

### 系统设置（4）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/settings` | 获取所有设置分组 |
| `GET` | `/api/settings/public` | 公开站设置（无需登录） |
| `GET` | `/api/settings/{group}` | 获取单个设置分组 |
| `PATCH` | `/api/settings/{group}` | 更新单个设置分组 |

### 主题（4）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `PUT` | `/api/admin/themes/current` | 管理员设置默认调色板 |
| `GET` | `/api/themes/active` | 获取当前激活主题（公开，支持 Customizer 前台渲染） |
| `GET` | `/api/themes/current.css` | 获取当前启用调色板的 CSS |
| `GET` | `/api/themes/palettes` | 获取所有可用调色板 |

### 主题平台（12）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/admin/themes` | 获取主题列表（管理员） |
| `POST` | `/api/admin/themes` | 安装主题（local / upload / remote） |
| `GET` | `/api/admin/themes/market` | 获取主题市场索引 |
| `POST` | `/api/admin/themes/market/{slug}/install` | 从市场一键安装主题 |
| `POST` | `/api/admin/themes/scan` | 扫描本地主题目录 |
| `GET` | `/api/admin/themes/{slug}` | 获取主题详情（管理员） |
| `DELETE` | `/api/admin/themes/{slug}` | 删除主题记录 |
| `PUT` | `/api/admin/themes/{slug}/activate` | 激活主题 |
| `GET` | `/api/admin/themes/{slug}/mods` | 获取主题 Mods 与 Schema |
| `PUT` | `/api/admin/themes/{slug}/mods` | 全量替换主题 Mods |
| `PATCH` | `/api/admin/themes/{slug}/mods` | 增量更新主题 Mods |
| `POST` | `/api/admin/themes/{slug}/upgrade` | 升级主题（重扫磁盘清单） |

### 插件平台（16）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/admin/plugins` | 获取插件列表（管理员） |
| `POST` | `/api/admin/plugins` | 安装插件（local / upload / remote） |
| `POST` | `/api/admin/plugins/bulk` | 批量插件操作 |
| `GET` | `/api/admin/plugins/market` | 获取插件市场索引 |
| `POST` | `/api/admin/plugins/market/{slug}/install` | 从市场一键安装插件 |
| `GET` | `/api/admin/plugins/menu-registry` | 获取插件后台菜单注册表 |
| `POST` | `/api/admin/plugins/scan` | 扫描本地插件目录 |
| `GET` | `/api/admin/plugins/{slug}` | 获取插件详情（管理员） |
| `DELETE` | `/api/admin/plugins/{slug}` | 删除插件 |
| `POST` | `/api/admin/plugins/{slug}/activate` | 激活插件 |
| `POST` | `/api/admin/plugins/{slug}/deactivate` | 停用插件 |
| `GET` | `/api/admin/plugins/{slug}/settings` | 获取插件设置 |
| `PUT` | `/api/admin/plugins/{slug}/settings` | 全量替换插件设置 |
| `PATCH` | `/api/admin/plugins/{slug}/settings` | 增量更新插件设置 |
| `PATCH` | `/api/admin/plugins/{slug}/status` | 切换插件启用状态 |
| `POST` | `/api/admin/plugins/{slug}/upgrade` | 升级插件（从磁盘清单重新同步元数据） |

### 开发文档（2）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/docs/list` | 列出所有开发文档条目 |
| `GET` | `/api/docs/{slug}` | 读取单篇文档 |

### Bing壁纸（5）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/bing/image` | Bing 图片流式代理 + 本地缓存 |
| `GET` | `/api/bing/image/archive` | 获取 Bing 最近 N 天图片归档（骨架） |
| `GET` | `/api/bing/image/today` | 获取 Bing 今日图元数据 |
| `GET` | `/api/bing/wallpaper` | 获取每日 Bing 壁纸 |
| `GET` | `/api/bing/wallpapers` | 获取最近多天的 Bing 壁纸列表 |

### 评论（8）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `POST` | `/api/admin/comments/batch` | 【管理员】批量操作评论（approve/reject/spam/delete） |
| `POST` | `/api/admin/comments/{comment_id}/approve` | 【管理员】批准评论（legacy 子动作，建议统一使用 PATCH /api/admin/comments/{id} status=approved） |
| `POST` | `/api/admin/comments/{comment_id}/reject` | 【管理员】拒绝评论（legacy 子动作） |
| `POST` | `/api/admin/comments/{comment_id}/spam` | 【管理员】标记为垃圾评论（legacy 子动作） |
| `POST` | `/api/comments/{comment_id}/like` | 给评论点赞（简单计数，允许匿名） |
| `GET` | `/api/comments/{comment_id}/replies` | 获取某根评论的全部回复分页 |
| `GET` | `/api/posts/{post_id_or_slug}/comments` | 获取某文章根评论分页（含前 3 条最新回复与 reply_total） |
| `POST` | `/api/posts/{post_id_or_slug}/comments` | 发表评论（游客或登录用户均可） |

### 相册（2）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/gallery/albums` | 获取公开相册列表 |
| `GET` | `/api/gallery/albums/{album_id}` | 获取相册详情及照片 |

### 相册管理（9）

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| `GET` | `/api/admin/gallery/albums` | 【管理员】获取所有相册 |
| `POST` | `/api/admin/gallery/albums` | 【管理员】创建相册 |
| `PUT` | `/api/admin/gallery/albums/{album_id}` | 【管理员】更新相册 |
| `DELETE` | `/api/admin/gallery/albums/{album_id}` | 【管理员】删除相册 |
| `GET` | `/api/admin/gallery/albums/{album_id}/photos` | 【管理员】获取相册照片列表 |
| `POST` | `/api/admin/gallery/photos` | 【管理员】添加照片到相册 |
| `DELETE` | `/api/admin/gallery/photos/batch` | 【管理员】批量删除照片 |
| `PUT` | `/api/admin/gallery/photos/{photo_id}` | 【管理员】更新照片 |
| `DELETE` | `/api/admin/gallery/photos/{photo_id}` | 【管理员】删除照片 |

<!-- END AUTO-GENERATED:ENDPOINT_INDEX -->

