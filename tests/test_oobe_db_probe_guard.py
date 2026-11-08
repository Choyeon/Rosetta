"""P1-1 回归：OOBE 数据库连接探测不得变成匿名内网扫描器。

安全边界是「安装完成后不再匿名可达」；私网/环回地址**不禁止**，因为安装向导
的合法用途正是连同机或内网的 PostgreSQL。
"""

import pytest
from fastapi import HTTPException

from backend.api.oobe import _assert_db_probe_target
from backend.core import deps


def test_probe_allows_local_postgres():
    _assert_db_probe_target("postgresql", "127.0.0.1", 5432)


def test_probe_ignores_sqlite():
    _assert_db_probe_target("sqlite", "anything", 22)


@pytest.mark.parametrize("port", [22, 6379, 8080, 0])
def test_probe_rejects_non_standard_ports(port):
    with pytest.raises(HTTPException):
        _assert_db_probe_target("postgresql", "127.0.0.1", port)


@pytest.mark.parametrize("host", ["169.254.169.254", "metadata.google.internal", "metadata"])
def test_probe_rejects_cloud_metadata(host):
    with pytest.raises(HTTPException):
        _assert_db_probe_target("postgresql", host, 5432)


@pytest.mark.asyncio
async def test_db_probe_endpoints_closed_after_oobe_completed(client, monkeypatch):
    monkeypatch.setattr(deps, "is_oobe_complete", lambda: True)
    post = await client.post("/api/oobe/test-database", json={"db_type": "sqlite"})
    get = await client.get("/api/oobe/test-database", params={"db_type": "sqlite"})
    assert post.status_code >= 400
    assert get.status_code >= 400
