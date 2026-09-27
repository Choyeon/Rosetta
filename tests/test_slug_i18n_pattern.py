"""内容型 slug 允许 CJK、插件/主题 manifest slug 仍锁 ASCII 的契约回归测试。

背景：中文标题的文章/分类在后台保存时，前端 slugify 刻意产出中文 slug，而写入侧
schema 曾长期锁 `^[a-z0-9-]+$`，导致任何中文 slug 被 Pydantic 判 422
`string_pattern_mismatch`——与读取/URL 层既定的中文 slug 支持自相矛盾（见 memory
chinese-slug-url-loop）。本用例把两侧口径钉死：内容 schema 收 CJK、拒绝结构字符；
manifest schema 继续拒绝非 ASCII，防止有人把边界一次性放宽到内部标识符。
"""

import pytest
from pydantic import ValidationError

from backend.schemas import CategoryCreate, PageCreate, PostCreate, TagCreate
from backend.schemas.manifest import RosettaPluginManifest, RosettaThemeManifest
from backend.schemas.post_series import PostSeriesCreate


# 各内容 schema 的构造工厂：只需喂最小必填字段 + 待测 slug，
# 这样 slug 以外的字段不会引入额外校验噪声。
def _post(slug):  # noqa: ANN001, ANN202
    return PostCreate(title={"zh": "标题"}, content={"zh": "正文"}, slug=slug)


def _category(slug):  # noqa: ANN001, ANN202
    return CategoryCreate(name={"zh": "技术"}, slug=slug)


def _tag(slug):  # noqa: ANN001, ANN202
    return TagCreate(name={"zh": "标签"}, slug=slug)


def _page(slug):  # noqa: ANN001, ANN202
    return PageCreate(title={"zh": "关于"}, content={"zh": "内容"}, slug=slug)


def _series(slug):  # noqa: ANN001, ANN202
    return PostSeriesCreate(title={"zh": "系列"}, slug=slug)


CONTENT_BUILDERS = [_post, _category, _tag, _page, _series]


def _slug_errors(builder, slug):  # noqa: ANN001, ANN202
    """返回 schema 因该 slug 抛出的 slug 相关错误 loc 列表（无错则空）。"""
    try:
        builder(slug)
        return []
    except ValidationError as exc:
        return [err for err in exc.errors() if err["loc"] and err["loc"][-1] == "slug"]


@pytest.mark.parametrize("builder", CONTENT_BUILDERS)
@pytest.mark.parametrize("slug", ["中文", "前端开发", "qoder-端到端草稿", "post-1-快速上手"])
def test_content_slug_accepts_cjk(builder, slug):  # noqa: ANN001
    assert _slug_errors(builder, slug) == []


@pytest.mark.parametrize("builder", CONTENT_BUILDERS)
@pytest.mark.parametrize(
    "slug",
    ["../../etc/passwd", "a b", "<script>", "a%2Db", "Hello", "path/x", "a\\b", "问 题"],
)
def test_content_slug_rejects_unsafe(builder, slug):  # noqa: ANN001
    errs = _slug_errors(builder, slug)
    assert errs, f"应当拒绝非法 slug：{slug!r}"


@pytest.mark.parametrize("manifest_cls", [RosettaPluginManifest, RosettaThemeManifest])
def test_manifest_slug_stays_ascii_strict(manifest_cls):  # noqa: ANN001
    # 合法的 kebab ASCII 放行
    assert manifest_cls(name="X", slug="hello-rosetta", version="1.0.0")
    # 中文 slug 必须仍被拒——内部标识符边界不得随内容一起放宽
    with pytest.raises(ValidationError) as exc:
        manifest_cls(name="X", slug="中文插件", version="1.0.0")
    assert any(err["loc"] == ("slug",) for err in exc.value.errors())
