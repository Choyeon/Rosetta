"""首页轮播「文字色调」（``text_color``）两端回归（批次 #28）。

这一列与 ``HeroSlide`` 同期建表，`HeroSlideCreate/Update/Response` 一路声明到底，匿名口
``GET /api/hero/slides`` 也把它投给每个访客，但：

- 后台 `pages/admin/content/hero.vue` 没有这个开关 —— 只能靠直接打接口或导 ZIP 才写进去；
- 首页 hero 文案六个元素把白字与黑色压暗层写死在模板里，写进去的值同样不渲染。

表现就是"雪景/白墙/浅灰渐变"这类亮底图上，首页标题是一行压在亮底上的白字——不可读，
而后台唯一的补救手段是把遮罩拉到最黑，代价是本来该透出来的图没了。
本文件钉住后端侧的四个不变量；前台消费侧由
`frontend/tests/unit/heroTextColorWired.spec.ts` 钉（色调类只能从 computed 来，
且缺省档必须与今天的观感逐条相等）。
"""

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


async def _read_tone(slide_id: int) -> str:
    async with async_session_maker() as db:
        row = (await db.execute(select(HeroSlide).where(HeroSlide.id == slide_id))).scalar_one()
        return row.text_color


async def _create(client: AsyncClient, headers: dict, **extra) -> int:
    body = {"media_url": "/media/hero-tone.jpg", **extra}
    resp = await client.post(ADMIN, headers=headers, json=body)
    assert resp.status_code == 201, resp.text
    return int(_unwrap(resp.json())["id"])


class TestDefaultToneIsOneStory:
    """缺省值不一致＝同一个语义有三份真相：换 worker/换入口就换皮肤。

    列默认、schema 默认、热榜虚拟轮播兜底行必须都是 `light`——那正是这个首页一直以来的
    白字观感，也是历史行在库里实际存着的值。
    """

    def test_column_default(self):
        assert HeroSlide.text_color.property.columns[0].default.arg == "light"

    def test_create_schema_default(self):
        assert HeroSlideCreate.model_fields["text_color"].default == "light"

    @pytest.mark.parametrize("model", [HeroSlideCreate, HeroSlideUpdate, HeroSlideResponse])
    def test_declared_on_every_side(self, model):
        assert "text_color" in model.model_fields, f"{model.__name__} 缺 text_color"


@pytest.mark.asyncio
async def test_create_persists_and_public_endpoint_delivers(
    client: AsyncClient, admin_headers: dict
):
    """后台读得到不算接通：这一列的消费点是**访客**看到的首页横幅。"""
    slide_id = await _create(client, admin_headers, text_color="dark")
    resp = await client.get(PUBLIC)  # 不带任何凭证
    assert resp.status_code == 200, resp.text
    row = next(item for item in _unwrap(resp.json()) if item["id"] == slide_id)
    assert row["text_color"] == "dark"
    assert await _read_tone(slide_id) == "dark"


@pytest.mark.asyncio
async def test_create_without_the_key_stays_light(client: AsyncClient, admin_headers: dict):
    """不传就是 light，不能凭空造出一个"没色调"的行让前端各写各的回落。"""
    slide_id = await _create(client, admin_headers)
    assert await _read_tone(slide_id) == "light"


@pytest.mark.asyncio
async def test_put_roundtrip_and_bogus_value(client: AsyncClient, admin_headers: dict):
    slide_id = await _create(client, admin_headers, text_color="dark")

    resp = await client.put(
        f"{ADMIN}/{slide_id}", headers=admin_headers, json={"text_color": "light"}
    )
    assert resp.status_code == 200, resp.text
    assert _unwrap(resp.json())["text_color"] == "light"

    # Literal["light", "dark"]：脏值在写口就拦成 422，而不是落库后由前端渲染出第三种观感
    resp = await client.put(
        f"{ADMIN}/{slide_id}", headers=admin_headers, json={"text_color": "white"}
    )
    assert resp.status_code == 422, resp.text
    # 回读只放在最后：端点的 COMMIT 发生在依赖 teardown（响应已返回之后），而测试会话与它共用
    # 同一条 SQLite 连接，中途 `async with async_session_maker()` 收尾会把那条尚未提交的事务
    # 一起 ROLLBACK —— 表现是"下一步说这一行不存在"。同段口径见 test_hero_secondary_cta.py。
    assert await _read_tone(slide_id) == "light"


@pytest.mark.asyncio
async def test_explicit_null_is_422_not_500(client: AsyncClient, admin_headers: dict):
    """列 NOT NULL：`{"text_color": null}` 走裸 setattr 会在 flush 撞 IntegrityError → 500。"""
    slide_id = await _create(client, admin_headers, text_color="dark")
    resp = await client.put(f"{ADMIN}/{slide_id}", headers=admin_headers, json={"text_color": None})
    assert resp.status_code == 422, resp.text
    assert await _read_tone(slide_id) == "dark"
