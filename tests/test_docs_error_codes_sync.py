"""钉住 `error_codes.md` 的自动生成区块与源码扫描逐字一致。

动机：手写错误码文档曾列出 36 个代码里根本不存在的幻觉码，前端按幻觉码分支永远
命中默认路径。清单改由 `gen_error_codes.py` 从 `backend/**/*.py` 反向生成；本测试
保证"改了 error_code 却没跑生成脚本"会直接红。
"""

from __future__ import annotations

from backend.scripts.gen_error_codes import BEGIN_MARKER, DOC_PATH, END_MARKER, build, collect

# 旧手写文档里的幻觉码——源码从未产出过，必须不在扫描结果中。
_HALLUCINATED = {
    "USER_NOT_FOUND",
    "TOKEN_INVALID",
    "LOGIN_FAILED",
    "NOT_STAFF",
    "SUPERUSER_REQUIRED",
    "LOGIN_RATE_LIMITED",
    "PROFILE_NOT_PUBLIC",
}


def test_doc_carries_auto_generated_markers():
    doc = DOC_PATH.read_text(encoding="utf-8")
    assert BEGIN_MARKER in doc, "error_codes.md 缺少 BEGIN 标记，生成脚本无处写回"
    assert END_MARKER in doc, "error_codes.md 缺少 END 标记，生成脚本无处写回"


def test_inventory_matches_doc_byte_for_byte():
    doc = DOC_PATH.read_text(encoding="utf-8")
    assert build(doc) == doc, (
        "error_codes.md 与源码不一致，请运行：uv run python -m backend.scripts.gen_error_codes --write"
    )


def test_no_hallucinated_codes_survive():
    codes = set(collect())
    leaked = _HALLUCINATED & codes
    assert not leaked, f"以下幻觉码不应出现在扫描结果中：{sorted(leaked)}"


def test_dev_tooling_is_not_scanned():
    # 生成脚本自身 docstring 里的 `NAME = "NAME"` 示例不得被当成真错误码。
    assert "NAME" not in collect()
