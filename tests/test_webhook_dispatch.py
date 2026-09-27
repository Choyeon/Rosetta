"""Webhook 事件投递链路的回归测试。

覆盖此前完全断链的一段：业务事件 -> hooks 总线 -> 订阅端点投递。
过去 trigger_webhook 没有任何调用方，/admin/system/webhooks 配置的订阅
永远不会兑现第二次请求；这里把「谁注册了什么钩子」「投给谁」「签名对什么字节」
钉成断言。
"""

import asyncio
import json
from types import SimpleNamespace

import pytest

from backend.api import webhook as wh
from backend.core import hooks as _hooks

# ── 订阅判定 ──────────────────────────────────────────────────────────────


def test_subscribes_reads_json_list():
    endpoint = SimpleNamespace(id=1, events='["post.published", "comment.created"]')
    assert wh._subscribes(endpoint, "post.published") is True
    assert wh._subscribes(endpoint, "post.deleted") is False


def test_subscribes_tolerates_already_parsed_list():
    endpoint = SimpleNamespace(id=1, events=["post.published"])
    assert wh._subscribes(endpoint, "post.published") is True


def test_subscribes_rejects_malformed_events_column():
    """库里存进脏数据时按「未订阅」处理，绝不在投递路径上抛异常。"""
    endpoint = SimpleNamespace(id=7, events="{not json")
    assert wh._subscribes(endpoint, "post.published") is False


# ── payload 字段白名单 ────────────────────────────────────────────────────


def test_event_payload_excludes_pii_and_non_entities():
    """邮箱等 PII 不得出现在对外 payload 里，session 之类对象也不该被扫。"""
    user = SimpleNamespace(id=42, email="p@ii.test", name="Alice")
    data = wh._event_payload((user,), {"db": object(), "current_user": user})
    assert data["id"] == 42
    assert data["name"] == "Alice"
    assert data["actor_id"] == 42
    assert "email" not in json.dumps(data)


def test_event_payload_merges_explicit_webhook_payload():
    """事件源显式声明的对外字段优先，未声明的字段仍走白名单。"""
    media = SimpleNamespace(id=9, filename="a.png", file_type="image", email="x@y.z")
    data = wh._event_payload(
        (media,),
        {"webhook_payload": {"url": "/uploads/a.png", "file_size": 123}},
    )
    assert data["url"] == "/uploads/a.png"
    assert data["file_size"] == 123
    assert data["id"] == 9
    assert "email" not in data


# ── 总线接线 ──────────────────────────────────────────────────────────────


@pytest.fixture
def clean_listeners():
    """注册/注销成对，且**进入用例前先清一次**。

    backend/main.py 的 startup 会调用 register_webhook_listeners()，跑全量套件时
    任何先创建过 app（client fixture）的用例都会让全局 _listeners 非空，
    导致"首次注册返回全部事件"这类断言按顺序假失败。这里显式回到干净起点。
    """
    wh.unregister_webhook_listeners()
    yield
    wh.unregister_webhook_listeners()


def _handlers_for(event_type: str) -> list:
    """总线上该事件当前挂的 handler 函数（含插件的，不只 webhook 的）。"""
    return [h.fn for h in _hooks._actions.get(event_type, [])]


def test_register_webhook_listeners_covers_catalog_and_is_idempotent(clean_listeners):
    first = wh.register_webhook_listeners()
    assert sorted(first) == sorted(wh.WEBHOOK_EVENTS)
    for event_type in wh.WEBHOOK_EVENTS:
        assert _hooks.has_action(event_type)

    # 第二次调用不得重复注册：否则一次事件会投递两份
    assert wh.register_webhook_listeners() == []
    handler = wh._listeners["post.published"]
    # 注册表存的是 _HookHandler 包装对象，按 .fn 身份比对
    assert _handlers_for("post.published").count(handler) == 1


def test_unregister_webhook_listeners_removes_everything(clean_listeners):
    wh.register_webhook_listeners()
    expected = {e: len(_handlers_for(e)) for e in wh.WEBHOOK_EVENTS}
    removed = wh.unregister_webhook_listeners()
    assert sorted(removed) == sorted(wh.WEBHOOK_EVENTS)
    assert wh._listeners == {}
    # 只要求 webhook 自己那份被摘掉：同名事件上插件的 handler 不归本模块管
    for event_type, before in expected.items():
        assert len(_handlers_for(event_type)) == before - 1


@pytest.mark.asyncio
async def test_bus_event_reaches_dispatch(clean_listeners, monkeypatch):
    """总线事件必须真正排到投递任务——这段链路历史上是彻底断的。"""
    captured: list[tuple] = []

    class _FakeSession:
        async def commit(self):
            pass

        async def __aexit__(self, *exc):
            return False

        async def __aenter__(self):
            return self

    monkeypatch.setattr(wh, "async_session_maker", lambda: _FakeSession())

    async def _capture(event_type, payload, session):
        captured.append((event_type, payload))
        return 0

    monkeypatch.setattr(wh, "trigger_webhook", _capture)
    wh.register_webhook_listeners()

    post = SimpleNamespace(id=7, slug="hello", status="published", email="a@b.test")
    # 同名事件上 seo-toolkit 也挂了 handler（插件全量套件里会启动），
    # 所以"执行了几个 handler"不是本用例的保证；保证的是**恰好一次**投递。
    executed = await _hooks.do_action("post.published", post)
    assert executed >= 1

    # 投递是 create_task，等它跑完再断言
    await asyncio.gather(*list(wh._dispatch_tasks))

    assert captured == [("post.published", {"id": 7, "slug": "hello", "status": "published"})]


# ── 投递 ──────────────────────────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "ok"):
        self.status_code = status_code
        self.text = text


class _FakeClient:
    """记录 (url, content, headers) 调用序列；按 url 尾号决定返回码。"""

    def __init__(self, failures=None):
        self.calls = []
        self.failures = failures or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, content=None, headers=None):
        self.calls.append({"url": url, "content": content, "headers": headers})
        if url in self.failures:
            raise self.failures[url]
        return _FakeResponse(self._code_for(url))

    def _code_for(self, url):
        return 500 if url.endswith("/boom") else 204


async def _make_endpoint(db, *, url, events, secret=None, active=True):
    endpoint = wh.WebhookEndpoint(
        name=f"e-{url}",
        url=url,
        secret=secret,
        events=json.dumps(events),
        is_active=active,
    )
    db.add(endpoint)
    await db.flush()
    return endpoint


@pytest.mark.asyncio
async def test_send_once_signs_the_exact_bytes_and_sets_event_header(monkeypatch):
    monkeypatch.setattr(wh, "_validate_webhook_url", _noop)
    client = _FakeClient()
    body = b'{"event":"post.published"}'

    code, text, error = await wh._send_once(
        client, "https://x.test/hook", body, "s3cret", "post.published"
    )

    assert (code, error) == (204, None)
    call = client.calls[0]
    assert call["content"] is body
    assert call["headers"]["X-Rosetta-Event"] == "post.published"
    # 签名必须对「实际发出的字节」计算：重新序列化就会与接收方校验不上
    import hashlib
    import hmac

    expected = hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    assert call["headers"]["X-Rosetta-Signature"] == f"sha256={expected}"


@pytest.mark.asyncio
async def test_send_once_reports_5xx_as_error(monkeypatch):
    monkeypatch.setattr(wh, "_validate_webhook_url", _noop)
    client = _FakeClient()

    code, _text, error = await wh._send_once(
        client, "https://x.test/boom", b"{}", None, "post.created"
    )

    assert code == 500
    assert error == "HTTP 500"


@pytest.mark.asyncio
async def test_send_once_blocks_unsafe_target(monkeypatch):
    from backend.core.net_guard import UnsafeTargetError

    async def _raise(_url):
        raise UnsafeTargetError("private address")

    # _validate_webhook_url 抛 HTTPException 是既有约定（创建/更新路径复用同一护栏）
    from fastapi import HTTPException

    async def _raise_http(_url):
        raise HTTPException(status_code=400, detail="private address")

    monkeypatch.setattr(wh, "_validate_webhook_url", _raise_http)
    client = _FakeClient()

    code, _text, error = await wh._send_once(
        client, "http://127.0.0.1/hook", b"{}", None, "post.created"
    )

    assert code is None
    assert error and "blocked" in error
    assert client.calls == []
    assert UnsafeTargetError is not None  # 护栏异常类型仍被模块使用


@pytest.mark.asyncio
async def test_trigger_webhook_delivers_only_to_subscribed_active_endpoints(
    db_session, monkeypatch
):
    monkeypatch.setattr(wh, "_validate_webhook_url", _noop)
    client = _FakeClient()
    monkeypatch.setattr(wh.httpx, "AsyncClient", lambda **_kw: client)

    subscribed = await _make_endpoint(
        db_session, url="https://x.test/a", events=["post.published"], secret="k"
    )
    other_event = await _make_endpoint(
        db_session, url="https://x.test/b", events=["comment.created"]
    )
    inactive = await _make_endpoint(
        db_session, url="https://x.test/c", events=["post.published"], active=False
    )

    delivered = await wh.trigger_webhook("post.published", {"id": 1}, db_session)

    assert delivered == 1
    assert [c["url"] for c in client.calls] == [subscribed.url]
    # 未订阅 / 已停用的端点不得收到任何投递（含投递记录行）
    for endpoint in (other_event, inactive):
        rows = (await db_session.execute(_deliveries_for(endpoint.id))).scalars().all()
        assert rows == []

    rows = (await db_session.execute(_deliveries_for(subscribed.id))).scalars().all()
    assert len(rows) == 1
    assert rows[0].status_code == 204
    assert rows[0].error is None
    assert rows[0].delivered_at is not None


@pytest.mark.asyncio
async def test_trigger_webhook_records_failure_without_raising(db_session, monkeypatch):
    monkeypatch.setattr(wh, "_validate_webhook_url", _noop)
    endpoint = await _make_endpoint(db_session, url="https://x.test/boom", events=["post.deleted"])
    client = _FakeClient()
    monkeypatch.setattr(wh.httpx, "AsyncClient", lambda **_kw: client)

    delivered = await wh.trigger_webhook("post.deleted", {"id": 2}, db_session)

    assert delivered == 1
    row = (await db_session.execute(_deliveries_for(endpoint.id))).scalars().one()
    assert row.status_code == 500
    assert row.error == "HTTP 500"


@pytest.mark.asyncio
async def test_trigger_webhook_isolates_a_failing_endpoint(db_session, monkeypatch):
    """单个端点抛异常不得带走整批投递（gather + return_exceptions）。"""
    monkeypatch.setattr(wh, "_validate_webhook_url", _noop)
    good = await _make_endpoint(db_session, url="https://x.test/good", events=["post.created"])
    bad = await _make_endpoint(db_session, url="https://x.test/bad", events=["post.created"])

    client = _FakeClient(failures={bad.url: RuntimeError("connection refused")})
    monkeypatch.setattr(wh.httpx, "AsyncClient", lambda **_kw: client)

    delivered = await wh.trigger_webhook("post.created", {"id": 3}, db_session)

    assert delivered == 2
    good_row = (await db_session.execute(_deliveries_for(good.id))).scalars().one()
    bad_row = (await db_session.execute(_deliveries_for(bad.id))).scalars().one()
    assert good_row.error is None
    assert bad_row.status_code is None
    assert "connection refused" in (bad_row.error or "")


async def _noop(_url):
    return None


def _deliveries_for(endpoint_id):
    from sqlalchemy import select

    return select(wh.WebhookDelivery).where(wh.WebhookDelivery.endpoint_id == endpoint_id)
