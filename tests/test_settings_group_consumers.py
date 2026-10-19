"""站点设置分组「保存即生效」契约回归（后台 13 组 → 真实执行点）。

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
from backend.api.settings_groups import PUBLIC_SETTING_GROUPS, SETTING_GROUPS, _default_for
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
    IP 落库前先脱敏成 ``<前两段>.x.x``（mask_ip），所以必须换**第二段**才算不同访客。
    """
    n = next(_IP_SEQ)
    return {"X-Forwarded-For": f"10.{n % 200 + 1}.1.1"}


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
    assert set(ui) == set(SETTING_GROUPS), f"设置页分组与后端 13 组不一致：{set(ui) ^ set(SETTING_GROUPS)}"
    unwritable = {
        g: sorted(keys - set(_default_for(g))) for g, keys in ui.items() if keys - set(_default_for(g))
    }
    assert not unwritable, (
        "这些键设置页会提交但后端存不进去（不在分组默认值里，_save_group 静默丢弃）："
        f"{unwritable}；要么补进 _default_*，要么从设置页移除"
    )


# 已删除的死配置：能存、能回显，但 read_group / /api/config 分组覆写 / 前端消费方三处全空。
# CDN 前缀的真实执行点是 media.use_cdn + media.cdn_prefix；缓存后端与 TTL 只在环境变量里；
# 友情链接走 friend_links 表 + /api/friend-links；侧边栏显示/位置走主题 Customizer 的 mods
# （show_sidebar / sidebar_position），代码配色走 --hljs-* 令牌，明暗首帧走 localStorage.theme。
# 留着它们只等于给管理员一批假开关。
_INERT_KEYS = {
    "cdn_url",
    "image_cdn_url",
    "static_cdn_url",
    "purge_token",
    "site_config_ttl",
    "post_list_ttl",
    "flush_on_post_update",
    "session_timeout_sec",
    "enable_rate_limit",
    "allowed_hosts",
    "cors_origins",
    "require_email_verification",
    "allow_password_reset",
    "custom_links",
    "auto_approve",
    "max_nested_depth",
    "admin_email",
    "code_theme",
    "code_theme_dark",
    "default_theme",
    "font_family",
    "widget_order",
    "show_profile",
    "show_categories",
    "show_tags",
    "show_recent_posts",
    "show_recent_comments",
    "show_tag_cloud",
    "show_site_info",
    "show_music",
    "show_statistics",
    "show_dynamics",
    # 第二轮收口：about_content 被 about_page_html 取代；媒体默认封面/头像没有任何读取点
    # （封面走 lib/post-cover.ts 的 picsum seed，头像走 core/avatar_resolver 的 DiceBear）；
    # 两个统计 ID 没有注入口，补注入口要放松 CSP（AGENTS §12.6 禁止）。
    "about_content",
    "default_post_cover",
    "default_avatar",
    "google_analytics_id",
    "baidu_analytics_id",
}

_INERT_GROUPS = {"cdn", "cache", "friendlinks", "sidebar"}


def test_inert_setting_keys_stay_removed():
    """死配置不得回流：一旦被重新放进 _default_*，设置页就能提交一个没人执行的开关。"""
    live = {k for g in SETTING_GROUPS for k in _default_for(g)}
    assert not (live & _INERT_KEYS), f"这些键没有任何执行点，却被放回分组默认值：{sorted(live & _INERT_KEYS)}"
    assert set(SETTING_GROUPS).isdisjoint(_INERT_GROUPS)


@pytest.mark.asyncio
async def test_stale_keys_in_stored_blob_are_not_resurfaced(client, staff_headers, db_session):
    """库里残留的已删除键不得再被接口回显。

    ``_load_all_groups`` 曾整段透出存量 JSON：删掉一个死键后旧 JSON 里它还在，
    设置页读出来再提交回去 = 刚删的开关被写回库，"删了但没删干净"。
    """
    from sqlalchemy import select

    from backend.models.core import SiteConfig

    row = (
        await db_session.execute(select(SiteConfig).where(SiteConfig.key == "navigation"))
    ).scalar_one_or_none()
    if row is None:
        row = SiteConfig(key="navigation", value="{}", description="系统设置 - navigation")
        db_session.add(row)
    row.value = '{"header_style": "static", "custom_links": [{"label": "旧链接"}]}'
    await db_session.commit()

    resp = await client.get("/api/settings/navigation", headers=staff_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert "custom_links" not in data
    assert data["header_style"] == "static"  # 存量里的活键必须原样保留


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
async def test_comments_require_approval_group_drives_guestbook(client, staff_headers):
    """留言板必须读同一份 comments.require_approval 分组（此前只按环境变量走，
    后台"新评论需审核"对留言静默失效）：勾上→pending，取消→approved。"""

    async def post_gb():
        return await client.post(
            "/api/guestbook",
            json={"content": "这是一条测试留言内容", "author_name": "读友"},
            headers=_fresh_ip(),
        )

    await _patch(client, staff_headers, "comments", {"require_approval": True})
    try:
        resp = await post_gb()
        assert resp.status_code in (200, 201), resp.text
        assert resp.json()["status"] == "pending", "分组勾了审核，留言却未进 pending"
    finally:
        await _patch(client, staff_headers, "comments", {"require_approval": False})
    after = await post_gb()
    assert after.status_code in (200, 201), after.text
    assert after.json()["status"] == "approved"
    await client.post(
        "/api/admin/guestbook/batch",
        json={"action": "delete", "ids": [resp.json()["id"], after.json()["id"]]},
        headers=staff_headers,
    )


@pytest.mark.asyncio
async def test_comments_antispam_toggle_drives_guestbook(client, staff_headers):
    """留言板必须读 comments.enable_antispam：开着时黑名单词直接 rejected，
    关掉后跳过敏感词判定、只按 require_approval 走（此前留言板恒按黑名单拒绝，开关无效）。"""
    black = "这是一条含 porn 的测试留言"

    async def post_black():
        return await client.post(
            "/api/guestbook",
            json={"content": black, "author_name": "读友"},
            headers=_fresh_ip(),
        )

    await _patch(
        client, staff_headers, "comments", {"enable_antispam": True, "require_approval": False}
    )
    on = await post_black()
    assert on.status_code in (200, 201), on.text
    assert on.json()["status"] == "rejected"

    try:
        await _patch(client, staff_headers, "comments", {"enable_antispam": False})
        off = await post_black()
        assert off.status_code in (200, 201), off.text
        assert off.json()["status"] == "approved", "关掉反垃圾后黑名单词不应再被自动拒绝"
    finally:
        await _patch(client, staff_headers, "comments", {"enable_antispam": True})

    await client.post(
        "/api/admin/guestbook/batch",
        json={"action": "delete", "ids": [on.json()["id"], off.json()["id"]]},
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


@pytest.mark.asyncio
async def test_features_registration_gate_blocks_register(client, staff_headers):
    """enable_registration 曾只用来藏前端按钮；执行点读扁平 ENABLE_REGISTRATION，

    于是"后台关掉注册"之后直接 POST /api/users/register 仍然能建号。
    """
    await _patch(client, staff_headers, "features", {"enable_registration": False})
    try:
        resp = await client.post(
            "/api/users/register",
            json={"username": "gateduser", "email": "gated@example.com", "password": "Testpass999"},
        )
        assert resp.status_code == 403, resp.text
    finally:
        await _patch(client, staff_headers, "features", {"enable_registration": True})
    resp = await client.post(
        "/api/users/register",
        json={"username": "gateduser2", "email": "gated2@example.com", "password": "Testpass999"},
    )
    assert resp.status_code in (200, 201), resp.text


@pytest.mark.asyncio
async def test_features_guestbook_gate_blocks_post(client, staff_headers):
    """留言板历史上只有同 IP 频控，enable_guestbook 这个开关完全没有执行点。"""
    await _patch(client, staff_headers, "features", {"enable_guestbook": False})
    try:
        resp = await client.post(
            "/api/guestbook",
            json={"content": "这条应该被闸门挡住", "author_name": "读友"},
            headers=_fresh_ip(),
        )
        assert resp.status_code == 403, resp.text
        assert resp.json().get("error_code") == "GUESTBOOK_DISABLED"
    finally:
        await _patch(client, staff_headers, "features", {"enable_guestbook": True})
    resp = await client.post(
        "/api/guestbook",
        json={"content": "闸门打开后应当可以写入", "author_name": "读友"},
        headers=_fresh_ip(),
    )
    assert resp.status_code in (200, 201), resp.text


@pytest.mark.asyncio
async def test_features_enable_rss_gate_blocks_feed(client, staff_headers):
    """enable_rss 曾只控制页脚链接显示；/api/blog/rss 永远吐 200 的合法源。

    关掉之后爬虫与阅读器仍能订阅到全文，等于后台的开关只对自己人有效。
    """
    before = await client.get("/api/blog/rss")
    assert before.status_code == 200
    assert "<rss" in before.text

    await _patch(client, staff_headers, "features", {"enable_rss": False})
    try:
        resp = await client.get("/api/blog/rss")
        assert resp.status_code == 404, resp.text
        assert resp.json()["error_code"] == "RSS_DISABLED"
    finally:
        await _patch(client, staff_headers, "features", {"enable_rss": True})
    after = await client.get("/api/blog/rss")
    assert after.status_code == 200
    assert "<rss" in after.text


@pytest.mark.asyncio
async def test_features_enable_sitemap_gate_blocks_all_routes(client, staff_headers):
    """enable_sitemap 同理：index + 四个分片必须一起关，只关 index 会让已提交的
    分片 URL 继续被读取（Google 按分片独立抓取）。"""
    paths = [
        "/api/blog/sitemap.xml",
        "/api/blog/sitemap-posts.xml",
        "/api/blog/sitemap-taxonomies.xml",
        "/api/blog/sitemap-pages.xml",
    ]
    await _patch(client, staff_headers, "features", {"enable_sitemap": False})
    try:
        for p in paths:
            resp = await client.get(p)
            assert resp.status_code == 404, f"{p} -> {resp.status_code}"
            assert resp.json()["error_code"] == "SITEMAP_DISABLED"
    finally:
        await _patch(client, staff_headers, "features", {"enable_sitemap": True})
    for p in paths:
        assert (await client.get(p)).status_code == 200, p


@pytest.mark.asyncio
async def test_email_group_overrides_env_for_outbound_config(client, staff_headers):
    """email 分组历史上只有 settings.vue 在读写它，发信用的仍是构造时快照的 env。

    钉住两件事：后台填了的 from_address/from_name 必须真的进发信参数；
    后台留空的 smtp_password 不得把 .env 里的凭据清掉（整段落库 + 密码不回显）。
    """
    from backend.services.email_service import get_email_service

    svc = get_email_service()
    await _patch(
        client,
        staff_headers,
        "email",
        {"from_address": "blog@example.com", "from_name": "读友小站", "smtp_password": ""},
    )
    try:
        cfg = await svc.resolved_smtp()
        assert cfg["from_email"] == "blog@example.com"
        assert cfg["from_name"] == "读友小站"
        assert cfg["password"] == svc.smtp_password  # 空串 = 不覆写
        assert await svc.smtp_is_configured() == bool(
            cfg["host"] and cfg["user"] and cfg["password"]
        )
    finally:
        await _patch(client, staff_headers, "email", {"from_address": "", "from_name": ""})
    back = await svc.resolved_smtp()
    assert back["from_email"] != "blog@example.com"


@pytest.mark.asyncio
async def test_email_notifications_switch_is_read_by_caller(client, staff_headers):
    """enable_notifications 必须有人读（comment_service 在门它）。

    不在这里断言"未保存 = True"：上面那条用例已经把该分组落库，分组默认值
    enable_notifications=false 会跟着整段写进去——那正是该开关的语义，不是 bug。
    """
    from backend.services.email_service import email_notifications_enabled

    await _patch(client, staff_headers, "email", {"enable_notifications": False})
    try:
        assert await email_notifications_enabled() is False
    finally:
        await _patch(client, staff_headers, "email", {"enable_notifications": True})
    assert await email_notifications_enabled() is True


@pytest.mark.asyncio
async def test_security_group_lockout_threshold_and_duration(client, staff_headers):
    """security 分组历史上只有 env 版生效：后台把"最大登录次数"改成 2、锁定时长改成 60s，
    响应里看到的仍是 .env 的 5 次 / 10 分钟。

    用一次性账号，不碰共享的 test_user——这里没有解锁接口，锁定只能等它自然过期，
    锁到 test_user 身上会把后续用例的登录全变成 423。
    """
    reg = await client.post(
        "/api/users/register",
        json={
            "username": "secgrpuser",
            "email": "secgrp@example.com",
            "password": "Testpass999",
        },
    )
    assert reg.status_code in (200, 201), reg.text

    await _patch(
        client, staff_headers, "security", {"max_login_attempts": 2, "lockout_duration_sec": 60}
    )
    try:
        for i in range(2):
            r = await client.post(
                "/api/users/login",
                json={"username": "secgrpuser", "password": f"Wrongpass-secgrp-{i}"},
                headers=_fresh_ip(),
            )
            assert r.status_code == 401, r.text
        locked = await client.post(
            "/api/users/login",
            json={"username": "secgrpuser", "password": "Whatever"},
            headers=_fresh_ip(),
        )
        assert locked.status_code == 423, locked.text
        wait = int(locked.headers.get("Retry-After") or 0)
        assert 0 < wait <= 60, f"锁定秒数应来自分组 lockout_duration_sec=60，实得 {wait}"
    finally:
        await _patch(
            client,
            staff_headers,
            "security",
            {"max_login_attempts": 5, "lockout_duration_sec": 1800},
        )


# ==================== ⑤ 解析工具：坏配置不能炸主流程 ====================


def test_bool_of_and_int_of_tolerate_legacy_value_shapes():
    cfg = {"a": "true", "b": 0, "c": "1000", "d": "oops", "e": None}
    assert bool_of(cfg, "a", False) is True
    assert bool_of(cfg, "b", True) is False
    assert bool_of(cfg, "e", True) is True  # 显式 null 按未配置处理
    assert int_of(cfg, "c", 5) == 1000
    assert int_of(cfg, "d", 5) == 5
    assert int_of(cfg, "missing", 5) == 5


# ==================== ⑥ comments 分组必须能下发到匿名前台 ====================


def test_comments_group_is_publicly_readable():
    """allow_guest / max_length / enable_nested 的执行点在**前台表单**：
    访客要看到昵称邮箱框、字数上限、回复按钮，都得在未登录时读到这份分组。
    把它留在非公开组 = 后台三个开关永远没有界面表现（历史上的状态）。"""
    assert "comments" in PUBLIC_SETTING_GROUPS


@pytest.mark.asyncio
async def test_settings_public_exposes_comments_switch_values(client, staff_headers) -> None:
    """改值后匿名读口必须回新值，而不是分组的出厂默认。"""
    try:
        await _patch(
            client,
            staff_headers,
            "comments",
            {"allow_guest": False, "max_length": 120, "enable_nested": False},
        )
        pub = await client.get("/api/settings/public")
        assert pub.status_code == 200, pub.text
        comments = pub.json()["groups"]["comments"]
        assert comments["allow_guest"] is False
        assert comments["max_length"] == 120
        assert comments["enable_nested"] is False
    finally:
        await _patch(
            client,
            staff_headers,
            "comments",
            {"allow_guest": True, "max_length": 3000, "enable_nested": True},
        )
