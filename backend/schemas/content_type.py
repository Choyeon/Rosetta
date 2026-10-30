"""自定义内容类型的请求/响应模型。

定义本身是 JSON（``content_types.fields``），字段级的形状约束在
``ContentField``（models/content_type.py）里；这里只管定义层的四件事：
key 的字符集、显示名/描述的边界、字段 key 不重复、以及"key 不可改"。

key 一旦落库就不再接受修改：它是 ``posts.post_type`` 与 ``posts.meta_fields``
的关联键，改名等于让历史文章变成"引用了不存在的类型"。要换 key 只能新建一个
定义再把文章逐篇改过去——这条约束由 ``ContentTypeUpdate`` 不带 key 字段 +
模块尾部 ``extra="forbid"`` 共同兑现（请求体带 key 直接 422，而不是静默忽略）。

读侧（``ContentTypeResponse`` / ``ContentTypePublic``）的 ``fields`` 用
``ContentField`` 逐条校验是安全的：handler 只喂 ``parsed_fields``（脏条目已被
模型层跳过），不会把库里的历史脏 JSON 直接丢进响应模型。
"""

from pydantic import BaseModel, field_validator
from pydantic import Field as PDField

from backend.models.content_type import ContentField
from backend.schemas.strict_config import apply_strict_extra_forbid

KEY_PATTERN = r"^[a-z][a-z0-9_-]{0,49}$"
MAX_FIELDS = 50


def _assert_unique_field_keys(fields: list[ContentField] | None) -> list[ContentField] | None:
    if fields is None:
        return None
    keys = [field.key for field in fields]
    if len(set(keys)) != len(keys):
        raise ValueError("字段 key 不能重复")
    return fields


class ContentTypeCreate(BaseModel):
    key: str = PDField(
        ...,
        min_length=1,
        max_length=50,
        pattern=KEY_PATTERN,
        description="类型唯一键（小写字母开头，仅小写字母/数字/下划线/连字符），落库后不可修改",
    )
    name: str = PDField(..., min_length=1, max_length=128, description="显示名")
    icon: str | None = PDField(None, max_length=64, description="图标名（lucide 名称）")
    description: str | None = PDField(None, max_length=512, description="用途说明")
    fields: list[ContentField] = PDField(
        default_factory=list, max_length=MAX_FIELDS, description="自定义字段定义"
    )

    @field_validator("fields")
    @classmethod
    def _unique_keys(cls, v: list[ContentField]) -> list[ContentField]:
        return _assert_unique_field_keys(v) or []


class ContentTypeUpdate(BaseModel):
    """部分更新：省略的键不动；``key`` 不在模型里，带上了会被 extra=forbid 拒掉。"""

    name: str | None = PDField(None, min_length=1, max_length=128)
    icon: str | None = PDField(None, max_length=64)
    description: str | None = PDField(None, max_length=512)
    fields: list[ContentField] | None = PDField(None, max_length=MAX_FIELDS)

    @field_validator("fields")
    @classmethod
    def _unique_keys(cls, v: list[ContentField] | None) -> list[ContentField] | None:
        return _assert_unique_field_keys(v)


class ContentTypeResponse(BaseModel):
    """后台列表/写入响应：带 id 与引用计数，便于前端做行级操作。"""

    id: int
    key: str
    name: str
    icon: str | None = None
    description: str | None = None
    fields: list[ContentField]
    posts_count: int = 0


class ContentTypePublic(BaseModel):
    """公开定义（不带 id）：编辑器与前台渲染都只需要 key 与字段形状。"""

    key: str
    name: str
    icon: str | None = None
    description: str | None = None
    fields: list[ContentField]


apply_strict_extra_forbid(globals(), __name__)
