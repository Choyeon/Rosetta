"""第三方评论 provider 配置族退役后的守卫（批次 #109）。

删掉的是 26 个"看起来能切换评论系统"的键：`comment_system_type` 五家 provider（各家
自己的 env_id / server_url / repo / shortname / lang / js_url / emoji_json / 各类开关）。
它们的形状比"写口收键、读口不回吐"更坏一档——**三段全断**：

* 前端一个 provider 渲染器都没有（`twikoo` / `waline` / `artalk` / `giscus` / `disqus`
  这些串在 `frontend/` 的源码与四语文案里零命中），所以 `comment_system_type` 翻成任何值，
  评论区渲染的都是同一套站内组件；
* `PUT /api/config` 的 `config_map` 从不收这些键，处理器 `if not key: continue` 直接丢弃
  ——写口在 `SiteConfigUpdate` 里声明了它们，接口回 200，库里一行不增，等于假装保存；
* 读口 `get_str("COMMENT_TWIKOO_ENV_ID")` 只能回默认值，`/api/config` 却把它们投影给访客，
  而 `api/config` 是公开缓存口。

本站评论的真实口径是 `settings_groups._default_comments()`（唯一开关 `enable`，执行点
`CommentService.create_comment` 的 COMMENTS_DISABLED 闸门）+ `/api/comments` 一族 +
`SiteConfigResponse.enable_comments` 投影。这些必须原样活着——另一半断言防的就是
"把删幽灵做成删评论"。
"""

from pathlib import Path

from backend.main import app

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"

PROVIDER_NAMES = ("twikoo", "waline", "artalk", "giscus", "disqus")

GHOST_KEYS = (
    "comment_system_type",
    "comment_twikoo_env_id",
    "comment_twikoo_lang",
    "comment_twikoo_visitor_count",
    "comment_twikoo_js_url",
    "comment_twikoo_css_url",
    "comment_waline_server_url",
    "comment_waline_lang",
    "comment_waline_emoji_json",
    "comment_waline_login_mode",
    "comment_waline_visitor_count",
    "comment_artalk_server",
    "comment_artalk_locale",
    "comment_artalk_visitor_count",
    "comment_giscus_repo",
    "comment_giscus_repo_id",
    "comment_giscus_category",
    "comment_giscus_category_id",
    "comment_giscus_mapping",
    "comment_giscus_strict",
    "comment_giscus_reactions_enabled",
    "comment_giscus_emit_metadata",
    "comment_giscus_input_position",
    "comment_giscus_lang",
    "comment_giscus_loading",
    "comment_disqus_shortname",
)

GHOST_ENV_NAMES = tuple(key.upper() for key in GHOST_KEYS)

BACKEND_GHOST_FILES = (
    "api/core.py",
    "schemas/__init__.py",
    "api/settings_groups.py",
    "api/oobe.py",
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
    """源码面（不含 docs/：退役记录本身要点名这些 provider，那是给人读的账，不是能力声明）。"""
    out: list[Path] = []
    for path in root.rglob("*"):
        if path.suffix not in _SOURCE_SUFFIXES or not path.is_file():
            continue
        if _SKIP_DIR_NAMES.intersection(path.relative_to(root).parts[:-1]):
            continue
        out.append(path)
    return out


def _backend_text(rel: str) -> str:
    return (BACKEND / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------
# 假配置族不得回潮
# ---------------------------------------------------------
def test_ghost_keys_are_gone_from_request_and_response_models():
    from backend.schemas import SiteConfigResponse, SiteConfigUpdate

    for model, why in (
        (SiteConfigResponse, "又出现在 /api/config 的投影里：投影出去也没人判断，等于对访客撒谎"),
        (SiteConfigUpdate, "又被写口收下：config_map 不转译它，接口回 200 而库里一行不增"),
    ):
        for key in GHOST_KEYS:
            assert key not in model.model_fields, f"{key} {why}"


def test_ghost_keys_are_gone_from_backend_sources():
    for rel in BACKEND_GHOST_FILES:
        text = _backend_text(rel)
        for key in GHOST_KEYS:
            assert key not in text, f"backend/{rel} 仍在提 {key}"
        for name in PROVIDER_NAMES:
            assert name not in text.lower(), f"backend/{rel} 又出现了 {name} 的配置面"


def test_ghost_env_names_are_not_projected():
    """投影口按 ENV 名取值，ENV 名回来就是键回来的另一种形态。"""
    text = _backend_text("api/core.py")
    for env in GHOST_ENV_NAMES:
        assert f'"{env}"' not in text, f"{env} 又被读进 /api/config"
    assert '"COMMENT_SYSTEM_TYPE"' not in text


def test_ghost_providers_have_no_front_end_renderer():
    """这族当初就该删的理由：前端从没渲染过任何一个 provider，翻开关看不出区别。"""
    hits = [
        path.relative_to(REPO).as_posix()
        for path in _sources(FRONTEND)
        if any(
            name in path.read_text(encoding="utf-8", errors="ignore").lower()
            for name in PROVIDER_NAMES
        )
    ]
    assert hits == [], f"前端出现 provider 引用——要么恢复整族，要么这就是新的一套假开关：{hits}"


def test_openapi_drops_the_ghost_family():
    """按生成后的文档核对（AGENTS.md §7.4 第 4 条），不读 app.routes。"""
    body = str(app.openapi()["components"]["schemas"])
    for key in GHOST_KEYS:
        assert key not in body, f"{key} 又回到接口文档了"


def test_no_setting_group_declares_a_provider_switch():
    """分组默认值也不得另起一套 provider 选择：评论只有站内这一套系统。"""
    from backend.api.settings_groups import _default_comments

    assert not any("system_type" in k or "provider" in k for k in _default_comments())


# ---------------------------------------------------------
# 活评论系统不得被一起删掉
# ---------------------------------------------------------
def test_live_comments_group_is_intact():
    from backend.api.settings_groups import _default_comments

    assert {
        "enable",
        "require_approval",
        "allow_guest",
        "max_length",
        "enable_antispam",
        "enable_nested",
    } == set(_default_comments()), "评论分组被改动了：这一组才是评论系统的真源"


def test_live_comment_config_keys_still_round_trip():
    """PUT /api/config 里那四条**有转译**的旧评论键必须原样可用。"""
    from backend.schemas import SiteConfigResponse, SiteConfigUpdate

    text = _backend_text("api/core.py")
    for field, env in (
        ("comment_require_approval", "COMMENT_REQUIRE_APPROVAL"),
        ("comment_allow_guest", "COMMENT_ALLOW_GUEST"),
        ("comment_max_length", "COMMENT_MAX_LENGTH"),
        ("comment_antispam", "COMMENT_ANTISPAM"),
    ):
        assert f'"{field}": "{env}"' in text, f"config_map 丢了 {field}：后台保存不再落库"
        assert field in SiteConfigUpdate.model_fields, f"{field} 不再是写口字段"
        assert field in SiteConfigResponse.model_fields, f"{field} 不再被投影"


def test_flat_enable_comments_is_still_projected_from_the_group():
    """enable_comments 是 comments.enable 的镜像（不是幽灵），投影必须留着。"""
    from backend.schemas import SiteConfigResponse

    assert "enable_comments" in SiteConfigResponse.model_fields
    text = _backend_text("api/core.py")
    assert 'cfg_base["enable_comments"] = bool(parsed["enable"])' in text, (
        "分组 → 扁平的镜像不见了：前台评论区判据与后台开关脱钩"
    )


def test_comment_api_router_is_still_mounted():
    """评论系统的真实入口：文章维度读写口 + 按 ID 的删除/回复/举报口。"""
    paths = app.openapi()["paths"]
    for path in (
        "/api/posts/{post_id_or_slug}/comments",
        "/api/comments/{comment_id}",
        "/api/comments/{comment_id}/report",
    ):
        assert path in paths, f"{path} 不见了：删幽灵把站内评论系统一起删掉了"
    assert "post" in paths["/api/posts/{post_id_or_slug}/comments"], "匿名提交评论的写口不见了"


def test_coverage_doc_records_the_retirement():
    doc = (FRONTEND / "docs" / "API_COVERAGE.md").read_text(encoding="utf-8")
    # 按"这一段"清点，不按单行：文档里的长句是折行的。
    blocks = [b for b in doc.split("\n   - ") if "第三方评论假配置族" in b]
    assert len(blocks) == 1, "文档里这段退役记录丢失或重复：下一个人会照着旧清单重接 provider"
    block = blocks[0]
    assert "已退役" in block and "不是待接缺口" in block
    for name in PROVIDER_NAMES:
        assert name in block, f"退役记录没有点名 {name}"
    assert "config_map" in block, "没写「为什么写了也不落库」，容易被当成接线漏了一半"
