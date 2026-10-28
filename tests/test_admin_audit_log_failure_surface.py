"""审计日志「失败操作」面的读写两端守卫。

这一族此前的形状：``OperationLog.status`` / ``error_code`` 由
``core/logging_middleware.py::log_operation`` **真实写入**（登录失败=AUTH_INVALID_CREDENTIALS、
账号锁定=ACCOUNT_LOCKED 都是 ``status="failed"``），``request_path`` / ``request_method``
也每行都填；但是

* ``GET /api/admin/logs`` 的响应体只发 ``status``，连 ``error_code`` 都不回吐，
  而 ``q`` 谓词一直在搜 ``error_code``——搜得着、看不见；
* 列表口**没有 status 过滤参数**，管理员无法只看失败操作；
* 导出口另写一套过滤条件（没有 ``q``、没有 ``status``），却在自己的 docstring 里承诺
  "按与列表接口相同的过滤条件导出"——筛了关键词再导出，拿到的是没筛过的 1000 条；
* 前端包装层归一化时把 ``status`` 整条丢掉，所以页面上既没有状态筛选也没有失败标记。

即安全事件记进了库、却在后台看不见也导不出来。这里钉住四条口径：
写口（log_operation）→ 存储 → 响应模型逐字段一致 → 两条口共用同一套过滤。
"""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.advanced import OperationLogEntryOut
from backend.core.logging_middleware import log_operation
from backend.models.log import OperationLog
from backend.utils.compat import utc_now_naive

PROBE_ACTION = "probe_audit_slice"


def _row(**overrides) -> OperationLog:
    base = {
        "action": PROBE_ACTION,
        "resource_type": "users",
        "resource_id": 7,
        "detail": json.dumps({"identifier": "choyeon"}, ensure_ascii=False),
        "ip_address": "203.0.113.9",
        "user_agent": "pytest/1.0",
        "request_path": "/api/auth/login",
        "request_method": "POST",
        "status": "success",
        "error_code": None,
        # 显式给时间：列上没有 server_default 可用的话，created_at 会是 NULL，
        # 而列表口按 created_at 倒序取页——NULL 行直接读不到，守卫就变成假通过。
        "created_at": utc_now_naive(),
    }
    base.update(overrides)
    return OperationLog(**base)


async def _seed(db_session: AsyncSession) -> dict[str, int]:
    """两条 failed（凭据错 / 账号锁定）+ 一条 success，返回 {标签: id}。"""
    rows = {
        "bad_credentials": _row(status="failed", error_code="AUTH_INVALID_CREDENTIALS"),
        "locked": _row(status="failed", error_code="ACCOUNT_LOCKED", ip_address="198.51.100.7"),
        "ok": _row(status="success"),
    }
    for row in rows.values():
        db_session.add(row)
    await db_session.commit()
    return {label: row.id for label, row in rows.items()}


async def _items(client: AsyncClient, headers: dict, **params) -> dict:
    response = await client.get("/api/admin/logs", headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.usefixtures("db_session")
class TestFailureColumnsAreReadable:
    @pytest.mark.asyncio
    async def test_list_emits_status_error_code_and_request(
        self, client: AsyncClient, staff_headers: dict, db_session: AsyncSession
    ) -> None:
        ids = await _seed(db_session)
        payload = await _items(client, staff_headers, action=PROBE_ACTION, page_size=200)
        by_id = {item["id"]: item for item in payload["items"]}

        for label, expected_status, expected_code in (
            ("bad_credentials", "failed", "AUTH_INVALID_CREDENTIALS"),
            ("locked", "failed", "ACCOUNT_LOCKED"),
            ("ok", "success", None),
        ):
            item = by_id[ids[label]]
            assert item["status"] == expected_status
            assert item["error_code"] == expected_code
            assert item["request_path"] == "/api/auth/login"
            assert item["request_method"] == "POST"

    @pytest.mark.asyncio
    async def test_response_body_matches_documented_model(
        self, client: AsyncClient, staff_headers: dict, db_session: AsyncSession
    ) -> None:
        """运行时行形态必须与 ``OperationLogEntryOut`` 精确相等——两个方向都不许漂移。"""
        await _seed(db_session)
        payload = await _items(client, staff_headers, action=PROBE_ACTION, page_size=50)
        emitted = set(payload["items"][0].keys())
        documented = set(OperationLogEntryOut.model_fields)
        assert emitted == documented, (
            f"仅响应有={emitted - documented} 仅文档有={documented - emitted}"
        )

    @pytest.mark.asyncio
    async def test_writer_path_reaches_reader(
        self, client: AsyncClient, staff_headers: dict, db_session: AsyncSession
    ) -> None:
        """经真实写口 log_operation 落的一行，必须能在列表口按 error_code 读回来。"""
        log = await log_operation(
            db_session,
            None,
            action=PROBE_ACTION,
            target_type="users",
            status="failed",
            error_code="PERMISSION_DENIED",
            details={"reason": "探针"},
        )
        assert log is not None, "log_operation 内部吞异常返回 None（写口没落地）"
        await db_session.commit()

        payload = await _items(
            client, staff_headers, action=PROBE_ACTION, status="failed", q="PERMISSION_DENIED"
        )
        assert [item["id"] for item in payload["items"]] == [log.id]
        assert payload["items"][0]["error_code"] == "PERMISSION_DENIED"


class TestStatusFilter:
    @pytest.mark.asyncio
    async def test_failed_only(
        self, client: AsyncClient, staff_headers: dict, db_session: AsyncSession
    ) -> None:
        ids = await _seed(db_session)
        payload = await _items(
            client, staff_headers, action=PROBE_ACTION, status="failed", page_size=200
        )
        assert {item["id"] for item in payload["items"]} == {ids["bad_credentials"], ids["locked"]}
        assert payload["total"] == 2
        assert all(item["status"] == "failed" for item in payload["items"])

    @pytest.mark.asyncio
    async def test_success_only(
        self, client: AsyncClient, staff_headers: dict, db_session: AsyncSession
    ) -> None:
        ids = await _seed(db_session)
        payload = await _items(
            client, staff_headers, action=PROBE_ACTION, status="success", page_size=200
        )
        assert {item["id"] for item in payload["items"]} == {ids["ok"]}

    @pytest.mark.asyncio
    async def test_unknown_status_is_rejected_not_ignored(
        self, client: AsyncClient, staff_headers: dict, db_session: AsyncSession
    ) -> None:
        """判别位不许"取值不认识就当中性"：那等于让调用方拿到全量却以为筛过了。"""
        await _seed(db_session)
        response = await client.get(
            "/api/admin/logs",
            headers=staff_headers,
            params={"action": PROBE_ACTION, "status": "bogus"},
        )
        assert response.status_code == 422, response.text

    @pytest.mark.asyncio
    async def test_q_matches_error_code(
        self, client: AsyncClient, staff_headers: dict, db_session: AsyncSession
    ) -> None:
        """q 一直声称能搜 error_code；这一条把"谓词背后真有数据"钉住。"""
        ids = await _seed(db_session)
        payload = await _items(client, staff_headers, action=PROBE_ACTION, q="ACCOUNT_LOCKED")
        assert [item["id"] for item in payload["items"]] == [ids["locked"]]


class TestExportSharesListFilters:
    async def _export_json(self, client: AsyncClient, headers: dict, **params) -> list[dict]:
        response = await client.get(
            "/api/admin/logs/export", headers=headers, params={"format": "json", **params}
        )
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("application/json")
        return json.loads(response.text)

    @pytest.mark.asyncio
    async def test_export_honours_status_and_q(
        self, client: AsyncClient, staff_headers: dict, db_session: AsyncSession
    ) -> None:
        ids = await _seed(db_session)
        exported = await self._export_json(
            client, staff_headers, action=PROBE_ACTION, status="failed", q="AUTH_INVALID"
        )
        assert [row["id"] for row in exported] == [ids["bad_credentials"]], (
            "导出口没跟列表口同口径过滤（'导出=当前筛选'是假话）"
        )

    @pytest.mark.asyncio
    async def test_export_json_rows_match_list_rows(
        self, client: AsyncClient, staff_headers: dict, db_session: AsyncSession
    ) -> None:
        await _seed(db_session)
        listed = await _items(
            client, staff_headers, action=PROBE_ACTION, status="failed", page_size=200
        )
        exported = await self._export_json(
            client, staff_headers, action=PROBE_ACTION, status="failed"
        )
        assert sorted(r["id"] for r in exported) == sorted(i["id"] for i in listed["items"])
        exported_by_id = {row["id"]: row for row in exported}
        for item in listed["items"]:
            assert exported_by_id[item["id"]] == item, "两条口同一行却给出不同字段（形态漂移）"

    @pytest.mark.asyncio
    async def test_export_csv_carries_error_code_and_request(
        self, client: AsyncClient, staff_headers: dict, db_session: AsyncSession
    ) -> None:
        await _seed(db_session)
        response = await client.get(
            "/api/admin/logs/export",
            headers=staff_headers,
            params={
                "format": "csv",
                "action": PROBE_ACTION,
                "status": "failed",
                "q": "ACCOUNT_LOCKED",
            },
        )
        assert response.status_code == 200, response.text
        lines = [line for line in response.text.splitlines() if line.strip()]
        header = lines[0]
        assert "错误码" in header and "请求" in header
        assert len(lines) == 2, f"CSV 行数应=表头+1 条命中，实得 {len(lines)}：{lines}"
        assert "ACCOUNT_LOCKED" in lines[1]
        assert "/api/auth/login" in lines[1]
