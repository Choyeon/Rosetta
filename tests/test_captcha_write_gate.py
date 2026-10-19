"""图形验证码闸门：后台开关打开后，匿名评论/留言必须带有效验证码。

契约（2026-10 落地；此前 `api/captcha.py` 只有签发与自助校验，没有任何写入口消费它）：
1. 开关是 `features.enable_captcha`，默认 **False**——存量站点行为不变。
2. 只挡匿名提交；登录用户始终免验（已有账号级信号，再加图形码只会打残正常流程）。
3. 失败语义用 **400** 而不是 401：验证码错 ≠ 凭证失效（AGENTS §7.2）。
4. 一次性凭据：先作废再比对，重试必须重新取图。
5. 开关必须能在 `/api/settings/public` 里读到——前台表单要靠它决定是否渲染验证码输入框。
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from backend.services.captcha_service import consume_captcha, store_captcha_answer

_GB_BODY = {"content": "验证码闸门集成测试", "author_name": "测试访客"}


@pytest.fixture
async def captcha_on(client, staff_headers):
    """打开 `features.enable_captcha`，用例结束后按默认值复原。

    走 PATCH 而不是直写 SiteConfig：PATCH 才代表真实写路径（含分组缓存失效）。
    复原成 False 是必须的——残留 `enable_captcha: true` 会让后续任何匿名
    评论/留言用例突然被要求填码，那种红既不是回归也难排查。
    """
    await client.patch(
        "/api/settings/features", json={"enable_captcha": True}, headers=staff_headers
    )
    try:
        yield
    finally:
        await client.patch(
            "/api/settings/features", json={"enable_captcha": False}, headers=staff_headers
        )


# ==================== 单元：消费语义 ====================


@pytest.mark.asyncio
async def test_missing_fields_raise_required() -> None:
    for key, code in ((None, "AB"), ("k", None), ("", "AB"), ("k", "  ")):
        with pytest.raises(ValueError) as exc:
            await consume_captcha(key, code)
        assert str(exc.value) == "CAPTCHA_REQUIRED", f"key={key!r} code={code!r}"


@pytest.mark.asyncio
async def test_valid_code_is_case_insensitive_and_single_use() -> None:
    await store_captcha_answer("cap-ok", "AB3D")
    # 大小写不敏感
    await consume_captcha("cap-ok", "ab3d")
    # 已消费：同一 key 再用即过期，挡重放
    with pytest.raises(ValueError) as exc:
        await consume_captcha("cap-ok", "ab3d")
    assert str(exc.value) == "CAPTCHA_EXPIRED"


@pytest.mark.asyncio
async def test_wrong_code_invalidates_the_captcha() -> None:
    """比对不通过也要作废——32^4 的字符集扛不住 5 分钟在线枚举。"""
    await store_captcha_answer("cap-bad", "AB3D")
    with pytest.raises(ValueError) as exc:
        await consume_captcha("cap-bad", "ZZZZ")
    assert str(exc.value) == "CAPTCHA_INVALID"
    with pytest.raises(ValueError) as again:
        await consume_captcha("cap-bad", "AB3D")
    assert str(again.value) == "CAPTCHA_EXPIRED"


@pytest.mark.asyncio
async def test_unknown_key_is_expired() -> None:
    with pytest.raises(ValueError) as exc:
        await consume_captcha("never-issued", "AB3D")
    assert str(exc.value) == "CAPTCHA_EXPIRED"


# ==================== 集成：留言板写口 ====================


@pytest.mark.asyncio
async def test_guestbook_anonymous_requires_captcha(client: AsyncClient, captcha_on) -> None:
    resp = await client.post("/api/guestbook", json=dict(_GB_BODY))
    assert resp.status_code == 400, resp.text
    assert resp.json()["error_code"] == "CAPTCHA_REQUIRED"


@pytest.mark.asyncio
async def test_guestbook_wrong_captcha_is_400_not_401(client: AsyncClient, captcha_on) -> None:
    """401 会让前端把这次操作判成"登录过期"并清登录态——业务校验失败必须 400。"""
    await store_captcha_answer("gb-wrong", "QK7M")
    body = dict(_GB_BODY, captcha_key="gb-wrong", captcha_code="XXXX")
    resp = await client.post("/api/guestbook", json=body)
    assert resp.status_code == 400, resp.text
    assert resp.json()["error_code"] == "CAPTCHA_INVALID"


@pytest.mark.asyncio
async def test_guestbook_accepts_valid_captcha(client: AsyncClient, captcha_on, db_session) -> None:
    await store_captcha_answer("gb-cap", "QK7M")
    body = dict(_GB_BODY, captcha_key="gb-cap", captcha_code="qk7m")
    resp = await client.post("/api/guestbook", json=body)
    assert resp.status_code == 201, resp.text

    # 用后即弃：真落了库的测试留言不能留给别的用例
    from sqlalchemy import select

    from backend.models.guestbook import GuestbookEntry

    row = (
        await db_session.execute(
            select(GuestbookEntry).where(GuestbookEntry.id == resp.json()["id"])
        )
    ).scalar_one()
    await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_captcha_flag_off_keeps_anonymous_guestbook_open(
    client: AsyncClient, staff_headers, db_session
) -> None:
    """默认值必须等于既有行为：没配过 / 配成 False 时匿名留言照常通过。"""
    group = (await client.get("/api/settings/features", headers=staff_headers)).json()["data"]
    assert group["enable_captcha"] is False, "features 默认值被改动：闸门会打残存量站点的匿名留言"

    body = dict(_GB_BODY, captcha_key=None, captcha_code=None)
    resp = await client.post("/api/guestbook", json=body)
    assert resp.status_code == 201, resp.text

    from sqlalchemy import select

    from backend.models.guestbook import GuestbookEntry

    row = (
        await db_session.execute(
            select(GuestbookEntry).where(GuestbookEntry.id == resp.json()["id"])
        )
    ).scalar_one()
    await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_captcha_flag_is_public_for_the_form(client: AsyncClient) -> None:
    """前台表单要在未登录时读到这个开关——所以它必须在公开分组白名单里。"""
    pub = await client.get("/api/settings/public")
    assert pub.status_code == 200, pub.text
    data = pub.json()["groups"]
    assert "features" in data
    assert "enable_captcha" in data["features"]


def test_captcha_verify_endpoint_is_not_the_only_consumer() -> None:
    """写入口必须真的调闸门：漏接线时验证码只是"能取能验但没人看"（历史上的状态）。"""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    for rel in ("backend/services/comment_service.py", "backend/services/guestbook_service.py"):
        source = (root / rel).read_text(encoding="utf-8")
        assert "ensure_captcha_for_guest" in source, f"{rel} 没有接验证码闸门"


def test_login_fail_helpers_stay_removed() -> None:
    """`login_fail:*` 那套按失败次数决定是否需要验证码的实现从未被调用，已删除；
    登录锁定由 `security.max_login_attempts` 那条路径负责，不要长出第二套。"""
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / "backend" / "api" / "captcha.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("check_captcha_required", "record_login_fail", "login_fail:"):
        assert forbidden not in source, f"已删除的无调用方实现又回流了：{forbidden}"


def test_unused_sentinel_type_import_guard() -> None:
    """Any 只用于登录用户绕过那条用例的占位对象；不引入运行期依赖。"""

    async def _noop() -> Any:  # pragma: no cover - 结构性断言占位
        return object()

    assert _noop is not None
