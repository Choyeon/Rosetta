# Rosetta 插件开发教程

> 版本：2.0.0 · 最后更新：2026-09 · 语言：zh-CN · 对应 Rosetta `v2.1.x`

Rosetta 插件系统由**五大子系统**构成：

| 子系统 | 模块 | 作用 |
| --- | --- | --- |
| Hook 引擎 | `backend/core/hooks.py` | Action（副作用）/ Filter（值变换），全进程**唯一**注册表 |
| Shortcode 引擎 | `backend/core/shortcodes.py` | 在文章中以 `[tag]` 语法嵌入动态 HTML，输出白名单消毒 |
| 路由注册表 | `backend/core/routing_registry.py` | 集中暂存插件 APIRouter 与后台菜单，统一挂载 |
| 插件管理器 | `backend/core/extensions.py` | 安装 / 激活 / 停用 / 删除 / 升级的生命周期与 KV 设置 |
| 兼容门面 | `backend/core/plugin_bus.py` | `PluginBus` 薄门面，核心代码 `bus.do_action()` 统一汇入 hooks |

每个插件是 `backend/plugins/<slug>/` 下的一个 Python 包，入口为 `plugin.py` 中的
`register()` 函数（**同步或异步均可**）。

> **本次重构的关键变化**：历史上 `PluginBus` 与 hooks 模块各持一份互不相通的注册表，
> 插件监听的钩子在真实请求中永远不会被触发。重构后所有注册 / 触发 / 摘除全部汇入
> `backend/core/hooks.py` 的唯一注册表，插件钩子在真实请求路径中可靠生效。

---

## 1. 30 秒最小插件

```python
# backend/plugins/hello-world/plugin.py
from __future__ import annotations
import logging

logger = logging.getLogger("hello-world")
PLUGIN_SLUG = "hello-world"


def on_post_published(post_id, post=None, **_kw):
    logger.info("文章已发布: id=%s slug=%s", post_id, getattr(post, "slug", "?"))


def register(*args, **kwargs):
    from backend.core.hooks import add_action, remove_action
    remove_action("post.published", on_post_published)   # 幂等：先摘后挂
    add_action("post.published", on_post_published, priority=10, plugin=PLUGIN_SLUG)
```

```json
// backend/plugins/hello-world/rosetta-plugin.json
{
  "manifest_version": "1.0",
  "name": "Hello World",
  "slug": "hello-world",
  "version": "0.1.0",
  "description": "最小插件示例：监听文章发布。",
  "entry": "plugin.py"
}
```

在后台「插件管理」点扫描 → 启用即可。文章发布时日志中会出现上述记录。

---

## 2. 目录规范

```
backend/plugins/
  <slug>/
    __init__.py           ← 空文件；使插件成为 Python 包
    plugin.py             ← register() 所在（文件名由 manifest.entry 指定，默认 plugin.py）
    rosetta-plugin.json   ← 必填：插件清单
    README.md             ← 可选：使用说明（不进入后台文档浏览器）
    requirements.txt      ← 可选：第三方依赖，建议锁定精确版本
```

- 目录名 = `slug`，规范：`^[a-z0-9-]{3,64}$`（小写字母、数字、连字符）
- 内建插件位于 `backend/plugins/`；ZIP / 市场安装的插件解压到同一目录

---

## 3. 插件清单 rosetta-plugin.json

清单由 `RosettaPluginManifest`（`backend/schemas/manifest.py`）校验。

### 3.1 完整字段参考

| 字段 | 必填 | 类型 / 默认 | 说明 |
| --- | --- | --- | --- |
| `manifest_version` | | `"1.0"` | 清单格式版本 |
| **`name`** | ✅ | string | 显示名 |
| **`slug`** | ✅ | `^[a-z0-9-]{3,64}$` | 与目录名一致 |
| **`version`** | ✅ | semver `x.y.z` | 语义化版本，支持预发布后缀 |
| `requires_rosetta` | | `">=1.0.0"` | 所需 Rosetta 版本范围（PEP 440 风格） |
| `description` | | string | 一句话描述 |
| `description_i18n` | | `{lang: string}` | 多语言描述（`zh/en/ja/zh_Hant`） |
| `author` | | `{"name", "uri"}` | 作者对象 |
| `author_name` | | string | 作者名简写 |
| `plugin_uri` | | string | 插件主页 |
| `author_uri` | | string | 作者主页 |
| `textdomain` | | 默认 = `slug` | 翻译文本域 |
| `tags` | | string[] | 关键词 |
| `category` | | enum | `seo/performance/content/social/media/security/utility/integration/publishing/customization/editorial` |
| `settings_schema` | | JSON Schema | 插件设置结构，见 §10 |
| `screenshot_urls` | | string[] | 截图地址 |
| `dependencies` | | object[] | 依赖插件，元素形如 `{"slug": "other-plugin"}` |
| `entry` | | `"plugin.py"` | 入口文件 |
| `hooks` | | string[] | **声明性文档**：本插件使用的钩子名（供市场/审计展示，不参与注册） |
| `admin_menu` | | object | 后台菜单项，见 §7.5 |

> **关于旧字段**：`id`、`entrypoint`、`license`、`compatibility`、`conflicts`、
> 菜单中的 `iconName` 均**不是**当前 schema 字段（校验策略为 `extra="ignore"`，
> 写了也会被忽略）。请改用 `requires_rosetta`、`admin_menu.icon` 等当前字段。

### 3.2 清单示例

```json
{
  "manifest_version": "1.0",
  "name": "My Plugin",
  "slug": "my-plugin",
  "version": "0.1.0",
  "requires_rosetta": ">=2.1.0",
  "description": "插件用途的一句话描述。",
  "author": { "name": "Your Name", "uri": "https://example.com" },
  "category": "utility",
  "tags": ["sample"],
  "entry": "plugin.py",
  "hooks": ["post.published", "the_content"],
  "settings_schema": {
    "type": "object",
    "properties": {
      "my_option": { "type": "string", "default": "hello" }
    }
  },
  "admin_menu": {
    "label": "我的插件",
    "icon": "material-symbols:settings",
    "path": "/admin/plugins/my-plugin/settings"
  }
}
```

---

## 4. 注册入口 register()

### 4.1 签名：同步 / 异步均可

激活插件时，管理器调用 `plugin.py` 中的 `register`。以下写法都被支持：

```python
def register(*args, **kwargs): ...      # 同步（推荐：注册钩子无需 IO）
async def register(*args, **kwargs): ... # 异步（需要启动期 IO 时使用）
```

调用约定（管理器按函数签名自动适配）：

- `register(ctx)` —— 新风格，收到 `PluginContext`
- `register(app, bus)` —— 历史风格，收到 FastAPI app 与 PluginBus
- 参数名显式包含 `ctx` / `app` / `bus` 时按名注入

> 推荐统一使用 **`def register(*args, **kwargs)`** 并忽略入参——钩子直接注册到全局
> 引擎，不依赖 ctx 传递；需要路由时再从参数中识别 ctx（参考内建 `guestbook-rss`）。

### 4.2 幂等铁律

Rosetta 存在两条加载路径（启动期 legacy 扫描 + 激活时沙箱导入），`register()` 可能被
调用多次。**所有注册都必须幂等**：

```python
from backend.core.hooks import add_action, remove_action

def register(*args, **kwargs):
    remove_action("post.published", handler)   # 先按函数引用摘除
    add_action("post.published", handler, priority=10, plugin=PLUGIN_SLUG)
```

- Action / Filter：把处理器定义为**模块级函数**，注册前先 `remove_action/remove_filter`
- Shortcode：注册即 dict 覆盖，天然幂等
- 路由：路由注册表按 slug 去重，重复注册自动跳过

---

## 5. PluginContext API 参考

`register(ctx)` 收到的上下文对象（`backend/core/plugin_loader.py:PluginContext`）。

### 5.1 属性

| 属性 | 说明 |
| --- | --- |
| `ctx.slug` | 插件 slug |
| `ctx.manifest` | 清单字典（来自 rosetta-plugin.json） |
| `ctx.app` | FastAPI 应用实例（只读） |
| `ctx.bus` | PluginBus 兼容门面 |

### 5.2 方法（10 个）

| # | 方法 | 说明 |
| --- | --- | --- |
| 1 | `ctx.add_action(hook, fn, *, priority=10)` | 注册 action（自动标记 plugin=slug） |
| 2 | `ctx.add_filter(hook, fn, *, priority=10)` | 注册 filter |
| 3 | `ctx.register_shortcode(name, fn)` | 注册短代码（默认成对模式） |
| 4 | `ctx.register_admin_router(router)` | 挂到 `/api/admin/plugins/{slug}`，**自动注入管理员鉴权** |
| 5 | `ctx.register_public_router(router)` | 挂到 `/api/plugins/{slug}`，公开访问 |
| 6 | `ctx.register_admin_menu(item)` | 后台侧边栏「插件」分组加菜单项 |
| 7 | `ctx.settings` | 属性：读取设置快照（DB 不可用时返回 `{}`） |
| 8 | `await ctx.set_settings(payload)` | 校验并写入设置 |
| 9 | `await ctx.do_action(hook, *args, **kwargs)` | 主动触发 action |
| 10 | `await ctx.apply_filters(hook, value, *args, **kwargs)` | 主动应用 filter 链 |

---

## 6. 扩展点开发指南

### 6.1 Action（副作用，返回值忽略）

```python
def on_comment_created(comment, db=None, **_kw):
    # 同步回调：禁止阻塞 IO；如需 IO 请定义 async 函数
    print("新评论:", getattr(comment, "id", "?"))

def register(*args, **kwargs):
    from backend.core.hooks import add_action, remove_action
    remove_action("comment.created", on_comment_created)
    add_action("comment.created", on_comment_created, priority=10, plugin=PLUGIN_SLUG)
```

- 处理器可以是同步或异步；同步函数在线程池中执行，不会阻塞事件循环
- 所有处理器在**沙箱**中调用，异常只记录日志，不冒泡到主请求链路
- 处理器显式返回 `False` 可短路后续同钩子 action（扩展语义）
- 执行顺序：priority 升序，同优先级按注册顺序（FIFO）

### 6.2 Filter（值变换，必须返回值）

```python
def add_suffix(title, post=None, language=None, context=None, **_kw):
    if not isinstance(title, str) or title.endswith(" · NEW"):
        return title
    return title + " · NEW"

def register(*args, **kwargs):
    from backend.core.hooks import add_filter, remove_filter
    remove_filter("the_title", add_suffix)
    add_filter("the_title", add_suffix, priority=10, plugin=PLUGIN_SLUG)
```

规则：

- 第一个参数永远是**待变换的值**，必须返回该值（同类型）
- 内容类钩子同时支持 **canonical 名（WordPress 风格）与历史别名**，挂任一即可：

| 内容 | canonical（推荐） | 历史别名 |
| --- | --- | --- |
| 标题 | `the_title` | `post.title` |
| 正文 | `the_content` | `post.content` |
| 摘要 | `the_excerpt` | `post.excerpt` |

- 回调异常时该处理器被跳过，保留当前值继续传递，不会破坏页面

### 6.3 Shortcode（短代码）

在文章里写 `[hello to="World" /]` 即可展开为动态 HTML。

```python
import html as _html

def hello_shortcode(to="World", content="", ctx=None, **_kw):
    return f'<p>Hello, <b>{_html.escape(str(to))}</b>!</p>'

def register(*args, **kwargs):
    from backend.core.shortcodes import register_shortcode
    # 需要 has_paired / description 等完整参数时，直接调用全局注册函数
    register_shortcode("hello", hello_shortcode, plugin=PLUGIN_SLUG,
                       has_paired=False, description='[hello to="World" /]')
```

语法（WordPress 兼容子集）：

- 自闭合：`[hello to="World" /]`
- 成对：`[box cls="warning"]正文[/box]`，内部文本以关键字参数 `content` 传入
- 属性：`k=v` / `k="v"` / `k='v'`；裸词 `flag` 视为 `"True"`
- 名称：`^[A-Za-z_][\w\-]*$`

**安全模型**：

1. 所有短代码输出强制经过**白名单消毒**（零 bleach 依赖，纯 stdlib 实现）：
   允许 `a/blockquote/code/div/h1~h6/hr/img/li/ol/p/pre/span/strong/table` 等结构标签；
   `script/style/iframe/object` 等整段剥离，`onxxx` 事件属性与 `javascript:` 伪协议删除
2. **未注册的短代码原样保留**，不丢弃用户内容

### 6.4 独立路由（前台 / 后台）

```python
from fastapi import APIRouter
from fastapi.responses import Response

def _build():
    public = APIRouter(tags=["My Plugin"])

    @public.get("/feed.xml")
    async def feed():
        return Response("<rss/>", media_type="application/rss+xml")

    admin = APIRouter(tags=["My Plugin Admin"])

    @admin.get("/stats")
    async def stats():
        return {"success": True, "data": {"hits": 1}}

    return public, admin


async def register(ctx=None, **_kwargs):
    if ctx is None:                       # 旧签名 register(app, bus) 兜底
        from backend.core.routing_registry import routing_registry
        public, admin = _build()
        routing_registry.register_public_router(PLUGIN_SLUG, public)
        routing_registry.register_admin_router(PLUGIN_SLUG, admin)
        return
    public, admin = _build()
    ctx.register_public_router(public)    # → /api/plugins/my-plugin/feed.xml
    ctx.register_admin_router(admin)      # → /api/admin/plugins/my-plugin/stats
```

- 后台路由自动加 `get_current_staff` 管理员依赖，无需手写 `Depends`
- 统一挂载之后注册的路由会立即挂载（插件在 lifespan 中加载，晚于核心路由）

### 6.5 后台菜单（admin 侧边栏）

**推荐方式：在 manifest 中声明**，激活时自动注册：

```json
"admin_menu": {
  "label": "我的插件",
  "icon": "material-symbols:settings",
  "path": "/admin/plugins/my-plugin/settings",
  "badge": "new"
}
```

也可在 `register()` 中调用 `ctx.register_admin_menu({...})`（至少含 `label` / `path`）。

- 前端侧边栏通过 `GET /api/admin/plugins/menu-registry` 拉取，在「插件」分组下渲染
  （`composables/usePluginMenu.ts` + `components/admin/AdminSidebar.vue`）
- 菜单 `path` 指向前端页面，例如内建插件 guestbook-rss 的原生设置页
  `/admin/plugins/guestbook-rss/settings`

---

## 7. 钩子目录（完整参考）

以下为当前核心代码真实触发的全部钩子（参数为关键字传参，处理器应使用 `**_kw` 兜底）。

### 7.1 内容 / 文章（Action）

| 钩子 | 触发时机 | 参数 |
| --- | --- | --- |
| `post.created` | 文章新建 | `post`, `current_user`, `db` |
| `post.published` | 文章发布（新建即发布 / 状态切到发布） | 位置参数 `post_id`；`post`, `current_user`, `db` |
| `post.updated` | 文章更新 | `post`, `current_user`, `db` |
| `post.deleted` | 文章删除 | `post`, `current_user`, `db` |
| `post.rendered` | 文章详情渲染完成（纯通知） | `post`, `language`, `title`, `content`, `excerpt`, `context` |

### 7.2 评论（Action）

| 钩子 | 触发时机 | 参数 |
| --- | --- | --- |
| `comment.created` | 新评论提交 | `comment`, `db` |
| `comment.approved` | 评论审核通过 | `comment`, (`current_user`), `db` |
| `comment.spam` | 评论标记垃圾 | `comment`, `db` |
| `comment.deleted` | 评论删除 | `comment`, `current_user`, `db` |

### 7.3 插件生命周期（Action）

| 钩子 | 参数 |
| --- | --- |
| `plugins.scanned` | `added`, `updated`, `slugs` |
| `plugin.installed` | `slug`, `manifest`, `version` |
| `plugin.activated` | `slug`, `row` |
| `plugin.deactivated` | `slug`, `row` |
| `plugin.upgraded` | `slug`, `row` |
| `plugin.deleted` | `slug` |

### 7.4 主题生命周期（Action）

| 钩子 | 参数 |
| --- | --- |
| `themes.scanned` | `added`, `updated` |
| `theme.installed` | `slug`, `manifest`, `version` |
| `theme.activated` | `slug`, `previous` |
| `theme.deleted` | `slug` |
| `theme.upgraded` | `slug`, `row` |
| `theme.mods_saved` | `slug`, `mods` |

### 7.5 Filter

| 钩子（canonical / 别名） | 变换的值 | 上下文参数 |
| --- | --- | --- |
| `the_title` / `post.title` | 标题字符串 | `post`, `language`, `context` |
| `the_content` / `post.content` | 正文 HTML | `post`, `language`, `context` |
| `the_excerpt` / `post.excerpt` | 摘要 HTML | `post`, `language`, `context` |

> 新增钩子命名约定：action 用 `{domain}.{verb}`（如 `post.published`）；
> filter 用 `the_{name}` 或 `{domain}_{property}_filter`。

---

## 8. 生命周期与清理契约

```
扫描 scan  →  安装 install  →  激活 activate  →  运行
                                         ↓
                    停用 deactivate  →  删除 delete
```

| 阶段 | 行为 |
| --- | --- |
| 安装 | 解压 / 登记清单，状态 `installed`；触发 `plugin.installed` |
| 激活 | 导入入口 → 调用 `register()`；状态 `active`；触发 `plugin.activated` |
| 停用 | **按 plugin=slug 摘除全部 action/filter**，摘除其全部 shortcode；状态 `inactive`；触发 `plugin.deactivated` |
| 删除 | 停用（若需要）→ 删除目录与 DB 行；触发 `plugin.deleted` |
| 进程关闭 | `unload_plugins` 对每个插件尽力调用 `deactivate(app, bus)`，再按 slug 兜底摘除钩子 |

**插件作者注意**：

- 停用时钩子与短代码由平台按 slug 自动清理，无需插件自己处理；若插件在 `register()`
  中创建了后台任务 / 打开了资源，可定义 `def deactivate(app, bus): ...`（同步/异步均可）
  做资源回收
- 路由卸载是「尽力而为」：FastAPI 未公开 `remove_router`，停用后已注册的 URL 仍存在，
  但可在路由内部自行检查启用状态

### 冷启动双重加载防护

启动期 legacy 扫描可能已注册钩子/路由；此时激活路径只更新 DB 状态，**不再重复导入**，
避免重复回调与 Duplicate Operation ID。这也是 `register()` 必须幂等的原因。

---

## 9. 去耦合保证

插件与核心通过钩子契约交互，重构保证：

1. 核心请求代码只调用 `bus.do_action()`，不感知插件是否存在；无插件时零开销（一次 dict 查找）
2. 内容渲染统一走 `backend/services/content_renderer.py`（短代码 → filter 链 → action 通知），
   渲染器不依赖 ORM、不修改传入的 post 对象
3. 插件回调异常一律由沙箱隔离，**任何插件错误都不会导致页面 500**
4. 路由 / 菜单 / 设置均经注册表与管理器，插件不直接操作 FastAPI 路由表
5. 插件不提供前台 CSS（避免污染主题与 Admin）；需要样式时由短代码输出内联样式或类名，
   由当前主题承载

---

## 10. 插件设置（KV 存储）

在清单中声明 `settings_schema`（标准 JSON Schema）：

```json
"settings_schema": {
  "type": "object",
  "properties": {
    "max_items": { "type": "integer", "minimum": 1, "maximum": 200, "default": 50 },
    "enabled":   { "type": "boolean", "default": true }
  },
  "additionalProperties": false
}
```

读取 / 写入：

- REST：`GET /api/admin/plugins/{slug}/settings`、`PUT`（全量替换，先补默认值）、
  `PATCH`（增量合并）
- 代码内：`await plugin_manager.get_settings(db, slug)` / `set_settings(db, slug, payload)`
- 写入按 schema 校验，非法值返回 `400 PLUGIN_SETTINGS_INVALID`

> 密钥（token / 密码）禁止存入 settings，应写入 `.env` 经后端配置读取。

---

## 11. 安全规范

插件与主应用共享 Python 进程权限，属于「可信扩展」。请遵守：

### 11.1 代码清单

- ✅ 禁止 `eval / exec` 处理用户输入或 settings
- ✅ SQL 一律使用 SQLAlchemy `select(...)`，禁止拼接 SQL 字符串
- ✅ 短代码输出对用户输入做 `html.escape`（引擎外层还有白名单消毒）
- ✅ 文件写入限定在插件数据目录，用 `Path.resolve()` + `is_relative_to()` 防 `..` 越权
- ✅ 第三方依赖锁定精确版本（`httpx==0.27.0`）

### 11.2 高风险模块

| 模块 | 建议 |
| --- | --- |
| `subprocess` | 仅在必要时使用，参数以列表传递、`shell=False` |
| `os.system` / `popen` | 一律替换为 `subprocess.run([...])` |
| `pickle.loads` | 严禁，用 JSON 替代 |
| `ctypes` / `cffi` | 避免，除非确需原生库 |
| 动态 `importlib.import_module` | 名称必须来自白名单，不可来自用户输入 |

---

## 12. 打包与分发

### 12.1 ZIP 包结构（根目录只有 `<slug>/` 一层）

```
my-plugin-0.1.0.zip
└── my-plugin/
    ├── __init__.py
    ├── plugin.py
    └── rosetta-plugin.json
```

```powershell
Compress-Archive -Path backend/plugins/my-plugin -DestinationPath my-plugin-0.1.0.zip
```

### 12.2 三种安装来源

| 来源 | 接口 |
| --- | --- |
| 本地目录 | `POST /api/admin/plugins?source=local`（body 带 slug，先扫描） |
| ZIP 上传 | `POST /api/admin/plugins?source=upload`（multipart，字段 `file`） |
| 市场远程 | `POST /api/admin/plugins?source=remote`（body 带 `remote.url`，可选 SHA-256 校验）；或 `POST /api/admin/plugins/market/{slug}/install` |

完整请求 / 响应字段与错误码见《[REST API 参考](/admin/docs/rest-api)》。

---

## 13. 内建插件参考实现

| 插件 | 覆盖扩展点 | 位置 |
| --- | --- | --- |
| `hello-rosetta` | Filter `the_title` / `the_content`、Action `post.rendered`、Shortcode `[hello]` | `backend/plugins/hello-rosetta/` |
| `guestbook-rss` | 前台路由 feed.xml、后台路由 settings、admin_menu | `backend/plugins/guestbook-rss/` |
| `seo-toolkit` | Action `post.published`、Filter `the_content` | `backend/plugins/seo-toolkit/` |

开发新插件时建议复制 `hello-rosetta`（钩子型）或 `guestbook-rss`（路由型）目录改名，
再替换清单与处理器。
