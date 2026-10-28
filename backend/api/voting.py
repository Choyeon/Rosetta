"""
投票管理 API

提供投票创建、参与和结果查看功能。
"""

import math

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.auth import DB, CurrentStaff, CurrentUserOptional
from backend.core.partial_update import apply_partial_update
from backend.models.blog import Post
from backend.models.voting import Choice, Poll, Vote
from backend.schemas import (
    BaseResponse,
    PaginatedResponse,
    PollCreate,
    PollResponse,
    PollUpdate,
    VoteCreate,
)

router = APIRouter(tags=["投票"])


async def _ensure_post_exists(db: AsyncSession, post_id: int | None) -> None:
    """校验绑定的文章真的存在。

    不校验的话，PG 会在 flush 时抛外键 IntegrityError → 整条请求 500，而管理员看到的
    是"保存失败，未知错误"；SQLite 测试库不强制外键，同一段代码在 CI 里是绿的。
    """
    if post_id is None:
        return
    found = (await db.execute(select(Post.id).where(Post.id == post_id).limit(1))).first()
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="绑定的文章不存在",
        )


@router.get(
    "/polls",
    response_model=PaginatedResponse,
    summary="投票列表",
    description=(
        "获取投票列表，可按状态筛选。"
        "`post_id` 按文章筛选：只返回**这篇文章的专属投票 + 全站投票**（`post_id IS NULL`）， "
        "其它文章的专属投票不会出现。"
    ),
)
async def list_polls(
    db: DB,
    current_user: CurrentUserOptional = None,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(12, ge=1, le=100, description="每页数量"),
    is_active: bool | None = Query(None, description="是否进行中"),
    post_id: int | None = Query(None, ge=1, description="绑定文章的 ID；不过滤则返回全部"),
):
    """获取投票列表

    优化：批量获取投票统计数据，避免 N+1 查询。

    show_results 闸门：当 poll.show_results=False 时，对非 staff/superuser 隐藏 votes_count / total_votes。
    """
    query = select(Poll).options(selectinload(Poll.choices))

    if is_active is not None:
        query = query.where(Poll.is_active == is_active)

    if post_id is not None:
        query = query.where(or_(Poll.post_id == post_id, Poll.post_id.is_(None)))

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Poll.created_at.desc())
    result = await db.execute(query)
    polls = result.scalars().unique().all()

    if polls:
        poll_ids = [p.id for p in polls]

        vote_counts = await db.execute(
            select(
                Vote.poll_id,
                Vote.choice_id,
                func.count().label("count"),
            )
            .where(Vote.poll_id.in_(poll_ids))
            .group_by(Vote.poll_id, Vote.choice_id)
        )

        poll_stats: dict[int, dict] = {}
        for row in vote_counts:
            if row.poll_id not in poll_stats:
                poll_stats[row.poll_id] = {"total": 0, "choices": {}}
            poll_stats[row.poll_id]["total"] += row.count
            poll_stats[row.poll_id]["choices"][row.choice_id] = row.count
    else:
        poll_stats = {}

    is_privileged = bool(
        current_user
        and (
            getattr(current_user, "is_staff", False) or getattr(current_user, "is_superuser", False)
        )
    )

    items = []
    for poll in polls:
        stats = poll_stats.get(poll.id, {"total": 0, "choices": {}})

        # show_results 闸门：非特权用户看不到票数
        can_see_results = poll.show_results or is_privileged

        choices_data = [
            {
                "id": choice.id,
                "text": choice.text,
                "order": choice.order,
                "votes_count": stats["choices"].get(choice.id, 0) if can_see_results else None,
            }
            for choice in poll.choices
        ]

        items.append(
            PollResponse(
                id=poll.id,
                title=poll.title,
                description=poll.description,
                post_id=poll.post_id,
                is_active=poll.is_active,
                allow_multiple=poll.allow_multiple,
                show_results=poll.show_results,
                choices=choices_data,
                total_votes=stats["total"] if can_see_results else 0,
                created_at=poll.created_at,
            )
        )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get(
    "/polls/{poll_id}",
    response_model=PollResponse,
    summary="投票详情",
    description="获取投票详情和各选项票数。show_results=False 时对非 staff/superuser 隐藏票数。",
)
async def get_poll(poll_id: int, db: DB, current_user: CurrentUserOptional = None):
    """获取投票详情"""
    result = await db.execute(
        select(Poll).options(selectinload(Poll.choices)).where(Poll.id == poll_id)
    )
    poll = result.scalar_one_or_none()

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="投票不存在",
        )

    # 统计总票数
    total_votes = await db.scalar(select(func.count()).where(Vote.poll_id == poll.id)) or 0

    # 各选项票数：与 GET /polls 列表口径一致，一次 GROUP BY 取代逐选项 COUNT
    vote_rows = await db.execute(
        select(Vote.choice_id, func.count()).where(Vote.poll_id == poll.id).group_by(Vote.choice_id)
    )
    votes_by_choice = {int(choice_id): int(count) for choice_id, count in vote_rows.all()}

    # show_results 闸门：非特权用户看不到票数
    is_privileged = bool(
        current_user
        and (
            getattr(current_user, "is_staff", False) or getattr(current_user, "is_superuser", False)
        )
    )
    can_see_results = poll.show_results or is_privileged

    choices_data = [
        {
            "id": choice.id,
            "text": choice.text,
            "order": choice.order,
            "votes_count": votes_by_choice.get(choice.id, 0) if can_see_results else None,
        }
        for choice in poll.choices
    ]

    return PollResponse(
        id=poll.id,
        title=poll.title,
        description=poll.description,
        post_id=poll.post_id,
        is_active=poll.is_active,
        allow_multiple=poll.allow_multiple,
        show_results=poll.show_results,
        choices=choices_data,
        total_votes=total_votes if can_see_results else 0,
        created_at=poll.created_at,
    )


@router.post(
    "/polls",
    response_model=PollResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建投票",
    description="创建新投票，需要管理员权限。",
)
async def create_poll(data: PollCreate, current_user: CurrentStaff, db: DB):
    """创建投票"""
    await _ensure_post_exists(db, data.post_id)
    poll = Poll(
        title=data.title,
        description=data.description,
        post_id=data.post_id,
        is_active=data.is_active,
        allow_multiple=data.allow_multiple,
        show_results=data.show_results,
    )
    db.add(poll)
    await db.flush()

    # 创建选项
    for idx, text in enumerate(data.choices):
        choice = Choice(poll_id=poll.id, text=text, order=idx)
        db.add(choice)

    await db.flush()

    return await get_poll(poll.id, db)


@router.put(
    "/polls/{poll_id}",
    response_model=PollResponse,
    summary="更新投票",
    description=(
        "更新投票的标题/说明/绑定文章与三个开关，需要管理员权限。"
        "只写入请求体里**实际出现**的键（缺省键保持原值），所以"
        '「结束投票」提交 `{"is_active": false}` 即可，不会顺带清掉说明。'
        "选项不可改：每个选项 id 上挂着 votes 行，替换选项等于删票数。"
    ),
)
async def update_poll(poll_id: int, data: PollUpdate, current_user: CurrentStaff, db: DB):
    """更新投票（显式写值，不做服务端翻转）

    刻意用 PUT 而不是 `POST /polls/{id}/toggle`：翻转语义在重试、双击、两个管理员
    并发时不收敛（一次重放就得到相反状态），而显式写值幂等。

    写回走全仓同一条 `apply_partial_update`：只提交了的键才写，且显式 null 落在
    NOT NULL 列（title / is_active 这类）上会被拦成 422，而不是 setattr 后一路
    flush 出 IntegrityError → 500。
    """
    result = await db.execute(select(Poll).where(Poll.id == poll_id))
    poll = result.scalar_one_or_none()

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="投票不存在",
        )

    update_data = data.model_dump(exclude_unset=True)
    if "post_id" in update_data:
        await _ensure_post_exists(db, update_data["post_id"])
    apply_partial_update(poll, update_data)

    await db.flush()

    return await get_poll(poll.id, db)


@router.post(
    "/polls/{poll_id}/vote",
    response_model=BaseResponse,
    summary="参与投票",
    description=(
        "提交投票选择，支持匿名投票。**已登录用户每人一票**：重复提交返回 409。"
        "匿名请求没有稳定标识（``ip_address`` 列存在但本路径不采集），仍按次放行。"
    ),
)
async def cast_vote(
    poll_id: int,
    data: VoteCreate,
    db: DB,
    current_user: CurrentUserOptional = None,
):
    """参与投票"""
    # 检查投票是否存在
    result = await db.execute(select(Poll).where(Poll.id == poll_id))
    poll = result.scalar_one_or_none()

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="投票不存在",
        )

    # 检查是否进行中
    if not poll.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="投票已结束",
        )

    # 已登录用户不得重复参与：原先这条路径**完全没有**查重，同一账号可以无限次提交，
    # 每次都在 votes 表里追加行，票数统计因此可被单个用户任意拉高（votes 表上也没有
    # (poll_id, user_id) 唯一约束，匿名票 user_id 为 NULL 更是无法用唯一约束表达）。
    # 因此护栏只能落在写入口：匿名请求仍按现状放行（ip_address 未采集，无稳定标识可用）。
    if current_user is not None:
        voted = (
            await db.execute(
                select(Vote.id)
                .where(Vote.poll_id == poll_id, Vote.user_id == current_user.id)
                .limit(1)
            )
        ).first()
        if voted:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="您已参与过该投票",
            )

    # 检查是否多选
    if not poll.allow_multiple and len(data.choice_ids) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该投票只能选择一个选项",
        )

    # 验证选项是否有效
    choices_result = await db.execute(
        select(Choice).where(Choice.id.in_(data.choice_ids), Choice.poll_id == poll_id)
    )
    choices = list(choices_result.scalars().all())

    if len(choices) != len(data.choice_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="部分选项不存在",
        )

    # 记录投票
    for choice in choices:
        vote = Vote(
            poll_id=poll_id,
            choice_id=choice.id,
            user_id=current_user.id if current_user else None,
        )
        db.add(vote)

    return BaseResponse(message="投票成功")


@router.delete(
    "/polls/{poll_id}",
    response_model=BaseResponse,
    summary="删除投票",
    description="删除投票，需要管理员权限。",
)
async def delete_poll(poll_id: int, current_user: CurrentStaff, db: DB):
    """删除投票"""
    result = await db.execute(select(Poll).where(Poll.id == poll_id))
    poll = result.scalar_one_or_none()

    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="投票不存在",
        )

    await db.delete(poll)
    return BaseResponse(message="投票已删除")
