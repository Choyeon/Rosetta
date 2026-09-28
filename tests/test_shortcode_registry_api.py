"""短代码注册/渲染 API 的边界回归（HTTP 层）。

引擎单测（``tests/test_shortcodes.py``）从不经过这 5 条路由，于是钉不住六类
只有走接口才暴露的缺陷：

1. 模板 handler 的签名与引擎调用约定不符 —— 注册 200、列表可见，渲染永远是
   ``<!-- shortcode-error … -->`` 注释（还把异常文本吐到读者可见的正文里）。
2. 注册/注销不失效已渲染内容缓存 —— TTL 内访客仍看旧展开结果。
3. 注册表只是进程内存 —— ``--workers 4`` 下"刷新两次就找不到"，重启即全丢。
4. 公开渲染接口接受调用方 ``context`` —— 未鉴权就能影响插件 handler 的取数判断。
5. 运行时接口可以覆盖/注销插件自带的短代码 —— 注销后除了重启没有恢复路径。
6. 成对短代码递归渲染没有深度闸门 —— 构造正文可打成 RecursionError（500）。
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.api.shortcodes import RENDER_MAX_CHARS
from backend.core.cache import cache
from backend.core.extensions import (
    delete_shortcode_template,
    get_shortcode_templates,
    put_shortcode_template,
)
from backend.core.shortcodes import (
    _MAX_NESTING_DEPTH,
    _reset_shortcodes_for_tests,
    do_shortcode,
    list_shortcodes,
    register_shortcode,
)

RENDER_PATH = "/api/shortcodes/render"
LIST_PATH = "/api/admin/shortcodes"  # GET = 列表，POST = 管理员预览
REGISTER_PATH = "/api/admin/shortcodes/register"


@pytest.fixture(autouse=True)
def isolate_registry():
    """注册表是模块单例上的 dict，用例之间必须隔离。"""
    _reset_shortcodes_for_tests()
    yield
    _reset_shortcodes_for_tests()


def _tags(items: list[dict]) -> set[str]:
    return {i["tag"] for i in items}


class TestTemplateHandlerEngineConvention:
    """缺陷 1：模板 handler 必须能被引擎调起来。"""

    @pytest.mark.asyncio
    async def test_paired_template_renders_instead_of_error_comment(
        self, client: AsyncClient, staff_headers: dict
    ):
        resp = await client.post(
            REGISTER_PATH,
            headers=staff_headers,
            json={
                "tag": "promo",
                "replacement": '<div class="promo">{content}</div>',
                "description": "促销块",
            },
        )
        assert resp.status_code == 200

        rendered = await client.post(RENDER_PATH, json={"content": "前 [promo]限时[/promo] 后"})
        assert rendered.status_code == 200
        html = rendered.json()["data"]["rendered"]
        assert "shortcode-error" not in html
        assert html == '前 <div class="promo">限时</div> 后'

    @pytest.mark.asyncio
    async def test_attribute_interpolation_on_self_closing_tag(
        self, client: AsyncClient, staff_headers: dict
    ):
        await client.post(
            REGISTER_PATH,
            headers=staff_headers,
            json={"tag": "cta", "replacement": '<a href="{url}">{content}</a>'},
        )
        resp = await client.post(RENDER_PATH, json={"content": '[cta url="/docs" /]'})
        assert resp.json()["data"]["rendered"] == '<a href="/docs"></a>'

    @pytest.mark.asyncio
    async def test_engine_reserved_kwargs_are_not_interpolated(
        self, client: AsyncClient, staff_headers: dict
    ):
        """``{content}`` 之外的引擎注入项（ctx / _content）不得被当成属性写进正文。"""
        await client.post(
            REGISTER_PATH,
            headers=staff_headers,
            json={"tag": "leaky", "replacement": "X{ctx}Y{_content}Z"},
        )
        resp = await client.post(RENDER_PATH, json={"content": "[leaky /]"})
        html = resp.json()["data"]["rendered"]
        assert html == "X{ctx}Y{_content}Z"
        assert "shortcode-error" not in html


class TestRenderedCacheInvalidation:
    """缺陷 2：注册表变化必须抹掉嵌有渲染结果的缓存。"""

    async def _seed(self):
        await cache.set("post:hello:zh", {"id": 1}, 60)
        await cache.set("posts:list:zh:1:10", {"items": []}, 60)
        await cache.set("archive:2026", {"items": []}, 60)
        await cache.set("categories:raw-i18n", {"items": []}, 60)

    @pytest.mark.asyncio
    async def test_register_clears_rendered_content_caches(
        self, client: AsyncClient, staff_headers: dict
    ):
        await self._seed()
        resp = await client.post(
            REGISTER_PATH, headers=staff_headers, json={"tag": "t1", "replacement": "A"}
        )
        assert resp.status_code == 200
        assert await cache.get("post:hello:zh") is None
        assert await cache.get("posts:list:zh:1:10") is None
        assert await cache.get("archive:2026") is None
        # 与短代码无关的键不得被顺手抹掉
        assert await cache.get("categories:raw-i18n") is not None

    @pytest.mark.asyncio
    async def test_delete_clears_and_missing_tag_does_not(
        self, client: AsyncClient, staff_headers: dict
    ):
        await client.post(
            REGISTER_PATH, headers=staff_headers, json={"tag": "t2", "replacement": "B"}
        )

        await self._seed()
        resp = await client.delete("/api/admin/shortcodes/t2", headers=staff_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["was_registered"] is True
        assert await cache.get("post:hello:zh") is None

        await self._seed()
        miss = await client.delete("/api/admin/shortcodes/never_existed", headers=staff_headers)
        assert miss.status_code == 200
        assert miss.json()["data"]["was_registered"] is False
        assert await cache.get("post:hello:zh") is not None, "空删除不该触发全站缓存失效"


class TestPersistenceAcrossWorkers:
    """缺陷 3：注册表落 SiteConfig KV，新进程/新 worker 从 DB 重放。"""

    @pytest.mark.asyncio
    async def test_register_writes_siteconfig(
        self, client: AsyncClient, staff_headers: dict, db_session
    ):
        await client.post(
            REGISTER_PATH,
            headers=staff_headers,
            json={"tag": "kept", "replacement": "K", "description": "d"},
        )
        templates = await get_shortcode_templates(db_session)
        assert templates["kept"]["replacement"] == "K"

    @pytest.mark.asyncio
    async def test_fresh_worker_replays_on_list(self, client: AsyncClient, staff_headers: dict):
        await client.post(
            REGISTER_PATH, headers=staff_headers, json={"tag": "kept", "replacement": "K"}
        )
        # 模拟另一个 worker / 重启后的冷进程：内存注册表空了
        _reset_shortcodes_for_tests()
        assert "kept" not in {i.tag for i in list_shortcodes()}

        resp = await client.get(LIST_PATH, headers=staff_headers)
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert "kept" in _tags(body["items"])
        assert body["persisted"] == 1
        item = next(i for i in body["items"] if i["tag"] == "kept")
        assert item["template"] is True
        assert item["plugin"] is None

        # 重放后渲染照常
        rendered = await client.post(RENDER_PATH, json={"content": "[kept /]"})
        assert rendered.json()["data"]["rendered"] == "K"

    @pytest.mark.asyncio
    async def test_list_picks_up_template_written_by_another_worker(
        self, client: AsyncClient, staff_headers: dict, db_session
    ):
        await put_shortcode_template(db_session, "orphan", replacement="O", description=None)
        await db_session.commit()
        resp = await client.get(LIST_PATH, headers=staff_headers)
        assert "orphan" in _tags(resp.json()["data"]["items"])

    @pytest.mark.asyncio
    async def test_delete_removes_from_siteconfig(
        self, client: AsyncClient, staff_headers: dict, db_session
    ):
        await client.post(
            REGISTER_PATH, headers=staff_headers, json={"tag": "gone", "replacement": "G"}
        )
        resp = await client.delete("/api/admin/shortcodes/gone", headers=staff_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["was_persisted"] is True
        assert "gone" not in await get_shortcode_templates(db_session)
        _reset_shortcodes_for_tests()
        listing = await client.get(LIST_PATH, headers=staff_headers)
        assert "gone" not in _tags(listing.json()["data"]["items"])


class TestRenderContextBoundary:
    """缺陷 4：公开渲染接口不接受调用方提供的渲染上下文。"""

    @pytest.fixture(autouse=True)
    def _ctx_reader(self):
        register_shortcode(
            "whoami",
            lambda **kw: f"[{(kw.get('ctx') or {}).get('secret', 'none')}]",
            plugin="probe-plugin",
        )

    @pytest.mark.asyncio
    async def test_public_render_ignores_supplied_context(self, client: AsyncClient):
        resp = await client.post(
            RENDER_PATH,
            json={"content": "[whoami /]", "context": {"secret": "visitor-controlled"}},
        )
        assert resp.status_code == 200
        assert "visitor-controlled" not in resp.json()["data"]["rendered"]

    @pytest.mark.asyncio
    async def test_admin_preview_is_the_only_context_capable_entry(
        self, client: AsyncClient, staff_headers: dict
    ):
        resp = await client.post(
            LIST_PATH,
            headers=staff_headers,
            json={"content": "[whoami /]", "context": {"secret": "staff-only"}},
        )
        assert resp.status_code == 200
        assert "staff-only" in resp.json()["data"]["rendered"]

    @pytest.mark.asyncio
    async def test_admin_routes_require_staff(self, client: AsyncClient, auth_headers: dict):
        assert (await client.get(LIST_PATH, headers=auth_headers)).status_code == 403
        assert (
            await client.post(
                REGISTER_PATH, headers=auth_headers, json={"tag": "x", "replacement": "y"}
            )
        ).status_code == 403
        assert (
            await client.delete("/api/admin/shortcodes/x", headers=auth_headers)
        ).status_code == 403

    @pytest.mark.asyncio
    async def test_public_render_bounds_content_size(self, client: AsyncClient):
        resp = await client.post(RENDER_PATH, json={"content": "a" * (RENDER_MAX_CHARS + 1)})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_public_render_is_not_an_html_sanitizer(self, client: AsyncClient):
        """文档口径：只展开已注册短代码，未匹配文本原样返回——它不是净化器。"""
        resp = await client.post(RENDER_PATH, json={"content": "<script>alert(1)</script>[nope]"})
        assert resp.status_code == 200
        html = resp.json()["data"]["rendered"]
        assert "<script>alert(1)</script>" in html
        assert "[nope]" in html


class TestPluginOwnedShortcodes:
    """缺陷 5：插件自带的短代码归插件生命周期管。"""

    @pytest.fixture(autouse=True)
    def _plugin_shortcode(self):
        register_shortcode("owned", lambda **kw: "PLUGIN", plugin="probe-plugin")

    @pytest.mark.asyncio
    async def test_register_cannot_shadow_plugin_shortcode(
        self, client: AsyncClient, staff_headers: dict
    ):
        resp = await client.post(
            REGISTER_PATH, headers=staff_headers, json={"tag": "owned", "replacement": "SHADOW"}
        )
        assert resp.status_code == 409
        assert resp.json()["error_code"] == "SHORTCODE_PLUGIN_OWNED"
        assert do_shortcode("[owned /]") == "PLUGIN"

    @pytest.mark.asyncio
    async def test_delete_cannot_unregister_plugin_shortcode(
        self, client: AsyncClient, staff_headers: dict
    ):
        resp = await client.delete("/api/admin/shortcodes/owned", headers=staff_headers)
        assert resp.status_code == 409
        assert resp.json()["error_code"] == "SHORTCODE_PLUGIN_OWNED"
        assert do_shortcode("[owned /]") == "PLUGIN"

    @pytest.mark.asyncio
    async def test_list_exposes_ownership(self, client: AsyncClient, staff_headers: dict):
        items = (await client.get(LIST_PATH, headers=staff_headers)).json()["data"]["items"]
        owned = next(i for i in items if i["tag"] == "owned")
        assert owned["plugin"] == "probe-plugin"
        assert owned["template"] is False

    @pytest.mark.asyncio
    async def test_replay_does_not_override_plugin_shortcode(
        self, client: AsyncClient, staff_headers: dict, db_session
    ):
        """DB 里遗留的同名模板（先注册模板、后装插件）不得在重放时压过插件实现。"""
        await put_shortcode_template(db_session, "owned", replacement="SHADOW", description=None)
        await db_session.commit()
        resp = await client.get(LIST_PATH, headers=staff_headers)
        assert resp.status_code == 200
        assert do_shortcode("[owned /]") == "PLUGIN"
        # 清理：KV 里的冲突条目不影响本用例结论
        await delete_shortcode_template(db_session, "owned")
        await db_session.commit()


class TestNestingDepthGate:
    """缺陷 6：递归渲染有闸门，构造正文不能打成 500。"""

    def test_deep_nesting_stops_at_gate(self):
        register_shortcode(
            "nest",
            lambda **kw: f"<{kw['content']}>",
            plugin="probe-plugin",
        )
        depth = _MAX_NESTING_DEPTH * 3
        text = "[nest]" * depth + "[/nest]" * depth
        out = do_shortcode(text)
        assert out.count("<") == _MAX_NESTING_DEPTH
        assert "[nest]" in out  # 超限的内层原样保留，内容不丢

    @pytest.mark.asyncio
    async def test_deep_nesting_over_http_does_not_500(self, client: AsyncClient):
        register_shortcode("nest", lambda **kw: f"<{kw['content']}>", plugin="probe-plugin")
        depth = _MAX_NESTING_DEPTH * 3
        resp = await client.post(
            RENDER_PATH, json={"content": "[nest]" * depth + "[/nest]" * depth}
        )
        assert resp.status_code == 200
