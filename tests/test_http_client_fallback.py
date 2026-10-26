"""出站 HTTP 客户端构造兜底：环境代理写坏时不得让所有出站请求失效。

复现条件（本机实测）：`NO_PROXY` 里含带方括号的 IPv6 项（如 `[::1]`）时，
`httpx.AsyncClient(...)` 在**构造阶段**就抛 `InvalidURL: Invalid port ':1]'`。
所有出站调用点（webhook 投递、前端缓存清除、IndexNow、头像代理、远程安装）
都是 fire-and-forget，异常被 `except` 吞成 debug 日志——现场表现是"功能静默不生效"，
最典型的一条是主题切换后 Nitro 页面缓存永远清不掉（purge 端点恒不被调用）。
"""

from __future__ import annotations

import httpx
import pytest

from backend.core import http_client


def test_falls_back_to_direct_when_env_proxy_is_malformed(monkeypatch):
    """构造期 InvalidURL → 自动退回 trust_env=False。"""
    calls: list[dict] = []
    real_client = httpx.AsyncClient

    def _fake_client(**kwargs):
        calls.append(kwargs)
        if kwargs.get("trust_env") is not False:
            raise httpx.InvalidURL("Invalid port: ':1]'")
        return "client-direct"

    monkeypatch.setattr(httpx, "AsyncClient", _fake_client)

    client = http_client.create_async_client(timeout=5)

    assert client == "client-direct"
    assert len(calls) == 2, "应当先按原样构造一次，失败后再退回直连"
    assert calls[0] == {"timeout": 5}
    assert calls[1] == {"timeout": 5, "trust_env": False}
    monkeypatch.setattr(httpx, "AsyncClient", real_client)


def test_normal_environment_keeps_env_proxy(monkeypatch):
    """环境正常时不改成直连（保留企业代理配置）。"""
    calls: list[dict] = []

    def _fake_client(**kwargs):
        calls.append(kwargs)
        return "client-normal"

    monkeypatch.setattr(httpx, "AsyncClient", _fake_client)

    client = http_client.create_async_client(timeout=3, follow_redirects=False)

    assert client == "client-normal"
    assert calls == [{"timeout": 3, "follow_redirects": False}]
    assert "trust_env" not in calls[0]


def test_explicit_trust_env_is_not_duplicated(monkeypatch):
    """调用方显式传 trust_env 时，兜底不得重复传（否则 TypeError）。"""
    calls: list[dict] = []

    def _fake_client(**kwargs):
        calls.append(dict(kwargs))
        if kwargs.get("trust_env") is True:
            raise ValueError("boom")
        return "client-direct"

    monkeypatch.setattr(httpx, "AsyncClient", _fake_client)

    assert http_client.create_async_client(trust_env=True, timeout=1) == "client-direct"
    assert calls[-1] == {"timeout": 1, "trust_env": False}


@pytest.mark.parametrize("exc", [httpx.InvalidURL("bad"), ValueError("bad")])
def test_both_error_types_are_covered(monkeypatch, exc):
    def _fake_client(**_kwargs):
        raise exc

    monkeypatch.setattr(httpx, "AsyncClient", _fake_client)
    # 第二次仍失败 → 异常照常抛出（不无限重试、不吞成成功）
    with pytest.raises(type(exc)):
        http_client.create_async_client(timeout=1)
