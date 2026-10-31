/**
 * 导航菜单位置（location）的读写闭环（批次 #224）。
 *
 * 后端很早就有 location：模型列、写入侧 pattern、公开口与管理口的筛选、按位置分键的缓存。
 * 但前台只有一个消费方（顶栏），后台也没有任何写入口——于是：
 *   ① 顶栏不带筛选地读全量，一旦有行落到 footer/sidebar（导入工具、旧数据、手写库），
 *      同一个链接就在顶栏出现多次；
 *   ② 后台把「页脚/侧边栏」两档做成没人渲染的死档位，存进去的项静默消失。
 * 这一族的守卫按四条口径钉：
 *   ① UI 档位清单 ⇔ 后端 schema pattern 的值集合**相等**（多一个是死档位，少一个后端能力没接）；
 *   ② 每个档位都必须有一个真实的前台消费方，且各带自己的 useAPI 缓存键
 *      （判别位进了 WHERE 就得进键，共键的那一档会在 TTL 内读到别档的行）；
 *   ③ URL 归一化与去重只有一个来源（lib/navigation.ts），三个消费方各自复制必漂移；
 *   ④ 后台的筛选与表单要真的把参数流进请求，只在 ref 里存着等于什么都没接。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const REPO = resolve(ROOT, '..')

const read = (path: string) => readFileSync(resolve(path), 'utf-8').replace(/\r\n/g, '\n')

const SCHEMAS = read(resolve(REPO, 'backend/schemas/__init__.py'))
const CORE_API = read(resolve(REPO, 'backend/api/core.py'))
const WRAPPER = read(resolve(ROOT, 'composables/useAdminManage.ts'))
const LIB = read(resolve(ROOT, 'lib/navigation.ts'))
const PAGE = read(resolve(ROOT, 'pages/admin/system/navigation.vue'))

/** 档位 → 前台消费方文件（唯一清单：每档恰好一个渲染面） */
const CONSUMERS: Record<string, string> = {
  header: 'components/AppHeader.vue',
  footer: 'components/AppFooter.vue',
  sidebar: 'components/SiteNavSidebar.vue'
}

/** 后台 UI 的档位清单（ADMIN_NAV_LOCATIONS 的字面量）。 */
const uiLocations = (): string[] => {
  const literal = WRAPPER.match(/export const ADMIN_NAV_LOCATIONS = \[([^\]]*)\] as const/)?.[1] ?? ''
  return [...literal.matchAll(/'([^']+)'/g)].map(m => m[1] as string)
}

/** 后端写入侧 pattern 里的档位（NavigationBase 与 NavigationUpdate 各一条，必须一致）。 */
const backendLocations = (): string[][] => {
  const blocks = [...SCHEMAS.matchAll(/class Navigation(?:Base|Update)\b[\s\S]*?\n\nclass /g)]
    .map(m => m[0])
  const found = blocks.map((block) => {
    const pattern = block.match(/location: str \| None = Field\(.*?pattern="\^\(([^)]*)\)\$"/)?.[1]
      ?? block.match(/location: str = Field\(.*?pattern="\^\(([^)]*)\)\$"/)?.[1]
      ?? ''
    return pattern.split('|').filter(Boolean)
  })
  return found
}

describe('导航菜单位置（location）', () => {
  it('后端两条 pattern 都解析出来了，且与 UI 档位清单集合相等', () => {
    const blocks = backendLocations()
    expect(blocks.length, 'NavigationBase / NavigationUpdate 的 location pattern 没解析出来').toBe(2)
    for (const patternValues of blocks) {
      expect(patternValues.length).toBeGreaterThan(0)
      expect(patternValues.slice().sort()).toEqual(uiLocations().slice().sort())
    }
  })

  it('每个档位都有中文名，且档位集合与前台消费方集合相等', () => {
    const labels = WRAPPER.match(/export const NAV_LOCATION_LABELS: Record<AdminNavLocation, string> = \{([\s\S]*?)\n\}/)?.[1] ?? ''
    for (const loc of uiLocations()) {
      expect(labels, `NAV_LOCATION_LABELS 缺少 ${loc}`).toContain(`${loc}: `)
    }
    expect(Object.keys(CONSUMERS).slice().sort()).toEqual(uiLocations().slice().sort())
  })

  it('三个消费方各读自己那一档，并且各自带一条位置化的缓存键', () => {
    for (const [loc, relPath] of Object.entries(CONSUMERS)) {
      const src = read(resolve(ROOT, relPath))
      const call = src.match(/useAPI<NavApiRow\[\]>\('\/navigations', \{[\s\S]*?\n\}\)/)?.[0] ?? ''
      expect(call, `${relPath} 找不到读 /navigations 的 useAPI`).not.toBe('')
      expect(call, `${relPath} 没有将 location=${loc} 写进请求`).toContain(`query: { location: '${loc}' },`)
      // 判别位进了 SQL WHERE 就必须进缓存键：共键会让其中一档在 TTL 内读到别档的行
      expect(call, `${relPath} 的缓存键没带位置`).toContain(`public:navigations:${loc}:`)
      // 只允许这一条读口：第二条不带筛选的 /navigations 会把三档行混回一个列表
      expect([...src.matchAll(/'\/navigations'/g)].length, `${relPath} 读了多次 /navigations`).toBe(1)
    }
  })

  it('侧边栏那一档自带 server: false（ClientOnly 里的 default 会让请求永不发出）', () => {
    // 线上实测：抽屉打开后 sidebar 一节永久为空，CDP 网络面板里根本没有这条请求，
    // 而同一 URL 手工 fetch 正常返回行。原因是 SiteNavSidebar 挂在 <ClientOnly> 内，
    // hydration 期 Nuxt 命中 `fetchOnServer && isHydrating && data.value !== void 0`
    // 这一支——`default: () => []` 已经把 data 填成空数组，于是状态直接标成 success、
    // handler 一次都不跑。只有 `server: false` 能让它走到 initialFetch()。
    // 分类那一节是巧合存活：它与 AppFooter 共用 blog:categories 键，SSR 已把该键填好。
    const sidebar = read(resolve(ROOT, 'components/SiteNavSidebar.vue'))
    const call = sidebar.match(/useAPI<NavApiRow\[\]>\('\/navigations', \{[\s\S]*?\n\}\)/)?.[0] ?? ''
    expect(call, '找不到侧边栏读 /navigations 的 useAPI').not.toBe('')
    expect(call, '侧边栏的 sidebar 档读口必须 server: false').toContain('server: false')
  })

  it('页脚与侧边栏在两套骨架里都渲染（少一副就是换主题后菜单项消失）', () => {
    // 遍历的是 flattenNavLinks(...)：二级项必须和父项一起进同一批循环，
    // 否则"只渲染一级"会让挂在 parent_id 下的那一条在这两面彻底消失。
    const footer = read(resolve(ROOT, 'components/AppFooter.vue'))
    expect([...footer.matchAll(/v-for="link in flattenNavLinks\(footerNavLinks\)"/g)].length).toBeGreaterThanOrEqual(2)
    const sidebar = read(resolve(ROOT, 'components/SiteNavSidebar.vue'))
    expect(sidebar).toContain('v-for="link in flattenNavLinks(sidebarNavLinks)"')
  })

  it('URL 归一化与去重只有一个来源，消费方不得各写一份', () => {
    expect(LIB).toContain('export function normalizeNavRowUrl(')
    expect(LIB).toContain('export function dedupeByTo<')
    expect(LIB).toContain('export function navRowsToLinks(')
    for (const relPath of Object.values(CONSUMERS)) {
      const src = read(resolve(ROOT, relPath))
      expect(src, `${relPath} 自己重写了一份归一化`).not.toMatch(/const normalizeNavPath\s*=/)
      expect(src, `${relPath} 自己重写了一份去重`).not.toMatch(/const dedupeByTo\s*=/)
    }
  })

  it('封装层把位置带进请求，并把脏值归到有人渲染的那一档', () => {
    const fetcher = WRAPPER.match(/export async function fetchAdminNavigations\([\s\S]*?\n\}/)?.[0] ?? ''
    expect(fetcher).toContain('location?: AdminNavLocation')
    expect(fetcher).toContain('location ? { query: { location } } : undefined')
    // 旧数据/导入工具喂进无法识别的位置时，落回 header（有人渲染）而不是落进死档位
    expect(fetcher).toContain('isAdminNavLocation(x.location) ? x.location : \'header\'')
    expect(WRAPPER).toContain('location: AdminNavLocation')
    expect(WRAPPER).toContain('is_active: boolean')
  })

  it('后台页有位置筛选器，且筛选值真的流进请求', () => {
    expect(PAGE).toContain('const locationFilter = ref<AdminNavLocation | \'all\'>')
    expect(PAGE).toContain('<Select v-model="locationFilter">')
    expect(PAGE).toContain('watch(locationFilter, loadAll)')
    const loadAll = PAGE.match(/async function loadAll\(\) \{[\s\S]*?\n\}/)?.[0] ?? ''
    expect(loadAll).toContain('locationFilter.value === \'all\' ? undefined : locationFilter.value')
  })

  it('表单能写位置与显隐，且父级只认同一档', () => {
    expect(PAGE).toContain('<Select v-model="form.location">')
    expect(PAGE).toContain('v-model="form.is_active"')
    const payload = PAGE.match(/const payload = \{[\s\S]*?\n {2}\}/)?.[0] ?? ''
    expect(payload).toContain('location: form.value.location')
    expect(payload).toContain('is_active: form.value.is_active')
    const parents = PAGE.match(/const parentOptions = computed\(\(\) =>[\s\S]*?\n\)/)?.[0] ?? ''
    expect(parents).toContain('i.location === form.value.location')
    // 换位置后旧父级已不在候选里，不清掉会把「父级在别的位置」的关系留在库里
    expect(PAGE).toContain('watch(() => form.value.location')
  })

  it('停用项在列表里有可见标记（后台看不到状态就是假开关）', () => {
    expect(PAGE).toContain('v-if="!item.is_active"')
    expect(PAGE).toContain('已停用')
  })

  it('后端两个读口都接 location 参数，公开口的缓存键也带位置', () => {
    const publicList = CORE_API.match(/async def list_navigations\([\s\S]*?\n {4}return response/)?.[0] ?? ''
    expect(publicList).toContain('location: str | None = Query(')
    expect(publicList).toContain('query.where(Navigation.location == location)')
    expect(publicList).toContain('make_cache_key("navigations", location or "all")')
    // 公开口只回激活项，管理口回全量（后台要能把停用项重新打开）
    expect(publicList).toContain('Navigation.is_active.is_(True)')
    const adminList = CORE_API.match(/async def admin_list_navigations\([\s\S]*?\n {4}return result\.scalars\(\)\.all\(\)/)?.[0] ?? ''
    expect(adminList).toContain('location: str | None = Query(')
    expect(adminList).toContain('query.where(Navigation.location == location)')
    expect(adminList).not.toContain('is_active')
  })
})
