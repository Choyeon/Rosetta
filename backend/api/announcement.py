"""
公告 API

提供公开接口获取当前活跃公告，以及管理员接口管理公告 CRUD。

路由设计：
- 公开接口: GET /api/announcements
- 管理接口: /api/admin/announcements (GET/POST/PUT/DELETE/toggle)

三条容易被漏掉的横切约束，改动本文件时别只盯着 CRUD：

1. **前台页面缓存必须一起失效。** 公告条渲染在 `layouts/default.vue`，也就是
   **每一个**前台页面的 SSR HTML 里；Nitro routeRules 对这些页面做了 swr 300~3600s
   缓存。写操作不调 `purge_frontend_page_cache()` 的话，管理员发布公告后访客最长
   一小时仍看到旧的那批（新建的甚至完全不出现）。设置页 notice 分组保存时已经这么
   做了，公告侧补上才不会"同一条横幅两个来源两种生效速度"。
2. **公开接口有后端缓存，写操作必须失效。** 该接口在每个 SSR 首屏都被 await，
   不加缓存等于每次首屏一次全表扫描；加了不失效就是"改了公告前台不刷新"。
3. **写路径必须发钩子。** 与文章/评论同构，插件与 Webhook 外发的唯一触发源
   就是这里的 `bus.do_action`，事件名同步登记在 `api/webhook.py::WEBHOOK_EVENTS`。
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from backend.core.auth import DB, CurrentStaff
from backend.core.cache import cache, make_cache_key
from backend.core.exceptions import ValidationException
from backend.core.partial_update import apply_partial_update
from backend.core.plugin_bus import bus
from backend.models.announcement import Announcement
from backend.schemas import BaseResponse
from backend.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementResponse,
    AnnouncementUpdate,
    ensure_utc,
)
from backend.services.frontend_cache_purge import purge_frontend_page_cache
from backend.utils.compat import UTC

router = APIRouter(tags=["公告"])

# 公开列表缓存。公告是站点级低频变更内容，但每个首屏都要读；60s 是"管理员改完
# 最坏 60s 内生效"与"别让首屏每次都打库"之间的折中——真正的即时生效靠下面的
# purge_frontend_page_cache 清 Nitro 的 HTML 缓存。
ANNOUNCEMENTS_CACHE_TTL = 60


def _announcements_cache_key() -> str:
    return make_cache_key("announcements", "active")


async def _invalidate_announcements_cache() -> None:
    try:
        await cache.delete(_announcements_cache_key())
    except Exception:  # noqa: BLE001 - 缓存不可用时不能让写操作失败
        # 与 settings_groups 同口径：缓存后端挂掉只影响性能，不影响正确性。
        pass


def _purge(reason: str) -> None:
    """写操作后清前台 SSR 页面缓存（fire-and-forget，见模块文档第 1 条）。"""
    purge_frontend_page_cache(f"公告变更: {reason}")


def _validate_window(start_time: datetime | None, end_time: datetime | None) -> None:
    """部分更新场景下不能只靠 schema：库里的旧值它看不到。

    只提交 end_time 时，`end <= start` 在 schema 层根本无从判断，而结果同样是
    "公告被存下来却永远不会下发"。合并库里的现值再判一次。

    两端都必须先 `ensure_utc`：**SQLite 回读的是朴素 datetime**（列的
    `timezone=True` 对它无效），而入参已被 schema 补成带 tz 的 UTC，直接比会抛
    `can't compare offset-naive and offset-aware datetimes` → 500。
    """
    start = ensure_utc(start_time)
    end = ensure_utc(end_time)
    if start and end and end <= start:
        raise ValidationException(
            message="结束时间必须晚于开始时间",
            details={"fields": ["start_time", "end_time"]},
        )


# ==================== 公开接口 ====================


@router.get(
    "/announcements",
    response_model=list[AnnouncementResponse],
    summary="获取当前活跃公告",
    description=(
        "获取当前时间范围内处于激活状态的公告列表，按 sort_order 升序排列。"
        "结果缓存 60 秒，公告写操作会立即失效缓存。"
    ),
)
async def list_active_announcements(db: DB):
    """获取当前生效的公告（公开接口）"""
    cache_key = _announcements_cache_key()
    cached = await cache.get(cache_key)
    if cached is not None:
        # 存进去的是 model_dump(mode="json") 的纯 JSON 结构（Redis 后端要求可序列化），
        # response_model 会把它重新校验成 AnnouncementResponse。
        return cached

    now = datetime.now(UTC)

    query = (
        select(Announcement)
        .where(Announcement.is_active.is_(True))
        .where((Announcement.start_time.is_(None)) | (Announcement.start_time <= now))
        .where((Announcement.end_time.is_(None)) | (Announcement.end_time >= now))
        .order_by(Announcement.sort_order.asc(), Announcement.created_at.desc())
    )

    result = await db.execute(query)
    rows = [AnnouncementResponse.model_validate(a) for a in result.scalars().all()]
    try:
        await cache.set(
            cache_key,
            [r.model_dump(mode="json") for r in rows],
            ttl=ANNOUNCEMENTS_CACHE_TTL,
        )
    except Exception:  # noqa: BLE001 - 缓存写失败不该让首屏 500
        pass
    return rows


# ==================== 管理接口


@router.get(
    "/admin/announcements",
    response_model=list[AnnouncementResponse],
    summary="管理员获取所有公告",
    description=(
        "管理员获取所有公告列表，支持按激活状态过滤。"
        "注意：本端点有意返回全量裸列表（不分页）——前端 fetchAdminManage/announcements 页"
        "按 list 结构消费且未实现分页器；page/page_size 参数不会被接受或生效。"
    ),
)
async def admin_list_announcements(
    db: DB,
    current_user: CurrentStaff,
    is_active: bool | None = Query(None, description="按激活状态过滤"),
):
    """管理员获取所有公告

    公告总量极小（站点级运营内容），且现有前端调用方（useAdminManage.ts 的
    fetchAdminAnnouncements 与 announcements.vue）都按裸 list 消费并自行包装
    AdminPaged 结构；改为 {items,total,...} 分页对象会直接破坏这些调用方，
    因此保持不分页的全量列表契约。
    """
    query = select(Announcement).order_by(
        Announcement.sort_order.asc(), Announcement.created_at.desc()
    )

    if is_active is not None:
        query = query.where(Announcement.is_active == is_active)

    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/admin/announcements",
    response_model=AnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建公告",
    description="管理员创建新公告。",
)
async def create_announcement(
    data: AnnouncementCreate,
    db: DB,
    current_user: CurrentStaff,
):
    """创建公告"""
    announcement = Announcement(
        title=data.title,
        content=data.content,
        type=data.type,
        is_active=data.is_active,
        is_dismissible=data.is_dismissible,
        start_time=data.start_time,
        end_time=data.end_time,
        sort_order=data.sort_order,
    )
    db.add(announcement)
    await db.flush()
    await db.refresh(announcement)

    response = AnnouncementResponse.model_validate(announcement)
    await bus.do_action("announcement.created", announcement, current_user=current_user, db=db)
    await _invalidate_announcements_cache()
    _purge("create")
    return response


@router.put(
    "/admin/announcements/{announcement_id}",
    response_model=AnnouncementResponse,
    summary="更新公告",
    description="管理员更新指定公告。",
)
async def update_announcement(
    announcement_id: int,
    data: AnnouncementUpdate,
    db: DB,
    current_user: CurrentStaff,
):
    """更新公告"""
    announcement = await db.get(Announcement, announcement_id)

    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公告不存在",
        )

    update_data = data.model_dump(exclude_unset=True)
    # 合并后校验：只传 end_time（或只传 start_time）时，窗口倒挂在 schema 层判不出来。
    _validate_window(
        update_data.get("start_time", announcement.start_time),
        update_data.get("end_time", announcement.end_time),
    )
    apply_partial_update(announcement, update_data)

    await db.flush()
    await db.refresh(announcement)

    response = AnnouncementResponse.model_validate(announcement)
    await bus.do_action("announcement.updated", announcement, current_user=current_user, db=db)
    await _invalidate_announcements_cache()
    _purge("update")
    return response


@router.delete(
    "/admin/announcements/{announcement_id}",
    response_model=BaseResponse,
    summary="删除公告",
    description="管理员删除指定公告。",
)
async def delete_announcement(
    announcement_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """删除公告"""
    announcement = await db.get(Announcement, announcement_id)

    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公告不存在",
        )

    await db.delete(announcement)
    await db.flush()

    await bus.do_action("announcement.deleted", announcement, current_user=current_user, db=db)
    await _invalidate_announcements_cache()
    _purge("delete")
    return BaseResponse(message="公告已删除")


@router.put(
    "/admin/announcements/{announcement_id}/toggle",
    response_model=AnnouncementResponse,
    summary="切换公告激活状态",
    description="管理员切换公告的激活状态。",
)
async def toggle_announcement(
    announcement_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """切换公告激活状态"""
    announcement = await db.get(Announcement, announcement_id)

    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公告不存在",
        )

    announcement.is_active = not announcement.is_active
    await db.flush()
    await db.refresh(announcement)

    response = AnnouncementResponse.model_validate(announcement)
    await bus.do_action("announcement.updated", announcement, current_user=current_user, db=db)
    await _invalidate_announcements_cache()
    _purge("toggle")
    return response
