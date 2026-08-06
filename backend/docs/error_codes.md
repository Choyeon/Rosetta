# Rosetta API 错误码文档

## 概述

本文档列出了 Rosetta API 返回的所有错误码及其含义，帮助前端开发者正确处理错误。

## 错误响应格式

所有错误响应遵循统一格式：

```json
{
  "success": false,
  "message": "错误描述信息",
  "error_code": "ERROR_CODE",
  "errors": [
    {
      "field": "字段名",
      "message": "字段错误信息",
      "type": "错误类型"
    }
  ]
}
```

## HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 资源创建成功 |
| 400 | 请求参数错误 |
| 401 | 未授权访问 |
| 403 | 禁止访问 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 数据验证失败 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |
| 503 | 服务暂时不可用 |

---

## 错误码列表

### 通用错误 (1xxx)

| 错误码 | HTTP 状态码 | 说明 | 处理建议 |
|--------|-------------|------|----------|
| `INTERNAL_ERROR` | 500 | 服务器内部错误 | 联系管理员，稍后重试 |
| `SERVICE_UNAVAILABLE` | 503 | 服务暂时不可用 | 等待后重试 |
| `VALIDATION_ERROR` | 422 | 数据验证失败 | 检查请求参数 |
| `BAD_REQUEST` | 400 | 请求参数错误 | 检查请求格式 |

### 认证错误 (2xxx)

| 错误码 | HTTP 状态码 | 说明 | 处理建议 |
|--------|-------------|------|----------|
| `UNAUTHORIZED` | 401 | 未授权访问 | 跳转登录页面 |
| `TOKEN_EXPIRED` | 401 | 令牌已过期 | 使用刷新令牌获取新令牌 |
| `TOKEN_INVALID` | 401 | 无效的令牌 | 重新登录 |
| `REFRESH_TOKEN_INVALID` | 401 | 无效的刷新令牌 | 重新登录 |
| `REFRESH_TOKEN_EXPIRED` | 401 | 刷新令牌已过期 | 重新登录 |
| `REFRESH_TOKEN_REVOKED` | 401 | 刷新令牌已撤销 | 重新登录 |

### 权限错误 (3xxx)

| 错误码 | HTTP 状态码 | 说明 | 处理建议 |
|--------|-------------|------|----------|
| `FORBIDDEN` | 403 | 禁止访问 | 检查用户权限 |
| `NOT_STAFF` | 403 | 需要管理员权限 | 联系管理员获取权限 |
| `NOT_SUPERUSER` | 403 | 需要超级管理员权限 | 联系超级管理员 |
| `USER_BANNED` | 403 | 用户已被封禁 | 联系管理员 |
| `USER_INACTIVE` | 403 | 用户账号未激活 | 激活账号 |
| `PROFILE_NOT_PUBLIC` | 403 | 用户资料不公开 | 无权限查看 |

### 资源错误 (4xxx)

| 错误码 | HTTP 状态码 | 说明 | 处理建议 |
|--------|-------------|------|----------|
| `NOT_FOUND` | 404 | 资源不存在 | 检查资源 ID 或 slug |
| `POST_NOT_FOUND` | 404 | 文章不存在 | 检查文章 slug |
| `USER_NOT_FOUND` | 404 | 用户不存在 | 检查用户 ID |
| `CATEGORY_NOT_FOUND` | 404 | 分类不存在 | 检查分类 ID 或 slug |
| `TAG_NOT_FOUND` | 404 | 标签不存在 | 检查标签 ID 或 slug |
| `COMMENT_NOT_FOUND` | 404 | 评论不存在 | 检查评论 ID |
| `PAGE_NOT_FOUND` | 404 | 页面不存在 | 检查页面 slug |
| `NAVIGATION_NOT_FOUND` | 404 | 导航不存在 | 检查导航 ID |
| `FRIEND_LINK_NOT_FOUND` | 404 | 友链不存在 | 检查友链 ID |

### 冲突错误 (5xxx)

| 错误码 | HTTP 状态码 | 说明 | 处理建议 |
|--------|-------------|------|----------|
| `CONFLICT` | 409 | 资源冲突 | 检查资源是否已存在 |
| `USERNAME_EXISTS` | 400 | 用户名已存在 | 更换用户名 |
| `EMAIL_EXISTS` | 400 | 邮箱已存在 | 更换邮箱或使用已有账号登录 |
| `SLUG_EXISTS` | 400 | 别名已存在 | 更换 slug |
| `CATEGORY_SLUG_EXISTS` | 400 | 分类别名已存在 | 更换分类 slug |
| `TAG_SLUG_EXISTS` | 400 | 标签别名已存在 | 更换标签 slug |
| `PAGE_SLUG_EXISTS` | 400 | 页面别名已存在 | 更换页面 slug |

### 业务错误 (6xxx)

| 错误码 | HTTP 状态码 | 说明 | 处理建议 |
|--------|-------------|------|----------|
| `REGISTRATION_DISABLED` | 403 | 注册功能已关闭 | 联系管理员 |
| `LOGIN_FAILED` | 401 | 登录失败 | 检查用户名和密码 |
| `PASSWORD_MISMATCH` | 400 | 密码不匹配 | 检查密码输入 |
| `PASSWORD_TOO_WEAK` | 400 | 密码强度不足 | 使用更强的密码 |
| `COMMENTS_DISABLED` | 403 | 评论功能已关闭 | 无法发表评论 |
| `POST_COMMENTS_DISABLED` | 403 | 该文章禁止评论 | 无法发表评论 |
| `POST_PASSWORD_REQUIRED` | 403 | 文章需要密码访问 | 提供正确的密码 |
| `POST_PASSWORD_INCORRECT` | 403 | 文章密码错误 | 提供正确的密码 |
| `COMMENT_NEED_APPROVAL` | 403 | 评论需要审核 | 等待审核通过 |
| `PARENT_COMMENT_NOT_FOUND` | 400 | 父评论不存在 | 检查父评论 ID |

### 限流错误 (7xxx)

| 错误码 | HTTP 状态码 | 说明 | 处理建议 |
|--------|-------------|------|----------|
| `RATE_LIMIT_EXCEEDED` | 429 | 请求过于频繁 | 等待 `retry_after` 秒后重试 |
| `LOGIN_RATE_LIMITED` | 429 | 登录尝试次数过多 | 等待锁定时间结束后重试 |
| `ACCOUNT_LOCKED` | 403 | 账户已被锁定 | 等待解锁或联系管理员 |

### 文件上传错误 (8xxx)

| 错误码 | HTTP 状态码 | 说明 | 处理建议 |
|--------|-------------|------|----------|
| `FILE_TOO_LARGE` | 400 | 文件大小超过限制 | 压缩文件或上传更小的文件 |
| `INVALID_FILE_TYPE` | 400 | 不支持的文件类型 | 使用支持的文件格式 |
| `INVALID_IMAGE` | 400 | 无效的图片文件 | 检查图片文件是否损坏 |
| `UPLOAD_FAILED` | 500 | 文件上传失败 | 稍后重试 |

---

## 常见错误处理示例

### 401 未授权

```typescript
if (response.status === 401) {
  // 尝试刷新令牌
  const refreshed = await refreshToken()
  if (!refreshed) {
    // 跳转登录页面
    router.push('/login')
  }
}
```

### 429 请求过于频繁

```typescript
if (response.status === 429) {
  const retryAfter = response.headers.get('Retry-After')
  // 显示等待提示
  showToast(`请等待 ${retryAfter} 秒后重试`)
}
```

### 422 数据验证失败

```typescript
if (response.status === 422) {
  const errors = response.data.errors
  // 显示字段错误
  errors.forEach(error => {
    setFieldError(error.field, error.message)
  })
}
```

### 网络错误

```typescript
try {
  const response = await api.get('/posts')
} catch (error) {
  if (!error.response) {
    // 网络错误
    showToast('网络连接失败，请检查网络设置')
  }
}
```

---

## 错误码与 HTTP 状态码映射

```
HTTP 400 -> BAD_REQUEST, VALIDATION_ERROR, USERNAME_EXISTS, EMAIL_EXISTS, ...
HTTP 401 -> UNAUTHORIZED, TOKEN_EXPIRED, TOKEN_INVALID, LOGIN_FAILED, ...
HTTP 403 -> FORBIDDEN, NOT_STAFF, USER_BANNED, REGISTRATION_DISABLED, ...
HTTP 404 -> NOT_FOUND, POST_NOT_FOUND, USER_NOT_FOUND, ...
HTTP 409 -> CONFLICT, ...
HTTP 422 -> VALIDATION_ERROR, ...
HTTP 429 -> RATE_LIMIT_EXCEEDED, LOGIN_RATE_LIMITED, ...
HTTP 500 -> INTERNAL_ERROR, ...
HTTP 503 -> SERVICE_UNAVAILABLE, ...
```

---

## 前端错误处理最佳实践

1. **统一错误处理**：使用 axios 拦截器统一处理错误响应

```typescript
axios.interceptors.response.use(
  response => response,
  error => {
    const { response } = error
    if (response) {
      switch (response.status) {
        case 401:
          // 处理未授权
          break
        case 403:
          // 处理禁止访问
          break
        case 404:
          // 处理资源不存在
          break
        case 429:
          // 处理限流
          break
        default:
          // 其他错误
      }
    }
    return Promise.reject(error)
  }
)
```

2. **用户友好提示**：将技术性错误转换为用户友好的提示信息

3. **错误日志**：记录错误信息以便调试

4. **重试机制**：对于临时性错误（如网络错误）实现自动重试
