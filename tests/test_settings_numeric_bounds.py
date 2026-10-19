"""数值设置键的写入侧区间闸门（`_check_numeric_bounds`）。

分组 PATCH 过去只按键集过滤，不判类型也不判区间，脏值原样进库后被执行点直接消费。
真实后果（每条都是一个"保存成功、前台坏了"的缺陷，不是理论风险）：
comments.max_length 负数 → 评论全线写不进去；reading.posts_per_page > 200 → 五个列表页
撞 api/blog.py 的 `Query(le=200)` 全部 422；security.max_login_attempts 巨大 → 锁定永不
触发；security.lockout_duration_sec 巨大 → 账号永久锁定；email.smtp_port 越界 → 发信静默失败。
"""

import pytest
from httpx import AsyncClient

from backend.api.media import UPLOAD_SIZE_CEILING_BYTES, UPLOAD_SIZE_FLOOR_BYTES
from backend.api.settings_groups import _GROUP_DEFAULTS, _NUMERIC_BOUNDS, _default_for


def _numeric_default_keys() -> set[str]:
    out: set[str] = set()
    for group in _GROUP_DEFAULTS:
        for key, value in _default_for(group).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                out.add(f"{group}.{key}")
    return out


def test_every_numeric_setting_key_declares_bounds():
    """新增数值键必须同时在 _NUMERIC_BOUNDS 里给出区间——否则它能存任意值。"""
    assert _numeric_default_keys() == set(_NUMERIC_BOUNDS), (
        "数值设置键清单与区间表不一致：少的那把键可以被写成 0/负数/天文数字，"
        "多的那条是已删键留下的死条目"
    )


def test_declared_bounds_contain_the_backend_default():
    """默认值自己要在区间内——否则"未保存过的站点"和"保存过的站点"口径互相矛盾。"""
    for dotted, (lo, hi) in _NUMERIC_BOUNDS.items():
        group, key = dotted.split(".")
        value = _default_for(group)[key]
        assert lo <= value <= hi, f"{dotted} 默认值 {value!r} 不在区间 {lo}-{hi} 内"


def test_upload_size_bounds_equal_the_server_clamp():
    """设置页输入框与 PATCH 的区间必须等于 api/media.py 的钳位区间，不得各写一份。"""
    assert _NUMERIC_BOUNDS["media.max_upload_size"] == (
        UPLOAD_SIZE_FLOOR_BYTES,
        UPLOAD_SIZE_CEILING_BYTES,
    )


@pytest.mark.parametrize(
    ("group", "key", "bad"),
    [
        ("reading", "posts_per_page", 0),
        ("reading", "posts_per_page", -5),
        ("reading", "posts_per_page", 51),
        # 前台把这里读到的数当 page_size 传给列表接口，而列表接口 le=200
        ("reading", "posts_per_page", 500),
        ("reading", "toc_depth", 0),
        ("reading", "toc_depth", 7),
        ("reading", "font_size", 0),
        ("reading", "font_size", 25),
        ("reading", "line_height", 0.5),
        ("reading", "line_height", 3),
        ("comments", "max_length", -3000),
        ("comments", "max_length", 0),
        ("comments", "max_length", 99),
        ("media", "max_upload_size", 1024),
        ("media", "max_upload_size", 10**9),
        ("email", "smtp_port", 0),
        ("email", "smtp_port", 65536),
        ("security", "max_login_attempts", 0),
        ("security", "max_login_attempts", 999999),
        ("security", "lockout_duration_sec", 59),
        ("security", "lockout_duration_sec", 10**9),
        ("appearance", "page_width_px", 0),
        ("appearance", "page_width_px", 799),
    ],
)
async def test_out_of_range_number_is_rejected_and_not_stored(
    client: AsyncClient, admin_headers: dict, group: str, key: str, bad: object
):
    before = (await client.get(f"/api/settings/{group}", headers=admin_headers)).json()["data"][key]

    resp = await client.patch(f"/api/settings/{group}", headers=admin_headers, json={key: bad})

    assert resp.status_code == 400, resp.text
    assert key in resp.text, f"报错要指出是哪把键：{resp.text}"
    after = (await client.get(f"/api/settings/{group}", headers=admin_headers)).json()["data"][key]
    assert after == before, "被拒的 PATCH 不得改动库里已有的值"


@pytest.mark.parametrize(
    ("group", "key", "value"),
    [
        ("reading", "posts_per_page", 12),
        ("reading", "posts_per_page", 1),
        ("reading", "posts_per_page", 50),
        ("reading", "line_height", 2),
        ("reading", "line_height", 1.75),
        ("comments", "max_length", 500),
        ("email", "smtp_port", 587),
        ("security", "max_login_attempts", 3),
        ("security", "lockout_duration_sec", 86400),
        ("appearance", "page_width_px", 1600),
    ],
)
async def test_in_range_number_is_stored_as_is(
    client: AsyncClient, admin_headers: dict, group: str, key: str, value: object
):
    resp = await client.patch(f"/api/settings/{group}", headers=admin_headers, json={key: value})

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"][key] == value
    fetched = (await client.get(f"/api/settings/{group}", headers=admin_headers)).json()["data"]
    assert fetched[key] == value, "回显必须等于写入值，不得被静默改写"


@pytest.mark.parametrize(
    ("group", "key", "bad"),
    [
        # 整数键拒收小数：9.5 会一路走到 SQLAlchemy 的 .limit() 才炸，那时已经是前台 500
        ("reading", "posts_per_page", 9.5),
        # bool 是 int 的子类，不能因为 isinstance(True, int) 就存成 1
        ("reading", "posts_per_page", True),
        ("comments", "max_length", False),
        ("email", "smtp_port", "465"),
        ("reading", "font_size", None),
        ("security", "max_login_attempts", ""),
    ],
)
async def test_wrong_type_is_rejected(
    client: AsyncClient, admin_headers: dict, group: str, key: str, bad: object
):
    resp = await client.patch(f"/api/settings/{group}", headers=admin_headers, json={key: bad})

    assert resp.status_code == 400, resp.text
    assert key in resp.text


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
async def test_non_finite_number_is_rejected(
    client: AsyncClient, admin_headers: dict, literal: str
):
    """json.loads 接受 NaN/Infinity 字面量，它们既能被存进库、又能让前台 JSON.parse 炸。

    NaN 还有一条更阴的路径：`lo <= NaN <= hi` 为 False 不代表它安全——它会被 json.dumps
    原样写回（allow_nan 默认 True），于是 /api/settings 的响应体不再是合法 JSON。

    请求体必须手写 JSON 文本：`json={"posts_per_page": float("nan")}` 在 httpx 本地就
    抛 ValueError（Out of range float values are not JSON compliant），根本到不了服务端，
    而真实的攻击面是过网络送进来的裸字面量。
    """
    resp = await client.patch(
        "/api/settings/reading",
        headers={**admin_headers, "Content-Type": "application/json"},
        content=f'{{"posts_per_page": {literal}}}',
    )

    assert resp.status_code == 400, resp.text
    assert "posts_per_page" in resp.text
    saved = (await client.get("/api/settings/reading", headers=admin_headers)).json()["data"]
    assert saved["posts_per_page"] == _default_for("reading")["posts_per_page"]
