"""schema 严格加固（extra=forbid）真的生效的守卫。

坑：Pydantic v2 在类创建时就把 `model_config` 编译进 core schema，
**事后只改字典不会改变校验行为**（原项目里 8 份复制粘贴的加固全部是假的，
而且还被 `except Exception: pass` 包着）。这些用例钉的是"多带字段必须 422"，
一旦加固退化成空操作，这里先红。
"""

import ast
import sys
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from backend.schemas import (
    AdminUserCreate,
    AdminUserUpdateFull,
    CommentBase,
    GuestbookEntryBase,
    PasswordChange,
    PasswordReset,
    SiteSettingItem,
    UserBase,
    UserCreate,
)
from backend.schemas.activity import ActivityCreate
from backend.schemas.gallery import PhotoUpdate
from backend.schemas.strict_config import apply_strict_extra_forbid


def _validator_of(schema, field):
    """取该 schema 上绑定到 field 的那个 field_validator 原函数。

    pydantic 2.13 的 `Decorator` 把绑定字段放在 `info.fields` 上（早期版本才有顶层
    `.fields`），读错位置会让这道守卫永远取不到 validator 而直接红。
    """
    info = schema.__pydantic_decorators__.field_validators
    matched = [d for d in info.values() if field in d.info.fields]
    assert matched, f"{schema.__name__} 上没有 {field} 的 field_validator"
    return matched[0].func


def _validator_source(schema, field) -> str:
    """取"绑定到该字段的那个 field_validator"的源码，按磁盘文本 + AST 定位。

    不用 `inspect.getsource(函数)`：全量跑里这条会在**别的用例跑过之后**取到错位的一整块
    （同一份文件、函数对象的行号却是另一套），于是守卫读到邻接类的源码——既会假红，
    也会在读到桩时假绿。同仓先例的口径见 `tests/test_user_notify_by_email_preference.py`
    里"按文件文本读而不是 inspect.getsource"那条注释。
    运行时仍然用 `__pydantic_decorators__` 确认"这个字段确实有 validator"，
    所以这里拿不到对应函数就直接红，不会静默放过。
    """
    assert _validator_of(schema, field), "运行侧没绑定该字段的 validator"

    trees: dict[str, ast.Module] = {}
    for klass in schema.__mro__:
        if klass.__name__ == "BaseModel" or getattr(klass, "__module__", "") != schema.__module__:
            continue
        mod = sys.modules[klass.__module__]
        path = str(mod.__file__)
        if path not in trees:
            trees[path] = ast.parse(Path(path).read_text(encoding="utf-8"))
        for node in trees[path].body:
            if not (isinstance(node, ast.ClassDef) and node.name == klass.__name__):
                continue
            for fn in node.body:
                if not isinstance(fn, ast.FunctionDef):
                    continue
                for dec in fn.decorator_list:
                    if not (
                        isinstance(dec, ast.Call) and _callee_name(dec.func) == "field_validator"
                    ):
                        continue
                    bound = {
                        a.value
                        for a in dec.args
                        if isinstance(a, ast.Constant) and isinstance(a.value, str)
                    }
                    if field in bound:
                        return ast.unparse(fn)
    pytest.fail(f"{schema.__name__}.{field} 的 field_validator 在源码里找不到（被改名或被搬走？）")


def _callee_name(node) -> str:
    """`field_validator(...)` 与 `pydantic.field_validator(...)` 两种写法都要认。"""
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


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


@pytest.mark.parametrize(
    "schema,field",
    [
        (UserCreate, "password"),
        (PasswordChange, "new_password"),
        (PasswordReset, "new_password"),
        (AdminUserCreate, "password"),
    ],
)
def test_password_strength_rule_is_single_sourced(schema, field):
    """4 份密码校验必须只调用 `_check_password_strength`，不得再内联一份。

    这条规则原先在 4 个 schema 里逐字复制，改一次口径要动 4 处；漏一处的表现是
    "注册要求大写、改密码不要求"，同一账号两条路径互相判逆。
    """
    source = _validator_source(schema, field)
    assert "_check_password_strength" in source
    assert "密码必须包含至少一个大写字母" not in source


@pytest.mark.parametrize(
    "schema,field",
    [(UserBase, "website"), (AdminUserCreate, "github"), (AdminUserUpdateFull, "github")],
)
def test_profile_url_rule_is_single_sourced(schema, field):
    """资料类 URL 的唯一口径是 `_normalize_optional_url`（缺 scheme 补 https）。"""
    source = _validator_source(schema, field)
    assert "_normalize_optional_url" in source
    assert 'f"https://' not in source


@pytest.mark.parametrize(
    "schema,field",
    [(CommentBase, "author_website"), (GuestbookEntryBase, "author_website")],
)
def test_ugc_url_rule_is_single_sourced(schema, field):
    """UGC 的 URL 走严格档 `_require_absolute_url`（拒缺 scheme，空值归 None）。

    它和资料档是**两条策略**不是重复实现，所以各自收口、不合并成一个函数。
    """
    source = _validator_source(schema, field)
    assert "_require_absolute_url" in source
    assert "raise ValueError" not in source


def test_password_rule_still_rejects_weak_values():
    """收口不许改行为：三条强度规则逐条仍然生效，强密码仍然放行。

    `_check_password_strength` 是**短路**的（长度→大写→小写→数字，第一条不满足即抛），
    所以每个样本必须只缺它要测的那一条，否则报的是前面那条规则的消息。
    """
    base = {"username": "tester1", "email": "t@example.com"}
    for value, msg in [
        ("abcd1234", "一个大写字母"),
        ("ABCD1234", "一个小写字母"),
        ("abcdEFGH", "一个数字"),
    ]:
        with pytest.raises(ValidationError) as excinfo:
            UserCreate.model_validate({**base, "password": value})
        assert msg in str(excinfo.value)
    assert UserCreate.model_validate({**base, "password": "Abcdefg1"}).password == "Abcdefg1"


def test_profile_url_still_prepends_https():
    base = {"username": "tester1", "email": "t@example.com"}
    got = UserBase.model_validate({**base, "website": "example.com"})
    assert got.website == "https://example.com"
    assert UserBase.model_validate({**base, "website": None}).website is None


def test_ugc_url_still_rejects_missing_scheme_and_maps_empty_to_none():
    base = {"content": "hello", "author_name": "nick"}
    with pytest.raises(ValidationError):
        CommentBase.model_validate({**base, "author_website": "example.com"})
    assert CommentBase.model_validate({**base, "author_website": ""}).author_website is None
    got = CommentBase.model_validate({**base, "author_website": "https://e.com"})
    assert got.author_website == "https://e.com"
