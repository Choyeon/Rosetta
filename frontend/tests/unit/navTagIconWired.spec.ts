/**
 * 图标字段接通闭环（批次 #115）：导航菜单 `Navigation.icon` + 标签 `Tag.icon`。
 *
 * 两者是同一族缺陷的形状：后台表格能写、响应模型也回吐，但公开渲染面一个都不读——
 * 图标只活在后台里。守卫分两层：
 *
 *   纯函数层：`icon` 只在 `navRowsToLinks` 这个唯一构造点归一并挂到 NavLink 上，
 *     空串 / 纯空白 / null / 非字符串都当成「没有图标」（键整个不存在，渲染面不输出节点）；
 *     折叠进 children、去重上提、平铺展开三条路径都不许把它丢掉。
 *   接线层：每个渲染标签的导航位都必须配一个图标渲染器（数量相等，新增一处标签却漏挂
 *     图标就直接红）；每个 TagBadge 调用点都必须把行上的 icon 传下去。
 *
 * 另有一条安全红线：图标值来自后台自由文本，只能经 DynamicIcon 解析，
 * 任何渲染面都不许对它用 v-html。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  flattenNavLinks,
  navRowsToLinks,
  withoutDuplicateTos,
  type NavApiRow
} from '~~/lib/navigation'

const ROOT = resolve(__dirname, '..', '..')

const read = (path: string) => readFileSync(resolve(ROOT, path), 'utf-8').replace(/\r\n/g, '\n')

const labelOf = (row: NavApiRow): string => {
  const label = row.label
  return label && typeof label === 'object' ? (label.zh ?? '') : String(label ?? '')
}

const row = (id: number, zh: string, url: string, extra: Partial<NavApiRow> = {}): NavApiRow => ({
  id,
  label: { zh },
  url,
  ...extra
})

/** 纯字符串出现次数（模板里的属性成对出现用这个数，比正则好读且不会被转义绊倒）。 */
const countNeedle = (src: string, needle: string) => src.split(needle).length - 1

const NAV_SURFACES = [
  'components/AppHeader.vue',
  'components/AppFooter.vue',
  'components/SiteNavSidebar.vue'
]

describe('导航图标随链接下发（navRowsToLinks / nestNavRows / flattenNavLinks）', () => {
  it('有值时挂在链接上，无值时这个键根本不存在', () => {
    const links = navRowsToLinks(
      [row(1, '文章', '/posts', { icon: 'heroicons:book-open' }), row(2, '关于', '/about')],
      labelOf
    )
    expect(links[0]?.icon).toBe('heroicons:book-open')
    expect(links[1]).not.toHaveProperty('icon')
  })

  it('空串 / 纯空白 / null / 非字符串都判成「没有图标」', () => {
    const links = navRowsToLinks(
      [
        row(1, 'a', '/a', { icon: '' }),
        row(2, 'b', '/b', { icon: '   ' }),
        row(3, 'c', '/c', { icon: null }),
        row(4, 'd', '/d', { icon: 42 as unknown as string })
      ],
      labelOf
    )
    expect(links).toHaveLength(4)
    for (const link of links) expect(link).not.toHaveProperty('icon')
  })

  it('子项保留自己的图标，父项图标不会串到子上', () => {
    const links = navRowsToLinks(
      [
        row(1, '文章', '/posts', { icon: 'heroicons:book-open' }),
        row(2, '分类', '/categories', { icon: '📁', parent_id: 1 })
      ],
      labelOf
    )
    expect(links[0]?.icon).toBe('heroicons:book-open')
    expect(links[0]?.children?.[0]?.icon).toBe('📁')
  })

  it('平铺展开表带着图标（页脚 / 抽屉走的是展开表，不是嵌套结构）', () => {
    const links = navRowsToLinks(
      [
        row(1, '文章', '/posts', { icon: 'heroicons:book-open' }),
        row(2, '分类', '/categories', { icon: '📁', parent_id: 1 })
      ],
      labelOf
    )
    expect(flattenNavLinks(links).map(item => `${item.depth}:${item.label}:${item.icon ?? '-'}`))
      .toEqual(['0:文章:heroicons:book-open', '1:分类:📁'])
  })

  it('去重后仍在：留下的链接带图标，被摘掉的父项把带图标的子上提', () => {
    const links = navRowsToLinks(
      [
        row(1, '文章', '/posts', { icon: 'heroicons:book-open' }),
        row(2, '分类', '/categories', { icon: '📁', parent_id: 1 })
      ],
      labelOf
    )
    const kept = withoutDuplicateTos(links, new Set<string>())
    expect(kept[0]?.icon).toBe('heroicons:book-open')
    expect(kept[0]?.children?.[0]?.icon).toBe('📁')

    const lifted = withoutDuplicateTos(links, new Set(['/posts']))
    expect(lifted).toHaveLength(1)
    expect(lifted[0]?.label).toBe('分类')
    expect(lifted[0]?.icon).toBe('📁')
  })
})

describe('导航渲染面各自接上图标', () => {
  it.each(NAV_SURFACES)('%s 导入 DynamicIcon', (file) => {
    expect(read(file)).toContain('import DynamicIcon from')
  })

  /**
   * 「渲染标签的位置」与「渲染图标的位置」数量相等：
   * 只在一处挂图标、另两处漏掉，恰好是这批要挡的缺陷形态。
   */
  it.each(NAV_SURFACES)('%s 每个标签渲染位都有图标渲染器', (file) => {
    const src = read(file)
    const labels = countNeedle(src, '{{ item.label }}') + countNeedle(src, '{{ link.label }}')
    expect(labels).toBeGreaterThan(0)
    expect(countNeedle(src, '<DynamicIcon')).toBe(labels)
  })

  it('图标值只经 DynamicIcon，绝不 v-html', () => {
    // 图标是后台自由文本（heroicons 名 / emoji / 任意串）。页脚另有 v-html 绑到
    // 已消毒的自定义 HTML，那是另一件事，所以这里只钉「v-html 不得绑 icon」。
    for (const file of [...NAV_SURFACES, 'components/TagBadge.vue', 'components/DynamicIcon.vue']) {
      const binds = read(file).match(/v-html="[^"]*"/g) ?? []
      expect(binds.filter(b => b.includes('icon')), file).toEqual([])
    }
  })
})

describe('标签图标接上胶囊', () => {
  const badge = () => read('components/TagBadge.vue')

  it('TagBadge 声明并默认 icon prop', () => {
    const src = badge()
    expect(src).toContain('import DynamicIcon from')
    expect(src).toContain('icon?: string | null')
    expect(src).toContain('icon: null,')
  })

  it('两副壳（有 to / 无 to）都渲染图标，且图标顶掉左侧圆点', () => {
    const src = badge()
    // 有自定义图标 → DynamicIcon；没有才回落到内建 tag 字形（v-else-if）。
    expect(countNeedle(src, '<DynamicIcon')).toBe(2)
    expect(countNeedle(src, 'v-else-if="showIcon"')).toBe(2)
    expect(countNeedle(src, 'v-if="showDot && !icon"')).toBe(2)
  })

  /** 逐个 <TagBadge … /> 块断言，而不是数 `:icon=` 的出现次数：同文件里 CategoryBadge 也用它。 */
  it('每个 TagBadge 调用点都把行上的 icon 传下去', () => {
    const files = [
      'components/PostCard.vue',
      'pages/posts/[slug].vue',
      'pages/tags/index.vue',
      'pages/tags/[slug].vue'
    ]
    for (const file of files) {
      const blocks = read(file).match(/<TagBadge\b[\s\S]*?\/>/g) ?? []
      expect(blocks.length, file).toBeGreaterThan(0)
      for (const block of blocks) expect(block, `${file} 有个 TagBadge 没传 icon`).toContain(':icon=')
    }
  })

  it('卡片与详情页的标签投影带上 icon（调用点拿不到值等于没接）', () => {
    expect(read('components/PostCard.vue')).toContain('icon: t.icon ?? null')
    expect(read('pages/posts/[slug].vue')).toContain('icon: (tag.icon ?? null) as string | null')
    expect(read('pages/tags/[slug].vue')).toContain('const tagIcon = computed')
  })

  /**
   * 前台开始渲染这个值之后，"清掉图标"就成了新的公开面：PUT 是 exclude_unset 语义，
   * 省略键 = 不动它。所以包装函数必须区分 undefined 与 null，两个后台表单必须始终带键。
   * 同一条口径先落在 cover_image / parent_id 上（见 useAdminManage 的注释）。
   */
  it('后台清得掉图标（省略键与显式 null 是两回事）', () => {
    const wrapper = read('composables/useAdminManage.ts')
    expect(wrapper).toContain('if (payload.icon !== undefined) body.icon = payload.icon?.trim() || null')
    expect(wrapper).toContain('icon?: string | null')
    for (const file of ['pages/admin/content/tags.vue', 'pages/admin/content/categories.vue']) {
      expect(read(file), file).toContain('icon: form.icon || null,')
    }
  })
})
