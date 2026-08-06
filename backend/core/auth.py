"""
Rosetta FastAPI 后端 - 认证模块

提供完整的 JWT 认证系统，包括：
- 密码哈希和验证
- JWT 令牌生成和验证（支持 kid, jti, version）
- 访问令牌和刷新令牌（支持 rotate + 单次使用）
- 刷新令牌黑名单（Redis/内存）
- 用户认证依赖注入

Example:
    >>> from backend.core.auth import get_current_user, CurrentUser
    >>>
    >>> @router.get("/me")
    >>> async def get_me(user: CurrentUser):
    >>>     return user
"""

import asyncio
import base64
import hashlib
import logging
import uuid
from contextlib import suppress
from datetime import datetime
from typing import Annotated, Any

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import cache
from backend.core.config import settings
from backend.core.database import get_db
from backend.models.user import User
from backend.utils.compat import UTC, timedelta

logger = logging.getLogger(__name__)

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)

REFRESH_BLACKLIST_PREFIX = "refresh_blacklist"
MEMORY_REFRESH_BLACKLIST: set[str] = set()
_MEMORY_BLACKLIST_LOCK = asyncio.Lock()


async def _add_jti_to_blacklist(jti: str, ttl_days: int) -> None:
    """
    将 refresh token 的 jti 加入黑名单

    Args:
        jti: JWT ID
        ttl_days: 过期天数
    """
    ttl = int(ttl_days * 86400) + 86400
    key = f"{REFRESH_BLACKLIST_PREFIX}:{jti}"

    try:
        redis_backend = getattr(cache, "backend", None)
        if redis_backend and settings.redis_enabled and hasattr(redis_backend, "_get_client"):
            client = await redis_backend._get_client()
            if getattr(redis_backend, "_connected", False):
                await client.setex(key, ttl, "1")
                return
    except Exception as e:
        logger.warning(f"Redis 黑名单写入失败，回退到内存: {e}")

    async with _MEMORY_BLACKLIST_LOCK:
        MEMORY_REFRESH_BLACKLIST.add(jti)


async def _is_jti_blacklisted(jti: str) -> bool:
    """
    检查 jti 是否已在黑名单（已被使用过）

    Args:
        jti: JWT ID

    Returns:
        bool: True = 已使用/无效
    """
    key = f"{REFRESH_BLACKLIST_PREFIX}:{jti}"

    try:
        redis_backend = getattr(cache, "backend", None)
        if redis_backend and settings.redis_enabled and hasattr(redis_backend, "_get_client"):
            client = await redis_backend._get_client()
            if getattr(redis_backend, "_connected", False):
                return await client.exists(key) > 0
    except Exception as e:
        logger.warning(f"Redis 黑名单读取失败，回退到内存: {e}")

    async with _MEMORY_BLACKLIST_LOCK:
        return jti in MEMORY_REFRESH_BLACKLIST


def get_password_hash(password: str) -> str:
    """
    生成密码哈希

    使用 bcrypt 算法生成安全的密码哈希。
    bcrypt 5.0.0+ 要求密码不超过 72 字节。
    对于超长密码，先使用 SHA-256 哈希后再用 bcrypt 处理。

    Args:
        password: 明文密码

    Returns:
        str: 哈希后的密码
    """
    password_bytes = password.encode("utf-8")

    if len(password_bytes) > 72:
        password_bytes = base64.b64encode(hashlib.sha256(password_bytes).digest())

    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)

    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码

    Returns:
        bool: 密码匹配返回 True
    """
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")

    if len(password_bytes) > 72:
        password_bytes = base64.b64encode(hashlib.sha256(password_bytes).digest())

    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    创建访问令牌

    Args:
        data: 要编码的数据，通常包含用户 ID
        expires_delta: 自定义过期时间

    Returns:
        str: JWT 访问令牌
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update(
        {
            "exp": expire,
            "type": "access",
            "iat": datetime.now(UTC),
        }
    )

    headers = {"kid": "default"}
    return jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
        headers=headers,
    )


def create_refresh_token(
    data: dict[str, Any],
    *,
    user_token_version: int = 0,
    expires_delta: timedelta | None = None,
) -> tuple[str, str]:
    """
    创建刷新令牌

    刷新令牌有效期更长，用于获取新的访问令牌。
    每次生成会携带：
      - version: user.token_version（密码变更时自增）
      - type: "refresh"
      - jti: uuid，一次性令牌标识
      - iat / exp

    Args:
        data: 要编码的数据，通常包含用户 ID
        user_token_version: 用户的 token_version 字段值
        expires_delta: 自定义过期时间

    Returns:
        tuple[str, str]: (refresh_token, jti)
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
        expire_days = expires_delta.days or settings.refresh_token_expire_days
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
        expire_days = settings.refresh_token_expire_days

    jti = str(uuid.uuid4())

    to_encode.update(
        {
            "exp": expire,
            "type": "refresh",
            "iat": datetime.now(UTC),
            "version": user_token_version,
            "jti": jti,
            "ttl_days": expire_days,
        }
    )

    headers = {"kid": "default"}
    token = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
        headers=headers,
    )
    return token, jti


def decode_token(token: str) -> dict[str, Any] | None:
    """
    解码 JWT 令牌

    Args:
        token: JWT 令牌字符串

    Returns:
        dict | None: 解码后的数据，解码失败返回 None
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    获取当前认证用户（必需认证）

    Args:
        credentials: HTTP Bearer 凭据
        db: 数据库会话

    Returns:
        User: 当前用户

    Raises:
        HTTPException: 令牌无效或用户状态异常
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise credentials_exception

    if payload.get("type") != "access":
        raise credentials_exception  # pragma: no cover

    user_id: int | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id_int))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号未激活",
        )

    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被封禁",
        )

    return user


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_optional)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """
    获取当前用户（可选认证）

    如果提供了有效令牌则返回用户，否则返回 None。
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None or payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        return None

    result = await db.execute(select(User).where(User.id == user_id_int))
    user = result.scalar_one_or_none()

    if user and user.is_active and not user.is_banned:
        return user

    return None


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号未激活",
        )
    return current_user


async def _write_permission_denied_log(
    request: Request | None,
    db: AsyncSession,
    user: User,
    *,
    detail: str,
    resource: str,
) -> None:
    """统一记录权限越权日志（不抛出异常）。"""
    with suppress(Exception):
        from backend.core.logging_middleware import log_operation

        await log_operation(
            db,
            request,
            user_id=user.id,
            action="permission",
            target_type=resource,
            target_id=None,
            details={
                "reason": detail,
                "role": getattr(user, "role", None),
                "is_staff": getattr(user, "is_staff", None),
                "is_superuser": getattr(user, "is_superuser", None),
            },
            status="failed",
            error_code="PERMISSION_DENIED",
            commit=True,
        )


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """获取当前超级管理员"""
    if not current_user.is_superuser:
        await _write_permission_denied_log(
            request, db, current_user, detail="需要超级管理员权限", resource="admin:superuser"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限",
        )
    return current_user


async def get_current_staff(
    current_user: Annotated[User, Depends(get_current_user)],
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """获取当前管理员"""
    if not (current_user.is_staff or current_user.is_superuser):
        await _write_permission_denied_log(
            request, db, current_user, detail="需要管理员权限", resource="admin:staff"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


async def validate_token(token: str, db: AsyncSession) -> User | None:
    """
    验证令牌并返回用户

    Args:
        token: JWT 令牌
        db: 数据库会话

    Returns:
        User | None: 用户对象或 None
    """
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        return None

    result = await db.execute(select(User).where(User.id == user_id_int))
    user = result.scalar_one_or_none()

    if user and user.is_active and not user.is_banned:
        return user

    return None


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserOptional = Annotated[User | None, Depends(get_current_user_optional)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentSuperUser = Annotated[User, Depends(get_current_superuser)]
CurrentStaff = Annotated[User, Depends(get_current_staff)]
DB = Annotated[AsyncSession, Depends(get_db)]
