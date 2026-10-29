/**
 * SSR 渲染失败必须变成 500 + no-store，不能是缓存的 200 空壳。
 *
 * 实测：Vue 3 生产构建对组件 setup / render 异常只记日志、把出错子树渲染成空，
 * 不向 Nitro 抛 —— Nuxt 照常回 200，页面只剩布局（<title> 是站点名、h1=0）。
 * 该路由带 swr 时这个空壳会被缓存（/zh_Hant/archive/<年>/<月> 的 RangeError 就是这样
 * 被缓存成 3600s 的"正常页"）。app.vue 的 onErrorCaptured 在服务端把它降级成 500：
 * nitropack 的缓存校验对 code>=400 的条目一律判失效，所以坏渲染不会再被复用。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const src = readFileSync(resolve(__dirname, '..', '..', 'app.vue'), 'utf-8')

describe('app.vue 的 SSR 渲染错误上报', () => {
  // 断言用正则而不是字面量：Vite 会把测试文件里的 `import.meta.server` 直接编译成 `false`，
  // 写在字符串里也会被替换，`toContain('… import.meta.server …')` 恒假。
  it('setup 期同步取好 request event（异步回调里再取会拿到 undefined）', () => {
    expect(src).toMatch(/const ssrEvent = import\.meta\.server \? useRequestEvent\(\) : undefined/)
  })

  it('服务端把捕获到的渲染错误升级成 500', () => {
    expect(src).toMatch(/if \(import\.meta\.server && ssrEvent\) \{/)
    expect(src).toContain('setResponseStatus(ssrEvent, 500)')
  })

  it('同时打 no-store，避免空壳被任何一层缓存', () => {
    expect(src).toMatch(/setHeader\(\s*'cache-control'\s*,\s*'no-store'\s*\)/)
  })
})
