"""
用户管理 API

提供用户注册、登录、信息管理等功能。

性能优化：
- 使用服务层封装业务逻辑
- 使用仓储层进行数据访问
- 使用缓存减少数据库查询
- 多条独立查询用 concurrent_query 顺序批处理（AsyncSession 非并发安全，无并行收益）
"""

import logging
import math
import secrets
import string
from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import defer, selectinload

logger = logging.getLogger(__name__)

from backend.api._user_response_helper import apply_email_privacy, build_user_response
from backend.core.auth import (
    DB,
    CurrentStaff,
    CurrentUser,
    CurrentUserOptional,
    aget_password_hash,
    averify_password,
)
from backend.core.cache import cache
from backend.core.concurrency import concurrent_query
from backend.core.config import settings
from backend.core.exceptions import AppException
from backend.core.password_policy import validate_password
from backend.core.plugin_bus import bus
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
    UserListItem,
    UserPreferenceResponse,
    UserPreferenceUpdate,
    UserResponse,
    UserUpdate,
)
from backend.services.content_renderer import render_excerpt
from backend.services.email_service import get_email_service
from backend.services.user_service import get_user_service
from backend.utils.compat import UTC

router = APIRouter(tags=["用户"])

PREFIX = "password_reset"
RESET_CODE_TTL = 15 * 60  # 验证码有效期；尝试计数与它同 TTL，验证码过期即一并清零
RESET_CODE_MAX_ATTEMPTS = 5  # 6 位码 → 5 次尝试的枚举收益已低于噪声阈值


class _PasswordResetRequest(BaseModel):
    email_or_username: str = Field(..., min_length=1, max_length=255, description="邮箱或用户名")


class _PasswordResetBody(BaseModel):
    token_or_email: str = Field(..., min_length=1, max_length=255, description="邮箱或用户名")
    code: str = Field(..., min_length=6, max_length=6, description="6 位数字验证码")
    new_password: str = Field(..., min_length=1, max_length=255, description="新密码")


class _PasswordChangeBody(BaseModel):
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., description="新密码")


class _DeleteAccountBody(BaseModel):
    """注销账户请求体：密码走 body 而非 Query，避免明文密码进入访问日志 / Referer / 浏览器历史"""

    password: str = Field(..., min_length=1, max_length=255, description="当前密码验证")


# ═══════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════════


class PasswordResetDebugDoc(BaseModel):
    """密码重置请求响应里的调试载荷（仅非生产环境出现）。"""

    reset_code: str = Field(
        ...,
        description="本次生成的 6 位数字验证码（可能以 0 开头，故是字符串）。"
        "仅当 DEBUG=true 且 environment != production 时才会随响应下发",
    )


class PasswordResetRequestResponseDoc(BaseModel):
    """``POST /api/users/password-reset-request`` 的响应体（裸 dict，无 data 信封）。"""

    message: str = Field(
        ...,
        description="恒定文案（无论账号是否存在、邮件是否投递成功都是同一句），避免枚举账号",
    )
    success: bool = Field(True, description="固定为 true：本端点成功路径永远 200，不区分投递结果")
    debug: PasswordResetDebugDoc | None = Field(
        None,
        description="调试回显：只有非生产环境且 DEBUG=true 时存在（生产环境绝不回传验证码），"
        "该分支下也不会走「投递失败作废」逻辑",
    )


class UserPreferencesPublicDoc(BaseModel):
    """``GET /api/users/username/{username}/preferences`` 的响应体（裸 dict，5 个隐私开关）。

    无偏好行时返回下述模型默认值（public_profile=True、show_email=False、其余 True），
    口径与 UserPreference 的建表默认一致。
    """

    public_profile: bool = Field(True, description="是否公开个人资料页")
    show_email: bool = Field(False, description="是否对外展示邮箱（默认拒绝）")
    show_posts: bool = Field(True, description="是否公开文章列表")
    show_comments: bool = Field(True, description="是否公开评论列表")
    show_stats: bool = Field(True, description="是否公开统计数据")


class UserStatsDoc(BaseModel):
    """``GET /api/users/{user_id}/stats`` 的响应体（裸 dict，无信封）。"""

    user_id: int = Field(..., description="用户 ID（路径参数回显）")
    posts_count: int = Field(..., description="已发布文章数（status=published，无数据为 0）")
    comments_count: int = Field(..., description="已过审评论数（active=True，无数据为 0）")
    total_views: int = Field(
        ...,
        description="本人已发布文章的 views 列求和（SUM 无行为 null，兜底成 0）",
    )
    total_likes: int = Field(..., description="本人全部文章（含草稿）收到的点赞总数，无数据为 0")
    joined_at: str | None = Field(
        None, description="注册时间：handler 手工 isoformat() 的字符串，无创建时间时为 null"
    )


async def _gen_reset_code(user: User) -> str:
    """生成 6 位验证码并写入缓存 15 分钟

    只存验证码：`/password-reset` 的唯一凭据就是这 6 位码（配合尝试次数限流与
    token_version 递增踢会话）。历史上的 reset_token / meta 两个键从不出现在校验
    路径上，属于纯暴露的幽灵密钥，已移除。
    """
    code = "".join(secrets.choice(string.digits) for _ in range(6))
    await cache.set(f"{PREFIX}:code:{user.id}", code, ttl=RESET_CODE_TTL)
    return code


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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            message=msg,
            error_code=code,
        )
    except IntegrityError as e:
        # 并发同名注册的"先查后插"窗口：唯一约束兜底，转 409 而非 500
        await db.rollback()
        detail = str(e.orig).lower()
        code = "EMAIL_TAKEN" if "email" in detail else "USERNAME_EXISTS"
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            message="用户名或邮箱已被使用",
            error_code=code,
        )

    # 事件 payload 不带邮箱等 PII（字段白名单见 api/webhook.py）：
    # user.registered 可被管理员转发到第三方 URL。
    await bus.do_action("user.registered", result["user"])

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
    description=(
        "通过邮箱/用户名请求密码重置，不泄露账号是否存在（恒定 message + success=true，永远 200）。"
        "公开接口、按 IP 限流。验证码 15 分钟有效；SMTP 未配置或投递失败时验证码会被作废"
        "（不留发不出去却能通过校验的孤儿凭证），响应形态不变。"
        "仅非生产 + DEBUG 环境额外返回 debug.reset_code 供本地调试。"
    ),
    responses={200: {"model": PasswordResetRequestResponseDoc}},
)
async def password_reset_request(
    body: _PasswordResetRequest,
    db: DB,
    _rl=Depends(rate_limit_sensitive("password_reset_request")),
):
    """请求密码重置（永远返回 200，避免枚举）"""
    # 恒定文案：账号不存在 / 邮件发送失败都返回同一句，既不泄露账号存在性，也不谎报"已送达"
    result: dict[str, object] = {
        "message": "若该账号存在，重置验证码已发送至其绑定邮箱；如未收到，请联系站点管理员",
        "success": True,
    }
    stmt = select(User).where(
        (User.email == body.email_or_username) | (User.username == body.email_or_username)
    )
    r = await db.execute(stmt)
    user: User | None = r.scalar_one_or_none()

    if user is None:
        return result

    code = await _gen_reset_code(user)

    # is_configured 同时要求 host/user/password 齐备；
    # 单看 smtp_host 会被 config.py 的默认值 "smtp.qq.com" 恒真欺骗。
    email_service = get_email_service()
    email_sent = False
    if user.email and email_service.is_configured:
        try:
            # 同步等待（background=False）：只有拿到确定结果才能判定投递成败
            mail_result = await email_service.send_email(
                to=user.email,
                subject=f"[{settings.site_name}] 密码重置验证码",
                body=f"您的密码重置验证码：{code}（15 分钟内有效）。如非本人操作，请忽略本邮件。",
                background=False,
            )
            email_sent = bool(mail_result.success)
            if not email_sent:
                logger.error(
                    "密码重置验证码邮件投递失败 user_id=%s error=%s",
                    user.id,
                    mail_result.error,
                )
        except Exception:
            logger.exception("密码重置验证码邮件发送异常 user_id=%s", user.id)
    else:
        logger.error(
            "密码重置请求无法投递：SMTP 未配置或用户无邮箱 user_id=%s has_email=%s smtp=%s",
            user.id,
            bool(user.email),
            email_service.is_configured,
        )

    # 仅本地开发便利：生产环境即使 debug=True 也不回传重置凭证，
    # 否则任何人请求管理员邮箱的重置即可在响应中拿到 reset_code 完成接管。
    # 判据必须前置于"投递失败即作废"——开发环境一般没配 SMTP，否则本地永远拿不到码。
    dev_echo = settings.debug and settings.environment != "production"
    if dev_echo:
        result["debug"] = {"reset_code": code}
        return result

    if not email_sent:
        # 投递失败即作废验证码：不留一把发不出去却仍能通过校验的孤儿凭证
        try:
            await cache.delete(f"{PREFIX}:code:{user.id}")
        except Exception:
            logger.warning("密码重置验证码清理失败 user_id=%s", user.id, exc_info=True)

    return result


@router.post(
    "/password-reset",
    response_model=BaseResponse,
    summary="重置密码（验证码 + 新密码）",
    description="使用请求阶段投递到邮箱的验证码重置密码。",
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
        # 不区分"账号不存在"与"验证码错误"，避免枚举
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "验证码无效",
                "error_code": "RESET_CODE_INVALID",
            },
        )

    key_code = f"{PREFIX}:code:{user.id}"
    key_attempts = f"{PREFIX}:attempts:{user.id}"

    try:
        cached_code = await cache.get(key_code)
        attempts = await cache.get(key_attempts)
    except Exception as exc:  # noqa: BLE001 —— 缓存故障按"无验证码"处理（fail-closed）
        # 拒绝而不是放行是安全的；但必须留痕：否则 Redis 挂掉时用户看到的是
        # 永远"验证码无效"，排查方向会被完全带偏到邮件/发码环节。
        logger.warning(f"[password-reset] 验证码缓存读取失败，按无效处理: {exc!r}")
        cached_code = None
        attempts = None

    # 限制同一验证码的尝试次数（防 6 位码暴力枚举；IP 限流可被伪造头绕过，不能只靠它）
    try:
        attempt_count = int(attempts) if attempts is not None else 0
    except (TypeError, ValueError):
        attempt_count = 0

    # 计数达到上限就作废验证码。作废失败只记日志：`raise` 不能被它连带吞掉，
    # 否则锁定制服静默失效，暴力枚举窗口重新打开。
    if attempt_count >= RESET_CODE_MAX_ATTEMPTS:
        try:
            await cache.delete(key_code)
        except Exception:
            logger.warning("密码重置验证码作废失败 user_id=%s", user.id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "尝试次数过多，验证码已作废，请重新申请",
                "error_code": "RESET_CODE_INVALID",
            },
        )

    code_matches = cached_code is not None and secrets.compare_digest(
        str(cached_code), str(body.code)
    )

    if not code_matches:
        try:
            await cache.set(key_attempts, attempt_count + 1, ttl=RESET_CODE_TTL)
        except Exception:
            logger.warning(
                "密码重置尝试计数写入失败，暴力枚举防护可能失效 user_id=%s", user.id, exc_info=True
            )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "验证码或令牌无效或已过期",
                "error_code": "RESET_CODE_INVALID",
            },
        )

    # 密码强度检查
    errors = validate_password(body.new_password)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "新密码不符合强度要求",
                "errors": errors,
                "error_code": "WEAK_PASSWORD",
            },
        )

    # 设置新密码 + 踢所有会话下线
    user.password_hash = await aget_password_hash(body.new_password)
    user.token_version = (getattr(user, "token_version", 0) or 0) + 1

    # 清理验证码与尝试计数（成功后计数没意义，留着会让下一次申请带上历史）
    try:
        await cache.delete(key_code)
        await cache.delete(key_attempts)
    except Exception:
        logger.warning("密码重置凭证清理失败 user_id=%s", user.id, exc_info=True)

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
    description=(
        "更新当前用户的个人资料。若改动了文章作者卡片会展示的字段"
        "（昵称/头像/封面/简介/网站/GitHub/用户名），"
        "会自动失效该作者全部文章的详情缓存与列表/RSS 缓存。"
    ),
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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
        # 这里**不能**用 401：请求本身是带着有效 access token 进来的，401 的含义是
        # 「身份凭证失效」，而 apiFetch 见到 401 会走 refreshAccessToken 重试链，重试仍 401
        # 就 clearTokens + 跳 /login —— 用户只是把旧密码打错一个字符就被整站登出。
        # 口径与本文件另外两处「当前密码错误」一致（change_password_legacy、delete_account 都用 400）。
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
    await db.refresh(preference)
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


def _profile_is_hidden(
    preference: UserPreference | None,
    user_id: int,
    current_user: User | None,
) -> bool:
    """这个用户的资料对外是否应当表现为「不存在」。

    `public_profile=False` 与"查无此人"共用 404 口径（见 `GET /users/{user_id}`）：
    403/401 等于承认账号真实存在，是账号枚举面；而资料页的**子资源**（文章列表、
    评论列表、统计、隐私开关组）只要还能匿名读出内容，主页级的 404 就只是把门帘
    放下、门没关——尤其 `GET /users/username/{u}/preferences` 直接把整组开关回给
    匿名调用方，等于把"这个人存在，只是藏起来了"念出来。

    本人和管理员越过该闸门；**无偏好行按可见处理**（与 UserPreference 建表默认一致）。
    """
    if preference is None or preference.public_profile is not False:
        return False
    if current_user is not None and (current_user.id == user_id or current_user.is_staff):
        return False
    return True


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="获取用户信息",
    description=(
        "根据 ID 获取用户公开信息。用户关闭「公开资料」（`public_profile=False`）时"
        "对外统一返回 404（与「查无此人」同口径，避免账号枚举），仅本人可读。"
    ),
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

    # 资料不公开一律按"不存在"回 404，且闸门只看 is_public（不区分匿名/登录访客）：
    # 1) 403 等于承认该账号真实存在（枚举面）；前台作者主页的 404 闸门只认 404/空对象，
    #    403 会渲染兜底 UI 却返回 HTTP 200，再被该路由的 swr 缓存成一个可索引的错误页。
    # 2) 服务层对"非本人 + 关了公开"返回的是精简 dict（不含 email），
    #    放行任何一类访客都会让它走到 build_user_response → UserResponse 必填 email 缺失 → 500。
    if not profile.get("is_public"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    response = build_user_response(profile["user"])
    apply_email_privacy(response, profile, current_user)
    return response


@router.get(
    "/username/{username}",
    response_model=UserResponse,
    summary="通过用户名获取用户",
    description=(
        "根据用户名获取用户公开信息。这是前台作者主页 `/authors/<username>` 的资料来源，"
        "关闭「公开资料」的作者在此对外返回 404（口径同 `GET /users/{user_id}`）。"
    ),
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

    # 口径同 ``GET /users/{user_id}``：不公开一律 404（防枚举 + 防 swr 缓存可索引错误页 +
    # 服务层的精简 dict 缺 email，放行任何访客都会变成 500）。
    if not profile.get("is_public"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    response = build_user_response(user)
    apply_email_privacy(response, profile, current_user)
    return response


@router.get(
    "/username/{username}/preferences",
    summary="获取用户隐私设置",
    description=(
        "获取用户的隐私设置（公开部分）。公开接口、无需鉴权。"
        "响应为裸 dict（5 个布尔开关，无 data 信封）；用户从未动过设置（无偏好行）时"
        "返回与建表默认一致的默认开关组（show_email 默认拒绝）。用户不存在返回 404。"
        "**资料已关闭公开（`public_profile=False`）时同样返回 404**——把整组开关摊给"
        "匿名调用方等于宣布「这个账号存在，只是藏起来了」，会打穿资料接口刻意选定的"
        "统一 404 防枚举口径。仅本人可读到自己的真实开关组。"
    ),
    responses={200: {"model": UserPreferencesPublicDoc}},
)
async def get_user_preferences_by_username(
    username: str, db: DB, current_user: CurrentUserOptional = None
):
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

    # 关了公开资料的人，其开关组本身也是"这个主页不存在"的一部分（见 _profile_is_hidden）。
    if _profile_is_hidden(preference, user.id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

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
    summary="用户列表（精简投影）",
    description=(
        "获取用户列表，支持搜索和分页（需 staff）。"
        "响应为裸分页 dict（items/total/page/page_size/total_pages，无 success/data 信封）；"
        "items 内每项是 **UserListItem** 精简投影：只有 id/username/nickname/avatar/"
        "resolved_avatar_url/role/title/is_active/created_at。"
        "**不含 email / bio / qq / github / website** —— 列表页不展示这些字段，"
        "按 page_size=100 一页要多搬 100 份，且会把联系方式摊给所有能过鉴权的人。"
        "需要完整字段走 `GET /users/{id}`；需要封禁态与内容计数走 `GET /admin/users`。"
    ),
)
async def list_users(
    db: DB,
    _viewer: CurrentStaff,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: str | None = Query(None, max_length=100, description="搜索关键词"),
    sort: str = Query("created_at", description="排序字段：created_at|last_login|username"),
    order: str = Query("desc", description="排序方向：asc|desc"),
):
    """
    获取用户列表（精简投影）

    - `defer(User.password_hash)`：列表响应不含哈希，但 `select(User)` 默认取整行，
      每页 100 个用户就多拉 100 条 argon2 哈希（每条几十字节，且是敏感数据）。
    - `selectinload(User.title)`：头衔一次 IN 查完，避免逐行懒加载。
      注意 `concurrent_query` 是**顺序**执行（AsyncSession 非并发安全），别期待并行收益。
    - 投影在**这一层**收窄（而不是靠 response_model 事后裁剪）：`UserListItem` 只声明
      9 个字段，`defer` 掉的长文本列（bio 等）连读取都省了。
    """
    query = select(User).options(
        selectinload(User.title),
        defer(User.password_hash),
        # 只 defer **确定用不到**的宽列：bio 最长 500 字符，一页 100 条就是 50KB 纯浪费。
        # 注意 qq / github / email / avatar_source **绝对不能 defer** ——
        # resolved_for_user() 要靠它们算 resolved_avatar_url，defer 之后一旦被访问
        # 就是异步会话上的懒加载 → MissingGreenlet（这个坑踩过一次）。
        defer(User.bio),
        defer(User.website),
        defer(User.cover_image),
    )

    if search:
        query = query.where(
            User.username.ilike(f"%{search}%")
            | User.nickname.ilike(f"%{search}%")
            | User.email.ilike(f"%{search}%")
        )

    # 排序
    sort_col = {
        "created_at": User.created_at,
        "last_login": User.last_login,
        "username": User.username,
    }.get(sort, User.created_at)
    query = query.order_by(sort_col.desc() if order == "desc" else sort_col.asc())

    # 计数 + 列表（顺序两条查询）
    count_query = select(func.count()).select_from(query.subquery())

    total, result = await concurrent_query(
        db.scalar(count_query),
        db.execute(query.offset((page - 1) * page_size).limit(page_size)),
    )

    users = result.scalars().all()
    total = total or 0

    # resolved_avatar_url 不是 ORM 列，是头像代理链算出来的，必须手工回填
    # （build_user_response 干的就是这件事，但它产出的是宽 UserResponse）。
    from backend.services._avatar_helpers import resolved_for_user

    items: list[UserListItem] = []
    for u in users:
        item = UserListItem.model_validate(u)
        item.resolved_avatar_url = resolved_for_user(u)
        items.append(item)

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.delete(
    "/me",
    response_model=BaseResponse,
    summary="注销账户",
    description="注销当前用户账户（软删除），需要验证密码。",
)
async def delete_account(
    current_user: CurrentUser,
    db: DB,
    body: _DeleteAccountBody,
):
    """注销账户"""
    if current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="超级管理员不能注销自己的账户",
        )

    # 直接验证密码（不用 change_password(new=old) hack，因为它现在会拒绝同密码）
    if not await averify_password(body.password, current_user.password_hash):
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
    description="更新当前用户的头像；头像属于作者展示字段，会失效该作者全部文章的缓存。",
)
async def update_avatar(
    current_user: CurrentUser,
    db: DB,
    avatar: str = Query(..., description="头像 URL"),
):
    """更新用户头像"""
    service = await get_user_service(db)
    updated_user = await service.update_profile(current_user.id, {"avatar": avatar})
    return build_user_response(updated_user)


@router.put(
    "/me/cover",
    response_model=UserResponse,
    summary="更新封面图",
    description=("更新当前用户的封面图；封面图属于作者展示字段，会失效该作者全部文章的缓存。"),
)
async def update_cover(
    current_user: CurrentUser,
    db: DB,
    cover_image: str = Query(..., description="封面图 URL"),
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
    description=(
        "获取指定用户发布的文章列表。摘要与 `blog.py` 列表口径一致，"
        "经内容渲染管线处理（短代码 + the_excerpt filter 链），插件不会在此页失效。"
        "隐私：作者关闭「公开资料」（`public_profile=False`）时返回 404（主页不存在口径），"
        "只关闭 `show_posts` 时返回空页 200。"
    ),
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

    - 正文/加密正文/SEO meta 一律 `defer`：本接口的手写响应体不读这些列，
      不 defer 就等于把每篇文章的整篇 Markdown 从磁盘捞进内存再丢掉。
      （`blog.py` 的文章列表同样处理，两者口径一致。）
    - 分类、标签用 selectinload 批量预加载。
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

    # 资料页整体关闭时，它下面的集合也按"不存在"回 404（口径同 GET /users/{user_id}），
    # 而 show_posts=false 只是"这个列表是空的"——两个开关语义不同，不要合并。
    if _profile_is_hidden(preference, user_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if preference and not preference.show_posts and not is_self and not is_staff:
        return PaginatedResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)

    query = (
        select(Post)
        .where(Post.author_id == user_id, Post.status == "published")
        .options(
            selectinload(Post.category),
            selectinload(Post.tags),
            defer(Post.content),
            defer(Post.encrypted_content),
            defer(Post.meta_fields),
            defer(Post.meta_title),
            defer(Post.meta_description),
            defer(Post.meta_keywords),
        )
        .order_by(Post.published_at.desc())
    )

    # 计数 + 列表（顺序两条查询）
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
        # 摘要走统一渲染管线（短代码 + the_excerpt filter 链），保持多语言 dict 形状；
        # 直接吐 raw dict 会让声明 the_excerpt 的插件在作者主页静默失效。
        excerpt_value = post.excerpt
        if isinstance(excerpt_value, dict):
            excerpt_value = {
                lang: await render_excerpt(text, post=post, language=lang)
                for lang, text in excerpt_value.items()
            }
        elif excerpt_value is not None:
            excerpt_value = await render_excerpt(excerpt_value, post=post)
        items.append(
            {
                "id": post.id,
                "title": post.title,
                "slug": post.slug,
                "excerpt": excerpt_value,
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

    - 只用到评论正文的截断 + 文章的 id/title/slug，所以 `Comment.post` 预加载时
      必须 defer 掉正文与 meta 列，否则每页最多 50 条评论会连带读入 50 篇全文。
    - 计数与列表两条查询顺序执行（`concurrent_query` 不并行）。
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

    # 资料整体关闭 → 404（同 /{user_id}/posts）；show_comments=false → 空页。
    if _profile_is_hidden(preference, user_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if preference and not preference.show_comments and not is_self and not is_staff:
        return PaginatedResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)

    query = (
        select(Comment)
        .where(Comment.user_id == user_id, Comment.active.is_(True))
        .options(
            selectinload(Comment.post).options(
                defer(Post.content),
                defer(Post.encrypted_content),
                defer(Post.meta_fields),
            )
        )
        .order_by(Comment.created_at.desc())
    )

    # 计数 + 列表（顺序两条查询）
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
    description=(
        "获取指定用户的统计数据。公开接口、无需鉴权。响应为裸 dict"
        "（user_id/posts_count/comments_count/total_views/total_likes/joined_at，无信封）；"
        "计数在无数据时兜底为 0，joined_at 为 ISO 8601 字符串或 null。用户不存在返回 404。"
        "隐私口径：作者关闭「公开资料」（`public_profile=False`）时返回 404（同资料接口）；"
        "只关闭「显示统计」（`show_stats=False`）时返回 200 + 全零计数，与"
        "「还没有任何活动」不可区分正是隐藏语义，且此时不再执行任何聚合查询。"
    ),
    responses={200: {"model": UserStatsDoc}},
)
async def get_user_stats(
    user_id: int,
    db: DB,
    current_user: CurrentUserOptional = None,
):
    """
    获取用户统计信息

    - 四条聚合（文章数/评论数/浏览量/点赞数）顺序执行，命中隐藏开关时整段跳过。
    - 隐私两层：`public_profile=False` → 404（资料整体不存在口径）；
      `show_stats=False` → 200 全零（列表/计数类开关的"隐藏即空"口径）。本人可越过两层。
    """

    # 检查用户是否存在
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    preference = await db.scalar(select(UserPreference).where(UserPreference.user_id == user_id))
    if _profile_is_hidden(preference, user_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    is_self = bool(current_user and current_user.id == user_id)
    hide_stats = bool(preference and preference.show_stats is False) and not (
        is_self or (current_user and current_user.is_staff)
    )
    if hide_stats:
        return {
            "user_id": user_id,
            "posts_count": 0,
            "comments_count": 0,
            "total_views": 0,
            "total_likes": 0,
            "joined_at": user.created_at.isoformat() if user.created_at else None,
        }

    # 顺序执行多条统计查询
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
