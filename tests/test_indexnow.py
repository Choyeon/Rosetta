"""IndexNow 即时推送回归。

契约（backend/services/indexnow.py）：
1. seo 分组 indexnow_enabled=True 且 indexnow_key 非空时，POST 携带该文章四语 URL
   （zh 裸路径 + /en /ja /zh_Hant）；
2. 开关关闭 / key 为空 / site_url 无主机名 → 不发请求；
3. 投递异常一律吞掉（只记 warning，且日志绝不出现 key 明文）；
4. 总线监听器同步取 slug、异步排任务，不阻塞文章写路径。
"""

import asyncio
from types import SimpleNamespace

import pytest

from backend.services import indexnow


@pytest.fixture(autouse=True)
def _isolate_state():
    """每个用例后清掉总线监听与未完成任务，防跨用例残留。"""
    yield
    indexnow.unregister_indexnow_listeners()
    indexnow._push_tasks.clear()


def _fake_config(monkeypatch, *, enabled=True, key="s3cr3t-indexnow-key"):
    async def _read_group(name, db=None):
        assert name == "seo"
        return {"indexnow_enabled": enabled, "indexnow_key": key}

    monkeypatch.setattr(indexnow, "read_group", _read_group)


def _capture_send(monkeypatch, *, status_code=200, boom=None):
    sent: list[dict] = []

    async def _send(payload):
        sent.append(payload)
        if boom is not None:
            raise boom
        return status_code

    monkeypatch.setattr(indexnow, "_send", _send)
    return sent


@pytest.mark.asyncio
async def test_push_sends_four_locale_urls(monkeypatch):
    """enabled + key：一次 POST，urlList 恰为该文章的四语 URL。"""
    _fake_config(monkeypatch)
    sent = _capture_send(monkeypatch)
    monkeypatch.setattr(indexnow.settings, "site_url", "https://blog.example.com")

    pushed = await indexnow.push_post_to_indexnow("hello-world")

    assert pushed is True
    assert len(sent) == 1
    payload = sent[0]
    assert payload["host"] == "blog.example.com"
    assert payload["key"] == "s3cr3t-indexnow-key"
    assert payload["urlList"] == [
        "https://blog.example.com/posts/hello-world",
        "https://blog.example.com/en/posts/hello-world",
        "https://blog.example.com/ja/posts/hello-world",
        "https://blog.example.com/zh_Hant/posts/hello-world",
    ]


@pytest.mark.asyncio
async def test_push_skipped_when_disabled(monkeypatch):
    _fake_config(monkeypatch, enabled=False)
    sent = _capture_send(monkeypatch)
    monkeypatch.setattr(indexnow.settings, "site_url", "https://blog.example.com")

    assert await indexnow.push_post_to_indexnow("x") is False
    assert sent == []


@pytest.mark.asyncio
async def test_push_skipped_when_key_empty(monkeypatch):
    _fake_config(monkeypatch, key="   ")
    sent = _capture_send(monkeypatch)
    monkeypatch.setattr(indexnow.settings, "site_url", "https://blog.example.com")

    assert await indexnow.push_post_to_indexnow("x") is False
    assert sent == []


@pytest.mark.asyncio
async def test_push_skipped_without_site_url_host(monkeypatch):
    """site_url 未配置：host 无法确定，不发请求（也不虚构域名）。"""
    _fake_config(monkeypatch)
    sent = _capture_send(monkeypatch)
    monkeypatch.setattr(indexnow.settings, "site_url", "")

    assert await indexnow.push_post_to_indexnow("x") is False
    assert sent == []


@pytest.mark.asyncio
async def test_send_exception_is_swallowed_and_key_never_logged(monkeypatch, caplog):
    """POST 抛异常 → 返回 False 且不外泄；日志里不得出现 key 明文。"""
    _fake_config(monkeypatch)
    _capture_send(monkeypatch, boom=RuntimeError("connection reset"))
    monkeypatch.setattr(indexnow.settings, "site_url", "https://blog.example.com")

    with caplog.at_level("WARNING"):
        assert await indexnow.push_post_to_indexnow("boom-post") is False

    assert "connection reset" in caplog.text
    assert "s3cr3t-indexnow-key" not in caplog.text


@pytest.mark.asyncio
async def test_non_2xx_only_warns(monkeypatch, caplog):
    _fake_config(monkeypatch)
    sent = _capture_send(monkeypatch, status_code=422)
    monkeypatch.setattr(indexnow.settings, "site_url", "https://blog.example.com")

    with caplog.at_level("WARNING"):
        assert await indexnow.push_post_to_indexnow("x") is True

    assert len(sent) == 1
    assert "422" in caplog.text


def test_extract_slug_covers_both_event_shapes():
    """post.published 把实体放 kwarg（首位参数是 int id）；post.updated 按位置传实体。"""
    post = SimpleNamespace(slug="dual-shape")
    assert indexnow._extract_slug((7,), {"post": post}) == "dual-shape"
    assert indexnow._extract_slug((post,), {}) == "dual-shape"
    assert indexnow._extract_slug((7,), {}) is None


@pytest.mark.asyncio
async def test_listener_registers_and_pushes_without_blocking(monkeypatch):
    """注册幂等 + 总线回调排任务：事件返回后任务才在后台跑，slug 正确传递。"""
    registered = indexnow.register_indexnow_listeners()
    assert registered == ["post.published", "post.updated"]
    assert indexnow.register_indexnow_listeners() == []

    pushed: list[str] = []

    async def _fake_push(slug):
        pushed.append(slug)
        await asyncio.sleep(0)
        return True

    monkeypatch.setattr(indexnow, "push_post_to_indexnow", _fake_push)

    post = SimpleNamespace(slug="listener-post")
    await indexnow._on_post_event(1, post=post, current_user=None, db=None)
    await indexnow._on_post_event(post)

    assert indexnow._push_tasks, "监听器必须排后台任务，而不是同步 await 投递"
    await asyncio.gather(*indexnow._push_tasks)
    assert pushed == ["listener-post", "listener-post"]
