import logging
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

logger = logging.getLogger(__name__)

__all__ = ["UTC", "parse_utc_date", "timedelta", "utc_now_naive"]


def utc_now_naive() -> datetime:
    """当前的 UTC 时间，**不带** tzinfo。

    本项目的 `created_at / updated_at` 在库里就是 UTC：SQLite 走
    `CURRENT_TIMESTAMP`（UTC 朴素值），PG 走 `TIMESTAMPTZ`（真瞬时）。
    写入与窗口比对统一用朴素 UTC，才不会因为运行机器时区（如 UTC+8）
    产生 8 小时偏移。等价于已废弃的 `datetime.utcnow()`，但在 3.12+ 不再告警。
    """
    return datetime.now(UTC).replace(tzinfo=None)


def parse_utc_date(raw: str | None) -> datetime | None:
    """把日期字符串解析为带 UTC tzinfo 的 datetime，解析不了返回 None。

    接受 `2026-01-02` / `2026-01-02T10:00:00` / `...Z` 三种前端写法：
    Python 3.10 的 `fromisoformat` 对部分形态直接抛错，而项目最低就支持 3.10，
    所以纯日期要单独 strptime 兜底；朴素时间一律按 UTC 补齐 tzinfo。

    返回 None 意味着"这个过滤条件没有生效"，调用方多半会退回全量查询——
    因此必须留痕，不能静默。
    """
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        pass
    stripped = raw.strip()
    if len(stripped) == 10:  # YYYY-MM-DD
        try:
            return datetime.strptime(stripped, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError:
            pass
    logger.warning(f"[dates] 无法解析日期参数 {raw!r}，对应的过滤条件已忽略")
    return None
