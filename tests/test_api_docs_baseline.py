"""API 文档基线守卫：每个 JSON 端点都必须声明响应体 schema。

为什么需要它：本仓曾经有 166 个端点既无 `response_model` 也无 `responses` 声明，
OpenAPI 里只查得到"有个 200"而查不到字段形态，前端只能靠试错对接。补完之后
必须钉住基线，否则新增端点会无声地把缺口重新积累回去。

口径与手法（与 backend/api 现状一致，写在 `--` 下面）：
  - 已文档化 = 装饰器有 `responses={2xx: {"model": M}}` / 非 JSON 端点有
    `raw_content_response(...)` 媒体类型声明 / 函数有真实模型返回注解 / 204-205 无响应体。
  - `-> Any`、`-> dict[str, Any]` **不算**已文档化：实测本仓 FastAPI 会把它们派生成
    真实 response_model，端点一旦返回裸 ORM 实例就 500，而 OpenAPI 里只多出
    `"title": "Response Xyz..."` 噪声、连 `$ref` 都不产出。
  - 同理禁止给返回裸 dict 的端点加过滤性 `response_model=`（会静默删掉 SSR 页面在读的字段）。

不读 OpenAPI 产物而直接静态扫源码：本仓 FastAPI 版本把 `include_router()` 的结果懒挂载
成 `_IncludedRouter`，`app.routes` 只有 54 项而 spec 有 284 条路径，且嵌套路由 `.path`
不带 prefix，把路由对象与 spec 对齐极易错位（曾把 166 个缺口误报成 5 个）。
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[1] / "backend" / "api"
VERBS = {"get", "post", "put", "patch", "delete"}
NO_BODY_ATTRS = {"HTTP_204_NO_CONTENT", "HTTP_205_RESET_CONTENT"}
NO_BODY_CONSTS = {204, 205}
# 派生后零文档价值、却会引入隐式校验层的注解形态（见模块 docstring）
USELESS_ANNOTS = {"any", "dict[str,any]", "dict[str,object]", "list[any]", "list[dict[str,any]]"}

# 缺口已清零：每个 JSON 端点都必须带响应体 schema，任何新增端点都得一并补齐。
# 若确有"返回二进制/文本"这类无 schema 的端点，用 backend.schemas.raw_content_response
# 声明真实媒体类型，不要退回裸 200。
GAP_BASELINE = 0


def _route_decorators(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Call]:
    return [
        d
        for d in node.decorator_list
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr in VERBS
    ]


def _keywords(decs: list[ast.Call], name: str) -> list[ast.keyword]:
    return [kw for d in decs for kw in d.keywords if kw.arg == name]


def _annotation_is_documenting(src: str, node) -> bool:
    if node.returns is None:
        return False
    text = (ast.get_source_segment(src, node.returns) or "").replace(" ", "").lower()
    return text not in USELESS_ANNOTS


def _has_2xx_schema(src: str, decs: list[ast.Call]) -> bool:
    for kw in _keywords(decs, "responses"):
        if isinstance(kw.value, ast.Call):
            # raw_content_response(...) 只在运行时展开成 dict，按函数名识别
            func = kw.value.func
            return isinstance(func, ast.Name) and func.id == "raw_content_response"
        if not isinstance(kw.value, ast.Dict):
            continue
        for key, val in zip(kw.value.keys, kw.value.values):
            code = key.value if isinstance(key, ast.Constant) else None
            if not (isinstance(code, int) and 200 <= code < 300 and isinstance(val, ast.Dict)):
                continue
            for vk, vv in zip(val.keys, val.values):
                name = vk.value if isinstance(vk, ast.Constant) else None
                if name == "model" and not (isinstance(vv, ast.Constant) and vv.value is None):
                    return True
                if name == "content" and (ast.get_source_segment(src, vv) or "").strip() not in (
                    "",
                    "{}",
                ):
                    return True
    return False


def _has_no_body_status(decs: list[ast.Call]) -> bool:
    for kw in _keywords(decs, "status_code"):
        value = kw.value
        if isinstance(value, ast.Attribute) and value.attr in NO_BODY_ATTRS:
            return True
        if isinstance(value, ast.Constant) and value.value in NO_BODY_CONSTS:
            return True
    return False


def _has_response_model(decs: list[ast.Call]) -> bool:
    for kw in _keywords(decs, "response_model"):
        if not (isinstance(kw.value, ast.Constant) and kw.value.value is None):
            return True
    return False


def collect_gaps() -> list[str]:
    """返回「未声明响应体 schema」的端点标识：文件::行::函数名。"""
    gaps: list[str] = []
    for base, dirs, files in os.walk(API_DIR):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            path = Path(base) / fn
            src = path.read_text(encoding="utf-8")
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                decs = _route_decorators(node)
                if not decs:
                    continue
                if (
                    _has_response_model(decs)
                    or _has_2xx_schema(src, decs)
                    or _has_no_body_status(decs)
                    or _annotation_is_documenting(src, node)
                ):
                    continue
                rel = path.relative_to(API_DIR.parent.parent).as_posix()
                gaps.append(f"{rel}::{node.lineno}::{node.name}")
    return sorted(gaps)


def test_api_response_schema_baseline():
    gaps = collect_gaps()
    assert len(gaps) <= GAP_BASELINE, (
        f"API 响应文档缺口回退：{len(gaps)} > 基线 {GAP_BASELINE}\n"
        "请给端点补 responses={200: {'model': ...}}（文档用，不过滤运行时字段）"
        "或非 JSON 端点的 raw_content_response(...)：\n" + "\n".join(gaps)
    )


@pytest.mark.parametrize("module", ["backend.api"])
def test_no_useless_any_annotations_on_routes(module):
    """路由不得再用 `-> Any` / `-> dict[str, Any]` 凑文档（会派生真实 response_model）。"""
    offenders: list[str] = []
    for base, dirs, files in os.walk(API_DIR):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            path = Path(base) / fn
            src = path.read_text(encoding="utf-8")
            for node in ast.walk(ast.parse(src)):
                if (
                    not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    or node.returns is None
                ):
                    continue
                if not _route_decorators(node):
                    continue
                text = (ast.get_source_segment(src, node.returns) or "").replace(" ", "").lower()
                if text in USELESS_ANNOTS:
                    rel = path.relative_to(API_DIR.parent.parent).as_posix()
                    offenders.append(f"{rel}::{node.lineno}::{node.name} -> {text}")
    assert not offenders, (
        "这些注解会被 FastAPI 派生成 response_model（返回裸 ORM 实例即 500）且不产出 $ref，"
        "改用 responses={200: {'model': M}}：\n" + "\n".join(offenders)
    )
