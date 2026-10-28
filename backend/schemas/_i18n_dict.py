"""i18n JSON 列在 schema 层的形态闸门（单源）。

声明为 `dict[str, str]` 的列**不保证**是 dict：导入工具、早期写入路径、直接写库都会留下
`title="技术"` 这种单语行（`core/i18n.py::get_i18n_value` 早就认这一支，说明它不是假设）。
纯函数侧认了，**Pydantic 侧没认**——`dict[str, str]` 遇到裸字符串直接 ValidationError，
FastAPI 把它当成响应序列化失败 → 整口 500。同一篇脏数据在分类列表、标签列表、导航、
独立页、友链、系列、评论里的头衔徽章各炸一次，而且都是匿名可读口。

这里提供两件东西，避免 8 个调用点各写一遍 isinstance：

- `I18nDict`：字段类型注解。裸字符串折成 `{默认语言: 原文}`，其余形态原样交给
  `dict[str, str]` 校验（真写坏了形态仍然该报错，不静默吞）。
- `as_i18n_dict`：给"拿到 ORM 值就要 `.items()` 遍历"的调用点用的同一条归一函数。

折成**单语 dict**（而不是四语复制）是刻意的：正文可能几 MB，四份拷贝等于把响应体撑大四倍；
而前端 `pickLocalizedText` 与后端 `get_i18n_value` 都带"取不到当前语言就回退"的链，
观测到的文本与折之前完全一致。

住叶子模块（与 `_url_policy.py` 同族）：`schemas/__init__.py` 要在**定义期**拿到它做字段注解。
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BeforeValidator

from backend.core.i18n import DEFAULT_LANGUAGE


def as_i18n_dict(value: Any) -> Any:
    """裸字符串 → 单语 dict；dict / None 原样返回。"""
    if isinstance(value, str):
        # 空白串折成空 dict：语义是"没有内容"，不是"默认语言下躺着一串空白"。
        return {} if not value.strip() else {DEFAULT_LANGUAGE: value}
    return value


I18nDict = Annotated[dict[str, str], BeforeValidator(as_i18n_dict)]
