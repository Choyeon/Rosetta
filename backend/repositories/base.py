"""
仓储层基类

提供通用的 CRUD 操作基类，支持：
- 基础 CRUD 操作（创建、读取、更新、删除）
- 分页查询
- 过滤和排序
- 并发查询优化
"""

from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from backend.core.concurrency import concurrent_query
from backend.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class PaginationResult(Generic[ModelType]):
    """分页结果包装类"""

    def __init__(
        self,
        items: list[ModelType],
        total: int,
        page: int,
        page_size: int,
    ):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        self.has_next = page < self.total_pages
        self.has_prev = page > 1

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
        }


class BaseRepository(Generic[ModelType]):
    """
    仓储层基类

    提供通用的数据库操作方法，所有具体仓储类都应继承此类。

    Attributes:
        model: SQLAlchemy 模型类
        session: 异步数据库会话

    Example:
        >>> class UserRepository(BaseRepository[User]):
        ...     def __init__(self, session: AsyncSession):
        ...         super().__init__(User, session)
    """

    def __init__(self, model: type[ModelType], session: AsyncSession):
        """
        初始化仓储

        Args:
            model: SQLAlchemy 模型类
            session: 异步数据库会话
        """
        self.model = model
        self.session = session

    async def get_by_id(self, id: int) -> ModelType | None:
        """
        根据 ID 获取单个记录

        Args:
            id: 记录 ID

        Returns:
            模型实例，不存在则返回 None
        """
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: list[int]) -> list[ModelType]:
        """
        根据 ID 列表批量获取记录

        Args:
            ids: ID 列表

        Returns:
            模型实例列表
        """
        if not ids:
            return []
        result = await self.session.execute(select(self.model).where(self.model.id.in_(ids)))
        return list(result.scalars().all())

    async def get_all(
        self,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[ModelType]:
        """
        获取所有记录

        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            模型实例列表
        """
        query = select(self.model).offset(skip)
        if limit is not None:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, data: dict[str, Any] | ModelType) -> ModelType:
        """
        创建新记录

        Args:
            data: 字典数据或模型实例

        Returns:
            创建的模型实例
        """
        if isinstance(data, self.model):
            instance = data
        else:
            instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, instance: ModelType, data: dict[str, Any]) -> ModelType:
        """
        更新记录

        Args:
            instance: 模型实例
            data: 更新数据字典

        Returns:
            更新后的模型实例
        """
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> bool:
        """
        删除记录

        Args:
            instance: 模型实例

        Returns:
            删除成功返回 True
        """
        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def delete_by_id(self, id: int) -> bool:
        """
        根据 ID 删除记录

        Args:
            id: 记录 ID

        Returns:
            删除成功返回 True，记录不存在返回 False
        """
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        return await self.delete(instance)

    async def count(self) -> int:
        """
        统计记录总数

        Returns:
            记录总数
        """
        result = await self.session.execute(select(func.count()).select_from(self.model))
        return result.scalar_one()

    async def exists(self, id: int) -> bool:
        """
        检查记录是否存在

        Args:
            id: 记录 ID

        Returns:
            存在返回 True
        """
        result = await self.session.execute(
            select(func.count()).select_from(self.model).where(self.model.id == id)
        )
        return result.scalar_one() > 0

    async def paginate(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: dict[str, Any] | None = None,
        order_by: InstrumentedAttribute[Any] | str | None = None,
        descending: bool = False,
    ) -> PaginationResult[ModelType]:
        """
        分页查询

        Args:
            page: 页码（从 1 开始）
            page_size: 每页记录数
            filters: 过滤条件字典
            order_by: 排序字段
            descending: 是否降序

        Returns:
            分页结果对象
        """
        query = select(self.model)

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.where(getattr(self.model, key) == value)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        if order_by is not None:
            if isinstance(order_by, str):
                order_column = getattr(self.model, order_by, None)
                if order_column is not None:
                    query = query.order_by(order_column.desc() if descending else order_column)
            else:
                query = query.order_by(order_by.desc() if descending else order_by)

        skip = (page - 1) * page_size
        query = query.offset(skip).limit(page_size)

        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return PaginationResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_by_field(self, field: str, value: Any) -> ModelType | None:
        """
        根据字段值获取单个记录

        Args:
            field: 字段名
            value: 字段值

        Returns:
            模型实例，不存在则返回 None
        """
        if not hasattr(self.model, field):
            return None
        result = await self.session.execute(
            select(self.model).where(getattr(self.model, field) == value)
        )
        return result.scalar_one_or_none()

    async def get_all_by_field(
        self,
        field: str,
        value: Any,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[ModelType]:
        """
        根据字段值获取所有匹配记录

        Args:
            field: 字段名
            value: 字段值
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            模型实例列表
        """
        if not hasattr(self.model, field):
            return []
        query = select(self.model).where(getattr(self.model, field) == value).offset(skip)
        if limit is not None:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search(
        self,
        keyword: str,
        fields: list[str],
        skip: int = 0,
        limit: int | None = None,
    ) -> list[ModelType]:
        """
        模糊搜索

        Args:
            keyword: 搜索关键词
            fields: 搜索字段列表
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            模型实例列表
        """
        if not keyword or not fields:
            return []

        conditions = []
        for field in fields:
            if hasattr(self.model, field):
                conditions.append(getattr(self.model, field).ilike(f"%{keyword}%"))

        if not conditions:
            return []

        from sqlalchemy import or_

        query = select(self.model).where(or_(*conditions)).offset(skip)
        if limit is not None:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def bulk_create(self, data_list: list[dict[str, Any]]) -> list[ModelType]:
        """
        批量创建记录

        Args:
            data_list: 数据字典列表

        Returns:
            创建的模型实例列表
        """
        instances = [self.model(**data) for data in data_list]
        self.session.add_all(instances)
        await self.session.flush()
        for instance in instances:
            await self.session.refresh(instance)
        return instances

    async def bulk_update(
        self, instances: list[ModelType], data: dict[str, Any]
    ) -> list[ModelType]:
        """
        批量更新记录

        Args:
            instances: 模型实例列表
            data: 更新数据字典

        Returns:
            更新后的模型实例列表
        """
        for instance in instances:
            for key, value in data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
        await self.session.flush()
        for instance in instances:
            await self.session.refresh(instance)
        return instances

    async def bulk_delete(self, instances: list[ModelType]) -> int:
        """
        批量删除记录

        Args:
            instances: 模型实例列表

        Returns:
            删除的记录数
        """
        count = len(instances)
        for instance in instances:
            await self.session.delete(instance)
        await self.session.flush()
        return count

    async def get_or_create(
        self,
        defaults: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> tuple[ModelType, bool]:
        """
        获取或创建记录

        Args:
            defaults: 创建时的默认值
            **kwargs: 查询条件

        Returns:
            (模型实例, 是否新创建) 元组
        """
        conditions = [getattr(self.model, key) == value for key, value in kwargs.items()]
        query = select(self.model).where(*conditions)
        result = await self.session.execute(query)
        instance = result.scalar_one_or_none()

        if instance is not None:
            return instance, False

        create_data = {**kwargs}
        if defaults:
            create_data.update(defaults)
        instance = await self.create(create_data)
        return instance, True

    async def concurrent_get_by_ids(self, ids: list[int], batch_size: int = 10) -> list[ModelType]:
        """
        并发批量获取记录

        将 ID 列表分批并发查询，适用于大量 ID 的场景。

        Args:
            ids: ID 列表
            batch_size: 每批查询的数量

        Returns:
            模型实例列表
        """
        if not ids:
            return []

        batches = [ids[i : i + batch_size] for i in range(0, len(ids), batch_size)]

        async def get_batch(batch_ids: list[int]) -> list[ModelType]:
            return await self.get_by_ids(batch_ids)

        results = await concurrent_query(*[get_batch(batch) for batch in batches])

        all_items: list[ModelType] = []
        for result in results:
            if isinstance(result, list):
                all_items.extend(result)

        return all_items
