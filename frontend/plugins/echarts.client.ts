/**
 * ECharts + vue-echarts 客户端插件（懒加载版）
 *  - 仅在 client 端注册（admin 全部 ssr:false，公开页面也仅客户端用图表）
 *  - 按需引入（tree-shaking），避免打包整个 echarts
 *  - 使用 defineAsyncComponent 延迟加载：echarts 核心代码仅在 <v-chart>
 *    首次渲染时才下载，公开页面（访客）完全不加载 echarts chunk
 *  - 全局注册 <v-chart> 组件（自动导入无需 import）
 * @doc https://github.com/ecomfe/vue-echarts
 */
import { defineAsyncComponent } from 'vue'
import type { App, Component } from 'vue'

let registered = false

async function loadEcharts(): Promise<Component> {
  if (!registered) {
    const [
      { use },
      { CanvasRenderer, SVGRenderer },
      { LineChart, BarChart, PieChart, GaugeChart, RadarChart },
      {
        GridComponent,
        TooltipComponent,
        LegendComponent,
        TitleComponent,
        DataZoomComponent,
        GraphicComponent,
        RadarComponent,
        AriaComponent,
        MarkLineComponent,
        MarkPointComponent
      },
      { default: VChart }
    ] = await Promise.all([
      import('echarts/core'),
      import('echarts/renderers'),
      import('echarts/charts'),
      import('echarts/components'),
      import('vue-echarts')
    ])

    // —— 按需注册 ECharts 核心能力（仅在首次渲染图表时执行一次）——
    use([
      CanvasRenderer,
      SVGRenderer,
      LineChart,
      BarChart,
      PieChart,
      GaugeChart,
      RadarChart,
      GridComponent,
      TooltipComponent,
      LegendComponent,
      TitleComponent,
      DataZoomComponent,
      GraphicComponent,
      RadarComponent,
      AriaComponent,
      MarkLineComponent,
      MarkPointComponent
    ])
    registered = true
    return VChart
  }
  // 已注册过：直接返回 vue-echarts 默认导出（模块缓存，不会重复下载）
  const { default: VChart } = await import('vue-echarts')
  return VChart
}

export default defineNuxtPlugin((nuxtApp) => {
  // 全局注册异步 <v-chart>：首次渲染时触发 loadEcharts() 下载 echarts chunk
  const AsyncVChart = defineAsyncComponent({
    loader: loadEcharts,
    // 加载中占位：避免图表区域空白闪烁
    loadingComponent: {
      template: '<div class="w-full h-full flex items-center justify-center text-muted-foreground text-sm">…</div>'
    },
    delay: 200,
    suspensible: false
  })
  ;(nuxtApp.vueApp as App).component('VChart', AsyncVChart)
})
