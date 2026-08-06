"""
密码强度策略模块

提供统一的密码强度验证，支持：
- 最小长度
- 大小写字母要求
- 数字要求
- 禁止常见弱密码（Top 100）
- 可通过 security_password_policy 开关控制
"""

import logging
import re
from typing import Any

from backend.core.config import settings

logger = logging.getLogger(__name__)

PASSWORD_BLOCKLIST: list[str] = [
    "123456",
    "password",
    "12345678",
    "qwerty",
    "abc123",
    "123456789",
    "111111",
    "1234567",
    "123123",
    "admin",
    "letmein",
    "welcome",
    "monkey",
    "dragon",
    "master",
    "666666",
    "sunshine",
    "princess",
    "qwertyuiop",
    "football",
    "123321",
    "1q2w3e4r",
    "654321",
    "1234567890",
    "iloveyou",
    "password1",
    "12345",
    "1234",
    "123456a",
    "q1w2e3r4",
    "000000",
    "password123",
    "1qaz2wsx",
    "121212",
    "123qwe",
    "aa123456",
    "7777777",
    "aaaaaa",
    "123",
    "888888",
    "123abc",
    "qwerty123",
    "abc12345",
    "66666666",
    "1234qwer",
    "a123456",
    "asdfghjkl",
    "987654321",
    "11111111",
    "12341234",
    "zaq12wsx",
    "password!",
    "0",
    "1",
    "12345a",
    "love",
    "112233",
    "102030",
    "qqqqqq",
    "asdasd",
    "zxcvbnm",
    "222222",
    "333333",
    "qwe123",
    "asdf1234",
    "123654",
    "1q2w3e",
    "qazwsx",
    "1111",
    "135790",
    "246810",
    "qwer1234",
    "abcd1234",
    "abcd",
    "qwer",
    "asdf",
    "zxcv",
    "p@ssw0rd",
    "p@ssword",
    "pass123",
    "passw0rd",
    "1111111",
    "555555",
    "123456q",
    "1qazxsw2",
    "147258369",
    "789456123",
    "999999",
    "159357",
    "741852963",
    "q1w2e3",
    "123456789a",
    "a123456789",
    "a1b2c3",
    "z1x2c3",
    "qazwsxedc",
    "159753",
    "456789",
    "12345678910",
    "0987654321",
]


def validate_password(password: str | None) -> list[str]:
    """
    验证密码强度

    Args:
        password: 要验证的密码字符串

    Returns:
        list[str]: 错误消息列表（中文），空列表表示通过
    """
    errors: list[str] = []

    if not settings.security_password_policy:
        return errors

    if password is None:
        errors.append("密码不能为空")
        return errors

    pw = password
    if len(pw) < 8:
        errors.append("密码长度至少需要 8 个字符")

    if not re.search(r"[a-z]", pw):
        errors.append("密码必须包含至少一个小写字母")

    if not re.search(r"[A-Z]", pw):
        errors.append("密码必须包含至少一个大写字母")

    if not re.search(r"\d", pw):
        errors.append("密码必须包含至少一个数字")

    lowered = pw.lower()
    if lowered in PASSWORD_BLOCKLIST:
        errors.append("该密码属于常见弱密码，请更换为更复杂的密码")

    return errors


async def check_site_password_policy() -> bool:
    """
    检查站点级密码策略开关（后续可接入 site_settings）

    当前优先使用 settings.security_password_policy
    """
    try:
        from backend.core.site_config import site_settings

        v: Any = await site_settings.get("security", "password_policy", default=None)
        if v is not None:
            return bool(v)
    except Exception:
        pass

    return settings.security_password_policy
