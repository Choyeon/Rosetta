"""
PATCH/PUT 局部更新写回守卫。

全仓十几个更新端点（以及 `repositories/base.py` 的通用 update）都是同一个形状：

```python
update_data = data.model_dump(exclude_unset=True)
for field, value in update_data.items():
    setattr(obj, field, value)
await db.flush()
```

`exclude_unset` 只丢掉"客户端没提这个 key"，**显式传 JSON `null` 会原样保留**。
而 Pydantic 侧为了表达"这个字段可选"普遍写成 `X | None = None`，于是
`{"color": null}` 这类包会一路 setattr 到 `nullable=False` 的列上：
`flush()` 抛 IntegrityError → `main.py` 的兜底 except 转成 **HTTP 500**
（客户端看到的是一句"服务器内部错误"，而它其实只是少传了一个颜色）。

这里按 ORM 元数据统一判定"目标列是否允许 NULL"，在写回之前拦成 422
（`ValidationException` → `{success:false, error_code:VALIDATION_ERROR}`），
新增列 / 新增端点不必再补一次手写校验。

判定依据是**列的 nullable**而不是 Python 注解：历史模型里
`Mapped[str | None]` 与 `nullable=False` 并不总是自洽，列约束才是真相。
"""

from typing import Any

from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.orm import ColumnProperty, RelationshipProperty

from backend.core.exceptions import ValidationException


def not_null_violations(target: Any, data: dict[str, Any]) -> list[str]:
    """返回 `data` 里"值为 null 但目标列 NOT NULL"的字段名。

    `target` 接受 ORM 实例或映射类；`data` 里不属于该 mapper 的键（如派生字段、
    关系属性）一律跳过，交由调用方原有逻辑处理。
    """
    # inspect(实例) 返回的是 InstanceState（.attrs 是 AttributeState，不是
    # ColumnProperty），inspect(类) 才返回 Mapper。端点写回时传的都是实例，
    # 若直接 inspect(target) 会把所有列当成"非 ColumnProperty"跳过，守卫形同虚设
    # ——显式 null 照样 setattr 到 NOT NULL 列、撞出 500。统一按类取 mapper。
    mapper = sqlalchemy_inspect(target if isinstance(target, type) else type(target))
    violations: list[str] = []
    for field, value in data.items():
        if value is not None:
            continue
        attr = mapper.attrs.get(field)
        if attr is None or isinstance(attr, RelationshipProperty):
            continue
        if not isinstance(attr, ColumnProperty):
            continue
        if all(column.nullable for column in attr.columns):
            continue
        violations.append(field)
    return violations


def validate_partial_update(target: Any, data: dict[str, Any]) -> None:
    """只校验不写回：给"还要再过一层 service/repository"的端点用。"""
    violations = not_null_violations(target, data)
    if violations:
        raise ValidationException(
            message=f"字段不允许为空：{', '.join(violations)}",
            details={"fields": violations},
        )


def apply_partial_update(target: Any, data: dict[str, Any]) -> None:
    """校验并写回，替代端点里裸的 `for k, v: setattr`。

    只写 mapper 里真实存在的属性（列 / 关系）。schema 常带"兼容字段 / 派生字段"
    （如 PhotoUpdate.original_url 会被并入 url，thumbnail_url / media_id 是前端别名占位），
    它们并非模型列。裸 setattr 会在实例上留下一个非映射属性，`db.refresh()` 只重载
    映射列、不会清掉它，于是 `Response.model_validate(obj)` 把这个"从没进库"的值回显给
    前端——客户端以为保存成功，下次拉取却消失。这里直接跳过非映射键，杜绝该假成功。
    """
    validate_partial_update(target, data)
    mapper = sqlalchemy_inspect(target if isinstance(target, type) else type(target))
    for field, value in data.items():
        if field not in mapper.attrs:
            continue
        setattr(target, field, value)
