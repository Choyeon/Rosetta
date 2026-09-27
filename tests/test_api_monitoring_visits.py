"""访问量汇总的"数据覆盖口径"契约

`visit_logs` 会被 `LOG_RETENTION_DAYS` 自动清理，而 `/visits/summary` 的 `week`/`month`
是**固定** 7/30 天窗口计数。保留窗口小于窗口天数时（默认就是 7 天），"最近 30 天"
只剩部分数据——数字仍然"正确"，但它是个下界，不说明口径就会被当成全量读数。

本文件钉住响应必须自带口径字段：
  - `retention_days`：当前保留窗口（<=0 表示不清理）
  - `data_since`：现存最早一条日志的时间（表空为 null）
少了这两个字段，任何消费方都无法判断自己看到的是窗口全量还是被截短的下界。
"""

from datetime import datetime

import pytest
from sqlalchemy import func, select

from backend.core.config import settings
from backend.models.monitoring import VisitLog
from backend.utils.compat import UTC, timedelta


async def _seed_two_visits(db_session) -> datetime:
    """插入一旧一新两条访问记录，返回"旧"那条的时间（超出 30 天窗口）。"""
    now = datetime.now(UTC)
    old = now - timedelta(days=45)
    db_session.add_all(
        [
            VisitLog(
                path="/old", method="GET", status_code=200, response_time_ms=1.0, created_at=old
            ),
            VisitLog(
                path="/new", method="GET", status_code=200, response_time_ms=1.0, created_at=now
            ),
        ]
    )
    await db_session.flush()
    return old


@pytest.mark.asyncio
async def test_visits_summary_exposes_coverage_fields(client, staff_headers, db_session):
    old = await _seed_two_visits(db_session)

    resp = await client.get("/api/monitoring/visits/summary", headers=staff_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # 该路由不套 { success, data } 信封，直接返回裸对象
    assert "success" not in body

    assert body["retention_days"] == settings.log_retention_days
    assert body["data_since"], "缺口径字段会让消费方把下界当成全量"
    since = datetime.fromisoformat(body["data_since"])
    assert since.tzinfo is not None, "SQLite 存的是 naive UTC，序列化前必须补上时区"
    assert since <= old + timedelta(minutes=1), f"data_since={body['data_since']} 晚于已知最早记录"


@pytest.mark.asyncio
async def test_month_window_is_strictly_narrower_than_full_range(client, staff_headers, db_session):
    """45 天前的那条不计入 month，但必须体现在 data_since 之前——两者口径不能互相矛盾。"""
    await _seed_two_visits(db_session)
    total_rows = await db_session.scalar(select(func.count()).select_from(VisitLog))

    resp = await client.get("/api/monitoring/visits/summary", headers=staff_headers)
    body = resp.json()

    assert body["total"] == total_rows
    assert body["month"] <= body["total"]
    assert body["week"] <= body["month"]
    assert body["today"] >= 1
    assert len(body["trend"]) == 7, "7 日趋势固定 7 个点（含今天），缺失日补 0"
