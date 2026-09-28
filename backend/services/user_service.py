"""
用户服务层

封装用户相关的业务逻辑，包括：
- 用户注册
- 用户登录
- 用户登出
- 用户资料获取和更新
- 缓存集成
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import make_transient

from backend.core.auth import (
    _add_jti_to_blacklist,
    aget_password_hash,
    averify_password,
    averify_password_with_rehash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.core.config import settings
from backend.core.partial_update import apply_partial_update
from backend.models.blog import Post
from backend.models.user import User, UserPreference
from backend.repositories.user import (
    RefreshTokenRepository,
    UserPreferenceRepository,
    UserRepository,
)
from backend.services._avatar_helpers import resolved_for_user
from backend.services.cache_service import CacheService
from backend.services.post_cache import invalidate_post_caches_by_slugs
from backend.utils.compat import UTC, timedelta

logger = logging.getLogger(__name__)

USER_PROFILE_TTL = 300
USER_STATS_TTL = 60

# 偏好可写字段 = UserPreference 的列全集减去身份列与时间戳。
# 这里刻意不手写名单：旧实现写死 ["theme", "public_profile"]，于是 show_email、
# show_posts、show_comments、show_stats 四个隐私开关从 API 传进来被**静默丢弃**——
# 接口返回 200、前端提示"已保存"、库里一个字节都没改，用户以为邮箱已经隐藏其实一直暴露。
# 以模型为唯一事实源，加列时不会再出现"服务层漏掉"的第二个真相。
PREFERENCE_WRITABLE_FIELDS: frozenset[str] = frozenset(
    str(attr.key) for attr in inspect(UserPreference).mapper.column_attrs
) - {"id", "user_id", "created_at", "updated_at"}

# 会被嵌进文章详情缓存 author 段的展示字段（见 blog._build_author_data）。
# 只有这些字段变更才需要顺带失效文章缓存；email/qq/password 等隐私字段不进 author 段。
_AUTHOR_VISIBLE_FIELDS: frozenset[str] = frozenset(
    {"username", "nickname", "avatar", "bio", "website", "github", "cover_image"}
)


def _detach_for_cache(*instances: object | None) -> None:
    """把要进响应缓存的 ORM 实例摘成 transient（只用于**只读**载荷）。

    缓存载荷跨请求复用，但实例的所有权属于「第一次那次请求」的会话：请求结束时该会话
    commit / close，`expire_on_commit=True` 会把实例的全部属性标成过期。下一次命中缓存
    的请求再读任何一个属性（隐私闸门要读 ``preferences.public_profile``、邮箱遮蔽要读
    ``show_email``、组装响应要读用户列）都会走延迟刷新，而它已经没有会话可刷了 ——
    ``DetachedInstanceError`` → HTTP 500。表现为「同一个作者主页，第一次 404/200 正常，
    TTL 内的第二次请求起报服务器错误」。

    ``make_transient`` 把实例从 identity map 里摘掉：属性保持已加载的值，后续 commit
    也不再碰它。代价是这份载荷只读（改字段再 flush 不会落库），所以只对展示路径使用。
    """
    for obj in instances:
        if obj is not None:
            make_transient(obj)  # type: ignore[arg-type]


class UserService:
    """
    用户服务类

    封装用户相关的业务逻辑，使用 UserRepository 进行数据访问，
    集成缓存提高性能。

    Attributes:
        db: 数据库会话
        user_repo: 用户仓储实例
        token_repo: 刷新令牌仓储实例
        preference_repo: 用户偏好设置仓储实例
        cache: 缓存服务实例

    Example:
        >>> async with get_db_context() as db:
        ...     service = UserService(db)
        ...     user = await service.register(username="test", email="test@example.com", password="password")
    """

    def __init__(
        self,
        db: AsyncSession,
        cache: CacheService | None = None,
    ):
        """
        初始化用户服务

        Args:
            db: 数据库会话
            cache: 缓存服务实例，None 则创建新实例
        """
        self._db = db
        self._user_repo = UserRepository(db)
        self._token_repo = RefreshTokenRepository(db)
        self._preference_repo = UserPreferenceRepository(db)
        self._cache = cache or CacheService()

    async def register(
        self,
        username: str,
        email: str,
        password: str,
        nickname: str | None = None,
    ) -> dict[str, Any]:
        """
        用户注册

        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            nickname: 昵称

        Returns:
            包含用户信息和令牌的字典

        Raises:
            ValueError: 用户名或邮箱已存在
        """
        if await self._user_repo.username_exists(username):
            raise ValueError("用户名已存在")

        if await self._user_repo.email_exists(email):
            raise ValueError("邮箱已被注册")

        password_hash = await aget_password_hash(password)

        user = await self._user_repo.create(
            {
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "nickname": nickname or username,
                "is_active": True,
            }
        )

        await self._preference_repo.get_or_create_for_user(user.id)

        access_token = create_access_token({"sub": str(user.id)})
        refresh_token_str, _jti = create_refresh_token(
            {"sub": str(user.id)},
            user_token_version=getattr(user, "token_version", 0) or 0,
        )
        refresh_token = await self._token_repo.create(
            {
                "token": refresh_token_str,
                "user_id": user.id,
                "expires_at": datetime.now(UTC)
                + timedelta(days=settings.refresh_token_expire_days),
            }
        )

        await self._db.commit()

        logger.info(f"用户注册成功: id={user.id}, username={username}")

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token.token,
            "token_type": "bearer",
        }

    async def login(
        self,
        identifier: str,
        password: str,
    ) -> dict[str, Any]:
        """
        用户登录

        Args:
            identifier: 用户名或邮箱
            password: 密码

        Returns:
            包含用户信息和令牌的字典

        Raises:
            ValueError: 凭据无效或用户状态异常
        """
        user = await self._user_repo.get_by_username_or_email_case_insensitive(identifier)

        if user is None:
            raise ValueError("用户名或密码错误")

        pwd_ok, need_rehash = await averify_password_with_rehash(password, user.password_hash)
        if not pwd_ok:
            raise ValueError("用户名或密码错误")

        # bcrypt → argon2id 平滑升级：首次登录成功就重新保存为 argon2 哈希
        if need_rehash:
            try:
                user.password_hash = await aget_password_hash(password)
                await self._db.flush()
            except Exception as e:  # noqa: BLE001
                logger.warning(f"用户 {user.id} 密码 rehash (bcrypt→argon2id) 失败：{e}")

        if not user.is_active:
            raise ValueError("用户账号未激活")

        if user.is_banned:
            raise ValueError("用户已被封禁")

        await self._user_repo.update_last_login(user.id)

        access_token = create_access_token({"sub": str(user.id)})
        refresh_token_str, _jti = create_refresh_token(
            {"sub": str(user.id)},
            user_token_version=getattr(user, "token_version", 0) or 0,
        )
        refresh_token = await self._token_repo.create(
            {
                "token": refresh_token_str,
                "user_id": user.id,
                "expires_at": datetime.now(UTC)
                + timedelta(days=settings.refresh_token_expire_days),
            }
        )

        await self._db.commit()

        await self._cache.invalidate_user_cache(user.id)

        logger.info(f"用户登录成功: id={user.id}, username={user.username}")

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token.token,
            "token_type": "bearer",
        }

    async def logout(
        self,
        user_id: int,
        refresh_token: str | None = None,
        all_sessions: bool = False,
    ) -> bool:
        """
        用户登出

        Args:
            user_id: 用户 ID
            refresh_token: 刷新令牌，None 则只撤销当前令牌
            all_sessions: 是否撤销所有会话

        Returns:
            登出成功返回 True
        """
        if all_sessions:
            count = await self._token_repo.revoke_all_user_tokens(user_id)
            logger.info(f"用户登出所有会话: user_id={user_id}, revoked={count}")
        elif refresh_token:
            await self._token_repo.revoke_token(refresh_token)
            logger.info(f"用户登出: user_id={user_id}")

        await self._cache.invalidate_user_cache(user_id)

        return True

    async def refresh_access_token(
        self,
        refresh_token_str: str,
    ) -> dict[str, Any] | None:
        """
        刷新访问令牌（JWT rotate：单次使用 + version 校验）

        流程：
          1. 解析 refresh token，取 sub/version/jti/ttl_days
          2. 查 DB user.token_version，不一致 → TOKEN_VERSION_MISMATCH
          3. jti 是否已在黑名单 → TOKEN_REUSED
          4. jti 加入黑名单，user.token_version += 1 commit
          5. 生成新 access + refresh 返回

        Returns:
            dict 或 None；业务异常通过 ValueError 抛出
        """
        from backend.core.auth import _is_jti_blacklisted

        payload = decode_token(refresh_token_str)
        if payload is None or payload.get("type") != "refresh":
            raise ValueError("无效或过期的刷新令牌")

        user_id_raw = payload.get("sub")
        old_version = payload.get("version")
        jti = payload.get("jti")
        ttl_days = int(payload.get("ttl_days") or settings.refresh_token_expire_days)

        if user_id_raw is None or old_version is None or jti is None:
            raise ValueError("无效或过期的刷新令牌")

        try:
            user_id = int(user_id_raw)
            old_version_int = int(old_version)
        except (TypeError, ValueError) as err:
            raise ValueError("无效或过期的刷新令牌") from err

        db_token = await self._token_repo.get_valid_token(refresh_token_str)

        user = await self._user_repo.get_by_id(user_id)
        if user is None or not user.is_active or user.is_banned:
            raise ValueError("用户状态异常或不存在")

        current_version = getattr(user, "token_version", 0) or 0

        if await _is_jti_blacklisted(jti):
            raise ValueError("TOKEN_REUSED")

        if current_version != old_version_int:
            raise ValueError("TOKEN_VERSION_MISMATCH")

        # 消费 SET NX 的原子结果：上面的 _is_jti_blacklisted 与写入之间仍有窗口，
        # 两个并发刷新可能同时通过预检；以"本次是否首次拉黑"为最终判据。
        if not await _add_jti_to_blacklist(jti, ttl_days):
            raise ValueError("TOKEN_REUSED")

        user.token_version = current_version + 1
        await self._db.flush()

        access_token = create_access_token({"sub": str(user.id)})
        new_refresh_token_str, _new_jti = create_refresh_token(
            {"sub": str(user.id)},
            user_token_version=user.token_version,
        )

        if db_token is not None:
            db_token.revoked = True
            db_token.token = new_refresh_token_str
            db_token.expires_at = datetime.now(UTC) + timedelta(
                days=settings.refresh_token_expire_days
            )
        else:
            await self._token_repo.create(
                {
                    "token": new_refresh_token_str,
                    "user_id": user.id,
                    "expires_at": datetime.now(UTC)
                    + timedelta(days=settings.refresh_token_expire_days),
                }
            )

        await self._db.commit()
        await self._cache.invalidate_user_cache(user.id)

        logger.info(f"令牌刷新(rotate)成功: user_id={user.id}, new_version={user.token_version}")

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token_str,
            "token_type": "bearer",
        }

    async def get_user_profile(
        self,
        user_id: int,
        current_user_id: int | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any] | None:
        """
        获取用户资料

        Args:
            user_id: 用户 ID
            current_user_id: 当前用户 ID（用于判断是否为自己）
            use_cache: 是否使用缓存

        Returns:
            用户资料字典，不存在返回 None
        """
        cache_key = self._cache.build_key("user_profile", user_id)

        async def fetch():
            """只取「与谁在看无关」的原始资料。

            请求者相关的字段（is_self、隐私门收窄后的精简视图、is_public）一律在
            缓存之外推导（见 ``_decorate_profile_for_viewer``）：缓存键只按被查看的
            user_id 生成，如果把 `current_user_id` 的判断结果一起缓存，本人或管理员
            看过一次之后，缓存里就带着 ``is_self: True`` 与明文邮箱，
            紧接着的匿名请求会原样拿到这份特权视图。
            """
            profile = await self._user_repo.get_full_profile(user_id)
            if profile is None:
                return None

            payload = {
                "user": profile["user"],
                "title": profile["title"],
                "preferences": profile["preferences"],
                "post_count": profile["post_count"],
                "comment_count": profile["comment_count"],
            }
            _detach_for_cache(payload["user"], payload["title"], payload["preferences"])
            return payload

        raw = (
            await self._cache.get_or_set(cache_key, fetch, ttl=USER_PROFILE_TTL)
            if use_cache
            else await fetch()
        )
        if raw is None:
            return None

        return self._decorate_profile_for_viewer(raw, user_id, current_user_id)

    @staticmethod
    def _decorate_profile_for_viewer(
        raw: dict[str, Any],
        user_id: int,
        current_user_id: int | None,
    ) -> dict[str, Any]:
        """按查看者身份推导资料视图：非本人且关了「公开资料」开关时只回最小字段。"""
        user = raw["user"]
        preferences = raw["preferences"]

        if current_user_id != user_id and preferences and not preferences.public_profile:
            return {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "nickname": user.nickname,
                    "avatar": user.avatar,
                    "title": user.title,
                    "qq": getattr(user, "qq", None),
                    "github": user.github,
                    "website": user.website,
                    "avatar_source": getattr(user, "avatar_source", "auto"),
                    "resolved_avatar_url": resolved_for_user(user),
                },
                "is_public": False,
            }

        return {
            "user": user,
            "title": raw["title"],
            "preferences": preferences,
            "post_count": raw["post_count"],
            "comment_count": raw["comment_count"],
            "is_public": True,
            "is_self": current_user_id == user_id,
        }

    async def update_profile(
        self,
        user_id: int,
        data: dict[str, Any],
    ) -> User | None:
        """
        更新用户资料

        Args:
            user_id: 用户 ID
            data: 更新数据

        Returns:
            更新后的用户实例，不存在返回 None

        Raises:
            ValueError: 用户名或邮箱已被使用
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            return None

        if "username" in data and data["username"] != user.username:
            if await self._user_repo.username_exists(data["username"], exclude_id=user_id):
                raise ValueError("用户名已存在")

        if "email" in data and data["email"] != user.email:
            if await self._user_repo.email_exists(data["email"], exclude_id=user_id):
                raise ValueError("邮箱已被使用")

        if "password" in data:
            data["password_hash"] = await aget_password_hash(data["password"])
            del data["password"]

        allowed_fields = [
            "username",
            "email",
            "password_hash",
            "nickname",
            "bio",
            "avatar",
            "cover_image",
            "website",
            "github",
            "qq",
            "avatar_source",
        ]
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        updated_user = await self._user_repo.update(user, update_data)

        await self._cache.invalidate_user_cache(user_id)

        # 作者可见资料会被写进文章详情缓存的 author 段（见 blog._build_author_data），
        # 而该缓存 key 是 `post:{slug}:{lang}`，invalidate_user_cache 覆盖不到。
        # 仅当本次改动确实命中这些展示字段时，才失效该作者全部文章的详情/列表缓存。
        if update_data.keys() & _AUTHOR_VISIBLE_FIELDS:
            await self._invalidate_author_post_caches(user_id)

        logger.info(f"用户资料更新成功: id={user_id}")

        return updated_user

    async def _invalidate_author_post_caches(self, user_id: int) -> None:
        """失效某作者全部文章的详情缓存与列表/RSS 缓存（作者资料变更后调用）。"""
        rows = await self._db.execute(select(Post.slug).where(Post.author_id == user_id))
        await invalidate_post_caches_by_slugs(rows.scalars().all())

    async def update_preferences(
        self,
        user_id: int,
        data: dict[str, Any],
    ) -> UserPreference | None:
        """
        更新用户偏好设置

        Args:
            user_id: 用户 ID
            data: 更新数据

        Returns:
            更新后的偏好设置实例
        """
        preference = await self._preference_repo.get_by_user_id(user_id)
        if preference is None:
            preference = await self._preference_repo.get_or_create_for_user(user_id)

        allowed_fields = PREFERENCE_WRITABLE_FIELDS
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        if len(update_data) != len(data):
            # 只可能发生在"模型加了列、Schema 没加"或反之：静默丢弃就是这次修复要消灭的 bug 类，
            # 至少留一条日志，别让"接口 200 但什么都没保存"再次无声发生。
            logger.warning(
                "更新偏好丢弃未知字段: %s",
                sorted(set(data) - set(update_data)),
            )

        # 偏好六个列全是 NOT NULL（客户端显式传 null 会撞 flush → 500），
        # 走统一守卫而不是裸 setattr。
        apply_partial_update(preference, update_data)

        await self._db.flush()
        await self._db.refresh(preference)

        await self._cache.invalidate_user_cache(user_id)

        logger.info(f"用户偏好设置更新成功: user_id={user_id}")

        return preference

    async def change_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str,
    ) -> bool:
        """
        修改密码

        Args:
            user_id: 用户 ID
            old_password: 旧密码
            new_password: 新密码

        Returns:
            修改成功返回 True

        Raises:
            ValueError: 旧密码错误
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            return False

        if not await averify_password(old_password, user.password_hash):
            raise ValueError("旧密码错误")

        if await averify_password(new_password, user.password_hash):
            raise ValueError("新密码不能与当前密码相同")

        user.password_hash = await aget_password_hash(new_password)
        current_v = getattr(user, "token_version", 0) or 0
        user.token_version = current_v + 1
        await self._db.flush()

        await self._token_repo.revoke_all_user_tokens(user_id)

        await self._cache.invalidate_user_cache(user_id)

        logger.info(f"用户密码修改成功: id={user_id}")

        return True

    async def get_user_by_id(
        self,
        user_id: int,
    ) -> User | None:
        """
        根据 ID 获取用户（**总是读库，不走缓存**）。

        Args:
            user_id: 用户 ID

        Returns:
            用户实例，不存在返回 None

        这里曾经带 300 秒缓存，而六个调用点全在后台**写**路径上（重置密码、删除用户、
        封禁、改 staff、改头像来源…）。缓存命中时返回的是别的请求会话里的实例：
        那次请求结束、会话 commit 之后属性全部过期，读任何一个属性直接
        ``DetachedInstanceError``（500）；而改字段再 flush 作用在当前会话上，
        那个已脱离会话的对象根本不在 unit of work 里 —— 接口回 200、库里一个字节都没改，
        管理员看到"操作成功"但状态没变，还会把这份特权/过期对象继续供给别人。
        写路径必须拿到当前会话的持久实例，所以这里不再缓存。
        """
        return await self._user_repo.get_by_id(user_id)

    async def get_user_by_username(
        self,
        username: str,
    ) -> User | None:
        """
        根据用户名获取用户

        Args:
            username: 用户名

        Returns:
            用户实例，不存在返回 None
        """
        return await self._user_repo.get_by_username_case_insensitive(username)

    async def get_user_by_email(
        self,
        email: str,
    ) -> User | None:
        """
        根据邮箱获取用户

        Args:
            email: 邮箱

        Returns:
            用户实例，不存在返回 None
        """
        return await self._user_repo.get_by_email_case_insensitive(email)

    async def get_active_users(
        self,
        skip: int = 0,
        limit: int = 20,
    ) -> list[User]:
        """
        获取活跃用户列表

        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            活跃用户列表
        """
        return await self._user_repo.get_active_users(skip, limit)

    async def get_staff_users(self) -> list[User]:
        """
        获取管理员用户列表

        Returns:
            管理员用户列表
        """
        return await self._user_repo.get_staff_users()

    async def search_users(
        self,
        keyword: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[User]:
        """
        搜索用户

        Args:
            keyword: 搜索关键词
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            用户列表
        """
        return await self._user_repo.search_users(keyword, skip, limit)

    async def ban_user(
        self,
        user_id: int,
    ) -> bool:
        """
        封禁用户

        Args:
            user_id: 用户 ID

        Returns:
            成功返回 True
        """
        success = await self._user_repo.ban_user(user_id)
        if success:
            await self._token_repo.revoke_all_user_tokens(user_id)
            await self._cache.invalidate_user_cache(user_id)
            logger.info(f"用户已封禁: id={user_id}")
        return success

    async def unban_user(
        self,
        user_id: int,
    ) -> bool:
        """
        解封用户

        Args:
            user_id: 用户 ID

        Returns:
            成功返回 True
        """
        success = await self._user_repo.unban_user(user_id)
        if success:
            await self._cache.invalidate_user_cache(user_id)
            logger.info(f"用户已解封: id={user_id}")
        return success

    async def activate_user(
        self,
        user_id: int,
    ) -> bool:
        """
        激活用户

        Args:
            user_id: 用户 ID

        Returns:
            成功返回 True
        """
        success = await self._user_repo.activate_user(user_id)
        if success:
            await self._cache.invalidate_user_cache(user_id)
            logger.info(f"用户已激活: id={user_id}")
        return success

    async def deactivate_user(
        self,
        user_id: int,
    ) -> bool:
        """
        停用用户

        Args:
            user_id: 用户 ID

        Returns:
            成功返回 True
        """
        success = await self._user_repo.deactivate_user(user_id)
        if success:
            await self._token_repo.revoke_all_user_tokens(user_id)
            await self._cache.invalidate_user_cache(user_id)
            logger.info(f"用户已停用: id={user_id}")
        return success

    async def set_staff_status(
        self,
        user_id: int,
        is_staff: bool,
    ) -> bool:
        """
        设置管理员状态

        Args:
            user_id: 用户 ID
            is_staff: 是否为管理员

        Returns:
            成功返回 True
        """
        success = await self._user_repo.set_staff_status(user_id, is_staff)
        if success:
            await self._cache.invalidate_user_cache(user_id)
            logger.info(f"用户管理员状态更新: id={user_id}, is_staff={is_staff}")
        return success

    async def get_user_stats(
        self,
        user_id: int,
        use_cache: bool = True,
    ) -> dict[str, Any] | None:
        """
        获取用户统计数据

        Args:
            user_id: 用户 ID
            use_cache: 是否使用缓存

        Returns:
            统计数据字典
        """
        cache_key = self._cache.build_key("user_stats", user_id)

        async def fetch():
            profile = await self._user_repo.get_full_profile(user_id)
            if profile is None:
                return None

            return {
                "post_count": profile["post_count"],
                "comment_count": profile["comment_count"],
            }

        if use_cache:
            return await self._cache.get_or_set(
                cache_key,
                fetch,
                ttl=USER_STATS_TTL,
            )

        return await fetch()

    async def validate_user_status(
        self,
        user_id: int,
    ) -> dict[str, Any]:
        """
        验证用户状态

        Args:
            user_id: 用户 ID

        Returns:
            用户状态信息
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            return {
                "valid": False,
                "reason": "用户不存在",
            }

        if not user.is_active:
            return {
                "valid": False,
                "reason": "用户未激活",
            }

        if user.is_banned:
            return {
                "valid": False,
                "reason": "用户已被封禁",
            }

        return {
            "valid": True,
            "user": user,
        }


async def get_user_service(
    db: AsyncSession,
    cache: CacheService | None = None,
) -> UserService:
    """
    获取用户服务实例（依赖注入）

    Args:
        db: 数据库会话
        cache: 缓存服务实例

    Returns:
        UserService 实例
    """
    return UserService(db, cache)
