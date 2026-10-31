"""文章级音视频（``audio`` / ``video`` / ``video_url``）四段接通的回归测试。

这一族此前的形状是「只有列」：``Post`` 上有三个 ``String(500)``，但 ``PostCreate`` /
``PostUpdate`` 不收、创建端点不传、详情响应模型不带、后台编辑器没有格子、前台详情页
没有播放器——等于三个永远为空的死列。本文件钉住接通之后的六条口径：

1. **写口落值**：POST 创建与 PUT 更新提交的三个地址，下一次 GET 必须读得到（四段里
   「写口 → 存储」这一段最容易漏，创建端点是手写 ``Post(...)`` 显式列清单）。
2. **站内路径判据（CSP 驱动）**：``audio`` / ``video`` 只接受站内路径。CSP 的
   ``media-src`` 是 ``'self' blob: data:``，外链会被浏览器拦成空白播放器，而接口一个错
   都不报——所以必须在写口就拒，两个写口都要拒。
3. **嵌入地址只认 YouTube ID**：渲染侧用解析出的 ID 拼 ``youtube-nocookie.com/embed/<id>``
   （``frame-src`` 只放这一个域），绝不把库里的原始串拼进 ``iframe src``。
4. **空串 = 清掉**（``exclude_unset`` 语义下"省略键"是"不动它"，删掉音轨必须发显式空值）。
5. **约束只挂写口**：响应模型把同三个字段重新声明成裸 ``str | None``。库里躺着外链
   （导入 ZIP / 直连 SQL）时读口必须仍回 200，由消费方决定不渲染，而不是整条详情 500。
6. **密码档**：正文没解锁时这三列一起投影成 null——音频/视频常直接引用正文内容，
   留在响应里等于绕过闸门。
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import cache
from backend.models.blog import Category, Post
from backend.models.user import User
from backend.schemas import (
    PostCreate,
    PostEditResponse,
    PostLocalizedResponse,
    PostResponse,
    PostUpdate,
)

GUARDED_PASSWORD_HASH = "$argon2id$fake.placeholder.hash"
GOOD_AUDIO = "/media/2026/03/podcast.mp3"
GOOD_VIDEO = "/media/2026/03/clip.mp4"
GOOD_EMBED = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
GOOD_EMBED_ID = "dQw4w9WgXcQ"


def _payload(body: dict) -> dict:
    if isinstance(body, dict) and "data" in body and "success" in body:
        return body["data"] or {}
    return body or {}


async def _post_with_media(
    db_session: AsyncSession,
    test_user: User,
    test_category: Category,
    *,
    slug: str = "media-probe",
    password: str | None = None,
    audio: str | None = GOOD_AUDIO,
    video: str | None = GOOD_VIDEO,
    video_url: str | None = GOOD_EMBED,
) -> Post:
    post = Post(
        title={"zh": "带音视频的文章", "en": "Post With Media"},
        slug=slug,
        content={"zh": "正文内容", "en": "body text"},
        excerpt={"zh": "摘要", "en": "excerpt"},
        author_id=test_user.id,
        category_id=test_category.id,
        status="published",
        visibility="password" if password else "public",
        password=password,
        audio=audio,
        video=video,
        video_url=video_url,
        allow_comments=True,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


class TestWriterSide:
    """创建与更新真的把三列写进库，并且回吐给同一次响应。"""

    @pytest.mark.asyncio
    async def test_create_persists_all_three_and_echoes_them(
        self, client: AsyncClient, admin_headers: dict
    ):
        response = await client.post(
            "/api/blog/posts",
            headers=admin_headers,
            json={
                "title": {"zh": "新建带音视频", "en": "Created With Media"},
                "slug": "media-created",
                "content": {"zh": "正文", "en": "body"},
                "status": "published",
                "audio": GOOD_AUDIO,
                "video": GOOD_VIDEO,
                "video_url": GOOD_EMBED,
            },
        )
        assert response.status_code == 201, response.text
        data = _payload(response.json())
        assert data["audio"] == GOOD_AUDIO
        assert data["video"] == GOOD_VIDEO
        assert data["video_url"] == GOOD_EMBED

        await cache.clear()
        detail = _payload((await client.get("/api/blog/posts/media-created")).json())
        assert detail["audio"] == GOOD_AUDIO
        assert detail["video"] == GOOD_VIDEO
        assert detail["video_url"] == GOOD_EMBED

    @pytest.mark.asyncio
    async def test_update_rewrites_and_clears_with_empty_string(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
        test_user: User,
        test_category: Category,
    ):
        """空串必须清掉：省略键是「不动它」，删掉音轨只有显式发空值才落得了库。"""
        post = await _post_with_media(db_session, test_user, test_category, slug="media-put")

        rewritten = await client.put(
            f"/api/blog/posts/{post.id}",
            headers=admin_headers,
            json={"audio": "/media/2026/04/other.mp3"},
        )
        assert rewritten.status_code == 200, rewritten.text
        await cache.clear()
        after = _payload((await client.get(f"/api/blog/posts/{post.slug}")).json())
        assert after["audio"] == "/media/2026/04/other.mp3"
        assert after["video"] == GOOD_VIDEO, "只改 audio 不得连带抹掉另两列"

        cleared = await client.put(
            f"/api/blog/posts/{post.id}",
            headers=admin_headers,
            json={"audio": "", "video": "", "video_url": ""},
        )
        assert cleared.status_code == 200, cleared.text
        await cache.clear()
        blank = _payload((await client.get(f"/api/blog/posts/{post.slug}")).json())
        assert blank["audio"] is None
        assert blank["video"] is None
        assert blank["video_url"] is None

    @pytest.mark.asyncio
    async def test_omitted_keys_leave_values_untouched(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
        test_user: User,
        test_category: Category,
    ):
        """exclude_unset 的正向半边：改标题不该顺手清掉音轨。"""
        post = await _post_with_media(db_session, test_user, test_category, slug="media-omit")
        response = await client.put(
            f"/api/blog/posts/{post.id}",
            headers=admin_headers,
            json={"title": {"zh": "只改标题", "en": "Title Only"}},
        )
        assert response.status_code == 200, response.text
        await cache.clear()
        detail = _payload((await client.get(f"/api/blog/posts/{post.slug}")).json())
        assert detail["audio"] == GOOD_AUDIO
        assert detail["video"] == GOOD_VIDEO
        assert detail["video_url"] == GOOD_EMBED

    @pytest.mark.asyncio
    async def test_edit_endpoint_returns_media_for_backfill(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
        test_user: User,
        test_category: Category,
    ):
        """编辑器回填的唯一取数口：不回填则每次 PUT 把三列提交成空串。"""
        post = await _post_with_media(db_session, test_user, test_category, slug="media-edit")
        response = await client.get(f"/api/blog/posts/{post.id}/edit", headers=admin_headers)
        assert response.status_code == 200, response.text
        data = _payload(response.json())
        assert data["audio"] == GOOD_AUDIO
        assert data["video"] == GOOD_VIDEO
        assert data["video_url"] == GOOD_EMBED


class TestMediaSchemeRules:
    """两个写口同一条判据：站内路径 + 可解析出 ID 的 YouTube 地址。"""

    @pytest.mark.parametrize("field", ["audio", "video"])
    @pytest.mark.parametrize(
        "bad",
        [
            "https://evil.example/x.mp4",
            "http://cdn.example.com/a.mp3",
            "//cdn.example.com/a.mp4",  # 协议相对也是外链
            "media/x.mp4",  # 相对当前目录，不是站内绝对路径
        ],
    )
    def test_internal_only_fields_reject_non_site_paths(self, field: str, bad: str):
        with pytest.raises(ValueError, match="站内路径"):
            PostCreate(title={"zh": "t"}, content={"zh": "c"}, slug="s", **{field: bad})
        with pytest.raises(ValueError, match="站内路径"):
            PostUpdate(**{field: bad})

    @pytest.mark.parametrize("field", ["audio", "video"])
    @pytest.mark.parametrize("bad", ["javascript:alert(1)", "data:text/html,<script>1</script>"])
    def test_internal_only_fields_reject_executable_schemes(self, field: str, bad: str):
        """伪协议由第三档先拦（文案不同，但都是"这个值不能进库"），不得退化成站内相对路径。"""
        with pytest.raises(ValueError):
            PostUpdate(**{field: bad})

    @pytest.mark.parametrize("field", ["audio", "video"])
    @pytest.mark.parametrize("good", [GOOD_AUDIO, GOOD_VIDEO, "/media/a.webm", "  /media/a.mp3  "])
    def test_internal_only_fields_accept_site_paths(self, field: str, good: str):
        model = PostUpdate(**{field: good})
        assert getattr(model, field).startswith("/media/")

    @pytest.mark.parametrize("field", ["audio", "video"])
    def test_blank_clears_rather_than_rejects(self, field: str):
        """空串与纯空白都是「清掉」的合法写法，不是格式错误。"""
        assert getattr(PostUpdate(**{field: ""}), field) is None
        assert getattr(PostUpdate(**{field: "   "}), field) is None

    @pytest.mark.parametrize(
        "good",
        [
            GOOD_EMBED,
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        ],
    )
    def test_embed_accepts_youtube_forms(self, good: str):
        assert PostUpdate(video_url=good).video_url == good

    @pytest.mark.parametrize(
        "bad",
        [
            "https://player.bilibili.com/player.html?aid=1",
            "https://evil.example/youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/watch",  # 解析不出 ID
            "/media/clip.mp4",
            "javascript:alert(1)",
        ],
    )
    def test_embed_rejects_anything_without_a_youtube_id(self, bad: str):
        with pytest.raises(ValueError, match="YouTube"):
            PostUpdate(video_url=bad)
        with pytest.raises(ValueError, match="YouTube"):
            PostCreate(title={"zh": "t"}, content={"zh": "c"}, slug="s", video_url=bad)

    @pytest.mark.asyncio
    async def test_create_endpoint_returns_422_for_external_audio(
        self, client: AsyncClient, admin_headers: dict
    ):
        response = await client.post(
            "/api/blog/posts",
            headers=admin_headers,
            json={
                "title": {"zh": "外链音频", "en": "External Audio"},
                "slug": "media-bad-create",
                "content": {"zh": "正文", "en": "body"},
                "audio": "https://evil.example/x.mp3",
            },
        )
        assert response.status_code == 422, response.text

    @pytest.mark.asyncio
    async def test_update_endpoint_returns_422_for_bad_embed(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
        test_user: User,
        test_category: Category,
    ):
        """两个写口都要拦：创建拦得住、改一下就有＝首页播放器变成空白。"""
        post = await _post_with_media(db_session, test_user, test_category, slug="media-bad-put")
        response = await client.put(
            f"/api/blog/posts/{post.id}",
            headers=admin_headers,
            json={"video_url": "https://evil.example/embed"},
        )
        assert response.status_code == 422, response.text
        await cache.clear()
        detail = _payload((await client.get(f"/api/blog/posts/{post.slug}")).json())
        assert detail["video_url"] == GOOD_EMBED, "被拒的请求不得改动库里现值"


class TestReadSideToleratesStoredValues:
    """约束只挂写口：脏值读得出、不 500，渲染判据交给消费方。"""

    @pytest.mark.asyncio
    async def test_detail_returns_200_for_external_urls_stored_directly(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        """导入工具与直连 SQL 能塞进任意地址；响应模型再校验一次＝整条详情口 500。"""
        await _post_with_media(
            db_session,
            test_user,
            test_category,
            slug="media-dirty",
            audio="https://evil.example/x.mp3",
            video="//cdn.example.com/a.mp4",
            video_url="https://evil.example/youtu.be/dQw4w9WgXcQ",
        )
        await cache.clear()
        response = await client.get("/api/blog/posts/media-dirty")
        assert response.status_code == 200, response.text
        data = _payload(response.json())
        # 原样回吐（不在读侧改写），前端 lib/post-media 判不合规就不渲染播放器
        assert data["audio"] == "https://evil.example/x.mp3"
        assert data["video_url"] == "https://evil.example/youtu.be/dQw4w9WgXcQ"

    @pytest.mark.parametrize(
        "model", [PostResponse, PostEditResponse, PostLocalizedResponse], ids=lambda m: m.__name__
    )
    def test_response_models_carry_no_write_constraints(self, model):
        for field in ("audio", "video", "video_url"):
            info = model.model_fields[field]
            assert info.metadata == [], (
                f"{model.__name__}.{field} 带了写口约束，脏值会把读口打成 500"
            )

    def test_write_models_declare_the_three_fields(self):
        for model in (PostCreate, PostUpdate):
            for field in ("audio", "video", "video_url"):
                assert field in model.model_fields


class TestPasswordGateHidesMedia:
    """音频/视频常直接引用正文内容：正文没解锁，这三列必须一起收起。"""

    @pytest.mark.asyncio
    async def test_locked_post_projects_media_as_null(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        post = await _post_with_media(
            db_session,
            test_user,
            test_category,
            slug="media-locked",
            password=GUARDED_PASSWORD_HASH,
        )
        await cache.clear()
        response = await client.get(f"/api/blog/posts/{post.slug}")
        assert response.status_code == 200
        data = _payload(response.json())
        assert data["is_password_protected"] is True
        assert not data["content"]
        assert data["audio"] is None
        assert data["video"] is None
        assert data["video_url"] is None
        assert GOOD_AUDIO not in response.text
        assert GOOD_EMBED_ID not in response.text

    @pytest.mark.asyncio
    async def test_by_id_detail_hides_media_too(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        """两条详情口同口径（按 ID 那条曾只给提示不给判据）。"""
        post = await _post_with_media(
            db_session,
            test_user,
            test_category,
            slug="media-locked-by-id",
            password=GUARDED_PASSWORD_HASH,
        )
        await cache.clear()
        data = _payload((await client.get(f"/api/blog/posts/id/{post.id}")).json())
        assert data["audio"] is None
        assert data["video_url"] is None
