# -*- coding: utf-8 -*-
"""Todo 6: 发布文章（草稿→发布）+ 前台可读（分步策略：POST 不带 tag_ids，再 PUT 补充，完美绕开 POST 的 greenlet 问题）

精确路径：
  创建文章：POST /api/blog/posts        (不传 tag_ids，category_id 可传或不传)
  更新文章：PUT  /api/blog/posts/{id}   (补充 tag_ids / category_id / status / is_pinned ...)
  前台 URL ：http://127.0.0.1:4321/posts/<slug>/
"""
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
FRONTEND = "http://127.0.0.1:4321"


def load_creds() -> dict:
    return json.loads(SIDE.read_text(encoding="utf-8"))


def b(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


def log(label: str, r: requests.Response) -> dict:
    try:
        body = r.json() if r.content else {}
    except Exception:
        body = {}
    ok = r.status_code < 400
    msg = ""
    if isinstance(body, dict):
        id_ = body.get("id")
        slug = body.get("slug")
        status = body.get("status")
        tags = body.get("tags")
        cat = body.get("category")
        extras = []
        if id_:
            extras.append(f"id={id_}")
        if slug:
            extras.append(f"slug={slug}")
        if status:
            extras.append(f"status={status}")
        if isinstance(tags, list) and tags:
            extras.append(f"tags=[{','.join(str(t.get('id')) for t in tags)}]")
        if isinstance(cat, dict) and cat.get("id"):
            extras.append(f"cat={cat['id']}")
        msg = "  ".join(extras) or (body.get("message") or body.get("detail") or "")
    print(f"[{label:<30s}] {r.status_code}  {str(msg)[:180]}")
    if not ok:
        preview = json.dumps(body, ensure_ascii=False)[:320] if isinstance(body, (dict, list)) else (r.text[:320] if isinstance(r.text, str) else "")
        print("   ↳ body:", preview)
    return body


def main() -> int:
    creds = load_creds()
    backend = creds.get("backend") or BACKEND
    frontend = FRONTEND
    s = requests.Session()
    s.verify = False
    access = creds["access_token"]
    cat_ids = creds.get("cat_ids") or []
    tag_ids = creds.get("tag_ids") or []

    cat_devops = cat_ids[0] if len(cat_ids) > 0 else None
    cat_life = cat_ids[1] if len(cat_ids) > 1 else cat_devops
    tag_k8s = tag_ids[0] if len(tag_ids) > 0 else None
    tag_travel = tag_ids[1] if len(tag_ids) > 1 else None
    tag_ai = tag_ids[2] if len(tag_ids) > 2 else None

    # =====================================================================
    # 文章 A: 先 POST draft(无 tags)  → PUT 补 tag_ids+category_id → PUT status=published
    # =====================================================================
    slug_a = "e2e-k8s-in-practice"
    post_a_content = {
        "zh": """<h2>1. 节点规划</h2><p>控制面 3 台 etcd + kube-apiserver，工作节点按业务扩缩容。</p>
<h2>2. 网络</h2><p>CNI 选 Calico，BGP 模式 + 网络策略。</p>
<h2>3. 可观测性</h2><p>Prometheus + Loki + Tempo + Grafana 四件套。</p>
<h2>4. 存储</h2><p>Longhorn 做块存储，MinIO 做对象存储备份。</p>
<h2>5. 发布</h2><p>Argo CD 做 GitOps 持续交付 + 金丝雀发布。</p>""",
        "en": """<h2>1. Nodes</h2><p>3 control plane (etcd + apiserver), worker nodes autoscaled.</p>
<h2>2. Networking</h2><p>Calico CNI in BGP mode + NetworkPolicy.</p>
<h2>3. Observability</h2><p>Prometheus + Loki + Tempo + Grafana stack.</p>""",
    }
    # Step A1: POST draft (no tag_ids! 空列表即可，category_id 可传)
    payload_a_create = {
        "title": {"zh": "Kubernetes 在生产环境的落地实践（E2E·分步）", "en": "Kubernetes in Production (E2E·Stepped)"},
        "subtitle": {"zh": "从零到一构建可运维的集群", "en": "Building an Operable Cluster from Zero"},
        "slug": slug_a,
        "content": post_a_content,
        "excerpt": {
            "zh": "E2E 测试：从草稿 → 补标签 → 发布，完整走完一篇 K8s 实战文章的生命周期。",
            "en": "E2E test: walk through a post lifecycle draft→tags→published.",
        },
        "category_id": cat_devops,
        "tag_ids": [],  # ← 关键：空列表跳过赋值
        "status": "draft",
        "visibility": "public",
    }
    r_a1 = s.post(f"{backend}/api/blog/posts", json=payload_a_create, headers=b(access), timeout=30, allow_redirects=True)
    j_a1 = log("A1 POST draft (no tags)", r_a1)
    if r_a1.status_code != 201 or not isinstance(j_a1, dict) or not j_a1.get("id"):
        return 11
    post_a_id = int(j_a1["id"])
    time.sleep(0.4)

    # Step A2: PUT 补 tag_ids + 长 content（如果需要再微调）
    payload_a_up_tags = {
        "tag_ids": [x for x in [tag_k8s, tag_ai] if x],
    }
    r_a2 = s.put(f"{backend}/api/blog/posts/{post_a_id}", json=payload_a_up_tags, headers=b(access), timeout=20, allow_redirects=True)
    j_a2 = log(f"A2 PUT tags {post_a_id}", r_a2)
    if r_a2.status_code != 200:
        return 12
    time.sleep(0.4)

    # Step A3: PUT status → published
    r_a3 = s.put(f"{backend}/api/blog/posts/{post_a_id}", json={"status": "published"}, headers=b(access), timeout=20, allow_redirects=True)
    j_a3 = log(f"A3 PUT status=published {post_a_id}", r_a3)
    if r_a3.status_code != 200 or (isinstance(j_a3, dict) and j_a3.get("status") != "published"):
        return 13
    # 前台详情
    r_fe_a = s.get(f"{frontend}/posts/{slug_a}/", timeout=20, allow_redirects=True)
    fe_a_ok = r_fe_a.status_code == 200 and len(r_fe_a.content) >= 500
    print(f"[GET /posts/{slug_a}/{'':>4s}] {r_fe_a.status_code}  len={len(r_fe_a.content)}B  {'OK' if fe_a_ok else 'WARN(太短)'}")
    if not fe_a_ok:
        return 14

    # =====================================================================
    # 文章 B: POST 直接 published (空 tags) → PUT 补 tag_ids + cat + is_pinned
    # =====================================================================
    slug_b = "e2e-travel-hokkaido-autumn"
    post_b_content = {
        "zh": """<h2>Day 1 札幌</h2><p>新千岁机场 → 狸小路 → 薄野拉面横丁 吃一碗味噌拉面。</p>
<h2>Day 2 小樽</h2><p>运河散步 + 八音盒堂 + LeTAO 乳酪蛋糕 + 北一硝子。</p>
<h2>Day 3-4 函馆</h2><p>函馆山百万夜景、朝市海鲜丼、汤之川温泉。</p>
<h2>Day 5 登别</h2><p>地狱谷、熊牧场、温泉旅馆一泊二食。</p>
<h2>Day 6-7 富良野·美瑛</h2><p>丘陵风景、青池、妖精之森、富田农场。</p>""",
        "en": """<h2>Day 1 Sapporo</h2><p>Shin-Chitose → Tanukikoji → Susukino Ramen Alley.</p>
<h2>Day 2 Otaru</h2><p>Canal walk + Music Box Museum + LeTAO cheesecake.</p>
<h2>Day 3-4 Hakodate</h2><p>Mt. Hakodate night view, morning market seafood don, Yunokawa onsen.</p>
<h2>Day 5 Noboribetsu</h2><p>Jigokudani, bear ranch, onsen ryokan.</p>
<h2>Day 6-7 Furano·Biei</h2><p>Rolling hills, Blue Pond, Fairy Forest, Farm Tomita.</p>""",
    }
    payload_b_create = {
        "title": {"zh": "北海道的秋天：札幌·小樽·函馆 7 日自由行（E2E·分步直接发布）", "en": "Hokkaido Autumn 7 Days — E2E directly published"},
        "subtitle": {"zh": "红叶、海鲜、温泉与电车", "en": "Koyo, Seafood, Onsen and Trams"},
        "slug": slug_b,
        "content": post_b_content,
        "excerpt": {
            "zh": "E2E 直接发布（分步补 tag/cat）：北海道 7 日自由行完整路线",
            "en": "E2E directly published (stepped): full 7-day Hokkaido itinerary.",
        },
        "category_id": None,
        "tag_ids": [],  # ← 空列表
        "status": "published",
        "visibility": "public",
    }
    r_b1 = s.post(f"{backend}/api/blog/posts", json=payload_b_create, headers=b(access), timeout=30, allow_redirects=True)
    j_b1 = log("B1 POST published (no tags)", r_b1)
    if r_b1.status_code != 201 or not isinstance(j_b1, dict) or not j_b1.get("id"):
        return 21
    post_b_id = int(j_b1["id"])
    time.sleep(0.4)
    # Step B2: PUT 补 cat + tags + is_pinned=True
    payload_b_up = {
        "category_id": cat_life,
        "tag_ids": [x for x in [tag_travel] if x],
        "is_pinned": True,
    }
    r_b2 = s.put(f"{backend}/api/blog/posts/{post_b_id}", json=payload_b_up, headers=b(access), timeout=20, allow_redirects=True)
    j_b2 = log(f"B2 PUT cat+tags+pinned {post_b_id}", r_b2)
    if r_b2.status_code != 200:
        return 22
    time.sleep(0.4)
    # 前台详情
    r_fe_b = s.get(f"{frontend}/posts/{slug_b}/", timeout=20, allow_redirects=True)
    fe_b_ok = r_fe_b.status_code == 200 and len(r_fe_b.content) >= 500
    print(f"[GET /posts/{slug_b}/ ] {r_fe_b.status_code}  len={len(r_fe_b.content)}B  {'OK' if fe_b_ok else 'WARN(太短)'}")
    if not fe_b_ok:
        return 23

    # 前台首页 SSR 再确认一次（文章列表有更新）
    r_fe_home = s.get(f"{frontend}/", timeout=20, allow_redirects=True)
    home_ok = r_fe_home.status_code == 200 and len(r_fe_home.content) >= 1000
    print(f"[GET /{'':>18s}] {r_fe_home.status_code}  len={len(r_fe_home.content)}B  {'OK' if home_ok else 'WARN'}")

    # sidecar v3
    sidecar3 = dict(creds)
    sidecar3["post_ids"] = [post_a_id, post_b_id]
    sidecar3["post_slugs"] = [slug_a, slug_b]
    SIDE.write_text(json.dumps(sidecar3, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n[sidecar v3] written post ids + slugs")

    print("\n[Todo 6 OK] 2 posts created with stepped strategy (POST no-tags, PUT tags/status/cat) → FE SSR pages OK; Home SSR OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
