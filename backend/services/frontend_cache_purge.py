"""
frontend_cache_purge — 主题变更后通知 Nuxt/Nitro 清除页面级 SWR 缓存。

背景（闪屏根因）：
  Nitro routeRules 对公开页做 swr 缓存（'/' 300s，/archive 等最长 3600s），
  缓存的 HTML 首字节内嵌了渲染当时的主题标记（data-rosetta-theme / <link> /
  颜色 tokens）。后台切换主题后缓存不会失效，访客在缓存窗口内拿到的仍是
  旧主题 HTML，客户端 app:mounted 纠偏再把 DOM 换成新主题 → 视觉上
  "旧主题闪一下再切换"。

  本模块在主题激活 / mods 保存等写操作 commit 之后，向 Nitro 的内部清除
  端点发一个带共享密钥的 POST，让下一次 SSR 立即以新主题渲染。

设计约束：
  - fire-and-forget：绝不 await 进响应链路，前端不可达时只记 debug 日志；
  - 生产必须同时配置 FRONTEND_BASE_URL + FRONTEND_PURGE_SECRET 才启用；
    开发模式（environment=development）允许仅凭 URL/默认 localhost 直连，
    Nitro 端在 dev 下放宽密钥校验（仅本机监听）。
"""

import asyncio
import logging

from backend.core.config import settings
from backend.core.http_client import create_async_client

logger = logging.getLogger(__name__)

PURGE_PATH = "/_rosetta/purge-cache"
PURGE_SECRET_HEADER = "x-rosetta-purge-secret"


def resolve_purge_target() -> str | None:
    """返回清除端点完整 URL；未配置（生产默认）时返回 None 表示禁用。"""
    base = (settings.frontend_base_url or "").strip().rstrip("/")
    if not base and settings.is_development:
        base = "http://localhost:3000"
    if not base:
        return None
    return f"{base}{PURGE_PATH}"


async def _post_purge(url: str) -> None:
    headers = {}
    secret = (settings.frontend_purge_secret or "").strip()
    if secret:
        headers[PURGE_SECRET_HEADER] = secret
    try:
        async with create_async_client(timeout=5) as client:
            resp = await client.post(url, headers=headers)
            if resp.status_code >= 400:
                # 403 = 密钥不一致，404 = 端点未启用；这两种以前只在 debug 里，
                # 现场表现为"改了主题/正文，前台一直不更新"，没有任何信号可查。
                logger.warning("前端缓存清除被拒绝：HTTP %s（%s）", resp.status_code, url)
                return
            try:
                body = resp.json()
            except Exception:  # noqa: BLE001 - 端点返回非 JSON 时不影响主流程
                body = {}
            purged = body.get("purged") if isinstance(body, dict) else None
            if purged == 0:
                # 命中 0 个键有两种可能：本来就没缓存（正常），或键名约定漂移（病态）。
                # 后者只能靠这行日志发现。
                logger.info("前端缓存清除命中 0 个键（%s）", url)
            elif purged is not None:
                logger.debug("前端缓存清除完成：%s 个键（%s）", purged, url)
    except Exception as err:  # noqa: BLE001 - 清除失败不影响业务响应
        logger.warning("前端缓存清除请求失败（%s）：%s", url, err)


def purge_frontend_page_cache(reason: str = "") -> None:
    """非阻塞触发一次前端页面缓存清除；同一事件循环内 fire-and-forget。"""
    url = resolve_purge_target()
    if url is None:
        return
    try:
        task = asyncio.create_task(_post_purge(url))
    except RuntimeError:
        # 无运行中的事件循环（例如同步上下文）：直接放弃，客户端纠偏兜底
        return
    task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
    if reason:
        logger.debug("已调度前端页面缓存清除：%s", reason)
