"""
Rosetta 多租户（Multi-Tenant）骨架。

当前实现为「单站点」版本：所有查询默认绑定 ``DEFAULT_SITE_ID = 1``，
对上层业务透明。未来要启用多站点时：

1. 在 ``backend/models/site.py`` 中补全 ``Site`` ORM 模型与迁移；
2. 在 ``main.py`` 的 ``tenant_middleware`` 内解析 Host / ``/s/{slug}`` → 查 sites 表 → 写入上下文；
3. 业务层用 ``require_site_filter(model)`` 给 select/update 语句拼接 ``site_id == current_site`` 条件。

约定：**不强行在 SQLAlchemy session 层做全局自动过滤**，避免与现有复杂查询（关联/聚合/缓存键）冲突，
而是由业务仓储显式调用 ``require_site_filter`` 逐步迁移。
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Optional

from sqlalchemy import Column, Integer
from sqlalchemy.orm import declared_attr


# 单站点默认值：当前部署形态恒定 = 1（个人博客单一站点）
DEFAULT_SITE_ID: int = 1

_current_site_id: ContextVar[Optional[int]] = ContextVar(
    "tenant.current_site_id",
    default=DEFAULT_SITE_ID,
)


def get_current_site_id() -> Optional[int]:
    """返回当前请求绑定的租户 id（未设置返回 DEFAULT_SITE_ID）。"""
    return _current_site_id.get()


def set_current_site_id(site_id: Optional[int]) -> Token:
    """设置当前请求的租户 id，返回用于 reset 的 Token。

    传 ``None`` 显式清除（请求结束时）。
    """
    if site_id is None:
        return _current_site_id.set(DEFAULT_SITE_ID)
    return _current_site_id.set(site_id)


def reset_current_site_id(token: Token) -> None:
    """重置 set_current_site_id 返回的 Token。"""
    _current_site_id.reset(token)


class TenantMixin:
    """ORM 混入：给模型增加 ``site_id`` 列。

    使用示例::

        class Post(Base, TenantMixin):
            id = Column(Integer, primary_key=True)
            ...

    当前默认 ``server_default=1``，不破坏已存在的行。多站点上线
    后再根据站点切换填充真实 site_id。
    """

    @declared_attr
    def site_id(cls):  # noqa: N805 - declared_attr convention
        return Column(
            Integer,
            nullable=False,
            default=DEFAULT_SITE_ID,
            server_default=str(DEFAULT_SITE_ID),
            index=True,
            comment="租户/站点ID（多站点启用后使用）",
        )


def require_site_filter(site_id: Optional[int] = None):
    """返回 ``site_id == value`` 的 SQL 表达式，便于仓储层显式拼接过滤。

    当不传 site_id 时，使用当前上下文的 current_site_id。
    """
    from sqlalchemy.sql.expression import true

    sid = site_id if site_id is not None else get_current_site_id()
    # 未设置或为默认值时返回 true()（不做实际过滤，保持向后兼容）
    if sid in (None, DEFAULT_SITE_ID):
        return true()
    return TenantMixin.site_id == sid
