"""并行文章加密族退役后的守卫。

2026-10-31 删掉的是**第二套文章保护设计**，它与主线闸门长期并存但互不相通：

* 主线（保留）：`Post.password` 存 argon2/bcrypt 哈希，判据单源
  `services/post_access.py::post_content_unlocked`，解锁后由详情口直接返回明文
  `Post.content`；`Post.encryption_hint` 是它的锁屏提示（批次 #17 接通读写四段）。
* 并行（退役）：`Post.encryption_enabled` + `encrypted_content`（AES-GCM 密文）
  + salt/verifier/algorithm 四个盐值字段，配上 7 条端点
  （`POST /api/posts/{id}/decrypt`、`POST|PUT|DELETE /api/admin/posts/{id}/encrypt`、
  `POST /api/post_crypto/derive_keys`、`POST /api/post_crypto/verify_access`、
  `GET /api/post_crypto/encrypted/{post_id}/preview`）与 `backend/core/crypto.py`。

这条族为什么是僵尸而不是"未完成的功能"：详情响应模型从不带 `encrypted_content`，
所以**任何访客路径都拿不到密文**；前端零调用（`grep post_crypto frontend/` 为空）；
`verify_access` 还会铸一枚 `scope=post_access` 的 JWT，而全站没有任何端点认它。
线上实测（批次 #106 前置探针）`encryption_enabled=true` 的行数与 `encrypted_content`
非空行数都是 0，删掉解密口不会让任何一篇正文失去唯一副本。

生产库的 5 个列**刻意保留**（不做破坏性迁移）：`defer(Post.encrypted_content)` 的
四处读侧护栏、以及 ZIP 导出/导入对密文的原样往返，都是为"历史备份里可能有密文"留的。
退役的边界是**接口与写口**，不是表结构。

断言各挡一种回归：
* 端点回到 OpenAPI，或模块被"照旧文档补回来"；
* `PostCreate` / `PostUpdate` 重新收下四个盐值字段——写口收键而没有任何读口回吐，
  正是本次要消除的那种形状（AGENTS.md「写口收键、读口不回吐」）；
* OOBE 的 `enable_encrypted_posts` 假开关回潮（写了 `.env` 与 SiteConfig，没人读）；
* 活路径被一起删掉——把"删僵尸"做成"删功能"：`Post.password` 哈希、
  `post_content_unlocked` 判据、`encryption_hint` 四段往返、以及密文的备份往返都必须在。

口径依据 AGENTS.md §7.4 第 4 条：核对路由存在性读**生成后的** ``app.openapi()["paths"]``。
"""

from pathlib import Path

from backend.main import TAG_METADATA, app

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"

# 退役的 7 条口（OpenAPI 里的完整路径）
RETIRED_PATHS = (
    "/api/posts/{post_id}/decrypt",
    "/api/admin/posts/{post_id}/encrypt",
    "/api/post_crypto/derive_keys",
    "/api/post_crypto/verify_access",
    "/api/post_crypto/encrypted/{post_id}/preview",
)

# 并行族的四个"写口收键"字段：真值是库里那 5 个列，接口层不再收
RETIRED_POST_FIELDS = {
    "encryption_enabled",
    "encryption_salt",
    "encryption_verifier",
    "encryption_algorithm",
}

_PY_SUFFIXES = {".py"}
_FRONTEND_SUFFIXES = {".ts", ".vue", ".json"}
_SKIP_DIR_NAMES = {"node_modules", ".output", ".nuxt", "dist", ".cache", "__pycache__"}


def _sources(root: Path, suffixes: set[str]) -> list[Path]:
    out: list[Path] = []
    for path in root.rglob("*"):
        if path.suffix not in suffixes or not path.is_file():
            continue
        if _SKIP_DIR_NAMES.intersection(path.relative_to(root).parts[:-1]):
            continue
        out.append(path)
    return out


def test_retired_paths_are_gone_from_openapi():
    """PUT/DELETE 与 POST 共用同一个 path，所以这条按 path 覆盖整族 7 条操作。"""
    paths = set(app.openapi()["paths"])
    for retired in RETIRED_PATHS:
        assert retired not in paths, f"{retired} 又出现了：并行加密族是退役决定，不是缺口"


def test_retired_modules_and_helpers_are_deleted():
    for rel in ("api/post_encryption.py", "api/post_crypto.py", "core/crypto.py"):
        assert not (BACKEND / rel).exists(), f"backend/{rel} 回来了：它没有任何调用方"

    hits = [
        path.relative_to(REPO).as_posix()
        for path in _sources(BACKEND, _PY_SUFFIXES)
        if any(
            needle in path.read_text(encoding="utf-8")
            for needle in ("backend.core.crypto", "post_crypto", "post_encryption")
        )
    ]
    assert hits == [], f"这些后端文件仍引用退役模块：{hits}"


def test_main_py_neither_imports_nor_registers_the_family():
    src = (BACKEND / "main.py").read_text(encoding="utf-8")
    assert "post_crypto" not in src and "post_encryption" not in src
    tags = {entry["name"] for entry in TAG_METADATA}
    assert "内容加密" not in tags and "文章加密工具" not in tags, (
        "TAG_METADATA 里留着只挂僵尸路由的标签，OpenAPI 侧栏会出现点不开的空分组"
    )


def test_post_write_schemas_drop_the_salt_fields_but_keep_the_live_ones():
    from backend.schemas import PostCreate, PostUpdate

    for model in (PostCreate, PostUpdate):
        fields = set(model.model_fields)
        assert not (fields & RETIRED_POST_FIELDS), (
            f"{model.__name__} 重新收下 {sorted(fields & RETIRED_POST_FIELDS)}："
            "这四个字段写进去后没有任何读口回吐，属于「写口收键、读口不回吐」"
        )
        assert {"password", "encryption_hint"} <= fields, (
            f"{model.__name__} 连主线密码字段一起删了——那是把删僵尸做成删功能"
        )


def test_oobe_fake_switch_is_gone_end_to_end():
    from backend.api.oobe import CombinedInstallRequest
    from backend.schemas import SiteConfigResponse

    assert "enable_encrypted_posts" not in CombinedInstallRequest.model_fields, (
        "OOBE 又收这个键了：它只落 .env 与 SiteConfig，全站没有读取方"
    )
    assert "enable_encrypted_posts" not in SiteConfigResponse.model_fields

    for rel in ("api/oobe.py", "api/core.py", "core/oobe_constants.py", "scripts/auto_oobe.py"):
        assert "enable_encrypted_posts" not in (BACKEND / rel).read_text(encoding="utf-8"), rel

    hits = [
        path.relative_to(REPO).as_posix()
        for path in _sources(FRONTEND, _FRONTEND_SUFFIXES)
        if "enableEncryptedPosts" in path.read_text(encoding="utf-8")
        or "fCrypto" in path.read_text(encoding="utf-8")
    ]
    assert hits == [], f"前端仍声明加密文章开关（表单或四语文案）：{hits}"


# ---------------------------------------------------------
# 以下是"活路径不得被一起删掉"的一侧
# ---------------------------------------------------------
def test_mainline_password_gate_is_intact():
    """主线闸门 = 哈希落 Post.password + 判据单源 + 详情口按判据隐藏正文。"""
    from backend.models.blog import Post

    columns = {column.name for column in Post.__table__.columns}
    assert {"password", "encryption_hint", "encrypted_content"} <= columns, (
        "表结构被动了：这次退役的边界是接口与写口，不是列（历史备份里可能有密文）"
    )

    gate_src = (BACKEND / "services" / "post_access.py").read_text(encoding="utf-8")
    assert "async def post_content_unlocked" in gate_src
    assert 'getattr(post, "password"' in gate_src, (
        "判据不再读 Post.password——主线密码门换了真相源，要跟这条守卫一起改"
    )

    blog_src = (BACKEND / "api" / "blog.py").read_text(encoding="utf-8")
    assert "hash_post_password" in blog_src, "写口不再哈希密码：密码文章等于没设密码"
    assert "is_password_protected = bool(post.password)" in blog_src, (
        "详情口不再按 Post.password 判门，并行族的字段却已被接口层拒收"
    )
    assert "encryption_hint" in blog_src, "encryption_hint 的读写四段被一起删掉了（批次 #17）"


def test_cipher_blob_still_round_trips_through_backup():
    """ZIP 导出/导入原样搬运密文列：删接口不等于让历史备份丢正文。"""
    src = (BACKEND / "api" / "import_export.py").read_text(encoding="utf-8")
    assert '"encrypted_content": p.encrypted_content' in src, "导出不再带密文列"
    assert "encrypted_content=item.get(" in src, "导入不再写回密文列"


def test_coverage_doc_records_the_retirement():
    doc = (FRONTEND / "docs" / "API_COVERAGE.md").read_text(encoding="utf-8")
    # 按"表行"的写法清点，而不是按裸模块名：退役记录本身要提到这两个名字与守卫文件名。
    for row_head in ("| post_encryption（", "| post_crypto（"):
        assert row_head not in doc, (
            f"覆盖度文档仍留着 {row_head}… 这一行：下一个人会当成待接入的缺口重接一遍"
        )
    assert "退役" in doc
