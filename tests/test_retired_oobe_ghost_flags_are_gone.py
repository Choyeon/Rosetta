"""OOBE 幽灵开关退役后的守卫（批次 #108）。

删掉的是**三项从没实现过的能力声明**，它们共同的形状是「装完就落库、之后没有任何读取方」：

* `enable_pagefind_search` / `enable_music_player`：向导上有开关、`CombinedInstallRequest`
  收键、`.env` 与 SiteConfig 都落了值、`/api/config` 也投影出去，但全仓没有一处判断它们 ——
  既没有 Pagefind 索引构建与搜索面，也没有音乐播放器组件。关掉与打开在站点上看不出区别。
* `enable_pio`（看板娘）：更直接，安装时硬写 `"false"` 进 SiteConfig，唯一提到它的地方是
  那张死字典和这行种子。
* `core/oobe_constants.py` 的 `FEATURE_FLAGS`（十三个 key，含追番/动漫/侧边栏组件/公告栏）
  与 `FEATURE_FLAG_DEFAULTS`：零引用。它们不挡任何漂移，只是让下一个人以为这些能力
  "有清单待接线"，照着清单去接一条后端根本不存在的口子。

真正的能力开关清单是 `settings_groups._default_features()`（每一条都有消费点，
由 `tests/test_settings_group_consumers.py` 逐键钉住），不是向导里的这张表。

另一半断言防的是"把删幽灵做成删功能"：向导里那四把**有消费点**的开关
（评论 / 注册 / RSS / Bing 壁纸）必须仍走完「请求字段 → SiteConfig 种子 → /api/config 投影
→ 前端消费」，`FEATURE_FLAG_DB_KEY_MAP` 也必须留着它唯一的消费者（RSS 的 DB key 改名映射）。
"""

from pathlib import Path

from backend.main import app

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"

GHOST_KEYS = ("enable_pagefind_search", "enable_music_player", "enable_pio")

# 死字典里凭空声明过的能力名（None of them was ever implemented）
GHOST_FLAG_NAMES = (
    "enable_pio",
    "enable_sidebar_widgets",
    "enable_bangumi",
    "enable_anime",
    "enable_announcement",
    "enable_friend_links",
    "enable_gallery",
)

BACKEND_GHOST_FILES = (
    "api/oobe.py",
    "api/core.py",
    "core/oobe_constants.py",
    "core/setup_config.py",
    "schemas/__init__.py",
    "scripts/auto_oobe.py",
)

_SKIP_DIR_NAMES = {
    "node_modules",
    ".output",
    ".nuxt",
    "dist",
    ".cache",
    "__pycache__",
    "scripts_tmp",
}
_FRONTEND_SUFFIXES = {".ts", ".vue", ".json"}


def _frontend_sources() -> list[Path]:
    out: list[Path] = []
    for path in FRONTEND.rglob("*"):
        if path.suffix not in _FRONTEND_SUFFIXES or not path.is_file():
            continue
        if _SKIP_DIR_NAMES.intersection(path.relative_to(FRONTEND).parts[:-1]):
            continue
        out.append(path)
    return out


def _backend_text(rel: str) -> str:
    return (BACKEND / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------
# 幽灵不得回潮
# ---------------------------------------------------------
def test_ghost_flags_are_gone_from_backend_end_to_end():
    from backend.api.oobe import CombinedInstallRequest
    from backend.schemas import SiteConfigResponse

    for key in GHOST_KEYS:
        assert key not in CombinedInstallRequest.model_fields, (
            f"{key} 又被 OOBE 收下了：它写了 .env 与 SiteConfig，但全站没有读取方"
        )
        assert key not in SiteConfigResponse.model_fields, (
            f"{key} 又出现在 /api/config 的投影里：投影出去也没人判断，等于对访客撒谎"
        )
        for rel in BACKEND_GHOST_FILES:
            assert key not in _backend_text(rel), f"backend/{rel} 仍在提 {key}"


def test_ghost_flags_are_gone_from_frontend():
    """前端侧的形态是驼峰（表单/载荷）与 i18n key（fPagefind / fMusic）。"""
    needles = ("enablePagefindSearch", "enableMusicPlayer", "fPagefind", "fMusic", "pagefind")
    hits = [
        path.relative_to(REPO).as_posix()
        for path in _frontend_sources()
        if any(needle in path.read_text(encoding="utf-8", errors="ignore") for needle in needles)
    ]
    assert hits == [], f"前端仍声明这些能力（向导开关、类型或四语文案）：{hits}"


def test_openapi_drops_the_ghost_keys():
    """按生成后的文档核对（AGENTS.md §7.4 第 4 条），不读 app.routes。"""
    schemas = app.openapi()["components"]["schemas"]
    names = {name for name, spec in schemas.items() if GHOST_KEYS[0] in str(spec)}
    assert names == set(), f"OpenAPI 里仍把这些键描述成安装参数/配置字段：{sorted(names)}"
    body = str(schemas)
    for key in GHOST_KEYS:
        assert key not in body, f"{key} 又回到接口文档了"


def test_dead_feature_flag_dicts_are_gone():
    from backend.core import oobe_constants

    for name in ("FEATURE_FLAGS", "FEATURE_FLAG_DEFAULTS"):
        assert not hasattr(oobe_constants, name), (
            f"{name} 回来了：零引用的清单只会让下一个人去接一条后端没有的口子"
        )

    hits = [
        rel
        for rel in ("api/oobe.py", "api/core.py", "api/settings_groups.py", "main.py")
        if "FEATURE_FLAGS" in _backend_text(rel) or "FEATURE_FLAG_DEFAULTS" in _backend_text(rel)
    ]
    assert hits == [], f"这些文件仍引用已删的死字典：{hits}"


def test_ghost_capability_names_are_not_re_seeded():
    """死字典之外，种子清单也不得把这些名字单独写进 SiteConfig。"""
    seed_src = _backend_text("api/oobe.py") + _backend_text("core/setup_config.py")
    for name in GHOST_FLAG_NAMES:
        assert f'"{name}"' not in seed_src and f"'{name}'" not in seed_src, (
            f"{name} 又被种进 SiteConfig：它没有实现，落库只是把假声明存档"
        )


# ---------------------------------------------------------
# 活路径不得被一起删掉
# ---------------------------------------------------------
def test_live_oobe_flags_still_round_trip():
    """四把有真实消费点的开关：请求字段 → 种子 → 投影 三段都必须在。"""
    from backend.api.oobe import CombinedInstallRequest

    fields = CombinedInstallRequest.model_fields
    assert {"enable_comments", "enable_registration", "enable_rss", "enable_bing_wallpaper"} <= set(
        fields
    ), "向导的能力开关被一起删掉了——这四把都有读取方"

    seed_src = _backend_text("api/oobe.py")
    for key, seed_key in (
        ("enable_comments", "enable_comments"),
        ("enable_registration", "enable_registration"),
        ("enable_rss", "enable_rss_feed"),
        ("enable_bing_wallpaper", "enable_bing_wallpaper"),
    ):
        assert f'("{seed_key}",' in seed_src or f"{key}).lower()" in seed_src, (
            f"{key} 的种子行不见了：装完不落库，后台与前台都拿不到这次选择"
        )

    projection_src = _backend_text("api/core.py")
    assert 'enable_bing_wallpaper=get_bool("ENABLE_BING_WALLPAPER", "true")' in projection_src
    assert 'enable_rss=get_bool("ENABLE_RSS_FEED", "true")' in projection_src
    assert 'enable_registration=get_bool("ENABLE_REGISTRATION", "true")' in projection_src


def test_rss_db_key_map_keeps_its_only_consumer():
    from backend.core.oobe_constants import FEATURE_FLAG_DB_KEY_MAP

    assert FEATURE_FLAG_DB_KEY_MAP == {"enable_rss": "enable_rss_feed"}
    assert 'FEATURE_FLAG_DB_KEY_MAP.get("enable_rss"' in _backend_text("api/oobe.py"), (
        "映射不再被使用：RSS 那条 DB 改名要么一起删掉，要么恢复消费点"
    )


def test_bing_wallpaper_switch_still_has_a_front_end_gate():
    """这次删的是无实现开关，有实现的 Bing 壁纸开关不能被同批删掉消费点。"""
    sources = {
        path.name: path.read_text(encoding="utf-8")
        for path in _frontend_sources()
        if path.name in {"login.vue", "register.vue"}
    }
    assert set(sources) == {"login.vue", "register.vue"}
    for name, src in sources.items():
        assert "publicConfig?.enable_bing_wallpaper" in src, f"{name} 不再读这一项"


def test_coverage_doc_records_the_retirement():
    doc = (FRONTEND / "docs" / "API_COVERAGE.md").read_text(encoding="utf-8")
    # 按"这一段"清点，不按单行：文档里的长句是折行的，键名与"退役"两个字往往不在同一行。
    blocks = [b for b in doc.split("\n   - ") if "OOBE 幽灵开关" in b]
    assert len(blocks) == 1, "文档里这段退役记录丢失或重复：下一个人会照着旧清单重接空开关"
    block = blocks[0]
    assert "已退役" in block and "不是待接缺口" in block
    for key in ("enable_pagefind_search", "enable_music_player", "enable_pio"):
        assert key in block, f"退役记录没有点名 {key}"
    assert "FEATURE_FLAGS" in block, "死字典的删除没有记录，清单会被人凭记忆补回来"
