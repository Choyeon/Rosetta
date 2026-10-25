# Rosetta SEO 优化方案（2026-10-25）

> 方法：`website-seo` 五阶段框架（On-page → Technical → Schema → 内链 → 持续监测）+ `blog-schema` @graph 口径 + `SEO-&-GEO-Playbook`（AI 引用/IndexNow）。
> 所有问题均以 **代码 file:line** 或 **生产机 curl 实测** 为证据；未实测的不写成结论。
> 证据采集基线：HEAD `4d7f14f7`，生产 `https://choyeon.cc`（2026-10-25）。

## 0'. 实施状态台账（2026-10-25 批次 #73 起）

| 项 | 状态 | 落点 |
| --- | --- | --- |
| P0-1 404 禁缓存 | 已实现 | `server/utils/ssrHtmlCacheControl.ts`（`errorHtmlCacheControl`）+ `server/plugins/ssr-html-revalidate.nitro.ts`（两道钩子读状态码） |
| P0-2 分页锚点 | 已实现 | `pages/posts/index.vue`（`pageHref` + `<a>`，当前页 `aria-current` span） |
| P0-3 hero LCP + img 宽高 | 已实现 | 各公开页/组件 `<img>` 显式宽高、hero 缩略图去 `loading=lazy`；守卫 `tests/unit/heroLcpAttributes.spec.ts` |
| P1-1 `?page` 越界 301 | 已实现 | `pages/posts/index.vue`（`app:rendered` 闸门 + `no-store`） |
| P1-2 `<html lang>` BCP-47 | 已实现 | `HREFLANG_MAP` 是 BCP-47 单源，三处写点全部走它：`composables/useSeo.ts`（SSR 页覆盖）、`app.vue`（全局 `htmlAttrs.lang`，此前直接吐 `locale.value` = `zh_Hant`）、`nuxt.config.ts`（`app.head.htmlAttrs.lang` 默认值）；守卫 `tests/unit/seoLocaleUrl.spec.ts` |
| P1-3 og:image 去外链 | 已实现 | `lib/post-cover.ts` 回落改站内 `/placeholder-covers/1..6.svg`；`public/og-default.png` + `seo.default_og_image` 设置键 |
| P1-4 JSON-LD @graph | 已实现 | `composables/useSeo.ts::buildArticleJsonLdGraph`（BlogPosting + Person/Organization/ImageObject/BreadcrumbList，`@id` 互指；面包屑首项走 `nav.home`）；守卫 `tests/unit/articleJsonLdGraph.spec.ts` |
| P1-5 `/seo/schema` URL | 已实现 | `backend/api/seo.py`（`/posts/{slug}`、`/authors/{username}`）；守卫 `tests/test_api_seo.py` |
| P1-6 canonical 单源 | 复测更正 | 页面侧本无重复；只加守卫 spec |
| P2-1 sitemap lastmod | 已实现 | `backend/api/blog.py`（子表索引 `<lastmod>` 取该表最大更新日期，空表省略节点） |
| P2-2 RSS lastBuildDate | 已实现 | `backend/api/blog.py`（取本次构建时刻，恒 >= 任何条目 pubDate） |
| P2-3 llms.txt + security.txt | 已实现（humans.txt / FAQPage 复测后刻意不做） | `server/routes/llms.txt.get.ts` + `server/routes/.well-known/security.txt.get.ts`（nitropack `scanDir` 的 globby 带 `dot:true`，点目录会被收录）；守卫 `tests/unit/geoDeliveryRoutes.spec.ts` |
| P2-4 IndexNow | 已实现 | `backend/services/indexnow.py`（`post.published` / `post.updated` 钩子，四语 URL 一次推送）；守卫 `tests/test_indexnow.py` |
| P2-5 移动端 / CWV | 结构性动作已实现，lab 读数受阻 | 宽高与 `fetchpriority` 已实测（首页 53/53 图带宽高、CLS 累积 0）；PSI API 从生产机返回 403、面板 WebView `visibility=hidden` 无 paint 记录，LCP/INP 毫秒数**未采集**，详见 §P2-5 |

***

***

## 0. 现状盘点（已经做对的）

| 项 | 状态 | 证据 |
| --- | --- | --- |
| canonical/hreflang 单源 | ✅ 全部走 `applyLocalePrefix`，无 `localePath()` 残留 | [frontend/composables/useSeo.ts:356-369](file:///D:/WebProjects/Rosetta/frontend/composables/useSeo.ts#L356-L369) |
| 四语 hreflang 集群 + x-default | ✅ 生产文章页 head 实测输出 `zh-CN/en/ja/zh-Hant/x-default` 互指 | curl 文章页 `<link rel=alternate>` |
| 301 归一 | ✅ http→https、www→裸域、尾斜杠→裸路径，直连 200 无跳转链 | curl `-I` 三组探针 |
| SSR 内容页 | ✅ 首页/文章/分类均有真实 HTML；首页 gzip 56.9 KB、TTFB ~0.11 s | curl `--write-out` |
| robots.txt 口径 | ✅ 只挡 `/api/` `/admin/`；noindex 页靠 meta 而非 Disallow | [frontend/composables/useSeo.ts:29](file:///D:/WebProjects/Rosetta/frontend/composables/useSeo.ts#L29)（`NOINDEX_ROBOTS = 'noindex, follow'` 全仓单源） |
| SSR 404 闸门 | ✅ 不存在的 `/posts/{slug}` 回真 404（error.vue + 状态码），且标题/canonical 同口径 noindex | [frontend/composables/useContentStatus.ts](file:///D:/WebProjects/Rosetta/frontend/composables/useContentStatus.ts) + curl 探针 |
| Sitemap 多语言 | ✅ 每个内容节点输出 4 条 `<url>` × 5 条 `<xhtml:link>` | [backend/api/blog.py:3527-3776](file:///D:/WebProjects/Rosetta/backend/api/blog.py#L3527-L3776) |
| 安全头 + HSTS | ✅ 线上 `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`（但见 §5 限制 2） | curl 首页响应头 |
| SWR 缓存头规范 | ✅ `public, max-age=0, s-maxage=<T>, stale-while-revalidate=86400` 完整形态 | [frontend/server/plugins/ssr-html-revalidate.nitro.ts](file:///D:/WebProjects/Rosetta/frontend/server/plugins/ssr-html-revalidate.nitro.ts) |

***

## 1. P0 — 直接影响索引/收录，本周内修

### P0-1 404 响应被共享缓存（swr 600 固化死链）

**现象**：curl `/posts/nope-404-probe-zz` → `HTTP 404`，但响应头带
`cache-control: public, max-age=0, s-maxage=600, stale-while-revalidate=86400`。

**影响**：404 与其 noindex 信号被 CDN/共享缓存固化 600 s + 软过期 24 h。文章改名/重发布的自愈窗口内，爬虫拿到的是缓存旧 404；同时 `stale-while-revalidate=86400` 意味着一个拼错的 URL 被留站爬虫引用后，会在一天内持续返回 404 壳。反过来更危险的是同一条缓存键把"曾经 404"和"曾经 200"混在同一 path 下，SEO 信号抖动。

**改法**：Nitro 缓存处理器对非 2xx 不应写 swr 头。在 `ssr-html-revalidate` 的 `beforeResponse`（或 routeRules 层）加判据：`status >= 400` 时把 `Cache-Control` 改写成 `no-store` 原样透出，不进 swr 归档。

**验证**：
```bash
ssh root@207.57.127.6 "curl -sk -o /dev/null -D- https://choyeon.cc/posts/nope-$(date +%s)-zz | grep -i cache-control"
# 期望：cache-control: no-store（或至少不含 s-maxage / stale-while-revalidate）
```

**回归测试**：`frontend/tests/unit/ssrHtmlCacheControl.spec.ts` 增加"404 状态不补 public/max-age、改为 no-store"用例。

### P0-2 分页对爬虫不可达（`/posts` 翻页只有 `<button>`）

**现象**：[frontend/pages/posts/index.vue:211-239](file:///D:/WebProjects/Rosetta/frontend/pages/posts/index.vue#L211-L239) 的分页是 `Button + @click="handlePageChange(...)"`，无 `<a href>`。生产 curl `/posts` 的 SSR HTML 中 `page=\d+` 锚点数 = **0**。

**影响**：第 2 页起的所有文章没有任何入链，只能靠 sitemap 发现；权重传递断裂、新文章收录延迟，等于主动放弃列表页的 crawl depth 扩展。这是全站公开列表的通则问题（分类/标签/归档同构）。

**改法**：分页按钮改为（或包一层）真 `<a :href="localeHref(`/posts?page=${page}`)")`，保留 click 拦截做 SPA 行为。注意 canonical 查询白名单已含 `page`（[useSeo.ts:257-269](file:///D:/WebProjects/Rosetta/frontend/composables/useSeo.ts#L257-L269)），无需再动 SEO 侧。

**验证**：
```bash
curl -sk https://choyeon.cc/posts | grep -o 'href="[^"]*page=[0-9]*"' | head
# 期望：出现 page=2 等锚点
```

**回归测试**：`frontend/tests/unit/postsPaginationLinks.spec.ts`（新建）：断言分页 DOM 为 `<a>` 且 href 带前缀语言形态（`/en/posts?page=2`）。

### P0-3 首页 hero 图：外链 + lazy + 无尺寸（LCP 三重打击）

**现象**：[frontend/pages/index.vue:249-250](file:///D:/WebProjects/Rosetta/frontend/pages/index.vue#L249-L250) hero `<img loading="lazy">`，源为 picsum.photos 外链；首页 58 个 `<img>` 仅 27 个带 `width/height`。

**影响**：
1. hero 是首页 LCP 候选，`loading="lazy"` 让浏览器先布局再请求，LCP 直接推后；
2. 跨域冷连接（picsum TLS 握手）叠加在上述延迟之后；
3. 无 `width/height` → 图片落位时整页位移 → CLS 超 0.1。

**改法**：
- hero 图改 `fetchpriority="high"`、去 `loading="lazy"`，源换成本地 `/themes/**` 或上传媒体（走 nginx 强缓存 immutable）；
- 所有公开页 `<img>` 补齐 `width/height`（文章封面走后端 caption 字段透传尺寸）；
- 中期引入 `@nuxt/image` 做 WebP/AVIF + 响应式 `srcset`（当前 [nuxt.config.ts](file:///D:/WebProjects/Rosetta/frontend/nuxt.config.ts) 未安装）。

**验证**：
```bash
curl -sk https://choyeon.cc/ | grep -o '<img[^>]*>' | awk '/width=/{w++}END{print w" / "NR}'
# 期望：width 覆盖数 = img 总数；hero img 无 loading="lazy"
```
LCP/CLS 数值验收用 PageSpeed Insights（https://pagespeed.web.dev/analysis?url=https://choyeon.cc/），目标 LCP < 2.5 s、CLS < 0.1。

**回归测试**：`frontend/tests/unit/heroMobileLayout.spec.ts` 同族新增 `heroLcpAttributes.spec.ts`：断言 hero `<img>` 不含 `loading="lazy"`、含 `fetchpriority` 与显式宽高。

***

## 2. P1 — 信号质量与规范化，两周内修

### P1-1 `?page=9999` 软 404 + canonical 污染

**现象**：curl `/posts?page=9999` → HTTP **200**，canonical 自指 `?page=9999`；空列表页与正常页同状态码。

**影响**：Google 判定为 soft 404（低质页面信号），且每个越界页都产生一条自指 canonical，等于无限参数化页面被承认。

**改法**：列表数据回来后判 `page > totalPages`：沿用 §2.3.2 闸门口径，在 `app:rendered` 阶段把状态码改为 **301 → `/posts`（去掉越界参数）** 或 404（与内容缺失同族），noindex 同步。推荐 301：自愈且不产生索引条目。

**验证**：`curl -sk -o /dev/null -w '%{http_code} %{redirect_url}' 'https://choyeon.cc/posts?page=9999'` → `301 .../posts`。

**回归测试**：`frontend/tests/unit/contentNotFoundStatus.spec.ts` 扩展分页越界形态。

### P1-2 `<html lang="zh_Hant">` 非法 BCP-47

**现象**：curl `/zh_Hant` 页面 head：`<html lang="zh_Hant">`（underscore + 非子标签形态）；en/ja 正常。

**影响**：`lang` 属性必须是 BCP-47（`zh-Hant`）。下划线形态被部分解析器降级处理，语言识别信号减弱；而 hreflang 侧输出已是正确的 `zh-Hant`——同一页两套语言代码口径不一致。

**改法**：[useSeo.ts:462](file:///D:/WebProjects/Rosetta/frontend/composables/useSeo.ts#L462) `htmlAttrs.lang` 处加一张映射 `zh→zh-CN / zh_Hant→zh-Hant / en→en / ja→ja`（复用 `HREFLANG_MAP` 的值，不新建清单）。实现时补了两处同样直接吐 `locale.code` 的写点（`app.vue` 全局 `htmlAttrs.lang`、`nuxt.config.ts` 的 `app.head.htmlAttrs.lang` 默认值）——只改 `useSeo` 挡不住没调用它的口（404 错误页、`/oobe`、SPA 壳）。

**验证**（复测更正）：`<html>` 上除了 `lang` 还挂着 `data-default-lang="zh-CN"`，用 `grep -o '<html[^>]*lang="[^"]*"'` 会被贪婪匹配吃到后面那个属性，`/en` 读出 `zh-CN`（本轮 6 条假 FAIL 的来源）。正确探针是先切标签再只认"前面是空白"的属性：

```bash
curl -s https://choyeon.cc/en | tr '\n' ' ' | grep -o '<html[^>]*>' | head -1 \
  | grep -oE '(^|[[:space:]])lang="[^"]*"' | head -1
```

**线上覆盖口径**：`/oobe` 在安装完成后由 `middleware/oobe.global.ts` 回 302 → `/`（且 OOBE 路径按 `composables/useLocaleLink.ts` 的约定不参与语言前缀），所以它在生产机上取不到 HTML，不是 lang 写点的靶面；真实靶面是 **404 错误页**（`app.vue` 那条写点），已实测 `/no-such-page → zh-CN`、`/en/no-such-page → en`、`/ja/no-such-page → ja`。

**回归测试**：`frontend/tests/unit/seoLocaleUrl.spec.ts`（`HREFLANG_MAP` 每个值必须匹配 `^[a-z]{2,3}(-[A-Z]{2}|-[A-Z][a-z]{3})*$`，即 `zh-Hant`/`zh-Hant-TW` 形态合法）。

### P1-3 og:image / 封面图为 picsum 占位
**真源定位（实现阶段更正）**：picsum 回退不在后端序列化，而在前端封面单源 [frontend/lib/post-cover.ts:13](file:///D:/WebProjects/Rosetta/frontend/lib/post-cover.ts#L13) 的 `defaultPostCover()`——`postCoverUrl()` 被 PostCard/详情页/首页 hero 幻灯片与 og:image 取值共用，一处回落全站中招。

**现象**：生产文章页 `og:image`、`twitter:image`、JSON-LD `BlogPosting.image` 均指向 `picsum.photos` 外链；站内 `media/` 有真实上传能力。

**影响**：社交分享卡片依赖外部服务（限流/被墙即无图）；picsum 是随机图，与文章标题/内容无关，图片搜索零收益；AI 抓取器按 caption 关联图文也拿不到任何信号。

**改法**：发布流程要求封面图（无封面时后端 `_og_image` 回退品牌 OG 图 `/og-default.png` 而非 picsum）；`ImageObject` 补 `width/height/caption`（caption 对齐 alt，见 blog-schema 技能 Step 7.5）。

**验证**：`curl -sk <新发文章> | grep -E 'og:image|twitter:image'` → 域名 ∈ `choyeon.cc`。

**回归测试**：`tests/test_api_seo.py` 断言文章序列化时 `og_image` 缺省值不是外链。

### P1-4 JSON-LD 单块 BlogPosting，无 @graph 实体互链

**现象**：文章页 head 仅 1 个 `<script type="application/ld+json">`（BlogPosting），`author` 只有 `{name}`；无 Person、Organization、BreadcrumbList、ImageObject；[useArticleJsonLd](file:///D:/WebProjects/Rosetta/frontend/composables/useSeo.ts#L633-L745)、[useBreadcrumbJsonLd](file:///D:/WebProjects/Rosetta/frontend/composables/useSeo.ts#L751-L791) 已存在但未在该页接全。

**影响**：blog-schema 技能口径——≥3 种 schema 类型 AI 引用率约 +13%；当前 1 种。作者无 Person 实体 → E-E-A-T 的 Author 信号缺失；无 Breadcrumb → 面包屑富结果不可能。

**改法**（@graph 模式，单 script，稳定 @id）：
```json
{"@context":"https://schema.org","@graph":[
  {"@type":"BlogPosting","@id":"{site}/posts/{slug}#article",
   "author":{"@id":"{site}/author/{id}#person"},
   "publisher":{"@id":"{site}#organization"},
   "image":{"@id":"{site}/posts/{slug}#primaryimage"}},
  {"@type":"Person","@id":"...#person","name":"...","url":"...","jobTitle":"..."},
  {"@type":"Organization","@id":"{site}#organization","name":"...","logo":{...600x60 矩形...}},
  {"@type":"BreadcrumbList","@id":"...#breadcrumb","itemListElement":[Home→分类→标题]},
  {"@type":"ImageObject","@id":"...#primaryimage","url":"...","width":1200,"height":630,"caption":"..."}
]}
```
校验规则照抄技能 Step 8：@id 全部解析、dateModified≥datePublished、headline≤110、URL 全绝对、breadcrumb 位置连续。

**验证**：把 head 的 JSON-LD 贴入 https://search.google.com/test/rich-results 或 `curl ... | python -m json.tool` 比对 @graph 长度 ≥5。

**回归测试**：`frontend/tests/unit/articleJsonLdGraph.spec.ts`（新建）。

### P1-5 `backend/api/seo.py` 的 `/seo/schema/{type}/{id}` 用旧 URL 形态且无前端消费点

**现象**：[backend/api/seo.py:654-778](file:///D:/WebProjects/Rosetta/backend/api/seo.py#L654-L778) 产出 `/post/{slug}`（单数）、`/users/{id}`；前端真实路由是 `/posts/{slug}`，且该接口未接进任何 SSR 页面（双重孤儿：URL 错 + 无消费）。

**影响**：若未来把它接进 JSON-LD，schema 里的 URL 与 canonical/hreflang 直接矛盾；现在是死代码但带着错误口径留在真源候选位。

**改法**：要么删接口，要么把 URL 生成改为 `applyLocalePrefix` 同口径并补一个消费点（如 `/api/schema/{type}/{id}` 给第三方引用）。按 ponytail 选最小：先修正 URL + 加一条"该接口输出与 useSeo 生成的 canonical 逐段相等"的对账测试，接口保留。

**验证**：`curl -sk http://127.0.0.1:8000/api/seo/schema/post/1 | grep -o '"url":"[^"]*"'` → 全部是 `https://choyeon.cc/posts/...` 形态。

**回归测试**：`tests/test_api_seo.py` 新增 `test_schema_urls_match_frontend_routes`。

### P1-6 canonical 单源守卫（复测更正：页面侧重复声明为 0）
**复测更正**：实现阶段 grep 复核 `frontend/pages/` 全目录，`rel: 'canonical'` / `rel="canonical"` 字面量出现 **0 次**——页面侧并无重复声明，无需删改。

**残留风险**：该口径目前只靠页面文件头注释约束，无机器守卫；新页面复制一段 `useHead({ link: [{ rel: 'canonical' }] })` 就会静默破坏单源（§2.3.3 第 3 条红线：canonical 单源 + 不得用请求 Host 拼地址，swr 缓存会把 Host 固化给全站）。

**改法**：只加静态扫描守卫测试，不改代码。

**回归测试**：`frontend/tests/unit/canonicalSingleSource.spec.ts`（新建，递归扫 `pages/` 断言页面侧 canonical 字面量为 0）。

***

## 3. P2 — 精细化与 GEO，一个月内做

### P2-1 Sitemap 索引 `lastmod` 恒为"今天"

**现象**：[backend/api/blog.py:3832-3842](file:///D:/WebProjects/Rosetta/backend/api/blog.py#L3832-L3842) 索引文件每个子表的 `<lastmod>` 都取当前日期；生产 sitemap 索引 3 个子表 lastmod 全为同一天。

**影响**：lastmod 是抓取预算的核心信号。每天全量"我刚更新过"会在数月内耗尽爬虫信任，最后退化成按平均频率抓取——恰恰在真正发布新内容时失去即时性。

**改法**：子表 lastmod 取该子表内最大 `updated_at`；仅索引层保留"最近一次生成时间"语义（或干脆省略索引层 lastmod）。

**验证**：`curl -sk https://choyeon.cc/sitemap.xml | grep lastmod` → 各子表不再同日全等。

**回归测试**：`tests/test_api_seo.py` 断言索引 lastmod = 子表最大更新时间而非 `date.today()`。

### P2-2 RSS 日期口径自相矛盾

**现象**：生产 RSS：`<lastBuildDate>` 为 2026-09-29，但条目 `<pubDate>` 最新为 2026-10-25；[backend/api/blog.py:230](file:///D:/WebProjects/Rosetta/backend/api/blog.py#L230) 取的是"最新文章时间"，[.py:243](file:///D:/WebProjects/Rosetta/backend/api/blog.py#L243) item link 固定默认语言。

**影响**：lastBuildDate < 最大 pubDate 是格式违规（RFC 订明它是"feed 整体最后构建时间"），聚合器据此判 feed 失养。

**改法**：`lastBuildDate = max(now, 最新 pubDate)` 取当下生成时间即可；item link 单语言是既定口径（AGENTS.md §2.2.1 第 7 条），**不改**。

**验证**：`curl -sk /rss.xml | xargs -I{} sh -c 'grep -o "<pubDate>[^<]*" {} | sort | tail -1'` 对比 lastBuildDate。

**回归测试**：`tests/test_api_seo.py::test_rss_lastbuild_date_is_build_time`。

### P2-3 GEO（AI 引用）零覆盖：llms.txt / security.txt / humans.txt

**现象**：`/llms.txt`、`/.well-known/security.txt`、`/humans.txt` 生产全 404。

**影响**：SEO & GEO Playbook 口径——AI 抓取器（ChatGPT/Perplexity/Gemini）对结构化摘要源有专门抓取习惯；llms.txt 是目前成本最低的 AI 侧投递面。FAQPage schema 富结果虽已限政府/健康站，但 AI 抽取仍直接消费其结构化问答。

**改法**：
1. Nitro 新增 `server/routes/llms.txt.get.ts`：站点一句话简介 + 四语入口 + 最新文章清单（复用 RSS 源数据，带 cache）；
2. `/.well-known/security.txt`（联系邮箱 + 有效期）；
3. 文章模板保留 FAQ 段落时同步输出 FAQPage schema（≥2 问才挂，照 blog-schema Step 6）。

**验证**：`curl -sk https://choyeon.cc/llms.txt | head` → 200 text/plain。

**回归测试**：`frontend/tests/unit/geoDeliveryRoutes.spec.ts`（llms.txt 与 security.txt 同文件，含"全仓只有一条 security.txt 生成器"反向断言）。

**复测更正（两处刻意不做）**：
1. `/humans.txt` 未落地——本项的 AI 投递面已由 `llms.txt`（纯文本 + 真实文章绝对链接 + 四语入口）覆盖，`humans.txt` 无任何抓取器消费口径，写一条没人读的纯文本路由属于死代码（AGENTS.md 无消费点红线，同批次 #23/#35/#45 的收口方向）。
2. FAQPage schema 未落地——全仓（排除 `pnpm-lock.yaml` 与本文档）grep `faq` 只命中图标名清单 `frontend/lib/lucide-svg-icons-all.ts`：站里既没有 FAQ 问答结构，也没有承载它的短代码或内容类型，"≥2 问才挂"的前置条件恒假。将来真加 FAQ 组件时，随组件一起补 schema 与守卫，不要先埋一段永不触发的分支。

### P2-4 IndexNow 即时推送（可选）

**现状**：仅 sitemap + 被动抓取。**改法**：发布/更新钩子（`do_action` 已有 post.published 族）挂 IndexNow key 推送（必应系；Google 不认但不冲突）。按 lean-build 原则列为可选项，不排进四周路线，只登记在 §6 待办。

### P2-5 移动端与 Core Web Vitals 专项

| 维度 | 当前 | 目标 | 动作 |
| --- | --- | --- | --- |
| LCP | 站内 hero（非外链）、首屏不 lazy、详情头图 `fetchpriority="high"`、列表卡片 `fetchpriority="low"` | < 2.5 s | 结构性动作已完成并由 `heroLcpAttributes.spec.ts` + 线上 curl 钉住；**PSI 读数本环境取不到**（见下） |
| CLS | 首页 `<img>` 宽高覆盖 **53/53**（实测 `document.images` 全带 `width`/`height`），`layout-shift` 累积值 **0** | < 0.1 | 已达成：全量补宽高；Google Fonts preload-only 已避免阻塞，无需再动 |
| INP | 后台 `/api/monitoring/performance/summary` 需 staff（匿名 401），未取窗口读数 | < 200 ms | 需要管理员 token 或在后台页面读数；列表页 `busy` 禁用态的交互反馈保持现状 |
| 移动可用性 | 窄屏外壳与首页 hero 均有契约测试 | — | 保持 `mobileShellLayout.spec.ts` · `heroMobileLayout.spec.ts` 绿即可 |

**PSI 实测受阻（2026-10-26 复测，两条路都堵）**：
1. PageSpeed Insights API 从生产机调用返回 **HTTP 403**（`www.googleapis.com/pagespeedonline/v5/...`，无 API key 的配额路径被 Google 侧拒），本机直连超时；
2. 面板内浏览器读 paint timing 拿到 `visibilityState="hidden"` + `viewport 0x0`，`largest-contentful-paint` 条目为空——后台化的 WebView 不产生绘制记录，任何 LCP/INP 读数在这里都是假的。

因此 LCP/INP 的**毫秒级 lab 读数不在本批次证据链里**，不要凭"门禁全绿"当作已达标。可用的替代实测（均为服务端与真实 DOM 口径）：首页 TTFB 1.07 s / 完整响应 1.08 s（HTML 289 KB）、`/posts` TTFB 0.61 s、CLS 累积 0、首页图片宽高覆盖 53/53。要拿到真实 CWV 需在有桌面网络的浏览器里手动跑一次 PSI 并回填本表。

***

## 4. 四周实施路线

| 周 | 内容 | 验收 |
| --- | --- | --- |
| W1 | P0-1 404 不缓存、P0-2 分页锚点、P0-3 hero LCP + 全量 img 宽高 | 三条 curl 验证全过 + 新增 3 个前端契约测试绿；生产机 `pnpm lint/typecheck/test/build` 串行全绿 |
| W2 | P1-1 越界页 301、P1-2 lang 映射、P1-3 og:image 去外链 | 同上；PSI 跑一次留基线截图 |
| W3 | P1-4 @graph 五实体、P1-5 seo.py URL 对账、P1-6 canonical 单源扫描 | rich-results 测试通过 ≥5 实体；对账测试绿 |
| W4 | P2-1 lastmod、P2-2 RSS 日期、P2-3 llms.txt + security.txt | sitemap/RSS/llms.txt 三 curl 全过；月度审计清单（§5 技能 Phase 5）首轮勾选 |

每轮收端口径：本地/生产机门禁串行 → CI 绿（注意 AGENTS.md 新口径：**CI 不含 vitest/build，必须生产机补跑**）→ curl/PSI 实测 → 再谈下一项。

***

## 5. 诚实限制（报告结论边界）

1. **社区技能 `web-quality-audit` 未安装成功**：`git clone https://github.com/addyosmani/web-quality-skills.git` 两次失败于本机 GitHub HTTPS 网络中断（与既有记忆一致）。其覆盖的 accessibility/performance 审计维度本报告未独立展开，仅由 website-seo 的 CWV 清单部分代替。
2. **线上 nginx 与仓库 conf 不同步**：生产首页实际返回 HSTS（`max-age=63072000; includeSubDomains; preload`），但 [deploy/nginx-site.conf](file:///D:/WebProjects/Rosetta/deploy/nginx-site.conf) 中 HSTS 声明是注释状态。线上 vhost 手调过——改任何头之前必须先 diff 线上 `/etc/nginx/` 实际配置，不能以仓库文件为准。
3. 本报告 P0/P1 的"影响"是机制推导 + 状态码/头实测；**LCP/CLS/INP 的具体毫秒数未采集**（需 PSI field/lab 数据），W1 完成后补。

***

## 6. 参考

- `website-seo` 技能：五阶段（On-page/Technical/Schema/Internal linking/Monthly audit）
- `blog-schema` 技能：@graph 实体互链、Step 8 验证清单、废弃类型禁令（HowTo/SpecialAnnouncement/Q&A/Dataset/Sitelinks Searchbox）
- `SEO-&-GEO-Playbook` 技能：GEO/IndexNow/E-E-A-T
- 项目红线：AGENTS.md §2.3.3（canonical/hreflang 单源）、§2.3.2（状态码闸门只能放路由中间件/`app:rendered`）
