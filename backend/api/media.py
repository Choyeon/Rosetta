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
import mimetypes
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.core.auth import DB, CurrentStaff, CurrentUser, get_current_user
from backend.core.concurrency import concurrent_query
from backend.core.plugin_bus import bus
from backend.models.core import Media
from backend.schemas import raw_content_response
from backend.services.media_service import apply_watermark, build_media_url, generate_thumbnails

logger = logging.getLogger(__name__)

router = APIRouter(tags=["媒体"])

MEDIA_DIR = Path("media")
UPLOADS_DIR = MEDIA_DIR / "uploads"
AVATARS_DIR = MEDIA_DIR / "avatars"
COVERS_DIR = MEDIA_DIR / "covers"


def _resolve_media_file_path(stored: str | None) -> Path:
    """把 Media.file 存储路径（如 ``/media/uploads/image/x.png``）解析为 MEDIA_DIR 内的绝对路径。

    修复点：
    - 原实现用 ``lstrip("/media/")`` 是**字符集**语义，会连续吃掉路径开头所有
      属于 {/, m, e, d, i, a} 的字符（如 ``/media/image/…`` 会被错剥成 ``ge/…``）；
      改为精确的前缀剥离 + 绝对 URL 分离。
    - 同时防御路径穿越：解析结果必须仍位于 MEDIA_DIR 之内。
    """
    rel = (stored or "").strip()
    if rel.startswith(("http://", "https://")):
        # 外链文件（CDN / 远程 URL）：本地无文件可删
        raise FileNotFoundError("外链媒体文件不在本地存储")
    if rel.startswith("/media/"):
        rel = rel[len("/media/") :]
    rel = rel.lstrip("/")
    candidate = (MEDIA_DIR / rel).resolve()
    media_root = MEDIA_DIR.resolve()
    if candidate != media_root and media_root not in candidate.parents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="非法的媒体文件路径",
        )
    return candidate


async def _delete_media_derivatives(media: Media) -> list[str]:
    """删除 Media.sizes 记录的派生档（thumbnail/medium/large 等变体）。

    删除路径原先只删 media.file 原图，上传时生成的派生档永久残留成磁盘孤儿
    （2026-09 curl 实证：DELETE 后 -large/-medium/-thumbnail 三件仍在）。
    单项失败不阻断记录删除，返回失败 URL 列表供调用方记日志。"""
    failed: list[str] = []
    sizes = media.sizes if isinstance(media.sizes, dict) else {}
    for entry in sizes.values():
        url = entry.get("url") if isinstance(entry, dict) else None
        if not url:
            continue
        try:
            path = _resolve_media_file_path(url)
            if await async_file_exists(path):
                await async_delete_file(path)
        except FileNotFoundError:
            continue  # 外链档（远程 URL）/ 本就不存在：无需处理
        except Exception as err:  # noqa: BLE001 - 派生档失败不得阻断记录删除
            logger.warning("派生档删除失败（%s）：%s", url, err)
            failed.append(str(url))
    return failed


# 允许的图片类型
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
# 流式上传块大小 64KB
CHUNK_SIZE = 64 * 1024

UPLOAD_MAGIC_MISMATCH = "UPLOAD_MAGIC_MISMATCH"
UPLOAD_PATH_TRAVERSAL = "UPLOAD_PATH_TRAVERSAL"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
# 单文件上传上限 10MB（upload_image / upload_image_stream 使用）
MAX_FILE_SIZE = 10 * 1024 * 1024

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

# 媒体库「文件格式分类 → 扩展名」白名单。服务端强制校验（AGENTS §12.7 双校验红线），
# 清单与前端 composables/useUploadProgress.ts::ALLOWED_UPLOAD_EXTENSIONS 同源。
LIBRARY_TYPE_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "image": ("jpg", "jpeg", "png", "gif", "webp", "svg"),
    "video": ("mp4", "webm", "mov"),
    "audio": ("mp3", "wav", "ogg"),
    "document": ("pdf", "doc", "docx", "xls", "xlsx"),
}
LIBRARY_ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    ext for exts in LIBRARY_TYPE_EXTENSIONS.values() for ext in exts
)

UPLOAD_EXT_REJECTED = "UPLOAD_EXT_REJECTED"
UPLOAD_SVG_UNSAFE = "UPLOAD_SVG_UNSAFE"

# SVG 与页面同源渲染（/media 静态挂载 + GET /media/{category}/{filename}），
# 内含脚本即等价于站点自身的 XSS，因此按内容拒绝，扩展名白名单挡不住它。
_SVG_UNSAFE_RE = re.compile(rb"<script|\son[a-z]+\s*=|javascript:", re.IGNORECASE)


def _file_type_for_ext(ext: str) -> str:
    """扩展名 → 文件格式分类；调用前必须先过 LIBRARY_ALLOWED_EXTENSIONS。"""
    for ftype, extensions in LIBRARY_TYPE_EXTENSIONS.items():
        if ext in extensions:
            return ftype
    return "other"  # pragma: no cover - 白名单已排除


def _assert_svg_content_safe(content: bytes) -> None:
    """拒绝含可执行内容的 SVG（script 标签 / 事件处理器 / javascript: 协议）。"""
    if _SVG_UNSAFE_RE.search(content):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "SVG 含脚本或事件处理器属性，已拒绝上传（同源渲染会造成 XSS）",
                "error_code": UPLOAD_SVG_UNSAFE,
            },
        )


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
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
        HTTPException(400, UPLOAD_SVG_UNSAFE)
        HTTPException(422, UPLOAD_MAGIC_MISMATCH)
        HTTPException(422, UPLOAD_PATH_TRAVERSAL)
    """
    filename = file.filename or "upload.bin"
    ext = Path(filename).suffix.lower()

    content = await file.read()
    total_size = size if size is not None else len(content)
    if total_size > max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={
                "success": False,
                "message": f"文件大小不能超过 {max_upload_bytes // (1024 * 1024)}MB",
                "error_code": "REQUEST_ENTITY_TOO_LARGE",
            },
        )

    head = content[:512]
    _validate_magic(head, ext, filename)
    if ext == ".svg":
        _assert_svg_content_safe(content)

    media_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _sanitize_filename(filename)
    target_dir_resolved = media_dir.resolve()
    final_path = _resolve_available_path(target_dir_resolved, safe_name).resolve()
    try:
        final_path.relative_to(target_dir_resolved)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "success": False,
                "message": "非法文件路径",
                "error_code": UPLOAD_PATH_TRAVERSAL,
            },
        ) from exc
    if not final_path.is_relative_to(target_dir_resolved):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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


async def async_save_stream(
    filepath: Path, stream: UploadFile, max_bytes: int | None = None
) -> int:
    """
    异步流式保存文件

    Args:
        filepath: 文件路径
        stream: FastAPI/Starlette 的 ``UploadFile`` 本体——它的 ``read`` 是异步的
            （内部转 threadpool）。传 ``upload.file``（同步 BinaryIO）会立刻
            ``await bytes`` 抛 TypeError；本函数早期正是那么调的，导致
            ``POST /media/upload/stream`` 从未真正可用过。
        max_bytes: 写入过程中即生效的字节上限；None 表示不限制

    Returns:
        写入的总字节数

    Raises:
        HTTPException(413): 超过 max_bytes。超限的字节已经落盘，
            所以必须在这里删掉半成品——否则"先全部写完再比较大小"的写法
            等于允许调用方用任意大的请求体打满磁盘（Nginx 侧放行 50m）。
    """
    total_size = 0
    oversize = False
    async with aiofiles.open(filepath, "wb") as f:
        while True:
            chunk = await stream.read(CHUNK_SIZE)
            if not chunk:
                break
            total_size += len(chunk)
            await f.write(chunk)
            if max_bytes is not None and total_size > max_bytes:
                oversize = True
                break

    if oversize:
        await async_delete_file(filepath)
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"文件大小不能超过 {max_bytes // (1024 * 1024)}MB",
        )
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
        # JPEG 不支持 alpha 通道，保存前必须去掉透明/调色板模式
        # Pillow 支持的 JPEG 安全模式：1 / L / RGB / CMYK / YCbCr / I / I;16 / F
        # 其他模式（RGBA / RGBa / LA / PA / P 等）统一转 RGB，避免
        # "cannot write mode LA as JPEG" / "cannot write mode RGBA as JPEG" 类错误。
        save_format = (format or "JPEG").upper()
        if save_format in {"JPEG", "JPG"}:
            jpeg_safe = {"1", "L", "RGB", "CMYK", "YCbCr", "I", "I;16", "F"}
            if image.mode not in jpeg_safe:
                converted_image = image.convert("RGB")
            else:
                converted_image = image
        else:
            converted_image = image
        converted_image.save(output, format=save_format, quality=quality)
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


# ═══════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════════


class MediaThumbnailSize(BaseModel):
    """单档缩略图（``Media.sizes`` 的一个取值）。"""

    url: str = Field(..., description="该档缩略图的对外可访问 URL")
    width: int = Field(..., description="缩略图宽度（像素）")
    height: int = Field(..., description="缩略图高度（像素）")


class MediaUploaderRef(BaseModel):
    """媒体条目上的上传者摘要（只含展示字段，不含邮箱等私密信息）。"""

    id: int = Field(..., description="上传者用户 ID")
    username: str = Field(..., description="上传者用户名")
    nickname: str | None = Field(None, description="上传者昵称，未设置时为 null")


class MediaItemBase(BaseModel):
    """媒体记录的对外公共字段（``Media`` 表投影；时间统一为 ISO 字符串）。"""

    id: int = Field(..., description="媒体记录 ID")
    file: str = Field(
        ...,
        description=(
            "文件可访问地址（入库前经 CDN 前缀改写）：未配置 CDN 时是站内相对路径，"
            "配置后是绝对 http(s) URL；任何情况下都不是服务器上的磁盘路径"
        ),
    )
    filename: str | None = Field(
        None, description="上传时的原始文件名（已 sanitize 前的客户端命名）"
    )
    file_type: str = Field(
        ..., description="文件格式分类：image / video / audio / document（由扩展名白名单派生）"
    )
    file_size: int = Field(0, description="文件大小（字节）")
    title: str | None = Field(None, description="标题")
    alt_text: str | None = Field(None, description="替代文本")
    description: str | None = Field(None, description="描述")
    width: int | None = Field(None, description="原图宽度（像素）；非图片为 null")
    height: int | None = Field(None, description="原图高度（像素）；非图片为 null")
    sizes: dict[str, MediaThumbnailSize] | None = Field(
        None,
        description=(
            "多尺寸缩略图表，键为档位名 thumbnail / medium / large；"
            "非图片、SVG 或后处理失败时为 null"
        ),
    )
    uploaded_by: MediaUploaderRef | None = Field(
        None, description="上传者摘要；记录未关联上传者时为 null"
    )
    created_at: str | None = Field(None, description="创建时间 ISO 8601 字符串；无值时为 null")
    updated_at: str | None = Field(None, description="更新时间 ISO 8601 字符串；无值时为 null")


class MediaLibraryItem(MediaItemBase):
    """媒体库列表项：公共字段之上再挂一组前端 AdminMediaItem 别名字段。"""

    url: str = Field(..., description="与 ``file`` 同值的可访问 URL（前端读取的别名）")
    category: str = Field(..., description="与 ``file_type`` 同值的业务分类别名")
    mime: str = Field(
        ...,
        description="按文件名推断的 MIME；推不出时回退 ``file_type``，再兜底 application/octet-stream",
    )
    size_bytes: int = Field(0, description="与 ``file_size`` 同值的字节数别名")


class MediaLibraryListResponse(BaseModel):
    """媒体库列表端点的响应体（裸分页信封，不带 success）。"""

    items: list[MediaLibraryItem] = Field(default_factory=list, description="当前页媒体条目")
    total: int = Field(0, description="符合筛选条件的媒体总数")
    page: int = Field(1, description="当前页码（回显请求参数）")
    page_size: int = Field(20, description="每页数量（回显请求参数，上限 100）")
    total_pages: int = Field(0, description="总页数 = ceil(total / page_size)，total 为 0 时是 0")


class MediaDetailResponse(MediaItemBase):
    """单媒体详情端点的响应体（一条媒体记录，无列表用的别名字段）。"""


class MediaUploadMetadata(BaseModel):
    """上传结果里的 ``metadata`` 载荷。"""

    sizes: dict[str, MediaThumbnailSize] | None = Field(
        None, description="生成的多尺寸缩略图表；非图片或后处理失败时为 null"
    )
    file_type: str = Field(..., description="按扩展名判定的文件格式分类")


class MediaUploadResult(BaseModel):
    """媒体库上传成功后的响应体（两个上传路径同构）。"""

    id: int = Field(..., description="新建媒体记录 ID")
    title: str | None = Field(None, description="标题（取自表单，未填为 null）")
    description: str | None = Field(None, description="描述（取自表单，未填为 null）")
    alt_text: str | None = Field(None, description="替代文本（取自表单，未填为 null）")
    filename: str | None = Field(
        None,
        description="入库记录里的文件名（即客户端提交的原始文件名）；记录该列为空时回退本次生成的落盘名",
    )
    original_name: str | None = Field(None, description="客户端提交的原始文件名")
    url: str = Field(..., description="文件可访问 URL（已按 CDN 前缀生成）")
    thumbnail_url: str = Field(
        ...,
        description="缩略图 URL：按 thumbnail → medium → large 取首个可用档位，全缺省时等于 ``url``",
    )
    category: str = Field(
        ...,
        description="业务分类：表单传入且合法时用表单值，否则回退文件格式分类",
    )
    mime_type: str = Field(
        ...,
        description="MIME：图片取 Pillow 识别结果，其它取请求声明的 content-type 或 application/octet-stream",
    )
    size: int = Field(..., description="文件大小（字节，按实际读到的内容长度计）")
    width: int | None = Field(None, description="原图宽度（像素）；非图片为 null")
    height: int | None = Field(None, description="原图高度（像素）；非图片为 null")
    duration: None = Field(None, description="音视频时长：当前实现固定为 null（未探测）")
    storage: str = Field("local", description="存储位置标识，当前实现固定为 local")
    metadata: MediaUploadMetadata = Field(..., description="附加元信息（缩略图表与文件格式分类）")
    is_active: bool = Field(True, description="是否启用：入库即为 true")
    created_at: str = Field("", description="创建时间 ISO 字符串；记录缺值时为空字符串")
    updated_at: str = Field("", description="更新时间 ISO 字符串；记录缺值时为空字符串")


class MediaUpdatedInfo(BaseModel):
    """媒体信息更新成功后回显的媒体字段子集。"""

    id: int = Field(..., description="媒体记录 ID")
    title: str | None = Field(None, description="更新后的标题")
    alt_text: str | None = Field(None, description="更新后的替代文本")
    description: str | None = Field(None, description="更新后的描述")
    width: int | None = Field(None, description="原图宽度（像素），本端点不修改该值")
    height: int | None = Field(None, description="原图高度（像素），本端点不修改该值")
    sizes: dict[str, MediaThumbnailSize] | None = Field(
        None, description="多尺寸缩略图表，本端点不修改该值"
    )


class MediaUpdateResponse(BaseModel):
    """媒体信息更新端点的响应体。"""

    success: bool = Field(True, description="固定为 true（失败走 HTTPException 错误信封）")
    message: str = Field("媒体信息已更新", description="人类可读结果")
    media: MediaUpdatedInfo = Field(..., description="更新后回显的字段子集")


class MediaTypeStat(BaseModel):
    """单个文件格式分类的计数与占用。"""

    count: int = Field(0, description="该格式的文件数")
    size: int = Field(0, description="该格式占用字节数合计；NULL 行按 0 计")


class MediaStatsData(BaseModel):
    """媒体库统计载荷（同一数值挂了多组前端别名字段）。"""

    total_count: int = Field(0, description="媒体文件总数")
    total_size: int = Field(0, description="全部文件占用字节数")
    total_size_formatted: str = Field(
        "0.00 B", description="人类可读体积（B/KB/MB/GB/TB/PB，保留两位小数）"
    )
    type_stats: dict[str, MediaTypeStat] = Field(
        default_factory=dict,
        description="按文件格式分类的统计，键为 image / video / audio / document（仅出现库里实际存在的类型）",
    )
    total_files: int = Field(0, description="与 ``total_count`` 同值的前端别名")
    total_size_bytes: int = Field(0, description="与 ``total_size`` 同值的字节数别名")
    images: int = Field(0, description="image 分类文件数（type_stats 缺该键时为 0）")
    videos: int = Field(0, description="video 分类文件数")
    audios: int = Field(0, description="audio 分类文件数")
    documents: int = Field(0, description="document 分类文件数")


class MediaStatsResponse(BaseModel):
    """媒体库统计端点的响应体。"""

    success: bool = Field(True, description="固定为 true")
    data: MediaStatsData = Field(..., description="统计载荷")
    message: str = Field("获取媒体库统计成功", description="人类可读结果")


class MediaDeleteRefusal(BaseModel):
    """批量删除中被拒绝保留的单条记录。"""

    id: int = Field(..., description="被保留的媒体记录 ID")
    reason: str = Field(..., description="拒绝删除的原因（存储路径不落在媒体目录内）")


class MediaBatchDeleteResponse(BaseModel):
    """媒体批量删除端点的响应体。"""

    success: bool = Field(True, description="固定为 true；调用方须再看 refused / missing_ids")
    message: str = Field(..., description="汇总文案，含保留与不存在条目的数量")
    deleted_count: int = Field(0, description="实际删除的记录数")
    refused: list[MediaDeleteRefusal] = Field(
        default_factory=list,
        description="路径非法被拒绝删除（DB 记录与物理文件都保留）的条目",
    )
    missing_ids: list[int] = Field(
        default_factory=list, description="请求里查无此记录的媒体 ID（升序）"
    )


class MediaDeleteResponse(BaseModel):
    """单媒体删除端点的响应体。"""

    success: bool = Field(True, description="固定为 true；失败路径走 HTTPException 错误信封")
    message: str = Field("媒体文件已删除", description="人类可读结果")


class ImageDeleteResponse(BaseModel):
    """按「分类目录 + 文件名」删除图片端点的响应体。"""

    success: bool = Field(True, description="固定为 true；失败路径走 HTTPException 错误信封")
    message: str = Field("图片已删除", description="人类可读结果")


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

    与 `save_upload` 的区别只在写入方式：分块边读边写，避免把整张图先读进内存。
    安全口径（扩展名白名单 + 魔数 + SVG 主动内容 + 大小上限）与 `save_upload` 一致。
    """
    await ensure_dirs()

    # 检查文件类型
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"不支持的文件类型: {file.content_type}"
        )

    # content_type 由客户端自报，不能当唯一依据：`image/png` + `x.html`
    # 就能把可执行文档塞进同源可访问的 uploads 目录（AGENTS §12.7 双校验红线）。
    ext = Path(file.filename or "image.jpg").suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": f"不支持的文件扩展名: {ext or '(无扩展名)'}",
                "error_code": UPLOAD_EXT_REJECTED,
            },
        )

    # 生成文件名
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = UPLOADS_DIR / filename

    # 流式保存文件（超限即在写入过程中中断并清理半成品）
    total_size = await async_save_stream(filepath, file, max_bytes=MAX_FILE_SIZE)

    # 校验内容与扩展名相符，且不是伪装成图片的脚本载体
    try:
        content = await async_read_file(filepath)
        _validate_magic(content[:16], ext, filename)
        if ext == ".svg":
            _assert_svg_content_safe(content)
        width, height, _ = await validate_image_async(content)
    except HTTPException:
        await async_delete_file(filepath)
        raise
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
    description=(
        "获取媒体库文件列表，支持分页、搜索和筛选。需 staff 及以上权限（未登录 401，非管理员 403）。"
        "`file_type` 与 `category` 都映射到同一列，同时传入时 `file_type` 优先；"
        "`page_size` 上限 100；`sort_by` 只接受 created_at / file_size / filename / updated_at，"
        "非法值静默回退 created_at；`search` 对文件名、标题、描述做不区分大小写的模糊匹配。"
    ),
    responses={200: {"model": MediaLibraryListResponse}},
)
async def list_media_library(
    db: DB,
    current_user: CurrentStaff,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    file_type: str | None = Query(None, description="文件类型：image/video/audio/other"),
    category: str | None = Query(None, description="业务分类：image/video/audio/document/other"),
    search: str | None = Query(None, description="搜索关键词"),
    sort_by: str = Query("created_at", description="排序字段：created_at/file_size/filename"),
    sort_order: str = Query("desc", description="排序方向：asc/desc"),
):
    """
    获取媒体库列表

    性能优化：
    - 支持多种筛选和排序
    """
    query = select(Media).options(selectinload(Media.uploaded_by))

    # 筛选条件：file_type 与 category 都映射到 Media.file_type
    # （Media 表以 file_type 区分文件格式；category 是前端业务分类别名）
    if file_type:
        query = query.where(Media.file_type == file_type)
    elif category:
        query = query.where(Media.file_type == category)

    if search:
        query = query.where(
            Media.filename.ilike(f"%{search}%")
            | Media.title.ilike(f"%{search}%")
            | Media.description.ilike(f"%{search}%")
        )

    # 排序白名单（与端点文档一致：created_at/file_size/filename；防 getattr 命中方法属性）
    _SORTABLE = {
        "created_at": Media.created_at,
        "file_size": Media.file_size,
        "filename": Media.filename,
        "updated_at": Media.updated_at,
    }
    sort_column = _SORTABLE.get(sort_by, Media.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # 计数 + 列表（两条顺序查询；concurrent_query 不并行）
    count_query = select(func.count()).select_from(query.subquery())

    total, result = await concurrent_query(
        db.scalar(count_query),
        db.execute(query.offset((page - 1) * page_size).limit(page_size)),
    )

    media_list = result.scalars().all()
    total = total or 0

    # 转换为响应格式
    # 字段对齐前端 AdminMediaItem：url / mime / size_bytes / category
    # （media.file 在入库时已是 build_media_url 生成的可访问 URL）
    items = []
    for media in media_list:
        guessed_mime = mimetypes.guess_type(media.filename or "")[0]
        items.append(
            {
                "id": media.id,
                "file": media.file,
                "url": media.file,
                "filename": media.filename,
                "file_type": media.file_type,
                "category": media.file_type,
                "mime": guessed_mime or media.file_type or "application/octet-stream",
                "file_size": media.file_size,
                "size_bytes": media.file_size or 0,
                "title": media.title,
                "alt_text": media.alt_text,
                "description": media.description,
                "width": media.width,
                "height": media.height,
                "sizes": media.sizes,
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
    description=(
        "获取媒体库的统计信息：总文件数、总占用字节数与人类可读体积，"
        "并按文件格式分类给出计数。需 staff 及以上权限（未登录 401，非管理员 403）。"
        "单次请求内跑三条聚合查询，未做缓存。"
    ),
    responses={200: {"model": MediaStatsResponse}},
)
async def get_media_stats(
    db: DB,
    current_user: CurrentStaff,
):
    """
    获取媒体库统计信息

    性能优化：
    """
    # 顺序执行多条统计查询
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
        "success": True,
        "data": {
            "total_count": total_count or 0,
            "total_size": total_size or 0,
            "total_size_formatted": format_file_size(total_size or 0),
            "type_stats": type_statistics,
            # 前端 AdminMediaStats 别名字段（total_files / total_size_bytes / 分类型计数）
            "total_files": total_count or 0,
            "total_size_bytes": total_size or 0,
            "images": type_statistics.get("image", {}).get("count", 0),
            "videos": type_statistics.get("video", {}).get("count", 0),
            "audios": type_statistics.get("audio", {}).get("count", 0),
            "documents": type_statistics.get("document", {}).get("count", 0),
        },
        "message": "获取媒体库统计成功",
    }


async def _save_media_to_library(
    db: Any,
    current_user: Any,
    file: UploadFile,
    *,
    category: str | None = None,
    title: str | None = None,
    alt_text: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """
    内部实现：将上传文件写入媒体库。

    参数：
    - category：前端传来的业务分类（gallery/post-cover/avatar 等），仅用于创建 AdminPhoto
      等上层业务关联，**不**写入 Media 表（Media 表以 file_type 区分文件格式）。
    - 落盘路径为 ``MEDIA_DIR/uploads/<file_type>/<时间戳>_<随机名>.<ext>``；``ext``
      必须命中 ``LIBRARY_ALLOWED_EXTENSIONS``，未知/危险扩展名直接 400——前端
      useUploadProgress 的白名单只是体验优化，服务端不信任它（AGENTS §12.7）。
    返回：扁平化的 MediaItem-like 字典，与前端 types/api.ts 的 MediaItem 对齐。
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名不能为空",
        )

    # 校验单文件大小：20MB（含非图片文件），避免 uvicorn 被大文件打爆连接
    size_hint = getattr(file, "size", None)
    if isinstance(size_hint, int) and size_hint > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"文件过大，最大允许 {MAX_UPLOAD_BYTES // 1024 // 1024}MB",
        )

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in LIBRARY_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": f"不支持的文件类型：.{ext or '(无扩展名)'}",
                "error_code": UPLOAD_EXT_REJECTED,
            },
        )

    # ext 命中白名单 ⇒ 必然归属某一类，不存在 other 兜底
    file_type = _file_type_for_ext(ext)

    timestamp = datetime.now().strftime("%Y%m%d")
    unique_id = uuid.uuid4().hex[:8]
    new_filename = f"{timestamp}_{unique_id}.{ext}"

    # 物理落盘
    upload_dir = MEDIA_DIR / "uploads" / file_type
    upload_dir.mkdir(parents=True, exist_ok=True)
    filepath = upload_dir / new_filename

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"文件过大，最大允许 {MAX_UPLOAD_BYTES // 1024 // 1024}MB",
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="上传文件内容为空",
        )
    if ext == "svg":
        _assert_svg_content_safe(content)
    await async_write_file(filepath, content)

    cdn_prefix = await _read_cdn_prefix(db)
    file_url = build_media_url(f"/media/uploads/{file_type}/{new_filename}", cdn_prefix)

    # 图片：压缩原图 + 生成多尺寸缩略图 + 可选水印
    width: int | None = None
    height: int | None = None
    sizes: dict | None = None
    thumbnail_url: str | None = None
    mime_type = file.content_type or "application/octet-stream"
    if file_type == "image" and ext.lower() not in ("svg",):
        try:
            pil_image = await _open_image_decoded(filepath)
            width, height = pil_image.size
            mime_type = getattr(pil_image, "get_format_mimetype", lambda: mime_type)() or mime_type

            # 压缩原图：超大图缩放 + JPEG/WebP 质量优化
            compressed = await _compress_original_image(pil_image, filepath, ext)
            if compressed is not None:
                pil_image = compressed
                width, height = pil_image.size

            watermark_text = await _read_watermark_text(db)
            if watermark_text:
                pil_image = await apply_watermark(pil_image, watermark_text)
                encoded = await asyncio.to_thread(_pil_to_bytes, pil_image, ext)
                await async_write_file(filepath, encoded)
            sizes = await generate_thumbnails(
                pil_image, upload_dir, f"{timestamp}_{unique_id}", f".{ext}", cdn_prefix
            )
            # 取 thumbnail / medium / large 第一个可用 URL 做缩略图
            for key in ("thumbnail", "medium", "large"):
                if (
                    sizes
                    and isinstance(sizes, dict)
                    and sizes.get(key)
                    and isinstance(sizes[key], dict)
                ):
                    maybe_url = sizes[key].get("url")
                    if maybe_url:
                        thumbnail_url = str(maybe_url)
                        break
        except Exception as e:
            logger.warning(f"图片后处理失败（压缩/缩略图/水印），仅保存原图: {e}")

    # category：若前端传入则优先使用（例如 gallery）；否则回退 file_type
    final_category = category or file_type
    valid_categories = {
        "image",
        "video",
        "audio",
        "document",
        "other",
        "gallery",
        "post-cover",
        "avatar",
        "cover",
    }
    if final_category not in valid_categories:
        final_category = file_type

    media = Media(
        file=file_url,
        filename=file.filename,
        file_type=file_type,
        file_size=len(content),
        title=title,
        alt_text=alt_text,
        description=description,
        width=width,
        height=height,
        sizes=sizes,
        uploaded_by_id=current_user.id,
    )
    db.add(media)
    await db.flush()
    await db.refresh(media)

    # 素材入库事件：webhook 端点是第三方地址，故显式给出对外字段，
    # 不把整条 Media 记录交给总线去扫（见 api/webhook.py 的 payload 白名单）
    await bus.do_action(
        "media.uploaded",
        media,
        webhook_payload={
            "id": media.id,
            "filename": media.filename,
            "file_type": media.file_type,
            "file_size": media.file_size,
            "url": media.file,
        },
    )

    return {
        "id": media.id,
        "title": media.title,
        "description": media.description,
        "alt_text": media.alt_text,
        "filename": media.filename or new_filename,
        "original_name": file.filename,
        "url": media.file,
        "thumbnail_url": thumbnail_url or media.file,
        "category": final_category,  # type: ignore[arg-type]
        "mime_type": mime_type,
        "size": media.file_size,
        "width": media.width,
        "height": media.height,
        "duration": None,
        "storage": "local",
        "metadata": {
            "sizes": sizes,
            "file_type": file_type,
        },
        "is_active": True,
        "created_at": media.created_at.isoformat() if media.created_at else "",
        "updated_at": media.updated_at.isoformat() if media.updated_at else "",
    }


@router.post(
    "/library",
    summary="上传到媒体库（REST 主路径）",
    description=(
        "与媒体库列表接口配对：上传文件到媒体库。需 staff 及以上权限（未登录 401，非管理员 403）。"
        "multipart 单文件上限 20MB（超限 413 REQUEST_ENTITY_TOO_LARGE）；"
        "扩展名白名单为 image(jpg/jpeg/png/gif/webp/svg)、video(mp4/webm/mov)、"
        "audio(mp3/wav/ogg)、document(pdf/doc/docx/xls/xlsx)，未命中返回 400 UPLOAD_EXT_REJECTED；"
        "含脚本或事件处理器属性的 SVG 按内容拒绝（400 UPLOAD_SVG_UNSAFE）；空文件 400。"
        "category 用于业务分类（gallery/post-cover 等），非法值静默回退文件格式分类；"
        "图片会压缩原图并生成 thumbnail/medium/large 三档缩略图，站点配置了水印文案时叠加水印。"
    ),
    responses={200: {"model": MediaUploadResult}},
)
async def upload_library_rest(
    db: DB,
    current_user: CurrentStaff,
    file: UploadFile = File(...),
    category: str | None = Form(
        None, description="业务分类：gallery / post-cover / avatar / cover 等"
    ),
    title: str | None = Form(None, description="标题"),
    alt_text: str | None = Form(None, description="替代文本"),
    description: str | None = Form(None, description="描述"),
):
    """REST 风格：POST /api/media/library"""
    try:
        return await _save_media_to_library(
            db,
            current_user,
            file,
            category=category,
            title=title,
            alt_text=alt_text,
            description=description,
        )
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover - 防御性兜底
        logger.exception("媒体库上传失败")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传失败：{e}",
        )


@router.post(
    "/library/upload",
    summary="上传到媒体库（别名路径）",
    description=(
        "兼容旧客户端的别名路径，参数、鉴权（staff 及以上）、"
        "20MB 上限、扩展名白名单、SVG 内容拦截与缩略图行为均与 REST 主路径一致。"
    ),
    responses={200: {"model": MediaUploadResult}},
)
async def upload_to_library(
    db: DB,
    current_user: CurrentStaff,
    file: UploadFile = File(...),
    category: str | None = Form(
        None, description="业务分类：gallery / post-cover / avatar / cover 等"
    ),
    title: str | None = Form(None, description="标题"),
    alt_text: str | None = Form(None, description="替代文本"),
    description: str | None = Form(None, description="描述"),
):
    try:
        return await _save_media_to_library(
            db,
            current_user,
            file,
            category=category,
            title=title,
            alt_text=alt_text,
            description=description,
        )
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover
        logger.exception("媒体库上传失败 (别名路径)")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传失败：{e}",
        )


@router.get(
    "/library/{media_id}",
    summary="媒体详情",
    description=(
        "获取单个媒体文件的详细信息。需登录（任意角色，游客 401）；"
        "记录不存在或 ID 无法解析为整数时分别返回 404 / 422。"
    ),
    responses={200: {"model": MediaDetailResponse}},
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
        "width": media.width,
        "height": media.height,
        "sizes": media.sizes,
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
    description=(
        "更新媒体文件的标题、替代文本与描述。需 staff 及以上权限（未登录 401，非管理员 403）。"
        "采用「传了才改」语义：请求体中为 null 的字段保留原值，因此无法用本接口清空已有文案；"
        "只改元信息，不触碰物理文件与缩略图；记录不存在返回 404。"
    ),
    responses={200: {"model": MediaUpdateResponse}},
)
async def update_media(
    media_id: int,
    db: DB,
    current_user: CurrentStaff,
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
    await db.refresh(media)

    return {
        "success": True,
        "message": "媒体信息已更新",
        "media": {
            "id": media.id,
            "title": media.title,
            "alt_text": media.alt_text,
            "description": media.description,
            "width": media.width,
            "height": media.height,
            "sizes": media.sizes,
        },
    }


@router.delete(
    "/library/batch",
    summary="批量删除媒体",
    description=(
        "批量删除多个媒体文件，同时删除数据库记录和物理文件。需 staff 及以上权限（未登录 401，非管理员 403）。"
        "ids 为空数组返回 400。响应除 `deleted_count` 外还回 `refused`（路径非法、记录被保留的条目）"
        "与 `missing_ids`，调用方不得只看 `success` 判定全部删除完成。"
    ),
    responses={200: {"model": MediaBatchDeleteResponse}},
)
async def batch_delete_media(
    db: DB,
    current_user: CurrentStaff,
    ids: list[int] = Body(..., embed=True, description="媒体 ID 列表"),
):
    """
    批量删除媒体

    同时删除数据库记录和物理文件。

    注意：本路由必须注册在 ``/library/{media_id}`` 之前，
    否则 FastAPI 会把路径段 "batch" 尝试按 int 解析 ``{media_id}`` → 422。
    """
    if not ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供要删除的媒体 ID",
        )

    # 查询媒体记录
    result = await db.execute(select(Media).where(Media.id.in_(ids)))
    media_list = result.scalars().all()

    deleted_count = 0
    refused: list[dict] = []
    for media in media_list:
        # 非法路径必须**拒绝删除该条记录**：单条删除走的是 `raise`，批量这里原先把
        # HTTPException 一起吞掉却照样删 DB 行，等于留着越权文件变成永久孤儿，
        # 而界面上显示"已删除"。FileNotFoundError 才是可忽略的正常分支（文件本就不在）。
        try:
            filepath = _resolve_media_file_path(media.file)
        except HTTPException as exc:
            logger.warning("批量删除跳过媒体 %s：文件路径非法（%s）", media.id, exc.detail)
            refused.append({"id": media.id, "reason": str(exc.detail)})
            continue
        try:
            if await async_file_exists(filepath):
                await async_delete_file(filepath)
        except FileNotFoundError:
            pass
        await _delete_media_derivatives(media)

        # 删除数据库记录
        await db.delete(media)
        deleted_count += 1

    await db.flush()

    missing = sorted(set(ids) - {m.id for m in media_list})
    message = f"已删除 {deleted_count} 个媒体文件"
    if refused:
        message += f"，{len(refused)} 个因路径非法被保留"
    if missing:
        message += f"，{len(missing)} 个 ID 不存在"

    return {
        "success": True,
        "message": message,
        "deleted_count": deleted_count,
        "refused": refused,
        "missing_ids": missing,
    }


@router.delete(
    "/library/{media_id}",
    summary="删除单个媒体",
    description=(
        "删除单个媒体文件，同时删除数据库记录、物理原图与 sizes 中的全部派生档（thumbnail/medium/large）。"
        "需 staff 及以上权限（未登录 401，非管理员 403）。"
        "记录不存在返回 404；存储路径不落在媒体目录内时拒绝删除并返回 400（UPLOAD_PATH_TRAVERSAL）；"
        "外链记录（远程 URL）仅删数据库记录。"
    ),
    responses={200: {"model": MediaDeleteResponse}},
)
async def delete_media_by_id(
    media_id: int,
    db: DB,
    current_user: CurrentStaff,
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

    # 删除物理文件（原图 + sizes 里的全部派生档）
    try:
        filepath = _resolve_media_file_path(media.file)
        if await async_file_exists(filepath):
            await async_delete_file(filepath)
    except FileNotFoundError:
        pass  # 外链文件：仅删数据库记录
    except HTTPException:
        raise  # 非法路径：显式拒绝，避免误删其他文件
    await _delete_media_derivatives(media)

    # 删除数据库记录
    await db.delete(media)
    await db.flush()

    return {"success": True, "message": "媒体文件已删除"}


# ==================== 图片文件访问 API ====================


def _resolve_category_filepath(category: str, filename: str) -> Path:
    """净化文件名并校验最终路径位于 MEDIA_DIR/category 之内，防止路径穿越。"""
    safe_name = _sanitize_filename(filename)
    target_dir_resolved = (MEDIA_DIR / category).resolve()
    final_path = (target_dir_resolved / safe_name).resolve()
    if not final_path.is_relative_to(target_dir_resolved):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "非法文件路径",
                "error_code": UPLOAD_PATH_TRAVERSAL,
            },
        )
    return final_path


@router.get(
    "/{category}/{filename}",
    summary="获取图片",
    description=(
        "按「分类目录 + 文件名」直出图片二进制流，公开访问、无需鉴权。"
        "category 仅接受 uploads / avatars / covers / defaults，其余返回 404；"
        "文件名先经净化并校验落在媒体目录内，越界返回 400（error_code: UPLOAD_PATH_TRAVERSAL）。"
        "Content-Type 按扩展名映射，未知类型回退 application/octet-stream 并带 X-Content-Type-Options: nosniff；"
        "响应带 Cache-Control: public, max-age=31536000（一年强缓存），分块 64KB 流式读盘。"
    ),
    responses=raw_content_response(
        "image/*",
        "图片二进制流；Content-Type 按扩展名映射，未知类型回退 application/octet-stream。",
        binary=True,
    ),
    response_class=Response,
)
async def get_image(category: str, filename: str) -> StreamingResponse:
    """获取图片文件"""
    valid_categories = ["uploads", "avatars", "covers", "defaults"]
    if category not in valid_categories:
        raise HTTPException(status_code=404, detail="图片不存在")

    filepath = _resolve_category_filepath(category, filename)
    if not await async_file_exists(filepath):
        raise HTTPException(status_code=404, detail="图片不存在")

    # 按扩展名推断 MIME，避免把 png/svg/webp 硬标成 image/jpeg 导致浏览器渲染异常
    suffix = Path(filename).suffix.lower().lstrip(".")
    _MIME_MAP = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
        "svg": "image/svg+xml",
        "bmp": "image/bmp",
        "avif": "image/avif",
        "ico": "image/x-icon",
    }
    media_type = _MIME_MAP.get(suffix, "application/octet-stream")

    # 分块读盘直出：整文件 async_read_file 会把每张图（最大 10MB）完整压进内存，
    # 图库页并发加载 N 张就是 N 倍峰值；生成器按 CHUNK_SIZE 边读边发。
    async def aiter_file(path: Path):
        async with aiofiles.open(path, "rb") as f:
            while True:
                chunk = await f.read(CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        aiter_file(filepath),
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=31536000",
            # 显式声明不嗅探：octet-stream 兜底依赖浏览器尊重 Content-Type
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete(
    "/{category}/{filename}",
    summary="删除图片",
    description=(
        "按「分类目录 + 文件名」直接删除物理文件，需 staff 权限"
        "（与按媒体 ID 删除的口径一致）。"
        "文件名先经净化并校验落在媒体目录内，越界返回 400（error_code: UPLOAD_PATH_TRAVERSAL）；"
        "分类非法或文件不存在返回 404。注意：本接口只删物理文件，不清理对应的数据库记录。"
    ),
    responses={200: {"model": ImageDeleteResponse}},
)
async def delete_image(
    category: str,
    filename: str,
    current_user: CurrentStaff,
):
    """删除图片文件（按文件名直删物理文件，仅限 staff）"""
    valid_categories = ["uploads", "avatars", "covers"]
    if category not in valid_categories:
        raise HTTPException(status_code=404, detail="图片不存在")

    filepath = _resolve_category_filepath(category, filename)
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


# ─────────────────────────────────────────────────────────────────────────────
# 媒体高级能力辅助：从 site_configs 读 media 组配置（CDN / 水印）
# ─────────────────────────────────────────────────────────────────────────────


async def _read_media_settings(db: DB) -> dict:
    """读取 site_configs 中 key='media' 的 JSON 配置。"""
    from backend.models.core import SiteConfig

    result = await db.execute(select(SiteConfig).where(SiteConfig.key == "media"))
    row = result.scalar_one_or_none()
    if not row or not row.value:
        return {}
    try:
        import json

        return json.loads(row.value)
    except Exception:
        return {}


async def _read_cdn_prefix(db: DB) -> str | None:
    """返回启用的 CDN 前缀，未启用返回 None。"""
    cfg = await _read_media_settings(db)
    if not cfg.get("use_cdn"):
        return None
    prefix = (cfg.get("cdn_prefix") or "").strip()
    return prefix or None


async def _read_watermark_text(db: DB) -> str | None:
    """返回水印文字（media 组 watermark_text 非空时启用），否则 None。"""
    cfg = await _read_media_settings(db)
    text = (cfg.get("watermark_text") or "").strip()
    return text or None


async def _open_image_decoded(path: Path):
    """打开并**完整解码**图片，返回 PIL.Image。

    ``Image.open`` 只是惰性建对象，真正的 CPU 在 ``load()``，因此两步必须在同一个
    worker 线程里完成；否则一次上传就把事件循环按住几十到几百毫秒。
    """
    from PIL import Image

    def _open_and_load():
        img = Image.open(path)
        img.load()
        return img

    return await asyncio.to_thread(_open_and_load)


def _pil_to_bytes(image: Any, ext: str) -> bytes:
    """把 PIL.Image 序列化为字节（用于回写加了水印的原图）。"""

    out = io.BytesIO()
    save_format = "JPEG" if ext.lower() in ("jpg", "jpeg", "webp") else "PNG"
    img = image
    if img.mode in ("RGBA", "P", "LA") and save_format == "JPEG":
        img = img.convert("RGB")
    img.save(out, format=save_format, quality=90)
    return out.getvalue()


# 原图压缩相关常量
MAX_ORIGINAL_DIMENSION = 3840  # 超过此边长的原图会被等比缩放
JPEG_WEBP_QUALITY = 85  # JPEG/WebP 重保存质量
PNG_OPTIMIZE = True


async def _compress_original_image(image: Any, filepath: Path, ext: str) -> Any | None:
    """
    压缩原图并回写磁盘，返回压缩后的 PIL Image；未压缩返回 None。

    策略：
    - 边长超过 MAX_ORIGINAL_DIMENSION：等比缩放（LANCZOS）
    - JPEG / WebP：以 JPEG_WEBP_QUALITY 质量重保存（透明通道转 RGB）
    - PNG：optimize=True 重保存（无损）
    - 仅在确实需要压缩时回写，避免无谓的质量损失
    """
    from PIL import Image

    orig_w, orig_h = image.size
    needs_resize = max(orig_w, orig_h) > MAX_ORIGINAL_DIMENSION
    ext_lower = ext.lower()
    is_jpeg_like = ext_lower in ("jpg", "jpeg", "webp")
    is_png = ext_lower == "png"

    if not needs_resize and not is_jpeg_like and not is_png:
        return None

    img = image
    changed = False

    if needs_resize:
        ratio = MAX_ORIGINAL_DIMENSION / max(orig_w, orig_h)
        new_w = max(1, round(orig_w * ratio))
        new_h = max(1, round(orig_h * ratio))

        def _resize():
            return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        img = await asyncio.to_thread(_resize)
        changed = True

    if is_jpeg_like:
        # JPEG/WebP 统一走质量压缩
        save_format = "WEBP" if ext_lower == "webp" else "JPEG"

        def _save_jpeg():
            working = img
            if working.mode in ("RGBA", "P", "LA", "RGBa"):
                working = working.convert("RGB")
            out = io.BytesIO()
            working.save(
                out,
                format=save_format,
                quality=JPEG_WEBP_QUALITY,
                optimize=True,
                progressive=(save_format == "JPEG"),
            )
            return out.getvalue()

        compressed_bytes = await asyncio.to_thread(_save_jpeg)
        # 仅当压缩后更小才回写，避免反而变大
        if len(compressed_bytes) < filepath.stat().st_size or changed:
            await async_write_file(filepath, compressed_bytes)
            changed = True
        return img

    if is_png and needs_resize:
        # PNG 仅在缩放后才重保存（无损 optimize）
        def _save_png():
            out = io.BytesIO()
            img.save(out, format="PNG", optimize=PNG_OPTIMIZE)
            return out.getvalue()

        png_bytes = await asyncio.to_thread(_save_png)
        if len(png_bytes) < filepath.stat().st_size:
            await async_write_file(filepath, png_bytes)
        return img

    return img if changed else None


# ==================== Bing 每日壁纸代理 API ====================

BING_API_URL = "https://www.bing.com/HPImageArchive.aspx"
BING_WALLPAPER_CACHE_TTL = 3600 * 12  # 12 小时

_bing_fallback_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_bing_last_success: list[dict[str, Any]] | None = None
_bing_last_success_at: float = 0.0
BING_FALLBACK_TTL = 3600 * 24  # 24 小时


def _get_proxy() -> str | None:
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
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
    request: Request,
    idx: int = Query(0, description="偏移天数 (0=今天, 1=昨天...)，超出范围自动 clamp 到 [0, 7]"),
    n: int = Query(1, description="返回壁纸数量，超出范围自动 clamp 到 [1, 15]"),
    mkt: str = Query("zh-CN", description="地区市场，如 zh-CN / en-US / ja-JP"),
) -> Response:
    idx = max(0, min(7, int(idx)))
    n = max(1, min(15, int(n)))
    cache_key = f"bing_wallpaper_{idx}_{n}_{mkt}"

    # 1) 尝试 12h 缓存
    try:
        from backend.core.cache import cache, make_cache_key

        full_key = make_cache_key(cache_key)
        cached = await cache.get(full_key)
        if cached and isinstance(cached, dict) and "images" in cached:
            resp = JSONResponse(content=cached)
            resp.headers["Access-Control-Allow-Origin"] = "*"
            resp.headers["X-Bing-Cache"] = "HIT"
            return resp
    except ImportError as exc:
        # 只可能发生在 import 阶段：RedisCacheBackend / MemoryCacheBackend 的 get 自己
        # 就 try/except 到底并 logger.error 后返回 None，缓存层从不向外抛异常。
        logger.warning(f"[bing] 缓存模块不可用，跳过缓存读取: {exc}")

    # 2) 请求 Bing API
    import httpx as _httpx

    proxy = _get_proxy()
    params = {"format": "js", "idx": idx, "n": n, "mkt": mkt}
    images_out: list[dict[str, Any]] = []

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
        now = time.time()
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
        resp = JSONResponse(content=body, status_code=200)
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
        _bing_last_success_at = time.time()

    # 写 12h 缓存
    try:
        from backend.core.cache import cache, make_cache_key

        full_key = make_cache_key(cache_key)
        await cache.set(full_key, body, BING_WALLPAPER_CACHE_TTL)
    except ImportError as exc:
        # 同上：缓存层内部已降级，写失败只是下次重新请求 Bing，端点还有 last-success 兜底
        logger.warning(f"[bing] 缓存模块不可用，跳过缓存写入: {exc}")

    resp = JSONResponse(content=body)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["X-Bing-Cache"] = "MISS"
    return resp
