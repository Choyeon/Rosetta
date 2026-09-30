/**
 * 自定义 class 的 CSS 定义守卫。
 *
 * 起因（真实事故）：components/ui/skeleton/Skeleton.vue 从第一版起就在根节点写
 * `skeleton-shimmer`，但全仓 CSS 从来没有定义过这个类 —— 共享骨架组件等于一个
 * 普通空 div，所有 <Skeleton> 都是静止灰块、没有任何加载动效。因为没有测试守着，
 * 谁也没发现；各页面为了让骨架动起来只好各自手写 animate-pulse，口径越走越散。
 *
 * 这类缺陷的共性：Vue 模板里的 class 是字符串，拼错/漏定义不会报错、不会报警告，
 * 只会静默没有样式。因此这里用静态扫描把「组件里用到的自定义 class」与
 * 「CSS 里实际定义的类」对起来。
 *
 * 扫描面刻意收窄到 components/ui/** 内的核心视觉原子件（它们是全站共用、
 * 单个类名失效影响面最大），并且只校验**带下划线前缀、明显是项目自定义**的类名
 * —— Tailwind 工具类天然不出现在 CSS 源文件里，扫它们必然假红。
 */
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve } from 'node:path'

const CSS_FILES = [
  'assets/css/main.css'
]

/** 组件里不能被 Tailwind 生成、必须由本仓 CSS 兜底自定义的 class 名（手工登记 → 有意为之） */
const WATCHED_CLASSES: Array<{ name: string, owner: string }> = [
  { name: 'skeleton-shimmer', owner: 'components/ui/skeleton/Skeleton.vue' },
  { name: 'card-surface', owner: 'components/ui/card/Card.vue' },
  { name: 'chip', owner: 'components/ui/badge' }
]

function readCss(): string {
  return CSS_FILES
    .map(f => readFileSync(resolve(process.cwd(), f), 'utf8'))
    .join('\n')
}

function walk(dir: string, out: string[] = []): string[] {
  const abs = resolve(process.cwd(), dir)
  let entries: string[]
  try {
    entries = readdirSync(abs)
  } catch {
    return out
  }
  for (const name of entries) {
    const full = `${dir}/${name}`
    if (statSync(resolve(process.cwd(), full)).isDirectory()) walk(full, out)
    else if (full.endsWith('.vue') || full.endsWith('.ts')) out.push(full)
  }
  return out
}

describe('自定义 class 必须在本仓 CSS 里有定义', () => {
  const css = readCss()

  it('扫描的 CSS 文件都存在（防路径漂移导致全绿假象）', () => {
    expect(CSS_FILES.length).toBeGreaterThan(0)
    expect(css.length).toBeGreaterThan(1000)
  })

  it.each(WATCHED_CLASSES)('.$name 必须在 %s 中定义（消费方：$owner）', ({ name }) => {
    // `.classname` 出现在选择器位置的任意一个 CSS 源里即可
    const defined = new RegExp(`\\.${name}\\b`).test(css)
    expect(defined, `缺少 .${name} 的 CSS 定义 —— 该 class 会让组件静默失去样式`).toBe(true)
  })

  it('骨架组件的 shimmer 类名不得漂移（改名必须同步改 CSS 与本守卫）', () => {
    const skeleton = readFileSync(
      resolve(process.cwd(), 'components/ui/skeleton/Skeleton.vue'),
      'utf8'
    )
    expect(skeleton).toContain('skeleton-shimmer')
  })

  it('共享骨架组件真的被用到（否则上面几条断言失去意义）', () => {
    const consumers = walk('components')
      .concat(walk('pages'))
      .filter(f => /<Skeleton\b/.test(readFileSync(resolve(process.cwd(), f), 'utf8')))
    expect(consumers.length, '至少应有若干页面使用 <Skeleton>').toBeGreaterThan(0)
  })
})

/**
 * 后台「页面卡片」面层统一守卫。
 *
 * 卡片观感的唯一真源是 `.card-surface`：中性基座在 main.css，admin 的装饰层
 * （渐变玻璃面 / 内发光 / 彗星描边）冻结在 admin-ui.css 按 data-layout-scope 隔离。
 * 但历史上很多后台页面是手写 `rounded-xl border bg-card` 复制出来的，
 * 于是同一个后台里同时存在「有装饰的卡片」和「素面描边盒子」，且改主题时只有前者会跟着变。
 *
 * 这里只禁**面板级**的手写面层。以下几类刻意放行，但**必须在 offending 行上写明理由**
 * （`panel-exempt: <原因>`，可以是 HTML 注释也可以是 JS 行尾注释）：
 *   1. 分段筛选器（`inline-flex ... p-1 bg-card`）—— 是控件不是内容面板；
 *   2. 网格里的瓦片项（KPI 卡、快捷入口、媒体缩略图、主题卡及其加载骨架）——
 *      渐变玻璃面铺到几十个格子上只剩噪点，且要与它替换的真实项同口径，否则加载完成跳变；
 *   3. 绝对定位浮层（下拉/弹出面板）；
 *   4. 已经处在某个 `.card-surface` 内部的内框（盒中盒）。
 * 共同的技术原因：`.card-surface` 带 `isolation: isolate` + `backdrop-filter`，
 * 会为每个元素新建层叠上下文，大面积铺开会压住内部绝对定位装饰、打断浮层层级。
 *
 * 没有理由的裸标记不算豁免（正则要求 `panel-exempt:` 后必须跟非空文本），
 * 避免后人当成万能屏蔽词乱贴。
 */
describe('后台面板必须走 .card-surface，不得手写面层', () => {
  /** 面板级手写面层的特征：圆角 + 边框 + 卡片底色三件套 */
  const ADHOC_PANEL = /rounded-(?:\[\d+px\]|lg|xl|2xl)[^"']*\bborder\b[^"']*\bbg-card\b/
  /** 同时出现 border-border 与 bg-card 的也算（顺序不定） */
  const ADHOC_PANEL_REVERSED = /\bbg-card\b[^"']*\bborder-border\b/
  /** 豁免标记：必须带原因，裸标记不认 */
  const EXEMPT = /panel-exempt\s*:\s*\S/

  /**
   * 注释里的类名不该被当成真标记扫描（文档里引用 `rounded-xl border bg-card` 很常见）。
   * 但**豁免标记本身就写在注释里**，所以只把"不含 panel-exempt 的注释"抹成空白，
   * 其余字符换成空格以保留行号，报错定位才准。
   */
  function blankComments(src: string): string {
    return src.replace(/<!--[\s\S]*?-->|\/\*[\s\S]*?\*\//g, (m) =>
      EXEMPT.test(m) ? m : m.replace(/[^\n]/g, ' ')
    )
  }

  it.each(
    walk('pages/admin').concat(walk('components/admin'))
  )('%s 不得手写面板面层', (file) => {
    const src = blankComments(readFileSync(resolve(process.cwd(), file), 'utf8'))
    const offenders = src
      .split('\n')
      .map((line, i) => ({ line: i + 1, text: line.trim() }))
      .filter(
        ({ text }) =>
          (ADHOC_PANEL.test(text) || ADHOC_PANEL_REVERSED.test(text)) &&
          !text.includes('card-surface') &&
          !EXEMPT.test(text)
      )
    expect(
      offenders,
      `${file} 里发现手写面层，应改用 .card-surface 或 <AdminCard>；` +
        '确属豁免类型的，在同一行补 `panel-exempt: <原因>`：\n' +
        offenders.map(o => `  L${o.line}: ${o.text.slice(0, 120)}`).join('\n')
    ).toHaveLength(0)
  })
})
