"""裸字符串 JSON 列在**响应模型侧**的 500 面（批次 #34）。

`title` / `name` / `content` 这些列声明的是 JSON，类型注解写的是 `dict[str, str]`，而库里真的会
躺 `name="技术"` 这种单语行（导入工具、早期写入路径、直接写库都留得下）。
`core/i18n.py::get_i18n_value` 早就认这一支，**Pydantic 侧没认**：裸字符串进 `dict[str, str]`
字段直接 ValidationError，FastAPI 把它当响应序列化失败 → 整口 500。文章详情那一族已在调用点
按 isinstance 归一（`test_i18n_value_shapes.py` 钉着），这一轮把其余口收到同一个闸门后面：
分类列表、标签列表、导航、独立页详情、友链、系列列表、称号列表。

三条口径：

1. 修法用**单源类型**（`backend/schemas/_i18n_dict.py::I18nDict`）而不是在 8 个调用点各写一遍
   isinstance——漏一处的表现不是报错，而是某个周末一条旧数据让整口挂掉。
2. 折成 `{默认语言: 原文}` 而不是四语复制：正文可能几 MB，四份拷贝把响应体撑大四倍；
   前后端两边都有"当前语言取不到就回退"的链，观测到的文本与折之前完全一致。
3. 断言不只看 200，还看**归一后的形态**（`{"zh": 原文}`）。只断 200 会放过另一种坏法：
   字段被整个丢掉、或降级成空 dict——接口是活了，内容没了。

`/api/pages/{slug}` 那条额外钉住调用点的 `.items()`：正文是裸字符串时它先 `AttributeError`，
schema 侧的闸门救不到它，必须同一条 `as_i18n_dict` 在遍历前归一。

称号走 `GET /api/admin/titles`（staff）而不是留言板：留言板那条口要先穿过 `entry.user.title` 关系
加载才拿得到徽章，测的是"关系有没有预加载"这件事，混进来会让这条用例红了不知道修哪个洞。

响应缓存：分类/标签/导航/友链/系列都是带 TTL 的公开口，fixture 写行之前键位可能已被别的用例
暖好，所以每次打口前先清一遍——否则"这一行在场"是一次假红，而"没 500"是一次假绿。
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import invalidate_cache
from backend.core.i18n import DEFAULT_LANGUAGE
from backend.models.blog import Category, Post, Tag
from backend.models.core import FriendLink, Navigation, Page
from backend.models.post_series import PostSeries
from backend.models.user import User, UserTitle
from backend.schemas._i18n_dict import as_i18n_dict

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
SCHEMAS_DIR = BACKEND_DIR / "schemas"

LEGACY_CATEGORY = "旧导入的分类名"
LEGACY_TAG = "旧导入的标签名"
LEGACY_NAV = "旧导入的导航名"
LEGACY_PAGE_TITLE = "旧导入的页面标题"
LEGACY_PAGE_BODY = "旧导入的页面正文等待渲染管线逐语言处理"
LEGACY_FRIEND = "旧导入的友链名"
LEGACY_SERIES = "旧导入的系列名"
LEGACY_TITLE = "旧导入的称号名"


def folded(text: str) -> dict[str, str]:
    """归一后的唯一形态：单语 dict 挂在默认语言下。"""
    return {DEFAULT_LANGUAGE: text}


async def _clear_read_caches() -> None:
    for pattern in (
        "categories",
        "tags",
        "navigations",
        "friend_links",
        "series",
        "pages",
        "page",
        "posts",
        "post:",
        "settings_public",
    ):
        await invalidate_cache(pattern)


def _row_by(items: list[dict[str, Any]], key: str, value: Any) -> dict[str, Any]:
    """按字段值取自己那一行；取不到就先红，别退化成"列表里没有＝没测到"。"""
    for item in items:
        if item.get(key) == value:
            return item
    raise AssertionError(f"列表里没有 {key}={value!r} 这一行：{items}")


async def _get_ok(client: AsyncClient, path: str, headers: dict | None = None) -> Any:
    """打口并钉住"没 500"；返回解析后的 body。"""
    await _clear_read_caches()
    response = await client.get(path, headers=headers)
    assert response.status_code == 200, f"{path} → {response.status_code} {response.text[:200]}"
    return response.json()


def _rows_of(body: Any) -> list[dict[str, Any]]:
    """列表口有两种形态：裸 list（navigations / friend-links / titles / series）与 Paginated。"""
    if isinstance(body, list):
        return body
    data = body.get("data", body)
    return data if isinstance(data, list) else data.get("items", [])


class TestCoercionHelper:
    """闸门本体的三种入参——其余用例证明它接上了，这几条证明它折得对。"""

    def test_bare_string_folds_into_default_language(self):
        assert as_i18n_dict("单语标题") == {DEFAULT_LANGUAGE: "单语标题"}

    def test_blank_string_folds_into_empty_dict(self):
        # 空白串的语义是"没有内容"，不是"默认语言下躺着一串空白"
        assert as_i18n_dict("   ") == {}

    def test_dict_and_none_pass_through(self):
        data = {"zh": "中文", "en": "English"}
        assert as_i18n_dict(data) is data
        assert as_i18n_dict(None) is None


class TestLegacyRowsDoNotFiveHundred:
    async def test_category_list(self, client: AsyncClient, db_session: AsyncSession):
        slug = "legacy-i18n-cat"
        db_session.add(Category(name=LEGACY_CATEGORY, slug=slug, color="#111111"))
        await db_session.commit()

        rows = _rows_of(await _get_ok(client, "/api/blog/categories"))
        assert _row_by(rows, "slug", slug)["name"] == folded(LEGACY_CATEGORY)

    async def test_tag_list(self, client: AsyncClient, db_session: AsyncSession):
        slug = "legacy-i18n-tag"
        db_session.add(Tag(name=LEGACY_TAG, slug=slug))
        await db_session.commit()

        rows = _rows_of(await _get_ok(client, "/api/blog/tags"))
        assert _row_by(rows, "slug", slug)["name"] == folded(LEGACY_TAG)

    async def test_navigation_list(self, client: AsyncClient, db_session: AsyncSession):
        url = "/legacy-i18n-nav"
        nav = Navigation(title=LEGACY_NAV, url=url, location="header", order=99)
        db_session.add(nav)
        await db_session.commit()

        rows = _rows_of(await _get_ok(client, "/api/navigations?location=header"))
        assert _row_by(rows, "url", url)["title"] == folded(LEGACY_NAV)

    async def test_page_detail_renders_the_legacy_body(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """两条洞叠在同一条口上：`PageResponse.title` 的 schema 校验 + `content.items()`。"""
        slug = "legacy-i18n-page"
        page = Page(
            title=LEGACY_PAGE_TITLE,
            slug=slug,
            content=LEGACY_PAGE_BODY,
            status="published",
        )
        db_session.add(page)
        await db_session.commit()

        body = await _get_ok(client, f"/api/pages/{slug}")
        assert body["title"] == folded(LEGACY_PAGE_TITLE)
        # 渲染管线逐语言跑：折成单语 dict 后仍要产出**默认语言**那一份正文
        content = body["content"]
        assert isinstance(content, dict), f"正文没有归一成 dict：{content!r}"
        assert LEGACY_PAGE_BODY in "".join(content.values())

    async def test_friend_link_list(self, client: AsyncClient, db_session: AsyncSession):
        url = "https://legacy-i18n.example.com"
        link = FriendLink(name=LEGACY_FRIEND, url=url, status="approved", is_active=True, order=99)
        db_session.add(link)
        await db_session.commit()

        rows = _rows_of(await _get_ok(client, "/api/friend-links"))
        assert _row_by(rows, "url", url)["name"] == folded(LEGACY_FRIEND)

    async def test_series_list(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        slug = "legacy-i18n-series"
        series = PostSeries(title=LEGACY_SERIES, slug=slug, is_active=True, sort_order=99)
        db_session.add(series)
        await db_session.commit()
        # 列表口只收"有已发布文章"的系列，不挂一篇进去这条断言就是空转
        chapter = Post(
            title={"zh": "旧系列里的一篇文章"},
            slug="legacy-i18n-series-post",
            content={"zh": "正文"},
            status="published",
            author_id=test_user.id,
            series_id=series.id,
        )
        db_session.add(chapter)
        await db_session.commit()

        rows = _rows_of(await _get_ok(client, "/api/series"))
        assert _row_by(rows, "slug", slug)["title"] == folded(LEGACY_SERIES)

    async def test_title_list(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers
    ):
        db_session.add(UserTitle(name=LEGACY_TITLE, color="#123456"))
        await db_session.commit()

        # staff 口（`/api/admin/titles`）：不带 token 会先撞 401，那条断言就只是在测鉴权
        # 而不是测形态
        rows = _rows_of(await _get_ok(client, "/api/admin/titles", headers=admin_headers))
        names = [row["name"] for row in rows]
        assert folded(LEGACY_TITLE) in names, names


class TestSingleSourceGuard:
    """新增响应模型不得再对 i18n 字段声明裸 `dict[str, str]`。

    只扫 `backend/schemas/`：那里的 `*Response` 都是真挂到 `response_model=` 上的模型。
    api 文件里的 `*Doc` 模型按 §7.4 只进 OpenAPI 文档、运行时不校验，不在本守卫射程内
    （它们当中确有几位"看着像但不会 500"，扫进来只会教后来的人去改不会坏的东西）。
    """

    I18N_FIELDS = {
        "name",
        "title",
        "description",
        "content",
        "excerpt",
        "subtitle",
        "meta_title",
        "meta_description",
        "meta_keywords",
    }

    def _violations(self) -> list[str]:
        found: list[str] = []
        for path in sorted(SCHEMAS_DIR.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef) or not node.name.endswith("Response"):
                    continue
                for stmt in node.body:
                    if not isinstance(stmt, ast.AnnAssign) or not isinstance(
                        stmt.target, ast.Name
                    ):
                        continue
                    field = stmt.target.id
                    if field not in self.I18N_FIELDS:
                        continue
                    text = ast.unparse(stmt.annotation)
                    if "I18nDict" in text:
                        continue
                    if "dict[" in text:
                        found.append(f"{path.name}:{node.name}.{field} = {text}")
        return found

    def test_no_response_model_declares_a_bare_dict_for_i18n_fields(self):
        violations = self._violations()
        assert not violations, (
            "i18n 字段请用 backend.schemas._i18n_dict.I18nDict；"
            f"仍写着裸 dict 的响应模型：{violations}"
        )

    def test_the_shape_is_decided_in_exactly_one_module(self):
        # 归一函数只此一份：调用点再手写 isinstance 会变成两套口径互相漂移
        helpers = [p.name for p in (BACKEND_DIR / "schemas").glob("_i18n_dict*.py")]
        assert helpers == ["_i18n_dict.py"]
