"""友链「审核状态」(status) 的公开强制口与管理口守卫。

这一族曾是三种「半接通」形状叠在一起：

1. **公开口兼任管理视图**：`GET /api/friend-links?all=true` 无鉴权，任何人
   （含抓取器）可枚举 pending / rejected / 已停用友链的 name、url、logo、
   created_at —— 后台包装层一度就是这么取的。
2. **公开闸门只看镜像列**：`status` 与 `is_active` 是两列，而响应模型的对齐
   只改字段值、**不删行**，所以「status=rejected 而 is_active 仍为 True」的
   历史/导入行照样进公开列表与响应缓存。
3. **恢复工具是第三个写手**：只搬 `is_active`，于是它能当场制造出上面那对
   矛盾列，而导出又不带 `status`（导出→恢复一圈把审核结果抹成默认档）。

口径：
* **status 是唯一控制权**，`is_active` 只是它的投影（后台只有一个审核档位
  Select，没有任何"独立停用"的入口）。域规则单源在 `FriendLink` 模型
  （`VALID_STATUSES` / `normalize_status_active` / `publicly_visible`），
  写口 pattern、公开 SQL 谓词、预热口、恢复归一四处必须同源。
* 管理视图另开 `GET /api/admin/friend-links`（staff only，整表返回，
  不进响应缓存 —— 它跨权限档位，缓存了就是把未审核行烘进公开键位）。
* 兼容档：`status` 缺失/非法的老行按 `is_active` 判，免得把"库里早就公示着
  的行"因为档位没写而凭空收掉。
"""

from __future__ import annotations

import pathlib

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import cache, make_cache_key
from backend.models.core import FriendLink


def _items(payload) -> list[dict]:
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    if isinstance(payload, list):
        return payload
    raise AssertionError(f"接口没有返回列表载荷: {payload!r}")


def _urls(payload) -> list[str]:
    return [r["url"] for r in _items(payload)]


async def _add(db_session: AsyncSession, url: str, status: str, is_active: bool) -> FriendLink:
    link = FriendLink(
        name={"zh": url, "en": url, "ja": url, "zh_Hant": url},
        url=url,
        order=1,
        status=status,
        is_active=is_active,
    )
    db_session.add(link)
    await db_session.commit()
    return link


class TestPublicGateFollowsStatus:
    """公开口必须按 status 挡行，而不是按镜像列。"""

    async def test_pending_and_rejected_are_not_public_even_when_mirror_is_true(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await cache.clear()
        await _add(db_session, "https://ok.example.com", "approved", True)
        await _add(db_session, "https://pending.example.com", "pending", True)
        await _add(db_session, "https://rejected.example.com", "rejected", True)

        urls = _urls((await client.get("/api/friend-links")).json())
        assert urls == ["https://ok.example.com"], f"公开口漏出未通过审核的行: {urls}"

    async def test_approved_wins_over_a_stale_mirror_column(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """「已通过但镜像列没跟上」按 status 判公开。

        这一条是"镜像不是第二个控制权"的另一面：后台没有独立停用入口，
        所以脏镜像列不该把已通过的行永久藏起来（那才是没人能改回来的死状态）。
        """
        await cache.clear()
        await _add(db_session, "https://stale-mirror.example.com", "approved", False)

        urls = _urls((await client.get("/api/friend-links")).json())
        assert "https://stale-mirror.example.com" in urls

    async def test_all_param_no_longer_returns_an_admin_view(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """?all=true 曾是匿名管理视图；现在它只是一个被忽略的多余查询参数。"""
        await cache.clear()
        await _add(db_session, "https://ok2.example.com", "approved", True)
        await _add(db_session, "https://secret2.example.com", "rejected", True)

        with_all = _urls((await client.get("/api/friend-links", params={"all": "true"})).json())
        assert with_all == ["https://ok2.example.com"]

    async def test_legacy_row_without_valid_status_falls_back_to_the_mirror(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """收紧不能把「档位脏但一直公示着」的老行一起吞掉。"""
        await cache.clear()
        await _add(db_session, "https://legacy-ok.example.com", "approved", True)
        link = await _add(db_session, "https://legacy-weird.example.com", "approved", True)
        link.status = ""  # 直接写库/早期导入留下的脏档位
        await db_session.commit()
        await cache.clear()

        urls = _urls((await client.get("/api/friend-links")).json())
        assert "https://legacy-weird.example.com" in urls

    async def test_approve_flipping_a_pending_row_makes_it_public(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await cache.clear()
        link = await _add(db_session, "https://to-approve.example.com", "pending", False)
        assert "https://to-approve.example.com" not in _urls(
            (await client.get("/api/friend-links")).json()
        )

        link.status = "approved"
        link.is_active = True
        await db_session.commit()
        await cache.clear()

        assert "https://to-approve.example.com" in _urls(
            (await client.get("/api/friend-links")).json()
        )

    async def test_anonymous_cannot_read_the_admin_list(self, client: AsyncClient):
        resp = await client.get("/api/admin/friend-links")
        assert resp.status_code in (401, 403)


class TestAdminListSurface:
    """管理口给出全部档位（审核页的页签计数依赖整表）。"""

    async def test_staff_sees_every_status(
        self, client: AsyncClient, db_session: AsyncSession, staff_headers: dict
    ):
        await cache.clear()
        await _add(db_session, "https://a-approved.example.com", "approved", True)
        await _add(db_session, "https://a-pending.example.com", "pending", False)
        await _add(db_session, "https://a-rejected.example.com", "rejected", False)

        all_rows = _urls(
            (await client.get("/api/admin/friend-links", headers=staff_headers)).json()
        )
        assert set(all_rows) == {
            "https://a-approved.example.com",
            "https://a-pending.example.com",
            "https://a-rejected.example.com",
        }

    async def test_admin_list_has_no_status_filter_param(
        self, client: AsyncClient, staff_headers: dict
    ):
        """筛选参数没有执行者就不该存在：审核页每个页签都要显示各档计数，
        服务端按档过滤会把其余页签的数字钉成 0（假读数）。
        """
        resp = await client.get(
            "/api/admin/friend-links", params={"status": "whatever"}, headers=staff_headers
        )
        assert resp.status_code == 200, "多余参数应被忽略，而不是造出一个没人用的筛选档"

    async def test_response_carries_status_for_the_admin_table(
        self, client: AsyncClient, db_session: AsyncSession, staff_headers: dict
    ):
        await cache.clear()
        await _add(db_session, "https://shape.example.com", "pending", True)
        rows = _items((await client.get("/api/admin/friend-links", headers=staff_headers)).json())
        row = next(r for r in rows if r["url"] == "https://shape.example.com")
        assert row["status"] == "pending", "管理表必须拿到审核档位本身"
        assert row["is_active"] is False, "镜像列必须由 status 投影，两列不得各说各话"


class TestCacheKeyDoesNotCrossBleed:
    """公开缓存键位固定为 active 档，管理视图不得写进同一键。"""

    async def test_admin_list_never_populates_the_public_key(
        self, client: AsyncClient, db_session: AsyncSession, staff_headers: dict
    ):
        await cache.clear()
        await _add(db_session, "https://bleed-ok.example.com", "approved", True)
        await _add(db_session, "https://bleed-hidden.example.com", "rejected", False)

        await client.get("/api/admin/friend-links", headers=staff_headers)
        assert await cache.get(make_cache_key("friend_links", "active")) is None, (
            "管理口写进了公开缓存键位"
        )

        await client.get("/api/friend-links")
        cached = await cache.get(make_cache_key("friend_links", "active"))
        assert cached and [r["url"] for r in cached] == ["https://bleed-ok.example.com"]


class TestNormalizeIsSingleSource:
    """归一函数的入参形态（公开谓词、写口、恢复工具共用同一份）。"""

    def test_only_approved_projects_to_active(self):
        assert FriendLink.normalize_status_active("approved", False) == ("approved", True)
        assert FriendLink.normalize_status_active("pending", True) == ("pending", False)
        assert FriendLink.normalize_status_active("rejected", True) == ("rejected", False)

    def test_missing_or_stray_status_falls_back_to_the_mirror_column(self):
        assert FriendLink.normalize_status_active(None, True) == ("approved", True)
        assert FriendLink.normalize_status_active("", False) == ("pending", False)
        assert FriendLink.normalize_status_active("weird", True) == ("approved", True)

    async def test_sql_predicate_and_response_projection_agree(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """SQL 闸门（公开读口 + 预热）与响应投影（is_active）是两处代码，必须对
        同一批行给出同一个答案 —— 各写一份分支的结局就是"管理表显示已拒绝、
        前台却公示出去"。所以拿真实 HTTP 读口交叉核对，而不是用同一个函数自证。
        """
        await cache.clear()
        cases = [
            ("https://pr-approved.example.com", "approved", True),
            ("https://pr-pending.example.com", "pending", True),
            ("https://pr-rejected.example.com", "rejected", True),
            ("https://pr-stray.example.com", "not-a-status", True),
        ]
        for url, status, act in cases:
            await _add(db_session, url, status, act)
        await cache.clear()

        public = set(_urls((await client.get("/api/friend-links")).json()))

        rows = (
            (
                await db_session.execute(
                    select(FriendLink).where(FriendLink.url.in_([c[0] for c in cases]))
                )
            )
            .scalars()
            .all()
        )
        from backend.schemas import FriendLinkResponse

        projected = {r.url for r in rows if FriendLinkResponse.model_validate(r).is_active}
        assert public == projected, (
            f"公开读口与响应投影判据分叉: sql={sorted(public)} proj={sorted(projected)}"
        )


class TestRestoreAndExportCarryStatus:
    """恢复工具是第三个写手：必须与写口同归一，否则当场造出矛盾列。

    整站恢复会重建全站表，在测试库里驱动它的成本与风险都远高于断言这几行
    存在（与 test_category_is_active_wired 同口径），所以用源文本守卫。
    """

    def test_export_payload_includes_status(self):
        """导出丢 status = 恢复一圈把审核结果重置成默认档。"""
        text = pathlib.Path("backend/api/import_export.py").read_text(encoding="utf-8")
        block = text[text.index("friend_links_data = [") :]
        block = block[: block.index("]")]
        assert '"status": f.status' in block

    def test_restore_normalizes_both_columns_on_each_branch(self):
        text = pathlib.Path("backend/api/import_export.py").read_text(encoding="utf-8")
        block = text[text.index("# === 6. friend_links ===") :]
        block = block[: block.index("# === 7. pages ===")]
        assert block.count("FriendLink.normalize_status_active(") == 2, (
            "覆盖分支与新建分支都要重过归一，缺一个就是矛盾列的制造口"
        )
        assert "existing_obj.status = st" in block
        assert "status=st" in block

    def test_model_owns_the_domain_and_every_surface_reads_it(self):
        """档位清单/归一/谓词只允许有一份，写在模型上。"""
        model = pathlib.Path("backend/models/core.py").read_text(encoding="utf-8")
        block = model[model.index("class FriendLink(") :]
        assert "STATUS_PENDING" in block and "VALID_STATUSES" in block
        assert "def normalize_status_active" in block and "def publicly_visible" in block

        schemas = pathlib.Path("backend/schemas/__init__.py").read_text(encoding="utf-8")
        assert "FriendLink.normalize_status_active(" in schemas, (
            "schemas 必须转发模型归一，不得自己再写一遍分支"
        )
        assert 'in ("pending", "approved", "rejected")' not in schemas, (
            "档位清单只允许有一份（在模型的 VALID_STATUSES 上）"
        )

        warmer = pathlib.Path("backend/core/cache_warmer.py").read_text(encoding="utf-8")
        anchor = "async def _warmup_friend_links"
        block = warmer[warmer.index(anchor) + len(anchor) :].split("async def ")[0]
        assert "FriendLink.publicly_visible()" in block, (
            "预热口必须复用同一条谓词，不得再镜像一遍判据"
        )
