"""首页轮播「生效时间窗」（``start_time`` / ``end_time``）两端回归（批次 #40）。

这一对列和后端过滤早就在线上：`GET /api/hero/slides` 按
`is_active AND (start IS NULL OR start <= now) AND (end IS NULL OR end >= now)` 下发，
`HeroSlideCreate/Update/Response` 也一路声明。缺的是两端各一半：

- 后台 `pages/admin/content/hero.vue` 没有输入口，运营者只能靠直连接口或导 ZIP 排期；
- **写口不判倒挂**：`end <= start` 的行能 201 存进去、后台列表显示"启用中"，
  而公开口永远不下发这一张——静默失效，且没有任何一处会报错。

本文件钉住：schema 声明 → 倒挂拒 422（含相等这条边界）→ 窗口内下发 / 未到点与已结束不下发 →
PUT 只提交一侧时必须**合并库里的现值**再判（`exclude_unset` 的部分更新是这条守卫唯一会漏的口子）→
显式 null 清得掉、省略键不动。

前端侧（输入口 + 提交键 + 列表状态列 + 首页只渲染 image 档）由
`frontend/tests/unit/heroSchedule.spec.ts` 钉。
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.api.hero import _validate_window
from backend.core.database import async_session_maker
from backend.core.exceptions import ValidationException
from backend.models.hero import HeroSlide
from backend.schemas.hero import HeroSlideCreate, HeroSlideResponse, HeroSlideUpdate

ADMIN = "/api/admin/hero/slides"
PUBLIC = "/api/hero/slides"


def _unwrap(body):
    """两种形态都接：全局信封 ``{success, data}`` 与裸 list/dict。"""
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


def _iso(offset_hours: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=offset_hours)).isoformat()


async def _public_ids(client: AsyncClient) -> set[int]:
    resp = await client.get(PUBLIC)  # 不带任何凭证：消费点是访客看到的首页横幅
    assert resp.status_code == 200, resp.text
    return {item["id"] for item in _unwrap(resp.json())}


async def _create(client: AsyncClient, headers: dict, **extra) -> int:
    body = {"media_url": "/media/hero-window.jpg", **extra}
    resp = await client.post(ADMIN, headers=headers, json=body)
    assert resp.status_code == 201, resp.text
    return int(_unwrap(resp.json())["id"])


async def _read_window(slide_id: int) -> tuple[object, object]:
    async with async_session_maker() as db:
        row = (
            await db.execute(
                select(HeroSlide.start_time, HeroSlide.end_time).where(HeroSlide.id == slide_id)
            )
        ).one()
    return row[0], row[1]


class TestSchemaDeclaresTheWindow:
    """缺任何一处声明就分别是"写不进"（Create/Update）或"读不出"（Response）。"""

    @pytest.mark.parametrize("model", [HeroSlideCreate, HeroSlideUpdate, HeroSlideResponse])
    def test_both_fields_present(self, model):
        for field in ("start_time", "end_time"):
            assert field in model.model_fields, f"{model.__name__} 缺 {field}"


class TestInvertedWindowRejected:
    @pytest.mark.asyncio
    async def test_create_with_end_before_start_is_422(
        self, client: AsyncClient, admin_headers: dict
    ):
        resp = await client.post(
            ADMIN,
            headers=admin_headers,
            json={"media_url": "/media/x.jpg", "start_time": _iso(2), "end_time": _iso(1)},
        )
        assert resp.status_code == 422, resp.text
        assert "VALIDATION" in resp.text

    @pytest.mark.asyncio
    async def test_create_with_equal_bounds_is_422(self, client: AsyncClient, admin_headers: dict):
        """端点值本身属于"生效中"（后端两侧都是 `<= now` / `>= now`），
        所以 start == end 的窗口里没有任何时刻满足条件——同一条判据必须拒掉。"""
        same = _iso(3)
        resp = await client.post(
            ADMIN,
            headers=admin_headers,
            json={"media_url": "/media/x.jpg", "start_time": same, "end_time": same},
        )
        assert resp.status_code == 422, resp.text

    def test_validator_handles_naive_stored_values(self):
        """SQLite 把 `DateTime(timezone=True)` 读回成朴素值，PG 读回带 tz。

        合并校验拿朴素值和 aware 入参直接比会抛 TypeError → 500（而不是 422）。
        """
        naive_start = datetime(2026, 1, 2, 3, 4)
        aware_end = datetime(2026, 1, 2, 3, 3, tzinfo=timezone.utc)
        with pytest.raises(ValidationException):
            _validate_window(naive_start, aware_end)
        assert _validate_window(None, aware_end) is None
        assert _validate_window(naive_start, None) is None


class TestWindowDrivesDelivery:
    @pytest.mark.asyncio
    async def test_in_window_slide_is_delivered(self, client: AsyncClient, admin_headers: dict):
        slide_id = await _create(
            client, admin_headers, start_time=_iso(-2), end_time=_iso(2), is_active=True
        )
        assert slide_id in await _public_ids(client)

    @pytest.mark.asyncio
    async def test_not_yet_started_slide_is_held_back(
        self, client: AsyncClient, admin_headers: dict
    ):
        """存进去、后台看得见，但此刻还不该出现在访客首页。"""
        slide_id = await _create(
            client, admin_headers, start_time=_iso(2), end_time=_iso(6), is_active=True
        )
        assert slide_id not in await _public_ids(client)
        listed = _unwrap((await client.get(ADMIN, headers=admin_headers)).json())
        assert slide_id in {row["id"] for row in listed}

    @pytest.mark.asyncio
    async def test_expired_slide_is_held_back(self, client: AsyncClient, admin_headers: dict):
        slide_id = await _create(
            client, admin_headers, start_time=_iso(-72), end_time=_iso(-24), is_active=True
        )
        assert slide_id not in await _public_ids(client)

    @pytest.mark.asyncio
    async def test_windowless_slide_is_long_lived(self, client: AsyncClient, admin_headers: dict):
        """两端留空＝长期生效（缺省值口径，不能被判成"永远不生效"）。"""
        slide_id = await _create(client, admin_headers, is_active=True)
        assert slide_id in await _public_ids(client)

    @pytest.mark.asyncio
    async def test_inactive_in_window_slide_is_not_delivered(
        self, client: AsyncClient, admin_headers: dict
    ):
        slide_id = await _create(
            client, admin_headers, start_time=_iso(-2), end_time=_iso(2), is_active=False
        )
        assert slide_id not in await _public_ids(client)


class TestPartialUpdateMergesStoredWindow:
    @pytest.mark.asyncio
    async def test_put_only_end_must_see_stored_start(
        self, client: AsyncClient, admin_headers: dict
    ):
        """`exclude_unset` 的部分更新是这条守卫唯一会漏的口子。

        只提交 end_time 时 schema 层看不到库里的 start_time，不合并现值就等于把倒挂窗口
        放行落库——表现是"运营者只改了结束时间，这张幻灯片从此再也不出现"。
        """
        slide_id = await _create(client, admin_headers, start_time=_iso(1), end_time=_iso(5))
        resp = await client.put(
            f"{ADMIN}/{slide_id}", headers=admin_headers, json={"end_time": _iso(0.5)}
        )
        assert resp.status_code == 422, resp.text
        # 被拒的那次不得留下半个窗口：回读只放在最后（见批次 #27 的会话说明）。
        stored_start, stored_end = await _read_window(slide_id)
        assert stored_end is not None
        assert stored_end > stored_start

    @pytest.mark.asyncio
    async def test_put_only_start_must_see_stored_end(
        self, client: AsyncClient, admin_headers: dict
    ):
        slide_id = await _create(client, admin_headers, start_time=_iso(-5), end_time=_iso(-1))
        resp = await client.put(
            f"{ADMIN}/{slide_id}", headers=admin_headers, json={"start_time": _iso(0)}
        )
        assert resp.status_code == 422, resp.text

    @pytest.mark.asyncio
    async def test_put_valid_window_wins(self, client: AsyncClient, admin_headers: dict):
        slide_id = await _create(client, admin_headers, start_time=_iso(-1), end_time=_iso(1))
        resp = await client.put(
            f"{ADMIN}/{slide_id}", headers=admin_headers, json={"end_time": _iso(24)}
        )
        assert resp.status_code == 200, resp.text
        assert slide_id in await _public_ids(client)

    @pytest.mark.asyncio
    async def test_put_explicit_null_clears_the_window(
        self, client: AsyncClient, admin_headers: dict
    ):
        """留空＝长期生效：显式 null 必须清得掉，否则"取消排期"这个操作在界面上做不到。"""
        slide_id = await _create(client, admin_headers, start_time=_iso(24), end_time=_iso(48))
        assert slide_id not in await _public_ids(client)
        resp = await client.put(
            f"{ADMIN}/{slide_id}",
            headers=admin_headers,
            json={"start_time": None, "end_time": None},
        )
        assert resp.status_code == 200, resp.text
        assert slide_id in await _public_ids(client)
        # 直连回读放在最后：测试会话与端点共用同一条 SQLite 连接，中途关掉一个
        # `async_session_maker()` 会把端点尚未提交的收尾一起 ROLLBACK（批次 #27 同口径）。
        assert await _read_window(slide_id) == (None, None)

    @pytest.mark.asyncio
    async def test_put_omitting_keys_leaves_the_window(
        self, client: AsyncClient, admin_headers: dict
    ):
        """exclude_unset 语义：只改标题不得抹掉排期（一次改名等于把长期生效悄悄打开）。"""
        slide_id = await _create(client, admin_headers, start_time=_iso(24), end_time=_iso(48))
        resp = await client.put(
            f"{ADMIN}/{slide_id}", headers=admin_headers, json={"sort_order": 7}
        )
        assert resp.status_code == 200, resp.text
        assert _unwrap(resp.json())["sort_order"] == 7
        assert await _read_window(slide_id) != (None, None)


class TestGuardSitsOnBothWritePaths:
    """将来重写 handler 时，漏掉任一调用点都会让"存得进去却永不下发"回来。"""

    def test_both_handlers_call_the_validator(self):
        from pathlib import Path

        text = Path("backend/api/hero.py").read_text(encoding="utf-8")
        assert text.count("_validate_window(") >= 3  # 定义 + create + update
        assert 'update_data.get("start_time", slide.start_time)' in text
        assert 'update_data.get("end_time", slide.end_time)' in text
