"""主题/插件磁盘扫描的查询次数上限（防 N+1 回潮）

`scan_local` 原先对磁盘上每个 manifest 单发一条 `SELECT ... WHERE slug=?`，
插件/主题数量线性增长即拉高启动期与后台"重新扫描"的往返次数。现改为
一次性预取本站全部行后在内存比对。本用例把"扫描一次的 SELECT 条数"钉成常数。
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.extensions import PluginManager, ThemeManager


class _CountingSession:
    """透明代理：只统计 `execute` 调用次数，其余全部转发给真实 session"""

    def __init__(self, inner: AsyncSession) -> None:
        self._inner = inner
        self.executes = 0

    def __getattr__(self, name):
        attr = getattr(self._inner, name)
        if name != "execute":
            return attr

        async def counted(*args, **kwargs):
            self.executes += 1
            return await attr(*args, **kwargs)

        return counted


@pytest.mark.asyncio
async def test_plugin_scan_local_uses_constant_query_count(db_session: AsyncSession):
    spy = _CountingSession(db_session)
    await PluginManager().scan_local(spy)
    # 预取 1 次 + 僵尸行清理 1 次；与磁盘插件数量无关
    assert spy.executes <= 3, (
        f"插件扫描 SELECT 次数应恒为常数，实际={spy.executes}（疑似逐 slug 查询回潮）"
    )


@pytest.mark.asyncio
async def test_theme_scan_local_uses_constant_query_count(db_session: AsyncSession):
    spy = _CountingSession(db_session)
    await ThemeManager().scan_local(spy)
    assert spy.executes <= 4, (
        f"主题扫描 SELECT 次数应恒为常数，实际={spy.executes}（疑似逐 slug 查询回潮）"
    )


@pytest.mark.asyncio
async def test_scan_local_is_idempotent(db_session: AsyncSession):
    """重复扫描不得产生重复行，也不得把已激活状态刷掉"""
    from sqlalchemy import select

    from backend.models.extensions import Theme

    mgr = ThemeManager()
    first = await mgr.scan_local(db_session)
    active_before = (
        (await db_session.execute(select(Theme.slug).where(Theme.is_active.is_(True))))
        .scalars()
        .all()
    )
    second = await mgr.scan_local(db_session)
    await db_session.commit()

    assert second[0] == 0, (
        f"第二次扫描不应再判定为新增，实际 added={second[0]}：{first} -> {second}"
    )
    rows = (await db_session.execute(select(Theme.slug))).scalars().all()
    assert len(rows) == len(set(rows)), f"扫描产生了重复 slug 行: {rows}"
    active_after = (
        (await db_session.execute(select(Theme.slug).where(Theme.is_active.is_(True))))
        .scalars()
        .all()
    )
    assert set(active_after) == set(active_before), "重扫不得改变激活主题"
