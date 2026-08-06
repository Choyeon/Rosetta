"""
用户管理 API

提供用户注册、登录、信息管理等功能。

性能优化：
- 使用服务层封装业务逻辑
- 使用仓储层进行数据访问
- 使用缓存减少数据库查询
- 使用并发查询优化
"""

import math
import random
import secrets
import string
from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.core.auth import (
    DB,
    CurrentUser,
    CurrentUserOptional,
    get_password_hash,
    verify_password,
)
from backend.core.cache import cache
from backend.core.concurrency import concurrent_query
from backend.core.config import settings
from backend.core.exceptions import AppException
from backend.core.password_policy import validate_password
from backend.core.rate_limit import rate_limit_sensitive, rate_limit_write
from backend.models.blog import Comment, Post, post_likes
from backend.models.user import User, UserPreference
from backend.schemas import (
    BaseResponse,
    LoginRequest,
    PaginatedResponse,
    PasswordChange,
    TokenResponse,
    UserCreate,
    UserPreferenceResponse,
    UserPreferenceUpdate,
    UserResponse,
    UserUpdate,
)
from backend.api._user_response_helper import build_user_response
from backend.services.user_service import get_user_service
from backend.utils.compat import UTC

router = APIRouter(tags=["用户"])

PREFIX = "password_reset"


class _PasswordResetRequest(BaseModel):
    email_or_username: str = Field(..., min_length=1, max_length=255, description="邮箱或用户名")


class _PasswordResetBody(BaseModel):
    token_or_email: str = Field(
        ..., min_length=1, max_length=255, description="邮箱或用户名或 reset_token"
    )
    code: str = Field(..., min_length=6, max_length=6, description="6 位数字验证码")
    new_password: str = Field(..., min_length=1, max_length=255, description="新密码")


class _PasswordChangeBody(BaseModel):
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., description="新密码")


async def _gen_reset_code_and_token(user: User) -> tuple[str, str]:
    """生成 6 位 code + 32 位 token 并写入缓存 15 分钟"""
    digits = string.digits
    code = "".join(random.choices(digits, k=6))
    token = secrets.token_hex(16)
    ttl = 15 * 60

    key_code = f"{PREFIX}:code:{user.id}"
    key_token = f"{PREFIX}:token:{user.id}"
    key_meta = f"{PREFIX}:meta:{user.id}"

    await cache.set(key_code, code, ttl=ttl)
    await cache.set(key_token, token, ttl=ttl)
    await cache.set(key_meta, {"email": user.email or user.username}, ttl=ttl)

    return code, token


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description="注册新用户账号，成功后自动登录返回令牌。",
)
async def register(
    user_data: UserCreate,
    db: DB,
    _rl=Depends(rate_limit_sensitive("register")),
):
    """用户注册"""
    if not settings.enable_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="注册功能已关闭",
        )

    errors = validate_password(user_data.password)
    if errors:
        raise AppException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=errors[0],
            error_code="WEAK_PASSWORD",
            details={"errors": errors},
        )

    service = await get_user_service(db)
    try:
        result = await service.register(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            nickname=user_data.nickname,
        )
    except ValueError as e:
        msg = str(e)
        # 统一业务错误码：注册类业务校验统一使用 422
        if "用户名" in msg and "已存在" in msg:
            code = "USERNAME_EXISTS"
        elif "邮箱" in msg and ("已被注册" in msg or "已被使用" in msg):
            code = "EMAIL_TAKEN"
        else:
            code = "REGISTER_FAILED"
        raise AppException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=msg,
            error_code=code,
        )

    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="用户登录",
    description="使用用户名或邮箱登录，返回访问令牌和刷新令牌。",
)
async def login(
    request: Request,
    data: LoginRequest,
    db: DB,
    _rl=Depends(rate_limit_sensitive("login")),
):
    """用户登录（含账号锁定 + 失败计数）"""
    from contextlib import suppress

    from backend.core.logging_middleware import log_operation

    stmt = select(User).where((User.username == data.username) | (User.email == data.username))
    r = await db.execute(stmt)
    user: User | None = r.scalar_one_or_none()

    # Step 1: 即使账号不存在也做延迟/锁定检查？这里不泄露账号是否存在，仅对已知 user 做锁定
    if user is not None:
        now = datetime.now(UTC)
        if user.locked_until is not None and user.locked_until > now:
            wait_secs = int((user.locked_until - now).total_seconds())
            headers = {"Retry-After": str(wait_secs)}
            with suppress(Exception):
                await log_operation(
                    db,
                    request,
                    user_id=user.id,
                    action="login",
                    target_type="users",
                    target_id=user.id,
                    details={"retry_after_seconds": wait_secs},
                    status="failed",
                    error_code="ACCOUNT_LOCKED",
                    commit=True,
                )
            raise HTTPException(
                status_code=423,
                detail={
                    "message": "账号因多次登录失败已被暂时锁定",
                    "retry_after_seconds": wait_secs,
                    "error_code": "ACCOUNT_LOCKED",
                },
                headers=headers,
            )
        # 锁定到期重置失败计数
        if user.locked_until is not None and user.locked_until <= now:
            user.failed_login_attempts = 0
            user.locked_until = None
            await db.flush()

    service = await get_user_service(db)
    try:
        result = await service.login(
            identifier=data.username,
            password=data.password,
        )
    except ValueError:
        # 登录失败 → 计数 +1，达到阈值则锁定
        if user is not None:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            max_attempts = getattr(settings, "max_login_attempts", 10)
            if user.failed_login_attempts >= max_attempts:
                lock_min = getattr(settings, "login_lockout_minutes", 10)
                user.locked_until = datetime.now(UTC) + timedelta(minutes=lock_min)
                user.failed_login_attempts = max_attempts
            await db.commit()
        with suppress(Exception):
            await log_operation(
                db,
                request,
                user_id=getattr(user, "id", None),
                action="login",
                target_type="users",
                target_id=getattr(user, "id", None),
                details={"identifier": data.username},
                status="failed",
                error_code="AUTH_INVALID_CREDENTIALS",
                commit=True,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名/邮箱或密码错误",
        )

    # 登录成功 → 重置失败计数
    if user is not None and user.failed_login_attempts or user is not None and user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None
        await db.commit()

    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="刷新令牌",
    description="使用刷新令牌获取新的访问令牌（rotate：单次使用）。",
)
async def refresh_token(
    refresh_token: str = Body(..., embed=True, description="刷新令牌"),
    db: DB = None,
    _rl=Depends(rate_limit_sensitive("refresh")),
):
    """刷新访问令牌（JWT rotate）"""
    service = await get_user_service(db)
    try:
        result = await service.refresh_access_token(refresh_token)
    except ValueError as e:
        msg = str(e)
        if msg == "TOKEN_VERSION_MISMATCH":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "密码已修改，该刷新令牌已失效",
                    "error_code": "TOKEN_VERSION_MISMATCH",
                },
            )
        if msg == "TOKEN_REUSED":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "该刷新令牌已被使用过（禁止重用）",
                    "error_code": "TOKEN_REUSED",
                },
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=msg,
        )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的刷新令牌",
        )

    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post(
    "/password-reset-request",
    summary="请求密码重置",
    description="通过邮箱/用户名请求密码重置，不泄露账号是否存在。调试模式下会返回验证码。",
)
async def password_reset_request(
    body: _PasswordResetRequest,
    db: DB,
    _rl=Depends(rate_limit_sensitive("password_reset_request")),
):
    """请求密码重置（永远返回 200，避免枚举）"""
    result: dict[str, object] = {"message": "若该账号存在，重置链接已发送", "success": True}
    stmt = select(User).where(
        (User.email == body.email_or_username) | (User.username == body.email_or_username)
    )
    r = await db.execute(stmt)
    user: User | None = r.scalar_one_or_none()

    if user is None:
        return result

    code, token = await _gen_reset_code_and_token(user)

    has_smtp = bool(getattr(settings, "smtp_host", None))
    if not has_smtp:
        try:
            from sqlalchemy import text as _t

            content = f"密码重置验证码：{code}，重置令牌：{token}（15 分钟内有效）"
            try:
                await db.execute(
                    _t(
                        "INSERT INTO notifications (user_id, type, content, is_read, created_at) "
                        "VALUES (:uid, :typ, :c, :r, :now)"
                    ),
                    {
                        "uid": user.id,
                        "typ": "password_reset",
                        "c": content,
                        "r": False,
                        "now": datetime.now(UTC),
                    },
                )
                await db.commit()
            except Exception:
                await db.rollback()
        except Exception:
            pass

    if settings.debug:
        result["debug"] = {
            "reset_code": code,
            "reset_token": token,
        }

    return result


@router.post(
    "/password-reset",
    response_model=BaseResponse,
    summary="重置密码（验证码 + 新密码）",
    description="使用请求阶段下发的验证码和令牌重置密码。",
)
async def password_reset(
    body: _PasswordResetBody,
    db: DB,
    _rl=Depends(rate_limit_sensitive("password_reset")),
):
    """重置密码"""
    stmt = select(User).where(
        (User.email == body.token_or_email) | (User.username == body.token_or_email)
    )
    r = await db.execute(stmt)
    user: User | None = r.scalar_one_or_none()

    if user is None:
        # 也可能 body.token_or_email 直接就是 reset_token，查 meta 反查
        # 简化：如果找不到 user 也不暴露，直接 422 验证码无效
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "验证码或令牌无效",
                "error_code": "RESET_CODE_INVALID",
            },
        )

    key_code = f"{PREFIX}:code:{user.id}"
    key_token = f"{PREFIX}:token:{user.id}"

    try:
        cached_code = await cache.get(key_code)
        cached_token = await cache.get(key_token)
    except Exception:
        cached_code = None
        cached_token = None

    code_matches = cached_code is not None and str(cached_code) == body.code
    token_matches = cached_token is not None and str(cached_token) == body.token_or_email

    if not code_matches and not (cached_token is not None and token_matches):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "验证码或令牌无效或已过期",
                "error_code": "RESET_CODE_INVALID",
            },
        )

    # 密码强度检查
    errors = validate_password(body.new_password)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "新密码不符合强度要求",
                "errors": errors,
                "error_code": "WEAK_PASSWORD",
            },
        )

    # 设置新密码 + 踢所有会话下线
    user.password_hash = get_password_hash(body.new_password)
    user.token_version = (getattr(user, "token_version", 0) or 0) + 1

    # 清理验证码
    try:
        await cache.delete(key_code)
        await cache.delete(key_token)
    except Exception:
        pass

    # 撤销所有 refresh token（service 层）
    service = await get_user_service(db)
    await service._token_repo.revoke_all_user_tokens(user.id)
    await db.commit()

    return BaseResponse(message="密码重置成功")


@router.post(
    "/logout",
    response_model=BaseResponse,
    summary="用户登出",
    description="撤销当前用户的刷新令牌。",
)
async def logout(
    current_user: CurrentUser,
    db: DB,
    refresh_token: str | None = Query(None, description="要撤销的刷新令牌"),
):
    """用户登出，撤销刷新令牌"""
    service = await get_user_service(db)
    await service.logout(current_user.id, refresh_token)
    return BaseResponse(message="登出成功")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户",
    description="获取当前登录用户的详细信息。",
)
async def get_me(current_user: CurrentUser):
    """获取当前用户信息"""
    return build_user_response(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="更新个人信息",
    description="更新当前用户的个人资料。",
)
async def update_me(user_data: UserUpdate, current_user: CurrentUser, db: DB):
    """更新个人信息"""
    service = await get_user_service(db)
    update_dict = user_data.model_dump(exclude_unset=True)
    updated_user = await service.update_profile(current_user.id, update_dict)
    return build_user_response(updated_user)


@router.post(
    "/me/password",
    response_model=BaseResponse,
    summary="修改密码",
    description="已登录用户修改密码，需提供旧密码。成功后踢所有会话下线。",
)
async def change_password_v2(
    body: _PasswordChangeBody,
    current_user: CurrentUser,
    db: DB,
    _rl=Depends(rate_limit_write("change_password")),
):
    """修改密码"""
    errors = validate_password(body.new_password)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "新密码不符合强度要求",
                "errors": errors,
                "error_code": "WEAK_PASSWORD",
            },
        )

    service = await get_user_service(db)
    try:
        await service.change_password(
            user_id=current_user.id,
            old_password=body.old_password,
            new_password=body.new_password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    return BaseResponse(message="密码修改成功，所有设备已下线")


@router.post(
    "/me/change-password",
    response_model=BaseResponse,
    summary="修改密码（旧路径）",
    description="兼容旧路径：修改当前用户的密码，需要验证当前密码。",
)
async def change_password_legacy(
    data: PasswordChange,
    current_user: CurrentUser,
    db: DB,
    _rl=Depends(rate_limit_write("change_password_legacy")),
):
    """修改密码（兼容旧路径 /me/change-password）"""
    errors = validate_password(data.new_password)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "新密码不符合强度要求",
                "errors": errors,
                "error_code": "WEAK_PASSWORD",
            },
        )

    service = await get_user_service(db)
    try:
        await service.change_password(
            user_id=current_user.id,
            old_password=data.current_password,
            new_password=data.new_password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return BaseResponse(message="密码修改成功")


@router.get(
    "/me/preferences",
    response_model=UserPreferenceResponse,
    summary="获取个人偏好",
    description="获取当前用户的偏好设置。",
)
async def get_my_preferences(current_user: CurrentUser, db: DB):
    """获取用户偏好设置"""
    service = await get_user_service(db)
    profile = await service.get_user_profile(current_user.id, current_user.id)
    if profile and profile.get("preferences"):
        return UserPreferenceResponse.model_validate(profile["preferences"])

    preference = UserPreference(user_id=current_user.id)
    db.add(preference)
    await db.flush()
    return UserPreferenceResponse.model_validate(preference)


@router.put(
    "/me/preferences",
    response_model=UserPreferenceResponse,
    summary="更新个人偏好",
    description="更新当前用户的偏好设置。",
)
async def update_my_preferences(
    data: UserPreferenceUpdate,
    current_user: CurrentUser,
    db: DB,
):
    """更新用户偏好设置"""
    service = await get_user_service(db)
    update_dict = data.model_dump(exclude_unset=True)
    preference = await service.update_preferences(current_user.id, update_dict)
    return UserPreferenceResponse.model_validate(preference)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="获取用户信息",
    description="根据 ID 获取用户公开信息。",
)
async def get_user(user_id: int, db: DB, current_user: CurrentUserOptional = None):
    """获取指定用户信息"""
    service = await get_user_service(db)
    current_user_id = current_user.id if current_user else None
    profile = await service.get_user_profile(user_id, current_user_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if not profile.get("is_public") and not current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户资料不公开",
        )

    return build_user_response(profile["user"])


@router.get(
    "/username/{username}",
    response_model=UserResponse,
    summary="通过用户名获取用户",
    description="根据用户名获取用户公开信息。",
)
async def get_user_by_username(username: str, db: DB, current_user: CurrentUserOptional = None):
    """通过用户名获取用户信息"""
    service = await get_user_service(db)
    user = await service.get_user_by_username(username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    current_user_id = current_user.id if current_user else None
    profile = await service.get_user_profile(user.id, current_user_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if not profile.get("is_public") and not current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户资料不公开",
        )

    response = build_user_response(user)
    preference = profile.get("preferences")

    if (
        preference
        and not preference.show_email
        and not profile.get("is_self")
        and not (current_user and current_user.is_staff)
    ):
        response.email = "***"

    return response


@router.get(
    "/username/{username}/preferences",
    summary="获取用户隐私设置",
    description="获取用户的隐私设置（公开部分）。",
)
async def get_user_preferences_by_username(username: str, db: DB):
    """获取用户的隐私设置"""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    result = await db.execute(select(UserPreference).where(UserPreference.user_id == user.id))
    preference = result.scalar_one_or_none()

    if not preference:
        # 返回默认设置
        return {
            "public_profile": True,
            "show_email": False,
            "show_posts": True,
            "show_comments": True,
            "show_stats": True,
        }

    return {
        "public_profile": preference.public_profile,
        "show_email": preference.show_email,
        "show_posts": preference.show_posts,
        "show_comments": preference.show_comments,
        "show_stats": preference.show_stats,
    }


@router.get(
    "/",
    response_model=PaginatedResponse,
    summary="用户列表",
    description="获取用户列表，支持搜索和分页。",
)
async def list_users(
    db: DB,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: str | None = Query(None, description="搜索关键词"),
):
    """
    获取用户列表

    性能优化：
    - 使用并发查询获取总数和列表
    - 使用 selectinload 预加载关联数据
    """
    query = select(User).options(selectinload(User.title))

    if search:
        query = query.where(
            User.username.ilike(f"%{search}%")
            | User.nickname.ilike(f"%{search}%")
            | User.email.ilike(f"%{search}%")
        )

    # 并发执行计数和列表查询
    count_query = select(func.count()).select_from(query.subquery())

    total, result = await concurrent_query(
        db.scalar(count_query),
        db.execute(
            query.offset((page - 1) * page_size).limit(page_size).order_by(User.created_at.desc())
        ),
    )

    users = result.scalars().all()
    total = total or 0

    return PaginatedResponse(
        items=[build_user_response(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.post(
    "/me/change-password",
    response_model=BaseResponse,
    summary="修改密码",
    description="修改当前用户的密码，需要验证当前密码。",
)
async def change_password(
    data: PasswordChange,
    current_user: CurrentUser,
    db: DB,
):
    """修改密码"""
    service = await get_user_service(db)
    try:
        await service.change_password(
            user_id=current_user.id,
            old_password=data.current_password,
            new_password=data.new_password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return BaseResponse(message="密码修改成功")


@router.delete(
    "/me",
    response_model=BaseResponse,
    summary="注销账户",
    description="注销当前用户账户（软删除），需要验证密码。",
)
async def delete_account(
    current_user: CurrentUser,
    db: DB,
    password: str = Query(..., description="当前密码验证"),
):
    """注销账户"""
    if current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="超级管理员不能注销自己的账户",
        )

    # 直接验证密码（不用 change_password(new=old) hack，因为它现在会拒绝同密码）
    if not verify_password(password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码错误",
        )

    service = await get_user_service(db)
    await service.deactivate_user(current_user.id)
    return BaseResponse(message="账户已注销")


@router.put(
    "/me/avatar",
    response_model=UserResponse,
    summary="更新头像",
    description="更新当前用户的头像。",
)
async def update_avatar(
    avatar: str = Query(..., description="头像 URL"),
    current_user: CurrentUser = None,
    db: DB = None,
):
    """更新用户头像"""
    service = await get_user_service(db)
    updated_user = await service.update_profile(current_user.id, {"avatar": avatar})
    return build_user_response(updated_user)


@router.put(
    "/me/cover",
    response_model=UserResponse,
    summary="更新封面图",
    description="更新当前用户的封面图。",
)
async def update_cover(
    cover_image: str = Query(..., description="封面图 URL"),
    current_user: CurrentUser = None,
    db: DB = None,
):
    """更新用户封面图"""
    service = await get_user_service(db)
    updated_user = await service.update_profile(current_user.id, {"cover_image": cover_image})
    return build_user_response(updated_user)


# ==================== 用户主页 API ====================


@router.get(
    "/{user_id}/posts",
    response_model=PaginatedResponse,
    summary="用户文章列表",
    description="获取指定用户发布的文章列表。",
)
async def get_user_posts(
    user_id: int,
    db: DB,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=50, description="每页数量"),
    current_user: CurrentUserOptional = None,
):
    """
    获取用户发布的文章

    性能优化：
    - 使用并发查询获取总数和列表
    - 预加载分类和标签
    """

    # 检查用户是否存在
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    # 检查隐私设置
    result = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    preference = result.scalar_one_or_none()

    is_self = current_user and current_user.id == user_id
    is_staff = current_user and current_user.is_staff

    if preference and not preference.show_posts and not is_self and not is_staff:
        return PaginatedResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)

    query = (
        select(Post)
        .where(Post.author_id == user_id, Post.status == "published")
        .options(selectinload(Post.category), selectinload(Post.tags))
        .order_by(Post.published_at.desc())
    )

    # 并发执行计数和列表查询
    count_query = select(func.count()).select_from(
        select(Post).where(Post.author_id == user_id, Post.status == "published").subquery()
    )

    total, result = await concurrent_query(
        db.scalar(count_query),
        db.execute(query.offset((page - 1) * page_size).limit(page_size)),
    )

    posts = result.scalars().all()
    total = total or 0

    # 转换为响应格式
    items = []
    for post in posts:
        items.append(
            {
                "id": post.id,
                "title": post.title,
                "slug": post.slug,
                "excerpt": post.excerpt,
                "cover_image": post.cover_image,
                "views": post.views,
                "category": {
                    "id": post.category.id,
                    "name": post.category.name,
                    "color": post.category.color,
                }
                if post.category
                else None,
                "tags": [{"id": t.id, "name": t.name, "color": t.color} for t in post.tags],
                "published_at": post.published_at.isoformat() if post.published_at else None,
                "created_at": post.created_at.isoformat() if post.created_at else None,
            }
        )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get(
    "/{user_id}/comments",
    response_model=PaginatedResponse,
    summary="用户评论列表",
    description="获取指定用户发表的评论列表。",
)
async def get_user_comments(
    user_id: int,
    db: DB,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=50, description="每页数量"),
    current_user: CurrentUserOptional = None,
):
    """
    获取用户发表的评论

    性能优化：
    - 使用并发查询获取总数和列表
    - 预加载文章信息
    """

    # 检查用户是否存在
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    # 检查隐私设置
    result = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    preference = result.scalar_one_or_none()

    is_self = current_user and current_user.id == user_id
    is_staff = current_user and current_user.is_staff

    if preference and not preference.show_comments and not is_self and not is_staff:
        return PaginatedResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)

    query = (
        select(Comment)
        .where(Comment.user_id == user_id, Comment.active.is_(True))
        .options(selectinload(Comment.post))
        .order_by(Comment.created_at.desc())
    )

    # 并发执行计数和列表查询
    count_query = select(func.count()).select_from(
        select(Comment).where(Comment.user_id == user_id, Comment.active.is_(True)).subquery()
    )

    total, result = await concurrent_query(
        db.scalar(count_query),
        db.execute(query.offset((page - 1) * page_size).limit(page_size)),
    )

    comments = result.scalars().all()
    total = total or 0

    # 转换为响应格式
    items = []
    for comment in comments:
        items.append(
            {
                "id": comment.id,
                "content": comment.content[:200] + "..."
                if len(comment.content) > 200
                else comment.content,
                "post": {
                    "id": comment.post.id,
                    "title": comment.post.title,
                    "slug": comment.post.slug,
                }
                if comment.post
                else None,
                "created_at": comment.created_at.isoformat() if comment.created_at else None,
            }
        )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get(
    "/{user_id}/stats",
    summary="用户统计信息",
    description="获取指定用户的统计数据。",
)
async def get_user_stats(
    user_id: int,
    db: DB,
):
    """
    获取用户统计信息

    性能优化：
    - 使用并发查询同时获取多个统计值
    """

    # 检查用户是否存在
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    # 并发执行所有统计查询
    posts_count, comments_count, total_views, total_likes = await concurrent_query(
        # 文章数
        db.scalar(
            select(func.count())
            .select_from(Post)
            .where(Post.author_id == user_id, Post.status == "published")
        ),
        # 评论数
        db.scalar(
            select(func.count())
            .select_from(Comment)
            .where(Comment.user_id == user_id, Comment.active.is_(True))
        ),
        # 总浏览量
        db.scalar(
            select(func.sum(Post.views))
            .select_from(Post)
            .where(Post.author_id == user_id, Post.status == "published")
        ),
        # 总点赞数
        db.scalar(
            select(func.count())
            .select_from(post_likes.join(Post, post_likes.c.post_id == Post.id))
            .where(Post.author_id == user_id)
        ),
    )

    return {
        "user_id": user_id,
        "posts_count": posts_count or 0,
        "comments_count": comments_count or 0,
        "total_views": total_views or 0,
        "total_likes": total_likes or 0,
        "joined_at": user.created_at.isoformat() if user.created_at else None,
    }
