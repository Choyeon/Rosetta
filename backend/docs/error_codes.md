# Rosetta API 错误码文档

## 概述

本文档列出 Rosetta API 返回的错误码及其含义，帮助前端开发者正确处理错误。

> **错误码清单区块由脚本从源码反向生成，请勿手改**：清单内的每一个错误码都在
> `backend/**/*.py` 里有真实字面量证据（`error_code=` / `HTTPException` 包络 /
> `AppException` 子类 / `main.py::_STATUS_ERROR_CODES` 回退表）。
> 新增或删除错误码后运行：
> `uv run python -m backend.scripts.gen_error_codes --write`
> 漂移守卫见 `tests/test_docs_error_codes_sync.py`——改了码没改文档会直接红。
>
> 历史教训：旧版本文档手写 49 个码，其中 36 个（`USER_NOT_FOUND`、`TOKEN_INVALID`、
> `LOGIN_FAILED`、`NOT_STAFF` 等）代码里从未产出过，真实码反而一个都没写。前端按
> 幻觉码分支处理，真实错误全部落到默认分支。现已改为源码驱动。

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
| 423 | 账号被临时锁定 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |
| 503 | 服务暂时不可用 |

---

<!-- BEGIN AUTO-GENERATED:ERROR_CODE_INDEX 由 backend/scripts/gen_error_codes.py 生成，请勿手改 -->

## 错误码清单（自动生成）

本区块由 `backend/scripts/gen_error_codes.py` 扫描 `backend/**/*.py` 生成，共 **62 个真实存在的错误码**。

- 出处列只列到文件级：同一个码可能出现在多个端点，具体判定看源码。
- HTTP 列为该码在当前源码里能推断出的状态码；`—` 表示该码由 AppException 子类外的路径抛出且附近没有 `status_code=`（以调用点为准）。
- 新增/删除错误码后跑 `uv run python -m backend.scripts.gen_error_codes --write`，否则 `tests/test_docs_error_codes_sync.py` 会失败。

### 通用与状态码回退（18）

| 错误码 | HTTP | 说明 | 出处 |
| --- | --- | --- | --- |
| `BAD_REQUEST` | 400 | — | `backend/core/exceptions.py`<br>`backend/main.py` |
| `CONFLICT` | 409 | — | `backend/core/exceptions.py`<br>`backend/main.py` |
| `FORBIDDEN` | 403 | — | `backend/core/exceptions.py`<br>`backend/main.py` |
| `INTERNAL` | 500 | 服务器错误 | `backend/api/comments.py`<br>`backend/api/guestbook.py` |
| `INTERNAL_SERVER_ERROR` | — | — | `backend/main.py` |
| `INVALID_INSTALL_SOURCE` | — | — | `backend/api/plugins.py`<br>`backend/api/themes_ext.py` |
| `METHOD_NOT_ALLOWED` | 405 | — | `backend/main.py` |
| `NOT_FOUND` | 404 | — | `backend/core/exceptions.py`<br>`backend/main.py` |
| `PAYLOAD_INVALID` | — | — | `backend/api/plugins.py`<br>`backend/api/themes_ext.py` |
| `PAYLOAD_TOO_LARGE` | 413 | — | `backend/main.py` |
| `PERMISSION_DENIED` | — | — | `backend/core/auth.py` |
| `POST_NOT_FOUND` | 404 | 文章不存在 | `backend/api/comments.py` |
| `REQUEST_ENTITY_TOO_LARGE` | — | — | `backend/api/media.py` |
| `RESOURCE_NOT_FOUND` | 404 | 资源不存在 | `backend/core/exceptions.py` |
| `SERVICE_UNAVAILABLE` | 503 | — | `backend/core/exceptions.py`<br>`backend/main.py` |
| `UNAUTHORIZED` | 401 | — | `backend/core/exceptions.py`<br>`backend/main.py` |
| `VALIDATION_ERROR` | 422 | — | `backend/core/exceptions.py`<br>`backend/main.py` |
| `VALIDATION_FAILED` | 422 | payload 必须是 object | `backend/main.py`<br>`backend/plugins/guestbook-rss/plugin.py` |

### 认证与授权（2）

| 错误码 | HTTP | 说明 | 出处 |
| --- | --- | --- | --- |
| `AUTH_INVALID_CREDENTIALS` | — | — | `backend/api/users.py` |
| `AUTH_REQUIRED` | — | 请先登录后再发布动态 | `backend/api/activity.py` |

### 令牌与刷新（2）

| 错误码 | HTTP | 说明 | 出处 |
| --- | --- | --- | --- |
| `TOKEN_REUSED` | — | 该刷新令牌已被使用过（禁止重用） | `backend/api/users.py` |
| `TOKEN_VERSION_MISMATCH` | — | 密码已修改，该刷新令牌已失效 | `backend/api/users.py` |

### 密码重置（1）

| 错误码 | HTTP | 说明 | 出处 |
| --- | --- | --- | --- |
| `RESET_CODE_INVALID` | — | 尝试次数过多，验证码已作废，请重新申请 | `backend/api/users.py` |

### 密码策略（1）

| 错误码 | HTTP | 说明 | 出处 |
| --- | --- | --- | --- |
| `WEAK_PASSWORD` | 422 | 新密码不符合强度要求 | `backend/api/users.py`<br>`backend/core/exceptions.py` |

### 限流与锁定（2）

| 错误码 | HTTP | 说明 | 出处 |
| --- | --- | --- | --- |
| `ACCOUNT_LOCKED` | 423 | 账号因多次登录失败已被暂时锁定 | `backend/api/users.py`<br>`backend/main.py` |
| `RATE_LIMIT_EXCEEDED` | 429 | — | `backend/core/exceptions.py` |

### CSRF（1）

| 错误码 | HTTP | 说明 | 出处 |
| --- | --- | --- | --- |
| `CSRF_CHECK_FAILED` | — | — | `backend/core/csrf.py` |

### OOBE 安装向导（3）

| 错误码 | HTTP | 说明 | 出处 |
| --- | --- | --- | --- |
| `ADMIN_NOT_CREATED` | 400 | — | `backend/core/exceptions.py` |
| `OOBE_ALREADY_COMPLETED` | 409 | — | `backend/core/exceptions.py` |
| `OOBE_REQUIRED` | 503 | — | `backend/core/exceptions.py` |

### 文件上传（4）

| 错误码 | HTTP | 说明 | 出处 |
| --- | --- | --- | --- |
| `UPLOAD_EXT_REJECTED` | — | — | `backend/api/media.py` |
| `UPLOAD_MAGIC_MISMATCH` | — | — | `backend/api/media.py` |
| `UPLOAD_PATH_TRAVERSAL` | — | — | `backend/api/media.py` |
| `UPLOAD_SVG_UNSAFE` | — | — | `backend/api/media.py` |

### 插件系统（6）

| 错误码 | HTTP | 说明 | 出处 |
| --- | --- | --- | --- |
| `PLUGIN_ALREADY_ACTIVE` | 409 | 请先禁用该插件再删除 | `backend/api/plugins.py`<br>`backend/core/extensions.py` |
| `PLUGIN_IMPORT_ERROR` | 500 | — | `backend/core/extensions.py` |
| `PLUGIN_INVALID_ACTION` | 422 | — | `backend/core/extensions.py` |
| `PLUGIN_NOT_FOUND` | 404 | — | `backend/api/plugins.py`<br>`backend/core/extensions.py` |
| `PLUGIN_SETTINGS_INVALID` | 422 | 插件设置必须是 JSON 对象 | `backend/api/plugins.py`<br>`backend/core/extensions.py` |
| `PLUGIN_SLUG_REQUIRED` | — | source=local 时必须通过 JSON body 提供 slug 字段 | `backend/api/plugins.py` |

### 主题系统（5）

| 错误码 | HTTP | 说明 | 出处 |
| --- | --- | --- | --- |
| `MODS_SCHEMA_VIOLATION` | 400 | — | `backend/core/extensions.py` |
| `THEME_ALREADY_ACTIVE` | 409 | 激活中的主题不允许删除（请先切换） | `backend/core/extensions.py` |
| `THEME_MODS_INVALID` | 422 | 主题 mods 必须是 JSON 对象 | `backend/core/extensions.py` |
| `THEME_NOT_FOUND` | 404 | — | `backend/api/themes_ext.py`<br>`backend/core/extensions.py` |
| `THEME_SLUG_REQUIRED` | — | source=local 时必须通过 JSON body 提供 slug 字段 | `backend/api/themes_ext.py` |

### 扩展包（插件/主题）下载与解压（10）

| 错误码 | HTTP | 说明 | 出处 |
| --- | --- | --- | --- |
| `PACKAGE_ALREADY_ACTIVE` | 409 | — | `backend/core/extensions.py` |
| `PACKAGE_CHECKSUM_MISMATCH` | 400 | SHA-256 校验不匹配 | `backend/core/extensions.py` |
| `PACKAGE_DOWNLOAD_FAILED` | 502 | — | `backend/core/extensions.py` |
| `PACKAGE_EMPTY` | 400 | ZIP 内没有文件 | `backend/core/extensions.py` |
| `PACKAGE_MANIFEST_NOT_FOUND` | 400 | — | `backend/core/extensions.py` |
| `PACKAGE_PATH_INVALID` | 400 | — | `backend/core/extensions.py` |
| `PACKAGE_STRUCTURE_INVALID` | 400 | — | `backend/core/extensions.py` |
| `PACKAGE_TOO_LARGE` | 400 | — | `backend/core/extensions.py` |
| `PACKAGE_UPLOAD_FILE_REQUIRED` | — | source=upload 时必须通过 multipart/form-data 提供 file 字段 | `backend/api/plugins.py`<br>`backend/api/themes_ext.py` |
| `PACKAGE_ZIP_INVALID` | 400 | — | `backend/core/extensions.py` |

### 扩展市场（3）

| 错误码 | HTTP | 说明 | 出处 |
| --- | --- | --- | --- |
| `MARKET_INDEX_INVALID` | — | 市场索引格式异常：缺少 items 列表 | `backend/api/plugins.py`<br>`backend/api/themes_ext.py` |
| `MARKET_ITEM_MISSING_ZIP_URL` | — | — | `backend/api/plugins.py`<br>`backend/api/themes_ext.py` |
| `MARKET_ITEM_NOT_FOUND` | — | — | `backend/api/plugins.py`<br>`backend/api/themes_ext.py` |

### 远程来源（2）

| 错误码 | HTTP | 说明 | 出处 |
| --- | --- | --- | --- |
| `REMOTE_INFO_MISSING` | 400 | remote 字段必填 | `backend/api/plugins.py`<br>`backend/api/themes_ext.py`<br>`backend/core/extensions.py` |
| `REMOTE_URL_NOT_ALLOWED` | 400 | — | `backend/core/extensions.py` |

### 清单校验（2）

| 错误码 | HTTP | 说明 | 出处 |
| --- | --- | --- | --- |
| `MANIFEST_INVALID` | 400 | — | `backend/core/extensions.py` |
| `SCHEMA_VALIDATOR_UNAVAILABLE` | 500 | 既无 jsonschema 也无 pydantic，无法执行 schema 校验 | `backend/core/extensions.py` |

<!-- END AUTO-GENERATED:ERROR_CODE_INDEX -->

---

## 限流与账号锁定口径说明

> 429 的对外错误码**全站唯一**为 `RATE_LIMIT_EXCEEDED`，三个触发点（限流中间件、
> `@rate_limit` 装饰器、`build_depends_rate_limit` 依赖）与状态码回退表都取
> `backend/core/exceptions.py::RATE_LIMIT_EXCEEDED`。
> 旧文档里的 `LOGIN_RATE_LIMITED` 代码里从未产出过（登录爆破走 423 锁定 +
> 敏感接口限流），已删除。回归见 `tests/test_core_rate_limit_contract.py`。
> 423 `ACCOUNT_LOCKED` 携带 `Retry-After` 头与响应体 `retry_after_seconds`，
> 前端应据此展示倒计时而非笼统报错。

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

### 423 账号锁定

```typescript
if (response.status === 423) {
  const secs = response.data.retry_after_seconds
  showToast(`账号已锁定，请 ${secs} 秒后再试`)
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

## 前端错误处理最佳实践

1. **按 `error_code` 分支，不要按 `message` 字符串匹配**：`message` 是人类可读且会随
   i18n 变化的文案，`error_code` 才是稳定契约。
2. **未知错误码走默认分支并 toast**：失败一律给用户可见反馈，"静默失败"是 bug。
3. **401 自动刷新**：`apiFetch` 已内置 `refreshAccessToken`，刷新失败清登录态跳 `/login`。
4. **503 `OOBE_REQUIRED`**：前端跳 `/oobe` 安装向导。
