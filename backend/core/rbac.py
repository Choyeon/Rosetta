"""
Rosetta RBAC 模块（单一角色 + 能力位图 轻量实现）。

角色层级（数值小 → 大 = 权限低 → 高）::

    subscriber(10) < contributor(20) < author(30) < editor(40) < admin(50) < super_admin(100)

业务代码使用方式::

    from backend.core.rbac import get_role_level, role_from_flags, Cap, user_has_capability

向后兼容：旧代码通过 ``is_staff`` / ``is_superuser`` 布尔派生角色；
新代码统一读写 ``User.role`` 字符串，必要时用 ``role_from_flags`` 做转换。
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum

# ─────────────────────────────────────────────────────────────────────────────
# 角色定义
# ─────────────────────────────────────────────────────────────────────────────

ALL_ROLES: tuple[str, ...] = (
    "subscriber",
    "contributor",
    "author",
    "editor",
    "admin",
    "super_admin",
)

_ROLE_LEVELS: dict[str, int] = {
    "subscriber": 10,
    "contributor": 20,
    "author": 30,
    "editor": 40,
    "admin": 50,
    "super_admin": 100,
}


def get_role_level(role: object) -> int:
    """返回角色的权限等级（未知角色按 subscriber 处理）。"""
    if isinstance(role, str) and role in _ROLE_LEVELS:
        return _ROLE_LEVELS[role]
    return _ROLE_LEVELS["subscriber"]


def role_from_flags(is_staff: bool, is_superuser: bool) -> str:
    """由旧布尔字段推导单一角色字符串。"""
    if is_superuser:
        return "super_admin"
    if is_staff:
        return "admin"
    return "subscriber"


def effective_role(user: object) -> str:
    """求用户的**有效角色** —— role 列与旧布尔 flag 取权限更高的一侧。

    这一层是必须的，不能让调用方直接读 ``user.role``：

    - ``role`` 列有 DB 默认值 ``'subscriber'``，历史账号（含 OOBE 创建的那批）里存在
      ``is_staff=True`` / ``is_superuser=True`` 但 ``role`` 仍是 ``'subscriber'`` 的行。
    - ``get_current_staff`` 早就做了双源判定（flag 或 role>=admin 都放行），而
      ``user_has_capability`` 只看 ``role`` 字符串。两套判定不一致的后果是：
      一个 legacy 管理员过了 `CurrentStaff` 闸门，却在下一行 `require_capability`
      被判为 subscriber 而 403 —— 权限体系出现"下半身截瘫"。
    - 另一侧也成立：某些账号 role 列已经提到 editor，但旧的 flag 还没同步，
      此时也不应被 flag 拉回 subscriber。

    取 max(level) 而非简单的 flag 优先：两条规则都只做提升（is_staff→admin、
    is_superuser→super_admin），不会互相降级。
    """
    from_role = normalize_role(getattr(user, "role", None))
    from_flags = role_from_flags(
        bool(getattr(user, "is_staff", False)),
        bool(getattr(user, "is_superuser", False)),
    )
    if from_role is None:
        return from_flags
    return from_role if get_role_level(from_role) >= get_role_level(from_flags) else from_flags


def normalize_role(role: object) -> str | None:
    """把多种角色输入（str/int/flag）统一为规范角色字符串。

    - 字符串忽略大小写并忽略下划线/空格变体
    - 整数按层级数值匹配：10→subscriber, 20→contributor, ..., 100→super_admin
    - 无法识别时返回 None（让调用方决定是 subscriber 还是报错）
    """
    if role is None:
        return None

    # 字符串路径
    if isinstance(role, str):
        normalized = role.strip().lower().replace(" ", "_").replace("-", "_")
        if normalized in ALL_ROLES:
            return normalized
        # 数值字符串
        if normalized.isdigit():
            return normalize_role(int(normalized))
        return None

    # 整数/层级值路径
    if isinstance(role, int):
        # 精确匹配
        for canonical, level in _ROLE_LEVELS.items():
            if level == role:
                return canonical
        # 取最接近的合法层级（向上取整）
        levels_sorted = sorted(_ROLE_LEVELS.items(), key=lambda kv: kv[1])
        for canonical, level in levels_sorted:
            if role <= level:
                return canonical
        return None

    # 其他类型：尝试字符串化
    return normalize_role(str(role))


# ─────────────────────────────────────────────────────────────────────────────
# 能力（Capability）枚举
# ─────────────────────────────────────────────────────────────────────────────


class Cap(str, Enum):
    """细粒度能力标识。``require_capability(Cap.X.value)`` 用于 FastAPI 依赖。"""

    # 内容
    EDIT_OWN_POSTS = "content:edit_own_posts"
    EDIT_OTHERS_POSTS = "content:edit_others_posts"
    DELETE_OWN_POSTS = "content:delete_own_posts"
    DELETE_OTHERS_POSTS = "content:delete_others_posts"
    PUBLISH_POSTS = "content:publish_posts"
    MANAGE_TERMS = "content:manage_terms"

    # 互动
    MODERATE_COMMENTS = "interaction:moderate_comments"

    # 媒体
    UPLOAD_MEDIA = "media:upload"
    MANAGE_MEDIA = "media:manage"

    # 用户
    MANAGE_USERS = "users:manage"
    EDIT_OWN_PROFILE = "users:edit_own_profile"

    # 系统
    VIEW_DASHBOARD = "system:view_dashboard"
    MANAGE_SETTINGS = "system:manage_settings"
    MANAGE_PLUGINS = "system:manage_plugins"
    VIEW_SITE_HEALTH = "system:view_site_health"


# ─────────────────────────────────────────────────────────────────────────────
# 角色 → 能力映射
# ─────────────────────────────────────────────────────────────────────────────

_ROLE_CAPS: dict[str, Iterable[Cap]] = {
    "subscriber": (
        Cap.EDIT_OWN_PROFILE,
        Cap.VIEW_DASHBOARD,
    ),
    "contributor": (
        Cap.EDIT_OWN_PROFILE,
        Cap.EDIT_OWN_POSTS,
        Cap.DELETE_OWN_POSTS,
        Cap.UPLOAD_MEDIA,
        Cap.VIEW_DASHBOARD,
    ),
    "author": (
        Cap.EDIT_OWN_PROFILE,
        Cap.EDIT_OWN_POSTS,
        Cap.DELETE_OWN_POSTS,
        Cap.PUBLISH_POSTS,
        Cap.UPLOAD_MEDIA,
        Cap.MANAGE_MEDIA,
        Cap.MANAGE_TERMS,
        Cap.VIEW_DASHBOARD,
    ),
    "editor": (
        Cap.EDIT_OWN_PROFILE,
        Cap.EDIT_OWN_POSTS,
        Cap.EDIT_OTHERS_POSTS,
        Cap.DELETE_OWN_POSTS,
        Cap.DELETE_OTHERS_POSTS,
        Cap.PUBLISH_POSTS,
        Cap.UPLOAD_MEDIA,
        Cap.MANAGE_MEDIA,
        Cap.MANAGE_TERMS,
        Cap.MODERATE_COMMENTS,
        Cap.VIEW_DASHBOARD,
    ),
    "admin": (
        *Cap,  # 管理员拥有除 superuser 专属外的全部能力
        Cap.VIEW_SITE_HEALTH,
    ),
    "super_admin": (
        *Cap,
        Cap.MANAGE_SETTINGS,
        Cap.MANAGE_PLUGINS,
        Cap.VIEW_SITE_HEALTH,
        Cap.MANAGE_USERS,
    ),
}


def user_has_capability(role: object, cap: str) -> bool:
    """判断指定角色是否拥有某能力（未知角色返回 False）。"""
    if not isinstance(role, str) or role not in _ROLE_CAPS:
        role = "subscriber"
    caps = _ROLE_CAPS.get(role, ())
    return cap in {c.value for c in caps}
