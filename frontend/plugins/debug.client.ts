export default defineNuxtPlugin((nuxtApp) => {
  /**
   * 判断是否是 CORS 隐藏的第三方脚本错误（"Script error."）。
   *
   * 当错误来自 CDN / 字体 / 浏览器扩展等不同源脚本时，浏览器出于隐私把错误细节裁掉：
   *   message = 'Script error.'，file=''，line=0，col=0，error=null
   * 这类错误不是工程 bug，也无法定位到具体代码，应该直接静默避免污染日志 / 持久化错误。
   */
  function isForeignScriptError(
    message: unknown,
    file: unknown,
    line: unknown,
    col: unknown,
    error: unknown
  ): boolean {
    if (typeof message !== 'string' || !message.startsWith('Script error')) return false
    const noFile = !file || (typeof file === 'string' && file.trim() === '')
    const noLine = line == null || line === 0
    const noCol = col == null || col === 0
    const noError = error == null
    return noFile && noLine && noCol && noError
  }

  /**
   * 判断是不是 Hydration 级联错误（SSR mismatch → Vue 拆 SSR DOM → 子组件 instance detach
   * → instance.refs === null → TypeError reading refs）。
   *
   * 根因修复见 02-hydration-safety.global.client：
   *   1. 捕获后切换全局 __safetyRootKey → 整页 remount 为纯 CSR（不会再 detach）。
   *   2. 这里不再重复 console.error / toast，避免用户看到 4 条 refs null 红日志。
   */
  function isHydrationCascade(err: unknown): boolean {
    const s = (() => {
      if (err instanceof Error) return err.message
      if (err == null) return ''
      if (typeof (err as { message?: unknown }).message === 'string') {
        return (err as { message: string }).message
      }
      return String(err)
    })()
    if (!s) return false
    const lc = s.toLowerCase()
    if (lc.includes('hydration') || lc.includes('mismatch')) return true
    if (s.includes('reading refs') || (lc.includes('null') && lc.includes('refs'))) return true
    return false
  }

  const persist = (label: string, err: unknown, extra?: Record<string, unknown>) => {
    if (isHydrationCascade(err)) return
    const errObj = err as { stack?: string, message?: string }
    const rec = {
      label,
      message: String(err),
      stack: errObj?.stack || 'none',
      extra: extra ? JSON.stringify(extra, (k, v) => typeof v === 'string' ? v.substring(0, 500) : v, 2).substring(0, 1000) : ''
    }
    localStorage.setItem('__captured_error__', JSON.stringify(rec, null, 2))
    console.error(label, rec)
  }

  nuxtApp.hook('vue:error', (err, instance, info) => persist('NUXT HOOK vue:error', err, { info }))
  nuxtApp.hook('app:error', err => persist('NUXT HOOK app:error', err))

  nuxtApp.vueApp.config.errorHandler = (err, instance, info) => persist('VUE config.errorHandler', err, { info })

  window.addEventListener('error', (e) => {
    // 静默跳过 CDN / 浏览器扩展等跨域脚本抛出的 "Script error."
    if (isForeignScriptError(e.message, e.filename, e.lineno, e.colno, e.error)) return
    persist('WINDOW error', e.error || e.message, { file: e.filename, line: e.lineno, col: e.colno })
  })
  window.addEventListener('unhandledrejection', (e) => {
    const reason = e.reason
    // 同样把 Promise 形态的 "Script error." 空壳过滤掉
    const msg = typeof reason === 'string' ? reason : (reason as { message?: unknown } | null)?.message
    if (isForeignScriptError(msg, '', 0, 0, reason == null ? null : reason)) return
    if (isHydrationCascade(reason)) {
      e.preventDefault()
      return
    }
    persist('UNHANDLED REJECTION', reason)
  })
})
