#!/usr/bin/env python3
"""Rosetta API 对比分析脚本"""

import os
import re
import json
from pathlib import Path

BACKEND_DIR = Path(r"d:\WebProjects\Rosetta\backend")
FRONTEND_API_DIR = Path(r"d:\WebProjects\Rosetta\frontend\src\api")


def extract_routers_from_main():
    """从 main.py 提取 include_router 的 prefix 和 router 变量映射"""
    main_file = BACKEND_DIR / "main.py"
    content = main_file.read_text(encoding="utf-8")

    routers = []
    pattern = re.compile(
        r'app\.include_router\(\s*(\w+)\.router\s*,\s*prefix\s*=\s*["\']([^"\']+)["\']'
    )
    for match in pattern.finditer(content):
        var_name = match.group(1)
        prefix = match.group(2)
        routers.append({"var_name": var_name, "prefix": prefix})

    return routers


def map_var_to_file(var_name):
    """根据变量名映射到文件"""
    mapping = {
        "users": "users.py",
        "blog": "blog.py",
        "core": "core.py",
        "media": "media.py",
        "guestbook": "guestbook.py",
        "voting": "voting.py",
        "notification": "notification.py",
        "favorite": "favorite.py",
        "admin": "admin.py",
        "webhook": "webhook.py",
        "import_export": "import_export.py",
        "seo": "seo.py",
        "advanced": "advanced.py",
        "monitoring": "monitoring.py",
        "toc": "toc.py",
        "title": "title.py",
        "captcha": "captcha.py",
        "messages": "messages.py",
        "translate": "translate.py",
        "oobe": "oobe.py",
        "announcement": "announcement.py",
        "activity": "activity.py",
        "hero": "hero.py",
        "post_series": "post_series.py",
        "post_encryption": "post_encryption.py",
        "post_crypto": "post_crypto.py",
        "scheduled_posts": "scheduled_posts.py",
        "comment_reactions": "comment_reactions.py",
        "ranking": "ranking.py",
        "performance": "performance.py",
        "stats": "stats.py",
        "admin_logs": "admin_logs.py",
        "settings_groups": "settings_groups.py",
        "bing": "bing.py",
        "comments": "comments.py",
    }
    return mapping.get(var_name, f"{var_name}.py")


def extract_routes_from_file(file_path, prefix):
    """从 router 文件提取所有路由"""
    routes = []
    if not file_path.exists():
        print(f"WARNING: 文件不存在: {file_path}")
        return routes

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"WARNING: 读取文件失败 {file_path}: {e}")
        return routes

    pattern = re.compile(
        r'@router\.(get|post|put|delete|patch)\(\s*["\']([^"\']*)["\']',
        re.IGNORECASE,
    )

    for match in pattern.finditer(content):
        method = match.group(1).upper()
        path = match.group(2)

        if path and not path.startswith("/"):
            path = "/" + path

        full_url = prefix + path
        full_url = re.sub(r"/+", "/", full_url)
        routes.append({"method": method, "path": full_url, "source_file": file_path.name})

    return routes


def extract_all_backend_routes():
    """提取所有后端路由"""
    all_routes = []

    routers = extract_routers_from_main()
    for router_info in routers:
        var_name = router_info["var_name"]
        prefix = router_info["prefix"]
        file_name = map_var_to_file(var_name)
        file_path = BACKEND_DIR / "api" / file_name

        routes = extract_routes_from_file(file_path, prefix)
        all_routes.extend(routes)

    return all_routes


def extract_frontend_api_calls():
    """从前端 src/api 目录提取所有 API 调用"""
    all_calls = []

    ts_files = [
        "admin.ts", "auth.ts", "blog.ts", "client.ts", "comments.ts", "content.ts",
        "index.ts", "pages.ts", "schema-contract.ts", "schema-contract-activity.ts",
        "schema-contract-announcement.ts", "schema-contract-comment-reaction.ts",
        "schema-contract-hero.ts", "schema-contract-post-series.ts", "site.ts", "users.ts",
    ]

    api_methods = ["apiGet", "apiPost", "apiPut", "apiDelete", "apiPatch", "apiUpload"]
    method_map = {
        "apiGet": "GET",
        "apiPost": "POST",
        "apiPut": "PUT",
        "apiDelete": "DELETE",
        "apiPatch": "PATCH",
        "apiUpload": "POST",
    }

    for ts_file in ts_files:
        file_path = FRONTEND_API_DIR / ts_file
        if not file_path.exists():
            print(f"WARNING: 前端文件不存在: {file_path}")
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"WARNING: 读取文件失败 {file_path}: {e}")
            continue

        for api_method in api_methods:
            http_method = method_map[api_method]

            pattern_quote = re.compile(
                rf'{api_method}(?:<[^>]*>)?\(\s*["\']([^"\']+)["\']',
                re.MULTILINE,
            )
            for match in pattern_quote.finditer(content):
                path = match.group(1)

                if path.startswith("http"):
                    full_url = path
                else:
                    if not path.startswith("/"):
                        path = "/" + path
                    full_url = "/api" + path

                full_url = re.sub(r"/+", "/", full_url)

                all_calls.append({
                    "method": http_method,
                    "path": full_url,
                    "raw_path": path,
                    "source_file": ts_file,
                })

            pattern_template = re.compile(
                rf'{api_method}(?:<[^>]*>)?\(\s*`([^`]*)`',
                re.MULTILINE,
            )
            for match in pattern_template.finditer(content):
                raw_template = match.group(1)
                path = re.sub(r'\$\{[^}]*\}', '{param}', raw_template)

                if path.startswith("http"):
                    full_url = path
                else:
                    if not path.startswith("/"):
                        path = "/" + path
                    full_url = "/api" + path

                full_url = re.sub(r"/+", "/", full_url)

                all_calls.append({
                    "method": http_method,
                    "path": full_url,
                    "raw_path": raw_template,
                    "source_file": ts_file,
                })

    return all_calls


def normalize_path_for_match(path):
    """规范化路径用于匹配：把动态参数段替换为占位符"""
    parts = path.strip("/").split("/")
    normalized = []
    for part in parts:
        if re.match(r"^\{.*\}$", part):
            normalized.append("{param}")
        elif re.match(r"^\$\{.*\}$", part):
            normalized.append("{param}")
        elif re.match(r"^:\w+$", part):
            normalized.append("{param}")
        elif re.match(r"^\d+$", part):
            normalized.append("{param}")
        else:
            normalized.append(part)
    return "/" + "/".join(normalized) if normalized else "/"


def match_routes(backend_routes, frontend_calls):
    """匹配前后端路由"""
    backend_norm = {}
    for br in backend_routes:
        key = (br["method"], normalize_path_for_match(br["path"]))
        if key not in backend_norm:
            backend_norm[key] = []
        backend_norm[key].append(br)

    frontend_norm = {}
    for fc in frontend_calls:
        key = (fc["method"], normalize_path_for_match(fc["path"]))
        if key not in frontend_norm:
            frontend_norm[key] = []
        frontend_norm[key].append(fc)

    matched_keys = set(backend_norm.keys()) & set(frontend_norm.keys())
    backend_only_keys = set(backend_norm.keys()) - set(frontend_norm.keys())
    frontend_only_keys = set(frontend_norm.keys()) - set(backend_norm.keys())

    matched = len(matched_keys)

    frontend_only = []
    for key in frontend_only_keys:
        method, norm_path = key
        for call in frontend_norm[key]:
            frontend_only.append(call)

    backend_only = []
    for key in backend_only_keys:
        method, norm_path = key
        for route in backend_norm[key]:
            backend_only.append(route)

    frontend_only.sort(key=lambda x: (x["method"], x["path"]))
    backend_only.sort(key=lambda x: (x["method"], x["path"]))

    return frontend_only, backend_only, matched


def suggest_fix(call):
    """为前端独有的 API 调用建议修复方式（基于实际后端路由结构分析）"""
    path = call["path"]
    method = call["method"]
    raw = call.get("raw_path", path)

    suggestions = []
    fix_frontend = []
    fix_backend = []

    if "/hero-slides" in path:
        fix_frontend.append("路径命名不一致：前端用 hero-slides(破折号)，后端用 hero/slides(子路径)。应改为 /hero/slides")
    elif "/post-series" in path and "/post_series" not in path:
        fix_frontend.append("路径命名不一致：前端用 post-series，后端用 /series(无post前缀)。应改为 /series")
    elif "/core/announcements" in path:
        fix_frontend.append("多了 /core 前缀：后端 announcement.router prefix=/api，路径应是 /announcements 不带 /core")
    elif path.startswith("/api/admin/navigations"):
        fix_frontend.append("前缀不一致：navigations 在 core.py(prefix=/api) 不带 /admin。应改为 /api/navigations")
    elif path.startswith("/api/admin/pages/") or path == "/api/admin/pages":
        fix_frontend.append("前缀不一致：pages 在 core.py(prefix=/api) 不带 /admin。应改为 /api/pages")
    elif "/gallery/" in path:
        fix_backend.append("后端完全缺失 gallery 模块路由（media.py 没有 gallery），需新增画廊管理后端功能")
    elif "/admin/dashboard/stats" in path:
        fix_frontend.append("路径不一致：stats.router prefix=/api/admin，路由是 /stats。应改为 GET /api/admin/stats")
    elif "/admin/performance/metrics" in path:
        fix_frontend.append("后端无 /metrics 路由。performance.py 有 /performance/summary、/slow、/storage，三选一或后端新增 /metrics")
    elif "/admin/polls" in path:
        fix_frontend.append("前缀不一致：voting.router prefix=/api/voting。应改为 /api/voting/polls")
        if "/close" in path:
            fix_backend.append("voting.py 目前无 /polls/{id}/close 关闭投票接口，需后端新增")
    elif "/seo/config" in path:
        fix_backend.append("seo.py 目前只有 /robots.txt、/schema/*、/open-graph/*，完全缺失 /seo/config 读写接口")
    elif "/seo/sitemap/generate" in path:
        fix_backend.append("seo.py 目前缺失 sitemap 生成接口，blog.py 有 GET /blog/sitemap.xml 但无 POST 生成器")
    elif path == "/api/settings" or path.startswith("/api/settings/"):
        fix_frontend.append("路径不一致：settings_groups.router prefix=/api。GET 全量是 /api(空path)，单组是 /api/{group}，方法是 PATCH 不是 GET/PUT")
    elif path == "/api/admin/settings":
        fix_frontend.append("后端 settings_groups 不带 /admin 前缀，且方法是 PATCH /api/{group} 不是 PUT /api/admin/settings")
    elif "/activities" in path and "/admin/" not in path:
        if method == "POST":
            fix_backend.append("activity.py 公开接口只有 GET /activities，没有 POST（仅 /admin/activities 有 POST），需新增公开活动发布路由")
        if "/like" in path:
            fix_backend.append("activity.py 完全缺失 /activities/{id}/like 点赞路由，需后端新增")
    elif "/media/" in path and "/library/" not in path:
        fix_frontend.append("路径不一致：media.py 路由为 /media/library/{media_id} 不是 /media/{id}。应改用 /media/library/ 前缀")
    elif "/users/change-password" in path and "/me/" not in path:
        fix_frontend.append("路径不一致：users.py 有 POST /users/me/change-password，前端缺少 /me 前缀")
    elif "/admin/comments" in path and ("/approve" in path or "/reject" in path):
        if method == "PUT":
            fix_frontend.append("HTTP方法不一致：comments.py 中 approve/reject 是 POST 不是 PUT")
    elif "/admin/titles" in path:
        fix_frontend.append("路径不一致：title.router prefix=/api/admin。注意后端路由 /admin/titles(列表)、/admin/titles/{title_id}(单条)、/admin/users/{user_id}/title(设置称号)")

    if not fix_frontend and not fix_backend:
        if "/admin/" in path:
            generic = "检查后端 admin.py/stats.py/performance.py/import_export.py 是否遗漏此路由"
        elif "/blog/" in path:
            generic = "检查 blog.py 是否遗漏此路由"
        elif "/users/" in path:
            generic = "检查 users.py 是否遗漏此路由"
        elif "/comments" in path:
            generic = "检查 comments.py 或 admin.py 是否遗漏此路由"
        elif "/seo" in path:
            generic = "检查 seo.py 是否遗漏此路由"
        elif "/monitoring" in path:
            generic = "检查 monitoring.py 是否遗漏此路由"
        elif "/notifications" in path:
            generic = "检查 notification.py 是否遗漏此路由"
        elif "/favorites" in path:
            generic = "检查 favorite.py 是否遗漏此路由"
        elif "/voting" in path:
            generic = "检查 voting.py 是否遗漏此路由"
        elif "/webhooks" in path:
            generic = "检查 webhook.py 是否遗漏此路由"
        elif "/media/" in path:
            generic = "检查 media.py 是否遗漏此路由"
        else:
            generic = "检查后端对应 router 文件是否遗漏，或前端路径拼写错误"
        suggestions.append(generic)
    else:
        if fix_frontend:
            suggestions.append("【改前端】" + "；".join(fix_frontend))
        if fix_backend:
            suggestions.append("【加后端】" + "；".join(fix_backend))

    return "｜".join(suggestions)


def generate_report(backend_routes, frontend_calls, frontend_only, backend_only, matched):
    """生成 Markdown 报告"""
    report = []

    report.append("# Rosetta 项目前后端 API 缺口分析报告\n")

    report.append("## 概览统计\n")
    report.append(f"| 指标 | 数量 |")
    report.append(f"|------|------|")
    report.append(f"| 后端路由总数 | {len(backend_routes)} |")
    report.append(f"| 前端 API 调用数 | {len(frontend_calls)} |")
    report.append(f"| MATCHED (匹配成功) | **{matched}** |")
    report.append(f"| FRONTEND_ONLY (前端独有) | **{len(frontend_only)}** ← Bug 候选 |")
    report.append(f"| BACKEND_ONLY (后端独有) | {len(backend_only)} |")
    report.append("")

    report.append("---\n")

    report.append("## FRONTEND_ONLY（前端调用但后端不存在的 API）⚠️\n")
    report.append(f"> 共 **{len(frontend_only)}** 项，这些是 **Bug 候选**，需要逐一排查：实现后端路由或修正前端调用。\n")
    report.append("| # | Method | Path | 来源文件 | 修复建议 |")
    report.append("|---|--------|------|----------|----------|")

    for i, call in enumerate(frontend_only, 1):
        report.append(
            f"| {i} | {call['method']} | `{call['path']}` | {call['source_file']} | {suggest_fix(call)} |"
        )

    report.append("")

    report.append("---\n")

    report.append(f"## BACKEND_ONLY（后端有路由但前端未使用） 参考\n")
    report.append(f"> 共 **{len(backend_only)}** 项，仅供参考（可能是管理后台暂未使用、公开 API 等），不要求修复。\n")
    report.append("| # | Method | Path | 来源文件 |")
    report.append("|---|--------|------|----------|")

    for i, route in enumerate(backend_only[:100], 1):
        report.append(
            f"| {i} | {route['method']} | `{route['path']}` | {route['source_file']} |"
        )

    if len(backend_only) > 100:
        report.append(f"\n> （仅显示前 100 项，剩余 {len(backend_only) - 100} 项省略）")

    report.append("")

    return "\n".join(report)


def main():
    print("=" * 60)
    print("Rosetta API 对比分析")
    print("=" * 60)

    print("\n[1/4] 提取后端路由...")
    backend_routes = extract_all_backend_routes()
    print(f"  ✓ 后端路由总数: {len(backend_routes)}")

    print("\n[2/4] 提取前端 API 调用...")
    frontend_calls = extract_frontend_api_calls()
    print(f"  ✓ 前端 API 调用数: {len(frontend_calls)}")

    print("\n[3/4] 匹配对比...")
    frontend_only, backend_only, matched = match_routes(backend_routes, frontend_calls)
    print(f"  ✓ MATCHED: {matched}")
    print(f"  ✓ FRONTEND_ONLY: {len(frontend_only)}")
    print(f"  ✓ BACKEND_ONLY: {len(backend_only)}")

    print("\n[4/4] 生成报告...")
    report = generate_report(backend_routes, frontend_calls, frontend_only, backend_only, matched)

    output_file = Path(r"d:\WebProjects\Rosetta\api-gap-report.md")
    output_file.write_text(report, encoding="utf-8")
    print(f"  ✓ 报告已生成: {output_file}")

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)

    print("\n\n===== FRONTEND_ONLY 列表预览 =====")
    for i, call in enumerate(frontend_only[:30], 1):
        print(f"  {i}. [{call['method']}] {call['path']}  ({call['source_file']})")
    if len(frontend_only) > 30:
        print(f"  ... 剩余 {len(frontend_only) - 30} 项详见报告")


if __name__ == "__main__":
    main()
