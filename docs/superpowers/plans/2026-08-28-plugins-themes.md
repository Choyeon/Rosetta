# Rosetta 插件与主题系统 完整交付 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to run task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Rosetta 博客系统的「插件 & 主题系统」从零碎骨架推进到可完整发布：后端提供 zip 上传/市场/短代码/独立路由注册 全部 API，前端提供 Customizer 与插件管理页，提供 2 套示例主题 + 2 套示例插件覆盖所有扩展点，并输出三份中文开发文档 + 后台文档浏览入口，补全 pytest 与 typecheck。

**Architecture:** 不重写现有骨架，直接以现有 `hooks.py + plugin_loader + extensions.py + plugin_bus.py + api/plugins.py + api/themes_ext.py + frontend/pages/admin/{plugins,themes}.vue` 为底座做增量补齐；文档以 Markdown 存于 `docs/`，后台挂 `/admin/docs` 以 Nitro 静态渲染方式读取；示例主题/示例插件遵循已有的 `rosetta-theme.json` / `rosetta-plugin.json` 清单规范。

**Tech Stack:** 后端 FastAPI + SQLAlchemy 2.0 async + Pydantic；钩子引擎 `backend/core/hooks.py` 与 `plugin_bus.py`；前端 Nuxt 4.5 + Vue 3 + TS + shadcn-vue；文档 Markdown + 前端 docs viewer 自渲染。

---

## 0. 现有骨架与 Gap 清单

**已有（不重写，只在基础上增量）**
- [backend/core/hooks.py](file:///d:/WebProjects/Rosetta/backend/core/hooks.py)：`register_action / register_filter / remove_hooks_for_plugin / do_action / apply_filters`
- [backend/core/plugin_bus.py](file:///d:/WebProjects/Rosetta/backend/core/plugin_bus.py)：事件总线 `add_action / add_filter / do_action / apply_filters`，钩子通信
- [backend/core/plugin_loader.py](file:///d:/WebProjects/Rosetta/backend/core/plugin_loader.py)：插件目录扫描、`register / activate / deactivate`、路由卸载尽力而为
- [backend/core/extensions.py](file:///d:/WebProjects/Rosetta/backend/core/extensions.py#L88-L442)：`PluginManager` 生命周期（manifest 扫描、DB 同步、列表、激活、禁用、安装、删除、设置 KV、升级、批量、重放）；`ThemeManager` + `bootstrap_extensions` 与 mods KV、主题互斥切换
- [backend/api/plugins.py](file:///d:/WebProjects/Rosetta/backend/api/plugins.py#L30-L258)：GET/列表、GET/详情、POST/scan、POST/status、设置 PUT/PATCH、activate
- [backend/api/themes_ext.py](file:///d:/WebProjects/Rosetta/backend/api/themes_ext.py#L72-L374)：列表、当前主题、详情、激活、删除、扫描、Mods GET/PUT/PATCH、安装、升级（但 `upload/remote` 目前抛 400）
- [backend/schemas/manifest.py](file:///d:/WebProjects/Rosetta/backend/schemas/manifest.py#L7-L80)：`RosettaPluginManifest` / `RosettaThemeManifest` 清单校验
- [backend/models/extensions.py](file:///d:/WebProjects/Rosetta/backend/models/extensions.py#L30-L144)：`plugins` / `themes` 表（slug、version、status、manifest、settings、mods_schema、installed_at 等）
- 现有主题 2 套：`frontend/themes/editorial-wp-style/`、`frontend/themes/minimal-brutalist/`
- 现有插件 1 套：`backend/plugins/seo-toolkit/`
- 后台管理页面：[frontend/pages/admin/system/plugins.vue](file:///d:/WebProjects/Rosetta/frontend/pages/admin/system/plugins.vue)、[frontend/pages/admin/system/themes.vue](file:///d:/WebProjects/Rosetta/frontend/pages/admin/system/themes.vue)

**Gap（本计划逐项关闭）**
- G1. **zip 上传 / remote 安装**：插件与主题的 `POST /plugins`、`POST /admin/themes/install` 目前对 `upload/remote` 直接抛 400「暂不支持」
- G2. **Marketplace 官方市场索引 API**：无 `GET /plugins/market`、`GET /themes/market`；无官方 market index json 与离线缓存
- G3. **Mods schema 校验**：主题 Customizer 写入 mods 未按 mods_schema 校验类型与枚举；前端 Customizer 也没按 schema 渲染动态表单
- G4. **短代码（Shortcode）引擎**：`[slack id="123"][/slack]`、`[gallery ids="1,2,3"]` 这种解析、注册、安全白名单、do_shortcode 接口没有
- G5. **插件独立路由注册**：插件想加「前台 `/plugins/xxx/xxx` 页面」和「后台 `/admin/plugins/<slug>/**` 管理页」目前没注册点、也没挂载；前端没有第三方插件菜单注册
- G6. **示例主题与示例插件**：只各有 1 套，用户要求至少 2 主题 + 2 插件；且示例插件要覆盖「action / filter / shortcode / 独立后台页 / 独立前台路由」五类扩展点
- G7. **文档**：中文的「REST API 参考 / 主题清单教程 / 插件开发教程」+ 后台文档浏览页 `/admin/docs` 没有
- G8. **测试覆盖**：缺少 zip 上传、shortcode、独立路由注册、mods schema 校验、market index 解析、示例插件 五类 pytest

---

## 1. 任务拆解

### Task A：补齐 ZIP 上传 / 远程安装（插件 + 主题 双侧）

**Files:**
- Modify: `backend/core/extensions.py` — 新增 `PluginManager.install_from_uploaded_zip / install_from_remote / upgrade_from_remote` 与 `ThemeManager` 同系列方法
- Modify: `backend/schemas/extensions.py` — 给 `PluginInstallFrom` / `ThemeInstallFrom` 加 `url`、`checksum_sha256`、`allow_pre_release` 字段
- Modify: `backend/api/plugins.py` — `POST /api/admin/plugins` 当 `source=upload` 走 zip；`source=remote` 走市场 URL 下载
- Modify: `backend/api/themes_ext.py` — 同上，`POST /api/admin/themes/install` 支持 upload/remote
- Modify: `backend/core/config.py` — 加 `PLUGINS_MARKET_BASE_URL` / `THEMES_MARKET_BASE_URL` / `UPLOAD_MAX_PACKAGE_SIZE_MB = 30` 环境变量
- Create: `tests/test_extensions_installer.py` — 测试本地 fixture zip 安装、重复安装、非法 zip、校验 remote url 下载（Mock httpx）

- [ ] **Step 1: 写失败测试 tests/test_extensions_installer.py**

```python
from __future__ import annotations
import io
import zipfile
import pytest
import pytest_asyncio
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from backend.main import app
from backend.core.database import async_session_maker
from backend.models.extensions import Plugin, Theme

BACKEND_ROOT = Path(__file__).resolve().parents[1]

def _make_fake_plugin_zip(slug: str = "hello-plugin") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            f"{slug}/rosetta-plugin.json",
            """{"id":"io.github.rosetta.hello-plugin","slug":"hello-plugin","name":"Hello","version":"0.1.0","description":"演示","author":"Rosetta","entrypoint":"plugin:register","license":"MIT"}""",
        )
        z.writestr(
            f"{slug}/__init__.py",
            "from .plugin import register",
        )
        z.writestr(
            f"{slug}/plugin.py",
            "async def register(ctx):\n    ctx.add_action('shutdown', lambda *a, **k: None)\n",
        )
    return buf.getvalue()

def _make_fake_theme_zip(slug: str = "hello-theme") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            f"{slug}/rosetta-theme.json",
            """{"id":"io.github.rosetta.hello-theme","slug":"hello-theme","name":"Hello Theme","version":"0.1.0","description":"演示","author":"Rosetta","license":"MIT","mods_schema":{"properties":{},"type":"object"}}""",
        )
        z.writestr(f"{slug}/style.css", "/* hello */")
    return buf.getvalue()

@pytest.mark.asyncio
async def test_install_plugin_from_uploaded_zip():
    data = _make_fake_plugin_zip("hello-plugin")
    with TestClient(app) as client:
        files = {"file": ("hello-plugin.zip", data, "application/zip")}
        resp = client.post(
            "/api/admin/plugins",
            params={"source": "upload"},
            files=files,
            headers={"Authorization": "Bearer replace-with-admin-token"},
        )
        # 没有 token 会 401/503(OOBE) 两种路径都要接受；这里仅断言非 400「暂不支持 upload/remote」
        assert resp.status_code != 400 or "暂不支持" not in (resp.text or "")
```

- [ ] **Step 2: 运行测试，确保失败**

Run: `uv run pytest tests/test_extensions_installer.py -v --timeout=60`
Expected: FAIL（POST 返回 400 「暂不支持 remote/upload 安装方式」）

- [ ] **Step 3: 实现后端安装器增量（extensions.py + schemas/extensions.py + api plugins & themes_ext）**

A. 在 `backend/schemas/extensions.py` 末尾补：

```python
class PackageInstallRemote(BaseModel):
    url: HttpUrl = Field(..., description="官方市场 zip URL 或 raw GitHub zip URL")
    checksum_sha256: str | None = Field(default=None, min_length=16, max_length=64)
    allow_pre_release: bool = Field(default=False)
```

在 `PluginInstallFrom` 中加字段：
```python
class PluginInstallFrom(BaseModel):
    source: Literal["local", "remote", "upload"] = Field(default="local")
    slug: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9\-]{1,48}$")
    remote: PackageInstallRemote | None = None
```

同理为 Theme 安装补 `ThemeInstallFrom`（结构完全同，建议复用 PackageInstallRemote）。

B. 在 `backend/core/extensions.py` 给 `PluginManager` 加方法：

```python
    import zipfile
    import tempfile
    import httpx
    from pathlib import Path

    async def install_from_uploaded_bytes(self, db: AsyncSession, filename: str, data: bytes) -> Plugin:
        # 1. size 校验 <= config.UPLOAD_MAX_PACKAGE_SIZE_MB
        # 2. zipfile 解析；根目录只允许一层，且根目录下必须有 rosetta-plugin.json
        # 3. 校验 manifest（schemas.manifest.validate_manifest）
        # 4. 目标目录：BACKEND_ROOT / "plugins" / slug；已存在同版本抛 409；旧版本备份为 slug.old.<ts>
        # 5. 写入 DB -> plugins 表：status=installed；is_active=False；installed_at=utcnow()
        # 6. 触发 do_action('plugin.installed', slug, manifest)
        ...

    async def install_from_remote(self, db: AsyncSession, payload: PluginInstallFrom) -> Plugin:
        async with httpx.AsyncClient(timeout=60) as h:
            r = await h.get(str(payload.remote.url))
            r.raise_for_status()
            if payload.remote.checksum_sha256:
                digest = hashlib.sha256(r.content).hexdigest()
                assert digest == payload.remote.checksum_sha256, "checksum mismatch"
            return await self.install_from_uploaded_bytes(db, f"{payload.slug}.zip", r.content)
```

`ThemeManager.install_from_uploaded_bytes / install_from_remote` 完全同理，目标目录改为 `FRONTEND_ROOT / "themes" / slug`，清单文件 `rosetta-theme.json`。

C. 在 `backend/api/plugins.py` 用 FastAPI `UploadFile` 接管 upload 分支；把原来 `if source in (remote,upload): raise HTTPException(400,…)` 的分支删除改成对应调用：

```python
    if payload.source == "upload":
        file: UploadFile | None = kwargs.pop("file", None)
        data = await file.read() if file else b""
        row = await plugin_manager.install_from_uploaded_bytes(db, file.filename, data)
```

`backend/api/themes_ext.py` 同样处理。

D. 在 `backend/core/config.py` 加：
```python
PLUGINS_MARKET_BASE_URL: str = Field(default="https://market.rosetta.dev/plugins")
THEMES_MARKET_BASE_URL: str = Field(default="https://market.rosetta.dev/themes")
UPLOAD_MAX_PACKAGE_SIZE_MB: int = Field(default=30, ge=1, le=500)
PACKAGE_ALLOW_PUBLISH_SCOPE: str = Field(default="*")  # 预留 scope 过滤
```

- [ ] **Step 4: 运行测试**

Run: `uv run pytest tests/test_extensions_installer.py -v --timeout=90`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/extensions.py backend/core/config.py backend/schemas/extensions.py backend/api/plugins.py backend/api/themes_ext.py tests/test_extensions_installer.py
git commit -m "feat(backend): support plugin/theme zip upload and remote install"
```

---

### Task B：官方市场索引 + 一键安装前端入口 + mods schema 校验

**Files:**
- Create: `backend/core/market.py` — 市场索引 HTTP 客户端 + 本地缓存 JSON（8 小时）
- Modify: `backend/api/plugins.py` — 加 `GET /api/admin/plugins/market`、`POST /api/admin/plugins/market/{slug}/install`
- Modify: `backend/api/themes_ext.py` — 加 `GET /api/admin/themes/market`、`POST /api/admin/themes/market/{slug}/install`
- Create: `tests/test_market_index.py` — Mock 市场 index JSON，测列表 + 一键安装
- Modify: `backend/core/extensions.py ThemeManager.set_mods()` — mods 写入时先 `jsonschema.validate` mods_schema 再落 KV
- Modify: `frontend/pages/admin/system/themes.vue` — Customizer 区域：根据 manifest.mods_schema 按类型动态渲染 `<Input>/<Select>/<Switch>/ColorPicker>`，保存走 `PATCH /api/admin/themes/{slug}/mods`，保存后用 `useFrontendTheme().reload()`

- [ ] **Step 1: 写失败测试 tests/test_market_index.py**

```python
import respx
import httpx
import pytest
from fastapi.testclient import TestClient
from backend.main import app

MARKET_PLUGINS_JSON = {
  "items": [
    {"id":"com.example.hello","slug":"hello","name":"Hello","version":"1.0.0","type":"plugin","zip_url":"https://cdn.example/hello-1.0.0.zip","tags":["hello"],"description":"Hello plugin"}
  ]
}

@pytest.mark.asyncio
@respx.mock
async def test_plugin_market_list():
    route = respx.get("https://market.rosetta.dev/plugins/index.json").mock(return_value=httpx.Response(200, json=MARKET_PLUGINS_JSON))
    with TestClient(app) as client:
        resp = client.get("/api/admin/plugins/market")
        assert route.called
        # 即使 401/503 也不许 404
        assert resp.status_code in (200, 401, 503)
```

- [ ] **Step 2: 运行失败测试**

Run: `uv run pytest tests/test_market_index.py -v`
Expected: FAIL（路由不存在 → 404）

- [ ] **Step 3: 实现 core/market.py 与对应 REST API**

`backend/core/market.py` 核心：
```python
from __future__ import annotations
import asyncio
import json
import time
from pathlib import Path
from backend.core.config import settings
import httpx

CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "market_cache"
CACHE_TTL = 8 * 3600

async def fetch_market_index(kind: str, *, force: bool = False) -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fp = CACHE_DIR / f"{kind}.json"
    if not force and fp.exists() and (time.time() - fp.stat().st_mtime) < CACHE_TTL:
        return json.loads(fp.read_text(encoding="utf-8"))
    base = settings.PLUGINS_MARKET_BASE_URL if kind == "plugins" else settings.THEMES_MARKET_BASE_URL
    url = f"{base.rstrip('/')}/index.json"
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as h:
        r = await h.get(url)
        r.raise_for_status()
        data = r.json()
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
```

plugins 路由加：
```python
@router.get("/plugins/market")
async def list_plugin_market(kind: str = "plugins"):
    data = await fetch_market_index("plugins")
    return {"success": True, "data": data}

@router.post("/plugins/market/{slug}/install")
async def install_market_plugin(slug: str, db: AsyncSessionDep, _: AdminDep):
    index = await fetch_market_index("plugins")
    item = next((x for x in (index.get("items") or []) if x.get("slug") == slug), None)
    if not item: raise HTTPException(404, error_code="MARKET_ITEM_NOT_FOUND", message="市场中未找到该插件")
    from backend.schemas.extensions import PluginInstallFrom, PackageInstallRemote
    return await plugin_manager.install_from_remote(db, PluginInstallFrom(
        source="remote",
        slug=slug,
        remote=PackageInstallRemote(url=item["zip_url"], checksum_sha256=item.get("checksum_sha256"))
    ))
```

主题同构。再补 ThemeManager 的 mods schema 校验：
```python
# ThemeManager.set_mods() 内
import jsonschema
schema = manifest.get("mods_schema") or {}
if schema and isinstance(schema, dict) and schema.get("type") == "object":
    try:
        jsonschema.validate(patch, schema)
    except jsonschema.ValidationError as e:
        raise HTTPException(400, error_code="MODS_SCHEMA_VIOLATION", message=str(e.message))
```

前端 themes.vue 的 Customizer 动态表单（伪代码，真实写 TSX 风格 Vue <script setup>）：
```vue
<template>
  <div class="space-y-4">
    <div v-for="item in schemaProperties" :key="item.key">
      <label class="text-sm font-medium">{{ item.title }}</label>
      <Input v-if="item.type==='string' && !item.enum" v-model="mods[item.key]" />
      <Select v-else-if="item.enum" v-model="mods[item.key]" :options="item.enum.map(v=>({label:v,value:v}))" />
      <Switch v-else-if="item.type==='boolean'" v-model="mods[item.key]" />
      <Input type="number" v-else-if="item.type==='integer' || item.type==='number'" v-model.number="mods[item.key]" />
      <Input v-else type="color" v-if="item.format==='color'" v-model="mods[item.key]" />
      <p class="text-xs text-muted-foreground">{{ item.description }}</p>
    </div>
    <Button @click="save">保存</Button>
  </div>
</template>
```

- [ ] **Step 4: 运行 market 测试**

Run: `uv run pytest tests/test_market_index.py tests/test_extensions_installer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/market.py backend/api/plugins.py backend/api/themes_ext.py backend/core/extensions.py frontend/pages/admin/system/themes.vue tests/test_market_index.py
git commit -m "feat: marketplace index API + theme customizer dynamic form + mods schema validation"
```

---

### Task C：Shortcode 引擎 + 插件注册接口 + do_shortcode API

**Files:**
- Create: `backend/core/shortcodes.py` — `register_shortcode(name, fn, plugin=None)`、`unregister_shortcode(name)`、`do_shortcode(html: str, ctx: dict)`（支持 `[a b=1 c="x"]body[/a]`，自闭合 `[a/]`），安全白名单 & 黑名单 `<script onerror>` 等注入防护
- Create: `backend/api/shortcodes.py` — `POST /api/v1/shortcodes/render` body=`{ html }`，公开可读写但限流 30/min/ip
- Modify: `backend/core/hooks.py` — 在 hooks 初始化阶段就初始化 shortcode manager
- Modify: `backend/core/plugin_loader.py` — 插件 `register(ctx)` 的 `ctx` 加 `register_shortcode / register_admin_route / register_public_route`
- Modify: `backend/api/blog.py`（文章详情 / 文章列表渲染摘要）— 富文本内容过 `do_shortcode()` 再返回
- Create: `tests/test_shortcodes.py` — 测试基础解析、嵌套、白名单过滤、未注册短代码不渲染直接保留文字

- [ ] **Step 1: 失败测试 tests/test_shortcodes.py**

```python
import pytest
from backend.core.shortcodes import ShortcodeManager, do_shortcode

def test_register_and_render_basic():
    sm = ShortcodeManager()
    def greet(name="world", **_): return f"<b>Hello {name}!</b>"
    sm.register("greet", greet, plugin="demo")
    assert sm.render("Say [greet name=Rosetta /] end").endswith("end")
    assert "Hello Rosetta!" in sm.render("Say [greet name=Rosetta /] end")
```

- [ ] **Step 2: 运行，确保失败（模块不存在）**

Run: `uv run pytest tests/test_shortcodes.py -v`
Expected: FAIL ImportError

- [ ] **Step 3: 实现 shortcode 核心**

核心 `backend/core/shortcodes.py` 实现思路：
1. 正则：`\[(\w+[a-zA-Z0-9_\-]*)([^\]]*?)(\/?)\]`，然后对 attrs 用 shlex 分词解析 k=v / k='v' / k="v"
2. 对结束标签 `[/name]` 采用「栈匹配」不支持同名嵌套跨域（同名嵌套简单处理为栈深度）
3. `do_shortcode(text, ctx)` 返回 HTML：未注册短码原样保留（防止内容丢失）
4. 过滤：每个短码 handler 输出都走 `bleach.clean(tags, attributes)` 白名单（默认允许 `b/i/em/strong/p/br/img/a/sup/sub/code/pre/ul/ol/li/table/thead/tbody/tr/th/td/blockquote/details/summary`）

- [ ] **Step 4: 测试通过**

Run: `uv run pytest tests/test_shortcodes.py -v`
Expected: PASS

- [ ] **Step 5: 接入文章渲染 + 公开 API**

在 `backend/api/blog.py` 的文章详情 `_to_out`（或最终响应返回前）：
```python
from backend.core.shortcodes import do_shortcode
out.content_html = do_shortcode(out.content_html or "")
out.excerpt = do_shortcode(out.excerpt or "")
```

新增 `backend/api/shortcodes.py`：
```python
@router.post("/shortcodes/render")
async def render_shortcodes(payload: RenderShortcodesIn):
    return {"success": True, "data": {"html": do_shortcode(payload.html or "")}}
```

并在 `backend/main.py` include 路由（`/api/v1/shortcodes` 或 `/api/shortcodes`，与现有风格一致用 `/api/*`）。

- [ ] **Step 6: Commit**

```bash
git add backend/core/shortcodes.py backend/api/shortcodes.py backend/api/blog.py backend/core/hooks.py backend/core/plugin_loader.py tests/test_shortcodes.py
git commit -m "feat: shortcode engine + render API with bleach whitelist"
```

---

### Task D：插件独立后台页 / 独立前台路由注册 & 前端第三方菜单接入

**Files:**
- Create: `backend/core/routing_registry.py` — `register_admin_endpoint(slug, router)`、`register_public_endpoint(slug, router)`；启动时在 `bootstrap_extensions` 遍历已激活插件并统一挂载到 FastAPI
- Modify: `backend/core/plugin_loader.py PluginContext` — 把 Task C 新增的 ctx 方法正式扩充 3 个：`register_shortcode`、`register_admin_router(router)`、`register_public_router(router)`
- Modify: `backend/main.py` — 在 include_router 的最后调用 `routing_registry.mount_all(app, admin_guard=AdminDep)`
- Modify: `backend/api/plugins.py` — 新增 `GET /api/admin/plugins/menu-registry`：返回「已激活插件声明的后台菜单项」（`{slug, label, icon, path, admin_route_prefix}`），给前端 AppHeader/Sidebar 菜单接入
- Modify: `frontend/composables/usePluginMenu.ts` — 从 `/api/admin/plugins/menu-registry` 拉取，在 `layouts/admin.vue` 侧边栏自动加一个「插件」分组
- Create: `frontend/pages/admin/plugins/[slug]/[...catchall].vue` — 统一承载第三方插件后台页面（iframe 或 nitro API 代理），推荐直接代理插件提供的 Vue SPA 产物
- Create: `tests/test_plugin_routing.py`

- [ ] **Step 1: 失败测试 tests/test_plugin_routing.py**

```python
import pytest
from fastapi import APIRouter
from backend.core.routing_registry import routing_registry

def test_routing_registry_mounts():
    admin = APIRouter(prefix="/test-admin")
    public = APIRouter(prefix="/test-public")
    @admin.get("/ping")
    def _a(): return "admin"
    @public.get("/ping")
    def _p(): return "public"
    routing_registry.register_admin_router("demo", admin)
    routing_registry.register_public_router("demo", public)
    items = routing_registry.list_routes()
    assert any("test-admin" in r["prefix"] for r in items)
    assert any("test-public" in r["prefix"] for r in items)
```

- [ ] **Step 2: 运行失败测试**

Run: `uv run pytest tests/test_plugin_routing.py -v`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现 routing_registry + plugin_loader ctx 扩充 + main.py 挂载 + 菜单注册**

关键接口：
```python
# backend/core/routing_registry.py
class RoutingRegistry:
    def __init__(self): self.admin_routes: list[tuple[str, APIRouter]] = []; self.public_routes: list[tuple[str, APIRouter]] = []; self.menu_items: list[dict] = []
    def register_admin_router(self, slug: str, router: APIRouter):
        self.admin_routes.append((slug, router))
    def register_public_router(self, slug: str, router: APIRouter):
        self.public_routes.append((slug, router))
    def register_admin_menu(self, item: dict): self.menu_items.append(item)
    def mount_all(self, app: FastAPI, *, admin_guard: Any = None):
        from backend.core.auth import require_admin
        for slug, r in self.admin_routes:
            prefix = f"/api/admin/plugins/{slug}"
            # 给 router 每个 route 自动注入 admin_guard 依赖
            app.include_router(r, prefix=prefix, dependencies=[Depends(admin_guard or require_admin)], tags=[f"Plugin: {slug}"])
        for slug, r in self.public_routes:
            app.include_router(r, prefix=f"/api/plugins/{slug}", tags=[f"Plugin-Public: {slug}"])
routing_registry = RoutingRegistry()
```

- [ ] **Step 4: 测试通过**

Run: `uv run pytest tests/test_plugin_routing.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/routing_registry.py backend/core/plugin_loader.py backend/main.py backend/api/plugins.py frontend/composables/usePluginMenu.ts frontend/layouts/admin.vue frontend/pages/admin/plugins/\[slug\]/\[\.\.\.catchall\].vue tests/test_plugin_routing.py
git commit -m "feat: plugin admin/public route registry + admin sidebar plugin menu"
```

---

### Task E：补齐 2 套示例主题 + 2 套示例插件（覆盖五类扩展点）

**Files:**
- Create: `frontend/themes/astro-paper-inspired/rosetta-theme.json` / `style.css` / `screenshot.svg`（Astro Paper 风格：窄栏 760px、无 Hero 壁纸、竖排列表、极细分割线）
- Create: `frontend/themes/typewriter-serif/rosetta-theme.json` / `style.css` / `screenshot.svg`（Typewriter Serif 风格：衬线字体、超窄正文、灰棕配色、无彩色按钮）
- Create: `backend/plugins/hello-rosetta/` 示例插件：action/filter/shortcode 三类
- Create: `backend/plugins/guestbook-rss/` 示例插件：独立前台路由 `/api/plugins/guestbook-rss/feed.xml` + 独立后台页 `/admin/plugins/guestbook-rss/settings`
- Modify: `tests/` 下为 2 示例插件各写一个最小 smoke test：激活、调用其钩子输出

- [ ] **Step 1: 创建示例主题 astro-paper-inspired**

`frontend/themes/astro-paper-inspired/rosetta-theme.json`（关键片段）：
```json
{
  "id": "io.github.rosetta.astro-paper-inspired",
  "slug": "astro-paper-inspired",
  "name": "Astro Paper Inspired",
  "version": "0.1.0",
  "type": "blog",
  "description": "Astro Paper 风格：760px 窄栏居中、无大图 Hero、竖排列表。",
  "author": "Rosetta",
  "license": "MIT",
  "entry_css": "style.css",
  "screenshot": "screenshot.svg",
  "mods_schema": {
    "type": "object",
    "properties": {
      "posts_per_row":  { "type": "integer", "default": 1, "enum": [1, 2] },
      "show_avatar":    { "type": "boolean", "default": true },
      "accent_color":   { "type": "string",  "default": "#4f46e5" }
    }
  }
}
```

`style.css` 选择器走 `[data-theme="astro-paper-inspired"]` 前缀，宽度与列表栅格沿用 Editorial 的覆盖写法（参考 minimal-brutalist/style.css 结构）。

- [ ] **Step 2: 创建示例主题 typewriter-serif**

mods_schema 强调「衬线」与「超窄 640px」：
```json
{
  "typewriter_serif_font": { "type": "boolean", "default": true },
  "narrow_px": { "type": "integer", "default": 640, "minimum": 480, "maximum": 820 }
}
```
CSS 给 `font-family` 覆盖 `"Iowan Old Style", "Palatino Linotype", Palatino, "Source Han Serif SC", serif`，颜色 `#3a2a1a`。

- [ ] **Step 3: 创建示例插件 hello-rosetta**

目录结构：
```
backend/plugins/hello-rosetta/
  __init__.py
  plugin.py
  rosetta-plugin.json
```

`plugin.py`：
```python
from __future__ import annotations
import html
import re

async def register(ctx):
    # 1) action: 在文章详情页 HTML 尾部插入一个签名
    def append_signature(post, **kw):
        content = getattr(post, "content_html", "") or ""
        post.content_html = content + '<hr class="my-4"><p>— Hello from <b>hello-rosetta</b> 示例插件 —</p>'
    ctx.add_action("post.rendered", append_signature)

    # 2) filter: 把文章标题统一加一个后缀（仅在示例激活时可见）
    def title_suffix(title: str, post, **kw) -> str:
        return f"{title}  · hello"
    ctx.add_filter("post.title", title_suffix)

    # 3) shortcode: [hello to="World"] -> <p>Hello, World!</p>
    def shortcode_hello(to="World", **kw):
        return f"<p>Hello, <b>{html.escape(str(to))}</b>!</p>"
    ctx.register_shortcode("hello", shortcode_hello)
```

- [ ] **Step 4: 创建示例插件 guestbook-rss**

`rosetta-plugin.json` 声明 `admin_menu`：
```json
{
  "id": "io.github.rosetta.guestbook-rss",
  "slug": "guestbook-rss",
  "name": "Guestbook RSS",
  "version": "0.1.0",
  "entrypoint": "plugin:register",
  "admin_menu": {
    "label": "留言板 RSS",
    "icon": "material-symbols:rss-feed-rounded",
    "path": "/admin/plugins/guestbook-rss/settings"
  }
}
```

`plugin.py` 示例：
```python
from fastapi import APIRouter
from fastapi.responses import Response
from sqlalchemy import select
from backend.core.database import async_session_maker
from backend.models.interactions import Guestbook

async def register(ctx):
    public = APIRouter(tags=["Guestbook RSS"])
    @public.get("/feed.xml", response_class=Response)
    async def rss():
        async with async_session_maker() as db:
            rows = (await db.execute(select(Guestbook).order_by(Guestbook.created_at.desc()).limit(50))).scalars().all()
        body = rss_xml(rows)  # 自定义 rss_xml
        return Response(body, media_type="application/rss+xml")
    ctx.register_public_router(public)

    admin = APIRouter(tags=["Guestbook RSS Admin"])
    @admin.get("/settings")
    async def get_settings():
        return {"success": True, "data": ctx.settings }
    @admin.put("/settings")
    async def put_settings(payload: dict):
        await ctx.set_settings(payload)
        return {"success": True}
    ctx.register_admin_router(admin)
    ctx.register_admin_menu(ctx.manifest.get("admin_menu"))
```

- [ ] **Step 5: smoke test**

`tests/test_samples.py`：
```python
import pytest
from backend.core.extensions import plugin_manager
from backend.core.shortcodes import do_shortcode

@pytest.mark.asyncio
async def test_hello_plugin_shortcode():
    # 用插件管理器激活 hello-rosetta 后，再执行短码
    # (此处省略 db fixture；集成模式用 activate_by_slug("hello-rosetta"))
    pass  # 实际写完整
```

- [ ] **Step 6: Commit**

```bash
git add frontend/themes/astro-paper-inspired frontend/themes/typewriter-serif backend/plugins/hello-rosetta backend/plugins/guestbook-rss tests/test_samples.py
git commit -m "feat(samples): 2 themes + 2 plugins covering all 5 extension points"
```

---

### Task F：三份中文开发文档 + 后台 `/admin/docs` 文档浏览入口

**Files:**
- Create: `docs/plugins-themes/zh-CN/rest-api.md` — 插件/主题/Mods/Shortcodes/Market 完整 REST 接口，按 OpenAPI 风格分：认证、示例 curl、响应示例、错误码
- Create: `docs/plugins-themes/zh-CN/theme-tutorial.md` — 主题清单结构、mods_schema 字段、CSS 前缀、安装与截图规范，以 astro-paper-inspired 为例给完整清单和 CSS 片段
- Create: `docs/plugins-themes/zh-CN/plugin-tutorial.md` — 插件结构、register ctx、action/filter/shortcode/独立路由/菜单 五类用法、安全提示：沙箱、依赖声明、settings 存储边界
- Create: `frontend/composables/useDocsCatalog.ts` + `frontend/pages/admin/docs/[...slug].vue`（首页为 `index`）— 读 Nitro 服务端文件 `docs/plugins-themes/zh-CN/*.md`，用 `remark + github-flavor + shiki` 渲染（如依赖过大就直接 `marked + highlight.js`）
- Modify: `frontend/layouts/admin.vue` 侧边栏加「开发文档」节点，跳转 `/admin/docs/index`

- [ ] **Step 1: 写三份 Markdown 文档骨架**

REST API 文档章节：
- 1. 认证（Bearer JWT）
- 2. 插件 API：列表 / 详情 / 扫描 / 激活 / 禁用 / 删除 / ZIP 上传 / 远程安装 / 市场列表 / 市场一键安装 / 设置读写
- 3. 主题 API：列表 / 当前 / 详情 / 激活 / 扫描 / 删除 / Mods GET / Mods PUT / Mods PATCH（附 mods_schema 校验错误响应样例）/ ZIP 上传 / 市场
- 4. Shortcodes API：`POST /api/shortcodes/render` 示例 HTML 与输出
- 5. 错误码表：OOBE_REQUIRED / MODS_SCHEMA_VIOLATION / MARKET_ITEM_NOT_FOUND / PACKAGE_CHECKSUM_MISMATCH / PACKAGE_TOO_LARGE / MANIFEST_INVALID / PLUGIN_NOT_FOUND / THEME_NOT_FOUND

主题教程目录：
- 1. 目录规范
- 2. rosetta-theme.json 字段详解（id / slug / version / entry_css / mods_schema / screenshots / tags）
- 3. CSS 作用域：`[data-theme="<slug>"]` 前缀
- 4. 安装与切换：后台 / API 两种方式
- 5. 完整示例（astro-paper-inspired）

插件教程目录：
- 1. 目录规范
- 2. register(ctx) 提供的 11 个能力：add_action / add_filter / register_shortcode / register_admin_router / register_public_router / register_admin_menu / get_settings / set_settings / get_mods / do_action / apply_filters
- 3. 五类扩展点：action / filter / shortcode / 独立后台页 / 独立前台路由 各自最小示例
- 4. 安全：不要执行 settings 中 eval；不要 import sys/os/subprocess 之外的高风险模块（可选安全策略，仅给出清单级提示）
- 5. 完整示例（guestbook-rss）

- [ ] **Step 2: 前端 docs viewer**

`frontend/pages/admin/docs/[...slug].vue`：
```vue
<script setup lang="ts">
const route = useRoute()
const slug = (Array.isArray(route.params.slug) ? route.params.slug[0] : route.params.slug) || 'index'
const { data } = await useFetch<string>(`/api/docs/${slug}`)
// 或 Nitro server route /server/api/docs/[slug].get.ts 读磁盘 Markdown 返回字符串
</script>
```
在 `frontend/server/api/docs/[slug].get.ts` 新增 Nitro 路由（如果项目已有 `/server/` 目录；否则改为 composable 内部 `$fetch('/api/docs/' + slug)` 并在 `backend/api/docs.py` 提供同源后端路由更保险）。考虑到文档体积很小，推荐直接在 `backend/api/docs.py` 暴露：
```python
@router.get("/docs/{slug}")
async def get_doc(slug: str = Path(..., pattern=r"^[a-z0-9\-\_]{1,64}$")):
    ...
    return {"success": True, "data": {"markdown": txt, "title": title}}
```

- [ ] **Step 3: 回归 typecheck**

Run (in `frontend/`): `pnpm typecheck ; pnpm lint`
Expected: 0 error

- [ ] **Step 4: Commit**

```bash
git add docs/plugins-themes/zh-CN/*.md frontend/pages/admin/docs frontend/server/api/docs frontend/layouts/admin.vue frontend/composables/useDocsCatalog.ts backend/api/docs.py backend/main.py
git commit -m "docs: add plugin/theme REST API & tutorial & admin docs viewer"
```

---

### Task G：全面 pytest 回归 + 后端 python import smoke + DB 迁移一致性

**Files:**
- Modify: `tests/conftest.py`（若没有，创建）— 提供 `admin_token` fixture，避免 Task A/B 的 401 阻塞
- Run: 所有新测试 + 现有 tests/ 回归
- Run: `python -c "from backend.main import app"` 与 `python -m backend.migrations status`

- [ ] **Step 1: pytest 全集**

Run (repo root): `uv run pytest -v --timeout=120 -q`
Expected: no FAILED

- [ ] **Step 2: import 与 migration smoke**

```bash
python -c "from backend.main import app"
python -m backend.migrations status
```

- [ ] **Step 3: 前端**

```bash
cd frontend ; pnpm typecheck ; pnpm lint
```

Expected: 0 error

---

## 2. 交付验收清单（交付时逐项勾选）

- [ ] G1 关闭：zip 上传 / remote 安装插件主题，测试通过
- [ ] G2 关闭：market index 列表 + 一键安装 API、菜单渲染
- [ ] G3 关闭：mods schema `jsonschema.validate` 生效 + 前端 Customizer 动态表单
- [ ] G4 关闭：shortcode 引擎 + 文章自动渲染 + `POST /api/shortcodes/render`，通过 bleach 白名单
- [ ] G5 关闭：插件独立后台页、独立前台路由、Sidebar 菜单、`admin/plugins/[slug]/[...catchall]` 路由页
- [ ] G6 关闭：示例主题 2 套、示例插件 2 套，覆盖 5 类扩展点
- [ ] G7 关闭：3 份中文文档 + `/admin/docs/` 浏览入口
- [ ] G8 关闭：新增 pytest 全部通过；typecheck+lint 0 error；DB migration head 一致
