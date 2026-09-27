"""
邮件服务测试：投递必须有时间预算

密码重置等接口会同步等待 send_email 结果来决定降级，因此 SMTP 卡死绝不能
无限挂住请求。这里用假 smtplib 锁定两件事：连接带 timeout、超时收敛为失败结果。
"""

import pytest

from backend.services import email_service as es


class _FakeSMTP:
    """记录构造参数并可按注入方式抛错的 smtplib 替身"""

    instances: list["_FakeSMTP"] = []
    exc: Exception | None = None

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sent = False
        self.quit_called = False
        _FakeSMTP.instances.append(self)

    def starttls(self):
        return None

    def login(self, user, password):
        return None

    def sendmail(self, from_addr, to_addrs, msg):
        if _FakeSMTP.exc is not None:
            raise _FakeSMTP.exc
        self.sent = True

    def quit(self):
        self.quit_called = True


@pytest.fixture(autouse=True)
def _reset_fake():
    _FakeSMTP.instances = []
    _FakeSMTP.exc = None
    yield


def _service() -> es.EmailService:
    return es.EmailService(
        smtp_host="smtp.example.test",
        smtp_port=587,
        smtp_user="bot@example.test",
        smtp_password="secret",
        smtp_use_tls=False,
        from_email="bot@example.test",
        template_dir=".__nonexistent_templates__",
    )


def _message() -> es.EmailMessage:
    return es.EmailMessage(to="user@example.test", subject="t", body="b")


@pytest.mark.asyncio
async def test_smtp_connection_carries_timeout(monkeypatch):
    monkeypatch.setattr(es.smtplib, "SMTP", _FakeSMTP)

    result = await _service()._send_sync(_message())

    assert result.success is True
    conn = _FakeSMTP.instances[0]
    assert conn.timeout == es._SMTP_TIMEOUT, "smtplib 必须带 timeout，否则网络黑洞会挂死请求"
    assert conn.sent is True


@pytest.mark.asyncio
async def test_timeout_converts_to_failed_result(monkeypatch):
    monkeypatch.setattr(es.smtplib, "SMTP", _FakeSMTP)
    _FakeSMTP.exc = TimeoutError("timed out")

    result = await _service()._send_sync(_message())

    assert result.success is False
    assert result.error and "timed out" in result.error
    assert _FakeSMTP.instances[0].quit_called is True, "失败路径也必须关闭连接，否则每次失败漏一条"
