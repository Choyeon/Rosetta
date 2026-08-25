import { toast as sonnerToast } from 'vue-sonner'

export default defineNuxtPlugin(() => {
  const toast = sonnerToast

  const showError = (message: string, detail?: unknown) => {
    // 避免刷屏：同一个消息在 3 秒内只弹一次
    const key = String(message).slice(0, 80)
    if ((showError as unknown as { _recent?: Map<string, number> })._recent?.has(key)) {
      const last = (showError as unknown as { _recent: Map<string, number> })._recent.get(key) ?? 0
      if (Date.now() - last < 3000) return
    }
    if (!(showError as unknown as { _recent?: Map<string, number> })._recent) {
      (showError as unknown as { _recent: Map<string, number> })._recent = new Map()
    }
    (showError as unknown as { _recent: Map<string, number> })._recent.set(key, Date.now())

    // 控制台同步保留，方便开发者看堆栈
    // eslint-disable-next-line no-console
    console.error('[GlobalErrorHandler]', message, detail)

    toast.error(message)
  }

  const extractMessage = (err: unknown): string => {
    if (err instanceof Error) return err.message
    if (typeof err === 'string') return err
    try {
      return JSON.stringify(err)
    } catch {
      return '发生未知错误'
    }
  }

  window.onerror = (message, source, lineno, colno, error) => {
    const msg = typeof message === 'string' ? message : extractMessage(message)
    showError(msg || '脚本执行出错', { source, lineno, colno, error })
    return false
  }

  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason
    const msg = extractMessage(reason)
    // Nuxt 的 "Must be called at the top of a setup function" 非常常见，给出更友好的提示
    if (msg.includes('Must be called at the top of a `setup` function')) {
      showError('页面上下文异常：某些请求没有正确初始化，请刷新页面重试', { reason })
    } else {
      showError(msg || '未处理的异步错误', { reason })
    }
    // 不阻止默认行为，保留控制台输出
  })
})
