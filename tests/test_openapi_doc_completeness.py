"""OpenAPI 文档完整性守卫。

`tests/test_api_docs_baseline.py` 只在各模块源码层面检查 `responses={...}` 有没有写，
它防不住两类问题：

1. 某个 router 导入失败或忘了 `include_router` —— 端点直接从文档里消失，
   源码级检查看不见"少掉的东西"；
2. 端点写了 `responses` 却没写 `description`，或 `summary`/`description` 全空 ——
   文档仍算合法，但 `/docs` 里是一片空白。

所以这里改成对**生成后的文档**断言：先卡一个操作数下限（端点只增不减），
再要求每个操作都有可读说明与带描述的响应块。
"""

from backend.main import app

# 操作数下限：当前实测 284 paths / 355 operations，留出余量。
# 新增端点不会触发；删端点或 router 掉线会触发——那时要么同步调低，要么把路由补回来。
MIN_OPERATIONS = 340

_HTTP_VERBS = ("get", "post", "put", "patch", "delete", "head", "options")


def _operations():
    """遍历生成后的 OpenAPI 文档，产出 ``(VERB path, operation)`` 二元组。"""
    spec = app.openapi()
    for path, item in spec["paths"].items():
        for verb in _HTTP_VERBS:
            op = item.get(verb)
            if op is not None:
                yield f"{verb.upper()} {path}", op


def test_openapi_document_generates():
    """文档必须可生成，且注册的端点数量不缩水。"""
    spec = app.openapi()
    assert spec["info"]["version"] == app.version

    ops = list(_operations())
    assert len(ops) >= MIN_OPERATIONS, (
        f"OpenAPI 只注册了 {len(ops)} 个操作，低于下限 {MIN_OPERATIONS}；"
        "检查是否有 router 未 include 或模块导入失败"
    )


def test_every_operation_is_documented():
    """每个操作都要有 summary 或 description，且响应块必须带描述。"""
    missing_prose: list[str] = []
    missing_responses: list[str] = []
    missing_resp_desc: list[str] = []

    for key, op in _operations():
        if not (op.get("summary") or "").strip() and not (op.get("description") or "").strip():
            missing_prose.append(key)

        responses = op.get("responses") or {}
        if not responses:
            missing_responses.append(key)
        for code, resp in responses.items():
            if not (resp.get("description") or "").strip():
                missing_resp_desc.append(f"{key} -> {code}")

    assert not missing_prose, f"以下操作既无 summary 也无 description：{missing_prose}"
    assert not missing_responses, f"以下操作没有 responses 块：{missing_responses}"
    assert not missing_resp_desc, f"以下响应码缺少 description：{missing_resp_desc}"
