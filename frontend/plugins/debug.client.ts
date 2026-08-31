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

  const persist = (label: string, err: unknown, extra?: Record<string, unknown>) => {
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
    persist('UNHANDLED REJECTION', reason)
  })
})
