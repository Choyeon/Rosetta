"""
自定义内容类型服务层。

提供：
* ``create_content_type`` —— 写入 ``content_types`` 表；
* ``get_definition`` —— 按 key 查询 ContentTypeDefinition；
* ``build_dynamic_schema(definition)`` —— 动态生成 Pydantic 模型，用于校验字段；
* ``validate_and_pack_meta(definition, payload)`` —— 校验 payload 并打包成 JSON 字典（可直接存 Post.meta_fields）；
* ``read_meta(post, key)`` —— 读取 Post.meta_fields 中指定字段，类型按需转换。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field as PDField, create_model, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.blog import Post
from backend.models.content_type import ContentField, ContentTypeDefinition

logger = logging.getLogger(__name__)


# ── 字段类型 → Pydantic 规范 ────────────────────────────────────────────────

def _type_spec(ftype: str) -> tuple[type, Any]:
    """返回 (python_type, pydantic_default) 用于动态 Pydantic 模型构造。"""
    if ftype == "number":
        return (float, None)
    if ftype == "boolean":
        return (bool, False)
    if ftype in {"date", "datetime"}:
        return (str, None)
    if ftype == "integer":
        return (int, None)
    return (str, None)


async def create_content_type(
    session: AsyncSession,
    *,
    key: str,
    name: str,
    icon: str | None = None,
    description: str | None = None,
    fields: list[dict] | None = None,
) -> ContentTypeDefinition:
    """创建一条 ContentTypeDefinition。

    :param fields: list[dict]（ContentField 规范），创建前会做一次 Pydantic 校验，
                   非法字段抛 ValidationError 给上层统一处理。
    """
    normalized_fields: list[dict] = []
    if fields:
        for f in fields:
            if isinstance(f, ContentField):
                normalized_fields.append(f.model_dump(mode="json"))
            else:
                normalized_fields.append(
                    ContentField.model_validate(f).model_dump(mode="json")
                )
    obj = ContentTypeDefinition(
        key=key,
        name=name,
        icon=icon,
        description=description,
        fields=normalized_fields,
    )
    session.add(obj)
    return obj


async def get_definition(session: AsyncSession, key: str) -> ContentTypeDefinition | None:
    """按 key 查询 ContentTypeDefinition。"""
    r = await session.execute(
        select(ContentTypeDefinition).where(ContentTypeDefinition.key == key)
    )
    return r.scalar_one_or_none()


def build_dynamic_schema(definition: ContentTypeDefinition) -> Callable[..., BaseModel]:
    """基于 ContentTypeDefinition.parsed_fields 动态生成 Pydantic 模型类。

    返回的模型类接受 ``__call__(**kwargs)``，校验失败抛 Pydantic 校验错误（非空字段）：
    在 content_type 单测中使用方式::

        schema = build_dynamic_schema(definition)
        with pytest.raises(Exception):
            schema(author=None)  # 必填 author 缺失
    """
    fields: dict[str, Any] = {}
    for f in definition.parsed_fields:
        py_type, default = _type_spec(f.field_type)
        # 如果 必填：default 为 PDField(...)；否则默认 default 值
        default_any: Any = PDField(...) if f.required else PDField(default=default)
        fields[f.key] = (py_type if f.required else f"{py_type.__name__} | None", default_any)  # type: ignore[assignment]

    # 上面的类型注解表达不严谨，改用 create_model 直接传 PEP 604 类型字符串不行：
    # Pydantic 需要真实类型对象；重写一遍：
    fields2: dict[str, Any] = {}
    for f in definition.parsed_fields:
        py_type, _default = _type_spec(f.field_type)
        if f.required:
            fields2[f.key] = (py_type, PDField(..., description=f.label))
        else:
            from typing import Optional as _Optional
            fields2[f.key] = (_Optional[py_type], PDField(default=None, description=f.label))

    model_cls = create_model(
        f"DynamicContent_{definition.key}",
        __config__=ConfigDict(extra="ignore", from_attributes=True),
        **fields2,  # type: ignore[arg-type]
    )
    return model_cls


def validate_and_pack_meta(
    definition: ContentTypeDefinition,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """校验 payload 并打包为 JSON-safe 的 dict（可直接写入 Post.meta_fields）。

    处理细节：
    * 未知字段忽略（Pydantic extra=ignore）；
    * 必填字段缺失抛异常（与 ``build_dynamic_schema`` 保持一致）；
    * number 字段自动做 ``float`` 归一，boolean 做布尔归一；
    * 返回 dict 经过 JSON round-trip 保证序列化安全。
    """
    schema = build_dynamic_schema(definition)
    model = schema(**(payload or {}))
    data = model.model_dump(mode="python") if isinstance(model, BaseModel) else dict(model)
    # JSON round-trip 消除非 JSON 类型（datetime / Decimal / set 等）
    return json.loads(json.dumps(data, ensure_ascii=False, default=str))


def read_meta(post: Post, key: str) -> Any:
    """从 Post.meta_fields（dict 或 JSON str）中读取自定义字段 key 的值。

    用法::

        author_name = read_meta(post, "author")
    """
    meta = getattr(post, "meta_fields", None)
    if meta is None:
        return None
    if isinstance(meta, (bytes, bytearray, memoryview)):
        meta = meta.decode("utf-8") if isinstance(meta, (bytes, bytearray)) else bytes(meta).decode("utf-8")
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            return None
    if not isinstance(meta, dict):
        return None
    return meta.get(key)
