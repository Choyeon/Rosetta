"""
内容审核 / 敏感词过滤模块

提供评论 / 留言等用户生成内容的黑白名单过滤。
- BLACKLIST: 命中直接拒绝 / 标记 spam
- GRAYLIST: 命中强制进入待审核 pending
"""

from dataclasses import dataclass

BLACKLIST = [
    "色情片",
    "黄色视频",
    "成人网站",
    "赌博平台",
    "线上赌场",
    "真人百家乐",
    "六合彩",
    "伟哥",
    "迷奸药",
    "枪支弹药",
    "毒品交易",
    "假币",
    "发票代开",
    "走私",
    "黑客破解",
    "加微群领资料",
    "兼职刷单",
    "包养上门",
    "裸聊直播",
    "porn",
    "casino",
    "gambling",
    "escort",
    "viagra",
    "cocaine",
    "counterfeit money",
    "fake id",
    "credit card dump",
    "hacking tool",
]


GRAYLIST = [
    "广告",
    "加群",
    "加微信",
    "加qq群",
    "私聊我",
    "联系我",
    "扫码加",
    "点此进入",
    "免费领",
    "点击领取",
    "关注公众号",
    "推广链接",
    "赚钱好项目",
    "月入过万",
    "advertisement",
    "sponsored",
    "dm me",
    "click here",
    "follow me",
    "check my profile",
]


@dataclass
class ModerationResult:
    """审核结果"""

    passed: bool
    level: str
    matched_words: list[str]

    @property
    def is_rejected(self) -> bool:
        return self.level == "black"

    @property
    def is_pending(self) -> bool:
        return self.level == "gray"


def moderate_text(text: str) -> ModerationResult:
    """
    审核一段文本是否命中敏感词。

    返回 ModerationResult:
    - level="black": 命中黑名单，应直接拒绝
    - level="gray": 命中灰名单，应强制 pending
    - level="ok": 一切正常
    """
    if not text:
        return ModerationResult(passed=True, level="ok", matched_words=[])

    lower = text.lower()
    original = text

    matched_black = [w for w in BLACKLIST if (w in original or w.lower() in lower)]
    if matched_black:
        return ModerationResult(
            passed=False,
            level="black",
            matched_words=matched_black,
        )

    matched_gray = [w for w in GRAYLIST if (w in original or w.lower() in lower)]
    if matched_gray:
        return ModerationResult(
            passed=True,
            level="gray",
            matched_words=matched_gray,
        )

    return ModerationResult(passed=True, level="ok", matched_words=[])
