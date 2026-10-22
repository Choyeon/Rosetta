/**
 * 后台仪表盘图表几何：ECharts 的 pie `radius` 百分比是按 **min(容器宽, 容器高)** 折算的，
 * 而仪表盘的卡片是「扁」的（宽 < 高 × 1.56），所以写死的 `radius:['58%','82%'] + center:['32%','50%']`
 * 会把圆环左半边推出画布：实测 xl 卡片 395×360 与手机 286×260 两种容器都被切。
 * 画布没有 CSS 断点概念，唯一稳的口径是按实测容器尺寸算像素几何（center/radius 允许传 px 数值）。
 * 本文件只放纯算术，尺寸口径改动必须由 vitest 钉住，不要搬回组件里。
 */

/** 竖排 legend 在右侧占用的宽度（色块 9 + 间距 5 + 最长标签「已发布文章」≈ 82） */
const SIDE_LEGEND_W = 96
/** 竖排 legend 挪到圆环下方时，每行占用的行高（字号 11 + itemGap 6） */
const LEGEND_ROW_H = 18
/** 圆环左右各留的气泡，避免描边（borderWidth 2 + emphasis scale 6）贴画布边 */
const RING_PAD = 10

/**
 * 容器宽小于该值时，右侧已放不下「圆环 + 竖排 legend」两栏，
 * legend 改为整条挪到圆环下方（横排放不下 5 条中文标签，所以用竖排）。
 */
export const DONUT_STACK_MAX_W = 380

export type DonutGeometry = {
  /** 窄容器：legend 在圆环下方 */
  stacked: boolean
  center: [number, number]
  radius: [number, number]
  legend: {
    orient: 'vertical'
    right?: number
    left?: string
    top?: number | 'center'
    itemGap: number
  }
  /** 中心装饰 gauge 的几何（必须与圆环同心，否则「全站内容体量」数字会偏到环外） */
  labelCenter: [number, number]
  labelRadius: number
  detailFontSize: number
}

/**
 * 未测到尺寸（首帧 ResizeObserver 还没回调）时按 xl 卡片的实际比例兜底，
 * 保证任何情况下圆环都不会被切——宁可先画窄一版，下一帧再校正。
 */
export function donutGeometry(w: number, h: number, legendRows = 5): DonutGeometry {
  const width = w > 0 ? w : 420
  const height = h > 0 ? h : 340
  const stacked = width < DONUT_STACK_MAX_W

  if (!stacked) {
    const boxW = width - SIDE_LEGEND_W - RING_PAD * 2
    const outer = Math.max(40, (Math.min(boxW, height - RING_PAD * 2) / 2) * 0.94)
    const inner = outer * 0.68
    return {
      stacked,
      center: [RING_PAD + boxW / 2, height / 2],
      radius: [inner, outer],
      legend: { orient: 'vertical', right: 4, top: 'center', itemGap: 12 },
      labelCenter: [RING_PAD + boxW / 2, height / 2],
      labelRadius: inner * 0.78,
      detailFontSize: inner >= 60 ? 20 : 16
    }
  }

  const legendH = legendRows * LEGEND_ROW_H + 6
  const boxH = Math.max(60, height - legendH - RING_PAD)
  const outer = Math.max(36, (Math.min(width - RING_PAD * 2, boxH) / 2) * 0.96)
  const inner = outer * 0.62
  return {
    stacked,
    center: [width / 2, RING_PAD + boxH / 2],
    radius: [inner, outer],
    legend: { orient: 'vertical', left: 'center', top: height - legendH, itemGap: 6 },
    labelCenter: [width / 2, RING_PAD + boxH / 2],
    labelRadius: inner * 0.8,
    detailFontSize: inner >= 52 ? 20 : 16
  }
}

/**
 * 热门文章水平柱：y 轴分类标签是文章标题本身，会直接吃掉绘图宽度
 * （实测 326px 容器里 22 字标题把柱区压到只剩 120px）。窄容器截更短，
 * 完整标题由 tooltip 承载。
 */
export function topArticleLabelLimit(w: number): number {
  return w > 0 && w < 420 ? 12 : 22
}

/** x 轴刻度数：窄容器给 5 档会挤成「0 10200300400500600」这种连号噪声 */
export function topArticleAxisTicks(w: number): number {
  return w > 0 && w < 420 ? 3 : 5
}
