/**
 * ECharts + vue-echarts 客户端插件
 *  - 仅在 client 端注册（admin 全部 ssr:false，公开页面也仅客户端用图表）
 *  - 使用按需引入（tree-shaking），避免打包整个 echarts
 *  - 全局注册 <v-chart> 组件（自动导入无需 import）
 * @doc https://github.com/ecomfe/vue-echarts
 */
import { use } from 'echarts/core'
import { CanvasRenderer, SVGRenderer } from 'echarts/renderers'
import {
  LineChart,
  BarChart,
  PieChart,
  GaugeChart,
  RadarChart
} from 'echarts/charts'
import {
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
} from 'echarts/components'
import VChart from 'vue-echarts'
import type { App } from 'vue'

// —— 按需注册 ECharts 核心能力 ——
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

export default defineNuxtPlugin((nuxtApp) => {
  // 全局注册 <v-chart>，SFC 中无需再单独 import
  ;(nuxtApp.vueApp as App).component('VChart', VChart)
})
