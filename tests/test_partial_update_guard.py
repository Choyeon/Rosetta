"""`backend/core/partial_update.py` 守卫测试：显式 null 不得写进 NOT NULL 列。

覆盖两层：
1. 元数据判定本身——按列的 `nullable` 而不是 Pydantic 的 `X | None` 注解决定，
   关系属性与非列键要跳过（否则会把 `{"icon": null}` 这种合法清空也拦掉）。
2. 端到端形状——挑几个真实更新端点，发送 `{"<NOT NULL 字段>": null}`，
   断言拿到的是 422 校验信封而不是 500（修复前这些请求会一路走到 flush）。
"""

import pytest
from httpx import AsyncClient

from backend.core.exceptions import ValidationException
from backend.core.partial_update import (
    apply_partial_update,
    not_null_violations,
    validate_partial_update,
)
from backend.models.activity import Activity
from backend.models.announcement import Announcement
from backend.models.blog import Category, Post, Tag
from backend.models.core import FriendLink, Navigation, Page
from backend.models.gallery import Album, Photo
from backend.models.hero import HeroSlide
from backend.models.post_series import PostSeries
from backend.models.user import User, UserPreference, UserTitle

# 每个条目 = (映射类, 该表里 NOT NULL 的列名)。取自各 models/* 的 mapped_column(nullable=False)。
NOT_NULL_CASES = [
    (Activity, "content"),
    (Announcement, "title"),
    (Album, "title"),
    (Category, "color"),
    (FriendLink, "name"),
    (HeroSlide, "overlay_color"),
    (Navigation, "title"),
    (Page, "slug"),
    (Photo, "url"),
    (Post, "title"),
    (PostSeries, "title"),
    (Tag, "slug"),
    (User, "email"),
    (UserPreference, "theme"),
    (UserTitle, "color"),
]

# 允许为 NULL 的列：清空它们是合法请求，守卫不得拦截。
NULLABLE_CASES = [
    (UserTitle, "icon"),
    (User, "bio"),
    (Category, "description"),
]


@pytest.mark.parametrize("model,field", NOT_NULL_CASES)
def test_flags_not_null_column(model, field: str):
    assert not_null_violations(model, {field: None}) == [f"{field}"], (
        f"{model.__name__}.{field} 是 NOT NULL 列，却没被守卫识别"
    )


@pytest.mark.parametrize("model,field", NULLABLE_CASES)
def test_allows_nullable_column(model, field: str):
    column = model.__table__.columns[field]
    assert column.nullable, f"用例过期：{model.__name__}.{field} 已不再是可空列"
    assert not_null_violations(model, {field: None}) == []


def test_skips_unknown_keys_and_relationships():
    """非列键（派生字段）与关系属性都不该由本守卫判定。"""
    assert not_null_violations(UserTitle, {"not_a_column": None}) == []
    assert not_null_violations(User, {"title": None}) == []


def test_validate_raises_422_envelope():
    with pytest.raises(ValidationException) as exc_info:
        validate_partial_update(UserTitle, {"color": None, "icon": None})
    assert exc_info.value.status_code == 422
    assert exc_info.value.details["fields"] == ["color"]


@pytest.mark.asyncio
async def test_category_color_null_is_422_not_500(
    client: AsyncClient, admin_headers: dict, test_category: Category
):
    r = await client.put(
        f"/api/blog/categories/{test_category.id}", json={"color": None}, headers=admin_headers
    )
    assert r.status_code == 422, f"显式 null 颜色变成了 {r.status_code}：{r.text[:200]}"
    assert r.json()["success"] is False


@pytest.mark.asyncio
async def test_post_title_null_keeps_record(
    client: AsyncClient, admin_headers: dict, test_post: Post
):
    r = await client.put(
        f"/api/blog/posts/{test_post.id}", json={"title": None}, headers=admin_headers
    )
    assert r.status_code == 422, f"显式 null 标题变成了 {r.status_code}：{r.text[:200]}"

    after = await client.get(f"/api/blog/posts/{test_post.id}")
    assert after.status_code == 200
    assert after.json()["title"], "校验失败却把已有标题清掉了"


@pytest.mark.asyncio
async def test_preference_theme_null_is_422(client: AsyncClient, auth_headers: dict):
    r = await client.put("/api/users/me/preferences", json={"theme": None}, headers=auth_headers)
    assert r.status_code == 422, f"显式 null 偏好变成了 {r.status_code}：{r.text[:200]}"


def test_apply_skips_unmapped_keys_and_writes_columns():
    """schema 里的兼容/派生键（Photo 的 thumbnail_url / media_id / original_url）
    不是模型列：裸 setattr 会留下非映射属性，refresh 后仍被 Response 回显成"假成功"。
    apply_partial_update 必须只写真实映射属性。"""
    photo = Photo(album_id=1, url="/a.jpg", title=None)
    apply_partial_update(
        photo,
        {
            "title": "真标题",  # 映射列：应写入
            "thumbnail_url": "phantom-thumb",  # 非列：应跳过
            "media_id": 999,  # 非列：应跳过
            "original_url": "phantom-orig",  # 非列：应跳过
        },
    )
    assert photo.title == "真标题"
    for phantom in ("thumbnail_url", "media_id", "original_url"):
        assert phantom not in photo.__dict__, f"{phantom} 被写成了非映射属性（假成功来源）"
