"""扁平站点配置的最后 59 个零消费方键退役后的守卫（批次 #112）。

批次 #109（第三方评论 26 键）、#110（music/wallpaper/sidebar/sakura/pio 46 键）之后，
`/api/config` 这一族剩下的形状是：**147 个响应字段里只有 88 个真的有人读**。本批删掉其余 59 个，
它们分两种缺陷（同一份判据，断点位置不同）：

* **「存得进、没人读」17 个**——`about_content`、`dynamic_page_*`(4)、`friends_page_*` +
  `friends_apply_html`(5)、`sponsor_page_*` + `sponsor_methods_json` + `sponsor_show_sponsors_list`(6)、
  `site_start_date`。它们在 `POST /api/admin/settings` 的 `config_map` 里，写了会落库，
  `/api/config` 又原样投影给访客与 SSR；但前台一个渲染器都不读。
* **「假装保存」42 个**——`post_list_*`(5)、`cover_*`(4)、`license_*`(4)、`bangumi_*`(5)、
  `anime_*`(3)、`page_*_enabled`(7)、`mermaid_*`(2) + `plantuml_server_url`、`image_opt_*`(3)、
  `pagination_posts_per_page`、`category_bar_enabled`、`archive_fold_old_articles`、
  `post_show_last_modified`、`post_outdated_threshold_days`、`post_enable_share_poster`、
  `post_generate_og_images`、`dynamic_page_*` 之外的版式项。它们只在 `SiteConfigUpdate`
  里被收下，`config_map` 从不转译落库——接口回 200，库里一个字节没变。

**为什么是退役而不是接线**：每一族都已经有一个真在工作的单源，把扁平键"接通"只会造出第二个
互相矛盾的真相源——

| 退役的扁平键 | 现存唯一真源 |
| --- | --- |
| `friends_page_title` / `dynamic_page_title` / `sponsor_page_title` | i18n（`t('friends.title')`、`t('activity.title')`）与 `donate.title` |
| `friends_apply_html` / `friends_page_description` / `dynamic_page_description` | 页面自身与 i18n 文案 |
| `about_content` | `basic.about_page_html`（前台 /about 只渲染它） |
| `sponsor_methods_json` / `sponsor_show_sponsors_list` | `donate.methods` / `donate.sponsors` / `donate.show_sponsors_list` |
| `sponsor_page_usage` | `donate.description` |
| `page_guestbook_enabled` | `features.enable_guestbook`（`api/guestbook.py` 强制点） |
| `page_sponsor_enabled` | `donate.enable`（批次 #210 的公开面收起） |
| `pagination_posts_per_page` | `reading.posts_per_page`（列表/分类/标签/作者/搜索五页） |
| `post_show_last_modified` | 详情页 `showUpdatedAt`：`updated > published` 才显示，按值判定不按开关 |
| `cover_*` | `frontend/lib/post-cover.ts` 展示/分享两档（批次 #1/#2） |
| `post_enable_share_poster` | `features.enable_share_buttons` |
| `bangumi_*` / `anime_*` / `page_bangumi_enabled` / `page_anime_enabled` | 整族无实现：`frontend/pages/` 没有 bangumi/anime 页，后端也没有对应 router |
| `mermaid_*` / `plantuml_server_url` / `image_opt_*` / `license_*` / `post_generate_og_images` / `post_outdated_threshold_days` / `category_bar_enabled` / `archive_fold_old_articles` / `site_start_date` / `post_list_*` / `page_*_enabled` 其余项 | 零消费方，且不存在"另一份配置"——前端要么固定实现，要么根本没有这个功能 |

另一半断言防"把删死键做成删活功能"：i18n 标题、`donate` 分组、`basic.about_page_html`、
`features.enable_guestbook`、`reading.posts_per_page`、详情页的「更新于」判定必须原样活着；
`/api/config` 的字段总数按声明模型收敛（88/77），不再随库里的存量行膨胀。
"""

import re
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select

from backend.main import app

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"

DEAD_KEYS: tuple[str, ...] = (
    "about_content",
    "anime_bilibili_uid",
    "anime_tmdb_api_key",
    "anime_tmdb_list_id",
    "archive_fold_old_articles",
    "bangumi_api_url",
    "bangumi_category_order_json",
    "bangumi_mode",
    "bangumi_subject_base_url",
    "bangumi_user_id",
    "category_bar_enabled",
    "cover_enable_in_post",
    "cover_enable_overlay",
    "cover_random_apis_json",
    "cover_random_enable",
    "cover_show_loading",
    "dynamic_page_description",
    "dynamic_page_items_per_page",
    "dynamic_page_show_comment",
    "dynamic_page_title",
    "friends_apply_html",
    "friends_page_description",
    "friends_page_show_comment",
    "friends_page_show_custom_content",
    "friends_page_title",
    "image_opt_formats",
    "image_opt_no_referrer_json",
    "image_opt_quality",
    "license_enable",
    "license_icon",
    "license_name",
    "license_url",
    "mermaid_security_level",
    "mermaid_theme",
    "page_anime_enabled",
    "page_bangumi_enabled",
    "page_dynamic_enabled",
    "page_friends_enabled",
    "page_gallery_enabled",
    "page_guestbook_enabled",
    "page_sponsor_enabled",
    "pagination_posts_per_page",
    "plantuml_server_url",
    "post_enable_share_poster",
    "post_generate_og_images",
    "post_list_default_mode",
    "post_list_description_lines",
    "post_list_mobile_mode",
    "post_list_show_stats_icons",
    "post_list_tags_position",
    "post_outdated_threshold_days",
    "post_show_last_modified",
    "site_start_date",
    "sponsor_methods_json",
    "sponsor_page_description",
    "sponsor_page_show_comment",
    "sponsor_page_title",
    "sponsor_page_usage",
    "sponsor_show_sponsors_list",
)

DEAD_ENVS = tuple(key.upper() for key in DEAD_KEYS)

# 这 17 个曾在 config_map 里（写了就落库）；其余 42 个连转译表都不收
STORED_BEFORE = (
    "about_content",
    "dynamic_page_description",
    "dynamic_page_items_per_page",
    "dynamic_page_show_comment",
    "dynamic_page_title",
    "friends_apply_html",
    "friends_page_description",
    "friends_page_show_comment",
    "friends_page_show_custom_content",
    "friends_page_title",
    "site_start_date",
    "sponsor_methods_json",
    "sponsor_page_description",
    "sponsor_page_show_comment",
    "sponsor_page_title",
    "sponsor_page_usage",
    "sponsor_show_sponsors_list",
)

_SKIP_DIR_NAMES = {
    "node_modules",
    ".output",
    ".nuxt",
    "dist",
    ".cache",
    "__pycache__",
    "scripts_tmp",
    "docs",
}
_SOURCE_SUFFIXES = {".ts", ".vue", ".json", ".py"}


def _sources(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in root.rglob("*"):
        if path.suffix not in _SOURCE_SUFFIXES or not path.is_file():
            continue
        if _SKIP_DIR_NAMES.intersection(path.relative_to(root).parts[:-1]):
            continue
        out.append(path)
    return out


def _core_text() -> str:
    return (BACKEND / "api" / "core.py").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _isolate_site_config_cache():
    """`/api/config` 有 3600s 跨进程缓存，用例之间必须各读各的。"""
    from backend.core.cache import CacheService, make_cache_key

    async def _purge() -> None:
        await CacheService().delete(make_cache_key("site_config"))

    yield
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_purge())


# ---------------------------------------------------------
# 59 个键不得在任何一段链路上回潮
# ---------------------------------------------------------
def test_the_retired_list_is_the_planned_59_and_covers_both_defect_halves():
    """清单本身要有硬数字：少写一个键＝那个键悄悄回潮也没人报。"""
    assert len(DEAD_KEYS) == 59
    assert len(set(DEAD_KEYS)) == 59
    assert len(STORED_BEFORE) == 17
    assert set(STORED_BEFORE) <= set(DEAD_KEYS)
    assert all(key == key.lower() for key in DEAD_KEYS)


def test_dead_keys_are_gone_from_both_config_models():
    from backend.schemas import SiteConfigResponse, SiteConfigUpdate

    for model, why in (
        (SiteConfigResponse, "又回到 /api/config 的投影里：匿名可读 + CDN 缓存，投出去没人判断"),
        (SiteConfigUpdate, "又被写口收下：没有消费方的键只会让接口假装保存"),
    ):
        for key in DEAD_KEYS:
            assert key not in model.model_fields, f"{key} {why}"


def test_surviving_field_counts_are_the_converged_88_and_77():
    """收敛后的字段数必须是**读侧全字段投影**的口径：再多一个键就是有人偷偷加回扁平项。"""
    from backend.schemas import SiteConfigResponse, SiteConfigUpdate

    resp = set(SiteConfigResponse.model_fields)
    upd = set(SiteConfigUpdate.model_fields)
    assert len(resp) == 88, f"响应字段数漂移：{len(resp)}"
    assert len(upd) == 77, f"写口字段数漂移：{len(upd)}"
    assert not (resp & set(DEAD_KEYS))
    assert not (upd & set(DEAD_KEYS))
    # 反向：活键必须还在（删过头的判据）
    for live in (
        "site_name",
        "about_page_html",
        "enable_comments",
        "comment_allow_guest",
        "enable_bing_wallpaper",
        "enable_guestbook",
        "pagination_page_size",
        "custom_css",
    ):
        assert live in resp, f"{live} 被一起删掉了"


def test_core_py_carries_neither_kwarg_nor_env_form():
    text = _core_text()
    for key in DEAD_KEYS:
        assert f"{key}=" not in text, f"core.py 又把它塞回 dict 关键字参数：{key}="
        assert f'"{key}":' not in text, f"core.py 又把它列进转译表：{key}"
    for env in DEAD_ENVS:
        assert f'"{env}"' not in text, f"core.py 又去读/写环境变量 {env}"
    # 反空转：三个区域都还在，且都带着活键
    for opener, live in (
        ("oobe_kwargs = dict(", "site_name="),
        ("response_dict: dict[str, Any] = dict(", "site_name="),
        ("config_map = {", '"site_name": "SITE_NAME"'),
    ):
        assert opener in text, f"{opener} 整块不见了：断言变成恒真"
        assert live in text, f"{live} 不在core.py 里：区域被删过头"


def test_config_map_drops_the_17_stored_keys():
    """`config_map` 是「写了就落库」的唯一清单。"""
    text = _core_text()
    block = text[text.index("config_map = {") :]
    for key in STORED_BEFORE:
        assert f'"{key}":' not in block, f"{key} 又被 config_map 转译落库"
    # 活键仍在这张表里（删过头的反证）
    for live in ("site_name", "comment_allow_guest", "custom_css", "enable_guestbook"):
        assert f'"{live}":' in block, f"{live} 从转译表消失了"


def test_front_end_has_zero_consumers():
    """键名在 `frontend/` 全量源码零命中＝「接通」这条路根本不存在，删掉不会砸渲染。"""
    key_pat = re.compile(rf"\b({'|'.join(DEAD_KEYS)})\b")
    hits = []
    for path in _sources(FRONTEND):
        if key_pat.search(path.read_text(encoding="utf-8", errors="ignore")):
            hits.append(path.relative_to(REPO).as_posix())
    assert hits == [], f"前端又引用了退役的扁平键：{hits}"


def test_backend_outside_the_models_has_zero_consumers():
    """除了声明处，后端其余文件（含 settings_groups / services）也不许再点它们。"""
    key_pat = re.compile(rf"\b({'|'.join(DEAD_KEYS)})\b")
    hits = []
    for path in _sources(BACKEND):
        if path in (BACKEND / "api" / "core.py", BACKEND / "schemas" / "__init__.py"):
            continue
        if key_pat.search(path.read_text(encoding="utf-8", errors="ignore")):
            hits.append(path.relative_to(REPO).as_posix())
    assert hits == [], f"后端别处又出现退役键（新增读取点的信号）：{hits}"


def test_openapi_drops_all_59():
    body = str(app.openapi()["components"]["schemas"])
    for key in DEAD_KEYS:
        assert key not in body, f"{key} 又回到接口文档了"
    assert "about_page_html" in body, "文档里连活键都不见了＝断言在空转"


# ---------------------------------------------------------
# 写口 / 读口的真实行为
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_legacy_db_rows_do_not_resurrect_the_keys(client):
    """库里躺着退役前的旧行是**存量事实**（生产 PG 就有）：读口必须无视它们，而不是 500。"""
    from backend.core.database import async_session_maker
    from backend.models.core import SiteConfig

    seed_envs = (
        "POST_LIST_DEFAULT_MODE",
        "SPONSOR_PAGE_TITLE",
        "BANGUMI_USER_ID",
        "LICENSE_NAME",
        "ABOUT_CONTENT",
        "FRIENDS_APPLY_HTML",
    )
    seeded: list[int] = []
    async with async_session_maker() as session:
        for env in seed_envs:
            row = (
                await session.execute(select(SiteConfig).where(SiteConfig.key == env))
            ).scalar_one_or_none()
            if row is None:
                row = SiteConfig(key=env, value="whatever", description="")
                session.add(row)
            else:
                row.value = "whatever"
            await session.flush()
            seeded.append(row.id)
        await session.commit()

    try:
        resp = await client.get("/api/config")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        for key in DEAD_KEYS:
            assert key not in body, f"{key} 被存量库行重新投影出来了"
        assert body["site_name"], "读口至少要带回活字段，否则这条断言是恒真的"
    finally:
        async with async_session_maker() as session:
            await session.execute(delete(SiteConfig).where(SiteConfig.id.in_(seeded)))
            await session.commit()


@pytest.mark.asyncio
async def test_write_endpoint_rejects_dead_keys_and_persists_nothing(client, admin_headers):
    """「假装保存」这一半现在必须是**明确拒绝**：422 + 一个字节都不落库。

    退役前它们是 `SiteConfigUpdate` 的声明字段 → 接口回 200 而 `config_map` 从不转译，
    运营者看到的是"保存成功"，库里什么都没有。strict_config 的 `extra="forbid"`
    把这条路彻底堵掉（守卫 tests/test_schema_strict_extra_forbid.py）。
    """
    from backend.core.database import async_session_maker
    from backend.models.core import SiteConfig

    payload = {
        "sponsor_page_title": "合成标题",
        "post_list_default_mode": "grid",
        "license_name": "X",
        "about_content": "合成正文",
        "bangumi_user_id": "1",
    }
    resp = await client.post("/api/admin/settings", headers=admin_headers, json=payload)
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["success"] is False
    fields = {e["field"].split(".")[-1] for e in body["errors"]}
    assert fields == set(payload), f"422 指认的字段与提交的键不一致：{fields}"
    assert all(e["type"] == "extra_forbidden" for e in body["errors"])

    async with async_session_maker() as session:
        rows = (
            await session.execute(
                select(func.count(SiteConfig.id)).where(
                    SiteConfig.key.in_([key.upper() for key in payload])
                )
            )
        ).scalar_one()
    assert rows == 0, "退役键又被写口落库了"

    # 反空转：活键仍然能存，并且真的落库（测完还原，测试库是跨用例共享的同一连接）
    async with async_session_maker() as session:
        original = (
            await session.execute(select(SiteConfig.value).where(SiteConfig.key == "FOOTER_TEXT"))
        ).scalar_one_or_none()

    ok = await client.post(
        "/api/admin/settings", headers=admin_headers, json={"footer_text": "批次 112 校验"}
    )
    assert ok.status_code == 200, ok.text
    async with async_session_maker() as session:
        value = (
            await session.execute(select(SiteConfig.value).where(SiteConfig.key == "FOOTER_TEXT"))
        ).scalar_one_or_none()
    assert value == "批次 112 校验", "写口整体失效，前一条 422 断言就是空转"
    assert (await client.get("/api/config")).json()["footer_text"] == "批次 112 校验"

    async with async_session_maker() as session:
        row = (
            await session.execute(select(SiteConfig).where(SiteConfig.key == "FOOTER_TEXT"))
        ).scalar_one_or_none()
        if row is None and original is not None:
            session.add(SiteConfig(key="FOOTER_TEXT", value=original, description=""))
        elif row is not None:
            row.value = original or ""
        await session.commit()


# ---------------------------------------------------------
# 活功能不得被一起删掉（每族都有一个真在工作的单源）
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_about_page_single_source_is_basic_html(client):
    """`about_content` 死了，`about_page_html` 必须继续是 /about 的唯一内容源。"""
    from backend.api.settings_groups import _default_basic

    basic = _default_basic()
    assert "about_page_html" in basic
    assert "about_content" not in basic, "分组里又长出 about_content＝两份正文来源"
    body = (await client.get("/api/config")).json()
    assert body.get("about_page_html") is not None, "读口不再投影 about_page_html"
    assert "about_content" not in body


@pytest.mark.asyncio
async def test_donate_group_is_the_only_sponsor_source():
    from backend.api.settings_groups import _default_donate

    donate = _default_donate()
    for live in ("enable", "title", "description", "methods", "sponsors", "show_sponsors_list"):
        assert live in donate, f"donate 分组缺少 {live}"
    for dead in ("sponsor_methods_json", "sponsor_page_usage", "sponsor_show_sponsors_list"):
        assert dead not in donate, f"{dead} 又回到 donate 分组"
    text = _core_text()
    assert "list_sponsors" in text and "donate" in text, "/api/sponsors 不再读 donate 分组"


def test_friends_and_activity_titles_come_from_i18n():
    friends = (FRONTEND / "pages" / "friends.vue").read_text(encoding="utf-8")
    activity = (FRONTEND / "pages" / "activity.vue").read_text(encoding="utf-8")
    sponsor = (FRONTEND / "pages" / "sponsor.vue").read_text(encoding="utf-8")
    assert "friends.title" in friends, "友链页标题来源变了，需要更新本批口径"
    assert "activity.title" in activity, "动态页标题来源变了，需要更新本批口径"
    assert "donate.title" in sponsor, "捐助页不再读 donate.title"
    for name, text in (("friends", friends), ("activity", activity), ("sponsor", sponsor)):
        assert f"{name}_page_title" not in text


def test_the_live_page_gates_are_still_enforced():
    """页面开关死的是 `page_*_enabled`，活的是 features / donate 分组那两条。"""
    from backend.api.settings_groups import _default_features

    assert _default_features()["enable_guestbook"] is True
    text = _core_text()
    assert "enable_guestbook=get_bool(" in text, "features.enable_guestbook 不再进公开投影"
    guestbook = (BACKEND / "api" / "guestbook.py").read_text(encoding="utf-8")
    assert "enable_guestbook" in guestbook, "留言板读口不再执行该开关"


def test_the_real_page_size_knob_is_reading_group():
    """`pagination_posts_per_page` 是死的，每页条数的真源是 reading.posts_per_page。"""
    from backend.api.settings_groups import _default_reading
    from backend.schemas import SiteConfigResponse

    assert "posts_per_page" in _default_reading()
    assert "pagination_posts_per_page" not in SiteConfigResponse.model_fields
    assert "pagination_page_size" in SiteConfigResponse.model_fields


def test_post_detail_still_decides_last_modified_by_value():
    """`post_show_last_modified` 死的是开关；「更新于」判定本身必须留在详情页。"""
    text = (FRONTEND / "pages" / "posts" / "[slug].vue").read_text(encoding="utf-8")
    assert "showUpdatedAt" in text
    assert "updated > published" in text, "详情页的更新标记判据消失＝删过头"


def test_coverage_doc_records_the_retirement():
    doc = (FRONTEND / "docs" / "API_COVERAGE.md").read_text(encoding="utf-8")
    blocks = [b for b in doc.split("\n   - ") if "扁平死配置键" in b]
    assert len(blocks) == 1, "文档里这段退役记录丢失或重复：下一个人会照着旧清单重接"
    block = blocks[0]
    assert "59" in block and "不是待接缺口" in block
    for family in ("post_list_", "cover_", "license_", "bangumi_", "sponsor_page_", "page_"):
        assert family in block, f"退役记录没有点名 {family}"
