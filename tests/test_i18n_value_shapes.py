"""JSON 多语言列的**值形态**容错：`get_i18n_value` 是 60+ 个读取面的汇聚点。

`title` / `content` / `excerpt` 声明的是 JSON 列，类型注解写的是 `dict[str, str] | None`，
但库里真的会出现**裸字符串**：导入工具、早期写入路径、直接写库都能留下
`content="正文"` 这种单语行（`blog.py` 的列表口早已按 `isinstance(..., dict)` 分支处理过
同一形态，说明这不是假设）。收口前 `get_i18n_value` 只会 `data.get(...)`，于是这样一行
数据让文章详情口 `GET /api/blog/posts/{slug}` 直接 500——单个访客就能撞见，
且同一篇文章在列表、RSS、SEO schema 里各自炸一次。

下面按"纯函数三种入参 + 真实详情口 + 列表口"钉住：脏数据必须降级成"整段当默认语言"，
而不是把接口打挂。
"""

import io
import zipfile
from datetime import datetime

import pytest

from backend.core.i18n import get_i18n_value
from backend.models.activity import Activity
from backend.models.blog import Category, Post, Tag
from backend.models.core import (
    FriendLink,
    Navigation,
    Notification,
    Page,
    SearchPlaceholder,
)
from backend.models.post_series import PostSeries


class TestHelperToleratesNonDict:
    def test_bare_string_returns_as_is(self):
        assert get_i18n_value("单语正文", "en") == "单语正文"
        assert get_i18n_value("单语正文", "ja", fallback=False) == "单语正文"

    def test_dict_still_resolves_by_language(self):
        data = {"zh": "中文", "en": "English"}
        assert get_i18n_value(data, "en") == "English"
        assert get_i18n_value(data, "ja") == "中文"

    def test_empty_shapes_stay_empty(self):
        assert get_i18n_value(None, "zh") == ""
        assert get_i18n_value("", "zh") == ""
        assert get_i18n_value({}, "zh") == ""


async def _make_legacy_row(db_session, author, slug: str) -> Post:
    """直写 ORM 造一行"单语列里躺裸字符串"的历史数据（正常接口不会这么写）。

    `published_at` 留 NULL：匿名列表的谓词是 `published_at IS NULL OR <= now()`，
    SQLite 把 aware datetime 存成带 `+00:00` 后缀的字符串、与 `CURRENT_TIMESTAMP`
    做字符串比较时永远判成"在未来"，写死时间会让这条用例在 SQLite 上读到空页。
    """
    post = Post(
        title="旧导入的标题",
        slug=slug,
        status="published",
        content="旧导入的正文，含中文与 <code>标签</code>",
        excerpt="旧导入的摘要",
        author_id=author.id,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/blog/posts/{slug}",
        "/api/blog/posts/{slug}/adjacent",
    ],
    ids=["detail", "adjacent"],
)
async def test_legacy_string_columns_do_not_500_the_detail_family(
    client, db_session, admin_user, path
):
    slug = "legacy-str-content-detail"
    await _make_legacy_row(db_session, admin_user, slug)

    response = await client.get(path.format(slug=slug))
    assert response.status_code == 200, (
        "单语列里的裸字符串把读取面打挂了：get_i18n_value 必须原样返回而不是 .get()"
    )

    if path.endswith("{slug}"):
        # 详情口直接返回模型（无 {success,data} 信封）；列表/搜索那侧才有信封，
        # 这里按"拿到什么形态就读什么"两种都兼容。
        body = response.json()
        data = body.get("data") if isinstance(body.get("data"), dict) else body
        assert "旧导入的正文" in (data.get("content") or ""), data.get("content")
        assert data.get("title") == "旧导入的标题"


@pytest.mark.asyncio
async def test_legacy_row_also_survives_the_list_surface(client, db_session, admin_user):
    """列表口读的是同一批列；`title` 那侧的 isinstance 分支不能只护住一条口。"""
    await _make_legacy_row(db_session, admin_user, "legacy-str-content-list")

    response = await client.get("/api/blog/posts")
    assert response.status_code == 200, response.text
    payload = response.json()
    # 列表口直接返回 PaginatedResponse（items 在顶层），与详情口同样是"无信封"形态
    items = payload.get("items") or (payload.get("data") or {}).get("items") or []
    assert any("旧导入的标题" in str(row.get("title")) for row in items), items


async def _make_legacy_archived_row(db_session, author, category, slug: str, when, tags=None):
    """带发布日期的裸字符串行——归档口按 `extract(year/month)` 过滤，必须有时间才选得到。

    `published_at` 用 **naive** datetime：SQLite 把 aware 值存成带 `+00:00` 后缀的字符串，
    `strftime('%Y', …)` 对这种串取不出年份，这条会被 WHERE 直接滤掉、用例假绿。

    `tags` 只能在构造时传：commit/refresh 之后再 `post.tags = [...]` 会先懒加载旧集合，
    而异步会话里的属性懒加载就是 MissingGreenlet。
    """
    post = Post(
        title="旧导入的归档标题",
        slug=slug,
        status="published",
        content="旧导入的归档正文",
        excerpt="旧导入的归档摘要",
        category_id=category.id,
        author_id=author.id,
        published_at=when,
        tags=tags or [],
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


@pytest.mark.asyncio
async def test_legacy_columns_do_not_500_the_archive_family(client, db_session, admin_user):
    """归档年/月两条公开口（SSR 前台页直接打）曾经各自 `.get(lang)` 一遍。"""

    category = Category(name="旧导入的分类", slug="legacy-str-cat", color="#111111")
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    when = datetime(2026, 3, 14, 9, 30)
    await _make_legacy_archived_row(db_session, admin_user, category, "legacy-str-archive", when)

    year_resp = await client.get("/api/blog/archive/2026")
    assert year_resp.status_code == 200, year_resp.text
    month_resp = await client.get("/api/blog/archive/2026/3")
    assert month_resp.status_code == 200, month_resp.text

    blob = year_resp.text + month_resp.text
    assert "旧导入的归档标题" in blob, blob[:400]
    assert "旧导入的分类" in blob, blob[:400]


@pytest.mark.asyncio
async def test_legacy_category_name_survives_seo_schema(client, db_session, admin_user):
    """JSON-LD 的 `articleSection` 取的是 `category.name`，与正文是两条独立读取路径。"""

    category = Category(name="旧导入的分类", slug="legacy-str-cat-seo", color="#222222")
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    post = await _make_legacy_archived_row(
        db_session, admin_user, category, "legacy-str-seo-schema", datetime(2026, 3, 15, 9, 30)
    )

    response = await client.get(f"/api/seo/schema/article/{post.id}")
    assert response.status_code == 200, response.text
    assert response.json()["articleSection"] == "旧导入的分类"


@pytest.mark.asyncio
async def test_legacy_title_survives_series_autocomplete(client, db_session, admin_user):
    """autocomplete 走投影查询（id/title/slug），拿到的是 JSON 反序列化后的原值形态。"""

    category = Category(name={"zh": "分类"}, slug="legacy-str-cat-complete", color="#333333")
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    await _make_legacy_archived_row(
        db_session, admin_user, category, "legacy-str-complete", datetime(2026, 3, 16, 9, 30)
    )

    response = await client.post(
        "/api/post_series/complete", json={"query": "legacy-str-cat-complete"}
    )
    assert response.status_code == 200, response.text
    assert any(row["title"] == "旧导入的归档标题" for row in response.json()), response.json()


@pytest.mark.asyncio
async def test_legacy_columns_survive_markdown_export(
    client, db_session, admin_user, admin_headers
):
    """导出把 title/content/category/tag 四个 JSON 列一次性摊进 frontmatter。"""
    from datetime import datetime

    category = Category(name="旧导入的分类", slug="legacy-str-cat-export", color="#444444")
    tag = Tag(name="旧导入的标签", slug="legacy-str-tag-export")
    db_session.add_all([category, tag])
    await db_session.commit()
    await db_session.refresh(category)
    await db_session.refresh(tag)
    await _make_legacy_archived_row(
        db_session,
        admin_user,
        category,
        "legacy-str-export",
        datetime(2026, 3, 17, 9, 30),
        tags=[tag],
    )

    response = await client.get("/api/admin/export/markdown", headers=admin_headers)
    assert response.status_code == 200, response.text
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        md = zf.read("legacy-str-export.md").decode("utf-8")
    assert "title: 旧导入的归档标题" in md, md[:300]
    assert "category: 旧导入的分类" in md, md[:300]
    assert "旧导入的标签" in md, md[:300]


class TestReprsTolerateLegacyShapes:
    """`__repr__` 会出现在日志与断言输出里——记录一条日志不该变成 500。"""

    def test_post_and_taxonomy_reprs(self):
        assert "旧标题" in repr(Post(title="旧标题", id=1))
        assert "旧分类" in repr(Category(name="旧分类", id=1))
        assert "旧标签" in repr(Tag(name="旧标签", id=1))

    def test_dict_shapes_still_render(self):
        assert "中文标题" in repr(Post(title={"zh": "中文标题"}, id=2))
        assert repr(Post(title=None, id=3)).count("Untitled") == 1

    def test_other_model_reprs(self):
        assert "旧活动" in repr(Activity(content="旧活动", id=1, type="post.published"))
        assert "旧页面" in repr(Page(title="旧页面", id=1))
        assert "旧系列" in repr(PostSeries(title="旧系列", id=1))
        assert "旧导航" in repr(Navigation(title="旧导航", id=1))
        assert "旧链接" in repr(FriendLink(name="旧链接", id=1))
        assert "旧占位" in repr(SearchPlaceholder(text="旧占位", id=1))
        assert "旧通知" in repr(Notification(title="旧通知", id=1))
