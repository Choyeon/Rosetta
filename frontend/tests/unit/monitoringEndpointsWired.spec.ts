/**
 * `/api/monitoring/*` 八个只读端点必须有前端消费方（批次 #94 之前是八条全部零消费者：
 * 后端一直在算指标，后台一个都看不到）。守卫按"后端声明的清单 ⇔ 页面实际请求的清单"**集合相等**
 * 做双向对账，所以新增一条端点不接线会红、页面调用一条不存在的端点也会红。
 *
 * 另三条口径是这个接口族特有的坑，页面改坏任意一条都会静默出假读数：
 * * `/database` 的 `database_url` 是掩码连接串，但掩码不等于可公开，不得上屏；
 * * `/performance` 的环形缓冲无样本时**不回 `sample_count` 键**，必须按键存在性区分"没样本"与"0ms"；
 * * `visit_logs` 受 `LOG_RETENTION_DAYS` 清理，`retention_days < 窗口天数` 时读数只是下界，
 *   必须同时用 `retention_days` 与 `data_since` 标注。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')
const page = readFileSync(resolve(ROOT, 'pages/admin/tools/monitoring.vue'), 'utf8')
const backend = readFileSync(resolve(ROOT, '../backend/api/monitoring.py'), 'utf8')
const menu = readFileSync(resolve(ROOT, 'config/admin-menu.ts'), 'utf8')

/** 后端 `@router.get("/x")` 声明的全部路径（monitoring 只有 GET，全为只读）。 */
function declaredPaths(): string[] {
  const out: string[] = []
  const re = /@router\.get\(\s*"([^"]+)"/g
  let m: RegExpExecArray | null
  while ((m = re.exec(backend)) !== null) out.push(m[1]!.replace(/^\//, ''))
  return out
}

/** 页面 `section('/monitoring/xxx?query')` 实际请求的路径（查询串不参与对账）。 */
function requestedPaths(): string[] {
  const out: string[] = []
  // 实参类型不能漏：`section<LatencyShape>(...)` 也要被算成一次接线，
  // 否则页面只要加上泛型（typecheck 要求的）就会误报"端点没消费"。
  const re = /section(?:<[^>]+>)?\(\s*[`'"]([^`'"]+)[`'"]/g
  let m: RegExpExecArray | null
  while ((m = re.exec(page)) !== null) {
    out.push(m[1]!.split('?')[0]!.replace('/monitoring/', ''))
  }
  return [...new Set(out)]
}

describe('monitoring 端点必须全部接线', () => {
  it('后端声明的清单非空且含八条', () => {
    expect(declaredPaths()).toHaveLength(8)
  })

  it('页面请求集与后端声明集精确相等', () => {
    expect([...requestedPaths()].sort()).toEqual([...declaredPaths()].sort())
  })

  it('两个性能窗口分别取数（缓冲 ≠ 历史日志）', () => {
    expect(page).toContain('/monitoring/performance?period=')
    expect(page).toContain('/monitoring/performance/summary')
    expect(page).toMatch(/环形缓冲/)
    expect(page).toMatch(/跨重启|访问日志/)
  })
})

describe('监控页的三条读数口径', () => {
  it('掩码连接串不得渲染上屏（只查模板区，文件头注释可以提它）', () => {
    const template = page.slice(page.indexOf('<template>'), page.indexOf('<script setup'))
    expect(template).not.toContain('database_url')
    expect(template).toMatch(/掩码/)
  })

  it('环形缓冲无样本用键存在性判定，不把"没样本"读成 0ms', () => {
    expect(page).toContain('sample_count === undefined')
  })

  it('保留窗口截短时标注为下界并给出数据起点', () => {
    expect(page).toContain('retention_days')
    expect(page).toContain('data_since')
    expect(page).toMatch(/下界/)
  })

  it('单段取数失败只影响本段，整页不清空', () => {
    expect(page).toContain('silentToast: true')
    expect(page).toContain('Promise.all')
  })
})

describe('监控页的注册与渲染口径', () => {
  it('后台菜单有入口，且与页面路径一致', () => {
    expect(menu).toContain('\'/admin/tools/monitoring\'')
  })

  it('后台页保持 ssr:false + admin 布局', () => {
    expect(page).toMatch(/definePageMeta\(\{\s*ssr:\s*false,\s*layout:\s*'admin'\s*\}\)/)
  })

  it('30s 静默轮询必须在卸载时清理计时器', () => {
    expect(page).toMatch(/POLL_MS\s*=\s*30_000/)
    expect(page).toMatch(/onUnmounted\(\(\)\s*=>\s*\{[\s\S]*clearInterval\(timer\)/)
  })
})
