"""
投票管理 API

提供投票创建、参与和结果查看功能。
"""

import math

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.core.auth import DB, CurrentStaff, CurrentUserOptional
from backend.models.voting import Choice, Poll, Vote
from backend.schemas import (
    BaseResponse,
    PaginatedResponse,
    PollCreate,
    PollResponse,
    VoteCreate,
)

router = APIRouter(tags=["投票"])


@router.get(
    "/polls",
    response_model=PaginatedResponse,
    summary="投票列表",
    description="获取投票列表，可按状态筛选。",
)
async def list_polls(
    db: DB,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(12, ge=1, le=100, description="每页数量"),
    is_active: bool | None = Query(None, description="是否进行中"),
):
    """获取投票列表

    优化：批量获取投票统计数据，避免 N+1 查询
    """
    query = select(Poll).options(selectinload(Poll.choices))

    if is_active is not None:
        query = query.where(Poll.is_active == is_active)

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

    items = []
    for poll in polls:
        stats = poll_stats.get(poll.id, {"total": 0, "choices": {}})

        choices_data = [
            {
                "id": choice.id,
                "text": choice.text,
                "order": choice.order,
                "votes_count": stats["choices"].get(choice.id, 0),
            }
            for choice in poll.choices
        ]

        items.append(
            PollResponse(
                id=poll.id,
                title=poll.title,
                description=poll.description,
                is_active=poll.is_active,
                allow_multiple=poll.allow_multiple,
                show_results=poll.show_results,
                choices=choices_data,
                total_votes=stats["total"],
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
    description="获取投票详情和各选项票数。",
)
async def get_poll(poll_id: int, db: DB):
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

    # 统计各选项票数
    choices_data = []
    for choice in poll.choices:
        votes_count = await db.scalar(select(func.count()).where(Vote.choice_id == choice.id)) or 0
        choices_data.append(
            {
                "id": choice.id,
                "text": choice.text,
                "order": choice.order,
                "votes_count": votes_count,
            }
        )

    return PollResponse(
        id=poll.id,
        title=poll.title,
        description=poll.description,
        is_active=poll.is_active,
        allow_multiple=poll.allow_multiple,
        show_results=poll.show_results,
        choices=choices_data,
        total_votes=total_votes,
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
    poll = Poll(
        title=data.title,
        description=data.description,
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


@router.post(
    "/polls/{poll_id}/vote",
    response_model=BaseResponse,
    summary="参与投票",
    description="提交投票选择，支持匿名投票。",
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
