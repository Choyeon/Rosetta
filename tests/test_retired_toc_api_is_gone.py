"""批次 #155：`backend/api/toc.py` 整族退役后的负向清点。

删掉的是三个**公开、无鉴权、零消费方**的 POST（`/api/toc/generate`、`/extract`、`/add-ids`）：

* 前端一个都不调——文章目录的锚点、层级、渲染全部由 `frontend/lib/toc.ts` 在浏览器/SSR 里算
  （契约钉在 `frontend/tests/unit/tocAnchors.spec.ts`），后台编辑器也没有接；
* 后端那一份的 id 规则和前台**不一致**（`re.sub(r"[^\\w\\u4e00-\\u9fff-]", "-", text.lower())`
  vs `frontend/lib/toc.ts` 的单源），所以它不是"另一个可用实现"，而是"看起来能用、接上就跳错锚点"
  的第二份真相；
* 三个口都是纯 CPU 的递归解析且没有任何限流规则登记，等于是给匿名访客的免费正则轰炸面。

同批退役的还有这三族在 `/api/config` 里的扁平镜像键（`enable_toc` / `enable_reading_time` /
`enable_word_count`），守卫在 `tests/test_retired_flat_config_keys_are_gone.py`。

另一半断言防"把退役做成误删活功能"：`frontend/lib/toc.ts` 与详情页的消费点必须原样在场。
"""

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"

RETIRED_PATHS = ("/api/toc/generate", "/api/toc/extract", "/api/toc/add-ids")
RETIRED_MODELS = ("TOCItem", "TOCRequest", "TOCResponse", "TOCHeadingItem")


def test_the_module_and_its_wiring_are_gone():
    assert not (BACKEND / "api" / "toc.py").exists(), "toc.py 又回来了"
    text = (BACKEND / "main.py").read_text(encoding="utf-8")
    assert "\n    toc,\n" not in text, "main.py 的导入清单里又出现 toc"
    assert "include_router(toc" not in text, "路由又被挂回 /api/toc"


def test_openapi_has_no_toc_paths_or_models():
    from backend.main import app

    paths = app.openapi()["paths"]
    for path in RETIRED_PATHS:
        assert path not in paths, f"{path} 又出现在接口文档里"
    assert not any(p.startswith("/api/toc") for p in paths)
    schemas = app.openapi()["components"]["schemas"]
    for name in RETIRED_MODELS:
        assert name not in schemas, f"文档模型 {name} 又回来了"


@pytest.mark.asyncio
async def test_the_three_endpoints_answer_404(client):
    """退役必须是 404，不是 405/422——路由整条不存在才是「已退役」。"""
    for path in RETIRED_PATHS:
        resp = await client.post(path, json={})
        assert resp.status_code == 404, f"{path} 仍在提供服务（{resp.status_code}）"


def test_no_rate_limit_rule_is_left_orphaned():
    """限流表里不该留一条指向不存在路由的规则（死规则还会占住首命中位置）。"""
    text = (BACKEND / "core" / "rate_limit.py").read_text(encoding="utf-8")
    assert "/api/toc" not in text


def test_the_live_toc_source_is_still_the_frontend_lib():
    """删掉重复实现不等于删掉目录功能：唯一实现与它的消费点必须还在。"""
    lib = (FRONTEND / "lib" / "toc.ts").read_text(encoding="utf-8")
    assert "export const annotateHeadings" in lib, "lib/toc.ts 的锚点写入消失"
    assert "export const slugifyHeading" in lib, "lib/toc.ts 的 id 规则单源消失"

    detail = (FRONTEND / "pages" / "posts" / "[slug].vue").read_text(encoding="utf-8")
    assert "annotateHeadings" in detail, "详情页不再消费单源锚点"
    assert "extractTOC(el, site.reading.value.toc_depth)" in detail, (
        "详情页目录不再按 reading.toc_depth 取数＝活开关断了"
    )

    spec = (FRONTEND / "tests" / "unit" / "tocAnchors.spec.ts").read_text(encoding="utf-8")
    assert "lib/toc" in spec, "目录契约守卫不再点名 lib/toc＝上一批断言在空转"


def test_pyproject_coverage_omit_has_no_dangling_entries():
    """退役一个模块要连 `pyproject.toml` 的覆盖率 omit 一起清。

    那份清单是按文件路径写的，文件没了它不会报错——只会长期挂着「backend/api/toc.py」
    这种指向不存在文件的条目（本批同批清掉的还有批次 #106 留下的 post_crypto /
    post_encryption 两条）。挂着的害处不是脏：下一个读到它的人会以为那两个模块还在，
    而覆盖率统计里也永远不会有人发现这条 omit 早已失效。
    """
    import re

    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    listed = re.findall(r'"(backend/[^"]+\.py)"', text)
    assert listed, "omit 清单一条都扫不到＝扫描方式失效，本测试会恒真"
    dangling = [item for item in listed if not (REPO / item).exists()]
    assert not dangling, f"覆盖率 omit 里挂着已删除的文件：{dangling}"
    assert "backend/api/toc.py" not in text
