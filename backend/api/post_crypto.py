"""
文章加密工具 API（Task 7 新增）

提供 derive_keys / verify_access / encrypted preview 三个端点，
用于前后端统一的加密文章密码派生、访问验证与后台预览。

路由：
- POST /api/post_crypto/derive_keys      匿名，派生 salt/verifier/algorithm
- POST /api/post_crypto/verify_access    匿名，校验访问密码返回短期 JWT
- GET  /api/post_crypto/encrypted/{post_id}/preview  author/admin 权限，返回摘要
"""

import hmac
import secrets
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Any

from fastapi import APIRouter, HTTPException, status
from jose import jwt
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.core.auth import DB, CurrentUserOptional
from backend.core.config import settings
from backend.models.blog import Post

router = APIRouter(tags=["文章加密工具"])


ALGO_DEFAULT = "AES-256-GCM"
POST_ACCESS_SCOPE = "post_access"
POST_ACCESS_TTL_SECONDS = 3600


# ==================== Schemas ====================


class DeriveKeysRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=128, description="用户输入的明文密码")


class DeriveKeysResponse(BaseModel):
    salt: str
    verifier: str
    algorithm: str = ALGO_DEFAULT


class VerifyAccessRequest(BaseModel):
    post_id: int = Field(..., ge=1, description="目标文章 ID")
    password: str = Field(..., min_length=1, max_length=128, description="访问密码（明文）")


class VerifyAccessResponse(BaseModel):
    ok: bool
    token: str | None = None
    message: str | None = None


class EncryptedPreviewResponse(BaseModel):
    id: int
    title: dict[str, Any] | str
    slug: str
    created_at: datetime
    scheduled_at: datetime | None = None
    encryption_enabled: bool
    encryption_hint: str | None = None


# ==================== Helpers ====================


def _compute_verifier(salt_hex: str, password: str) -> str:
    salt_bytes = bytes.fromhex(salt_hex)
    return hmac.new(salt_bytes, password.encode("utf-8"), sha256).hexdigest()


def _sign_post_access_token(post_id: int) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": f"post:{post_id}",
        "scope": POST_ACCESS_SCOPE,
        "post_id": post_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=POST_ACCESS_TTL_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


# ==================== Public endpoints ====================


@router.post(
    "/post_crypto/derive_keys",
    response_model=DeriveKeysResponse,
    summary="派生加密元数据",
    description="给定密码，生成随机 salt 与 verifier（HMAC-SHA256(salt, password)）。"
    "前端将这三个字段与 PostCreate 一起发送，后端不保存明文密码。",
)
async def derive_keys(data: DeriveKeysRequest) -> DeriveKeysResponse:
    salt_bytes = secrets.token_bytes(32)
    salt_hex = salt_bytes.hex()
    verifier = _compute_verifier(salt_hex, data.password)
    return DeriveKeysResponse(
        salt=salt_hex,
        verifier=verifier,
        algorithm=ALGO_DEFAULT,
    )


@router.post(
    "/post_crypto/verify_access",
    response_model=VerifyAccessResponse,
    summary="验证文章访问密码",
    description="给定文章 ID 与密码，重新计算 verifier 并与数据库比对。"
    "成功返回 ok=true 和 1h 短期 JWT（scope=post_access）。",
)
async def verify_access(data: VerifyAccessRequest, db: DB) -> VerifyAccessResponse:
    result = await db.execute(select(Post).where(Post.id == data.post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="文章不存在")

    if not post.encryption_enabled:
        return VerifyAccessResponse(ok=True, message="该文章未启用加密，无需验证")

    if not post.encryption_salt or not post.encryption_verifier:
        if post.password:
            from backend.core.auth import verify_password

            try:
                ok = verify_password(data.password, post.password)
            except Exception:
                ok = False
            if ok:
                token = _sign_post_access_token(post.id)
                return VerifyAccessResponse(ok=True, token=token)
        return VerifyAccessResponse(ok=False, message="文章加密数据不完整")

    expected = _compute_verifier(post.encryption_salt, data.password)
    if not hmac.compare_digest(expected, post.encryption_verifier):
        return VerifyAccessResponse(ok=False, message="密码错误")

    token = _sign_post_access_token(post.id)
    return VerifyAccessResponse(ok=True, token=token)


# ==================== Author/Admin preview ====================


@router.get(
    "/post_crypto/encrypted/{post_id}/preview",
    response_model=EncryptedPreviewResponse,
    summary="后台预览加密文章摘要",
    description="作者或管理员获取加密文章的基本信息（标题/创建时间/加密状态），"
    "用于编辑器预览加密效果。",
)
async def encrypted_preview(
    post_id: int,
    db: DB,
    current_user: CurrentUserOptional = None,
) -> EncryptedPreviewResponse:
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="文章不存在")

    is_owner = current_user and current_user.id == post.author_id
    is_staff = current_user and (current_user.is_staff or current_user.is_superuser)
    if not (is_owner or is_staff):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="仅作者或管理员可预览加密文章",
        )

    return EncryptedPreviewResponse(
        id=post.id,
        title=post.title,
        slug=post.slug,
        created_at=post.created_at,
        scheduled_at=post.scheduled_at,
        encryption_enabled=post.encryption_enabled,
        encryption_hint=post.encryption_hint,
    )
