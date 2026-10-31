/**
 * /activity 的类型筛选 chip（批次 #222）。
 *
 * 动态页此前只有分页：`?type=` 后端早就支持（后台管理口在用），前台却把五种类型摊在
 * 一条时间线里，「只看碎碎念」这种最常见的读法要翻完整个列表。三条必须挡住的回归形态：
 *   ① 筛选状态只活在组件里：刷新 / 分享 / 后退会掉回「全部」，而越界 301 会把人踢到
 *      不带筛选的第一页（等于跳转把用户刚做的选择吃掉）。
 *   ② chip 枚举与后端 `ActivityType` Literal 漂移：新增类型漏补时，筛出来的动态全部
 *      落回「说说」图标（集合相等由 tests/test_activity_type_filter.py 跨语言对账，
 *      这里补图标与 i18n 两处必须同批跟着的部分）。
 *   ③ 切换筛选后停在旧页码：每种类型条数不同，第 3 页换筛选会落进对方不存在的页码，
 *      表现是「筛完变空白」。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const src = readFileSync(resolve(ROOT, 'pages/activity.vue'), 'utf-8').replace(/\r\n/g, '\n')
const LOCALES = ['zh', 'en', 'ja', 'zh_Hant'] as const
const localeOf = (code: string) =>
  JSON.parse(readFileSync(resolve(ROOT, `i18n/locales/${code}.json`), 'utf-8')) as Record<
    string,
    Record<string, unknown>
  >

const TYPES = ['say', 'article', 'update', 'notice', 'link'] as const

const queryWithBody = src.match(/const queryWith = [\s\S]*?\n\}/)?.[0] ?? ''
const setTypeBody = src.match(/const setType = \(next: ActivityType \| null\) => \{[\s\S]*?\n\}/)?.[0] ?? ''
const requestQuery = src.match(/query: computed\(\(\) => \(\{[\s\S]*?\}\)\)/)?.[0] ?? ''

describe('activity 类型筛选', () => {
  it('类型清单是单源常量，且图标 / 白名单判定都从它派生', () => {
    expect(src).toContain(`const ACTIVITY_TYPES = [${TYPES.map(v => `'${v}'`).join(', ')}] as const`)
    // 图标表必须为每一种类型备一个键：漏一个即「筛得出来但图标掉回说说」
    const iconsBlock = src.match(/const ICONS = \{[\s\S]*?\n\} as const/)?.[0] ?? ''
    for (const type of TYPES) {
      expect(iconsBlock, `ICONS 缺少 ${type} 图标`).toContain(`  ${type}: {`)
    }
    // 未知值一律回落 say，不再手写一串 if
    expect(src).toContain('const backendToIconKey = (type: string): string => (isActivityType(type) ? type : \'say\')')
    expect(src).toContain('const isActivityType = (value: unknown): value is ActivityType =>')
  })

  it('筛选与页码共用同一个 query 构造器，空值不写进地址栏', () => {
    expect(queryWithBody).toContain('if (type) q.type = type')
    expect(queryWithBody).toContain('if (page > 1) q.page = String(page)')
    // 请求侧始终带 page/page_size，筛选只在有值时发这个键（口径同 currentType 一条 ref）
    expect(requestQuery).toContain('page: currentPage.value')
    expect(requestQuery).toContain('page_size: PAGE_SIZE')
    expect(requestQuery).toContain('...(currentType.value ? { type: currentType.value } : {})')
    // 翻页锚点与页码一样带筛选，否则点下一页就掉回「全部」
    expect(src).toContain('const pageHref = (page: number) => hrefWith(queryWith(page, currentType.value))')
  })

  it('初始状态从地址栏读，非白名单值按「全部」处理（与后端归一口径一致）', () => {
    expect(src).toContain('const currentType = ref<ActivityType | null>(isActivityType(route.query.type) ? route.query.type : null)')
  })

  it('切换筛选回到第 1 页并 replace 地址栏', () => {
    expect(setTypeBody).toContain('currentType.value = next')
    expect(setTypeBody).toContain('currentPage.value = 1')
    expect(setTypeBody).toContain('router.replace({ query: queryWith(1, next) })')
    // 点当前已选中的 chip 不重发请求
    expect(setTypeBody).toContain('if (currentType.value === next) return')
  })

  it('翻页与「发完动态回顶」也保留当前筛选', () => {
    const handlePage = src.match(/const handlePageChange = \(page: number\) => \{[\s\S]*?\n\}/)?.[0] ?? ''
    expect(handlePage).toContain('router.replace({ query: queryWith(page, currentType.value) })')
    const publish = src.match(/async function publishActivity\(\) \{[\s\S]*?\n\}/)?.[0] ?? ''
    expect(publish).toContain('router.replace({ query: queryWith(1, currentType.value) })')
  })

  it('越界页码的 SSR 301 跳回「带当前筛选的第一页」，不是裸动态页', () => {
    expect(src).toContain('ssrEvent.node.res.setHeader(\'location\', hrefWith(queryWith(1, currentType.value)))')
  })

  it('chip 组是真实锚点：href 与分页共用 queryWith/hrefWith 单源，激活项用 aria-current', () => {
    expect(src).toContain('role="group"')
    expect(src).toContain(':aria-label="t(\'activity.filterLabel\')"')
    const start = src.indexOf('v-for="opt in typeOptions"')
    const chips = src.match(/v-for="opt in typeOptions"/g) ?? []
    expect(chips.length).toBe(1)
    const chipBlock = src.slice(start, src.indexOf('</a>', start))
    expect(chipBlock).toContain(':href="typeHref(opt.value)"')
    expect(chipBlock).toContain('@click.prevent="setType(opt.value)"')
    expect(chipBlock).toMatch(/:aria-current="currentType === opt\.value \? 'true' : undefined"/)
    // <Button role="radio"> 的旧形态：SSR HTML 里一个 ?type= 都读不到
    expect(chipBlock).not.toContain(':variant')
    expect(src).not.toContain('role="radio"')
    expect(src).toContain('const typeHref = (type: ActivityType | null) => hrefWith(queryWith(1, type))')
    // 选项来自同一个枚举（「全部」+ 五种类型），不是手写的第二个清单
    const options = src.match(/const typeOptions = computed\(\(\) => \[[\s\S]*?\n\]/)?.[0] ?? ''
    expect(options).toContain('String(t(\'activity.filterAll\'))')
    expect(options).toContain('...ACTIVITY_TYPES.map')
    expect(options).toContain('t(`activity.type_${value}`)')
  })

  it('四语都有筛选标签与五种类型名', () => {
    for (const code of LOCALES) {
      const activity = localeOf(code).activity ?? {}
      expect(activity.filterAll, `${code}.activity.filterAll 缺失`).toBeTruthy()
      expect(activity.filterLabel, `${code}.activity.filterLabel 缺失`).toBeTruthy()
      for (const type of TYPES) {
        expect(activity[`type_${type}`], `${code}.activity.type_${type} 缺失`).toBeTruthy()
      }
    }
  })

  it('后端公开口确实接受 type 并把判别位带进缓存键（chip 不是装饰）', () => {
    const api = readFileSync(resolve(ROOT, '..', 'backend', 'api', 'activity.py'), 'utf-8')
    expect(api).toContain('ACTIVITY_TYPE_FILTERS = frozenset(get_args(ActivityType))')
    expect(api).toContain('conditions.append(Activity.type == activity_type)')
    expect(api).toContain('f"t{activity_type or \'all\'}"')
  })
})
