"""站内搜索的多语言召回（批次 #36）。

线上实测：`GET /api/blog/posts?search=コンポジション` 返回 **0 条**，而 `/ja` 页面上这篇的标题
正是「Vue 3 コンポジション API 実践」；同样搜 `組合式` 也搜不到繁体内容。原因很朴素——公开列表口
的 SQL 谓词只写了 `zh` 与 `en` 两档。对日语与繁体访客来说，**站内搜索看不见用他们语言写的内容**：
内容存在、URL 存在、页面能打开，只有搜索这一个入口把它藏了。第二条同型坑是历史裸字符串行：
`col["zh"]` 对一个 JSON 字符串永远返回 NULL，于是批次 #34 那批"列表里看得见"的数据在搜索里彻底
不存在。

所以本文件的断言分三层，缺一层都算没修完：

1. **每一种语言都能单独召回**（参数化跑在 `LANGUAGE_CODES` 上，而不是写死四语清单）。新增第五种
   语言时（AGENTS.md §14 要同步四处）如果漏了搜索，这一条会自己变红——把"静默漏一种语言"变成
   一次红测试，是本批最大的收益。
2. **三个被搜的字段各自成立**（title / excerpt / content）：只把正文接进谓词而摘要漏了，表现是
   "标题搜得到、内容搜不到"，用户会判成搜索坏了。
3. **谓词不 over-match**：整列文本兜底会把 JSON 的**键名**当成命中（搜 `zh_Hant` 命中每一行），
   所以兜底只允许作用于非对象形态的行。这一条是反证——它钉住的是那个 `{%` 闸门，不是运气。

外加两条守卫：`i18n_contains` 必须在 PG 与 SQLite 两种方言下都编译得过（`astext` 是 PG 方言专有
扩展，公开口当年用的 `cast(col[lang], String)` 两边都能编译）；全仓不得再出现手写的按语言 `ilike`
谓词（口径单源在 `backend/utils/i18n_query.py`）。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import JSON
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.i18n import LANGUAGE_CODES
from backend.models.blog import Post
from backend.models.user import User

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"


# 每个 token 只属于一种语言：`i18nsearchzhtoken` 不会是 `i18nsearchzh_hanttoken` 的子串。
# 库里存**大写**形态、搜索用**小写**形态，顺带把 `ilike`（不是 `like`）这条也钉住——英文站点的
# 检索词大小写由访客决定，用 LIKE 会把 "vue" 判成 0 条。
def _token(code: str) -> str:
    return f"i18nsearch{code}token"


def _stored(code: str) -> str:
    return f"Probe {_token(code).upper()} article"


async def _seed(
    db: AsyncSession,
    author: User,
    *,
    slug: str,
    title: object,
    content: object,
    excerpt: object,
) -> Post:
    post = Post(
        title=title,  # type: ignore[arg-type]
        content=content,  # type: ignore[arg-type]
        excerpt=excerpt,  # type: ignore[arg-type]
        slug=slug,
        author_id=author.id,
        status="published",
        visibility="public",
        allow_comments=True,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


def _page(payload: dict) -> dict:
    """兼容 `{success, data: {...}}` 信封与裸 PaginatedResponse 两种形态。"""
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"] or {}
    return payload or {}


async def _search(client: AsyncClient, term: str) -> tuple[int, set[str]]:
    response = await client.get(f"/api/blog/posts?search={term}&page_size=50")
    assert response.status_code == 200, response.text
    page = _page(response.json())
    items = page.get("items") or []
    return int(page.get("total") or 0), {row.get("slug") for row in items if row.get("slug")}


class TestEveryLocaleIsRecalled:
    """每种语言单独放进标题都要搜得到——这是线上那个 0 条的直接反证。"""

    @pytest.mark.parametrize("code", LANGUAGE_CODES)
    async def test_only_this_locale_title_is_found(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User, code: str
    ):
        title = {code: _stored(code)}
        await _seed(
            db_session,
            test_user,
            slug=f"locale-{code}",
            title=title,
            content={code: "普通正文，不含检索标记。"},
            excerpt={code: "普通摘要。"},
        )
        total, slugs = await _search(client, _token(code))
        assert "locale-" + code in slugs, (
            f"只有 {code} 一档语言的内容搜不到（total={total}，结果={slugs}）："
            "搜索谓词的语言清单必须跟随 LANGUAGE_CODES"
        )

    async def test_ja_only_title_is_found_named_repro(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        """把线上那条复现原样钉住：日语标题用日语词搜。"""
        await _seed(
            db_session,
            test_user,
            slug="ja-repro",
            title={"ja": "Vue 3 コンポジション API 実践"},
            content={"ja": "Composition API の実践記録"},
            excerpt={"ja": "日本語の抜粋"},
        )
        _total, slugs = await _search(client, "コンポジション")
        assert "ja-repro" in slugs, slugs


class TestEverySearchedFieldIsRecalled:
    """title / excerpt / content 三档各自命中一次——只接两个字段是半个功能。"""

    @pytest.mark.parametrize("field", ["title", "excerpt", "content"])
    async def test_only_this_field_holds_the_term(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User, field: str
    ):
        # 用离默认语言最远的一档（zh_Hant），这样这一条同时也覆盖了语言维度。
        marker = _stored("zh_Hant")
        values: dict[str, object] = {
            "title": {"zh_Hant": "與標記無關的標題"},
            "excerpt": {"zh_Hant": "與標記無關的摘要"},
            "content": {"zh_Hant": "與標記無關的正文"},
        }
        values[field] = {"zh_Hant": marker}
        await _seed(
            db_session,
            test_user,
            slug=f"field-{field}",
            title=values["title"],
            content=values["content"],
            excerpt=values["excerpt"],
        )
        _total, slugs = await _search(client, _token("zh_Hant"))
        assert f"field-{field}" in slugs, f"标记只在 {field} 里，却搜不到：{slugs}"


class TestBareStringRowsAreRecalled:
    """裸字符串的历史行：列表里看得见，搜索里也必须看得见。

    `col["zh"]` 对 JSON 字符串返回 NULL，所以这一档完全靠"整列文本"那半条谓词。
    """

    async def test_bare_string_title_is_found(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        await _seed(
            db_session,
            test_user,
            slug="bare-string",
            title=_stored("en"),
            content={"zh": "这是内容"},
            excerpt={"zh": "这是摘要"},
        )
        _total, slugs = await _search(client, _token("en"))
        assert "bare-string" in slugs, (
            f"裸字符串标题没被召回（{slugs}）：同一行在列表与详情页都能打开，只搜不到就是 bug"
        )


class TestPredicateDoesNotOverMatch:
    """兜底整列文本不得把 JSON 的键名当成命中。

    去掉 `{%` 闸门后，`search=zh_Hant` 会匹配每一行（每个 title 对象都有这个键）——假阳性
    淹没真实结果，用户看到的是"随便搜什么都有几百条"。
    """

    async def test_language_key_name_matches_nothing(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        await _seed(
            db_session,
            test_user,
            slug="four-locale-object",
            title={code: f"标题 {idx}" for idx, code in enumerate(LANGUAGE_CODES)},
            content={code: f"正文 {idx}" for idx, code in enumerate(LANGUAGE_CODES)},
            excerpt={code: f"摘要 {idx}" for idx, code in enumerate(LANGUAGE_CODES)},
        )
        listed_total, listed = await _search(client, "")
        assert "four-locale-object" in listed, listed

        for key in LANGUAGE_CODES:
            total, slugs = await _search(client, key)
            assert total == 0 and not slugs, (
                f"search={key} 命中了 {slugs}：JSON 键名被当成正文匹配，"
                "整列兜底必须只作用于非对象形态的行"
            )


class TestDialectCompiles:
    """同一份谓词要在生产 PG 与测试 SQLite 上都编译得过。

    `col[lang].astext` 是 PG 方言专有扩展，SQLite 下直接报错；当年三个消费点两种写法，
    等于"改一次口径要动九处、漏一处就是两个入口结果不同"。
    """

    def test_i18n_contains_compiles_on_both_dialects(self):
        from backend.utils.i18n_query import i18n_contains

        # 语言键是 bindparam，要 literal_binds 才看得到实际档位（守卫自己第一次就栽在这里：
        # 直接断 `"zh" in sql` 永远红，因为 SQL 里只有 `%(title_1)s`）。
        plain = str(i18n_contains(Post.title, "%x%").compile(dialect=postgresql.dialect()))
        assert plain.count("ILIKE") == len(LANGUAGE_CODES) + 1, plain  # 每语一档 + 整列兜底
        assert "NOT LIKE" in plain, plain  # 整列兜底只作用于非对象形态的行
        bound = str(
            i18n_contains(Post.title, "%x%").compile(
                dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
            )
        )
        for code in LANGUAGE_CODES:
            assert f"'{code}'" in bound, f"PG SQL 里没有 {code} 这一档：{bound}"
        # SQLite 侧同一表达式必须照常可编译，避免修 PG 把开发库改炸
        lite = str(i18n_contains(Post.title, "%x%").compile(dialect=sqlite.dialect()))
        assert "LIKE" in lite, lite
        assert "->" not in lite, lite  # 不能有 PG 专有运算符漏到 SQLite


class TestNoHandInlinedSearchPredicate:
    """口径单源守卫：全仓不得再出现"自己拼一份按语言的 ilike"。"""

    @staticmethod
    def _json_attrs() -> set[tuple[str, str]]:
        import backend.main  # noqa: F401  导入即注册全部模型（含定义在 api/*.py 里的表）
        from backend.core.database import Base

        return {
            (mapper.class_.__name__, col.name)
            for mapper in Base.registry.mappers
            for col in mapper.class_.__table__.columns
            if isinstance(col.type, JSON)
        }

    @staticmethod
    def _sources() -> list[Path]:
        skip = {"i18n_query.py"}
        out = []
        for path in sorted(BACKEND_DIR.rglob("*.py")):
            if path.name in skip or "__pycache__" in path.parts:
                continue
            if "migrations" in path.parts:  # 迁移里的 astext_type 是类型声明，不是查询
                continue
            out.append(path)
        return out

    def test_no_json_column_is_iliked_without_the_single_source_helper(self):
        attrs = self._json_attrs()
        assert attrs, "元数据里应当存在 JSON 列——本守卫失去对象说明口径变了，需同步修改"
        lang_key = re.compile(r"""\[[\"'](?:zh|en|ja|zh_Hant)[\"']\]""")
        violations: list[str] = []
        for path in self._sources():
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1
            ):
                if line.lstrip().startswith("#"):
                    continue
                model_col = re.findall(r"\b([A-Z][A-Za-z]*)\.([a-z_][a-z0-9_]*)\.ilike\(", line)
                for model, col in model_col:
                    if (model, col) in attrs:
                        violations.append(
                            f"{path.name}:{lineno} JSON 列 {model}.{col} 直接 ilike（PG 下无操作符）"
                        )
                if lang_key.search(line) and ".ilike" in line:
                    violations.append(
                        f"{path.name}:{lineno} 手写了按语言的 ilike 谓词，请走 i18n_contains"
                    )
        assert not violations, "；".join(violations)

    def test_no_pg_only_astext_extension_outside_migrations(self):
        offenders = []
        for path in self._sources():
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1
            ):
                stripped = line.lstrip()
                if stripped.startswith("#") or "astext_type" in line:
                    continue
                if ".astext" in line:
                    offenders.append(f"{path.name}:{lineno}")
        assert not offenders, (
            f"`.astext` 是 PG 方言专有扩展，SQLite 下报错：{offenders}；查询请走 i18n_contains"
        )

    def test_every_search_consumer_imports_the_helper(self):
        """三个已知消费点必须还在吃这份单源（漏一个就是"同一个关键词两个入口结果不同"）。"""
        consumers = {
            "api/blog.py": 3,
            "api/post_series.py": 3,
            "repositories/post.py": 3,
        }
        for rel, minimum in consumers.items():
            text = (BACKEND_DIR / rel).read_text(encoding="utf-8")
            assert "from backend.utils.i18n_query import i18n_contains" in text, rel
            assert text.count("i18n_contains(") >= minimum, (
                f"{rel} 只调了 {text.count('i18n_contains(')} 次 i18n_contains，"
                f"少于 {minimum}（title/excerpt/content 或语言档缺了一个）"
            )
