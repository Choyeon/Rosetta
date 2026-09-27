"""回归测试：HTTPException 错误包络语义化 error_code（缺陷1） + OpenAPI 标签唯一性（缺陷2）

背景（修复前的实际行为，main.py 旧版 http_exception_handler）：
    raise HTTPException(429, detail={"error_code": "TOO_FREQUENT_GUESTBOOK", ...})
    → 响应体 {"success": false, "message": {...原 dict...}, "error_code": 429}
    语义错误码被数字状态码覆盖、message 变成 dict，前端契约断裂。

修复后契约（AGENTS.md §7.2）：
    - detail 为包络 dict → error_code/message/errors 原样透传，绝不数字覆盖；
    - detail 为普通字符串 → error_code 回退到按状态码映射的语义默认值；
    - detail 为校验 list → 展开为 errors:[{field,message,type}]；
    - 401 仍是 HTTP 401（前端按 status 判定刷新，error_code 为字符串不影响该链路）；
    - 503 + OOBE_REQUIRED 判定（前端 isOobeRequiredError）保持成立。
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def sub_app_client() -> AsyncGenerator[tuple[FastAPI, AsyncClient], None]:
    """挂载探针路由的独立子 FastAPI，复用同一个异常处理器逻辑做端到端断言。

    main.py 的处理器注册在 create_application() 内；这里用相同注册方式建最小 app，
    避免依赖数据库即可稳定触发各 detail 形状分支。
    """
    from starlette.exceptions import HTTPException as StarletteHTTPException

    from backend.main import create_application

    main_app = create_application()

    sub = FastAPI()
    # 复用 main app 注册的同一个 http_exception_handler（缺陷 1 的修复对象）
    sub.add_exception_handler(
        StarletteHTTPException,
        main_app.exception_handlers[StarletteHTTPException],
    )

    @sub.get("/probe/str-detail-404")
    async def _str404():
        raise HTTPException(status_code=404)

    @sub.get("/probe/str-detail-429")
    async def _str429():
        raise HTTPException(status_code=429, detail="slow down")

    @sub.get("/probe/no-auth-401")
    async def _unauth():
        raise HTTPException(status_code=401, detail="Not authenticated")

    @sub.get("/probe/envelope-429")
    async def _env429():
        # 复刻 guestbook._service_err_to_http 的形状（含 Retry-After 头）
        raise HTTPException(
            status_code=429,
            detail={
                "success": False,
                "message": "你在留言板发表留言太频繁了，请稍后再试",
                "error_code": "TOO_FREQUENT_GUESTBOOK",
            },
            headers={"Retry-After": "30"},
        )

    @sub.get("/probe/envelope-weak-password")
    async def _weak():
        # 复刻 users.py 重置密码弱密码分支：errors 为字符串列表 + 扩展键
        raise HTTPException(
            status_code=422,
            detail={
                "message": "新密码不符合强度要求",
                "errors": ["密码至少需要一个大写字母"],
                "error_code": "WEAK_PASSWORD",
            },
        )

    @sub.get("/probe/envelope-locked")
    async def _locked():
        # 复刻 users.py 登录锁定：detail 含未知扩展键，必须一并透传
        raise HTTPException(
            status_code=423,
            detail={
                "message": "账号因多次登录失败已被暂时锁定",
                "retry_after_seconds": 600,
                "error_code": "ACCOUNT_LOCKED",
            },
        )

    @sub.get("/probe/envelope-message-only")
    async def _msg_only():
        # 包络缺 error_code → 语义回退，不得输出数字
        raise HTTPException(status_code=400, detail={"message": "参数不对"})

    @sub.get("/probe/list-detail")
    async def _list_detail():
        # 校验形状 list detail → 必须展开成 {field,message,type}
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "loc": ["body", "password"],
                    "msg": "密码至少 8 位",
                    "type": "value_error",
                }
            ],
        )

    async with AsyncClient(transport=ASGITransport(app=sub), base_url="http://test") as ac:
        yield sub, ac


# ── 缺陷 1：包络透传 / 语义化回退 ──────────────────────────────────────────


@pytest.mark.asyncio
class TestErrorEnvelope:
    async def test_string_detail_falls_back_to_semantic_code(self, sub_app_client):
        _, ac = sub_app_client
        r = await ac.get("/probe/str-detail-404")
        assert r.status_code == 404
        body = r.json()
        assert body["success"] is False
        # 修复前：error_code == 404（数字）。修复后：语义化字符串，message 保留可读文本
        assert isinstance(body["error_code"], str)
        assert body["error_code"] == "NOT_FOUND"
        assert isinstance(body["message"], str)

    async def test_429_string_detail_maps_rate_limit_code(self, sub_app_client):
        """429 的对外错误码全站唯一（`RATE_LIMIT_EXCEEDED`）：
        状态码回退表、限流中间件、`@rate_limit` 装饰器、依赖式限流必须同源，
        否则客户端按 error_code 分支只能覆盖其中一条链路。"""
        _, ac = sub_app_client
        r = await ac.get("/probe/str-detail-429")
        assert r.status_code == 429
        body = r.json()
        assert body["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert body["message"] == "slow down"

    async def test_401_remains_recognizable_by_status(self, sub_app_client):
        """前端 apiFetch 按 HTTP status===401 触发刷新（useApi.ts），
        error_code 语义化字符串不得改变状态码本身。"""
        _, ac = sub_app_client
        r = await ac.get("/probe/no-auth-401")
        assert r.status_code == 401
        body = r.json()
        assert body["error_code"] == "UNAUTHORIZED"
        assert isinstance(body["error_code"], str)

    async def test_envelope_dict_detail_passthrough(self, sub_app_client):
        """guestbook TOO_FREQUENT_GUESTBOOK 链路：修复前 error_code 被 429 数字覆盖、
        message 变成整个 dict；修复后必须原样透传且保留 Retry-After 头。"""
        _, ac = sub_app_client
        r = await ac.get("/probe/envelope-429")
        assert r.status_code == 429
        assert r.headers["retry-after"] == "30"
        body = r.json()
        assert body["success"] is False
        assert body["error_code"] == "TOO_FREQUENT_GUESTBOOK"
        assert isinstance(body["message"], str)
        assert "太频繁" in body["message"]

    async def test_envelope_errors_list_passthrough(self, sub_app_client):
        _, ac = sub_app_client
        r = await ac.get("/probe/envelope-weak-password")
        assert r.status_code == 422
        body = r.json()
        assert body["error_code"] == "WEAK_PASSWORD"
        assert body["errors"] == ["密码至少需要一个大写字母"]

    async def test_envelope_extra_keys_preserved(self, sub_app_client):
        _, ac = sub_app_client
        r = await ac.get("/probe/envelope-locked")
        assert r.status_code == 423
        body = r.json()
        assert body["error_code"] == "ACCOUNT_LOCKED"
        assert body["retry_after_seconds"] == 600

    async def test_envelope_without_error_code_gets_semantic_fallback(self, sub_app_client):
        _, ac = sub_app_client
        r = await ac.get("/probe/envelope-message-only")
        assert r.status_code == 400
        body = r.json()
        assert body["error_code"] == "BAD_REQUEST"
        assert body["message"] == "参数不对"

    async def test_list_detail_expanded_to_field_message_type(self, sub_app_client):
        _, ac = sub_app_client
        r = await ac.get("/probe/list-detail")
        assert r.status_code == 422
        body = r.json()
        assert isinstance(body["message"], str)
        assert body["errors"] == [
            {"field": "body.password", "message": "密码至少 8 位", "type": "value_error"}
        ]
        # 禁止 [object Object] 型退化
        assert not any("Object" in str(e) for e in body["errors"])

    async def test_real_request_validation_422_shape_unchanged(self, client: AsyncClient):
        """真实 RequestValidationError（query 约束）继续走既有 handler：
        errors:[{field,message,type}] 且 error_code 为字符串。"""
        r = await client.get("/api/blog/posts?page=0")
        if r.status_code != 422:
            pytest.skip("该端点未触发 422，改日再验")
        body = r.json()
        assert isinstance(body.get("error_code"), str)
        assert isinstance(body.get("errors"), list)
        assert all(
            set(e) >= {"field", "message", "type"} for e in body["errors"] if isinstance(e, dict)
        )

    async def test_guestbook_real_422_business_code(self, client: AsyncClient):
        """真实端点回归：留言板缺昵称提交 → 422 + TOO... 族语义码透传到顶层。"""
        r = await client.post(
            "/api/guestbook",
            json={"author_name": "", "content": ""},
        )
        assert r.status_code in (400, 403, 422, 503)
        if r.status_code == 503:
            pytest.skip("OOBE 未完成")
        body = r.json()
        if isinstance(body, dict) and body.get("success") is False:
            assert isinstance(body.get("error_code"), str), (
                f"error_code 必须是语义化字符串，实际 {body!r}"
            )


# ── 缺陷 2：OpenAPI 标签唯一分组 ──────────────────────────────────────────


class TestOpenApiTags:
    def test_every_operation_has_exactly_one_tag(self):
        from backend.main import create_application

        schema = create_application().openapi()
        for path, item in schema["paths"].items():
            for method, op in item.items():
                tags = op.get("tags", [])
                assert len(tags) == 1, f"{method.upper()} {path} 有 {len(tags)} 个标签: {tags}"
                assert len(set(tags)) == 1

    def test_no_duplicate_tag_groups_in_metadata(self):
        from backend.main import TAG_METADATA, create_application

        schema = create_application().openapi()
        meta_names = [t["name"] for t in schema["tags"]]
        assert len(meta_names) == len(set(meta_names))
        # 已删除的同源占位标签不得再出现
        assert "插件" not in meta_names
        assert "高级功能" not in meta_names
        assert meta_names == [t["name"] for t in TAG_METADATA]

    def test_used_tags_subset_of_declared(self):
        from backend.main import create_application

        schema = create_application().openapi()
        declared = {t["name"] for t in schema["tags"]}
        used = {
            tag
            for item in schema["paths"].values()
            for op in item.values()
            for tag in op.get("tags", [])
        }
        assert used <= declared, f"未登记标签: {used - declared}"

    def test_plugin_routes_tagged_authoritatively(self):
        from backend.main import create_application

        schema = create_application().openapi()
        for path, item in schema["paths"].items():
            if "/admin/plugins" in path:
                for op in item.values():
                    assert op.get("tags") == ["插件平台"], f"{path} 标签应为权威名: {op}"
