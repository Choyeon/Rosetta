# Rosetta 插件与主题 REST API 参考

> 版本：1.0.0 · 最后更新：2026-08-28 · 语言：zh-CN

本文件描述 Rosetta 博客平台中与 **插件（Plugins）**、**主题（Themes）**、**主题 Mods**、**短代码（Shortcodes）** 以及 **官方市场（Marketplace）** 相关的全部公开 REST 接口。
所有接口遵循 Rosetta 统一响应约定：

```json
{
  "success": true | false,
  "message": "可选描述",
  "error_code": "错误码（失败时）",
  "data": {}
}
```

分页接口额外返回 `total / page / per_page / total_pages / has_next`。

---

## 1. 认证（Bearer JWT）

除少数明确标记为「公开」的接口外，其余所有 `/api/admin/*` 接口必须携带管理员 JWT：

```http
Authorization: Bearer <access_token>
```

JWT 通过 `POST /api/users/login` 获取；未完成 OOBE 安装向导前，所有 `/api/*` 除白名单外返回 `503 OOBE_REQUIRED`。

### 示例 curl（列出插件）

```bash
curl -H "Authorization: Bearer <TOKEN>" \
  "https://example.com/api/admin/plugins?status=active&per_page=20"
```

### 响应示例（成功）

```json
{
  "success": true,
  "data": [
    {
      "slug": "seo-toolkit",
      "name": "SEO Toolkit",
      "version": "1.2.0",
      "status": "active",
      "author": "Rosetta"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 20,
  "total_pages": 1,
  "has_next": false
}
```

### 响应示例（失败）

```json
{
  "success": false,
  "error_code": "PLUGIN_NOT_FOUND",
  "message": "插件不存在: not-exist"
}
```

---

## 2. 插件 API

所有路由前缀：`/api/admin/plugins`；需要管理员权限。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET  | `/api/admin/plugins` | 列表（支持 status / search / page / per_page 过滤） |
| GET  | `/api/admin/plugins/{slug}` | 详情（含 manifest、settings、安装时间） |
| POST | `/api/admin/plugins/_scan` | 重新扫描磁盘插件目录并同步 DB |
| POST | `/api/admin/plugins/{slug}/activate` | 激活指定插件 |
| POST | `/api/admin/plugins/{slug}/deactivate` | 禁用指定插件 |
| DELETE | `/api/admin/plugins/{slug}` | 删除插件（磁盘 + DB 双清理） |
| POST | `/api/admin/plugins?source=upload` | ZIP 上传安装（multipart/form-data，字段名 `file`） |
| POST | `/api/admin/plugins?source=remote` | 市场 URL 远程安装（JSON Body：`{ slug, remote: { url, checksum_sha256, allow_pre_release } }`） |
| POST | `/api/admin/plugins/_bulk` | 批量 activate / deactivate / delete |
| GET  | `/api/admin/plugins/market` | 官方市场插件列表（8 小时本地缓存） |
| POST | `/api/admin/plugins/market/{slug}/install` | 从官方市场一键安装 |
| GET  | `/api/admin/plugins/{slug}/settings` | 读取插件设置（KV） |
| PUT  | `/api/admin/plugins/{slug}/settings` | 全量覆盖插件设置 |
| PATCH| `/api/admin/plugins/{slug}/settings` | 部分合并插件设置 |
| GET  | `/api/admin/plugins/menu-registry` | 返回所有已激活插件声明的后台菜单项（供 Sidebar 渲染） |

### 示例：ZIP 上传安装

```bash
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  -F "file=@seo-toolkit-1.2.0.zip;type=application/zip" \
  "https://example.com/api/admin/plugins?source=upload"
```

### 示例：远程安装

```bash
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  "https://example.com/api/admin/plugins?source=remote" \
  -d '{
    "slug": "guestbook-rss",
    "remote": {
      "url": "https://market.rosetta.dev/plugins/guestbook-rss/0.1.0.zip",
      "checksum_sha256": "aabbccdd00112233...",
      "allow_pre_release": false
    }
  }'
```

### 示例：激活插件

```bash
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  "https://example.com/api/admin/plugins/hello-rosetta/activate"
```

---

## 3. 主题 API

主题分为 **公开只读接口**（前缀 `/api/themes`）与 **管理接口**（前缀 `/api/admin/themes`）。

### 3.1 公开只读接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET  | `/api/themes/current` | 当前激活主题 slug / manifest / mods / mods_schema |

### 3.2 管理接口（/api/admin/themes）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET  | `/api/admin/themes` | 列表（status / search / page / per_page） |
| GET  | `/api/admin/themes/{slug}` | 主题详情（manifest、mods、mods_schema、截图） |
| PUT  | `/api/admin/themes/{slug}/activate` | 激活主题（互斥：其它主题自动 inactive） |
| POST | `/api/admin/themes/_scan` | 扫描 `frontend/themes/*/rosetta-theme.json` 并同步 DB |
| DELETE | `/api/admin/themes/{slug}` | 删除主题目录与 DB 记录（当前激活主题不可删） |
| GET  | `/api/admin/themes/{slug}/mods` | 读取主题 mods 键值 |
| PUT  | `/api/admin/themes/{slug}/mods` | 全量覆盖 mods（严格校验 mods_schema） |
| PATCH| `/api/admin/themes/{slug}/mods` | 部分合并 mods（严格校验 mods_schema） |
| POST | `/api/admin/themes/install?source=upload` | ZIP 上传安装主题（字段名 `file`） |
| POST | `/api/admin/themes/install?source=remote` | 远程安装主题 |
| POST | `/api/admin/themes/{slug}/upgrade?source=remote` | 在线升级 |
| GET  | `/api/admin/themes/market` | 官方市场主题列表 |
| POST | `/api/admin/themes/market/{slug}/install` | 官方市场一键安装主题 |

### Mods Schema 校验错误响应样例

当 PUT/PATCH mods 不符合 `mods_schema`（JSON Schema Draft-07）时返回：

```json
{
  "success": false,
  "error_code": "MODS_SCHEMA_VIOLATION",
  "message": "'accent_color' is not of type 'string'",
  "data": {
    "schema_path": "/properties/accent_color/type",
    "failing_value": 123
  }
}
```

### 示例：部分修改 mods

```bash
curl -X PATCH -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  "https://example.com/api/admin/themes/astro-paper-inspired/mods" \
  -d '{ "accent_color": "#6d28d9", "posts_per_row": 2 }'
```

---

## 4. Shortcodes API

前缀：`/api/shortcodes`；渲染接口公开可访问（带 30/min/IP 限流）。

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | `/api/shortcodes/render` | 公开 | 把含短代码的文本渲染为 HTML（走 bleach 白名单） |
| GET  | `/api/shortcodes` | 管理员 | 列出所有已注册短代码及描述 |
| POST | `/api/shortcodes` | 管理员 | 注册一个简单「字符串模板」式短代码 |
| DELETE | `/api/shortcodes/{tag}` | 管理员 | 删除 API 方式注册的短代码 |

### 示例：渲染

```http
POST /api/shortcodes/render
Content-Type: application/json

{
  "content": "欢迎来到 Rosetta！[hello to=\"开发者\" /]\n\n[warning]注意：启用插件后才可见额外短代码。[/warning]",
  "context": { "post_id": 42 }
}
```

响应：

```json
{
  "success": true,
  "data": {
    "rendered": "<p>欢迎来到 Rosetta！<p>Hello, <b>开发者</b>!</p></p>\n\n<div class=\"alert warning\">注意：启用插件后才可见额外短代码。</div>",
    "original_length": 91,
    "rendered_length": 176
  }
}
```

> 安全说明：`rendered` 已经过 bleach 白名单过滤；默认允许的标签为 `b / i / em / strong / p / br / img / a / sup / sub / code / pre / ul / ol / li / table / thead / tbody / tr / th / td / blockquote / details / summary`。

---

## 5. 错误码表

| 错误码 | HTTP | 说明 |
| --- | --- | --- |
| `OOBE_REQUIRED` | 503 | 未完成安装向导；所有业务 API 均需 OOBE 锁文件存在 |
| `MODS_SCHEMA_VIOLATION` | 400 | 主题 mods 写入值不符合 mods_schema；见 `data.schema_path` 定位字段 |
| `MARKET_ITEM_NOT_FOUND` | 404 | 官方市场索引中不存在该 slug 条目 |
| `PACKAGE_CHECKSUM_MISMATCH` | 400 | 远程安装 ZIP 的 SHA-256 与清单校验值不一致 |
| `PACKAGE_TOO_LARGE` | 413 | 上传 ZIP 超过 `UPLOAD_MAX_PACKAGE_SIZE_MB`（默认 30MB） |
| `MANIFEST_INVALID` | 422 | `rosetta-plugin.json` / `rosetta-theme.json` 校验失败（缺字段 / 枚举不符 / slug 正则不匹配） |
| `PLUGIN_NOT_FOUND` | 404 | 插件 slug 未注册到 DB（请先 `_scan` 或安装） |
| `THEME_NOT_FOUND` | 404 | 主题 slug 未注册到 DB |
| `PLUGIN_ALREADY_ACTIVE` | 409 | 重复激活 |
| `PLUGIN_NOT_ACTIVE` | 409 | 目标插件未处于 active 状态（执行 deactivate 等时） |
| `THEME_ALREADY_ACTIVE` | 409 | 目标主题已是当前激活主题 |
| `THEME_MODS_INVALID` | 400 | mods 写入值类型错误（schema 层） |
| `VALIDATION_ERROR` | 422 | FastAPI 请求参数校验失败；`data.errors[]` 列出所有字段问题 |

> 统一响应中 `success=false` 且 `error_code` 为上述常量之一时，前端可直接用 `t(error_code)` 做多语言提示映射。
