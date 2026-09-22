"""
阅读时长计算工具

将阅读时长计算逻辑从 ``backend/api/blog.py`` 抽取到独立工具模块，
供服务层（创建/更新文章时持久化）与 API 层（兼容回退）共用。

设计要点：
- ``calculate_reading_time`` 基于中文汉字数 + 英文单词数估算分钟数
- ``compute_reading_time_from_content`` 处理多语言 content dict，
  优先取 zh，其次 en，最后回退到首个非空语言
"""

import math
import re


def calculate_reading_time(content: str) -> int:
    """计算纯文本的阅读时间（分钟）。

    中文按 300 字/分钟、英文按 150 词/分钟估算，最少 1 分钟。
    """
    chinese_chars = len(re.findall(r"[\u4e00-\u9fa5]", content))
    english_words = len(re.findall(r"[a-zA-Z0-9]+", content))
    minutes = (chinese_chars / 300) + (english_words / 150)
    return max(1, math.ceil(minutes))


def compute_reading_time_from_content(content: dict | None) -> int:
    """从多语言 content dict 计算阅读时间。

    优先级：zh → en → 首个非空语言。
    用于在创建/更新文章时持久化 ``reading_time``，列表接口即可 defer(content) 不加载大字段。
    """
    if not isinstance(content, dict) or not content:
        return 1
    for lang in ("zh", "en"):
        text = content.get(lang)
        if isinstance(text, str) and text:
            return calculate_reading_time(text)
    for text in content.values():
        if isinstance(text, str) and text:
            return calculate_reading_time(text)
    return 1
