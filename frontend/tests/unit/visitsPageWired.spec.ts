/**
 * 访客记录页（/admin/tools/visits）的接线与读数口径。
 *
 * 这页存在的意义是把"谁访问了站点"回答完整：真实来源 IP、原始 UA、按 UA 现算的系统/浏览器/设备、
 * Cookie 名称、Accept-Language、登录身份。它同时是仪表盘 PV/UV 卡片「访客记录」入口的落地页。
 *
 * 最硬的一条是**后端 items 字段集 ⇔ 页面 VisitItem 字段集**双向对账：
 * 后端加一列（比如新的遥测头）而页面清单没登记，表现是"接口回了、后台永远看不到"，
 * 接口层一个错都不报——正是本仓反复踩过的「写口收键、读口不回吐」的镜像形态。
 *
 * 另外四条口径写进页面头注释，这里逐条钉住：
 * * IP 只在 `TRUSTED_PROXY_IPS` 含反代时才是访客真实地址，整批回环必须显式告警（否则 UV 被读成 1）；
 * * Cookie 只有名字，值不落库也不上屏；
 * * `is_bot === null` 是"未判定"的历史行，既不算真人也不算机器；
 * * `window_truncated` 时窗口读数只是下界。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')
const visitsPage = readFileSync(resolve(ROOT, 'pages/admin/tools/visits.vue'), 'utf8')
const dashboard = readFileSync(resolve(ROOT, 'pages/admin/index.vue'), 'utf8')
const monitoringPage = readFileSync(resolve(ROOT, 'pages/admin/tools/monitoring.vue'), 'utf8')
const menu = readFileSync(resolve(ROOT, 'config/admin-menu.ts'), 'utf8')
const backend = readFileSync(resolve(ROOT, '../backend/api/monitoring.py'), 'utf8')

/**
 * 只扫 `get_visit_records` 这一个 handler 的函数体。
 * 锚点不能落在 `items.append(` 上——`_flush_visit_queue` 里也有同一条语句，
 * 按全文第一次出现取块会拿到队列代码，两个清单都会"对账通过"却对的是别处。
 */
const HANDLER = backend.slice(backend.indexOf('async def get_visit_records('))

/** 后端 handler 里 `items.append({...})` 真实回吐的键。 */
function backendItemKeys(): string[] {
  const start = HANDLER.indexOf('items.append(')
  const block = HANDLER.slice(start, HANDLER.indexOf('return {', start))
  const keys: string[] = []
  const re = /"(\w+)":\s/g
  let m: RegExpExecArray | null
  while ((m = re.exec(block)) !== null) keys.push(m[1]!)
  return [...new Set(keys)]
}

/** 后端响应体顶层键（items.append 之后那个 return 字典，止于下一条装饰器）。 */
function backendBodyKeys(): string[] {
  const start = HANDLER.indexOf('return {')
  const block = HANDLER.slice(start, HANDLER.indexOf('\n@', start))
  const keys: string[] = []
  const re = /^\s{8}"(\w+)":\s/gm
  let m: RegExpExecArray | null
  while ((m = re.exec(block)) !== null) keys.push(m[1]!)
  return [...new Set(keys)]
}

function interfaceFields(name: string): string[] {
  const start = visitsPage.indexOf(`interface ${name} {`)
  expect(start, `页面里没有 interface ${name}`).toBeGreaterThan(-1)
  const block = visitsPage.slice(start + 1, visitsPage.indexOf('\n}', start))
  const keys: string[] = []
  const re = /^ {2}(\w+)\??:/gm
  let m: RegExpExecArray | null
  while ((m = re.exec(block)) !== null) keys.push(m[1]!)
  return keys
}

describe('访客记录页的取数接线', () => {
  it('扫描器自检：后端明细字段与顶层字段都取到了', () => {
    expect(backendItemKeys().length).toBeGreaterThanOrEqual(20)
    expect(backendBodyKeys()).toEqual(
      expect.arrayContaining(['items', 'total', 'unique_ips', 'bot_total', 'window_truncated'])
    )
  })

  it('页面 VisitItem 字段集与后端 items 键集精确相等', () => {
    expect(interfaceFields('VisitItem').sort()).toEqual(backendItemKeys().sort())
  })

  it('页面 ListBody 字段集与后端响应顶层键集精确相等', () => {
    expect(interfaceFields('ListBody').sort()).toEqual(backendBodyKeys().sort())
  })

  it('明细与访问量两条口都请求，且不套 success 信封', () => {
    expect(visitsPage).toContain('/monitoring/visits')
    expect(visitsPage).toContain('/monitoring/visits/summary')
    expect(visitsPage).not.toMatch(/body\.success|data\.success/)
  })

  it('取数失败按段隔离：两段各自 silentToast，一段挂不清整页', () => {
    expect(visitsPage).toContain('silentToast: true')
    expect(visitsPage).toContain('Promise.all([loadSummary(), loadList()])')
    expect(visitsPage).toContain('summaryError')
    expect(visitsPage).toContain('listError')
  })

  it('后台菜单有入口，且监控页给出跳转', () => {
    expect(menu).toContain('\'/admin/tools/visits\'')
    expect(menu).toContain('访客记录')
    expect(monitoringPage).toContain('/admin/tools/visits')
  })

  it('仪表盘 PV 与 UV 两张卡都把入口指到本页', () => {
    const toVisits = dashboard.match(/to: '\/admin\/tools\/visits'/g) ?? []
    expect(toVisits.length).toBe(2)
  })

  it('后台页保持 ssr:false + admin 布局', () => {
    expect(visitsPage).toMatch(/definePageMeta\(\{\s*ssr:\s*false,\s*layout:\s*'admin'\s*\}\)/)
  })
})

describe('访客记录页的四条读数口径', () => {
  it('整批回环 IP 时显式告警并说明 TRUSTED_PROXY_IPS', () => {
    const template = visitsPage.slice(visitsPage.indexOf('<template>'), visitsPage.indexOf('<script setup'))
    expect(template).toContain('loopbackOnly')
    expect(visitsPage).toContain('TRUSTED_PROXY_IPS')
    expect(visitsPage).toMatch(/127\./)
  })

  it('Cookie 只回名字，页面上不得出现任何"值"的取数或渲染', () => {
    expect(visitsPage).toContain('cookie_names')
    expect(visitsPage).not.toContain('cookie_values')
    expect(visitsPage).toMatch(/Cookie 只记录名称|Cookie 名/)
  })

  it('is_bot 为 null 时显示"未判定"，不硬猜成真人或机器', () => {
    expect(visitsPage).toContain('is_bot === null')
    expect(visitsPage).toContain('未判定')
  })

  it('窗口被保留策略截短时下界口径必须同时给出', () => {
    expect(visitsPage).toContain('window_truncated')
    expect(visitsPage).toContain('retention_days')
    expect(visitsPage).toContain('data_since')
    expect(visitsPage).toMatch(/下界/)
  })

  it('筛选要显式应用且把页码重置回 1', () => {
    expect(visitsPage).toMatch(/function applyFilters\(\)[\s\S]*?page\.value = 1/)
    expect(visitsPage).toMatch(/watch\(\[page, pageSize\]/)
  })
})
