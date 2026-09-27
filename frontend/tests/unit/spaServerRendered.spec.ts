/**
 * spa-serverrendered-zero 的 payload 语义修正回归测试。
 *
 * 背景（2026-09-27 实测 bug）：__NUXT_DATA__ 是 devalue 扁平数组格式，
 * 对象属性里的整数是「数组下标引用」而不是字面量。旧实现用正则把
 * "serverRendered":1 改成 ":0"，等于让该字段指向下标 0 的根对象（真值、
 * 且循环），/admin 的 admin.global 中间件 await authStore.initialize()
 * 因此误判「仍在 hydrate」等待 app:mounted → 挂载被路由阻塞 → 冷访问
 * /admin 永久白屏。此测试钉死新实现的三条核心语义。
 */
import { describe, expect, it, vi } from 'vitest'

// 模块顶层会调用 Nitro 的 defineNitroPlugin；vitest 环境无 Nitro 运行时，
// 先用桩替换全局再动态 import（default 导出只是原样拿回插件函数）。
vi.stubGlobal('defineNitroPlugin', (fn: unknown) => fn)
const { fixServerRendered } = await import('../../server/plugins/spa-serverrendered-zero.nitro')

/** 解析回数组并求 serverRendered 的引用真值 */
function resolveServerRendered(payload: string): unknown {
  const d = JSON.parse(payload)
  const idx = d[0].serverRendered
  return typeof idx === 'number' ? d[idx] : idx
}

describe('fixServerRendered（扁平 payload 引用语义）', () => {
  it('serverRendered 指向 true 时：改写为指向布尔 false', () => {
    const raw = JSON.stringify([{ path: 2, serverRendered: 1 }, true, '/admin'])
    const out = fixServerRendered(raw)
    expect(resolveServerRendered(out)).toBe(false)
    // 其它槽位下标不得漂移（path:2 仍须解析为 '/admin'）
    const d = JSON.parse(out)
    expect(d[d[0].path]).toBe('/admin')
  })

  it('serverRendered 已是 false 引用时：幂等 no-op（原字符串返回）', () => {
    const raw = JSON.stringify([{ serverRendered: 1 }, false])
    expect(fixServerRendered(raw)).toBe(raw)
  })

  it('数组里没有 false 槽位时：追加在尾部，不改动既有元素', () => {
    const raw = JSON.stringify([{ serverRendered: 1 }, true, 'x'])
    const out = JSON.parse(fixServerRendered(raw))
    expect(out[1]).toBe(true)
    expect(out[2]).toBe('x')
    expect(out[out.length - 1]).toBe(false)
    expect(out[0].serverRendered).toBe(out.length - 1)
  })

  it('非 JSON / 无数组根 / 无 serverRendered 键：一律原样返回', () => {
    expect(fixServerRendered('not-json[')).toBe('not-json[')
    expect(fixServerRendered('{"serverRendered":1}')).toBe('{"serverRendered":1}')
    const noKey = JSON.stringify([{ path: 1 }, '/admin'])
    expect(fixServerRendered(noKey)).toBe(noKey)
  })

  it('旧版误伤形态（:0 自引用）在双次钩子下不会被再次改写（幂等防御）', () => {
    // 模拟：如果历史 HTML 里出现过 serverRendered 指向非布尔值（下标 0 = 根对象），
    // 新实现应识别为「既非 true 也非 false」而不动它（交给下一次真实渲染修正）。
    const weird = JSON.stringify([{ serverRendered: 0 }])
    expect(fixServerRendered(weird)).toBe(weird)
  })
})
