"""站点设置逐键往返：每一把键都必须"写得进、读得回、匿名口投影得出"。

`test_settings_group_consumers.py` 钉的是"每个键都有人消费"，`test_settings_numeric_bounds.py`
钉的是"数值键有区间闸门"，`test_settings_partial_patch_preserves_group.py` 钉的是"局部保存
不清空同组"。三面合起来仍漏掉最直接的一问：**这 88 把键里有没有哪一把根本存不进去或回不来**。

历史上的三种真实形态都会被这条往返抓住：
- `_only_known_keys` 之外的静默丢弃（写口 200、库里没动，界面上"保存成功、值还是旧的"）；
- 合并时按键类型改写（布尔被写成 1、float 被 int() 截断，回显与写入值不同）；
- `GET /api/settings/public` 漏投影某把键（前台读的是默认值，管理员改了没反应）。

公开分组（`PUBLIC_SETTING_GROUPS`）额外断言匿名口必须等于刚写入的值；名单里的分组之外
（email / security）则必须**不出现**在匿名口里。凭据形态的键（本文件自持一份 `_CREDENTIAL_RE`）
在匿名口必须是掩码，不得出现明文——`/api/config` 曾把发信地址念给匿名访客听过。
"""

import re

import pytest
from httpx import AsyncClient

from backend.api.settings_groups import (
    _GROUP_DEFAULTS,
    _NUMERIC_BOUNDS,
    _SENSITIVE_KEY_RE,
    PUBLIC_SETTING_GROUPS,
    _default_for,
)

# 判据在测试里自持一份，不直接拿后端那个对象当条件：后端名单缩掉一条（比如 `_key$`），
# 用同一个对象写的守卫会跟着一起变松，匿名口把凭据原文发出去时测试仍然全绿。
_CREDENTIAL_RE = re.compile(
    r"(password|secret|token|api_?key|private_key|authorization|_key$)", re.I
)
MASK_VALUE = "******"

I18N_PROBE = {"zh": "探针", "en": "probe", "ja": "プローブ", "zh_Hant": "探針"}

# 只有"值有形状约定"的键需要单独给探针；其余按类型自动生成。
STR_PROBES = {
    "basic.site_url": "https://probe.example.com",
    "basic.logo": "/logo-probe.svg",
    "appearance.primary_color": "#123456",
    "appearance.accent_color": "#654321",
    "hero.cta_url": "/archive",
    "hero.bg_image": "/covers/probe-cover.png",
    "hero.bg_gradient": "linear-gradient(180deg, #123456 0%, #654321 100%)",
    "media.allowed_image_types": "png,webp",
    "media.allowed_file_types": "mp4,pdf",
    "media.cdn_prefix": "https://cdn.probe.example",
    "notice.type": "warning",
    "navigation.header_style": "static",
    "seo.default_og_image": "/og-probe.png",
    "seo.indexnow_key": "0123456789abcdef0123456789abcdef",
    "email.smtp_host": "smtp.probe.example",
    "email.smtp_user": "probe@example.com",
    "email.smtp_password": "probe-smtp-secret",
    "email.from_address": "no-reply@probe.example",
}

LIST_PROBES = {
    "donate.methods": [
        {"name": "支付宝", "image": "/media/probe-alipay.png", "note": "扫码支持"},
        {"name": "微信支付", "image": "/media/probe-wechat.png", "note": ""},
    ],
    "donate.sponsors": [
        {"name": "路人甲", "avatar": "/media/probe-a.png", "amount": "50", "date": "2026-01-02"},
        {"name": "匿名", "avatar": "", "amount": "", "date": ""},
    ],
}


def _probe_for(group: str, key: str, default: object) -> object:
    dotted = f"{group}.{key}"
    if dotted in STR_PROBES:
        return STR_PROBES[dotted]
    if dotted in LIST_PROBES:
        return LIST_PROBES[dotted]
    if isinstance(default, bool):
        return not default
    if isinstance(default, dict):
        return {**I18N_PROBE}
    if isinstance(default, float):
        lo, hi = _NUMERIC_BOUNDS[dotted]
        return 1.25 if default != 1.25 else 1.5
    if isinstance(default, int):
        lo, hi = _NUMERIC_BOUNDS[dotted]
        for candidate in (int((lo + hi) / 2), int(lo), int(hi)):
            if candidate != default:
                return candidate
        raise AssertionError(f"{dotted} 的区间容不下任何与默认值不同的整数")
    if isinstance(default, str):
        return f"probe-{key}"
    raise AssertionError(f"{dotted} 出现了未预期的默认值类型：{type(default).__name__}")


def _group_cases():
    return [pytest.param(group, id=group) for group in sorted(_GROUP_DEFAULTS)]


def _all_keys() -> set[str]:
    return {f"{group}.{key}" for group in _GROUP_DEFAULTS for key in _default_for(group)}


@pytest.mark.parametrize("group", _group_cases())
async def test_every_setting_key_roundtrips(group: str, client: AsyncClient, admin_headers: dict):
    defaults = _default_for(group)
    failures: list[str] = []

    for key, default in defaults.items():
        probe = _probe_for(group, key, default)
        if probe == default:
            failures.append(f"{key}: 探针与默认值相同，往返无判别力")
            continue

        resp = await client.patch(
            f"/api/settings/{group}", headers=admin_headers, json={key: probe}
        )
        if resp.status_code != 200:
            failures.append(f"{key}: PATCH {resp.status_code} {resp.text[:160]}")
            continue
        if resp.json()["data"].get(key) != probe:
            failures.append(f"{key}: PATCH 响应不等于写入值 -> {resp.json()['data'].get(key)!r}")
            continue

        fetched = (await client.get(f"/api/settings/{group}", headers=admin_headers)).json()["data"]
        if fetched.get(key) != probe:
            failures.append(f"{key}: 回读不等于写入值 -> {fetched.get(key)!r}")

    assert failures == [], f"{group} 组设置往返失败：\n" + "\n".join(failures)


@pytest.mark.parametrize("group", _group_cases())
async def test_public_projection_matches_or_withholds(
    group: str, client: AsyncClient, admin_headers: dict
):
    """写进去的值必须能从匿名口读出（公开分组），且绝不以明文读出（凭据形态的键）。"""
    defaults = _default_for(group)
    probes = {key: _probe_for(group, key, default) for key, default in defaults.items()}

    resp = await client.patch(f"/api/settings/{group}", headers=admin_headers, json=probes)
    assert resp.status_code == 200, resp.text

    public = await client.get("/api/settings/public")
    assert public.status_code == 200
    # 该口返回 {"groups": {...}} 裸对象，没有 {success,data} 信封。
    payload = public.json()["groups"]

    if group not in PUBLIC_SETTING_GROUPS:
        assert group not in payload, f"{group} 不该出现在匿名口"
        return

    assert group in payload, f"{group} 是公开分组却没被投影"
    problems = []
    for key, probe in probes.items():
        got = payload[group].get(key)
        if _CREDENTIAL_RE.search(key) and probe not in ("", None):
            # 断言"被掩码"而不是"不等于明文"：只判不等时，投影顺手删掉这个键也算过，
            # 而后台的"已配置"指示灯靠的就是这条掩码值。
            if got != MASK_VALUE:
                problems.append(f"{key}: 凭据形态的键在匿名口读到 {got!r}，期望掩码 {MASK_VALUE!r}")
            continue
        expected = _expected_public(group, key, probe, probes)
        if got != expected:
            problems.append(f"{key}: 匿名口读到 {got!r}，期望 {expected!r}")
    assert problems == [], f"{group} 的匿名投影与写入值不一致：\n" + "\n".join(problems)


def _expected_public(group: str, key: str, probe: object, probes: dict) -> object:
    """匿名投影里唯一"故意不等于存值"的键：donate 关掉时的三个收敛位。

    `_public_donate` 在 `enable=False` 时把 methods / sponsors 清空、
    `show_sponsors_list` 置 False——"本站不再接受捐助"必须连收款码一起对外消失，
    所以这三键按投影规则判，而不是按写入值判。
    """
    if group == "donate" and probes.get("enable") is False and key in {"methods", "sponsors"}:
        return []
    if group == "donate" and probes.get("enable") is False and key == "show_sponsors_list":
        return False
    return probe


def test_security_group_is_the_only_private_one_left():
    """`security`（登录锁定阈值）与 `email`（SMTP 凭据）都不得进匿名口。

    email 在名单里出现过的话就是泄漏：`resolved_smtp()` 读的是 `.env` + 分组，
    前台不需要它，而 `from_address` 是发信地址。
    """
    assert "security" not in PUBLIC_SETTING_GROUPS
    assert "email" not in PUBLIC_SETTING_GROUPS
    assert set(PUBLIC_SETTING_GROUPS) <= set(_GROUP_DEFAULTS), "公开名单里有不存在的分组"


def test_probes_cover_every_composite_key():
    """数组形态的键必须有专用探针：通用值会被闸门拒掉或根本没有判别力。

    dict（i18n）形态统一用四语探针，`I18N_PROBE` 本身就是"与任何默认值都不同"的形状，
    所以只有 list 需要点名。
    """
    lists = set()
    for group in _GROUP_DEFAULTS:
        for key, value in _default_for(group).items():
            if isinstance(value, list):
                lists.add(f"{group}.{key}")
    assert lists == set(LIST_PROBES), (
        f"数组键清单与专用探针不一致（多的是已删键，少的是没有探针）：{lists ^ set(LIST_PROBES)}"
    )


def test_i18n_probe_covers_all_four_languages():
    assert set(I18N_PROBE) == {"zh", "en", "ja", "zh_Hant"}


def test_backend_mask_list_matches_this_files_credential_list():
    """`email.smtp_password` 不在公开分组里，匿名口那条断言永远跑不到它——所以两边的名单
    必须在这里对账一次：后端漏一把，私有的那把也一样会随下一次分组公开而外泄。"""
    backend = {k for k in _all_keys() if _SENSITIVE_KEY_RE.search(k.split(".", 1)[1])}
    local = {k for k in _all_keys() if _CREDENTIAL_RE.search(k.split(".", 1)[1])}
    assert local == backend, f"脱敏名单与本文件的凭据清单不一致：{local ^ backend}"
    assert {"email.smtp_password", "seo.indexnow_key"} <= local


def test_probe_table_has_no_dead_names():
    """点名探针必须对应真实键——拼错的名字让该键退回通用探针，
    于是形状约定（URL / 枚举 / 十六进制色值）悄悄失去覆盖，而测试仍全绿。"""
    dead = sorted((set(STR_PROBES) | set(LIST_PROBES)) - _all_keys())
    assert dead == [], f"这些点名探针已经没有对应的设置键：{dead}"


def test_the_round_trip_covers_every_key():
    """清点覆盖面：本文件的判别力就是"每把键都走一次写读投影"，条数掉了等于守卫退化。"""
    total = sum(len(_default_for(g)) for g in _GROUP_DEFAULTS)
    assert len(_all_keys()) == total
    assert total >= 85, f"设置键总数异常偏少（{total}），要么删了键要么分组读错"
