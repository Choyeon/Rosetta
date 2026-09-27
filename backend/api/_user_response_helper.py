"""UserResponse 构建 helper：所有给前端的用户响应统一走这里 → resolved_avatar_url。"""

from __future__ import annotations

from typing import TypeVar

from backend.schemas import UserDetailResponse, UserResponse
from backend.services._avatar_helpers import resolved_for_user

_RT = TypeVar("_RT", bound=UserResponse)


def build_user_response(user, response_cls: type[_RT] = UserResponse) -> _RT:
    r = response_cls.model_validate(user)
    r.resolved_avatar_url = resolved_for_user(user)
    return r


def build_user_detail_response(user) -> UserDetailResponse:
    return build_user_response(user, response_cls=UserDetailResponse)


def apply_email_privacy(response, profile, current_user) -> None:
    """按用户隐私偏好在对外响应里遮蔽邮箱。

    口径是**默认拒绝**：``UserPreference.show_email`` 的模型默认值是 False，
    ``GET /users/{x}/preferences`` 在没有偏好行时也返回 ``show_email: False``，
    所以"没有偏好行"必须等同于"不公开邮箱"，否则注册后未动过设置的用户一被
    ``GET /users/{id}`` 查询就泄露邮箱。豁免只有两条：本人、以及 staff（后台需要联系用户）。
    此前只有 ``GET /users/username/{username}`` 做了遮蔽，``GET /users/{user_id}`` 直接返回
    明文邮箱——同一份数据换个路由就能绕过隐私开关，等于开关形同虚设。
    两个路由现在都走这里，不要再各自复制。
    """
    if profile and profile.get("is_self"):
        return
    if current_user is not None and current_user.is_staff:
        return
    preference = profile.get("preferences") if profile else None
    show_email = bool(getattr(preference, "show_email", False))
    if not show_email:
        response.email = "***"
