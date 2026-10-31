"""作者主页的邮箱展示面（批次 #147）：把 `show_email` 的第四段接上。

`show_email` 的写口（个人中心 → 偏好口）、存储（`UserPreference.show_email`，默认拒绝）、
投影（`apply_email_privacy` → `AuthorProfileResponse.email`）三段早就齐了，
唯独第四段空着：`/authors/<username>` 把 website / github 摊成链接，却从不读 email。
于是这个开关只能"关"不能"开"——作者主动选择公开邮箱，页面上什么都不会出现。

这里钉两条容易被后来者顺手改坏的东西：

1. **遮蔽值是 `***` 而不是 null**。`AuthorProfileResponse.email` 保持必填是有意的失败设计
   （服务层对"非本人 + 关了公开"返回的精简 dict 不含 email，隐私闸门一旦失守要 500
   而不是静默回 null）。把它"统一成隐藏即 null"看着整齐，实际是拆掉那道响亮失败——
   所以消费方的判据必须是"这一位不是掩码"，而不是"这一位非空"。
2. **消费方真的渲染了**。只有 helper 在遮、页面从不读，等于隐私开关是个哑按钮。
"""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api._user_response_helper import EMAIL_MASK
from backend.core.auth import get_password_hash
from backend.models.user import User, UserPreference


async def _author(db_session: AsyncSession, *, username: str, show_email: bool | None) -> User:
    user = User(
        username=username,
        email=f"{username}@example.invalid",
        password_hash=get_password_hash("Probe@12345"),
        nickname="邮箱面作者",
        is_active=True,
        is_staff=False,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.flush()
    if show_email is not None:
        db_session.add(UserPreference(user_id=user.id, public_profile=True, show_email=show_email))
    await db_session.commit()
    return user


class TestMaskIsNotNone:
    """闸门关掉时对外回的是掩码字符串——前端据此判隐藏，改成 null 会连带判据失真。"""

    async def test_both_profile_routes_return_the_mask(
        self, db_session: AsyncSession, client: AsyncClient
    ):
        author = await _author(db_session, username="maskauthor", show_email=False)
        for path in (f"/api/users/{author.id}", f"/api/users/username/{author.username}"):
            res = await client.get(path)
            assert res.status_code == 200, res.text
            body = res.json()
            assert body["email"] == EMAIL_MASK, path
            # 掩码必须是"非空但不是邮箱"：消费方若只判 v-if="email"，*** 会被当成公开邮箱。
            assert body["email"], path
            assert "@" not in body["email"], path

    async def test_missing_preference_row_defaults_to_masked(
        self, db_session: AsyncSession, client: AsyncClient
    ):
        """没有偏好行 = 模型默认拒绝，不得因为"读不到偏好"而放行明文。"""
        author = await _author(db_session, username="noPrefRowAuthor", show_email=None)
        row = (
            await db_session.execute(
                select(UserPreference).where(UserPreference.user_id == author.id)
            )
        ).scalar_one_or_none()
        assert row is None
        res = await client.get(f"/api/users/username/{author.username}")
        assert res.json()["email"] == EMAIL_MASK

    async def test_opt_in_projects_the_real_address(
        self, db_session: AsyncSession, client: AsyncClient
    ):
        """这一条就是批次 #147 的正面：作者开了开关，资料口必须给出真实地址。"""
        author = await _author(db_session, username="openmailauthor", show_email=True)
        res = await client.get(f"/api/users/username/{author.username}")
        assert res.json()["email"] == author.email


class TestConsumerSurface:
    """投影之后必须有人把它画出来，否则第四段仍是空的。"""

    def _page(self) -> str:
        from pathlib import Path

        return (
            Path(__file__).resolve().parents[1]
            / "frontend"
            / "pages"
            / "authors"
            / "[username].vue"
        ).read_text(encoding="utf-8")

    def test_page_reads_the_projected_field_and_renders_mailto(self):
        src = self._page()
        assert "email?: string | null" in src
        assert "const EMAIL_MASK = '***'" in src, "掩码判据必须与后端 EMAIL_MASK 同值"
        assert "if (!raw || raw === EMAIL_MASK) return ''" in src
        assert "`mailto:${publicEmail}`" in src
        start = src.index("<template>")
        end = src.rindex("</template>")
        tpl = src[start:end]
        assert 'v-if="publicEmail"' in tpl, "徽标必须在 template 区，不是 script 里算了没人用"
        assert "publicEmail" in tpl
        # 邮箱是库里来的字符串：不得进 v-html，也不得拼进非 mailto 的 scheme
        assert "v-html" not in tpl

    def test_social_row_also_opens_for_email_alone(self):
        """只有公开邮箱、没填网站/GitHub 的作者，这一行不能整段收起。"""
        src = self._page()
        assert "profile?.website || profile?.github || publicEmail" in src
