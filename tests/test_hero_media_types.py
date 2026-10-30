"""首页轮播「媒体类型 ↔ 地址」两端回归（批次 #233）。

`media_type` 三档（image / video / youtube）与 `poster_url` 早已是列与 schema 的一部分，
但三处一直缺一段，表现是"后台存得进去、首页永远不播"：

- 后台表单把 `media_type` 写死成 `'image'`，运营者根本发不出另外两档；
- 首页读取侧有一条 `media_type === 'image'` 的过滤，非 image 的行被静默丢弃；
- CSP 没有 `frame-src`，`default-src 'self'` 会把所有 YouTube iframe 拦掉——即使前两处
  补齐，嵌入位仍然是一片空白。

本文件钉住判据本身（ID 解析 + 搭配校验）、两个写口（Create 的 schema 校验、PUT 的
"合并库里现值再判"）、公开口的响应字段，以及 CSP 两处声明（后端 `_build_csp` 与
nginx 的 HTML CSP，少一处就前后台策略分叉）。
前端渲染与后台表单由 `frontend/tests/unit/heroMedia.spec.ts` 等钉。
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import delete

from backend.core.database import async_session_maker
from backend.core.security_middleware import CSP_FRAME_SRCS, _build_csp
from backend.models.hero import HeroSlide
from backend.schemas.hero import (
    HeroSlideCreate,
    HeroSlideResponse,
    HeroSlideUpdate,
    extract_youtube_id,
    validate_media_pair,
)

ADMIN = "/api/admin/hero/slides"
PUBLIC = "/api/hero/slides"


def _unwrap(body):
    """两种形态都接：全局信封 ``{success, data}`` 与裸 list/dict。"""
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


YOUTUBE_GOOD = [
    ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("  dQw4w9WgXcQ  ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://youtube.com/watch?v=dQw4w9WgXcQ&t=42s", "dQw4w9WgXcQ"),
    ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ?si=abc", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/v/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
]

YOUTUBE_BAD = [
    None,
    "",
    "   ",
    "not-a-video-id",
    "dQw4w9WgXc",  # 10 位
    "dQw4w9WgXcQQ",  # 12 位
    "https://example.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch",  # 没有 v
    "https://www.youtube.com/watch?v=short",
    "https://vimeo.com/123456",
    "javascript:alert(1)",
    "https://evil.example/youtu.be/dQw4w9WgXcQ",
]


class TestExtractYoutubeId:
    @pytest.mark.parametrize("raw,expected", YOUTUBE_GOOD)
    def test_accepts_common_shapes(self, raw, expected):
        assert extract_youtube_id(raw) == expected

    @pytest.mark.parametrize("raw", YOUTUBE_BAD)
    def test_rejects_unusable(self, raw):
        assert extract_youtube_id(raw) is None


class TestValidateMediaPair:
    @pytest.mark.parametrize("raw,_", YOUTUBE_GOOD)
    def test_youtube_accepts_parsable(self, raw, _):
        assert validate_media_pair("youtube", raw) is None

    @pytest.mark.parametrize("raw", YOUTUBE_BAD)
    def test_youtube_rejects_unparsable(self, raw):
        assert validate_media_pair("youtube", raw) is not None

    @pytest.mark.parametrize("url", ["/media/2026/01/hero.mp4", "/media/a.webm"])
    def test_video_accepts_site_relative(self, url):
        assert validate_media_pair("video", url) is None

    @pytest.mark.parametrize(
        "url",
        [
            "https://cdn.example.com/hero.mp4",
            "http://cdn.example.com/hero.mp4",
            "//cdn.example.com/hero.mp4",  # 协议相对：同样逃出 media-src 'self'
            "media/hero.mp4",  # 相对路径会被拼到当前页路径下，不是站内媒体口的地址
            "",
            None,
        ],
    )
    def test_video_rejects_external_or_empty(self, url):
        assert validate_media_pair("video", url) is not None

    @pytest.mark.parametrize(
        "url", ["https://img.example.com/a.jpg", "/media/a.jpg", "data:image/gif;base64,AA"]
    )
    def test_image_only_requires_non_empty(self, url):
        assert validate_media_pair("image", url) is None

    def test_every_type_rejects_empty(self):
        for media_type in ("image", "video", "youtube"):
            assert validate_media_pair(media_type, "  ") is not None


class TestCreateWritePath:
    async def test_youtube_slide_persists_media_type_and_poster(
        self, client: AsyncClient, admin_headers
    ):
        resp = await client.post(
            ADMIN,
            headers=admin_headers,
            json={
                "media_type": "youtube",
                "media_url": "https://youtu.be/dQw4w9WgXcQ",
                "poster_url": "/media/hero-poster.jpg",
            },
        )
        assert resp.status_code == 201, resp.text
        data = _unwrap(resp.json())
        assert data["media_type"] == "youtube"
        assert data["media_url"] == "https://youtu.be/dQw4w9WgXcQ"
        assert data["poster_url"] == "/media/hero-poster.jpg"

    @pytest.mark.parametrize(
        "payload",
        [
            {"media_type": "youtube", "media_url": "https://example.com/watch?v=dQw4w9WgXcQ"},
            {"media_type": "youtube", "media_url": "not-an-id"},
            {"media_type": "video", "media_url": "https://cdn.example.com/hero.mp4"},
            {"media_type": "video", "media_url": "//cdn.example.com/hero.mp4"},
        ],
    )
    async def test_create_rejects_mismatched_pair(
        self, client: AsyncClient, admin_headers, payload
    ):
        resp = await client.post(ADMIN, headers=admin_headers, json=payload)
        assert resp.status_code == 422, resp.text

    async def test_video_slide_accepts_site_path(self, client: AsyncClient, admin_headers):
        resp = await client.post(
            ADMIN,
            headers=admin_headers,
            json={"media_type": "video", "media_url": "/media/2026/01/hero.mp4"},
        )
        assert resp.status_code == 201, resp.text
        assert _unwrap(resp.json())["media_type"] == "video"

    def test_schema_declares_both_fields(self):
        for model in (HeroSlideCreate, HeroSlideUpdate):
            assert "media_type" in model.model_fields
            assert "poster_url" in model.model_fields


class TestUpdateMergesStoredSide:
    """PUT 是 `exclude_unset` 增量更新：schema 只看得到本次提交的那半边。

    不合并现值就等于"创建时拦住、改一下就有"——这条是 #233 里最容易漏的第二个写口。
    """

    async def _create(self, client: AsyncClient, admin_headers, **payload) -> int:
        resp = await client.post(ADMIN, headers=admin_headers, json=payload)
        assert resp.status_code == 201, resp.text
        return int(_unwrap(resp.json())["id"])

    async def test_switching_type_to_youtube_with_bad_stored_url_is_rejected(
        self, client: AsyncClient, admin_headers
    ):
        slide_id = await self._create(
            client, admin_headers, media_type="image", media_url="https://img.example.com/a.jpg"
        )
        resp = await client.put(
            f"{ADMIN}/{slide_id}", headers=admin_headers, json={"media_type": "youtube"}
        )
        assert resp.status_code == 422, resp.text

    async def test_switching_type_to_youtube_with_good_url_passes(
        self, client: AsyncClient, admin_headers
    ):
        slide_id = await self._create(
            client, admin_headers, media_type="image", media_url="https://img.example.com/a.jpg"
        )
        resp = await client.put(
            f"{ADMIN}/{slide_id}",
            headers=admin_headers,
            json={
                "media_type": "youtube",
                "media_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "poster_url": "/media/poster.jpg",
            },
        )
        assert resp.status_code == 200, resp.text
        data = _unwrap(resp.json())
        assert data["media_type"] == "youtube"
        assert data["poster_url"] == "/media/poster.jpg"

    async def test_changing_only_url_on_a_video_slide_is_checked(
        self, client: AsyncClient, admin_headers
    ):
        slide_id = await self._create(
            client, admin_headers, media_type="video", media_url="/media/2026/01/hero.mp4"
        )
        resp = await client.put(
            f"{ADMIN}/{slide_id}",
            headers=admin_headers,
            json={"media_url": "https://cdn.example.com/other.mp4"},
        )
        assert resp.status_code == 422, resp.text

    async def test_poster_can_be_cleared_with_explicit_null(
        self, client: AsyncClient, admin_headers
    ):
        slide_id = await self._create(
            client,
            admin_headers,
            media_type="video",
            media_url="/media/2026/01/hero.mp4",
            poster_url="/media/poster.jpg",
        )
        resp = await client.put(
            f"{ADMIN}/{slide_id}", headers=admin_headers, json={"poster_url": None}
        )
        assert resp.status_code == 200, resp.text
        assert _unwrap(resp.json())["poster_url"] is None


class TestPublicSurface:
    async def test_public_endpoint_emits_all_three_types(self, client: AsyncClient, admin_headers):
        created = []
        for payload in (
            {"media_type": "image", "media_url": "https://img.example.com/a.jpg"},
            {
                "media_type": "video",
                "media_url": "/media/2026/01/hero.mp4",
                "poster_url": "/media/poster.jpg",
            },
            {
                "media_type": "youtube",
                "media_url": "https://youtu.be/dQw4w9WgXcQ",
                "poster_url": "/media/yt-poster.jpg",
            },
        ):
            resp = await client.post(ADMIN, headers=admin_headers, json=payload)
            assert resp.status_code == 201, resp.text
            created.append(int(_unwrap(resp.json())["id"]))

        resp = await client.get(PUBLIC)
        assert resp.status_code == 200, resp.text
        rows = {item["id"]: item for item in _unwrap(resp.json())}

        # 三档都必须下发（旧实现里前端会再过滤掉非 image，这里钉的是后端不吞）
        for slide_id in created:
            assert slide_id in rows, f"公开口吞掉了 {slide_id}"
        types = {rows[slide_id]["media_type"] for slide_id in created}
        assert types == {"image", "video", "youtube"}

        video = rows[created[1]]
        assert video["poster_url"] == "/media/poster.jpg"


class TestPublicReadPathToleratesStoredValues:
    """公开读口不得因为库里一条历史脏值整条 500（批次 #233 线上探针踩到）。

    `HeroSlideResponse` 会把 `hero_slides` 已有的行原样序列化出去，而这张表可以被直连 SQL、
    早期版本或导 ZIP 写入。取值约束（`ge=` / `Literal` / `max_length`）因此只挂在写口，
    读侧只声明类型——线上实测：`sort_order=-1000` 的行让 `GET /api/hero/slides` 回 500，
    首页横幅与轮播整个消失，而库里那一行本身并没有任何非法之处。
    """

    NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)

    def _row(self, **overrides) -> dict:
        return {
            "id": 1,
            "media_type": "image",
            "media_url": "/media/x.jpg",
            "created_at": self.NOW,
            "updated_at": self.NOW,
            **overrides,
        }

    @pytest.mark.parametrize(
        "field,value",
        [
            ("sort_order", -1000),
            ("overlay_opacity", 140),
            ("overlay_opacity", -5),
            ("media_type", "vimeo"),
            ("text_align", "justify"),
            ("text_color", "sepia"),
            ("media_url", ""),
            ("media_url", "https://cdn.example.com/" + "a" * 600),
            ("poster_url", "https://cdn.example.com/" + "b" * 600),
        ],
    )
    def test_response_model_accepts_stored_values(self, field, value):
        model = HeroSlideResponse.model_validate(self._row(**{field: value}))
        assert getattr(model, field) == value

    @pytest.mark.parametrize(
        "payload",
        [
            {"media_url": "/media/x.jpg", "sort_order": -1},
            {"media_url": "/media/x.jpg", "overlay_opacity": 101},
            {"media_url": "/media/x.jpg", "overlay_opacity": -1},
            {"media_url": "/media/x.jpg", "media_type": "vimeo"},
            {"media_url": "/media/x.jpg", "text_align": "justify"},
            {"media_url": "/media/x.jpg", "text_color": "sepia"},
            {"media_url": ""},
            {"media_url": "/media/x.jpg", "poster_url": "https://cdn.example.com/" + "b" * 600},
        ],
    )
    def test_write_schemas_still_reject_them(self, payload):
        """放宽的只有读侧：写口的 422 一条都不能少，否则脏值又会从接口进来。"""
        with pytest.raises(ValidationError):
            HeroSlideCreate(**payload)

    async def test_public_endpoint_survives_a_dirty_stored_row(self, client: AsyncClient):
        async with async_session_maker() as db:
            row = HeroSlide(
                title="dirty-slide",
                media_type="vimeo",
                media_url="",
                overlay_opacity=140,
                text_align="justify",
                text_color="sepia",
                is_active=True,
                sort_order=-7,
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            slide_id = row.id
        try:
            resp = await client.get(PUBLIC)
            assert resp.status_code == 200, resp.text
            assert slide_id in {item["id"] for item in _unwrap(resp.json())}
        finally:
            async with async_session_maker() as db:
                await db.execute(delete(HeroSlide).where(HeroSlide.id == slide_id))
                await db.commit()

    def test_response_redeclares_every_constrained_field(self):
        """将来给 Base 新增 `ge=` / `Literal` 字段时，读侧要同批放宽（否则 500 面又长回来）。"""
        constrained = {
            name for name, field in HeroSlideResponse.model_fields.items() if field.metadata
        }
        assert constrained == set(), f"响应模型仍带取值约束：{sorted(constrained)}"


class TestContentSecurityPolicy:
    """iframe 能不能加载由 CSP 决定，而这条策略有两份声明，少一处就分叉。"""

    def test_backend_csp_declares_frame_src(self):
        csp = _build_csp("probe-nonce")
        assert f"frame-src {CSP_FRAME_SRCS}" in csp
        assert "https://www.youtube-nocookie.com" in csp
        # 顺带钉住"不连通用 youtube 域"：嵌入地址由前端固定拼 nocookie
        assert "https://www.youtube.com" not in csp
        assert "https://youtube.com" not in csp

    def test_nginx_html_csp_mirrors_it(self):
        conf = Path(__file__).resolve().parents[1] / "deploy" / "nginx-site.conf"
        html = conf.read_text(encoding="utf-8")
        assert f"frame-src {CSP_FRAME_SRCS};" in html, (
            "deploy/nginx-site.conf 的 HTML CSP 与后端 _build_csp 必须同口径："
            "HTML 页面走 nginx 那一份，漏改的表现是后台/前台 iframe 被浏览器拦掉"
        )
