"""
验证码系统

支持图形验证码和验证码验证。
"""

import base64
import io
import random
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.cache import cache
from backend.core.database import Base
from backend.utils.compat import UTC


class CaptchaRecord(Base):
    """验证码记录"""

    __tablename__ = "captcha_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


router = APIRouter(tags=["验证码"])


class CaptchaResponse(BaseModel):
    """验证码响应"""

    key: str
    image: str  # Base64 编码的图片


class CaptchaVerifyRequest(BaseModel):
    """验证码验证请求"""

    key: str
    code: str


# ═══════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════════


class CaptchaVerifyResponse(BaseModel):
    """验证码校验端点的响应体（失败一律走 400 错误信封，故出现即代表通过）。"""

    success: bool = Field(True, description="固定为 true：不通过时本接口抛 400 而不返回 false")
    message: str = Field("验证成功", description="人类可读结果")


def generate_captcha_code(length: int = 4) -> str:
    """生成验证码字符串"""
    # 排除容易混淆的字符
    chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "".join(random.choice(chars) for _ in range(length))


def generate_captcha_image(code: str, width: int = 120, height: int = 40) -> bytes:
    """
    生成验证码图片

    使用 PIL 生成简单的验证码图片。
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        # 如果没有 PIL，返回一个简单的占位图
        return b""

    # 创建图片
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # 尝试使用系统字体
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except Exception:
        try:
            font = ImageFont.truetype("arial.ttf", 28)
        except Exception:
            font = ImageFont.load_default()

    # 添加干扰线
    for _ in range(3):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(200, 200, 200), width=1)

    # 添加干扰点
    for _ in range(100):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        draw.point(
            (x, y),
            fill=(random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)),
        )

    # 绘制验证码文字
    text_width = len(code) * 25
    x = (width - text_width) // 2
    y = (height - 30) // 2

    for i, char in enumerate(code):
        # 随机颜色
        color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        # 随机偏移
        offset_x = random.randint(-3, 3)
        offset_y = random.randint(-3, 3)
        draw.text((x + i * 25 + offset_x, y + offset_y), char, font=font, fill=color)

    # 转换为 bytes
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@router.get(
    "",
    response_model=CaptchaResponse,
    summary="获取验证码",
    description=(
        "生成并返回一个图形验证码。公开接口、无需鉴权。"
        "code 是 4 位字符，字符集刻意排除易混淆的 0/O/1/I；"
        "image 字段是 data:image/png;base64 内联图，可直接塞进 img 标签。"
        "答案按 key 存进缓存，有效期 5 分钟，过期后校验会返回 400。"
    ),
)
async def get_captcha():
    """
    获取验证码

    返回验证码 key 和 Base64 编码的图片。
    验证码有效期为 5 分钟。
    """
    import uuid

    # 生成验证码
    code = generate_captcha_code(4)
    key = uuid.uuid4().hex[:16]

    # 生成图片
    image_bytes = generate_captcha_image(code)
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    # 存储到缓存（5 分钟有效）
    await cache.set(f"captcha:{key}", code.lower(), 300)

    return CaptchaResponse(
        key=key,
        image=f"data:image/png;base64,{image_base64}",
    )


@router.post(
    "/verify",
    summary="验证验证码",
    description=(
        "验证用户输入的验证码是否正确。公开接口、无需鉴权。"
        "比对不区分大小写。key 不存在或已过期返回 400（验证码已过期或不存在）。"
        "是一次性凭据：无论校验成功还是失败都会立即作废，"
        "失败即作废是为了挡住小字符集下的在线枚举，因此前端重试必须重新获取验证码。"
        "成功响应为裸 dict（success + message），无 data 信封。"
    ),
    responses={200: {"model": CaptchaVerifyResponse}},
)
async def verify_captcha(
    data: CaptchaVerifyRequest,
):
    """
    验证验证码

    验证成功后验证码失效。
    """
    # 从缓存获取验证码
    stored_code = await cache.get(f"captcha:{data.key}")

    if not stored_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码已过期或不存在",
        )

    # 验证（不区分大小写）
    if data.code.lower() != stored_code.lower():
        # 错误即作废：验证码字符集只有 32^4≈100 万组合，
        # 若失败不作废，5 分钟有效期内可被在线暴力枚举
        await cache.delete(f"captcha:{data.key}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误",
        )

    # 验证成功后删除验证码
    await cache.delete(f"captcha:{data.key}")

    return {"success": True, "message": "验证成功"}


async def check_captcha_required(ip_address: str) -> bool:
    """
    检查是否需要验证码

    根据登录失败次数判断是否需要验证码。
    """
    # 获取该 IP 的失败次数
    fail_count = await cache.get(f"login_fail:{ip_address}") or 0
    return fail_count >= 3


async def record_login_fail(ip_address: str):
    """记录登录失败"""
    key = f"login_fail:{ip_address}"
    count = await cache.get(key) or 0
    await cache.set(key, count + 1, 1800)  # 30 分钟


async def clear_login_fail(ip_address: str):
    """清除登录失败记录"""
    await cache.delete(f"login_fail:{ip_address}")
