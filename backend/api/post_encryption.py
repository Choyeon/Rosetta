"""
文章内容加密 API

提供对文章敏感内容的 AES-GCM 加密存储与解密读取能力。

路由设计：
- 公开接口:
    POST /api/posts/{post_id}/decrypt   校验密码后返回解密内容
- 管理接口:
    POST /api/admin/posts/{post_id}/encrypt   设置文章加密内容

加密说明：
- 密文存储于 Post.encrypted_content（JSON：{"data": "<base64>"}）
- Post.password 存储 bcrypt 哈希用于校验访问密码
- Post.encryption_enabled 标记是否启用加密
- Post.encryption_hint 提供给用户的密码提示
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.core.auth import DB, CurrentStaff, get_password_hash, verify_password
from backend.core.crypto import DecryptionError, decrypt_content, encrypt_content
from backend.models.blog import Post
from backend.schemas import BaseResponse

router = APIRouter(tags=["内容加密"])


class EncryptRequest(BaseModel):
    """设置加密内容请求"""

    password: str = Field(..., min_length=1, max_length=128, description="加密密码（明文）")
    content: str = Field(..., min_length=1, description="待加密的明文内容")
    hint: str | None = Field(None, max_length=200, description="密码提示文案")


class UpdateEncryptionRequest(BaseModel):
    """更新加密内容请求（换密码/更新内容）"""

    old_password: str | None = Field(None, description="旧密码（用于验证）；为空时跳过验证")
    new_password: str = Field(..., min_length=1, max_length=128, description="新密码（明文）")
    content: str | None = Field(None, description="新的明文内容；为空时使用旧内容解密后重新加密")
    hint: str | None = Field(None, max_length=200, description="密码提示文案")


class DecryptRequest(BaseModel):
    """解密内容请求"""

    password: str = Field(..., min_length=1, max_length=128, description="访问密码（明文）")


class DecryptResponse(BaseModel):
    """解密内容响应"""

    content: str
    hint: str | None = None


# ==================== 公开接口 ====================


@router.post(
    "/posts/{post_id}/decrypt",
    response_model=DecryptResponse,
    summary="解密文章内容",
    description="提交访问密码，校验通过后返回文章的解密内容。仅对已启用加密的文章有效。",
)
async def decrypt_post(
    post_id: int,
    data: DecryptRequest,
    db: DB,
):
    """校验密码并返回解密内容（公开接口）"""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    if not post.encryption_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该文章未启用内容加密",
        )

    if not post.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该文章未设置访问密码",
        )

    # 校验密码（bcrypt 比对）
    if not verify_password(data.password, post.password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="密码错误",
        )

    encrypted_data = post.encrypted_content or {}
    ciphertext = encrypted_data.get("data") if isinstance(encrypted_data, dict) else None

    if not ciphertext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="加密内容缺失",
        )

    try:
        plaintext = decrypt_content(ciphertext, data.password)
    except DecryptionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="密码错误或密文已损坏",
        )

    return DecryptResponse(content=plaintext, hint=post.encryption_hint)


# ==================== 管理接口 ====================


@router.post(
    "/admin/posts/{post_id}/encrypt",
    response_model=BaseResponse,
    summary="设置文章加密内容",
    description="管理员使用指定密码对内容进行 AES-GCM 加密并存储，同时标记文章为加密状态。",
)
async def encrypt_post(
    post_id: int,
    data: EncryptRequest,
    db: DB,
    current_user: CurrentStaff,
):
    """设置文章加密内容（管理接口）"""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    ciphertext = encrypt_content(data.content, data.password)

    post.encrypted_content = {"data": ciphertext}
    post.encryption_enabled = True
    post.encryption_hint = data.hint
    post.password = get_password_hash(data.password)

    await db.flush()

    return BaseResponse(message="加密内容已设置")


@router.put(
    "/admin/posts/{post_id}/encrypt",
    response_model=BaseResponse,
    summary="更新文章加密内容（换密码/内容）",
    description="使用旧密码验证后，重新加密内容或更换访问密码。若 old_password 为空则跳过验证（需管理员权限）。",
)
async def update_post_encryption(
    post_id: int,
    data: UpdateEncryptionRequest,
    db: DB,
    current_user: CurrentStaff,
):
    """更新文章加密内容（管理接口）"""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    if not post.encryption_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该文章未启用内容加密，请先使用 POST 创建加密",
        )

    # 获取旧明文内容
    plaintext = data.content
    if plaintext is None:
        # 使用旧内容解密后重新加密
        if not post.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该文章未设置访问密码",
            )
        # 验证旧密码（如果提供了）
        verify_pwd = data.old_password
        if verify_pwd is None:
            # 管理员强制重置：尝试用现有 password 字段无法解密，
            # 此时必须提供新的 content
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未提供 old_password 时必须同时提供新的 content",
            )
        if not verify_password(verify_pwd, post.password):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="旧密码错误",
            )
        encrypted_data = post.encrypted_content or {}
        ciphertext = encrypted_data.get("data") if isinstance(encrypted_data, dict) else None
        if not ciphertext:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="加密内容缺失",
            )
        try:
            plaintext = decrypt_content(ciphertext, verify_pwd)
        except DecryptionError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="旧密码错误或密文已损坏",
            )
    else:
        # 提供了新内容，但仍需验证旧密码（如果提供了）
        if data.old_password is not None and post.password:
            if not verify_password(data.old_password, post.password):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="旧密码错误",
                )

    # 重新加密
    new_ciphertext = encrypt_content(plaintext, data.new_password)
    post.encrypted_content = {"data": new_ciphertext}
    post.encryption_hint = data.hint
    post.password = get_password_hash(data.new_password)

    await db.flush()

    return BaseResponse(message="加密内容已更新")


@router.delete(
    "/admin/posts/{post_id}/encrypt",
    response_model=BaseResponse,
    summary="关闭文章内容加密",
    description="关闭加密并清除密文、密码哈希与提示。文章内容将恢复为公开可读（仍受 Post.content 字段控制）。",
)
async def disable_post_encryption(
    post_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """关闭文章内容加密（管理接口）"""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    if not post.encryption_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该文章未启用内容加密",
        )

    post.encrypted_content = None
    post.encryption_enabled = False
    post.encryption_hint = None
    post.password = None

    await db.flush()

    return BaseResponse(message="已关闭内容加密")
