/**
 * 审计日志「手动清理」的后台落地契约。
 *
 * 起因：`DELETE /api/admin/logs/retention` 早已实现（days 限 1-3650、返回真实 cutoff），
 * 前台却没有任何入口——管理员只能等服务端定时任务，等于"能删日志"这件事在界面上不存在。
 * 补 UI 时最容易写错的两侧都钉住：
 *   ① 档位越过 days 的 ge/le 会让请求静默 422；
 *   ② 这个端点只删 operation_logs，文案若写成"清理全部日志"就是在承诺它做不到的事
 *      （访问日志/性能指标由 LOG_RETENTION_DAYS 保留循环处理）。
 * 另一半：删除成功后必须重读列表，否则界面继续显示库里已经没有的行。
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const PAGE_REL = 'pages/admin/tools/audit-logs.vue'
const WRAPPER_REL = 'composables/useAdminManage.ts'
const BACKEND_REL = '../backend/api/admin_logs.py'

const page = readFileSync(resolve(process.cwd(), PAGE_REL), 'utf8')
const wrapper = readFileSync(resolve(process.cwd(), WRAPPER_REL), 'utf8')
const backend = readFileSync(resolve(process.cwd(), BACKEND_REL), 'utf8')

describe('审计日志清理 · 后台落地契约', () => {
  it('清理端点有真实调用，且 days 走查询参数', () => {
    expect(wrapper).toContain(`'/admin/logs/retention'`)
    expect(wrapper).toMatch(/method:\s*'DELETE'[\s\S]{0,80}query:\s*\{\s*days\s*\}/)
    // 失败由 DangerConfirmDialog 内联展示，wrapper 不能再 toast
    expect(wrapper).toMatch(/silentToast:\s*true/)
    expect(page).toContain('cleanupAdminAuditLogs(')
  })

  it('清理走危险确认弹窗，且必须输入确认短语', () => {
    expect(page).toMatch(/<DangerConfirmDialog[\s\S]*v-model:open="cleanupOpen"/)
    expect(page).toMatch(/confirm-phrase="清理日志"/)
    expect(page).toMatch(/:on-confirm="runCleanup"/)
  })

  it('前端档位落在后端 days 的 ge/le 区间内', () => {
    const bounds = backend.match(/days:\s*int\s*=\s*Query\([^)]*?ge=(\d+),\s*le=(\d+)/)
    expect(bounds, '后端应可解析出 ge/le').not.toBeNull()
    const ge = Number(bounds?.[1])
    const le = Number(bounds?.[2])
    const optionsRaw = page.match(/const cleanupDayOptions = \[([^\]]*)\]/)?.[1] ?? ''
    const options = optionsRaw.split(',').map(s => Number(s.trim().replace(/['"]/g, '')))
    expect(options.length, '档位不得为空').toBeGreaterThan(0)
    for (const d of options) {
      expect(d, `档位 ${d} 越界`).toBeGreaterThanOrEqual(ge)
      expect(d, `档位 ${d} 越界`).toBeLessThanOrEqual(le)
    }
  })

  it('文案如实说明只清操作日志，不越权承诺访问日志', () => {
    expect(page).toMatch(/删除 \$\{cleanupDays\.value\} 天之前的操作日志/)
    expect(page).toMatch(/访问日志与性能指标不在本接口范围内/)
  })

  it('清理成功后回到第 1 页并重读列表', () => {
    expect(page).toMatch(/async function runCleanup\(\)[\s\S]{0,600}page\.value = 1[\s\S]{0,60}await loadLogs\(\)/)
  })
})
