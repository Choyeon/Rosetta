# -*- coding: utf-8 -*-
"""非一键 OOBE + 后台冒烟：reset → install → login → dashboard stats"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BACKEND = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:4321"

INSTALL_PAYLOAD = {
    "database_type": "sqlite",
    "db_host": "localhost",
    "db_port": 5432,
    "db_name": "rosetta",
    "db_user": "",
    "db_password": "",
    "db_path": ".e2e/rosetta_e2e_api.db",
    "redis_enabled": False,
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_password": "",
    "admin_username": "Choyeon",
    "admin_email": "choyeon+e2e@foxmail.com",
    "admin_password": "Rosetta@2026!",
    "admin_nickname": "Choyeon (E2E)",
    "admin_bio": "E2E Test Admin — non-oneclick OOBE",
    "admin_qq": "952223950",
    "admin_github": "Choyeon",
    "admin_website": "http://127.0.0.1:4321",
    "admin_avatar_source": "auto",
    "site_name": "Rosetta Test E2E",
    "site_description": "E2E Test Site - 通过 HTTP API 完成非一键安装",
    "site_url": "http://127.0.0.1:4321",
    "site_keywords": "Rosetta,E2E,博客,API Install",
    "site_author": "Choyeon",
    "site_email": "choyeon+e2e@foxmail.com",
    "enable_comments": False,
    "enable_registration": False,
    "enable_rss": True,
    "enable_bing_wallpaper": False,
    "enable_pagefind_search": True,
    "enable_encrypted_posts": False,
    "enable_music_player": False,
    "environment": "development",
}


def main() -> int:
    s = requests.Session()
    s.headers.update({"Accept": "application/json"})
    s.verify = False

    # 0. 清理旧的 E2E SQLite DB 文件（reset OOBE 不会删业务 DB）
    db_rel = INSTALL_PAYLOAD["db_path"]
    db_path = (ROOT / db_rel).resolve() if not Path(db_rel).is_absolute() else Path(db_rel)
    if db_path.exists():
        try:
            db_path.unlink()
            print("[db/clean ] removed stale", db_path)
        except Exception as e:
            print(f"[db/clean ] WARN cannot remove {db_path}: {e}")
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)

    # 0b. 清理 rosetta_config.db（OOBE 的配置文件位置：项目根或 backend/）
    for p in [ROOT / "rosetta_config.db", ROOT / "backend" / "rosetta_config.db"]:
        if p.exists():
            try:
                p.unlink()
                print("[cfg/clean] removed", p)
            except Exception as e:
                print(f"[cfg/clean] WARN cannot remove {p}: {e}")

    # 1. health
    r0a = s.get(f"{BACKEND}/health/", timeout=10, allow_redirects=True)
    r0b = s.get(f"{FRONTEND}/api/oobe/status/", timeout=10, allow_redirects=True)
    print(f"[health] backend={r0a.status_code} frontend_oobe_probe={r0b.status_code}")

    # 2. status
    r1 = s.get(f"{BACKEND}/api/oobe/status/", timeout=10, allow_redirects=True)
    d1 = r1.json()
    print("[oobe/status]", r1.status_code, json.dumps(d1, ensure_ascii=False)[:180])

    # 3. reset
    r_reset = s.post(f"{BACKEND}/api/oobe/reset/", json={}, timeout=15, allow_redirects=True)
    print("[oobe/reset ]", r_reset.status_code,
          (r_reset.json().get("message") if r_reset.status_code < 400 else r_reset.text[:160]))

    # 4. env check
    r_env = s.post(f"{BACKEND}/api/oobe/check/", json={}, timeout=30, allow_redirects=True)
    env = r_env.json() if r_env.status_code < 400 else {}
    print("[oobe/check ]", r_env.status_code,
          json.dumps(env.get("checks") or env, ensure_ascii=False)[:260])

    # 5. install (non-oneclick, custom payload)
    print("[oobe/install] sending (DB init + admin + site config + feature flags) …")
    r_install = s.post(
        f"{BACKEND}/api/oobe/install/",
        json=INSTALL_PAYLOAD,
        timeout=600,
        allow_redirects=True,
    )
    data = r_install.json() if r_install.content else {}
    ok = r_install.status_code == 200 and data.get("success")
    print("[oobe/install]", r_install.status_code,
          "success=" + str(ok),
          "msg=" + str((data.get("message") or data.get("detail") or str(data))[:260]))
    if not ok:
        if isinstance(data.get("detail"), list):
            for err in data["detail"]:
                print("   → err:", json.dumps(err, ensure_ascii=False))
        print("INSTALL FAILED")
        return 2

    # 6. login (JSON body)
    r_login = s.post(
        f"{BACKEND}/api/users/login",
        json={
            "username": INSTALL_PAYLOAD["admin_username"],
            "password": INSTALL_PAYLOAD["admin_password"],
        },
        timeout=30,
        allow_redirects=True,
    )
    tok = r_login.json() if r_login.content else {}
    print("[users/login]", r_login.status_code,
          ("has_access_token=" + str("access_token" in tok)) if r_login.status_code == 200
          else (r_login.text[:220]))
    if r_login.status_code != 200 or "access_token" not in tok:
        return 3
    bearer = {"Authorization": f"Bearer {tok['access_token']}"}

    # 7. Dashboard stats
    r_stats = s.get(f"{BACKEND}/api/admin/stats", headers=bearer, timeout=20, allow_redirects=True)
    st = r_stats.json() if r_stats.content else {}
    print("[admin/stats]", r_stats.status_code,
          (f"users={st.get('users')} posts={st.get('posts')} cats={st.get('categories')} tags={st.get('tags')} comments={st.get('comments')}")
          if r_stats.status_code == 200 else r_stats.text[:200])
    if r_stats.status_code != 200:
        return 4

    # 8. current user info (profile)
    r_me = s.get(f"{BACKEND}/api/users/me", headers=bearer, timeout=20, allow_redirects=True)
    me = r_me.json() if r_me.content else {}
    print("[users/me   ]", r_me.status_code,
          ("id=" + str(me.get('id')) + " user=" + str(me.get('username')) + " email=" + str(me.get('email')) + " role=" + str(me.get('role')))
          if r_me.status_code == 200 else r_me.text[:200])
    if r_me.status_code != 200:
        return 5

    # 9. save admin password into sidecar file for later steps
    sidecar = ROOT / ".e2e" / "_admin_creds.json"
    sidecar.write_text(
        json.dumps(
            {
                "username": INSTALL_PAYLOAD["admin_username"],
                "password": INSTALL_PAYLOAD["admin_password"],
                "access_token": tok["access_token"],
                "user_id": me.get("id"),
                "backend": BACKEND,
                "frontend": FRONTEND,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("[sidecar   ] wrote", sidecar)
    print("\n[E2E OK] non-oneclick OOBE → admin login → dashboard stats → auth/me all passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
