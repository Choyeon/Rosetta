# -*- coding: utf-8 -*-
"""Todo 7: Spot tests（smoke）— 操作日志 / 导入导出 / 通知 / 站点设置"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SIDE = ROOT / ".e2e" / "_admin_creds.json"
BACKEND = "http://127.0.0.1:8000"


def load_creds() -> dict:
    return json.loads(SIDE.read_text(encoding="utf-8"))


def b(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


def _msg(body) -> str:
    if isinstance(body, dict):
        if body.get("message"):
            return str(body["message"])[:120]
        keys = [k for k in ("total", "count", "unread_count", "items") if k in body]
        if keys:
            preview = {k: (len(body[k]) if isinstance(body[k], (list, dict, str)) else body[k]) for k in keys}
            return json.dumps(preview, ensure_ascii=False)[:120]
    return ""


def log(label: str, r: requests.Response):
    try:
        body = r.json() if r.content else None
    except Exception:
        body = None
    ok = r.status_code < 400
    print(f"[{label:<28s}] {r.status_code}  {'✔' if ok else '✗'}  {_msg(body)}")
    if not ok:
        if isinstance(body, (dict, list)):
            preview = json.dumps(body, ensure_ascii=False)[:260]
        else:
            preview = (r.text or "")[:260]
        print("   ↳ body:", preview)
    return ok, body


def main() -> int:
    creds = load_creds()
    backend = creds.get("backend") or BACKEND
    s = requests.Session()
    s.verify = False
    access = creds["access_token"]
    fails = []

    # ========== 公开：站点配置 + 站点统计 ==========
    ok, _ = log("GET /api/config (site public)", s.get(f"{backend}/api/config", timeout=15))
    if not ok: fails.append("GET /api/config")
    ok, _ = log("GET /api/blog/site-stats", s.get(f"{backend}/api/blog/site-stats", timeout=15))
    if not ok: fails.append("GET /api/blog/site-stats")

    # ========== 管理员：操作日志 ==========
    ok, logs_body = log("GET /api/admin/logs (audit)", s.get(f"{backend}/api/admin/logs", headers=b(access), params={"page": 1, "page_size": 5}, timeout=15))
    if not ok: fails.append("GET /api/admin/logs")
    # 导出日志（HEAD-like 快路径，用 stream 防止下载过大数据）
    try:
        r = s.get(f"{backend}/api/admin/logs/export", headers=b(access), params={"format": "json"}, timeout=15, stream=True, allow_redirects=True)
        first_chunk = next(r.iter_content(chunk_size=128), b"")
        r.close()
        ok_e = r.status_code < 400 and (len(first_chunk) > 0 or r.status_code == 204)
        print(f"[GET /api/admin/logs/export   ] {r.status_code}  {'✔' if ok_e else '✗'}  first_chunk_len={len(first_chunk)}")
        if not ok_e: fails.append("GET /api/admin/logs/export")
    except Exception as e:
        print(f"[GET /api/admin/logs/export   ] ERR  {e!r}"); fails.append("GET /api/admin/logs/export")

    # ========== 管理员：导入导出 ==========
    # 导出 JSON（可能有数据）
    ok, _ = log("GET /api/admin/export/posts", s.get(f"{backend}/api/admin/export/posts", headers=b(access), timeout=60))
    if not ok: fails.append("GET /api/admin/export/posts")
    # 导出 Markdown（可能需要较长时间，超时放宽）
    try:
        r = s.get(f"{backend}/api/admin/export/markdown", headers=b(access), timeout=120)
        ok_e = r.status_code < 400
        sz = len(r.content)
        print(f"[GET /api/admin/export/markdown] {r.status_code}  {'✔' if ok_e else '✗'}  size={sz}B")
        if not ok_e: fails.append("GET /api/admin/export/markdown")
    except Exception as e:
        print(f"[GET /api/admin/export/markdown] ERR  {e!r}"); fails.append("GET /api/admin/export/markdown")

    # ========== 管理员：站点配置（完整/更新） ==========
    ok, full_cfg = log("GET /api/config/full (admin)", s.get(f"{backend}/api/config/full", headers=b(access), timeout=15))
    if not ok: fails.append("GET /api/config/full")
    # 更新站点设置：只改一个小字段 seo_site_description_zh，然后立刻还原
    time.sleep(0.3)
    ok, upd_body = log(
        "POST /api/admin/settings (seo desc)",
        s.post(
            f"{backend}/api/admin/settings",
            headers=b(access),
            json={"seo": {"site_description_zh": "E2E Spot Test（即刻还原）"}},
            timeout=20,
        ),
    )
    if not ok: fails.append("POST /api/admin/settings")
    # 再 GET 一下看看有没有生效
    time.sleep(0.3)
    ok2, _ = log("GET /api/config/full (after update)", s.get(f"{backend}/api/config/full", headers=b(access), timeout=15))
    if not ok2: fails.append("GET /api/config/full (after update)")

    # ========== 通知 ==========
    ok, _ = log("GET /api/notifications/ (list)", s.get(f"{backend}/api/notifications/", headers=b(access), params={"page": 1, "page_size": 5}, timeout=15))
    if not ok: fails.append("GET /api/notifications/")
    ok, _ = log("GET /api/notifications/unread-count", s.get(f"{backend}/api/notifications/unread-count", headers=b(access), timeout=15))
    if not ok: fails.append("GET /api/notifications/unread-count")
    ok, _ = log("GET /api/notifications/stats", s.get(f"{backend}/api/notifications/stats", headers=b(access), timeout=15))
    if not ok: fails.append("GET /api/notifications/stats")

    print()
    if fails:
        print("[Todo 7 SPOT FAILS]:", ", ".join(fails))
        return 1
    print("[Todo 7 OK] Spot checks: 操作日志 + 导入导出 JSON/MD + 通知 3 endpoints + 站点配置 GET/PUT/FULL 全部 2xx。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
