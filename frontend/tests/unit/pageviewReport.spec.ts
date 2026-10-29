/**
 * 边缘页面浏览上报（批次 #59）的口径闸门。
 *
 * 为什么访客记录必须由 Nitro 边缘上报：nginx 只把 `/api` 与 `/media` 转给 FastAPI，
 * HTML 全部由 Nitro 自己渲染直接回浏览器——后端从没见过那次页面请求，`visit_logs`
 * 数出来的只有 XHR 和后台自己的调用（真实访客读完一篇文章、Googlebot 抓走一个页面，
 * 一条都不进表）。这条链的成败全在"报什么、怎么报"两个问题上，所以两侧都要钉住：
 *
 * 1. 纯函数：哪些请求算"有人看了一个页面"、IP 取哪一跳、Cookie 发什么。
 *    红线是**只发名字不发值**——值是会话凭证，落进纯追加的访问日志表等于长期泄漏。
 * 2. 跨端契约：前端产出的载荷键集合必须与后端 `PageviewReport` 声明的字段集合相等。
 *    后端那个模型带 `extra="forbid"`，所以两边一旦漂移，线上表现是**每一条上报都 422**、
 *    访客记录页永远只有 API 行——而这条链是 fire-and-forget，一个错都不会报出来。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  PAGEVIEW_PATH,
  SHARED_SECRET_HEADER,
  buildPageviewPayload,
  cookieNameList,
  firstForwardedHop,
  isDocumentRequest
} from '../../server/middleware/09-pageview-report'

const HTML_ACCEPT = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'

function readSource(rel: string): string {
  return readFileSync(resolve(process.cwd(), rel), 'utf8').replace(/\r\n/g, '\n')
}

const middlewareSource = readSource('server/middleware/09-pageview-report.ts')
const backendSource = readSource('../backend/api/monitoring.py')

function documented(path: string, accept = HTML_ACCEPT, method = 'GET'): boolean {
  return isDocumentRequest({ method, path, accept })
}

describe('isDocumentRequest：只把人看的页面算作页面浏览', () => {
  it('真实页面路径计入（含语言前缀与带查询串的裸路径）', () => {
    for (const path of ['/', '/posts/hello', '/en/posts/hello', '/zh_Hant/guestbook', '/about']) {
      expect(documented(path), path).toBe(true)
    }
  })

  it('机器面与资源面一律不计入', () => {
    const machineFaces = [
      '/api/settings/public',
      '/media/uploads/a.png',
      '/themes/editorial-wp-style/style.css',
      '/_nuxt/entry.js',
      '/_rosetta/purge-cache',
      '/@vite/client',
      '/.well-known/security.txt',
      '/favicon.ico',
      '/robots.txt',
      '/rss.xml',
      '/feed',
      '/sitemap.xml',
      '/sitemap-posts-1.xml',
      '/placeholder-covers/3.svg'
    ]
    for (const path of machineFaces) {
      expect(documented(path), path).toBe(false)
    }
  })

  it('非 GET 与不带 text/html 的请求不计入', () => {
    expect(documented('/posts/hello', HTML_ACCEPT, 'POST')).toBe(false)
    expect(documented('/posts/hello', 'application/json')).toBe(false)
    expect(documented('/posts/hello', '')).toBe(false)
    // 爬虫与 curl 常不带 Accept；只认 xhtml 的客户端同样算看过一个页面
    expect(documented('/posts/hello', 'application/xhtml+xml')).toBe(true)
  })

  it('无扩展名的中文 slug 照常计入，带扩展名的路径不靠猜', () => {
    expect(documented('/%E9%9A%90%E7%A7%98')).toBe(true)
    expect(documented('/about.data.json')).toBe(false)
  })
})

describe('firstForwardedHop：取最外层反代看到的那一跳', () => {
  it('链式 XFF 取第一跳', () => {
    expect(firstForwardedHop('203.0.113.1, 10.0.0.1, 127.0.0.1')).toBe('203.0.113.1')
  })

  it('缺失、空值与超长值回空串（由调用方退回 socket 对端）', () => {
    expect(firstForwardedHop(undefined)).toBe('')
    expect(firstForwardedHop('')).toBe('')
    expect(firstForwardedHop([])).toBe('')
    expect(firstForwardedHop('x'.repeat(51))).toBe('')
    expect(firstForwardedHop(['203.0.113.9, 10.0.0.1'])).toBe('203.0.113.9')
  })
})

describe('cookieNameList：名字留下，值一个字节都不走', () => {
  it('切掉等号右侧并去重', () => {
    expect(cookieNameList('rosetta_lang=zh; session_token=SECRET-VALUE; rosetta_lang=en')).toBe(
      'rosetta_lang; session_token'
    )
  })

  it('不保留任何值形态的片段', () => {
    const names = cookieNameList('a=1; b=2; c=3')
    expect(names).toBe('a; b; c')
    expect(names).not.toMatch(/[=0-9]/)
  })

  it('空请求头回空串，名称数量与总长度都有上限', () => {
    expect(cookieNameList(undefined)).toBe('')
    const many = Array.from({ length: 40 }, (_, i) => `n${i}=v`).join('; ')
    const limited = cookieNameList(many)
    expect(limited.split('; ')).toHaveLength(24)
    expect(limited.length).toBeLessThanOrEqual(255)
  })
})

describe('buildPageviewPayload：与后端字段限制逐条对齐', () => {
  const base = {
    path: '/posts/hello',
    headers: {
      'x-forwarded-for': '203.0.113.42, 127.0.0.1',
      'user-agent': 'Mozilla/5.0 (Macintosh) Chrome/120',
      'referer': 'https://choyeon.cc/',
      'cookie': 'rosetta_lang=zh; session_token=SECRET-VALUE',
      'accept-language': 'zh-CN,zh;q=0.9'
    },
    socketPeer: '127.0.0.1',
    statusCode: 200,
    responseTimeMs: 83
  }

  it('字段取值口径', () => {
    const payload = buildPageviewPayload(base)
    expect(payload).toEqual({
      path: '/posts/hello',
      method: 'GET',
      ip: '203.0.113.42',
      user_agent: 'Mozilla/5.0 (Macintosh) Chrome/120',
      referer: 'https://choyeon.cc/',
      cookie_names: 'rosetta_lang; session_token',
      accept_language: 'zh-CN,zh;q=0.9',
      status_code: 200,
      response_time_ms: 83
    })
  })

  it('没有转发头时退回 socket 对端（而不是留空）', () => {
    const payload = buildPageviewPayload({ ...base, headers: {} })
    expect(payload.ip).toBe('127.0.0.1')
    expect(payload.cookie_names).toBe('')
  })

  it('载荷里不存在 cookie 原文字段，序列化后也不含任何值', () => {
    const payload = buildPageviewPayload(base)
    expect(Object.keys(payload)).not.toContain('cookie')
    expect(JSON.stringify(payload)).not.toContain('SECRET-VALUE')
  })

  it('超长输入按后端 max_length 裁切，负耗时钳到 0', () => {
    const payload = buildPageviewPayload({
      ...base,
      path: `/${'p'.repeat(600)}`,
      headers: { ...base.headers, 'user-agent': 'u'.repeat(600), 'accept-language': 'l'.repeat(200) },
      responseTimeMs: -5.7
    })
    expect(payload.path).toHaveLength(500)
    expect(payload.user_agent).toHaveLength(500)
    expect(payload.accept_language).toHaveLength(100)
    expect(payload.response_time_ms).toBe(0)
  })

  it('状态码原样透传（404 页面也是真实的一次访问）', () => {
    expect(buildPageviewPayload({ ...base, statusCode: 404 }).status_code).toBe(404)
  })
})

describe('跨端契约：前端载荷 ⇔ 后端 PageviewReport', () => {
  /** 从后端源码里取出 PageviewReport 的类体（到下一个顶层声明为止）。 */
  function backendReportClassBody(): string {
    const block = backendSource.match(/class PageviewReport\(BaseModel\):\n([\s\S]*?)\n\nclass /)
    if (!block) throw new Error('未在后端源码找到 PageviewReport —— 口被删了？')
    return block[1] ?? ''
  }

  it('字段集合精确相等（后端 extra="forbid"，漂移即全量 422）', () => {
    const payload = buildPageviewPayload({
      path: '/',
      headers: {},
      statusCode: 200,
      responseTimeMs: 0
    })
    const declared = [...backendReportClassBody().matchAll(/^ {4}(\w+):\s/gm)].map(m => m[1])
    expect(declared.length).toBeGreaterThan(0)
    expect(Object.keys(payload).sort()).toEqual(declared.sort())
  })

  it('后端模型声明禁止多余键', () => {
    expect(backendReportClassBody()).toMatch(/model_config = ConfigDict\(extra="forbid"\)/)
  })

  it('上报路径与后端挂载前缀拼得出完整 API 路径', () => {
    expect(PAGEVIEW_PATH).toBe('/monitoring/pageviews')
    expect(backendSource).toMatch(/@router\.post\(\n {4}"\/pageviews",/)
    expect(readSource('../backend/main.py')).toMatch(/prefix="\/api\/monitoring"/)
  })

  it('鉴权头名两侧同一个（复用前后端已有的共享密钥，不新增配置项）', () => {
    expect(SHARED_SECRET_HEADER).toBe('x-rosetta-purge-secret')
    expect(backendSource).toMatch(/alias="x-rosetta-purge-secret"/)
  })
})

describe('中间件红线：遥测不得影响访客本身', () => {
  it('上报不 await —— 失败绝不能变成访客看到的 500', () => {
    expect(middlewareSource).toMatch(/\n {4}globalThis\n {6}\.fetch\(/)
    expect(middlewareSource).not.toMatch(/\bawait globalThis\.fetch|\bawait \(?\s*globalThis/)
  })

  it('密钥缺失时静默关闭整条链（不发注定 403 的请求）', () => {
    expect(middlewareSource).toMatch(/if \(!secret\) return/)
  })

  it('后端地址未配时跳过，而不是让页面渲染撞 503', () => {
    expect(middlewareSource).toMatch(/catch \{\n {6}return \/\/ 后端地址没配/)
  })

  it('落库前服务端还会重导一次 cookie 名称（双保险）', () => {
    expect(backendSource).toMatch(/cookie_names=_cookie_names_from_raw\(payload\.cookie_names\)/)
  })
})
