/**
 * 观测元素内容尺寸。ECharts 画布没有断点概念，窄容器里的图表几何必须实测，
 * 所以后台仪表盘用它把卡片宽度喂给 lib/adminChartLayout。
 * 只在客户端观测（图表页全是 ssr:false），卸载时断开，避免残留 observer。
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { Ref } from 'vue'

export function useElementSize<T extends HTMLElement>(target: Ref<T | null | undefined>) {
  const width = ref(0)
  const height = ref(0)
  let observer: ResizeObserver | null = null

  const read = () => {
    const el = target.value
    if (!el) return
    width.value = el.clientWidth
    height.value = el.clientHeight
  }

  onMounted(() => {
    const el = target.value
    read()
    if (!el || typeof ResizeObserver === 'undefined') return
    observer = new ResizeObserver((entries) => {
      const box = entries[entries.length - 1]
      if (!box) return
      width.value = box.contentRect.width
      height.value = box.contentRect.height
    })
    observer.observe(el)
  })

  onBeforeUnmount(() => {
    observer?.disconnect()
    observer = null
  })

  return { width, height }
}
