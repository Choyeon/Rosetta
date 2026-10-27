"""SiteConfig 写侧缓存失效单源契约（两族读面必须一起删净）。

`site_configs` 表有两个互不相通的读面，键形不同、TTL 同档（3600s）：

- ``site_config`` —— 聚合值。``/api/config`` 与 RSS channel 读它，分组 JSON（basic/seo/
  footer…）在 ``core.py::_apply_settings_groups`` 里叠进这份聚合。
- ``site_config_value:<KEY>`` —— ``core/site_config.py::get_site_config_value`` 的逐键缓存。
  robots.txt、sitemap 与 OG 的站点名/简介走的是这条口（seo.py 三处读 SITE_NAME /
  SITE_DESCRIPTION / SEO_ROBOTS）。

写侧历史上只删第一族（``cache.delete(make_cache_key("site_config"))``），表现是
"后台改了站点名，接口与 RSS 立刻是新的，但爬虫读的 robots.txt / sitemap 一小时内
仍写旧站名"。SEO 那条口反过来只删 ``site_config:*`` 与 ``site_config_value:*``，而带
冒号的模式压根匹配不到裸聚合键 ``site_config``。两处各漏一半。

口径单源是 ``invalidate_site_config_caches()``：一条 ``site_config`` 前缀通配同时覆盖两族
（OOBE 装机与整站恢复本来就用这个前缀）。本文件钉住三个后台写口各自把两族删净，
并且源码里不再出现"只删一族"的窄写法。
"""

import re
from pathlib import Path

from backend.core.cache import cache, make_cache_key
from backend.core.site_config import get_site_config_value, invalidate_site_config_caches

API_DIR = Path(__file__).resolve().parents[1] / "backend/api"

AGGREGATE_KEY = make_cache_key("site_config")
PER_KEY_SITE_NAME = make_cache_key("site_config_value", "SITE_NAME")

# 往 site_configs 写行的模块 → 允许它用哪种失效手法。
# 新增写口必须出现在这张表里（用单源函数），否则本守卫红。
SITE_CONFIG_WRITERS: dict[str, tuple[str, ...]] = {
    "core.py": ("invalidate_site_config_caches",),
    "settings_groups.py": ("invalidate_site_config_caches",),
    "seo.py": ("invalidate_site_config_caches",),
    # 装机与整站恢复删的是一整串前缀，其中 "site_config" 这条已经覆盖两族。
    "oobe.py": ("invalidate_cache(_prefix)", '"site_config",'),
    "import_export.py": ("_invalidate_content_caches", '"site_config"'),
    # themes.py 曾经写调色板键 theme_palette（读侧直查 DB、不经这两族缓存，所以登记为空），
    # 2026-10-28 调色板一族退役后它只剩一条只读口，不再是 SiteConfig 写口：
    # 见 tests/test_retired_palette_family_is_gone.py。
}


async def _prime_both_families() -> None:
    """把两族缓存都写成"旧值"，让任何漏删都能被断言抓到。"""
    await cache.set(AGGREGATE_KEY, {"site_name": "装机旧站名"}, 3600)
    await cache.set(PER_KEY_SITE_NAME, "装机旧站名", 3600)


async def _assert_both_families_gone(context: str) -> None:
    assert await cache.get(AGGREGATE_KEY) is None, f"{context}：聚合 site_config 没删"
    assert await cache.get(PER_KEY_SITE_NAME) is None, f"{context}：逐键 site_config_value 没删"


async def test_helper_clears_both_key_families():
    """单源函数本身：一次调用删净聚合键与逐键族，并回报删除条数。"""
    await _prime_both_families()
    assert await invalidate_site_config_caches() >= 2
    await _assert_both_families_gone("invalidate_site_config_caches")


async def test_helper_returns_zero_when_nothing_cached():
    assert await invalidate_site_config_caches() == 0


async def test_flat_settings_endpoint_clears_both_families(client, staff_headers):
    """POST /api/admin/settings 写的是扁平 UPPERCASE 键，必须连逐键缓存一起清。"""
    await _prime_both_families()

    resp = await client.post(
        "/api/admin/settings",
        json={"site_name": "改过的站名"},
        headers=staff_headers,
    )
    assert resp.status_code == 200, resp.text
    await _assert_both_families_gone("POST /api/admin/settings")
    # 逐键读面拿到新值 = 缓存确实没把旧值端出去
    assert await get_site_config_value("SITE_NAME") == "改过的站名"


async def test_group_patch_clears_both_families(client, staff_headers):
    """PATCH /api/settings/{group} 覆写聚合值，同样必须删净两族。"""
    await _prime_both_families()

    resp = await client.patch(
        "/api/settings/basic",
        json={"site_name": "分组新站名"},
        headers=staff_headers,
    )
    assert resp.status_code == 200, resp.text
    await _assert_both_families_gone("PATCH /api/settings/basic")


async def test_seo_config_put_clears_both_families(client, staff_headers):
    """PUT /api/seo/config 曾只删 `site_config:*`（匹配不到裸聚合键）与逐键族。"""
    await _prime_both_families()

    resp = await client.put(
        "/api/seo/config",
        json={"SEO_ROBOTS": "User-agent: *\nDisallow: /tmp-test/"},
        headers=staff_headers,
    )
    assert resp.status_code == 200, resp.text
    await _assert_both_families_gone("PUT /api/seo/config")


async def test_no_narrow_aggregate_only_delete():
    """写侧不得再出现"只删一族"的窄写法（精确删聚合键 / 只带冒号的模式）。"""
    narrow = re.compile(r"cache\.delete\(\s*make_cache_key\(\s*[\"']site_config[\"']\s*\)\s*\)")
    narrow_pattern = re.compile(r"cache\.delete_pattern\(\s*make_cache_key\(\s*[\"']site_config:")
    offenders = []
    for path in sorted(API_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if narrow.search(text) or narrow_pattern.search(text):
            offenders.append(path.name)
    assert not offenders, f"仍在只删单族 SiteConfig 缓存：{offenders}"


async def test_every_site_config_writer_declares_its_invalidation():
    """新增写口若没登记失效手法，守卫直接红；已登记的要真在源码里用上。"""
    found = {p.name for p in API_DIR.glob("*.py") if "SiteConfig(" in p.read_text(encoding="utf-8")}
    assert found == set(SITE_CONFIG_WRITERS), (
        f"写 SiteConfig 的模块清单变了：多出 {sorted(found - set(SITE_CONFIG_WRITERS))}，"
        f"缺少 {sorted(set(SITE_CONFIG_WRITERS) - found)}"
    )
    unproved = []
    for name, markers in SITE_CONFIG_WRITERS.items():
        text = (API_DIR / name).read_text(encoding="utf-8")
        if markers and not all(m in text for m in markers):
            unproved.append(name)
    assert not unproved, f"登记表声明了失效手法、源码里却找不到：{unproved}"
