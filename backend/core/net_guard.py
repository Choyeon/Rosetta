"""服务端主动外连的安全护栏（anti-SSRF）。

供头像代理 / Bing 图片代理 / 远程安装等「服务端按 URL 主动发起请求」的
场景共用：在发起请求**之前**解析目标域名并校验全部解析结果均为公网地址，
阻断对内网 / 环回 / 链路本地 / 保留网段的探测与数据回读。

注意：这是 check-then-fetch 模式，无法抵御低 TTL 的 DNS rebinding
（校验与连接两次解析结果不一致）；如需彻底防护需在连接层固定已校验 IP。
当前实现已覆盖绝大多数攻击面，剩余风险在各调用方文档中注明。
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# 重定向跳数上限：正常头像 / 壁纸 CDN 链不会超过 3 跳
MAX_SAFE_REDIRECTS = 4


class UnsafeTargetError(Exception):
    """目标地址解析到了不可信网络（内网 / 环回 / 保留段）或协议不合法。"""


def _is_untrusted_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """判定单个 IP 是否属于不可信网段。

    采用「必须 is_global」的保守策略：头像 / 壁纸类外连没有任何理由
    指向非全球单播地址；这同时覆盖了私网、环回、链路本地、组播、
    保留段以及 100.64.0.0/10（CGN）等历史 gray zone。
    """
    # IPv4-mapped IPv6（如 ::ffff:10.0.0.1）取内嵌 IPv4 再判定
    if isinstance(ip, ipaddress.IPv6Address):
        mapped = ip.ipv4_mapped
        if mapped is not None:
            ip = mapped
        elif ip.is_site_local or ip.is_loopback:
            return True

    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
        or not ip.is_global
    )


# DNS 解析函数（测试可注入 mock；生产走 running loop 的 getaddrinfo）
_resolver = None


async def _resolve_host(host: str):
    if _resolver is not None:
        return await _resolver(host)
    # Python 3.10-3.12 无 asyncio.getaddrinfo 模块级函数，须走 running loop
    loop = asyncio.get_running_loop()
    return await loop.getaddrinfo(host, None)


async def assert_public_http_url(
    url: str,
    *,
    allow_schemes: tuple[str, ...] = ("http", "https"),
) -> None:
    """校验 URL 可安全地由服务端发起请求，不合法时抛 ``UnsafeTargetError``。

    - scheme 必须是 http/https（防 file://、gopher:// 等）
    - 主机名必须能解析，且**全部**解析结果均为公网地址
      （任一命中内网即拒绝——域名同时绑公网与内网 IP 也不放行）
    """
    parsed = urlparse(url)
    if parsed.scheme not in allow_schemes:
        raise UnsafeTargetError(f"不允许的协议: {parsed.scheme!r}")

    host = (parsed.hostname or "").strip().lower()
    if not host:
        raise UnsafeTargetError("URL 缺少主机名")

    # 字面量 IP 直接判定，省一次 DNS
    try:
        literal_ip = ipaddress.ip_address(host)
    except ValueError:
        literal_ip = None
    if literal_ip is not None:
        if _is_untrusted_ip(literal_ip):
            raise UnsafeTargetError(f"目标地址位于不可信网段: {host}")
        return

    try:
        infos = await _resolve_host(host)
    except (socket.gaierror, OSError) as exc:
        raise UnsafeTargetError(f"域名解析失败: {host}") from exc

    if not infos:
        raise UnsafeTargetError(f"域名无解析结果: {host}")

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if _is_untrusted_ip(ip):
            logger.warning("[net_guard] 拒绝指向不可信网段的目标 %s -> %s", host, ip)
            raise UnsafeTargetError(f"目标域名解析到不可信网段: {host} -> {ip}")


async def validated_get(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    max_redirects: int = MAX_SAFE_REDIRECTS,
) -> httpx.Response:
    """在 ``client`` 上发起 GET，并对**每一跳**重定向目标执行 SSRF 校验。

    要求调用方创建 client 时 ``follow_redirects=False``（否则 httpx 会在
    校验之外自动跟跳，护栏失效）。返回最终的非重定向响应（body 未消费，
    调用方可继续 ``aiter_bytes`` 流式转发）；重定向超限抛 ``UnsafeTargetError``。
    """
    current = url
    for _hop in range(max_redirects + 1):
        await assert_public_http_url(current)
        resp = await client.get(current, headers=headers)
        if resp.status_code not in (301, 302, 303, 307, 308):
            return resp
        location = resp.headers.get("location")
        await resp.aclose()
        if not location:
            raise UnsafeTargetError("重定向缺少 Location 头")
        current = str(httpx.URL(current).join(location))
    raise UnsafeTargetError(f"重定向跳数超过 {max_redirects}")
