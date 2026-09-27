"""
从后端源码反向生成 `backend/docs/error_codes.md` 的错误码清单。

动机（2026-09 实测）：该文档原有 49 个错误码，其中 **36 个在代码里根本不存在**
（`USER_NOT_FOUND` / `TOKEN_INVALID` / `LOGIN_RATE_LIMITED` 这一整批），
而真实存在的 62 个（`AUTH_INVALID_CREDENTIALS` / `PACKAGE_*` / `PLUGIN_*` / `UPLOAD_*` 系列）
一个都没写。前端按文档分支处理错误时，命中的是幻觉码，真实码全部落到默认分支。

事实来源改为源码（正则逐调用点扫描 + 上下文窗口提取 status/message）：
- `HTTPException(status_code=..., detail={"error_code": ..., "message": ...})`
- `AppException(status_code=..., error_code=..., message=...)` 及其子类的 `super().__init__`
- `core/exceptions.py` 的模块级常量（`NAME = "NAME"`）
- `main.py::_STATUS_ERROR_CODES`（状态码 → 语义回退码）

用法::

    uv run python -m backend.scripts.gen_error_codes --write
    uv run python -m backend.scripts.gen_error_codes --check

输出必须完全确定（不写时间戳），否则逐字比对没有意义。
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
DOC_PATH = REPO_ROOT / "backend" / "docs" / "error_codes.md"

BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED:ERROR_CODE_INDEX 由 backend/scripts/gen_error_codes.py 生成，请勿手改 -->"  # noqa: E501
END_MARKER = "<!-- END AUTO-GENERATED:ERROR_CODE_INDEX -->"

_CONST_RE = re.compile(r"^\s*([A-Z][A-Z0-9_]{3,})\s*=\s*\"\1\"$", re.M)
_STATUS_MAP_ENTRY_RE = re.compile(r"^\s*(\d{3}):\s*\"([A-Z][A-Z0-9_]{2,})\",?$", re.M)

# 调用点里的错误码字面量：`"error_code": "NAME"`（detail 包络）或 `error_code="NAME"`（kwarg）。
_CODE_RE = re.compile(r"error_code[\"']?\s*[:=]\s*[\"']([A-Z][A-Z0-9_]{2,})[\"']")
# AppException 子类经 super().__init__ 传参：group(1)=调用标记 group(2)=状态码 group(3)=码标识符。
_APP_EXC_RE = re.compile(
    r"(AppException|super\(\)\.__init__)\(\s*status_code\s*=\s*(\d{3})[^\)]*?error_code\s*=\s*"
    r"([A-Za-z_][A-Za-z0-9_]*)",
    re.S,
)
_STATUS_RE = re.compile(r"status_code\s*=\s*(\d{3})")
_MESSAGE_RE = re.compile(r"\"?message\"?\s*[:=]\s*\"([^\"]+)\"")
# 命中错误码后向前后各取若干字符作为上下文窗口，从中提取 status/message。
_WINDOW = 240


@dataclass
class CodeInfo:
    """一个错误码在源码里的全部出现证据。"""

    statuses: set[int] = field(default_factory=set)
    messages: set[str] = field(default_factory=set)
    files: set[str] = field(default_factory=set)


def _iter_py_files() -> Iterator[tuple[Path, str]]:
    for path in sorted(BACKEND_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        # 跳过 dev 工具脚本自身：其 docstring 里的 `NAME = "NAME"`、`error_code=...`
        # 示例会被扫成真错误码（自指假阳性）。真正产出错误码的都是 api/core/services。
        if "scripts" in path.relative_to(BACKEND_ROOT).parts:
            continue
        yield path, path.read_text(encoding="utf-8", errors="ignore")


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def collect() -> dict[str, CodeInfo]:
    inventory: dict[str, CodeInfo] = {}

    def touch(code: str) -> CodeInfo:
        return inventory.setdefault(code, CodeInfo())

    for path, text in _iter_py_files():
        for match in _CODE_RE.finditer(text):
            info = touch(match.group(1))
            info.files.add(_rel(path))
            lo = max(0, match.start() - _WINDOW)
            hi = min(len(text), match.end() + _WINDOW)
            window = text[lo:hi]
            anchor = match.start() - lo
            # 只取"距错误码字面量最近"的那一个 status_code / message，避免把相邻调用点
            # 的状态码与文案串到一个码上（HTTPException 里 status_code 恒在 error_code 之前）。
            nearest_status, best_status = None, None
            for sm in _STATUS_RE.finditer(window):
                dist = min(abs(sm.start() - anchor), abs(sm.end() - anchor))
                if best_status is None or dist < best_status:
                    best_status, nearest_status = dist, int(sm.group(1))
            if nearest_status is not None:
                info.statuses.add(nearest_status)
            nearest_message, best_message = None, None
            for mm in _MESSAGE_RE.finditer(window):
                msg = mm.group(1)
                if msg.startswith("{") or "%s" in msg:
                    continue  # i18n 的 t("...") / 变量拼接不属于人类可读文案
                dist = min(abs(mm.start() - anchor), abs(mm.end() - anchor))
                if best_message is None or dist < best_message:
                    best_message, nearest_message = dist, msg
            if nearest_message is not None:
                info.messages.add(nearest_message)

        # 模块级常量与 AppException 子类：status/message 在类体内，窗口够用。
        for match in _CONST_RE.finditer(text):
            touch(match.group(1)).files.add(_rel(path))
        for match in _APP_EXC_RE.finditer(text):
            info = touch(match.group(3))
            info.statuses.add(int(match.group(2)))
            info.files.add(_rel(path))

        # 状态码回退表：`429: "RATE_LIMIT_EXCEEDED",` 这类映射没有 error_code= 字面量。
        if path.name == "main.py":
            block = text[text.find("_STATUS_ERROR_CODES") :]
            block = block[: block.find("}")]
            for status, code in _STATUS_MAP_ENTRY_RE.findall(block):
                info = touch(code)
                info.statuses.add(int(status))
                info.files.add(_rel(path))
    return inventory


def _family(code: str) -> str:
    prefix = code.split("_", 1)[0]
    return {
        "AUTH": "认证与授权",
        "OOBE": "OOBE 安装向导",
        "PLUGIN": "插件系统",
        "THEME": "主题系统",
        "MODS": "主题系统",
        "PACKAGE": "扩展包（插件/主题）下载与解压",
        "MARKET": "扩展市场",
        "REMOTE": "远程来源",
        "MANIFEST": "清单校验",
        "SCHEMA": "清单校验",
        "UPLOAD": "文件上传",
        "TOKEN": "令牌与刷新",
        "RESET": "密码重置",
        "PASSWORD": "密码策略",
        "WEAK": "密码策略",
        "CSRF": "CSRF",
        "RATE": "限流与锁定",
        "ACCOUNT": "限流与锁定",
        "ADMIN": "OOBE 安装向导",
    }.get(prefix, "通用与状态码回退")


_ORDER = [
    "通用与状态码回退",
    "认证与授权",
    "令牌与刷新",
    "密码重置",
    "密码策略",
    "限流与锁定",
    "CSRF",
    "OOBE 安装向导",
    "文件上传",
    "插件系统",
    "主题系统",
    "扩展包（插件/主题）下载与解压",
    "扩展市场",
    "远程来源",
    "清单校验",
]


def render(inventory: dict[str, CodeInfo]) -> str:
    groups: dict[str, list[tuple[str, CodeInfo]]] = {}
    for code, info in inventory.items():
        groups.setdefault(_family(code), []).append((code, info))

    lines: list[str] = [
        "## 错误码清单（自动生成）",
        "",
        f"本区块由 `backend/scripts/gen_error_codes.py` 扫描 `backend/**/*.py` 生成，"
        f"共 **{len(inventory)} 个真实存在的错误码**。",
        "",
        "- 出处列只列到文件级：同一个码可能出现在多个端点，具体判定看源码。",
        "- HTTP 列为该码在当前源码里能推断出的状态码；`—` 表示该码由 AppException 子类外的"
        "路径抛出且附近没有 `status_code=`（以调用点为准）。",
        "- 新增/删除错误码后跑 `uv run python -m backend.scripts.gen_error_codes --write`，"
        "否则 `tests/test_docs_error_codes_sync.py` 会失败。",
        "",
    ]
    ordered_families = [f for f in _ORDER if f in groups] + sorted(set(groups) - set(_ORDER))
    for family in ordered_families:
        entries = sorted(groups[family])
        lines += [
            f"### {family}（{len(entries)}）",
            "",
            "| 错误码 | HTTP | 说明 | 出处 |",
            "| --- | --- | --- | --- |",
        ]
        for code, info in entries:
            status = "/".join(str(s) for s in sorted(info.statuses)) or "—"
            message = sorted(info.messages)[0] if info.messages else "—"
            files = "<br>".join(f"`{f}`" for f in sorted(info.files))
            safe = message.replace("|", "\\|")
            lines.append(f"| `{code}` | {status} | {safe} | {files} |")
        lines.append("")
    return "\n".join(lines).rstrip("\n")


def build(doc: str) -> str:
    body = render(collect())
    start = doc.find(BEGIN_MARKER)
    end = doc.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        raise SystemExit(f"文档缺少自动生成标记，请手工补上：{DOC_PATH}")
    return f"{doc[: start + len(BEGIN_MARKER)]}\n\n{body}\n\n{doc[end:]}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成 error_codes.md 错误码清单")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    doc = DOC_PATH.read_text(encoding="utf-8")
    new_doc = build(doc)

    if args.check:
        if new_doc != doc:
            sys.stderr.write(
                "error_codes.md 的错误码清单与源码不一致，"
                "请执行：uv run python -m backend.scripts.gen_error_codes --write\n"
            )
            return 1
        sys.stdout.write("错误码清单与源码一致\n")
        return 0

    if new_doc != doc:
        DOC_PATH.write_text(new_doc, encoding="utf-8")
        sys.stdout.write(f"已写回 {DOC_PATH.relative_to(REPO_ROOT)}\n")
    else:
        sys.stdout.write("内容未变化\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
