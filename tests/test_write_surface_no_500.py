"""写入口的 500 闸门：每个写端点（JSON 与 multipart）都必须把"输入不对"判成 4xx，而不是把自己弄崩。

JSON 面先跑两轮（都由 OpenAPI 的 paths/requestBody 生成用例，新增端点自动进入巡检）：

1. `test_empty_body_is_not_a_server_error` —— 空 body `{}` 打过去。合法期望 422/400/404/403，**500 是服务端自己的崩溃**。
   这一轮覆盖的是"路由接线 + 依赖解析 + 权限判定"这段公共代码。
2. `test_synthesized_payload_is_not_a_server_error` —— 按 requestBody 的 JSON Schema 现场合成一份"类型正确"的载荷再打。
   空 body 会被 Pydantic 在校验层直接挡掉（压根进不到 handler），所以这一轮才真正走业务代码：
   崩点通常在"字段齐了以后继续往下"的那一行——关系取 None 后 `.id`、JSON 列按 dict 迭代、
   `int(None)`、枚举值落进 else 分支之前的裸访问。

排除清单（`_SKIP_FRAGMENTS`）不是"这些端点不重要"，而是"合成载荷打它们会做真正危险的事"：
迁移/备份还原/OOBE 安装会改进程与库结构，插件与主题的安装扫描会读写磁盘与市场缓存，
`cache/flush` 会清掉同批次其它用例正在依赖的缓存。它们各自有专门套件覆盖。

`TestMultipartSurfaceNever500` 补的是前两轮够不到的那条面（JSON 合成发不出文件，multipart
端点只能整条排除）：上传口按四种"递错东西"的形态各打一次——按 JSON 打、真 multipart 但漏掉
文件字段、扩展名/类型不对、名字与 MIME 合规但内容只有魔数的残缺图片。判据仍是"别 500"：
最后那条是扩展名白名单先放行、解析器随后接住截断流的地方，也是本仓安全红线里
"图片必须 Pillow verify"唯一能被接口面证明的形态。体积上限与 zip 解压炸弹另有套件，不在这里重复。

最后一轮的"牙齿"断言（`TestWriteSurfaceNever500.test_payload_generator_has_teeth`）是防这条守卫变成空壳：
如果合成的载荷全部被 422 挡在校验门外，前面那条 <500 就永远绿得毫无意义。
multipart 四轮有同族的 `test_multipart_rounds_reach_handlers`。
"""

import re
from typing import Any

import pytest
from httpx import AsyncClient

from backend.main import app

WRITE_METHODS = ("post", "put", "patch", "delete")

# 路径片段命中即跳过（见模块文档：合成载荷会触发真正危险的动作）
_SKIP_FRAGMENTS = (
    "/oobe",
    "/backup/restore",
    "/alembic",
    "/migration/",
    "/cache/flush",
    "/themes/market",
    "/themes/scan",
    "/plugins/market",
    "/plugins/scan",
    "/plugins/bulk",
    "/translate",
    "/webhooks/deliveries",
)

# `{param}` 的取值：主键类给 1（存在与否都只看状态码），slug/name 类给明显的假值。
_PARAM_SAMPLES = {
    "activity_id": "1",
    "album_id": "1",
    "announcement_id": "1",
    "category": "covers",
    "category_id": "1",
    "comment_id": "1",
    "delivery_id": "1",
    "emoji": "thumbsup",
    "entry_id": "1",
    "favorite_id": "1",
    "field": "nope",
    "filename": "nope.txt",
    "folder_id": "1",
    "group": "basic",
    "key": "nope",
    "link_id": "1",
    "media_id": "1",
    "message_id": "1",
    "nav_id": "1",
    "notification_id": "1",
    "page_id": "1",
    "photo_id": "1",
    "placeholder_id": "1",
    "poll_id": "1",
    "post_id": "1",
    "post_id_or_slug": "1",
    "revision_id": "1",
    "series_id": "1",
    "slide_id": "1",
    "slug": "does-not-exist",
    "tag": "does-not-exist",
    "tag_id": "1",
    "title_id": "1",
    "trash_id": "1",
    "user_id": "1",
    "webhook_id": "1",
}


def _resolve(path: str) -> str:
    out = path
    while "{" in out:
        start = out.index("{")
        end = out.index("}", start)
        name = out[start + 1 : end]
        value = _PARAM_SAMPLES.get(name)
        if value is None:  # 新增参数却不在样本表里：宁可显式失败，也不要拼出畸形 URL
            raise AssertionError(f"path param {name!r} has no sample value")
        out = out[:start] + value + out[end + 1 :]
    return out


def _write_operations() -> list[tuple[str, str, dict]]:
    """[(method, 已解析 URL, operation 对象)]，multipart 端点排除（合成不了文件）。"""
    rows: list[tuple[str, str, dict]] = []
    seen: set[tuple[str, str]] = set()
    for raw_path, operations in app.openapi()["paths"].items():
        if any(fragment in raw_path for fragment in _SKIP_FRAGMENTS):
            continue
        for method, operation in operations.items():
            if method not in WRITE_METHODS:
                continue
            content = operation.get("requestBody", {}).get("content", {})
            if "multipart/form-data" in content:
                continue
            key = (method.upper(), _resolve(raw_path))
            if key in seen:
                continue
            seen.add(key)
            rows.append((key[0], key[1], operation))
    return sorted(rows)


_OPERATIONS = _write_operations()


# ---------------------------------------------------------------------------
# 载荷合成：把 JSON Schema（含 $ref / allOf / anyOf）铺成一份类型正确的实例
# ---------------------------------------------------------------------------

_SPEC = app.openapi()
_SCHEMAS = _SPEC.get("components", {}).get("schemas", {})
_FORMAT_SAMPLES = {
    "email": "probe@example.com",
    "uuid": "00000000-0000-4000-8000-000000000001",
    "date": "2026-01-01",
    "date-time": "2026-01-01T00:00:00",
    "uri": "http://127.0.0.1:8000/probe",
    "binary": "probe",
    "byte": "cHJvYmU=",
}


def _deref(schema: dict) -> dict:
    """展开 $ref 与 allOf，返回可直接读 type/properties 的单层视图。

    Pydantic 的可选字段会铺成 `anyOf: [T, {type: null}]`——取第一个非常量分支即可，
    否则合成出来的是 None 而不是值，等于没填。
    """
    if not isinstance(schema, dict):
        return {}
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return _deref(_SCHEMAS.get(name, {}))
    if "allOf" in schema:
        merged: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
        for part in schema["allOf"]:
            piece = _deref(part)
            merged["properties"].update(piece.get("properties", {}))
            merged["required"] = list(set(merged["required"]) | set(piece.get("required", [])))
        return merged
    if "anyOf" in schema or "oneOf" in schema:
        branches = [
            _deref(part)
            for part in schema.get("anyOf") or schema.get("oneOf") or []
            if _deref(part).get("type") != "null"
        ]
        return branches[0] if branches else {}
    return schema


def _sample_for(schema: dict, key_hint: str = "") -> Any:
    schema = _deref(schema)
    if not schema:
        return "probe"
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]
    if "const" in schema:
        return schema["const"]
    if "default" in schema and schema["default"] is not None:
        return schema["default"]
    fmt = schema.get("format")
    if fmt in _FORMAT_SAMPLES:
        return _FORMAT_SAMPLES[fmt]
    # pattern 声明的字段拿通用串会被拒（`^[^<>]*$` 之类），但 "probe" 恰好不含尖括号；
    # 少数带长度下限的键给长一点的串，避免整条请求因为一个字段被 422 挡掉。
    kind = schema.get("type")
    if kind == "integer":
        return max(schema.get("minimum", 0), 1)
    if kind == "number":
        return max(schema.get("minimum", 0), 1.0)
    if kind == "boolean":
        return True
    if kind == "array":
        item = _sample_for(schema.get("items", {}), key_hint)
        minimum = schema.get("minItems", 0) or 0
        rows = [item] if minimum == 0 else [item] * int(minimum)
        return rows
    if kind == "object":
        props = schema.get("properties") or {}
        if props:
            required = set(schema.get("required", []))
            # 可选对象字段留空：把每一层都填满会让载荷偏离真实提交形态，
            # 而这一轮的判据是"别 500"，不是"必须 200"。
            return {k: _sample_for(v, k) for k, v in props.items() if k in required}
        return {}
    if kind == "string":
        min_length = int(schema.get("minLength", 0) or 0)
        text = "probe"
        if key_hint.lower() in {"title", "name", "slug", "url", "content", "excerpt", "password"}:
            text = f"probe-{key_hint}"
        return text if len(text) >= min_length else text * (min_length // len(text) + 1)
    return "probe"


def _payload_for(operation: dict) -> dict | None:
    """按 operation 的 requestBody schema 合成载荷；合成不出来返回 None（跳过该用例）。"""
    content = operation.get("requestBody", {}).get("content", {})
    schema = content.get("application/json", {}).get("schema")
    if not schema:
        return None
    schema = _deref(schema)
    if schema.get("type") != "object":
        return None
    props = schema.get("properties", {})
    if not props:
        return None
    required = set(schema.get("required", []))
    # 必填全给；非必填只给"看起来像内容"或"外键"的那几类：
    # - 内容类字段为空会让大半 handler 提前分支出去；
    # - `_id` 一律给 1，而 fixture 里 id=1 的文章/分类/标签/用户/评论都存在，
    #   于是"取关联对象再读属性"这条路真的被走到底（给 999 会在 404 处停下，检出率反而低）。
    # 把其余可选字段一并塞满会撞上更多校验分支，那些 422 恰好掩盖 handler 里的崩溃点。
    body = {k: _sample_for(v, k) for k, v in props.items() if k in required}
    for k, v in props.items():
        if k in body:
            continue
        if re.fullmatch(
            r"([a-z_]+_id|[a-z_]+Id|title|name|content|text|value|url|link|message|description)", k
        ):
            body[k] = _sample_for(v, k)
    return body or None


_EMPTY_CASES = [(m, u) for m, u, _op in _OPERATIONS]
_BODY_CASES = [
    (m, u, payload) for m, u, op in _OPERATIONS if (payload := _payload_for(op)) is not None
]
# 每条请求的实际状态码，用于"牙齿"断言：全被 422 挡住就等于这条守卫没在巡检业务代码。
_STATUS_LOG: list[tuple[str, str, int]] = []


class TestWriteSurfaceNever500:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method,url",
        _EMPTY_CASES,
        ids=[f"{m.lower()} {u}" for m, u in _EMPTY_CASES],
    )
    async def test_empty_body_is_not_a_server_error(
        self,
        client: AsyncClient,
        admin_headers: dict,
        method: str,
        url: str,
    ):
        response = await client.request(method, url, headers=admin_headers, json={})
        assert response.status_code < 500, (
            f"{method} {url} 空 body 返回 {response.status_code}：{response.text[:300]}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method,url,payload",
        _BODY_CASES,
        ids=[f"{m.lower()} {u}" for m, u, _p in _BODY_CASES],
    )
    async def test_synthesized_payload_is_not_a_server_error(
        self,
        client: AsyncClient,
        admin_headers: dict,
        method: str,
        url: str,
        payload: dict,
    ):
        response = await client.request(method, url, headers=admin_headers, json=payload)
        _STATUS_LOG.append((method, url, response.status_code))
        assert response.status_code < 500, (
            f"{method} {url} body={payload!r} 返回 {response.status_code}：{response.text[:300]}"
        )

    def test_payload_generator_has_teeth(self):
        """合成载荷必须真的打进足够多的 handler，而不是整批被校验层挡回 422。

        定义顺序保证它跑在上一轮之后（pytest 按声明顺序执行同一类里的用例）。
        下限取 40：本仓有真实业务写入的端点远多于此，跌破说明 Schema 合成整体失效。
        """
        non_validation = [row for row in _STATUS_LOG if row[2] not in (422,)]
        assert len(_STATUS_LOG) > 60, f"合成载荷只覆盖了 {len(_STATUS_LOG)} 条端点"
        assert len(non_validation) >= 40, (
            f"只有 {len(non_validation)}/{len(_STATUS_LOG)} 条请求穿过校验进到业务代码，"
            "这条守卫已经失去检出能力"
        )

    def test_candidate_list_is_populated(self):
        """清单本身不能塌成空集——路由整体掉线时上面的参数化会静默变成 0 条。"""
        assert len(_EMPTY_CASES) > 120, f"写端点清单只有 {len(_EMPTY_CASES)} 条，疑似路由未挂载"


# ---------------------------------------------------------------------------
# multipart 写入口：上一批把这条面"声明性排除"了，而它恰恰是用户最容易递错东西的口子
# ---------------------------------------------------------------------------


def _is_file_field(schema: dict) -> bool:
    """FastAPI 把 UploadFile 铺成 {type: string, contentMediaType: application/octet-stream}。"""
    return _deref(schema).get("contentMediaType") == "application/octet-stream"


def _multipart_operations() -> list[tuple[str, str, str, tuple[str, ...]]]:
    """[(method, 已解析 URL, 文件字段名, 文本字段名)] —— OpenAPI 声明为 multipart 的写端点。

    判据来自"文档里真的声明了 multipart"，不是猜文件名：哪天某个上传口改成手动 `Request.form()`
    而不再声明，这条清单会缩水，由 `test_multipart_list_is_populated` 的下限把它喊回来。
    """
    rows: set[tuple[str, str, str, tuple[str, ...]]] = set()
    for raw_path, operations in app.openapi()["paths"].items():
        if any(fragment in raw_path for fragment in _SKIP_FRAGMENTS):
            continue
        for method, operation in operations.items():
            if method not in WRITE_METHODS:
                continue
            media = operation.get("requestBody", {}).get("content", {})
            schema = _deref(media.get("multipart/form-data", {}).get("schema", {}))
            props = schema.get("properties") or {}
            file_fields = [key for key, val in props.items() if _is_file_field(val)]
            if not file_fields:
                continue
            text_fields = tuple(sorted(key for key in props if key not in file_fields))
            rows.add((method.upper(), _resolve(raw_path), file_fields[0], text_fields))
    return sorted(rows)


_MULTIPART_CASES = _multipart_operations()
# 一帧合法 PNG 的头 + 明显残缺的后续：扩展名与 MIME 都合规，只有内容检查（Pillow verify）挡得住。
# 这一条是整轮里最可能把自己弄崩的输入——`ALLOWED_EXTENSIONS` 先放行，随后解析器拿到截断流。
_CORRUPT_PNG = b"\x89PNG\r\n\x1a\n" + b"truncated-by-probe"
_MULTIPART_STATUS_LOG: list[tuple[str, str, int]] = []


class TestMultipartSurfaceNever500:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method,url,file_field,text_fields",
        _MULTIPART_CASES,
        ids=[f"{m.lower()} {u}" for m, u, _f, _t in _MULTIPART_CASES],
    )
    async def test_json_body_on_a_multipart_endpoint_is_not_a_server_error(
        self,
        client: AsyncClient,
        admin_headers: dict,
        method: str,
        url: str,
        file_field: str,
        text_fields: tuple[str, ...],
    ):
        """按 JSON 打一个声明为 multipart 的口子：形态不匹配是客户端的错，必须是 4xx。"""
        response = await client.request(method, url, headers=admin_headers, json={})
        _MULTIPART_STATUS_LOG.append((method, url, response.status_code))
        assert response.status_code < 500, (
            f"{method} {url} JSON body 返回 {response.status_code}：{response.text[:300]}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method,url,file_field,text_fields",
        _MULTIPART_CASES,
        ids=[f"{m.lower()} {u} no-file" for m, u, _f, _t in _MULTIPART_CASES],
    )
    async def test_missing_file_is_not_a_server_error(
        self,
        client: AsyncClient,
        admin_headers: dict,
        method: str,
        url: str,
        file_field: str,
        text_fields: tuple[str, ...],
    ):
        """真 multipart 表单、但漏掉必填文件字段：文本字段照常送，看 handler 有没有先读 file。"""
        files = {"_probe_stray": ("stray.txt", b"", "text/plain")}
        data = {name: "probe" for name in text_fields}
        response = await client.request(method, url, headers=admin_headers, files=files, data=data)
        _MULTIPART_STATUS_LOG.append((method, url, response.status_code))
        assert response.status_code < 500, (
            f"{method} {url} 缺 {file_field} 返回 {response.status_code}：{response.text[:300]}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method,url,file_field,text_fields",
        _MULTIPART_CASES,
        ids=[f"{m.lower()} {u} wrong-type" for m, u, _f, _t in _MULTIPART_CASES],
    )
    async def test_wrong_type_file_is_not_a_server_error(
        self,
        client: AsyncClient,
        admin_headers: dict,
        method: str,
        url: str,
        file_field: str,
        text_fields: tuple[str, ...],
    ):
        """递一个纯文本 .txt：白名单/解析器必须把它判成"不收"，而不是抛异常。"""
        files = {
            file_field: (
                "probe.txt",
                b"probe: not a media file, not a structured export",
                "text/plain",
            )
        }
        data = {name: "probe" for name in text_fields}
        response = await client.request(method, url, headers=admin_headers, files=files, data=data)
        _MULTIPART_STATUS_LOG.append((method, url, response.status_code))
        assert response.status_code < 500, (
            f"{method} {url} .txt 文件返回 {response.status_code}：{response.text[:300]}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method,url,file_field,text_fields",
        _MULTIPART_CASES,
        ids=[f"{m.lower()} {u} corrupt-image" for m, u, _f, _t in _MULTIPART_CASES],
    )
    async def test_corrupt_image_file_is_not_a_server_error(
        self,
        client: AsyncClient,
        admin_headers: dict,
        method: str,
        url: str,
        file_field: str,
        text_fields: tuple[str, ...],
    ):
        """名字与 MIME 都合规、内容只有 PNG 魔数的残缺图片：扩展名放行后必须有内容级校验兜住。"""
        files = {file_field: ("probe.png", _CORRUPT_PNG, "image/png")}
        data = {name: "probe" for name in text_fields}
        response = await client.request(method, url, headers=admin_headers, files=files, data=data)
        _MULTIPART_STATUS_LOG.append((method, url, response.status_code))
        assert response.status_code < 500, (
            f"{method} {url} 残缺 PNG 返回 {response.status_code}：{response.text[:300]}"
        )

    def test_multipart_list_is_populated(self):
        """清单不能塌成空集：本仓真实存在的上传/导入口远超下限。"""
        assert len(_MULTIPART_CASES) >= 6, (
            f"multipart 写端点只有 {len(_MULTIPART_CASES)} 条，疑似声明形态变化"
        )

    def test_multipart_rounds_reach_handlers(self):
        """四轮的牙齿：至少要有一部分穿过形态校验进到业务代码，否则 <500 绿得没有意义。

        下限取 8：每个端点四轮里只要有一轮真正被 handler 处理（解析图片 / 读 zip / 逐行导入），
        这条守卫就在检业务崩溃点；全被 422 挡住意味着文件压根没送出去。
        """
        non_validation = [row for row in _MULTIPART_STATUS_LOG if row[2] != 422]
        assert len(_MULTIPART_STATUS_LOG) >= len(_MULTIPART_CASES) * 4, (
            f"只记录了 {len(_MULTIPART_STATUS_LOG)} 次响应，四轮没有跑满"
        )
        assert len(non_validation) >= 8, (
            f"multipart 四轮里只有 {len(non_validation)}/{len(_MULTIPART_STATUS_LOG)} 条"
            "穿过校验进到业务代码，这条守卫已失去检出能力"
        )
