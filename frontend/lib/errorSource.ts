/**
 * errorSource.ts —— 全局错误处理器的「来源域」判定（纯函数，便于单测）。
 *
 * 背景：error-handler.client.ts 是客户端唯一的 toast 出口。浏览器扩展
 * （uBlock / Tampermonkey 等）注入页面世界的脚本抛错时，window.onerror 会
 * 拿到完整消息 + chrome-extension:// 来源，直接 toast 给访客看是产品缺陷
 * （用户看到红色报错却与站点无关）。按 AGENTS.md 红线，禁止按消息子串吞错，
 * 这里只做来源域分类：非本站 origin 的脚本错误降级为 console 记录。
 */

const EXTENSION_SCHEMES = /^(chrome|moz|ms-browser|brave|edge)-extension:\/\//i
/** 堆栈行形如 "    at chrome-extension://<id>/content.js:1:2"，scheme 不在行首，须用非锚定版。 */
const EXTENSION_SCHEMES_ANY = /(chrome|moz|ms-browser|brave|edge)-extension:\/\//i

/**
 * source 是否来自第三方（扩展注入脚本或异源资源）。
 * 解析失败的空/畸形值一律返回 false —— 宁可多弹一次 toast，不静默自家 bug。
 */
export function isThirdPartyErrorSource(source: unknown, selfOrigin: string): boolean {
  if (typeof source !== 'string' || source.trim() === '') return false
  if (EXTENSION_SCHEMES.test(source)) return true
  if (source.startsWith('(browser-extension)')) return true
  try {
    return new URL(source, selfOrigin).origin !== selfOrigin
  } catch {
    return false
  }
}

/**
 * unhandledrejection 的 reason 没有 source 参数，退而看堆栈里是否只含扩展 URL。
 * 保守判定：stack 中存在本站 URL 时不算第三方（混合栈可能是我们的 async 调了扩展 API）。
 */
export function isExtensionOnlyStack(reason: unknown, selfOrigin: string): boolean {
  const stack = typeof reason === 'string' ? reason : (reason as Error | null)?.stack
  if (typeof stack !== 'string' || stack === '') return false
  const extLines = stack.split('\n').filter(l => EXTENSION_SCHEMES_ANY.test(l))
  if (extLines.length === 0) return false
  return !stack.split('\n').some(l => l.trim().startsWith('at') && l.includes(selfOrigin))
}
