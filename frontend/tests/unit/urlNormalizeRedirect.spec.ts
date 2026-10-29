/**
 * URL 规范化中间件（server/middleware/05-url-normalize.ts）的运行时契约。
 *
 * 两条口径都用 fake event 直测（h3 v1 的 sendRedirect 只碰 `event.node.res`）：
 * ① 折叠/去尾斜杠的目标必须精确，且保留 query；
 * ② 301 的 `cache-control` 必须是 `no-store` —— 本中间件直接结束响应、不走渲染器，
 *    `ssr-html-revalidate` 的两道钩子都轮不到它，routeRules 给该路径的
 *    `public, max-age=0, s-maxage=…` 会原样留在 301 上（线上实测 `/en/` 回了 300s 可缓存）。
 */

import { describe, it, expect } from 'vitest'
import middleware from '../../server/middleware/05-url-normalize'

interface FakeEvent {
  node: {
    req: { url: string, method: string }
    res: {
      statusCode: number
      setHeader: (name: string, value: string) => void
      getHeader: (name: string) => string | undefined
      removeHeader: (name: string) => void
      end: () => void
      writableEnded: boolean
      headersSent: boolean
    }
  }
  method: string
  path: string
  handled: boolean
  headers: Map<string, string>
}

function makeEvent(url: string, method = 'GET'): FakeEvent {
  const headers = new Map<string, string>()
  const res = {
    statusCode: 200,
    setHeader(name: string, value: string) {
      headers.set(name.toLowerCase(), value)
    },
    getHeader(name: string) {
      return headers.get(name.toLowerCase())
    },
    removeHeader(name: string) {
      headers.delete(name.toLowerCase())
    },
    end() {},
    writableEnded: false,
    headersSent: false
  }
  return { node: { req: { url, method }, res }, method, path: url, handled: false, headers }
}

async function run(url: string, method = 'GET'): Promise<FakeEvent> {
  const event = makeEvent(url, method)
  // sendRedirect 内部走 defer，await 一下让 res.end 落地
  await (middleware as unknown as (e: FakeEvent) => unknown)(event)
  await Promise.resolve()
  return event
}

describe('05-url-normalize', () => {
  it('去掉页面路径末尾斜杠，并保留 query', async () => {
    const event = await run('/posts/hello/?a=1')
    expect(event.node.res.statusCode).toBe(301)
    expect(event.headers.get('location')).toBe('/posts/hello?a=1')
    expect(event.headers.get('cache-control')).toBe('no-store')
  })

  it('/en/ 这类语言前缀首页同样 301 到无斜杠形态', async () => {
    const event = await run('/en/')
    expect(event.node.res.statusCode).toBe(301)
    expect(event.headers.get('location')).toBe('/en')
    expect(event.headers.get('cache-control')).toBe('no-store')
  })

  it('折叠百分号叠加编码（%25E6 → %E6），且不误伤真实 %XX', async () => {
    const event = await run('/posts/%25E6%2588%2591')
    expect(event.headers.get('location')).toBe('/posts/%E6%88%91')
    expect(event.headers.get('cache-control')).toBe('no-store')
  })

  it('重复斜杠前缀归一', async () => {
    const event = await run('//posts')
    expect(event.headers.get('location')).toBe('/posts')
  })

  it('已规范的 URL 不重定向', async () => {
    const event = await run('/posts/hello')
    expect(event.headers.get('location')).toBeUndefined()
    expect(event.node.res.statusCode).toBe(200)
  })

  it('首页 / 不做处理（默认语言首页，也是 x-default 指向）', async () => {
    const event = await run('/')
    expect(event.headers.get('location')).toBeUndefined()
  })

  it('/api 与内部资源不做处理', async () => {
    for (const url of ['/api/blog/posts/', '/_nuxt/x.js/', '/@vite/client/']) {
      const event = await run(url)
      expect(event.headers.get('location'), url).toBeUndefined()
    }
  })

  it('非 GET/HEAD 不做处理（写请求的 URL 形态由调用方负责）', async () => {
    const event = await run('/posts/hello/', 'POST')
    expect(event.headers.get('location')).toBeUndefined()
  })
})
