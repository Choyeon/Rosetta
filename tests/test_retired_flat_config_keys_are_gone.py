"""扁平站点配置的最后 59 个零消费方键退役后的守卫（批次 #112）。

批次 #109（第三方评论 26 键）、#110（music/wallpaper/sidebar/sakura/pio 46 键）之后，
`/api/config` 这一族剩下的形状是：**147 个响应字段里只有 88 个真的有人读**。首批删掉其余 59 个（#155 后为 62 个、85 个活字段），
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

**批次 #155 追加的 3 个是第三种形态**（`enable_toc` / `enable_reading_time` / `enable_word_count`）：
  「两个写口、一份真相」的形态：后台「环境变量」面板里那三把开关写的是扁平 UPPERCASE 行，
  `/api/config` 再原样投影回来，而前台目录/阅读时间/字数三处只读 `reading` 分组的
  `show_toc` / `show_reading_time` / `show_word_count`（`useSite.ts` 的 reading 投影）。
  所以拨扁平面那三把＝接口 200、前台纹丝不动。同批退役的还有 `backend/api/toc.py`
  那三个零消费方的公开 POST（`/api/toc/generate`·`/extract`·`/add-ids`）——
  目录锚点的唯一实现是 `frontend/lib/toc.ts`（`tocAnchors.spec.ts` 钉住），
  后端那份的 id 生成规则与它不一致，属同族重复实现。守卫见
  tests/test_retired_toc_api_is_gone.py。

**批次 #156 追加的 19 个是同一族的「只拆了一半」**：`tests/test_settings_group_consumers.py`
的 `_INERT_KEYS` 早就按「能存、能回显，但 read_group / 分组覆写 / 前端消费方三处全空」删掉了
**分组侧**的 `code_theme_dark`、`default_post_cover`、`default_avatar`、`google_analytics_id`、
`baidu_analytics_id`、`session_timeout_sec`、`require_email_verification`、`allow_password_reset`，
而 `/api/config` 的**扁平镜像 + 后台「环境变量」面板那 14 把开关**原封不动留在那里——
分组已经没人写了，扁平那张就成了唯一还挂着的假开关。另三类同判据：
`custom_header_code` / `custom_footer_code` / `custom_css` / `custom_js`（全仓没有任何 head/style/script
注入口；补注入口要放松 CSP，AGENTS §12.6 禁止）、`maintenance_end_time`（`core/maintenance.py`
只判 mode 与 message）、`pagination_max_page_size`（分页上限由代码常量给），
以及 `email_configured` / `email_from` / `email_from_name`——这三条只在投影里出现、`config_map`
从不转译，等于**把发信地址与"邮件是否配好"原样念给匿名访客听**，而真正的发信判据是
`services/email_service.py::resolved_smtp()` 读的 `.env` + `email` 分组。

另一半断言防"把删死键做成删活功能"：i18n 标题、`donate` 分组、`basic.about_page_html`、
`features.enable_guestbook`、`reading.posts_per_page`、详情页的「更新于」判定必须原样活着；
`/api/config` 的字段总数按声明模型收敛（首批 88/77，#155 后 85/74，#156 后 66/58），不再随库里的存量行膨胀。
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
    "allow_password_reset",
    "anime_bilibili_uid",
    "anime_tmdb_api_key",
    "anime_tmdb_list_id",
    "archive_fold_old_articles",
    "baidu_analytics_id",
    "bangumi_api_url",
    "bangumi_category_order_json",
    "bangumi_mode",
    "bangumi_subject_base_url",
    "bangumi_user_id",
    "category_bar_enabled",
    "code_theme_dark",
    "cover_enable_in_post",
    "cover_enable_overlay",
    "cover_random_apis_json",
    "cover_random_enable",
    "cover_show_loading",
    "custom_css",
    "custom_footer_code",
    "custom_header_code",
    "custom_js",
    "default_avatar",
    "default_category_cover",
    "default_post_cover",
    "dynamic_page_description",
    "dynamic_page_items_per_page",
    "dynamic_page_show_comment",
    "dynamic_page_title",
    "email_configured",
    "email_from",
    "email_from_name",
    "enable_reading_time",
    "enable_toc",
    "enable_word_count",
    "friends_apply_html",
    "friends_page_description",
    "friends_page_show_comment",
    "friends_page_show_custom_content",
    "friends_page_title",
    "google_analytics_id",
    "image_opt_formats",
    "image_opt_no_referrer_json",
    "image_opt_quality",
    "license_enable",
    "license_icon",
    "license_name",
    "license_url",
    "login_lockout_duration",
    "maintenance_end_time",
    "mermaid_security_level",
    "mermaid_theme",
    "page_anime_enabled",
    "page_bangumi_enabled",
    "page_dynamic_enabled",
    "page_friends_enabled",
    "page_gallery_enabled",
    "page_guestbook_enabled",
    "page_sponsor_enabled",
    "pagination_max_page_size",
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
    "require_email_verification",
    "session_timeout",
    "site_start_date",
    "sponsor_methods_json",
    "sponsor_page_description",
    "sponsor_page_show_comment",
    "sponsor_page_title",
    "sponsor_page_usage",
    "sponsor_show_sponsors_list",
)

DEAD_ENVS = tuple(key.upper() for key in DEAD_KEYS)

# 这批里 36 个曾在 config_map 里（写了就落库）；其余连转译表都不收
STORED_BEFORE = (
    "about_content",
    "allow_password_reset",
    "baidu_analytics_id",
    "code_theme_dark",
    "custom_css",
    "custom_footer_code",
    "custom_header_code",
    "custom_js",
    "default_avatar",
    "default_category_cover",
    "default_post_cover",
    "dynamic_page_description",
    "dynamic_page_items_per_page",
    "dynamic_page_show_comment",
    "dynamic_page_title",
    "enable_reading_time",
    "enable_toc",
    "enable_word_count",
    "friends_apply_html",
    "friends_page_description",
    "friends_page_show_comment",
    "friends_page_show_custom_content",
    "friends_page_title",
    "google_analytics_id",
    "login_lockout_duration",
    "maintenance_end_time",
    "pagination_max_page_size",
    "require_email_verification",
    "session_timeout",
    "site_start_date",
    "sponsor_methods_json",
    "sponsor_page_description",
    "sponsor_page_show_comment",
    "sponsor_page_title",
    "sponsor_page_usage",
    "sponsor_show_sponsors_list",
)

# ==================== 批次 #157：扁平镜像族（18 键）====================
# 这一族与 DEAD_KEYS 的判据同源但**不能并进 DEAD_KEYS 的全局词边界扫描**：它们的**分组侧同名/近名
# 对象是活的**——`appearance.primary_color`、`comments.require_approval`、`seo.robots_txt`、
# `Comment.author_name`（UGC 昵称列）、主题 mods 的 `primary_color`，以及 `frontend/composables/`
# 里同名的本地变量。全局扫描会在这些活对象上直接红，所以本族按**面**清点：
# 两个配置模型的字段集、`core.py` 的关键字参数 / 转译表 / ENV 串 / 后台面板项、以及这两个模型自己的
# OpenAPI 组件（不是整份 components——seo 分组 schema 里的 robots_txt 是真字段）。
FLAT_MIRROR_KEYS: tuple[str, ...] = (
    "accent_color",
    "author_avatar",
    "author_bio",
    "author_links_json",
    "author_name",
    "baidu_site_verification",
    "code_theme",
    "comment_allow_guest",
    "comment_antispam",
    "comment_max_length",
    "comment_require_approval",
    "default_cover_image",
    "default_theme",
    "font_family",
    "google_site_verification",
    "pagination_page_size",
    "primary_color",
    "robots_txt",
)

FLAT_MIRROR_ENVS = tuple(key.upper() for key in FLAT_MIRROR_KEYS)

# 16 个曾在 config_map 里（拨动即落一行无人读取的 UPPERCASE）；accent_color / default_cover_image
# 只投影不转译，pagination_page_size 之外的三条作者键与封面键走的是 OOBE 那条种子链。
MIRROR_STORED_BEFORE = (
    "author_avatar",
    "author_bio",
    "author_links_json",
    "author_name",
    "baidu_site_verification",
    "code_theme",
    "comment_allow_guest",
    "comment_antispam",
    "comment_max_length",
    "comment_require_approval",
    "default_theme",
    "font_family",
    "google_site_verification",
    "pagination_page_size",
    "primary_color",
    "robots_txt",
)

# 15 个曾挂在后台「环境变量」面板（`GET /config/full` 的 SiteSettingItem）上。
MIRROR_IN_ENV_PANEL = (
    "author_avatar",
    "author_bio",
    "author_links_json",
    "author_name",
    "baidu_site_verification",
    "code_theme",
    "comment_allow_guest",
    "comment_antispam",
    "comment_max_length",
    "comment_require_approval",
    "default_theme",
    "font_family",
    "google_site_verification",
    "primary_color",
    "robots_txt",
)

# 5 个曾被 OOBE 写口/装种链路带上（请求模型字段 + site_configs 行 + .env 行）。
MIRROR_OOBE_SEEDED = (
    "author_avatar",
    "author_bio",
    "author_links_json",
    "author_name",
    "default_cover_image",
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
# 81 个键不得在任何一段链路上回潮
# ---------------------------------------------------------
def test_the_retired_list_is_the_planned_81_and_covers_both_defect_halves():
    """清单本身要有硬数字：少写一个键＝那个键悄悄回潮也没人报。"""
    assert len(DEAD_KEYS) == 81
    assert len(set(DEAD_KEYS)) == 81
    assert len(STORED_BEFORE) == 36
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


def test_surviving_field_counts_are_the_converged_48_and_45():
    """收敛后的字段数必须是**读侧全字段投影**的口径：再多一个键就是有人偷偷加回扁平项。"""
    from backend.schemas import SiteConfigResponse, SiteConfigUpdate

    resp = set(SiteConfigResponse.model_fields)
    upd = set(SiteConfigUpdate.model_fields)
    assert len(resp) == 48, f"响应字段数漂移：{len(resp)}"
    assert len(upd) == 45, f"写口字段数漂移：{len(upd)}"
    assert not (resp & set(DEAD_KEYS))
    assert not (upd & set(DEAD_KEYS))
    assert not (resp & set(FLAT_MIRROR_KEYS))
    assert not (upd & set(FLAT_MIRROR_KEYS))
    # 反向：活键必须还在（删过头的判据）
    for live in (
        "site_name",
        "about_page_html",
        "enable_comments",
        "enable_bing_wallpaper",
        "enable_guestbook",
        "footer_text",
        # 批次 #157 保留下来的是「扁平名与分组键同名」的那批真镜像
        "theme_primary",
        "theme_accent",
        "default_og_image",
        "max_upload_size",
        "allowed_image_types",
        "site_url",
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


def test_config_map_drops_the_stored_keys():
    """`config_map` 是「写了就落库」的唯一清单。"""
    text = _core_text()
    block = text[text.index("config_map = {") :]
    for key in STORED_BEFORE:
        assert f'"{key}":' not in block, f"{key} 又被 config_map 转译落库"
    # 活键仍在这张表里（删过头的反证）
    for live in ("site_name", "site_url", "footer_text", "enable_guestbook", "max_upload_size"):
        assert f'"{live}":' in block, f"{live} 从转译表消失了"


def test_front_end_has_zero_consumers():
    """键名在 `frontend/` 全量源码零命中＝「接通」这条路根本不存在，删掉不会砸渲染。"""
    key_pat = re.compile(rf"\b({'|'.join(DEAD_KEYS)})\b")
    hits = []
    for path in _sources(FRONTEND):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix == ".py":
            # 整行注释是退役台账，不是读取点：settings_groups.py 里「某某键已删除」的
            # 说明必须留着，否则下一个人不知道该不该把它接回来。代码行照旧严格。
            text = "\n".join(
                line for line in text.splitlines() if not line.lstrip().startswith("#")
            )
        if key_pat.search(text):
            hits.append(path.relative_to(REPO).as_posix())
    assert hits == [], f"前端又引用了退役的扁平键：{hits}"


def test_backend_outside_the_models_has_zero_consumers():
    """除了声明处，后端其余文件（含 settings_groups / services）也不许再点它们。"""
    key_pat = re.compile(rf"\b({'|'.join(DEAD_KEYS)})\b")
    hits = []
    for path in _sources(BACKEND):
        if path in (BACKEND / "api" / "core.py", BACKEND / "schemas" / "__init__.py"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix == ".py":
            # 整行注释是退役台账，不是读取点：settings_groups.py 里「某某键已删除」的
            # 说明必须留着，否则下一个人不知道该不该把它接回来。代码行照旧严格。
            text = "\n".join(
                line for line in text.splitlines() if not line.lstrip().startswith("#")
            )
        if key_pat.search(text):
            hits.append(path.relative_to(REPO).as_posix())
    assert hits == [], f"后端别处又出现退役键（新增读取点的信号）：{hits}"


def test_openapi_drops_all_retired_keys():
    body = str(app.openapi()["components"]["schemas"])
    for key in DEAD_KEYS:
        assert key not in body, f"{key} 又回到接口文档了"
    assert "about_page_html" in body, "文档里连活键都不见了＝断言在空转"


def test_static_api_docs_do_not_re_describe_the_retired_keys():
    """`backend/docs/` 是第四个面：手抄的字段清单会在键退役后继续教运营者去拨一个不存在的开关。

    `api_endpoints.md` 与 `types.ts` 由脚本从运行时 spec 生成（改接口要重跑 `--write`），
    `api_reference.md` 是手写的——它此前既列过退役键，也漏过新增键，两个方向都没人管。
    """
    docs = sorted((BACKEND / "docs").glob("*.md")) + [BACKEND / "docs" / "types.ts"]
    assert docs, "backend/docs 扫不到文件＝断言在空转"
    for path in docs:
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = [key for key in DEAD_KEYS if re.search(rf"\b{key}\b", text)]
        assert not hits, f"{path.name} 仍在描述退役键：{hits}"


def test_reference_doc_config_example_matches_the_live_response_model():
    """`api_reference.md` 里那份 `/api/config` 响应示例必须与 `SiteConfigResponse` 字段集合相等。

    手抄一份字段清单本身是漂移源：少抄＝新键不上文档，多抄＝退役键还在教人拨。把它钉成
    集合相等，下一次退役/新增时按 `SiteConfigResponse.model_fields` 重写那个代码块就是一条 diff。
    """
    import json

    from backend.schemas import SiteConfigResponse

    text = (BACKEND / "docs" / "api_reference.md").read_text(encoding="utf-8")
    anchor = text.index("GET /api/config\n")
    match = re.search(r"```json\n(\{.*?\n\})\n```", text[anchor:], re.S)
    assert match, "api_reference.md 里找不到 /api/config 的响应示例"
    example = json.loads(match.group(1))
    live = set(SiteConfigResponse.model_fields)
    assert set(example) == live, (
        f"文档示例与模型字段不再相等：文档多 {sorted(set(example) - live)}、"
        f"缺 {sorted(live - set(example))}"
    )


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
        "ENABLE_TOC",
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
    """`pagination_posts_per_page` 与 `pagination_page_size` 都是死的，每页条数真源是 reading.posts_per_page。"""
    from backend.api.settings_groups import _default_reading
    from backend.schemas import SiteConfigResponse

    assert "posts_per_page" in _default_reading()
    assert "pagination_posts_per_page" not in SiteConfigResponse.model_fields
    # 批次 #157：扁平镜像 pagination_page_size 退役（前台四处分页读 site.reading.value.posts_per_page）
    assert "pagination_page_size" not in SiteConfigResponse.model_fields


def test_the_toc_and_reading_switches_have_exactly_one_live_source():
    """批次 #155：enable_toc / enable_reading_time / enable_word_count 是扁平镜像，
    真源是 reading 分组的 show_* —— 退役镜像时活的那一半必须一个不少。

    两个写口对着同一个开关（后台「环境变量」里的 ENABLE_TOC 与站点设置 reading 分组），
    运营者拨哪一个都回 200，但前台只读 reading 那一份：扁平面是第二份假真相。
    """
    from backend.api.settings_groups import _default_reading

    reading = _default_reading()
    for live in ("show_reading_time", "show_word_count", "show_toc", "toc_depth"):
        assert live in reading, f"reading 分组缺少 {live}：镜像退役时把活开关一起删了"
    assert "enable_toc" not in reading, "reading 分组里长出扁平键＝两份来源又开始了"

    site = (FRONTEND / "composables" / "useSite.ts").read_text(encoding="utf-8")
    for live in ("show_reading_time", "show_word_count", "show_toc", "toc_depth"):
        assert live in site, f"useSite 不再投影 reading.{live}"

    detail = (FRONTEND / "pages" / "posts" / "[slug].vue").read_text(encoding="utf-8")
    assert "showToc" in detail, "详情页的目录开关判据消失＝删过头"


def test_post_detail_still_decides_last_modified_by_value():
    """`post_show_last_modified` 死的是开关；「更新于」判定本身必须留在详情页。"""
    text = (FRONTEND / "pages" / "posts" / "[slug].vue").read_text(encoding="utf-8")
    assert "showUpdatedAt" in text
    assert "updated > published" in text, "详情页的更新标记判据消失＝删过头"


def test_types_ts_does_not_declare_the_retired_mirrors():
    """`backend/docs/types.ts` 手抄的两个配置接口不得再声明这批镜像键。

    只按**成员名**核对，不做全文扫描：`robots_txt` / `primary_color` 是 seo、appearance 分组的
    真字段名，全文扫会把分组的说明一起判红；而台账注释（整行 `//`）必须留着。
    """
    text = (BACKEND / "docs" / "types.ts").read_text(encoding="utf-8")
    for iface in ("SiteConfig", "SiteConfigUpdate"):
        block = text[text.index(f"export interface {iface} {{") :]
        block = block[: block.index("\n}")]
        members = set(re.findall(r"^\s{2}([a-z_]+)\??\s*:", block, re.M))
        assert members, f"types.ts 的 {iface} 解析不到成员＝断言在空转"
        for key in FLAT_MIRROR_KEYS:
            assert key not in members, f"{key} 又回到 types.ts 的 {iface} 声明里"
        assert "site_name" in members and "enable_comments" in members, (
            f"{iface} 的活键也不见了＝解析跑偏"
        )


def test_coverage_doc_records_the_retirement():
    doc = (FRONTEND / "docs" / "API_COVERAGE.md").read_text(encoding="utf-8")
    blocks = [b for b in doc.split("\n   - ") if "扁平死配置键" in b]
    assert len(blocks) == 1, "文档里这段退役记录丢失或重复：下一个人会照着旧清单重接"
    block = blocks[0]
    assert "59" in block and "不是待接缺口" in block
    for family in ("post_list_", "cover_", "license_", "bangumi_", "sponsor_page_", "page_"):
        assert family in block, f"退役记录没有点名 {family}"


# ---------------------------------------------------------
# 批次 #157：扁平镜像族按面清点
# ---------------------------------------------------------
def test_the_flat_mirror_list_is_the_planned_18_and_has_its_ledgers():
    """三份台账（转译表 / 后台面板 / OOBE 种子）都必须落在 18 键之内——
    台账就是「这个键退役前挂在哪个面上」的证据，超出清单＝有人新加了一把没人读的开关。"""
    assert len(FLAT_MIRROR_KEYS) == 18
    assert len(set(FLAT_MIRROR_KEYS)) == 18
    assert all(key == key.lower() for key in FLAT_MIRROR_KEYS)
    assert not (set(FLAT_MIRROR_KEYS) & set(DEAD_KEYS)), (
        "同一键进两份台账＝下一个人不知道以哪份为准"
    )
    for ledger, count in (
        (MIRROR_STORED_BEFORE, 16),
        (MIRROR_IN_ENV_PANEL, 15),
        (MIRROR_OOBE_SEEDED, 5),
    ):
        assert len(ledger) == count, f"台账 {ledger[:1]}… 条目数漂移"
        assert set(ledger) <= set(FLAT_MIRROR_KEYS)


def test_flat_mirrors_are_gone_from_both_config_models():
    from backend.schemas import SiteConfigResponse, SiteConfigUpdate

    resp, upd = SiteConfigResponse.model_fields, SiteConfigUpdate.model_fields
    for key in FLAT_MIRROR_KEYS:
        assert key not in resp, f"{key} 又回到 /api/config 的投影里"
        assert key not in upd, f"{key} 又被写口收下"


def test_core_py_drops_every_flat_mirror_surface():
    """四面：投影关键字参数、config_map 转译、ENV 读取/面板键。

    `primary_color` / `accent_color` 在 core.py 里**仍然出现**，那是 appearance 分组的
    分组键（`parsed.get("primary_color")` → 投影成 `theme_primary`），属于活路径；
    所以本族只按形态清点，不做词边界全扫。
    """
    text = _core_text()
    block = text[text.index("config_map = {") :]
    for key in FLAT_MIRROR_KEYS:
        assert f"{key}=" not in text, f"core.py 又把它塞回投影关键字参数：{key}="
        assert f'"{key}":' not in block, f"core.py 又把它列进转译表：{key}"
    for env in FLAT_MIRROR_ENVS:
        assert f'"{env}"' not in text, (
            f"core.py 又去读/写环境变量 {env}（含后台面板 SiteSettingItem）"
        )
    # 反空转：appearance 分组仍在投影 theme_primary，否则上面三条对 primary_color 恒真
    assert 'cfg_base["theme_primary"] = str(parsed["primary_color"])' in text
    assert 'cfg_base["theme_accent"] = str(parsed["accent_color"])' in text


def test_the_three_env_panel_groups_are_retired_wholesale():
    """后台「环境变量」面板的 appearance / seo / comment 三组整组退役：
    它们挂的 11 条键全是零读取点镜像，留着就是给运营者第二张假写面。"""
    text = _core_text()
    for name in ("appearance", "seo", "comment"):
        assert f'name="{name}",' not in text, (
            f"/config/full 又长出 {name} 分组：与 PATCH 分组同名冲突"
        )
    # 活分组仍在（删过头的反证）
    for live in ("basic", "footer", "security", "maintenance", "upload", "social", "features"):
        assert f'name="{live}"' in text, f"/config/full 的 {live} 分组消失＝面板整体被误删"


def test_flat_mirrors_leave_the_two_model_schemas_in_openapi():
    """按**这两个模型的组件**核对，不按整份 components：
    seo 分组的 schema 里 `robots_txt` 是真字段，全局扫会假红。"""
    schemas = app.openapi()["components"]["schemas"]
    for model in ("SiteConfigResponse", "SiteConfigUpdate"):
        props = set(schemas[model]["properties"])
        for key in FLAT_MIRROR_KEYS:
            assert key not in props, f"{key} 又出现在 {model} 的接口文档里"
        assert "theme_primary" in props, f"{model} 的活键也不见了＝断言在空转"


@pytest.mark.asyncio
async def test_legacy_flat_rows_are_ignored_by_the_read_surface(client):
    """存量库里这些 UPPERCASE 行还在（生产 PG 就有）：读口必须无视，而不是 500 也不是回吐。"""
    from backend.core.database import async_session_maker
    from backend.models.core import SiteConfig

    seed_envs = (
        "PAGINATION_PAGE_SIZE",
        "PRIMARY_COLOR",
        "CODE_THEME",
        "ROBOTS_TXT",
        "GOOGLE_SITE_VERIFICATION",
        "COMMENT_MAX_LENGTH",
        "AUTHOR_BIO",
        "DEFAULT_COVER_IMAGE",
    )
    seeded: list[int] = []
    async with async_session_maker() as session:
        for env in seed_envs:
            row = (
                await session.execute(select(SiteConfig).where(SiteConfig.key == env))
            ).scalar_one_or_none()
            if row is None:
                row = SiteConfig(key=env, value="stale-157", description="")
                session.add(row)
            else:
                row.value = "stale-157"
            await session.flush()
            seeded.append(row.id)
        await session.commit()
    try:
        from backend.core.cache import invalidate_cache

        await invalidate_cache("site_config")
        resp = await client.get("/api/config")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        for key in FLAT_MIRROR_KEYS:
            assert key not in body, f"{key} 被存量库行重新投影出来了"
        # 活的那一半必须还活着：分组仍然是唯一真源
        assert "site_name" in body, "读口连活键都不返回＝这条断言在空转"
    finally:
        async with async_session_maker() as session:
            await session.execute(delete(SiteConfig).where(SiteConfig.id.in_(seeded)))
            await session.commit()
        from backend.core.cache import invalidate_cache

        await invalidate_cache("site_config")


@pytest.mark.asyncio
async def test_the_write_surface_rejects_retired_mirrors(client, admin_headers):
    """退役前 `POST /api/admin/settings` 收下这些键并落一行没人读的 UPPERCASE；
    现在必须明确 422，而不是继续回 200。"""
    from backend.core.database import async_session_maker
    from backend.models.core import SiteConfig

    payload = {
        "pagination_page_size": 20,
        "primary_color": "#111111",
        "comment_max_length": 500,
        "robots_txt": "User-agent: *\nDisallow: /",
        "author_bio": "合成签名",
    }
    resp = await client.post("/api/admin/settings", headers=admin_headers, json=payload)
    assert resp.status_code == 422, resp.text
    fields = {e["field"].split(".")[-1] for e in resp.json()["errors"]}
    assert fields == set(payload)

    async with async_session_maker() as session:
        rows = (
            await session.execute(
                select(func.count(SiteConfig.id)).where(
                    SiteConfig.key.in_([key.upper() for key in payload])
                )
            )
        ).scalar_one()
    assert rows == 0, "退役镜像又被写口落库了"


# ---------------------------------------------------------
# 五族的真源必须一个不少（删镜像 ≠ 删功能）
# ---------------------------------------------------------
def test_pagination_true_source_is_the_reading_group():
    from backend.api.settings_groups import _default_reading

    assert _default_reading()["posts_per_page"]
    site = (FRONTEND / "composables" / "useSite.ts").read_text(encoding="utf-8")
    assert "posts_per_page" in site, "useSite 不再投影 reading.posts_per_page"
    listing = (FRONTEND / "pages" / "posts" / "index.vue").read_text(encoding="utf-8")
    assert "posts_per_page" in listing, "列表页不再按 reading 分组取每页条数"


def test_appearance_true_source_is_the_group_plus_theme_mods():
    from backend.api.settings_groups import _default_appearance

    appearance = _default_appearance()
    for live in ("primary_color", "accent_color", "page_width_px"):
        assert live in appearance, f"appearance 分组缺少 {live}"
    theme = (FRONTEND / "composables" / "useFrontendTheme.ts").read_text(encoding="utf-8")
    assert "primary_color" in theme, "主题 mods 的主色消费点消失＝删过头"
    assert "--hljs" in (FRONTEND / "assets" / "css" / "main.css").read_text(encoding="utf-8"), (
        "代码配色令牌不在了：code_theme 退役的前提（配色归 --hljs-* 令牌）失效"
    )


def test_seo_true_source_is_the_seo_group():
    from backend.api.settings_groups import _default_seo

    seo = _default_seo()
    for live in ("robots_txt", "google_verification", "baidu_verification", "default_og_image"):
        assert live in seo, f"seo 分组缺少 {live}"
    seo_api = (BACKEND / "api" / "seo.py").read_text(encoding="utf-8")
    assert "robots_txt" in seo_api, "robots 正文不再读 seo 分组"
    use_seo = (FRONTEND / "composables" / "useSeo.ts").read_text(encoding="utf-8")
    assert "google_verification" in use_seo and "baidu_site_verification" not in use_seo, (
        "验证码消费点口径变了：真源应是 seo.google_verification"
    )


def test_comments_true_source_is_the_comments_group():
    from backend.api.settings_groups import _default_comments

    comments = _default_comments()
    for live in ("enable", "require_approval", "allow_guest", "max_length", "enable_antispam"):
        assert live in comments, f"comments 分组缺少 {live}"
    text = _core_text()
    assert 'cfg_base["enable_comments"] = bool(parsed["enable"])' in text
    service = (BACKEND / "services" / "comment_service.py").read_text(encoding="utf-8")
    assert "require_approval" in service and "allow_guest" in service, "执行点不再读 comments 分组"


def test_author_true_source_is_the_user_row_plus_site_author():
    """author_* 四键死的是配置面；作者资料本身仍有两个真源，别把它们一起删了。"""
    from backend.schemas import SiteConfigResponse

    assert "site_author" in SiteConfigResponse.model_fields
    rows = (FRONTEND / "pages" / "about.vue").read_text(encoding="utf-8")
    assert "site_author" in rows, "关于页不再读 site_author"
    oobe = (BACKEND / "api" / "oobe.py").read_text(encoding="utf-8")
    assert "nickname=req.admin_nickname" in oobe, "OOBE 不再把昵称写进管理员 User 行"
