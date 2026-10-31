/**
 * 批次 #149：监控页五个「后端一直在算、后台一个都没画」的读数。
 *
 * 这一族的形状与接口缺口不同：接口存在、字段存在、页面也点了那条口，
 * 只是响应摊开后有五个键没人读。表现是运营者以为"缓存没指标""中位数没人关心"，
 * 而服务端每次请求都在算——`monitoringEndpointsWired.spec.ts` 按「路由集合 ⇔ 页面请求集合」
 * 对账，看不见"同一条口里的某几个键没人读"。所以这里的守卫必须是**字段级**双向对账：
 * 后端 `monitoring.py` 的声明 ↔ 页面 `type ...Shape` ↔ 模板/计算属性里的真实消费点，三处都要有。
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..')
const REPO = join(ROOT, '..')

const page = readFileSync(join(ROOT, 'pages', 'admin', 'tools', 'monitoring.vue'), 'utf-8')
const api = readFileSync(join(REPO, 'backend', 'api', 'monitoring.py'), 'utf-8')

function templateOf(source: string): string {
  const start = source.indexOf('<template>')
  const end = source.lastIndexOf('</template>')
  expect(start).toBeGreaterThanOrEqual(0)
  expect(end).toBeGreaterThan(start)
  return source.slice(start, end)
}

const tpl = templateOf(page)

describe('五个字段在后端仍是声明过的读数', () => {
  // 反向闸门：后端哪天删掉某个键，本页面的消费点就是死读，红在这里比红在线上早
  for (const key of ['today_requests', 'avg_latency_ms', 'p50_response_time_ms', 'miss_rate', 'total_commands_processed']) {
    it(`后端 monitoring.py 仍产出 ${key}`, () => {
      expect(api.includes(key), key).toBe(true)
    })
  }
})

describe('/stats 的 requests 段', () => {
  it('类型清单补齐了三个键（少一个就是整段被当裸对象丢在 ref 里没人读）', () => {
    expect(page).toMatch(/requests\?: \{[^}]*total_requests[^}]*today_requests[^}]*avg_latency_ms/)
  })

  it('模板真的把三个读数画出来', () => {
    expect(tpl).toContain('stats?.requests?.total_requests')
    expect(tpl).toContain('stats?.requests?.today_requests')
    expect(tpl).toContain('stats?.requests?.avg_latency_ms')
  })

  it('写明"进程快照"与访问日志窗口是两个源', () => {
    expect(tpl).toContain('缓冲平均延迟')
    expect(tpl).toContain('重启即空')
  })
})

describe('/performance/summary 的中位数', () => {
  it('PerfSummaryShape 补了 p50（只有 p95 的表把中位数整个丢了）', () => {
    expect(page).toMatch(/avg_response_time_ms\?: number\s+p50_response_time_ms\?: number/)
  })

  it('historyRows 两行都带 p50，模板也有对应列', () => {
    expect((page.match(/p50: (h|d)\?\.p50_response_time_ms/g) ?? []).length).toBe(2)
    expect(tpl).toContain('P50 {{ round2(row.p50) }} ms')
    expect(tpl).toContain('grid grid-cols-6')
  })
})

describe('/cache 的未命中率与累计命令数', () => {
  it('CacheShape 的 metrics 补齐两个键', () => {
    expect(page).toMatch(/miss_rate\?: number/)
    expect(page).toMatch(/total_commands_processed\?: number/)
  })

  it('模板各有一条 MetricCell 消费，且未命中率带百分号', () => {
    expect(tpl).toContain('cacheStats?.metrics?.miss_rate')
    expect(tpl).toContain('cacheStats?.metrics?.total_commands_processed')
    const missCell = tpl.slice(tpl.indexOf('未命中率'), tpl.indexOf('未命中率') + 160)
    expect(missCell).toContain('unit="%"')
  })

  it('Memory 后端的占位 0 说明仍在（新键同样不能当真读数）', () => {
    expect(tpl).toContain('以上为占位 0')
  })
})
