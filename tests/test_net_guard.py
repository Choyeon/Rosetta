"""net_guard SSRF 护栏与头像/Bing 代理接线的行为测试。

不发起真实网络请求：
- DNS 解析通过 net_guard._resolver 注入点 mock
- validated_get 的重定向逐跳校验用 httpx.MockTransport
- avatar_proxy 端点级测试只断言「内网目标被拒绝 → 307 兜底」，不发真实请求
"""

import base64
import socket

import httpx
import pytest

from backend.core import net_guard
from backend.core.net_guard import UnsafeTargetError, assert_public_http_url, validated_get


def _install_resolver(monkeypatch, results):
    """注入假 DNS：results 是 {host: [ip, ...]}"""

    async def fake_resolver(host: str):
        ips = results.get(host)
        if ips is None:
            raise socket.gaierror(8, "Unknown host")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0)) for ip in ips]

    monkeypatch.setattr(net_guard, "_resolver", fake_resolver)


# ---------------------------------------------------------------------------
# assert_public_http_url
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reject_private_literal_ip():
    with pytest.raises(UnsafeTargetError):
        await assert_public_http_url("http://192.168.1.1/avatar.png")


@pytest.mark.asyncio
async def test_reject_loopback_literal_ip():
    with pytest.raises(UnsafeTargetError):
        await assert_public_http_url("http://127.0.0.1:8000/health")


@pytest.mark.asyncio
async def test_reject_ipv6_mapped_v4():
    # IPv4-mapped IPv6 内嵌私网地址
    with pytest.raises(UnsafeTargetError):
        await assert_public_http_url("http://[::ffff:10.0.0.1]/x")


@pytest.mark.asyncio
async def test_reject_metadata_endpoint():
    # 云元数据端点 169.254.169.254 属链路本地段
    with pytest.raises(UnsafeTargetError):
        await assert_public_http_url("http://169.254.169.254/latest/meta-data/")


@pytest.mark.asyncio
async def test_reject_non_http_scheme():
    with pytest.raises(UnsafeTargetError):
        await assert_public_http_url("file:///etc/passwd")
    with pytest.raises(UnsafeTargetError):
        await assert_public_http_url("gopher://example.com/x")


@pytest.mark.asyncio
async def test_reject_domain_resolving_to_private(monkeypatch):
    """域名解析到内网 IP（经典 SSRF）必须被拒——即使域名本身看起来无害。"""
    _install_resolver(monkeypatch, {"evil.example.com": ["192.168.0.10"]})
    with pytest.raises(UnsafeTargetError):
        await assert_public_http_url("https://evil.example.com/avatar.png")


@pytest.mark.asyncio
async def test_accept_domain_resolving_to_public(monkeypatch):
    _install_resolver(monkeypatch, {"example.com": ["93.184.216.34"]})
    # 不抛异常即通过
    await assert_public_http_url("https://example.com/avatar.png")


@pytest.mark.asyncio
async def test_reject_when_any_resolution_is_private(monkeypatch):
    """多 A 记录域名：任一解析结果在内网即整体拒绝。"""
    _install_resolver(monkeypatch, {"dual-stack.example.com": ["93.184.216.34", "172.16.5.5"]})
    with pytest.raises(UnsafeTargetError):
        await assert_public_http_url("https://dual-stack.example.com/a.png")


# ---------------------------------------------------------------------------
# validated_get：重定向逐跳校验
# ---------------------------------------------------------------------------


def _client_with(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=False,
    )


_PUBLIC_RESOLVER = {
    "public-a.example.com": ["93.184.216.34"],
    "public-b.example.com": ["93.184.216.35"],
    "loopy.example.com": ["93.184.216.36"],
}


@pytest.mark.asyncio
async def test_validated_get_follows_safe_redirect(monkeypatch):
    _install_resolver(monkeypatch, _PUBLIC_RESOLVER)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "public-a.example.com":
            return httpx.Response(302, headers={"location": "https://public-b.example.com/img.png"})
        return httpx.Response(200, headers={"content-type": "image/png"}, content=b"png")

    async with _client_with(handler) as c:
        r = await validated_get(c, "https://public-a.example.com/img.png")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_validated_get_blocks_redirect_to_private(monkeypatch):
    """公网域名 302 弹到内网地址 → 必须拒绝（不能让 httpx 自动跟跳绕过校验）。"""
    _install_resolver(monkeypatch, _PUBLIC_RESOLVER)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "public-a.example.com":
            return httpx.Response(302, headers={"location": "http://192.168.1.1/admin"})
        raise AssertionError("不应请求内网地址")

    async with _client_with(handler) as c:
        with pytest.raises(UnsafeTargetError):
            await validated_get(c, "https://public-a.example.com/img.png")


@pytest.mark.asyncio
async def test_validated_get_redirect_loop_rejected(monkeypatch):
    _install_resolver(monkeypatch, _PUBLIC_RESOLVER)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": str(request.url)})

    async with _client_with(handler) as c:
        with pytest.raises(UnsafeTargetError):
            await validated_get(c, "https://loopy.example.com/img.png")


@pytest.mark.asyncio
async def test_validated_get_relative_location_joined(monkeypatch):
    """相对路径 Location 头按当前 URL 拼接后校验。"""
    _install_resolver(monkeypatch, _PUBLIC_RESOLVER)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/hop":
            return httpx.Response(302, headers={"location": "/final.png"})
        return httpx.Response(200, headers={"content-type": "image/png"}, content=b"png")

    async with _client_with(handler) as c:
        r = await validated_get(c, "https://public-a.example.com/hop")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# avatar_proxy 端点级行为（不发真实请求）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_avatar_proxy_rejects_private_target(client):
    """src 指向内网字面量 IP → 307 兜底，而非服务端发起请求。"""
    target = "http://192.168.1.1/secret.png"
    src = base64.urlsafe_b64encode(target.encode()).decode()
    r = await client.get(f"/api/media/avatar?src={src}&fallback=1")
    assert r.status_code == 307
    assert r.headers["location"] == "/favicon/rosetta-256.png"


@pytest.mark.asyncio
async def test_avatar_proxy_rejects_metadata_target(client):
    target = "http://169.254.169.254/latest/meta-data/"
    src = base64.urlsafe_b64encode(target.encode()).decode()
    r = await client.get(f"/api/media/avatar?src={src}")
    assert r.status_code == 307
    assert r.headers["location"] == "/favicon/rosetta-256.png"
