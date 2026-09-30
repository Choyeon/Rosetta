<!-- 本文件由 backend/scripts/gen_api_detail.py 生成，请勿手改 -->
# Rosetta API 逐接口参考（自动生成）

> 本文件由 `backend/scripts/gen_api_detail.py` 从运行时 `app.openapi()` 生成，**请勿手改**。
> 接口有增删 → 重跑 `uv run python -m backend.scripts.gen_api_detail --write`。

共 **357 个操作**，字段级契约以本文件为准；语义错误码清单见 [error_codes.md](./error_codes.md)，重点接口的背景与坑见 [api_reference.md](./api_reference.md)。

## 通用约定

### 鉴权

受保护接口的请求头格式：

```
Authorization: Bearer <access_token>
X-CSRF-Token: <csrf_token>   # 写接口需要，从 GET /api/csrf 获取
```

`access_token` 有效期 1 小时，过期用 `POST /api/users/refresh` 换新。

### 响应包络

成功：`{"success": true, "data": {...}, "message": "..."}`（部分接口直出裸 dict，见各接口出参表）

失败：`{"success": false, "error_code": "语义码", "message": "人类可读说明", "errors": [{field, message, type}]?}`

前端判定刷新/OOBE 跳转依赖 `error_code` 而非裸状态码，见 `main.py::_STATUS_ERROR_CODES`。

### 全局通用错误码

以下状态码由全局异常处理器产出，任何接口都可能返回，正文章节不再重复：

| 状态码 | 说明 |
| --- | --- |
| `400` | 请求参数错误（`BAD_REQUEST`） |
| `401` | 未登录或令牌失效（`UNAUTHORIZED`）——前端应触发 refresh 或跳登录 |
| `403` | 已登录但权限不足（`FORBIDDEN`） |
| `404` | 资源不存在或不可见（`NOT_FOUND`） |
| `409` | 资源冲突（`CONFLICT`，如 slug 已存在） |
| `413` | 请求体过大（`PAYLOAD_TOO_LARGE`） |
| `422` | 参数校验失败（`VALIDATION_ERROR`，`errors[]` 含字段级明细） |
| `423` | 账户已锁定（`ACCOUNT_LOCKED`） |
| `429` | 触发限流（`RATE_LIMIT_EXCEEDED`，响应头带 `X-RateLimit-*` / `Retry-After`） |
| `500` | 服务端内部错误（`INTERNAL_SERVER_ERROR`） |
| `503` | 服务不可用（`SERVICE_UNAVAILABLE` / OOBE 未完成时的 `OOBE_REQUIRED`） |

完整语义错误码清单（含业务码）见 [error_codes.md](./error_codes.md)。

---

## 系统（3）

应用健康检查与基础信息

### `GET /`

- **摘要**：API 根路径
- **鉴权**：公开接口（无需鉴权）

返回应用名、版本与文档/健康检查入口的导航信息，无需鉴权。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/health`

- **摘要**：健康检查 (/api 前缀别名)
- **鉴权**：公开接口（无需鉴权）

前端 SSR/Nitro 同源代理场景下的健康检查入口，与 /health 等价。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /health`

- **摘要**：健康检查
- **鉴权**：公开接口（无需鉴权）

检查服务是否正常运行

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

---

## 用户（22）

注册、登录、令牌刷新、个人资料与密码管理

### `GET /api/users/`

- **摘要**：用户列表（精简投影）
- **鉴权**：需鉴权：`HTTPBearer`

获取用户列表，支持搜索和分页（需 staff）。响应为裸分页 dict（items/total/page/page_size/total_pages，无 success/data 信封）；items 内每项是 **UserListItem** 精简投影：只有 id/username/nickname/avatar/resolved_avatar_url/role/title/is_active/created_at。**不含 email / bio / qq / github / website** —— 列表页不展示这些字段，按 page_size=100 一页要多搬 100 份，且会把联系方式摊给所有能过鉴权的人。需要完整字段走 `GET /users/{id}`；需要封禁态与内容计数走 `GET /admin/users`。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PaginatedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | any[] | 是 |  |
| page | integer | 是 | 当前页码 |
| page_size | integer | 是 | 每页大小 |
| total | integer | 是 | 总记录数 |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/users/login`

- **摘要**：用户登录
- **鉴权**：公开接口（无需鉴权）

使用用户名或邮箱登录，返回访问令牌和刷新令牌。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `LoginRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| password | string | 是 | 密码 |
| username | string | 是 | 用户名或邮箱 |

```json
{
  "password": "string",
  "username": "string"
}
```

**出参**

`200` · 模型 `TokenResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| access_token | string | 是 | 访问令牌 |
| expires_in | integer | 是 | 过期时间（秒） |
| refresh_token | string | 是 | 刷新令牌 |
| token_type | string | 否 | 令牌类型 |

响应示例：

```json
{
  "access_token": "string",
  "expires_in": 0,
  "refresh_token": "string",
  "token_type": "bearer"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/users/logout`

- **摘要**：用户登出
- **鉴权**：需鉴权：`HTTPBearer`

撤销当前用户的刷新令牌。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/users/me`

- **摘要**：获取当前用户
- **鉴权**：需鉴权：`HTTPBearer`

获取当前登录用户的详细信息。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `UserResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| avatar | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| bio | string \| null | 否 | 个人简介 |
| cover_image | string \| null | 否 |  |
| created_at | string | 是 |  |
| email | string | 是 | 邮箱地址 |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 是 |  |
| is_staff | boolean | 是 |  |
| is_superuser | boolean | 是 |  |
| last_login | string \| null | 否 |  |
| nickname | string \| null | 否 | 昵称 |
| qq | string \| null | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| role | string \| null | 否 |  |
| title | object \| null | 否 |  |
| username | string | 是 | 用户名 |
| website | string \| null | 否 |  |

响应示例：

```json
{
  "avatar": "string",
  "avatar_source": "string",
  "bio": "string",
  "cover_image": "string",
  "created_at": "string",
  "email": "string",
  "github": "string",
  "id": 0,
  "is_active": false,
  "is_staff": false,
  "is_superuser": false,
  "last_login": "string",
  "nickname": "string",
  "qq": "string",
  "resolved_avatar_url": "string",
  "role": "string",
  "title": "string",
  "username": "string",
  "website": "string"
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `PUT /api/users/me`

- **摘要**：更新个人信息
- **鉴权**：需鉴权：`HTTPBearer`

更新当前用户的个人资料。若改动了文章作者卡片会展示的字段（昵称/头像/封面/简介/网站/GitHub/用户名），会自动失效该作者全部文章的详情缓存与列表/RSS 缓存。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `UserUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| avatar | string \| null | 否 |  |
| avatar_source | enum(`auto`, `custom`, `github`, `qq`, `gravatar`) \| null | 否 |  |
| bio | string \| null | 否 |  |
| cover_image | string \| null | 否 |  |
| github | string \| null | 否 |  |
| nickname | string \| null | 否 |  |
| qq | string \| null | 否 |  |
| website | string \| null | 否 |  |

```json
{
  "avatar": "string",
  "avatar_source": "string",
  "bio": "string",
  "cover_image": "string",
  "github": "string",
  "nickname": "string",
  "qq": "string",
  "website": "string"
}
```

**出参**

`200` · 模型 `UserResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| avatar | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| bio | string \| null | 否 | 个人简介 |
| cover_image | string \| null | 否 |  |
| created_at | string | 是 |  |
| email | string | 是 | 邮箱地址 |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 是 |  |
| is_staff | boolean | 是 |  |
| is_superuser | boolean | 是 |  |
| last_login | string \| null | 否 |  |
| nickname | string \| null | 否 | 昵称 |
| qq | string \| null | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| role | string \| null | 否 |  |
| title | object \| null | 否 |  |
| username | string | 是 | 用户名 |
| website | string \| null | 否 |  |

响应示例：

```json
{
  "avatar": "string",
  "avatar_source": "string",
  "bio": "string",
  "cover_image": "string",
  "created_at": "string",
  "email": "string",
  "github": "string",
  "id": 0,
  "is_active": false,
  "is_staff": false,
  "is_superuser": false,
  "last_login": "string",
  "nickname": "string",
  "qq": "string",
  "resolved_avatar_url": "string",
  "role": "string",
  "title": "string",
  "username": "string",
  "website": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/users/me`

- **摘要**：注销账户
- **鉴权**：需鉴权：`HTTPBearer`

注销当前用户账户（软删除），需要验证密码。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `_DeleteAccountBody`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| password | string | 是 | 当前密码验证 |

```json
{
  "password": "string"
}
```

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/users/me/avatar`

- **摘要**：更新头像
- **鉴权**：需鉴权：`HTTPBearer`

更新当前用户的头像；头像属于作者展示字段，会失效该作者全部文章的缓存。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `UserResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| avatar | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| bio | string \| null | 否 | 个人简介 |
| cover_image | string \| null | 否 |  |
| created_at | string | 是 |  |
| email | string | 是 | 邮箱地址 |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 是 |  |
| is_staff | boolean | 是 |  |
| is_superuser | boolean | 是 |  |
| last_login | string \| null | 否 |  |
| nickname | string \| null | 否 | 昵称 |
| qq | string \| null | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| role | string \| null | 否 |  |
| title | object \| null | 否 |  |
| username | string | 是 | 用户名 |
| website | string \| null | 否 |  |

响应示例：

```json
{
  "avatar": "string",
  "avatar_source": "string",
  "bio": "string",
  "cover_image": "string",
  "created_at": "string",
  "email": "string",
  "github": "string",
  "id": 0,
  "is_active": false,
  "is_staff": false,
  "is_superuser": false,
  "last_login": "string",
  "nickname": "string",
  "qq": "string",
  "resolved_avatar_url": "string",
  "role": "string",
  "title": "string",
  "username": "string",
  "website": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/users/me/change-password`

- **摘要**：修改密码（旧路径）
- **鉴权**：需鉴权：`HTTPBearer`

兼容旧路径：修改当前用户的密码，需要验证当前密码。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `PasswordChange`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| current_password | string | 是 | 当前密码 |
| new_password | string | 是 | 新密码（至少8位，包含大小写字母和数字） |

```json
{
  "current_password": "string",
  "new_password": "string"
}
```

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/users/me/cover`

- **摘要**：更新封面图
- **鉴权**：需鉴权：`HTTPBearer`

更新当前用户的封面图；封面图属于作者展示字段，会失效该作者全部文章的缓存。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `UserResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| avatar | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| bio | string \| null | 否 | 个人简介 |
| cover_image | string \| null | 否 |  |
| created_at | string | 是 |  |
| email | string | 是 | 邮箱地址 |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 是 |  |
| is_staff | boolean | 是 |  |
| is_superuser | boolean | 是 |  |
| last_login | string \| null | 否 |  |
| nickname | string \| null | 否 | 昵称 |
| qq | string \| null | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| role | string \| null | 否 |  |
| title | object \| null | 否 |  |
| username | string | 是 | 用户名 |
| website | string \| null | 否 |  |

响应示例：

```json
{
  "avatar": "string",
  "avatar_source": "string",
  "bio": "string",
  "cover_image": "string",
  "created_at": "string",
  "email": "string",
  "github": "string",
  "id": 0,
  "is_active": false,
  "is_staff": false,
  "is_superuser": false,
  "last_login": "string",
  "nickname": "string",
  "qq": "string",
  "resolved_avatar_url": "string",
  "role": "string",
  "title": "string",
  "username": "string",
  "website": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/users/me/password`

- **摘要**：修改密码
- **鉴权**：需鉴权：`HTTPBearer`

已登录用户，需提供旧密码。成功后踢所有会话下线。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `_PasswordChangeBody`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| new_password | string | 是 | 新密码 |
| old_password | string | 是 | 旧密码 |

```json
{
  "new_password": "string",
  "old_password": "string"
}
```

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/users/me/preferences`

- **摘要**：获取个人偏好
- **鉴权**：需鉴权：`HTTPBearer`

获取当前用户的偏好设置。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `UserPreferenceResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| public_profile | boolean | 是 |  |
| show_comments | boolean | 是 |  |
| show_email | boolean | 是 |  |
| show_posts | boolean | 是 |  |
| show_stats | boolean | 是 |  |
| theme | string | 是 |  |

响应示例：

```json
{
  "public_profile": false,
  "show_comments": false,
  "show_email": false,
  "show_posts": false,
  "show_stats": false,
  "theme": "string"
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `PUT /api/users/me/preferences`

- **摘要**：更新个人偏好
- **鉴权**：需鉴权：`HTTPBearer`

更新当前用户的偏好设置。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `UserPreferenceUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| public_profile | boolean \| null | 否 |  |
| show_comments | boolean \| null | 否 |  |
| show_email | boolean \| null | 否 |  |
| show_posts | boolean \| null | 否 |  |
| show_stats | boolean \| null | 否 |  |
| theme | string \| null | 否 |  |

```json
{
  "public_profile": "string",
  "show_comments": "string",
  "show_email": "string",
  "show_posts": "string",
  "show_stats": "string",
  "theme": "string"
}
```

**出参**

`200` · 模型 `UserPreferenceResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| public_profile | boolean | 是 |  |
| show_comments | boolean | 是 |  |
| show_email | boolean | 是 |  |
| show_posts | boolean | 是 |  |
| show_stats | boolean | 是 |  |
| theme | string | 是 |  |

响应示例：

```json
{
  "public_profile": false,
  "show_comments": false,
  "show_email": false,
  "show_posts": false,
  "show_stats": false,
  "theme": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/users/password-reset`

- **摘要**：重置密码（验证码 + 新密码）
- **鉴权**：公开接口（无需鉴权）

使用请求阶段投递到邮箱的验证码重置密码。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `_PasswordResetBody`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | string | 是 | 6 位数字验证码 |
| new_password | string | 是 | 新密码 |
| token_or_email | string | 是 | 邮箱或用户名 |

```json
{
  "code": "string",
  "new_password": "string",
  "token_or_email": "string"
}
```

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/users/password-reset-request`

- **摘要**：请求密码重置
- **鉴权**：公开接口（无需鉴权）

通过邮箱/用户名，不泄露账号是否存在（恒定 message + success=true，永远 200）。公开接口、按 IP 限流。验证码 15 分钟有效；SMTP 未配置或投递失败时验证码会被作废（不留发不出去却能通过校验的孤儿凭证），响应形态不变。仅非生产 + DEBUG 环境额外返回 debug.reset_code 供本地调试。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `_PasswordResetRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| email_or_username | string | 是 | 邮箱或用户名 |

```json
{
  "email_or_username": "string"
}
```

**出参**

`200` · 模型 `PasswordResetRequestResponseDoc`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| debug | object \| null | 否 | 调试回显：只有非生产环境且 DEBUG=true 时存在（生产环境绝不回传验证码），该分支下也不会走「投递失败作废」逻辑 |
| message | string | 是 | 恒定文案（无论账号是否存在、邮件是否投递成功都是同一句），避免枚举账号 |
| success | boolean | 否 | 固定为 true：本端点成功路径永远 200，不区分投递结果 |

响应示例：

```json
{
  "debug": "string",
  "message": "string",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/users/refresh`

- **摘要**：刷新令牌
- **鉴权**：公开接口（无需鉴权）

使用获取新的访问令牌（rotate：单次使用）。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_refresh_token_api_users_refresh_post`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| refresh_token | string | 是 | 刷新令牌 |

```json
{
  "refresh_token": "string"
}
```

**出参**

`200` · 模型 `TokenResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| access_token | string | 是 | 访问令牌 |
| expires_in | integer | 是 | 过期时间（秒） |
| refresh_token | string | 是 | 刷新令牌 |
| token_type | string | 否 | 令牌类型 |

响应示例：

```json
{
  "access_token": "string",
  "expires_in": 0,
  "refresh_token": "string",
  "token_type": "bearer"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/users/register`

- **摘要**：用户注册
- **鉴权**：公开接口（无需鉴权）

注册新用户账号，成功后自动登录返回令牌。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `UserCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| avatar_source | enum(`auto`, `custom`, `github`, `qq`, `gravatar`) | 否 | 头像来源 |
| bio | string \| null | 否 | 个人简介 |
| email | string | 是 | 邮箱地址 |
| github | string \| null | 否 | GitHub 主页 |
| nickname | string \| null | 否 | 昵称 |
| password | string | 是 | 密码（至少8位，包含大小写字母和数字） |
| qq | string \| null | 否 | QQ 号（可选，用于头像识别） |
| username | string | 是 | 用户名（只允许字母、数字、下划线和连字符） |
| website | string \| null | 否 | 个人网站 |

```json
{
  "avatar_source": "auto",
  "bio": "string",
  "email": "string",
  "github": "string",
  "nickname": "string",
  "password": "string",
  "qq": "string",
  "username": "string",
  "website": "string"
}
```

**出参**

`201` · 模型 `TokenResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| access_token | string | 是 | 访问令牌 |
| expires_in | integer | 是 | 过期时间（秒） |
| refresh_token | string | 是 | 刷新令牌 |
| token_type | string | 否 | 令牌类型 |

响应示例：

```json
{
  "access_token": "string",
  "expires_in": 0,
  "refresh_token": "string",
  "token_type": "bearer"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/users/username/{username}`

- **摘要**：通过用户名获取用户
- **鉴权**：需鉴权：`HTTPBearer`

根据用户名获取用户公开信息。这是前台作者主页 `/authors/<username>` 的资料来源，关闭「公开资料」的作者在此对外返回 404（口径同 `GET /users/{user_id}`）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `UserResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| avatar | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| bio | string \| null | 否 | 个人简介 |
| cover_image | string \| null | 否 |  |
| created_at | string | 是 |  |
| email | string | 是 | 邮箱地址 |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 是 |  |
| is_staff | boolean | 是 |  |
| is_superuser | boolean | 是 |  |
| last_login | string \| null | 否 |  |
| nickname | string \| null | 否 | 昵称 |
| qq | string \| null | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| role | string \| null | 否 |  |
| title | object \| null | 否 |  |
| username | string | 是 | 用户名 |
| website | string \| null | 否 |  |

响应示例：

```json
{
  "avatar": "string",
  "avatar_source": "string",
  "bio": "string",
  "cover_image": "string",
  "created_at": "string",
  "email": "string",
  "github": "string",
  "id": 0,
  "is_active": false,
  "is_staff": false,
  "is_superuser": false,
  "last_login": "string",
  "nickname": "string",
  "qq": "string",
  "resolved_avatar_url": "string",
  "role": "string",
  "title": "string",
  "username": "string",
  "website": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/users/username/{username}/preferences`

- **摘要**：获取用户隐私设置
- **鉴权**：需鉴权：`HTTPBearer`

获取用户的隐私设置（公开部分）。公开接口、无需鉴权。响应为裸 dict（5 个布尔开关，无 data 信封）；用户从未动过设置（无偏好行）时返回与建表默认一致的默认开关组（show_email 默认拒绝）。用户不存在返回 404。**资料已关闭公开（`public_profile=False`）时同样返回 404**——把整组开关摊给匿名调用方等于宣布「这个账号存在，只是藏起来了」，会打穿资料接口刻意选定的统一 404 防枚举口径。仅本人可读到自己的真实开关组。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `UserPreferencesPublicDoc`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| public_profile | boolean | 否 | 是否公开个人资料页 |
| show_comments | boolean | 否 | 是否公开评论列表 |
| show_email | boolean | 否 | 是否对外展示邮箱（默认拒绝） |
| show_posts | boolean | 否 | 是否公开文章列表 |
| show_stats | boolean | 否 | 是否公开统计数据 |

响应示例：

```json
{
  "public_profile": true,
  "show_comments": true,
  "show_email": false,
  "show_posts": true,
  "show_stats": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/users/{user_id}`

- **摘要**：获取用户信息
- **鉴权**：需鉴权：`HTTPBearer`

根据 ID 获取用户公开信息。用户关闭「公开资料」（`public_profile=False`）时对外统一返回 404（与「查无此人」同口径，避免账号枚举），仅本人可读。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `UserResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| avatar | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| bio | string \| null | 否 | 个人简介 |
| cover_image | string \| null | 否 |  |
| created_at | string | 是 |  |
| email | string | 是 | 邮箱地址 |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 是 |  |
| is_staff | boolean | 是 |  |
| is_superuser | boolean | 是 |  |
| last_login | string \| null | 否 |  |
| nickname | string \| null | 否 | 昵称 |
| qq | string \| null | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| role | string \| null | 否 |  |
| title | object \| null | 否 |  |
| username | string | 是 | 用户名 |
| website | string \| null | 否 |  |

响应示例：

```json
{
  "avatar": "string",
  "avatar_source": "string",
  "bio": "string",
  "cover_image": "string",
  "created_at": "string",
  "email": "string",
  "github": "string",
  "id": 0,
  "is_active": false,
  "is_staff": false,
  "is_superuser": false,
  "last_login": "string",
  "nickname": "string",
  "qq": "string",
  "resolved_avatar_url": "string",
  "role": "string",
  "title": "string",
  "username": "string",
  "website": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/users/{user_id}/comments`

- **摘要**：用户评论列表
- **鉴权**：需鉴权：`HTTPBearer`

获取指定用户发表的评论列表。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PaginatedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | any[] | 是 |  |
| page | integer | 是 | 当前页码 |
| page_size | integer | 是 | 每页大小 |
| total | integer | 是 | 总记录数 |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/users/{user_id}/posts`

- **摘要**：用户文章列表
- **鉴权**：需鉴权：`HTTPBearer`

获取指定用户发布的文章列表。摘要与 `blog.py` 列表口径一致，经内容渲染管线处理（短代码 + the_excerpt filter 链），插件不会在此页失效。隐私：作者关闭「公开资料」（`public_profile=False`）时返回 404（主页不存在口径），只关闭 `show_posts` 时返回空页 200。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PaginatedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | any[] | 是 |  |
| page | integer | 是 | 当前页码 |
| page_size | integer | 是 | 每页大小 |
| total | integer | 是 | 总记录数 |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/users/{user_id}/stats`

- **摘要**：用户统计信息
- **鉴权**：需鉴权：`HTTPBearer`

获取指定用户的统计数据。公开接口、无需鉴权。响应为裸 dict（user_id/posts_count/comments_count/total_views/total_likes/joined_at，无信封）；计数在无数据时兜底为 0，joined_at 为 ISO 8601 字符串或 null。用户不存在返回 404。隐私口径：作者关闭「公开资料」（`public_profile=False`）时返回 404（同资料接口）；只关闭「显示统计」（`show_stats=False`）时返回 200 + 全零计数，与「还没有任何活动」不可区分正是隐藏语义，且此时不再执行任何聚合查询。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `UserStatsDoc`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| comments_count | integer | 是 | 已过审评论数（active=True，无数据为 0） |
| joined_at | string \| null | 否 | 注册时间：handler 手工 isoformat() 的字符串，无创建时间时为 null |
| posts_count | integer | 是 | 已发布文章数（status=published，无数据为 0） |
| total_likes | integer | 是 | 本人全部文章（含草稿）收到的点赞总数，无数据为 0 |
| total_views | integer | 是 | 本人已发布文章的 views 列求和（SUM 无行为 null，兜底成 0） |
| user_id | integer | 是 | 用户 ID（路径参数回显） |

响应示例：

```json
{
  "comments_count": 0,
  "joined_at": "string",
  "posts_count": 0,
  "total_likes": 0,
  "total_views": 0,
  "user_id": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 博客（41）

文章、分类、标签、评论的公开与管理接口

### `GET /api/blog/archive`

- **摘要**：文章归档
- **鉴权**：公开接口（无需鉴权）

按年月分组获取已发布文章的归档列表。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "count": 0,
    "month": 0,
    "posts": [
      {
        "category": "…",
        "created_at": "…",
        "id": "…",
        "published_at": "…",
        "slug": "…",
        "title": "…",
        "views": "…"
      }
    ],
    "year": 0
  }
]
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/archive/stats`

- **摘要**：归档统计
- **鉴权**：公开接口（无需鉴权）

获取信息，包括总文章数、年份数等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `ArchiveStats`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| total_posts | integer | 是 | 已发布文章总数 |
| total_years | integer | 是 | 有文章的年份数 |
| year_stats | object<string, integer> | 否 | 年份 → 该年文章数。注意 JSON 序列化后键是字符串，如 {"2026": 12} |
| years | integer[] | 否 | 年份列表，倒序 |

响应示例：

```json
{
  "total_posts": 0,
  "total_years": 0,
  "year_stats": {},
  "years": [
    0
  ]
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/blog/archive/{year}`

- **摘要**：按年份获取归档
- **鉴权**：公开接口（无需鉴权）

获取指定年份的文章归档。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "count": 0,
    "month": 0,
    "posts": [
      {
        "category": "…",
        "created_at": "…",
        "id": "…",
        "published_at": "…",
        "slug": "…",
        "title": "…",
        "views": "…"
      }
    ],
    "year": 0
  }
]
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/archive/{year}/{month}`

- **摘要**：按年月获取归档
- **鉴权**：公开接口（无需鉴权）

获取指定年月的文章归档。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `ArchiveMonthPage`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| count | integer | 是 | 该月返回的文章条数（等于 posts 长度） |
| month | integer | 是 | 月份（1-12） |
| page | integer | 否 | 当前页码，从 1 开始 |
| page_size | integer | 否 | 每页条数 |
| posts | object[] | 否 | 该月文章条目，按月内倒序 |
| total_pages | integer | 否 | 总页数；无数据时为 0 |
| year | integer | 是 | 年份 |

响应示例：

```json
{
  "count": 0,
  "month": 0,
  "page": 1,
  "page_size": 20,
  "posts": [
    {
      "category": "string",
      "created_at": "string",
      "id": 0,
      "published_at": "string",
      "slug": "string",
      "title": "string",
      "views": 0
    }
  ],
  "total_pages": 0,
  "year": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/categories`

- **摘要**：分类列表
- **鉴权**：公开接口（无需鉴权）

获取所有分类及其文章数量（返回多语言原始dict，前端自行本地化显示）。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "color": "string",
    "cover_image": "string",
    "created_at": "string",
    "description": "string",
    "icon": "string",
    "id": 0,
    "name": {},
    "post_count": 0,
    "slug": "string"
  }
]
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/blog/categories`

- **摘要**：创建分类
- **鉴权**：需鉴权：`HTTPBearer`

创建新分类，需要管理员权限。返回完整 i18n dict 供 I18nTabsEditor 回填。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `CategoryCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| color | string | 否 |  |
| description | object<string, string> \| null | 否 | 多语言分类描述 |
| icon | string \| null | 否 |  |
| name | object<string, string> | 是 | 多语言分类名称，如 {'zh': '技术', 'en': 'Technology', 'ja': '技術', 'zh_Hant': '技術'} |
| slug | string \| null | 否 |  |

```json
{
  "color": "#3B82F6",
  "description": "string",
  "icon": "string",
  "name": {},
  "slug": "string"
}
```

**出参**

`201` · 模型 `CategoryResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| color | string | 是 |  |
| cover_image | string \| null | 否 |  |
| created_at | string | 是 |  |
| description | object<string, string> \| null | 否 |  |
| icon | string \| null | 否 |  |
| id | integer | 是 |  |
| name | object<string, string> | 是 |  |
| post_count | integer | 否 |  |
| slug | string | 是 |  |

响应示例：

```json
{
  "color": "string",
  "cover_image": "string",
  "created_at": "string",
  "description": "string",
  "icon": "string",
  "id": 0,
  "name": {},
  "post_count": 0,
  "slug": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/categories/slug/{slug}`

- **摘要**：获取分类详情
- **鉴权**：公开接口（无需鉴权）

根据 slug （返回完整 i18n dict）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `CategoryResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| color | string | 是 |  |
| cover_image | string \| null | 否 |  |
| created_at | string | 是 |  |
| description | object<string, string> \| null | 否 |  |
| icon | string \| null | 否 |  |
| id | integer | 是 |  |
| name | object<string, string> | 是 |  |
| post_count | integer | 否 |  |
| slug | string | 是 |  |

响应示例：

```json
{
  "color": "string",
  "cover_image": "string",
  "created_at": "string",
  "description": "string",
  "icon": "string",
  "id": 0,
  "name": {},
  "post_count": 0,
  "slug": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/blog/categories/{category_id}`

- **摘要**：更新分类
- **鉴权**：需鉴权：`HTTPBearer`

信息，需要管理员权限。返回完整 i18n dict 供 I18nTabsEditor 回填。改名/改色会同步失效该分类下所有文章的详情缓存（`post:{slug}:{lang}`）与列表/RSS 缓存，避免前台文章页在 TTL 内继续显示旧分类名/颜色。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `CategoryUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| color | string \| null | 否 |  |
| cover_image | string \| null | 否 |  |
| description | object<string, string> \| null | 否 |  |
| icon | string \| null | 否 |  |
| name | object<string, string> \| null | 否 |  |
| slug | string \| null | 否 |  |

```json
{
  "color": "string",
  "cover_image": "string",
  "description": "string",
  "icon": "string",
  "name": "string",
  "slug": "string"
}
```

**出参**

`200` · 模型 `CategoryResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| color | string | 是 |  |
| cover_image | string \| null | 否 |  |
| created_at | string | 是 |  |
| description | object<string, string> \| null | 否 |  |
| icon | string \| null | 否 |  |
| id | integer | 是 |  |
| name | object<string, string> | 是 |  |
| post_count | integer | 否 |  |
| slug | string | 是 |  |

响应示例：

```json
{
  "color": "string",
  "cover_image": "string",
  "created_at": "string",
  "description": "string",
  "icon": "string",
  "id": 0,
  "name": {},
  "post_count": 0,
  "slug": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/blog/categories/{category_id}`

- **摘要**：删除分类
- **鉴权**：需鉴权：`HTTPBearer`

，需要管理员权限。删除会把该分类下文章的 category_id 置空（SET NULL），并失效这些文章的详情/列表/RSS 缓存，使前台立即回落到「无分类」而非旧分类。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/posts`

- **摘要**：文章列表
- **鉴权**：需鉴权：`HTTPBearer`

获取，支持分类、标签、作者（用户名）筛选和关键词搜索。支持多语言返回。`author` 走作者归档口径：作者不存在返回空页（不 404，让资料接口负责 404）；作者把 `show_posts` 关掉后，非本人/非管理员同样返回空页（与 `GET /users/{user_id}/posts` 同一道隐私闸门）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PaginatedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | any[] | 是 |  |
| page | integer | 是 | 当前页码 |
| page_size | integer | 是 | 每页大小 |
| total | integer | 是 | 总记录数 |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/blog/posts`

- **摘要**：创建文章
- **鉴权**：需鉴权：`HTTPBearer`

创建新文章，需要管理员权限。支持多语言内容。可设置访问密码。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `PostCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| allow_comments | boolean | 否 |  |
| category_id | integer \| null | 否 |  |
| content | object<string, string> | 是 | 多语言文章内容 |
| cover_image | string \| null | 否 |  |
| encryption_algorithm | string | 否 |  |
| encryption_enabled | boolean | 否 |  |
| encryption_hint | string \| null | 否 |  |
| encryption_salt | string \| null | 否 |  |
| encryption_verifier | string \| null | 否 |  |
| excerpt | object<string, string> \| null | 否 | 多语言摘要 |
| is_pinned | boolean | 否 |  |
| meta_description | object<string, string> \| null | 否 | 多语言 SEO 描述 |
| meta_keywords | object<string, string> \| null | 否 | 多语言 SEO 关键词 |
| meta_title | object<string, string> \| null | 否 | 多语言 SEO 标题 |
| password | string \| null | 否 |  |
| scheduled_at | string \| null | 否 | 定时发布时间，status=scheduled 时生效 |
| series_id | integer \| null | 否 | 所属系列 ID |
| series_order | integer | 否 | 系列内排序 |
| slug | string \| null | 否 |  |
| source | string | 否 |  |
| source_url | string \| null | 否 |  |
| status | string | 否 |  |
| subtitle | object<string, string> \| null | 否 | 多语言副标题 |
| tag_ids | integer[] | 否 |  |
| title | object<string, string> | 是 | 多语言文章标题 |
| view_password | string \| null | 否 | (保留字段，请勿使用明文) |
| visibility | string | 否 | 可见性: public(公开)/password(密码保护)/private(私密仅作者可见) |

```json
{
  "allow_comments": true,
  "category_id": "string",
  "content": {},
  "cover_image": "string",
  "encryption_algorithm": "AES-256-GCM",
  "encryption_enabled": false,
  "encryption_hint": "string",
  "encryption_salt": "string",
  "encryption_verifier": "string",
  "excerpt": "string",
  "is_pinned": false,
  "meta_description": "string",
  "meta_keywords": "string",
  "meta_title": "string",
  "password": "string",
  "scheduled_at": "string",
  "series_id": "string",
  "series_order": 0,
  "slug": "string",
  "source": "原创",
  "source_url": "string",
  "status": "draft",
  "subtitle": "string",
  "tag_ids": [
    0
  ],
  "title": {},
  "view_password": "string",
  "visibility": "public"
}
```

**出参**

`201` · 模型 `PostLocalizedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| allow_comments | boolean | 是 |  |
| audio | string \| null | 否 |  |
| author | object | 是 | 公开作者卡片模型（用于文章 / 相册等资源的 ``author`` 字段）。 与 :class:`UserResponse` 的差别就是本模型**没有**的那些字段： ``email``、``qq``、``is_active`` / ``is_staff`` / ``is_sup … （完整说明见 `/docs`） |
| author.avatar | string \| null | 否 |  |
| author.avatar_source | string \| null | 否 |  |
| author.bio | string \| null | 否 |  |
| author.cover_image | string \| null | 否 |  |
| author.created_at | string | 是 |  |
| author.github | string \| null | 否 |  |
| author.id | integer | 是 |  |
| author.nickname | string \| null | 否 |  |
| author.resolved_avatar_url | string \| null | 否 |  |
| author.title | object \| null | 否 |  |
| author.username | string | 是 |  |
| author.website | string \| null | 否 |  |
| category | object \| null | 否 |  |
| comments_count | integer | 否 |  |
| content | string | 是 |  |
| cover_image | string \| null | 否 |  |
| created_at | string | 是 |  |
| excerpt | string \| null | 否 |  |
| id | integer | 是 |  |
| is_password_protected | boolean | 否 |  |
| is_pinned | boolean | 是 |  |
| likes_count | integer | 否 |  |
| meta_description | string \| null | 否 |  |
| meta_keywords | string \| null | 否 |  |
| meta_title | string \| null | 否 |  |
| password | string \| null | 否 |  |
| published_at | string \| null | 否 |  |
| reading_time | integer | 否 |  |
| slug | string | 是 |  |
| source | string | 是 |  |
| source_url | string \| null | 否 |  |
| status | string | 是 |  |
| subtitle | string \| null | 否 |  |
| tags | object[] | 否 |  |
| title | string | 是 |  |
| updated_at | string | 是 |  |
| video | string \| null | 否 |  |
| … 其余 3 个字段 | | | 见 `/docs` |

响应示例：

```json
{
  "allow_comments": false,
  "audio": "string",
  "author": {
    "avatar": "string",
    "avatar_source": "string",
    "bio": "string",
    "cover_image": "string",
    "created_at": "string",
    "github": "string",
    "id": 0,
    "nickname": "string",
    "resolved_avatar_url": "string",
    "title": "string",
    "username": "string",
    "website": "string"
  },
  "category": "string",
  "comments_count": 0,
  "content": "string",
  "cover_image": "string",
  "created_at": "string",
  "excerpt": "string",
  "id": 0,
  "is_password_protected": false,
  "is_pinned": false,
  "likes_count": 0,
  "meta_description": "string",
  "meta_keywords": "string",
  "meta_title": "string",
  "password": "string",
  "published_at": "string",
  "reading_time": 1,
  "slug": "string",
  "source": "string",
  "source_url": "string",
  "status": "string",
  "subtitle": "string",
  "tags": [],
  "title": "string",
  "updated_at": "string",
  "video": "string",
  "video_url": "string",
  "views": 0,
  "visibility": "public"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/blog/posts/batch-status`

- **摘要**：批量更新文章状态
- **鉴权**：需鉴权：`HTTPBearer`

批量更新当前用户可操作文章的状态，仅作者或超级管理员可操作。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `BatchPostStatusUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| post_ids | integer[] | 是 |  |
| status | enum(`draft`, `published`, `scheduled`) | 是 |  |

```json
{
  "post_ids": [
    0
  ],
  "status": "draft"
}
```

**出参**

`200` · 模型 `BatchPostStatusResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object<string, integer> | 是 |  |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "data": {},
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/posts/hot`

- **摘要**：热门文章（HackerNews 风格热榜）
- **鉴权**：公开接口（无需鉴权）

按 HackerNews 公式的综合热度排序：（浏览 + 点赞×10 + 评论×20）/(发布小时+2)^1.8。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "author": {
      "avatar": "string",
      "avatar_source": "string",
      "bio": "string",
      "cover_image": "string",
      "created_at": "string",
      "github": "string",
      "id": 0,
      "nickname": "string",
      "resolved_avatar_url": "string",
      "title": "string",
      "username": "string",
      "website": "string"
    },
    "category": "string",
    "comments_count": 0,
    "cover_image": "string",
    "created_at": "string",
    "excerpt": "string",
    "id": 0,
    "is_pinned": false,
    "likes_count": 0,
    "published_at": "string",
    "reading_time": 1,
    "slug": "string",
    "status": "string",
    "subtitle": "string",
    "tags": [],
    "title": "string",
    "updated_at": "string",
    "views": 0
  }
]
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/posts/id/{post_id}`

- **摘要**：按ID获取文章
- **鉴权**：需鉴权：`HTTPBearer`

根据文章ID获取文章详情。可见性口径与 slug 详情端点一致：草稿/未到排期时间的文章仅作者与职员可见；加密文章需通过 X-Post-Password 验证才返回正文；密码散列永不出现在响应中。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PostLocalizedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| allow_comments | boolean | 是 |  |
| audio | string \| null | 否 |  |
| author | object | 是 | 公开作者卡片模型（用于文章 / 相册等资源的 ``author`` 字段）。 与 :class:`UserResponse` 的差别就是本模型**没有**的那些字段： ``email``、``qq``、``is_active`` / ``is_staff`` / ``is_sup … （完整说明见 `/docs`） |
| author.avatar | string \| null | 否 |  |
| author.avatar_source | string \| null | 否 |  |
| author.bio | string \| null | 否 |  |
| author.cover_image | string \| null | 否 |  |
| author.created_at | string | 是 |  |
| author.github | string \| null | 否 |  |
| author.id | integer | 是 |  |
| author.nickname | string \| null | 否 |  |
| author.resolved_avatar_url | string \| null | 否 |  |
| author.title | object \| null | 否 |  |
| author.username | string | 是 |  |
| author.website | string \| null | 否 |  |
| category | object \| null | 否 |  |
| comments_count | integer | 否 |  |
| content | string | 是 |  |
| cover_image | string \| null | 否 |  |
| created_at | string | 是 |  |
| excerpt | string \| null | 否 |  |
| id | integer | 是 |  |
| is_password_protected | boolean | 否 |  |
| is_pinned | boolean | 是 |  |
| likes_count | integer | 否 |  |
| meta_description | string \| null | 否 |  |
| meta_keywords | string \| null | 否 |  |
| meta_title | string \| null | 否 |  |
| password | string \| null | 否 |  |
| published_at | string \| null | 否 |  |
| reading_time | integer | 否 |  |
| slug | string | 是 |  |
| source | string | 是 |  |
| source_url | string \| null | 否 |  |
| status | string | 是 |  |
| subtitle | string \| null | 否 |  |
| tags | object[] | 否 |  |
| title | string | 是 |  |
| updated_at | string | 是 |  |
| video | string \| null | 否 |  |
| … 其余 3 个字段 | | | 见 `/docs` |

响应示例：

```json
{
  "allow_comments": false,
  "audio": "string",
  "author": {
    "avatar": "string",
    "avatar_source": "string",
    "bio": "string",
    "cover_image": "string",
    "created_at": "string",
    "github": "string",
    "id": 0,
    "nickname": "string",
    "resolved_avatar_url": "string",
    "title": "string",
    "username": "string",
    "website": "string"
  },
  "category": "string",
  "comments_count": 0,
  "content": "string",
  "cover_image": "string",
  "created_at": "string",
  "excerpt": "string",
  "id": 0,
  "is_password_protected": false,
  "is_pinned": false,
  "likes_count": 0,
  "meta_description": "string",
  "meta_keywords": "string",
  "meta_title": "string",
  "password": "string",
  "published_at": "string",
  "reading_time": 1,
  "slug": "string",
  "source": "string",
  "source_url": "string",
  "status": "string",
  "subtitle": "string",
  "tags": [],
  "title": "string",
  "updated_at": "string",
  "video": "string",
  "video_url": "string",
  "views": 0,
  "visibility": "public"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/posts/recommended`

- **摘要**：推荐文章列表
- **鉴权**：需鉴权：`HTTPBearer`

获取，基于浏览量、点赞数、评论数、时间衰减和标签匹配的综合算法。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PaginatedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | any[] | 是 |  |
| page | integer | 是 | 当前页码 |
| page_size | integer | 是 | 每页大小 |
| total | integer | 是 | 总记录数 |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/blog/posts/{post_id}`

- **摘要**：更新文章
- **鉴权**：需鉴权：`HTTPBearer`

内容，仅作者或超级管理员可操作。支持多语言内容。可设置访问密码。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `PostUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| allow_comments | boolean \| null | 否 |  |
| audio | string \| null | 否 |  |
| category_id | integer \| null | 否 |  |
| content | object<string, string> \| null | 否 |  |
| cover_image | string \| null | 否 |  |
| encryption_algorithm | string \| null | 否 |  |
| encryption_enabled | boolean \| null | 否 |  |
| encryption_hint | string \| null | 否 |  |
| encryption_salt | string \| null | 否 |  |
| encryption_verifier | string \| null | 否 |  |
| excerpt | object<string, string> \| null | 否 |  |
| is_pinned | boolean \| null | 否 |  |
| meta_description | object<string, string> \| null | 否 |  |
| meta_keywords | object<string, string> \| null | 否 |  |
| meta_title | object<string, string> \| null | 否 |  |
| password | string \| null | 否 |  |
| scheduled_at | string \| null | 否 |  |
| series_id | integer \| null | 否 |  |
| series_order | integer \| null | 否 |  |
| slug | string \| null | 否 |  |
| source | string \| null | 否 |  |
| source_url | string \| null | 否 |  |
| status | string \| null | 否 |  |
| subtitle | object<string, string> \| null | 否 |  |
| tag_ids | integer[] \| null | 否 |  |
| title | object<string, string> \| null | 否 |  |
| video | string \| null | 否 |  |
| video_url | string \| null | 否 |  |
| view_password | string \| null | 否 |  |
| visibility | string \| null | 否 |  |

```json
{
  "allow_comments": "string",
  "audio": "string",
  "category_id": "string",
  "content": "string",
  "cover_image": "string",
  "encryption_algorithm": "string",
  "encryption_enabled": "string",
  "encryption_hint": "string",
  "encryption_salt": "string",
  "encryption_verifier": "string",
  "excerpt": "string",
  "is_pinned": "string",
  "meta_description": "string",
  "meta_keywords": "string",
  "meta_title": "string",
  "password": "string",
  "scheduled_at": "string",
  "series_id": "string",
  "series_order": "string",
  "slug": "string",
  "source": "string",
  "source_url": "string",
  "status": "string",
  "subtitle": "string",
  "tag_ids": "string",
  "title": "string",
  "video": "string",
  "video_url": "string",
  "view_password": "string",
  "visibility": "string"
}
```

**出参**

`200` · 模型 `PostLocalizedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| allow_comments | boolean | 是 |  |
| audio | string \| null | 否 |  |
| author | object | 是 | 公开作者卡片模型（用于文章 / 相册等资源的 ``author`` 字段）。 与 :class:`UserResponse` 的差别就是本模型**没有**的那些字段： ``email``、``qq``、``is_active`` / ``is_staff`` / ``is_sup … （完整说明见 `/docs`） |
| author.avatar | string \| null | 否 |  |
| author.avatar_source | string \| null | 否 |  |
| author.bio | string \| null | 否 |  |
| author.cover_image | string \| null | 否 |  |
| author.created_at | string | 是 |  |
| author.github | string \| null | 否 |  |
| author.id | integer | 是 |  |
| author.nickname | string \| null | 否 |  |
| author.resolved_avatar_url | string \| null | 否 |  |
| author.title | object \| null | 否 |  |
| author.username | string | 是 |  |
| author.website | string \| null | 否 |  |
| category | object \| null | 否 |  |
| comments_count | integer | 否 |  |
| content | string | 是 |  |
| cover_image | string \| null | 否 |  |
| created_at | string | 是 |  |
| excerpt | string \| null | 否 |  |
| id | integer | 是 |  |
| is_password_protected | boolean | 否 |  |
| is_pinned | boolean | 是 |  |
| likes_count | integer | 否 |  |
| meta_description | string \| null | 否 |  |
| meta_keywords | string \| null | 否 |  |
| meta_title | string \| null | 否 |  |
| password | string \| null | 否 |  |
| published_at | string \| null | 否 |  |
| reading_time | integer | 否 |  |
| slug | string | 是 |  |
| source | string | 是 |  |
| source_url | string \| null | 否 |  |
| status | string | 是 |  |
| subtitle | string \| null | 否 |  |
| tags | object[] | 否 |  |
| title | string | 是 |  |
| updated_at | string | 是 |  |
| video | string \| null | 否 |  |
| … 其余 3 个字段 | | | 见 `/docs` |

响应示例：

```json
{
  "allow_comments": false,
  "audio": "string",
  "author": {
    "avatar": "string",
    "avatar_source": "string",
    "bio": "string",
    "cover_image": "string",
    "created_at": "string",
    "github": "string",
    "id": 0,
    "nickname": "string",
    "resolved_avatar_url": "string",
    "title": "string",
    "username": "string",
    "website": "string"
  },
  "category": "string",
  "comments_count": 0,
  "content": "string",
  "cover_image": "string",
  "created_at": "string",
  "excerpt": "string",
  "id": 0,
  "is_password_protected": false,
  "is_pinned": false,
  "likes_count": 0,
  "meta_description": "string",
  "meta_keywords": "string",
  "meta_title": "string",
  "password": "string",
  "published_at": "string",
  "reading_time": 1,
  "slug": "string",
  "source": "string",
  "source_url": "string",
  "status": "string",
  "subtitle": "string",
  "tags": [],
  "title": "string",
  "updated_at": "string",
  "video": "string",
  "video_url": "string",
  "views": 0,
  "visibility": "public"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/blog/posts/{post_id}`

- **摘要**：删除文章
- **鉴权**：需鉴权：`HTTPBearer`

将文章移入回收站（30 天后自动清除），仅作者或超级管理员可操作。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/posts/{post_id}/comments`

- **摘要**：评论列表
- **鉴权**：需鉴权：`HTTPBearer`

获取文章的评论树形结构。评论树的可读性与文章本体同闸门：草稿/待审/定时未到的文章、以及设了密码但本次未带正确密码（``password`` 查询参数或 ``X-Post-Password`` 头，作者与 staff 免验）的文章返回空列表——文章详情把正文藏起来却把评论全公开，等于绕过密码保护。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "author_avatar": "",
    "author_name": "string",
    "author_website": "string",
    "avatar_source": "string",
    "content": "string",
    "created_at": "string",
    "github": "string",
    "id": 0,
    "is_pinned": false,
    "likes_count": 0,
    "parent_id": "string",
    "parent_ref": "string",
    "post_id": 0,
    "post_ref": "string",
    "qq": "string",
    "replies": [],
    "reply_total": 0,
    "resolved_avatar_url": "string",
    "status": "pending",
    "user_id": "string",
    "user_ref": "string"
  }
]
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/blog/posts/{post_id}/comments`

- **摘要**：发表评论
- **鉴权**：需鉴权：`HTTPBearer`

在文章下，支持回复。文章不可见（草稿/定时未到/加密未解锁）时按 404 处理，不接受对看不见的文章写评论；文章禁止评论（allow_comments=false）返回 403。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `CommentCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author_avatar_source | enum(`auto`, `custom`, `github`, `qq`, `gravatar`) \| null | 否 | 【已废弃】请使用 avatar_source；旧调用方兼容位，若为非 None 会覆盖 avatar_source |
| author_email | string \| null | 否 |  |
| author_name | string \| null | 否 |  |
| author_website | string \| null | 否 |  |
| avatar_source | enum(`auto`, `custom`, `github`, `qq`, `gravatar`) | 否 | 头像来源 |
| content | string | 是 |  |
| github | string \| null | 否 | 评论者 GitHub 用户名（可选） |
| hcaptcha_token | string \| null | 否 |  |
| parent_id | integer \| null | 否 |  |
| qq | string \| null | 否 | 评论者 QQ（可选） |

```json
{
  "author_avatar_source": "string",
  "author_email": "string",
  "author_name": "string",
  "author_website": "string",
  "avatar_source": "auto",
  "content": "string",
  "github": "string",
  "hcaptcha_token": "string",
  "parent_id": "string",
  "qq": "string"
}
```

**出参**

`201` · 模型 `CommentResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author_avatar | string | 否 |  |
| author_name | string | 是 |  |
| author_website | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| content | string | 是 |  |
| created_at | string | 是 |  |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_pinned | boolean | 否 |  |
| likes_count | integer | 否 |  |
| parent_id | integer \| null | 否 |  |
| parent_ref | object \| null | 否 |  |
| post_id | integer | 是 |  |
| post_ref | object \| null | 否 |  |
| qq | string \| null | 否 |  |
| replies | object[] | 否 |  |
| reply_total | integer | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| status | string | 否 |  |
| user_id | integer \| null | 否 |  |
| user_ref | object \| null | 否 |  |

响应示例：

```json
{
  "author_avatar": "",
  "author_name": "string",
  "author_website": "string",
  "avatar_source": "string",
  "content": "string",
  "created_at": "string",
  "github": "string",
  "id": 0,
  "is_pinned": false,
  "likes_count": 0,
  "parent_id": "string",
  "parent_ref": "string",
  "post_id": 0,
  "post_ref": "string",
  "qq": "string",
  "replies": [],
  "reply_total": 0,
  "resolved_avatar_url": "string",
  "status": "pending",
  "user_id": "string",
  "user_ref": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/posts/{post_id}/edit`

- **摘要**：获取文章用于编辑
- **鉴权**：需鉴权：`HTTPBearer`

根据文章ID获取完整的多语言内容，用于文章编辑页面。使用 /edit 后缀避免被 GET /posts/{slug} 路由遮蔽。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PostEditResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| allow_comments | boolean | 是 |  |
| audio | string \| null | 否 |  |
| category | object \| null | 否 |  |
| content | object<string, string> | 是 |  |
| cover_image | string \| null | 否 |  |
| created_at | string | 是 |  |
| excerpt | object<string, string> \| null | 否 |  |
| has_password | boolean | 否 |  |
| id | integer | 是 |  |
| is_pinned | boolean | 是 |  |
| meta_description | object<string, string> \| null | 否 |  |
| meta_keywords | object<string, string> \| null | 否 |  |
| meta_title | object<string, string> \| null | 否 |  |
| published_at | string \| null | 否 |  |
| scheduled_at | string \| null | 否 |  |
| slug | string | 是 |  |
| source | string | 是 |  |
| source_url | string \| null | 否 |  |
| status | string | 是 |  |
| subtitle | object<string, string> \| null | 否 |  |
| tags | object[] | 否 |  |
| title | object<string, string> | 是 |  |
| updated_at | string | 是 |  |
| video | string \| null | 否 |  |
| video_url | string \| null | 否 |  |
| visibility | string | 是 |  |

响应示例：

```json
{
  "allow_comments": false,
  "audio": "string",
  "category": "string",
  "content": {},
  "cover_image": "string",
  "created_at": "string",
  "excerpt": "string",
  "has_password": false,
  "id": 0,
  "is_pinned": false,
  "meta_description": "string",
  "meta_keywords": "string",
  "meta_title": "string",
  "published_at": "string",
  "scheduled_at": "string",
  "slug": "string",
  "source": "string",
  "source_url": "string",
  "status": "string",
  "subtitle": "string",
  "tags": [],
  "title": {},
  "updated_at": "string",
  "video": "string",
  "video_url": "string",
  "visibility": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/blog/posts/{post_id}/like`

- **摘要**：点赞/取消点赞
- **鉴权**：需鉴权：`HTTPBearer`

切换文章点赞状态。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/posts/{post_id}/similar`

- **摘要**：相似文章推荐
- **鉴权**：公开接口（无需鉴权）

获取与当前文章相似的推荐文章，基于标签和分类匹配。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "author": {
      "avatar": "string",
      "avatar_source": "string",
      "bio": "string",
      "cover_image": "string",
      "created_at": "string",
      "github": "string",
      "id": 0,
      "nickname": "string",
      "resolved_avatar_url": "string",
      "title": "string",
      "username": "string",
      "website": "string"
    },
    "category": "string",
    "comments_count": 0,
    "cover_image": "string",
    "created_at": "string",
    "excerpt": "string",
    "id": 0,
    "is_pinned": false,
    "likes_count": 0,
    "published_at": "string",
    "reading_time": 1,
    "slug": "string",
    "status": "string",
    "subtitle": "string",
    "tags": [],
    "title": "string",
    "updated_at": "string",
    "views": 0
  }
]
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/posts/{slug}`

- **摘要**：文章详情
- **鉴权**：需鉴权：`HTTPBearer`

根据 slug 获取，自动增加阅读量。支持多语言返回。加密文章需要提供密码。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PostLocalizedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| allow_comments | boolean | 是 |  |
| audio | string \| null | 否 |  |
| author | object | 是 | 公开作者卡片模型（用于文章 / 相册等资源的 ``author`` 字段）。 与 :class:`UserResponse` 的差别就是本模型**没有**的那些字段： ``email``、``qq``、``is_active`` / ``is_staff`` / ``is_sup … （完整说明见 `/docs`） |
| author.avatar | string \| null | 否 |  |
| author.avatar_source | string \| null | 否 |  |
| author.bio | string \| null | 否 |  |
| author.cover_image | string \| null | 否 |  |
| author.created_at | string | 是 |  |
| author.github | string \| null | 否 |  |
| author.id | integer | 是 |  |
| author.nickname | string \| null | 否 |  |
| author.resolved_avatar_url | string \| null | 否 |  |
| author.title | object \| null | 否 |  |
| author.username | string | 是 |  |
| author.website | string \| null | 否 |  |
| category | object \| null | 否 |  |
| comments_count | integer | 否 |  |
| content | string | 是 |  |
| cover_image | string \| null | 否 |  |
| created_at | string | 是 |  |
| excerpt | string \| null | 否 |  |
| id | integer | 是 |  |
| is_password_protected | boolean | 否 |  |
| is_pinned | boolean | 是 |  |
| likes_count | integer | 否 |  |
| meta_description | string \| null | 否 |  |
| meta_keywords | string \| null | 否 |  |
| meta_title | string \| null | 否 |  |
| password | string \| null | 否 |  |
| published_at | string \| null | 否 |  |
| reading_time | integer | 否 |  |
| slug | string | 是 |  |
| source | string | 是 |  |
| source_url | string \| null | 否 |  |
| status | string | 是 |  |
| subtitle | string \| null | 否 |  |
| tags | object[] | 否 |  |
| title | string | 是 |  |
| updated_at | string | 是 |  |
| video | string \| null | 否 |  |
| … 其余 3 个字段 | | | 见 `/docs` |

响应示例：

```json
{
  "allow_comments": false,
  "audio": "string",
  "author": {
    "avatar": "string",
    "avatar_source": "string",
    "bio": "string",
    "cover_image": "string",
    "created_at": "string",
    "github": "string",
    "id": 0,
    "nickname": "string",
    "resolved_avatar_url": "string",
    "title": "string",
    "username": "string",
    "website": "string"
  },
  "category": "string",
  "comments_count": 0,
  "content": "string",
  "cover_image": "string",
  "created_at": "string",
  "excerpt": "string",
  "id": 0,
  "is_password_protected": false,
  "is_pinned": false,
  "likes_count": 0,
  "meta_description": "string",
  "meta_keywords": "string",
  "meta_title": "string",
  "password": "string",
  "published_at": "string",
  "reading_time": 1,
  "slug": "string",
  "source": "string",
  "source_url": "string",
  "status": "string",
  "subtitle": "string",
  "tags": [],
  "title": "string",
  "updated_at": "string",
  "video": "string",
  "video_url": "string",
  "views": 0,
  "visibility": "public"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/posts/{slug}/adjacent`

- **摘要**：上一篇/下一篇
- **鉴权**：公开接口（无需鉴权）

按发布时间线获取当前公开文章的上一篇（更早）与下一篇（更晚），仅包含已发布且已到发布时间的文章。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PostAdjacentResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object \| null | 否 | 上下篇数据 |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "data": "string",
  "message": "",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/rss`

- **摘要**：RSS 订阅
- **鉴权**：公开接口（无需鉴权）

获取 RSS 2.0 格式的文章订阅源。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/site-stats`

- **摘要**：站点统计
- **鉴权**：公开接口（无需鉴权）

获取站点公开统计信息：总字数、文章数、分类数、标签数。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `SiteStats`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| total_categories | integer | 否 | 被文章引用过的去重分类数 |
| total_posts | integer | 否 | 已发布文章数 |
| total_tags | integer | 否 | 被文章引用过的去重标签数 |
| total_words | integer | 否 | 已发布文章的中文字数 + 英文词数合计 |

响应示例：

```json
{
  "total_categories": 0,
  "total_posts": 0,
  "total_tags": 0,
  "total_words": 0
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/blog/sitemap-pages.xml`

- **摘要**：静态路由 / 独立页面 Sitemap
- **鉴权**：公开接口（无需鉴权）

返回固定公开路由与已发布独立页面（/page/<slug>）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/blog/sitemap-posts.xml`

- **摘要**：文章 Sitemap（分页）
- **鉴权**：公开接口（无需鉴权）

按 page 参数返回单页文章 sitemap，每页最多 1000 条，含封面图。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/sitemap-taxonomies.xml`

- **摘要**：分类 / 标签 / 系列 / 作者归档 Sitemap
- **鉴权**：公开接口（无需鉴权）

返回分类、标签、系列的索引页与详情页，外加作者归档落地页 `/authors/<username>`（合并文件）。作者清单只含「有已发布文章，且未关闭 `show_posts` / `public_profile`」的作者——空归档页与 404 页都不该出现在爬虫视野里。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/blog/sitemap.xml`

- **摘要**：Sitemap 索引
- **鉴权**：公开接口（无需鉴权）

站点地图索引：列出 pages 静态表、posts 分页表、taxonomies 分类表。所有子表均指向对外站点域名（由 Nitro BFF 代理）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/blog/tags`

- **摘要**：标签列表
- **鉴权**：公开接口（无需鉴权）

获取所有激活的标签及其文章数量（返回多语言原始dict）。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "color": "string",
    "created_at": "string",
    "icon": "string",
    "id": 0,
    "is_active": false,
    "name": {},
    "post_count": 0,
    "slug": "string"
  }
]
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/blog/tags`

- **摘要**：创建标签
- **鉴权**：需鉴权：`HTTPBearer`

创建新标签，需要管理员权限。返回完整 i18n dict 供 I18nTabsEditor 回填。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `TagCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| color | string \| null | 否 |  |
| icon | string \| null | 否 |  |
| is_active | boolean | 否 |  |
| name | object<string, string> | 是 | 多语言标签名称 |
| slug | string \| null | 否 |  |

```json
{
  "color": "string",
  "icon": "string",
  "is_active": true,
  "name": {},
  "slug": "string"
}
```

**出参**

`201` · 模型 `TagResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| color | string \| null | 否 |  |
| created_at | string | 是 |  |
| icon | string \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 是 |  |
| name | object<string, string> | 是 |  |
| post_count | integer | 否 |  |
| slug | string | 是 |  |

响应示例：

```json
{
  "color": "string",
  "created_at": "string",
  "icon": "string",
  "id": 0,
  "is_active": false,
  "name": {},
  "post_count": 0,
  "slug": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/tags/slug/{slug}`

- **摘要**：获取标签详情
- **鉴权**：公开接口（无需鉴权）

根据 slug （返回完整 i18n dict）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `TagResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| color | string \| null | 否 |  |
| created_at | string | 是 |  |
| icon | string \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 是 |  |
| name | object<string, string> | 是 |  |
| post_count | integer | 否 |  |
| slug | string | 是 |  |

响应示例：

```json
{
  "color": "string",
  "created_at": "string",
  "icon": "string",
  "id": 0,
  "is_active": false,
  "name": {},
  "post_count": 0,
  "slug": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/blog/tags/{tag_id}`

- **摘要**：更新标签
- **鉴权**：需鉴权：`HTTPBearer`

信息，需要管理员权限。返回完整 i18n dict 供 I18nTabsEditor 回填。改名/改色会失效所有引用该标签的文章详情缓存与列表/RSS 缓存。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `TagUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| color | string \| null | 否 |  |
| icon | string \| null | 否 |  |
| is_active | boolean \| null | 否 |  |
| name | object<string, string> \| null | 否 |  |
| slug | string \| null | 否 |  |

```json
{
  "color": "string",
  "icon": "string",
  "is_active": "string",
  "name": "string",
  "slug": "string"
}
```

**出参**

`200` · 模型 `TagResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| color | string \| null | 否 |  |
| created_at | string | 是 |  |
| icon | string \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 是 |  |
| name | object<string, string> | 是 |  |
| post_count | integer | 否 |  |
| slug | string | 是 |  |

响应示例：

```json
{
  "color": "string",
  "created_at": "string",
  "icon": "string",
  "id": 0,
  "is_active": false,
  "name": {},
  "post_count": 0,
  "slug": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/blog/tags/{tag_id}`

- **摘要**：删除标签
- **鉴权**：需鉴权：`HTTPBearer`

，需要管理员权限。删除会 CASCADE 清空 post_tags 关联，并失效原引用该标签文章的详情/列表/RSS 缓存。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/users/me/comments`

- **摘要**：获取我的评论
- **鉴权**：需鉴权：`HTTPBearer`

获取当前用户发表的所有评论。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PaginatedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | any[] | 是 |  |
| page | integer | 是 | 当前页码 |
| page_size | integer | 是 | 每页大小 |
| total | integer | 是 | 总记录数 |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/users/me/history`

- **摘要**：获取阅读历史
- **鉴权**：需鉴权：`HTTPBearer`

获取当前用户的阅读历史记录。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PaginatedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | any[] | 是 |  |
| page | integer | 是 | 当前页码 |
| page_size | integer | 是 | 每页大小 |
| total | integer | 是 | 总记录数 |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/blog/users/me/history`

- **摘要**：清空阅读历史
- **鉴权**：需鉴权：`HTTPBearer`

清空当前用户的阅读历史记录。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/blog/users/me/likes`

- **摘要**：获取我的点赞
- **鉴权**：需鉴权：`HTTPBearer`

获取当前用户点赞的所有文章。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PaginatedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | any[] | 是 |  |
| page | integer | 是 | 当前页码 |
| page_size | integer | 是 | 每页大小 |
| total | integer | 是 | 总记录数 |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/users/me/posts`

- **摘要**：获取我的文章
- **鉴权**：需鉴权：`HTTPBearer`

获取当前用户发表的所有文章，包括草稿。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PaginatedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | any[] | 是 |  |
| page | integer | 是 | 当前页码 |
| page_size | integer | 是 | 每页大小 |
| total | integer | 是 | 总记录数 |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/blog/users/me/stats`

- **摘要**：获取我的统计
- **鉴权**：需鉴权：`HTTPBearer`

获取当前用户的文章数、评论数、获赞数统计。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `UserBlogStatsResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object \| null | 否 | 统计数据 |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "data": "string",
  "message": "获取统计成功",
  "success": true
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

---

## 核心（19）

站点公开配置、导航、友情链接等前台核心数据

### `GET /api/admin/navigations`

- **摘要**：管理员获取所有导航
- **鉴权**：需鉴权：`HTTPBearer`

菜单（包括未激活），需要管理员权限。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "created_at": "string",
    "icon": "string",
    "id": 0,
    "is_active": false,
    "location": "string",
    "order": 0,
    "parent_id": "string",
    "target_blank": false,
    "title": {},
    "updated_at": "string",
    "url": "string"
  }
]
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/settings`

- **摘要**：更新站点设置
- **鉴权**：需鉴权：`HTTPBearer`

更新站点配置，需要管理员权限。局部更新（exclude_unset）：省略某字段表示不改它；**显式传 null 表示清空该项，落库为空串**（不是字符串 "None"）。布尔项统一以小写 'true'/'false' 存储，与读取侧 `.lower()=='true'` 对齐；整数/URL 等按其字符串形式入库。注意读写面：本端点只写 site_configs 的扁平 UPPERCASE 键；basic/seo/footer/appearance 分组 JSON（同行小写键，经 PATCH /settings/{group} 写入）在 /api/config 合并时优先级更高——两组键有交集的项（site_name / icp_number 等）会被分组值覆写（分组空串同样覆写为 null）。前台设置页已全量走分组接口，本端点为程序化/兼容入口。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `SiteConfigUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| about_content | string \| null | 否 |  |
| accent_color | string \| null | 否 |  |
| allow_password_reset | boolean \| null | 否 |  |
| allowed_file_types | string \| null | 否 |  |
| allowed_image_types | string \| null | 否 |  |
| anime_bilibili_uid | string \| null | 否 |  |
| anime_tmdb_api_key | string \| null | 否 |  |
| anime_tmdb_list_id | string \| null | 否 |  |
| archive_fold_old_articles | boolean \| null | 否 |  |
| baidu_analytics_id | string \| null | 否 |  |
| baidu_site_verification | string \| null | 否 |  |
| bangumi_api_url | string \| null | 否 |  |
| bangumi_category_order_json | string \| null | 否 |  |
| bangumi_mode | string \| null | 否 |  |
| bangumi_subject_base_url | string \| null | 否 |  |
| bangumi_user_id | string \| null | 否 |  |
| bilibili_url | string \| null | 否 |  |
| category_bar_enabled | boolean \| null | 否 |  |
| code_theme | string \| null | 否 |  |
| code_theme_dark | string \| null | 否 |  |
| comment_allow_guest | boolean \| null | 否 |  |
| comment_antispam | boolean \| null | 否 |  |
| comment_artalk_locale | string \| null | 否 |  |
| comment_artalk_server | string \| null | 否 |  |
| comment_artalk_visitor_count | boolean \| null | 否 |  |
| comment_disqus_shortname | string \| null | 否 |  |
| comment_giscus_category | string \| null | 否 |  |
| comment_giscus_category_id | string \| null | 否 |  |
| comment_giscus_emit_metadata | string \| null | 否 |  |
| comment_giscus_input_position | string \| null | 否 |  |
| comment_giscus_lang | string \| null | 否 |  |
| comment_giscus_loading | string \| null | 否 |  |
| comment_giscus_mapping | string \| null | 否 |  |
| comment_giscus_reactions_enabled | string \| null | 否 |  |
| comment_giscus_repo | string \| null | 否 |  |
| comment_giscus_repo_id | string \| null | 否 |  |
| comment_giscus_strict | string \| null | 否 |  |
| comment_max_length | integer \| null | 否 |  |
| comment_require_approval | boolean \| null | 否 |  |
| comment_system_type | string \| null | 否 |  |
| … 其余 157 个字段 | | | 见 `/docs` |

```json
{
  "about_content": "string",
  "accent_color": "string",
  "allow_password_reset": "string",
  "allowed_file_types": "string",
  "allowed_image_types": "string",
  "anime_bilibili_uid": "string",
  "anime_tmdb_api_key": "string",
  "anime_tmdb_list_id": "string",
  "archive_fold_old_articles": "string",
  "baidu_analytics_id": "string",
  "baidu_site_verification": "string",
  "bangumi_api_url": "string",
  "bangumi_category_order_json": "string",
  "bangumi_mode": "string",
  "bangumi_subject_base_url": "string",
  "bangumi_user_id": "string",
  "bilibili_url": "string",
  "category_bar_enabled": "string",
  "code_theme": "string",
  "code_theme_dark": "string",
  "comment_allow_guest": "string",
  "comment_antispam": "string",
  "comment_artalk_locale": "string",
  "comment_artalk_server": "string",
  "comment_artalk_visitor_count": "string",
  "comment_disqus_shortname": "string",
  "comment_giscus_category": "string",
  "comment_giscus_category_id": "string",
  "comment_giscus_emit_metadata": "string",
  "comment_giscus_input_position": "string",
  "comment_giscus_lang": "string",
  "comment_giscus_loading": "string",
  "comment_giscus_mapping": "string",
  "comment_giscus_reactions_enabled": "string",
  "comment_giscus_repo": "string",
  "comment_giscus_repo_id": "string",
  "comment_giscus_strict": "string",
  "comment_max_length": "string",
  "comment_require_approval": "string",
  "comment_system_type": "string",
  "comment_twikoo_css_url": "string",
  "comment_twikoo_env_id": "string",
  "comment_twikoo_js_url": "string",
  "comment_twikoo_lang": "string",
  "comment_twikoo_visitor_count": "string",
  "comment_waline_emoji_json": "string",
  "comment_waline_lang": "string",
  "comment_waline_login_mode": "string",
  "comment_waline_server_url": "string",
  "comment_waline_visitor_count": "string",
  "contact_email": "string",
  "contact_qq": "string",
  "contact_wechat": "string",
  "copyright_text": "string",
  "cover_enable_in_post": "string",
  "cover_enable_overlay": "string",
  "cover_random_apis_json": "string",
  "cover_random_enable": "string",
  "cover_show_loading": "string",
  "custom_css": "string",
  "custom_footer_code": "string",
  "custom_header_code": "string",
  "custom_js": "string",
  "default_avatar": "string",
  "default_category_cover": "string",
  "default_og_image": "string",
  "default_post_cover": "string",
  "default_theme": "string",
  "dynamic_page_description": "string",
  "dynamic_page_items_per_page": "string",
  "dynamic_page_show_comment": "string",
  "dynamic_page_title": "string",
  "enable_comments": "string",
  "enable_dark_mode": "string",
  "enable_guestbook": "string",
  "enable_like_button": "string",
  "enable_reading_time": "string",
  "enable_registration": "string",
  "enable_rss_feed": "string",
  "enable_search": "string",
  "enable_share_buttons": "string",
  "enable_sitemap": "string",
  "enable_toc": "string",
  "enable_word_count": "string",
  "font_family": "string",
  "footer_custom_html": "string",
  "footer_slogan": "string",
  "footer_text": "string",
  "friends_apply_html": "string",
  "friends_page_description": "string",
  "friends_page_show_comment": "string",
  "friends_page_show_custom_content": "string",
  "friends_page_title": "string",
  "github_url": "string",
  "google_analytics_id": "string",
  "google_site_verification": "string",
  "icp_number": "string",
  "image_opt_formats": "string",
  "image_opt_no_referrer_json": "string",
  "image_opt_quality": "string",
  "license_enable": "string",
  "license_icon": "string",
  "license_name": "string",
  "license_url": "string",
  "linkedin_url": "string",
  "login_lockout_duration": "string",
  "maintenance_end_time": "string",
  "maintenance_message": "string",
  "maintenance_mode": "string",
  "max_login_attempts": "string",
  "max_upload_size": "string",
  "mermaid_security_level": "string",
  "mermaid_theme": "string",
  "music_enabled": "string",
  "music_meting_api": "string",
  "music_meting_id": "string",
  "music_meting_server": "string",
  "music_meting_type": "string",
  "music_mode": "string",
  "music_play_mode": "string",
  "music_show_in_navbar": "string",
  "music_show_in_sidebar": "string",
  "music_show_lyrics": "string",
  "music_volume": "string",
  "page_anime_enabled": "string",
  "page_bangumi_enabled": "string",
  "page_dynamic_enabled": "string",
  "page_friends_enabled": "string",
  "page_gallery_enabled": "string",
  "page_guestbook_enabled": "string",
  "page_sponsor_enabled": "string",
  "pagination_max_page_size": "string",
  "pagination_page_size": "string",
  "pagination_posts_per_page": "string",
  "pio_spine_enable": "string",
  "pio_spine_height": "string",
  "pio_spine_model_path": "string",
  "pio_spine_position_corner": "string",
  "pio_spine_scale": "string",
  "pio_spine_width": "string",
  "pio_spine_z_index": "string",
  "plantuml_server_url": "string",
  "police_icp_number": "string",
  "post_enable_share_poster": "string",
  "post_generate_og_images": "string",
  "post_list_default_mode": "string",
  "post_list_description_lines": "string",
  "post_list_mobile_mode": "string",
  "post_list_show_stats_icons": "string",
  "post_list_tags_position": "string",
  "post_outdated_threshold_days": "string",
  "post_show_last_modified": "string",
  "primary_color": "string",
  "require_email_verification": "string",
  "robots_txt": "string",
  "sakura_count": "string",
  "sakura_enable": "string",
  "sakura_max_opacity": "string",
  "sakura_max_scale": "string",
  "sakura_min_opacity": "string",
  "sakura_min_scale": "string",
  "sakura_z_index": "string",
  "session_timeout": "string",
  "site_author": "string",
  "site_description": "string",
  "site_email": "string",
  "site_favicon": "string",
  "site_icon": "string",
  "site_keywords": "string",
  "site_logo": "string",
  "site_name": "string",
  "site_start_date": "string",
  "site_subtitle": "string",
  "site_url": "string",
  "sponsor_methods_json": "string",
  "sponsor_page_description": "string",
  "sponsor_page_show_comment": "string",
  "sponsor_page_title": "string",
  "sponsor_page_usage": "string",
  "sponsor_show_sponsors_list": "string",
  "telegram_url": "string",
  "theme_accent": "string",
  "theme_primary": "string",
  "wallpaper_bing_days": "string",
  "wallpaper_desktop": "string",
  "wallpaper_dim_opacity": "string",
  "wallpaper_home_subtitle": "string",
  "wallpaper_home_title": "string",
  "wallpaper_mobile": "string",
  "wallpaper_mode": "string",
  "wallpaper_player_enable": "string",
  "wallpaper_use_bing": "string",
  "wallpaper_video": "string",
  "weibo_url": "string",
  "x_url": "string",
  "youtube_url": "string",
  "zhihu_url": "string"
}
```

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/config`

- **摘要**：站点配置
- **鉴权**：公开接口（无需鉴权）

获取网站全局配置信息。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `SiteConfigResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| about_content | string | 否 |  |
| about_page_html | string | 否 |  |
| accent_color | string | 否 |  |
| allow_password_reset | boolean | 否 |  |
| allowed_file_types | string | 否 |  |
| allowed_image_types | string | 否 |  |
| anime_bilibili_uid | string | 否 |  |
| anime_tmdb_api_key | string | 否 |  |
| anime_tmdb_list_id | string | 否 |  |
| archive_fold_old_articles | boolean | 否 |  |
| author_avatar | string | 否 |  |
| author_bio | string | 否 |  |
| author_links_json | string | 否 |  |
| author_name | string | 否 |  |
| baidu_analytics_id | string \| null | 否 |  |
| baidu_site_verification | string \| null | 否 |  |
| bangumi_api_url | string | 否 |  |
| bangumi_category_order_json | string | 否 |  |
| bangumi_mode | string | 否 |  |
| bangumi_subject_base_url | string | 否 |  |
| bangumi_user_id | string | 否 |  |
| bilibili_url | string \| null | 否 |  |
| category_bar_enabled | boolean | 否 |  |
| code_theme | string | 否 |  |
| code_theme_dark | string | 否 |  |
| comment_allow_guest | boolean | 否 |  |
| comment_antispam | boolean | 否 |  |
| comment_artalk_locale | string | 否 |  |
| comment_artalk_server | string | 否 |  |
| comment_artalk_visitor_count | boolean | 否 |  |
| comment_disqus_shortname | string | 否 |  |
| comment_giscus_category | string | 否 |  |
| comment_giscus_category_id | string | 否 |  |
| comment_giscus_emit_metadata | string | 否 |  |
| comment_giscus_input_position | string | 否 |  |
| comment_giscus_lang | string | 否 |  |
| comment_giscus_loading | string | 否 |  |
| comment_giscus_mapping | string | 否 |  |
| comment_giscus_reactions_enabled | string | 否 |  |
| comment_giscus_repo | string | 否 |  |
| … 其余 182 个字段 | | | 见 `/docs` |

响应示例：

```json
{
  "about_content": "",
  "about_page_html": "",
  "accent_color": "#0284C7",
  "allow_password_reset": true,
  "allowed_file_types": "pdf,doc,docx,xls,xlsx,ppt,pptx,zip,rar",
  "allowed_image_types": "jpg,jpeg,png,gif,webp,svg",
  "anime_bilibili_uid": "",
  "anime_tmdb_api_key": "",
  "anime_tmdb_list_id": "",
  "archive_fold_old_articles": true,
  "author_avatar": "",
  "author_bio": "",
  "author_links_json": "[]",
  "author_name": "",
  "baidu_analytics_id": "string",
  "baidu_site_verification": "string",
  "bangumi_api_url": "https://bgmapi.anibt.net",
  "bangumi_category_order_json": "[\"anime\",\"book\",\"music\",\"game\"]",
  "bangumi_mode": "dynamic",
  "bangumi_subject_base_url": "https://bgmmi.anibt.net/subject/",
  "bangumi_user_id": "",
  "bilibili_url": "string",
  "category_bar_enabled": true,
  "code_theme": "github",
  "code_theme_dark": "github-dark",
  "comment_allow_guest": false,
  "comment_antispam": true,
  "comment_artalk_locale": "zh-CN",
  "comment_artalk_server": "",
  "comment_artalk_visitor_count": true,
  "comment_disqus_shortname": "",
  "comment_giscus_category": "General",
  "comment_giscus_category_id": "",
  "comment_giscus_emit_metadata": "1",
  "comment_giscus_input_position": "top",
  "comment_giscus_lang": "zh-CN",
  "comment_giscus_loading": "lazy",
  "comment_giscus_mapping": "title",
  "comment_giscus_reactions_enabled": "1",
  "comment_giscus_repo": "",
  "comment_giscus_repo_id": "",
  "comment_giscus_strict": "0",
  "comment_max_length": 1000,
  "comment_require_approval": false,
  "comment_system_type": "none",
  "comment_twikoo_css_url": "",
  "comment_twikoo_env_id": "",
  "comment_twikoo_js_url": "https://cdn.jsdelivr.net/npm/twikoo@1.7.14/dist/twikoo.min.js",
  "comment_twikoo_lang": "zh-CN",
  "comment_twikoo_visitor_count": true,
  "comment_waline_emoji_json": "[\"https://unpkg.com/@waline/emojis@1.4.0/weibo\",\"https://unpkg.com/@waline/emojis@1.4.0/bilibili\"]",
  "comment_waline_lang": "zh-CN",
  "comment_waline_login_mode": "enable",
  "comment_waline_server_url": "",
  "comment_waline_visitor_count": true,
  "contact_email": "string",
  "contact_qq": "string",
  "contact_wechat": "string",
  "copyright_text": "string",
  "cover_enable_in_post": true,
  "cover_enable_overlay": true,
  "cover_random_apis_json": "[]",
  "cover_random_enable": false,
  "cover_show_loading": false,
  "custom_css": "string",
  "custom_footer_code": "string",
  "custom_header_code": "string",
  "custom_js": "string",
  "default_avatar": "string",
  "default_category_cover": "string",
  "default_cover_image": "",
  "default_og_image": "string",
  "default_post_cover": "string",
  "default_theme": "system",
  "dynamic_page_description": "",
  "dynamic_page_items_per_page": 10,
  "dynamic_page_show_comment": true,
  "dynamic_page_title": "",
  "email_configured": false,
  "email_from": "string",
  "email_from_name": "string",
  "enable_bing_wallpaper": true,
  "enable_comments": true,
  "enable_dark_mode": true,
  "enable_encrypted_posts": false,
  "enable_guestbook": true,
  "enable_like_button": true,
  "enable_music_player": true,
  "enable_pagefind_search": true,
  "enable_reading_time": true,
  "enable_registration": true,
  "enable_rss": true,
  "enable_rss_feed": true,
  "enable_search": true,
  "enable_share_buttons": true,
  "enable_sitemap": true,
  "enable_toc": true,
  "enable_word_count": true,
  "font_family": "string",
  "footer_custom_html": "",
  "footer_slogan": "string",
  "footer_text": "string",
  "friends_apply_html": "",
  "friends_page_description": "",
  "friends_page_show_comment": true,
  "friends_page_show_custom_content": true,
  "friends_page_title": "",
  "github_url": "string",
  "google_analytics_id": "string",
  "google_site_verification": "string",
  "icp_number": "string",
  "image_opt_formats": "webp",
  "image_opt_no_referrer_json": "[\"*.hdslb.com\",\"*.bilibili.com\"]",
  "image_opt_quality": 85,
  "license_enable": true,
  "license_icon": "",
  "license_name": "CC BY-NC-SA 4.0",
  "license_url": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
  "linkedin_url": "string",
  "login_lockout_duration": 1800,
  "maintenance_end_time": "string",
  "maintenance_message": "string",
  "maintenance_mode": false,
  "max_login_attempts": 5,
  "max_upload_size": 10485760,
  "mermaid_security_level": "strict",
  "mermaid_theme": "default",
  "music_enabled": true,
  "music_meting_api": "",
  "music_meting_id": "",
  "music_meting_server": "netease",
  "music_meting_type": "playlist",
  "music_mode": "meting",
  "music_play_mode": "list",
  "music_show_in_navbar": true,
  "music_show_in_sidebar": true,
  "music_show_lyrics": true,
  "music_volume": 0.7,
  "page_anime_enabled": true,
  "page_bangumi_enabled": true,
  "page_dynamic_enabled": true,
  "page_friends_enabled": true,
  "page_gallery_enabled": true,
  "page_guestbook_enabled": true,
  "page_sponsor_enabled": true,
  "pagination_max_page_size": 100,
  "pagination_page_size": 12,
  "pagination_posts_per_page": 10,
  "pio_spine_enable": false,
  "pio_spine_height": 165,
  "pio_spine_model_path": "",
  "pio_spine_position_corner": "bottom-left",
  "pio_spine_scale": 1.0,
  "pio_spine_width": 135,
  "pio_spine_z_index": 1000,
  "plantuml_server_url": "https://www.plantuml.com/plantuml",
  "police_icp_number": "string",
  "post_enable_share_poster": true,
  "post_generate_og_images": false,
  "post_list_default_mode": "list",
  "post_list_description_lines": 2,
  "post_list_mobile_mode": "grid",
  "post_list_show_stats_icons": true,
  "post_list_tags_position": "bottom",
  "post_outdated_threshold_days": 30,
  "post_show_last_modified": true,
  "primary_color": "#3B82F6",
  "require_email_verification": false,
  "robots_txt": "string",
  "sakura_count": 21,
  "sakura_enable": false,
  "sakura_max_opacity": 0.9,
  "sakura_max_scale": 1.1,
  "sakura_min_opacity": 0.3,
  "sakura_min_scale": 0.5,
  "sakura_z_index": 100,
  "session_timeout": 3600,
  "sidebar_show_categories": true,
  "sidebar_show_dynamics": true,
  "sidebar_show_music": true,
  "sidebar_show_profile": true,
  "sidebar_show_recent_comments": true,
  "sidebar_show_recent_posts": true,
  "sidebar_show_site_info": true,
  "sidebar_show_statistics": true,
  "sidebar_show_tag_cloud": true,
  "sidebar_show_tags": true,
  "sidebar_widget_order": [
    "profile",
    "site_info",
    "statistics",
    "dynamics",
    "music",
    "categories",
    "tags",
    "recent_posts",
    "recent_comments"
  ],
  "site_author": "string",
  "site_description": "string",
  "site_email": "string",
  "site_favicon": "string",
  "site_icon": "string",
  "site_keywords": "string",
  "site_logo": "string",
  "site_name": "string",
  "site_start_date": "2025-01-01",
  "site_subtitle": "",
  "site_url": "",
  "sponsor_methods_json": "[]",
  "sponsor_page_description": "",
  "sponsor_page_show_comment": true,
  "sponsor_page_title": "",
  "sponsor_page_usage": "",
  "sponsor_show_sponsors_list": true,
  "telegram_url": "string",
  "theme_accent": "#0284C7",
  "theme_primary": "#0EA5A9",
  "wallpaper_bing_days": 30,
  "wallpaper_desktop": "",
  "wallpaper_dim_opacity": 0.2,
  "wallpaper_home_subtitle": "",
  "wallpaper_home_title": "Welcome",
  "wallpaper_mobile": "",
  "wallpaper_mode": "banner",
  "wallpaper_player_enable": true,
  "wallpaper_use_bing": true,
  "wallpaper_video": "",
  "weibo_url": "string",
  "x_url": "string",
  "youtube_url": "string",
  "zhihu_url": "string"
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/config/full`

- **摘要**：完整站点配置（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

获取完整的站点配置，包含分组信息，需要管理员权限。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `SiteConfigFullResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| groups | object[] | 是 |  |
| last_updated | string \| null | 否 |  |

响应示例：

```json
{
  "groups": [
    {
      "description": "string",
      "icon": "string",
      "label": "string",
      "name": "string",
      "settings": [
        "…"
      ]
    }
  ],
  "last_updated": "string"
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/friend-links`

- **摘要**：友链列表
- **鉴权**：公开接口（无需鉴权）

获取友情链接列表。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "created_at": "string",
    "description": "string",
    "id": 0,
    "is_active": false,
    "logo": "string",
    "name": {},
    "order": 0,
    "status": "string",
    "target_blank": false,
    "url": "string"
  }
]
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/friend-links`

- **摘要**：创建友链
- **鉴权**：需鉴权：`HTTPBearer`

添加友情链接，需要管理员权限。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `FriendLinkCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| description | object<string, string> \| string \| null | 否 | 网站描述，支持字符串或多语言格式 |
| is_active | boolean | 否 |  |
| logo | string \| null | 否 |  |
| name | object<string, string> \| string | 是 | 网站名称，支持字符串或多语言格式 |
| order | integer | 否 |  |
| status | string | 否 | 审核状态：pending待审核 / approved已通过 / rejected已拒绝 |
| target_blank | boolean | 否 |  |
| url | string | 是 |  |

```json
{
  "description": "string",
  "is_active": true,
  "logo": "string",
  "name": "string",
  "order": 0,
  "status": "pending",
  "target_blank": false,
  "url": "string"
}
```

**出参**

`201` · 模型 `FriendLinkResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| created_at | string | 是 |  |
| description | object<string, string> \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 是 |  |
| logo | string \| null | 否 |  |
| name | object<string, string> | 是 |  |
| order | integer | 是 |  |
| status | string | 是 |  |
| target_blank | boolean | 是 |  |
| url | string | 是 |  |

响应示例：

```json
{
  "created_at": "string",
  "description": "string",
  "id": 0,
  "is_active": false,
  "logo": "string",
  "name": {},
  "order": 0,
  "status": "string",
  "target_blank": false,
  "url": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/friend-links/{link_id}`

- **摘要**：更新友链
- **鉴权**：需鉴权：`HTTPBearer`

更新友情链接，需要管理员权限。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `FriendLinkUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| description | object<string, string> \| string \| null | 否 |  |
| is_active | boolean \| null | 否 |  |
| logo | string \| null | 否 |  |
| name | object<string, string> \| string \| null | 否 |  |
| order | integer \| null | 否 |  |
| status | string \| null | 否 |  |
| target_blank | boolean \| null | 否 |  |
| url | string \| null | 否 |  |

```json
{
  "description": "string",
  "is_active": "string",
  "logo": "string",
  "name": "string",
  "order": "string",
  "status": "string",
  "target_blank": "string",
  "url": "string"
}
```

**出参**

`200` · 模型 `FriendLinkResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| created_at | string | 是 |  |
| description | object<string, string> \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 是 |  |
| logo | string \| null | 否 |  |
| name | object<string, string> | 是 |  |
| order | integer | 是 |  |
| status | string | 是 |  |
| target_blank | boolean | 是 |  |
| url | string | 是 |  |

响应示例：

```json
{
  "created_at": "string",
  "description": "string",
  "id": 0,
  "is_active": false,
  "logo": "string",
  "name": {},
  "order": 0,
  "status": "string",
  "target_blank": false,
  "url": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/friend-links/{link_id}`

- **摘要**：删除友链
- **鉴权**：需鉴权：`HTTPBearer`

删除友情链接，需要管理员权限。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/navigations`

- **摘要**：导航列表
- **鉴权**：公开接口（无需鉴权）

获取网站导航菜单，可按位置筛选。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "created_at": "string",
    "icon": "string",
    "id": 0,
    "is_active": false,
    "location": "string",
    "order": 0,
    "parent_id": "string",
    "target_blank": false,
    "title": {},
    "updated_at": "string",
    "url": "string"
  }
]
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/navigations`

- **摘要**：创建导航
- **鉴权**：需鉴权：`HTTPBearer`

添加导航菜单项，需要管理员权限。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `NavigationCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| icon | string \| null | 否 | 图标名称 |
| is_active | boolean | 否 |  |
| location | string | 否 |  |
| order | integer | 否 |  |
| parent_id | integer \| null | 否 | 父导航ID |
| target_blank | boolean | 否 |  |
| title | object<string, string> | 是 | 多语言导航标题 |
| url | string | 是 |  |

```json
{
  "icon": "string",
  "is_active": true,
  "location": "header",
  "order": 0,
  "parent_id": "string",
  "target_blank": false,
  "title": {},
  "url": "string"
}
```

**出参**

`201` · 模型 `NavigationResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| created_at | string \| null | 否 |  |
| icon | string \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 是 |  |
| location | string | 是 |  |
| order | integer | 是 |  |
| parent_id | integer \| null | 否 |  |
| target_blank | boolean | 是 |  |
| title | object<string, string> | 是 |  |
| updated_at | string \| null | 否 |  |
| url | string | 是 |  |

响应示例：

```json
{
  "created_at": "string",
  "icon": "string",
  "id": 0,
  "is_active": false,
  "location": "string",
  "order": 0,
  "parent_id": "string",
  "target_blank": false,
  "title": {},
  "updated_at": "string",
  "url": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/navigations/{nav_id}`

- **摘要**：更新导航
- **鉴权**：需鉴权：`HTTPBearer`

菜单项，需要管理员权限。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `NavigationUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| icon | string \| null | 否 |  |
| is_active | boolean \| null | 否 |  |
| location | string \| null | 否 |  |
| order | integer \| null | 否 |  |
| parent_id | integer \| null | 否 |  |
| target_blank | boolean \| null | 否 |  |
| title | object<string, string> \| null | 否 |  |
| url | string \| null | 否 |  |

```json
{
  "icon": "string",
  "is_active": "string",
  "location": "string",
  "order": "string",
  "parent_id": "string",
  "target_blank": "string",
  "title": "string",
  "url": "string"
}
```

**出参**

`200` · 模型 `NavigationResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| created_at | string \| null | 否 |  |
| icon | string \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 是 |  |
| location | string | 是 |  |
| order | integer | 是 |  |
| parent_id | integer \| null | 否 |  |
| target_blank | boolean | 是 |  |
| title | object<string, string> | 是 |  |
| updated_at | string \| null | 否 |  |
| url | string | 是 |  |

响应示例：

```json
{
  "created_at": "string",
  "icon": "string",
  "id": 0,
  "is_active": false,
  "location": "string",
  "order": 0,
  "parent_id": "string",
  "target_blank": false,
  "title": {},
  "updated_at": "string",
  "url": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/navigations/{nav_id}`

- **摘要**：删除导航
- **鉴权**：需鉴权：`HTTPBearer`

菜单项，需要管理员权限。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/pages`

- **摘要**：页面列表
- **鉴权**：需鉴权：`HTTPBearer`

获取独立，普通用户只能看到已发布的页面。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PaginatedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | any[] | 是 |  |
| page | integer | 是 | 当前页码 |
| page_size | integer | 是 | 每页大小 |
| total | integer | 是 | 总记录数 |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/pages`

- **摘要**：创建页面
- **鉴权**：需鉴权：`HTTPBearer`

创建独立页面，需要管理员权限。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `PageCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | object<string, string> | 是 | 多语言页面内容 |
| slug | string | 是 |  |
| status | string | 否 |  |
| title | object<string, string> | 是 | 多语言页面标题 |

```json
{
  "content": {},
  "slug": "string",
  "status": "published",
  "title": {}
}
```

**出参**

`201` · 模型 `PageResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | object<string, string> | 是 |  |
| created_at | string | 是 |  |
| id | integer | 是 |  |
| slug | string | 是 |  |
| status | string | 是 |  |
| title | object<string, string> | 是 |  |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "content": {},
  "created_at": "string",
  "id": 0,
  "slug": "string",
  "status": "string",
  "title": {},
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/pages/{page_id}`

- **摘要**：更新页面
- **鉴权**：需鉴权：`HTTPBearer`

内容，需要管理员权限。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `PageUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | object<string, string> \| null | 否 |  |
| slug | string \| null | 否 |  |
| status | string \| null | 否 |  |
| title | object<string, string> \| null | 否 |  |

```json
{
  "content": "string",
  "slug": "string",
  "status": "string",
  "title": "string"
}
```

**出参**

`200` · 模型 `PageResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | object<string, string> | 是 |  |
| created_at | string | 是 |  |
| id | integer | 是 |  |
| slug | string | 是 |  |
| status | string | 是 |  |
| title | object<string, string> | 是 |  |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "content": {},
  "created_at": "string",
  "id": 0,
  "slug": "string",
  "status": "string",
  "title": {},
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/pages/{page_id}`

- **摘要**：删除页面
- **鉴权**：需鉴权：`HTTPBearer`

，需要管理员权限。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/pages/{slug}`

- **摘要**：页面详情
- **鉴权**：需鉴权：`HTTPBearer`

根据 slug 获取页面内容。正文经统一内容渲染管线（短代码 + the_content filter 链），与文章详情同口径。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PageResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | object<string, string> | 是 |  |
| created_at | string | 是 |  |
| id | integer | 是 |  |
| slug | string | 是 |  |
| status | string | 是 |  |
| title | object<string, string> | 是 |  |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "content": {},
  "created_at": "string",
  "id": 0,
  "slug": "string",
  "status": "string",
  "title": {},
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/search-placeholders`

- **摘要**：搜索占位符
- **鉴权**：公开接口（无需鉴权）

获取搜索框的随机占位符文本列表。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | string[] | — |  |

响应示例：

```json
[
  "string"
]
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/sponsors`

- **摘要**：打赏者列表
- **鉴权**：公开接口（无需鉴权）

获取公开的。优先从站点配置 SPONSORS 读取，未配置时返回空列表。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {}
]
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

---

## 媒体（16）

文件上传、头像代理、图片处理

### `GET /api/media/avatar`

- **摘要**：头像代理
- **鉴权**：公开接口（无需鉴权）

代理外部头像 URL，白名单域名 302 直跳，非白名单流式代理，失败时回退 DiceBear SVG。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/media/avatar`

- **摘要**：上传头像
- **鉴权**：需鉴权：`HTTPBearer`

（前端已裁剪） 鉴权：只要登录态。写的是个人资料图，语义等价 ``Cap.EDIT_OWN_PROFILE`` （rbac 矩阵里 subscriber 就拥有），因此**不要**给它套 ``Cap.UPLOAD_MEDIA`` —— 那会把「普通注册用户改自己的头像」一起拒掉，与 /account/settings 的现状冲突。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_upload_avatar_api_media_avatar_post`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| file | string | 是 |  |

```json
{
  "file": "string"
}
```

**出参**

`200` · 模型 `ImageResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| filename | string | 是 |  |
| height | integer | 是 |  |
| url | string | 是 |  |
| width | integer | 是 |  |

响应示例：

```json
{
  "filename": "string",
  "height": 0,
  "url": "string",
  "width": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/media/bing-wallpaper`

- **摘要**：Bing 每日壁纸代理（支持批量）
- **鉴权**：公开接口（无需鉴权）

代理 Bing 每日壁纸 API，支持 HTTP/HTTPS 代理、12h 缓存、出错时 fallback 到最近 24h 成功结果。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/media/cover`

- **摘要**：上传封面图
- **鉴权**：需鉴权：`HTTPBearer`

（前端已裁剪） 鉴权同 ``/avatar``：登录态即可。前端 ``/account/settings`` 允许普通注册用户换自己的封面图， 所以这里不能收紧到 ``Cap.UPLOAD_MEDIA``（那是公共素材目录的门槛）。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_upload_cover_api_media_cover_post`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| file | string | 是 |  |

```json
{
  "file": "string"
}
```

**出参**

`200` · 模型 `ImageResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| filename | string | 是 |  |
| height | integer | 是 |  |
| url | string | 是 |  |
| width | integer | 是 |  |

响应示例：

```json
{
  "filename": "string",
  "height": 0,
  "url": "string",
  "width": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/media/library`

- **摘要**：媒体库列表
- **鉴权**：需鉴权：`HTTPBearer`

获取媒体库文件列表，支持分页、搜索和筛选。需 staff 及以上权限（未登录 401，非管理员 403）。`file_type` 与 `category` 都映射到同一列，同时传入时 `file_type` 优先；`page_size` 上限 100；`sort_by` 只接受 created_at / file_size / filename / updated_at，非法值静默回退 created_at；`search` 对文件名、标题、描述做不区分大小写的模糊匹配。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `MediaLibraryListResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 否 | 当前页媒体条目 |
| page | integer | 否 | 当前页码（回显请求参数） |
| page_size | integer | 否 | 每页数量（回显请求参数，上限 100） |
| total | integer | 否 | 符合筛选条件的媒体总数 |
| total_pages | integer | 否 | 总页数 = ceil(total / page_size)，total 为 0 时是 0 |

响应示例：

```json
{
  "items": [
    {
      "alt_text": "string",
      "category": "string",
      "created_at": "string",
      "description": "string",
      "file": "string",
      "file_size": 0,
      "file_type": "string",
      "filename": "string",
      "height": "string",
      "id": 0,
      "mime": "string",
      "size_bytes": 0,
      "sizes": "string",
      "title": "string",
      "updated_at": "string",
      "uploaded_by": "string",
      "url": "string",
      "width": "string"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/media/library`

- **摘要**：上传到媒体库（REST 主路径）
- **鉴权**：需鉴权：`HTTPBearer`

与媒体库列表接口配对：上传文件到媒体库。需 staff 及以上权限（未登录 401，非管理员 403）。multipart 单文件上限 20MB（超限 413 REQUEST_ENTITY_TOO_LARGE）；扩展名白名单为 image(jpg/jpeg/png/gif/webp/svg)、video(mp4/webm/mov)、audio(mp3/wav/ogg)、document(pdf/doc/docx/xls/xlsx)，未命中返回 400 UPLOAD_EXT_REJECTED；含脚本或事件处理器属性的 SVG 按内容拒绝（400 UPLOAD_SVG_UNSAFE）；空文件 400。category 用于业务分类（gallery/post-cover 等），非法值静默回退文件格式分类；图片会压缩原图并生成 thumbnail/medium/large 三档缩略图，站点配置了水印文案时叠加水印。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_upload_library_rest_api_media_library_post`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| alt_text | string \| null | 否 | 替代文本 |
| category | string \| null | 否 | 业务分类：gallery / post-cover / avatar / cover 等 |
| description | string \| null | 否 | 描述 |
| file | string | 是 |  |
| title | string \| null | 否 | 标题 |

```json
{
  "alt_text": "string",
  "category": "string",
  "description": "string",
  "file": "string",
  "title": "string"
}
```

**出参**

`200` · 模型 `MediaUploadResult`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| alt_text | string \| null | 否 | 替代文本（取自表单，未填为 null） |
| category | string | 是 | 业务分类：表单传入且合法时用表单值，否则回退文件格式分类 |
| created_at | string | 否 | 创建时间 ISO 字符串；记录缺值时为空字符串 |
| description | string \| null | 否 | 描述（取自表单，未填为 null） |
| duration | null | 否 | 音视频时长：当前实现固定为 null（未探测） |
| filename | string \| null | 否 | 入库记录里的文件名（即客户端提交的原始文件名）；记录该列为空时回退本次生成的落盘名 |
| height | integer \| null | 否 | 原图高度（像素）；非图片为 null |
| id | integer | 是 | 新建媒体记录 ID |
| is_active | boolean | 否 | 是否启用：入库即为 true |
| metadata | object | 是 | 上传结果里的 ``metadata`` 载荷。 |
| metadata.file_type | string | 是 | 按扩展名判定的文件格式分类 |
| metadata.sizes | object<string, object> \| null | 否 | 生成的多尺寸缩略图表；非图片或后处理失败时为 null |
| mime_type | string | 是 | MIME：图片取 Pillow 识别结果，其它取请求声明的 content-type 或 application/octet-stream |
| original_name | string \| null | 否 | 客户端提交的原始文件名 |
| size | integer | 是 | 文件大小（字节，按实际读到的内容长度计） |
| storage | string | 否 | 存储位置标识，当前实现固定为 local |
| thumbnail_url | string | 是 | 缩略图 URL：按 thumbnail → medium → large 取首个可用档位，全缺省时等于 ``url`` |
| title | string \| null | 否 | 标题（取自表单，未填为 null） |
| updated_at | string | 否 | 更新时间 ISO 字符串；记录缺值时为空字符串 |
| url | string | 是 | 文件可访问 URL（已按 CDN 前缀生成） |
| width | integer \| null | 否 | 原图宽度（像素）；非图片为 null |

响应示例：

```json
{
  "alt_text": "string",
  "category": "string",
  "created_at": "",
  "description": "string",
  "duration": "string",
  "filename": "string",
  "height": "string",
  "id": 0,
  "is_active": true,
  "metadata": {
    "file_type": "string",
    "sizes": "string"
  },
  "mime_type": "string",
  "original_name": "string",
  "size": 0,
  "storage": "local",
  "thumbnail_url": "string",
  "title": "string",
  "updated_at": "",
  "url": "string",
  "width": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/media/library/batch`

- **摘要**：批量删除媒体
- **鉴权**：需鉴权：`HTTPBearer`

批量删除多个媒体文件，同时删除数据库记录和物理文件。需 staff 及以上权限（未登录 401，非管理员 403）。ids 为空数组返回 400。响应除 `deleted_count` 外还回 `refused`（被内容引用或路径非法、记录被保留的条目）与 `missing_ids`，调用方不得只看 `success` 判定全部删除完成。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_batch_delete_media_api_media_library_batch_delete`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| ids | integer[] | 是 | 媒体 ID 列表 |

```json
{
  "ids": [
    0
  ]
}
```

**出参**

`200` · 模型 `MediaBatchDeleteResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| deleted_count | integer | 否 | 实际删除的记录数 |
| message | string | 是 | 汇总文案，含保留与不存在条目的数量 |
| missing_ids | integer[] | 否 | 请求里查无此记录的媒体 ID（升序） |
| refused | object[] | 否 | 被内容引用或路径非法而拒绝删除（DB 记录与物理文件都保留）的条目 |
| success | boolean | 否 | 固定为 true；调用方须再看 refused / missing_ids |

响应示例：

```json
{
  "deleted_count": 0,
  "message": "string",
  "missing_ids": [
    0
  ],
  "refused": [
    {
      "id": 0,
      "reason": "string"
    }
  ],
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/media/library/stats`

- **摘要**：媒体库统计
- **鉴权**：需鉴权：`HTTPBearer`

获取媒体库的统计信息：总文件数、总占用字节数与人类可读体积，并按文件格式分类给出计数。需 staff 及以上权限（未登录 401，非管理员 403）。单次请求内跑三条聚合查询，未做缓存。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `MediaStatsResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 媒体库统计载荷（同一数值挂了多组前端别名字段）。 |
| data.audios | integer | 否 | audio 分类文件数 |
| data.documents | integer | 否 | document 分类文件数 |
| data.images | integer | 否 | image 分类文件数（type_stats 缺该键时为 0） |
| data.total_count | integer | 否 | 媒体文件总数 |
| data.total_files | integer | 否 | 与 ``total_count`` 同值的前端别名 |
| data.total_size | integer | 否 | 全部文件占用字节数 |
| data.total_size_bytes | integer | 否 | 与 ``total_size`` 同值的字节数别名 |
| data.total_size_formatted | string | 否 | 人类可读体积（B/KB/MB/GB/TB/PB，保留两位小数） |
| data.type_stats | object<string, object> | 否 | 按文件格式分类的统计，键为 image / video / audio / document（仅出现库里实际存在的类型） |
| data.videos | integer | 否 | video 分类文件数 |
| message | string | 否 | 人类可读结果 |
| success | boolean | 否 | 固定为 true |

响应示例：

```json
{
  "data": {
    "audios": 0,
    "documents": 0,
    "images": 0,
    "total_count": 0,
    "total_files": 0,
    "total_size": 0,
    "total_size_bytes": 0,
    "total_size_formatted": "0.00 B",
    "type_stats": {},
    "videos": 0
  },
  "message": "获取媒体库统计成功",
  "success": true
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `POST /api/media/library/upload`

- **摘要**：上传到媒体库（别名路径）
- **鉴权**：需鉴权：`HTTPBearer`

兼容旧客户端的别名路径，参数、鉴权（staff 及以上）、20MB 上限、扩展名白名单、SVG 内容拦截与缩略图行为均与 REST 主路径一致。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_upload_to_library_api_media_library_upload_post`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| alt_text | string \| null | 否 | 替代文本 |
| category | string \| null | 否 | 业务分类：gallery / post-cover / avatar / cover 等 |
| description | string \| null | 否 | 描述 |
| file | string | 是 |  |
| title | string \| null | 否 | 标题 |

```json
{
  "alt_text": "string",
  "category": "string",
  "description": "string",
  "file": "string",
  "title": "string"
}
```

**出参**

`200` · 模型 `MediaUploadResult`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| alt_text | string \| null | 否 | 替代文本（取自表单，未填为 null） |
| category | string | 是 | 业务分类：表单传入且合法时用表单值，否则回退文件格式分类 |
| created_at | string | 否 | 创建时间 ISO 字符串；记录缺值时为空字符串 |
| description | string \| null | 否 | 描述（取自表单，未填为 null） |
| duration | null | 否 | 音视频时长：当前实现固定为 null（未探测） |
| filename | string \| null | 否 | 入库记录里的文件名（即客户端提交的原始文件名）；记录该列为空时回退本次生成的落盘名 |
| height | integer \| null | 否 | 原图高度（像素）；非图片为 null |
| id | integer | 是 | 新建媒体记录 ID |
| is_active | boolean | 否 | 是否启用：入库即为 true |
| metadata | object | 是 | 上传结果里的 ``metadata`` 载荷。 |
| metadata.file_type | string | 是 | 按扩展名判定的文件格式分类 |
| metadata.sizes | object<string, object> \| null | 否 | 生成的多尺寸缩略图表；非图片或后处理失败时为 null |
| mime_type | string | 是 | MIME：图片取 Pillow 识别结果，其它取请求声明的 content-type 或 application/octet-stream |
| original_name | string \| null | 否 | 客户端提交的原始文件名 |
| size | integer | 是 | 文件大小（字节，按实际读到的内容长度计） |
| storage | string | 否 | 存储位置标识，当前实现固定为 local |
| thumbnail_url | string | 是 | 缩略图 URL：按 thumbnail → medium → large 取首个可用档位，全缺省时等于 ``url`` |
| title | string \| null | 否 | 标题（取自表单，未填为 null） |
| updated_at | string | 否 | 更新时间 ISO 字符串；记录缺值时为空字符串 |
| url | string | 是 | 文件可访问 URL（已按 CDN 前缀生成） |
| width | integer \| null | 否 | 原图宽度（像素）；非图片为 null |

响应示例：

```json
{
  "alt_text": "string",
  "category": "string",
  "created_at": "",
  "description": "string",
  "duration": "string",
  "filename": "string",
  "height": "string",
  "id": 0,
  "is_active": true,
  "metadata": {
    "file_type": "string",
    "sizes": "string"
  },
  "mime_type": "string",
  "original_name": "string",
  "size": 0,
  "storage": "local",
  "thumbnail_url": "string",
  "title": "string",
  "updated_at": "",
  "url": "string",
  "width": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/media/library/{media_id}`

- **摘要**：媒体详情
- **鉴权**：需鉴权：`HTTPBearer`

获取单个媒体文件的详细信息。需管理员/编辑权限（与媒体库列表、统计、更新、删除同一档位）；记录不存在或 ID 无法解析为整数时分别返回 404 / 422。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `MediaDetailResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| alt_text | string \| null | 否 | 替代文本 |
| created_at | string \| null | 否 | 创建时间 ISO 8601 字符串；无值时为 null |
| description | string \| null | 否 | 描述 |
| file | string | 是 | 文件可访问地址（入库前经 CDN 前缀改写）：未配置 CDN 时是站内相对路径，配置后是绝对 http(s) URL；任何情况下都不是服务器上的磁盘路径 |
| file_size | integer | 否 | 文件大小（字节） |
| file_type | string | 是 | 文件格式分类：image / video / audio / document（由扩展名白名单派生） |
| filename | string \| null | 否 | 上传时的原始文件名（已 sanitize 前的客户端命名） |
| height | integer \| null | 否 | 原图高度（像素）；非图片为 null |
| id | integer | 是 | 媒体记录 ID |
| sizes | object<string, object> \| null | 否 | 多尺寸缩略图表，键为档位名 thumbnail / medium / large；非图片、SVG 或后处理失败时为 null |
| title | string \| null | 否 | 标题 |
| updated_at | string \| null | 否 | 更新时间 ISO 8601 字符串；无值时为 null |
| uploaded_by | object \| null | 否 | 上传者摘要；记录未关联上传者时为 null |
| width | integer \| null | 否 | 原图宽度（像素）；非图片为 null |

响应示例：

```json
{
  "alt_text": "string",
  "created_at": "string",
  "description": "string",
  "file": "string",
  "file_size": 0,
  "file_type": "string",
  "filename": "string",
  "height": "string",
  "id": 0,
  "sizes": "string",
  "title": "string",
  "updated_at": "string",
  "uploaded_by": "string",
  "width": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/media/library/{media_id}`

- **摘要**：更新媒体信息
- **鉴权**：需鉴权：`HTTPBearer`

更新媒体文件的标题、替代文本与描述。需 staff 及以上权限（未登录 401，非管理员 403）。采用「传了才改」语义：请求体中为 null 的字段保留原值，因此无法用本接口清空已有文案；只改元信息，不触碰物理文件与缩略图；记录不存在返回 404。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_update_media_api_media_library__media_id__put`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| alt_text | string \| null | 否 | 替代文本 |
| description | string \| null | 否 | 描述 |
| title | string \| null | 否 | 标题 |

```json
{
  "alt_text": "string",
  "description": "string",
  "title": "string"
}
```

**出参**

`200` · 模型 `MediaUpdateResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| media | object | 是 | 媒体信息更新成功后回显的媒体字段子集。 |
| media.alt_text | string \| null | 否 | 更新后的替代文本 |
| media.description | string \| null | 否 | 更新后的描述 |
| media.height | integer \| null | 否 | 原图高度（像素），本端点不修改该值 |
| media.id | integer | 是 | 媒体记录 ID |
| media.sizes | object<string, object> \| null | 否 | 多尺寸缩略图表，本端点不修改该值 |
| media.title | string \| null | 否 | 更新后的标题 |
| media.width | integer \| null | 否 | 原图宽度（像素），本端点不修改该值 |
| message | string | 否 | 人类可读结果 |
| success | boolean | 否 | 固定为 true（失败走 HTTPException 错误信封） |

响应示例：

```json
{
  "media": {
    "alt_text": "string",
    "description": "string",
    "height": "string",
    "id": 0,
    "sizes": "string",
    "title": "string",
    "width": "string"
  },
  "message": "媒体信息已更新",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/media/library/{media_id}`

- **摘要**：删除单个媒体
- **鉴权**：需鉴权：`HTTPBearer`

文件，同时删除数据库记录、物理原图与 sizes 中的全部派生档（thumbnail/medium/large）。需 staff 及以上权限（未登录 401，非管理员 403）。记录不存在返回 404；被内容引用（相册/文章/分类/系列/用户/Hero/站点配置的 URL 列）返回 409（error_code: MEDIA_IN_USE，记录与文件都保留）；存储路径不落在媒体目录内时拒绝删除并返回 400（UPLOAD_PATH_TRAVERSAL）；外链记录（远程 URL）仅删数据库记录。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `MediaDeleteResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 | 人类可读结果 |
| success | boolean | 否 | 固定为 true；失败路径走 HTTPException 错误信封 |

响应示例：

```json
{
  "message": "媒体文件已删除",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/media/upload`

- **摘要**：上传图片
- **鉴权**：需鉴权：`HTTPBearer`

支持的格式: JPG, PNG, GIF, WebP 最大文件大小: 10MB 鉴权说明： 这里刻意用 ``Cap.UPLOAD_MEDIA`` 而不是「任意登录用户」。本端点写的是**公共素材目录** （``/uploads/post|gallery/...``），落盘后任何人都可以通过 URL 直接取到，属于可写公共资源； 而 ``/media/avatar`` 与 ``/media/cover`` 写的是个人资料图，语义上属于 ``Cap.EDIT_OWN_PROFILE``（subscriber 就有），所以那两个端点仍只对登录态开放。 按 rbac 能力矩阵，``UPLOAD_MEDIA`` 从 contributor(20) 起授予 —— subscriber 只能改自己的 头像/封面，不能往公共空间塞文件。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_upload_image_api_media_upload_post`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| file | string | 是 |  |

```json
{
  "file": "string"
}
```

**出参**

`200` · 模型 `ImageUploadResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| filename | string | 是 |  |
| height | integer | 是 |  |
| size | integer | 是 |  |
| url | string | 是 |  |
| width | integer | 是 |  |

响应示例：

```json
{
  "filename": "string",
  "height": 0,
  "size": 0,
  "url": "string",
  "width": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/media/upload/stream`

- **摘要**：流式上传图片
- **鉴权**：需鉴权：`HTTPBearer`

（支持大文件） 与 `save_upload` 的区别只在写入方式：分块边读边写，避免把整张图先读进内存。 安全口径（扩展名白名单 + 魔数 + SVG 主动内容 + 大小上限）与 `save_upload` 一致。 鉴权口径同 `/upload`：写公共目录，要求 ``Cap.UPLOAD_MEDIA``（见 upload_image 注释）。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_upload_image_stream_api_media_upload_stream_post`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| file | string | 是 |  |

```json
{
  "file": "string"
}
```

**出参**

`200` · 模型 `ImageUploadResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| filename | string | 是 |  |
| height | integer | 是 |  |
| size | integer | 是 |  |
| url | string | 是 |  |
| width | integer | 是 |  |

响应示例：

```json
{
  "filename": "string",
  "height": 0,
  "size": 0,
  "url": "string",
  "width": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/media/{category}/{filename}`

- **摘要**：获取图片
- **鉴权**：公开接口（无需鉴权）

按「分类目录 + 文件名」直出图片二进制流，公开访问、无需鉴权。category 仅接受 uploads / avatars / covers / defaults，其余返回 404；文件名先经净化并校验落在媒体目录内，越界返回 400（error_code: UPLOAD_PATH_TRAVERSAL）。Content-Type 按扩展名映射，未知类型回退 application/octet-stream 并带 X-Content-Type-Options: nosniff；响应带 Cache-Control: public, max-age=31536000（一年强缓存），分块 64KB 流式读盘。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/media/{category}/{filename}`

- **摘要**：删除图片
- **鉴权**：需鉴权：`HTTPBearer`

按「分类目录 + 文件名」直接删除物理文件，需 staff 权限（与按媒体 ID 删除的口径一致）。文件名先经净化并校验落在媒体目录内，越界返回 400（error_code: UPLOAD_PATH_TRAVERSAL）；对应 URL 正被内容引用返回 409（error_code: MEDIA_IN_USE，文件保留）；分类非法或文件不存在返回 404。注意：本接口只删物理文件，不清理对应的数据库记录。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `ImageDeleteResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 | 人类可读结果 |
| success | boolean | 否 | 固定为 true；失败路径走 HTTPException 错误信封 |

响应示例：

```json
{
  "message": "图片已删除",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 数据库迁移（4）

Alembic 迁移状态查询与执行

### `POST /api/admin/migration/cancel`

- **摘要**：取消当前运行中的迁移任务
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。作用于最近一次创建的迁移任务：优先置协作式取消标志（_cancel_flag），否则退化为 asyncio Task.cancel()，任务状态改为 cancelled。当前没有任何迁移任务时返回 404，任务不在 running 时返回 400。取消不可逆，需重新发起迁移。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `MigrationStartOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| job | object | 是 | 迁移任务对外快照（``MigrationJob.to_public()`` 的字段形态）。 |
| job.created_at | number | 是 | 任务创建时间（Unix 秒级时间戳） |
| job.created_by | string | 是 | 发起者用户名（无用户名时回退为 staff） |
| job.dry_run | boolean | 是 | 是否演练模式（只读校验不落数据） |
| job.errors | string[] | 是 | 错误摘要列表（每条事件尾部 20 条累加） |
| job.events_count | integer | 是 | 环形缓冲内累计事件条数（上限 2000） |
| job.events_tail | object[] | 是 | 最近 200 条进度事件，供前端渲染阶段时间线 |
| job.finished_at | number \| null | 否 | 结束时间；运行中为 null |
| job.job_id | string | 是 | 任务唯一标识（uuid hex） |
| job.latest_progress | object \| null | 否 | 最近一条进度事件（来自 migrate_database.run_migration 的事件字典），无进度为 null |
| job.skip_schema | boolean | 是 | 是否跳过目标库表结构创建 |
| job.source | string | 是 | 源库连接串原文回显（含凭据时由前端自行保管） |
| job.started_at | number \| null | 否 | 实际开始执行时间；未开始为 null |
| job.status | string | 是 | 任务状态：pending \| running \| done \| error \| cancelled |
| job.target | string | 是 | 目标库连接串原文回显 |
| job.warnings | string[] | 是 | 告警摘要列表（每条事件尾部 20 条累加） |
| success | boolean | 是 | 固定为 true；失败走 4xx 错误信封 |

响应示例：

```json
{
  "job": {
    "created_at": 0.0,
    "created_by": "string",
    "dry_run": false,
    "errors": [
      "string"
    ],
    "events_count": 0,
    "events_tail": [
      {}
    ],
    "finished_at": "string",
    "job_id": "string",
    "latest_progress": "string",
    "skip_schema": false,
    "source": "string",
    "started_at": "string",
    "status": "string",
    "target": "string",
    "warnings": [
      "string"
    ]
  },
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `400` | 任务未在运行，无法取消 |
| `404` | 当前没有迁移任务 |

### `GET /api/admin/migration/presets`

- **摘要**：获取常用连接预设
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。返回内置 SQLite 默认路径与当前实例已生效的数据库（Redis 开启时含 Redis）连接串，供前端表单快速填充。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `MigrationPresetsOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| presets | object<string, string> | 是 | 连接预设键值对：sqlite_default（内置 SQLite 默认路径）、current_database（当前实例生效的库连接串）、current_redis（仅在 Redis 开启时存在） |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "presets": {},
  "success": false
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `POST /api/admin/migration/start`

- **摘要**：发起跨库迁移任务
- **鉴权**：需鉴权：`HTTPBearer`

管理员专属（CurrentStaff）。后台 asyncio task 异步运行，通过 /status 查看进度。全局同时只允许一个运行中的任务，冲突时返回 409。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `MigrationStartIn`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| dry_run | boolean | 否 |  |
| skip_schema | boolean | 否 |  |
| source | string | 是 | 源库 SQLAlchemy URL，如 sqlite+aiosqlite:///./rosetta.db |
| target | string | 是 | 目标库 SQLAlchemy URL，如 postgresql+asyncpg://user:pass@localhost:5432/rosetta |

```json
{
  "dry_run": false,
  "skip_schema": false,
  "source": "string",
  "target": "string"
}
```

**出参**

`200` · 模型 `MigrationStartOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| job | object | 是 | 迁移任务对外快照（``MigrationJob.to_public()`` 的字段形态）。 |
| job.created_at | number | 是 | 任务创建时间（Unix 秒级时间戳） |
| job.created_by | string | 是 | 发起者用户名（无用户名时回退为 staff） |
| job.dry_run | boolean | 是 | 是否演练模式（只读校验不落数据） |
| job.errors | string[] | 是 | 错误摘要列表（每条事件尾部 20 条累加） |
| job.events_count | integer | 是 | 环形缓冲内累计事件条数（上限 2000） |
| job.events_tail | object[] | 是 | 最近 200 条进度事件，供前端渲染阶段时间线 |
| job.finished_at | number \| null | 否 | 结束时间；运行中为 null |
| job.job_id | string | 是 | 任务唯一标识（uuid hex） |
| job.latest_progress | object \| null | 否 | 最近一条进度事件（来自 migrate_database.run_migration 的事件字典），无进度为 null |
| job.skip_schema | boolean | 是 | 是否跳过目标库表结构创建 |
| job.source | string | 是 | 源库连接串原文回显（含凭据时由前端自行保管） |
| job.started_at | number \| null | 否 | 实际开始执行时间；未开始为 null |
| job.status | string | 是 | 任务状态：pending \| running \| done \| error \| cancelled |
| job.target | string | 是 | 目标库连接串原文回显 |
| job.warnings | string[] | 是 | 告警摘要列表（每条事件尾部 20 条累加） |
| success | boolean | 是 | 固定为 true；失败走 4xx 错误信封 |

响应示例：

```json
{
  "job": {
    "created_at": 0.0,
    "created_by": "string",
    "dry_run": false,
    "errors": [
      "string"
    ],
    "events_count": 0,
    "events_tail": [
      {}
    ],
    "finished_at": "string",
    "job_id": "string",
    "latest_progress": "string",
    "skip_schema": false,
    "source": "string",
    "started_at": "string",
    "status": "string",
    "target": "string",
    "warnings": [
      "string"
    ]
  },
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `409` | 已有迁移任务运行中 |
| `422` | Validation Error |

### `GET /api/admin/migration/status`

- **摘要**：查询最新迁移任务状态
- **鉴权**：需鉴权：`HTTPBearer`

管理员专属（CurrentStaff）。返回进程内最新一次任务（running/done/error 均在列）的完整进度；任务历史只存内存，进程重启即为空（job 为 null）。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `MigrationStatusOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| job | object \| null | 否 | 进程内最近一次迁移任务；从未发起过时为 null |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "job": "string",
  "success": false
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

---

## 留言板（11）

访客留言的提交、审核与管理

### `GET /api/admin/guestbook`

- **摘要**：【管理员】留言板列表（含审核状态过滤/回收站/搜索）
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff（管理员 Bearer Token）。支持 status 过滤（pending|approved|rejected|spam|trashed|all）与 keyword 对内容/昵称/邮箱的模糊搜索，分页返回含审核状态的完整条目（含未过审与回收站数据，仅管理员可见）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `GuestbookEntryPagedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 |  |
| page | integer | 是 |  |
| page_size | integer | 是 |  |
| total | integer | 是 |  |
| total_pages | integer | 是 |  |

响应示例：

```json
{
  "items": [
    {
      "author_avatar": "",
      "author_name": "string",
      "author_website": "string",
      "avatar_source": "string",
      "content": "string",
      "created_at": "string",
      "github": "string",
      "id": 0,
      "is_featured": false,
      "is_pinned": false,
      "likes_count": 0,
      "qq": "string",
      "resolved_avatar_url": "string",
      "status": "pending",
      "title": "string",
      "user_id": "string"
    }
  ],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/guestbook/batch`

- **摘要**：【管理员】批量操作留言（approve/reject/spam/pin/feature/trash/restore/delete）
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。请求体 {ids: [留言ID...], action: 上述枚举之一}。逐条执行并统计处理数量；action 不在枚举内返回 422（业务码 INVALID_ACTION）。trash/restore 进/出回收站，delete 为彻底删除（回收站内条目也可删）。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `GuestbookBatchAction`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| action | string | 是 |  |
| ids | integer[] | 是 |  |

```json
{
  "action": "string",
  "ids": [
    0
  ]
}
```

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/admin/guestbook/{entry_id}`

- **摘要**：【管理员】单条删除留言
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。内部复用批量 delete 通道彻底删除（非软删除，不可恢复）。条目不存在或已被删除时返回 404。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/guestbook/{entry_id}/approve`

- **摘要**：【管理员】批准留言
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。将留言状态置为 approved 并立即对公众可见。幂等：对已批准条目重复调用不产生副作用。留言不存在时返回 404（业务码 GUESTBOOK_ENTRY_NOT_FOUND）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `GuestbookEntryResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author_avatar | string | 否 |  |
| author_name | string | 是 |  |
| author_website | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| content | string | 是 |  |
| created_at | string | 是 |  |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_featured | boolean | 否 |  |
| is_pinned | boolean | 否 |  |
| likes_count | integer | 否 |  |
| qq | string \| null | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| status | string | 否 |  |
| title | object \| null | 否 |  |
| user_id | integer \| null | 否 |  |

响应示例：

```json
{
  "author_avatar": "",
  "author_name": "string",
  "author_website": "string",
  "avatar_source": "string",
  "content": "string",
  "created_at": "string",
  "github": "string",
  "id": 0,
  "is_featured": false,
  "is_pinned": false,
  "likes_count": 0,
  "qq": "string",
  "resolved_avatar_url": "string",
  "status": "pending",
  "title": "string",
  "user_id": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/guestbook/{entry_id}/feature`

- **摘要**：【管理员】切换留言精华
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。Toggle 语义：当前为精华则取消、反之设为精华。留言不存在时返回 404（业务码 GUESTBOOK_ENTRY_NOT_FOUND）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `GuestbookEntryResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author_avatar | string | 否 |  |
| author_name | string | 是 |  |
| author_website | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| content | string | 是 |  |
| created_at | string | 是 |  |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_featured | boolean | 否 |  |
| is_pinned | boolean | 否 |  |
| likes_count | integer | 否 |  |
| qq | string \| null | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| status | string | 否 |  |
| title | object \| null | 否 |  |
| user_id | integer \| null | 否 |  |

响应示例：

```json
{
  "author_avatar": "",
  "author_name": "string",
  "author_website": "string",
  "avatar_source": "string",
  "content": "string",
  "created_at": "string",
  "github": "string",
  "id": 0,
  "is_featured": false,
  "is_pinned": false,
  "likes_count": 0,
  "qq": "string",
  "resolved_avatar_url": "string",
  "status": "pending",
  "title": "string",
  "user_id": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/guestbook/{entry_id}/pin`

- **摘要**：【管理员】切换留言置顶
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。Toggle 语义：当前置顶则取消、未置顶则置顶，可安全重复调用（幂等于切换）。留言不存在时返回 404（业务码 GUESTBOOK_ENTRY_NOT_FOUND）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `GuestbookEntryResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author_avatar | string | 否 |  |
| author_name | string | 是 |  |
| author_website | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| content | string | 是 |  |
| created_at | string | 是 |  |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_featured | boolean | 否 |  |
| is_pinned | boolean | 否 |  |
| likes_count | integer | 否 |  |
| qq | string \| null | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| status | string | 否 |  |
| title | object \| null | 否 |  |
| user_id | integer \| null | 否 |  |

响应示例：

```json
{
  "author_avatar": "",
  "author_name": "string",
  "author_website": "string",
  "avatar_source": "string",
  "content": "string",
  "created_at": "string",
  "github": "string",
  "id": 0,
  "is_featured": false,
  "is_pinned": false,
  "likes_count": 0,
  "qq": "string",
  "resolved_avatar_url": "string",
  "status": "pending",
  "title": "string",
  "user_id": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/guestbook/{entry_id}/reject`

- **摘要**：【管理员】拒绝留言
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。将留言状态置为 rejected，前台不再展示（作者登录可见自己的被拒条目）。留言不存在时返回 404（业务码 GUESTBOOK_ENTRY_NOT_FOUND）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `GuestbookEntryResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author_avatar | string | 否 |  |
| author_name | string | 是 |  |
| author_website | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| content | string | 是 |  |
| created_at | string | 是 |  |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_featured | boolean | 否 |  |
| is_pinned | boolean | 否 |  |
| likes_count | integer | 否 |  |
| qq | string \| null | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| status | string | 否 |  |
| title | object \| null | 否 |  |
| user_id | integer \| null | 否 |  |

响应示例：

```json
{
  "author_avatar": "",
  "author_name": "string",
  "author_website": "string",
  "avatar_source": "string",
  "content": "string",
  "created_at": "string",
  "github": "string",
  "id": 0,
  "is_featured": false,
  "is_pinned": false,
  "likes_count": 0,
  "qq": "string",
  "resolved_avatar_url": "string",
  "status": "pending",
  "title": "string",
  "user_id": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/guestbook/{entry_id}/spam`

- **摘要**：【管理员】标记为垃圾留言
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。将留言状态置为 spam，前台不再展示。留言不存在时返回 404（业务码 GUESTBOOK_ENTRY_NOT_FOUND）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `GuestbookEntryResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author_avatar | string | 否 |  |
| author_name | string | 是 |  |
| author_website | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| content | string | 是 |  |
| created_at | string | 是 |  |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_featured | boolean | 否 |  |
| is_pinned | boolean | 否 |  |
| likes_count | integer | 否 |  |
| qq | string \| null | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| status | string | 否 |  |
| title | object \| null | 否 |  |
| user_id | integer \| null | 否 |  |

响应示例：

```json
{
  "author_avatar": "",
  "author_name": "string",
  "author_website": "string",
  "avatar_source": "string",
  "content": "string",
  "created_at": "string",
  "github": "string",
  "id": 0,
  "is_featured": false,
  "is_pinned": false,
  "likes_count": 0,
  "qq": "string",
  "resolved_avatar_url": "string",
  "status": "pending",
  "title": "string",
  "user_id": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/guestbook`

- **摘要**：获取留言板分页列表
- **鉴权**：需鉴权：`HTTPBearer`

公开接口，无需登录。按 置顶 → 精华 → 时间 倒序分页返回留言。默认只返回 approved 条目；status 支持 approved|pending|rejected|spam|all|trashed，include=trashed 时包含回收站条目（管理员语义）。携带 Bearer Token 时登录用户可看到自己尚未过审的留言；匿名访客只看得到已过审内容。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `GuestbookEntryPagedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 |  |
| page | integer | 是 |  |
| page_size | integer | 是 |  |
| total | integer | 是 |  |
| total_pages | integer | 是 |  |

响应示例：

```json
{
  "items": [
    {
      "author_avatar": "",
      "author_name": "string",
      "author_website": "string",
      "avatar_source": "string",
      "content": "string",
      "created_at": "string",
      "github": "string",
      "id": 0,
      "is_featured": false,
      "is_pinned": false,
      "likes_count": 0,
      "qq": "string",
      "resolved_avatar_url": "string",
      "status": "pending",
      "title": "string",
      "user_id": "string"
    }
  ],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/guestbook`

- **摘要**：发表留言（游客或登录用户均可）
- **鉴权**：需鉴权：`HTTPBearer`

公开写入接口，携带可选 Bearer Token 时自动关联登录用户身份。服务端记录客户端 IP 与 User-Agent 用于审核追溯；留言进入审核流，管理员批准后才对公众可见。受敏感接口限流与同 IP 频控保护：过于频繁返回 429（业务码 TOO_FREQUENT_GUESTBOOK，响应头带 Retry-After: 30）。字段校验失败返回 422：AUTHOR_NAME_REQUIRED / AUTHOR_NAME_TOO_SHORT / CONTENT_TOO_SHORT / CONTENT_TOO_LONG。非幂等，重复提交会产生多条留言。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `GuestbookEntryCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author_avatar_source | enum(`auto`, `custom`, `github`, `qq`, `gravatar`) | 否 | 头像来源 |
| author_email | string \| null | 否 |  |
| author_name | string \| null | 否 |  |
| author_website | string \| null | 否 |  |
| content | string | 是 |  |
| github | string \| null | 否 | 评论者 GitHub 用户名（可选） |
| qq | string \| null | 否 | 评论者 QQ（可选） |

```json
{
  "author_avatar_source": "auto",
  "author_email": "string",
  "author_name": "string",
  "author_website": "string",
  "content": "string",
  "github": "string",
  "qq": "string"
}
```

**出参**

`201` · 模型 `GuestbookEntryResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author_avatar | string | 否 |  |
| author_name | string | 是 |  |
| author_website | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| content | string | 是 |  |
| created_at | string | 是 |  |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_featured | boolean | 否 |  |
| is_pinned | boolean | 否 |  |
| likes_count | integer | 否 |  |
| qq | string \| null | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| status | string | 否 |  |
| title | object \| null | 否 |  |
| user_id | integer \| null | 否 |  |

响应示例：

```json
{
  "author_avatar": "",
  "author_name": "string",
  "author_website": "string",
  "avatar_source": "string",
  "content": "string",
  "created_at": "string",
  "github": "string",
  "id": 0,
  "is_featured": false,
  "is_pinned": false,
  "likes_count": 0,
  "qq": "string",
  "resolved_avatar_url": "string",
  "status": "pending",
  "title": "string",
  "user_id": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/guestbook/{entry_id}/like`

- **摘要**：给留言点赞（简单计数，允许匿名）
- **鉴权**：公开接口（无需鉴权）

公开接口，无需登录。对指定留言的 likes_count 做简单自增，不做按用户去重，因此非幂等（重复调用会重复计数）。自增前对留言行加行锁，并发点赞不会丢计数。按 IP 限流 30 次/分钟（滑动窗口）。留言不存在或已被移入回收站时返回 404（业务码 GUESTBOOK_ENTRY_NOT_FOUND）。返回值是点赞后的累计总数，不是本次增量。响应为裸 dict（success + 自增后的 likes_count 累计总数），无 data 信封。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `GuestbookLikeResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| likes_count | integer | 否 | 自增之后该留言的最新点赞总数（不是本次请求的增量，恒为正整数） |
| success | boolean | 否 | 固定为 true：留言不存在时本接口返回 404 而非 false |

响应示例：

```json
{
  "likes_count": 0,
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 投票（5）

文章投票与统计

### `GET /api/voting/polls`

- **摘要**：投票列表
- **鉴权**：需鉴权：`HTTPBearer`

获取，可按状态筛选。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PaginatedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | any[] | 是 |  |
| page | integer | 是 | 当前页码 |
| page_size | integer | 是 | 每页大小 |
| total | integer | 是 | 总记录数 |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/voting/polls`

- **摘要**：创建投票
- **鉴权**：需鉴权：`HTTPBearer`

创建新投票，需要管理员权限。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `PollCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| allow_multiple | boolean | 否 |  |
| choices | string[] | 是 | 选项列表；每项 1-200 字符 |
| description | string \| null | 否 |  |
| is_active | boolean | 否 |  |
| show_results | boolean | 否 |  |
| title | string | 是 |  |

```json
{
  "allow_multiple": false,
  "choices": [
    "string"
  ],
  "description": "string",
  "is_active": true,
  "show_results": true,
  "title": "string"
}
```

**出参**

`201` · 模型 `PollResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| allow_multiple | boolean | 否 |  |
| choices | object[] | 是 |  |
| created_at | string | 是 |  |
| description | string \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 否 |  |
| show_results | boolean | 否 |  |
| title | string | 是 |  |
| total_votes | integer | 否 |  |

响应示例：

```json
{
  "allow_multiple": false,
  "choices": [
    {
      "id": 0,
      "order": 0,
      "text": "string",
      "votes_count": "string"
    }
  ],
  "created_at": "string",
  "description": "string",
  "id": 0,
  "is_active": true,
  "show_results": true,
  "title": "string",
  "total_votes": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/voting/polls/{poll_id}`

- **摘要**：投票详情
- **鉴权**：需鉴权：`HTTPBearer`

获取和各选项票数。show_results=False 时对非 staff/superuser 隐藏票数。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PollResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| allow_multiple | boolean | 否 |  |
| choices | object[] | 是 |  |
| created_at | string | 是 |  |
| description | string \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 否 |  |
| show_results | boolean | 否 |  |
| title | string | 是 |  |
| total_votes | integer | 否 |  |

响应示例：

```json
{
  "allow_multiple": false,
  "choices": [
    {
      "id": 0,
      "order": 0,
      "text": "string",
      "votes_count": "string"
    }
  ],
  "created_at": "string",
  "description": "string",
  "id": 0,
  "is_active": true,
  "show_results": true,
  "title": "string",
  "total_votes": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/voting/polls/{poll_id}`

- **摘要**：删除投票
- **鉴权**：需鉴权：`HTTPBearer`

，需要管理员权限。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/voting/polls/{poll_id}/vote`

- **摘要**：参与投票
- **鉴权**：需鉴权：`HTTPBearer`

提交投票选择，支持匿名投票。**已登录用户每人一票**：重复提交返回 409。匿名请求没有稳定标识（``ip_address`` 列存在但本路径不采集），仍按次放行。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `VoteCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| choice_ids | integer[] | 是 |  |

```json
{
  "choice_ids": [
    0
  ]
}
```

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 通知（7）

站内通知的读取与标记

### `GET /api/notifications`

- **摘要**：通知列表
- **鉴权**：需鉴权：`HTTPBearer`

获取当前用户的（需登录）。支持按未读筛选与分页；响应中的 unread_count 始终是全量未读数，不受 unread_only 筛选影响。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `NotificationListOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 | 本页通知列表，按创建时间倒序 |
| page | integer | 是 | 当前页码，从 1 开始 |
| page_size | integer | 是 | 每页条数 |
| total | integer | 是 | 符合筛选条件的通知总数（非本页条数） |
| total_pages | integer | 是 | 总页数；total 为 0 时是 0 |
| unread_count | integer | 是 | 当前用户全部未读通知数，用于角标展示 |

响应示例：

```json
{
  "items": [
    {
      "actor": "string",
      "created_at": "string",
      "id": 0,
      "is_read": false,
      "level": "string",
      "link": "string",
      "message": "string",
      "title": "string",
      "verb": "string"
    }
  ],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0,
  "unread_count": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/notifications`

- **摘要**：清空通知
- **鉴权**：需鉴权：`HTTPBearer`

清空当前用户的所有通知，read_only=true 时只清空已读通知（需登录）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `NotificationActionResultOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 人类可读操作结果提示（如「已标记为已读」） |
| success | boolean | 否 | 操作是否成功 |

响应示例：

```json
{
  "message": "string",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/notifications/read-all`

- **摘要**：全部已读
- **鉴权**：需鉴权：`HTTPBearer`

标记当前用户所有通知为已读（需登录）。成功后未读数归零。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `NotificationActionResultOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 人类可读操作结果提示（如「已标记为已读」） |
| success | boolean | 否 | 操作是否成功 |

响应示例：

```json
{
  "message": "string",
  "success": true
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/notifications/stats`

- **摘要**：通知统计
- **鉴权**：需鉴权：`HTTPBearer`

获取当前用户的信息（需登录），含按动作类型 verb 分组的数量分布。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `NotificationStatsOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| read | integer | 是 | 已读通知数（total - unread） |
| total | integer | 是 | 通知总数 |
| type_distribution | object<string, integer> | 是 | 按 verb 分组的通知数量统计，键为动作类型、值为条数 |
| unread | integer | 是 | 未读通知数 |

响应示例：

```json
{
  "read": 0,
  "total": 0,
  "type_distribution": {},
  "unread": 0
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/notifications/unread-count`

- **摘要**：未读通知数
- **鉴权**：需鉴权：`HTTPBearer`

获取当前用户的量（需登录，用于角标轮询）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `NotificationUnreadCountOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| unread_count | integer | 是 | 当前用户的未读通知数量 |

响应示例：

```json
{
  "unread_count": 0
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `DELETE /api/notifications/{notification_id}`

- **摘要**：删除通知
- **鉴权**：需鉴权：`HTTPBearer`

删除单条通知（需登录）。通知不存在或不属于当前用户时 404。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `NotificationActionResultOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 人类可读操作结果提示（如「已标记为已读」） |
| success | boolean | 否 | 操作是否成功 |

响应示例：

```json
{
  "message": "string",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/notifications/{notification_id}/read`

- **摘要**：标记已读
- **鉴权**：需鉴权：`HTTPBearer`

标记单条通知为已读（需登录）。会减少未读数；通知不存在或不属于当前用户时 404。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `NotificationActionResultOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 人类可读操作结果提示（如「已标记为已读」） |
| success | boolean | 否 | 操作是否成功 |

响应示例：

```json
{
  "message": "string",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 收藏（12）

文章收藏管理

### `GET /api/favorites`

- **摘要**：我的收藏列表
- **鉴权**：需鉴权：`HTTPBearer`

获取当前用户的收藏列表（需登录）。可按收藏夹筛选并分页；``total`` / ``total_pages`` 与该筛选同口径。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `FavoriteListOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 | 本页收藏列表，按收藏时间倒序 |
| page | integer | 是 | 当前页码，从 1 开始 |
| page_size | integer | 是 | 每页条数 |
| total | integer | 是 | 符合当前筛选（含 folder_id）的收藏总数 |
| total_pages | integer | 是 | 总页数；total 为 0 时是 0 |

响应示例：

```json
{
  "items": [
    {
      "created_at": "string",
      "folder_id": "string",
      "id": 0,
      "note": "string",
      "post": "string"
    }
  ],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/favorites`

- **摘要**：收藏文章
- **鉴权**：需鉴权：`HTTPBearer`

收藏一篇文章（需登录）。文章不存在时 404；重复收藏时 400；指定 folder_id 时收藏夹必须属于当前用户，否则 404。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_add_favorite_api_favorites_post`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| folder_id | integer \| null | 否 |  |
| note | string \| null | 否 |  |
| post_id | integer | 是 |  |

```json
{
  "folder_id": "string",
  "note": "string",
  "post_id": 0
}
```

**出参**

`200` · 模型 `FavoriteActionResultOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 人类可读操作结果提示（如「收藏成功」） |
| success | boolean | 否 | 操作是否成功 |

响应示例：

```json
{
  "message": "string",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/favorites/check`

- **摘要**：检查收藏状态
- **鉴权**：需鉴权：`HTTPBearer`

批量检查多篇文章是否已被当前用户收藏（需登录）。响应以文章 ID 字符串为键，未收藏的文章 favorite_id 为 null。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_check_favorites_api_favorites_check_post`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| post_ids | integer[] | 是 |  |

```json
{
  "post_ids": [
    0
  ]
}
```

**出参**

`200` · 模型 `FavoriteCheckResultOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| favorites | object<string, object> | 是 | 以文章 ID 字符串为键的收藏状态映射，覆盖请求中的全部 post_ids |

响应示例：

```json
{
  "favorites": {}
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/favorites/folders`

- **摘要**：我的收藏夹列表
- **鉴权**：需鉴权：`HTTPBearer`

获取当前用户的收藏夹列表（需登录），每项含该收藏夹内的收藏文章数量。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `FavoriteFolderListOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 | 收藏夹列表，按 order 升序、创建时间倒序 |
| total | integer | 是 | 收藏夹总数 |

响应示例：

```json
{
  "items": [
    {
      "count": 0,
      "created_at": "string",
      "description": "string",
      "id": 0,
      "is_public": false,
      "name": "string"
    }
  ],
  "total": 0
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `POST /api/favorites/folders`

- **摘要**：创建收藏夹
- **鉴权**：需鉴权：`HTTPBearer`

创建新的收藏夹（需登录）。成功后回显新收藏夹的 ID 与基本信息。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `FolderCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| description | string \| null | 否 |  |
| is_public | boolean | 否 |  |
| name | string | 是 |  |

```json
{
  "description": "string",
  "is_public": false,
  "name": "string"
}
```

**出参**

`200` · 模型 `FavoriteFolderCreateOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| folder | object | 是 | 创建收藏夹后回显的收藏夹摘要 |
| folder.description | string \| null | 否 | 收藏夹描述，未填写时为 null |
| folder.id | integer | 是 | 新建收藏夹 ID |
| folder.is_public | boolean | 是 | 是否公开 |
| folder.name | string | 是 | 收藏夹名称 |
| message | string | 是 | 人类可读操作结果提示 |
| success | boolean | 否 | 操作是否成功 |

响应示例：

```json
{
  "folder": {
    "description": "string",
    "id": 0,
    "is_public": false,
    "name": "string"
  },
  "message": "string",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/favorites/folders/{folder_id}`

- **摘要**：更新收藏夹
- **鉴权**：需鉴权：`HTTPBearer`

信息（需登录）。仅更新传入的字段；收藏夹不存在或不属于当前用户时 404。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `FolderUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| description | string \| null | 否 |  |
| is_public | boolean \| null | 否 |  |
| name | string \| null | 否 |  |

```json
{
  "description": "string",
  "is_public": "string",
  "name": "string"
}
```

**出参**

`200` · 模型 `FavoriteActionResultOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 人类可读操作结果提示（如「收藏成功」） |
| success | boolean | 否 | 操作是否成功 |

响应示例：

```json
{
  "message": "string",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/favorites/folders/{folder_id}`

- **摘要**：删除收藏夹
- **鉴权**：需鉴权：`HTTPBearer`

（需登录），收藏夹内的文章会移到默认收藏（folder_id 置空）而不被删除。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `FavoriteActionResultOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 人类可读操作结果提示（如「收藏成功」） |
| success | boolean | 否 | 操作是否成功 |

响应示例：

```json
{
  "message": "string",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/favorites/post/{post_id}`

- **摘要**：按文章ID取消收藏
- **鉴权**：需鉴权：`HTTPBearer`

根据文章 ID 取消收藏（需登录）。该文章未被当前用户收藏时 404。历史重复行（同一文章的多条收藏）会被一并清除。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `FavoriteActionResultOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 人类可读操作结果提示（如「收藏成功」） |
| success | boolean | 否 | 操作是否成功 |

响应示例：

```json
{
  "message": "string",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PATCH /api/favorites/post/{post_id}/folder`

- **摘要**：按文章ID移动收藏夹
- **鉴权**：需鉴权：`HTTPBearer`

根据文章 ID 移动收藏到指定收藏夹（需登录，folder_id 传 null 表示移回默认收藏）。成功后直接回显更新后的收藏记录行（重复行时回显最新一条，且所有重复行同步改夹）；收藏或目标收藏夹不存在时 404。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_move_favorite_by_post_api_favorites_post__post_id__folder_patch`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| folder_id | integer \| null | 否 |  |

```json
{
  "folder_id": "string"
}
```

**出参**

`200` · 模型 `FavoriteRecordOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| created_at | string \| null | 否 | 收藏时间（ISO 8601 字符串） |
| folder_id | integer \| null | 否 | 移动后的收藏夹 ID，移回默认收藏时为 null |
| id | integer | 是 | 收藏记录 ID |
| note | string \| null | 否 | 收藏备注，清空后为 null |
| post_id | integer | 是 | 被收藏的文章 ID |
| user_id | integer | 是 | 所属用户 ID |

响应示例：

```json
{
  "created_at": "string",
  "folder_id": "string",
  "id": 0,
  "note": "string",
  "post_id": 0,
  "user_id": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PATCH /api/favorites/post/{post_id}/note`

- **摘要**：按文章ID更新备注
- **鉴权**：需鉴权：`HTTPBearer`

根据文章 ID 更新收藏备注（需登录，note 传 null 表示清空备注）。成功后直接回显更新后的收藏记录行（重复行时回显最新一条，且所有重复行同步改备注）；收藏不存在时 404。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_update_favorite_note_by_post_api_favorites_post__post_id__note_patch`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| note | string \| null | 否 |  |

```json
{
  "note": "string"
}
```

**出参**

`200` · 模型 `FavoriteRecordOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| created_at | string \| null | 否 | 收藏时间（ISO 8601 字符串） |
| folder_id | integer \| null | 否 | 移动后的收藏夹 ID，移回默认收藏时为 null |
| id | integer | 是 | 收藏记录 ID |
| note | string \| null | 否 | 收藏备注，清空后为 null |
| post_id | integer | 是 | 被收藏的文章 ID |
| user_id | integer | 是 | 所属用户 ID |

响应示例：

```json
{
  "created_at": "string",
  "folder_id": "string",
  "id": 0,
  "note": "string",
  "post_id": 0,
  "user_id": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/favorites/{favorite_id}`

- **摘要**：更新收藏
- **鉴权**：需鉴权：`HTTPBearer`

信息（移动收藏夹、添加备注）。需登录；收藏不存在或不属于当前用户时 404，目标收藏夹非法时 404。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_update_favorite_api_favorites__favorite_id__put`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| folder_id | integer \| null | 否 |  |
| note | string \| null | 否 |  |

```json
{
  "folder_id": "string",
  "note": "string"
}
```

**出参**

`200` · 模型 `FavoriteActionResultOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 人类可读操作结果提示（如「收藏成功」） |
| success | boolean | 否 | 操作是否成功 |

响应示例：

```json
{
  "message": "string",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/favorites/{favorite_id}`

- **摘要**：取消收藏
- **鉴权**：需鉴权：`HTTPBearer`

按收藏记录 ID （需登录）。收藏不存在或不属于当前用户时 404。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `FavoriteActionResultOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 人类可读操作结果提示（如「收藏成功」） |
| success | boolean | 否 | 操作是否成功 |

响应示例：

```json
{
  "message": "string",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 后台管理（15）

仪表盘统计、用户管理、系统概览

### `GET /api/admin/comments`

- **摘要**：评论列表（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

获取所有评论，支持按状态、文章、作者筛选和分页。需 CurrentStaff。响应为裸分页 dict（items/total/page/page_size/total_pages，无 success/data 信封）；items 内每条评论是服务端手工拼装的投影：含 resolved_avatar_url、title 头衔徽章、post_ref/parent_ref/user_ref 摘要与 reply_total 聚合计数，replies 恒为空数组。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `CommentAdminListResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 否 | 当前页评论列表，按创建时间倒序 |
| page | integer | 是 | 当前页码，从 1 开始 |
| page_size | integer | 是 | 每页条数（1-100） |
| total | integer | 是 | 符合筛选条件的评论总数（不带 JOIN 的裸 count） |
| total_pages | integer | 是 | 总页数；total 为 0 时是 0 |

响应示例：

```json
{
  "items": [
    {
      "active": false,
      "author_avatar": "string",
      "author_email": "string",
      "author_name": "string",
      "author_url": "string",
      "author_website": "string",
      "avatar_source": "string",
      "content": "string",
      "created_at": "string",
      "github": "string",
      "id": 0,
      "is_pinned": false,
      "likes_count": 0,
      "parent_id": "string",
      "parent_ref": "string",
      "post_id": 0,
      "post_ref": "string",
      "qq": "string",
      "replies": [],
      "reply_total": 0,
      "resolved_avatar_url": "string",
      "status": "string",
      "title": "string",
      "updated_at": "string",
      "user_id": "string",
      "user_ref": "string"
    }
  ],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PATCH /api/admin/comments/{comment_id}`

- **摘要**：更新评论（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

修改评论内容、状态（approved/rejected/spam）等。status/active 变更会改变文章的 comments_count，故顺带失效该文章的详情/列表缓存。响应为手工拼装、与列表端点同构的评论投影 dict（不再经 CommentResponse 二次校验），但比列表条目少一个 title 头衔字段；replies 恒为空数组，reply_total 实时统计。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `CommentAdminUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| active | boolean \| null | 否 |  |
| content | string \| null | 否 |  |
| status | enum(`approved`, `pending`, `rejected`, `spam`) \| null | 否 |  |

```json
{
  "active": "string",
  "content": "string",
  "status": "string"
}
```

**出参**

`200` · 模型 `CommentAdminUpdatedDoc`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| active | boolean | 是 | 是否公开展示（旧布尔列，与 status 双向同步） |
| author_avatar | string | 是 | 作者头像原始 URL（模型 avatar 列），无头像时为空串 |
| author_email | string \| null | 否 | 匿名评论填写的邮箱，登录作者通常为 null |
| author_name | string | 是 | 显示名：author_name → 关联用户 nickname → 兜底字符串「匿名用户」 |
| author_url | string \| null | 否 | 匿名评论填写的个人站点 URL |
| author_website | string \| null | 否 | 作者网站：评论 author_website → 关联用户 website → null |
| avatar_source | string \| null | 否 | 头像来源标识（avatar_source 或 author_avatar_source），未设置为 null |
| content | string | 是 | 评论正文 |
| created_at | string \| null | 否 | 创建时间 ISO 8601 字符串，缺失为 null |
| github | string \| null | 否 | GitHub 用户名/主页，未提供为 null |
| id | integer | 是 | 评论 ID |
| is_pinned | boolean | 是 | 是否置顶 |
| likes_count | integer | 是 | 点赞数 |
| parent_id | integer \| null | 否 | 父评论 ID，顶级评论为 null |
| parent_ref | object \| null | 否 | 父评论摘要，顶级评论为 null |
| post_id | integer | 是 | 所属文章 ID |
| post_ref | object \| null | 否 | 关联文章摘要，文章缺失为 null |
| qq | string \| null | 否 | QQ 号（头像识别用），未提供为 null |
| replies | any[] | 否 | 嵌套回复列表：管理员列表端点恒为空数组（回复走 reply_total） |
| reply_total | integer | 是 | 直接回复数（按 parent_id 一条 GROUP BY 聚合，非模型列） |
| resolved_avatar_url | string \| null | 否 | 经 avatar_resolver 统一解析后的最终头像 URL |
| status | string | 是 | 审核状态：status 列真实值；为空时按 active 兜底推导 approved/rejected |
| title | null | 否 | 该端点不输出头衔（与列表端点的唯一字段差异），恒为 null |
| updated_at | string \| null | 否 | 更新时间 ISO 8601 字符串，缺失为 null |
| user_id | integer \| null | 否 | 登录作者的用户 ID，匿名评论为 null |
| user_ref | object \| null | 否 | 登录作者完整用户投影（UserResponse.model_dump），匿名评论为 null |

响应示例：

```json
{
  "active": false,
  "author_avatar": "string",
  "author_email": "string",
  "author_name": "string",
  "author_url": "string",
  "author_website": "string",
  "avatar_source": "string",
  "content": "string",
  "created_at": "string",
  "github": "string",
  "id": 0,
  "is_pinned": false,
  "likes_count": 0,
  "parent_id": "string",
  "parent_ref": "string",
  "post_id": 0,
  "post_ref": "string",
  "qq": "string",
  "replies": [],
  "reply_total": 0,
  "resolved_avatar_url": "string",
  "status": "string",
  "title": "string",
  "updated_at": "string",
  "user_id": "string",
  "user_ref": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/admin/comments/{comment_id}`

- **摘要**：删除评论（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

永久删除指定评论及其子回复。删除会改变文章的 comments_count，因此顺带失效该文章的详情/列表缓存。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/tools/optimize-search`

- **摘要**：补全检索字段
- **鉴权**：需鉴权：`HTTPBearer`

扫描缺少 slug 或摘要的文章，按标题生成唯一 slug、按各语言正文生成摘要。有实际改动时同步失效文章详情与列表缓存，避免 TTL 内继续吐出补字段前的旧正文。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `OptimizeSearchResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| excerpt_filled_count | integer | 是 |  |
| message | string | 是 |  |
| scanned_count | integer | 是 |  |
| slug_filled_count | integer | 是 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "excerpt_filled_count": 0,
  "message": "string",
  "scanned_count": 0,
  "slug_filled_count": 0,
  "success": true
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/admin/tools/search-stats`

- **摘要**：检索字段体检
- **鉴权**：需鉴权：`HTTPBearer`

统计缺少摘要/标签的文章数与 slug、摘要平均长度，为「补全检索字段」提供依据。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `SearchStatsResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| avg_excerpt_length | number | 是 |  |
| avg_slug_length | number | 是 |  |
| posts_without_excerpt | integer | 是 |  |
| posts_without_slug | integer | 是 |  |
| posts_without_tags | integer | 是 |  |
| recommendations | object[] | 是 |  |
| total_categories | integer | 是 |  |
| total_posts | integer | 是 |  |

响应示例：

```json
{
  "avg_excerpt_length": 0.0,
  "avg_slug_length": 0.0,
  "posts_without_excerpt": 0,
  "posts_without_slug": 0,
  "posts_without_tags": 0,
  "recommendations": [
    {
      "count": 0,
      "message": "string",
      "type": "excerpt"
    }
  ],
  "total_categories": 0,
  "total_posts": 0
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/admin/users`

- **摘要**：用户列表（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

获取所有用户列表，支持按 staff / 激活 / 封禁状态筛选与分页。响应为裸分页 dict（items/total/page/page_size/total_pages，无 success/data 信封）；items 内每项是 **AdminUserListItem** 投影（含 email / 封禁态 / 文章与评论计数），**不含** bio / website / github / qq / cover_image —— 那些在 `GET /admin/users/{id}`（UserDetailResponse）里。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PaginatedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | any[] | 是 |  |
| page | integer | 是 | 当前页码 |
| page_size | integer | 是 | 每页大小 |
| total | integer | 是 | 总记录数 |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/users`

- **摘要**：创建用户（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

管理员创建新用户。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `AdminUserCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| bio | string \| null | 否 | 个人简介 |
| email | string | 是 | 邮箱地址 |
| github | string \| null | 否 | GitHub 主页 |
| is_active | boolean | 否 | 是否激活 |
| is_staff | boolean | 否 | 是否为管理员（兼容字段，创建后会同步 role） |
| nickname | string \| null | 否 | 昵称 |
| password | string | 是 | 密码（至少8位，包含大小写字母和数字） |
| role | string \| null | 否 | RBAC 角色：super_admin/admin/editor/author/contributor/subscriber。为空时由 is_staff/is_superuser 派生。 |
| username | string | 是 | 用户名（只允许字母、数字、下划线和连字符） |
| website | string \| null | 否 | 个人网站 |

```json
{
  "bio": "string",
  "email": "string",
  "github": "string",
  "is_active": true,
  "is_staff": false,
  "nickname": "string",
  "password": "string",
  "role": "string",
  "username": "string",
  "website": "string"
}
```

**出参**

`201` · 模型 `UserResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| avatar | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| bio | string \| null | 否 | 个人简介 |
| cover_image | string \| null | 否 |  |
| created_at | string | 是 |  |
| email | string | 是 | 邮箱地址 |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 是 |  |
| is_staff | boolean | 是 |  |
| is_superuser | boolean | 是 |  |
| last_login | string \| null | 否 |  |
| nickname | string \| null | 否 | 昵称 |
| qq | string \| null | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| role | string \| null | 否 |  |
| title | object \| null | 否 |  |
| username | string | 是 | 用户名 |
| website | string \| null | 否 |  |

响应示例：

```json
{
  "avatar": "string",
  "avatar_source": "string",
  "bio": "string",
  "cover_image": "string",
  "created_at": "string",
  "email": "string",
  "github": "string",
  "id": 0,
  "is_active": false,
  "is_staff": false,
  "is_superuser": false,
  "last_login": "string",
  "nickname": "string",
  "qq": "string",
  "resolved_avatar_url": "string",
  "role": "string",
  "title": "string",
  "username": "string",
  "website": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/admin/users/{user_id}`

- **摘要**：获取用户详情（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

管理员获取用户详细信息。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `UserDetailResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| avatar | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| bio | string \| null | 否 |  |
| comments_count | integer | 否 |  |
| cover_image | string \| null | 否 |  |
| created_at | string | 是 |  |
| email | string | 是 | 邮箱地址 |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 是 |  |
| is_banned | boolean | 否 |  |
| is_staff | boolean | 是 |  |
| is_superuser | boolean | 是 |  |
| last_login | string \| null | 否 |  |
| nickname | string \| null | 否 | 昵称 |
| posts_count | integer | 否 |  |
| qq | string \| null | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| role | string \| null | 否 |  |
| title | object \| null | 否 |  |
| updated_at | string \| null | 否 |  |
| username | string | 是 | 用户名 |
| website | string \| null | 否 |  |

响应示例：

```json
{
  "avatar": "string",
  "avatar_source": "string",
  "bio": "string",
  "comments_count": 0,
  "cover_image": "string",
  "created_at": "string",
  "email": "string",
  "github": "string",
  "id": 0,
  "is_active": false,
  "is_banned": false,
  "is_staff": false,
  "is_superuser": false,
  "last_login": "string",
  "nickname": "string",
  "posts_count": 0,
  "qq": "string",
  "resolved_avatar_url": "string",
  "role": "string",
  "title": "string",
  "updated_at": "string",
  "username": "string",
  "website": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/admin/users/{user_id}`

- **摘要**：更新用户（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

管理员更新用户信息。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `AdminUserUpdateFull`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| avatar | string \| null | 否 |  |
| avatar_source | enum(`auto`, `custom`, `github`, `qq`, `gravatar`) \| null | 否 | 头像来源，取值与 /api/media/avatar 解析器白名单一致 |
| bio | string \| null | 否 |  |
| cover_image | string \| null | 否 |  |
| email | string \| null | 否 |  |
| github | string \| null | 否 |  |
| is_active | boolean \| null | 否 |  |
| is_banned | boolean \| null | 否 |  |
| is_staff | boolean \| null | 否 |  |
| nickname | string \| null | 否 |  |
| qq | string \| null | 否 | QQ 号；UserDetailResponse 会回显该字段，此处必须可写，否则管理员改 QQ 静默失效 |
| role | string \| null | 否 | RBAC 角色：super_admin/admin/editor/author/contributor/subscriber。为空时不变更。 |
| username | string \| null | 否 | 用户名（可选，留空则不修改） |
| website | string \| null | 否 |  |

```json
{
  "avatar": "string",
  "avatar_source": "string",
  "bio": "string",
  "cover_image": "string",
  "email": "string",
  "github": "string",
  "is_active": "string",
  "is_banned": "string",
  "is_staff": "string",
  "nickname": "string",
  "qq": "string",
  "role": "string",
  "username": "string",
  "website": "string"
}
```

**出参**

`200` · 模型 `UserDetailResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| avatar | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| bio | string \| null | 否 |  |
| comments_count | integer | 否 |  |
| cover_image | string \| null | 否 |  |
| created_at | string | 是 |  |
| email | string | 是 | 邮箱地址 |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_active | boolean | 是 |  |
| is_banned | boolean | 否 |  |
| is_staff | boolean | 是 |  |
| is_superuser | boolean | 是 |  |
| last_login | string \| null | 否 |  |
| nickname | string \| null | 否 | 昵称 |
| posts_count | integer | 否 |  |
| qq | string \| null | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| role | string \| null | 否 |  |
| title | object \| null | 否 |  |
| updated_at | string \| null | 否 |  |
| username | string | 是 | 用户名 |
| website | string \| null | 否 |  |

响应示例：

```json
{
  "avatar": "string",
  "avatar_source": "string",
  "bio": "string",
  "comments_count": 0,
  "cover_image": "string",
  "created_at": "string",
  "email": "string",
  "github": "string",
  "id": 0,
  "is_active": false,
  "is_banned": false,
  "is_staff": false,
  "is_superuser": false,
  "last_login": "string",
  "nickname": "string",
  "posts_count": 0,
  "qq": "string",
  "resolved_avatar_url": "string",
  "role": "string",
  "title": "string",
  "updated_at": "string",
  "username": "string",
  "website": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PATCH /api/admin/users/{user_id}`

- **摘要**：部分更新用户（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

仅更新提供的字段：is_staff/is_active/is_banned 状态位与 RBAC role。需超级管理员（CurrentSuperUser）；不能改自己（400）、目标不存在（404）、不能改超级管理员（403）、角色非法（400）或高于自身层级（403）。变更 role 后会反向同步 is_superuser/is_staff 布尔位，响应回显更新后的用户状态摘要。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `AdminUserUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| is_active | boolean \| null | 否 |  |
| is_banned | boolean \| null | 否 |  |
| is_staff | boolean \| null | 否 |  |
| role | string \| null | 否 | RBAC 角色：super_admin/admin/editor/author/contributor/subscriber。为空时不变更。 |

```json
{
  "is_active": "string",
  "is_banned": "string",
  "is_staff": "string",
  "role": "string"
}
```

**出参**

`200` · 模型 `AdminUserStatusResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| avatar | string \| null | 否 | 自定义头像 URL，未设置时为 null |
| email | string | 是 | 邮箱（管理员视图明文回显） |
| id | integer | 是 | 用户 ID |
| is_active | boolean | 是 | 账号是否激活 |
| is_banned | boolean | 是 | 是否封禁 |
| is_staff | boolean | 是 | 是否管理员（变更 role 时按 RBAC 层级反向同步） |
| is_superuser | boolean | 是 | 是否超级管理员（仅 role==super_admin 时为 true） |
| nickname | string \| null | 否 | 昵称，未设置时为 null |
| role | string \| null | 否 | RBAC 角色名，历史数据可能为 null |
| username | string | 是 | 用户名 |

响应示例：

```json
{
  "avatar": "string",
  "email": "string",
  "id": 0,
  "is_active": false,
  "is_banned": false,
  "is_staff": false,
  "is_superuser": false,
  "nickname": "string",
  "role": "string",
  "username": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/admin/users/{user_id}`

- **摘要**：删除用户（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentSuperUser。软删除：只封禁 + 停用，用户行保留。副作用是把该用户的可空外键引用置空——评论与留言板变匿名；`Post.author_id` 为 NOT NULL，文章继续归属原作者（不做处理）。不能删除自己或超级管理员，均返回 4xx。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/users/{user_id}/activate`

- **摘要**：激活用户（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

管理员激活已禁用的用户。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/users/{user_id}/ban`

- **摘要**：封禁用户（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

管理员封禁用户。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/users/{user_id}/reset-password`

- **摘要**：重置用户密码（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

管理员重置用户密码。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `PasswordReset`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| new_password | string | 是 | 新密码（至少8位，包含大小写字母和数字） |

```json
{
  "new_password": "string"
}
```

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/users/{user_id}/unban`

- **摘要**：解封用户（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

管理员解封用户。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## Webhook（9）

外部服务回调配置与日志

### `GET /api/webhooks`

- **摘要**：Webhook 列表
- **鉴权**：需鉴权：`HTTPBearer`

获取所有 Webhook 端点列表。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `WebhookListOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 |  |
| page | integer | 是 |  |
| page_size | integer | 是 |  |
| total | integer | 是 |  |

响应示例：

```json
{
  "items": [
    {
      "active": false,
      "created_at": "string",
      "events": [
        "…"
      ],
      "has_secret": false,
      "id": 0,
      "last_triggered_at": "string",
      "name": "string",
      "provider": "string",
      "updated_at": "string",
      "url": "string"
    }
  ],
  "page": 0,
  "page_size": 0,
  "total": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/webhooks`

- **摘要**：创建 Webhook
- **鉴权**：需鉴权：`HTTPBearer`

创建新的 Webhook 端点。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `WebhookCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| active | boolean | 否 |  |
| events | string[] | 是 |  |
| name | string | 是 |  |
| provider | string | 否 |  |
| secret | string \| null | 否 |  |
| url | string | 是 |  |

```json
{
  "active": true,
  "events": [
    "string"
  ],
  "name": "string",
  "provider": "generic",
  "secret": "string",
  "url": "string"
}
```

**出参**

`200` · 模型 `WebhookOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| active | boolean | 是 |  |
| created_at | string \| null | 否 |  |
| events | string[] | 是 |  |
| has_secret | boolean | 是 |  |
| id | integer | 是 |  |
| last_triggered_at | string \| null | 否 |  |
| name | string | 是 |  |
| provider | string | 是 |  |
| updated_at | string \| null | 否 |  |
| url | string | 是 |  |

响应示例：

```json
{
  "active": false,
  "created_at": "string",
  "events": [
    "string"
  ],
  "has_secret": false,
  "id": 0,
  "last_triggered_at": "string",
  "name": "string",
  "provider": "string",
  "updated_at": "string",
  "url": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/webhooks/deliveries/{delivery_id}/retry`

- **摘要**：重试投递
- **鉴权**：需鉴权：`HTTPBearer`

重新发送失败的 Webhook 投递（需管理员）。按库内 payload 原文复发以保持签名一致性，并就地更新该投递记录的状态码/响应体/错误；投递或端点不存在时 404。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `WebhookActionResultOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 人类可读操作结果提示 |
| success | boolean | 否 | 操作是否成功 |

响应示例：

```json
{
  "message": "string",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/webhooks/events`

- **摘要**：支持的事件类型
- **鉴权**：公开接口（无需鉴权）

获取所有可订阅的 Webhook 事件类型（无需管理员写权限即可读取）。事件名即 hooks 总线上的 do_action 名，前端订阅清单必须来自本接口，不得自有一套命名。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `WebhookEventsOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| events | object[] | 是 | 全部可订阅事件列表，是前端订阅 UI 的唯一事件名来源 |

响应示例：

```json
{
  "events": [
    {
      "description": "string",
      "type": "string"
    }
  ]
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `PUT /api/webhooks/{webhook_id}`

- **摘要**：更新 Webhook
- **鉴权**：需鉴权：`HTTPBearer`

端点配置。未提供的字段保持不变；secret 传空串表示清除密钥。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `WebhookUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| active | boolean \| null | 否 |  |
| events | string[] \| null | 否 |  |
| name | string \| null | 否 |  |
| provider | string \| null | 否 |  |
| secret | string \| null | 否 |  |
| url | string \| null | 否 |  |

```json
{
  "active": "string",
  "events": "string",
  "name": "string",
  "provider": "string",
  "secret": "string",
  "url": "string"
}
```

**出参**

`200` · 模型 `WebhookOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| active | boolean | 是 |  |
| created_at | string \| null | 否 |  |
| events | string[] | 是 |  |
| has_secret | boolean | 是 |  |
| id | integer | 是 |  |
| last_triggered_at | string \| null | 否 |  |
| name | string | 是 |  |
| provider | string | 是 |  |
| updated_at | string \| null | 否 |  |
| url | string | 是 |  |

响应示例：

```json
{
  "active": false,
  "created_at": "string",
  "events": [
    "string"
  ],
  "has_secret": false,
  "id": 0,
  "last_triggered_at": "string",
  "name": "string",
  "provider": "string",
  "updated_at": "string",
  "url": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/webhooks/{webhook_id}`

- **摘要**：删除 Webhook
- **鉴权**：需鉴权：`HTTPBearer`

端点（需管理员）。端点不存在时 404；删除后该端点不再接收任何事件投递。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `WebhookActionResultOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 人类可读操作结果提示 |
| success | boolean | 否 | 操作是否成功 |

响应示例：

```json
{
  "message": "string",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/webhooks/{webhook_id}/deliveries`

- **摘要**：投递记录
- **鉴权**：需鉴权：`HTTPBearer`

获取 Webhook 的。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `WebhookDeliveryListOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 |  |
| page | integer | 是 |  |
| page_size | integer | 是 |  |
| total | integer | 是 |  |

响应示例：

```json
{
  "items": [
    {
      "created_at": "string",
      "delivered_at": "string",
      "error": "string",
      "event_type": "string",
      "id": 0,
      "response_body": "string",
      "status_code": "string"
    }
  ],
  "page": 0,
  "page_size": 0,
  "total": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/webhooks/{webhook_id}/regenerate-secret`

- **摘要**：重新生成密钥
- **鉴权**：需鉴权：`HTTPBearer`

生成新的 HMAC 密钥并返回**明文**（需管理员，仅此接口给出）；旧密钥立即失效，接收方必须同步更新，否则后续投递的签名校验全部失败。端点不存在时 404。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `WebhookSecretRotateOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 轮换后一次性给出的密钥数据 |
| data.secret | string | 是 | 新生成的 HMAC-SHA256 密钥明文（64 位十六进制字符串）。仅此接口、仅此一次返回明文，此后列表/详情只回显 has_secret，旧密钥立即失效 |
| message | string | 是 | 提示需同步更新接收方配置 |
| success | boolean | 否 | 操作是否成功 |

响应示例：

```json
{
  "data": {
    "secret": "string"
  },
  "message": "string",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/webhooks/{webhook_id}/test`

- **摘要**：测试 Webhook
- **鉴权**：需鉴权：`HTTPBearer`

发送测试请求到 Webhook URL（需管理员）。与真实投递共用同一套签名头与 SSRF 护栏，并落一条 event_type=test 的投递记录；端点不存在时 404。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `WebhookTestResultOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 测试结果说明；失败时含错误摘要 |
| status_code | integer \| null | 否 | 目标端点返回的 HTTP 状态码；请求未发出（网络错误/被护栏拦截）时为 null |
| success | boolean | 是 | 测试是否通过（目标端点未返回 5xx 且未被 SSRF 护栏拦截） |

响应示例：

```json
{
  "message": "string",
  "status_code": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 导入导出（7）

内容数据的批量导入与导出

### `GET /api/admin/backup/full`

- **摘要**：全站备份
- **鉴权**：需鉴权：`HTTPBearer`

导出整站数据为 ZIP 文件，包含所有内容模型及 manifest.json。需 staff 及以上权限（未登录 401，非管理员 403）。包内按模型分文件（文章、分类、标签、评论、用户、媒体、友情链接、导航、页面、公告、首屏轮播、站点配置，文章系列可用时另有一份），时间统一序列化为 ISO 字符串；manifest.json 记录备份版本、生成时间、导出者与每张表的条数。注意：备份的是数据库行（含媒体记录），不打包磁盘上的媒体文件本体；整包在内存里组装后流式下发，大站慎用。导入本包请用全站恢复接口。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/admin/backup/info`

- **摘要**：备份信息
- **鉴权**：需鉴权：`HTTPBearer`

返回当前数据库各项数据统计，用于备份前预览。需 staff 及以上权限（未登录 401，非管理员 403）。每个模型一条 COUNT 查询，无缓存；文章系列模型不可用时 counts 里没有对应键。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BackupInfoResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| counts | object<string, integer> | 否 | 各内容模型的行数。键固定为 posts / categories / tags / comments / users / media / friend_links / navigations / pages / announcements / hero_slides / site … （完整说明见 `/docs`） |
| queried_at | string | 是 | 统计时刻的 UTC ISO 8601 时间字符串 |
| queried_by | string | 是 | 发起本次统计的登录用户名 |
| total | integer | 否 | counts 各值之和，即整站记录总条数 |

响应示例：

```json
{
  "counts": {},
  "queried_at": "string",
  "queried_by": "string",
  "total": 0
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `POST /api/admin/backup/restore`

- **摘要**：全站恢复
- **鉴权**：需鉴权：`HTTPBearer`

上传全站备份 ZIP 恢复整站数据。需 staff 及以上权限（未登录 401，非管理员 403）。文件名必须以 .zip 结尾，否则 400；压缩包本身解析失败也是 400。缺某个 JSON 分项不报错、按空集合跳过，因此请确认包来自全站备份接口。按外键依赖顺序导入（站点配置 → 用户 → 分类/标签 → …… → 文章 → 评论 → 媒体）。是否已存在按自然键判断：站点配置看 key、用户看 username、分类/标签/页面/文章看 slug、媒体看存储路径。策略 skip_existing（默认）把已存在条目计为跳过；overwrite 覆盖可写字段并计入 created_count，但用户是分脱敏恢复（不还原密码，新用户用占位密码与邮箱），文章的密码 hash 也不信任备份值。完成后连带失效内容、站点配置、导航、友情链接等缓存。结果以 200 返回，success 恒为 true，逐条失败看 error_count 与 errors（最多回传前 20 条）。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_backup_restore_api_admin_backup_restore_post`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| file | string | 是 |  |

```json
{
  "file": "string"
}
```

**出参**

`200` · 模型 `ImportResult`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| created_count | integer | 否 | 新建或被覆盖更新的条目数；单文件 Markdown 导入成功时为 1 |
| error_count | integer | 否 | 逐条解析或写库失败的条目数；计数是全量的 |
| errors | string[] | 否 | 失败明细（每条一个中文短句）：文章导入最多回传前 10 条，全站恢复最多回传前 20 条 |
| message | string | 是 | 人类可读汇总文案（含创建/跳过/失败计数） |
| skipped_count | integer | 否 | 按策略跳过的条目数（同 slug 已存在、恢复策略为 skip_existing 等） |
| success | boolean | 是 | 本次导入整体是否成功；false 时 message 说明失败原因 |

响应示例：

```json
{
  "created_count": 0,
  "error_count": 0,
  "errors": [
    "string"
  ],
  "message": "string",
  "skipped_count": 0,
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/admin/export/markdown`

- **摘要**：导出为 Markdown
- **鉴权**：需鉴权：`HTTPBearer`

将文章 文件。需 staff 及以上权限（未登录 401，非管理员 403）。只导已发布文章（无草稿开关），每篇一个 ``<slug>.md``，正文前拼 YAML frontmatter（title / slug / date / category / tags / cover，空字段整行省略），并附一个 README.md 记录导出时间与篇数。lang 选择 frontmatter 与正文取用的语言变体，取不到时回退 zh。from/to 按创建时间过滤（含边界）；不含图片资产，压缩包是纯文本。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/admin/export/posts`

- **摘要**：导出文章
- **鉴权**：需鉴权：`HTTPBearer`

导出所有文章为 JSON 格式（Rosetta 原生 JSON ZIP）。需 staff 及以上权限（未登录 401，非管理员 403）。format 仅支持 json，未实现格式明确 400。默认只导已发布文章，include_drafts=true 时含草稿（scope=published 又把范围收窄回已发布）；from/to 按创建时间过滤（含边界，只给日期时上界补足到当天 23:59:59）；include_content=false 可只导元数据不带正文。包内是 posts.json / categories.json / tags.json 三个 UTF-8 JSON 文件。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/import/markdown`

- **摘要**：导入 Markdown
- **鉴权**：需鉴权：`HTTPBearer`

导入单个 Markdown 文件为文章。需 staff 及以上权限（未登录 401，非管理员 403）。上传内容按 UTF-8 文本解析：必须是以 --- 包裹的 frontmatter，取其中的 title 与 slug（缺 slug 时由标题小写转写生成），正文落为 zh 变体；default_category 参数当前实现未参与写库。导入的文章一律是草稿状态，不会直接上线。未提供文件名时 400；slug 已存在或解析不到 frontmatter 时返回 200 且 success=false（不抛 4xx），调用方须读 success 判定结果。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_import_markdown_api_admin_import_markdown_post`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| file | string | 是 |  |

```json
{
  "file": "string"
}
```

**出参**

`200` · 模型 `ImportResult`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| created_count | integer | 否 | 新建或被覆盖更新的条目数；单文件 Markdown 导入成功时为 1 |
| error_count | integer | 否 | 逐条解析或写库失败的条目数；计数是全量的 |
| errors | string[] | 否 | 失败明细（每条一个中文短句）：文章导入最多回传前 10 条，全站恢复最多回传前 20 条 |
| message | string | 是 | 人类可读汇总文案（含创建/跳过/失败计数） |
| skipped_count | integer | 否 | 按策略跳过的条目数（同 slug 已存在、恢复策略为 skip_existing 等） |
| success | boolean | 是 | 本次导入整体是否成功；false 时 message 说明失败原因 |

响应示例：

```json
{
  "created_count": 0,
  "error_count": 0,
  "errors": [
    "string"
  ],
  "message": "string",
  "skipped_count": 0,
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/import/posts`

- **摘要**：导入文章
- **鉴权**：需鉴权：`HTTPBearer`

从 Rosetta 导出的 JSON ZIP（posts/categories/tags.json）。需 staff 及以上权限（未登录 401，非管理员 403）。skip_existing=true 跳过同名 slug；false 覆盖更新既有文章，但覆盖时有意保留原作者与密码 hash。format 仅支持 json，其它取值 400。压缩包解析不出 posts.json 时 400。成功与失败都以 200 返回，由 success 与 errors 判定逐条结果；errors 只回传前 10 条，error_count 才是全量失败数。导入后会写一条后台操作日志并失效内容缓存。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_import_posts_api_admin_import_posts_post`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| file | string | 是 |  |

```json
{
  "file": "string"
}
```

**出参**

`200` · 模型 `ImportResult`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| created_count | integer | 否 | 新建或被覆盖更新的条目数；单文件 Markdown 导入成功时为 1 |
| error_count | integer | 否 | 逐条解析或写库失败的条目数；计数是全量的 |
| errors | string[] | 否 | 失败明细（每条一个中文短句）：文章导入最多回传前 10 条，全站恢复最多回传前 20 条 |
| message | string | 是 | 人类可读汇总文案（含创建/跳过/失败计数） |
| skipped_count | integer | 否 | 按策略跳过的条目数（同 slug 已存在、恢复策略为 skip_existing 等） |
| success | boolean | 是 | 本次导入整体是否成功；false 时 message 说明失败原因 |

响应示例：

```json
{
  "created_count": 0,
  "error_count": 0,
  "errors": [
    "string"
  ],
  "message": "string",
  "skipped_count": 0,
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## SEO（9）

站点地图、Robots、SEO 设置

### `GET /api/seo/config`

- **摘要**：获取 SEO 配置
- **鉴权**：公开接口（无需鉴权）

读取站点 SEO 相关配置（TITLE、DESCRIPTION、KEYWORDS 等），公开接口。返回裸对象且只含服务端白名单里已配置的键，未配置的键不会出现。结果按站点配置缓存组缓存 1 小时，任何一次更新配置都会连带清掉这批缓存。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `SeoConfigMapResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| SEO_AUTHOR | string \| null | 否 | 默认作者署名 |
| SEO_CANONICAL | string \| null | 否 | 规范链接（canonical）覆盖值 |
| SEO_DESCRIPTION | string \| null | 否 | 站点描述 |
| SEO_IMAGE | string \| null | 否 | 默认分享图 URL |
| SEO_KEYWORDS | string \| null | 否 | 站点关键词 |
| SEO_OG_SITE_NAME | string \| null | 否 | Open Graph 站点名 |
| SEO_ROBOTS | string \| null | 否 | 默认 robots 指令 |
| SEO_STRUCTURED_DATA | string \| null | 否 | 附加结构化数据（JSON-LD 文本） |
| SEO_TITLE | string \| null | 否 | 站点标题 |
| SEO_TWITTER_SITE | string \| null | 否 | Twitter 站点账号（@handle） |

响应示例：

```json
{
  "SEO_AUTHOR": "string",
  "SEO_CANONICAL": "string",
  "SEO_DESCRIPTION": "string",
  "SEO_IMAGE": "string",
  "SEO_KEYWORDS": "string",
  "SEO_OG_SITE_NAME": "string",
  "SEO_ROBOTS": "string",
  "SEO_STRUCTURED_DATA": "string",
  "SEO_TITLE": "string",
  "SEO_TWITTER_SITE": "string"
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `PUT /api/seo/config`

- **摘要**：【管理员】更新 SEO 配置
- **鉴权**：需鉴权：`HTTPBearer`

批量更新 SEO 配置 key-value，保存到 SiteConfig 表。需 staff 及以上权限（未登录 401，非管理员 403）。请求体是 SEO 键到字符串的扁平对象；白名单外的键被静默忽略，值为 null 时写入空字符串（即清空）。成功后会清掉 seo / site_config 相关缓存并回写全量配置。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`）


```json
{}
```

**出参**

`200` · 模型 `SeoConfigUpdateResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | SEO 配置键值集合（裸对象，无 success 信封）。 键来自服务端白名单，未配置过的键直接缺席而非返回 null， 因此全部字段声明为可选。 |
| data.SEO_AUTHOR | string \| null | 否 | 默认作者署名 |
| data.SEO_CANONICAL | string \| null | 否 | 规范链接（canonical）覆盖值 |
| data.SEO_DESCRIPTION | string \| null | 否 | 站点描述 |
| data.SEO_IMAGE | string \| null | 否 | 默认分享图 URL |
| data.SEO_KEYWORDS | string \| null | 否 | 站点关键词 |
| data.SEO_OG_SITE_NAME | string \| null | 否 | Open Graph 站点名 |
| data.SEO_ROBOTS | string \| null | 否 | 默认 robots 指令 |
| data.SEO_STRUCTURED_DATA | string \| null | 否 | 附加结构化数据（JSON-LD 文本） |
| data.SEO_TITLE | string \| null | 否 | 站点标题 |
| data.SEO_TWITTER_SITE | string \| null | 否 | Twitter 站点账号（@handle） |
| message | string | 否 | 人类可读结果 |
| success | boolean | 否 | 固定为 true；失败走 HTTPException 错误信封 |

响应示例：

```json
{
  "data": {
    "SEO_AUTHOR": "string",
    "SEO_CANONICAL": "string",
    "SEO_DESCRIPTION": "string",
    "SEO_IMAGE": "string",
    "SEO_KEYWORDS": "string",
    "SEO_OG_SITE_NAME": "string",
    "SEO_ROBOTS": "string",
    "SEO_STRUCTURED_DATA": "string",
    "SEO_TITLE": "string",
    "SEO_TWITTER_SITE": "string"
  },
  "message": "SEO 配置已更新",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/seo/open-graph/{resource_type}/{resource_id}`

- **摘要**：Open Graph 数据
- **鉴权**：公开接口（无需鉴权）

获取资源的 Open Graph 元数据，公开访问、无需鉴权，用于社交媒体分享时显示预览。目前只对文章内容资源有实现，返回 og:* / article:* / twitter:* 三组键（键名含冒号，需按字面取值），返回 og:* / article:* / twitter:* 三组键（键名含冒号，需按字面取值），摘要在服务端剥离短代码与 HTML 标签后截断到前 200 字符。资源不存在或类型不受支持时返回 200 且响应体只有 error 字段（不是 404）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `OpenGraphResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| article:author | string \| null | 否 | 作者主页 URL；文章无作者记录时为 null |
| article:modified_time | string \| null | 否 | 更新时间 ISO 8601 字符串；无值时为 null |
| article:published_time | string \| null | 否 | 发布时间 ISO 8601 字符串；未发布时为 null |
| error | string \| null | 否 | 错误说明（Article not found / Unsupported resource type）；出现该字段时不再包含任何 og:* 键，HTTP 状态仍是 200 |
| og:description | string | 否 | 文章摘要，服务端截断到前 200 字符；摘要为空时是空字符串 |
| og:image | string \| null | 否 | 封面图 URL；未设置封面时为 null |
| og:locale | string | 否 | 固定 zh_CN |
| og:site_name | string | 否 | 站点名，取不到时回退 Rosetta Blog |
| og:title | string | 否 | 文章标题（多语言取 zh 文案） |
| og:type | string | 否 | Open Graph 类型，文章资源固定 article |
| og:url | string | 否 | 文章规范 URL |
| twitter:card | string | 否 | Twitter 卡片样式，固定大图卡 |
| twitter:description | string | 否 | 与 og:description 同值（同样截断到 200 字符） |
| twitter:image | string \| null | 否 | 与 og:image 同值；未设置封面时为 null |
| twitter:title | string | 否 | 与 og:title 同值 |

响应示例：

```json
{
  "article:author": "string",
  "article:modified_time": "string",
  "article:published_time": "string",
  "error": "string",
  "og:description": "",
  "og:image": "string",
  "og:locale": "zh_CN",
  "og:site_name": "",
  "og:title": "",
  "og:type": "article",
  "og:url": "",
  "twitter:card": "summary_large_image",
  "twitter:description": "",
  "twitter:image": "string",
  "twitter:title": ""
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/seo/robots.txt`

- **摘要**：robots.txt
- **鉴权**：公开接口（无需鉴权）

动态生成 文件。公开访问、无需鉴权，返回 text/plain。优先取站点配置里维护的 robots 全文，缺省时输出默认规则（放行全站、屏蔽后台与接口目录、追加站点 sitemap 绝对地址）。结果缓存 1 小时。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/seo/schema/{resource_type}/{resource_id}`

- **摘要**：结构化数据
- **鉴权**：公开接口（无需鉴权）

获取资源的 JSON-LD ，公开访问、无需鉴权。resource_type 支持 article/post、person、website、breadcrumb，返回的 @type 相应为 Article / Person / WebSite / BreadcrumbList，其中 Article 会带上作者、发布方与所属分类；标题与摘要为服务端纯文本（已剥离短代码字面量与 HTML 标签）。资源不存在或类型不受支持时返回 200 且响应体只有 error 字段（不是 404），调用方需自行判空。breadcrumb 分支不查库，固定返回首页一项。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `JsonLdSchemaResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| @context | string \| null | 否 | 固定为 https://schema.org（OpenAPI 键名 @context） |
| @type | string \| null | 否 | schema.org 类型：article/post 取 Article，person 取 Person，website 取 WebSite，breadcrumb 取 BreadcrumbList |
| articleSection | string \| null | 否 | Article 所属分类名（多语言取 zh）；文章没有分类时该键整体缺席 |
| author | object \| null | 否 | Article 形态的作者对象：{@type: Person, name, url}；无作者记录时 name 为 Anonymous、url 为 null |
| dateModified | string \| null | 否 | Article 形态的更新时间 ISO 8601 字符串；无值时为 null |
| datePublished | string \| null | 否 | Article 形态的发布时间 ISO 8601 字符串；未发布时为 null |
| description | string \| null | 否 | Article / Person / WebSite 形态共用的描述文案 |
| error | string \| null | 否 | 错误说明（Article not found / Person not found / Unsupported resource type）；出现该字段时不再包含任何 JSON-LD 字段，HTTP 状态仍是 200 |
| headline | string \| null | 否 | Article 形态的标题（取多语言 zh 文案） |
| image | string \| null | 否 | Article 形态为封面图 URL；Person 形态为头像 URL |
| itemListElement | object[] | 否 | BreadcrumbList 形态的面包屑项数组，当前实现固定一项首页 {@type, position, name, item} |
| mainEntityOfPage | object \| null | 否 | Article 形态的宿主页面引用：{@type: WebPage, @id: 文章 URL} |
| name | string \| null | 否 | Person 昵称（缺省回退用户名）/ WebSite 站点名（Article 形态无该键） |
| potentialAction | object \| null | 否 | WebSite 形态的站内搜索动作：{@type: SearchAction, target, query-input} |
| publisher | object \| null | 否 | Article 形态的发布方对象：{@type: Organization, name, logo}，name 固定 Rosetta Blog |
| sameAs | string[] | 否 | Person 形态的外部主页集合（GitHub、个人网站），为空的链接不会入列 |
| url | string \| null | 否 | 实体规范 URL：Article 指文章页，Person 指作者页，WebSite 指站点根 |

响应示例：

```json
{
  "@context": "string",
  "@type": "string",
  "articleSection": "string",
  "author": "string",
  "dateModified": "string",
  "datePublished": "string",
  "description": "string",
  "error": "string",
  "headline": "string",
  "image": "string",
  "itemListElement": [
    {}
  ],
  "mainEntityOfPage": "string",
  "name": "string",
  "potentialAction": "string",
  "publisher": "string",
  "sameAs": [
    "string"
  ],
  "url": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/seo/scores`

- **摘要**：【管理员】文章 SEO 评分
- **鉴权**：需鉴权：`HTTPBearer`

对已发布文章进行 SEO 评分（标题长度、摘要、封面、内容长度、标签），分页返回。需 staff 及以上权限（未登录 401，非管理员 403）。评分在内存里对全量已发布文章计算后再切片，返回按得分升序排列（最需要改进的文章在前）；page_size 上限 100。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `SeoScoresResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 否 | 当前页评分条目，按得分升序（差的排前面） |
| page | integer | 否 | 当前页码（回显请求参数） |
| page_size | integer | 否 | 每页数量（回显请求参数，上限 100） |
| total | integer | 否 | 已发布文章总数（评分在内存里全量算完再分页） |
| total_pages | integer | 否 | 总页数；total 为 0 时是 0 |

响应示例：

```json
{
  "items": [
    {
      "id": 0,
      "score": 0,
      "slug": "string",
      "suggestions": [
        "…"
      ],
      "title": "string"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/seo/sitemap-check`

- **摘要**：【管理员】校验 Sitemap 健康度
- **鉴权**：需鉴权：`HTTPBearer`

检查已发布文章是否具备 SEO 必要字段（标题 / 摘要 / 封面），返回校验结果与问题清单。需 staff 及以上权限（未登录 401，非管理员 403）。问题清单最多返回前 50 条，但 url_count 与 ok 的判定基于全量文章；无缓存，每次请求都会全表扫描已发布文章。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `SitemapCheckResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | Sitemap 健康度校验载荷。 |
| data.errors | string[] | 否 | 问题清单，中文字面量（如「文章 #12 缺少摘要」），最多返回前 50 条 |
| data.ok | boolean | 是 | 是否零问题：只要有一条缺项即为 false |
| data.url_count | integer | 否 | 参与校验的已发布文章数（未截断，可能大于 errors 的可见条数） |
| success | boolean | 否 | 固定为 true；有问题不代表请求失败 |

响应示例：

```json
{
  "data": {
    "errors": [
      "string"
    ],
    "ok": false,
    "url_count": 0
  },
  "success": true
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/seo/sitemap.xml`

- **摘要**：SEO sitemap.xml（同 /api/blog/sitemap.xml）
- **鉴权**：公开接口（无需鉴权）

从 SEO 模块对外暴露统一 sitemap 路径，避免前端路由不一致。公开访问、无需鉴权。索引含已发布文章（带 lastmod）、启用中的分类与标签；结果缓存 1 小时，命中缓存时直接回吐 XML 文本。Content-Type 为 application/xml。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `POST /api/seo/sitemap/generate`

- **摘要**：【管理员】强制重新生成 sitemap 缓存
- **鉴权**：需鉴权：`HTTPBearer`

清除 sitemap 相关缓存（含博客列表缓存前缀），下一次请求将重新生成。需 staff 及以上权限（未登录 401，非管理员 403）。本接口是异步失效而非同步重建，因此不返回 XML 内容，也不保证缓存已被预热。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `SeoCacheResetResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 | 人类可读结果（本接口不返回新缓存内容） |
| success | boolean | 否 | 固定为 true |

响应示例：

```json
{
  "message": "Sitemap 缓存已清除，下次访问将重新生成",
  "success": true
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

---

## 高级管理（11）

缓存清理、系统维护等高级操作

### `GET /api/admin/logs`

- **摘要**：操作日志列表
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。分页读取操作日志，支持按用户、动作、资源类型、时间区间（from/to，仅给日期时 to 扩展到当天末尾）与关键词（匹配 detail / error_code / ip）过滤。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `OperationLogListResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 | 当前页日志，按创建时间倒序（最新在前） |
| page | integer | 是 | 当前页码（从 1 开始） |
| page_size | integer | 是 | 每页数量（上限 200） |
| total | integer | 是 | 符合筛选条件的总条数 |
| total_pages | integer | 是 | 总页数；total 为 0 时是 0 |

响应示例：

```json
{
  "items": [
    {
      "action": "string",
      "created_at": "string",
      "detail": "string",
      "id": 0,
      "ip_address": "string",
      "resource_id": "string",
      "resource_type": "string",
      "status": "string",
      "user": "string"
    }
  ],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/admin/logs/export`

- **摘要**：导出操作日志
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。按与列表接口相同的过滤条件导出**最多 1000 条**日志为文件下载（带 Content-Disposition: attachment）：``format=csv`` 回 text/csv（单元格已做公式注入防护），``format=json``（默认）回 application/json 数组。只读、无副作用。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "action": "string",
    "created_at": "string",
    "detail": "string",
    "id": 0,
    "ip_address": "string",
    "resource_id": "string",
    "resource_type": "string",
    "status": "string",
    "user": "string"
  }
]
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/posts/batch`

- **摘要**：批量操作文章
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。对多篇文章执行同一种动作，成功后失效 posts 列表与详情缓存。delete 为软删除（移入回收站，30 天后自动清除）；其余动作幂等。未选中任何文章返回 400，全部找不到返回 404。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `BatchActionRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| action | string | 是 |  |
| category_id | integer \| null | 否 |  |
| post_ids | integer[] | 是 |  |
| tag_ids | integer[] \| null | 否 |  |

```json
{
  "action": "string",
  "category_id": "string",
  "post_ids": [
    0
  ],
  "tag_ids": "string"
}
```

**出参**

`200` · 模型 `BatchActionResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| affected_count | integer | 是 | 状态真正发生变化的文章篇数（publish/draft 会跳过本就符合目标的记录） |
| message | string | 是 | 提示语，含实际处理篇数 |
| success | boolean | 是 | 固定为 true；失败走 4xx 错误信封 |

响应示例：

```json
{
  "affected_count": 0,
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `400` | 未选择文章 / 缺少 category_id 或 tag_ids / 不支持的 action |
| `404` | 未找到任何匹配的文章或目标分类 |
| `422` | Validation Error |

### `GET /api/admin/posts/{post_id}/revisions`

- **摘要**：文章修订历史
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。读取某篇文章的全部修订版本（不含正文，正文走单版本详情接口），按版本号倒序。版本在每次「改了标题/正文/摘要」的保存时自动生成，快照存的是改动前的状态；只改状态或重复保存同一份内容不会产版本。文章不存在返回 404。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `RevisionListResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| current_title | object \| string \| null | 否 | 文章当前标题（多语言字典），供前端对比各版本 |
| post_id | integer | 是 | 文章 ID |
| revisions | object[] | 是 | 修订版本列表，按 revision_number 倒序（最新在前） |
| total | integer | 是 | 版本条数（等于 revisions 长度） |

响应示例：

```json
{
  "current_title": "string",
  "post_id": 0,
  "revisions": [
    {
      "author": "string",
      "change_summary": "string",
      "created_at": "string",
      "id": 0,
      "revision_number": 0,
      "title": "string"
    }
  ],
  "total": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 文章不存在 |
| `422` | Validation Error |

### `GET /api/admin/posts/{post_id}/revisions/compare`

- **摘要**：比较修订版本
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。按 ``rev1`` / ``rev2`` 两个版本 ID 返回正文快照，由前端做 diff。任一 ID 不属于该文章（或只传到一个）时返回 404。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `RevisionCompareResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| revision1 | object | 是 | 版本比对里单侧的内容快照。 |
| revision1.content | object | 是 | 该版本正文（多语言字典，键为语言码；缺失时为空对象） |
| revision1.created_at | string \| null | 否 | 版本创建时间（ISO 8601） |
| revision1.id | integer | 是 | 修订版本 ID |
| revision1.revision_number | integer | 是 | 版本号 |
| revision2 | object | 是 | 版本比对里单侧的内容快照。 |
| revision2.content | object | 是 | 该版本正文（多语言字典，键为语言码；缺失时为空对象） |
| revision2.created_at | string \| null | 否 | 版本创建时间（ISO 8601） |
| revision2.id | integer | 是 | 修订版本 ID |
| revision2.revision_number | integer | 是 | 版本号 |

响应示例：

```json
{
  "revision1": {
    "content": {},
    "created_at": "string",
    "id": 0,
    "revision_number": 0
  },
  "revision2": {
    "content": {},
    "created_at": "string",
    "id": 0,
    "revision_number": 0
  }
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 找不到指定的修订版本 |
| `422` | Validation Error |

### `GET /api/admin/posts/{post_id}/revisions/{revision_id}`

- **摘要**：修订版本详情
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。返回指定修订版本的标题 / 正文 / 摘要全文，用于版本预览与恢复前确认。版本不存在或不属于该文章返回 404。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `RevisionDetailResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| change_summary | string \| null | 否 | 变更说明 |
| content | object \| string \| null | 否 | 该版本正文 |
| created_at | string \| null | 否 | 版本创建时间（ISO 8601） |
| excerpt | object \| string \| null | 否 | 该版本摘要；未设置时为 null |
| id | integer | 是 | 修订版本 ID |
| post_id | integer | 是 | 所属文章 ID |
| revision_number | integer | 是 | 版本号 |
| title | object \| string \| null | 否 | 该版本多语言标题 |

响应示例：

```json
{
  "change_summary": "string",
  "content": "string",
  "created_at": "string",
  "excerpt": "string",
  "id": 0,
  "post_id": 0,
  "revision_number": 0,
  "title": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 修订版本不存在 |
| `422` | Validation Error |

### `POST /api/admin/posts/{post_id}/revisions/{revision_id}/restore`

- **摘要**：恢复到指定版本
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。有副作用：先把文章当前内容另存为新版本（避免丢失），再用目标版本的 title/content/excerpt 覆盖文章，并重算阅读时长，最后失效该文章详情缓存与 posts 列表缓存。文章或版本不存在返回 404。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `SimpleActionResultResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 人类可读结果提示（如「项目已恢复」） |
| success | boolean | 是 | 固定为 true；失败走 4xx 错误信封 |

响应示例：

```json
{
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 文章不存在或修订版本不存在 |
| `422` | Validation Error |

### `GET /api/admin/trash`

- **摘要**：回收站列表
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。分页读取回收站记录，可按资源类型过滤，按入站时间倒序。只读、幂等；返回裸分页对象（无 success 信封）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `TrashListResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 | 当前页回收站记录，按创建时间倒序 |
| page | integer | 是 | 当前页码（从 1 开始） |
| page_size | integer | 是 | 每页数量 |
| total | integer | 是 | 符合筛选条件的总条数 |
| total_pages | integer | 是 | 总页数；total 为 0 时是 0 |

响应示例：

```json
{
  "items": [
    {
      "auto_delete_at": "string",
      "created_at": "string",
      "deleted_by": "string",
      "id": 0,
      "resource_data": {},
      "resource_id": 0,
      "resource_type": "string"
    }
  ],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/admin/trash`

- **摘要**：清空回收站
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。不可逆：逐条删除回收站记录（可限定资源类型，不传则清空全部），message 里回显实际清除条数。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `SimpleActionResultResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 人类可读结果提示（如「项目已恢复」） |
| success | boolean | 是 | 固定为 true；失败走 4xx 错误信封 |

响应示例：

```json
{
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/admin/trash/{trash_id}`

- **摘要**：永久删除
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。不可逆：删除回收站记录本体（原始资源在入站时已删除），并写入 permanent_delete 操作日志。记录不存在返回 404。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `SimpleActionResultResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 人类可读结果提示（如「项目已恢复」） |
| success | boolean | 是 | 固定为 true；失败走 4xx 错误信封 |

响应示例：

```json
{
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 回收站项目不存在 |
| `422` | Validation Error |

### `POST /api/admin/trash/{trash_id}/restore`

- **摘要**：恢复项目
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。按回收站记录重建原始资源（仅支持 post / comment）并删除该条记录，同时写入 restore 操作日志。非幂等：文章 slug 已被占用时返回 400，记录不存在返回 404。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `SimpleActionResultResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 人类可读结果提示（如「项目已恢复」） |
| success | boolean | 是 | 固定为 true；失败走 4xx 错误信封 |

响应示例：

```json
{
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `400` | 文章 slug 已被使用，无法恢复 |
| `404` | 回收站项目不存在 |
| `422` | Validation Error |

---

## 监控（8）

运行状态、访问日志、性能指标

### `GET /api/monitoring/cache`

- **摘要**：缓存监控
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。Redis 配置存在时实时 INFO 一次（键总量/命中率/内存占用/客户端数），探测失败回 connected=false 并附 error 文本；memory 后端只回三项占位 0。返回裸对象（无 success 信封）。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `CacheMonitorResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| connected | boolean | 是 | 是否连通；Redis 探测失败时置 false |
| error | string \| null | 否 | Redis 探测异常信息；正常时不返回该键 |
| metrics | object | 是 | 缓存指标。memory 后端固定为 total_keys / hit_rate / miss_rate 三个占位 0；Redis 后端额外含 used_memory_human、connected_clients、total_commands_processed，hit_rate … （完整说明见 `/docs`） |
| type | string | 是 | 缓存后端类型：redis 或 memory |

响应示例：

```json
{
  "connected": false,
  "error": "string",
  "metrics": {},
  "type": "string"
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/monitoring/database`

- **摘要**：数据库监控
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。读取 SQLAlchemy 连接池占用与 users/posts 两张表的行数。database_url 为运行时生效的连接串且凭据段已掩码，请勿在前端公开展示。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `DatabaseMonitorResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| database_url | string \| null | 否 | 生效的数据库连接串，凭据段已做掩码处理；无 URL 时为 null |
| pool | object | 是 | SQLAlchemy 连接池状态。 |
| pool.checked_in | integer | 是 | 空闲（已归还）连接数 |
| pool.checked_out | integer | 是 | 已被占用（借出）的连接数 |
| pool.overflow | integer | 是 | 超出 size 的临时连接数 |
| pool.size | integer | 是 | 池内连接数；池类型不支持该探针时为 0 |
| table_sizes | object<string, integer> | 是 | 按表名聚合的行数，当前键为 users 与 posts |

响应示例：

```json
{
  "database_url": "string",
  "pool": {
    "checked_in": 0,
    "checked_out": 0,
    "overflow": 0,
    "size": 0
  },
  "table_sizes": {}
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/monitoring/health`

- **摘要**：健康检查
- **鉴权**：公开接口（无需鉴权）

匿名可访问（OOBE 与负载均衡探针白名单）。对数据库与缓存各做一次真实探测，任一组件非 healthy 时整体降级为 degraded。只读、幂等，无副作用。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `HealthCheckResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| checks | object<string, object> | 是 | 按组件名聚合的探测结果，当前键为 database 与 cache |
| status | string | 是 | 整体状态：全部组件 healthy 才为 healthy，否则 degraded |
| timestamp | string | 是 | 服务端探测完成时间（ISO 8601，UTC） |

响应示例：

```json
{
  "checks": {},
  "status": "string",
  "timestamp": "string"
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/monitoring/performance`

- **摘要**：性能指标
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。统计**进程内内存环形缓冲**里最近 period 分钟（默认 60，上限 1440）的请求延迟分位数；缓冲不落盘，进程重启后清零，无样本时快速返回全 0（该分支不含 sample_count 键）。错误率另算：环形缓冲只记耗时不记状态码，无法判错，故 `error_rate` / `error_count` / `window_requests` 三个键取自 `visit_logs`（同一 period 窗口，`status_code >= 400` 计为错误，分母为窗口内全部日志条数），口径与 `/performance/summary` 一致，单位是百分数（13.29 即 13.29%）。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PerformanceLatencyResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| avg_latency | number | 是 | 平均延迟（毫秒） |
| error_rate | number | 是 | 错误率（当前实现固定回 0） |
| p50_latency | number | 是 | 中位延迟（毫秒） |
| p95_latency | number | 是 | P95 延迟（毫秒） |
| p99_latency | number | 是 | P99 延迟（毫秒） |
| requests_per_minute | number | 是 | 采样窗口内的每分钟平均请求数 |
| sample_count | integer \| null | 否 | 窗口内采样条数；无样本的快速分支不返回该键 |

响应示例：

```json
{
  "avg_latency": 0.0,
  "error_rate": 0.0,
  "p50_latency": 0.0,
  "p95_latency": 0.0,
  "p99_latency": 0.0,
  "requests_per_minute": 0.0,
  "sample_count": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/monitoring/performance/summary`

- **摘要**：性能概览
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。基于访问日志的 response_time_ms 计算 24 小时与 7 天窗口的均值与P50/P95/P99 分位数，并按 status_code >= 400 统计错误数与错误率。只统计耗时大于 0 的请求（取窗口内最近 50000 条样本），无数据时各分位回 0。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PerformanceSummaryResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| last_24h | object | 是 | 某个时间窗口的响应耗时统计（/performance/summary 的两段结构）。 |
| last_24h.avg_response_time_ms | number | 是 | 平均响应耗时（毫秒） |
| last_24h.error_count | integer | 是 | 状态码 >= 400 的请求条数（按窗口全量统计） |
| last_24h.error_rate | number | 是 | 错误率百分比（error_count / window_requests），保留两位小数 |
| last_24h.p50_response_time_ms | number | 是 | 中位数响应耗时（毫秒） |
| last_24h.p95_response_time_ms | number | 是 | P95 响应耗时（毫秒） |
| last_24h.p99_response_time_ms | number | 是 | P99 响应耗时（毫秒） |
| last_24h.total_requests | integer | 是 | 参与统计的请求条数（仅 response_time_ms > 0） |
| last_24h.window_requests | integer | 是 | 窗口内全部访问日志条数（error_rate 的分母，与 error_count 同口径） |
| last_7d | object | 是 | 某个时间窗口的响应耗时统计（/performance/summary 的两段结构）。 |
| last_7d.avg_response_time_ms | number | 是 | 平均响应耗时（毫秒） |
| last_7d.error_count | integer | 是 | 状态码 >= 400 的请求条数（按窗口全量统计） |
| last_7d.error_rate | number | 是 | 错误率百分比（error_count / window_requests），保留两位小数 |
| last_7d.p50_response_time_ms | number | 是 | 中位数响应耗时（毫秒） |
| last_7d.p95_response_time_ms | number | 是 | P95 响应耗时（毫秒） |
| last_7d.p99_response_time_ms | number | 是 | P99 响应耗时（毫秒） |
| last_7d.total_requests | integer | 是 | 参与统计的请求条数（仅 response_time_ms > 0） |
| last_7d.window_requests | integer | 是 | 窗口内全部访问日志条数（error_rate 的分母，与 error_count 同口径） |

响应示例：

```json
{
  "last_24h": {
    "avg_response_time_ms": 0.0,
    "error_count": 0,
    "error_rate": 0.0,
    "p50_response_time_ms": 0.0,
    "p95_response_time_ms": 0.0,
    "p99_response_time_ms": 0.0,
    "total_requests": 0,
    "window_requests": 0
  },
  "last_7d": {
    "avg_response_time_ms": 0.0,
    "error_count": 0,
    "error_rate": 0.0,
    "p50_response_time_ms": 0.0,
    "p95_response_time_ms": 0.0,
    "p99_response_time_ms": 0.0,
    "total_requests": 0,
    "window_requests": 0
  }
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/monitoring/stats`

- **摘要**：系统统计
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。聚合内容量、访问量、缓存后端、进程内存与 CPU 五类指标，供后台仪表盘首屏使用；psutil 缺失时内存/CPU 回 0 而不是报错。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `SystemStatsResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| cache | object | 是 | 缓存后端标识（/stats 的 cache 段）。 |
| cache.connected | boolean | 是 | 本字段为固定占位 true，真实可用性看 /cache 与 /health |
| cache.type | string | 是 | 缓存后端类型：redis 或 memory |
| cpu | object | 是 | CPU 指标（/stats 的 cpu 段）；psutil 不可用时保持默认值。 |
| cpu.count | integer \| null | 是 | 逻辑核心数，探测不到时为 null |
| cpu.percent | number | 是 | 瞬时 CPU 使用率百分比 |
| database | object | 是 | 内容量统计（/stats 的 database 段）。 |
| database.active_comments_count | integer | 是 | 已通过审核的评论数 |
| database.comments_count | integer | 是 | 评论总数 |
| database.posts_count | integer | 是 | 文章总数（含草稿） |
| database.published_posts_count | integer | 是 | 已发布文章数 |
| database.users_count | integer | 是 | 用户总数 |
| memory | object | 是 | 进程内存占用（/stats 的 memory 段）；psutil 不可用时全部为 0。 |
| memory.percent | number | 是 | 进程占系统内存百分比 |
| memory.rss_mb | number | 是 | 常驻内存（MB，保留两位小数） |
| memory.vms_mb | number | 是 | 虚拟内存（MB，保留两位小数） |
| requests | object | 是 | 请求量统计（/stats 的 requests 段）。 |
| requests.avg_latency_ms | number | 是 | 进程内缓冲区（最近一万条）的平均响应毫秒数，冷启动时为 0 |
| requests.today_requests | integer | 是 | 今日（UTC 零点起）访问条数 |
| requests.total_requests | integer | 是 | 访问日志累计条数 |
| timestamp | string | 是 | 统计生成时间（ISO 8601，UTC） |
| uptime_seconds | number | 是 | 进程启动至今的运行秒数 |
| visits | object | 是 | 访问计数（/stats 的 visits 段）。 |
| visits.today | integer | 是 | 今日（UTC 零点起）访问条数 |
| visits.total | integer | 是 | 访问日志累计条数 |

响应示例：

```json
{
  "cache": {
    "connected": false,
    "type": "string"
  },
  "cpu": {
    "count": "string",
    "percent": 0.0
  },
  "database": {
    "active_comments_count": 0,
    "comments_count": 0,
    "posts_count": 0,
    "published_posts_count": 0,
    "users_count": 0
  },
  "memory": {
    "percent": 0.0,
    "rss_mb": 0.0,
    "vms_mb": 0.0
  },
  "requests": {
    "avg_latency_ms": 0.0,
    "today_requests": 0,
    "total_requests": 0
  },
  "timestamp": "string",
  "uptime_seconds": 0.0,
  "visits": {
    "today": 0,
    "total": 0
  }
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/monitoring/trends`

- **摘要**：趋势数据
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。返回文章/评论/用户/访问四条按天分桶的折线，天数 1-30（默认 7）。每张表一条 GROUP BY 查询，缺失日期补 0，数组长度恒等于 days。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `TrendsResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| comments | object[] | 是 | 每日新增评论数 |
| posts | object[] | 是 | 每日新增文章数 |
| users | object[] | 是 | 每日新增用户数 |
| visits | object[] | 是 | 每日访问量 |

响应示例：

```json
{
  "comments": [
    {
      "count": 0,
      "date": "string"
    }
  ],
  "posts": [
    {
      "count": 0,
      "date": "string"
    }
  ],
  "users": [
    {
      "count": 0,
      "date": "string"
    }
  ],
  "visits": [
    {
      "count": 0,
      "date": "string"
    }
  ]
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/monitoring/visits/summary`

- **摘要**：访问量汇总
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。按今日/昨日/7 天/30 天窗口汇总访问日志条数，并给出最近 7 天逐日曲线与今日环比增长率。趋势用单条 GROUP BY 聚合，不按天循环查询。只读、幂等。响应另带 retention_days 与 data_since：日志受 LOG_RETENTION_DAYS 自动清理，保留窗口小于窗口天数时 week/month 只是下界，消费方据此标注口径。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `VisitsSummaryResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data_since | string \| null | 否 | visit_logs 现存最早一条的 UTC 时间（ISO 8601）；表为空时为 null。用于判断窗口是否被保留策略截短 |
| growth | number | 是 | 今日相对昨日的增长率百分比；昨日为 0 时回 0 |
| month | integer | 是 | 最近 30 天访问条数 |
| retention_days | integer | 是 | 日志自动保留窗口天数（LOG_RETENTION_DAYS）。<=0 表示不清理，week/month 恒为真实窗口；>0 且小于窗口天数时，对应计数只是下界 |
| today | integer | 是 | 今日（UTC 零点起）访问条数 |
| total | integer | 是 | 访问日志累计条数 |
| trend | object[] | 是 | 最近 7 天逐日访问曲线，固定 7 个点（含今天），缺失日补 0 |
| unique_ips_today | integer | 是 | 今日去重来源 IP 数（忽略 IP 为空的记录） |
| week | integer | 是 | 最近 7 天访问条数 |
| yesterday | integer | 是 | 昨日全天访问条数 |

响应示例：

```json
{
  "data_since": "string",
  "growth": 0.0,
  "month": 0,
  "retention_days": 0,
  "today": 0,
  "total": 0,
  "trend": [
    {
      "date": "string",
      "value": 0
    }
  ],
  "unique_ips_today": 0,
  "week": 0,
  "yesterday": 0
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

---

## TOC（3）

文章目录生成

### `POST /api/toc/add-ids`

- **摘要**：添加标题 ID
- **鉴权**：公开接口（无需鉴权）

为 Markdown 内容中的标题添加 ID 属性。公开接口、无需鉴权。逐行匹配 ATX 标题并改写为带 id 的原生 HTML 标题标签，锚点 id 的推导规则与标题提取接口一致，id 与文本都做 HTML 转义以防注入；非标题行与 max_depth 无关（本接口不截断层级）。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_add_heading_ids_api_toc_add_ids_post`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | string | 是 |  |

```json
{
  "content": "string"
}
```

**出参**

`200` · 模型 `TOCAddIdsResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | string | 是 | 改写后的整篇内容：行首的 Markdown 标题被替换成带 id 属性的原生 h1–h6 HTML 标签（文本与 id 均已 HTML 转义），其余行原样保留；没有标题时与入参完全相同 |

响应示例：

```json
{
  "content": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/toc/extract`

- **摘要**：提取标题
- **鉴权**：公开接口（无需鉴权）

从 Markdown 内容中提取所有标题。公开接口、无需鉴权，纯文本解析不落库。只认 ATX 形式（行首 1–6 个 # 加空格），max_depth 指定保留的最大层级（更深的标题整条丢弃）。返回的是按文中顺序排列的扁平列表，不构建树结构（要树请用本模块的目录生成接口）。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_extract_toc_api_toc_extract_post`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | string | 是 |  |
| max_depth | integer | 否 |  |

```json
{
  "content": "string",
  "max_depth": 3
}
```

**出参**

`200` · 模型 `TOCExtractResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| count | integer | 否 | 标题条数，等于 headings 长度 |
| headings | object[] | 否 | 按文中出现顺序排列的扁平标题列表，无命中时是空数组 |

响应示例：

```json
{
  "count": 0,
  "headings": [
    {
      "id": "string",
      "level": 0,
      "text": "string"
    }
  ]
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/toc/generate`

- **摘要**：生成目录
- **鉴权**：公开接口（无需鉴权）

从 Markdown 内容中生成文章目录。公开接口、无需鉴权。提取 ATX 标题（max_depth 控制保留层级）后按层级嵌套成树，并渲染成 toc-list 结构的无序列表 HTML；标题文本与锚点 id 均已 HTML 转义。无命中标题时 items 为空数组、html 为空字符串。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `TOCRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | string | 是 |  |
| max_depth | integer | 否 |  |

```json
{
  "content": "string",
  "max_depth": 3
}
```

**出参**

`200` · 模型 `TOCResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| html | string | 是 |  |
| items | object[] | 是 |  |

响应示例：

```json
{
  "html": "string",
  "items": [
    {
      "children": [],
      "id": "string",
      "level": 0,
      "text": "string"
    }
  ]
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 短代码（5）

内容短代码解析与预览

### `GET /api/admin/shortcodes`

- **摘要**：列出所有已注册短代码（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。返回本进程注册表内的所有短代码及元数据（``plugin`` = 归属插件 slug，``template`` = 可经本接口管理的模板）。列表前会先把 SiteConfig KV 里的模板重放进本进程注册表，因此多 worker 下也能看到其他进程刚注册的那条。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `ShortcodeListResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 |  |
| data.count | integer | 是 |  |
| data.items | object[] | 是 |  |
| data.persisted | integer | 是 | SiteConfig KV 中登记的模板短代码条数（跨 worker/重启的事实来源） |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "data": {
    "count": 0,
    "items": [
      {
        "description": "…",
        "has_paired": "…",
        "plugin": "…",
        "tag": "…",
        "template": "…"
      }
    ],
    "persisted": 0
  },
  "message": "操作成功",
  "success": true
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `POST /api/admin/shortcodes`

- **摘要**：预览短代码渲染结果（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

与公开渲染接口的差异是**唯一**能带 ``context`` 的入口：该字段会作为 ``ctx`` 传给每个 handler，供依赖文章/用户上下文的插件短代码在预览时取数。正文上限与公开接口一致（请求模型继承自公开请求，``context`` 为额外字段）。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `ShortcodePreviewRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | string | 是 | 包含短代码的原始内容文本 |
| context | object \| null | 否 | 渲染上下文，作为 ``ctx`` 关键字参数传给每个 handler。仅管理接口接受——公开渲染接口会忽略（且拒绝）该字段。 |

```json
{
  "content": "string",
  "context": "string"
}
```

**出参**

`200` · 模型 `ShortcodeRenderResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 渲染结果数据 |
| data.original_length | integer | 是 | 原始内容长度 |
| data.rendered | string | 是 | 经过短代码展开 + 安全清理后的 HTML |
| data.rendered_length | integer | 是 | 渲染结果长度 |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "data": {
    "original_length": 0,
    "rendered": "string",
    "rendered_length": 0
  },
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/shortcodes/register`

- **摘要**：注册简单模板式短代码（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

运行时注册一个基于 {replacement} 字符串模板的短代码，并写入 SiteConfig KV ``shortcode_templates``（多 worker 与重启后仍然生效）。模板中可用 ``{content}`` 表示成对短代码的内部内容，或用 ``{属性名}`` 引用调用时传入的属性；属性值与正文都只经过引擎的 handler 输出清洗。同名标签若已由插件注册则返回 409（``SHORTCODE_PLUGIN_OWNED``），不覆盖插件实现。注册成功后返回重放后的短代码列表，并失效已渲染内容缓存。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `ShortcodeRegisterRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| description | string \| null | 否 |  |
| replacement | string | 是 | 用于替换 [tag] 或 [tag /] 的固定 HTML 文本。使用 {content} 表示内部内容，{key} 表示属性。 |
| tag | string | 是 |  |

```json
{
  "description": "string",
  "replacement": "string",
  "tag": "string"
}
```

**出参**

`200` · 模型 `ShortcodeListResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 |  |
| data.count | integer | 是 |  |
| data.items | object[] | 是 |  |
| data.persisted | integer | 是 | SiteConfig KV 中登记的模板短代码条数（跨 worker/重启的事实来源） |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "data": {
    "count": 0,
    "items": [
      {
        "description": "…",
        "has_paired": "…",
        "plugin": "…",
        "tag": "…",
        "template": "…"
      }
    ],
    "persisted": 0
  },
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `409` | 同名短代码由插件注册，运行时接口不得覆盖（error_code: SHORTCODE_PLUGIN_OWNED） |
| `422` | Validation Error |

### `DELETE /api/admin/shortcodes/{tag}`

- **摘要**：注销运行时已注册的短代码（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

移除一个 API 注册的模板式短代码：同时摘除本进程注册表条目、SiteConfig KV 记录，并失效已渲染内容缓存。tag 不存在仍视为成功（幂等）。插件自带的同名短代码返回 409（``SHORTCODE_PLUGIN_OWNED``）——插件短代码跟着插件启停走，运行时注销后除了重启进程没有恢复路径。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `ShortcodeDeleteResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 否 |  |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "data": {},
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `409` | 该 tag 归属插件，须经插件停用移除（error_code: SHORTCODE_PLUGIN_OWNED） |
| `422` | Validation Error |

### `POST /api/shortcodes/render`

- **摘要**：渲染内容中的短代码
- **鉴权**：公开接口（无需鉴权）

输入任意文本，将 [tag]、[tag attr=val] 或 [tag]content[/tag] 等短代码展开为 HTML 后返回。清理口径：只注册过的短代码会被展开，未匹配的文本**原样返回**（不转义、不过滤），因此本接口不是 HTML 净化器；白名单 allowlist 只作用于 handler 的返回值。公开可访问但**不接受** ``context``（传了会被整体忽略，防止未鉴权调用方注入插件 handler 读取的渲染上下文）；需要上下文请用 ``POST /api/admin/shortcodes``。正文上限 200000 字符，同名嵌套超过引擎深度闸门后内层原样保留。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `ShortcodeRenderRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | string | 是 | 包含短代码的原始内容文本 |

```json
{
  "content": "string"
}
```

**出参**

`200` · 模型 `ShortcodeRenderResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 渲染结果数据 |
| data.original_length | integer | 是 | 原始内容长度 |
| data.rendered | string | 是 | 经过短代码展开 + 安全清理后的 HTML |
| data.rendered_length | integer | 是 | 渲染结果长度 |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "data": {
    "original_length": 0,
    "rendered": "string",
    "rendered_length": 0
  },
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 用户称号（9）

用户头衔与徽章管理

### `GET /api/admin/titles`

- **摘要**：称号列表
- **鉴权**：需鉴权：`HTTPBearer`

获取所有用户称号及其使用数量。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "color": "string",
    "created_at": "string",
    "description": "string",
    "icon": "string",
    "id": 0,
    "name": {},
    "users_count": 0
  }
]
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `POST /api/admin/titles`

- **摘要**：创建称号
- **鉴权**：需鉴权：`HTTPBearer`

创建新的用户称号，需要管理员权限。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `UserTitleCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| color | string | 否 | 显示颜色（十六进制，如 #3B82F6） |
| description | object<string, string> \| null | 否 | 称号描述（多语言） |
| icon | string \| null | 否 | 图标：预设 ID（star/crown/…）或 emoji，不接受 HTML/SVG 标记 |
| name | object<string, string> | 是 | 称号名称（多语言） |

```json
{
  "color": "#3B82F6",
  "description": "string",
  "icon": "string",
  "name": {}
}
```

**出参**

`200` · 模型 `backend__api__title__UserTitleResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| color | string | 是 |  |
| created_at | string | 是 |  |
| description | object<string, string> \| null | 否 |  |
| icon | string \| null | 否 |  |
| id | integer | 是 |  |
| name | object<string, string> | 是 |  |
| users_count | integer | 否 |  |

响应示例：

```json
{
  "color": "string",
  "created_at": "string",
  "description": "string",
  "icon": "string",
  "id": 0,
  "name": {},
  "users_count": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/titles/assign`

- **摘要**：分配称号
- **鉴权**：需鉴权：`HTTPBearer`

为用户。称号会被嵌进该用户文章的作者段与公开资料缓存，因此成功后自动失效其全部文章详情/列表缓存与用户资料缓存。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `UserTitleAssign`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| title_id | integer | 是 | 称号ID |
| user_id | integer | 是 | 用户ID |

```json
{
  "title_id": 0,
  "user_id": 0
}
```

**出参**

`200` · 模型 `TitleAssignResult`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 | 人类可读结果提示 |
| title_id | integer | 是 | 已分配的称号ID |
| user_id | integer | 是 | 被分配称号的用户ID |

响应示例：

```json
{
  "message": "称号分配成功",
  "title_id": 0,
  "user_id": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/admin/titles/{title_id}`

- **摘要**：称号详情
- **鉴权**：需鉴权：`HTTPBearer`

获取指定称号的详细信息。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `backend__api__title__UserTitleResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| color | string | 是 |  |
| created_at | string | 是 |  |
| description | object<string, string> \| null | 否 |  |
| icon | string \| null | 否 |  |
| id | integer | 是 |  |
| name | object<string, string> | 是 |  |
| users_count | integer | 否 |  |

响应示例：

```json
{
  "color": "string",
  "created_at": "string",
  "description": "string",
  "icon": "string",
  "id": 0,
  "name": {},
  "users_count": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/admin/titles/{title_id}`

- **摘要**：更新称号
- **鉴权**：需鉴权：`HTTPBearer`

信息，需要管理员权限。称号的 name/color/icon 会被嵌入文章详情与公开资料缓存，更新后自动失效全部持有者的相关缓存。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `UserTitleUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| color | string \| null | 否 | 显示颜色（十六进制）；省略该 key 表示不修改（列非空，不能置 null） |
| description | object<string, string> \| null | 否 | 称号描述（多语言） |
| icon | string \| null | 否 | 图标：预设 ID（star/crown/…）或 emoji，不接受 HTML/SVG 标记 |
| name | object<string, string> \| null | 否 | 称号名称（多语言） |

```json
{
  "color": "string",
  "description": "string",
  "icon": "string",
  "name": "string"
}
```

**出参**

`200` · 模型 `backend__api__title__UserTitleResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| color | string | 是 |  |
| created_at | string | 是 |  |
| description | object<string, string> \| null | 否 |  |
| icon | string \| null | 否 |  |
| id | integer | 是 |  |
| name | object<string, string> | 是 |  |
| users_count | integer | 否 |  |

响应示例：

```json
{
  "color": "string",
  "created_at": "string",
  "description": "string",
  "icon": "string",
  "id": 0,
  "name": {},
  "users_count": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PATCH /api/admin/titles/{title_id}`

- **摘要**：更新称号
- **鉴权**：需鉴权：`HTTPBearer`

信息，需要管理员权限。称号的 name/color/icon 会被嵌入文章详情与公开资料缓存，更新后自动失效全部持有者的相关缓存。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `UserTitleUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| color | string \| null | 否 | 显示颜色（十六进制）；省略该 key 表示不修改（列非空，不能置 null） |
| description | object<string, string> \| null | 否 | 称号描述（多语言） |
| icon | string \| null | 否 | 图标：预设 ID（star/crown/…）或 emoji，不接受 HTML/SVG 标记 |
| name | object<string, string> \| null | 否 | 称号名称（多语言） |

```json
{
  "color": "string",
  "description": "string",
  "icon": "string",
  "name": "string"
}
```

**出参**

`200` · 模型 `backend__api__title__UserTitleResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| color | string | 是 |  |
| created_at | string | 是 |  |
| description | object<string, string> \| null | 否 |  |
| icon | string \| null | 否 |  |
| id | integer | 是 |  |
| name | object<string, string> | 是 |  |
| users_count | integer | 否 |  |

响应示例：

```json
{
  "color": "string",
  "created_at": "string",
  "description": "string",
  "icon": "string",
  "id": 0,
  "name": {},
  "users_count": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/admin/titles/{title_id}`

- **摘要**：删除称号
- **鉴权**：需鉴权：`HTTPBearer`

，需要管理员权限。删除会同时摘除全部持有者，并失效其文章详情/列表与公开资料缓存，避免前台残留已删称号的徽章。

**入参**

_无路径 / query 参数_

**出参**

_未在 OpenAPI 中声明成功响应_

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/admin/users/{user_id}/title`

- **摘要**：获取用户称号
- **鉴权**：需鉴权：`HTTPBearer`

获取用户的当前称号。需登录（CurrentUser）。响应为裸 dict：user_id + title（头衔徽章投影，name/description 为多语言 dict，icon 为纯文本、color 为十六进制串）；用户无头衔时 title 为 null 而非缺键。用户不存在返回 404。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `UserTitleGetResultDoc`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| title | object \| null | 是 | 用户当前头衔徽章（id/name/color/icon/description）；用户尚未分配头衔时为 null（键仍在，不是缺字段） |
| user_id | integer | 是 | 查询的用户 ID（取自用户行，与路径参数一致） |

响应示例：

```json
{
  "title": "string",
  "user_id": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/admin/users/{user_id}/title`

- **摘要**：移除用户称号
- **鉴权**：需鉴权：`HTTPBearer`

移除用户的称号。同样会失效该用户的公开资料缓存与其全部文章详情/列表缓存，避免前台继续显示已撤销的徽章。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `TitleRemoveResult`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 | 人类可读结果提示 |
| user_id | integer | 是 | 被移除称号的用户ID |

响应示例：

```json
{
  "message": "称号已移除",
  "user_id": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 验证码（2）

图形验证码生成与校验

### `GET /api/captcha`

- **摘要**：获取验证码
- **鉴权**：公开接口（无需鉴权）

生成并返回一个图形验证码。公开接口、无需鉴权。code 是 4 位字符，字符集刻意排除易混淆的 0/O/1/I；image 字段是 data:image/png;base64 内联图，可直接塞进 img 标签。答案按 key 存进缓存，有效期 5 分钟，过期后校验会返回 400。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `CaptchaResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| image | string | 是 |  |
| key | string | 是 |  |

响应示例：

```json
{
  "image": "string",
  "key": "string"
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `POST /api/captcha/verify`

- **摘要**：验证验证码
- **鉴权**：公开接口（无需鉴权）

验证用户输入的验证码是否正确。公开接口、无需鉴权。比对不区分大小写。key 不存在或已过期返回 400（验证码已过期或不存在）。是一次性凭据：无论校验成功还是失败都会立即作废，失败即作废是为了挡住小字符集下的在线枚举，因此前端重试必须重新获取验证码。成功响应为裸 dict（success + message），无 data 信封。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `CaptchaVerifyRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | string | 是 |  |
| key | string | 是 |  |

```json
{
  "code": "string",
  "key": "string"
}
```

**出参**

`200` · 模型 `CaptchaVerifyResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 | 人类可读结果 |
| success | boolean | 否 | 固定为 true：不通过时本接口抛 400 而不返回 false |

响应示例：

```json
{
  "message": "验证成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 私信（6）

用户间私信收发

### `POST /api/messages`

- **摘要**：发送私信
- **鉴权**：需鉴权：`HTTPBearer`

向指定用户发送一条私信消息（需登录）。参数走 **JSON 请求体**：正文若走 query string 会整条落进 nginx 访问日志（``log_format`` 打的是完整请求行），5000 字上限还会顶破请求头缓冲直接 414/400。给自己发送时 400；接收者不存在时 404。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `MessageSendRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | string | 是 | 消息正文 |
| recipient_id | integer | 是 | 接收者用户 ID |

```json
{
  "content": "string",
  "recipient_id": 0
}
```

**出参**

`201` · 模型 `MessageSendOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | string | 是 | 消息内容 |
| created_at | string | 是 | 发送时间（ISO 8601 字符串） |
| id | integer | 是 | 新建消息 ID |
| recipient_id | integer | 是 | 接收者用户 ID |

响应示例：

```json
{
  "content": "string",
  "created_at": "string",
  "id": 0,
  "recipient_id": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/messages/conversations`

- **摘要**：获取会话列表
- **鉴权**：需鉴权：`HTTPBearer`

当前用户的私信会话，按最近消息时间倒序，**每个对端一行**。返回 ``{items, total, page, page_size, total_pages}``；``total`` 是会话总数（非本页条数），``items[].unread_count`` 只统计「对方发给我且未读」的消息。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `MessageConversationListOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 | 本页会话列表，按最近消息时间倒序 |
| page | integer | 是 | 当前页码，从 1 开始 |
| page_size | integer | 是 | 每页条数 |
| total | integer | 是 | 会话总数（对端数量，非本页条数） |
| total_pages | integer | 是 | 总页数，至少为 1 |

响应示例：

```json
{
  "items": [
    {
      "last_message": {
        "content": "…",
        "created_at": "…",
        "is_mine": "…"
      },
      "unread_count": 0,
      "user": {
        "avatar": "…",
        "id": "…",
        "nickname": "…",
        "username": "…"
      }
    }
  ],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/messages/read-all/{user_id}`

- **摘要**：标记某会话全部已读
- **鉴权**：需鉴权：`HTTPBearer`

将与指定用户的所有私信标记为已读（需登录，仅标记对方发给当前用户的未读消息）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `MessageSuccessOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| success | boolean | 否 | 操作是否成功 |

响应示例：

```json
{
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/messages/unread/count`

- **摘要**：获取未读消息数
- **鉴权**：需鉴权：`HTTPBearer`

返回当前用户所有未读私信的总数（需登录，用于角标轮询）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `MessageUnreadCountOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| count | integer | 是 | 当前用户收到的全部未读私信条数 |

响应示例：

```json
{
  "count": 0
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `PUT /api/messages/{message_id}/read`

- **摘要**：标记单条消息已读
- **鉴权**：需鉴权：`HTTPBearer`

将指定私信标记为已读（需登录）。消息不存在**或不属于当前用户**时一律 404——私信 id 是连续自增的，用 403 区分「存在但非你的」等于把别人的私信存在性摊给攻击者（收藏、通知同族同为 404）。成功后该会话/全局未读数相应减少。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `MessageSuccessOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| success | boolean | 否 | 操作是否成功 |

响应示例：

```json
{
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/messages/{user_id}`

- **摘要**：获取与某用户的会话
- **鉴权**：需鉴权：`HTTPBearer`

获取当前用户与指定用户之间的私信记录，支持分页（需登录）。**副作用**：读取时会把该用户发给当前用户的未读消息全部标记为已读。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `MessageConversationDetailOut`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 | 本页消息列表，按时间正序 |
| other_user | object | 是 | 会话对端用户的公开资料 |
| other_user.avatar | string \| null | 否 | 头像 URL，未设置时为 null |
| other_user.id | integer | 是 | 对端用户 ID |
| other_user.nickname | string \| null | 否 | 昵称，未设置时为 null |
| other_user.username | string | 是 | 用户名 |
| page | integer | 是 | 当前页码，从 1 开始 |
| page_size | integer | 是 | 每页条数 |
| total | integer | 是 | 双方消息总数（非本页条数） |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [
    {
      "content": "string",
      "created_at": "string",
      "id": 0,
      "is_mine": false,
      "is_read": false
    }
  ],
  "other_user": {
    "avatar": "string",
    "id": 0,
    "nickname": "string",
    "username": "string"
  },
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 翻译（1）

多语言内容翻译接口

### `POST /api/translate`

- **摘要**：翻译文本
- **鉴权**：需鉴权：`HTTPBearer`

到多种语言 支持的语言： - zh: 简体中文 - en: English - ja: 日本語 - zh_Hant: 繁體中文 需要登录用户权限。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `TranslateRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| source_lang | string | 否 | 源语言 |
| target_langs | string[] | 否 | 目标语言列表 |
| text | string | 是 | 待翻译文本 |

```json
{
  "source_lang": "zh",
  "target_langs": [
    "en",
    "ja",
    "zh_Hant"
  ],
  "text": "string"
}
```

**出参**

`200` · 模型 `TranslateResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| translations | object<string, string> | 否 | 翻译结果 |

响应示例：

```json
{
  "translations": {}
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## OOBE（18）

开箱即用安装向导（首次部署时使用）

### `POST /api/oobe/admin-account`

- **摘要**：保存管理员账户信息（已废弃）
- **鉴权**：公开接口（无需鉴权）

**Deprecated**：旧分步式接口，请改用 POST /oobe/install。仅 OOBE 未完成时可用。把管理员资料草稿写进向导 state 文件，**此步骤不创建任何用户、不校验邮箱是否已注册**；用户名长度/字符集或密码长度不合规返回 400。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `AdminAccountRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| email | string | 是 |  |
| nickname | string | 否 |  |
| password | string | 是 |  |
| username | string | 是 |  |

```json
{
  "email": "string",
  "nickname": "",
  "password": "string",
  "username": "string"
}
```

**出参**

`200` · 模型 `OobeSimpleSuccessResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| success | boolean | 是 | 固定为 true；校验失败走 4xx/5xx 错误信封 |

响应示例：

```json
{
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `400` | 用户名不合规或密码过短 |
| `422` | Validation Error |
| `503` | OOBE 已完成（error_code: OOBE_REQUIRED） |

### `GET /api/oobe/check`

- **摘要**：环境检测
- **鉴权**：公开接口（无需鉴权）

匿名可访问（OOBE 白名单）。逐项探测 Python / uv / node / pnpm 版本、数据库与 Redis 连通性、磁盘与内存余量。**单项失败不影响整体 HTTP 200**，前端按项渲染红绿灯。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `OobeCheckResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| database_connectivity | object | 是 | 环境检测单项结果（``_ok()`` 的字段形态）。 |
| database_connectivity.error | string \| null | 否 | 失败原因或告警提示；通过时为 null |
| database_connectivity.ok | boolean | 是 | 该项是否通过（可选组件失败也可能为 true） |
| database_connectivity.value | object | 否 | 探测值，类型随项而定：版本号字符串 / 布尔连通性 / 数值（GB 或 MB）；探测失败为 null |
| disk_free_gb | object | 是 | 磁盘可用空间检测项（附带总量与使用率）。 |
| disk_free_gb.display | string | 是 | 供向导直接渲染的一行摘要文案 |
| disk_free_gb.error | string \| null | 否 | 失败原因或告警提示；通过时为 null |
| disk_free_gb.ok | boolean | 是 | 该项是否通过（可选组件失败也可能为 true） |
| disk_free_gb.os_summary | string | 是 | 系统概览文案（系统名 · 架构 · 核数） |
| disk_free_gb.path | string | 是 | 被探测的卷路径 |
| disk_free_gb.total_gb | integer | 是 | 卷总容量（GB） |
| disk_free_gb.usage_pct | integer | 是 | 使用率百分比 |
| disk_free_gb.used_gb | integer | 是 | 已用容量（GB） |
| disk_free_gb.value | object | 否 | 探测值，类型随项而定：版本号字符串 / 布尔连通性 / 数值（GB 或 MB）；探测失败为 null |
| memory_free_mb | object | 是 | 可用内存检测项（附带总量、使用率与 CPU 概览）。 |
| memory_free_mb.arch | string | 是 | CPU 架构标识，如 AMD64 / x86_64 |
| memory_free_mb.avail_gb | number | 是 | 可用内存（GB，保留一位小数） |
| memory_free_mb.cpu_count | integer | 是 | 逻辑 CPU 核数 |
| memory_free_mb.cpu_name | string | 是 | CPU 型号名称，探测不到时为空串 |
| memory_free_mb.display | string | 是 | 供向导直接渲染的一行摘要文案 |
| memory_free_mb.error | string \| null | 否 | 失败原因或告警提示；通过时为 null |
| memory_free_mb.ok | boolean | 是 | 该项是否通过（可选组件失败也可能为 true） |
| memory_free_mb.os_summary | string | 是 | 系统概览文案 |
| memory_free_mb.total_gb | number | 是 | 内存总量（GB，保留一位小数） |
| memory_free_mb.total_mb | integer | 是 | 物理内存总量（MB） |
| memory_free_mb.usage_pct | integer | 是 | 内存使用率百分比 |
| memory_free_mb.used_gb | number | 是 | 已用内存（GB，保留一位小数） |
| memory_free_mb.used_mb | integer | 是 | 已用内存（MB） |
| memory_free_mb.value | object | 否 | 探测值，类型随项而定：版本号字符串 / 布尔连通性 / 数值（GB 或 MB）；探测失败为 null |
| node_version | object | 是 | 环境检测单项结果（``_ok()`` 的字段形态）。 |
| node_version.error | string \| null | 否 | 失败原因或告警提示；通过时为 null |
| node_version.ok | boolean | 是 | 该项是否通过（可选组件失败也可能为 true） |
| node_version.value | object | 否 | 探测值，类型随项而定：版本号字符串 / 布尔连通性 / 数值（GB 或 MB）；探测失败为 null |
| pnpm_version | object | 是 | 环境检测单项结果（``_ok()`` 的字段形态）。 |
| pnpm_version.error | string \| null | 否 | 失败原因或告警提示；通过时为 null |
| pnpm_version.ok | boolean | 是 | 该项是否通过（可选组件失败也可能为 true） |
| pnpm_version.value | object | 否 | 探测值，类型随项而定：版本号字符串 / 布尔连通性 / 数值（GB 或 MB）；探测失败为 null |
| python_version | object | 是 | 环境检测单项结果（``_ok()`` 的字段形态）。 |
| python_version.error | string \| null | 否 | 失败原因或告警提示；通过时为 null |
| python_version.ok | boolean | 是 | 该项是否通过（可选组件失败也可能为 true） |
| … 其余 15 个字段 | | | 见 `/docs` |

响应示例：

```json
{
  "database_connectivity": {
    "error": "string",
    "ok": false,
    "value": "string"
  },
  "disk_free_gb": {
    "display": "string",
    "error": "string",
    "ok": false,
    "os_summary": "string",
    "path": "string",
    "total_gb": 0,
    "usage_pct": 0,
    "used_gb": 0,
    "value": "string"
  },
  "memory_free_mb": {
    "arch": "string",
    "avail_gb": 0.0,
    "cpu_count": 0,
    "cpu_name": "string",
    "display": "string",
    "error": "string",
    "ok": false,
    "os_summary": "string",
    "total_gb": 0.0,
    "total_mb": 0,
    "usage_pct": 0,
    "used_gb": 0.0,
    "used_mb": 0,
    "value": "string"
  },
  "node_version": {
    "error": "string",
    "ok": false,
    "value": "string"
  },
  "pnpm_version": {
    "error": "string",
    "ok": false,
    "value": "string"
  },
  "python_version": {
    "error": "string",
    "ok": false,
    "value": "string"
  },
  "redis_connectivity": {
    "error": "string",
    "ok": false,
    "value": "string"
  },
  "success": false,
  "uv_installed": {
    "error": "string",
    "ok": false,
    "uv_version": "string",
    "value": false
  },
  "uv_version": {
    "error": "string",
    "ok": false,
    "value": "string"
  }
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/oobe/check-username`

- **摘要**：检查用户名是否可用
- **鉴权**：公开接口（无需鉴权）

匿名可访问（OOBE 白名单）。只校验长度与字符集（字母数字，允许下划线/连字符），不查库、不建账号，因此**不保证最终唯一性**。返回裸对象（无 success 信封）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `OobeUsernameCheckResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| available | boolean | 是 | 用户名是否可用（长度与字符集校验通过即 true） |
| message | string \| null | 否 | 不可用原因（四语文案）；可用时不返回该键 |

响应示例：

```json
{
  "available": false,
  "message": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/oobe/database-config`

- **摘要**：保存数据库配置（已废弃）
- **鉴权**：公开接口（无需鉴权）

**Deprecated**：旧分步式接口，请改用 POST /oobe/install。仅 OOBE 未完成时可用。把数据库/Redis 配置草稿写入向导 state 文件（不落库、不建连接）；响应回显时**剔除所有密码字段**。非 sqlite 且缺 db_user、或 db_name 为空时返回 400。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `DatabaseConfigRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| db_host | string | 否 |  |
| db_name | string | 否 |  |
| db_password | string | 否 |  |
| db_path | string | 否 |  |
| db_port | integer | 否 |  |
| db_type | string | 否 |  |
| db_user | string | 否 |  |
| redis_enabled | boolean | 否 |  |
| redis_host | string | 否 |  |
| redis_password | string | 否 |  |
| redis_port | integer | 否 |  |

```json
{
  "db_host": "localhost",
  "db_name": "rosetta",
  "db_password": "",
  "db_path": "rosetta.db",
  "db_port": 5432,
  "db_type": "sqlite",
  "db_user": "",
  "redis_enabled": false,
  "redis_host": "localhost",
  "redis_password": "",
  "redis_port": 6379
}
```

**出参**

`200` · 模型 `OobeDatabaseConfigResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| config | object | 是 | 已保存的数据库/Redis 配置草稿回显，**密码类键（db_password、redis_password）已被剔除**，不随响应外泄 |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "config": {},
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `400` | 数据库用户名或库名缺失 |
| `422` | Validation Error |
| `503` | OOBE 已完成（error_code: OOBE_REQUIRED） |

### `GET /api/oobe/dependencies`

- **摘要**：检查系统依赖
- **鉴权**：公开接口（无需鉴权）

匿名可访问（OOBE 白名单）。逐项检测 python / uv / node / pnpm / postgresql / redis / npm / pip / sqlite 是否可用及版本；有副作用：检测后会刷新进程 PATH（``_refresh_path``），让刚安装的工具立即可见。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `OobeDependenciesResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| node | object | 是 | 单个依赖/工具链的可用性条目。 |
| node.available | boolean | 是 | 是否已安装（INSTALLED / COMPATIBLE 视为可用） |
| node.message | string | 是 | 展示文案，如「已安装」「未检测到」「npm x.y 已安装」 |
| node.required | string | 是 | 要求版本；npm/pip/sqlite 等项不校验，恒为空串 |
| node.version | string | 是 | 当前版本串；探测不到时为空串 |
| npm | object | 是 | 单个依赖/工具链的可用性条目。 |
| npm.available | boolean | 是 | 是否已安装（INSTALLED / COMPATIBLE 视为可用） |
| npm.message | string | 是 | 展示文案，如「已安装」「未检测到」「npm x.y 已安装」 |
| npm.required | string | 是 | 要求版本；npm/pip/sqlite 等项不校验，恒为空串 |
| npm.version | string | 是 | 当前版本串；探测不到时为空串 |
| pip | object | 是 | 单个依赖/工具链的可用性条目。 |
| pip.available | boolean | 是 | 是否已安装（INSTALLED / COMPATIBLE 视为可用） |
| pip.message | string | 是 | 展示文案，如「已安装」「未检测到」「npm x.y 已安装」 |
| pip.required | string | 是 | 要求版本；npm/pip/sqlite 等项不校验，恒为空串 |
| pip.version | string | 是 | 当前版本串；探测不到时为空串 |
| pnpm | object | 是 | 单个依赖/工具链的可用性条目。 |
| pnpm.available | boolean | 是 | 是否已安装（INSTALLED / COMPATIBLE 视为可用） |
| pnpm.message | string | 是 | 展示文案，如「已安装」「未检测到」「npm x.y 已安装」 |
| pnpm.required | string | 是 | 要求版本；npm/pip/sqlite 等项不校验，恒为空串 |
| pnpm.version | string | 是 | 当前版本串；探测不到时为空串 |
| postgresql | object | 是 | 单个依赖/工具链的可用性条目。 |
| postgresql.available | boolean | 是 | 是否已安装（INSTALLED / COMPATIBLE 视为可用） |
| postgresql.message | string | 是 | 展示文案，如「已安装」「未检测到」「npm x.y 已安装」 |
| postgresql.required | string | 是 | 要求版本；npm/pip/sqlite 等项不校验，恒为空串 |
| postgresql.version | string | 是 | 当前版本串；探测不到时为空串 |
| python | object | 是 | 单个依赖/工具链的可用性条目。 |
| python.available | boolean | 是 | 是否已安装（INSTALLED / COMPATIBLE 视为可用） |
| python.message | string | 是 | 展示文案，如「已安装」「未检测到」「npm x.y 已安装」 |
| python.required | string | 是 | 要求版本；npm/pip/sqlite 等项不校验，恒为空串 |
| python.version | string | 是 | 当前版本串；探测不到时为空串 |
| redis | object | 是 | 单个依赖/工具链的可用性条目。 |
| redis.available | boolean | 是 | 是否已安装（INSTALLED / COMPATIBLE 视为可用） |
| redis.message | string | 是 | 展示文案，如「已安装」「未检测到」「npm x.y 已安装」 |
| redis.required | string | 是 | 要求版本；npm/pip/sqlite 等项不校验，恒为空串 |
| redis.version | string | 是 | 当前版本串；探测不到时为空串 |
| sqlite | object | 是 | 单个依赖/工具链的可用性条目。 |
| sqlite.available | boolean | 是 | 是否已安装（INSTALLED / COMPATIBLE 视为可用） |
| sqlite.message | string | 是 | 展示文案，如「已安装」「未检测到」「npm x.y 已安装」 |
| sqlite.required | string | 是 | 要求版本；npm/pip/sqlite 等项不校验，恒为空串 |
| sqlite.version | string | 是 | 当前版本串；探测不到时为空串 |
| … 其余 6 个字段 | | | 见 `/docs` |

响应示例：

```json
{
  "node": {
    "available": false,
    "message": "string",
    "required": "string",
    "version": "string"
  },
  "npm": {
    "available": false,
    "message": "string",
    "required": "string",
    "version": "string"
  },
  "pip": {
    "available": false,
    "message": "string",
    "required": "string",
    "version": "string"
  },
  "pnpm": {
    "available": false,
    "message": "string",
    "required": "string",
    "version": "string"
  },
  "postgresql": {
    "available": false,
    "message": "string",
    "required": "string",
    "version": "string"
  },
  "python": {
    "available": false,
    "message": "string",
    "required": "string",
    "version": "string"
  },
  "redis": {
    "available": false,
    "message": "string",
    "required": "string",
    "version": "string"
  },
  "sqlite": {
    "available": false,
    "message": "string",
    "required": "string",
    "version": "string"
  },
  "success": false,
  "uv": {
    "available": false,
    "message": "string",
    "required": "string",
    "version": "string"
  }
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `POST /api/oobe/environment`

- **摘要**：保存环境选择（已废弃）
- **鉴权**：公开接口（无需鉴权）

**Deprecated**：旧分步式接口，仅为兼容保留，请改用 POST /oobe/install 一键安装。仅 OOBE 未完成时可用；把 environment 写进向导 state（development 会连带把库类型定为 sqlite、production 定为 postgresql）。非法取值返回 400。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `OobeEnvironmentResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| environment | string | 是 | 已写入状态的运行环境：development 或 production |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "environment": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `400` | environment 不是 development / production |
| `422` | Validation Error |
| `503` | OOBE 已完成（error_code: OOBE_REQUIRED） |

### `POST /api/oobe/install`

- **摘要**：OOBE 一键安装
- **鉴权**：公开接口（无需鉴权）

唯一的安装入口（匿名可访问，但仅 OOBE 未完成时可用）。**危险且不可逆的副作用**：写 .env 与配置文件、重建数据库引擎并建表、创建超级管理员、写入站点设置与示例数据/页面/导航，最后落 OOBE 完成锁。三层幂等防线（入口检查 + 进程内 asyncio.Lock + 拿锁后二次检查），已完成返回 409 + ``OOBE_ALREADY_COMPLETED``，密码过短回 422，其余异常回 500。实时进度走 GET /oobe/install/stream。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `CombinedInstallRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| admin_avatar_source | string | 否 |  |
| admin_bio | string | 否 |  |
| admin_email | string | 是 |  |
| admin_github | string | 否 |  |
| admin_nickname | string | 否 |  |
| admin_password | string | 是 |  |
| admin_qq | string | 否 |  |
| admin_username | string | 是 |  |
| admin_website | string | 否 |  |
| database_type | enum(`sqlite`, `postgresql`) | 否 |  |
| db_host | string | 否 |  |
| db_name | string | 否 |  |
| db_password | string | 否 |  |
| db_path | string | 否 |  |
| db_port | integer | 否 |  |
| db_user | string | 否 |  |
| enable_bing_wallpaper | boolean | 否 |  |
| enable_comments | boolean | 否 |  |
| enable_encrypted_posts | boolean | 否 |  |
| enable_music_player | boolean | 否 |  |
| enable_pagefind_search | boolean | 否 |  |
| enable_registration | boolean | 否 |  |
| enable_rss | boolean | 否 |  |
| environment | enum(`development`, `production`) | 否 |  |
| redis_enabled | boolean | 否 |  |
| redis_host | string | 否 |  |
| redis_password | string | 否 |  |
| redis_port | integer | 否 |  |
| site_author | string | 否 |  |
| site_description | string | 否 |  |
| site_email | string | 否 |  |
| site_keywords | string | 否 |  |
| site_name | string | 否 |  |
| site_url | string | 是 | 站点对外访问地址（用于拼接绝对 URL） |

```json
{
  "admin_avatar_source": "auto",
  "admin_bio": "",
  "admin_email": "string",
  "admin_github": "",
  "admin_nickname": "",
  "admin_password": "string",
  "admin_qq": "",
  "admin_username": "string",
  "admin_website": "",
  "database_type": "sqlite",
  "db_host": "localhost",
  "db_name": "rosetta",
  "db_password": "",
  "db_path": "rosetta.db",
  "db_port": 5432,
  "db_user": "",
  "enable_bing_wallpaper": true,
  "enable_comments": true,
  "enable_encrypted_posts": false,
  "enable_music_player": true,
  "enable_pagefind_search": true,
  "enable_registration": true,
  "enable_rss": true,
  "environment": "production",
  "redis_enabled": false,
  "redis_host": "localhost",
  "redis_password": "",
  "redis_port": 6379,
  "site_author": "",
  "site_description": "一个功能齐全、主题优雅、开箱即用的现代博客引擎",
  "site_email": "",
  "site_keywords": "",
  "site_name": "Rosetta",
  "site_url": "string"
}
```

**出参**

`200` · 模型 `OobeInstallResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| admin_url | string | 是 | 后台入口地址（前台 URL 追加 /admin） |
| frontend_url | string | 是 | 站点前台地址（取自提交的站点 URL） |
| success | boolean | 是 | 固定为 true；失败走 4xx/5xx 错误信封 |

响应示例：

```json
{
  "admin_url": "string",
  "frontend_url": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `409` | OOBE 已完成（error_code: OOBE_ALREADY_COMPLETED） |
| `422` | Validation Error |

### `POST /api/oobe/install-dependencies`

- **摘要**：一键安装缺失依赖
- **鉴权**：公开接口（无需鉴权）

匿名可访问，但**仅 OOBE 未完成时可调用**，完成后返回 ``503 OOBE_REQUIRED``。**高危副作用**：在服务器上执行 uv / npm / pip 等安装命令（工具链 + 后端 + 前端依赖），耗时较长；实时日志走 GET /oobe/install-dependencies/stream。响应里的 ``success`` 键是安装成功项计数而非布尔值，判断整体结果请看 ``all_success``。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `OobeInstallDependenciesResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| all_success | boolean | 是 | 是否零失败 |
| failed | integer | 是 | 失败项数 |
| logs | object[] | 是 | 安装期日志条目（命令输出等） |
| results | object<string, object> | 是 | 按依赖名聚合的逐项安装结果 |
| skipped | integer | 是 | 跳过项数（已满足要求） |
| success | integer \| boolean | 是 | 注意：该键被展开的安装摘要覆盖，实际含义是**安装成功项计数**（int），不是布尔成功标记；判断整体是否全绿请看 all_success |
| total | integer | 是 | 参与安装的依赖项总数 |

响应示例：

```json
{
  "all_success": false,
  "failed": 0,
  "logs": [
    {}
  ],
  "results": {},
  "skipped": 0,
  "success": "string",
  "total": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `503` | OOBE 已完成（error_code: OOBE_REQUIRED） |

### `GET /api/oobe/install-dependencies/stream`

- **摘要**：依赖安装进度 SSE 流
- **鉴权**：公开接口（无需鉴权）

与 POST /oobe/install-dependencies 配对：点击「一键安装」后连接本端点，实时接收 ``connected`` 握手、逐依赖进度、命令行日志与 ``done`` 汇总。**仅安装未完成（OOBE 锁存在）时可访问**：缓冲内含 pip/npm 命令输出，OOBE 完成后返回 ``503 OOBE_REQUIRED``；空闲约 10 分钟无事件自动关闭。事件载荷为 SSE 文本帧（type: connected / progress / log / done），不是 JSON 响应体。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |
| `503` | OOBE 已完成（error_code: OOBE_REQUIRED） |

### `GET /api/oobe/install/stream`

- **摘要**：一键安装进度 SSE 流
- **鉴权**：公开接口（无需鉴权）

客户端在发起 POST /oobe/install 前后连接，通过 ``sid`` 订阅安装进度事件。**仅安装未完成（OOBE 锁存在）时可访问**；空闲约 10 分钟无事件自动关闭。事件载荷为 SSE 文本帧（type: connected / progress / done / error），不是 JSON 响应体；``done`` 帧里的 frontend_url / admin_url 由向导消费，改字段需同步 useOOBE。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |
| `503` | OOBE 已完成（error_code: OOBE_REQUIRED） |

### `POST /api/oobe/preflight`

- **摘要**：安装前干跑校验
- **鉴权**：公开接口（无需鉴权）

匿名可访问（OOBE 白名单），**只读、不写任何文件、不建库、不建账号**。把向导里已填的内容提交上来做一次体检：用户名/邮箱/密码强度/站点地址走表单校验，数据库（postgresql 时）走真实连接探测并给出结构化错误码。**所有字段可选**，只校验提交上来的那部分——因此可分别在管理员步骤和站点步骤调用，点安装前再带全量跑一次。返回的 `issues[].code` 是稳定标识，前端按 code 分支渲染，不要匹配 `message` 文案（文案会随 i18n 变）。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `OobePreflightRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| admin_email | string \| null | 否 |  |
| admin_password | string \| null | 否 |  |
| admin_username | string \| null | 否 |  |
| check_database | boolean | 否 |  |
| database_type | enum(`sqlite`, `postgresql`) | 否 |  |
| db_host | string | 否 |  |
| db_name | string | 否 |  |
| db_password | string | 否 |  |
| db_path | string | 否 |  |
| db_port | integer | 否 |  |
| db_user | string | 否 |  |
| site_name | string \| null | 否 |  |
| site_url | string \| null | 否 |  |

```json
{
  "admin_email": "string",
  "admin_password": "string",
  "admin_username": "string",
  "check_database": true,
  "database_type": "sqlite",
  "db_host": "localhost",
  "db_name": "rosetta",
  "db_password": "",
  "db_path": "rosetta.db",
  "db_port": 5432,
  "db_user": "",
  "site_name": "string",
  "site_url": "string"
}
```

**出参**

`200` · 模型 `OobePreflightResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| database | object | 是 | 预检里的数据库体检结果。 |
| database.checked | boolean | 是 | 是否真的做了连接探测 |
| database.code | string | 是 | 结构化错误码（DB_* 系列） |
| database.hint | string \| null | 否 | 可操作的下一步建议 |
| database.message | string | 是 | 人读结论 |
| database.ok | boolean | 是 | 是否可继续安装（库不存在但账号能建库时仍为 true） |
| database.version | string \| null | 否 | 探测到的 PostgreSQL 版本串 |
| issues | object[] | 是 | 问题清单；全绿时为空数组 |
| ok | boolean | 是 | 是否没有任何 error 级问题（warn 不影响） |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "database": {
    "checked": false,
    "code": "string",
    "hint": "string",
    "message": "string",
    "ok": false,
    "version": "string"
  },
  "issues": [
    {
      "code": "string",
      "field": "string",
      "hint": "string",
      "level": "error",
      "message": "string"
    }
  ],
  "ok": false,
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/oobe/reset`

- **摘要**：重置 OOBE 状态
- **鉴权**：需鉴权：`HTTPBearer`

**危险操作**：删除安装锁、.env、配置文件与向导 state，使站点回到未安装态（其余接口立即 503）。站点已安装时必须携带超级管理员凭证，否则 403；尚未安装时开放。任一文件删除失败回 500 并在 detail 列明残留项，不会返回半成功状态。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `OobeSimpleSuccessResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| success | boolean | 是 | 固定为 true；校验失败走 4xx/5xx 错误信封 |

响应示例：

```json
{
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `403` | 站点已安装，需要超级管理员权限 |
| `500` | 部分文件无法删除（detail 列出残留项） |

### `POST /api/oobe/site-config`

- **摘要**：保存站点配置（已废弃）
- **鉴权**：公开接口（无需鉴权）

**Deprecated**：旧分步式接口，请改用 POST /oobe/install。仅 OOBE 未完成时可用。把站点名称/描述/社交链接/页脚与评论、注册、RSS 开关写进向导 state 文件，不落库。site_name 或 site_email 为空时返回 400。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `SiteConfigRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| bilibili_url | string | 否 |  |
| default_cover_image | string | 否 |  |
| enable_comments | boolean | 否 |  |
| enable_registration | boolean | 否 |  |
| enable_rss | boolean | 否 |  |
| footer_text | string | 否 |  |
| github_url | string | 否 |  |
| site_author | string | 否 |  |
| site_description | string | 否 |  |
| site_email | string | 否 |  |
| site_keywords | string | 否 |  |
| site_name | string | 否 |  |
| site_title | string | 否 |  |
| site_url | string | 否 |  |
| x_url | string | 否 |  |

```json
{
  "bilibili_url": "",
  "default_cover_image": "",
  "enable_comments": true,
  "enable_registration": true,
  "enable_rss": true,
  "footer_text": "",
  "github_url": "",
  "site_author": "",
  "site_description": "",
  "site_email": "",
  "site_keywords": "",
  "site_name": "Rosetta",
  "site_title": "",
  "site_url": "http://localhost:4321",
  "x_url": ""
}
```

**出参**

`200` · 模型 `OobeSimpleSuccessResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| success | boolean | 是 | 固定为 true；校验失败走 4xx/5xx 错误信封 |

响应示例：

```json
{
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `400` | 站点名称或联系邮箱为空 |
| `422` | Validation Error |
| `503` | OOBE 已完成（error_code: OOBE_REQUIRED） |

### `GET /api/oobe/state`

- **摘要**：获取向导断点状态
- **鉴权**：公开接口（无需鉴权）

匿名可访问，但**仅 OOBE 未完成时可用**（require_oobe_incomplete），安装完成后返回 ``503 OOBE_REQUIRED``。返回断点续传所需的步骤与环境/配置草稿。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `OobeStateResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| admin_config | object | 是 | 管理员资料草稿（username / email / nickname），未填写时为空对象 |
| completed | boolean | 是 | 向导是否已走到最后一步 |
| current_step | integer | 是 | 当前所处步骤序号（1 起） |
| database_config | object | 是 | 数据库/Redis 配置草稿的键值集合（db_type、db_host、db_port、db_name、db_user、db_path、redis_host、redis_port、redis_enabled 等）；尚未填写时为空对象，密码类键不落在此处回显 |
| environment | string | 是 | 环境选择：development 或 production |
| errors | string[] | 是 | 各步骤累积的错误摘要列表 |
| site_config | object | 是 | 站点配置草稿（site_name / site_url / 社交链接 / 功能开关等字段），未填写时为空对象 |
| success | boolean | 是 | 固定为 true；OOBE 已完成时该端点被 503 短路 |
| total_steps | integer | 是 | 总步骤数，固定 5 |

响应示例：

```json
{
  "admin_config": {},
  "completed": false,
  "current_step": 0,
  "database_config": {},
  "environment": "string",
  "errors": [
    "string"
  ],
  "site_config": {},
  "success": false,
  "total_steps": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `503` | OOBE 已完成（error_code: OOBE_REQUIRED） |

### `GET /api/oobe/status`

- **摘要**：获取 OOBE 状态
- **鉴权**：公开接口（无需鉴权）

匿名可访问（安装锁未摘时也在白名单内）。前端启动插件据此判断是否跳转 /oobe 向导；已完成时不再返回 state 进度。只读、幂等、无副作用。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `OobeStatusResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| config | object \| null | 否 | 已落盘配置文件的回显；数据库/Redis/管理员密码与 secret_key 一律替换为掩码串。文件不存在或读取失败时为 null |
| has_config | boolean | 是 | 配置文件是否已落盘 |
| oobe_complete | boolean | 是 | 安装锁是否存在；true 时前台正常放行，false 时其余接口 503 |
| state | object \| null | 否 | 向导断点状态；OOBE 已完成时为 null（不再对外暴露进度） |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "config": "string",
  "has_config": false,
  "oobe_complete": false,
  "state": "string",
  "success": false
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/oobe/system-info`

- **摘要**：获取系统信息
- **鉴权**：公开接口（无需鉴权）

匿名可访问（OOBE 白名单）。返回操作系统、CPU、内存、磁盘与当前解释器等主机概览，供向导第一步展示运行环境。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `OobeSystemInfoResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| architecture | string | 是 | 机器架构标识，如 AMD64 / x86_64 |
| available_memory_mb | integer | 是 | 可用内存（MB，四舍五入） |
| cpu_count | integer | 是 | 逻辑 CPU 核数 |
| disk_free_gb | integer | 是 | 启动盘剩余容量（GB，四舍五入） |
| disk_total_gb | integer | 是 | 启动盘总容量（GB，四舍五入） |
| hostname | string | 是 | 主机名 |
| os_name | string | 是 | 友好的操作系统名，如 Windows / macOS / 发行版全名 |
| os_type | string | 是 | 平台族标识：Windows / Darwin / Linux |
| os_version | string | 是 | 操作系统版本串 |
| processor | string | 是 | CPU 型号名称，探测不到时为空串 |
| python_path | string | 是 | 当前解释器可执行文件路径 |
| python_version | string | 是 | Python 解释器版本串 |
| success | boolean | 是 | 固定为 true |
| total_memory_mb | integer | 是 | 物理内存总量（MB，四舍五入） |

响应示例：

```json
{
  "architecture": "string",
  "available_memory_mb": 0,
  "cpu_count": 0,
  "disk_free_gb": 0,
  "disk_total_gb": 0,
  "hostname": "string",
  "os_name": "string",
  "os_type": "string",
  "os_version": "string",
  "processor": "string",
  "python_path": "string",
  "python_version": "string",
  "success": false,
  "total_memory_mb": 0
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/oobe/test-database`

- **摘要**：测试数据库连接（已废弃）
- **鉴权**：公开接口（无需鉴权）

**Deprecated**：请改用 **POST /oobe/test-database**。本端点把数据库密码放在 query string 里（`?db_password=...`），而 query string 会被 Nginx / uvicorn / 浏览器历史 / APM 原样写进访问日志——等于把口令明文落盘。保留仅为兼容。匿名可访问（OOBE 白名单，安装前不存在任何凭证可保护它）。sqlite 分支不建连接，只回一句提示与由表单参数构建出的连接串；postgresql 分支用 asyncpg 实连维护库做探测，连接失败也回 HTTP 200 + success=false（原因在 message/details，均已脱敏）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `OobeDatabaseTestResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| database_url | string \| null | 否 | 仅 SQLite 分支返回：由表单构建出的连接串（不含凭据） |
| details | object \| null | 否 | 仅 PostgreSQL 分支返回：附加信息，成功时含服务端 version 文本，异常时含 warning |
| message | string | 是 | 结果说明文案，含失败原因与安装依赖提示 |
| success | boolean | 是 | 连接是否成功（SQLite 分支恒为 true） |

响应示例：

```json
{
  "database_url": "string",
  "details": "string",
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/oobe/test-database`

- **摘要**：测试数据库连接（推荐）
- **鉴权**：公开接口（无需鉴权）

匿名可访问（OOBE 白名单）。**请优先使用本端点而不是同路径的 GET**：GET 会把数据库密码带在 query string 里，从而落进访问日志。postgresql 分支先连维护库证明账号密码可用，再查目标库是否存在、账号有无建库权限；结果以结构化 `code`（DB_* 系列）返回，失败也回 HTTP 200。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `DatabaseTestRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| db_host | string | 否 |  |
| db_name | string | 否 |  |
| db_password | string | 否 |  |
| db_path | string | 否 |  |
| db_port | integer | 否 |  |
| db_type | string | 否 |  |
| db_user | string | 否 |  |

```json
{
  "db_host": "localhost",
  "db_name": "rosetta",
  "db_password": "",
  "db_path": "rosetta.db",
  "db_port": 5432,
  "db_type": "sqlite",
  "db_user": ""
}
```

**出参**

`200` · 模型 `OobeDatabaseTestPostResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | string | 是 | 结构化错误码（DB_* 系列） |
| database_url | string \| null | 否 | 仅 SQLite 分支返回：由表单构建出的连接串（不含凭据） |
| details | object \| null | 否 | 附加信息：version / exists 等 |
| hint | string \| null | 否 | 可操作的下一步建议 |
| message | string | 是 | 结论文案（已脱敏，不含口令） |
| success | boolean | 是 | 连接是否成功（SQLite 分支恒为 true） |

响应示例：

```json
{
  "code": "string",
  "database_url": "string",
  "details": "string",
  "hint": "string",
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 公告（6）

站点公告发布与管理

### `GET /api/admin/announcements`

- **摘要**：管理员获取所有公告
- **鉴权**：需鉴权：`HTTPBearer`

列表，支持按激活状态过滤。注意：本端点有意返回全量裸列表（不分页）——前端 fetchAdminManage/announcements 页按 list 结构消费且未实现分页器；page/page_size 参数不会被接受或生效。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "content": "string",
    "created_at": "string",
    "end_time": "string",
    "id": 0,
    "is_active": true,
    "is_dismissible": true,
    "sort_order": 0,
    "start_time": "string",
    "title": "string",
    "type": "info",
    "updated_at": "string"
  }
]
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/announcements`

- **摘要**：创建公告
- **鉴权**：需鉴权：`HTTPBearer`

管理员创建新公告。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `AnnouncementCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | string | 是 | 公告正文 |
| end_time | string \| null | 否 | 生效结束时间 |
| is_active | boolean | 否 | 是否启用 |
| is_dismissible | boolean | 否 | 是否允许用户关闭 |
| sort_order | integer | 否 | 排序权重，越小越靠前 |
| start_time | string \| null | 否 | 生效开始时间 |
| title | string | 是 | 公告标题 |
| type | enum(`info`, `warning`, `success`, `error`) | 否 | 公告类型 |

```json
{
  "content": "string",
  "end_time": "string",
  "is_active": true,
  "is_dismissible": true,
  "sort_order": 0,
  "start_time": "string",
  "title": "string",
  "type": "info"
}
```

**出参**

`201` · 模型 `AnnouncementResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | string | 是 | 公告正文 |
| created_at | string | 是 |  |
| end_time | string \| null | 否 | 生效结束时间 |
| id | integer | 是 |  |
| is_active | boolean | 否 | 是否启用 |
| is_dismissible | boolean | 否 | 是否允许用户关闭 |
| sort_order | integer | 否 | 排序权重，越小越靠前 |
| start_time | string \| null | 否 | 生效开始时间 |
| title | string | 是 | 公告标题 |
| type | enum(`info`, `warning`, `success`, `error`) | 否 | 公告类型 |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "content": "string",
  "created_at": "string",
  "end_time": "string",
  "id": 0,
  "is_active": true,
  "is_dismissible": true,
  "sort_order": 0,
  "start_time": "string",
  "title": "string",
  "type": "info",
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/admin/announcements/{announcement_id}`

- **摘要**：更新公告
- **鉴权**：需鉴权：`HTTPBearer`

管理员更新指定公告。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `AnnouncementUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | string \| null | 否 |  |
| end_time | string \| null | 否 |  |
| is_active | boolean \| null | 否 |  |
| is_dismissible | boolean \| null | 否 |  |
| sort_order | integer \| null | 否 |  |
| start_time | string \| null | 否 |  |
| title | string \| null | 否 |  |
| type | enum(`info`, `warning`, `success`, `error`) \| null | 否 |  |

```json
{
  "content": "string",
  "end_time": "string",
  "is_active": "string",
  "is_dismissible": "string",
  "sort_order": "string",
  "start_time": "string",
  "title": "string",
  "type": "string"
}
```

**出参**

`200` · 模型 `AnnouncementResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | string | 是 | 公告正文 |
| created_at | string | 是 |  |
| end_time | string \| null | 否 | 生效结束时间 |
| id | integer | 是 |  |
| is_active | boolean | 否 | 是否启用 |
| is_dismissible | boolean | 否 | 是否允许用户关闭 |
| sort_order | integer | 否 | 排序权重，越小越靠前 |
| start_time | string \| null | 否 | 生效开始时间 |
| title | string | 是 | 公告标题 |
| type | enum(`info`, `warning`, `success`, `error`) | 否 | 公告类型 |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "content": "string",
  "created_at": "string",
  "end_time": "string",
  "id": 0,
  "is_active": true,
  "is_dismissible": true,
  "sort_order": 0,
  "start_time": "string",
  "title": "string",
  "type": "info",
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/admin/announcements/{announcement_id}`

- **摘要**：删除公告
- **鉴权**：需鉴权：`HTTPBearer`

管理员删除指定公告。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/admin/announcements/{announcement_id}/toggle`

- **摘要**：切换公告激活状态
- **鉴权**：需鉴权：`HTTPBearer`

管理员切换公告的激活状态。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `AnnouncementResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | string | 是 | 公告正文 |
| created_at | string | 是 |  |
| end_time | string \| null | 否 | 生效结束时间 |
| id | integer | 是 |  |
| is_active | boolean | 否 | 是否启用 |
| is_dismissible | boolean | 否 | 是否允许用户关闭 |
| sort_order | integer | 否 | 排序权重，越小越靠前 |
| start_time | string \| null | 否 | 生效开始时间 |
| title | string | 是 | 公告标题 |
| type | enum(`info`, `warning`, `success`, `error`) | 否 | 公告类型 |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "content": "string",
  "created_at": "string",
  "end_time": "string",
  "id": 0,
  "is_active": true,
  "is_dismissible": true,
  "sort_order": 0,
  "start_time": "string",
  "title": "string",
  "type": "info",
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/announcements`

- **摘要**：获取当前活跃公告
- **鉴权**：公开接口（无需鉴权）

获取当前时间范围内处于激活状态的公告列表，按 sort_order 升序排列。结果缓存 60 秒，公告写操作会立即失效缓存。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "content": "string",
    "created_at": "string",
    "end_time": "string",
    "id": 0,
    "is_active": true,
    "is_dismissible": true,
    "sort_order": 0,
    "start_time": "string",
    "title": "string",
    "type": "info",
    "updated_at": "string"
  }
]
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

---

## 网站动态（8）

用户活动时间线

### `GET /api/activities`

- **摘要**：获取已发布动态列表
- **鉴权**：公开接口（无需鉴权）

获取已发布的网站动态列表，支持分页。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PaginatedResponse_ActivityLocalizedResponse_`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 |  |
| page | integer | 是 | 当前页码 |
| page_size | integer | 是 | 每页大小 |
| total | integer | 是 | 总记录数 |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [
    {
      "author": {
        "avatar": "…",
        "avatar_source": "…",
        "bio": "…",
        "cover_image": "…",
        "created_at": "…",
        "github": "…",
        "id": "…",
        "nickname": "…",
        "resolved_avatar_url": "…",
        "title": "…",
        "username": "…",
        "website": "…"
      },
      "content": "string",
      "created_at": "string",
      "id": 0,
      "is_published": false,
      "likes_count": 0,
      "type": "say",
      "updated_at": "string"
    }
  ],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/activities`

- **摘要**：创建动态（登录用户可发布公开说说）
- **鉴权**：需鉴权：`HTTPBearer`

登录用户可以创建自己的动态，is_published 默认 True；如果未登录返回 401。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `ActivityCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | object<string, string> | 是 | 多语言内容，如 {'zh': '内容', 'en': 'Content', 'ja': 'コンテンツ', 'zh_Hant': '內容'} |
| is_published | boolean | 否 | 是否已发布 |
| type | enum(`say`, `article`, `update`, `notice`, `link`) | 否 | 动态类型 |

```json
{
  "content": {},
  "is_published": true,
  "type": "say"
}
```

**出参**

`201` · 模型 `ActivityResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author | object | 是 | 公开作者卡片模型（用于文章 / 相册等资源的 ``author`` 字段）。 与 :class:`UserResponse` 的差别就是本模型**没有**的那些字段： ``email``、``qq``、``is_active`` / ``is_staff`` / ``is_sup … （完整说明见 `/docs`） |
| author.avatar | string \| null | 否 |  |
| author.avatar_source | string \| null | 否 |  |
| author.bio | string \| null | 否 |  |
| author.cover_image | string \| null | 否 |  |
| author.created_at | string | 是 |  |
| author.github | string \| null | 否 |  |
| author.id | integer | 是 |  |
| author.nickname | string \| null | 否 |  |
| author.resolved_avatar_url | string \| null | 否 |  |
| author.title | object \| null | 否 |  |
| author.username | string | 是 |  |
| author.website | string \| null | 否 |  |
| content | object<string, string> | 是 |  |
| created_at | string | 是 |  |
| id | integer | 是 |  |
| is_published | boolean | 是 |  |
| likes_count | integer | 否 |  |
| type | enum(`say`, `article`, `update`, `notice`, `link`) | 是 |  |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "author": {
    "avatar": "string",
    "avatar_source": "string",
    "bio": "string",
    "cover_image": "string",
    "created_at": "string",
    "github": "string",
    "id": 0,
    "nickname": "string",
    "resolved_avatar_url": "string",
    "title": "string",
    "username": "string",
    "website": "string"
  },
  "content": {},
  "created_at": "string",
  "id": 0,
  "is_published": false,
  "likes_count": 0,
  "type": "say",
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/activities/{activity_id}/like`

- **摘要**：给动态点赞
- **鉴权**：公开接口（无需鉴权）

每次调用 likes_count +1，允许匿名。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/admin/activities`

- **摘要**：管理员获取所有动态
- **鉴权**：需鉴权：`HTTPBearer`

列表，包括未发布的，支持按发布状态与类型（type）过滤、分页。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PaginatedResponse_ActivityResponse_`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 |  |
| page | integer | 是 | 当前页码 |
| page_size | integer | 是 | 每页大小 |
| total | integer | 是 | 总记录数 |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [
    {
      "author": {
        "avatar": "…",
        "avatar_source": "…",
        "bio": "…",
        "cover_image": "…",
        "created_at": "…",
        "github": "…",
        "id": "…",
        "nickname": "…",
        "resolved_avatar_url": "…",
        "title": "…",
        "username": "…",
        "website": "…"
      },
      "content": {},
      "created_at": "string",
      "id": 0,
      "is_published": false,
      "likes_count": 0,
      "type": "say",
      "updated_at": "string"
    }
  ],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/activities`

- **摘要**：创建动态
- **鉴权**：需鉴权：`HTTPBearer`

管理员创建新动态。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `ActivityCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | object<string, string> | 是 | 多语言内容，如 {'zh': '内容', 'en': 'Content', 'ja': 'コンテンツ', 'zh_Hant': '內容'} |
| is_published | boolean | 否 | 是否已发布 |
| type | enum(`say`, `article`, `update`, `notice`, `link`) | 否 | 动态类型 |

```json
{
  "content": {},
  "is_published": true,
  "type": "say"
}
```

**出参**

`201` · 模型 `ActivityResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author | object | 是 | 公开作者卡片模型（用于文章 / 相册等资源的 ``author`` 字段）。 与 :class:`UserResponse` 的差别就是本模型**没有**的那些字段： ``email``、``qq``、``is_active`` / ``is_staff`` / ``is_sup … （完整说明见 `/docs`） |
| author.avatar | string \| null | 否 |  |
| author.avatar_source | string \| null | 否 |  |
| author.bio | string \| null | 否 |  |
| author.cover_image | string \| null | 否 |  |
| author.created_at | string | 是 |  |
| author.github | string \| null | 否 |  |
| author.id | integer | 是 |  |
| author.nickname | string \| null | 否 |  |
| author.resolved_avatar_url | string \| null | 否 |  |
| author.title | object \| null | 否 |  |
| author.username | string | 是 |  |
| author.website | string \| null | 否 |  |
| content | object<string, string> | 是 |  |
| created_at | string | 是 |  |
| id | integer | 是 |  |
| is_published | boolean | 是 |  |
| likes_count | integer | 否 |  |
| type | enum(`say`, `article`, `update`, `notice`, `link`) | 是 |  |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "author": {
    "avatar": "string",
    "avatar_source": "string",
    "bio": "string",
    "cover_image": "string",
    "created_at": "string",
    "github": "string",
    "id": 0,
    "nickname": "string",
    "resolved_avatar_url": "string",
    "title": "string",
    "username": "string",
    "website": "string"
  },
  "content": {},
  "created_at": "string",
  "id": 0,
  "is_published": false,
  "likes_count": 0,
  "type": "say",
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/admin/activities/{activity_id}`

- **摘要**：更新动态
- **鉴权**：需鉴权：`HTTPBearer`

管理员更新指定动态。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `ActivityUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | object<string, string> \| null | 否 |  |
| is_published | boolean \| null | 否 |  |
| type | enum(`say`, `article`, `update`, `notice`, `link`) \| null | 否 |  |

```json
{
  "content": "string",
  "is_published": "string",
  "type": "string"
}
```

**出参**

`200` · 模型 `ActivityResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author | object | 是 | 公开作者卡片模型（用于文章 / 相册等资源的 ``author`` 字段）。 与 :class:`UserResponse` 的差别就是本模型**没有**的那些字段： ``email``、``qq``、``is_active`` / ``is_staff`` / ``is_sup … （完整说明见 `/docs`） |
| author.avatar | string \| null | 否 |  |
| author.avatar_source | string \| null | 否 |  |
| author.bio | string \| null | 否 |  |
| author.cover_image | string \| null | 否 |  |
| author.created_at | string | 是 |  |
| author.github | string \| null | 否 |  |
| author.id | integer | 是 |  |
| author.nickname | string \| null | 否 |  |
| author.resolved_avatar_url | string \| null | 否 |  |
| author.title | object \| null | 否 |  |
| author.username | string | 是 |  |
| author.website | string \| null | 否 |  |
| content | object<string, string> | 是 |  |
| created_at | string | 是 |  |
| id | integer | 是 |  |
| is_published | boolean | 是 |  |
| likes_count | integer | 否 |  |
| type | enum(`say`, `article`, `update`, `notice`, `link`) | 是 |  |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "author": {
    "avatar": "string",
    "avatar_source": "string",
    "bio": "string",
    "cover_image": "string",
    "created_at": "string",
    "github": "string",
    "id": 0,
    "nickname": "string",
    "resolved_avatar_url": "string",
    "title": "string",
    "username": "string",
    "website": "string"
  },
  "content": {},
  "created_at": "string",
  "id": 0,
  "is_published": false,
  "likes_count": 0,
  "type": "say",
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/admin/activities/{activity_id}`

- **摘要**：删除动态
- **鉴权**：需鉴权：`HTTPBearer`

管理员删除指定动态。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/admin/activities/{activity_id}/toggle`

- **摘要**：切换动态发布状态
- **鉴权**：需鉴权：`HTTPBearer`

管理员切换动态的发布状态。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `ActivityResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author | object | 是 | 公开作者卡片模型（用于文章 / 相册等资源的 ``author`` 字段）。 与 :class:`UserResponse` 的差别就是本模型**没有**的那些字段： ``email``、``qq``、``is_active`` / ``is_staff`` / ``is_sup … （完整说明见 `/docs`） |
| author.avatar | string \| null | 否 |  |
| author.avatar_source | string \| null | 否 |  |
| author.bio | string \| null | 否 |  |
| author.cover_image | string \| null | 否 |  |
| author.created_at | string | 是 |  |
| author.github | string \| null | 否 |  |
| author.id | integer | 是 |  |
| author.nickname | string \| null | 否 |  |
| author.resolved_avatar_url | string \| null | 否 |  |
| author.title | object \| null | 否 |  |
| author.username | string | 是 |  |
| author.website | string \| null | 否 |  |
| content | object<string, string> | 是 |  |
| created_at | string | 是 |  |
| id | integer | 是 |  |
| is_published | boolean | 是 |  |
| likes_count | integer | 否 |  |
| type | enum(`say`, `article`, `update`, `notice`, `link`) | 是 |  |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "author": {
    "avatar": "string",
    "avatar_source": "string",
    "bio": "string",
    "cover_image": "string",
    "created_at": "string",
    "github": "string",
    "id": 0,
    "nickname": "string",
    "resolved_avatar_url": "string",
    "title": "string",
    "username": "string",
    "website": "string"
  },
  "content": {},
  "created_at": "string",
  "id": 0,
  "is_published": false,
  "likes_count": 0,
  "type": "say",
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## Hero轮播（6）

首页 Hero 区轮播图配置

### `GET /api/admin/hero/slides`

- **摘要**：管理员获取所有 Hero 幻灯片
- **鉴权**：需鉴权：`HTTPBearer`

列表，支持按激活状态过滤。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "created_at": "string",
    "cta_secondary_text": "string",
    "cta_secondary_url": "string",
    "cta_text": "string",
    "cta_url": "string",
    "end_time": "string",
    "id": 0,
    "is_active": true,
    "media_type": "image",
    "media_url": "string",
    "overlay_color": "#000000",
    "overlay_opacity": 40,
    "poster_url": "string",
    "sort_order": 0,
    "start_time": "string",
    "subtitle": "string",
    "text_align": "center",
    "text_color": "light",
    "title": "string",
    "updated_at": "string"
  }
]
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/hero/slides`

- **摘要**：创建 Hero 幻灯片
- **鉴权**：需鉴权：`HTTPBearer`

管理员创建新 Hero 幻灯片。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `HeroSlideCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| cta_secondary_text | string \| null | 否 | 次按钮文案（多语言 JSON） |
| cta_secondary_url | string \| null | 否 | 次按钮链接 |
| cta_text | string \| null | 否 | 主按钮文案（多语言 JSON） |
| cta_url | string \| null | 否 | 主按钮链接 |
| end_time | string \| null | 否 | 生效结束时间 |
| is_active | boolean | 否 | 是否启用 |
| media_type | enum(`image`, `video`, `youtube`) | 否 | 媒体类型 |
| media_url | string | 是 | 媒体地址 |
| overlay_color | string | 否 | 遮罩颜色 |
| overlay_opacity | integer | 否 | 遮罩透明度 0-100 |
| poster_url | string \| null | 否 | 视频封面图 |
| sort_order | integer | 否 | 排序权重 |
| start_time | string \| null | 否 | 生效开始时间 |
| subtitle | string \| null | 否 | 副标题（多语言 JSON） |
| text_align | enum(`left`, `center`, `right`) | 否 | 文字对齐 |
| text_color | enum(`light`, `dark`) | 否 | 文字颜色主题 |
| title | string \| null | 否 | 主标题（多语言 JSON） |

```json
{
  "cta_secondary_text": "string",
  "cta_secondary_url": "string",
  "cta_text": "string",
  "cta_url": "string",
  "end_time": "string",
  "is_active": true,
  "media_type": "image",
  "media_url": "string",
  "overlay_color": "#000000",
  "overlay_opacity": 40,
  "poster_url": "string",
  "sort_order": 0,
  "start_time": "string",
  "subtitle": "string",
  "text_align": "center",
  "text_color": "light",
  "title": "string"
}
```

**出参**

`201` · 模型 `HeroSlideResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| created_at | string | 是 |  |
| cta_secondary_text | string \| null | 否 | 次按钮文案（多语言 JSON） |
| cta_secondary_url | string \| null | 否 | 次按钮链接 |
| cta_text | string \| null | 否 | 主按钮文案（多语言 JSON） |
| cta_url | string \| null | 否 | 主按钮链接 |
| end_time | string \| null | 否 | 生效结束时间 |
| id | integer | 是 |  |
| is_active | boolean | 否 | 是否启用 |
| media_type | enum(`image`, `video`, `youtube`) | 否 | 媒体类型 |
| media_url | string | 是 | 媒体地址 |
| overlay_color | string | 否 | 遮罩颜色 |
| overlay_opacity | integer | 否 | 遮罩透明度 0-100 |
| poster_url | string \| null | 否 | 视频封面图 |
| sort_order | integer | 否 | 排序权重 |
| start_time | string \| null | 否 | 生效开始时间 |
| subtitle | string \| null | 否 | 副标题（多语言 JSON） |
| text_align | enum(`left`, `center`, `right`) | 否 | 文字对齐 |
| text_color | enum(`light`, `dark`) | 否 | 文字颜色主题 |
| title | string \| null | 否 | 主标题（多语言 JSON） |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "created_at": "string",
  "cta_secondary_text": "string",
  "cta_secondary_url": "string",
  "cta_text": "string",
  "cta_url": "string",
  "end_time": "string",
  "id": 0,
  "is_active": true,
  "media_type": "image",
  "media_url": "string",
  "overlay_color": "#000000",
  "overlay_opacity": 40,
  "poster_url": "string",
  "sort_order": 0,
  "start_time": "string",
  "subtitle": "string",
  "text_align": "center",
  "text_color": "light",
  "title": "string",
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/admin/hero/slides/{slide_id}`

- **摘要**：更新 Hero 幻灯片
- **鉴权**：需鉴权：`HTTPBearer`

管理员更新指定 Hero 幻灯片。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `HeroSlideUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| cta_secondary_text | string \| null | 否 |  |
| cta_secondary_url | string \| null | 否 |  |
| cta_text | string \| null | 否 |  |
| cta_url | string \| null | 否 |  |
| end_time | string \| null | 否 |  |
| is_active | boolean \| null | 否 |  |
| media_type | enum(`image`, `video`, `youtube`) \| null | 否 |  |
| media_url | string \| null | 否 |  |
| overlay_color | string \| null | 否 |  |
| overlay_opacity | integer \| null | 否 |  |
| poster_url | string \| null | 否 |  |
| sort_order | integer \| null | 否 |  |
| start_time | string \| null | 否 |  |
| subtitle | string \| null | 否 |  |
| text_align | enum(`left`, `center`, `right`) \| null | 否 |  |
| text_color | enum(`light`, `dark`) \| null | 否 |  |
| title | string \| null | 否 |  |

```json
{
  "cta_secondary_text": "string",
  "cta_secondary_url": "string",
  "cta_text": "string",
  "cta_url": "string",
  "end_time": "string",
  "is_active": "string",
  "media_type": "string",
  "media_url": "string",
  "overlay_color": "string",
  "overlay_opacity": "string",
  "poster_url": "string",
  "sort_order": "string",
  "start_time": "string",
  "subtitle": "string",
  "text_align": "string",
  "text_color": "string",
  "title": "string"
}
```

**出参**

`200` · 模型 `HeroSlideResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| created_at | string | 是 |  |
| cta_secondary_text | string \| null | 否 | 次按钮文案（多语言 JSON） |
| cta_secondary_url | string \| null | 否 | 次按钮链接 |
| cta_text | string \| null | 否 | 主按钮文案（多语言 JSON） |
| cta_url | string \| null | 否 | 主按钮链接 |
| end_time | string \| null | 否 | 生效结束时间 |
| id | integer | 是 |  |
| is_active | boolean | 否 | 是否启用 |
| media_type | enum(`image`, `video`, `youtube`) | 否 | 媒体类型 |
| media_url | string | 是 | 媒体地址 |
| overlay_color | string | 否 | 遮罩颜色 |
| overlay_opacity | integer | 否 | 遮罩透明度 0-100 |
| poster_url | string \| null | 否 | 视频封面图 |
| sort_order | integer | 否 | 排序权重 |
| start_time | string \| null | 否 | 生效开始时间 |
| subtitle | string \| null | 否 | 副标题（多语言 JSON） |
| text_align | enum(`left`, `center`, `right`) | 否 | 文字对齐 |
| text_color | enum(`light`, `dark`) | 否 | 文字颜色主题 |
| title | string \| null | 否 | 主标题（多语言 JSON） |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "created_at": "string",
  "cta_secondary_text": "string",
  "cta_secondary_url": "string",
  "cta_text": "string",
  "cta_url": "string",
  "end_time": "string",
  "id": 0,
  "is_active": true,
  "media_type": "image",
  "media_url": "string",
  "overlay_color": "#000000",
  "overlay_opacity": 40,
  "poster_url": "string",
  "sort_order": 0,
  "start_time": "string",
  "subtitle": "string",
  "text_align": "center",
  "text_color": "light",
  "title": "string",
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/admin/hero/slides/{slide_id}`

- **摘要**：删除 Hero 幻灯片
- **鉴权**：需鉴权：`HTTPBearer`

管理员删除指定 Hero 幻灯片。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/admin/hero/slides/{slide_id}/toggle`

- **摘要**：切换 Hero 幻灯片激活状态
- **鉴权**：需鉴权：`HTTPBearer`

管理员切换 Hero 幻灯片的激活状态。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `HeroSlideResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| created_at | string | 是 |  |
| cta_secondary_text | string \| null | 否 | 次按钮文案（多语言 JSON） |
| cta_secondary_url | string \| null | 否 | 次按钮链接 |
| cta_text | string \| null | 否 | 主按钮文案（多语言 JSON） |
| cta_url | string \| null | 否 | 主按钮链接 |
| end_time | string \| null | 否 | 生效结束时间 |
| id | integer | 是 |  |
| is_active | boolean | 否 | 是否启用 |
| media_type | enum(`image`, `video`, `youtube`) | 否 | 媒体类型 |
| media_url | string | 是 | 媒体地址 |
| overlay_color | string | 否 | 遮罩颜色 |
| overlay_opacity | integer | 否 | 遮罩透明度 0-100 |
| poster_url | string \| null | 否 | 视频封面图 |
| sort_order | integer | 否 | 排序权重 |
| start_time | string \| null | 否 | 生效开始时间 |
| subtitle | string \| null | 否 | 副标题（多语言 JSON） |
| text_align | enum(`left`, `center`, `right`) | 否 | 文字对齐 |
| text_color | enum(`light`, `dark`) | 否 | 文字颜色主题 |
| title | string \| null | 否 | 主标题（多语言 JSON） |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "created_at": "string",
  "cta_secondary_text": "string",
  "cta_secondary_url": "string",
  "cta_text": "string",
  "cta_url": "string",
  "end_time": "string",
  "id": 0,
  "is_active": true,
  "media_type": "image",
  "media_url": "string",
  "overlay_color": "#000000",
  "overlay_opacity": 40,
  "poster_url": "string",
  "sort_order": 0,
  "start_time": "string",
  "subtitle": "string",
  "text_align": "center",
  "text_color": "light",
  "title": "string",
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/hero/slides`

- **摘要**：获取当前活跃 Hero 幻灯片
- **鉴权**：公开接口（无需鉴权）

获取当前时间范围内处于激活状态的 Hero 幻灯片列表，按 sort_order 升序排列。若尚未配置任何轮播且开启 Bing 壁纸，则自动用 Bing 最近几日壁纸作为虚拟轮播填充。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "created_at": "string",
    "cta_secondary_text": "string",
    "cta_secondary_url": "string",
    "cta_text": "string",
    "cta_url": "string",
    "end_time": "string",
    "id": 0,
    "is_active": true,
    "media_type": "image",
    "media_url": "string",
    "overlay_color": "#000000",
    "overlay_opacity": 40,
    "poster_url": "string",
    "sort_order": 0,
    "start_time": "string",
    "subtitle": "string",
    "text_align": "center",
    "text_color": "light",
    "title": "string",
    "updated_at": "string"
  }
]
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

---

## 文章系列（8）

系列文章的组织与展示

### `GET /api/admin/series`

- **摘要**：管理员获取所有系列
- **鉴权**：需鉴权：`HTTPBearer`

列表，支持按激活状态过滤，并包含各系列下的文章数量。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "cover_image": "string",
    "created_at": "string",
    "description": "string",
    "id": 0,
    "is_active": true,
    "post_count": 0,
    "slug": "string",
    "sort_order": 0,
    "title": {},
    "updated_at": "string"
  }
]
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/series`

- **摘要**：创建系列
- **鉴权**：需鉴权：`HTTPBearer`

管理员创建新文章系列。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `PostSeriesCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| cover_image | string \| null | 否 | 系列封面图 URL |
| description | object<string, string> \| null | 否 | 多语言系列描述 |
| is_active | boolean | 否 | 是否启用 |
| slug | string | 是 | 唯一标识，用于 URL |
| sort_order | integer | 否 | 排序权重，越小越靠前 |
| title | object<string, string> | 是 | 多语言系列标题，如 {'zh': '...', 'en': '...'} |

```json
{
  "cover_image": "string",
  "description": "string",
  "is_active": true,
  "slug": "string",
  "sort_order": 0,
  "title": {}
}
```

**出参**

`201` · 模型 `PostSeriesResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| cover_image | string \| null | 否 | 系列封面图 URL |
| created_at | string | 是 |  |
| description | object<string, string> \| null | 否 | 多语言系列描述 |
| id | integer | 是 |  |
| is_active | boolean | 否 | 是否启用 |
| post_count | integer | 否 |  |
| slug | string | 是 | 唯一标识，用于 URL |
| sort_order | integer | 否 | 排序权重，越小越靠前 |
| title | object<string, string> | 是 | 多语言系列标题，如 {'zh': '...', 'en': '...'} |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "cover_image": "string",
  "created_at": "string",
  "description": "string",
  "id": 0,
  "is_active": true,
  "post_count": 0,
  "slug": "string",
  "sort_order": 0,
  "title": {},
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/admin/series/{series_id}`

- **摘要**：更新系列
- **鉴权**：需鉴权：`HTTPBearer`

管理员更新指定系列。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `PostSeriesUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| cover_image | string \| null | 否 |  |
| description | object<string, string> \| null | 否 |  |
| is_active | boolean \| null | 否 |  |
| slug | string \| null | 否 |  |
| sort_order | integer \| null | 否 |  |
| title | object<string, string> \| null | 否 |  |

```json
{
  "cover_image": "string",
  "description": "string",
  "is_active": "string",
  "slug": "string",
  "sort_order": "string",
  "title": "string"
}
```

**出参**

`200` · 模型 `PostSeriesResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| cover_image | string \| null | 否 | 系列封面图 URL |
| created_at | string | 是 |  |
| description | object<string, string> \| null | 否 | 多语言系列描述 |
| id | integer | 是 |  |
| is_active | boolean | 否 | 是否启用 |
| post_count | integer | 否 |  |
| slug | string | 是 | 唯一标识，用于 URL |
| sort_order | integer | 否 | 排序权重，越小越靠前 |
| title | object<string, string> | 是 | 多语言系列标题，如 {'zh': '...', 'en': '...'} |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "cover_image": "string",
  "created_at": "string",
  "description": "string",
  "id": 0,
  "is_active": true,
  "post_count": 0,
  "slug": "string",
  "sort_order": 0,
  "title": {},
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/admin/series/{series_id}`

- **摘要**：删除系列
- **鉴权**：需鉴权：`HTTPBearer`

管理员删除指定系列。系列下的文章 series_id 会被置空（级联 SET NULL）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/admin/series/{series_id}/toggle`

- **摘要**：切换系列激活状态
- **鉴权**：需鉴权：`HTTPBearer`

管理员切换系列的激活状态。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PostSeriesResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| cover_image | string \| null | 否 | 系列封面图 URL |
| created_at | string | 是 |  |
| description | object<string, string> \| null | 否 | 多语言系列描述 |
| id | integer | 是 |  |
| is_active | boolean | 否 | 是否启用 |
| post_count | integer | 否 |  |
| slug | string | 是 | 唯一标识，用于 URL |
| sort_order | integer | 否 | 排序权重，越小越靠前 |
| title | object<string, string> | 是 | 多语言系列标题，如 {'zh': '...', 'en': '...'} |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "cover_image": "string",
  "created_at": "string",
  "description": "string",
  "id": 0,
  "is_active": true,
  "post_count": 0,
  "slug": "string",
  "sort_order": 0,
  "title": {},
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/post_series/complete`

- **摘要**：编辑器 autocomplete 同系列文章
- **鉴权**：公开接口（无需鉴权）

根据关键词 autocomplete 系列文章（最多前 8 条）。优先匹配 PostSeries；否则按分类（Category）近似作为系列。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `SeriesCompleteRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| query | string | 是 | 搜索关键词 |

```json
{
  "query": "string"
}
```

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "id": 0,
    "slug": "string",
    "title": "string"
  }
]
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/series`

- **摘要**：获取文章系列列表
- **鉴权**：公开接口（无需鉴权）

获取所有启用且包含已发布文章的系列，按 sort_order 升序排列。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "cover_image": "string",
    "created_at": "string",
    "description": "string",
    "id": 0,
    "is_active": true,
    "post_count": 0,
    "slug": "string",
    "sort_order": 0,
    "title": {},
    "updated_at": "string"
  }
]
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/series/{slug}`

- **摘要**：获取系列详情
- **鉴权**：公开接口（无需鉴权）

根据 slug ，包含该系列下所有已发布文章列表（按 series_order 排序）。公开接口、无需鉴权；响应为裸 dict（无 success/data 信封），post_count 恒等于 posts 长度；系列不存在或未激活返回 404。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `SeriesDetailDoc`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| cover_image | string \| null | 否 | 系列封面图 URL，未设置时为 null |
| created_at | string | 是 | 创建时间（响应序列化为 ISO 8601 字符串） |
| description | object<string, string> \| null | 否 | 多语言系列描述，未设置时为 null |
| id | integer | 是 | 系列 ID |
| post_count | integer | 是 | 已发布文章数，等于 posts 数组长度 |
| posts | object[] | 否 | 已发布文章列表，按 series_order 升序、再按发布时间倒序 |
| slug | string | 是 | 系列 slug |
| sort_order | integer | 是 | 系列间排序权重，越小越靠前 |
| title | object<string, string> | 是 | 多语言系列标题（JSON 列原样返回） |
| updated_at | string | 是 | 更新时间（响应序列化为 ISO 8601 字符串） |

响应示例：

```json
{
  "cover_image": "string",
  "created_at": "string",
  "description": "string",
  "id": 0,
  "post_count": 0,
  "posts": [
    {
      "cover_image": "string",
      "id": 0,
      "published_at": "string",
      "series_order": "string",
      "slug": "string",
      "title": {},
      "views": "string"
    }
  ],
  "slug": "string",
  "sort_order": 0,
  "title": {},
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 内容加密（4）

文章内容加密访问

### `POST /api/admin/posts/{post_id}/encrypt`

- **摘要**：设置文章加密内容
- **鉴权**：需鉴权：`HTTPBearer`

管理员使用指定密码对内容进行 AES-GCM 加密并存储，同时标记文章为加密状态。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `EncryptRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | string | 是 | 待加密的明文内容 |
| hint | string \| null | 否 | 密码提示文案 |
| password | string | 是 | 加密密码（明文） |

```json
{
  "content": "string",
  "hint": "string",
  "password": "string"
}
```

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/admin/posts/{post_id}/encrypt`

- **摘要**：更新文章加密内容（换密码/内容）
- **鉴权**：需鉴权：`HTTPBearer`

使用旧密码验证后，重新加密内容或更换访问密码。若 old_password 为空则跳过验证（需管理员权限）。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `UpdateEncryptionRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | string \| null | 否 | 新的明文内容；为空时使用旧内容解密后重新加密 |
| hint | string \| null | 否 | 密码提示文案 |
| new_password | string | 是 | 新密码（明文） |
| old_password | string \| null | 否 | 旧密码（用于验证）；为空时跳过验证 |

```json
{
  "content": "string",
  "hint": "string",
  "new_password": "string",
  "old_password": "string"
}
```

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/admin/posts/{post_id}/encrypt`

- **摘要**：关闭文章内容加密
- **鉴权**：需鉴权：`HTTPBearer`

关闭加密并清除密文、密码哈希与提示。文章内容将恢复为公开可读（仍受 Post.content 字段控制）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/posts/{post_id}/decrypt`

- **摘要**：解密文章内容
- **鉴权**：公开接口（无需鉴权）

提交访问密码，校验通过后返回文章的解密内容。仅对已启用加密的文章有效。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `DecryptRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| password | string | 是 | 访问密码（明文） |

```json
{
  "password": "string"
}
```

**出参**

`200` · 模型 `DecryptResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| content | string | 是 |  |
| hint | string \| null | 否 |  |

响应示例：

```json
{
  "content": "string",
  "hint": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 文章加密工具（3）

文章加密的管理工具

### `POST /api/post_crypto/derive_keys`

- **摘要**：派生加密元数据
- **鉴权**：公开接口（无需鉴权）

给定密码，生成随机 salt 与 verifier（HMAC-SHA256(salt, password)）。前端将这三个字段与 PostCreate 一起发送，后端不保存明文密码。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `DeriveKeysRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| password | string | 是 | 用户输入的明文密码 |

```json
{
  "password": "string"
}
```

**出参**

`200` · 模型 `DeriveKeysResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| algorithm | string | 否 |  |
| salt | string | 是 |  |
| verifier | string | 是 |  |

响应示例：

```json
{
  "algorithm": "AES-256-GCM",
  "salt": "string",
  "verifier": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/post_crypto/encrypted/{post_id}/preview`

- **摘要**：后台预览加密文章摘要
- **鉴权**：需鉴权：`HTTPBearer`

作者或管理员获取加密文章的基本信息（标题/创建时间/加密状态），用于编辑器预览加密效果。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `EncryptedPreviewResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| created_at | string | 是 |  |
| encryption_enabled | boolean | 是 |  |
| encryption_hint | string \| null | 否 |  |
| id | integer | 是 |  |
| scheduled_at | string \| null | 否 |  |
| slug | string | 是 |  |
| title | object \| string | 是 |  |

响应示例：

```json
{
  "created_at": "string",
  "encryption_enabled": false,
  "encryption_hint": "string",
  "id": 0,
  "scheduled_at": "string",
  "slug": "string",
  "title": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/post_crypto/verify_access`

- **摘要**：验证文章访问密码
- **鉴权**：公开接口（无需鉴权）

给定文章 ID 与密码，重新计算 verifier 并与数据库比对。成功返回 ok=true 和 1h 短期 JWT（scope=post_access）。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `VerifyAccessRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| password | string | 是 | 访问密码（明文） |
| post_id | integer | 是 | 目标文章 ID |

```json
{
  "password": "string",
  "post_id": 0
}
```

**出参**

`200` · 模型 `VerifyAccessResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string \| null | 否 |  |
| ok | boolean | 是 |  |
| token | string \| null | 否 |  |

响应示例：

```json
{
  "message": "string",
  "ok": false,
  "token": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 定时发布（3）

定时发布任务管理

### `GET /api/admin/posts/scheduled`

- **摘要**：获取定时发布文章列表
- **鉴权**：需鉴权：`HTTPBearer`

获取所有处于定时等待状态的文章（scheduled_at 非空），按 scheduled_at 升序，响应为裸数组（无分页/信封）。需 CurrentStaff。查询前会先触发到期文章的发布，因此列表中不会再包含已到点的文章。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "author_id": "string",
    "cover_image": "string",
    "id": 0,
    "published_at": "string",
    "scheduled_at": "string",
    "slug": "string",
    "status": "string",
    "title": {}
  }
]
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `PUT /api/admin/posts/{post_id}/schedule`

- **摘要**：设置定时发布
- **鉴权**：需鉴权：`HTTPBearer`

为文章时间。若计划时间已过去则立即发布。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `ScheduleRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| scheduled_at | string | 是 | 计划发布时间（UTC） |
| status | string \| null | 否 | 文章状态，默认为 published（定时发布） |

```json
{
  "scheduled_at": "string",
  "status": "string"
}
```

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/admin/posts/{post_id}/schedule`

- **摘要**：取消定时发布
- **鉴权**：需鉴权：`HTTPBearer`

取消文章的定时发布计划（清空 scheduled_at），不影响文章当前状态。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 评论表情反应（3）

评论表情互动

### `GET /api/comments/{comment_id}/reactions`

- **摘要**：获取评论表情反应统计
- **鉴权**：需鉴权：`HTTPBearer`

公开获取指定评论的所有表情反应统计。如当前用户已登录，返回 reacted 字段标识是否已添加该表情。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `CommentReactionSummaryList`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| comment_id | integer | 是 |  |
| reactions | object[] | 是 |  |
| total | integer | 是 |  |

响应示例：

```json
{
  "comment_id": 0,
  "reactions": [
    {
      "count": 0,
      "emoji": "string",
      "reacted": false
    }
  ],
  "total": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/comments/{comment_id}/reactions`

- **摘要**：添加评论表情反应
- **鉴权**：需鉴权：`HTTPBearer`

登录用户对指定评论添加一个表情反应。同一用户对同一评论的同一表情只能添加一次。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `CommentReactionCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| emoji | string | 是 | 表情符号 |

```json
{
  "emoji": "string"
}
```

**出参**

`201` · 模型 `CommentReactionResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| comment_id | integer | 是 |  |
| created_at | string | 是 |  |
| emoji | string | 是 |  |
| id | integer | 是 |  |
| user_id | integer | 是 |  |

响应示例：

```json
{
  "comment_id": 0,
  "created_at": "string",
  "emoji": "string",
  "id": 0,
  "user_id": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/comments/{comment_id}/reactions/{emoji}`

- **摘要**：取消评论表情反应
- **鉴权**：需鉴权：`HTTPBearer`

登录用户取消自己对指定评论的某个表情反应。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 热门排行（1）

热门文章排行榜

### `GET /api/ranking/posts`

- **摘要**：热门文章排行榜
- **鉴权**：公开接口（无需鉴权）

根据浏览量、点赞数、评论数综合排序的。支持按时间周期过滤。公开接口、无需鉴权；结果带 60s 响应缓存（命中缓存与实时计算的响应体同构）。响应为裸 dict（period + items，无信封），items 的 title 是未解析的多语言 dict。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `HotPostsRankingResponseDoc`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 否 | 榜单条目：all 榜按总浏览量倒序直接截断；周期榜按综合分重排后截断 limit 条；窗口内无任何候选文章时是空数组 |
| period | string | 是 | 回显统计周期：day / week / month / all（month 实际窗口为 30 天） |

响应示例：

```json
{
  "items": [
    {
      "comments_count": 0,
      "cover_image": "string",
      "created_at": "string",
      "id": 0,
      "likes_count": 0,
      "published_at": "string",
      "recent_views": "string",
      "score": 0,
      "slug": "string",
      "title": {},
      "views": 0
    }
  ],
  "period": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 性能监控（4）

接口性能数据查询

### `DELETE /api/admin/performance/cleanup`

- **摘要**：清理性能监控旧数据
- **鉴权**：需鉴权：`HTTPBearer`

删除指定天数之前的性能监控记录，避免表无限增长。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `CleanupResult`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| cutoff_date | string | 是 |  |
| deleted_count | integer | 是 |  |
| remaining_count | integer | 是 |  |
| success | boolean | 是 |  |

响应示例：

```json
{
  "cutoff_date": "string",
  "deleted_count": 0,
  "remaining_count": 0,
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/admin/performance/slow`

- **摘要**：最慢的请求
- **鉴权**：需鉴权：`HTTPBearer`

返回最近 7 天内最慢的 20 个请求记录。

**入参**

_无路径 / query 参数_

**出参**

`200`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| (根) | object[] | — |  |

响应示例：

```json
[
  {
    "created_at": "string",
    "endpoint": "string",
    "id": 0,
    "ip": "string",
    "method": "string",
    "response_time_ms": 0,
    "status_code": 0,
    "user_agent": "string"
  }
]
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/admin/performance/storage`

- **摘要**：性能数据存储统计
- **鉴权**：需鉴权：`HTTPBearer`

返回性能监控表的数据量、时间范围及按状态码分组的统计，便于评估是否需要清理。需 CurrentStaff。响应为裸 dict（total_count/earliest_record/latest_record/status_breakdown/daily_breakdown/queried_at，无信封）；空表时两条时间边界为 null。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PerformanceStorageResponseDoc`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| daily_breakdown | object[] | 否 | 最近 7 天的逐日统计，日期升序 |
| earliest_record | string \| null | 否 | 最早记录的 created_at ISO 8601 字符串，空表时为 null |
| latest_record | string \| null | 否 | 最晚记录的 created_at ISO 8601 字符串，空表时为 null |
| queried_at | string | 是 | 查询时刻（handler 在返回前再取一次当前 UTC 时间的 isoformat 字符串） |
| status_breakdown | object[] | 否 | 按状态码分组计数，状态码升序 |
| total_count | integer | 是 | performance_metrics 全表行数 |

响应示例：

```json
{
  "daily_breakdown": [
    {
      "avg_response_time_ms": 0.0,
      "count": 0,
      "date": "string"
    }
  ],
  "earliest_record": "string",
  "latest_record": "string",
  "queried_at": "string",
  "status_breakdown": [
    {
      "count": 0,
      "status_code": 0
    }
  ],
  "total_count": 0
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/admin/performance/summary`

- **摘要**：性能统计摘要
- **鉴权**：需鉴权：`HTTPBearer`

返回最近 24 小时和 7 天的性能统计：平均响应时间、P95/P99、错误率、热门慢接口。需 CurrentStaff。响应为裸 dict（last_24h/last_7d/timestamp，无信封），两个窗口由同一段统计逻辑分别计算，结构完全一致。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PerformanceSummaryResponseDoc`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| last_24h | object | 是 | 单个时间窗口（24h / 7d）的性能统计块，由 ``_stats_for_period`` 产出。 |
| last_24h.avg_response_time_ms | number | 是 | 平均响应时间毫秒（保留 2 位小数） |
| last_24h.error_count | integer | 是 | 状态码 >= 400 的请求数 |
| last_24h.error_rate | number | 是 | 错误率百分比（error_count/total_requests*100，保留 2 位小数；零请求为 0） |
| last_24h.max_response_time_ms | integer | 是 | 最慢一次请求的响应时间毫秒 |
| last_24h.p95_response_time_ms | integer | 是 | P95 响应时间毫秒（升序取整索引，无数据时为 0） |
| last_24h.p99_response_time_ms | integer | 是 | P99 响应时间毫秒（同上，无数据时为 0） |
| last_24h.slow_endpoints | object[] | 否 | 平均耗时最高的 5 个接口 |
| last_24h.total_requests | integer | 是 | 窗口内记录的请求总数 |
| last_7d | object | 是 | 单个时间窗口（24h / 7d）的性能统计块，由 ``_stats_for_period`` 产出。 |
| last_7d.avg_response_time_ms | number | 是 | 平均响应时间毫秒（保留 2 位小数） |
| last_7d.error_count | integer | 是 | 状态码 >= 400 的请求数 |
| last_7d.error_rate | number | 是 | 错误率百分比（error_count/total_requests*100，保留 2 位小数；零请求为 0） |
| last_7d.max_response_time_ms | integer | 是 | 最慢一次请求的响应时间毫秒 |
| last_7d.p95_response_time_ms | integer | 是 | P95 响应时间毫秒（升序取整索引，无数据时为 0） |
| last_7d.p99_response_time_ms | integer | 是 | P99 响应时间毫秒（同上，无数据时为 0） |
| last_7d.slow_endpoints | object[] | 否 | 平均耗时最高的 5 个接口 |
| last_7d.total_requests | integer | 是 | 窗口内记录的请求总数 |
| timestamp | string | 是 | 统计基准时刻（当前 UTC 时间的 isoformat 字符串，两窗口共用） |

响应示例：

```json
{
  "last_24h": {
    "avg_response_time_ms": 0.0,
    "error_count": 0,
    "error_rate": 0.0,
    "max_response_time_ms": 0,
    "p95_response_time_ms": 0,
    "p99_response_time_ms": 0,
    "slow_endpoints": [
      {
        "avg_response_time_ms": "…",
        "endpoint": "…",
        "method": "…",
        "request_count": "…"
      }
    ],
    "total_requests": 0
  },
  "last_7d": {
    "avg_response_time_ms": 0.0,
    "error_count": 0,
    "error_rate": 0.0,
    "max_response_time_ms": 0,
    "p95_response_time_ms": 0,
    "p99_response_time_ms": 0,
    "slow_endpoints": [
      {
        "avg_response_time_ms": "…",
        "endpoint": "…",
        "method": "…",
        "request_count": "…"
      }
    ],
    "total_requests": 0
  },
  "timestamp": "string"
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

---

## 仪表盘（1）

后台仪表盘统计数据

### `GET /api/admin/stats`

- **摘要**：管理后台统计数据
- **鉴权**：需鉴权：`HTTPBearer`

获取文章、评论、用户、媒体等模块的统计概览数据。需 CurrentStaff。range 参数选 7d（默认）或 30d（其它值一律按 7 天处理）。响应为 success/data/message 信封；没有真实数据时返回 0 / 空数组，绝不回填演示数据，由前端渲染空状态。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `AdminStatsResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 仪表盘统计的 data 载荷。 |
| data.active_commenters | object[] | 否 | 评论数 Top 5 用户（无数据时为空数组） |
| data.summary | object | 是 | 仪表盘顶部的 8 个总量/今日计数。 |
| data.system_health | object | 是 | 系统健康探测（各指标独立降级：探测失败如实为 null，未知 ≠ 健康）。 |
| data.timeseries | object | 是 | 仪表盘折线图数据。 |
| data.top_articles | object[] | 否 | 浏览量 Top 5（无文章时为空数组） |
| message | string | 否 | 人类可读提示 |
| success | boolean | 否 | 固定为 true（失败走错误信封） |

响应示例：

```json
{
  "data": {
    "active_commenters": [
      {
        "avatar": "…",
        "comments_count": "…",
        "name": "…",
        "title": "…"
      }
    ],
    "summary": {
      "total_comments": 0,
      "total_comments_today": 0,
      "total_drafts": 0,
      "total_pending_comments": 0,
      "total_posts": 0,
      "total_published": 0,
      "total_users": 0,
      "total_views_today": 0
    },
    "system_health": {
      "cache_hit_percent": "string",
      "cpu_percent": "string",
      "db_rtt_ms": "string",
      "health_score": "string",
      "memory_percent": "string",
      "metric_scores": {
        "cache": "…",
        "cpu": "…",
        "db": "…",
        "memory": "…"
      }
    },
    "timeseries": {
      "datasets": [
        "…"
      ],
      "labels": [
        "…"
      ]
    },
    "top_articles": [
      {
        "comments_count": "…",
        "id": "…",
        "title": "…",
        "views": "…"
      }
    ]
  },
  "message": "获取仪表盘统计成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 操作日志（1）

管理员操作审计日志

### `DELETE /api/admin/logs/retention`

- **摘要**：清理旧日志
- **鉴权**：需鉴权：`HTTPBearer`

按保留天数删除早于 N 天的操作日志记录。需登录且为 staff/superuser（不满足返回 403）；days 取值 1-3650，越界 422。响应即 _RetentionResponse 模型实例（deleted_count + cutoff 时间点），无信封包裹。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `_RetentionResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| before | string | 是 | 保留期截止时间点（cutoff）的 ISO 8601 字符串，早于该时间的记录被删除 |
| deleted_count | integer | 是 | 本次实际删除的日志条数（无可删记录时为 0） |

响应示例：

```json
{
  "before": "string",
  "deleted_count": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## Admin 工具（4）

后台通用工具接口

### `GET /api/admin/alembic/status`

- **摘要**：查看 Alembic 迁移状态
- **鉴权**：需鉴权：`HTTPBearer`

读取当前数据库版本、最新版本、已应用与待应用的迁移列表。读取失败返回 500，不会回 `is_latest=true` 的空壳响应——前端迁移页据此展示错误态，而不是把「取不到状态」显示成「已是最新」。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `AlembicStatusResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| applied | object[] | 否 |  |
| current_version | string | 是 |  |
| is_latest | boolean | 是 |  |
| latest_version | string | 是 |  |
| pending | object[] | 否 |  |

响应示例：

```json
{
  "applied": [
    {
      "applied_at": "string",
      "message": "",
      "version": "string"
    }
  ],
  "current_version": "string",
  "is_latest": false,
  "latest_version": "string",
  "pending": [
    {
      "message": "",
      "version": "string"
    }
  ]
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `POST /api/admin/alembic/upgrade`

- **摘要**：执行 Alembic schema 升级（upgrade head）
- **鉴权**：需鉴权：`HTTPBearer`

在后台线程执行 `alembic upgrade head`，将数据库 schema 升级到最新版本。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `AlembicUpgradeResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 |  |
| success | boolean | 是 |  |

响应示例：

```json
{
  "message": "string",
  "success": false
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `POST /api/admin/cache/flush`

- **摘要**：刷新缓存
- **鉴权**：需鉴权：`HTTPBearer`

按前缀或全部清空缓存，支持指定 pattern。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `CacheFlushRequest`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| mode | enum(`all`, `post_list`, `post_detail`, `settings`, `fragments`) | 否 |  |

```json
{
  "mode": "all"
}
```

**出参**

`200` · 模型 `CacheFlushResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| deleted_keys | integer | 是 |  |
| message | string | 是 |  |
| mode | enum(`all`, `post_list`, `post_detail`, `settings`, `fragments`) | 是 |  |

响应示例：

```json
{
  "deleted_keys": 0,
  "message": "string",
  "mode": "all"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/admin/cache/status`

- **摘要**：查看缓存状态
- **鉴权**：需鉴权：`HTTPBearer`

获取当前缓存后端的统计信息（命中率、内存使用等）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `CacheStatusResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| backend | enum(`memory`, `redis`) | 是 |  |
| hit_rate | number \| null | 否 |  |
| keys | integer | 否 |  |
| memory_used_bytes | integer \| null | 否 |  |

响应示例：

```json
{
  "backend": "memory",
  "hit_rate": "string",
  "keys": 0,
  "memory_used_bytes": "string"
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

---

## 系统设置（4）

站点配置分组读写

### `GET /api/settings`

- **摘要**：获取所有设置分组
- **鉴权**：需鉴权：`HTTPBearer`

需管理员（CurrentStaff）。返回全部 17 组分组的配置项（含敏感明文值，如 SMTP 密码）；前台/SSR 一律改用 GET /settings/public，不得调用本接口。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `SettingsAllResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| groups | object | 是 | 全部 17 组配置，键为分组名、值为该组合并默认值后的完整 dict（含敏感明文值） |

响应示例：

```json
{
  "groups": {}
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/settings/public`

- **摘要**：公开站设置（无需登录）
- **鉴权**：公开接口（无需鉴权）

匿名可读的站点配置子集：只对 PUBLIC_SETTING_GROUPS 白名单分组下发，白名单内疑似敏感键（password/secret/token/api_key/...）统一脱敏为 "******"。结果服务端缓存 300s（PATCH 任一分组后立即失效）。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `SettingsPublicResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| groups | object | 是 | 仅 PUBLIC_SETTING_GROUPS 白名单内的分组；疑似敏感键（password/secret/token/api_key 等）值统一脱敏为 "******" |

响应示例：

```json
{
  "groups": {}
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/settings/{group}`

- **摘要**：获取单个设置分组
- **鉴权**：需鉴权：`HTTPBearer`

需管理员（CurrentStaff）。返回指定分组（17 组之一）合并默认值后的完整配置；未知分组 404。直接返回 {group, data} 裸对象（无 success 信封）。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `SettingsGroupResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 该分组的完整配置（默认值与 DB 存值的合并结果） |
| group | string | 是 | 分组键（17 组之一） |

响应示例：

```json
{
  "data": {},
  "group": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 未知设置分组 |
| `422` | Validation Error |

### `PATCH /api/settings/{group}`

- **摘要**：更新单个设置分组
- **鉴权**：需鉴权：`HTTPBearer`

需管理员（CurrentStaff）。payload 为该分组的部分键值对象；不在该组默认值键集内的键被静默丢弃。副作用：写入操作日志（含 before/after diff）、落库 site_configs 后立刻失效 /settings/public（300s）与 /api/config 的 site_config（3600s）缓存——分组 JSON 是 /api/config 的权威覆写来源，不失效则站点名等改动最长 1 小时不可见。未知分组 404；payload 非对象 400。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`）


```json
{}
```

**出参**

`200` · 模型 `SettingsPatchResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| changed | string[] | 否 | 与更新前相比发生变化的键名列表 |
| data | object | 是 | 保存后的最终配置（payload 中不在该组默认值键集内的键已被丢弃） |
| group | string | 是 | 被更新的分组键 |
| success | boolean | 是 | 固定为 true；已写操作日志并失效公开设置缓存 |

响应示例：

```json
{
  "changed": [
    "string"
  ],
  "data": {},
  "group": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `400` | payload 必须为 JSON 对象 |
| `404` | 未知设置分组 |
| `422` | Validation Error |

---

## 主题（4）

前台主题切换与配置

### `PUT /api/admin/themes/current`

- **摘要**：管理员设置默认调色板
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。请求体 {palette_id}（或兼容 {id}），取值必须在 AVAILABLE_PALETTES 内，否则 422 并列出可选值。写入 SiteConfig KV 键 theme_palette，幂等（重复设置同值无副作用）；生效后经 GET /api/themes/current.css 编译为 HSL CSS 变量注入前台。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`）


```json
{}
```

**出参**

`200` · 模型 `PaletteSetResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 默认调色板写入成功后回显的载荷。 |
| data.palette_id | string | 是 | 已生效的调色板 id（即请求体提交值，必在清单内） |
| success | boolean | 否 | 固定为 true（校验失败走 422 错误信封） |

响应示例：

```json
{
  "data": {
    "palette_id": "string"
  },
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/themes/active`

- **摘要**：获取当前激活主题（公开，支持 Customizer 前台渲染）
- **鉴权**：需鉴权：`HTTPBearer`

公开接口，访客无需登录即可读取（也可带 token，但权限一致），供前台页面渲染主题 Customizer 覆盖样式。data 是主题记录，mods 为清单默认值与已存值的合并；mods 读取失败只把 mods 置 null，不阻断响应。站点尚未启用任何主题时 data 为 null 并附 message 提示。preview 参数是后台预览入口：传主题 slug 时返回该主题自身的信息（不改变站点激活主题），slug 不存在或未安装时静默回落到激活主题。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `ActiveThemeResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object \| null | 否 | 主题记录：mods 为清单默认值与 DB 存值的合并结果，mods 读取失败时该字段回退 null 而不阻断响应；站点尚未启用任何主题时为 null |
| message | string \| null | 否 | 仅 data 为 null 时出现，取值为「未启用自定义主题」 |
| success | boolean | 否 | 固定为 true |

响应示例：

```json
{
  "data": "string",
  "message": "string",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/themes/current.css`

- **摘要**：获取当前启用调色板的 CSS
- **鉴权**：公开接口（无需鉴权）

返回当前启用调色板编译出的 CSS 自定义属性样式表（text/css; charset=utf-8），公开访问、无需鉴权，可直接作为 <link rel=stylesheet> 链接使用。未显式指定 palette 参数时取站点配置里保存的默认调色板，缺省回退内置调色板；参数取值不在清单内时 400。编译结果按调色板 id 走进程内缓存，响应本身不带 HTTP 缓存头。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/themes/palettes`

- **摘要**：获取所有可用调色板
- **鉴权**：需鉴权：`HTTPBearer`

公开接口。返回后端 AVAILABLE_PALETTES 全量清单（id / name / label / 明暗主色 swatch）与 DEFAULT_PALETTE_ID，清单与前端 useThemePalette.ts 的 PALETTES 一一对应，供主题管理页渲染调色板选择器。

**入参**

_无路径 / query 参数_

**出参**

`200`


```json
{}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

---

## 主题平台（12）

主题市场与安装管理

### `GET /api/admin/themes`

- **摘要**：获取主题列表（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。按 status（inactive|active|error|installed）与 search（名称/slug 模糊）过滤分页（默认 50 条/页，上限 200）。每项附带该主题当前生效的 mods 值（schema 默认值与 DB 存储值合并结果），供后台主题管理卡片渲染。update_available 与插件侧同口径：磁盘清单版本新于 DB 记录才为 true。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `ThemeListResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object[] | 否 | 当前页主题记录列表，每项附带合并后的 mods 值 |
| has_next | boolean | 否 | 是否还有下一页 |
| page | integer | 否 | 当前页码（从 1 开始） |
| per_page | integer | 否 | 每页条数（上限 200） |
| success | boolean | 是 | 固定为 true（失败走 AppException 错误信封） |
| total | integer | 否 | 符合过滤条件的主题总数 |
| total_pages | integer | 否 | 总页数 = ceil(total / per_page) |

响应示例：

```json
{
  "data": [
    {
      "activated_at": "string",
      "author": "string",
      "author_uri": "string",
      "created_at": "string",
      "description": "string",
      "error_message": "string",
      "folder": "string",
      "id": 0,
      "installed_at": "string",
      "is_active": false,
      "manifest_version": "1.0",
      "mods": "string",
      "mods_schema": "string",
      "name": "string",
      "parent_theme": "string",
      "requires_rosetta": "string",
      "screenshot_urls": [],
      "slug": "string",
      "status": "installed",
      "tags": [],
      "textdomain": "string",
      "theme_uri": "string",
      "update_available": false,
      "updated_at": "string",
      "version": "string"
    }
  ],
  "has_next": false,
  "page": 1,
  "per_page": 50,
  "success": false,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/themes`

- **摘要**：安装主题（local / upload / remote）
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。统一安装入口，由 query 参数 source 决定分支：local=按 JSON body 的 slug 扫描本地目录并登记（缺 slug 422 THEME_SLUG_REQUIRED）；upload=multipart/form-data 上传 zip（缺 file 字段 400 PACKAGE_UPLOAD_FILE_REQUIRED）；remote=按 {remote:{url,checksum_sha256?}} 下载 zip 安装（缺 remote 400 REMOTE_INFO_MISSING）。JSON body 校验失败 422（PAYLOAD_INVALID）；未知 source 400（INVALID_INSTALL_SOURCE）。成功后返回安装完成的主题记录（含合并后的 mods）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `ThemeDetailResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 主题记录，mods 为 schema 默认值与 DB 存值的合并结果 |
| data.activated_at | string \| null | 否 |  |
| data.author | string \| null | 否 |  |
| data.author_uri | string \| null | 否 |  |
| data.created_at | string | 是 |  |
| data.description | string \| null | 否 |  |
| data.error_message | string \| null | 否 |  |
| data.folder | string \| null | 否 |  |
| data.id | integer | 是 |  |
| data.installed_at | string \| null | 否 |  |
| data.is_active | boolean | 否 |  |
| data.manifest_version | string | 否 |  |
| data.mods | object \| null | 否 |  |
| data.mods_schema | object \| null | 否 |  |
| data.name | string | 是 |  |
| data.parent_theme | string \| null | 否 |  |
| data.requires_rosetta | string \| null | 否 |  |
| data.screenshot_urls | string[] | 否 |  |
| data.slug | string | 是 |  |
| data.status | string | 否 |  |
| data.tags | string[] | 否 |  |
| data.textdomain | string \| null | 否 |  |
| data.theme_uri | string \| null | 否 |  |
| data.update_available | boolean | 否 |  |
| data.updated_at | string | 是 |  |
| data.version | string | 是 |  |
| message | string \| null | 否 | 可选提示（如升级端点的「已从磁盘清单重新同步元数据」） |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {
    "activated_at": "string",
    "author": "string",
    "author_uri": "string",
    "created_at": "string",
    "description": "string",
    "error_message": "string",
    "folder": "string",
    "id": 0,
    "installed_at": "string",
    "is_active": false,
    "manifest_version": "1.0",
    "mods": "string",
    "mods_schema": "string",
    "name": "string",
    "parent_theme": "string",
    "requires_rosetta": "string",
    "screenshot_urls": [],
    "slug": "string",
    "status": "installed",
    "tags": [],
    "textdomain": "string",
    "theme_uri": "string",
    "update_available": false,
    "updated_at": "string",
    "version": "string"
  },
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/admin/themes/market`

- **摘要**：获取主题市场索引
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。返回远端主题市场索引（本地缓存 8 小时），force=true 跳过缓存重拉。响应附带 items 列表、total 与 cached_at（缓存时间戳，便于前端展示数据新鲜度）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `ThemeMarketResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 否 | 远端市场索引载荷（插件/主题共用结构）。 |
| data.cached_at | integer \| string \| null | 否 | 索引落盘时间戳（Unix 秒）；旧缓存无该字段时为 null |
| data.index | object | 否 | 完整索引 JSON（含 items 及远端附加元数据；本地缓存 8 小时） |
| data.items | object[] | 否 | 可安装条目列表（每项含 slug/zip_url/checksum_sha256 等）；索引缺 items 时为空数组 |
| data.total | integer | 否 | 条目条数 |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {
    "cached_at": "string",
    "index": {},
    "items": [
      {}
    ],
    "total": 0
  },
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/themes/market/{slug}/install`

- **摘要**：从市场一键安装主题
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。在市场索引（本地缓存 8h）中按 slug 查找条目，复用 install_from_remote 通道下载 zip 并安装（含 SHA-256 校验与 pre-release 开关）。索引缺 items 时 502（MARKET_INDEX_INVALID）；市场无该 slug 时 404（MARKET_ITEM_NOT_FOUND）；条目缺 zip_url 时 502（MARKET_ITEM_MISSING_ZIP_URL）。成功后返回安装完成的主题记录。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `ThemeDetailResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 主题记录，mods 为 schema 默认值与 DB 存值的合并结果 |
| data.activated_at | string \| null | 否 |  |
| data.author | string \| null | 否 |  |
| data.author_uri | string \| null | 否 |  |
| data.created_at | string | 是 |  |
| data.description | string \| null | 否 |  |
| data.error_message | string \| null | 否 |  |
| data.folder | string \| null | 否 |  |
| data.id | integer | 是 |  |
| data.installed_at | string \| null | 否 |  |
| data.is_active | boolean | 否 |  |
| data.manifest_version | string | 否 |  |
| data.mods | object \| null | 否 |  |
| data.mods_schema | object \| null | 否 |  |
| data.name | string | 是 |  |
| data.parent_theme | string \| null | 否 |  |
| data.requires_rosetta | string \| null | 否 |  |
| data.screenshot_urls | string[] | 否 |  |
| data.slug | string | 是 |  |
| data.status | string | 否 |  |
| data.tags | string[] | 否 |  |
| data.textdomain | string \| null | 否 |  |
| data.theme_uri | string \| null | 否 |  |
| data.update_available | boolean | 否 |  |
| data.updated_at | string | 是 |  |
| data.version | string | 是 |  |
| message | string \| null | 否 | 可选提示（如升级端点的「已从磁盘清单重新同步元数据」） |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {
    "activated_at": "string",
    "author": "string",
    "author_uri": "string",
    "created_at": "string",
    "description": "string",
    "error_message": "string",
    "folder": "string",
    "id": 0,
    "installed_at": "string",
    "is_active": false,
    "manifest_version": "1.0",
    "mods": "string",
    "mods_schema": "string",
    "name": "string",
    "parent_theme": "string",
    "requires_rosetta": "string",
    "screenshot_urls": [],
    "slug": "string",
    "status": "installed",
    "tags": [],
    "textdomain": "string",
    "theme_uri": "string",
    "update_available": false,
    "updated_at": "string",
    "version": "string"
  },
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 市场中未找到该主题（error_code: MARKET_ITEM_NOT_FOUND） |
| `422` | Validation Error |
| `502` | 市场索引异常或缺 zip_url（error_code: MARKET_INDEX_INVALID / MARKET_ITEM_MISSING_ZIP_URL） |

### `POST /api/admin/themes/scan`

- **摘要**：扫描本地主题目录
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。扫描 frontend/themes/*/rosetta-theme.json 与 DB 对齐：新增未登记主题、刷新清单变更（version/mods_schema 等）、清理非激活且磁盘已不存在的僵尸记录。返回 added/refreshed/removed 计数。幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `ThemeScanResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 否 | 主题本地目录扫描结果。 |
| data.added | integer | 否 | 新登记进 DB 的主题数 |
| data.refreshed | integer | 否 | 清单变更被刷回 DB 的主题数 |
| data.removed | string[] | 否 | 被清理的僵尸记录 slug 列表（非激活且磁盘已不存在） |
| message | string | 否 | 人类可读的扫描结果摘要（含清理僵尸条数） |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {
    "added": 0,
    "refreshed": 0,
    "removed": [
      "string"
    ]
  },
  "message": "",
  "success": false
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/admin/themes/{slug}`

- **摘要**：获取主题详情（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。返回主题完整记录（含 mods_schema 与当前 mods 值）。主题未安装时返回 404（error_code: THEME_NOT_FOUND）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `ThemeDetailResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 主题记录，mods 为 schema 默认值与 DB 存值的合并结果 |
| data.activated_at | string \| null | 否 |  |
| data.author | string \| null | 否 |  |
| data.author_uri | string \| null | 否 |  |
| data.created_at | string | 是 |  |
| data.description | string \| null | 否 |  |
| data.error_message | string \| null | 否 |  |
| data.folder | string \| null | 否 |  |
| data.id | integer | 是 |  |
| data.installed_at | string \| null | 否 |  |
| data.is_active | boolean | 否 |  |
| data.manifest_version | string | 否 |  |
| data.mods | object \| null | 否 |  |
| data.mods_schema | object \| null | 否 |  |
| data.name | string | 是 |  |
| data.parent_theme | string \| null | 否 |  |
| data.requires_rosetta | string \| null | 否 |  |
| data.screenshot_urls | string[] | 否 |  |
| data.slug | string | 是 |  |
| data.status | string | 否 |  |
| data.tags | string[] | 否 |  |
| data.textdomain | string \| null | 否 |  |
| data.theme_uri | string \| null | 否 |  |
| data.update_available | boolean | 否 |  |
| data.updated_at | string | 是 |  |
| data.version | string | 是 |  |
| message | string \| null | 否 | 可选提示（如升级端点的「已从磁盘清单重新同步元数据」） |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {
    "activated_at": "string",
    "author": "string",
    "author_uri": "string",
    "created_at": "string",
    "description": "string",
    "error_message": "string",
    "folder": "string",
    "id": 0,
    "installed_at": "string",
    "is_active": false,
    "manifest_version": "1.0",
    "mods": "string",
    "mods_schema": "string",
    "name": "string",
    "parent_theme": "string",
    "requires_rosetta": "string",
    "screenshot_urls": [],
    "slug": "string",
    "status": "installed",
    "tags": [],
    "textdomain": "string",
    "theme_uri": "string",
    "update_available": false,
    "updated_at": "string",
    "version": "string"
  },
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 主题不存在（error_code: THEME_NOT_FOUND） |
| `422` | Validation Error |

### `DELETE /api/admin/themes/{slug}`

- **摘要**：删除主题记录
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。404/409 判定统一在 ThemeManager.delete 内：未安装 → 404 THEME_NOT_FOUND；仍为激活主题 → 409 THEME_ALREADY_ACTIVE（须先激活其他主题）。仅清除 DB 记录，不删除磁盘文件（磁盘 ↔ DB 由扫描同步）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PackageMessageResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 | 人类可读结果（如「已删除」「升级完成 (stub)」） |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "message": "",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 主题未安装（error_code: THEME_NOT_FOUND） |
| `409` | 主题处于激活态，禁止删除（error_code: THEME_ALREADY_ACTIVE） |
| `422` | Validation Error |

### `PUT /api/admin/themes/{slug}/activate`

- **摘要**：激活主题
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。同一站点同时只有一个：激活新主题时旧激活项自动降为 installed。幂等：目标主题已激活时直接返回现状（不刷新 activated_at、不重放钩子）。成功后清空前台页面缓存，前台经 GET /api/themes/active 拉取新 slug 与 mods。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `ThemeDetailResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 主题记录，mods 为 schema 默认值与 DB 存值的合并结果 |
| data.activated_at | string \| null | 否 |  |
| data.author | string \| null | 否 |  |
| data.author_uri | string \| null | 否 |  |
| data.created_at | string | 是 |  |
| data.description | string \| null | 否 |  |
| data.error_message | string \| null | 否 |  |
| data.folder | string \| null | 否 |  |
| data.id | integer | 是 |  |
| data.installed_at | string \| null | 否 |  |
| data.is_active | boolean | 否 |  |
| data.manifest_version | string | 否 |  |
| data.mods | object \| null | 否 |  |
| data.mods_schema | object \| null | 否 |  |
| data.name | string | 是 |  |
| data.parent_theme | string \| null | 否 |  |
| data.requires_rosetta | string \| null | 否 |  |
| data.screenshot_urls | string[] | 否 |  |
| data.slug | string | 是 |  |
| data.status | string | 否 |  |
| data.tags | string[] | 否 |  |
| data.textdomain | string \| null | 否 |  |
| data.theme_uri | string \| null | 否 |  |
| data.update_available | boolean | 否 |  |
| data.updated_at | string | 是 |  |
| data.version | string | 是 |  |
| message | string \| null | 否 | 可选提示（如升级端点的「已从磁盘清单重新同步元数据」） |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {
    "activated_at": "string",
    "author": "string",
    "author_uri": "string",
    "created_at": "string",
    "description": "string",
    "error_message": "string",
    "folder": "string",
    "id": 0,
    "installed_at": "string",
    "is_active": false,
    "manifest_version": "1.0",
    "mods": "string",
    "mods_schema": "string",
    "name": "string",
    "parent_theme": "string",
    "requires_rosetta": "string",
    "screenshot_urls": [],
    "slug": "string",
    "status": "installed",
    "tags": [],
    "textdomain": "string",
    "theme_uri": "string",
    "update_available": false,
    "updated_at": "string",
    "version": "string"
  },
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 主题未安装（error_code: THEME_NOT_FOUND） |
| `422` | Validation Error |

### `GET /api/admin/themes/{slug}/mods`

- **摘要**：获取主题 Mods 与 Schema
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。返回 mods（schema 默认值与 DB 已存值的合并结果）与 mods_schema（JSON Schema Draft-07）。mods_schema.properties 是 Customizer 控件的唯一清单。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `ThemeModsResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 否 | ``GET /api/admin/themes/{slug}/mods`` 的 data 载荷。 |
| data.mods | object | 否 | schema 默认值与 DB 已存值的合并结果 |
| data.mods_schema | object \| null | 否 | JSON Schema Draft-07 声明；properties 是 Customizer 控件的唯一清单 |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {
    "mods": {},
    "mods_schema": "string"
  },
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 主题未安装（error_code: THEME_NOT_FOUND） |
| `422` | Validation Error |

### `PUT /api/admin/themes/{slug}/mods`

- **摘要**：全量替换主题 Mods
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。PUT 全量替换语义：先重置为 mods_schema 声明的默认值，再叠加 payload.mods。schema 未声明的键被静默丢弃（仅记 warning，不整单拒绝）；payload.mods 非 JSON 对象在请求 schema 层拒绝，返回 422（error_code: VALIDATION_ERROR）；合并值违反 schema 约束（如越界数字）返回 400（error_code: MODS_SCHEMA_VIOLATION）。写入 SiteConfig KV theme_mods:<slug>，成功后清空前台页面缓存。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `ThemeModsIn`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| mods | object | 是 |  |

```json
{
  "mods": {}
}
```

**出参**

`200` · 模型 `ThemeModsSavedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 否 | 保存后的最终 mods（schema 未声明的键已被静默丢弃） |
| success | boolean | 是 | 固定为 true（写库成功且已清空前台页面缓存） |

响应示例：

```json
{
  "data": {},
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `400` | mods 违反 mods_schema 约束（error_code: MODS_SCHEMA_VIOLATION） |
| `404` | 主题未安装（error_code: THEME_NOT_FOUND） |
| `422` | Validation Error |

### `PATCH /api/admin/themes/{slug}/mods`

- **摘要**：增量更新主题 Mods
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。在现有值上仅覆盖 payload.mods 出现的键，其余保持不变；schema 未声明的键同样被静默丢弃；payload.mods 非 JSON 对象在请求 schema 层拒绝，返回 422（error_code: VALIDATION_ERROR）；合并值违反 schema 约束返回 400（error_code: MODS_SCHEMA_VIOLATION）。成功后清空前台页面缓存。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `ThemeModsIn`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| mods | object | 是 |  |

```json
{
  "mods": {}
}
```

**出参**

`200` · 模型 `ThemeModsSavedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 否 | 保存后的最终 mods（schema 未声明的键已被静默丢弃） |
| success | boolean | 是 | 固定为 true（写库成功且已清空前台页面缓存） |

响应示例：

```json
{
  "data": {},
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `400` | mods 违反 mods_schema 约束（error_code: MODS_SCHEMA_VIOLATION） |
| `404` | 主题未安装（error_code: THEME_NOT_FOUND） |
| `422` | Validation Error |

### `POST /api/admin/themes/{slug}/upgrade`

- **摘要**：升级主题（重扫磁盘清单）
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。主题没有独立的下载通道：升级 = 重新扫描磁盘清单并把 version / mods_schema 等元数据刷回 DB（zip 覆盖安装请走 POST /themes?source=upload|remote）。version 变化会使前台 <link> 的 ?v= bust 参数失效，故同步清空前台页面缓存。主题未安装时由 ThemeManager 抛出 404（error_code: THEME_NOT_FOUND）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `ThemeDetailResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 主题记录，mods 为 schema 默认值与 DB 存值的合并结果 |
| data.activated_at | string \| null | 否 |  |
| data.author | string \| null | 否 |  |
| data.author_uri | string \| null | 否 |  |
| data.created_at | string | 是 |  |
| data.description | string \| null | 否 |  |
| data.error_message | string \| null | 否 |  |
| data.folder | string \| null | 否 |  |
| data.id | integer | 是 |  |
| data.installed_at | string \| null | 否 |  |
| data.is_active | boolean | 否 |  |
| data.manifest_version | string | 否 |  |
| data.mods | object \| null | 否 |  |
| data.mods_schema | object \| null | 否 |  |
| data.name | string | 是 |  |
| data.parent_theme | string \| null | 否 |  |
| data.requires_rosetta | string \| null | 否 |  |
| data.screenshot_urls | string[] | 否 |  |
| data.slug | string | 是 |  |
| data.status | string | 否 |  |
| data.tags | string[] | 否 |  |
| data.textdomain | string \| null | 否 |  |
| data.theme_uri | string \| null | 否 |  |
| data.update_available | boolean | 否 |  |
| data.updated_at | string | 是 |  |
| data.version | string | 是 |  |
| message | string \| null | 否 | 可选提示（如升级端点的「已从磁盘清单重新同步元数据」） |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {
    "activated_at": "string",
    "author": "string",
    "author_uri": "string",
    "created_at": "string",
    "description": "string",
    "error_message": "string",
    "folder": "string",
    "id": 0,
    "installed_at": "string",
    "is_active": false,
    "manifest_version": "1.0",
    "mods": "string",
    "mods_schema": "string",
    "name": "string",
    "parent_theme": "string",
    "requires_rosetta": "string",
    "screenshot_urls": [],
    "slug": "string",
    "status": "installed",
    "tags": [],
    "textdomain": "string",
    "theme_uri": "string",
    "update_available": false,
    "updated_at": "string",
    "version": "string"
  },
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 主题未安装（error_code: THEME_NOT_FOUND） |
| `422` | Validation Error |

---

## 插件平台（16）

插件市场与安装管理

### `GET /api/admin/plugins`

- **摘要**：获取插件列表（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。按 status（inactive|active|error|installed）与 search（名称/slug 模糊）过滤分页（默认 20 条/页，上限 100）。每项附带当前 settings（单插件读取失败时置 null，不影响整体列表）。update_available 由磁盘清单版本与 DB 版本比对得出 —— 与「升级=回读磁盘清单」同口径，磁盘缺目录时为 false（升级本来做不了）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PluginListResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object[] | 否 | 当前页插件记录列表 |
| has_next | boolean | 否 | 是否还有下一页 |
| page | integer | 否 | 当前页码（从 1 开始） |
| per_page | integer | 否 | 每页条数（上限 100） |
| success | boolean | 是 | 固定为 true（失败走 AppException 错误信封） |
| total | integer | 否 | 符合过滤条件的插件总数 |
| total_pages | integer | 否 | 总页数 = ceil(total / per_page) |

响应示例：

```json
{
  "data": [
    {
      "activated_at": "string",
      "author": "string",
      "author_uri": "string",
      "created_at": "string",
      "description": "string",
      "error_message": "string",
      "folder": "string",
      "id": 0,
      "install_path": "string",
      "installed_at": "string",
      "manifest_version": "1.0",
      "name": "string",
      "plugin_uri": "string",
      "requires_rosetta": "string",
      "settings": "string",
      "settings_schema": "string",
      "slug": "string",
      "status": "inactive",
      "textdomain": "string",
      "update_available": false,
      "updated_at": "string",
      "version": "string"
    }
  ],
  "has_next": false,
  "page": 1,
  "per_page": 20,
  "success": false,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/plugins`

- **摘要**：安装插件（local / upload / remote）
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。统一安装入口，由 query 参数 source 决定分支：local=按 JSON body 的 slug 扫描本地目录并登记；upload=multipart/form-data 上传 zip（缺 file 字段 400 PACKAGE_UPLOAD_FILE_REQUIRED）；remote=按 {remote:{url,checksum_sha256?}}下载 zip 安装（缺 remote 400 REMOTE_INFO_MISSING）。JSON body 校验失败 422（PAYLOAD_INVALID）；source=local 缺 slug 422（PLUGIN_SLUG_REQUIRED）；未知 source 400（INVALID_INSTALL_SOURCE）。成功后返回安装完成的插件记录。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PluginDetailResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 插件记录（列表/详情场景附带 settings，读取失败时为 null） |
| data.activated_at | string \| null | 否 |  |
| data.author | string \| null | 否 |  |
| data.author_uri | string \| null | 否 |  |
| data.created_at | string | 是 |  |
| data.description | string \| null | 否 |  |
| data.error_message | string \| null | 否 |  |
| data.folder | string \| null | 否 |  |
| data.id | integer | 是 |  |
| data.install_path | string \| null | 否 |  |
| data.installed_at | string \| null | 否 |  |
| data.manifest_version | string | 否 |  |
| data.name | string | 是 |  |
| data.plugin_uri | string \| null | 否 |  |
| data.requires_rosetta | string \| null | 否 |  |
| data.settings | object \| null | 否 |  |
| data.settings_schema | object \| null | 否 |  |
| data.slug | string | 是 |  |
| data.status | string | 否 |  |
| data.textdomain | string \| null | 否 |  |
| data.update_available | boolean | 否 |  |
| data.updated_at | string | 是 |  |
| data.version | string | 是 |  |
| message | string \| null | 否 | 可选提示（如幂等分支的「插件已处于目标状态」），常规成功时缺席 |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {
    "activated_at": "string",
    "author": "string",
    "author_uri": "string",
    "created_at": "string",
    "description": "string",
    "error_message": "string",
    "folder": "string",
    "id": 0,
    "install_path": "string",
    "installed_at": "string",
    "manifest_version": "1.0",
    "name": "string",
    "plugin_uri": "string",
    "requires_rosetta": "string",
    "settings": "string",
    "settings_schema": "string",
    "slug": "string",
    "status": "inactive",
    "textdomain": "string",
    "update_available": false,
    "updated_at": "string",
    "version": "string"
  },
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/plugins/bulk`

- **摘要**：批量插件操作
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。请求体 {action: activate|deactivate|delete|upgrade, slugs:[...]}，action 越界在 Pydantic 层即 422（VALIDATION_ERROR）。逐插件执行：单个失败不中断整体，失败项以 {slug, error_code, message} 汇总在 data 中返回。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `PluginBulkIn`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| action | enum(`activate`, `deactivate`, `delete`, `upgrade`) | 是 |  |
| slugs | string[] | 是 |  |

```json
{
  "action": "activate",
  "slugs": [
    "string"
  ]
}
```

**出参**

`200` · 模型 `PluginBulkResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 否 | total/success/failed 计数；errors 为 [{slug, error_code, message}] 列表，全部成功时为 null |
| data.errors | object[] \| null | 否 |  |
| data.failed | integer | 是 |  |
| data.success | integer | 是 |  |
| data.total | integer | 是 |  |
| success | boolean | 是 | 固定为 true（个别插件失败不影响整体 200） |

响应示例：

```json
{
  "data": {
    "errors": "string",
    "failed": 0,
    "success": 0,
    "total": 0
  },
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/admin/plugins/market`

- **摘要**：获取插件市场索引
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。返回远端插件市场索引（本地缓存 8 小时），force=true 跳过缓存重新拉取。响应附带 items 列表、total 与 cached_at。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PluginMarketResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 否 | 远端市场索引载荷（插件/主题共用结构）。 |
| data.cached_at | integer \| string \| null | 否 | 索引落盘时间戳（Unix 秒）；旧缓存无该字段时为 null |
| data.index | object | 否 | 完整索引 JSON（含 items 及远端附加元数据；本地缓存 8 小时） |
| data.items | object[] | 否 | 可安装条目列表（每项含 slug/zip_url/checksum_sha256 等）；索引缺 items 时为空数组 |
| data.total | integer | 否 | 条目条数 |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {
    "cached_at": "string",
    "index": {},
    "items": [
      {}
    ],
    "total": 0
  },
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/plugins/market/{slug}/install`

- **摘要**：从市场一键安装插件
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。在市场索引（本地缓存 8h）中按 slug 查找条目，复用 install_from_remote 通道下载 zip 并安装（含 SHA-256 校验与 pre-release 开关）。索引缺 items 时 502（MARKET_INDEX_INVALID）；市场无该 slug 时 404（MARKET_ITEM_NOT_FOUND）；条目缺 zip_url 时 502（MARKET_ITEM_MISSING_ZIP_URL）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PluginDetailResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 插件记录（列表/详情场景附带 settings，读取失败时为 null） |
| data.activated_at | string \| null | 否 |  |
| data.author | string \| null | 否 |  |
| data.author_uri | string \| null | 否 |  |
| data.created_at | string | 是 |  |
| data.description | string \| null | 否 |  |
| data.error_message | string \| null | 否 |  |
| data.folder | string \| null | 否 |  |
| data.id | integer | 是 |  |
| data.install_path | string \| null | 否 |  |
| data.installed_at | string \| null | 否 |  |
| data.manifest_version | string | 否 |  |
| data.name | string | 是 |  |
| data.plugin_uri | string \| null | 否 |  |
| data.requires_rosetta | string \| null | 否 |  |
| data.settings | object \| null | 否 |  |
| data.settings_schema | object \| null | 否 |  |
| data.slug | string | 是 |  |
| data.status | string | 否 |  |
| data.textdomain | string \| null | 否 |  |
| data.update_available | boolean | 否 |  |
| data.updated_at | string | 是 |  |
| data.version | string | 是 |  |
| message | string \| null | 否 | 可选提示（如幂等分支的「插件已处于目标状态」），常规成功时缺席 |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {
    "activated_at": "string",
    "author": "string",
    "author_uri": "string",
    "created_at": "string",
    "description": "string",
    "error_message": "string",
    "folder": "string",
    "id": 0,
    "install_path": "string",
    "installed_at": "string",
    "manifest_version": "1.0",
    "name": "string",
    "plugin_uri": "string",
    "requires_rosetta": "string",
    "settings": "string",
    "settings_schema": "string",
    "slug": "string",
    "status": "inactive",
    "textdomain": "string",
    "update_available": false,
    "updated_at": "string",
    "version": "string"
  },
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 市场中未找到该插件（error_code: MARKET_ITEM_NOT_FOUND） |
| `422` | Validation Error |
| `502` | 市场索引异常或缺 zip_url（error_code: MARKET_INDEX_INVALID / MARKET_ITEM_MISSING_ZIP_URL） |

### `GET /api/admin/plugins/menu-registry`

- **摘要**：获取插件后台菜单注册表
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。返回已激活插件经 routing_registry 声明的后台菜单项（Sidebar「插件」分组数据源），每项附带其 admin_route_prefix。只读、幂等。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PluginMenuRegistryResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 否 | ``GET /api/admin/plugins/menu-registry`` 的 data 载荷。 |
| data.items | object[] | 否 | 菜单项列表 |
| data.total | integer | 否 | 菜单项条数 |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {
    "items": [
      {
        "admin_route_prefix": "…",
        "badge": "…",
        "extras": "…",
        "icon": "…",
        "label": "…",
        "path": "…",
        "slug": "…"
      }
    ],
    "total": 0
  },
  "success": false
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `POST /api/admin/plugins/scan`

- **摘要**：扫描本地插件目录
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。扫描 backend/plugins/*/rosetta-plugin.json 与 DB 对齐：登记新插件、刷新清单变更。返回 added/refreshed 计数。幂等，可安全重复调用。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PluginScanResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 否 | 插件本地目录扫描计数。 |
| data.added | integer | 否 | 新登记进 DB 的插件数 |
| data.refreshed | integer | 否 | 清单变更被刷回 DB 的插件数 |
| message | string | 否 | 人类可读的扫描结果摘要（含新增/更新计数） |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {
    "added": 0,
    "refreshed": 0
  },
  "message": "",
  "success": false
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/admin/plugins/{slug}`

- **摘要**：获取插件详情（管理员）
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。返回插件记录（PluginOut）并附带当前 settings；settings 读取失败时置 null 而不报错。未安装时 404（error_code: PLUGIN_NOT_FOUND）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PluginDetailResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 插件记录（列表/详情场景附带 settings，读取失败时为 null） |
| data.activated_at | string \| null | 否 |  |
| data.author | string \| null | 否 |  |
| data.author_uri | string \| null | 否 |  |
| data.created_at | string | 是 |  |
| data.description | string \| null | 否 |  |
| data.error_message | string \| null | 否 |  |
| data.folder | string \| null | 否 |  |
| data.id | integer | 是 |  |
| data.install_path | string \| null | 否 |  |
| data.installed_at | string \| null | 否 |  |
| data.manifest_version | string | 否 |  |
| data.name | string | 是 |  |
| data.plugin_uri | string \| null | 否 |  |
| data.requires_rosetta | string \| null | 否 |  |
| data.settings | object \| null | 否 |  |
| data.settings_schema | object \| null | 否 |  |
| data.slug | string | 是 |  |
| data.status | string | 否 |  |
| data.textdomain | string \| null | 否 |  |
| data.update_available | boolean | 否 |  |
| data.updated_at | string | 是 |  |
| data.version | string | 是 |  |
| message | string \| null | 否 | 可选提示（如幂等分支的「插件已处于目标状态」），常规成功时缺席 |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {
    "activated_at": "string",
    "author": "string",
    "author_uri": "string",
    "created_at": "string",
    "description": "string",
    "error_message": "string",
    "folder": "string",
    "id": 0,
    "install_path": "string",
    "installed_at": "string",
    "manifest_version": "1.0",
    "name": "string",
    "plugin_uri": "string",
    "requires_rosetta": "string",
    "settings": "string",
    "settings_schema": "string",
    "slug": "string",
    "status": "inactive",
    "textdomain": "string",
    "update_available": false,
    "updated_at": "string",
    "version": "string"
  },
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 插件不存在（error_code: PLUGIN_NOT_FOUND） |
| `422` | Validation Error |

### `DELETE /api/admin/plugins/{slug}`

- **摘要**：删除插件
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。删除 DB 记录与 settings KV，并失效已渲染内容/页面缓存（防 TTL 内访客仍见已删插件的钩子输出）；仅安装态（非 active）可删，激活中返回 409（PLUGIN_ALREADY_ACTIVE，需先停用）。未安装时 404（error_code: PLUGIN_NOT_FOUND）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PackageMessageResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 | 人类可读结果（如「已删除」「升级完成 (stub)」） |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "message": "",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 插件不存在（error_code: PLUGIN_NOT_FOUND） |
| `409` | 插件处于激活态，禁止删除（error_code: PLUGIN_ALREADY_ACTIVE） |
| `422` | Validation Error |

### `POST /api/admin/plugins/{slug}/activate`

- **摘要**：激活插件
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。加载插件包并执行 register/activate 钩子（Bus 模式，见 core/plugin_loader + plugin_bus）。幂等：已激活时直接返回现状（success=true，不报错）。激活后失效已渲染文章缓存。未安装 404（PLUGIN_NOT_FOUND）；导入/初始化失败 500（PLUGIN_IMPORT_ERROR）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PluginDetailResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 插件记录（列表/详情场景附带 settings，读取失败时为 null） |
| data.activated_at | string \| null | 否 |  |
| data.author | string \| null | 否 |  |
| data.author_uri | string \| null | 否 |  |
| data.created_at | string | 是 |  |
| data.description | string \| null | 否 |  |
| data.error_message | string \| null | 否 |  |
| data.folder | string \| null | 否 |  |
| data.id | integer | 是 |  |
| data.install_path | string \| null | 否 |  |
| data.installed_at | string \| null | 否 |  |
| data.manifest_version | string | 否 |  |
| data.name | string | 是 |  |
| data.plugin_uri | string \| null | 否 |  |
| data.requires_rosetta | string \| null | 否 |  |
| data.settings | object \| null | 否 |  |
| data.settings_schema | object \| null | 否 |  |
| data.slug | string | 是 |  |
| data.status | string | 否 |  |
| data.textdomain | string \| null | 否 |  |
| data.update_available | boolean | 否 |  |
| data.updated_at | string | 是 |  |
| data.version | string | 是 |  |
| message | string \| null | 否 | 可选提示（如幂等分支的「插件已处于目标状态」），常规成功时缺席 |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {
    "activated_at": "string",
    "author": "string",
    "author_uri": "string",
    "created_at": "string",
    "description": "string",
    "error_message": "string",
    "folder": "string",
    "id": 0,
    "install_path": "string",
    "installed_at": "string",
    "manifest_version": "1.0",
    "name": "string",
    "plugin_uri": "string",
    "requires_rosetta": "string",
    "settings": "string",
    "settings_schema": "string",
    "slug": "string",
    "status": "inactive",
    "textdomain": "string",
    "update_available": false,
    "updated_at": "string",
    "version": "string"
  },
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 插件不存在（error_code: PLUGIN_NOT_FOUND） |
| `422` | Validation Error |

### `POST /api/admin/plugins/{slug}/deactivate`

- **摘要**：停用插件
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。执行插件 deactivate 钩子并置为禁用态。幂等：本就未激活时直接返回现状（success=true，不报错）。停用后失效已渲染文章缓存。未安装时 404（error_code: PLUGIN_NOT_FOUND）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PluginDeactivateResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 否 | 停用后的插件记录：幂等分支为 PluginOut 序列化结果；真实停用分支当前直接序列化 ORM 行（键为表列名超集，如含 site_id/settings_schema） |
| message | string \| null | 否 | 幂等分支的提示语，真实停用时缺席 |
| success | boolean | 是 | 固定为 true（本就未激活时同样返回成功，幂等） |

响应示例：

```json
{
  "data": {},
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 插件不存在（error_code: PLUGIN_NOT_FOUND） |
| `422` | Validation Error |

### `GET /api/admin/plugins/{slug}/settings`

- **摘要**：获取插件设置
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。返回该插件在 SiteConfig 中持久化的 settings（已应用 schema 默认值）。未安装时 404（error_code: PLUGIN_NOT_FOUND）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PluginSettingsResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 否 | 插件设置键值对（settings_schema.properties 是合法键的唯一清单，已应用 schema 默认值） |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {},
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 插件不存在（error_code: PLUGIN_NOT_FOUND） |
| `422` | Validation Error |

### `PUT /api/admin/plugins/{slug}/settings`

- **摘要**：全量替换插件设置
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。PUT 全量替换语义：先重置为 settings_schema 声明的默认值，再叠加 payload.settings 后整体保存。保存后立即刷新插件运行时 settings 快照（plugin_loader.set_settings_snapshot），无需重启；并失效已渲染文章缓存（设置可影响 filter 输出）。未安装 404（PLUGIN_NOT_FOUND）；保存校验失败 400（PLUGIN_SETTINGS_INVALID）。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `PluginConfigIn`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| settings | object | 是 |  |
| slug | string \| null | 否 |  |

```json
{
  "settings": {},
  "slug": "string"
}
```

**出参**

`200` · 模型 `PluginSettingsResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 否 | 插件设置键值对（settings_schema.properties 是合法键的唯一清单，已应用 schema 默认值） |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {},
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 插件不存在（error_code: PLUGIN_NOT_FOUND） |
| `422` | Validation Error |

### `PATCH /api/admin/plugins/{slug}/settings`

- **摘要**：增量更新插件设置
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。仅覆盖 payload.settings 中出现的键，其余保持现值。保存后立即刷新运行时 settings 快照，并失效已渲染文章缓存。未安装 404（PLUGIN_NOT_FOUND）；保存校验失败 400（PLUGIN_SETTINGS_INVALID）。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `PluginConfigIn`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| settings | object | 是 |  |
| slug | string \| null | 否 |  |

```json
{
  "settings": {},
  "slug": "string"
}
```

**出参**

`200` · 模型 `PluginSettingsResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 否 | 插件设置键值对（settings_schema.properties 是合法键的唯一清单，已应用 schema 默认值） |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {},
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 插件不存在（error_code: PLUGIN_NOT_FOUND） |
| `422` | Validation Error |

### `PATCH /api/admin/plugins/{slug}/status`

- **摘要**：切换插件启用状态
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。请求体 {enabled: true|false}。幂等：插件已处于目标状态时直接返回现状并附 message，不抛 4xx，保证前端 Switch 二次触发与客户端重试安全。状态真实变化时失效文章详情/列表/RSS 与前端页面缓存，钩子渲染结果即刻生效。未安装时 404（error_code: PLUGIN_NOT_FOUND）。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `PluginStatusToggleIn`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| enabled | boolean | 是 |  |

```json
{
  "enabled": false
}
```

**出参**

`200` · 模型 `PluginDetailResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 插件记录（列表/详情场景附带 settings，读取失败时为 null） |
| data.activated_at | string \| null | 否 |  |
| data.author | string \| null | 否 |  |
| data.author_uri | string \| null | 否 |  |
| data.created_at | string | 是 |  |
| data.description | string \| null | 否 |  |
| data.error_message | string \| null | 否 |  |
| data.folder | string \| null | 否 |  |
| data.id | integer | 是 |  |
| data.install_path | string \| null | 否 |  |
| data.installed_at | string \| null | 否 |  |
| data.manifest_version | string | 否 |  |
| data.name | string | 是 |  |
| data.plugin_uri | string \| null | 否 |  |
| data.requires_rosetta | string \| null | 否 |  |
| data.settings | object \| null | 否 |  |
| data.settings_schema | object \| null | 否 |  |
| data.slug | string | 是 |  |
| data.status | string | 否 |  |
| data.textdomain | string \| null | 否 |  |
| data.update_available | boolean | 否 |  |
| data.updated_at | string | 是 |  |
| data.version | string | 是 |  |
| message | string \| null | 否 | 可选提示（如幂等分支的「插件已处于目标状态」），常规成功时缺席 |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {
    "activated_at": "string",
    "author": "string",
    "author_uri": "string",
    "created_at": "string",
    "description": "string",
    "error_message": "string",
    "folder": "string",
    "id": 0,
    "install_path": "string",
    "installed_at": "string",
    "manifest_version": "1.0",
    "name": "string",
    "plugin_uri": "string",
    "requires_rosetta": "string",
    "settings": "string",
    "settings_schema": "string",
    "slug": "string",
    "status": "inactive",
    "textdomain": "string",
    "update_available": false,
    "updated_at": "string",
    "version": "string"
  },
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 插件不存在（error_code: PLUGIN_NOT_FOUND） |
| `422` | Validation Error |

### `POST /api/admin/plugins/{slug}/upgrade`

- **摘要**：升级插件（从磁盘清单重新同步元数据）
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。升级 = 重新扫描磁盘清单并把已替换的元数据（版本/名称/settings_schema 等）刷回 DB，与主题侧 `POST /themes/{slug}/upgrade` 同口径；真正的版本包替换走 zip 覆盖安装（POST /plugins?source=upload|remote）。响应 data 为同步后的插件记录。未安装 404（PLUGIN_NOT_FOUND）；磁盘目录已缺失（清理后不可升级）同样 404，message 提示重新安装。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PluginDetailResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 插件记录（列表/详情场景附带 settings，读取失败时为 null） |
| data.activated_at | string \| null | 否 |  |
| data.author | string \| null | 否 |  |
| data.author_uri | string \| null | 否 |  |
| data.created_at | string | 是 |  |
| data.description | string \| null | 否 |  |
| data.error_message | string \| null | 否 |  |
| data.folder | string \| null | 否 |  |
| data.id | integer | 是 |  |
| data.install_path | string \| null | 否 |  |
| data.installed_at | string \| null | 否 |  |
| data.manifest_version | string | 否 |  |
| data.name | string | 是 |  |
| data.plugin_uri | string \| null | 否 |  |
| data.requires_rosetta | string \| null | 否 |  |
| data.settings | object \| null | 否 |  |
| data.settings_schema | object \| null | 否 |  |
| data.slug | string | 是 |  |
| data.status | string | 否 |  |
| data.textdomain | string \| null | 否 |  |
| data.update_available | boolean | 否 |  |
| data.updated_at | string | 是 |  |
| data.version | string | 是 |  |
| message | string \| null | 否 | 可选提示（如幂等分支的「插件已处于目标状态」），常规成功时缺席 |
| success | boolean | 是 | 固定为 true |

响应示例：

```json
{
  "data": {
    "activated_at": "string",
    "author": "string",
    "author_uri": "string",
    "created_at": "string",
    "description": "string",
    "error_message": "string",
    "folder": "string",
    "id": 0,
    "install_path": "string",
    "installed_at": "string",
    "manifest_version": "1.0",
    "name": "string",
    "plugin_uri": "string",
    "requires_rosetta": "string",
    "settings": "string",
    "settings_schema": "string",
    "slug": "string",
    "status": "inactive",
    "textdomain": "string",
    "update_available": false,
    "updated_at": "string",
    "version": "string"
  },
  "message": "string",
  "success": false
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `404` | 插件不存在或磁盘目录缺失（error_code: PLUGIN_NOT_FOUND） |
| `422` | Validation Error |

---

## 开发文档（2）

API 文档与开发指南

### `GET /api/docs/list`

- **摘要**：列出所有开发文档条目
- **鉴权**：公开接口（无需鉴权）

返回菜单排序、分类与描述；用于侧边栏 / TOC 渲染。公开接口、无需鉴权。响应为 success/data 信封，data.items 按 order 升序，available 反映磁盘文件是否存在。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `DocListResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 目录接口的 data 载荷。 |
| data.items | object[] | 否 | 按 order 升序的条目 |
| data.language | string | 否 | 文档语言标识（当前内建目录仅中文，固定值） |
| success | boolean | 否 | 固定为 true（本接口成功路径无分支） |

响应示例：

```json
{
  "data": {
    "items": [
      {
        "available": "…",
        "category": "…",
        "description": "…",
        "order": "…",
        "slug": "…",
        "title": "…"
      }
    ],
    "language": "zh-CN"
  },
  "success": true
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/docs/{slug}`

- **摘要**：读取单篇文档
- **鉴权**：公开接口（无需鉴权）

返回 {markdown, title}；markdown 为原始 Markdown 文本，由前端 marked + highlight.js 渲染为 HTML。响应为 success/data 信封（data 含 slug/title/markdown/language）；slug 未注册或磁盘文件缺失返回 404 错误信封。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `DocDetailResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | 单篇文档接口的 data 载荷。 |
| data.language | string | 否 | 文档语言标识（固定值） |
| data.markdown | string | 是 | 原始 Markdown 全文，由前端 marked + highlight.js 渲染 |
| data.slug | string | 是 | 请求的文档 slug |
| data.title | string | 是 | 优先取 Markdown 首个 H1，缺省回退目录标题/slug |
| success | boolean | 否 | 固定为 true（slug 未注册 / 文件缺失走 404 错误信封） |

响应示例：

```json
{
  "data": {
    "language": "zh-CN",
    "markdown": "string",
    "slug": "string",
    "title": "string"
  },
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## Bing壁纸（5）

Bing 每日壁纸获取

### `GET /api/bing/image`

- **摘要**：Bing 图片流式代理 + 本地缓存
- **鉴权**：公开接口（无需鉴权）

图片代理端点：src 参数是原始图片地址的标准 base64（可含 URL 安全字符替换），解码失败、非 http(s) 协议或上游拉取失败时，一律 307 跳到站内兜底图，绝不 302 跳外部地址，以防被当作开放重定向使用。命中本地缓存或下载成功后以文件直出，Content-Type 取自落盘扩展名，带 Cache-Control: public, max-age=2592000, immutable（30 天强缓存）与 nosniff。上游只允许 Bing / Microsoft 白名单域名，且经 SSRF 校验（拒内网、逐跳校验重定向）；响应 Content-Type 必须是 image/*，否则不落盘直接走兜底。公开访问、无需鉴权。

**入参**

_无路径 / query 参数_

**出参**

`200` · 无响应体（或响应类型未在 OpenAPI 中声明）

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/bing/image/archive`

- **摘要**：获取 Bing 最近 N 天图片归档（骨架）
- **鉴权**：公开接口（无需鉴权）

返回最近 days 天的图片元数据列表，公开访问、无需鉴权。实现是串行请求上游归档接口（每天一次请求、每请求间隔 50ms，单次超时 10 秒），days 取值 1..14，越界由框架返回 422；因此大天数会显著拉长响应时间。上游不可用或某天缺数据时跳过该天，count 可能小于 days；整体异常同样返回 200，只带已抓到的部分（可能是空数组）。无服务端缓存。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BingArchiveResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| count | integer | 否 | data 的实际长度，可能小于请求参数 days |
| data | object[] | 否 | 归档条目，按请求天数从新到旧排列；上游非 200 或当天无数据的天会被跳过，因此条数可能少于请求的 days，异常时可为空数组 |
| success | boolean | 否 | 恒为 true：整体异常被吞掉并返回已抓到的部分 |

响应示例：

```json
{
  "count": 0,
  "data": [
    {
      "copyright": "string",
      "date": "string",
      "title": "string",
      "url": "string",
      "url_uhd": "string"
    }
  ],
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/bing/image/today`

- **摘要**：获取 Bing 今日图元数据
- **鉴权**：公开接口（无需鉴权）

从 Bing 首页图像元数据接口抓取今日信息，公开访问、无需鉴权。上游请求超时上限 8 秒；任何上游异常都不返回错误码，而是带 fallback 标记返回一条 data: URI 占位图，保证前端不崩。结果不做服务端缓存，每次请求都会打上游。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BingTodayResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| data | object | 是 | Bing 每日一图的元数据条目（对上游 URL 拼装后的结果，不含图片本体）。 |
| data.copyright | string \| null | 否 | 上游版权署名文字；上游未提供时为 null |
| data.date | string | 是 | YYYY-MM-DD，服务端按服务器当天日期填入 |
| data.title | string | 是 | 标题；上游无标题时回退版权文字，再回退兜底文案 |
| data.url | string | 是 | 1920x1080 JPEG 直链；上游未给 urlbase 时是空字符串，今日图接口兜底分支则是一条 data: URI 占位图 |
| data.url_uhd | string \| null | 否 | 4K UHD 原图直链；无 urlbase 时为 null |
| fallback | boolean \| null | 否 | 仅在上游拉取失败、走占位图兜底时出现并为 true；正常拉取时该键缺席 |
| success | boolean | 否 | 恒为 true：上游拉取失败也按兜底数据成功返回 |

响应示例：

```json
{
  "data": {
    "copyright": "string",
    "date": "string",
    "title": "string",
    "url": "string",
    "url_uhd": "string"
  },
  "fallback": "string",
  "success": true
}
```

**错误码**

_除下方“全局通用错误码”外，本接口未声明自定义错误响应_

### `GET /api/bing/wallpaper`

- **摘要**：获取每日 Bing 壁纸
- **鉴权**：公开接口（无需鉴权）

获取 Bing 每日壁纸信息，包含图片 URL、标题、描述和版权信息。结果会被缓存。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BingWallpaperResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| copyright | string | 否 | 版权信息 |
| copyright_link | string | 否 | 版权链接 |
| date | string | 是 | 壁纸日期 YYYY-MM-DD |
| description | string | 否 | 壁纸描述 |
| full_url | string | 是 | 完整壁纸图片 URL |
| title | string | 是 | 壁纸标题 |
| url | string | 是 | 壁纸图片 URL |

响应示例：

```json
{
  "copyright": "",
  "copyright_link": "",
  "date": "string",
  "description": "",
  "full_url": "string",
  "title": "string",
  "url": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/bing/wallpapers`

- **摘要**：获取最近多天的 Bing 壁纸列表
- **鉴权**：公开接口（无需鉴权）

代理 Bing HPImageArchive 接口，一次返回最近 n 天（1-8）的壁纸数据，供前端规避 CORS 直连限制。结果缓存 1 小时。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BingWallpaperListResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| images | object[] | 否 | 壁纸列表 |

响应示例：

```json
{
  "images": [
    {
      "copyright": "",
      "copyright_link": "",
      "enddate": "",
      "full_url": "",
      "startdate": "",
      "title": "",
      "uhd_url": "",
      "url": "",
      "urlbase": ""
    }
  ]
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 评论（8）

文章评论的提交与管理

### `POST /api/admin/comments/batch`

- **摘要**：【管理员】批量操作评论（approve/reject/spam/delete）
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。请求体 {ids: [评论ID...], action: approve|reject|spam|delete}，逐条执行并返回处理计数；action 不在枚举内返回 422（业务码 INVALID_ACTION）。四种动作都会改变文章的可见评论集合，处理完顺带失效受影响文章的详情/列表缓存。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `CommentBatchAction`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| action | string | 是 |  |
| ids | integer[] | 是 |  |

```json
{
  "action": "string",
  "ids": [
    0
  ]
}
```

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/comments/{comment_id}/approve`

- **摘要**：【管理员】批准评论（legacy 子动作，建议统一使用 PATCH /api/admin/comments/{id} status=approved）
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。将评论置为 approved 并公开展示；成功后触发插件钩子 comment.approved。评论不存在返回 404（业务码 COMMENT_NOT_FOUND）。保留原因：React Admin 前端仍在调用。审核会改变文章 comments_count，故顺带失效该文章的详情/列表缓存。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `CommentResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author_avatar | string | 否 |  |
| author_name | string | 是 |  |
| author_website | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| content | string | 是 |  |
| created_at | string | 是 |  |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_pinned | boolean | 否 |  |
| likes_count | integer | 否 |  |
| parent_id | integer \| null | 否 |  |
| parent_ref | object \| null | 否 |  |
| post_id | integer | 是 |  |
| post_ref | object \| null | 否 |  |
| qq | string \| null | 否 |  |
| replies | object[] | 否 |  |
| reply_total | integer | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| status | string | 否 |  |
| user_id | integer \| null | 否 |  |
| user_ref | object \| null | 否 |  |

响应示例：

```json
{
  "author_avatar": "",
  "author_name": "string",
  "author_website": "string",
  "avatar_source": "string",
  "content": "string",
  "created_at": "string",
  "github": "string",
  "id": 0,
  "is_pinned": false,
  "likes_count": 0,
  "parent_id": "string",
  "parent_ref": "string",
  "post_id": 0,
  "post_ref": "string",
  "qq": "string",
  "replies": [],
  "reply_total": 0,
  "resolved_avatar_url": "string",
  "status": "pending",
  "user_id": "string",
  "user_ref": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/comments/{comment_id}/reject`

- **摘要**：【管理员】拒绝评论（legacy 子动作）
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。将评论置为 rejected，前台不再展示。评论不存在返回 404（业务码 COMMENT_NOT_FOUND）。下架会改变文章 comments_count，故顺带失效该文章的详情/列表缓存。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `CommentResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author_avatar | string | 否 |  |
| author_name | string | 是 |  |
| author_website | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| content | string | 是 |  |
| created_at | string | 是 |  |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_pinned | boolean | 否 |  |
| likes_count | integer | 否 |  |
| parent_id | integer \| null | 否 |  |
| parent_ref | object \| null | 否 |  |
| post_id | integer | 是 |  |
| post_ref | object \| null | 否 |  |
| qq | string \| null | 否 |  |
| replies | object[] | 否 |  |
| reply_total | integer | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| status | string | 否 |  |
| user_id | integer \| null | 否 |  |
| user_ref | object \| null | 否 |  |

响应示例：

```json
{
  "author_avatar": "",
  "author_name": "string",
  "author_website": "string",
  "avatar_source": "string",
  "content": "string",
  "created_at": "string",
  "github": "string",
  "id": 0,
  "is_pinned": false,
  "likes_count": 0,
  "parent_id": "string",
  "parent_ref": "string",
  "post_id": 0,
  "post_ref": "string",
  "qq": "string",
  "replies": [],
  "reply_total": 0,
  "resolved_avatar_url": "string",
  "status": "pending",
  "user_id": "string",
  "user_ref": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/comments/{comment_id}/spam`

- **摘要**：【管理员】标记为垃圾评论（legacy 子动作）
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。将评论置为 spam，前台不再展示；成功后触发插件钩子 comment.spam。评论不存在返回 404（业务码 COMMENT_NOT_FOUND）。判垃圾会改变文章 comments_count，故顺带失效该文章的详情/列表缓存。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `CommentResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author_avatar | string | 否 |  |
| author_name | string | 是 |  |
| author_website | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| content | string | 是 |  |
| created_at | string | 是 |  |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_pinned | boolean | 否 |  |
| likes_count | integer | 否 |  |
| parent_id | integer \| null | 否 |  |
| parent_ref | object \| null | 否 |  |
| post_id | integer | 是 |  |
| post_ref | object \| null | 否 |  |
| qq | string \| null | 否 |  |
| replies | object[] | 否 |  |
| reply_total | integer | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| status | string | 否 |  |
| user_id | integer \| null | 否 |  |
| user_ref | object \| null | 否 |  |

响应示例：

```json
{
  "author_avatar": "",
  "author_name": "string",
  "author_website": "string",
  "avatar_source": "string",
  "content": "string",
  "created_at": "string",
  "github": "string",
  "id": 0,
  "is_pinned": false,
  "likes_count": 0,
  "parent_id": "string",
  "parent_ref": "string",
  "post_id": 0,
  "post_ref": "string",
  "qq": "string",
  "replies": [],
  "reply_total": 0,
  "resolved_avatar_url": "string",
  "status": "pending",
  "user_id": "string",
  "user_ref": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/comments/{comment_id}/like`

- **摘要**：给评论点赞（简单计数，允许匿名）
- **鉴权**：公开接口（无需鉴权）

公开接口，无需登录。对评论 likes_count 简单自增，不按用户去重，非幂等。按 IP 限流 30 次/分钟（滑动窗口）。评论不存在返回 404（业务码 COMMENT_NOT_FOUND）。响应为裸 dict（success + 自增后的 likes_count 累计总数），无 data 信封。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `CommentLikeResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| likes_count | integer | 否 | 自增之后该评论的最新点赞总数（不是本次请求的增量，非幂等） |
| success | boolean | 否 | 固定为 true：评论不存在时本接口返回 404 而非 false |

响应示例：

```json
{
  "likes_count": 0,
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/comments/{comment_id}/replies`

- **摘要**：获取某根评论的全部回复分页
- **鉴权**：需鉴权：`HTTPBearer`

公开接口，按时间正序分页返回该根评论下的全部回复（回复只有一层，嵌套超过 1 层的回复在发表时即被拒绝）。评论不存在返回 404（业务码 COMMENT_NOT_FOUND）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `CommentPagedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 |  |
| page | integer | 是 |  |
| page_size | integer | 是 |  |
| total | integer | 是 |  |
| total_pages | integer | 是 |  |

响应示例：

```json
{
  "items": [
    {
      "author_avatar": "",
      "author_name": "string",
      "author_website": "string",
      "avatar_source": "string",
      "content": "string",
      "created_at": "string",
      "github": "string",
      "id": 0,
      "is_pinned": false,
      "likes_count": 0,
      "parent_id": "string",
      "parent_ref": "string",
      "post_id": 0,
      "post_ref": "string",
      "qq": "string",
      "replies": [],
      "reply_total": 0,
      "resolved_avatar_url": "string",
      "status": "pending",
      "user_id": "string",
      "user_ref": "string"
    }
  ],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/posts/{post_id_or_slug}/comments`

- **摘要**：获取某文章根评论分页（含前 3 条最新回复与 reply_total）
- **鉴权**：需鉴权：`HTTPBearer`

公开接口。post_id_or_slug 同时接受数字 ID 或文章 slug；文章不存在返回 404（业务码 POST_NOT_FOUND）。每条根评论附带前 3 条最新回复与 reply_total，完整回复走 GET /api/comments/{comment_id}/replies。include_unapproved=true 仅对作者本人/管理员生效，匿名访客始终只见过审评论。评论树的可读性判定与文章详情同源：草稿/待审/定时未到的文章、以及设了密码但本次未带正确密码（``password`` 查询参数或 ``X-Post-Password`` 头，作者与 staff 免验）的文章，对无权观看者一律 404 POST_NOT_FOUND，而不是把正文藏起来却把评论全给你。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `CommentPagedResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 |  |
| page | integer | 是 |  |
| page_size | integer | 是 |  |
| total | integer | 是 |  |
| total_pages | integer | 是 |  |

响应示例：

```json
{
  "items": [
    {
      "author_avatar": "",
      "author_name": "string",
      "author_website": "string",
      "avatar_source": "string",
      "content": "string",
      "created_at": "string",
      "github": "string",
      "id": 0,
      "is_pinned": false,
      "likes_count": 0,
      "parent_id": "string",
      "parent_ref": "string",
      "post_id": 0,
      "post_ref": "string",
      "qq": "string",
      "replies": [],
      "reply_total": 0,
      "resolved_avatar_url": "string",
      "status": "pending",
      "user_id": "string",
      "user_ref": "string"
    }
  ],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/posts/{post_id_or_slug}/comments`

- **摘要**：发表评论（游客或登录用户均可）
- **鉴权**：需鉴权：`HTTPBearer`

公开写入接口，支持对根评论的一层回复（parent_id 指向的评论必须属于同一篇文章）。携带 Bearer Token（登录用户发帖）时强制执行 CSRF 校验：Origin 须在白名单且 Cookie csrf_token 与 X-CSRF-Token 双提交一致，否则 403（CSRF_CHECK_FAILED）；匿名请求不带 Authorization 时跳过该校验。文章不存在返回 404（POST_NOT_FOUND）。与读取口同口径：草稿/待审/定时未到的文章与未解锁的加密文章一律按 404 处理，不给草稿或加密文章写评论。常见失败：422 AUTHOR_NAME_REQUIRED / AUTHOR_NAME_TOO_SHORT / COMMENT_PARENT_WRONG_POST / NESTED_REPLY_TOO_DEEP；404 COMMENT_PARENT_NOT_FOUND；429 TOO_FREQUENT_COMMENT（Retry-After: 30，同文章同 IP 频控）。成功后触发插件钩子 comment.created。非幂等。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `CommentCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author_avatar_source | enum(`auto`, `custom`, `github`, `qq`, `gravatar`) \| null | 否 | 【已废弃】请使用 avatar_source；旧调用方兼容位，若为非 None 会覆盖 avatar_source |
| author_email | string \| null | 否 |  |
| author_name | string \| null | 否 |  |
| author_website | string \| null | 否 |  |
| avatar_source | enum(`auto`, `custom`, `github`, `qq`, `gravatar`) | 否 | 头像来源 |
| content | string | 是 |  |
| github | string \| null | 否 | 评论者 GitHub 用户名（可选） |
| hcaptcha_token | string \| null | 否 |  |
| parent_id | integer \| null | 否 |  |
| qq | string \| null | 否 | 评论者 QQ（可选） |

```json
{
  "author_avatar_source": "string",
  "author_email": "string",
  "author_name": "string",
  "author_website": "string",
  "avatar_source": "auto",
  "content": "string",
  "github": "string",
  "hcaptcha_token": "string",
  "parent_id": "string",
  "qq": "string"
}
```

**出参**

`201` · 模型 `CommentResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| author_avatar | string | 否 |  |
| author_name | string | 是 |  |
| author_website | string \| null | 否 |  |
| avatar_source | string \| null | 否 |  |
| content | string | 是 |  |
| created_at | string | 是 |  |
| github | string \| null | 否 |  |
| id | integer | 是 |  |
| is_pinned | boolean | 否 |  |
| likes_count | integer | 否 |  |
| parent_id | integer \| null | 否 |  |
| parent_ref | object \| null | 否 |  |
| post_id | integer | 是 |  |
| post_ref | object \| null | 否 |  |
| qq | string \| null | 否 |  |
| replies | object[] | 否 |  |
| reply_total | integer | 否 |  |
| resolved_avatar_url | string \| null | 否 |  |
| status | string | 否 |  |
| user_id | integer \| null | 否 |  |
| user_ref | object \| null | 否 |  |

响应示例：

```json
{
  "author_avatar": "",
  "author_name": "string",
  "author_website": "string",
  "avatar_source": "string",
  "content": "string",
  "created_at": "string",
  "github": "string",
  "id": 0,
  "is_pinned": false,
  "likes_count": 0,
  "parent_id": "string",
  "parent_ref": "string",
  "post_id": 0,
  "post_ref": "string",
  "qq": "string",
  "replies": [],
  "reply_total": 0,
  "resolved_avatar_url": "string",
  "status": "pending",
  "user_id": "string",
  "user_ref": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 相册（2）

公开相册浏览

### `GET /api/gallery/albums`

- **摘要**：获取公开相册列表
- **鉴权**：公开接口（无需鉴权）

公开相册列表（分页）

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PaginatedResponse_AlbumResponse_`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 |  |
| page | integer | 是 | 当前页码 |
| page_size | integer | 是 | 每页大小 |
| total | integer | 是 | 总记录数 |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [
    {
      "cover": "string",
      "created_at": "string",
      "description": "string",
      "id": 0,
      "is_published": true,
      "photo_count": 0,
      "sort_order": 0,
      "title": "string",
      "updated_at": "string"
    }
  ],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/gallery/albums/{album_id}`

- **摘要**：获取相册详情及照片
- **鉴权**：公开接口（无需鉴权）

获取指定相册详情（包含照片列表，仅公开相册）

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `AlbumDetailResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| cover | string \| null | 否 | 封面 URL |
| created_at | string | 是 |  |
| description | string \| null | 否 | 相册描述 |
| id | integer | 是 |  |
| is_published | boolean | 否 | 是否公开 |
| photo_count | integer | 否 |  |
| photos | object[] | 否 |  |
| sort_order | integer | 否 | 排序权重（越小越靠前） |
| title | string | 是 | 相册标题 |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "cover": "string",
  "created_at": "string",
  "description": "string",
  "id": 0,
  "is_published": true,
  "photo_count": 0,
  "photos": [],
  "sort_order": 0,
  "title": "string",
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---

## 相册管理（9）

相册与照片管理

### `GET /api/admin/gallery/albums`

- **摘要**：【管理员】获取所有相册
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。按 sort_order 升序 + 创建时间倒序分页返回全部相册（含未发布项），可用 is_published 按发布状态过滤。封面为空时自动填充兜底图（仅展示层，不回写 DB）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PaginatedResponse_AlbumResponse_`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 |  |
| page | integer | 是 | 当前页码 |
| page_size | integer | 是 | 每页大小 |
| total | integer | 是 | 总记录数 |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [
    {
      "cover": "string",
      "created_at": "string",
      "description": "string",
      "id": 0,
      "is_published": true,
      "photo_count": 0,
      "sort_order": 0,
      "title": "string",
      "updated_at": "string"
    }
  ],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/gallery/albums`

- **摘要**：【管理员】创建相册
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。创建后作者记为当前管理员，并立即失效相册公开缓存（gallery:*）与前台页面缓存（/gallery swr 600）。非幂等，重复提交会产生同名多相册。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `AlbumCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| cover | string \| null | 否 | 封面 URL |
| description | string \| null | 否 | 相册描述 |
| is_published | boolean | 否 | 是否公开 |
| sort_order | integer | 否 | 排序权重（越小越靠前） |
| title | string | 是 | 相册标题 |

```json
{
  "cover": "string",
  "description": "string",
  "is_published": true,
  "sort_order": 0,
  "title": "string"
}
```

**出参**

`201` · 模型 `AlbumResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| cover | string \| null | 否 | 封面 URL |
| created_at | string | 是 |  |
| description | string \| null | 否 | 相册描述 |
| id | integer | 是 |  |
| is_published | boolean | 否 | 是否公开 |
| photo_count | integer | 否 |  |
| sort_order | integer | 否 | 排序权重（越小越靠前） |
| title | string | 是 | 相册标题 |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "cover": "string",
  "created_at": "string",
  "description": "string",
  "id": 0,
  "is_published": true,
  "photo_count": 0,
  "sort_order": 0,
  "title": "string",
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/admin/gallery/albums/{album_id}`

- **摘要**：【管理员】更新相册
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。PATCH 风格局部更新：仅写入请求体中出现的字段（exclude_unset）。相册不存在返回 404。保存后失效相册公开缓存与前台页面缓存。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `AlbumUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| cover | string \| null | 否 |  |
| description | string \| null | 否 |  |
| is_published | boolean \| null | 否 |  |
| sort_order | integer \| null | 否 |  |
| title | string \| null | 否 |  |

```json
{
  "cover": "string",
  "description": "string",
  "is_published": "string",
  "sort_order": "string",
  "title": "string"
}
```

**出参**

`200` · 模型 `AlbumResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| cover | string \| null | 否 | 封面 URL |
| created_at | string | 是 |  |
| description | string \| null | 否 | 相册描述 |
| id | integer | 是 |  |
| is_published | boolean | 否 | 是否公开 |
| photo_count | integer | 否 |  |
| sort_order | integer | 否 | 排序权重（越小越靠前） |
| title | string | 是 | 相册标题 |
| updated_at | string | 是 |  |

响应示例：

```json
{
  "cover": "string",
  "created_at": "string",
  "description": "string",
  "id": 0,
  "is_published": true,
  "photo_count": 0,
  "sort_order": 0,
  "title": "string",
  "updated_at": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/admin/gallery/albums/{album_id}`

- **摘要**：【管理员】删除相册
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。物理删除相册（级联行为由 ORM relationship 定义），不存在返回 404。删除后失效相册公开缓存与前台页面缓存。不可恢复。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `GET /api/admin/gallery/albums/{album_id}/photos`

- **摘要**：【管理员】获取相册照片列表
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。按 sort_order 升序 + 创建时间正序分页返回该相册全部照片（含未发布语义）。相册不存在返回 404。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `PaginatedResponse_PhotoResponse_`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | object[] | 是 |  |
| page | integer | 是 | 当前页码 |
| page_size | integer | 是 | 每页大小 |
| total | integer | 是 | 总记录数 |
| total_pages | integer | 是 | 总页数 |

响应示例：

```json
{
  "items": [
    {
      "album_id": 0,
      "created_at": "string",
      "description": "string",
      "id": 0,
      "original_url": "string",
      "sort_order": 0,
      "thumbnail_url": "string",
      "title": "string",
      "url": "string"
    }
  ],
  "page": 0,
  "page_size": 0,
  "total": 0,
  "total_pages": 0
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `POST /api/admin/gallery/photos`

- **摘要**：【管理员】添加照片到相册
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。photo.url 应指向 /api/media 上传后的媒体地址（本接口不接收文件本身）。写入后同步刷新所属相册 photo_count 并失效相册公开缓存与前台页面缓存；album_id 对应相册不存在返回 404。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `PhotoCreate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| album_id | integer | 是 | 所属相册 ID |
| description | string \| null | 否 | 照片描述 |
| media_id | integer \| null | 否 | 关联的媒体库 ID（透传保留，暂不写入 photos 表） |
| original_url | string \| null | 否 | 照片 URL（兼容字段名，优先使用 url） |
| sort_order | integer | 否 | 排序权重 |
| thumbnail_url | string \| null | 否 | 缩略图 URL（透传保留，暂不写入 photos 表） |
| title | string \| null | 否 | 照片标题 |
| url | string | 是 | 照片 URL |

```json
{
  "album_id": 0,
  "description": "string",
  "media_id": "string",
  "original_url": "string",
  "sort_order": 0,
  "thumbnail_url": "string",
  "title": "string",
  "url": "string"
}
```

**出参**

`201` · 模型 `PhotoResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| album_id | integer | 是 |  |
| created_at | string | 是 |  |
| description | string \| null | 否 | 照片描述 |
| id | integer | 是 |  |
| original_url | string \| null | 否 |  |
| sort_order | integer | 否 | 排序权重 |
| thumbnail_url | string \| null | 否 |  |
| title | string \| null | 否 | 照片标题 |
| url | string | 是 | 照片 URL |

响应示例：

```json
{
  "album_id": 0,
  "created_at": "string",
  "description": "string",
  "id": 0,
  "original_url": "string",
  "sort_order": 0,
  "thumbnail_url": "string",
  "title": "string",
  "url": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/admin/gallery/photos/batch`

- **摘要**：【管理员】批量删除照片
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。一次请求删除多张照片：`DELETE /photos/{photo_id}` 的批量版，前端逐张调用会把 N 张照片变成 N 次请求 + N 次全量相册缓存失效。受影响的相册各重算一次 `photo_count`。响应含 `deleted_count` 与 `missing_ids`（请求里不存在的 ID），调用方不得只看 `success` 判定全部删除完成。只删 DB 记录，媒体文件不自动清理，不可恢复。会失效相册公开缓存与前台页面缓存，并对每张实际删除的照片发一条 photo.deleted 钩子。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `Body_admin_delete_photos_batch_api_admin_gallery_photos_batch_delete`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| ids | integer[] | 是 | 照片 ID 列表 |

```json
{
  "ids": [
    0
  ]
}
```

**出参**

`200` · 模型 `PhotoBatchDeleteResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| deleted_count | integer | 是 | 本次实际删除的行数（请求 ID 中与库内交集的大小） |
| message | string | 是 | 人类可读汇总，如「已删除 3 张照片，2 个 ID 不存在」（后半段仅缺失时出现） |
| missing_ids | integer[] | 否 | 请求里不存在的 ID 列表，升序去重；调用方不得只看 success 判定全部删除完成 |
| success | boolean | 否 | 固定为 true：一条都不存在时本接口返回 404 而非 false；部分缺失仍为 true |

响应示例：

```json
{
  "deleted_count": 0,
  "message": "string",
  "missing_ids": [
    0
  ],
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `PUT /api/admin/gallery/photos/{photo_id}`

- **摘要**：【管理员】更新照片
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。局部更新（exclude_unset）；若传入新的 album_id 则执行跨相册移动，新旧相册的 photo_count 都会重算。照片不存在返回 404，目标相册不存在返回 404。保存后失效相册公开缓存与前台页面缓存。

**入参**

_无路径 / query 参数_

**请求体**（`application/json`，模型 `PhotoUpdate`）

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| album_id | integer \| null | 否 |  |
| description | string \| null | 否 |  |
| media_id | integer \| null | 否 |  |
| original_url | string \| null | 否 | 兼容字段，会覆盖 url |
| sort_order | integer \| null | 否 |  |
| thumbnail_url | string \| null | 否 |  |
| title | string \| null | 否 |  |
| url | string \| null | 否 |  |

```json
{
  "album_id": "string",
  "description": "string",
  "media_id": "string",
  "original_url": "string",
  "sort_order": "string",
  "thumbnail_url": "string",
  "title": "string",
  "url": "string"
}
```

**出参**

`200` · 模型 `PhotoResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| album_id | integer | 是 |  |
| created_at | string | 是 |  |
| description | string \| null | 否 | 照片描述 |
| id | integer | 是 |  |
| original_url | string \| null | 否 |  |
| sort_order | integer | 否 | 排序权重 |
| thumbnail_url | string \| null | 否 |  |
| title | string \| null | 否 | 照片标题 |
| url | string | 是 | 照片 URL |

响应示例：

```json
{
  "album_id": 0,
  "created_at": "string",
  "description": "string",
  "id": 0,
  "original_url": "string",
  "sort_order": 0,
  "thumbnail_url": "string",
  "title": "string",
  "url": "string"
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

### `DELETE /api/admin/gallery/photos/{photo_id}`

- **摘要**：【管理员】删除照片
- **鉴权**：需鉴权：`HTTPBearer`

需 CurrentStaff。物理删除照片并重算所属相册 photo_count，不存在返回 404。删除后失效相册公开缓存与前台页面缓存。不可恢复（仅删 DB 记录，媒体文件不自动清理）。

**入参**

_无路径 / query 参数_

**出参**

`200` · 模型 `BaseResponse`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 否 |  |
| success | boolean | 否 |  |

响应示例：

```json
{
  "message": "操作成功",
  "success": true
}
```

**错误码**

| 状态码 | 说明 |
| --- | --- |
| `422` | Validation Error |

---
