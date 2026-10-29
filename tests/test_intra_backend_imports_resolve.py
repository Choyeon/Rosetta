"""仓内导入名必须真的存在（静态 AST 闸门）。

起因：2026-10-29 删 `backend/core/deps.py` 里那个 `RequireCSRF` 别名时，连同一行
`from backend.core.csrf import require_csrf` 一起删了。那行不是给 deps 自己用的，
但它把名字带进了 deps 的命名空间，而 `backend/api/comments.py` 的
`from backend.core.deps import (..., require_csrf)` 一直在吃这个转口 —— 删完
`from backend.main import app` 直接 ImportError。本机跑不了 pytest（没有 venv），
线上门禁又只在 collect-only 阶段报错、后面的重启照做，于是生产 API 停了整一个下午。

判据口径：
* 只查**仓内** `from backend.x.y import name`（不含 `import backend.x.y` 形态，那种由解释器
  自己按模块路径解析，没有"名字清单"可核对）；
* 目标模块的顶层可见名 = def/class/赋值/`from`-`import` 别名/`try:` 块里的导入与赋值，
  判定只看**顶层**，函数内部的局部赋值不算；
* 目标不是单个 .py 文件（包 `__init__.py`、C 扩展、命名空间包）时跳过：包的重导出常见
  `__getattr__` 懒加载，静态判会误报。
"""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
REPO_ROOT = BACKEND.parent


def _toplevel_names(path: Path) -> set[str]:
    """模块顶层可见的名字集合。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()

    def harvest(node: ast.stmt) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            # `import a.b.c` 在命名空间里只留下最左边的 a
            names.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.Try):
            for sub in [*node.body, *node.orelse, *node.finalbody]:
                harvest(sub)

    for node in tree.body:
        harvest(node)
    return names


def _module_path(node: ast.ImportFrom) -> Path | None:
    if node.level:  # 相对导入：留待解释器判，本闸门不碰
        return None
    module = node.module or ""
    if not module.startswith("backend."):
        return None
    candidate = REPO_ROOT / (module.replace(".", "/") + ".py")
    return candidate if candidate.is_file() else None


def _dangling() -> list[str]:
    problems: list[str] = []
    for src in sorted(BACKEND.rglob("*.py")):
        if "__pycache__" in src.parts:
            continue
        tree = ast.parse(src.read_text(encoding="utf-8"), filename=str(src))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            target = _module_path(node)
            if target is None:
                continue
            visible = _toplevel_names(target)
            for alias in node.names:
                if alias.name == "*":
                    continue
                if alias.name not in visible:
                    rel = src.relative_to(REPO_ROOT)
                    problems.append(f"{rel}:{node.lineno} from {node.module} import {alias.name}")
    return problems


def test_no_dangling_intra_backend_import_names():
    """删掉一个转口/别名之前，先问有没有人正在从那里 import 它。"""
    assert _dangling() == []


def test_guard_actually_sees_the_import_surface():
    """闸门本身不能是空的：仓内至少要有几百条 `from backend.*` 才算在管事。"""
    counted = 0
    for src in BACKEND.rglob("*.py"):
        if "__pycache__" in src.parts:
            continue
        tree = ast.parse(src.read_text(encoding="utf-8"), filename=str(src))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and _module_path(node) is not None:
                counted += len(node.names)
    assert counted > 300, counted
