"""
导航菜单位置（location）的读写闭环

后端早就有 location 这一列、写入侧的 pattern、公开口与管理口的筛选，`test_admin_nav_crud.py`
也测过"每个 Tab 独立数据"。这里钉的是那套筛选真正吃到的两个前提：

1. **缓存键必须带 location**：`make_cache_key("navigations", location or "all")` 少了第二个片段，
   先请求的那一档 payload 会被写进整族共用的键位，后请求的另一档直接拿到别人的菜单
   （表现：页脚显示顶栏的链接，且在 TTL 内稳定复现）。
2. **写口的失效必须覆盖全部位置键**：`invalidate_cache("navigations")` 是前缀删除，
   把一项从 header 移到 footer 之后，两档的公开口都要立刻反映这次移动。

另外补齐 `test_admin_nav_crud.py` 没测的两条：管理口带筛选时**仍回停用项**（后台要能把它打开），
以及 schema 的 pattern 档位与前台 UI 的档位清单逐值相等（前台三个渲染面各认一档，
少一档就是一个没人渲染的死档位，守卫见 `frontend/tests/unit/navigationLocationWired.spec.ts`）。
"""

import pytest
from httpx import AsyncClient

LOCATIONS = ("header", "footer", "sidebar")


def _titles_zh(rows: list[dict]) -> set[str]:
    return {str((r.get("title") or {}).get("zh", "")) for r in rows}


@pytest.mark.asyncio
class TestNavigationLocationRead:
    """公开口按位置分面 + 缓存键分面"""

    async def test_public_cache_key_carries_location(self, client: AsyncClient, make_navigations):
        """只 seed header 时，footer 档必须是空的。

        反证：缓存键去掉 location 后，footer 这一次请求会命中 header 刚写进去的同一份缓存，
        拿到 4 条 header 菜单——列表断言直接红，而不是"看起来也没错"。
        """
        await make_navigations("header", root_titles=["H1", "H2", "H3", "H4"])

        r_header = await client.get("/api/navigations", params={"location": "header"})
        assert r_header.status_code == 200
        assert _titles_zh(r_header.json()) == {"H1", "H2", "H3", "H4"}

        r_footer = await client.get("/api/navigations", params={"location": "footer"})
        assert r_footer.status_code == 200
        assert r_footer.json() == [], f"footer 档读到了别的位置：{r_footer.json()}"

        # 不带参数仍是全量（前端兜底与旧消费方依赖这个形态）
        r_all = await client.get("/api/navigations")
        assert _titles_zh(r_all.json()) == {"H1", "H2", "H3", "H4"}

    async def test_public_excludes_inactive_per_location(
        self, client: AsyncClient, staff_headers: dict
    ):
        """停用项在每一档都不可见（公开口只有一条 is_active 判据，不能只在 header 生效）"""
        for loc, title in zip(LOCATIONS, ("A-live", "B-live", "C-live"), strict=True):
            r = await client.post(
                "/api/navigations",
                headers=staff_headers,
                json={"title": {"zh": title}, "url": f"/{loc}", "location": loc},
            )
            assert r.status_code in (200, 201), r.text
        r_dead = await client.post(
            "/api/navigations",
            headers=staff_headers,
            json={
                "title": {"zh": "B-dead"},
                "url": "/footer-dead",
                "location": "footer",
                "is_active": False,
            },
        )
        assert r_dead.status_code in (200, 201), r_dead.text

        for loc, live_title in zip(LOCATIONS, ("A-live", "B-live", "C-live"), strict=True):
            rows = _titles_zh(
                (await client.get("/api/navigations", params={"location": loc})).json()
            )
            assert live_title in rows, f"{loc} 档读不到自己的激活项"
            assert "B-dead" not in rows, f"{loc} 档泄漏了停用项"
            others = {"A-live", "B-live", "C-live"} - {live_title}
            assert not (rows & others), f"{loc} 档读到了其它位置的项：{rows & others}"

    async def test_admin_location_filter_still_lists_inactive(
        self, client: AsyncClient, staff_headers: dict
    ):
        """后台筛选必须带出停用项，否则「隐藏」的项在后台消失、再也打不开"""
        created = []
        for title, loc in (
            ("AdminLive", "footer"),
            ("AdminHidden", "footer"),
            ("AdminOther", "sidebar"),
        ):
            r = await client.post(
                "/api/navigations",
                headers=staff_headers,
                json={
                    "title": {"zh": title},
                    "url": f"/{title.lower()}",
                    "location": loc,
                    "is_active": title != "AdminHidden",
                },
            )
            assert r.status_code in (200, 201), r.text
            created.append(r.json())
        assert {c["location"] for c in created} == {"footer", "sidebar"}
        assert [c["is_active"] for c in created] == [True, False, True], (
            "写口的 location / is_active 没有落值"
        )

        r_footer = await client.get(
            "/api/admin/navigations", headers=staff_headers, params={"location": "footer"}
        )
        assert r_footer.status_code == 200
        footer_rows = r_footer.json()
        assert {"AdminLive", "AdminHidden"} <= _titles_zh(footer_rows), _titles_zh(footer_rows)
        assert "AdminOther" not in _titles_zh(footer_rows), "管理口按位置筛漏了"
        assert "AdminHidden" not in _titles_zh(
            (await client.get("/api/navigations", params={"location": "footer"})).json()
        )


@pytest.mark.asyncio
class TestNavigationLocationWrite:
    """移动位置 = 换渲染面，且立刻生效"""

    async def test_move_between_locations_switches_faces(
        self, client: AsyncClient, staff_headers: dict
    ):
        r = await client.post(
            "/api/navigations",
            headers=staff_headers,
            json={"title": {"zh": "Mover"}, "url": "/mover", "location": "header"},
        )
        assert r.status_code in (200, 201), r.text
        nav_id = r.json()["id"]

        # 先读一次，把 header 档写进缓存；再读 sidebar（空），两档各自成键
        assert "Mover" in _titles_zh(
            (await client.get("/api/navigations", params={"location": "header"})).json()
        )
        assert (await client.get("/api/navigations", params={"location": "sidebar"})).json() == []

        moved = await client.put(
            f"/api/navigations/{nav_id}", headers=staff_headers, json={"location": "sidebar"}
        )
        assert moved.status_code == 200, moved.text
        assert moved.json()["location"] == "sidebar"

        # 反证：invalidate 只清了 navigations:all 或按旧键清，这里至少有一档仍是旧的
        assert "Mover" not in _titles_zh(
            (await client.get("/api/navigations", params={"location": "header"})).json()
        )
        assert "Mover" in _titles_zh(
            (await client.get("/api/navigations", params={"location": "sidebar"})).json()
        )

    async def test_partial_update_keeps_location(self, client: AsyncClient, staff_headers: dict):
        """PUT 是 exclude_unset 增量语义：只改 order 不得把位置抹回默认值"""
        r = await client.post(
            "/api/navigations",
            headers=staff_headers,
            json={"title": {"zh": "KeepMe"}, "url": "/keep-me", "location": "footer", "order": 3},
        )
        nav_id = r.json()["id"]
        upd = await client.put(
            f"/api/navigations/{nav_id}", headers=staff_headers, json={"order": 9}
        )
        assert upd.status_code == 200, upd.text
        assert upd.json()["location"] == "footer", "局部更新抹掉了位置"
        assert upd.json()["order"] == 9

    async def test_every_ui_location_roundtrips(self, client: AsyncClient, staff_headers: dict):
        """后台 UI 提供的三档逐值写入并落位；档位清单与前台渲染面由
        `frontend/tests/unit/navigationLocationWired.spec.ts` 双向对账。"""
        for index, loc in enumerate(LOCATIONS):
            title = f"Loc{index}"
            r = await client.post(
                "/api/navigations",
                headers=staff_headers,
                json={"title": {"zh": title}, "url": f"/loc-{index}", "location": loc},
            )
            assert r.status_code in (200, 201), r.text
            assert r.json()["location"] == loc, f"写口响应的位置与提交值不一致：{r.json()}"
            assert title in _titles_zh(
                (await client.get("/api/navigations", params={"location": loc})).json()
            )

    async def test_out_of_pattern_location_is_rejected(
        self, client: AsyncClient, staff_headers: dict
    ):
        r = await client.post(
            "/api/navigations",
            headers=staff_headers,
            json={"title": {"zh": "Bad"}, "url": "/bad", "location": "navbar"},
        )
        assert r.status_code == 422, f"非法位置应当被 schema 拒掉：{r.status_code} {r.text[:200]}"
