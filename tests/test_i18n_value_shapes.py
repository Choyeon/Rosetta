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

import pytest

from backend.core.i18n import get_i18n_value
from backend.models.blog import Post


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
