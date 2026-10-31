"""阅读分钟数的单源契约（批次 #136）。

同一篇文章的「预计阅读 N 分钟」以前有三套算法：持久化列走
``utils/reading_time.calculate_reading_time``（汉字 300/分钟 + 英文词 150/分钟），
``PostLocalizedResponse._calculate_reading_time`` 自己写 ``len(content) // 500``
（把 Markdown 标记与半个词都当字数），详情页再按 380 字/分钟算第三遍。
表现是列表卡片 6 分钟、正文页 4 分钟，读者以为点开了另一篇。

现在两处出口都委托给持久化列那一个函数。这里钉三件事：
1. 出口函数与持久化算法对同一份正文给同一个数（含空正文的 1 分钟兜底）；
2. 旧的第二套公式不以任何形态留在后端（就地重算＝第四套算法）；
3. 列表/详情读的是列，不是正文 —— 列表口 ``defer(Post.content)``，
   正文根本不在载荷里，任何「读出来再算一遍」连输入都拿不到。
"""

import re
from pathlib import Path

from backend.schemas import PostLocalizedResponse
from backend.utils.reading_time import (
    calculate_reading_time,
    compute_reading_time_from_content,
)

BACKEND = Path(__file__).resolve().parents[1] / "backend"

SAMPLES = [
    "",
    "   ",
    "一两句中文",
    "汉字" * 300,
    "汉字" * 601,
    "word " * 150,
    "混合 content 与 english words 和中文汉字",
    "# 标题\n\n**加粗** 与 [链接](https://example.com) 的 Markdown 标记",
]


def test_outlet_matches_persisted_formula():
    """出口读数必须与写入侧持久化算法一致，否则卡片与详情页又会分叉。"""
    for text in SAMPLES:
        content = {"zh": text, "en": text, "ja": text, "zh_Hant": text}
        expected = compute_reading_time_from_content(content)
        assert PostLocalizedResponse._calculate_reading_time(text) == expected, text[:20]


def test_empty_content_is_one_minute_not_zero():
    """空正文给 1 分钟：卡片和详情页都不该显示「0 分钟阅读」。"""
    assert PostLocalizedResponse._calculate_reading_time("") == 1
    assert calculate_reading_time("") == 1
    assert compute_reading_time_from_content(None) == 1


def test_second_formula_never_comes_back():
    """``len(...) // 500`` 是漂移出来的第二套公式；就地重算一律视为回归。"""
    offenders = [
        str(path.relative_to(BACKEND))
        for path in sorted(BACKEND.rglob("*.py"))
        if re.search(r"len\([^()]*\)\s*//\s*500", path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_list_and_detail_outlets_read_the_column():
    """列表/详情出口取持久化列。"""
    blog = (BACKEND / "api" / "blog.py").read_text(encoding="utf-8")
    assert "reading_time=post.reading_time or 1" in blog
    assert "_reading_time = post.reading_time" in blog
    assert "reading_time=_reading_time or 1" in blog
    # 列表口 defer 正文：就地重算拿不到输入，这是「只能读列」的结构性理由
    assert re.search(r"defer\(\s*Post\.content", blog)
