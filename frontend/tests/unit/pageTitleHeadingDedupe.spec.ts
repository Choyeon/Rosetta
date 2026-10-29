/**
 * 独立页正文首行 H1 与模板标题去重。
 *
 * 实测（生产站，2026-10-30）：`/page/about` 的 SSR HTML 里 `<h1` 计数为 2 —— 模板渲染页面标题
 * 一个，正文 Markdown 首行 `# 关于` 又转换出一个。文章详情页早就有这条规则，独立页两条口
 * （顶级 catchall `pages/[slug].vue` 与兼容路由 `pages/page/[slug].vue`）都没有，
 * 于是同一份正文在两种路由下标题层级不一致。
 *
 * 一半是纯函数行为，一半是静态接线守卫（漏接一页就红）。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { stripDuplicateTitleHeading } from '../../lib/markdown'

const ROOT = resolve(__dirname, '..', '..')
const read = (rel: string) => readFileSync(resolve(ROOT, rel), 'utf-8')

describe('stripDuplicateTitleHeading', () => {
  it('首行 H1 与标题完全相同 → 剥掉该行', () => {
    const out = stripDuplicateTitleHeading('# 关于\n\n正文第一段', '关于')
    expect(out).toBe('正文第一段')
  })

  it('首行 H1 包含标题（迁移时常带后缀）→ 剥掉', () => {
    const out = stripDuplicateTitleHeading('# 关于 · 本站\n\n正文', '关于')
    expect(out).toBe('正文')
  })

  it('标题包含首行 H1（正文用了更短的写法）→ 剥掉', () => {
    const out = stripDuplicateTitleHeading('# 隐私\n\n正文', '隐私政策与数据说明')
    expect(out).toBe('正文')
  })

  it('首行 H1 与标题无关 → 原样保留（正文里真的一级标题不能被吃掉）', () => {
    const src = '# 别的章节\n\n正文'
    expect(stripDuplicateTitleHeading(src, '关于')).toBe(src)
  })

  it('首行是二级标题 → 不动', () => {
    const src = '## 小节\n\n正文'
    expect(stripDuplicateTitleHeading(src, '小节')).toBe(src)
  })

  it('标题为空（加载中 / 404 态）→ 不剥，避免把正文第一行扔掉', () => {
    const src = '# 关于\n\n正文'
    expect(stripDuplicateTitleHeading(src, '')).toBe(src)
    expect(stripDuplicateTitleHeading(src, null)).toBe(src)
  })

  it('文件只有一行 H1（无换行结尾）→ 剥成空串', () => {
    expect(stripDuplicateTitleHeading('# 关于', '关于')).toBe('')
  })

  it('闭合 # 与缩进同样识别', () => {
    expect(stripDuplicateTitleHeading('  # 关于 ##\n正文', '关于')).toBe('正文')
  })
})

describe('三个渲染口都接上同一条去重规则', () => {
  const PAGES = ['pages/[slug].vue', 'pages/page/[slug].vue', 'pages/posts/[slug].vue']

  it.each(PAGES)('%s 从 lib/markdown 引入并使用', (rel) => {
    const src = read(rel)
    expect(src, `${rel} 没有引入 stripDuplicateTitleHeading`).toMatch(
      /import \{ stripDuplicateTitleHeading \} from '~~\/lib\/markdown'/
    )
    expect(src, `${rel} 引入了但没在渲染路径调用`).toMatch(/stripDuplicateTitleHeading\(/)
  })

  it.each(['pages/[slug].vue', 'pages/page/[slug].vue'])(
    '%s 把去重结果喂给 marked.parse（不是原始正文）',
    (rel) => {
      const src = read(rel)
      expect(src, `${rel} 仍然直接把原始正文交给 md.parse`).not.toMatch(
        /md\.parse\(\s*rawContent\s*\)/
      )
      expect(src).toMatch(/md\.parse\(\s*body\s*\)/)
    }
  )

  it('页面里不再各自维护一份正则（单源）', () => {
    for (const rel of PAGES) {
      expect(read(rel), `${rel} 仍内联了一份首行 H1 正则`).not.toMatch(
        /\/\^\\s\{0,3\}#\\s\+/
      )
    }
  })
})
