"""llms.txt 的核心页面清单必须与后端 sitemap 的公开目录页同口径。

`_STATIC_SITEMAP_ROUTES` 是「恒存在且恒可索引」那张表，三个分类学根目录由
`generate_taxonomy_sitemap` 输出（所以不在那张表里，但同样是目录页）。llms.txt 是同一批
页面交给 **AI 抓取器**的那份纯文本索引。两张表各写一份迟早分叉——往 sitemap 加一页而
llms.txt 没跟上，等于给爬虫一份少条目的索引；反过来在 llms.txt 列出可索引性由运行时配置
决定的页面（/sponsor 看捐助配置、/gallery 与 /wallpapers 看有没有内容）则会把动态答案写死进
一份带 3600s 缓存的静态文本里。所以判据是**集合相等，例外只有 feed 与分类学根目录两类**。
"""

import re
from pathlib import Path

from backend.api.blog import _STATIC_SITEMAP_ROUTES

REPO_ROOT = Path(__file__).resolve().parents[1]
LLMS_ROUTE = REPO_ROOT / "frontend" / "server" / "routes" / "llms.txt.get.ts"

# 已知的非页面出口：feed 与索引本身，它们不是 pages/ 下的路由。
FEED_EXEMPTIONS = {"/rss.xml", "/sitemap.xml"}
# 分类学根目录：由 generate_taxonomy_sitemap 输出，不在 _STATIC_SITEMAP_ROUTES 那张表里。
TAXONOMY_ROOTS = {"/categories", "/tags", "/series"}


def core_page_paths() -> set[str]:
    source = LLMS_ROUTE.read_text(encoding="utf-8")
    block = re.search(r"const CORE_PAGES = \[([\s\S]*?)\] as const", source)
    assert block, "llms.txt 里找不到 CORE_PAGES 常量（清单形态变了，判据要跟着改）"
    return set(re.findall(r"\[\s*'[^']*'\s*,\s*'([^']+)'\s*\]", block.group(1)))


def test_llms_core_pages_are_declared_as_a_single_block():
    """清单必须还是那个可静态解析的形态：改了写法就要同步改这里的正则，不得静默失聪。"""
    assert LLMS_ROUTE.exists(), f"缺少 {LLMS_ROUTE}"
    assert core_page_paths(), "CORE_PAGES 解析出空清单"


def test_core_pages_equal_public_directory_pages():
    sitemap_paths = {path for path, _freq, _prio in _STATIC_SITEMAP_ROUTES}
    assert sitemap_paths, "后端固定路由表被清空了——那 sitemap 也不再收录任何目录页"
    expected = sitemap_paths | TAXONOMY_ROOTS | FEED_EXEMPTIONS
    assert core_page_paths() == expected, (
        "llms.txt 与公开目录页分叉："
        f"只在 llms.txt={sorted(core_page_paths() - expected)} "
        f"只在 sitemap={sorted(expected - core_page_paths())}"
    )


def test_core_pages_exclude_runtime_conditional_pages():
    """可索引性由运行时配置/内容决定的页不得进这份静态索引。"""
    core = core_page_paths()
    for conditional in ("/sponsor", "/gallery", "/wallpapers"):
        assert conditional not in core, f"{conditional} 的可索引性是条件性的，不该写进 CORE_PAGES"
