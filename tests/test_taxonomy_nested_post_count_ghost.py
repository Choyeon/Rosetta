"""嵌套分类/标签投影里的 `post_count` 幽灵键守卫（批次 #154）。

`CategoryLocalizedResponse` / `TagLocalizedResponse` 只出现在**文章载荷的嵌套位**
（详情 / 列表 / 搜索 / 推荐 / 相似 / 热榜的 `category` 与 `tags[]`），而它们的构造器写的是
`post_count=getattr(category, "post_count", 0)` —— `Category`/`Tag` 模型上根本没有这一列
（真实列只有 id/name/slug/description/icon/color/cover_image/parent_id/is_active/created_at/updated_at，
关系只有 posts/parent），默认值 0 让它看起来像"字段活着、只是这个分类没文章"。
于是每一篇对外文章都在替它的分类和标签宣布"0 篇文章"，而 OpenAPI 把这个恒 0 的键声明成真实字段。

真正的计数在**分类/标签自己的集合口**（`/blog/categories`、`/blog/tags`、详情口）由 SQL 聚合出来，
消费方读的就是那一份；后台两个列表页（`admin/content/categories.vue` / `tags.vue`）亦然。
所以这里的口径是**删掉嵌套位的恒 0 键**，而不是给每篇文章再补一次聚合查询（那是 N+1）。
"""

import ast
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient

from backend.models.blog import Category, Post, Tag

SCHEMAS_SRC = Path("backend/schemas/__init__.py").read_text(encoding="utf-8")

# 嵌套投影（挂在文章载荷里）与集合投影（分类/标签自己的列表口）是两套模型
NESTED_MODELS = ("CategoryLocalizedResponse", "TagLocalizedResponse")
COLLECTION_MODELS = ("CategoryResponse", "TagResponse")


def _class_body_src(name: str) -> str:
    tree = ast.parse(SCHEMAS_SRC)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return ast.unparse(node)
    raise AssertionError(f"class {name} not found in backend/schemas/__init__.py")


def _rows_of(response) -> list[dict]:
    """分类/标签集合口回裸 list（不是 {success,data} 信封）。"""
    body = response.json()
    return body["data"] if isinstance(body, dict) else body


async def _make_taxonomy(db_session, slug_hint: str = "ghost"):
    category = Category(
        name={"zh": "计数守卫分类", "en": "guard", "ja": "guard", "zh_Hant": "guard"},
        slug=f"{slug_hint}-count-category-{uuid.uuid4().hex[:8]}",
        color="#123456",
    )
    tag = Tag(
        name={"zh": "计数守卫标签", "en": "guard", "ja": "guard", "zh_Hant": "guard"},
        slug=f"{slug_hint}-count-tag-{uuid.uuid4().hex[:8]}",
        color="#654321",
        is_active=True,
    )
    db_session.add_all([category, tag])
    await db_session.commit()
    return category, tag


async def _make_post(db_session, author_id: int, *, category, tags):
    """关系只能在构造器一次给全：commit 之后再赋 `post.tags` 会先懒加载旧集合，
    异步会话里的属性懒加载就是 MissingGreenlet。`published_at` 留 NULL——
    SQLite 把 aware datetime 存成带 +00:00 的字符串，与 CURRENT_TIMESTAMP 做字符串比较，
    刚写入的行会被「发布时间已到今天」的谓词判成在未来。"""
    post = Post(
        title={"zh": "嵌套计数守卫文章", "en": "Nested ghost count"},
        content={"zh": "正文", "en": "Body"},
        slug=f"nested-ghost-{uuid.uuid4().hex[:10]}",
        author_id=author_id,
        category=category,
        tags=tags,
        status="published",
    )
    db_session.add(post)
    await db_session.commit()
    return post


@pytest.mark.parametrize("model_name", NESTED_MODELS)
def test_ghost_getattr_is_gone_from_schemas_source(model_name):
    """构造器不许再对分类/标签实例 getattr("post_count", 默认值)（幽灵键的源头）。"""
    body = _class_body_src(model_name)
    assert 'getattr(category, "post_count"' not in body
    assert 'getattr(tag, "post_count"' not in body
    offenders = []
    for node in ast.walk(ast.parse(body)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 3
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == "post_count"
        ):
            offenders.append(ast.unparse(node))
    assert offenders == [], f"{model_name} 里仍有兜底默认值的 getattr：{offenders}"


@pytest.mark.parametrize("model_name", NESTED_MODELS)
def test_nested_models_do_not_declare_post_count(model_name):
    from backend.schemas import CategoryLocalizedResponse, TagLocalizedResponse

    cls = CategoryLocalizedResponse if "Category" in model_name else TagLocalizedResponse
    assert "post_count" not in cls.model_fields, f"{model_name} 仍在声明一个永远为 0 的键"


@pytest.mark.parametrize("model_name", COLLECTION_MODELS)
def test_collection_models_keep_real_post_count(model_name):
    """集合口那一份是真聚合，不许被这一批一起删掉。"""
    from backend.schemas import CategoryResponse, TagResponse

    cls = CategoryResponse if "Category" in model_name else TagResponse
    assert "post_count" in cls.model_fields


def test_openapi_does_not_document_the_ghost_key():
    from backend.main import app

    schema = app.openapi()
    for name in NESTED_MODELS:
        ref = schema["components"]["schemas"].get(name)
        assert ref is not None, f"{name} 从文档里消失了（不应由本批造成）"
        assert "post_count" not in ref.get("properties", {}), f"{name} 的文档还挂着恒 0 键"


@pytest.mark.asyncio
async def test_post_payload_nested_taxonomy_has_no_post_count(
    client: AsyncClient, db_session, test_user
):
    category, tag = await _make_taxonomy(db_session)
    post = await _make_post(db_session, test_user.id, category=category, tags=[tag])

    response = await client.get(f"/api/blog/posts/{post.slug}")
    assert response.status_code == 200, response.text
    data = response.json().get("data", response.json())

    nested = data.get("category")
    assert nested is not None and nested.get("slug") == category.slug
    assert "post_count" not in nested, "文章载荷里的分类又带上了恒 0 计数"

    tags = data.get("tags") or []
    assert any(t.get("slug") == tag.slug for t in tags), f"标签没进载荷：{tags}"
    for item in tags:
        assert "post_count" not in item, "文章载荷里的标签又带上了恒 0 计数"


@pytest.mark.asyncio
async def test_category_and_tag_lists_still_report_real_counts(
    client: AsyncClient, db_session, test_user
):
    """集合口的计数必须是真数（删幽灵不许顺手把真值也弄没）。"""
    category, tag = await _make_taxonomy(db_session, slug_hint="real")
    await _make_post(db_session, test_user.id, category=category, tags=[tag])

    cats = _rows_of(await client.get("/api/blog/categories"))
    row = next((c for c in cats if c.get("slug") == category.slug), None)
    assert row is not None, f"分类列表里没有它：{[c.get('slug') for c in cats]}"
    assert row.get("post_count") == 1, row

    tags = _rows_of(await client.get("/api/blog/tags"))
    trow = next((t for t in tags if t.get("slug") == tag.slug), None)
    assert trow is not None, f"标签列表里没有它：{[t.get('slug') for t in tags]}"
    assert trow.get("post_count") == 1, trow
