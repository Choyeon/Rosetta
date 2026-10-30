/**
 * 文章目录锚点的「服务端直出」守卫。
 *
 * 历史缺陷：标题 id 只由 `extractTOC` 在 `onMounted` 之后补——服务端 HTML 里 `<h2>` 没有 id，
 * 于是①外部分享的 `#小节` 链接落空（浏览器在 JS 跑起来之前找不到锚点）②抓取器/禁 JS 读者
 * 读不到任何章节地址 ③窄屏根本没有目录（aside 是 `hidden lg:block`）。
 *
 * 现在 `lib/toc.ts::annotateHeadings` 在渲染字符串阶段就写 id，并与 `extractTOC` 共用
 * `slugifyHeading` —— 两边各写一份 slug 规则必然漂移，表现是 scroll-spy 高亮永远不亮。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { annotateHeadings, slugifyHeading } from '../../lib/toc'

const ROOT = resolve(__dirname, '../..')
const postPage = readFileSync(resolve(ROOT, 'pages/posts/[slug].vue'), 'utf8')
const readingUX = readFileSync(resolve(ROOT, 'composables/useReadingUX.ts'), 'utf8')

describe('annotateHeadings', () => {
  it('给 h1–h4 写 id 并产出同序目录项', () => {
    const { html, items } = annotateHeadings(
      '<h1>引言</h1><p>x</p><h2>快速上手</h2><h3>安装依赖</h3>'
    )
    expect(html).toContain('<h1 id="引言">引言</h1>')
    expect(html).toContain('<h2 id="快速上手">快速上手</h2>')
    expect(items.map(i => [i.level, i.id])).toEqual([[1, '引言'], [2, '快速上手'], [3, '安装依赖']])
  })

  it('同级同名标题按 -2/-3 去重（与 extractTOC 的编号规则一致）', () => {
    const { html, items } = annotateHeadings('<h2>A</h2><h2>A</h2><h2>A</h2>')
    expect(items.map(i => i.id)).toEqual(['a', 'a-2', 'a-3'])
    expect(html.match(/id="a(-[23])?"/g)).toEqual(['id="a"', 'id="a-2"', 'id="a-3"'])
  })

  it('标题内的内联标签与实体只影响目录文本，不影响结构', () => {
    const { html, items } = annotateHeadings('<h2>用 <code>pnpm</code> &amp; 构建</h2>')
    expect(items[0]?.text).toBe('用 pnpm & 构建')
    // 去掉 `&` 后的连续连字符被压平，锚点不会出现 `--`
    expect(html).toContain('id="用-pnpm-构建"')
    // 内联标签原样保留
    expect(html).toContain('<code>pnpm</code>')
  })

  it('超过 maxLevel 的标题仍拿 id（锚点可用）但不进目录', () => {
    const { html, items } = annotateHeadings('<h2>a</h2><h3>b</h3><h4>c</h4>', 2)
    expect(items.map(i => i.id)).toEqual(['a'])
    expect(html).toContain('<h3 id="b">')
    expect(html).toContain('<h4 id="c">')
  })

  it('已带 id 的标题保留原值，且参与后续去重', () => {
    const { html, items } = annotateHeadings('<h2 id="keep">Keep</h2><h2>keep</h2>')
    expect(html).toContain('<h2 id="keep">Keep</h2>')
    expect(items.map(i => i.id)).toEqual(['keep', 'keep-2'])
  })

  it('空标题退化为 section；空正文直接返回', () => {
    expect(annotateHeadings('<h2>!</h2>').items[0]?.id).toBe('section')
    expect(annotateHeadings('')).toEqual({ html: '', items: [] })
  })

  it('slugifyHeading 对空白与符号的处理是确定的', () => {
    const used = new Set<string>()
    expect(slugifyHeading('  Hello   World  ', used)).toBe('hello-world')
    expect(slugifyHeading('中文 标题！', used)).toBe('中文-标题')
    expect(slugifyHeading('!!!', used)).toBe('section')
  })
})

describe('文章页接线', () => {
  it('正文渲染走 annotateHeadings，且 toc_depth 与 extractTOC 同源', () => {
    expect(postPage).toContain('import { annotateHeadings, type TocHeading } from \'~~/lib/toc\'')
    expect(postPage).toContain('const renderedContent = computed(() => annotatedContent.value.html)')
    expect(postPage).toContain('annotateHeadings(')
    expect(postPage).toContain('site.reading.value.toc_depth')
  })

  it('目录清单 SSR 期可直出：tocList 回落到 ssrTocItems，两个目录都消费它', () => {
    expect(postPage).toContain('const ssrTocItems = computed(() => annotatedContent.value.items)')
    expect(postPage).toContain('tocItems.value.length ? tocItems.value : ssrTocItems.value')
    // 桌面aside 与窄屏 details 都必须读 tocList（读 tocItems 会让 SSR HTML 里没有目录）
    expect(postPage.match(/v-for="item in tocList"/g)?.length).toBe(2)
    expect(postPage).not.toContain('v-for="item in tocItems"')
  })

  it('目录项是真实锚点：href="#id" + JS 平滑滚动', () => {
    expect(postPage).toContain(':href="`#${item.id}`"')
    expect(postPage).toContain('@click.prevent="scrollTo(item.id)"')
  })

  it('窄屏目录存在且不是 lg-only', () => {
    expect(postPage).toContain('<details')
    expect(postPage).toContain('class="lg:hidden mt-10')
    expect(postPage).toContain('t(\'post.toc\', \'目录\')')
  })

  it('slug 规则单源：extractTOC 不再自带一份 slugify', () => {
    expect(readingUX).toContain('import { slugifyHeading } from \'~~/lib/toc\'')
    expect(readingUX).toContain('if (!h.id) h.id = slugifyHeading(')
    expect(readingUX).not.toMatch(/const slugify = /)
  })
})
