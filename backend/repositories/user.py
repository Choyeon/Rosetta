"""
用户仓储层

提供用户相关的数据库操作，包括：
- 用户 CRUD 操作
- 按用户名、邮箱查询
- 认证相关查询
- 用户偏好设置
"""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from backend.core.concurrency import concurrent_query
from backend.models.user import RefreshToken, User, UserPreference, UserTitle
from backend.repositories.base import BaseRepository, PaginationResult
from backend.utils.compat import UTC


class UserRepository(BaseRepository[User]):
    """
    用户仓储类

    提供用户相关的数据库操作方法。

    Attributes:
        session: 异步数据库会话

    Example:
        >>> async with get_db_context() as session:
        ...     repo = UserRepository(session)
        ...     user = await repo.get_by_username("admin")
    """

    def __init__(self, session: AsyncSession):
        """
        初始化用户仓储

        Args:
            session: 异步数据库会话
        """
        super().__init__(User, session)

    async def get_by_username(self, username: str) -> User | None:
        """
        根据用户名获取用户

        Args:
            username: 用户名

        Returns:
            用户实例，不存在则返回 None
        """
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_username_case_insensitive(self, username: str) -> User | None:
        """
        根据用户名获取用户（不区分大小写）

        Args:
            username: 用户名

        Returns:
            用户实例，不存在则返回 None
        """
        result = await self.session.execute(
            select(User).where(func.lower(User.username) == username.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """
        根据邮箱获取用户

        Args:
            email: 邮箱地址

        Returns:
            用户实例，不存在则返回 None
        """
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_email_case_insensitive(self, email: str) -> User | None:
        """
        根据邮箱获取用户（不区分大小写）

        Args:
            email: 邮箱地址

        Returns:
            用户实例，不存在则返回 None
        """
        result = await self.session.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_username_or_email(self, identifier: str) -> User | None:
        """
        根据用户名或邮箱获取用户

        Args:
            identifier: 用户名或邮箱

        Returns:
            用户实例，不存在则返回 None
        """
        result = await self.session.execute(
            select(User).where((User.username == identifier) | (User.email == identifier))
        )
        return result.scalar_one_or_none()

    async def get_by_username_or_email_case_insensitive(self, identifier: str) -> User | None:
        """
        根据用户名或邮箱获取用户（不区分大小写）

        Args:
            identifier: 用户名或邮箱

        Returns:
            用户实例，不存在则返回 None
        """
        identifier_lower = identifier.lower()
        result = await self.session.execute(
            select(User).where(
                (func.lower(User.username) == identifier_lower)
                | (func.lower(User.email) == identifier_lower)
            )
        )
        return result.scalar_one_or_none()

    async def get_with_title(self, user_id: int) -> User | None:
        """
        获取用户及其头衔

        Args:
            user_id: 用户 ID

        Returns:
            用户实例（包含头衔），不存在则返回 None
        """
        result = await self.session.execute(
            select(User).where(User.id == user_id).options(joinedload(User.title))
        )
        return result.scalar_one_or_none()

    async def get_with_preferences(self, user_id: int) -> User | None:
        """
        获取用户及其偏好设置

        Args:
            user_id: 用户 ID

        Returns:
            用户实例（包含偏好设置），不存在则返回 None
        """
        result = await self.session.execute(
            select(User).where(User.id == user_id).options(joinedload(User.preferences))
        )
        return result.scalar_one_or_none()

    async def get_full_profile(self, user_id: int) -> dict[str, Any] | None:
        """
        获取用户完整资料

        预加载关系 + 仅并行执行真实 DB 查询（避免 MissingGreenlet）。

        Args:
            user_id: 用户 ID

        Returns:
            包含用户完整资料的字典
        """
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.title),
                selectinload(User.preferences),
            )
        )
        user = result.scalar_one_or_none()
        if user is None:
            return None

        from backend.models.blog import Comment, Post

        # 仅真实需要访问 DB 的 count 查询保留为协程
        async def get_post_count():
            r = await self.session.execute(
                select(func.count()).select_from(Post).where(Post.author_id == user_id)
            )
            return r.scalar_one()

        async def get_comment_count():
            r = await self.session.execute(
                select(func.count()).select_from(Comment).where(Comment.user_id == user_id)
            )
            return r.scalar_one()

        post_count, comment_count = await concurrent_query(
            get_post_count(),
            get_comment_count(),
        )

        return {
            "user": user,
            "title": user.title,
            "preferences": user.preferences,
            "post_count": post_count,
            "comment_count": comment_count,
        }

    async def username_exists(self, username: str, exclude_id: int | None = None) -> bool:
        """
        检查用户名是否已存在

        Args:
            username: 用户名
            exclude_id: 排除的用户 ID（用于更新时检查）

        Returns:
            存在返回 True
        """
        query = (
            select(func.count())
            .select_from(User)
            .where(func.lower(User.username) == username.lower())
        )
        if exclude_id is not None:
            query = query.where(User.id != exclude_id)
        result = await self.session.execute(query)
        return result.scalar_one() > 0

    async def email_exists(self, email: str, exclude_id: int | None = None) -> bool:
        """
        检查邮箱是否已存在

        Args:
            email: 邮箱地址
            exclude_id: 排除的用户 ID（用于更新时检查）

        Returns:
            存在返回 True
        """
        query = (
            select(func.count()).select_from(User).where(func.lower(User.email) == email.lower())
        )
        if exclude_id is not None:
            query = query.where(User.id != exclude_id)
        result = await self.session.execute(query)
        return result.scalar_one() > 0

    async def update_last_login(self, user_id: int) -> bool:
        """
        更新最后登录时间

        Args:
            user_id: 用户 ID

        Returns:
            成功返回 True
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return False
        user.update_last_login()
        await self.session.flush()
        return True

    async def get_active_users(self, skip: int = 0, limit: int = 20) -> list[User]:
        """
        获取活跃用户列表

        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            活跃用户列表
        """
        query = (
            select(User)
            .where(User.is_active.is_(True), User.is_banned.is_(False))
            .order_by(User.last_login.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_staff_users(self) -> list[User]:
        """
        获取管理员用户列表

        Returns:
            管理员用户列表
        """
        result = await self.session.execute(
            select(User).where(User.is_staff.is_(True), User.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def get_superusers(self) -> list[User]:
        """
        获取超级管理员用户列表

        Returns:
            超级管理员用户列表
        """
        result = await self.session.execute(
            select(User).where(User.is_superuser.is_(True), User.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def ban_user(self, user_id: int) -> bool:
        """
        封禁用户

        Args:
            user_id: 用户 ID

        Returns:
            成功返回 True
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return False
        user.is_banned = True
        await self.session.flush()
        return True

    async def unban_user(self, user_id: int) -> bool:
        """
        解封用户

        Args:
            user_id: 用户 ID

        Returns:
            成功返回 True
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return False
        user.is_banned = False
        await self.session.flush()
        return True

    async def activate_user(self, user_id: int) -> bool:
        """
        激活用户

        Args:
            user_id: 用户 ID

        Returns:
            成功返回 True
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return False
        user.is_active = True
        await self.session.flush()
        return True

    async def deactivate_user(self, user_id: int) -> bool:
        """
        停用用户

        Args:
            user_id: 用户 ID

        Returns:
            成功返回 True
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return False
        user.is_active = False
        await self.session.flush()
        return True

    async def set_staff_status(self, user_id: int, is_staff: bool) -> bool:
        """
        设置管理员状态

        Args:
            user_id: 用户 ID
            is_staff: 是否为管理员

        Returns:
            成功返回 True
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return False
        user.is_staff = is_staff
        await self.session.flush()
        return True

    async def search_users(
        self,
        keyword: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[User]:
        """
        搜索用户

        在用户名、昵称、邮箱中搜索关键词。

        Args:
            keyword: 搜索关键词
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            用户列表
        """
        from sqlalchemy import or_

        search_pattern = f"%{keyword}%"

        query = (
            select(User)
            .where(
                or_(
                    User.username.ilike(search_pattern),
                    User.nickname.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                )
            )
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_users_by_status(
        self,
        is_active: bool | None = None,
        is_staff: bool | None = None,
        is_banned: bool | None = None,
    ) -> int:
        """
        统计指定状态的用户数

        Args:
            is_active: 是否活跃
            is_staff: 是否为管理员
            is_banned: 是否被封禁

        Returns:
            用户数
        """
        query = select(func.count()).select_from(User)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        if is_staff is not None:
            query = query.where(User.is_staff == is_staff)
        if is_banned is not None:
            query = query.where(User.is_banned == is_banned)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def paginate_users(
        self,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
        is_staff: bool | None = None,
        is_banned: bool | None = None,
        title_id: int | None = None,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> PaginationResult[User]:
        """
        分页查询用户

        支持多条件过滤和排序。

        Args:
            page: 页码
            page_size: 每页记录数
            is_active: 是否活跃
            is_staff: 是否为管理员
            is_banned: 是否被封禁
            title_id: 头衔 ID
            order_by: 排序字段
            descending: 是否降序

        Returns:
            分页结果
        """
        query = select(User)

        if is_active is not None:
            query = query.where(User.is_active == is_active)
        if is_staff is not None:
            query = query.where(User.is_staff == is_staff)
        if is_banned is not None:
            query = query.where(User.is_banned == is_banned)
        if title_id is not None:
            query = query.where(User.title_id == title_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        order_column = getattr(User, order_by, User.created_at)
        query = query.order_by(order_column.desc() if descending else order_column)

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


class UserPreferenceRepository(BaseRepository[UserPreference]):
    """
    用户偏好设置仓储类

    提供用户偏好设置相关的数据库操作方法。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化用户偏好设置仓储

        Args:
            session: 异步数据库会话
        """
        super().__init__(UserPreference, session)

    async def get_by_user_id(self, user_id: int) -> UserPreference | None:
        """
        根据用户 ID 获取偏好设置

        Args:
            user_id: 用户 ID

        Returns:
            偏好设置实例，不存在则返回 None
        """
        result = await self.session.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_for_user(self, user_id: int) -> UserPreference:
        """
        获取或创建用户偏好设置

        Args:
            user_id: 用户 ID

        Returns:
            偏好设置实例
        """
        preference = await self.get_by_user_id(user_id)
        if preference is not None:
            return preference

        preference = await self.create({"user_id": user_id})
        return preference

    async def update_theme(self, user_id: int, theme: str) -> UserPreference | None:
        """
        更新用户主题偏好

        Args:
            user_id: 用户 ID
            theme: 主题名称

        Returns:
            更新后的偏好设置实例
        """
        preference = await self.get_by_user_id(user_id)
        if preference is None:
            return None
        preference.theme = theme
        await self.session.flush()
        await self.session.refresh(preference)
        return preference

    async def update_public_profile(self, user_id: int, public: bool) -> UserPreference | None:
        """
        更新用户公开资料设置

        Args:
            user_id: 用户 ID
            public: 是否公开

        Returns:
            更新后的偏好设置实例
        """
        preference = await self.get_by_user_id(user_id)
        if preference is None:
            return None
        preference.public_profile = public
        await self.session.flush()
        await self.session.refresh(preference)
        return preference


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """
    刷新令牌仓储类

    提供刷新令牌相关的数据库操作方法。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化刷新令牌仓储

        Args:
            session: 异步数据库会话
        """
        super().__init__(RefreshToken, session)

    async def get_by_token(self, token: str) -> RefreshToken | None:
        """
        根据令牌字符串获取刷新令牌

        Args:
            token: 令牌字符串

        Returns:
            刷新令牌实例，不存在则返回 None
        """
        result = await self.session.execute(select(RefreshToken).where(RefreshToken.token == token))
        return result.scalar_one_or_none()

    async def get_valid_token(self, token: str) -> RefreshToken | None:
        """
        获取有效的刷新令牌

        Args:
            token: 令牌字符串

        Returns:
            有效的刷新令牌实例，不存在或无效则返回 None
        """
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.token == token,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > datetime.now(UTC),
            )
        )
        return result.scalar_one_or_none()

    async def get_user_tokens(self, user_id: int) -> list[RefreshToken]:
        """
        获取用户的所有刷新令牌

        Args:
            user_id: 用户 ID

        Returns:
            刷新令牌列表
        """
        result = await self.session.execute(
            select(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .order_by(RefreshToken.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_user_tokens(self, user_id: int) -> list[RefreshToken]:
        """
        获取用户的有效刷新令牌

        Args:
            user_id: 用户 ID

        Returns:
            有效的刷新令牌列表
        """
        result = await self.session.execute(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > datetime.now(UTC),
            )
            .order_by(RefreshToken.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke_token(self, token: str) -> bool:
        """
        撤销刷新令牌

        Args:
            token: 令牌字符串

        Returns:
            成功返回 True
        """
        refresh_token = await self.get_by_token(token)
        if refresh_token is None:
            return False
        refresh_token.revoked = True
        await self.session.flush()
        return True

    async def revoke_all_user_tokens(self, user_id: int) -> int:
        """
        撤销用户所有刷新令牌

        Args:
            user_id: 用户 ID

        Returns:
            撤销的令牌数
        """
        tokens = await self.get_active_user_tokens(user_id)
        count = 0
        for token in tokens:
            token.revoked = True
            count += 1
        await self.session.flush()
        return count

    async def cleanup_expired_tokens(self) -> int:
        """
        清理过期的刷新令牌

        Returns:
            删除的令牌数
        """
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < datetime.now(UTC))
        )
        await self.session.flush()
        return result.rowcount


class UserTitleRepository(BaseRepository[UserTitle]):
    """
    用户头衔仓储类

    提供用户头衔相关的数据库操作方法。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化用户头衔仓储

        Args:
            session: 异步数据库会话
        """
        super().__init__(UserTitle, session)

    async def get_by_name(self, name: str) -> UserTitle | None:
        """
        根据名称获取头衔

        Args:
            name: 头衔名称

        Returns:
            头衔实例，不存在则返回 None
        """
        result = await self.session.execute(select(UserTitle).where(UserTitle.name == name))
        return result.scalar_one_or_none()

    async def get_all_active(self) -> list[UserTitle]:
        """
        获取所有头衔

        Returns:
            头衔列表
        """
        result = await self.session.execute(select(UserTitle).order_by(UserTitle.created_at.desc()))
        return list(result.scalars().all())
