"""
CRUD 基类

提供统一的 CRUD 操作接口，支持：
- 缓存策略
- 批量操作
- 分页查询
- PostgreSQL 特有优化
"""

import math
from abc import ABC
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import Insert, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql import Select

from backend.core.cache import cache, invalidate_cache, make_cache_key
from backend.core.config import settings
from backend.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType], ABC):
    """
    CRUD 基类

    提供通用的 CRUD 操作，子类可以覆盖特定方法。

    属性:
        model: SQLAlchemy 模型类
        cache_prefix: 缓存键前缀
        cache_ttl: 缓存过期时间（秒）
    """

    def __init__(
        self,
        model: type[ModelType],
        cache_prefix: str = "",
        cache_ttl: int = 300,
    ):
        self.model = model
        self.cache_prefix = cache_prefix or model.__tablename__
        self.cache_ttl = cache_ttl

    def _get_cache_key(self, *parts: Any) -> str:
        """生成缓存键"""
        return make_cache_key(self.cache_prefix, *map(str, parts))

    async def _invalidate_cache(self, obj_id: int | None = None) -> None:
        """使缓存失效"""
        if obj_id:
            await cache.delete(self._get_cache_key("id", obj_id))
        await invalidate_cache(self.cache_prefix)

    async def get(
        self,
        db: AsyncSession,
        id: int,
        *,
        use_cache: bool = True,
        options: list | None = None,
    ) -> ModelType | None:
        """
        根据 ID 获取单个对象

        Args:
            db: 数据库会话
            id: 对象 ID
            use_cache: 是否使用缓存
            options: SQLAlchemy 加载选项

        Returns:
            模型实例或 None
        """
        if use_cache:
            cache_key = self._get_cache_key("id", id)
            cached = await cache.get(cache_key)
            if cached:
                return cached

        query = select(self.model).where(self.model.id == id)
        if options:
            query = query.options(*options)

        result = await db.execute(query)
        obj = result.scalar_one_or_none()

        if use_cache and obj:
            await cache.set(cache_key, obj, self.cache_ttl)

        return obj

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: InstrumentedAttribute | None = None,
        options: list | None = None,
    ) -> list[ModelType]:
        """
        获取多个对象

        Args:
            db: 数据库会话
            skip: 跳过数量
            limit: 返回数量
            order_by: 排序字段
            options: SQLAlchemy 加载选项

        Returns:
            模型实例列表
        """
        query = select(self.model)

        if options:
            query = query.options(*options)
        if order_by is not None:
            query = query.order_by(order_by)

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_paginated(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 12,
        query: Select | None = None,
        options: list | None = None,
        use_cache: bool = False,
        cache_key: str | None = None,
    ) -> dict[str, Any]:
        """
        分页查询

        Args:
            db: 数据库会话
            page: 页码
            page_size: 每页数量
            query: 自定义查询
            options: SQLAlchemy 加载选项
            use_cache: 是否使用缓存
            cache_key: 自定义缓存键

        Returns:
            包含 items, total, page, page_size, total_pages 的字典
        """
        if use_cache and cache_key:
            cached = await cache.get(cache_key)
            if cached:
                return cached

        base_query = query if query is not None else select(self.model)

        if options:
            base_query = base_query.options(*options)

        count_query = select(func.count()).select_from(base_query.subquery())
        total = await db.scalar(count_query) or 0

        paginated_query = base_query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(paginated_query)
        items = list(result.scalars().all())

        response = {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if total > 0 else 0,
        }

        if use_cache and cache_key:
            await cache.set(cache_key, response, self.cache_ttl)

        return response

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: CreateSchemaType,
        extra_data: dict | None = None,
    ) -> ModelType:
        """
        创建对象

        Args:
            db: 数据库会话
            obj_in: 创建数据模型
            extra_data: 额外数据

        Returns:
            创建的模型实例
        """
        obj_data = obj_in.model_dump() if hasattr(obj_in, "model_dump") else dict(obj_in)
        if extra_data:
            obj_data.update(extra_data)

        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)

        await self._invalidate_cache()

        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict,
    ) -> ModelType:
        """
        更新对象

        Args:
            db: 数据库会话
            db_obj: 要更新的模型实例
            obj_in: 更新数据模型或字典

        Returns:
            更新后的模型实例
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        await db.flush()
        await db.refresh(db_obj)

        await self._invalidate_cache(db_obj.id)

        return db_obj

    async def delete(
        self,
        db: AsyncSession,
        *,
        id: int,
    ) -> bool:
        """
        删除对象

        Args:
            db: 数据库会话
            id: 对象 ID

        Returns:
            是否删除成功
        """
        result = await db.execute(delete(self.model).where(self.model.id == id))

        if result.rowcount > 0:
            await self._invalidate_cache(id)
            return True
        return False

    async def exists(
        self,
        db: AsyncSession,
        *,
        id: int | None = None,
        **filters: Any,
    ) -> bool:
        """
        检查对象是否存在

        Args:
            db: 数据库会话
            id: 对象 ID
            **filters: 其他过滤条件

        Returns:
            是否存在
        """
        query = select(func.count()).select_from(self.model)

        if id is not None:
            query = query.where(self.model.id == id)

        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)

        count = await db.scalar(query)
        return (count or 0) > 0

    async def count(
        self,
        db: AsyncSession,
        **filters: Any,
    ) -> int:
        """
        统计数量

        Args:
            db: 数据库会话
            **filters: 过滤条件

        Returns:
            数量
        """
        query = select(func.count()).select_from(self.model)

        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)

        return await db.scalar(query) or 0

    async def bulk_create(
        self,
        db: AsyncSession,
        *,
        objects: list[CreateSchemaType],
    ) -> int:
        """
        批量创建

        Args:
            db: 数据库会话
            objects: 创建数据列表

        Returns:
            创建数量
        """
        if not objects:
            return 0

        data_list = [
            obj.model_dump() if hasattr(obj, "model_dump") else dict(obj) for obj in objects
        ]

        stmt = Insert(self.model).values(data_list)

        if settings.is_postgresql:
            from sqlalchemy.dialects.postgresql import insert

            stmt = insert(self.model).values(data_list)

        await db.execute(stmt)
        await db.flush()

        await self._invalidate_cache()

        return len(data_list)

    async def bulk_update(
        self,
        db: AsyncSession,
        *,
        updates: list[dict],
        key_field: str = "id",
    ) -> int:
        """
        批量更新

        Args:
            db: 数据库会话
            updates: 更新数据列表，每个字典必须包含 key_field
            key_field: 用于匹配的字段

        Returns:
            更新数量
        """
        if not updates:
            return 0

        count = 0
        for update_data in updates:
            if key_field not in update_data:
                continue

            key_value = update_data.pop(key_field)
            result = await db.execute(
                update(self.model)
                .where(getattr(self.model, key_field) == key_value)
                .values(**update_data)
            )
            count += result.rowcount

        await db.flush()
        await self._invalidate_cache()

        return count


class CachedQuery:
    """
    缓存查询工具类

    提供常用的缓存查询方法。
    """

    @staticmethod
    async def get_or_set(
        key: str,
        factory,
        ttl: int = 300,
    ) -> Any:
        """
        获取或设置缓存

        Args:
            key: 缓存键
            factory: 缓存未命中时的工厂函数
            ttl: 过期时间

        Returns:
            缓存值或工厂函数结果
        """
        cached = await cache.get(key)
        if cached is not None:
            return cached

        value = await factory()
        if value is not None:
            await cache.set(key, value, ttl)

        return value

    @staticmethod
    async def get_list(
        key: str,
        factory,
        ttl: int = 300,
    ) -> list:
        """
        获取列表缓存

        Args:
            key: 缓存键
            factory: 缓存未命中时的工厂函数
            ttl: 过期时间

        Returns:
            列表
        """
        cached = await cache.get(key)
        if cached is not None:
            return cached

        value = await factory()
        if value is None:
            value = []

        await cache.set(key, value, ttl)
        return value
