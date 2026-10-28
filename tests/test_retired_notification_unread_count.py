"""通知未读计数口退役后的守卫。

2026-10-28 删掉的是 ``GET /api/notifications/unread-count``：它与 ``GET /stats`` 是同一条
`WHERE recipient_id = ? AND is_read = false` 的 COUNT，而顶栏铃铛读的一直是 ``/stats``
（``useAdminManage.fetchNotificationStats`` 把 ``unread`` 归一成 ``unread_count``），
``/unread-count`` 从前端、插件、测试到后台文档都没有第二个读取方。
留着的代价不是"多一个接口"：它是**每次轮询都要单独打一发**的计数口，
接入方越多，铃铛越容易把同一个数字数两遍。

四条断言各自挡一种回归：
* 端点回到 OpenAPI / ``notification.py`` 多出同族计数路由（照旧文档"顺手补回来"）；
* 请求这个 URL 仍被当成可用口（有人用 `/{id}` 的 catch-all 兜出一条新路由）；
* 活路径 ``GET /stats`` 被一起删掉或不再回 ``unread``（那会把删僵尸做成删功能）；
* 退役没写进覆盖度文档（下一个人会当成缺口重接一遍）。

口径依据 AGENTS.md §7.4 第 4 条：核对路由存在性读**生成后的** ``app.openapi()["paths"]``，
不读 ``app.routes``（``_IncludedRouter`` 懒挂载会假通过）。
"""

from pathlib import Path

import pytest

from backend.api import notification as notification_module
from backend.main import app
from backend.models.core import Notification

REPO = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = REPO / "frontend"
USE_ADMIN_MANAGE = FRONTEND_ROOT / "composables" / "useAdminManage.ts"
COVERAGE_DOC = FRONTEND_ROOT / "docs" / "API_COVERAGE.md"
ENDPOINTS_DOC = REPO / "backend" / "docs" / "api_endpoints.md"
REFERENCE_DOC = REPO / "backend" / "docs" / "api_reference.md"

RETIRED_PATH = "/api/notifications/unread-count"


def _openapi_paths() -> set[str]:
    return set(app.openapi()["paths"].keys())


def test_retired_count_path_is_gone_from_openapi():
    paths = _openapi_paths()
    assert RETIRED_PATH not in paths, f"{RETIRED_PATH} 又出现了：未读计数由 /stats 单源承担"


def test_notification_module_has_no_second_counter_route():
    """/stats 是唯一的计数读口；多出一条计数路由要先说明它有没有读取方。

    列表口在 router 上的 path 是空串（`@router.get("/")` 与 APIRouter 默认前缀合并的结果），
    写断言时按实测形态列全，不要用 `"/"` 去猜。
    """
    declared = sorted({route.path for route in notification_module.router.routes})
    assert declared == [
        "",
        "/read-all",
        "/stats",
        "/ws",
        "/{notification_id}",
        "/{notification_id}/read",
    ], f"notification.py 的路由清单变成了 {declared}"


@pytest.mark.asyncio
async def test_requesting_the_retired_url_does_not_return_a_count(client, auth_headers):
    """登录态请求旧 URL 必须拿不到 unread_count（405 可接受：路径被 DELETE 口接住）。"""
    resp = await client.get(RETIRED_PATH, headers=auth_headers)
    assert resp.status_code != 200, f"旧计数口仍可返回 200：{resp.text[:200]}"
    assert "unread_count" not in resp.text


@pytest.mark.asyncio
async def test_stats_still_answers_the_badge_with_real_rows(
    client, db_session, test_user, staff_user, auth_headers
):
    """活路径必须在：铃铛只剩这一个数字来源，删它等于把角标做成常量 0。"""
    db_session.add_all(
        [
            Notification(
                recipient_id=test_user.id,
                actor_id=staff_user.id,
                verb="reply",
                title={"zh": "守卫"},
                message={"zh": "未读"},
                is_read=False,
            ),
            Notification(
                recipient_id=test_user.id,
                actor_id=staff_user.id,
                verb="like",
                title={"zh": "守卫"},
                message={"zh": "已读"},
                is_read=True,
            ),
        ]
    )
    await db_session.commit()

    resp = await client.get("/api/notifications/stats", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["unread"] == 1
    assert body["total"] == 2
    assert body["read"] == 1
    # verb 分组是 /stats 独有的另一半，/unread-count 从来给不出这个
    assert body["type_distribution"] == {"reply": 1, "like": 1}


def test_live_frontend_adapter_still_normalizes_stats():
    text = USE_ADMIN_MANAGE.read_text(encoding="utf-8")
    assert "/notifications/stats" in text, "铃铛不再读 /stats，未读数没有来源了"
    assert "unread_count: num(s.unread_count ?? s.unread ?? 0)" in text, (
        "fetchNotificationStats 归一被改：/stats 的 unread 键到不了页面"
    )
    assert "unread-count" not in text, "前端又去请求退役的 /unread-count 口了"


@pytest.mark.parametrize("doc", [ENDPOINTS_DOC, REFERENCE_DOC], ids=["endpoints", "reference"])
def test_generated_docs_no_longer_advertise_the_retired_endpoint(doc):
    """生成后的 OpenAPI 文档不得再列这条口（覆盖度文档例外——它要写下退役决定）。"""
    assert RETIRED_PATH not in doc.read_text(encoding="utf-8"), (
        f"{doc.name} 还在列 {RETIRED_PATH}——文档里的僵尸口会被当成缺口重接"
    )


def test_coverage_doc_records_the_retirement():
    assert "退役" in COVERAGE_DOC.read_text(encoding="utf-8")
