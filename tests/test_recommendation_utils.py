"""
推荐算法工具函数测试

覆盖 normalize_text / tokenize / build_tf / compute_cosine_similarity /
jaccard / exponential_decay / heat_score 等纯函数。
"""

from collections import Counter
from datetime import datetime, timedelta

import pytest

from backend.services.recommendation import (
    build_tf,
    compute_cosine_similarity,
    exponential_decay,
    heat_score,
    jaccard,
    normalize_text,
    score_search_docs,
    score_similar_posts,
    tokenize,
)


def test_normalize_text_empty():
    assert normalize_text(None) == ""
    assert normalize_text("") == ""


def test_normalize_text_strips_markdown():
    raw = "# Title\nSome **bold** text with `code` and [link](http://x.com)"
    result = normalize_text(raw)
    assert "#" not in result
    assert "**" not in result
    assert "`" not in result
    assert "http://x.com" not in result
    assert "title" in result
    assert "bold" in result


def test_normalize_text_strips_html_and_images():
    raw = "<p>Hello</p> ![alt](img.png) ```code block```"
    result = normalize_text(raw)
    assert "<p>" not in result
    assert "img.png" not in result
    assert "code block" not in result
    assert "hello" in result


def test_normalize_text_nfkc_and_lower():
    result = normalize_text("ＨＥＬＬＯ　Ｗｏｒｌｄ")
    assert result == "hello world"


def test_tokenize_empty():
    assert tokenize("") == []


def test_tokenize_english_words():
    tokens = tokenize("hello world test")
    assert "hello" in tokens
    assert "world" in tokens
    assert "test" in tokens
    # 单字符不应被收录
    tokens2 = tokenize("a b c")
    assert tokens2 == []


def test_tokenize_cjk_bigram():
    tokens = tokenize("你好世界")
    assert "你好" in tokens
    assert "好世" in tokens
    assert "世界" in tokens


def test_tokenize_mixed():
    tokens = tokenize("Python 编程")
    assert "Python" in tokens
    assert "编程" in tokens


def test_build_tf_counts():
    tf = build_tf(["a", "b", "a", "c"])
    assert tf["a"] == 2
    assert tf["b"] == 1
    assert tf["c"] == 1


def test_cosine_similarity_empty():
    assert compute_cosine_similarity(Counter(), Counter({"a": 1}), {}) == 0.0
    assert compute_cosine_similarity(Counter({"a": 1}), Counter(), {}) == 0.0


def test_cosine_similarity_identical():
    tf = Counter({"hello": 2, "world": 1})
    idf = {"hello": 1.0, "world": 1.0}
    sim = compute_cosine_similarity(tf, tf, idf)
    assert sim == pytest.approx(1.0, abs=1e-6)


def test_cosine_similarity_orthogonal():
    tf_a = Counter({"hello": 1})
    tf_b = Counter({"world": 1})
    idf = {"hello": 1.0, "world": 1.0}
    assert compute_cosine_similarity(tf_a, tf_b, idf) == 0.0


def test_cosine_similarity_zero_idf():
    tf_a = Counter({"hello": 1})
    tf_b = Counter({"hello": 1})
    idf = {"hello": 0.0}
    assert compute_cosine_similarity(tf_a, tf_b, idf) == 0.0


def test_jaccard_empty():
    assert jaccard(set(), {1, 2}) == 0.0
    assert jaccard({1, 2}, set()) == 0.0


def test_jaccard_identical():
    assert jaccard({1, 2, 3}, {1, 2, 3}) == 1.0


def test_jaccard_partial():
    assert jaccard({1, 2, 3}, {2, 3, 4}) == pytest.approx(2 / 4)


def test_jaccard_disjoint():
    assert jaccard({1, 2}, {3, 4}) == 0.0


def test_exponential_decay_none():
    assert exponential_decay(None) == 0.4


def test_exponential_decay_recent():
    now = datetime.now()
    score = exponential_decay(now)
    # 刚发布的文章得分应接近 1.0
    assert score > 0.9


def test_exponential_decay_old():
    old = datetime.now() - timedelta(days=365)
    score = exponential_decay(old)
    # 一年前的文章得分应很低
    assert score < 0.3


def test_heat_score_zero():
    assert heat_score(0, 0, 0) == 0.0


def test_heat_score_high():
    score = heat_score(10000, 500, 200)
    assert score > 0.8
    assert score <= 1.0


def test_heat_score_clamped():
    # 极端值不应超过 1.0
    score = heat_score(10**9, 10**9, 10**9)
    assert score <= 1.0
    assert score >= 0.0


# ────────────── 纯计算打分（原先在事件循环里跑，现由 worker 线程执行）──────────────
# 这两个函数是 search_rerank / get_similar_posts 的算法本体：
# 候选集最多 300 篇全文，分词+余弦的耗时会随站点文章数增长，
# 因此服务层必须先拍平数据、再 asyncio.to_thread 调用它们。此处锁住打分语义。


def test_score_search_docs_prefers_title_match_over_content_match():
    docs = [
        ("fastapi 性能 优化 实战", "", "", []),  # 命中 title（×3.0）
        ("无关 标题", "", "正文里提到 一次 fastapi", []),  # 命中 content（×1.0）
    ]
    scores = score_search_docs("fastapi", docs)
    assert scores[0] > scores[1] > 0


def test_score_search_docs_tag_hit_counts_and_absent_term_is_zero():
    docs = [("标题", "摘要", "正文", ["kubernetes"]), ("标题二", "摘要二", "正文二", [])]
    scores = score_search_docs("kubernetes", docs)
    assert scores[0] > 0
    assert scores[1] == 0.0


def test_score_search_docs_empty_inputs():
    assert score_search_docs("", [("a", "b", "c", ["d"])]) == [0.0]
    assert score_search_docs("rust", []) == []


def test_score_similar_posts_orders_by_text_then_tag_overlap():
    anchor_text = "postgres 索引 与 慢查询 优化"
    docs = [
        (1, "postgres 索引 优化 慢查询", {7}, 3, None, None),  # 文本 + 标签 + 分类
        (2, "前端 构建 打包", {7}, 3, None, None),  # 仅标签/分类
        (3, "完全无关 的 话题", set(), 9, None, None),  # 都不沾
    ]
    scored = score_similar_posts(anchor_text, {7}, 3, docs, {})
    assert [cid for cid, _ in scored] == [1, 2, 3]
    assert scored[0][1] > scored[1][1] > scored[2][1]


def test_score_similar_posts_heat_breaks_tie():
    anchor_text = "共同 词汇 若干"
    docs = [
        (1, "共同 词汇 若干", set(), None, None, None),
        (2, "共同 词汇 若干", set(), None, None, None),
    ]
    cold = score_similar_posts(anchor_text, set(), None, docs, {1: (0, 0, 0), 2: (0, 0, 0)})
    hot = score_similar_posts(anchor_text, set(), None, docs, {1: (0, 0, 0), 2: (9999, 999, 999)})
    assert [cid for cid, _ in cold] == [1, 2]  # 无热度差异时保持输入顺序（稳定排序）
    assert [cid for cid, _ in hot] == [2, 1]  # 热度高的排前面
