"""调色板（palette）一族退役后的守卫。

2026-10-28 删掉的是一条**看起来还在、实际什么都不发生**的能力：
``GET /api/themes/palettes`` / ``GET /api/themes/current.css`` /
``PUT /api/admin/themes/current`` 三条端点读写 SiteConfig KV ``theme_palette``，
而全站没有任何一处读这个键；``main.css`` 里那 16 个 ``html.palette-*`` 块也从未生效——
唯一给 ``<html>`` 挂 ``palette-*`` class 的 ``composables/useThemePalette.ts``
在主题解耦那一轮（f0c195c1）已经删除，只剩后端清单与 CSS 僵尸。
站点主色的活路径只有一条：``settings.appearance.primary_color`` 与主题 mods 的
``primary_color``，由 ``frontend/composables/useFrontendTheme.ts`` 写进 ``:root --primary``。

四条断言各自挡一种回归：
* 端点回到 OpenAPI / ``themes.py`` 出现第二条路由（有人照着旧文档把同族别名口"顺手补回来"）；
* 前端重新出现 ``palette-`` 字样而 CSS 里没有对应块（半接线的调色板，后台改了没反应）；
* 活路径 ``primary_color`` 被一起删掉（那会把"删僵尸"做成"删功能"）；
* 覆盖度文档没留下退役记录（下一个人会当成缺口重接一遍）。

口径依据 AGENTS.md §7.4 第 4 条：核对路由存在性读**生成后的** ``app.openapi()["paths"]``，
不读 ``app.routes``（``_IncludedRouter`` 懒挂载会假通过）。
"""

from pathlib import Path

import pytest

from backend.api import themes as themes_module
from backend.main import app

REPO = Path(__file__).resolve().parents[1]
MAIN_CSS = REPO / "frontend" / "assets" / "css" / "main.css"
FRONTEND_ROOT = REPO / "frontend"
USE_FRONTEND_THEME = FRONTEND_ROOT / "composables" / "useFrontendTheme.ts"
COVERAGE_DOC = FRONTEND_ROOT / "docs" / "API_COVERAGE.md"

# 退役的三条口（OpenAPI 里的完整路径）
RETIRED_PATHS = (
    "/api/themes/palettes",
    "/api/themes/current.css",
    "/api/admin/themes/current",
)

# 扫描前端源码时跳过的目录（构建产物与依赖里必然含 "palette-" 字样，会假红）
_SKIP_DIR_NAMES = {"node_modules", ".output", ".nuxt", "dist", ".cache"}
_SCAN_SUFFIXES = {".ts", ".vue", ".css", ".js"}


def _openapi_paths() -> set[str]:
    return set(app.openapi()["paths"].keys())


def _frontend_sources() -> list[Path]:
    out: list[Path] = []
    for path in FRONTEND_ROOT.rglob("*"):
        if path.suffix not in _SCAN_SUFFIXES or not path.is_file():
            continue
        if _SKIP_DIR_NAMES.intersection(set(path.relative_to(FRONTEND_ROOT).parts[:-1])):
            continue
        out.append(path)
    return out


def test_retired_palette_paths_are_gone_from_openapi():
    paths = _openapi_paths()
    for retired in RETIRED_PATHS:
        assert retired not in paths, f"{retired} 又出现了：调色板一族是退役决定，不是缺口"


def test_themes_module_registers_only_the_active_theme_route():
    """``themes.py`` 只剩一条公开读口；多出任何一条都要先说明它有没有读取方。"""
    declared = {route.path for route in themes_module.router.routes}
    assert declared == {"/themes/active"}, f"themes.py 的路由清单变成了 {declared}"


def test_main_css_no_longer_carries_palette_selectors():
    assert "palette-" not in MAIN_CSS.read_text(encoding="utf-8"), (
        "main.css 里重新出现 palette-* 块——它们是永远挂不上的死 CSS，每个访客都要多下一份"
    )


def test_no_frontend_source_applies_a_palette_class():
    """前端不得出现 ``palette-`` 字样：挂 class 的那一侧已经删干净了。"""
    hits = [
        path.relative_to(FRONTEND_ROOT).as_posix()
        for path in _frontend_sources()
        if "palette-" in path.read_text(encoding="utf-8")
    ]
    assert hits == [], f"这些前端文件引用了 palette- 类名：{hits}"


def test_live_primary_color_path_still_exists():
    """守卫的意义是删僵尸，不是删功能——活路径必须在。"""
    text = USE_FRONTEND_THEME.read_text(encoding="utf-8")
    assert "primary_color" in text, "useFrontendTheme 不再消费 primary_color，主色单源断了"
    assert "setProperty(" in text and "--primary" in text, (
        "useFrontendTheme 不再把主色写进 :root，主题 mods 的主色开关会失效"
    )


@pytest.mark.parametrize("needle", ["退役"])
def test_coverage_doc_records_the_retirement(needle):
    """覆盖度文档要把这次删除写成决定，否则下一个人会当成缺口重接一遍。"""
    assert needle in COVERAGE_DOC.read_text(encoding="utf-8")
