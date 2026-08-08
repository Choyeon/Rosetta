{
    "title_zh": "Docker Compose 生产部署实战",
    "title_en": "Docker Compose Production Deployment Guide",
    "title_ja": "Docker Compose 本番デプロイ実践",
    "title_zh_hant": "Docker Compose 生產部署實戰",
    "excerpt_zh": "本文深入讲解 Docker Compose 在生产环境中的最佳实践，覆盖多阶段构建、健康检查、资源限制、日志配置、网络隔离、密钥管理等核心话题，助你构建稳定可扩展的容器化部署方案。",
    "excerpt_en": "Deep dive into Docker Compose production best practices: multi-stage builds, health checks, resource limits, logging, network isolation, and secrets management for reliable container deployments.",
    "excerpt_ja": "Docker Composeの本番環境ベストプラクティス：マルチステージビルド、ヘルスチェック、リソース制限、ログ設定、ネットワーク分離、シークレット管理を解説。",
    "excerpt_zh_hant": "本文深入講解 Docker Compose 在生產環境中的最佳實踐，覆蓋多階段構建、健康檢查、資源限制、日誌配置、網絡隔離、密鑰管理等核心話題，助你構建穩定可擴展的容器化部署方案。",
    "category_slug": "tools",
    "tag_slugs": ["docker", "linux", "performance", "security"],
    "cover_theme": "blue",
    "code_language": "yaml",
    "code_snippet": """version: "3.9"
services:
  web:
    build: { context: ., dockerfile: Dockerfile, target: production }
    image: registry.example.com/app:${TAG:-latest}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits: { cpus: "2.0", memory: 2G }
        reservations: { cpus: "0.5", memory: 512M }
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "5" }
    networks: [frontend, backend]
    secrets: [db_password]
    depends_on:
      db: { condition: service_healthy }
  db:
    image: postgres:16-alpine
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 10s
      timeout: 5s
      retries: 5
volumes: { pgdata: null }
networks: { frontend: null, backend: { internal: true } }
secrets: { db_password: { file: ./secrets/db_password.txt } }
""",
    "content_zh": "# Docker Compose 生产部署实战\n\n容器化部署已成为现代应用交付的标准方式，Docker Compose 能快速编排多服务架构，但生产环境需要更多稳定性保障措施。\n\n## 服务配置与资源限制\n\n为每个服务配置合理的 CPU 和内存限制，防止单点故障拖垮宿主机。配合 healthcheck 确保服务异常时自动重启。\n\n```yaml\n{code}\n```\n\n## 网络与安全隔离\n\n将数据库等内部服务放入 internal 网络，不对外暴露端口。敏感凭证通过 secrets 机制挂载，避免硬编码进镜像。\n\n| 配置项 | 开发环境 | 生产环境 | 推荐值 |\n|--------|---------|---------|--------|\n| restart | no | unless-stopped | 生产必开 |\n| healthcheck | 可选 | 必须 | 30s间隔/3次重试 |\n| resource limits | 无 | 必须 | CPU 2C/内存 2G |\n| logging driver | 默认 | json-file | max-size 10m |\n| network mode | bridge | 分frontend/backend | internal隔离DB |\n\n## 最佳实践\n\n使用多阶段构建减小镜像体积，结合 .dockerignore 排除无关文件，定期清理悬空镜像和卷。",
    "content_en": "# Docker Compose Production Deployment Guide\n\nContainerization is standard for modern delivery. Docker Compose simplifies multi-service orchestration but production demands extra safeguards.\n\n## Service Configuration and Resource Limits\n\nSet reasonable CPU/memory limits per service to prevent cascading failures. Pair with healthchecks to auto-restart unhealthy containers.\n\n```yaml\n{code}\n```\n\n## Network and Security Isolation\n\nPlace internal services on internal networks without exposed ports. Mount credentials via secrets instead of hardcoding in images.\n\n| Config Item | Development | Production | Recommended |\n|-------------|-------------|------------|-------------|\n| restart | no | unless-stopped | Enable in prod |\n| healthcheck | Optional | Required | 30s/3 retries |\n| resource limits | None | Required | 2C CPU/2G RAM |\n| logging driver | default | json-file | max-size 10m |\n| network mode | bridge | split networks | internal for DB |\n\n## Best Practices\n\nUse multi-stage builds to shrink image size, combine with .dockerignore, and regularly prune dangling images and volumes."
},
{
    "title_zh": "PostgreSQL 查询优化技巧",
    "title_en": "PostgreSQL Query Optimization Techniques",
    "title_ja": "PostgreSQL クエリ最適化テクニック",
    "title_zh_hant": "PostgreSQL 查詢優化技巧",
    "excerpt_zh": "深入掌握 PostgreSQL 查询优化的核心方法：从 EXPLAIN ANALYZE 执行计划解读，到索引类型选择（B-tree/GIN/BRIN）、统计信息更新、连接策略调整、分区表设计，全方位提升数据库查询性能。",
    "excerpt_en": "Master PostgreSQL optimization: EXPLAIN ANALYZE plans, choosing index types (B-tree/GIN/BRIN), updating statistics, tuning joins, and partitioned table design for maximum performance.",
    "excerpt_ja": "PostgreSQLクエリ最適化：EXPLAIN ANALYZEの読み方、インデックス種別選択、統計情報更新、結合戦略調整、パーティションテーブル設計。",
    "excerpt_zh_hant": "深入掌握 PostgreSQL 查詢優化的核心方法：從 EXPLAIN ANALYZE 執行計劃解讀，到索引類型選擇（B-tree/GIN/BRIN）、統計資訊更新、連接策略調整、分區表設計，全方位提升數據庫查詢性能。",
    "category_slug": "technology",
    "tag_slugs": ["postgresql", "performance", "algorithms", "linux"],
    "cover_theme": "indigo",
    "code_language": "sql",
    "code_snippet": """EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT o.order_id, o.created_at, u.username, sum(oi.quantity * oi.price) AS total
FROM orders o
JOIN users u ON o.user_id = u.user_id
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.created_at BETWEEN '2024-01-01' AND '2024-12-31'
GROUP BY o.order_id, o.created_at, u.username
HAVING sum(oi.quantity * oi.price) > 1000
ORDER BY total DESC
LIMIT 100;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_created_user
ON orders (created_at, user_id) INCLUDE (order_id);

ALTER TABLE orders SET (autovacuum_analyze_scale_factor = 0.01);
ANALYZE orders (order_id, user_id, created_at);

SET enable_hashjoin = off; SET enable_mergejoin = on;
EXPLAIN ANALYZE SELECT * FROM orders o JOIN users u ON o.user_id = u.user_id;
RESET enable_hashjoin; RESET enable_mergejoin;

SELECT schemaname, relname, indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE relname IN ('orders','order_items','users') ORDER BY idx_scan DESC;
""",
    "content_zh": "# PostgreSQL 查询优化技巧\n\n查询性能问题是后端开发的常见瓶颈，PostgreSQL 提供了丰富的诊断工具和优化手段，合理利用可实现数量级性能提升。\n\n## 执行计划诊断\n\n使用 EXPLAIN (ANALYZE, BUFFERS) 获取真实执行时间和缓冲区命中，重点关注全表扫描、Rows 估算偏差、Sort/Hash 溢出磁盘等信号。\n\n```sql\n{code}\n```\n\n## 索引设计与调优\n\n根据查询模式选择索引类型：等值查询用 B-tree、全文/数组用 GIN、时序有序数据用 BRIN。复合索引要注意列的顺序（区分度高的列在前）。\n\n| 场景 | 推荐索引类型 | 命中率 | 维护成本 |\n|------|------------|--------|----------|\n| 主键/外键等值 | B-tree | 极高 | 低 |\n| JSONB/数组包含 | GIN | 高 | 中 |\n| 时序范围查询 | BRIN | 中高 | 极低 |\n| 模糊查询前缀 | B-tree varchar_pattern_ops | 中 | 低 |\n| 多列过滤排序 | 复合B-tree | 高 | 中高 |\n\n## 最佳实践\n\n定期分析慢查询日志，关注 pg_stat_statements 的 mean_exec_time，大表用 CONCURRENTLY 建索引避免锁表。",
    "content_en": "# PostgreSQL Query Optimization Techniques\n\nQuery performance is a common backend bottleneck. PostgreSQL provides rich diagnostic tools and optimization levers delivering orders-of-magnitude improvements.\n\n## Execution Plan Diagnosis\n\nUse EXPLAIN (ANALYZE, BUFFERS) for real times and buffer hits. Watch for Seq Scans, row estimate deviations, Sort/Hash spills to disk.\n\n```sql\n{code}\n```\n\n## Index Design and Tuning\n\nChoose index types by pattern: B-tree for equality, GIN for JSONB/arrays, BRIN for ordered time-series. Order composite index columns by selectivity (highest first).\n\n| Scenario | Index Type | Hit Rate | Maint. Cost |\n|----------|-----------|----------|------------|\n| PK/FK equality | B-tree | Very High | Low |\n| JSONB/array contains | GIN | High | Medium |\n| Time range queries | BRIN | Medium-High | Very Low |\n| Prefix fuzzy search | B-tree varchar_pattern_ops | Medium | Low |\n| Multi-col filter+sort | Composite B-tree | High | Medium-High |\n\n## Best Practices\n\nRegularly analyze slow query logs, monitor mean_exec_time in pg_stat_statements, use CONCURRENTLY on large tables to avoid locking during index creation."
},
{
    "title_zh": "Redis 缓存设计模式",
    "title_en": "Redis Cache Design Patterns",
    "title_ja": "Redis キャッシュ設計パターン",
    "title_zh_hant": "Redis 緩存設計模式",
    "excerpt_zh": "系统讲解三种核心缓存模式：Cache-Aside（旁路缓存）一致性保障、Write-Through（写穿透）原子性保证、Write-Behind（写回）高吞吐异步写入，以及缓存击穿/穿透/雪崩解决方案。",
    "excerpt_en": "Three core caching patterns: Cache-Aside consistency, Write-Through atomic updates, Write-Behind async high-throughput writes, plus solutions for stampede, penetration, and avalanche.",
    "excerpt_ja": "3種のキャッシュパターン：Cache-Aside、Write-Through、Write-Behindの実装と適用シーン、キャッシュ問題対策まで。",
    "excerpt_zh_hant": "系統講解三種核心緩存模式：Cache-Aside（旁路緩存）一致性保障、Write-Through（寫穿透）原子性保證、Write-Behind（寫回）高吞吐異步寫入，以及緩存擊穿/穿透/雪崩解決方案。",
    "category_slug": "backend",
    "tag_slugs": ["redis", "performance", "python", "algorithms"],
    "cover_theme": "red",
    "code_language": "python",
    "code_snippet": """import redis, json, hashlib, random
from functools import wraps
from typing import Callable, Any

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

def cache_aside(ttl: int = 300, jitter: float = 0.1):
    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            k = f"c:{fn.__name__}:{hashlib.md5(str((args,sorted(kwargs.items()))).encode()).hexdigest()[:10]}"
            cached = r.get(k)
            if cached == "__NULL__": return None
            if cached is not None: return json.loads(cached)
            result = fn(*args, **kwargs)
            t = int(ttl * (1 + random.uniform(-jitter, jitter)))
            if result is None: r.setex(k, max(30, t//5), "__NULL__")
            else: r.setex(k, max(1, t), json.dumps(result, default=str))
            return result
        return wrapper
    return decorator

def write_through(key: str, value: Any, db_update: Callable, ttl: int = 300):
    pipe = r.pipeline()
    pipe.setex(key, ttl, json.dumps(value, default=str))
    try:
        db_update(value)
        pipe.execute()
    except Exception:
        pipe.reset(); raise

bg_queue: list[tuple[str, Any]] = []
def write_behind(key: str, value: Any):
    bg_queue.append((key, value))
    r.setex(key, 60, json.dumps(value, default=str))

def flush_bg(db_update: Callable):
    while bg_queue:
        k, v = bg_queue.pop(0)
        try: db_update(k, v)
        except Exception: bg_queue.insert(0, (k, v)); break

@cache_aside(ttl=600)
def get_product(pid: int):
    return {"id": pid, "name": f"Product {pid}", "price": 99.99}
""",
    "content_zh": "# Redis 缓存设计模式\n\n缓存是提升系统性能最有效的手段之一，但选择错误的模式或缺乏异常处理反而会引入不一致和稳定性问题。\n\n## Cache-Aside 旁路缓存\n\n读时先查缓存，miss 再查 DB 并回填；写时先更新 DB 再删除缓存（推荐删除而非更新，避免并发脏读）。实现简单但需处理击穿穿透雪崩。\n\n```python\n{code}\n```\n\n## Write-Through / Write-Behind\n\nWrite-Through 写缓存同时同步写 DB，原子性强但延迟高。Write-Behind 先写缓存，异步批量刷 DB，吞吐高但存在短窗口数据丢失风险。\n\n| 模式 | 一致性 | 读性能 | 写性能 | 适用场景 |\n|------|--------|--------|--------|---------|\n| Cache-Aside | 最终一致 | 高 | 中 | 读多写少 |\n| Write-Through | 强一致 | 高 | 低延迟差 | 一致性要求高 |\n| Write-Behind | 弱一致/最终 | 高 | 极高 | 日志/统计写多读少 |\n| Refresh-Ahead | 最终一致 | 极高 | 中 | 热点Key可预测 |\n\n## 最佳实践\n\n设置随机 TTL ±10% 防止雪崩，热点 Key 加互斥锁或逻辑过期防击穿，不存在的数据写空值防穿透。",
    "content_en": "# Redis Cache Design Patterns\n\nCaching is one of the most effective performance boosters, but wrong patterns without failure handling introduce inconsistency and instability.\n\n## Cache-Aside Pattern\n\nOn read, check cache first; on miss, query DB and backfill. On write, update DB then delete cache (delete preferred over update to avoid concurrent dirty reads). Simple but must handle stampede, penetration, avalanche.\n\n```python\n{code}\n```\n\n## Write-Through vs Write-Behind\n\nWrite-Through updates cache and DB synchronously with strong consistency but higher latency. Write-Behind writes cache first then flushes asynchronously in batches for maximum throughput but risks short data-loss windows.\n\n| Pattern | Consistency | Read Perf | Write Perf | Best For |\n|---------|------------|-----------|------------|----------|\n| Cache-Aside | Eventual | High | Medium | Read-heavy |\n| Write-Through | Strong | High | Low latency | Strict consistency |\n| Write-Behind | Weak/Eventual | High | Very High | Logging/stats write-heavy |\n| Refresh-Ahead | Eventual | Very High | Medium | Predictable hot keys |\n\n## Best Practices\n\nAdd +-10% random jitter to TTL against avalanches. Use mutex/logical expiration for hot keys against stampedes. Cache null values for non-existent keys against penetration."
},
{
    "title_zh": "Git 高级工作流",
    "title_en": "Advanced Git Workflows",
    "title_ja": "Git 高度なワークフロー",
    "title_zh_hant": "Git 高級工作流",
    "excerpt_zh": "全面掌握 Git 进阶操作：Interactive Rebase 整理提交历史、Cherry-pick 精挑细选移植提交、Bisect 二分查找回归 Bug 源头，配合 reflog 与 reset 拯救误操作。",
    "excerpt_en": "Master advanced Git: Interactive Rebase for history cleanup, Cherry-pick selective commit porting, Bisect binary-search bug regression hunting, reflog and reset recovery.",
    "excerpt_ja": "Git上級操作：Interactive Rebase、Cherry-pick、Bisectによるバグ特定、reflogとresetによる誤操作からの復旧。",
    "excerpt_zh_hant": "全面掌握 Git 進階操作：Interactive Rebase 整理提交歷史、Cherry-pick 精挑細選移植提交、Bisect 二分查找回歸 Bug 源頭，配合 reflog 與 reset 拯救誤操作。",
    "category_slug": "tools",
    "tag_slugs": ["git", "linux", "python", "typescript"],
    "cover_theme": "orange",
    "code_language": "bash",
    "code_snippet": """#!/usr/bin/env bash
set -euo pipefail

# 1. Interactive Rebase: squash最近5条WIP，reword命名
git rebase -i HEAD~5 <<EOF
pick   a1b2c3d feat: add login API
reword b3e4f5g fix typo in user model
squash c6h7i8j wip: add test cases
fixup  d9k0l1m fix lint issues
drop   e2n3o4p tmp debug log
EOF

# 2. Cherry-pick: 跨分支移植hotfix
git checkout release/2.0
git cherry-pick -x a1b2c3d
# 多个提交合入暂存区手动合并后一次性提交:
# git cherry-pick --no-commit b3e4f5g c6h7i8j
# git cherry-pick --continue / --abort

# 3. Bisect: 二分找引入Bug的提交
git bisect start
git bisect bad HEAD
git bisect good v1.8.0
git bisect run pytest tests/test_auth.py -x
# Output: a1b2c3d is the first bad commit
git bisect reset

# 4. Reflog救援
git reflog --date=iso | head -20
# git reset --hard HEAD@{3}

# 5. 批量修复作者信息
git filter-branch -f --env-filter '
if [ "$GIT_AUTHOR_EMAIL" = "old@example.com" ]; then
    export GIT_AUTHOR_NAME="Correct Name" GIT_AUTHOR_EMAIL="new@example.com"
    export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME" GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
fi
' HEAD
""",
    "content_zh": "# Git 高级工作流\n\n基础的 add/commit/push 只能满足日常协作，掌握进阶命令能精确控制版本历史、高效排查问题。\n\n## Interactive Rebase 整理历史\n\n通过 reword/squash/fixup/drop 指令重写提交序列，合并 WIP 提交、修正信息、删除调试代码，保持主分支提交历史清晰可读。\n\n```bash\n{code}\n```\n\n## Bisect 二分查 Bug\n\n当回归 Bug 不知何时引入时，Bisect 通过二分搜索自动找出首个坏提交。配合自动化测试脚本可零人工介入，几分钟定位问题。\n\n| 命令 | 作用 | 风险级别 | 推荐场景 |\n|------|------|---------|---------|\n| rebase -i | 重写历史 | 中（只改未推送分支） | 提交整理/MR前 |\n| cherry-pick | 移植提交 | 低（产生新hash） | 回移hotfix |\n| bisect | 二分查Bug | 极低（只读） | 回归Bug定位 |\n| reflog | 操作历史 | 零（只读） | 误操作救援 |\n| filter-branch | 批量改写 | 极高（改所有hash） | 作者信息修复 |\n\n## 最佳实践\n\n黄金原则：永远不要 rebase 已经推送到公共分支的提交。危险操作前先打 git tag backup-$(date +%Y%m%d) 保险标签。",
    "content_en": "# Advanced Git Workflows\n\nBasic add/commit/push handles daily collaboration. Advanced commands give precise history control and efficient debugging.\n\n## Interactive Rebase for Clean History\n\nUse reword/squash/fixup/drop directives to rewrite sequences: merge WIP commits, fix messages, remove debug code, keep main branch history clean.\n\n```bash\n{code}\n```\n\n## Bisect for Binary-Search Bug Hunting\n\nWhen regression appeared mysteriously, Bisect binary-searches the first bad commit. Combined with test scripts it finds the issue in minutes with zero manual effort.\n\n| Command | Purpose | Risk Level | Best For |\n|---------|---------|-----------|----------|\n| rebase -i | Rewrite history | Medium (local only) | Before merge request |\n| cherry-pick | Port commits | Low (new hashes) | Backport hotfixes |\n| bisect | Binary search | Very Low (read-only) | Regression hunting |\n| reflog | Op history | Zero (read-only) | Disaster recovery |\n| filter-branch | Bulk rewrite | Very High (hash change) | Author info fixes |\n\n## Best Practices\n\nGolden rule: never rebase pushed commits. Before destructive ops, tag safety net with git tag backup-$(date +%Y%m%d)."
},
{
    "title_zh": "CSS Container Queries 完全指南",
    "title_en": "Complete Guide to CSS Container Queries",
    "title_ja": "CSS Container Queries 完全ガイド",
    "title_zh_hant": "CSS Container Queries 完全指南",
    "excerpt_zh": "彻底掌握现代响应式 CSS：Container Queries 让组件基于父容器尺寸自适应（而非视口），配合 :has() 父选择器实现依赖后代状态的样式变化，彻底改变组件化响应式设计范式。",
    "excerpt_en": "Modern responsive CSS pillars: Container Queries for component-level responsiveness based on parent size (not viewport), plus :has() parent selector for ancestor styling based on descendants.",
    "excerpt_ja": "モダンCSSの2大レスポンシブ機能：親コンテナ寸法に応じるContainer Queries、子孫要素の状態で親をスタイルする:has()セレクタ。",
    "excerpt_zh_hant": "徹底掌握現代響應式 CSS：Container Queries 讓元件基於父容器尺寸自適應（而非視口），配合 :has() 父選擇器實現依賴後代狀態的樣式變化，徹底改變元件化響應式設計範式。",
    "category_slug": "frontend",
    "tag_slugs": ["css", "vue", "react", "performance"],
    "cover_theme": "cyan",
    "code_language": "vue",
    "code_snippet": """.card-wrapper { container-type: inline-size; container-name: productCard; }
.product-card {
  display: flex; flex-direction: column; padding: 1rem;
  border: 1px solid var(--border); border-radius: 12px; transition: all 0.2s;
}
.product-image { width: 100%; aspect-ratio: 4 / 3; }
.product-info { display: grid; grid-template-columns: 1fr; gap: 0.5rem; }
.product-title { font-size: 1rem; }
.product-price { font-weight: 700; color: var(--primary); }

@container productCard (min-width: 400px) {
  .product-card { flex-direction: row; gap: 1rem; }
  .product-image { width: 45%; aspect-ratio: 1 / 1; }
  .product-title { font-size: 1.125rem; }
}
@container productCard (min-width: 640px) {
  .product-card { padding: 1.5rem; }
  .product-info { grid-template-columns: 2fr 1fr; }
  .product-title { font-size: 1.25rem; grid-row: span 2; }
  .product-price { font-size: 1.5rem; align-self: end; }
}

.product-card:has(.out-of-stock) { opacity: 0.7; filter: grayscale(0.3); }
.product-card:has(input[type="checkbox"]:checked) {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary) 30%, transparent);
}
.product-wrapper:has(> .product-card:hover) .product-card:not(:hover) {
  transform: scale(0.98); opacity: 0.85;
}

.hero-title { font-size: clamp(1.5rem, 8cqi, 3rem); line-height: 1.1; }
.hero-cta { padding: 0.05cqw 0.2cqh; border-radius: 0.1cqh; }
""",
    "content_zh": "# CSS Container Queries 完全指南\n\n多年来响应式只能依赖媒体查询（基于视口），但组件化时代组件可能被放置在任意宽度区域。Container Queries + :has() 开启真正组件级响应式。\n\n## Container Queries 容器查询\n\n给父容器声明 container-type: inline-size，子元素即可用 @container 根据父容器宽度切换布局，搭配 cqw/cqh/cqi 容器相对单位，实现上下文自适应。\n\n```css\n{code}\n```\n\n## :has() 父选择器\n\n长久以来 CSS 只能祖先 → 后代单向选择，:has() 打破这个限制。根据子元素是否存在/状态设置祖先样式，实现悬停兄弟弱化、表单验证反馈、空状态样式等。\n\n| 特性 | 媒体查询 @media | 容器查询 @container | :has() 选择器 |\n|------|--------------|------------------|-------------|\n| 触发依据 | 视口尺寸 | 父容器尺寸 | 后代元素状态 |\n| 适用层级 | 页面级 | 组件级 | 任意祖先层级 |\n| 单位 | vw/vh/vmin | cqw/cqh/cqi | - |\n| 浏览器支持 | 全支持 | 现代浏览器 | Chrome/Safari/Firefox |\n\n## 最佳实践\n\n不要滥用 :has() 嵌套过深，避免 :has(*:hover) 这类全量匹配。容器查询配合 container-name 防多实例冲突。",
    "content_en": "# Complete Guide to CSS Container Queries\n\nFor years responsive relied on media queries (viewport-based), but components live in arbitrary widths. Container Queries + :has() deliver true component-level responsiveness.\n\n## Container Queries\n\nDeclare container-type: inline-size on parent; use @container in children to switch layout by parent width. Pair with cqw/cqh/cqi units for contextual adaptation.\n\n```css\n{code}\n```\n\n## The :has() Parent Selector\n\nCSS traditionally styled ancestors -> descendants one-way. :has() breaks the limit: style ancestors by descendant presence/state for hover-sibling-dim, form validation, empty-state styling.\n\n| Feature | @media | @container | :has() |\n|---------|--------|-----------|--------|\n| Trigger | Viewport size | Parent size | Descendant state |\n| Scope | Page-level | Component-level | Any ancestor |\n| Units | vw/vh/vmin | cqw/cqh/cqi | - |\n| Support | Universal | Modern evergreen | Chrome/Safari/Firefox |\n\n## Best Practices\n\nAvoid deeply nested :has() and universal :has(*:hover). Pair container queries with explicit container-name to prevent multi-instance collisions."
},
{
    "title_zh": "WebAssembly 入门：Rust 编译 WASM + JS 调用",
    "title_en": "Getting Started with WebAssembly: Rust to WASM + JS",
    "title_ja": "WebAssembly 入門：Rust → WASM + JS 呼び出し",
    "title_zh_hant": "WebAssembly 入門：Rust 編譯 WASM + JS 調用",
    "excerpt_zh": "从零搭建 Rust → WebAssembly 开发流程：wasm-pack 工具链、wasm-bindgen 类型绑定、JavaScript 同步/异步调用 WASM 函数、内存共享与 TypedArray 传递大数据，适合计算密集型任务移植到浏览器端。",
    "excerpt_en": "End-to-end Rust to WASM setup: wasm-pack toolchain, wasm-bindgen type bindings, JS sync/async invocation, TypedArray memory sharing for compute-heavy browser workloads.",
    "excerpt_ja": "Rust→WASM開発環境構築：wasm-pack、wasm-bindgen型バインディング、JSからの呼び出し、メモリ共有による大規模データ処理。",
    "excerpt_zh_hant": "從零搭建 Rust → WebAssembly 開發流程：wasm-pack 工具鏈、wasm-bindgen 類型綁定、JavaScript 同步/異步調用 WASM 函數、內存共享與 TypedArray 傳遞大數據。",
    "category_slug": "technology",
    "tag_slugs": ["webassembly", "rust", "javascript", "performance"],
    "cover_theme": "purple",
    "code_language": "rust",
    "code_snippet": """use wasm_bindgen::prelude::*;
use serde::{Serialize, Deserialize};
use web_sys::console;

#[derive(Serialize, Deserialize)]
pub struct MatrixResult { rows: usize, cols: usize, data: Vec<f64>, compute_ms: f64 }

#[wasm_bindgen(start)]
pub fn init() {
    console_error_panic_hook::set_once();
    console::log_1(&"[WASM] Matrix module loaded".into());
}

#[wasm_bindgen]
pub fn matrix_multiply(a_ptr: *mut f64, a_rows: usize, a_cols: usize, b_ptr: *mut f64, b_cols: usize) -> JsValue {
    use std::time::Instant;
    let t0 = Instant::now();
    let a = unsafe { std::slice::from_raw_parts(a_ptr, a_rows * a_cols) };
    let b = unsafe { std::slice::from_raw_parts(b_ptr, a_cols * b_cols) };
    let mut c = vec![0.0f64; a_rows * b_cols];
    for i in 0..a_rows {
        for k in 0..a_cols {
            let aik = a[i * a_cols + k];
            let rb = &b[k * b_cols..(k + 1) * b_cols];
            let rc = &mut c[i * b_cols..(i + 1) * b_cols];
            for j in 0..b_cols { rc[j] += aik * rb[j]; }
        }
    }
    let r = MatrixResult { rows: a_rows, cols: b_cols, data: c, compute_ms: t0.elapsed().as_secs_f64() * 1000.0 };
    serde_wasm_bindgen::to_value(&r).unwrap()
}

#[wasm_bindgen]
pub fn fibonacci_iter(n: u32) -> u64 {
    if n <= 1 { return n as u64; }
    let (mut prev, mut curr) = (0u64, 1u64);
    for _ in 2..=n { let next = prev.saturating_add(curr); prev = curr; curr = next; }
    curr
}

#[wasm_bindgen(js_name = "allocateFloat64Array")]
pub fn allocate_f64(len: usize) -> *mut f64 {
    let mut v = Vec::with_capacity(len);
    let p = v.as_mut_ptr();
    std::mem::forget(v);
    p
}
""",
    "content_zh": "# WebAssembly 入门：Rust 编译 WASM + JS 调用\n\n前端遇到图像/矩阵/密码学等 CPU 密集任务时，JS 性能成瓶颈。WebAssembly 让 Rust 代码编译为接近原生速度的字节码。\n\n## 工具链与基础绑定\n\n安装 wasm-pack 后，用 #[wasm_bindgen] 宏把 Rust 函数导出为 JS 可调用形式。复杂结构用 serde + serde_wasm_bindgen 序列化跨语言传递。\n\n```rust\n{code}\n```\n\n## JS 调用与内存共享\n\nWASM 内存是共享 ArrayBuffer，通过 TypedArray 视图直接读写比参数序列化快 10-100 倍。大数据时直接分配内存给 JS 端填充，再传指针和尺寸给 WASM。\n\n| 对比项 | 纯 JS | WASM (Rust) | 加速倍数 | 适用场景 |\n|--------|------|------------|---------|---------|\n| 矩阵乘法 1024x1024 | ~1800ms | ~85ms | ~21x | 3D/游戏/AI推理 |\n| Fibonacci(n=40) | ~980ms | ~8ms | ~120x | 数学计算 |\n| SHA-256 1MB | ~42ms | ~6ms | ~7x | 密码学/校验 |\n\n## 最佳实践\n\n适合计算密集型循环，不要做 DOM 操作。优先 TypedArray 共享内存而非大对象参数，发布构建用 wasm-opt 优化体积。",
    "content_en": "# Getting Started with WebAssembly: Rust to WASM + JS Interop\n\nFor CPU-heavy tasks like image/matrix/crypto in browser, JS hits performance limits. WASM compiles Rust to near-native bytecode running in every modern browser.\n\n## Toolchain and Basic Bindings\n\nInstall wasm-pack and use #[wasm_bindgen] to export Rust functions callable from JS. Complex structs cross via serde + serde_wasm_bindgen serialization.\n\n```rust\n{code}\n```\n\n## JS Invocation and Memory Sharing\n\nWASM memory is a shared ArrayBuffer; reading/writing through TypedArray views is 10-100x faster than serialization. Allocate from JS into WASM memory then pass pointers/sizes for large data.\n\n| Metric | Plain JS | WASM (Rust) | Speedup | Best For |\n|--------|----------|------------|---------|----------|\n| Matmul 1024x1024 | ~1800ms | ~85ms | ~21x | 3D/Games/AI |\n| Fibonacci(n=40) | ~980ms | ~8ms | ~120x | Math workloads |\n| SHA-256 1MB | ~42ms | ~6ms | ~7x | Crypto/Checksums |\n\n## Best Practices\n\nTarget compute-heavy loops, not DOM work. Prefer TypedArray memory sharing for large data over serialized parameters. Use wasm-opt on release builds to shrink binary size."
},
{
    "title_zh": "Astro 静态站点深度：群岛架构 & 内容集合",
    "title_en": "Astro Deep Dive: Islands Architecture & Content Collections",
    "title_ja": "Astro 静的サイト：アイランドアーキテクチャ & コンテンツコレクション",
    "title_zh_hant": "Astro 靜態站點深度：群島架構 & 內容集合",
    "excerpt_zh": "深入理解 Astro 核心创新：群岛架构实现最小化 JS 注入，仅交互组件按需水合；内容集合提供类型安全的 Markdown/MDX 管理，构建零 JS 的高性能静态站点。",
    "excerpt_en": "Astro innovations: Islands Architecture for minimal JS with partial hydration, Content Collections for type-safe Markdown/MDX management, ultra-fast zero-JS static sites.",
    "excerpt_ja": "Astroの革新：最小JSのアイランドアーキテクチャ、型安全なMarkdown/MDXのコンテンツコレクション、ゼロJSの高速静的サイト構築。",
    "excerpt_zh_hant": "深入理解 Astro 核心創新：群島架構實現最小化 JS 注入，僅交互元件按需水合；內容集合提供類型安全的 Markdown/MDX 管理，構建零 JS 的高性能靜態站點。",
    "category_slug": "frontend",
    "tag_slugs": ["astro", "javascript", "typescript", "performance"],
    "cover_theme": "teal",
    "code_language": "typescript",
    "code_snippet": """// src/content/config.ts
import { defineCollection, z } from 'astro:content';

const blog = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string().max(80),
    description: z.string().max(200),
    pubDate: z.coerce.date(),
    tags: z.array(z.string()).default([]),
    cover: z.object({ src: z.string(), alt: z.string() }).optional(),
    draft: z.boolean().default(false),
    category: z.enum(['tutorial','technology','essays','translation']),
  }),
});
const projects = defineCollection({
  type: 'content',
  schema: ({ image }) => z.object({
    name: z.string(), summary: z.string(),
    hero: image(), stack: z.array(z.string()),
    repo: z.string().url().optional(), live: z.string().url().optional(),
    featured: z.boolean().default(false),
  }),
});
export const collections = { blog, projects };

// src/pages/blog/[...slug].astro
/* ---
import { getCollection, type CollectionEntry } from 'astro:content';
import { Image } from 'astro:assets';
import LikeCounter from '../../components/LikeCounter.svelte';

export async function getStaticPaths() {
  const posts = await getCollection('blog', ({ data }) => import.meta.env.DEV || !data.draft);
  return posts.map(p => ({ params: { slug: p.slug }, props: { post: p } }));
}
const { post } = Astro.props as { post: CollectionEntry<'blog'> };
const { Content } = await post.render();
--- ---
<article>
  <header>
    <h1>{post.data.title}</h1>
    {post.data.cover && <Image src={post.data.cover.src} alt={post.data.cover.alt} widths={[400,800,1200]} />}
  </header>
  <Content />
  <LikeCounter client:idle postSlug={post.slug} />
</article>
*/
""",
    "content_zh": "# Astro 静态站点深度：群岛架构 & 内容集合\n\nAstro 默认零 JavaScript，核心是群岛架构（组件按需水合）和类型安全的内容集合，兼具极致性能和现代开发体验。\n\n## 群岛架构与水合策略\n\n非交互内容输出纯静态 HTML，只有标记 client:load/visible/idle/only 的组件才会加载 JS 并水合。同一页面可混合 React/Svelte/Vue 组件互不冲突。\n\n```typescript\n{code}\n```\n\n## Content Collections 类型安全\n\n在 content/config.ts 中用 Zod 为集合定义 schema，getCollection 返回内容时自动校验 frontmatter，不匹配直接报错。支持图片自动优化。\n\n| 水合指令 | 触发时机 | 体积开销 | 适合组件 |\n|---------|---------|---------|---------|\n| (默认) | 永远不水合 | 0 JS | 纯展示卡片/正文 |\n| client:load | 页面加载即水合 | 最高 | 导航/核心交互 |\n| client:idle | 浏览器空闲时 | 中低 | 点赞/次要交互 |\n| client:visible | 滚动进入视口 | 极低 | 页脚/长列表后项 |\n\n## 最佳实践\n\n默认先不写 client:*，确定需要交互再添加。内容集合 schema 严格化避免脏数据。用 getStaticPaths + Slug 预渲染所有动态路由。",
    "content_en": "# Astro Deep Dive: Islands Architecture & Content Collections\n\nAstro ships zero JS by default, powered by Islands Architecture (selective hydration) and type-safe Content Collections, delivering peak performance with modern DX.\n\n## Islands Architecture and Hydration Strategies\n\nNon-interactive content renders as pure static HTML. Only components with client:load/visible/idle/only fetch JS and hydrate. React/Svelte/Vue components coexist on same page independently.\n\n```typescript\n{code}\n```\n\n## Type-Safe Content Collections\n\nDefine Zod schemas per collection in content/config.ts. When calling getCollection, Astro validates frontmatter and throws at build time on invalid data. Built-in image optimization works through schemas.\n\n| Directive | Trigger Timing | Overhead | Best For |\n|-----------|---------------|----------|----------|\n| Default | Never hydrates | Zero JS | Static cards, body |\n| client:load | Immediate on load | Highest | Nav, core UI |\n| client:idle | After first idle | Medium-low | Likes, secondary |\n| client:visible | Enters viewport | Very Low | Footer, late items |\n\n## Best Practices\n\nStart without client:* directives - add only after proving interactivity needed. Enforce strict collection schemas to avoid data drift. Pre-render every dynamic route via getStaticPaths + slug pattern."
},
{
    "title_zh": "Node.js 性能诊断：clinic.js + flamegraph",
    "title_en": "Node.js Performance Diagnostics: clinic.js & Flamegraphs",
    "title_ja": "Node.js 性能診断：clinic.js + フレームグラフ",
    "title_zh_hant": "Node.js 性能診斷：clinic.js + flamegraph",
    "excerpt_zh": "系统学习 Node.js 性能定位工具链：clinic.js 一键生成分析报告，解读火焰图热点函数、阻塞事件循环的同步代码、内存泄漏对象栈，精准定位 CPU/内存瓶颈。",
    "excerpt_en": "Node.js performance diagnostics: clinic.js one-click reports, reading flamegraphs for hot functions, event-loop blockers, memory leak stacks to pinpoint CPU/memory bottlenecks.",
    "excerpt_ja": "Node.js性能調査：clinic.jsレポート生成、フレームグラフ読解でホット関数、イベントループブロッカー、メモリリークを特定。",
    "excerpt_zh_hant": "系統學習 Node.js 性能定位工具鏈：clinic.js 一鍵生成分析報告，解讀火焰圖熱點函數、阻塞事件循環的同步代碼、內存洩漏對象棧，精準定位 CPU/內存瓶頸。",
    "category_slug": "backend",
    "tag_slugs": ["nodejs", "performance", "javascript", "linux"],
    "cover_theme": "green",
    "code_language": "bash",
    "code_snippet": """#!/usr/bin/env bash
set -euo pipefail

# 1. 安装工具链
# npm i -g clinic 0x autocannon

# 2. Clinic Doctor: 一键综合体检 (自动压测20s)
# clinic doctor --on-port 'autocannon -c 50 -d 20 http://localhost:$PORT/api/search?q=test' -- node dist/server.js

# 3. 火焰图定位 CPU 热点（0x 工具）
# 0x -- node dist/server.js &  sleep 2
# autocannon -c 80 -d 15 http://localhost:3000/api/heavy
# Ctrl+C → flamegraph.html

# 4. Clinic Bubbleprof: 异步延迟分析（Promise/IO等待链条）
# clinic bubbleprof --on-port 'autocannon -c 30 -d 15 http://localhost:$PORT/api/upload' -- node dist/server.js

# 5. Clinic Heapprofiler: 堆内存泄漏（300s采样对比快照）
# clinic heapprofiler --sample-interval 1000 --on-port 'autocannon -c 40 -d 300 http://localhost:$PORT/api/cart' -- node dist/server.js

# 6. V8 底层采样（无侵入生产可用）
NODE_ENV=production node --prof dist/server.js &
SPID=$!; sleep 3
autocannon -c 100 -d 30 http://localhost:3000/api/heavy
kill -INT $SPID
# node --prof-process isolate-0x*-v8.log > processed.txt
# 查看 [Bottom up (heavy) profile] 部分
""",
    "content_zh": "# Node.js 性能诊断：clinic.js + flamegraph\n\nNode.js 异步模型让性能定位比传统语言更具挑战：事件循环阻塞、Promise 链等待、内存泄漏都需要专门工具链。clinic.js 是最易用的一站式诊断套件。\n\n## 火焰图：从宽度看耗时\n\n火焰图每一格代表一个函数栈帧，宽度代表占用 CPU 的采样数。平而宽的顶层栈帧就是热点函数；向上生长的尖刺通常是深层递归或同步 IO；找\"平顶\"最值得优化。\n\n```bash\n{code}\n```\n\n## Clinic.js 三大子工具分工\n\nDoctor 做全局体检，给出阻塞/泄漏概率评分和建议；Bubbleprof 专注异步调用链气泡图；Heapprofiler 生成堆采样时间序列，对比不同时间对象增长。\n\n| 工具 | 分析维度 | 开销 | 输出格式 | 最擅长 |\n|------|---------|------|---------|--------|\n| clinic doctor | CPU/内存/事件循环 | 低(<5%) | 单页HTML报告 | 首诊定位方向 |\n| 0x flamegraph | CPU栈时间占比 | 低 | 交互式SVG | 找CPU热点函数 |\n| clinic bubbleprof | 异步调用链延迟 | 中 | 交互式气泡图 | Promise/回调等待 |\n| clinic heapprofiler | 堆对象增长曲线 | 中 | 交互式堆分析 | 内存泄漏定位 |\n| --prof-process | V8底层统计 | 极低 | 文本报告 | 对比版本差异 |\n\n## 最佳实践\n\n先 doctor 扫全局再针对性深挖。压测流量必须贴近真实请求分布，否则误判。基线数据先存一份，优化后再跑对比。",
    "content_en": "# Node.js Performance Diagnostics: clinic.js & Flamegraphs\n\nNode's async model makes debugging trickier than traditional languages. clinic.js is today's most user-friendly one-stop diagnostic suite for event-loop, promise, and memory issues.\n\n## Reading Flamegraphs: Width Equals Time\n\nEach flamegraph box is a stack frame. Width equals CPU samples. Wide, flat top frames are hotspots. Tall upward spikes hint at deep recursion or sync IO. Seek the \"flat tops\" for lowest-hanging fruit.\n\n```bash\n{code}\n```\n\n## Three Clinic.js Sub-tools\n\nDoctor runs a full health check with scores and fix suggestions. Bubbleprof visualizes async call chains. Heapprofiler samples heap allocation over time and compares object-type growth rates.\n\n| Tool | Dimension | Overhead | Output | Best At |\n|------|-----------|----------|--------|---------|\n| clinic doctor | CPU/mem/event loop | Low (<5%) | Single HTML | First-pass triage |\n| 0x flamegraph | CPU stack share | Low | Interactive SVG | CPU hotspots |\n| clinic bubbleprof | Async latency | Medium | Interactive bubbles | Promise waits |\n| clinic heapprofiler | Heap growth timeline | Medium | Interactive heap | Memory leaks |\n| --prof-process | V8 raw stats | Very Low | Text report | Version diffs |\n\n## Best Practices\n\nStart with Doctor for a global scan then drill. Load-test traffic must reflect production distributions to avoid skewed conclusions. Capture baselines first; compare post-optimization runs."
},
{
    "title_zh": "Python 并发：asyncio vs ThreadPool vs ProcessPool",
    "title_en": "Python Concurrency: asyncio vs ThreadPool vs ProcessPool",
    "title_ja": "Python 並行処理：asyncio vs ThreadPool vs ProcessPool",
    "title_zh_hant": "Python 併發：asyncio vs ThreadPool vs ProcessPool",
    "excerpt_zh": "深度对比 Python 三大并发模型：GIL 限制下的线程池（IO 密集）、进程池（绕 GIL 适合 CPU 密集）、asyncio 协程（超高并发 IO）。从原理/性能/复杂度四维度给出选型决策树。",
    "excerpt_en": "Deep Python concurrency comparison: ThreadPool for IO-bound, ProcessPool bypassing GIL for CPU-bound, asyncio coroutines for ultra IO. 4-dimension decision tree with perf and complexity.",
    "excerpt_ja": "Pythonの3大並行モデル徹底比較：GIL下のThreadPool、GIL回避のProcessPool、超高IO向けasyncio。性能と複雑性の4次元デシジョンツリー。",
    "excerpt_zh_hant": "深度對比 Python 三大併發模型：GIL 限制下的線程池（IO 密集）、進程池（繞 GIL 適合 CPU 密集）、asyncio 協程（超高併發 IO）。從原理/性能/複雜度四維度給出選型決策樹。",
    "category_slug": "tutorial",
    "tag_slugs": ["python", "performance", "algorithms"],
    "cover_theme": "emerald",
    "code_language": "python",
    "code_snippet": """import asyncio, time, requests, httpx
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List

URLS = [f"https://jsonplaceholder.typicode.com/posts/{i}" for i in range(1, 51)]

def fetch_sync(url: str) -> dict:
    return requests.get(url, timeout=10).json()

async def fetch_async(client, url: str) -> dict:
    r = await client.get(url, timeout=10.0)
    return r.json()

def run_threadpool(urls, maxw=20):
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=maxw) as ex:
        fs = [ex.submit(fetch_sync, u) for u in urls]
        results = [f.result() for f in as_completed(fs)]
    print(f"[ThreadPool] {len(results)} tasks, {time.perf_counter()-t0:.2f}s")

def cpu_heavy(n):
    sieve = [True]*(n+1); sieve[0]=sieve[1]=False
    for i in range(2, int(n**0.5)+1):
        if sieve[i]: sieve[i*i::i] = [False]*len(sieve[i*i::i])
    return sum(sieve)

def run_processpool(args):
    t0 = time.perf_counter()
    with ProcessPoolExecutor() as ex:
        results = list(ex.map(cpu_heavy, args))
    print(f"[ProcessPool] sum={sum(results)}, {time.perf_counter()-t0:.2f}s")

async def run_asyncio(urls):
    t0 = time.perf_counter()
    async with httpx.AsyncClient() as client:
        tasks = [fetch_async(client, u) for u in urls]
        results = await asyncio.gather(*tasks)
    print(f"[asyncio] {len(results)} tasks, {time.perf_counter()-t0:.2f}s")

if __name__ == "__main__":
    run_threadpool(URLS)
    run_processpool([100000]*8)
    asyncio.run(run_asyncio(URLS))
""",
    "content_zh": "# Python 并发：asyncio vs ThreadPool vs ProcessPool\n\n由于全局解释器锁（GIL）的存在，Python 并发性选择常让人困惑。IO 密集和 CPU 密集场景需要完全不同的模型，选错会让性能不升反降。\n\n## 三大模型原理与代码\n\n线程池提交阻塞函数到系统线程，GIL 在 IO 等待时释放，并发 10-50；进程池子进程彻底绕 GIL，适合 CPU 任务但传参有序列化开销；asyncio 单线程调度协程，适合超大量轻量 IO。\n\n```python\n{code}\n```\n\n## 选型决策与性能对比\n\n纯 CPU 运算 → ProcessPool；网络/文件 IO → asyncio 或 ThreadPool；混合场景 → asyncio.run_in_executor 把 CPU 任务扔进程池，IO 走协程。\n\n| 对比维度 | ThreadPool | ProcessPool | asyncio |\n|---------|-----------|------------|----------|\n| 原理 | 多线程共享GIL | 多进程独立GIL | 单线程事件循环+协程 |\n| GIL影响 | IO时释放/CPU无效 | 完全无 | 单线程无竞争 |\n| 50HTTP请求 | ~5-8s | ~40s(启动慢) | ~1.5-3s |\n| 8个CPU素数 | ~45s(串行) | ~7s(多核) | ~40s(单线程) |\n| 最大并发规模 | 数百 | CPU核心×2 | 数千~数万 |\n| 改造成本 | 低 | 中(可pickle) | 高(全链路async) |\n\n## 最佳实践\n\nIO 优先 asyncio，第三方库全同步才退用 ThreadPool。CPU 直接多进程，进程数不超过核心数 1-2 倍。",
    "content_en": "# Python Concurrency: asyncio vs ThreadPool vs ProcessPool\n\nThe GIL makes Python concurrency confusing. IO-bound and CPU-bound workloads demand different models - pick wrong and performance worsens.\n\n## Three Models and Code\n\nThreadPool submits blocking calls; GIL releases on IO waits (10-50 workers). ProcessPool uses subprocesses to evade GIL for CPU work (serialization overhead). asyncio schedules coroutines on one thread for massive light IO concurrency.\n\n```python\n{code}\n```\n\n## Decision Framework and Benchmarks\n\nPure CPU math → ProcessPool. Network/file IO → asyncio or ThreadPool. Mixed → asyncio.run_in_executor offloads CPU to pool while IO stays in coroutines.\n\n| Dimension | ThreadPool | ProcessPool | asyncio |\n|-----------|-----------|------------|----------|\n| Principle | Multi-thread shared GIL | Multi-process, own GIL | Single-thread loop + coroutines |\n| GIL impact | Released on IO / useless on CPU | No GIL at all | No contention |\n| 50 HTTP reqs | ~5-8s | ~40s (fork slow) | ~1.5-3s |\n| 8 CPU primes | ~45s (serial) | ~7s (multi-core) | ~40s (single) |\n| Max concurrency | Hundreds | Cores × 2 | Thousands+ |\n| Migration cost | Low | Medium (pickle) | High (full async chain) |\n\n## Best Practices\n\nPrefer asyncio for IO first; fall to ThreadPool if dependencies synchronous. Use ProcessPool for CPU tasks and cap workers at 1-2 × core count."
},
{
    "title_zh": "Rust 所有权与借用机制：彻底理解生命周期",
    "title_en": "Rust Ownership & Borrowing: Lifetimes Explained",
    "title_ja": "Rust 所有権と借用：ライフタイム完全理解",
    "title_zh_hant": "Rust 所有權與借用機制：徹底理解生命週期",
    "excerpt_zh": "系统攻克 Rust 最独特概念：所有权规则、可变/不可变借用约束、引用生命周期标注。通过编译错误示例 + 修复方案，彻底掌握借用检查器思维方式，写出安全零抽象开销的系统代码。",
    "excerpt_en": "Master Rust's most unique concepts: ownership rules, mutable/immutable borrowing constraints, lifetime annotations. Compile-error examples + fixes to think like the Borrow Checker for safe zero-cost code.",
    "excerpt_ja": "Rustの最難解概念をマスター：所有権ルール、可変/不変借用の制約、ライフタイム注釈。コンパイルエラー例と修正を通してBorrow Checkerの思考法を習得。",
    "excerpt_zh_hant": "系統攻克 Rust 最獨特概念：所有權規則、可變/不可變借用約束、引用生命週期標註。通過編譯錯誤示例 + 修復方案，徹底掌握借用檢查器思維方式，寫出安全零抽象開銷的系統代碼。",
    "category_slug": "technology",
    "tag_slugs": ["rust", "performance", "algorithms", "linux"],
    "cover_theme": "amber",
    "code_language": "rust",
    "code_snippet": """use std::collections::HashMap;

#[derive(Debug, Clone)]
struct User { id: u32, username: String, profile: Option<Box<User>> }

struct UserCache<'a> {
    users: HashMap<u32, User>,
    last_accessed: Option<&'a User>,
}

impl<'a> UserCache<'a> {
    fn new() -> Self { Self { users: HashMap::new(), last_accessed: None } }
    fn insert(&mut self, user: User) { self.users.insert(user.id, user); }
    fn get(&'a mut self, id: u32) -> Option<&'a User> {
        if let Some(u) = self.users.get(&id) {
            self.last_accessed = Some(u);
            self.last_accessed
        } else { None }
    }
}

fn longest_str<'a>(x: &'a str, y: &'a str) -> &'a str { if x.len() >= y.len() { x } else { y } }

struct Parser<'s, 'b> where 's: 'b { source: &'s str, buffer: &'b mut [u8] }

impl<'s, 'b> Parser<'s, 'b> where 's: 'b {
    fn new(source: &'s str, buffer: &'b mut [u8]) -> Self { Self { source, buffer } }
}

fn main() {
    let s1 = String::from("hello");
    let s2 = s1.clone();
    println!("s1={s1}, s2={s2}");
    let a = String::from("short"); let b = String::from("longest string wins");
    println!("longest: {}", longest_str(&a, &b));
    let mut cache = UserCache::new();
    cache.insert(User { id: 1, username: "rosetta".into(), profile: None });
    let u = cache.get(1);
    println!("Got user: {:?}", u.map(|x| &x.username));
    let mut buf = vec![0u8; 1024];
    let p = Parser::new("input", buf.as_mut_slice());
    println!("Parser source len: {}", p.source.len());
}
""",
    "content_zh": "# Rust 所有权与借用机制：彻底理解生命周期\n\nRust 不用 GC 却能保证内存安全，核心武器是所有权系统和借用检查器。编译期检查内存访问合法性，运行时零开销，但理解门槛是主流语言中最高的。\n\n## 三大所有权铁律\n\n1）每个值有且仅有一个所有者；2）所有者离开作用域，值立即被 drop；3）同一值最多只能有一个可变引用，可变和不可变引用不能同时存在。几乎所有初学生命周期错误都是违背第3条。\n\n```rust\n{code}\n```\n\n## 生命周期标注与约束\n\n当函数/结构体中出现引用时，Rust 需要显式生命周期标注（'a、'b）告知编译器引用有效期关系。's: 'b 表示 's 存活时间不短于 'b，常见于结构体自引用场景。\n\n| 常见错误 | 本质 | 修复模式 |\n|---------|------|---------|\n| use of moved value | 所有权被转移 | .clone()/用&borrow |\n| cannot borrow X mutable+immutable | 违反借用规则 | 缩小作用域/分块 |\n| missing lifetime specifier | 编译器推不出 | 加'a关联输入输出 |\n| lifetime may not live long enough | 引用先被释放 | 延长作用域/改用拥有所有权类型 |\n\n## 最佳实践\n\n写代码初期全用拥有所有权类型（String/Vec/Box），编译通过后再按需改为引用。不要过早纠结生命周期标注，让编译器给你驱动式修改建议。",
    "content_en": "# Rust Ownership & Borrowing: Lifetimes Thoroughly Explained\n\nRust guarantees memory safety without a GC, powered by ownership and borrow checker. Validates legality at compile time with zero runtime cost but steepest learning curve.\n\n## Three Iron Ownership Rules\n\n(1) Every value has exactly one owner. (2) When owner leaves scope value is dropped. (3) A value can have either one mutable reference OR any immutable references - never both at once. Most beginner lifetime errors violate #3.\n\n```rust\n{code}\n```\n\n## Lifetime Annotations and Bounds\n\nWhen functions/structs contain references, Rust needs explicit labels ('a, 'b) expressing validity relationships. Bound 's: 'b means lifetime 's outlives 'b - common in self-referential structs.\n\n| Common Error | Root Cause | Fix Pattern |\n|--------------|-----------|-------------|\n| use of moved value | Ownership transferred already | .clone() or borrow with & |\n| cannot borrow X as mutable + immutable | Borrow rule violated | Narrow scopes / split blocks |\n| missing lifetime specifier | Compiler can't infer relation | Add 'a tying inputs/outputs |\n| lifetime may not live long enough | Referenced value dropped earlier | Extend scope / owning types |\n\n## Best Practices\n\nFirst versions use owning types everywhere (String/Vec/Box). After passing, convert parameters to references. Don't chase lifetime annotations prematurely - let compiler errors drive incremental fixes."
},
{
    "title_zh": "Go 语言并发：goroutine + channel + sync.WaitGroup",
    "title_en": "Go Concurrency: Goroutines, Channels & sync.WaitGroup",
    "title_ja": "Go 言語並行：goroutine + channel + sync.WaitGroup",
    "title_zh_hant": "Go 語言併發：goroutine + channel + sync.WaitGroup",
    "excerpt_zh": "完整掌握 Go 原生并发模型：轻量级协程 goroutine（KB 级开销）、CSP 模式 channel 通信、sync.WaitGroup 生命周期管理，加上 Context 取消、工作池模式，以及 goroutine 泄漏防护。",
    "excerpt_en": "Complete Go native concurrency guide: lightweight goroutines, CSP-style channels, sync.WaitGroup, Context cancellation, worker pool patterns, and goroutine leak prevention.",
    "excerpt_ja": "Goのネイティブ並行完全ガイド：軽量goroutine、CSPモデルのchannel、sync.WaitGroup、Contextキャンセル、ワーカープール、goroutineリーク対策。",
    "excerpt_zh_hant": "完整掌握 Go 原生併發模型：輕量級協程 goroutine（KB 級開銷）、CSP 模式 channel 通信、sync.WaitGroup 生命週期管理，加上 Context 取消、工作池模式，以及 goroutine 洩漏防護。",
    "category_slug": "backend",
    "tag_slugs": ["go", "performance", "algorithms", "linux"],
    "cover_theme": "teal",
    "code_language": "go",
    "code_snippet": """package main

import (
    "context"
    "fmt"
    "log"
    "sync"
    "time"
)

type Job struct{ ID int; URL string }
type Result struct{ JobID int; Latency time.Duration; Status int; Err error }

func worker(ctx context.Context, id int, jobs <-chan Job, results chan<- Result, wg *sync.WaitGroup) {
    defer wg.Done()
    log.Printf("[worker %d] started", id)
    for {
        select {
        case <-ctx.Done():
            log.Printf("[worker %d] cancelled: %v", id, ctx.Err())
            return
        case job, ok := <-jobs:
            if !ok { return }
            t0 := time.Now()
            select {
            case <-ctx.Done():
                results <- Result{JobID: job.ID, Err: ctx.Err()}
                return
            case <-time.After(500 * time.Millisecond):
                results <- Result{JobID: job.ID, Latency: time.Since(t0), Status: 200}
            }
        }
    }
}

func main() {
    const (
        workerCount = 4
        jobCount    = 20
    )
    ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
    defer cancel()
    jobs := make(chan Job, workerCount*2)
    results := make(chan Result, workerCount*2)
    var wg sync.WaitGroup
    for i := 1; i <= workerCount; i++ {
        wg.Add(1)
        go worker(ctx, i, jobs, results, &wg)
    }
    go func() {
        for i := 1; i <= jobCount; i++ {
            jobs <- Job{ID: i, URL: fmt.Sprintf("https://api.example.com/item/%d", i)}
        }
        close(jobs)
    }()
    go func() { wg.Wait(); close(results) }()
    total := 0
    for r := range results {
        total++
        if r.Err != nil { fmt.Printf("[job %02d] ERROR %v\\n", r.JobID, r.Err) }
        fmt.Printf("[job %02d] status=%d latency=%-8s total=%d\\n", r.JobID, r.Status, r.Latency, total)
    }
    fmt.Printf("Done: %d/%d jobs\\n", total, jobCount)
}
""",
    "content_zh": "# Go 语言并发：goroutine + channel + sync.WaitGroup\n\nGo 最引以为豪的特性就是原生并发模型：\"不要通过共享内存通信，而要通过通信共享内存\"。goroutine + channel 的 CSP 模式让并发代码可读性和安全性大幅提升。\n\n## goroutine 与工作池模式\n\n一个 goroutine 初始栈仅 2KB，可以轻松启动十万级别。通过带缓冲 channel 实现固定大小 worker pool，避免无限创建导致调度压力，用 sync.WaitGroup 等待所有 worker 退出。\n\n```go\n{code}\n```\n\n## Context 取消与陷阱\n\ncontext.WithTimeout/WithCancel 同时关闭所有嵌套协程，是防止泄漏的关键。常见陷阱：for-range 读已关闭 channel 自动退出、select 加 default 变成忙循环、无缓冲 channel 发送端阻塞造成 goroutine 悬挂。\n\n| 特性 | Go goroutine+channel | Java Thread+Queue | Rust async+tokio |\n|------|---------------------|-------------------|------------------|\n| 最小开销 | ~2KB栈 | ~1MB栈 | 结构体级 |\n| 启动10万耗时 | <100ms | 数秒/OOM | ~200ms |\n| 同步原语 | channel/mutex/Cond | BlockingQueue/锁 | tokio::sync::* |\n| 取消机制 | Context统一 | Future.cancel/中断 | Drop/select! |\n| 常见陷阱 | goroutine泄漏/阻塞 | 虚假唤醒/死锁 | Pin! 生命周期 |\n\n## 最佳实践\n\n发送端 close channel，不要接收端关。优先使用有界缓冲 channel，避免无界队列导致内存暴涨。用 defer 覆盖所有关闭路径，防止异常下 goroutine 泄漏。",
    "content_en": "# Go Concurrency: Goroutines, Channels & sync.WaitGroup\n\nGo's defining feature is native concurrency: \"don't communicate by sharing memory; share memory by communicating\". CSP pattern delivers highly readable, safe concurrent code.\n\n## Goroutines and Worker Pool Pattern\n\nA goroutine starts with 2KB stack, so hundreds of thousands are practical. Bound concurrency with buffered channel for fixed worker pool; avoid runaway creation stressing scheduler. Use sync.WaitGroup to await graceful shutdown.\n\n```go\n{code}\n```\n\n## Context Cancellation and Pitfalls\n\ncontext.WithTimeout/WithCancel propagates cancellation through all nested goroutines - key defense against leaks. Common traps: for-range on closed channels exit cleanly, select with default causes busy loops, unbuffered channel send blocks and hangs goroutines.\n\n| Feature | Go goroutine+channel | Java Thread+Queue | Rust async+tokio |\n|---------|---------------------|-------------------|------------------|\n| Min cost | ~2KB stack | ~1MB stack | Struct-level |\n| Spawn 100k time | <100ms | Seconds/OOM | ~200ms |\n| Sync primitives | channel/mutex/Cond | BlockingQueue/locks | tokio::sync::* |\n| Cancel mechanism | Unified Context | Future.cancel/interrupt | Drop/select! |\n| Pitfalls | Goroutine leaks/blocked | Spurious wakeups/deadlock | Pin! lifetimes |\n\n## Best Practices\n\nSenders close channels, not receivers. Prefer bounded buffered channels to avoid unbounded memory growth. Cover all exit paths with defer for cleanup; exceptions otherwise silently leak goroutines."
},
{
    "title_zh": "Kubernetes Pod 生命周期 + Init Container + Sidecar",
    "title_en": "K8s Pod Lifecycle, Init Containers & Sidecars",
    "title_ja": "K8s Pod ライフサイクル + Init コンテナ + Sidecar",
    "title_zh_hant": "Kubernetes Pod 生命週期 + Init Container + Sidecar",
    "excerpt_zh": "详细拆解 Kubernetes Pod 从 Pending 到 Terminated 的完整状态机、PostStart/PreStop 钩子执行时机、Init Container 前置依赖保证、Sidecar 容器模式（istio-proxy、日志收集），以及优雅终止零停机配置。",
    "excerpt_en": "Full K8s Pod state machine Pending→Terminated, PostStart/PreStop hooks, Init Container dependency guarantees, Sidecar patterns (istio-proxy, log collectors), and zero-downtime graceful termination configs.",
    "excerpt_ja": "K8s Pod状態遷移Pending→Terminated、PostStart/PreStopフック、Init Container依存保証、Sidecarパターン、グレースフル停止ゼロダウンタイム設定。",
    "excerpt_zh_hant": "詳細拆解 Kubernetes Pod 從 Pending 到 Terminated 的完整狀態機、PostStart/PreStop 鉤子執行時機、Init Container 前置依賴保證、Sidecar 容器模式（istio-proxy、日誌收集），以及優雅終止零停機配置。",
    "category_slug": "technology",
    "tag_slugs": ["kubernetes", "docker", "linux", "security"],
    "cover_theme": "indigo",
    "code_language": "yaml",
    "code_snippet": """apiVersion: v1
kind: Pod
metadata: { name: web-app-pod, labels: { app: web } }
spec:
  terminationGracePeriodSeconds: 60
  shareProcessNamespace: true
  serviceAccountName: web-sa
  initContainers:
    - name: wait-for-db
      image: bitnami/postgresql:16
      command: ["/bin/sh", "-c", "until pg_isready -h postgres -p 5432 -U app; do echo wait; sleep 3; done;"]
    - name: migrate-db
      image: registry.example.com/app:${APP_VERSION}
      command: ["alembic", "upgrade", "head"]
      envFrom: [{ configMapRef: { name: web-config } }]
      volumeMounts: [{ name: app-secret, mountPath: /run/secrets, readOnly: true }]
    - name: fetch-assets
      image: amazon/aws-cli
      command: ["aws", "s3", "sync", "s3://app-assets/static/", "/var/www/static/", "--delete"]
      volumeMounts: [{ name: static-assets, mountPath: /var/www/static }]
  containers:
    - name: app
      image: registry.example.com/app:${APP_VERSION}
      ports: [{ containerPort: 8000, name: http }]
      lifecycle:
        postStart: { exec: { command: ["/bin/sh", "-c", "echo started >> /var/log/app/boot.log"] } }
        preStop:
          exec: { command: ["/bin/sh", "-c", "sleep 5; kill -SIGTERM 1; while pidof app >/dev/null; do sleep 1; done;"] }
      readinessProbe: { httpGet: { path: /health/ready, port: http }, initialDelaySeconds: 3, periodSeconds: 5 }
      livenessProbe: { httpGet: { path: /health/live, port: http }, initialDelaySeconds: 15, periodSeconds: 20, failureThreshold: 3 }
      startupProbe: { httpGet: { path: /health/started, port: http }, periodSeconds: 5, failureThreshold: 30 }
      resources:
        requests: { cpu: 100m, memory: 256Mi }
        limits:   { cpu: 1000m, memory: 1Gi }
      volumeMounts:
        - { name: static-assets, mountPath: /app/static, readOnly: true }
        - { name: app-logs, mountPath: /var/log/app }
    - name: envoy-sidecar
      image: envoyproxy/envoy:v1.30
      lifecycle:
        preStop: { exec: { command: ["/bin/sh", "-c", "curl -X POST http://localhost:15000/healthcheck/fail; sleep 10;"] } }
    - name: fluentbit-sidecar
      image: fluent/fluent-bit:3.0
      volumeMounts: [{ name: app-logs, mountPath: /var/log/app, readOnly: true }]
  volumes:
    - { name: static-assets, emptyDir: {} }
    - { name: app-logs, emptyDir: {} }
    - { name: app-secret, secret: { secretName: web-secret } }
""",
    "content_zh": "# Kubernetes Pod 生命周期 + Init Container + Sidecar\n\nPod 是 K8s 最小调度单位，理解其状态流转和容器协作模式是应用稳定性的前提。一个 Pod 中多个容器的启动/终止顺序、探针配置的细微差别直接影响线上表现。\n\n## Pod 生命周期状态机\n\n创建 → PodScheduled（调度到节点）→ Init Containers 依次执行 → 主容器启动 → PostStart 钩子 → readiness 通过才被 service 接收流量 → liveness 失败重启 → 删除时 SIGTERM → preStop → terminationGracePeriodSeconds 超时强制杀。\n\n```yaml\n{code}\n```\n\n## Init 容器与 Sidecar 模式\n\nInit Containers 按顺序逐一执行，成功后主容器才启动。适合做数据库等待、数据迁移、静态资源拉取。Sidecar 和主容器共享网络/卷，提供主容器无侵入的代理（istio/envoy）、日志收集（fluentbit）。\n\n| 容器类型 | 启动时机 | 与主容器关系 | 用途示例 |\n|---------|---------|-------------|---------|\n| Init Container | 主容器之前串行 | 成功一次即可退出 | 等待DB、数据迁移 |\n| Sidecar 容器 | 与主容器并行 | 同生命周期同退 | Service Mesh代理 |\n| Sidecar 容器 | 与主容器并行 | 生命周期相同 | 日志收集fluentbit |\n| Main App 容器 | Init完成后 | 业务主进程 | Web服务API |\n| Ephemeral 容器 | 任意时刻debug注入 | 临时 | 调试故障Pod |\n\n## 最佳实践\n\n永远配 startupProbe 给冷启动慢的应用，preStop 里睡几秒等待 service 摘掉端点再终止，避免流量进来时进程已死掉。readiness 判断数据库依赖，不要启动就 ready。",
    "content_en": "# K8s Pod Lifecycle, Init Containers & Sidecars\n\nPod is K8s' smallest schedulable unit. Master state transitions and inter-container patterns for reliability. Subtle differences in startup/shutdown ordering and probe configs directly affect production behavior.\n\n## Pod Lifecycle State Machine\n\nCreation → PodScheduled → Init Containers run serially → Main containers start → PostStart hooks → readiness must pass before service sends traffic → liveness failures trigger restart → deletion sends SIGTERM → preStop fires → terminationGracePeriodSeconds hard kill.\n\n```yaml\n{code}\n```\n\n## Init Containers and Sidecar Patterns\n\nInit Containers execute in order; only when all succeed do mains start. Perfect for DB waits, migrations, asset pulls. Sidecars share network/volumes with the main app, providing non-intrusive proxies (istio/envoy) or log shipping (fluentbit).\n\n| Container Type | Startup Timing | Relationship to App | Use Cases |\n|---------------|---------------|--------------------|----------|\n| Init Container | Before main, serialized | Runs-once success required | DB waits, migrations |\n| Sidecar | Parallel with main | Same lifecycle, exits together | Service Mesh proxy |\n| Sidecar | Parallel with main | Same lifecycle | Log collector fluentbit |\n| Main App | After init succeeds | Business process | Web API server |\n| Ephemeral | kubectl debug any time | Temporary injection | Debug broken pods |\n\n## Best Practices\n\nAlways add startupProbe for slow-booting apps. Sleep a few seconds in preStop to let endpoints deregister from services before killing process - prevents race where traffic arrives as app dies. Readiness should check DB dependencies, not just process liveness."
},
{
    "title_zh": "Linux 性能调优：perf_events + bpftrace + BCC",
    "title_en": "Linux Performance Tuning: perf, bpftrace & BCC",
    "title_ja": "Linux 性能チューニング：perf + bpftrace + BCC",
    "title_zh_hant": "Linux 性能調優：perf_events + bpftrace + BCC",
    "excerpt_zh": "从 CPU、内存、IO、网络四个维度，使用 perf_events 采样堆栈、bpftrace 一行脚本追踪内核点、BCC 工具集 biolatency/offcputime，快速定位生产服务器性能瓶颈，附真实排查思路。",
    "excerpt_en": "Tune Linux across CPU/mem/IO/net: perf for CPU sampling, bpftrace one-liners for kernel tracepoints, BCC classics biolatency/offcputime to pinpoint production bottlenecks with real incident methodology.",
    "excerpt_ja": "CPU/メモリ/IO/ネットワーク4次元：perfによるサンプリング、bpftraceワンライナー、BCC biolatency/offcputimeを用いた本番ボトルネック特定とトラブルシューティング。",
    "excerpt_zh_hant": "從 CPU、內存、IO、網絡四個維度，使用 perf_events 採樣堆棧、bpftrace 一行腳本追蹤內核點、BCC 工具集 biolatency/offcputime，快速定位生產服務器性能瓶頸，附真實排查思路。",
    "category_slug": "technology",
    "tag_slugs": ["linux", "performance", "go", "rust"],
    "cover_theme": "yellow",
    "code_language": "bash",
    "code_snippet": """#!/usr/bin/env bash
set -euo pipefail
LOG=perf-report-$(date +%Y%m%d-%H%M).log
exec > >(tee -a "$LOG") 2>&1

echo "===== [1] CPU TOP functions 30s ====="
perf record -F 99 -a -g -- sleep 30
perf report --stdio -n --sort comm,dso,symbol | head -60
# perf script | FlameGraph/stackcollapse-perf.pl | flamegraph.pl > cpu-flame.svg

echo "\\n===== [2] perf stat system-wide ====="
perf stat -a -d -- sleep 10
# 关注 context-switches, cache-misses 比率, stalled-cycles-frontend

echo "\\n===== [3] bpftrace: block IO size distribution by comm ====="
bpftrace -e '
tracepoint:block:block_rq_issue { @[comm, args->rwbs[0]] = hist(args->bytes); }
interval:s:15 { printf("\\n=== 15s IO hist by process ===\\n"); print(@); clear(@); exit(); }
' 2>&1 | head -40 || true

echo "\\n===== [4] bpftrace: TCP active connect trace ====="
bpftrace -e '
kprobe:tcp_connect { printf("PID %d (%s) -> %s\\n", pid, comm, ntop(args->family, args->daddr)); }
' -c 'curl -s https://example.com >/dev/null' 2>&1 | head -20 || true

echo "\\n===== [5] BCC biolatency + tcplife ====="
/usr/share/bcc/tools/biolatency -mF 1 5 || true
# /usr/share/bcc/tools/offcputime -df 5 1 > offcpu.stacks
timeout 15 /usr/share/bcc/tools/tcplife -L -T 2>/dev/null | head -40 || true

echo "\\n===== [6] snapshot vmstat slabtop sar ====="
vmstat 1 5
echo "--- slab top ---"
slabtop -o -s c | head -25 || true
echo "--- THP check ---"
grep -E "AnonHugePages|HugePages_Total" /proc/meminfo || true
echo "\\nSaved to: $LOG"
""",
    "content_zh": "# Linux 性能调优：perf_events + bpftrace + BCC\n\n线上服务器性能问题排查的核心思路是 USE 法：先看每个资源的 Utilization（利用率）、Saturation（饱和度）、Errors（错误数），再用对应工具深入。本文介绍三大主流工具。\n\n## perf_events：CPU 级热点分析\n\nperf 基于 CPU PMU 硬件计数器，开销极低（~2%）。99Hz 采样避开调度周期整倍数获取真实分布。perf stat 看 cache miss、分支预测失败宏观指标；perf record + FlameGraph 生成交互式火焰图。\n\n```bash\n{code}\n```\n\n## bpftrace / BCC：内核事件追踪\n\neBPF 可在内核函数、tracepoint、USDT 探针挂载自定义 C 程序，安全沙箱化运行。bpftrace 适合一行脚本速查；BCC 是预编译好的 200+ 常用工具，biolatency、offcputime、tcplife 是 IO/阻塞/网络延迟三板斧。\n\n| 资源维度 | 宏观指标（一眼定位） | 微观诊断工具（深入分析） |\n|---------|---------------------|-----------------------|\n| CPU | top/vmstat us,sy,wa,st | perf record + FlameGraph |\n| 调度延迟 | /proc/schedstat pidstat -w | BCC runqlat bpftrace sched_switch |\n| 内存 | free/vmstat si,so sar -r | BCC memleak perf kmem slabtop |\n| 磁盘IO | iostat -xz await/util% | BCC biolatency bpftrace block_rq_* |\n| 网络延迟 | ss -ti/sar -n TCP,ETCP | BCC tcplife bpftrace tcp:probe |\n\n## 最佳实践\n\n先宏观再微观：先跑 sar/vmstat 确定是哪类资源问题，再用对应 BCC 工具，最后 perf/bpftrace 自定义追踪。eBPF 权限高，生产先 staging 验证，注意运行时长不超过几分钟。",
    "content_en": "# Linux Performance Tuning: perf, bpftrace & BCC\n\nThe USE Method guides production debugging: first measure Utilization, Saturation, and Errors for each resource, then deep-dive with specific tools. This covers today's three most important tools.\n\n## perf_events: CPU-level Hotspot Analysis\n\nperf uses CPU PMU hardware counters with tiny overhead (~2%). Sample at 99Hz to avoid lock-step with scheduler periodicity for accurate distributions. perf stat captures macro metrics; perf record + FlameGraph builds interactive visualizations.\n\n```bash\n{code}\n```\n\n## bpftrace and BCC: Kernel Event Tracing\n\neBPF attaches sandboxed C programs to kernel functions, tracepoints, USDT probes. bpftrace excels at one-liner rapid investigations. BCC ships 200+ prepackaged tools; biolatency, offcputime, and tcplife are your triad for IO/block/network latency triage.\n\n| Resource Dimension | Macro Triage (orientation) | Micro Diagnostic (deep dive) |\n|--------------------|---------------------------|-----------------------------|\n| CPU | top/vmstat us,sy,wa,st cols | perf record + FlameGraph |\n| Scheduler latency | /proc/schedstat pidstat -w | BCC runqlat bpftrace sched_switch |\n| Memory | free/vmstat si,so sar -r | BCC memleak perf kmem slabtop |\n| Disk IO | iostat -xz await/util% | BCC biolatency bpftrace block_rq_* |\n| Network latency | ss -ti/sar -n TCP,ETCP | BCC tcplife bpftrace tcp:probe |\n\n## Best Practices\n\nMacro before micro: start with sar/vmstat to classify which resource type is the issue, then pick right BCC tools, finally drop into custom perf/bpftrace. eBPF is privileged; validate scripts in staging first and limit production runs to few minutes at a time."
},
{
    "title_zh": "JWT 认证安全最佳实践 + OAuth2 vs SAML",
    "title_en": "JWT Security Best Practices + OAuth2 vs SAML",
    "title_ja": "JWT 認証セキュリティ + OAuth2 vs SAML",
    "title_zh_hant": "JWT 認證安全最佳實踐 + OAuth2 vs SAML",
    "excerpt_zh": "系统性归纳 JWT 常见安全漏洞防护：算法混淆攻击（none/RS256→HS256）、密钥爆破、KID注入、重放攻击防御，再从多个维度对比 OAuth2（授权码+PKCE）、OIDC、SAML 2.0 三种主流认证协议选型。",
    "excerpt_en": "Comprehensive JWT vulnerability playbook: alg confusion attacks, key brute force, KID injection, replay defenses. Compare OAuth2(+PKCE), OIDC, SAML 2.0 across dimensions for protocol selection.",
    "excerpt_ja": "JWT脆弱性と対策：alg混乱攻撃、鍵総当たり、KIDインジェクション、リプレイ対策。さらにOAuth2+PKCE、OIDC、SAML2.0の3プロトコル多次元比較。",
    "excerpt_zh_hant": "系統性歸納 JWT 常見安全漏洞防護：算法混淆攻擊（none/RS256→HS256）、密鑰爆破、KID注入、重放攻擊防禦，再從多個維度對比 OAuth2（授權碼+PKCE）、OIDC、SAML 2.0 三種主流認證協議選型。",
    "category_slug": "essays",
    "tag_slugs": ["security", "fastapi", "nodejs", "python"],
    "cover_theme": "rose",
    "code_language": "typescript",
    "code_snippet": """import { createSign, createVerify, randomBytes, timingSafeEqual } from "node:crypto";

export interface JwtConfig {
    algorithm: "RS256";
    privateKeyPem: string;
    publicKeyPem: string;
    issuer: string;
    audience: string;
    accessTokenTtlSec: number;
    allowedAlgos: readonly string[];
}
export interface TokenPayload {
    sub: string; scopes: readonly string[]; jti: string;
    exp: number; nbf: number; iat: number; iss: string; aud: string;
}
const B64 = {
    enc: (b: Buffer) => b.toString("base64url"),
    dec: (s: string) => Buffer.from(s, "base64url"),
};
const DENIED = new Set<string>();

export function createJwt(cfg: JwtConfig, claims: Partial<TokenPayload> & { sub: string; scopes: readonly string[] }): string {
    const now = Math.floor(Date.now() / 1000);
    const header = { alg: cfg.algorithm, typ: "JWT", kid: "k1" };
    const payload: TokenPayload = {
        sub: claims.sub, scopes: claims.scopes,
        jti: randomBytes(16).toString("hex"),
        iat: now, nbf: now, exp: now + cfg.accessTokenTtlSec,
        iss: cfg.issuer, aud: cfg.audience,
    };
    const input = `${B64.enc(Buffer.from(JSON.stringify(header)))}.${B64.enc(Buffer.from(JSON.stringify(payload)))}`;
    const s = createSign("RSA-SHA256"); s.update(input);
    return `${input}.${B64.enc(s.sign(cfg.privateKeyPem))}`;
}

export function verifyJwt(cfg: JwtConfig, token: string): TokenPayload {
    const parts = token.split(".");
    if (parts.length !== 3) throw new Error("malformed");
    const [hB64, pB64, sB64] = parts;
    const header = JSON.parse(B64.dec(hB64).toString());
    if (!cfg.allowedAlgos.includes(header.alg) || header.alg === "none") throw new Error("alg not allowed");
    const ver = createVerify("RSA-SHA256"); ver.update(`${hB64}.${pB64}`);
    if (!ver.verify(cfg.publicKeyPem, B64.dec(sB64))) throw new Error("signature mismatch");
    const p = JSON.parse(B64.dec(pB64).toString()) as TokenPayload;
    if (!timingSafeEqual(Buffer.from(p.iss), Buffer.from(cfg.issuer))) throw new Error("iss");
    if (p.aud !== cfg.audience) throw new Error("aud");
    const now = Math.floor(Date.now() / 1000);
    if (p.exp < now) throw new Error("expired");
    if (p.nbf > now) throw new Error("not yet valid");
    if (DENIED.has(p.jti)) throw new Error("revoked");
    return p;
}
""",
    "content_zh": "# JWT 认证安全最佳实践 + OAuth2 vs SAML\n\nJWT 因其无状态、跨服务易用被广泛采用，但配置不严谨会成攻击重灾区。现代系统常需第三方登录或企业 SSO，选对联邦协议也是架构师必修课。\n\n## JWT 安全实现要点\n\n绝对不要使用对称密钥 HMAC 直接在前端签发（密钥会泄漏），生产用 RS256/ES256 非对称，公钥公开验证。严格白名单允许算法、用 timingSafeEqual 做 iss/aud 对比防时序攻击，jti 黑名单支持吊销。\n\n```typescript\n{code}\n```\n\n## OAuth2 / OIDC / SAML 对比\n\nOAuth2 是授权框架不是认证协议，OpenID Connect 在其之上加了 id_token 才是登录。SAML 2.0 是传统企业联邦协议，XML 格式兼容性强但移动端体验差。\n\n| 特性 | OAuth2 + PKCE | OIDC (基于OAuth2) | SAML 2.0 |\n|------|--------------|------------------|----------|\n| 本质 | 授权(delegation) | 认证(authentication) | 认证+授权联邦 |\n| 适用 | 移动端/SPA | Web/移动/API | 企业内部SSO |\n| Token | access_token | access_token + id_token(JWT) | SAML Assertion(XML) |\n| 安全性 | 需PKCE防code注入 | 原生支持nonce | 签名XML流程复杂 |\n| 移动端体验 | 好(App转场) | 好 | 差(重定向多) |\n| 集成复杂度 | 中 | 低 | 高(双方元数据) |\n\n## 最佳实践\n\nJWT 存敏感信息：短 TTL(5-15min) + refresh_token 轮换。SPA 用 HttpOnly Cookie 承载 refresh_token 避免 XSS。第三方登录场景统一用 OIDC。",
    "content_en": "# JWT Security Best Practices + OAuth2 vs SAML\n\nJWT is ubiquitous for stateless cross-service convenience but sloppy config is a top attack target. Modern systems also need third-party login or enterprise SSO so choosing the right federation protocol is mandatory architect knowledge.\n\n## JWT Secure Implementation Checklist\n\nNever sign tokens client-side with symmetric HMAC secrets. Production uses RS256/ES256 asymmetric - public keys verify openly. Whitelist only allowed algorithms; compare iss/aud with timingSafeEqual to prevent timing oracles; track jti blacklists for revocation.\n\n```typescript\n{code}\n```\n\n## OAuth2 / OIDC / SAML Compared\n\nOAuth2 is an authorization framework, NOT authentication. OpenID Connect adds id_token on top of OAuth2 to deliver real login. SAML 2.0 is classic enterprise federation with XML payloads - compatible but clunky on mobile.\n\n| Feature | OAuth2 + PKCE | OIDC (over OAuth2) | SAML 2.0 |\n|---------|--------------|-------------------|----------|\n| Nature | Delegated authorization | User authentication | Federated authN+authZ |\n| Best fit | Mobile / SPA | Web/Mobile/APIs | Enterprise internal SSO |\n| Credentials | access_token only | access_token + id_token (JWT) | SAML Assertion (XML) |\n| Security | Requires PKCE against CSRF | Native nonce support | Signed XML, complex flows |\n| Mobile UX | Great (app transitions) | Great | Poor (many redirects) |\n| Integration complexity | Medium | Low | High (metadata exchange) |\n\n## Best Practices\n\nIf JWTs carry sensitive scope: short TTL (5-15 min) + refresh token rotation. SPAs should store refresh tokens in HttpOnly cookies to sidestep XSS. Standardize on OIDC for any third-party login scenario."
},
{
    "title_zh": "CQRS + Event Sourcing 架构模式解析",
    "title_en": "CQRS + Event Sourcing Architecture Patterns",
    "title_ja": "CQRS + Event Sourcing アーキテクチャ解説",
    "title_zh_hant": "CQRS + Event Sourcing 架構模式解析",
    "excerpt_zh": "透彻解析两种高复杂度分布式架构模式：CQRS 读写模型分离实现查询极致性能、Event Sourcing 以事件作为唯一真相源实现全量审计与时间回溯，讨论一致性/快照/幂等难点与反模式。",
    "excerpt_en": "Advanced patterns: CQRS separate read/write models for query performance; Event Sourcing using events as source of truth for audit + time travel. Covers consistency, snapshots, idempotency pitfalls and anti-patterns.",
    "excerpt_ja": "高度な分散パターン：CQRS読み書き分離でクエリ性能、Event Sourcingはイベントを唯一の源として監査+時間遡行。一貫性・スナップショット・べき等とアンチパターンを解説。",
    "excerpt_zh_hant": "透徹解析兩種高複雜度分布式架構模式：CQRS 讀寫模型分離實現查詢極致性能、Event Sourcing 以事件作為唯一真相源實現全量審計與時間回溯，討論一致性/快照/冪等難點與反模式。",
    "category_slug": "essays",
    "tag_slugs": ["algorithms", "postgresql", "redis", "fastapi"],
    "cover_theme": "purple",
    "code_language": "python",
    "code_snippet": """from __future__ import annotations
import json, time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Any
from collections import defaultdict

@dataclass
class DomainEvent:
    event_id: str
    aggregate_type: str
    aggregate_id: str
    event_type: str
    payload: dict
    occurred_at: float = field(default_factory=time.time)
    version: int = 1

class EventStore:
    def __init__(self) -> None:
        self._events: list[DomainEvent] = []
        self._snapshots: dict[tuple[str, str], tuple[int, Any]] = {}
        self._subs: dict[str, list[Callable[[DomainEvent], None]]] = defaultdict(list)

    def append(self, events: Iterable[DomainEvent], expected_version: int | None = None) -> None:
        events = list(events)
        if expected_version is not None and events:
            at, aid = events[0].aggregate_type, events[0].aggregate_id
            cur = sum(1 for e in self._events if e.aggregate_type == at and e.aggregate_id == aid)
            if cur != expected_version:
                raise ValueError(f"Concurrency conflict: expected v{expected_version}, got v{cur}")
        for e in events:
            self._events.append(e)
            for s in self._subs.get(e.event_type, []) + self._subs.get("*", []): s(e)

    def load(self, agg_type: str, agg_id: str, snapshot_every: int = 50) -> tuple[Any, int]:
        key = (agg_type, agg_id)
        start_ver, state = self._snapshots.get(key, (0, None))
        version = start_ver
        events = [e for e in self._events if e.aggregate_type == agg_type and e.aggregate_id == agg_id][start_ver:]
        for e in events:
            version += 1
            fn = globals().get(f"apply_{e.event_type}")
            state = fn(state, e) if fn else state
            if version % snapshot_every == 0: self._snapshots[key] = (version, state)
        return state, version

    def subscribe(self, event_type: str, fn: Callable[[DomainEvent], None]) -> None:
        self._subs[event_type].append(fn)

def apply_OrderCreated(state, e): return {"order_id": e.aggregate_id, "items": {}, "status": "CREATED", **e.payload}
def apply_ItemAdded(state, e):
    s = dict(state); pid = e.payload["product_id"]
    s["items"] = {**s["items"], pid: s["items"].get(pid, 0) + e.payload["qty"]}
    return s
def apply_OrderPlaced(state, e): return {**state, "status": "PLACED", "placed_at": e.occurred_at}

store = EventStore()
projection: dict[str, dict] = {}
store.subscribe("OrderPlaced", lambda e: projection.__setitem__(e.aggregate_id, {"status": "PLACED", **e.payload}))
""",
    "content_zh": "# CQRS + Event Sourcing 架构模式解析\n\n当业务发展到一定规模，传统 CRUD 读写同库模型在复杂查询/审计/并发控制遇到瓶颈。CQRS + ES 是打破瓶颈的高级模式，但复杂度成倍上升，必须慎重选型。\n\n## Event Sourcing：事件为真相源\n\n不存当前状态，只存导致状态变化的事件流（OrderCreated → ItemAdded → OrderPlaced）。重放所有事件可重建任意时间点状态，天然拥有完整审计轨迹。配合快照避免每次从 0 重放。\n\n```python\n{code}\n```\n\n## CQRS：写读模型分离\n\n写入侧走领域模型 + 事件，通过事件订阅异步构建读侧投影表（Projection）。写侧保证一致性，读侧针对查询做反范式和索引，各自最优，但引入最终一致性窗口。\n\n| 维度 | 传统 CRUD | 纯 CQRS | CQRS + Event Sourcing |\n|------|----------|--------|---------------------|\n| 存储 | 单表既读又写 | 写库+读库 | 事件流+N个投影表 |\n| 查询能力 | 中等 | 极高 | 极高+时间旅行 |\n| 审计追溯 | 额外加字段 | 难 | 天生免费 |\n| 调试难度 | 低 | 中高 | 非常高 |\n| 适合场景 | 大部分业务 | 读多写少查询复杂 | 金融/账本/溯源 |\n\n## 最佳实践\n\n先问三问再决定：业务是否需要不可变审计？查询是否真的复杂到读写冲突？团队是否有 DDD 经验？三个 Yes 才考虑。否则传统 CRUD + 审计表往往 ROI 更高。",
    "content_en": "# CQRS + Event Sourcing Architecture Patterns\n\nAs systems scale, traditional CRUD single-model architectures hit bottlenecks in complex queries, audit trails, and concurrency. CQRS + ES are advanced patterns that break these limits, but added complexity demands careful adoption decisions.\n\n## Event Sourcing: Events as Source of Truth\n\nNever persist current state; append only events that caused state changes (OrderCreated → ItemAdded → OrderPlaced). Replaying reconstructs state at any point; complete audit trail for free. Pair with snapshots to avoid replaying from zero on each load.\n\n```python\n{code}\n```\n\n## CQRS: Separate Write and Read Models\n\nWrite path goes through domain model and produces events. Event subscribers asynchronously build denormalized projection tables tuned for queries. Write side enforces consistency while read side optimized for retrieval, but introduces an eventual consistency window.\n\n| Dimension | Classic CRUD | CQRS Only | CQRS + Event Sourcing |\n|-----------|-------------|-----------|-----------------------|\n| Storage | Single table both | Write DB + Read DB | Event stream + N projections |\n| Query flexibility | Medium | Very High | Very High + time travel |\n| Audit history | Extra columns | Hard | Free and immutable |\n| Debug difficulty | Low | Medium-High | Very High |\n| Fit for | 90% of business | Read-heavy complex queries | Finance/ledger/provenance |\n\n## Best Practices\n\nAsk three questions before adopting: Do you require an immutable audit trail? Are queries genuinely painful with CRUD? Does the team have DDD experience? Only proceed if all three are Yes. Otherwise classic CRUD plus a simple audit table nearly always delivers better ROI."
},
{
    "title_zh": "前端性能优化：Core Web Vitals 实战",
    "title_en": "Frontend Performance: Core Web Vitals in Practice",
    "title_ja": "フロントエンド性能：Core Web Vitals 実践",
    "title_zh_hant": "前端性能優化：Core Web Vitals 實戰",
    "excerpt_zh": "Google 搜索排名核心指标完全实战：LCP 最大内容绘制（预连接/图像优先级/CDN缓存）、CLS 累积布局偏移（图像尺寸/字体FOIT/动态占位）、INP 交互响应（长任务拆分/防抖节流）全面落地。",
    "excerpt_en": "Practical Google Core Web Vitals playbook: LCP via preconnects/image-priority/CDN, CLS elimination via image dimensions/font-loading/placeholders, INP via long-task splitting + debouncing.",
    "excerpt_ja": "Google検索順位のCore Web Vitals完全実践：LCP最適化（事前接続・画像優先度・CDN）、CLS除去（画像寸法・フォント・プレースホルダ）、INP改善（長タスク分割・デバウンス）。",
    "excerpt_zh_hant": "Google 搜索排名核心指標完全實戰：LCP 最大內容繪製（預連接/圖像優先級/CDN緩存）、CLS 累積佈局偏移（圖像尺寸/字體FOIT/動態佔位）、INP 交互響應（長任務拆分/防抖節流）全面落地。",
    "category_slug": "frontend",
    "tag_slugs": ["javascript", "performance", "css", "astro"],
    "cover_theme": "cyan",
    "code_language": "typescript",
    "code_snippet": """import { onCLS, onINP, onLCP, type Metric } from "web-vitals";

const URL = "/api/analytics/vitals";
function send(metric: Metric) {
    const body = JSON.stringify({
        name: metric.name, value: metric.value, rating: metric.rating,
        id: metric.id, url: location.href, ts: Date.now(),
    });
    if (navigator.sendBeacon) navigator.sendBeacon(URL, body);
    else fetch(URL, { body, method: "POST", keepalive: true }).catch(() => {});
}
export function initVitals() {
    if (location.hostname === "localhost") {
        const log = (m: Metric) => console.log(`[vitals] ${m.name}=${Math.round(m.value)} rating=${m.rating}`);
        onLCP(log); onCLS(log); onINP(log); return;
    }
    onLCP(send); onCLS(send); onINP(send);
}

export function scheduleHigh(work: () => void): void {
    if ("scheduler" in window && "postTask" in (window as any).scheduler)
        (window as any).scheduler.postTask(work, { priority: "user-blocking" });
    else if ("requestIdleCallback" in window)
        requestAnimationFrame(() => requestIdleCallback(() => work(), { timeout: 1500 }));
    else setTimeout(work, 0);
}

export function splitTasks(total: number, unit: (i: number) => void, chunk = 25): void {
    let i = 0;
    const pump = (deadline?: any): void => {
        const rem = typeof deadline !== "undefined" && deadline.timeRemaining ? deadline : { timeRemaining: () => 8 };
        while (i < total && rem.timeRemaining() > 1 && (i % chunk !== 0 || i === 0)) unit(i++);
        if (i < total) "requestIdleCallback" in window ? requestIdleCallback(pump) : setTimeout(pump, 0);
    };
    "requestIdleCallback" in window ? requestIdleCallback(pump) : pump();
}

export function throttle<T extends (...a: any[]) => void>(fn: T, wait = 150, opts: { leading?: boolean; trailing?: boolean } = {}): T {
    const { leading = true, trailing = true } = opts;
    let last = 0, tId: any = null, lastArgs: any[] | null = null;
    return function (this: any, ...args: any[]) {
        const now = Date.now();
        if (!last && !leading) last = now;
        const remaining = wait - (now - last);
        lastArgs = args;
        if (remaining <= 0) {
            if (tId) { clearTimeout(tId); tId = null; }
            last = now; fn.apply(this, args); lastArgs = null;
        } else if (trailing && !tId) {
            tId = setTimeout(() => {
                last = leading ? Date.now() : 0; tId = null;
                if (lastArgs) { fn.apply(this, lastArgs); lastArgs = null; }
            }, remaining);
        }
    } as T;
}
""",
    "content_zh": "# 前端性能优化：Core Web Vitals (LCP/CLS/INP) 实战\n\n自 2021 年起 Google 把 Core Web Vitals 纳入搜索排名因子，性能不再只是体验问题，而是直接影响业务增长。三个指标分别衡量加载/稳定/流畅的用户直观感受。\n\n## LCP 最大内容绘制 <2.5s\n\n四大影响因素：慢服务器响应→CDN/HTTP3/preconnect关键域名；资源阻塞渲染→内联关键CSS/defer非关键JS；资源加载慢→fetchpriority=high/srcset多尺寸/AVIF；客户端渲染慢→SSR/孤岛架构。\n\n```typescript\n{code}\n```\n\n## CLS 布局偏移 <0.1 & INP <200ms\n\nCLS 元凶：图片/video缺宽高、字体替换抖动、未预留高度的横幅/动态插入内容。INP 是 FID 继任指标，关注每次输入到下一次绘制，>50ms 长任务是重点优化对象。\n\n| 指标 | 目标阈值 | 最大元凶 1 | 最大元凶 2 | 核心优化方法 |\n|------|---------|----------|----------|------------|\n| LCP | <2.5s (绿) | 大图片/视频 | 慢TTFB | preconnect, AVIF, fetchpriority |\n| CLS | <0.1 (绿) | 图片未设尺寸 | 字体切换抖动 | width+height声明, font-display:optional |\n| INP | <200ms (绿) | 长任务阻塞主线程 | 重样式/重排 | scheduler.postTask, rIC splitting |\n| TTFB | <800ms | 后端慢查询 | 无缓存/边缘 | CDN缓存, SSR streaming |\n\n## 最佳实践\n\n安装 web-vitals 库埋点真实用户数据（RUM），别只看本地 Lighthouse 实验室数据。移动端性能预算 3x 重要，因为设备慢 3-10 倍。",
    "content_en": "# Frontend Performance: Core Web Vitals in Practice\n\nSince 2021 Google includes Core Web Vitals in search rankings, making performance a growth lever instead of just UX polish. Three metrics directly capture user perception of load, stability, and responsiveness.\n\n## LCP (Largest Contentful Paint) <2.5s\n\nFour LCP factors: slow server response -> CDN/HTTP3/preconnect critical origins. Render-blocking resources -> inline critical CSS / defer the rest. Slow loads -> fetchpriority=high/srcset/AVIF. Client render -> SSR/islands.\n\n```typescript\n{code}\n```\n\n## CLS <0.1 & INP <200ms\n\nCLS culprits: images/videos without explicit dimensions, font swap jitter, unbanners/dynamic inserts without reserved height. INP replaces FID - measures every input-to-paint; >50ms Long Tasks the primary optimization target.\n\n| Metric | Green Target | Top Culprit #1 | Top Culprit #2 | Primary Fixes |\n|--------|-------------|---------------|----------------|---------------|\n| LCP | <2.5s | Heavy hero images | Slow TTFB | preconnect, AVIF, fetchpriority |\n| CLS | <0.1 | Images without w/h | Font swap reflow | Declare dims, font-display:optional |\n| INP | <200ms | Long task blocks main | Heavy style/layout | postTask, rIC splitting |\n| TTFB | <800ms | Slow backend queries | No edge caching | CDN cache, SSR streaming |\n\n## Best Practices\n\nShip the web-vitals library for Real User Monitoring (RUM). Local Lighthouse lab data isn't enough. Always budget 3-10x headroom because mobile devices are slower by that factor."
},
{
    "title_zh": "算法与数据结构：动态规划 5 大解题模板",
    "title_en": "Dynamic Programming: 5 Universal Templates",
    "title_ja": "アルゴリズム：動的計画法 5大テンプレート",
    "title_zh_hant": "算法與數據結構：動態規劃 5 大解題模板",
    "excerpt_zh": "彻底掌握动态规划：先给出通用 DP 解题五步法，再精解五大高频模板：背包类、子序列类、区间DP、状态压缩DP、树形DP，每个模板附典型代码与变形要点。",
    "excerpt_en": "Master DP: 5-step universal framework then 5 high-frequency templates: Knapsack, Subsequence, Interval DP, Bitmask DP, Tree DP, each with canonical code and variant keys.",
    "excerpt_ja": "DP完全制覇：5ステップ共通フレームワーク+5大高頻度テンプレート：ナップサック、部分列、区間DP、ビットDP、木DPに典型コードと変形ポイント。",
    "excerpt_zh_hant": "徹底掌握動態規劃：先給出通用 DP 解題五步法，再精解五大高頻模板：背包類、子序列類、區間DP、狀態壓縮DP、樹形DP，每個模板附典型代碼與變形要點。",
    "category_slug": "tutorial",
    "tag_slugs": ["algorithms", "python", "rust", "go"],
    "cover_theme": "pink",
    "code_language": "python",
    "code_snippet": """from functools import lru_cache
from typing import List
import bisect

def t1_01_knapsack(cap: int, ws: List[int], vs: List[int]) -> int:
    n = len(ws); dp = [0] * (cap + 1)
    for i in range(n):
        for c in range(cap, ws[i] - 1, -1):
            dp[c] = max(dp[c], dp[c - ws[i]] + vs[i])
    return dp[cap]

def t2_unbounded_knapsack(cap: int, ws: List[int], vs: List[int]) -> int:
    dp = [0] * (cap + 1)
    for c in range(1, cap + 1):
        for i, w in enumerate(ws):
            if w <= c: dp[c] = max(dp[c], dp[c - w] + vs[i])
    return dp[cap]

def t3_lcs(a: str, b: str) -> int:
    m, n = len(a), len(b); prev = [0] * (n + 1)
    for i in range(1, m + 1):
        cur = [0] * (n + 1)
        for j in range(1, n + 1):
            cur[j] = prev[j - 1] + 1 if a[i - 1] == b[j - 1] else max(prev[j], cur[j - 1])
        prev = cur
    return prev[n]

def t4_lis(nums: List[int]) -> int:
    tails = []
    for x in nums:
        i = bisect.bisect_left(tails, x)
        if i == len(tails): tails.append(x)
        else: tails[i] = x
    return len(tails)

def t5_interval_palindrome_cuts(s: str) -> int:
    n = len(s)
    is_pal = [[False] * n for _ in range(n)]
    for i in range(n - 1, -1, -1):
        for j in range(i, n):
            is_pal[i][j] = s[i] == s[j] and (j - i < 3 or is_pal[i + 1][j - 1])
    cut = [float('inf')] * n
    for j in range(n):
        if is_pal[0][j]: cut[j] = 0
        else:
            for i in range(1, j + 1):
                if is_pal[i][j]: cut[j] = min(cut[j], cut[i - 1] + 1)
    return int(cut[n - 1])

if __name__ == "__main__":
    print(t1_01_knapsack(10, [2, 3, 5, 7], [3, 4, 6, 10]))
    print(t3_lcs("abcde", "aceb"), t4_lis([10, 9, 2, 5, 3, 7, 101, 18]))
    print(t5_interval_palindrome_cuts("aabcbdadcb"))
""",
    "content_zh": "# 算法与数据结构：动态规划 5 大解题模板\n\n动态规划是算法面试中区分度最高的题型，核心思想是把大问题拆为重叠子问题、存储中间结果避免重复计算。掌握通用五步法加五类高频模板，90%的 DP 题都能解。\n\n## 通用五步法与背包类\n\n五步：① 状态定义 dp[i][j] 含义 ② 转移方程（找最后一步两种选择）③ 初始化 base case ④ 遍历顺序 ⑤ 滚动数组空间优化。01 背包每个物品选/不选，容量倒序；完全背包物品可多次选，容量正序。\n\n```python\n{code}\n```\n\n## 子序列 / 区间 / 状压 / 树形\n\n子序列类通常两串用二维 dp[i][j]。区间 DP 按区间长度枚举，适合回文/博弈/合并石子。状态压缩用 bitmask 表示访问过的点集（TSP）。树形 DFS 对每个子节点返回(选/不选)两状态。\n\n| DP 类型 | 状态定义关键词 | 遍历顺序 | 典型题 |\n|--------|--------------|---------|--------|\n| 01 背包 | dp[c]=容量c时最大价值 | 容量倒序 | LC416 分割等和子集 |\n| 完全背包 | dp[c]=凑硬币最少个数 | 容量正序 | LC322 零钱兑换 |\n| LIS/LCS | dp[i]=以i结尾LIS长 | 双重i<j | LC300/LC1143 |\n| 区间 DP | dp[i][j]=区间[i,j]最优 | len从短到长 | LC132 分割回文II |\n| 状压 DP | dp[mask]=集合mask最优 | mask从小到大 | LC847 访问所有节点最短路径 |\n| 树形 DP | dfs(node)返回(选,不选) | 后序遍历 | LC337 打家劫舍III |\n\n## 最佳实践\n\n写不出转移方程时先暴力搜索+记忆化，画出递归树就能看到重叠子问题的形状，再转自底向上迭代就清晰了。先过样例再空间优化。",
    "content_en": "# Dynamic Programming: 5 Universal Problem-Solving Templates\n\nDP is the highest-signal topic in algorithm interviews. Core idea: split large problem into overlapping subproblems, store intermediate results to avoid recomputation. Master 5 steps + 5 templates to solve 90% of DP problems.\n\n## Universal Five Steps + Knapsack Family\n\nFive steps: (1) Define what dp[i][j] means. (2) Derive transitions by considering last binary choice. (3) Init base cases. (4) Determine correct for-loop order. (5) Apply rolling-array space optimization. 0/1 Knapsack iterates capacity backwards (one item each); Unbounded iterates forwards.\n\n```python\n{code}\n```\n\n## Subsequence / Interval / Bitmask / Tree DP\n\nFor two-string subsequence, dp[i][j] encodes first i chars vs first j. Interval DP enumerates by interval length (palindromes/games/stones). Bitmask tracks visited set (TSP). Tree DFS returns two states per child (picked / not-picked).\n\n| DP Type | State Keyword | Traversal Order | Example Problem |\n|---------|--------------|-----------------|----------------|\n| 0/1 Knapsack | dp[c] = max value cap c | Capacity reverse | LC416 Partition Equal Subset |\n| Unbounded KS | dp[c] = min coins to reach c | Capacity forward | LC322 Coin Change |\n| LIS/LCS | dp[i] = LIS ending at i | Nested i<j loops | LC300 / LC1143 |\n| Interval DP | dp[i][j] = best on [i,j] | Length increasing | LC132 Palindrome Partition II |\n| Bitmask DP | dp[mask] = best for visited set | Mask increasing | LC847 Shortest Path Visiting All |\n| Tree DP | dfs(node) -> (take, no-take) | Post-order walk | LC337 House Robber III |\n\n## Best Practices\n\nIf transitions feel mysterious, start with brute recursion + memoization and draw the recursion tree. Once you see the shape of overlapping subproblems, convert to bottom-up iterative. Pass samples first; optimize space only when logic is rock solid."
},
{
    "title_zh": "GraphQL vs REST：从 7 个维度深度对比",
    "title_en": "GraphQL vs REST: 7-Dimension Deep Comparison",
    "title_ja": "GraphQL vs REST：7つの視点から深く比較",
    "title_zh_hant": "GraphQL vs REST：從 7 個維度深度對比",
    "excerpt_zh": "终结选型焦虑：从网络传输效率、前端开发体验、后端演进成本、缓存策略、类型安全、安全风险、生态工具链 7 大维度系统对比 GraphQL 与 REST，给出清晰决策树与混合架构模式。",
    "excerpt_en": "End the API style debate: compared across 7 dimensions - network efficiency, DX, evolution cost, caching, type-safety, security risks, ecosystem - with clear decision tree and hybrid architecture patterns.",
    "excerpt_ja": "APIスタイル選択迷宮を終わらせる：ネットワーク効率・DX・進化コスト・キャッシュ・型安全性・セキュリティ・エコシステムの7次元で比較。明確なデシジョンツリーとハイブリッド構成を提示。",
    "excerpt_zh_hant": "終結選型焦慮：從網絡傳輸效率、前端開發體驗、後端演進成本、緩存策略、類型安全、安全風險、生態工具鏈 7 大維度系統對比 GraphQL 與 REST，給出清晰決策樹與混合架構模式。",
    "category_slug": "essays",
    "tag_slugs": ["fastapi", "nodejs", "typescript", "performance"],
    "cover_theme": "blue",
    "code_language": "typescript",
    "code_snippet": """import express, { Request, Response } from "express";
import { graphqlHTTP } from "express-graphql";
import { buildSchema, parse, visit, Kind } from "graphql";

const app = express();
app.use(express.json());

const schema = buildSchema(`
  type User { id: ID!; username: String!; orders(limit: Int = 10): [Order!]! }
  type Order { id: ID!; total: Float!; items(limit: Int = 20): [OrderItem!]! }
  type OrderItem { productId: ID!; qty: Int!; price: Float! }
  type Query { user(id: ID!): User; users(limit: Int = 20): [User!]! }
  schema { query: Query }
`);

class ComplexityGuard {
    private costs: Record<string, number> = { orders: 5, items: 2, users: 10 };
    private readonly MAX = 150;
    analyze(query: string): { total: number; exceeded: boolean } {
        const doc = parse(query); let total = 1;
        visit(doc, {
            Field: (node) => {
                const base = this.costs[node.name.value] || 1;
                const args = Object.fromEntries((node.arguments || []).map(a => [a.name.value, (a.value as any).value]));
                const mult = args.limit ? Math.ceil(Number(args.limit) / 10) : 1;
                total += base * mult;
            },
        });
        return { total, exceeded: total > this.MAX };
    }
}

const root = {
    user: ({ id }: { id: string }) => ({
        id, username: `u${id}`,
        orders: ({ limit = 10 }: any) => Array.from({ length: limit }, (_, i) => ({
            id: `o${i}`, total: 99.5 + i,
            items: ({ limit = 20 }: any) => Array.from({ length: limit }, (_, k) => ({ productId: `p${k}`, qty: k + 1, price: 9.9 })),
        })),
    }),
    users: ({ limit = 20 }: any) => Array.from({ length: limit }, (_, i) => root.user({ id: String(i + 1) })),
};

const guard = new ComplexityGuard();
app.get("/rest/users/:id", (req: Request, res: Response) => {
    res.json({ data: { id: req.params.id, username: `u${req.params.id}` }, _links: { orders: { href: `/rest/users/${req.params.id}/orders` } } });
});
app.use("/graphql", (req: Request, res: Response, next) => {
    const q = (req.body?.query) || (req.query.query as string) || "";
    const r = guard.analyze(q);
    if (r.exceeded) return res.status(400).json({ error: `Complexity ${r.total} exceeds cap 150` });
    res.setHeader("X-GraphQL-Complexity", String(r.total));
    next();
}, graphqlHTTP({ schema, rootValue: root, graphiql: process.env.NODE_ENV !== "production" }));

app.listen(3000, () => console.log("[compare] REST+GraphQL on :3000"));
""",
    "content_zh": "# GraphQL vs REST：从 7 个维度深度对比\n\nGraphQL 常被宣传为 REST 的终结者，但实际两者各有适合场景。盲目选择 GraphQL 会带来 N+1 查询、复杂度爆炸、缓存失效等坑；只用 REST 又有过取/欠取问题。理性对比再做选择。\n\n## 典型架构与复杂度防护\n\nGraphQL 单端点接收查询，前端声明式指定字段结构，解决 REST 常见的 20 个接口拼数据或大接口返回 80% 不用字段的问题。但必须在网关层加上查询复杂度分析、字段级权限、深度限制。\n\n```typescript\n{code}\n```\n\n## 七大维度横向对比\n\n| 对比维度 | REST (JSON:API风格) | GraphQL | 胜者 |\n|---------|-------------------|---------|-----|\n| 网络传输效率 | 多请求过取欠取 | 单请求精确字段POST不利CDN | 简单REST赢/复杂视图GraphQL赢 |\n| 前端开发体验 | 新字段等后端加接口 | 自助取字段+内省生成类型 | GraphQL |\n| 后端演进成本 | 版本化管理/v1/v2 | 字段弃用平滑但resolver复杂度涨 | REST |\n| HTTP缓存 | 天然支持Get请求 | 需持久化查询ID+自定义层 | REST |\n| 类型安全 | 需OpenAPI代码生成 | Schema强类型+内省生成SDK | GraphQL |\n| 安全风险 | 普通CRUD鉴权易做 | 深度/复杂度/批注入要防护 | REST安全面更小 |\n| 生态工具链 | OpenAPI/Postman成熟 | Apollo Studio/GraphiQL完善 | 打平 |\n\n## 最佳实践\n\n决策树：团队以 BFF 形态存在且前端迭代快 → GraphQL；微服务间调用或纯资源 CRUD → REST；混合架构：BFF 用 GraphQL 组合多个 REST 微服务是目前大厂主流方案。",
    "content_en": "# GraphQL vs REST: 7-Dimension Deep Comparison\n\nGraphQL is marketed as REST killer but each excels in different scenarios. Blind GraphQL adoption brings N+1, complexity explosion, cache invalidation; pure REST suffers over/under-fetching. Compare rationally.\n\n## Reference Architecture and Complexity Guards\n\nGraphQL exposes one endpoint accepting declarative queries fetching exactly requested fields - fixing REST's \"20 endpoints to assemble\" and \"80% fields unused\" problems. But gateways MUST enforce complexity analysis, field-level auth, and depth limits.\n\n```typescript\n{code}\n```\n\n## Seven Dimensions Side by Side\n\n| Dimension | REST (JSON:API style) | GraphQL | Winner |\n|-----------|----------------------|---------|--------|\n| Network efficiency | Multi-trip over/under fetch | Single exact fetch, POST hurts CDN | REST wins simple/GraphQL complex views |\n| Frontend DX | New fields = new backend endpoint | Self-service + introspect TS types | GraphQL |\n| Backend evolution | Versioned routes /v1 /v2 | Smooth deprecation but resolver complexity explodes | REST |\n| HTTP caching | Native GET support | Requires persisted query IDs + custom | REST |\n| Type safety | Needs OpenAPI codegen | Strong schema + SDK generation built in | GraphQL |\n| Security surface | Standard CRUD auth | Depth/complexity/batch injection guard needed | REST smaller surface |\n| Tooling ecosystem | OpenAPI/Postman mature | Apollo Studio/GraphiQL mature | Tied |\n\n## Best Practices\n\nDecision tree: Team runs BFF with fast frontend iteration → GraphQL. Inter-service calls or pure resource CRUD → REST. Hybrid (GraphQL BFF composing multiple REST microservices) is today's major-factory mainstream pattern."
},
{
    "title_zh": "Monorepo 工具链：Turborepo + pnpm workspace",
    "title_en": "Monorepo Toolchain: Turborepo + pnpm workspace",
    "title_ja": "Monorepo ツールチェーン：Turborepo + pnpm workspace",
    "title_zh_hant": "Monorepo 工具鏈：Turborepo + pnpm workspace",
    "excerpt_zh": "单仓多包（Monorepo）管理大型前端全栈项目的完全指南：用 pnpm workspace 做依赖统一安装和链接，Turborepo 做任务编排、增量构建和远程缓存，对比 Nx/Lerna，附带代码复用与版本发布最佳实践。",
    "excerpt_en": "Complete monorepo guide for large fullstack projects: pnpm workspace for unified dependency install + linking, Turborepo for task orchestration, incremental builds and remote caching. Compares Nx/Lerna, includes code sharing and release best practices.",
    "excerpt_ja": "大規模フルスタックプロジェクト向けMonorepo完全ガイド：pnpm workspaceによる依存関係統合管理、Turborepoによるタスクオーケストレーション・インクリメンタルビルド・リモートキャッシュ。Nx/Lerna比較、コード共通化とリリースベストプラクティス。",
    "excerpt_zh_hant": "單倉多包（Monorepo）管理大型前端全棧項目的完全指南：用 pnpm workspace 做依賴統一安裝和鏈接，Turborepo 做任務編排、增量構建和遠程緩存，對比 Nx/Lerna，附帶代碼複用與版本發佈最佳實踐。",
    "category_slug": "tools",
    "tag_slugs": ["typescript", "nodejs", "react", "nextjs"],
    "cover_theme": "orange",
    "code_language": "yaml",
    "code_snippet": """# pnpm-workspace.yaml
packages:
  - 'apps/*'
  - 'packages/*'
  - 'tooling/*'

# turbo.json
{
  "$schema": "https://turbo.build/schema.json",
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "dist/**"],
      "cache": true
    },
    "typecheck": { "dependsOn": ["^build"], "outputs": [] },
    "lint": { "dependsOn": ["^build"], "outputs": [] },
    "test": {
      "dependsOn": ["^build"],
      "outputs": ["coverage/**"],
      "inputs": ["**/*.test.*", "jest.config.*"]
    },
    "dev": { "cache": false, "persistent": true }
  }
}

# root package.json
{
  "name": "my-monorepo",
  "private": true,
  "packageManager": "pnpm@9.0.0",
  "scripts": {
    "build": "turbo build",
    "typecheck": "turbo typecheck",
    "test": "turbo test",
    "dev": "turbo dev",
    "release": "changeset version && changeset publish"
  },
  "devDependencies": {
    "turbo": "^2.0.0",
    "@changesets/cli": "^2.27.0",
    "typescript": "^5.4.0"
  }
}

# packages/ui/package.json
{
  "name": "@company/ui",
  "version": "1.2.0",
  "type": "module",
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": { "types": "./dist/index.d.ts", "import": "./dist/index.js" },
    "./styles.css": "./dist/styles.css"
  },
  "sideEffects": false
}
""",
    "content_zh": "# Monorepo 工具链：Turborepo + pnpm workspace\n\n当项目从一个包拆为多个包，每个独立 repo 会导致依赖版本不一致、代码复用难、发布链路繁琐。Monorepo 用工具链解决这些痛点，Turborepo + pnpm 是目前体验最优组合。\n\n## pnpm workspace 依赖管理\n\n在 pnpm-workspace.yaml 中声明 apps/* 和 packages/* 目录结构，根目录 pnpm install 自动硬链接，同一依赖跨包共享，node_modules 严格隔离避免幽灵依赖。workspace: 协议引用内部包，修改即时生效无需发版。\n\n```yaml\n{code}\n```\n\n## Turborepo 增量构建与缓存\n\nturbo.json 声明任务依赖图：子包 build 依赖上游^build，自动拓扑排序。每次构建的输入哈希命中本地或远程缓存直接跳过，CI 构建速度可提升 5-20 倍。\n\n| 维度 | 手工多仓 | Lerna + yarn | pnpm + Turborepo | pnpm + Nx |\n|------|---------|-------------|----------------|----------|\n| 依赖去重 | 跨仓各装 | 中等 hoisting | 硬链接共享 | 与Turborepo相同 |\n| 任务编排 | 脚本 | 弱并行lerna run | DAG智能缓存 | targetDefaults |\n| 远程缓存 | 无 | 付费企业版 | 自建S3/Vercel免费 | Nx Cloud免费额度 |\n| 幽灵依赖风险 | 低 | 高 | 极低 | 极低 |\n\n## 最佳实践\n\n内部包统一 @scope/pkg 命名，Changesets 管理版本与 changelog，禁止跨包相对路径 import。远程缓存配团队 S3 存储，CI 共享加速全员构建。",
    "content_en": "# Monorepo Toolchain: Turborepo + pnpm workspace\n\nAs projects split from one package to many, separate repos cause divergent deps, painful code reuse, and fragmented releases. Monorepo solves these with tooling. Turborepo + pnpm delivers the best combination today.\n\n## pnpm workspace Dependency Management\n\nDeclare apps/* packages/* structure in pnpm-workspace.yaml. Root pnpm install uses hard-links so the same dep is shared across packages with strictly isolated node_modules against phantom dependencies. workspace: protocol references internal packages instantly without publishing.\n\n```yaml\n{code}\n```\n\n## Turborepo Incremental Builds and Caching\n\nturbo.json declares task DAG: child build depends on upstream ^build, topologically sorted automatically. Per-task input hash hits local or remote cache to skip entire builds - CI speedup typically 5-20x.\n\n| Dimension | Manual repos | Lerna + yarn | pnpm + Turborepo | pnpm + Nx |\n|-----------|-------------|-------------|------------------|----------|\n| Deduped deps | Per-repo copies | Medium hoisting | Hardlink shared | Same as Turborepo |\n| Task orchestration | Scripts | Weak lerna run | DAG smart cache | targetDefaults |\n| Remote cache | None | Paid enterprise | Self-host S3/Vercel free | Nx Cloud free tier |\n| Phantom dep risk | Low | High | Very Low | Very Low |\n\n## Best Practices\n\nStandardize internal packages on @scope/pkg naming. Use Changesets for versioning/changelogs. Never cross-package relative imports. Wire remote cache to team S3 bucket so every CI run shares cache globally."
},
{
    "title_zh": "Prompt Engineering 入门：Few-Shot + CoT + 结构化输出",
    "title_en": "Prompt Engineering 101: Few-Shot + CoT + Structured Output",
    "title_ja": "Prompt Engineering 入門：Few-Shot + CoT + 構造化出力",
    "title_zh_hant": "Prompt Engineering 入門：Few-Shot + CoT + 結構化輸出",
    "excerpt_zh": "系统入门 Prompt Engineering 三大核心技术：Few-Shot 示例学习注入专业领域风格、Chain-of-Thought (CoT) 思维链引导复杂推理、JSON Schema 强制结构化输出对接下游系统。附真实 prompt 模板和避坑指南。",
    "excerpt_en": "Systematic prompt engineering primer covering three core techniques: Few-Shot examples for style injection, Chain-of-Thought for complex reasoning, JSON Schema enforced structured outputs for downstream systems. Includes real templates and anti-patterns.",
    "excerpt_ja": "Prompt Engineering体系入門：3つのコアテクニック——Few-Shot例示学習でドメインスタイル注入、Chain-of-Thoughtで複雑推論誘導、JSON Schema強制構造化出力で下流システム連携。実テンプレートとアンチパターン集付き。",
    "excerpt_zh_hant": "系統入門 Prompt Engineering 三大核心技術：Few-Shot 示例學習注入專業領域風格、Chain-of-Thought (CoT) 思維鏈引導複雜推理、JSON Schema 強制結構化輸出對接下游系統。附真實 prompt 模板和避坑指南。",
    "category_slug": "essays",
    "tag_slugs": ["ai", "python", "typescript"],
    "cover_theme": "indigo",
    "code_language": "python",
    "code_snippet": """from openai import AsyncOpenAI
import json
from typing import Any
from pydantic import BaseModel, Field

client = AsyncOpenAI()

FEW_SHOT_PROMPT = '''你是资深后端技术写作编辑，擅长将草稿改写成精炼博客风格。
要求：事实准确，保留技术细节，简洁专业，段落开头先给核心结论。

## 示例1 输入
"FastAPI比Flask快，因为用了ASGI和Pydantic，自动生成文档"
## 示例1 输出
**核心结论：FastAPI 通过 ASGI 异步 + Pydantic 类型驱动两大设计，同等硬件下单接口吞吐量约为 Flask 的 2.5-4 倍。**
除异步网络栈外，FastAPI 的请求校验基于 Pydantic v2 的 Rust 内核（pydantic-core），单个 schema 校验耗时较 Flask + marshmallow 方案低一个数量级；另一个隐形收益是基于 OpenAPI spec 自动生成的接口文档和类型化客户端 SDK，在团队协作场景相当于免费的 API 契约工具链。

## 待改写输入
"{raw_input}"

## 你的输出'''

COT_PROMPT = '''你是算法竞赛金牌选手。请逐步推导再给出最终答案，每一步标记并解释推理依据。
问题：给定数组 nums = [3, 1, 4, 2, 5, 8, 7, 6]，求最长递增子序列的长度。
思考步骤：
步骤1：
步骤2：
步骤3：
最终答案（仅数字）：'''

class ProductCategorizeResult(BaseModel):
    reasoning: list[str] = Field(description="分类判断过程，每个维度一条")
    category: str = Field(description="必须属于 [Electronics, Fashion, Books, Home, Other]")
    confidence: float = Field(ge=0.0, le=1.0)
    matched_keywords: list[str] = Field(default_factory=list)

async def few_shot_transform(raw: str) -> str:
    r = await client.chat.completions.create(
        model="gpt-4o-mini", temperature=0.3,
        messages=[{"role": "user", "content": FEW_SHOT_PROMPT.format(raw_input=raw)}])
    return r.choices[0].message.content or ""

async def categorize_structured(title: str, desc: str) -> dict[str, Any]:
    r = await client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18", temperature=0.0,
        messages=[{"role": "user", "content": f"商品标题 {title}\\n描述 {desc}"}],
        response_format={"type": "json_object"})
    data = json.loads(r.choices[0].message.content or "{}")
    return ProductCategorizeResult(**data).model_dump()
""",
    "content_zh": "# Prompt Engineering 入门：Few-Shot + CoT + 结构化输出\n\n大模型能力是固定的，真正拉开差距的是 Prompt Engineering 水平。掌握三大核心技术（少样本示例、思维链、结构化输出）可以让同一个模型输出质量提升一个档次，稳定对接生产流水线。\n\n## Few-Shot：示例驱动风格对齐\n\n直接写\"把这段写得专业点\"产出效果随机性大。在 Prompt 里先给 2-3 个真实的输入输出示例，模型会从示例中精确学习你的写作风格、格式要求、术语偏好。比纯自然语言指令稳定得多，且支持中英混合示例。\n\n```python\n{code}\n```\n\n## CoT 思维链 & 结构化输出\n\n需要复杂推理（逻辑/数学/代码调试）时，显式要求模型分步骤推理，最后才给结论，准确率平均提升 15-30%。要喂给下游系统的结果，用 Pydantic + response_format 强制 JSON 模式，失败重试兜底，避免自由文本解析。\n\n| 技术 | 解决问题 | 最佳温度 | 典型应用场景 |\n|------|---------|---------|-------------|\n| Zero-Shot 纯指令 | 任务简单标准 | 0.1-0.3 | 翻译、摘要、格式转换 |\n| Few-Shot 示例注入 | 风格/格式特殊要求 | 0.2-0.5 | 文案改写、标签标注、代码风格统一 |\n| CoT 思维链分步 | 多步推理/数学/逻辑 | 0.0-0.3 | 算法题、代码调试、根因分析 |\n| JSON Schema 结构化 | 对接程序接口 | 0.0 固定 | 打标入库、字段抽取、函数调用 |\n\n## 最佳实践\n\n写 Prompt 先给角色（System Prompt），再给上下文+任务，再给约束（字数/格式/语气/禁忌）。迭代：用 20 条样本测真实准确率，失败案例回灌为 few-shot 示例，每次改进都有量化依据。",
    "content_en": "# Prompt Engineering 101: Few-Shot + CoT + Structured Output\n\nModel capabilities are fixed; what truly differentiates outcomes is Prompt Engineering. Mastering the big three (few-shot exemplars, chain-of-thought, structured output) lifts quality one tier on the same model, reliably feeding production pipelines.\n\n## Few-Shot: Style Alignment by Example\n\n\"Rewrite professionally\" is vague and yields random results. Prepend 2-3 real input-output exemplars in the prompt; the model precisely learns your style, formatting rules, and terminology preferences from concrete samples. Far more stable than pure natural-language instructions, and handles bilingual mixed corpora.\n\n```python\n{code}\n```\n\n## Chain-of-Thought & Structured Outputs\n\nFor multi-step reasoning (logic/math/code debugging), explicitly require step-by-step deduction before final answer - accuracy typically improves 15-30%. For downstream-system consumption, enforce JSON mode via Pydantic response_format + retry on parse failures to avoid brittle free-text regex scraping.\n\n| Technique | Problem Solved | Optimal Temp | Typical Use Cases |\n|-----------|---------------|-------------|-------------------|\n| Zero-Shot instruction | Simple standard tasks | 0.1-0.3 | Translation, summarization, format conversion |\n| Few-Shot exemplar injection | Custom style/format rules | 0.2-0.5 | Copy rewrite, labeling, coding style alignment |\n| Chain-of-Thought steps | Multi-step reasoning/logic | 0.0-0.3 | Algorithm problems, debugging, root cause analysis |\n| JSON Schema structured | Program interface handoff | 0.0 fixed | Tag ingestion, field extraction, function calling |\n\n## Best Practices\n\nStart prompts with role (System), then context+task, then constraints (word count/format/tone/forbidden). Iterate against 20 labeled samples for real accuracy metrics; failure cases feed back as few-shot exemplars so every improvement has quantified evidence."
},
{
    "title_zh": "RAG 检索增强生成实战：Embedding + Vector DB + ReRank",
    "title_en": "RAG in Practice: Embedding + Vector DB + ReRank",
    "title_ja": "RAG 検索拡張生成実践：Embedding + Vector DB + ReRank",
    "title_zh_hant": "RAG 檢索增強生成實戰：Embedding + Vector DB + ReRank",
    "excerpt_zh": "从零搭建生产级 RAG 系统：文档分块策略（Chunk Size/重叠窗口）、Embedding 模型选型与向量化、向量数据库（PGVector/Milvus）检索过滤、Reranker 重排精修 Top-K，加上引用溯源和 Prompt 压缩优化，附完整可运行代码。",
    "excerpt_en": "Build production-grade RAG from scratch: doc chunking (size + overlap windows), embedding model selection, vector DB retrieval filters, Reranker refining Top-K, plus citation grounding and prompt compression. Complete runnable code included.",
    "excerpt_ja": "プロダクション級RAGをゼロから構築：文書チャンク戦略、Embeddingモデル選定、Vector DBフィルタ検索、RerankerによるTop-K精緻化、引用根拠とプロンプト圧縮。完全動作コード付き。",
    "excerpt_zh_hant": "從零搭建生產級 RAG 系統：文檔分塊策略（Chunk Size/重疊窗口）、Embedding 模型選型與向量化、向量數據庫（PGVector/Milvus）檢索過濾、Reranker 重排精修 Top-K，加上引用溯源和 Prompt 壓縮優化，附完整可運行代碼。",
    "category_slug": "tutorial",
    "tag_slugs": ["ai", "python", "postgresql", "typescript"],
    "cover_theme": "purple",
    "code_language": "python",
    "code_snippet": """from __future__ import annotations
import json, re
from dataclasses import dataclass
from typing import Iterable
import numpy as np
import psycopg2.extras
from sentence_transformers import SentenceTransformer, CrossEncoder

CHUNK_SIZE = 512
CHUNK_OVERLAP = 80
EMBED_MODEL = "BAAI/bge-m3"
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
TOP_K_RETRIEVAL = 20
TOP_K_FINAL = 4

embedder = SentenceTransformer(EMBED_MODEL)
reranker = CrossEncoder(RERANK_MODEL)

@dataclass
class Chunk:
    doc_id: str
    chunk_idx: int
    text: str
    metadata: dict

def smart_chunk(doc_id: str, text: str, meta: dict | None = None) -> list[Chunk]:
    paragraphs = re.split(r"\\n\\s*\\n", text.strip())
    chunks: list[Chunk] = []
    buf, buf_len, idx = [], 0, 0
    for p in paragraphs:
        p_len = len(p.split())
        if buf and buf_len + p_len > CHUNK_SIZE:
            chunks.append(Chunk(doc_id, idx, "\\n\\n".join(buf), meta or {}))
            idx += 1
            drop = max(1, len(buf) - (CHUNK_OVERLAP * len(buf) // max(1, buf_len)))
            buf, buf_len = buf[drop:], sum(len(b.split()) for b in buf[drop:])
        buf.append(p); buf_len += p_len
    if buf: chunks.append(Chunk(doc_id, idx, "\\n\\n".join(buf), meta or {}))
    return chunks

def pgvector_store(conn, chunks: Iterable[Chunk]) -> None:
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute(f"CREATE TABLE IF NOT EXISTS docs (id BIGSERIAL PRIMARY KEY, doc_id TEXT NOT NULL, chunk_idx INT NOT NULL, content TEXT NOT NULL, metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb, embedding vector(1024) NOT NULL, UNIQUE(doc_id, chunk_idx))")
    rows = []
    for c in chunks:
        emb = embedder.encode(c.text, normalize_embeddings=True)
        rows.append((c.doc_id, c.chunk_idx, c.text, json.dumps(c.metadata or {}), psycopg2.extras.Json(emb.tolist())))
    psycopg2.extras.execute_batch(cur, "INSERT INTO docs(doc_id, chunk_idx, content, metadata, embedding) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", rows)
    conn.commit()

def hybrid_search(conn, query: str, top_k: int = TOP_K_RETRIEVAL, category: str | None = None):
    q_emb = embedder.encode(query, normalize_embeddings=True).tolist()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    where_sql = "AND metadata->>'category' = %s" if category else ""
    params = [q_emb, top_k] + ([category] if category else [])
    cur.execute(f"SELECT id, content, metadata, 1 - (embedding <=> %s::vector) AS score FROM docs WHERE true {where_sql} ORDER BY embedding <=> %s::vector LIMIT %s", params)
    return [(h["content"], {"id": h["id"], "meta": dict(h["metadata"]), "vec_score": float(h["score"])}) for h in cur.fetchall()]

def rag_answer(conn, query: str, **filters) -> dict:
    raw_hits = hybrid_search(conn, query, **filters)
    if not raw_hits: return {"answer": "抱歉，未找到相关资料。", "citations": []}
    texts = [h[0] for h in raw_hits]
    scores = reranker.predict([(query, t) for t in texts], apply_softmax=True)
    ranked = sorted(zip(scores, raw_hits), reverse=True)[:TOP_K_FINAL]
    contexts = [f"[{i+1}] {t[1][0]}" for i, t in enumerate(ranked)]
    citations = [{"id": t[1][1]["id"], "rerank_score": float(t[0]), **t[1][1]["meta"]} for t in ranked]
    prompt = f"基于以下参考资料回答问题，每句结论必须标注引用编号[1]-[{TOP_K_FINAL}]；资料外的内容用'根据所提供资料无法确定'回答。\\n参考资料：\\n{chr(10).join(contexts)}\\n\\n问题：{query}\\n带引用的答案："
    return {"answer_prompt": prompt, "citations": citations}
""",
    "content_zh": "# RAG 检索增强生成实战：Embedding + Vector DB + ReRank\n\n大模型闭卷考试会产生幻觉，RAG（检索增强生成）在生成前先从私有知识库检索最相关 Top-K 段落，再带着上下文答题，是目前让大模型接入企业私有数据最主流、最落地的生产方案。\n\n## 文档分块与向量入库\n\n分块是 RAG 效果的第一道闸门：太小丢上下文，太大污染检索。实际生产通常 200-800 tokens 加 15-20% 重叠窗口；按自然段/标题边界切开比硬切字符效果强很多。用 BGE-M3 / E5-large-v2 这类开源中英双语 Embedding 效果远超 openai-ada-002。\n\n```python\n{code}\n```\n\n## 检索+重排两阶段流水线\n\n向量库 ANN 召回 Top 20-50 保证召回率（不要一开始就取 Top3），再用 CrossEncoder（Reranker）精排到 Top 4 喂给大模型，综合相关性质量提升 20-40%。最终给 Prompt 注入参考资料编号，要求回答强制标注引用编号，可追溯防幻觉。\n\n| 模块 | 朴素方案（Demo） | 生产方案（推荐） | 质量提升 |\n|------|---------------|---------------|---------|\n| 分块 | 硬切 1000 字符 | 自然段边界+512词+15%重叠 | +20-35% |\n| Embedding | openai text-ada-002 | BAAI/bge-m3 多语言 | +15-25% |\n| 检索 | 向量余弦 Top3 | ANN Top30 + Metadata过滤 | +10-20% |\n| 精修排序 | 不做 | CrossEncoder Reranker | +20-40% |\n| 回答生成 | 直接拼接context | 引用编号强制溯源+拒答兜底 | -40-60%幻觉率 |\n\n## 最佳实践\n\n上线前一定要离线评测：建立 100 条标注问题集（query+期望引用chunk列表），监控 Recall@10/Reciprocal Rank/MRR 三个指标。分块策略、模型、Rerank 的每一次改动都要量化对比，不要凭感觉调参。",
    "content_en": "# RAG in Practice: Embedding + Vector DB + ReRank\n\nLLMs hallucinate on closed-book exams. RAG (Retrieval-Augmented Generation) retrieves the most relevant Top-K passages from your private knowledge base before generating, producing grounded answers - today's most production-proven pattern for connecting LLMs to enterprise data.\n\n## Document Chunking and Vector Ingestion\n\nChunking is the first quality gate: too small loses context, too large pollutes retrieval. Production typically uses 200-800 token windows with 15-20% overlap; chunking along paragraph/title boundaries outperforms raw character-splitting dramatically. Open bilingual embeddings like BGE-M3/E5-large-v2 outperform openai-ada-002 on mixed corpora.\n\n```python\n{code}\n```\n\n## Two-Stage Retrieval + Rerank Pipeline\n\nANN vector recall fetches Top 20-50 for recall (never start with Top3), then CrossEncoder Reranker distills to Top 4 fed to LLM - net relevance quality jump 20-40%. Inject numbered references into the prompt, require inline citation IDs on every claim, enforce traceability against hallucinations.\n\n| Module | Naive (Demo) | Production (Recommended) | Quality Gain |\n|--------|-------------|------------------------|--------------|\n| Chunking | Hard-split 1000 chars | Natural breaks+512t+15% overlap | +20-35% |\n| Embedding | openai text-ada-002 | BAAI/bge-m3 multilingual | +15-25% |\n| Retrieval | Vector cos Top3 | ANN Top30 + Metadata filter | +10-20% |\n| Re-rank | None | CrossEncoder Reranker | +20-40% |\n| Generation | Raw context concat | Forced citation IDs + refusal fallback | -40-60% hallucination |\n\n## Best Practices\n\nAlways offline-evaluate before launch: build 100 labeled queries (query + expected chunk list), monitor Recall@10, Reciprocal Rank, MRR. Quantify every change to chunking/model/rerank - never tune by feel."
},
{
    "title_zh": "测试金字塔：单元/集成/E2E 测试比例与落地",
    "title_en": "Test Pyramid: Unit/Integration/E2E Ratios & Implementation",
    "title_ja": "テストピラミッド：単体/結合/E2E 比率と実践",
    "title_zh_hant": "測試金字塔：單元/整合/E2E 測試比例與落地",
    "excerpt_zh": "系统解析测试金字塔架构：从底层单元测试（大量快速、Mock 隔离依赖）、中层集成测试（服务/数据库/消息协作真实交互）、顶层 E2E 测试（真实用户路径少量精测）的推荐比例 70% / 20% / 10%，附项目覆盖率指标与落地实践。",
    "excerpt_en": "Systematic test pyramid breakdown: bottom unit tests (many, fast, mock isolated), middle integration tests (real service/db/message interaction), top E2E tests (few, critical user flows). Recommended ratio 70/20/10, with coverage metrics and implementation playbook.",
    "excerpt_ja": "テストピラミッド体系解説：下層 単体テスト（多数・高速・Mock分離）、中層 結合テスト（実DB/メッセージ協調）、上層 E2E（少数・重要ユーザーフロー）。推奨比率 70/20/10、カバレッジ指標と実践ガイド。",
    "excerpt_zh_hant": "系統解析測試金字塔架構：從底層單元測試（大量快速、Mock 隔離依賴）、中層整合測試（服務/數據庫/消息協作真實交互）、頂層 E2E 測試（真實用戶路徑少量精測）的推薦比例 70% / 20% / 10%，附項目覆蓋率指標與落地實踐。",
    "category_slug": "technology",
    "tag_slugs": ["nodejs", "python", "typescript", "algorithms"],
    "cover_theme": "emerald",
    "code_language": "typescript",
    "code_snippet": """// ====== 单元测试 (pactum + vitest + mocking) ======
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { OrderService } from './order.service';
import type { PaymentGateway, InventoryRepo, OrderRepo } from './ports';

const makeSUT = () => {
  const payment = { charge: vi.fn().mockResolvedValue({ success: true, txId: 'tx_001' }) } as unknown as PaymentGateway;
  const inventory = { lockStock: vi.fn().mockResolvedValue(true), releaseStock: vi.fn() } as unknown as InventoryRepo;
  const orders = { save: vi.fn().mockImplementation(o => Promise.resolve({ ...o, id: 'ord_42' })) } as unknown as OrderRepo;
  return { sut: new OrderService(orders, inventory, payment), payment, inventory, orders };
};

describe('OrderService.placeOrder 单元测试', () => {
  it('正常下单: 扣库存-扣款-落库三阶段成功', async () => {
    const { sut, orders, inventory, payment } = makeSUT();
    const order = await sut.placeOrder({ userId: 'u1', items: [{ sku: 'SK1', qty: 2, unitPrice: 99 }] });
    expect(order.id).toBe('ord_42');
    expect(inventory.lockStock).toHaveBeenCalledWith('SK1', 2);
    expect(payment.charge).toHaveBeenCalledWith(198, expect.any(String));
    expect(orders.save).toHaveBeenCalledTimes(1);
  });
  it('扣款失败时自动回滚库存释放', async () => {
    const { sut, payment, inventory } = makeSUT();
    payment.charge.mockResolvedValueOnce({ success: false, txId: 'tx_002', reason: 'INSUFFICIENT_FUNDS' });
    await expect(sut.placeOrder({ userId: 'u1', items: [{ sku: 'SK1', qty: 1, unitPrice: 99 }] }))
      .rejects.toThrow(/PAYMENT_FAILED/);
    expect(inventory.releaseStock).toHaveBeenCalledWith('SK1', 1);
  });
});

// ====== 集成测试 (TestContainer 启动真实 Postgres + Redis) ======
import { PostgreSqlContainer, RedisContainer } from '@testcontainers/postgresql';
import { createClient } from 'redis';

describe('CartRepository 集成测试', () => {
  let pgContainer: PostgreSqlContainer, redisContainer: RedisContainer;
  let pool: any, redis: ReturnType<typeof createClient>;

  beforeAll(async () => {
    pgContainer = await new PostgreSqlContainer('postgres:16-alpine').withDatabase('testdb').start();
    redisContainer = await new RedisContainer('redis:7-alpine').start();
    pool = require('pg').Pool({ connectionString: pgContainer.getConnectionUri() });
    await pool.query('CREATE TABLE carts (user_id TEXT PRIMARY KEY, items JSONB NOT NULL, updated_at TIMESTAMPTZ DEFAULT NOW())');
    redis = createClient({ url: redisContainer.getConnectionUrl() });
    await redis.connect();
  }, 60000);

  it('写 PG 后读 Redis 双写一致 (100 次并发下)', async () => {
    const repo = new (require('./cart.repo').CartRepository)(pool, redis);
    const N = 100;
    await Promise.all(Array.from({ length: N }, (_, i) => repo.upsert(`user_${i}`, [{ sku: `S${i}`, qty: i % 5 + 1 }])));
    for (let i = 0; i < N; i++) {
      const cached = JSON.parse(await redis.get(`cart:user_${i}`) || 'null');
      const row = (await pool.query('SELECT items FROM carts WHERE user_id=$1', [`user_${i}`])).rows[0];
      expect(cached).toMatchObject(row.items);
    }
  });

  afterAll(async () => {
    await pool?.end(); await redis?.quit();
    await pgContainer?.stop(); await redisContainer?.stop();
  });
});

// ====== E2E 测试 (Playwright - 仅核心 happy path) ======
import { test, expect } from '@playwright/test';

test.describe('结账核心链路 E2E', () => {
  test('登录→加购→结账→订单成功页完整路径', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', 'e2e-user@example.com');
    await page.fill('input[name="password"]', 'ValidPass123!');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/products');
    await page.click('[data-testid="product-42-add"]');
    await expect(page.locator('[data-testid="cart-count"]')).toHaveText('1');
    await page.goto('/checkout');
    await page.fill('[data-testid="card-number"]', '4242424242424242');
    await page.fill('[data-testid="card-cvc"]', '123');
    await page.click('[data-testid="submit-order"]');
    await expect(page.locator('[data-testid="order-success"]')).toBeVisible({ timeout: 15000 });
  });
});
""",
    "content_zh": "# 测试金字塔：单元/集成/E2E 测试比例与落地\n\n测试反模式（全是 E2E 全是 Mock）都会导致测试又慢又不稳。经典测试金字塔用分层结构解决：数量从上到下指数增加，速度越来越快，反馈周期越来越短，是大型团队十年验证过的稳定方法论。\n\n## 三层分工与推荐比例\n\n底层单元测试占 70%：覆盖纯逻辑、边界条件、错误分支，Mock 所有外部依赖，毫秒级跑完。中层集成测试 20%：用 TestContainer 启动真实数据库/Redis/消息队列，测服务之间真实协作不造假。顶层 E2E 10%：Playwright/Cypress 模拟真实用户，只覆盖核心业务路径（登录-下单-支付），不跑边角分支。\n\n```typescript\n{code}\n```\n\n## 覆盖率指标与落地节奏\n\n不要迷信 100% 行覆盖率。实际推荐：单元测试行覆盖 70-85%，重点模块分支覆盖 90%+；集成测试重点测写操作（提交订单/支付回调）和一致性；E2E 按业务 P0 清单来。按 2/3/5 法则：2 秒内跑完全部单测，3 分钟内跑完集成，5 分钟内跑完核心 E2E。\n\n| 层级 | 数量比例 | 单次速度 | 失败含义 | 归属负责人 |\n|------|---------|---------|---------|-----------|\n| 单元测试 | 70% | <50ms | 函数级逻辑bug | 开发自测CI必过 |\n| 集成测试 | 20% | <3s | 服务协作bug/DBSchema不一致 | 开发 + QA |\n| E2E 测试 | 10% | <1min | 链路级回归/构建产物损坏 | QA + 发布门禁 |\n\n## 最佳实践\n\n先写契约再写实现（TDD），新需求从 E2E 失败用例开始驱动，逐层下沉细化。CI 分层执行：PR 提交先跑单测+集成，发布分支再跑 E2E，避免阻塞日常迭代。",
    "content_en": "# Test Pyramid: Unit/Integration/E2E Ratios & Implementation\n\nAnti-patterns (all-E2E or all-Mock) produce slow, flaky test suites. The classic pyramid solves this with layered structure: exponentially more tests as you go down, faster execution, tighter feedback loops - battle-proven methodology for large teams over a decade.\n\n## Three-Layer Responsibilities and Recommended Ratios\n\nUnit tests at the bottom 70%: cover pure logic, edge cases, error branches. Mock all external deps; runs in milliseconds. Middle integration tests 20%: spin up real DB/Redis/message brokers via TestContainers. Verifies real service collaboration, no fakes. Top E2E 10%: Playwright/Cypress simulate real users on only critical business paths (login→order→pay), skip edge branches entirely.\n\n```typescript\n{code}\n```\n\n## Coverage Metrics and Adoption Cadence\n\nDon't worship 100% line coverage. Practical targets: unit line coverage 70-85%, branch coverage 90%+ on critical modules; integration tests stress writes (order submission, payment callbacks) and consistency; E2E is driven by business P0 checklist. Follow the 2/3/5 rule: all unit tests under 2s, integration done under 3 min, core E2E within 5 min.\n\n| Layer | Volume Ratio | Per-Run Speed | Failure Indicates | Owner |\n|-------|-------------|--------------|-------------------|-------|\n| Unit | 70% | <50ms | Function-level logic bug | Dev self-test, CI gate |\n| Integration | 20% | <3s | Service collaboration / DB schema drift | Dev + QA |\n| E2E | 10% | <1min | End-to-end regression / build broken | QA + release gate |\n\n## Best Practices\n\nDefine contracts before implementation (TDD). New features start with failing E2E spec, drill down layer by layer. CI stages: PR runs unit+integration immediately, release branch runs E2E only so daily iteration stays unblocked."
},
{
    "title_zh": "CI/CD Pipeline 设计：GitHub Actions + Cache + Matrix Build",
    "title_en": "CI/CD Pipeline Design: GitHub Actions + Cache + Matrix Build",
    "title_ja": "CI/CD パイプライン設計：GitHub Actions + Cache + Matrix Build",
    "title_zh_hant": "CI/CD Pipeline 設計：GitHub Actions + Cache + Matrix Build",
    "excerpt_zh": "从零设计一套工业级 GitHub Actions 流水线：npm/pip 依赖缓存、多版本 Node/Python Matrix 并行构建、Docker 镜像分层缓存、Lint+Test+Build+Publish 分阶段、条件执行、环境矩阵、失败重试和发布门禁最佳实践，附完整工作流代码。",
    "excerpt_en": "Production GitHub Actions pipeline from scratch: npm/pip cache, multi-version Node/Python matrix builds, Docker layer caching, Lint+Test+Build+Publish stages, conditional execution, env matrix, failure retry, and release gating best practices. Complete workflow YAML included.",
    "excerpt_ja": "本番級GitHub Actionsパイプライン設計：npm/pipキャッシュ、マルチバージョンNode/Python Matrix並列ビルド、Dockerレイヤーキャッシュ、Lint/Test/Build/Publish段階化、条件実行、環境マトリクス、失敗リトライとリリースゲートベストプラクティス。完全ワークフロー付き。",
    "excerpt_zh_hant": "從零設計一套工業級 GitHub Actions 流水線：npm/pip 依賴緩存、多版本 Node/Python Matrix 並行構建、Docker 鏡像分層緩存、Lint+Test+Build+Publish 分階段、條件執行、環境矩陣、失敗重試和發佈門禁最佳實踐，附完整工作流代碼。",
    "category_slug": "tools",
    "tag_slugs": ["git", "docker", "nodejs", "python"],
    "cover_theme": "cyan",
    "code_language": "yaml",
    "code_snippet": """.github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
    tags: ['v*.*.*']
  pull_request:
    branches: [main, develop]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      backend: ${{ steps.filter.outputs.backend }}
      frontend: ${{ steps.filter.outputs.frontend }}
      infra: ${{ steps.filter.outputs.infra }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            backend:
              - 'apps/api/**'
              - 'packages/shared/**'
              - 'pyproject.toml'
            frontend:
              - 'apps/web/**'
              - 'packages/ui/**'
              - 'pnpm-lock.yaml'
            infra:
              - 'infra/**'
              - 'Dockerfile*'

  lint:
    needs: changes
    if: needs.changes.outputs.backend == 'true' || needs.changes.outputs.frontend == 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 8
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with: { version: 9 }
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
          cache-dependency-path: pnpm-lock.yaml
      - name: Install Node deps
        run: pnpm install --frozen-lockfile --prefer-offline
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip
          cache-dependency-path: pyproject.toml
      - name: Install Python deps
        run: pip install -e ".[dev]" --retries 3
      - name: Run ESLint + Ruff
        run: |
          pnpm lint
          ruff check apps/api packages
      - name: Cache turbo setup
        uses: actions/cache@v4
        with:
          path: .turbo
          key: turbo-${{ github.sha }}
          restore-keys: turbo-

  test:
    needs: lint
    runs-on: ubuntu-latest
    timeout-minutes: 20
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.11', '3.12', '3.13']
        node-version: ['18', '20', '22']
        os: [ubuntu-latest]
        include:
          - os: macos-latest
            python-version: '3.12'
            node-version: '20'
    services:
      postgres:
        image: postgres:16-alpine
        env: { POSTGRES_USER: test, POSTGRES_PASSWORD: test, POSTGRES_DB: test }
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready
          --health-interval 10s --health-timeout 5s --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ['6379:6379']
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4; with: { version: 9 }
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: pnpm
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - run: pnpm install --frozen-lockfile
      - run: pip install -e ".[test]"
      - name: Run tests with coverage
        run: |
          pnpm test -- --coverage --reporter=github
          pytest apps/api --cov=apps/api --cov-report=xml
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test
          REDIS_URL: redis://localhost:6379
      - uses: codecov/codecov-action@v4
        if: matrix.os == 'ubuntu-latest' && matrix.node-version == '20' && matrix.python-version == '3.12'
        with: { fail_ci_if_error: false, token: ${{ secrets.CODECOV_TOKEN }} }

  build-and-push-image:
    needs: test
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix=
      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          platforms: linux/amd64,linux/arm64
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
""",
    "content_zh": "# CI/CD Pipeline 设计：GitHub Actions + Cache + Matrix Build\n\nCI/CD 是研发效率的脊梁。设计差的流水线 PR 等 40 分钟、随机失败、无法复用；设计好的流水线 5 分钟内给出可信反馈，并发矩阵覆盖多版本多 OS，缓存命中让重复构建秒过。\n\n## 阶段拆分与路径过滤\n\n经典 5 阶段：(1) changes 路径过滤：未改动的子项目整段跳过（PR 只改文档不跑后端测试）；(2) lint 阶段快失败优先（8 分钟内出结果）；(3) test 多版本矩阵并发；(4) build 构建产物；(5) 打 tag 才执行 publish 推送镜像/发布包。concurrency 同 ref 自动取消旧运行，节省 Action 分钟。\n\n```yaml\n{code}\n```\n\n## 缓存矩阵构建加速三剑客\n\n(1) 依赖缓存：setup-node + pnpm cache、pip cache 让 90% 构建免装依赖；(2) 任务产物缓存：turbo cache 跨工作流复用构建结果；(3) Docker 层缓存：buildx gha cache 复用层，推送时间从 5 分钟缩到 40 秒。Matrix 跨 OS/版本覆盖 Python 3.11-3.13 × Node 18-22，矩阵 include 注入 MacOS 单测确保 Unix 类兼容性。\n\n| 优化项 | 未优化耗时 | 优化后耗时 | 节省比例 |\n|--------|----------|----------|---------|\n| npm/pip 依赖安装 | 3min | 20s (95%命中) | 89% |\n| Turborepo 构建 | 6min | 15s (全命中) | 96% |\n| Docker 镜像推送 | 5min | 40s | 87% |\n| Matrix 顺序执行 | 30min | 6min (5并发) | 80% |\n| 路径过滤跳过 | 20min/每次PR | 3min | 85% |\n\n## 最佳实践\n\ntimeout-minutes 每个 Job 强制上限防挂死；services 用 Postgres/Redis 健康检查等待就绪后再跑；fail-fast:false 保证所有组合跑完不提前中断；最终 semver tag 触发发布流程，main 分支仅 build+test 止。",
    "content_en": "# CI/CD Pipeline Design: GitHub Actions + Cache + Matrix Build\n\nCI/CD is the backbone of engineering throughput. Poor design forces 40+ min PR waits and random failures; well-designed pipelines deliver trusted feedback under 5 minutes, run matrix tests across versions/OSes, and cache hits make repeat builds instant.\n\n## Stage Split and Path Filtering\n\nClassic 5 phases: (1) changes filter: skip entire untouched subtrees (docs-only PR bypasses backend tests); (2) lint stage fast-fails within 8 min max; (3) test multi-version matrix parallel; (4) build artifacts; (5) publish on git tags only. Concurrency auto-cancels prior runs on same ref, saves Action minutes.\n\n```yaml\n{code}\n```\n\n## Cache + Matrix Build: Three Musketeers of Speed\n\n(1) Dep cache: setup-node pnpm cache + pip cache skip install on 90%+ builds; (2) Task artifact cache: turbo cache shares builds across workflow runs; (3) Docker layer cache: buildx gha cache reuses layers, push drops from 5 min to 40s. Matrix spans Python 3.11-3.13 × Node 18-22 across OSes; matrix include injects macOS single run to catch Unix-compat regressions.\n\n| Optimization | Baseline Duration | Optimized | Savings |\n|-------------|------------------|-----------|---------|\n| npm/pip install | 3 min | 20s (95% hit) | 89% |\n| Turborepo build | 6 min | 15s (full hit) | 96% |\n| Docker image push | 5 min | 40s | 87% |\n| Matrix sequential | 30 min | 6 min (5 parallel) | 80% |\n| Path filtering skip | 20 min / PR | 3 min | 85% |\n\n## Best Practices\n\nEvery job sets timeout-minutes hard cap against hangs. services use Postgres/Redis healthcheck before test start. fail-fast:false keeps all matrix combos running to surface every failure. Only semver tags trigger publish; main branch stops at build+test only."
},
{
    "title_zh": "Tailwind CSS v4 新特性：Zero-config + CSS-native 变量",
    "title_en": "Tailwind CSS v4: Zero-config + CSS-native Variables",
    "title_ja": "Tailwind CSS v4 新機能：Zero-config + CSS ネイティブ変数",
    "title_zh_hant": "Tailwind CSS v4 新特性：Zero-config + CSS-native 變數",
    "excerpt_zh": "Tailwind CSS v4 是一次架构级升级：彻底抛弃 tailwind.config.js，用 @theme 块在原生 CSS 文件声明设计令牌；新增 @import \"tailwindcss\" 单入口代替 postcss.config；内置 CSS 变量、容器查询原生支持、oxc 引擎提速 10-40 倍、颜色函数简化。",
    "excerpt_en": "Tailwind CSS v4 is an architectural upgrade: goodbye tailwind.config.js, declare design tokens in @theme blocks inside native CSS files. Single @import \"tailwindcss\" entry replaces postcss.config; built-in CSS vars, native container queries, oxc engine 10-40x faster, simplified color functions.",
    "excerpt_ja": "Tailwind CSS v4はアーキテクチャ級アップデート：tailwind.config.js を廃止し、ネイティブCSS内の@themeブロックでデザイントークン宣言。@import \"tailwindcss\" 単一エントリでpostcss設定不要。CSS変数内蔵、Container Queriesネイティブ対応、oxcエンジンで10-40倍高速化、カラー関数簡略化。",
    "excerpt_zh_hant": "Tailwind CSS v4 是一次架構級升級：徹底拋棄 tailwind.config.js，用 @theme 塊在原生 CSS 文件聲明設計令牌；新增 @import \"tailwindcss\" 單入口代替 postcss.config；內置 CSS 變量、容器查詢原生支持、oxc 引擎提速 10-40 倍、顏色函數簡化。",
    "category_slug": "frontend",
    "tag_slugs": ["css", "typescript", "react", "vue"],
    "cover_theme": "amber",
    "code_language": "vue",
    "code_snippet": """/** @type {import('tailwindcss').Config} 以前 tailwind.config.js 写法现在不要了 **/
/* ====== app.css v4 新写法：零配置 @theme 块 ====== */
@import "tailwindcss";

@theme {
  --color-brand-50: #effaf5;
  --color-brand-100: #d9f2e5;
  --color-brand-500: #11a97a;
  --color-brand-600: #0e8a63;
  --color-surface: #0b0d12;
  --color-muted: color-mix(in oklab, var(--color-surface), white 65%);

  --font-sans: "Inter", "PingFang SC", "Noto Sans JP", ui-sans-serif, system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;

  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-xl: 1.5rem;
  --radius-2xl: 2rem;

  --shadow-card: 0 1px 2px rgba(0,0,0,0.04), 0 12px 32px -16px rgba(0,0,0,0.25);
  --shadow-glow: 0 0 0 1px color-mix(in oklab, var(--color-brand-500), transparent 70%),
                 0 0 32px -8px color-mix(in oklab, var(--color-brand-500), transparent 40%);

  --spacing-18: 4.5rem;
  --spacing-88: 22rem;
  --spacing-128: 32rem;

  --animate-float: float 6s ease-in-out infinite;
  --animate-shimmer: shimmer 2s linear infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}
@keyframes shimmer {
  from { background-position: -200% 0; }
  to   { background-position: 200% 0; }
}

@layer utilities {
  .text-balance { text-wrap: balance; }
  .bg-grid {
    background-image: linear-gradient(currentColor 1px, transparent 1px),
                      linear-gradient(90deg, currentColor 1px, transparent 1px);
    background-size: 24px 24px;
  }
  .mask-fade-b {
    mask-image: linear-gradient(to bottom, black 60%, transparent);
  }
}

/* 媒体查询 & 容器查询 v4 原生支持 */
@container card (min-width: 420px) {
  .card-title { font-size: 1.5rem; }
}
@media (prefers-color-scheme: dark) {
  :root { color-scheme: dark; }
}

/* ====== 业务组件中使用 ====== */
.card {
  @apply bg-white dark:bg-zinc-900/60 backdrop-blur-md rounded-2xl shadow-card p-8 transition-all duration-300;
}
.card:hover {
  @apply shadow-glow -translate-y-1;
}

/* ====== nextjs app router 入口 ====== */
// app/globals.css 首行导入即可，不需要 tailwind.config.js
// tailwindcss v4 依赖：npm i tailwindcss @tailwindcss/next
// next.config.mjs:
import createMDX from "@next/mdx";
import tailwindcss from "@tailwindcss/next";

/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: { optimizePackageImports: ["shiki", "@shikijs/rehype"] },
};

export default tailwindcss(createMDX()(nextConfig));

// React 组件里直接用新的工具类
export function PricingCard({ tier }: { tier: "pro" | "enterprise" }) {
  const highlight = tier === "enterprise" ? "ring-2 ring-brand-500/40" : "";
  return (
    <article className={`card ${highlight} @lg:flex-row`}>
      <h3 className="card-title text-2xl font-semibold tracking-tight text-balance">
        {tier === "enterprise" ? (
          <span className="bg-gradient-to-r from-brand-500 to-brand-300 bg-clip-text text-transparent">
            Enterprise
          </span>
        ) : "Pro Plan"}
      </h3>
      <div className="mt-6 space-y-4 text-sm text-zinc-600 dark:text-zinc-300">
        <Feature text="SSO SAML / SCIM provisioning" />
        <Feature text="99.99% uptime SLA" />
        <Feature text="Dedicated CSM" />
      </div>
    </article>
  );
}
""",
    "content_zh": "# Tailwind CSS v4 新特性：Zero-config + CSS-native 变量\n\nTailwind CSS v4 是 2024 年底发布的架构级重写，最大变化是\"回归 CSS 本身\"：以前 tailwind.config.js 的所有能力现在都能用原生 CSS 的 @theme 和 CSS 变量实现，配合 oxc 引擎比 v3 快 10-40 倍。\n\n## 零配置与 @theme 设计令牌\n\n彻底删除 tailwind.config.js。入口文件只需要一行 @import \"tailwindcss\"；所有主题令牌（颜色、字体、阴影、间距、动画）在同个 CSS 文件用 @theme 块声明，和 CSS 自定义属性语法完全一致。Next.js/Vite 无需 postcss.config 即可生效，新手上手门槛降低 50%。\n\n```css\n{code}\n```\n\n## 内置 oxc 引擎 & 容器查询 & @layer utilities\n\n新编译器 oxc 用 Rust 写，10k 文件项目构建从 8s 降到 300ms。@media 媒体查询、@container 容器查询、@property、color-mix 都是一等公民支持，无需插件。@layer utilities 定义项目专属工具类，和官方工具类一起参与 JIT 排序与 purge。\n\n| 维度 | Tailwind CSS v3 | Tailwind CSS v4 |\n|------|----------------|----------------|\n| 配置文件 | tailwind.config.js（TypeScript） | 零配置，CSS @theme 块 |\n| 编译器 | PostCSS + js | oxc (Rust) 10-40x |\n| CSS 原生特性 | 部分通过插件 | @property / container / color-mix 全支持 |\n| 设计令牌来源 | config.theme + preset 合并 | 纯 CSS 变量，浏览器原生可覆盖 |\n| 框架集成 | postcss.config 必配 | @tailwindcss/next / @tailwindcss/vite 零配置 |\n\n## 最佳实践\n\n沿用 v3 的 JIT 命名习惯但迁移配置到 @theme。旧项目用官方升级工具 npx @tailwindcss/upgrade 一键迁移。不要混用 @apply 超过 5 个类，复杂样式直接写原生 CSS 配合 theme() 函数取值。",
    "content_en": "# Tailwind CSS v4: Zero-config + CSS-native Variables\n\nTailwind CSS v4 is the late-2024 architectural rewrite - its biggest shift is \"going back to CSS itself\". Everything previously in tailwind.config.js is now expressed via native CSS @theme blocks and CSS variables, and the new oxc engine delivers 10-40x speedup over v3.\n\n## Zero-config & @theme Design Tokens\n\nDelete tailwind.config.js entirely. Entry CSS needs only one line: @import \"tailwindcss\". All theme tokens (colors, font stacks, shadows, spacing, animations) live inside the same CSS file in @theme block using real CSS custom-property syntax. Works with Next.js/Vite with no postcss.config - onboarding friction cut in half.\n\n```css\n{code}\n```\n\n## Bundled oxc Engine, Container Queries, @layer utilities\n\nNew Rust-based oxc compiler cuts 10k-file project build from 8s to 300ms. @media queries, @container queries, @property, color-mix are first-class citizens - no plugins required. @layer utilities defines project-specific utility classes that join official utilities in JIT sorting and purge.\n\n| Dimension | Tailwind CSS v3 | Tailwind CSS v4 |\n|-----------|----------------|----------------|\n| Config file | tailwind.config.js (TS) | Zero-config, CSS @theme block |\n| Compiler | PostCSS + JS | oxc (Rust) 10-40x |\n| Native CSS features | Partial via plugins | @property/container/color-mix full support |\n| Design token source | config.theme + preset merge | Pure CSS vars, browser-overridable |\n| Framework integration | postcss.config required | @tailwindcss/next / @tailwindcss/vite zero-config |\n\n## Best Practices\n\nKeep v3 JIT naming habits but migrate configs to @theme. For legacy projects run `npx @tailwindcss/upgrade` one-shot migration. Don't stack @apply beyond 5 utilities; for complex compositions write native CSS pulling tokens via theme() function."
},

{
    "title_zh": "PWA 离线应用实战：Service Worker + IndexedDB + Background Sync",
    "title_en": "PWA Offline App in Practice: Service Worker + IndexedDB + Background Sync",
    "title_ja": "PWA オフラインアプリ実践：Service Worker + IndexedDB + Background Sync",
    "title_zh_hant": "PWA 離線應用實戰：Service Worker + IndexedDB + Background Sync",
    "excerpt_zh": "逐步构建可安装、可离线运行、网络恢复自动同步的 Progressive Web App：Service Worker 缓存策略（Cache First / Stale-While-Revalidate）、IndexedDB 封装结构化本地数据、Background Sync 后台队列在用户离线操作后网络恢复时自动提交变更，附完整 TS 代码。",
    "excerpt_en": "Build installable, offline-first Progressive Web Apps: Service Worker caching strategies (Cache First, Stale-While-Revalidate), IndexedDB wrapper for structured local data, Background Sync queue that replays offline operations when network returns. Full TypeScript code included.",
    "excerpt_ja": "インストール可能・オフラインファーストなPWAを段階的構築：Service Worker キャッシュ戦略（Cache First / Stale-While-Revalidate）、構造化ローカルデータ用IndexedDBラッパー、ネットワーク復旧時にオフライン操作を自動リプレイするBackground Syncキュー。完全TypeScriptコード付き。",
    "excerpt_zh_hant": "逐步構建可安裝、可離線運行、網絡恢復自動同步的 Progressive Web App：Service Worker 緩存策略（Cache First / Stale-While-Revalidate）、IndexedDB 封裝結構化本地數據、Background Sync 後台隊列在用戶離線操作後網絡恢復時自動提交變更，附完整 TS 代碼。",
    "category_slug": "frontend",
    "tag_slugs": ["javascript", "typescript", "vue", "nextjs"],
    "cover_theme": "blue",
    "code_language": "typescript",
    "code_snippet": """// ====== sw.ts Service Worker - Vite 推荐用 vite-plugin-pwa ======
import { PrecacheEntry } from 'workbox-precaching/_types';
import { precacheAndRoute, cleanupOutdatedCaches } from 'workbox-precaching';
import { registerRoute, NavigationRoute } from 'workbox-routing';
import { CacheFirst, StaleWhileRevalidate, NetworkFirst } from 'workbox-strategies';
import { CacheableResponsePlugin } from 'workbox-cacheable-response';
import { ExpirationPlugin } from 'workbox-expiration';
import { backgroundSyncQueue } from './lib/bg-sync';

declare const self: ServiceWorkerGlobalScope;

cleanupOutdatedCaches();
precacheAndRoute(self.__WB_MANIFEST as unknown as PrecacheEntry[]);

// 1. SPA 导航请求：NetworkFirst，失败 fallback 到 /index.html
registerRoute(
  new NavigationRoute(new NetworkFirst({
    networkTimeoutSeconds: 3,
    cacheName: 'app-shell',
    plugins: [new CacheableResponsePlugin({ statuses: [0, 200] })]
  }))
);

// 2. 静态资源：Cache First 且限制数量
registerRoute(
  ({ request, sameOrigin }) => sameOrigin &&
    ['style', 'script', 'worker', 'font', 'image'].includes(request.destination),
  new CacheFirst({
    cacheName: 'static-assets-v1',
    plugins: [
      new CacheableResponsePlugin({ statuses: [0, 200] }),
      new ExpirationPlugin({ maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 * 30 })
    ]
  })
);

// 3. API GET：Stale-While-Revalidate — 立返缓存，后台静默更新
registerRoute(
  ({ url, request }) => request.method === 'GET' && url.pathname.startsWith('/api/v1/'),
  new StaleWhileRevalidate({
    cacheName: 'api-read-v1',
    plugins: [
      new CacheableResponsePlugin({ statuses: [200] }),
      new ExpirationPlugin({ maxEntries: 500, maxAgeSeconds: 60 * 5 })
    ]
  })
);

// 4. API POST/PUT/DELETE：失败时进入 Background Sync 队列
self.addEventListener('fetch', (event: FetchEvent) => {
  const req = event.request;
  if (!['POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method)) return;
  if (!req.url.includes('/api/v1/')) return;
  event.respondWith((async () => {
    try {
      const cloned = req.clone();
      return await fetch(req);
    } catch (err) {
      await backgroundSyncQueue.enqueue(cloned);
      await self.registration.sync.register('outbox-sync');
      return new Response(JSON.stringify({
        ok: false,
        queued: true,
        message: '已进入离线队列，网络恢复后自动发送'
      }), { status: 202, headers: { 'Content-Type': 'application/json' } });
    }
  })());
});

// ====== lib/idb.ts — IndexedDB 封装（用 idb 库）======
import { openDB, DBSchema, IDBPDatabase } from 'idb';

interface AppDB extends DBSchema {
  drafts: {
    key: string;
    value: { id: string; title: string; body: string; createdAt: number; pending: boolean };
    indexes: { 'by-created': number; 'by-pending': boolean };
  };
  settings: { key: string; value: any };
}

const DB_NAME = 'pwa-app-db';
const DB_VERSION = 2;

export async function getDB(): Promise<IDBPDatabase<AppDB>> {
  return openDB<AppDB>(DB_NAME, DB_VERSION, {
    upgrade(db, oldVer, newVer, tx) {
      if (!db.objectStoreNames.contains('drafts')) {
        const s = db.createObjectStore('drafts', { keyPath: 'id' });
        s.createIndex('by-created', 'createdAt');
        s.createIndex('by-pending', 'pending');
      }
      if (!db.objectStoreNames.contains('settings')) {
        db.createObjectStore('settings');
      }
    }
  });
}

export const DraftRepo = {
  async list(pending?: boolean) {
    const db = await getDB();
    if (pending !== undefined) return db.getAllFromIndex('drafts', 'by-pending', pending);
    return db.getAll('drafts');
  },
  async save(draft: AppDB['drafts']['value']) {
    const db = await getDB();
    await db.put('drafts', draft);
  },
  async delete(id: string) {
    const db = await getDB();
    await db.delete('drafts', id);
  }
};

// ====== 应用入口 main.ts 注册 SW + 离线状态监听 ======
import { registerSW } from 'virtual:pwa-register';

const updateSW = registerSW({
  immediate: true,
  onOfflineReady() { console.log('[PWA] 缓存就绪，可离线使用'); },
  onNeedRefresh() {
    if (confirm('检测到新版本，是否立即刷新？')) updateSW(true);
  },
});

window.addEventListener('online', async () => {
  if ('SyncManager' in window) return;
  // 浏览器不支持 SyncManager 时兜底：上线立即重放队列
  const pending = await DraftRepo.list(true);
  for (const d of pending) {
    try {
      await fetch('/api/v1/drafts', { method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(d) });
      d.pending = false; await DraftRepo.save(d);
    } catch {}
  }
});

export function useApp() {
  const isOnline = ref(navigator.onLine);
  onMounted(() => {
    window.addEventListener('online',  () => (isOnline.value = true));
    window.addEventListener('offline', () => (isOnline.value = false));
  });
  return { isOnline, DraftRepo };
}
""",
    "content_zh": "# PWA 离线应用实战：Service Worker + IndexedDB + Background Sync\n\nPWA（Progressive Web App）在 Chrome/Edge/Safari/iOS 16.4+ 都已原生支持，能把 Web 应用安装到用户桌面，离线可用、离线提交、网络恢复自动同步，体验已接近原生 App，且无需过审上架商店。\n\n## Service Worker 缓存策略\n\nApp Shell（HTML壳+首屏资源）用 NetworkFirst，3 秒未响应回退缓存，保障弱网秒开；静态图片/字体/脚本用 Cache First + 容量上限；API GET 列表页用 Stale-While-Revalidate（立返缓存 + 后台静默更新），让数据总是新的且加载无延迟。\n\n```typescript\n{code}\n```\n\n## IndexedDB 结构化存储 + Background Sync\n\nlocalStorage 只有 5MB 同步阻塞，不适合结构化数据。用 IndexedDB 存草稿/聊天记录/订单，可查询、可索引、可批量，容量可达数 GB。所有写操作（POST/PUT/DELETE）失败时推入 Background Sync 队列，注册 sync 事件，用户重新联网后 Service Worker 自动按顺序重放，保证离线操作 100% 不丢。\n\n| 存储技术 | 容量 | 异步 | 结构化/索引 | 持久化 | 适用场景 |\n|---------|-----|-----|-----------|-------|---------|\n| localStorage | ~5MB | 否 | 否 | 部分手动清 | Token/偏好设置 |\n| sessionStorage | ~5MB | 否 | 否 | 会话内消失 | 临时状态 |\n| Cache API | 不限策略制 | 是 | URL键/Response | 按缓存策略 | 静态文件+API GET响应 |\n| IndexedDB | 数十GB | 是 | 完整Schema/索引/事务 | 持久保存 | 结构化业务数据 |\n| OPFS (File System) | 数百GB | 是 | 文件流API | 持久保存 | 大文件/媒体编辑 |\n\n## 最佳实践\n\n用 Vite + vite-plugin-pwa 避免手写 Manifest/SW。iOS 有 3 个大坑：SW 每 7 天重置、推送通知需添加到主屏后才可用、视频 autoplay 需静音。写操作一定要在应用层给 UI 反馈：\"已保存草稿，稍后联网自动同步\"。",
    "content_en": "# PWA Offline App in Practice: Service Worker + IndexedDB + Background Sync\n\nPWA is natively supported in Chrome/Edge/Safari/iOS 16.4+. Installs to user home screen, works offline, accepts writes offline, replays on network return. Experience approaches native without App Store review walls.\n\n## Service Worker Caching Strategies\n\nApp Shell (HTML + first-paint assets) uses NetworkFirst with 3s timeout fallback to cache for instant weak-network render. Static images/fonts/scripts use Cache First with capacity caps. API GET list endpoints use Stale-While-Revalidate — return cache instantly while background silently fetches fresh copy — always-new data with zero perceived latency.\n\n```typescript\n{code}\n```\n\n## IndexedDB Structured Store + Background Sync\n\nlocalStorage is 5MB sync-blocking and unsuitable for structured data. IndexedDB stores drafts/chat/orders with queries, indexes, batches, multi-GB capacity. All writes (POST/PUT/DELETE) that fail go into Background Sync queue; sync event fires when user reconnects and SW replays them in sequence, guaranteeing zero loss for offline actions.\n\n| Storage | Quota | Async | Structured/Indexes | Persistence | Use Case |\n|---------|-------|-------|-------------------|-------------|----------|\n| localStorage | ~5MB | No | No | Partial manual purge | Tokens, prefs |\n| sessionStorage | ~5MB | No | No | Per session only | Temp state |\n| Cache API | Unbounded (policy) | Yes | URL key / Response | Per cache strategy | Static files + API GET responses |\n| IndexedDB | Tens of GB | Yes | Full schema/indexes/transactions | Persistent | Structured business data |\n| OPFS (File System) | Hundreds GB | Yes | File stream API | Persistent | Large files, media editing |\n\n## Best Practices\n\nUse Vite + vite-plugin-pwa to skip manual Manifest/SW boilerplate. Three iOS gotchas: SW resets every 7 days, push requires add-to-home-screen, video autoplay needs mute. Always give app-layer UI feedback for writes: \"Saved as draft. Will sync when you're back online.\""
},
{
    "title_zh": "Zero Trust 安全架构入门：永不信任，始终验证",
    "title_en": "Zero Trust Security Architecture: Never Trust, Always Verify",
    "title_ja": "Zero Trust セキュリティアーキテクチャ入門：決して信用せず、常に検証",
    "title_zh_hant": "Zero Trust 安全架構入門：永不信任，始終驗證",
    "excerpt_zh": "零信任安全模型系统入门：以\"永不信任，始终验证\"为核心原则，打破传统边界防护（VPN=内部可信）的思维。从身份认证（MFA/SAML）、设备健康检查、最小权限 RBAC、微隔离 mTLS、持续信任评分到可观测审计链路的 6 大支柱详解，附落地实施路线。",
    "excerpt_en": "Zero Trust security model primer: built on \"never trust, always verify\" and dismantles traditional VPN-equals-trusted perimeter thinking. Six pillars explained — identity (MFA/SAML), device health checks, least-privilege RBAC, microsegmentation mTLS, continuous trust scoring, observable audit trail — with implementation roadmap.",
    "excerpt_ja": "Zero Trust セキュリティモデル体系入門：「決して信用せず、常に検証」を原則に、伝統的 VPN=内部信頼の境界防衛思考を打ち砕く。身元認証（MFA/SAML）、端末健康チェック、最小権限RBAC、マイクロセグメンテーションmTLS、継続的信用スコア、可視化監査ログの6本柱を解説、実装ロードマップ付き。",
    "excerpt_zh_hant": "零信任安全模型系統入門：以\"永不信任，始終驗證\"為核心原則，打破傳統邊界防護（VPN=內部可信）的思維。從身份認證（MFA/SAML）、設備健康檢查、最小權限 RBAC、微隔離 mTLS、持續信任評分到可觀測審計鏈路的 6 大支柱詳解，附落地實施路線。",
    "category_slug": "technology",
    "tag_slugs": ["security", "kubernetes", "linux", "docker"],
    "cover_theme": "red",
    "code_language": "bash",
    "code_snippet": """# ====== 1. SPIFFE SPIRE 颁发服务身份（Workload Identity）======
# 注册 workload registration entry
spire-server entry create \
  -parentID "spiffe://example.com/k8s-ns/production" \
  -spiffeID "spiffe://example.com/svc/payment-gateway" \
  -selector "k8s:ns" \
  -selector "k8s:sa" \
  -value "payment-sa" \
  -dns "payment.internal.example.com" \
  -ttl 3600

# ====== 2. Istio 授权策略（服务粒度 mTLS + RBAC）======
cat <<'EOF' | kubectl apply -f -
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: payment-rbac
  namespace: production
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: payment-gateway
  action: ALLOW
  rules:
    - from:
        - source:
            principals:
              - "cluster.local/ns/production/sa/order-service"
              - "cluster.local/ns/production/sa/checkout-worker"
      to:
        - operation:
            methods: ["POST"]
            paths: ["/v1/charges", "/v1/refunds"]
      when:
        - key: request.auth.claims[roles]
          values: ["payments:write"]
EOF

# ====== 3. OPA Gatekeeper 命名空间隔离 ======
cat <<'EOF' | kubectl apply -f -
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: namespace-must-have-owner-and-tier
spec:
  match:
    kinds: [{ apiGroups: [""], kinds: ["Namespace"] }]
  parameters:
    labels:
      - key: "security.example.com/owner"
      - key: "security.example.com/data-tier"
        allowedRegex: "^(public|internal|restricted)$"
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sDisallowedPrivileged
metadata:
  name: block-privileged-containers-in-restricted
spec:
  match:
    scope: Namespaced
    kinds: [{ apiGroups: [""], kinds: ["Pod"] }]
    labelSelector:
      matchExpressions:
        - key: security.example.com/data-tier
          operator: In
          values: ["restricted"]
EOF

# ====== 4. 身份层：Keycloak MFA + 条件访问策略 ======
# 启用 TOTP OTP + WebAuthn (Passkey) 双重挑战
kcadm.sh update authentication/flows -r master \
  --alias "browser" -b '{
  "authenticationExecutions": [
    {"authenticator":"auth-cookie","requirement":"ALTERNATIVE"},
    {"authenticator":"identity-provider-redirector","requirement":"ALTERNATIVE"},
    {"level":"1","required":"true","requirement":"CONDITIONAL"},
    {"authenticator":"basic-auth","requirement":"REQUIRED"},
    {"authenticator":"conditional-user-configured","requirement":"REQUIRED"},
    {"authenticator":"otp-form","requirement":"REQUIRED"},
    {"authenticator":"webauthn-authenticator","requirement":"ALTERNATIVE"}
  ]}'

# 按风险评分拒访：异常IP + 非受管设备
kcadm.sh create clients -r master -s clientId=risk-engine \
  -s 'attributes."risk.score.threshold"=70' \
  -s 'attributes."risk.check.geo_anomaly"=true' \
  -s 'attributes."risk.check.managed_device"=true'

# ====== 5. 审计事件转发 SIEM ======
# Falco 运行时异常规则
cat <<'EOF' > /etc/falco/rules.d/zero-trust-rules.yaml
- rule: DB 服务向外建立可疑连接
  desc: MySQL/PG 不应主动发起外连，可能发生数据外泄
  condition: >
    spawned_process and proc.name in (mysql, postgres) and
    outbound and not fd.sip in (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
  output: >
    DB 服务疑似数据外泄 user=%user.name proc=%proc.name
    dst_ip=%fd.sip dst_port=%fd.sport cmd=%proc.cmdline
  priority: CRITICAL
  tags: [zero-trust, data-exfiltration, mitre:T1041]
EOF
systemctl restart falco
falco -r /etc/falco/falco_rules.yaml -r /etc/falco/rules.d/zero-trust-rules.yaml

# ====== 6. Tailscale + OIDC 取代 VPN：每用户按设备入网 ======
tailscale up \
  --ssh \
  --accept-dns \
  --accept-routes \
  --exit-node="" \
  --auth-key="tskey-client-XXX" \
  --advertise-tags=tag:backend,tag:production

# 在 Tailscale ACL 控制台写入最小权限
# "acls": [ { "action": "accept", "src": ["group:sre"],
#             "dst": ["tag:production:*", "tag:backend:22"] } ]
""",
    "content_zh": "# Zero Trust 安全架构入门：永不信任，始终验证\n\n传统安全模型的假设是\"内网=安全、VPN接入=可信\"，而在云原生、远程办公、供应链攻击（SolarWinds级）频繁的今天，边界早已不存在。NIST SP 800-207 零信任定义：每一次访问都显式认证授权、最小权限授予、所有流量加密、全程可审计。\n\n## 六大核心支柱落地\n\n身份（Identity）是新的边界：OIDC/SAML 统一登录，强制 MFA（TOTP + Passkey 二选一+以上），按风险评分加挑战。设备（Device）健康：MDM 验证 OS 补丁、杀毒、磁盘加密，非受管设备只允许访问隔离沙箱。微隔离：服务间严格 mTLS，授权策略按服务身份 + 方法 + 路径三元组，绝不按网段放行。\n\n```bash\n{code}\n```\n\n## 控制面 + 数据面 + 审计面三层\n\n控制面用 SPIRE/Istio 签发短生命周期 X.509/SVID 身份（1小时TTL，泄漏可快速吊销），OPA/Gatekeeper 静态约束策略。数据面每个服务的 Sidecar/内核 eBPF（Cilium）按授权策略逐包过滤。审计面：Falco 运行时异常规则、K8s Audit Log、Keycloak 登录事件全部汇聚 SIEM（Splunk/Elastic），关联用户身份+设备指纹+服务请求，支撑事后溯源与合规。\n\n| 旧边界模型 | Zero Trust 模型 |\n|-----------|----------------|\n| 信任前提：内部网段自动可信 | 信任前提：每一次请求显式验证 |\n| 认证点：一次登录进VPN通行全程 | 认证点：身份+设备+信任评分 每请求或每小时重评估 |\n| 网络层：VLAN/ACL 分段 | 网络层：默认拒绝，服务粒度 mTLS 微隔离 |\n| 权限：Role 粗粒度 过度授权 | 权限：ABAC 动态属性 + JIT 临时提权 用完收回 |\n| 日志：分散设备/应用各存一份 | 日志：结构化聚合 可溯源整条访问链路 UID |\n| 响应：入侵后修复 以天计 | 响应：实时吊销身份 秒级阻断 |\n\n## 最佳实践\n\n三阶段路线图：P1（1-3月）统一身份+强制MFA+VPN替换为ZTNA；P2（3-6月）K8s mTLS STRICT + 授权策略落地；P3（6-12月）运行时 eBPF 检测+全链路审计+ABAC 动态授信。零信任不是产品，是架构演进，需要持续投资。",
    "content_en": "# Zero Trust Security Architecture: Never Trust, Always Verify\n\nTraditional perimeter security assumed \"internal network = safe, VPN = trusted\". Cloud-native work, remote teams, and SolarWinds-class supply chain attacks killed that boundary. NIST SP 800-207 defines Zero Trust: every access gets explicit authentication, least-privilege authorization, encryption of all traffic, and end-to-end auditability.\n\n## Six Core Pillars Implementation\n\nIdentity is the new perimeter: OIDC/SAML SSO with mandatory MFA (TOTP + Passkey minimum), step-up challenges by risk score. Device health: MDM verifies OS patches, EDR, full-disk-encryption; unmanaged devices get only sandboxed access. Microsegmentation: strict service-to-service mTLS, authorization by identity+method+path triples, never by CIDR block.\n\n```bash\n{code}\n```\n\n## Control Plane + Data Plane + Audit Plane Layers\n\nControl plane (SPIRE/Istio) issues short-lived X.509/SVID (1h TTL so leaks revoke fast); OPA/Gatekeeper does static constraint policy. Data plane per-service Sidecar or kernel eBPF (Cilium) packet-level enforces authorization. Audit plane: Falco runtime rules, K8s audit logs, Keycloak events all streamed to SIEM (Splunk/Elastic) — correlated by user ID + device fingerprint + service request ID for forensic timelines and compliance.\n\n| Legacy Perimeter Model | Zero Trust Model |\n|-----------------------|-----------------|\n| Trust premise: internal subnet = auto trusted | Trust premise: every request explicitly verified |\n| Auth checkpoint: once on VPN = blanket pass | Auth checkpoint: identity + device + risk score, re-evaluated per-request or hourly |\n| Networking: VLAN/ACL segmentation | Networking: default-deny, per-service mTLS microsegmentation |\n| Permissions: Coarse roles, constant overprovisioning | Permissions: ABAC dynamic attrs + JIT elevation returned after use |\n| Logging: Per-app silos | Logging: Structured aggregation full-chain traceable UID |\n| Incident response: Post-breach remediation in days | Response: Real-time identity revocation in seconds |\n\n## Best Practices\n\nThree-phase roadmap: P1 (1-3mo) unify identity + mandate MFA + replace VPN with ZTNA; P2 (3-6mo) K8s mTLS STRICT + authz policies; P3 (6-12mo) runtime eBPF detection + end-to-end audit + ABAC dynamic trust. Zero Trust is not a product — it's architectural evolution requiring sustained investment."
},
{
    "title_zh": "Alembic 深度指南：数据库迁移 + 自动生成 + 分支合并",
    "title_en": "Alembic Deep Dive: Migrations, Autogenerate, and Branch Merging",
    "title_ja": "Alembic ディープガイド：DBマイグレーション + 自動生成 + ブランチマージ",
    "title_zh_hant": "Alembic 深度指南：數據庫遷移 + 自動生成 + 分支合併",
    "excerpt_zh": "SQLAlchemy 官方迁移工具 Alembic 完全指南：从 env.py 配置、autogenerate 自动检测模型变更（字段、索引、约束）、批处理脚本、downgrade 回滚策略，到多人并发开发时 migration 分支冲突、head 分叉合并的标准操作流程，附生产部署检查表。",
    "excerpt_en": "Comprehensive Alembic (official SQLAlchemy migration tool) guide: env.py setup, autogenerate detecting model changes (fields, indexes, constraints), batch scripts, downgrade rollback strategies, plus standard SOP for multi-developer migration branch conflicts and divergent head merging, with production deploy checklist.",
    "excerpt_ja": "SQLAlchemy公式マイグレーションツール Alembic 完全ガイド：env.py設定、autogenerateによるモデル変更検出（カラム・インデックス・制約）、バッチスクリプト、ダウングレードロールバック戦略、複数人開発時のマイグレーションコンフリクトとhead分岐マージの標準SOP、本番デプロイチェックリスト付き。",
    "excerpt_zh_hant": "SQLAlchemy 官方遷移工具 Alembic 完全指南：從 env.py 配置、autogenerate 自動檢測模型變更（字段、索引、約束）、批處理腳本、downgrade 回滾策略，到多人併發開發時 migration 分支衝突、head 分叉合併的標準操作流程，附生產部署檢查表。",
    "category_slug": "tutorial",
    "tag_slugs": ["python", "postgresql", "git", "fastapi"],
    "cover_theme": "green",
    "code_language": "python",
    "code_snippet": """# ====== alembic.ini 核心调优 ======
[alembic]
script_location = migrations
sqlalchemy.url = postgresql+psycopg://app:${DB_PASSWORD}@${DB_HOST}:5432/app
prepend_sys_path = .
timezone = Asia/Shanghai

[loggers]
keys = root,sqlalchemy,alembic
[handlers]
keys = console
[formatters]
keys = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S

# ====== migrations/env.py 支持自动生成 + 命名约定 ======
from __future__ import with_statement
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool, MetaData
import os, sys

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
from app.models import Base
from app.db.naming import NAMING_CONVENTION

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata: MetaData = Base.metadata
target_metadata.naming_convention = NAMING_CONVENTION  # 关键：约束自动命名

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite 等支持批处理ALTER
        compare_type=True, compare_server_default=True,
        include_object=include_object_fn
    )
    with context.begin_transaction():
        context.run_migrations()

def include_object_fn(object, name, type_, reflected, compare_to):
    if type_ == "table" and name in {"spatial_ref_sys", "alembic_version"}:
        return False
    return True

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.", poolclass=pool.NullPool, future=True
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
            compare_server_default=True,
            include_object=include_object_fn,
            transaction_per_migration=True,  # 每个迁移独立事务
            lock_timeout=30                   # DDL 锁超时 30s
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

# ====== app/db/naming.py — 约束命名公约防分支冲突 ======
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# ====== 典型迁移 revision 示例：data-only 迁移 ======
'''${message}

Revision ID: 0004_add_user_status
Revises: 0003_user_baseline
Create Date: 2024-06-15 11:22:33

'''
from alembic import op
import sqlalchemy as sa
from sqlalchemy import update
from sqlalchemy.orm import Session

# revision identifiers, used by Alembic.
revision = '0004_add_user_status'
down_revision = '0003_user_baseline'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('users', sa.Column('status', sa.String(16), nullable=False,
                  server_default='ACTIVE'))
    op.create_index('ix_users_status_created', 'users', ['status', 'created_at'])
    bind = op.get_bind(); sess = Session(bind)
    from app.models import User
    sess.execute(update(User).where(User.email.endswith('@test.com')).
                 values(status='INACTIVE'))
    sess.commit()

def downgrade() -> None:
    op.drop_index('ix_users_status_created', 'users')
    op.drop_column('users', 'status')

# ====== 多分支 HEAD 合并：建一个 merge migration ======
# 场景: Alice 分支 head=0005_add_posts, Bob 分支 head=0006_add_tags
# 解决:
#   alembic merge -m "merge posts and tags branches" 0005_add_posts 0006_add_tags
# 生成:
revision = '0007_merge_posts_tags'
down_revision = ('0005_add_posts', '0006_add_tags')
branch_labels = None
depends_on = None

def upgrade(): pass   # merge 迁移通常空实现，只解决 DAG 头分叉
def downgrade(): pass
""",
    "content_zh": "# Alembic 深度指南：数据库迁移 + 自动生成 + 分支合并\n\n数据库 Schema 变更管理是团队协作最容易出事故的一环：手动 DDL 改表忘记录入、生产与本地不一致、多分支合并后 migration 执行死锁。Alembic 作为 SQLAlchemy 官方迁移工具，能自动检测模型变更、版本化、可回滚、支持复杂合并。\n\n## 自动生成与命名约定\n\n命名约定（NAMING_CONVENTION）是多人协作的地基。不加命名约定的话，同一个约束在两台机器 autogenerate 名字随机（如约束名含随机hash），PR 一合并立刻 migration 冲突。env.py 配置 compare_type、compare_server_default 让自动检测更准，避免漏掉 bool 默认值变更、VARCHAR 长度变化这种常见的自动生成漏检。\n\n```python\n{code}\n```\n\n## 分支合并与生产发布流程\n\nAlice 和 Bob 同时拉两个 feature 分支，各写各的 migration，最后 merge 回 main 就会出现\"两个 head\"（分叉）。标准解法：`alembic merge <hash1> <hash2> -m \"merge A and B\"` 生成一个空的 merge revision，把两条链合成一条，down_revision 写成元组。生产发布：(1) 先备份数据库；(2) 事务+DDL锁超时；(3) 超大表（>100万行）用 CREATE INDEX CONCURRENTLY，禁止单一事务包裹长迁移。\n\n| 场景 | 操作命令 | 注意事项 |\n|------|---------|---------|\n| 检测模型变化生成迁移 | alembic revision --autogenerate -m \"msg\" | 生成后必须人工review生成的up/down代码 |\n| 升到最新版本 | alembic upgrade head | CI必须校验 upgrade→downgrade→upgrade 幂等 |\n| 撤回到上一个版本 | alembic downgrade -1 | 数据删除型down要谨慎，最好 data-only 先备份 |\n| 两个 head 分叉合并 | alembic merge head1 head2 -m \"merge\" | merge 迁移通常空实现 |\n| 生成SQL脚本离线部署 | alembic upgrade head --sql | DBA审批流程适用 |\n| 大表索引不锁表建 | op.create_index(..., postgresql_concurrently=True) | 不能在事务里，transaction_per_migration=True |\n\n## 最佳实践\n\n每个迁移拆两类：Schema-only（结构变更，可快速回滚）和 Data-only（数据清洗回填，慎用）。禁止同一 migration 既改表又回写数据。每次 PR 发 CI 检查三件事：upgrade 跑一遍、downgrade 回前一版再 upgrade 一遍（幂等）、和主分支 head 数量一致。",
    "content_en": "# Alembic Deep Dive: Migrations, Autogenerate, and Branch Merging\n\nSchema change management is the most accident-prone part of team collaboration: handwritten DDL not tracked, prod/dev out of sync, deadlocks from migrations after multi-branch merge. As SQLAlchemy's official tool, Alembic auto-detects model changes, versions them rollbackably, and handles complex merges.\n\n## Autogenerate and Naming Convention\n\nNaming convention (NAMING_CONVENTION) is the foundation of team collaboration. Without it, constraint names on two dev machines autogenerate randomly (hash suffixes), causing migration conflicts on PR merge the instant they land. env.py options compare_type + compare_server_default boost detection accuracy, catching common false-negatives like bool default or VARCHAR length tweaks.\n\n```python\n{code}\n```\n\n## Branch Merging and Production Release Flow\n\nAlice and Bob open two feature branches with separate migrations; merging back to main yields \"two divergent heads\". Standard fix: `alembic merge <hash1> <hash2> -m \"merge A and B\"` produces an empty merge revision tying both chains together, with down_revision as a tuple. Production playbook: (1) take DB backup first; (2) per-migration transactions with DDL lock timeout; (3) large tables (>1M rows) use CREATE INDEX CONCURRENTLY — never wrap long migrations in single txn.\n\n| Scenario | Command | Caveats |\n|----------|---------|---------|\n| Auto-detect model change → migration | alembic revision --autogenerate -m \"msg\" | Always human-review generated up/down |\n| Upgrade to latest | alembic upgrade head | CI must verify upgrade→downgrade→upgrade idempotent |\n| Roll back one revision | alembic downgrade -1 | Destructive downgrades: backup-first data-only |\n| Merge two divergent heads | alembic merge h1 h2 -m \"merge\" | Merge migration typically no-op |\n| Offline SQL for DBA review | alembic upgrade head --sql | Use for DBA approval workflows |\n| Online non-blocking index | op.create_index(..., postgresql_concurrently=True) | Cannot run inside txn; use transaction_per_migration=True |\n\n## Best Practices\n\nSplit each migration into Schema-only (structural change, rollback-safe) vs Data-only (backfill/cleanup - use sparingly). Never mix DDL and bulk writes in same migration. Every PR CI runs three checks: upgrade once, downgrade one revision then upgrade again (idempotency), count of migration heads matches main branch count."
}

