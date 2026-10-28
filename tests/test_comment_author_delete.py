"""作者删除自己评论（``DELETE /api/comments/{id}``）的两端与强制点回归（批次 #38）。

这条口此前整块不存在：用户发出去的评论只能由管理员删，前台 CommentItem 只有点赞/回复。
API_COVERAGE 里 ``DELETE /comments/{id}`` 长期挂在未消费清单，判词写的是"用户删评论缺口"。
这一批补的就是那一格，覆盖面按"少了任何一条会出现哪一类缺陷"来定：

1. 路由与鉴权：口存在、动词是 DELETE、匿名 401、CSRF 与其它 Bearer 写口同轨
   （漏挂 require_csrf 等于给跨站请求开了一扇"把本人评论连点删光"的门）。
2. 归属判据进 SELECT 的 WHERE：别人的评论与不存在的 id 回同一个 404。专门钉三条——
   他人 404（不是 403：主键连续自增时 403 在替攻击者数"这条存在"）、
   staff 也一样 404（这条口不开特权后门，管理员删别人的评论走 admin 口）、
   游客评论（user_id 为 NULL）任何账号都删不掉。
3. 与管理员单删同构：先落回收站快照再删原行，钩子照发、缓存照清。少任何一环的
   表现分别是"用户删掉的评论人间蒸发（回收站的评论这一类永远缺）"、
   "插件/Webhook 听不到删除"、"文章评论计数与列表页 SSR 里的数字在 TTL 内仍是旧的"。
4. 投递面：删完立刻从公开评论列表口消失，且它名下已存在的回复不丢。
5. 前端真实调用点：封装存在但没人点是本仓反复出现过的假阳性，所以逐处读源文本判，
   并判"归属用的是后端 user_id 而不是 author.id 的展示兜底"、"删除图标走 SSR 安全的
   单源图标模块而不是 `@lucide/vue`"（后者在服务端渲染成空注释节点 = hydration mismatch）。
6. 四语文案：新增四个键四语齐全（缺语等于英文界面冒出中文）。
"""

import json
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.core.plugin_bus import bus
from backend.models.blog import Comment
from backend.models.log import TrashItem

COMMENTS = "/api/comments"
POST_COMMENTS = "/api/blog/posts"


async def _mk_comment(db, *, post_id: int, user_id: int | None, content: str, **extra) -> Comment:
    comment = Comment(
        post_id=post_id,
        user_id=user_id,
        parent_id=extra.pop("parent_id", None),
        author_name=extra.pop("author_name", "Guest" if user_id is None else "Owner"),
        content=content,
        status="approved",
        active=True,
        likes_count=0,
        is_pinned=False,
        **extra,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


async def _reload_comment(db, comment_id: int) -> Comment | None:
    """接口回 200 之后到库里读回这一行。

    只 `expire_all()`，**不 rollback**：`client` fixture 把 `get_db` 覆盖成同一个
    `db_session`，handler 的 `delete + flush` 就落在这条会话的事务里——回滚等于把这次
    删除自己撤销掉，任何"删完读不到"的断言都会变成假失败。
    读只用 SELECT：``session.get()`` 在 AsyncSession 上是同步入口，属性一失效就 MissingGreenlet。
    """
    db.expire_all()
    return (await db.execute(select(Comment).where(Comment.id == comment_id))).scalar_one_or_none()


def _flatten_contents(rows: list[dict]) -> list[str]:
    """评论树摊平成正文列表（回复在 ``replies`` 里，不断一层就会漏判）。"""
    out: list[str] = []
    for row in rows:
        out.append(row["content"])
        out.extend(_flatten_contents(row.get("replies") or []))
    return out


async def _public_comment_contents(client: AsyncClient, post_id: int) -> list[str]:
    resp = await client.get(f"{POST_COMMENTS}/{post_id}/comments")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    rows = body["data"] if isinstance(body, dict) else body
    return _flatten_contents(rows)


@pytest.fixture
def recorded_deleted():
    """在生产总线上挂 comment.deleted 的临时监听，记录 (事件名, 评论 id)。

    刻意不 mock ``do_action``：传法（位置参数 vs 关键字）与 webhook 监听侧的解析口径
    必须一起被验，mock 会把这两者解耦成"看起来发了"。
    """
    events: list[tuple[str, object]] = []

    async def handler(*args, **kwargs):
        entity = kwargs.get("comment") if "comment" in kwargs else (args[0] if args else None)
        events.append(("comment.deleted", getattr(entity, "id", entity)))

    bus.add_action("comment.deleted", handler)
    try:
        yield events
    finally:
        bus.remove_action("comment.deleted", handler)


class TestRouteIsWired:
    def test_openapi_declares_delete_on_comments_item(self):
        from backend.main import app

        paths = app.openapi()["paths"]
        item = paths.get(f"{COMMENTS}/{{comment_id}}")
        assert item is not None, "OpenAPI 里没有 /api/comments/{comment_id} 这条路径"
        assert "delete" in item, "该路径上没有 DELETE 动词（前端封装打的是 DELETE）"
        delete_op = item["delete"]
        assert delete_op.get("responses"), "响应体未声明——API 文档基线会把这条算成缺口"

    @pytest.mark.asyncio
    async def test_anonymous_is_rejected(
        self, client: AsyncClient, db_session, test_post, test_user
    ):
        comment = await _mk_comment(
            db_session, post_id=test_post.id, user_id=test_user.id, content="匿名删不掉"
        )
        resp = await client.delete(f"{COMMENTS}/{comment.id}")
        assert resp.status_code == 401, resp.text
        assert await _reload_comment(db_session, comment.id) is not None

    @pytest.mark.asyncio
    async def test_cross_origin_bearer_request_is_blocked(
        self, client: AsyncClient, db_session, test_post, auth_headers, test_user
    ):
        """CSRF 与同模块写口同轨：Origin 不在白名单的 Bearer 写请求一律 403。"""
        comment = await _mk_comment(
            db_session, post_id=test_post.id, user_id=test_user.id, content="跨站删不掉"
        )
        resp = await client.delete(
            f"{COMMENTS}/{comment.id}",
            headers={**auth_headers, "Origin": "http://evil-csrf.example"},
        )
        assert resp.status_code == 403, resp.text
        assert "CSRF_CHECK_FAILED" in resp.text
        assert await _reload_comment(db_session, comment.id) is not None


class TestOwnershipGate:
    @pytest.mark.asyncio
    async def test_author_can_delete_own_comment(
        self, client: AsyncClient, db_session, test_post, test_user, auth_headers
    ):
        comment = await _mk_comment(
            db_session, post_id=test_post.id, user_id=test_user.id, content="我自己的评论"
        )
        resp = await client.delete(f"{COMMENTS}/{comment.id}", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert await _reload_comment(db_session, comment.id) is None

    @pytest.mark.asyncio
    async def test_another_users_comment_is_404_not_403(
        self,
        client: AsyncClient,
        db_session,
        test_post,
        test_user,
        subscriber_user,
        subscriber_headers,
    ):
        """两种"删不掉"必须是同一个 404：403 等于承认这条评论存在，可枚举全站评论 id。"""
        mine = await _mk_comment(
            db_session, post_id=test_post.id, user_id=test_user.id, content="别人的评论"
        )
        resp = await client.delete(f"{COMMENTS}/{mine.id}", headers=subscriber_headers)
        assert resp.status_code == 404, resp.text
        body = resp.json()
        payload = body.get("data", body)
        assert payload.get("error_code") == "COMMENT_NOT_FOUND"
        assert await _reload_comment(db_session, mine.id) is not None

    @pytest.mark.asyncio
    async def test_staff_gets_404_for_others_comments(
        self,
        client: AsyncClient,
        db_session,
        test_post,
        test_user,
        staff_user,
        staff_headers,
    ):
        """这条口不开特权后门：管理员删别人的评论走 DELETE /api/admin/comments/{id}。"""
        target = await _mk_comment(
            db_session, post_id=test_post.id, user_id=test_user.id, content="staff 不该在这条口删"
        )
        resp = await client.delete(f"{COMMENTS}/{target.id}", headers=staff_headers)
        assert resp.status_code == 404, resp.text
        assert await _reload_comment(db_session, target.id) is not None

    @pytest.mark.asyncio
    async def test_guest_comment_is_not_deletable_by_anyone(
        self, client: AsyncClient, db_session, test_post, test_user, auth_headers
    ):
        """游客行 user_id 为 NULL：任何登录账号都匹配不上，只有管理员能删。"""
        guest = await _mk_comment(
            db_session,
            post_id=test_post.id,
            user_id=None,
            content="游客评论",
            author_name="Visitor",
            author_email="visitor@example.com",
        )
        resp = await client.delete(f"{COMMENTS}/{guest.id}", headers=auth_headers)
        assert resp.status_code == 404, resp.text
        assert await _reload_comment(db_session, guest.id) is not None

    @pytest.mark.asyncio
    async def test_missing_id_is_404(self, client: AsyncClient, auth_headers):
        resp = await client.delete(f"{COMMENTS}/999999", headers=auth_headers)
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_second_delete_is_404(
        self, client: AsyncClient, db_session, test_post, test_user, auth_headers
    ):
        """删除非幂等：第二次落到"不存在"，而不是 500 或 200 假装成功。"""
        comment = await _mk_comment(
            db_session, post_id=test_post.id, user_id=test_user.id, content="删两次"
        )
        first = await client.delete(f"{COMMENTS}/{comment.id}", headers=auth_headers)
        assert first.status_code == 200, first.text
        second = await client.delete(f"{COMMENTS}/{comment.id}", headers=auth_headers)
        assert second.status_code == 404, second.text

    @pytest.mark.asyncio
    async def test_id_collision_with_comment_pk_does_not_grant_access(
        self,
        client: AsyncClient,
        db_session,
        test_post,
        test_user,
        subscriber_user,
        subscriber_headers,
    ):
        """归属判据是"这一行的 user_id 等于我"，不是"我的 id 能凑上某个号"。

        前台 author.id 有个 `?? 评论 id` 的展示兜底（见 normalizeComment），
        所以库里存在"user_id=NULL 且评论 id 恰好等于某个用户 id"的游客行时，
        服务端仍必须拒掉——本例直接构造这种同号形态。
        """
        guest = await _mk_comment(
            db_session, post_id=test_post.id, user_id=None, content="游客行", author_name="V"
        )
        resp = await client.delete(f"{COMMENTS}/{guest.id}", headers=subscriber_headers)
        assert resp.status_code == 404, resp.text


class TestSameShapeAsAdminDelete:
    @pytest.mark.asyncio
    async def test_snapshot_lands_in_trash_with_full_payload(
        self, client: AsyncClient, db_session, test_post, test_user, auth_headers
    ):
        comment = await _mk_comment(
            db_session,
            post_id=test_post.id,
            user_id=test_user.id,
            content="进回收站的那条",
            qq="10001",
            github="choyeon",
        )
        # 号必须在 delete 之前抄下来：这一行的实例随后会随会话失效，
        # 在异步会话上再访问它的属性会走同步懒加载 → MissingGreenlet。
        comment_id = comment.id
        author_id = test_user.id
        from backend.services.trash import comment_trash_payload

        payload_keys = set(comment_trash_payload(comment))
        resp = await client.delete(f"{COMMENTS}/{comment_id}", headers=auth_headers)
        assert resp.status_code == 200, resp.text

        item = (
            await db_session.execute(
                select(TrashItem).where(
                    TrashItem.resource_type == "comment",
                    TrashItem.resource_id == comment_id,
                )
            )
        ).scalar_one()
        assert item.deleted_by_id == author_id
        assert item.auto_delete_at is not None, "快照没有到期时间＝回收站的 30 天承诺落空"
        data = json.loads(item.resource_data)
        assert data["content"] == "进回收站的那条"
        assert data["user_id"] == author_id
        assert data["post_id"] == test_post.id
        # 恢复分支按整组键重建 NOT NULL 列，少一个键就是"删了恢复不了"
        assert set(data) == payload_keys
        assert data["qq"] == "10001" and data["github"] == "choyeon"

    @pytest.mark.asyncio
    async def test_deleted_event_is_emitted_on_production_bus(
        self,
        client: AsyncClient,
        db_session,
        test_post,
        test_user,
        auth_headers,
        recorded_deleted,
    ):
        comment = await _mk_comment(
            db_session, post_id=test_post.id, user_id=test_user.id, content="钩子要听到"
        )
        resp = await client.delete(f"{COMMENTS}/{comment.id}", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert ("comment.deleted", comment.id) in recorded_deleted

    def test_deleted_event_is_a_registered_webhook_event(self):
        """事件名必须已在唯一清单里（后台订阅 UI 与 webhook 投递都读它）。"""
        from backend.api.webhook import WEBHOOK_EVENTS

        assert "comment.deleted" in WEBHOOK_EVENTS

    @pytest.mark.asyncio
    async def test_post_caches_and_frontend_page_are_purged(
        self,
        client: AsyncClient,
        db_session,
        test_post,
        test_user,
        auth_headers,
        monkeypatch,
    ):
        """可见评论集合变了：文章详情/列表缓存与前台页面缓存都要清。

        评论树由客户端拉取，但首页与列表页 SSR 的 HTML 里烘着评论计数——只清后端响应缓存，
        Nitro 的 swr 窗口内访客仍看到旧的评论数。
        """
        invalidated: list[list[int]] = []
        purged: list[str] = []

        async def fake_invalidate(_db, post_ids):
            invalidated.append(list(post_ids))

        def fake_purge(reason: str = "", *args, **kwargs):
            purged.append(reason)

        monkeypatch.setattr("backend.api.comments.invalidate_post_caches_by_ids", fake_invalidate)
        monkeypatch.setattr("backend.api.comments.purge_frontend_page_cache", fake_purge)

        comment = await _mk_comment(
            db_session, post_id=test_post.id, user_id=test_user.id, content="要清缓存"
        )
        resp = await client.delete(f"{COMMENTS}/{comment.id}", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert invalidated == [[test_post.id]], (
            "文章评论计数缓存未失效（列表仍带着旧 comments_count）"
        )
        assert len(purged) == 1, "前台页面缓存清除口没被调用（漏调＝访客面 TTL 内旧样）"

    @pytest.mark.asyncio
    async def test_failed_lookup_clears_nothing(
        self,
        client: AsyncClient,
        db_session,
        test_post,
        test_user,
        subscriber_user,
        subscriber_headers,
        monkeypatch,
    ):
        """404 路径不得顺带清缓存：否则任何人拿别人的评论 id 就能反复打清缓存口。"""
        calls: list[list[int]] = []

        async def fake_invalidate(_db, post_ids):
            calls.append(list(post_ids))

        monkeypatch.setattr("backend.api.comments.invalidate_post_caches_by_ids", fake_invalidate)

        mine = await _mk_comment(
            db_session, post_id=test_post.id, user_id=test_user.id, content="别人的"
        )
        resp = await client.delete(f"{COMMENTS}/{mine.id}", headers=subscriber_headers)
        assert resp.status_code == 404, resp.text
        assert calls == []


class TestReadSideDropsIt:
    @pytest.mark.asyncio
    async def test_public_comment_list_no_longer_contains_it(
        self, client: AsyncClient, db_session, test_post, test_user, auth_headers
    ):
        await _mk_comment(
            db_session, post_id=test_post.id, user_id=test_user.id, content="PX38-mine"
        )
        await _mk_comment(
            db_session,
            post_id=test_post.id,
            user_id=None,
            content="PX38-guest",
            author_name="V",
            author_email="v@example.com",
        )
        before = await _public_comment_contents(client, test_post.id)
        assert "PX38-mine" in before

        target = (
            await db_session.execute(select(Comment).where(Comment.content == "PX38-mine"))
        ).scalar_one()
        resp = await client.delete(f"{COMMENTS}/{target.id}", headers=auth_headers)
        assert resp.status_code == 200, resp.text

        after = await _public_comment_contents(client, test_post.id)
        assert "PX38-mine" not in after, "删掉的评论仍在公开列表里"
        assert "PX38-guest" in after, "误删了他人的行"

    @pytest.mark.asyncio
    async def test_replies_survive_their_parent(
        self, client: AsyncClient, db_session, test_post, test_user, auth_headers
    ):
        """父评论被作者删掉时回复不丢（外键 ON DELETE SET NULL 提为根评论）。"""
        parent = await _mk_comment(
            db_session, post_id=test_post.id, user_id=test_user.id, content="PX38-parent"
        )
        child = await _mk_comment(
            db_session,
            post_id=test_post.id,
            user_id=test_user.id,
            content="PX38-child",
            parent_id=parent.id,
        )
        resp = await client.delete(f"{COMMENTS}/{parent.id}", headers=auth_headers)
        assert resp.status_code == 200, resp.text

        kept = await _reload_comment(db_session, child.id)
        assert kept is not None, "删父评论把回复一起带走了"
        assert kept.parent_id is None, "回复仍指向已删除的父评论（悬挂外键）"


class TestFrontendHasARealControlPoint:
    """前端调用点全部读源文本判：本仓出过"封装存在但没人点"的假阳性。"""

    manage = Path("frontend/composables/useComments.ts")
    item = Path("frontend/components/CommentItem.vue")
    page = Path("frontend/pages/posts/[slug].vue")

    def _read(self, p: Path) -> str:
        assert p.exists(), f"{p} 不存在"
        return p.read_text(encoding="utf-8")

    def test_wrapper_hits_delete_on_comments_item_and_is_exported(self):
        text = self._read(self.manage)
        block = text[text.index("const deleteComment") :]
        assert "apiFetch" in block[:400]
        assert "/comments/${id}" in block
        assert "method: 'DELETE'" in block
        assert "deleteComment," in text[text.index("  return {") :], "封装没导出给调用方"

    def test_item_renders_entry_only_when_allowed(self):
        text = self._read(self.item)
        assert "canDelete" in text and "can-delete" not in text.split("<script")[0]
        head = text.split("<script")[0]
        assert 'v-if="canDelete"' in head
        assert "$emit('delete', comment.id)" in head
        assert "t('comment.delete')" in head
        assert "deleting: false" in text, "删除进行中的锁默认为未锁"

    def test_item_uses_the_ssr_safe_icon_module(self):
        """评论组件在文章详情页的 SSR HTML 里渲染。

        `lib/lucide-svg-icons.ts` 的文件头写明了本仓的坑：`@lucide/vue` 在 Nuxt SSR 下
        服务端渲染成空注释节点、客户端渲染成真 svg → hydration mismatch + 重建级联报错。
        后台 SPA 组件用 `@lucide/vue` 没问题，前台 SSR 组件不行。
        """
        text = self._read(self.item)
        assert "@lucide/vue" not in text, (
            "前台 SSR 组件不得直接引 @lucide/vue（hydration mismatch）"
        )
        script = text.split("<script")[1]
        assert "Trash2" in script
        imports = [line for line in script.splitlines() if "lib/lucide-svg-icons" in line]
        assert imports and "Trash2" in imports[0], "删除图标没和同组件其余图标同处一个 import"
        lib = Path("frontend/lib/lucide-svg-icons.ts").read_text(encoding="utf-8")
        assert "export const Trash2" in lib, "图标没进 SSR 安全的单源图标模块"

    def test_page_computes_ownership_from_backend_user_id(self):
        text = self._read(self.page)
        assert "ownerId: rawId(raw.user_id)" in text
        assert "isOwnComment" in text
        block = text[text.index("const isOwnComment") :]
        block = (
            block[: block.index("\n")]
            if "\n\n" not in block[:200]
            else block[: block.index("\n\n")]
        )
        assert "comment.ownerId" in block
        assert "authStore.user?.id" in block
        assert "author" not in block, "归属判据不能用 author.id（它有 `?? 评论 id` 的展示兜底）"
        assert ':can-delete="isOwnComment(comment)"' in text
        assert '@delete="handleDeleteComment"' in text

    def test_page_removes_row_and_locks_entry(self):
        text = self._read(self.page)
        block = text[text.index("const handleDeleteComment") :]
        block = block[: block.index("\n\n") if "\n\n" in block[:900] else len(block)]
        assert "commentsAPI.deleteComment(commentId)" in block
        assert "deletingCommentId.value = commentId" in block
        assert "comments.value = comments.value.filter" in block
        assert "window.confirm" in block
        assert "toast.success" in block
        assert not any(token in block for token in ["toast.error", "toast.warning"]), (
            "catch 内二次弹错＝双 toast（apiFetch 已统一发）"
        )

    def test_four_locales_carry_the_new_copy(self):
        for loc in ("zh", "en", "ja", "zh_Hant"):
            data = json.loads(Path(f"frontend/i18n/locales/{loc}.json").read_text(encoding="utf-8"))
            comment = data["comment"]
            for key in ("delete", "deleting", "deleteConfirm", "deleted"):
                assert comment.get(key), f"{loc} 缺 comment.{key}"


class TestDocSurface:
    def test_coverage_doc_no_longer_lists_it_as_unconsumed(self):
        """模块叙述行改掉，否则下一次扫描重算前，人读到的还是"这条口没人用"。"""
        text = Path("frontend/docs/API_COVERAGE.md").read_text(encoding="utf-8")
        assert "用户删评论缺口" not in text
