/**
 * 搜索占位符链路（管理端写口 → 公开读口 → 前台轮播）的接线守卫。
 *
 * 缺陷类：`SearchPlaceholder` 有读无写——公开口 `GET /api/search-placeholders` 与前台
 * `/posts` 搜索框轮播都在，但全仓没有任何写入点，运营者永远加不了一条文案。
 * 同一处还叠着一只隐性 500：读口声明 `response_model=list[str]` 却直出 JSON 列的 dict，
 * 一旦真有行就会因 dict→str 校验失败整口挂掉。所以两条必须一起钉：
 * 公开口按请求语言解析成字符串；后台口（/all）回完整 dict 供四语编辑器回填。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')
const backend = readFileSync(resolve(ROOT, '../backend/api/core.py'), 'utf8')
const page = readFileSync(resolve(ROOT, 'pages/admin/system/search-placeholders.vue'), 'utf8')
const api = readFileSync(resolve(ROOT, 'composables/useAdminManage.ts'), 'utf8')
const menu = readFileSync(resolve(ROOT, 'config/admin-menu.ts'), 'utf8')
const postsIndex = readFileSync(resolve(ROOT, 'pages/posts/index.vue'), 'utf8')

function section(source: string, start: string, end: string): string {
  const from = source.indexOf(start)
  expect(from, `找不到起点：${start}`).toBeGreaterThanOrEqual(0)
  const rest = source.slice(from)
  const to = rest.indexOf(end)
  expect(to, `找不到终点：${end}`).toBeGreaterThan(-1)
  return rest.slice(0, to)
}

describe('搜索占位符接线', () => {
  it('公开读口按请求语言解析，不再把 dict 直出 list[str]', () => {
    const handler = section(
      backend,
      'async def list_search_placeholders',
      'async def list_all_search_placeholders'
    )
    expect(handler).toContain('get_language_from_request(request, lang)')
    // 这一行是 500 面的解药：逐行解析后才拼成 list[str]
    expect(handler).toContain('get_i18n_value(row[0], language)')
  })

  it('后台口回完整 dict，且四条写路径都在', () => {
    expect(backend).toContain('"/search-placeholders/all"')
    expect(backend).toContain('SearchPlaceholderResponse.model_validate(row)')
    for (const marker of [
      'async def create_search_placeholder',
      'async def update_search_placeholder',
      'async def delete_search_placeholder'
    ]) {
      expect(backend).toContain(marker)
    }
    // 写路径必须清前台页面缓存：/posts 是 swr 300 且占位文案是 SSR 烘进去的
    expect(
      section(backend, 'async def create_search_placeholder', '@router.get(\n    "/config",')
    ).toContain('purge_frontend_page_cache("搜索占位符变更")')
  })

  it('管理页四条请求路径与后端声明逐字一致', () => {
    expect(api).toContain('apiFetch<Record<string, unknown>[]>(\'/search-placeholders/all\')')
    expect(api).toContain('apiFetch<Record<string, unknown>>(\'/search-placeholders\', {')
    expect(api).toContain('`/search-placeholders/${id}`, {')
    // 页面消费同一组 helper，不裸写 URL
    expect(page).toContain('fetchAdminSearchPlaceholders')
    expect(page).toContain('updateAdminSearchPlaceholder(item.id, { is_active: next })')
    // 四语 dict 直接提交，不做单语重组（重组会抹掉其余语言）
    expect(page).toContain('text: form.value.text')
    // 编辑必须回填启停与排序，否则一次普通保存就把停用行重新启用
    expect(page).toContain('is_active: item.is_active')
    expect(page).toContain('sort_order: item.sort_order')
  })

  it('侧栏注册了入口，前台仍走同一公开口', () => {
    expect(menu).toContain('{ path: \'/admin/system/search-placeholders\'')
    expect(postsIndex).toContain('useAPI<string[]>(\'/search-placeholders\'')
  })
})
