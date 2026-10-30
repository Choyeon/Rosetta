"""自定义内容类型：定义读取 + 文章写口的 ``meta_fields`` 校验。

四段契约里这一段是"写口 → 存储"之间的闸门，落点只有两个：

- ``GET /api/content-types``（公开，定义供前台渲染标签）与后台 CRUD 读定义；
- ``POST/PUT /api/blog/posts`` 在落库**之前**调用 :func:`resolve_post_type_and_meta`，
  未知类型、缺必填、类型不符、未知字段一律 422（``VALIDATION_ERROR``）。

三条设计约束，改之前先读：

1. **读侧不校验。** 定义可以在有文章之后被改（改标签、删字段、把可选改必填），
   历史行里就会留着今日定义之外的键。公开详情照原样下发 ``meta_fields``，
   渲染侧只展示"定义里存在且值非空"的键；在这里给读侧加校验等于让一次定义调整
   把一批文章详情整条打成 500（与 hero 响应模型那次线上事故同一形状）。
2. **``default`` 只在编辑器预填，写入时不自动补。** 必填字段缺值必须显式 422；
   服务端静默补默认值，作者看到的是"保存成功"，库里的值与他在表单里看到的不是一回事。
3. **内置类型 ``post`` 不接受自定义字段。** 标准文章没有定义可依，收下自由 JSON
   等于把"未接管的动态字段"重新引入：没人渲染、没人校验，只会在库里堆积脏数据。
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, NoReturn

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import ValidationException
from backend.models.content_type import ContentField, ContentTypeDefinition
from backend.schemas._url_policy import reject_pseudo_url_scheme
from backend.utils.compat import UTC

BUILTIN_POST_TYPE = "post"
POST_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,49}$")

# 文本类字段的长度上限。markdown 最宽（正文级内容），text 最窄（书目号、ISBN 这类短值）。
_TEXT_LIMITS = {"text": 500, "textarea": 20000, "markdown": 50000}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _fail(field: str | None, message: str) -> NoReturn:
    """统一抛 422：字段级错误带上 ``fields`` 与 ``errors``，前端可直接标到输入框上。"""
    details: dict[str, Any] = {}
    if field:
        details["fields"] = [field]
        details["errors"] = [{"field": field, "message": message}]
    raise ValidationException(message=message, details=details or None)


async def get_content_type(db: AsyncSession, key: str) -> ContentTypeDefinition | None:
    """按 key 取定义（当前是单站点，``site_id`` 由唯一约束兜住）。"""
    result = await db.execute(select(ContentTypeDefinition).where(ContentTypeDefinition.key == key))
    return result.scalar_one_or_none()


async def list_content_types(db: AsyncSession) -> list[ContentTypeDefinition]:
    result = await db.execute(
        select(ContentTypeDefinition).order_by(
            ContentTypeDefinition.key.asc(), ContentTypeDefinition.id.asc()
        )
    )
    return list(result.scalars().all())


async def resolve_post_type_and_meta(
    db: AsyncSession,
    post_type: str | None,
    meta_fields: dict[str, Any] | None,
) -> tuple[str, dict[str, Any] | None]:
    """把请求里的 ``(post_type, meta_fields)`` 归一成可落库的一对值。"""
    key = (post_type or BUILTIN_POST_TYPE).strip().lower()
    if not POST_TYPE_PATTERN.match(key):
        _fail("post_type", "内容类型 key 只能是小写字母开头的 1-50 位小写字母/数字/下划线/连字符")

    if key == BUILTIN_POST_TYPE:
        if meta_fields:
            _fail("meta_fields", "标准文章（post）不接受自定义字段，请先选择或定义一个内容类型")
        return key, None

    definition = await get_content_type(db, key)
    if definition is None:
        _fail("post_type", f"未定义的内容类型：{key}")
    return key, normalize_meta_fields(definition, meta_fields)


def normalize_meta_fields(
    definition: ContentTypeDefinition, meta: dict[str, Any] | None
) -> dict[str, Any] | None:
    """按定义校验并归一化 ``meta_fields``；全部为空时返回 None（列语义 = 没有扩展字段）。"""
    if meta is None:
        return None
    if not isinstance(meta, dict):
        _fail("meta_fields", "自定义字段必须是 JSON 对象")

    fields = definition.parsed_fields
    known = {field.key: field for field in fields}
    unknown = sorted(set(meta) - set(known))
    if unknown:
        _fail("meta_fields", f"未知字段：{', '.join(unknown)}")

    normalized: dict[str, Any] = {}
    for field in fields:
        raw = meta.get(field.key)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            if field.required:
                _fail(field.key, f"「{field.label}」是必填字段")
            continue
        normalized[field.key] = _coerce_value(field, raw)
    return normalized or None


def _coerce_value(field: ContentField, raw: Any) -> Any:
    """把一个字段值校验并归一化成 JSON 可存的形态；失败即 422。"""
    kind = field.field_type

    if kind in _TEXT_LIMITS:
        if not isinstance(raw, str):
            _fail(field.key, f"「{field.label}」必须是文本")
        value = raw.strip() if kind == "text" else raw
        if not value:
            _fail(field.key, f"「{field.label}」不能为空")
        limit = _TEXT_LIMITS[kind]
        if len(value) > limit:
            _fail(field.key, f"「{field.label}」最多 {limit} 个字符")
        return value

    if kind == "number":
        if isinstance(raw, bool):
            _fail(field.key, f"「{field.label}」必须是数字")
        if isinstance(raw, (int, float)):
            number = float(raw)
        elif isinstance(raw, str):
            try:
                number = float(raw.strip())
            except ValueError:
                _fail(field.key, f"「{field.label}」必须是数字")
        else:
            _fail(field.key, f"「{field.label}」必须是数字")
        if number != number or number in (float("inf"), float("-inf")):  # NaN / Infinity
            _fail(field.key, f"「{field.label}」必须是有限数字")
        return int(number) if number.is_integer() else number

    if kind == "boolean":
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str) and raw.strip().lower() in {"true", "false", "1", "0"}:
            return raw.strip().lower() in {"true", "1"}
        _fail(field.key, f"「{field.label}」必须是布尔值")

    if kind == "select":
        if not isinstance(raw, str) or raw not in (field.options or []):
            _fail(field.key, f"「{field.label}」的取值必须是候选项之一")
        return raw

    if kind == "date":
        if not isinstance(raw, str) or not _DATE_RE.match(raw.strip()):
            _fail(field.key, f"「{field.label}」必须是 YYYY-MM-DD 格式的日期")
        try:
            date.fromisoformat(raw.strip())
        except ValueError:
            _fail(field.key, f"「{field.label}」不是合法日期")
        return raw.strip()

    if kind == "datetime":
        if not isinstance(raw, str):
            _fail(field.key, f"「{field.label}」必须是日期时间")
        text = raw.strip()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            _fail(field.key, f"「{field.label}」必须是 ISO 8601 日期时间")
        # 朴素值按 UTC 解释（与 hero 排期窗同一口径）：带偏移的入参折算成 UTC 表示。
        # 这个字段是纯数据，前端不按本地时区展示；口径统一才谈得上"同一个瞬时同一个值"。
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).isoformat()

    if kind in {"image", "url"}:
        if not isinstance(raw, str):
            _fail(field.key, f"「{field.label}」必须是链接文本")
        value = raw.strip()
        if not value:
            _fail(field.key, f"「{field.label}」不能为空")
        if len(value) > 500:
            _fail(field.key, f"「{field.label}」最多 500 个字符")
        try:
            reject_pseudo_url_scheme(value)
        except ValueError as exc:
            _fail(field.key, str(exc))
        if not (value.startswith("/") or value.lower().startswith(("http://", "https://"))):
            _fail(field.key, f"「{field.label}」必须是站内路径（/…）或 http(s) 链接")
        return value

    # field_type 已由 ContentField 的 pattern 收口，走到这里说明模型契约被改坏
    _fail(field.key, f"不支持的字段类型：{kind}")
