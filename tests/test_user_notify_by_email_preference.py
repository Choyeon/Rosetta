"""
个人偏好里「邮件通知」（``notify_by_email``）读写两端的守卫。

这一族此前的形状是**半接通**：`User.notify_by_email` 列存在、
`comment_service._fire_notifications_and_email` 真的按它筛选收件人（第 672 行
`select(User.email, User.notify_by_email)`），但偏好接口的请求模型不带这个键、
响应模型也不带、账号设置页没有对应开关。于是站点一旦配好 SMTP，
每个人都会收到评论/回复邮件而且**没有任何地方能关掉**——
这与"用户以为已关闭"相比更糟的是隐私面：唯一的真实强制点读的是一个没人能写的列。

四条口径必须钉住：
* 写口 PUT 必须把值落到 **User 行**（不在 `user_preferences` 表里，
  服务层那份从模型派生的白名单永远筛不出它，漏一处即成静默丢弃）。
* 读口 GET 必须回读 User 行的真值，不能让 Pydantic 默认值替它说话——
  默认 true 会让"已关闭"的用户刷新后看到开关又亮着。
* 匿名的公开隐私口（`/users/username/{u}/preferences`）**不得**摊出这一项。
* 未发送的键不得被顺手改写（exclude_unset 语义）。
"""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User, UserPreference
from backend.schemas import UserPreferenceResponse, UserPreferenceUpdate


async def _notify_flag(db: AsyncSession, user_id: int) -> bool:
    row = await db.execute(select(User.notify_by_email).where(User.id == user_id))
    return bool(row.scalar_one())


async def _pref_row(db: AsyncSession, user_id: int) -> UserPreference | None:
    row = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    return row.scalar_one_or_none()


class TestSchemaDeclaresTheSwitch:
    def test_both_preference_models_carry_it(self):
        assert "notify_by_email" in UserPreferenceUpdate.model_fields
        assert "notify_by_email" in UserPreferenceResponse.model_fields

    def test_response_default_matches_column_server_default(self):
        # 列是 server_default="true"；响应的兜底值必须同数，
        # 否则任何"忘记补值"的拼装口都会把已关闭的用户报成开启。
        default = UserPreferenceResponse.model_fields["notify_by_email"].default
        assert default is True


class TestWriteReadRoundTrip:
    async def test_get_reflects_the_user_row_not_the_schema_default(
        self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        test_user.notify_by_email = False
        await db_session.flush()

        resp = await client.get("/api/users/me/preferences", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["notify_by_email"] is False

    async def test_put_writes_the_user_row_and_echoes_it(
        self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        assert await _notify_flag(db_session, test_user.id) is True

        resp = await client.put(
            "/api/users/me/preferences", headers=auth_headers, json={"notify_by_email": False}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["notify_by_email"] is False
        # 响应回显不等于落库：必须直接读列
        assert await _notify_flag(db_session, test_user.id) is False

    async def test_toggle_back_on(
        self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        await client.put(
            "/api/users/me/preferences", headers=auth_headers, json={"notify_by_email": False}
        )
        resp = await client.put(
            "/api/users/me/preferences", headers=auth_headers, json={"notify_by_email": True}
        )
        assert resp.json()["notify_by_email"] is True
        assert await _notify_flag(db_session, test_user.id) is True

    async def test_sending_it_together_with_a_preference_column_persists_both(
        self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        resp = await client.put(
            "/api/users/me/preferences",
            headers=auth_headers,
            json={"show_email": True, "notify_by_email": False},
        )
        assert resp.status_code == 200, resp.text
        assert await _notify_flag(db_session, test_user.id) is False
        pref = await _pref_row(db_session, test_user.id)
        assert pref is not None and pref.show_email is True, "分流不得把偏好表的开关弄丢"

    async def test_omitting_it_leaves_the_row_untouched(
        self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        await client.put(
            "/api/users/me/preferences", headers=auth_headers, json={"notify_by_email": False}
        )
        resp = await client.put(
            "/api/users/me/preferences", headers=auth_headers, json={"show_posts": False}
        )
        assert resp.status_code == 200, resp.text
        assert await _notify_flag(db_session, test_user.id) is False, (
            "exclude_unset：没发送这一项就不能把它重置回默认值"
        )
        assert resp.json()["notify_by_email"] is False


class TestPublicProjectionDoesNotLeakIt:
    async def test_username_preferences_has_only_the_six_privacy_switches(
        self, client: AsyncClient, test_user: User
    ):
        """匿名可读口只摊 6 个"别人看得到"的开关；邮件通知是本人凭据相关的偏好。

        清单单源见 `tests/test_user_social_links_preference.py::PUBLIC_SWITCH_KEYS`。
        """
        from tests.test_user_social_links_preference import PUBLIC_SWITCH_KEYS

        resp = await client.get(f"/api/users/username/{test_user.username}/preferences")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert set(body) == PUBLIC_SWITCH_KEYS
        assert "notify_by_email" not in body

    def test_consumer_still_filters_recipients_by_the_column(self):
        """真实强制点必须还在读这一列——写口的意义全在这里。

        按文件文本读而不是 `inspect.getsource`：conftest 为了隔离测试把
        `_fire_notifications_and_email` 整个桩成了 noop，取到的会是桩的源码。
        """
        from pathlib import Path

        import backend.services.comment_service as comment_service_module

        source = Path(comment_service_module.__file__).read_text(encoding="utf-8")
        assert "select(User.email, User.notify_by_email)" in source
        assert "if notify and em" in source, "收件人筛选必须真的按这一列过滤，而不是只 SELECT 出来"
