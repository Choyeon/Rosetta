"""IndexNow 即时推送（文章发布/更新后通知搜索引擎，最小实现）。

执行点在 hooks 总线：``post.published`` / ``post.updated`` 触发后向
``https://api.indexnow.org/indexnow`` POST ``{host, key, urlList}``，
urlList 为该文章的四语 URL（zh 裸路径 + /en /ja /zh_Hant 前缀，
口径同 ``blog._locale_path_variants`` 的 sitemap 语言变体）。

红线：
- 开关与密钥来自站点设置 seo 分组（``indexnow_enabled`` / ``indexnow_key``），
  默认关闭、默认空——空 key 一律跳过，key 绝不硬编码、绝不进任何日志。
- 投递异步且不阻塞写路径：监听器只做同步取 slug + ``create_task``，
  绝不在 do_action 里 await HTTP（与 api/webhook.py 同族口径）。
- 失败静默：非 2xx / 网络异常只记 warning，不影响文章写请求。
- SSRF 护栏不适用：目标是写死的公网固定端点，不是用户提供的 URL。
"""

import asyncio
import logging
from typing import Any
from urllib.parse import urlparse

import httpx

from backend.core import hooks as _hooks
from backend.core.config import settings
from backend.services.site_settings import bool_of, read_group

logger = logging.getLogger(__name__)

INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
INDEXNOW_TIMEOUT = 10.0
# 非默认语言前缀（默认语言 zh 走裸路径，prefix_except_default 策略）
INDEXNOW_LOCALE_PREFIXES = ("en", "ja", "zh_Hant")

_push_tasks: set = set()  # 强引用：裸 create_task 的任务无引用时可能被 GC
_listeners: dict[str, Any] = {}


def build_post_url_list(slug: str, site_url: str) -> list[str]:
    """一篇文章的四语公开 URL：zh 裸路径在前，三个语言前缀变体随后。"""
    base = site_url.rstrip("/")
    return [f"{base}/posts/{slug}"] + [
        f"{base}/{code}/posts/{slug}" for code in INDEXNOW_LOCALE_PREFIXES
    ]


async def _send(payload: dict) -> int:
    """向 IndexNow POST 一次，返回状态码。异常向上传播，由调用方吞掉。"""
    async with httpx.AsyncClient(timeout=INDEXNOW_TIMEOUT) as client:
        resp = await client.post(INDEXNOW_ENDPOINT, json=payload)
    return resp.status_code


async def push_post_to_indexnow(slug: str) -> bool:
    """读取 seo 分组 → 组装 payload → 投递。返回是否真正发出了请求。

    跳过条件（都静默或只记不含密钥的 warning）：开关关闭、key 未配置、
    site_url 未配置（host 无法确定）。任何投递异常都不外泄。
    """
    cfg = await read_group("seo")
    if not bool_of(cfg, "indexnow_enabled", False):
        return False
    key = str(cfg.get("indexnow_key") or "").strip()
    if not key:
        logger.info("IndexNow 已启用但未配置 key，跳过推送")
        return False
    site_url = getattr(settings, "site_url", None) or ""
    host = urlparse(site_url).netloc
    if not host:
        logger.warning("IndexNow 跳过推送：site_url 未配置或不含主机名")
        return False

    payload = {"host": host, "key": key, "urlList": build_post_url_list(slug, site_url)}
    try:
        status_code = await _send(payload)
    except Exception as exc:  # noqa: BLE001 - 即时推送失败不得影响任何主流程
        # 只记异常本身；payload（含 key）绝不入日志。
        logger.warning("IndexNow 推送失败 slug=%s: %s", slug, exc)
        return False
    if status_code >= 400:
        logger.warning("IndexNow 推送返回 %s slug=%s", status_code, slug)
    return True


def _extract_slug(args: tuple, kwargs: dict) -> str | None:
    """从总线参数里取文章 slug。

    实体传法不统一（post.updated 按位置传 Post 对象、post.published 首位参数是
    post.id 而实体在 kwarg），因此 kwargs["post"] 优先，其次扫位置参数里第一个
    带非空 slug 属性的对象（int 的 post.id 拿不到 slug，自然被跳过）。
    只读 slug 一个属性，且在 do_action 的同步阶段读取——那时请求会话还活着，
    换成后台任务里再读就是 DetachedInstanceError。
    """
    candidates = [kwargs.get("post")] + list(args)
    for entity in candidates:
        slug = getattr(entity, "slug", None)
        if slug:
            return str(slug)
    return None


async def _on_post_event(*args: Any, **kwargs: Any) -> None:
    """总线回调：同步取 slug，排后台投递任务，绝不 await HTTP。"""
    slug = _extract_slug(args, kwargs)
    if not slug:
        return

    async def _run() -> None:
        try:
            await push_post_to_indexnow(slug)
        except Exception:  # noqa: BLE001 - 后台任务异常不得冒泡成未处理错误
            logger.exception("IndexNow 后台推送任务异常")

    task = asyncio.create_task(_run())
    _push_tasks.add(task)
    task.add_done_callback(_push_tasks.discard)


def register_indexnow_listeners() -> list[str]:
    """把 post.published / post.updated 挂到 hooks 总线。幂等：重复调用只补注册缺失的事件。"""
    registered: list[str] = []
    for event_type in ("post.published", "post.updated"):
        if event_type in _listeners:
            continue
        _hooks.add_action(event_type, _on_post_event)
        _listeners[event_type] = _on_post_event
        registered.append(event_type)
    return registered


def unregister_indexnow_listeners() -> list[str]:
    """注销总线回调（测试 teardown 用：全局钩子表会跨用例残留）。"""
    removed: list[str] = []
    for event_type, handler in list(_listeners.items()):
        _hooks.remove_action(event_type, handler)
        del _listeners[event_type]
        removed.append(event_type)
    return removed
