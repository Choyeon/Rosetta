"""站点设置分组「保存即生效」契约回归（后台 17 组 → 真实执行点）。

起因：设置页写的是 site_configs 里 ``key=分组名`` 的整段 JSON，而历史上只有
``/api/config`` 与 ``/settings/public`` 两条读口会把其中一部分叠进返回值。于是两类
静默缺陷长期存在，且都不报错：

① **写了存不进**：``_save_group`` 用 ``if k in base`` 过滤 payload，任何不在
   ``_default_<group>()`` 键集里的字段被静默丢弃。设置页已经在发 ``basic.about_page_html``
   （前台 /about 真的会渲染它）——管理员改完点保存，接口回 200，库里永远没有这个键。
② **存了没人读**：``comments`` 分组七个键、``media.max_upload_size``、``seo.robots_txt``、
   ``features.*`` 全部只进库不进制——执行点读的是环境变量或硬编码常量。
   表现是"关掉评论还能评、改小上传上限照样传 20MB、robots 改了爬虫读的仍是旧的"。

本文件把两件事钉住：UI 发的每个键都必须在后端默认键集里（否则 CI 红），
以及关键分组的值必须在**读者真正拿到的那份响应里**生效。
"""

import itertools
import re
from pathlib import Path

import pytest

from backend.api.media import (
    LIBRARY_ALLOWED_EXTENSIONS,
    UPLOAD_SIZE_CEILING_BYTES,
    UPLOAD_SIZE_FLOOR_BYTES,
    _effective_library_exts,
    _effective_upload_limit,
)
from backend.api.settings_groups import SETTING_GROUPS_17, _default_for
from backend.services.site_settings import bool_of, int_of

SETTINGS_PAGE = Path(__file__).resolve().parents[1] / "frontend/pages/admin/system/settings.vue"


async def _patch(client, staff_headers, group: str, payload: dict):
    resp = await client.patch(f"/api/settings/{group}", json=payload, headers=staff_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


_IP_SEQ = itertools.count(1)


def _fresh_ip() -> dict:
    """每次换一个新访客 IP。

    评论写口有"同 post + 同 IP 30s 防重"（429 TOO_FREQUENT_COMMENT），同一条用例里
    连发两条就会被它拦下——那是频控在正常工作，不是分组设置没生效。
    """
    n = next(_IP_SEQ)
    return {"X-Forwarded-For": f"10.77.{n // 250 % 250}.{n % 250}"}


async def _post_comment(client, post_id: int, content: str = "这是一条测试评论内容"):
    return await client.post(
        f"/api/posts/{post_id}/comments",
        json={"content": content, "author_name": "读友"},
        headers=_fresh_ip(),
    )


# ==================== ① 写入口：UI 发的键必须都能落库 ====================


def _ui_group_fields() -> dict[str, set[str]]:
    """从设置页源码里抽出每个分组实际提交的键名。"""
    text = SETTINGS_PAGE.read_text(encoding="utf-8")
    body = re.search(r"function getDefaultsFor.*?\n\}", text, re.S)
    assert body, "设置页里找不到 getDefaultsFor —— 该回归的前提已经变了，请同步改这个测试"
    out: dict[str, set[str]] = {}
    for gm in re.finditer(r"^\s{4}(\w+): \{(.*)\},?$", body.group(0), re.M):
        out[gm.group(1)] = {km.group(1) for km in re.finditer(r"([A-Za-z_]\w*)\s*:", gm.group(2))}
    return out


def test_settings_page_submits_only_writable_keys():
    """设置页提交的每个键都必须在 ``_default_<group>()`` 键集内。

    ``_save_group`` 的 ``if k in base`` 是静默丢弃，不是报错：这条断言是它唯一的暴露面。
    """
    ui = _ui_group_fields()
    assert set(ui) == set(SETTING_GROUPS_17), f"设置页分组与后端 17 组不一致：{set(ui) ^ set(SETTING_GROUPS_17)}"
    unwritable = {
        g: sorted(keys - set(_default_for(g))) for g, keys in ui.items() if keys - set(_default_for(g))
    }
    assert not unwritable, (
        "这些键设置页会提交但后端存不进去（不在分组默认值里，_save_group 静默丢弃）："
        f"{unwritable}；要么补进 _default_*，要么从设置页移除"
    )


# ==================== ② 执行点：comments 分组真的决定评论行为 ====================


@pytest.mark.asyncio
async def test_comments_group_disabling_blocks_new_comments(client, staff_headers, test_post):
    """关掉评论开关后写口必须拒（此前该分组 100% 无人读取，关了也能评）。"""
    await _patch(client, staff_headers, "comments", {"enable": False})
    try:
        resp = await _post_comment(client, test_post.id)
        assert resp.status_code == 403, resp.text
        assert resp.json()["error_code"] == "COMMENTS_DISABLED"
    finally:
        await _patch(client, staff_headers, "comments", {"enable": True})


@pytest.mark.asyncio
async def test_comments_require_approval_group_overrides_env(client, staff_headers, test_post):
    """分组里勾了"新评论需审核" → 落库状态是 pending，不是环境变量算出来的 approved。"""
    pid = test_post.id
    await _patch(client, staff_headers, "comments", {"require_approval": True})
    try:
        resp = await _post_comment(client, pid)
        assert resp.status_code in (200, 201), resp.text
        assert resp.json()["status"] == "pending"
    finally:
        await _patch(client, staff_headers, "comments", {"require_approval": False})
    after = await _post_comment(client, pid)
    assert after.status_code in (200, 201), after.text
    assert after.json()["status"] == "approved"
    # 用后即弃：别把测试评论留给其它用例当"已有评论"读
    await client.post(
        "/api/admin/comments/batch",
        json={"action": "delete", "ids": [resp.json()["id"], after.json()["id"]]},
        headers=staff_headers,
    )


@pytest.mark.asyncio
async def test_comments_guest_toggle_rejects_anonymous_only(
    client, staff_headers, test_post, auth_headers
):
    """allow_guest=false：匿名 403，登录用户照写（用 401 会把前端判成登录过期）。"""
    # 先取好 id：请求失败路径上的 rollback 会把测试会话里的 ORM 行标记为过期，
    # 之后在测试代码里再读 test_post.id 会在 greenlet 外触发隐式 IO（MissingGreenlet）。
    pid = test_post.id
    await _patch(client, staff_headers, "comments", {"allow_guest": False})
    try:
        anon = await _post_comment(client, pid)
        assert anon.status_code == 403, anon.text
        assert anon.json()["error_code"] == "COMMENT_GUEST_NOT_ALLOWED"
        member = await client.post(
            f"/api/posts/{pid}/comments",
            json={"content": "登录用户的测试评论"},
            headers={**auth_headers, **_fresh_ip()},
        )
        assert member.status_code in (200, 201), member.text
    finally:
        await _patch(client, staff_headers, "comments", {"allow_guest": True})
    if member.status_code in (200, 201):
        await client.post(
            "/api/admin/comments/batch",
            json={"action": "delete", "ids": [member.json()["id"]]},
            headers=staff_headers,
        )


@pytest.mark.asyncio
async def test_comments_max_length_from_group(client, staff_headers, test_post):
    """max_length=10 → 20 字正文被拒（历史上只有 Pydantic 的 3000 硬编码在守）。"""
    await _patch(client, staff_headers, "comments", {"max_length": 10})
    try:
        resp = await _post_comment(client, test_post.id, content="十个字不够用这条应该被拒掉的")
        assert resp.status_code == 422, resp.text
        assert resp.json()["error_code"] == "COMMENT_TOO_LONG"
    finally:
        await _patch(client, staff_headers, "comments", {"max_length": 3000})


# ==================== ③ media 分组：收紧生效，放松无效 ====================


def test_upload_limit_respects_group_but_stays_clamped():
    assert _effective_upload_limit({"max_upload_size": 1024 * 1024}, 20 * 1024 * 1024) == 1024 * 1024
    # 未配置 = 既有上限，不被 _default_media 的 10MB 悄悄改写
    assert _effective_upload_limit({}, 20 * 1024 * 1024) == 20 * 1024 * 1024
    # 填错单位/填 0/填一个 GB：钳进安全区间，不放开也不关掉上传
    assert _effective_upload_limit({"max_upload_size": 0}, 10 * 1024 * 1024) == UPLOAD_SIZE_FLOOR_BYTES
    assert (
        _effective_upload_limit({"max_upload_size": 999 * 1024 * 1024}, 10 * 1024 * 1024)
        == UPLOAD_SIZE_CEILING_BYTES
    )
    assert _effective_upload_limit({"max_upload_size": "abc"}, 10 * 1024 * 1024) == 10 * 1024 * 1024


def test_library_extensions_can_narrow_never_widen():
    only_png = {"allowed_image_types": "png,.PNG ", "allowed_file_types": ""}
    assert _effective_library_exts(only_png) == frozenset({"png"})
    # 白名单之外的一律交集掉：没有魔术字节表的扩展名 = 同源可执行文件落地
    hostile = {"allowed_file_types": "png,exe,php,html"}
    assert _effective_library_exts(hostile) == frozenset({"png"})
    assert _effective_library_exts({}) == LIBRARY_ALLOWED_EXTENSIONS


@pytest.mark.asyncio
async def test_media_watermark_key_is_persisted(client, staff_headers):
    """media.watermark_text 是 api/media.py::_read_watermark_text 在读的键，
    缺 _default_media 时属于"①写了存不进"，这里钉住它能存能读回。"""
    saved = await _patch(client, staff_headers, "media", {"watermark_text": "© choyeon.cc"})
    assert saved["watermark_text"] == "© choyeon.cc"
    resp = await client.get("/api/settings/media", headers=staff_headers)
    assert resp.json()["data"]["watermark_text"] == "© choyeon.cc"
    await _patch(client, staff_headers, "media", {"watermark_text": ""})


@pytest.mark.asyncio
async def test_about_page_html_is_persisted(client, staff_headers):
    """basic.about_page_html：前台 /about 会 v-html 它，设置页在发它，
    但它曾不在 _default_basic 里 → 保存 200、库里没有。"""
    saved = await _patch(client, staff_headers, "basic", {"about_page_html": "<h1>关于我</h1>"})
    assert saved["about_page_html"] == "<h1>关于我</h1>"
    cfg = await client.get("/api/config")
    assert cfg.json()["about_page_html"] == "<h1>关于我</h1>"
    await _patch(client, staff_headers, "basic", {"about_page_html": ""})


# ==================== ④ seo / features 分组下发到读者 ====================


@pytest.mark.asyncio
async def test_seo_group_robots_txt_replaces_generated_default(client, staff_headers):
    """管理员写了真正的 robots 正文 → 接口下发它；留空/保留占位文本 → 继续下发系统生成的安全版。"""
    custom = "User-agent: *\nDisallow: /private/"
    await _patch(client, staff_headers, "seo", {"robots_txt": custom})
    try:
        resp = await client.get("/api/seo/robots.txt")
        assert resp.status_code == 200
        assert "Disallow: /private/" in resp.text
    finally:
        await _patch(client, staff_headers, "seo", {"robots_txt": ""})
    fallback = await client.get("/api/seo/robots.txt")
    assert "/api/" in fallback.text  # 安全默认版一定挡着 /api/


@pytest.mark.asyncio
async def test_features_group_reaches_api_config(client, staff_headers):
    """features 分组曾只进库；/api/config 的 enable_* 读的是扁平 ENABLE_* 键。"""
    await _patch(client, staff_headers, "features", {"enable_guestbook": False})
    try:
        cfg = await client.get("/api/config")
        assert cfg.json()["enable_guestbook"] is False
    finally:
        await _patch(client, staff_headers, "features", {"enable_guestbook": True})
    cfg = await client.get("/api/config")
    assert cfg.json()["enable_guestbook"] is True


# ==================== ⑤ 解析工具：坏配置不能炸主流程 ====================


def test_bool_of_and_int_of_tolerate_legacy_value_shapes():
    cfg = {"a": "true", "b": 0, "c": "1000", "d": "oops", "e": None}
    assert bool_of(cfg, "a", False) is True
    assert bool_of(cfg, "b", True) is False
    assert bool_of(cfg, "e", True) is True  # 显式 null 按未配置处理
    assert int_of(cfg, "c", 5) == 1000
    assert int_of(cfg, "d", 5) == 5
    assert int_of(cfg, "missing", 5) == 5
