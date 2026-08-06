"""
媒体文件 API 路由

提供图片上传、媒体库管理等功能。
使用异步文件操作提升性能。

功能：
- 图片上传（头像、封面、文章图片）
- 媒体库管理（列表、详情、更新、删除）
- 媒体统计
"""

import asyncio
import io
import logging
import math
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.core.auth import DB, CurrentUser, get_current_user
from backend.core.concurrency import concurrent_query
from backend.models.core import Media

logger = logging.getLogger(__name__)

router = APIRouter(tags=["媒体"])

MEDIA_DIR = Path("media")
UPLOADS_DIR = MEDIA_DIR / "uploads"
AVATARS_DIR = MEDIA_DIR / "avatars"
COVERS_DIR = MEDIA_DIR / "covers"

# 允许的图片类型
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
# 流式上传块大小 64KB
CHUNK_SIZE = 64 * 1024

UPLOAD_MAGIC_MISMATCH = "UPLOAD_MAGIC_MISMATCH"
UPLOAD_PATH_TRAVERSAL = "UPLOAD_PATH_TRAVERSAL"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

MAGIC_SIGNATURES: dict[str, tuple[tuple[bytes, ...], ...]] = {
    ".jpg": ((b"\xff\xd8\xff",),),
    ".jpeg": ((b"\xff\xd8\xff",),),
    ".png": ((b"\x89PNG\r\n\x1a\n",),),
    ".gif": ((b"GIF8",),),
    ".webp": ((b"RIFF", b"WEBP"),),
    ".svg": (),
}

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}

SAFE_NAME_RE = re.compile(r"[^\w\-.一-龠ぁ-ゔァ-ヴー\u4e00-\u9fa5a-zA-Z0-9]")


def _sanitize_filename(filename: str) -> str:
    name = Path(Path(filename).name).name or "upload"
    stem = Path(name).stem or "file"
    suffix = Path(name).suffix.lower()
    safe_stem = SAFE_NAME_RE.sub("_", stem) or "file"
    if not suffix:
        suffix = ".bin"
    return f"{safe_stem}{suffix}"


def _resolve_available_path(media_dir: Path, safe_name: str) -> Path:
    candidate = media_dir / safe_name
    if not candidate.exists():
        return candidate
    stem = Path(safe_name).stem
    suffix = Path(safe_name).suffix
    i = 1
    while True:
        candidate = media_dir / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def _validate_magic(head: bytes, ext: str, filename: str) -> None:
    ext = ext.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return
    if ext == ".svg":
        stripped = head.lstrip().lower()
        if not (
            stripped.startswith(b"<svg")
            or stripped.startswith(b"<?xml")
            or b"<!doctype svg" in stripped
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "message": "上传文件内容与扩展名不匹配（SVG magic）",
                    "error_code": UPLOAD_MAGIC_MISMATCH,
                },
            )
        return
    signatures = MAGIC_SIGNATURES.get(ext)
    if not signatures:
        return
    for sig in signatures:
        ok = True
        offset = 0
        for part in sig:
            chunk = head[offset : offset + len(part)]
            if chunk != part:
                ok = False
                break
            if part == b"RIFF":
                offset = 8
        if ok:
            return
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "success": False,
            "message": "上传文件内容与扩展名不匹配",
            "error_code": UPLOAD_MAGIC_MISMATCH,
        },
    )


async def save_upload(
    file: UploadFile,
    media_dir: Path = UPLOADS_DIR,
    max_upload_bytes: int = MAX_UPLOAD_BYTES,
    size: int | None = None,
) -> tuple[Path, bytes]:
    """
    安全保存上传文件：魔数校验 + 文件名 sanitize + 路径遍历防护 + 大小限制

    Returns:
        (最终保存的绝对/规范化路径, 文件二进制内容)

    Raises:
        HTTPException(413, REQUEST_ENTITY_TOO_LARGE)
        HTTPException(422, UPLOAD_MAGIC_MISMATCH)
        HTTPException(422, UPLOAD_PATH_TRAVERSAL)
    """
    filename = file.filename or "upload.bin"
    ext = Path(filename).suffix.lower()

    content = await file.read()
    total_size = size if size is not None else len(content)
    if total_size > max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "success": False,
                "message": f"文件大小不能超过 {max_upload_bytes // (1024 * 1024)}MB",
                "error_code": "REQUEST_ENTITY_TOO_LARGE",
            },
        )

    head = content[:512]
    _validate_magic(head, ext, filename)

    media_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _sanitize_filename(filename)
    target_dir_resolved = media_dir.resolve()
    final_path = _resolve_available_path(target_dir_resolved, safe_name).resolve()
    try:
        final_path.relative_to(target_dir_resolved)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "success": False,
                "message": "非法文件路径",
                "error_code": UPLOAD_PATH_TRAVERSAL,
            },
        ) from exc
    if not final_path.is_relative_to(target_dir_resolved):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "success": False,
                "message": "非法文件路径",
                "error_code": UPLOAD_PATH_TRAVERSAL,
            },
        )

    await async_write_file(final_path, content)
    return final_path, content


async def ensure_dirs() -> None:
    """异步确保媒体目录存在"""
    for dir_path in [UPLOADS_DIR, AVATARS_DIR, COVERS_DIR]:
        await aiofiles.os.makedirs(str(dir_path), exist_ok=True)


async def async_save_file(filepath: Path, content: bytes) -> None:
    """
    异步保存文件

    Args:
        filepath: 文件路径
        content: 文件内容
    """
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)


async def async_read_file(filepath: Path) -> bytes:
    """
    异步读取文件

    Args:
        filepath: 文件路径

    Returns:
        文件内容
    """
    async with aiofiles.open(filepath, "rb") as f:
        return await f.read()


async def async_write_file(filepath: Path, content: bytes) -> int:
    """
    异步写入文件

    Args:
        filepath: 文件路径
        content: 文件内容

    Returns:
        写入的字节数
    """
    async with aiofiles.open(filepath, "wb") as f:
        return await f.write(content)


async def async_delete_file(filepath: Path) -> bool:
    """
    异步删除文件

    Args:
        filepath: 文件路径

    Returns:
        是否删除成功
    """
    try:
        await aiofiles.os.remove(str(filepath))
        return True
    except FileNotFoundError:
        return False


async def async_file_exists(filepath: Path) -> bool:
    """
    异步检查文件是否存在

    Args:
        filepath: 文件路径

    Returns:
        文件是否存在
    """
    try:
        await aiofiles.os.stat(str(filepath))
        return True
    except FileNotFoundError:
        return False


async def async_save_stream(filepath: Path, stream: Any) -> int:
    """
    异步流式保存文件

    Args:
        filepath: 文件路径
        stream: 文件流（UploadFile 的 file 属性）

    Returns:
        写入的总字节数
    """
    total_size = 0
    async with aiofiles.open(filepath, "wb") as f:
        while True:
            chunk = await stream.read(CHUNK_SIZE)
            if not chunk:
                break
            await f.write(chunk)
            total_size += len(chunk)
    return total_size


async def validate_image_async(content: bytes) -> tuple[int, int, Any]:
    """
    异步验证图片并返回尺寸信息

    Args:
        content: 图片二进制内容

    Returns:
        (宽度, 高度, PIL Image 对象)

    Raises:
        ValueError: 图片无效时抛出
    """
    from PIL import Image

    def _open_image():
        return Image.open(io.BytesIO(content))

    image = await asyncio.to_thread(_open_image)
    width, height = image.size
    return width, height, image


async def process_and_save_image(
    image: Any,
    filepath: Path,
    format: str = "JPEG",
    quality: int = 90,
) -> tuple[int, int]:
    """
    异步处理并保存图片

    Args:
        image: PIL Image 对象
        filepath: 保存路径
        format: 图片格式
        quality: 图片质量

    Returns:
        (宽度, 高度)
    """

    def _process_image():
        output = io.BytesIO()
        if image.mode in ("RGBA", "P"):
            converted_image = image.convert("RGB")
        else:
            converted_image = image
        converted_image.save(output, format=format, quality=quality)
        output.seek(0)
        return output.getvalue(), converted_image.width, converted_image.height

    content, width, height = await asyncio.to_thread(_process_image)
    await async_save_file(filepath, content)
    return width, height


class ImageUploadResponse(BaseModel):
    """图片上传响应"""

    url: str
    filename: str
    width: int
    height: int
    size: int


class ImageResponse(BaseModel):
    """图片响应"""

    url: str
    filename: str
    width: int
    height: int


@router.post("/upload", response_model=ImageUploadResponse, summary="上传图片")
async def upload_image(
    file: UploadFile = File(...),
    current_user: Any = Depends(get_current_user),
) -> ImageUploadResponse:
    """
    上传图片

    支持的格式: JPG, PNG, GIF, WebP
    最大文件大小: 10MB
    """
    await ensure_dirs()

    # 检查文件类型
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"不支持的文件类型: {file.content_type}"
        )

    # 读取文件内容
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件大小不能超过 10MB")

    # 异步验证图片
    try:
        width, height, _ = await validate_image_async(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"无效的图片文件: {str(e)}"
        )

    # 生成文件名
    ext = Path(file.filename or "image.jpg").suffix or ".jpg"
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = UPLOADS_DIR / filename

    # 异步保存文件
    await async_save_file(filepath, content)

    return ImageUploadResponse(
        url=f"/media/uploads/{filename}",
        filename=filename,
        width=width,
        height=height,
        size=len(content),
    )


@router.post("/upload/stream", response_model=ImageUploadResponse, summary="流式上传图片")
async def upload_image_stream(
    file: UploadFile = File(...),
    current_user: Any = Depends(get_current_user),
) -> ImageUploadResponse:
    """
    流式上传图片（支持大文件）

    适用于大文件上传，使用流式处理减少内存占用。
    """
    await ensure_dirs()

    # 检查文件类型
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"不支持的文件类型: {file.content_type}"
        )

    # 生成文件名
    ext = Path(file.filename or "image.jpg").suffix or ".jpg"
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = UPLOADS_DIR / filename

    # 流式保存文件
    total_size = await async_save_stream(filepath, file.file)

    # 检查文件大小
    if total_size > MAX_FILE_SIZE:
        await async_delete_file(filepath)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件大小不能超过 10MB")

    # 异步验证图片
    try:
        content = await async_read_file(filepath)
        width, height, _ = await validate_image_async(content)
    except Exception as e:
        await async_delete_file(filepath)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"无效的图片文件: {str(e)}"
        )

    return ImageUploadResponse(
        url=f"/media/uploads/{filename}",
        filename=filename,
        width=width,
        height=height,
        size=total_size,
    )


@router.post("/avatar", response_model=ImageResponse, summary="上传头像")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: Any = Depends(get_current_user),
) -> ImageResponse:
    """
    上传头像（前端已裁剪）
    """
    await ensure_dirs()

    content = await file.read()

    # 异步验证图片
    try:
        _, _, image = await validate_image_async(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"无效的图片文件: {str(e)}"
        )

    # 保存
    filename = f"{current_user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    filepath = AVATARS_DIR / filename

    width, height = await process_and_save_image(image, filepath)

    return ImageResponse(
        url=f"/media/avatars/{filename}", filename=filename, width=width, height=height
    )


@router.post("/cover", response_model=ImageResponse, summary="上传封面图")
async def upload_cover(
    file: UploadFile = File(...),
    current_user: Any = Depends(get_current_user),
) -> ImageResponse:
    """
    上传封面图（前端已裁剪）
    """
    await ensure_dirs()

    content = await file.read()

    # 异步验证图片
    try:
        _, _, image = await validate_image_async(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"无效的图片文件: {str(e)}"
        )

    # 保存
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
    filepath = COVERS_DIR / filename

    width, height = await process_and_save_image(image, filepath)

    return ImageResponse(
        url=f"/media/covers/{filename}", filename=filename, width=width, height=height
    )


# ==================== 媒体库 API ====================
# 注意：媒体库路由必须放在 /{category}/{filename} 之前，否则会被错误匹配


@router.get(
    "/library",
    summary="媒体库列表",
    description="获取媒体库文件列表，支持分页、搜索和筛选。",
)
async def list_media_library(
    db: DB,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    file_type: str | None = Query(None, description="文件类型：image/video/audio/other"),
    search: str | None = Query(None, description="搜索关键词"),
    sort_by: str = Query("created_at", description="排序字段：created_at/file_size/filename"),
    sort_order: str = Query("desc", description="排序方向：asc/desc"),
):
    """
    获取媒体库列表

    性能优化：
    - 使用并发查询获取总数和列表
    - 支持多种筛选和排序
    """
    query = select(Media).options(selectinload(Media.uploaded_by))

    # 筛选条件
    if file_type:
        query = query.where(Media.file_type == file_type)

    if search:
        query = query.where(
            Media.filename.ilike(f"%{search}%")
            | Media.title.ilike(f"%{search}%")
            | Media.description.ilike(f"%{search}%")
        )

    # 排序
    sort_column = getattr(Media, sort_by, Media.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # 并发执行计数和列表查询
    count_query = select(func.count()).select_from(query.subquery())

    total, result = await concurrent_query(
        db.scalar(count_query),
        db.execute(query.offset((page - 1) * page_size).limit(page_size)),
    )

    media_list = result.scalars().all()
    total = total or 0

    # 转换为响应格式
    items = []
    for media in media_list:
        items.append(
            {
                "id": media.id,
                "file": media.file,
                "filename": media.filename,
                "file_type": media.file_type,
                "file_size": media.file_size,
                "title": media.title,
                "alt_text": media.alt_text,
                "description": media.description,
                "uploaded_by": {
                    "id": media.uploaded_by.id,
                    "username": media.uploaded_by.username,
                    "nickname": media.uploaded_by.nickname,
                }
                if media.uploaded_by
                else None,
                "created_at": media.created_at.isoformat() if media.created_at else None,
                "updated_at": media.updated_at.isoformat() if media.updated_at else None,
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total > 0 else 0,
    }


@router.get(
    "/library/stats",
    summary="媒体库统计",
    description="获取媒体库的统计信息。",
)
async def get_media_stats(
    db: DB,
    current_user: CurrentUser,
):
    """
    获取媒体库统计信息

    性能优化：
    - 使用并发查询同时获取多个统计值
    """
    # 并发执行所有统计查询
    total_count, total_size, type_stats = await concurrent_query(
        # 总文件数
        db.scalar(select(func.count()).select_from(Media)),
        # 总文件大小
        db.scalar(select(func.sum(Media.file_size)).select_from(Media)),
        # 按类型统计
        db.execute(
            select(
                Media.file_type,
                func.count().label("count"),
                func.sum(Media.file_size).label("size"),
            ).group_by(Media.file_type)
        ),
    )

    # 处理类型统计
    type_statistics = {}
    for row in type_stats:
        type_statistics[row.file_type] = {
            "count": row.count,
            "size": row.size or 0,
        }

    return {
        "total_count": total_count or 0,
        "total_size": total_size or 0,
        "total_size_formatted": format_file_size(total_size or 0),
        "type_stats": type_statistics,
    }


@router.post(
    "/library/upload",
    summary="上传到媒体库",
    description="上传文件到媒体库，支持图片、视频、音频等。",
)
async def upload_to_library(
    db: DB,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    title: str | None = Form(None, description="标题"),
    alt_text: str | None = Form(None, description="替代文本"),
    description: str | None = Form(None, description="描述"),
):
    """
    上传文件到媒体库

    支持：
    - 图片：jpg, jpeg, png, gif, webp, svg
    - 视频：mp4, webm, mov
    - 音频：mp3, wav, ogg
    - 文档：pdf, doc, docx, xls, xlsx
    """
    # 验证文件类型
    allowed_types = {
        "image": ["jpg", "jpeg", "png", "gif", "webp", "svg"],
        "video": ["mp4", "webm", "mov"],
        "audio": ["mp3", "wav", "ogg"],
        "document": ["pdf", "doc", "docx", "xls", "xlsx"],
    }

    # 获取文件扩展名
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名不能为空",
        )

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

    # 确定文件类型
    file_type = "other"
    for ftype, extensions in allowed_types.items():
        if ext in extensions:
            file_type = ftype
            break

    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d")
    unique_id = uuid.uuid4().hex[:8]
    new_filename = f"{timestamp}_{unique_id}.{ext}"

    # 保存文件
    upload_dir = MEDIA_DIR / "uploads" / file_type
    upload_dir.mkdir(parents=True, exist_ok=True)
    filepath = upload_dir / new_filename

    content = await file.read()
    await async_write_file(filepath, content)

    # URL 路径
    file_url = f"/media/uploads/{file_type}/{new_filename}"

    # 创建数据库记录
    media = Media(
        file=file_url,
        filename=file.filename,
        file_type=file_type,
        file_size=len(content),
        title=title,
        alt_text=alt_text,
        description=description,
        uploaded_by_id=current_user.id,
    )
    db.add(media)
    await db.flush()
    await db.refresh(media)

    return {
        "success": True,
        "message": "文件上传成功",
        "media": {
            "id": media.id,
            "file": media.file,
            "filename": media.filename,
            "file_type": media.file_type,
            "file_size": media.file_size,
            "title": media.title,
            "alt_text": media.alt_text,
            "description": media.description,
        },
    }


@router.get(
    "/library/{media_id}",
    summary="媒体详情",
    description="获取单个媒体文件的详细信息。",
)
async def get_media_detail(
    media_id: int,
    db: DB,
    current_user: CurrentUser,
):
    """获取媒体详情"""
    result = await db.execute(
        select(Media).options(selectinload(Media.uploaded_by)).where(Media.id == media_id)
    )
    media = result.scalar_one_or_none()

    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="媒体文件不存在",
        )

    return {
        "id": media.id,
        "file": media.file,
        "filename": media.filename,
        "file_type": media.file_type,
        "file_size": media.file_size,
        "title": media.title,
        "alt_text": media.alt_text,
        "description": media.description,
        "uploaded_by": {
            "id": media.uploaded_by.id,
            "username": media.uploaded_by.username,
            "nickname": media.uploaded_by.nickname,
        }
        if media.uploaded_by
        else None,
        "created_at": media.created_at.isoformat() if media.created_at else None,
        "updated_at": media.updated_at.isoformat() if media.updated_at else None,
    }


@router.put(
    "/library/{media_id}",
    summary="更新媒体信息",
    description="更新媒体文件的标题、描述等信息。",
)
async def update_media(
    media_id: int,
    db: DB,
    current_user: CurrentUser,
    title: str | None = Body(None, description="标题"),
    alt_text: str | None = Body(None, description="替代文本"),
    description: str | None = Body(None, description="描述"),
):
    """更新媒体信息"""
    result = await db.execute(select(Media).where(Media.id == media_id))
    media = result.scalar_one_or_none()

    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="媒体文件不存在",
        )

    # 更新字段
    if title is not None:
        media.title = title
    if alt_text is not None:
        media.alt_text = alt_text
    if description is not None:
        media.description = description

    await db.flush()

    return {
        "success": True,
        "message": "媒体信息已更新",
        "media": {
            "id": media.id,
            "title": media.title,
            "alt_text": media.alt_text,
            "description": media.description,
        },
    }


@router.delete(
    "/library/{media_id}",
    summary="删除单个媒体",
    description="删除单个媒体文件。",
)
async def delete_media_by_id(
    media_id: int,
    db: DB,
    current_user: CurrentUser,
):
    """
    删除单个媒体

    同时删除数据库记录和物理文件
    """
    result = await db.execute(select(Media).where(Media.id == media_id))
    media = result.scalar_one_or_none()

    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="媒体文件不存在",
        )

    # 删除物理文件
    filepath = MEDIA_DIR / media.file.lstrip("/media/")
    if await async_file_exists(filepath):
        await async_delete_file(filepath)

    # 删除数据库记录
    await db.delete(media)
    await db.flush()

    return {"success": True, "message": "媒体文件已删除"}


@router.delete(
    "/library/batch",
    summary="批量删除媒体",
    description="批量删除多个媒体文件。",
)
async def batch_delete_media(
    db: DB,
    current_user: CurrentUser,
    media_ids: list[int] = Body(..., description="媒体 ID 列表"),
):
    """
    批量删除媒体

    同时删除数据库记录和物理文件
    """
    if not media_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供要删除的媒体 ID",
        )

    # 查询媒体记录
    result = await db.execute(select(Media).where(Media.id.in_(media_ids)))
    media_list = result.scalars().all()

    deleted_count = 0
    for media in media_list:
        # 删除物理文件
        filepath = MEDIA_DIR / media.file.lstrip("/media/")
        if await async_file_exists(filepath):
            await async_delete_file(filepath)

        # 删除数据库记录
        await db.delete(media)
        deleted_count += 1

    await db.flush()

    return {
        "success": True,
        "message": f"已删除 {deleted_count} 个媒体文件",
        "deleted_count": deleted_count,
    }


# ==================== 图片文件访问 API ====================


@router.get("/{category}/{filename}", summary="获取图片")
async def get_image(category: str, filename: str):
    """获取图片文件"""
    valid_categories = ["uploads", "avatars", "covers", "defaults"]
    if category not in valid_categories:
        raise HTTPException(status_code=404, detail="图片不存在")

    filepath = MEDIA_DIR / category / filename
    if not await async_file_exists(filepath):
        raise HTTPException(status_code=404, detail="图片不存在")

    # 异步读取文件内容
    content = await async_read_file(filepath)

    def iter_content():
        yield content

    return StreamingResponse(
        iter_content(),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000"},
    )


@router.delete("/{category}/{filename}", summary="删除图片")
async def delete_image(
    category: str,
    filename: str,
    current_user: Any = Depends(get_current_user),
):
    """删除图片文件"""
    valid_categories = ["uploads", "avatars", "covers"]
    if category not in valid_categories:
        raise HTTPException(status_code=404, detail="图片不存在")

    filepath = MEDIA_DIR / category / filename
    if not await async_file_exists(filepath):
        raise HTTPException(status_code=404, detail="图片不存在")

    await async_delete_file(filepath)

    return {"success": True, "message": "图片已删除"}


def format_file_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


# ==================== Bing 每日壁纸代理 API ====================

import os as _os
import time as _time
from typing import Any as _Any

from fastapi import Request as _Request
from fastapi import Response as _Response
from fastapi.responses import JSONResponse as _JSONResponse

BING_API_URL = "https://www.bing.com/HPImageArchive.aspx"
BING_WALLPAPER_CACHE_TTL = 3600 * 12  # 12 小时

_bing_fallback_cache: dict[str, tuple[float, list[dict[str, _Any]]]] = {}
_bing_last_success: list[dict[str, _Any]] | None = None
_bing_last_success_at: float = 0.0
BING_FALLBACK_TTL = 3600 * 24  # 24 小时


def _get_proxy() -> str | None:
    http_proxy = _os.environ.get("HTTP_PROXY") or _os.environ.get("http_proxy")
    https_proxy = _os.environ.get("HTTPS_PROXY") or _os.environ.get("https_proxy")
    return https_proxy or http_proxy or None


def _build_full_url(url: str | None, urlbase: str | None) -> str:
    if url:
        if url.startswith("http"):
            return url
        return f"https://www.bing.com{url}"
    if urlbase:
        return f"https://www.bing.com{urlbase}_1920x1080.jpg"
    return ""


@router.get(
    "/bing-wallpaper",
    summary="Bing 每日壁纸代理（支持批量）",
    description=(
        "代理 Bing 每日壁纸 API，支持 HTTP/HTTPS 代理、12h 缓存、"
        "出错时 fallback 到最近 24h 成功结果。"
    ),
)
async def get_bing_wallpaper_batch(
    request: _Request,
    idx: int = Query(0, description="偏移天数 (0=今天, 1=昨天...)，超出范围自动 clamp 到 [0, 7]"),
    n: int = Query(1, description="返回壁纸数量，超出范围自动 clamp 到 [1, 15]"),
    mkt: str = Query("zh-CN", description="地区市场，如 zh-CN / en-US / ja-JP"),
) -> _Response:
    idx = max(0, min(7, int(idx)))
    n = max(1, min(15, int(n)))
    cache_key = f"bing_wallpaper_{idx}_{n}_{mkt}"

    # 1) 尝试 12h 缓存
    try:
        from backend.core.cache import cache, make_cache_key

        full_key = make_cache_key(cache_key)
        cached = await cache.get(full_key)
        if cached and isinstance(cached, dict) and "images" in cached:
            resp = _JSONResponse(content=cached)
            resp.headers["Access-Control-Allow-Origin"] = "*"
            resp.headers["X-Bing-Cache"] = "HIT"
            return resp
    except Exception:
        pass

    # 2) 请求 Bing API
    import httpx as _httpx

    proxy = _get_proxy()
    params = {"format": "js", "idx": idx, "n": n, "mkt": mkt}
    images_out: list[dict[str, _Any]] = []

    try:
        timeout = _httpx.Timeout(15.0, connect=8.0)
        async with _httpx.AsyncClient(timeout=timeout, proxy=proxy) as client:
            raw = await client.get(BING_API_URL, params=params)
            if raw.status_code != 200:
                raise RuntimeError(f"Bing HTTP {raw.status_code}")
            data = raw.json()
    except Exception as exc:
        logger.warning(f"Bing 壁纸请求失败 idx={idx} n={n} mkt={mkt}: {exc}")
        # 3a) fallback: 最近一次成功 (24h)
        global _bing_last_success, _bing_last_success_at
        now = _time.time()
        if _bing_last_success and (now - _bing_last_success_at) < BING_FALLBACK_TTL:
            take = max(1, min(n, len(_bing_last_success)))
            images_out = _bing_last_success[:take]
        else:
            # 3b) 最终 fallback: 空占位
            images_out = [
                {
                    "url": "",
                    "urlbase": "",
                    "title": "Bing 壁纸暂不可用",
                    "copyright": "Rosetta 内置占位",
                    "copyrightlink": "",
                    "startdate": "",
                    "enddate": "",
                    "full_url": "",
                }
            ]
        body = {"images": images_out}
        resp = _JSONResponse(content=body, status_code=200)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["X-Bing-Cache"] = "FALLBACK"
        return resp

    raw_images = data.get("images") or []
    for img in raw_images:
        url = img.get("url") or ""
        urlbase = img.get("urlbase") or ""
        images_out.append(
            {
                "url": url,
                "urlbase": urlbase,
                "title": img.get("title", ""),
                "copyright": img.get("copyright", ""),
                "copyrightlink": img.get("copyrightlink", ""),
                "startdate": img.get("startdate", ""),
                "enddate": img.get("enddate", ""),
                "full_url": _build_full_url(url, urlbase),
            }
        )

    body = {"images": images_out}

    # 更新 last-success fallback
    if images_out:
        _bing_last_success = list(images_out)
        _bing_last_success_at = _time.time()

    # 写 12h 缓存
    try:
        from backend.core.cache import cache, make_cache_key

        full_key = make_cache_key(cache_key)
        await cache.set(full_key, body, BING_WALLPAPER_CACHE_TTL)
    except Exception:
        pass

    resp = _JSONResponse(content=body)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["X-Bing-Cache"] = "MISS"
    return resp
