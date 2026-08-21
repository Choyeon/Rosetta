"""
Rosetta OOBE 种子数据源（重构精简版）。

历史：原文件 9793 LOC 的「上帝脚本」，32 篇四语言真实文章正文直接内联为 Python 字面量，
与 mock_data.py 大量重复（分类/标签/工厂代码三份写开）。

重构后：
1. 所有本地化长字符串迁移到 ``backend/data/seed_content.<lang>.json`` （4 份文件）。
2. 共享业务工厂集中在 ``backend.scripts._seed_shared.SeedContext`` 单一入口。
3. 本模块只做两件事：
   - 以**与旧代码完全兼容**的名称暴露原始常量（OOBE_CATEGORIES / OOBE_TAGS /
     ARTICLE_TEMPLATES_V3 / COMMENT_PERSONAS / COMMENT_CONTENT_TEMPLATES / ACTIVITY_TEMPLATES）
     —— 这样 mock_data.py 或者任何第三方 import 都不会在过渡期直接断裂。
   - 提供一条可选的 CLI 包装 ``run_oobe_seed(db, admin_user)`` 委托给 SeedContext。
"""

from __future__ import annotations

import logging
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.scripts._seed_shared import SeedContext, SeedDataBundle, UTC

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 向后兼容：从 4 份 JSON 重建 Python 字面量（与 9793 行老脚本等价）
# 注意：为了性能，常量按懒加载，首次访问构建并缓存。
# ---------------------------------------------------------------------------

_CACHE: dict[str, Any] = {}


def _bundle() -> SeedDataBundle:
    if "_bundle" in _CACHE:
        return _CACHE["_bundle"]
    _CACHE["_bundle"] = SeedDataBundle()
    return _CACHE["_bundle"]


def _build_oobe_categories() -> list[dict]:
    out: list[dict] = []
    for slug in _bundle().cat_slugs():
        info = _bundle().cat_i18n(slug)
        out.append({
            "slug": slug,
            "name": info["name"],
            "description": info["description"],
            "color": info["meta"].get("color") or "#3B82F6",
            "icon": info["meta"].get("icon") or "heroicons:code-bracket",
        })
    return out


def _build_oobe_tags() -> list[dict]:
    out: list[dict] = []
    for slug in _bundle().tag_slugs():
        info = _bundle().tag_i18n(slug)
        out.append({
            "slug": slug,
            "name": info["name"],
            "color": info["color"] or "#6366F1",
        })
    return out


def _build_article_templates_v3() -> list[dict]:
    """32 篇四语言技术文章模板：字段对齐旧脚本。"""
    out: list[dict] = []
    for slug in _bundle().post_slugs():
        i18n = _bundle().post_i18n(slug)
        meta_src = _bundle()._posts_by_slug.get(slug, {}).get("zh") or next(
            iter(_bundle()._posts_by_slug.get(slug, {}).values()), {}
        )
        cats = meta_src.get("categories") or ["technology"]
        out.append({
            "slug": slug,
            "title_zh": i18n["title"].get("zh", ""),
            "title_en": i18n["title"].get("en", ""),
            "title_ja": i18n["title"].get("ja", ""),
            "title_zh_hant": i18n["title"].get("zh_Hant", ""),
            "excerpt_zh": i18n["summary"].get("zh", ""),
            "excerpt_en": i18n["summary"].get("en", ""),
            "excerpt_ja": i18n["summary"].get("ja", ""),
            "excerpt_zh_hant": i18n["summary"].get("zh_Hant", ""),
            "content_zh": i18n["content_md"].get("zh", ""),
            "content_en": i18n["content_md"].get("en", ""),
            "content_ja": i18n["content_md"].get("ja", ""),
            "content_zh_hant": i18n["content_md"].get("zh_Hant", ""),
            "category_slug": cats[0],
            "tag_slugs": list(meta_src.get("tags") or []),
            "cover_theme": meta_src.get("cover_theme") or "",
            "code_language": meta_src.get("code_language") or "",
            "code_snippet": meta_src.get("code_snippet") or "",
        })
    return out


def _build_comment_personas() -> list[dict]:
    rows = _bundle().get("users", "zh")
    out: list[dict] = []
    for r in rows:
        out.append({
            "nickname": r.get("nickname", ""),
            "email": r.get("email", ""),
            "style": r.get("style") or "normal",
            "website": r.get("website"),
            "github": r.get("github"),
            "qq": r.get("qq"),
            "avatar_source": r.get("avatar_source", "auto"),
            "user_agent": r.get("user_agent"),
            "ip_range": r.get("ip_range"),
        })
    return out


def _build_comment_content_templates() -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {}
    for r in _bundle().get("comments", "zh"):
        buckets.setdefault(r.get("bucket", "backend"), []).append(r.get("text", ""))
    return buckets


def _build_activity_templates() -> list[dict]:
    out: list[dict] = []
    zh_rows = _bundle().get("activities", "zh")
    for i, row in enumerate(zh_rows):
        t: dict[str, str] = {}
        for loc in ("zh", "en", "ja", "zh_Hant"):
            arr = _bundle().get("activities", loc)
            t[loc] = arr[i].get("text", "") if i < len(arr) else ""
        out.append({"type": row.get("type", "say"), **t})
    return out


# ---- 旧代码使用「直接 import 名字」：模块顶层以列表/字典常量暴露。 ----
# 注意：以下模块级赋值同时确保 ``from ... import X`` 与 ``getattr(module, "X")`` 均正确。
OOBE_CATEGORIES: list[dict] = _build_oobe_categories()
OOBE_TAGS: list[dict] = _build_oobe_tags()
ARTICLE_TEMPLATES_V3: list[dict] = _build_article_templates_v3()
COMMENT_PERSONAS: list[dict] = _build_comment_personas()
COMMENT_CONTENT_TEMPLATES: dict[str, list[str]] = _build_comment_content_templates()
ACTIVITY_TEMPLATES: list[dict] = _build_activity_templates()

# 为 IDE / inspect 友好：保留显式 __all__。
__all__ = [
    "OOBE_CATEGORIES",
    "OOBE_TAGS",
    "ARTICLE_TEMPLATES_V3",
    "COMMENT_PERSONAS",
    "COMMENT_CONTENT_TEMPLATES",
    "ACTIVITY_TEMPLATES",
    "run_oobe_seed",
    "UTC",
]


# ---------------------------------------------------------------------------
# 新的一流入口：委托给共享工厂 SeedContext
# ---------------------------------------------------------------------------


async def run_oobe_seed(db, admin_user) -> dict:
    """一次性注入完整的 OOBE 种子数据（新代码推荐入口）。

    Args:
        db: AsyncSession
        admin_user: 已创建的管理员 ORM 对象（通常是 OOBE 第五步刚建完的用户）

    Returns:
        dict with counts: {categories, tags, posts, comments, activities,
        guestbook_entries, galleries_albums, galleries_photos, pages, created_total}
    """
    ctx = SeedContext(db, lang="zh")
    res = await ctx.run_seed(
        author=admin_user,
        include_posts=True,
        include_comments=True,
        include_activities=True,
        include_guestbook=True,
        include_galleries=True,
        include_pages=True,
        include_navigation=False,
    )
    d = res.details
    out = {
        "categories": d.get("categories", {}).get("created", 0),
        "tags": d.get("tags", {}).get("created", 0),
        "posts": d.get("posts", {}).get("created", 0),
        "comments": d.get("comments", {}).get("created", 0),
        "activities": d.get("activities", {}).get("created", 0),
        "guestbook_entries": d.get("guestbooks", {}).get("created", 0),
        "galleries_albums": d.get("galleries_albums", {}).get("created", 0),
        "galleries_photos": d.get("galleries_photos", {}).get("created", 0),
        "pages": d.get("pages", {}).get("created", 0),
        "navigations": d.get("navigations", {}).get("created", 0),
        "created_total": res.created,
        "skipped_total": res.skipped,
    }
    return out


# ---------------------------------------------------------------------------
# 离线调试：把当前常量导出成 pickle（供 JSON 提取或对比测试使用）
# ---------------------------------------------------------------------------


def _dump_pickle(out_path: str) -> None:
    data = {
        "OOBE_CATEGORIES": _OOBE_CATEGORIES,
        "OOBE_TAGS": _OOBE_TAGS,
        "ARTICLE_TEMPLATES_V3": _ARTICLE_TEMPLATES_V3,
        "COMMENT_PERSONAS": _COMMENT_PERSONAS,
        "COMMENT_CONTENT_TEMPLATES": _COMMENT_CONTENT_TEMPLATES,
        "ACTIVITY_TEMPLATES": _ACTIVITY_TEMPLATES,
    }
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        pickle.dump(data, f)
    print(f"Pickle dump written: {p}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OOBE seed data utilities (refactor edition)")
    parser.add_argument("--dump-pickle", type=str, help="Write backward-compat constants to a pickle file")
    parser.add_argument("--print-counts", action="store_true", help="Print counts of each constant")
    args = parser.parse_args()

    if args.dump_pickle:
        _dump_pickle(args.dump_pickle)

    if args.print_counts or (not args.dump_pickle and not args.dump_pickle):
        print("[oobe_seed_data] loaded constant counts (from JSON):")
        print(f"  categories : {len(_OOBE_CATEGORIES)}")
        print(f"  tags       : {len(_OOBE_TAGS)}")
        print(f"  articles   : {len(_ARTICLE_TEMPLATES_V3)}")
        print(f"  personas   : {len(_COMMENT_PERSONAS)}")
        print(f"  comment buckets: {len(_COMMENT_CONTENT_TEMPLATES)} "
              f"({sum(len(v) for v in _COMMENT_CONTENT_TEMPLATES.values())} templates)")
        print(f"  activities : {len(_ACTIVITY_TEMPLATES)}")
