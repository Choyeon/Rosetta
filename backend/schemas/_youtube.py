"""YouTube 视频 ID 的解析单源（写入口与渲染侧都按这一份判定）。

放在叶子模块而不是 `hero.py`，是因为现在有两个定义期取值的消费方：
`hero.py`（轮播 `media_type=youtube` 的搭配校验）与 `schemas/__init__.py`（文章
`video_url` 的写入口校验）。后者正在执行包 `__init__`，反向 import 兄弟模块会把
它的整条依赖链（`strict_config` 等）拖进包初始化期。

`frontend/lib/hero-media.ts::extractYoutubeId` 是同一口径的前端副本（渲染侧不能信
库里的字段形态：导入 ZIP 与直连 SQL 都能塞进任意串），两份必须一起改。
"""

import re
from urllib.parse import parse_qs, urlsplit

# YouTube 视频 ID 固定 11 个字符（base64url 字符集）
_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_HOSTS = {"youtube.com", "m.youtube.com", "youtube-nocookie.com", "youtu.be"}


def extract_youtube_id(url: str | None) -> str | None:
    """从常见 YouTube 地址形态里取视频 ID；解析不出来回 None。

    支持裸 ID、youtu.be/<id>、watch?v=<id>、/embed/<id>、/shorts/<id>、/live/<id>。
    写口用它拒绝不可嵌入的地址；读侧（前端 `lib/hero-media.ts` 同口径）对历史脏数据
    回落封面图 / 不渲染播放器，不因为一条坏链接让整页 500。
    """
    if not url:
        return None
    candidate = url.strip()
    if _YOUTUBE_ID_RE.match(candidate):
        return candidate
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host.removeprefix("www.")
    if host not in _YOUTUBE_HOSTS:
        return None
    if host == "youtu.be":
        vid = parsed.path.lstrip("/").split("/")[0]
        return vid if _YOUTUBE_ID_RE.match(vid) else None
    if parsed.path.rstrip("/") == "/watch":
        vid = (parse_qs(parsed.query).get("v") or [""])[0]
        return vid if _YOUTUBE_ID_RE.match(vid) else None
    for prefix in ("/embed/", "/shorts/", "/live/", "/v/"):
        if parsed.path.startswith(prefix):
            vid = parsed.path[len(prefix) :].split("/")[0]
            return vid if _YOUTUBE_ID_RE.match(vid) else None
    return None
