"""扁平死配置族退役后的守卫（批次 #110）。

删掉的是五族、46 个键：音乐播放器（`music_*` 11）、壁纸/Banner 旧体系（`wallpaper_*` 10）、
侧边栏小工具（`sidebar_show_*` / `sidebar_widget_order` 11）、樱花特效（`sakura_*` 7）、
Live2D 看板娘（`pio_spine_*` 7）。它们的共同形状是**整条链路只有声明，没有实现**：

* 前台没有任何渲染器读它们——`frontend/` 全量源码里这些键零命中，也没有 APlayer / MetingJS
  / 花瓣 canvas / Spine 运行时的一行代码；
* 后台真正的设置口 `/api/settings`（`settings_groups.py`）里**没有**这五组，sidebar 分组早已
  删掉（侧边栏显隐与位置归主题 Customizer 的 mods，导航的 header/footer/sidebar 归
  `navigation` 表），所以运营者连"把它打开"的按钮都找不到；
* 唯一还提它们的地方是 `/api/config/full` 里的两组死开关声明，而那个端点自身零消费方。

`music_*` / `wallpaper_*` / `sidebar_*` 还额外满足"存得进、没人读"：它们在 `PUT /api/config`
的 `config_map` 里，写了会落库，`/api/config` 又原样投影给访客与 SSR——一整条链都在认真搬运
一个不存在的功能。`sakura_*` / `pio_spine_*` 更糟一档：连 `config_map` 都不收，写了就丢。

另一半断言防"把删死键做成删活功能"：Bing 每日壁纸（`enable_bing_wallpaper` +
`services/site_settings.bing_wallpaper_enabled` + `/wallpapers` 归档页）、首页轮播（hero 一族）、
站内评论与导航的 `sidebar` 位置必须原样活着。
"""

import re
from pathlib import Path

import pytest
from sqlalchemy import delete, select

from backend.main import app

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"

DEAD_KEYS: tuple[str, ...] = (
    # 音乐播放器
    "music_enabled",
    "music_show_in_navbar",
    "music_show_in_sidebar",
    "music_mode",
    "music_volume",
    "music_play_mode",
    "music_show_lyrics",
    "music_meting_api",
    "music_meting_server",
    "music_meting_type",
    "music_meting_id",
    # 壁纸/Banner 旧体系（与 Bing 壁纸无关）
    "wallpaper_mode",
    "wallpaper_player_enable",
    "wallpaper_desktop",
    "wallpaper_mobile",
    "wallpaper_video",
    "wallpaper_use_bing",
    "wallpaper_bing_days",
    "wallpaper_dim_opacity",
    "wallpaper_home_title",
    "wallpaper_home_subtitle",
    # 侧边栏小工具
    "sidebar_show_profile",
    "sidebar_show_categories",
    "sidebar_show_tags",
    "sidebar_show_recent_posts",
    "sidebar_show_recent_comments",
    "sidebar_show_tag_cloud",
    "sidebar_show_site_info",
    "sidebar_show_music",
    "sidebar_show_statistics",
    "sidebar_show_dynamics",
    "sidebar_widget_order",
    # 樱花特效
    "sakura_enable",
    "sakura_count",
    "sakura_min_scale",
    "sakura_max_scale",
    "sakura_min_opacity",
    "sakura_max_opacity",
    "sakura_z_index",
    # Live2D / Spine 看板娘
    "pio_spine_enable",
    "pio_spine_model_path",
    "pio_spine_scale",
    "pio_spine_position_corner",
    "pio_spine_width",
    "pio_spine_height",
    "pio_spine_z_index",
)

DEAD_ENVS = tuple(key.upper() for key in DEAD_KEYS)

# 前端若要"真的实现"这几族，必然出现的运行时名字；零命中即"没有实现"的证据
FRONTEND_RUNTIME_TOKENS = ("aplayer", "metingjs", "meting-api", "spine-", "sakura-canvas")

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


def _backend_text(rel: str) -> str:
    return (BACKEND / rel).read_text(encoding="utf-8")


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
# 死族不得回潮
# ---------------------------------------------------------
def test_dead_keys_are_gone_from_both_config_models():
    from backend.schemas import SiteConfigResponse, SiteConfigUpdate

    for model, why in (
        (SiteConfigResponse, "又回到 /api/config 的投影里：投出去也没人判断"),
        (SiteConfigUpdate, "又被写口收下：没有消费方的键落库只是攒脏数据"),
    ):
        for key in DEAD_KEYS:
            assert key not in model.model_fields, f"{key} {why}"


def test_dead_env_names_are_not_read_or_written_anywhere_in_core():
    text = _backend_text("api/core.py")
    for env in DEAD_ENVS:
        assert f'"{env}"' not in text, f"core.py 又去读/写 {env}"
    for marker in ("_sidebar_dict_to_flat", "default_sidebar", "parsed_sb"):
        assert marker not in text, f"core.py 还留着侧边栏打平机制的 {marker}"


def test_config_map_does_not_persist_the_dead_families():
    """`config_map` 是"写了就落库"的清单；这几族再进去就等于恢复一条无人消费的数据流。"""
    text = _backend_text("api/core.py")
    block = text[text.index("config_map") :]
    for key in DEAD_KEYS:
        assert f'"{key}":' not in block, f"{key} 又被 config_map 转译落库"


def test_full_config_endpoint_declares_neither_group():
    """`/api/config/full` 里那两组开关是这族唯一的"运营面"（虽然该端点本身零消费方）。"""
    text = _backend_text("api/core.py")
    for name in ("music", "wallpaper", "sakura", "pio_spine", "sidebar"):
        assert f'name="{name}"' not in text, f"分组 {name} 又出现在 /config/full"


def test_front_end_has_no_consumer_or_runtime():
    """键名与运行时库名双双零命中——这才是"整族没实现"的判据，而不是"接线漏了一半"。"""
    key_pat = re.compile(rf"\b({'|'.join(DEAD_KEYS)})\b")
    key_hits: list[str] = []
    runtime_hits: list[str] = []
    for path in _sources(FRONTEND):
        body = path.read_text(encoding="utf-8", errors="ignore")
        if key_pat.search(body):
            key_hits.append(path.relative_to(REPO).as_posix())
        lowered = body.lower()
        if any(tok in lowered for tok in FRONTEND_RUNTIME_TOKENS):
            runtime_hits.append(path.relative_to(REPO).as_posix())
    assert key_hits == [], f"前端又引用了死键：{key_hits}"
    assert runtime_hits == [], f"前端出现播放器/看板娘运行时引用但后端已无配置口：{runtime_hits}"


def test_openapi_drops_the_dead_family():
    body = str(app.openapi()["components"]["schemas"])
    for key in DEAD_KEYS:
        assert key not in body, f"{key} 又回到接口文档了"


@pytest.mark.asyncio
async def test_legacy_db_rows_do_not_resurrect_the_keys(client):
    """库里躺着退役前的旧行是**存量事实**（生产 PG 就有）：读口必须无视它们，而不是 500。"""
    from backend.core.database import async_session_maker
    from backend.models.core import SiteConfig

    seeded: list[int] = []
    async with async_session_maker() as session:
        for env in ("MUSIC_ENABLED", "WALLPAPER_MODE", "SIDEBAR"):
            row = (
                await session.execute(select(SiteConfig).where(SiteConfig.key == env))
            ).scalar_one_or_none()
            if row is None:
                row = SiteConfig(key=env, value="true", description="")
                session.add(row)
            else:
                row.value = "true"
            await session.flush()
            seeded.append(row.id)
        await session.commit()

    try:
        resp = await client.get("/api/config")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        for key in DEAD_KEYS:
            assert key not in body, f"{key} 被存量库行重新投影出来了"
        assert body["site_name"], "读口至少要正常带回活字段，否则这条断言是恒真的"
    finally:
        async with async_session_maker() as session:
            await session.execute(delete(SiteConfig).where(SiteConfig.id.in_(seeded)))
            await session.commit()


# ---------------------------------------------------------
# 活功能不得被一起删掉
# ---------------------------------------------------------
def test_bing_wallpaper_system_is_intact():
    """`wallpaper_*` 死的是旧 Banner 体系；Bing 每日壁纸是另一套，必须全链活着。"""
    from backend.schemas import SiteConfigResponse

    assert "enable_bing_wallpaper" in SiteConfigResponse.model_fields
    text = _backend_text("api/core.py")
    assert "ENABLE_BING_WALLPAPER" in text
    paths = app.openapi()["paths"]
    assert "/api/bing/wallpaper" in paths, "Bing 壁纸接口不见了"


@pytest.mark.asyncio
async def test_bing_wallpaper_service_still_reads_the_live_switch():
    from backend.services.site_settings import bing_wallpaper_enabled

    assert await bing_wallpaper_enabled() is not None


def test_navigation_sidebar_location_is_still_supported():
    """删侧边栏**小工具**配置不等于删导航的 `sidebar` 位置（批次 #95/#96 的产物）。"""
    from pydantic import ValidationError

    from backend.schemas import NavigationCreate

    assert (
        NavigationCreate(title={"zh": "侧边栏"}, url="/links", location="sidebar").location
        == "sidebar"
    )
    with pytest.raises(ValidationError):
        NavigationCreate(title={"zh": "x"}, url="/x", location="notaplace")
    assert "位置：header/footer/sidebar" in _backend_text("api/core.py"), (
        "读口不再按 sidebar 位置取导航"
    )


def test_hero_config_family_is_intact():
    """首页轮播是**表驱动**的另一套（`hero_slides` + `/api/hero/*`），删扁平键不该动到它。"""
    paths = app.openapi()["paths"]
    for path in ("/api/hero/slides", "/api/admin/hero/slides/{slide_id}"):
        assert path in paths, f"{path} 不见了：首页轮播被一起删掉了"
    text = _backend_text("api/hero.py")
    assert "hero_slides" in text


def test_coverage_doc_records_the_retirement():
    doc = (FRONTEND / "docs" / "API_COVERAGE.md").read_text(encoding="utf-8")
    blocks = [b for b in doc.split("\n   - ") if "扁平死配置族" in b]
    assert len(blocks) == 1, "文档里这段退役记录丢失或重复：下一个人会照着旧清单重接"
    block = blocks[0]
    assert "已退役" in block and "不是待接缺口" in block
    for family in ("music_", "wallpaper_", "sidebar_", "sakura_", "pio_spine_"):
        assert family in block, f"退役记录没有点名 {family}"
    assert "Bing" in block, "没写清「死的是旧 Banner 体系、Bing 壁纸仍活」，容易被误删"
