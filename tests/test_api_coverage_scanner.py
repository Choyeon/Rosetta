"""覆盖度汇总表必须由扫描器生成，且与当前源码一致。

这张表的历史失败方式不是"数字不准"，而是**同一个文档里存在两套永不重算的数字**：
2026-09-26 的手工快照按"合计"行累加，45 条模块行按各轮手改增量各自漂移
（`messages` 行长期写 0 ✅，而下面明细写「已接入 5 条」），于是拿它当缺口清单来排
下一轮接线工作，会去接一条早就接完的口子。

现在表由 `backend/scripts/gen_api_coverage.py` 生成在 `<!-- COVERAGE-AUTO -->` 区块里，
这条守卫只做一件事：**区块内容 == 当场重扫的结果**。改接口或接线后不重算就是 CI 失败，
修复动作是执行 --write，不是改断言。

区块之外的那些"局部更新""等价数字"历史段落已经作废（见文档开头的口径说明），
本测试不核对它们。
"""

from pathlib import Path

import pytest

from backend.scripts.gen_api_coverage import (
    BEGIN_MARK,
    DOC_PATH,
    END_MARK,
    _candidate_paths,
    _context_of,
    _verbs_at,
    _verbs_for_const,
    build_block,
)

REPO = Path(__file__).resolve().parents[1]


def _ctx(text: str, literal: str) -> tuple[str, str | None, str | None]:
    """在合成片段里定位那条字面量并问它"在干什么"。

    扫描器拿到的是 `(['"])(/…)\\1` 的 match，`start()` 落在**开引号那一位**，这里保持同口径。
    """
    return _context_of(text, text.index(literal))


def test_scanner_script_exists_in_the_place_the_doc_advertises():
    """文档里的重算命令必须指向真实存在的脚本，否则下一个人只会手改数字。"""
    assert (REPO / "backend" / "scripts" / "gen_api_coverage.py").is_file()


def test_coverage_doc_carries_the_auto_block():
    text = DOC_PATH.read_text(encoding="utf-8")
    assert BEGIN_MARK in text and END_MARK in text, (
        "API_COVERAGE.md 里没有自动区块标记；汇总表又变回手改的了"
    )


def test_auto_block_matches_a_fresh_scan():
    text = DOC_PATH.read_text(encoding="utf-8")
    stored = text.split(BEGIN_MARK, 1)[1].split(END_MARK, 1)[0]
    fresh = build_block().split(BEGIN_MARK, 1)[1].split(END_MARK, 1)[0]
    # 行首尾空白由 _render 负责（区块后恰好一个空行），这里只比内容
    assert [ln.rstrip() for ln in stored.strip().splitlines()] == [
        ln.rstrip() for ln in fresh.strip().splitlines()
    ], (
        "覆盖度汇总表与扫描结果不一致：执行 "
        "PYTHONPATH=. python backend/scripts/gen_api_coverage.py --write 重算后再提交"
    )


@pytest.mark.parametrize("needle", ["gen_api_coverage.py", "勿手改"])
def test_block_documents_its_own_regeneration(needle):
    """区块要能自解释：看的人不需要先读这份测试才知道怎么刷新。"""
    assert needle in DOC_PATH.read_text(encoding="utf-8")


# ---- 消费点判据（"隔了一层传 URL" 的三种真实写法 + 两种必须继续判未消费）----
# 这些形态每一条都对应过一次误报：判据改坏不会让本地任何测试变红，只会让缺口清单失真，
# 于是下一轮拿着假缺口去接一条早就接完的口子（或更糟——把没接线的算成已覆盖）。


def test_ternary_branch_inside_a_request_call_is_consumed():
    text = (
        "const path = isMd ? '/admin/export/markdown' : '/admin/export/posts'\n"
        "    const blob = await apiFetch<Blob>(path, {\n      method: 'GET'\n    })"
    )
    assert _ctx(text, "'/admin/export/markdown'")[0] == "fetch"
    assert _ctx(text, "'/admin/export/posts'")[0] == "fetch"
    # 动词从使用点读回来，不在声明上猜
    anchor = text.index("'/admin/export/posts'")
    assert _verbs_for_const(text, "path", anchor) == {"get"}


def test_computed_url_const_is_consumed_via_its_use_site():
    """个人中心：`const listUrl = computed(...)` 交给 `useAPI(() => listUrl.value)`。"""
    text = (
        "const listUrl = computed(() =>\n"
        "  tab.value === 'favorites' ? '/favorites' : `/blog/users/me/${tab.value}`\n"
        ")\n"
        "const {\n  data\n} = useAPI<AccountList>(() => listUrl.value, {\n  query: listQuery\n})"
    )
    ctx = _ctx(text, "'/favorites'")
    assert ctx[0] == "fetch" and ctx[1] == "listUrl"
    assert _verbs_for_const(text, "listUrl", text.index("'/favorites'")) == {"get"}


def test_navigation_table_is_still_not_coverage():
    """后台菜单表里的 `path: '/admin/posts'` 长得和 API 路径一模一样，但不是请求点。"""
    text = (
        "const menu = ref([\n  { path: '/admin/posts', label: '文章' },\n"
        "  { path: '/admin/pages', label: '页面' }\n])"
    )
    assert _ctx(text, "'/admin/posts'")[0] == "none"
    assert _ctx(text, "'/admin/pages'")[0] == "none"


def test_declared_const_nobody_fetches_is_not_coverage():
    """变量名对得上，但全文没有任何请求封装用它——仍须判未消费。"""
    text = (
        "const target = mode === 'a' ? '/admin/unused' : '/admin/other'\n\n"
        "function label() {\n  return target.value\n}"
    )
    assert _ctx(text, "'/admin/unused'")[0] == "none"


def test_nested_template_query_keeps_the_parent_path():
    """Nitro 侧 `` `/blog/rss${qs ? `?${qs}` : ''}` ``：反引号嵌套不能把父路径丢掉。"""
    assert "/api/blog/rss" in _candidate_paths("/blog/rss${qs ? `?${qs}` : ''}")
    # 路径参数形态不许截出"上一级集合口"（`/admin/themes/${slug}/mods` ≠ /api/admin/themes）
    assert _candidate_paths("/admin/themes/${slug}/mods") == {"/api/admin/themes/*/mods"}


def test_generic_body_with_string_literal_types_still_reveals_the_callee():
    """`request<{ issues: Array<{ level: 'error' | 'warn' }> }>('/oobe/preflight', …)`。

    泛型体里带引号曾被当成"这不是泛型"，POST /oobe/preflight 因此漏判一轮。
    """
    text = (
        "  return request<{\n"
        "      issues?: Array<{ level: 'error' | 'warn' }>\n"
        "    }>('/oobe/preflight', {\n"
        "      method: 'POST', body\n"
        "    })"
    )
    assert _ctx(text, "'/oobe/preflight'")[:1] == ("fetch",)
    anchor = text.index("'/oobe/preflight'")
    assert _verbs_at(text, anchor, anchor + len("'/oobe/preflight'"), "request") == {"post"}
