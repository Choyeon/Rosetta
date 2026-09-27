"""媒体上传护栏（服务端独立成立，不依赖前端校验）。

覆盖三件事：
1. 落盘扩展名白名单 —— AGENTS §12.7「大小 + 扩展名双校验」红线；前端
   ``composables/useUploadProgress.ts`` 的同名清单只是体验层，两份清单必须逐项一致。
2. SVG 主动内容拦截 —— SVG 与页面同源渲染（``/media`` 静态挂载 +
   ``GET /api/media/{category}/{filename}``），内含 script / 事件处理器即站点自身 XSS。
3. ``DELETE /api/media/{category}/{filename}`` 的鉴权口径与 ID 版删除一致（staff）。
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile
from httpx import AsyncClient

from backend.api.media import (
    LIBRARY_ALLOWED_EXTENSIONS,
    LIBRARY_TYPE_EXTENSIONS,
    _assert_svg_content_safe,
    _file_type_for_ext,
    save_upload,
)

PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


def _upload_file(payload: bytes, filename: str) -> UploadFile:
    """构造真实 UploadFile。

    async_save_stream 必须收到 UploadFile 本体：其 ``read`` 是异步的，
    而 ``upload.file`` 是同步 BinaryIO，传进去会 ``await bytes`` 抛 TypeError。
    """
    return UploadFile(
        file=io.BytesIO(payload), filename=filename, headers={"content-type": "image/png"}
    )


SAFE_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8">'
    b'<rect width="8" height="8" fill="#333"/></svg>'
)
XSS_SVG_CASES = {
    "script 标签": b'<svg xmlns="http://www.w3.org/2000/svg"><script>fetch("/x")</script></svg>',
    "事件处理器": b'<svg xmlns="http://www.w3.org/2000/svg"><rect onload="alert(1)"/></svg>',
    "javascript 协议": b'<svg xmlns="http://www.w3.org/2000/svg">'
    b'<a href="javascript:alert(1)">x</a></svg>',
}

# 同源可渲染 / 可被解释执行的扩展名：全部必须被白名单挡下
REJECTED_EXTENSIONS = [
    "html",
    "htm",
    "shtml",
    "xhtml",
    "php",
    "phtml",
    "js",
    "mjs",
    "sh",
    "py",
    "exe",
    "dll",
    "jar",
    "svgz",
]


def _frontend_allowed_extensions() -> set[str]:
    """解析前端白名单常量源码（跨栈契约，防止两边各自漂移）。"""
    ts = Path(__file__).resolve().parents[1] / "frontend" / "composables" / "useUploadProgress.ts"
    match = re.search(
        r"ALLOWED_UPLOAD_EXTENSIONS[^=]*=\s*\[(.*?)]", ts.read_text(encoding="utf-8"), re.S
    )
    assert match, "未找到前端白名单常量，契约断言将失去意义"
    return set(re.findall(r"'([^']+)'", match.group(1)))


def test_server_whitelist_matches_frontend_contract():
    frontend = _frontend_allowed_extensions()
    assert frontend, "前端白名单解析为空，测试本身失效"
    assert set(LIBRARY_ALLOWED_EXTENSIONS) == frontend


def test_every_whitelisted_extension_classifies():
    for ftype, extensions in LIBRARY_TYPE_EXTENSIONS.items():
        for ext in extensions:
            assert _file_type_for_ext(ext) == ftype
    # 白名单内不允许出现会被浏览器当作文档执行的扩展名
    assert not set(REJECTED_EXTENSIONS) & LIBRARY_ALLOWED_EXTENSIONS


@pytest.mark.parametrize("ext", REJECTED_EXTENSIONS)
def test_unknown_extension_rejected_by_whitelist(ext: str):
    assert ext not in LIBRARY_ALLOWED_EXTENSIONS


# ── SVG 主动内容 ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("payload", list(XSS_SVG_CASES.values()), ids=list(XSS_SVG_CASES))
def test_assert_svg_content_safe_rejects_active_content(payload: bytes):
    with pytest.raises(HTTPException) as excinfo:
        _assert_svg_content_safe(payload)
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail["error_code"] == "UPLOAD_SVG_UNSAFE"


def test_assert_svg_content_safe_allows_plain_vector():
    _assert_svg_content_safe(SAFE_SVG)  # 不抛异常即通过


@pytest.mark.asyncio
async def test_save_upload_rejects_script_svg_and_writes_nothing(tmp_path: Path):
    upload = UploadFile(
        filename="banner.svg",
        file=io.BytesIO(XSS_SVG_CASES["script 标签"]),
        headers={"content-type": "image/svg+xml"},
    )
    with pytest.raises(HTTPException) as excinfo:
        await save_upload(upload, media_dir=tmp_path)
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail["error_code"] == "UPLOAD_SVG_UNSAFE"
    assert list(tmp_path.iterdir()) == [], "拒绝前不得留下半个文件"


@pytest.mark.asyncio
async def test_save_upload_accepts_plain_svg(tmp_path: Path):
    upload = UploadFile(
        filename="logo.svg",
        file=io.BytesIO(SAFE_SVG),
        headers={"content-type": "image/svg+xml"},
    )
    final_path, content = await save_upload(upload, media_dir=tmp_path)
    assert final_path.read_bytes() == content == SAFE_SVG


# ── 按文件名删除的鉴权口径 ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_by_filename_requires_staff(
    client: AsyncClient, auth_headers: dict, staff_headers: dict
):
    """普通登录用户不得按文件名删他人文件；staff 通过鉴权、只因地径不存在 404。

    staff 一侧断言 404 而非 403，用来区分「鉴权失败」与「CSRF/中间件误拦」。
    """
    denied = await client.delete("/api/media/uploads/gone.png", headers=auth_headers)
    assert denied.status_code == 403

    allowed = await client.delete(
        "/api/media/uploads/definitely-missing.png", headers=staff_headers
    )
    assert allowed.status_code == 404


@pytest.mark.asyncio
async def test_batch_delete_refuses_illegal_path_and_reports_it(
    client: AsyncClient,
    staff_headers: dict,
    db_session,
):
    """批量删除遇到非法路径必须**保留该行并上报**，不能吞掉 HTTPException 后照样删记录。

    原实现在批量路径上 `except (FileNotFoundError, HTTPException): pass`，越权文件（Media.file
    被写成 `../../etc/passwd` 之类）解析失败后仍然删掉了 DB 行，结果是磁盘上留下永久孤儿文件、
    界面回"已删除"，管理员无从得知。
    """
    from sqlalchemy import select

    from backend.models.core import Media

    bad = Media(
        file="/media/../../outside-evil.png",
        filename="outside-evil.png",
        file_type="image",
        file_size=1,
    )
    good = Media(
        file="/media/uploads/image/already-gone.png",
        filename="already-gone.png",
        file_type="image",
        file_size=1,
    )
    db_session.add_all([bad, good])
    await db_session.commit()
    await db_session.refresh(bad)
    await db_session.refresh(good)

    r = await client.request(
        "DELETE",
        "/api/media/library/batch",
        headers=staff_headers,
        json={"ids": [bad.id, good.id, 999999]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["deleted_count"] == 1, f"只应删掉合法那一条：{body}"
    assert [x["id"] for x in body["refused"]] == [bad.id], f"非法路径必须上报：{body}"
    assert body["missing_ids"] == [999999], f"不存在的 ID 必须说明：{body}"
    assert "保留" in body["message"] and "不存在" in body["message"], body["message"]

    # 非法路径的行必须仍在库里（可被管理员看到并处理），合法那行已消失
    remaining = await db_session.execute(select(Media.id).where(Media.id.in_([bad.id, good.id])))
    assert [bad.id] == list(remaining.scalars().all()), f"删除结果不符：{body}"


@pytest.mark.asyncio
async def test_batch_delete_requires_staff(client: AsyncClient, auth_headers: dict, db_session):
    """未鉴权/普通用户不得触发批量删除（防止越权清空媒体库）"""
    r = await client.request("DELETE", "/api/media/library/batch", json={"ids": [1]})
    assert r.status_code in (401, 403), f"匿名批量删除必须被拒：{r.status_code} {r.text}"
    r2 = await client.request(
        "DELETE", "/api/media/library/batch", headers=auth_headers, json={"ids": [1]}
    )
    assert r2.status_code in (401, 403), f"普通用户批量删除必须被拒：{r2.status_code} {r2.text}"


# ── 按文件名读取（GET /api/media/{category}/{filename}） ──────────────────────


@pytest.mark.asyncio
async def test_get_image_streams_every_chunk(client: AsyncClient, monkeypatch, tmp_path: Path):
    """分块直出必须还原完整字节。

    该端点原先把整个文件读进内存再一次性 yield（10MB 图 x 并发 = 内存峰值），
    改成按 CHUNK_SIZE 读盘生成器后最典型的回归是"只发出第一块"，所以刻意用
    跨越多个 CHUNK_SIZE 的载荷断言字节级一致。
    """
    from backend.api import media as media_api

    monkeypatch.setattr(media_api, "MEDIA_DIR", tmp_path)
    payload = PNG_HEADER + b"\x5a" * (media_api.CHUNK_SIZE * 3 + 7)
    uploads = tmp_path / "uploads"
    uploads.mkdir(parents=True)
    (uploads / "big.png").write_bytes(payload)

    r = await client.get("/api/media/uploads/big.png")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("image/png")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.content == payload, "分块响应丢失了尾部字节"


@pytest.mark.asyncio
async def test_get_image_serves_unknown_extension_as_download(
    client: AsyncClient, monkeypatch, tmp_path: Path
):
    """白名单外的扩展名即便落盘也只能按 octet-stream 出，不给浏览器解释执行的机会。"""
    from backend.api import media as media_api

    monkeypatch.setattr(media_api, "MEDIA_DIR", tmp_path)
    uploads = tmp_path / "uploads"
    uploads.mkdir(parents=True)
    (uploads / "payload.txt").write_bytes(b"<script>alert(1)</script>")

    r = await client.get("/api/media/uploads/payload.txt")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/octet-stream")
    assert r.headers["x-content-type-options"] == "nosniff"


@pytest.mark.asyncio
async def test_get_image_rejects_unknown_category_and_missing_file(
    client: AsyncClient, monkeypatch, tmp_path: Path
):
    """分类必须在白名单内；不存在的路径统一 404，不泄露目录结构。"""
    from backend.api import media as media_api

    monkeypatch.setattr(media_api, "MEDIA_DIR", tmp_path)
    (tmp_path / "secret.png").write_bytes(PNG_HEADER)

    r_bad_category = await client.get("/api/media/private/secret.png")
    assert r_bad_category.status_code == 404

    r_missing = await client.get("/api/media/uploads/no-such-file.png")
    assert r_missing.status_code == 404


@pytest.mark.parametrize(
    "raw",
    [
        "../secret.png",
        "..\\secret.png",
        "....//secret.png",
        "a/../../secret.png",
        "/absolute/secret.png",
        "..%2fsecret.png",
    ],
)
def test_resolve_category_filepath_contains_filename_in_category(monkeypatch, tmp_path: Path, raw):
    """任意恶意文件名净化后都必须落在 MEDIA_DIR/category 之内。

    净化（``Path(...).name``）是主防线，``is_relative_to`` 是兜底；因此断言"结果仍在目录内"
    而不是"抛异常"——后者在净化已生效时永远不会触发，写出来只是一条假守卫。
    """
    from backend.api import media as media_api

    monkeypatch.setattr(media_api, "MEDIA_DIR", tmp_path)
    (tmp_path / "uploads").mkdir()
    (tmp_path / "secret.png").write_bytes(PNG_HEADER)

    resolved = media_api._resolve_category_filepath("uploads", raw)
    uploads_dir = (tmp_path / "uploads").resolve()
    assert resolved.parent == uploads_dir, f"路径逃逸出 category 目录：{raw} -> {resolved}"


@pytest.mark.asyncio
async def test_get_image_rejects_traversal_url(client: AsyncClient, monkeypatch, tmp_path: Path):
    """HTTP 层：穿越形式的 URL 不得读到 category 之外的文件（拿不到 200 即达标）。"""
    from backend.api import media as media_api

    monkeypatch.setattr(media_api, "MEDIA_DIR", tmp_path)
    (tmp_path / "uploads").mkdir()
    (tmp_path / "secret.png").write_bytes(PNG_HEADER)

    r = await client.get("/api/media/uploads/%2e%2e%2fsecret.png")
    assert r.status_code == 404, f"穿越读取未被阻断：{r.status_code} {r.content[:80]!r}"


@pytest.mark.asyncio
async def test_async_save_stream_caps_size_during_write_and_cleans_up(tmp_path: Path):
    """流式落盘必须在写入过程中限幅。

    旧实现是"全部写完再比较大小"：超限字节已经全部落盘，认证用户即可用大请求体
    反复打满磁盘（Nginx 侧 client_max_body_size 放行 50m，拦不住 10MB 级的滥用）。
    """
    from fastapi import HTTPException as FastHTTPException

    from backend.api import media as media_api

    limit = 4096
    payload = b"x" * (limit * 5)
    target = tmp_path / "stream.png"

    with pytest.raises(FastHTTPException) as excinfo:
        await media_api.async_save_stream(
            target, _upload_file(payload, "stream.png"), max_bytes=limit
        )

    assert excinfo.value.status_code == 413
    assert not target.exists(), "超限后必须删掉半成品，不得留下磁盘孤儿"


@pytest.mark.asyncio
async def test_async_save_stream_writes_within_limit(tmp_path: Path):
    from backend.api import media as media_api

    target = tmp_path / "ok.png"
    payload = PNG_HEADER + b"y" * 128
    size = await media_api.async_save_stream(
        target, _upload_file(payload, "ok.png"), max_bytes=1024 * 1024
    )
    assert size == len(payload)
    assert target.read_bytes() == payload
