"""私信会话列表与投票详情的聚合正确性。

两处端点原先都在循环里逐条 COUNT（会话数 / 选项数个查询），已改为一次 GROUP BY。
本文件锁住改写后的语义：**按对端分别计数、只数未读、读过的不计**，
并让投票详情与列表走同一份统计口径（两端结果必须一致）。
"""

from __future__ import annotations

import ast
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.message import PrivateMessage
from backend.models.user import User

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BASE_TIME = datetime(2026, 1, 1, 12, 0, 0)


def _model_class_names() -> set[str]:
    """backend/models 下所有声明式模型类名（不导入运行期，纯 AST）。"""
    names: set[str] = set()
    for py in (_REPO_ROOT / "backend" / "models").rglob("*.py"):
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ClassDef):
                names.add(node.name)
    return names


def test_no_python_not_applied_to_model_columns():
    """静态护栏：``not Model.column`` 不是取反，SQLAlchemy 会把整个 WHERE 塌成
    ``WHERE false`` 并且**不报错**（本仓库曾在 5 处查询里踩中，未读数/待审数恒 0）。
    正确写法是 ``Model.column.is_(False)`` 或 ``~expr``。
    """
    models = _model_class_names()
    offenders: list[str] = []
    for py in (_REPO_ROOT / "backend").rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.UnaryOp) or not isinstance(node.op, ast.Not):
                continue
            operand = node.operand
            if (
                isinstance(operand, ast.Attribute)
                and isinstance(operand.value, ast.Name)
                and operand.value.id in models
            ):
                rel = py.relative_to(_REPO_ROOT).as_posix()
                offenders.append(f"{rel}:{node.lineno} not {operand.value.id}.{operand.attr}")
    assert offenders == [], "SQL 谓词改用 .is_(False) / ~expr：\n" + "\n".join(offenders)


async def _seed_thread(
    db: AsyncSession, *, me: User, peer: User, unread: int, read: int, replied: bool
) -> None:
    """构造 me 与 peer 的一串私信：peer→me 的 ``unread`` 未读 + ``read`` 已读。"""
    seq = 0
    for _ in range(unread):
        seq += 1
        db.add(
            PrivateMessage(
                sender_id=peer.id,
                recipient_id=me.id,
                content=f"{peer.username} 发来的未读 {seq}",
                is_read=False,
                created_at=_BASE_TIME + timedelta(minutes=seq),
            )
        )
    for _ in range(read):
        seq += 1
        db.add(
            PrivateMessage(
                sender_id=peer.id,
                recipient_id=me.id,
                content=f"{peer.username} 发来的已读 {seq}",
                is_read=True,
                created_at=_BASE_TIME + timedelta(minutes=seq),
            )
        )
    if replied:
        seq += 1
        db.add(
            PrivateMessage(
                sender_id=me.id,
                recipient_id=peer.id,
                content=f"我回复 {peer.username}",
                is_read=True,
                created_at=_BASE_TIME + timedelta(minutes=seq),
            )
        )
    await db.commit()


@pytest.mark.asyncio
async def test_conversations_unread_count_grouped_per_peer(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    admin_user: User,
    staff_user: User,
    auth_headers: dict,
):
    """未读数按对端分别统计：不能把所有发件人合并成一个总数。"""
    await _seed_thread(db_session, me=test_user, peer=admin_user, unread=3, read=1, replied=True)
    await _seed_thread(db_session, me=test_user, peer=staff_user, unread=1, read=2, replied=False)

    resp = await client.get("/api/messages/conversations", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]

    by_name = {c["user"]["username"]: c for c in items}
    assert set(by_name) == {admin_user.username, staff_user.username}
    assert by_name[admin_user.username]["unread_count"] == 3
    assert by_name[staff_user.username]["unread_count"] == 1
    # 最近一条是我发出的 ⇒ 会话仍在列表里，且 is_mine 为真
    assert by_name[admin_user.username]["last_message"]["is_mine"] is True
    assert by_name[staff_user.username]["last_message"]["is_mine"] is False

    # 分页此前被完全忽略（page/page_size 收了不用）：现在 total 是全量、items 是本页
    paged = await client.get("/api/messages/conversations?page=1&page_size=1", headers=auth_headers)
    assert paged.status_code == 200, paged.text
    page_body = paged.json()
    page_items = page_body["items"]
    assert len(page_items) == 1
    assert page_body["total"] == 2
    assert page_body["total_pages"] == 2
    # admin 线程最后一条时间最晚，倒序首页应是它
    assert page_items[0]["user"]["username"] == admin_user.username


@pytest.mark.asyncio
async def test_conversations_empty_for_user_without_messages(
    client: AsyncClient, auth_headers: dict
):
    """无任何私信的账号：会话列表应为空数组，而不是缺 key 或 null。"""
    resp = await client.get("/api/messages/conversations", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_poll_detail_votes_per_choice_matches_list(client: AsyncClient, admin_headers: dict):
    """投票详情按选项计票：逐选项 COUNT 换成 GROUP BY 后计数不得串选项/丢选项。"""
    create = await client.post(
        "/api/voting/polls",
        json={
            "title": "选一个框架",
            "choices": ["FastAPI", "Nuxt", "Both"],
            "allow_multiple": True,
        },
        headers=admin_headers,
    )
    assert create.status_code == 201, create.text
    poll = create.json()
    poll_id = poll["id"]
    choice_ids = [c["id"] for c in poll["choices"]]
    assert len(choice_ids) == 3

    # 刻意走匿名投票：本接口对已登录用户是「每人一票」（见
    # test_logged_in_user_cannot_vote_twice），用 admin_headers 连投就是在测旧缺陷。
    for _ in range(2):
        vote = await client.post(
            f"/api/voting/polls/{poll_id}/vote",
            json={"choice_ids": [choice_ids[0]]},
        )
        assert vote.status_code == 200, vote.text
    vote = await client.post(
        f"/api/voting/polls/{poll_id}/vote",
        json={"choice_ids": [choice_ids[1], choice_ids[2]]},
    )
    assert vote.status_code == 200, vote.text

    detail = await client.get(f"/api/voting/polls/{poll_id}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["total_votes"] == 4
    assert [c["votes_count"] for c in body["choices"]] == [2, 1, 1]

    listing = await client.get("/api/voting/polls?page=1&page_size=100")
    assert listing.status_code == 200, listing.text
    page = listing.json()
    listed = next(p for p in page["items"] if p["id"] == poll_id)
    assert [c["votes_count"] for c in listed["choices"]] == [2, 1, 1]
    assert listed["total_votes"] == body["total_votes"]


async def _mk_poll(client, admin_headers):
    create = await client.post(
        "/api/voting/polls",
        json={"title": "一人一票验证", "choices": ["甲", "乙"], "allow_multiple": False},
        headers=admin_headers,
    )
    assert create.status_code == 201, create.text
    body = create.json()
    return body["id"], [c["id"] for c in body["choices"]]


@pytest.mark.asyncio
async def test_poll_logged_in_user_cannot_vote_twice(client: AsyncClient, admin_headers: dict):
    """同一登录账号重复投票：原先**完全没有查重**，票数可被单账号任意拉高。"""
    poll_id, choice_ids = await _mk_poll(client, admin_headers)

    first = await client.post(
        f"/api/voting/polls/{poll_id}/vote",
        json={"choice_ids": [choice_ids[0]]},
        headers=admin_headers,
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        f"/api/voting/polls/{poll_id}/vote",
        json={"choice_ids": [choice_ids[1]]},
        headers=admin_headers,
    )
    assert second.status_code == 409, second.text

    detail = await client.get(f"/api/voting/polls/{poll_id}")
    body = detail.json()
    assert body["total_votes"] == 1
    assert [c["votes_count"] for c in body["choices"]] == [1, 0]


@pytest.mark.asyncio
async def test_poll_anonymous_voting_still_per_call(client: AsyncClient, admin_headers: dict):
    """护栏只覆盖可识别用户：匿名没有稳定标识（ip_address 未采集），仍按次放行。"""
    poll_id, choice_ids = await _mk_poll(client, admin_headers)

    for _ in range(2):
        vote = await client.post(
            f"/api/voting/polls/{poll_id}/vote",
            json={"choice_ids": [choice_ids[0]]},
        )
        assert vote.status_code == 200, vote.text

    detail = await client.get(f"/api/voting/polls/{poll_id}")
    assert detail.json()["total_votes"] == 2
