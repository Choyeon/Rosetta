# Rosetta 插件开发教程

> 版本：1.0.0 · 最后更新：2026-08-28 · 语言：zh-CN

Rosetta 的插件系统基于 **钩子引擎（Hooks: Action / Filter）+ 短代码引擎（Shortcode）+ 独立路由注册 + 插件设置 KV 存储** 五件套构建。
每个插件是 `backend/plugins/<slug>/` 下的一个 Python 包，注册入口为单个异步函数 `register(ctx)`。
本文以 **`guestbook-rss`** 示例插件为主线，完整演示五类扩展点的最小代码写法，并给出安全提示与打包规范。

---

## 1. 目录规范

```
backend/plugins/
  guestbook-rss/
    __init__.py           ← 空文件即可；使插件成为 Python 包
    plugin.py             ← register(ctx) 实现所在；由 entrypoint 指定
    rosetta-plugin.json   ← 必填：插件清单（manifest）
    README.md             ← 可选：使用说明
    requirements.txt      ← 可选：第三方依赖清单（建议锁定版本）
```

- 目录名 = `slug`，正则：`^[a-z][a-z0-9\-]{1,48}$`
- `rosetta-plugin.json` 通过 `RosettaPluginManifest` 校验（见 `backend/schemas/manifest.py`）
- Python 入口通过 `entrypoint: "module:callable"` 指定，通常写为 `plugin:register`

### rosetta-plugin.json 示例（guestbook-rss）

```json
{
  "id": "io.github.rosetta.guestbook-rss",
  "slug": "guestbook-rss",
  "name": "Guestbook RSS",
  "version": "0.1.0",
  "description": "为 Rosetta 留言板生成 RSS 2.0 订阅源，并提供一个后台设置页。",
  "author": "Rosetta",
  "license": "MIT",
  "entrypoint": "plugin:register",
  "dependencies": [],
  "settings_schema": {
    "type": "object",
    "properties": {
      "feed_title":    { "type": "string", "default": "Rosetta 留言板 RSS" },
      "feed_language": { "type": "string", "default": "zh-cn" },
      "max_items":     { "type": "integer", "default": 50, "minimum": 10, "maximum": 500 },
      "enable_ttl":    { "type": "boolean", "default": true }
    },
    "additionalProperties": false
  },
  "admin_menu": {
    "label": "留言板 RSS",
    "iconName": "rss",
    "path": "/admin/plugins/guestbook-rss/settings",
    "badge": "new"
  },
  "tags": ["rss", "guestbook", "syndication"],
  "compatibility": {
    "min_rosetta": "1.0.0"
  }
}
```

清单字段（必含加粗）：

| 字段 | 说明 |
| --- | --- |
| `id` | 反向域名式唯一 ID |
| **`slug`** | 与目录名一致 |
| **`name`** | 显示名 |
| **`version`** | 语义化版本 |
| **`description`** | 一句话描述 |
| **`author`** | 作者 |
| **`license`** | SPDX 协议 |
| **`entrypoint`** | `module:async_func` 形式，默认为 `plugin:register` |
| `dependencies` | 依赖的其它插件 slug 数组；激活时按顺序自动激活 |
| `settings_schema` | JSON Schema；插件设置 PUT/PATCH 时由后端校验 |
| `admin_menu` | 后台侧边栏菜单项（Sidebar 由 `usePluginMenuGroup` 拉取渲染） |
| `tags` | 关键词数组 |
| `compatibility.min_rosetta / max_rosetta` | 兼容性 |

---

## 2. `register(ctx)` 提供的 11 个能力

插件启动（`bootstrap_extensions` 扫描 → 激活 → import → 调用 entrypoint）时，
Rosetta 会把一个 `PluginContext` 对象作为唯一参数传给 `register(ctx)`。该上下文是插件与平台交互的唯一通道，提供以下 11 个能力：

| # | 能力 | 方法签名 | 说明 |
| --- | --- | --- | --- |
| 1 | 注册 Action | `ctx.add_action(hook: str, fn, priority: int = 10)` | 在某个执行点触发副作用 |
| 2 | 注册 Filter | `ctx.add_filter(hook: str, fn, priority: int = 10)` | 对某个值做变换并返回 |
| 3 | 注册 Shortcode | `ctx.register_shortcode(tag: str, fn, *, has_paired: bool = True, description=None)` | 注册 `[tag]...[/tag]` 或 `[tag /]` |
| 4 | 注册后台路由 | `ctx.register_admin_router(router: APIRouter)` | 路由自动挂到 `/api/admin/plugins/<slug>/`，并注入管理员鉴权依赖 |
| 5 | 注册前台路由 | `ctx.register_public_router(router: APIRouter)` | 路由自动挂到 `/api/plugins/<slug>/`，公开访问 |
| 6 | 注册后台菜单 | `ctx.register_admin_menu({label, iconName, path, badge})` | Sidebar 「插件」分组中显示一个菜单项 |
| 7 | 读取设置 | `await ctx.get_settings(db) -> dict` | 读取插件 KV 设置（已包含 schema defaults） |
| 8 | 写入设置 | `await ctx.set_settings(db, payload: dict)` | 按 settings_schema 校验后写入 |
| 9 | 读取当前主题 mods | `await ctx.get_mods(db, slug?) -> dict` | 读取指定主题或当前激活主题的 mods |
| 10 | 触发 Action | `ctx.do_action(hook, *args, **kwargs)` | 主动触发一个钩子广播 |
| 11 | 应用 Filter | `ctx.apply_filters(hook, value, *args, **kwargs)` | 主动把值通过过滤器链跑一遍 |

> 注意：`register()` 是 **async** 函数。如需做耗时 IO（建表、拉 HTTP），
> 建议用 `asyncio.create_task` 放到后台，避免阻塞应用启动。

---

## 3. 五类扩展点各自最小示例

### 3.1 Action（动作：做副作用，返回值被忽略）

```python
# plugin.py
from __future__ import annotations
import logging

log = logging.getLogger(__name__)

async def register(ctx):
    async def on_post_published(post, **_):
        log.info("[guestbook-rss] 文章已发布: %s", getattr(post, "slug", "?"))
    ctx.add_action("post.published", on_post_published, priority=20)
```

常见内置钩子：`post.published / post.rendered / plugin.installed / theme.activated / shutdown`。

### 3.2 Filter（过滤器：必须返回变换后的值）

```python
async def register(ctx):
    def title_suffix(title: str, post, **_) -> str:
        return f"{title} · RSS 订阅可用"
    ctx.add_filter("post.title", title_suffix, priority=10)
```

Filter 回调的第一个参数永远是「待变换的值」；后续参数是上下文（如 `post`、`site_id` 等）。**必须返回同类型值**，否则破坏链式语义。

### 3.3 Shortcode（短代码）

```python
from __future__ import annotations
import html

async def register(ctx):
    def rss_link(href="#", text="订阅留言板 RSS", **_):
        safe_href = html.escape(href, quote=True)
        safe_text = html.escape(text)
        return f'<a href="{safe_href}" rel="noopener" class="rss-link">{safe_text}</a>'
    ctx.register_shortcode("rss-link", rss_link, has_paired=False,
                           description="[rss-link href=/api/plugins/guestbook-rss/feed.xml /]")
```

短代码可以自闭合 `[rss-link /]`，也可以成对 `[warning]...[/warning]`；
**函数参数名 = 短代码属性名**；内容对的内部文本以关键字参数 `content` 传入（当 `has_paired=True`）。

### 3.4 独立后台页

```python
from __future__ import annotations
from fastapi import APIRouter, Depends
from backend.core.auth import CurrentStaff
from backend.core.database import AsyncSession as DB

async def register(ctx):
    admin = APIRouter(tags=["Guestbook RSS Admin"])

    @admin.get("/settings")
    async def get_settings(db: DB, _: CurrentStaff):
        return {"success": True, "data": await ctx.get_settings(db)}

    @admin.put("/settings")
    async def put_settings(payload: dict, db: DB, _: CurrentStaff):
        await ctx.set_settings(db, payload)
        return {"success": True}

    ctx.register_admin_router(admin)
    ctx.register_admin_menu(ctx.manifest.get("admin_menu") or {
        "label": "留言板 RSS",
        "path": "/admin/plugins/guestbook-rss/settings",
        "iconName": "rss"
    })
```

- 路由前缀自动拼接为 `/api/admin/plugins/guestbook-rss/settings`
- 自动注入管理员依赖（`require_admin`），无需手动写 Depends
- 前端统一承载页为 `frontend/pages/admin/plugins/[slug]/[...catchall].vue`（iframe / 代理均可）

### 3.5 独立前台路由

```python
from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import Response
from sqlalchemy import select
from backend.core.database import async_session_maker
from backend.models.guestbook import Guestbook

async def register(ctx):
    public = APIRouter(tags=["Guestbook RSS Public"])

    @public.get("/feed.xml", response_class=Response)
    async def feed():
        settings = ctx.settings or {}
        limit = int(settings.get("max_items", 50))
        async with async_session_maker() as db:
            rows = (await db.execute(
                select(Guestbook)
                .order_by(Guestbook.created_at.desc())
                .limit(limit)
            )).scalars().all()
        xml = _build_rss(rows, settings)
        return Response(xml, media_type="application/rss+xml; charset=utf-8")

    ctx.register_public_router(public)
```

路由自动挂载为 `/api/plugins/guestbook-rss/feed.xml`，对外公开可访问。

---

## 4. 安全提示

Rosetta 插件拥有与主应用相同的 Python 进程权限，插件本身即是「可信扩展」而非浏览器沙箱脚本。
为了减少供应链风险，作者与站点管理员请遵守以下实践：

### 4.1 代码安全清单

- ✅ 不要 `eval(...)` / `exec(...)` settings 或用户输入，包括 `ast.literal_eval` 之外的动态编译
- ✅ 不要在 settings 里保存密钥（access token / SMTP 密码等），建议写入 `.env` 并通过 `settings.read_secrets()` 读取
- ✅ SQL 查询统一使用 SQLAlchemy ORM / Core（`select(...)`），严禁拼接 SQL 字符串
- ✅ 所有短代码输出必须对用户输入做 `html.escape`；核心引擎外层会走 bleach 白名单，但内层转义能降低疏忽带来的 XSS 风险
- ✅ 对文件系统写入：限定目录在 `BACKEND_ROOT/data/plugins/<slug>/` 内，使用 `Path.resolve().is_relative_to()` 做 `..` 越权检测
- ✅ 第三方依赖尽量锁定精确版本（`requirements.txt` 写 `httpx==0.27.0`，不要写 `httpx>=0.20`）

### 4.2 高风险模块建议避免 / 最少权限使用

| 模块 | 风险等级 | 建议 |
| --- | --- | --- |
| `subprocess` | 极高 | 仅在确需调用可执行文件（如 image magick）时使用，且参数必须用 `shlex.quote` 或列表形式传参 |
| `os.system` / `popen` | 极高 | 一律替换为 `subprocess.run([...], shell=False)` |
| `sys` | 中 | 只读 `sys.version` / `sys.platform` 可以；不要 `sys.exit` / `sys.modules[...] = ...` 动态改模块表 |
| `ctypes` / `cffi` | 高 | 避免；除非确实需要调用原生库 |
| 动态 `importlib.import_module(name)` | 中高 | `name` 必须限制为白名单字符串，不可来自用户输入 / settings |
| `pickle.loads(...)` | 极高 | 严禁；JSON 替代序列化 |

### 4.3 插件激活前的边界检查

后端 `PluginManager.activate()` 会做：
1. manifest schema 校验
2. 依赖 plugins 的激活顺序与存在性检查
3. 互斥性（若有 `conflicts` 声明则拒绝）
4. `settings_schema` 校验默认值并初始化 KV 行

但 **不会** 拦截插件代码内部的高风险调用；这需要通过代码审计 + 只从官方市场安装来规避。

---

## 5. 完整示例（guestbook-rss）

把前述的 manifest + 五类扩展点示例合并，得到一个覆盖所有扩展点的 `plugin.py`：

```python
"""guestbook-rss 插件：Action + Filter + Shortcode + 后台页 + 前台路由 全覆盖。"""
from __future__ import annotations

import html
import logging
from xml.sax.saxutils import escape as xml_escape

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select

from backend.core.auth import CurrentStaff
from backend.core.database import AsyncSession as DB, async_session_maker
from backend.models.guestbook import Guestbook

log = logging.getLogger(__name__)


def _build_rss(rows, settings: dict) -> str:
    title = xml_escape(settings.get("feed_title") or "Rosetta 留言板 RSS")
    lang = xml_escape(settings.get("feed_language") or "zh-cn")
    items_xml = []
    for r in rows:
        ts = (r.created_at.isoformat() if hasattr(r, "created_at") and r.created_at else "")
        items_xml.append(
            "<item>"
            f"<title>#{getattr(r, 'id', '?')} · {xml_escape(str(getattr(r, 'nickname', '')))}</title>"
            f"<description>{xml_escape(str(getattr(r, 'content', '') or ''))}</description>"
            f"<pubDate>{ts}</pubDate>"
            f"<guid>guestbook-{getattr(r, 'id', '?')}</guid>"
            "</item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0"><channel>'
        f"<title>{title}</title>"
        f"<language>{lang}</language>"
        + ("".join(items_xml))
        + "</channel></rss>"
    )


async def register(ctx):
    # 1) Action：文章发布时打日志
    async def on_post_published(post, **_):
        log.info("[guestbook-rss] 新文章发布: slug=%s", getattr(post, "slug", "?"))
    ctx.add_action("post.published", on_post_published, priority=20)

    # 2) Filter：统一在站点副标题末尾加 RSS 提示
    def site_subtitle_suffix(value: str, **_) -> str:
        if "RSS" in (value or ""):
            return value
        return f"{value or ''} · 留言板支持 RSS 订阅"
    ctx.add_filter("site.subtitle", site_subtitle_suffix)

    # 3) Shortcode：[rss-link href=/api/plugins/guestbook-rss/feed.xml text=订阅 /]
    def sc_rss_link(href: str = "/api/plugins/guestbook-rss/feed.xml",
                    text: str = "订阅留言板 RSS", **_):
        return (
            f'<a class="rss-link" href="{html.escape(href, quote=True)}" '
            f'rel="noopener noreferrer" target="_blank">'
            f'{html.escape(text)}</a>'
        )
    ctx.register_shortcode("rss-link", sc_rss_link, has_paired=False)

    # 4) 后台路由 + 菜单
    admin = APIRouter(tags=["Guestbook RSS Admin"])

    @admin.get("/settings")
    async def get_settings(db: DB, _: CurrentStaff):
        return {"success": True, "data": await ctx.get_settings(db)}

    @admin.put("/settings")
    async def put_settings(payload: dict, db: DB, _: CurrentStaff):
        await ctx.set_settings(db, payload)
        return {"success": True}

    ctx.register_admin_router(admin)
    ctx.register_admin_menu(
        ctx.manifest.get("admin_menu")
        or {
            "label": "留言板 RSS",
            "iconName": "rss",
            "path": "/admin/plugins/guestbook-rss/settings",
            "badge": "new",
        }
    )

    # 5) 公开前台路由：RSS XML
    public = APIRouter(tags=["Guestbook RSS Public"])

    @public.get("/feed.xml", response_class=Response)
    async def feed():
        settings = ctx.settings or {}
        limit = int(settings.get("max_items", 50))
        async with async_session_maker() as db:
            rows = (
                await db.execute(
                    select(Guestbook)
                    .order_by(Guestbook.created_at.desc())
                    .limit(limit)
                )
            ).scalars().all()
        return Response(_build_rss(rows, settings),
                        media_type="application/rss+xml; charset=utf-8")

    ctx.register_public_router(public)
    log.info("[guestbook-rss] 插件注册完成")
```

### 打包发布

1. 打包为 ZIP（根目录下只有 `<slug>/` 一层）：

   ```bash
   cd backend/plugins
   zip -r guestbook-rss-0.1.0.zip guestbook-rss
   ```

2. 通过后台「插件管理 → ZIP 上传」或官方市场提交后，即可一键安装。

> 本插件是 Rosetta 内置示例插件的完整参考，位于 `backend/plugins/guestbook-rss/`。
> 开发新插件时可直接复制该目录改名为你的 slug，再替换清单文件即可。
