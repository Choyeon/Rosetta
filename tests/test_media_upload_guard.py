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
    _validate_non_image_magic,
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


# ── 非图片族（视频/音频/文档）魔术字节校验 ────────────────────────────────────
# 媒体库允许 mp4/webm/mov/mp3/wav/ogg/pdf/doc/docx/xls/xlsx。曾经这些扩展名
# **完全没有内容校验**：把 shell 脚本改名为 a.mp4 就能原样存进 /media 静态目录，
# 并被同源 URL 引用（内容类型的欺骗比 XSS 更隐蔽）。这里用文件头把它们钉住。

NON_IMAGE_VALID_CASES: list[tuple[str, bytes]] = [
    ("mp4", b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00"),
    ("mov", b"\x00\x00\x00\x14ftypqt  \x00\x00\x02\x00"),
    ("webm", b"\x1a\x45\xdf\xa3\x01\x00\x00\x00"),
    ("mp3", b"ID3\x03\x00\x00\x00\x00\x00\x00"),
    ("mp3", b"\xff\xfb\x90\x64\x00\x00"),  # 裸 MPEG 帧同步（无 ID3 头）
    ("wav", b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00"),
    ("ogg", b"OggS\x00\x02\x00\x00\x00\x00\x00\x00"),
    ("pdf", b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"),
    ("doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1\x00\x00"),
    ("xls", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1\x00\x00"),
    ("docx", b"PK\x03\x04\x14\x00\x06\x00\x08\x00"),
    ("xlsx", b"PK\x03\x04\x14\x00\x06\x00\x08\x00"),
]

# 伪装案例：每一条都曾经能被"仅看扩展名"的白名单放行
NON_IMAGE_SPOOFED_CASES: list[tuple[str, bytes]] = [
    ("mp4", b"#!/bin/sh\nrm -rf /\n"),
    ("webm", b"<?php system($_GET['c']); ?>"),
    ("mp3", b"<html><script>alert(1)</script></html>"),
    ("wav", b"MZ\x90\x00\x03\x00\x00\x00"),  # PE 可执行文件
    ("pdf", b"#!/usr/bin/env python3\nimport os\n"),
    ("doc", b"%PDF-1.4 fake is not doc"),  # 族内串号：PDF 头冒充 doc
    ("docx", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),  # OLE2 冒充 ZIP 容器
    ("xlsx", b"\x7fELF\x02\x01\x01\x00"),  # ELF 可执行文件
]


@pytest.mark.parametrize(
    ("ext", "payload"), NON_IMAGE_VALID_CASES, ids=[f"{e}-{i}" for i, (e, _) in enumerate(NON_IMAGE_VALID_CASES)]
)
def test_non_image_magic_accepts_real_containers(ext: str, payload: bytes):
    _validate_non_image_magic(payload, ext, f"clip.{ext}")  # 不抛异常即通过


@pytest.mark.parametrize(
    ("ext", "payload"),
    NON_IMAGE_SPOOFED_CASES,
    ids=[f"{e}-{i}" for i, (e, _) in enumerate(NON_IMAGE_SPOOFED_CASES)],
)
def test_non_image_magic_rejects_disguised_payload(ext: str, payload: bytes):
    with pytest.raises(HTTPException) as excinfo:
        _validate_non_image_magic(payload, ext, f"evil.{ext}")
    assert excinfo.value.status_code == 422
    assert excinfo.value.detail["error_code"] == "UPLOAD_MAGIC_MISMATCH"


def test_non_image_magic_ignores_unregistered_extension():
    """未登记的扩展名直接放行 —— 内容校验不取代白名单，只是它的第二道闸门。"""
    _validate_non_image_magic(b"whatever", "unknown", "x.unknown")


def test_every_library_extension_has_a_magic_rule():
    """白名单里的每个扩展名都必须有归宿：要么落在表内，要么显式豁免。

    这条守卫防止后人往 LIBRARY_TYPE_EXTENSIONS 里新增扩展名却忘了登记，
    那样会静默退化成"只看扩展名"的旧状态。
    """
    from backend.api.media import _MAGIC_NON_IMAGE

    for ftype, extensions in LIBRARY_TYPE_EXTENSIONS.items():
        if ftype == "image":
            continue
        for ext in extensions:
            assert ext in _MAGIC_NON_IMAGE, f".{ext} 缺少魔术字节规则，可被任意内容伪造"


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


# ── 公共素材上传的能力闸门 ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_public_upload_requires_upload_media_capability(
    client: AsyncClient, auth_headers: dict, staff_headers: dict
):
    """``POST /media/upload`` 写的是公共素材目录，subscriber 必须被拒。

    rbac 能力矩阵里 ``media:upload`` 从 contributor(20) 起授予，subscriber 只有
    ``users:edit_own_profile``（够改自己的头像/封面，不够往公共空间塞文件）。
    这条用例锁住的是「相对旧行为收紧」的那一步，防止后人把它改回任意登录用户可写。
    """
    files = {"file": ("x.png", io.BytesIO(PNG_HEADER), "image/png")}

    denied = await client.post("/api/media/upload", files=files, headers=auth_headers)
    assert denied.status_code == 403, denied.text
    assert "media:upload" in denied.text

    # staff 通过能力闸门；后续失败（入库/路径）与鉴权无关，因此只断言不是 401/403
    allowed = await client.post(
        "/api/media/upload", files={"file": ("y.png", io.BytesIO(PNG_HEADER), "image/png")},
        headers=staff_headers,
    )
    assert allowed.status_code not in (401, 403)


@pytest.mark.asyncio
async def test_upload_stream_shares_the_same_capability_gate(
    client: AsyncClient, auth_headers: dict, staff_headers: dict
):
    """/upload/stream 只是写入方式不同，鉴权口径必须与 /upload 完全一致。"""
    denied = await client.post(
        "/api/media/upload/stream",
        files={"file": ("s.png", io.BytesIO(PNG_HEADER), "image/png")},
        headers=auth_headers,
    )
    assert denied.status_code == 403

    allowed = await client.post(
        "/api/media/upload/stream",
        files={"file": ("s.png", io.BytesIO(PNG_HEADER), "image/png")},
        headers=staff_headers,
    )
    assert allowed.status_code not in (401, 403)


@pytest.mark.asyncio
async def test_avatar_and_cover_stay_open_to_plain_users(
    client: AsyncClient, auth_headers: dict
):
    """头像/封面属于 EDIT_OWN_PROFILE：普通注册用户要能换，不能被 UPLOAD_MEDIA 误伤。

    这里只断言「没被能力闸门挡在门外」（非 403）。请求Body 是真实 PNG，
    后端会继续走 PIL 重编码等后续流程，那条链路的结果不是本用例关心的边界。
    """
    for path in ("/api/media/avatar", "/api/media/cover"):
        r = await client.post(
            path,
            files={"file": ("a.png", io.BytesIO(PNG_HEADER), "image/png")},
            headers=auth_headers,
        )
        assert r.status_code != 403, f"{path} 不应要求 UPLOAD_MEDIA: {r.text}"
        assert r.status_code != 401


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


def _make_media_with_derivatives(tmp_path: Path, stem: str) -> tuple:
    """在 tmp_path 下铺一套 原图+thumbnail+medium 派生档，返回 (Media, [路径])。"""
    from backend.models.core import Media

    up = tmp_path / "uploads" / "image"
    up.mkdir(parents=True, exist_ok=True)
    paths = [up / f"{stem}{suffix}.png" for suffix in ("", "-thumbnail", "-medium")]
    for p in paths:
        p.write_bytes(b"\x89PNG\r\n\x1a\n")
    media = Media(
        file=f"/media/uploads/image/{stem}.png",
        filename=f"{stem}.png",
        file_type="image",
        file_size=8,
        sizes={
            "thumbnail": {
                "url": f"/media/uploads/image/{stem}-thumbnail.png",
                "width": 1,
                "height": 1,
            },
            "medium": {"url": f"/media/uploads/image/{stem}-medium.png", "width": 1, "height": 1},
            # 外链档必须被安全跳过而不是报错阻断记录删除
            "remote": {"url": "https://cdn.example.com/x.png", "width": 1, "height": 1},
        },
    )
    return media, paths


@pytest.mark.asyncio
async def test_single_delete_removes_derivative_files(
    client: AsyncClient, staff_headers: dict, db_session, monkeypatch, tmp_path: Path
):
    """单删必须连 sizes 里的派生档一起清。

    2026-09 curl 实证：DELETE /api/media/library/{id} 只删原图，
    -thumbnail/-medium/-large 变体永久残留成磁盘孤儿。"""
    from backend.api import media as media_api

    monkeypatch.setattr(media_api, "MEDIA_DIR", tmp_path)
    media, paths = _make_media_with_derivatives(tmp_path, "pic")
    db_session.add(media)
    await db_session.commit()
    await db_session.refresh(media)

    r = await client.delete(f"/api/media/library/{media.id}", headers=staff_headers)
    assert r.status_code == 200, r.text
    for p in paths:
        assert not p.exists(), f"派生档残留：{p}"


@pytest.mark.asyncio
async def test_batch_delete_removes_derivative_files(
    client: AsyncClient, staff_headers: dict, db_session, monkeypatch, tmp_path: Path
):
    """批删与单删同口径：原图 + 全部派生档都必须清掉。"""
    from backend.api import media as media_api

    monkeypatch.setattr(media_api, "MEDIA_DIR", tmp_path)
    m1, p1 = _make_media_with_derivatives(tmp_path, "a")
    m2, p2 = _make_media_with_derivatives(tmp_path, "b")
    db_session.add_all([m1, m2])
    await db_session.commit()
    await db_session.refresh(m1)
    await db_session.refresh(m2)

    r = await client.request(
        "DELETE",
        "/api/media/library/batch",
        headers=staff_headers,
        json={"ids": [m1.id, m2.id]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["deleted_count"] == 2, r.text
    for p in [*p1, *p2]:
        assert not p.exists(), f"派生档残留：{p}"


# ── 删除引用护栏（被内容引用的媒体不得静默删除） ──────────────────────────────


async def _make_referenced_media(db_session, tmp_path: Path, stem: str):
    """铺一条媒体记录 + 一张引用它原图 URL 的相册照片，返回 (media, 原图路径)。"""
    from backend.models.core import Media
    from backend.models.gallery import Album, Photo

    up = tmp_path / "uploads" / "image"
    up.mkdir(parents=True, exist_ok=True)
    original = up / f"{stem}.png"
    original.write_bytes(b"\x89PNG\r\n\x1a\n")
    media = Media(
        file=f"/media/uploads/image/{stem}.png",
        filename=f"{stem}.png",
        file_type="image",
        file_size=8,
    )
    db_session.add(media)
    await db_session.commit()
    await db_session.refresh(media)

    album = Album(title=f"album-{stem}")
    db_session.add(album)
    await db_session.commit()
    await db_session.refresh(album)
    db_session.add(Photo(album_id=album.id, url=media.file))
    await db_session.commit()
    return media, original


@pytest.mark.asyncio
async def test_single_delete_refuses_media_referenced_by_photo(
    client: AsyncClient, staff_headers: dict, db_session, monkeypatch, tmp_path: Path
):
    """被相册照片引用的媒体单删必须 409 拒绝，记录与文件都保留。

    原实现零引用检查：管理员从媒体库删掉在用图片，相册/文章封面页立刻 404 图，
    界面却回"已删除"，无从得知也不可从公开页面恢复。"""
    from sqlalchemy import select

    from backend.api import media as media_api

    monkeypatch.setattr(media_api, "MEDIA_DIR", tmp_path)
    media, original = await _make_referenced_media(db_session, tmp_path, "used")

    r = await client.delete(f"/api/media/library/{media.id}", headers=staff_headers)
    assert r.status_code == 409, f"被引用媒体必须拒绝删除：{r.status_code} {r.text}"
    # 统一错误包络（main.py::http_exception_handler 对含 error_code 的 dict detail 原样透传）
    body = r.json()
    assert body.get("error_code") == "MEDIA_IN_USE", body
    assert "相册照片" in body.get("message", ""), body

    assert original.exists(), "拒绝删除后物理文件必须保留"
    remaining = await db_session.execute(
        select(media_api.Media).where(media_api.Media.id == media.id)
    )
    assert remaining.scalar_one_or_none() is not None, "拒绝删除后 DB 记录必须保留"


@pytest.mark.asyncio
async def test_batch_delete_reports_referenced_media_as_refused(
    client: AsyncClient, staff_headers: dict, db_session, monkeypatch, tmp_path: Path
):
    """批删把被引用条目并入 refused 上报；只引用到派生档 URL 也算整条在用。"""
    from backend.api import media as media_api
    from backend.models.core import Media
    from backend.models.gallery import Album, Photo

    monkeypatch.setattr(media_api, "MEDIA_DIR", tmp_path)
    img = tmp_path / "uploads" / "image"
    img.mkdir(parents=True, exist_ok=True)
    original = img / "inuse.png"
    thumb = img / "inuse-thumbnail.png"
    original.write_bytes(b"\x89PNG\r\n\x1a\n")
    thumb.write_bytes(b"\x89PNG\r\n\x1a\n")

    used = Media(
        file="/media/uploads/image/inuse.png",
        filename="inuse.png",
        file_type="image",
        file_size=8,
        sizes={
            "thumbnail": {
                "url": "/media/uploads/image/inuse-thumbnail.png",
                "width": 1,
                "height": 1,
            }
        },
    )
    free, free_paths = _make_media_with_derivatives(tmp_path, "free")
    db_session.add_all([used, free])
    await db_session.commit()
    await db_session.refresh(used)
    await db_session.refresh(free)

    album = Album(title="audit-album")
    db_session.add(album)
    await db_session.commit()
    await db_session.refresh(album)
    # 照片只引用派生档：删记录会连带删掉该派生档，同样必须算"在用"
    db_session.add(Photo(album_id=album.id, url="/media/uploads/image/inuse-thumbnail.png"))
    await db_session.commit()

    r = await client.request(
        "DELETE",
        "/api/media/library/batch",
        headers=staff_headers,
        json={"ids": [used.id, free.id]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["deleted_count"] == 1, f"只应删掉未被引用那条：{body}"
    assert [x["id"] for x in body["refused"]] == [used.id], f"派生档被引用必须整条保留：{body}"
    assert "相册照片" in body["refused"][0]["reason"], body
    assert original.exists() and thumb.exists(), "被保留条目的文件不得被顺手删除"
    for p in free_paths:
        assert not p.exists(), f"未引用条目应删干净：{p}"


@pytest.mark.asyncio
async def test_delete_by_filename_refuses_referenced_url(
    client: AsyncClient, staff_headers: dict, db_session, monkeypatch, tmp_path: Path
):
    """按「分类+文件名」直删物理文件同样必须先查引用；未引用时照常删。

    该端点绕过 Media 记录直接删盘上文件，若不查引用，删掉正被相册照片/头像
    指向的文件后 DB 记录还在、页面图却 404——比按 ID 删更隐蔽。"""
    from backend.api import media as media_api
    from backend.models.gallery import Album, Photo

    monkeypatch.setattr(media_api, "MEDIA_DIR", tmp_path)
    (tmp_path / "avatars").mkdir(parents=True, exist_ok=True)
    used_file = tmp_path / "avatars" / "pic.png"
    used_file.write_bytes(b"\x89PNG\r\n\x1a\n")
    free_file = tmp_path / "avatars" / "spare.png"
    free_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    album = Album(title="filename-guard")
    db_session.add(album)
    await db_session.commit()
    await db_session.refresh(album)
    db_session.add(Photo(album_id=album.id, url="/media/avatars/pic.png"))
    await db_session.commit()

    r = await client.delete("/api/media/avatars/pic.png", headers=staff_headers)
    assert r.status_code == 409, f"被引用文件按名直删必须被拒：{r.status_code} {r.text}"
    assert r.json().get("error_code") == "MEDIA_IN_USE", r.text
    assert used_file.exists(), "拒绝后文件必须保留"

    r2 = await client.delete("/api/media/avatars/spare.png", headers=staff_headers)
    assert r2.status_code == 200, r2.text
    assert not free_file.exists(), "未引用文件应正常删除"


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
