"""私信 / 通知 / 收藏 / 监控四个"私密读面"的回归。

四类缺陷同属一族：**边界条件写在了子查询里，却没写进真正决定返回行的那一层**。
1. 会话列表按「每个对端一行」聚合，锚点原先是 ``created_at`` 相等，而外层查询没有
   ``between_us`` 条件——第三方会话只要时间戳撞在一起（SQLite 只到秒、PG 同事务
   必然相同），它的正文与对端资料就被当成"我的最近消息"返回，同一对端还会出多行。
2. 发私信把正文放在 query string：正文整条进 nginx 访问日志，长消息顶破请求头。
3. 通知 WebSocket 只做 ``decode_token``（验签名+过期），不判 ``type``、不查用户状态，
   长效 refresh 令牌与被封禁用户的令牌照样能挂进连接表收推送；顺带修掉
   ``manager.connect`` 未 await（协程从未执行 ⇒ 连接根本没登记）与二次 accept。
4. 收藏列表的 total 用未筛选的计数，按 folder 过滤时宣称的页数拉不出内容。
5. 监控 error_rate 的分子按状态码全量统计、分母却只数 ``response_time_ms > 0`` 的样本，
   亚毫秒错误（429/401 落库为 0）在分母外，比例能报过 100%。
6. 标记单条私信已读用 403 区分「存在但不是你的」——私信主键连续自增，这等于让攻击者
   逐 id 数出站内外私信的存在性；同族（收藏、通知）本就一律 404，这里是最后一个缺口。
"""

from datetime import datetime, timedelta

import pytest
from fastapi import WebSocketDisconnect
from sqlalchemy import select

from backend.api.favorite import Favorite, FavoriteFolder
from backend.api.notification import manager, websocket_notifications
from backend.api.notification import router as notification_router
from backend.core.auth import create_access_token, create_refresh_token, get_password_hash
from backend.models.message import PrivateMessage
from backend.models.monitoring import VisitLog
from backend.models.user import User
from backend.utils.compat import UTC


@pytest.fixture
async def other_users(db_session):
    """会话/推送之外的角色：friend（我的对端）、stranger（与 friend 有同秒会话）、以及建用户工厂。"""

    async def _mk(username: str, *, banned: bool = False) -> User:
        user = User(
            username=username,
            email=f"{username}@peers.test",
            password_hash=get_password_hash("P@ssw0rd!"),
            nickname=username,
            is_active=True,
            is_banned=banned,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    friend = await _mk("peer_friend")
    stranger = await _mk("peer_stranger")
    return friend, stranger, _mk


async def _add_message(db_session, sender: User, recipient: User, content: str, at: datetime):
    db_session.add(
        PrivateMessage(
            sender_id=sender.id,
            recipient_id=recipient.id,
            content=content,
            created_at=at,
        )
    )
    await db_session.commit()


class TestConversationScopeIsPerPeer:
    @pytest.mark.asyncio
    async def test_third_party_message_never_shows_as_mine(
        self, client, auth_headers, test_user, db_session, other_users
    ):
        """同秒的第三方会话行不得挤进我的列表（旧实现：外层 join 无 between_us 条件）。

        对端「朋友」在同一个时间戳里还给陌生人发过一条消息。按旧实现，那条消息
        的 ``other_id_expr``（我不在其间 ⇒ 取 sender_id）正好等于我会话行的
        ``other_id``，时间戳也相等，于是它被当成「我和朋友的最后一条消息」返回——
        第三方正文泄漏 + 同一对端重复成两行。
        """
        friend, stranger, _ = other_users
        same_second = datetime.now(UTC).replace(microsecond=0)

        await _add_message(db_session, test_user, friend, "我和朋友的对话", same_second)
        await _add_message(db_session, friend, stranger, "第三方私密正文", same_second)

        resp = await client.get("/api/messages/conversations", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        contents = [item["last_message"]["content"] for item in body["items"]]
        assert contents == ["我和朋友的对话"]
        assert body["total"] == 1

    @pytest.mark.asyncio
    async def test_one_row_per_peer_even_on_timestamp_tie(
        self, client, auth_headers, test_user, db_session, other_users
    ):
        """同一对端的多条同秒消息只出一行，且取最后写入的那条。"""
        friend, _, _ = other_users
        same_second = datetime.now(UTC).replace(microsecond=0)

        await _add_message(db_session, test_user, friend, "第一条", same_second)
        await _add_message(db_session, friend, test_user, "第二条", same_second)

        resp = await client.get("/api/messages/conversations", headers=auth_headers)
        body = resp.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["last_message"]["content"] == "第二条"


class TestSendMessageUsesRequestBody:
    @pytest.mark.asyncio
    async def test_send_accepts_json_body(self, client, auth_headers, other_users):
        friend, _, _ = other_users
        resp = await client.post(
            "/api/messages",
            headers=auth_headers,
            json={"recipient_id": friend.id, "content": "走请求体的正文"},
        )
        assert resp.status_code == 201
        assert resp.json()["content"] == "走请求体的正文"

    @pytest.mark.asyncio
    async def test_query_string_transport_is_rejected(self, client, auth_headers, other_users):
        """正文不再可能走 URL：旧调用方式必须 422，而不是被收下并写进访问日志。"""
        friend, _, _ = other_users
        resp = await client.post(
            "/api/messages",
            headers=auth_headers,
            params={"recipient_id": friend.id, "content": "不该出现在请求行里的正文"},
        )
        assert resp.status_code == 422


class TestMarkReadDoesNotConfirmExistence:
    @pytest.mark.asyncio
    async def test_foreign_message_id_is_404_not_403(
        self, client, auth_headers, db_session, other_users
    ):
        """别人的私信 id 一律 404。

        私信主键连续自增，403「存在但不是你的」与 404「不存在」可区分，攻击者就能
        逐 id 数出站内外私信的总量；收藏与通知同族已经是 404，这里补齐最后一个缺口。
        """
        friend, stranger, _ = other_users
        await _add_message(
            db_session, stranger, friend, "别人之间的私信", datetime.now(UTC).replace(microsecond=0)
        )
        foreign_id = (
            await db_session.scalar(
                select(PrivateMessage.id).where(PrivateMessage.recipient_id == friend.id)
            )
            or 0
        )
        assert foreign_id

        resp = await client.put(f"/api/messages/{foreign_id}/read", headers=auth_headers)
        assert resp.status_code == 404

        # 404 之外还要证明"没有顺手改掉别人的数据"。取列而不是对象：本会话的 identity
        # map 里已有这行，拿实例读属性可能是提交前的旧值，列级 SELECT 才会真读库。
        is_read = await db_session.scalar(
            select(PrivateMessage.is_read).where(PrivateMessage.id == foreign_id)
        )
        assert is_read is False


class _StubSocket:
    """最小 WebSocket 替身：够跑 auth/ping 分支，不需要真实 ASGI 传输。"""

    def __init__(self, inbound: list[dict]):
        self._inbound = list(inbound)
        self.accepted = False
        self.sent: list[dict] = []

    async def accept(self):
        self.accepted = True

    async def receive_json(self):
        if not self._inbound:
            raise WebSocketDisconnect
        return self._inbound.pop(0)

    async def send_json(self, payload: dict):
        self.sent.append(payload)


async def _run_socket(inbound: list[dict], db_session) -> _StubSocket:
    socket = _StubSocket(inbound)
    await websocket_notifications(socket, db_session)  # type: ignore[arg-type]
    return socket


class TestNotificationWebSocketCredentials:
    @pytest.mark.asyncio
    async def test_access_token_registers_the_connection(self, test_user, db_session, monkeypatch):
        seen: list[tuple[int, list[object]]] = []
        original_connect = manager.connect

        async def spy(websocket, user_id):
            await original_connect(websocket, user_id)
            seen.append((user_id, list(manager.active_connections.get(user_id, []))))

        monkeypatch.setattr(manager, "connect", spy)

        socket = await _run_socket(
            [
                {"type": "auth", "token": create_access_token({"sub": str(test_user.id)})},
                {"type": "ping"},
            ],
            db_session,
        )
        assert socket.accepted is True
        assert socket.sent[0] == {"type": "auth", "status": "success"}
        assert socket.sent[1] == {"type": "pong"}
        # 连接真的登记进了管理器：旧实现漏 await，协程从未执行，seen 恒空
        assert seen == [(test_user.id, [socket])]
        # 断开时对称摘除，不留僵尸连接
        assert test_user.id not in manager.active_connections

    @pytest.mark.asyncio
    async def test_refresh_token_is_rejected(self, test_user, db_session):
        token, _ = create_refresh_token({"sub": str(test_user.id)})
        socket = await _run_socket([{"type": "auth", "token": token}], db_session)
        assert socket.sent[0] == {"type": "auth", "status": "error"}
        assert test_user.id not in manager.active_connections

    @pytest.mark.asyncio
    async def test_banned_user_access_token_is_rejected(self, db_session, other_users):
        _, _, mk = other_users
        banned = await mk("peer_banned", banned=True)
        socket = await _run_socket(
            [{"type": "auth", "token": create_access_token({"sub": str(banned.id)})}], db_session
        )
        assert socket.sent[0] == {"type": "auth", "status": "error"}
        assert banned.id not in manager.active_connections

    @pytest.mark.asyncio
    async def test_ws_route_still_mounted(self):
        """WS 入口仍在通知路由上（防止改鉴权时把整条路由删掉）。"""
        assert any(getattr(route, "path", "") == "/ws" for route in notification_router.routes)


class TestFavoriteCountMatchesFilter:
    @pytest.mark.asyncio
    async def test_total_follows_folder_filter(
        self, client, auth_headers, test_user, test_post, db_session
    ):
        folder = FavoriteFolder(user_id=test_user.id, name="只看这一夹")
        db_session.add(folder)
        await db_session.commit()
        await db_session.refresh(folder)

        for offset in range(3):
            db_session.add(
                Favorite(
                    user_id=test_user.id,
                    post_id=test_post.id,
                    folder_id=folder.id if offset < 2 else None,
                    note=f"n{offset}",
                )
            )
        await db_session.commit()

        resp = await client.get(
            "/api/favorites", headers=auth_headers, params={"folder_id": folder.id}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2
        # total_pages 必须与筛选后的 total 一致，不能宣称还有空的下一页
        assert body["total_pages"] == 1


class TestErrorRateDenominator:
    @pytest.mark.asyncio
    async def test_fast_errors_do_not_inflate_rate(self, client, staff_headers, db_session):
        """亚毫秒 4xx（response_time_ms=0）计入分子时，也必须在分母里。"""
        stamp = datetime.now(UTC) - timedelta(minutes=5)
        rows = [
            VisitLog(
                path="/api/fast-error",
                method="GET",
                ip="127.0.0.1",
                user_agent="pytest",
                status_code=429,
                response_time_ms=0,
                created_at=stamp,
            )
            for _ in range(10)
        ]
        # 10 条带耗时的正常请求：旧实现的分母只有这 10 条，于是错误率报成 100%
        rows += [
            VisitLog(
                path="/api/ok",
                method="GET",
                ip="127.0.0.1",
                user_agent="pytest",
                status_code=200,
                response_time_ms=120,
                created_at=stamp,
            )
            for _ in range(10)
        ]
        db_session.add_all(rows)
        await db_session.commit()

        resp = await client.get("/api/monitoring/performance/summary", headers=staff_headers)
        assert resp.status_code == 200
        payload = resp.json()
        h24 = payload.get("data", payload)["last_24h"]
        assert h24["error_count"] >= 10
        assert h24["window_requests"] >= 20
        assert h24["error_rate"] <= 100.0
        assert h24["error_rate"] == pytest.approx(
            round(h24["error_count"] / max(h24["window_requests"], 1) * 100, 2), abs=0.01
        )


class TestPerformanceMetricsErrorRate:
    """``GET /api/monitoring/performance`` 的 error_rate 曾经恒为 0——环形缓冲不记状态码，
    于是这个字段把一个"看起来像读数"的假值交给了任何消费者。修后它另取自 visit_logs。"""

    @staticmethod
    def _seed(db_session):
        stamp = datetime.now(UTC) - timedelta(minutes=2)
        rows = [
            VisitLog(
                path="/api/mixed-ok",
                method="GET",
                ip="127.0.0.1",
                user_agent="pytest",
                status_code=200,
                response_time_ms=30,
                created_at=stamp,
            )
            for _ in range(3)
        ] + [
            VisitLog(
                path="/api/mixed-err",
                method="GET",
                ip="127.0.0.1",
                user_agent="pytest",
                status_code=500,
                response_time_ms=40,
                created_at=stamp,
            )
            for _ in range(1)
        ]
        db_session.add_all(rows)

    @pytest.mark.asyncio
    async def test_error_rate_is_measured_not_zero_filled(self, client, staff_headers, db_session):
        self._seed(db_session)
        await db_session.commit()

        resp = await client.get(
            "/api/monitoring/performance", headers=staff_headers, params={"period": 60}
        )
        assert resp.status_code == 200
        payload = resp.json()
        data = payload.get("data", payload)
        assert data["error_count"] >= 1
        assert data["window_requests"] >= 4
        assert data["error_rate"] > 0
        assert data["error_rate"] == pytest.approx(
            round(data["error_count"] / max(data["window_requests"], 1) * 100, 2), abs=0.01
        )

    @pytest.mark.asyncio
    async def test_empty_latency_buffer_still_reports_errors(
        self, client, staff_headers, db_session
    ):
        """进程刚重启（缓冲为空）时延迟回 0，但错误率不得跟着回 0。"""
        import backend.api.monitoring as monitoring

        self._seed(db_session)
        await db_session.commit()

        saved = dict(monitoring._metrics)
        saved_ts = dict(monitoring._metrics_timestamps)
        monitoring._metrics["request_latency"] = []
        monitoring._metrics_timestamps["request_latency"] = []
        try:
            resp = await client.get(
                "/api/monitoring/performance", headers=staff_headers, params={"period": 60}
            )
        finally:
            monitoring._metrics.clear()
            monitoring._metrics.update(saved)
            monitoring._metrics_timestamps.clear()
            monitoring._metrics_timestamps.update(saved_ts)

        assert resp.status_code == 200
        data = resp.json()
        data = data.get("data", data)
        assert data["avg_latency"] == 0
        assert "sample_count" not in data
        assert data["error_count"] >= 1
        assert data["error_rate"] > 0
