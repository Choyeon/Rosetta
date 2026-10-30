"""
Hero 轮播相关 Pydantic Schema
"""

import re
from datetime import datetime
from typing import Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.schemas._url_policy import reject_pseudo_url_scheme as _reject_pseudo_url_scheme
from backend.utils.compat import to_utc_instant

MediaType = Literal["image", "video", "youtube"]
TextAlign = Literal["left", "center", "right"]
TextColor = Literal["light", "dark"]

# YouTube 视频 ID 固定 11 个字符（base64url 字符集）
_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_HOSTS = {"youtube.com", "m.youtube.com", "youtube-nocookie.com", "youtu.be"}


def extract_youtube_id(url: str | None) -> str | None:
    """从常见 YouTube 地址形态里取视频 ID；解析不出来回 None。

    支持裸 ID、youtu.be/<id>、watch?v=<id>、/embed/<id>、/shorts/<id>、/live/<id>。
    写口用它拒绝不可嵌入的地址；读侧（前端 `lib/hero-media.ts` 同口径）对历史脏数据
    回落封面图，不因为一条坏链接让整页 500。
    """
    if not url:
        return None
    candidate = url.strip()
    if _YOUTUBE_ID_RE.match(candidate):
        return candidate
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host.removeprefix("www.")
    if host not in _YOUTUBE_HOSTS:
        return None
    if host == "youtu.be":
        vid = parsed.path.lstrip("/").split("/")[0]
        return vid if _YOUTUBE_ID_RE.match(vid) else None
    if parsed.path.rstrip("/") == "/watch":
        vid = (parse_qs(parsed.query).get("v") or [""])[0]
        return vid if _YOUTUBE_ID_RE.match(vid) else None
    for prefix in ("/embed/", "/shorts/", "/live/", "/v/"):
        if parsed.path.startswith(prefix):
            vid = parsed.path[len(prefix) :].split("/")[0]
            return vid if _YOUTUBE_ID_RE.match(vid) else None
    return None


def validate_media_pair(media_type: str, media_url: str | None) -> str | None:
    """校验「媒体类型 ↔ 媒体地址」的搭配，返回错误文案（None = 通过）。

    写口（Create 的 schema 校验 + Update 合并现值后的端点校验）共用这一份判据：

    - youtube：地址必须能解析出视频 ID，前端据此拼 `youtube-nocookie.com/embed/<id>`；
      解析不出的地址存进去就是一块空白 iframe（甚至会把任意站外页面嵌进来）。
    - video：必须是站内路径（`/media/...`）。CSP 的 `media-src` 只有 `'self' blob: data:`，
      外链视频会被浏览器直接拦掉——表现是"后台存成功了、首页一片黑"，不如在写口就拒绝。
    - image：不额外约束（外链图片由 `img-src https:` 放行）。
    """
    url = (media_url or "").strip()
    if not url:
        return "媒体地址不能为空"
    if media_type == "youtube":
        if extract_youtube_id(url) is None:
            return "YouTube 地址无法解析出视频 ID（支持 watch?v= / youtu.be / embed / shorts）"
        return None
    if media_type == "video":
        # `//host/...` 是协议相对外链，同样逃出 media-src 'self'
        if not url.startswith("/") or url.startswith("//"):
            return "视频地址必须是站内路径（如 /media/xxx.mp4），外链会被 CSP 拦截"
        return None
    return None


class HeroSlideBase(BaseModel):
    """Hero 幻灯片基础模型"""

    title: str | None = Field(None, description="主标题（多语言 JSON）")
    subtitle: str | None = Field(None, description="副标题（多语言 JSON）")
    media_type: MediaType = Field(default="image", description="媒体类型")
    media_url: str = Field(..., min_length=1, max_length=500, description="媒体地址")
    poster_url: str | None = Field(None, max_length=500, description="视频封面图")
    overlay_opacity: int = Field(default=40, ge=0, le=100, description="遮罩透明度 0-100")
    overlay_color: str = Field(default="#000000", max_length=20, description="遮罩颜色")
    cta_text: str | None = Field(None, description="主按钮文案（多语言 JSON）")
    cta_url: str | None = Field(None, max_length=500, description="主按钮链接")
    cta_secondary_text: str | None = Field(None, description="次按钮文案（多语言 JSON）")
    cta_secondary_url: str | None = Field(None, max_length=500, description="次按钮链接")
    text_align: TextAlign = Field(default="center", description="文字对齐")
    text_color: TextColor = Field(default="light", description="文字颜色主题")
    is_active: bool = Field(default=True, description="是否启用")
    sort_order: int = Field(default=0, ge=0, description="排序权重")
    start_time: datetime | None = Field(default=None, description="生效开始时间")
    end_time: datetime | None = Field(default=None, description="生效结束时间")


class HeroSlideCreate(HeroSlideBase):
    """创建 Hero 幻灯片"""

    # 只挂在写口，不挂 HeroSlideBase：HeroSlideResponse 继承 Base，挂在 Base 会让
    # `model_validate(ORM 行)` 也跑一遍——库里躺着历史脏值时公开口就从"渲染一条坏链接"
    # 变成整站 500。读侧的防线是前端 safeHeroHref 回落缺省，不是拒绝响应。
    @field_validator("cta_url", "cta_secondary_url", "poster_url")
    @classmethod
    def _reject_pseudo_scheme(cls, v: str | None) -> str | None:
        return _reject_pseudo_url_scheme(v)

    @model_validator(mode="after")
    def _check_media_pair(self) -> "HeroSlideCreate":
        error = validate_media_pair(self.media_type, self.media_url)
        if error:
            raise ValueError(error)
        return self

    @field_validator("start_time", "end_time")
    @classmethod
    def _fold_to_utc_instant(cls, v: datetime | None) -> datetime | None:
        """朴素值直接进 `DateTime(timezone=True)` 会被 PG 按会话时区解释（实测偏 8 小时）。

        口径与理由见 `backend/utils/compat.py::to_utc_instant`。
        """
        return to_utc_instant(v)


class HeroSlideUpdate(BaseModel):
    """更新 Hero 幻灯片"""

    title: str | None = None
    subtitle: str | None = None
    media_type: MediaType | None = None
    media_url: str | None = Field(None, min_length=1, max_length=500)
    poster_url: str | None = Field(None, max_length=500)
    overlay_opacity: int | None = Field(None, ge=0, le=100)
    overlay_color: str | None = Field(None, max_length=20)
    cta_text: str | None = None
    cta_url: str | None = Field(None, max_length=500)
    cta_secondary_text: str | None = None
    cta_secondary_url: str | None = Field(None, max_length=500)
    text_align: TextAlign | None = None
    text_color: TextColor | None = None
    is_active: bool | None = None
    sort_order: int | None = Field(None, ge=0)
    start_time: datetime | None = None
    end_time: datetime | None = None

    # 与 HeroSlideCreate 同口径：PUT 也必须挡伪协议，否则"创建时拦住、改一下就有"。
    @field_validator("cta_url", "cta_secondary_url", "poster_url")
    @classmethod
    def _reject_pseudo_scheme(cls, v: str | None) -> str | None:
        return _reject_pseudo_url_scheme(v)

    # PUT 是这条守卫唯一会漏的第二个写口：只改一侧时另一侧走 exclude_unset 不进模型，
    # 但提交的那一侧仍必须是折算过的瞬时。
    @field_validator("start_time", "end_time")
    @classmethod
    def _fold_to_utc_instant(cls, v: datetime | None) -> datetime | None:
        return to_utc_instant(v)


class HeroSlideResponse(HeroSlideBase):
    """Hero 幻灯片响应模型。

    下面这组字段刻意把写口的取值约束（`ge=` / `le=` / `Literal` / `max_length`）放宽成裸类型：
    响应模型会把 `hero_slides` 里**已有的行**直接序列化出去，而这张表可以被直连 SQL、
    早期版本或导 ZIP 写入。约束留在读侧，等于一条历史脏值把 `GET /api/hero/slides` 打成 500
    （2026-10-30 线上探针实测：`sort_order=-1000` 的行让整条公开口 500，首页横幅一起消失）。
    读侧的正确降级是"原值下发、前端按 `safeHeroHref` / 兜底图收口"，不是拒绝整份响应。
    与 `HeroSlideCreate` 上只挂写口的伪协议校验同一条口径。
    """

    media_type: str = Field(default="image", description="媒体类型")
    media_url: str = Field(..., description="媒体地址")
    poster_url: str | None = Field(None, description="视频封面图")
    overlay_opacity: int = Field(default=40, description="遮罩透明度 0-100")
    overlay_color: str = Field(default="#000000", description="遮罩颜色")
    cta_url: str | None = Field(None, description="主按钮链接")
    cta_secondary_url: str | None = Field(None, description="次按钮链接")
    text_align: str = Field(default="center", description="文字对齐")
    text_color: str = Field(default="light", description="文字颜色主题")
    sort_order: int = Field(default=0, description="排序权重")

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


from backend.schemas.strict_config import apply_strict_extra_forbid

apply_strict_extra_forbid(globals(), __name__)
