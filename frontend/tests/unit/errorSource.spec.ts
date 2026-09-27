/**
 * errorSource 来源域判定回归（error-handler.client.ts 的第三方静默层）。
 * 曾有缺陷：uBlock/Tampermonkey 等扩展注入页面世界的脚本抛错
 * （如 "Cannot read properties of undefined (reading 'dispose')"），
 * window.onerror 拿到完整消息 + chrome-extension:// 来源后直接 toast 给访客。
 * 本 spec 钉死口径：只按来源域/堆栈归属分类，异源与扩展 → true；
 * 本站脚本、相对路径、空/畸形值 → false（宁可多弹，不静默自家 bug）。
 */
import { describe, expect, it } from 'vitest'

import { isThirdPartyErrorSource, isExtensionOnlyStack } from '~~/lib/errorSource'

const SELF = 'http://localhost:3000'

describe('isThirdPartyErrorSource', () => {
  it('extension scheme sources are third party', () => {
    expect(isThirdPartyErrorSource('chrome-extension://abcdef/content.js', SELF)).toBe(true)
    expect(isThirdPartyErrorSource('moz-extension://x/y.js', SELF)).toBe(true)
    expect(isThirdPartyErrorSource('edge-extension://x/y.js', SELF)).toBe(true)
    expect(isThirdPartyErrorSource('(browser-extension)', SELF)).toBe(true)
  })

  it('cross-origin http(s) sources are third party (CDN)', () => {
    expect(isThirdPartyErrorSource('https://cdn.other.example/a.js', SELF)).toBe(true)
  })

  it('same-origin and relative-path sources are NOT third party', () => {
    expect(isThirdPartyErrorSource(`${SELF}/_nuxt/app.js`, SELF)).toBe(false)
    expect(isThirdPartyErrorSource('/_nuxt/app.js', SELF)).toBe(false)
    expect(isThirdPartyErrorSource('pages/index.vue', SELF)).toBe(false)
  })

  it('empty, non-string and malformed sources return false (prefer showing)', () => {
    expect(isThirdPartyErrorSource('', SELF)).toBe(false)
    expect(isThirdPartyErrorSource('   ', SELF)).toBe(false)
    expect(isThirdPartyErrorSource(undefined, SELF)).toBe(false)
    expect(isThirdPartyErrorSource(123, SELF)).toBe(false)
    expect(isThirdPartyErrorSource('not a url', SELF)).toBe(false)
  })
})

describe('isExtensionOnlyStack', () => {
  it('stack containing only extension frames is third party', () => {
    const err = new Error('boom')
    err.stack = [
      'Error: boom',
      '    at chrome-extension://abcdef/content.js:10:5',
      '    at chrome-extension://abcdef/content.js:20:9'
    ].join('\n')
    expect(isExtensionOnlyStack(err, SELF)).toBe(true)
  })

  it('plain string reason with only extension frames is third party', () => {
    expect(
      isExtensionOnlyStack(
        'TypeError: x is undefined\n  at moz-extension://id/inject.js:1:1',
        SELF
      )
    ).toBe(true)
  })

  it('mixed stack (own frame present) is NOT third party', () => {
    const err = new Error('boom')
    err.stack = [
      'Error: boom',
      '    at chrome-extension://abcdef/content.js:10:5',
      `    at ${SELF}/_nuxt/app.js:1:1`
    ].join('\n')
    expect(isExtensionOnlyStack(err, SELF)).toBe(false)
  })

  it('no stack / no extension frames returns false', () => {
    expect(isExtensionOnlyStack(undefined, SELF)).toBe(false)
    expect(isExtensionOnlyStack({}, SELF)).toBe(false)
    expect(isExtensionOnlyStack('failed without frames', SELF)).toBe(false)
    const err = new Error('boom')
    err.stack = `Error: boom\n  at ${SELF}/_nuxt/app.js:1:1`
    expect(isExtensionOnlyStack(err, SELF)).toBe(false)
  })
})
