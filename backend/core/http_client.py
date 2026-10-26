"""
出站 HTTP 客户端的统一构造入口。

为什么需要这一层：`httpx` 在**构造** `AsyncClient` 时就会解析代理环境变量，把
`NO_PROXY` 的每一项当成 URL 模式。Windows 上常见写法 `NO_PROXY=...,::1,[::1]`
（带方括号的 IPv6）会让 `URLPattern` 直接抛

    httpx.InvalidURL: Invalid port: ':1]'

——也就是"机器上一个环境变量写错，所有出站请求全部失效"，而且这些调用点大多是
fire-and-forget（webhook 投递、前端缓存清除、IndexNow），异常还会被 `except` 吞成
debug 日志，现场只表现为"功能静默不生效"。本机实测复现：webhook 永不投递、
`POST /_rosetta/purge-cache` 永不触发 → 主题切换后缓存一直不失效。

兜底策略：先按原样构造（尊重代理），仅在构造期解析失败时退回 `trust_env=False`
（直连）。直连不会让请求打到内网——SSRF 护栏是另一层独立校验（core/net_guard.py）。
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def create_async_client(**kwargs: Any) -> httpx.AsyncClient:
    """构造 ``httpx.AsyncClient``，环境代理配置畸形时自动退回直连。"""
    try:
        return httpx.AsyncClient(**kwargs)
    except (httpx.InvalidURL, ValueError) as exc:
        logger.warning("环境代理配置不可用，已改用直连（trust_env=False）：%s", exc)
        kwargs.pop("trust_env", None)
        return httpx.AsyncClient(trust_env=False, **kwargs)
