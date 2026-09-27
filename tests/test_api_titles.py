"""用户称号 API 测试：CRUD 形状 + 图标取值约束（存储型 XSS 封堵）+ 名称查重口径

覆盖 `backend/api/title.py`：
- GET/POST `/api/admin/titles`、PATCH/DELETE `/api/admin/titles/{id}`、
  POST `/titles/assign` 与 GET/DELETE `/users/{id}/title`（戴/摘是两个独立端点）。
- `color` 必须是十六进制、且不能显式置 null（列 NOT NULL，脏值走到 flush 就是 500）。
- 删除称号前批量摘除持有者的 `title_id`，不留孤儿外键。
- `icon` 只允许"预设 ID / emoji"这类纯文本：含尖括号的标记必须 422 且不得落库。
  前台 `TitleIconSvg.vue` 过去会把以 `<` 开头的值直接 v-html 渲染到访客页面，
  写入侧的 pattern 才是唯一可靠的闸门（渲染侧同时已删除该分支）。
- 名称查重改读 Python 侧多语言值并做精确匹配：旧的
  `CAST(name AS CHAR) LIKE '%名称%'` 在 SQLite 下对中文恒不命中（JSON 里是 `\\uXXXX`），
  还会把 "VIP" 误判为 "VIP Pro" 的重复；且 PATCH 改名完全不查重。
- staff 权限门禁
- 称号内容/归属变化后必须失效"把称号显示出去"的缓存（文章详情 author.title 段 +
  公开资料缓存），详见文件末尾 `TestTitleCacheInvalidation`
"""

import pytest
from httpx import AsyncClient

from backend.core.cache import cache, make_cache_key
from backend.models.blog import Post
from backend.models.user import User

MARKUP_ICON = '<svg onload="alert(1)"><circle r="9"/></svg>'


async def _create(client: AsyncClient, headers: dict, payload: dict):
    return await client.post("/api/admin/titles", headers=headers, json=payload)


@pytest.mark.asyncio
async def test_create_title_accepts_preset_id_and_emoji(client: AsyncClient, staff_headers: dict):
    """预设 ID 与 emoji 是合法取值，创建后原样回显（含 users_count=0）"""
    for idx, icon in enumerate(("crown", "⭐"), start=1):
        r = await _create(
            client,
            staff_headers,
            {"name": {"zh": f"合法称号{idx}", "en": f"Valid Title {idx}"}, "icon": icon},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["icon"] == icon
        assert data["users_count"] == 0


@pytest.mark.asyncio
async def test_create_title_rejects_markup_icon_and_stores_nothing(
    client: AsyncClient, staff_headers: dict
):
    """标记语言必须 422 拒之门外，且不能被写进库（否则每次渲染都成 XSS 载体）"""
    r = await _create(
        client,
        staff_headers,
        {"name": {"zh": "恶意称号", "en": "Evil Title"}, "icon": MARKUP_ICON},
    )
    assert r.status_code == 422, f"标记型 icon 被接受：{r.status_code} {r.text[:200]}"

    listing = await client.get("/api/admin/titles", headers=staff_headers)
    assert listing.status_code == 200, listing.text
    assert all(t["icon"] != MARKUP_ICON for t in listing.json()), "被拒的图标仍然落库了"


@pytest.mark.asyncio
async def test_update_title_rejects_markup_icon(client: AsyncClient, staff_headers: dict):
    """PATCH 与 POST 用同一套约束，不能只在创建侧设防"""
    created = await _create(
        client,
        staff_headers,
        {"name": {"zh": "待改称号", "en": "Mutable Title"}, "icon": "star"},
    )
    assert created.status_code == 200, created.text
    title_id = created.json()["id"]

    r = await client.patch(
        f"/api/admin/titles/{title_id}",
        headers=staff_headers,
        json={"icon": MARKUP_ICON},
    )
    assert r.status_code == 422, r.text

    after = await client.get(f"/api/admin/titles/{title_id}", headers=staff_headers)
    assert after.status_code == 200, after.text
    assert after.json()["icon"] == "star", "校验失败却把脏值写进了已有记录"


@pytest.mark.asyncio
async def test_create_title_rejects_oversized_icon(client: AsyncClient, staff_headers: dict):
    """50 字符上限：emoji 与预设 ID 远短于此，超长只可能是被塞进来的片段"""
    r = await _create(
        client,
        staff_headers,
        {"name": {"zh": "超长图标称号", "en": "Long Icon Title"}, "icon": "x" * 51},
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_create_title_rejects_duplicate_name(client: AsyncClient, staff_headers: dict):
    """重名走业务 400（与 Pydantic 的 422 区分：前者是冲突，后者是格式非法）

    旧实现用 `CAST(name AS CHAR) LIKE '%名称%'` 判重：SQLite 里 JSON 中文名被存成
    `\\uXXXX` 转义，中文称号永远不判重；换成 Python 侧精确匹配后此路才真正生效。
    """
    payload = {"name": {"zh": "重复名称", "en": "Duplicated Title"}}
    first = await _create(client, staff_headers, payload)
    assert first.status_code == 200, first.text
    second = await _create(client, staff_headers, payload)
    assert second.status_code == 400, second.text
    assert "称号名称已存在" in second.text

    # 只换个语言命中也算重复（多语言列任一值相同即冲突）
    partial = await _create(client, staff_headers, {"name": {"ja": "重复名称"}})
    assert partial.status_code == 400, partial.text


@pytest.mark.asyncio
async def test_duplicate_name_check_is_exact_not_substring(
    client: AsyncClient, staff_headers: dict
):
    """`VIP` 不该因为已有 `VIP Pro` 就被判为重复（旧 LIKE %..% 的假阳性）"""
    assert (await _create(client, staff_headers, {"name": {"en": "VIP Pro"}})).status_code == 200
    r = await _create(client, staff_headers, {"name": {"en": "VIP"}})
    assert r.status_code == 200, f"子串被误判为重复：{r.status_code} {r.text[:160]}"


@pytest.mark.asyncio
async def test_rename_title_into_existing_name_is_rejected(
    client: AsyncClient, staff_headers: dict
):
    """改名同样查重：不能把 B 称号改成 A 的名字（旧实现只在创建侧设防）"""
    a = await _create(client, staff_headers, {"name": {"zh": "既有称号", "en": "Existing"}})
    b = await _create(client, staff_headers, {"name": {"zh": "另一个称号", "en": "Another"}})
    assert a.status_code == 200 and b.status_code == 200, (a.text, b.text)

    r = await client.patch(
        f"/api/admin/titles/{b.json()['id']}",
        headers=staff_headers,
        json={"name": {"zh": "既有称号", "en": "Existing"}},
    )
    assert r.status_code == 400, r.text

    # 原名不动、只改颜色的 PATCH 必须照常通过（exclude_unset 语义不能被查重误伤）
    ok = await client.patch(
        f"/api/admin/titles/{a.json()['id']}",
        headers=staff_headers,
        json={"color": "#123456"},
    )
    assert ok.status_code == 200, ok.text


@pytest.mark.asyncio
async def test_create_title_rejects_blank_name(client: AsyncClient, staff_headers: dict):
    """全空的名字（`{"zh": "  "}`）既不是合法展示内容，也不该成为可分配的称号"""
    r = await _create(client, staff_headers, {"name": {"zh": "   "}})
    assert r.status_code == 422, r.text
    assert "称号名称不能为空" in r.text


@pytest.mark.asyncio
async def test_color_is_not_optional_on_write(client: AsyncClient, staff_headers: dict):
    """`color` 是 NOT NULL 列：写入侧只接受字符串，`null` 必须在 422 就被挡住，
    不能一路走到 flush 变 500（前端"清空取色器"就会发出这种请求）。
    """
    r = await _create(
        client,
        staff_headers,
        {"name": {"zh": "无色称号", "en": "No Color Title"}, "color": None},
    )
    assert r.status_code == 422, f"color=null 未被拒绝：{r.status_code} {r.text[:200]}"


@pytest.mark.asyncio
async def test_delete_title_returns_204(client: AsyncClient, staff_headers: dict):
    created = await _create(
        client,
        staff_headers,
        {"name": {"zh": "将被删除", "en": "Doomed Title"}, "icon": "zap"},
    )
    title_id = created.json()["id"]

    r = await client.delete(f"/api/admin/titles/{title_id}", headers=staff_headers)
    assert r.status_code == 204, r.text

    after = await client.get(f"/api/admin/titles/{title_id}", headers=staff_headers)
    assert after.status_code == 404, after.text


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/admin/titles"),
        ("POST", "/api/admin/titles"),
        ("PATCH", "/api/admin/titles/1"),
        ("DELETE", "/api/admin/titles/1"),
    ],
)
@pytest.mark.asyncio
async def test_title_endpoints_require_auth(client: AsyncClient, method: str, path: str):
    r = await client.request(method, path, json={"name": {"zh": "未授权"}})
    assert r.status_code in (401, 403), f"{method} {path} 未鉴权却返回 {r.status_code}"


@pytest.mark.asyncio
async def test_subscriber_cannot_manage_titles(client: AsyncClient, subscriber_headers: dict):
    r = await _create(
        client,
        subscriber_headers,
        {"name": {"zh": "越权称号", "en": "Escalated Title"}},
    )
    assert r.status_code in (401, 403), f"普通用户却能创建称号：{r.status_code} {r.text[:200]}"


@pytest.mark.asyncio
async def test_update_title_rejects_explicit_null_color(client: AsyncClient, staff_headers: dict):
    """`color` 是 NOT NULL 列：PATCH 显式传 null 不能走到 flush 变 500。"""
    created = await _create(client, staff_headers, {"name": {"zh": "夜航"}, "color": "#8B5CF6"})
    title_id = created.json()["id"]

    r = await client.patch(
        f"/api/admin/titles/{title_id}", json={"color": None}, headers=staff_headers
    )
    assert r.status_code == 422, f"null 颜色未被拒绝：{r.status_code} {r.text[:200]}"

    after = await client.get(f"/api/admin/titles/{title_id}", headers=staff_headers)
    assert after.json()["color"] == "#8B5CF6"


@pytest.mark.asyncio
async def test_color_must_be_hex(client: AsyncClient, staff_headers: dict):
    """color 写进 String(20) 的十六进制列：自由文本会让徽章不可见、超长还会撞列宽。"""
    for bad in ("red", "#12345", "background:url(//evil)", "#3b82f6aabbccdd0099"):
        r = await _create(
            client,
            staff_headers,
            {"name": {"zh": f"坏色{bad[:6]}"}, "color": bad},
        )
        assert r.status_code == 422, f"非法颜色被接受：{bad!r} -> {r.status_code}"


@pytest.mark.asyncio
async def test_assign_and_remove_user_title(
    client: AsyncClient,
    staff_headers: dict,
    test_user: User,
):
    """戴/摘称号是彼此独立的两个端点（前端曾把摘称号短路成假成功）。"""
    created = await _create(client, staff_headers, {"name": {"zh": "夜航员"}, "icon": "moon"})
    title_id = created.json()["id"]

    assigned = await client.post(
        "/api/admin/titles/assign",
        json={"user_id": test_user.id, "title_id": title_id},
        headers=staff_headers,
    )
    assert assigned.status_code == 200, assigned.text
    current = await client.get(f"/api/admin/users/{test_user.id}/title", headers=staff_headers)
    assert current.json()["title"]["id"] == title_id

    removed = await client.delete(
        f"/api/admin/users/{test_user.id}/title",
        headers=staff_headers,
    )
    assert removed.status_code == 200, removed.text
    after = await client.get(f"/api/admin/users/{test_user.id}/title", headers=staff_headers)
    assert after.json()["title"] is None


@pytest.mark.asyncio
async def test_delete_title_detaches_holders(
    client: AsyncClient, staff_headers: dict, test_user: User
):
    """删称号不能留下指向已删行的 title_id 孤儿（前台徽章会读到 None）。"""
    created = await _create(client, staff_headers, {"name": {"zh": "退役称号"}})
    title_id = created.json()["id"]
    await client.post(
        "/api/admin/titles/assign",
        json={"user_id": test_user.id, "title_id": title_id},
        headers=staff_headers,
    )

    deleted = await client.delete(f"/api/admin/titles/{title_id}", headers=staff_headers)
    assert deleted.status_code == 204

    current = await client.get(f"/api/admin/users/{test_user.id}/title", headers=staff_headers)
    assert current.json()["title"] is None


async def _seed_stale_post_caches(slug: str) -> tuple[str, str]:
    """塞入"旧称号还嵌在里面"的文章缓存，返回 (详情键, 列表键)。"""
    detail_key = make_cache_key("post", slug, "zh")
    list_key = make_cache_key("posts", "list", "zh")
    await cache.set(detail_key, {"stale": True}, ttl=600)
    await cache.set(list_key, {"stale": True}, ttl=600)
    assert await cache.get(detail_key) is not None
    assert await cache.get(list_key) is not None
    return detail_key, list_key


class TestTitleCacheInvalidation:
    """称号写操作必须连带失效"把称号显示出去"的缓存。

    `blog._build_author_data` 会把 title 的 id/name/icon/color/description 整段嵌进
    文章详情响应，而详情缓存键是 `post:{slug}:{lang}`——它既不在 `posts` 前缀下，
    也不在 `invalidate_user_cache` 的三族键里。旧实现四个写端点一次缓存都没清：
    后台把称号改名/换色，持有者的每篇文章在 600s TTL 内继续挂旧徽章；
    删掉称号则会让访客页持续渲染一个数据库里已不存在的"幽灵称号"。
    """

    async def _grant(self, client: AsyncClient, staff_headers: dict, user_id: int, icon: str):
        created = await _create(
            client, staff_headers, {"name": {"zh": f"缓存称号{icon}"}, "icon": icon}
        )
        assert created.status_code == 200, created.text
        title_id = created.json()["id"]
        assigned = await client.post(
            "/api/admin/titles/assign",
            json={"user_id": user_id, "title_id": title_id},
            headers=staff_headers,
        )
        assert assigned.status_code == 200, assigned.text
        return title_id

    @pytest.mark.asyncio
    async def test_granting_a_title_clears_new_holders_post_caches(
        self,
        client: AsyncClient,
        staff_headers: dict,
        test_post: Post,
    ):
        created = await _create(client, staff_headers, {"name": {"zh": "新授予"}, "icon": "star"})
        title_id = created.json()["id"]

        detail_key, list_key = await _seed_stale_post_caches(test_post.slug)
        r = await client.post(
            "/api/admin/titles/assign",
            json={"user_id": test_post.author_id, "title_id": title_id},
            headers=staff_headers,
        )
        assert r.status_code == 200, r.text

        assert await cache.get(detail_key) is None, "授予称号后作者文章详情缓存仍是旧徽章"
        assert await cache.get(list_key) is None, "授予称号后列表/RSS 缓存未失效"

    @pytest.mark.asyncio
    async def test_removing_a_title_clears_holders_post_caches(
        self,
        client: AsyncClient,
        staff_headers: dict,
        test_post: Post,
    ):
        await self._grant(client, staff_headers, test_post.author_id, "moon")
        detail_key, list_key = await _seed_stale_post_caches(test_post.slug)

        r = await client.delete(
            f"/api/admin/users/{test_post.author_id}/title",
            headers=staff_headers,
        )
        assert r.status_code == 200, r.text

        assert await cache.get(detail_key) is None, "撤销称号后详情缓存仍显示已摘掉的徽章"
        assert await cache.get(list_key) is None

    @pytest.mark.asyncio
    async def test_recoloring_a_title_clears_holders_post_caches(
        self,
        client: AsyncClient,
        staff_headers: dict,
        test_post: Post,
    ):
        title_id = await self._grant(client, staff_headers, test_post.author_id, "crown")
        detail_key, list_key = await _seed_stale_post_caches(test_post.slug)

        r = await client.patch(
            f"/api/admin/titles/{title_id}",
            json={"color": "#FF6600"},
            headers=staff_headers,
        )
        assert r.status_code == 200, r.text

        assert await cache.get(detail_key) is None, "改色后作者文章仍缓存旧颜色"
        assert await cache.get(list_key) is None

    @pytest.mark.asyncio
    async def test_deleting_a_title_clears_holders_post_caches(
        self,
        client: AsyncClient,
        staff_headers: dict,
        test_post: Post,
    ):
        title_id = await self._grant(client, staff_headers, test_post.author_id, "zap")
        detail_key, list_key = await _seed_stale_post_caches(test_post.slug)

        r = await client.delete(f"/api/admin/titles/{title_id}", headers=staff_headers)
        assert r.status_code == 204, r.text

        assert await cache.get(detail_key) is None, "删除称号后详情缓存仍在渲染已删称号"
        assert await cache.get(list_key) is None

    @pytest.mark.asyncio
    async def test_title_without_holders_keeps_post_caches(
        self, client: AsyncClient, staff_headers: dict, test_post: Post
    ):
        """没人持有的称号改色，不该顺手清掉全站文章缓存。

        失效范围必须按"受影响 slug 集合"收敛——否则任何一个称号编辑都退化成
        全站缓存雪崩，第一页起的所有文章全部回源。
        """
        created = await _create(client, staff_headers, {"name": {"zh": "无人持有"}})
        title_id = created.json()["id"]

        detail_key, list_key = await _seed_stale_post_caches(test_post.slug)
        r = await client.patch(
            f"/api/admin/titles/{title_id}",
            json={"color": "#00FF88"},
            headers=staff_headers,
        )
        assert r.status_code == 200, r.text

        assert await cache.get(detail_key) is not None, "无关称号编辑不应清详情缓存"
        assert await cache.get(list_key) is not None, "无关称号编辑不应清列表缓存"
