"""SQLite 写得通、生产 PG 直接 500 的那两类方言差异守卫。

本仓测试跑在 SQLite 上，CI 也跑在 SQLite 上，而生产是 PostgreSQL + asyncpg。两类
写法在 SQLite 下完全合法、在 PG 下要么在 bind 阶段抛 `DataError`，要么在服务端解析
阶段抛 `UndefinedFunctionError`，两者都表现为"接口恒 500"：

1. **naive 时间列收到 aware datetime。** 早期 `create_all` 建出的表里，时间列是
   `TIMESTAMP WITHOUT TIME ZONE`（`favorites` / `favorite_folders` / `captcha_records` /
   `webhook_endpoints` / `webhook_deliveries`），而默认值写成 `datetime.now(UTC)` 时，
   SQLite 落库静默丢 tz、测试全绿，asyncpg 却拒绝把带 tzinfo 的值绑给 naive 列。
   实例：收藏按钮、创建 Webhook、Webhook「测试发送」在生产各 500 若干轮。
2. **JSON 列与裸字符串比较。** PG 侧 JSON 列是 jsonb，`jsonb = character varying`
   没有对应操作符，SQLAlchemy 也不会补 cast。实例：`_missing_i18n_json` 里的
   `column == ""` 让「检索字段体检」与「补全检索字段」两个工具页在生产恒 500。

守卫口径来自实测（生产机 `information_schema` + 逐条 SQL 变体试跑），不是推测。
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from sqlalchemy import JSON, DateTime
from sqlalchemy.schema import ColumnDefault

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"


def _all_mapped_classes() -> list[type]:
    """把所有 ORM 类收集出来（含定义在 api/*.py 里的表）。"""
    import backend.main  # noqa: F401  导入即注册全部路由与其内联模型
    from backend.core.database import Base

    return [m.class_ for m in Base.registry.mappers]


def _naive_datetime_columns() -> list[tuple[str, str, object]]:
    out = []
    for cls in _all_mapped_classes():
        for col in cls.__table__.columns:
            if isinstance(col.type, DateTime) and not getattr(col.type, "timezone", False):
                out.append((cls.__tablename__, col.name, col))
    return out


def test_naive_timestamp_columns_never_default_to_aware_datetime():
    """每张 naive 时间列的可调用默认值/onupdate 必须返回 naive UTC。

    生产 PG 的 `timestamp without time zone` 不接受带 tzinfo 的绑定值；SQLite 会
    悄悄丢掉 tzinfo，所以这条只能静态钉住（默认值函数是纯 Python，跑得动）。
    """
    cols = _naive_datetime_columns()
    assert cols, "元数据里应当存在 naive 时间列——本守卫失去对象说明口径变了，需同步修改"

    offenders = []
    for table, name, col in cols:
        for label, d in (("default", col.default), ("onupdate", col.onupdate)):
            if not (isinstance(d, ColumnDefault) and d.is_callable):
                continue
            # SQLAlchemy 可能按内部约定包一层带列上下文的签名，两种调用形态都试
            try:
                value = d.arg({})
            except TypeError:
                value = d.arg()
            if not (isinstance(value, datetime) and value.tzinfo is None):
                offenders.append(f"{table}.{name}({label})")
    assert not offenders, (
        f"naive 时间列的默认值返回了 aware datetime，生产 PG 会在 bind 阶段 500：{offenders}；"
        "改用 backend.utils.compat.utc_now_naive"
    )


def test_json_column_empty_predicate_compiles_for_postgresql():
    """`_missing_i18n_json` 编译成 PG SQL 后，比较左侧必须带 CAST。

    旧写法里的 `column == ""` 渲染成 `posts.excerpt = $1::VARCHAR`，PG 在解析阶段
    报 `operator does not exist: jsonb = character varying`；SQLite 全绿。
    """
    from sqlalchemy.dialects import postgresql

    from backend.api.admin import _missing_i18n_json
    from backend.models.blog import Post

    sql = str(_missing_i18n_json(Post.excerpt).compile(dialect=postgresql.dialect()))
    assert "CAST(posts.excerpt AS VARCHAR)" in sql, sql
    # 不允许再出现"裸列 = 参数"的比较（左侧必须是 CAST(...)）
    assert re.search(r"posts\.excerpt\s*=\s*\$", sql) is None, sql

    # SQLite 侧同一表达式必须照常可编译，避免修 PG 把开发库改炸
    from sqlalchemy.dialects import sqlite

    str(_missing_i18n_json(Post.excerpt).compile(dialect=sqlite.dialect()))


def test_no_backend_source_compares_a_json_column_to_a_string_literal():
    """全仓静态扫：JSON 列不得与字符串字面量直接 == / != 比较。

    判定按"拥有该列的模型类名 + 属性名"匹配，避免把 String 列的同名属性
    （如 `Navigation.title`）误报成违规。
    """
    json_attrs: set[tuple[str, str]] = set()
    for cls in _all_mapped_classes():
        for col in cls.__table__.columns:
            if isinstance(col.type, JSON):
                json_attrs.add((cls.__name__, col.name))
    assert json_attrs, "元数据里应当存在 JSON 列——本守卫失去对象说明口径变了，需同步修改"

    violations = []
    for path in sorted(BACKEND_DIR.rglob("*.py")):
        source = path.read_text(encoding="utf-8", errors="ignore")
        if "==" not in source and "!=" not in source:
            continue
        for model, attr in json_attrs:
            if re.search(rf"\b{model}\.{attr}\s*(==|!=)\s*[\"']", source):
                violations.append(f"{path.relative_to(BACKEND_DIR.parent)}: {model}.{attr}")
    assert not violations, (
        f"JSON 列与字符串字面量直接比较，PG 下 jsonb = varchar 无操作符：{violations}；"
        "改成 cast(col, String) 再比，或走 api/admin.py::_missing_i18n_json"
    )
