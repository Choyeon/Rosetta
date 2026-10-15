/**
 * 首页侧栏排序 + 置顶区块自适应契约（静态源码断言，不挂载千行页面组件）。
 *
 * 钉住两条观感契约：
 *   1. 「最新动态」卡是侧栏第一块（原先排在站点数据之后，等于把站更新鲜的内容
 *      压在页尾）；左右两种侧栏分支都要成立，sidebarPosition 可切换不能只改一边。
 *   2. 置顶区块按"实际置顶条数"自适应：单篇走 feature 通栏特写（左大图 + 右标题摘要），
 *      ≥2 篇走网格且列数由条数封顶——posts_per_row 是上限而非固定值，2 篇摊 3 列会缺角；
 *      加载骨架/空态（条数 0）仍按设置出列，避免占位跳列。
 *   3. PostCard 的 feature 变体三件事不得回退：变体登记进类型联合、封面取 DETAIL 尺寸
 *      （通栏宽度下 CARD 尺寸的回落图会糊）、特写卡仍保留置顶徽标。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const homepageSource = readFileSync(resolve(ROOT, 'pages/index.vue'), 'utf-8')
const postCardSource = readFileSync(resolve(ROOT, 'components/PostCard.vue'), 'utf-8')

/** 取某个分支起始标记之后的源码窗口 */
function windowAfter(needle: string, span: number, source = homepageSource): string {
  const at = source.indexOf(needle)
  expect(at, `源码应包含 ${needle}`).toBeGreaterThan(-1)
  return source.slice(at, at + span)
}

describe('首页侧栏「最新动态」置顶', () => {
  it('侧栏左右两个分支都把动态卡排在站点数据之前', () => {
    // 分支容器 class 各自唯一，比模板里的 v-if 表达式更稳（后者含引号嵌套，断言易碎）
    for (const branch of ['order-2 lg:order-1', 'flex flex-col gap-6 order-3']) {
      const block = windowAfter(branch, 1200)
      const activityAt = block.indexOf('<ActivitySidebarCard />')
      const statsAt = block.indexOf('<!-- Site stats -->')
      expect(activityAt, `${branch} 应挂载动态卡`).toBeGreaterThan(-1)
      expect(statsAt, `${branch} 应仍有站点数据卡`).toBeGreaterThan(-1)
      expect(activityAt, `${branch}：动态卡必须排在站点数据之前`).toBeLessThan(statsAt)
    }
  })

  it('动态卡只挂载两次（一左一右），没有第三份副本', () => {
    const mounts = homepageSource.match(/<ActivitySidebarCard \/>/g) ?? []
    expect(mounts).toHaveLength(2)
  })
})

describe('首页置顶区块列数自适应', () => {
  const gridSource = windowAfter('const pinnedGridClass', 900)

  it('列数取 posts_per_row 与实际条数的较小值', () => {
    expect(gridSource).toContain('pinnedPosts.value.length')
    expect(gridSource).toContain('Math.min(ft.postsPerRow.value, n)')
  })

  it('条数为 0（骨架/空态）时仍按设置出列，占位不跳列', () => {
    expect(gridSource).toContain('n === 0 ? ft.postsPerRow.value')
  })

  it('单篇置顶走 feature 通栏特写，而不是窄卡撑大间距', () => {
    expect(homepageSource).toContain('pinnedPosts.value.length === 1')
    expect(homepageSource).toMatch(/v-else-if="singlePinnedPost"[\s\S]{0,120}variant="feature"/)
    expect(homepageSource).not.toContain('pinnedSingleClass')
  })

  it('骨架分支不受条数封顶影响', () => {
    const skeleton = windowAfter('v-else-if="postsPending && pinnedPosts.length === 0"', 240)
    expect(skeleton).toContain('pinnedGridClass')
  })
})

describe('PostCard feature 通栏特写变体', () => {
  it('变体既在类型联合里，也有模板分支', () => {
    expect(postCardSource).toMatch(/type PostCardVariant = 'default' \| 'compact' \| 'feature'/)
    expect(postCardSource).toMatch(/v-else-if="variant === 'feature'"/)
  })

  it('特写卡取 DETAIL 尺寸封面，其余变体仍是 CARD 尺寸', () => {
    expect(postCardSource).toMatch(/props\.variant === 'feature' \? POST_COVER_DETAIL : POST_COVER_CARD/)
  })

  it('特写分支保留置顶徽标与两栏栅格（通栏不是纯图文块）', () => {
    // 用 v-else-if 的起始片段定位分支窗口，避开串里嵌套引号导致的转义噪声
    const branch = windowAfter('v-else-if="variant', 2600, postCardSource)
    expect(branch).toContain('isPinned')
    expect(branch).toContain('md:grid-cols-')
  })
})
