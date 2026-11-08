# Rosetta 全栈代码审查报告（2026-11-08）

> **性质**：只读静态审查。未修改任何生产代码，未执行测试 / 构建 / 渗透验证。
> **前次审计**：`docs/fullstack-audit-2026-09-29.md` 是修复记录；本报告不重复其中已修项，只列本次仍存在的问题。
> **保密**：报告不复现任何真实密钥、口令或 `.env` 实际值；下文出现的字符串均为仓库内公开的模板占位符。
> **证据格式**：`路径:行号` 均在本轮逐行复核过；标注「复核」的是我亲自二次打开确认的条目。

---

## 0. 结论

### 0.1 一句话判断

**架构分层和安全意识在水准之上（有 net_guard、魔数校验、Lua 分布式锁、purge 密钥校验、SSR 单源 origin），但存在一个系统性缺陷：「配置」与「代码」之间的契约没有测试钉住，导致一条环境变量名漂移把整个生产安全判定链整体关掉。** 这不是单点漏洞，而是「配置漂移 → 弱密钥 → 权限绕过 → 容器默认态」连成的一条可直接接管的链，必须先止血再谈优化。

### 0.2 分级计数

| 级别 | 数量 | 含义 |
| --- | --- | --- |
| P0 | 2（互为条件，构成一条攻击链） | 上线前必须修；当前仓库默认部署即可匿名接管 |
| P1 | 17 | 安全 7 / 性能与正确性 6 / 工程化交付 4；应在一个迭代内排期 |
| P2 | 10 | 可维护性债，随功能迭代分批偿还 |
| 保留 | — | 第 6 节列出「不要重构」的好设计，避免误伤 |

### 0.3 最高优先级攻击链（组合利用，非单点）

```
① docker-compose.yml:81 写 APP_ENV=production，但 config.py:71 的字段叫 environment
   → pydantic-settings 只认 ENVIRONMENT，extra="ignore"(:52) 静默丢弃 APP_ENV
   → settings.environment 恒为 development，validate_secret_key 的生产分支(:480) 永不执行
② docker-compose.yml:88 的 SECRET_KEY 默认是可预测的公开占位符（且 :84 AUTO_OOBE=1、:97 管理员口令固定）
③ docker-compose.yml:33/57/109 把 PG / Redis / 后端 8000 全绑 0.0.0.0，可绕过 Nginx 直连
④ 用公开 SECRET_KEY 本地签 HS256 JWT（sub=任意用户）即可调用后台；或直接登录默认管理员
```

**任意一条单独修掉都能断链，但只有 ① 修完并补回归测试才能防止复发。**

### 0.4 审查方法与边界

- 四路并行静态探查（后端安全 / 后端性能与可维护性 / 前端与 Nitro BFF / 基础设施与 CI），再由我对 P0/P1 逐条打开源码复核，共精读约 90 个关键文件。
- **未执行**：`pytest`、`vitest`、`nuxt build`、`docker build`、任何 HTTP 请求、任何数据库操作。所有「影响」是静态推断，需在 staging 验证。
- **未核实**：线上 Nginx 实际配置（仓库内只有 80 端口模板，TLS 可能在外部 LB 终止）、真实 `.env` 部署值、Docker 镜像是否曾构建成功。
- 已剔除的误报倾向：插件自动加载未登记目录需要「已有文件系统写权限」前提，降为 P2 纵深防御；缓存全量失效是**已知代价但只保护了聚合缓存**，见 P1-10 的准确口径。

---

## 1. P0：上线前必须修

### P0-1 环境变量名漂移，使生产安全判定整体失效 【复核】

**证据**
- `backend/core/config.py:48-53`：`SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")`
- `backend/core/config.py:71-74`：`environment: Literal[...] = Field(default="development")`，**无 `validation_alias`**
- `backend/core/config.py:472-489`：`if self.environment == "production":` 才拒绝默认密钥 / 短密钥
- `backend/core/config.py:502`：`is_production` 同样依赖该字段
- 写入方全部用 `APP_ENV`：`backend/core/setup_config.py:393`、`.env.production:17`、`docker-compose.yml:81`
- 第三处漂移：`.github/workflows/ci.yml:44` 写 `ROSETTA_ENV: test`，同样不是 `ENVIRONMENT`

**机理**：pydantic-settings 对字段 `environment` 只认 `ENVIRONMENT`；`APP_ENV` 因 `extra="ignore"` 被静默丢弃。`settings.environment` 恒为 `development`，连带后果：`validate_secret_key` 生产分支不执行、`is_production=False`、docs/TrustedHost 策略回退、登录限流用 development 阈值（`rate_limit.py:753` 30 次/60s，而非生产 5 次/900s）。

**第二层坑（比第一层更隐蔽）**：即便修好别名，`.env.production:37` 的占位符 `CHANGE_THIS_TO_A_SECURE_RANDOM_STRING...` 既不等于 `default_secret`（`:479`），长度又 ≥32（`:486`），**仍然能通过校验**。也就是说「生产校验」即便生效也拦不住公开占位符。

**重构方案（分两步，兼容存量部署）**

第 1 步 —— 立即止血，不依赖环境判定（`backend/core/config.py`）：

```python
_SECRET_KEY_PLACEHOLDERS = (
    "your-secret-key-change-in-production",
    "change-this-secret-key-in-production-please",
)

@model_validator(mode="after")
def validate_secret_key(self) -> "Settings":
    key = self.secret_key.strip()
    if not key or key in _SECRET_KEY_PLACEHOLDERS or "CHANGE_THIS" in key.upper() or "CHANGE-THIS" in key.upper():
        raise ValueError("SECRET_KEY 是占位符，拒绝启动：请用 openssl rand -hex 32 生成")
    if len(key) < 32:
        raise ValueError("SECRET_KEY 长度不足 32 字符，拒绝启动")
    return self
```

> 注意：把「开发也要求强密钥」写死会影响 `tests/conftest.py` 与本地 `dev.ps1`，因此需同步在测试 conftest 里注入一个测试用 32 字符常量（非真实密钥），或给 validator 加 `if self.environment == "test"` 分支。**这是必须一起改的连带项，别只改 config.py。**

第 2 步 —— 兼容存量 `.env`，避免改名让已有部署「突然变成 production」（`backend/core/config.py:71`）：

```python
from pydantic import AliasChoices, Field

environment: Literal["development", "staging", "production"] = Field(
    default="development",
    validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV"),
)
```

同时把 `setup_config.py:393`、`.env.production:17`、`.env.docker`、`docker-compose.yml:81`、`ci.yml:44` 统一改为 `ENVIRONMENT=`（`AliasChoices` 保留旧 `APP_ENV` 只作向后兼容）。`AliasChoices` 与当前 pydantic-settings 版本的适配**需要单测确认**；若不支持，退化为在 `model_validator(mode="before")` 里读 `os.getenv("APP_ENV")` 兜底。

**回归测试（新增 `tests/test_config_env_alias.py`）**：分别用 `ENVIRONMENT=production` / `APP_ENV=production` / 都不设 三种环境构造 `Settings`，断言前两者 `is_production is True`；断言默认密钥与三类占位符均抛 `ValidationError`；断言 `TRUSTED_PROXY_IPS` 与 `cors_origins` 的列表解码仍走 `_decode_env_lists`（AGENTS §6 的既有契约，别被这次改动破坏）。

---

### P0-2 Docker 默认态 = 开箱即接管 【复核】

**证据**：`docker-compose.yml:84-97`（`AUTO_OOBE=1`、`SECRET_KEY=${SECRET_KEY:-change-this-secret-key-in-production-please}`、`ADMIN_PASSWORD=${ADMIN_PASSWORD:-Admin123456}`、`DB_PASSWORD:-rosetta_secret`）、`:33/:57/:109/:131`（PG / Redis / 后端 / 前端端口裸绑）、`.env.docker:5`（写明「不修改也可以直接启动」）、`docker/backend-entrypoint.sh:19`（`AUTO_OOBE` 自动建号）。

**重构方案（`docker-compose.yml`）**

```yaml
services:
  backend:
    environment:
      - ENVIRONMENT=production
      - AUTO_OOBE=0
      - SECRET_KEY=${SECRET_KEY:?运行 openssl rand -hex 32 并写入 .env}
      - ADMIN_PASSWORD=${ADMIN_PASSWORD:?必须显式设置}
      - DATABASE_URL=postgresql+asyncpg://${DB_USER:?}:${DB_PASSWORD:?}@postgres:5432/${DB_NAME:?}
      - TRUSTED_PROXY_IPS=["172.20.0.10"]
    expose: ["8000"]          # 删除 ports
  postgres:
    expose: ["5432"]          # 删除 ports
  redis:
    expose: ["6379"]          # 删除 ports
  frontend:
    ports: ["127.0.0.1:${FRONTEND_PORT:-80}:80"]
    networks:
      rosetta-network:
        ipv4_address: 172.20.0.10
networks:
  rosetta-network:
    ipam: { config: [{ subnet: 172.20.0.0/16 }] }
```

`POSTGRES_PASSWORD: ${DB_PASSWORD:?}` 与 redis `--requirepass ${REDIS_PASSWORD:?}` 同样改必填。

**为什么要给 frontend 固定 IP**：`rate_limit.py:525` 对 `trusted_proxy_ips` 是**精确字符串**匹配，CIDR 无效；Docker 下后端 socket 对端是 frontend 容器 IP，不注入 `TRUSTED_PROXY_IPS` 就永不采信 XFF，全体访客塌缩到同一个限流桶（AGENTS §6 已记录同机部署要配 `["127.0.0.1"]`，Docker 路径漏了）。

**风险 / 回滚**：`:?` 会让未配置 `.env` 的开发机 `docker compose up` 直接失败——这是**期望行为**，需在 `.env.docker` 顶部写明生成命令；本地开发保留一份不提交的 `.env.local`。回滚只需还原 `:-` 默认值，但回滚后等于恢复 P0，不应作为长期方案。

---

## 2. P1：安全（7 项）

### P1-1 OOBE 数据库连接测试端点安装完成后仍匿名可达（SSRF + 口令落日志）【复核】

`backend/api/oobe.py:1589`（POST）、`:1800`（GET）两个 `test_database*` 端点**都没有** `await require_oobe_incomplete()`；`oobe.py:204` 的 `APIRouter` 也无 `dependencies`。对比同文件 `:712/:938/:1010/:1034/:1755/:1846/:1918` 的其它端点都有该闸门。`backend/main.py:590-629` 在 `oobe_done=True` 时对全部 `/api/*` 直接 `call_next`，所以安装前后都匿名可用。`db_host/db_port` 直接进 `setup_database.py:140` 的 `asyncpg.connect`，不经 net_guard。GET 端点自己的文档（`:1582-1583`）承认密码会进 query string 落访问日志。

**改法**：① 两个端点首行加 `await require_oobe_incomplete()`；② **删除 GET 端点**（POST 已覆盖且更安全），保留路由重定向兼容；③ `test_postgresql_connection` 入口用 `ipaddress` 拒绝私网/环回/保留地址，端口限制到 5432/5433；④ 新增 `tests/test_oobe_db_probe_guard.py`：安装完成后 `POST /api/oobe/test-database` 必须 403，`db_host=127.0.0.1` 必须被拒。

### P1-2 SVG 内容检查正则可绕过 → 同源存储型 XSS 【复核】

`backend/api/media.py:274`：`_SVG_UNSAFE_RE = re.compile(rb"<script|\son[a-z]+\s*=|javascript:", re.IGNORECASE)`。事件属性分支要求属性名**前有空白**，而 HTML/SVG 允许 `/` 作分隔符：`<svg/onload=alert(1)>` 以 `<svg` 开头（通过魔数校验），又不匹配三条规则 → 落盘到同源 `/media`（`main.py:941` 挂 StaticFiles）。同文件 `:272-273` 注释自己写明「内含脚本即等价于站点自身的 XSS」。仅需任一登录用户（`upload_avatar` / `upload_cover`）。

**改法（推荐一次性收口）**：从 `ALLOWED_IMAGE_EXTENSIONS`（`:224`）与 `LIBRARY_TYPE_EXTENSIONS["image"]`（`:260`）移除 `svg`。若业务必须保留 SVG，则不要继续加正则——改用 XML 解析做「标签 + 属性」白名单（只允许 `<svg><path><g><circle>…` 与 `d/fill/stroke/viewBox`），并显式拒绝 `xlink:href`、`srcdoc`、`foreignObject`、`data:` URI、实体编码；同时给 `/media` 增加 `Content-Security-Policy: default-src 'none'; sandbox` 与 `X-Content-Type-Options: nosniff` 响应头（Nginx `location ~* \.svg$`），把同源 SVG 隔离成第二道防线。

> 只把正则改成 `(?:\s|/)on[a-z]+\s*=` 是**不够**的：属性编码、`xlink:href`、`animate` 等向量仍在。这里应做白名单而非黑名单。

### P1-3 net_guard 是 check-then-fetch，且完全不限制端口（已记录的遗留债）

`backend/core/net_guard.py:7-9` 注释自认「无法抵御低 TTL 的 DNS rebinding」；`:97-113` 只校验 scheme 与解析 IP，**没有端口白名单**；`:145-146` 先 `assert_public_http_url(current)` 再由 httpx `client.get(current)` **重新解析** DNS 并连接（TOCTOU）。影响四个调用方：`avatar_proxy.py:119`、`bing_image.py:171`、`webhook.py:644`、`extensions.py:984`。重定向逐跳校验（`:143-153`）是做对了的，别动。

**改法**：`assert_public_http_url` 改为返回「已校验 IP 列表」；`validated_get` 用自定义 `httpx.AsyncHTTPTransport`（或 resolver 映射）把连接**固定到该 IP**，保留原 `Host` 头与 TLS SNI；新增 `allow_ports=(80, 443)` 参数，代理类调用一律显式传入。回归用 `tests/test_net_guard.py` 的 monkeypatch resolver 补两条：端口非白名单被拒、校验与连接解析结果不一致时被拒。

### P1-4 头像代理是匿名开放 GET 代理

`backend/api/avatar_proxy.py:174-183`：白名单 `_ALLOWED_HOST_SUFFIXES` 只用于「命中则 307 直跳省带宽」，**非白名单或 `fallback=1` 一律走 `_proxy_and_validate`**（`:119` → `validated_get`）。`src` 是任意 base64 URL 且端点无鉴权，服务端会向任意公网 host:port 发 GET（响应要求 `image/*` 只影响回显，不影响请求已发出）。与 P1-3 叠加可打内网。

**改法**：代理分支也强制要求 host 命中可代理域名白名单，否则直接 307 到 `_FINAL_FALLBACK`；端口固定 80/443；对同一 `src` 加短 TTL 去重，避免被当扫描器放大。

### P1-5 前端 XSS 面三层失守（token 持久化 / 净化配置漂移 / JSON-LD 未编码）

| 层 | 证据 | 问题 |
| --- | --- | --- |
| 凭据 | `frontend/stores/auth.ts:88-89` | access + refresh（长期有效）明文存 localStorage；全仓无 CSP |
| 净化 | `frontend/pages/[slug].vue:265-273`、`pages/page/[slug].vue:101-109` 对照 `lib/sanitize.ts:23,31-39` | 两处内联 `SANITIZE_CONFIG` 漏封 `svg/math/srcdoc/formaction`，还改用 `IN_PLACE`；`lib/sanitize.ts:9,27` 注释却声称「与前台内联配置保持同一组键值」 |
| 输出编码 | `frontend/composables/useSeo.ts:674-728`，注入点 `:626/:1031/:1077` | `jsonLdStringify` 直接 `return JSON.stringify(value, replacer)`，无 `<` 转义；字段含 `</script>` 即提前闭合 script 标签 |

另外 `jsonLdStringify` 的 replacer 用 `Object.prototype.hasOwnProperty.call(val, 'value')`（`:681`）判断 Vue Ref，而 AGENTS §2.3.4 第 5 条明确记录「Vue 3.5 computed 的 `value` 是原型链 getter，`hasOwnProperty` 看不到」——**建议顺带复核 JSON-LD 传 ComputedRef 时是否输出空对象**（本次未做运行时验证，列为待确认）。

**改法（按代价递增）**
1. **立刻做、零架构改动**：删两页内联配置，统一 `import { sanitizeMarkdownHtml } from '~~/lib/sanitize'`（照 `components/admin/MarkdownEditor.vue:13` 既有做法）；`jsonLdStringify` 返回前加：
   ```ts
   return JSON.stringify(value, replacer).replace(/</g, '\\u003c').replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029')
   ```
   并补 `frontend/tests/unit/jsonLdEscaping.spec.ts` 钉住含 `</script>` 的标题。
2. **短期加固**：补安全响应头（nosniff / Referrer-Policy / frame-ancestors / Permissions-Policy）。**不要直接照抄 `script-src 'self' 'unsafe-inline'`** —— 放行内联脚本等于放弃 XSS 防护，且会破坏 Nuxt payload。CSP 走分阶段：先 `Content-Security-Policy-Report-Only` 收集违规，再用 nonce（Nitro `render:html` 钩子给所有 `<script>` 注入 nonce）或引入 `nuxt-security`。
3. **架构级（需你决策，见第 7 节风险）**：refresh token 移入 `httpOnly; Secure; SameSite=Lax` cookie，access token 只留内存；代价是**一旦用 cookie 就必须补 CSRF**（当前后端零 `set_cookie`、认证只靠 `Authorization` 头，AGENTS 现有模型里明确「无 CSRF 面」）。低风险替代：保留 localStorage，但把 access TTL 压到 10–15 分钟、refresh 强制轮换 + 服务端 jti 黑名单，并先上 CSP Report-Only。

### P1-6 插件安装 = 任意 Python 代码执行，权限边界过宽

`backend/api/plugins.py:368` 的 `install_plugin` 只需 `CurrentStaff`；`:400` 上传 zip → 激活时 `extensions.py:619` 用 `SourceFileLoader.exec_module` 执行包内 `plugin.py` 顶层代码。`CurrentStaff` 明显低于 `CurrentSuperUser`（项目有 `rbac.effective_role` 分层），staff 与超管的边界在这里被抹平。前提是拿到 staff 账号，但配合 P0 链条即可直达 RCE。

**改法**：`install_plugin` / `activate_plugin` / `bulk_plugin_operation` / `install_from_market` 统一改 `CurrentSuperUser`（读接口保持 `CurrentStaff` 不动，避免误伤后台列表）；`plugin_loader.py:298-303` 顺带把「DB 无记录也照常 import」改为 `continue`（纵深防御，前提是有文件系统写权限，故列为 P2 级加固，不是独立漏洞）。Zip Slip 防护（`_safe_zip_extract_path`）与 manifest slug 正则已正确，**不要动**。

### P1-7 限流在生产可静默回退单进程内存态，且受信对端直连可绕过

`rate_limit.py:143` 的 `_memory_store`、`config.py:107-109` 的 `redis_enabled` 默认 `False`、`rate_limit.py:154-160` 静默返回 `None` → 多 worker 各算各的、重启清零；`:574-577` 的 `is_internal_request` 判定「对端在 `trusted_proxy_ips` 且无 XFF/X-Real-IP」即 `:709` 直接跳过限流，而 AGENTS §6 推荐把该值配成 `127.0.0.1` → 任何本机直连后端且不带转发头的请求完全不受限流。与 P0-2 的 8000 端口直连叠加。

**改法**：`setup_rate_limit_middleware()` 在 `settings.is_production` 且 Redis 未连通时**拒绝启动**（不要静默降级）；`is_internal_request` 收窄为仅豁免 `/health`、`/api/health` 等明确路径。注意 `P0-1` 修好后 `is_production` 才为真，这两条要一起上线。

---

## 3. P1：性能与正确性（6 项）

### P1-8 空值缓存（防穿透）100% 失效 【复核】

`backend/core/cache_v2.py:409-426`：`get()` 把 `NULL_MARKER` 翻译成 `None`；`:612-614` 与 `:636-638` 的 `get_or_set` / `_fetch_and_store` 都用 `cached is not None` 判命中 → `set_null()`（`:643`）写了等于没写，每次请求都回源 DB。生产调用点 `services/user_service.py:435/:928` 在用户不存在时返回 `None`，因此遍历随机 `user_id` 是 **N 次请求 = N 次回源**，可被稳定用来打 DB。

**改法（最小改动，不改 `get()` 对外的返回契约）**：新增 `get_with_hit(key) -> tuple[bool, Any]`，命中 `NULL_MARKER` 返回 `(True, None)`；`get()` 内部改为调用它保持兼容；`get_or_set` / `_fetch_and_store` / `@cached` 的 `skip_local` 分支（`:735-737`）统一改用 `hit` 判定。补 `tests/test_cache_null_marker.py`：连续两次 `get_or_set` 同一个不存在的 key，断言 `fetch_func` 只被调用 1 次。

### P1-9 「清退全部缓存」直接 `flushdb()`，抹掉非缓存键 【复核】

`backend/api/admin_tools.py:304`（`mode == "all"` → `cache.clear()`）→ `backend/core/cache.py:346-352` 的 `await client.flushdb()`。连带删除 refresh token 黑名单（`core/auth.py:203`）、限流滑动窗口、分布式锁键，以及共享同一 DB 的其它实例键。一次点击 = 已注销 refresh token 可重放 + 全站限流归零 + 进行中的互斥锁消失。

**改法（两阶段，因为当前 key 命名空间并不统一）**：
- 立即：把 `mode="all"` 分支改为按 `_AGGREGATE_PREFIXES` + 已知业务前缀列表逐个 `invalidate_pattern`，**不碰未知键**；或在后台 UI 直接下线「清退全部」选项（改动最小）。
- 随后：随 P1-13 的 `KeyRegistry` 统一 `rosetta:*` 前缀后，`clear()` 改用 `async for k in client.scan_iter(match="rosetta:*", count=500): await client.delete(k)`，并在代码里禁用 `flushdb`。

### P1-10 评论高频写 → 全站列表缓存归零 【复核，口径已校正】

准确链路：`backend/api/comments.py:292/:387/:414/:437/:461` → `invalidate_post_caches_by_ids`（`services/post_cache.py:79-89`）→ `invalidate_post_caches_by_slugs`（`:40-54`）→ `:50` `await invalidate_cache("posts")`，按 `posts*` 前缀删掉全部「语言 × 页 × page_size × 筛选 × 排序」键（Redis 后端走 `core/cache.py:320-331` 的 `scan_iter` 批量 DEL）。

需要说清楚的是：`:111-121` 的注释只把「聚合缓存」刻意从这条路径摘了出去，**列表缓存仍在全删**；`:43-44` 注释也自认这是「全站文章列表集体回源的缓存雪崩」并用 early return 降低触发频率，但没有根治。键基数可达上千，1 条评论 = 全站列表缓存归零，随后首波 `list_posts` 全部回源（每条含 COUNT + 两路聚合 join + 3 组 selectinload）。

**改法**：列表缓存换代际键 `posts:v{gen}:{lang}:{page}:{size}:{filters}`，写侧只 `INCR posts:gen`（O(1)，旧键靠 TTL 自然消亡），读侧把 gen 放进本地 L1 缓存 2–5 秒避免每次多一次 Redis 往返；详情键 `post:{slug}:{lang}` 仍按 slug 精确删。代价是 `gen` 变更瞬间会有一次全量冷启动，但比「每条评论全删」可控得多。

### P1-11 推荐 / 热榜每次回源都做全表聚合 join，分页在 Python 里做 【复核】

`backend/services/recommendation.py:557-571`：`stats_q` 对**全部**公开文章 × likes × comments 做 `outerjoin + GROUP BY`，无 LIMIT；`:657-675` 的 `_hot_scored_ids` 同样拉回内存 `scored.sort()` 后 Python 切片；`tags_q` 又用 `in_(all_ids)` 传全表 id。`RECOMMENDATION_TTL=300s` / `HOT_RANKING_TTL=600s` 到期固定触发一次全库回源。N=1 万篇文章、单页 20 条时，扫描放大约 500×。

**改法（推荐物化列，跨 PG/SQLite 通用且可索引）**：给 `posts` 加 `hot_score REAL DEFAULT 0`，定时任务（复用现有 `cache_warmer` 的后台任务框架）每 10 分钟批量重算，查询直接 `ORDER BY hot_score DESC LIMIT :limit`；`tags_q` 只对页内 20 个 id 查询。备选是把 HN 分数写成 SQL 表达式下推，但 `extract(epoch)` 在 SQLite 需 `julianday` 方言分支，维护成本更高。验收：压测对比回源时 `EXPLAIN ANALYZE` 扫描行数与 P99，目标从 O(N) 降到 O(limit)。

### P1-12 三套缓存实现并存、key 命名空间割裂、失效靠硬编码映射

`core/cache.py`（Redis/Memory 降级，裸键 `posts:…`）、`core/cache_v2.py`（`rosetta:v1:…` + L1/L2 + 击穿锁 + 空值）、`services/cache_service.py`（纯转发）三套并存约 1900 行；`services/post_cache.py:26` 必须硬编码 `_RECOMMENDATION_PATTERNS = ("simv2:*", "hotv2:*", "rosetta:v1:recsv2:*")` 才能清掉推荐缓存，注释里已记录多起「漏清缓存」事故。另外 `core/cache.py` 的 `MemoryCacheBackend` 无容量上限 / LRU，单机长时间运行内存无界。

**改法**：保留 `cache_v2` 为唯一后端；删除 `services/cache_service.py` 转发层；新建 `KeyRegistry` 集中声明「前缀 + 版本 + 失效 pattern」，所有调用方只通过它拿 key；内存后端复用 `LocalCache` 补 `max_size` + LRU。这是**跨多文件的重构，务必放在 P0/P1-8/P1-9 修完并补测试之后**，不要与止血混在同一批。

### P1-13 启动流程固定开销：每次 `create_all` + 全表逐列 ALTER + 重复扫描

`backend/core/database.py:269-322`：每次启动对每张表 `insp.get_columns()`、对每列比对并尝试 ALTER（失败还有第二次 fallback）；20+ 表 × 10+ 列 ≈ 200+ 次元数据查询，且 DDL 在 `run_sync` 线程池里串行执行。`main.py:400` 的 `load_plugins` 与 `core/extensions.py:2053-2054` 的 `bootstrap_extensions` 又各扫一次盘面。生产已由 Alembic 独占 DDL（三个部署入口都跑 `migrations upgrade`）。

**改法**：`_repair_columns` 仅在 `settings.is_development` 或测试环境启用，生产路径直接跳过；把两处盘面扫描合并为一次并复用结果；文件扫描放 `asyncio.to_thread`。收益：冷启动时延随表数增长的部分被消掉。

---

## 4. P1：工程化与交付（4 项）

### P1-14 测试与覆盖率门禁整体失效 【复核】

- `.github/workflows/ci.yml:46`：`uv run pytest -q --no-cov` → `pyproject.toml:148` 的 `fail_under = 45` 完全不执行。
- `pyproject.toml:77`：`--cov-append` 跨多次运行累加脏数据。
- `pyproject.toml:103-139`：`omit` 把 `cache.py` / `cache_v2.py` / `distributed_lock.py` / `concurrency.py` 等核心模块 + 13 个 API 模块全部排除；`exclude_lines` 把 `except Exception:`、`logger.warning`、validator 等大量非平凡分支剔除。
- `.github/workflows/ci.yml:69-79`：frontend job 到 `pnpm lint` 结束，**百余个 `frontend/tests/unit/*.spec.ts` 与 `nuxt build` 从未在 CI 执行**（`vitest.config.ts:26` 的收集配置本身是正常的）。
- `tests/conftest.py:302-325` 把 `check_rate_limit` 全局 patch 成永远放行 → 限流集成路径零覆盖。

**结果**：本报告的 P1-8（空值缓存）、P0-1（配置别名）等缺陷，现有门禁一条都拦不住。

**改法**：
```yaml
# .github/workflows/ci.yml
- name: Run backend tests
  run: uv run pytest -q              # 去掉 --no-cov
- name: Frontend unit tests
  run: pnpm test
- name: Frontend build
  run: pnpm build
```
```toml
# pyproject.toml
addopts = "-v --tb=short --cov=backend --cov-report=term-missing:skip-covered --cov-report=xml --strict-config"  # 去掉 --cov-append
```
移除核心模块的 `omit`、收紧 `exclude_lines`（只留真正不可达分支）；`fail_under` 先保持 45 不调，等覆盖率真实回升后再逐步上调——**一次性把门槛拉到 70 只会让 CI 长期红灯，失去意义**。

### P1-15 三条生产入口吞掉 Alembic 迁移失败并继续服务

`docker/backend-entrypoint.sh:13-15`、`deploy/linux-install.sh:155-156`、`deploy/windows-start.ps1:93-95` 都是「迁移失败但继续启动服务」；配合 compose 的 `restart: unless-stopped` 会持续掩盖失败，schema 未升级时新代码读不存在的列 → 运行时 500。

**改法**：
```bash
# docker/backend-entrypoint.sh
python -m backend.migrations upgrade head || { echo "migration failed" >&2; exit 1; }
```
```powershell
# deploy/windows-start.ps1
if ($LASTEXITCODE -ne 0) { throw "Alembic 迁移失败" }
```
`deploy/linux-install.sh` 同理改为非零退出。**发布流程必须配套「先备份 DB + 可回滚的 downgrade 脚本」**：当前 `backend/migrations/versions/` 有 27 个修订、单一 head（无冲突），但部分 `downgrade` 是 `pass`（如 `1e26faaeeb6b…py:28`），数据类迁移缺回滚，这是上线风险，需单独补齐。

### P1-16 `.dockerignore` 排除 `static`，而 Dockerfile 要 `COPY static/`

`.dockerignore:65` 有 `static`（无 `!` 例外，已复核全文件），`Dockerfile:63` 有 `COPY static/ ./static/`，且 `:61-62` 注释明确说这是头像兜底图必需资源。结果：`docker build --target backend` 在此处报 `COPY failed: no source files were specified`，**生产后端镜像产不出来**（静态推断，本轮未实际构建）。

**改法**：把 `.dockerignore:65` 改为
```
static/*
!static/rosetta-256.png
```
验证命令见第 8 节。

### P1-17 前端容器健康检查假阳性 + Node 非 PID 1

`Dockerfile:115-123`：`node .output/server/index.mjs &` 后 `nginx -g "daemon off;"`，healthcheck 打的是 `docker/nginx.conf:65-70` 的静态 `return 200 "healthy"` → Nitro 挂掉容器仍 `healthy`，compose 不重启；Node 是 sh 后台子进程，容器停止无 SIGTERM 转发。另外 `docker/nginx.conf` 的 `/media/` location 内单独写了 `add_header Cache-Control`，按 Nginx `add_header` 不继承规则，会让 server 层的安全头在该 location **全部失效**。

**改法**：`RUN apk add --no-cache curl tini` + `ENTRYPOINT ["/sbin/tini", "--"]`；healthcheck 改打 Nitro 真实路径（`curl -fsS http://127.0.0.1:3000/`），或把 `/health` 从静态 200 改成 `proxy_pass http://nitro/health;`；start 脚本补 `trap 'kill $NODE 2>/dev/null || true' TERM INT`；安全头统一放 `snippets/rosetta-security.conf`，在**每个 location 内 include**。

---

## 5. P2：可维护性（分批偿还）

| # | 证据 | 问题 | 重构动作 |
| --- | --- | --- | --- |
| 1 | `backend/api/import_export.py:1227-1978`（`backup_restore` 752 行）、`api/core.py:1063-1385` 与 `:1394-1727`（两份 300+ 行站点配置读取）、`main.py:477-974`（`create_application` 498 行）、`api/blog.py` 4590 行 | 超大函数 / 同一口径实现两遍，`core.py:1097-1100` 已记录「两处口径不一致」事故 | 抽 `SiteConfigLoader` 一次查询返回归一化 dict，两端点只做投影；`create_application` 拆 `_register_middleware / _register_exception_handlers / _register_routers`；`blog.py` 按 posts/taxonomy/archive/sitemap 拆 4 模块 |
| 2 | `frontend/composables/useAdminManage.ts` 2857 行 / 139 导出、`pages/oobe.vue` 3321、`pages/posts/[slug].vue` 2659、`pages/admin/index.vue` 2085 | 单文件混装多域，chunk 无法细分，测试只能靠正则断言源码文本 | 按域拆 `useAdminPosts/Users/Comments/Settings`；OOBE 按 wizard step 拆 `components/oobe/*` |
| 3 | `frontend/composables/useApi.ts:376,387` 对照有守卫的 `:330/:445` | 401 终态在 SSR 端调 `navigateTo` + 客户端 toast，违反文件头「SSR 分支禁止 navigateTo」与 AGENTS §2.4 | 把跳转与 toast 包进 `if (import.meta.client){}`，服务端只 `clearTokens()` 后 rethrow |
| 4 | `frontend/pages/[slug].vue:205`、`pages/posts/[slug].vue:1581`、`composables/useOOBE.ts:285`、`useBingWallpaper.ts:206`、`pages/oobe.vue:2023` | 5+ 处裸 `$fetch` 绕过统一出口，缺 401 刷新 / 超时 / i18n 头；**直接违反 AGENTS §4.2 铁律** | 统一改 `apiFetch` / `useAPI`；把重复的两份「擦泛型断类型推断」样板抽成 `useApi.ts` 导出的 `createApiFetch()` |
| 5 | `frontend/nuxt.config.ts:901-924`、`i18n.config.ts:3-4`、`i18n/index.ts` | 四语 JSON 合计 231,240 字节，i18n v10 `lazy` 默认 false 未开启；语言码/fallback 双入口维护 | i18n 段加 `lazy: true`；删 `i18n.config.ts`，只留 `vueI18n: './index.ts'` |
| 6 | `frontend/lib/top-level-routes.ts:12-38`、`nuxt.config.ts:50-66/263-432`、`server/middleware/06-page-alias.ts:21,36`、后端 `_TOP_LEVEL_ROUTE_SLUGS` | 同一概念 4 份手写清单，跨前后端；靠 `pageAliasTopLevelRoutes.spec.ts` 事后文本断言兜底 | 收敛为单一常量（已有 `I18N_URL_PREFIXES` 先例），routeRules 与 `NON_LOCALIZED_PREFIXES` 由它生成；后端从同一份 JSON 或 `/api/config` 读取 |
| 7 | `frontend/server/middleware/00-api-proxy.ts:175-177` | 502 把内网 `backendBase` 与上游 `ECONNREFUSED` 原文回给浏览器 | 内网信息只写 `console.error`，响应改固定文案「后端服务暂不可用」 |
| 8 | `frontend/pages/posts/[slug].vue:2199-2225` | 巨型 `computed` 内跑 marked + highlight.js + DOMPurify，SSR 与客户端各一遍 | 正文渲染移出 computed，用 `useAsyncData` 按 `slug+lang+content hash` 缓存一次 |
| 9 | `backend/api/blog.py:727-738`、`:823-824/:860-866`；`api/gallery.py:546-557` | COUNT 复用带两路 outerjoin 的 query 作子查询（聚合跑两遍）；批量删照片循环内串行 await DB 与 hook | COUNT 改用纯过滤 `select(func.count()).select_from(Post).where(*filters)`；相册计数改单条 `UPDATE ... WHERE album_id IN (...)`，hook 用 `asyncio.gather` |
| 10 | `backend/core/shortcodes.py:229`（`"*"` 允许 `style`）、`services/content_renderer.py:81`、`api/blog.py:301` | 白名单允许任意 CSS（可做数据外带）；正文原生 HTML 后端不净化，RSS `<content:encoded>` 原样输出；与 `core/xss_filter.py:119` 口径不一致 | 去掉 `style` 或做 CSS 属性/值白名单；`render_content()` 在 `do_shortcode` 之后对整段结果调用 `sanitize_html()` |

**另有一组部署一致性问题（合并列为 P2）**：CI Python 3.11 / Docker 3.12 / ruff py310 三套版本不对齐；`uv sync --extra dev` 未加 `--frozen`；pytest/ruff/coverage 写在 `[project.dependencies]` 会把测试工具装进生产镜像；`uv:latest` / `pnpm@latest` 与 `packageManager: pnpm@11.20.0` 可能冲突；容器默认 root；`rosetta.json` 明文 `secret_key`（**已核实未被 git 跟踪，但落在工作区/备份里仍是暴露面，建议轮换并从该文件移除**）；两份 Nginx 只有 80 端口生效、443 块整段注释、无 `limit_req`、XFF 用 `$proxy_add_x_forwarded_for` 追加（客户端可伪造多跳，应改为 `$remote_addr` 覆盖）、`client_max_body_size` 两份配置 50m/20m 不一致。

---

## 6. 值得保留的设计（重构时不要动）

1. **分布式锁**：`core/distributed_lock.py:152` `SET NX EX` + UUID token，释放/续期用 Lua 校验持有者，按 Task 记账可重入，`MAX_TRACKED_LOCKS=256` 防键无界。
2. **阻塞调用 offload**：`core/auth.py:158-172` 把 argon2 KDF 放 `asyncio.to_thread`；`api/media.py:2070-2083` 把 PIL 整体放线程池；推荐算法 / OOBE subprocess 同样处理。
3. **列表查询反 N+1**：`api/blog.py:727-765` 用两条 `GROUP BY` 子查询批量取计数 + 3 组 `selectinload` + `defer` 大字段；缓存键把 language/page/sort/author 等全部纳入（`:420-443`）。
4. **SSR 单源 origin**：`server/utils/ssr.ts:66-84` 只信配置的 `siteUrl`，`rss.xml.get.ts:63-69` 明确拒绝 `x-forwarded-host`，挡住 Host 头投毒与缓存键膨胀。
5. **Bing BFF 键控防放大**：`server/api/bing-wallpaper.get.ts:36-44` 的 `MKT_PATTERN` 白名单 + `idx` 钳到 0–7 + `getKey`/handler 共用 `parseParams`。
6. **认证细节**：JWT 单算法固定、refresh 的 `type` 校验 / `token_version` / jti 黑名单 `SET NX` 原子消费 / rotate 四件套；`stores/auth.ts:203-236` 的 `_refreshInFlight` 并发互斥。
7. **安全默认值**：`debug` 默认 False、`.env*` 被 `.gitignore` 排除、`git ls-files` 未发现密钥文件入库、Zip Slip / 魔数 / 路径校验均已到位。
8. **测试隔离**：`tests/conftest.py` 用内存 SQLite + `StaticPool` + `ASGITransport`，全局关 Redis，无真实网络依赖。

---

## 7. 重构路线图（按依赖排序，不要跳批）

| 批次 | 内容 | 交付判据 | 主要风险 / 回滚 |
| --- | --- | --- | --- |
| **B0 止血（当天）** | P0-1 两步 + P0-2 compose + P1-1 / P1-2 / P1-9（下线 flush all）+ P1-15 迁移失败退出 + P1-16 `.dockerignore` | 新增 4 组回归测试全绿；`docker compose config` 无弱默认值；`docker build --target backend` 成功 | 强密钥校验会打断本地 dev 与测试，必须同步改 conftest；`:?` 会让未配 `.env` 的开发机起不来（期望行为，写进 `.env.docker` 说明） |
| **B1 安全收口（1 迭代）** | P1-3 固定 IP + 端口白名单、P1-4 代理域名白名单、P1-5 净化统一 + JSON-LD 转义 + 安全头 + CSP Report-Only、P1-6 超管闸门、P1-7 限流禁降级 / 收窄豁免、P1-14 CI 门禁 | CI 跑 `pytest`（带 cov）+ `pnpm test` + `pnpm build`；`nuxt build` 产物 SSR 首屏正常 | `fixed-IP transport` 改动影响全部外连调用方，需在 staging 验证头像/Bing/webhook 三条路径；CSP 只上 Report-Only，**不要一步切到强制** |
| **B2 性能与正确性（1 迭代）** | P1-8 空值缓存、P1-10 世代键、P1-11 物化热度列 + Alembic 迁移、P1-13 启动瘦身、P2-9 查询优化 | 压测对比：随机不存在 ID 回源次数 1/N；评论写不再触发 `scan_iter`；推荐回源扫描行数 O(limit)；冷启动时延下降 | 世代键与物化列都涉及缓存/DB 语义变化，需灰度 + 可回滚迁移；热度列迁移需 `downgrade` 真实现（见 P1-15） |
| **B3 可维护性（随功能迭代）** | P1-12 `KeyRegistry` 统一缓存、P2 全部 | 三套缓存收敛为一套；巨型文件拆分后现有 `tests/unit/*.spec.ts` 的文本断言需同步更新 | **跨文件大重构，必须与 B0/B1 分开**；文本断言型测试脆弱，拆文件前先改成行为断言 |

**需要你决策的一项**：P1-5 第 3 步（refresh token → httpOnly cookie）会改变认证模型并强制引入 CSRF，影响前后端、BFF 代理、SSR 与全部登录态测试。建议先做第 1/2 步（净化统一 + 转义 + 安全头 + CSP Report-Only），观察 Report-Only 数据后再决定是否改认证模型；若不做，至少把 access TTL 压短并强制 refresh 轮换。

---

## 8. 验证命令（可直接复制；本轮**均未执行**）

```bash
# 后端门禁（项目根）
uv run ruff check backend tests
uv run ruff format --check backend tests
uv run pytest -q                        # 不带 --no-cov，验证 fail_under 真实生效
uv run pytest tests/test_config_env_alias.py tests/test_cache_null_marker.py -q

# 前端（frontend/ 目录）
pnpm install --frozen-lockfile
pnpm typecheck
pnpm lint
pnpm test
pnpm build

# 部署形态（项目根）
docker compose config                    # 确认无 :- 弱默认值、端口不再裸绑
docker build --target backend -t rosetta-backend .
docker run --rm rosetta-backend test -f /app/static/rosetta-256.png

# 配置别名回归（应打印 production）
ENVIRONMENT=production uv run python -c "from backend.core.config import settings; print(settings.environment, settings.is_production)"
APP_ENV=production   uv run python -c "from backend.core.config import settings; print(settings.environment, settings.is_production)"
```

**预期输出要点**：两条别名命令都打印 `production True`；默认密钥启动抛 `ValidationError`；`pytest` 输出含 coverage 且不低于 45；`pnpm test` 收集到百余个 spec；`docker compose config` 中不含任何 `change-this` / `Admin123456` 字符串。

---

## 9. 风险、限制与未核实项（显式列出）

1. **本轮未运行任何测试 / 构建 / HTTP 请求**，所有性能数字（如「500× 放大」「231KB」「752 行」）来自静态代码与文件统计，需在 staging 实测校正。
2. Nginx 结论仅针对仓库内 `deploy/nginx-site.conf` 与 `docker/nginx.conf`；**线上可能由外部 LB 终止 TLS**，不能据此判定线上无 HTTPS。
3. 未读取真实 `.env` / `.env.production` 部署值；不排除实际部署已手工换成强密钥。P0-1 的结论是「默认模板与 OOBE 生成路径不可靠」，不是「线上一定已被攻破」。
4. `AliasChoices` 与当前 pydantic-settings 版本的适配、`fixed-IP httpx transport` 的 TLS SNI 行为、`lazy: true` 与现有 i18n 双入口的兼容，均需单测 / 构建确认，**本轮未验证**。
5. `docker build` 失败（P1-16）是静态配置冲突推断，未实际执行构建；若构建上下文中另有 `static` 来源则结论需修正。
6. Alembic 部分 `downgrade` 为 `pass`，上线前必须补可回滚脚本；本次未在真实 PostgreSQL 上验证任何迁移。
7. `jsonLdStringify` 处理 `ComputedRef` 是否输出异常（AGENTS §2.3.4 第 5 条同源问题）列为**待确认**，未做运行时验证。
8. 报告涉及的所有修复**均未实施**；若需要我按 B0 批次落地代码与测试，请明确指定范围（涉及认证模型改动的部分会先与你确认）。

---

## 10. 证据索引（已逐行复核的关键位置）

```
配置链   backend/core/config.py:48-53,71-74,472-489,502 · backend/core/setup_config.py:393
         .env.production:17,37 · docker-compose.yml:81,84-97 · .github/workflows/ci.yml:44
部署     docker-compose.yml:33,57,84-97,108-109,130-131 · .env.docker:5
         docker/backend-entrypoint.sh:13-15,19 · deploy/linux-install.sh:155-156 · deploy/windows-start.ps1:93-95
         .dockerignore:65 · Dockerfile:61-63,115-123 · docker/nginx.conf:65-70
安全     backend/api/oobe.py:204,1589,1800,1755,1846,1918 · backend/main.py:590-629,941
         backend/api/media.py:224,260,274 · backend/core/net_guard.py:7-9,97-113,143-153
         backend/api/avatar_proxy.py:119,174-183 · backend/api/plugins.py:368,400
         backend/core/plugin_loader.py:298-303 · backend/core/extensions.py:619
         backend/core/rate_limit.py:143,154-160,525,574-577,709 · backend/core/shortcodes.py:229
前端     frontend/stores/auth.ts:88-89,203-236 · frontend/lib/sanitize.ts:23,31-39
         frontend/pages/[slug].vue:265-273 · frontend/pages/page/[slug].vue:101-109
         frontend/composables/useSeo.ts:626,674-728,1031,1077 · frontend/composables/useApi.ts:330,376,387,445
         frontend/server/middleware/00-api-proxy.ts:175-177 · frontend/nuxt.config.ts:901-924
性能     backend/core/cache_v2.py:409-426,612-647,735-737 · backend/core/cache.py:346-352
         backend/api/admin_tools.py:296-305 · backend/services/post_cache.py:26,40-54,79-89,111-121
         backend/services/recommendation.py:557-571,657-675 · backend/core/database.py:269-322
门禁     pyproject.toml:77,103-139,148 · .github/workflows/ci.yml:41-46,69-79
         tests/conftest.py:61-70,302-325 · frontend/vitest.config.ts:26
规范     AGENTS.md:205-219（Ref 解包 / SSR 网格）、524-552（§4 BaseURL 单源）、613-636（§6 环境变量）、777-822（§9 验证清单）
```
