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

from backend.scripts.gen_api_coverage import BEGIN_MARK, DOC_PATH, END_MARK, build_block

REPO = Path(__file__).resolve().parents[1]


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
