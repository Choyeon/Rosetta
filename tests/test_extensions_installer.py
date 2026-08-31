"""
插件与主题 ZIP 上传 / 远程安装 测试（Task A）

覆盖：
- T1: 插件 zip 上传安装（成功路径）—— 不应返回 501 NOT_IMPLEMENTED
- T2: 主题 zip 上传安装（成功路径）—— 不应返回 501 NOT_IMPLEMENTED
- T3: 非法 zip（缺少 manifest）不应返回 501 NOT_IMPLEMENTED
- T4: 重复安装同版本插件不应返回 501 NOT_IMPLEMENTED
- T5: 超大包上传不应返回 501 NOT_IMPLEMENTED
- T6: 插件远程安装（Mock httpx + checksum 校验）—— 不应返回 501
- T7: 主题远程安装 checksum 不匹配 —— 不应返回 501
- T8: 匿名请求时 upload/remote 不返回 501（应返回 401/503）
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient

# ============================================================
# Fixtures: 构造 zip bytes
# ============================================================


def _make_fake_plugin_zip(slug: str = "hello-plugin", version: str = "0.1.0") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        manifest = {
            "id": f"io.github.rosetta.{slug}",
            "slug": slug,
            "name": f"Hello {slug}",
            "version": version,
            "description": f"演示插件 {slug}",
            "author": "Rosetta",
            "license": "MIT",
            "entry": "plugin.py",
            "settings_schema": {"type": "object", "properties": {}},
        }
        z.writestr(f"{slug}/rosetta-plugin.json", json.dumps(manifest, ensure_ascii=False))
        z.writestr(f"{slug}/__init__.py", "from .plugin import register\n")
        z.writestr(
            f"{slug}/plugin.py",
            "async def register(app=None, bus=None):\n"
            "    return None\n",
        )
    return buf.getvalue()


def _make_fake_theme_zip(slug: str = "hello-theme", version: str = "0.1.0") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        manifest = {
            "id": f"io.github.rosetta.{slug}",
            "slug": slug,
            "name": f"Hello Theme {slug}",
            "version": version,
            "description": f"演示主题 {slug}",
            "author": "Rosetta",
            "license": "MIT",
            "stylesheet": "style.css",
            "mods_schema": {"type": "object", "properties": {}},
            "tags": ["demo"],
        }
        z.writestr(f"{slug}/rosetta-theme.json", json.dumps(manifest, ensure_ascii=False))
        z.writestr(f"{slug}/style.css", f"/* theme {slug} {version} */\n")
        z.writestr(
            f"{slug}/screenshot.svg",
            f'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="200">'
            f'<text x="20" y="40">{slug}</text></svg>',
        )
    return buf.getvalue()


def _make_invalid_package_zip() -> bytes:
    """无 manifest 的 zip"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("garbage-package/random.txt", "no manifest here\n")
    return buf.getvalue()


# ============================================================
# T1: 插件上传 —— 核心断言：不允许返回 501 NOT_IMPLEMENTED
# ============================================================


@pytest.mark.asyncio
async def test_t1_install_plugin_from_uploaded_zip(
    client: AsyncClient, admin_headers: dict
):
    """T1: 上传插件 zip → 绝不返回 501「暂不支持 upload/remote 安装方式」。

    TDD 红阶段：当前 api/plugins.py 返回 501 NOT_IMPLEMENTED，所以 status_code == 501，
    断言 assert status_code != 501 会失败 → 这就是预期的「红」。
    完成实现后，status_code 应该是 200（成功）或 4xx（业务错误），断言通过。
    """
    data = _make_fake_plugin_zip("hello-plugin")
    files = {"file": ("hello-plugin.zip", data, "application/zip")}
    resp = await client.post(
        "/api/admin/plugins",
        params={"source": "upload"},
        files=files,
        headers=admin_headers,
    )
    assert resp.status_code != 501, (
        f"TDD-Red: 当前实现返回 501 NOT_IMPLEMENTED，"
        f"请实现 upload 分支后重新运行。resp={resp.text}"
    )
    assert "暂不支持" not in (resp.text or "")
    # 如果走到业务层：成功返回 200 + success，错误返回 4xx
    if resp.status_code == 200:
        body = resp.json()
        assert body.get("success") is True
        assert body.get("data", {}).get("slug") == "hello-plugin"


# ============================================================
# T2: 主题上传 —— 同样不允许 501
# ============================================================


@pytest.mark.asyncio
async def test_t2_install_theme_from_uploaded_zip(
    client: AsyncClient, admin_headers: dict
):
    """T2: 上传主题 zip → 绝不返回 501 NOT_IMPLEMENTED"""
    data = _make_fake_theme_zip("hello-theme")
    files = {"file": ("hello-theme.zip", data, "application/zip")}
    resp = await client.post(
        "/api/admin/themes",
        params={"source": "upload"},
        files=files,
        headers=admin_headers,
    )
    assert resp.status_code != 501, (
        f"TDD-Red: 主题 upload 返回 501 NOT_IMPLEMENTED，"
        f"请实现 themes_ext.py install upload 分支。resp={resp.text}"
    )
    assert "暂不支持" not in (resp.text or "")
    if resp.status_code == 200:
        body = resp.json()
        assert body.get("success") is True
        assert body.get("data", {}).get("slug") == "hello-theme"


# ============================================================
# T3: 非法 zip（无 manifest）→ 不返回 501，业务层返回 400
# ============================================================


@pytest.mark.asyncio
async def test_t3_invalid_zip_no_manifest(
    client: AsyncClient, admin_headers: dict
):
    """T3: 缺少 rosetta-plugin.json 的 zip → 400 MANIFEST_INVALID，不是 501"""
    data = _make_invalid_package_zip()
    files = {"file": ("garbage.zip", data, "application/zip")}
    resp = await client.post(
        "/api/admin/plugins",
        params={"source": "upload"},
        files=files,
        headers=admin_headers,
    )
    assert resp.status_code != 501
    assert "暂不支持" not in (resp.text or "")
    # 如果走到业务逻辑（非 401/503），必须返回 400 MANIFEST_INVALID / PACKAGE_MANIFEST_NOT_FOUND
    if resp.status_code == 400:
        body = resp.json()
        ec = str(body.get("error_code", ""))
        assert "MANIFEST" in ec or "INVALID" in ec or "MISSING" in ec


# ============================================================
# T4: 同插件重复安装 → 不返回 501；要么覆盖成功要么 409 CONFLICT
# ============================================================


@pytest.mark.asyncio
async def test_t4_duplicate_plugin_same_version_conflict(
    client: AsyncClient, admin_headers: dict
):
    """T4: 同 slug 上传两次 → 不返回 501；要么 200 覆盖，要么 409。"""
    data = _make_fake_plugin_zip("dup-plugin", "0.1.0")
    files = {"file": ("dup-1.zip", data, "application/zip")}
    r1 = await client.post(
        "/api/admin/plugins",
        params={"source": "upload"},
        files=files,
        headers=admin_headers,
    )
    assert r1.status_code != 501, "首次上传也返回 501 NOT_IMPLEMENTED"
    # 如果 401/503 跳过业务校验，否则第二次
    if r1.status_code == 401 or r1.status_code == 503:
        pytest.skip(f"首次安装 auth/OOBE 拒绝 status={r1.status_code}，跳过后续业务断言")
    if r1.status_code != 200:
        # 首次没成功也有可能是磁盘写入失败等；跳过冲突测试
        pytest.skip(f"首次安装未成功 status={r1.status_code}: {r1.text[:100]}，跳过冲突校验")

    files2 = {"file": ("dup-2.zip", data, "application/zip")}
    r2 = await client.post(
        "/api/admin/plugins",
        params={"source": "upload"},
        files=files2,
        headers=admin_headers,
    )
    assert r2.status_code != 501
    # 允许 200（覆盖）或 409（冲突），不是 501 就可以
    if r2.status_code == 409:
        body = r2.json()
        ec = str(body.get("error_code", ""))
        assert "EXISTS" in ec or "CONFLICT" in ec or "VERSION" in ec


# ============================================================
# T5: 超大小包 → 不返回 501；应该是 400 PACKAGE_TOO_LARGE
# ============================================================


@pytest.mark.asyncio
async def test_t5_package_too_large(client: AsyncClient, admin_headers: dict, monkeypatch):
    """T5: monkeypatch config，用 tiny limit 触发 size 超限。"""
    from backend.core.config import settings as _s

    # 先写入上限字节数：我们把 max_upload_size 临时调成 512 bytes
    # （api/plugins.py 实现里应该读 config.UPLOAD_MAX_PACKAGE_SIZE_MB 或者 max_upload_size）
    original = getattr(_s, "max_upload_size", None)
    # 设置一个非常小的值（512 字节）让普通 zip 就超了
    monkeypatch.setattr(_s, "max_upload_size", 512)
    try:
        # 构造一个肯定超 512B 的 zip（光是 zip 最小结构就 22B，加上文件会更大）
        data = _make_fake_plugin_zip("big-plugin")
        assert len(data) > 512, "测试数据必须大于 512B 才能触发超限"
        files = {"file": ("big.zip", data, "application/zip")}
        resp = await client.post(
            "/api/admin/plugins",
            params={"source": "upload"},
            files=files,
            headers=admin_headers,
        )
        assert resp.status_code != 501
        assert "暂不支持" not in (resp.text or "")
        if resp.status_code == 400:
            body = resp.json()
            ec = str(body.get("error_code", ""))
            assert "LARGE" in ec or "SIZE" in ec or "TOO_BIG" in ec
    finally:
        if original is not None:
            monkeypatch.setattr(_s, "max_upload_size", original)


# ============================================================
# Mock httpx.AsyncClient helper
# ============================================================


class _FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self._content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx as _httpx_mod

            raise _httpx_mod.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=None,
                response=self,
            )

    @property
    def content(self):
        return self._content


class _FakeHttpxClient:
    """Mock: 对预设 URL 返回预设 bytes"""

    def __init__(self, resp_by_url: dict[str, bytes]):
        self._resp = resp_by_url

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, *a, **k):
        if url not in self._resp:
            return _FakeResponse(b"not found", 404)
        return _FakeResponse(self._resp[url])


# ============================================================
# T6: 插件远程安装 + checksum OK → 不返回 501
# ============================================================


@pytest.mark.asyncio
async def test_t6_plugin_remote_install_checksum_ok(
    client: AsyncClient, admin_headers: dict, monkeypatch
):
    """T6: 插件远程安装 url + checksum → 不返回 501"""
    data = _make_fake_plugin_zip("remote-plugin", "1.0.0")
    digest = hashlib.sha256(data).hexdigest()
    url = "https://market.rosetta.dev/plugins/remote-plugin-1.0.0.zip"

    import httpx as _httpx_mod

    _orig = _httpx_mod.AsyncClient

    class _MockClient(_FakeHttpxClient):
        def __init__(self, *a, **k):
            super().__init__({url: data})

    monkeypatch.setattr(_httpx_mod, "AsyncClient", _MockClient)

    payload = {
        "source": "remote",
        "slug": "remote-plugin",
        "remote": {
            "url": url,
            "checksum_sha256": digest,
            "allow_pre_release": False,
        },
    }
    resp = await client.post(
        "/api/admin/plugins",
        params={"source": "remote"},
        json=payload,
        headers=admin_headers,
    )
    assert resp.status_code != 501, (
        f"TDD-Red: 插件 remote 安装返回 501 NOT_IMPLEMENTED，"
        f"请实现 plugins.py install remote 分支。resp={resp.text}"
    )
    assert "暂不支持" not in (resp.text or "")


# ============================================================
# T7: 主题远程安装 checksum 不匹配 → 不返回 501；应该是 400 CHECKSUM
# ============================================================


@pytest.mark.asyncio
async def test_t7_theme_remote_install_checksum_mismatch(
    client: AsyncClient, admin_headers: dict, monkeypatch
):
    """T7: 主题远程安装 checksum 错误 → 400 PACKAGE_CHECKSUM_MISMATCH"""
    data = _make_fake_theme_zip("remote-theme", "1.0.0")
    url = "https://market.rosetta.dev/themes/remote-theme-1.0.0.zip"
    wrong_checksum = "0" * 64

    import httpx as _httpx_mod

    class _MockClient(_FakeHttpxClient):
        def __init__(self, *a, **k):
            super().__init__({url: data})

    monkeypatch.setattr(_httpx_mod, "AsyncClient", _MockClient)

    payload = {
        "source": "remote",
        "slug": "remote-theme",
        "remote": {
            "url": url,
            "checksum_sha256": wrong_checksum,
        },
    }
    resp = await client.post(
        "/api/admin/themes",
        params={"source": "remote"},
        json=payload,
        headers=admin_headers,
    )
    assert resp.status_code != 501
    assert "暂不支持" not in (resp.text or "")
    if resp.status_code == 400:
        body = resp.json()
        ec = str(body.get("error_code", ""))
        assert "CHECKSUM" in ec or "MISMATCH" in ec


# ============================================================
# T8: 匿名请求 → 返回 401/503，不返回 501 NOT_IMPLEMENTED
# ============================================================


@pytest.mark.asyncio
async def test_t8_no_auth_should_not_return_not_implemented(client: AsyncClient):
    """T8: 无鉴权时应该返回 401/503，绝不暴露 501 NOT_IMPLEMENTED"""
    # 插件上传
    data = _make_fake_plugin_zip("noauth-plugin")
    files = {"file": ("p.zip", data, "application/zip")}
    resp = await client.post(
        "/api/admin/plugins",
        params={"source": "upload"},
        files=files,
    )
    assert resp.status_code != 501
    assert "暂不支持" not in (resp.text or "")
    # 主题上传
    data2 = _make_fake_theme_zip("noauth-theme")
    files2 = {"file": ("t.zip", data2, "application/zip")}
    resp2 = await client.post(
        "/api/admin/themes",
        params={"source": "upload"},
        files=files2,
    )
    assert resp2.status_code != 501
    assert "暂不支持" not in (resp2.text or "")
    # 插件远程
    resp3 = await client.post(
        "/api/admin/plugins",
        params={"source": "remote"},
        json={"source": "remote", "slug": "x", "remote": {"url": "https://x/y.zip"}},
    )
    assert resp3.status_code != 501
    # 主题远程
    resp4 = await client.post(
        "/api/admin/themes",
        params={"source": "remote"},
        json={"source": "remote", "slug": "x", "remote": {"url": "https://x/y.zip"}},
    )
    assert resp4.status_code != 501
