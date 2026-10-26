"""角色 → 能力映射的守卫。

``_ROLE_CAPS`` 里 ``"admin": (*Cap, ...)`` 看起来只是"全部能力"，实际含义是
"以后新增的每一个 superuser 专属能力都会自动发给 admin"——而 ``require_capability``
正是新管理端点默认会挂的闸门。这类"默认多给"不会报错、不会红测试，只会安静地把
不该开的门打开。

下面三条把意图写成可执行断言：
1. admin 不得拥有 superuser 专属的三项能力；
2. super_admin 拥有枚举里的全部能力（新增 Cap 时自动被覆盖）；
3. 角色能力随等级单调递增（低等级角色有的，高等级角色一定有）。
"""

import pytest

from backend.core.rbac import Cap, user_has_capability

SUPERUSER_ONLY = (Cap.MANAGE_USERS, Cap.MANAGE_SETTINGS, Cap.MANAGE_PLUGINS)

ROLE_LADDER = ["subscriber", "contributor", "author", "editor", "admin", "super_admin"]


@pytest.mark.parametrize("cap", SUPERUSER_ONLY, ids=lambda c: c.value)
def test_admin_does_not_get_superuser_only_capabilities(cap: Cap):
    """admin 是"站点管理员"，不是"平台所有者"：三项能力留在 super_admin。"""
    assert not user_has_capability("admin", cap.value), (
        f"admin 不该拥有 {cap.value}（只有 super_admin 可以）"
    )
    assert user_has_capability("super_admin", cap.value)


def test_super_admin_holds_every_declared_capability():
    """新增 Cap 而忘记给超级管理员时立刻红：否则新能力谁都没有。"""
    missing = [cap.value for cap in Cap if not user_has_capability("super_admin", cap.value)]
    assert missing == []


def test_capability_ladder_is_monotonic():
    """等级越高能力越多：低等级角色拥有的能力必须被高等级角色继承。"""
    for lower, higher in zip(ROLE_LADDER, ROLE_LADDER[1:], strict=False):
        lower_caps = {cap.value for cap in Cap if user_has_capability(lower, cap.value)}
        missing = {value for value in lower_caps if not user_has_capability(higher, value)}
        assert not missing, f"{higher} 缺少 {lower} 已有的能力: {sorted(missing)}"


def test_unknown_role_degrades_to_subscriber():
    """未知/空角色按最低权限处理，不是"按最高"。"""
    assert user_has_capability("not-a-role", Cap.VIEW_DASHBOARD.value)
    assert not user_has_capability("not-a-role", Cap.MANAGE_USERS.value)
    assert not user_has_capability(None, Cap.PUBLISH_POSTS.value)
