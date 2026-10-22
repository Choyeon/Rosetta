/**
 * 批次 #68 契约：后台低宽度布局与图表几何。
 * 两条口径必须由数值/源码双向钉住：
 * 1) 圆环几何按实测容器算，任何宽高组合下环体不得出画布（ECharts pie 的百分比 radius
 *    按 min(宽,高) 折算，扁容器必切左半边——这是本批的根因，不是 legend 摆放问题）。
 * 2) 环形图 legend 必须显式给 data，否则 ECharts 从**所有** series 名收集，
 *    中心装饰 gauge 会在图例里变成一行假数据。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  DONUT_STACK_MAX_W,
  donutGeometry,
  topArticleAxisTicks,
  topArticleLabelLimit
} from '@/lib/adminChartLayout'

const read = (f: string) => readFileSync(resolve(process.cwd(), f), 'utf8')
const dash = read('pages/admin/index.vue')
const filterBar = read('components/admin/AdminFilterBar.vue')

/** 环体四个方向都必须落在画布内（outer 由 Math.max 兜住下限，inner < outer 才有环） */
function expectRingInsideCanvas(g: ReturnType<typeof donutGeometry>, w: number, h: number) {
  const [cx, cy] = g.center
  const outer = g.radius[1]
  const inner = g.radius[0]
  expect(inner).toBeGreaterThan(0)
  expect(inner).toBeLessThan(outer)
  expect(cx - outer).toBeGreaterThanOrEqual(0)
  expect(cx + outer).toBeLessThanOrEqual(w)
  expect(cy - outer).toBeGreaterThanOrEqual(0)
  expect(cy + outer).toBeLessThanOrEqual(h)
}

describe('donutGeometry · 圆环不出画布', () => {
  // 手机 390 视口：内容宽 ≈ 390-72(侧栏)-32(main p-4)-48(CardContent p-6) ≈ 238，卡片实测 286
  const cases: Array<[string, number, number]> = [
    ['手机窄卡', 286, 260],
    ['平板卡', 326, 300],
    ['xl 宽卡', 395, 360],
    ['2xl 超宽卡', 560, 360],
    ['极端窄', 180, 240],
    ['首帧未测到', 0, 0]
  ]

  for (const [name, w, h] of cases) {
    it(`${name} ${w}x${h}：环体完整在画布内`, () => {
      // donutGeometry 内部对未测到尺寸按 420x340 兜底，断言用同一口径
      expectRingInsideCanvas(donutGeometry(w, h), w > 0 ? w : 420, h > 0 ? h : 340)
    })
  }

  it('宽容器：右侧竖排 legend 与圆环分栏，环体右端给 legend 留出 96px', () => {
    const g = donutGeometry(395, 360)
    expect(g.stacked).toBe(false)
    expect(g.legend.orient).toBe('vertical')
    expect(g.legend.right).toBeDefined()
    // 环右端 + 竖排 legend 宽 ≤ 容器宽
    expect(g.center[0] + g.radius[1] + 96).toBeLessThanOrEqual(395)
  })

  it('窄容器：legend 整条挪到圆环下方，且不与环体重叠', () => {
    const g = donutGeometry(326, 300, 5)
    expect(g.stacked).toBe(true)
    expect(g.legend.left).toBe('center')
    const legendTop = g.legend.top as number
    expect(g.center[1] + g.radius[1]).toBeLessThanOrEqual(legendTop)
  })

  it('分栏阈值单源：DONUT_STACK_MAX_W 两侧行为互斥', () => {
    expect(donutGeometry(DONUT_STACK_MAX_W - 1, 300).stacked).toBe(true)
    expect(donutGeometry(DONUT_STACK_MAX_W, 300).stacked).toBe(false)
  })

  it('中心装饰与圆环同心，数字不会飘到环外', () => {
    for (const [w, h] of [[326, 300], [395, 360], [0, 0]] as const) {
      const g = donutGeometry(w, h)
      expect(g.labelCenter).toEqual(g.center)
      expect(g.labelRadius).toBeLessThan(g.radius[0])
      expect(g.detailFontSize === 16 || g.detailFontSize === 20).toBe(true)
    }
  })

  it('极端小容器不塌成 0 半径（Math.max 下限）', () => {
    const g = donutGeometry(60, 60)
    expect(g.radius[1]).toBeGreaterThanOrEqual(36)
    expect(g.radius[0]).toBeGreaterThan(0)
  })
})

describe('热门文章 TOP · 截断与刻度随容器宽', () => {
  it('窄容器截更短、刻度更少', () => {
    expect(topArticleLabelLimit(326)).toBe(12)
    expect(topArticleLabelLimit(560)).toBe(22)
    expect(topArticleAxisTicks(326)).toBe(3)
    expect(topArticleAxisTicks(560)).toBe(5)
  })

  it('未测到宽度时按宽容器口径（不得截成 12 字）', () => {
    expect(topArticleLabelLimit(0)).toBe(22)
    expect(topArticleAxisTicks(0)).toBe(5)
  })
})

describe('pages/admin/index.vue · 接线', () => {
  it('环形图 legend 显式给 data，假数据项不会进图例', () => {
    expect(dash).toContain('data: data.map(d => d.name)')
    expect(dash).not.toMatch(/name:\s*'center'/)
  })

  it('两个图表容器都接了实测 ref', () => {
    expect(dash).toContain('ref="donutEl"')
    expect(dash).toContain('ref="topArticlesEl"')
    expect(dash).toContain('useElementSize(donutEl)')
    expect(dash).toContain('useElementSize(topArticlesEl)')
  })

  it('圆环几何来自 donutGeometry，不再写死百分比 radius/center', () => {
    expect(dash).toContain('radius: geo.radius')
    expect(dash).toContain('center: geo.center')
    expect(dash).not.toContain("radius: ['58%', '82%']")
    expect(dash).not.toContain("center: ['32%', '50%']")
  })

  it('x 轴刻度重叠由 hideOverlap 兜住', () => {
    expect(dash.match(/hideOverlap: true/g)?.length ?? 0).toBeGreaterThanOrEqual(3)
  })

  it('热门榜 grid 用 containLabel，标题不再吃光绘图区', () => {
    expect(dash).toContain('containLabel: true')
  })

  it('KPI 网格窄屏至少两列（6 卡单列 = 1460px 滚动）', () => {
    expect(dash).toContain('grid-cols-1 min-[520px]:grid-cols-2')
  })

  it('卡片头标题可截断：min-w-0 + truncate 成对出现', () => {
    expect(dash.match(/class="min-w-0"/g)?.length ?? 0).toBeGreaterThanOrEqual(5)
    expect(dash.match(/CardTitle class="text-\[15px\] truncate"/g)?.length ?? 0).toBeGreaterThanOrEqual(5)
  })
})

describe('AdminFilterBar.vue · 窄屏不再竖排六行', () => {
  it('sm 以下走两列网格，关键字与日期条横跨整行', () => {
    expect(filterBar).toContain('grid grid-cols-2 gap-3 flex-1 sm:flex sm:flex-row')
    expect(filterBar).toContain('col-span-2 sm:min-w-[240px] sm:flex-1')
    expect(filterBar).toContain('order-last col-span-2')
  })

  it('状态选择器窄屏撑满、sm 起回到 140px', () => {
    expect(filterBar).toContain('w-full h-9 rounded-[10px] sm:w-[140px]')
  })
})
