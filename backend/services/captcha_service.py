"""图形验证码的答案存储与消费（评论 / 留言写入口的安全闸门）。

分层原因：HTTP 口在 `api/captcha.py`，而闸门要在 service 层判断，
service 不得反向依赖 api（见 backend/AGENTS.md 调用方向），
所以"答案在缓存里的生命周期"单源放在这里，`api/captcha.py` 的校验端点同样走这里。

缓存键位 `captcha:<key>` 与 `api/captcha.py` 的签发端保持一致；
一次性凭据：**先作废再比对**——字符集只有 32^4 量级，
失败不作废等于给在线枚举留 5 分钟窗口。
"""

from __future__ import annotations

import logging

from backend.core.cache import cache
from backend.services.site_settings import bool_of, read_group

logger = logging.getLogger(__name__)

CAPTCHA_CACHE_PREFIX = "captcha:"

# 与 api/captcha.py 签发端的 TTL 同值（5 分钟）
CAPTCHA_TTL = 300


def captcha_cache_key(key: str) -> str:
    return f"{CAPTCHA_CACHE_PREFIX}{key}"


async def store_captcha_answer(key: str, code: str) -> None:
    """签发时登记答案（统一小写，比对侧同样小写）。"""
    await cache.set(captcha_cache_key(key), (code or "").lower(), CAPTCHA_TTL)


async def consume_captcha(key: str | None, code: str | None) -> None:
    """校验并作废一次；不通过抛 ``ValueError(CODE)``，由 API 层映射成 HTTP 状态。

    - ``CAPTCHA_REQUIRED``：没带 key 或没填码（前端漏挂字段 / 空提交）
    - ``CAPTCHA_EXPIRED``：键不存在或已超过 5 分钟
    - ``CAPTCHA_INVALID``：比对不通过（该键已被消费，重试必须重新取图）
    """
    if not key or not (code or "").strip():
        raise ValueError("CAPTCHA_REQUIRED")

    stored = await cache.get(captcha_cache_key(key))
    # 先删再比：无论结果如何这张图都不能再用
    await cache.delete(captcha_cache_key(key))

    if not stored:
        raise ValueError("CAPTCHA_EXPIRED")
    if (code or "").strip().lower() != str(stored).lower():
        raise ValueError("CAPTCHA_INVALID")


async def ensure_captcha_for_guest(
    db,
    *,
    current_user,
    captcha_key: str | None,
    captcha_code: str | None,
) -> None:
    """匿名写入口的验证码闸门。

    只在「后台功能开关打开」且「提交者是匿名」时生效：
    登录用户已有账号级信号，给它们加图形码只会把登录用户的评论流程打残。
    兜底值取**既有行为**（未保存过 features 分组 = 不要验证码），
    否则一次改动就把所有存量站点的评论/留言流程改成必须填码。
    """
    if current_user is not None:
        return
    feats = await read_group("features", db)
    if not bool_of(feats, "enable_captcha", False):
        return
    await consume_captcha(captcha_key, captcha_code)
