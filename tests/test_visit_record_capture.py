"""访客记录的采集口与明细口契约（完整访客记录功能）

两半合在一个文件里，因为它们钉的是同一条链路的两个断点：

1. **采集**（`record_visit` → 队列草稿）：真实来源 IP 必须在受信反代之后才采信
   转发头；Cookie 只准记名字；bot 判定、Accept-Language、Bearer 用户 id 在此刻落进草稿。
   配好 `TRUSTED_PROXY_IPS` 后，「受信对端 + 不带任何转发头」的本机服务直连（Nitro SSR
   渲染时打 127.0.0.1:8000）一律**不进表**——生产实测这类调用占 8.4 万条里的 8.3 万条。
2. **落库**（`_flush_visit_queue`）：草稿具名字段 → 模型列。加列时最容易漏的就是这一步
   （采集写了、模型有、flush 没映射 → 接口永远回 null，且一个错都不报）。
3. **明细口**（`GET /api/monitoring/visits`）：UA 标签读取时现算、bot 档位可按 SQL 筛、
   筛选值按字面量匹配、口径字段（`retention_days` / `data_since` / `window_truncated`）自带。

`conftest.neutralize_visit_telemetry` 会在每个用例 setup 时把模块属性 `record_visit`
换成 no-op，所以本文件在**导入期**抓一次真身（那还没被桩掉）。
"""

import asyncio
import json
from datetime import datetime

import pytest
from sqlalchemy import select
from starlette.requests import Request

import backend.api.monitoring as mon
from backend.core.auth import create_access_token, create_refresh_token
from backend.core.config import settings
from backend.models.monitoring import VisitLog
from backend.utils.compat import UTC, timedelta

_record_visit = mon.record_visit

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)
GOOGLEBOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"


def _request(
    headers: dict[str, str] | None = None,
    *,
    client_addr: tuple[str, int] | None = ("203.0.113.20", 51234),
    path: str = "/blog/posts/hello",
    method: str = "GET",
) -> Request:
    """构造一个最小 http scope 的 Request（不必起整台 app 就能测采集逻辑）。

    直连对端默认是公网地址而不是 127.0.0.1：`tests/conftest.py` 会把
    `trusted_proxy_ips` 设成 `["testclient", "127.0.0.1"]`，于是"回环对端 + 不带转发头"
    在本套件里就是"本机服务直连"，采集口会按设计跳过它。IP/内部流量那几组用例各自显式
    传对端，其余用例（cookie、UA、截断、身份）不该被这层判定影响。
    """
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": path,
        "raw_path": path.encode("latin-1"),
        "query_string": b"",
        "root_path": "",
        "headers": [
            (k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in (headers or {}).items()
        ],
        "server": ("choyeon.cc", 443),
    }
    if client_addr is not None:
        scope["client"] = client_addr
    return Request(scope)


@pytest.fixture
def queue():
    """独立队列，避免与真实单例/后台 flush 任务串台。"""
    previous = mon._visit_queue
    mon._visit_queue = asyncio.Queue(maxsize=100)
    yield mon._visit_queue
    mon._visit_queue = previous


def _only(queue: asyncio.Queue) -> mon._VisitDraft:
    assert queue.qsize() == 1, f"期望恰好一条草稿，实际 {queue.qsize()} 条"
    return queue.get_nowait()


async def _capture(queue: asyncio.Queue, request: Request) -> mon._VisitDraft:
    await _record_visit(request, 200, 12.5)
    return _only(queue)


# ── 1. 真实来源 IP ─────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_trusted_proxy_forwards_real_ip(queue, monkeypatch):
    """直连对端是 nginx（127.0.0.1）时，必须取 XFF 里最右侧非受信跳。

    不采信的话整张表都是回环：去重 IP、UV、按 IP 筛访客一起退化成 1 个值。
    """
    monkeypatch.setattr(settings, "trusted_proxy_ips", ["127.0.0.1"])
    draft = await _capture(
        queue,
        _request(
            {"x-forwarded-for": "198.51.100.23, 127.0.0.1", "user-agent": CHROME_UA},
            client_addr=("127.0.0.1", 51234),
        ),
    )
    assert draft.ip == "198.51.100.23"


@pytest.mark.asyncio
async def test_spoofed_forwarded_for_from_untrusted_peer_is_ignored(queue, monkeypatch):
    """客户端自己伪造 XFF 挡不住遥测投毒的唯一办法：只信受信对端递来的头。

    这条如果反过来（无条件读 XFF），任何人都能把访问日志里的 IP 写成任意值。
    """
    monkeypatch.setattr(settings, "trusted_proxy_ips", ["127.0.0.1"])
    draft = await _capture(
        queue,
        _request({"x-forwarded-for": "203.0.113.77"}, client_addr=("198.51.100.4", 40000)),
    )
    assert draft.ip == "198.51.100.4", "非受信对端的 XFF 必须整体忽略"


@pytest.mark.asyncio
async def test_without_trusted_proxies_the_peer_ip_is_recorded(queue, monkeypatch):
    """默认不设 TRUSTED_PROXY_IPS 时记的就是直连对端 —— 经本机 nginx 的请求因此读成回环。

    钉住这层行为，部署侧要配什么就成了可证明的结论而不是猜测。
    """
    monkeypatch.setattr(settings, "trusted_proxy_ips", [])
    draft = await _capture(
        queue,
        _request({"x-forwarded-for": "203.0.113.77"}, client_addr=("127.0.0.1", 51234)),
    )
    assert draft.ip == "127.0.0.1"


@pytest.mark.asyncio
async def test_missing_peer_is_recorded_as_null_ip(queue, monkeypatch):
    """拿不到 socket 对端时写 null，而不是字面量 "unknown" 占位。

    "unknown" 会被 `count(distinct ip)` 当成一个真实访客计入 UV。
    """
    monkeypatch.setattr(settings, "trusted_proxy_ips", [])
    draft = await _capture(queue, _request(client_addr=None))
    assert draft.ip is None


# ── 1b. 本机服务直连不是访客 ───────────────────────────────────────────────
@pytest.mark.asyncio
async def test_internal_service_call_is_not_recorded(queue, monkeypatch):
    """Nitro SSR 渲染时打 127.0.0.1:8000 取设置/列表，不是"一个访客在看站点"。

    生产实测 8.4 万条访问日志里 8.3 万条 IP 是 127.0.0.1，后台的"独立 IP"、UV
    与按 IP 筛人因此全部读成"整站只有本机这一个访客"。判定要求"受信对端 + 不带
    任何转发头"，真实访客经 nginx 时必然带 XFF，所以不会被一起挡掉。
    """
    monkeypatch.setattr(settings, "trusted_proxy_ips", ["127.0.0.1"])
    await _record_visit(
        _request({"user-agent": "Rosetta-SSR"}, client_addr=("127.0.0.1", 40001)),
        200,
        3.0,
    )
    assert queue.qsize() == 0, "本机内部调用不得进访问日志"


@pytest.mark.asyncio
async def test_proxy_forwarded_request_is_still_recorded(queue, monkeypatch):
    """带转发头的受信对端请求＝经反代进来的真实访客，必须照常记一条。

    上一条件如果写宽成"对端是回环就不记"，nginx 本机反代下的所有访客会一起消失。
    """
    monkeypatch.setattr(settings, "trusted_proxy_ips", ["127.0.0.1"])
    draft = await _capture(
        queue,
        _request(
            {"x-forwarded-for": "203.0.113.9", "user-agent": CHROME_UA},
            client_addr=("127.0.0.1", 51234),
        ),
    )
    assert draft.ip == "203.0.113.9"


@pytest.mark.asyncio
async def test_without_trusted_proxies_nothing_is_treated_as_internal(queue, monkeypatch):
    """未配置 TRUSTED_PROXY_IPS 时一条都不跳（保持旧行为，别把访客误当内部流量）。

    没有信任边界就无从区分"本机服务"与"本机伪造的请求"，宁可多记也不能漏记真人。
    """
    monkeypatch.setattr(settings, "trusted_proxy_ips", [])
    draft = await _capture(
        queue,
        _request({"user-agent": "Rosetta-SSR"}, client_addr=("127.0.0.1", 51234)),
    )
    assert draft.ip == "127.0.0.1"


# ── 2. Cookie / 语言 / bot / 身份 ──────────────────────────────────────────
@pytest.mark.asyncio
async def test_cookie_names_are_recorded_but_never_their_values(queue):
    """Cookie 值是会话凭证；遥测表只准留名字（AGENTS.md §12.5 的凭证不落日志口径）。"""
    draft = await _capture(
        queue,
        _request({"cookie": "rosetta_lang=zh; session_token=SECRET-JWT-VALUE; cf_clearance=abc"}),
    )
    assert draft.cookie_names == "rosetta_lang; session_token; cf_clearance"
    assert "SECRET" not in draft.cookie_names


@pytest.mark.asyncio
async def test_duplicate_cookie_names_are_collapsed_and_capped(queue):
    draft = await _capture(
        queue,
        _request({"cookie": "a=1; a=2; b=3", "accept-language": "zh-CN,zh;q=0.9,en;q=0.8"}),
    )
    assert draft.cookie_names == "a; b"
    assert draft.accept_language == "zh-CN,zh;q=0.9,en;q=0.8"


@pytest.mark.asyncio
async def test_absent_headers_are_null_not_empty_string(queue):
    draft = await _capture(queue, _request({}, path="/x"))
    assert draft.cookie_names is None
    assert draft.accept_language is None
    assert draft.referer is None
    assert draft.user_agent is None


@pytest.mark.asyncio
async def test_bot_verdict_is_frozen_at_capture_time(queue):
    """is_bot 是唯一落库的 UA 派生值：它要在 SQL 里筛（分页/计数），其余标签读取时现算。"""
    bot = await _capture(queue, _request({"user-agent": GOOGLEBOT_UA}))
    assert bot.is_bot is True
    human = await _capture(queue, _request({"user-agent": CHROME_UA}, path="/"))
    assert human.is_bot is False


@pytest.mark.asyncio
async def test_oversized_inputs_are_truncated(queue):
    """列宽是 String(500)/String(255)：超长值必须在入队前截断，否则整批 INSERT 撞约束。"""
    draft = await _capture(
        queue,
        _request(
            {"user-agent": "Mozilla/5.0 " + "x" * 900, "referer": "https://e/" + "y" * 900},
            path="/" + "z" * 900,
        ),
    )
    assert len(draft.user_agent) == 500
    assert len(draft.referer) == 500
    assert len(draft.path) == 500


@pytest.mark.asyncio
async def test_bearer_access_token_marks_the_visiting_user(queue):
    token = create_access_token({"sub": "42"})
    draft = await _capture(queue, _request({"authorization": f"Bearer {token}"}))
    assert draft.user_id == 42


@pytest.mark.asyncio
async def test_refresh_token_and_garbage_do_not_mark_a_user(queue):
    """只认 access：refresh 也带 sub，拿它标注会把"刷新令牌的请求"记成某个用户的浏览。"""
    refresh, _ = create_refresh_token({"sub": "42"}, user_token_version=0)
    draft = await _capture(queue, _request({"authorization": f"Bearer {refresh}"}))
    assert draft.user_id is None
    draft2 = await _capture(queue, _request({"authorization": "Bearer not-a-jwt"}, path="/b"))
    assert draft2.user_id is None


# ── 3. 草稿 → 模型列 ───────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_flush_maps_every_new_column_to_the_row(queue, db_session, monkeypatch):
    """采集写了、模型有列、flush 没映射 = 接口永远回 null 且一声不响。

    所以新列必须在这里对账一次：草稿字段与行字段逐个相等。
    """
    token = create_access_token({"sub": "7"})
    await _record_visit(
        _request(
            {
                "user-agent": GOOGLEBOT_UA,
                "cookie": "cf_clearance=whatever",
                "accept-language": "ja",
                "authorization": f"Bearer {token}",
            }
        ),
        404,
        33.7,
    )
    monkeypatch.setattr(mon, "_VISIT_BATCH_SIZE", 50)
    assert await mon._flush_visit_queue() == 1

    row = (
        await db_session.execute(select(VisitLog).where(VisitLog.path == "/blog/posts/hello"))
    ).scalar_one()
    assert row.cookie_names == "cf_clearance"
    assert row.accept_language == "ja"
    assert row.user_id == 7
    assert row.is_bot is True
    assert row.status_code == 404
    assert row.response_time_ms == 33
    assert row.user_agent == GOOGLEBOT_UA


# ── 4. 明细口 GET /api/monitoring/visits ───────────────────────────────────
async def _seed(db_session, **kwargs) -> VisitLog:
    values: dict[str, object] = {
        "method": "GET",
        "status_code": 200,
        "response_time_ms": 10,
        "created_at": datetime.now(UTC),
    }
    values.update(kwargs)
    row = VisitLog(**values)
    db_session.add(row)
    await db_session.flush()
    return row


@pytest.mark.asyncio
async def test_visits_endpoint_is_staff_only(client, auth_headers, db_session):
    await _seed(db_session, path="/", ip="203.0.113.1")

    anon = await client.get("/api/monitoring/visits")
    assert anon.status_code == 401

    as_user = await client.get("/api/monitoring/visits", headers=auth_headers)
    assert as_user.status_code == 403, "普通登录用户不得读到全站访客 IP/UA 明细"


@pytest.mark.asyncio
async def test_visits_returns_derived_ua_labels_at_read_time(client, staff_headers, db_session):
    """标签不落库，所以改一次规则历史行跟着变；同时原始 UA 必须随行返回供人工复核。"""
    await _seed(
        db_session,
        path="/posts/x",
        ip="203.0.113.9",
        user_agent=CHROME_UA,
        cookie_names="rosetta_lang",
        is_bot=False,
    )

    resp = await client.get("/api/monitoring/visits", headers=staff_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "success" not in body, "本族接口一贯返回裸对象，不套 {success,data} 信封"

    item = body["items"][0]
    assert item["os"] == "Windows"
    assert item["os_version"] == "10 / 11", "Windows NT 10.0 是产品名口径，不是原始数字"
    assert item["browser"] == "Chrome"
    assert item["device"] == "desktop"
    assert item["is_bot"] is False
    assert item["user_agent"] == CHROME_UA
    assert item["cookie_names"] == "rosetta_lang"
    assert item["created_at"].endswith("+00:00"), "naive UTC 序列化前必须补时区"


@pytest.mark.asyncio
async def test_bot_kind_filter_excludes_undecided_history(client, staff_headers, db_session):
    """本列上线前的历史行 is_bot 为 NULL：两档筛选都不该把它们算进去。"""
    await _seed(db_session, path="/bot", ip="1.1.1.1", user_agent=GOOGLEBOT_UA, is_bot=True)
    await _seed(db_session, path="/human", ip="1.1.1.2", user_agent=CHROME_UA, is_bot=False)
    await _seed(db_session, path="/legacy", ip="1.1.1.3", user_agent=CHROME_UA, is_bot=None)

    async def total(kind):
        body = (
            await client.get(f"/api/monitoring/visits?kind={kind}", headers=staff_headers)
        ).json()
        return body["total"], [i["path"] for i in body["items"]]

    all_total, all_paths = await total("all")
    bot_total_, bot_paths = await total("bot")
    human_total, human_paths = await total("human")

    assert all_total == 3
    assert sorted(all_paths) == ["/bot", "/human", "/legacy"]
    assert (bot_total_, bot_paths) == (1, ["/bot"])
    assert (human_total, human_paths) == (1, ["/human"]), "NULL（未判定）不得被当成真人"


@pytest.mark.asyncio
async def test_filter_wildcards_are_literal_not_patterns(client, staff_headers, db_session):
    """IP 框里打一个 `%` 变成"匹配全部"、路径框里的 `_` 匹配任意单字符＝筛选悄悄失效。"""
    await _seed(db_session, path="/a_b", ip="203.0.113.5")
    await _seed(db_session, path="/axb", ip="198.51.100.9")

    body = (await client.get("/api/monitoring/visits?ip=%", headers=staff_headers)).json()
    assert body["total"] == 0, "通配符必须按字面量处理"

    body = (await client.get("/api/monitoring/visits?path=a_b", headers=staff_headers)).json()
    assert [i["path"] for i in body["items"]] == ["/a_b"]

    body = (await client.get("/api/monitoring/visits?ip=203.0.113.5", headers=staff_headers)).json()
    assert body["total"] == 1


@pytest.mark.asyncio
async def test_status_and_window_filters_and_counter_fields(client, staff_headers, db_session):
    now = datetime.now(UTC)
    await _seed(db_session, path="/ok", ip="9.9.9.9", user_agent=CHROME_UA, is_bot=False)
    await _seed(
        db_session,
        path="/gone",
        ip="9.9.9.9",
        status_code=404,
        user_agent=GOOGLEBOT_UA,
        is_bot=True,
    )
    await _seed(
        db_session,
        path="/ancient",
        ip="8.8.8.8",
        user_agent=CHROME_UA,
        is_bot=False,
        created_at=now - timedelta(days=40),
    )

    body = (await client.get("/api/monitoring/visits?days=30", headers=staff_headers)).json()
    assert body["days"] == 30
    assert sorted(i["path"] for i in body["items"]) == ["/gone", "/ok"], "窗口外的行不参与计数"
    assert body["total"] == 2
    assert body["unique_ips"] == 1, "同一 IP 的多条访问只算一个独立访客"
    assert body["bot_total"] == 1

    body = (await client.get("/api/monitoring/visits?status=404", headers=staff_headers)).json()
    assert [i["path"] for i in body["items"]] == ["/gone"]
    assert body["bot_total"] == 1, "bot_total 按 base 条件算，不随 status 之外的档位变"

    body = (await client.get("/api/monitoring/visits?days=365", headers=staff_headers)).json()
    assert body["total"] == 3
    assert body["data_since"], "现存最早一条的时间是判断窗口是否被截短的依据"


@pytest.mark.asyncio
async def test_window_truncated_tracks_retention(client, staff_headers, db_session, monkeypatch):
    """保留窗口短于请求窗口 → 读数只是下界，必须自带标记供前端说明口径。"""
    await _seed(db_session, path="/", ip="1.2.3.4", user_agent=CHROME_UA)

    monkeypatch.setattr(settings, "log_retention_days", 7)
    assert (await client.get("/api/monitoring/visits?days=30", headers=staff_headers)).json()[
        "window_truncated"
    ] is True
    assert (await client.get("/api/monitoring/visits?days=7", headers=staff_headers)).json()[
        "window_truncated"
    ] is False

    monkeypatch.setattr(settings, "log_retention_days", 0)
    body = (await client.get("/api/monitoring/visits?days=30", headers=staff_headers)).json()
    assert body["window_truncated"] is False, "0/负数表示不清理，窗口就是全量"
    assert body["retention_days"] == 0


@pytest.mark.asyncio
async def test_cookie_values_never_reach_the_response(client, staff_headers, db_session):
    """整条响应体扫一遍：即便哪天有人把值写进列，这口径也会立刻红。"""
    await _seed(
        db_session,
        path="/",
        ip="1.2.3.4",
        user_agent=CHROME_UA,
        cookie_names="rosetta_lang; session_token",
    )
    text = (await client.get("/api/monitoring/visits", headers=staff_headers)).text
    for needle in ("secret", "Bearer", "eyJ"):
        assert needle.lower() not in text.lower(), (
            f"响应里出现了 {needle} —— 有凭据形态的东西被回吐了"
        )


@pytest.mark.asyncio
async def test_visiting_user_is_annotated_with_username(
    client, staff_headers, staff_user, db_session
):
    await _seed(
        db_session,
        path="/admin",
        ip="1.2.3.4",
        user_agent=CHROME_UA,
        user_id=staff_user.id,
    )
    await _seed(db_session, path="/anon", ip="1.2.3.5", user_agent=CHROME_UA)

    body = (await client.get("/api/monitoring/visits", headers=staff_headers)).json()
    by_path = {i["path"]: i for i in body["items"]}
    assert by_path["/admin"]["username"] == staff_user.username
    assert by_path["/anon"]["username"] is None

    # 已删除用户的 id 只留 id，不能因为查不到昵称就整口 500
    await _seed(db_session, path="/ghost", ip="1.2.3.6", user_agent=CHROME_UA, user_id=999999)
    body = (await client.get("/api/monitoring/visits", headers=staff_headers)).json()
    ghost = {i["path"]: i for i in body["items"]}["/ghost"]
    assert ghost["user_id"] == 999999 and ghost["username"] is None


@pytest.mark.asyncio
async def test_pagination_reports_full_total_and_respects_page_size(
    client, staff_headers, db_session
):
    for i in range(12):
        await _seed(db_session, path=f"/p{i}", ip=f"10.0.0.{i}", user_agent=CHROME_UA)

    body = (
        await client.get("/api/monitoring/visits?days=1&page=1&page_size=10", headers=staff_headers)
    ).json()
    assert body["total"] == 12
    assert len(body["items"]) == 10
    assert body["page_size"] == 10

    page2 = json.loads(
        (
            await client.get(
                "/api/monitoring/visits?days=1&page=2&page_size=10", headers=staff_headers
            )
        ).text
    )
    assert len(page2["items"]) == 2
    seen = {i["path"] for i in body["items"] + page2["items"]}
    assert len(seen) == 12, "翻页不得重复或漏行"


@pytest.mark.asyncio
async def test_invalid_query_params_are_rejected(client, staff_headers):
    for q in ("days=0", "days=400", "page=0", "page_size=5", "page_size=500", "kind=nope"):
        resp = await client.get(f"/api/monitoring/visits?{q}", headers=staff_headers)
        assert resp.status_code == 422, f"{q} 应被校验拦下，实际 {resp.status_code}"
