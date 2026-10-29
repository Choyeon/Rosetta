"""页面浏览上报链（批次 #59）契约。

为什么要有这条链：nginx 只把 `/api` 与 `/media` 转给 FastAPI，HTML 文档全部由 Nitro
渲染后直接回浏览器，后端**从来没见过**那次请求。于是 `visit_logs` 只是"API 请求明细"：
真实访客读完一篇文章、Googlebot 抓走一个页面，一条都不进表——批次 #53 的访客记录页
上线时线上实测"打页面路径零记录、打 /api 路径留下行"。补的是 `POST /api/monitoring/pageviews`
（Nitro 在每次文档响应后 fire-and-forget 调用）。

本文件钉住四条：
1. 鉴权只有"共享密钥"这一种，且**未配置即禁用**（403），不给匿名方留一个能往只增遥测表
   里写任意行的口子（伪造访客记录＝伪造 UV／机器人档位读数）。
2. Cookie **值**即使被调用方带上来也不会落进草稿：重导名称的单源 helper 在这里也必须生效，
   否则"值是会话凭证"这条红线就取决于前端代码写对没有。
3. 草稿字段映射齐（path/ip/status/耗时/is_bot），漏一个的表现是页面永远读不到那一列。
4. 队列满时回 `recorded=false` 而不是抛错——上报方是 fire-and-forget，抛错会变成
   后端日志里的 500 与前端的一次次重试。
"""

import asyncio
from datetime import datetime

import pytest

import backend.api.monitoring as mon
from backend.core.config import settings

SECRET = "unit-test-pageview-secret"
HEADERS = {"x-rosetta-purge-secret": SECRET}
REPORT = {
    "path": "/posts/hello-world",
    "method": "GET",
    "ip": "203.0.113.42",
    "user_agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    ),
    "referer": "https://choyeon.cc/",
    "cookie_names": "rosetta_lang; cf_clearance",
    "accept_language": "zh-CN,zh;q=0.9",
    "status_code": 200,
    "response_time_ms": 83,
}


@pytest.fixture
def isolated_queue(monkeypatch):
    """独立队列 + 挡住 flusher 懒启动。

    不挡住的话后台循环会在断言之前把这批草稿取走写库，用例读到的是空队列——
    那种"偶尔红"的形态正好是遥测用例最难复现的一类。
    """
    previous = mon._visit_queue
    previous_flusher = mon._visit_flusher
    monkeypatch.setattr(mon, "_visit_queue", asyncio.Queue(maxsize=100), raising=False)
    monkeypatch.setattr(mon, "_visit_flusher", asyncio.Future(), raising=False)
    yield mon._visit_queue
    mon._visit_queue = previous
    mon._visit_flusher = previous_flusher


@pytest.fixture
def with_secret(monkeypatch):
    monkeypatch.setattr(settings, "frontend_purge_secret", SECRET)


async def test_report_without_secret_is_403(client, with_secret, isolated_queue):
    resp = await client.post("/api/monitoring/pageviews", json=REPORT)
    assert resp.status_code == 403
    assert isolated_queue.qsize() == 0, "鉴权失败不能留下任何草稿"


async def test_report_with_wrong_secret_is_403(client, with_secret, isolated_queue):
    resp = await client.post(
        "/api/monitoring/pageviews", json=REPORT, headers={"x-rosetta-purge-secret": "nope"}
    )
    assert resp.status_code == 403
    assert isolated_queue.qsize() == 0


async def test_unconfigured_secret_disables_the_whole_chain(client, monkeypatch, isolated_queue):
    """没配密钥＝这条链没装配。空串不能被当成"匹配另一个空串"放行。"""
    monkeypatch.setattr(settings, "frontend_purge_secret", "")
    resp = await client.post(
        "/api/monitoring/pageviews", json=REPORT, headers={"x-rosetta-purge-secret": ""}
    )
    assert resp.status_code == 403


async def test_valid_report_lands_a_complete_draft(client, with_secret, isolated_queue):
    resp = await client.post("/api/monitoring/pageviews", json=REPORT, headers=HEADERS)
    assert resp.status_code == 202, resp.text
    assert resp.json() == {"recorded": True}
    assert isolated_queue.qsize() == 1
    draft = isolated_queue.get_nowait()
    assert draft.path == "/posts/hello-world"
    assert draft.method == "GET"
    # 边缘传来的 IP 原样采信：它已经是 nginx 那一跳写进 XFF 的真实访客地址。
    assert draft.ip == "203.0.113.42"
    assert draft.status_code == 200
    assert draft.response_time_ms == 83
    assert draft.is_bot is False
    assert draft.accept_language == "zh-CN,zh;q=0.9"
    assert draft.user_id is None, "文档请求这一跳没有 token，不该凭空归属给某个用户"
    assert isinstance(draft.created_at, datetime)


async def test_bot_pageview_is_flagged_as_bot(client, with_secret, isolated_queue):
    resp = await client.post(
        "/api/monitoring/pageviews",
        json={
            **REPORT,
            "user_agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        },
        headers=HEADERS,
    )
    assert resp.status_code == 202
    assert isolated_queue.get_nowait().is_bot is True


async def test_cookie_values_never_survive_the_report(client, with_secret, isolated_queue):
    """调用方把值一起送上来也只剩名字。

    这条是"值不落库"红线的服务端一侧：只靠前端只发名字＝一个前端 bug 就把会话凭证
    写进只增、可导出、后台整页列出的遥测表。
    """
    resp = await client.post(
        "/api/monitoring/pageviews",
        json={
            **REPORT,
            "cookie_names": "rosetta_lang=zh; session_token=SECRET-JWT-VALUE; cf_clearance=abc",
        },
        headers=HEADERS,
    )
    assert resp.status_code == 202
    names = isolated_queue.get_nowait().cookie_names
    assert names == "rosetta_lang; session_token; cf_clearance"
    assert "SECRET-JWT-VALUE" not in names


async def test_unknown_keys_are_rejected(client, with_secret, isolated_queue):
    """`extra="forbid"`：这个口能写的只有遥测表，但"多收一个键就静默丢掉"是所有
    上报接口的默认腐化路径（将来加字段时没人知道少了一列）。"""
    resp = await client.post(
        "/api/monitoring/pageviews", json={**REPORT, "is_admin": True}, headers=HEADERS
    )
    assert resp.status_code == 422
    assert isolated_queue.qsize() == 0


@pytest.mark.parametrize(
    "bad", [{"status_code": 999}, {"status_code": 0}, {"path": ""}, {"response_time_ms": -1}]
)
async def test_out_of_range_fields_are_rejected(client, with_secret, isolated_queue, bad):
    resp = await client.post("/api/monitoring/pageviews", json={**REPORT, **bad}, headers=HEADERS)
    assert resp.status_code == 422


async def test_full_queue_reports_not_recorded_instead_of_raising(client, with_secret, monkeypatch):
    """队列满时是"有损遥测"，不是 500：上报方 fire-and-forget，抛错只会让它重试得更凶。"""
    monkeypatch.setattr(mon, "_visit_queue", asyncio.Queue(maxsize=1), raising=False)
    monkeypatch.setattr(mon, "_visit_flusher", asyncio.Future(), raising=False)
    await mon._enqueue_visit_draft(
        mon._VisitDraft(
            path="/seeded",
            method="GET",
            ip=None,
            user_agent=None,
            referer=None,
            status_code=200,
            response_time_ms=1,
            created_at=datetime.now(),
        )
    )
    resp = await client.post("/api/monitoring/pageviews", json=REPORT, headers=HEADERS)
    assert resp.status_code == 202
    assert resp.json() == {"recorded": False}
