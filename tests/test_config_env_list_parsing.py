"""列表型环境变量必须三种写法都接（批次 #53 补充）。

背景（不是理论风险，是 2026-10-29 的实测）：pydantic-settings 对 `list[str]` 的默认解码是
**严格 JSON**，于是 `TRUSTED_PROXY_IPS=127.0.0.1` 这种最自然的写法在 `Settings()` 构造期直接
抛 `SettingsError` —— 进程起不来，而 `backend/core/config.py` 的字段描述、`rate_limit.get_client_ip`
的注释和后台访客记录页的告警文案**都**教运营者这么写。访客 IP 那条链（TRUSTED_PROXY_IPS → 采信
X-Forwarded-For → 本机 SSR 直连不再算访客）本来就是要靠这个变量打开的，写法一错就等于
"照文档配置 → 站点 502"。

所有用例都走 `monkeypatch.setenv` + `Settings(_env_file=None)`：构造参数不会经过
EnvSettingsSource，也就碰不到真正出问题的那条解码路径（`extra="ignore"` 还会把大写关键字
静默丢掉，写成 kwargs 的用例恒绿而无判别力）。

反证要点：四形（单值 / 逗号 / JSON / 空串）各自变异 `_decode_env_lists` 的对应分支会红对应那条；
把校验器的字段清单摘掉一项，`test_every_list_setting_is_covered` 会红。
"""

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsError

from backend.core.config import Settings


def _from_env(monkeypatch, name, value):
    """只喂一个环境变量、不读仓库 .env，保证读数与本机配置无关。"""
    monkeypatch.setenv(name, value)
    return Settings(_env_file=None)


def test_plain_ip_without_json_does_not_break_startup(monkeypatch):
    """这条就是修的那件事：以前它连 Settings() 都构造不出来。"""
    s = _from_env(monkeypatch, "TRUSTED_PROXY_IPS", "127.0.0.1")
    assert s.trusted_proxy_ips == ["127.0.0.1"]


def test_comma_separated_list_splits(monkeypatch):
    s = _from_env(monkeypatch, "TRUSTED_PROXY_IPS", "127.0.0.1, ::1")
    assert s.trusted_proxy_ips == ["127.0.0.1", "::1"]


def test_json_array_still_works(monkeypatch):
    """不能为了逗号把旧的 JSON 写法弄坏：生产 `CORS_ORIGINS` 现在就是这个形态。"""
    assert _from_env(monkeypatch, "TRUSTED_PROXY_IPS", '["127.0.0.1"]').trusted_proxy_ips == [
        "127.0.0.1"
    ]
    monkeypatch.setenv("CORS_ORIGINS", '["https://choyeon.cc","https://www.choyeon.cc"]')
    assert Settings(_env_file=None).cors_origins == [
        "https://choyeon.cc",
        "https://www.choyeon.cc",
    ]


def test_empty_value_is_empty_list_not_crash(monkeypatch):
    assert _from_env(monkeypatch, "TRUSTED_PROXY_IPS", "").trusted_proxy_ips == []
    assert _from_env(monkeypatch, "TRUSTED_PROXY_IPS", "   ").trusted_proxy_ips == []


def test_bad_json_is_an_error_not_one_giant_element(monkeypatch):
    """`["127.0.0.1"` 静默变成一个元素，等于"配了但不生效"——比报错更难查。"""
    with pytest.raises((ValidationError, SettingsError)):
        _from_env(monkeypatch, "TRUSTED_PROXY_IPS", '["127.0.0.1"')


def test_defaults_untouched(monkeypatch):
    """不给环境变量时必须是原默认值：这条挡住"校验器把默认值也解一遍解空了"。"""
    monkeypatch.delenv("TRUSTED_PROXY_IPS", raising=False)
    s = Settings(_env_file=None)
    assert s.trusted_proxy_ips == []
    assert s.supported_languages == ["zh", "en", "ja", "zh_Hant"]
    assert "jpg" in s.allowed_extensions


def test_every_list_setting_is_covered():
    """新增列表型设置项必须一起进校验器字段清单，否则又会退回严格 JSON 那一套。"""
    from typing import get_origin

    list_fields = {n for n, f in Settings.model_fields.items() if get_origin(f.annotation) is list}
    decorated = Settings.__pydantic_decorators__.field_validators["_decode_env_lists"].info.fields
    assert list_fields <= set(decorated), (
        f"未接住逗号写法的列表设置项：{sorted(list_fields - set(decorated))}"
    )


def test_parsed_list_reaches_the_consumer(monkeypatch):
    """环境变量解出来的值真的被 `_trusted_proxies()` 用得上（不是只在模型里躺着）。

    `rate_limit._trusted_proxies()` 读的是 `settings` 单例并带模块级缓存，所以这里把解好的值
    喂给单例、清掉缓存，断言限流与访客采集口看到的是同一份。
    """
    import backend.core.rate_limit as rl
    from backend.core.config import settings

    parsed = _from_env(monkeypatch, "TRUSTED_PROXY_IPS", "127.0.0.1, 10.0.0.5").trusted_proxy_ips
    cached = rl._TRUSTED_PROXY_CACHE
    original = settings.trusted_proxy_ips
    try:
        settings.trusted_proxy_ips = parsed
        rl._TRUSTED_PROXY_CACHE = None
        assert rl._trusted_proxies() == frozenset({"127.0.0.1", "10.0.0.5"})
    finally:
        rl._TRUSTED_PROXY_CACHE = cached
        settings.trusted_proxy_ips = original
