"""SECRET_KEY 配置强度与可观测性回归测试。

背景：上一轮审查发现 `.env.production` 的占位符 ``CHANGE_THIS_TO_A_SECURE...``
虽 ≥32 字符、又不等于默认串，能绕过旧校验直接进生产。本测试锁定：

- 分类器能识别「看起来够长但本质是模板/低熵」的弱密钥；
- 生产环境对占位符 / 空 / 短密钥一律拒绝启动；
- 支持从 ``SECRET_KEY_FILE`` 挂载文件加载，且文件缺失在生产直接拒绝；
- 开发态占位符被替换为进程级随机强密钥；
- ``secret_key_status()`` 不泄露密钥内容，仅暴露强度 / 长度 / 来源。
"""

import secrets

import pytest

from backend.core.config import Settings, classify_secret_key


# ---------------------------------------------------------------------------
# 1) 分类器单元
# ---------------------------------------------------------------------------
def test_classify_empty_is_placeholder():
    assert classify_secret_key("") == "placeholder"
    assert classify_secret_key("   ") == "placeholder"


def test_classify_exact_default_is_placeholder():
    assert classify_secret_key("your-secret-key-change-in-production") == "placeholder"
    assert (
        classify_secret_key("CHANGE_THIS_TO_A_SECURE_RANDOM_STRING_AT_LEAST_64_CHARS_LONG")
        == "placeholder"
    )


def test_classify_long_but_template_substring_is_placeholder():
    # 关键回归：长度够、但命中模板子串，旧校验会放过。
    assert (
        classify_secret_key("my-production-key-please-change-this-now-0123456789") == "placeholder"
    )
    assert classify_secret_key("use-example-secret-key-aaaaaaaaaaaaaaaaaa") == "placeholder"


def test_classify_low_entropy_is_placeholder():
    # 40 个相同字符：即便很长也判为占位符。
    assert classify_secret_key("a" * 40) == "placeholder"
    # 单字符连续 ≥16 次。
    assert classify_secret_key("k" * 16 + secrets.token_urlsafe(32)) == "placeholder"


def test_classify_short_is_weak():
    assert classify_secret_key("short") == "weak"
    assert classify_secret_key(secrets.token_urlsafe(10)) == "weak"  # ~13 字符


def test_classify_strong_random():
    assert classify_secret_key(secrets.token_urlsafe(48)) == "strong"


# ---------------------------------------------------------------------------
# 2) 生产环境校验
# ---------------------------------------------------------------------------
def test_production_rejects_template_substring(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ValueError):
        Settings(_env_file=None, secret_key="x" * 30 + "CHANGE_THIS-later-0123456789")


def test_production_rejects_empty(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ValueError):
        Settings(_env_file=None, secret_key="")


def test_production_rejects_short(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ValueError):
        Settings(_env_file=None, secret_key="tooshort")


def test_production_accepts_strong_key(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    s = Settings(_env_file=None, secret_key=secrets.token_urlsafe(48))
    assert s.secret_key_status()["configured"] is True
    assert s.secret_key_status()["source"] == "env"


def test_production_rejects_missing_secret_key_file(monkeypatch, tmp_path):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY_FILE", str(tmp_path / "does_not_exist"))
    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_production_accepts_secret_key_file(monkeypatch, tmp_path):
    expected = secrets.token_urlsafe(48)
    key_file = tmp_path / "rosetta.key"
    key_file.write_text(expected + "\n", encoding="utf-8")  # 模拟挂载密钥含尾随换行
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY_FILE", str(key_file))
    s = Settings(_env_file=None)
    assert s.secret_key_status()["configured"] is True
    assert s.secret_key_status()["source"] == "file"
    # 文件内容（去空白）应作为实际密钥使用，而非退回占位符。
    assert s.secret_key == expected


# ---------------------------------------------------------------------------
# 3) 开发/测试态：占位符自动替换为随机强密钥
# ---------------------------------------------------------------------------
def test_development_replaces_placeholder(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    s = Settings(_env_file=None, secret_key="your-secret-key-change-in-production")
    assert s.secret_key != "your-secret-key-change-in-production"
    assert len(s.secret_key) >= 32
    assert s.secret_key_status()["configured"] is True


def test_development_keeps_strong_key(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    strong = secrets.token_urlsafe(48)
    s = Settings(_env_file=None, secret_key=strong)
    assert s.secret_key == strong
    assert s.secret_key_status()["configured"] is True


# ---------------------------------------------------------------------------
# 4) secret_key_status 形状（不泄露内容）
# ---------------------------------------------------------------------------
def test_secret_key_status_shape(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    s = Settings(_env_file=None, secret_key=secrets.token_urlsafe(48))
    status = s.secret_key_status()
    assert set(status) == {"configured", "strength", "length", "source"}
    assert status["configured"] is True
    assert status["strength"] in {"strong", "weak", "placeholder"}
    assert isinstance(status["length"], int)
    # 绝不包含密钥原文。
    assert secrets.token_urlsafe(48) not in status
