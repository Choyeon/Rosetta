/**
 * 顶栏导航折叠契约（静态源码断言）。
 *
 * 踩过的坑：默认主题把后台配的全部导航项（实测 10 条）平铺进固定 h-16 的一行，
 * flex 容器把每项压到内容宽度以下时，中文标签会在任意字符处断行——
 * "留言板"竖排成三行、整条顶栏错位（用户截图报的就是这个）。
 * 修复口径有三条，任何一条被改回去都会重新出问题，所以在这里钉住：
 *   1) 桌面导航与汉堡按钮共用同一个断点（两处必须一起改，否则中间带宽屏既无导航也无汉堡）；
 *   2) 溢出项收进「更多」下拉，条数上限按主题取，不允许回退成"默认主题全量平铺"；
 *   3) 导航项必须带 whitespace-nowrap + shrink-0（CJK 默认可逐字断行）。
 * 另：极简主题在 [data-layout-scope=frontend] 嵌套里给本导航写了 display:flex，
 * 编译后权重高于 Tailwind 的 .hidden，所以折叠用的 display 工具类必须带 ! 后缀（v4 语法）。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const src = readFileSync(resolve(__dirname, '..', '..', 'components/AppHeader.vue'), 'utf-8')

const NAV_OPEN_RE = /<nav\s+data-navbar="menu"[\s\S]*?>/

describe('AppHeader 顶栏导航折叠', () => {
  it('桌面导航与汉堡按钮同断点，且折叠用的 display 工具类带 important', () => {
    const open = src.match(NAV_OPEN_RE)
    expect(open, '顶栏必须有 data-navbar="menu" 的桌面导航').not.toBeNull()
    expect(open![0]).toMatch(/hidden!/)
    const bp = open![0].match(/(sm|md|lg|xl|2xl):flex!/)?.[1]
    expect(bp, '导航必须有一个"从某档起显示"的断点').toBeTruthy()
    const sheet = src.match(/class="(sm|md|lg|xl|2xl):hidden"\s*\n\s*:aria-label="t\('common\.titleMenu'\)/)?.[1]
    expect(sheet, '汉堡按钮的隐藏断点必须与导航显示断点一致').toBe(bp)
  })

  it('溢出项收进「更多」，不允许回退成默认主题全量平铺', () => {
    expect(src).toMatch(/const primaryNavItems = computed\(\(\) => navItems\.value\.slice\(0, NAV_PRIMARY_MAX\.value\)\)/)
    // 溢出清单取自**展开后的全集**（flatNavItems）：折叠后的一级切片只到 NAV_PRIMARY_MAX 为止，
    // 挂在一级项下面的二级项就会在 lg–2xl 之间没有任何入口（下拉是它们唯一的收纳口）。
    const overflowBlock = src.match(/const overflowNavItems = computed\(\(\) => \{[\s\S]*?\n\}\)/)?.[0] ?? ''
    expect(overflowBlock, '溢出清单没从展开表取，二级项会被顶栏切片吞掉').toContain('flatNavItems.value.filter')
    expect(overflowBlock, '常驻段的闸门还得跟着 NAV_PRIMARY_MAX').toContain('primaryNavItems.value.map(item => item.to)')
    expect(src).toMatch(/<ClientOnly v-if="overflowNavItems\.length > 0">\s*<DropdownMenu>/)
  })

  it('reka-ui 交互控件一律关在 ClientOnly 里，SSR 只吐占位注释', () => {
    // 踩过的坑：导航里的「更多」DropdownMenu 原先是裸写的，服务端渲染出 `<!---->`、
    // 客户端却要渲染触发器 button，于是整站每一页都报
    // 「Hydration node mismatch: rendered on server: #comment」。
    // 判定方式：把每个 ClientOnly 区间之外的 reka 根组件找出来，必须一个都不剩。
    const spans: Array<[number, number]> = []
    for (const m of src.matchAll(/<ClientOnly\b[^>]*>/g)) {
      const end = src.indexOf('</ClientOnly>', m.index!)
      spans.push([m.index!, end === -1 ? src.length : end])
    }
    const outside: string[] = []
    for (const m of src.matchAll(/<(DropdownMenu|Tooltip|Sheet|Popover)\b[^>]*>/g)) {
      const at = m.index!
      if (!spans.some(([s, e]) => at > s && at < e)) outside.push(m[0].slice(0, 50))
    }
    expect(outside, `这些 reka 根组件在 ClientOnly 外，会重新引入 hydration mismatch：${outside.join(' | ')}`).toEqual([])
  })

  it('桌面导航项一律禁止换行与压缩', () => {
    const start = src.search(NAV_OPEN_RE)
    const region = src.slice(start, src.indexOf('</nav>', start))
    const bindings = [...region.matchAll(/:class="\[\n\s*'([^']+)'/g)].map(m => m[1])
    expect(bindings.length, '常驻项 / 平铺档 / 「更多」触发器三处类绑定都要扫到').toBe(3)
    for (const cls of bindings) {
      expect(cls, `缺 whitespace-nowrap：${cls}`).toMatch(/whitespace-nowrap/)
      expect(cls, `缺 shrink-0：${cls}`).toMatch(/shrink-0/)
    }
  })
})
