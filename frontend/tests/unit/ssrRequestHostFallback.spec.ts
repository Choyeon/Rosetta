/**
 * 站点根兜底：SSR 期从请求事件里取 Host 的三形态 + 回环闸门。
 *
 * 背景（实测，2026-10-30 本地 dev）：
 *   `usePublicSiteUrl()` 在 SSR 期用 `useRequestHeaders(['host'])` 取 Host，但本仓的 Nitro
 *   版本把 event 包成 web 形态，`event.node.req.headers` 是**空对象**（同
 *   `server/utils/purgeSecret.ts` 的坑），于是 host 恒为空串。表现有两条：
 *     ① 未配 NUXT_PUBLIC_SITE_URL 时（本地开发），canonical / og:url / 分享链接渲染成相对路径；
 *     ② 客户端用 `window.location.origin` 算出绝对地址，文章页每次加载都报
 *        `Hydration attribute mismatch`（分享条的 X / 微博 / Telegram 三个 href）。
 *   修法是按 web headers → node headers → rawHeaders 顺序取；rawHeaders 是实测唯一有值的容器。
 *
 * 生产环境不收 Host 推导（Nitro 页面缓存键不含 Host，伪造一次就能把攻击者域名写进 canonical
 * 并在 TTL 内投毒），所以回环闸门本身也是被测对象：`localhost.evil.com` 这类前缀骗术必须落空。
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import process from 'node:process'

import { pickRequestHost, loopbackOriginFromHost } from '~~/composables/useSeo'

const SEO_TS = `${process.cwd().replace(/[\\/]$/, '')}/composables/useSeo.ts`

describe('pickRequestHost：三形态取 Host', () => {
  it('web 形态的 Headers.get（h3 web event 的标准形状）', () => {
    expect(pickRequestHost({
      webHeaders: new Headers({ host: 'localhost:3000' })
    })).toBe('localhost:3000')
  })

  it('web 形态的普通对象头袋', () => {
    expect(pickRequestHost({
      webHeaders: { host: 'localhost:3000' }
    })).toBe('localhost:3000')
  })

  it('node 形态头袋有值时直接命中', () => {
    expect(pickRequestHost({
      nodeHeaders: { host: '127.0.0.1:3000' }
    })).toBe('127.0.0.1:3000')
  })

  it('node 头袋是空对象时退回 rawHeaders（真实踩到的形态）', () => {
    // 实测 dev SSR：nodeHeaders = {}、rawHeaders 里才有 host
    expect(pickRequestHost({
      webHeaders: null,
      nodeHeaders: {},
      rawHeaders: ['Host', 'localhost:3000', 'accept', 'text/html']
    })).toBe('localhost:3000')
  })

  it('web / node / raw 全空时返回空串（生产缺配置时的安全退化）', () => {
    expect(pickRequestHost({})).toBe('')
    expect(pickRequestHost({ webHeaders: null, nodeHeaders: {}, rawHeaders: [] })).toBe('')
  })

  it('rawHeaders 里没有 host（或数组不完整）也不会造出假值', () => {
    expect(pickRequestHost({ rawHeaders: ['accept', 'text/html'] })).toBe('')
    expect(pickRequestHost({ rawHeaders: ['host'] })).toBe('')
  })
})

describe('loopbackOriginFromHost：只认回环地址', () => {
  it('三种回环形态（含端口）都能推导成站点根', () => {
    expect(loopbackOriginFromHost('localhost:3000')).toBe('http://localhost:3000')
    expect(loopbackOriginFromHost('127.0.0.1')).toBe('http://127.0.0.1')
    expect(loopbackOriginFromHost('[::1]:3000')).toBe('http://[::1]:3000')
  })

  it('真实域名 / 前缀骗术 / 私有网段一律不推导', () => {
    for (const host of [
      'choyeon.cc',
      'www.choyeon.cc',
      'localhost.evil.com',
      '127.0.0.1.evil.com',
      'notlocalhost',
      '10.0.0.5',
      ''
    ]) {
      expect(loopbackOriginFromHost(host), `${host} 不该被当成站点根`).toBe('')
    }
  })
})

describe('接线：usePublicSiteUrl 不得再走 useRequestHeaders', () => {
  const src = readFileSync(SEO_TS, 'utf8')

  it('SSR 兜底走 pickRequestHost → loopbackOriginFromHost', () => {
    expect(src).toContain('return loopbackOriginFromHost(readSsrRequestHost())')
    expect(src).toContain('rawHeaders: event.node?.req?.rawHeaders ?? null')
  })

  it('不再用 useRequestHeaders 取 host（那个袋子实测恒空）', () => {
    expect(src).not.toMatch(/useRequestHeaders\(\['host'\]\)/)
  })
})
