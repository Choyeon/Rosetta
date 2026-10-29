import logging
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

logger = logging.getLogger(__name__)

__all__ = ["UTC", "ensure_aware", "parse_utc_date", "timedelta", "to_utc_instant", "utc_now_naive"]


def ensure_aware(value: datetime | None) -> datetime | None:
    """无时区的时间一律按 UTC 解释（与 ``services/post_access.py`` 同口径）。

    同一列 ``DateTime(timezone=True)`` 在 PG 下读回是 aware，在 SQLite 下 tz 会被
    丢弃读回 naive。拿 naive 去和 ``datetime.now(UTC)`` 比较直接抛 ``TypeError``——
    实测表现是登录锁定一旦落库，SQLite 部署下之后每次登录都 500，而"锁定到期
    自动解锁"那支同样走不到，账号等于永久锁死。

    这是**读取/比对侧**的口径（不改动已经带 tz 的值）。要往库里写客户端给的时间，
    用 :func:`to_utc_instant`。
    """
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def to_utc_instant(value: datetime | None) -> datetime | None:
    """**写入侧**的单源口径：落库前折算成"带 UTC tzinfo 的瞬时"。

    ``DateTime(timezone=True)`` 这一列在两种库里的失败方式不一样，而且都静默：

    - PG 的 ``TIMESTAMPTZ`` 把**朴素值**按数据库会话时区解释，"2026-10-28T23:43:26"
      在东八区会话下落成 15:43Z。线上探针实测偏 8 小时——偏移量取决于部署机器的
      时区设置，换台机器就换一个数，谁都看不出来；
    - SQLite 的驱动按**不含偏移**的格式串写入，**带非 UTC 偏移**的值会被吃掉偏移，
      存进去的是那个时区的墙钟而不是同一个瞬时。

    朴素补 UTC + 已 aware 的折算到 UTC，两边落下的才是同一个瞬时。前台
    `frontend/lib/datetime.ts` 那句"后端把朴素 datetime 按 UTC 解释"说的就是这条契约。
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


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
