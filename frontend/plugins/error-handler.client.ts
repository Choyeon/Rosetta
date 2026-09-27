/**
 * error-handler.client.ts —— 客户端全局错误唯一的 toast 出口（.client 插件：window 只在浏览器存在）。
 * 这里是直接给 window.onerror 赋值而不是 addEventListener，所以再加第二个赋值点会互相冲掉；
 * debug.client.ts 走 addEventListener('error')，与本插件共存且只写日志。
 * showError 用 message 前 80 字符做 3 秒去重，防止一个坏组件刷满屏 toast；
 * 跨域 "Script error."、异源/扩展注入脚本（按来源域判定，见 lib/errorSource.ts，
 * 绝非消息子串吞错）、hydration 级联一律静默（后者交给 02-hydration-safety 重挂载，误报只会吓用户）。
 */

import { toast as sonnerToast } from 'vue-sonner'
import { isThirdPartyErrorSource, isExtensionOnlyStack } from '~/lib/errorSource'

export default defineNuxtPlugin(() => {
  const toast = sonnerToast

  /**
   * 判断是否是 CORS 隐藏的第三方脚本错误（"Script error."）。
   *
   * 当错误来自不同源的 <script>（CDN、字体、广告、浏览器扩展等）时，浏览器出于
   * 隐私/安全会把错误信息裁剪为占位：
   *   message = 'Script error.'，file=''，line=0，col=0，error=null
   * 这种错误无法定位到具体代码行，也不是我们工程的 bug；应该直接静默，
   * 否则每次刷新都会在控制台、toast 和错误收集里出现噪音。
   */
  function isForeignScriptError(
    message: unknown,
    source: unknown,
    lineno: unknown,
    colno: unknown,
    error: unknown
  ): boolean {
    if (typeof message !== 'string' || !message.startsWith('Script error')) return false
    const noSource = !source || (typeof source === 'string' && source.trim() === '')
    const noLine = lineno == null || lineno === 0
    const noCol = colno == null || colno === 0
    const noError = error == null
    return noSource && noLine && noCol && noError
  }

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

  /**
   * Hydration 级联错误（refs null / mismatch）：
   * 由 02-hydration-safety.global.client.ts 负责静默 + CSR 重挂载，
   * 这里提前拦截避免 toast 对用户误报。
   */
  const isHydrationCascade = (err: unknown): boolean => {
    const msg = extractMessage(err).toLowerCase()
    if (msg.includes('hydration') || msg.includes('mismatch')) return true
    if (msg.includes('refs')) {
      if (msg.includes('null') || msg.includes('reading')) return true
    }
    return false
  }

  window.onerror = (message, source, lineno, colno, error) => {
    // 静默跳过 CDN / 浏览器扩展等跨域脚本抛出的 "Script error."
    if (isForeignScriptError(message, source, lineno, colno, error)) return false
    // 扩展注入脚本（chrome-extension:// 等）或异源脚本抛的错：与站点无关，
    // 按来源域降级为 console 记录，不打扰用户。判定只看 origin，绝不按
    // 消息子串吞错（AGENTS.md 红线），本站脚本的错误照常 toast。
    if (isThirdPartyErrorSource(source, location.origin)) {
      console.warn('[GlobalErrorHandler] 忽略第三方脚本错误：', message, source)
      return false
    }
    if (isHydrationCascade(error ?? message)) return false
    const msg = typeof message === 'string' ? message : extractMessage(message)
    showError(msg || '脚本执行出错', { source, lineno, colno, error })
    return false
  }

  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason
    if (isExtensionOnlyStack(reason, location.origin)) {
      console.warn('[GlobalErrorHandler] 忽略扩展堆栈的异步错误：', reason)
      event.preventDefault()
      return
    }
    if (isHydrationCascade(reason)) {
      event.preventDefault()
      return
    }
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
