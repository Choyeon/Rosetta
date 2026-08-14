export default defineNuxtPlugin((nuxtApp) => {
  const persist = (label: string, err: unknown, extra?: any) => {
    const rec = {
      label,
      message: String(err),
      stack: (err as any)?.stack || 'none',
      extra: extra ? JSON.stringify(extra, (k, v) => typeof v === 'string' ? v.substring(0, 500) : v, 2).substring(0, 1000) : ''
    }
    localStorage.setItem('__captured_error__', JSON.stringify(rec, null, 2))
    console.error(label, rec)
  }

  nuxtApp.hook('vue:error', (err, instance, info) => persist('NUXT HOOK vue:error', err, { info }))
  nuxtApp.hook('app:error', (err) => persist('NUXT HOOK app:error', err))
  nuxtApp.hook('page:loading:error', (err) => persist('NUXT HOOK page:loading:error', err))

  nuxtApp.vueApp.config.errorHandler = (err, instance, info) => persist('VUE config.errorHandler', err, { info })

  window.addEventListener('error', (e) => persist('WINDOW error', e.error || e.message, { file: e.filename, line: e.lineno, col: e.colno }))
  window.addEventListener('unhandledrejection', (e) => persist('UNHANDLED REJECTION', e.reason))
})
