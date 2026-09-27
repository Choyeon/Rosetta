"""导入导出 / 备份接口契约回归测试。

覆盖动机：
1. ZIP 的序列化 + 压缩现已搬进 ``asyncio.to_thread``，需要证明产物结构没变；
2. ``import_posts`` 历史上对用户上传的 ZIP 直接取 ``row["slug"]``，
   一份缺 slug 的 categories.json 会把请求打成 500，现在必须是语义化 400；
3. ``backup/full`` 会导出全站用户数据，必须钉死"不含 password"这条安全底线。
"""

import io
import json
import zipfile

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

ADMIN = "/api/admin"


def _zip_bytes(files: dict[str, object]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, payload in files.items():
            zf.writestr(name, payload if isinstance(payload, str) else json.dumps(payload))
    return buffer.getvalue()


def _open_zip(content: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(content))


async def _upload(
    client, staff_headers, content: bytes, url: str = f"{ADMIN}/import/posts", **params
):
    return await client.post(
        url,
        files={"file": ("rosetta_export.zip", content, "application/zip")},
        params=params,
        headers=staff_headers,
    )


# ==================== 导出 ====================


@pytest.mark.asyncio
async def test_export_posts_zip_roundtrip(client, staff_headers, test_post, test_category):
    resp = await client.get(
        f"{ADMIN}/export/posts", params={"include_drafts": True}, headers=staff_headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("application/zip")

    with _open_zip(resp.content) as zf:
        names = set(zf.namelist())
        assert {"posts.json", "categories.json", "tags.json", "export_info.json"} <= names
        posts = json.loads(zf.read("posts.json"))
        info = json.loads(zf.read("export_info.json"))

    assert [p["slug"] for p in posts] == [test_post.slug]
    assert info["posts_count"] == 1
    assert info["include_drafts"] is True


@pytest.mark.asyncio
async def test_export_posts_rejects_unimplemented_format(client, staff_headers, test_post):
    """format 下拉不能静默降级：未实现格式必须 400。"""
    resp = await client.get(
        f"{ADMIN}/export/posts", params={"format": "wordpress"}, headers=staff_headers
    )
    assert resp.status_code == 400
    assert "wordpress" in resp.json()["message"]


@pytest.mark.asyncio
async def test_export_markdown_contains_frontmatter(client, staff_headers, test_post):
    resp = await client.get(f"{ADMIN}/export/markdown", headers=staff_headers)
    assert resp.status_code == 200, resp.text

    with _open_zip(resp.content) as zf:
        names = set(zf.namelist())
        assert "README.md" in names
        assert f"{test_post.slug}.md" in names
        markdown = zf.read(f"{test_post.slug}.md").decode("utf-8")

    assert markdown.startswith("---\n")
    assert f"slug: {test_post.slug}" in markdown


# ==================== 导入 ====================


@pytest.mark.asyncio
async def test_import_posts_creates_category_tag_and_post(client, staff_headers, db_session):
    from backend.models.blog import Post

    payload = _zip_bytes(
        {
            "posts.json": [
                {
                    "id": 9001,
                    "title": {"zh": "导入的文章"},
                    "slug": "imported-post",
                    "content": {"zh": "# 正文"},
                    "category": {"id": 8001, "slug": "imported-cat"},
                    "tags": [{"id": 7001, "slug": "imported-tag"}],
                    "status": "published",
                }
            ],
            "categories.json": [{"id": 8001, "name": {"zh": "导入分类"}, "slug": "imported-cat"}],
            "tags.json": [{"id": 7001, "name": {"zh": "导入标签"}, "slug": "imported-tag"}],
        }
    )

    resp = await _upload(client, staff_headers, payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["error_count"] == 0, body["errors"]
    assert body["created_count"] >= 1

    created = (
        (
            await db_session.execute(
                select(Post)
                .options(selectinload(Post.tags), selectinload(Post.category))
                .where(Post.slug == "imported-post")
            )
        )
        .scalars()
        .all()
    )
    assert len(created) == 1
    assert created[0].category.slug == "imported-cat"
    assert [t.slug for t in created[0].tags] == ["imported-tag"]


@pytest.mark.asyncio
async def test_import_posts_overwrite_mode_updates_in_place(
    client, staff_headers, db_session, test_post
):
    """skip_existing=false 走覆盖分支：历史 bug 是 tags 未 eager load 直接炸。"""
    from backend.models.blog import Post

    payload = _zip_bytes(
        {
            "posts.json": [
                {
                    "id": 1,
                    "title": {"zh": "已被覆盖的标题"},
                    "slug": test_post.slug,
                    "content": {"zh": "新正文"},
                    "status": "published",
                    "tags": [],
                }
            ],
            "categories.json": [],
            "tags.json": [],
        }
    )

    resp = await _upload(client, staff_headers, payload, skip_existing=False)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["error_count"] == 0, body["errors"]
    assert body["skipped_count"] == 0

    refreshed = (
        (await db_session.execute(select(Post).where(Post.slug == test_post.slug))).scalars().one()
    )
    assert refreshed.title["zh"] == "已被覆盖的标题"


@pytest.mark.asyncio
async def test_import_posts_skip_existing_skips_duplicate(client, staff_headers, test_post):
    """skip_existing=true（默认）必须真跳过同 slug，而不是又建一条。"""
    payload = _zip_bytes(
        {
            "posts.json": [{"slug": test_post.slug, "title": {"zh": "重复"}}],
            "categories.json": [],
            "tags.json": [],
        }
    )
    resp = await _upload(client, staff_headers, payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["skipped_count"] == 1
    assert body["created_count"] == 0


@pytest.mark.asyncio
async def test_import_posts_missing_slug_is_400_not_500(client, staff_headers):
    """回归：categories.json 条目缺 slug 时，旧实现直接 row["slug"] 抛 KeyError → 500。"""
    payload = _zip_bytes(
        {
            "posts.json": [],
            "categories.json": [{"id": 1, "name": {"zh": "没有 slug"}}],
            "tags.json": [],
        }
    )

    resp = await _upload(client, staff_headers, payload)
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body["success"] is False
    assert "slug" in body["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "files, keyword",
    [
        ({"posts.json": {"not": "a list"}}, "数组"),
        ({"posts.json": ["string-row"]}, "不是对象"),
    ],
)
async def test_import_posts_structure_validation(client, staff_headers, files, keyword):
    resp = await _upload(client, staff_headers, _zip_bytes(files))
    assert resp.status_code == 400
    assert keyword in resp.json()["message"]


@pytest.mark.asyncio
async def test_import_posts_empty_zip_succeeds(client, staff_headers):
    """tags.json 合法但 posts 为空：解析通过，不应被结构校验误伤。"""
    payload = _zip_bytes(
        {
            "posts.json": [],
            "categories.json": [],
            "tags.json": [{"id": 1, "slug": "x", "name": {"zh": "x"}}],
        }
    )
    resp = await _upload(client, staff_headers, payload)
    assert resp.status_code == 200
    assert resp.json()["created_count"] == 0


@pytest.mark.asyncio
async def test_import_posts_rejects_non_dict_category(client, staff_headers):
    """posts[].category 给了非对象（如字符串）时，旧实现 .get() 直接 AttributeError。"""
    payload = _zip_bytes(
        {
            "posts.json": [{"slug": "bad-cat", "title": {"zh": "x"}, "category": "not-an-obj"}],
            "categories.json": [],
            "tags.json": [],
        }
    )
    resp = await _upload(client, staff_headers, payload)
    assert resp.status_code == 400
    assert "category" in resp.json()["message"]


@pytest.mark.asyncio
async def test_import_posts_rejects_non_zip_and_unknown_format(client, staff_headers):
    resp = await client.post(
        f"{ADMIN}/import/posts",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        headers=staff_headers,
    )
    assert resp.status_code == 400
    assert "ZIP" in resp.json()["message"]

    resp2 = await _upload(client, staff_headers, _zip_bytes({"posts.json": []}), format="halo")
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_import_markdown_creates_post(client, staff_headers, db_session):
    markdown = "---\ntitle: Markdown 文章\nslug: md-imported\ncategory: 默认\n---\n\n正文内容\n"
    resp = await client.post(
        f"{ADMIN}/import/markdown",
        files={"file": ("md-imported.md", markdown.encode("utf-8"), "text/markdown")},
        headers=staff_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["created_count"] == 1


# ==================== 备份 ====================


@pytest.mark.asyncio
async def test_backup_info_counts(client, staff_headers, test_post):
    resp = await client.get(f"{ADMIN}/backup/info", headers=staff_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["counts"]["posts"] == 1
    assert body["total"] >= 1
    assert body["queried_at"]


@pytest.mark.asyncio
async def test_backup_full_contains_every_model_and_hides_password(
    client, staff_headers, test_post
):
    resp = await client.get(f"{ADMIN}/backup/full", headers=staff_headers)
    assert resp.status_code == 200, resp.text

    with _open_zip(resp.content) as zf:
        names = set(zf.namelist())
        assert {
            "manifest.json",
            "posts.json",
            "categories.json",
            "tags.json",
            "comments.json",
            "users.json",
            "media.json",
            "site_config.json",
        } <= names
        manifest = json.loads(zf.read("manifest.json"))
        users = json.loads(zf.read("users.json"))

    assert manifest["counts"]["posts"] == 1
    assert manifest["version"]
    # 全站备份里绝不能出现口令散列 / 重置 token
    assert users
    for row in users:
        assert "password" not in row
        assert "password_hash" not in row
        assert "reset_token" not in row


@pytest.mark.asyncio
async def test_backup_endpoints_require_staff(client, auth_headers, test_post):
    for path in ("backup/info", "backup/full", "export/posts"):
        resp = await client.get(f"{ADMIN}/{path}", headers=auth_headers)
        assert resp.status_code in (401, 403), f"{path} -> {resp.status_code}"
