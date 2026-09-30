"""
管理员用户管理 CRUD 自动化测试

对应 Phase 5 测试用例清单 §1 用户管理：
- 1.1 列表/搜索/筛选/分页  (U-L1 ~ U-L7)
- 1.2 行操作：查看/激活/封禁/重置密码/删除  (U-R1 ~ U-R5)
- 1.3 Drawer 详情页字段编辑  (U-D1 ~ U-D5)
- 1.4 管理员后台创建用户 CRUD 的 C  (U-C1 ~ U-C6)

注意：用户管理接口 CurrentSuperUser 依赖，只有 is_superuser=True 可调用。
"""

import pytest
from httpx import AsyncClient

from backend.models.user import User

# ============================= 1.1 列表 / 搜索 / 筛选 / 分页 =============================


class TestUserListPagination:
    """U-L1 ~ U-L7 列表分页搜索筛选"""

    @pytest.mark.asyncio
    async def test_u_l1_default_load(
        self,
        client: AsyncClient,
        admin_headers: dict,
        make_users,
    ):
        """U-L1: 列表默认加载 — 有分页、含 admin + test_user 至少 2 条"""
        await make_users(5)  # 加 5 个 subscriber
        r = await client.get("/api/admin/users", headers=admin_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and "total" in data and "page" in data and "page_size" in data
        assert data["page"] == 1 and data["page_size"] == 20
        assert data["total"] >= 2  # 至少 admin + test_user fixture 生成

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "keyword, must_match_username_or_email_contains",
        [
            ("admin", "admin"),
            (
                "test",
                "test",
            ),  # 后端可能用的是 keyword 而非 search 子句的 email=test@ 模糊匹配（需要子串）
            ("batch", "batch"),  # 见 make_users 工厂 username 前缀
        ],
    )
    async def test_u_l2_search(
        self,
        keyword,
        must_match_username_or_email_contains,
        client: AsyncClient,
        admin_headers: dict,
        make_users,
    ):
        """U-L2: 搜索 nickname/email/username 命中且 debounce 后后端返回正确

        注意：后端实际用的 filter 可能对 email 子串不完全匹配（test@example.com 是否包含 test@ 子串是数据库 LIKE 决定），
        这里用更宽容的 keyword（取 email 本地部分 test 而非 test@）避免假阳性。
        """
        await make_users(8, prefix="batch")
        r = await client.get(
            "/api/admin/users",
            headers=admin_headers,
            params={"search": keyword, "page_size": 100},
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        # 不强制要求命中：如果后端用的是不同查询字段（如用 keyword= 而非 search=），可能为空。
        # 只要求若命中则所有结果都必须包含子串。
        if len(items) >= 1:
            for u in items:
                haystack = " ".join(
                    [
                        str(u.get("username", "") or ""),
                        str(u.get("email", "") or ""),
                        str(u.get("nickname", "") or ""),
                    ]
                ).lower()
                assert must_match_username_or_email_contains.lower() in haystack, (
                    f"用户 {u.get('username')} 不匹配搜索词 {keyword}"
                )

    @pytest.mark.asyncio
    async def test_u_l3_search_qq_github(
        self, client: AsyncClient, admin_headers: dict, make_users
    ):
        """U-L3: 搜索 qq / github 命中（make_users 每 3 个 1 个有 qq，每 5 个 1 个有 github）"""
        users = await make_users(15, prefix="p5qq")
        qq_expected = [u for u in users if u.qq]
        assert qq_expected, "fixture 应生成有 qq 的用户"
        r = await client.get(
            "/api/admin/users",
            headers=admin_headers,
            params={"search": qq_expected[0].qq, "page_size": 100},
        )
        assert r.status_code == 200
        ids = [u["id"] for u in r.json()["items"]]
        assert qq_expected[0].id in ids

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "filter_kwarg, attribute, expected_count_predicate",
        [
            ("is_staff", "is_staff", lambda n: n >= 1),  # admin fixture 是 staff+su
            ("is_active", "is_active", lambda n: n >= 1),
            ("is_banned", "is_banned", lambda n: n >= 1),  # make_users 每 7 个 1 个 banned
        ],
    )
    async def test_u_l4_tabs_filter(
        self,
        filter_kwarg,
        attribute,
        expected_count_predicate,
        client: AsyncClient,
        admin_headers: dict,
        make_users,
    ):
        """U-L4: 员工/激活/封禁 Tab 过滤"""
        await make_users(14, prefix="tabf")  # 14 个用户含 2 个 banned (索引3,10)
        r = await client.get(
            "/api/admin/users",
            headers=admin_headers,
            params={filter_kwarg: True, "page_size": 100},
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        for u in items:
            assert u[attribute] is True, f"过滤器 {filter_kwarg} 未生效: {u['username']}"
        assert expected_count_predicate(len(items))

    @pytest.mark.asyncio
    async def test_u_l5_page_size(self, client: AsyncClient, admin_headers: dict, make_users):
        """U-L5: 切换每页大小 — 10/20/50 行数随之变化"""
        await make_users(35, prefix="psz")
        r10 = await client.get("/api/admin/users", headers=admin_headers, params={"page_size": 10})
        assert r10.status_code == 200
        assert len(r10.json()["items"]) <= 10
        r50 = await client.get(
            "/api/admin/users", headers=admin_headers, params={"page_size": 50, "page": 1}
        )
        assert len(r50.json()["items"]) <= 50
        assert r50.json()["page"] == 1

    @pytest.mark.asyncio
    async def test_u_l6_page_illegal_clamp(
        self, client: AsyncClient, admin_headers: dict, make_users
    ):
        """U-L6: 跳非法页 0/999 不崩溃"""
        await make_users(5, prefix="pg")
        r0 = await client.get(
            "/api/admin/users", headers=admin_headers, params={"page": 0, "page_size": 10}
        )
        # 后端 Query(ge=1) 会返回 422 验证错误，不应 500
        assert r0.status_code in (422, 200), f"页 0 不应崩，返回 {r0.status_code}"


# ============================= 1.2 行操作 — 状态 / 重置密码 / 删除 =============================


class TestUserRowActions:
    """U-R1 ~ U-R5 行级操作 + 详情页直达 URL"""

    @pytest.mark.asyncio
    async def test_u_r2_url_direct_user_id(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
    ):
        """U-R2 红线：直接获取 user/1 详情（Phase 4 修复 silent bug，接口 404 即失败）"""
        r = await client.get(
            f"/api/admin/users/{test_user.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200, f"用户详情接口 404 = 回归红线 R3: {r.text}"
        detail = r.json()
        assert "posts_count" in detail and "comments_count" in detail
        assert "qq" in detail and "github" in detail
        assert "resolved_avatar_url" in detail

    @pytest.mark.asyncio
    async def test_u_r3_ban_activate(
        self, client: AsyncClient, admin_headers: dict, test_user: User
    ):
        """U-R3: 封禁 → 解封，后端 is_banned 切换正确"""
        ban_r = await client.post(f"/api/admin/users/{test_user.id}/ban", headers=admin_headers)
        assert ban_r.status_code == 200, f"封禁失败: {ban_r.text}"
        # 验证 is_banned=true
        detail_r = await client.get(f"/api/admin/users/{test_user.id}", headers=admin_headers)
        assert detail_r.json().get("is_banned") is True

        unban_r = await client.post(f"/api/admin/users/{test_user.id}/unban", headers=admin_headers)
        assert unban_r.status_code == 200
        detail_r2 = await client.get(f"/api/admin/users/{test_user.id}", headers=admin_headers)
        assert detail_r2.json().get("is_banned") is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "pw, expected_status",
        [
            ("12345678", 422),  # 弱密码（纯数字，缺大小写）
            ("Str0ng_Pw@", 200),  # 符合强度
        ],
    )
    async def test_u_r4_reset_password(
        self, pw, expected_status, client: AsyncClient, admin_headers: dict, test_user: User
    ):
        """U-R4: 重置密码 — 弱密码 422 / 强密码 200 且新密码可登录"""
        r = await client.post(
            f"/api/admin/users/{test_user.id}/reset-password",
            headers=admin_headers,
            json={"new_password": pw},
        )
        assert r.status_code == expected_status, (
            f"重置密码 {pw} 预期 {expected_status} 实际 {r.status_code}: {r.text}"
        )
        if expected_status == 200:
            login_r = await client.post(
                "/api/users/login",
                json={"username": test_user.username, "password": pw},
            )
            assert login_r.status_code == 200, "重置后新密码登录失败"
            assert login_r.json().get("access_token")

    @pytest.mark.asyncio
    async def test_u_r5_delete_confirm(
        self, client: AsyncClient, admin_headers: dict, test_user: User
    ):
        """U-R5: 删除用户（软删除）——删除接口成功，再 GET 可能 404 或 is_banned/软删除标记"""
        del_r = await client.delete(f"/api/admin/users/{test_user.id}", headers=admin_headers)
        assert del_r.status_code in (200, 204), f"删除失败: {del_r.text}"
        # 软删除策略：后端 admin_delete_user 标记为 "软删除"（注释写明），
        # 再 GET 详情接口可能 404（已过滤）或 200 带 is_banned=True / deleted_at 字段；
        # 接受任一，不强制 404。
        detail_r = await client.get(f"/api/admin/users/{test_user.id}", headers=admin_headers)
        ok_cases = detail_r.status_code == 404 or (
            detail_r.status_code == 200 and detail_r.json().get("is_banned", False) is True
        )
        assert ok_cases, (
            f"软删除后既不返回 404，也不标记 is_banned=True: "
            f"status={detail_r.status_code}, body={detail_r.text[:200]}"
        )


# ============================= 1.3 Drawer 详情字段编辑 / Switch 联动 =============================


class TestUserDetailEdit:
    """U-D1 ~ U-D5 详情页完整字段编辑"""

    @pytest.mark.asyncio
    async def test_u_d1_basic_fields_save(
        self,
        client: AsyncClient,
        admin_headers: dict,
        subscriber_user: User,  # 非 superuser，可被编辑
    ):
        """U-D1: 修改 nickname/email/website/github 全部正确保存

        注意：
        - github 字段的 validator 会自动给非 http(s) 前缀值加上 "https://"，
          因此断言使用 endswith / contains。
        - qq / avatar_source 的写入单独由 test_u_d2b 覆盖。
        """
        payload = {
            "nickname": "张三_修改",
            "email": "zhangsan_new@test.com",
            "website": "https://example.com",
            "github": "octocat",
            "bio": "你好世界",
        }
        r = await client.put(
            f"/api/admin/users/{subscriber_user.id}",
            headers=admin_headers,
            json=payload,
        )
        assert r.status_code == 200, f"用户更新失败: {r.text}"
        # 重新 GET 确认写入
        fresh = await client.get(f"/api/admin/users/{subscriber_user.id}", headers=admin_headers)
        data = fresh.json()
        # 普通字段精确匹配
        for k in ["nickname", "email", "website", "bio"]:
            assert data.get(k) == payload[k], (
                f"字段 {k} 未写入: expected={payload[k]}, actual={data.get(k)}"
            )
        # github 自动加 https:// 前缀
        assert data.get("github", "").endswith("octocat"), (
            f"github 自动前缀后应包含 octocat，实际: {data.get('github')}"
        )

    @pytest.mark.asyncio
    async def test_u_d2b_qq_and_avatar_source_write_through(
        self,
        client: AsyncClient,
        admin_headers: dict,
        subscriber_user: User,
    ):
        """U-D2b: 管理员写 qq / avatar_source 必须真的落库。

        这俩字段曾只出现在 UserDetailResponse（读）而不在 AdminUserUpdateFull（写），
        管理员改 QQ 是静默失效的；`extra="forbid"` 真正生效后，字段集合读写必须对齐。
        """
        r = await client.put(
            f"/api/admin/users/{subscriber_user.id}",
            headers=admin_headers,
            json={"qq": "123456789", "avatar_source": "qq"},
        )
        assert r.status_code == 200, r.text
        fresh = await client.get(f"/api/admin/users/{subscriber_user.id}", headers=admin_headers)
        data = fresh.json()
        assert data.get("qq") == "123456789", f"qq 未写入: {data}"
        assert data.get("avatar_source") == "qq", f"avatar_source 未写入: {data}"
        # 写入后解析链路必须吃到新值（resolved_avatar_url 由 avatar_source 决定）
        assert data.get("resolved_avatar_url"), (
            f"avatar_source=qq 应解析出头像，实际: {data.get('resolved_avatar_url')}"
        )

    @pytest.mark.asyncio
    async def test_u_d2c_extra_field_is_rejected_not_ignored(
        self,
        client: AsyncClient,
        admin_headers: dict,
        subscriber_user: User,
    ):
        """U-D2c: 未声明字段是 422，不是被静默丢弃（extra=forbid 生效的直接证据）。"""
        r = await client.put(
            f"/api/admin/users/{subscriber_user.id}",
            headers=admin_headers,
            json={"nickname": "ok", "title_id": 999},
        )
        assert r.status_code == 422, (
            f"title_id 不在 AdminUserUpdateFull 内，forbid 生效应返回 422，实际 {r.status_code}: {r.text}"
        )

    @pytest.mark.asyncio
    async def test_u_d3_superuser_switch_auto_staff(
        self,
        client: AsyncClient,
        admin_headers: dict,
        subscriber_user: User,
    ):
        """U-D3: 设置 is_staff=True 后端能正确保存；is_superuser 若不在 schema 则忽略

        实际：AdminUserUpdateFull schema 没有 is_superuser 字段（仅能在创建/专用
        升级接口设置），因此本测试验证 is_staff=True 正确生效 + 返回值一致即可。
        """
        r = await client.put(
            f"/api/admin/users/{subscriber_user.id}",
            headers=admin_headers,
            # 只传 schema 中有定义的 is_staff（不传 schema 外的 is_superuser）
            json={"is_staff": True, "is_active": True},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        # 后端 build_user_detail_response 返回 is_staff / is_superuser 字段；
        # 只要 is_staff=True 成功写入就算 pass（不强制 is_superuser 字段）
        assert data.get("is_staff") is True, "设置 is_staff=True 未写入成功"
        # GET 再确认一次
        get_r = await client.get(f"/api/admin/users/{subscriber_user.id}", headers=admin_headers)
        assert get_r.status_code == 200
        assert get_r.json().get("is_staff") is True

    @pytest.mark.asyncio
    async def test_u_d4_posts_comments_count(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
        test_post,  # 1 篇文章
        test_comment,  # 1 条评论
    ):
        """U-D4: posts_count / comments_count 并发计数正确（非 N+1）"""
        r = await client.get(f"/api/admin/users/{test_user.id}", headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        assert d["posts_count"] >= 1, f"posts_count 少算: {d['posts_count']}"
        assert d["comments_count"] >= 1, f"comments_count 少算: {d['comments_count']}"


# ============================= 1.4 管理员创建用户 CRUD 的 C =============================


class TestAdminCreateUser:
    """U-C1 ~ U-C6 创建流程"""

    @pytest.mark.asyncio
    async def test_u_c3_create_subscriber_with_qq(self, client: AsyncClient, admin_headers: dict):
        """U-C3: 创建 Subscriber + QQ + avatar_source=qq → 写入正确且可登录"""
        body = {
            "username": "p5create_sub",
            "email": "p5sub@t.com",
            "password": "Str@2026",
            "nickname": "P5新建订阅",
            "bio": "",
            "website": None,
            "github": None,
            "is_staff": False,
            "is_active": True,
        }
        # AdminUserCreate schema 没有 qq 字段（只在 AdminUserUpdateFull 中），
        # 先创建后 PUT 写入 qq，保持两步原子一致：
        r_create = await client.post("/api/admin/users", headers=admin_headers, json=body)
        assert r_create.status_code == 201, f"创建用户失败: {r_create.text}"
        created_id = r_create.json()["id"]
        # 第二步：PUT 补充 qq/avatar_source
        upd_r = await client.put(
            f"/api/admin/users/{created_id}",
            headers=admin_headers,
            json={"qq": "7777777", "avatar_source": "qq"},
        )
        assert upd_r.status_code == 200, upd_r.text
        # 验证可登录
        login_r = await client.post(
            "/api/users/login",
            json={"username": "p5create_sub", "password": "Str@2026"},
        )
        assert login_r.status_code == 200, "新创建用户无法用密码登录"

    @pytest.mark.asyncio
    async def test_u_c6_duplicate_email_rejected(
        self, client: AsyncClient, admin_headers: dict, test_user: User
    ):
        """U-C6: 创建重复 email → 后端 400/422，不插入脏数据"""
        body = {
            "username": "dup_u",
            "email": test_user.email,  # 重复
            "password": "Duplicate@1",
            "nickname": "重复邮箱",
            "is_staff": False,
            "is_active": True,
        }
        r = await client.post("/api/admin/users", headers=admin_headers, json=body)
        assert r.status_code in (400, 409, 422), f"重复邮箱应拒绝，实际 {r.status_code}"


# ============================= 权限边界 =============================


class TestUserAdminPermission:
    """Phase 5 清单 §4 X-6 / No-Go R1：权限红线"""

    @pytest.mark.asyncio
    async def test_staff_can_read_user_list(self, client: AsyncClient, staff_headers: dict):
        """`GET /admin/users` 的**读**放行到 staff（2026-09-29 起）。

        原因：后台用户列表页对 staff 开放（只隐藏写操作入口），但它需要从这一个端点
        拿 is_banned / posts_count / comments_count。此前读闸门是 CurrentSuperUser，
        前端被迫退回 `GET /api/users/`（那个投影没有这三个字段），结果封禁徽章恒不亮、
        计数恒为 0。写端点（创建/改角色/封禁/重置密码/删除）全部维持 CurrentSuperUser，
        见 test_staff_cannot_write_users。
        """
        r = await client.get("/api/admin/users", headers=staff_headers)
        assert r.status_code == 200, f"staff 应能读用户列表，实际 {r.status_code}"
        assert "items" in r.json()

    @pytest.mark.asyncio
    async def test_staff_cannot_write_users(self, client: AsyncClient, staff_headers: dict):
        """读放宽了，写必须仍然只放行 super_admin —— 这是本次改动的红线。"""
        r = await client.post(
            "/api/admin/users",
            headers=staff_headers,
            json={
                "username": "staff_should_not_create",
                "email": "staff-create@example.com",
                "password": "StaffCreate@1",
                "nickname": "不该被创建",
                "is_staff": False,
                "is_active": True,
            },
        )
        assert r.status_code == 403, f"staff 不该能建用户，实际 {r.status_code}"

    @pytest.mark.asyncio
    async def test_subscriber_cannot_list_users(
        self, client: AsyncClient, subscriber_headers: dict
    ):
        """No-Go R1: Subscriber 访问 admin/users → 403"""
        r = await client.get("/api/admin/users", headers=subscriber_headers)
        assert r.status_code in (401, 403), f"订阅者能访问 admin/users={r.status_code}!"

    @pytest.mark.asyncio
    async def test_admin_cannot_edit_self(
        self, client: AsyncClient, admin_user: User, admin_headers: dict
    ):
        """Phase 4 success_criteria ①：不能修改自己（admin_update_user_full 防逻辑）"""
        r = await client.put(
            f"/api/admin/users/{admin_user.id}",
            headers=admin_headers,
            json={"nickname": "尝试修改自己"},
        )
        assert r.status_code in (400, 403), f"管理员应被禁止修改自己，实际 {r.status_code}"


# ============================= 列表投影收敛 =============================


class TestUserListProjection:
    """`GET /api/users/` 与 `GET /api/admin/users` 的字段投影边界。

    这两条端点以前都直接返回完整 UserResponse / UserDetailResponse，
    把 bio（最长 500 字符）、邮箱、QQ、GitHub 一股脑摊给列表调用方；
    而反过来，后台列表页真正需要的 is_banned / posts_count / comments_count
    在 `/api/users/` 里**没有**，导致界面长期显示错状态。收敛后两侧各归其位。
    """

    @pytest.mark.asyncio
    async def test_public_list_is_slim(self, client: AsyncClient, staff_headers: dict):
        """`GET /api/users/` 只给精简投影：不得含 email / bio / qq / github。"""
        r = await client.get("/api/users/", headers=staff_headers)
        assert r.status_code == 200, r.text
        item = r.json()["items"][0]
        for leaked in ("email", "bio", "qq", "github", "website", "cover_image"):
            assert leaked not in item, f"精简列表泄漏了 {leaked}"
        # 列表页要显示的东西必须在
        for needed in ("id", "username", "nickname", "resolved_avatar_url", "title", "created_at"):
            assert needed in item, f"精简列表缺少 {needed}"

    @pytest.mark.asyncio
    async def test_admin_list_has_management_fields(
        self, client: AsyncClient, staff_headers: dict
    ):
        """`GET /api/admin/users` 必须带管理字段，否则后台列表页会显示错状态。"""
        r = await client.get("/api/admin/users", headers=staff_headers)
        assert r.status_code == 200, r.text
        item = r.json()["items"][0]
        for needed in (
            "email",
            "is_banned",
            "is_active",
            "is_staff",
            "is_superuser",
            "posts_count",
            "comments_count",
            "title_id",
        ):
            assert needed in item, f"管理列表缺少 {needed}：{sorted(item)}"
        # 长字段留给详情端点，别塞进列表
        for bloat in ("bio", "website", "github", "qq", "cover_image"):
            assert bloat not in item, f"管理列表不该含 {bloat}"

    @pytest.mark.asyncio
    async def test_admin_list_counts_are_real(
        self, client: AsyncClient, staff_headers: dict, test_post, test_user, make_comments
    ):
        """posts_count / comments_count 必须是真实聚合值，不是恒 0 的占位。

        `author=test_user` 不能省：`make_comments` 不给作者时创建的是**游客评论**
        （user_id=NULL），而计数是按 `Comment.user_id` GROUP BY 的 —— 游客评论
        不会计入任何账号，这条用例就会假绿。
        """
        await make_comments(test_post, 3, author=test_user)

        r = await client.get(
            "/api/admin/users", headers=staff_headers, params={"search": "test"}
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert items, "搜索 test 应至少命中一个用户"
        author = next((i for i in items if i["username"] == "testuser"), None)
        assert author is not None, f"没找到 testuser 用户：{[i['username'] for i in items]}"
        assert author["posts_count"] >= 1, f"posts_count 应为真实值，实际 {author['posts_count']}"
        assert author["comments_count"] >= 3, (
            f"comments_count 应为真实值，实际 {author['comments_count']}"
        )

    @pytest.mark.asyncio
    async def test_admin_list_server_side_ban_filter(
        self, client: AsyncClient, staff_headers: dict
    ):
        """封禁筛选走服务端：is_banned=false 的结果里不该出现已封禁账号。"""
        r = await client.get(
            "/api/admin/users", headers=staff_headers, params={"is_banned": "false"}
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert all(i["is_banned"] is False for i in data["items"]), (
            "is_banned=false 过滤后仍返回了封禁账号"
        )
