/**
 * 导航二级菜单（parent_id）的展开闭环（批次 #225）。
 *
 * 后台一直在写 `parent_id`，列表也打「二级菜单」徽标，但四个公开渲染面此前一律平铺——
 * 层级只存在于后台表格里，属于「有声明、无执行者」。这一族的守卫分两层：
 *
 *   纯函数层（折叠规则）：三种"父行取不到"的脏数据都必须把子项留在顶层而不是丢掉它——
 *     ① 父行不在同一批（跨位置 / 已停用 / 已删除）② 自指或成环 ③ 链超过渲染层数。
 *     父行本身因为 URL 重复被摘掉时子项上提：缺层级比缺入口可接受得多。
 *   接线层（渲染面）：每个面都遍历 flattenNavLinks(...) 的展开表，于是子项在 SSR HTML 里
 *     是真实 `<a>`（顶栏的下拉是 ClientOnly，只把子项放那儿等于后台一挂 parent_id
 *     就从爬虫内链图里少一条），且 `_blank` 必带 rel。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  flattenNavLinks,
  navRowsToLinks,
  withoutDuplicateTos,
  type NavApiRow,
  type NavLink
} from '~~/lib/navigation'

const ROOT = resolve(__dirname, '..', '..')

const read = (path: string) => readFileSync(resolve(ROOT, path), 'utf-8').replace(/\r\n/g, '\n')

/** 测试数据只用 label.zh（取文案）+ url（取地址）两个字段。 */
const labelOf = (row: NavApiRow): string => {
  const label = row.label
  return label && typeof label === 'object' ? (label.zh ?? '') : String(label ?? '')
}

const row = (
  id: number,
  zh: string,
  url: string,
  parent?: number | string | null,
  extra: Partial<NavApiRow> = {}
): NavApiRow => ({ id, label: { zh }, url, parent_id: parent ?? null, ...extra })

/** 展开表读起来是「深度:标签」序列——层级与顺序一起钉住。 */
const flat = (links: NavLink[]) => flattenNavLinks(links).map(item => `${item.depth}:${item.label}`)

/** 纯字符串出现次数（模板里的属性成对出现用这个数，比正则好读且不会被转义绊倒）。 */
const countNeedle = (src: string, needle: string) => src.split(needle).length - 1

const NAV_SURFACES = [
  'components/AppHeader.vue',
  'components/AppFooter.vue',
  'components/SiteNavSidebar.vue'
]

describe('导航二级菜单折叠（navRowsToLinks / flattenNavLinks）', () => {
  it('同批父行：子项并进 children，父在前子紧随', () => {
    const links = navRowsToLinks([row(1, '文章', '/posts'), row(2, '分类', '/categories', 1)], labelOf)
    expect(links.length).toBe(1)
    expect(links[0]?.children?.map(child => child.to)).toEqual(['/categories'])
    expect(flat(links)).toEqual(['0:文章', '1:分类'])
  })

  it('父行不在同一批（跨位置 / 停用 / 已删）→ 子项留在顶层，不丢链接', () => {
    expect(flat(navRowsToLinks([row(7, '留言板', '/guestbook', 999)], labelOf))).toEqual(['0:留言板'])
  })

  it('自指与成环不挂死：相关项一律留在顶层', () => {
    expect(flat(navRowsToLinks([row(1, '首页', '/', 1)], labelOf))).toEqual(['0:首页'])
    // a→b、b→a：两条都在本批里，上溯会无限循环，必须有预算并退回顶层
    expect(flat(navRowsToLinks([row(1, '甲', '/a', 2), row(2, '乙', '/b', 1)], labelOf)))
      .toEqual(['0:甲', '0:乙'])
  })

  it('三层链：第 3 层并进根的 children（少一层视觉层级，但一项不丢）', () => {
    const links = navRowsToLinks(
      [row(1, '根', '/a'), row(2, '子', '/b', 1), row(3, '孙', '/c', 2)],
      labelOf
    )
    expect(flat(links)).toEqual(['0:根', '1:子', '1:孙'])
  })

  it('父行本身是重复 URL 被摘掉 → 子项上提，不整支消失', () => {
    const links = navRowsToLinks(
      [row(1, '首页甲', '/'), row(2, '首页乙', '/', 3), row(3, '关于', '/about'), row(4, '子菜单', '/posts', 2)],
      labelOf
    )
    // id=2 与 id=1 同 URL，按"第一次出现"保留 → id=2 落不进树；
    // 它的子项 id=4 上溯时取不到父行 → 留在顶层可见。
    expect(flat(links)).toEqual(['0:首页甲', '0:关于', '0:子菜单'])
  })

  it('脏 parent_id（0 / null / 空串 / 非数字 / 负数）一律当"没有父级"', () => {
    for (const dirty of [0, null, '', 'abc', -1]) {
      const links = navRowsToLinks([row(1, '文章', '/posts'), row(2, '标签', '/tags', dirty)], labelOf)
      expect(flat(links), `parent_id=${JSON.stringify(dirty)}`).toEqual(['0:文章', '0:标签'])
    }
  })

  it('顶栏不吃外链，页脚/侧边栏按原样透传', () => {
    const rows = [row(1, '站内', '/posts'), row(2, '站外', 'https://example.com')]
    expect(flat(navRowsToLinks(rows, labelOf, { includeExternal: false }))).toEqual(['0:站内'])
    expect(navRowsToLinks(rows, labelOf).map(link => link.to)).toEqual(['/posts', 'https://example.com'])
  })

  it('target_blank 的两种写法都翻成 _blank，且不因新窗口设定被踢出导航', () => {
    const links = navRowsToLinks(
      [
        row(1, '站外', 'https://example.com', null, { target_blank: true }),
        row(2, '子项', '/posts', 1, { target: '_blank' })
      ],
      labelOf
    )
    expect(links[0]?.target).toBe('_blank')
    expect(links[0]?.children?.[0]?.target).toBe('_blank')
    expect(flat(links)).toEqual(['0:站外', '1:子项'])
  })

  it('withoutDuplicateTos：重复的父项摘掉后子项顶上来，且不落 children 空壳', () => {
    const links: NavLink[] = [
      { label: '关于', to: '/about', children: [{ label: '联系', to: '/contact' }] },
      { label: '孤立', to: '/solo' }
    ]
    const out = withoutDuplicateTos(links, new Set(['/about']))
    expect(out).toEqual([{ label: '联系', to: '/contact' }, { label: '孤立', to: '/solo' }])
    expect(out[1]?.children).toBeUndefined()
  })
})

describe('公开渲染面真的展开层级', () => {
  for (const file of NAV_SURFACES) {
    it(`${file} 遍历展开表并按 depth 缩进（只遍历一级会让子项消失）`, () => {
      const src = read(file)
      expect(src).toContain('flattenNavLinks(')
      expect(src, `${file} 没有按 depth 缩进`).toMatch(/depth > 0 \? 'pl-\d/)
    })

    it(`${file} 的 _blank 链接全部带 rel（tabnabbing）`, () => {
      const src = read(file)
      for (const v of ['item', 'link']) {
        const targets = countNeedle(src, `:target="${v}.target"`)
        const rels = countNeedle(src, `:rel="${v}.target === '_blank' ? 'noopener noreferrer' : undefined"`)
        expect(rels, `${file} 有 ${targets} 处 :target="${v}.target" 却只有 ${rels} 处配对 rel`).toBeGreaterThanOrEqual(targets)
      }
    })
  }

  it('顶栏的子项在 SSR 里是真实 <a>：溢出清单来自展开后的全集', () => {
    const header = read('components/AppHeader.vue')
    // 溢出项来自 flatNavItems（含子项），而不是 navItems.slice(N)（只剩一级）——
    // 后者在平铺档关掉时只存在于 ClientOnly 下拉，爬虫读不到那条内链。
    expect(header).toContain('const flatNavItems = computed(() => flattenNavLinks(navItems.value))')
    expect(header).toMatch(/const overflowNavItems = computed\(\(\) => \{[\s\S]*?flatNavItems\.value\.filter/)
    // 平铺闸门按展开后的条数算：子项也占顶栏宽度，按一级条数判会让溢出段静默超宽
    expect(header).toContain('flatNavItems.value.length <= NAV_FLAT_MAX')
    // 行 → 链接的构造收在 lib（含 includeExternal: false 的顶栏口径），不再自己写一遍
    expect(header).toContain('navRowsToLinks(')
    expect(header).not.toMatch(/const normalizeNavPath\s*=/)
  })

  it('顶栏 ENSURE_PRESENT 的「已存在」判定看得见子项（否则同屏两条同链接）', () => {
    const header = read('components/AppHeader.vue')
    expect(header).toContain('flattenNavLinks(base).map(item => item.to)')
    expect(header, '仍按只比一级的写法判存在').not.toMatch(/if \(base\.some\(x => x\.to === req\.to\)\) continue/)
  })

  it('后台契约注释不再声称"任何面都无法展开"', () => {
    const page = read('pages/admin/system/navigation.vue')
    expect(page).not.toContain('跨位置的父子关系在任何一个渲染面都无法展开')
    expect(page).toContain('parent_id 有真实执行者')
  })
})
