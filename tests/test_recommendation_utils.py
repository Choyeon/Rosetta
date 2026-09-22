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
