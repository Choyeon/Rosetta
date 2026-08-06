"""
Rosetta 测试配置

提供共享的测试 fixtures 和配置。
"""

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.auth import get_password_hash
from backend.core.database import Base, get_db
from backend.main import create_application
from backend.models.blog import Category, Comment, Post, Tag
from backend.models.core import SiteConfig
from backend.models.user import User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ======================================================================
# Session 级全局 settings patch（对所有测试生效，无论是否使用 client fixture）
#   - 关闭 Redis：避免 Redis 未启动导致所有 cache/ban/reset 相关用例失败
#   - 开启注册：确保注册流程用例不被 403 阻断
#   - 开启评论、RSS：使 CMS 默认功能对单测可用
#   - 关闭敏感词需要审批：避免评论创建后被自动置 pending 导致断言偏移
# ======================================================================
def _apply_global_settings_patches() -> None:
    from backend.core.config import settings as _s

    # Redis 全关
    _s.redis_enabled = False
    # 注册 / 评论 / RSS 开启
    if hasattr(_s, "enable_registration"):
        _s.enable_registration = True
    if hasattr(_s, "enable_comments"):
        _s.enable_comments = True
    if hasattr(_s, "enable_rss_feed"):
        _s.enable_rss_feed = True
    if hasattr(_s, "comment_require_approval"):
        _s.comment_require_approval = False
    # HSTS：测试环境默认关闭，但具体单测需要时会 patch 为 True
    if hasattr(_s, "force_hsts"):
        _s.force_hsts = False
    # cache_v2 后端置空
    try:
        import backend.core.cache_v2 as _cv2
        _cv2.redis_backend = None  # type: ignore[attr-defined]
    except Exception:
        pass
    # cache 模块 backend 置空
    try:
        import backend.core.cache as _cc
        if hasattr(_cc, "backend"):
            _cc.backend = None  # type: ignore[attr-defined]
    except Exception:
        pass


_apply_global_settings_patches()


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """创建测试数据库引擎"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(
    db_session: AsyncSession, monkeypatch
) -> AsyncGenerator[AsyncClient, None]:
    """创建测试客户端

    关键修复：
    1. Monkey-patch oobe_middleware 使用的 is_oobe_complete() 返回 True，避免 OOBE_REQUIRED 503
    2. Monkey-patch MaintenanceMiddleware._is_oobe_complete() 返回 False 直接放行
       （因为它内部使用全局 async_session_maker 连接真实 rosetta.db，绕过了 get_db override）
    3. 确保内存库中的 MAINTENANCE_MODE=false 作为双重保险
    """

    # --- Patch 1: 标记 OOBE 已完成，放行 oobe_middleware 以及 core.py / blog.py 内本地重定义版本 ---
    # --- Patch 1b: 关闭 Redis（测试环境没有 Redis 服务器，防止一切 redis 连接异常） ---
    from backend.core.config import settings as _settings

    monkeypatch.setattr(_settings, "redis_enabled", False)
    # 同时把 cache_v2 里的 redis_backend 设为空，避免初始化
    try:
        import backend.core.cache_v2 as _cv2

        monkeypatch.setattr(_cv2, "redis_backend", None)
    except Exception:
        pass
    import backend.core.deps as _deps_mod

    monkeypatch.setattr(_deps_mod, "is_oobe_complete", lambda: True)

    import backend.api.core as _core_api_mod

    monkeypatch.setattr(_core_api_mod, "is_oobe_complete", lambda: True)

    import backend.api.blog as _blog_api_mod

    monkeypatch.setattr(_blog_api_mod, "is_oobe_complete", lambda: True)

    # --- Patch 2: 让 MaintenanceMiddleware 直接放行，避免查真实 DB ---
    import backend.core.maintenance as _maint_mod

    async def _bypass_maintenance_dispatch(self, request, call_next):
        return await call_next(request)

    monkeypatch.setattr(
        _maint_mod.MaintenanceMiddleware,
        "dispatch",
        _bypass_maintenance_dispatch,
    )

    # --- Patch 3: 禁用速率限制（测试并发触发 429 Too Many Requests） ---
    import backend.core.rate_limit as _rl_mod

    # 清空内存存储，避免跨测试状态共享
    _rl_mod.rate_limiter._memory_store.clear()
    _rl_mod.login_rate_limiter._memory_store.clear()

    # 将 RateLimiter.check_rate_limit 改为始终允许（测试不需要真实限流）
    _orig_check = _rl_mod.rate_limiter.check_rate_limit

    async def _always_allowed_check(key, rule):
        from backend.core.rate_limit import RateLimitResult

        return RateLimitResult(
            allowed=True,
            remaining=rule.requests,
            reset_at=__import__("time").time() + rule.window_seconds,
        )

    monkeypatch.setattr(_rl_mod.rate_limiter, "check_rate_limit", _always_allowed_check)

    # 登录限流：始终未锁定、记录无效果
    async def _never_locked(username):
        return False, None

    async def _noop_record(username, ip_address, success=False):
        return 0, False

    monkeypatch.setattr(_rl_mod.login_rate_limiter, "is_locked", _never_locked)
    monkeypatch.setattr(_rl_mod.login_rate_limiter, "record_attempt", _noop_record)

    # --- 清除缓存（内存缓存是全局单例，跨测试会污染） ---
    import backend.core.cache as _cache_mod

    await _cache_mod.cache.clear()

    # --- 禁用 cache_warmer 的预热（使用全局 async_session_maker 连接空 SQLite :memory:，会污染缓存为默认值） ---
    try:
        from backend.core.cache_warmer import cache_warmer as _cache_warmer

        async def _noop_warmup(task_name: str):
            from backend.core.cache_warmer import WarmupTaskResult, WarmupTaskStatus

            r = WarmupTaskResult(task_name=task_name, status=WarmupTaskStatus.COMPLETED)
            r.items_cached = 0
            return r

        monkeypatch.setattr(_cache_warmer, "warmup_task", _noop_warmup)
        monkeypatch.setattr(_cache_warmer, "warmup_all", lambda *a, **k: asyncio.coroutine(lambda: None)())
    except Exception:
        pass

    # --- 初始化测试 SiteConfig（MAINTENANCE_MODE=false 等） ---
    for key, value in [
        ("MAINTENANCE_MODE", "false"),
        ("SITE_NAME", "Rosetta Test"),
        ("SITE_DESCRIPTION", "Test Instance"),
        ("enable_registration", "true"),
    ]:
        existing = await db_session.get(SiteConfig, key)
        if not existing:
            db_session.add(SiteConfig(key=key, value=value))
    await db_session.commit()

    # --- 立即再次清除缓存，防止任何启动期中间件使用全局 session 写入默认值 ---
    await _cache_mod.cache.clear()

    # --- Override 依赖并创建 app ---
    async def override_get_db():
        yield db_session

    app = create_application()
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """创建测试用户"""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=get_password_hash("Testpass123"),
        nickname="测试用户",
        is_active=True,
        is_staff=False,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """创建管理员用户"""
    user = User(
        username="admin",
        email="admin@example.com",
        password_hash=get_password_hash("Admin123"),
        nickname="管理员",
        is_active=True,
        is_staff=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user: User) -> dict:
    """获取认证头"""
    response = await client.post(
        "/api/users/login",
        json={
            "username": "testuser",
            "password": "Testpass123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    token = data.get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict:
    """获取管理员认证头"""
    response = await client.post(
        "/api/users/login",
        json={
            "username": "admin",
            "password": "Admin123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    token = data.get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_category(db_session: AsyncSession) -> Category:
    """创建测试分类"""
    category = Category(
        name={"zh": "技术", "en": "Technology"},
        slug="technology",
        description={"zh": "技术相关文章", "en": "Technology articles"},
        color="#3B82F6",
        icon="heroicons:code-bracket",
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest_asyncio.fixture
async def test_tag(db_session: AsyncSession) -> Tag:
    """创建测试标签"""
    tag = Tag(
        name={"zh": "Python", "en": "Python"},
        slug="python",
        color="#3776AB",
        is_active=True,
    )
    db_session.add(tag)
    await db_session.commit()
    await db_session.refresh(tag)
    return tag


@pytest_asyncio.fixture
async def test_post(db_session: AsyncSession, test_user: User, test_category: Category) -> Post:
    """创建测试文章"""
    post = Post(
        title={"zh": "测试文章", "en": "Test Post"},
        slug="test-post",
        content={"zh": "这是测试内容", "en": "This is test content"},
        excerpt={"zh": "测试摘要", "en": "Test excerpt"},
        author_id=test_user.id,
        category_id=test_category.id,
        status="published",
        allow_comments=True,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


@pytest_asyncio.fixture
async def test_comment(db_session: AsyncSession, test_post: Post, test_user: User) -> Comment:
    """创建测试评论（符合新 schema 要求的 author_name/status 等字段）"""
    comment = Comment(
        post_id=test_post.id,
        user_id=test_user.id,
        parent_id=None,
        author_name=getattr(test_user, "nickname", None) or test_user.username,
        author_email=getattr(test_user, "email", None),
        author_website=None,
        author_ip=None,
        author_user_agent=None,
        content="这是一条测试评论",
        status="approved",
        active=True,
        likes_count=0,
        is_pinned=False,
    )
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)
    return comment


# ================================= Phase 5 新增 fixtures =================================
# 覆盖 Phase 5 测试用例清单：E-环境 / U-用户 / C-评论 / N-导航 / X-跨模块


@pytest_asyncio.fixture
async def staff_user(db_session: AsyncSession) -> User:
    """员工用户（is_staff=True，非 superuser）：验证 CurrentStaff 权限边界"""
    user = User(
        username="staff",
        email="staff@example.com",
        password_hash=get_password_hash("Staff@123"),
        nickname="员工账号",
        is_active=True,
        is_staff=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def staff_headers(client: AsyncClient, staff_user: User) -> dict:
    """获取员工账号认证头（CurrentStaff 可用但 CurrentSuperUser 拒绝）"""
    response = await client.post(
        "/api/users/login",
        json={"username": "staff", "password": "Staff@123"},
    )
    assert response.status_code == 200, f"staff 登录失败: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def subscriber_user(db_session: AsyncSession) -> User:
    """订阅者用户（全 false）—— 无权访问 /admin/*，用于权限红线测试"""
    user = User(
        username="subscriber",
        email="sub@example.com",
        password_hash=get_password_hash("Sub@1234"),
        nickname="普通订阅者",
        is_active=True,
        is_staff=False,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def subscriber_headers(client: AsyncClient, subscriber_user: User) -> dict:
    """订阅者认证头（用于模拟 No-Go R1 红线突破测试）"""
    response = await client.post(
        "/api/users/login",
        json={"username": "subscriber", "password": "Sub@1234"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def user_with_qq_github(db_session: AsyncSession) -> User:
    """设置了 QQ + GitHub 字段的用户（用于 U-D2 头像解析优先级验证）"""
    user = User(
        username="avatar_tester",
        email="avatar@example.com",
        password_hash=get_password_hash("Av@12345"),
        nickname="头像测试员",
        is_active=True,
        is_staff=False,
        is_superuser=False,
        qq="123456",
        github="octocat",
        website="https://avatar.test",
        avatar_source="auto",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def make_users(db_session: AsyncSession):
    """工厂函数：批量生成 N 个用户（用于分页/搜索测试）"""

    async def _factory(count: int, role: str = "subscriber", prefix: str = "batch") -> list[User]:
        users = []
        for i in range(count):
            flag_staff = role == "staff"
            flag_su = role == "superuser"
            users.append(
                User(
                    username=f"{prefix}_u_{i}",
                    email=f"{prefix}{i}@test.com",
                    password_hash=get_password_hash(f"P@ssw0rd{i}"),
                    nickname=f"批量用户{i:03d}",
                    is_active=True,
                    is_staff=flag_staff or flag_su,
                    is_superuser=flag_su,
                    is_banned=(i % 7 == 3),  # 每 7 个造 1 个被封禁的（索引3）
                    qq=f"{100000 + i}" if i % 3 == 0 else None,
                    github=f"gh_{prefix}_{i}" if i % 5 == 0 else None,
                )
            )
        db_session.add_all(users)
        await db_session.commit()
        for u in users:
            await db_session.refresh(u)
        return users

    return _factory


@pytest_asyncio.fixture
async def make_comments(db_session: AsyncSession):
    """工厂函数：在同一篇文章下批量生成 N 条评论（不同 status 用于 Tab 过滤）"""

    async def _factory(
        post: Post,
        count: int,
        author: User | None = None,
        status_cycle: list[str] | None = None,
    ) -> list[Comment]:
        if status_cycle is None:
            status_cycle = ["pending", "approved", "rejected", "spam"]
        comments = []
        for i in range(count):
            status = status_cycle[i % len(status_cycle)]
            active = status == "approved"
            comments.append(
                Comment(
                    post_id=post.id,
                    user_id=author.id if author else None,
                    parent_id=None,
                    author_name=(author.nickname if author else None) or f"匿名{i}",
                    author_email=(author.email if author else None) or f"anon{i}@t.com",
                    author_website=f"https://c{i}.test" if i % 4 == 0 else None,
                    author_ip=f"10.0.0.{i % 255}",
                    content=f"第 {i} 条评论内容 — Status={status}. 长文本填充用于列表搜索：keyword_xyz_{i:04d}",
                    status=status,
                    active=active,
                    likes_count=i % 10,
                    is_pinned=False,
                    qq=f"{200000 + i}" if i % 6 == 0 else None,
                    github=f"gh_anon_{i}" if i % 8 == 0 else None,
                )
            )
        db_session.add_all(comments)
        await db_session.commit()
        for c in comments:
            await db_session.refresh(c)
        return comments

    return _factory


@pytest_asyncio.fixture
async def nested_comments(
    db_session: AsyncSession, test_post: Post, test_user: User
) -> dict[str, Comment]:
    """创建嵌套回复链：P（父）→ C（回复P）→ GC（回复C）用于回复链显示验证"""
    parent = Comment(
        post_id=test_post.id,
        user_id=test_user.id,
        parent_id=None,
        author_name=test_user.nickname,
        author_email=test_user.email,
        content="顶层父评论，被其他用户回复",
        status="approved",
        active=True,
    )
    db_session.add(parent)
    await db_session.flush()

    child = Comment(
        post_id=test_post.id,
        user_id=None,  # 匿名游客回复
        parent_id=parent.id,
        author_name="匿名回复者",
        author_email="child@test.com",
        content="我回复了顶层父评论",
        status="approved",
        active=True,
    )
    db_session.add(child)
    await db_session.flush()

    grandchild = Comment(
        post_id=test_post.id,
        user_id=test_user.id,
        parent_id=child.id,
        author_name=test_user.nickname,
        author_email=test_user.email,
        content="我回复了匿名回复者（孙级）",
        status="approved",
        active=True,
    )
    db_session.add(grandchild)
    await db_session.commit()

    for obj in (parent, child, grandchild):
        await db_session.refresh(obj)

    return {"parent": parent, "child": child, "grandchild": grandchild}


@pytest_asyncio.fixture
async def make_navigations(db_session: AsyncSession):
    """工厂函数：批量生成导航节点（支持层级，用于 Nav CRUD tree 视图测试）"""

    async def _factory(
        location: str = "header",
        root_titles: list[str] | None = None,
        children_per_root: int = 0,
    ) -> list["Navigation"]:
        # 延迟导入，避免 conftest 加载时 models/__init__.py 未初始化
        from backend.models.core import Navigation as _Nav

        if root_titles is None:
            root_titles = ["首页", "文章", "关于", "社交"]
        created = []
        for idx, t in enumerate(root_titles):
            root = _Nav(
                title={"zh": t, "en": t, "ja": t, "zh_Hant": t},
                url=f"/{t.lower()}/" if t != "首页" else "/",
                icon="material-symbols:folder",
                parent_id=None,
                location=location,
                order=idx + 1,
                is_active=True,
                target_blank=False,
            )
            db_session.add(root)
            await db_session.flush()
            created.append(root)
            for ci in range(children_per_root):
                child = _Nav(
                    title={
                        "zh": f"{t}-子{ci+1}",
                        "en": f"{t}-child{ci+1}",
                        "zh_Hant": f"{t}-子{ci+1}",
                        "ja": f"{t}-ch{ci+1}",
                    },
                    url=f"/{t.lower()}/c{ci+1}/",
                    icon="material-symbols:subdirectory-arrow-right",
                    parent_id=root.id,
                    location=location,
                    order=ci + 1,
                    is_active=idx % 2 == 0 or ci < children_per_root - 1,
                    target_blank=ci == children_per_root - 1,  # 最后一个子项新窗口
                )
                db_session.add(child)
                created.append(child)
        await db_session.commit()
        for n in created:
            await db_session.refresh(n)
        return created

    return _factory

