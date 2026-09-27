"""schema 严格加固（extra=forbid）真的生效的守卫。

坑：Pydantic v2 在类创建时就把 `model_config` 编译进 core schema，
**事后只改字典不会改变校验行为**（原项目里 8 份复制粘贴的加固全部是假的，
而且还被 `except Exception: pass` 包着）。这些用例钉的是"多带字段必须 422"，
一旦加固退化成空操作，这里先红。
"""

import pytest
from pydantic import BaseModel, ValidationError

from backend.schemas import AdminUserUpdateFull, SiteSettingItem
from backend.schemas.activity import ActivityCreate
from backend.schemas.gallery import PhotoUpdate
from backend.schemas.strict_config import apply_strict_extra_forbid


@pytest.mark.parametrize(
    "schema,kwargs",
    [
        (PhotoUpdate, {"url": "https://x/y.png"}),
        (ActivityCreate, {"content": {"zh": "hi"}}),
        (AdminUserUpdateFull, {"nickname": "n"}),
    ],
)
def test_extra_field_is_rejected(schema, kwargs):
    """各加固模块的 request schema 必须拒绝未声明字段。"""
    with pytest.raises(ValidationError) as excinfo:
        schema.model_validate({**kwargs, "not_a_field": 1})
    assert excinfo.value.errors()[0]["type"] == "extra_forbidden"


def test_admin_user_update_can_write_qq_and_avatar_source():
    """`UserDetailResponse` 会回显 qq / avatar_source，写入侧必须同样可写。

    原先二者只在响应模型里，PUT 请求带上一律被静默丢弃（加固生效后变 422，
    才暴露出这个读写不对称）。
    """
    data = AdminUserUpdateFull.model_validate({"qq": "7777777", "avatar_source": "qq"})
    assert data.qq == "7777777"
    assert data.avatar_source == "qq"


def test_avatar_source_rejects_unknown_source():
    with pytest.raises(ValidationError):
        AdminUserUpdateFull.model_validate({"avatar_source": "evil"})


def test_site_setting_item_has_no_undeclared_rows_kwarg():
    """`rows` 从未被前端消费，也不在 schema 里 —— 曾经靠"加固无效"混进响应。"""
    with pytest.raises(ValidationError) as excinfo:
        SiteSettingItem.model_validate(
            {"key": "K", "label": "L", "type": "textarea", "value": "v", "rows": 2}
        )
    assert excinfo.value.errors()[0]["type"] == "extra_forbidden"


def test_helper_rebuilds_and_forbids():
    """直接验证 helper 的加固动作：不重建就 forbid 不生效，重建后必须生效。"""

    class _Probe(BaseModel):
        a: int = 1

    namespace = {"_Probe": _Probe}
    # 加固前：Pydantic 默认 ignore，多余字段被静默接受（这就是旧代码的假象来源）
    assert _Probe.model_validate({"a": 2, "junk": 3}).model_dump() == {"a": 2}

    apply_strict_extra_forbid(namespace, _Probe.__module__)
    assert _Probe.model_config["extra"] == "forbid"
    with pytest.raises(ValidationError):
        _Probe.model_validate({"a": 2, "junk": 3})
