"""
媒体服务层：CDN URL 构造、缩略图生成、水印。

这些逻辑原本散落在 ``api/media.py`` 里；抽成服务层是为了：
1. 单元测试可直接 import（不依赖 FastAPI 请求/DB 会话）；
2. 未来的 Webhook、批处理脚本、插件也能复用缩略图/水印管线。
"""

from __future__ import annotations

import asyncio
import io
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# 缩略图尺寸预设（宽高上限，保持宽高比，不裁剪）
_THUMBNAIL_PRESETS: dict[str, tuple[int, int]] = {
    "thumbnail": (150, 150),
    "medium": (300, 300),
    "large": (1024, 1024),
}

# 缩略图输出目录对应的 URL 前缀：统一映射到 /media/uploads/
# 这样 Nginx 或 StaticFiles 挂载 /media → <project>/media/uploads 都能一致访问。
_UPLOADS_URL_PREFIX = "/media/uploads/"


def build_media_url(path: str, cdn_prefix: str | None = None) -> str:
    """根据是否启用 CDN，把本地 /media/... 路径拼成对外 URL。

    规则：
    * ``path`` 已经是绝对 http(s) URL → 原样返回，不套用 CDN；
    * ``cdn_prefix`` 为空 → 原样返回 path；
    * ``path`` 以 ``/media/`` 开头 → 把 ``/media/`` 前缀替换为 cdn_prefix；
    * 其他路径 → 直接 ``urljoin(cdn_prefix, path)``。

    测试断言要求：
        build_media_url("/media/uploads/x.jpg", "https://cdn.example.com/")
        == "https://cdn.example.com/media/uploads/x.jpg"
        build_media_url("/media/uploads/x.jpg") == "/media/uploads/x.jpg"
        build_media_url("https://other.com/a.png", "https://cdn.example.com")
        == "https://other.com/a.png"
    """
    if not path:
        return path
    # 绝对 URL 不动
    if isinstance(path, str) and re.match(r"^https?://", path):
        return path
    if not cdn_prefix:
        return path
    # 归一化 cdn_prefix：去掉末尾斜杠，再统一按 / 拼接
    clean_prefix = cdn_prefix.rstrip("/")
    if path.startswith("/media/"):
        # 拼接后保证 cdn_prefix/media/...
        return clean_prefix + path
    # 非 /media/ 路径用 urljoin（不处理相对 cdn_prefix 的情况）
    return urljoin(clean_prefix + "/", path.lstrip("/"))


async def generate_thumbnails(
    image: Image.Image,
    output_dir: Path | str,
    filename_stem: str,
    ext_with_dot: str,
    cdn_prefix: str | None = None,
) -> dict[str, dict[str, Any]]:
    """为给定 PIL Image 生成多尺寸缩略图，返回 {size: {url, width, height}}。

    生成的物理文件：``{output_dir}/{filename_stem}-{size}{ext_with_dot}``。
    URL：使用 ``_UPLOADS_URL_PREFIX`` 前缀拼接 + 可选 cdn_prefix 替换。

    注意：如果原图尺寸小于预设的 max 尺寸，则直接复用 ``large`` 为原图大小（不放大）。
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = ext_with_dot if ext_with_dot.startswith(".") else f".{ext_with_dot}"

    result: dict[str, dict[str, Any]] = {}

    def _do_one(size_key: str, max_w: int, max_h: int) -> None:
        im = image.copy()
        orig_w, orig_h = im.size
        ratio = min(max_w / orig_w, max_h / orig_h, 1.0)  # 不放大
        new_w = max(1, round(orig_w * ratio))
        new_h = max(1, round(orig_h * ratio))
        if (new_w, new_h) != (orig_w, orig_h):
            im = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
        fname = f"{filename_stem}-{size_key}{ext}"
        fpath = out_dir / fname
        save_format = ext.lstrip(".").upper()
        if save_format == "JPG":
            save_format = "JPEG"
        # 兼容 alpha：缩略图统一按安全规则保存
        save_kwargs: dict[str, Any] = {}
        if save_format == "JPEG":
            if im.mode not in {"1", "L", "RGB", "CMYK", "YCbCr", "I", "I;16", "F"}:
                im = im.convert("RGB")
            save_kwargs["quality"] = 85
        elif save_format == "PNG":
            save_kwargs["optimize"] = True
        im.save(fpath, format=save_format, **save_kwargs)
        # 对外 URL 按 uploads 前缀算
        relative = f"{filename_stem}-{size_key}{ext}"
        # 约定：传入的 output_dir 对应 URL 的 /media/uploads/ 目录
        # （media.py 中 upload_dir = media/uploads/<type>/，因此 relative 前还要补目录？
        #  实际上上层调用在 media.py 生成的 upload_dir 就等于 media/uploads/<type>，
        #  但 thumbnail 文件名本身不含 <type> 前缀；因此需要我们按 output_dir 推出
        #  相对于 MEDIA_ROOT/uploads 的子路径。）
        try:
            sub = out_dir.relative_to(MEDIA_ROOT / "uploads")
            rel_path_part = f"{sub.as_posix()}/{relative}" if str(sub) != "." else relative
        except Exception:
            rel_path_part = relative
        url = build_media_url(f"{_UPLOADS_URL_PREFIX}{rel_path_part}", cdn_prefix)
        result[size_key] = {"url": url, "width": im.size[0], "height": im.size[1]}

    # 串行执行避免一次性占用过多内存；异步层使用 to_thread 不阻塞事件循环
    loop = asyncio.get_running_loop()
    for key, (mw, mh) in _THUMBNAIL_PRESETS.items():
        await loop.run_in_executor(None, _do_one, key, mw, mh)
    return result


async def apply_watermark(image: Image.Image, text: str) -> Image.Image:
    """给图像右下角加文字水印，返回新的 PIL Image（RGB 模式）。"""
    if not text:
        return image

    def _apply():
        # 转 RGB 方便合成
        src = image.convert("RGB")
        w, h = src.size
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        # 字体：优先用系统常见字体，失败则默认位图字体
        font = None
        for candidate in ("arial.ttf", "msyh.ttc", "msyh.ttf", "DejaVuSans.ttf"):
            try:
                font = ImageFont.truetype(candidate, size=max(14, min(w, h) // 40))
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()
        # 估测文本框
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            tw, th = draw.textsize(text, font=font) if hasattr(draw, "textsize") else (len(text) * 10, 16)
        margin = max(8, min(w, h) // 40)
        pos = (w - tw - margin, h - th - margin)
        # 阴影
        draw.text((pos[0] + 1, pos[1] + 1), text, font=font, fill=(0, 0, 0, 120))
        draw.text(pos, text, font=font, fill=(255, 255, 255, 210))
        combined = Image.alpha_composite(src.convert("RGBA"), overlay)
        return combined.convert("RGB")

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _apply)
