/**
 * SEO 工具页「爬虫预览」标签的接线守卫（批次 #96 之前：`GET /api/seo/open-graph/*` 与
 * `GET /api/seo/schema/*` 两条公开口在后台零消费方——运营者只能靠 curl 或"分享出去看看"
 * 来判断爬虫实际读到了什么）。
 *
 * 三条口径必须由源码级断言钉住，任何一条改坏都是静默的假读数：
 * * 两条口**无 `{success,data}` 信封**，且对缺失/不可见资源回 **HTTP 200 + 只剩 `error` 键**
 *   （不是 404：承认存在即可按 id 枚举草稿）。页面必须把 `error` 判成"这篇不存在"，
 *   不能因为状态码 200 就渲染空卡片。
 * * 两条口**不读调用方身份**（内部按 `post_is_publicly_visible(post, None)` 判定），
 *   所以管理员登录态不会让预览"解锁"出爬虫看不到的东西——页面上的警告就是爬虫看到的。
 * * og 键名含冒号，`AdminSeoOpenGraph` 与逐键展示清单必须与后端产出的键**一一对应**：
 *   后端加一个 `og:*` 而前端清单没登记，表现是抓取器读得到、后台永远看不到。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')
const page = readFileSync(resolve(ROOT, 'pages/admin/tools/seo.vue'), 'utf8')
const helper = readFileSync(resolve(ROOT, 'composables/useAdminManage.ts'), 'utf8')
const backend = readFileSync(resolve(ROOT, '../backend/api/seo.py'), 'utf8')

/** 后端按资源取数的两条公开口（本 FastAPI 版本装饰器的路径写在下一行，正则要跨行）。
 *  `{resource_type}` 归一成 `article`：本页只做文章预览，分类/作者的 resource_type 不在范围内。 */
function declaredResourcePaths(): string[] {
  const re = /@router\.get\(\s*"([^"]+)"/g
  const out: string[] = []
  let m: RegExpExecArray | null
  while ((m = re.exec(backend)) !== null) {
    const path = m[1]!
    if (path.includes('open-graph') || path.includes('schema')) {
      out.push(path.replace(/^\//, '').replace('{resource_type}', 'article'))
    }
  }
  return [...new Set(out)].sort()
}

/** 页面侧真正发出的请求：取 helper 两个 fetcher 里 apiFetch 的实参，把模板变量归一。
 *  `seo/` 前缀要剥掉——apiFetch 的 baseURL 自带 `/api`，而后端装饰器只写 router 内的相对路径。 */
function requestedResourcePaths(): string[] {
  const re = /apiFetch<\s*(?:AdminSeoOpenGraph|AdminSeoJsonLd)\s*>\(\s*['"`]([^'"`]+)['"`]/g
  const out: string[] = []
  let m: RegExpExecArray | null
  while ((m = re.exec(helper)) !== null) {
    out.push(
      m[1]!
        .replace(/\$\{resourceId\}/g, '{resource_id}')
        .replace(/^\/?seo\//, '')
    )
  }
  return [...new Set(out)].sort()
}

/** helper 里某个 fetcher 的函数体，用于逐函数检查请求形态。 */
function helperFnBody(name: string): string {
  const start = helper.indexOf(`export function ${name}`)
  expect(start, `helper 缺函数 ${name}`).toBeGreaterThan(-1)
  const end = helper.indexOf('\n}', start)
  return helper.slice(start, end)
}

/** 后端 open-graph 分支产出的全部 `og:* / article:* / twitter:*` 字面键。 */
function backendOpenGraphKeys(): string[] {
  const re = /"(og|article|twitter):[a-z_]+(?::[a-z_]+)?"/g
  const out: string[] = []
  let m: RegExpExecArray | null
  while ((m = re.exec(backend)) !== null) out.push(m[0]!.slice(1, -1))
  return [...new Set(out)].sort()
}

describe('爬虫预览的两条公开口接线', () => {
  it('后端只声明这两条按资源取数的口，且 resource_type 是路径段', () => {
    expect(declaredResourcePaths()).toEqual([
      'open-graph/article/{resource_id}',
      'schema/article/{resource_id}'
    ])
    expect(backend).toMatch(/open-graph\/\{resource_type\}\/\{resource_id\}"/)
    expect(backend).toMatch(/\/schema\/\{resource_type\}\/\{resource_id\}"/)
  })

  it('前端请求集与后端声明集精确相等（路径归一后）', () => {
    expect(requestedResourcePaths()).toEqual(declaredResourcePaths())
  })

  it('页面取数走 helper 的两个 fetcher，不裸写 apiFetch', () => {
    expect(page).toContain('fetchAdminSeoOpenGraph(')
    expect(page).toContain('fetchAdminSeoJsonLd(')
  })

  it('两条口都是 GET 语义（helper 里不得带 method），且静默失败由页内分支承接', () => {
    for (const name of ['fetchAdminSeoOpenGraph', 'fetchAdminSeoJsonLd']) {
      const body = helperFnBody(name)
      expect(body, `${name} 不该声明 method`).not.toMatch(/method:\s*['"`]/)
      expect(body).toContain('silentToast: options.silentToast ?? true')
    }
  })
})

describe('200 + error 键必须判成「爬虫看不到」', () => {
  it('隐藏态判定同时看两条口的 error（任一条缺内容都不算成功）', () => {
    expect(page).toMatch(
      /const previewHidden = computed\(\(\) => !!openGraph\.value\?\.error \|\| !!jsonLd\.value\?\.error\)/
    )
  })

  it('隐藏态渲染 warning 分支而不是空卡片', () => {
    expect(page).toMatch(/v-else-if="previewHidden"/)
    expect(page).toMatch(/variant="warning"/)
    expect(page).toMatch(/previewHiddenReason/)
  })

  it('口径写进类型与注释：200 ≠ 有内容、接口不读调用方身份', () => {
    expect(page).toMatch(/不读调用方身份/)
    expect(helper).toMatch(/不读调用方身份/)
    expect(page).toMatch(/无 \{success,data\} 信封|不是 404/)
  })
})

describe('og 键清单与后端逐键对齐', () => {
  it('AdminSeoOpenGraph 声明了后端产出的每一个键', () => {
    const iface = helper.slice(
      helper.indexOf('export interface AdminSeoOpenGraph'),
      helper.indexOf('export interface AdminSeoJsonLd')
    )
    for (const key of backendOpenGraphKeys()) {
      expect(iface, `类型缺键 ${key}`).toContain(`'${key}'`)
    }
  })

  it('逐键展示清单（OG_ROW_KEYS）覆盖同一组键，一个不漏', () => {
    const rows = page.slice(
      page.indexOf('const OG_ROW_KEYS'),
      page.indexOf('const OG_DESCRIPTION_LIMIT')
    )
    for (const key of backendOpenGraphKeys()) {
      expect(rows, `展示清单缺键 ${key}`).toContain(`'${key}'`)
    }
    expect(page).toMatch(/v-for="row in ogRows"/)
  })

  it('展示面渲染 JSON-LD 原文，不做前端二次拼装', () => {
    expect(page).toMatch(/data-testid="seo-preview-jsonld"/)
    expect(page).toMatch(/JSON\.stringify\(jsonLd\.value \?\? \{\}, null, 2\)/)
  })

  it('og:description 截断阈值与后端 `[:200]` 同数', () => {
    expect(backend).toMatch(/description\[:200\]/)
    expect(page).toMatch(/const OG_DESCRIPTION_LIMIT = 200/)
  })
})

describe('候选清单与渲染口径', () => {
  it('选择器复用 GET /seo/scores 并按后端上限取满 100（评分表当前页只有 10 行）', () => {
    expect(backend).toMatch(/page_size: int = Query\(20, ge=1, le=100\)/)
    expect(page).toMatch(/fetchAdminSeoScores\(\{\s*page: 1, page_size: 100\s*\}/)
  })

  it('候选只在进入标签时取一次，失败可强制重试，不做静默轮询', () => {
    expect(page).toMatch(/watch\(activeTab,[\s\S]*?if \(tab === 'preview'\) void ensurePreviewCandidates\(\)/)
    expect(page).toMatch(/async function ensurePreviewCandidates\(force = false\)/)
    expect(page).toMatch(/@click="ensurePreviewCandidates\(true\)"/)
    expect(page).not.toMatch(/setInterval/)
  })

  it('后台页保持 ssr:false + admin 布局', () => {
    expect(page).toMatch(/definePageMeta\(\{\s*ssr:\s*false,\s*layout:\s*'admin'\s*\}\)/)
  })

  it('全部请求 silentToast，错误走页内分支而非自动 toast', () => {
    const previewBody = page.slice(
      page.indexOf('async function loadPreview()'),
      page.indexOf('async function ensurePreviewCandidates')
    )
    expect(previewBody).toMatch(/silentToast: true/)
    expect(previewBody).toMatch(/previewError\.value = errText\(/)
    const candidatesBody = page.slice(
      page.indexOf('async function ensurePreviewCandidates'),
      page.indexOf('watch(activeTab')
    )
    expect(candidatesBody).toMatch(/silentToast: true/)
    expect(candidatesBody).toMatch(/previewError\.value = errText\(/)
  })

  it('未用 eslint-disable 绕开规范', () => {
    expect(page).not.toMatch(/eslint-disable/)
  })
})
