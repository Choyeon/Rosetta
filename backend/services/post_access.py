"""
文章可读性判定的单一来源。

文章详情端点（`backend/api/blog.py::get_post`）历史上把这套规则**内联**在自己函数体里，
而派生资源（评论、回复、留言引用）各自另写一份或干脆不写——表现就是"正文已按状态/密码
收口，但同一篇文章的评论口匿名直读"。本模块把那两条判据抽出来，供派生资源复用：

1. ``post_is_publicly_visible``：非 published 与"定时发布未到"的文章只有作者本人与
   staff/超管可读；对其他人**按不存在处理**（404，不是 403——承认存在即可枚举草稿 id）。
2. ``post_content_unlocked``：设了密码的文章，未带正确密码时对任何人都不放行
   （作者/staff 短路）。
3. ``is_private_post`` / ``private_posts_excluded``：``visibility="private"`` 的文章对外
   不存在。前两条判据管的是"这篇还没公开"，第三条管"作者主动把它收起来"——二者在
   status/密码都合规时才会分叉，所以私密档必须单独有一条判据，而集合口（列表 / RSS /
   sitemap / 归档 / 热榜 / 系列 / 推荐）要有能进 SQL 的谓词形态。

本模块还兼管**列表面的媒体三位**（``media_flags`` / ``post_media_flags``）的唯一产出点：
归档那一族走列投影（不实例化 Post）、热榜与推荐走 ORM 行，两边都要产出同一组键，
所以这个 helper 放在两边都能导入的底层，而不是某个 api 模块里（repository 反向 import
api 会成环）。

与文章详情端点的差异是刻意的：详情口对加密文章返回 200 并置
``is_password_protected=true``、正文留空，由客户端出解锁界面；派生资源没有"部分可见"
这种形态，只能整体给或不给。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import ColumnElement, and_, func

from backend.models.blog import Post

if TYPE_CHECKING:
    from backend.models.user import User

PRIVATE_VISIBILITY = "private"


def _ensure_aware(value: datetime | None) -> datetime | None:
    """无时区的时间一律按 UTC 解释（与 blog.py 同口径，避免 naive/aware 比较 TypeError）。"""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def is_private_post(post: Post) -> bool:
    """对象级私密判定；NULL/空串按 public 处理（迁移 0482c6771d47 之前留下的行）。"""
    return (getattr(post, "visibility", None) or "public") == PRIVATE_VISIBILITY


def media_flags(*, audio, video, video_url) -> dict[str, bool]:
    """
    列表面的「带不带音频 / 视频 / 嵌入」三位：键名与取值的唯一产出点。

    只带存在性，**不带地址**——列表载荷被更多缓存键位与更多消费方复用，带上路径等于把
    媒体文件名摊开；地址仍只有详情口回。三个键在响应模型里一律给默认值 `False`
    （载荷进响应缓存，新增**必填**字段等于让 TTL 内的旧载荷整口 500）。

    取值按参数而不是按 ORM 实例：`/blog/archive` 那一族走的是列投影（不实例化 Post），
    而热榜/推荐/相似走 ORM 行——两处都要产出同一组键，就不能只有一种入口。
    """
    return {
        "has_audio": bool(audio),
        "has_video": bool(video),
        "has_embed": bool(video_url),
    }


def post_media_flags(post: Post) -> dict[str, bool]:
    """ORM 行形态的便捷入口（列投影用 ``media_flags``）。

    每处各写一遍字段清单，正是批次 #118"创建口漏三列"的同一族错法，所以四个手写
    ``PostListItemLocalized`` 构造点、榜单口与归档口都走这里。``PostListItemLocalized.from_post``
    是同类的第五个构造点，但当前无调用方，靠模型默认值拿 False。
    """
    return media_flags(audio=post.audio, video=post.video, video_url=post.video_url)


def private_posts_excluded() -> ColumnElement[bool]:
    """
    集合级 SQL 谓词单源：匿名可见的文章集合必须排除 private。

    每条以 `Post.status == "published"` 圈定"对外存在"的文章的查询都必须叠上它，
    否则私密文章照常进列表、进 RSS、进 sitemap、进热榜。SQL 侧带不动"作者本人可见"
    这层身份语义——那是详情端点（``post_is_publicly_visible``）的职责；集合口一律
    按最保守的匿名视角排除，登录的作者要找回自己的私密稿走后台列表（staff 分支）。
    """
    return func.coalesce(Post.visibility, "public") != PRIVATE_VISIBILITY


def publicly_listable_posts() -> ColumnElement[bool]:
    """
    集合口（列表 / 归档 / RSS / sitemap / 热榜 / 推荐 / 相似）的完整匿名谓词。

    三条判据里最容易被漏的是**定时未到**那一条：`status == "published"` 是定时发布
    落库时的写法（`api/scheduled_posts.py`），所以"published 但 `published_at` 还在未来"
    是常态而不是脏数据。详情端点（``post_is_publicly_visible``）把它判成 404，
    前台主列表也带 `published_at <= now()`（`api/blog.py`）——只有派生集合口漏掉时，
    表现是"推荐位/热榜里点进去是 404"，而不是报错。

    只圈 status 的写法等于把另外两条判据交给调用方各自回忆，漏一处即成泄漏面，
    所以新增集合查询请直接用本函数，不要再手写 `Post.status == "published"`。

    "到点没有"必须拿 Python 侧的时刻判，不能用 SQL 的 `now()`：
    - SQLite 的 `CURRENT_TIMESTAMP` 只到**秒**，而 `published_at` 落库是带微秒的
      TEXT，同一秒内发布的文章按字符串比就大于这个"现在"——表现为刚点完发布，
      RSS/列表/热榜里这篇不存在，而这一份"少一篇"的快照还要缓存 300s。
    - PG 的 `now()` 是**事务开始**时刻，同一事务里刚写入的行同样判成"未到"。
      两侧都用 `datetime.now(UTC)`（带 tzinfo，渲染形态与写入侧一致）才是同一个时钟。
    """
    return and_(
        Post.status == "published",
        private_posts_excluded(),
        Post.published_at.is_(None) | (Post.published_at <= datetime.now(timezone.utc)),
    )


def _is_privileged(post: Post, current_user: User | None) -> bool:
    if current_user is None:
        return False
    return bool(
        current_user.id == post.author_id
        or getattr(current_user, "is_staff", False)
        or getattr(current_user, "is_superuser", False)
    )


def post_is_publicly_visible(post: Post, current_user: User | None) -> bool:
    """这篇文章对当前观看者是否"存在"。草稿/待审/未来定时/私密 → 仅作者与 staff。"""
    if _is_privileged(post, current_user):
        return True
    if post.status != "published":
        return False
    if is_private_post(post):
        return False
    published_at = _ensure_aware(getattr(post, "published_at", None))
    if published_at and published_at > datetime.now(timezone.utc):
        return False
    return True


async def post_content_unlocked(
    post: Post,
    current_user: User | None,
    provided_password: str | None = None,
) -> bool:
    """加密文章的密码闸门；未设密码恒 True。"""
    password_hash: Any = getattr(post, "password", None)
    if not password_hash:
        return True
    if _is_privileged(post, current_user):
        return True
    if not provided_password:
        return False
    from backend.core.auth import averify_password

    return await averify_password(provided_password, password_hash)
