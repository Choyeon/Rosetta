"""友链公开申请 `POST /api/friend-links/apply` 的四段契约（批次 #113）。

背景：`/friends` 页只有读口，站点想收友链申请只能靠留言板口头转达；被退役的
`friends_apply_html` 扁平键（批次 #112）更是"存得进、没人读"的假开关。这一族落地后
口径是「匿名写口 → pending 队列 → 管理员在 /admin/friend-links 裁决」，五条红线：

1. **默认关闭**：这是匿名可写入口，`features.enable_friend_apply` 没勾过就不该突然开始收申请。
2. **提交者写不出档位**：status / is_active / order / target_blank 不在请求模型里，
   带上就直接 422（`extra="forbid"`）——能从请求体带进来等于让提交者自己批准自己。
3. **pending 绝不进公开面**：公示判据是 `FriendLink.publicly_visible()` 这一条 SQL 谓词，
   所以申请落库后既不用清响应缓存也不用清 Nitro 页面缓存（没有对外可见的变化）。
4. **地址与文案走严格档**：值最终进访客页面的 `<a href>` / `<img src>`，
   伪协议与标记字符必须在写入口起掉（AGENTS §12.8）。
5. **验证码闸门同评论/留言同轨**：只挡匿名，失败用 400 而不是 401。
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from backend.core.cache import invalidate_cache
from backend.models.core import FriendLink
from backend.services.captcha_service import store_captcha_answer

_FIRST = "https://first.example.com"
_SECOND = "https://second.example.com"


@pytest.fixture
async def apply_on(client: AsyncClient, staff_headers):
    """打开友链申请开关，用例结束按默认值（False）复原。

    残留 True 会让后续任何匿名用例突然能往 friend_links 写行；残留 False 又会让
    本文件之外的用例撞 403——两边都得干净。
    """
    await client.patch(
        "/api/settings/features", json={"enable_friend_apply": True}, headers=staff_headers
    )
    try:
        yield
    finally:
        await client.patch(
            "/api/settings/features", json={"enable_friend_apply": False}, headers=staff_headers
        )


@pytest.fixture
async def clean_rows(db_session):
    """用后即弃：本文件造的行一律按 URL 清掉，不留给别的用例当"已有友链"。"""
    yield
    await db_session.execute(delete(FriendLink).where(FriendLink.url.in_((_FIRST, _SECOND))))
    await db_session.commit()
    await invalidate_cache("friend_links")


async def _apply(client: AsyncClient, url: str = _FIRST, **extra):
    # 限流在测试里被 conftest 整条桩成恒放行，所以不需要为每条用例换 IP；
    # 验证码、去重、开关这三道闸门才是本文件要钉的对象。
    return await client.post(
        "/api/friend-links/apply",
        json={"name": "示例小站", "url": url, "description": "一个示例站点", **extra},
    )


async def _row(db_session, url: str) -> FriendLink | None:
    return (
        await db_session.execute(select(FriendLink).where(FriendLink.url == url))
    ).scalar_one_or_none()


# ==================== ① 开关：默认关闭，关闭即 403 ====================


@pytest.mark.asyncio
async def test_apply_is_disabled_by_default(client: AsyncClient, staff_headers, clean_rows):
    """未配置过该分组 = 既有行为（不收申请）。"""
    group = (await client.get("/api/settings/features", headers=staff_headers)).json()["data"]
    assert group["enable_friend_apply"] is False, "默认值被改成 True＝给所有存量站点开一个匿名写口"

    resp = await _apply(client)
    assert resp.status_code == 403, resp.text
    assert resp.json()["error_code"] == "FRIEND_APPLY_DISABLED"


@pytest.mark.asyncio
async def test_disabled_gate_writes_no_row(client: AsyncClient, db_session, clean_rows):
    resp = await _apply(client)
    assert resp.status_code == 403, resp.text
    assert await _row(db_session, _FIRST) is None, "403 之前就把行写进去了"


@pytest.mark.asyncio
async def test_switch_is_publicly_readable_for_the_form(client: AsyncClient):
    """前台 /friends 页要在未登录时读到这个开关，否则表单要么恒显示要么恒隐藏。"""
    pub = await client.get("/api/settings/public")
    assert pub.status_code == 200, pub.text
    assert "enable_friend_apply" in pub.json()["groups"]["features"]


# ==================== ② 正常提交：落 pending，不进公开面 ====================


@pytest.mark.asyncio
async def test_valid_apply_lands_in_pending_queue(
    client: AsyncClient, apply_on, db_session, clean_rows
):
    resp = await _apply(client)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == FriendLink.STATUS_PENDING
    assert body["duplicate"] is False
    assert body["message"]

    row = await _row(db_session, _FIRST)
    assert row is not None
    assert row.status == FriendLink.STATUS_PENDING
    # is_active 是 status 的兼容镜像列：写出口归一函数要求 pending 必须镜像成 False，
    # 否则历史那版"审核页显示待审核、前台却公示出去"的缺陷会随这个新写口长回来。
    assert row.is_active is False
    assert row.order == 0 and row.target_blank is False


@pytest.mark.asyncio
async def test_pending_apply_is_not_publicly_visible(
    client: AsyncClient, apply_on, db_session, clean_rows, staff_headers
):
    """公示读口按 SQL 谓词收档：申请刚落地，访客侧一条都不能看见。"""
    await invalidate_cache("friend_links")
    before = (await client.get("/api/friend-links")).json()
    assert _FIRST not in {item["url"] for item in before}

    assert (await _apply(client)).status_code == 201

    await invalidate_cache("friend_links")
    after = (await client.get("/api/friend-links")).json()
    assert _FIRST not in {item["url"] for item in after}, "pending 行漏进公开口＝未审核内容对外公示"

    # 管理员的审核队列必须能看见它，否则"pending 队列"只是个没人读的信箱
    admin_rows = (await client.get("/api/admin/friend-links", headers=staff_headers)).json()
    assert _FIRST in {item["url"] for item in admin_rows}


@pytest.mark.asyncio
async def test_approved_row_becomes_public_without_further_writes(
    client: AsyncClient, apply_on, db_session, clean_rows, staff_headers
):
    """审核这一步只走既有的管理口：申请口不需要为公示再写任何东西。"""
    created = await _apply(client)
    link_id = created.json()["id"]
    updated = await client.put(
        f"/api/friend-links/{link_id}",
        json={"status": "approved"},
        headers=staff_headers,
    )
    assert updated.status_code == 200, updated.text
    await invalidate_cache("friend_links")
    public = (await client.get("/api/friend-links")).json()
    assert _FIRST in {item["url"] for item in public}


# ==================== ③ 请求模型的边界：档位带不进来、伪协议进不来 ====================


@pytest.mark.asyncio
async def test_applicant_cannot_supply_status_or_order(
    client: AsyncClient, apply_on, db_session, clean_rows
):
    """`extra="forbid"` 的价值：静默丢掉自批字段后，没人看得出有人试过自己批准自己。"""
    for hostile in (
        {"status": "approved"},
        {"is_active": True},
        {"order": -100},
        {"target_blank": True},
    ):
        resp = await _apply(client, **hostile)
        assert resp.status_code == 422, f"{hostile} -> {resp.status_code} {resp.text}"
        assert await _row(db_session, _FIRST) is None, f"{hostile} 居然写进去了"


@pytest.mark.asyncio
async def test_url_must_be_absolute_http_or_https(client: AsyncClient, apply_on, clean_rows):
    """值会进访客页面的 <a href>：宽容档（自动补 scheme）与非 http(s) 协议一律 422。"""
    for bad in (
        "example.com",
        "javascript:alert(1)",
        "data:text/html,hack",
        "ftp://a/b",
        "//x.com",
    ):
        resp = await _apply(client, url=bad)
        assert resp.status_code == 422, f"{bad} -> {resp.status_code}"


@pytest.mark.asyncio
async def test_logo_must_be_absolute_too(client: AsyncClient, apply_on, clean_rows):
    """logo 进 <img src>，与 url 同一档判据。"""
    resp = await _apply(client, logo="javascript:alert(1)")
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_markup_in_name_and_description_is_rejected(
    client: AsyncClient, apply_on, clean_rows
):
    """AGENTS §12.8：会渲染到访客页面上的短字符串字段，写入侧就得起标记字符。"""
    resp = await client.post(
        "/api/friend-links/apply",
        json={"name": "<script>alert(1)</script>", "url": _FIRST},
    )
    assert resp.status_code == 422, resp.text

    resp2 = await _apply(client, url=_FIRST, description="<img src=x onerror=alert(1)>")
    assert resp2.status_code == 422, resp2.text


@pytest.mark.asyncio
async def test_name_length_bounds(client: AsyncClient, apply_on, clean_rows):
    too_short = await client.post(
        "/api/friend-links/apply",
        json={"name": "A", "url": _FIRST},
    )
    assert too_short.status_code == 422, too_short.text


# ==================== ④ 去重：同地址不刷行，驳回后可再报 ====================


@pytest.mark.asyncio
async def test_duplicate_pending_apply_returns_200_without_new_row(
    client: AsyncClient, apply_on, db_session, clean_rows
):
    first = await _apply(client)
    assert first.status_code == 201, first.text

    second = await _apply(client, name="同一个地址换个说法")
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["duplicate"] is True
    assert body["id"] == first.json()["id"], "去重必须回已有的那条，而不是新建一行"
    assert body["status"] == FriendLink.STATUS_PENDING

    rows = (
        (await db_session.execute(select(FriendLink).where(FriendLink.url == _FIRST)))
        .scalars()
        .all()
    )
    assert len(rows) == 1, "同地址刷出了多行，审核队列会被同一条目占满"


@pytest.mark.asyncio
async def test_already_approved_address_is_not_requeued(
    client: AsyncClient, apply_on, db_session, clean_rows, staff_headers
):
    await _apply(client)
    link_id = (await _row(db_session, _FIRST)).id
    await client.put(
        f"/api/friend-links/{link_id}", json={"status": "approved"}, headers=staff_headers
    )

    again = await _apply(client)
    assert again.status_code == 200, again.text
    assert again.json()["duplicate"] is True
    assert again.json()["status"] == FriendLink.STATUS_APPROVED, (
        "已公示的地址被重新排进 pending＝管理员的裁决被匿名请求改写"
    )


@pytest.mark.asyncio
async def test_rejected_address_can_apply_again(
    client: AsyncClient, apply_on, db_session, clean_rows, staff_headers
):
    """去重只看 pending/approved（与评论举报只看 open 同构）：驳回后再申请是正常诉求。"""
    await _apply(client)
    link_id = (await _row(db_session, _FIRST)).id
    await client.put(
        f"/api/friend-links/{link_id}", json={"status": "rejected"}, headers=staff_headers
    )

    again = await _apply(client)
    assert again.status_code == 201, again.text
    assert again.json()["duplicate"] is False


# ==================== ⑤ 验证码闸门与评论/留言同轨 ====================


@pytest.mark.asyncio
async def test_captcha_gate_blocks_anonymous_when_enabled(
    client: AsyncClient, apply_on, staff_headers, clean_rows
):
    await client.patch(
        "/api/settings/features", json={"enable_captcha": True}, headers=staff_headers
    )
    try:
        missing = await _apply(client, url=_SECOND)
        assert missing.status_code == 400, missing.text
        assert missing.json()["error_code"] == "CAPTCHA_REQUIRED"

        wrong = await _apply(client, url=_SECOND, captcha_key="fa-key", captcha_code="ZZZZ")
        assert wrong.status_code == 400, wrong.text
        assert wrong.json()["error_code"] in ("CAPTCHA_INVALID", "CAPTCHA_EXPIRED")

        await store_captcha_answer("ok-key", "QK7M")
        good = await _apply(client, url=_SECOND, captcha_key="ok-key", captcha_code="qk7m")
        assert good.status_code == 201, good.text
    finally:
        await client.patch(
            "/api/settings/features", json={"enable_captcha": False}, headers=staff_headers
        )


@pytest.mark.asyncio
async def test_logged_in_user_skips_captcha(
    client: AsyncClient, apply_on, auth_headers, staff_headers, clean_rows
):
    await client.patch(
        "/api/settings/features", json={"enable_captcha": True}, headers=staff_headers
    )
    try:
        resp = await client.post(
            "/api/friend-links/apply",
            json={"name": "登录用户的站", "url": _SECOND},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
    finally:
        await client.patch(
            "/api/settings/features", json={"enable_captcha": False}, headers=staff_headers
        )


# ==================== ⑥ 原文按请求语言入库，读取面靠回退链不缺字 ====================


@pytest.mark.asyncio
async def test_original_text_is_stored_under_request_language(
    client: AsyncClient, apply_on, db_session, clean_rows
):
    resp = await client.post(
        "/api/friend-links/apply",
        json={"name": "Example Blog", "url": _FIRST, "description": "A demo site"},
        headers={"Accept-Language": "en"},
    )
    assert resp.status_code == 201, resp.text

    row = await _row(db_session, _FIRST)
    assert set(row.name) == {"en"}, "四语复制会把短字段白存四份，单语 dict 才是既有口径"

    from backend.core.i18n import get_i18n_value

    # 中文页面读同一条必须仍然有字（回退链：目标语言 → 默认语言 → 任意语言）
    assert get_i18n_value(row.name, "zh") == "Example Blog"
    assert get_i18n_value(row.description, "ja") == "A demo site"
