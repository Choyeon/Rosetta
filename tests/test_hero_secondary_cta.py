"""首页轮播「次按钮」（``cta_secondary_text`` / ``cta_secondary_url``）两端回归（批次 #27）。

这一对列很早就在 `hero_slides` 表里，`HeroSlideCreate/Update/Response` 也一路声明到底，
匿名口 `GET /api/hero/slides` 把它们投给每个访客，但：

- 后台 `pages/admin/content/hero.vue` 没有这两个输入口 —— 只能靠直接打接口或导 ZIP 才写进去；
- 首页把第二个按钮硬编码成「查看全部 → /posts」，所以写进去的值永远不渲染。

于是"配了没生效"和"能配但看不见"两头都占。本文件钉住这条真链路：
schema 三处声明 → 创建口能写 → 匿名口能读 → PUT 能改能清 → 省略键不动 → 超长拒 422。
前端消费侧（次按钮取值 + href 伪协议闸门）由 `frontend/tests/unit/heroSecondaryCta.spec.ts` 钉。
"""

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.core.database import async_session_maker
from backend.models.hero import HeroSlide
from backend.schemas.hero import HeroSlideCreate, HeroSlideResponse, HeroSlideUpdate

ADMIN = "/api/admin/hero/slides"
PUBLIC = "/api/hero/slides"


def _unwrap(body):
    """两种形态都接：全局信封 ``{success, data}`` 与裸 list/dict。"""
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


def _secondary_dict(zh: str) -> str:
    """这一列存的是多语言 JSON 字符串（与 title/cta_text 同族契约）。"""
    return json.dumps({"zh": zh, "en": zh}, ensure_ascii=False)


async def _read_pair(slide_id: int) -> tuple[str | None, str | None]:
    async with async_session_maker() as db:
        row = (await db.execute(select(HeroSlide).where(HeroSlide.id == slide_id))).scalar_one()
        return row.cta_secondary_text, row.cta_secondary_url


async def _create(client: AsyncClient, headers: dict, **extra) -> int:
    body = {"media_url": "/media/hero-test.jpg", "title": _secondary_dict("标题"), **extra}
    resp = await client.post(ADMIN, headers=headers, json=body)
    assert resp.status_code == 201, resp.text
    return int(_unwrap(resp.json())["id"])


class TestSchemaDeclaresThePair:
    """缺任何一处声明就分别是"写不进"（Create/Update）或"读不出"（Response）。"""

    @pytest.mark.parametrize("model", [HeroSlideCreate, HeroSlideUpdate, HeroSlideResponse])
    def test_both_fields_present(self, model):
        for field in ("cta_secondary_text", "cta_secondary_url"):
            assert field in model.model_fields, f"{model.__name__} 缺 {field}"

    def test_url_column_length_mirrored(self):
        """列是 String(500)：SQLite 超长静默收下、PG 在 flush 时抛 value too long → 500。"""
        for model in (HeroSlideCreate, HeroSlideUpdate):
            info = model.model_fields["cta_secondary_url"].metadata
            limits = [m for m in info if type(m).__name__ == "MaxLen"]
            assert limits and limits[0].max_length == 500, f"{model.__name__} 缺 500 上限"


@pytest.mark.asyncio
async def test_create_accepts_the_pair(client: AsyncClient, admin_headers: dict):
    text = _secondary_dict("看系列")
    slide_id = await _create(
        client, admin_headers, cta_secondary_text=text, cta_secondary_url="/series/python"
    )
    resp = await client.get(PUBLIC)
    assert resp.status_code == 200, resp.text
    row = next(item for item in _unwrap(resp.json()) if item["id"] == slide_id)
    assert row["cta_secondary_text"] == text
    assert row["cta_secondary_url"] == "/series/python"
    assert await _read_pair(slide_id) == (text, "/series/python")


@pytest.mark.asyncio
async def test_create_without_them_stays_empty(client: AsyncClient, admin_headers: dict):
    """不传就是 NULL —— 首页据此回落到缺省按钮，不能凭空造出一个空按钮。"""
    slide_id = await _create(client, admin_headers)
    resp = await client.get(PUBLIC)
    row = next(item for item in _unwrap(resp.json()) if item["id"] == slide_id)
    assert row["cta_secondary_text"] is None
    assert row["cta_secondary_url"] is None


@pytest.mark.asyncio
async def test_anonymous_public_endpoint_delivers_them(client: AsyncClient, admin_headers: dict):
    """后台读得到不算接通：这一对的消费点是**访客**看到的首页横幅。"""
    text = _secondary_dict("订阅")
    slide_id = await _create(
        client,
        admin_headers,
        cta_secondary_text=text,
        cta_secondary_url="https://choyeon.cc/rss.xml",
    )
    resp = await client.get(PUBLIC)  # 不带任何凭证
    assert resp.status_code == 200, resp.text
    row = next(item for item in _unwrap(resp.json()) if item["id"] == slide_id)
    assert row["cta_secondary_text"] == text
    assert row["cta_secondary_url"] == "https://choyeon.cc/rss.xml"


@pytest.mark.asyncio
async def test_put_changes_and_clears(client: AsyncClient, admin_headers: dict):
    slide_id = await _create(
        client, admin_headers, cta_secondary_text=_secondary_dict("旧"), cta_secondary_url="/old"
    )

    resp = await client.put(
        f"{ADMIN}/{slide_id}", headers=admin_headers, json={"cta_secondary_url": "/new"}
    )
    assert resp.status_code == 200, resp.text
    body = _unwrap(resp.json())
    assert body["cta_secondary_url"] == "/new"
    assert body["cta_secondary_text"] == _secondary_dict("旧")  # 未提交的键不受影响

    # 显式 null 才清得掉：这一列可空，且首页把 NULL 判成"用缺省按钮"
    resp = await client.put(
        f"{ADMIN}/{slide_id}",
        headers=admin_headers,
        json={"cta_secondary_text": None, "cta_secondary_url": None},
    )
    assert resp.status_code == 200, resp.text
    # 回读只放在最后：端点的 COMMIT 发生在依赖 teardown（响应已返回之后），而测试会话与它共用
    # 同一条 SQLite 连接。中途 `async with async_session_maker()` 收尾会把那条尚未提交的
    # 事务一起 ROLLBACK —— 表现是"下一步请求 404 说这一行不存在"，而不是产品写坏了。
    assert await _read_pair(slide_id) == (None, None)


@pytest.mark.asyncio
async def test_put_omitting_keys_leaves_them_untouched(client: AsyncClient, admin_headers: dict):
    """exclude_unset 语义：只改标题不得把两个按钮抹掉（否则后台一次改名就丢配置）。"""
    text = _secondary_dict("保持")
    slide_id = await _create(
        client, admin_headers, cta_secondary_text=text, cta_secondary_url="/keep"
    )
    resp = await client.put(f"{ADMIN}/{slide_id}", headers=admin_headers, json={"sort_order": 9})
    assert resp.status_code == 200, resp.text
    assert _unwrap(resp.json())["sort_order"] == 9
    assert await _read_pair(slide_id) == (text, "/keep")


@pytest.mark.asyncio
async def test_overlong_url_is_422_not_500(client: AsyncClient, admin_headers: dict):
    slide_id = await _create(client, admin_headers, cta_secondary_url="/keep")
    resp = await client.put(
        f"{ADMIN}/{slide_id}",
        headers=admin_headers,
        json={"cta_secondary_url": "https://x.test/" + "y" * 600},
    )
    assert resp.status_code == 422, resp.text
    assert await _read_pair(slide_id) == (None, "/keep")
