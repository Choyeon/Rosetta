"""P0-1 回归：环境变量别名与生产密钥强校验。

历史缺陷：字段 ``environment`` 只认 ``ENVIRONMENT``，而 .env 模板 / OOBE 生成器 /
docker-compose 全写 ``APP_ENV``，``extra="ignore"`` 静默丢弃，导致
``is_production`` 恒为 False、生产密钥校验与生产限流阈值永不生效。
"""

import pytest
from pydantic import ValidationError

from backend.core.config import Settings


def test_environment_reads_canonical_name(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "a" * 48)
    s = Settings(_env_file=None)
    assert s.environment == "production"
    assert s.is_production is True


def test_environment_keeps_legacy_app_env_compatible(monkeypatch):
    # 存量部署的 .env 仍写 APP_ENV，别名必须继续认，不能"改名即切断"
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "a" * 48)
    s = Settings(_env_file=None)
    assert s.is_production is True


@pytest.mark.parametrize(
    "secret",
    [
        "your-secret-key-change-in-production",
        "CHANGE_THIS_TO_A_SECURE_RANDOM_STRING_AT_LEAST_64_CHARS_LONG",
        "change-this-secret-key-in-production-please-use-a-strong-random-string",
        "short",
    ],
)
def test_production_rejects_placeholder_or_short_secret(monkeypatch, secret):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", secret)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_production_rejects_missing_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_development_generates_random_secret(monkeypatch):
    # 开发/测试不能因为"没配密钥"就起不来，但也不能留一个公开可预测的值
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    a = Settings(_env_file=None)
    b = Settings(_env_file=None)
    assert len(a.secret_key) >= 32
    assert a.secret_key != b.secret_key
    assert a.secret_key != "your-secret-key-change-in-production"
