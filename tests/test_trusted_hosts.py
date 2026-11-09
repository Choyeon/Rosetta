"""生产 TrustedHost 白名单的回环保护回归。

上一轮本地 UI 验收踩到的真实问题：`SITE_URL=http://localhost:3000` 时旧逻辑
只在站点域名「不是回环」时才补 localhost/127.0.0.1，白名单于是只有
["localhost"]；devProxy 的 changeOrigin 把 Host 改成 127.0.0.1:8000，
所有 /api/* 直接 400 Invalid host header，内页集体"加载失败"。
正式 Nginx 用 `proxy_set_header Host $host` 不受影响，但本地/容器直连必踩。

这里同时钉住纯函数输出与中间件实际放行行为。
"""

from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from backend.core.security_middleware import build_trusted_hosts


class TestBuildTrustedHosts:
    def test_localhost_site_url_still_allows_loopback_ip(self):
        assert build_trusted_hosts("http://localhost:3000") == ["localhost", "127.0.0.1"]

    def test_loopback_ip_site_url_still_allows_localhost(self):
        assert build_trusted_hosts("http://127.0.0.1:3000") == ["127.0.0.1", "localhost"]

    def test_public_site_url_keeps_domain_and_loopback(self):
        assert build_trusted_hosts("https://blog.example.com/") == [
            "blog.example.com",
            "localhost",
            "127.0.0.1",
        ]

    def test_empty_site_url_degrades_to_loopback_only(self):
        assert build_trusted_hosts("") == ["localhost", "127.0.0.1"]

    def test_no_duplicates(self):
        hosts = build_trusted_hosts("https://localhost")
        assert len(hosts) == len(set(hosts)) == 2


async def _health(_request):
    return PlainTextResponse("ok")


def _app(hosts: list[str]) -> Starlette:
    app = Starlette(routes=[Route("/health", _health)])
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)
    return app


class TestMiddlewareActuallyAcceptsBothLoopbacks:
    async def _status(self, hosts: list[str], host_header: str) -> int:
        async with AsyncClient(
            transport=ASGITransport(app=_app(hosts)), base_url="http://test"
        ) as ac:
            return (await ac.get("/health", headers={"Host": host_header})).status_code

    async def test_localhost_site_url_accepts_127_host_header(self):
        hosts = build_trusted_hosts("http://localhost:3000")
        assert await self._status(hosts, "localhost:3000") == 200
        assert await self._status(hosts, "127.0.0.1:8000") == 200
        assert await self._status(hosts, "evil.example.com") == 400

    async def test_public_site_url_accepts_domain_and_loopback(self):
        hosts = build_trusted_hosts("https://blog.example.com")
        assert await self._status(hosts, "blog.example.com") == 200
        assert await self._status(hosts, "127.0.0.1:8000") == 200
        assert await self._status(hosts, "evil.example.com") == 400
