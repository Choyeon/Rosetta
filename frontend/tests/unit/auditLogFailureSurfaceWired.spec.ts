/**
 * 审计日志「失败操作面」读写两端接线的守卫。
 *
 * 此前的形状是**半接通**：`log_operation()` 会把 `status` / `error_code` / `request_path` /
 * `request_method` 四列写进 `operation_logs`，`GET /api/admin/logs` 的响应模型却不带这四个键，
 * 也没有状态过滤；导出口（`/admin/logs/export`）自己的 docstring 写着"按与列表接口相同的过滤条件"，
 * 实际少一个 `q`。前端包装层再丢一次，页面就永远只能看到"谁做了什么"，看不到"哪次没做成"——
 * 登录失败、账号锁定、接口 200 但库里没改这一类事故正好只靠这四列区分。
 *
 * 五条口径必须钉住：
 * * 后端两条口共用一套过滤（`_log_filters`）与一行形态（`_log_row`），字段名不得两边分叉。
 * * 状态候选与后端 `LOG_STATUSES` 逐值相等——后端对 `status` 做了 pattern 校验，传别的值 422。
 * * 包装层的归一化必须保留四列，且 params 类型收录 `status` / `q` / `resource_type`
 *   （页面曾用交集类型在外面补，等于把"包装层不转发"这个洞留在契约里）。
 * * 导出必须转发页面上的每一个筛选，提示语不得再声明"某条件不参与导出"。
 * * 页面必须真的消费这四列：失败徽标 + 错误码 + 展开区的请求方法/路径。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')
// 逐文件读源做静态断言时先归一换行：仓库里 .py 与 .vue 的换行不完全一致，
// 多行 marker 撞上 CRLF 会"找不到终点"而误判成接线丢失。
function readSource(path: string): string {
  return readFileSync(path, 'utf8').replace(/\r\n/g, '\n')
}
const api = readSource(resolve(ROOT, '../backend/api/advanced.py'))
const wrapper = readSource(resolve(ROOT, 'composables/useAdminManage.ts'))
const page = readSource(resolve(ROOT, 'pages/admin/tools/audit-logs.vue'))

function section(source: string, startMarker: string, endMarker: string): string {
  const start = source.indexOf(startMarker)
  expect(start, `源码里找不到起点：${startMarker}`).toBeGreaterThanOrEqual(0)
  const rest = source.slice(start)
  const end = rest.indexOf(endMarker)
  expect(end, `源码里找不到终点：${endMarker}（起点 ${startMarker}）`).toBeGreaterThan(-1)
  return rest.slice(0, end)
}

const FAIL_COLUMNS = ['status', 'error_code', 'request_method', 'request_path']

describe('审计日志失败操作面接线', () => {
  it('后端两条口共用同一套过滤条件与同一行构造', () => {
    const shared = section(api, 'def _log_filters(', 'def _log_row(')
    expect(shared).toContain('status_filter: str | None = None')
    expect(shared).toContain('OperationLog.status == status_filter')
    // 导出口此前漏掉的那一条：q 同时命中 detail / error_code / ip
    expect(shared).toContain('OperationLog.error_code.ilike(like)')
    expect(shared).toContain('OperationLog.ip_address.ilike(like)')
    expect(api.match(/_log_filters\(/g)?.length).toBeGreaterThanOrEqual(2)
    expect(api.match(/_log_row\(/g)?.length).toBeGreaterThanOrEqual(2)
  })

  it('后端行构造产出的四个失败列与响应模型一致', () => {
    const row = section(api, 'def _log_row(', '@router.get(\n    "/logs",')
    for (const col of FAIL_COLUMNS) {
      expect(row, `_log_row 未产出 ${col}`).toContain(`"${col}": log.${col}`)
    }
    const model = section(api, 'class OperationLogEntryOut(BaseModel)', 'class OperationLogListResponse')
    for (const col of FAIL_COLUMNS) {
      expect(model, `OperationLogEntryOut 未声明 ${col}`).toContain(`    ${col}:`)
    }
  })

  it('页面状态候选与后端 LOG_STATUSES 逐值相等', () => {
    const declared = api.match(/LOG_STATUSES = \(([^)]*)\)/)
    expect(declared, '后端缺少 LOG_STATUSES 常量').not.toBeNull()
    const backendValues = (declared?.[1] ?? '')
      .split(',')
      .map(s => s.trim().replace(/^["']|["']$/g, ''))
      .filter(Boolean)
    expect(backendValues).toEqual(['success', 'failed'])
    const options = section(page, 'const statusOptions = [', ']\n\nfunction actionLabel')
    for (const value of backendValues) {
      expect(options, `页面缺 status=${value} 选项`).toContain(`value: '${value}'`)
    }
  })

  it('包装层保留四列，且 params 收录后端全部查询参数', () => {
    const iface = section(wrapper, 'export interface AdminAuditLog {', '\n}\n')
    for (const col of FAIL_COLUMNS) {
      expect(iface, `AdminAuditLog 未声明 ${col}`).toContain(`  ${col}?:`)
    }
    const fetcher = section(wrapper, 'export function fetchAdminAuditLogs(', '// ==================== 回收站')
    for (const key of ['status', 'q', 'resource_type']) {
      expect(fetcher, `fetchAdminAuditLogs 形参未收录 ${key}`).toContain(`${key}?: string`)
    }
    for (const col of FAIL_COLUMNS) {
      expect(fetcher, `归一化丢弃 ${col}`).toContain(`${col}: (raw.${col} ?? null)`)
    }
    // 交集类型补齐的洞已经封住：页面不该再用 `& { q?: string` 这类外挂
    expect(page).not.toContain('& { q?: string')
  })

  it('导出转发页面全部筛选，且不再声明"某条件不参与导出"', () => {
    const exporter = section(wrapper, 'export function exportAdminAuditLogs(', '/** 落成浏览器下载')
    expect(exporter).toContain('status?: string')
    expect(exporter).toContain('q?: string')
    expect(exporter).toContain('resourceType?: string')
    for (const key of ['status', 'q', 'resource_type']) {
      expect(exporter, `导出未转发 ${key}`).toContain(`{ ${key}: filters.`)
    }
    const exportCall = section(page, 'const blob = await exportAdminAuditLogs(', 'downloadBlob(blob')
    expect(exportCall).toContain('status: filters.status')
    expect(exportCall).toContain('q: filters.keyword.trim()')
    expect(exportCall).toContain('resourceType: filters.resourceType.trim()')
    // 头部注释允许解释"过去说过导出不含某条件"，函数体里不能再有这句免责文案
    expect(section(page, 'async function handleExport(', '\n}\n')).not.toContain('不参与')
  })

  it('页面渲染失败徽标、错误码与展开区的请求方法/路径', () => {
    expect(page).toContain('v-model="filters.status"')
    expect(page).toContain('v-if="log.status === ')
    expect(page).toContain('v-if="log.error_code"')
    expect(page).toContain('{{ log.request_method ??')
    expect(page).toContain('{{ log.request_path ??')
    // 状态进了"当前筛选"摘要，也必须在重置里清掉
    expect(page).toContain('状态：')
    expect(section(page, 'function resetFilters() {', '\n}\n')).toContain('filters.status =')
  })
})
