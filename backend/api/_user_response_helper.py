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
