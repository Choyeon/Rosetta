"""Pydantic schema 的严格化加固（`extra="forbid"`）。

原先这段逻辑在 7 个 schema 模块和包 `__init__` 里各抄了一份（共 8 份），
每份都把赋值包在 `except Exception: pass` 里。这里收敛为单一实现，并修掉
三个真实缺陷：

1. **事后改 `model_config` 字典本身不生效**：Pydantic v2 在类创建时就把配置
   编译进 core schema，实测 `A(x=1, junk=2)` 照样通过。必须 `model_rebuild()`
   才真正 forbid。
2. **加固失败不得静默**：`extra="forbid"` 拦的是"请求体多带字段被接受"，
   静默跳过等于门禁无声失效。本模块把导入期无法重建的类（跨模块前向引用，
   由 `backend/schemas/__init__.py` 末尾的延迟重建通道负责）登记到 `_PENDING`，
   由 `finalize_strict_extra_forbid()` 兜底；兜底仍失败才 `logger.error` 留痕。
3. **`strict: True` 一并去掉**。它和 forbid 一样从未真正生效过，而一旦生效，
   等于给**全部** schema 打开严格类型模式：`"12"` 不再转 int、SQLite 里以字符串
   存放的列回读到 int 字段直接报错。这不是安全项，是把一个从未验证过的全局
   策略悄悄推上线。真要收紧类型策略，应当逐 schema 显式声明并配测试。
"""

import logging

from pydantic import BaseModel, PydanticUndefinedAnnotation

logger = logging.getLogger(__name__)

_STRICT_EXTRA_FORBID = {"extra": "forbid"}

# 导入期引用还没解析出来的类，等包 __init__ 全部 import 完再重建。
_PENDING: list[type[BaseModel]] = []


def apply_strict_extra_forbid(namespace: dict, module_name: str) -> None:
    """给 `namespace` 里**本模块定义**的所有 BaseModel 子类补上严格配置。"""
    for obj in list(namespace.values()):
        if not (isinstance(obj, type) and issubclass(obj, BaseModel)):
            continue
        # 只处理本模块定义的类；包 __init__ re-export 进来的类型由其源模块加固。
        if obj is BaseModel or obj.__module__ != module_name:
            continue
        existing = obj.model_config if isinstance(obj.model_config, dict) else {}
        obj.model_config = {**existing, **_STRICT_EXTRA_FORBID}
        _rebuild(obj)


def _rebuild(obj: type[BaseModel]) -> None:
    try:
        obj.model_rebuild(force=True)
    except PydanticUndefinedAnnotation:
        _PENDING.append(obj)


def finalize_strict_extra_forbid() -> None:
    """包导入收尾时调用：重建登记下来的类，仍失败则如实报错。"""
    pending, _PENDING[:] = _PENDING, []
    for obj in pending:
        try:
            obj.model_rebuild(force=True)
        except PydanticUndefinedAnnotation as exc:
            logger.error(
                "schema %s.%s 无法重建，extra=forbid 未生效（前向引用解析不出，需补 import）：%s",
                obj.__module__,
                obj.__name__,
                exc,
            )
