"""
邮件服务测试：投递必须有时间预算 + 干跑模式零真实投递

密码重置等接口会同步等待 send_email 结果来决定降级，因此 SMTP 卡死绝不能
无限挂住请求。这里用假 smtplib 锁定两件事：连接带 timeout、超时收敛为失败结果。

dry_run（后台「邮件通知 → 干跑模式」）是评论邮件等功能联调的安全阀：
开启时邮件只写日志、不连接 SMTP——否则测试邮件真实发往不存在的地址，
退信会全部回到 from_address（管理员自己的邮箱）。
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
    svc = es.EmailService(
        smtp_host="smtp.example.test",
        smtp_port=587,
        smtp_user="bot@example.test",
        smtp_password="secret",
        smtp_use_tls=False,
        from_email="bot@example.test",
        template_dir=".__nonexistent_templates__",
    )

    # resolved_smtp() 会用后台 `email` 分组覆写构造参数，而生产机上真的配了 QQ SMTP
    # （465 + SSL）：不钉死配置的话，本用例会走进 SMTP_SSL 分支、把 5 个位置参数交给被替换
    # 的 SMTP，于是"连接带 timeout"测的是这台机器的配置而不是代码。
    async def _cfg() -> dict:
        return {
            "host": "smtp.example.test",
            "port": 587,
            "user": "bot@example.test",
            "password": "secret",
            "tls": False,
            "from_email": "bot@example.test",
            "from_name": "Bot",
            "dry_run": False,
        }

    svc.resolved_smtp = _cfg
    return svc


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


@pytest.mark.asyncio
async def test_dry_run_never_touches_smtp(monkeypatch):
    """dry_run 开启：一封真实邮件都不许发出（连 SMTP 对象都不许构造）。"""
    monkeypatch.setattr(es.smtplib, "SMTP", _FakeSMTP)
    monkeypatch.setattr(es.smtplib, "SMTP_SSL", _FakeSMTP)

    svc = _service()

    async def _cfg() -> dict:
        return {
            "host": "smtp.example.test",
            "port": 587,
            "user": "bot@example.test",
            "password": "secret",
            "tls": False,
            "from_email": "bot@example.test",
            "from_name": "Bot",
            "dry_run": True,
        }

    svc.resolved_smtp = _cfg

    result = await svc._send_sync(_message())

    assert result.success is True
    assert _FakeSMTP.instances == [], "干跑模式不允许构造任何 SMTP 连接"


@pytest.mark.asyncio
async def test_dry_run_counts_as_configured():
    """只开 dry_run、不填 SMTP 凭据时也必须算"可用"——否则评论通知会在
    发信之前就被 smtp_is_configured() 挡掉，干跑形同虚设。"""
    svc = es.EmailService(
        smtp_host="",
        smtp_port=465,
        smtp_user="",
        smtp_password="",
        from_email="",
        template_dir=".__nonexistent_templates__",
    )

    async def _cfg() -> dict:
        return {
            "host": "",
            "port": 465,
            "user": "",
            "password": "",
            "tls": True,
            "from_email": "",
            "from_name": "",
            "dry_run": True,
        }

    svc.resolved_smtp = _cfg
    assert await svc.smtp_is_configured() is True
