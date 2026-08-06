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
GET /api/admin/stats
Authorization: Bearer <access_token>
```

**响应**:
```json
{
  "posts": 100,
  "views": 10000,
  "comments": 500,
  "users": 50
}
```

### 访问趋势

```http
GET /api/admin/view-trends?days=7
Authorization: Bearer <access_token>
```

### 分类统计

```http
GET /api/admin/category-stats
Authorization: Bearer <access_token>
```

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
  "error_code": 429,
  "retry_after": 60
}
```
