/**
 * SSR-only shim that Vite resolver substitutes for `@lucide/vue` when
 * building/rendering on the server (see `rosetta-lucide-ssr-fix` in nuxt.config.ts).
 *
 * 本文件由 scripts/gen-lucide-ssr-shim.mjs 生成（勿手改）。
 *
 * v2（2026-10-01）：从 @lucide/vue dist esm icons 提取**真实 __iconNode**，
 * 服务端渲染与客户端真实包字节级一致（class 前缀 / width/height / path 数据
 * 全部对齐）——v1 的 rect placeholder 与手写 path 都会导致 hydration mismatch。
 *
 * 渲染语义复刻 createLucideIcon/Icon.mjs 的确定性路径（无 Provider 上下文）：
 *   svg 属性 = defaultAttributes，class = `lucide lucide-<kebab>-icon lucide-<kebab>`，
 *   其余 attrs（class/style 等）经 inheritAttrs fallthrough 合并，与客户端一致。
 *
 * Client builds use the original npm: @lucide/vue package (paths correct).
 */
import { defineComponent, h } from 'vue'
import type { DefineComponent } from 'vue'

type IconNode = ReadonlyArray<readonly [string, Record<string, unknown>]>

const defaultAttrs: Record<string, string | number> = {
  'xmlns': 'http://www.w3.org/2000/svg',
  'width': 24,
  'height': 24,
  'viewBox': '0 0 24 24',
  'fill': 'none',
  'stroke': 'currentColor',
  'stroke-width': 2,
  'stroke-linecap': 'round',
  'stroke-linejoin': 'round'
}

const toPascal = (s: string): string =>
  s.split('-').map((p) => (p ? p[0].toUpperCase() + p.slice(1) : '')).join('')
const toKebab = (s: string): string => s.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase()
// ⚠️ 与 npm Icon.mjs 逐字节对齐：第一段 class 走 kebab(pascal(name)) 往返，
// 名字含数字时连字符会在 Pascal 化时被合并（link-2 -> Link2 -> link2），
// 这是 @lucide/vue v1.37 客户端的实际行为（含 bug 语义），SSR shim 必须复刻，
// 否则出现 Hydration class mismatch（/friends 页 lucide-link-2 实证 2026-10-01）。
const iconClass = (name: string): string =>
  `lucide lucide-${toKebab(toPascal(name))}-icon lucide-${toKebab(name)}`

const ssrIcon = (name: string, iconNode: IconNode): DefineComponent =>
  defineComponent({
    name: `LucideSSR_${name}`,
    inheritAttrs: true,
    setup() {
      return () =>
        h(
          'svg',
          { ...defaultAttrs, class: iconClass(name) },
          iconNode.map(([tag, props]) => h(tag, props))
        )
    }
  }) as unknown as DefineComponent

// 极少数无法解析 iconNode 的名字走 rect 占位（仍保证 svg first-child 同构）
const stubIcon = (name: string): DefineComponent =>
  defineComponent({
    name: `LucideSSR_stub_${name}`,
    inheritAttrs: true,
    setup() {
      return () =>
        h('svg', { ...defaultAttrs, class: iconClass(name) }, [
          h('rect', { x: 3, y: 3, width: 18, height: 18, rx: 2, ry: 2, opacity: 0 })
        ])
    }
  }) as unknown as DefineComponent

// Dynamic fallback：任何未静态导出的名字仍可解析（Proxy）
const base: Record<string, DefineComponent> = {}
const withExports = new Proxy(base, {
  get(target, prop, receiver) {
    if (typeof prop !== 'string') return Reflect.get(target, prop, receiver)
    if (prop in target) return Reflect.get(target, prop, receiver)
    if (prop === 'default') return Reflect.get(target, prop, receiver)
    if (!prop.startsWith('__') && /^[A-Z][A-Za-z0-9]*$/.test(prop)) {
      const stub = stubIcon(prop)
      target[prop] = stub
      return stub
    }
    return Reflect.get(target, prop, receiver)
  },
  has(target, prop) {
    if (typeof prop === 'string' && /^[A-Z][A-Za-z0-9]*$/.test(prop)) return true
    return Reflect.has(target, prop)
  }
})
export default withExports
export const LucideSSR = withExports

// ==== Exhaustive real-data exports（1790 canonical icons）====
export const AArrowDown = ssrIcon('a-arrow-down', [["path",{"d":"m14 12 4 4 4-4","key":"buelq4"}],["path",{"d":"M18 16V7","key":"ty0viw"}],["path",{"d":"m2 16 4.039-9.69a.5.5 0 0 1 .923 0L11 16","key":"d5nyq2"}],["path",{"d":"M3.304 13h6.392","key":"1q3zxz"}]])
export const AArrowUp = ssrIcon('a-arrow-up', [["path",{"d":"m14 11 4-4 4 4","key":"1pu57t"}],["path",{"d":"M18 16V7","key":"ty0viw"}],["path",{"d":"m2 16 4.039-9.69a.5.5 0 0 1 .923 0L11 16","key":"d5nyq2"}],["path",{"d":"M3.304 13h6.392","key":"1q3zxz"}]])
export const ALargeSmall = ssrIcon('a-large-small', [["path",{"d":"m15 16 2.536-7.328a1.02 1.02 1 0 1 1.928 0L22 16","key":"xik6mr"}],["path",{"d":"M15.697 14h5.606","key":"1stdlc"}],["path",{"d":"m2 16 4.039-9.69a.5.5 0 0 1 .923 0L11 16","key":"d5nyq2"}],["path",{"d":"M3.304 13h6.392","key":"1q3zxz"}]])
export const Accessibility = ssrIcon('accessibility', [["circle",{"cx":"16","cy":"4","r":"1","key":"1grugj"}],["path",{"d":"m18 19 1-7-6 1","key":"r0i19z"}],["path",{"d":"m5 8 3-3 5.5 3-2.36 3.5","key":"9ptxx2"}],["path",{"d":"M4.24 14.5a5 5 0 0 0 6.88 6","key":"10kmtu"}],["path",{"d":"M13.76 17.5a5 5 0 0 0-6.88-6","key":"2qq6rc"}]])
export const Activity = ssrIcon('activity', [["path",{"d":"M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2","key":"169zse"}]])
export const SquareActivity = ssrIcon('square-activity', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M17 12h-2l-2 5-2-10-2 5H7","key":"15hlnc"}]])
export const Ad = ssrIcon('ad', [["path",{"d":"M10 13H6","key":"18d9xh"}],["path",{"d":"M10 15v-4a2 2 0 0 0-4 0v4","key":"ss28p3"}],["path",{"d":"M14 14.5a.5.5 0 0 0 .5.5h1a2.5 2.5 0 0 0 2.5-2.5v-1A2.5 2.5 0 0 0 15.5 9h-1a.5.5 0 0 0-.5.5z","key":"b3f847"}],["rect",{"x":"2","y":"5","width":"20","height":"14","rx":"2","key":"qneu4z"}]])
export const AirVent = ssrIcon('air-vent', [["path",{"d":"M18 17.5a2.5 2.5 0 1 1-4 2.03V12","key":"yd12zl"}],["path",{"d":"M6 12H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2","key":"larmp2"}],["path",{"d":"M6 8h12","key":"6g4wlu"}],["path",{"d":"M6.6 15.572A2 2 0 1 0 10 17v-5","key":"1x1kqn"}]])
export const Airplay = ssrIcon('airplay', [["path",{"d":"M5 17H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-1","key":"ns4c3b"}],["path",{"d":"m12 15 5 6H7Z","key":"14qnn2"}]])
export const AlarmClockCheck = ssrIcon('alarm-clock-check', [["circle",{"cx":"12","cy":"13","r":"8","key":"3y4lt7"}],["path",{"d":"M5 3 2 6","key":"18tl5t"}],["path",{"d":"m22 6-3-3","key":"1opdir"}],["path",{"d":"M6.38 18.7 4 21","key":"17xu3x"}],["path",{"d":"M17.64 18.67 20 21","key":"kv2oe2"}],["path",{"d":"m9 13 2 2 4-4","key":"6343dt"}]])
export const AlarmClock = ssrIcon('alarm-clock', [["circle",{"cx":"12","cy":"13","r":"8","key":"3y4lt7"}],["path",{"d":"M12 9v4l2 2","key":"1c63tq"}],["path",{"d":"M5 3 2 6","key":"18tl5t"}],["path",{"d":"m22 6-3-3","key":"1opdir"}],["path",{"d":"M6.38 18.7 4 21","key":"17xu3x"}],["path",{"d":"M17.64 18.67 20 21","key":"kv2oe2"}]])
export const AlarmClockMinus = ssrIcon('alarm-clock-minus', [["circle",{"cx":"12","cy":"13","r":"8","key":"3y4lt7"}],["path",{"d":"M5 3 2 6","key":"18tl5t"}],["path",{"d":"m22 6-3-3","key":"1opdir"}],["path",{"d":"M6.38 18.7 4 21","key":"17xu3x"}],["path",{"d":"M17.64 18.67 20 21","key":"kv2oe2"}],["path",{"d":"M9 13h6","key":"1uhe8q"}]])
export const AlarmClockOff = ssrIcon('alarm-clock-off', [["path",{"d":"M6.87 6.87a8 8 0 1 0 11.26 11.26","key":"3on8tj"}],["path",{"d":"M19.9 14.25a8 8 0 0 0-9.15-9.15","key":"15ghsc"}],["path",{"d":"m22 6-3-3","key":"1opdir"}],["path",{"d":"M6.26 18.67 4 21","key":"yzmioq"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M4 4 2 6","key":"1ycko6"}]])
export const AlarmClockPlus = ssrIcon('alarm-clock-plus', [["circle",{"cx":"12","cy":"13","r":"8","key":"3y4lt7"}],["path",{"d":"M5 3 2 6","key":"18tl5t"}],["path",{"d":"m22 6-3-3","key":"1opdir"}],["path",{"d":"M6.38 18.7 4 21","key":"17xu3x"}],["path",{"d":"M17.64 18.67 20 21","key":"kv2oe2"}],["path",{"d":"M12 10v6","key":"1bos4e"}],["path",{"d":"M9 13h6","key":"1uhe8q"}]])
export const AlarmSmoke = ssrIcon('alarm-smoke', [["path",{"d":"M11 21c0-2.5 2-2.5 2-5","key":"1sicvv"}],["path",{"d":"M16 21c0-2.5 2-2.5 2-5","key":"1o3eny"}],["path",{"d":"m19 8-.8 3a1.25 1.25 0 0 1-1.2 1H7a1.25 1.25 0 0 1-1.2-1L5 8","key":"1bvca4"}],["path",{"d":"M21 3a1 1 0 0 1 1 1v2a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4a1 1 0 0 1 1-1z","key":"x3qr1j"}],["path",{"d":"M6 21c0-2.5 2-2.5 2-5","key":"i3w1gp"}]])
export const Album = ssrIcon('album', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","ry":"2","key":"1m3agn"}],["polyline",{"points":"11 3 11 11 14 8 17 11 17 3","key":"1wcwz3"}]])
export const CircleAlert = ssrIcon('circle-alert', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["line",{"x1":"12","x2":"12","y1":"8","y2":"12","key":"1pkeuh"}],["line",{"x1":"12","x2":"12.01","y1":"16","y2":"16","key":"4dfq90"}]])
export const OctagonAlert = ssrIcon('octagon-alert', [["path",{"d":"M12 16h.01","key":"1drbdi"}],["path",{"d":"M12 8v4","key":"1got3b"}],["path",{"d":"M15.312 2a2 2 0 0 1 1.414.586l4.688 4.688A2 2 0 0 1 22 8.688v6.624a2 2 0 0 1-.586 1.414l-4.688 4.688a2 2 0 0 1-1.414.586H8.688a2 2 0 0 1-1.414-.586l-4.688-4.688A2 2 0 0 1 2 15.312V8.688a2 2 0 0 1 .586-1.414l4.688-4.688A2 2 0 0 1 8.688 2z","key":"1fd625"}]])
export const TriangleAlert = ssrIcon('triangle-alert', [["path",{"d":"m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3","key":"wmoenq"}],["path",{"d":"M12 9v4","key":"juzpu7"}],["path",{"d":"M12 17h.01","key":"p32p05"}]])
export const TextAlignCenter = ssrIcon('text-align-center', [["path",{"d":"M21 5H3","key":"1fi0y6"}],["path",{"d":"M17 12H7","key":"16if0g"}],["path",{"d":"M19 19H5","key":"vjpgq2"}]])
export const AlignCenterHorizontal = ssrIcon('align-center-horizontal', [["path",{"d":"M2 12h20","key":"9i4pu4"}],["path",{"d":"M10 16v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-4","key":"11f1s0"}],["path",{"d":"M10 8V4a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v4","key":"t14dx9"}],["path",{"d":"M20 16v1a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2v-1","key":"1w07xs"}],["path",{"d":"M14 8V7c0-1.1.9-2 2-2h2a2 2 0 0 1 2 2v1","key":"1apec2"}]])
export const AlignCenterVertical = ssrIcon('align-center-vertical', [["path",{"d":"M12 2v20","key":"t6zp3m"}],["path",{"d":"M8 10H4a2 2 0 0 1-2-2V6c0-1.1.9-2 2-2h4","key":"14d6g8"}],["path",{"d":"M16 10h4a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-4","key":"1e2lrw"}],["path",{"d":"M8 20H7a2 2 0 0 1-2-2v-2c0-1.1.9-2 2-2h1","key":"1fkdwx"}],["path",{"d":"M16 14h1a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2h-1","key":"1euafb"}]])
export const AlignEndHorizontal = ssrIcon('align-end-horizontal', [["rect",{"width":"6","height":"16","x":"4","y":"2","rx":"2","key":"z5wdxg"}],["rect",{"width":"6","height":"9","x":"14","y":"9","rx":"2","key":"um7a8w"}],["path",{"d":"M22 22H2","key":"19qnx5"}]])
export const AlignEndVertical = ssrIcon('align-end-vertical', [["rect",{"width":"16","height":"6","x":"2","y":"4","rx":"2","key":"10wcwx"}],["rect",{"width":"9","height":"6","x":"9","y":"14","rx":"2","key":"4p5bwg"}],["path",{"d":"M22 22V2","key":"12ipfv"}]])
export const AlignHorizontalDistributeCenter = ssrIcon('align-horizontal-distribute-center', [["rect",{"width":"6","height":"14","x":"4","y":"5","rx":"2","key":"1wwnby"}],["rect",{"width":"6","height":"10","x":"14","y":"7","rx":"2","key":"1fe6j6"}],["path",{"d":"M17 22v-5","key":"4b6g73"}],["path",{"d":"M17 7V2","key":"hnrr36"}],["path",{"d":"M7 22v-3","key":"1r4jpn"}],["path",{"d":"M7 5V2","key":"liy1u9"}]])
export const AlignHorizontalDistributeEnd = ssrIcon('align-horizontal-distribute-end', [["rect",{"width":"6","height":"14","x":"4","y":"5","rx":"2","key":"1wwnby"}],["rect",{"width":"6","height":"10","x":"14","y":"7","rx":"2","key":"1fe6j6"}],["path",{"d":"M10 2v20","key":"uyc634"}],["path",{"d":"M20 2v20","key":"1tx262"}]])
export const AlignHorizontalDistributeStart = ssrIcon('align-horizontal-distribute-start', [["rect",{"width":"6","height":"14","x":"4","y":"5","rx":"2","key":"1wwnby"}],["rect",{"width":"6","height":"10","x":"14","y":"7","rx":"2","key":"1fe6j6"}],["path",{"d":"M4 2v20","key":"gtpd5x"}],["path",{"d":"M14 2v20","key":"tg6bpw"}]])
export const AlignHorizontalJustifyCenter = ssrIcon('align-horizontal-justify-center', [["rect",{"width":"6","height":"14","x":"2","y":"5","rx":"2","key":"dy24zr"}],["rect",{"width":"6","height":"10","x":"16","y":"7","rx":"2","key":"13zkjt"}],["path",{"d":"M12 2v20","key":"t6zp3m"}]])
export const AlignHorizontalJustifyEnd = ssrIcon('align-horizontal-justify-end', [["rect",{"width":"6","height":"14","x":"2","y":"5","rx":"2","key":"dy24zr"}],["rect",{"width":"6","height":"10","x":"12","y":"7","rx":"2","key":"1ht384"}],["path",{"d":"M22 2v20","key":"40qfg1"}]])
export const AlignHorizontalJustifyStart = ssrIcon('align-horizontal-justify-start', [["rect",{"width":"6","height":"14","x":"6","y":"5","rx":"2","key":"hsirpf"}],["rect",{"width":"6","height":"10","x":"16","y":"7","rx":"2","key":"13zkjt"}],["path",{"d":"M2 2v20","key":"1ivd8o"}]])
export const AlignHorizontalSpaceAround = ssrIcon('align-horizontal-space-around', [["rect",{"width":"6","height":"10","x":"9","y":"7","rx":"2","key":"yn7j0q"}],["path",{"d":"M4 22V2","key":"tsjzd3"}],["path",{"d":"M20 22V2","key":"1bnhr8"}]])
export const AlignHorizontalSpaceBetween = ssrIcon('align-horizontal-space-between', [["rect",{"width":"6","height":"14","x":"3","y":"5","rx":"2","key":"j77dae"}],["rect",{"width":"6","height":"10","x":"15","y":"7","rx":"2","key":"bq30hj"}],["path",{"d":"M3 2v20","key":"1d2pfg"}],["path",{"d":"M21 2v20","key":"p059bm"}]])
export const TextAlignJustify = ssrIcon('text-align-justify', [["path",{"d":"M3 5h18","key":"1u36vt"}],["path",{"d":"M3 12h18","key":"1i2n21"}],["path",{"d":"M3 19h18","key":"awlh7x"}]])
export const TextAlignStart = ssrIcon('text-align-start', [["path",{"d":"M21 5H3","key":"1fi0y6"}],["path",{"d":"M15 12H3","key":"6jk70r"}],["path",{"d":"M17 19H3","key":"z6ezky"}]])
export const TextAlignEnd = ssrIcon('text-align-end', [["path",{"d":"M21 5H3","key":"1fi0y6"}],["path",{"d":"M21 12H9","key":"dn1m92"}],["path",{"d":"M21 19H7","key":"4cu937"}]])
export const AlignStartHorizontal = ssrIcon('align-start-horizontal', [["rect",{"width":"6","height":"16","x":"4","y":"6","rx":"2","key":"1n4dg1"}],["rect",{"width":"6","height":"9","x":"14","y":"6","rx":"2","key":"17khns"}],["path",{"d":"M22 2H2","key":"fhrpnj"}]])
export const AlignStartVertical = ssrIcon('align-start-vertical', [["rect",{"width":"9","height":"6","x":"6","y":"14","rx":"2","key":"lpm2y7"}],["rect",{"width":"16","height":"6","x":"6","y":"4","rx":"2","key":"rdj6ps"}],["path",{"d":"M2 2v20","key":"1ivd8o"}]])
export const AlignVerticalDistributeCenter = ssrIcon('align-vertical-distribute-center', [["path",{"d":"M22 17h-3","key":"1lwga1"}],["path",{"d":"M22 7h-5","key":"o2endc"}],["path",{"d":"M5 17H2","key":"1gx9xc"}],["path",{"d":"M7 7H2","key":"6bq26l"}],["rect",{"x":"5","y":"14","width":"14","height":"6","rx":"2","key":"1qrzuf"}],["rect",{"x":"7","y":"4","width":"10","height":"6","rx":"2","key":"we8e9z"}]])
export const AlignVerticalDistributeEnd = ssrIcon('align-vertical-distribute-end', [["rect",{"width":"14","height":"6","x":"5","y":"14","rx":"2","key":"jmoj9s"}],["rect",{"width":"10","height":"6","x":"7","y":"4","rx":"2","key":"aza5on"}],["path",{"d":"M2 20h20","key":"owomy5"}],["path",{"d":"M2 10h20","key":"1ir3d8"}]])
export const AlignVerticalDistributeStart = ssrIcon('align-vertical-distribute-start', [["rect",{"width":"14","height":"6","x":"5","y":"14","rx":"2","key":"jmoj9s"}],["rect",{"width":"10","height":"6","x":"7","y":"4","rx":"2","key":"aza5on"}],["path",{"d":"M2 14h20","key":"myj16y"}],["path",{"d":"M2 4h20","key":"mda7wb"}]])
export const AlignVerticalJustifyCenter = ssrIcon('align-vertical-justify-center', [["rect",{"width":"14","height":"6","x":"5","y":"16","rx":"2","key":"1i8z2d"}],["rect",{"width":"10","height":"6","x":"7","y":"2","rx":"2","key":"ypihtt"}],["path",{"d":"M2 12h20","key":"9i4pu4"}]])
export const AlignVerticalJustifyEnd = ssrIcon('align-vertical-justify-end', [["rect",{"width":"14","height":"6","x":"5","y":"12","rx":"2","key":"4l4tp2"}],["rect",{"width":"10","height":"6","x":"7","y":"2","rx":"2","key":"ypihtt"}],["path",{"d":"M2 22h20","key":"272qi7"}]])
export const AlignVerticalJustifyStart = ssrIcon('align-vertical-justify-start', [["rect",{"width":"14","height":"6","x":"5","y":"16","rx":"2","key":"1i8z2d"}],["rect",{"width":"10","height":"6","x":"7","y":"6","rx":"2","key":"13squh"}],["path",{"d":"M2 2h20","key":"1ennik"}]])
export const AlignVerticalSpaceAround = ssrIcon('align-vertical-space-around', [["rect",{"width":"10","height":"6","x":"7","y":"9","rx":"2","key":"b1zbii"}],["path",{"d":"M22 20H2","key":"1p1f7z"}],["path",{"d":"M22 4H2","key":"1b7qnq"}]])
export const AlignVerticalSpaceBetween = ssrIcon('align-vertical-space-between', [["rect",{"width":"14","height":"6","x":"5","y":"15","rx":"2","key":"1w91an"}],["rect",{"width":"10","height":"6","x":"7","y":"3","rx":"2","key":"17wqzy"}],["path",{"d":"M2 21h20","key":"1nyx9w"}],["path",{"d":"M2 3h20","key":"91anmk"}]])
export const Ambulance = ssrIcon('ambulance', [["path",{"d":"M10 10H6","key":"1bsnug"}],["path",{"d":"M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2","key":"wrbu53"}],["path",{"d":"M19 18h2a1 1 0 0 0 1-1v-3.28a1 1 0 0 0-.684-.948l-1.923-.641a1 1 0 0 1-.578-.502l-1.539-3.076A1 1 0 0 0 16.382 8H14","key":"lrkjwd"}],["path",{"d":"M8 8v4","key":"1fwk8c"}],["path",{"d":"M9 18h6","key":"x1upvd"}],["circle",{"cx":"17","cy":"18","r":"2","key":"332jqn"}],["circle",{"cx":"7","cy":"18","r":"2","key":"19iecd"}]])
export const Ampersand = ssrIcon('ampersand', [["path",{"d":"M16 12h3","key":"4uvgyw"}],["path",{"d":"M17.5 12a8 8 0 0 1-8 8A4.5 4.5 0 0 1 5 15.5c0-6 8-4 8-8.5a3 3 0 1 0-6 0c0 3 2.5 8.5 12 13","key":"nfoe1t"}]])
export const Ampersands = ssrIcon('ampersands', [["path",{"d":"M10 17c-5-3-7-7-7-9a2 2 0 0 1 4 0c0 2.5-5 2.5-5 6 0 1.7 1.3 3 3 3 2.8 0 5-2.2 5-5","key":"12lh1k"}],["path",{"d":"M22 17c-5-3-7-7-7-9a2 2 0 0 1 4 0c0 2.5-5 2.5-5 6 0 1.7 1.3 3 3 3 2.8 0 5-2.2 5-5","key":"173c68"}]])
export const Amphora = ssrIcon('amphora', [["path",{"d":"M10 2v5.632c0 .424-.272.795-.653.982A6 6 0 0 0 6 14c.006 4 3 7 5 8","key":"1h8rid"}],["path",{"d":"M10 5H8a2 2 0 0 0 0 4h.68","key":"3ezsi6"}],["path",{"d":"M14 2v5.632c0 .424.272.795.652.982A6 6 0 0 1 18 14c0 4-3 7-5 8","key":"yt6q09"}],["path",{"d":"M14 5h2a2 2 0 0 1 0 4h-.68","key":"8f95yk"}],["path",{"d":"M18 22H6","key":"mg6kv4"}],["path",{"d":"M9 2h6","key":"1jrp98"}]])
export const Anchor = ssrIcon('anchor', [["path",{"d":"M12 6v16","key":"nqf5sj"}],["path",{"d":"m19 13 2-1a9 9 0 0 1-18 0l2 1","key":"y7qv08"}],["path",{"d":"M9 11h6","key":"1fldmi"}],["circle",{"cx":"12","cy":"4","r":"2","key":"muu5ef"}]])
export const Angle = ssrIcon('angle', [["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}],["path",{"d":"M3 11a10 10 0 0 1 10 10","key":"jhvw44"}]])
export const FaceAngry = ssrIcon('face-angry', [["path",{"d":"M15 12v-1.584","key":"1md67h"}],["path",{"d":"M17 10a5 5 0 00-3 1","key":"1dqs4m"}],["path",{"d":"M7 10a5 5 0 013 1","key":"1okmnq"}],["path",{"d":"M9 12v-1.584","key":"cfo04w"}],["path",{"d":"M9 17a5 5 0 016.001 0","key":"ipdrmp"}],["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}]])
export const FaceExpressionless = ssrIcon('face-expressionless', [["path",{"d":"M14 10h2","key":"1lstlu"}],["path",{"d":"M8 10h2","key":"66od0"}],["path",{"d":"M8 16h8","key":"10ke2u"}],["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}]])
export const Antenna = ssrIcon('antenna', [["path",{"d":"M2 12 7 2","key":"117k30"}],["path",{"d":"m7 12 5-10","key":"1tvx22"}],["path",{"d":"m12 12 5-10","key":"ev1o1a"}],["path",{"d":"m17 12 5-10","key":"1e4ti3"}],["path",{"d":"M4.5 7h15","key":"vlsxkz"}],["path",{"d":"M12 16v6","key":"c8a4gj"}]])
export const Anvil = ssrIcon('anvil', [["path",{"d":"M7 10H6a4 4 0 0 1-4-4 1 1 0 0 1 1-1h4","key":"1hjpb6"}],["path",{"d":"M7 5a1 1 0 0 1 1-1h13a1 1 0 0 1 1 1 7 7 0 0 1-7 7H8a1 1 0 0 1-1-1z","key":"1qn45f"}],["path",{"d":"M9 12v5","key":"3anwtq"}],["path",{"d":"M15 12v5","key":"5xh3zn"}],["path",{"d":"M5 20a3 3 0 0 1 3-3h8a3 3 0 0 1 3 3 1 1 0 0 1-1 1H6a1 1 0 0 1-1-1","key":"1fi4x8"}]])
export const Aperture = ssrIcon('aperture', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"m14.31 8 5.74 9.94","key":"1y6ab4"}],["path",{"d":"M9.69 8h11.48","key":"1wxppr"}],["path",{"d":"m7.38 12 5.74-9.94","key":"1grp0k"}],["path",{"d":"M9.69 16 3.95 6.06","key":"libnyf"}],["path",{"d":"M14.31 16H2.83","key":"x5fava"}],["path",{"d":"m16.62 12-5.74 9.94","key":"1vwawt"}]])
export const AppWindow = ssrIcon('app-window', [["rect",{"x":"2","y":"4","width":"20","height":"16","rx":"2","key":"izxlao"}],["path",{"d":"M10 4v4","key":"pp8u80"}],["path",{"d":"M2 8h20","key":"d11cs7"}],["path",{"d":"M6 4v4","key":"1svtjw"}]])
export const AppWindowMac = ssrIcon('app-window-mac', [["rect",{"width":"20","height":"16","x":"2","y":"4","rx":"2","key":"18n3k1"}],["path",{"d":"M6 8h.01","key":"x9i8wu"}],["path",{"d":"M10 8h.01","key":"1r9ogq"}],["path",{"d":"M14 8h.01","key":"1primd"}]])
export const Apple = ssrIcon('apple', [["path",{"d":"M12 6.528V3a1 1 0 0 1 1-1h0","key":"11qiee"}],["path",{"d":"M18.237 21A15 15 0 0 0 22 11a6 6 0 0 0-10-4.472A6 6 0 0 0 2 11a15.1 15.1 0 0 0 3.763 10 3 3 0 0 0 3.648.648 5.5 5.5 0 0 1 5.178 0A3 3 0 0 0 18.237 21","key":"110c12"}]])
export const Archive = ssrIcon('archive', [["rect",{"width":"20","height":"5","x":"2","y":"3","rx":"1","key":"1wp1u1"}],["path",{"d":"M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8","key":"1s80jp"}],["path",{"d":"M10 12h4","key":"a56b0p"}]])
export const ArchiveRestore = ssrIcon('archive-restore', [["rect",{"width":"20","height":"5","x":"2","y":"3","rx":"1","key":"1wp1u1"}],["path",{"d":"M4 8v11a2 2 0 0 0 2 2h2","key":"tvwodi"}],["path",{"d":"M20 8v11a2 2 0 0 1-2 2h-2","key":"1gkqxj"}],["path",{"d":"m9 15 3-3 3 3","key":"1pd0qc"}],["path",{"d":"M12 12v9","key":"192myk"}]])
export const ArchiveX = ssrIcon('archive-x', [["rect",{"width":"20","height":"5","x":"2","y":"3","rx":"1","key":"1wp1u1"}],["path",{"d":"M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8","key":"1s80jp"}],["path",{"d":"m9.5 17 5-5","key":"nakeu6"}],["path",{"d":"m9.5 12 5 5","key":"1hccrj"}]])
export const ChartArea = ssrIcon('chart-area', [["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}],["path",{"d":"M7 11.207a.5.5 0 0 1 .146-.353l2-2a.5.5 0 0 1 .708 0l3.292 3.292a.5.5 0 0 0 .708 0l4.292-4.292a.5.5 0 0 1 .854.353V16a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1z","key":"q0gr47"}]])
export const Armchair = ssrIcon('armchair', [["path",{"d":"M19 9V6a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v3","key":"irtipd"}],["path",{"d":"M3 16a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5a2 2 0 0 0-4 0v1.5a.5.5 0 0 1-.5.5h-9a.5.5 0 0 1-.5-.5V11a2 2 0 0 0-4 0z","key":"1qyhux"}],["path",{"d":"M5 18v2","key":"ppbyun"}],["path",{"d":"M19 18v2","key":"gy7782"}]])
export const ArrowBigDown = ssrIcon('arrow-big-down', [["path",{"d":"M9 5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v6a1 1 0 0 0 1 1h3.293a.707.707 0 0 1 .5 1.207l-7.086 7.086a1 1 0 0 1-1.414 0l-7.086-7.086a.707.707 0 0 1 .5-1.207H8a1 1 0 0 0 1-1z","key":"1o3tkq"}]])
export const ArrowBigDownDash = ssrIcon('arrow-big-down-dash', [["path",{"d":"M14 8a1 1 0 0 1 1 1v2a1 1 0 0 0 1 1h3.293a.707.707 0 0 1 .5 1.207l-6.939 6.939a1.207 1.207 0 0 1-1.708 0l-6.94-6.94a.707.707 0 0 1 .5-1.206H8a1 1 0 0 0 1-1V9a1 1 0 0 1 1-1z","key":"1b91ra"}],["path",{"d":"M9 4h6","key":"10am2s"}]])
export const ArrowBigLeft = ssrIcon('arrow-big-left', [["path",{"d":"M10.793 19.793a.707.707 0 0 0 1.207-.5V16a1 1 0 0 1 1-1h6a1 1 0 0 0 1-1v-4a1 1 0 0 0-1-1h-6a1 1 0 0 1-1-1V4.707a.707.707 0 0 0-1.207-.5l-6.94 6.94a1.207 1.207 0 0 0 0 1.707z","key":"qbhtmx"}]])
export const ArrowBigLeftDash = ssrIcon('arrow-big-left-dash', [["path",{"d":"M13 9a1 1 0 0 1-1-1V4.707a.707.707 0 0 0-1.207-.5l-6.94 6.94a1.207 1.207 0 0 0 0 1.707l6.94 6.94a.707.707 0 0 0 1.207-.5V16a1 1 0 0 1 1-1h2a1 1 0 0 0 1-1v-4a1 1 0 0 0-1-1z","key":"17jy80"}],["path",{"d":"M20 9v6","key":"14roy0"}]])
export const ArrowBigRight = ssrIcon('arrow-big-right', [["path",{"d":"M13.207 19.793a.707.707 0 0 1-1.207-.5V16a1 1 0 0 0-1-1H5a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1h6a1 1 0 0 0 1-1V4.707a.707.707 0 0 1 1.207-.5l6.94 6.94a1.207 1.207 0 0 1 0 1.707z","key":"zee3eo"}]])
export const ArrowBigRightDash = ssrIcon('arrow-big-right-dash', [["path",{"d":"M11 9a1 1 0 0 0 1-1V4.707a.707.707 0 0 1 1.207-.5l6.94 6.94a1.207 1.207 0 0 1 0 1.707l-6.94 6.94a.707.707 0 0 1-1.207-.5V16a1 1 0 0 0-1-1H9a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1z","key":"9idyso"}],["path",{"d":"M4 9v6","key":"bns7oa"}]])
export const ArrowBigUp = ssrIcon('arrow-big-up', [["path",{"d":"M9 19a1 1 0 0 0 1 1h4a1 1 0 0 0 1-1v-6a1 1 0 0 1 1-1h3.293a.707.707 0 0 0 .5-1.207l-7.086-7.086a1 1 0 0 0-1.414 0l-7.086 7.086a.707.707 0 0 0 .5 1.207H8a1 1 0 0 1 1 1z","key":"106j91"}]])
export const ArrowBigUpDash = ssrIcon('arrow-big-up-dash', [["path",{"d":"M14 16a1 1 0 0 0 1-1v-2a1 1 0 0 1 1-1h3.293a.707.707 0 0 0 .5-1.207l-6.939-6.939a1.207 1.207 0 0 0-1.708 0l-6.94 6.94a.707.707 0 0 0 .5 1.206H8a1 1 0 0 1 1 1v2a1 1 0 0 0 1 1z","key":"q57loy"}],["path",{"d":"M9 20h6","key":"s66wpe"}]])
export const ArrowDown = ssrIcon('arrow-down', [["path",{"d":"M12 5v14","key":"s699le"}],["path",{"d":"m19 12-7 7-7-7","key":"1idqje"}]])
export const ArrowDown01 = ssrIcon('arrow-down-0-1', [["path",{"d":"m3 16 4 4 4-4","key":"1co6wj"}],["path",{"d":"M7 20V4","key":"1yoxec"}],["rect",{"x":"15","y":"4","width":"4","height":"6","ry":"2","key":"1bwicg"}],["path",{"d":"M17 20v-6h-2","key":"1qp1so"}],["path",{"d":"M15 20h4","key":"1j968p"}]])
export const ArrowDown10 = ssrIcon('arrow-down-1-0', [["path",{"d":"m3 16 4 4 4-4","key":"1co6wj"}],["path",{"d":"M7 20V4","key":"1yoxec"}],["path",{"d":"M17 10V4h-2","key":"zcsr5x"}],["path",{"d":"M15 10h4","key":"id2lce"}],["rect",{"x":"15","y":"14","width":"4","height":"6","ry":"2","key":"33xykx"}]])
export const ArrowDownAZ = ssrIcon('arrow-down-a-z', [["path",{"d":"m3 16 4 4 4-4","key":"1co6wj"}],["path",{"d":"M7 20V4","key":"1yoxec"}],["path",{"d":"M20 8h-5","key":"1vsyxs"}],["path",{"d":"M15 10V6.5a2.5 2.5 0 0 1 5 0V10","key":"ag13bf"}],["path",{"d":"M15 14h5l-5 6h5","key":"ur5jdg"}]])
export const CircleArrowDown = ssrIcon('circle-arrow-down', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 8v8","key":"napkw2"}],["path",{"d":"m8 12 4 4 4-4","key":"k98ssh"}]])
export const ArrowDownFromLine = ssrIcon('arrow-down-from-line', [["path",{"d":"M19 3H5","key":"1236rx"}],["path",{"d":"M12 21V7","key":"gj6g52"}],["path",{"d":"m6 15 6 6 6-6","key":"h15q88"}]])
export const ArrowDownLeft = ssrIcon('arrow-down-left', [["path",{"d":"M17 7 7 17","key":"15tmo1"}],["path",{"d":"M17 17H7V7","key":"1org7z"}]])
export const CircleArrowOutDownLeft = ssrIcon('circle-arrow-out-down-left', [["path",{"d":"M2 12a10 10 0 1 1 10 10","key":"1yn6ov"}],["path",{"d":"m2 22 10-10","key":"28ilpk"}],["path",{"d":"M8 22H2v-6","key":"sulq54"}]])
export const SquareArrowOutDownLeft = ssrIcon('square-arrow-out-down-left', [["path",{"d":"M13 21h6a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v6","key":"14qz4y"}],["path",{"d":"m3 21 9-9","key":"1jfql5"}],["path",{"d":"M9 21H3v-6","key":"wtvkvv"}]])
export const SquareArrowDownLeft = ssrIcon('square-arrow-down-left', [["path",{"d":"M15 15H9l6-6","key":"1w52wt"}],["path",{"d":"M9 15V9","key":"1kwqze"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const ArrowDownNarrowWide = ssrIcon('arrow-down-narrow-wide', [["path",{"d":"m3 16 4 4 4-4","key":"1co6wj"}],["path",{"d":"M7 20V4","key":"1yoxec"}],["path",{"d":"M11 4h4","key":"6d7r33"}],["path",{"d":"M11 8h7","key":"djye34"}],["path",{"d":"M11 12h10","key":"1438ji"}]])
export const ArrowDownRight = ssrIcon('arrow-down-right', [["path",{"d":"m7 7 10 10","key":"1fmybs"}],["path",{"d":"M17 7v10H7","key":"6fjiku"}]])
export const CircleArrowOutDownRight = ssrIcon('circle-arrow-out-down-right', [["path",{"d":"M12 22a10 10 0 1 1 10-10","key":"130bv5"}],["path",{"d":"M22 22 12 12","key":"131aw7"}],["path",{"d":"M22 16v6h-6","key":"1gvm70"}]])
export const SquareArrowOutDownRight = ssrIcon('square-arrow-out-down-right', [["path",{"d":"M21 11V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h6","key":"14rsvq"}],["path",{"d":"m21 21-9-9","key":"1et2py"}],["path",{"d":"M21 15v6h-6","key":"1jko0i"}]])
export const SquareArrowDownRight = ssrIcon('square-arrow-down-right', [["path",{"d":"M15 15 9 9","key":"qb9ybb"}],["path",{"d":"M9 15h6V9","key":"1wezwn"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const SquareArrowDown = ssrIcon('square-arrow-down', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M12 8v8","key":"napkw2"}],["path",{"d":"m8 12 4 4 4-4","key":"k98ssh"}]])
export const ArrowDownToDot = ssrIcon('arrow-down-to-dot', [["path",{"d":"M12 2v14","key":"jyx4ut"}],["path",{"d":"m19 9-7 7-7-7","key":"1oe3oy"}],["circle",{"cx":"12","cy":"21","r":"1","key":"o0uj5v"}]])
export const ArrowDownToLine = ssrIcon('arrow-down-to-line', [["path",{"d":"M12 17V3","key":"1cwfxf"}],["path",{"d":"m6 11 6 6 6-6","key":"12ii2o"}],["path",{"d":"M19 21H5","key":"150jfl"}]])
export const ArrowDownUp = ssrIcon('arrow-down-up', [["path",{"d":"m3 16 4 4 4-4","key":"1co6wj"}],["path",{"d":"M7 20V4","key":"1yoxec"}],["path",{"d":"m21 8-4-4-4 4","key":"1c9v7m"}],["path",{"d":"M17 4v16","key":"7dpous"}]])
export const ArrowDownWideNarrow = ssrIcon('arrow-down-wide-narrow', [["path",{"d":"m3 16 4 4 4-4","key":"1co6wj"}],["path",{"d":"M7 20V4","key":"1yoxec"}],["path",{"d":"M11 4h10","key":"1w87gc"}],["path",{"d":"M11 8h7","key":"djye34"}],["path",{"d":"M11 12h4","key":"q8tih4"}]])
export const ArrowDownZA = ssrIcon('arrow-down-z-a', [["path",{"d":"m3 16 4 4 4-4","key":"1co6wj"}],["path",{"d":"M7 4v16","key":"1glfcx"}],["path",{"d":"M15 4h5l-5 6h5","key":"8asdl1"}],["path",{"d":"M15 20v-3.5a2.5 2.5 0 0 1 5 0V20","key":"r6l5cz"}],["path",{"d":"M20 18h-5","key":"18j1r2"}]])
export const ArrowLeft = ssrIcon('arrow-left', [["path",{"d":"m12 19-7-7 7-7","key":"1l729n"}],["path",{"d":"M19 12H5","key":"x3x0zl"}]])
export const CircleArrowLeft = ssrIcon('circle-arrow-left', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"m12 8-4 4 4 4","key":"15vm53"}],["path",{"d":"M16 12H8","key":"1fr5h0"}]])
export const ArrowLeftFromLine = ssrIcon('arrow-left-from-line', [["path",{"d":"m9 6-6 6 6 6","key":"7v63n9"}],["path",{"d":"M3 12h14","key":"13k4hi"}],["path",{"d":"M21 19V5","key":"b4bplr"}]])
export const ArrowLeftRight = ssrIcon('arrow-left-right', [["path",{"d":"M8 3 4 7l4 4","key":"9rb6wj"}],["path",{"d":"M4 7h16","key":"6tx8e3"}],["path",{"d":"m16 21 4-4-4-4","key":"siv7j2"}],["path",{"d":"M20 17H4","key":"h6l3hr"}]])
export const SquareArrowLeft = ssrIcon('square-arrow-left', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"m12 8-4 4 4 4","key":"15vm53"}],["path",{"d":"M16 12H8","key":"1fr5h0"}]])
export const ArrowLeftToLine = ssrIcon('arrow-left-to-line', [["path",{"d":"M3 19V5","key":"rwsyhb"}],["path",{"d":"m13 6-6 6 6 6","key":"1yhaz7"}],["path",{"d":"M7 12h14","key":"uoisry"}]])
export const ArrowRight = ssrIcon('arrow-right', [["path",{"d":"M5 12h14","key":"1ays0h"}],["path",{"d":"m12 5 7 7-7 7","key":"xquz4c"}]])
export const CircleArrowRight = ssrIcon('circle-arrow-right', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"m12 16 4-4-4-4","key":"1i9zcv"}],["path",{"d":"M8 12h8","key":"1wcyev"}]])
export const ArrowRightFromLine = ssrIcon('arrow-right-from-line', [["path",{"d":"M3 5v14","key":"1nt18q"}],["path",{"d":"M21 12H7","key":"13ipq5"}],["path",{"d":"m15 18 6-6-6-6","key":"6tx3qv"}]])
export const ArrowRightLeft = ssrIcon('arrow-right-left', [["path",{"d":"m16 3 4 4-4 4","key":"1x1c3m"}],["path",{"d":"M20 7H4","key":"zbl0bi"}],["path",{"d":"m8 21-4-4 4-4","key":"h9nckh"}],["path",{"d":"M4 17h16","key":"g4d7ey"}]])
export const SquareArrowRight = ssrIcon('square-arrow-right', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M8 12h8","key":"1wcyev"}],["path",{"d":"m12 16 4-4-4-4","key":"1i9zcv"}]])
export const ArrowRightToLine = ssrIcon('arrow-right-to-line', [["path",{"d":"M17 12H3","key":"8awo09"}],["path",{"d":"m11 18 6-6-6-6","key":"8c2y43"}],["path",{"d":"M21 5v14","key":"nzette"}]])
export const ArrowUp = ssrIcon('arrow-up', [["path",{"d":"m5 12 7-7 7 7","key":"hav0vg"}],["path",{"d":"M12 19V5","key":"x0mq9r"}]])
export const ArrowUp01 = ssrIcon('arrow-up-0-1', [["path",{"d":"m3 8 4-4 4 4","key":"11wl7u"}],["path",{"d":"M7 4v16","key":"1glfcx"}],["rect",{"x":"15","y":"4","width":"4","height":"6","ry":"2","key":"1bwicg"}],["path",{"d":"M17 20v-6h-2","key":"1qp1so"}],["path",{"d":"M15 20h4","key":"1j968p"}]])
export const ArrowUp10 = ssrIcon('arrow-up-1-0', [["path",{"d":"m3 8 4-4 4 4","key":"11wl7u"}],["path",{"d":"M7 4v16","key":"1glfcx"}],["path",{"d":"M17 10V4h-2","key":"zcsr5x"}],["path",{"d":"M15 10h4","key":"id2lce"}],["rect",{"x":"15","y":"14","width":"4","height":"6","ry":"2","key":"33xykx"}]])
export const ArrowUpAZ = ssrIcon('arrow-up-a-z', [["path",{"d":"m3 8 4-4 4 4","key":"11wl7u"}],["path",{"d":"M7 4v16","key":"1glfcx"}],["path",{"d":"M20 8h-5","key":"1vsyxs"}],["path",{"d":"M15 10V6.5a2.5 2.5 0 0 1 5 0V10","key":"ag13bf"}],["path",{"d":"M15 14h5l-5 6h5","key":"ur5jdg"}]])
export const CircleArrowUp = ssrIcon('circle-arrow-up', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"m16 12-4-4-4 4","key":"177agl"}],["path",{"d":"M12 16V8","key":"1sbj14"}]])
export const ArrowUpDown = ssrIcon('arrow-up-down', [["path",{"d":"m21 16-4 4-4-4","key":"f6ql7i"}],["path",{"d":"M17 20V4","key":"1ejh1v"}],["path",{"d":"m3 8 4-4 4 4","key":"11wl7u"}],["path",{"d":"M7 4v16","key":"1glfcx"}]])
export const ArrowUpFromDot = ssrIcon('arrow-up-from-dot', [["path",{"d":"m5 9 7-7 7 7","key":"1hw5ic"}],["path",{"d":"M12 16V2","key":"ywoabb"}],["circle",{"cx":"12","cy":"21","r":"1","key":"o0uj5v"}]])
export const ArrowUpFromLine = ssrIcon('arrow-up-from-line', [["path",{"d":"m18 9-6-6-6 6","key":"kcunyi"}],["path",{"d":"M12 3v14","key":"7cf3v8"}],["path",{"d":"M5 21h14","key":"11awu3"}]])
export const ArrowUpLeft = ssrIcon('arrow-up-left', [["path",{"d":"M7 17V7h10","key":"11bw93"}],["path",{"d":"M17 17 7 7","key":"2786uv"}]])
export const CircleArrowOutUpLeft = ssrIcon('circle-arrow-out-up-left', [["path",{"d":"M2 8V2h6","key":"hiwtdz"}],["path",{"d":"m2 2 10 10","key":"1oh8rs"}],["path",{"d":"M12 2A10 10 0 1 1 2 12","key":"rrk4fa"}]])
export const SquareArrowOutUpLeft = ssrIcon('square-arrow-out-up-left', [["path",{"d":"M13 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-6","key":"14mv1t"}],["path",{"d":"m3 3 9 9","key":"rks13r"}],["path",{"d":"M3 9V3h6","key":"ira0h2"}]])
export const SquareArrowUpLeft = ssrIcon('square-arrow-up-left', [["path",{"d":"M15 15 9 9","key":"qb9ybb"}],["path",{"d":"M9 15V9h6","key":"1pdr5l"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const ArrowUpNarrowWide = ssrIcon('arrow-up-narrow-wide', [["path",{"d":"m3 8 4-4 4 4","key":"11wl7u"}],["path",{"d":"M7 4v16","key":"1glfcx"}],["path",{"d":"M11 12h4","key":"q8tih4"}],["path",{"d":"M11 16h7","key":"uosisv"}],["path",{"d":"M11 20h10","key":"jvxblo"}]])
export const ArrowUpRight = ssrIcon('arrow-up-right', [["path",{"d":"M7 7h10v10","key":"1tivn9"}],["path",{"d":"M7 17 17 7","key":"1vkiza"}]])
export const CircleArrowOutUpRight = ssrIcon('circle-arrow-out-up-right', [["path",{"d":"M22 12A10 10 0 1 1 12 2","key":"1fm58d"}],["path",{"d":"M22 2 12 12","key":"yg2myt"}],["path",{"d":"M16 2h6v6","key":"zan5cs"}]])
export const SquareArrowOutUpRight = ssrIcon('square-arrow-out-up-right', [["path",{"d":"M21 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h6","key":"y09zxi"}],["path",{"d":"m21 3-9 9","key":"mpx6sq"}],["path",{"d":"M15 3h6v6","key":"1q9fwt"}]])
export const SquareArrowUpRight = ssrIcon('square-arrow-up-right', [["path",{"d":"M15 15V9H9","key":"vxyd2h"}],["path",{"d":"m9 15 6-6","key":"1ygkhp"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const SquareArrowUp = ssrIcon('square-arrow-up', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"m16 12-4-4-4 4","key":"177agl"}],["path",{"d":"M12 16V8","key":"1sbj14"}]])
export const ArrowUpToLine = ssrIcon('arrow-up-to-line', [["path",{"d":"M5 3h14","key":"7usisc"}],["path",{"d":"m18 13-6-6-6 6","key":"1kf1n9"}],["path",{"d":"M12 7v14","key":"1akyts"}]])
export const ArrowUpWideNarrow = ssrIcon('arrow-up-wide-narrow', [["path",{"d":"m3 8 4-4 4 4","key":"11wl7u"}],["path",{"d":"M7 4v16","key":"1glfcx"}],["path",{"d":"M11 12h10","key":"1438ji"}],["path",{"d":"M11 16h7","key":"uosisv"}],["path",{"d":"M11 20h4","key":"1krc32"}]])
export const ArrowUpZA = ssrIcon('arrow-up-z-a', [["path",{"d":"m3 8 4-4 4 4","key":"11wl7u"}],["path",{"d":"M7 4v16","key":"1glfcx"}],["path",{"d":"M15 4h5l-5 6h5","key":"8asdl1"}],["path",{"d":"M15 20v-3.5a2.5 2.5 0 0 1 5 0V20","key":"r6l5cz"}],["path",{"d":"M20 18h-5","key":"18j1r2"}]])
export const ArrowsUpFromLine = ssrIcon('arrows-up-from-line', [["path",{"d":"m4 6 3-3 3 3","key":"9aidw8"}],["path",{"d":"M7 17V3","key":"19qxw1"}],["path",{"d":"m14 6 3-3 3 3","key":"6iy689"}],["path",{"d":"M17 17V3","key":"o0fmgi"}],["path",{"d":"M4 21h16","key":"1h09gz"}]])
export const Asterisk = ssrIcon('asterisk', [["path",{"d":"M12 5v14","key":"s699le"}],["path",{"d":"m18.065 8.496-12.125 7","key":"1h26g9"}],["path",{"d":"m5.94 8.504 12.125 7","key":"k77sdm"}]])
export const SquareAsterisk = ssrIcon('square-asterisk', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M12 8v8","key":"napkw2"}],["path",{"d":"m8.5 14 7-4","key":"12hpby"}],["path",{"d":"m8.5 10 7 4","key":"wwy2dy"}]])
export const Astroid = ssrIcon('astroid', [["path",{"d":"M12.983 21.186a1 1 0 0 1-1.966 0 10 10 0 0 0-8.203-8.203 1 1 0 0 1 0-1.966 10 10 0 0 0 8.203-8.203 1 1 0 0 1 1.966 0 10 10 0 0 0 8.203 8.203 1 1 0 0 1 0 1.966 10 10 0 0 0-8.203 8.203","key":"1tipus"}]])
export const AtSign = ssrIcon('at-sign', [["circle",{"cx":"12","cy":"12","r":"4","key":"4exip2"}],["path",{"d":"M16 8v5a3 3 0 0 0 6 0v-1a10 10 0 1 0-4 8","key":"7n84p3"}]])
export const Atom = ssrIcon('atom', [["circle",{"cx":"12","cy":"12","r":"1","key":"41hilf"}],["path",{"d":"M20.2 20.2c2.04-2.03.02-7.36-4.5-11.9-4.54-4.52-9.87-6.54-11.9-4.5-2.04 2.03-.02 7.36 4.5 11.9 4.54 4.52 9.87 6.54 11.9 4.5Z","key":"1l2ple"}],["path",{"d":"M15.7 15.7c4.52-4.54 6.54-9.87 4.5-11.9-2.03-2.04-7.36-.02-11.9 4.5-4.52 4.54-6.54 9.87-4.5 11.9 2.03 2.04 7.36.02 11.9-4.5Z","key":"1wam0m"}]])
export const AudioLines = ssrIcon('audio-lines', [["path",{"d":"M2 10v3","key":"1fnikh"}],["path",{"d":"M6 6v11","key":"11sgs0"}],["path",{"d":"M10 3v18","key":"yhl04a"}],["path",{"d":"M14 8v7","key":"3a1oy3"}],["path",{"d":"M18 5v13","key":"123xd1"}],["path",{"d":"M22 10v3","key":"154ddg"}]])
export const AudioLinesOff = ssrIcon('audio-lines-off', [["path",{"d":"M10 10v11","key":"tkf9cx"}],["path",{"d":"M10 3v1.35","key":"1rsffz"}],["path",{"d":"M14 14v1","key":"hsexio"}],["path",{"d":"M14 8v.35","key":"isohmc"}],["path",{"d":"M18 5v7.35","key":"1b0cqo"}],["path",{"d":"M2 10v3","key":"1fnikh"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M22 10v3","key":"154ddg"}],["path",{"d":"M6 6v11","key":"11sgs0"}]])
export const AudioLinesX = ssrIcon('audio-lines-x', [["path",{"d":"M10 3v18","key":"yhl04a"}],["path",{"d":"M14 8v6.35","key":"1ubbml"}],["path",{"d":"m17 17 5 5","key":"p7ous7"}],["path",{"d":"M18 5v8.1","key":"1icuhc"}],["path",{"d":"M2 10v3","key":"1fnikh"}],["path",{"d":"M22 10v3","key":"154ddg"}],["path",{"d":"m22 17-5 5","key":"gqnmv0"}],["path",{"d":"M6 6v11","key":"11sgs0"}]])
export const AudioWaveform = ssrIcon('audio-waveform', [["path",{"d":"M2 13a2 2 0 0 0 2-2V7a2 2 0 0 1 4 0v13a2 2 0 0 0 4 0V4a2 2 0 0 1 4 0v13a2 2 0 0 0 4 0v-4a2 2 0 0 1 2-2","key":"57tc96"}]])
export const Award = ssrIcon('award', [["path",{"d":"m15.477 12.89 1.515 8.526a.5.5 0 0 1-.81.47l-3.58-2.687a1 1 0 0 0-1.197 0l-3.586 2.686a.5.5 0 0 1-.81-.469l1.514-8.526","key":"1yiouv"}],["circle",{"cx":"12","cy":"8","r":"6","key":"1vp47v"}]])
export const Axe = ssrIcon('axe', [["path",{"d":"m14 12-8.381 8.38a1 1 0 0 1-3.001-3L11 9","key":"5z9253"}],["path",{"d":"M15 15.5a.5.5 0 0 0 .5.5A6.5 6.5 0 0 0 22 9.5a.5.5 0 0 0-.5-.5h-1.672a2 2 0 0 1-1.414-.586l-5.062-5.062a1.205 1.205 0 0 0-1.704 0L9.352 5.648a1.205 1.205 0 0 0 0 1.704l5.062 5.062A2 2 0 0 1 15 13.828z","key":"19zklq"}]])
export const Axis3d = ssrIcon('axis-3d', [["path",{"d":"M13.5 10.5 15 9","key":"1nsxvm"}],["path",{"d":"M4 4v15a1 1 0 0 0 1 1h15","key":"1w6lkd"}],["path",{"d":"M4.293 19.707 6 18","key":"3g1p8c"}],["path",{"d":"m9 15 1.5-1.5","key":"1xfbes"}]])
export const Baby = ssrIcon('baby', [["path",{"d":"M10 16c.5.3 1.2.5 2 .5s1.5-.2 2-.5","key":"1u7htd"}],["path",{"d":"M15 12h.01","key":"1k8ypt"}],["path",{"d":"M19.38 6.813A9 9 0 0 1 20.8 10.2a2 2 0 0 1 0 3.6 9 9 0 0 1-17.6 0 2 2 0 0 1 0-3.6A9 9 0 0 1 12 3c2 0 3.5 1.1 3.5 2.5s-.9 2.5-2 2.5c-.8 0-1.5-.4-1.5-1","key":"11xh7x"}],["path",{"d":"M9 12h.01","key":"157uk2"}]])
export const Backpack = ssrIcon('backpack', [["path",{"d":"M4 10a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z","key":"1ol0lm"}],["path",{"d":"M8 10h8","key":"c7uz4u"}],["path",{"d":"M8 18h8","key":"1no2b1"}],["path",{"d":"M8 22v-6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v6","key":"1fr6do"}],["path",{"d":"M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2","key":"donm21"}]])
export const Badge = ssrIcon('badge', [["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z","key":"3c2336"}]])
export const BadgeAlert = ssrIcon('badge-alert', [["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z","key":"3c2336"}],["line",{"x1":"12","x2":"12","y1":"8","y2":"12","key":"1pkeuh"}],["line",{"x1":"12","x2":"12.01","y1":"16","y2":"16","key":"4dfq90"}]])
export const BadgeCent = ssrIcon('badge-cent', [["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z","key":"3c2336"}],["path",{"d":"M12 7v10","key":"jspqdw"}],["path",{"d":"M15.4 10a4 4 0 1 0 0 4","key":"2eqtx8"}]])
export const BadgeCheck = ssrIcon('badge-check', [["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z","key":"3c2336"}],["path",{"d":"m16 9-5.5 5.5L8 12","key":"xofnsj"}]])
export const BadgeDollarSign = ssrIcon('badge-dollar-sign', [["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z","key":"3c2336"}],["path",{"d":"M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8","key":"1h4pet"}],["path",{"d":"M12 18V6","key":"zqpxq5"}]])
export const BadgeEuro = ssrIcon('badge-euro', [["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z","key":"3c2336"}],["path",{"d":"M7 12h5","key":"gblrwe"}],["path",{"d":"M15 9.4a4 4 0 1 0 0 5.2","key":"1makmb"}]])
export const BadgeQuestionMark = ssrIcon('badge-question-mark', [["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z","key":"3c2336"}],["path",{"d":"M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3","key":"1u773s"}],["line",{"x1":"12","x2":"12.01","y1":"17","y2":"17","key":"io3f8k"}]])
export const BadgeIndianRupee = ssrIcon('badge-indian-rupee', [["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z","key":"3c2336"}],["path",{"d":"M8 8h8","key":"1bis0t"}],["path",{"d":"M8 12h8","key":"1wcyev"}],["path",{"d":"m13 17-5-1h1a4 4 0 0 0 0-8","key":"nu2bwa"}]])
export const BadgeInfo = ssrIcon('badge-info', [["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z","key":"3c2336"}],["line",{"x1":"12","x2":"12","y1":"16","y2":"12","key":"1y1yb1"}],["line",{"x1":"12","x2":"12.01","y1":"8","y2":"8","key":"110wyk"}]])
export const BadgeJapaneseYen = ssrIcon('badge-japanese-yen', [["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z","key":"3c2336"}],["path",{"d":"m9 8 3 3v7","key":"17yadx"}],["path",{"d":"m12 11 3-3","key":"p4cfq1"}],["path",{"d":"M9 12h6","key":"1c52cq"}],["path",{"d":"M9 16h6","key":"8wimt3"}]])
export const BadgeMinus = ssrIcon('badge-minus', [["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z","key":"3c2336"}],["line",{"x1":"8","x2":"16","y1":"12","y2":"12","key":"1jonct"}]])
export const BadgePercent = ssrIcon('badge-percent', [["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z","key":"3c2336"}],["path",{"d":"m15 9-6 6","key":"1uzhvr"}],["path",{"d":"M9 9h.01","key":"1q5me6"}],["path",{"d":"M15 15h.01","key":"lqbp3k"}]])
export const BadgePlus = ssrIcon('badge-plus', [["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z","key":"3c2336"}],["line",{"x1":"12","x2":"12","y1":"8","y2":"16","key":"10p56q"}],["line",{"x1":"8","x2":"16","y1":"12","y2":"12","key":"1jonct"}]])
export const BadgePoundSterling = ssrIcon('badge-pound-sterling', [["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z","key":"3c2336"}],["path",{"d":"M8 12h4","key":"qz6y1c"}],["path",{"d":"M10 16V9.5a2.5 2.5 0 0 1 5 0","key":"3mlbjk"}],["path",{"d":"M8 16h7","key":"sbedsn"}]])
export const BadgeRussianRuble = ssrIcon('badge-russian-ruble', [["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z","key":"3c2336"}],["path",{"d":"M9 16h5","key":"1syiyw"}],["path",{"d":"M9 12h5a2 2 0 1 0 0-4h-3v9","key":"1ge9c1"}]])
export const BadgeSwissFranc = ssrIcon('badge-swiss-franc', [["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z","key":"3c2336"}],["path",{"d":"M11 17V8h4","key":"1bfq6y"}],["path",{"d":"M11 12h3","key":"2eqnfz"}],["path",{"d":"M9 16h4","key":"1skf3a"}]])
export const BadgeTurkishLira = ssrIcon('badge-turkish-lira', [["path",{"d":"M11 7v10a5 5 0 0 0 5-5","key":"1ja3ih"}],["path",{"d":"m15 8-6 3","key":"4x0uwz"}],["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76","key":"18242g"}]])
export const BadgeX = ssrIcon('badge-x', [["path",{"d":"M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z","key":"3c2336"}],["line",{"x1":"15","x2":"9","y1":"9","y2":"15","key":"f7djnv"}],["line",{"x1":"9","x2":"15","y1":"9","y2":"15","key":"1shsy8"}]])
export const BaggageClaim = ssrIcon('baggage-claim', [["path",{"d":"M22 18H6a2 2 0 0 1-2-2V7a2 2 0 0 0-2-2","key":"4irg2o"}],["path",{"d":"M17 14V4a2 2 0 0 0-2-2h-1a2 2 0 0 0-2 2v10","key":"14fcyx"}],["rect",{"width":"13","height":"8","x":"8","y":"6","rx":"1","key":"o6oiis"}],["circle",{"cx":"18","cy":"20","r":"2","key":"t9985n"}],["circle",{"cx":"9","cy":"20","r":"2","key":"e5v82j"}]])
export const Balloon = ssrIcon('balloon', [["path",{"d":"M12 16v1a2 2 0 0 0 2 2h1a2 2 0 0 1 2 2v1","key":"2nz4b"}],["path",{"d":"M12 6a2 2 0 0 1 2 2","key":"7y7d82"}],["path",{"d":"M18 8c0 4-3.5 8-6 8s-6-4-6-8a6 6 0 0 1 12 0","key":"vqb5s3"}]])
export const Ban = ssrIcon('ban', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M4.929 4.929 19.07 19.071","key":"196cmz"}]])
export const Banana = ssrIcon('banana', [["path",{"d":"M4 13c3.5-2 8-2 10 2a5.5 5.5 0 0 1 8 5","key":"1cscit"}],["path",{"d":"M5.15 17.89c5.52-1.52 8.65-6.89 7-12C11.55 4 11.5 2 13 2c3.22 0 5 5.5 5 8 0 6.5-4.2 12-10.49 12C5.11 22 2 22 2 20c0-1.5 1.14-1.55 3.15-2.11Z","key":"1y1nbv"}]])
export const Bandage = ssrIcon('bandage', [["path",{"d":"M10 10.01h.01","key":"1e9xi7"}],["path",{"d":"M10 14.01h.01","key":"ac23bv"}],["path",{"d":"M14 10.01h.01","key":"2wfrvf"}],["path",{"d":"M14 14.01h.01","key":"8tw8yn"}],["path",{"d":"M18 6v12","key":"1bcixs"}],["path",{"d":"M6 6v12","key":"vkc79e"}],["rect",{"x":"2","y":"6","width":"20","height":"12","rx":"2","key":"1wpnh2"}]])
export const Banknote = ssrIcon('banknote', [["rect",{"width":"20","height":"12","x":"2","y":"6","rx":"2","key":"9lu3g6"}],["circle",{"cx":"12","cy":"12","r":"2","key":"1c9p78"}],["path",{"d":"M6 12h.01M18 12h.01","key":"113zkx"}]])
export const BanknoteArrowDown = ssrIcon('banknote-arrow-down', [["path",{"d":"M12 18H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5","key":"x6cv4u"}],["path",{"d":"m16 19 3 3 3-3","key":"1ibux0"}],["path",{"d":"M18 12h.01","key":"yjnet6"}],["path",{"d":"M19 16v6","key":"tddt3s"}],["path",{"d":"M6 12h.01","key":"c2rlol"}],["circle",{"cx":"12","cy":"12","r":"2","key":"1c9p78"}]])
export const BanknoteArrowUp = ssrIcon('banknote-arrow-up', [["path",{"d":"M12 18H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5","key":"x6cv4u"}],["path",{"d":"M18 12h.01","key":"yjnet6"}],["path",{"d":"M19 22v-6","key":"qhmiwi"}],["path",{"d":"m22 19-3-3-3 3","key":"rn6bg2"}],["path",{"d":"M6 12h.01","key":"c2rlol"}],["circle",{"cx":"12","cy":"12","r":"2","key":"1c9p78"}]])
export const BanknoteCheck = ssrIcon('banknote-check', [["path",{"d":"M11.748 18H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v4.875","key":"t4e5a5"}],["path",{"d":"m16 19 2 2 4-4","key":"1b14m6"}],["path",{"d":"M18 12h.01","key":"yjnet6"}],["path",{"d":"M6 12h.01","key":"c2rlol"}],["circle",{"cx":"12","cy":"12","r":"2","key":"1c9p78"}]])
export const BanknoteX = ssrIcon('banknote-x', [["path",{"d":"M13 18H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5","key":"16nib6"}],["path",{"d":"m17 17 5 5","key":"p7ous7"}],["path",{"d":"M18 12h.01","key":"yjnet6"}],["path",{"d":"m22 17-5 5","key":"gqnmv0"}],["path",{"d":"M6 12h.01","key":"c2rlol"}],["circle",{"cx":"12","cy":"12","r":"2","key":"1c9p78"}]])
export const ChartNoAxesColumnIncreasing = ssrIcon('chart-no-axes-column-increasing', [["path",{"d":"M5 21v-6","key":"1hz6c0"}],["path",{"d":"M12 21V9","key":"uvy0l4"}],["path",{"d":"M19 21V3","key":"11j9sm"}]])
export const ChartNoAxesColumn = ssrIcon('chart-no-axes-column', [["path",{"d":"M5 21v-6","key":"1hz6c0"}],["path",{"d":"M12 21V3","key":"1lcnhd"}],["path",{"d":"M19 21V9","key":"unv183"}]])
export const ChartColumn = ssrIcon('chart-column', [["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}],["path",{"d":"M18 17V9","key":"2bz60n"}],["path",{"d":"M13 17V5","key":"1frdt8"}],["path",{"d":"M8 17v-3","key":"17ska0"}]])
export const ChartColumnIncreasing = ssrIcon('chart-column-increasing', [["path",{"d":"M13 17V9","key":"1fwyjl"}],["path",{"d":"M18 17V5","key":"sfb6ij"}],["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}],["path",{"d":"M8 17v-3","key":"17ska0"}]])
export const ChartColumnBig = ssrIcon('chart-column-big', [["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}],["rect",{"x":"15","y":"5","width":"4","height":"12","rx":"1","key":"q8uenq"}],["rect",{"x":"7","y":"8","width":"4","height":"9","rx":"1","key":"sr5ea"}]])
export const ChartBar = ssrIcon('chart-bar', [["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}],["path",{"d":"M7 16h8","key":"srdodz"}],["path",{"d":"M7 11h12","key":"127s9w"}],["path",{"d":"M7 6h3","key":"w9rmul"}]])
export const ChartBarBig = ssrIcon('chart-bar-big', [["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}],["rect",{"x":"7","y":"13","width":"9","height":"4","rx":"1","key":"1iip1u"}],["rect",{"x":"7","y":"5","width":"12","height":"4","rx":"1","key":"1anskk"}]])
export const Barcode = ssrIcon('barcode', [["path",{"d":"M3 5v14","key":"1nt18q"}],["path",{"d":"M8 5v14","key":"1ybrkv"}],["path",{"d":"M12 5v14","key":"s699le"}],["path",{"d":"M17 5v14","key":"ycjyhj"}],["path",{"d":"M21 5v14","key":"nzette"}]])
export const Barrel = ssrIcon('barrel', [["path",{"d":"M10 3a41 41 0 000 18","key":"1f9k6x"}],["path",{"d":"M14 3a41 41 0 010 18","key":"1qo28r"}],["path",{"d":"M16.997 21a2 2 0 001.68-.92 15.25 15.25 0 000-16.16 2 2 0 00-1.68-.92h-10a2 2 0 00-1.681.92 15.25 15.25 0 000 16.16 2 2 0 001.681.92z","key":"1nrwe5"}],["path",{"d":"M3.54 16h16.914","key":"jntgtt"}],["path",{"d":"M3.54 8h16.914","key":"14pf7i"}]])
export const Baseline = ssrIcon('baseline', [["path",{"d":"M4 20h16","key":"14thso"}],["path",{"d":"m6 16 6-12 6 12","key":"1b4byz"}],["path",{"d":"M8 12h8","key":"1wcyev"}]])
export const Bath = ssrIcon('bath', [["path",{"d":"M10 4 8 6","key":"1rru8s"}],["path",{"d":"M17 19v2","key":"ts1sot"}],["path",{"d":"M2 12h20","key":"9i4pu4"}],["path",{"d":"M7 19v2","key":"12npes"}],["path",{"d":"M9 5 7.621 3.621A2.121 2.121 0 0 0 4 5v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5","key":"14ym8i"}]])
export const Battery = ssrIcon('battery', [["path",{"d":"M 22 14 L 22 10","key":"nqc4tb"}],["rect",{"x":"2","y":"6","width":"16","height":"12","rx":"2","key":"13zb55"}]])
export const BatteryCharging = ssrIcon('battery-charging', [["path",{"d":"m11 7-3 5h4l-3 5","key":"b4a64w"}],["path",{"d":"M14.856 6H16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.935","key":"lre1cr"}],["path",{"d":"M22 14v-4","key":"14q9d5"}],["path",{"d":"M5.14 18H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h2.936","key":"13q5k0"}]])
export const BatteryFull = ssrIcon('battery-full', [["path",{"d":"M10 10v4","key":"1mb2ec"}],["path",{"d":"M14 10v4","key":"1nt88p"}],["path",{"d":"M22 14v-4","key":"14q9d5"}],["path",{"d":"M6 10v4","key":"1n77qd"}],["rect",{"x":"2","y":"6","width":"16","height":"12","rx":"2","key":"13zb55"}]])
export const BatteryLow = ssrIcon('battery-low', [["path",{"d":"M22 14v-4","key":"14q9d5"}],["path",{"d":"M6 14v-4","key":"14a6bd"}],["rect",{"x":"2","y":"6","width":"16","height":"12","rx":"2","key":"13zb55"}]])
export const BatteryMedium = ssrIcon('battery-medium', [["path",{"d":"M10 14v-4","key":"suye4c"}],["path",{"d":"M22 14v-4","key":"14q9d5"}],["path",{"d":"M6 14v-4","key":"14a6bd"}],["rect",{"x":"2","y":"6","width":"16","height":"12","rx":"2","key":"13zb55"}]])
export const BatteryPlus = ssrIcon('battery-plus', [["path",{"d":"M10 9v6","key":"17i7lo"}],["path",{"d":"M12.543 6H16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-3.605","key":"o09yah"}],["path",{"d":"M22 14v-4","key":"14q9d5"}],["path",{"d":"M7 12h6","key":"iekk3h"}],["path",{"d":"M7.606 18H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h3.606","key":"xyqvf1"}]])
export const BatteryWarning = ssrIcon('battery-warning', [["path",{"d":"M10 17h.01","key":"nbq80n"}],["path",{"d":"M10 7v6","key":"nne03l"}],["path",{"d":"M14 6h2a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2","key":"1m83kb"}],["path",{"d":"M22 14v-4","key":"14q9d5"}],["path",{"d":"M6 18H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h2","key":"h8lgfh"}]])
export const Beaker = ssrIcon('beaker', [["path",{"d":"M4.5 3h15","key":"c7n0jr"}],["path",{"d":"M6 3v16a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V3","key":"m1uhx7"}],["path",{"d":"M6 14h12","key":"4cwo0f"}]])
export const Bean = ssrIcon('bean', [["path",{"d":"M10.165 6.598C9.954 7.478 9.64 8.36 9 9c-.64.64-1.521.954-2.402 1.165A6 6 0 0 0 8 22c7.732 0 14-6.268 14-14a6 6 0 0 0-11.835-1.402Z","key":"1tvzk7"}],["path",{"d":"M5.341 10.62a4 4 0 1 0 5.279-5.28","key":"2cyri2"}]])
export const BeanOff = ssrIcon('bean-off', [["path",{"d":"M9 9c-.64.64-1.521.954-2.402 1.165A6 6 0 0 0 8 22a13.96 13.96 0 0 0 9.9-4.1","key":"bq3udt"}],["path",{"d":"M10.75 5.093A6 6 0 0 1 22 8c0 2.411-.61 4.68-1.683 6.66","key":"17ccse"}],["path",{"d":"M5.341 10.62a4 4 0 0 0 6.487 1.208M10.62 5.341a4.015 4.015 0 0 1 2.039 2.04","key":"18zqgq"}],["line",{"x1":"2","x2":"22","y1":"2","y2":"22","key":"a6p6uj"}]])
export const Bed = ssrIcon('bed', [["path",{"d":"M2 4v16","key":"vw9hq8"}],["path",{"d":"M2 8h18a2 2 0 0 1 2 2v10","key":"1dgv2r"}],["path",{"d":"M2 17h20","key":"18nfp3"}],["path",{"d":"M6 8v9","key":"1yriud"}]])
export const BedDouble = ssrIcon('bed-double', [["path",{"d":"M2 20v-8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v8","key":"1k78r4"}],["path",{"d":"M4 10V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v4","key":"fb3tl2"}],["path",{"d":"M12 4v6","key":"1dcgq2"}],["path",{"d":"M2 18h20","key":"ajqnye"}]])
export const BedSingle = ssrIcon('bed-single', [["path",{"d":"M3 20v-8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v8","key":"1wm6mi"}],["path",{"d":"M5 10V6a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v4","key":"4k93s5"}],["path",{"d":"M3 18h18","key":"1h113x"}]])
export const Beef = ssrIcon('beef', [["path",{"d":"M16.4 13.7A6.5 6.5 0 1 0 6.28 6.6c-1.1 3.13-.78 3.9-3.18 6.08A3 3 0 0 0 5 18c4 0 8.4-1.8 11.4-4.3","key":"cisjcv"}],["path",{"d":"m18.5 6 1.754 3.5a6.48 6.48 0 0 1-1.854 8.2C15.4 20.2 11 22 7 22a3 3 0 0 1-2.68-1.66L2.4 16.5","key":"hvizuk"}],["circle",{"cx":"12.5","cy":"8.5","r":"2.5","key":"9738u8"}]])
export const BeefOff = ssrIcon('beef-off', [["path",{"d":"M11.771 6.109a2.5 2.5 0 0 1 3.12 3.12","key":"3w1grc"}],["path",{"d":"M17.852 12.185a6.5 6.5 0 0 0-9.035-9.04","key":"1xgl7b"}],["path",{"d":"M18.013 18.013C15.029 20.349 10.831 22 7 22a3 3 0 0 1-2.68-1.66L2.4 16.5","key":"3m3yc0"}],["path",{"d":"m18.5 6 2.19 4.5a6.48 6.48 0 0 1-.139 4.393","key":"1rvkn7"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M6.355 6.37a7 7 0 0 0-.075.23c-1.1 3.13-.78 3.9-3.18 6.08A3 3 0 0 0 5 18c3.356 0 6.993-1.267 9.85-3.151","key":"54713r"}]])
export const Beer = ssrIcon('beer', [["path",{"d":"M17 11h1a3 3 0 0 1 0 6h-1","key":"1yp76v"}],["path",{"d":"M9 12v6","key":"1u1cab"}],["path",{"d":"M13 12v6","key":"1sugkk"}],["path",{"d":"M14 7.5c-1 0-1.44.5-3 .5s-2-.5-3-.5-1.72.5-2.5.5a2.5 2.5 0 0 1 0-5c.78 0 1.57.5 2.5.5S9.44 2 11 2s2 1.5 3 1.5 1.72-.5 2.5-.5a2.5 2.5 0 0 1 0 5c-.78 0-1.5-.5-2.5-.5Z","key":"1510fo"}],["path",{"d":"M5 8v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V8","key":"19jb7n"}]])
export const BeerOff = ssrIcon('beer-off', [["path",{"d":"M13 13v5","key":"igwfh0"}],["path",{"d":"M17 11.47V8","key":"16yw0g"}],["path",{"d":"M17 11h1a3 3 0 0 1 2.745 4.211","key":"1xbt65"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M5 8v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-3","key":"c55o3e"}],["path",{"d":"M7.536 7.535C6.766 7.649 6.154 8 5.5 8a2.5 2.5 0 0 1-1.768-4.268","key":"1ydug7"}],["path",{"d":"M8.727 3.204C9.306 2.767 9.885 2 11 2c1.56 0 2 1.5 3 1.5s1.72-.5 2.5-.5a1 1 0 1 1 0 5c-.78 0-1.5-.5-2.5-.5a3.149 3.149 0 0 0-.842.12","key":"q81o7q"}],["path",{"d":"M9 14.6V18","key":"20ek98"}]])
export const Bell = ssrIcon('bell', [["path",{"d":"M10.268 21a2 2 0 0 0 3.464 0","key":"vwvbt9"}],["path",{"d":"M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326","key":"11g9vi"}]])
export const BellCheck = ssrIcon('bell-check', [["path",{"d":"M10.268 21a2 2 0 0 0 3.464 0","key":"vwvbt9"}],["path",{"d":"m15 8 2 2 4-4","key":"sbrgsm"}],["path",{"d":"M16.8607 4.4824A6 6 0 0 0 6 8C6 12.499 4.589 13.956 3.262 15.326","key":"qcog4a"}],["path",{"d":"M3.262 15.326A1 1 0 0 0 4 17H20A1 1 0 0 0 20.74 15.327C20.209 14.779 19.665 14.218 19.203 13.454","key":"mxnnoh"}]])
export const BellDot = ssrIcon('bell-dot', [["path",{"d":"M10.268 21a2 2 0 0 0 3.464 0","key":"vwvbt9"}],["path",{"d":"M11.68 2.009A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673c-.824-.85-1.678-1.731-2.21-3.348","key":"xaq59h"}],["circle",{"cx":"18","cy":"5","r":"3","key":"gq8acd"}]])
export const BellElectric = ssrIcon('bell-electric', [["path",{"d":"M18.518 17.347A7 7 0 0 1 14 19","key":"1emhpo"}],["path",{"d":"M18.8 4A11 11 0 0 1 20 9","key":"127b67"}],["path",{"d":"M9 9h.01","key":"1q5me6"}],["circle",{"cx":"20","cy":"16","r":"2","key":"1v9bxh"}],["circle",{"cx":"9","cy":"9","r":"7","key":"p2h5vp"}],["rect",{"x":"4","y":"16","width":"10","height":"6","rx":"2","key":"bfnviv"}]])
export const BellMinus = ssrIcon('bell-minus', [["path",{"d":"M10.268 21a2 2 0 0 0 3.464 0","key":"vwvbt9"}],["path",{"d":"M15 8h6","key":"8ybuxh"}],["path",{"d":"M16.243 3.757A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673A9.4 9.4 0 0 1 18.667 12","key":"bdwj86"}]])
export const BellOff = ssrIcon('bell-off', [["path",{"d":"M10.268 21a2 2 0 0 0 3.464 0","key":"vwvbt9"}],["path",{"d":"M17 17H4a1 1 0 0 1-.74-1.673C4.59 13.956 6 12.499 6 8a6 6 0 0 1 .258-1.742","key":"178tsu"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M8.668 3.01A6 6 0 0 1 18 8c0 2.687.77 4.653 1.707 6.05","key":"1hqiys"}]])
export const BellPlus = ssrIcon('bell-plus', [["path",{"d":"M10.268 21a2 2 0 0 0 3.464 0","key":"vwvbt9"}],["path",{"d":"M15 8h6","key":"8ybuxh"}],["path",{"d":"M18 5v6","key":"g5ayrv"}],["path",{"d":"M20.002 14.464a9 9 0 0 0 .738.863A1 1 0 0 1 20 17H4a1 1 0 0 1-.74-1.673C4.59 13.956 6 12.499 6 8a6 6 0 0 1 8.75-5.332","key":"1abcvy"}]])
export const BellRing = ssrIcon('bell-ring', [["path",{"d":"M10.268 21a2 2 0 0 0 3.464 0","key":"vwvbt9"}],["path",{"d":"M22 8c0-2.3-.8-4.3-2-6","key":"5bb3ad"}],["path",{"d":"M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326","key":"11g9vi"}],["path",{"d":"M4 2C2.8 3.7 2 5.7 2 8","key":"tap9e0"}]])
export const BetweenHorizontalEnd = ssrIcon('between-horizontal-end', [["rect",{"width":"13","height":"7","x":"3","y":"3","rx":"1","key":"11xb64"}],["path",{"d":"m22 15-3-3 3-3","key":"26chmm"}],["rect",{"width":"13","height":"7","x":"3","y":"14","rx":"1","key":"k6ky7n"}]])
export const BetweenHorizontalStart = ssrIcon('between-horizontal-start', [["rect",{"width":"13","height":"7","x":"8","y":"3","rx":"1","key":"pkso9a"}],["path",{"d":"m2 9 3 3-3 3","key":"1agib5"}],["rect",{"width":"13","height":"7","x":"8","y":"14","rx":"1","key":"1q5fc1"}]])
export const BetweenVerticalEnd = ssrIcon('between-vertical-end', [["rect",{"width":"7","height":"13","x":"3","y":"3","rx":"1","key":"1fdu0f"}],["path",{"d":"m9 22 3-3 3 3","key":"17z65a"}],["rect",{"width":"7","height":"13","x":"14","y":"3","rx":"1","key":"1squn4"}]])
export const BetweenVerticalStart = ssrIcon('between-vertical-start', [["rect",{"width":"7","height":"13","x":"3","y":"8","rx":"1","key":"1fjrkv"}],["path",{"d":"m15 2-3 3-3-3","key":"1uh6eb"}],["rect",{"width":"7","height":"13","x":"14","y":"8","rx":"1","key":"w3fjg8"}]])
export const BicepsFlexed = ssrIcon('biceps-flexed', [["path",{"d":"M12.409 13.017A5 5 0 0 1 22 15c0 3.866-4 7-9 7-4.077 0-8.153-.82-10.371-2.462-.426-.316-.631-.832-.62-1.362C2.118 12.723 2.627 2 10 2a3 3 0 0 1 3 3 2 2 0 0 1-2 2c-1.105 0-1.64-.444-2-1","key":"1pmlyh"}],["path",{"d":"M15 14a5 5 0 0 0-7.584 2","key":"5rb254"}],["path",{"d":"M9.964 6.825C8.019 7.977 9.5 13 8 15","key":"kbvsx9"}]])
export const Bike = ssrIcon('bike', [["circle",{"cx":"18.5","cy":"17.5","r":"3.5","key":"15x4ox"}],["circle",{"cx":"5.5","cy":"17.5","r":"3.5","key":"1noe27"}],["circle",{"cx":"15","cy":"5","r":"1","key":"19l28e"}],["path",{"d":"M12 17.5V14l-3-3 4-3 2 3h2","key":"1npguv"}]])
export const Binary = ssrIcon('binary', [["rect",{"x":"14","y":"14","width":"4","height":"6","rx":"2","key":"p02svl"}],["rect",{"x":"6","y":"4","width":"4","height":"6","rx":"2","key":"xm4xkj"}],["path",{"d":"M6 20h4","key":"1i6q5t"}],["path",{"d":"M14 10h4","key":"ru81e7"}],["path",{"d":"M6 14h2v6","key":"16z9wg"}],["path",{"d":"M14 4h2v6","key":"1idq9u"}]])
export const Binoculars = ssrIcon('binoculars', [["path",{"d":"M10 10h4","key":"tcdvrf"}],["path",{"d":"M19 7V4a1 1 0 0 0-1-1h-2a1 1 0 0 0-1 1v3","key":"3apit1"}],["path",{"d":"M20 21a2 2 0 0 0 2-2v-3.851c0-1.39-2-2.962-2-4.829V8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v11a2 2 0 0 0 2 2z","key":"rhpgnw"}],["path",{"d":"M 22 16 L 2 16","key":"14lkq7"}],["path",{"d":"M4 21a2 2 0 0 1-2-2v-3.851c0-1.39 2-2.962 2-4.829V8a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v11a2 2 0 0 1-2 2z","key":"104b3k"}],["path",{"d":"M9 7V4a1 1 0 0 0-1-1H6a1 1 0 0 0-1 1v3","key":"14fczp"}]])
export const Biohazard = ssrIcon('biohazard', [["circle",{"cx":"12","cy":"11.9","r":"2","key":"e8h31w"}],["path",{"d":"M6.7 3.4c-.9 2.5 0 5.2 2.2 6.7C6.5 9 3.7 9.6 2 11.6","key":"17bolr"}],["path",{"d":"m8.9 10.1 1.4.8","key":"15ezny"}],["path",{"d":"M17.3 3.4c.9 2.5 0 5.2-2.2 6.7 2.4-1.2 5.2-.6 6.9 1.5","key":"wtwa5u"}],["path",{"d":"m15.1 10.1-1.4.8","key":"1r0b28"}],["path",{"d":"M16.7 20.8c-2.6-.4-4.6-2.6-4.7-5.3-.2 2.6-2.1 4.8-4.7 5.2","key":"m7qszh"}],["path",{"d":"M12 13.9v1.6","key":"zfyyim"}],["path",{"d":"M13.5 5.4c-1-.2-2-.2-3 0","key":"1bi9q0"}],["path",{"d":"M17 16.4c.7-.7 1.2-1.6 1.5-2.5","key":"1rhjqw"}],["path",{"d":"M5.5 13.9c.3.9.8 1.8 1.5 2.5","key":"8gsud3"}]])
export const Bird = ssrIcon('bird', [["path",{"d":"M16 7h.01","key":"1kdx03"}],["path",{"d":"M3.4 18H12a8 8 0 0 0 8-8V7a4 4 0 0 0-7.28-2.3L2 20","key":"oj1oa8"}],["path",{"d":"m20 7 2 .5-2 .5","key":"12nv4d"}],["path",{"d":"M10 18v3","key":"1yea0a"}],["path",{"d":"M14 17.75V21","key":"1pymcb"}],["path",{"d":"M7 18a6 6 0 0 0 3.84-10.61","key":"1npnn0"}]])
export const Birdhouse = ssrIcon('birdhouse', [["path",{"d":"M12 18v4","key":"jadmvz"}],["path",{"d":"m17 18 1.956-11.468","key":"l5n2ro"}],["path",{"d":"m3 8 7.82-5.615a2 2 0 0 1 2.36 0L21 8","key":"1sy6n7"}],["path",{"d":"M4 18h16","key":"19g7jn"}],["path",{"d":"M7 18 5.044 6.532","key":"1uqdf2"}],["circle",{"cx":"12","cy":"10","r":"2","key":"1yojzk"}]])
export const Bitcoin = ssrIcon('bitcoin', [["path",{"d":"M11.767 19.089c4.924.868 6.14-6.025 1.216-6.894m-1.216 6.894L5.86 18.047m5.908 1.042-.347 1.97m1.563-8.864c4.924.869 6.14-6.025 1.215-6.893m-1.215 6.893-3.94-.694m5.155-6.2L8.29 4.26m5.908 1.042.348-1.97M7.48 20.364l3.126-17.727","key":"yr8idg"}]])
export const Blend = ssrIcon('blend', [["circle",{"cx":"15","cy":"9","r":"7","key":"1i12rt"}],["circle",{"cx":"9","cy":"15","r":"7","key":"19bs8k"}]])
export const Blender = ssrIcon('blender', [["path",{"d":"M8 14a2 2 0 0 0-1.963 1.615l-1.018 5.193A1 1 0 0 0 6 22h12a1 1 0 0 0 .981-1.192l-1.018-5.193A2 2 0 0 0 16 14z","key":"11zxmj"}],["path",{"d":"m17 2-1 12","key":"nxm2fw"}],["path",{"d":"M8.006 14 7 2","key":"13bxiv"}],["path",{"d":"M7.565 8.787A5 5 0 0 0 12 8a5 5 0 0 1 4.56-.75","key":"1s61ad"}],["path",{"d":"M19 2H5a2 2 0 0 0-2 2v5a2 2 0 0 0 .688 1.5","key":"gel3rg"}],["path",{"d":"M12 18h.01","key":"mhygvu"}]])
export const Blinds = ssrIcon('blinds', [["path",{"d":"M3 3h18","key":"o7r712"}],["path",{"d":"M20 7H8","key":"gd2fo2"}],["path",{"d":"M20 11H8","key":"1ynp89"}],["path",{"d":"M10 19h10","key":"19hjk5"}],["path",{"d":"M8 15h12","key":"1yqzne"}],["path",{"d":"M4 3v14","key":"fggqzn"}],["circle",{"cx":"4","cy":"19","r":"2","key":"p3m9r0"}]])
export const Blocks = ssrIcon('blocks', [["path",{"d":"M10 22V7a1 1 0 0 0-1-1H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5a1 1 0 0 0-1-1H2","key":"1ah6g2"}],["rect",{"x":"14","y":"2","width":"8","height":"8","rx":"1","key":"88lufb"}]])
export const Bluetooth = ssrIcon('bluetooth', [["path",{"d":"m7 7 10 10-5 5V2l5 5L7 17","key":"1q5490"}]])
export const BluetoothConnected = ssrIcon('bluetooth-connected', [["path",{"d":"m7 7 10 10-5 5V2l5 5L7 17","key":"1q5490"}],["line",{"x1":"18","x2":"21","y1":"12","y2":"12","key":"1rsjjs"}],["line",{"x1":"3","x2":"6","y1":"12","y2":"12","key":"11yl8c"}]])
export const BluetoothOff = ssrIcon('bluetooth-off', [["path",{"d":"m17 17-5 5V12l-5 5","key":"v5aci6"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M14.5 9.5 17 7l-5-5v4.5","key":"1kddfz"}]])
export const BluetoothSearching = ssrIcon('bluetooth-searching', [["path",{"d":"m7 7 10 10-5 5V2l5 5L7 17","key":"1q5490"}],["path",{"d":"M20.83 14.83a4 4 0 0 0 0-5.66","key":"k8tn1j"}],["path",{"d":"M18 12h.01","key":"yjnet6"}]])
export const Bold = ssrIcon('bold', [["path",{"d":"M6 12h9a4 4 0 0 1 0 8H7a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h7a4 4 0 0 1 0 8","key":"mg9rjx"}]])
export const Bolt = ssrIcon('bolt', [["path",{"d":"M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z","key":"yt0hxn"}],["circle",{"cx":"12","cy":"12","r":"4","key":"4exip2"}]])
export const Bomb = ssrIcon('bomb', [["circle",{"cx":"11","cy":"13","r":"9","key":"hd149"}],["path",{"d":"M14.35 4.65 16.3 2.7a2.41 2.41 0 0 1 3.4 0l1.6 1.6a2.4 2.4 0 0 1 0 3.4l-1.95 1.95","key":"jp4j1b"}],["path",{"d":"m22 2-1.5 1.5","key":"ay92ug"}]])
export const Bone = ssrIcon('bone', [["path",{"d":"M17 10c.7-.7 1.69 0 2.5 0a2.5 2.5 0 1 0 0-5 .5.5 0 0 1-.5-.5 2.5 2.5 0 1 0-5 0c0 .81.7 1.8 0 2.5l-7 7c-.7.7-1.69 0-2.5 0a2.5 2.5 0 0 0 0 5c.28 0 .5.22.5.5a2.5 2.5 0 1 0 5 0c0-.81-.7-1.8 0-2.5Z","key":"w610uw"}]])
export const BoneFracture = ssrIcon('bone-fracture', [["path",{"d":"M14 4.5a1 1 0 0 1 5 0 .5.5 0 0 0 .5.5 1 1 0 0 1 0 5c-.81 0-1.8-.7-2.5 0l-1.958 1.957a.15.15 0 0 1-.252-.072l-.493-2.07a.15.15 0 0 0-.111-.112l-2.072-.494a.15.15 0 0 1-.072-.252L14 7c.7-.7 0-1.69 0-2.5","key":"1c7o5b"}],["path",{"d":"m16 20-1-2","key":"5348lt"}],["path",{"d":"m20 16-2-1","key":"2c7pv5"}],["path",{"d":"m4 8 2 1","key":"rpj1x4"}],["path",{"d":"m8 4 1 2","key":"1r4zbp"}],["path",{"d":"M9.698 14.19a.15.15 0 0 0 .112.112l2.074.489a.15.15 0 0 1 .072.252L10 17c-.7.7 0 1.69 0 2.5a1 1 0 0 1-5 0 .495.495 0 0 0-.5-.5 1 1 0 0 1 0-5c.81 0 1.8.7 2.5 0l1.956-1.957a.15.15 0 0 1 .252.072z","key":"3u61yx"}]])
export const Book = ssrIcon('book', [["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"k3hazp"}]])
export const BookA = ssrIcon('book-a', [["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"k3hazp"}],["path",{"d":"m8 13 4-7 4 7","key":"4rari8"}],["path",{"d":"M9.1 11h5.7","key":"1gkovt"}]])
export const BookAlert = ssrIcon('book-alert', [["path",{"d":"M12 13h.01","key":"y0uutt"}],["path",{"d":"M12 6v3","key":"1m4b9j"}],["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"k3hazp"}]])
export const BookAudio = ssrIcon('book-audio', [["path",{"d":"M12 6v7","key":"1f6ttz"}],["path",{"d":"M16 8v3","key":"gejaml"}],["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"k3hazp"}],["path",{"d":"M8 8v3","key":"1qzp49"}]])
export const BookCheck = ssrIcon('book-check', [["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"k3hazp"}],["path",{"d":"m9 9.5 2 2 4-4","key":"1dth82"}]])
export const BookCopy = ssrIcon('book-copy', [["path",{"d":"M5 7a2 2 0 0 0-2 2v11","key":"1yhqjt"}],["path",{"d":"M5.803 18H5a2 2 0 0 0 0 4h9.5a.5.5 0 0 0 .5-.5V21","key":"edzzo5"}],["path",{"d":"M9 15V4a2 2 0 0 1 2-2h9.5a.5.5 0 0 1 .5.5v14a.5.5 0 0 1-.5.5H11a2 2 0 0 1 0-4h10","key":"1nwzrg"}]])
export const BookDashed = ssrIcon('book-dashed', [["path",{"d":"M12 17h1.5","key":"1gkc67"}],["path",{"d":"M12 22h1.5","key":"1my7sn"}],["path",{"d":"M12 2h1.5","key":"19tvb7"}],["path",{"d":"M17.5 22H19a1 1 0 0 0 1-1","key":"10akbh"}],["path",{"d":"M17.5 2H19a1 1 0 0 1 1 1v1.5","key":"1vrfjs"}],["path",{"d":"M20 14v3h-2.5","key":"1naeju"}],["path",{"d":"M20 8.5V10","key":"1ctpfu"}],["path",{"d":"M4 10V8.5","key":"1o3zg5"}],["path",{"d":"M4 19.5V14","key":"ob81pf"}],["path",{"d":"M4 4.5A2.5 2.5 0 0 1 6.5 2H8","key":"s8vcyb"}],["path",{"d":"M8 22H6.5a1 1 0 0 1 0-5H8","key":"1cu73q"}]])
export const BookDown = ssrIcon('book-down', [["path",{"d":"M12 13V7","key":"h0r20n"}],["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"k3hazp"}],["path",{"d":"m9 10 3 3 3-3","key":"zt5b4y"}]])
export const BookHeadphones = ssrIcon('book-headphones', [["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"k3hazp"}],["path",{"d":"M8 12v-2a4 4 0 0 1 8 0v2","key":"1vsqkj"}],["circle",{"cx":"15","cy":"12","r":"1","key":"1tmaij"}],["circle",{"cx":"9","cy":"12","r":"1","key":"1vctgf"}]])
export const BookHeart = ssrIcon('book-heart', [["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"k3hazp"}],["path",{"d":"M8.62 9.8A2.25 2.25 0 1 1 12 6.836a2.25 2.25 0 1 1 3.38 2.966l-2.626 2.856a.998.998 0 0 1-1.507 0z","key":"9v40y5"}]])
export const BookImage = ssrIcon('book-image', [["path",{"d":"m20 13.7-2.1-2.1a2 2 0 0 0-2.8 0L9.7 17","key":"q6ojf0"}],["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"k3hazp"}],["circle",{"cx":"10","cy":"8","r":"2","key":"2qkj4p"}]])
export const BookKey = ssrIcon('book-key', [["path",{"d":"M13 2H6.5A2.5 2.5 0 0 0 4 4.5v15","key":"4azifu"}],["path",{"d":"M17 2v6","key":"qgmh37"}],["path",{"d":"M17 4h2","key":"13vrzo"}],["path",{"d":"M20 15.2V21a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"192hzx"}],["circle",{"cx":"17","cy":"10","r":"2","key":"y0i25j"}]])
export const BookLock = ssrIcon('book-lock', [["path",{"d":"M18 6V4a2 2 0 1 0-4 0v2","key":"1aquzs"}],["path",{"d":"M20 15v6a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"1rkj32"}],["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H10","key":"18wgow"}],["rect",{"x":"12","y":"6","width":"8","height":"5","rx":"1","key":"73l30o"}]])
export const BookMarked = ssrIcon('book-marked', [["path",{"d":"M10 2v8l3-3 3 3V2","key":"sqw3rj"}],["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"k3hazp"}]])
export const BookMinus = ssrIcon('book-minus', [["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"k3hazp"}],["path",{"d":"M9 10h6","key":"9gxzsh"}]])
export const BookOpen = ssrIcon('book-open', [["path",{"d":"M12 5v16","key":"1f6ucr"}],["path",{"d":"M20.001 19A2 2 0 0022 17V5a2 2 0 00-1.999-2L16 3.002A5 5 0 0012 5a5 5 0 00-4-2H4a2 2 0 00-2 2v12a2 2 0 001.999 2H8a5 5 0 014 2 5 5 0 014-2z","key":"1fyvmf"}]])
export const BookOpenCheck = ssrIcon('book-open-check', [["path",{"d":"M12 5v16","key":"1f6ucr"}],["path",{"d":"m16 12 2 2 4-4","key":"mdajum"}],["path",{"d":"M22 6V5a2 2 0 00-1.999-2L16 3.002A5 5 0 0012 5a5 5 0 00-4-2H4a2 2 0 00-2 2v12a2 2 0 001.999 2H8a5 5 0 014 2 5 5 0 014-2h4.001A2 2 0 0022 17v-1.344","key":"144kbk"}]])
export const BookOpenText = ssrIcon('book-open-text', [["path",{"d":"M12 5v16","key":"1f6ucr"}],["path",{"d":"M16 13h2","key":"weia3s"}],["path",{"d":"M16 9h2","key":"1n7gjm"}],["path",{"d":"M20.001 19A2 2 0 0022 17V5a2 2 0 00-1.999-2L16 3.002A5 5 0 0012 5a5 5 0 00-4-2H4a2 2 0 00-2 2v12a2 2 0 001.999 2H8a5 5 0 014 2 5 5 0 014-2z","key":"1fyvmf"}],["path",{"d":"M6 13h2","key":"1cckiz"}],["path",{"d":"M6 9h2","key":"1k7j9f"}]])
export const BookPlus = ssrIcon('book-plus', [["path",{"d":"M12 7v6","key":"lw1j43"}],["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"k3hazp"}],["path",{"d":"M9 10h6","key":"9gxzsh"}]])
export const BookSearch = ssrIcon('book-search', [["path",{"d":"M11 22H5.5a1 1 0 0 1 0-5h4.501","key":"mcbepb"}],["path",{"d":"m21 22-1.879-1.878","key":"12q7x1"}],["path",{"d":"M3 19.5v-15A2.5 2.5 0 0 1 5.5 2H18a1 1 0 0 1 1 1v8","key":"olfd5n"}],["circle",{"cx":"17","cy":"18","r":"3","key":"82mm0e"}]])
export const BookText = ssrIcon('book-text', [["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"k3hazp"}],["path",{"d":"M8 11h8","key":"vwpz6n"}],["path",{"d":"M8 7h6","key":"1f0q6e"}]])
export const BookType = ssrIcon('book-type', [["path",{"d":"M10 13h4","key":"ytezjc"}],["path",{"d":"M12 6v7","key":"1f6ttz"}],["path",{"d":"M16 8V6H8v2","key":"x8j6u4"}],["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"k3hazp"}]])
export const BookUp = ssrIcon('book-up', [["path",{"d":"M12 13V7","key":"h0r20n"}],["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"k3hazp"}],["path",{"d":"m9 10 3-3 3 3","key":"11gsxs"}]])
export const BookUp2 = ssrIcon('book-up-2', [["path",{"d":"M12 13V7","key":"h0r20n"}],["path",{"d":"M18 2h1a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"161d7n"}],["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2","key":"1lorq7"}],["path",{"d":"m9 10 3-3 3 3","key":"11gsxs"}],["path",{"d":"m9 5 3-3 3 3","key":"l8vdw6"}]])
export const BookUser = ssrIcon('book-user', [["path",{"d":"M15 13a3 3 0 1 0-6 0","key":"10j68g"}],["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"k3hazp"}],["circle",{"cx":"12","cy":"8","r":"2","key":"1822b1"}]])
export const BookX = ssrIcon('book-x', [["path",{"d":"m14.5 7.5-5 5","key":"3lb6iw"}],["path",{"d":"M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20","key":"k3hazp"}],["path",{"d":"m9.5 7.5 5 5","key":"ko136h"}]])
export const Bookmark = ssrIcon('bookmark', [["path",{"d":"M17 3a2 2 0 0 1 2 2v15a1 1 0 0 1-1.496.868l-4.512-2.578a2 2 0 0 0-1.984 0l-4.512 2.578A1 1 0 0 1 5 20V5a2 2 0 0 1 2-2z","key":"oz39mx"}]])
export const BookmarkCheck = ssrIcon('bookmark-check', [["path",{"d":"M17 3a2 2 0 0 1 2 2v15a1 1 0 0 1-1.496.868l-4.512-2.578a2 2 0 0 0-1.984 0l-4.512 2.578A1 1 0 0 1 5 20V5a2 2 0 0 1 2-2z","key":"oz39mx"}],["path",{"d":"m9 10 2 2 4-4","key":"1gnqz4"}]])
export const BookmarkMinus = ssrIcon('bookmark-minus', [["path",{"d":"M15 10H9","key":"o6yqo3"}],["path",{"d":"M17 3a2 2 0 0 1 2 2v15a1 1 0 0 1-1.496.868l-4.512-2.578a2 2 0 0 0-1.984 0l-4.512 2.578A1 1 0 0 1 5 20V5a2 2 0 0 1 2-2z","key":"oz39mx"}]])
export const BookmarkOff = ssrIcon('bookmark-off', [["path",{"d":"M19 19v1a1 1 0 0 1-1.496.868l-4.512-2.578a2 2 0 0 0-1.984 0l-4.512 2.578A1 1 0 0 1 5 20V5","key":"nigmce"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M8.656 3H17a2 2 0 0 1 2 2v8.344","key":"hlvsa"}]])
export const BookmarkPlus = ssrIcon('bookmark-plus', [["path",{"d":"M12 7v6","key":"lw1j43"}],["path",{"d":"M15 10H9","key":"o6yqo3"}],["path",{"d":"M17 3a2 2 0 0 1 2 2v15a1 1 0 0 1-1.496.868l-4.512-2.578a2 2 0 0 0-1.984 0l-4.512 2.578A1 1 0 0 1 5 20V5a2 2 0 0 1 2-2z","key":"oz39mx"}]])
export const BookmarkX = ssrIcon('bookmark-x', [["path",{"d":"m14.5 7.5-5 5","key":"3lb6iw"}],["path",{"d":"M17 3a2 2 0 0 1 2 2v15a1 1 0 0 1-1.496.868l-4.512-2.578a2 2 0 0 0-1.984 0l-4.512 2.578A1 1 0 0 1 5 20V5a2 2 0 0 1 2-2z","key":"oz39mx"}],["path",{"d":"m9.5 7.5 5 5","key":"ko136h"}]])
export const BoomBox = ssrIcon('boom-box', [["path",{"d":"M4 9V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v4","key":"vvzvr1"}],["path",{"d":"M8 8v1","key":"xcqmfk"}],["path",{"d":"M12 8v1","key":"1rj8u4"}],["path",{"d":"M16 8v1","key":"1q12zr"}],["rect",{"width":"20","height":"12","x":"2","y":"9","rx":"2","key":"igpb89"}],["circle",{"cx":"8","cy":"15","r":"2","key":"fa4a8s"}],["circle",{"cx":"16","cy":"15","r":"2","key":"14c3ya"}]])
export const Bot = ssrIcon('bot', [["path",{"d":"M12 8V4H8","key":"hb8ula"}],["rect",{"width":"16","height":"12","x":"4","y":"8","rx":"2","key":"enze0r"}],["path",{"d":"M2 14h2","key":"vft8re"}],["path",{"d":"M20 14h2","key":"4cs60a"}],["path",{"d":"M15 13v2","key":"1xurst"}],["path",{"d":"M9 13v2","key":"rq6x2g"}]])
export const BotMessageSquare = ssrIcon('bot-message-square', [["path",{"d":"M12 6V2H8","key":"1155em"}],["path",{"d":"M15 11v2","key":"i11awn"}],["path",{"d":"M2 12h2","key":"1t8f8n"}],["path",{"d":"M20 12h2","key":"1q8mjw"}],["path",{"d":"M20 16a2 2 0 0 1-2 2H8.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 4 20.286V8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2z","key":"11gyqh"}],["path",{"d":"M9 11v2","key":"1ueba0"}]])
export const BotOff = ssrIcon('bot-off', [["path",{"d":"M13.67 8H18a2 2 0 0 1 2 2v4.33","key":"7az073"}],["path",{"d":"M2 14h2","key":"vft8re"}],["path",{"d":"M20 14h2","key":"4cs60a"}],["path",{"d":"M22 22 2 2","key":"1r8tn9"}],["path",{"d":"M8 8H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h12a2 2 0 0 0 1.414-.586","key":"s09a7a"}],["path",{"d":"M9 13v2","key":"rq6x2g"}],["path",{"d":"M9.67 4H12v2.33","key":"110xot"}]])
export const BottleWine = ssrIcon('bottle-wine', [["path",{"d":"M10 3a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v2a6 6 0 0 0 1.2 3.6l.6.8A6 6 0 0 1 17 13v8a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1v-8a6 6 0 0 1 1.2-3.6l.6-.8A6 6 0 0 0 10 5z","key":"blqgoc"}],["path",{"d":"M17 13h-4a1 1 0 0 0-1 1v3a1 1 0 0 0 1 1h4","key":"43jbee"}]])
export const BowArrow = ssrIcon('bow-arrow', [["path",{"d":"M17 3h4v4","key":"19p9u1"}],["path",{"d":"M18.575 11.082a13 13 0 0 1 1.048 9.027 1.17 1.17 0 0 1-1.914.597L14 17","key":"12t3w9"}],["path",{"d":"M7 10 3.29 6.29a1.17 1.17 0 0 1 .6-1.91 13 13 0 0 1 9.03 1.05","key":"ogng5l"}],["path",{"d":"M7 14a1.7 1.7 0 0 0-1.207.5l-2.646 2.646A.5.5 0 0 0 3.5 18H5a1 1 0 0 1 1 1v1.5a.5.5 0 0 0 .854.354L9.5 18.207A1.7 1.7 0 0 0 10 17v-2a1 1 0 0 0-1-1z","key":"8v3fy2"}],["path",{"d":"M9.707 14.293 21 3","key":"ydm3bn"}]])
export const Box = ssrIcon('box', [["path",{"d":"M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z","key":"hh9hay"}],["path",{"d":"m3.3 7 8.7 5 8.7-5","key":"g66t2b"}],["path",{"d":"M12 22V12","key":"d0xqtd"}]])
export const SquareDashed = ssrIcon('square-dashed', [["path",{"d":"M5 3a2 2 0 0 0-2 2","key":"y57alp"}],["path",{"d":"M19 3a2 2 0 0 1 2 2","key":"18rm91"}],["path",{"d":"M21 19a2 2 0 0 1-2 2","key":"1j7049"}],["path",{"d":"M5 21a2 2 0 0 1-2-2","key":"sbafld"}],["path",{"d":"M9 3h1","key":"1yesri"}],["path",{"d":"M9 21h1","key":"15o7lz"}],["path",{"d":"M14 3h1","key":"1ec4yj"}],["path",{"d":"M14 21h1","key":"v9vybs"}],["path",{"d":"M3 9v1","key":"1r0deq"}],["path",{"d":"M21 9v1","key":"mxsmne"}],["path",{"d":"M3 14v1","key":"vnatye"}],["path",{"d":"M21 14v1","key":"169vum"}]])
export const Boxes = ssrIcon('boxes', [["path",{"d":"M2.97 12.92A2 2 0 0 0 2 14.63v3.24a2 2 0 0 0 .97 1.71l3 1.8a2 2 0 0 0 2.06 0L12 19v-5.5l-5-3-4.03 2.42Z","key":"lc1i9w"}],["path",{"d":"m7 16.5-4.74-2.85","key":"1o9zyk"}],["path",{"d":"m7 16.5 5-3","key":"va8pkn"}],["path",{"d":"M7 16.5v5.17","key":"jnp8gn"}],["path",{"d":"M12 13.5V19l3.97 2.38a2 2 0 0 0 2.06 0l3-1.8a2 2 0 0 0 .97-1.71v-3.24a2 2 0 0 0-.97-1.71L17 10.5l-5 3Z","key":"8zsnat"}],["path",{"d":"m17 16.5-5-3","key":"8arw3v"}],["path",{"d":"m17 16.5 4.74-2.85","key":"8rfmw"}],["path",{"d":"M17 16.5v5.17","key":"k6z78m"}],["path",{"d":"M7.97 4.42A2 2 0 0 0 7 6.13v4.37l5 3 5-3V6.13a2 2 0 0 0-.97-1.71l-3-1.8a2 2 0 0 0-2.06 0l-3 1.8Z","key":"1xygjf"}],["path",{"d":"M12 8 7.26 5.15","key":"1vbdud"}],["path",{"d":"m12 8 4.74-2.85","key":"3rx089"}],["path",{"d":"M12 13.5V8","key":"1io7kd"}]])
export const Braces = ssrIcon('braces', [["path",{"d":"M8 3H7a2 2 0 0 0-2 2v5a2 2 0 0 1-2 2 2 2 0 0 1 2 2v5c0 1.1.9 2 2 2h1","key":"ezmyqa"}],["path",{"d":"M16 21h1a2 2 0 0 0 2-2v-5c0-1.1.9-2 2-2a2 2 0 0 1-2-2V5a2 2 0 0 0-2-2h-1","key":"e1hn23"}]])
export const Brackets = ssrIcon('brackets', [["path",{"d":"M16 3h3a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1h-3","key":"1kt8lf"}],["path",{"d":"M8 21H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h3","key":"gduv9"}]])
export const Brain = ssrIcon('brain', [["path",{"d":"M12 18V5","key":"adv99a"}],["path",{"d":"M15 13a4.17 4.17 0 0 1-3-4 4.17 4.17 0 0 1-3 4","key":"1e3is1"}],["path",{"d":"M17.598 6.5A3 3 0 1 0 12 5a3 3 0 1 0-5.598 1.5","key":"1gqd8o"}],["path",{"d":"M17.997 5.125a4 4 0 0 1 2.526 5.77","key":"iwvgf7"}],["path",{"d":"M18 18a4 4 0 0 0 2-7.464","key":"efp6ie"}],["path",{"d":"M19.967 17.483A4 4 0 1 1 12 18a4 4 0 1 1-7.967-.517","key":"1gq6am"}],["path",{"d":"M6 18a4 4 0 0 1-2-7.464","key":"k1g0md"}],["path",{"d":"M6.003 5.125a4 4 0 0 0-2.526 5.77","key":"q97ue3"}]])
export const BrainCircuit = ssrIcon('brain-circuit', [["path",{"d":"M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z","key":"l5xja"}],["path",{"d":"M9 13a4.5 4.5 0 0 0 3-4","key":"10igwf"}],["path",{"d":"M6.003 5.125A3 3 0 0 0 6.401 6.5","key":"105sqy"}],["path",{"d":"M3.477 10.896a4 4 0 0 1 .585-.396","key":"ql3yin"}],["path",{"d":"M6 18a4 4 0 0 1-1.967-.516","key":"2e4loj"}],["path",{"d":"M12 13h4","key":"1ku699"}],["path",{"d":"M12 18h6a2 2 0 0 1 2 2v1","key":"105ag5"}],["path",{"d":"M12 8h8","key":"1lhi5i"}],["path",{"d":"M16 8V5a2 2 0 0 1 2-2","key":"u6izg6"}],["circle",{"cx":"16","cy":"13","r":".5","key":"ry7gng"}],["circle",{"cx":"18","cy":"3","r":".5","key":"1aiba7"}],["circle",{"cx":"20","cy":"21","r":".5","key":"yhc1fs"}],["circle",{"cx":"20","cy":"8","r":".5","key":"1e43v0"}]])
export const BrainCog = ssrIcon('brain-cog', [["path",{"d":"m10.852 14.772-.383.923","key":"11vil6"}],["path",{"d":"m10.852 9.228-.383-.923","key":"1fjppe"}],["path",{"d":"m13.148 14.772.382.924","key":"je3va1"}],["path",{"d":"m13.531 8.305-.383.923","key":"18epck"}],["path",{"d":"m14.772 10.852.923-.383","key":"k9m8cz"}],["path",{"d":"m14.772 13.148.923.383","key":"1xvhww"}],["path",{"d":"M17.598 6.5A3 3 0 1 0 12 5a3 3 0 0 0-5.63-1.446 3 3 0 0 0-.368 1.571 4 4 0 0 0-2.525 5.771","key":"jcbbz1"}],["path",{"d":"M17.998 5.125a4 4 0 0 1 2.525 5.771","key":"1kkn7e"}],["path",{"d":"M19.505 10.294a4 4 0 0 1-1.5 7.706","key":"18bmuc"}],["path",{"d":"M4.032 17.483A4 4 0 0 0 11.464 20c.18-.311.892-.311 1.072 0a4 4 0 0 0 7.432-2.516","key":"uozx0d"}],["path",{"d":"M4.5 10.291A4 4 0 0 0 6 18","key":"whdemb"}],["path",{"d":"M6.002 5.125a3 3 0 0 0 .4 1.375","key":"1kqy2g"}],["path",{"d":"m9.228 10.852-.923-.383","key":"1wtb30"}],["path",{"d":"m9.228 13.148-.923.383","key":"1a830x"}],["circle",{"cx":"12","cy":"12","r":"3","key":"1v7zrd"}]])
export const BrickWall = ssrIcon('brick-wall', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M12 9v6","key":"199k2o"}],["path",{"d":"M16 15v6","key":"8rj2es"}],["path",{"d":"M16 3v6","key":"1j6rpj"}],["path",{"d":"M3 15h18","key":"5xshup"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M8 15v6","key":"1stoo3"}],["path",{"d":"M8 3v6","key":"vlvjmk"}]])
export const BrickWallFire = ssrIcon('brick-wall-fire', [["path",{"d":"M16 3v2.107","key":"gq8xun"}],["path",{"d":"M17 9c1 3 2.5 3.5 3.5 4.5A5 5 0 0 1 22 17a5 5 0 0 1-10 0c0-.3 0-.6.1-.9a2 2 0 1 0 3.3-2C13 11.5 16 9 17 9","key":"1l2pih"}],["path",{"d":"M21 8.274V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h3.938","key":"jrnqjp"}],["path",{"d":"M3 15h5.253","key":"xqg7rb"}],["path",{"d":"M3 9h8.228","key":"1ppb70"}],["path",{"d":"M8 15v6","key":"1stoo3"}],["path",{"d":"M8 3v6","key":"vlvjmk"}]])
export const BrickWallShield = ssrIcon('brick-wall-shield', [["path",{"d":"M12 9v1.258","key":"iwpddn"}],["path",{"d":"M16 3v5.46","key":"d7ew98"}],["path",{"d":"M21 9.118V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h5.75","key":"137t5x"}],["path",{"d":"M22 17.5c0 2.499-1.75 3.749-3.83 4.474a.5.5 0 0 1-.335-.005c-2.085-.72-3.835-1.97-3.835-4.47V14a.5.5 0 0 1 .5-.499c1 0 2.25-.6 3.12-1.36a.6.6 0 0 1 .76-.001c.875.765 2.12 1.36 3.12 1.36a.5.5 0 0 1 .5.5z","key":"16j3tf"}],["path",{"d":"M3 15h7","key":"1qldh6"}],["path",{"d":"M3 9h12.142","key":"1yjd6m"}],["path",{"d":"M8 15v6","key":"1stoo3"}],["path",{"d":"M8 3v6","key":"vlvjmk"}]])
export const Briefcase = ssrIcon('briefcase', [["path",{"d":"M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16","key":"jecpp"}],["rect",{"width":"20","height":"14","x":"2","y":"6","rx":"2","key":"i6l2r4"}]])
export const BriefcaseBusiness = ssrIcon('briefcase-business', [["path",{"d":"M12 12h.01","key":"1mp3jc"}],["path",{"d":"M16 6V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2","key":"1ksdt3"}],["path",{"d":"M22 13a18.15 18.15 0 0 1-20 0","key":"12hx5q"}],["rect",{"width":"20","height":"14","x":"2","y":"6","rx":"2","key":"i6l2r4"}]])
export const BriefcaseConveyorBelt = ssrIcon('briefcase-conveyor-belt', [["path",{"d":"M10 20v2","key":"1n8e1g"}],["path",{"d":"M14 20v2","key":"1lq872"}],["path",{"d":"M18 20v2","key":"10uadw"}],["path",{"d":"M21 20H3","key":"kdqkdp"}],["path",{"d":"M6 20v2","key":"a9bc87"}],["path",{"d":"M8 16V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v12","key":"17n9tx"}],["rect",{"x":"4","y":"6","width":"16","height":"10","rx":"2","key":"1097i5"}]])
export const BriefcaseMedical = ssrIcon('briefcase-medical', [["path",{"d":"M12 11v4","key":"a6ujw6"}],["path",{"d":"M14 13h-4","key":"1pl8zg"}],["path",{"d":"M16 6V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2","key":"1ksdt3"}],["path",{"d":"M18 6v14","key":"1mu4gy"}],["path",{"d":"M6 6v14","key":"1s15cj"}],["rect",{"width":"20","height":"14","x":"2","y":"6","rx":"2","key":"i6l2r4"}]])
export const BringToFront = ssrIcon('bring-to-front', [["rect",{"x":"8","y":"8","width":"8","height":"8","rx":"2","key":"yj20xf"}],["path",{"d":"M4 10a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2","key":"1ltk23"}],["path",{"d":"M14 20a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-4a2 2 0 0 0-2-2","key":"1q24h9"}]])
export const Broccoli = ssrIcon('broccoli', [["path",{"d":"M10 13a3 3 0 0 1-2.121-5.121","key":"1oqad0"}],["path",{"d":"M15.606 14.204c-3.5 1.5-5.899 4.503-8.899 7.503A1 1 0 0 1 6 22c-2 0-4-2-4-4a1 1 0 0 1 .293-.707c1.911-1.911 3.823-3.578 5.347-5.441","key":"c93qjr"}],["path",{"d":"M16.573 14.737A4 4 0 0 1 14 11","key":"1ymr17"}],["path",{"d":"M7.14 10.907a4 4 0 1 1 2.756-7.43A4 4 0 0 1 16.7 4.48a2 2 0 0 1 2.82 2.82 4 4 0 0 1 1.002 6.805A4 4 0 1 1 13 16","key":"1kbgad"}]])
export const Broom = ssrIcon('broom', [["path",{"d":"M13.5 10.5 22 2","key":"1yxz6l"}],["path",{"d":"M14.734 13.841a2 2 0 00-.314-2.42L12.58 9.58a2 2 0 00-2.421-.314l-7.657 4.461A1 1 0 002.3 15.3l6.403 6.403a1 1 0 001.571-.204z","key":"1q75r6"}],["path",{"d":"m5 18 2-2","key":"11qwpn"}],["path",{"d":"m7.699 10.7 5.602 5.601","key":"1rehuz"}]])
export const BroomSparkles = ssrIcon('broom-sparkles', [["path",{"d":"M11 2v2","key":"1539x4"}],["path",{"d":"M12 3h-2","key":"1su5n0"}],["path",{"d":"M13.5 10.5 22 2","key":"1yxz6l"}],["path",{"d":"M14.734 13.841a2 2 0 00-.314-2.42L12.58 9.58a2 2 0 00-2.421-.314l-7.657 4.461A1 1 0 002.3 15.3l6.403 6.403a1 1 0 001.571-.204z","key":"1q75r6"}],["path",{"d":"M20 15v4","key":"nmhudv"}],["path",{"d":"M22 17h-4","key":"1sj068"}],["path",{"d":"M4 4v4","key":"a4sqb9"}],["path",{"d":"m5 18 2-2","key":"11qwpn"}],["path",{"d":"M6 6H2","key":"1cli1h"}],["path",{"d":"m7.699 10.7 5.602 5.601","key":"1rehuz"}]])
export const Brush = ssrIcon('brush', [["path",{"d":"m11 10 3 3","key":"fzmg1i"}],["path",{"d":"M6.5 21A3.5 3.5 0 1 0 3 17.5a2.62 2.62 0 0 1-.708 1.792A1 1 0 0 0 3 21z","key":"p4q2r7"}],["path",{"d":"M9.969 17.031 21.378 5.624a1 1 0 0 0-3.002-3.002L6.967 14.031","key":"wy6l02"}]])
export const BrushCleaning = ssrIcon('brush-cleaning', [["path",{"d":"m16 22-1-4","key":"1ow2iv"}],["path",{"d":"M19 14a1 1 0 0 0 1-1v-1a2 2 0 0 0-2-2h-3a1 1 0 0 1-1-1V4a2 2 0 0 0-4 0v5a1 1 0 0 1-1 1H6a2 2 0 0 0-2 2v1a1 1 0 0 0 1 1","key":"11gii7"}],["path",{"d":"M19 14H5l-1.973 6.767A1 1 0 0 0 4 22h16a1 1 0 0 0 .973-1.233z","key":"bju7h4"}],["path",{"d":"m8 22 1-4","key":"s3unb"}]])
export const Bubbles = ssrIcon('bubbles', [["path",{"d":"M7.001 15.085A1.5 1.5 0 0 1 9 16.5","key":"y44lvh"}],["circle",{"cx":"18.5","cy":"8.5","r":"3.5","key":"1wadoa"}],["circle",{"cx":"7.5","cy":"16.5","r":"5.5","key":"6mdt3g"}],["circle",{"cx":"7.5","cy":"4.5","r":"2.5","key":"637s54"}]])
export const Bug = ssrIcon('bug', [["path",{"d":"M12 20v-9","key":"1qisl0"}],["path",{"d":"M14 7a4 4 0 0 1 4 4v3a6 6 0 0 1-12 0v-3a4 4 0 0 1 4-4z","key":"uouzyp"}],["path",{"d":"M14.12 3.88 16 2","key":"qol33r"}],["path",{"d":"M21 21a4 4 0 0 0-3.81-4","key":"1b0z45"}],["path",{"d":"M21 5a4 4 0 0 1-3.55 3.97","key":"5cxbf6"}],["path",{"d":"M22 13h-4","key":"1jl80f"}],["path",{"d":"M3 21a4 4 0 0 1 3.81-4","key":"1fjd4g"}],["path",{"d":"M3 5a4 4 0 0 0 3.55 3.97","key":"1d7oge"}],["path",{"d":"M6 13H2","key":"82j7cp"}],["path",{"d":"m8 2 1.88 1.88","key":"fmnt4t"}],["path",{"d":"M9 7.13V6a3 3 0 1 1 6 0v1.13","key":"1vgav8"}]])
export const BugOff = ssrIcon('bug-off', [["path",{"d":"M12 20v-8","key":"i3yub9"}],["path",{"d":"M12.656 7H14a4 4 0 0 1 4 4v1.344","key":"vvueyn"}],["path",{"d":"M14.12 3.88 16 2","key":"qol33r"}],["path",{"d":"M17.123 17.123A6 6 0 0 1 6 14v-3a4 4 0 0 1 1.72-3.287","key":"1cu21y"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M21 5a4 4 0 0 1-3.55 3.97","key":"5cxbf6"}],["path",{"d":"M22 13h-3.344","key":"qb08am"}],["path",{"d":"M3 21a4 4 0 0 1 3.81-4","key":"1fjd4g"}],["path",{"d":"M3 5a4 4 0 0 0 3.55 3.97","key":"1d7oge"}],["path",{"d":"M6 13H2","key":"82j7cp"}],["path",{"d":"m8 2 1.88 1.88","key":"fmnt4t"}],["path",{"d":"M9.712 4.06A3 3 0 0 1 15 6v1.13","key":"1bvup6"}]])
export const BugPlay = ssrIcon('bug-play', [["path",{"d":"M10 19.655A6 6 0 0 1 6 14v-3a4 4 0 0 1 4-4h4a4 4 0 0 1 4 3.97","key":"1gnv52"}],["path",{"d":"M14 15.003a1 1 0 0 1 1.517-.859l4.997 2.997a1 1 0 0 1 0 1.718l-4.997 2.997a1 1 0 0 1-1.517-.86z","key":"1weqy9"}],["path",{"d":"M14.12 3.88 16 2","key":"qol33r"}],["path",{"d":"M21 5a4 4 0 0 1-3.55 3.97","key":"5cxbf6"}],["path",{"d":"M3 21a4 4 0 0 1 3.81-4","key":"1fjd4g"}],["path",{"d":"M3 5a4 4 0 0 0 3.55 3.97","key":"1d7oge"}],["path",{"d":"M6 13H2","key":"82j7cp"}],["path",{"d":"m8 2 1.88 1.88","key":"fmnt4t"}],["path",{"d":"M9 7.13V6a3 3 0 1 1 6 0v1.13","key":"1vgav8"}]])
export const Building = ssrIcon('building', [["path",{"d":"M12 10h.01","key":"1nrarc"}],["path",{"d":"M12 14h.01","key":"1etili"}],["path",{"d":"M12 6h.01","key":"1vi96p"}],["path",{"d":"M16 10h.01","key":"1m94wz"}],["path",{"d":"M16 14h.01","key":"1gbofw"}],["path",{"d":"M16 6h.01","key":"1x0f13"}],["path",{"d":"M8 10h.01","key":"19clt8"}],["path",{"d":"M8 14h.01","key":"6423bh"}],["path",{"d":"M8 6h.01","key":"1dz90k"}],["path",{"d":"M9 22v-3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3","key":"cabbwy"}],["rect",{"x":"4","y":"2","width":"16","height":"20","rx":"2","key":"1uxh74"}]])
export const Building2 = ssrIcon('building-2', [["path",{"d":"M10 12h4","key":"a56b0p"}],["path",{"d":"M10 8h4","key":"1sr2af"}],["path",{"d":"M14 21v-3a2 2 0 0 0-4 0v3","key":"1rgiei"}],["path",{"d":"M6 10H4a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-2","key":"secmi2"}],["path",{"d":"M6 21V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v16","key":"16ra0t"}]])
export const Bus = ssrIcon('bus', [["path",{"d":"M8 6v6","key":"18i7km"}],["path",{"d":"M15 6v6","key":"1sg6z9"}],["path",{"d":"M2 12h19.6","key":"de5uta"}],["path",{"d":"M18 18h3s.5-1.7.8-2.8c.1-.4.2-.8.2-1.2 0-.4-.1-.8-.2-1.2l-1.4-5C20.1 6.8 19.1 6 18 6H4a2 2 0 0 0-2 2v10h3","key":"1wwztk"}],["circle",{"cx":"7","cy":"18","r":"2","key":"19iecd"}],["path",{"d":"M9 18h5","key":"lrx6i"}],["circle",{"cx":"16","cy":"18","r":"2","key":"1v4tcr"}]])
export const BusFront = ssrIcon('bus-front', [["path",{"d":"M4 6 2 7","key":"1mqr15"}],["path",{"d":"M10 6h4","key":"1itunk"}],["path",{"d":"m22 7-2-1","key":"1umjhc"}],["rect",{"width":"16","height":"16","x":"4","y":"3","rx":"2","key":"1wxw4b"}],["path",{"d":"M4 11h16","key":"mpoxn0"}],["path",{"d":"M8 15h.01","key":"a7atzg"}],["path",{"d":"M16 15h.01","key":"rnfrdf"}],["path",{"d":"M6 19v2","key":"1loha6"}],["path",{"d":"M18 21v-2","key":"sqyl04"}]])
export const Cable = ssrIcon('cable', [["path",{"d":"M17 19a1 1 0 0 1-1-1v-2a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2a1 1 0 0 1-1 1z","key":"trhst0"}],["path",{"d":"M17 21v-2","key":"ds4u3f"}],["path",{"d":"M19 14V6.5a1 1 0 0 0-7 0v11a1 1 0 0 1-7 0V10","key":"1mo9zo"}],["path",{"d":"M21 21v-2","key":"eo0ou"}],["path",{"d":"M3 5V3","key":"1k5hjh"}],["path",{"d":"M4 10a2 2 0 0 1-2-2V6a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2a2 2 0 0 1-2 2z","key":"1dd30t"}],["path",{"d":"M7 5V3","key":"1t1388"}]])
export const CableCar = ssrIcon('cable-car', [["path",{"d":"M10 3h.01","key":"lbucoy"}],["path",{"d":"M14 2h.01","key":"1k8aa1"}],["path",{"d":"m2 9 20-5","key":"1kz0j5"}],["path",{"d":"M12 12V6.5","key":"1vbrij"}],["rect",{"width":"16","height":"10","x":"4","y":"12","rx":"3","key":"if91er"}],["path",{"d":"M9 12v5","key":"3anwtq"}],["path",{"d":"M15 12v5","key":"5xh3zn"}],["path",{"d":"M4 17h16","key":"g4d7ey"}]])
export const Cake = ssrIcon('cake', [["path",{"d":"M20 21v-8a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8","key":"1w3rig"}],["path",{"d":"M4 16s.5-1 2-1 2.5 2 4 2 2.5-2 4-2 2.5 2 4 2 2-1 2-1","key":"n2jgmb"}],["path",{"d":"M2 21h20","key":"1nyx9w"}],["path",{"d":"M7 8v3","key":"1qtyvj"}],["path",{"d":"M12 8v3","key":"hwp4zt"}],["path",{"d":"M17 8v3","key":"1i6e5u"}],["path",{"d":"M7 4h.01","key":"1bh4kh"}],["path",{"d":"M12 4h.01","key":"1ujb9j"}],["path",{"d":"M17 4h.01","key":"1upcoc"}]])
export const CakeSlice = ssrIcon('cake-slice', [["path",{"d":"M16 13H3","key":"1wpj08"}],["path",{"d":"M16 17H3","key":"3lvfcd"}],["path",{"d":"m7.2 7.9-3.388 2.5A2 2 0 0 0 3 12.01V20a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1v-8.654c0-2-2.44-6.026-6.44-8.026a1 1 0 0 0-1.082.057L10.4 5.6","key":"1gmhf7"}],["circle",{"cx":"9","cy":"7","r":"2","key":"1305pl"}]])
export const Calculator = ssrIcon('calculator', [["rect",{"width":"16","height":"20","x":"4","y":"2","rx":"2","key":"1nb95v"}],["line",{"x1":"8","x2":"16","y1":"6","y2":"6","key":"x4nwl0"}],["line",{"x1":"16","x2":"16","y1":"14","y2":"18","key":"wjye3r"}],["path",{"d":"M16 10h.01","key":"1m94wz"}],["path",{"d":"M12 10h.01","key":"1nrarc"}],["path",{"d":"M8 10h.01","key":"19clt8"}],["path",{"d":"M12 14h.01","key":"1etili"}],["path",{"d":"M8 14h.01","key":"6423bh"}],["path",{"d":"M12 18h.01","key":"mhygvu"}],["path",{"d":"M8 18h.01","key":"lrp35t"}]])
export const Calendar = ssrIcon('calendar', [["path",{"d":"M8 2v3","key":"1ioesn"}],["path",{"d":"M16 2v3","key":"otl347"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}],["path",{"d":"M3 9h18","key":"1pudct"}]])
export const Calendar1 = ssrIcon('calendar-1', [["path",{"d":"M11 13h1v4","key":"10p4bv"}],["path",{"d":"M16 2v3","key":"otl347"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M8 2v3","key":"1ioesn"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const CalendarArrowDown = ssrIcon('calendar-arrow-down', [["path",{"d":"m14 17 4 4 4-4","key":"17qdjf"}],["path",{"d":"M16 2v3","key":"otl347"}],["path",{"d":"M18 13v8","key":"1a00n0"}],["path",{"d":"M21 10.354V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2h7.343","key":"1qsorh"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M8 2v3","key":"1ioesn"}]])
export const CalendarArrowUp = ssrIcon('calendar-arrow-up', [["path",{"d":"m14 17 4-4 4 4","key":"1qa3u6"}],["path",{"d":"M16 2v3","key":"otl347"}],["path",{"d":"M18 21v-8","key":"1ao88k"}],["path",{"d":"M21 10.343V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2h9","key":"185mot"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M8 2v3","key":"1ioesn"}]])
export const CalendarCheck = ssrIcon('calendar-check', [["path",{"d":"M8 2v3","key":"1ioesn"}],["path",{"d":"M16 2v3","key":"otl347"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"m9 15 2 2 4-4","key":"1grp1n"}]])
export const CalendarCheck2 = ssrIcon('calendar-check-2', [["path",{"d":"M 19 3 L 5 3","key":"1xn3iy"}],["path",{"d":"M 21 13 L 21 5","key":"102s58"}],["path",{"d":"M 21 5 A2 2 0 0 0 19 3","key":"1xylja"}],["path",{"d":"M 3 19 A2 2 0 0 0 5 21","key":"19jxbv"}],["path",{"d":"M 3 5 L 3 19","key":"1yylhw"}],["path",{"d":"M 5 3 A2 2 0 0 0 3 5","key":"164twa"}],["path",{"d":"m16 19 2 2 4-4","key":"1b14m6"}],["path",{"d":"M16 2v3","key":"otl347"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M5 21 L12.5 21","key":"1n38e0"}],["path",{"d":"M8 2v3","key":"1ioesn"}]])
export const CalendarClock = ssrIcon('calendar-clock', [["path",{"d":"M16 14v2.2l1.6 1","key":"fo4ql5"}],["path",{"d":"M16 2v3","key":"otl347"}],["path",{"d":"M21 7.338V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2h2.338","key":"7hb8p4"}],["path",{"d":"M3 9h5.859","key":"numkqi"}],["path",{"d":"M8 2v3","key":"1ioesn"}],["circle",{"cx":"16","cy":"16","r":"6","key":"qoo3c4"}]])
export const CalendarCog = ssrIcon('calendar-cog', [["path",{"d":"m15.228 16.852-.923-.383","key":"npixar"}],["path",{"d":"m15.228 19.148-.923.383","key":"51cr3n"}],["path",{"d":"M16 2v3","key":"otl347"}],["path",{"d":"m16.47 14.305.382.923","key":"obybxd"}],["path",{"d":"m16.852 20.772-.383.924","key":"dpfhf9"}],["path",{"d":"m19.148 15.228.383-.923","key":"1reyyz"}],["path",{"d":"m19.53 21.696-.382-.924","key":"1goivc"}],["path",{"d":"m20.773 16.852.924-.383","key":"ybmb4k"}],["path",{"d":"m20.773 19.148.924.383","key":"1c2d3p"}],["path",{"d":"M21 10.5V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2h5.5","key":"1e6z1y"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M8 2v3","key":"1ioesn"}],["circle",{"cx":"18","cy":"18","r":"3","key":"1xkwt0"}]])
export const CalendarDays = ssrIcon('calendar-days', [["path",{"d":"M8 2v3","key":"1ioesn"}],["path",{"d":"M16 2v3","key":"otl347"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M8 13h.01","key":"1sbv64"}],["path",{"d":"M12 13h.01","key":"y0uutt"}],["path",{"d":"M16 13h.01","key":"wip0gl"}],["path",{"d":"M8 17h.01","key":"p3bg7i"}],["path",{"d":"M12 17h.01","key":"p32p05"}],["path",{"d":"M16 17h.01","key":"ql8jdd"}]])
export const CalendarFold = ssrIcon('calendar-fold', [["path",{"d":"M16 2v3","key":"otl347"}],["path",{"d":"M21 15V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2h10v-5a1 1 0 011-1za2.4 2.4 0 01-.706 1.706l-3.588 3.588A2.4 2.4 0 0115 21","key":"4uit17"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M8 2v3","key":"1ioesn"}]])
export const CalendarHeart = ssrIcon('calendar-heart', [["path",{"d":"M12.127 21H5a2 2 0 01-2-2V5a2 2 0 012-2h14a2 2 0 012 2v5.125","key":"1fsxpc"}],["path",{"d":"M14.62 17.8A2.25 2.25 0 1118 14.836a2.25 2.25 0 113.38 2.966l-2.626 2.856a.998.998 0 01-1.507 0z","key":"1gk3ue"}],["path",{"d":"M16 2v3","key":"otl347"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M8 2v3","key":"1ioesn"}]])
export const CalendarMinus = ssrIcon('calendar-minus', [["path",{"d":"M16 18h6","key":"987eiv"}],["path",{"d":"M16 2v3","key":"otl347"}],["path",{"d":"M21 14V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2h8.3","key":"gcu0od"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M8 2v3","key":"1ioesn"}]])
export const CalendarMinus2 = ssrIcon('calendar-minus-2', [["path",{"d":"M8 2v3","key":"1ioesn"}],["path",{"d":"M16 2v3","key":"otl347"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M10 15h4","key":"192ueg"}]])
export const CalendarOff = ssrIcon('calendar-off', [["path",{"d":"M16 2v3","key":"otl347"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M21 9h-5.5","key":"1g344v"}],["path",{"d":"M3 9h6","key":"1q2djq"}],["path",{"d":"M3.586 3.586A2 2 0 003 5v14a2 2 0 002 2h14a2 2 0 001.414-.586","key":"1g7ltu"}],["path",{"d":"M8.656 3H19a2 2 0 012 2v10.344","key":"1bwpd1"}]])
export const CalendarPlus = ssrIcon('calendar-plus', [["path",{"d":"M16 18h6","key":"987eiv"}],["path",{"d":"M16 2v3","key":"otl347"}],["path",{"d":"M19 15v6","key":"10aioa"}],["path",{"d":"M21 11.5V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2h8.3","key":"jgwkxf"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M8 2v3","key":"1ioesn"}]])
export const CalendarPlus2 = ssrIcon('calendar-plus-2', [["path",{"d":"M8 2v3","key":"1ioesn"}],["path",{"d":"M16 2v3","key":"otl347"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M10 15h4","key":"192ueg"}],["path",{"d":"M12 13v4","key":"1il4po"}]])
export const CalendarRange = ssrIcon('calendar-range', [["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}],["path",{"d":"M16 2v3","key":"otl347"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M8 2v3","key":"1ioesn"}],["path",{"d":"M17 13h-6","key":"1qbiup"}],["path",{"d":"M13 17H7","key":"1x38vv"}],["path",{"d":"M7 13h.01","key":"1vezk1"}],["path",{"d":"M17 17h.01","key":"1sd3ek"}]])
export const CalendarSearch = ssrIcon('calendar-search', [["path",{"d":"M16 2v3","key":"otl347"}],["path",{"d":"M21 10.69V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2h7.25","key":"h6gkkz"}],["path",{"d":"m22 21-1.875-1.875","key":"1dzjql"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M8 2v3","key":"1ioesn"}],["circle",{"cx":"18","cy":"17","r":"3","key":"1hty4x"}]])
export const CalendarSync = ssrIcon('calendar-sync', [["path",{"d":"M11 10v4h4","key":"172dkj"}],["path",{"d":"m11 14 1.535-1.605a5 5 0 018 1.5","key":"jekqcd"}],["path",{"d":"M16 2v3","key":"otl347"}],["path",{"d":"m21 18-1.535 1.605a5 5 0 01-8-1.5","key":"n107hu"}],["path",{"d":"M21 22v-4h-4","key":"hrummi"}],["path",{"d":"M21 8.517V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2h3.517","key":"yafrba"}],["path",{"d":"M3 9h4","key":"rnfnj5"}],["path",{"d":"M8 2v3","key":"1ioesn"}]])
export const CalendarX = ssrIcon('calendar-x', [["path",{"d":"M8 2v3","key":"1ioesn"}],["path",{"d":"M16 2v3","key":"otl347"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"m14 13-4 4","key":"1gib57"}],["path",{"d":"m10 13 4 4","key":"153uiq"}]])
export const CalendarX2 = ssrIcon('calendar-x-2', [["path",{"d":"M16 2v3","key":"otl347"}],["path",{"d":"m17 16 5 5","key":"1a37d9"}],["path",{"d":"m17 21 5-5","key":"1b797a"}],["path",{"d":"M21 12V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2h8","key":"14ws7l"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M8 2v3","key":"1ioesn"}]])
export const Calendars = ssrIcon('calendars', [["path",{"d":"M12 2v2","key":"tus03m"}],["path",{"d":"M15.726 21.01A2 2 0 0 1 14 22H4a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2","key":"j6srht"}],["path",{"d":"M18 2v2","key":"1kh14s"}],["path",{"d":"M2 13h2","key":"13gyu8"}],["path",{"d":"M8 8h14","key":"12jxz2"}],["rect",{"x":"8","y":"3","width":"14","height":"14","rx":"2","key":"nsru6w"}]])
export const Camera = ssrIcon('camera', [["path",{"d":"M13.997 4a2 2 0 0 1 1.76 1.05l.486.9A2 2 0 0 0 18.003 7H20a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h1.997a2 2 0 0 0 1.759-1.048l.489-.904A2 2 0 0 1 10.004 4z","key":"18u6gg"}],["circle",{"cx":"12","cy":"13","r":"3","key":"1vg3eu"}]])
export const CameraOff = ssrIcon('camera-off', [["path",{"d":"M14.564 14.558a3 3 0 1 1-4.122-4.121","key":"1rnrzw"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M20 20H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h1.997a2 2 0 0 0 .819-.175","key":"1x3arw"}],["path",{"d":"M9.695 4.024A2 2 0 0 1 10.004 4h3.993a2 2 0 0 1 1.76 1.05l.486.9A2 2 0 0 0 18.003 7H20a2 2 0 0 1 2 2v7.344","key":"1i84u0"}]])
export const ChartCandlestick = ssrIcon('chart-candlestick', [["path",{"d":"M9 5v4","key":"14uxtq"}],["rect",{"width":"4","height":"6","x":"7","y":"9","rx":"1","key":"f4fvz0"}],["path",{"d":"M9 15v2","key":"r5rk32"}],["path",{"d":"M17 3v2","key":"1l2re6"}],["rect",{"width":"4","height":"8","x":"15","y":"5","rx":"1","key":"z38je5"}],["path",{"d":"M17 13v3","key":"5l0wba"}],["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}]])
export const Candy = ssrIcon('candy', [["path",{"d":"M10 7v10.9","key":"1gynux"}],["path",{"d":"M14 6.1V17","key":"116kdf"}],["path",{"d":"M16 7V3a1 1 0 0 1 1.707-.707 2.5 2.5 0 0 0 2.152.717 1 1 0 0 1 1.131 1.131 2.5 2.5 0 0 0 .717 2.152A1 1 0 0 1 21 8h-4","key":"gpb6xx"}],["path",{"d":"M16.536 7.465a5 5 0 0 0-7.072 0l-2 2a5 5 0 0 0 0 7.07 5 5 0 0 0 7.072 0l2-2a5 5 0 0 0 0-7.07","key":"1tsln4"}],["path",{"d":"M8 17v4a1 1 0 0 1-1.707.707 2.5 2.5 0 0 0-2.152-.717 1 1 0 0 1-1.131-1.131 2.5 2.5 0 0 0-.717-2.152A1 1 0 0 1 3 16h4","key":"qexcha"}]])
export const CandyCane = ssrIcon('candy-cane', [["path",{"d":"m10.8 5 2.111 4.223","key":"11kb8w"}],["path",{"d":"M17.75 7 15 2.1","key":"12x7e8"}],["path",{"d":"m4.874 14.647 2.12 4.24","key":"ccpt4b"}],["path",{"d":"M5.7 21a2 2 0 0 1-3.5-2l8.6-14a6 6 0 0 1 10.4 6 2 2 0 1 1-3.464-2 2 2 0 1 0-3.464-2z","key":"u5e8z4"}],["path",{"d":"m7.906 9.712 2.005 4.411","key":"1k0qph"}]])
export const CandyOff = ssrIcon('candy-off', [["path",{"d":"M10 10v7.9","key":"m8g9tt"}],["path",{"d":"M11.802 6.145a5 5 0 0 1 6.053 6.053","key":"dn87i3"}],["path",{"d":"M14 6.1v2.243","key":"1kzysn"}],["path",{"d":"m15.5 15.571-.964.964a5 5 0 0 1-7.071 0 5 5 0 0 1 0-7.07l.964-.965","key":"3sxy18"}],["path",{"d":"M16 7V3a1 1 0 0 1 1.707-.707 2.5 2.5 0 0 0 2.152.717 1 1 0 0 1 1.131 1.131 2.5 2.5 0 0 0 .717 2.152A1 1 0 0 1 21 8h-4","key":"gpb6xx"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M8 17v4a1 1 0 0 1-1.707.707 2.5 2.5 0 0 0-2.152-.717 1 1 0 0 1-1.131-1.131 2.5 2.5 0 0 0-.717-2.152A1 1 0 0 1 3 16h4","key":"qexcha"}]])
export const Cannabis = ssrIcon('cannabis', [["path",{"d":"M12 22v-4","key":"1utk9m"}],["path",{"d":"M7 12c-1.5 0-4.5 1.5-5 3 3.5 1.5 6 1 6 1-1.5 1.5-2 3.5-2 5 2.5 0 4.5-1.5 6-3 1.5 1.5 3.5 3 6 3 0-1.5-.5-3.5-2-5 0 0 2.5.5 6-1-.5-1.5-3.5-3-5-3 1.5-1 4-4 4-6-2.5 0-5.5 1.5-7 3 0-2.5-.5-5-2-7-1.5 2-2 4.5-2 7-1.5-1.5-4.5-3-7-3 0 2 2.5 5 4 6","key":"1mezod"}]])
export const CannabisOff = ssrIcon('cannabis-off', [["path",{"d":"M12 22v-4c1.5 1.5 3.5 3 6 3 0-1.5-.5-3.5-2-5","key":"1bqfb7"}],["path",{"d":"M13.988 8.327C13.902 6.054 13.365 3.82 12 2a9.3 9.3 0 0 0-1.445 2.9","key":"1p520n"}],["path",{"d":"M17.375 11.725C18.882 10.53 21 7.841 21 6c-2.324 0-5.08 1.296-6.662 2.684","key":"q2itvb"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M21.024 15.378A15 15 0 0 0 22 15c-.426-1.279-2.67-2.557-4.25-2.907","key":"j9amvs"}],["path",{"d":"M6.995 6.992C5.714 6.4 4.29 6 3 6c0 2 2.5 5 4 6-1.5 0-4.5 1.5-5 3 3.5 1.5 6 1 6 1-1.5 1.5-2 3.5-2 5 2.5 0 4.5-1.5 6-3","key":"8gmd5g"}]])
export const Captions = ssrIcon('captions', [["rect",{"width":"18","height":"14","x":"3","y":"5","rx":"2","ry":"2","key":"12ruh7"}],["path",{"d":"M7 15h4M15 15h2M7 11h2M13 11h4","key":"1ueiar"}]])
export const CaptionsOff = ssrIcon('captions-off', [["path",{"d":"M10.5 5H19a2 2 0 0 1 2 2v8.5","key":"jqtk4d"}],["path",{"d":"M17 11h-.5","key":"1961ue"}],["path",{"d":"M19 19H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2","key":"1keqsi"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M7 11h4","key":"1o1z6v"}],["path",{"d":"M7 15h2.5","key":"1ina1g"}]])
export const Car = ssrIcon('car', [["path",{"d":"M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2","key":"5owen"}],["circle",{"cx":"7","cy":"17","r":"2","key":"u2ysq9"}],["path",{"d":"M9 17h6","key":"r8uit2"}],["circle",{"cx":"17","cy":"17","r":"2","key":"axvx0g"}]])
export const CarBattery = ssrIcon('car-battery', [["path",{"d":"M14 13h4","key":"xb9564"}],["path",{"d":"M16 15v-4","key":"rpmtp7"}],["path",{"d":"M18 5v2","key":"n2sebz"}],["path",{"d":"M6 13h4","key":"vm80m7"}],["path",{"d":"M6 5v2","key":"h3tt00"}],["rect",{"x":"2","y":"7","width":"20","height":"12","rx":"2","key":"uzf593"}]])
export const CarFront = ssrIcon('car-front', [["path",{"d":"m21 8-2 2-1.5-3.7A2 2 0 0 0 15.646 5H8.4a2 2 0 0 0-1.903 1.257L5 10 3 8","key":"1imjwt"}],["path",{"d":"M7 14h.01","key":"1qa3f1"}],["path",{"d":"M17 14h.01","key":"7oqj8z"}],["rect",{"width":"18","height":"8","x":"3","y":"10","rx":"2","key":"a7itu8"}],["path",{"d":"M5 18v2","key":"ppbyun"}],["path",{"d":"M19 18v2","key":"gy7782"}]])
export const CarTaxiFront = ssrIcon('car-taxi-front', [["path",{"d":"M10 2h4","key":"n1abiw"}],["path",{"d":"m21 8-2 2-1.5-3.7A2 2 0 0 0 15.646 5H8.4a2 2 0 0 0-1.903 1.257L5 10 3 8","key":"1imjwt"}],["path",{"d":"M7 14h.01","key":"1qa3f1"}],["path",{"d":"M17 14h.01","key":"7oqj8z"}],["rect",{"width":"18","height":"8","x":"3","y":"10","rx":"2","key":"a7itu8"}],["path",{"d":"M5 18v2","key":"ppbyun"}],["path",{"d":"M19 18v2","key":"gy7782"}]])
export const Caravan = ssrIcon('caravan', [["path",{"d":"M18 19V9a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v8a2 2 0 0 0 2 2h2","key":"19jm3t"}],["path",{"d":"M2 9h3a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1H2","key":"13hakp"}],["path",{"d":"M22 17v1a1 1 0 0 1-1 1H10v-9a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v9","key":"1crci8"}],["circle",{"cx":"8","cy":"19","r":"2","key":"t8fc5s"}]])
export const CardSim = ssrIcon('card-sim', [["path",{"d":"M12 14v4","key":"1thi36"}],["path",{"d":"M14.172 2a2 2 0 0 1 1.414.586l3.828 3.828A2 2 0 0 1 20 7.828V20a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z","key":"1o66bk"}],["path",{"d":"M8 14h8","key":"1fgep2"}],["rect",{"x":"8","y":"10","width":"8","height":"8","rx":"1","key":"1aonk6"}]])
export const Carrot = ssrIcon('carrot', [["path",{"d":"M15 16a1 1 0 0 0-7-7q-4 4-5.987 12.385a.5.5 0 0 0 .602.602Q11 20 15 16l-3-3","key":"1ta62j"}],["path",{"d":"M15 9q4 4 7 0-3-4-7 0 4-4 0-7-4 3 0 7","key":"1svf7i"}],["path",{"d":"m8 15-2.58-2.58","key":"7t238r"}]])
export const CaseLower = ssrIcon('case-lower', [["path",{"d":"M10 9v7","key":"ylp826"}],["path",{"d":"M14 6v10","key":"1jy4vg"}],["circle",{"cx":"17.5","cy":"12.5","r":"3.5","key":"1a9481"}],["circle",{"cx":"6.5","cy":"12.5","r":"3.5","key":"2jlv1r"}]])
export const CaseSensitive = ssrIcon('case-sensitive', [["path",{"d":"m2 16 4.039-9.69a.5.5 0 0 1 .923 0L11 16","key":"d5nyq2"}],["path",{"d":"M22 9v7","key":"pvm9v3"}],["path",{"d":"M3.304 13h6.392","key":"1q3zxz"}],["circle",{"cx":"18.5","cy":"12.5","r":"3.5","key":"z97x68"}]])
export const CaseUpper = ssrIcon('case-upper', [["path",{"d":"M15 11h4.5a1 1 0 0 1 0 5h-4a.5.5 0 0 1-.5-.5v-9a.5.5 0 0 1 .5-.5h3a1 1 0 0 1 0 5","key":"nxs35"}],["path",{"d":"m2 16 4.039-9.69a.5.5 0 0 1 .923 0L11 16","key":"d5nyq2"}],["path",{"d":"M3.304 13h6.392","key":"1q3zxz"}]])
export const CassetteTape = ssrIcon('cassette-tape', [["rect",{"width":"20","height":"16","x":"2","y":"4","rx":"2","key":"18n3k1"}],["circle",{"cx":"8","cy":"10","r":"2","key":"1xl4ub"}],["path",{"d":"M8 12h8","key":"1wcyev"}],["circle",{"cx":"16","cy":"10","r":"2","key":"r14t7q"}],["path",{"d":"m6 20 .7-2.9A1.4 1.4 0 0 1 8.1 16h7.8a1.4 1.4 0 0 1 1.4 1l.7 3","key":"l01ucn"}]])
export const Cast = ssrIcon('cast', [["path",{"d":"M2 8V6a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-6","key":"3zrzxg"}],["path",{"d":"M2 12a9 9 0 0 1 8 8","key":"g6cvee"}],["path",{"d":"M2 16a5 5 0 0 1 4 4","key":"1y1dii"}],["line",{"x1":"2","x2":"2.01","y1":"20","y2":"20","key":"xu2jvo"}]])
export const Castle = ssrIcon('castle', [["path",{"d":"M10 5V3","key":"1y54qe"}],["path",{"d":"M14 5V3","key":"m6isi"}],["path",{"d":"M15 21v-3a3 3 0 0 0-6 0v3","key":"lbp5hj"}],["path",{"d":"M18 3v8","key":"2ollhf"}],["path",{"d":"M18 5H6","key":"98imr9"}],["path",{"d":"M22 11H2","key":"1lmjae"}],["path",{"d":"M22 9v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9","key":"1rly83"}],["path",{"d":"M6 3v8","key":"csox7g"}]])
export const Cat = ssrIcon('cat', [["path",{"d":"M12 5c.67 0 1.35.09 2 .26 1.78-2 5.03-2.84 6.42-2.26 1.4.58-.42 7-.42 7 .57 1.07 1 2.24 1 3.44C21 17.9 16.97 21 12 21s-9-3-9-7.56c0-1.25.5-2.4 1-3.44 0 0-1.89-6.42-.5-7 1.39-.58 4.72.23 6.5 2.23A9.04 9.04 0 0 1 12 5Z","key":"x6xyqk"}],["path",{"d":"M8 14v.5","key":"1nzgdb"}],["path",{"d":"M16 14v.5","key":"1lajdz"}],["path",{"d":"M11.25 16.25h1.5L12 17l-.75-.75Z","key":"12kq1m"}]])
export const Cctv = ssrIcon('cctv', [["path",{"d":"M16.75 12h3.632a1 1 0 0 1 .894 1.447l-2.034 4.069a1 1 0 0 1-1.708.134l-2.124-2.97","key":"ir91b5"}],["path",{"d":"M17.106 9.053a1 1 0 0 1 .447 1.341l-3.106 6.211a1 1 0 0 1-1.342.447L3.61 12.3a2.92 2.92 0 0 1-1.3-3.91L3.69 5.6a2.92 2.92 0 0 1 3.92-1.3z","key":"jlp8i1"}],["path",{"d":"M2 19h3.76a2 2 0 0 0 1.8-1.1L9 15","key":"19bib8"}],["path",{"d":"M2 21v-4","key":"l40lih"}],["path",{"d":"M7 9h.01","key":"19b3jx"}]])
export const CctvOff = ssrIcon('cctv-off', [["path",{"d":"m12.309 6.652 4.797 2.401a1 1 0 0 1 .447 1.341l-.501 1.001.605.605h2.725a1 1 0 0 1 .894 1.447l-.724 1.448","key":"e75roo"}],["path",{"d":"m15.166 15.166-.719 1.439a1 1 0 0 1-1.342.447L3.61 12.3a2.92 2.92 0 0 1-1.3-3.91L3.69 5.6a2.9 2.9 0 0 1 .873-1.037","key":"1h9o5r"}],["path",{"d":"M2 19h3.76a2 2 0 0 0 1.8-1.1l1.441-2.902","key":"1askrb"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M2 21v-4","key":"l40lih"}],["path",{"d":"M7 9h.01","key":"19b3jx"}]])
export const ChartBarDecreasing = ssrIcon('chart-bar-decreasing', [["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}],["path",{"d":"M7 11h8","key":"1feolt"}],["path",{"d":"M7 16h3","key":"ur6vzw"}],["path",{"d":"M7 6h12","key":"sz5b0d"}]])
export const ChartBarIncreasing = ssrIcon('chart-bar-increasing', [["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}],["path",{"d":"M7 11h8","key":"1feolt"}],["path",{"d":"M7 16h12","key":"wsnu98"}],["path",{"d":"M7 6h3","key":"w9rmul"}]])
export const ChartBarStacked = ssrIcon('chart-bar-stacked', [["path",{"d":"M11 13v4","key":"vyy2rb"}],["path",{"d":"M15 5v4","key":"1gx88a"}],["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}],["rect",{"x":"7","y":"13","width":"9","height":"4","rx":"1","key":"1iip1u"}],["rect",{"x":"7","y":"5","width":"12","height":"4","rx":"1","key":"1anskk"}]])
export const ChartColumnDecreasing = ssrIcon('chart-column-decreasing', [["path",{"d":"M13 17V9","key":"1fwyjl"}],["path",{"d":"M18 17v-3","key":"1sqioe"}],["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}],["path",{"d":"M8 17V5","key":"1wzmnc"}]])
export const ChartColumnStacked = ssrIcon('chart-column-stacked', [["path",{"d":"M11 13H7","key":"t0o9gq"}],["path",{"d":"M19 9h-4","key":"rera1j"}],["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}],["rect",{"x":"15","y":"5","width":"4","height":"12","rx":"1","key":"q8uenq"}],["rect",{"x":"7","y":"8","width":"4","height":"9","rx":"1","key":"sr5ea"}]])
export const ChartGantt = ssrIcon('chart-gantt', [["path",{"d":"M10 6h8","key":"zvc2xc"}],["path",{"d":"M12 16h6","key":"yi5mkt"}],["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}],["path",{"d":"M8 11h7","key":"wz2hg0"}]])
export const ChartLine = ssrIcon('chart-line', [["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}],["path",{"d":"m19 9-5 5-4-4-3 3","key":"2osh9i"}]])
export const ChartNetwork = ssrIcon('chart-network', [["path",{"d":"m13.11 7.664 1.78 2.672","key":"go2gg9"}],["path",{"d":"m14.162 12.788-3.324 1.424","key":"11x848"}],["path",{"d":"m20 4-6.06 1.515","key":"1wxxh7"}],["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}],["circle",{"cx":"12","cy":"6","r":"2","key":"1jj5th"}],["circle",{"cx":"16","cy":"12","r":"2","key":"4ma0v8"}],["circle",{"cx":"9","cy":"15","r":"2","key":"lf2ghp"}]])
export const ChartNoAxesColumnDecreasing = ssrIcon('chart-no-axes-column-decreasing', [["path",{"d":"M5 21V3","key":"clc1r8"}],["path",{"d":"M12 21V9","key":"uvy0l4"}],["path",{"d":"M19 21v-6","key":"tkawy9"}]])
export const ChartNoAxesCombined = ssrIcon('chart-no-axes-combined', [["path",{"d":"M12 16v5","key":"zza2cw"}],["path",{"d":"M16 14.639V21","key":"1s85h0"}],["path",{"d":"M20 10.656V21","key":"q45596"}],["path",{"d":"m22 3-8.646 8.646a.5.5 0 0 1-.708 0L9.354 8.354a.5.5 0 0 0-.707 0L2 15","key":"1fw8x9"}],["path",{"d":"M4 18.463V21","key":"1otddq"}],["path",{"d":"M8 14.656V21","key":"1t2idw"}]])
export const ChartNoAxesGantt = ssrIcon('chart-no-axes-gantt', [["path",{"d":"M6 5h12","key":"fvfigv"}],["path",{"d":"M4 12h10","key":"oujl3d"}],["path",{"d":"M12 19h8","key":"baeox8"}]])
export const ChartPie = ssrIcon('chart-pie', [["path",{"d":"M21 12c.552 0 1.005-.449.95-.998a10 10 0 0 0-8.953-8.951c-.55-.055-.998.398-.998.95v8a1 1 0 0 0 1 1z","key":"pzmjnu"}],["path",{"d":"M21.21 15.89A10 10 0 1 1 8 2.83","key":"k2fpak"}]])
export const ChartScatter = ssrIcon('chart-scatter', [["circle",{"cx":"7.5","cy":"7.5","r":".5","fill":"currentColor","key":"kqv944"}],["circle",{"cx":"18.5","cy":"5.5","r":".5","fill":"currentColor","key":"lysivs"}],["circle",{"cx":"11.5","cy":"11.5","r":".5","fill":"currentColor","key":"byv1b8"}],["circle",{"cx":"7.5","cy":"16.5","r":".5","fill":"currentColor","key":"nkw3mc"}],["circle",{"cx":"17.5","cy":"14.5","r":".5","fill":"currentColor","key":"1gjh6j"}],["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}]])
export const ChartSpline = ssrIcon('chart-spline', [["path",{"d":"M3 3v16a2 2 0 0 0 2 2h16","key":"c24i48"}],["path",{"d":"M7 16c.5-2 1.5-7 4-7 2 0 2 3 4 3 2.5 0 4.5-5 5-7","key":"lw07rv"}]])
export const Check = ssrIcon('check', [["path",{"d":"M20 6 9 17l-5-5","key":"1gmf2c"}]])
export const CheckCheck = ssrIcon('check-check', [["path",{"d":"M18 6 7 17l-5-5","key":"116fxf"}],["path",{"d":"m22 10-7.5 7.5L13 16","key":"ke71qq"}]])
export const CircleCheckBig = ssrIcon('circle-check-big', [["path",{"d":"M21.801 10A10 10 0 1 1 17 3.335","key":"yps3ct"}],["path",{"d":"m9 11 3 3L22 4","key":"1pflzl"}]])
export const CircleCheck = ssrIcon('circle-check', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"m16 9-5.5 5.5L8 12","key":"xofnsj"}]])
export const CheckLine = ssrIcon('check-line', [["path",{"d":"M20 4L9 15","key":"1qkx8z"}],["path",{"d":"M21 19L3 19","key":"100sma"}],["path",{"d":"M9 15L4 10","key":"9zxff7"}]])
export const SquareCheckBig = ssrIcon('square-check-big', [["path",{"d":"M21 10.656V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h12.344","key":"2acyp4"}],["path",{"d":"m9 11 3 3L22 4","key":"1pflzl"}]])
export const SquareCheck = ssrIcon('square-check', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"m16 9-5.5 5.5L8 12","key":"xofnsj"}]])
export const ChefHat = ssrIcon('chef-hat', [["path",{"d":"M17 21a1 1 0 0 0 1-1v-5.35c0-.457.316-.844.727-1.041a4 4 0 0 0-2.134-7.589 5 5 0 0 0-9.186 0 4 4 0 0 0-2.134 7.588c.411.198.727.585.727 1.041V20a1 1 0 0 0 1 1Z","key":"1qvrer"}],["path",{"d":"M6 17h12","key":"1jwigz"}]])
export const Cherry = ssrIcon('cherry', [["path",{"d":"M2 17a5 5 0 0 0 10 0c0-2.76-2.5-5-5-3-2.5-2-5 .24-5 3Z","key":"cvxqlc"}],["path",{"d":"M12 17a5 5 0 0 0 10 0c0-2.76-2.5-5-5-3-2.5-2-5 .24-5 3Z","key":"1ostrc"}],["path",{"d":"M7 14c3.22-2.91 4.29-8.75 5-12 1.66 2.38 4.94 9 5 12","key":"hqx58h"}],["path",{"d":"M22 9c-4.29 0-7.14-2.33-10-7 5.71 0 10 4.67 10 7Z","key":"eykp1o"}]])
export const ChessBishop = ssrIcon('chess-bishop', [["path",{"d":"M5 20a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v1a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1z","key":"b89hwq"}],["path",{"d":"M15 18c1.5-.615 3-2.461 3-4.923C18 8.769 14.5 4.462 12 2 9.5 4.462 6 8.77 6 13.077 6 15.539 7.5 17.385 9 18","key":"8jdkhx"}],["path",{"d":"m16 7-2.5 2.5","key":"1jq90w"}],["path",{"d":"M9 2h6","key":"1jrp98"}]])
export const ChessKing = ssrIcon('chess-king', [["path",{"d":"M4 20a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v1a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z","key":"mqzwx6"}],["path",{"d":"m6.7 18-1-1C4.35 15.682 3 14.09 3 12a5 5 0 0 1 4.95-5c1.584 0 2.7.455 4.05 1.818C13.35 7.455 14.466 7 16.05 7A5 5 0 0 1 21 12c0 2.082-1.359 3.673-2.7 5l-1 1","key":"1gdt1g"}],["path",{"d":"M10 4h4","key":"1xpv9s"}],["path",{"d":"M12 2v6.818","key":"b17a49"}]])
export const ChessKnight = ssrIcon('chess-knight', [["path",{"d":"M5 20a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v1a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1z","key":"b89hwq"}],["path",{"d":"M16.5 18c1-2 2.5-5 2.5-9a7 7 0 0 0-7-7H6.635a1 1 0 0 0-.768 1.64L7 5l-2.32 5.802a2 2 0 0 0 .95 2.526l2.87 1.456","key":"axbnlq"}],["path",{"d":"m15 5 1.425-1.425","key":"15xz8w"}],["path",{"d":"m17 8 1.53-1.53","key":"15zhqh"}],["path",{"d":"M9.713 12.185 7 18","key":"1ocm0l"}]])
export const ChessPawn = ssrIcon('chess-pawn', [["path",{"d":"M5 20a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v1a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1z","key":"b89hwq"}],["path",{"d":"m14.5 10 1.5 8","key":"cim3qy"}],["path",{"d":"M7 10h10","key":"1101jm"}],["path",{"d":"m8 18 1.5-8","key":"ja3yjd"}],["circle",{"cx":"12","cy":"6","r":"4","key":"1frrej"}]])
export const ChessQueen = ssrIcon('chess-queen', [["path",{"d":"M4 20a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v1a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z","key":"mqzwx6"}],["path",{"d":"m12.474 5.943 1.567 5.34a1 1 0 0 0 1.75.328l2.616-3.402","key":"1js4gl"}],["path",{"d":"m20 9-3 9","key":"r75r3f"}],["path",{"d":"m5.594 8.209 2.615 3.403a1 1 0 0 0 1.75-.329l1.567-5.34","key":"1joj19"}],["path",{"d":"M7 18 4 9","key":"1mfzj8"}],["circle",{"cx":"12","cy":"4","r":"2","key":"muu5ef"}],["circle",{"cx":"20","cy":"7","r":"2","key":"9w7p1x"}],["circle",{"cx":"4","cy":"7","r":"2","key":"1d9wy8"}]])
export const ChessRook = ssrIcon('chess-rook', [["path",{"d":"M5 20a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v1a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1z","key":"b89hwq"}],["path",{"d":"M10 2v2","key":"7u0qdc"}],["path",{"d":"M14 2v2","key":"6buw04"}],["path",{"d":"m17 18-1-9","key":"10nd7q"}],["path",{"d":"M6 2v5a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V2","key":"uxf4yx"}],["path",{"d":"M6 4h12","key":"1x2ag7"}],["path",{"d":"m7 18 1-9","key":"1si9vq"}]])
export const ChevronDown = ssrIcon('chevron-down', [["path",{"d":"m6 9 6 6 6-6","key":"qrunsl"}]])
export const CircleChevronDown = ssrIcon('circle-chevron-down', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"m16 10-4 4-4-4","key":"894hmk"}]])
export const SquareChevronDown = ssrIcon('square-chevron-down', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"m16 10-4 4-4-4","key":"894hmk"}]])
export const ChevronFirst = ssrIcon('chevron-first', [["path",{"d":"m17 18-6-6 6-6","key":"1yerx2"}],["path",{"d":"M7 6v12","key":"1p53r6"}]])
export const ChevronLast = ssrIcon('chevron-last', [["path",{"d":"m7 18 6-6-6-6","key":"lwmzdw"}],["path",{"d":"M17 6v12","key":"1o0aio"}]])
export const ChevronLeft = ssrIcon('chevron-left', [["path",{"d":"m15 18-6-6 6-6","key":"1wnfg3"}]])
export const CircleChevronLeft = ssrIcon('circle-chevron-left', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"m14 16-4-4 4-4","key":"ojs7w8"}]])
export const SquareChevronLeft = ssrIcon('square-chevron-left', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"m14 16-4-4 4-4","key":"ojs7w8"}]])
export const ChevronRight = ssrIcon('chevron-right', [["path",{"d":"m9 18 6-6-6-6","key":"mthhwq"}]])
export const CircleChevronRight = ssrIcon('circle-chevron-right', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"m10 8 4 4-4 4","key":"1wy4r4"}]])
export const SquareChevronRight = ssrIcon('square-chevron-right', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"m10 8 4 4-4 4","key":"1wy4r4"}]])
export const ChevronUp = ssrIcon('chevron-up', [["path",{"d":"m18 15-6-6-6 6","key":"153udz"}]])
export const CircleChevronUp = ssrIcon('circle-chevron-up', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"m8 14 4-4 4 4","key":"fy2ptz"}]])
export const SquareChevronUp = ssrIcon('square-chevron-up', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"m8 14 4-4 4 4","key":"fy2ptz"}]])
export const ChevronsDown = ssrIcon('chevrons-down', [["path",{"d":"m7 6 5 5 5-5","key":"1lc07p"}],["path",{"d":"m7 13 5 5 5-5","key":"1d48rs"}]])
export const ChevronsDownUp = ssrIcon('chevrons-down-up', [["path",{"d":"m7 20 5-5 5 5","key":"13a0gw"}],["path",{"d":"m7 4 5 5 5-5","key":"1kwcof"}]])
export const ChevronsLeft = ssrIcon('chevrons-left', [["path",{"d":"m11 17-5-5 5-5","key":"13zhaf"}],["path",{"d":"m18 17-5-5 5-5","key":"h8a8et"}]])
export const ChevronsLeftRight = ssrIcon('chevrons-left-right', [["path",{"d":"m9 7-5 5 5 5","key":"j5w590"}],["path",{"d":"m15 7 5 5-5 5","key":"1bl6da"}]])
export const ChevronsLeftRightEllipsis = ssrIcon('chevrons-left-right-ellipsis', [["path",{"d":"M12 12h.01","key":"1mp3jc"}],["path",{"d":"M16 12h.01","key":"1l6xoz"}],["path",{"d":"m17 7 5 5-5 5","key":"1xlxn0"}],["path",{"d":"m7 7-5 5 5 5","key":"19njba"}],["path",{"d":"M8 12h.01","key":"czm47f"}]])
export const ChevronsRight = ssrIcon('chevrons-right', [["path",{"d":"m6 17 5-5-5-5","key":"xnjwq"}],["path",{"d":"m13 17 5-5-5-5","key":"17xmmf"}]])
export const ChevronsRightLeft = ssrIcon('chevrons-right-left', [["path",{"d":"m20 17-5-5 5-5","key":"30x0n2"}],["path",{"d":"m4 17 5-5-5-5","key":"16spf4"}]])
export const ChevronsUp = ssrIcon('chevrons-up', [["path",{"d":"m17 11-5-5-5 5","key":"e8nh98"}],["path",{"d":"m17 18-5-5-5 5","key":"2avn1x"}]])
export const ChevronsUpDown = ssrIcon('chevrons-up-down', [["path",{"d":"m7 15 5 5 5-5","key":"1hf1tw"}],["path",{"d":"m7 9 5-5 5 5","key":"sgt6xg"}]])
export const Church = ssrIcon('church', [["path",{"d":"M10 9h4","key":"u4k05v"}],["path",{"d":"M12 7v5","key":"ma6bk"}],["path",{"d":"M14 21v-3a2 2 0 0 0-4 0v3","key":"1rgiei"}],["path",{"d":"m18 9 3.52 2.147a1 1 0 0 1 .48.854V19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6.999a1 1 0 0 1 .48-.854L6 9","key":"flvdwo"}],["path",{"d":"M6 21V7a1 1 0 0 1 .376-.782l5-3.999a1 1 0 0 1 1.249.001l5 4A1 1 0 0 1 18 7v14","key":"a5i0n2"}]])
export const Cigarette = ssrIcon('cigarette', [["path",{"d":"M17 12H3a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1h14","key":"1mb5g1"}],["path",{"d":"M18 8c0-2.5-2-2.5-2-5","key":"1il607"}],["path",{"d":"M21 16a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1","key":"1yl5r7"}],["path",{"d":"M22 8c0-2.5-2-2.5-2-5","key":"1gah44"}],["path",{"d":"M7 12v4","key":"jqww69"}]])
export const CigaretteOff = ssrIcon('cigarette-off', [["path",{"d":"M12 12H3a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1h13","key":"1gdiyg"}],["path",{"d":"M18 8c0-2.5-2-2.5-2-5","key":"1il607"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M21 12a1 1 0 0 1 1 1v2a1 1 0 0 1-.5.866","key":"166zjj"}],["path",{"d":"M22 8c0-2.5-2-2.5-2-5","key":"1gah44"}],["path",{"d":"M7 12v4","key":"jqww69"}]])
export const Circle = ssrIcon('circle', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}]])
export const CircleDashed = ssrIcon('circle-dashed', [["path",{"d":"M10.1 2.182a10 10 0 0 1 3.8 0","key":"5ilxe3"}],["path",{"d":"M13.9 21.818a10 10 0 0 1-3.8 0","key":"11zvb9"}],["path",{"d":"M17.609 3.721a10 10 0 0 1 2.69 2.7","key":"1iw5b2"}],["path",{"d":"M2.182 13.9a10 10 0 0 1 0-3.8","key":"c0bmvh"}],["path",{"d":"M20.279 17.609a10 10 0 0 1-2.7 2.69","key":"1ruxm7"}],["path",{"d":"M21.818 10.1a10 10 0 0 1 0 3.8","key":"qkgqxc"}],["path",{"d":"M3.721 6.391a10 10 0 0 1 2.7-2.69","key":"1mcia2"}],["path",{"d":"M6.391 20.279a10 10 0 0 1-2.69-2.7","key":"1fvljs"}]])
export const CircleDivide = ssrIcon('circle-divide', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["line",{"x1":"8","x2":"16","y1":"12","y2":"12","key":"1jonct"}],["line",{"x1":"12","x2":"12","y1":"16","y2":"16","key":"aqc6ln"}],["line",{"x1":"12","x2":"12","y1":"8","y2":"8","key":"1mkcni"}]])
export const CircleDollarSign = ssrIcon('circle-dollar-sign', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8","key":"1h4pet"}],["path",{"d":"M12 18V6","key":"zqpxq5"}]])
export const CircleDot = ssrIcon('circle-dot', [["circle",{"cx":"12","cy":"12","r":"1","key":"41hilf"}],["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}]])
export const CircleDotDashed = ssrIcon('circle-dot-dashed', [["path",{"d":"M10.1 2.18a9.93 9.93 0 0 1 3.8 0","key":"1qdqn0"}],["path",{"d":"M17.6 3.71a9.95 9.95 0 0 1 2.69 2.7","key":"1bq7p6"}],["path",{"d":"M21.82 10.1a9.93 9.93 0 0 1 0 3.8","key":"1rlaqf"}],["path",{"d":"M20.29 17.6a9.95 9.95 0 0 1-2.7 2.69","key":"1xk03u"}],["path",{"d":"M13.9 21.82a9.94 9.94 0 0 1-3.8 0","key":"l7re25"}],["path",{"d":"M6.4 20.29a9.95 9.95 0 0 1-2.69-2.7","key":"1v18p6"}],["path",{"d":"M2.18 13.9a9.93 9.93 0 0 1 0-3.8","key":"xdo6bj"}],["path",{"d":"M3.71 6.4a9.95 9.95 0 0 1 2.7-2.69","key":"1jjmaz"}],["circle",{"cx":"12","cy":"12","r":"1","key":"41hilf"}]])
export const CircleEllipsis = ssrIcon('circle-ellipsis', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M17 12h.01","key":"1m0b6t"}],["path",{"d":"M12 12h.01","key":"1mp3jc"}],["path",{"d":"M7 12h.01","key":"eqddd0"}]])
export const CircleEqual = ssrIcon('circle-equal', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M7 10h10","key":"1101jm"}],["path",{"d":"M7 14h10","key":"1mhdw3"}]])
export const CircleEuro = ssrIcon('circle-euro', [["path",{"d":"M15 9.4a4 4 0 1 0 0 5.2","key":"1makmb"}],["path",{"d":"M7 12h5","key":"gblrwe"}],["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}]])
export const CircleFadingArrowUp = ssrIcon('circle-fading-arrow-up', [["path",{"d":"M12 2a10 10 0 0 1 7.38 16.75","key":"175t95"}],["path",{"d":"m16 12-4-4-4 4","key":"177agl"}],["path",{"d":"M12 16V8","key":"1sbj14"}],["path",{"d":"M2.5 8.875a10 10 0 0 0-.5 3","key":"1vce0s"}],["path",{"d":"M2.83 16a10 10 0 0 0 2.43 3.4","key":"o3fkw4"}],["path",{"d":"M4.636 5.235a10 10 0 0 1 .891-.857","key":"1szpfk"}],["path",{"d":"M8.644 21.42a10 10 0 0 0 7.631-.38","key":"9yhvd4"}]])
export const CircleFadingPlus = ssrIcon('circle-fading-plus', [["path",{"d":"M12 2a10 10 0 0 1 7.38 16.75","key":"175t95"}],["path",{"d":"M12 8v8","key":"napkw2"}],["path",{"d":"M16 12H8","key":"1fr5h0"}],["path",{"d":"M2.5 8.875a10 10 0 0 0-.5 3","key":"1vce0s"}],["path",{"d":"M2.83 16a10 10 0 0 0 2.43 3.4","key":"o3fkw4"}],["path",{"d":"M4.636 5.235a10 10 0 0 1 .891-.857","key":"1szpfk"}],["path",{"d":"M8.644 21.42a10 10 0 0 0 7.631-.38","key":"9yhvd4"}]])
export const CircleGauge = ssrIcon('circle-gauge', [["path",{"d":"M15.6 2.7a10 10 0 1 0 5.7 5.7","key":"1e0p6d"}],["circle",{"cx":"12","cy":"12","r":"2","key":"1c9p78"}],["path",{"d":"M13.4 10.6 19 5","key":"1kr7tw"}]])
export const CircleQuestionMark = ssrIcon('circle-question-mark', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3","key":"1u773s"}],["path",{"d":"M12 17h.01","key":"p32p05"}]])
export const CircleMinus = ssrIcon('circle-minus', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M8 12h8","key":"1wcyev"}]])
export const CircleOff = ssrIcon('circle-off', [["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M8.35 2.69A10 10 0 0 1 21.3 15.65","key":"1pfsoa"}],["path",{"d":"M19.08 19.08A10 10 0 1 1 4.92 4.92","key":"1ablyi"}]])
export const CircleParking = ssrIcon('circle-parking', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M9 17V7h4a3 3 0 0 1 0 6H9","key":"1dfk2c"}]])
export const CircleParkingOff = ssrIcon('circle-parking-off', [["path",{"d":"M12.656 7H13a3 3 0 0 1 2.984 3.307","key":"1sjx87"}],["path",{"d":"M13 13H9","key":"e2beee"}],["path",{"d":"M19.071 19.071A1 1 0 0 1 4.93 4.93","key":"1kb595"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M8.357 2.687a10 10 0 0 1 12.956 12.956","key":"5bsfdx"}],["path",{"d":"M9 17V9","key":"ojradj"}]])
export const CirclePause = ssrIcon('circle-pause', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["line",{"x1":"10","x2":"10","y1":"15","y2":"9","key":"c1nkhi"}],["line",{"x1":"14","x2":"14","y1":"15","y2":"9","key":"h65svq"}]])
export const CirclePercent = ssrIcon('circle-percent', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"m15 9-6 6","key":"1uzhvr"}],["path",{"d":"M9 9h.01","key":"1q5me6"}],["path",{"d":"M15 15h.01","key":"lqbp3k"}]])
export const CirclePile = ssrIcon('circle-pile', [["circle",{"cx":"12","cy":"19","r":"2","key":"13j0tp"}],["circle",{"cx":"12","cy":"5","r":"2","key":"f1ur92"}],["circle",{"cx":"16","cy":"12","r":"2","key":"4ma0v8"}],["circle",{"cx":"20","cy":"19","r":"2","key":"1obnsp"}],["circle",{"cx":"4","cy":"19","r":"2","key":"p3m9r0"}],["circle",{"cx":"8","cy":"12","r":"2","key":"1nvbw3"}]])
export const CirclePlay = ssrIcon('circle-play', [["path",{"d":"M9 9.003a1 1 0 0 1 1.517-.859l4.997 2.997a1 1 0 0 1 0 1.718l-4.997 2.997A1 1 0 0 1 9 14.996z","key":"kmsa83"}],["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}]])
export const CirclePlus = ssrIcon('circle-plus', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M8 12h8","key":"1wcyev"}],["path",{"d":"M12 8v8","key":"napkw2"}]])
export const CirclePoundSterling = ssrIcon('circle-pound-sterling', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M10 16V9.5a1 1 0 0 1 5 0","key":"1i1are"}],["path",{"d":"M8 12h4","key":"qz6y1c"}],["path",{"d":"M8 16h7","key":"sbedsn"}]])
export const CirclePower = ssrIcon('circle-power', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 7v4","key":"xawao1"}],["path",{"d":"M7.998 9.003a5 5 0 1 0 8-.005","key":"1pek45"}]])
export const CircleSlash = ssrIcon('circle-slash', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["line",{"x1":"9","x2":"15","y1":"15","y2":"9","key":"1dfufj"}]])
export const CircleSlash2 = ssrIcon('circle-slash-2', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M22 2 2 22","key":"y4kqgn"}]])
export const CircleSmall = ssrIcon('circle-small', [["circle",{"cx":"12","cy":"12","r":"6","key":"1vlfrh"}]])
export const CircleStar = ssrIcon('circle-star', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M11.051 7.616a1 1 0 0 1 1.909.024l.737 1.452a1 1 0 0 0 .737.535l1.634.256a1 1 0 0 1 .588 1.806l-1.172 1.168a1 1 0 0 0-.282.866l.259 1.613a1 1 0 0 1-1.541 1.134l-1.465-.75a1 1 0 0 0-.912 0l-1.465.75a1 1 0 0 1-1.539-1.133l.258-1.613a1 1 0 0 0-.282-.867l-1.156-1.152a1 1 0 0 1 .572-1.822l1.633-.256a1 1 0 0 0 .737-.535z","key":"285bvi"}]])
export const CircleStop = ssrIcon('circle-stop', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["rect",{"x":"9","y":"9","width":"6","height":"6","rx":"1","key":"1ssd4o"}]])
export const CircleUser = ssrIcon('circle-user', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["circle",{"cx":"12","cy":"10","r":"3","key":"ilqhr7"}],["path",{"d":"M7 20.662V19a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v1.662","key":"154egf"}]])
export const CircleUserRound = ssrIcon('circle-user-round', [["path",{"d":"M17.925 20.056a6 6 0 0 0-11.851.001","key":"z69sun"}],["circle",{"cx":"12","cy":"11","r":"4","key":"1gt34v"}],["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}]])
export const CircleX = ssrIcon('circle-x', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"m15 9-6 6","key":"1uzhvr"}],["path",{"d":"m9 9 6 6","key":"z0biqf"}]])
export const CircuitBoard = ssrIcon('circuit-board', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M11 9h4a2 2 0 0 0 2-2V3","key":"1ve2rv"}],["circle",{"cx":"9","cy":"9","r":"2","key":"af1f0g"}],["path",{"d":"M7 21v-4a2 2 0 0 1 2-2h4","key":"1fwkro"}],["circle",{"cx":"15","cy":"15","r":"2","key":"3i40o0"}]])
export const Citrus = ssrIcon('citrus', [["path",{"d":"M21.66 17.67a1.08 1.08 0 0 1-.04 1.6A12 12 0 0 1 4.73 2.38a1.1 1.1 0 0 1 1.61-.04z","key":"4ite01"}],["path",{"d":"M19.65 15.66A8 8 0 0 1 8.35 4.34","key":"1gxipu"}],["path",{"d":"m14 10-5.5 5.5","key":"92pfem"}],["path",{"d":"M14 17.85V10H6.15","key":"xqmtsk"}]])
export const Clapperboard = ssrIcon('clapperboard', [["path",{"d":"m12.296 3.464 3.02 3.956","key":"qash78"}],["path",{"d":"M20.2 6 3 11l-.9-2.4c-.3-1.1.3-2.2 1.3-2.5l13.5-4c1.1-.3 2.2.3 2.5 1.3z","key":"1h7j8b"}],["path",{"d":"M3 11h18v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z","key":"4lm6w1"}],["path",{"d":"m6.18 5.276 3.1 3.899","key":"zjj9t3"}]])
export const Clipboard = ssrIcon('clipboard', [["rect",{"width":"8","height":"4","x":"8","y":"2","rx":"1","ry":"1","key":"tgr4d6"}],["path",{"d":"M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2","key":"116196"}]])
export const ClipboardCheck = ssrIcon('clipboard-check', [["rect",{"width":"8","height":"4","x":"8","y":"2","rx":"1","ry":"1","key":"tgr4d6"}],["path",{"d":"M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2","key":"116196"}],["path",{"d":"m9 14 2 2 4-4","key":"df797q"}]])
export const ClipboardClock = ssrIcon('clipboard-clock', [["path",{"d":"M16 14v2.2l1.6 1","key":"fo4ql5"}],["path",{"d":"M16 4h2a2 2 0 0 1 2 2v.832","key":"1ujtp2"}],["path",{"d":"M8 4H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h2","key":"qvpao1"}],["circle",{"cx":"16","cy":"16","r":"6","key":"qoo3c4"}],["rect",{"x":"8","y":"2","width":"8","height":"4","rx":"1","key":"ublpy"}]])
export const ClipboardCopy = ssrIcon('clipboard-copy', [["rect",{"width":"8","height":"4","x":"8","y":"2","rx":"1","ry":"1","key":"tgr4d6"}],["path",{"d":"M8 4H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2","key":"4jdomd"}],["path",{"d":"M16 4h2a2 2 0 0 1 2 2v4","key":"3hqy98"}],["path",{"d":"M21 14H11","key":"1bme5i"}],["path",{"d":"m15 10-4 4 4 4","key":"5dvupr"}]])
export const ClipboardPen = ssrIcon('clipboard-pen', [["path",{"d":"M16 4h2a2 2 0 0 1 2 2v2","key":"j91f56"}],["path",{"d":"M21.34 15.664a1 1 0 1 0-3.004-3.004l-5.01 5.012a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z","key":"16fuwn"}],["path",{"d":"M8 22H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2","key":"120tdm"}],["rect",{"x":"8","y":"2","width":"8","height":"4","rx":"1","key":"ublpy"}]])
export const ClipboardList = ssrIcon('clipboard-list', [["rect",{"width":"8","height":"4","x":"8","y":"2","rx":"1","ry":"1","key":"tgr4d6"}],["path",{"d":"M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2","key":"116196"}],["path",{"d":"M12 11h4","key":"1jrz19"}],["path",{"d":"M12 16h4","key":"n85exb"}],["path",{"d":"M8 11h.01","key":"1dfujw"}],["path",{"d":"M8 16h.01","key":"18s6g9"}]])
export const ClipboardMinus = ssrIcon('clipboard-minus', [["rect",{"width":"8","height":"4","x":"8","y":"2","rx":"1","ry":"1","key":"tgr4d6"}],["path",{"d":"M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2","key":"116196"}],["path",{"d":"M9 14h6","key":"159ibu"}]])
export const ClipboardPaste = ssrIcon('clipboard-paste', [["path",{"d":"M11 14h10","key":"1w8e9d"}],["path",{"d":"M16 4h2a2 2 0 0 1 2 2v1.344","key":"1e62lh"}],["path",{"d":"m17 18 4-4-4-4","key":"z2g111"}],["path",{"d":"M8 4H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 1.793-1.113","key":"bjbb7m"}],["rect",{"x":"8","y":"2","width":"8","height":"4","rx":"1","key":"ublpy"}]])
export const ClipboardPenLine = ssrIcon('clipboard-pen-line', [["rect",{"width":"8","height":"4","x":"8","y":"2","rx":"1","key":"1oijnt"}],["path",{"d":"M8 4H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-.5","key":"1but9f"}],["path",{"d":"M16 4h2a2 2 0 0 1 1.73 1","key":"1p8n7l"}],["path",{"d":"M8 18h1","key":"13wk12"}],["path",{"d":"M21.378 12.626a1 1 0 0 0-3.004-3.004l-4.01 4.012a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z","key":"2t3380"}]])
export const ClipboardPlus = ssrIcon('clipboard-plus', [["rect",{"width":"8","height":"4","x":"8","y":"2","rx":"1","ry":"1","key":"tgr4d6"}],["path",{"d":"M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2","key":"116196"}],["path",{"d":"M9 14h6","key":"159ibu"}],["path",{"d":"M12 17v-6","key":"1y8rbf"}]])
export const ClipboardType = ssrIcon('clipboard-type', [["rect",{"width":"8","height":"4","x":"8","y":"2","rx":"1","ry":"1","key":"tgr4d6"}],["path",{"d":"M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2","key":"116196"}],["path",{"d":"M9 12v-1h6v1","key":"iehl6m"}],["path",{"d":"M11 17h2","key":"12w5me"}],["path",{"d":"M12 11v6","key":"1bwqyc"}]])
export const ClipboardX = ssrIcon('clipboard-x', [["rect",{"width":"8","height":"4","x":"8","y":"2","rx":"1","ry":"1","key":"tgr4d6"}],["path",{"d":"M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2","key":"116196"}],["path",{"d":"m14.5 11.5-5 5","key":"1eaq8h"}],["path",{"d":"m9.5 11.5 5 5","key":"1exjew"}]])
export const Clock = ssrIcon('clock', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 6v6l4 2","key":"mmk7yg"}]])
export const Clock1 = ssrIcon('clock-1', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 6v6l2-4","key":"miptyd"}]])
export const Clock10 = ssrIcon('clock-10', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 6v6l-4-2","key":"cedpoo"}]])
export const Clock11 = ssrIcon('clock-11', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 6v6l-2-4","key":"ns39ag"}]])
export const Clock12 = ssrIcon('clock-12', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 6v6","key":"1ipuwl"}]])
export const Clock2 = ssrIcon('clock-2', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 6v6l4-2","key":"1r2kuh"}]])
export const Clock3 = ssrIcon('clock-3', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 6v6h4","key":"135r8i"}]])
export const Clock4 = ssrIcon('clock-4', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 6v6l4 2","key":"mmk7yg"}]])
export const Clock5 = ssrIcon('clock-5', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 6v6l2 4","key":"1287s9"}]])
export const Clock6 = ssrIcon('clock-6', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 6v10","key":"wf7rdh"}]])
export const Clock7 = ssrIcon('clock-7', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 6v6l-2 4","key":"1095bu"}]])
export const Clock8 = ssrIcon('clock-8', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 6v6l-4 2","key":"imc3wl"}]])
export const Clock9 = ssrIcon('clock-9', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 6v6H8","key":"u39vzm"}]])
export const ClockAlert = ssrIcon('clock-alert', [["path",{"d":"M12 6v6l4 2","key":"mmk7yg"}],["path",{"d":"M20 12v5","key":"12wsvk"}],["path",{"d":"M20 21h.01","key":"1p6o6n"}],["path",{"d":"M21.25 8.2A10 10 0 1 0 16 21.16","key":"17fp9f"}]])
export const ClockArrowDown = ssrIcon('clock-arrow-down', [["path",{"d":"M12 6v6l2 1","key":"19cm8n"}],["path",{"d":"M12.337 21.994a10 10 0 1 1 9.588-8.767","key":"28moa"}],["path",{"d":"m14 18 4 4 4-4","key":"1waygx"}],["path",{"d":"M18 14v8","key":"irew45"}]])
export const ClockArrowLeft = ssrIcon('clock-arrow-left', [["path",{"d":"M12 6v6l1.5.8","key":"uc7jki"}],["path",{"d":"M12.338 21.994a10 10 0 1 1 9.587-8.767","key":"1lz5pu"}],["path",{"d":"M14 18h8","key":"1le3fr"}],["path",{"d":"m18 22-4-4 4-4","key":"dh5o1f"}]])
export const ClockArrowRight = ssrIcon('clock-arrow-right', [["path",{"d":"M12 6v6l2 1","key":"19cm8n"}],["path",{"d":"M13.5 21.885A10 10 0 1 1 22 12","key":"xgp8as"}],["path",{"d":"M14 18h8","key":"1le3fr"}],["path",{"d":"m18 22 4-4-4-4","key":"mordo3"}]])
export const ClockArrowUp = ssrIcon('clock-arrow-up', [["path",{"d":"M12 6v6l1.56.78","key":"14ed3g"}],["path",{"d":"M13.227 21.925a10 10 0 1 1 8.767-9.588","key":"jwkls1"}],["path",{"d":"m14 18 4-4 4 4","key":"ftkppy"}],["path",{"d":"M18 22v-8","key":"su0gjh"}]])
export const ClockCheck = ssrIcon('clock-check', [["path",{"d":"M21.95 13a10 10 0 1 0-8.685 8.92","key":"1ujumx"}],["path",{"d":"M12 6v6l4 2","key":"mmk7yg"}],["path",{"d":"m16 19 2 2 4-4","key":"1b14m6"}]])
export const ClockFading = ssrIcon('clock-fading', [["path",{"d":"M12 2a10 10 0 0 1 7.38 16.75","key":"175t95"}],["path",{"d":"M12 6v6l4 2","key":"mmk7yg"}],["path",{"d":"M2.5 8.875a10 10 0 0 0-.5 3","key":"1vce0s"}],["path",{"d":"M2.83 16a10 10 0 0 0 2.43 3.4","key":"o3fkw4"}],["path",{"d":"M4.636 5.235a10 10 0 0 1 .891-.857","key":"1szpfk"}],["path",{"d":"M8.644 21.42a10 10 0 0 0 7.631-.38","key":"9yhvd4"}]])
export const ClockPlus = ssrIcon('clock-plus', [["path",{"d":"M12 6v6l3.644 1.822","key":"1jmett"}],["path",{"d":"M16 19h6","key":"xwg31i"}],["path",{"d":"M19 16v6","key":"tddt3s"}],["path",{"d":"M21.92 13.267a10 10 0 1 0-8.653 8.653","key":"1u0osk"}]])
export const ClosedCaption = ssrIcon('closed-caption', [["path",{"d":"M10 9.17a3 3 0 1 0 0 5.66","key":"h9wayk"}],["path",{"d":"M17 9.17a3 3 0 1 0 0 5.66","key":"1v6zke"}],["rect",{"x":"2","y":"5","width":"20","height":"14","rx":"2","key":"qneu4z"}]])
export const Cloud = ssrIcon('cloud', [["path",{"d":"M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z","key":"p7xjir"}]])
export const CloudAlert = ssrIcon('cloud-alert', [["path",{"d":"M12 12v4","key":"tww15h"}],["path",{"d":"M12 20h.01","key":"zekei9"}],["path",{"d":"M8.128 16.949A7 7 0 1 1 15.71 8h1.79a1 1 0 0 1 0 9h-1.642","key":"1namsd"}]])
export const CloudBackup = ssrIcon('cloud-backup', [["path",{"d":"M21 15.251A4.5 4.5 0 0 0 17.5 8h-1.79A7 7 0 1 0 3 13.607","key":"xpoh9y"}],["path",{"d":"M7 11v4h4","key":"q9yh32"}],["path",{"d":"M8 19a5 5 0 0 0 9-3 4.5 4.5 0 0 0-4.5-4.5 4.82 4.82 0 0 0-3.41 1.41L7 15","key":"1xm8iu"}]])
export const CloudCheck = ssrIcon('cloud-check', [["path",{"d":"m17 15-5.5 5.5L9 18","key":"15q87x"}],["path",{"d":"M5.516 16.07A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 3.501 7.327","key":"1xtj56"}]])
export const CloudCog = ssrIcon('cloud-cog', [["path",{"d":"m10.852 19.772-.383.924","key":"r7sl7d"}],["path",{"d":"m13.148 14.228.383-.923","key":"1d5zpm"}],["path",{"d":"M13.148 19.772a3 3 0 1 0-2.296-5.544l-.383-.923","key":"1ydik7"}],["path",{"d":"m13.53 20.696-.382-.924a3 3 0 1 1-2.296-5.544","key":"1m1vsf"}],["path",{"d":"m14.772 15.852.923-.383","key":"660p6e"}],["path",{"d":"m14.772 18.148.923.383","key":"hrcpis"}],["path",{"d":"M4.2 15.1a7 7 0 1 1 9.93-9.858A7 7 0 0 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.2","key":"j2q98n"}],["path",{"d":"m9.228 15.852-.923-.383","key":"1p9ong"}],["path",{"d":"m9.228 18.148-.923.383","key":"6558rz"}]])
export const CloudDownload = ssrIcon('cloud-download', [["path",{"d":"M12 13v8l-4-4","key":"1f5nwf"}],["path",{"d":"m12 21 4-4","key":"1lfcce"}],["path",{"d":"M4.393 15.269A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.436 8.284","key":"ui1hmy"}]])
export const CloudDrizzle = ssrIcon('cloud-drizzle', [["path",{"d":"M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242","key":"1pljnt"}],["path",{"d":"M8 19v1","key":"1dk2by"}],["path",{"d":"M8 14v1","key":"84yxot"}],["path",{"d":"M16 19v1","key":"v220m7"}],["path",{"d":"M16 14v1","key":"g12gj6"}],["path",{"d":"M12 21v1","key":"q8vafk"}],["path",{"d":"M12 16v1","key":"1mx6rx"}]])
export const CloudFog = ssrIcon('cloud-fog', [["path",{"d":"M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242","key":"1pljnt"}],["path",{"d":"M16 17H7","key":"pygtm1"}],["path",{"d":"M17 21H9","key":"1u2q02"}]])
export const CloudHail = ssrIcon('cloud-hail', [["path",{"d":"M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242","key":"1pljnt"}],["path",{"d":"M16 14v2","key":"a1is7l"}],["path",{"d":"M8 14v2","key":"1e9m6t"}],["path",{"d":"M16 20h.01","key":"xwek51"}],["path",{"d":"M8 20h.01","key":"1vjney"}],["path",{"d":"M12 16v2","key":"z66u1j"}],["path",{"d":"M12 22h.01","key":"1urd7a"}]])
export const CloudLightning = ssrIcon('cloud-lightning', [["path",{"d":"M6 16.326A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 .5 8.973","key":"1cez44"}],["path",{"d":"m13 12-3 5h4l-3 5","key":"1t22er"}]])
export const CloudMoon = ssrIcon('cloud-moon', [["path",{"d":"M13 16a3 3 0 0 1 0 6H7a5 5 0 1 1 4.9-6z","key":"ie2ih4"}],["path",{"d":"M18.376 14.512a6 6 0 0 0 3.461-4.127c.148-.625-.659-.97-1.248-.714a4 4 0 0 1-5.259-5.26c.255-.589-.09-1.395-.716-1.248a6 6 0 0 0-4.594 5.36","key":"zwnc1e"}]])
export const CloudMoonRain = ssrIcon('cloud-moon-rain', [["path",{"d":"M11 20v2","key":"174qtz"}],["path",{"d":"M18.376 14.512a6 6 0 0 0 3.461-4.127c.148-.625-.659-.97-1.248-.714a4 4 0 0 1-5.259-5.26c.255-.589-.09-1.395-.716-1.248a6 6 0 0 0-4.594 5.36","key":"zwnc1e"}],["path",{"d":"M3 20a5 5 0 1 1 8.9-4H13a3 3 0 0 1 2 5.24","key":"1qmrp3"}],["path",{"d":"M7 19v2","key":"12npes"}]])
export const CloudOff = ssrIcon('cloud-off', [["path",{"d":"M10.94 5.274A7 7 0 0 1 15.71 10h1.79a4.5 4.5 0 0 1 4.222 6.057","key":"1uxyv8"}],["path",{"d":"M18.796 18.81A4.5 4.5 0 0 1 17.5 19H9A7 7 0 0 1 5.79 5.78","key":"99tcn7"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}]])
export const CloudRain = ssrIcon('cloud-rain', [["path",{"d":"M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242","key":"1pljnt"}],["path",{"d":"M16 14v6","key":"1j4efv"}],["path",{"d":"M8 14v6","key":"17c4r9"}],["path",{"d":"M12 16v6","key":"c8a4gj"}]])
export const CloudRainWind = ssrIcon('cloud-rain-wind', [["path",{"d":"M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242","key":"1pljnt"}],["path",{"d":"m9.2 22 3-7","key":"sb5f6j"}],["path",{"d":"m9 13-3 7","key":"500co5"}],["path",{"d":"m17 13-3 7","key":"8t2fiy"}]])
export const CloudSnow = ssrIcon('cloud-snow', [["path",{"d":"M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242","key":"1pljnt"}],["path",{"d":"M8 15h.01","key":"a7atzg"}],["path",{"d":"M8 19h.01","key":"puxtts"}],["path",{"d":"M12 17h.01","key":"p32p05"}],["path",{"d":"M12 21h.01","key":"h35vbk"}],["path",{"d":"M16 15h.01","key":"rnfrdf"}],["path",{"d":"M16 19h.01","key":"1vcnzz"}]])
export const CloudSun = ssrIcon('cloud-sun', [["path",{"d":"M12 2v2","key":"tus03m"}],["path",{"d":"m4.93 4.93 1.41 1.41","key":"149t6j"}],["path",{"d":"M20 12h2","key":"1q8mjw"}],["path",{"d":"m19.07 4.93-1.41 1.41","key":"1shlcs"}],["path",{"d":"M15.947 12.65a4 4 0 0 0-5.925-4.128","key":"dpwdj0"}],["path",{"d":"M13 22H7a5 5 0 1 1 4.9-6H13a3 3 0 0 1 0 6Z","key":"s09mg5"}]])
export const CloudSunRain = ssrIcon('cloud-sun-rain', [["path",{"d":"M12 2v2","key":"tus03m"}],["path",{"d":"m4.93 4.93 1.41 1.41","key":"149t6j"}],["path",{"d":"M20 12h2","key":"1q8mjw"}],["path",{"d":"m19.07 4.93-1.41 1.41","key":"1shlcs"}],["path",{"d":"M15.947 12.65a4 4 0 0 0-5.925-4.128","key":"dpwdj0"}],["path",{"d":"M3 20a5 5 0 1 1 8.9-4H13a3 3 0 0 1 2 5.24","key":"1qmrp3"}],["path",{"d":"M11 20v2","key":"174qtz"}],["path",{"d":"M7 19v2","key":"12npes"}]])
export const CloudSync = ssrIcon('cloud-sync', [["path",{"d":"m17 18-1.535 1.605a5 5 0 0 1-8-1.5","key":"adpv5j"}],["path",{"d":"M17 22v-4h-4","key":"ex1ofj"}],["path",{"d":"M20.996 15.251A4.5 4.5 0 0 0 17.495 8h-1.79a7 7 0 1 0-12.709 5.607","key":"ziqt14"}],["path",{"d":"M7 10v4h4","key":"1j6gx1"}],["path",{"d":"m7 14 1.535-1.605a5 5 0 0 1 8 1.5","key":"19q5h7"}]])
export const CloudUpload = ssrIcon('cloud-upload', [["path",{"d":"M12 13v8","key":"1l5pq0"}],["path",{"d":"M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242","key":"1pljnt"}],["path",{"d":"m8 17 4-4 4 4","key":"1quai1"}]])
export const Cloudy = ssrIcon('cloudy', [["path",{"d":"M17.5 12a1 1 0 1 1 0 9H9.006a7 7 0 1 1 6.702-9z","key":"44yre2"}],["path",{"d":"M21.832 9A3 3 0 0 0 19 7h-2.207a5.5 5.5 0 0 0-10.72.61","key":"leugyv"}]])
export const Clover = ssrIcon('clover', [["path",{"d":"M16.17 7.83 2 22","key":"t58vo8"}],["path",{"d":"M4.02 12a2.827 2.827 0 1 1 3.81-4.17A2.827 2.827 0 1 1 12 4.02a2.827 2.827 0 1 1 4.17 3.81A2.827 2.827 0 1 1 19.98 12a2.827 2.827 0 1 1-3.81 4.17A2.827 2.827 0 1 1 12 19.98a2.827 2.827 0 1 1-4.17-3.81A1 1 0 1 1 4 12","key":"17k36q"}],["path",{"d":"m7.83 7.83 8.34 8.34","key":"1d7sxk"}]])
export const Club = ssrIcon('club', [["path",{"d":"M17.28 9.05a5.5 5.5 0 1 0-10.56 0A5.5 5.5 0 1 0 12 17.66a5.5 5.5 0 1 0 5.28-8.6Z","key":"27yuqz"}],["path",{"d":"M12 17.66L12 22","key":"ogfahf"}]])
export const Code = ssrIcon('code', [["path",{"d":"m16 18 6-6-6-6","key":"eg8j8"}],["path",{"d":"m8 6-6 6 6 6","key":"ppft3o"}]])
export const CodeXml = ssrIcon('code-xml', [["path",{"d":"m18 16 4-4-4-4","key":"1inbqp"}],["path",{"d":"m6 8-4 4 4 4","key":"15zrgr"}],["path",{"d":"m14.5 4-5 16","key":"e7oirm"}]])
export const SquareCode = ssrIcon('square-code', [["path",{"d":"m10 9-3 3 3 3","key":"1oro0q"}],["path",{"d":"m14 15 3-3-3-3","key":"bz13h7"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const Coffee = ssrIcon('coffee', [["path",{"d":"M10 2v2","key":"7u0qdc"}],["path",{"d":"M14 2v2","key":"6buw04"}],["path",{"d":"M16 8a1 1 0 0 1 1 1v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1h14a4 4 0 1 1 0 8h-1","key":"pwadti"}],["path",{"d":"M6 2v2","key":"colzsn"}]])
export const Cog = ssrIcon('cog', [["path",{"d":"M11 10.27 7 3.34","key":"16pf9h"}],["path",{"d":"m11 13.73-4 6.93","key":"794ttg"}],["path",{"d":"M12 22v-2","key":"1osdcq"}],["path",{"d":"M12 2v2","key":"tus03m"}],["path",{"d":"M14 12h8","key":"4f43i9"}],["path",{"d":"m17 20.66-1-1.73","key":"eq3orb"}],["path",{"d":"m17 3.34-1 1.73","key":"2wel8s"}],["path",{"d":"M2 12h2","key":"1t8f8n"}],["path",{"d":"m20.66 17-1.73-1","key":"sg0v6f"}],["path",{"d":"m20.66 7-1.73 1","key":"1ow05n"}],["path",{"d":"m3.34 17 1.73-1","key":"nuk764"}],["path",{"d":"m3.34 7 1.73 1","key":"1ulond"}],["circle",{"cx":"12","cy":"12","r":"2","key":"1c9p78"}],["circle",{"cx":"12","cy":"12","r":"8","key":"46899m"}]])
export const Coins = ssrIcon('coins', [["path",{"d":"M13.744 17.736a6 6 0 1 1-7.48-7.48","key":"bq4yh3"}],["path",{"d":"M15 6h1v4","key":"11y1tn"}],["path",{"d":"m6.134 14.768.866-.5 2 3.464","key":"17snzx"}],["circle",{"cx":"16","cy":"8","r":"6","key":"14bfc9"}]])
export const Columns2 = ssrIcon('columns-2', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M12 3v18","key":"108xh3"}]])
export const Columns3 = ssrIcon('columns-3', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M9 3v18","key":"fh3hqa"}],["path",{"d":"M15 3v18","key":"14nvp0"}]])
export const Columns3Cog = ssrIcon('columns-3-cog', [["path",{"d":"M10.6 21H5a2 2 0 01-2-2V5a2 2 0 012-2h14a2 2 0 012 2v5.6","key":"19s2bv"}],["path",{"d":"m14.305 19.53.923-.382","key":"3m78fa"}],["path",{"d":"M15 3v7.6","key":"mv9izd"}],["path",{"d":"m15.229 16.852-.924-.383","key":"qpfz85"}],["path",{"d":"m16.852 15.228-.383-.923","key":"5xggr7"}],["path",{"d":"m16.852 20.772-.383.924","key":"dpfhf9"}],["path",{"d":"m19.148 15.228.383-.923","key":"1reyyz"}],["path",{"d":"m19.53 21.696-.382-.924","key":"1goivc"}],["path",{"d":"m20.773 16.852.922-.383","key":"59dfo2"}],["path",{"d":"m20.773 19.148.922.383","key":"1lk755"}],["path",{"d":"M9 3v18","key":"fh3hqa"}],["circle",{"cx":"18","cy":"18","r":"3","key":"1xkwt0"}]])
export const Columns4 = ssrIcon('columns-4', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M7.5 3v18","key":"w0wo6v"}],["path",{"d":"M12 3v18","key":"108xh3"}],["path",{"d":"M16.5 3v18","key":"10tjh1"}]])
export const Combine = ssrIcon('combine', [["path",{"d":"M14 3a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1","key":"1l7d7l"}],["path",{"d":"M19 3a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1","key":"9955pe"}],["path",{"d":"m7 15 3 3","key":"4hkfgk"}],["path",{"d":"m7 21 3-3H5a2 2 0 0 1-2-2v-2","key":"1xljwe"}],["rect",{"x":"14","y":"14","width":"7","height":"7","rx":"1","key":"1cdgtw"}],["rect",{"x":"3","y":"3","width":"7","height":"7","rx":"1","key":"zi3rio"}]])
export const Command = ssrIcon('command', [["path",{"d":"M15 6v12a3 3 0 1 0 3-3H6a3 3 0 1 0 3 3V6a3 3 0 1 0-3 3h12a3 3 0 1 0-3-3","key":"11bfej"}]])
export const Compass = ssrIcon('compass', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z","key":"9ktpf1"}]])
export const Component = ssrIcon('component', [["path",{"d":"M15.536 11.293a1 1 0 0 0 0 1.414l2.376 2.377a1 1 0 0 0 1.414 0l2.377-2.377a1 1 0 0 0 0-1.414l-2.377-2.377a1 1 0 0 0-1.414 0z","key":"1uwlt4"}],["path",{"d":"M2.297 11.293a1 1 0 0 0 0 1.414l2.377 2.377a1 1 0 0 0 1.414 0l2.377-2.377a1 1 0 0 0 0-1.414L6.088 8.916a1 1 0 0 0-1.414 0z","key":"10291m"}],["path",{"d":"M8.916 17.912a1 1 0 0 0 0 1.415l2.377 2.376a1 1 0 0 0 1.414 0l2.377-2.376a1 1 0 0 0 0-1.415l-2.377-2.376a1 1 0 0 0-1.414 0z","key":"1tqoq1"}],["path",{"d":"M8.916 4.674a1 1 0 0 0 0 1.414l2.377 2.376a1 1 0 0 0 1.414 0l2.377-2.376a1 1 0 0 0 0-1.414l-2.377-2.377a1 1 0 0 0-1.414 0z","key":"1x6lto"}]])
export const Computer = ssrIcon('computer', [["rect",{"width":"14","height":"8","x":"5","y":"2","rx":"2","key":"wc9tft"}],["rect",{"width":"20","height":"8","x":"2","y":"14","rx":"2","key":"w68u3i"}],["path",{"d":"M6 18h2","key":"rwmk9e"}],["path",{"d":"M12 18h6","key":"aqd8w3"}]])
export const ConciergeBell = ssrIcon('concierge-bell', [["path",{"d":"M3 20a1 1 0 0 1-1-1v-1a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v1a1 1 0 0 1-1 1Z","key":"1pvr1r"}],["path",{"d":"M20 16a8 8 0 1 0-16 0","key":"1pa543"}],["path",{"d":"M12 4v4","key":"1bq03y"}],["path",{"d":"M10 4h4","key":"1xpv9s"}]])
export const Cone = ssrIcon('cone', [["path",{"d":"m20.9 18.55-8-15.98a1 1 0 0 0-1.8 0l-8 15.98","key":"53pte7"}],["ellipse",{"cx":"12","cy":"19","rx":"9","ry":"3","key":"1ji25f"}]])
export const Construction = ssrIcon('construction', [["rect",{"x":"2","y":"6","width":"20","height":"8","rx":"1","key":"1estib"}],["path",{"d":"M17 14v7","key":"7m2elx"}],["path",{"d":"M7 14v7","key":"1cm7wv"}],["path",{"d":"M17 3v3","key":"1v4jwn"}],["path",{"d":"M7 3v3","key":"7o6guu"}],["path",{"d":"M10 14 2.3 6.3","key":"1023jk"}],["path",{"d":"m14 6 7.7 7.7","key":"1s8pl2"}],["path",{"d":"m8 6 8 8","key":"hl96qh"}]])
export const Contact = ssrIcon('contact', [["path",{"d":"M16 2v2","key":"scm5qe"}],["path",{"d":"M7 21v-2a2 2 0 012-2h6a2 2 0 012 2v2","key":"k82dct"}],["path",{"d":"M8 2v2","key":"pbkmx"}],["circle",{"cx":"12","cy":"10","r":"3","key":"ilqhr7"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const ContactRound = ssrIcon('contact-round', [["path",{"d":"M16 2v2","key":"scm5qe"}],["path",{"d":"M17.915 21a6 6 0 10-12 0","key":"13n4mv"}],["path",{"d":"M8 2v2","key":"pbkmx"}],["circle",{"cx":"12","cy":"11","r":"4","key":"1gt34v"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const Container = ssrIcon('container', [["path",{"d":"M22 7.7c0-.6-.4-1.2-.8-1.5l-6.3-3.9a1.72 1.72 0 0 0-1.7 0l-10.3 6c-.5.2-.9.8-.9 1.4v6.6c0 .5.4 1.2.8 1.5l6.3 3.9a1.72 1.72 0 0 0 1.7 0l10.3-6c.5-.3.9-1 .9-1.5Z","key":"1t2lqe"}],["path",{"d":"M10 21.9V14L2.1 9.1","key":"o7czzq"}],["path",{"d":"m10 14 11.9-6.9","key":"zm5e20"}],["path",{"d":"M14 19.8v-8.1","key":"159ecu"}],["path",{"d":"M18 17.5V9.4","key":"11uown"}]])
export const Contrast = ssrIcon('contrast', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 18a6 6 0 0 0 0-12v12z","key":"j4l70d"}]])
export const Cookie = ssrIcon('cookie', [["path",{"d":"M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5","key":"laymnq"}],["path",{"d":"M8.5 8.5v.01","key":"ue8clq"}],["path",{"d":"M16 15.5v.01","key":"14dtrp"}],["path",{"d":"M12 12v.01","key":"u5ubse"}],["path",{"d":"M11 17v.01","key":"1hyl5a"}],["path",{"d":"M7 14v.01","key":"uct60s"}]])
export const CookingPot = ssrIcon('cooking-pot', [["path",{"d":"M2 12h20","key":"9i4pu4"}],["path",{"d":"M20 12v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8","key":"u0tga0"}],["path",{"d":"m4 8 16-4","key":"16g0ng"}],["path",{"d":"m8.86 6.78-.45-1.81a2 2 0 0 1 1.45-2.43l1.94-.48a2 2 0 0 1 2.43 1.46l.45 1.8","key":"12cejc"}]])
export const Copy = ssrIcon('copy', [["rect",{"width":"14","height":"14","x":"8","y":"8","rx":"2","ry":"2","key":"17jyea"}],["path",{"d":"M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2","key":"zix9uf"}]])
export const CopyCheck = ssrIcon('copy-check', [["path",{"d":"m12 15 2 2 4-4","key":"2c609p"}],["rect",{"width":"14","height":"14","x":"8","y":"8","rx":"2","ry":"2","key":"17jyea"}],["path",{"d":"M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2","key":"zix9uf"}]])
export const CopyMinus = ssrIcon('copy-minus', [["line",{"x1":"12","x2":"18","y1":"15","y2":"15","key":"1nscbv"}],["rect",{"width":"14","height":"14","x":"8","y":"8","rx":"2","ry":"2","key":"17jyea"}],["path",{"d":"M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2","key":"zix9uf"}]])
export const CopyPlus = ssrIcon('copy-plus', [["line",{"x1":"15","x2":"15","y1":"12","y2":"18","key":"1p7wdc"}],["line",{"x1":"12","x2":"18","y1":"15","y2":"15","key":"1nscbv"}],["rect",{"width":"14","height":"14","x":"8","y":"8","rx":"2","ry":"2","key":"17jyea"}],["path",{"d":"M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2","key":"zix9uf"}]])
export const CopySlash = ssrIcon('copy-slash', [["line",{"x1":"12","x2":"18","y1":"18","y2":"12","key":"ebkxgr"}],["rect",{"width":"14","height":"14","x":"8","y":"8","rx":"2","ry":"2","key":"17jyea"}],["path",{"d":"M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2","key":"zix9uf"}]])
export const CopyX = ssrIcon('copy-x', [["path",{"d":"M4 16a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2","key":"1qd6ae"}],["rect",{"x":"8","y":"8","width":"14","height":"14","rx":"2","key":"1an92s"}],["path",{"d":"m12.5 12.5 5 5","key":"1simgt"}],["path",{"d":"m12.5 17.5 5-5","key":"pc59mn"}]])
export const Copyleft = ssrIcon('copyleft', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M9.17 14.83a4 4 0 1 0 0-5.66","key":"1sveal"}]])
export const Copyright = ssrIcon('copyright', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M14.83 14.83a4 4 0 1 1 0-5.66","key":"1i56pz"}]])
export const CornerDownLeft = ssrIcon('corner-down-left', [["path",{"d":"M20 4v7a4 4 0 0 1-4 4H4","key":"6o5b7l"}],["path",{"d":"m9 10-5 5 5 5","key":"1kshq7"}]])
export const CornerDownRight = ssrIcon('corner-down-right', [["path",{"d":"m15 10 5 5-5 5","key":"qqa56n"}],["path",{"d":"M4 4v7a4 4 0 0 0 4 4h12","key":"z08zvw"}]])
export const CornerLeftDown = ssrIcon('corner-left-down', [["path",{"d":"m14 15-5 5-5-5","key":"1eia93"}],["path",{"d":"M20 4h-7a4 4 0 0 0-4 4v12","key":"nbpdq2"}]])
export const CornerLeftUp = ssrIcon('corner-left-up', [["path",{"d":"M14 9 9 4 4 9","key":"1af5af"}],["path",{"d":"M20 20h-7a4 4 0 0 1-4-4V4","key":"1blwi3"}]])
export const CornerRightDown = ssrIcon('corner-right-down', [["path",{"d":"m10 15 5 5 5-5","key":"1hpjnr"}],["path",{"d":"M4 4h7a4 4 0 0 1 4 4v12","key":"wcbgct"}]])
export const CornerRightUp = ssrIcon('corner-right-up', [["path",{"d":"m10 9 5-5 5 5","key":"9ctzwi"}],["path",{"d":"M4 20h7a4 4 0 0 0 4-4V4","key":"1plgdj"}]])
export const CornerUpLeft = ssrIcon('corner-up-left', [["path",{"d":"M20 20v-7a4 4 0 0 0-4-4H4","key":"1nkjon"}],["path",{"d":"M9 14 4 9l5-5","key":"102s5s"}]])
export const CornerUpRight = ssrIcon('corner-up-right', [["path",{"d":"m15 14 5-5-5-5","key":"12vg1m"}],["path",{"d":"M4 20v-7a4 4 0 0 1 4-4h12","key":"1lu4f8"}]])
export const Cpu = ssrIcon('cpu', [["path",{"d":"M12 20v2","key":"1lh1kg"}],["path",{"d":"M12 2v2","key":"tus03m"}],["path",{"d":"M17 20v2","key":"1rnc9c"}],["path",{"d":"M17 2v2","key":"11trls"}],["path",{"d":"M2 12h2","key":"1t8f8n"}],["path",{"d":"M2 17h2","key":"7oei6x"}],["path",{"d":"M2 7h2","key":"asdhe0"}],["path",{"d":"M20 12h2","key":"1q8mjw"}],["path",{"d":"M20 17h2","key":"1fpfkl"}],["path",{"d":"M20 7h2","key":"1o8tra"}],["path",{"d":"M7 20v2","key":"4gnj0m"}],["path",{"d":"M7 2v2","key":"1i4yhu"}],["rect",{"x":"4","y":"4","width":"16","height":"16","rx":"2","key":"1vbyd7"}],["rect",{"x":"8","y":"8","width":"8","height":"8","rx":"1","key":"z9xiuo"}]])
export const CreativeCommons = ssrIcon('creative-commons', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M10 9.3a2.8 2.8 0 0 0-3.5 1 3.1 3.1 0 0 0 0 3.4 2.7 2.7 0 0 0 3.5 1","key":"1ss3eq"}],["path",{"d":"M17 9.3a2.8 2.8 0 0 0-3.5 1 3.1 3.1 0 0 0 0 3.4 2.7 2.7 0 0 0 3.5 1","key":"1od56t"}]])
export const CreditCard = ssrIcon('credit-card', [["rect",{"width":"20","height":"14","x":"2","y":"5","rx":"2","key":"ynyp8z"}],["line",{"x1":"2","x2":"22","y1":"10","y2":"10","key":"1b3vmo"}]])
export const CreditCardCheck = ssrIcon('credit-card-check', [["path",{"d":"M12.5 19H4a2 2 0 01-2-2V7a2 2 0 012-2h16a2 2 0 012 2v4","key":"1pfaq2"}],["path",{"d":"m16 17 2 2 4-4","key":"uh5qu3"}],["path",{"d":"M2 10h20","key":"1ir3d8"}]])
export const CreditCardMinus = ssrIcon('credit-card-minus', [["path",{"d":"M16 17h6","key":"1ook5g"}],["path",{"d":"M22 10H2","key":"jawrgs"}],["path",{"d":"M22 13V7a2 2 0 00-2-2H4a2 2 0 00-2 2v10a2 2 0 002 2h8.536","key":"ljwgfh"}]])
export const CreditCardPlus = ssrIcon('credit-card-plus', [["path",{"d":"M16 17h6","key":"1ook5g"}],["path",{"d":"M19 14v6","key":"1ckrd5"}],["path",{"d":"M22 10H2","key":"jawrgs"}],["path",{"d":"M22 11.354V7a2 2 0 00-2-2H4a2 2 0 00-2 2v10a2 2 0 002 2h8.536","key":"19x2x0"}]])
export const CreditCardX = ssrIcon('credit-card-x', [["path",{"d":"M12.5 19H4a2 2 0 01-2-2V7a2 2 0 012-2h16a2 2 0 012 2v3.5","key":"187u2m"}],["path",{"d":"m16.5 14.5 5 5","key":"ozpm51"}],["path",{"d":"M2 10h20","key":"1ir3d8"}],["path",{"d":"m21.5 14.5-5 5","key":"1bnlip"}]])
export const Croissant = ssrIcon('croissant', [["path",{"d":"M10.2 18H4.774a1.5 1.5 0 0 1-1.352-.97 11 11 0 0 1 .132-6.487","key":"14kkz9"}],["path",{"d":"M18 10.2V4.774a1.5 1.5 0 0 0-.97-1.352 11 11 0 0 0-6.486.132","key":"1g7v07"}],["path",{"d":"M18 5a4 3 0 0 1 4 3 2 2 0 0 1-2 2 10 10 0 0 0-5.139 1.42","key":"ratg6b"}],["path",{"d":"M5 18a3 4 0 0 0 3 4 2 2 0 0 0 2-2 10 10 0 0 1 1.42-5.14","key":"4454f0"}],["path",{"d":"M8.709 2.554a10 10 0 0 0-6.155 6.155 1.5 1.5 0 0 0 .676 1.626l9.807 5.42a2 2 0 0 0 2.718-2.718l-5.42-9.807a1.5 1.5 0 0 0-1.626-.676","key":"qmemie"}]])
export const Crop = ssrIcon('crop', [["path",{"d":"M6 2v14a2 2 0 0 0 2 2h14","key":"ron5a4"}],["path",{"d":"M18 22V8a2 2 0 0 0-2-2H2","key":"7s9ehn"}]])
export const Cross = ssrIcon('cross', [["path",{"d":"M4 9a2 2 0 0 0-2 2v2a2 2 0 0 0 2 2h4a1 1 0 0 1 1 1v4a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2v-4a1 1 0 0 1 1-1h4a2 2 0 0 0 2-2v-2a2 2 0 0 0-2-2h-4a1 1 0 0 1-1-1V4a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v4a1 1 0 0 1-1 1z","key":"1xbrqy"}]])
export const Crosshair = ssrIcon('crosshair', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["line",{"x1":"22","x2":"18","y1":"12","y2":"12","key":"l9bcsi"}],["line",{"x1":"6","x2":"2","y1":"12","y2":"12","key":"13hhkx"}],["line",{"x1":"12","x2":"12","y1":"6","y2":"2","key":"10w3f3"}],["line",{"x1":"12","x2":"12","y1":"22","y2":"18","key":"15g9kq"}]])
export const Crown = ssrIcon('crown', [["path",{"d":"M11.562 3.266a.5.5 0 0 1 .876 0L15.39 8.87a1 1 0 0 0 1.516.294L21.183 5.5a.5.5 0 0 1 .798.519l-2.834 10.246a1 1 0 0 1-.956.734H5.81a1 1 0 0 1-.957-.734L2.02 6.02a.5.5 0 0 1 .798-.519l4.276 3.664a1 1 0 0 0 1.516-.294z","key":"1vdc57"}],["path",{"d":"M5 21h14","key":"11awu3"}]])
export const Cuboid = ssrIcon('cuboid', [["path",{"d":"M10 22v-8","key":"1f8443"}],["path",{"d":"M2.336 8.89 10 14l11.715-7.029","key":"1qnufy"}],["path",{"d":"M22 14a2 2 0 0 1-.971 1.715l-10 6a2 2 0 0 1-2.138-.05l-6-4A2 2 0 0 1 2 16v-6a2 2 0 0 1 .971-1.715l10-6a2 2 0 0 1 2.138.05l6 4A2 2 0 0 1 22 8z","key":"670npk"}]])
export const CupSoda = ssrIcon('cup-soda', [["path",{"d":"m6 8 1.75 12.28a2 2 0 0 0 2 1.72h4.54a2 2 0 0 0 2-1.72L18 8","key":"8166m8"}],["path",{"d":"M5 8h14","key":"pcz4l3"}],["path",{"d":"M7 15a6.47 6.47 0 0 1 5 0 6.47 6.47 0 0 0 5 0","key":"yjz344"}],["path",{"d":"m12 8 1-6h2","key":"3ybfa4"}]])
export const Currency = ssrIcon('currency', [["circle",{"cx":"12","cy":"12","r":"8","key":"46899m"}],["line",{"x1":"3","x2":"6","y1":"3","y2":"6","key":"1jkytn"}],["line",{"x1":"21","x2":"18","y1":"3","y2":"6","key":"14zfjt"}],["line",{"x1":"3","x2":"6","y1":"21","y2":"18","key":"iusuec"}],["line",{"x1":"21","x2":"18","y1":"21","y2":"18","key":"yj2dd7"}]])
export const Cylinder = ssrIcon('cylinder', [["ellipse",{"cx":"12","cy":"5","rx":"9","ry":"3","key":"msslwz"}],["path",{"d":"M3 5v14a9 3 0 0 0 18 0V5","key":"aqi0yr"}]])
export const Dam = ssrIcon('dam', [["path",{"d":"M11 11.31c1.17.56 1.54 1.69 3.5 1.69 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1","key":"157kva"}],["path",{"d":"M11.75 18c.35.5 1.45 1 2.75 1 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1","key":"d7q6m6"}],["path",{"d":"M2 10h4","key":"l0bgd4"}],["path",{"d":"M2 14h4","key":"1gsvsf"}],["path",{"d":"M2 18h4","key":"1bu2t1"}],["path",{"d":"M2 6h4","key":"aawbzj"}],["path",{"d":"M7 3a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h4a1 1 0 0 0 1-1L10 4a1 1 0 0 0-1-1z","key":"pr6s65"}]])
export const Database = ssrIcon('database', [["ellipse",{"cx":"12","cy":"5","rx":"9","ry":"3","key":"msslwz"}],["path",{"d":"M3 5V19A9 3 0 0 0 21 19V5","key":"1wlel7"}],["path",{"d":"M3 12A9 3 0 0 0 21 12","key":"mv7ke4"}]])
export const DatabaseArrowDown = ssrIcon('database-arrow-down', [["path",{"d":"m16 19 3 3 3-3","key":"1ibux0"}],["path",{"d":"M19 16v6","key":"tddt3s"}],["path",{"d":"M21 12.536V5","key":"zeza6i"}],["path",{"d":"M3 12A9 3 0 0 0 15.182 14.806","key":"11e5wb"}],["path",{"d":"M3 5V19A9 3 0 0 0 13.318 21.968","key":"1lyu4j"}],["ellipse",{"cx":"12","cy":"5","rx":"9","ry":"3","key":"msslwz"}]])
export const DatabaseArrowUp = ssrIcon('database-arrow-up', [["path",{"d":"M19 22v-6","key":"qhmiwi"}],["path",{"d":"M21 12.536V5","key":"zeza6i"}],["path",{"d":"m22 19-3-3-3 3","key":"rn6bg2"}],["path",{"d":"M3 12A9 3 0 0 0 14.457 14.886","key":"1941vg"}],["path",{"d":"M3 5V19A9 3 0 0 0 13.318 21.968","key":"1lyu4j"}],["ellipse",{"cx":"12","cy":"5","rx":"9","ry":"3","key":"msslwz"}]])
export const DatabaseBackup = ssrIcon('database-backup', [["ellipse",{"cx":"12","cy":"5","rx":"9","ry":"3","key":"msslwz"}],["path",{"d":"M3 12a9 3 0 0 0 5 2.69","key":"1ui2ym"}],["path",{"d":"M21 9.3V5","key":"6k6cib"}],["path",{"d":"M3 5v14a9 3 0 0 0 6.47 2.88","key":"i62tjy"}],["path",{"d":"M12 12v4h4","key":"1bxaet"}],["path",{"d":"M13 20a5 5 0 0 0 9-3 4.5 4.5 0 0 0-4.5-4.5c-1.33 0-2.54.54-3.41 1.41L12 16","key":"1f4ei9"}]])
export const DatabaseCheck = ssrIcon('database-check', [["path",{"d":"m16 19 2 2 4-4","key":"1b14m6"}],["path",{"d":"M21 13.127V5","key":"59o5vz"}],["path",{"d":"M3 12A9 3 0 0 0 21 12","key":"mv7ke4"}],["path",{"d":"M3 5V19A9 3 0 0 0 13.318 21.968","key":"1lyu4j"}],["ellipse",{"cx":"12","cy":"5","rx":"9","ry":"3","key":"msslwz"}]])
export const DatabaseMinus = ssrIcon('database-minus', [["path",{"d":"M21 15V5","key":"1lbg5w"}],["path",{"d":"M22 19h-6","key":"vcuq98"}],["path",{"d":"M3 12A9 3 0 0 0 21 12","key":"mv7ke4"}],["path",{"d":"M3 5V19A9 3 0 0 0 13.318 21.968","key":"1lyu4j"}],["ellipse",{"cx":"12","cy":"5","rx":"9","ry":"3","key":"msslwz"}]])
export const DatabasePlus = ssrIcon('database-plus', [["path",{"d":"M19 16v6","key":"tddt3s"}],["path",{"d":"M21 12.536V5","key":"zeza6i"}],["path",{"d":"M22 19h-6","key":"vcuq98"}],["path",{"d":"M3 12A9 3 0 0 0 15.1824 14.8061","key":"ukc3b1"}],["path",{"d":"M3 5V19A9 3 0 0 0 13.318 21.968","key":"1lyu4j"}],["ellipse",{"cx":"12","cy":"5","rx":"9","ry":"3","key":"msslwz"}]])
export const DatabaseSearch = ssrIcon('database-search', [["path",{"d":"M21 11.693V5","key":"175m1t"}],["path",{"d":"m22 22-1.875-1.875","key":"13zax7"}],["path",{"d":"M3 12a9 3 0 0 0 8.697 2.998","key":"151u9p"}],["path",{"d":"M3 5v14a9 3 0 0 0 9.28 2.999","key":"q2rs2p"}],["circle",{"cx":"18","cy":"18","r":"3","key":"1xkwt0"}],["ellipse",{"cx":"12","cy":"5","rx":"9","ry":"3","key":"msslwz"}]])
export const DatabaseX = ssrIcon('database-x', [["path",{"d":"m17 17 5 5","key":"p7ous7"}],["path",{"d":"M19.323 13.744A9 3 0 0 0 21 12","key":"hmry77"}],["path",{"d":"M21 13.127V5","key":"59o5vz"}],["path",{"d":"m22 17-5 5","key":"gqnmv0"}],["path",{"d":"M3 12A9 3 0 0 0 13.563 14.954","key":"1rmyhq"}],["path",{"d":"M3 5V19A9 3 0 0 0 13 21.981","key":"159k2m"}],["ellipse",{"cx":"12","cy":"5","rx":"9","ry":"3","key":"msslwz"}]])
export const DatabaseZap = ssrIcon('database-zap', [["ellipse",{"cx":"12","cy":"5","rx":"9","ry":"3","key":"msslwz"}],["path",{"d":"M3 5V19A9 3 0 0 0 15 21.84","key":"14ibmq"}],["path",{"d":"M21 5V8","key":"1marbg"}],["path",{"d":"M21 12L18 17H22L19 22","key":"zafso"}],["path",{"d":"M3 12A9 3 0 0 0 14.59 14.87","key":"1y4wr8"}]])
export const DecimalsArrowLeft = ssrIcon('decimals-arrow-left', [["path",{"d":"m13 21-3-3 3-3","key":"s3o1nf"}],["path",{"d":"M20 18H10","key":"14r3mt"}],["path",{"d":"M3 11h.01","key":"1eifu7"}],["rect",{"x":"6","y":"3","width":"5","height":"8","rx":"2.5","key":"v9paqo"}]])
export const DecimalsArrowRight = ssrIcon('decimals-arrow-right', [["path",{"d":"M10 18h10","key":"1y5s8o"}],["path",{"d":"m17 21 3-3-3-3","key":"1ammt0"}],["path",{"d":"M3 11h.01","key":"1eifu7"}],["rect",{"x":"15","y":"3","width":"5","height":"8","rx":"2.5","key":"76md6a"}],["rect",{"x":"6","y":"3","width":"5","height":"8","rx":"2.5","key":"v9paqo"}]])
export const Delete = ssrIcon('delete', [["path",{"d":"M10 5a2 2 0 0 0-1.344.519l-6.328 5.74a1 1 0 0 0 0 1.481l6.328 5.741A2 2 0 0 0 10 19h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2z","key":"1yo7s0"}],["path",{"d":"m12 9 6 6","key":"anjzzh"}],["path",{"d":"m18 9-6 6","key":"1fp51s"}]])
export const Dessert = ssrIcon('dessert', [["path",{"d":"M10.162 3.167A10 10 0 0 0 2 13a2 2 0 0 0 4 0v-1a2 2 0 0 1 4 0v4a2 2 0 0 0 4 0v-4a2 2 0 0 1 4 0v1a2 2 0 0 0 4-.006 10 10 0 0 0-8.161-9.826","key":"xi88qy"}],["path",{"d":"M20.804 14.869a9 9 0 0 1-17.608 0","key":"1r28rg"}],["circle",{"cx":"12","cy":"4","r":"2","key":"muu5ef"}]])
export const Diameter = ssrIcon('diameter', [["circle",{"cx":"19","cy":"19","r":"2","key":"17f5cg"}],["circle",{"cx":"5","cy":"5","r":"2","key":"1gwv83"}],["path",{"d":"M6.48 3.66a10 10 0 0 1 13.86 13.86","key":"xr8kdq"}],["path",{"d":"m6.41 6.41 11.18 11.18","key":"uhpjw7"}],["path",{"d":"M3.66 6.48a10 10 0 0 0 13.86 13.86","key":"cldpwv"}]])
export const Diamond = ssrIcon('diamond', [["path",{"d":"M2.7 10.3a2.41 2.41 0 0 0 0 3.41l7.59 7.59a2.41 2.41 0 0 0 3.41 0l7.59-7.59a2.41 2.41 0 0 0 0-3.41l-7.59-7.59a2.41 2.41 0 0 0-3.41 0Z","key":"1f1r0c"}]])
export const DiamondMinus = ssrIcon('diamond-minus', [["path",{"d":"M2.7 10.3a2.41 2.41 0 0 0 0 3.41l7.59 7.59a2.41 2.41 0 0 0 3.41 0l7.59-7.59a2.41 2.41 0 0 0 0-3.41L13.7 2.71a2.41 2.41 0 0 0-3.41 0z","key":"1ey20j"}],["path",{"d":"M8 12h8","key":"1wcyev"}]])
export const DiamondPercent = ssrIcon('diamond-percent', [["path",{"d":"M2.7 10.3a2.41 2.41 0 0 0 0 3.41l7.59 7.59a2.41 2.41 0 0 0 3.41 0l7.59-7.59a2.41 2.41 0 0 0 0-3.41L13.7 2.71a2.41 2.41 0 0 0-3.41 0Z","key":"1tpxz2"}],["path",{"d":"M9.2 9.2h.01","key":"1b7bvt"}],["path",{"d":"m14.5 9.5-5 5","key":"17q4r4"}],["path",{"d":"M14.7 14.8h.01","key":"17nsh4"}]])
export const DiamondPlus = ssrIcon('diamond-plus', [["path",{"d":"M12 8v8","key":"napkw2"}],["path",{"d":"M2.7 10.3a2.41 2.41 0 0 0 0 3.41l7.59 7.59a2.41 2.41 0 0 0 3.41 0l7.59-7.59a2.41 2.41 0 0 0 0-3.41L13.7 2.71a2.41 2.41 0 0 0-3.41 0z","key":"1ey20j"}],["path",{"d":"M8 12h8","key":"1wcyev"}]])
export const Dice1 = ssrIcon('dice-1', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","ry":"2","key":"1m3agn"}],["path",{"d":"M12 12h.01","key":"1mp3jc"}]])
export const Dice2 = ssrIcon('dice-2', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","ry":"2","key":"1m3agn"}],["path",{"d":"M15 9h.01","key":"x1ddxp"}],["path",{"d":"M9 15h.01","key":"fzyn71"}]])
export const Dice3 = ssrIcon('dice-3', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","ry":"2","key":"1m3agn"}],["path",{"d":"M16 8h.01","key":"cr5u4v"}],["path",{"d":"M12 12h.01","key":"1mp3jc"}],["path",{"d":"M8 16h.01","key":"18s6g9"}]])
export const Dice4 = ssrIcon('dice-4', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","ry":"2","key":"1m3agn"}],["path",{"d":"M16 8h.01","key":"cr5u4v"}],["path",{"d":"M8 8h.01","key":"1e4136"}],["path",{"d":"M8 16h.01","key":"18s6g9"}],["path",{"d":"M16 16h.01","key":"1f9h7w"}]])
export const Dice5 = ssrIcon('dice-5', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","ry":"2","key":"1m3agn"}],["path",{"d":"M16 8h.01","key":"cr5u4v"}],["path",{"d":"M8 8h.01","key":"1e4136"}],["path",{"d":"M8 16h.01","key":"18s6g9"}],["path",{"d":"M16 16h.01","key":"1f9h7w"}],["path",{"d":"M12 12h.01","key":"1mp3jc"}]])
export const Dice6 = ssrIcon('dice-6', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","ry":"2","key":"1m3agn"}],["path",{"d":"M16 8h.01","key":"cr5u4v"}],["path",{"d":"M16 12h.01","key":"1l6xoz"}],["path",{"d":"M16 16h.01","key":"1f9h7w"}],["path",{"d":"M8 8h.01","key":"1e4136"}],["path",{"d":"M8 12h.01","key":"czm47f"}],["path",{"d":"M8 16h.01","key":"18s6g9"}]])
export const Dices = ssrIcon('dices', [["rect",{"width":"12","height":"12","x":"2","y":"10","rx":"2","ry":"2","key":"6agr2n"}],["path",{"d":"m17.92 14 3.5-3.5a2.24 2.24 0 0 0 0-3l-5-4.92a2.24 2.24 0 0 0-3 0L10 6","key":"1o487t"}],["path",{"d":"M6 18h.01","key":"uhywen"}],["path",{"d":"M10 14h.01","key":"ssrbsk"}],["path",{"d":"M15 6h.01","key":"cblpky"}],["path",{"d":"M18 9h.01","key":"2061c0"}]])
export const Diff = ssrIcon('diff', [["path",{"d":"M12 3v14","key":"7cf3v8"}],["path",{"d":"M5 10h14","key":"elsbfy"}],["path",{"d":"M5 21h14","key":"11awu3"}]])
export const Disc = ssrIcon('disc', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["circle",{"cx":"12","cy":"12","r":"2","key":"1c9p78"}]])
export const Disc2 = ssrIcon('disc-2', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["circle",{"cx":"12","cy":"12","r":"4","key":"4exip2"}],["path",{"d":"M12 12h.01","key":"1mp3jc"}]])
export const Disc3 = ssrIcon('disc-3', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M6 12c0-1.7.7-3.2 1.8-4.2","key":"oqkarx"}],["circle",{"cx":"12","cy":"12","r":"2","key":"1c9p78"}],["path",{"d":"M18 12c0 1.7-.7 3.2-1.8 4.2","key":"1eah9h"}]])
export const DiscAlbum = ssrIcon('disc-album', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["circle",{"cx":"12","cy":"12","r":"5","key":"nd82uf"}],["path",{"d":"M12 12h.01","key":"1mp3jc"}]])
export const Divide = ssrIcon('divide', [["circle",{"cx":"12","cy":"6","r":"1","key":"1bh7o1"}],["line",{"x1":"5","x2":"19","y1":"12","y2":"12","key":"13b5wn"}],["circle",{"cx":"12","cy":"18","r":"1","key":"lqb9t5"}]])
export const SquareDivide = ssrIcon('square-divide', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","ry":"2","key":"1m3agn"}],["line",{"x1":"8","x2":"16","y1":"12","y2":"12","key":"1jonct"}],["line",{"x1":"12","x2":"12","y1":"16","y2":"16","key":"aqc6ln"}],["line",{"x1":"12","x2":"12","y1":"8","y2":"8","key":"1mkcni"}]])
export const Dna = ssrIcon('dna', [["path",{"d":"m10 16 1.5 1.5","key":"11lckj"}],["path",{"d":"m14 8-1.5-1.5","key":"1ohn8i"}],["path",{"d":"M15 2c-1.798 1.998-2.518 3.995-2.807 5.993","key":"80uv8i"}],["path",{"d":"m16.5 10.5 1 1","key":"696xn5"}],["path",{"d":"m17 6-2.891-2.891","key":"xu6p2f"}],["path",{"d":"M2 15c6.667-6 13.333 0 20-6","key":"1pyr53"}],["path",{"d":"m20 9 .891.891","key":"3xwk7g"}],["path",{"d":"M3.109 14.109 4 15","key":"q76aoh"}],["path",{"d":"m6.5 12.5 1 1","key":"cs35ky"}],["path",{"d":"m7 18 2.891 2.891","key":"1sisit"}],["path",{"d":"M9 22c1.798-1.998 2.518-3.995 2.807-5.993","key":"q3hbxp"}]])
export const DnaOff = ssrIcon('dna-off', [["path",{"d":"M15 2c-1.35 1.5-2.092 3-2.5 4.5L14 8","key":"1bivrr"}],["path",{"d":"m17 6-2.891-2.891","key":"xu6p2f"}],["path",{"d":"M2 15c3.333-3 6.667-3 10-3","key":"nxix30"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"m20 9 .891.891","key":"3xwk7g"}],["path",{"d":"M22 9c-1.5 1.35-3 2.092-4.5 2.5l-1-1","key":"18cutr"}],["path",{"d":"M3.109 14.109 4 15","key":"q76aoh"}],["path",{"d":"m6.5 12.5 1 1","key":"cs35ky"}],["path",{"d":"m7 18 2.891 2.891","key":"1sisit"}],["path",{"d":"M9 22c1.35-1.5 2.092-3 2.5-4.5L10 16","key":"rlvei3"}]])
export const Dock = ssrIcon('dock', [["path",{"d":"M2 8h20","key":"d11cs7"}],["rect",{"width":"20","height":"16","x":"2","y":"4","rx":"2","key":"18n3k1"}],["path",{"d":"M6 16h12","key":"u522kt"}]])
export const Dog = ssrIcon('dog', [["path",{"d":"M11.25 16.25h1.5L12 17z","key":"w7jh35"}],["path",{"d":"M16 14v.5","key":"1lajdz"}],["path",{"d":"M4.42 11.247A13.152 13.152 0 0 0 4 14.556C4 18.728 7.582 21 12 21s8-2.272 8-6.444a11.702 11.702 0 0 0-.493-3.309","key":"u7s9ue"}],["path",{"d":"M8 14v.5","key":"1nzgdb"}],["path",{"d":"M8.5 8.5c-.384 1.05-1.083 2.028-2.344 2.5-1.931.722-3.576-.297-3.656-1-.113-.994 1.177-6.53 4-7 1.923-.321 3.651.845 3.651 2.235A7.497 7.497 0 0 1 14 5.277c0-1.39 1.844-2.598 3.767-2.277 2.823.47 4.113 6.006 4 7-.08.703-1.725 1.722-3.656 1-1.261-.472-1.855-1.45-2.239-2.5","key":"v8hric"}]])
export const DollarSign = ssrIcon('dollar-sign', [["line",{"x1":"12","x2":"12","y1":"2","y2":"22","key":"7eqyqh"}],["path",{"d":"M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6","key":"1b0p4s"}]])
export const Donut = ssrIcon('donut', [["path",{"d":"M20.5 10a2.5 2.5 0 0 1-2.4-3H18a2.95 2.95 0 0 1-2.6-4.4 10 10 0 1 0 6.3 7.1c-.3.2-.8.3-1.2.3","key":"19sr3x"}],["circle",{"cx":"12","cy":"12","r":"3","key":"1v7zrd"}]])
export const DoorClosed = ssrIcon('door-closed', [["path",{"d":"M10 12h.01","key":"1kxr2c"}],["path",{"d":"M18 20V6a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v14","key":"36qu9e"}],["path",{"d":"M2 20h20","key":"owomy5"}]])
export const DoorClosedLocked = ssrIcon('door-closed-locked', [["path",{"d":"M10 12h.01","key":"1kxr2c"}],["path",{"d":"M18 9V6a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v14","key":"1bnhmg"}],["path",{"d":"M2 20h8","key":"10ntw1"}],["path",{"d":"M20 17v-2a2 2 0 1 0-4 0v2","key":"pwaxnr"}],["rect",{"x":"14","y":"17","width":"8","height":"5","rx":"1","key":"15pjcy"}]])
export const DoorOpen = ssrIcon('door-open', [["path",{"d":"M11 20H2","key":"nlcfvz"}],["path",{"d":"M11 4.562v16.157a1 1 0 0 0 1.242.97L19 20V5.562a2 2 0 0 0-1.515-1.94l-4-1A2 2 0 0 0 11 4.561z","key":"au4z13"}],["path",{"d":"M11 4H8a2 2 0 0 0-2 2v14","key":"74r1mk"}],["path",{"d":"M14 12h.01","key":"1jfl7z"}],["path",{"d":"M22 20h-3","key":"vhrsz"}]])
export const Dot = ssrIcon('dot', [["circle",{"cx":"12","cy":"12","r":"1","key":"41hilf"}]])
export const SquareDot = ssrIcon('square-dot', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["circle",{"cx":"12","cy":"12","r":"1","key":"41hilf"}]])
export const Download = ssrIcon('download', [["path",{"d":"M12 15V3","key":"m9g1x1"}],["path",{"d":"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4","key":"ih7n3h"}],["path",{"d":"m7 10 5 5 5-5","key":"brsn70"}]])
export const DraftingCompass = ssrIcon('drafting-compass', [["path",{"d":"m12.99 6.74 1.93 3.44","key":"iwagvd"}],["path",{"d":"M19.136 12a10 10 0 0 1-14.271 0","key":"ppmlo4"}],["path",{"d":"m21 21-2.16-3.84","key":"vylbct"}],["path",{"d":"m3 21 8.02-14.26","key":"1ssaw4"}],["circle",{"cx":"12","cy":"5","r":"2","key":"f1ur92"}]])
export const Drama = ssrIcon('drama', [["path",{"d":"M10 11h.01","key":"d2at3l"}],["path",{"d":"M14 6h.01","key":"k028ub"}],["path",{"d":"M18 6h.01","key":"1v4wsw"}],["path",{"d":"M6.5 13.1h.01","key":"1748ia"}],["path",{"d":"M22 5c0 9-4 12-6 12s-6-3-6-12c0-2 2-3 6-3s6 1 6 3","key":"172yzv"}],["path",{"d":"M17.4 9.9c-.8.8-2 .8-2.8 0","key":"1obv0w"}],["path",{"d":"M10.1 7.1C9 7.2 7.7 7.7 6 8.6c-3.5 2-4.7 3.9-3.7 5.6 4.5 7.8 9.5 8.4 11.2 7.4.9-.5 1.9-2.1 1.9-4.7","key":"rqjl8i"}],["path",{"d":"M9.1 16.5c.3-1.1 1.4-1.7 2.4-1.4","key":"1mr6wy"}]])
export const Drill = ssrIcon('drill', [["path",{"d":"M10 18a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1H5a3 3 0 0 1-3-3 1 1 0 0 1 1-1z","key":"ioqxb1"}],["path",{"d":"M13 10H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1l-.81 3.242a1 1 0 0 1-.97.758H8","key":"1rs59n"}],["path",{"d":"M14 4h3a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1h-3","key":"105ega"}],["path",{"d":"M18 6h4","key":"66u95g"}],["path",{"d":"m5 10-2 8","key":"xt2lic"}],["path",{"d":"m7 18 2-8","key":"1bzku2"}]])
export const Drone = ssrIcon('drone', [["path",{"d":"M10 10 7 7","key":"zp14k7"}],["path",{"d":"m10 14-3 3","key":"1jrpxk"}],["path",{"d":"m14 10 3-3","key":"7tigam"}],["path",{"d":"m14 14 3 3","key":"vm23p3"}],["path",{"d":"M14.205 4.139a4 4 0 1 1 5.439 5.863","key":"1tm5p2"}],["path",{"d":"M19.637 14a4 4 0 1 1-5.432 5.868","key":"16egi2"}],["path",{"d":"M4.367 10a4 4 0 1 1 5.438-5.862","key":"1wta6a"}],["path",{"d":"M9.795 19.862a4 4 0 1 1-5.429-5.873","key":"q39hpv"}],["rect",{"x":"10","y":"8","width":"4","height":"8","rx":"1","key":"phrjt1"}]])
export const Droplet = ssrIcon('droplet', [["path",{"d":"M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z","key":"c7niix"}]])
export const DropletOff = ssrIcon('droplet-off', [["path",{"d":"M18.715 13.186C18.29 11.858 17.384 10.607 16 9.5c-2-1.6-3.5-4-4-6.5a10.7 10.7 0 0 1-.884 2.586","key":"8suz2t"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M8.795 8.797A11 11 0 0 1 8 9.5C6 11.1 5 13 5 15a7 7 0 0 0 13.222 3.208","key":"19dw9m"}]])
export const Droplets = ssrIcon('droplets', [["path",{"d":"M7 16.3c2.2 0 4-1.83 4-4.05 0-1.16-.57-2.26-1.71-3.19S7.29 6.75 7 5.3c-.29 1.45-1.14 2.84-2.29 3.76S3 11.1 3 12.25c0 2.22 1.8 4.05 4 4.05z","key":"1ptgy4"}],["path",{"d":"M12.56 6.6A10.97 10.97 0 0 0 14 3.02c.5 2.5 2 4.9 4 6.5s3 3.5 3 5.5a6.98 6.98 0 0 1-11.91 4.97","key":"1sl1rz"}]])
export const Drum = ssrIcon('drum', [["path",{"d":"m2 2 8 8","key":"1v6059"}],["path",{"d":"m22 2-8 8","key":"173r8a"}],["ellipse",{"cx":"12","cy":"9","rx":"10","ry":"5","key":"liohsx"}],["path",{"d":"M7 13.4v7.9","key":"1yi6u9"}],["path",{"d":"M12 14v8","key":"1tn2tj"}],["path",{"d":"M17 13.4v7.9","key":"eqz2v3"}],["path",{"d":"M2 9v8a10 5 0 0 0 20 0V9","key":"1750ul"}]])
export const Drumstick = ssrIcon('drumstick', [["path",{"d":"M15.4 15.63a7.875 6 135 1 1 6.23-6.23 4.5 3.43 135 0 0-6.23 6.23","key":"1dtqwm"}],["path",{"d":"m8.29 12.71-2.6 2.6a2.5 2.5 0 1 0-1.65 4.65A2.5 2.5 0 1 0 8.7 18.3l2.59-2.59","key":"1oq1fw"}]])
export const Dumbbell = ssrIcon('dumbbell', [["path",{"d":"M17.596 12.768a2 2 0 1 0 2.829-2.829l-1.768-1.767a2 2 0 0 0 2.828-2.829l-2.828-2.828a2 2 0 0 0-2.829 2.828l-1.767-1.768a2 2 0 1 0-2.829 2.829z","key":"9m4mmf"}],["path",{"d":"m2.5 21.5 1.4-1.4","key":"17g3f0"}],["path",{"d":"m20.1 3.9 1.4-1.4","key":"1qn309"}],["path",{"d":"M5.343 21.485a2 2 0 1 0 2.829-2.828l1.767 1.768a2 2 0 1 0 2.829-2.829l-6.364-6.364a2 2 0 1 0-2.829 2.829l1.768 1.767a2 2 0 0 0-2.828 2.829z","key":"1t2c92"}],["path",{"d":"m9.6 14.4 4.8-4.8","key":"6umqxw"}]])
export const Ear = ssrIcon('ear', [["path",{"d":"M6 8.5a6.5 6.5 0 1 1 13 0c0 6-6 6-6 10a3.5 3.5 0 1 1-7 0","key":"1dfaln"}],["path",{"d":"M15 8.5a2.5 2.5 0 0 0-5 0v1a2 2 0 1 1 0 4","key":"1qnva7"}]])
export const EarOff = ssrIcon('ear-off', [["path",{"d":"M6 18.5a3.5 3.5 0 1 0 7 0c0-1.57.92-2.52 2.04-3.46","key":"1qngmn"}],["path",{"d":"M6 8.5c0-.75.13-1.47.36-2.14","key":"b06bma"}],["path",{"d":"M8.8 3.15A6.5 6.5 0 0 1 19 8.5c0 1.63-.44 2.81-1.09 3.76","key":"g10hsz"}],["path",{"d":"M12.5 6A2.5 2.5 0 0 1 15 8.5M10 13a2 2 0 0 0 1.82-1.18","key":"ygzou7"}],["line",{"x1":"2","x2":"22","y1":"2","y2":"22","key":"a6p6uj"}]])
export const Earth = ssrIcon('earth', [["path",{"d":"M21.54 15H17a2 2 0 0 0-2 2v4.54","key":"1djwo0"}],["path",{"d":"M7 3.34V5a3 3 0 0 0 3 3a2 2 0 0 1 2 2c0 1.1.9 2 2 2a2 2 0 0 0 2-2c0-1.1.9-2 2-2h3.17","key":"1tzkfa"}],["path",{"d":"M11 21.95V18a2 2 0 0 0-2-2a2 2 0 0 1-2-2v-1a2 2 0 0 0-2-2H2.05","key":"14pb5j"}],["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}]])
export const EarthLock = ssrIcon('earth-lock', [["path",{"d":"M7 3.34V5a3 3 0 0 0 3 3","key":"w732o8"}],["path",{"d":"M11 21.95V18a2 2 0 0 0-2-2 2 2 0 0 1-2-2v-1a2 2 0 0 0-2-2H2.05","key":"f02343"}],["path",{"d":"M21.54 15H17a2 2 0 0 0-2 2v4.54","key":"1djwo0"}],["path",{"d":"M12 2a10 10 0 1 0 9.54 13","key":"zjsr6q"}],["path",{"d":"M20 6V4a2 2 0 1 0-4 0v2","key":"1of5e8"}],["rect",{"width":"8","height":"5","x":"14","y":"6","rx":"1","key":"1fmf51"}]])
export const Eclipse = ssrIcon('eclipse', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 2a7 7 0 1 0 10 10","key":"1yuj32"}]])
export const SquarePen = ssrIcon('square-pen', [["path",{"d":"M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7","key":"1m0v6g"}],["path",{"d":"M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z","key":"ohrbg2"}]])
export const Pen = ssrIcon('pen', [["path",{"d":"M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z","key":"1a8usu"}]])
export const PenLine = ssrIcon('pen-line', [["path",{"d":"M13 21h8","key":"1jsn5i"}],["path",{"d":"M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z","key":"1a8usu"}]])
export const Egg = ssrIcon('egg', [["path",{"d":"M12 2C8 2 4 8 4 14a8 8 0 0 0 16 0c0-6-4-12-8-12","key":"1le142"}]])
export const EggFried = ssrIcon('egg-fried', [["circle",{"cx":"11.5","cy":"12.5","r":"3.5","key":"1cl1mi"}],["path",{"d":"M3 8c0-3.5 2.5-6 6.5-6 5 0 4.83 3 7.5 5s5 2 5 6c0 4.5-2.5 6.5-7 6.5-2.5 0-2.5 2.5-6 2.5s-7-2-7-5.5c0-3 1.5-3 1.5-5C3.5 10 3 9 3 8Z","key":"165ef9"}]])
export const EggOff = ssrIcon('egg-off', [["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M20 14.347V14c0-6-4-12-8-12-1.078 0-2.157.436-3.157 1.19","key":"13g2jy"}],["path",{"d":"M6.206 6.21C4.871 8.4 4 11.2 4 14a8 8 0 0 0 14.568 4.568","key":"1581id"}]])
export const Eject = ssrIcon('eject', [["path",{"d":"M4 13a1 1 0 0 1-.72-1.695l7.257-7.668a2 2 0 0 1 2.926 0l7.256 7.668A1 1 0 0 1 20 13z","key":"ua5u6w"}],["rect",{"x":"3","y":"17","width":"18","height":"4","rx":"1","key":"kj6cfs"}]])
export const Ellipse = ssrIcon('ellipse', [["ellipse",{"cx":"12","cy":"12","rx":"10","ry":"6","key":"swdkt4"}]])
export const Ellipsis = ssrIcon('ellipsis', [["circle",{"cx":"12","cy":"12","r":"1","key":"41hilf"}],["circle",{"cx":"19","cy":"12","r":"1","key":"1wjl8i"}],["circle",{"cx":"5","cy":"12","r":"1","key":"1pcz8c"}]])
export const EllipsisVertical = ssrIcon('ellipsis-vertical', [["circle",{"cx":"12","cy":"12","r":"1","key":"41hilf"}],["circle",{"cx":"12","cy":"5","r":"1","key":"gxeob9"}],["circle",{"cx":"12","cy":"19","r":"1","key":"lyex9k"}]])
export const Equal = ssrIcon('equal', [["line",{"x1":"5","x2":"19","y1":"9","y2":"9","key":"1nwqeh"}],["line",{"x1":"5","x2":"19","y1":"15","y2":"15","key":"g8yjpy"}]])
export const EqualApproximately = ssrIcon('equal-approximately', [["path",{"d":"M5 15a6.5 6.5 0 0 1 7 0 6.5 6.5 0 0 0 7 0","key":"yrdkhy"}],["path",{"d":"M5 9a6.5 6.5 0 0 1 7 0 6.5 6.5 0 0 0 7 0","key":"gzkvyz"}]])
export const EqualNot = ssrIcon('equal-not', [["line",{"x1":"5","x2":"19","y1":"9","y2":"9","key":"1nwqeh"}],["line",{"x1":"5","x2":"19","y1":"15","y2":"15","key":"g8yjpy"}],["line",{"x1":"19","x2":"5","y1":"5","y2":"19","key":"1x9vlm"}]])
export const SquareEqual = ssrIcon('square-equal', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M7 10h10","key":"1101jm"}],["path",{"d":"M7 14h10","key":"1mhdw3"}]])
export const Eraser = ssrIcon('eraser', [["path",{"d":"M21 21H8a2 2 0 0 1-1.42-.587l-3.994-3.999a2 2 0 0 1 0-2.828l10-10a2 2 0 0 1 2.829 0l5.999 6a2 2 0 0 1 0 2.828L12.834 21","key":"g5wo59"}],["path",{"d":"m5.082 11.09 8.828 8.828","key":"1wx5vj"}]])
export const EthernetPort = ssrIcon('ethernet-port', [["path",{"d":"M10 8v1","key":"1talb4"}],["path",{"d":"M14 8v1","key":"1rsfgr"}],["path",{"d":"M18 8v1","key":"gnkwox"}],["path",{"d":"M19 17a2 2 0 00-1.765 1.059l-.47.882A2 2 0 0115 20H9a2 2 0 01-1.765-1.059l-.47-.882A2 2 0 005 17H4a2 2 0 01-2-2V6a2 2 0 012-2h16a2 2 0 012 2v9a2 2 0 01-2 2z","key":"v5qa57"}],["path",{"d":"M6 8v1","key":"1636ez"}]])
export const Euro = ssrIcon('euro', [["path",{"d":"M4 10h12","key":"1y6xl8"}],["path",{"d":"M4 14h9","key":"1loblj"}],["path",{"d":"M19 6a7.7 7.7 0 0 0-5.2-2A7.9 7.9 0 0 0 6 12c0 4.4 3.5 8 7.8 8 2 0 3.8-.8 5.2-2","key":"1j6lzo"}]])
export const EvCharger = ssrIcon('ev-charger', [["path",{"d":"M14 13h2a2 2 0 0 1 2 2v2a2 2 0 0 0 4 0v-6.998a2 2 0 0 0-.59-1.42L18 5","key":"1wtuz0"}],["path",{"d":"M14 21V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v16","key":"e09ifn"}],["path",{"d":"M2 21h13","key":"1x0fut"}],["path",{"d":"M3 7h11","key":"19efrr"}],["path",{"d":"m9 11-2 3h3l-2 3","key":"lmzxi1"}]])
export const Expand = ssrIcon('expand', [["path",{"d":"m15 15 6 6","key":"1s409w"}],["path",{"d":"m15 9 6-6","key":"ko1vev"}],["path",{"d":"M21 16v5h-5","key":"1ck2sf"}],["path",{"d":"M21 8V3h-5","key":"1qoq8a"}],["path",{"d":"M3 16v5h5","key":"1t08am"}],["path",{"d":"m3 21 6-6","key":"wwnumi"}],["path",{"d":"M3 8V3h5","key":"1ln10m"}],["path",{"d":"M9 9 3 3","key":"v551iv"}]])
export const ExternalLink = ssrIcon('external-link', [["path",{"d":"M15 3h6v6","key":"1q9fwt"}],["path",{"d":"M10 14 21 3","key":"gplh6r"}],["path",{"d":"M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6","key":"a6xqqp"}]])
export const Eye = ssrIcon('eye', [["path",{"d":"M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0","key":"1nclc0"}],["circle",{"cx":"12","cy":"12","r":"3","key":"1v7zrd"}]])
export const EyeClosed = ssrIcon('eye-closed', [["path",{"d":"m15 18-.722-3.25","key":"1j64jw"}],["path",{"d":"M2 8a10.645 10.645 0 0 0 20 0","key":"1e7gxb"}],["path",{"d":"m20 15-1.726-2.05","key":"1cnuld"}],["path",{"d":"m4 15 1.726-2.05","key":"1dsqqd"}],["path",{"d":"m9 18 .722-3.25","key":"ypw2yx"}]])
export const EyeDashed = ssrIcon('eye-dashed', [["path",{"d":"M13.054 18.946a11 11 0 0 1-2.11 0","key":"1lgjj0"}],["path",{"d":"M13.054 5.054a11 11 0 0 0-2.11-.001","key":"f7voaa"}],["path",{"d":"M17.072 6.274a11 11 0 0 1 1.753 1.173","key":"1rga24"}],["path",{"d":"M18.825 16.552a11 11 0 0 1-1.753 1.174","key":"jfvai2"}],["path",{"d":"M2.514 13.303a11 11 0 0 1-.452-.954 1 1 0 0 1 0-.697 11 11 0 0 1 .45-.955","key":"1deed4"}],["path",{"d":"M21.485 10.697a11 11 0 0 1 .453.955 1 1 0 0 1 0 .697 11 11 0 0 1-.453.954","key":"1k4xil"}],["path",{"d":"M5.173 7.448a11 11 0 0 1 1.753-1.174","key":"mwd8rq"}],["path",{"d":"M6.926 17.726a11 11 0 0 1-1.753-1.174","key":"15rpim"}],["circle",{"cx":"12","cy":"12","r":"3","key":"1v7zrd"}]])
export const EyeOff = ssrIcon('eye-off', [["path",{"d":"M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49","key":"ct8e1f"}],["path",{"d":"M14.084 14.158a3 3 0 0 1-4.242-4.242","key":"151rxh"}],["path",{"d":"M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143","key":"13bj9a"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}]])
export const FaceGrinning = ssrIcon('face-grinning', [["path",{"d":"M15 10V9","key":"4dkmfx"}],["path",{"d":"M7.084 14.302a5.12 5.12 0 009.833 0 .24.24 0 00-.235-.302H7.32a.24.24 0 00-.235.302","key":"1ad3z7"}],["path",{"d":"M9 10V9","key":"1lazqi"}],["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}]])
export const FaceNeutral = ssrIcon('face-neutral', [["path",{"d":"M15 10V9","key":"4dkmfx"}],["path",{"d":"M8 16h8","key":"10ke2u"}],["path",{"d":"M9 10V9","key":"1lazqi"}],["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}]])
export const FaceSlightlyFrowning = ssrIcon('face-slightly-frowning', [["path",{"d":"M15 10V9","key":"4dkmfx"}],["path",{"d":"M9 10V9","key":"1lazqi"}],["path",{"d":"M9 16a5 5 0 016 0","key":"34mdxb"}],["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}]])
export const FaceSlightlySmiling = ssrIcon('face-slightly-smiling', [["path",{"d":"M15 10V9","key":"4dkmfx"}],["path",{"d":"M16.472 15a6 6 0 01-8.943 0","key":"7qomzy"}],["path",{"d":"M9 10V9","key":"1lazqi"}],["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}]])
export const FaceSlightlySmilingPlus = ssrIcon('face-slightly-smiling-plus', [["path",{"d":"M13.267 2.08a10 10 0 108.653 8.653","key":"1wbpyh"}],["path",{"d":"M15 10V9","key":"4dkmfx"}],["path",{"d":"M16 5h6","key":"1vod17"}],["path",{"d":"M16.472 15a6 6 0 01-8.943 0","key":"7qomzy"}],["path",{"d":"M19 2v6","key":"4bpg5p"}],["path",{"d":"M9 10V9","key":"1lazqi"}]])
export const Factory = ssrIcon('factory', [["path",{"d":"M12 16h.01","key":"1drbdi"}],["path",{"d":"M16 16h.01","key":"1f9h7w"}],["path",{"d":"M3 19a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V8.5a.5.5 0 0 0-.769-.422l-4.462 2.844A.5.5 0 0 1 15 10.5v-2a.5.5 0 0 0-.769-.422L9.77 10.922A.5.5 0 0 1 9 10.5V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2z","key":"1iv0i2"}],["path",{"d":"M8 16h.01","key":"18s6g9"}]])
export const Fan = ssrIcon('fan', [["path",{"d":"M10.827 16.379a6.082 6.082 0 0 1-8.618-7.002l5.412 1.45a6.082 6.082 0 0 1 7.002-8.618l-1.45 5.412a6.082 6.082 0 0 1 8.618 7.002l-5.412-1.45a6.082 6.082 0 0 1-7.002 8.618l1.45-5.412Z","key":"484a7f"}],["path",{"d":"M12 12v.01","key":"u5ubse"}]])
export const FastForward = ssrIcon('fast-forward', [["path",{"d":"M12 6a2 2 0 0 1 3.414-1.414l6 6a2 2 0 0 1 0 2.828l-6 6A2 2 0 0 1 12 18z","key":"b19h5q"}],["path",{"d":"M2 6a2 2 0 0 1 3.414-1.414l6 6a2 2 0 0 1 0 2.828l-6 6A2 2 0 0 1 2 18z","key":"h7h5ge"}]])
export const Feather = ssrIcon('feather', [["path",{"d":"M14.086 18.412A2 2 0 0112.67 19H5v-7.672a2 2 0 01.586-1.414L11.75 3.75a6 6 0 118.49 8.49z","key":"1nq9jb"}],["path",{"d":"M16 8 2 22","key":"vp34q"}],["path",{"d":"M17.488 15H9","key":"16yirz"}]])
export const Fence = ssrIcon('fence', [["path",{"d":"M4 3 2 5v15c0 .6.4 1 1 1h2c.6 0 1-.4 1-1V5Z","key":"1n2rgs"}],["path",{"d":"M6 8h4","key":"utf9t1"}],["path",{"d":"M6 18h4","key":"12yh4b"}],["path",{"d":"m12 3-2 2v15c0 .6.4 1 1 1h2c.6 0 1-.4 1-1V5Z","key":"3ha7mj"}],["path",{"d":"M14 8h4","key":"1r8wg2"}],["path",{"d":"M14 18h4","key":"1t3kbu"}],["path",{"d":"m20 3-2 2v15c0 .6.4 1 1 1h2c.6 0 1-.4 1-1V5Z","key":"dfd4e2"}]])
export const FerrisWheel = ssrIcon('ferris-wheel', [["circle",{"cx":"12","cy":"12","r":"2","key":"1c9p78"}],["path",{"d":"M12 2v4","key":"3427ic"}],["path",{"d":"m6.8 15-3.5 2","key":"hjy98k"}],["path",{"d":"m20.7 7-3.5 2","key":"f08gto"}],["path",{"d":"M6.8 9 3.3 7","key":"1aevh4"}],["path",{"d":"m20.7 17-3.5-2","key":"1liqo3"}],["path",{"d":"m9 22 3-8 3 8","key":"wees03"}],["path",{"d":"M8 22h8","key":"rmew8v"}],["path",{"d":"M18 18.7a9 9 0 1 0-12 0","key":"dhzg4g"}]])
export const File = ssrIcon('file', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}]])
export const FileArchive = ssrIcon('file-archive', [["path",{"d":"M13.659 22H18a2 2 0 0 0 2-2V8a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 14 2H6a2 2 0 0 0-2 2v11.5","key":"4pqfef"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M8 12v-1","key":"1ej8lb"}],["path",{"d":"M8 18v-2","key":"qcmpov"}],["path",{"d":"M8 7V6","key":"1nbb54"}],["circle",{"cx":"8","cy":"20","r":"2","key":"ckkr5m"}]])
export const FileHeadphone = ssrIcon('file-headphone', [["path",{"d":"M4 6.835V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2h-.343","key":"1vfytu"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M2 19a2 2 0 0 1 4 0v1a2 2 0 0 1-4 0v-4a6 6 0 0 1 12 0v4a2 2 0 0 1-4 0v-1a2 2 0 0 1 4 0","key":"1etmh7"}]])
export const FileAxis3d = ssrIcon('file-axis-3d', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"m8 18 4-4","key":"12zab0"}],["path",{"d":"M8 10v8h8","key":"tlaukw"}]])
export const FileBadge = ssrIcon('file-badge', [["path",{"d":"M13 22h5a2 2 0 0 0 2-2V8a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 14 2H6a2 2 0 0 0-2 2v3.3","key":"cvl1xm"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"m7.69 16.479 1.29 4.88a.5.5 0 0 1-.698.591l-1.843-.849a1 1 0 0 0-.879.001l-1.846.85a.5.5 0 0 1-.692-.593l1.29-4.88","key":"1ff7gj"}],["circle",{"cx":"6","cy":"14","r":"3","key":"a1xfv6"}]])
export const FileChartColumnIncreasing = ssrIcon('file-chart-column-increasing', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M8 18v-2","key":"qcmpov"}],["path",{"d":"M12 18v-4","key":"q1q25u"}],["path",{"d":"M16 18v-6","key":"15y0np"}]])
export const FileChartColumn = ssrIcon('file-chart-column', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M8 18v-1","key":"zg0ygc"}],["path",{"d":"M12 18v-6","key":"17g6i2"}],["path",{"d":"M16 18v-3","key":"j5jt4h"}]])
export const FileBox = ssrIcon('file-box', [["path",{"d":"M14 2v5a1 1 0 001 1h5","key":"9v5fu7"}],["path",{"d":"M14.692 22H18a2 2 0 002-2V8a2.4 2.4 0 00-.706-1.706l-3.588-3.588A2.4 2.4 0 0014 2H6a2 2 0 00-2 2v3.804","key":"1ne0j7"}],["path",{"d":"M2.264 13.752 7 16.5l4.737-2.748","key":"t73mg3"}],["path",{"d":"M2.995 13.014A2 2 0 002 14.744v3.516a2 2 0 00.996 1.73l3 1.74a2 2 0 002.008 0l3-1.74A2 2 0 0012 18.26v-3.517a2 2 0 00-.995-1.73l-3-1.742a2 2 0 00-1.892-.064z","key":"h4qck"}],["path",{"d":"M7 16.5V22","key":"1i1gou"}]])
export const FileBraces = ssrIcon('file-braces', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M10 12a1 1 0 0 0-1 1v1a1 1 0 0 1-1 1 1 1 0 0 1 1 1v1a1 1 0 0 0 1 1","key":"1oajmo"}],["path",{"d":"M14 18a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1 1 1 0 0 1-1-1v-1a1 1 0 0 0-1-1","key":"mpwhp6"}]])
export const FileBracesCorner = ssrIcon('file-braces-corner', [["path",{"d":"M14 22h4a2 2 0 0 0 2-2V8a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 14 2H6a2 2 0 0 0-2 2v6","key":"14cnrg"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M5 14a1 1 0 0 0-1 1v2a1 1 0 0 1-1 1 1 1 0 0 1 1 1v2a1 1 0 0 0 1 1","key":"sr0ebq"}],["path",{"d":"M9 22a1 1 0 0 0 1-1v-2a1 1 0 0 1 1-1 1 1 0 0 1-1-1v-2a1 1 0 0 0-1-1","key":"w793db"}]])
export const FileChartLine = ssrIcon('file-chart-line', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"m16 13-3.5 3.5-2-2L8 17","key":"zz7yod"}]])
export const FileChartPie = ssrIcon('file-chart-pie', [["path",{"d":"M15.941 22H18a2 2 0 0 0 2-2V8a2.4 2.4 0 0 0-.706-1.704l-3.588-3.588A2.4 2.4 0 0 0 14 2H6a2 2 0 0 0-2 2v3.512","key":"13hoie"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M4.017 11.512a6 6 0 1 0 8.466 8.475","key":"s6vs5t"}],["path",{"d":"M9 16a1 1 0 0 1-1-1v-4c0-.552.45-1.008.995-.917a6 6 0 0 1 4.922 4.922c.091.544-.365.995-.917.995z","key":"1dl6s6"}]])
export const FileCheck = ssrIcon('file-check', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"m9 15 2 2 4-4","key":"1grp1n"}]])
export const FileCheckCorner = ssrIcon('file-check-corner', [["path",{"d":"M10.5 22H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v6","key":"g5mvt7"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"m14 20 2 2 4-4","key":"15kota"}]])
export const FileClock = ssrIcon('file-clock', [["path",{"d":"M16 22h2a2 2 0 0 0 2-2V8a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 14 2H6a2 2 0 0 0-2 2v2.85","key":"ryk6xj"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M8 14v2.2l1.6 1","key":"6m4bie"}],["circle",{"cx":"8","cy":"16","r":"6","key":"10v15b"}]])
export const FileCode = ssrIcon('file-code', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M10 12.5 8 15l2 2.5","key":"1tg20x"}],["path",{"d":"m14 12.5 2 2.5-2 2.5","key":"yinavb"}]])
export const FileCodeCorner = ssrIcon('file-code-corner', [["path",{"d":"M4 12.15V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2h-3.35","key":"1wthlu"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"m5 16-3 3 3 3","key":"331omg"}],["path",{"d":"m9 22 3-3-3-3","key":"lsp7cz"}]])
export const FileCog = ssrIcon('file-cog', [["path",{"d":"M15 8a1 1 0 0 1-1-1V2a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8z","key":"1ckgky"}],["path",{"d":"M20 8v12a2 2 0 0 1-2 2h-4.182","key":"1726p0"}],["path",{"d":"m3.305 19.53.923-.382","key":"ao1pio"}],["path",{"d":"M4 10.592V4a2 2 0 0 1 2-2h8","key":"1foop0"}],["path",{"d":"m4.228 16.852-.924-.383","key":"1fv9zy"}],["path",{"d":"m5.852 15.228-.383-.923","key":"1a9hc2"}],["path",{"d":"m5.852 20.772-.383.924","key":"1sh9ke"}],["path",{"d":"m8.148 15.228.383-.923","key":"4yu6lf"}],["path",{"d":"m8.53 21.696-.382-.924","key":"18b0s9"}],["path",{"d":"m9.773 16.852.922-.383","key":"ti6xop"}],["path",{"d":"m9.773 19.148.922.383","key":"rws47d"}],["circle",{"cx":"7","cy":"18","r":"3","key":"lvkj7j"}]])
export const FileDiff = ssrIcon('file-diff', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M9 10h6","key":"9gxzsh"}],["path",{"d":"M12 13V7","key":"h0r20n"}],["path",{"d":"M9 17h6","key":"r8uit2"}]])
export const FileDigit = ssrIcon('file-digit', [["path",{"d":"M4 12V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2","key":"jrl274"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M10 16h2v6","key":"1bxocy"}],["path",{"d":"M10 22h4","key":"ceow96"}],["rect",{"x":"2","y":"16","width":"4","height":"6","rx":"2","key":"r45zd0"}]])
export const FileDown = ssrIcon('file-down', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M12 18v-6","key":"17g6i2"}],["path",{"d":"m9 15 3 3 3-3","key":"1npd3o"}]])
export const FilePen = ssrIcon('file-pen', [["path",{"d":"M12.659 22H18a2 2 0 0 0 2-2V8a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 14 2H6a2 2 0 0 0-2 2v9.34","key":"o6klzx"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M10.378 12.622a1 1 0 0 1 3 3.003L8.36 20.637a2 2 0 0 1-.854.506l-2.867.837a.5.5 0 0 1-.62-.62l.836-2.869a2 2 0 0 1 .506-.853z","key":"zhnas1"}]])
export const FileExclamationPoint = ssrIcon('file-exclamation-point', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M12 9v4","key":"juzpu7"}],["path",{"d":"M12 17h.01","key":"p32p05"}]])
export const FileHeart = ssrIcon('file-heart', [["path",{"d":"M13 22h5a2 2 0 0 0 2-2V8a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 14 2H6a2 2 0 0 0-2 2v7","key":"oagw2b"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M3.62 18.8A2.25 2.25 0 1 1 7 15.836a2.25 2.25 0 1 1 3.38 2.966l-2.626 2.856a1 1 0 0 1-1.507 0z","key":"rg3psg"}]])
export const FileImage = ssrIcon('file-image', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["circle",{"cx":"10","cy":"12","r":"2","key":"737tya"}],["path",{"d":"m20 17-1.296-1.296a2.41 2.41 0 0 0-3.408 0L9 22","key":"wt3hpn"}]])
export const FileInput = ssrIcon('file-input', [["path",{"d":"M4 11V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-1","key":"1q9hii"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M2 15h10","key":"jfw4w8"}],["path",{"d":"m9 18 3-3-3-3","key":"112psh"}]])
export const FileKey = ssrIcon('file-key', [["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M4 12v6","key":"bg1pfk"}],["path",{"d":"M4 14h2","key":"1sf9f8"}],["path",{"d":"M9.65 22H18a2 2 0 0 0 2-2V8a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 14 2H6a2 2 0 0 0-2 2v4","key":"d56i0q"}],["circle",{"cx":"4","cy":"20","r":"2","key":"6kqj1y"}]])
export const FileLock = ssrIcon('file-lock', [["path",{"d":"M4 9.8V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2h-3","key":"1432pc"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M9 17v-2a2 2 0 0 0-4 0v2","key":"168m41"}],["rect",{"width":"8","height":"5","x":"3","y":"17","rx":"1","key":"o8vfew"}]])
export const FileMinus = ssrIcon('file-minus', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M9 15h6","key":"cctwl0"}]])
export const FileMinusCorner = ssrIcon('file-minus-corner', [["path",{"d":"M20 14V8a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12","key":"l9p8hp"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M14 18h6","key":"1m8k6r"}]])
export const FileMusic = ssrIcon('file-music', [["path",{"d":"M11.65 22H18a2 2 0 0 0 2-2V8a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 14 2H6a2 2 0 0 0-2 2v10.35","key":"5ad7z2"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M8 20v-7l3 1.474","key":"1ggyb9"}],["circle",{"cx":"6","cy":"20","r":"2","key":"j7wjp0"}]])
export const FileOutput = ssrIcon('file-output', [["path",{"d":"M4.226 20.925A2 2 0 0 0 6 22h12a2 2 0 0 0 2-2V8a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 14 2H6a2 2 0 0 0-2 2v3.127","key":"wfxp4w"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"m5 11-3 3","key":"1dgrs4"}],["path",{"d":"m5 17-3-3h10","key":"1mvvaf"}]])
export const FilePenLine = ssrIcon('file-pen-line', [["path",{"d":"M14.364 13.634a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506l4.013-4.009a1 1 0 0 0-3.004-3.004z","key":"ukzhwg"}],["path",{"d":"M14.487 7.858A1 1 0 0 1 14 7V2","key":"1klhew"}],["path",{"d":"M20 19.645V20a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l2.516 2.516","key":"rxaxab"}],["path",{"d":"M8 18h1","key":"13wk12"}]])
export const FilePlay = ssrIcon('file-play', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M15.033 13.44a.647.647 0 0 1 0 1.12l-4.065 2.352a.645.645 0 0 1-.968-.56v-4.704a.645.645 0 0 1 .967-.56z","key":"1tzo1f"}]])
export const FilePlus = ssrIcon('file-plus', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M9 15h6","key":"cctwl0"}],["path",{"d":"M12 18v-6","key":"17g6i2"}]])
export const FilePlusCorner = ssrIcon('file-plus-corner', [["path",{"d":"M11.35 22H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v5.35","key":"17jvcc"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M14 19h6","key":"bvotb8"}],["path",{"d":"M17 16v6","key":"18yu1i"}]])
export const FileQuestionMark = ssrIcon('file-question-mark', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M12 17h.01","key":"p32p05"}],["path",{"d":"M9.1 9a3 3 0 0 1 5.82 1c0 2-3 3-3 3","key":"mhlwft"}]])
export const FileScan = ssrIcon('file-scan', [["path",{"d":"M20 10V8a2.4 2.4 0 0 0-.706-1.704l-3.588-3.588A2.4 2.4 0 0 0 14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h4.35","key":"1cdjst"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M16 14a2 2 0 0 0-2 2","key":"ceaadl"}],["path",{"d":"M16 22a2 2 0 0 1-2-2","key":"1wqh5n"}],["path",{"d":"M20 14a2 2 0 0 1 2 2","key":"1ny6zw"}],["path",{"d":"M20 22a2 2 0 0 0 2-2","key":"1l9q4k"}]])
export const FileSearch = ssrIcon('file-search', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["circle",{"cx":"11.5","cy":"14.5","r":"2.5","key":"1bq0ko"}],["path",{"d":"M13.3 16.3 15 18","key":"2quom7"}]])
export const FileSearchCorner = ssrIcon('file-search-corner', [["path",{"d":"M11.1 22H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.589 3.588A2.4 2.4 0 0 1 20 8v3.25","key":"uh4ikj"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"m21 22-2.88-2.88","key":"9dd25w"}],["circle",{"cx":"16","cy":"17","r":"3","key":"11br10"}]])
export const FileSignal = ssrIcon('file-signal', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M8 15h.01","key":"a7atzg"}],["path",{"d":"M11.5 13.5a2.5 2.5 0 0 1 0 3","key":"1fccat"}],["path",{"d":"M15 12a5 5 0 0 1 0 6","key":"ps46cm"}]])
export const FileSliders = ssrIcon('file-sliders', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M8 12h8","key":"1wcyev"}],["path",{"d":"M10 11v2","key":"1s651w"}],["path",{"d":"M8 17h8","key":"wh5c61"}],["path",{"d":"M14 16v2","key":"12fp5e"}]])
export const FileSpreadsheet = ssrIcon('file-spreadsheet', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M8 13h2","key":"yr2amv"}],["path",{"d":"M14 13h2","key":"un5t4a"}],["path",{"d":"M8 17h2","key":"2yhykz"}],["path",{"d":"M14 17h2","key":"10kma7"}]])
export const FileStack = ssrIcon('file-stack', [["path",{"d":"M11 21a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1","key":"likhh7"}],["path",{"d":"M16 16a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1","key":"17ky3x"}],["path",{"d":"M21 6a2 2 0 0 0-.586-1.414l-2-2A2 2 0 0 0 17 2h-3a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1z","key":"1hyeo0"}]])
export const FileSymlink = ssrIcon('file-symlink', [["path",{"d":"M4 11V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h7","key":"huwfnr"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"m10 18 3-3-3-3","key":"18f6ys"}]])
export const FileTerminal = ssrIcon('file-terminal', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"m8 16 2-2-2-2","key":"10vzyd"}],["path",{"d":"M12 18h4","key":"1wd2n7"}]])
export const FileText = ssrIcon('file-text', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M10 9H8","key":"b1mrlr"}],["path",{"d":"M16 13H8","key":"t4e002"}],["path",{"d":"M16 17H8","key":"z1uh3a"}]])
export const FileType = ssrIcon('file-type', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M11 18h2","key":"12mj7e"}],["path",{"d":"M12 12v6","key":"3ahymv"}],["path",{"d":"M9 13v-.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 .5.5v.5","key":"qbrxap"}]])
export const FileTypeCorner = ssrIcon('file-type-corner', [["path",{"d":"M12 22h6a2 2 0 0 0 2-2V8a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 14 2H6a2 2 0 0 0-2 2v6","key":"15usau"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M3 16v-1.5a.5.5 0 0 1 .5-.5h7a.5.5 0 0 1 .5.5V16","key":"s1gz5"}],["path",{"d":"M6 22h2","key":"194x9m"}],["path",{"d":"M7 14v8","key":"11ixej"}]])
export const FileUp = ssrIcon('file-up', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M12 12v6","key":"3ahymv"}],["path",{"d":"m15 15-3-3-3 3","key":"15xj92"}]])
export const FileUser = ssrIcon('file-user', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M16 22a4 4 0 0 0-8 0","key":"7a83pg"}],["circle",{"cx":"12","cy":"15","r":"3","key":"g36mzq"}]])
export const FileVideoCamera = ssrIcon('file-video-camera', [["path",{"d":"M4 12V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2","key":"jrl274"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"m10 17.843 3.033-1.755a.64.64 0 0 1 .967.56v4.704a.65.65 0 0 1-.967.56L10 20.157","key":"17aeo9"}],["rect",{"width":"7","height":"6","x":"3","y":"16","rx":"1","key":"s27ndx"}]])
export const FileVolume = ssrIcon('file-volume', [["path",{"d":"M4 11.55V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2h-1.95","key":"44gpjv"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M12 15a5 5 0 0 1 0 6","key":"oxg87a"}],["path",{"d":"M8 14.502a.5.5 0 0 0-.826-.381l-1.893 1.631a1 1 0 0 1-.651.243H3.5a.5.5 0 0 0-.5.501v3.006a.5.5 0 0 0 .5.501h1.129a1 1 0 0 1 .652.243l1.893 1.633a.5.5 0 0 0 .826-.38z","key":"8rtoi1"}]])
export const FileX = ssrIcon('file-x', [["path",{"d":"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z","key":"1oefj6"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"m14.5 12.5-5 5","key":"b62r18"}],["path",{"d":"m9.5 12.5 5 5","key":"1rk7el"}]])
export const FileXCorner = ssrIcon('file-x-corner', [["path",{"d":"M11 22H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v5","key":"1jo35a"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"m15 17 5 5","key":"36xl1x"}],["path",{"d":"m20 17-5 5","key":"vdz27y"}]])
export const Files = ssrIcon('files', [["path",{"d":"M15 2h-4a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V8","key":"14sh0y"}],["path",{"d":"M16.706 2.706A2.4 2.4 0 0 0 15 2v5a1 1 0 0 0 1 1h5a2.4 2.4 0 0 0-.706-1.706z","key":"1970lx"}],["path",{"d":"M5 7a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h8a2 2 0 0 0 1.732-1","key":"l4dndm"}]])
export const Film = ssrIcon('film', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M7 3v18","key":"bbkbws"}],["path",{"d":"M3 7.5h4","key":"zfgn84"}],["path",{"d":"M3 12h18","key":"1i2n21"}],["path",{"d":"M3 16.5h4","key":"1230mu"}],["path",{"d":"M17 3v18","key":"in4fa5"}],["path",{"d":"M17 7.5h4","key":"myr1c1"}],["path",{"d":"M17 16.5h4","key":"go4c1d"}]])
export const Funnel = ssrIcon('funnel', [["path",{"d":"M10 20a1 1 0 0 0 .553.895l2 1A1 1 0 0 0 14 21v-7a2 2 0 0 1 .517-1.341L21.74 4.67A1 1 0 0 0 21 3H3a1 1 0 0 0-.742 1.67l7.225 7.989A2 2 0 0 1 10 14z","key":"sc7q7i"}]])
export const FunnelX = ssrIcon('funnel-x', [["path",{"d":"M12.531 3H3a1 1 0 0 0-.742 1.67l7.225 7.989A2 2 0 0 1 10 14v6a1 1 0 0 0 .553.895l2 1A1 1 0 0 0 14 21v-7a2 2 0 0 1 .517-1.341l.427-.473","key":"ol2ft2"}],["path",{"d":"m16.5 3.5 5 5","key":"15e6fa"}],["path",{"d":"m21.5 3.5-5 5","key":"m0lwru"}]])
export const FingerprintPattern = ssrIcon('fingerprint-pattern', [["path",{"d":"M12 10a2 2 0 0 0-2 2c0 1.02-.1 2.51-.26 4","key":"1nerag"}],["path",{"d":"M14 13.12c0 2.38 0 6.38-1 8.88","key":"o46ks0"}],["path",{"d":"M17.29 21.02c.12-.6.43-2.3.5-3.02","key":"ptglia"}],["path",{"d":"M2 12a10 10 0 0 1 18-6","key":"ydlgp0"}],["path",{"d":"M2 16h.01","key":"1gqxmh"}],["path",{"d":"M21.8 16c.2-2 .131-5.354 0-6","key":"drycrb"}],["path",{"d":"M5 19.5C5.5 18 6 15 6 12a6 6 0 0 1 .34-2","key":"1tidbn"}],["path",{"d":"M8.65 22c.21-.66.45-1.32.57-2","key":"13wd9y"}],["path",{"d":"M9 6.8a6 6 0 0 1 9 5.2v2","key":"1fr1j5"}]])
export const FireExtinguisher = ssrIcon('fire-extinguisher', [["path",{"d":"M15 6.5V3a1 1 0 0 0-1-1h-2a1 1 0 0 0-1 1v3.5","key":"sqyvz"}],["path",{"d":"M9 18h8","key":"i7pszb"}],["path",{"d":"M18 3h-3","key":"7idoqj"}],["path",{"d":"M11 3a6 6 0 0 0-6 6v11","key":"1v5je3"}],["path",{"d":"M5 13h4","key":"svpcxo"}],["path",{"d":"M17 10a4 4 0 0 0-8 0v10a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2Z","key":"vsjego"}]])
export const Fish = ssrIcon('fish', [["path",{"d":"M6.5 12c.94-3.46 4.94-6 8.5-6 3.56 0 6.06 2.54 7 6-.94 3.47-3.44 6-7 6s-7.56-2.53-8.5-6Z","key":"15baut"}],["path",{"d":"M18 12v.5","key":"18hhni"}],["path",{"d":"M16 17.93a9.77 9.77 0 0 1 0-11.86","key":"16dt7o"}],["path",{"d":"M7 10.67C7 8 5.58 5.97 2.73 5.5c-1 1.5-1 5 .23 6.5-1.24 1.5-1.24 5-.23 6.5C5.58 18.03 7 16 7 13.33","key":"l9di03"}],["path",{"d":"M10.46 7.26C10.2 5.88 9.17 4.24 8 3h5.8a2 2 0 0 1 1.98 1.67l.23 1.4","key":"1kjonw"}],["path",{"d":"m16.01 17.93-.23 1.4A2 2 0 0 1 13.8 21H9.5a5.96 5.96 0 0 0 1.49-3.98","key":"1zlm23"}]])
export const FishOff = ssrIcon('fish-off', [["path",{"d":"M18 12.47v.03m0-.5v.47m-.475 5.056A6.744 6.744 0 0 1 15 18c-3.56 0-7.56-2.53-8.5-6 .348-1.28 1.114-2.433 2.121-3.38m3.444-2.088A8.802 8.802 0 0 1 15 6c3.56 0 6.06 2.54 7 6-.309 1.14-.786 2.177-1.413 3.058","key":"1j1hse"}],["path",{"d":"M7 10.67C7 8 5.58 5.97 2.73 5.5c-1 1.5-1 5 .23 6.5-1.24 1.5-1.24 5-.23 6.5C5.58 18.03 7 16 7 13.33m7.48-4.372A9.77 9.77 0 0 1 16 6.07m0 11.86a9.77 9.77 0 0 1-1.728-3.618","key":"1q46z8"}],["path",{"d":"m16.01 17.93-.23 1.4A2 2 0 0 1 13.8 21H9.5a5.96 5.96 0 0 0 1.49-3.98M8.53 3h5.27a2 2 0 0 1 1.98 1.67l.23 1.4M2 2l20 20","key":"1407gh"}]])
export const FishSymbol = ssrIcon('fish-symbol', [["path",{"d":"M2 16s9-15 20-4C11 23 2 8 2 8","key":"h4oh4o"}]])
export const FishingHook = ssrIcon('fishing-hook', [["path",{"d":"m17.586 11.414-5.93 5.93a1 1 0 0 1-8-8l3.137-3.137a.707.707 0 0 1 1.207.5V10","key":"157y8s"}],["path",{"d":"M20.414 8.586 22 7","key":"5g2s34"}],["circle",{"cx":"19","cy":"10","r":"2","key":"7363ft"}]])
export const FishingRod = ssrIcon('fishing-rod', [["path",{"d":"M4 11h1","key":"13eipc"}],["path",{"d":"M8 15a2 2 0 0 1-4 0V3a1 1 0 0 1 1-1h.5C14 2 20 9 20 18v4","key":"1hs3im"}],["circle",{"cx":"18","cy":"18","r":"2","key":"1emm8v"}]])
export const Flag = ssrIcon('flag', [["path",{"d":"M4 22V4a1 1 0 0 1 .4-.8A6 6 0 0 1 8 2c3 0 5 2 7.333 2q2 0 3.067-.8A1 1 0 0 1 20 4v10a1 1 0 0 1-.4.8A6 6 0 0 1 16 16c-3 0-5-2-8-2a6 6 0 0 0-4 1.528","key":"1jaruq"}]])
export const FlagOff = ssrIcon('flag-off', [["path",{"d":"M16 16c-3 0-5-2-8-2a6 6 0 0 0-4 1.528","key":"1q158e"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M4 22V4","key":"1plyxx"}],["path",{"d":"M7.656 2H8c3 0 5 2 7.333 2q2 0 3.067-.8A1 1 0 0 1 20 4v10.347","key":"xj1b71"}]])
export const FlagTriangleLeft = ssrIcon('flag-triangle-left', [["path",{"d":"M18 22V2.8a.8.8 0 0 0-1.17-.71L5.45 7.78a.8.8 0 0 0 0 1.44L18 15.5","key":"rbbtmw"}]])
export const FlagTriangleRight = ssrIcon('flag-triangle-right', [["path",{"d":"M6 22V2.8a.8.8 0 0 1 1.17-.71l11.38 5.69a.8.8 0 0 1 0 1.44L6 15.5","key":"kfjsu0"}]])
export const Flame = ssrIcon('flame', [["path",{"d":"M12 3q1 4 4 6.5t3 5.5a1 1 0 0 1-14 0 5 5 0 0 1 1-3 1 1 0 0 0 5 0c0-2-1.5-3-1.5-5q0-2 2.5-4","key":"1slcih"}]])
export const FlameKindling = ssrIcon('flame-kindling', [["path",{"d":"M12 2c1 3 2.5 3.5 3.5 4.5A5 5 0 0 1 17 10a5 5 0 1 1-10 0c0-.3 0-.6.1-.9a2 2 0 1 0 3.3-2C8 4.5 11 2 12 2Z","key":"1ir223"}],["path",{"d":"m5 22 14-4","key":"1brv4h"}],["path",{"d":"m5 18 14 4","key":"lgyyje"}]])
export const Flashlight = ssrIcon('flashlight', [["path",{"d":"M12 13v1","key":"176q98"}],["path",{"d":"M17 2a1 1 0 0 1 1 1v4a3 3 0 0 1-.6 1.8l-.6.8A4 4 0 0 0 16 12v8a2 2 0 0 1-2 2H10a2 2 0 0 1-2-2v-8a4 4 0 0 0-.8-2.4l-.6-.8A3 3 0 0 1 6 7V3a1 1 0 0 1 1-1z","key":"17vh7j"}],["path",{"d":"M6 6h12","key":"n6hhss"}]])
export const FlashlightOff = ssrIcon('flashlight-off', [["path",{"d":"M11.652 6H18","key":"voqkpr"}],["path",{"d":"M12 13v1","key":"176q98"}],["path",{"d":"M16 16v4a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-8a4 4 0 0 0-.8-2.4l-.6-.8A3 3 0 0 1 6 7V6","key":"dzyf92"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M7.649 2H17a1 1 0 0 1 1 1v4a3 3 0 0 1-.6 1.8l-.6.8a4 4 0 0 0-.55 1.007","key":"1hvcfn"}]])
export const FlaskConical = ssrIcon('flask-conical', [["path",{"d":"M14 2v6a2 2 0 0 0 .245.96l5.51 10.08A2 2 0 0 1 18 22H6a2 2 0 0 1-1.755-2.96l5.51-10.08A2 2 0 0 0 10 8V2","key":"18mbvz"}],["path",{"d":"M6.453 15h11.094","key":"3shlmq"}],["path",{"d":"M8.5 2h7","key":"csnxdl"}]])
export const FlaskConicalOff = ssrIcon('flask-conical-off', [["path",{"d":"M10 2v2.343","key":"15t272"}],["path",{"d":"M14 2v6.343","key":"sxr80q"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M20 20a2 2 0 0 1-2 2H6a2 2 0 0 1-1.755-2.96l5.227-9.563","key":"k0duyd"}],["path",{"d":"M6.453 15H15","key":"1f0z33"}],["path",{"d":"M8.5 2h7","key":"csnxdl"}]])
export const FlaskRound = ssrIcon('flask-round', [["path",{"d":"M10 2v6.292a7 7 0 1 0 4 0V2","key":"1s42pc"}],["path",{"d":"M5 15h14","key":"m0yey3"}],["path",{"d":"M8.5 2h7","key":"csnxdl"}]])
export const SquareCenterlineDashedHorizontal = ssrIcon('square-centerline-dashed-horizontal', [["path",{"d":"M8 3H5a2 2 0 0 0-2 2v14c0 1.1.9 2 2 2h3","key":"1i73f7"}],["path",{"d":"M16 3h3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-3","key":"saxlbk"}],["path",{"d":"M12 20v2","key":"1lh1kg"}],["path",{"d":"M12 14v2","key":"8jcxud"}],["path",{"d":"M12 8v2","key":"1woqiv"}],["path",{"d":"M12 2v2","key":"tus03m"}]])
export const FlipHorizontal2 = ssrIcon('flip-horizontal-2', [["path",{"d":"m3 7 5 5-5 5V7","key":"couhi7"}],["path",{"d":"m21 7-5 5 5 5V7","key":"6ouia7"}],["path",{"d":"M12 20v2","key":"1lh1kg"}],["path",{"d":"M12 14v2","key":"8jcxud"}],["path",{"d":"M12 8v2","key":"1woqiv"}],["path",{"d":"M12 2v2","key":"tus03m"}]])
export const SquareCenterlineDashedVertical = ssrIcon('square-centerline-dashed-vertical', [["path",{"d":"M21 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v3","key":"14bfxa"}],["path",{"d":"M21 16v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-3","key":"14rx03"}],["path",{"d":"M4 12H2","key":"rhcxmi"}],["path",{"d":"M10 12H8","key":"s88cx1"}],["path",{"d":"M16 12h-2","key":"10asgb"}],["path",{"d":"M22 12h-2","key":"14jgyd"}]])
export const FlipVertical2 = ssrIcon('flip-vertical-2', [["path",{"d":"m17 3-5 5-5-5h10","key":"1ftt6x"}],["path",{"d":"m17 21-5-5-5 5h10","key":"1m0wmu"}],["path",{"d":"M4 12H2","key":"rhcxmi"}],["path",{"d":"M10 12H8","key":"s88cx1"}],["path",{"d":"M16 12h-2","key":"10asgb"}],["path",{"d":"M22 12h-2","key":"14jgyd"}]])
export const Flower = ssrIcon('flower', [["circle",{"cx":"12","cy":"12","r":"3","key":"1v7zrd"}],["path",{"d":"M12 16.5A4.5 4.5 0 1 1 7.5 12 4.5 4.5 0 1 1 12 7.5a4.5 4.5 0 1 1 4.5 4.5 4.5 4.5 0 1 1-4.5 4.5","key":"14wa3c"}],["path",{"d":"M12 7.5V9","key":"1oy5b0"}],["path",{"d":"M7.5 12H9","key":"eltsq1"}],["path",{"d":"M16.5 12H15","key":"vk5kw4"}],["path",{"d":"M12 16.5V15","key":"k7eayi"}],["path",{"d":"m8 8 1.88 1.88","key":"nxy4qf"}],["path",{"d":"M14.12 9.88 16 8","key":"1lst6k"}],["path",{"d":"m8 16 1.88-1.88","key":"h2eex1"}],["path",{"d":"M14.12 14.12 16 16","key":"uqkrx3"}]])
export const Flower2 = ssrIcon('flower-2', [["path",{"d":"M12 5a3 3 0 1 1 3 3m-3-3a3 3 0 1 0-3 3m3-3v1M9 8a3 3 0 1 0 3 3M9 8h1m5 0a3 3 0 1 1-3 3m3-3h-1m-2 3v-1","key":"3pnvol"}],["circle",{"cx":"12","cy":"8","r":"2","key":"1822b1"}],["path",{"d":"M12 10v12","key":"6ubwww"}],["path",{"d":"M12 22c4.2 0 7-1.667 7-5-4.2 0-7 1.667-7 5Z","key":"9hd38g"}],["path",{"d":"M12 22c-4.2 0-7-1.667-7-5 4.2 0 7 1.667 7 5Z","key":"ufn41s"}]])
export const Focus = ssrIcon('focus', [["circle",{"cx":"12","cy":"12","r":"3","key":"1v7zrd"}],["path",{"d":"M3 7V5a2 2 0 0 1 2-2h2","key":"aa7l1z"}],["path",{"d":"M17 3h2a2 2 0 0 1 2 2v2","key":"4qcy5o"}],["path",{"d":"M21 17v2a2 2 0 0 1-2 2h-2","key":"6vwrx8"}],["path",{"d":"M7 21H5a2 2 0 0 1-2-2v-2","key":"ioqczr"}]])
export const FoldHorizontal = ssrIcon('fold-horizontal', [["path",{"d":"M2 12h6","key":"1wqiqv"}],["path",{"d":"M22 12h-6","key":"1eg9hc"}],["path",{"d":"M12 2v2","key":"tus03m"}],["path",{"d":"M12 8v2","key":"1woqiv"}],["path",{"d":"M12 14v2","key":"8jcxud"}],["path",{"d":"M12 20v2","key":"1lh1kg"}],["path",{"d":"m19 9-3 3 3 3","key":"12ol22"}],["path",{"d":"m5 15 3-3-3-3","key":"1kdhjc"}]])
export const FoldVertical = ssrIcon('fold-vertical', [["path",{"d":"M12 22v-6","key":"6o8u61"}],["path",{"d":"M12 8V2","key":"1wkif3"}],["path",{"d":"M4 12H2","key":"rhcxmi"}],["path",{"d":"M10 12H8","key":"s88cx1"}],["path",{"d":"M16 12h-2","key":"10asgb"}],["path",{"d":"M22 12h-2","key":"14jgyd"}],["path",{"d":"m15 19-3-3-3 3","key":"e37ymu"}],["path",{"d":"m15 5-3 3-3-3","key":"19d6lf"}]])
export const Folder = ssrIcon('folder', [["path",{"d":"M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z","key":"1kt360"}]])
export const FolderArchive = ssrIcon('folder-archive', [["circle",{"cx":"15","cy":"19","r":"2","key":"u2pros"}],["path",{"d":"M20.9 19.8A2 2 0 0 0 22 18V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h5.1","key":"1jj40k"}],["path",{"d":"M15 11v-1","key":"cntcp"}],["path",{"d":"M15 17v-2","key":"1279jj"}]])
export const FolderBookmark = ssrIcon('folder-bookmark', [["path",{"d":"M12 6v8l3-3 3 3V6","key":"11pvqx"}],["path",{"d":"M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2z","key":"1u1bxd"}]])
export const FolderCheck = ssrIcon('folder-check', [["path",{"d":"M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z","key":"1kt360"}],["path",{"d":"m9 13 2 2 4-4","key":"6343dt"}]])
export const FolderClock = ssrIcon('folder-clock', [["path",{"d":"M16 14v2.2l1.6 1","key":"fo4ql5"}],["path",{"d":"M7 20H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H20a2 2 0 0 1 2 2","key":"1urifu"}],["circle",{"cx":"16","cy":"16","r":"6","key":"qoo3c4"}]])
export const FolderClosed = ssrIcon('folder-closed', [["path",{"d":"M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z","key":"1kt360"}],["path",{"d":"M2 10h20","key":"1ir3d8"}]])
export const FolderCode = ssrIcon('folder-code', [["path",{"d":"M10 10.5 8 13l2 2.5","key":"m4t9c1"}],["path",{"d":"m14 10.5 2 2.5-2 2.5","key":"14w2eb"}],["path",{"d":"M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2z","key":"1u1bxd"}]])
export const FolderCog = ssrIcon('folder-cog', [["path",{"d":"M10.3 20H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.98a2 2 0 0 1 1.69.9l.66 1.2A2 2 0 0 0 12 6h8a2 2 0 0 1 2 2v3.3","key":"128dxu"}],["path",{"d":"m14.305 19.53.923-.382","key":"3m78fa"}],["path",{"d":"m15.228 16.852-.923-.383","key":"npixar"}],["path",{"d":"m16.852 15.228-.383-.923","key":"5xggr7"}],["path",{"d":"m16.852 20.772-.383.924","key":"dpfhf9"}],["path",{"d":"m19.148 15.228.383-.923","key":"1reyyz"}],["path",{"d":"m19.53 21.696-.382-.924","key":"1goivc"}],["path",{"d":"m20.772 16.852.924-.383","key":"htqkph"}],["path",{"d":"m20.772 19.148.924.383","key":"9w9pjp"}],["circle",{"cx":"18","cy":"18","r":"3","key":"1xkwt0"}]])
export const FolderDot = ssrIcon('folder-dot', [["path",{"d":"M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z","key":"1fr9dc"}],["circle",{"cx":"12","cy":"13","r":"1","key":"49l61u"}]])
export const FolderDown = ssrIcon('folder-down', [["path",{"d":"M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z","key":"1kt360"}],["path",{"d":"M12 10v6","key":"1bos4e"}],["path",{"d":"m15 13-3 3-3-3","key":"6j2sf0"}]])
export const FolderPen = ssrIcon('folder-pen', [["path",{"d":"M2 11.5V5a2 2 0 0 1 2-2h3.9c.7 0 1.3.3 1.7.9l.8 1.2c.4.6 1 .9 1.7.9H20a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-9.5","key":"a8xqs0"}],["path",{"d":"M11.378 13.626a1 1 0 1 0-3.004-3.004l-5.01 5.012a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z","key":"1saktj"}]])
export const FolderGit = ssrIcon('folder-git', [["circle",{"cx":"12","cy":"13","r":"2","key":"1c1ljs"}],["path",{"d":"M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z","key":"1kt360"}],["path",{"d":"M14 13h3","key":"1dgedf"}],["path",{"d":"M7 13h3","key":"1pygq7"}]])
export const FolderGit2 = ssrIcon('folder-git-2', [["path",{"d":"M18 19a5 5 0 0 1-5-5v8","key":"sz5oeg"}],["path",{"d":"M9 20H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H20a2 2 0 0 1 2 2v5","key":"1w6njk"}],["circle",{"cx":"13","cy":"12","r":"2","key":"1j92g6"}],["circle",{"cx":"20","cy":"19","r":"2","key":"1obnsp"}]])
export const FolderHeart = ssrIcon('folder-heart', [["path",{"d":"M10.638 20H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H20a2 2 0 0 1 2 2v3.417","key":"10r6g4"}],["path",{"d":"M14.62 18.8A2.25 2.25 0 1 1 18 15.836a2.25 2.25 0 1 1 3.38 2.966l-2.626 2.856a.998.998 0 0 1-1.507 0z","key":"15cy7q"}]])
export const FolderInput = ssrIcon('folder-input', [["path",{"d":"M2 9V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H20a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-1","key":"fm4g5t"}],["path",{"d":"M2 13h10","key":"pgb2dq"}],["path",{"d":"m9 16 3-3-3-3","key":"6m91ic"}]])
export const FolderKanban = ssrIcon('folder-kanban', [["path",{"d":"M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z","key":"1fr9dc"}],["path",{"d":"M8 10v4","key":"tgpxqk"}],["path",{"d":"M12 10v2","key":"hh53o1"}],["path",{"d":"M16 10v6","key":"1d6xys"}]])
export const FolderKey = ssrIcon('folder-key', [["path",{"d":"M13 20H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H20a2 2 0 0 1 2 2v1.36","key":"1shsnm"}],["path",{"d":"M19 12v6","key":"kflna4"}],["path",{"d":"M19 14h2","key":"wp2qbk"}],["circle",{"cx":"19","cy":"20","r":"2","key":"1jfyz6"}]])
export const FolderLock = ssrIcon('folder-lock', [["rect",{"width":"8","height":"5","x":"14","y":"17","rx":"1","key":"19aais"}],["path",{"d":"M10 20H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H20a2 2 0 0 1 2 2v2.5","key":"1w6v7t"}],["path",{"d":"M20 17v-2a2 2 0 1 0-4 0v2","key":"pwaxnr"}]])
export const FolderMinus = ssrIcon('folder-minus', [["path",{"d":"M9 13h6","key":"1uhe8q"}],["path",{"d":"M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z","key":"1kt360"}]])
export const FolderOpen = ssrIcon('folder-open', [["path",{"d":"m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2","key":"usdka0"}]])
export const FolderOpenDot = ssrIcon('folder-open-dot', [["path",{"d":"m6 14 1.45-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.55 6a2 2 0 0 1-1.94 1.5H4a2 2 0 0 1-2-2V5c0-1.1.9-2 2-2h3.93a2 2 0 0 1 1.66.9l.82 1.2a2 2 0 0 0 1.66.9H18a2 2 0 0 1 2 2v2","key":"1nmvlm"}],["circle",{"cx":"14","cy":"15","r":"1","key":"1gm4qj"}]])
export const FolderOutput = ssrIcon('folder-output', [["path",{"d":"M2 7.5V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H20a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-1.5","key":"1yk7aj"}],["path",{"d":"M2 13h10","key":"pgb2dq"}],["path",{"d":"m5 10-3 3 3 3","key":"1r8ie0"}]])
export const FolderPlus = ssrIcon('folder-plus', [["path",{"d":"M12 10v6","key":"1bos4e"}],["path",{"d":"M9 13h6","key":"1uhe8q"}],["path",{"d":"M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z","key":"1kt360"}]])
export const FolderRoot = ssrIcon('folder-root', [["path",{"d":"M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z","key":"1fr9dc"}],["circle",{"cx":"12","cy":"13","r":"2","key":"1c1ljs"}],["path",{"d":"M12 15v5","key":"11xva1"}]])
export const FolderSearch = ssrIcon('folder-search', [["path",{"d":"M10.7 20H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H20a2 2 0 0 1 2 2v4.1","key":"1bw5m7"}],["path",{"d":"m21 21-1.9-1.9","key":"1g2n9r"}],["circle",{"cx":"17","cy":"17","r":"3","key":"18b49y"}]])
export const FolderSearch2 = ssrIcon('folder-search-2', [["circle",{"cx":"11.5","cy":"12.5","r":"2.5","key":"1ea5ju"}],["path",{"d":"M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z","key":"1kt360"}],["path",{"d":"M13.3 14.3 15 16","key":"1y4v1n"}]])
export const FolderSymlink = ssrIcon('folder-symlink', [["path",{"d":"M2 9.35V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H20a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h7","key":"y8kt7d"}],["path",{"d":"m8 16 3-3-3-3","key":"rlqrt1"}]])
export const FolderSync = ssrIcon('folder-sync', [["path",{"d":"M9 20H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H20a2 2 0 0 1 2 2v.5","key":"1dkoa9"}],["path",{"d":"M12 10v4h4","key":"1czhmt"}],["path",{"d":"m12 14 1.535-1.605a5 5 0 0 1 8 1.5","key":"lvuxfi"}],["path",{"d":"M22 22v-4h-4","key":"1ewp4q"}],["path",{"d":"m22 18-1.535 1.605a5 5 0 0 1-8-1.5","key":"14ync0"}]])
export const FolderTree = ssrIcon('folder-tree', [["path",{"d":"M20 10a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1h-2.5a1 1 0 0 1-.8-.4l-.9-1.2A1 1 0 0 0 15 3h-2a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1Z","key":"hod4my"}],["path",{"d":"M20 21a1 1 0 0 0 1-1v-3a1 1 0 0 0-1-1h-2.9a1 1 0 0 1-.88-.55l-.42-.85a1 1 0 0 0-.92-.6H13a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1Z","key":"w4yl2u"}],["path",{"d":"M3 5a2 2 0 0 0 2 2h3","key":"f2jnh7"}],["path",{"d":"M3 3v13a2 2 0 0 0 2 2h3","key":"k8epm1"}]])
export const FolderUp = ssrIcon('folder-up', [["path",{"d":"M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z","key":"1kt360"}],["path",{"d":"M12 10v6","key":"1bos4e"}],["path",{"d":"m9 13 3-3 3 3","key":"1pxg3c"}]])
export const FolderX = ssrIcon('folder-x', [["path",{"d":"M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z","key":"1kt360"}],["path",{"d":"m9.5 10.5 5 5","key":"ra9qjz"}],["path",{"d":"m14.5 10.5-5 5","key":"l2rkpq"}]])
export const Folders = ssrIcon('folders', [["path",{"d":"M20 5a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h2.5a1.5 1.5 0 0 1 1.2.6l.6.8a1.5 1.5 0 0 0 1.2.6z","key":"a4852j"}],["path",{"d":"M3 8.268a2 2 0 0 0-1 1.738V19a2 2 0 0 0 2 2h11a2 2 0 0 0 1.732-1","key":"yxbcw3"}]])
export const Footprints = ssrIcon('footprints', [["path",{"d":"M4 16v-2.38C4 11.5 2.97 10.5 3 8c.03-2.72 1.49-6 4.5-6C9.37 2 10 3.8 10 5.5c0 3.11-2 5.66-2 8.68V16a2 2 0 1 1-4 0Z","key":"1dudjm"}],["path",{"d":"M20 20v-2.38c0-2.12 1.03-3.12 1-5.62-.03-2.72-1.49-6-4.5-6C14.63 6 14 7.8 14 9.5c0 3.11 2 5.66 2 8.68V20a2 2 0 1 0 4 0Z","key":"l2t8xc"}],["path",{"d":"M16 17h4","key":"1dejxt"}],["path",{"d":"M4 13h4","key":"1bwh8b"}]])
export const Utensils = ssrIcon('utensils', [["path",{"d":"M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2","key":"cjf0a3"}],["path",{"d":"M7 2v20","key":"1473qp"}],["path",{"d":"M21 15V2a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7","key":"j28e5"}]])
export const UtensilsCrossed = ssrIcon('utensils-crossed', [["path",{"d":"m16 2-2.3 2.3a3 3 0 0 0 0 4.2l1.8 1.8a3 3 0 0 0 4.2 0L22 8","key":"n7qcjb"}],["path",{"d":"M15 15 3.3 3.3a4.2 4.2 0 0 0 0 6l7.3 7.3c.7.7 2 .7 2.8 0L15 15Zm0 0 7 7","key":"d0u48b"}],["path",{"d":"m2.1 21.8 6.4-6.3","key":"yn04lh"}],["path",{"d":"m19 5-7 7","key":"194lzd"}]])
export const Forklift = ssrIcon('forklift', [["path",{"d":"M12 12H5a2 2 0 0 0-2 2v5","key":"7zsz91"}],["path",{"d":"M15 19h7","key":"1askl3"}],["path",{"d":"M16 19V2","key":"1gf9nk"}],["path",{"d":"M6 12V7a2 2 0 0 1 2-2h2.172a2 2 0 0 1 1.414.586l3.828 3.828A2 2 0 0 1 16 10.828","key":"enx9tf"}],["path",{"d":"M7 19h4","key":"fumhkk"}],["circle",{"cx":"13","cy":"19","r":"2","key":"wjnkru"}],["circle",{"cx":"5","cy":"19","r":"2","key":"v8kfzx"}]])
export const Form = ssrIcon('form', [["path",{"d":"M4 14h6","key":"77gv2w"}],["path",{"d":"M4 2h10","key":"a2b314"}],["rect",{"x":"4","y":"18","width":"16","height":"4","rx":"1","key":"sybzq6"}],["rect",{"x":"4","y":"6","width":"16","height":"4","rx":"1","key":"1osc9e"}]])
export const RectangleEllipsis = ssrIcon('rectangle-ellipsis', [["rect",{"width":"20","height":"12","x":"2","y":"6","rx":"2","key":"9lu3g6"}],["path",{"d":"M12 12h.01","key":"1mp3jc"}],["path",{"d":"M17 12h.01","key":"1m0b6t"}],["path",{"d":"M7 12h.01","key":"eqddd0"}]])
export const Forward = ssrIcon('forward', [["path",{"d":"m15 17 5-5-5-5","key":"nf172w"}],["path",{"d":"M4 18v-2a4 4 0 0 1 4-4h12","key":"jmiej9"}]])
export const Frame = ssrIcon('frame', [["line",{"x1":"22","x2":"2","y1":"6","y2":"6","key":"15w7dq"}],["line",{"x1":"22","x2":"2","y1":"18","y2":"18","key":"1ip48p"}],["line",{"x1":"6","x2":"6","y1":"2","y2":"22","key":"a2lnyx"}],["line",{"x1":"18","x2":"18","y1":"2","y2":"22","key":"8vb6jd"}]])
export const Fuel = ssrIcon('fuel', [["path",{"d":"M14 13h2a2 2 0 0 1 2 2v2a2 2 0 0 0 4 0v-6.998a2 2 0 0 0-.59-1.42L18 5","key":"1wtuz0"}],["path",{"d":"M14 21V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v16","key":"e09ifn"}],["path",{"d":"M2 21h13","key":"1x0fut"}],["path",{"d":"M3 9h11","key":"1p7c0w"}]])
export const Fullscreen = ssrIcon('fullscreen', [["path",{"d":"M3 7V5a2 2 0 0 1 2-2h2","key":"aa7l1z"}],["path",{"d":"M17 3h2a2 2 0 0 1 2 2v2","key":"4qcy5o"}],["path",{"d":"M21 17v2a2 2 0 0 1-2 2h-2","key":"6vwrx8"}],["path",{"d":"M7 21H5a2 2 0 0 1-2-2v-2","key":"ioqczr"}],["rect",{"width":"10","height":"8","x":"7","y":"8","rx":"1","key":"vys8me"}]])
export const SquareFunction = ssrIcon('square-function', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","ry":"2","key":"1m3agn"}],["path",{"d":"M9 17c2 0 2.8-1 2.8-2.8V10c0-2 1-3.3 3.2-3","key":"m1af9g"}],["path",{"d":"M9 11.2h5.7","key":"3zgcl2"}]])
export const FunnelPlus = ssrIcon('funnel-plus', [["path",{"d":"M13.354 3H3a1 1 0 0 0-.742 1.67l7.225 7.989A2 2 0 0 1 10 14v6a1 1 0 0 0 .553.895l2 1A1 1 0 0 0 14 21v-7a2 2 0 0 1 .517-1.341l1.218-1.348","key":"8mvsmf"}],["path",{"d":"M16 6h6","key":"1dogtp"}],["path",{"d":"M19 3v6","key":"1ytpjt"}]])
export const Galaxy = ssrIcon('galaxy', [["path",{"d":"M16.005 15.108a5.041 6.52 28.25 00-8.008-6.217 5.041 6.52 28.25 008.008 6.217A11.884 7.288-60.76 014.029 7.001","key":"1w3uyc"}],["path",{"d":"M17 21h.01","key":"1yigvh"}],["path",{"d":"M7 3h.01","key":"we4yfo"}],["path",{"d":"M7.997 8.891a11.885 7.288-60.756 0111.977 8.107","key":"mpf5op"}],["circle",{"cx":"12","cy":"12","r":"1","fill":"currentColor","key":"1t76vf"}]])
export const GalleryHorizontal = ssrIcon('gallery-horizontal', [["path",{"d":"M2 3v18","key":"pzttux"}],["rect",{"width":"12","height":"18","x":"6","y":"3","rx":"2","key":"btr8bg"}],["path",{"d":"M22 3v18","key":"6jf3v"}]])
export const GalleryHorizontalEnd = ssrIcon('gallery-horizontal-end', [["path",{"d":"M2 7v10","key":"a2pl2d"}],["path",{"d":"M6 5v14","key":"1kq3d7"}],["rect",{"width":"12","height":"18","x":"10","y":"3","rx":"2","key":"13i7bc"}]])
export const GalleryThumbnails = ssrIcon('gallery-thumbnails', [["rect",{"width":"18","height":"14","x":"3","y":"3","rx":"2","key":"74y24f"}],["path",{"d":"M4 21h1","key":"16zlid"}],["path",{"d":"M9 21h1","key":"15o7lz"}],["path",{"d":"M14 21h1","key":"v9vybs"}],["path",{"d":"M19 21h1","key":"edywat"}]])
export const GalleryVertical = ssrIcon('gallery-vertical', [["path",{"d":"M3 2h18","key":"15qxfx"}],["rect",{"width":"18","height":"12","x":"3","y":"6","rx":"2","key":"1439r6"}],["path",{"d":"M3 22h18","key":"8prr45"}]])
export const GalleryVerticalEnd = ssrIcon('gallery-vertical-end', [["path",{"d":"M7 2h10","key":"nczekb"}],["path",{"d":"M5 6h14","key":"u2x4p"}],["rect",{"width":"18","height":"12","x":"3","y":"10","rx":"2","key":"l0tzu3"}]])
export const Gamepad = ssrIcon('gamepad', [["line",{"x1":"6","x2":"10","y1":"12","y2":"12","key":"161bw2"}],["line",{"x1":"8","x2":"8","y1":"10","y2":"14","key":"1i6ji0"}],["line",{"x1":"15","x2":"15.01","y1":"13","y2":"13","key":"dqpgro"}],["line",{"x1":"18","x2":"18.01","y1":"11","y2":"11","key":"meh2c"}],["rect",{"width":"20","height":"12","x":"2","y":"6","rx":"2","key":"9lu3g6"}]])
export const Gamepad2 = ssrIcon('gamepad-2', [["line",{"x1":"6","x2":"10","y1":"11","y2":"11","key":"1gktln"}],["line",{"x1":"8","x2":"8","y1":"9","y2":"13","key":"qnk9ow"}],["line",{"x1":"15","x2":"15.01","y1":"12","y2":"12","key":"krot7o"}],["line",{"x1":"18","x2":"18.01","y1":"10","y2":"10","key":"1lcuu1"}],["path",{"d":"M17.32 5H6.68a4 4 0 0 0-3.978 3.59c-.006.052-.01.101-.017.152C2.604 9.416 2 14.456 2 16a3 3 0 0 0 3 3c1 0 1.5-.5 2-1l1.414-1.414A2 2 0 0 1 9.828 16h4.344a2 2 0 0 1 1.414.586L17 18c.5.5 1 1 2 1a3 3 0 0 0 3-3c0-1.545-.604-6.584-.685-7.258-.007-.05-.011-.1-.017-.151A4 4 0 0 0 17.32 5z","key":"mfqc10"}]])
export const GamepadDirectional = ssrIcon('gamepad-directional', [["path",{"d":"M11.146 15.854a1.207 1.207 0 0 1 1.708 0l1.56 1.56A2 2 0 0 1 15 18.828V21a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1v-2.172a2 2 0 0 1 .586-1.414z","key":"1re2og"}],["path",{"d":"M18.828 15a2 2 0 0 1-1.414-.586l-1.56-1.56a1.207 1.207 0 0 1 0-1.708l1.56-1.56A2 2 0 0 1 18.828 9H21a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1z","key":"1pchrj"}],["path",{"d":"M6.586 14.414A2 2 0 0 1 5.172 15H3a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1h2.172a2 2 0 0 1 1.414.586l1.56 1.56a1.207 1.207 0 0 1 0 1.708z","key":"16mt4c"}],["path",{"d":"M9 3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2.172a2 2 0 0 1-.586 1.414l-1.56 1.56a1.207 1.207 0 0 1-1.708 0l-1.56-1.56A2 2 0 0 1 9 5.172z","key":"19ox6c"}]])
export const SquareChartGantt = ssrIcon('square-chart-gantt', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M9 8h7","key":"kbo1nt"}],["path",{"d":"M8 12h6","key":"ikassy"}],["path",{"d":"M11 16h5","key":"oq65wt"}]])
export const Gauge = ssrIcon('gauge', [["path",{"d":"m12 14 4-4","key":"9kzdfg"}],["path",{"d":"M3.34 19a10 10 0 1 1 17.32 0","key":"19p75a"}]])
export const Gavel = ssrIcon('gavel', [["path",{"d":"m14 13-8.381 8.38a1 1 0 0 1-3.001-3l8.384-8.381","key":"pgg06f"}],["path",{"d":"m16 16 6-6","key":"vzrcl6"}],["path",{"d":"m21.5 10.5-8-8","key":"a17d9x"}],["path",{"d":"m8 8 6-6","key":"18bi4p"}],["path",{"d":"m8.5 7.5 8 8","key":"1oyaui"}]])
export const Gem = ssrIcon('gem', [["path",{"d":"M10.5 3 8 9l4 13 4-13-2.5-6","key":"b3dvk1"}],["path",{"d":"M17 3a2 2 0 0 1 1.6.8l3 4a2 2 0 0 1 .013 2.382l-7.99 10.986a2 2 0 0 1-3.247 0l-7.99-10.986A2 2 0 0 1 2.4 7.8l2.998-3.997A2 2 0 0 1 7 3z","key":"7w4byz"}],["path",{"d":"M2 9h20","key":"16fsjt"}]])
export const GeorgianLari = ssrIcon('georgian-lari', [["path",{"d":"M11.5 21a7.5 7.5 0 1 1 7.35-9","key":"1gyj8k"}],["path",{"d":"M13 12V3","key":"18om2a"}],["path",{"d":"M4 21h16","key":"1h09gz"}],["path",{"d":"M9 12V3","key":"geutu0"}]])
export const Ghost = ssrIcon('ghost', [["path",{"d":"M15 10v1","key":"oj8wfp"}],["path",{"d":"M7.528 20.472a1.6 1.6 0 012.277 0l1.057 1.056a1.6 1.6 0 002.276 0l1.057-1.056a1.6 1.6 0 012.277 0l1.114 1.114a1.4 1.4 0 002.414-1V10a8 8 0 00-16 0v10.586a1.4 1.4 0 002.414 1z","key":"13lou3"}],["path",{"d":"M9 10v1","key":"1e14fa"}]])
export const Gift = ssrIcon('gift', [["path",{"d":"M12 7v14","key":"1akyts"}],["path",{"d":"M20 11v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8","key":"1sqzm4"}],["path",{"d":"M7.5 7a1 1 0 0 1 0-5A4.8 8 0 0 1 12 7a4.8 8 0 0 1 4.5-5 1 1 0 0 1 0 5","key":"kc0143"}],["rect",{"x":"3","y":"7","width":"18","height":"4","rx":"1","key":"1hberx"}]])
export const GitBranch = ssrIcon('git-branch', [["path",{"d":"M15 6a9 9 0 0 0-9 9V3","key":"1cii5b"}],["circle",{"cx":"18","cy":"6","r":"3","key":"1h7g24"}],["circle",{"cx":"6","cy":"18","r":"3","key":"fqmcym"}]])
export const GitBranchMinus = ssrIcon('git-branch-minus', [["path",{"d":"M15 6a9 9 0 0 0-9 9V3","key":"1cii5b"}],["path",{"d":"M21 18h-6","key":"139f0c"}],["circle",{"cx":"18","cy":"6","r":"3","key":"1h7g24"}],["circle",{"cx":"6","cy":"18","r":"3","key":"fqmcym"}]])
export const GitBranchPlus = ssrIcon('git-branch-plus', [["path",{"d":"M6 3v12","key":"qpgusn"}],["path",{"d":"M18 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6z","key":"1d02ji"}],["path",{"d":"M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6z","key":"chk6ph"}],["path",{"d":"M15 6a9 9 0 0 0-9 9","key":"or332x"}],["path",{"d":"M18 15v6","key":"9wciyi"}],["path",{"d":"M21 18h-6","key":"139f0c"}]])
export const GitCommitHorizontal = ssrIcon('git-commit-horizontal', [["circle",{"cx":"12","cy":"12","r":"3","key":"1v7zrd"}],["line",{"x1":"3","x2":"9","y1":"12","y2":"12","key":"1dyftd"}],["line",{"x1":"15","x2":"21","y1":"12","y2":"12","key":"oup4p8"}]])
export const GitCommitVertical = ssrIcon('git-commit-vertical', [["path",{"d":"M12 3v6","key":"1holv5"}],["circle",{"cx":"12","cy":"12","r":"3","key":"1v7zrd"}],["path",{"d":"M12 15v6","key":"a9ows0"}]])
export const GitCompare = ssrIcon('git-compare', [["circle",{"cx":"18","cy":"18","r":"3","key":"1xkwt0"}],["circle",{"cx":"6","cy":"6","r":"3","key":"1lh9wr"}],["path",{"d":"M13 6h3a2 2 0 0 1 2 2v7","key":"1yeb86"}],["path",{"d":"M11 18H8a2 2 0 0 1-2-2V9","key":"19pyzm"}]])
export const GitCompareArrows = ssrIcon('git-compare-arrows', [["circle",{"cx":"5","cy":"6","r":"3","key":"1qnov2"}],["path",{"d":"M12 6h5a2 2 0 0 1 2 2v7","key":"1yj91y"}],["path",{"d":"m15 9-3-3 3-3","key":"1lwv8l"}],["circle",{"cx":"19","cy":"18","r":"3","key":"1qljk2"}],["path",{"d":"M12 18H7a2 2 0 0 1-2-2V9","key":"16sdep"}],["path",{"d":"m9 15 3 3-3 3","key":"1m3kbl"}]])
export const GitFork = ssrIcon('git-fork', [["circle",{"cx":"12","cy":"18","r":"3","key":"1mpf1b"}],["circle",{"cx":"6","cy":"6","r":"3","key":"1lh9wr"}],["circle",{"cx":"18","cy":"6","r":"3","key":"1h7g24"}],["path",{"d":"M18 9v2c0 .6-.4 1-1 1H7c-.6 0-1-.4-1-1V9","key":"1uq4wg"}],["path",{"d":"M12 12v3","key":"158kv8"}]])
export const GitGraph = ssrIcon('git-graph', [["circle",{"cx":"5","cy":"6","r":"3","key":"1qnov2"}],["path",{"d":"M5 9v6","key":"158jrl"}],["circle",{"cx":"5","cy":"18","r":"3","key":"104gr9"}],["path",{"d":"M12 3v18","key":"108xh3"}],["circle",{"cx":"19","cy":"6","r":"3","key":"108a5v"}],["path",{"d":"M16 15.7A9 9 0 0 0 19 9","key":"1e3vqb"}]])
export const GitMerge = ssrIcon('git-merge', [["circle",{"cx":"18","cy":"18","r":"3","key":"1xkwt0"}],["circle",{"cx":"6","cy":"6","r":"3","key":"1lh9wr"}],["path",{"d":"M6 21V9a9 9 0 0 0 9 9","key":"7kw0sc"}]])
export const GitMergeConflict = ssrIcon('git-merge-conflict', [["path",{"d":"M12 6h4a2 2 0 0 1 2 2v7","key":"18ej7s"}],["path",{"d":"M6 12v9","key":"9e33v1"}],["path",{"d":"m8.5 3.5-5 5","key":"cpmru9"}],["path",{"d":"m8.5 8.5-5-5","key":"1blc57"}],["circle",{"cx":"18","cy":"18","r":"3","key":"1xkwt0"}]])
export const GitPullRequest = ssrIcon('git-pull-request', [["circle",{"cx":"18","cy":"18","r":"3","key":"1xkwt0"}],["circle",{"cx":"6","cy":"6","r":"3","key":"1lh9wr"}],["path",{"d":"M13 6h3a2 2 0 0 1 2 2v7","key":"1yeb86"}],["line",{"x1":"6","x2":"6","y1":"9","y2":"21","key":"rroup"}]])
export const GitPullRequestArrow = ssrIcon('git-pull-request-arrow', [["circle",{"cx":"5","cy":"6","r":"3","key":"1qnov2"}],["path",{"d":"M5 9v12","key":"ih889a"}],["circle",{"cx":"19","cy":"18","r":"3","key":"1qljk2"}],["path",{"d":"m15 9-3-3 3-3","key":"1lwv8l"}],["path",{"d":"M12 6h5a2 2 0 0 1 2 2v7","key":"1yj91y"}]])
export const GitPullRequestClosed = ssrIcon('git-pull-request-closed', [["path",{"d":"m15.5 3.5 5 5","key":"1kmx7t"}],["path",{"d":"m15.5 8.5 5-5","key":"saftza"}],["path",{"d":"M18 11.62V15","key":"1greaj"}],["path",{"d":"M6 9v12","key":"1sc30k"}],["circle",{"cx":"18","cy":"18","r":"3","key":"1xkwt0"}],["circle",{"cx":"6","cy":"6","r":"3","key":"1lh9wr"}]])
export const GitPullRequestCreate = ssrIcon('git-pull-request-create', [["circle",{"cx":"6","cy":"6","r":"3","key":"1lh9wr"}],["path",{"d":"M6 9v12","key":"1sc30k"}],["path",{"d":"M13 6h3a2 2 0 0 1 2 2v3","key":"1jb6z3"}],["path",{"d":"M18 15v6","key":"9wciyi"}],["path",{"d":"M21 18h-6","key":"139f0c"}]])
export const GitPullRequestCreateArrow = ssrIcon('git-pull-request-create-arrow', [["circle",{"cx":"5","cy":"6","r":"3","key":"1qnov2"}],["path",{"d":"M5 9v12","key":"ih889a"}],["path",{"d":"m15 9-3-3 3-3","key":"1lwv8l"}],["path",{"d":"M12 6h5a2 2 0 0 1 2 2v3","key":"1rbwk6"}],["path",{"d":"M19 15v6","key":"10aioa"}],["path",{"d":"M22 18h-6","key":"1d5gi5"}]])
export const GitPullRequestDraft = ssrIcon('git-pull-request-draft', [["circle",{"cx":"18","cy":"18","r":"3","key":"1xkwt0"}],["circle",{"cx":"6","cy":"6","r":"3","key":"1lh9wr"}],["path",{"d":"M18 6V5","key":"1oao2s"}],["path",{"d":"M18 11v-1","key":"11c8tz"}],["line",{"x1":"6","x2":"6","y1":"9","y2":"21","key":"rroup"}]])
export const GlassWater = ssrIcon('glass-water', [["path",{"d":"M5.116 4.104A1 1 0 0 1 6.11 3h11.78a1 1 0 0 1 .994 1.105L17.19 20.21A2 2 0 0 1 15.2 22H8.8a2 2 0 0 1-2-1.79z","key":"p55z4y"}],["path",{"d":"M6 12a5 5 0 0 1 6 0 5 5 0 0 0 6 0","key":"mjntcy"}]])
export const Glasses = ssrIcon('glasses', [["circle",{"cx":"6","cy":"15","r":"4","key":"vux9w4"}],["circle",{"cx":"18","cy":"15","r":"4","key":"18o8ve"}],["path",{"d":"M14 15a2 2 0 0 0-2-2 2 2 0 0 0-2 2","key":"1ag4bs"}],["path",{"d":"M2.5 13 5 7c.7-1.3 1.4-2 3-2","key":"1hm1gs"}],["path",{"d":"M21.5 13 19 7c-.7-1.3-1.5-2-3-2","key":"1r31ai"}]])
export const Globe = ssrIcon('globe', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20","key":"13o1zl"}],["path",{"d":"M2 12h20","key":"9i4pu4"}]])
export const GlobeCheck = ssrIcon('globe-check', [["path",{"d":"m15 6 2 2 4-4","key":"levio8"}],["path",{"d":"M2 12h20A10 10 0 1 1 12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 4-10","key":"46evmv"}]])
export const GlobeLock = ssrIcon('globe-lock', [["path",{"d":"M15.686 15A14.5 14.5 0 0 1 12 22a14.5 14.5 0 0 1 0-20 10 10 0 1 0 9.542 13","key":"qkt0x6"}],["path",{"d":"M2 12h8.5","key":"ovaggd"}],["path",{"d":"M20 6V4a2 2 0 1 0-4 0v2","key":"1of5e8"}],["rect",{"width":"8","height":"5","x":"14","y":"6","rx":"1","key":"1fmf51"}]])
export const GlobeOff = ssrIcon('globe-off', [["path",{"d":"M10.114 4.462A14.5 14.5 0 0 1 12 2a10 10 0 0 1 9.313 13.643","key":"1jq2r7"}],["path",{"d":"M15.557 15.556A14.5 14.5 0 0 1 12 22 10 10 0 0 1 4.929 4.929","key":"1ohfya"}],["path",{"d":"M15.892 10.234A14.5 14.5 0 0 0 12 2a10 10 0 0 0-3.643.687","key":"1fyh9w"}],["path",{"d":"M17.656 12H22","key":"1ttse4"}],["path",{"d":"M19.071 19.071A10 10 0 0 1 12 22 14.5 14.5 0 0 1 8.44 8.45","key":"rmtjzo"}],["path",{"d":"M2 12h10","key":"19562f"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}]])
export const GlobeX = ssrIcon('globe-x', [["path",{"d":"m16 3 5 5","key":"1husv6"}],["path",{"d":"M2 12h20A10 10 0 1 1 12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 4-10","key":"46evmv"}],["path",{"d":"m21 3-5 5","key":"1g5oa7"}]])
export const Goal = ssrIcon('goal', [["path",{"d":"M12 13V2l8 4-8 4","key":"5wlwwj"}],["path",{"d":"M20.561 10.222a9 9 0 1 1-12.55-5.29","key":"1c0wjv"}],["path",{"d":"M8.002 9.997a5 5 0 1 0 8.9 2.02","key":"gb1g7m"}]])
export const Gpu = ssrIcon('gpu', [["path",{"d":"M2 17h18a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H2","key":"hpo31w"}],["path",{"d":"M2 21V3","key":"1bzk4w"}],["path",{"d":"M7 17v3a1 1 0 0 0 1 1h5a1 1 0 0 0 1-1v-3","key":"5hbqbf"}],["circle",{"cx":"16","cy":"11","r":"2","key":"qt15rb"}],["circle",{"cx":"8","cy":"11","r":"2","key":"ssideg"}]])
export const HandGrab = ssrIcon('hand-grab', [["path",{"d":"M18 11.5V9a2 2 0 0 0-2-2a2 2 0 0 0-2 2v1.4","key":"edstyy"}],["path",{"d":"M14 10V8a2 2 0 0 0-2-2a2 2 0 0 0-2 2v2","key":"19wdwo"}],["path",{"d":"M10 9.9V9a2 2 0 0 0-2-2a2 2 0 0 0-2 2v5","key":"1lugqo"}],["path",{"d":"M6 14a2 2 0 0 0-2-2a2 2 0 0 0-2 2","key":"1hbeus"}],["path",{"d":"M18 11a2 2 0 1 1 4 0v3a8 8 0 0 1-8 8h-4a8 8 0 0 1-8-8 2 2 0 1 1 4 0","key":"1etffm"}]])
export const GraduationCap = ssrIcon('graduation-cap', [["path",{"d":"M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z","key":"j76jl0"}],["path",{"d":"M22 10v6","key":"1lu8f3"}],["path",{"d":"M6 12.5V16a6 3 0 0 0 12 0v-3.5","key":"1r8lef"}]])
export const Grape = ssrIcon('grape', [["path",{"d":"M22 5V2l-5.89 5.89","key":"1eenpo"}],["circle",{"cx":"16.6","cy":"15.89","r":"3","key":"xjtalx"}],["circle",{"cx":"8.11","cy":"7.4","r":"3","key":"u2fv6i"}],["circle",{"cx":"12.35","cy":"11.65","r":"3","key":"i6i8g7"}],["circle",{"cx":"13.91","cy":"5.85","r":"3","key":"6ye0dv"}],["circle",{"cx":"18.15","cy":"10.09","r":"3","key":"snx9no"}],["circle",{"cx":"6.56","cy":"13.2","r":"3","key":"17x4xg"}],["circle",{"cx":"10.8","cy":"17.44","r":"3","key":"1hogw9"}],["circle",{"cx":"5","cy":"19","r":"3","key":"1sn6vo"}]])
export const Grid3x3 = ssrIcon('grid-3x3', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M3 15h18","key":"5xshup"}],["path",{"d":"M9 3v18","key":"fh3hqa"}],["path",{"d":"M15 3v18","key":"14nvp0"}]])
export const Grid2x2 = ssrIcon('grid-2x2', [["path",{"d":"M12 3v18","key":"108xh3"}],["path",{"d":"M3 12h18","key":"1i2n21"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const Grid2x2Check = ssrIcon('grid-2x2-check', [["path",{"d":"M12 3v17a1 1 0 0 1-1 1H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v6a1 1 0 0 1-1 1H3","key":"11za1p"}],["path",{"d":"m16 19 2 2 4-4","key":"1b14m6"}]])
export const Grid2x2Plus = ssrIcon('grid-2x2-plus', [["path",{"d":"M12 3v17a1 1 0 0 1-1 1H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v6a1 1 0 0 1-1 1H3","key":"11za1p"}],["path",{"d":"M16 19h6","key":"xwg31i"}],["path",{"d":"M19 22v-6","key":"qhmiwi"}]])
export const Grid2x2X = ssrIcon('grid-2x2-x', [["path",{"d":"M12 3v17a1 1 0 0 1-1 1H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v6a1 1 0 0 1-1 1H3","key":"11za1p"}],["path",{"d":"m16.5 16.5 5 5","key":"zc9lw7"}],["path",{"d":"m16.5 21.5 5-5","key":"1fr29m"}]])
export const Grid3x2 = ssrIcon('grid-3x2', [["path",{"d":"M15 3v18","key":"14nvp0"}],["path",{"d":"M3 12h18","key":"1i2n21"}],["path",{"d":"M9 3v18","key":"fh3hqa"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const Grip = ssrIcon('grip', [["circle",{"cx":"12","cy":"5","r":"1","key":"gxeob9"}],["circle",{"cx":"19","cy":"5","r":"1","key":"w8mnmm"}],["circle",{"cx":"5","cy":"5","r":"1","key":"lttvr7"}],["circle",{"cx":"12","cy":"12","r":"1","key":"41hilf"}],["circle",{"cx":"19","cy":"12","r":"1","key":"1wjl8i"}],["circle",{"cx":"5","cy":"12","r":"1","key":"1pcz8c"}],["circle",{"cx":"12","cy":"19","r":"1","key":"lyex9k"}],["circle",{"cx":"19","cy":"19","r":"1","key":"shf9b7"}],["circle",{"cx":"5","cy":"19","r":"1","key":"bfqh0e"}]])
export const GripHorizontal = ssrIcon('grip-horizontal', [["circle",{"cx":"12","cy":"9","r":"1","key":"124mty"}],["circle",{"cx":"19","cy":"9","r":"1","key":"1ruzo2"}],["circle",{"cx":"5","cy":"9","r":"1","key":"1a8b28"}],["circle",{"cx":"12","cy":"15","r":"1","key":"1e56xg"}],["circle",{"cx":"19","cy":"15","r":"1","key":"1a92ep"}],["circle",{"cx":"5","cy":"15","r":"1","key":"5r1jwy"}]])
export const GripVertical = ssrIcon('grip-vertical', [["circle",{"cx":"9","cy":"12","r":"1","key":"1vctgf"}],["circle",{"cx":"9","cy":"5","r":"1","key":"hp0tcf"}],["circle",{"cx":"9","cy":"19","r":"1","key":"fkjjf6"}],["circle",{"cx":"15","cy":"12","r":"1","key":"1tmaij"}],["circle",{"cx":"15","cy":"5","r":"1","key":"19l28e"}],["circle",{"cx":"15","cy":"19","r":"1","key":"f4zoj3"}]])
export const Group = ssrIcon('group', [["path",{"d":"M3 7V5c0-1.1.9-2 2-2h2","key":"adw53z"}],["path",{"d":"M17 3h2c1.1 0 2 .9 2 2v2","key":"an4l38"}],["path",{"d":"M21 17v2c0 1.1-.9 2-2 2h-2","key":"144t0e"}],["path",{"d":"M7 21H5c-1.1 0-2-.9-2-2v-2","key":"rtnfgi"}],["rect",{"width":"7","height":"5","x":"7","y":"7","rx":"1","key":"1eyiv7"}],["rect",{"width":"7","height":"5","x":"10","y":"12","rx":"1","key":"1qlmkx"}]])
export const Guitar = ssrIcon('guitar', [["path",{"d":"m11.9 12.1 4.514-4.514","key":"109xqo"}],["path",{"d":"M20.1 2.3a1 1 0 0 0-1.4 0l-1.114 1.114A2 2 0 0 0 17 4.828v1.344a2 2 0 0 1-.586 1.414A2 2 0 0 1 17.828 7h1.344a2 2 0 0 0 1.414-.586L21.7 5.3a1 1 0 0 0 0-1.4z","key":"txyc8t"}],["path",{"d":"m6 16 2 2","key":"16qmzd"}],["path",{"d":"M8.23 9.85A3 3 0 0 1 11 8a5 5 0 0 1 5 5 3 3 0 0 1-1.85 2.77l-.92.38A2 2 0 0 0 12 18a4 4 0 0 1-4 4 6 6 0 0 1-6-6 4 4 0 0 1 4-4 2 2 0 0 0 1.85-1.23z","key":"1de1vg"}]])
export const Ham = ssrIcon('ham', [["path",{"d":"M13.144 21.144A7.274 10.445 45 1 0 2.856 10.856","key":"1k1t7q"}],["path",{"d":"M13.144 21.144A7.274 4.365 45 0 0 2.856 10.856a7.274 4.365 45 0 0 10.288 10.288","key":"153t1g"}],["path",{"d":"M16.565 10.435 18.6 8.4a2.501 2.501 0 1 0 1.65-4.65 2.5 2.5 0 1 0-4.66 1.66l-2.024 2.025","key":"gzrt0n"}],["path",{"d":"m8.5 16.5-1-1","key":"otr954"}]])
export const Hamburger = ssrIcon('hamburger', [["path",{"d":"M12 16H4a2 2 0 1 1 0-4h16a2 2 0 1 1 0 4h-4.25","key":"5dloqd"}],["path",{"d":"M5 12a2 2 0 0 1-2-2 9 7 0 0 1 18 0 2 2 0 0 1-2 2","key":"1vl3my"}],["path",{"d":"M5 16a2 2 0 0 0-2 2 3 3 0 0 0 3 3h12a3 3 0 0 0 3-3 2 2 0 0 0-2-2q0 0 0 0","key":"1us75o"}],["path",{"d":"m6.67 12 6.13 4.6a2 2 0 0 0 2.8-.4l3.15-4.2","key":"qqzweh"}]])
export const Hammer = ssrIcon('hammer', [["path",{"d":"m15 12-9.373 9.373a1 1 0 0 1-3.001-3L12 9","key":"1hayfq"}],["path",{"d":"m18 15 4-4","key":"16gjal"}],["path",{"d":"m21.5 11.5-1.914-1.914A2 2 0 0 1 19 8.172v-.344a2 2 0 0 0-.586-1.414l-1.657-1.657A6 6 0 0 0 12.516 3H9l1.243 1.243A6 6 0 0 1 12 8.485V10l2 2h1.172a2 2 0 0 1 1.414.586L18.5 14.5","key":"15ts47"}]])
export const Hand = ssrIcon('hand', [["path",{"d":"M18 11V6a2 2 0 0 0-2-2a2 2 0 0 0-2 2","key":"1fvzgz"}],["path",{"d":"M14 10V4a2 2 0 0 0-2-2a2 2 0 0 0-2 2v2","key":"1kc0my"}],["path",{"d":"M10 10.5V6a2 2 0 0 0-2-2a2 2 0 0 0-2 2v8","key":"10h0bg"}],["path",{"d":"M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15","key":"1s1gnw"}]])
export const HandCoins = ssrIcon('hand-coins', [["path",{"d":"M11 15h2a2 2 0 1 0 0-4h-3c-.6 0-1.1.2-1.4.6L3 17","key":"geh8rc"}],["path",{"d":"m7 21 1.6-1.4c.3-.4.8-.6 1.4-.6h4c1.1 0 2.1-.4 2.8-1.2l4.6-4.4a2 2 0 0 0-2.75-2.91l-4.2 3.9","key":"1fto5m"}],["path",{"d":"m2 16 6 6","key":"1pfhp9"}],["circle",{"cx":"16","cy":"9","r":"2.9","key":"1n0dlu"}],["circle",{"cx":"6","cy":"5","r":"3","key":"151irh"}]])
export const HandFist = ssrIcon('hand-fist', [["path",{"d":"M12.035 17.012a3 3 0 0 0-3-3l-.311-.002a.72.72 0 0 1-.505-1.229l1.195-1.195A2 2 0 0 1 10.828 11H12a2 2 0 0 0 0-4H9.243a3 3 0 0 0-2.122.879l-2.707 2.707A4.83 4.83 0 0 0 3 14a8 8 0 0 0 8 8h2a8 8 0 0 0 8-8V7a2 2 0 1 0-4 0v2a2 2 0 1 0 4 0","key":"1ff7rl"}],["path",{"d":"M13.888 9.662A2 2 0 0 0 17 8V5A2 2 0 1 0 13 5","key":"1xmd21"}],["path",{"d":"M9 5A2 2 0 1 0 5 5V10","key":"f3wfjw"}],["path",{"d":"M9 7V4A2 2 0 1 1 13 4V7.268","key":"eaoucv"}]])
export const HandHeart = ssrIcon('hand-heart', [["path",{"d":"M11 14h2a2 2 0 0 0 0-4h-3c-.6 0-1.1.2-1.4.6L3 16","key":"1v1a37"}],["path",{"d":"m14.45 13.39 5.05-4.694C20.196 8 21 6.85 21 5.75a2.75 2.75 0 0 0-4.797-1.837.276.276 0 0 1-.406 0A2.75 2.75 0 0 0 11 5.75c0 1.2.802 2.248 1.5 2.946L16 11.95","key":"fhfbnt"}],["path",{"d":"m2 15 6 6","key":"10dquu"}],["path",{"d":"m7 20 1.6-1.4c.3-.4.8-.6 1.4-.6h4c1.1 0 2.1-.4 2.8-1.2l4.6-4.4a1 1 0 0 0-2.75-2.91","key":"1x6kdw"}]])
export const HandHelping = ssrIcon('hand-helping', [["path",{"d":"M11 12h2a2 2 0 1 0 0-4h-3c-.6 0-1.1.2-1.4.6L3 14","key":"1j4xps"}],["path",{"d":"m7 18 1.6-1.4c.3-.4.8-.6 1.4-.6h4c1.1 0 2.1-.4 2.8-1.2l4.6-4.4a2 2 0 0 0-2.75-2.91l-4.2 3.9","key":"uospg8"}],["path",{"d":"m2 13 6 6","key":"16e5sb"}]])
export const HandMetal = ssrIcon('hand-metal', [["path",{"d":"M18 12.5V10a2 2 0 0 0-2-2a2 2 0 0 0-2 2v1.4","key":"wc6myp"}],["path",{"d":"M14 11V9a2 2 0 1 0-4 0v2","key":"94qvcw"}],["path",{"d":"M10 10.5V5a2 2 0 1 0-4 0v9","key":"m1ah89"}],["path",{"d":"m7 15-1.76-1.76a2 2 0 0 0-2.83 2.82l3.6 3.6C7.5 21.14 9.2 22 12 22h2a8 8 0 0 0 8-8V7a2 2 0 1 0-4 0v5","key":"t1skq1"}]])
export const HandPlatter = ssrIcon('hand-platter', [["path",{"d":"M12 3V2","key":"ar7q03"}],["path",{"d":"m15.4 17.4 3.2-2.8a2 2 0 1 1 2.8 2.9l-3.6 3.3c-.7.8-1.7 1.2-2.8 1.2h-4c-1.1 0-2.1-.4-2.8-1.2l-1.302-1.464A1 1 0 0 0 6.151 19H5","key":"n2g93r"}],["path",{"d":"M2 14h12a2 2 0 0 1 0 4h-2","key":"1o2jem"}],["path",{"d":"M4 10h16","key":"img6z1"}],["path",{"d":"M5 10a7 7 0 0 1 14 0","key":"1ega1o"}],["path",{"d":"M5 14v6a1 1 0 0 1-1 1H2","key":"1hescx"}]])
export const Handbag = ssrIcon('handbag', [["path",{"d":"M2.048 18.566A2 2 0 0 0 4 21h16a2 2 0 0 0 1.952-2.434l-2-9A2 2 0 0 0 18 8H6a2 2 0 0 0-1.952 1.566z","key":"1qbui5"}],["path",{"d":"M8 11V6a4 4 0 0 1 8 0v5","key":"tcht90"}]])
export const Handshake = ssrIcon('handshake', [["path",{"d":"m11 17 2 2a1 1 0 1 0 3-3","key":"efffak"}],["path",{"d":"m14 14 2.5 2.5a1 1 0 1 0 3-3l-3.88-3.88a3 3 0 0 0-4.24 0l-.88.88a1 1 0 1 1-3-3l2.81-2.81a5.79 5.79 0 0 1 7.06-.87l.47.28a2 2 0 0 0 1.42.25L21 4","key":"9pr0kb"}],["path",{"d":"m21 3 1 11h-2","key":"1tisrp"}],["path",{"d":"M3 3 2 14l6.5 6.5a1 1 0 1 0 3-3","key":"1uvwmv"}],["path",{"d":"M3 4h8","key":"1ep09j"}]])
export const HardDrive = ssrIcon('hard-drive', [["path",{"d":"M10 16h.01","key":"1bzywj"}],["path",{"d":"M2.212 11.577a2 2 0 0 0-.212.896V18a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-5.527a2 2 0 0 0-.212-.896L18.55 5.11A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z","key":"18tbho"}],["path",{"d":"M21.946 12.013H2.054","key":"zqlbp7"}],["path",{"d":"M6 16h.01","key":"1pmjb7"}]])
export const HardDriveDownload = ssrIcon('hard-drive-download', [["path",{"d":"M12 2v8","key":"1q4o3n"}],["path",{"d":"m16 6-4 4-4-4","key":"6wukr"}],["rect",{"width":"20","height":"8","x":"2","y":"14","rx":"2","key":"w68u3i"}],["path",{"d":"M6 18h.01","key":"uhywen"}],["path",{"d":"M10 18h.01","key":"h775k"}]])
export const HardDriveUpload = ssrIcon('hard-drive-upload', [["path",{"d":"m16 6-4-4-4 4","key":"13yo43"}],["path",{"d":"M12 2v8","key":"1q4o3n"}],["rect",{"width":"20","height":"8","x":"2","y":"14","rx":"2","key":"w68u3i"}],["path",{"d":"M6 18h.01","key":"uhywen"}],["path",{"d":"M10 18h.01","key":"h775k"}]])
export const HardHat = ssrIcon('hard-hat', [["path",{"d":"M10 10V5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v5","key":"1p9q5i"}],["path",{"d":"M14 6a6 6 0 0 1 6 6v3","key":"1hnv84"}],["path",{"d":"M4 15v-3a6 6 0 0 1 6-6","key":"9ciidu"}],["rect",{"x":"2","y":"15","width":"20","height":"4","rx":"1","key":"g3x8cw"}]])
export const Hash = ssrIcon('hash', [["line",{"x1":"4","x2":"20","y1":"9","y2":"9","key":"4lhtct"}],["line",{"x1":"4","x2":"20","y1":"15","y2":"15","key":"vyu0kd"}],["line",{"x1":"10","x2":"8","y1":"3","y2":"21","key":"1ggp8o"}],["line",{"x1":"16","x2":"14","y1":"3","y2":"21","key":"weycgp"}]])
export const HatGlasses = ssrIcon('hat-glasses', [["path",{"d":"M14 18a2 2 0 0 0-4 0","key":"1v8fkw"}],["path",{"d":"m19 11-2.11-6.657a2 2 0 0 0-2.752-1.148l-1.276.61A2 2 0 0 1 12 4H8.5a2 2 0 0 0-1.925 1.456L5 11","key":"1fkr7p"}],["path",{"d":"M2 11h20","key":"3eubbj"}],["circle",{"cx":"17","cy":"18","r":"3","key":"82mm0e"}],["circle",{"cx":"7","cy":"18","r":"3","key":"lvkj7j"}]])
export const Haze = ssrIcon('haze', [["path",{"d":"m5.2 6.2 1.4 1.4","key":"17imol"}],["path",{"d":"M2 13h2","key":"13gyu8"}],["path",{"d":"M20 13h2","key":"16rner"}],["path",{"d":"m17.4 7.6 1.4-1.4","key":"t4xlah"}],["path",{"d":"M22 17H2","key":"1gtaj3"}],["path",{"d":"M22 21H2","key":"1gy6en"}],["path",{"d":"M16 13a4 4 0 0 0-8 0","key":"1dyczq"}],["path",{"d":"M12 5V2.5","key":"1vytko"}]])
export const Hd = ssrIcon('hd', [["path",{"d":"M10 12H6","key":"15f2ro"}],["path",{"d":"M10 15V9","key":"1lckn7"}],["path",{"d":"M14 14.5a.5.5 0 0 0 .5.5h1a2.5 2.5 0 0 0 2.5-2.5v-1A2.5 2.5 0 0 0 15.5 9h-1a.5.5 0 0 0-.5.5z","key":"b3f847"}],["path",{"d":"M6 15V9","key":"12stmj"}],["rect",{"x":"2","y":"5","width":"20","height":"14","rx":"2","key":"qneu4z"}]])
export const HdmiPort = ssrIcon('hdmi-port', [["path",{"d":"M22 9a1 1 0 00-1-1H3a1 1 0 00-1 1v4a1 1 0 001 1h.5a2 2 0 011.6.8l.3.4A2 2 0 007 16h10a2 2 0 001.6-.8l.3-.4a2 2 0 011.6-.8h.5a1 1 0 001-1z","key":"1kwg9h"}],["path",{"d":"M8 12h8","key":"1wcyev"}]])
export const Heading = ssrIcon('heading', [["path",{"d":"M6 12h12","key":"8npq4p"}],["path",{"d":"M6 20V4","key":"1w1bmo"}],["path",{"d":"M18 20V4","key":"o2hl4u"}]])
export const Heading1 = ssrIcon('heading-1', [["path",{"d":"M4 12h8","key":"17cfdx"}],["path",{"d":"M4 18V6","key":"1rz3zl"}],["path",{"d":"M12 18V6","key":"zqpxq5"}],["path",{"d":"m17 12 3-2v8","key":"1hhhft"}]])
export const Heading2 = ssrIcon('heading-2', [["path",{"d":"M4 12h8","key":"17cfdx"}],["path",{"d":"M4 18V6","key":"1rz3zl"}],["path",{"d":"M12 18V6","key":"zqpxq5"}],["path",{"d":"M21 18h-4c0-4 4-3 4-6 0-1.5-2-2.5-4-1","key":"9jr5yi"}]])
export const Heading3 = ssrIcon('heading-3', [["path",{"d":"M4 12h8","key":"17cfdx"}],["path",{"d":"M4 18V6","key":"1rz3zl"}],["path",{"d":"M12 18V6","key":"zqpxq5"}],["path",{"d":"M17.5 10.5c1.7-1 3.5 0 3.5 1.5a2 2 0 0 1-2 2","key":"68ncm8"}],["path",{"d":"M17 17.5c2 1.5 4 .3 4-1.5a2 2 0 0 0-2-2","key":"1ejuhz"}]])
export const Heading4 = ssrIcon('heading-4', [["path",{"d":"M12 18V6","key":"zqpxq5"}],["path",{"d":"M17 10v3a1 1 0 0 0 1 1h3","key":"tj5zdr"}],["path",{"d":"M21 10v8","key":"1kdml4"}],["path",{"d":"M4 12h8","key":"17cfdx"}],["path",{"d":"M4 18V6","key":"1rz3zl"}]])
export const Heading5 = ssrIcon('heading-5', [["path",{"d":"M4 12h8","key":"17cfdx"}],["path",{"d":"M4 18V6","key":"1rz3zl"}],["path",{"d":"M12 18V6","key":"zqpxq5"}],["path",{"d":"M17 13v-3h4","key":"1nvgqp"}],["path",{"d":"M17 17.7c.4.2.8.3 1.3.3 1.5 0 2.7-1.1 2.7-2.5S19.8 13 18.3 13H17","key":"2nebdn"}]])
export const Heading6 = ssrIcon('heading-6', [["path",{"d":"M4 12h8","key":"17cfdx"}],["path",{"d":"M4 18V6","key":"1rz3zl"}],["path",{"d":"M12 18V6","key":"zqpxq5"}],["circle",{"cx":"19","cy":"16","r":"2","key":"15mx69"}],["path",{"d":"M20 10c-2 2-3 3.5-3 6","key":"f35dl0"}]])
export const HeadphoneOff = ssrIcon('headphone-off', [["path",{"d":"M21 14h-1.343","key":"1jdnxi"}],["path",{"d":"M9.128 3.47A9 9 0 0 1 21 12v3.343","key":"6kipu2"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M20.414 20.414A2 2 0 0 1 19 21h-1a2 2 0 0 1-2-2v-3","key":"9x50f4"}],["path",{"d":"M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 2.636-6.364","key":"1bkxnm"}]])
export const Headphones = ssrIcon('headphones', [["path",{"d":"M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3","key":"1xhozi"}]])
export const Headset = ssrIcon('headset', [["path",{"d":"M3 11h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-5Zm0 0a9 9 0 1 1 18 0m0 0v5a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3Z","key":"12oyoe"}],["path",{"d":"M21 16v2a4 4 0 0 1-4 4h-5","key":"1x7m43"}]])
export const Heart = ssrIcon('heart', [["path",{"d":"M2 9.5a5.5 5.5 0 0 1 9.591-3.676.56.56 0 0 0 .818 0A5.49 5.49 0 0 1 22 9.5c0 2.29-1.5 4-3 5.5l-5.492 5.313a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5","key":"mvr1a0"}]])
export const HeartCrack = ssrIcon('heart-crack', [["path",{"d":"M12.409 5.824c-.702.792-1.15 1.496-1.415 2.166l2.153 2.156a.5.5 0 0 1 0 .707l-2.293 2.293a.5.5 0 0 0 0 .707L12 15","key":"idzbju"}],["path",{"d":"M13.508 20.313a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5a5.5 5.5 0 0 1 9.591-3.677.6.6 0 0 0 .818.001A5.5 5.5 0 0 1 22 9.5c0 2.29-1.5 4-3 5.5z","key":"1su70f"}]])
export const HeartHandshake = ssrIcon('heart-handshake', [["path",{"d":"M19.414 14.414C21 12.828 22 11.5 22 9.5a5.5 5.5 0 0 0-9.591-3.676.6.6 0 0 1-.818.001A5.5 5.5 0 0 0 2 9.5c0 2.3 1.5 4 3 5.5l5.535 5.362a2 2 0 0 0 2.879.052 2.12 2.12 0 0 0-.004-3 2.124 2.124 0 1 0 3-3 2.124 2.124 0 0 0 3.004 0 2 2 0 0 0 0-2.828l-1.881-1.882a2.41 2.41 0 0 0-3.409 0l-1.71 1.71a2 2 0 0 1-2.828 0 2 2 0 0 1 0-2.828l2.823-2.762","key":"17lmqv"}]])
export const HeartMinus = ssrIcon('heart-minus', [["path",{"d":"m14.876 18.99-1.368 1.323a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5a5.5 5.5 0 0 1 9.591-3.676.56.56 0 0 0 .818 0A5.49 5.49 0 0 1 22 9.5a5.2 5.2 0 0 1-.244 1.572","key":"15yztm"}],["path",{"d":"M15 15h6","key":"1u4692"}]])
export const HeartOff = ssrIcon('heart-off', [["path",{"d":"M10.5 4.893a5.5 5.5 0 0 1 1.091.931.56.56 0 0 0 .818 0A5.49 5.49 0 0 1 22 9.5c0 1.872-1.002 3.356-2.187 4.655","key":"1inpfl"}],["path",{"d":"m16.967 16.967-3.459 3.346a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5a5.5 5.5 0 0 1 2.747-4.761","key":"vbc6x7"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}]])
export const HeartPlus = ssrIcon('heart-plus', [["path",{"d":"m14.479 19.374-.971.939a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5a5.5 5.5 0 0 1 9.591-3.676.56.56 0 0 0 .818 0A5.49 5.49 0 0 1 22 9.5a5.2 5.2 0 0 1-.219 1.49","key":"wg5jx"}],["path",{"d":"M15 15h6","key":"1u4692"}],["path",{"d":"M18 12v6","key":"1houu1"}]])
export const HeartPulse = ssrIcon('heart-pulse', [["path",{"d":"M2 9.5a5.5 5.5 0 0 1 9.591-3.676.56.56 0 0 0 .818 0A5.49 5.49 0 0 1 22 9.5c0 2.29-1.5 4-3 5.5l-5.492 5.313a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5","key":"mvr1a0"}],["path",{"d":"M3.22 13H9.5l.5-1 2 4.5 2-7 1.5 3.5h5.27","key":"auskq0"}]])
export const HeartX = ssrIcon('heart-x', [["path",{"d":"m15.5 12.5 5 5","key":"15wbfr"}],["path",{"d":"m20.5 12.5-5 5","key":"o012pn"}],["path",{"d":"M21.955 8.774a5.5 5.5 0 0 0-9.546-2.95.6.6 0 0 1-.818 0A5.5 5.5 0 0 0 2 9.5c0 2.3 1.5 4 3 5.5l5.508 5.332a2 2 0 0 0 2.57.352","key":"c1obtn"}]])
export const Heater = ssrIcon('heater', [["path",{"d":"M11 8c2-3-2-3 0-6","key":"1ldv5m"}],["path",{"d":"M15.5 8c2-3-2-3 0-6","key":"1otqoz"}],["path",{"d":"M6 10h.01","key":"1lbq93"}],["path",{"d":"M6 14h.01","key":"zudwn7"}],["path",{"d":"M10 16v-4","key":"1c25yv"}],["path",{"d":"M14 16v-4","key":"1dkbt8"}],["path",{"d":"M18 16v-4","key":"1yg9me"}],["path",{"d":"M20 6a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h3","key":"1ubg90"}],["path",{"d":"M5 20v2","key":"1abpe8"}],["path",{"d":"M19 20v2","key":"kqn6ft"}]])
export const Helicopter = ssrIcon('helicopter', [["path",{"d":"M11 17v4","key":"14wq8k"}],["path",{"d":"M14 3v8a2 2 0 0 0 2 2h5.865","key":"12oo5h"}],["path",{"d":"M17 17v4","key":"hdt4hh"}],["path",{"d":"M18 17a4 4 0 0 0 4-4 8 6 0 0 0-8-6 6 5 0 0 0-6 5v3a2 2 0 0 0 2 2z","key":"yynif"}],["path",{"d":"M2 10v5","key":"sa5akn"}],["path",{"d":"M6 3h16","key":"27qw71"}],["path",{"d":"M7 21h14","key":"1ugz0u"}],["path",{"d":"M8 13H2","key":"1thz1o"}]])
export const Hexagon = ssrIcon('hexagon', [["path",{"d":"M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z","key":"yt0hxn"}]])
export const Highlighter = ssrIcon('highlighter', [["path",{"d":"m9 11-6 6v3h9l3-3","key":"1a3l36"}],["path",{"d":"m22 12-4.6 4.6a2 2 0 0 1-2.8 0l-5.2-5.2a2 2 0 0 1 0-2.8L14 4","key":"14a9rk"}]])
export const RotateCcwClock = ssrIcon('rotate-ccw-clock', [["path",{"d":"M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8","key":"1357e3"}],["path",{"d":"M3 3v5h5","key":"1xhq8a"}],["path",{"d":"M12 7v5l4 2","key":"1fdv2h"}]])
export const House = ssrIcon('house', [["path",{"d":"M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8","key":"5wwlr5"}],["path",{"d":"M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z","key":"r6nss1"}]])
export const Hop = ssrIcon('hop', [["path",{"d":"M10.82 16.12c1.69.6 3.91.79 5.18.85.55.03 1-.42.97-.97-.06-1.27-.26-3.5-.85-5.18","key":"18lxf1"}],["path",{"d":"M11.5 6.5c1.64 0 5-.38 6.71-1.07.52-.2.55-.82.12-1.17A10 10 0 0 0 4.26 18.33c.35.43.96.4 1.17-.12.69-1.71 1.07-5.07 1.07-6.71 1.34.45 3.1.9 4.88.62a.88.88 0 0 0 .73-.74c.3-2.14-.15-3.5-.61-4.88","key":"vtfxrw"}],["path",{"d":"M15.62 16.95c.2.85.62 2.76.5 4.28a.77.77 0 0 1-.9.7 16.64 16.64 0 0 1-4.08-1.36","key":"13hl71"}],["path",{"d":"M16.13 21.05c1.65.63 3.68.84 4.87.91a.9.9 0 0 0 .96-.96 17.68 17.68 0 0 0-.9-4.87","key":"1sl8oj"}],["path",{"d":"M16.94 15.62c.86.2 2.77.62 4.29.5a.77.77 0 0 0 .7-.9 16.64 16.64 0 0 0-1.36-4.08","key":"19c6kt"}],["path",{"d":"M17.99 5.52a20.82 20.82 0 0 1 3.15 4.5.8.8 0 0 1-.68 1.13c-2.33.2-5.3-.32-8.27-1.57","key":"85ghs3"}],["path",{"d":"M4.93 4.93 3 3a.7.7 0 0 1 0-1","key":"x087yj"}],["path",{"d":"M9.58 12.18c1.24 2.98 1.77 5.95 1.57 8.28a.8.8 0 0 1-1.13.68 20.82 20.82 0 0 1-4.5-3.15","key":"11xdqo"}]])
export const HopOff = ssrIcon('hop-off', [["path",{"d":"M10.82 16.12c1.69.6 3.91.79 5.18.85.28.01.53-.09.7-.27","key":"qyzcap"}],["path",{"d":"M11.14 20.57c.52.24 2.44 1.12 4.08 1.37.46.06.86-.25.9-.71.12-1.52-.3-3.43-.5-4.28","key":"y078lb"}],["path",{"d":"M16.13 21.05c1.65.63 3.68.84 4.87.91a.9.9 0 0 0 .7-.26","key":"1utre3"}],["path",{"d":"M17.99 5.52a20.83 20.83 0 0 1 3.15 4.5.8.8 0 0 1-.68 1.13c-1.17.1-2.5.02-3.9-.25","key":"17o9hm"}],["path",{"d":"M20.57 11.14c.24.52 1.12 2.44 1.37 4.08.04.3-.08.59-.31.75","key":"1d1n4p"}],["path",{"d":"M4.93 4.93a10 10 0 0 0-.67 13.4c.35.43.96.4 1.17-.12.69-1.71 1.07-5.07 1.07-6.71 1.34.45 3.1.9 4.88.62a.85.85 0 0 0 .48-.24","key":"9uv3tt"}],["path",{"d":"M5.52 17.99c1.05.95 2.91 2.42 4.5 3.15a.8.8 0 0 0 1.13-.68c.2-2.34-.33-5.3-1.57-8.28","key":"1292wz"}],["path",{"d":"M8.35 2.68a10 10 0 0 1 9.98 1.58c.43.35.4.96-.12 1.17-1.5.6-4.3.98-6.07 1.05","key":"7ozu9p"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}]])
export const Hospital = ssrIcon('hospital', [["path",{"d":"M12 7v4","key":"xawao1"}],["path",{"d":"M14 21v-3a2 2 0 0 0-4 0v3","key":"1rgiei"}],["path",{"d":"M14 9h-4","key":"1w2s2s"}],["path",{"d":"M18 11h2a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-9a2 2 0 0 1 2-2h2","key":"1tthqt"}],["path",{"d":"M18 21V5a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16","key":"dw4p4i"}]])
export const Hotel = ssrIcon('hotel', [["path",{"d":"M10 22v-6.57","key":"1wmca3"}],["path",{"d":"M12 11h.01","key":"z322tv"}],["path",{"d":"M12 7h.01","key":"1ivr5q"}],["path",{"d":"M14 15.43V22","key":"1q2vjd"}],["path",{"d":"M15 16a5 5 0 0 0-6 0","key":"o9wqvi"}],["path",{"d":"M16 11h.01","key":"xkw8gn"}],["path",{"d":"M16 7h.01","key":"1kdx03"}],["path",{"d":"M8 11h.01","key":"1dfujw"}],["path",{"d":"M8 7h.01","key":"1vti4s"}],["rect",{"x":"4","y":"2","width":"16","height":"20","rx":"2","key":"1uxh74"}]])
export const Hourglass = ssrIcon('hourglass', [["path",{"d":"M5 22h14","key":"ehvnwv"}],["path",{"d":"M5 2h14","key":"pdyrp9"}],["path",{"d":"M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22","key":"1d314k"}],["path",{"d":"M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2","key":"1vvvr6"}]])
export const HouseHeart = ssrIcon('house-heart', [["path",{"d":"M8.62 13.8A2.25 2.25 0 1 1 12 10.836a2.25 2.25 0 1 1 3.38 2.966l-2.626 2.856a.998.998 0 0 1-1.507 0z","key":"n9s7kx"}],["path",{"d":"M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z","key":"r6nss1"}]])
export const HousePlug = ssrIcon('house-plug', [["path",{"d":"M10 12V8.964","key":"1vll13"}],["path",{"d":"M14 12V8.964","key":"1x3qvg"}],["path",{"d":"M15 12a1 1 0 0 1 1 1v2a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-2a1 1 0 0 1 1-1z","key":"ppykja"}],["path",{"d":"M8.5 21H5a2 2 0 0 1-2-2v-9a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2h-5a2 2 0 0 1-2-2v-2","key":"365xoy"}]])
export const HousePlus = ssrIcon('house-plus', [["path",{"d":"M12.35 21H5a2 2 0 0 1-2-2v-9a2 2 0 0 1 .71-1.53l7-6a2 2 0 0 1 2.58 0l7 6A2 2 0 0 1 21 10v2.35","key":"8ek5ge"}],["path",{"d":"M14.8 12.4A1 1 0 0 0 14 12h-4a1 1 0 0 0-1 1v8","key":"1rbg29"}],["path",{"d":"M15 18h6","key":"3b3c90"}],["path",{"d":"M18 15v6","key":"9wciyi"}]])
export const HouseWifi = ssrIcon('house-wifi', [["path",{"d":"M9.5 13.866a4 4 0 0 1 5 .01","key":"1wy54i"}],["path",{"d":"M12 17h.01","key":"p32p05"}],["path",{"d":"M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z","key":"r6nss1"}],["path",{"d":"M7 10.754a8 8 0 0 1 10 0","key":"exoy2g"}]])
export const IceCreamCone = ssrIcon('ice-cream-cone', [["path",{"d":"m7 11 4.08 10.35a1 1 0 0 0 1.84 0L17 11","key":"1v6356"}],["path",{"d":"M17 7A5 5 0 0 0 7 7","key":"151p3v"}],["path",{"d":"M17 7a2 2 0 0 1 0 4H7a2 2 0 0 1 0-4","key":"1sdaij"}]])
export const IceCreamBowl = ssrIcon('ice-cream-bowl', [["path",{"d":"M12 17c5 0 8-2.69 8-6H4c0 3.31 3 6 8 6m-4 4h8m-4-3v3M5.14 11a3.5 3.5 0 1 1 6.71 0","key":"1uxfcu"}],["path",{"d":"M12.14 11a3.5 3.5 0 1 1 6.71 0","key":"4k3m1s"}],["path",{"d":"M15.5 6.5a3.5 3.5 0 1 0-7 0","key":"zmuahr"}]])
export const IdCard = ssrIcon('id-card', [["path",{"d":"M16 10h2","key":"8sgtl7"}],["path",{"d":"M16 14h2","key":"epxaof"}],["path",{"d":"M6.17 15a3 3 0 0 1 5.66 0","key":"n6f512"}],["circle",{"cx":"9","cy":"11","r":"2","key":"yxgjnd"}],["rect",{"x":"2","y":"5","width":"20","height":"14","rx":"2","key":"qneu4z"}]])
export const IdCardLanyard = ssrIcon('id-card-lanyard', [["path",{"d":"M13.5 8h-3","key":"xvov4w"}],["path",{"d":"m15 2-1 2h3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h3","key":"16uttc"}],["path",{"d":"M16.899 22A5 5 0 0 0 7.1 22","key":"1d0ppr"}],["path",{"d":"m9 2 3 6","key":"1o7bd9"}],["circle",{"cx":"12","cy":"15","r":"3","key":"g36mzq"}]])
export const Image = ssrIcon('image', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","ry":"2","key":"1m3agn"}],["circle",{"cx":"9","cy":"9","r":"2","key":"af1f0g"}],["path",{"d":"m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21","key":"1xmnt7"}]])
export const ImageDown = ssrIcon('image-down', [["path",{"d":"M10.3 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10l-3.1-3.1a2 2 0 0 0-2.814.014L6 21","key":"9csbqa"}],["path",{"d":"m14 19 3 3v-5.5","key":"9ldu5r"}],["path",{"d":"m17 22 3-3","key":"1nkfve"}],["circle",{"cx":"9","cy":"9","r":"2","key":"af1f0g"}]])
export const ImageMinus = ssrIcon('image-minus', [["path",{"d":"M21 9v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7","key":"m87ecr"}],["line",{"x1":"16","x2":"22","y1":"5","y2":"5","key":"ez7e4s"}],["circle",{"cx":"9","cy":"9","r":"2","key":"af1f0g"}],["path",{"d":"m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21","key":"1xmnt7"}]])
export const ImageOff = ssrIcon('image-off', [["line",{"x1":"2","x2":"22","y1":"2","y2":"22","key":"a6p6uj"}],["path",{"d":"M10.41 10.41a2 2 0 1 1-2.83-2.83","key":"1bzlo9"}],["line",{"x1":"13.5","x2":"6","y1":"13.5","y2":"21","key":"1q0aeu"}],["line",{"x1":"18","x2":"21","y1":"12","y2":"15","key":"5mozeu"}],["path",{"d":"M3.59 3.59A1.99 1.99 0 0 0 3 5v14a2 2 0 0 0 2 2h14c.55 0 1.052-.22 1.41-.59","key":"mmje98"}],["path",{"d":"M21 15V5a2 2 0 0 0-2-2H9","key":"43el77"}]])
export const ImagePlay = ssrIcon('image-play', [["path",{"d":"M15 15.003a1 1 0 0 1 1.517-.859l4.997 2.997a1 1 0 0 1 0 1.718l-4.997 2.997a1 1 0 0 1-1.517-.86z","key":"nrt1m3"}],["path",{"d":"M21 12.17V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h6","key":"99hgts"}],["path",{"d":"m6 21 5-5","key":"1wyjai"}],["circle",{"cx":"9","cy":"9","r":"2","key":"af1f0g"}]])
export const ImagePlus = ssrIcon('image-plus', [["path",{"d":"M16 5h6","key":"1vod17"}],["path",{"d":"M19 2v6","key":"4bpg5p"}],["path",{"d":"M21 11.5V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7.5","key":"1ue2ih"}],["path",{"d":"m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21","key":"1xmnt7"}],["circle",{"cx":"9","cy":"9","r":"2","key":"af1f0g"}]])
export const ImageUp = ssrIcon('image-up', [["path",{"d":"M10.3 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10l-3.1-3.1a2 2 0 0 0-2.814.014L6 21","key":"9csbqa"}],["path",{"d":"m14 19.5 3-3 3 3","key":"9vmjn0"}],["path",{"d":"M17 22v-5.5","key":"1aa6fl"}],["circle",{"cx":"9","cy":"9","r":"2","key":"af1f0g"}]])
export const ImageUpscale = ssrIcon('image-upscale', [["path",{"d":"M16 3h5v5","key":"1806ms"}],["path",{"d":"M17 21h2a2 2 0 0 0 2-2","key":"130fy9"}],["path",{"d":"M21 12v3","key":"1wzk3p"}],["path",{"d":"m21 3-5 5","key":"1g5oa7"}],["path",{"d":"M3 7V5a2 2 0 0 1 2-2","key":"kk3yz1"}],["path",{"d":"m5 21 4.144-4.144a1.21 1.21 0 0 1 1.712 0L13 19","key":"fyekpt"}],["path",{"d":"M9 3h3","key":"d52fa"}],["rect",{"x":"3","y":"11","width":"10","height":"10","rx":"1","key":"1wpmix"}]])
export const Images = ssrIcon('images', [["path",{"d":"m22 11-1.296-1.296a2.4 2.4 0 0 0-3.408 0L11 16","key":"9kzy35"}],["path",{"d":"M4 8a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2","key":"1t0f0t"}],["circle",{"cx":"13","cy":"7","r":"1","fill":"currentColor","key":"1obus6"}],["rect",{"x":"8","y":"2","width":"14","height":"14","rx":"2","key":"1gvhby"}]])
export const Import = ssrIcon('import', [["path",{"d":"M12 3v12","key":"1x0j5s"}],["path",{"d":"m8 11 4 4 4-4","key":"1dohi6"}],["path",{"d":"M8 5H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-4","key":"1ywtjm"}]])
export const Inbox = ssrIcon('inbox', [["polyline",{"points":"22 12 16 12 14 15 10 15 8 12 2 12","key":"o97t9d"}],["path",{"d":"M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z","key":"oot6mr"}]])
export const ListIndentIncrease = ssrIcon('list-indent-increase', [["path",{"d":"M21 5H11","key":"us1j55"}],["path",{"d":"M21 12H11","key":"wd7e0v"}],["path",{"d":"M21 19H11","key":"saa85w"}],["path",{"d":"m3 8 4 4-4 4","key":"1a3j6y"}]])
export const ListIndentDecrease = ssrIcon('list-indent-decrease', [["path",{"d":"M21 5H11","key":"us1j55"}],["path",{"d":"M21 12H11","key":"wd7e0v"}],["path",{"d":"M21 19H11","key":"saa85w"}],["path",{"d":"m7 8-4 4 4 4","key":"o5hrat"}]])
export const IndianRupee = ssrIcon('indian-rupee', [["path",{"d":"M6 3h12","key":"ggurg9"}],["path",{"d":"M6 8h12","key":"6g4wlu"}],["path",{"d":"m6 13 8.5 8","key":"u1kupk"}],["path",{"d":"M6 13h3","key":"wdp6ag"}],["path",{"d":"M9 13c6.667 0 6.667-10 0-10","key":"1nkvk2"}]])
export const Infinity = ssrIcon('infinity', [["path",{"d":"M6 16c5 0 7-8 12-8a4 4 0 0 1 0 8c-5 0-7-8-12-8a4 4 0 1 0 0 8","key":"18ogeb"}]])
export const Info = ssrIcon('info', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"M12 16v-4","key":"1dtifu"}],["path",{"d":"M12 8h.01","key":"e9boi3"}]])
export const SquareMousePointer = ssrIcon('square-mouse-pointer', [["path",{"d":"M12.034 12.681a.498.498 0 0 1 .647-.647l9 3.5a.5.5 0 0 1-.033.943l-3.444 1.068a1 1 0 0 0-.66.66l-1.067 3.443a.5.5 0 0 1-.943.033z","key":"xwnzip"}],["path",{"d":"M21 11V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h6","key":"14rsvq"}]])
export const InspectionPanel = ssrIcon('inspection-panel', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M7 7h.01","key":"7u93v4"}],["path",{"d":"M17 7h.01","key":"14a9sn"}],["path",{"d":"M7 17h.01","key":"19xn7k"}],["path",{"d":"M17 17h.01","key":"1sd3ek"}]])
export const Italic = ssrIcon('italic', [["line",{"x1":"19","x2":"10","y1":"4","y2":"4","key":"15jd3p"}],["line",{"x1":"14","x2":"5","y1":"20","y2":"20","key":"bu0au3"}],["line",{"x1":"15","x2":"9","y1":"4","y2":"20","key":"uljnxc"}]])
export const IterationCcw = ssrIcon('iteration-ccw', [["path",{"d":"m16 14 4 4-4 4","key":"hkso8o"}],["path",{"d":"M20 10a8 8 0 1 0-8 8h8","key":"1bik7b"}]])
export const IterationCw = ssrIcon('iteration-cw', [["path",{"d":"M4 10a8 8 0 1 1 8 8H4","key":"svv66n"}],["path",{"d":"m8 22-4-4 4-4","key":"6g7gki"}]])
export const JapaneseYen = ssrIcon('japanese-yen', [["path",{"d":"M12 9.5V21m0-11.5L6 3m6 6.5L18 3","key":"2ej80x"}],["path",{"d":"M6 15h12","key":"1hwgt5"}],["path",{"d":"M6 11h12","key":"wf4gp6"}]])
export const Joystick = ssrIcon('joystick', [["path",{"d":"M21 17a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v2a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-2Z","key":"jg2n2t"}],["path",{"d":"M6 15v-2","key":"gd6mvg"}],["path",{"d":"M12 15V9","key":"8c7uyn"}],["circle",{"cx":"12","cy":"6","r":"3","key":"1gm2ql"}]])
export const Kanban = ssrIcon('kanban', [["path",{"d":"M5 3v14","key":"9nsxs2"}],["path",{"d":"M12 3v8","key":"1h2ygw"}],["path",{"d":"M19 3v18","key":"1sk56x"}]])
export const SquareKanban = ssrIcon('square-kanban', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M8 7v7","key":"1x2jlm"}],["path",{"d":"M12 7v4","key":"xawao1"}],["path",{"d":"M16 7v9","key":"1hp2iy"}]])
export const SquareDashedKanban = ssrIcon('square-dashed-kanban', [["path",{"d":"M8 7v7","key":"1x2jlm"}],["path",{"d":"M12 7v4","key":"xawao1"}],["path",{"d":"M16 7v9","key":"1hp2iy"}],["path",{"d":"M5 3a2 2 0 0 0-2 2","key":"y57alp"}],["path",{"d":"M9 3h1","key":"1yesri"}],["path",{"d":"M14 3h1","key":"1ec4yj"}],["path",{"d":"M19 3a2 2 0 0 1 2 2","key":"18rm91"}],["path",{"d":"M21 9v1","key":"mxsmne"}],["path",{"d":"M21 14v1","key":"169vum"}],["path",{"d":"M21 19a2 2 0 0 1-2 2","key":"1j7049"}],["path",{"d":"M14 21h1","key":"v9vybs"}],["path",{"d":"M9 21h1","key":"15o7lz"}],["path",{"d":"M5 21a2 2 0 0 1-2-2","key":"sbafld"}],["path",{"d":"M3 14v1","key":"vnatye"}],["path",{"d":"M3 9v1","key":"1r0deq"}]])
export const Kayak = ssrIcon('kayak', [["path",{"d":"M18 17a1 1 0 0 0-1 1v1a2 2 0 1 0 2-2z","key":"skzb1g"}],["path",{"d":"M20.97 3.61a.45.45 0 0 0-.58-.58C10.2 6.6 6.6 10.2 3.03 20.39a.45.45 0 0 0 .58.58C13.8 17.4 17.4 13.8 20.97 3.61","key":"cv9jm7"}],["path",{"d":"m6.707 6.707 10.586 10.586","key":"d2l993"}],["path",{"d":"M7 5a2 2 0 1 0-2 2h1a1 1 0 0 0 1-1z","key":"i0et4n"}]])
export const Key = ssrIcon('key', [["path",{"d":"m2 21 9.6-9.6","key":"9l79m3"}],["path",{"d":"m7.5 15.5 2.3 2.3a1 1 0 0 1 0 1.4l-2.1 2.1a1 1 0 0 1-1.4 0L4 19","key":"fw8biw"}],["circle",{"cx":"15.5","cy":"7.5","r":"5.5","key":"4wxmhb"}]])
export const KeyRound = ssrIcon('key-round', [["path",{"d":"M2.586 17.414A2 2 0 0 0 2 18.828V21a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h1a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h.172a2 2 0 0 0 1.414-.586l.814-.814a6.5 6.5 0 1 0-4-4z","key":"1s6t7t"}],["circle",{"cx":"16.5","cy":"7.5","r":".5","fill":"currentColor","key":"w0ekpg"}]])
export const KeySquare = ssrIcon('key-square', [["path",{"d":"M12.4 2.7a2.5 2.5 0 0 1 3.4 0l5.5 5.5a2.5 2.5 0 0 1 0 3.4l-3.7 3.7a2.5 2.5 0 0 1-3.4 0L8.7 9.8a2.5 2.5 0 0 1 0-3.4z","key":"165ttr"}],["path",{"d":"m14 7 3 3","key":"1r5n42"}],["path",{"d":"m9.4 10.6-6.814 6.814A2 2 0 0 0 2 18.828V21a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h1a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h.172a2 2 0 0 0 1.414-.586l.814-.814","key":"1ubxi2"}]])
export const Keyboard = ssrIcon('keyboard', [["path",{"d":"M10 8h.01","key":"1r9ogq"}],["path",{"d":"M12 12h.01","key":"1mp3jc"}],["path",{"d":"M14 8h.01","key":"1primd"}],["path",{"d":"M16 12h.01","key":"1l6xoz"}],["path",{"d":"M18 8h.01","key":"emo2bl"}],["path",{"d":"M6 8h.01","key":"x9i8wu"}],["path",{"d":"M7 16h10","key":"wp8him"}],["path",{"d":"M8 12h.01","key":"czm47f"}],["rect",{"width":"20","height":"16","x":"2","y":"4","rx":"2","key":"18n3k1"}]])
export const KeyboardMusic = ssrIcon('keyboard-music', [["rect",{"width":"20","height":"16","x":"2","y":"4","rx":"2","key":"18n3k1"}],["path",{"d":"M6 8h4","key":"utf9t1"}],["path",{"d":"M14 8h.01","key":"1primd"}],["path",{"d":"M18 8h.01","key":"emo2bl"}],["path",{"d":"M2 12h20","key":"9i4pu4"}],["path",{"d":"M6 12v4","key":"dy92yo"}],["path",{"d":"M10 12v4","key":"1fxnav"}],["path",{"d":"M14 12v4","key":"1hft58"}],["path",{"d":"M18 12v4","key":"tjjnbz"}]])
export const KeyboardOff = ssrIcon('keyboard-off', [["path",{"d":"M 20 4 A2 2 0 0 1 22 6","key":"1g1fkt"}],["path",{"d":"M 22 6 L 22 16.41","key":"1qjg3w"}],["path",{"d":"M 7 16 L 16 16","key":"n0yqwb"}],["path",{"d":"M 9.69 4 L 20 4","key":"kbpcgx"}],["path",{"d":"M14 8h.01","key":"1primd"}],["path",{"d":"M18 8h.01","key":"emo2bl"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M20 20H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2","key":"s23sx2"}],["path",{"d":"M6 8h.01","key":"x9i8wu"}],["path",{"d":"M8 12h.01","key":"czm47f"}]])
export const Lamp = ssrIcon('lamp', [["path",{"d":"M12 12v6","key":"3ahymv"}],["path",{"d":"M4.077 10.615A1 1 0 0 0 5 12h14a1 1 0 0 0 .923-1.385l-3.077-7.384A2 2 0 0 0 15 2H9a2 2 0 0 0-1.846 1.23Z","key":"1l7kg2"}],["path",{"d":"M8 20a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v1a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1z","key":"1mmzpi"}]])
export const LampCeiling = ssrIcon('lamp-ceiling', [["path",{"d":"M12 2v5","key":"nd4vlx"}],["path",{"d":"M14.829 15.998a3 3 0 1 1-5.658 0","key":"1pybiy"}],["path",{"d":"M20.92 14.606A1 1 0 0 1 20 16H4a1 1 0 0 1-.92-1.394l3-7A1 1 0 0 1 7 7h10a1 1 0 0 1 .92.606z","key":"ma1wor"}]])
export const LampDesk = ssrIcon('lamp-desk', [["path",{"d":"M10.293 2.293a1 1 0 0 1 1.414 0l2.5 2.5 5.994 1.227a1 1 0 0 1 .506 1.687l-7 7a1 1 0 0 1-1.687-.506l-1.227-5.994-2.5-2.5a1 1 0 0 1 0-1.414z","key":"sb8slu"}],["path",{"d":"m14.207 4.793-3.414 3.414","key":"m2x3oj"}],["path",{"d":"M3 20a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v1a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z","key":"8b3myj"}],["path",{"d":"m9.086 6.5-4.793 4.793a1 1 0 0 0-.18 1.17L7 18","key":"43s6cu"}]])
export const LampFloor = ssrIcon('lamp-floor', [["path",{"d":"M12 10v12","key":"6ubwww"}],["path",{"d":"M17.929 7.629A1 1 0 0 1 17 9H7a1 1 0 0 1-.928-1.371l2-5A1 1 0 0 1 9 2h6a1 1 0 0 1 .928.629z","key":"1o95gh"}],["path",{"d":"M9 22h6","key":"1rlq3v"}]])
export const LampWallDown = ssrIcon('lamp-wall-down', [["path",{"d":"M19.929 18.629A1 1 0 0 1 19 20H9a1 1 0 0 1-.928-1.371l2-5A1 1 0 0 1 11 13h6a1 1 0 0 1 .928.629z","key":"u4w2d7"}],["path",{"d":"M6 3a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z","key":"15356w"}],["path",{"d":"M8 6h4a2 2 0 0 1 2 2v5","key":"1m6m7x"}]])
export const LampWallUp = ssrIcon('lamp-wall-up', [["path",{"d":"M19.929 9.629A1 1 0 0 1 19 11H9a1 1 0 0 1-.928-1.371l2-5A1 1 0 0 1 11 4h6a1 1 0 0 1 .928.629z","key":"1uvrbf"}],["path",{"d":"M6 15a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2H5a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1z","key":"154r2a"}],["path",{"d":"M8 18h4a2 2 0 0 0 2-2v-5","key":"z9mbu0"}]])
export const LandPlot = ssrIcon('land-plot', [["path",{"d":"m12 8 6-3-6-3v10","key":"mvpnpy"}],["path",{"d":"m8 11.99-5.5 3.14a1 1 0 0 0 0 1.74l8.5 4.86a2 2 0 0 0 2 0l8.5-4.86a1 1 0 0 0 0-1.74L16 12","key":"ek95tt"}],["path",{"d":"m6.49 12.85 11.02 6.3","key":"1kt42w"}],["path",{"d":"M17.51 12.85 6.5 19.15","key":"v55bdg"}]])
export const Landmark = ssrIcon('landmark', [["path",{"d":"M10 18v-7","key":"wt116b"}],["path",{"d":"M11.119 2.205a2 2 0 0 1 1.762 0l7.84 3.846A.5.5 0 0 1 20.5 7h-17a.5.5 0 0 1-.22-.949z","key":"yxxwt6"}],["path",{"d":"M14 18v-7","key":"vav6t3"}],["path",{"d":"M18 18v-7","key":"aexdmj"}],["path",{"d":"M3 22h18","key":"8prr45"}],["path",{"d":"M6 18v-7","key":"1ivflk"}]])
export const Languages = ssrIcon('languages', [["path",{"d":"m5 8 6 6","key":"1wu5hv"}],["path",{"d":"m4 14 6-6 2-3","key":"1k1g8d"}],["path",{"d":"M2 5h12","key":"or177f"}],["path",{"d":"M7 2h1","key":"1t2jsx"}],["path",{"d":"m22 22-5-10-5 10","key":"don7ne"}],["path",{"d":"M14 18h6","key":"1m8k6r"}]])
export const Laptop = ssrIcon('laptop', [["path",{"d":"M18 5a2 2 0 0 1 2 2v8.526a2 2 0 0 0 .212.897l1.068 2.127a1 1 0 0 1-.9 1.45H3.62a1 1 0 0 1-.9-1.45l1.068-2.127A2 2 0 0 0 4 15.526V7a2 2 0 0 1 2-2z","key":"1pdavp"}],["path",{"d":"M20.054 15.987H3.946","key":"14rxg9"}]])
export const LaptopMinimal = ssrIcon('laptop-minimal', [["rect",{"width":"18","height":"12","x":"3","y":"4","rx":"2","ry":"2","key":"1qhy41"}],["line",{"x1":"2","x2":"22","y1":"20","y2":"20","key":"ni3hll"}]])
export const LaptopMinimalCheck = ssrIcon('laptop-minimal-check', [["path",{"d":"M2 20h20","key":"owomy5"}],["path",{"d":"m9 10 2 2 4-4","key":"1gnqz4"}],["rect",{"x":"3","y":"4","width":"18","height":"12","rx":"2","key":"8ur36m"}]])
export const Lasso = ssrIcon('lasso', [["path",{"d":"M3.704 14.467a10 8 0 1 1 3.115 2.375","key":"wxgc5m"}],["path",{"d":"M7 22a5 5 0 0 1-2-3.994","key":"1xp6a4"}],["circle",{"cx":"5","cy":"16","r":"2","key":"18csp3"}]])
export const LassoSelect = ssrIcon('lasso-select', [["path",{"d":"M7 22a5 5 0 0 1-2-4","key":"umushi"}],["path",{"d":"M7 16.93c.96.43 1.96.74 2.99.91","key":"ybbtv3"}],["path",{"d":"M3.34 14A6.8 6.8 0 0 1 2 10c0-4.42 4.48-8 10-8s10 3.58 10 8a7.19 7.19 0 0 1-.33 2","key":"gt5e1w"}],["path",{"d":"M5 18a2 2 0 1 0 0-4 2 2 0 0 0 0 4z","key":"bq3ynw"}],["path",{"d":"M14.33 22h-.09a.35.35 0 0 1-.24-.32v-10a.34.34 0 0 1 .33-.34c.08 0 .15.03.21.08l7.34 6a.33.33 0 0 1-.21.59h-4.49l-2.57 3.85a.35.35 0 0 1-.28.14z","key":"72q637"}]])
export const LayerArrowDown = ssrIcon('layer-arrow-down', [["path",{"d":"M12 10v10","key":"1ogziz"}],["path",{"d":"M22 10a1 1 0 01-.59.92l-5.077 2.308","key":"q38q1t"}],["path",{"d":"M22.017 10.005a1 1 0 00-.597-.916l-8.59-3.91a2 2 0 00-1.66.001L2.6 9.08a1 1 0 00-.02 1.831l5.093 2.316","key":"h1p4gn"}],["path",{"d":"m9 17 3 3 3-3","key":"l18qqt"}]])
export const LayerArrowUp = ssrIcon('layer-arrow-up', [["path",{"d":"M12 14V4","key":"1t7zjg"}],["path",{"d":"M7.674 10.774 2.58 13.09a1 1 0 000 1.822l8.6 3.91a2 2 0 001.65 0l8.58-3.9a1 1 0 00.59-.92 1 1 0 00-.59-.922l-5.078-2.308","key":"1cy4ex"}],["path",{"d":"m9 7 3-3 3 3","key":"8sjys4"}]])
export const Layers = ssrIcon('layers', [["path",{"d":"M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z","key":"zw3jo"}],["path",{"d":"M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12","key":"1wduqc"}],["path",{"d":"M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17","key":"kqbvx6"}]])
export const Layers2 = ssrIcon('layers-2', [["path",{"d":"M13 13.74a2 2 0 0 1-2 0L2.5 8.87a1 1 0 0 1 0-1.74L11 2.26a2 2 0 0 1 2 0l8.5 4.87a1 1 0 0 1 0 1.74z","key":"15q6uc"}],["path",{"d":"m20 14.285 1.5.845a1 1 0 0 1 0 1.74L13 21.74a2 2 0 0 1-2 0l-8.5-4.87a1 1 0 0 1 0-1.74l1.5-.845","key":"byia6g"}]])
export const LayersArrowDown = ssrIcon('layers-arrow-down', [["path",{"d":"M12 7v15","key":"1onnba"}],["path",{"d":"M2 12a1 1 0 00.58.91l5.093 2.316","key":"xofxlj"}],["path",{"d":"M22 12a1 1 0 01-.59.92l-5.077 2.308","key":"cc7swz"}],["path",{"d":"M8 10.37 2.6 7.91a1 1 0 010-1.831l8.57-3.9a2 2 0 011.66.001l8.59 3.91a1 1 0 010 1.831l-5.392 2.45","key":"kdwjlb"}],["path",{"d":"m9 19 3 3 3-3","key":"1fhphp"}]])
export const LayersArrowUp = ssrIcon('layers-arrow-up', [["path",{"d":"M12 12V2","key":"17ugg4"}],["path",{"d":"M2 17.002a1 1 0 00.58.91l8.6 3.91a2 2 0 001.65 0l8.58-3.9a1 1 0 00.59-.92","key":"1ke1hd"}],["path",{"d":"M7.674 8.774 2.58 11.09a1 1 0 000 1.822l8.6 3.91a2 2 0 001.65 0l8.58-3.9a1 1 0 00.59-.92 1 1 0 00-.59-.922l-5.078-2.308","key":"hlro1u"}],["path",{"d":"m9 5 3-3 3 3","key":"l8vdw6"}]])
export const LayersMinus = ssrIcon('layers-minus', [["path",{"d":"M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 .83.18 2 2 0 0 0 .83-.18l8.58-3.9a1 1 0 0 0 0-1.832z","key":"tq134k"}],["path",{"d":"M16 17h6","key":"1ook5g"}],["path",{"d":"M2.003 11.995a1 1 0 0 0 .597.915l8.58 3.91a2 2 0 0 0 .83.18","key":"8mjqed"}],["path",{"d":"M2.003 16.995a1 1 0 0 0 .597.915l8.58 3.91a2 2 0 0 0 .83.18 2 2 0 0 0 .83-.18l2.11-.96","key":"7vwz41"}],["path",{"d":"M22.018 12.004a1 1 0 0 1-.598.916l-.177.08","key":"bm5b9y"}]])
export const LayersPlus = ssrIcon('layers-plus', [["path",{"d":"M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 .83.18 2 2 0 0 0 .83-.18l8.58-3.9a1 1 0 0 0 0-1.831z","key":"zzgyd3"}],["path",{"d":"M16 17h6","key":"1ook5g"}],["path",{"d":"M19 14v6","key":"1ckrd5"}],["path",{"d":"M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 .825.178","key":"1ia9y3"}],["path",{"d":"M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l2.116-.962","key":"jksky3"}]])
export const PanelsTopLeft = ssrIcon('panels-top-left', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M9 21V9","key":"1oto5p"}]])
export const LayoutDashboard = ssrIcon('layout-dashboard', [["rect",{"width":"7","height":"9","x":"3","y":"3","rx":"1","key":"10lvy0"}],["rect",{"width":"7","height":"5","x":"14","y":"3","rx":"1","key":"16une8"}],["rect",{"width":"7","height":"9","x":"14","y":"12","rx":"1","key":"1hutg5"}],["rect",{"width":"7","height":"5","x":"3","y":"16","rx":"1","key":"ldoo1y"}]])
export const LayoutFreeform = ssrIcon('layout-freeform', [["rect",{"width":"7","height":"7","x":"3","y":"3","rx":"1","key":"1g98yp"}],["rect",{"width":"7","height":"7","x":"14","y":"4","rx":"1","key":"n7b4zl"}],["rect",{"width":"7","height":"7","x":"4","y":"14","rx":"1","key":"1ngf42"}]])
export const LayoutGrid = ssrIcon('layout-grid', [["rect",{"width":"7","height":"7","x":"3","y":"3","rx":"1","key":"1g98yp"}],["rect",{"width":"7","height":"7","x":"14","y":"3","rx":"1","key":"6d4xhi"}],["rect",{"width":"7","height":"7","x":"14","y":"14","rx":"1","key":"nxv5o0"}],["rect",{"width":"7","height":"7","x":"3","y":"14","rx":"1","key":"1bb6yr"}]])
export const LayoutList = ssrIcon('layout-list', [["rect",{"width":"7","height":"7","x":"3","y":"3","rx":"1","key":"1g98yp"}],["rect",{"width":"7","height":"7","x":"3","y":"14","rx":"1","key":"1bb6yr"}],["path",{"d":"M14 4h7","key":"3xa0d5"}],["path",{"d":"M14 9h7","key":"1icrd9"}],["path",{"d":"M14 15h7","key":"1mj8o2"}],["path",{"d":"M14 20h7","key":"11slyb"}]])
export const LayoutPanelLeft = ssrIcon('layout-panel-left', [["rect",{"width":"7","height":"18","x":"3","y":"3","rx":"1","key":"2obqm"}],["rect",{"width":"7","height":"7","x":"14","y":"3","rx":"1","key":"6d4xhi"}],["rect",{"width":"7","height":"7","x":"14","y":"14","rx":"1","key":"nxv5o0"}]])
export const LayoutPanelTop = ssrIcon('layout-panel-top', [["rect",{"width":"18","height":"7","x":"3","y":"3","rx":"1","key":"f1a2em"}],["rect",{"width":"7","height":"7","x":"3","y":"14","rx":"1","key":"1bb6yr"}],["rect",{"width":"7","height":"7","x":"14","y":"14","rx":"1","key":"nxv5o0"}]])
export const LayoutTemplate = ssrIcon('layout-template', [["rect",{"width":"18","height":"7","x":"3","y":"3","rx":"1","key":"f1a2em"}],["rect",{"width":"9","height":"7","x":"3","y":"14","rx":"1","key":"jqznyg"}],["rect",{"width":"5","height":"7","x":"16","y":"14","rx":"1","key":"q5h2i8"}]])
export const Leaf = ssrIcon('leaf', [["path",{"d":"M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z","key":"nnexq3"}],["path",{"d":"M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12","key":"mt58a7"}]])
export const LeafyGreen = ssrIcon('leafy-green', [["path",{"d":"M2 22c1.25-.987 2.27-1.975 3.9-2.2a5.56 5.56 0 0 1 3.8 1.5 4 4 0 0 0 6.187-2.353 3.5 3.5 0 0 0 3.69-5.116A3.5 3.5 0 0 0 20.95 8 3.5 3.5 0 1 0 16 3.05a3.5 3.5 0 0 0-5.831 1.373 3.5 3.5 0 0 0-5.116 3.69 4 4 0 0 0-2.348 6.155C3.499 15.42 4.409 16.712 4.2 18.1 3.926 19.743 3.014 20.732 2 22","key":"1134nt"}],["path",{"d":"M2 22 17 7","key":"1q7jp2"}]])
export const Lectern = ssrIcon('lectern', [["path",{"d":"M16 12h3a2 2 0 0 0 1.902-1.38l1.056-3.333A1 1 0 0 0 21 6H3a1 1 0 0 0-.958 1.287l1.056 3.334A2 2 0 0 0 5 12h3","key":"13jjxg"}],["path",{"d":"M18 6V3a1 1 0 0 0-1-1h-3","key":"1550fe"}],["rect",{"width":"8","height":"12","x":"8","y":"10","rx":"1","key":"qmu8b6"}]])
export const LensConcave = ssrIcon('lens-concave', [["path",{"d":"M7 2a1 1 0 0 0-.8 1.6 14 14 0 0 1 0 16.8A1 1 0 0 0 7 22h10a1 1 0 0 0 .8-1.6 14 14 0 0 1 0-16.8A1 1 0 0 0 17 2z","key":"109j23"}]])
export const LensConvex = ssrIcon('lens-convex', [["path",{"d":"M13.433 2a1 1 0 0 1 .824.448 18 18 0 0 1 0 19.104 1 1 0 0 1-.824.448h-2.866a1 1 0 0 1-.824-.448 18 18 0 0 1 0-19.104A1 1 0 0 1 10.567 2z","key":"cq67go"}]])
export const TextInitial = ssrIcon('text-initial', [["path",{"d":"M15 5h6","key":"1pr8yx"}],["path",{"d":"M15 12h6","key":"upa0zy"}],["path",{"d":"M3 19h18","key":"awlh7x"}],["path",{"d":"m3 12 3.553-7.724a.5.5 0 0 1 .894 0L11 12","key":"6lvno8"}],["path",{"d":"M3.92 10h6.16","key":"1tl8ex"}]])
export const Library = ssrIcon('library', [["path",{"d":"m16 6 4 14","key":"ji33uf"}],["path",{"d":"M12 6v14","key":"1n7gus"}],["path",{"d":"M8 8v12","key":"1gg7y9"}],["path",{"d":"M4 4v16","key":"6qkkli"}]])
export const LibraryBig = ssrIcon('library-big', [["rect",{"width":"8","height":"18","x":"3","y":"3","rx":"1","key":"oynpb5"}],["path",{"d":"M7 3v18","key":"bbkbws"}],["path",{"d":"M20.4 18.9c.2.5-.1 1.1-.6 1.3l-1.9.7c-.5.2-1.1-.1-1.3-.6L11.1 5.1c-.2-.5.1-1.1.6-1.3l1.9-.7c.5-.2 1.1.1 1.3.6Z","key":"1qboyk"}]])
export const SquareLibrary = ssrIcon('square-library', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M7 7v10","key":"d5nglc"}],["path",{"d":"M11 7v10","key":"pptsnr"}],["path",{"d":"m15 7 2 10","key":"1m7qm5"}]])
export const LifeBuoy = ssrIcon('life-buoy', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["path",{"d":"m4.93 4.93 4.24 4.24","key":"1ymg45"}],["path",{"d":"m14.83 9.17 4.24-4.24","key":"1cb5xl"}],["path",{"d":"m14.83 14.83 4.24 4.24","key":"q42g0n"}],["path",{"d":"m9.17 14.83-4.24 4.24","key":"bqpfvv"}],["circle",{"cx":"12","cy":"12","r":"4","key":"4exip2"}]])
export const Ligature = ssrIcon('ligature', [["path",{"d":"M14 12h2v8","key":"c1fccl"}],["path",{"d":"M14 20h4","key":"lzx1xo"}],["path",{"d":"M6 12h4","key":"a4o3ry"}],["path",{"d":"M6 20h4","key":"1i6q5t"}],["path",{"d":"M8 20V8a4 4 0 0 1 7.464-2","key":"wk9t6r"}]])
export const Lightbulb = ssrIcon('lightbulb', [["path",{"d":"M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5","key":"1gvzjb"}],["path",{"d":"M9 18h6","key":"x1upvd"}],["path",{"d":"M10 22h4","key":"ceow96"}]])
export const LightbulbOff = ssrIcon('lightbulb-off', [["path",{"d":"M16.8 11.2c.8-.9 1.2-2 1.2-3.2a6 6 0 0 0-9.3-5","key":"1fkcox"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M6.3 6.3a4.67 4.67 0 0 0 1.2 5.2c.7.7 1.3 1.5 1.5 2.5","key":"10m8kw"}],["path",{"d":"M9 18h6","key":"x1upvd"}],["path",{"d":"M10 22h4","key":"ceow96"}]])
export const LineDotRightHorizontal = ssrIcon('line-dot-right-horizontal', [["path",{"d":"M 3 12 L 15 12","key":"ymhu98"}],["circle",{"cx":"18","cy":"12","r":"3","key":"1kchzo"}]])
export const LineSquiggle = ssrIcon('line-squiggle', [["path",{"d":"M7 3.5c5-2 7 2.5 3 4C1.5 10 2 15 5 16c5 2 9-10 14-7s.5 13.5-4 12c-5-2.5.5-11 6-2","key":"1lrphd"}]])
export const LineStyle = ssrIcon('line-style', [["path",{"d":"M11 5h2","key":"1s6z07"}],["path",{"d":"M15 12h6","key":"upa0zy"}],["path",{"d":"M19 5h2","key":"fjylsg"}],["path",{"d":"M3 12h6","key":"ra68u1"}],["path",{"d":"M3 19h18","key":"awlh7x"}],["path",{"d":"M3 5h2","key":"1qgu90"}]])
export const Link = ssrIcon('link', [["path",{"d":"M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71","key":"1cjeqo"}],["path",{"d":"M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71","key":"19qd67"}]])
export const Link2 = ssrIcon('link-2', [["path",{"d":"M9 17H7A5 5 0 0 1 7 7h2","key":"8i5ue5"}],["path",{"d":"M15 7h2a5 5 0 1 1 0 10h-2","key":"1b9ql8"}],["line",{"x1":"8","x2":"16","y1":"12","y2":"12","key":"1jonct"}]])
export const Link2Off = ssrIcon('link-2-off', [["path",{"d":"M9 17H7A5 5 0 0 1 7 7","key":"10o201"}],["path",{"d":"M15 7h2a5 5 0 0 1 4 8","key":"1d3206"}],["line",{"x1":"8","x2":"12","y1":"12","y2":"12","key":"rvw6j4"}],["line",{"x1":"2","x2":"22","y1":"2","y2":"22","key":"a6p6uj"}]])
export const List = ssrIcon('list', [["path",{"d":"M3 5h.01","key":"18ugdj"}],["path",{"d":"M3 12h.01","key":"nlz23k"}],["path",{"d":"M3 19h.01","key":"noohij"}],["path",{"d":"M8 5h13","key":"1pao27"}],["path",{"d":"M8 12h13","key":"1za7za"}],["path",{"d":"M8 19h13","key":"m83p4d"}]])
export const ListCheck = ssrIcon('list-check', [["path",{"d":"M16 5H3","key":"m91uny"}],["path",{"d":"M16 12H3","key":"1a2rj7"}],["path",{"d":"M11 19H3","key":"zflm78"}],["path",{"d":"m15 18 2 2 4-4","key":"1szwhi"}]])
export const ListChecks = ssrIcon('list-checks', [["path",{"d":"M13 5h8","key":"a7qcls"}],["path",{"d":"M13 12h8","key":"h98zly"}],["path",{"d":"M13 19h8","key":"c3s6r1"}],["path",{"d":"m3 17 2 2 4-4","key":"1jhpwq"}],["path",{"d":"m3 7 2 2 4-4","key":"1obspn"}]])
export const ListChevronsDownUp = ssrIcon('list-chevrons-down-up', [["path",{"d":"M3 5h8","key":"18g2rq"}],["path",{"d":"M3 12h8","key":"1xfjp6"}],["path",{"d":"M3 19h8","key":"fpbke4"}],["path",{"d":"m15 5 3 3 3-3","key":"1t4thf"}],["path",{"d":"m15 19 3-3 3 3","key":"y4ckd2"}]])
export const ListChevronsUpDown = ssrIcon('list-chevrons-up-down', [["path",{"d":"M3 5h8","key":"18g2rq"}],["path",{"d":"M3 12h8","key":"1xfjp6"}],["path",{"d":"M3 19h8","key":"fpbke4"}],["path",{"d":"m15 8 3-3 3 3","key":"bc4io6"}],["path",{"d":"m15 16 3 3 3-3","key":"9wmg1l"}]])
export const ListClock = ssrIcon('list-clock', [["path",{"d":"M16 13v2.2l1.6 1","key":"1bc147"}],["path",{"d":"M3 12h3.458","key":"brzde3"}],["path",{"d":"M3 19h3.832","key":"1d2y74"}],["path",{"d":"M3 5h18","key":"1u36vt"}],["circle",{"cx":"16","cy":"15","r":"6","key":"1cvf88"}]])
export const ListCollapse = ssrIcon('list-collapse', [["path",{"d":"M10 5h11","key":"1hkqpe"}],["path",{"d":"M10 12h11","key":"6m4ad9"}],["path",{"d":"M10 19h11","key":"14g2nv"}],["path",{"d":"m3 10 3-3-3-3","key":"i7pm08"}],["path",{"d":"m3 20 3-3-3-3","key":"20gx1n"}]])
export const ListEnd = ssrIcon('list-end', [["path",{"d":"M16 5H3","key":"m91uny"}],["path",{"d":"M16 12H3","key":"1a2rj7"}],["path",{"d":"M9 19H3","key":"s61nz1"}],["path",{"d":"m16 16-3 3 3 3","key":"117b85"}],["path",{"d":"M21 5v12a2 2 0 0 1-2 2h-6","key":"hey24a"}]])
export const ListFilter = ssrIcon('list-filter', [["path",{"d":"M2 5h20","key":"1fs1ex"}],["path",{"d":"M6 12h12","key":"8npq4p"}],["path",{"d":"M9 19h6","key":"456am0"}]])
export const ListFilterPlus = ssrIcon('list-filter-plus', [["path",{"d":"M12 5H2","key":"1o22fu"}],["path",{"d":"M6 12h12","key":"8npq4p"}],["path",{"d":"M9 19h6","key":"456am0"}],["path",{"d":"M16 5h6","key":"1vod17"}],["path",{"d":"M19 8V2","key":"1wcffq"}]])
export const ListMinus = ssrIcon('list-minus', [["path",{"d":"M16 5H3","key":"m91uny"}],["path",{"d":"M11 12H3","key":"51ecnj"}],["path",{"d":"M16 19H3","key":"zzsher"}],["path",{"d":"M21 12h-6","key":"bt1uis"}]])
export const ListMusic = ssrIcon('list-music', [["path",{"d":"M16 5H3","key":"m91uny"}],["path",{"d":"M11 12H3","key":"51ecnj"}],["path",{"d":"M11 19H3","key":"zflm78"}],["path",{"d":"M21 16V5","key":"yxg4q8"}],["circle",{"cx":"18","cy":"16","r":"3","key":"1hluhg"}]])
export const ListOrdered = ssrIcon('list-ordered', [["path",{"d":"M11 5h10","key":"1cz7ny"}],["path",{"d":"M11 12h10","key":"1438ji"}],["path",{"d":"M11 19h10","key":"11t30w"}],["path",{"d":"M4 4h1v5","key":"10yrso"}],["path",{"d":"M4 9h2","key":"r1h2o0"}],["path",{"d":"M6.5 20H3.4c0-1 2.6-1.925 2.6-3.5a1.5 1.5 0 0 0-2.6-1.02","key":"xtkcd5"}]])
export const ListPlus = ssrIcon('list-plus', [["path",{"d":"M16 5H3","key":"m91uny"}],["path",{"d":"M11 12H3","key":"51ecnj"}],["path",{"d":"M16 19H3","key":"zzsher"}],["path",{"d":"M18 9v6","key":"1twb98"}],["path",{"d":"M21 12h-6","key":"bt1uis"}]])
export const ListRestart = ssrIcon('list-restart', [["path",{"d":"M21 5H3","key":"1fi0y6"}],["path",{"d":"M7 12H3","key":"13ou7f"}],["path",{"d":"M7 19H3","key":"wbqt3n"}],["path",{"d":"M12 18a5 5 0 0 0 9-3 4.5 4.5 0 0 0-4.5-4.5c-1.33 0-2.54.54-3.41 1.41L11 14","key":"qth677"}],["path",{"d":"M11 10v4h4","key":"172dkj"}]])
export const ListSortAscending = ssrIcon('list-sort-ascending', [["path",{"d":"M3 19h18","key":"awlh7x"}],["path",{"d":"M15 12H3","key":"6jk70r"}],["path",{"d":"M9 5H3","key":"15j2za"}]])
export const ListSortDescending = ssrIcon('list-sort-descending', [["path",{"d":"M15 12H3","key":"6jk70r"}],["path",{"d":"M3 5h18","key":"1u36vt"}],["path",{"d":"M9 19H3","key":"s61nz1"}]])
export const ListStart = ssrIcon('list-start', [["path",{"d":"M3 5h6","key":"1ltk0q"}],["path",{"d":"M3 12h13","key":"ppymz1"}],["path",{"d":"M3 19h13","key":"bpdczq"}],["path",{"d":"m16 8-3-3 3-3","key":"1pjpp6"}],["path",{"d":"M21 19V7a2 2 0 0 0-2-2h-6","key":"4zzq67"}]])
export const ListTodo = ssrIcon('list-todo', [["path",{"d":"M13 5h8","key":"a7qcls"}],["path",{"d":"M13 12h8","key":"h98zly"}],["path",{"d":"M13 19h8","key":"c3s6r1"}],["path",{"d":"m3 17 2 2 4-4","key":"1jhpwq"}],["rect",{"x":"3","y":"4","width":"6","height":"6","rx":"1","key":"cif1o7"}]])
export const ListTree = ssrIcon('list-tree', [["path",{"d":"M8 5h13","key":"1pao27"}],["path",{"d":"M13 12h8","key":"h98zly"}],["path",{"d":"M13 19h8","key":"c3s6r1"}],["path",{"d":"M3 10a2 2 0 0 0 2 2h3","key":"1npucw"}],["path",{"d":"M3 5v12a2 2 0 0 0 2 2h3","key":"x1gjn2"}]])
export const ListVideo = ssrIcon('list-video', [["path",{"d":"M21 5H3","key":"1fi0y6"}],["path",{"d":"M10 12H3","key":"1ulcyk"}],["path",{"d":"M10 19H3","key":"108z41"}],["path",{"d":"M15 12.003a1 1 0 0 1 1.517-.859l4.997 2.997a1 1 0 0 1 0 1.718l-4.997 2.997a1 1 0 0 1-1.517-.86z","key":"ms4nik"}]])
export const ListX = ssrIcon('list-x', [["path",{"d":"M16 5H3","key":"m91uny"}],["path",{"d":"M11 12H3","key":"51ecnj"}],["path",{"d":"M16 19H3","key":"zzsher"}],["path",{"d":"m15.5 9.5 5 5","key":"ytk86i"}],["path",{"d":"m20.5 9.5-5 5","key":"17o44f"}]])
export const Loader = ssrIcon('loader', [["path",{"d":"M12 2v4","key":"3427ic"}],["path",{"d":"m16.2 7.8 2.9-2.9","key":"r700ao"}],["path",{"d":"M18 12h4","key":"wj9ykh"}],["path",{"d":"m16.2 16.2 2.9 2.9","key":"1bxg5t"}],["path",{"d":"M12 18v4","key":"jadmvz"}],["path",{"d":"m4.9 19.1 2.9-2.9","key":"bwix9q"}],["path",{"d":"M2 12h4","key":"j09sii"}],["path",{"d":"m4.9 4.9 2.9 2.9","key":"giyufr"}]])
export const LoaderCircle = ssrIcon('loader-circle', [["path",{"d":"M21 12a9 9 0 1 1-6.219-8.56","key":"13zald"}]])
export const LoaderPinwheel = ssrIcon('loader-pinwheel', [["path",{"d":"M22 12a1 1 0 0 1-10 0 1 1 0 0 0-10 0","key":"1lzz15"}],["path",{"d":"M7 20.7a1 1 0 1 1 5-8.7 1 1 0 1 0 5-8.6","key":"1gnrpi"}],["path",{"d":"M7 3.3a1 1 0 1 1 5 8.6 1 1 0 1 0 5 8.6","key":"u9yy5q"}],["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}]])
export const Locate = ssrIcon('locate', [["line",{"x1":"2","x2":"5","y1":"12","y2":"12","key":"bvdh0s"}],["line",{"x1":"19","x2":"22","y1":"12","y2":"12","key":"1tbv5k"}],["line",{"x1":"12","x2":"12","y1":"2","y2":"5","key":"11lu5j"}],["line",{"x1":"12","x2":"12","y1":"19","y2":"22","key":"x3vr5v"}],["circle",{"cx":"12","cy":"12","r":"7","key":"fim9np"}]])
export const LocateFixed = ssrIcon('locate-fixed', [["line",{"x1":"2","x2":"5","y1":"12","y2":"12","key":"bvdh0s"}],["line",{"x1":"19","x2":"22","y1":"12","y2":"12","key":"1tbv5k"}],["line",{"x1":"12","x2":"12","y1":"2","y2":"5","key":"11lu5j"}],["line",{"x1":"12","x2":"12","y1":"19","y2":"22","key":"x3vr5v"}],["circle",{"cx":"12","cy":"12","r":"7","key":"fim9np"}],["circle",{"cx":"12","cy":"12","r":"3","key":"1v7zrd"}]])
export const LocateOff = ssrIcon('locate-off', [["path",{"d":"M12 19v3","key":"npa21l"}],["path",{"d":"M12 2v3","key":"qbqxhf"}],["path",{"d":"M18.89 13.24a7 7 0 0 0-8.13-8.13","key":"1v9jrh"}],["path",{"d":"M19 12h3","key":"osuazr"}],["path",{"d":"M2 12h3","key":"1wrr53"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M7.05 7.05a7 7 0 0 0 9.9 9.9","key":"rc5l2e"}]])
export const MapPinPen = ssrIcon('map-pin-pen', [["path",{"d":"M17.97 9.304A8 8 0 0 0 2 10c0 4.69 4.887 9.562 7.022 11.468","key":"1fahp3"}],["path",{"d":"M21.378 16.626a1 1 0 0 0-3.004-3.004l-4.01 4.012a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z","key":"1817ys"}],["circle",{"cx":"10","cy":"10","r":"3","key":"1ns7v1"}]])
export const Lock = ssrIcon('lock', [["rect",{"width":"18","height":"11","x":"3","y":"11","rx":"2","ry":"2","key":"1w4ew1"}],["path",{"d":"M7 11V7a5 5 0 0 1 10 0v4","key":"fwvmzm"}]])
export const LockKeyhole = ssrIcon('lock-keyhole', [["circle",{"cx":"12","cy":"16","r":"1","key":"1au0dj"}],["rect",{"x":"3","y":"10","width":"18","height":"12","rx":"2","key":"6s8ecr"}],["path",{"d":"M7 10V7a5 5 0 0 1 10 0v3","key":"1pqi11"}]])
export const LockKeyholeOpen = ssrIcon('lock-keyhole-open', [["circle",{"cx":"12","cy":"16","r":"1","key":"1au0dj"}],["rect",{"width":"18","height":"12","x":"3","y":"10","rx":"2","key":"l0tzu3"}],["path",{"d":"M7 10V7a5 5 0 0 1 9.33-2.5","key":"car5b7"}]])
export const LockOpen = ssrIcon('lock-open', [["rect",{"width":"18","height":"11","x":"3","y":"11","rx":"2","ry":"2","key":"1w4ew1"}],["path",{"d":"M7 11V7a5 5 0 0 1 9.9-1","key":"1mm8w8"}]])
export const LogIn = ssrIcon('log-in', [["path",{"d":"m10 17 5-5-5-5","key":"1bsop3"}],["path",{"d":"M15 12H3","key":"6jk70r"}],["path",{"d":"M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4","key":"u53s6r"}]])
export const LogOut = ssrIcon('log-out', [["path",{"d":"m16 17 5-5-5-5","key":"1bji2h"}],["path",{"d":"M21 12H9","key":"dn1m92"}],["path",{"d":"M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4","key":"1uf3rs"}]])
export const Logs = ssrIcon('logs', [["path",{"d":"M3 5h1","key":"1mv5vm"}],["path",{"d":"M3 12h1","key":"lp3yf2"}],["path",{"d":"M3 19h1","key":"w6f3n9"}],["path",{"d":"M8 5h1","key":"1nxr5w"}],["path",{"d":"M8 12h1","key":"1con00"}],["path",{"d":"M8 19h1","key":"k7p10e"}],["path",{"d":"M13 5h8","key":"a7qcls"}],["path",{"d":"M13 12h8","key":"h98zly"}],["path",{"d":"M13 19h8","key":"c3s6r1"}]])
export const Lollipop = ssrIcon('lollipop', [["circle",{"cx":"11","cy":"11","r":"8","key":"4ej97u"}],["path",{"d":"m21 21-4.3-4.3","key":"1qie3q"}],["path",{"d":"M11 11a2 2 0 0 0 4 0 4 4 0 0 0-8 0 6 6 0 0 0 12 0","key":"107gwy"}]])
export const Luggage = ssrIcon('luggage', [["path",{"d":"M6 20a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2","key":"1m57jg"}],["path",{"d":"M8 18V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v14","key":"1l99gc"}],["path",{"d":"M10 20h4","key":"ni2waw"}],["circle",{"cx":"16","cy":"20","r":"2","key":"1vifvg"}],["circle",{"cx":"8","cy":"20","r":"2","key":"ckkr5m"}]])
export const SquareM = ssrIcon('square-m', [["path",{"d":"M8 16V8.5a.5.5 0 0 1 .9-.3l2.7 3.599a.5.5 0 0 0 .8 0l2.7-3.6a.5.5 0 0 1 .9.3V16","key":"1ywlsj"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const Magnet = ssrIcon('magnet', [["path",{"d":"m12 15 4 4","key":"lnac28"}],["path",{"d":"M2.352 10.648a1.205 1.205 0 0 0 0 1.704l2.296 2.296a1.205 1.205 0 0 0 1.704 0l6.029-6.029a1 1 0 1 1 3 3l-6.029 6.029a1.205 1.205 0 0 0 0 1.704l2.296 2.296a1.205 1.205 0 0 0 1.704 0l6.365-6.367A1 1 0 0 0 8.716 4.282z","key":"nlhkjb"}],["path",{"d":"m5 8 4 4","key":"j6kj7e"}]])
export const Mail = ssrIcon('mail', [["path",{"d":"m22 7-8.991 5.727a2 2 0 0 1-2.009 0L2 7","key":"132q7q"}],["rect",{"x":"2","y":"4","width":"20","height":"16","rx":"2","key":"izxlao"}]])
export const MailBadge = ssrIcon('mail-badge', [["path",{"d":"M22 7.7V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8.25","key":"1a6dr2"}],["path",{"d":"M12 12.996a1.94 1.94 0 0 1-1.03-.296L2 7","key":"15acam"}],["path",{"d":"m20.69 16.479 1.29 4.88a.5.5 0 0 1-.698.591l-1.843-.849a1 1 0 0 0-.879.001l-1.846.85a.5.5 0 0 1-.692-.593l1.29-4.88","key":"1kx8o4"}],["circle",{"cx":"19","cy":"14","r":"3","key":"9c2nho"}]])
export const MailCheck = ssrIcon('mail-check', [["path",{"d":"M22 13V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v12c0 1.1.9 2 2 2h8","key":"12jkf8"}],["path",{"d":"m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7","key":"1ocrg3"}],["path",{"d":"m16 19 2 2 4-4","key":"1b14m6"}]])
export const MailClock = ssrIcon('mail-clock', [["path",{"d":"M16 14v2.2l1.6 1","key":"fo4ql5"}],["path",{"d":"m22 7-.759.484","key":"12ll7o"}],["path",{"d":"M6.835 20H4a2 2 0 01-2-2V6a2 2 0 012-2h16a2 2 0 012 2v2","key":"1wt3ht"}],["path",{"d":"M7.605 10.567 2 7","key":"1ducps"}],["circle",{"cx":"16","cy":"16","r":"6","key":"qoo3c4"}]])
export const MailMinus = ssrIcon('mail-minus', [["path",{"d":"M22 15V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v12c0 1.1.9 2 2 2h8","key":"fuxbkv"}],["path",{"d":"m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7","key":"1ocrg3"}],["path",{"d":"M16 19h6","key":"xwg31i"}]])
export const MailOpen = ssrIcon('mail-open', [["path",{"d":"M21.2 8.4c.5.38.8.97.8 1.6v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V10a2 2 0 0 1 .8-1.6l8-6a2 2 0 0 1 2.4 0l8 6Z","key":"1jhwl8"}],["path",{"d":"m22 10-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 10","key":"1qfld7"}]])
export const MailPlus = ssrIcon('mail-plus', [["path",{"d":"M22 13V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v12c0 1.1.9 2 2 2h8","key":"12jkf8"}],["path",{"d":"m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7","key":"1ocrg3"}],["path",{"d":"M19 16v6","key":"tddt3s"}],["path",{"d":"M16 19h6","key":"xwg31i"}]])
export const MailQuestionMark = ssrIcon('mail-question-mark', [["path",{"d":"M22 10.5V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v12c0 1.1.9 2 2 2h12.5","key":"e61zoh"}],["path",{"d":"m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7","key":"1ocrg3"}],["path",{"d":"M18 15.28c.2-.4.5-.8.9-1a2.1 2.1 0 0 1 2.6.4c.3.4.5.8.5 1.3 0 1.3-2 2-2 2","key":"7z9rxb"}],["path",{"d":"M20 22v.01","key":"12bgn6"}]])
export const MailSearch = ssrIcon('mail-search', [["path",{"d":"M22 12.5V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v12c0 1.1.9 2 2 2h7.5","key":"w80f2v"}],["path",{"d":"m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7","key":"1ocrg3"}],["path",{"d":"M18 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z","key":"8lzu5m"}],["circle",{"cx":"18","cy":"18","r":"3","key":"1xkwt0"}],["path",{"d":"m22 22-1.5-1.5","key":"1x83k4"}]])
export const MailWarning = ssrIcon('mail-warning', [["path",{"d":"M22 10.5V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v12c0 1.1.9 2 2 2h12.5","key":"e61zoh"}],["path",{"d":"m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7","key":"1ocrg3"}],["path",{"d":"M20 14v4","key":"1hm744"}],["path",{"d":"M20 22v.01","key":"12bgn6"}]])
export const MailX = ssrIcon('mail-x', [["path",{"d":"M22 12.532V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8.792","key":"8lpqwp"}],["path",{"d":"m22 7-8.991 5.727a2 2 0 0 1-2.009 0L2 7","key":"132q7q"}],["path",{"d":"m16.5 16.5 5 5","key":"zc9lw7"}],["path",{"d":"m21.5 16.5-5 5","key":"1empo3"}]])
export const Mailbox = ssrIcon('mailbox', [["path",{"d":"M22 17a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9.5C2 7 4 5 6.5 5H18c2.2 0 4 1.8 4 4v8Z","key":"1lbycx"}],["polyline",{"points":"15,9 18,9 18,11","key":"1pm9c0"}],["path",{"d":"M6.5 5C9 5 11 7 11 9.5V17a2 2 0 0 1-2 2","key":"15i455"}],["line",{"x1":"6","x2":"7","y1":"10","y2":"10","key":"1e2scm"}]])
export const Mails = ssrIcon('mails', [["path",{"d":"M17 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 1-1.732","key":"1vyzll"}],["path",{"d":"m22 5.5-6.419 4.179a2 2 0 0 1-2.162 0L7 5.5","key":"k7ramc"}],["rect",{"x":"7","y":"3","width":"15","height":"12","rx":"2","key":"17196g"}]])
export const Map = ssrIcon('map', [["path",{"d":"M14.106 5.553a2 2 0 0 0 1.788 0l3.659-1.83A1 1 0 0 1 21 4.619v12.764a1 1 0 0 1-.553.894l-4.553 2.277a2 2 0 0 1-1.788 0l-4.212-2.106a2 2 0 0 0-1.788 0l-3.659 1.83A1 1 0 0 1 3 19.381V6.618a1 1 0 0 1 .553-.894l4.553-2.277a2 2 0 0 1 1.788 0z","key":"169xi5"}],["path",{"d":"M15 5.764v15","key":"1pn4in"}],["path",{"d":"M9 3.236v15","key":"1uimfh"}]])
export const MapMinus = ssrIcon('map-minus', [["path",{"d":"m11 19-1.106-.552a2 2 0 0 0-1.788 0l-3.659 1.83A1 1 0 0 1 3 19.381V6.618a1 1 0 0 1 .553-.894l4.553-2.277a2 2 0 0 1 1.788 0l4.212 2.106a2 2 0 0 0 1.788 0l3.659-1.83A1 1 0 0 1 21 4.619V14","key":"40pylx"}],["path",{"d":"M15 5.764V14","key":"1bab71"}],["path",{"d":"M21 18h-6","key":"139f0c"}],["path",{"d":"M9 3.236v15","key":"1uimfh"}]])
export const MapPin = ssrIcon('map-pin', [["path",{"d":"M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0","key":"1r0f0z"}],["circle",{"cx":"12","cy":"10","r":"3","key":"ilqhr7"}]])
export const MapPinCheck = ssrIcon('map-pin-check', [["path",{"d":"M19.43 12.935c.357-.967.57-1.955.57-2.935a8 8 0 0 0-16 0c0 4.993 5.539 10.193 7.399 11.799a1 1 0 0 0 1.202 0 32.197 32.197 0 0 0 .813-.728","key":"1dq61d"}],["circle",{"cx":"12","cy":"10","r":"3","key":"ilqhr7"}],["path",{"d":"m16 18 2 2 4-4","key":"1mkfmb"}]])
export const MapPinCheckInside = ssrIcon('map-pin-check-inside', [["path",{"d":"M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0","key":"1r0f0z"}],["path",{"d":"m9 10 2 2 4-4","key":"1gnqz4"}]])
export const MapPinHouse = ssrIcon('map-pin-house', [["path",{"d":"M15 22a1 1 0 0 1-1-1v-4a1 1 0 0 1 .445-.832l3-2a1 1 0 0 1 1.11 0l3 2A1 1 0 0 1 22 17v4a1 1 0 0 1-1 1z","key":"1p1rcz"}],["path",{"d":"M18 10a8 8 0 0 0-16 0c0 4.993 5.539 10.193 7.399 11.799a1 1 0 0 0 .601.2","key":"mcbcs9"}],["path",{"d":"M18 22v-3","key":"1t1ugv"}],["circle",{"cx":"10","cy":"10","r":"3","key":"1ns7v1"}]])
export const MapPinMinus = ssrIcon('map-pin-minus', [["path",{"d":"M18.977 14C19.6 12.701 20 11.343 20 10a8 8 0 0 0-16 0c0 4.993 5.539 10.193 7.399 11.799a1 1 0 0 0 1.202 0 32 32 0 0 0 .824-.738","key":"11uxia"}],["circle",{"cx":"12","cy":"10","r":"3","key":"ilqhr7"}],["path",{"d":"M16 18h6","key":"987eiv"}]])
export const MapPinMinusInside = ssrIcon('map-pin-minus-inside', [["path",{"d":"M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0","key":"1r0f0z"}],["path",{"d":"M9 10h6","key":"9gxzsh"}]])
export const MapPinOff = ssrIcon('map-pin-off', [["path",{"d":"M12.75 7.09a3 3 0 0 1 2.16 2.16","key":"1d4wjd"}],["path",{"d":"M17.072 17.072c-1.634 2.17-3.527 3.912-4.471 4.727a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 1.432-4.568","key":"12yil7"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M8.475 2.818A8 8 0 0 1 20 10c0 1.183-.31 2.377-.81 3.533","key":"lhrkcz"}],["path",{"d":"M9.13 9.13a3 3 0 0 0 3.74 3.74","key":"13wojd"}]])
export const MapPinPlus = ssrIcon('map-pin-plus', [["path",{"d":"M19.914 11.105A7.298 7.298 0 0 0 20 10a8 8 0 0 0-16 0c0 4.993 5.539 10.193 7.399 11.799a1 1 0 0 0 1.202 0 32 32 0 0 0 .824-.738","key":"fcdtly"}],["circle",{"cx":"12","cy":"10","r":"3","key":"ilqhr7"}],["path",{"d":"M16 18h6","key":"987eiv"}],["path",{"d":"M19 15v6","key":"10aioa"}]])
export const MapPinPlusInside = ssrIcon('map-pin-plus-inside', [["path",{"d":"M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0","key":"1r0f0z"}],["path",{"d":"M12 7v6","key":"lw1j43"}],["path",{"d":"M9 10h6","key":"9gxzsh"}]])
export const MapPinSearch = ssrIcon('map-pin-search', [["path",{"d":"M 12.248 21.969 a 1 1 0 0 1 -0.849 -0.17 C 9.539 20.193 4 14.993 4 10 a 8 8 0 0 1 16 0 C 20 10.42 19.961 10.841 19.888 11.262","key":"1jho5b"}],["path",{"d":"m22 22-1.88-1.88","key":"1bgjp0"}],["circle",{"cx":"12","cy":"10","r":"3","key":"ilqhr7"}],["circle",{"cx":"18","cy":"18","r":"3","key":"1xkwt0"}]])
export const MapPinX = ssrIcon('map-pin-x', [["path",{"d":"M19.752 11.901A7.78 7.78 0 0 0 20 10a8 8 0 0 0-16 0c0 4.993 5.539 10.193 7.399 11.799a1 1 0 0 0 1.202 0 19 19 0 0 0 .09-.077","key":"y0ewhp"}],["circle",{"cx":"12","cy":"10","r":"3","key":"ilqhr7"}],["path",{"d":"m21.5 15.5-5 5","key":"11iqnx"}],["path",{"d":"m21.5 20.5-5-5","key":"1bylgx"}]])
export const MapPinXInside = ssrIcon('map-pin-x-inside', [["path",{"d":"M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0","key":"1r0f0z"}],["path",{"d":"m14.5 7.5-5 5","key":"3lb6iw"}],["path",{"d":"m9.5 7.5 5 5","key":"ko136h"}]])
export const MapPinned = ssrIcon('map-pinned', [["path",{"d":"M18 8c0 3.613-3.869 7.429-5.393 8.795a1 1 0 0 1-1.214 0C9.87 15.429 6 11.613 6 8a6 6 0 0 1 12 0","key":"11u0oz"}],["circle",{"cx":"12","cy":"8","r":"2","key":"1822b1"}],["path",{"d":"M8.714 14h-3.71a1 1 0 0 0-.948.683l-2.004 6A1 1 0 0 0 3 22h18a1 1 0 0 0 .948-1.316l-2-6a1 1 0 0 0-.949-.684h-3.712","key":"q8zwxj"}]])
export const MapPlus = ssrIcon('map-plus', [["path",{"d":"m11 19-1.106-.552a2 2 0 0 0-1.788 0l-3.659 1.83A1 1 0 0 1 3 19.381V6.618a1 1 0 0 1 .553-.894l4.553-2.277a2 2 0 0 1 1.788 0l4.212 2.106a2 2 0 0 0 1.788 0l3.659-1.83A1 1 0 0 1 21 4.619V12","key":"svfegj"}],["path",{"d":"M15 5.764V12","key":"1ocw4k"}],["path",{"d":"M18 15v6","key":"9wciyi"}],["path",{"d":"M21 18h-6","key":"139f0c"}],["path",{"d":"M9 3.236v15","key":"1uimfh"}]])
export const Mars = ssrIcon('mars', [["path",{"d":"M16 3h5v5","key":"1806ms"}],["path",{"d":"m21 3-6.75 6.75","key":"pv0uzu"}],["circle",{"cx":"10","cy":"14","r":"6","key":"1qwbdc"}]])
export const MarsStroke = ssrIcon('mars-stroke', [["path",{"d":"m14 6 4 4","key":"1q72g9"}],["path",{"d":"M17 3h4v4","key":"19p9u1"}],["path",{"d":"m21 3-7.75 7.75","key":"1cjbfd"}],["circle",{"cx":"9","cy":"15","r":"6","key":"bx5svt"}]])
export const Martini = ssrIcon('martini', [["path",{"d":"M12 12 4.207 4.207A.707.707 0 0 1 4.707 3h14.586a.707.707 0 0 1 .5 1.207z","key":"vxdekd"}],["path",{"d":"M12 12v10","key":"1nesaz"}],["path",{"d":"M7 22h10","key":"10w4w3"}]])
export const Maximize = ssrIcon('maximize', [["path",{"d":"M8 3H5a2 2 0 0 0-2 2v3","key":"1dcmit"}],["path",{"d":"M21 8V5a2 2 0 0 0-2-2h-3","key":"1e4gt3"}],["path",{"d":"M3 16v3a2 2 0 0 0 2 2h3","key":"wsl5sc"}],["path",{"d":"M16 21h3a2 2 0 0 0 2-2v-3","key":"18trek"}]])
export const Maximize2 = ssrIcon('maximize-2', [["path",{"d":"M15 3h6v6","key":"1q9fwt"}],["path",{"d":"m21 3-7 7","key":"1l2asr"}],["path",{"d":"m3 21 7-7","key":"tjx5ai"}],["path",{"d":"M9 21H3v-6","key":"wtvkvv"}]])
export const Medal = ssrIcon('medal', [["path",{"d":"M7.21 15 2.66 7.14a2 2 0 0 1 .13-2.2L4.4 2.8A2 2 0 0 1 6 2h12a2 2 0 0 1 1.6.8l1.6 2.14a2 2 0 0 1 .14 2.2L16.79 15","key":"143lza"}],["path",{"d":"M11 12 5.12 2.2","key":"qhuxz6"}],["path",{"d":"m13 12 5.88-9.8","key":"hbye0f"}],["path",{"d":"M8 7h8","key":"i86dvs"}],["circle",{"cx":"12","cy":"17","r":"5","key":"qbz8iq"}],["path",{"d":"M12 18v-2h-.5","key":"fawc4q"}]])
export const Megaphone = ssrIcon('megaphone', [["path",{"d":"M11 6a13 13 0 0 0 8.4-2.8A1 1 0 0 1 21 4v12a1 1 0 0 1-1.6.8A13 13 0 0 0 11 14H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z","key":"q8bfy3"}],["path",{"d":"M6 14a12 12 0 0 0 2.4 7.2 2 2 0 0 0 3.2-2.4A8 8 0 0 1 10 14","key":"1853fq"}],["path",{"d":"M8 6v8","key":"15ugcq"}]])
export const MegaphoneOff = ssrIcon('megaphone-off', [["path",{"d":"M11.636 6A13 13 0 0 0 19.4 3.2 1 1 0 0 1 21 4v11.344","key":"bycexp"}],["path",{"d":"M14.378 14.357A13 13 0 0 0 11 14H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h1","key":"1t17s6"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M6 14a12 12 0 0 0 2.4 7.2 2 2 0 0 0 3.2-2.4A8 8 0 0 1 10 14","key":"1853fq"}],["path",{"d":"M8 8v6","key":"aieo6v"}]])
export const MemoryStick = ssrIcon('memory-stick', [["path",{"d":"M12 12v-2","key":"fwoke6"}],["path",{"d":"M12 18v-2","key":"qj6yno"}],["path",{"d":"M16 12v-2","key":"heuere"}],["path",{"d":"M16 18v-2","key":"s1ct0w"}],["path",{"d":"M2 11h1.5","key":"15p63e"}],["path",{"d":"M20 18v-2","key":"12ehxp"}],["path",{"d":"M20.5 11H22","key":"khsy7a"}],["path",{"d":"M4 18v-2","key":"1c3oqr"}],["path",{"d":"M8 12v-2","key":"1mwtfd"}],["path",{"d":"M8 18v-2","key":"qcmpov"}],["rect",{"x":"2","y":"6","width":"20","height":"10","rx":"2","key":"1qcswk"}]])
export const Menu = ssrIcon('menu', [["path",{"d":"M4 5h16","key":"1tepv9"}],["path",{"d":"M4 12h16","key":"1lakjw"}],["path",{"d":"M4 19h16","key":"1djgab"}]])
export const SquareMenu = ssrIcon('square-menu', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M7 8h10","key":"1jw688"}],["path",{"d":"M7 12h10","key":"b7w52i"}],["path",{"d":"M7 16h10","key":"wp8him"}]])
export const Merge = ssrIcon('merge', [["path",{"d":"m8 6 4-4 4 4","key":"ybng9g"}],["path",{"d":"M12 2v10.3a4 4 0 0 1-1.172 2.872L4 22","key":"1hyw0i"}],["path",{"d":"m20 22-5-5","key":"1m27yz"}]])
export const MessageCircle = ssrIcon('message-circle', [["path",{"d":"M2.992 16.342a2 2 0 0 1 .094 1.167l-1.065 3.29a1 1 0 0 0 1.236 1.168l3.413-.998a2 2 0 0 1 1.099.092 10 10 0 1 0-4.777-4.719","key":"1sd12s"}]])
export const MessageCircleCheck = ssrIcon('message-circle-check', [["path",{"d":"M2.992 16.342a2 2 0 0 1 .094 1.167l-1.065 3.29a1 1 0 0 0 1.236 1.168l3.413-.998a2 2 0 0 1 1.099.092 10 10 0 1 0-4.777-4.719","key":"1sd12s"}],["path",{"d":"m16 9-5.5 5.5L8 12","key":"xofnsj"}]])
export const MessageCircleCode = ssrIcon('message-circle-code', [["path",{"d":"m10 9-3 3 3 3","key":"1oro0q"}],["path",{"d":"m14 15 3-3-3-3","key":"bz13h7"}],["path",{"d":"M2.992 16.342a2 2 0 0 1 .094 1.167l-1.065 3.29a1 1 0 0 0 1.236 1.168l3.413-.998a2 2 0 0 1 1.099.092 10 10 0 1 0-4.777-4.719","key":"1sd12s"}]])
export const MessageCircleDashed = ssrIcon('message-circle-dashed', [["path",{"d":"M10.1 2.182a10 10 0 0 1 3.8 0","key":"5ilxe3"}],["path",{"d":"M13.9 21.818a10 10 0 0 1-3.8 0","key":"11zvb9"}],["path",{"d":"M17.609 3.72a10 10 0 0 1 2.69 2.7","key":"jiglxs"}],["path",{"d":"M2.182 13.9a10 10 0 0 1 0-3.8","key":"c0bmvh"}],["path",{"d":"M20.28 17.61a10 10 0 0 1-2.7 2.69","key":"elg7ff"}],["path",{"d":"M21.818 10.1a10 10 0 0 1 0 3.8","key":"qkgqxc"}],["path",{"d":"M3.721 6.391a10 10 0 0 1 2.7-2.69","key":"1mcia2"}],["path",{"d":"m6.163 21.117-2.906.85a1 1 0 0 1-1.236-1.169l.965-2.98","key":"1qsu07"}]])
export const MessageCircleDashedCheck = ssrIcon('message-circle-dashed-check', [["path",{"d":"M10.1 2.182a10 10 0 013.8 0","key":"upsxbf"}],["path",{"d":"M13.9 21.818a10 10 0 01-3.8 0","key":"ms125y"}],["path",{"d":"M17.609 3.72a10 10 0 012.69 2.7","key":"1jzhoq"}],["path",{"d":"M2.182 13.9a10 10 0 010-3.8","key":"68e3e5"}],["path",{"d":"M20.28 17.61a10 10 0 01-2.7 2.69","key":"1m37bo"}],["path",{"d":"M21.818 10.1a10 10 0 010 3.8","key":"w6g6ls"}],["path",{"d":"M3.721 6.391a10 10 0 012.7-2.69","key":"sn8908"}],["path",{"d":"m6.163 21.117-2.906.85a1 1 0 01-1.236-1.169l.965-2.98","key":"7908cd"}],["path",{"d":"m16 9-5.5 5.5L8 12","key":"xofnsj"}]])
export const MessageCircleHeart = ssrIcon('message-circle-heart', [["path",{"d":"M2.992 16.342a2 2 0 0 1 .094 1.167l-1.065 3.29a1 1 0 0 0 1.236 1.168l3.413-.998a2 2 0 0 1 1.099.092 10 10 0 1 0-4.777-4.719","key":"1sd12s"}],["path",{"d":"M7.828 13.07A3 3 0 0 1 12 8.764a3 3 0 0 1 5.004 2.224 3 3 0 0 1-.832 2.083l-3.447 3.62a1 1 0 0 1-1.45-.001z","key":"hoo97p"}]])
export const MessageCircleMore = ssrIcon('message-circle-more', [["path",{"d":"M2.992 16.342a2 2 0 0 1 .094 1.167l-1.065 3.29a1 1 0 0 0 1.236 1.168l3.413-.998a2 2 0 0 1 1.099.092 10 10 0 1 0-4.777-4.719","key":"1sd12s"}],["path",{"d":"M8 12h.01","key":"czm47f"}],["path",{"d":"M12 12h.01","key":"1mp3jc"}],["path",{"d":"M16 12h.01","key":"1l6xoz"}]])
export const MessageCircleOff = ssrIcon('message-circle-off', [["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M4.93 4.929a10 10 0 0 0-1.938 11.412 2 2 0 0 1 .094 1.167l-1.065 3.29a1 1 0 0 0 1.236 1.168l3.413-.998a2 2 0 0 1 1.099.092 10 10 0 0 0 11.302-1.989","key":"7il5tn"}],["path",{"d":"M8.35 2.69A10 10 0 0 1 21.3 15.65","key":"1pfsoa"}]])
export const MessageCirclePlus = ssrIcon('message-circle-plus', [["path",{"d":"M2.992 16.342a2 2 0 0 1 .094 1.167l-1.065 3.29a1 1 0 0 0 1.236 1.168l3.413-.998a2 2 0 0 1 1.099.092 10 10 0 1 0-4.777-4.719","key":"1sd12s"}],["path",{"d":"M8 12h8","key":"1wcyev"}],["path",{"d":"M12 8v8","key":"napkw2"}]])
export const MessageCircleQuestionMark = ssrIcon('message-circle-question-mark', [["path",{"d":"M2.992 16.342a2 2 0 0 1 .094 1.167l-1.065 3.29a1 1 0 0 0 1.236 1.168l3.413-.998a2 2 0 0 1 1.099.092 10 10 0 1 0-4.777-4.719","key":"1sd12s"}],["path",{"d":"M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3","key":"1u773s"}],["path",{"d":"M12 17h.01","key":"p32p05"}]])
export const MessageCircleReply = ssrIcon('message-circle-reply', [["path",{"d":"M2.992 16.342a2 2 0 0 1 .094 1.167l-1.065 3.29a1 1 0 0 0 1.236 1.168l3.413-.998a2 2 0 0 1 1.099.092 10 10 0 1 0-4.777-4.719","key":"1sd12s"}],["path",{"d":"m10 15-3-3 3-3","key":"1pgupc"}],["path",{"d":"M7 12h8a2 2 0 0 1 2 2v1","key":"89sh1g"}]])
export const MessageCircleWarning = ssrIcon('message-circle-warning', [["path",{"d":"M2.992 16.342a2 2 0 0 1 .094 1.167l-1.065 3.29a1 1 0 0 0 1.236 1.168l3.413-.998a2 2 0 0 1 1.099.092 10 10 0 1 0-4.777-4.719","key":"1sd12s"}],["path",{"d":"M12 8v4","key":"1got3b"}],["path",{"d":"M12 16h.01","key":"1drbdi"}]])
export const MessageCircleX = ssrIcon('message-circle-x', [["path",{"d":"M2.992 16.342a2 2 0 0 1 .094 1.167l-1.065 3.29a1 1 0 0 0 1.236 1.168l3.413-.998a2 2 0 0 1 1.099.092 10 10 0 1 0-4.777-4.719","key":"1sd12s"}],["path",{"d":"m15 9-6 6","key":"1uzhvr"}],["path",{"d":"m9 9 6 6","key":"z0biqf"}]])
export const MessageSquare = ssrIcon('message-square', [["path",{"d":"M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z","key":"18887p"}]])
export const MessageSquareCheck = ssrIcon('message-square-check', [["path",{"d":"M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.7.7 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z","key":"m0kn7k"}],["path",{"d":"m9 11 2 2 4-4","key":"kz4plv"}]])
export const MessageSquareCode = ssrIcon('message-square-code', [["path",{"d":"M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z","key":"18887p"}],["path",{"d":"m10 8-3 3 3 3","key":"fp6dz7"}],["path",{"d":"m14 14 3-3-3-3","key":"1yrceu"}]])
export const MessageSquareDashed = ssrIcon('message-square-dashed', [["path",{"d":"M14 3h2","key":"1d12a5"}],["path",{"d":"M16 19h-2","key":"1agirb"}],["path",{"d":"M2 12v-2","key":"1ey295"}],["path",{"d":"M2 16v5.286a.71.71 0 0 0 1.212.502l1.149-1.149","key":"120k8q"}],["path",{"d":"M20 19a2 2 0 0 0 2-2v-1","key":"ior8tn"}],["path",{"d":"M22 10v2","key":"rmlecy"}],["path",{"d":"M22 6V5a2 2 0 0 0-2-2","key":"sp3k6r"}],["path",{"d":"M4 3a2 2 0 0 0-2 2v1","key":"11zt7s"}],["path",{"d":"M8 19h2","key":"jnunrx"}],["path",{"d":"M8 3h2","key":"ysbsee"}]])
export const MessageSquareDiff = ssrIcon('message-square-diff', [["path",{"d":"M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z","key":"18887p"}],["path",{"d":"M10 15h4","key":"192ueg"}],["path",{"d":"M10 9h4","key":"u4k05v"}],["path",{"d":"M12 7v4","key":"xawao1"}]])
export const MessageSquareDot = ssrIcon('message-square-dot', [["path",{"d":"M12.7 3H4a2 2 0 0 0-2 2v16.286a.71.71 0 0 0 1.212.502l2.202-2.202A2 2 0 0 1 6.828 19H20a2 2 0 0 0 2-2v-4.7","key":"wjb7ig"}],["circle",{"cx":"19","cy":"6","r":"3","key":"108a5v"}]])
export const MessageSquareHeart = ssrIcon('message-square-heart', [["path",{"d":"M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z","key":"18887p"}],["path",{"d":"M7.5 9.5c0 .687.265 1.383.697 1.844l3.009 3.264a1.14 1.14 0 0 0 .407.314 1 1 0 0 0 .783-.004 1.14 1.14 0 0 0 .398-.31l3.008-3.264A2.77 2.77 0 0 0 16.5 9.5 2.5 2.5 0 0 0 12 8a2.5 2.5 0 0 0-4.5 1.5","key":"1faxuh"}]])
export const MessageSquareLock = ssrIcon('message-square-lock', [["path",{"d":"M22 8.5V5a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v16.286a.71.71 0 0 0 1.212.502l2.202-2.202A2 2 0 0 1 6.828 19H10","key":"fu6chl"}],["path",{"d":"M20 15v-2a2 2 0 0 0-4 0v2","key":"vl8a78"}],["rect",{"x":"14","y":"15","width":"8","height":"5","rx":"1","key":"37aafw"}]])
export const MessageSquareMore = ssrIcon('message-square-more', [["path",{"d":"M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z","key":"18887p"}],["path",{"d":"M12 11h.01","key":"z322tv"}],["path",{"d":"M16 11h.01","key":"xkw8gn"}],["path",{"d":"M8 11h.01","key":"1dfujw"}]])
export const MessageSquareOff = ssrIcon('message-square-off', [["path",{"d":"M19 19H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.7.7 0 0 1 2 21.286V5a2 2 0 0 1 1.184-1.826","key":"1wyg69"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M8.656 3H20a2 2 0 0 1 2 2v11.344","key":"mhl4k6"}]])
export const MessageSquarePlus = ssrIcon('message-square-plus', [["path",{"d":"M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z","key":"18887p"}],["path",{"d":"M12 8v6","key":"1ib9pf"}],["path",{"d":"M9 11h6","key":"1fldmi"}]])
export const MessageSquareQuote = ssrIcon('message-square-quote', [["path",{"d":"M14 14a2 2 0 0 0 2-2V8h-2","key":"1r06pg"}],["path",{"d":"M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z","key":"18887p"}],["path",{"d":"M8 14a2 2 0 0 0 2-2V8H8","key":"1jzu5j"}]])
export const MessageSquareReply = ssrIcon('message-square-reply', [["path",{"d":"M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z","key":"18887p"}],["path",{"d":"m10 8-3 3 3 3","key":"fp6dz7"}],["path",{"d":"M17 14v-1a2 2 0 0 0-2-2H7","key":"1tkjnz"}]])
export const MessageSquareShare = ssrIcon('message-square-share', [["path",{"d":"M12 3H4a2 2 0 0 0-2 2v16.286a.71.71 0 0 0 1.212.502l2.202-2.202A2 2 0 0 1 6.828 19H20a2 2 0 0 0 2-2v-4","key":"11da1y"}],["path",{"d":"M16 3h6v6","key":"1bx56c"}],["path",{"d":"m16 9 6-6","key":"m4dnic"}]])
export const MessageSquareText = ssrIcon('message-square-text', [["path",{"d":"M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z","key":"18887p"}],["path",{"d":"M7 11h10","key":"1twpyw"}],["path",{"d":"M7 15h6","key":"d9of3u"}],["path",{"d":"M7 7h8","key":"af5zfr"}]])
export const MessageSquareWarning = ssrIcon('message-square-warning', [["path",{"d":"M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z","key":"18887p"}],["path",{"d":"M12 15h.01","key":"q59x07"}],["path",{"d":"M12 7v4","key":"xawao1"}]])
export const MessageSquareX = ssrIcon('message-square-x', [["path",{"d":"M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z","key":"18887p"}],["path",{"d":"m14.5 8.5-5 5","key":"19tnj2"}],["path",{"d":"m9.5 8.5 5 5","key":"1oa8ql"}]])
export const MessagesSquare = ssrIcon('messages-square', [["path",{"d":"M16 10a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 14.286V4a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z","key":"1n2ejm"}],["path",{"d":"M20 9a2 2 0 0 1 2 2v10.286a.71.71 0 0 1-1.212.502l-2.202-2.202A2 2 0 0 0 17.172 19H10a2 2 0 0 1-2-2v-1","key":"1qfcsi"}]])
export const Metronome = ssrIcon('metronome', [["path",{"d":"M12 11.4V9.1","key":"audfby"}],["path",{"d":"m12 17 6.59-6.59","key":"c0sb7j"}],["path",{"d":"m15.05 5.7-.218-.691a3 3 0 0 0-5.663 0L4.418 19.695A1 1 0 0 0 5.37 21h13.253a1 1 0 0 0 .951-1.31L18.45 16.2","key":"1pkfrk"}],["circle",{"cx":"20","cy":"9","r":"2","key":"1udoqf"}]])
export const Mic = ssrIcon('mic', [["path",{"d":"M12 19v3","key":"npa21l"}],["path",{"d":"M19 10v2a7 7 0 0 1-14 0v-2","key":"1vc78b"}],["rect",{"x":"9","y":"2","width":"6","height":"13","rx":"3","key":"s6n7sd"}]])
export const MicVocal = ssrIcon('mic-vocal', [["path",{"d":"m11 7.601-5.994 8.19a1 1 0 0 0 .1 1.298l.817.818a1 1 0 0 0 1.314.087L15.09 12","key":"80a601"}],["path",{"d":"M16.5 21.174C15.5 20.5 14.372 20 13 20c-2.058 0-3.928 2.356-6 2-2.072-.356-2.775-3.369-1.5-4.5","key":"j0ngtp"}],["circle",{"cx":"16","cy":"7","r":"5","key":"d08jfb"}]])
export const MicAudioLines = ssrIcon('mic-audio-lines', [["path",{"d":"M10 3v2.341","key":"d00509"}],["path",{"d":"M12 17v4","key":"1riwvh"}],["path",{"d":"M14 5v.341","key":"72nt6x"}],["path",{"d":"M18 5v13","key":"123xd1"}],["path",{"d":"M2 10v3","key":"1fnikh"}],["path",{"d":"M22 10v3","key":"154ddg"}],["path",{"d":"M6 6v11","key":"11sgs0"}],["path",{"d":"M9 21h6","key":"1udhl7"}],["rect",{"width":"4","height":"8","x":"10","y":"9","rx":"2","key":"1d9qhd"}]])
export const MicOff = ssrIcon('mic-off', [["path",{"d":"M12 19v3","key":"npa21l"}],["path",{"d":"M15 9.34V5a3 3 0 0 0-5.68-1.33","key":"1gzdoj"}],["path",{"d":"M16.95 16.95A7 7 0 0 1 5 12v-2","key":"cqa7eg"}],["path",{"d":"M18.89 13.23A7 7 0 0 0 19 12v-2","key":"16hl24"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M9 9v3a3 3 0 0 0 5.12 2.12","key":"r2i35w"}]])
export const MicSignal = ssrIcon('mic-signal', [["path",{"d":"M12 17v4","key":"1riwvh"}],["path",{"d":"M18 11a6 6 0 00-3-5.197","key":"1lvu40"}],["path",{"d":"M2 11a10 10 0 015-8.662","key":"bida4p"}],["path",{"d":"M22 11a10 10 0 00-5-8.662","key":"idvinr"}],["path",{"d":"M6 11a6 6 0 013-5.197","key":"17n2ii"}],["path",{"d":"M9 21h6","key":"1udhl7"}],["rect",{"x":"10","y":"9","width":"4","height":"8","rx":"2","key":"1l8p2f"}]])
export const Microchip = ssrIcon('microchip', [["path",{"d":"M10 12h4","key":"a56b0p"}],["path",{"d":"M10 17h4","key":"pvmtpo"}],["path",{"d":"M10 7h4","key":"1vgcok"}],["path",{"d":"M18 12h2","key":"quuxs7"}],["path",{"d":"M18 18h2","key":"4scel"}],["path",{"d":"M18 6h2","key":"1ptzki"}],["path",{"d":"M4 12h2","key":"1ltxp0"}],["path",{"d":"M4 18h2","key":"1xrofg"}],["path",{"d":"M4 6h2","key":"1cx33n"}],["rect",{"x":"6","y":"2","width":"12","height":"20","rx":"2","key":"749fme"}]])
export const Microscope = ssrIcon('microscope', [["path",{"d":"M6 18h8","key":"1borvv"}],["path",{"d":"M3 22h18","key":"8prr45"}],["path",{"d":"M14 22a7 7 0 1 0 0-14h-1","key":"1jwaiy"}],["path",{"d":"M9 14h2","key":"197e7h"}],["path",{"d":"M9 12a2 2 0 0 1-2-2V6h6v4a2 2 0 0 1-2 2Z","key":"1bmzmy"}],["path",{"d":"M12 6V3a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3","key":"1drr47"}]])
export const Microwave = ssrIcon('microwave', [["rect",{"width":"20","height":"15","x":"2","y":"4","rx":"2","key":"2no95f"}],["rect",{"width":"8","height":"7","x":"6","y":"8","rx":"1","key":"zh9wx"}],["path",{"d":"M18 8v7","key":"o5zi4n"}],["path",{"d":"M6 19v2","key":"1loha6"}],["path",{"d":"M18 19v2","key":"1dawf0"}]])
export const MidiPort = ssrIcon('midi-port', [["path",{"d":"M12 18h.01","key":"mhygvu"}],["path",{"d":"M15 2.458V5a1 1 0 01-1 1h-4a1 1 0 01-1-1V2.458","key":"1e2lr4"}],["path",{"d":"M16 16h.01","key":"1f9h7w"}],["path",{"d":"M18 12h.01","key":"yjnet6"}],["path",{"d":"M6 12h.01","key":"c2rlol"}],["path",{"d":"M8 16h.01","key":"18s6g9"}],["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}]])
export const Milestone = ssrIcon('milestone', [["path",{"d":"M12 13v8","key":"1l5pq0"}],["path",{"d":"M12 3v3","key":"1n5kay"}],["path",{"d":"M18.172 6a2 2 0 0 1 1.414.586l2.06 2.06a1.207 1.207 0 0 1 0 1.708l-2.06 2.06a2 2 0 0 1-1.414.586H4a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1z","key":"8gz4t4"}]])
export const Milk = ssrIcon('milk', [["path",{"d":"M8 2h8","key":"1ssgc1"}],["path",{"d":"M9 2v2.789a4 4 0 0 1-.672 2.219l-.656.984A4 4 0 0 0 7 10.212V20a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2v-9.789a4 4 0 0 0-.672-2.219l-.656-.984A4 4 0 0 1 15 4.788V2","key":"qtp12x"}],["path",{"d":"M7 15a6.472 6.472 0 0 1 5 0 6.47 6.47 0 0 0 5 0","key":"ygeh44"}]])
export const MilkOff = ssrIcon('milk-off', [["path",{"d":"M8 2h8","key":"1ssgc1"}],["path",{"d":"M9 2v1.343M15 2v2.789a4 4 0 0 0 .672 2.219l.656.984a4 4 0 0 1 .672 2.22v1.131M7.8 7.8l-.128.192A4 4 0 0 0 7 10.212V20a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2v-3","key":"y0ejgx"}],["path",{"d":"M7 15a6.47 6.47 0 0 1 5 0 6.472 6.472 0 0 0 3.435.435","key":"iaxqsy"}],["line",{"x1":"2","x2":"22","y1":"2","y2":"22","key":"a6p6uj"}]])
export const Minimize = ssrIcon('minimize', [["path",{"d":"M8 3v3a2 2 0 0 1-2 2H3","key":"hohbtr"}],["path",{"d":"M21 8h-3a2 2 0 0 1-2-2V3","key":"5jw1f3"}],["path",{"d":"M3 16h3a2 2 0 0 1 2 2v3","key":"198tvr"}],["path",{"d":"M16 21v-3a2 2 0 0 1 2-2h3","key":"ph8mxp"}]])
export const Minimize2 = ssrIcon('minimize-2', [["path",{"d":"m14 10 7-7","key":"oa77jy"}],["path",{"d":"M20 10h-6V4","key":"mjg0md"}],["path",{"d":"m3 21 7-7","key":"tjx5ai"}],["path",{"d":"M4 14h6v6","key":"rmj7iw"}]])
export const Minus = ssrIcon('minus', [["path",{"d":"M5 12h14","key":"1ays0h"}]])
export const SquareMinus = ssrIcon('square-minus', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M8 12h8","key":"1wcyev"}]])
export const MirrorRectangular = ssrIcon('mirror-rectangular', [["path",{"d":"M11 6 8 9","key":"7zt14w"}],["path",{"d":"m16 7-8 8","key":"tkgtvu"}],["rect",{"x":"4","y":"2","width":"16","height":"20","rx":"2","key":"1uxh74"}]])
export const MirrorRound = ssrIcon('mirror-round', [["path",{"d":"M10 6.6 8.6 8","key":"itrr7k"}],["path",{"d":"M12 18v4","key":"jadmvz"}],["path",{"d":"M15 7.5 9.5 13","key":"1vyrsv"}],["path",{"d":"M7 22h10","key":"10w4w3"}],["circle",{"cx":"12","cy":"10","r":"8","key":"1gshiw"}]])
export const Monitor = ssrIcon('monitor', [["rect",{"width":"20","height":"14","x":"2","y":"3","rx":"2","key":"48i651"}],["line",{"x1":"8","x2":"16","y1":"21","y2":"21","key":"1svkeh"}],["line",{"x1":"12","x2":"12","y1":"17","y2":"21","key":"vw1qmm"}]])
export const MonitorCheck = ssrIcon('monitor-check', [["path",{"d":"m9 10 2 2 4-4","key":"1gnqz4"}],["rect",{"width":"20","height":"14","x":"2","y":"3","rx":"2","key":"48i651"}],["path",{"d":"M12 17v4","key":"1riwvh"}],["path",{"d":"M8 21h8","key":"1ev6f3"}]])
export const MonitorCloud = ssrIcon('monitor-cloud', [["path",{"d":"M11 13a3 3 0 1 1 2.83-4H14a2 2 0 0 1 0 4z","key":"1da4q6"}],["path",{"d":"M12 17v4","key":"1riwvh"}],["path",{"d":"M8 21h8","key":"1ev6f3"}],["rect",{"x":"2","y":"3","width":"20","height":"14","rx":"2","key":"x3v2xh"}]])
export const MonitorCog = ssrIcon('monitor-cog', [["path",{"d":"M12 17v4","key":"1riwvh"}],["path",{"d":"m14.305 7.53.923-.382","key":"1mlnsw"}],["path",{"d":"m15.228 4.852-.923-.383","key":"82mpwg"}],["path",{"d":"m16.852 3.228-.383-.924","key":"ln4sir"}],["path",{"d":"m16.852 8.772-.383.923","key":"1dejw0"}],["path",{"d":"m19.148 3.228.383-.924","key":"192kgf"}],["path",{"d":"m19.53 9.696-.382-.924","key":"fiavlr"}],["path",{"d":"m20.772 4.852.924-.383","key":"1j8mgp"}],["path",{"d":"m20.772 7.148.924.383","key":"zix9be"}],["path",{"d":"M22 13v2a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7","key":"1tnzv8"}],["path",{"d":"M8 21h8","key":"1ev6f3"}],["circle",{"cx":"18","cy":"6","r":"3","key":"1h7g24"}]])
export const MonitorDot = ssrIcon('monitor-dot', [["path",{"d":"M12 17v4","key":"1riwvh"}],["path",{"d":"M22 12.307V15a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8.693","key":"1dx6ho"}],["path",{"d":"M8 21h8","key":"1ev6f3"}],["circle",{"cx":"19","cy":"6","r":"3","key":"108a5v"}]])
export const MonitorDown = ssrIcon('monitor-down', [["path",{"d":"M12 13V7","key":"h0r20n"}],["path",{"d":"m15 10-3 3-3-3","key":"lzhmyn"}],["rect",{"width":"20","height":"14","x":"2","y":"3","rx":"2","key":"48i651"}],["path",{"d":"M12 17v4","key":"1riwvh"}],["path",{"d":"M8 21h8","key":"1ev6f3"}]])
export const MonitorOff = ssrIcon('monitor-off', [["path",{"d":"M12 17v4","key":"1riwvh"}],["path",{"d":"M17 17H4a2 2 0 0 1-2-2V5a2 2 0 0 1 1.184-1.826","key":"cv7jms"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M8 21h8","key":"1ev6f3"}],["path",{"d":"M8.656 3H20a2 2 0 0 1 2 2v10a2 2 0 0 1-.293 1.042","key":"z8ni2w"}]])
export const MonitorPause = ssrIcon('monitor-pause', [["path",{"d":"M10 13V7","key":"1u13u9"}],["path",{"d":"M14 13V7","key":"1vj9om"}],["rect",{"width":"20","height":"14","x":"2","y":"3","rx":"2","key":"48i651"}],["path",{"d":"M12 17v4","key":"1riwvh"}],["path",{"d":"M8 21h8","key":"1ev6f3"}]])
export const MonitorPlay = ssrIcon('monitor-play', [["path",{"d":"M15.033 9.44a.647.647 0 0 1 0 1.12l-4.065 2.352a.645.645 0 0 1-.968-.56V7.648a.645.645 0 0 1 .967-.56z","key":"vbtd3f"}],["path",{"d":"M12 17v4","key":"1riwvh"}],["path",{"d":"M8 21h8","key":"1ev6f3"}],["rect",{"x":"2","y":"3","width":"20","height":"14","rx":"2","key":"x3v2xh"}]])
export const MonitorSmartphone = ssrIcon('monitor-smartphone', [["path",{"d":"M18 8V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h8","key":"10dyio"}],["path",{"d":"M10 19v-3.96 3.15","key":"1irgej"}],["path",{"d":"M7 19h5","key":"qswx4l"}],["rect",{"width":"6","height":"10","x":"16","y":"12","rx":"2","key":"1egngj"}]])
export const MonitorSpeaker = ssrIcon('monitor-speaker', [["path",{"d":"M5.5 20H8","key":"1k40s5"}],["path",{"d":"M17 9h.01","key":"1j24nn"}],["rect",{"width":"10","height":"16","x":"12","y":"4","rx":"2","key":"ixliua"}],["path",{"d":"M8 6H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h4","key":"1mp6e1"}],["circle",{"cx":"17","cy":"15","r":"1","key":"tqvash"}]])
export const MonitorStop = ssrIcon('monitor-stop', [["path",{"d":"M12 17v4","key":"1riwvh"}],["path",{"d":"M8 21h8","key":"1ev6f3"}],["rect",{"x":"2","y":"3","width":"20","height":"14","rx":"2","key":"x3v2xh"}],["rect",{"x":"9","y":"7","width":"6","height":"6","rx":"1","key":"5m2oou"}]])
export const MonitorUp = ssrIcon('monitor-up', [["path",{"d":"m9 10 3-3 3 3","key":"11gsxs"}],["path",{"d":"M12 13V7","key":"h0r20n"}],["rect",{"width":"20","height":"14","x":"2","y":"3","rx":"2","key":"48i651"}],["path",{"d":"M12 17v4","key":"1riwvh"}],["path",{"d":"M8 21h8","key":"1ev6f3"}]])
export const MonitorX = ssrIcon('monitor-x', [["path",{"d":"m14.5 12.5-5-5","key":"1jahn5"}],["path",{"d":"m9.5 12.5 5-5","key":"1k2t7b"}],["rect",{"width":"20","height":"14","x":"2","y":"3","rx":"2","key":"48i651"}],["path",{"d":"M12 17v4","key":"1riwvh"}],["path",{"d":"M8 21h8","key":"1ev6f3"}]])
export const Moon = ssrIcon('moon', [["path",{"d":"M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401","key":"kfwtm"}]])
export const MoonStar = ssrIcon('moon-star', [["path",{"d":"M18 5h4","key":"1lhgn2"}],["path",{"d":"M20 3v4","key":"1olli1"}],["path",{"d":"M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401","key":"kfwtm"}]])
export const Mop = ssrIcon('mop', [["path",{"d":"M10 22c2.761 0 5-1.79 5-4-4.42 0-4.08-5-8.5-5a1 1 0 100 9za3 3 0 01-3-3","key":"16ixf7"}],["path",{"d":"M12.5 11.5 22 2","key":"1r4cui"}],["path",{"d":"m6.98 13.02 2.665-2.664a1.21 1.21 0 011.71 0l2.29 2.288a1.21 1.21 0 010 1.712l-2.088 2.087","key":"1dw0bk"}]])
export const MopSparkles = ssrIcon('mop-sparkles', [["path",{"d":"M10 22a3 3 0 01-3-3","key":"oxdmti"}],["path",{"d":"M10 22c2.761 0 5-1.79 5-4-4.42 0-4.08-5-8.5-5a4.501 4.501 0 000 9z","key":"q53vem"}],["path",{"d":"M10 3H8","key":"mzdi2d"}],["path",{"d":"M12.5 11.5 22 2","key":"1r4cui"}],["path",{"d":"M20 13v4","key":"1ugfop"}],["path",{"d":"M22 15h-4","key":"1es58f"}],["path",{"d":"M4 5v4","key":"13jjxc"}],["path",{"d":"M6 7H2","key":"8zbtv0"}],["path",{"d":"m6.98 13.02 2.665-2.664a1.21 1.21 0 011.71 0l2.29 2.288a1.21 1.21 0 010 1.712l-2.088 2.087","key":"1dw0bk"}],["path",{"d":"M9 2v2","key":"165o2o"}]])
export const Mosque = ssrIcon('mosque', [["path",{"d":"M12.268 2a2 2 0 003.465 2","key":"3in8xp"}],["path",{"d":"M14 5 L14 8","key":"1fhhfb"}],["path",{"d":"M16 22v-3a2 2 0 00-4 0v3","key":"1p6nbd"}],["path",{"d":"M21 13c-.662-1.497-1.666-2.753-2.9-3.63C16.825 8.47 15.422 8 14 8s-2.826.47-4.1 1.37C8.668 10.248 7.663 11.504 7 13z","key":"ck3r5y"}],["path",{"d":"M3 9h4","key":"rnfnj5"}],["path",{"d":"M7 22V6a5 5 0 00-2-4 5 5 0 00-2 4v14a2 2 0 002 2h14a2 2 0 002-2v-7","key":"28kgc3"}]])
export const Motorbike = ssrIcon('motorbike', [["path",{"d":"m18 14-1-3","key":"bdajw9"}],["path",{"d":"m3 9 6 2a2 2 0 0 1 2-2h2a2 2 0 0 1 1.99 1.81","key":"f5fotj"}],["path",{"d":"M8 17h3a1 1 0 0 0 1-1 6 6 0 0 1 6-6 1 1 0 0 0 1-1v-.75A5 5 0 0 0 17 5","key":"3i90e2"}],["circle",{"cx":"19","cy":"17","r":"3","key":"1otbdv"}],["circle",{"cx":"5","cy":"17","r":"3","key":"1d8p0c"}]])
export const Mountain = ssrIcon('mountain', [["path",{"d":"m8 3 4 8 5-5 5 15H2L8 3z","key":"otkl63"}]])
export const MountainSnow = ssrIcon('mountain-snow', [["path",{"d":"m8 3 4 8 5-5 5 15H2L8 3z","key":"otkl63"}],["path",{"d":"M4.14 15.08c2.62-1.57 5.24-1.43 7.86.42 2.74 1.94 5.49 2 8.23.19","key":"1pvmmp"}]])
export const Mouse = ssrIcon('mouse', [["rect",{"x":"5","y":"2","width":"14","height":"20","rx":"7","key":"11ol66"}],["path",{"d":"M12 6v4","key":"16clxf"}]])
export const MouseLeft = ssrIcon('mouse-left', [["path",{"d":"M12 7.318V10","key":"17s7lh"}],["path",{"d":"M5 10v5a7 7 0 0 0 14 0V9c0-3.527-2.608-6.515-6-7","key":"imk5ea"}],["circle",{"cx":"7","cy":"4","r":"2","key":"ra7k3"}]])
export const MouseOff = ssrIcon('mouse-off', [["path",{"d":"M12 6v.343","key":"1gyhex"}],["path",{"d":"M18.218 18.218A7 7 0 0 1 5 15V9a7 7 0 0 1 .782-3.218","key":"ukzz01"}],["path",{"d":"M19 13.343V9A7 7 0 0 0 8.56 2.902","key":"104jy9"}],["path",{"d":"M22 22 2 2","key":"1r8tn9"}]])
export const MousePointer = ssrIcon('mouse-pointer', [["path",{"d":"M12.586 12.586 19 19","key":"ea5xo7"}],["path",{"d":"M3.688 3.037a.497.497 0 0 0-.651.651l6.5 15.999a.501.501 0 0 0 .947-.062l1.569-6.083a2 2 0 0 1 1.448-1.479l6.124-1.579a.5.5 0 0 0 .063-.947z","key":"277e5u"}]])
export const MousePointer2 = ssrIcon('mouse-pointer-2', [["path",{"d":"M4.037 4.688a.495.495 0 0 1 .651-.651l16 6.5a.5.5 0 0 1-.063.947l-6.124 1.58a2 2 0 0 0-1.438 1.435l-1.579 6.126a.5.5 0 0 1-.947.063z","key":"edeuup"}]])
export const MousePointer2Off = ssrIcon('mouse-pointer-2-off', [["path",{"d":"m15.55 8.45 5.138 2.087a.5.5 0 0 1-.063.947l-6.124 1.58a2 2 0 0 0-1.438 1.435l-1.579 6.126a.5.5 0 0 1-.947.063L8.45 15.551","key":"1qoshx"}],["path",{"d":"M22 2 2 22","key":"y4kqgn"}],["path",{"d":"m6.816 11.528-2.779-6.84a.495.495 0 0 1 .651-.651l6.84 2.779","key":"mymuvk"}]])
export const MousePointerBan = ssrIcon('mouse-pointer-ban', [["path",{"d":"M2.034 2.681a.498.498 0 0 1 .647-.647l9 3.5a.5.5 0 0 1-.033.944L8.204 7.545a1 1 0 0 0-.66.66l-1.066 3.443a.5.5 0 0 1-.944.033z","key":"11pp1i"}],["circle",{"cx":"16","cy":"16","r":"6","key":"qoo3c4"}],["path",{"d":"m11.8 11.8 8.4 8.4","key":"oogvdj"}]])
export const MousePointerClick = ssrIcon('mouse-pointer-click', [["path",{"d":"M14 4.1 12 6","key":"ita8i4"}],["path",{"d":"m5.1 8-2.9-.8","key":"1go3kf"}],["path",{"d":"m6 12-1.9 2","key":"mnht97"}],["path",{"d":"M7.2 2.2 8 5.1","key":"1cfko1"}],["path",{"d":"M9.037 9.69a.498.498 0 0 1 .653-.653l11 4.5a.5.5 0 0 1-.074.949l-4.349 1.041a1 1 0 0 0-.74.739l-1.04 4.35a.5.5 0 0 1-.95.074z","key":"s0h3yz"}]])
export const SquareDashedMousePointer = ssrIcon('square-dashed-mouse-pointer', [["path",{"d":"M12.034 12.681a.498.498 0 0 1 .647-.647l9 3.5a.5.5 0 0 1-.033.943l-3.444 1.068a1 1 0 0 0-.66.66l-1.067 3.443a.5.5 0 0 1-.943.033z","key":"xwnzip"}],["path",{"d":"M5 3a2 2 0 0 0-2 2","key":"y57alp"}],["path",{"d":"M19 3a2 2 0 0 1 2 2","key":"18rm91"}],["path",{"d":"M5 21a2 2 0 0 1-2-2","key":"sbafld"}],["path",{"d":"M9 3h1","key":"1yesri"}],["path",{"d":"M9 21h2","key":"1qve2z"}],["path",{"d":"M14 3h1","key":"1ec4yj"}],["path",{"d":"M3 9v1","key":"1r0deq"}],["path",{"d":"M21 9v2","key":"p14lih"}],["path",{"d":"M3 14v1","key":"vnatye"}]])
export const MouseRight = ssrIcon('mouse-right', [["path",{"d":"M12 7.318V10","key":"17s7lh"}],["path",{"d":"M19 10v5a7 7 0 0 1-14 0V9c0-3.527 2.608-6.515 6-7","key":"2es5nn"}],["circle",{"cx":"17","cy":"4","r":"2","key":"y5j2s2"}]])
export const Move = ssrIcon('move', [["path",{"d":"M12 2v20","key":"t6zp3m"}],["path",{"d":"m15 19-3 3-3-3","key":"11eu04"}],["path",{"d":"m19 9 3 3-3 3","key":"1mg7y2"}],["path",{"d":"M2 12h20","key":"9i4pu4"}],["path",{"d":"m5 9-3 3 3 3","key":"j64kie"}],["path",{"d":"m9 5 3-3 3 3","key":"l8vdw6"}]])
export const Move3d = ssrIcon('move-3d', [["path",{"d":"M5 3v16h16","key":"1mqmf9"}],["path",{"d":"m5 19 6-6","key":"jh6hbb"}],["path",{"d":"m2 6 3-3 3 3","key":"tkyvxa"}],["path",{"d":"m18 16 3 3-3 3","key":"1d4glt"}]])
export const MoveDiagonal = ssrIcon('move-diagonal', [["path",{"d":"M11 19H5v-6","key":"8awifj"}],["path",{"d":"M13 5h6v6","key":"7voy1q"}],["path",{"d":"M19 5 5 19","key":"wwaj1z"}]])
export const MoveDiagonal2 = ssrIcon('move-diagonal-2', [["path",{"d":"M19 13v6h-6","key":"1hxl6d"}],["path",{"d":"M5 11V5h6","key":"12e2xe"}],["path",{"d":"m5 5 14 14","key":"11anup"}]])
export const MoveDown = ssrIcon('move-down', [["path",{"d":"M8 18L12 22L16 18","key":"cskvfv"}],["path",{"d":"M12 2V22","key":"r89rzk"}]])
export const MoveDownLeft = ssrIcon('move-down-left', [["path",{"d":"M11 19H5V13","key":"1akmht"}],["path",{"d":"M19 5L5 19","key":"72u4yj"}]])
export const MoveDownRight = ssrIcon('move-down-right', [["path",{"d":"M19 13V19H13","key":"10vkzq"}],["path",{"d":"M5 5L19 19","key":"5zm2fv"}]])
export const MoveHorizontal = ssrIcon('move-horizontal', [["path",{"d":"m18 8 4 4-4 4","key":"1ak13k"}],["path",{"d":"M2 12h20","key":"9i4pu4"}],["path",{"d":"m6 8-4 4 4 4","key":"15zrgr"}]])
export const MoveLeft = ssrIcon('move-left', [["path",{"d":"M6 8L2 12L6 16","key":"kyvwex"}],["path",{"d":"M2 12H22","key":"1m8cig"}]])
export const MoveRight = ssrIcon('move-right', [["path",{"d":"M18 8L22 12L18 16","key":"1r0oui"}],["path",{"d":"M2 12H22","key":"1m8cig"}]])
export const MoveUp = ssrIcon('move-up', [["path",{"d":"M8 6L12 2L16 6","key":"1yvkyx"}],["path",{"d":"M12 2V22","key":"r89rzk"}]])
export const MoveUpLeft = ssrIcon('move-up-left', [["path",{"d":"M5 11V5H11","key":"3q78g9"}],["path",{"d":"M5 5L19 19","key":"5zm2fv"}]])
export const MoveUpRight = ssrIcon('move-up-right', [["path",{"d":"M13 5H19V11","key":"1n1gyv"}],["path",{"d":"M19 5L5 19","key":"72u4yj"}]])
export const MoveVertical = ssrIcon('move-vertical', [["path",{"d":"M12 2v20","key":"t6zp3m"}],["path",{"d":"m8 18 4 4 4-4","key":"bh5tu3"}],["path",{"d":"m8 6 4-4 4 4","key":"ybng9g"}]])
export const Music = ssrIcon('music', [["path",{"d":"M9 18V5l12-2v13","key":"1jmyc2"}],["circle",{"cx":"6","cy":"18","r":"3","key":"fqmcym"}],["circle",{"cx":"18","cy":"16","r":"3","key":"1hluhg"}]])
export const Music2 = ssrIcon('music-2', [["circle",{"cx":"8","cy":"18","r":"4","key":"1fc0mg"}],["path",{"d":"M12 18V2l7 4","key":"g04rme"}]])
export const Music3 = ssrIcon('music-3', [["circle",{"cx":"12","cy":"18","r":"4","key":"m3r9ws"}],["path",{"d":"M16 18V2","key":"40x2m5"}]])
export const Music4 = ssrIcon('music-4', [["path",{"d":"M9 18V5l12-2v13","key":"1jmyc2"}],["path",{"d":"m9 9 12-2","key":"1e64n2"}],["circle",{"cx":"6","cy":"18","r":"3","key":"fqmcym"}],["circle",{"cx":"18","cy":"16","r":"3","key":"1hluhg"}]])
export const Navigation = ssrIcon('navigation', [["polygon",{"points":"3 11 22 2 13 21 11 13 3 11","key":"1ltx0t"}]])
export const Navigation2 = ssrIcon('navigation-2', [["polygon",{"points":"12 2 19 21 12 17 5 21 12 2","key":"x8c0qg"}]])
export const Navigation2Off = ssrIcon('navigation-2-off', [["path",{"d":"M9.31 9.31 5 21l7-4 7 4-1.17-3.17","key":"qoq2o2"}],["path",{"d":"M14.53 8.88 12 2l-1.17 3.17","key":"k3sjzy"}],["line",{"x1":"2","x2":"22","y1":"2","y2":"22","key":"a6p6uj"}]])
export const NavigationOff = ssrIcon('navigation-off', [["path",{"d":"M8.43 8.43 3 11l8 2 2 8 2.57-5.43","key":"1vdtb7"}],["path",{"d":"M17.39 11.73 22 2l-9.73 4.61","key":"tya3r6"}],["line",{"x1":"2","x2":"22","y1":"2","y2":"22","key":"a6p6uj"}]])
export const Network = ssrIcon('network', [["rect",{"x":"16","y":"16","width":"6","height":"6","rx":"1","key":"4q2zg0"}],["rect",{"x":"2","y":"16","width":"6","height":"6","rx":"1","key":"8cvhb9"}],["rect",{"x":"9","y":"2","width":"6","height":"6","rx":"1","key":"1egb70"}],["path",{"d":"M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3","key":"1jsf9p"}],["path",{"d":"M12 12V8","key":"2874zd"}]])
export const Newspaper = ssrIcon('newspaper', [["path",{"d":"M15 18h-5","key":"95g1m2"}],["path",{"d":"M18 14h-8","key":"sponae"}],["path",{"d":"M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-4 0v-9a2 2 0 0 1 2-2h2","key":"39pd36"}],["rect",{"width":"8","height":"4","x":"10","y":"6","rx":"1","key":"aywv1n"}]])
export const Nfc = ssrIcon('nfc', [["path",{"d":"M6 8.32a7.43 7.43 0 0 1 0 7.36","key":"9iaqei"}],["path",{"d":"M9.46 6.21a11.76 11.76 0 0 1 0 11.58","key":"1yha7l"}],["path",{"d":"M12.91 4.1a15.91 15.91 0 0 1 .01 15.8","key":"4iu2gk"}],["path",{"d":"M16.37 2a20.16 20.16 0 0 1 0 20","key":"sap9u2"}]])
export const NonBinary = ssrIcon('non-binary', [["path",{"d":"M12 2v10","key":"mnfbl"}],["path",{"d":"m8.5 4 7 4","key":"m1xjk3"}],["path",{"d":"m8.5 8 7-4","key":"t0m5j6"}],["circle",{"cx":"12","cy":"17","r":"5","key":"qbz8iq"}]])
export const Notebook = ssrIcon('notebook', [["path",{"d":"M2 6h4","key":"aawbzj"}],["path",{"d":"M2 10h4","key":"l0bgd4"}],["path",{"d":"M2 14h4","key":"1gsvsf"}],["path",{"d":"M2 18h4","key":"1bu2t1"}],["rect",{"width":"16","height":"20","x":"4","y":"2","rx":"2","key":"1nb95v"}],["path",{"d":"M16 2v20","key":"rotuqe"}]])
export const NotebookPen = ssrIcon('notebook-pen', [["path",{"d":"M13.4 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7.4","key":"re6nr2"}],["path",{"d":"M2 6h4","key":"aawbzj"}],["path",{"d":"M2 10h4","key":"l0bgd4"}],["path",{"d":"M2 14h4","key":"1gsvsf"}],["path",{"d":"M2 18h4","key":"1bu2t1"}],["path",{"d":"M21.378 5.626a1 1 0 1 0-3.004-3.004l-5.01 5.012a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z","key":"pqwjuv"}]])
export const NotebookTabs = ssrIcon('notebook-tabs', [["path",{"d":"M2 6h4","key":"aawbzj"}],["path",{"d":"M2 10h4","key":"l0bgd4"}],["path",{"d":"M2 14h4","key":"1gsvsf"}],["path",{"d":"M2 18h4","key":"1bu2t1"}],["rect",{"width":"16","height":"20","x":"4","y":"2","rx":"2","key":"1nb95v"}],["path",{"d":"M15 2v20","key":"dcj49h"}],["path",{"d":"M15 7h5","key":"1xj5lc"}],["path",{"d":"M15 12h5","key":"w5shd9"}],["path",{"d":"M15 17h5","key":"1qaofu"}]])
export const NotebookText = ssrIcon('notebook-text', [["path",{"d":"M2 6h4","key":"aawbzj"}],["path",{"d":"M2 10h4","key":"l0bgd4"}],["path",{"d":"M2 14h4","key":"1gsvsf"}],["path",{"d":"M2 18h4","key":"1bu2t1"}],["rect",{"width":"16","height":"20","x":"4","y":"2","rx":"2","key":"1nb95v"}],["path",{"d":"M9.5 8h5","key":"11mslq"}],["path",{"d":"M9.5 12H16","key":"ktog6x"}],["path",{"d":"M9.5 16H14","key":"p1seyn"}]])
export const NotepadText = ssrIcon('notepad-text', [["path",{"d":"M8 2v4","key":"1cmpym"}],["path",{"d":"M12 2v4","key":"3427ic"}],["path",{"d":"M16 2v4","key":"4m81vk"}],["rect",{"width":"16","height":"18","x":"4","y":"4","rx":"2","key":"1u9h20"}],["path",{"d":"M8 10h6","key":"3oa6kw"}],["path",{"d":"M8 14h8","key":"1fgep2"}],["path",{"d":"M8 18h5","key":"17enja"}]])
export const NotepadTextDashed = ssrIcon('notepad-text-dashed', [["path",{"d":"M8 2v4","key":"1cmpym"}],["path",{"d":"M12 2v4","key":"3427ic"}],["path",{"d":"M16 2v4","key":"4m81vk"}],["path",{"d":"M16 4h2a2 2 0 0 1 2 2v2","key":"j91f56"}],["path",{"d":"M20 12v2","key":"w8o0tu"}],["path",{"d":"M20 18v2a2 2 0 0 1-2 2h-1","key":"1c9ggx"}],["path",{"d":"M13 22h-2","key":"191ugt"}],["path",{"d":"M7 22H6a2 2 0 0 1-2-2v-2","key":"1rt9px"}],["path",{"d":"M4 14v-2","key":"1v0sqh"}],["path",{"d":"M4 8V6a2 2 0 0 1 2-2h2","key":"1mwabg"}],["path",{"d":"M8 10h6","key":"3oa6kw"}],["path",{"d":"M8 14h8","key":"1fgep2"}],["path",{"d":"M8 18h5","key":"17enja"}]])
export const Nut = ssrIcon('nut', [["path",{"d":"M12 4V2","key":"1k5q1u"}],["path",{"d":"M5 10v4a7.004 7.004 0 0 0 5.277 6.787c.412.104.802.292 1.102.592L12 22l.621-.621c.3-.3.69-.488 1.102-.592A7.003 7.003 0 0 0 19 14v-4","key":"1tgyif"}],["path",{"d":"M12 4C8 4 4.5 6 4 8c-.243.97-.919 1.952-2 3 1.31-.082 1.972-.29 3-1 .54.92.982 1.356 2 2 1.452-.647 1.954-1.098 2.5-2 .595.995 1.151 1.427 2.5 2 1.31-.621 1.862-1.058 2.5-2 .629.977 1.162 1.423 2.5 2 1.209-.548 1.68-.967 2-2 1.032.916 1.683 1.157 3 1-1.297-1.036-1.758-2.03-2-3-.5-2-4-4-8-4Z","key":"tnsqj"}]])
export const NutOff = ssrIcon('nut-off', [["path",{"d":"M12 4V2","key":"1k5q1u"}],["path",{"d":"M5 10v4a7.004 7.004 0 0 0 5.277 6.787c.412.104.802.292 1.102.592L12 22l.621-.621c.3-.3.69-.488 1.102-.592a7.01 7.01 0 0 0 4.125-2.939","key":"1xcvy9"}],["path",{"d":"M19 10v3.343","key":"163tfc"}],["path",{"d":"M12 12c-1.349-.573-1.905-1.005-2.5-2-.546.902-1.048 1.353-2.5 2-1.018-.644-1.46-1.08-2-2-1.028.71-1.69.918-3 1 1.081-1.048 1.757-2.03 2-3 .194-.776.84-1.551 1.79-2.21m11.654 5.997c.887-.457 1.28-.891 1.556-1.787 1.032.916 1.683 1.157 3 1-1.297-1.036-1.758-2.03-2-3-.5-2-4-4-8-4-.74 0-1.461.068-2.15.192","key":"17914v"}],["line",{"x1":"2","x2":"22","y1":"2","y2":"22","key":"a6p6uj"}]])
export const Octagon = ssrIcon('octagon', [["path",{"d":"M2.586 16.726A2 2 0 0 1 2 15.312V8.688a2 2 0 0 1 .586-1.414l4.688-4.688A2 2 0 0 1 8.688 2h6.624a2 2 0 0 1 1.414.586l4.688 4.688A2 2 0 0 1 22 8.688v6.624a2 2 0 0 1-.586 1.414l-4.688 4.688a2 2 0 0 1-1.414.586H8.688a2 2 0 0 1-1.414-.586z","key":"2d38gg"}]])
export const OctagonMinus = ssrIcon('octagon-minus', [["path",{"d":"M2.586 16.726A2 2 0 0 1 2 15.312V8.688a2 2 0 0 1 .586-1.414l4.688-4.688A2 2 0 0 1 8.688 2h6.624a2 2 0 0 1 1.414.586l4.688 4.688A2 2 0 0 1 22 8.688v6.624a2 2 0 0 1-.586 1.414l-4.688 4.688a2 2 0 0 1-1.414.586H8.688a2 2 0 0 1-1.414-.586z","key":"2d38gg"}],["path",{"d":"M8 12h8","key":"1wcyev"}]])
export const OctagonPause = ssrIcon('octagon-pause', [["path",{"d":"M10 15V9","key":"1lckn7"}],["path",{"d":"M14 15V9","key":"1muqhk"}],["path",{"d":"M2.586 16.726A2 2 0 0 1 2 15.312V8.688a2 2 0 0 1 .586-1.414l4.688-4.688A2 2 0 0 1 8.688 2h6.624a2 2 0 0 1 1.414.586l4.688 4.688A2 2 0 0 1 22 8.688v6.624a2 2 0 0 1-.586 1.414l-4.688 4.688a2 2 0 0 1-1.414.586H8.688a2 2 0 0 1-1.414-.586z","key":"2d38gg"}]])
export const OctagonX = ssrIcon('octagon-x', [["path",{"d":"m15 9-6 6","key":"1uzhvr"}],["path",{"d":"M2.586 16.726A2 2 0 0 1 2 15.312V8.688a2 2 0 0 1 .586-1.414l4.688-4.688A2 2 0 0 1 8.688 2h6.624a2 2 0 0 1 1.414.586l4.688 4.688A2 2 0 0 1 22 8.688v6.624a2 2 0 0 1-.586 1.414l-4.688 4.688a2 2 0 0 1-1.414.586H8.688a2 2 0 0 1-1.414-.586z","key":"2d38gg"}],["path",{"d":"m9 9 6 6","key":"z0biqf"}]])
export const Omega = ssrIcon('omega', [["path",{"d":"M3 20h4.5a.5.5 0 0 0 .5-.5v-.282a.52.52 0 0 0-.247-.437 8 8 0 1 1 8.494-.001.52.52 0 0 0-.247.438v.282a.5.5 0 0 0 .5.5H21","key":"1x94xo"}]])
export const Option = ssrIcon('option', [["path",{"d":"M14 3h7","key":"16f0ms"}],["path",{"d":"M3 3h5.28a1 1 0 0 1 .948.684l5.544 16.632a1 1 0 0 0 .949.684H21","key":"1qf1im"}]])
export const Orbit = ssrIcon('orbit', [["path",{"d":"M20.341 6.484A10 10 0 0 1 10.266 21.85","key":"1enhxb"}],["path",{"d":"M3.659 17.516A10 10 0 0 1 13.74 2.152","key":"1crzgf"}],["circle",{"cx":"12","cy":"12","r":"3","key":"1v7zrd"}],["circle",{"cx":"19","cy":"5","r":"2","key":"mhkx31"}],["circle",{"cx":"5","cy":"19","r":"2","key":"v8kfzx"}]])
export const Origami = ssrIcon('origami', [["path",{"d":"M12 12V4a1 1 0 0 1 1-1h6.297a1 1 0 0 1 .651 1.759l-4.696 4.025","key":"1bx4vc"}],["path",{"d":"m12 21-7.414-7.414A2 2 0 0 1 4 12.172V6.415a1.002 1.002 0 0 1 1.707-.707L20 20.009","key":"1h3km6"}],["path",{"d":"m12.214 3.381 8.414 14.966a1 1 0 0 1-.167 1.199l-1.168 1.163a1 1 0 0 1-.706.291H6.351a1 1 0 0 1-.625-.219L3.25 18.8a1 1 0 0 1 .631-1.781l4.165.027","key":"1hj4wg"}]])
export const Package = ssrIcon('package', [["path",{"d":"M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z","key":"1a0edw"}],["path",{"d":"M12 22V12","key":"d0xqtd"}],["polyline",{"points":"3.29 7 12 12 20.71 7","key":"ousv84"}],["path",{"d":"m7.5 4.27 9 5.15","key":"1c824w"}]])
export const Package2 = ssrIcon('package-2', [["path",{"d":"M12 3v6","key":"1holv5"}],["path",{"d":"M16.76 3a2 2 0 0 1 1.8 1.1l2.23 4.479a2 2 0 0 1 .21.891V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9.472a2 2 0 0 1 .211-.894L5.45 4.1A2 2 0 0 1 7.24 3z","key":"187q7i"}],["path",{"d":"M3.054 9.013h17.893","key":"grwhos"}]])
export const PackageCheck = ssrIcon('package-check', [["path",{"d":"M12 22V12","key":"d0xqtd"}],["path",{"d":"m16 17 2 2 4-4","key":"uh5qu3"}],["path",{"d":"M21 11.127V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.729l7 4a2 2 0 0 0 2 .001l1.32-.753","key":"kpkbpo"}],["path",{"d":"M3.29 7 12 12l8.71-5","key":"19ckod"}],["path",{"d":"m7.5 4.27 8.997 5.148","key":"9yrvtv"}]])
export const PackageMinus = ssrIcon('package-minus', [["path",{"d":"M12 22V12","key":"d0xqtd"}],["path",{"d":"M16 17h6","key":"1ook5g"}],["path",{"d":"M21 13V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.729l7 4a2 2 0 0 0 2 .001l1.675-.955","key":"zu9avd"}],["path",{"d":"M3.29 7 12 12l8.71-5","key":"19ckod"}],["path",{"d":"m7.5 4.27 8.997 5.148","key":"9yrvtv"}]])
export const PackageOpen = ssrIcon('package-open', [["path",{"d":"M12 22v-9","key":"x3hkom"}],["path",{"d":"M15.17 2.21a1.67 1.67 0 0 1 1.63 0L21 4.57a1.93 1.93 0 0 1 0 3.36L8.82 14.79a1.655 1.655 0 0 1-1.64 0L3 12.43a1.93 1.93 0 0 1 0-3.36z","key":"2ntwy6"}],["path",{"d":"M20 13v3.87a2.06 2.06 0 0 1-1.11 1.83l-6 3.08a1.93 1.93 0 0 1-1.78 0l-6-3.08A2.06 2.06 0 0 1 4 16.87V13","key":"1pmm1c"}],["path",{"d":"M21 12.43a1.93 1.93 0 0 0 0-3.36L8.83 2.2a1.64 1.64 0 0 0-1.63 0L3 4.57a1.93 1.93 0 0 0 0 3.36l12.18 6.86a1.636 1.636 0 0 0 1.63 0z","key":"12ttoo"}]])
export const PackagePlus = ssrIcon('package-plus', [["path",{"d":"M12 22V12","key":"d0xqtd"}],["path",{"d":"M16 17h6","key":"1ook5g"}],["path",{"d":"M19 14v6","key":"1ckrd5"}],["path",{"d":"M21 10.535V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.729l7 4a2 2 0 0 0 2 .001l1.675-.955","key":"28k6lz"}],["path",{"d":"M3.29 7 12 12l8.71-5","key":"19ckod"}],["path",{"d":"m7.5 4.27 8.997 5.148","key":"9yrvtv"}]])
export const PackageSearch = ssrIcon('package-search', [["path",{"d":"M12 22V12","key":"d0xqtd"}],["path",{"d":"M20.27 18.27 22 20","key":"er2am"}],["path",{"d":"M21 10.498V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.729l7 4a2 2 0 0 0 2 .001l.98-.559","key":"tok1h1"}],["path",{"d":"M3.29 7 12 12l8.71-5","key":"19ckod"}],["path",{"d":"m7.5 4.27 8.997 5.148","key":"9yrvtv"}],["circle",{"cx":"18.5","cy":"16.5","r":"2.5","key":"ke13xx"}]])
export const PackageX = ssrIcon('package-x', [["path",{"d":"M12 22V12","key":"d0xqtd"}],["path",{"d":"m16.5 14.5 5 5","key":"ozpm51"}],["path",{"d":"m16.5 19.5 5-5","key":"syf6b9"}],["path",{"d":"M21 10.5V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.729l7 4a2 2 0 0 0 2 .001l.13-.074","key":"isw6gs"}],["path",{"d":"M3.29 7 12 12l8.71-5","key":"19ckod"}],["path",{"d":"m7.5 4.27 8.997 5.148","key":"9yrvtv"}]])
export const PaintBucket = ssrIcon('paint-bucket', [["path",{"d":"M11 7 6 2","key":"1jwth8"}],["path",{"d":"M18.992 12H2.041","key":"xw1gg"}],["path",{"d":"M21.145 18.38A3.34 3.34 0 0 1 20 16.5a3.3 3.3 0 0 1-1.145 1.88c-.575.46-.855 1.02-.855 1.595A2 2 0 0 0 20 22a2 2 0 0 0 2-2.025c0-.58-.285-1.13-.855-1.595","key":"1nkol4"}],["path",{"d":"m8.5 4.5 2.148-2.148a1.205 1.205 0 0 1 1.704 0l7.296 7.296a1.205 1.205 0 0 1 0 1.704l-7.592 7.592a3.615 3.615 0 0 1-5.112 0l-3.888-3.888a3.615 3.615 0 0 1 0-5.112L5.67 7.33","key":"1nk1rd"}]])
export const PaintRoller = ssrIcon('paint-roller', [["rect",{"width":"16","height":"6","x":"2","y":"2","rx":"2","key":"jcyz7m"}],["path",{"d":"M10 16v-2a2 2 0 0 1 2-2h8a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2","key":"1b9h7c"}],["rect",{"width":"4","height":"6","x":"8","y":"16","rx":"1","key":"d6e7yl"}]])
export const Paintbrush = ssrIcon('paintbrush', [["path",{"d":"m14.622 17.897-10.68-2.913","key":"vj2p1u"}],["path",{"d":"M18.376 2.622a1 1 0 1 1 3.002 3.002L17.36 9.643a.5.5 0 0 0 0 .707l.944.944a2.41 2.41 0 0 1 0 3.408l-.944.944a.5.5 0 0 1-.707 0L8.354 7.348a.5.5 0 0 1 0-.707l.944-.944a2.41 2.41 0 0 1 3.408 0l.944.944a.5.5 0 0 0 .707 0z","key":"18tc5c"}],["path",{"d":"M9 8c-1.804 2.71-3.97 3.46-6.583 3.948a.507.507 0 0 0-.302.819l7.32 8.883a1 1 0 0 0 1.185.204C12.735 20.405 16 16.792 16 15","key":"ytzfxy"}]])
export const PaintbrushVertical = ssrIcon('paintbrush-vertical', [["path",{"d":"M10 2v2","key":"7u0qdc"}],["path",{"d":"M14 2v4","key":"qmzblu"}],["path",{"d":"M17 2a1 1 0 0 1 1 1v9H6V3a1 1 0 0 1 1-1z","key":"ycvu00"}],["path",{"d":"M6 12a1 1 0 0 0-1 1v1a2 2 0 0 0 2 2h2a1 1 0 0 1 1 1v2.9a2 2 0 1 0 4 0V17a1 1 0 0 1 1-1h2a2 2 0 0 0 2-2v-1a1 1 0 0 0-1-1","key":"iw4wnp"}]])
export const Palette = ssrIcon('palette', [["path",{"d":"M12 22a1 1 0 0 1 0-20 10 9 0 0 1 10 9 5 5 0 0 1-5 5h-2.25a1.75 1.75 0 0 0-1.4 2.8l.3.4a1.75 1.75 0 0 1-1.4 2.8z","key":"e79jfc"}],["circle",{"cx":"13.5","cy":"6.5","r":".5","fill":"currentColor","key":"1okk4w"}],["circle",{"cx":"17.5","cy":"10.5","r":".5","fill":"currentColor","key":"f64h9f"}],["circle",{"cx":"6.5","cy":"12.5","r":".5","fill":"currentColor","key":"qy21gx"}],["circle",{"cx":"8.5","cy":"7.5","r":".5","fill":"currentColor","key":"fotxhn"}]])
export const TreePalm = ssrIcon('tree-palm', [["path",{"d":"M13 8c0-2.76-2.46-5-5.5-5S2 5.24 2 8h2l1-1 1 1h4","key":"foxbe7"}],["path",{"d":"M13 7.14A5.82 5.82 0 0 1 16.5 6c3.04 0 5.5 2.24 5.5 5h-3l-1-1-1 1h-3","key":"18arnh"}],["path",{"d":"M5.89 9.71c-2.15 2.15-2.3 5.47-.35 7.43l4.24-4.25.7-.7.71-.71 2.12-2.12c-1.95-1.96-5.27-1.8-7.42.35","key":"ywahnh"}],["path",{"d":"M11 15.5c.5 2.5-.17 4.5-1 6.5h4c2-5.5-.5-12-1-14","key":"ft0feo"}]])
export const Panda = ssrIcon('panda', [["path",{"d":"M11.25 17.25h1.5L12 18z","key":"1wmwwj"}],["path",{"d":"m15 12 2 2","key":"k60wz4"}],["path",{"d":"M17.902 6.599a8 8 0 0 0-.5-.5","key":"1hpval"}],["path",{"d":"M2 14.5C2 19.47 6.48 22 12 22s10-2.53 10-7.5a10 10 0 0 0-1.3-4.83 4.5 4.5 0 1 0-7.05-5.5 8 8 0 0 0-3.3 0 4.5 4.5 0 1 0-7.04 5.5A10 10 0 0 0 2 14.5","key":"fsvxqb"}],["path",{"d":"M6.099 6.599a8 8 0 0 1 .5-.5","key":"1mh6nx"}],["path",{"d":"m9 12-2 2","key":"326nkw"}]])
export const PanelBottom = ssrIcon('panel-bottom', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M3 15h18","key":"5xshup"}]])
export const PanelBottomClose = ssrIcon('panel-bottom-close', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M3 15h18","key":"5xshup"}],["path",{"d":"m15 8-3 3-3-3","key":"1oxy1z"}]])
export const PanelBottomDashed = ssrIcon('panel-bottom-dashed', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M14 15h1","key":"171nev"}],["path",{"d":"M19 15h2","key":"1vnucp"}],["path",{"d":"M3 15h2","key":"8bym0q"}],["path",{"d":"M9 15h1","key":"1tg3ks"}]])
export const PanelBottomOpen = ssrIcon('panel-bottom-open', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M3 15h18","key":"5xshup"}],["path",{"d":"m9 10 3-3 3 3","key":"11gsxs"}]])
export const PanelLeft = ssrIcon('panel-left', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M9 3v18","key":"fh3hqa"}]])
export const PanelLeftClose = ssrIcon('panel-left-close', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M9 3v18","key":"fh3hqa"}],["path",{"d":"m16 15-3-3 3-3","key":"14y99z"}]])
export const PanelLeftDashed = ssrIcon('panel-left-dashed', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M9 14v1","key":"askpd8"}],["path",{"d":"M9 19v2","key":"16tejx"}],["path",{"d":"M9 3v2","key":"1noubl"}],["path",{"d":"M9 9v1","key":"19ebxg"}]])
export const PanelLeftOpen = ssrIcon('panel-left-open', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M9 3v18","key":"fh3hqa"}],["path",{"d":"m14 9 3 3-3 3","key":"8010ee"}]])
export const PanelLeftRightDashed = ssrIcon('panel-left-right-dashed', [["path",{"d":"M15 10V9","key":"4dkmfx"}],["path",{"d":"M15 15v-1","key":"6a4afx"}],["path",{"d":"M15 21v-2","key":"1qshmc"}],["path",{"d":"M15 5V3","key":"1fk0mb"}],["path",{"d":"M9 10V9","key":"1lazqi"}],["path",{"d":"M9 15v-1","key":"9lx740"}],["path",{"d":"M9 21v-2","key":"1fwk0n"}],["path",{"d":"M9 5V3","key":"2q8zi6"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const PanelRight = ssrIcon('panel-right', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M15 3v18","key":"14nvp0"}]])
export const PanelRightClose = ssrIcon('panel-right-close', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M15 3v18","key":"14nvp0"}],["path",{"d":"m8 9 3 3-3 3","key":"12hl5m"}]])
export const PanelRightDashed = ssrIcon('panel-right-dashed', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M15 14v1","key":"ilsfch"}],["path",{"d":"M15 19v2","key":"1fst2f"}],["path",{"d":"M15 3v2","key":"z204g4"}],["path",{"d":"M15 9v1","key":"z2a8b1"}]])
export const PanelRightOpen = ssrIcon('panel-right-open', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M15 3v18","key":"14nvp0"}],["path",{"d":"m10 15-3-3 3-3","key":"1pgupc"}]])
export const PanelTop = ssrIcon('panel-top', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M3 9h18","key":"1pudct"}]])
export const PanelTopBottomDashed = ssrIcon('panel-top-bottom-dashed', [["path",{"d":"M14 15h1","key":"171nev"}],["path",{"d":"M14 9h1","key":"l0svgy"}],["path",{"d":"M19 15h2","key":"1vnucp"}],["path",{"d":"M19 9h2","key":"te2zfg"}],["path",{"d":"M3 15h2","key":"8bym0q"}],["path",{"d":"M3 9h2","key":"1h4ldw"}],["path",{"d":"M9 15h1","key":"1tg3ks"}],["path",{"d":"M9 9h1","key":"15jzuz"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const PanelTopClose = ssrIcon('panel-top-close', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"m9 16 3-3 3 3","key":"1idcnm"}]])
export const PanelTopDashed = ssrIcon('panel-top-dashed', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M14 9h1","key":"l0svgy"}],["path",{"d":"M19 9h2","key":"te2zfg"}],["path",{"d":"M3 9h2","key":"1h4ldw"}],["path",{"d":"M9 9h1","key":"15jzuz"}]])
export const PanelTopOpen = ssrIcon('panel-top-open', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"m15 14-3 3-3-3","key":"g215vf"}]])
export const PanelsLeftBottom = ssrIcon('panels-left-bottom', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M9 3v18","key":"fh3hqa"}],["path",{"d":"M9 15h12","key":"5ijen5"}]])
export const PanelsRightBottom = ssrIcon('panels-right-bottom', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M3 15h12","key":"1wkqb3"}],["path",{"d":"M15 3v18","key":"14nvp0"}]])
export const Rows3 = ssrIcon('rows-3', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M21 9H3","key":"1338ky"}],["path",{"d":"M21 15H3","key":"9uk58r"}]])
export const PaperBag = ssrIcon('paper-bag', [["path",{"d":"M5.364 3.848C4 6 3 9.652 3 12.652V19a2 2 0 002 2h14a2 2 0 002-2v-5c0-2.334-1.816-4.668-2.622-7.002","key":"vlsvfu"}],["path",{"d":"M7 3h11.379a2 2 0 011.789 1.106l.723 1.447A1 1 0 0119.997 7h-8.525a2 2 0 01-1.789-1.106L8.79 4.105a2 2 0 10-3.579 1.789l2.261 4.522A5 5 0 018 12.652V21","key":"12exh5"}]])
export const Paperclip = ssrIcon('paperclip', [["path",{"d":"m16 6-8.414 8.586a2 2 0 0 0 2.829 2.829l8.414-8.586a4 4 0 1 0-5.657-5.657l-8.379 8.551a6 6 0 1 0 8.485 8.485l8.379-8.551","key":"1miecu"}]])
export const Parasol = ssrIcon('parasol', [["path",{"d":"M12.5 11.134 18.196 21","key":"gf58kt"}],["path",{"d":"M20.425 5.299a10 10 0 0 0-16.941 9.78c.183.563.843.774 1.355.478L20.16 6.711c.512-.296.66-.973.264-1.413","key":"znqfe4"}],["path",{"d":"M21 21H3","key":"oafrgs"}]])
export const Parentheses = ssrIcon('parentheses', [["path",{"d":"M8 21s-4-3-4-9 4-9 4-9","key":"uto9ud"}],["path",{"d":"M16 3s4 3 4 9-4 9-4 9","key":"4w2vsq"}]])
export const ParkingMeter = ssrIcon('parking-meter', [["path",{"d":"M11 15h2","key":"199qp6"}],["path",{"d":"M12 12v3","key":"158kv8"}],["path",{"d":"M12 19v3","key":"npa21l"}],["path",{"d":"M15.282 19a1 1 0 0 0 .948-.68l2.37-6.988a7 7 0 1 0-13.2 0l2.37 6.988a1 1 0 0 0 .948.68z","key":"1jofit"}],["path",{"d":"M9 9a3 3 0 1 1 6 0","key":"jdoeu8"}]])
export const SquareParking = ssrIcon('square-parking', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M9 17V7h4a3 3 0 0 1 0 6H9","key":"1dfk2c"}]])
export const SquareParkingOff = ssrIcon('square-parking-off', [["path",{"d":"M3.6 3.6A2 2 0 0 1 5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-.59 1.41","key":"9l1ft6"}],["path",{"d":"M3 8.7V19a2 2 0 0 0 2 2h10.3","key":"17knke"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M13 13a3 3 0 1 0 0-6H9v2","key":"uoagbd"}],["path",{"d":"M9 17v-2.3","key":"1jxgo2"}]])
export const PartyPopper = ssrIcon('party-popper', [["path",{"d":"M5.8 11.3 2 22l10.7-3.79","key":"gwxi1d"}],["path",{"d":"M4 3h.01","key":"1vcuye"}],["path",{"d":"M22 8h.01","key":"1mrtc2"}],["path",{"d":"M15 2h.01","key":"1cjtqr"}],["path",{"d":"M22 20h.01","key":"1mrys2"}],["path",{"d":"m22 2-2.24.75a2.9 2.9 0 0 0-1.96 3.12c.1.86-.57 1.63-1.45 1.63h-.38c-.86 0-1.6.6-1.76 1.44L14 10","key":"hbicv8"}],["path",{"d":"m22 13-.82-.33c-.86-.34-1.82.2-1.98 1.11c-.11.7-.72 1.22-1.43 1.22H17","key":"1i94pl"}],["path",{"d":"m11 2 .33.82c.34.86-.2 1.82-1.11 1.98C9.52 4.9 9 5.52 9 6.23V7","key":"1cofks"}],["path",{"d":"M11 13c1.93 1.93 2.83 4.17 2 5-.83.83-3.07-.07-5-2-1.93-1.93-2.83-4.17-2-5 .83-.83 3.07.07 5 2Z","key":"4kbmks"}]])
export const Pause = ssrIcon('pause', [["rect",{"x":"14","y":"3","width":"5","height":"18","rx":"1","key":"kaeet6"}],["rect",{"x":"5","y":"3","width":"5","height":"18","rx":"1","key":"1wsw3u"}]])
export const PawPrint = ssrIcon('paw-print', [["circle",{"cx":"11","cy":"4","r":"2","key":"vol9p0"}],["circle",{"cx":"18","cy":"8","r":"2","key":"17gozi"}],["circle",{"cx":"20","cy":"16","r":"2","key":"1v9bxh"}],["path",{"d":"M9 10a5 5 0 0 1 5 5v3.5a3.5 3.5 0 0 1-6.84 1.045Q6.52 17.48 4.46 16.84A3.5 3.5 0 0 1 5.5 10Z","key":"1ydw1z"}]])
export const PcCase = ssrIcon('pc-case', [["rect",{"width":"14","height":"20","x":"5","y":"2","rx":"2","key":"1uq1d7"}],["path",{"d":"M15 14h.01","key":"1kp3bh"}],["path",{"d":"M9 6h6","key":"dgm16u"}],["path",{"d":"M9 10h6","key":"9gxzsh"}]])
export const PenOff = ssrIcon('pen-off', [["path",{"d":"m10 10-6.157 6.162a2 2 0 0 0-.5.833l-1.322 4.36a.5.5 0 0 0 .622.624l4.358-1.323a2 2 0 0 0 .83-.5L14 13.982","key":"bjo8r8"}],["path",{"d":"m12.829 7.172 4.359-4.346a1 1 0 1 1 3.986 3.986l-4.353 4.353","key":"16h5ne"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}]])
export const PenTool = ssrIcon('pen-tool', [["path",{"d":"M15.707 21.293a1 1 0 0 1-1.414 0l-1.586-1.586a1 1 0 0 1 0-1.414l5.586-5.586a1 1 0 0 1 1.414 0l1.586 1.586a1 1 0 0 1 0 1.414z","key":"nt11vn"}],["path",{"d":"m18 13-1.375-6.874a1 1 0 0 0-.746-.776L3.235 2.028a1 1 0 0 0-1.207 1.207L5.35 15.879a1 1 0 0 0 .776.746L13 18","key":"15qc1e"}],["path",{"d":"m2.3 2.3 7.286 7.286","key":"1wuzzi"}],["circle",{"cx":"11","cy":"11","r":"2","key":"xmgehs"}]])
export const Pencil = ssrIcon('pencil', [["path",{"d":"M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z","key":"1a8usu"}],["path",{"d":"m15 5 4 4","key":"1mk7zo"}]])
export const PencilLine = ssrIcon('pencil-line', [["path",{"d":"M13 21h8","key":"1jsn5i"}],["path",{"d":"m15 5 4 4","key":"1mk7zo"}],["path",{"d":"M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z","key":"1a8usu"}]])
export const PencilOff = ssrIcon('pencil-off', [["path",{"d":"m10 10-6.157 6.162a2 2 0 0 0-.5.833l-1.322 4.36a.5.5 0 0 0 .622.624l4.358-1.323a2 2 0 0 0 .83-.5L14 13.982","key":"bjo8r8"}],["path",{"d":"m12.829 7.172 4.359-4.346a1 1 0 1 1 3.986 3.986l-4.353 4.353","key":"16h5ne"}],["path",{"d":"m15 5 4 4","key":"1mk7zo"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}]])
export const PencilRuler = ssrIcon('pencil-ruler', [["path",{"d":"M13 7 8.7 2.7a2.41 2.41 0 0 0-3.4 0L2.7 5.3a2.41 2.41 0 0 0 0 3.4L7 13","key":"orapub"}],["path",{"d":"m8 6 2-2","key":"115y1s"}],["path",{"d":"m18 16 2-2","key":"ee94s4"}],["path",{"d":"m17 11 4.3 4.3c.94.94.94 2.46 0 3.4l-2.6 2.6c-.94.94-2.46.94-3.4 0L11 17","key":"cfq27r"}],["path",{"d":"M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z","key":"1a8usu"}],["path",{"d":"m15 5 4 4","key":"1mk7zo"}]])
export const PencilSparkles = ssrIcon('pencil-sparkles', [["path",{"d":"M10 3H8","key":"mzdi2d"}],["path",{"d":"m15.007 5.008 3.987 3.986","key":"1scubj"}],["path",{"d":"M20 15v4","key":"nmhudv"}],["path",{"d":"M21.174 6.813a2.82 2.82 0 0 0-3.986-3.987L3.842 16.175a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z","key":"fs0856"}],["path",{"d":"M22 17h-4","key":"1sj068"}],["path",{"d":"M4 5v4","key":"13jjxc"}],["path",{"d":"M6 7H2","key":"8zbtv0"}],["path",{"d":"M9 2v2","key":"165o2o"}]])
export const Pentagon = ssrIcon('pentagon', [["path",{"d":"M10.83 2.38a2 2 0 0 1 2.34 0l8 5.74a2 2 0 0 1 .73 2.25l-3.04 9.26a2 2 0 0 1-1.9 1.37H7.04a2 2 0 0 1-1.9-1.37L2.1 10.37a2 2 0 0 1 .73-2.25z","key":"2hea0t"}]])
export const Percent = ssrIcon('percent', [["line",{"x1":"19","x2":"5","y1":"5","y2":"19","key":"1x9vlm"}],["circle",{"cx":"6.5","cy":"6.5","r":"2.5","key":"4mh3h7"}],["circle",{"cx":"17.5","cy":"17.5","r":"2.5","key":"1mdrzq"}]])
export const SquarePercent = ssrIcon('square-percent', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"m15 9-6 6","key":"1uzhvr"}],["path",{"d":"M9 9h.01","key":"1q5me6"}],["path",{"d":"M15 15h.01","key":"lqbp3k"}]])
export const PersonStanding = ssrIcon('person-standing', [["circle",{"cx":"12","cy":"5","r":"1","key":"gxeob9"}],["path",{"d":"m9 20 3-6 3 6","key":"se2kox"}],["path",{"d":"m6 8 6 2 6-2","key":"4o3us4"}],["path",{"d":"M12 10v4","key":"1kjpxc"}]])
export const Phi = ssrIcon('phi', [["path",{"d":"M12 2v20","key":"t6zp3m"}],["circle",{"cx":"12","cy":"12","r":"7","key":"fim9np"}]])
export const PhilippinePeso = ssrIcon('philippine-peso', [["path",{"d":"M20 11H4","key":"6ut86h"}],["path",{"d":"M20 7H4","key":"zbl0bi"}],["path",{"d":"M7 21V4a1 1 0 0 1 1-1h4a1 1 0 0 1 0 12H7","key":"1ana5r"}]])
export const Phone = ssrIcon('phone', [["path",{"d":"M13.832 16.568a1 1 0 0 0 1.213-.303l.355-.465A2 2 0 0 1 17 15h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2A18 18 0 0 1 2 4a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3a2 2 0 0 1-.8 1.6l-.468.351a1 1 0 0 0-.292 1.233 14 14 0 0 0 6.392 6.384","key":"9njp5v"}]])
export const PhoneCall = ssrIcon('phone-call', [["path",{"d":"M13 2a9 9 0 0 1 9 9","key":"1itnx2"}],["path",{"d":"M13 6a5 5 0 0 1 5 5","key":"11nki7"}],["path",{"d":"M13.832 16.568a1 1 0 0 0 1.213-.303l.355-.465A2 2 0 0 1 17 15h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2A18 18 0 0 1 2 4a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3a2 2 0 0 1-.8 1.6l-.468.351a1 1 0 0 0-.292 1.233 14 14 0 0 0 6.392 6.384","key":"9njp5v"}]])
export const PhoneForwarded = ssrIcon('phone-forwarded', [["path",{"d":"M14 6h8","key":"yd68k4"}],["path",{"d":"m18 2 4 4-4 4","key":"pucp1d"}],["path",{"d":"M13.832 16.568a1 1 0 0 0 1.213-.303l.355-.465A2 2 0 0 1 17 15h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2A18 18 0 0 1 2 4a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3a2 2 0 0 1-.8 1.6l-.468.351a1 1 0 0 0-.292 1.233 14 14 0 0 0 6.392 6.384","key":"9njp5v"}]])
export const PhoneIncoming = ssrIcon('phone-incoming', [["path",{"d":"M16 2v6h6","key":"1mfrl5"}],["path",{"d":"m22 2-6 6","key":"6f0sa0"}],["path",{"d":"M13.832 16.568a1 1 0 0 0 1.213-.303l.355-.465A2 2 0 0 1 17 15h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2A18 18 0 0 1 2 4a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3a2 2 0 0 1-.8 1.6l-.468.351a1 1 0 0 0-.292 1.233 14 14 0 0 0 6.392 6.384","key":"9njp5v"}]])
export const PhoneMissed = ssrIcon('phone-missed', [["path",{"d":"m16 2 6 6","key":"1gw87d"}],["path",{"d":"m22 2-6 6","key":"6f0sa0"}],["path",{"d":"M13.832 16.568a1 1 0 0 0 1.213-.303l.355-.465A2 2 0 0 1 17 15h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2A18 18 0 0 1 2 4a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3a2 2 0 0 1-.8 1.6l-.468.351a1 1 0 0 0-.292 1.233 14 14 0 0 0 6.392 6.384","key":"9njp5v"}]])
export const PhoneOff = ssrIcon('phone-off', [["path",{"d":"M10.1 13.9a14 14 0 0 0 3.732 2.668 1 1 0 0 0 1.213-.303l.355-.465A2 2 0 0 1 17 15h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2 18 18 0 0 1-12.728-5.272","key":"1wngk7"}],["path",{"d":"M22 2 2 22","key":"y4kqgn"}],["path",{"d":"M4.76 13.582A18 18 0 0 1 2 4a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3a2 2 0 0 1-.8 1.6l-.468.351a1 1 0 0 0-.292 1.233 14 14 0 0 0 .244.473","key":"10hv5p"}]])
export const PhoneOutgoing = ssrIcon('phone-outgoing', [["path",{"d":"m16 8 6-6","key":"oawc05"}],["path",{"d":"M22 8V2h-6","key":"oqy2zc"}],["path",{"d":"M13.832 16.568a1 1 0 0 0 1.213-.303l.355-.465A2 2 0 0 1 17 15h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2A18 18 0 0 1 2 4a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3a2 2 0 0 1-.8 1.6l-.468.351a1 1 0 0 0-.292 1.233 14 14 0 0 0 6.392 6.384","key":"9njp5v"}]])
export const Pi = ssrIcon('pi', [["line",{"x1":"9","x2":"9","y1":"4","y2":"20","key":"ovs5a5"}],["path",{"d":"M4 7c0-1.7 1.3-3 3-3h13","key":"10pag4"}],["path",{"d":"M18 20c-1.7 0-3-1.3-3-3V4","key":"1gaosr"}]])
export const SquarePi = ssrIcon('square-pi', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M7 7h10","key":"udp07y"}],["path",{"d":"M10 7v10","key":"i1d9ee"}],["path",{"d":"M16 17a2 2 0 0 1-2-2V7","key":"ftwdc7"}]])
export const Piano = ssrIcon('piano', [["path",{"d":"M10 13v4","key":"5krxfa"}],["path",{"d":"M14 13v4","key":"72xrsi"}],["path",{"d":"M18 13v4","key":"1i7sbu"}],["path",{"d":"M2 13h20","key":"5evz65"}],["path",{"d":"M22 11.5A3.5 3.5 0 0018.5 8a3.52 3.52 0 01-3.173-2A7 7 0 002 9v10a2 2 0 002 2h16a2 2 0 002-2z","key":"1txdgy"}],["path",{"d":"M6 13v4","key":"9v0cap"}]])
export const Pickaxe = ssrIcon('pickaxe', [["path",{"d":"m14 13-8.381 8.38a1 1 0 0 1-3.001-3L11 9.999","key":"1lw9ds"}],["path",{"d":"M15.973 4.027A13 13 0 0 0 5.902 2.373c-1.398.342-1.092 2.158.277 2.601a19.9 19.9 0 0 1 5.822 3.024","key":"ffj4ej"}],["path",{"d":"M16.001 11.999a19.9 19.9 0 0 1 3.024 5.824c.444 1.369 2.26 1.676 2.603.278A13 13 0 0 0 20 8.069","key":"8tj4zw"}],["path",{"d":"M18.352 3.352a1.205 1.205 0 0 0-1.704 0l-5.296 5.296a1.205 1.205 0 0 0 0 1.704l2.296 2.296a1.205 1.205 0 0 0 1.704 0l5.296-5.296a1.205 1.205 0 0 0 0-1.704z","key":"hh6h97"}]])
export const PictureInPicture = ssrIcon('picture-in-picture', [["path",{"d":"M2 10h6V4","key":"zwrco"}],["path",{"d":"m2 4 6 6","key":"ug085t"}],["path",{"d":"M21 10V7a2 2 0 0 0-2-2h-7","key":"git5jr"}],["path",{"d":"M3 14v2a2 2 0 0 0 2 2h3","key":"1f7fh3"}],["rect",{"x":"12","y":"14","width":"10","height":"7","rx":"1","key":"1wjs3o"}]])
export const PictureInPicture2 = ssrIcon('picture-in-picture-2', [["path",{"d":"M21 9V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v10c0 1.1.9 2 2 2h4","key":"daa4of"}],["rect",{"width":"10","height":"7","x":"12","y":"13","rx":"2","key":"1nb8gs"}]])
export const PiggyBank = ssrIcon('piggy-bank', [["path",{"d":"M11 17h3v2a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1v-3a3.16 3.16 0 0 0 2-2h1a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1h-1a5 5 0 0 0-2-4V3a4 4 0 0 0-3.2 1.6l-.3.4H11a6 6 0 0 0-6 6v1a5 5 0 0 0 2 4v3a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1z","key":"1piglc"}],["path",{"d":"M16 10h.01","key":"1m94wz"}],["path",{"d":"M2 8v1a2 2 0 0 0 2 2h1","key":"1env43"}]])
export const Pilcrow = ssrIcon('pilcrow', [["path",{"d":"M13 4v16","key":"8vvj80"}],["path",{"d":"M17 4v16","key":"7dpous"}],["path",{"d":"M19 4H9.5a4.5 4.5 0 0 0 0 9H13","key":"sh4n9v"}]])
export const PilcrowLeft = ssrIcon('pilcrow-left', [["path",{"d":"M14 3v11","key":"mlfb7b"}],["path",{"d":"M14 9h-3a3 3 0 0 1 0-6h9","key":"1ulc19"}],["path",{"d":"M18 3v11","key":"1phi0r"}],["path",{"d":"M22 18H2l4-4","key":"yt65j9"}],["path",{"d":"m6 22-4-4","key":"6jgyf5"}]])
export const PilcrowRight = ssrIcon('pilcrow-right', [["path",{"d":"M10 3v11","key":"o3l5kj"}],["path",{"d":"M10 9H7a1 1 0 0 1 0-6h8","key":"1wb1nc"}],["path",{"d":"M14 3v11","key":"mlfb7b"}],["path",{"d":"m18 14 4 4H2","key":"4r8io1"}],["path",{"d":"m22 18-4 4","key":"1hjjrd"}]])
export const SquarePilcrow = ssrIcon('square-pilcrow', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M12 12H9.5a2.5 2.5 0 0 1 0-5H17","key":"1l9586"}],["path",{"d":"M12 7v10","key":"jspqdw"}],["path",{"d":"M16 7v10","key":"lavkr4"}]])
export const Pill = ssrIcon('pill', [["path",{"d":"m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z","key":"wa1lgi"}],["path",{"d":"m8.5 8.5 7 7","key":"rvfmvr"}]])
export const PillBottle = ssrIcon('pill-bottle', [["path",{"d":"M18 11h-4a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1h4","key":"17ldeb"}],["path",{"d":"M6 7v13a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7","key":"nc37y6"}],["rect",{"width":"16","height":"5","x":"4","y":"2","rx":"1","key":"3jeezo"}]])
export const Pin = ssrIcon('pin', [["path",{"d":"M12 17v5","key":"bb1du9"}],["path",{"d":"M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z","key":"1nkz8b"}]])
export const PinOff = ssrIcon('pin-off', [["path",{"d":"M12 17v5","key":"bb1du9"}],["path",{"d":"M15 9.34V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H7.89","key":"znwnzq"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M9 9v1.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h11","key":"c9qhm2"}]])
export const Pipette = ssrIcon('pipette', [["path",{"d":"m12 9-8.414 8.414A2 2 0 0 0 3 18.828v1.344a2 2 0 0 1-.586 1.414A2 2 0 0 1 3.828 21h1.344a2 2 0 0 0 1.414-.586L15 12","key":"1y3wsu"}],["path",{"d":"m18 9 .4.4a1 1 0 1 1-3 3l-3.8-3.8a1 1 0 1 1 3-3l.4.4 3.4-3.4a1 1 0 1 1 3 3z","key":"110lr1"}],["path",{"d":"m2 22 .414-.414","key":"jhxm08"}]])
export const Pizza = ssrIcon('pizza', [["path",{"d":"m12 14-1 1","key":"11onhr"}],["path",{"d":"m13.75 18.25-1.25 1.42","key":"1yisr3"}],["path",{"d":"M17.775 5.654a15.68 15.68 0 0 0-12.121 12.12","key":"1qtqk6"}],["path",{"d":"M18.8 9.3a1 1 0 0 0 2.1 7.7","key":"fbbbr2"}],["path",{"d":"M21.964 20.732a1 1 0 0 1-1.232 1.232l-18-5a1 1 0 0 1-.695-1.232A19.68 19.68 0 0 1 15.732 2.037a1 1 0 0 1 1.232.695z","key":"1hyfdd"}]])
export const Plane = ssrIcon('plane', [["path",{"d":"M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z","key":"1v9wt8"}]])
export const PlaneLanding = ssrIcon('plane-landing', [["path",{"d":"M2 22h20","key":"272qi7"}],["path",{"d":"M3.77 10.77 2 9l2-4.5 1.1.55c.55.28.9.84.9 1.45s.35 1.17.9 1.45L8 8.5l3-6 1.05.53a2 2 0 0 1 1.09 1.52l.72 5.4a2 2 0 0 0 1.09 1.52l4.4 2.2c.42.22.78.55 1.01.96l.6 1.03c.49.88-.06 1.98-1.06 2.1l-1.18.15c-.47.06-.95-.02-1.37-.24L4.29 11.15a2 2 0 0 1-.52-.38Z","key":"1ma21e"}]])
export const PlaneTakeoff = ssrIcon('plane-takeoff', [["path",{"d":"M2 22h20","key":"272qi7"}],["path",{"d":"M6.36 17.4 4 17l-2-4 1.1-.55a2 2 0 0 1 1.8 0l.17.1a2 2 0 0 0 1.8 0L8 12 5 6l.9-.45a2 2 0 0 1 2.09.2l4.02 3a2 2 0 0 0 2.1.2l4.19-2.06a2.41 2.41 0 0 1 1.73-.17L21 7a1.4 1.4 0 0 1 .87 1.99l-.38.76c-.23.46-.6.84-1.07 1.08L7.58 17.2a2 2 0 0 1-1.22.18Z","key":"fkigj9"}]])
export const Play = ssrIcon('play', [["path",{"d":"M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z","key":"10ikf1"}]])
export const PlayOff = ssrIcon('play-off', [["path",{"d":"m10.215 4.56 9.79 5.71a2 2 0 0 1 .003 3.458l-.393.23","key":"fdtkwz"}],["path",{"d":"m16.042 16.042-8.034 4.686A2 2 0 0 1 5 19V5","key":"1c8hxg"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}]])
export const SquarePlay = ssrIcon('square-play', [["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}],["path",{"d":"M9 9.003a1 1 0 0 1 1.517-.859l4.997 2.997a1 1 0 0 1 0 1.718l-4.997 2.997A1 1 0 0 1 9 14.996z","key":"kmsa83"}]])
export const PlayingCard = ssrIcon('playing-card', [["path",{"d":"M12.832 8.445a1 1 0 00-1.589-.098l-2.075 3.098a1 1 0 000 1.11l2 3a1 1 0 001.664 0l2-3a1 1 0 000-1.11z","key":"r2cm5y"}],["rect",{"x":"5","y":"2","width":"14","height":"20","rx":"2","key":"1k0ky4"}]])
export const PlayingCards = ssrIcon('playing-cards', [["path",{"d":"M14.832 8.445a1 1 0 00-1.589-.098l-2.075 3.098a1 1 0 000 1.11l2 3a1 1 0 001.664 0l2-3a1 1 0 000-1.11z","key":"ubuxio"}],["path",{"d":"m7.18 20.827-5-11a2 2 0 01.993-2.647L7 5.44","key":"1dure5"}],["rect",{"x":"7","y":"2","width":"14","height":"20","rx":"2","key":"p3xopd"}]])
export const PlayingCardsFan = ssrIcon('playing-cards-fan', [["path",{"d":"M12.65 7.65a2 2 0 012.629-1.046l5.51 2.374a2 2 0 011.046 2.628l-3.957 9.184a2 2 0 01-2.628 1.046l-5.51-2.374a2 2 0 01-1.046-2.628z","key":"15jvxw"}],["path",{"d":"M18 7.777V4a2 2 0 00-2-2h-6a2 2 0 00-2 2v10a2 2 0 001.137 1.805","key":"y6hc3m"}],["path",{"d":"m8 4.389-4.364.809a2 2 0 00-1.602 2.33l1.822 9.833a2 2 0 002.331 1.602l2.542-.47","key":"t01ww5"}]])
export const Plug = ssrIcon('plug', [["path",{"d":"M12 22v-5","key":"1ega77"}],["path",{"d":"M15 8V2","key":"18g5xt"}],["path",{"d":"M17 8a1 1 0 0 1 1 1v4a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1z","key":"1xoxul"}],["path",{"d":"M9 8V2","key":"14iosj"}]])
export const Plug2 = ssrIcon('plug-2', [["path",{"d":"M9 2v6","key":"17ngun"}],["path",{"d":"M15 2v6","key":"s7yy2p"}],["path",{"d":"M12 17v5","key":"bb1du9"}],["path",{"d":"M5 8h14","key":"pcz4l3"}],["path",{"d":"M6 11V8h12v3a6 6 0 1 1-12 0Z","key":"wtfw2c"}]])
export const PlugZap = ssrIcon('plug-zap', [["path",{"d":"M6.3 20.3a2.4 2.4 0 0 0 3.4 0L12 18l-6-6-2.3 2.3a2.4 2.4 0 0 0 0 3.4Z","key":"goz73y"}],["path",{"d":"m2 22 3-3","key":"19mgm9"}],["path",{"d":"M7.5 13.5 10 11","key":"7xgeeb"}],["path",{"d":"M10.5 16.5 13 14","key":"10btkg"}],["path",{"d":"m18 3-4 4h6l-4 4","key":"16psg9"}]])
export const Plus = ssrIcon('plus', [["path",{"d":"M5 12h14","key":"1ays0h"}],["path",{"d":"M12 5v14","key":"s699le"}]])
export const SquarePlus = ssrIcon('square-plus', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M8 12h8","key":"1wcyev"}],["path",{"d":"M12 8v8","key":"napkw2"}]])
export const PocketKnife = ssrIcon('pocket-knife', [["path",{"d":"M3 2v1c0 1 2 1 2 2S3 6 3 7s2 1 2 2-2 1-2 2 2 1 2 2","key":"19w3oe"}],["path",{"d":"M18 6h.01","key":"1v4wsw"}],["path",{"d":"M6 18h.01","key":"uhywen"}],["path",{"d":"M20.83 8.83a4 4 0 0 0-5.66-5.66l-12 12a4 4 0 1 0 5.66 5.66Z","key":"6fykxj"}],["path",{"d":"M18 11.66V22a4 4 0 0 0 4-4V6","key":"1utzek"}]])
export const Podium = ssrIcon('podium', [["path",{"d":"M12 6V2h-1","key":"1hv4eo"}],["path",{"d":"M9 15a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1v-3a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1","key":"1jvw5n"}],["path",{"d":"M9 21V11a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v10","key":"rgi5dp"}]])
export const Pointer = ssrIcon('pointer', [["path",{"d":"M22 14a8 8 0 0 1-8 8","key":"56vcr3"}],["path",{"d":"M18 11v-1a2 2 0 0 0-2-2a2 2 0 0 0-2 2","key":"1agjmk"}],["path",{"d":"M14 10V9a2 2 0 0 0-2-2a2 2 0 0 0-2 2v1","key":"wdbh2u"}],["path",{"d":"M10 9.5V4a2 2 0 0 0-2-2a2 2 0 0 0-2 2v10","key":"1ibuk9"}],["path",{"d":"M18 11a2 2 0 1 1 4 0v3a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15","key":"g6ys72"}]])
export const PointerOff = ssrIcon('pointer-off', [["path",{"d":"M10 4.5V4a2 2 0 0 0-2.41-1.957","key":"jsi14n"}],["path",{"d":"M13.9 8.4a2 2 0 0 0-1.26-1.295","key":"hirc7f"}],["path",{"d":"M21.7 16.2A8 8 0 0 0 22 14v-3a2 2 0 1 0-4 0v-1a2 2 0 0 0-3.63-1.158","key":"1jxb2e"}],["path",{"d":"m7 15-1.8-1.8a2 2 0 0 0-2.79 2.86L6 19.7a7.74 7.74 0 0 0 6 2.3h2a8 8 0 0 0 5.657-2.343","key":"10r7hm"}],["path",{"d":"M6 6v8","key":"tv5xkp"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}]])
export const Popcorn = ssrIcon('popcorn', [["path",{"d":"M18 8a2 2 0 0 0 0-4 2 2 0 0 0-4 0 2 2 0 0 0-4 0 2 2 0 0 0-4 0 2 2 0 0 0 0 4","key":"10td1f"}],["path",{"d":"M10 22 9 8","key":"yjptiv"}],["path",{"d":"m14 22 1-14","key":"8jwc8b"}],["path",{"d":"M20 8c.5 0 .9.4.8 1l-2.6 12c-.1.5-.7 1-1.2 1H7c-.6 0-1.1-.4-1.2-1L3.2 9c-.1-.6.3-1 .8-1Z","key":"1qo33t"}]])
export const Popsicle = ssrIcon('popsicle', [["path",{"d":"M18.6 14.4c.8-.8.8-2 0-2.8l-8.1-8.1a4.95 4.95 0 1 0-7.1 7.1l8.1 8.1c.9.7 2.1.7 2.9-.1Z","key":"1o68ps"}],["path",{"d":"m22 22-5.5-5.5","key":"17o70y"}]])
export const PoundSterling = ssrIcon('pound-sterling', [["path",{"d":"M18 7c0-5.333-8-5.333-8 0","key":"1prm2n"}],["path",{"d":"M10 7v14","key":"18tmcs"}],["path",{"d":"M6 21h12","key":"4dkmi1"}],["path",{"d":"M6 13h10","key":"ybwr4a"}]])
export const Power = ssrIcon('power', [["path",{"d":"M12 2v10","key":"mnfbl"}],["path",{"d":"M18.4 6.6a9 9 0 1 1-12.77.04","key":"obofu9"}]])
export const PowerOff = ssrIcon('power-off', [["path",{"d":"M18.36 6.64A9 9 0 0 1 20.77 15","key":"dxknvb"}],["path",{"d":"M6.16 6.16a9 9 0 1 0 12.68 12.68","key":"1x7qb5"}],["path",{"d":"M12 2v4","key":"3427ic"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}]])
export const SquarePower = ssrIcon('square-power', [["path",{"d":"M12 7v4","key":"xawao1"}],["path",{"d":"M7.998 9.003a5 5 0 1 0 8-.005","key":"1pek45"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const Presentation = ssrIcon('presentation', [["path",{"d":"M2 3h20","key":"91anmk"}],["path",{"d":"M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3","key":"2k9sn8"}],["path",{"d":"m7 21 5-5 5 5","key":"bip4we"}]])
export const Printer = ssrIcon('printer', [["path",{"d":"M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2","key":"143wyd"}],["path",{"d":"M6 9V3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v6","key":"1itne7"}],["rect",{"x":"6","y":"14","width":"12","height":"8","rx":"1","key":"1ue0tg"}]])
export const PrinterCheck = ssrIcon('printer-check', [["path",{"d":"M13.5 22H7a1 1 0 0 1-1-1v-6a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v.5","key":"qeb09x"}],["path",{"d":"m16 19 2 2 4-4","key":"1b14m6"}],["path",{"d":"M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v2","key":"1md90i"}],["path",{"d":"M6 9V3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v6","key":"1itne7"}]])
export const PrinterX = ssrIcon('printer-x', [["path",{"d":"M12.531 22H7a1 1 0 0 1-1-1v-6a1 1 0 0 1 1-1h6.377","key":"1w39xo"}],["path",{"d":"m16.5 16.5 5 5","key":"zc9lw7"}],["path",{"d":"m16.5 21.5 5-5","key":"1fr29m"}],["path",{"d":"M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v1.5","key":"18he39"}],["path",{"d":"M6 9V3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v6","key":"1itne7"}]])
export const Projector = ssrIcon('projector', [["path",{"d":"M5 7 3 5","key":"1yys58"}],["path",{"d":"M9 6V3","key":"1ptz9u"}],["path",{"d":"m13 7 2-2","key":"1w3vmq"}],["circle",{"cx":"9","cy":"13","r":"3","key":"1mma13"}],["path",{"d":"M11.83 12H20a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h2.17","key":"2frwzc"}],["path",{"d":"M16 16h2","key":"dnq2od"}]])
export const Proportions = ssrIcon('proportions', [["rect",{"width":"20","height":"16","x":"2","y":"4","rx":"2","key":"18n3k1"}],["path",{"d":"M12 9v11","key":"1fnkrn"}],["path",{"d":"M2 9h13a2 2 0 0 1 2 2v9","key":"11z3ex"}]])
export const Puzzle = ssrIcon('puzzle', [["path",{"d":"M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z","key":"w46dr5"}]])
export const Pyramid = ssrIcon('pyramid', [["path",{"d":"M2.5 16.88a1 1 0 0 1-.32-1.43l9-13.02a1 1 0 0 1 1.64 0l9 13.01a1 1 0 0 1-.32 1.44l-8.51 4.86a2 2 0 0 1-1.98 0Z","key":"aenxs0"}],["path",{"d":"M12 2v20","key":"t6zp3m"}]])
export const QrCode = ssrIcon('qr-code', [["rect",{"width":"5","height":"5","x":"3","y":"3","rx":"1","key":"1tu5fj"}],["rect",{"width":"5","height":"5","x":"16","y":"3","rx":"1","key":"1v8r4q"}],["rect",{"width":"5","height":"5","x":"3","y":"16","rx":"1","key":"1x03jg"}],["path",{"d":"M21 16h-3a2 2 0 0 0-2 2v3","key":"177gqh"}],["path",{"d":"M21 21v.01","key":"ents32"}],["path",{"d":"M12 7v3a2 2 0 0 1-2 2H7","key":"8crl2c"}],["path",{"d":"M3 12h.01","key":"nlz23k"}],["path",{"d":"M12 3h.01","key":"n36tog"}],["path",{"d":"M12 16v.01","key":"133mhm"}],["path",{"d":"M16 12h1","key":"1slzba"}],["path",{"d":"M21 12v.01","key":"1lwtk9"}],["path",{"d":"M12 21v-1","key":"1880an"}]])
export const Quote = ssrIcon('quote', [["path",{"d":"M16 3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2 1 1 0 0 1 1 1v1a2 2 0 0 1-2 2 1 1 0 0 0-1 1v2a1 1 0 0 0 1 1 6 6 0 0 0 6-6V5a2 2 0 0 0-2-2z","key":"rib7q0"}],["path",{"d":"M5 3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2 1 1 0 0 1 1 1v1a2 2 0 0 1-2 2 1 1 0 0 0-1 1v2a1 1 0 0 0 1 1 6 6 0 0 0 6-6V5a2 2 0 0 0-2-2z","key":"1ymkrd"}]])
export const Rabbit = ssrIcon('rabbit', [["path",{"d":"M13 16a3 3 0 0 1 2.24 5","key":"1epib5"}],["path",{"d":"M18 12h.01","key":"yjnet6"}],["path",{"d":"M18 21h-8a4 4 0 0 1-4-4 7 7 0 0 1 7-7h.2L9.6 6.4a1 1 0 1 1 2.8-2.8L15.8 7h.2c3.3 0 6 2.7 6 6v1a2 2 0 0 1-2 2h-1a3 3 0 0 0-3 3","key":"ue9ozu"}],["path",{"d":"M20 8.54V4a2 2 0 1 0-4 0v3","key":"49iql8"}],["path",{"d":"M7.612 12.524a3 3 0 1 0-1.6 4.3","key":"1e33i0"}]])
export const Radar = ssrIcon('radar', [["path",{"d":"M19.07 4.93A10 10 0 0 0 6.99 3.34","key":"z3du51"}],["path",{"d":"M4 6h.01","key":"oypzma"}],["path",{"d":"M2.29 9.62A10 10 0 1 0 21.31 8.35","key":"qzzz0"}],["path",{"d":"M16.24 7.76A6 6 0 1 0 8.23 16.67","key":"1yjesh"}],["path",{"d":"M12 18h.01","key":"mhygvu"}],["path",{"d":"M17.99 11.66A6 6 0 0 1 15.77 16.67","key":"1u2y91"}],["circle",{"cx":"12","cy":"12","r":"2","key":"1c9p78"}],["path",{"d":"m13.41 10.59 5.66-5.66","key":"mhq4k0"}]])
export const Radiation = ssrIcon('radiation', [["path",{"d":"M12 12h.01","key":"1mp3jc"}],["path",{"d":"M14 15.4641a4 4 0 0 1-4 0L7.52786 19.74597 A 1 1 0 0 0 7.99303 21.16211 10 10 0 0 0 16.00697 21.16211 1 1 0 0 0 16.47214 19.74597z","key":"1y4lzb"}],["path",{"d":"M16 12a4 4 0 0 0-2-3.464l2.472-4.282a1 1 0 0 1 1.46-.305 10 10 0 0 1 4.006 6.94A1 1 0 0 1 21 12z","key":"163ggk"}],["path",{"d":"M8 12a4 4 0 0 1 2-3.464L7.528 4.254a1 1 0 0 0-1.46-.305 10 10 0 0 0-4.006 6.94A1 1 0 0 0 3 12z","key":"1l9i0b"}]])
export const Radical = ssrIcon('radical', [["path",{"d":"M3 12h3.28a1 1 0 0 1 .948.684l2.298 7.934a.5.5 0 0 0 .96-.044L13.82 4.771A1 1 0 0 1 14.792 4H21","key":"1mqj8i"}]])
export const Radio = ssrIcon('radio', [["path",{"d":"M16.247 7.761a6 6 0 0 1 0 8.478","key":"1fwjs5"}],["path",{"d":"M19.075 4.933a10 10 0 0 1 0 14.134","key":"ehdyv1"}],["path",{"d":"M4.925 19.067a10 10 0 0 1 0-14.134","key":"1q22gi"}],["path",{"d":"M7.753 16.239a6 6 0 0 1 0-8.478","key":"r2q7qm"}],["circle",{"cx":"12","cy":"12","r":"2","key":"1c9p78"}]])
export const RadioOff = ssrIcon('radio-off', [["path",{"d":"M13.414 13.414a2 2 0 1 1-2.828-2.828","key":"srl686"}],["path",{"d":"M16.247 7.761a6 6 0 0 1 1.744 4.572","key":"1h86sp"}],["path",{"d":"M19.075 4.933a10 10 0 0 1 2.234 10.72","key":"1n13k4"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M4.925 19.067a10 10 0 0 1 0-14.134","key":"1q22gi"}],["path",{"d":"M7.753 16.239a6 6 0 0 1 0-8.478","key":"r2q7qm"}]])
export const RadioReceiver = ssrIcon('radio-receiver', [["path",{"d":"M5 16v2","key":"g5qcv5"}],["path",{"d":"M19 16v2","key":"1gbaio"}],["rect",{"width":"20","height":"8","x":"2","y":"8","rx":"2","key":"vjsjur"}],["path",{"d":"M18 12h.01","key":"yjnet6"}]])
export const RadioTower = ssrIcon('radio-tower', [["path",{"d":"M4.9 16.1C1 12.2 1 5.8 4.9 1.9","key":"s0qx1y"}],["path",{"d":"M7.8 4.7a6.14 6.14 0 0 0-.8 7.5","key":"1idnkw"}],["circle",{"cx":"12","cy":"9","r":"2","key":"1092wv"}],["path",{"d":"M16.2 4.8c2 2 2.26 5.11.8 7.47","key":"ojru2q"}],["path",{"d":"M19.1 1.9a9.96 9.96 0 0 1 0 14.1","key":"rhi7fg"}],["path",{"d":"M9.5 18h5","key":"mfy3pd"}],["path",{"d":"m8 22 4-11 4 11","key":"25yftu"}]])
export const Radius = ssrIcon('radius', [["path",{"d":"M20.34 17.52a10 10 0 1 0-2.82 2.82","key":"fydyku"}],["circle",{"cx":"19","cy":"19","r":"2","key":"17f5cg"}],["path",{"d":"m13.41 13.41 4.18 4.18","key":"1gqbwc"}],["circle",{"cx":"12","cy":"12","r":"2","key":"1c9p78"}]])
export const Rainbow = ssrIcon('rainbow', [["path",{"d":"M22 17a10 10 0 0 0-20 0","key":"ozegv"}],["path",{"d":"M6 17a6 6 0 0 1 12 0","key":"5giftw"}],["path",{"d":"M10 17a2 2 0 0 1 4 0","key":"gnsikk"}]])
export const Rat = ssrIcon('rat', [["path",{"d":"M13 22H4a2 2 0 0 1 0-4h12","key":"bt3f23"}],["path",{"d":"M13.236 18a3 3 0 0 0-2.2-5","key":"1tbvmo"}],["path",{"d":"M16 9h.01","key":"1bdo4e"}],["path",{"d":"M16.82 3.94a3 3 0 1 1 3.237 4.868l1.815 2.587a1.5 1.5 0 0 1-1.5 2.1l-2.872-.453a3 3 0 0 0-3.5 3","key":"9ch7kn"}],["path",{"d":"M17 4.988a3 3 0 1 0-5.2 2.052A7 7 0 0 0 4 14.015 4 4 0 0 0 8 18","key":"3s7e9i"}]])
export const Ratio = ssrIcon('ratio', [["rect",{"width":"12","height":"20","x":"6","y":"2","rx":"2","key":"1oxtiu"}],["rect",{"width":"20","height":"12","x":"2","y":"6","rx":"2","key":"9lu3g6"}]])
export const Receipt = ssrIcon('receipt', [["path",{"d":"M12 17V7","key":"pyj7ub"}],["path",{"d":"M16 8h-6a2 2 0 0 0 0 4h4a2 2 0 0 1 0 4H8","key":"1elt7d"}],["path",{"d":"M4 3a1 1 0 0 1 1-1 1.3 1.3 0 0 1 .7.2l.933.6a1.3 1.3 0 0 0 1.4 0l.934-.6a1.3 1.3 0 0 1 1.4 0l.933.6a1.3 1.3 0 0 0 1.4 0l.933-.6a1.3 1.3 0 0 1 1.4 0l.934.6a1.3 1.3 0 0 0 1.4 0l.933-.6A1.3 1.3 0 0 1 19 2a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1 1.3 1.3 0 0 1-.7-.2l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.934.6a1.3 1.3 0 0 1-1.4 0l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-1.4 0l-.934-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-.7.2 1 1 0 0 1-1-1z","key":"ycz6yz"}]])
export const ReceiptCent = ssrIcon('receipt-cent', [["path",{"d":"M12 7v10","key":"jspqdw"}],["path",{"d":"M14.828 14.829a4 4 0 0 1-5.656 0 4 4 0 0 1 0-5.657 4 4 0 0 1 5.656 0","key":"qvqont"}],["path",{"d":"M4 3a1 1 0 0 1 1-1 1.3 1.3 0 0 1 .7.2l.933.6a1.3 1.3 0 0 0 1.4 0l.934-.6a1.3 1.3 0 0 1 1.4 0l.933.6a1.3 1.3 0 0 0 1.4 0l.933-.6a1.3 1.3 0 0 1 1.4 0l.934.6a1.3 1.3 0 0 0 1.4 0l.933-.6A1.3 1.3 0 0 1 19 2a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1 1.3 1.3 0 0 1-.7-.2l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.934.6a1.3 1.3 0 0 1-1.4 0l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-1.4 0l-.934-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-.7.2 1 1 0 0 1-1-1z","key":"ycz6yz"}]])
export const ReceiptEuro = ssrIcon('receipt-euro', [["path",{"d":"M15.828 14.829a4 4 0 0 1-5.656 0 4 4 0 0 1 0-5.657 4 4 0 0 1 5.656 0","key":"16zdw4"}],["path",{"d":"M4 3a1 1 0 0 1 1-1 1.3 1.3 0 0 1 .7.2l.933.6a1.3 1.3 0 0 0 1.4 0l.934-.6a1.3 1.3 0 0 1 1.4 0l.933.6a1.3 1.3 0 0 0 1.4 0l.933-.6a1.3 1.3 0 0 1 1.4 0l.934.6a1.3 1.3 0 0 0 1.4 0l.933-.6A1.3 1.3 0 0 1 19 2a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1 1.3 1.3 0 0 1-.7-.2l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.934.6a1.3 1.3 0 0 1-1.4 0l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-1.4 0l-.934-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-.7.2 1 1 0 0 1-1-1z","key":"ycz6yz"}],["path",{"d":"M8 12h5","key":"1g6qi8"}]])
export const ReceiptIndianRupee = ssrIcon('receipt-indian-rupee', [["path",{"d":"M4 3a1 1 0 0 1 1-1 1.3 1.3 0 0 1 .7.2l.933.6a1.3 1.3 0 0 0 1.4 0l.934-.6a1.3 1.3 0 0 1 1.4 0l.933.6a1.3 1.3 0 0 0 1.4 0l.933-.6a1.3 1.3 0 0 1 1.4 0l.934.6a1.3 1.3 0 0 0 1.4 0l.933-.6A1.3 1.3 0 0 1 19 2a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1 1.3 1.3 0 0 1-.7-.2l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.934.6a1.3 1.3 0 0 1-1.4 0l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-1.4 0l-.934-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-.7.2 1 1 0 0 1-1-1z","key":"ycz6yz"}],["path",{"d":"M8 11h8","key":"vwpz6n"}],["path",{"d":"M8 7h8","key":"i86dvs"}],["path",{"d":"M9 7a4 4 0 0 1 0 8H8l3 2","key":"1xaco0"}]])
export const ReceiptJapaneseYen = ssrIcon('receipt-japanese-yen', [["path",{"d":"m12 10 3-3","key":"1mc12w"}],["path",{"d":"M4 3a1 1 0 0 1 1-1 1.3 1.3 0 0 1 .7.2l.933.6a1.3 1.3 0 0 0 1.4 0l.934-.6a1.3 1.3 0 0 1 1.4 0l.933.6a1.3 1.3 0 0 0 1.4 0l.933-.6a1.3 1.3 0 0 1 1.4 0l.934.6a1.3 1.3 0 0 0 1.4 0l.933-.6A1.3 1.3 0 0 1 19 2a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1 1.3 1.3 0 0 1-.7-.2l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.934.6a1.3 1.3 0 0 1-1.4 0l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-1.4 0l-.934-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-.7.2 1 1 0 0 1-1-1z","key":"ycz6yz"}],["path",{"d":"M9 11h6","key":"1fldmi"}],["path",{"d":"M9 15h6","key":"cctwl0"}],["path",{"d":"m9 7 3 3v7","key":"1x0cue"}]])
export const ReceiptPoundSterling = ssrIcon('receipt-pound-sterling', [["path",{"d":"M10 17V9.5a1 1 0 0 1 5 0","key":"td22vl"}],["path",{"d":"M4 3a1 1 0 0 1 1-1 1.3 1.3 0 0 1 .7.2l.933.6a1.3 1.3 0 0 0 1.4 0l.934-.6a1.3 1.3 0 0 1 1.4 0l.933.6a1.3 1.3 0 0 0 1.4 0l.933-.6a1.3 1.3 0 0 1 1.4 0l.934.6a1.3 1.3 0 0 0 1.4 0l.933-.6A1.3 1.3 0 0 1 19 2a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1 1.3 1.3 0 0 1-.7-.2l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.934.6a1.3 1.3 0 0 1-1.4 0l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-1.4 0l-.934-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-.7.2 1 1 0 0 1-1-1z","key":"ycz6yz"}],["path",{"d":"M8 13h5","key":"1k9z8w"}],["path",{"d":"M8 17h7","key":"8mjdqu"}]])
export const ReceiptRussianRuble = ssrIcon('receipt-russian-ruble', [["path",{"d":"M4 3a1 1 0 0 1 1-1 1.3 1.3 0 0 1 .7.2l.933.6a1.3 1.3 0 0 0 1.4 0l.934-.6a1.3 1.3 0 0 1 1.4 0l.933.6a1.3 1.3 0 0 0 1.4 0l.933-.6a1.3 1.3 0 0 1 1.4 0l.934.6a1.3 1.3 0 0 0 1.4 0l.933-.6A1.3 1.3 0 0 1 19 2a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1 1.3 1.3 0 0 1-.7-.2l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.934.6a1.3 1.3 0 0 1-1.4 0l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-1.4 0l-.934-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-.7.2 1 1 0 0 1-1-1z","key":"ycz6yz"}],["path",{"d":"M8 11h5a2 2 0 0 0 0-4h-3v10","key":"agnv0r"}],["path",{"d":"M8 15h5","key":"vxg57a"}]])
export const ReceiptSwissFranc = ssrIcon('receipt-swiss-franc', [["path",{"d":"M10 11h4","key":"1i0mka"}],["path",{"d":"M10 17V7h5","key":"k7jq18"}],["path",{"d":"M4 3a1 1 0 0 1 1-1 1.3 1.3 0 0 1 .7.2l.933.6a1.3 1.3 0 0 0 1.4 0l.934-.6a1.3 1.3 0 0 1 1.4 0l.933.6a1.3 1.3 0 0 0 1.4 0l.933-.6a1.3 1.3 0 0 1 1.4 0l.934.6a1.3 1.3 0 0 0 1.4 0l.933-.6A1.3 1.3 0 0 1 19 2a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1 1.3 1.3 0 0 1-.7-.2l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.934.6a1.3 1.3 0 0 1-1.4 0l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-1.4 0l-.934-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-.7.2 1 1 0 0 1-1-1z","key":"ycz6yz"}],["path",{"d":"M8 15h5","key":"vxg57a"}]])
export const ReceiptText = ssrIcon('receipt-text', [["path",{"d":"M13 16H8","key":"wsln4y"}],["path",{"d":"M14 8H8","key":"1l3xfs"}],["path",{"d":"M16 12H8","key":"1fr5h0"}],["path",{"d":"M4 3a1 1 0 0 1 1-1 1.3 1.3 0 0 1 .7.2l.933.6a1.3 1.3 0 0 0 1.4 0l.934-.6a1.3 1.3 0 0 1 1.4 0l.933.6a1.3 1.3 0 0 0 1.4 0l.933-.6a1.3 1.3 0 0 1 1.4 0l.934.6a1.3 1.3 0 0 0 1.4 0l.933-.6A1.3 1.3 0 0 1 19 2a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1 1.3 1.3 0 0 1-.7-.2l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.934.6a1.3 1.3 0 0 1-1.4 0l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-1.4 0l-.934-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-.7.2 1 1 0 0 1-1-1z","key":"ycz6yz"}]])
export const ReceiptTurkishLira = ssrIcon('receipt-turkish-lira', [["path",{"d":"M10 7v10a5 5 0 0 0 5-5","key":"1blmz7"}],["path",{"d":"m14 8-6 3","key":"2tb98i"}],["path",{"d":"M4 3a1 1 0 0 1 1-1 1.3 1.3 0 0 1 .7.2l.933.6a1.3 1.3 0 0 0 1.4 0l.934-.6a1.3 1.3 0 0 1 1.4 0l.933.6a1.3 1.3 0 0 0 1.4 0l.933-.6a1.3 1.3 0 0 1 1.4 0l.934.6a1.3 1.3 0 0 0 1.4 0l.933-.6A1.3 1.3 0 0 1 19 2a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1 1.3 1.3 0 0 1-.7-.2l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.934.6a1.3 1.3 0 0 1-1.4 0l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-1.4 0l-.934-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-.7.2 1 1 0 0 1-1-1z","key":"ycz6yz"}]])
export const RectangleCircle = ssrIcon('rectangle-circle', [["path",{"d":"M14 4v16H3a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z","key":"1m5n7q"}],["circle",{"cx":"14","cy":"12","r":"8","key":"1pag6k"}]])
export const RectangleGoggles = ssrIcon('rectangle-goggles', [["path",{"d":"M20 6a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-4a2 2 0 0 1-1.6-.8l-1.6-2.13a1 1 0 0 0-1.6 0L9.6 17.2A2 2 0 0 1 8 18H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z","key":"d5y1f"}]])
export const RectangleHorizontal = ssrIcon('rectangle-horizontal', [["rect",{"width":"20","height":"12","x":"2","y":"6","rx":"2","key":"9lu3g6"}]])
export const RectangleVertical = ssrIcon('rectangle-vertical', [["rect",{"width":"12","height":"20","x":"6","y":"2","rx":"2","key":"1oxtiu"}]])
export const Recycle = ssrIcon('recycle', [["path",{"d":"M7 19H4.815a1.83 1.83 0 0 1-1.57-.881 1.785 1.785 0 0 1-.004-1.784L7.196 9.5","key":"x6z5xu"}],["path",{"d":"M11 19h8.203a1.83 1.83 0 0 0 1.556-.89 1.784 1.784 0 0 0 0-1.775l-1.226-2.12","key":"1x4zh5"}],["path",{"d":"m14 16-3 3 3 3","key":"f6jyew"}],["path",{"d":"M8.293 13.596 7.196 9.5 3.1 10.598","key":"wf1obh"}],["path",{"d":"m9.344 5.811 1.093-1.892A1.83 1.83 0 0 1 11.985 3a1.784 1.784 0 0 1 1.546.888l3.943 6.843","key":"9tzpgr"}],["path",{"d":"m13.378 9.633 4.096 1.098 1.097-4.096","key":"1oe83g"}]])
export const Redo = ssrIcon('redo', [["path",{"d":"M21 7v6h-6","key":"3ptur4"}],["path",{"d":"M3 17a9 9 0 0 1 9-9 9 9 0 0 1 6 2.3l3 2.7","key":"1kgawr"}]])
export const Redo2 = ssrIcon('redo-2', [["path",{"d":"m15 14 5-5-5-5","key":"12vg1m"}],["path",{"d":"M20 9H9.5A5.5 5.5 0 0 0 4 14.5A5.5 5.5 0 0 0 9.5 20H13","key":"6uklza"}]])
export const RedoDot = ssrIcon('redo-dot', [["circle",{"cx":"12","cy":"17","r":"1","key":"1ixnty"}],["path",{"d":"M21 7v6h-6","key":"3ptur4"}],["path",{"d":"M3 17a9 9 0 0 1 9-9 9 9 0 0 1 6 2.3l3 2.7","key":"1kgawr"}]])
export const RefreshCcw = ssrIcon('refresh-ccw', [["path",{"d":"M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8","key":"14sxne"}],["path",{"d":"M3 3v5h5","key":"1xhq8a"}],["path",{"d":"M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16","key":"1hlbsb"}],["path",{"d":"M16 16h5v5","key":"ccwih5"}]])
export const RefreshCcwDot = ssrIcon('refresh-ccw-dot', [["path",{"d":"M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8","key":"14sxne"}],["path",{"d":"M3 3v5h5","key":"1xhq8a"}],["path",{"d":"M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16","key":"1hlbsb"}],["path",{"d":"M16 16h5v5","key":"ccwih5"}],["circle",{"cx":"12","cy":"12","r":"1","key":"41hilf"}]])
export const RefreshCw = ssrIcon('refresh-cw', [["path",{"d":"M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8","key":"v9h5vc"}],["path",{"d":"M21 3v5h-5","key":"1q7to0"}],["path",{"d":"M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16","key":"3uifl3"}],["path",{"d":"M8 16H3v5","key":"1cv678"}]])
export const RefreshCwOff = ssrIcon('refresh-cw-off', [["path",{"d":"M21 8L18.74 5.74A9.75 9.75 0 0 0 12 3C11 3 10.03 3.16 9.13 3.47","key":"1krf6h"}],["path",{"d":"M8 16H3v5","key":"1cv678"}],["path",{"d":"M3 12C3 9.51 4 7.26 5.64 5.64","key":"ruvoct"}],["path",{"d":"m3 16 2.26 2.26A9.75 9.75 0 0 0 12 21c2.49 0 4.74-1 6.36-2.64","key":"19q130"}],["path",{"d":"M21 12c0 1-.16 1.97-.47 2.87","key":"4w8emr"}],["path",{"d":"M21 3v5h-5","key":"1q7to0"}],["path",{"d":"M22 22 2 2","key":"1r8tn9"}]])
export const Refrigerator = ssrIcon('refrigerator', [["path",{"d":"M5 6a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6Z","key":"fpq118"}],["path",{"d":"M5 10h14","key":"elsbfy"}],["path",{"d":"M15 7v6","key":"1nx30x"}]])
export const Regex = ssrIcon('regex', [["path",{"d":"M17 3v10","key":"15fgeh"}],["path",{"d":"m12.67 5.5 8.66 5","key":"1gpheq"}],["path",{"d":"m12.67 10.5 8.66-5","key":"1dkfa6"}],["path",{"d":"M9 17a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v2a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2v-2z","key":"swwfx4"}]])
export const RemoveFormatting = ssrIcon('remove-formatting', [["path",{"d":"M4 7V4h16v3","key":"9msm58"}],["path",{"d":"M5 20h6","key":"1h6pxn"}],["path",{"d":"M13 4 8 20","key":"kqq6aj"}],["path",{"d":"m15 15 5 5","key":"me55sn"}],["path",{"d":"m20 15-5 5","key":"11p7ol"}]])
export const Repeat = ssrIcon('repeat', [["path",{"d":"m17 2 4 4-4 4","key":"nntrym"}],["path",{"d":"M3 11v-1a4 4 0 0 1 4-4h14","key":"84bu3i"}],["path",{"d":"m7 22-4-4 4-4","key":"1wqhfi"}],["path",{"d":"M21 13v1a4 4 0 0 1-4 4H3","key":"1rx37r"}]])
export const Repeat1 = ssrIcon('repeat-1', [["path",{"d":"m17 2 4 4-4 4","key":"nntrym"}],["path",{"d":"M3 11v-1a4 4 0 0 1 4-4h14","key":"84bu3i"}],["path",{"d":"m7 22-4-4 4-4","key":"1wqhfi"}],["path",{"d":"M21 13v1a4 4 0 0 1-4 4H3","key":"1rx37r"}],["path",{"d":"M11 10h1v4","key":"70cz1p"}]])
export const Repeat2 = ssrIcon('repeat-2', [["path",{"d":"m2 9 3-3 3 3","key":"1ltn5i"}],["path",{"d":"M13 18H7a2 2 0 0 1-2-2V6","key":"1r6tfw"}],["path",{"d":"m22 15-3 3-3-3","key":"4rnwn2"}],["path",{"d":"M11 6h6a2 2 0 0 1 2 2v10","key":"2f72bc"}]])
export const RepeatOff = ssrIcon('repeat-off', [["path",{"d":"M11.656 6H21l-4-4","key":"w9pozh"}],["path",{"d":"M17.898 17.898A4 4 0 0 1 17 18H3l4-4","key":"156mfe"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M21 13v1a4 4 0 0 1-.171 1.159","key":"2p1713"}],["path",{"d":"m21 6-4 4","key":"p7opkf"}],["path",{"d":"M3 11v-1a4 4 0 0 1 3.102-3.898","key":"8cius9"}],["path",{"d":"m7 22-4-4","key":"1kl3a3"}]])
export const Replace = ssrIcon('replace', [["path",{"d":"M14 4a1 1 0 0 1 1-1","key":"dhj8ez"}],["path",{"d":"M15 10a1 1 0 0 1-1-1","key":"1mnyi5"}],["path",{"d":"M21 4a1 1 0 0 0-1-1","key":"sfs9ap"}],["path",{"d":"M21 9a1 1 0 0 1-1 1","key":"mp6qeo"}],["path",{"d":"m3 7 3 3 3-3","key":"x25e72"}],["path",{"d":"M6 10V5a2 2 0 0 1 2-2h2","key":"15xut4"}],["rect",{"x":"3","y":"14","width":"7","height":"7","rx":"1","key":"1bkyp8"}]])
export const ReplaceAll = ssrIcon('replace-all', [["path",{"d":"M14 14a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1","key":"zg1ipl"}],["path",{"d":"M14 4a1 1 0 0 1 1-1","key":"dhj8ez"}],["path",{"d":"M15 10a1 1 0 0 1-1-1","key":"1mnyi5"}],["path",{"d":"M19 14a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1","key":"txt6k4"}],["path",{"d":"M21 4a1 1 0 0 0-1-1","key":"sfs9ap"}],["path",{"d":"M21 9a1 1 0 0 1-1 1","key":"mp6qeo"}],["path",{"d":"m3 7 3 3 3-3","key":"x25e72"}],["path",{"d":"M6 10V5a2 2 0 0 1 2-2h2","key":"15xut4"}],["rect",{"x":"3","y":"14","width":"7","height":"7","rx":"1","key":"1bkyp8"}]])
export const Reply = ssrIcon('reply', [["path",{"d":"M20 18v-2a4 4 0 0 0-4-4H4","key":"5vmcpk"}],["path",{"d":"m9 17-5-5 5-5","key":"nvlc11"}]])
export const ReplyAll = ssrIcon('reply-all', [["path",{"d":"m12 17-5-5 5-5","key":"1s3y5u"}],["path",{"d":"M22 18v-2a4 4 0 0 0-4-4H7","key":"1fcyog"}],["path",{"d":"m7 17-5-5 5-5","key":"1ed8i2"}]])
export const Rewind = ssrIcon('rewind', [["path",{"d":"M12 6a2 2 0 0 0-3.414-1.414l-6 6a2 2 0 0 0 0 2.828l6 6A2 2 0 0 0 12 18z","key":"2a1g8i"}],["path",{"d":"M22 6a2 2 0 0 0-3.414-1.414l-6 6a2 2 0 0 0 0 2.828l6 6A2 2 0 0 0 22 18z","key":"rg3s36"}]])
export const Ribbon = ssrIcon('ribbon', [["path",{"d":"M12 11.22C11 9.997 10 9 10 8a2 2 0 0 1 4 0c0 1-.998 2.002-2.01 3.22","key":"1rnhq3"}],["path",{"d":"m12 18 2.57-3.5","key":"116vt7"}],["path",{"d":"M6.243 9.016a7 7 0 0 1 11.507-.009","key":"10dq0b"}],["path",{"d":"M9.35 14.53 12 11.22","key":"tdsyp2"}],["path",{"d":"M9.35 14.53C7.728 12.246 6 10.221 6 7a6 5 0 0 1 12 0c-.005 3.22-1.778 5.235-3.43 7.5l3.557 4.527a1 1 0 0 1-.203 1.43l-1.894 1.36a1 1 0 0 1-1.384-.215L12 18l-2.679 3.593a1 1 0 0 1-1.39.213l-1.865-1.353a1 1 0 0 1-.203-1.422z","key":"nmifey"}]])
export const Road = ssrIcon('road', [["path",{"d":"M12 17v4","key":"1riwvh"}],["path",{"d":"M12 5V3","key":"vd5es"}],["path",{"d":"M12 9v3","key":"qyerrc"}],["path",{"d":"M2.077 18.449A2 2 0 0 0 4 21h16a2 2 0 0 0 1.924-2.55l-4-14A2 2 0 0 0 16 3H8a2 2 0 0 0-1.924 1.45z","key":"1cuxct"}]])
export const RobotArm = ssrIcon('robot-arm', [["path",{"d":"M12 21 7.5 8.322","key":"18d2q3"}],["path",{"d":"m14 7 1.75-3.767a.5.5 0 0 1 .662-.172L20 5.005","key":"1ui6cx"}],["path",{"d":"m20 8.998-3.588 1.944a.5.5 0 0 1-.662-.172L14 7H8","key":"mfi17k"}],["path",{"d":"M3.486 21h10","key":"d8eyu2"}],["path",{"d":"M5 21V8.732","key":"uljm3b"}],["circle",{"cx":"6","cy":"7","r":"2","key":"11yjtp"}]])
export const RobotVacuum = ssrIcon('robot-vacuum', [["path",{"d":"M11 17h2","key":"12w5me"}],["path",{"d":"M12 12h.01","key":"1mp3jc"}],["path",{"d":"M17 12a5 5 0 00-10 0","key":"7ltzr3"}],["path",{"d":"M19 2v2.8","key":"5fivdr"}],["path",{"d":"M2 5h2.8","key":"1hq9iq"}],["path",{"d":"M22 5h-2.8","key":"1w5mcv"}],["path",{"d":"M5 2v2.8","key":"1aozhq"}],["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}]])
export const Rocket = ssrIcon('rocket', [["path",{"d":"M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5","key":"qeys4"}],["path",{"d":"M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09","key":"u4xsad"}],["path",{"d":"M9 12a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.4 22.4 0 0 1-4 2z","key":"676m9"}],["path",{"d":"M9 12H4s.55-3.03 2-4c1.62-1.08 5 .05 5 .05","key":"92ym6u"}]])
export const RockingChair = ssrIcon('rocking-chair', [["path",{"d":"m15 13 3.708 7.416","key":"1edxn9"}],["path",{"d":"M3 19a15 15 0 0 0 18 0","key":"d0d1c4"}],["path",{"d":"m3 2 3.21 9.633A2 2 0 0 0 8.109 13H18","key":"tpa4et"}],["path",{"d":"m9 13-3.708 7.416","key":"1oplxx"}]])
export const RollerCoaster = ssrIcon('roller-coaster', [["path",{"d":"M6 19V5","key":"1r845m"}],["path",{"d":"M10 19V6.8","key":"9j2tfs"}],["path",{"d":"M14 19v-7.8","key":"10s8qv"}],["path",{"d":"M18 5v4","key":"1tajlv"}],["path",{"d":"M18 19v-6","key":"ielfq3"}],["path",{"d":"M22 19V9","key":"158nzp"}],["path",{"d":"M2 19V9a4 4 0 0 1 4-4c2 0 4 1.33 6 4s4 4 6 4a4 4 0 1 0-3-6.65","key":"1930oh"}]])
export const Rose = ssrIcon('rose', [["path",{"d":"M17 10h-1a4 4 0 1 1 4-4v.534","key":"7qf5zm"}],["path",{"d":"M17 6h1a4 4 0 0 1 1.42 7.74l-2.29.87a6 6 0 0 1-5.339-10.68l2.069-1.31","key":"1et29u"}],["path",{"d":"M4.5 17c2.8-.5 4.4 0 5.5.8s1.8 2.2 2.3 3.7c-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2","key":"kiv2lz"}],["path",{"d":"M9.77 12C4 15 2 22 2 22","key":"h28rw0"}],["circle",{"cx":"17","cy":"8","r":"2","key":"1330xn"}]])
export const Rotate3d = ssrIcon('rotate-3d', [["path",{"d":"m15.194 13.707 3.814 1.86-1.86 3.814","key":"16shm9"}],["path",{"d":"M16.47214 7.52786 A 5 10 0 1 0 13 21.79796","key":"1245p8"}],["path",{"d":"M21.79796 11 A 10 5 0 1 0 19 15.57071","key":"1i40ks"}]])
export const RotateCcw = ssrIcon('rotate-ccw', [["path",{"d":"M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8","key":"1357e3"}],["path",{"d":"M3 3v5h5","key":"1xhq8a"}]])
export const RotateCcwKey = ssrIcon('rotate-ccw-key', [["path",{"d":"M12 7v6","key":"lw1j43"}],["path",{"d":"M12 9h2","key":"1lpap9"}],["path",{"d":"M3 12a9 9 0 1 0 9-9 9.74 9.74 0 0 0-6.74 2.74L3 8","key":"g2jlw"}],["path",{"d":"M3 3v5h5","key":"1xhq8a"}],["circle",{"cx":"12","cy":"15","r":"2","key":"1vpstw"}]])
export const RotateCcwSquare = ssrIcon('rotate-ccw-square', [["path",{"d":"M20 9V7a2 2 0 0 0-2-2h-6","key":"19z8uc"}],["path",{"d":"m15 2-3 3 3 3","key":"177bxs"}],["path",{"d":"M20 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2","key":"d36hnl"}]])
export const RotateCw = ssrIcon('rotate-cw', [["path",{"d":"M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8","key":"1p45f6"}],["path",{"d":"M21 3v5h-5","key":"1q7to0"}]])
export const RotateCwFadingClock = ssrIcon('rotate-cw-fading-clock', [["path",{"d":"M12 3a9.75 9.75 0 0 1 6.74 2.74","key":"1k3kxf"}],["path",{"d":"M18.74 5.74 21 8","key":"1eb40o"}],["path",{"d":"M21 8V3","key":"1et280"}],["path",{"d":"M7.5 19.794c-6-3.464-6-12.124 0-15.588","key":"19r0lp"}],["path",{"d":"M7.5 4.206A9 9 0 0 1 12 3","key":"s8r11"}],["path",{"d":"M12 7v5l4 2","key":"1fdv2h"}],["path",{"d":"M14 20.775A9 9 0 0 1 12 21","key":"184rgu"}],["path",{"d":"M19 17.656a9 9 0 0 1-1.5 1.456","key":"7qgp6l"}],["path",{"d":"M21 12a9 9 0 0 1-.228 2","key":"1h378y"}],["path",{"d":"M21 8h-5","key":"k0yzmk"}]])
export const RotateCwSquare = ssrIcon('rotate-cw-square', [["path",{"d":"M12 5H6a2 2 0 0 0-2 2v3","key":"l96uqu"}],["path",{"d":"m9 8 3-3-3-3","key":"1gzgc3"}],["path",{"d":"M4 14v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2","key":"1w2k5h"}]])
export const Route = ssrIcon('route', [["circle",{"cx":"6","cy":"19","r":"3","key":"1kj8tv"}],["path",{"d":"M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15","key":"1d8sl"}],["circle",{"cx":"18","cy":"5","r":"3","key":"gq8acd"}]])
export const RouteOff = ssrIcon('route-off', [["circle",{"cx":"6","cy":"19","r":"3","key":"1kj8tv"}],["path",{"d":"M9 19h8.5c.4 0 .9-.1 1.3-.2","key":"1effex"}],["path",{"d":"M5.2 5.2A3.5 3.53 0 0 0 6.5 12H12","key":"k9y2ds"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M21 15.3a3.5 3.5 0 0 0-3.3-3.3","key":"11nlu2"}],["path",{"d":"M15 5h-4.3","key":"6537je"}],["circle",{"cx":"18","cy":"5","r":"3","key":"gq8acd"}]])
export const Router = ssrIcon('router', [["rect",{"width":"20","height":"8","x":"2","y":"14","rx":"2","key":"w68u3i"}],["path",{"d":"M6.01 18H6","key":"19vcac"}],["path",{"d":"M10.01 18H10","key":"uamcmx"}],["path",{"d":"M15 10v4","key":"qjz1xs"}],["path",{"d":"M17.84 7.17a4 4 0 0 0-5.66 0","key":"1rif40"}],["path",{"d":"M20.66 4.34a8 8 0 0 0-11.31 0","key":"6a5xfq"}]])
export const Rows2 = ssrIcon('rows-2', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M3 12h18","key":"1i2n21"}]])
export const Rows4 = ssrIcon('rows-4', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M21 7.5H3","key":"1hm9pq"}],["path",{"d":"M21 12H3","key":"2avoz0"}],["path",{"d":"M21 16.5H3","key":"n7jzkj"}]])
export const Rss = ssrIcon('rss', [["path",{"d":"M4 11a9 9 0 0 1 9 9","key":"pv89mb"}],["path",{"d":"M4 4a16 16 0 0 1 16 16","key":"k0647b"}],["circle",{"cx":"5","cy":"19","r":"1","key":"bfqh0e"}]])
export const Ruler = ssrIcon('ruler', [["path",{"d":"M21.3 15.3a2.4 2.4 0 0 1 0 3.4l-2.6 2.6a2.4 2.4 0 0 1-3.4 0L2.7 8.7a2.41 2.41 0 0 1 0-3.4l2.6-2.6a2.41 2.41 0 0 1 3.4 0Z","key":"icamh8"}],["path",{"d":"m14.5 12.5 2-2","key":"inckbg"}],["path",{"d":"m11.5 9.5 2-2","key":"fmmyf7"}],["path",{"d":"m8.5 6.5 2-2","key":"vc6u1g"}],["path",{"d":"m17.5 15.5 2-2","key":"wo5hmg"}]])
export const RulerDimensionLine = ssrIcon('ruler-dimension-line', [["path",{"d":"M10 15v-3","key":"1pjskw"}],["path",{"d":"M14 15v-3","key":"1o1mqj"}],["path",{"d":"M18 15v-3","key":"cws6he"}],["path",{"d":"M2 8V4","key":"3jv1jz"}],["path",{"d":"M22 6H2","key":"1iqbfk"}],["path",{"d":"M22 8V4","key":"16f4ou"}],["path",{"d":"M6 15v-3","key":"1ij1qe"}],["rect",{"x":"2","y":"12","width":"20","height":"8","rx":"2","key":"1tqiko"}]])
export const RussianRuble = ssrIcon('russian-ruble', [["path",{"d":"M6 11h8a4 4 0 0 0 0-8H9v18","key":"18ai8t"}],["path",{"d":"M6 15h8","key":"1y8f6l"}]])
export const Sailboat = ssrIcon('sailboat', [["path",{"d":"M10 2v15","key":"1qf71f"}],["path",{"d":"M7 22a4 4 0 0 1-4-4 1 1 0 0 1 1-1h16a1 1 0 0 1 1 1 4 4 0 0 1-4 4z","key":"1pxcvx"}],["path",{"d":"M9.159 2.46a1 1 0 0 1 1.521-.193l9.977 8.98A1 1 0 0 1 20 13H4a1 1 0 0 1-.824-1.567z","key":"5oog16"}]])
export const Salad = ssrIcon('salad', [["path",{"d":"M7 21h10","key":"1b0cd5"}],["path",{"d":"M12 21a9 9 0 0 0 9-9H3a9 9 0 0 0 9 9Z","key":"4rw317"}],["path",{"d":"M11.38 12a2.4 2.4 0 0 1-.4-4.77 2.4 2.4 0 0 1 3.2-2.77 2.4 2.4 0 0 1 3.47-.63 2.4 2.4 0 0 1 3.37 3.37 2.4 2.4 0 0 1-1.1 3.7 2.51 2.51 0 0 1 .03 1.1","key":"10xrj0"}],["path",{"d":"m13 12 4-4","key":"1hckqy"}],["path",{"d":"M10.9 7.25A3.99 3.99 0 0 0 4 10c0 .73.2 1.41.54 2","key":"1p4srx"}]])
export const Sandwich = ssrIcon('sandwich', [["path",{"d":"m2.37 11.223 8.372-6.777a2 2 0 0 1 2.516 0l8.371 6.777","key":"f1wd0e"}],["path",{"d":"M21 15a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1h-5.25","key":"1pfu07"}],["path",{"d":"M3 15a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1h9","key":"1oq9qw"}],["path",{"d":"m6.67 15 6.13 4.6a2 2 0 0 0 2.8-.4l3.15-4.2","key":"1fnwu5"}],["rect",{"width":"20","height":"4","x":"2","y":"11","rx":"1","key":"itshg"}]])
export const Satellite = ssrIcon('satellite', [["path",{"d":"m13.5 6.5-3.148-3.148a1.205 1.205 0 0 0-1.704 0L6.352 5.648a1.205 1.205 0 0 0 0 1.704L9.5 10.5","key":"dzhfyz"}],["path",{"d":"M16.5 7.5 19 5","key":"1ltcjm"}],["path",{"d":"m17.5 10.5 3.148 3.148a1.205 1.205 0 0 1 0 1.704l-2.296 2.296a1.205 1.205 0 0 1-1.704 0L13.5 14.5","key":"nfoymv"}],["path",{"d":"M9 21a6 6 0 0 0-6-6","key":"1iajcf"}],["path",{"d":"M9.352 10.648a1.205 1.205 0 0 0 0 1.704l2.296 2.296a1.205 1.205 0 0 0 1.704 0l4.296-4.296a1.205 1.205 0 0 0 0-1.704l-2.296-2.296a1.205 1.205 0 0 0-1.704 0z","key":"nv9zqy"}]])
export const SatelliteDish = ssrIcon('satellite-dish', [["path",{"d":"M4 10a7.31 7.31 0 0 0 10 10Z","key":"1fzpp3"}],["path",{"d":"m9 15 3-3","key":"88sc13"}],["path",{"d":"M17 13a6 6 0 0 0-6-6","key":"15cc6u"}],["path",{"d":"M21 13A10 10 0 0 0 11 3","key":"11nf8s"}]])
export const SaudiRiyal = ssrIcon('saudi-riyal', [["path",{"d":"m20 19.5-5.5 1.2","key":"1aenhr"}],["path",{"d":"M14.5 4v11.22a1 1 0 0 0 1.242.97L20 15.2","key":"2rtezt"}],["path",{"d":"m2.978 19.351 5.549-1.363A2 2 0 0 0 10 16V2","key":"1kbm92"}],["path",{"d":"M20 10 4 13.5","key":"8nums9"}]])
export const Save = ssrIcon('save', [["path",{"d":"M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z","key":"1c8476"}],["path",{"d":"M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7","key":"1ydtos"}],["path",{"d":"M7 3v4a1 1 0 0 0 1 1h7","key":"t51u73"}]])
export const SaveAll = ssrIcon('save-all', [["path",{"d":"M10 2v3a1 1 0 0 0 1 1h5","key":"1xspal"}],["path",{"d":"M18 18v-6a1 1 0 0 0-1-1h-6a1 1 0 0 0-1 1v6","key":"1ra60u"}],["path",{"d":"M18 22H4a2 2 0 0 1-2-2V6","key":"pblm9e"}],["path",{"d":"M8 18a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9.172a2 2 0 0 1 1.414.586l2.828 2.828A2 2 0 0 1 22 6.828V16a2 2 0 0 1-2.01 2z","key":"1yve0x"}]])
export const SaveCheck = ssrIcon('save-check', [["path",{"d":"M12.5 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h10.2a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4v4.35","key":"6jbevg"}],["path",{"d":"m16 19 2 2 4-4","key":"1b14m6"}],["path",{"d":"M17 15.13V14a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7","key":"1bzeol"}],["path",{"d":"M7 3v4a1 1 0 0 0 1 1h7","key":"t51u73"}]])
export const SaveOff = ssrIcon('save-off', [["path",{"d":"M13 13H8a1 1 0 0 0-1 1v7","key":"h8g396"}],["path",{"d":"M14 8h1","key":"1lfen6"}],["path",{"d":"M17 21v-4","key":"1yknxs"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M20.41 20.41A2 2 0 0 1 19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 .59-1.41","key":"1t4vdl"}],["path",{"d":"M29.5 11.5s5 5 4 5","key":"zzn4i6"}],["path",{"d":"M9 3h6.2a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V15","key":"24cby9"}]])
export const SavePen = ssrIcon('save-pen', [["path",{"d":"M13.33 13H8a1 1 0 00-1 1v7","key":"60fs50"}],["path",{"d":"M14.363 17.634a2 2 0 00-.506.854l-.837 2.87a.5.5 0 00.62.62l2.87-.837a2 2 0 00.854-.506l4.013-4.009a1 1 0 10-3.004-3.004z","key":"dpj1he"}],["path",{"d":"M7 3v4a1 1 0 001 1h7","key":"vkun1b"}],["path",{"d":"M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h10.2a2 2 0 011.4.6l3.8 3.8a2 2 0 01.6 1.4v.3","key":"1oj3yb"}]])
export const SavePlus = ssrIcon('save-plus', [["path",{"d":"M12.5 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h10.2a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V12","key":"bhibzn"}],["path",{"d":"M16 13H8a1 1 0 0 0-1 1v7","key":"164ge7"}],["path",{"d":"M19 22v-6","key":"qhmiwi"}],["path",{"d":"M22 19h-6","key":"vcuq98"}],["path",{"d":"M7 3v4a1 1 0 0 0 1 1h7","key":"t51u73"}]])
export const Scale = ssrIcon('scale', [["path",{"d":"M12 3v18","key":"108xh3"}],["path",{"d":"m19 8 3 8a5 5 0 0 1-6 0zV7","key":"zcdpyk"}],["path",{"d":"M3 7h1a17 17 0 0 0 8-2 17 17 0 0 0 8 2h1","key":"1yorad"}],["path",{"d":"m5 8 3 8a5 5 0 0 1-6 0zV7","key":"eua70x"}],["path",{"d":"M7 21h10","key":"1b0cd5"}]])
export const Scale3d = ssrIcon('scale-3d', [["path",{"d":"M5 7v11a1 1 0 0 0 1 1h11","key":"13dt1j"}],["path",{"d":"M5.293 18.707 11 13","key":"ezgbsx"}],["circle",{"cx":"19","cy":"19","r":"2","key":"17f5cg"}],["circle",{"cx":"5","cy":"5","r":"2","key":"1gwv83"}]])
export const Scaling = ssrIcon('scaling', [["path",{"d":"M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7","key":"1m0v6g"}],["path",{"d":"M14 15H9v-5","key":"pi4jk9"}],["path",{"d":"M16 3h5v5","key":"1806ms"}],["path",{"d":"M21 3 9 15","key":"15kdhq"}]])
export const Scan = ssrIcon('scan', [["path",{"d":"M3 7V5a2 2 0 0 1 2-2h2","key":"aa7l1z"}],["path",{"d":"M17 3h2a2 2 0 0 1 2 2v2","key":"4qcy5o"}],["path",{"d":"M21 17v2a2 2 0 0 1-2 2h-2","key":"6vwrx8"}],["path",{"d":"M7 21H5a2 2 0 0 1-2-2v-2","key":"ioqczr"}]])
export const ScanBarcode = ssrIcon('scan-barcode', [["path",{"d":"M3 7V5a2 2 0 0 1 2-2h2","key":"aa7l1z"}],["path",{"d":"M17 3h2a2 2 0 0 1 2 2v2","key":"4qcy5o"}],["path",{"d":"M21 17v2a2 2 0 0 1-2 2h-2","key":"6vwrx8"}],["path",{"d":"M7 21H5a2 2 0 0 1-2-2v-2","key":"ioqczr"}],["path",{"d":"M8 7v10","key":"23sfjj"}],["path",{"d":"M12 7v10","key":"jspqdw"}],["path",{"d":"M17 7v10","key":"578dap"}]])
export const ScanBox = ssrIcon('scan-box', [["path",{"d":"M12 12v5.5","key":"1fezw7"}],["path",{"d":"M17 3h2a2 2 0 012 2v2","key":"sxhzt8"}],["path",{"d":"M21 17v2a2 2 0 01-2 2h-2","key":"b4b27w"}],["path",{"d":"M3 7V5a2 2 0 012-2h2","key":"5quapj"}],["path",{"d":"M7 21H5a2 2 0 01-2-2v-2","key":"rx7q13"}],["path",{"d":"M7.264 9.252 12 12l4.737-2.748","key":"176tmc"}],["path",{"d":"M7.995 8.514A2 2 0 007 10.244v3.516a2 2 0 00.996 1.73l3 1.74a2 2 0 002.008 0l3-1.74A2 2 0 0017 13.76v-3.517a2 2 0 00-.995-1.73l-3-1.742a2 2 0 00-1.892-.064z","key":"7zy66p"}]])
export const ScanEye = ssrIcon('scan-eye', [["path",{"d":"M3 7V5a2 2 0 0 1 2-2h2","key":"aa7l1z"}],["path",{"d":"M17 3h2a2 2 0 0 1 2 2v2","key":"4qcy5o"}],["path",{"d":"M21 17v2a2 2 0 0 1-2 2h-2","key":"6vwrx8"}],["path",{"d":"M7 21H5a2 2 0 0 1-2-2v-2","key":"ioqczr"}],["circle",{"cx":"12","cy":"12","r":"1","key":"41hilf"}],["path",{"d":"M18.944 12.33a1 1 0 0 0 0-.66 7.5 7.5 0 0 0-13.888 0 1 1 0 0 0 0 .66 7.5 7.5 0 0 0 13.888 0","key":"11ak4c"}]])
export const ScanFace = ssrIcon('scan-face', [["path",{"d":"M3 7V5a2 2 0 0 1 2-2h2","key":"aa7l1z"}],["path",{"d":"M17 3h2a2 2 0 0 1 2 2v2","key":"4qcy5o"}],["path",{"d":"M21 17v2a2 2 0 0 1-2 2h-2","key":"6vwrx8"}],["path",{"d":"M7 21H5a2 2 0 0 1-2-2v-2","key":"ioqczr"}],["path",{"d":"M8 14s1.5 2 4 2 4-2 4-2","key":"1y1vjs"}],["path",{"d":"M9 9h.01","key":"1q5me6"}],["path",{"d":"M15 9h.01","key":"x1ddxp"}]])
export const ScanHeart = ssrIcon('scan-heart', [["path",{"d":"M17 3h2a2 2 0 0 1 2 2v2","key":"4qcy5o"}],["path",{"d":"M21 17v2a2 2 0 0 1-2 2h-2","key":"6vwrx8"}],["path",{"d":"M3 7V5a2 2 0 0 1 2-2h2","key":"aa7l1z"}],["path",{"d":"M7 21H5a2 2 0 0 1-2-2v-2","key":"ioqczr"}],["path",{"d":"M7.828 13.07A3 3 0 0 1 12 8.764a3 3 0 0 1 4.172 4.306l-3.447 3.62a1 1 0 0 1-1.449 0z","key":"1ak1ef"}]])
export const ScanLine = ssrIcon('scan-line', [["path",{"d":"M3 7V5a2 2 0 0 1 2-2h2","key":"aa7l1z"}],["path",{"d":"M17 3h2a2 2 0 0 1 2 2v2","key":"4qcy5o"}],["path",{"d":"M21 17v2a2 2 0 0 1-2 2h-2","key":"6vwrx8"}],["path",{"d":"M7 21H5a2 2 0 0 1-2-2v-2","key":"ioqczr"}],["path",{"d":"M7 12h10","key":"b7w52i"}]])
export const ScanQrCode = ssrIcon('scan-qr-code', [["path",{"d":"M17 12v4a1 1 0 0 1-1 1h-4","key":"uk4fdo"}],["path",{"d":"M17 3h2a2 2 0 0 1 2 2v2","key":"4qcy5o"}],["path",{"d":"M17 8V7","key":"q2g9wo"}],["path",{"d":"M21 17v2a2 2 0 0 1-2 2h-2","key":"6vwrx8"}],["path",{"d":"M3 7V5a2 2 0 0 1 2-2h2","key":"aa7l1z"}],["path",{"d":"M7 17h.01","key":"19xn7k"}],["path",{"d":"M7 21H5a2 2 0 0 1-2-2v-2","key":"ioqczr"}],["rect",{"x":"7","y":"7","width":"5","height":"5","rx":"1","key":"m9kyts"}]])
export const ScanSearch = ssrIcon('scan-search', [["path",{"d":"M3 7V5a2 2 0 0 1 2-2h2","key":"aa7l1z"}],["path",{"d":"M17 3h2a2 2 0 0 1 2 2v2","key":"4qcy5o"}],["path",{"d":"M21 17v2a2 2 0 0 1-2 2h-2","key":"6vwrx8"}],["path",{"d":"M7 21H5a2 2 0 0 1-2-2v-2","key":"ioqczr"}],["circle",{"cx":"12","cy":"12","r":"3","key":"1v7zrd"}],["path",{"d":"m16 16-1.9-1.9","key":"1dq9hf"}]])
export const ScanSquare = ssrIcon('scan-square', [["path",{"d":"M3 7V5a2 2 0 0 1 2-2h2","key":"aa7l1z"}],["path",{"d":"M17 3h2a2 2 0 0 1 2 2v2","key":"4qcy5o"}],["path",{"d":"M21 17v2a2 2 0 0 1-2 2h-2","key":"6vwrx8"}],["path",{"d":"M7 21H5a2 2 0 0 1-2-2v-2","key":"ioqczr"}],["rect",{"width":"8","height":"8","x":"8","y":"8","rx":"1","key":"69yp3k"}]])
export const ScanText = ssrIcon('scan-text', [["path",{"d":"M3 7V5a2 2 0 0 1 2-2h2","key":"aa7l1z"}],["path",{"d":"M17 3h2a2 2 0 0 1 2 2v2","key":"4qcy5o"}],["path",{"d":"M21 17v2a2 2 0 0 1-2 2h-2","key":"6vwrx8"}],["path",{"d":"M7 21H5a2 2 0 0 1-2-2v-2","key":"ioqczr"}],["path",{"d":"M7 8h8","key":"1jbsf9"}],["path",{"d":"M7 12h10","key":"b7w52i"}],["path",{"d":"M7 16h6","key":"1vyc9m"}]])
export const School = ssrIcon('school', [["path",{"d":"M14 21v-3a2 2 0 0 0-4 0v3","key":"1rgiei"}],["path",{"d":"M18 4.933V21","key":"tjwmp4"}],["path",{"d":"m4 6 7.106-3.79a2 2 0 0 1 1.788 0L20 6","key":"zywc2d"}],["path",{"d":"m6 11-3.52 2.147a1 1 0 0 0-.48.854V19a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-5a1 1 0 0 0-.48-.853L18 11","key":"1d4ql0"}],["path",{"d":"M6 4.933V21","key":"1ufz1j"}],["circle",{"cx":"12","cy":"9","r":"2","key":"1092wv"}]])
export const University = ssrIcon('university', [["path",{"d":"M14 21v-3a2 2 0 0 0-4 0v3","key":"1rgiei"}],["path",{"d":"M18 12h.01","key":"yjnet6"}],["path",{"d":"M18 16h.01","key":"plv8zi"}],["path",{"d":"M22 7a1 1 0 0 0-1-1h-2a2 2 0 0 1-1.143-.359L13.143 2.36a2 2 0 0 0-2.286-.001L6.143 5.64A2 2 0 0 1 5 6H3a1 1 0 0 0-1 1v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2z","key":"1ogmi3"}],["path",{"d":"M6 12h.01","key":"c2rlol"}],["path",{"d":"M6 16h.01","key":"1pmjb7"}],["circle",{"cx":"12","cy":"10","r":"2","key":"1yojzk"}]])
export const Scissors = ssrIcon('scissors', [["circle",{"cx":"6","cy":"6","r":"3","key":"1lh9wr"}],["path",{"d":"M8.12 8.12 12 12","key":"1alkpv"}],["path",{"d":"M20 4 8.12 15.88","key":"xgtan2"}],["circle",{"cx":"6","cy":"18","r":"3","key":"fqmcym"}],["path",{"d":"M14.8 14.8 20 20","key":"ptml3r"}]])
export const ScissorsLineDashed = ssrIcon('scissors-line-dashed', [["path",{"d":"M5.42 9.42 8 12","key":"12pkuq"}],["circle",{"cx":"4","cy":"8","r":"2","key":"107mxr"}],["path",{"d":"m14 6-8.58 8.58","key":"gvzu5l"}],["circle",{"cx":"4","cy":"16","r":"2","key":"1ehqvc"}],["path",{"d":"M10.8 14.8 14 18","key":"ax7m9r"}],["path",{"d":"M16 12h-2","key":"10asgb"}],["path",{"d":"M22 12h-2","key":"14jgyd"}]])
export const SquareScissors = ssrIcon('square-scissors', [["path",{"d":"m17 17-2.18-2.18","key":"1y7dt1"}],["path",{"d":"M9.56 14.44 17 7","key":"ue8l15"}],["path",{"d":"M9.56 9.56 12 12","key":"rml9qv"}],["circle",{"cx":"8.5","cy":"15.5","r":"1.5","key":"12hfy1"}],["circle",{"cx":"8.5","cy":"8.5","r":"1.5","key":"cn5opk"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const SquareBottomDashedScissors = ssrIcon('square-bottom-dashed-scissors', [["path",{"d":"M14 21h1","key":"v9vybs"}],["path",{"d":"m17 17-2.18-2.18","key":"1y7dt1"}],["path",{"d":"M5 21a2 2 0 01-2-2V5a2 2 0 012-2h14a2 2 0 012 2v14a2 2 0 01-2 2","key":"2q1jq4"}],["path",{"d":"M9 21h1","key":"15o7lz"}],["path",{"d":"M9.56 14.44 17 7","key":"ue8l15"}],["path",{"d":"M9.56 9.56 12 12","key":"rml9qv"}],["circle",{"cx":"8.5","cy":"15.5","r":"1.5","key":"12hfy1"}],["circle",{"cx":"8.5","cy":"8.5","r":"1.5","key":"cn5opk"}]])
export const Scooter = ssrIcon('scooter', [["path",{"d":"M21 4h-3.5l2 11.05","key":"1gktiw"}],["path",{"d":"M6.95 17h5.142c.523 0 .95-.406 1.063-.916a6.5 6.5 0 0 1 5.345-5.009","key":"1bq3u3"}],["circle",{"cx":"19.5","cy":"17.5","r":"2.5","key":"e4zhv9"}],["circle",{"cx":"4.5","cy":"17.5","r":"2.5","key":"50vk4p"}]])
export const ScreenShare = ssrIcon('screen-share', [["path",{"d":"M13 3H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-3","key":"i8wdob"}],["path",{"d":"M8 21h8","key":"1ev6f3"}],["path",{"d":"M12 17v4","key":"1riwvh"}],["path",{"d":"m17 8 5-5","key":"fqif7o"}],["path",{"d":"M17 3h5v5","key":"1o3tu8"}]])
export const ScreenShareOff = ssrIcon('screen-share-off', [["path",{"d":"M13 3H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-3","key":"i8wdob"}],["path",{"d":"M8 21h8","key":"1ev6f3"}],["path",{"d":"M12 17v4","key":"1riwvh"}],["path",{"d":"m22 3-5 5","key":"12jva0"}],["path",{"d":"m17 3 5 5","key":"k36vhe"}]])
export const Scroll = ssrIcon('scroll', [["path",{"d":"M19 17V5a2 2 0 0 0-2-2H4","key":"zz82l3"}],["path",{"d":"M8 21h12a2 2 0 0 0 2-2v-1a1 1 0 0 0-1-1H11a1 1 0 0 0-1 1v1a2 2 0 1 1-4 0V5a2 2 0 1 0-4 0v2a1 1 0 0 0 1 1h3","key":"1ph1d7"}]])
export const ScrollText = ssrIcon('scroll-text', [["path",{"d":"M15 12h-5","key":"r7krc0"}],["path",{"d":"M15 8h-5","key":"1khuty"}],["path",{"d":"M19 17V5a2 2 0 0 0-2-2H4","key":"zz82l3"}],["path",{"d":"M8 21h12a2 2 0 0 0 2-2v-1a1 1 0 0 0-1-1H11a1 1 0 0 0-1 1v1a2 2 0 1 1-4 0V5a2 2 0 1 0-4 0v2a1 1 0 0 0 1 1h3","key":"1ph1d7"}]])
export const Search = ssrIcon('search', [["path",{"d":"m21 21-4.34-4.34","key":"14j7rj"}],["circle",{"cx":"11","cy":"11","r":"8","key":"4ej97u"}]])
export const SearchAlert = ssrIcon('search-alert', [["circle",{"cx":"11","cy":"11","r":"8","key":"4ej97u"}],["path",{"d":"m21 21-4.3-4.3","key":"1qie3q"}],["path",{"d":"M11 7v4","key":"m2edmq"}],["path",{"d":"M11 15h.01","key":"k85uqc"}]])
export const SearchCheck = ssrIcon('search-check', [["path",{"d":"m8 11 2 2 4-4","key":"1sed1v"}],["circle",{"cx":"11","cy":"11","r":"8","key":"4ej97u"}],["path",{"d":"m21 21-4.3-4.3","key":"1qie3q"}]])
export const SearchCode = ssrIcon('search-code', [["path",{"d":"m13 13.5 2-2.5-2-2.5","key":"1rvxrh"}],["path",{"d":"m21 21-4.3-4.3","key":"1qie3q"}],["path",{"d":"M9 8.5 7 11l2 2.5","key":"6ffwbx"}],["circle",{"cx":"11","cy":"11","r":"8","key":"4ej97u"}]])
export const SearchSlash = ssrIcon('search-slash', [["path",{"d":"m13.5 8.5-5 5","key":"1cs55j"}],["circle",{"cx":"11","cy":"11","r":"8","key":"4ej97u"}],["path",{"d":"m21 21-4.3-4.3","key":"1qie3q"}]])
export const SearchX = ssrIcon('search-x', [["path",{"d":"m13.5 8.5-5 5","key":"1cs55j"}],["path",{"d":"m8.5 8.5 5 5","key":"a8mexj"}],["circle",{"cx":"11","cy":"11","r":"8","key":"4ej97u"}],["path",{"d":"m21 21-4.3-4.3","key":"1qie3q"}]])
export const Section = ssrIcon('section', [["path",{"d":"M16 5a4 3 0 0 0-8 0c0 4 8 3 8 7a4 3 0 0 1-8 0","key":"vqan6v"}],["path",{"d":"M8 19a4 3 0 0 0 8 0c0-4-8-3-8-7a4 3 0 0 1 8 0","key":"wdjd8o"}]])
export const Send = ssrIcon('send', [["path",{"d":"M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z","key":"1ffxy3"}],["path",{"d":"m21.854 2.147-10.94 10.939","key":"12cjpa"}]])
export const SendHorizontal = ssrIcon('send-horizontal', [["path",{"d":"M3.714 3.048a.498.498 0 0 0-.683.627l2.843 7.627a2 2 0 0 1 0 1.396l-2.842 7.627a.498.498 0 0 0 .682.627l18-8.5a.5.5 0 0 0 0-.904z","key":"117uat"}],["path",{"d":"M6 12h16","key":"s4cdu5"}]])
export const SendToBack = ssrIcon('send-to-back', [["rect",{"x":"14","y":"14","width":"8","height":"8","rx":"2","key":"1b0bso"}],["rect",{"x":"2","y":"2","width":"8","height":"8","rx":"2","key":"1x09vl"}],["path",{"d":"M7 14v1a2 2 0 0 0 2 2h1","key":"pao6x6"}],["path",{"d":"M14 7h1a2 2 0 0 1 2 2v1","key":"19tdru"}]])
export const SeparatorHorizontal = ssrIcon('separator-horizontal', [["path",{"d":"m16 16-4 4-4-4","key":"3dv8je"}],["path",{"d":"M3 12h18","key":"1i2n21"}],["path",{"d":"m8 8 4-4 4 4","key":"2bscm2"}]])
export const SeparatorVertical = ssrIcon('separator-vertical', [["path",{"d":"M12 3v18","key":"108xh3"}],["path",{"d":"m16 16 4-4-4-4","key":"1js579"}],["path",{"d":"m8 8-4 4 4 4","key":"1whems"}]])
export const Server = ssrIcon('server', [["rect",{"width":"20","height":"8","x":"2","y":"2","rx":"2","ry":"2","key":"ngkwjq"}],["rect",{"width":"20","height":"8","x":"2","y":"14","rx":"2","ry":"2","key":"iecqi9"}],["line",{"x1":"6","x2":"6.01","y1":"6","y2":"6","key":"16zg32"}],["line",{"x1":"6","x2":"6.01","y1":"18","y2":"18","key":"nzw8ys"}]])
export const ServerCog = ssrIcon('server-cog', [["path",{"d":"m10.852 14.772-.383.923","key":"11vil6"}],["path",{"d":"M13.148 14.772a3 3 0 1 0-2.296-5.544l-.383-.923","key":"1v3clb"}],["path",{"d":"m13.148 9.228.383-.923","key":"t2zzyc"}],["path",{"d":"m13.53 15.696-.382-.924a3 3 0 1 1-2.296-5.544","key":"1bxfiv"}],["path",{"d":"m14.772 10.852.923-.383","key":"k9m8cz"}],["path",{"d":"m14.772 13.148.923.383","key":"1xvhww"}],["path",{"d":"M4.5 10H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-.5","key":"tn8das"}],["path",{"d":"M4.5 14H4a2 2 0 0 0-2 2v4a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-4a2 2 0 0 0-2-2h-.5","key":"1g2pve"}],["path",{"d":"M6 18h.01","key":"uhywen"}],["path",{"d":"M6 6h.01","key":"1utrut"}],["path",{"d":"m9.228 10.852-.923-.383","key":"1wtb30"}],["path",{"d":"m9.228 13.148-.923.383","key":"1a830x"}]])
export const ServerCrash = ssrIcon('server-crash', [["path",{"d":"M6 10H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-2","key":"4b9dqc"}],["path",{"d":"M6 14H4a2 2 0 0 0-2 2v4a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-4a2 2 0 0 0-2-2h-2","key":"22nnkd"}],["path",{"d":"M6 6h.01","key":"1utrut"}],["path",{"d":"M6 18h.01","key":"uhywen"}],["path",{"d":"m13 6-4 6h6l-4 6","key":"14hqih"}]])
export const ServerOff = ssrIcon('server-off', [["path",{"d":"M7 2h13a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-5","key":"bt2siv"}],["path",{"d":"M10 10 2.5 2.5C2 2 2 2.5 2 5v3a2 2 0 0 0 2 2h6z","key":"1hjrv1"}],["path",{"d":"M22 17v-1a2 2 0 0 0-2-2h-1","key":"1iynyr"}],["path",{"d":"M4 14a2 2 0 0 0-2 2v4a2 2 0 0 0 2 2h16.5l1-.5.5.5-8-8H4z","key":"161ggg"}],["path",{"d":"M6 18h.01","key":"uhywen"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}]])
export const ServerPlus = ssrIcon('server-plus', [["path",{"d":"M12.5 10H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v2","key":"s66i12"}],["path",{"d":"M16 12h6","key":"15xry1"}],["path",{"d":"M19 9v6","key":"1kf5t6"}],["path",{"d":"M22 18v2a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h8.5","key":"lo70fm"}],["path",{"d":"M6 18h.01","key":"uhywen"}],["path",{"d":"M6 6h.01","key":"1utrut"}]])
export const Settings = ssrIcon('settings', [["path",{"d":"M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915","key":"1i5ecw"}],["circle",{"cx":"12","cy":"12","r":"3","key":"1v7zrd"}]])
export const Settings2 = ssrIcon('settings-2', [["path",{"d":"M14 17H5","key":"gfn3mx"}],["path",{"d":"M19 7h-9","key":"6i9tg"}],["circle",{"cx":"17","cy":"17","r":"3","key":"18b49y"}],["circle",{"cx":"7","cy":"7","r":"3","key":"dfmy0x"}]])
export const Shapes = ssrIcon('shapes', [["path",{"d":"M8.3 10a.7.7 0 0 1-.626-1.079L11.4 3a.7.7 0 0 1 1.198-.043L16.3 8.9a.7.7 0 0 1-.572 1.1Z","key":"1bo67w"}],["rect",{"x":"3","y":"14","width":"7","height":"7","rx":"1","key":"1bkyp8"}],["circle",{"cx":"17.5","cy":"17.5","r":"3.5","key":"w3z12y"}]])
export const Share = ssrIcon('share', [["path",{"d":"M12 2v13","key":"1km8f5"}],["path",{"d":"m16 6-4-4-4 4","key":"13yo43"}],["path",{"d":"M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8","key":"1b2hhj"}]])
export const Share2 = ssrIcon('share-2', [["circle",{"cx":"18","cy":"5","r":"3","key":"gq8acd"}],["circle",{"cx":"6","cy":"12","r":"3","key":"w7nqdw"}],["circle",{"cx":"18","cy":"19","r":"3","key":"1xt0gg"}],["line",{"x1":"8.59","x2":"15.42","y1":"13.51","y2":"17.49","key":"47mynk"}],["line",{"x1":"15.41","x2":"8.59","y1":"6.51","y2":"10.49","key":"1n3mei"}]])
export const Sheet = ssrIcon('sheet', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","ry":"2","key":"1m3agn"}],["line",{"x1":"3","x2":"21","y1":"9","y2":"9","key":"1vqk6q"}],["line",{"x1":"3","x2":"21","y1":"15","y2":"15","key":"o2sbyz"}],["line",{"x1":"9","x2":"9","y1":"9","y2":"21","key":"1ib60c"}],["line",{"x1":"15","x2":"15","y1":"9","y2":"21","key":"1n26ft"}]])
export const Shell = ssrIcon('shell', [["path",{"d":"M14 11a2 2 0 1 1-4 0 4 4 0 0 1 8 0 6 6 0 0 1-12 0 8 8 0 0 1 16 0 10 10 0 1 1-20 0 11.93 11.93 0 0 1 2.42-7.22 2 2 0 1 1 3.16 2.44","key":"1cn552"}]])
export const ShelvingUnit = ssrIcon('shelving-unit', [["path",{"d":"M12 12V9a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3","key":"wiz68x"}],["path",{"d":"M16 20v-3a1 1 0 0 0-1-1h-2a1 1 0 0 0-1 1v3","key":"1b59c4"}],["path",{"d":"M20 22V2","key":"1bnhr8"}],["path",{"d":"M4 12h16","key":"1lakjw"}],["path",{"d":"M4 20h16","key":"14thso"}],["path",{"d":"M4 2v20","key":"gtpd5x"}],["path",{"d":"M4 4h16","key":"1bkgr1"}]])
export const Shield = ssrIcon('shield', [["path",{"d":"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z","key":"oel41y"}]])
export const ShieldAlert = ssrIcon('shield-alert', [["path",{"d":"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z","key":"oel41y"}],["path",{"d":"M12 8v4","key":"1got3b"}],["path",{"d":"M12 16h.01","key":"1drbdi"}]])
export const ShieldBan = ssrIcon('shield-ban', [["path",{"d":"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z","key":"oel41y"}],["path",{"d":"m4.243 5.21 14.39 12.472","key":"1c9a7c"}]])
export const ShieldCheck = ssrIcon('shield-check', [["path",{"d":"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z","key":"oel41y"}],["path",{"d":"m9 12 2 2 4-4","key":"dzmm74"}]])
export const ShieldX = ssrIcon('shield-x', [["path",{"d":"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z","key":"oel41y"}],["path",{"d":"m14.5 9.5-5 5","key":"17q4r4"}],["path",{"d":"m9.5 9.5 5 5","key":"18nt4w"}]])
export const ShieldCog = ssrIcon('shield-cog', [["path",{"d":"m10.929 14.467-.383.924","key":"hdyevy"}],["path",{"d":"M10.929 8.923 10.546 8","key":"1nr44d"}],["path",{"d":"M13.225 8.923 13.608 8","key":"aewley"}],["path",{"d":"m13.607 15.391-.382-.924","key":"m37gf1"}],["path",{"d":"m14.849 10.547.923-.383","key":"1d3c4q"}],["path",{"d":"m14.849 12.843.923.383","key":"lmvhy3"}],["path",{"d":"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z","key":"oel41y"}],["path",{"d":"m9.305 10.547-.923-.383","key":"1d13ox"}],["path",{"d":"m9.305 12.843-.923.383","key":"7wxwh5"}],["circle",{"cx":"12.077","cy":"11.695","r":"3","key":"fse9k8"}]])
export const ShieldCogCorner = ssrIcon('shield-cog-corner', [["path",{"d":"M11 22c-3.806-1.45-7-3.966-7-9V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1v4","key":"hf1sz5"}],["path",{"d":"M14.923 16.547 14 16.164","key":"41f878"}],["path",{"d":"m14.923 18.843-.923.383","key":"82rvv5"}],["path",{"d":"M16.547 14.923 16.164 14","key":"1r7ypn"}],["path",{"d":"m16.547 20.467-.383.924","key":"au4kyj"}],["path",{"d":"m18.843 14.923.383-.923","key":"1cbrwq"}],["path",{"d":"m19.225 21.391-.382-.924","key":"1u2bh9"}],["path",{"d":"m20.467 16.547.923-.383","key":"cprboc"}],["path",{"d":"m20.467 18.843.923.383","key":"inm8l2"}],["circle",{"cx":"17.695","cy":"17.695","r":"3","key":"1i1rmh"}]])
export const ShieldEllipsis = ssrIcon('shield-ellipsis', [["path",{"d":"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z","key":"oel41y"}],["path",{"d":"M8 12h.01","key":"czm47f"}],["path",{"d":"M12 12h.01","key":"1mp3jc"}],["path",{"d":"M16 12h.01","key":"1l6xoz"}]])
export const ShieldHalf = ssrIcon('shield-half', [["path",{"d":"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z","key":"oel41y"}],["path",{"d":"M12 22V2","key":"zs6s6o"}]])
export const ShieldKeyhole = ssrIcon('shield-keyhole', [["path",{"d":"M12 13v3","key":"gkc6qb"}],["path",{"d":"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 01-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 011-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 011.52 0C14.51 3.81 17 5 19 5a1 1 0 011 1z","key":"1buusj"}],["circle",{"cx":"12","cy":"11","r":"2","key":"1yggc4"}]])
export const ShieldLock = ssrIcon('shield-lock', [["path",{"d":"M20 9.807V6a1 1 0 00-1-1c-2 0-4.49-1.19-6.24-2.72a1.17 1.17 0 00-1.52 0C9.5 3.8 7 5 5 5a1 1 0 00-1 1v7c0 3.88 2.107 6.254 5 7.796","key":"1gl1o4"}],["path",{"d":"M19 17v-2a2 2 0 00-4 0v2","key":"uefur0"}],["rect",{"x":"13","y":"17","width":"8","height":"5","rx":"1","key":"2y8vuh"}]])
export const ShieldMinus = ssrIcon('shield-minus', [["path",{"d":"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z","key":"oel41y"}],["path",{"d":"M9 12h6","key":"1c52cq"}]])
export const ShieldOff = ssrIcon('shield-off', [["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M5 5a1 1 0 0 0-1 1v7c0 5 3.5 7.5 7.67 8.94a1 1 0 0 0 .67.01c2.35-.82 4.48-1.97 5.9-3.71","key":"1jlk70"}],["path",{"d":"M9.309 3.652A12.252 12.252 0 0 0 11.24 2.28a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1v7a9.784 9.784 0 0 1-.08 1.264","key":"18rp1v"}]])
export const ShieldPlus = ssrIcon('shield-plus', [["path",{"d":"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z","key":"oel41y"}],["path",{"d":"M9 12h6","key":"1c52cq"}],["path",{"d":"M12 9v6","key":"199k2o"}]])
export const ShieldQuestionMark = ssrIcon('shield-question-mark', [["path",{"d":"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z","key":"oel41y"}],["path",{"d":"M9.1 9a3 3 0 0 1 5.82 1c0 2-3 3-3 3","key":"mhlwft"}],["path",{"d":"M12 17h.01","key":"p32p05"}]])
export const ShieldUser = ssrIcon('shield-user', [["path",{"d":"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z","key":"oel41y"}],["path",{"d":"M6.376 18.91a6 6 0 0 1 11.249.003","key":"hnjrf2"}],["circle",{"cx":"12","cy":"11","r":"4","key":"1gt34v"}]])
export const Ship = ssrIcon('ship', [["path",{"d":"M12 2v2","key":"tus03m"}],["path",{"d":"M12 9.189V13","key":"yp40p3"}],["path",{"d":"M19 12V6a2 2 0 00-2-2H7a2 2 0 00-2 2v6","key":"1wcigf"}],["path",{"d":"M19.38 19A11.6 11.6 0 0021 13l-8.188-3.639a2 2 0 00-1.624 0L3 13.001a11.6 11.6 0 002.81 7.76","key":"1kdp0u"}],["path",{"d":"M2 20c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1s1.2 1 2.5 1c2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1","key":"1l8w7g"}]])
export const ShipCargo = ssrIcon('ship-cargo', [["path",{"d":"M12 15v-3","key":"1rb51w"}],["path",{"d":"M12 2v2","key":"tus03m"}],["path",{"d":"M16.5 12V9a1 1 0 011-1h1a1 1 0 001-1V5a1 1 0 00-1-1h-13a1 1 0 00-1 1v2a1 1 0 001 1h1a1 1 0 011 1v3","key":"1byvar"}],["path",{"d":"M19.38 19c1.076-1.815 1.636-4.89 1.628-6.008a1 1 0 00-1-.992H3.984a1 1 0 00-1 .984c-.03 1.86.97 5.621 2.826 7.776","key":"1kvu1n"}],["path",{"d":"M2 20c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1s1.2 1 2.5 1c2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1","key":"1l8w7g"}]])
export const ShipWheel = ssrIcon('ship-wheel', [["circle",{"cx":"12","cy":"12","r":"8","key":"46899m"}],["path",{"d":"M12 2v7.5","key":"1e5rl5"}],["path",{"d":"m19 5-5.23 5.23","key":"1ezxxf"}],["path",{"d":"M22 12h-7.5","key":"le1719"}],["path",{"d":"m19 19-5.23-5.23","key":"p3fmgn"}],["path",{"d":"M12 14.5V22","key":"dgcmos"}],["path",{"d":"M10.23 13.77 5 19","key":"qwopd4"}],["path",{"d":"M9.5 12H2","key":"r7bup8"}],["path",{"d":"M10.23 10.23 5 5","key":"k2y7lj"}],["circle",{"cx":"12","cy":"12","r":"2.5","key":"ix0uyj"}]])
export const Shirt = ssrIcon('shirt', [["path",{"d":"M20.38 3.46 16 2a4 4 0 0 1-8 0L3.62 3.46a2 2 0 0 0-1.34 2.23l.58 3.47a1 1 0 0 0 .99.84H6v10c0 1.1.9 2 2 2h8a2 2 0 0 0 2-2V10h2.15a1 1 0 0 0 .99-.84l.58-3.47a2 2 0 0 0-1.34-2.23z","key":"1wgbhj"}]])
export const ShoppingBag = ssrIcon('shopping-bag', [["path",{"d":"M16 10a4 4 0 0 1-8 0","key":"1ltviw"}],["path",{"d":"M3.103 6.034h17.794","key":"awc11p"}],["path",{"d":"M3.4 5.467a2 2 0 0 0-.4 1.2V20a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6.667a2 2 0 0 0-.4-1.2l-2-2.667A2 2 0 0 0 17 2H7a2 2 0 0 0-1.6.8z","key":"o988cm"}]])
export const ShoppingBasket = ssrIcon('shopping-basket', [["path",{"d":"m15 11-1 9","key":"5wnq3a"}],["path",{"d":"m19 11-4-7","key":"cnml18"}],["path",{"d":"M2 11h20","key":"3eubbj"}],["path",{"d":"m3.5 11 1.6 7.4a2 2 0 0 0 2 1.6h9.8a2 2 0 0 0 2-1.6l1.7-7.4","key":"yiazzp"}],["path",{"d":"M4.5 15.5h15","key":"13mye1"}],["path",{"d":"m5 11 4-7","key":"116ra9"}],["path",{"d":"m9 11 1 9","key":"1ojof7"}]])
export const ShoppingCart = ssrIcon('shopping-cart', [["path",{"d":"m2.05 2.05 1.099-.028a1 1 0 0 1 1.008.815l2.69 14.347A1 1 0 0 0 7.83 18H18","key":"uebgi3"}],["path",{"d":"M4.563 5h16.435a1 1 0 0 1 .981 1.204l-1.026 6.226A2 2 0 0 1 18.962 14H6.25","key":"1j7c9p"}],["circle",{"cx":"18","cy":"20","r":"2","key":"t9985n"}],["circle",{"cx":"8","cy":"20","r":"2","key":"ckkr5m"}]])
export const Shovel = ssrIcon('shovel', [["path",{"d":"M21.56 4.56a1.5 1.5 0 0 1 0 2.122l-.47.47a3 3 0 0 1-4.212-.03 3 3 0 0 1 0-4.243l.44-.44a1.5 1.5 0 0 1 2.121 0z","key":"1gcedi"}],["path",{"d":"M3 22a1 1 0 0 1-1-1v-3.586a1 1 0 0 1 .293-.707l3.355-3.355a1.205 1.205 0 0 1 1.704 0l3.296 3.296a1.205 1.205 0 0 1 0 1.704l-3.355 3.355a1 1 0 0 1-.707.293z","key":"pg9kv3"}],["path",{"d":"m9 15 7.879-7.878","key":"1o1zgh"}]])
export const ShowerHead = ssrIcon('shower-head', [["path",{"d":"m4 4 2.5 2.5","key":"uv2vmf"}],["path",{"d":"M13.5 6.5a4.95 4.95 0 0 0-7 7","key":"frdkwv"}],["path",{"d":"M15 5 5 15","key":"1ag8rq"}],["path",{"d":"M14 17v.01","key":"eokfpp"}],["path",{"d":"M10 16v.01","key":"14uyyl"}],["path",{"d":"M13 13v.01","key":"1v1k97"}],["path",{"d":"M16 10v.01","key":"5169yg"}],["path",{"d":"M11 20v.01","key":"cj92p8"}],["path",{"d":"M17 14v.01","key":"11cswd"}],["path",{"d":"M20 11v.01","key":"19e0od"}]])
export const Shredder = ssrIcon('shredder', [["path",{"d":"M4 13V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v5","key":"1eob4r"}],["path",{"d":"M14 2v5a1 1 0 0 0 1 1h5","key":"wfsgrz"}],["path",{"d":"M10 22v-5","key":"sfixh4"}],["path",{"d":"M14 19v-2","key":"pdve8j"}],["path",{"d":"M18 20v-3","key":"uox2gk"}],["path",{"d":"M2 13h20","key":"5evz65"}],["path",{"d":"M6 20v-3","key":"c6pdcb"}]])
export const Shrimp = ssrIcon('shrimp', [["path",{"d":"M11 12h.01","key":"1lr4k6"}],["path",{"d":"M13 22c.5-.5 1.12-1 2.5-1-1.38 0-2-.5-2.5-1","key":"fatpdi"}],["path",{"d":"M14 2a3.28 3.28 0 0 1-3.227 1.798l-6.17-.561A2.387 2.387 0 1 0 4.387 8H15.5a1 1 0 0 1 0 13 1 1 0 0 0 0-5H12a7 7 0 0 1-7-7V8","key":"kehrqe"}],["path",{"d":"M14 8a8.5 8.5 0 0 1 0 8","key":"1imjx2"}],["path",{"d":"M16 16c2 0 4.5-4 4-6","key":"z0nejz"}]])
export const Shrink = ssrIcon('shrink', [["path",{"d":"m15 15 6 6m-6-6v4.8m0-4.8h4.8","key":"17vawe"}],["path",{"d":"M9 19.8V15m0 0H4.2M9 15l-6 6","key":"chjx8e"}],["path",{"d":"M15 4.2V9m0 0h4.8M15 9l6-6","key":"lav6yq"}],["path",{"d":"M9 4.2V9m0 0H4.2M9 9 3 3","key":"1pxi2q"}]])
export const Shrub = ssrIcon('shrub', [["path",{"d":"M12 22v-5.172a2 2 0 0 0-.586-1.414L9.5 13.5","key":"1p17fm"}],["path",{"d":"M14.5 14.5 12 17","key":"dy5w4y"}],["path",{"d":"M17 8.8A6 6 0 0 1 13.8 20H10A6.5 6.5 0 0 1 7 8a5 5 0 0 1 10 0z","key":"6z7b3o"}]])
export const Shuffle = ssrIcon('shuffle', [["path",{"d":"m18 14 4 4-4 4","key":"10pe0f"}],["path",{"d":"m18 2 4 4-4 4","key":"pucp1d"}],["path",{"d":"M2 18h1.973a4 4 0 0 0 3.3-1.7l5.454-8.6a4 4 0 0 1 3.3-1.7H22","key":"1ailkh"}],["path",{"d":"M2 6h1.972a4 4 0 0 1 3.6 2.2","key":"km57vx"}],["path",{"d":"M22 18h-6.041a4 4 0 0 1-3.3-1.8l-.359-.45","key":"os18l9"}]])
export const Sigma = ssrIcon('sigma', [["path",{"d":"M18 7V5a1 1 0 0 0-1-1H6.5a.5.5 0 0 0-.4.8l4.5 6a2 2 0 0 1 0 2.4l-4.5 6a.5.5 0 0 0 .4.8H17a1 1 0 0 0 1-1v-2","key":"wuwx1p"}]])
export const SquareSigma = ssrIcon('square-sigma', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M16 8.9V7H8l4 5-4 5h8v-1.9","key":"9nih0i"}]])
export const Signal = ssrIcon('signal', [["path",{"d":"M2 20h.01","key":"4haj6o"}],["path",{"d":"M7 20v-4","key":"j294jx"}],["path",{"d":"M12 20v-8","key":"i3yub9"}],["path",{"d":"M17 20V8","key":"1tkaf5"}],["path",{"d":"M22 4v16","key":"sih9yq"}]])
export const SignalHigh = ssrIcon('signal-high', [["path",{"d":"M2 20h.01","key":"4haj6o"}],["path",{"d":"M7 20v-4","key":"j294jx"}],["path",{"d":"M12 20v-8","key":"i3yub9"}],["path",{"d":"M17 20V8","key":"1tkaf5"}]])
export const SignalLow = ssrIcon('signal-low', [["path",{"d":"M2 20h.01","key":"4haj6o"}],["path",{"d":"M7 20v-4","key":"j294jx"}]])
export const SignalMedium = ssrIcon('signal-medium', [["path",{"d":"M2 20h.01","key":"4haj6o"}],["path",{"d":"M7 20v-4","key":"j294jx"}],["path",{"d":"M12 20v-8","key":"i3yub9"}]])
export const SignalZero = ssrIcon('signal-zero', [["path",{"d":"M2 20h.01","key":"4haj6o"}]])
export const Signature = ssrIcon('signature', [["path",{"d":"m21 17-2.156-1.868A.5.5 0 0 0 18 15.5v.5a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1c0-2.545-3.991-3.97-8.5-4a1 1 0 0 0 0 5c4.153 0 4.745-11.295 5.708-13.5a2.5 2.5 0 1 1 3.31 3.284","key":"y32ogt"}],["path",{"d":"M3 21h18","key":"itz85i"}]])
export const Signpost = ssrIcon('signpost', [["path",{"d":"M12 13v8","key":"1l5pq0"}],["path",{"d":"M12 3v3","key":"1n5kay"}],["path",{"d":"M2.354 10.354a1.207 1.207 0 0 1 0-1.708l2.06-2.06A2 2 0 0 1 5.828 6h12.344a2 2 0 0 1 1.414.586l2.06 2.06a1.207 1.207 0 0 1 0 1.708l-2.06 2.06a2 2 0 0 1-1.414.586H5.828a2 2 0 0 1-1.414-.586z","key":"1tm261"}]])
export const SignpostBig = ssrIcon('signpost-big', [["path",{"d":"M10 9H4L2 7l2-2h6","key":"1hq7x2"}],["path",{"d":"M14 5h6l2 2-2 2h-6","key":"bv62ej"}],["path",{"d":"M10 22V4a2 2 0 1 1 4 0v18","key":"eqpcf2"}],["path",{"d":"M8 22h8","key":"rmew8v"}]])
export const Siren = ssrIcon('siren', [["path",{"d":"M7 18v-6a5 5 0 1 1 10 0v6","key":"pcx96s"}],["path",{"d":"M5 21a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-1a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2z","key":"1b4s83"}],["path",{"d":"M21 12h1","key":"jtio3y"}],["path",{"d":"M18.5 4.5 18 5","key":"g5sp9y"}],["path",{"d":"M2 12h1","key":"1uaihz"}],["path",{"d":"M12 2v1","key":"11qlp1"}],["path",{"d":"m4.929 4.929.707.707","key":"1i51kw"}],["path",{"d":"M12 12v6","key":"3ahymv"}]])
export const SkipBack = ssrIcon('skip-back', [["path",{"d":"M17.971 4.285A2 2 0 0 1 21 6v12a2 2 0 0 1-3.029 1.715l-9.997-5.998a2 2 0 0 1-.003-3.432z","key":"15892j"}],["path",{"d":"M3 20V4","key":"1ptbpl"}]])
export const SkipForward = ssrIcon('skip-forward', [["path",{"d":"M21 4v16","key":"7j8fe9"}],["path",{"d":"M6.029 4.285A2 2 0 0 0 3 6v12a2 2 0 0 0 3.029 1.715l9.997-5.998a2 2 0 0 0 .003-3.432z","key":"zs4d6"}]])
export const Skull = ssrIcon('skull', [["path",{"d":"m12.5 17-.5-1-.5 1h1z","key":"3me087"}],["path",{"d":"M15 22a1 1 0 0 0 1-1v-1a2 2 0 0 0 1.56-3.25 8 8 0 1 0-11.12 0A2 2 0 0 0 8 20v1a1 1 0 0 0 1 1z","key":"1o5pge"}],["circle",{"cx":"15","cy":"12","r":"1","key":"1tmaij"}],["circle",{"cx":"9","cy":"12","r":"1","key":"1vctgf"}]])
export const Slash = ssrIcon('slash', [["path",{"d":"M22 2 2 22","key":"y4kqgn"}]])
export const SquareSlash = ssrIcon('square-slash', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["line",{"x1":"9","x2":"15","y1":"15","y2":"9","key":"1dfufj"}]])
export const Slice = ssrIcon('slice', [["path",{"d":"M11 16.586V19a1 1 0 0 1-1 1H2L18.37 3.63a1 1 0 1 1 3 3l-9.663 9.663a1 1 0 0 1-1.414 0L8 14","key":"1sllp5"}]])
export const SlidersVertical = ssrIcon('sliders-vertical', [["path",{"d":"M10 8h4","key":"1sr2af"}],["path",{"d":"M12 21v-9","key":"17s77i"}],["path",{"d":"M12 8V3","key":"13r4qs"}],["path",{"d":"M17 16h4","key":"h1uq16"}],["path",{"d":"M19 12V3","key":"o1uvq1"}],["path",{"d":"M19 21v-5","key":"qua636"}],["path",{"d":"M3 14h4","key":"bcjad9"}],["path",{"d":"M5 10V3","key":"cb8scm"}],["path",{"d":"M5 21v-7","key":"1w1uti"}]])
export const SlidersHorizontal = ssrIcon('sliders-horizontal', [["path",{"d":"M10 5H3","key":"1qgfaw"}],["path",{"d":"M12 19H3","key":"yhmn1j"}],["path",{"d":"M14 3v4","key":"1sua03"}],["path",{"d":"M16 17v4","key":"1q0r14"}],["path",{"d":"M21 12h-9","key":"1o4lsq"}],["path",{"d":"M21 19h-5","key":"1rlt1p"}],["path",{"d":"M21 5h-7","key":"1oszz2"}],["path",{"d":"M8 10v4","key":"tgpxqk"}],["path",{"d":"M8 12H3","key":"a7s4jb"}]])
export const Smartphone = ssrIcon('smartphone', [["rect",{"width":"14","height":"20","x":"5","y":"2","rx":"2","ry":"2","key":"1yt0o3"}],["path",{"d":"M12 18h.01","key":"mhygvu"}]])
export const SmartphoneCharging = ssrIcon('smartphone-charging', [["rect",{"width":"14","height":"20","x":"5","y":"2","rx":"2","ry":"2","key":"1yt0o3"}],["path",{"d":"M12.667 8 10 12h4l-2.667 4","key":"h9lk2d"}]])
export const SmartphoneNfc = ssrIcon('smartphone-nfc', [["rect",{"width":"7","height":"12","x":"2","y":"6","rx":"1","key":"5nje8w"}],["path",{"d":"M13 8.32a7.43 7.43 0 0 1 0 7.36","key":"1g306n"}],["path",{"d":"M16.46 6.21a11.76 11.76 0 0 1 0 11.58","key":"uqvjvo"}],["path",{"d":"M19.91 4.1a15.91 15.91 0 0 1 .01 15.8","key":"ujntz3"}]])
export const Snail = ssrIcon('snail', [["path",{"d":"M2 13a6 6 0 1 0 12 0 4 4 0 1 0-8 0 2 2 0 0 0 4 0","key":"hneq2s"}],["circle",{"cx":"10","cy":"13","r":"8","key":"194lz3"}],["path",{"d":"M2 21h12c4.4 0 8-3.6 8-8V7a2 2 0 1 0-4 0v6","key":"ixqyt7"}],["path",{"d":"M18 3 19.1 5.2","key":"9tjm43"}],["path",{"d":"M22 3 20.9 5.2","key":"j3odrs"}]])
export const Snowflake = ssrIcon('snowflake', [["path",{"d":"m10 20-1.25-2.5L6 18","key":"18frcb"}],["path",{"d":"M10 4 8.75 6.5 6 6","key":"7mghy3"}],["path",{"d":"m14 20 1.25-2.5L18 18","key":"1chtki"}],["path",{"d":"m14 4 1.25 2.5L18 6","key":"1b4wsy"}],["path",{"d":"m17 21-3-6h-4","key":"15hhxa"}],["path",{"d":"m17 3-3 6 1.5 3","key":"11697g"}],["path",{"d":"M2 12h6.5L10 9","key":"kv9z4n"}],["path",{"d":"m20 10-1.5 2 1.5 2","key":"1swlpi"}],["path",{"d":"M22 12h-6.5L14 15","key":"1mxi28"}],["path",{"d":"m4 10 1.5 2L4 14","key":"k9enpj"}],["path",{"d":"m7 21 3-6-1.5-3","key":"j8hb9u"}],["path",{"d":"m7 3 3 6h4","key":"1otusx"}]])
export const SoapDispenserDroplet = ssrIcon('soap-dispenser-droplet', [["path",{"d":"M10.5 2v4","key":"1xt6in"}],["path",{"d":"M14 2H7a2 2 0 0 0-2 2","key":"e6xig3"}],["path",{"d":"M19.29 14.76A6.67 6.67 0 0 1 17 11a6.6 6.6 0 0 1-2.29 3.76c-1.15.92-1.71 2.04-1.71 3.19 0 2.22 1.8 4.05 4 4.05s4-1.83 4-4.05c0-1.16-.57-2.26-1.71-3.19","key":"adq7uc"}],["path",{"d":"M9.607 21H6a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h7V7a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3","key":"t9hm96"}]])
export const Sofa = ssrIcon('sofa', [["path",{"d":"M20 9V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v3","key":"1dgpiv"}],["path",{"d":"M2 16a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-5a2 2 0 0 0-4 0v1.5a.5.5 0 0 1-.5.5h-11a.5.5 0 0 1-.5-.5V11a2 2 0 0 0-4 0z","key":"xacw8m"}],["path",{"d":"M4 18v2","key":"jwo5n2"}],["path",{"d":"M20 18v2","key":"1ar1qi"}],["path",{"d":"M12 4v9","key":"oqhhn3"}]])
export const SolarPanel = ssrIcon('solar-panel', [["path",{"d":"M11 2h2","key":"isr7bz"}],["path",{"d":"m14.28 14-4.56 8","key":"4anwcf"}],["path",{"d":"m21 22-1.558-4H4.558","key":"enk13h"}],["path",{"d":"M3 10v2","key":"w8mti9"}],["path",{"d":"M6.245 15.04A2 2 0 0 1 8 14h12a1 1 0 0 1 .864 1.505l-3.11 5.457A2 2 0 0 1 16 22H4a1 1 0 0 1-.863-1.506z","key":"pouggg"}],["path",{"d":"M7 2a4 4 0 0 1-4 4","key":"78s8of"}],["path",{"d":"m8.66 7.66 1.41 1.41","key":"1vaqj8"}]])
export const Soup = ssrIcon('soup', [["path",{"d":"M12 21a9 9 0 0 0 9-9H3a9 9 0 0 0 9 9Z","key":"4rw317"}],["path",{"d":"M7 21h10","key":"1b0cd5"}],["path",{"d":"M19.5 12 22 6","key":"shfsr5"}],["path",{"d":"M16.25 3c.27.1.8.53.75 1.36-.06.83-.93 1.2-1 2.02-.05.78.34 1.24.73 1.62","key":"rpc6vp"}],["path",{"d":"M11.25 3c.27.1.8.53.74 1.36-.05.83-.93 1.2-.98 2.02-.06.78.33 1.24.72 1.62","key":"1lf63m"}],["path",{"d":"M6.25 3c.27.1.8.53.75 1.36-.06.83-.93 1.2-1 2.02-.05.78.34 1.24.74 1.62","key":"97tijn"}]])
export const Space = ssrIcon('space', [["path",{"d":"M22 17v1c0 .5-.5 1-1 1H3c-.5 0-1-.5-1-1v-1","key":"lt2kga"}]])
export const Spade = ssrIcon('spade', [["path",{"d":"M12 18v4","key":"jadmvz"}],["path",{"d":"M2 14.499a5.5 5.5 0 0 0 9.591 3.675.6.6 0 0 1 .818.001A5.5 5.5 0 0 0 22 14.5c0-2.29-1.5-4-3-5.5l-5.492-5.312a2 2 0 0 0-3-.02L5 8.999c-1.5 1.5-3 3.2-3 5.5","key":"1aw2pz"}]])
export const Sparkle = ssrIcon('sparkle', [["path",{"d":"M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z","key":"1s2grr"}]])
export const Sparkles = ssrIcon('sparkles', [["path",{"d":"M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z","key":"1s2grr"}],["path",{"d":"M20 2v4","key":"1rf3ol"}],["path",{"d":"M22 4h-4","key":"gwowj6"}],["circle",{"cx":"4","cy":"20","r":"2","key":"6kqj1y"}]])
export const Speaker = ssrIcon('speaker', [["rect",{"width":"16","height":"20","x":"4","y":"2","rx":"2","key":"1nb95v"}],["path",{"d":"M12 6h.01","key":"1vi96p"}],["circle",{"cx":"12","cy":"14","r":"4","key":"1jruaj"}],["path",{"d":"M12 14h.01","key":"1etili"}]])
export const Speech = ssrIcon('speech', [["path",{"d":"M8.8 20v-4.1l1.9.2a2.3 2.3 0 0 0 2.164-2.1V8.3A5.37 5.37 0 0 0 2 8.25c0 2.8.656 3.054 1 4.55a5.77 5.77 0 0 1 .029 2.758L2 20","key":"11atix"}],["path",{"d":"M19.8 17.8a7.5 7.5 0 0 0 .003-10.603","key":"yol142"}],["path",{"d":"M17 15a3.5 3.5 0 0 0-.025-4.975","key":"ssbmkc"}]])
export const SpellCheck = ssrIcon('spell-check', [["path",{"d":"m20 15-5.5 5.5L12 18","key":"6ytzne"}],["path",{"d":"m4 16 6-12 5.115 10.23","key":"fyukjg"}],["path",{"d":"M6 12h8","key":"1hdiqa"}]])
export const SpellCheck2 = ssrIcon('spell-check-2', [["path",{"d":"m6 16 6-12 6 12","key":"1b4byz"}],["path",{"d":"M8 12h8","key":"1wcyev"}],["path",{"d":"M4 21c1.1 0 1.1-1 2.3-1s1.1 1 2.3 1c1.1 0 1.1-1 2.3-1 1.1 0 1.1 1 2.3 1 1.1 0 1.1-1 2.3-1 1.1 0 1.1 1 2.3 1 1.1 0 1.1-1 2.3-1","key":"8mdmtu"}]])
export const Spline = ssrIcon('spline', [["circle",{"cx":"19","cy":"5","r":"2","key":"mhkx31"}],["circle",{"cx":"5","cy":"19","r":"2","key":"v8kfzx"}],["path",{"d":"M5 17A12 12 0 0 1 17 5","key":"1okkup"}]])
export const SplinePointer = ssrIcon('spline-pointer', [["path",{"d":"M12.034 12.681a.498.498 0 0 1 .647-.647l9 3.5a.5.5 0 0 1-.033.943l-3.444 1.068a1 1 0 0 0-.66.66l-1.067 3.443a.5.5 0 0 1-.943.033z","key":"xwnzip"}],["path",{"d":"M5 17A12 12 0 0 1 17 5","key":"1okkup"}],["circle",{"cx":"19","cy":"5","r":"2","key":"mhkx31"}],["circle",{"cx":"5","cy":"19","r":"2","key":"v8kfzx"}]])
export const Split = ssrIcon('split', [["path",{"d":"M16 3h5v5","key":"1806ms"}],["path",{"d":"M8 3H3v5","key":"15dfkv"}],["path",{"d":"M12 22v-8.3a4 4 0 0 0-1.172-2.872L3 3","key":"1qrqzj"}],["path",{"d":"m15 9 6-6","key":"ko1vev"}]])
export const SquareSplitHorizontal = ssrIcon('square-split-horizontal', [["path",{"d":"M12 2v20","key":"t6zp3m"}],["path",{"d":"M16 3h3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-3","key":"saxlbk"}],["path",{"d":"M8 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3","key":"m1vog4"}]])
export const SquareSplitVertical = ssrIcon('square-split-vertical', [["path",{"d":"M2 12h20","key":"9i4pu4"}],["path",{"d":"M21 16v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-3","key":"14rx03"}],["path",{"d":"M3 8V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v3","key":"1haecz"}]])
export const Spool = ssrIcon('spool', [["path",{"d":"M17 13.44 4.442 17.082A2 2 0 0 0 4.982 21H19a2 2 0 0 0 .558-3.921l-1.115-.32A2 2 0 0 1 17 14.837V7.66","key":"13vns8"}],["path",{"d":"m7 10.56 12.558-3.642A2 2 0 0 0 19.018 3H5a2 2 0 0 0-.558 3.921l1.115.32A2 2 0 0 1 7 9.163v7.178","key":"s8x3u0"}]])
export const SportShoe = ssrIcon('sport-shoe', [["path",{"d":"m15 10.42 4.8-5.07","key":"10at9d"}],["path",{"d":"M19 18h3","key":"nnkd4d"}],["path",{"d":"M9.5 22 21.414 9.415A2 2 0 0 0 21.2 6.4l-5.61-4.208A1 1 0 0 0 14 3v2a2 2 0 0 1-1.394 1.906L8.677 8.053A1 1 0 0 0 8 9c-.155 6.393-2.082 9-4 9a2 2 0 0 0 0 4h14","key":"v410ed"}]])
export const Spotlight = ssrIcon('spotlight', [["path",{"d":"M15.295 19.562 16 22","key":"31jsb7"}],["path",{"d":"m17 16 3.758 2.098","key":"121ar7"}],["path",{"d":"m19 12.5 3.026-.598","key":"19ukd3"}],["path",{"d":"M7.61 6.3a3 3 0 0 0-3.92 1.3l-1.38 2.79a3 3 0 0 0 1.3 3.91l6.89 3.597a1 1 0 0 0 1.342-.447l3.106-6.211a1 1 0 0 0-.447-1.341z","key":"lwb9l9"}],["path",{"d":"M8 9V2","key":"1xa0v7"}]])
export const SprayCan = ssrIcon('spray-can', [["path",{"d":"M3 3h.01","key":"159qn6"}],["path",{"d":"M7 5h.01","key":"1hq22a"}],["path",{"d":"M11 7h.01","key":"1osv80"}],["path",{"d":"M3 7h.01","key":"1xzrh3"}],["path",{"d":"M7 9h.01","key":"19b3jx"}],["path",{"d":"M3 11h.01","key":"1eifu7"}],["rect",{"width":"4","height":"4","x":"15","y":"5","key":"mri9e4"}],["path",{"d":"m19 9 2 2v10c0 .6-.4 1-1 1h-6c-.6 0-1-.4-1-1V11l2-2","key":"aib6hk"}],["path",{"d":"m13 14 8-2","key":"1d7bmk"}],["path",{"d":"m13 19 8-2","key":"1y2vml"}]])
export const Sprout = ssrIcon('sprout', [["path",{"d":"M14 9.536V7a4 4 0 0 1 4-4h1.5a.5.5 0 0 1 .5.5V5a4 4 0 0 1-4 4 4 4 0 0 0-4 4c0 2 1 3 1 5a5 5 0 0 1-1 3","key":"139s4v"}],["path",{"d":"M4 9a5 5 0 0 1 8 4 5 5 0 0 1-8-4","key":"1dlkgp"}],["path",{"d":"M5 21h14","key":"11awu3"}]])
export const Square = ssrIcon('square', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}]])
export const SquareArrowRightEnter = ssrIcon('square-arrow-right-enter', [["path",{"d":"m10 16 4-4-4-4","key":"w9835o"}],["path",{"d":"M3 12h11","key":"pmja8f"}],["path",{"d":"M3 8V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-3","key":"1bqs5q"}]])
export const SquareArrowRightExit = ssrIcon('square-arrow-right-exit', [["path",{"d":"M10 12h11","key":"6m4ad9"}],["path",{"d":"m17 16 4-4-4-4","key":"iin4zf"}],["path",{"d":"M21 6.344V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-1.344","key":"1ojbhp"}]])
export const SquareDashedBottom = ssrIcon('square-dashed-bottom', [["path",{"d":"M5 21a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2","key":"as5y1o"}],["path",{"d":"M9 21h1","key":"15o7lz"}],["path",{"d":"M14 21h1","key":"v9vybs"}]])
export const SquareDashedBottomCode = ssrIcon('square-dashed-bottom-code', [["path",{"d":"M10 9.5 8 12l2 2.5","key":"3mjy60"}],["path",{"d":"M14 21h1","key":"v9vybs"}],["path",{"d":"m14 9.5 2 2.5-2 2.5","key":"1bir2l"}],["path",{"d":"M5 21a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2","key":"as5y1o"}],["path",{"d":"M9 21h1","key":"15o7lz"}]])
export const SquareDashedText = ssrIcon('square-dashed-text', [["path",{"d":"M14 21h1","key":"v9vybs"}],["path",{"d":"M14 3h1","key":"1ec4yj"}],["path",{"d":"M19 3a2 2 0 0 1 2 2","key":"18rm91"}],["path",{"d":"M21 14v1","key":"169vum"}],["path",{"d":"M21 19a2 2 0 0 1-2 2","key":"1j7049"}],["path",{"d":"M21 9v1","key":"mxsmne"}],["path",{"d":"M3 14v1","key":"vnatye"}],["path",{"d":"M3 9v1","key":"1r0deq"}],["path",{"d":"M5 21a2 2 0 0 1-2-2","key":"sbafld"}],["path",{"d":"M5 3a2 2 0 0 0-2 2","key":"y57alp"}],["path",{"d":"M7 12h10","key":"b7w52i"}],["path",{"d":"M7 16h6","key":"1vyc9m"}],["path",{"d":"M7 8h8","key":"1jbsf9"}],["path",{"d":"M9 21h1","key":"15o7lz"}],["path",{"d":"M9 3h1","key":"1yesri"}]])
export const SquareDashedTopSolid = ssrIcon('square-dashed-top-solid', [["path",{"d":"M14 21h1","key":"v9vybs"}],["path",{"d":"M21 14v1","key":"169vum"}],["path",{"d":"M21 19a2 2 0 0 1-2 2","key":"1j7049"}],["path",{"d":"M21 9v1","key":"mxsmne"}],["path",{"d":"M3 14v1","key":"vnatye"}],["path",{"d":"M3 5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2","key":"89voep"}],["path",{"d":"M3 9v1","key":"1r0deq"}],["path",{"d":"M5 21a2 2 0 0 1-2-2","key":"sbafld"}],["path",{"d":"M9 21h1","key":"15o7lz"}]])
export const SquareDimensions = ssrIcon('square-dimensions', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M12 7H7v5","key":"ow32kf"}],["path",{"d":"M12 17h5v-5","key":"1biuiz"}]])
export const SquareOff = ssrIcon('square-off', [["path",{"d":"M20.4 20.4a2 2 0 01-1.4.6H5a2 2 0 01-2-2V5a2 2 0 01.59-1.41","key":"7ym6nm"}],["path",{"d":"M21 15.3V5a2 2 0 00-2-2H8.7","key":"m4nk5y"}],["path",{"d":"M22 22 2 2","key":"1r8tn9"}]])
export const SquarePause = ssrIcon('square-pause', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["line",{"x1":"10","x2":"10","y1":"15","y2":"9","key":"c1nkhi"}],["line",{"x1":"14","x2":"14","y1":"15","y2":"9","key":"h65svq"}]])
export const SquareRadical = ssrIcon('square-radical', [["path",{"d":"M7 12h2l2 5 2-10h4","key":"1fxv6h"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const SquareRoundCorner = ssrIcon('square-round-corner', [["path",{"d":"M21 11a8 8 0 0 0-8-8","key":"1lxwo5"}],["path",{"d":"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4","key":"1dv2y5"}]])
export const SquareSquare = ssrIcon('square-square', [["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}],["rect",{"x":"8","y":"8","width":"8","height":"8","rx":"1","key":"z9xiuo"}]])
export const SquareStack = ssrIcon('square-stack', [["path",{"d":"M4 10c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h4c1.1 0 2 .9 2 2","key":"4i38lg"}],["path",{"d":"M10 16c-1.1 0-2-.9-2-2v-4c0-1.1.9-2 2-2h4c1.1 0 2 .9 2 2","key":"mlte4a"}],["rect",{"width":"8","height":"8","x":"14","y":"14","rx":"2","key":"1fa9i4"}]])
export const SquareStar = ssrIcon('square-star', [["path",{"d":"M11.035 7.69a1 1 0 0 1 1.909.024l.737 1.452a1 1 0 0 0 .737.535l1.634.256a1 1 0 0 1 .588 1.806l-1.172 1.168a1 1 0 0 0-.282.866l.259 1.613a1 1 0 0 1-1.541 1.134l-1.465-.75a1 1 0 0 0-.912 0l-1.465.75a1 1 0 0 1-1.539-1.133l.258-1.613a1 1 0 0 0-.282-.866l-1.156-1.153a1 1 0 0 1 .572-1.822l1.633-.256a1 1 0 0 0 .737-.535z","key":"13edca"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const SquareStop = ssrIcon('square-stop', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["rect",{"x":"9","y":"9","width":"6","height":"6","rx":"1","key":"1ssd4o"}]])
export const SquareTerminal = ssrIcon('square-terminal', [["path",{"d":"m7 11 2-2-2-2","key":"1lz0vl"}],["path",{"d":"M11 13h4","key":"1p7l4v"}],["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","ry":"2","key":"1m3agn"}]])
export const SquareText = ssrIcon('square-text', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M7 8h8","key":"1jbsf9"}],["path",{"d":"M7 12h10","key":"b7w52i"}],["path",{"d":"M7 16h6","key":"1vyc9m"}]])
export const SquareUser = ssrIcon('square-user', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["circle",{"cx":"12","cy":"10","r":"3","key":"ilqhr7"}],["path",{"d":"M7 21v-2a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v2","key":"1m6ac2"}]])
export const SquareUserRound = ssrIcon('square-user-round', [["path",{"d":"M18 21a6 6 0 0 0-12 0","key":"kaz2du"}],["circle",{"cx":"12","cy":"11","r":"4","key":"1gt34v"}],["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}]])
export const SquareX = ssrIcon('square-x', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","ry":"2","key":"1m3agn"}],["path",{"d":"m15 9-6 6","key":"1uzhvr"}],["path",{"d":"m9 9 6 6","key":"z0biqf"}]])
export const SquaresExclude = ssrIcon('squares-exclude', [["path",{"d":"M16 12v2a2 2 0 0 1-2 2H9a1 1 0 0 0-1 1v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V10a2 2 0 0 0-2-2h0","key":"1mcohs"}],["path",{"d":"M4 16a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v3a1 1 0 0 1-1 1h-5a2 2 0 0 0-2 2v2","key":"1r1efp"}]])
export const SquaresIntersect = ssrIcon('squares-intersect', [["path",{"d":"M10 22a2 2 0 0 1-2-2","key":"i7yj1i"}],["path",{"d":"M14 2a2 2 0 0 1 2 2","key":"170a0m"}],["path",{"d":"M16 22h-2","key":"18d249"}],["path",{"d":"M2 10V8","key":"7yj4fe"}],["path",{"d":"M2 4a2 2 0 0 1 2-2","key":"ddgnws"}],["path",{"d":"M20 8a2 2 0 0 1 2 2","key":"1770vt"}],["path",{"d":"M22 14v2","key":"iot8ja"}],["path",{"d":"M22 20a2 2 0 0 1-2 2","key":"qj8q6g"}],["path",{"d":"M4 16a2 2 0 0 1-2-2","key":"1dnafg"}],["path",{"d":"M8 10a2 2 0 0 1 2-2h5a1 1 0 0 1 1 1v5a2 2 0 0 1-2 2H9a1 1 0 0 1-1-1z","key":"ci6f0b"}],["path",{"d":"M8 2h2","key":"1gmkwm"}]])
export const SquaresSubtract = ssrIcon('squares-subtract', [["path",{"d":"M10 22a2 2 0 0 1-2-2","key":"i7yj1i"}],["path",{"d":"M16 22h-2","key":"18d249"}],["path",{"d":"M16 4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h3a1 1 0 0 0 1-1v-5a2 2 0 0 1 2-2h5a1 1 0 0 0 1-1z","key":"1njgbb"}],["path",{"d":"M20 8a2 2 0 0 1 2 2","key":"1770vt"}],["path",{"d":"M22 14v2","key":"iot8ja"}],["path",{"d":"M22 20a2 2 0 0 1-2 2","key":"qj8q6g"}]])
export const SquaresUnite = ssrIcon('squares-unite', [["path",{"d":"M4 16a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v3a1 1 0 0 0 1 1h3a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H10a2 2 0 0 1-2-2v-3a1 1 0 0 0-1-1z","key":"17jnth"}]])
export const Squircle = ssrIcon('squircle', [["path",{"d":"M12 3c7.2 0 9 1.8 9 9s-1.8 9-9 9-9-1.8-9-9 1.8-9 9-9","key":"garfkc"}]])
export const SquircleDashed = ssrIcon('squircle-dashed', [["path",{"d":"M13.77 3.043a34 34 0 0 0-3.54 0","key":"1oaobr"}],["path",{"d":"M13.771 20.956a33 33 0 0 1-3.541.001","key":"95iq0j"}],["path",{"d":"M20.18 17.74c-.51 1.15-1.29 1.93-2.439 2.44","key":"1u6qty"}],["path",{"d":"M20.18 6.259c-.51-1.148-1.291-1.929-2.44-2.438","key":"1ew6g6"}],["path",{"d":"M20.957 10.23a33 33 0 0 1 0 3.54","key":"1l9npr"}],["path",{"d":"M3.043 10.23a34 34 0 0 0 .001 3.541","key":"1it6jm"}],["path",{"d":"M6.26 20.179c-1.15-.508-1.93-1.29-2.44-2.438","key":"14uchd"}],["path",{"d":"M6.26 3.82c-1.149.51-1.93 1.291-2.44 2.44","key":"8k4agb"}]])
export const Squirrel = ssrIcon('squirrel', [["path",{"d":"M15.236 22a3 3 0 0 0-2.2-5","key":"21bitc"}],["path",{"d":"M16 20a3 3 0 0 1 3-3h1a2 2 0 0 0 2-2v-2a4 4 0 0 0-4-4V4","key":"oh0fg0"}],["path",{"d":"M18 13h.01","key":"9veqaj"}],["path",{"d":"M18 6a4 4 0 0 0-4 4 7 7 0 0 0-7 7c0-5 4-5 4-10.5a4.5 4.5 0 1 0-9 0 2.5 2.5 0 0 0 5 0C7 10 3 11 3 17c0 2.8 2.2 5 5 5h10","key":"980v8a"}]])
export const Stamp = ssrIcon('stamp', [["path",{"d":"M14 13V8.5C14 7 15 7 15 5a3 3 0 0 0-6 0c0 2 1 2 1 3.5V13","key":"i9gjdv"}],["path",{"d":"M20 15.5a2.5 2.5 0 0 0-2.5-2.5h-11A2.5 2.5 0 0 0 4 15.5V17a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1z","key":"1vzg3v"}],["path",{"d":"M5 22h14","key":"ehvnwv"}]])
export const Star = ssrIcon('star', [["path",{"d":"M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z","key":"r04s7s"}]])
export const StarCheck = ssrIcon('star-check', [["path",{"d":"m19.06 12.501 2.78-2.707a.53.53 0 0 0-.294-.905l-5.166-.755a2.1 2.1 0 0 1-1.595-1.16l-2.31-4.68a.53.53 0 0 0-.95.001L9.216 6.974a2.1 2.1 0 0 1-1.597 1.16l-5.165.755a.53.53 0 0 0-.294.906l3.736 3.637a2.1 2.1 0 0 1 .611 1.879l-.88 5.139a.53.53 0 0 0 .769.56l4.617-2.428.027-.014","key":"14g7km"}],["path",{"d":"m15 18 2 2 4-4","key":"1szwhi"}]])
export const StarHalf = ssrIcon('star-half', [["path",{"d":"M12 18.338a2.1 2.1 0 0 0-.987.244L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.12 2.12 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.12 2.12 0 0 0 1.597-1.16l2.309-4.679A.53.53 0 0 1 12 2","key":"2ksp49"}]])
export const StarMinus = ssrIcon('star-minus', [["path",{"d":"M15 18h6","key":"3b3c90"}],["path",{"d":"M17.688 14a2.1 2.1 0 0 1 .416-.568l3.736-3.638a.53.53 0 0 0-.294-.905l-5.166-.755a2.1 2.1 0 0 1-1.595-1.16l-2.31-4.68a.53.53 0 0 0-.95.001L9.216 6.974a2.1 2.1 0 0 1-1.597 1.16l-5.165.755a.53.53 0 0 0-.294.906l3.736 3.637a2.1 2.1 0 0 1 .611 1.879l-.88 5.139a.53.53 0 0 0 .769.56l4.617-2.428.027-.014","key":"rwo527"}]])
export const StarOff = ssrIcon('star-off', [["path",{"d":"m10.344 4.688 1.181-2.393a.53.53 0 0 1 .95 0l2.31 4.679a2.12 2.12 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.237 3.152","key":"19ctli"}],["path",{"d":"m17.945 17.945.43 2.505a.53.53 0 0 1-.771.56l-4.618-2.428a2.12 2.12 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.12 2.12 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a8 8 0 0 0 .4-.099","key":"ptqqvy"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}]])
export const StarPlus = ssrIcon('star-plus', [["path",{"d":"M11.013 18.582 6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.12 2.12 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.12 2.12 0 0 0 1.597-1.16l2.309-4.679a.53.53 0 0 1 .95 0l2.31 4.679a2.12 2.12 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904L20 11.5","key":"1hs8rk"}],["path",{"d":"M15 18h6","key":"3b3c90"}],["path",{"d":"M18 15v6","key":"9wciyi"}]])
export const StarX = ssrIcon('star-x', [["path",{"d":"m15.5 15.5 5 5","key":"1ky94l"}],["path",{"d":"m20.063 11.525 1.777-1.731a.53.53 0 0 0-.294-.905l-5.166-.755a2.1 2.1 0 0 1-1.595-1.16l-2.31-4.68a.53.53 0 0 0-.95.001L9.216 6.974a2.1 2.1 0 0 1-1.597 1.16l-5.165.755a.53.53 0 0 0-.294.906l3.736 3.637a2.1 2.1 0 0 1 .611 1.879l-.88 5.139a.53.53 0 0 0 .769.56l4.617-2.428a2.1 2.1 0 0 1 .987-.243 2 2 0 0 1 .132.004","key":"6uuto3"}],["path",{"d":"m20.5 15.5-5 5","key":"1w5am3"}]])
export const StepBack = ssrIcon('step-back', [["path",{"d":"M13.971 4.285A2 2 0 0 1 17 6v12a2 2 0 0 1-3.029 1.715l-9.997-5.998a2 2 0 0 1-.003-3.432z","key":"19qhus"}],["path",{"d":"M21 20V4","key":"cb8qj8"}]])
export const StepForward = ssrIcon('step-forward', [["path",{"d":"M10.029 4.285A2 2 0 0 0 7 6v12a2 2 0 0 0 3.029 1.715l9.997-5.998a2 2 0 0 0 .003-3.432z","key":"1ystz2"}],["path",{"d":"M3 4v16","key":"1ph11n"}]])
export const Stethoscope = ssrIcon('stethoscope', [["path",{"d":"M11 2v2","key":"1539x4"}],["path",{"d":"M5 2v2","key":"1yf1q8"}],["path",{"d":"M5 3H4a2 2 0 0 0-2 2v4a6 6 0 0 0 12 0V5a2 2 0 0 0-2-2h-1","key":"rb5t3r"}],["path",{"d":"M8 15a6 6 0 0 0 12 0v-3","key":"x18d4x"}],["circle",{"cx":"20","cy":"10","r":"2","key":"ts1r5v"}]])
export const Sticker = ssrIcon('sticker', [["path",{"d":"M21 9a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 15 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2z","key":"1dfntj"}],["path",{"d":"M15 3v5a1 1 0 0 0 1 1h5","key":"6s6qgf"}],["path",{"d":"M8 13h.01","key":"1sbv64"}],["path",{"d":"M16 13h.01","key":"wip0gl"}],["path",{"d":"M10 16s.8 1 2 1c1.3 0 2-1 2-1","key":"1vvgv3"}]])
export const StickyNote = ssrIcon('sticky-note', [["path",{"d":"M21 9a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 15 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2z","key":"1dfntj"}],["path",{"d":"M15 3v5a1 1 0 0 0 1 1h5","key":"6s6qgf"}]])
export const StickyNoteCheck = ssrIcon('sticky-note-check', [["path",{"d":"m15 19 2 2 4-4","key":"1wqv71"}],["path",{"d":"M15 3v5a1 1 0 0 0 1 1h5","key":"6s6qgf"}],["path",{"d":"M21 13V9a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 15 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h6.5","key":"1onoss"}]])
export const StickyNoteMinus = ssrIcon('sticky-note-minus', [["path",{"d":"M15 3v5a1 1 0 0 0 1 1h5","key":"6s6qgf"}],["path",{"d":"M21 14V9a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 15 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h7.35","key":"g18rj4"}],["path",{"d":"M21 18h-6","key":"139f0c"}]])
export const StickyNoteOff = ssrIcon('sticky-note-off', [["path",{"d":"M15 3v5a1 1 0 0 0 1 1h5","key":"6s6qgf"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M3.586 3.586A2 2 0 0 0 3 5v14a2 2 0 0 0 2 2h14a2 2 0 0 0 1.414-.586","key":"12nghy"}],["path",{"d":"M8.656 3H15a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 21 9v6.344","key":"134c6x"}]])
export const StickyNotePlus = ssrIcon('sticky-note-plus', [["path",{"d":"M15 3v5a1 1 0 0 0 1 1h5","key":"6s6qgf"}],["path",{"d":"M18 15v6","key":"9wciyi"}],["path",{"d":"M21 12.356V9a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 15 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h7.355","key":"12ish9"}],["path",{"d":"M21 18h-6","key":"139f0c"}]])
export const StickyNoteX = ssrIcon('sticky-note-x', [["path",{"d":"M15 3v5a1 1 0 0 0 1 1h5","key":"6s6qgf"}],["path",{"d":"m16 16 5 5","key":"8tpb07"}],["path",{"d":"M21 12V9a2.4 2.4 0 0 0-.706-1.706l-3.588-3.588A2.4 2.4 0 0 0 15 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h7","key":"156tez"}],["path",{"d":"m21 16-5 5","key":"kplof2"}]])
export const StickyNotes = ssrIcon('sticky-notes', [["path",{"d":"M10 8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 16 14v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2z","key":"19nc0g"}],["path",{"d":"M10 8v5a1 1 0 0 0 1 1h5","key":"m3law1"}],["path",{"d":"M8 4a2 2 0 0 1 2-2h6a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 22 8v6a2 2 0 0 1-2 2","key":"1iu1qd"}],["path",{"d":"M16 2v5a1 1 0 0 0 1 1h5","key":"af171p"}]])
export const Stone = ssrIcon('stone', [["path",{"d":"M11.264 2.205A4 4 0 0 0 6.42 4.211l-4 8a4 4 0 0 0 1.359 5.117l6 4a4 4 0 0 0 4.438 0l6-4a4 4 0 0 0 1.576-4.592l-2-6a4 4 0 0 0-2.53-2.53z","key":"1si4ox"}],["path",{"d":"M11.99 22 14 12l7.822 3.184","key":"1u8to0"}],["path",{"d":"M14 12 8.47 2.302","key":"guo3d5"}]])
export const Store = ssrIcon('store', [["path",{"d":"M15 21v-5a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v5","key":"slp6dd"}],["path",{"d":"M17.774 10.31a1.12 1.12 0 0 0-1.549 0 2.5 2.5 0 0 1-3.451 0 1.12 1.12 0 0 0-1.548 0 2.5 2.5 0 0 1-3.452 0 1.12 1.12 0 0 0-1.549 0 2.5 2.5 0 0 1-3.77-3.248l2.889-4.184A2 2 0 0 1 7 2h10a2 2 0 0 1 1.653.873l2.895 4.192a2.5 2.5 0 0 1-3.774 3.244","key":"o0xfot"}],["path",{"d":"M4 10.95V19a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8.05","key":"wn3emo"}]])
export const StretchHorizontal = ssrIcon('stretch-horizontal', [["rect",{"width":"20","height":"6","x":"2","y":"4","rx":"2","key":"qdearl"}],["rect",{"width":"20","height":"6","x":"2","y":"14","rx":"2","key":"1xrn6j"}]])
export const StretchVertical = ssrIcon('stretch-vertical', [["rect",{"width":"6","height":"20","x":"4","y":"2","rx":"2","key":"19qu7m"}],["rect",{"width":"6","height":"20","x":"14","y":"2","rx":"2","key":"24v0nk"}]])
export const Strikethrough = ssrIcon('strikethrough', [["path",{"d":"M16 4H9a3 3 0 0 0-2.83 4","key":"43sutm"}],["path",{"d":"M14 12a4 4 0 0 1 0 8H6","key":"nlfj13"}],["line",{"x1":"4","x2":"20","y1":"12","y2":"12","key":"1e0a9i"}]])
export const Subscript = ssrIcon('subscript', [["path",{"d":"m4 5 8 8","key":"1eunvl"}],["path",{"d":"m12 5-8 8","key":"1ah0jp"}],["path",{"d":"M20 19h-4c0-1.5.44-2 1.5-2.5S20 15.33 20 14c0-.47-.17-.93-.48-1.29a2.11 2.11 0 0 0-2.62-.44c-.42.24-.74.62-.9 1.07","key":"e8ta8j"}]])
export const Summary = ssrIcon('summary', [["path",{"d":"M15 4H7","key":"oyc4c8"}],["path",{"d":"m18 16 3 3-3 3","key":"1d4glt"}],["path",{"d":"M3 4v13a2 2 0 0 0 2 2h16","key":"o3n0ii"}],["path",{"d":"M7 14h7","key":"16kgpy"}],["path",{"d":"M7 9h12","key":"ihq7ma"}]])
export const Sun = ssrIcon('sun', [["circle",{"cx":"12","cy":"12","r":"4","key":"4exip2"}],["path",{"d":"M12 2v2","key":"tus03m"}],["path",{"d":"M12 20v2","key":"1lh1kg"}],["path",{"d":"m4.93 4.93 1.41 1.41","key":"149t6j"}],["path",{"d":"m17.66 17.66 1.41 1.41","key":"ptbguv"}],["path",{"d":"M2 12h2","key":"1t8f8n"}],["path",{"d":"M20 12h2","key":"1q8mjw"}],["path",{"d":"m6.34 17.66-1.41 1.41","key":"1m8zz5"}],["path",{"d":"m19.07 4.93-1.41 1.41","key":"1shlcs"}]])
export const SunDim = ssrIcon('sun-dim', [["circle",{"cx":"12","cy":"12","r":"4","key":"4exip2"}],["path",{"d":"M12 4h.01","key":"1ujb9j"}],["path",{"d":"M20 12h.01","key":"1ykeid"}],["path",{"d":"M12 20h.01","key":"zekei9"}],["path",{"d":"M4 12h.01","key":"158zrr"}],["path",{"d":"M17.657 6.343h.01","key":"31pqzk"}],["path",{"d":"M17.657 17.657h.01","key":"jehnf4"}],["path",{"d":"M6.343 17.657h.01","key":"gdk6ow"}],["path",{"d":"M6.343 6.343h.01","key":"1uurf0"}]])
export const SunMedium = ssrIcon('sun-medium', [["circle",{"cx":"12","cy":"12","r":"4","key":"4exip2"}],["path",{"d":"M12 3v1","key":"1asbbs"}],["path",{"d":"M12 20v1","key":"1wcdkc"}],["path",{"d":"M3 12h1","key":"lp3yf2"}],["path",{"d":"M20 12h1","key":"1vloll"}],["path",{"d":"m18.364 5.636-.707.707","key":"1hakh0"}],["path",{"d":"m6.343 17.657-.707.707","key":"18m9nf"}],["path",{"d":"m5.636 5.636.707.707","key":"1xv1c5"}],["path",{"d":"m17.657 17.657.707.707","key":"vl76zb"}]])
export const SunMoon = ssrIcon('sun-moon', [["path",{"d":"M12 2v2","key":"tus03m"}],["path",{"d":"M14.837 16.385a6 6 0 1 1-7.223-7.222c.624-.147.97.66.715 1.248a4 4 0 0 0 5.26 5.259c.589-.255 1.396.09 1.248.715","key":"xlf6rm"}],["path",{"d":"M16 12a4 4 0 0 0-4-4","key":"6vsxu"}],["path",{"d":"m19 5-1.256 1.256","key":"1yg6a6"}],["path",{"d":"M20 12h2","key":"1q8mjw"}]])
export const SunSnow = ssrIcon('sun-snow', [["path",{"d":"M10 21v-1","key":"1u8rkd"}],["path",{"d":"M10 4V3","key":"pkzwkn"}],["path",{"d":"M10 9a3 3 0 0 0 0 6","key":"gv75dk"}],["path",{"d":"m14 20 1.25-2.5L18 18","key":"1chtki"}],["path",{"d":"m14 4 1.25 2.5L18 6","key":"1b4wsy"}],["path",{"d":"m17 21-3-6 1.5-3H22","key":"o5qa3v"}],["path",{"d":"m17 3-3 6 1.5 3","key":"11697g"}],["path",{"d":"M2 12h1","key":"1uaihz"}],["path",{"d":"m20 10-1.5 2 1.5 2","key":"1swlpi"}],["path",{"d":"m3.64 18.36.7-.7","key":"105rm9"}],["path",{"d":"m4.34 6.34-.7-.7","key":"d3unjp"}]])
export const Sunrise = ssrIcon('sunrise', [["path",{"d":"M12 2v8","key":"1q4o3n"}],["path",{"d":"m4.93 10.93 1.41 1.41","key":"2a7f42"}],["path",{"d":"M2 18h2","key":"j10viu"}],["path",{"d":"M20 18h2","key":"wocana"}],["path",{"d":"m19.07 10.93-1.41 1.41","key":"15zs5n"}],["path",{"d":"M22 22H2","key":"19qnx5"}],["path",{"d":"m8 6 4-4 4 4","key":"ybng9g"}],["path",{"d":"M16 18a4 4 0 0 0-8 0","key":"1lzouq"}]])
export const Sunset = ssrIcon('sunset', [["path",{"d":"M12 10V2","key":"16sf7g"}],["path",{"d":"m4.93 10.93 1.41 1.41","key":"2a7f42"}],["path",{"d":"M2 18h2","key":"j10viu"}],["path",{"d":"M20 18h2","key":"wocana"}],["path",{"d":"m19.07 10.93-1.41 1.41","key":"15zs5n"}],["path",{"d":"M22 22H2","key":"19qnx5"}],["path",{"d":"m16 6-4 4-4-4","key":"6wukr"}],["path",{"d":"M16 18a4 4 0 0 0-8 0","key":"1lzouq"}]])
export const Superscript = ssrIcon('superscript', [["path",{"d":"m4 19 8-8","key":"hr47gm"}],["path",{"d":"m12 19-8-8","key":"1dhhmo"}],["path",{"d":"M20 12h-4c0-1.5.442-2 1.5-2.5S20 8.334 20 7.002c0-.472-.17-.93-.484-1.29a2.105 2.105 0 0 0-2.617-.436c-.42.239-.738.614-.899 1.06","key":"1dfcux"}]])
export const SwatchBook = ssrIcon('swatch-book', [["path",{"d":"M11 17a4 4 0 0 1-8 0V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2Z","key":"1ldrpk"}],["path",{"d":"M16.7 13H19a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2H7","key":"11i5po"}],["path",{"d":"M 7 17h.01","key":"1euzgo"}],["path",{"d":"m11 8 2.3-2.3a2.4 2.4 0 0 1 3.404.004L18.6 7.6a2.4 2.4 0 0 1 .026 3.434L9.9 19.8","key":"o2gii7"}]])
export const SwissFranc = ssrIcon('swiss-franc', [["path",{"d":"M10 21V3h8","key":"br2l0g"}],["path",{"d":"M6 16h9","key":"2py0wn"}],["path",{"d":"M10 9.5h7","key":"13dmhz"}]])
export const SwitchCamera = ssrIcon('switch-camera', [["path",{"d":"M11 19H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5","key":"mtk2lu"}],["path",{"d":"M13 5h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-5","key":"120jsl"}],["circle",{"cx":"12","cy":"12","r":"3","key":"1v7zrd"}],["path",{"d":"m18 22-3-3 3-3","key":"kgdoj7"}],["path",{"d":"m6 2 3 3-3 3","key":"1fnbkv"}]])
export const Sword = ssrIcon('sword', [["path",{"d":"m11 19-6-6","key":"s7kpr"}],["path",{"d":"m5 21-2-2","key":"1kw20b"}],["path",{"d":"m8 16-4 4","key":"1oqv8h"}],["path",{"d":"M9.5 17.5 20.414 6.586A2 2 0 0021 5.172V3h-2.172a2 2 0 00-1.414.586L6.5 14.5","key":"1pjndt"}]])
export const Swords = ssrIcon('swords', [["path",{"d":"m13 19 6-6","key":"gj6q8g"}],["path",{"d":"M14.5 17.5 3.586 6.586A2 2 0 013 5.172V3h2.172a2 2 0 011.414.586L17.5 14.5","key":"uwfxh8"}],["path",{"d":"m14.828 6.172 2.586-2.586A2 2 0 0118.828 3H21v2.172a2 2 0 01-.586 1.414l-2.586 2.586","key":"1f17hx"}],["path",{"d":"m16 16 4 4","key":"up5ibb"}],["path",{"d":"m19 21 2-2","key":"1phfkn"}],["path",{"d":"m5 14 4 4","key":"1gk0qx"}],["path",{"d":"m5 21-2-2","key":"1kw20b"}],["path",{"d":"M7.5 16.5 4 20","key":"14nozp"}]])
export const Syringe = ssrIcon('syringe', [["path",{"d":"m18 2 4 4","key":"22kx64"}],["path",{"d":"m17 7 3-3","key":"1w1zoj"}],["path",{"d":"M19 9 8.7 19.3c-1 1-2.5 1-3.4 0l-.6-.6c-1-1-1-2.5 0-3.4L15 5","key":"1exhtz"}],["path",{"d":"m9 11 4 4","key":"rovt3i"}],["path",{"d":"m5 19-3 3","key":"59f2uf"}],["path",{"d":"m14 4 6 6","key":"yqp9t2"}]])
export const Table = ssrIcon('table', [["path",{"d":"M12 3v18","key":"108xh3"}],["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M3 9h18","key":"1pudct"}],["path",{"d":"M3 15h18","key":"5xshup"}]])
export const Table2 = ssrIcon('table-2', [["path",{"d":"M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18","key":"gugj83"}]])
export const TableCellsMerge = ssrIcon('table-cells-merge', [["path",{"d":"M12 21v-6","key":"lihzve"}],["path",{"d":"M12 9V3","key":"da5inc"}],["path",{"d":"M3 15h18","key":"5xshup"}],["path",{"d":"M3 9h18","key":"1pudct"}],["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}]])
export const TableCellsSplit = ssrIcon('table-cells-split', [["path",{"d":"M12 15V9","key":"8c7uyn"}],["path",{"d":"M3 15h18","key":"5xshup"}],["path",{"d":"M3 9h18","key":"1pudct"}],["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}]])
export const TableColumnsSplit = ssrIcon('table-columns-split', [["path",{"d":"M14 14v2","key":"w2a1xv"}],["path",{"d":"M14 20v2","key":"1lq872"}],["path",{"d":"M14 2v2","key":"6buw04"}],["path",{"d":"M14 8v2","key":"i67w9a"}],["path",{"d":"M2 15h8","key":"82wtch"}],["path",{"d":"M2 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H2","key":"up0l64"}],["path",{"d":"M2 9h8","key":"yelfik"}],["path",{"d":"M22 15h-4","key":"1es58f"}],["path",{"d":"M22 3h-2a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h2","key":"pdjoqf"}],["path",{"d":"M22 9h-4","key":"1luja7"}],["path",{"d":"M5 3v18","key":"14hmio"}]])
export const TableOfContents = ssrIcon('table-of-contents', [["path",{"d":"M16 5H3","key":"m91uny"}],["path",{"d":"M16 12H3","key":"1a2rj7"}],["path",{"d":"M16 19H3","key":"zzsher"}],["path",{"d":"M21 5h.01","key":"wa75ra"}],["path",{"d":"M21 12h.01","key":"msek7k"}],["path",{"d":"M21 19h.01","key":"qvbq2j"}]])
export const TableProperties = ssrIcon('table-properties', [["path",{"d":"M15 3v18","key":"14nvp0"}],["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["path",{"d":"M21 9H3","key":"1338ky"}],["path",{"d":"M21 15H3","key":"9uk58r"}]])
export const TableRowsSplit = ssrIcon('table-rows-split', [["path",{"d":"M14 10h2","key":"1lstlu"}],["path",{"d":"M15 22v-8","key":"1fwwgm"}],["path",{"d":"M15 2v4","key":"1044rn"}],["path",{"d":"M2 10h2","key":"1r8dkt"}],["path",{"d":"M20 10h2","key":"1ug425"}],["path",{"d":"M3 19h18","key":"awlh7x"}],["path",{"d":"M3 22v-6a2 2 135 0 1 2-2h14a2 2 45 0 1 2 2v6","key":"ibqhof"}],["path",{"d":"M3 2v2a2 2 45 0 0 2 2h14a2 2 135 0 0 2-2V2","key":"1uenja"}],["path",{"d":"M8 10h2","key":"66od0"}],["path",{"d":"M9 22v-8","key":"fmnu31"}],["path",{"d":"M9 2v4","key":"j1yeou"}]])
export const Tablet = ssrIcon('tablet', [["rect",{"width":"16","height":"20","x":"4","y":"2","rx":"2","ry":"2","key":"76otgf"}],["line",{"x1":"12","x2":"12.01","y1":"18","y2":"18","key":"1dp563"}]])
export const TabletSmartphone = ssrIcon('tablet-smartphone', [["rect",{"width":"10","height":"14","x":"3","y":"8","rx":"2","key":"1vrsiq"}],["path",{"d":"M5 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2h-2.4","key":"1j4zmg"}],["path",{"d":"M8 18h.01","key":"lrp35t"}]])
export const Tablets = ssrIcon('tablets', [["circle",{"cx":"7","cy":"7","r":"5","key":"x29byf"}],["circle",{"cx":"17","cy":"17","r":"5","key":"1op1d2"}],["path",{"d":"M12 17h10","key":"ls21zv"}],["path",{"d":"m3.46 10.54 7.08-7.08","key":"1rehiu"}]])
export const Tag = ssrIcon('tag', [["path",{"d":"M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z","key":"vktsd0"}],["circle",{"cx":"7.5","cy":"7.5","r":".5","fill":"currentColor","key":"kqv944"}]])
export const TagPlus = ssrIcon('tag-plus', [["path",{"d":"M16 13h6","key":"1um0mj"}],["path",{"d":"m16.5 6.5-3.914-3.914A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l1.79-1.79","key":"dp0yc9"}],["path",{"d":"M19 10v6","key":"13mz7b"}],["circle",{"cx":"7.5","cy":"7.5","r":".5","fill":"currentColor","key":"kqv944"}]])
export const TagX = ssrIcon('tag-x', [["path",{"d":"m16.5 6.5-3.914-3.914A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.43 2.43 0 0 0 3.42 0l1.79-1.79","key":"hu94c9"}],["path",{"d":"m16.5 10.5 5 5","key":"1jo8bf"}],["path",{"d":"m21.5 10.5-5 5","key":"jzei60"}],["circle",{"cx":"7.5","cy":"7.5","r":".5","fill":"currentColor","key":"kqv944"}]])
export const Tags = ssrIcon('tags', [["path",{"d":"M13.172 2a2 2 0 0 1 1.414.586l6.71 6.71a2.4 2.4 0 0 1 0 3.408l-4.592 4.592a2.4 2.4 0 0 1-3.408 0l-6.71-6.71A2 2 0 0 1 6 9.172V3a1 1 0 0 1 1-1z","key":"16rjxf"}],["path",{"d":"M2 7v6.172a2 2 0 0 0 .586 1.414l6.71 6.71a2.4 2.4 0 0 0 3.191.193","key":"178nd4"}],["circle",{"cx":"10.5","cy":"6.5","r":".5","fill":"currentColor","key":"12ikhr"}]])
export const Tally1 = ssrIcon('tally-1', [["path",{"d":"M4 4v16","key":"6qkkli"}]])
export const Tally2 = ssrIcon('tally-2', [["path",{"d":"M4 4v16","key":"6qkkli"}],["path",{"d":"M9 4v16","key":"81ygyz"}]])
export const Tally3 = ssrIcon('tally-3', [["path",{"d":"M4 4v16","key":"6qkkli"}],["path",{"d":"M9 4v16","key":"81ygyz"}],["path",{"d":"M14 4v16","key":"12vmem"}]])
export const Tally4 = ssrIcon('tally-4', [["path",{"d":"M4 4v16","key":"6qkkli"}],["path",{"d":"M9 4v16","key":"81ygyz"}],["path",{"d":"M14 4v16","key":"12vmem"}],["path",{"d":"M19 4v16","key":"8ij5ei"}]])
export const Tally5 = ssrIcon('tally-5', [["path",{"d":"M4 4v16","key":"6qkkli"}],["path",{"d":"M9 4v16","key":"81ygyz"}],["path",{"d":"M14 4v16","key":"12vmem"}],["path",{"d":"M19 4v16","key":"8ij5ei"}],["path",{"d":"M22 6 2 18","key":"h9moai"}]])
export const Tangent = ssrIcon('tangent', [["circle",{"cx":"17","cy":"4","r":"2","key":"y5j2s2"}],["path",{"d":"M15.59 5.41 5.41 15.59","key":"l0vprr"}],["circle",{"cx":"4","cy":"17","r":"2","key":"9p4efm"}],["path",{"d":"M12 22s-4-9-1.5-11.5S22 12 22 12","key":"1twk4o"}]])
export const Target = ssrIcon('target', [["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}],["circle",{"cx":"12","cy":"12","r":"6","key":"1vlfrh"}],["circle",{"cx":"12","cy":"12","r":"2","key":"1c9p78"}]])
export const Telescope = ssrIcon('telescope', [["path",{"d":"m10.065 12.493-6.18 1.318a.934.934 0 0 1-1.108-.702l-.537-2.15a1.07 1.07 0 0 1 .691-1.265l13.504-4.44","key":"k4qptu"}],["path",{"d":"m13.56 11.747 4.332-.924","key":"19l80z"}],["path",{"d":"m16 21-3.105-6.21","key":"7oh9d"}],["path",{"d":"M16.485 5.94a2 2 0 0 1 1.455-2.425l1.09-.272a1 1 0 0 1 1.212.727l1.515 6.06a1 1 0 0 1-.727 1.213l-1.09.272a2 2 0 0 1-2.425-1.455z","key":"m7xp4m"}],["path",{"d":"m6.158 8.633 1.114 4.456","key":"74o979"}],["path",{"d":"m8 21 3.105-6.21","key":"1fvxut"}],["circle",{"cx":"12","cy":"13","r":"2","key":"1c1ljs"}]])
export const Tent = ssrIcon('tent', [["path",{"d":"M3.5 21 14 3","key":"1szst5"}],["path",{"d":"M20.5 21 10 3","key":"1310c3"}],["path",{"d":"M15.5 21 12 15l-3.5 6","key":"1ddtfw"}],["path",{"d":"M2 21h20","key":"1nyx9w"}]])
export const TentTree = ssrIcon('tent-tree', [["circle",{"cx":"4","cy":"4","r":"2","key":"bt5ra8"}],["path",{"d":"m14 5 3-3 3 3","key":"1sorif"}],["path",{"d":"m14 10 3-3 3 3","key":"1jyi9h"}],["path",{"d":"M17 14V2","key":"8ymqnk"}],["path",{"d":"M17 14H7l-5 8h20Z","key":"13ar7p"}],["path",{"d":"M8 14v8","key":"1ghmqk"}],["path",{"d":"m9 14 5 8","key":"13pgi6"}]])
export const Terminal = ssrIcon('terminal', [["path",{"d":"M12 19h8","key":"baeox8"}],["path",{"d":"m4 17 6-6-6-6","key":"1yngyt"}]])
export const TestTube = ssrIcon('test-tube', [["path",{"d":"M14.5 2v17.5c0 1.4-1.1 2.5-2.5 2.5c-1.4 0-2.5-1.1-2.5-2.5V2","key":"125lnx"}],["path",{"d":"M8.5 2h7","key":"csnxdl"}],["path",{"d":"M14.5 16h-5","key":"1ox875"}]])
export const TestTubeDiagonal = ssrIcon('test-tube-diagonal', [["path",{"d":"M21 7 6.82 21.18a2.83 2.83 0 0 1-3.99-.01a2.83 2.83 0 0 1 0-4L17 3","key":"1ub6xw"}],["path",{"d":"m16 2 6 6","key":"1gw87d"}],["path",{"d":"M12 16H4","key":"1cjfip"}]])
export const TestTubes = ssrIcon('test-tubes', [["path",{"d":"M9 2v17.5A2.5 2.5 0 0 1 6.5 22A2.5 2.5 0 0 1 4 19.5V2","key":"1hjrqt"}],["path",{"d":"M20 2v17.5a2.5 2.5 0 0 1-2.5 2.5a2.5 2.5 0 0 1-2.5-2.5V2","key":"16lc8n"}],["path",{"d":"M3 2h7","key":"7s29d5"}],["path",{"d":"M14 2h7","key":"7sicin"}],["path",{"d":"M9 16H4","key":"1bfye3"}],["path",{"d":"M20 16h-5","key":"ddnjpe"}]])
export const TextCursor = ssrIcon('text-cursor', [["path",{"d":"M17 22h-1a4 4 0 0 1-4-4V6a4 4 0 0 1 4-4h1","key":"uvaxm9"}],["path",{"d":"M7 22h1a4 4 0 0 0 4-4","key":"1l7xii"}],["path",{"d":"M7 2h1a4 4 0 0 1 4 4","key":"1vrvvh"}]])
export const TextCursorInput = ssrIcon('text-cursor-input', [["path",{"d":"M12 20h-1a2 2 0 0 1-2-2 2 2 0 0 1-2 2H6","key":"1528k5"}],["path",{"d":"M13 8h7a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-7","key":"13ksps"}],["path",{"d":"M5 16H4a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h1","key":"1n9rhb"}],["path",{"d":"M6 4h1a2 2 0 0 1 2 2 2 2 0 0 1 2-2h1","key":"1mj8rg"}],["path",{"d":"M9 6v12","key":"velyjx"}]])
export const TextQuote = ssrIcon('text-quote', [["path",{"d":"M17 5H3","key":"1cn7zz"}],["path",{"d":"M21 12H8","key":"scolzb"}],["path",{"d":"M21 19H8","key":"13qgcb"}],["path",{"d":"M3 12v7","key":"1ri8j3"}]])
export const TextSearch = ssrIcon('text-search', [["path",{"d":"M21 5H3","key":"1fi0y6"}],["path",{"d":"M10 12H3","key":"1ulcyk"}],["path",{"d":"M10 19H3","key":"108z41"}],["circle",{"cx":"17","cy":"15","r":"3","key":"1upz2a"}],["path",{"d":"m21 19-1.9-1.9","key":"dwi7p8"}]])
export const TextWrap = ssrIcon('text-wrap', [["path",{"d":"m16 16-3 3 3 3","key":"117b85"}],["path",{"d":"M3 12h14.5a1 1 0 0 1 0 7H13","key":"18xa6z"}],["path",{"d":"M3 19h6","key":"1ygdsz"}],["path",{"d":"M3 5h18","key":"1u36vt"}]])
export const Theater = ssrIcon('theater', [["path",{"d":"M2 10s3-3 3-8","key":"3xiif0"}],["path",{"d":"M22 10s-3-3-3-8","key":"ioaa5q"}],["path",{"d":"M10 2c0 4.4-3.6 8-8 8","key":"16fkpi"}],["path",{"d":"M14 2c0 4.4 3.6 8 8 8","key":"b9eulq"}],["path",{"d":"M2 10s2 2 2 5","key":"1au1lb"}],["path",{"d":"M22 10s-2 2-2 5","key":"qi2y5e"}],["path",{"d":"M8 15h8","key":"45n4r"}],["path",{"d":"M2 22v-1a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v1","key":"1vsc2m"}],["path",{"d":"M14 22v-1a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v1","key":"hrha4u"}]])
export const Thermometer = ssrIcon('thermometer', [["path",{"d":"M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z","key":"17jzev"}]])
export const ThermometerSnowflake = ssrIcon('thermometer-snowflake', [["path",{"d":"m10 20-1.25-2.5L6 18","key":"18frcb"}],["path",{"d":"M10 4 8.75 6.5 6 6","key":"7mghy3"}],["path",{"d":"M10.585 15H10","key":"4nqulp"}],["path",{"d":"M2 12h6.5L10 9","key":"kv9z4n"}],["path",{"d":"M20 14.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0z","key":"yu0u2z"}],["path",{"d":"m4 10 1.5 2L4 14","key":"k9enpj"}],["path",{"d":"m7 21 3-6-1.5-3","key":"j8hb9u"}],["path",{"d":"m7 3 3 6h2","key":"1bbqgq"}]])
export const ThermometerSun = ssrIcon('thermometer-sun', [["path",{"d":"M12 2v2","key":"tus03m"}],["path",{"d":"M12 8a4 4 0 0 0-1.645 7.647","key":"wz5p04"}],["path",{"d":"M2 12h2","key":"1t8f8n"}],["path",{"d":"M20 14.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0z","key":"yu0u2z"}],["path",{"d":"m4.93 4.93 1.41 1.41","key":"149t6j"}],["path",{"d":"m6.34 17.66-1.41 1.41","key":"1m8zz5"}]])
export const ThumbsDown = ssrIcon('thumbs-down', [["path",{"d":"M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z","key":"m61m77"}],["path",{"d":"M17 14V2","key":"8ymqnk"}]])
export const ThumbsUp = ssrIcon('thumbs-up', [["path",{"d":"M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z","key":"emmmcr"}],["path",{"d":"M7 10v12","key":"1qc93n"}]])
export const Ticket = ssrIcon('ticket', [["path",{"d":"M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z","key":"qn84l0"}],["path",{"d":"M13 5v2","key":"dyzc3o"}],["path",{"d":"M13 17v2","key":"1ont0d"}],["path",{"d":"M13 11v2","key":"1wjjxi"}]])
export const TicketCheck = ssrIcon('ticket-check', [["path",{"d":"M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z","key":"qn84l0"}],["path",{"d":"m9 12 2 2 4-4","key":"dzmm74"}]])
export const TicketMinus = ssrIcon('ticket-minus', [["path",{"d":"M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z","key":"qn84l0"}],["path",{"d":"M9 12h6","key":"1c52cq"}]])
export const TicketPercent = ssrIcon('ticket-percent', [["path",{"d":"M2 9a3 3 0 1 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 1 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z","key":"1l48ns"}],["path",{"d":"M9 9h.01","key":"1q5me6"}],["path",{"d":"m15 9-6 6","key":"1uzhvr"}],["path",{"d":"M15 15h.01","key":"lqbp3k"}]])
export const TicketPlus = ssrIcon('ticket-plus', [["path",{"d":"M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z","key":"qn84l0"}],["path",{"d":"M9 12h6","key":"1c52cq"}],["path",{"d":"M12 9v6","key":"199k2o"}]])
export const TicketSlash = ssrIcon('ticket-slash', [["path",{"d":"M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z","key":"qn84l0"}],["path",{"d":"m9.5 14.5 5-5","key":"qviqfa"}]])
export const TicketX = ssrIcon('ticket-x', [["path",{"d":"M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z","key":"qn84l0"}],["path",{"d":"m9.5 14.5 5-5","key":"qviqfa"}],["path",{"d":"m9.5 9.5 5 5","key":"18nt4w"}]])
export const Tickets = ssrIcon('tickets', [["path",{"d":"m3.173 8.18 11-5a2 2 0 0 1 2.647.993L18.56 8","key":"15hfpj"}],["path",{"d":"M6 10V8","key":"1y41hn"}],["path",{"d":"M6 14v1","key":"cao2tf"}],["path",{"d":"M6 19v2","key":"1loha6"}],["rect",{"x":"2","y":"8","width":"20","height":"13","rx":"2","key":"p3bz5l"}]])
export const TicketsPlane = ssrIcon('tickets-plane', [["path",{"d":"M10.5 17h1.227a2 2 0 0 0 1.345-.52L18 12","key":"16muxl"}],["path",{"d":"m12 13.5 3.794.506","key":"6v5z87"}],["path",{"d":"m3.173 8.18 11-5a2 2 0 0 1 2.647.993L18.56 8","key":"15hfpj"}],["path",{"d":"M6 10V8","key":"1y41hn"}],["path",{"d":"M6 14v1","key":"cao2tf"}],["path",{"d":"M6 19v2","key":"1loha6"}],["rect",{"x":"2","y":"8","width":"20","height":"13","rx":"2","key":"p3bz5l"}]])
export const Timeline = ssrIcon('timeline', [["path",{"d":"M4 12h.01","key":"158zrr"}],["path",{"d":"M4 16h.01","key":"jrnfb7"}],["path",{"d":"M4 20h.01","key":"orx0iu"}],["path",{"d":"M4 4h.01","key":"cieki8"}],["path",{"d":"M4 8h.01","key":"43g258"}],["path",{"d":"M9.414 13.414a2 2 0 0 0 1.414.586H19a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1h-8.172a2 2 0 0 0-1.414.586L8 12z","key":"1pvxkf"}],["path",{"d":"M9.414 21.414a2 2 0 0 0 1.414.586H19a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1h-8.172a2 2 0 0 0-1.414.586L8 20z","key":"1k13gh"}],["path",{"d":"M9.414 5.414A2 2 0 0 0 10.828 6H19a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1h-8.172a2 2 0 0 0-1.414.586L8 4z","key":"12x0hd"}]])
export const Timer = ssrIcon('timer', [["line",{"x1":"10","x2":"14","y1":"2","y2":"2","key":"14vaq8"}],["line",{"x1":"12","x2":"15","y1":"14","y2":"11","key":"17fdiu"}],["circle",{"cx":"12","cy":"14","r":"8","key":"1e1u0o"}]])
export const TimerOff = ssrIcon('timer-off', [["path",{"d":"M10 2h4","key":"n1abiw"}],["path",{"d":"M4.6 11a8 8 0 0 0 1.7 8.7 8 8 0 0 0 8.7 1.7","key":"10he05"}],["path",{"d":"M7.4 7.4a8 8 0 0 1 10.3 1 8 8 0 0 1 .9 10.2","key":"15f7sh"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M12 12v-2","key":"fwoke6"}]])
export const TimerReset = ssrIcon('timer-reset', [["path",{"d":"M10 2h4","key":"n1abiw"}],["path",{"d":"M12 14v-4","key":"1evpnu"}],["path",{"d":"M4 13a8 8 0 0 1 8-7 8 8 0 1 1-5.3 14L4 17.6","key":"1ts96g"}],["path",{"d":"M9 17H4v5","key":"8t5av"}]])
export const ToggleLeft = ssrIcon('toggle-left', [["circle",{"cx":"9","cy":"12","r":"3","key":"u3jwor"}],["rect",{"width":"20","height":"14","x":"2","y":"5","rx":"7","key":"g7kal2"}]])
export const ToggleRight = ssrIcon('toggle-right', [["circle",{"cx":"15","cy":"12","r":"3","key":"1afu0r"}],["rect",{"width":"20","height":"14","x":"2","y":"5","rx":"7","key":"g7kal2"}]])
export const Toilet = ssrIcon('toilet', [["path",{"d":"M7 12h13a1 1 0 0 1 1 1 5 5 0 0 1-5 5h-.598a.5.5 0 0 0-.424.765l1.544 2.47a.5.5 0 0 1-.424.765H5.402a.5.5 0 0 1-.424-.765L7 18","key":"kc4kqr"}],["path",{"d":"M8 18a5 5 0 0 1-5-5V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8","key":"1tqs57"}]])
export const ToolCase = ssrIcon('tool-case', [["path",{"d":"M10 15h4","key":"192ueg"}],["path",{"d":"m14.817 10.995-.971-1.45 1.034-1.232a2 2 0 0 0-2.025-3.238l-1.82.364L9.91 3.885a2 2 0 0 0-3.625.748L6.141 6.55l-1.725.426a2 2 0 0 0-.19 3.756l.657.27","key":"xbnumr"}],["path",{"d":"m18.822 10.995 2.26-5.38a1 1 0 0 0-.557-1.318L16.954 2.9a1 1 0 0 0-1.281.533l-.924 2.122","key":"eaw7gc"}],["path",{"d":"M4 12.006A1 1 0 0 1 4.994 11H19a1 1 0 0 1 1 1v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z","key":"1vaooh"}]])
export const Toolbox = ssrIcon('toolbox', [["path",{"d":"M16 12v4","key":"vf1vip"}],["path",{"d":"M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2","key":"llnzfg"}],["path",{"d":"M17 6a2 2 0 011.414.586l3 3A2 2 0 0122 11v8a2 2 0 01-2 2H4a2 2 0 01-2-2v-8a2 2 0 01.586-1.414l3-3A2 2 0 017 6z","key":"1hprxj"}],["path",{"d":"M2 14h20","key":"myj16y"}],["path",{"d":"M8 12v4","key":"1w4uao"}]])
export const Tornado = ssrIcon('tornado', [["path",{"d":"M21 4H3","key":"1hwok0"}],["path",{"d":"M18 8H6","key":"41n648"}],["path",{"d":"M19 12H9","key":"1g4lpz"}],["path",{"d":"M16 16h-6","key":"1j5d54"}],["path",{"d":"M11 20H9","key":"39obr8"}]])
export const Torus = ssrIcon('torus', [["ellipse",{"cx":"12","cy":"11","rx":"3","ry":"2","key":"1b2qxu"}],["ellipse",{"cx":"12","cy":"12.5","rx":"10","ry":"8.5","key":"h8emeu"}]])
export const Touchpad = ssrIcon('touchpad', [["rect",{"width":"20","height":"16","x":"2","y":"4","rx":"2","key":"18n3k1"}],["path",{"d":"M2 14h20","key":"myj16y"}],["path",{"d":"M12 20v-6","key":"1rm09r"}]])
export const TouchpadOff = ssrIcon('touchpad-off', [["path",{"d":"M12 20v-6","key":"1rm09r"}],["path",{"d":"M19.656 14H22","key":"170xzr"}],["path",{"d":"M2 14h12","key":"d8icqz"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M20 20H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2","key":"s23sx2"}],["path",{"d":"M9.656 4H20a2 2 0 0 1 2 2v10.344","key":"ovjcvl"}]])
export const TowelRack = ssrIcon('towel-rack', [["path",{"d":"M22 7h-2","key":"1okbx2"}],["path",{"d":"M6.5 3h11A2.5 2.5 0 0 1 20 5.5V20a1 1 0 0 1-1 1h-9a1 1 0 0 1-1-1V5.5a1 1 0 0 0-5 0V17a1 1 0 0 0 1 1h4","key":"kc32tg"}],["path",{"d":"M9 7H2","key":"ahf7b7"}]])
export const TowerControl = ssrIcon('tower-control', [["path",{"d":"M18.2 12.27 20 6H4l1.8 6.27a1 1 0 0 0 .95.73h10.5a1 1 0 0 0 .96-.73Z","key":"1pledb"}],["path",{"d":"M8 13v9","key":"hmv0ci"}],["path",{"d":"M16 22v-9","key":"ylnf1u"}],["path",{"d":"m9 6 1 7","key":"dpdgam"}],["path",{"d":"m15 6-1 7","key":"ls7zgu"}],["path",{"d":"M12 6V2","key":"1pj48d"}],["path",{"d":"M13 2h-2","key":"mj6ths"}]])
export const ToyBrick = ssrIcon('toy-brick', [["rect",{"width":"18","height":"12","x":"3","y":"8","rx":"1","key":"158fvp"}],["path",{"d":"M10 8V5c0-.6-.4-1-1-1H6a1 1 0 0 0-1 1v3","key":"s0042v"}],["path",{"d":"M19 8V5c0-.6-.4-1-1-1h-3a1 1 0 0 0-1 1v3","key":"9wmeh2"}]])
export const Tractor = ssrIcon('tractor', [["path",{"d":"m10 11 11 .9a1 1 0 0 1 .8 1.1l-.665 4.158a1 1 0 0 1-.988.842H20","key":"she1j9"}],["path",{"d":"M16 18h-5","key":"bq60fd"}],["path",{"d":"M18 5a1 1 0 0 0-1 1v5.573","key":"1kv8ia"}],["path",{"d":"M3 4h8.129a1 1 0 0 1 .99.863L13 11.246","key":"1q1ert"}],["path",{"d":"M4 11V4","key":"9ft8pt"}],["path",{"d":"M7 15h.01","key":"k5ht0j"}],["path",{"d":"M8 10.1V4","key":"1jgyzo"}],["circle",{"cx":"18","cy":"18","r":"2","key":"1emm8v"}],["circle",{"cx":"7","cy":"15","r":"5","key":"ddtuc"}]])
export const TrafficCone = ssrIcon('traffic-cone', [["path",{"d":"M16.05 10.966a5 2.5 0 0 1-8.1 0","key":"m5jpwb"}],["path",{"d":"m16.923 14.049 4.48 2.04a1 1 0 0 1 .001 1.831l-8.574 3.9a2 2 0 0 1-1.66 0l-8.574-3.91a1 1 0 0 1 0-1.83l4.484-2.04","key":"rbg3g8"}],["path",{"d":"M16.949 14.14a5 2.5 0 1 1-9.9 0L10.063 3.5a2 2 0 0 1 3.874 0z","key":"vap8c8"}],["path",{"d":"M9.194 6.57a5 2.5 0 0 0 5.61 0","key":"15hn5c"}]])
export const Trailer = ssrIcon('trailer', [["path",{"d":"M10 11.341V10","key":"1vu6ku"}],["path",{"d":"M14 13v-3","key":"ywspeg"}],["path",{"d":"M18 17V8a2 2 0 00-2-2H4a2 2 0 00-2 2v7a2 2 0 002 2h2","key":"19481b"}],["path",{"d":"M22 15v1a1 1 0 01-1 1H10","key":"1lvljf"}],["path",{"d":"M6 11.341V10","key":"1dkezj"}],["circle",{"cx":"8","cy":"17","r":"2","key":"5kbc0u"}]])
export const TramFront = ssrIcon('tram-front', [["rect",{"width":"16","height":"16","x":"4","y":"3","rx":"2","key":"1wxw4b"}],["path",{"d":"M4 11h16","key":"mpoxn0"}],["path",{"d":"M12 3v8","key":"1h2ygw"}],["path",{"d":"m8 19-2 3","key":"13i0xs"}],["path",{"d":"m18 22-2-3","key":"1p0ohu"}],["path",{"d":"M8 15h.01","key":"a7atzg"}],["path",{"d":"M16 15h.01","key":"rnfrdf"}]])
export const TrainFront = ssrIcon('train-front', [["path",{"d":"M8 3.1V7a4 4 0 0 0 8 0V3.1","key":"1v71zp"}],["path",{"d":"m9 15-1-1","key":"1yrq24"}],["path",{"d":"m15 15 1-1","key":"1t0d6s"}],["path",{"d":"M9 19c-2.8 0-5-2.2-5-5v-4a8 8 0 0 1 16 0v4c0 2.8-2.2 5-5 5Z","key":"1p0hjs"}],["path",{"d":"m8 19-2 3","key":"13i0xs"}],["path",{"d":"m16 19 2 3","key":"xo31yx"}]])
export const TrainFrontTunnel = ssrIcon('train-front-tunnel', [["path",{"d":"M2 22V12a10 10 0 1 1 20 0v10","key":"o0fyp0"}],["path",{"d":"M15 6.8v1.4a3 2.8 0 1 1-6 0V6.8","key":"m8q3n9"}],["path",{"d":"M10 15h.01","key":"44in9x"}],["path",{"d":"M14 15h.01","key":"5mohn5"}],["path",{"d":"M10 19a4 4 0 0 1-4-4v-3a6 6 0 1 1 12 0v3a4 4 0 0 1-4 4Z","key":"hckbmu"}],["path",{"d":"m9 19-2 3","key":"iij7hm"}],["path",{"d":"m15 19 2 3","key":"npx8sa"}]])
export const TrainTrack = ssrIcon('train-track', [["path",{"d":"M2 17 17 2","key":"18b09t"}],["path",{"d":"m2 14 8 8","key":"1gv9hu"}],["path",{"d":"m5 11 8 8","key":"189pqp"}],["path",{"d":"m8 8 8 8","key":"1imecy"}],["path",{"d":"m11 5 8 8","key":"ummqn6"}],["path",{"d":"m14 2 8 8","key":"1vk7dn"}],["path",{"d":"M7 22 22 7","key":"15mb1i"}]])
export const Transgender = ssrIcon('transgender', [["path",{"d":"M12 16v6","key":"c8a4gj"}],["path",{"d":"M14 20h-4","key":"m8m19d"}],["path",{"d":"M18 2h4v4","key":"1341mj"}],["path",{"d":"m2 2 7.17 7.17","key":"13q8l2"}],["path",{"d":"M2 5.355V2h3.357","key":"18136r"}],["path",{"d":"m22 2-7.17 7.17","key":"1epvy4"}],["path",{"d":"M8 5 5 8","key":"mgbjhz"}],["circle",{"cx":"12","cy":"12","r":"4","key":"4exip2"}]])
export const Trash = ssrIcon('trash', [["path",{"d":"M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6","key":"miytrc"}],["path",{"d":"M3 6h18","key":"d0wm0j"}],["path",{"d":"M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2","key":"e791ji"}]])
export const Trash2 = ssrIcon('trash-2', [["path",{"d":"M10 11v6","key":"nco0om"}],["path",{"d":"M14 11v6","key":"outv1u"}],["path",{"d":"M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6","key":"miytrc"}],["path",{"d":"M3 6h18","key":"d0wm0j"}],["path",{"d":"M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2","key":"e791ji"}]])
export const TreeDeciduous = ssrIcon('tree-deciduous', [["path",{"d":"M8 19a4 4 0 0 1-2.24-7.32A3.5 3.5 0 0 1 9 6.03V6a3 3 0 1 1 6 0v.04a3.5 3.5 0 0 1 3.24 5.65A4 4 0 0 1 16 19Z","key":"oadzkq"}],["path",{"d":"M12 19v3","key":"npa21l"}]])
export const TreePine = ssrIcon('tree-pine', [["path",{"d":"m17 14 3 3.3a1 1 0 0 1-.7 1.7H4.7a1 1 0 0 1-.7-1.7L7 14h-.3a1 1 0 0 1-.7-1.7L9 9h-.2A1 1 0 0 1 8 7.3L12 3l4 4.3a1 1 0 0 1-.8 1.7H15l3 3.3a1 1 0 0 1-.7 1.7H17Z","key":"cpyugq"}],["path",{"d":"M12 22v-3","key":"kmzjlo"}]])
export const Trees = ssrIcon('trees', [["path",{"d":"M10 10v.2A3 3 0 0 1 8.9 16H5a3 3 0 0 1-1-5.8V10a3 3 0 0 1 6 0Z","key":"1l6gj6"}],["path",{"d":"M7 16v6","key":"1a82de"}],["path",{"d":"M13 19v3","key":"13sx9i"}],["path",{"d":"M12 19h8.3a1 1 0 0 0 .7-1.7L18 14h.3a1 1 0 0 0 .7-1.7L16 9h.2a1 1 0 0 0 .8-1.7L13 3l-1.4 1.5","key":"1sj9kv"}]])
export const TrendingDown = ssrIcon('trending-down', [["path",{"d":"M16 17h6v-6","key":"t6n2it"}],["path",{"d":"m22 17-8.5-8.5-5 5L2 7","key":"x473p"}]])
export const TrendingUp = ssrIcon('trending-up', [["path",{"d":"M16 7h6v6","key":"box55l"}],["path",{"d":"m22 7-8.5 8.5-5-5L2 17","key":"1t1m79"}]])
export const TrendingUpDown = ssrIcon('trending-up-down', [["path",{"d":"M14.828 14.828 21 21","key":"ar5fw7"}],["path",{"d":"M21 16v5h-5","key":"1ck2sf"}],["path",{"d":"m21 3-9 9-4-4-6 6","key":"1h02xo"}],["path",{"d":"M21 8V3h-5","key":"1qoq8a"}]])
export const Triangle = ssrIcon('triangle', [["path",{"d":"M13.73 4a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z","key":"14u9p9"}]])
export const TriangleDashed = ssrIcon('triangle-dashed', [["path",{"d":"M10.17 4.193a2 2 0 0 1 3.666.013","key":"pltmmw"}],["path",{"d":"M14 21h2","key":"v4qezv"}],["path",{"d":"m15.874 7.743 1 1.732","key":"10m0iw"}],["path",{"d":"m18.849 12.952 1 1.732","key":"zadnam"}],["path",{"d":"M21.824 18.18a2 2 0 0 1-1.835 2.824","key":"fvwuk4"}],["path",{"d":"M4.024 21a2 2 0 0 1-1.839-2.839","key":"1e1kah"}],["path",{"d":"m5.136 12.952-1 1.732","key":"1u4ldi"}],["path",{"d":"M8 21h2","key":"i9zjee"}],["path",{"d":"m8.102 7.743-1 1.732","key":"1zzo4u"}]])
export const TriangleRight = ssrIcon('triangle-right', [["path",{"d":"M22 18a2 2 0 0 1-2 2H3c-1.1 0-1.3-.6-.4-1.3L20.4 4.3c.9-.7 1.6-.4 1.6.7Z","key":"183wce"}]])
export const Trophy = ssrIcon('trophy', [["path",{"d":"M10 14.66V17a1 1 0 0 1-1 1 2 2 0 0 0-2 2v2","key":"pwuv1l"}],["path",{"d":"M14 14.66V17a1 1 0 0 0 1 1 2 2 0 0 1 2 2v2","key":"1y54w1"}],["path",{"d":"M17.916 10H19.5A2.5 2.5 0 0 0 22 7.5V5a1 1 0 0 0-1-1h-3","key":"e30mpu"}],["path",{"d":"M4 22h16","key":"57wxv0"}],["path",{"d":"M6 9a6 6 0 0 0 12 0V3a1 1 0 0 0-1-1H7a1 1 0 0 0-1 1z","key":"1mhfuq"}],["path",{"d":"M6.084 10H4.5A2.5 2.5 0 0 1 2 7.5V5a1 1 0 0 1 1-1h3","key":"i0yafy"}]])
export const Truck = ssrIcon('truck', [["path",{"d":"M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2","key":"wrbu53"}],["path",{"d":"M15 18H9","key":"1lyqi6"}],["path",{"d":"M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14","key":"lysw3i"}],["circle",{"cx":"17","cy":"18","r":"2","key":"332jqn"}],["circle",{"cx":"7","cy":"18","r":"2","key":"19iecd"}]])
export const TruckElectric = ssrIcon('truck-electric', [["path",{"d":"M14 19V7a2 2 0 0 0-2-2H9","key":"15peso"}],["path",{"d":"M15 19H9","key":"18q6dt"}],["path",{"d":"M19 19h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.62L18.3 9.38a1 1 0 0 0-.78-.38H14","key":"1dkp3j"}],["path",{"d":"M2 13v5a1 1 0 0 0 1 1h2","key":"pkmmzz"}],["path",{"d":"M4 3 2.15 5.15a.495.495 0 0 0 .35.86h2.15a.47.47 0 0 1 .35.86L3 9.02","key":"1n26pd"}],["circle",{"cx":"17","cy":"19","r":"2","key":"1nxcgd"}],["circle",{"cx":"7","cy":"19","r":"2","key":"gzo7y7"}]])
export const TurkishLira = ssrIcon('turkish-lira', [["path",{"d":"M15 4 5 9","key":"14bkc9"}],["path",{"d":"m15 8.5-10 5","key":"1grtsx"}],["path",{"d":"M18 12a9 9 0 0 1-9 9V3","key":"1sst7f"}]])
export const Turntable = ssrIcon('turntable', [["path",{"d":"M10 12.01h.01","key":"7rp0yl"}],["path",{"d":"M18 8v4a8 8 0 0 1-1.07 4","key":"1st48v"}],["circle",{"cx":"10","cy":"12","r":"4","key":"19levz"}],["rect",{"x":"2","y":"4","width":"20","height":"16","rx":"2","key":"izxlao"}]])
export const Turtle = ssrIcon('turtle', [["path",{"d":"m12 10 2 4v3a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1v-3a8 8 0 1 0-16 0v3a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1v-3l2-4h4Z","key":"1lbbv7"}],["path",{"d":"M4.82 7.9 8 10","key":"m9wose"}],["path",{"d":"M15.18 7.9 12 10","key":"p8dp2u"}],["path",{"d":"M16.93 10H20a2 2 0 0 1 0 4H2","key":"12nsm7"}]])
export const Tv = ssrIcon('tv', [["path",{"d":"m17 2-5 5-5-5","key":"16satq"}],["rect",{"width":"20","height":"15","x":"2","y":"7","rx":"2","key":"1e6viu"}]])
export const TvMinimal = ssrIcon('tv-minimal', [["path",{"d":"M7 21h10","key":"1b0cd5"}],["rect",{"width":"20","height":"14","x":"2","y":"3","rx":"2","key":"48i651"}]])
export const TvMinimalPlay = ssrIcon('tv-minimal-play', [["path",{"d":"M15.033 9.44a.647.647 0 0 1 0 1.12l-4.065 2.352a.645.645 0 0 1-.968-.56V7.648a.645.645 0 0 1 .967-.56z","key":"vbtd3f"}],["path",{"d":"M7 21h10","key":"1b0cd5"}],["rect",{"width":"20","height":"14","x":"2","y":"3","rx":"2","key":"48i651"}]])
export const Type = ssrIcon('type', [["path",{"d":"M12 4v16","key":"1654pz"}],["path",{"d":"M4 7V5a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v2","key":"e0r10z"}],["path",{"d":"M9 20h6","key":"s66wpe"}]])
export const TypeOutline = ssrIcon('type-outline', [["path",{"d":"M14 16.5a.5.5 0 0 0 .5.5h.5a2 2 0 0 1 0 4H9a2 2 0 0 1 0-4h.5a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-3a.5.5 0 0 0-.5.5V8a2 2 0 0 1-4 0V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v3a2 2 0 0 1-4 0v-.5a.5.5 0 0 0-.5-.5h-3a.5.5 0 0 0-.5.5Z","key":"1reda3"}]])
export const Umbrella = ssrIcon('umbrella', [["path",{"d":"M12 13v7a2 2 0 0 0 4 0","key":"rpgb42"}],["path",{"d":"M12 2v2","key":"tus03m"}],["path",{"d":"M20.992 13a1 1 0 0 0 .97-1.274 10.284 10.284 0 0 0-19.923 0A1 1 0 0 0 3 13z","key":"124nyo"}]])
export const UmbrellaOff = ssrIcon('umbrella-off', [["path",{"d":"M12 13v7a2 2 0 0 0 4 0","key":"rpgb42"}],["path",{"d":"M12 2v2","key":"tus03m"}],["path",{"d":"M18.656 13h2.336a1 1 0 0 0 .97-1.274 10.284 10.284 0 0 0-12.07-7.51","key":"yawknk"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M5.961 5.957a10.28 10.28 0 0 0-3.922 5.769A1 1 0 0 0 3 13h10","key":"5sfalc"}]])
export const Underline = ssrIcon('underline', [["path",{"d":"M6 4v6a6 6 0 0 0 12 0V4","key":"9kb039"}],["line",{"x1":"4","x2":"20","y1":"20","y2":"20","key":"nun2al"}]])
export const Undo = ssrIcon('undo', [["path",{"d":"M3 7v6h6","key":"1v2h90"}],["path",{"d":"M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13","key":"1r6uu6"}]])
export const Undo2 = ssrIcon('undo-2', [["path",{"d":"M9 14 4 9l5-5","key":"102s5s"}],["path",{"d":"M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5a5.5 5.5 0 0 1-5.5 5.5H11","key":"f3b9sd"}]])
export const UndoDot = ssrIcon('undo-dot', [["path",{"d":"M21 17a9 9 0 0 0-15-6.7L3 13","key":"8mp6z9"}],["path",{"d":"M3 7v6h6","key":"1v2h90"}],["circle",{"cx":"12","cy":"17","r":"1","key":"1ixnty"}]])
export const UnfoldHorizontal = ssrIcon('unfold-horizontal', [["path",{"d":"M16 12h6","key":"15xry1"}],["path",{"d":"M8 12H2","key":"1jqql6"}],["path",{"d":"M12 2v2","key":"tus03m"}],["path",{"d":"M12 8v2","key":"1woqiv"}],["path",{"d":"M12 14v2","key":"8jcxud"}],["path",{"d":"M12 20v2","key":"1lh1kg"}],["path",{"d":"m19 15 3-3-3-3","key":"wjy7rq"}],["path",{"d":"m5 9-3 3 3 3","key":"j64kie"}]])
export const UnfoldVertical = ssrIcon('unfold-vertical', [["path",{"d":"M12 22v-6","key":"6o8u61"}],["path",{"d":"M12 8V2","key":"1wkif3"}],["path",{"d":"M4 12H2","key":"rhcxmi"}],["path",{"d":"M10 12H8","key":"s88cx1"}],["path",{"d":"M16 12h-2","key":"10asgb"}],["path",{"d":"M22 12h-2","key":"14jgyd"}],["path",{"d":"m15 19-3 3-3-3","key":"11eu04"}],["path",{"d":"m15 5-3-3-3 3","key":"itvq4r"}]])
export const Ungroup = ssrIcon('ungroup', [["rect",{"x":"11","y":"14","width":"10","height":"7","rx":"2","key":"nfm8rk"}],["rect",{"x":"3","y":"3","width":"10","height":"7","rx":"2","key":"1ljebb"}]])
export const Unlink = ssrIcon('unlink', [["path",{"d":"m18.84 12.25 1.72-1.71h-.02a5.004 5.004 0 0 0-.12-7.07 5.006 5.006 0 0 0-6.95 0l-1.72 1.71","key":"yqzxt4"}],["path",{"d":"m5.17 11.75-1.71 1.71a5.004 5.004 0 0 0 .12 7.07 5.006 5.006 0 0 0 6.95 0l1.71-1.71","key":"4qinb0"}],["line",{"x1":"8","x2":"8","y1":"2","y2":"5","key":"1041cp"}],["line",{"x1":"2","x2":"5","y1":"8","y2":"8","key":"14m1p5"}],["line",{"x1":"16","x2":"16","y1":"19","y2":"22","key":"rzdirn"}],["line",{"x1":"19","x2":"22","y1":"16","y2":"16","key":"ox905f"}]])
export const Unlink2 = ssrIcon('unlink-2', [["path",{"d":"M15 7h2a5 5 0 0 1 0 10h-2m-6 0H7A5 5 0 0 1 7 7h2","key":"1re2ne"}]])
export const Unplug = ssrIcon('unplug', [["path",{"d":"m19 5 3-3","key":"yk6iyv"}],["path",{"d":"m2 22 3-3","key":"19mgm9"}],["path",{"d":"M6.3 20.3a2.4 2.4 0 0 0 3.4 0L12 18l-6-6-2.3 2.3a2.4 2.4 0 0 0 0 3.4Z","key":"goz73y"}],["path",{"d":"M7.5 13.5 10 11","key":"7xgeeb"}],["path",{"d":"M10.5 16.5 13 14","key":"10btkg"}],["path",{"d":"m12 6 6 6 2.3-2.3a2.4 2.4 0 0 0 0-3.4l-2.6-2.6a2.4 2.4 0 0 0-3.4 0Z","key":"1snsnr"}]])
export const Upload = ssrIcon('upload', [["path",{"d":"M12 3v12","key":"1x0j5s"}],["path",{"d":"m17 8-5-5-5 5","key":"7q97r8"}],["path",{"d":"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4","key":"ih7n3h"}]])
export const Usb = ssrIcon('usb', [["circle",{"cx":"10","cy":"7","r":"1","key":"dypaad"}],["circle",{"cx":"4","cy":"20","r":"1","key":"22iqad"}],["path",{"d":"M4.7 19.3 19 5","key":"1enqfc"}],["path",{"d":"m21 3-3 1 2 2Z","key":"d3ov82"}],["path",{"d":"M9.26 7.68 5 12l2 5","key":"1esawj"}],["path",{"d":"m10 14 5 2 3.5-3.5","key":"v8oal5"}],["path",{"d":"m18 12 1-1 1 1-1 1Z","key":"1bh22v"}]])
export const UsbCPort = ssrIcon('usb-c-port', [["path",{"d":"M6 12h12","key":"8npq4p"}],["rect",{"x":"2","y":"8","width":"20","height":"8","rx":"4","key":"86l77p"}]])
export const User = ssrIcon('user', [["path",{"d":"M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2","key":"975kel"}],["circle",{"cx":"12","cy":"7","r":"4","key":"17ys0d"}]])
export const UserRound = ssrIcon('user-round', [["circle",{"cx":"12","cy":"8","r":"5","key":"1hypcn"}],["path",{"d":"M20 21a8 8 0 0 0-16 0","key":"rfgkzh"}]])
export const UserCheck = ssrIcon('user-check', [["path",{"d":"m16 11 2 2 4-4","key":"9rsbq5"}],["path",{"d":"M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2","key":"1yyitq"}],["circle",{"cx":"9","cy":"7","r":"4","key":"nufk8"}]])
export const UserRoundCheck = ssrIcon('user-round-check', [["path",{"d":"M2 21a8 8 0 0 1 13.292-6","key":"bjp14o"}],["circle",{"cx":"10","cy":"8","r":"5","key":"o932ke"}],["path",{"d":"m16 19 2 2 4-4","key":"1b14m6"}]])
export const UserCog = ssrIcon('user-cog', [["path",{"d":"M10 15H6a4 4 0 0 0-4 4v2","key":"1nfge6"}],["path",{"d":"m14.305 16.53.923-.382","key":"1itpsq"}],["path",{"d":"m15.228 13.852-.923-.383","key":"eplpkm"}],["path",{"d":"m16.852 12.228-.383-.923","key":"13v3q0"}],["path",{"d":"m16.852 17.772-.383.924","key":"1i8mnm"}],["path",{"d":"m19.148 12.228.383-.923","key":"1q8j1v"}],["path",{"d":"m19.53 18.696-.382-.924","key":"vk1qj3"}],["path",{"d":"m20.772 13.852.924-.383","key":"n880s0"}],["path",{"d":"m20.772 16.148.924.383","key":"1g6xey"}],["circle",{"cx":"18","cy":"15","r":"3","key":"gjjjvw"}],["circle",{"cx":"9","cy":"7","r":"4","key":"nufk8"}]])
export const UserRoundCog = ssrIcon('user-round-cog', [["path",{"d":"m14.305 19.53.923-.382","key":"3m78fa"}],["path",{"d":"m15.228 16.852-.923-.383","key":"npixar"}],["path",{"d":"m16.852 15.228-.383-.923","key":"5xggr7"}],["path",{"d":"m16.852 20.772-.383.924","key":"dpfhf9"}],["path",{"d":"m19.148 15.228.383-.923","key":"1reyyz"}],["path",{"d":"m19.53 21.696-.382-.924","key":"1goivc"}],["path",{"d":"M2 21a8 8 0 0 1 10.434-7.62","key":"1yezr2"}],["path",{"d":"m20.772 16.852.924-.383","key":"htqkph"}],["path",{"d":"m20.772 19.148.924.383","key":"9w9pjp"}],["circle",{"cx":"10","cy":"8","r":"5","key":"o932ke"}],["circle",{"cx":"18","cy":"18","r":"3","key":"1xkwt0"}]])
export const UserKey = ssrIcon('user-key', [["path",{"d":"M20 11v6","key":"d77pzp"}],["path",{"d":"M20 13h2","key":"16rner"}],["path",{"d":"M3 21v-2a4 4 0 0 1 4-4h6a4 4 0 0 1 2.072.578","key":"1yxgtw"}],["circle",{"cx":"10","cy":"7","r":"4","key":"e45bow"}],["circle",{"cx":"20","cy":"19","r":"2","key":"1obnsp"}]])
export const UserLock = ssrIcon('user-lock', [["path",{"d":"M19 16v-2a2 2 0 0 0-4 0v2","key":"17sujf"}],["path",{"d":"M9.5 15H7a4 4 0 0 0-4 4v2","key":"9it25y"}],["circle",{"cx":"10","cy":"7","r":"4","key":"e45bow"}],["rect",{"x":"13","y":"16","width":"8","height":"5","rx":".899","key":"ur80nz"}]])
export const UserMinus = ssrIcon('user-minus', [["path",{"d":"M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2","key":"1yyitq"}],["circle",{"cx":"9","cy":"7","r":"4","key":"nufk8"}],["line",{"x1":"22","x2":"16","y1":"11","y2":"11","key":"1shjgl"}]])
export const UserRoundMinus = ssrIcon('user-round-minus', [["path",{"d":"M2 21a8 8 0 0 1 13.292-6","key":"bjp14o"}],["circle",{"cx":"10","cy":"8","r":"5","key":"o932ke"}],["path",{"d":"M22 19h-6","key":"vcuq98"}]])
export const UserPen = ssrIcon('user-pen', [["path",{"d":"M11.5 15H7a4 4 0 0 0-4 4v2","key":"15lzij"}],["path",{"d":"M21.378 16.626a1 1 0 0 0-3.004-3.004l-4.01 4.012a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z","key":"1817ys"}],["circle",{"cx":"10","cy":"7","r":"4","key":"e45bow"}]])
export const UserPlus = ssrIcon('user-plus', [["path",{"d":"M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2","key":"1yyitq"}],["circle",{"cx":"9","cy":"7","r":"4","key":"nufk8"}],["line",{"x1":"19","x2":"19","y1":"8","y2":"14","key":"1bvyxn"}],["line",{"x1":"22","x2":"16","y1":"11","y2":"11","key":"1shjgl"}]])
export const UserRoundPlus = ssrIcon('user-round-plus', [["path",{"d":"M2 21a8 8 0 0 1 13.292-6","key":"bjp14o"}],["circle",{"cx":"10","cy":"8","r":"5","key":"o932ke"}],["path",{"d":"M19 16v6","key":"tddt3s"}],["path",{"d":"M22 19h-6","key":"vcuq98"}]])
export const UserRoundArrowLeft = ssrIcon('user-round-arrow-left', [["path",{"d":"m19 16-3 3","key":"lp3y45"}],["path",{"d":"M2 21a8 8 0 0 1 12.664-6.5","key":"1ap0vn"}],["path",{"d":"M22 19h-6l3 3","key":"13fjle"}],["circle",{"cx":"10","cy":"8","r":"5","key":"o932ke"}]])
export const UserRoundKey = ssrIcon('user-round-key', [["path",{"d":"M19 11v6","key":"rcqigv"}],["path",{"d":"M19 13h2","key":"1gch44"}],["path",{"d":"M2 21a8 8 0 0 1 12.868-6.349","key":"1lryzn"}],["circle",{"cx":"10","cy":"8","r":"5","key":"o932ke"}],["circle",{"cx":"19","cy":"19","r":"2","key":"17f5cg"}]])
export const UserRoundPen = ssrIcon('user-round-pen', [["path",{"d":"M2 21a8 8 0 0 1 10.821-7.487","key":"1c8h7z"}],["path",{"d":"M21.378 16.626a1 1 0 0 0-3.004-3.004l-4.01 4.012a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z","key":"1817ys"}],["circle",{"cx":"10","cy":"8","r":"5","key":"o932ke"}]])
export const UserRoundSearch = ssrIcon('user-round-search', [["circle",{"cx":"10","cy":"8","r":"5","key":"o932ke"}],["path",{"d":"M2 21a8 8 0 0 1 10.434-7.62","key":"1yezr2"}],["circle",{"cx":"18","cy":"18","r":"3","key":"1xkwt0"}],["path",{"d":"m22 22-1.9-1.9","key":"1e5ubv"}]])
export const UserRoundX = ssrIcon('user-round-x', [["path",{"d":"m16.5 16.5 5 5","key":"zc9lw7"}],["path",{"d":"M2 21a8 8 0 0 1 11.531-7.18","key":"x5izle"}],["path",{"d":"m21.5 16.5-5 5","key":"1empo3"}],["circle",{"cx":"10","cy":"8","r":"5","key":"o932ke"}]])
export const UserSearch = ssrIcon('user-search', [["circle",{"cx":"10","cy":"7","r":"4","key":"e45bow"}],["path",{"d":"M10.3 15H7a4 4 0 0 0-4 4v2","key":"3bnktk"}],["circle",{"cx":"17","cy":"17","r":"3","key":"18b49y"}],["path",{"d":"m21 21-1.9-1.9","key":"1g2n9r"}]])
export const UserShield = ssrIcon('user-shield', [["path",{"d":"M10 15H6a4 4 0 0 0-4 4v2","key":"1nfge6"}],["path",{"d":"M22 17.5c0 2.499-1.75 3.749-3.83 4.474a.5.5 0 0 1-.335-.005c-2.085-.72-3.835-1.97-3.835-4.47V14a.5.5 0 0 1 .5-.499c1 0 2.25-.6 3.12-1.36a.6.6 0 0 1 .76-.001c.875.765 2.12 1.36 3.12 1.36a.5.5 0 0 1 .5.5z","key":"16j3tf"}],["circle",{"cx":"9","cy":"7","r":"4","key":"nufk8"}]])
export const UserStar = ssrIcon('user-star', [["path",{"d":"M16.051 12.616a1 1 0 0 1 1.909.024l.737 1.452a1 1 0 0 0 .737.535l1.634.256a1 1 0 0 1 .588 1.806l-1.172 1.168a1 1 0 0 0-.282.866l.259 1.613a1 1 0 0 1-1.541 1.134l-1.465-.75a1 1 0 0 0-.912 0l-1.465.75a1 1 0 0 1-1.539-1.133l.258-1.613a1 1 0 0 0-.282-.866l-1.156-1.153a1 1 0 0 1 .572-1.822l1.633-.256a1 1 0 0 0 .737-.535z","key":"1m8t9f"}],["path",{"d":"M8 15H7a4 4 0 0 0-4 4v2","key":"l9tmp8"}],["circle",{"cx":"10","cy":"7","r":"4","key":"e45bow"}]])
export const UserX = ssrIcon('user-x', [["path",{"d":"M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2","key":"1yyitq"}],["circle",{"cx":"9","cy":"7","r":"4","key":"nufk8"}],["line",{"x1":"17","x2":"22","y1":"8","y2":"13","key":"3nzzx3"}],["line",{"x1":"22","x2":"17","y1":"8","y2":"13","key":"1swrse"}]])
export const Users = ssrIcon('users', [["path",{"d":"M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2","key":"1yyitq"}],["path",{"d":"M16 3.128a4 4 0 0 1 0 7.744","key":"16gr8j"}],["path",{"d":"M22 21v-2a4 4 0 0 0-3-3.87","key":"kshegd"}],["circle",{"cx":"9","cy":"7","r":"4","key":"nufk8"}]])
export const UsersRound = ssrIcon('users-round', [["path",{"d":"M18 21a8 8 0 0 0-16 0","key":"3ypg7q"}],["circle",{"cx":"10","cy":"8","r":"5","key":"o932ke"}],["path",{"d":"M22 20c0-3.37-2-6.5-4-8a5 5 0 0 0-.45-8.3","key":"10s06x"}]])
export const UtilityPole = ssrIcon('utility-pole', [["path",{"d":"M12 2v20","key":"t6zp3m"}],["path",{"d":"M2 5h20","key":"1fs1ex"}],["path",{"d":"M3 3v2","key":"9imdir"}],["path",{"d":"M7 3v2","key":"n0os7"}],["path",{"d":"M17 3v2","key":"1l2re6"}],["path",{"d":"M21 3v2","key":"1duuac"}],["path",{"d":"m19 5-7 7-7-7","key":"133zxf"}]])
export const Van = ssrIcon('van', [["path",{"d":"M13 6v5a1 1 0 0 0 1 1h6.102a1 1 0 0 1 .712.298l.898.91a1 1 0 0 1 .288.702V17a1 1 0 0 1-1 1h-3","key":"k3s650"}],["path",{"d":"M5 18H3a1 1 0 0 1-1-1V8a2 2 0 0 1 2-2h12c1.1 0 2.1.8 2.4 1.8l1.176 4.2","key":"fnd93u"}],["path",{"d":"M9 18h5","key":"lrx6i"}],["circle",{"cx":"16","cy":"18","r":"2","key":"1v4tcr"}],["circle",{"cx":"7","cy":"18","r":"2","key":"19iecd"}]])
export const Variable = ssrIcon('variable', [["path",{"d":"M8 21s-4-3-4-9 4-9 4-9","key":"uto9ud"}],["path",{"d":"M16 3s4 3 4 9-4 9-4 9","key":"4w2vsq"}],["line",{"x1":"15","x2":"9","y1":"9","y2":"15","key":"f7djnv"}],["line",{"x1":"9","x2":"15","y1":"9","y2":"15","key":"1shsy8"}]])
export const Vault = ssrIcon('vault', [["rect",{"width":"18","height":"18","x":"3","y":"3","rx":"2","key":"afitv7"}],["circle",{"cx":"7.5","cy":"7.5","r":".5","fill":"currentColor","key":"kqv944"}],["path",{"d":"m7.9 7.9 2.7 2.7","key":"hpeyl3"}],["circle",{"cx":"16.5","cy":"7.5","r":".5","fill":"currentColor","key":"w0ekpg"}],["path",{"d":"m13.4 10.6 2.7-2.7","key":"264c1n"}],["circle",{"cx":"7.5","cy":"16.5","r":".5","fill":"currentColor","key":"nkw3mc"}],["path",{"d":"m7.9 16.1 2.7-2.7","key":"p81g5e"}],["circle",{"cx":"16.5","cy":"16.5","r":".5","fill":"currentColor","key":"fubopw"}],["path",{"d":"m13.4 13.4 2.7 2.7","key":"abhel3"}],["circle",{"cx":"12","cy":"12","r":"2","key":"1c9p78"}]])
export const VectorSquare = ssrIcon('vector-square', [["path",{"d":"M19.5 7a24 24 0 0 1 0 10","key":"8n60xe"}],["path",{"d":"M4.5 7a24 24 0 0 0 0 10","key":"2lmadr"}],["path",{"d":"M7 19.5a24 24 0 0 0 10 0","key":"1q94o2"}],["path",{"d":"M7 4.5a24 24 0 0 1 10 0","key":"2z8ypa"}],["rect",{"x":"17","y":"17","width":"5","height":"5","rx":"1","key":"1ac74s"}],["rect",{"x":"17","y":"2","width":"5","height":"5","rx":"1","key":"1e7h5j"}],["rect",{"x":"2","y":"17","width":"5","height":"5","rx":"1","key":"1t4eah"}],["rect",{"x":"2","y":"2","width":"5","height":"5","rx":"1","key":"940dhs"}]])
export const Vegan = ssrIcon('vegan', [["path",{"d":"M16 8q6 0 6-6-6 0-6 6","key":"qsyyc4"}],["path",{"d":"M17.41 3.59a10 10 0 1 0 3 3","key":"41m9h7"}],["path",{"d":"M2 2a26.6 26.6 0 0 1 10 20c.9-6.82 1.5-9.5 4-14","key":"qiv7li"}]])
export const VenetianMask = ssrIcon('venetian-mask', [["path",{"d":"M18 11c-1.5 0-2.5.5-3 2","key":"1fod00"}],["path",{"d":"M4 6a2 2 0 0 0-2 2v4a5 5 0 0 0 5 5 8 8 0 0 1 5 2 8 8 0 0 1 5-2 5 5 0 0 0 5-5V8a2 2 0 0 0-2-2h-3a8 8 0 0 0-5 2 8 8 0 0 0-5-2z","key":"d70hit"}],["path",{"d":"M6 11c1.5 0 2.5.5 3 2","key":"136fht"}]])
export const Venus = ssrIcon('venus', [["path",{"d":"M12 15v7","key":"t2xh3l"}],["path",{"d":"M9 19h6","key":"456am0"}],["circle",{"cx":"12","cy":"9","r":"6","key":"1nw4tq"}]])
export const VenusAndMars = ssrIcon('venus-and-mars', [["path",{"d":"M10 20h4","key":"ni2waw"}],["path",{"d":"M12 16v6","key":"c8a4gj"}],["path",{"d":"M17 2h4v4","key":"vhe59"}],["path",{"d":"m21 2-5.46 5.46","key":"19kypf"}],["circle",{"cx":"12","cy":"11","r":"5","key":"16gxyc"}]])
export const Vibrate = ssrIcon('vibrate', [["path",{"d":"m2 8 2 2-2 2 2 2-2 2","key":"sv1b1"}],["path",{"d":"m22 8-2 2 2 2-2 2 2 2","key":"101i4y"}],["rect",{"width":"8","height":"14","x":"8","y":"5","rx":"1","key":"1oyrl4"}]])
export const VibrateOff = ssrIcon('vibrate-off', [["path",{"d":"m2 8 2 2-2 2 2 2-2 2","key":"sv1b1"}],["path",{"d":"m22 8-2 2 2 2-2 2 2 2","key":"101i4y"}],["path",{"d":"M8 8v10c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2","key":"1hbad5"}],["path",{"d":"M16 10.34V6c0-.55-.45-1-1-1h-4.34","key":"1x5tf0"}],["line",{"x1":"2","x2":"22","y1":"2","y2":"22","key":"a6p6uj"}]])
export const Video = ssrIcon('video', [["path",{"d":"m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.87a.5.5 0 0 0-.752-.432L16 10.5","key":"ftymec"}],["rect",{"x":"2","y":"6","width":"14","height":"12","rx":"2","key":"158x01"}]])
export const VideoOff = ssrIcon('video-off', [["path",{"d":"M10.66 6H14a2 2 0 0 1 2 2v2.5l5.248-3.062A.5.5 0 0 1 22 7.87v8.196","key":"w8jjjt"}],["path",{"d":"M16 16a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h2","key":"1xawa7"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}]])
export const Videotape = ssrIcon('videotape', [["rect",{"width":"20","height":"16","x":"2","y":"4","rx":"2","key":"18n3k1"}],["path",{"d":"M2 8h20","key":"d11cs7"}],["circle",{"cx":"8","cy":"14","r":"2","key":"1k2qr5"}],["path",{"d":"M8 12h8","key":"1wcyev"}],["circle",{"cx":"16","cy":"14","r":"2","key":"14k7lr"}]])
export const View = ssrIcon('view', [["path",{"d":"M21 17v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2","key":"mrq65r"}],["path",{"d":"M21 7V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v2","key":"be3xqs"}],["circle",{"cx":"12","cy":"12","r":"1","key":"41hilf"}],["path",{"d":"M18.944 12.33a1 1 0 0 0 0-.66 7.5 7.5 0 0 0-13.888 0 1 1 0 0 0 0 .66 7.5 7.5 0 0 0 13.888 0","key":"11ak4c"}]])
export const Voicemail = ssrIcon('voicemail', [["circle",{"cx":"6","cy":"12","r":"4","key":"1ehtga"}],["circle",{"cx":"18","cy":"12","r":"4","key":"4vafl8"}],["line",{"x1":"6","x2":"18","y1":"16","y2":"16","key":"pmt8us"}]])
export const Volleyball = ssrIcon('volleyball', [["path",{"d":"M11 7a16 16 20 0 1 10.98 4.362","key":"1mmfx7"}],["path",{"d":"M12 12a13 13 0 0 1-8.66 5","key":"14sm5y"}],["path",{"d":"M16.83 13.634a16 16 0 0 1-9.267 7.328","key":"j0eyj5"}],["path",{"d":"M20.66 17A13 13 0 0 0 12 12a13 13 0 0 1 0-10","key":"qaetsw"}],["path",{"d":"M8.17 15.366a16 16 0 0 1-1.713-11.69","key":"17ewdd"}],["circle",{"cx":"12","cy":"12","r":"10","key":"1mglay"}]])
export const Volume = ssrIcon('volume', [["path",{"d":"M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z","key":"uqj9uw"}]])
export const Volume1 = ssrIcon('volume-1', [["path",{"d":"M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z","key":"uqj9uw"}],["path",{"d":"M16 9a5 5 0 0 1 0 6","key":"1q6k2b"}]])
export const Volume2 = ssrIcon('volume-2', [["path",{"d":"M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z","key":"uqj9uw"}],["path",{"d":"M16 9a5 5 0 0 1 0 6","key":"1q6k2b"}],["path",{"d":"M19.364 18.364a9 9 0 0 0 0-12.728","key":"ijwkga"}]])
export const VolumeOff = ssrIcon('volume-off', [["path",{"d":"M16 9a5 5 0 0 1 .95 2.293","key":"1fgyg8"}],["path",{"d":"M19.364 5.636a9 9 0 0 1 1.889 9.96","key":"l3zxae"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"m7 7-.587.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298V11","key":"1gbwow"}],["path",{"d":"M9.828 4.172A.686.686 0 0 1 11 4.657v.686","key":"s2je0y"}]])
export const VolumeX = ssrIcon('volume-x', [["path",{"d":"M11 4.702a.7.7 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.7.7 0 0 0 11 19.298z","key":"1p7khw"}],["path",{"d":"m16.5 14.5 5-5","key":"cul3yw"}],["path",{"d":"m16.5 9.5 5 5","key":"1akey5"}]])
export const Vote = ssrIcon('vote', [["path",{"d":"m9 12 2 2 4-4","key":"dzmm74"}],["path",{"d":"M5 7c0-1.1.9-2 2-2h10a2 2 0 0 1 2 2v12H5V7Z","key":"1ezoue"}],["path",{"d":"M22 19H2","key":"nuriw5"}]])
export const Wallet = ssrIcon('wallet', [["path",{"d":"M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1","key":"18etb6"}],["path",{"d":"M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4","key":"xoc0q4"}]])
export const WalletMinimal = ssrIcon('wallet-minimal', [["path",{"d":"M17 14h.01","key":"7oqj8z"}],["path",{"d":"M7 7h12a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14","key":"u1rqew"}]])
export const WalletCards = ssrIcon('wallet-cards', [["path",{"d":"M3 11h3.75a2 2 0 0 1 1.6.8l.45.6a4 4 0 0 0 6.4 0l.45-.6a2 2 0 0 1 1.6-.8H21","key":"1vwh6y"}],["path",{"d":"M3 7h18","key":"1uiuf2"}],["rect",{"x":"3","y":"3","width":"18","height":"18","rx":"2","key":"h1oib"}]])
export const Wallpaper = ssrIcon('wallpaper', [["path",{"d":"M12 17v4","key":"1riwvh"}],["path",{"d":"M8 21h8","key":"1ev6f3"}],["path",{"d":"m9 17 6.1-6.1a2 2 0 0 1 2.81.01L22 15","key":"1sl52q"}],["circle",{"cx":"8","cy":"9","r":"2","key":"gjzl9d"}],["rect",{"x":"2","y":"3","width":"20","height":"14","rx":"2","key":"x3v2xh"}]])
export const Wand = ssrIcon('wand', [["path",{"d":"M15 4V2","key":"z1p9b7"}],["path",{"d":"M15 16v-2","key":"px0unx"}],["path",{"d":"M8 9h2","key":"1g203m"}],["path",{"d":"M20 9h2","key":"19tzq7"}],["path",{"d":"M17.8 11.8 19 13","key":"yihg8r"}],["path",{"d":"M15 9h.01","key":"x1ddxp"}],["path",{"d":"M17.8 6.2 19 5","key":"fd4us0"}],["path",{"d":"m3 21 9-9","key":"1jfql5"}],["path",{"d":"M12.2 6.2 11 5","key":"i3da3b"}]])
export const WandSparkles = ssrIcon('wand-sparkles', [["path",{"d":"m21.64 3.64-1.28-1.28a1.21 1.21 0 0 0-1.72 0L2.36 18.64a1.21 1.21 0 0 0 0 1.72l1.28 1.28a1.2 1.2 0 0 0 1.72 0L21.64 5.36a1.2 1.2 0 0 0 0-1.72","key":"ul74o6"}],["path",{"d":"m14 7 3 3","key":"1r5n42"}],["path",{"d":"M5 6v4","key":"ilb8ba"}],["path",{"d":"M19 14v4","key":"blhpug"}],["path",{"d":"M10 2v2","key":"7u0qdc"}],["path",{"d":"M7 8H3","key":"zfb6yr"}],["path",{"d":"M21 16h-4","key":"1cnmox"}],["path",{"d":"M11 3H9","key":"1obp7u"}]])
export const Warehouse = ssrIcon('warehouse', [["path",{"d":"M18 21V10a1 1 0 0 0-1-1H7a1 1 0 0 0-1 1v11","key":"pb2vm6"}],["path",{"d":"M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 1.132-1.803l7.95-3.974a2 2 0 0 1 1.837 0l7.948 3.974A2 2 0 0 1 22 8z","key":"doq5xv"}],["path",{"d":"M6 13h12","key":"yf64js"}],["path",{"d":"M6 17h12","key":"1jwigz"}]])
export const WashingMachine = ssrIcon('washing-machine', [["path",{"d":"M3 6h3","key":"155dbl"}],["path",{"d":"M17 6h.01","key":"e2y6kg"}],["rect",{"width":"18","height":"20","x":"3","y":"2","rx":"2","key":"od3kk9"}],["circle",{"cx":"12","cy":"13","r":"5","key":"nlbqau"}],["path",{"d":"M12 18a2.5 2.5 0 0 0 0-5 2.5 2.5 0 0 1 0-5","key":"17lach"}]])
export const Watch = ssrIcon('watch', [["path",{"d":"M12 10v2.2l1.6 1","key":"n3r21l"}],["path",{"d":"m16.13 7.66-.81-4.05a2 2 0 0 0-2-1.61h-2.68a2 2 0 0 0-2 1.61l-.78 4.05","key":"18k57s"}],["path",{"d":"m7.88 16.36.8 4a2 2 0 0 0 2 1.61h2.72a2 2 0 0 0 2-1.61l.81-4.05","key":"16ny36"}],["circle",{"cx":"12","cy":"12","r":"6","key":"1vlfrh"}]])
export const WavesHorizontal = ssrIcon('waves-horizontal', [["path",{"d":"M2 12q2.5 2 5 0t5 0 5 0 5 0","key":"8ddzzs"}],["path",{"d":"M2 19q2.5 2 5 0t5 0 5 0 5 0","key":"1wj4st"}],["path",{"d":"M2 5q2.5 2 5 0t5 0 5 0 5 0","key":"69x50u"}]])
export const WavesArrowDown = ssrIcon('waves-arrow-down', [["path",{"d":"M12 10L12 2","key":"jvb0aw"}],["path",{"d":"M16 6L12 10L8 6","key":"9j6vje"}],["path",{"d":"M2 15C2.6 15.5 3.2 16 4.5 16C7 16 7 14 9.5 14C12.1 14 11.9 16 14.5 16C17 16 17 14 19.5 14C20.8 14 21.4 14.5 22 15","key":"s2zepw"}],["path",{"d":"M2 21C2.6 21.5 3.2 22 4.5 22C7 22 7 20 9.5 20C12.1 20 11.9 22 14.5 22C17 22 17 20 19.5 20C20.8 20 21.4 20.5 22 21","key":"u68omc"}]])
export const WavesArrowUp = ssrIcon('waves-arrow-up', [["path",{"d":"M12 2v8","key":"1q4o3n"}],["path",{"d":"M2 15c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1","key":"1p9f19"}],["path",{"d":"M2 21c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1","key":"vbxynw"}],["path",{"d":"m8 6 4-4 4 4","key":"ybng9g"}]])
export const WavesLadder = ssrIcon('waves-ladder', [["path",{"d":"M19 5a2 2 0 0 0-2 2v11","key":"s41o68"}],["path",{"d":"M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1","key":"rd2r6e"}],["path",{"d":"M7 13h10","key":"1rwob1"}],["path",{"d":"M7 9h10","key":"12czzb"}],["path",{"d":"M9 5a2 2 0 0 0-2 2v11","key":"x0q4gh"}]])
export const WavesVertical = ssrIcon('waves-vertical', [["path",{"d":"M12 2q2 2.5 0 5t0 5 0 5 0 5","key":"13jdbg"}],["path",{"d":"M19 2q2 2.5 0 5t0 5 0 5 0 5","key":"1ozhzu"}],["path",{"d":"M5 2q2 2.5 0 5t0 5 0 5 0 5","key":"1bi6v5"}]])
export const Waypoints = ssrIcon('waypoints', [["path",{"d":"m10.586 5.414-5.172 5.172","key":"4mc350"}],["path",{"d":"m18.586 13.414-5.172 5.172","key":"8c96vv"}],["path",{"d":"M6 12h12","key":"8npq4p"}],["circle",{"cx":"12","cy":"20","r":"2","key":"144qzu"}],["circle",{"cx":"12","cy":"4","r":"2","key":"muu5ef"}],["circle",{"cx":"20","cy":"12","r":"2","key":"1xzzfp"}],["circle",{"cx":"4","cy":"12","r":"2","key":"1hvhnz"}]])
export const Webcam = ssrIcon('webcam', [["circle",{"cx":"12","cy":"10","r":"8","key":"1gshiw"}],["circle",{"cx":"12","cy":"10","r":"3","key":"ilqhr7"}],["path",{"d":"M7 22h10","key":"10w4w3"}],["path",{"d":"M12 22v-4","key":"1utk9m"}]])
export const WebcamOff = ssrIcon('webcam-off', [["path",{"d":"M12 22v-4","key":"1utk9m"}],["path",{"d":"M12.754 7.096a3 3 0 0 1 2.15 2.15","key":"1v0qsm"}],["path",{"d":"M12.863 12.873a3 3 0 0 1-3.736-3.735","key":"13aqxl"}],["path",{"d":"M16.566 16.57A8 8 0 0 1 5.43 5.433","key":"1hliph"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"M7 22h10","key":"10w4w3"}],["path",{"d":"M8.478 2.817a8 8 0 0 1 10.705 10.705","key":"r097k8"}]])
export const Webhook = ssrIcon('webhook', [["path",{"d":"M18 16.98h-5.99c-1.1 0-1.95.94-2.48 1.9A4 4 0 0 1 2 17c.01-.7.2-1.4.57-2","key":"q3hayz"}],["path",{"d":"m6 17 3.13-5.78c.53-.97.1-2.18-.5-3.1a4 4 0 1 1 6.89-4.06","key":"1go1hn"}],["path",{"d":"m12 6 3.13 5.73C15.66 12.7 16.9 13 18 13a4 4 0 0 1 0 8","key":"qlwsc0"}]])
export const WebhookOff = ssrIcon('webhook-off', [["path",{"d":"M17 17h-5c-1.09-.02-1.94.92-2.5 1.9A3 3 0 1 1 2.57 15","key":"1tvl6x"}],["path",{"d":"M9 3.4a4 4 0 0 1 6.52.66","key":"q04jfq"}],["path",{"d":"m6 17 3.1-5.8a2.5 2.5 0 0 0 .057-2.05","key":"azowf0"}],["path",{"d":"M20.3 20.3a4 4 0 0 1-2.3.7","key":"5joiws"}],["path",{"d":"M18.6 13a4 4 0 0 1 3.357 3.414","key":"cangb8"}],["path",{"d":"m12 6 .6 1","key":"tpjl1n"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}]])
export const Weight = ssrIcon('weight', [["circle",{"cx":"12","cy":"5","r":"3","key":"rqqgnr"}],["path",{"d":"M6.5 8a2 2 0 0 0-1.905 1.46L2.1 18.5A2 2 0 0 0 4 21h16a2 2 0 0 0 1.925-2.54L19.4 9.5A2 2 0 0 0 17.48 8Z","key":"56o5sh"}]])
export const WeightTilde = ssrIcon('weight-tilde', [["path",{"d":"M6.5 8a2 2 0 0 0-1.906 1.46L2.1 18.5A2 2 0 0 0 4 21h16a2 2 0 0 0 1.925-2.54L19.4 9.5A2 2 0 0 0 17.48 8z","key":"1wl739"}],["path",{"d":"M7.999 15a2.5 2.5 0 0 1 4 0 2.5 2.5 0 0 0 4 0","key":"1egezo"}],["circle",{"cx":"12","cy":"5","r":"3","key":"rqqgnr"}]])
export const Wheat = ssrIcon('wheat', [["path",{"d":"M2 22 16 8","key":"60hf96"}],["path",{"d":"M3.47 12.53 5 11l1.53 1.53a3.5 3.5 0 0 1 0 4.94L5 19l-1.53-1.53a3.5 3.5 0 0 1 0-4.94Z","key":"1rdhi6"}],["path",{"d":"M7.47 8.53 9 7l1.53 1.53a3.5 3.5 0 0 1 0 4.94L9 15l-1.53-1.53a3.5 3.5 0 0 1 0-4.94Z","key":"1sdzmb"}],["path",{"d":"M11.47 4.53 13 3l1.53 1.53a3.5 3.5 0 0 1 0 4.94L13 11l-1.53-1.53a3.5 3.5 0 0 1 0-4.94Z","key":"eoatbi"}],["path",{"d":"M20 2h2v2a4 4 0 0 1-4 4h-2V6a4 4 0 0 1 4-4Z","key":"19rau1"}],["path",{"d":"M11.47 17.47 13 19l-1.53 1.53a3.5 3.5 0 0 1-4.94 0L5 19l1.53-1.53a3.5 3.5 0 0 1 4.94 0Z","key":"tc8ph9"}],["path",{"d":"M15.47 13.47 17 15l-1.53 1.53a3.5 3.5 0 0 1-4.94 0L9 15l1.53-1.53a3.5 3.5 0 0 1 4.94 0Z","key":"2m8kc5"}],["path",{"d":"M19.47 9.47 21 11l-1.53 1.53a3.5 3.5 0 0 1-4.94 0L13 11l1.53-1.53a3.5 3.5 0 0 1 4.94 0Z","key":"vex3ng"}]])
export const WheatOff = ssrIcon('wheat-off', [["path",{"d":"m2 22 10-10","key":"28ilpk"}],["path",{"d":"m16 8-1.17 1.17","key":"1qqm82"}],["path",{"d":"M3.47 12.53 5 11l1.53 1.53a3.5 3.5 0 0 1 0 4.94L5 19l-1.53-1.53a3.5 3.5 0 0 1 0-4.94Z","key":"1rdhi6"}],["path",{"d":"m8 8-.53.53a3.5 3.5 0 0 0 0 4.94L9 15l1.53-1.53c.55-.55.88-1.25.98-1.97","key":"4wz8re"}],["path",{"d":"M10.91 5.26c.15-.26.34-.51.56-.73L13 3l1.53 1.53a3.5 3.5 0 0 1 .28 4.62","key":"rves66"}],["path",{"d":"M20 2h2v2a4 4 0 0 1-4 4h-2V6a4 4 0 0 1 4-4Z","key":"19rau1"}],["path",{"d":"M11.47 17.47 13 19l-1.53 1.53a3.5 3.5 0 0 1-4.94 0L5 19l1.53-1.53a3.5 3.5 0 0 1 4.94 0Z","key":"tc8ph9"}],["path",{"d":"m16 16-.53.53a3.5 3.5 0 0 1-4.94 0L9 15l1.53-1.53a3.49 3.49 0 0 1 1.97-.98","key":"ak46r"}],["path",{"d":"M18.74 13.09c.26-.15.51-.34.73-.56L21 11l-1.53-1.53a3.5 3.5 0 0 0-4.62-.28","key":"1tw520"}],["line",{"x1":"2","x2":"22","y1":"2","y2":"22","key":"a6p6uj"}]])
export const WholeWord = ssrIcon('whole-word', [["circle",{"cx":"7","cy":"12","r":"3","key":"12clwm"}],["path",{"d":"M10 9v6","key":"17i7lo"}],["circle",{"cx":"17","cy":"12","r":"3","key":"gl7c2s"}],["path",{"d":"M14 7v8","key":"dl84cr"}],["path",{"d":"M22 17v1c0 .5-.5 1-1 1H3c-.5 0-1-.5-1-1v-1","key":"lt2kga"}]])
export const Wifi = ssrIcon('wifi', [["path",{"d":"M12 20h.01","key":"zekei9"}],["path",{"d":"M2 8.82a15 15 0 0 1 20 0","key":"dnpr2z"}],["path",{"d":"M5 12.859a10 10 0 0 1 14 0","key":"1x1e6c"}],["path",{"d":"M8.5 16.429a5 5 0 0 1 7 0","key":"1bycff"}]])
export const WifiCog = ssrIcon('wifi-cog', [["path",{"d":"m14.305 19.53.923-.382","key":"3m78fa"}],["path",{"d":"m15.228 16.852-.923-.383","key":"npixar"}],["path",{"d":"m16.852 15.228-.383-.923","key":"5xggr7"}],["path",{"d":"m16.852 20.772-.383.924","key":"dpfhf9"}],["path",{"d":"m19.148 15.228.383-.923","key":"1reyyz"}],["path",{"d":"m19.53 21.696-.382-.924","key":"1goivc"}],["path",{"d":"M2 7.82a15 15 0 0 1 20 0","key":"1ovjuk"}],["path",{"d":"m20.772 16.852.924-.383","key":"htqkph"}],["path",{"d":"m20.772 19.148.924.383","key":"9w9pjp"}],["path",{"d":"M5 11.858a10 10 0 0 1 11.5-1.785","key":"3sn16i"}],["path",{"d":"M8.5 15.429a5 5 0 0 1 2.413-1.31","key":"1pxovh"}],["circle",{"cx":"18","cy":"18","r":"3","key":"1xkwt0"}]])
export const WifiHigh = ssrIcon('wifi-high', [["path",{"d":"M12 20h.01","key":"zekei9"}],["path",{"d":"M5 12.859a10 10 0 0 1 14 0","key":"1x1e6c"}],["path",{"d":"M8.5 16.429a5 5 0 0 1 7 0","key":"1bycff"}]])
export const WifiLow = ssrIcon('wifi-low', [["path",{"d":"M12 20h.01","key":"zekei9"}],["path",{"d":"M8.5 16.429a5 5 0 0 1 7 0","key":"1bycff"}]])
export const WifiOff = ssrIcon('wifi-off', [["path",{"d":"M12 20h.01","key":"zekei9"}],["path",{"d":"M8.5 16.429a5 5 0 0 1 7 0","key":"1bycff"}],["path",{"d":"M5 12.859a10 10 0 0 1 5.17-2.69","key":"1dl1wf"}],["path",{"d":"M19 12.859a10 10 0 0 0-2.007-1.523","key":"4k23kn"}],["path",{"d":"M2 8.82a15 15 0 0 1 4.177-2.643","key":"1grhjp"}],["path",{"d":"M22 8.82a15 15 0 0 0-11.288-3.764","key":"z3jwby"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}]])
export const WifiPen = ssrIcon('wifi-pen', [["path",{"d":"M2 8.82a15 15 0 0 1 20 0","key":"dnpr2z"}],["path",{"d":"M21.378 16.626a1 1 0 0 0-3.004-3.004l-4.01 4.012a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z","key":"1817ys"}],["path",{"d":"M5 12.859a10 10 0 0 1 10.5-2.222","key":"rpb7oy"}],["path",{"d":"M8.5 16.429a5 5 0 0 1 3-1.406","key":"r8bmzl"}]])
export const WifiSync = ssrIcon('wifi-sync', [["path",{"d":"M11.965 10.105v4L13.5 12.5a5 5 0 0 1 8 1.5","key":"1immaq"}],["path",{"d":"M11.965 14.105h4","key":"uejny8"}],["path",{"d":"M17.965 18.105h4L20.43 19.71a5 5 0 0 1-8-1.5","key":"1i3a7e"}],["path",{"d":"M2 8.82a15 15 0 0 1 20 0","key":"dnpr2z"}],["path",{"d":"M21.965 22.105v-4","key":"1ku6vx"}],["path",{"d":"M5 12.86a10 10 0 0 1 3-2.032","key":"pemdtu"}],["path",{"d":"M8.5 16.429h.01","key":"2bm739"}]])
export const WifiZero = ssrIcon('wifi-zero', [["path",{"d":"M12 20h.01","key":"zekei9"}]])
export const Wind = ssrIcon('wind', [["path",{"d":"M12.8 19.6A2 2 0 1 0 14 16H2","key":"148xed"}],["path",{"d":"M17.5 8a2.5 2.5 0 1 1 2 4H2","key":"1u4tom"}],["path",{"d":"M9.8 4.4A2 2 0 1 1 11 8H2","key":"75valh"}]])
export const WindArrowDown = ssrIcon('wind-arrow-down', [["path",{"d":"M10 2v8","key":"d4bbey"}],["path",{"d":"M12.8 21.6A2 2 0 1 0 14 18H2","key":"19kp1d"}],["path",{"d":"M17.5 10a2.5 2.5 0 1 1 2 4H2","key":"19kpjc"}],["path",{"d":"m6 6 4 4 4-4","key":"k13n16"}]])
export const Wine = ssrIcon('wine', [["path",{"d":"M8 22h8","key":"rmew8v"}],["path",{"d":"M7 10h10","key":"1101jm"}],["path",{"d":"M12 15v7","key":"t2xh3l"}],["path",{"d":"M12 15a5 5 0 0 0 5-5c0-2-.5-4-2-8H9c-1.5 4-2 6-2 8a5 5 0 0 0 5 5Z","key":"10ffi3"}]])
export const WineOff = ssrIcon('wine-off', [["path",{"d":"M8 22h8","key":"rmew8v"}],["path",{"d":"M7 10h3m7 0h-1.343","key":"v48bem"}],["path",{"d":"M12 15v7","key":"t2xh3l"}],["path",{"d":"M7.307 7.307A12.33 12.33 0 0 0 7 10a5 5 0 0 0 7.391 4.391M8.638 2.981C8.75 2.668 8.872 2.34 9 2h6c1.5 4 2 6 2 8 0 .407-.05.809-.145 1.198","key":"1ymjlu"}],["line",{"x1":"2","x2":"22","y1":"2","y2":"22","key":"a6p6uj"}]])
export const Workflow = ssrIcon('workflow', [["rect",{"width":"8","height":"8","x":"3","y":"3","rx":"2","key":"by2w9f"}],["path",{"d":"M7 11v4a2 2 0 0 0 2 2h4","key":"xkn7yn"}],["rect",{"width":"8","height":"8","x":"13","y":"13","rx":"2","key":"1cgmvn"}]])
export const Worm = ssrIcon('worm', [["path",{"d":"m19 12-1.5 3","key":"9bcu4o"}],["path",{"d":"M19.63 18.81 22 20","key":"121v98"}],["path",{"d":"M6.47 8.23a1.68 1.68 0 0 1 2.44 1.93l-.64 2.08a6.76 6.76 0 0 0 10.16 7.67l.42-.27a1 1 0 1 0-2.73-4.21l-.42.27a1.76 1.76 0 0 1-2.63-1.99l.64-2.08A6.66 6.66 0 0 0 3.94 3.9l-.7.4a1 1 0 1 0 2.55 4.34z","key":"1tij6q"}]])
export const Wrench = ssrIcon('wrench', [["path",{"d":"M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.106-3.105c.32-.322.863-.22.983.218a6 6 0 0 1-8.259 7.057l-7.91 7.91a1 1 0 0 1-2.999-3l7.91-7.91a6 6 0 0 1 7.057-8.259c.438.12.54.662.219.984z","key":"1ngwbx"}]])
export const WrenchOff = ssrIcon('wrench-off', [["path",{"d":"M10.747 5.093a6 6 0 0 1 6.841-2.882c.438.12.54.662.219.984L14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.106-3.105c.32-.322.863-.22.983.218a6 6 0 0 1-2.882 6.842","key":"sded7h"}],["path",{"d":"m13.5 13.5-7.88 7.88a1 1 0 0 1-2.999-3l7.88-7.88","key":"66etnh"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}]])
export const X = ssrIcon('x', [["path",{"d":"M18 6 6 18","key":"1bl5f8"}],["path",{"d":"m6 6 12 12","key":"d8bk6v"}]])
export const XLineTop = ssrIcon('x-line-top', [["path",{"d":"M18 4H6","key":"1hsngl"}],["path",{"d":"M18 8 6 20","key":"xspwia"}],["path",{"d":"m6 8 12 12","key":"qb1veh"}]])
export const Zap = ssrIcon('zap', [["path",{"d":"M15.914 4a1.5 1.5 0 00-2.474-1.561l-9 9A1.5 1.5 0 005.5 14h4.002a.5.5 0 01.471.666L8.086 20a1.5 1.5 0 002.475 1.56l9-9A1.5 1.5 0 0018.5 10h-3.997a.5.5 0 01-.472-.667z","key":"1v7up4"}]])
export const ZapOff = ssrIcon('zap-off', [["path",{"d":"M10.768 5.111 13.44 2.44a1.5 1.5 0 012.474 1.561l-1.633 4.625","key":"l6h226"}],["path",{"d":"m18.889 13.232.672-.672A1.5 1.5 0 0018.5 10h-2.844","key":"1717b9"}],["path",{"d":"m2 2 20 20","key":"1ooewy"}],["path",{"d":"m7.94 7.94-3.5 3.499A1.5 1.5 0 005.5 14h4.002a.5.5 0 01.471.666L8.086 20a1.5 1.5 0 002.475 1.56l5.5-5.5","key":"1bjzrh"}]])
export const ZodiacAquarius = ssrIcon('zodiac-aquarius', [["path",{"d":"m2 10 2.456-3.684a.7.7 0 0 1 1.106-.013l2.39 3.413a.7.7 0 0 0 1.096-.001l2.402-3.432a.7.7 0 0 1 1.098 0l2.402 3.432a.7.7 0 0 0 1.098 0l2.389-3.413a.7.7 0 0 1 1.106.013L22 10","key":"1o8iok"}],["path",{"d":"m2 18.002 2.456-3.684a.7.7 0 0 1 1.106-.013l2.39 3.413a.7.7 0 0 0 1.097 0l2.402-3.432a.7.7 0 0 1 1.098 0l2.402 3.432a.7.7 0 0 0 1.098 0l2.389-3.413a.7.7 0 0 1 1.106.013L22 18.002","key":"112qy7"}]])
export const ZodiacAries = ssrIcon('zodiac-aries', [["path",{"d":"M12 7.5a4.5 4.5 0 1 1 5 4.5","key":"k987hv"}],["path",{"d":"M7 12a4.5 4.5 0 1 1 5-4.5V21","key":"mjup0w"}]])
export const ZodiacCancer = ssrIcon('zodiac-cancer', [["path",{"d":"M21 14.5A9 6.5 0 0 1 5.5 19","key":"1xj2o6"}],["path",{"d":"M3 9.5A9 6.5 0 0 1 18.5 5","key":"1gln3t"}],["circle",{"cx":"17.5","cy":"14.5","r":"3.5","key":"1ccu1t"}],["circle",{"cx":"6.5","cy":"9.5","r":"3.5","key":"x5tc2d"}]])
export const ZodiacCapricorn = ssrIcon('zodiac-capricorn', [["path",{"d":"M11 21a3 3 0 0 0 3-3V6.5a1 1 0 0 0-7 0","key":"1kkncs"}],["path",{"d":"M7 19V6a3 3 0 0 0-3-3h0","key":"1jg5y1"}],["circle",{"cx":"17","cy":"17","r":"3","key":"18b49y"}]])
export const ZodiacGemini = ssrIcon('zodiac-gemini', [["path",{"d":"M16 4.525v14.948","key":"bgoxo0"}],["path",{"d":"M20 3A17 17 0 0 1 4 3","key":"1djemw"}],["path",{"d":"M4 21a17 17 0 0 1 16 0","key":"onoyo7"}],["path",{"d":"M8 4.525v14.948","key":"u5iyof"}]])
export const ZodiacLeo = ssrIcon('zodiac-leo', [["path",{"d":"M10 16c0-4-3-4.5-3-8a5 5 0 0 1 10 0c0 3.466-3 6.196-3 10a3 3 0 0 0 6 0","key":"1qj6nb"}],["circle",{"cx":"7","cy":"16","r":"3","key":"yyv3zl"}]])
export const ZodiacLibra = ssrIcon('zodiac-libra', [["path",{"d":"M3 16h6.857c.162-.012.19-.323.038-.38a6 6 0 1 1 4.212 0c-.153.057-.125.368.038.38H21","key":"1novf0"}],["path",{"d":"M3 20h18","key":"1l19wn"}]])
export const ZodiacOphiuchus = ssrIcon('zodiac-ophiuchus', [["path",{"d":"M3 10A6.06 6.06 0 0 1 12 10 A6.06 6.06 0 0 0 21 10","key":"13lfmc"}],["path",{"d":"M6 3v12a6 6 0 0 0 12 0V3","key":"1jnivp"}]])
export const ZodiacPisces = ssrIcon('zodiac-pisces', [["path",{"d":"M19 21a15 15 0 0 1 0-18","key":"br2vug"}],["path",{"d":"M20 12H4","key":"1mtusc"}],["path",{"d":"M5 3a15 15 0 0 1 0 18","key":"1w7hae"}]])
export const ZodiacSagittarius = ssrIcon('zodiac-sagittarius', [["path",{"d":"M15 3h6v6","key":"1q9fwt"}],["path",{"d":"M21 3 3 21","key":"1011np"}],["path",{"d":"m9 9 6 6","key":"z0biqf"}]])
export const ZodiacScorpio = ssrIcon('zodiac-scorpio', [["path",{"d":"M10 19V5.5a1 1 0 0 1 5 0V17a2 2 0 0 0 2 2h5l-3-3","key":"1w8g0z"}],["path",{"d":"m22 19-3 3","key":"1ix4wq"}],["path",{"d":"M5 19V5.5a1 1 0 0 1 5 0","key":"1d4oa3"}],["path",{"d":"M5 5.5A2.5 2.5 0 0 0 2.5 3","key":"gp646f"}]])
export const ZodiacTaurus = ssrIcon('zodiac-taurus', [["circle",{"cx":"12","cy":"15","r":"6","key":"lhqcmb"}],["path",{"d":"M18 3A6 6 0 0 1 6 3","key":"1p399e"}]])
export const ZodiacVirgo = ssrIcon('zodiac-virgo', [["path",{"d":"M11 5.5a1 1 0 0 1 5 0V16a5 5 0 0 0 5 5","key":"1szkuh"}],["path",{"d":"M16 11.5a1 1 0 0 1 5 0V16a5 5 0 0 1-5 5","key":"pyq0k2"}],["path",{"d":"M6 19V6a3 3 0 0 0-3-3h0","key":"pvee4g"}],["path",{"d":"M6 5.5a1 1 0 0 1 5 0V19","key":"vncctg"}]])
export const ZoomIn = ssrIcon('zoom-in', [["circle",{"cx":"11","cy":"11","r":"8","key":"4ej97u"}],["line",{"x1":"21","x2":"16.65","y1":"21","y2":"16.65","key":"13gj7c"}],["line",{"x1":"11","x2":"11","y1":"8","y2":"14","key":"1vmskp"}],["line",{"x1":"8","x2":"14","y1":"11","y2":"11","key":"durymu"}]])
export const ZoomOut = ssrIcon('zoom-out', [["circle",{"cx":"11","cy":"11","r":"8","key":"4ej97u"}],["line",{"x1":"21","x2":"16.65","y1":"21","y2":"16.65","key":"13gj7c"}],["line",{"x1":"8","x2":"14","y1":"11","y2":"11","key":"durymu"}]])
export { AArrowDown as AArrowDownIcon }
export { AArrowUp as AArrowUpIcon }
export { ALargeSmall as ALargeSmallIcon }
export { Accessibility as AccessibilityIcon }
export { Activity as ActivityIcon }
export { SquareActivity as ActivitySquare }
export { SquareActivity as ActivitySquareIcon }
export { Ad as AdIcon }
export { AirVent as AirVentIcon }
export { Airplay as AirplayIcon }
export { AlarmClockCheck as AlarmCheck }
export { AlarmClockCheck as AlarmCheckIcon }
export { AlarmClockCheck as AlarmClockCheckIcon }
export { AlarmClock as AlarmClockIcon }
export { AlarmClockMinus as AlarmClockMinusIcon }
export { AlarmClockOff as AlarmClockOffIcon }
export { AlarmClockPlus as AlarmClockPlusIcon }
export { AlarmClockMinus as AlarmMinus }
export { AlarmClockMinus as AlarmMinusIcon }
export { AlarmClockPlus as AlarmPlus }
export { AlarmClockPlus as AlarmPlusIcon }
export { AlarmSmoke as AlarmSmokeIcon }
export { Album as AlbumIcon }
export { CircleAlert as AlertCircle }
export { CircleAlert as AlertCircleIcon }
export { OctagonAlert as AlertOctagon }
export { OctagonAlert as AlertOctagonIcon }
export { TriangleAlert as AlertTriangle }
export { TriangleAlert as AlertTriangleIcon }
export { TextAlignCenter as AlignCenter }
export { AlignCenterHorizontal as AlignCenterHorizontalIcon }
export { TextAlignCenter as AlignCenterIcon }
export { AlignCenterVertical as AlignCenterVerticalIcon }
export { AlignEndHorizontal as AlignEndHorizontalIcon }
export { AlignEndVertical as AlignEndVerticalIcon }
export { AlignHorizontalDistributeCenter as AlignHorizontalDistributeCenterIcon }
export { AlignHorizontalDistributeEnd as AlignHorizontalDistributeEndIcon }
export { AlignHorizontalDistributeStart as AlignHorizontalDistributeStartIcon }
export { AlignHorizontalJustifyCenter as AlignHorizontalJustifyCenterIcon }
export { AlignHorizontalJustifyEnd as AlignHorizontalJustifyEndIcon }
export { AlignHorizontalJustifyStart as AlignHorizontalJustifyStartIcon }
export { AlignHorizontalSpaceAround as AlignHorizontalSpaceAroundIcon }
export { AlignHorizontalSpaceBetween as AlignHorizontalSpaceBetweenIcon }
export { TextAlignJustify as AlignJustify }
export { TextAlignJustify as AlignJustifyIcon }
export { TextAlignStart as AlignLeft }
export { TextAlignStart as AlignLeftIcon }
export { TextAlignEnd as AlignRight }
export { TextAlignEnd as AlignRightIcon }
export { AlignStartHorizontal as AlignStartHorizontalIcon }
export { AlignStartVertical as AlignStartVerticalIcon }
export { AlignVerticalDistributeCenter as AlignVerticalDistributeCenterIcon }
export { AlignVerticalDistributeEnd as AlignVerticalDistributeEndIcon }
export { AlignVerticalDistributeStart as AlignVerticalDistributeStartIcon }
export { AlignVerticalJustifyCenter as AlignVerticalJustifyCenterIcon }
export { AlignVerticalJustifyEnd as AlignVerticalJustifyEndIcon }
export { AlignVerticalJustifyStart as AlignVerticalJustifyStartIcon }
export { AlignVerticalSpaceAround as AlignVerticalSpaceAroundIcon }
export { AlignVerticalSpaceBetween as AlignVerticalSpaceBetweenIcon }
export { Ambulance as AmbulanceIcon }
export { Ampersand as AmpersandIcon }
export { Ampersands as AmpersandsIcon }
export { Amphora as AmphoraIcon }
export { Anchor as AnchorIcon }
export { Angle as AngleIcon }
export { FaceAngry as Angry }
export { FaceAngry as AngryIcon }
export { FaceExpressionless as Annoyed }
export { FaceExpressionless as AnnoyedIcon }
export { Antenna as AntennaIcon }
export { Anvil as AnvilIcon }
export { Aperture as ApertureIcon }
export { AppWindow as AppWindowIcon }
export { AppWindowMac as AppWindowMacIcon }
export { Apple as AppleIcon }
export { Archive as ArchiveIcon }
export { ArchiveRestore as ArchiveRestoreIcon }
export { ArchiveX as ArchiveXIcon }
export { ChartArea as AreaChart }
export { ChartArea as AreaChartIcon }
export { Armchair as ArmchairIcon }
export { ArrowBigDownDash as ArrowBigDownDashIcon }
export { ArrowBigDown as ArrowBigDownIcon }
export { ArrowBigLeftDash as ArrowBigLeftDashIcon }
export { ArrowBigLeft as ArrowBigLeftIcon }
export { ArrowBigRightDash as ArrowBigRightDashIcon }
export { ArrowBigRight as ArrowBigRightIcon }
export { ArrowBigUpDash as ArrowBigUpDashIcon }
export { ArrowBigUp as ArrowBigUpIcon }
export { ArrowDown01 as ArrowDown01Icon }
export { ArrowDown10 as ArrowDown10Icon }
export { ArrowDownAZ as ArrowDownAZIcon }
export { ArrowDownAZ as ArrowDownAz }
export { ArrowDownAZ as ArrowDownAzIcon }
export { CircleArrowDown as ArrowDownCircle }
export { CircleArrowDown as ArrowDownCircleIcon }
export { ArrowDownFromLine as ArrowDownFromLineIcon }
export { ArrowDown as ArrowDownIcon }
export { CircleArrowOutDownLeft as ArrowDownLeftFromCircle }
export { CircleArrowOutDownLeft as ArrowDownLeftFromCircleIcon }
export { SquareArrowOutDownLeft as ArrowDownLeftFromSquare }
export { SquareArrowOutDownLeft as ArrowDownLeftFromSquareIcon }
export { ArrowDownLeft as ArrowDownLeftIcon }
export { SquareArrowDownLeft as ArrowDownLeftSquare }
export { SquareArrowDownLeft as ArrowDownLeftSquareIcon }
export { ArrowDownNarrowWide as ArrowDownNarrowWideIcon }
export { CircleArrowOutDownRight as ArrowDownRightFromCircle }
export { CircleArrowOutDownRight as ArrowDownRightFromCircleIcon }
export { SquareArrowOutDownRight as ArrowDownRightFromSquare }
export { SquareArrowOutDownRight as ArrowDownRightFromSquareIcon }
export { ArrowDownRight as ArrowDownRightIcon }
export { SquareArrowDownRight as ArrowDownRightSquare }
export { SquareArrowDownRight as ArrowDownRightSquareIcon }
export { SquareArrowDown as ArrowDownSquare }
export { SquareArrowDown as ArrowDownSquareIcon }
export { ArrowDownToDot as ArrowDownToDotIcon }
export { ArrowDownToLine as ArrowDownToLineIcon }
export { ArrowDownUp as ArrowDownUpIcon }
export { ArrowDownWideNarrow as ArrowDownWideNarrowIcon }
export { ArrowDownZA as ArrowDownZAIcon }
export { ArrowDownZA as ArrowDownZa }
export { ArrowDownZA as ArrowDownZaIcon }
export { CircleArrowLeft as ArrowLeftCircle }
export { CircleArrowLeft as ArrowLeftCircleIcon }
export { ArrowLeftFromLine as ArrowLeftFromLineIcon }
export { ArrowLeft as ArrowLeftIcon }
export { ArrowLeftRight as ArrowLeftRightIcon }
export { SquareArrowLeft as ArrowLeftSquare }
export { SquareArrowLeft as ArrowLeftSquareIcon }
export { ArrowLeftToLine as ArrowLeftToLineIcon }
export { CircleArrowRight as ArrowRightCircle }
export { CircleArrowRight as ArrowRightCircleIcon }
export { ArrowRightFromLine as ArrowRightFromLineIcon }
export { ArrowRight as ArrowRightIcon }
export { ArrowRightLeft as ArrowRightLeftIcon }
export { SquareArrowRight as ArrowRightSquare }
export { SquareArrowRight as ArrowRightSquareIcon }
export { ArrowRightToLine as ArrowRightToLineIcon }
export { ArrowUp01 as ArrowUp01Icon }
export { ArrowUp10 as ArrowUp10Icon }
export { ArrowUpAZ as ArrowUpAZIcon }
export { ArrowUpAZ as ArrowUpAz }
export { ArrowUpAZ as ArrowUpAzIcon }
export { CircleArrowUp as ArrowUpCircle }
export { CircleArrowUp as ArrowUpCircleIcon }
export { ArrowUpDown as ArrowUpDownIcon }
export { ArrowUpFromDot as ArrowUpFromDotIcon }
export { ArrowUpFromLine as ArrowUpFromLineIcon }
export { ArrowUp as ArrowUpIcon }
export { CircleArrowOutUpLeft as ArrowUpLeftFromCircle }
export { CircleArrowOutUpLeft as ArrowUpLeftFromCircleIcon }
export { SquareArrowOutUpLeft as ArrowUpLeftFromSquare }
export { SquareArrowOutUpLeft as ArrowUpLeftFromSquareIcon }
export { ArrowUpLeft as ArrowUpLeftIcon }
export { SquareArrowUpLeft as ArrowUpLeftSquare }
export { SquareArrowUpLeft as ArrowUpLeftSquareIcon }
export { ArrowUpNarrowWide as ArrowUpNarrowWideIcon }
export { CircleArrowOutUpRight as ArrowUpRightFromCircle }
export { CircleArrowOutUpRight as ArrowUpRightFromCircleIcon }
export { SquareArrowOutUpRight as ArrowUpRightFromSquare }
export { SquareArrowOutUpRight as ArrowUpRightFromSquareIcon }
export { ArrowUpRight as ArrowUpRightIcon }
export { SquareArrowUpRight as ArrowUpRightSquare }
export { SquareArrowUpRight as ArrowUpRightSquareIcon }
export { SquareArrowUp as ArrowUpSquare }
export { SquareArrowUp as ArrowUpSquareIcon }
export { ArrowUpToLine as ArrowUpToLineIcon }
export { ArrowUpWideNarrow as ArrowUpWideNarrowIcon }
export { ArrowUpZA as ArrowUpZAIcon }
export { ArrowUpZA as ArrowUpZa }
export { ArrowUpZA as ArrowUpZaIcon }
export { ArrowsUpFromLine as ArrowsUpFromLineIcon }
export { Asterisk as AsteriskIcon }
export { SquareAsterisk as AsteriskSquare }
export { SquareAsterisk as AsteriskSquareIcon }
export { Astroid as AstroidIcon }
export { AtSign as AtSignIcon }
export { Atom as AtomIcon }
export { AudioLines as AudioLinesIcon }
export { AudioLinesOff as AudioLinesOffIcon }
export { AudioLinesX as AudioLinesXIcon }
export { AudioWaveform as AudioWaveformIcon }
export { Award as AwardIcon }
export { Axe as AxeIcon }
export { Axis3d as Axis3D }
export { Axis3d as Axis3DIcon }
export { Axis3d as Axis3dIcon }
export { Baby as BabyIcon }
export { Backpack as BackpackIcon }
export { BadgeAlert as BadgeAlertIcon }
export { BadgeCent as BadgeCentIcon }
export { BadgeCheck as BadgeCheckIcon }
export { BadgeDollarSign as BadgeDollarSignIcon }
export { BadgeEuro as BadgeEuroIcon }
export { BadgeQuestionMark as BadgeHelp }
export { BadgeQuestionMark as BadgeHelpIcon }
export { Badge as BadgeIcon }
export { BadgeIndianRupee as BadgeIndianRupeeIcon }
export { BadgeInfo as BadgeInfoIcon }
export { BadgeJapaneseYen as BadgeJapaneseYenIcon }
export { BadgeMinus as BadgeMinusIcon }
export { BadgePercent as BadgePercentIcon }
export { BadgePlus as BadgePlusIcon }
export { BadgePoundSterling as BadgePoundSterlingIcon }
export { BadgeQuestionMark as BadgeQuestionMarkIcon }
export { BadgeRussianRuble as BadgeRussianRubleIcon }
export { BadgeSwissFranc as BadgeSwissFrancIcon }
export { BadgeTurkishLira as BadgeTurkishLiraIcon }
export { BadgeX as BadgeXIcon }
export { BaggageClaim as BaggageClaimIcon }
export { Balloon as BalloonIcon }
export { Ban as BanIcon }
export { Banana as BananaIcon }
export { Bandage as BandageIcon }
export { BanknoteArrowDown as BanknoteArrowDownIcon }
export { BanknoteArrowUp as BanknoteArrowUpIcon }
export { BanknoteCheck as BanknoteCheckIcon }
export { Banknote as BanknoteIcon }
export { BanknoteX as BanknoteXIcon }
export { ChartNoAxesColumnIncreasing as BarChart }
export { ChartNoAxesColumn as BarChart2 }
export { ChartNoAxesColumn as BarChart2Icon }
export { ChartColumn as BarChart3 }
export { ChartColumn as BarChart3Icon }
export { ChartColumnIncreasing as BarChart4 }
export { ChartColumnIncreasing as BarChart4Icon }
export { ChartColumnBig as BarChartBig }
export { ChartColumnBig as BarChartBigIcon }
export { ChartBar as BarChartHorizontal }
export { ChartBarBig as BarChartHorizontalBig }
export { ChartBarBig as BarChartHorizontalBigIcon }
export { ChartBar as BarChartHorizontalIcon }
export { ChartNoAxesColumnIncreasing as BarChartIcon }
export { Barcode as BarcodeIcon }
export { Barrel as BarrelIcon }
export { Baseline as BaselineIcon }
export { Bath as BathIcon }
export { BatteryCharging as BatteryChargingIcon }
export { BatteryFull as BatteryFullIcon }
export { Battery as BatteryIcon }
export { BatteryLow as BatteryLowIcon }
export { BatteryMedium as BatteryMediumIcon }
export { BatteryPlus as BatteryPlusIcon }
export { BatteryWarning as BatteryWarningIcon }
export { Beaker as BeakerIcon }
export { Bean as BeanIcon }
export { BeanOff as BeanOffIcon }
export { BedDouble as BedDoubleIcon }
export { Bed as BedIcon }
export { BedSingle as BedSingleIcon }
export { Beef as BeefIcon }
export { BeefOff as BeefOffIcon }
export { Beer as BeerIcon }
export { BeerOff as BeerOffIcon }
export { BellCheck as BellCheckIcon }
export { BellDot as BellDotIcon }
export { BellElectric as BellElectricIcon }
export { Bell as BellIcon }
export { BellMinus as BellMinusIcon }
export { BellOff as BellOffIcon }
export { BellPlus as BellPlusIcon }
export { BellRing as BellRingIcon }
export { BetweenHorizontalEnd as BetweenHorizonalEnd }
export { BetweenHorizontalEnd as BetweenHorizonalEndIcon }
export { BetweenHorizontalStart as BetweenHorizonalStart }
export { BetweenHorizontalStart as BetweenHorizonalStartIcon }
export { BetweenHorizontalEnd as BetweenHorizontalEndIcon }
export { BetweenHorizontalStart as BetweenHorizontalStartIcon }
export { BetweenVerticalEnd as BetweenVerticalEndIcon }
export { BetweenVerticalStart as BetweenVerticalStartIcon }
export { BicepsFlexed as BicepsFlexedIcon }
export { Bike as BikeIcon }
export { Binary as BinaryIcon }
export { Binoculars as BinocularsIcon }
export { Biohazard as BiohazardIcon }
export { Bird as BirdIcon }
export { Birdhouse as BirdhouseIcon }
export { Bitcoin as BitcoinIcon }
export { Blend as BlendIcon }
export { Blender as BlenderIcon }
export { Blinds as BlindsIcon }
export { Blocks as BlocksIcon }
export { BluetoothConnected as BluetoothConnectedIcon }
export { Bluetooth as BluetoothIcon }
export { BluetoothOff as BluetoothOffIcon }
export { BluetoothSearching as BluetoothSearchingIcon }
export { Bold as BoldIcon }
export { Bolt as BoltIcon }
export { Bomb as BombIcon }
export { BoneFracture as BoneFractureIcon }
export { Bone as BoneIcon }
export { BookA as BookAIcon }
export { BookAlert as BookAlertIcon }
export { BookAudio as BookAudioIcon }
export { BookCheck as BookCheckIcon }
export { BookCopy as BookCopyIcon }
export { BookDashed as BookDashedIcon }
export { BookDown as BookDownIcon }
export { BookHeadphones as BookHeadphonesIcon }
export { BookHeart as BookHeartIcon }
export { Book as BookIcon }
export { BookImage as BookImageIcon }
export { BookKey as BookKeyIcon }
export { BookLock as BookLockIcon }
export { BookMarked as BookMarkedIcon }
export { BookMinus as BookMinusIcon }
export { BookOpenCheck as BookOpenCheckIcon }
export { BookOpen as BookOpenIcon }
export { BookOpenText as BookOpenTextIcon }
export { BookPlus as BookPlusIcon }
export { BookSearch as BookSearchIcon }
export { BookDashed as BookTemplate }
export { BookDashed as BookTemplateIcon }
export { BookText as BookTextIcon }
export { BookType as BookTypeIcon }
export { BookUp2 as BookUp2Icon }
export { BookUp as BookUpIcon }
export { BookUser as BookUserIcon }
export { BookX as BookXIcon }
export { BookmarkCheck as BookmarkCheckIcon }
export { Bookmark as BookmarkIcon }
export { BookmarkMinus as BookmarkMinusIcon }
export { BookmarkOff as BookmarkOffIcon }
export { BookmarkPlus as BookmarkPlusIcon }
export { BookmarkX as BookmarkXIcon }
export { BoomBox as BoomBoxIcon }
export { Bot as BotIcon }
export { BotMessageSquare as BotMessageSquareIcon }
export { BotOff as BotOffIcon }
export { BottleWine as BottleWineIcon }
export { BowArrow as BowArrowIcon }
export { Box as BoxIcon }
export { SquareDashed as BoxSelect }
export { SquareDashed as BoxSelectIcon }
export { Boxes as BoxesIcon }
export { Braces as BracesIcon }
export { Brackets as BracketsIcon }
export { BrainCircuit as BrainCircuitIcon }
export { BrainCog as BrainCogIcon }
export { Brain as BrainIcon }
export { BrickWallFire as BrickWallFireIcon }
export { BrickWall as BrickWallIcon }
export { BrickWallShield as BrickWallShieldIcon }
export { BriefcaseBusiness as BriefcaseBusinessIcon }
export { BriefcaseConveyorBelt as BriefcaseConveyorBeltIcon }
export { Briefcase as BriefcaseIcon }
export { BriefcaseMedical as BriefcaseMedicalIcon }
export { BringToFront as BringToFrontIcon }
export { Broccoli as BroccoliIcon }
export { Broom as BroomIcon }
export { BroomSparkles as BroomSparklesIcon }
export { BrushCleaning as BrushCleaningIcon }
export { Brush as BrushIcon }
export { Bubbles as BubblesIcon }
export { Bug as BugIcon }
export { BugOff as BugOffIcon }
export { BugPlay as BugPlayIcon }
export { Building2 as Building2Icon }
export { Building as BuildingIcon }
export { BusFront as BusFrontIcon }
export { Bus as BusIcon }
export { CableCar as CableCarIcon }
export { Cable as CableIcon }
export { Cake as CakeIcon }
export { CakeSlice as CakeSliceIcon }
export { Calculator as CalculatorIcon }
export { Calendar1 as Calendar1Icon }
export { CalendarArrowDown as CalendarArrowDownIcon }
export { CalendarArrowUp as CalendarArrowUpIcon }
export { CalendarCheck2 as CalendarCheck2Icon }
export { CalendarCheck as CalendarCheckIcon }
export { CalendarClock as CalendarClockIcon }
export { CalendarCog as CalendarCogIcon }
export { CalendarDays as CalendarDaysIcon }
export { CalendarFold as CalendarFoldIcon }
export { CalendarHeart as CalendarHeartIcon }
export { Calendar as CalendarIcon }
export { CalendarMinus2 as CalendarMinus2Icon }
export { CalendarMinus as CalendarMinusIcon }
export { CalendarOff as CalendarOffIcon }
export { CalendarPlus2 as CalendarPlus2Icon }
export { CalendarPlus as CalendarPlusIcon }
export { CalendarRange as CalendarRangeIcon }
export { CalendarSearch as CalendarSearchIcon }
export { CalendarSync as CalendarSyncIcon }
export { CalendarX2 as CalendarX2Icon }
export { CalendarX as CalendarXIcon }
export { Calendars as CalendarsIcon }
export { Camera as CameraIcon }
export { CameraOff as CameraOffIcon }
export { ChartCandlestick as CandlestickChart }
export { ChartCandlestick as CandlestickChartIcon }
export { CandyCane as CandyCaneIcon }
export { Candy as CandyIcon }
export { CandyOff as CandyOffIcon }
export { Cannabis as CannabisIcon }
export { CannabisOff as CannabisOffIcon }
export { Captions as CaptionsIcon }
export { CaptionsOff as CaptionsOffIcon }
export { CarBattery as CarBatteryIcon }
export { CarFront as CarFrontIcon }
export { Car as CarIcon }
export { CarTaxiFront as CarTaxiFrontIcon }
export { Caravan as CaravanIcon }
export { CardSim as CardSimIcon }
export { Carrot as CarrotIcon }
export { CaseLower as CaseLowerIcon }
export { CaseSensitive as CaseSensitiveIcon }
export { CaseUpper as CaseUpperIcon }
export { CassetteTape as CassetteTapeIcon }
export { Cast as CastIcon }
export { Castle as CastleIcon }
export { Cat as CatIcon }
export { Cctv as CctvIcon }
export { CctvOff as CctvOffIcon }
export { ChartArea as ChartAreaIcon }
export { ChartBarBig as ChartBarBigIcon }
export { ChartBarDecreasing as ChartBarDecreasingIcon }
export { ChartBar as ChartBarIcon }
export { ChartBarIncreasing as ChartBarIncreasingIcon }
export { ChartBarStacked as ChartBarStackedIcon }
export { ChartCandlestick as ChartCandlestickIcon }
export { ChartColumnBig as ChartColumnBigIcon }
export { ChartColumnDecreasing as ChartColumnDecreasingIcon }
export { ChartColumn as ChartColumnIcon }
export { ChartColumnIncreasing as ChartColumnIncreasingIcon }
export { ChartColumnStacked as ChartColumnStackedIcon }
export { ChartGantt as ChartGanttIcon }
export { ChartLine as ChartLineIcon }
export { ChartNetwork as ChartNetworkIcon }
export { ChartNoAxesColumnDecreasing as ChartNoAxesColumnDecreasingIcon }
export { ChartNoAxesColumn as ChartNoAxesColumnIcon }
export { ChartNoAxesColumnIncreasing as ChartNoAxesColumnIncreasingIcon }
export { ChartNoAxesCombined as ChartNoAxesCombinedIcon }
export { ChartNoAxesGantt as ChartNoAxesGanttIcon }
export { ChartPie as ChartPieIcon }
export { ChartScatter as ChartScatterIcon }
export { ChartSpline as ChartSplineIcon }
export { CheckCheck as CheckCheckIcon }
export { CircleCheckBig as CheckCircle }
export { CircleCheck as CheckCircle2 }
export { CircleCheck as CheckCircle2Icon }
export { CircleCheckBig as CheckCircleIcon }
export { Check as CheckIcon }
export { CheckLine as CheckLineIcon }
export { SquareCheckBig as CheckSquare }
export { SquareCheck as CheckSquare2 }
export { SquareCheck as CheckSquare2Icon }
export { SquareCheckBig as CheckSquareIcon }
export { ChefHat as ChefHatIcon }
export { Cherry as CherryIcon }
export { ChessBishop as ChessBishopIcon }
export { ChessKing as ChessKingIcon }
export { ChessKnight as ChessKnightIcon }
export { ChessPawn as ChessPawnIcon }
export { ChessQueen as ChessQueenIcon }
export { ChessRook as ChessRookIcon }
export { CircleChevronDown as ChevronDownCircle }
export { CircleChevronDown as ChevronDownCircleIcon }
export { ChevronDown as ChevronDownIcon }
export { SquareChevronDown as ChevronDownSquare }
export { SquareChevronDown as ChevronDownSquareIcon }
export { ChevronFirst as ChevronFirstIcon }
export { ChevronLast as ChevronLastIcon }
export { CircleChevronLeft as ChevronLeftCircle }
export { CircleChevronLeft as ChevronLeftCircleIcon }
export { ChevronLeft as ChevronLeftIcon }
export { SquareChevronLeft as ChevronLeftSquare }
export { SquareChevronLeft as ChevronLeftSquareIcon }
export { CircleChevronRight as ChevronRightCircle }
export { CircleChevronRight as ChevronRightCircleIcon }
export { ChevronRight as ChevronRightIcon }
export { SquareChevronRight as ChevronRightSquare }
export { SquareChevronRight as ChevronRightSquareIcon }
export { CircleChevronUp as ChevronUpCircle }
export { CircleChevronUp as ChevronUpCircleIcon }
export { ChevronUp as ChevronUpIcon }
export { SquareChevronUp as ChevronUpSquare }
export { SquareChevronUp as ChevronUpSquareIcon }
export { ChevronsDown as ChevronsDownIcon }
export { ChevronsDownUp as ChevronsDownUpIcon }
export { ChevronsLeft as ChevronsLeftIcon }
export { ChevronsLeftRightEllipsis as ChevronsLeftRightEllipsisIcon }
export { ChevronsLeftRight as ChevronsLeftRightIcon }
export { ChevronsRight as ChevronsRightIcon }
export { ChevronsRightLeft as ChevronsRightLeftIcon }
export { ChevronsUpDown as ChevronsUpDownIcon }
export { ChevronsUp as ChevronsUpIcon }
export { Church as ChurchIcon }
export { Cigarette as CigaretteIcon }
export { CigaretteOff as CigaretteOffIcon }
export { CircleAlert as CircleAlertIcon }
export { CircleArrowDown as CircleArrowDownIcon }
export { CircleArrowLeft as CircleArrowLeftIcon }
export { CircleArrowOutDownLeft as CircleArrowOutDownLeftIcon }
export { CircleArrowOutDownRight as CircleArrowOutDownRightIcon }
export { CircleArrowOutUpLeft as CircleArrowOutUpLeftIcon }
export { CircleArrowOutUpRight as CircleArrowOutUpRightIcon }
export { CircleArrowRight as CircleArrowRightIcon }
export { CircleArrowUp as CircleArrowUpIcon }
export { CircleCheckBig as CircleCheckBigIcon }
export { CircleCheck as CircleCheckIcon }
export { CircleChevronDown as CircleChevronDownIcon }
export { CircleChevronLeft as CircleChevronLeftIcon }
export { CircleChevronRight as CircleChevronRightIcon }
export { CircleChevronUp as CircleChevronUpIcon }
export { CircleDashed as CircleDashedIcon }
export { CircleDivide as CircleDivideIcon }
export { CircleDollarSign as CircleDollarSignIcon }
export { CircleDotDashed as CircleDotDashedIcon }
export { CircleDot as CircleDotIcon }
export { CircleEllipsis as CircleEllipsisIcon }
export { CircleEqual as CircleEqualIcon }
export { CircleEuro as CircleEuroIcon }
export { CircleFadingArrowUp as CircleFadingArrowUpIcon }
export { CircleFadingPlus as CircleFadingPlusIcon }
export { CircleGauge as CircleGaugeIcon }
export { CircleQuestionMark as CircleHelp }
export { CircleQuestionMark as CircleHelpIcon }
export { Circle as CircleIcon }
export { CircleMinus as CircleMinusIcon }
export { CircleOff as CircleOffIcon }
export { CircleParking as CircleParkingIcon }
export { CircleParkingOff as CircleParkingOffIcon }
export { CirclePause as CirclePauseIcon }
export { CirclePercent as CirclePercentIcon }
export { CirclePile as CirclePileIcon }
export { CirclePlay as CirclePlayIcon }
export { CirclePlus as CirclePlusIcon }
export { CirclePoundSterling as CirclePoundSterlingIcon }
export { CirclePower as CirclePowerIcon }
export { CircleQuestionMark as CircleQuestionMarkIcon }
export { CircleSlash2 as CircleSlash2Icon }
export { CircleSlash as CircleSlashIcon }
export { CircleSlash2 as CircleSlashed }
export { CircleSlash2 as CircleSlashedIcon }
export { CircleSmall as CircleSmallIcon }
export { CircleStar as CircleStarIcon }
export { CircleStop as CircleStopIcon }
export { CircleUser as CircleUserIcon }
export { CircleUserRound as CircleUserRoundIcon }
export { CircleX as CircleXIcon }
export { CircuitBoard as CircuitBoardIcon }
export { Citrus as CitrusIcon }
export { Clapperboard as ClapperboardIcon }
export { ClipboardCheck as ClipboardCheckIcon }
export { ClipboardClock as ClipboardClockIcon }
export { ClipboardCopy as ClipboardCopyIcon }
export { ClipboardPen as ClipboardEdit }
export { ClipboardPen as ClipboardEditIcon }
export { Clipboard as ClipboardIcon }
export { ClipboardList as ClipboardListIcon }
export { ClipboardMinus as ClipboardMinusIcon }
export { ClipboardPaste as ClipboardPasteIcon }
export { ClipboardPen as ClipboardPenIcon }
export { ClipboardPenLine as ClipboardPenLineIcon }
export { ClipboardPlus as ClipboardPlusIcon }
export { ClipboardPenLine as ClipboardSignature }
export { ClipboardPenLine as ClipboardSignatureIcon }
export { ClipboardType as ClipboardTypeIcon }
export { ClipboardX as ClipboardXIcon }
export { Clock10 as Clock10Icon }
export { Clock11 as Clock11Icon }
export { Clock12 as Clock12Icon }
export { Clock1 as Clock1Icon }
export { Clock2 as Clock2Icon }
export { Clock3 as Clock3Icon }
export { Clock4 as Clock4Icon }
export { Clock5 as Clock5Icon }
export { Clock6 as Clock6Icon }
export { Clock7 as Clock7Icon }
export { Clock8 as Clock8Icon }
export { Clock9 as Clock9Icon }
export { ClockAlert as ClockAlertIcon }
export { ClockArrowDown as ClockArrowDownIcon }
export { ClockArrowLeft as ClockArrowLeftIcon }
export { ClockArrowRight as ClockArrowRightIcon }
export { ClockArrowUp as ClockArrowUpIcon }
export { ClockCheck as ClockCheckIcon }
export { ClockFading as ClockFadingIcon }
export { Clock as ClockIcon }
export { ClockPlus as ClockPlusIcon }
export { ClosedCaption as ClosedCaptionIcon }
export { CloudAlert as CloudAlertIcon }
export { CloudBackup as CloudBackupIcon }
export { CloudCheck as CloudCheckIcon }
export { CloudCog as CloudCogIcon }
export { CloudDownload as CloudDownloadIcon }
export { CloudDrizzle as CloudDrizzleIcon }
export { CloudFog as CloudFogIcon }
export { CloudHail as CloudHailIcon }
export { Cloud as CloudIcon }
export { CloudLightning as CloudLightningIcon }
export { CloudMoon as CloudMoonIcon }
export { CloudMoonRain as CloudMoonRainIcon }
export { CloudOff as CloudOffIcon }
export { CloudRain as CloudRainIcon }
export { CloudRainWind as CloudRainWindIcon }
export { CloudSnow as CloudSnowIcon }
export { CloudSun as CloudSunIcon }
export { CloudSunRain as CloudSunRainIcon }
export { CloudSync as CloudSyncIcon }
export { CloudUpload as CloudUploadIcon }
export { Cloudy as CloudyIcon }
export { Clover as CloverIcon }
export { Club as ClubIcon }
export { CodeXml as Code2 }
export { CodeXml as Code2Icon }
export { Code as CodeIcon }
export { SquareCode as CodeSquare }
export { SquareCode as CodeSquareIcon }
export { CodeXml as CodeXmlIcon }
export { Coffee as CoffeeIcon }
export { Cog as CogIcon }
export { Coins as CoinsIcon }
export { Columns2 as Columns }
export { Columns2 as Columns2Icon }
export { Columns3Cog as Columns3CogIcon }
export { Columns3 as Columns3Icon }
export { Columns4 as Columns4Icon }
export { Columns2 as ColumnsIcon }
export { Columns3Cog as ColumnsSettings }
export { Columns3Cog as ColumnsSettingsIcon }
export { Combine as CombineIcon }
export { Command as CommandIcon }
export { Compass as CompassIcon }
export { Component as ComponentIcon }
export { Computer as ComputerIcon }
export { ConciergeBell as ConciergeBellIcon }
export { Cone as ConeIcon }
export { Construction as ConstructionIcon }
export { ContactRound as Contact2 }
export { ContactRound as Contact2Icon }
export { Contact as ContactIcon }
export { ContactRound as ContactRoundIcon }
export { Container as ContainerIcon }
export { Contrast as ContrastIcon }
export { Cookie as CookieIcon }
export { CookingPot as CookingPotIcon }
export { CopyCheck as CopyCheckIcon }
export { Copy as CopyIcon }
export { CopyMinus as CopyMinusIcon }
export { CopyPlus as CopyPlusIcon }
export { CopySlash as CopySlashIcon }
export { CopyX as CopyXIcon }
export { Copyleft as CopyleftIcon }
export { Copyright as CopyrightIcon }
export { CornerDownLeft as CornerDownLeftIcon }
export { CornerDownRight as CornerDownRightIcon }
export { CornerLeftDown as CornerLeftDownIcon }
export { CornerLeftUp as CornerLeftUpIcon }
export { CornerRightDown as CornerRightDownIcon }
export { CornerRightUp as CornerRightUpIcon }
export { CornerUpLeft as CornerUpLeftIcon }
export { CornerUpRight as CornerUpRightIcon }
export { Cpu as CpuIcon }
export { CreativeCommons as CreativeCommonsIcon }
export { CreditCardCheck as CreditCardCheckIcon }
export { CreditCard as CreditCardIcon }
export { CreditCardMinus as CreditCardMinusIcon }
export { CreditCardPlus as CreditCardPlusIcon }
export { CreditCardX as CreditCardXIcon }
export { Croissant as CroissantIcon }
export { Crop as CropIcon }
export { Cross as CrossIcon }
export { Crosshair as CrosshairIcon }
export { Crown as CrownIcon }
export { Cuboid as CuboidIcon }
export { CupSoda as CupSodaIcon }
export { Braces as CurlyBraces }
export { Braces as CurlyBracesIcon }
export { Currency as CurrencyIcon }
export { Cylinder as CylinderIcon }
export { Dam as DamIcon }
export { DatabaseArrowDown as DatabaseArrowDownIcon }
export { DatabaseArrowUp as DatabaseArrowUpIcon }
export { DatabaseBackup as DatabaseBackupIcon }
export { DatabaseCheck as DatabaseCheckIcon }
export { Database as DatabaseIcon }
export { DatabaseMinus as DatabaseMinusIcon }
export { DatabasePlus as DatabasePlusIcon }
export { DatabaseSearch as DatabaseSearchIcon }
export { DatabaseX as DatabaseXIcon }
export { DatabaseZap as DatabaseZapIcon }
export { DecimalsArrowLeft as DecimalsArrowLeftIcon }
export { DecimalsArrowRight as DecimalsArrowRightIcon }
export { Delete as DeleteIcon }
export { Dessert as DessertIcon }
export { Diameter as DiameterIcon }
export { Diamond as DiamondIcon }
export { DiamondMinus as DiamondMinusIcon }
export { DiamondPercent as DiamondPercentIcon }
export { DiamondPlus as DiamondPlusIcon }
export { Dice1 as Dice1Icon }
export { Dice2 as Dice2Icon }
export { Dice3 as Dice3Icon }
export { Dice4 as Dice4Icon }
export { Dice5 as Dice5Icon }
export { Dice6 as Dice6Icon }
export { Dices as DicesIcon }
export { Diff as DiffIcon }
export { Disc2 as Disc2Icon }
export { Disc3 as Disc3Icon }
export { DiscAlbum as DiscAlbumIcon }
export { Disc as DiscIcon }
export { CircleDivide as DivideCircle }
export { CircleDivide as DivideCircleIcon }
export { Divide as DivideIcon }
export { SquareDivide as DivideSquare }
export { SquareDivide as DivideSquareIcon }
export { Dna as DnaIcon }
export { DnaOff as DnaOffIcon }
export { Dock as DockIcon }
export { Dog as DogIcon }
export { DollarSign as DollarSignIcon }
export { Donut as DonutIcon }
export { DoorClosed as DoorClosedIcon }
export { DoorClosedLocked as DoorClosedLockedIcon }
export { DoorOpen as DoorOpenIcon }
export { Dot as DotIcon }
export { SquareDot as DotSquare }
export { SquareDot as DotSquareIcon }
export { CloudDownload as DownloadCloud }
export { CloudDownload as DownloadCloudIcon }
export { Download as DownloadIcon }
export { DraftingCompass as DraftingCompassIcon }
export { Drama as DramaIcon }
export { Drill as DrillIcon }
export { Drone as DroneIcon }
export { Droplet as DropletIcon }
export { DropletOff as DropletOffIcon }
export { Droplets as DropletsIcon }
export { Drum as DrumIcon }
export { Drumstick as DrumstickIcon }
export { Dumbbell as DumbbellIcon }
export { Ear as EarIcon }
export { EarOff as EarOffIcon }
export { Earth as EarthIcon }
export { EarthLock as EarthLockIcon }
export { Eclipse as EclipseIcon }
export { SquarePen as Edit }
export { Pen as Edit2 }
export { Pen as Edit2Icon }
export { PenLine as Edit3 }
export { PenLine as Edit3Icon }
export { SquarePen as EditIcon }
export { EggFried as EggFriedIcon }
export { Egg as EggIcon }
export { EggOff as EggOffIcon }
export { Eject as EjectIcon }
export { Ellipse as EllipseIcon }
export { Ellipsis as EllipsisIcon }
export { EllipsisVertical as EllipsisVerticalIcon }
export { EqualApproximately as EqualApproximatelyIcon }
export { Equal as EqualIcon }
export { EqualNot as EqualNotIcon }
export { SquareEqual as EqualSquare }
export { SquareEqual as EqualSquareIcon }
export { Eraser as EraserIcon }
export { EthernetPort as EthernetPortIcon }
export { Euro as EuroIcon }
export { EvCharger as EvChargerIcon }
export { Expand as ExpandIcon }
export { ExternalLink as ExternalLinkIcon }
export { EyeClosed as EyeClosedIcon }
export { EyeDashed as EyeDashedIcon }
export { Eye as EyeIcon }
export { EyeOff as EyeOffIcon }
export { FaceAngry as FaceAngryIcon }
export { FaceExpressionless as FaceExpressionlessIcon }
export { FaceGrinning as FaceGrinningIcon }
export { FaceNeutral as FaceNeutralIcon }
export { FaceSlightlyFrowning as FaceSlightlyFrowningIcon }
export { FaceSlightlySmiling as FaceSlightlySmilingIcon }
export { FaceSlightlySmilingPlus as FaceSlightlySmilingPlusIcon }
export { Factory as FactoryIcon }
export { Fan as FanIcon }
export { FastForward as FastForwardIcon }
export { Feather as FeatherIcon }
export { Fence as FenceIcon }
export { FerrisWheel as FerrisWheelIcon }
export { FileArchive as FileArchiveIcon }
export { FileHeadphone as FileAudio }
export { FileHeadphone as FileAudio2 }
export { FileHeadphone as FileAudio2Icon }
export { FileHeadphone as FileAudioIcon }
export { FileAxis3d as FileAxis3D }
export { FileAxis3d as FileAxis3DIcon }
export { FileAxis3d as FileAxis3dIcon }
export { FileBadge as FileBadge2 }
export { FileBadge as FileBadge2Icon }
export { FileBadge as FileBadgeIcon }
export { FileChartColumnIncreasing as FileBarChart }
export { FileChartColumn as FileBarChart2 }
export { FileChartColumn as FileBarChart2Icon }
export { FileChartColumnIncreasing as FileBarChartIcon }
export { FileBox as FileBoxIcon }
export { FileBracesCorner as FileBracesCornerIcon }
export { FileBraces as FileBracesIcon }
export { FileChartColumn as FileChartColumnIcon }
export { FileChartColumnIncreasing as FileChartColumnIncreasingIcon }
export { FileChartLine as FileChartLineIcon }
export { FileChartPie as FileChartPieIcon }
export { FileCheckCorner as FileCheck2 }
export { FileCheckCorner as FileCheck2Icon }
export { FileCheckCorner as FileCheckCornerIcon }
export { FileCheck as FileCheckIcon }
export { FileClock as FileClockIcon }
export { FileCodeCorner as FileCode2 }
export { FileCodeCorner as FileCode2Icon }
export { FileCodeCorner as FileCodeCornerIcon }
export { FileCode as FileCodeIcon }
export { FileCog as FileCog2 }
export { FileCog as FileCog2Icon }
export { FileCog as FileCogIcon }
export { FileDiff as FileDiffIcon }
export { FileDigit as FileDigitIcon }
export { FileDown as FileDownIcon }
export { FilePen as FileEdit }
export { FilePen as FileEditIcon }
export { FileExclamationPoint as FileExclamationPointIcon }
export { FileHeadphone as FileHeadphoneIcon }
export { FileHeart as FileHeartIcon }
export { File as FileIcon }
export { FileImage as FileImageIcon }
export { FileInput as FileInputIcon }
export { FileBraces as FileJson }
export { FileBracesCorner as FileJson2 }
export { FileBracesCorner as FileJson2Icon }
export { FileBraces as FileJsonIcon }
export { FileKey as FileKey2 }
export { FileKey as FileKey2Icon }
export { FileKey as FileKeyIcon }
export { FileChartLine as FileLineChart }
export { FileChartLine as FileLineChartIcon }
export { FileLock as FileLock2 }
export { FileLock as FileLock2Icon }
export { FileLock as FileLockIcon }
export { FileMinusCorner as FileMinus2 }
export { FileMinusCorner as FileMinus2Icon }
export { FileMinusCorner as FileMinusCornerIcon }
export { FileMinus as FileMinusIcon }
export { FileMusic as FileMusicIcon }
export { FileOutput as FileOutputIcon }
export { FilePen as FilePenIcon }
export { FilePenLine as FilePenLineIcon }
export { FileChartPie as FilePieChart }
export { FileChartPie as FilePieChartIcon }
export { FilePlay as FilePlayIcon }
export { FilePlusCorner as FilePlus2 }
export { FilePlusCorner as FilePlus2Icon }
export { FilePlusCorner as FilePlusCornerIcon }
export { FilePlus as FilePlusIcon }
export { FileQuestionMark as FileQuestion }
export { FileQuestionMark as FileQuestionIcon }
export { FileQuestionMark as FileQuestionMarkIcon }
export { FileScan as FileScanIcon }
export { FileSearchCorner as FileSearch2 }
export { FileSearchCorner as FileSearch2Icon }
export { FileSearchCorner as FileSearchCornerIcon }
export { FileSearch as FileSearchIcon }
export { FileSignal as FileSignalIcon }
export { FilePenLine as FileSignature }
export { FilePenLine as FileSignatureIcon }
export { FileSliders as FileSlidersIcon }
export { FileSpreadsheet as FileSpreadsheetIcon }
export { FileStack as FileStackIcon }
export { FileSymlink as FileSymlinkIcon }
export { FileTerminal as FileTerminalIcon }
export { FileText as FileTextIcon }
export { FileTypeCorner as FileType2 }
export { FileTypeCorner as FileType2Icon }
export { FileTypeCorner as FileTypeCornerIcon }
export { FileType as FileTypeIcon }
export { FileUp as FileUpIcon }
export { FileUser as FileUserIcon }
export { FilePlay as FileVideo }
export { FileVideoCamera as FileVideo2 }
export { FileVideoCamera as FileVideo2Icon }
export { FileVideoCamera as FileVideoCameraIcon }
export { FilePlay as FileVideoIcon }
export { FileSignal as FileVolume2 }
export { FileSignal as FileVolume2Icon }
export { FileVolume as FileVolumeIcon }
export { FileExclamationPoint as FileWarning }
export { FileExclamationPoint as FileWarningIcon }
export { FileXCorner as FileX2 }
export { FileXCorner as FileX2Icon }
export { FileXCorner as FileXCornerIcon }
export { FileX as FileXIcon }
export { Files as FilesIcon }
export { Film as FilmIcon }
export { Funnel as Filter }
export { Funnel as FilterIcon }
export { FunnelX as FilterX }
export { FunnelX as FilterXIcon }
export { FingerprintPattern as Fingerprint }
export { FingerprintPattern as FingerprintIcon }
export { FingerprintPattern as FingerprintPatternIcon }
export { FireExtinguisher as FireExtinguisherIcon }
export { Fish as FishIcon }
export { FishOff as FishOffIcon }
export { FishSymbol as FishSymbolIcon }
export { FishingHook as FishingHookIcon }
export { FishingRod as FishingRodIcon }
export { Flag as FlagIcon }
export { FlagOff as FlagOffIcon }
export { FlagTriangleLeft as FlagTriangleLeftIcon }
export { FlagTriangleRight as FlagTriangleRightIcon }
export { Flame as FlameIcon }
export { FlameKindling as FlameKindlingIcon }
export { Flashlight as FlashlightIcon }
export { FlashlightOff as FlashlightOffIcon }
export { FlaskConical as FlaskConicalIcon }
export { FlaskConicalOff as FlaskConicalOffIcon }
export { FlaskRound as FlaskRoundIcon }
export { SquareCenterlineDashedHorizontal as FlipHorizontal }
export { FlipHorizontal2 as FlipHorizontal2Icon }
export { SquareCenterlineDashedHorizontal as FlipHorizontalIcon }
export { SquareCenterlineDashedVertical as FlipVertical }
export { FlipVertical2 as FlipVertical2Icon }
export { SquareCenterlineDashedVertical as FlipVerticalIcon }
export { Flower2 as Flower2Icon }
export { Flower as FlowerIcon }
export { Focus as FocusIcon }
export { FoldHorizontal as FoldHorizontalIcon }
export { FoldVertical as FoldVerticalIcon }
export { FolderArchive as FolderArchiveIcon }
export { FolderBookmark as FolderBookmarkIcon }
export { FolderCheck as FolderCheckIcon }
export { FolderClock as FolderClockIcon }
export { FolderClosed as FolderClosedIcon }
export { FolderCode as FolderCodeIcon }
export { FolderCog as FolderCog2 }
export { FolderCog as FolderCog2Icon }
export { FolderCog as FolderCogIcon }
export { FolderDot as FolderDotIcon }
export { FolderDown as FolderDownIcon }
export { FolderPen as FolderEdit }
export { FolderPen as FolderEditIcon }
export { FolderGit2 as FolderGit2Icon }
export { FolderGit as FolderGitIcon }
export { FolderHeart as FolderHeartIcon }
export { Folder as FolderIcon }
export { FolderInput as FolderInputIcon }
export { FolderKanban as FolderKanbanIcon }
export { FolderKey as FolderKeyIcon }
export { FolderLock as FolderLockIcon }
export { FolderMinus as FolderMinusIcon }
export { FolderOpenDot as FolderOpenDotIcon }
export { FolderOpen as FolderOpenIcon }
export { FolderOutput as FolderOutputIcon }
export { FolderPen as FolderPenIcon }
export { FolderPlus as FolderPlusIcon }
export { FolderRoot as FolderRootIcon }
export { FolderSearch2 as FolderSearch2Icon }
export { FolderSearch as FolderSearchIcon }
export { FolderSymlink as FolderSymlinkIcon }
export { FolderSync as FolderSyncIcon }
export { FolderTree as FolderTreeIcon }
export { FolderUp as FolderUpIcon }
export { FolderX as FolderXIcon }
export { Folders as FoldersIcon }
export { Footprints as FootprintsIcon }
export { Utensils as ForkKnife }
export { UtensilsCrossed as ForkKnifeCrossed }
export { UtensilsCrossed as ForkKnifeCrossedIcon }
export { Utensils as ForkKnifeIcon }
export { Forklift as ForkliftIcon }
export { Form as FormIcon }
export { RectangleEllipsis as FormInput }
export { RectangleEllipsis as FormInputIcon }
export { Forward as ForwardIcon }
export { Frame as FrameIcon }
export { FaceSlightlyFrowning as Frown }
export { FaceSlightlyFrowning as FrownIcon }
export { Fuel as FuelIcon }
export { Fullscreen as FullscreenIcon }
export { SquareFunction as FunctionSquare }
export { SquareFunction as FunctionSquareIcon }
export { Funnel as FunnelIcon }
export { FunnelPlus as FunnelPlusIcon }
export { FunnelX as FunnelXIcon }
export { Galaxy as GalaxyIcon }
export { GalleryHorizontalEnd as GalleryHorizontalEndIcon }
export { GalleryHorizontal as GalleryHorizontalIcon }
export { GalleryThumbnails as GalleryThumbnailsIcon }
export { GalleryVerticalEnd as GalleryVerticalEndIcon }
export { GalleryVertical as GalleryVerticalIcon }
export { Gamepad2 as Gamepad2Icon }
export { GamepadDirectional as GamepadDirectionalIcon }
export { Gamepad as GamepadIcon }
export { ChartNoAxesGantt as GanttChart }
export { ChartNoAxesGantt as GanttChartIcon }
export { SquareChartGantt as GanttChartSquare }
export { SquareChartGantt as GanttChartSquareIcon }
export { CircleGauge as GaugeCircle }
export { CircleGauge as GaugeCircleIcon }
export { Gauge as GaugeIcon }
export { Gavel as GavelIcon }
export { Gem as GemIcon }
export { GeorgianLari as GeorgianLariIcon }
export { Ghost as GhostIcon }
export { Gift as GiftIcon }
export { GitBranch as GitBranchIcon }
export { GitBranchMinus as GitBranchMinusIcon }
export { GitBranchPlus as GitBranchPlusIcon }
export { GitCommitHorizontal as GitCommit }
export { GitCommitHorizontal as GitCommitHorizontalIcon }
export { GitCommitHorizontal as GitCommitIcon }
export { GitCommitVertical as GitCommitVerticalIcon }
export { GitCompareArrows as GitCompareArrowsIcon }
export { GitCompare as GitCompareIcon }
export { GitFork as GitForkIcon }
export { GitGraph as GitGraphIcon }
export { GitMergeConflict as GitMergeConflictIcon }
export { GitMerge as GitMergeIcon }
export { GitPullRequestArrow as GitPullRequestArrowIcon }
export { GitPullRequestClosed as GitPullRequestClosedIcon }
export { GitPullRequestCreateArrow as GitPullRequestCreateArrowIcon }
export { GitPullRequestCreate as GitPullRequestCreateIcon }
export { GitPullRequestDraft as GitPullRequestDraftIcon }
export { GitPullRequest as GitPullRequestIcon }
export { GlassWater as GlassWaterIcon }
export { Glasses as GlassesIcon }
export { Earth as Globe2 }
export { Earth as Globe2Icon }
export { GlobeCheck as GlobeCheckIcon }
export { Globe as GlobeIcon }
export { GlobeLock as GlobeLockIcon }
export { GlobeOff as GlobeOffIcon }
export { GlobeX as GlobeXIcon }
export { Goal as GoalIcon }
export { Gpu as GpuIcon }
export { HandGrab as Grab }
export { HandGrab as GrabIcon }
export { GraduationCap as GraduationCapIcon }
export { Grape as GrapeIcon }
export { Grid3x3 as Grid }
export { Grid2x2 as Grid2X2 }
export { Grid2x2Check as Grid2X2Check }
export { Grid2x2Check as Grid2X2CheckIcon }
export { Grid2x2 as Grid2X2Icon }
export { Grid2x2Plus as Grid2X2Plus }
export { Grid2x2Plus as Grid2X2PlusIcon }
export { Grid2x2X as Grid2X2X }
export { Grid2x2X as Grid2X2XIcon }
export { Grid2x2Check as Grid2x2CheckIcon }
export { Grid2x2 as Grid2x2Icon }
export { Grid2x2Plus as Grid2x2PlusIcon }
export { Grid2x2X as Grid2x2XIcon }
export { Grid3x3 as Grid3X3 }
export { Grid3x3 as Grid3X3Icon }
export { Grid3x2 as Grid3x2Icon }
export { Grid3x3 as Grid3x3Icon }
export { Grid3x3 as GridIcon }
export { GripHorizontal as GripHorizontalIcon }
export { Grip as GripIcon }
export { GripVertical as GripVerticalIcon }
export { Group as GroupIcon }
export { Guitar as GuitarIcon }
export { Ham as HamIcon }
export { Hamburger as HamburgerIcon }
export { Hammer as HammerIcon }
export { HandCoins as HandCoinsIcon }
export { HandFist as HandFistIcon }
export { HandGrab as HandGrabIcon }
export { HandHeart as HandHeartIcon }
export { HandHelping as HandHelpingIcon }
export { Hand as HandIcon }
export { HandMetal as HandMetalIcon }
export { HandPlatter as HandPlatterIcon }
export { Handbag as HandbagIcon }
export { Handshake as HandshakeIcon }
export { HardDriveDownload as HardDriveDownloadIcon }
export { HardDrive as HardDriveIcon }
export { HardDriveUpload as HardDriveUploadIcon }
export { HardHat as HardHatIcon }
export { Hash as HashIcon }
export { HatGlasses as HatGlassesIcon }
export { Haze as HazeIcon }
export { Hd as HdIcon }
export { HdmiPort as HdmiPortIcon }
export { Heading1 as Heading1Icon }
export { Heading2 as Heading2Icon }
export { Heading3 as Heading3Icon }
export { Heading4 as Heading4Icon }
export { Heading5 as Heading5Icon }
export { Heading6 as Heading6Icon }
export { Heading as HeadingIcon }
export { HeadphoneOff as HeadphoneOffIcon }
export { Headphones as HeadphonesIcon }
export { Headset as HeadsetIcon }
export { HeartCrack as HeartCrackIcon }
export { HeartHandshake as HeartHandshakeIcon }
export { Heart as HeartIcon }
export { HeartMinus as HeartMinusIcon }
export { HeartOff as HeartOffIcon }
export { HeartPlus as HeartPlusIcon }
export { HeartPulse as HeartPulseIcon }
export { HeartX as HeartXIcon }
export { Heater as HeaterIcon }
export { Helicopter as HelicopterIcon }
export { CircleQuestionMark as HelpCircle }
export { CircleQuestionMark as HelpCircleIcon }
export { HandHelping as HelpingHand }
export { HandHelping as HelpingHandIcon }
export { Hexagon as HexagonIcon }
export { Highlighter as HighlighterIcon }
export { RotateCcwClock as History }
export { RotateCcwClock as HistoryIcon }
export { House as Home }
export { House as HomeIcon }
export { Hop as HopIcon }
export { HopOff as HopOffIcon }
export { Hospital as HospitalIcon }
export { Hotel as HotelIcon }
export { Hourglass as HourglassIcon }
export { HouseHeart as HouseHeartIcon }
export { House as HouseIcon }
export { HousePlug as HousePlugIcon }
export { HousePlus as HousePlusIcon }
export { HouseWifi as HouseWifiIcon }
export { IceCreamCone as IceCream }
export { IceCreamBowl as IceCream2 }
export { IceCreamBowl as IceCream2Icon }
export { IceCreamBowl as IceCreamBowlIcon }
export { IceCreamCone as IceCreamConeIcon }
export { IceCreamCone as IceCreamIcon }
export { IdCard as IdCardIcon }
export { IdCardLanyard as IdCardLanyardIcon }
export { ImageDown as ImageDownIcon }
export { Image as ImageIcon }
export { ImageMinus as ImageMinusIcon }
export { ImageOff as ImageOffIcon }
export { ImagePlay as ImagePlayIcon }
export { ImagePlus as ImagePlusIcon }
export { ImageUp as ImageUpIcon }
export { ImageUpscale as ImageUpscaleIcon }
export { Images as ImagesIcon }
export { Import as ImportIcon }
export { Inbox as InboxIcon }
export { ListIndentIncrease as Indent }
export { ListIndentDecrease as IndentDecrease }
export { ListIndentDecrease as IndentDecreaseIcon }
export { ListIndentIncrease as IndentIcon }
export { ListIndentIncrease as IndentIncrease }
export { ListIndentIncrease as IndentIncreaseIcon }
export { IndianRupee as IndianRupeeIcon }
export { Infinity as InfinityIcon }
export { Info as InfoIcon }
export { SquareMousePointer as Inspect }
export { SquareMousePointer as InspectIcon }
export { InspectionPanel as InspectionPanelIcon }
export { Italic as ItalicIcon }
export { IterationCcw as IterationCcwIcon }
export { IterationCw as IterationCwIcon }
export { JapaneseYen as JapaneseYenIcon }
export { Joystick as JoystickIcon }
export { Kanban as KanbanIcon }
export { SquareKanban as KanbanSquare }
export { SquareDashedKanban as KanbanSquareDashed }
export { SquareDashedKanban as KanbanSquareDashedIcon }
export { SquareKanban as KanbanSquareIcon }
export { Kayak as KayakIcon }
export { Key as KeyIcon }
export { KeyRound as KeyRoundIcon }
export { KeySquare as KeySquareIcon }
export { Keyboard as KeyboardIcon }
export { KeyboardMusic as KeyboardMusicIcon }
export { KeyboardOff as KeyboardOffIcon }
export { LampCeiling as LampCeilingIcon }
export { LampDesk as LampDeskIcon }
export { LampFloor as LampFloorIcon }
export { Lamp as LampIcon }
export { LampWallDown as LampWallDownIcon }
export { LampWallUp as LampWallUpIcon }
export { LandPlot as LandPlotIcon }
export { Landmark as LandmarkIcon }
export { Languages as LanguagesIcon }
export { LaptopMinimal as Laptop2 }
export { LaptopMinimal as Laptop2Icon }
export { Laptop as LaptopIcon }
export { LaptopMinimalCheck as LaptopMinimalCheckIcon }
export { LaptopMinimal as LaptopMinimalIcon }
export { Lasso as LassoIcon }
export { LassoSelect as LassoSelectIcon }
export { FaceGrinning as Laugh }
export { FaceGrinning as LaughIcon }
export { LayerArrowDown as LayerArrowDownIcon }
export { LayerArrowUp as LayerArrowUpIcon }
export { Layers2 as Layers2Icon }
export { Layers as Layers3 }
export { Layers as Layers3Icon }
export { LayersArrowDown as LayersArrowDownIcon }
export { LayersArrowUp as LayersArrowUpIcon }
export { Layers as LayersIcon }
export { LayersMinus as LayersMinusIcon }
export { LayersPlus as LayersPlusIcon }
export { PanelsTopLeft as Layout }
export { LayoutDashboard as LayoutDashboardIcon }
export { LayoutFreeform as LayoutFreeformIcon }
export { LayoutGrid as LayoutGridIcon }
export { PanelsTopLeft as LayoutIcon }
export { LayoutList as LayoutListIcon }
export { LayoutPanelLeft as LayoutPanelLeftIcon }
export { LayoutPanelTop as LayoutPanelTopIcon }
export { LayoutTemplate as LayoutTemplateIcon }
export { Leaf as LeafIcon }
export { LeafyGreen as LeafyGreenIcon }
export { Lectern as LecternIcon }
export { LensConcave as LensConcaveIcon }
export { LensConvex as LensConvexIcon }
export { TextInitial as LetterText }
export { TextInitial as LetterTextIcon }
export { LibraryBig as LibraryBigIcon }
export { Library as LibraryIcon }
export { SquareLibrary as LibrarySquare }
export { SquareLibrary as LibrarySquareIcon }
export { LifeBuoy as LifeBuoyIcon }
export { Ligature as LigatureIcon }
export { Lightbulb as LightbulbIcon }
export { LightbulbOff as LightbulbOffIcon }
export { ChartLine as LineChart }
export { ChartLine as LineChartIcon }
export { LineDotRightHorizontal as LineDotRightHorizontalIcon }
export { LineSquiggle as LineSquiggleIcon }
export { LineStyle as LineStyleIcon }
export { Link2 as Link2Icon }
export { Link2Off as Link2OffIcon }
export { Link as LinkIcon }
export { ListCheck as ListCheckIcon }
export { ListChecks as ListChecksIcon }
export { ListChevronsDownUp as ListChevronsDownUpIcon }
export { ListChevronsUpDown as ListChevronsUpDownIcon }
export { ListClock as ListClockIcon }
export { ListCollapse as ListCollapseIcon }
export { ListEnd as ListEndIcon }
export { ListFilter as ListFilterIcon }
export { ListFilterPlus as ListFilterPlusIcon }
export { List as ListIcon }
export { ListIndentDecrease as ListIndentDecreaseIcon }
export { ListIndentIncrease as ListIndentIncreaseIcon }
export { ListMinus as ListMinusIcon }
export { ListMusic as ListMusicIcon }
export { ListOrdered as ListOrderedIcon }
export { ListPlus as ListPlusIcon }
export { ListRestart as ListRestartIcon }
export { ListSortAscending as ListSortAscendingIcon }
export { ListSortDescending as ListSortDescendingIcon }
export { ListStart as ListStartIcon }
export { ListTodo as ListTodoIcon }
export { ListTree as ListTreeIcon }
export { ListVideo as ListVideoIcon }
export { ListX as ListXIcon }
export { LoaderCircle as Loader2 }
export { LoaderCircle as Loader2Icon }
export { LoaderCircle as LoaderCircleIcon }
export { Loader as LoaderIcon }
export { LoaderPinwheel as LoaderPinwheelIcon }
export { LocateFixed as LocateFixedIcon }
export { Locate as LocateIcon }
export { LocateOff as LocateOffIcon }
export { MapPinPen as LocationEdit }
export { MapPinPen as LocationEditIcon }
export { Lock as LockIcon }
export { LockKeyhole as LockKeyholeIcon }
export { LockKeyholeOpen as LockKeyholeOpenIcon }
export { LockOpen as LockOpenIcon }
export { LogIn as LogInIcon }
export { LogOut as LogOutIcon }
export { Logs as LogsIcon }
export { Lollipop as LollipopIcon }
export { AArrowDown as LucideAArrowDown }
export { AArrowUp as LucideAArrowUp }
export { ALargeSmall as LucideALargeSmall }
export { Accessibility as LucideAccessibility }
export { Activity as LucideActivity }
export { SquareActivity as LucideActivitySquare }
export { Ad as LucideAd }
export { AirVent as LucideAirVent }
export { Airplay as LucideAirplay }
export { AlarmClockCheck as LucideAlarmCheck }
export { AlarmClock as LucideAlarmClock }
export { AlarmClockCheck as LucideAlarmClockCheck }
export { AlarmClockMinus as LucideAlarmClockMinus }
export { AlarmClockOff as LucideAlarmClockOff }
export { AlarmClockPlus as LucideAlarmClockPlus }
export { AlarmClockMinus as LucideAlarmMinus }
export { AlarmClockPlus as LucideAlarmPlus }
export { AlarmSmoke as LucideAlarmSmoke }
export { Album as LucideAlbum }
export { CircleAlert as LucideAlertCircle }
export { OctagonAlert as LucideAlertOctagon }
export { TriangleAlert as LucideAlertTriangle }
export { TextAlignCenter as LucideAlignCenter }
export { AlignCenterHorizontal as LucideAlignCenterHorizontal }
export { AlignCenterVertical as LucideAlignCenterVertical }
export { AlignEndHorizontal as LucideAlignEndHorizontal }
export { AlignEndVertical as LucideAlignEndVertical }
export { AlignHorizontalDistributeCenter as LucideAlignHorizontalDistributeCenter }
export { AlignHorizontalDistributeEnd as LucideAlignHorizontalDistributeEnd }
export { AlignHorizontalDistributeStart as LucideAlignHorizontalDistributeStart }
export { AlignHorizontalJustifyCenter as LucideAlignHorizontalJustifyCenter }
export { AlignHorizontalJustifyEnd as LucideAlignHorizontalJustifyEnd }
export { AlignHorizontalJustifyStart as LucideAlignHorizontalJustifyStart }
export { AlignHorizontalSpaceAround as LucideAlignHorizontalSpaceAround }
export { AlignHorizontalSpaceBetween as LucideAlignHorizontalSpaceBetween }
export { TextAlignJustify as LucideAlignJustify }
export { TextAlignStart as LucideAlignLeft }
export { TextAlignEnd as LucideAlignRight }
export { AlignStartHorizontal as LucideAlignStartHorizontal }
export { AlignStartVertical as LucideAlignStartVertical }
export { AlignVerticalDistributeCenter as LucideAlignVerticalDistributeCenter }
export { AlignVerticalDistributeEnd as LucideAlignVerticalDistributeEnd }
export { AlignVerticalDistributeStart as LucideAlignVerticalDistributeStart }
export { AlignVerticalJustifyCenter as LucideAlignVerticalJustifyCenter }
export { AlignVerticalJustifyEnd as LucideAlignVerticalJustifyEnd }
export { AlignVerticalJustifyStart as LucideAlignVerticalJustifyStart }
export { AlignVerticalSpaceAround as LucideAlignVerticalSpaceAround }
export { AlignVerticalSpaceBetween as LucideAlignVerticalSpaceBetween }
export { Ambulance as LucideAmbulance }
export { Ampersand as LucideAmpersand }
export { Ampersands as LucideAmpersands }
export { Amphora as LucideAmphora }
export { Anchor as LucideAnchor }
export { Angle as LucideAngle }
export { FaceAngry as LucideAngry }
export { FaceExpressionless as LucideAnnoyed }
export { Antenna as LucideAntenna }
export { Anvil as LucideAnvil }
export { Aperture as LucideAperture }
export { AppWindow as LucideAppWindow }
export { AppWindowMac as LucideAppWindowMac }
export { Apple as LucideApple }
export { Archive as LucideArchive }
export { ArchiveRestore as LucideArchiveRestore }
export { ArchiveX as LucideArchiveX }
export { ChartArea as LucideAreaChart }
export { Armchair as LucideArmchair }
export { ArrowBigDown as LucideArrowBigDown }
export { ArrowBigDownDash as LucideArrowBigDownDash }
export { ArrowBigLeft as LucideArrowBigLeft }
export { ArrowBigLeftDash as LucideArrowBigLeftDash }
export { ArrowBigRight as LucideArrowBigRight }
export { ArrowBigRightDash as LucideArrowBigRightDash }
export { ArrowBigUp as LucideArrowBigUp }
export { ArrowBigUpDash as LucideArrowBigUpDash }
export { ArrowDown as LucideArrowDown }
export { ArrowDown01 as LucideArrowDown01 }
export { ArrowDown10 as LucideArrowDown10 }
export { ArrowDownAZ as LucideArrowDownAZ }
export { ArrowDownAZ as LucideArrowDownAz }
export { CircleArrowDown as LucideArrowDownCircle }
export { ArrowDownFromLine as LucideArrowDownFromLine }
export { ArrowDownLeft as LucideArrowDownLeft }
export { CircleArrowOutDownLeft as LucideArrowDownLeftFromCircle }
export { SquareArrowOutDownLeft as LucideArrowDownLeftFromSquare }
export { SquareArrowDownLeft as LucideArrowDownLeftSquare }
export { ArrowDownNarrowWide as LucideArrowDownNarrowWide }
export { ArrowDownRight as LucideArrowDownRight }
export { CircleArrowOutDownRight as LucideArrowDownRightFromCircle }
export { SquareArrowOutDownRight as LucideArrowDownRightFromSquare }
export { SquareArrowDownRight as LucideArrowDownRightSquare }
export { SquareArrowDown as LucideArrowDownSquare }
export { ArrowDownToDot as LucideArrowDownToDot }
export { ArrowDownToLine as LucideArrowDownToLine }
export { ArrowDownUp as LucideArrowDownUp }
export { ArrowDownWideNarrow as LucideArrowDownWideNarrow }
export { ArrowDownZA as LucideArrowDownZA }
export { ArrowDownZA as LucideArrowDownZa }
export { ArrowLeft as LucideArrowLeft }
export { CircleArrowLeft as LucideArrowLeftCircle }
export { ArrowLeftFromLine as LucideArrowLeftFromLine }
export { ArrowLeftRight as LucideArrowLeftRight }
export { SquareArrowLeft as LucideArrowLeftSquare }
export { ArrowLeftToLine as LucideArrowLeftToLine }
export { ArrowRight as LucideArrowRight }
export { CircleArrowRight as LucideArrowRightCircle }
export { ArrowRightFromLine as LucideArrowRightFromLine }
export { ArrowRightLeft as LucideArrowRightLeft }
export { SquareArrowRight as LucideArrowRightSquare }
export { ArrowRightToLine as LucideArrowRightToLine }
export { ArrowUp as LucideArrowUp }
export { ArrowUp01 as LucideArrowUp01 }
export { ArrowUp10 as LucideArrowUp10 }
export { ArrowUpAZ as LucideArrowUpAZ }
export { ArrowUpAZ as LucideArrowUpAz }
export { CircleArrowUp as LucideArrowUpCircle }
export { ArrowUpDown as LucideArrowUpDown }
export { ArrowUpFromDot as LucideArrowUpFromDot }
export { ArrowUpFromLine as LucideArrowUpFromLine }
export { ArrowUpLeft as LucideArrowUpLeft }
export { CircleArrowOutUpLeft as LucideArrowUpLeftFromCircle }
export { SquareArrowOutUpLeft as LucideArrowUpLeftFromSquare }
export { SquareArrowUpLeft as LucideArrowUpLeftSquare }
export { ArrowUpNarrowWide as LucideArrowUpNarrowWide }
export { ArrowUpRight as LucideArrowUpRight }
export { CircleArrowOutUpRight as LucideArrowUpRightFromCircle }
export { SquareArrowOutUpRight as LucideArrowUpRightFromSquare }
export { SquareArrowUpRight as LucideArrowUpRightSquare }
export { SquareArrowUp as LucideArrowUpSquare }
export { ArrowUpToLine as LucideArrowUpToLine }
export { ArrowUpWideNarrow as LucideArrowUpWideNarrow }
export { ArrowUpZA as LucideArrowUpZA }
export { ArrowUpZA as LucideArrowUpZa }
export { ArrowsUpFromLine as LucideArrowsUpFromLine }
export { Asterisk as LucideAsterisk }
export { SquareAsterisk as LucideAsteriskSquare }
export { Astroid as LucideAstroid }
export { AtSign as LucideAtSign }
export { Atom as LucideAtom }
export { AudioLines as LucideAudioLines }
export { AudioLinesOff as LucideAudioLinesOff }
export { AudioLinesX as LucideAudioLinesX }
export { AudioWaveform as LucideAudioWaveform }
export { Award as LucideAward }
export { Axe as LucideAxe }
export { Axis3d as LucideAxis3D }
export { Axis3d as LucideAxis3d }
export { Baby as LucideBaby }
export { Backpack as LucideBackpack }
export { Badge as LucideBadge }
export { BadgeAlert as LucideBadgeAlert }
export { BadgeCent as LucideBadgeCent }
export { BadgeCheck as LucideBadgeCheck }
export { BadgeDollarSign as LucideBadgeDollarSign }
export { BadgeEuro as LucideBadgeEuro }
export { BadgeQuestionMark as LucideBadgeHelp }
export { BadgeIndianRupee as LucideBadgeIndianRupee }
export { BadgeInfo as LucideBadgeInfo }
export { BadgeJapaneseYen as LucideBadgeJapaneseYen }
export { BadgeMinus as LucideBadgeMinus }
export { BadgePercent as LucideBadgePercent }
export { BadgePlus as LucideBadgePlus }
export { BadgePoundSterling as LucideBadgePoundSterling }
export { BadgeQuestionMark as LucideBadgeQuestionMark }
export { BadgeRussianRuble as LucideBadgeRussianRuble }
export { BadgeSwissFranc as LucideBadgeSwissFranc }
export { BadgeTurkishLira as LucideBadgeTurkishLira }
export { BadgeX as LucideBadgeX }
export { BaggageClaim as LucideBaggageClaim }
export { Balloon as LucideBalloon }
export { Ban as LucideBan }
export { Banana as LucideBanana }
export { Bandage as LucideBandage }
export { Banknote as LucideBanknote }
export { BanknoteArrowDown as LucideBanknoteArrowDown }
export { BanknoteArrowUp as LucideBanknoteArrowUp }
export { BanknoteCheck as LucideBanknoteCheck }
export { BanknoteX as LucideBanknoteX }
export { ChartNoAxesColumnIncreasing as LucideBarChart }
export { ChartNoAxesColumn as LucideBarChart2 }
export { ChartColumn as LucideBarChart3 }
export { ChartColumnIncreasing as LucideBarChart4 }
export { ChartColumnBig as LucideBarChartBig }
export { ChartBar as LucideBarChartHorizontal }
export { ChartBarBig as LucideBarChartHorizontalBig }
export { Barcode as LucideBarcode }
export { Barrel as LucideBarrel }
export { Baseline as LucideBaseline }
export { Bath as LucideBath }
export { Battery as LucideBattery }
export { BatteryCharging as LucideBatteryCharging }
export { BatteryFull as LucideBatteryFull }
export { BatteryLow as LucideBatteryLow }
export { BatteryMedium as LucideBatteryMedium }
export { BatteryPlus as LucideBatteryPlus }
export { BatteryWarning as LucideBatteryWarning }
export { Beaker as LucideBeaker }
export { Bean as LucideBean }
export { BeanOff as LucideBeanOff }
export { Bed as LucideBed }
export { BedDouble as LucideBedDouble }
export { BedSingle as LucideBedSingle }
export { Beef as LucideBeef }
export { BeefOff as LucideBeefOff }
export { Beer as LucideBeer }
export { BeerOff as LucideBeerOff }
export { Bell as LucideBell }
export { BellCheck as LucideBellCheck }
export { BellDot as LucideBellDot }
export { BellElectric as LucideBellElectric }
export { BellMinus as LucideBellMinus }
export { BellOff as LucideBellOff }
export { BellPlus as LucideBellPlus }
export { BellRing as LucideBellRing }
export { BetweenHorizontalEnd as LucideBetweenHorizonalEnd }
export { BetweenHorizontalStart as LucideBetweenHorizonalStart }
export { BetweenHorizontalEnd as LucideBetweenHorizontalEnd }
export { BetweenHorizontalStart as LucideBetweenHorizontalStart }
export { BetweenVerticalEnd as LucideBetweenVerticalEnd }
export { BetweenVerticalStart as LucideBetweenVerticalStart }
export { BicepsFlexed as LucideBicepsFlexed }
export { Bike as LucideBike }
export { Binary as LucideBinary }
export { Binoculars as LucideBinoculars }
export { Biohazard as LucideBiohazard }
export { Bird as LucideBird }
export { Birdhouse as LucideBirdhouse }
export { Bitcoin as LucideBitcoin }
export { Blend as LucideBlend }
export { Blender as LucideBlender }
export { Blinds as LucideBlinds }
export { Blocks as LucideBlocks }
export { Bluetooth as LucideBluetooth }
export { BluetoothConnected as LucideBluetoothConnected }
export { BluetoothOff as LucideBluetoothOff }
export { BluetoothSearching as LucideBluetoothSearching }
export { Bold as LucideBold }
export { Bolt as LucideBolt }
export { Bomb as LucideBomb }
export { Bone as LucideBone }
export { BoneFracture as LucideBoneFracture }
export { Book as LucideBook }
export { BookA as LucideBookA }
export { BookAlert as LucideBookAlert }
export { BookAudio as LucideBookAudio }
export { BookCheck as LucideBookCheck }
export { BookCopy as LucideBookCopy }
export { BookDashed as LucideBookDashed }
export { BookDown as LucideBookDown }
export { BookHeadphones as LucideBookHeadphones }
export { BookHeart as LucideBookHeart }
export { BookImage as LucideBookImage }
export { BookKey as LucideBookKey }
export { BookLock as LucideBookLock }
export { BookMarked as LucideBookMarked }
export { BookMinus as LucideBookMinus }
export { BookOpen as LucideBookOpen }
export { BookOpenCheck as LucideBookOpenCheck }
export { BookOpenText as LucideBookOpenText }
export { BookPlus as LucideBookPlus }
export { BookSearch as LucideBookSearch }
export { BookDashed as LucideBookTemplate }
export { BookText as LucideBookText }
export { BookType as LucideBookType }
export { BookUp as LucideBookUp }
export { BookUp2 as LucideBookUp2 }
export { BookUser as LucideBookUser }
export { BookX as LucideBookX }
export { Bookmark as LucideBookmark }
export { BookmarkCheck as LucideBookmarkCheck }
export { BookmarkMinus as LucideBookmarkMinus }
export { BookmarkOff as LucideBookmarkOff }
export { BookmarkPlus as LucideBookmarkPlus }
export { BookmarkX as LucideBookmarkX }
export { BoomBox as LucideBoomBox }
export { Bot as LucideBot }
export { BotMessageSquare as LucideBotMessageSquare }
export { BotOff as LucideBotOff }
export { BottleWine as LucideBottleWine }
export { BowArrow as LucideBowArrow }
export { Box as LucideBox }
export { SquareDashed as LucideBoxSelect }
export { Boxes as LucideBoxes }
export { Braces as LucideBraces }
export { Brackets as LucideBrackets }
export { Brain as LucideBrain }
export { BrainCircuit as LucideBrainCircuit }
export { BrainCog as LucideBrainCog }
export { BrickWall as LucideBrickWall }
export { BrickWallFire as LucideBrickWallFire }
export { BrickWallShield as LucideBrickWallShield }
export { Briefcase as LucideBriefcase }
export { BriefcaseBusiness as LucideBriefcaseBusiness }
export { BriefcaseConveyorBelt as LucideBriefcaseConveyorBelt }
export { BriefcaseMedical as LucideBriefcaseMedical }
export { BringToFront as LucideBringToFront }
export { Broccoli as LucideBroccoli }
export { Broom as LucideBroom }
export { BroomSparkles as LucideBroomSparkles }
export { Brush as LucideBrush }
export { BrushCleaning as LucideBrushCleaning }
export { Bubbles as LucideBubbles }
export { Bug as LucideBug }
export { BugOff as LucideBugOff }
export { BugPlay as LucideBugPlay }
export { Building as LucideBuilding }
export { Building2 as LucideBuilding2 }
export { Bus as LucideBus }
export { BusFront as LucideBusFront }
export { Cable as LucideCable }
export { CableCar as LucideCableCar }
export { Cake as LucideCake }
export { CakeSlice as LucideCakeSlice }
export { Calculator as LucideCalculator }
export { Calendar as LucideCalendar }
export { Calendar1 as LucideCalendar1 }
export { CalendarArrowDown as LucideCalendarArrowDown }
export { CalendarArrowUp as LucideCalendarArrowUp }
export { CalendarCheck as LucideCalendarCheck }
export { CalendarCheck2 as LucideCalendarCheck2 }
export { CalendarClock as LucideCalendarClock }
export { CalendarCog as LucideCalendarCog }
export { CalendarDays as LucideCalendarDays }
export { CalendarFold as LucideCalendarFold }
export { CalendarHeart as LucideCalendarHeart }
export { CalendarMinus as LucideCalendarMinus }
export { CalendarMinus2 as LucideCalendarMinus2 }
export { CalendarOff as LucideCalendarOff }
export { CalendarPlus as LucideCalendarPlus }
export { CalendarPlus2 as LucideCalendarPlus2 }
export { CalendarRange as LucideCalendarRange }
export { CalendarSearch as LucideCalendarSearch }
export { CalendarSync as LucideCalendarSync }
export { CalendarX as LucideCalendarX }
export { CalendarX2 as LucideCalendarX2 }
export { Calendars as LucideCalendars }
export { Camera as LucideCamera }
export { CameraOff as LucideCameraOff }
export { ChartCandlestick as LucideCandlestickChart }
export { Candy as LucideCandy }
export { CandyCane as LucideCandyCane }
export { CandyOff as LucideCandyOff }
export { Cannabis as LucideCannabis }
export { CannabisOff as LucideCannabisOff }
export { Captions as LucideCaptions }
export { CaptionsOff as LucideCaptionsOff }
export { Car as LucideCar }
export { CarBattery as LucideCarBattery }
export { CarFront as LucideCarFront }
export { CarTaxiFront as LucideCarTaxiFront }
export { Caravan as LucideCaravan }
export { CardSim as LucideCardSim }
export { Carrot as LucideCarrot }
export { CaseLower as LucideCaseLower }
export { CaseSensitive as LucideCaseSensitive }
export { CaseUpper as LucideCaseUpper }
export { CassetteTape as LucideCassetteTape }
export { Cast as LucideCast }
export { Castle as LucideCastle }
export { Cat as LucideCat }
export { Cctv as LucideCctv }
export { CctvOff as LucideCctvOff }
export { ChartArea as LucideChartArea }
export { ChartBar as LucideChartBar }
export { ChartBarBig as LucideChartBarBig }
export { ChartBarDecreasing as LucideChartBarDecreasing }
export { ChartBarIncreasing as LucideChartBarIncreasing }
export { ChartBarStacked as LucideChartBarStacked }
export { ChartCandlestick as LucideChartCandlestick }
export { ChartColumn as LucideChartColumn }
export { ChartColumnBig as LucideChartColumnBig }
export { ChartColumnDecreasing as LucideChartColumnDecreasing }
export { ChartColumnIncreasing as LucideChartColumnIncreasing }
export { ChartColumnStacked as LucideChartColumnStacked }
export { ChartGantt as LucideChartGantt }
export { ChartLine as LucideChartLine }
export { ChartNetwork as LucideChartNetwork }
export { ChartNoAxesColumn as LucideChartNoAxesColumn }
export { ChartNoAxesColumnDecreasing as LucideChartNoAxesColumnDecreasing }
export { ChartNoAxesColumnIncreasing as LucideChartNoAxesColumnIncreasing }
export { ChartNoAxesCombined as LucideChartNoAxesCombined }
export { ChartNoAxesGantt as LucideChartNoAxesGantt }
export { ChartPie as LucideChartPie }
export { ChartScatter as LucideChartScatter }
export { ChartSpline as LucideChartSpline }
export { Check as LucideCheck }
export { CheckCheck as LucideCheckCheck }
export { CircleCheckBig as LucideCheckCircle }
export { CircleCheck as LucideCheckCircle2 }
export { CheckLine as LucideCheckLine }
export { SquareCheckBig as LucideCheckSquare }
export { SquareCheck as LucideCheckSquare2 }
export { ChefHat as LucideChefHat }
export { Cherry as LucideCherry }
export { ChessBishop as LucideChessBishop }
export { ChessKing as LucideChessKing }
export { ChessKnight as LucideChessKnight }
export { ChessPawn as LucideChessPawn }
export { ChessQueen as LucideChessQueen }
export { ChessRook as LucideChessRook }
export { ChevronDown as LucideChevronDown }
export { CircleChevronDown as LucideChevronDownCircle }
export { SquareChevronDown as LucideChevronDownSquare }
export { ChevronFirst as LucideChevronFirst }
export { ChevronLast as LucideChevronLast }
export { ChevronLeft as LucideChevronLeft }
export { CircleChevronLeft as LucideChevronLeftCircle }
export { SquareChevronLeft as LucideChevronLeftSquare }
export { ChevronRight as LucideChevronRight }
export { CircleChevronRight as LucideChevronRightCircle }
export { SquareChevronRight as LucideChevronRightSquare }
export { ChevronUp as LucideChevronUp }
export { CircleChevronUp as LucideChevronUpCircle }
export { SquareChevronUp as LucideChevronUpSquare }
export { ChevronsDown as LucideChevronsDown }
export { ChevronsDownUp as LucideChevronsDownUp }
export { ChevronsLeft as LucideChevronsLeft }
export { ChevronsLeftRight as LucideChevronsLeftRight }
export { ChevronsLeftRightEllipsis as LucideChevronsLeftRightEllipsis }
export { ChevronsRight as LucideChevronsRight }
export { ChevronsRightLeft as LucideChevronsRightLeft }
export { ChevronsUp as LucideChevronsUp }
export { ChevronsUpDown as LucideChevronsUpDown }
export { Church as LucideChurch }
export { Cigarette as LucideCigarette }
export { CigaretteOff as LucideCigaretteOff }
export { Circle as LucideCircle }
export { CircleAlert as LucideCircleAlert }
export { CircleArrowDown as LucideCircleArrowDown }
export { CircleArrowLeft as LucideCircleArrowLeft }
export { CircleArrowOutDownLeft as LucideCircleArrowOutDownLeft }
export { CircleArrowOutDownRight as LucideCircleArrowOutDownRight }
export { CircleArrowOutUpLeft as LucideCircleArrowOutUpLeft }
export { CircleArrowOutUpRight as LucideCircleArrowOutUpRight }
export { CircleArrowRight as LucideCircleArrowRight }
export { CircleArrowUp as LucideCircleArrowUp }
export { CircleCheck as LucideCircleCheck }
export { CircleCheckBig as LucideCircleCheckBig }
export { CircleChevronDown as LucideCircleChevronDown }
export { CircleChevronLeft as LucideCircleChevronLeft }
export { CircleChevronRight as LucideCircleChevronRight }
export { CircleChevronUp as LucideCircleChevronUp }
export { CircleDashed as LucideCircleDashed }
export { CircleDivide as LucideCircleDivide }
export { CircleDollarSign as LucideCircleDollarSign }
export { CircleDot as LucideCircleDot }
export { CircleDotDashed as LucideCircleDotDashed }
export { CircleEllipsis as LucideCircleEllipsis }
export { CircleEqual as LucideCircleEqual }
export { CircleEuro as LucideCircleEuro }
export { CircleFadingArrowUp as LucideCircleFadingArrowUp }
export { CircleFadingPlus as LucideCircleFadingPlus }
export { CircleGauge as LucideCircleGauge }
export { CircleQuestionMark as LucideCircleHelp }
export { CircleMinus as LucideCircleMinus }
export { CircleOff as LucideCircleOff }
export { CircleParking as LucideCircleParking }
export { CircleParkingOff as LucideCircleParkingOff }
export { CirclePause as LucideCirclePause }
export { CirclePercent as LucideCirclePercent }
export { CirclePile as LucideCirclePile }
export { CirclePlay as LucideCirclePlay }
export { CirclePlus as LucideCirclePlus }
export { CirclePoundSterling as LucideCirclePoundSterling }
export { CirclePower as LucideCirclePower }
export { CircleQuestionMark as LucideCircleQuestionMark }
export { CircleSlash as LucideCircleSlash }
export { CircleSlash2 as LucideCircleSlash2 }
export { CircleSlash2 as LucideCircleSlashed }
export { CircleSmall as LucideCircleSmall }
export { CircleStar as LucideCircleStar }
export { CircleStop as LucideCircleStop }
export { CircleUser as LucideCircleUser }
export { CircleUserRound as LucideCircleUserRound }
export { CircleX as LucideCircleX }
export { CircuitBoard as LucideCircuitBoard }
export { Citrus as LucideCitrus }
export { Clapperboard as LucideClapperboard }
export { Clipboard as LucideClipboard }
export { ClipboardCheck as LucideClipboardCheck }
export { ClipboardClock as LucideClipboardClock }
export { ClipboardCopy as LucideClipboardCopy }
export { ClipboardPen as LucideClipboardEdit }
export { ClipboardList as LucideClipboardList }
export { ClipboardMinus as LucideClipboardMinus }
export { ClipboardPaste as LucideClipboardPaste }
export { ClipboardPen as LucideClipboardPen }
export { ClipboardPenLine as LucideClipboardPenLine }
export { ClipboardPlus as LucideClipboardPlus }
export { ClipboardPenLine as LucideClipboardSignature }
export { ClipboardType as LucideClipboardType }
export { ClipboardX as LucideClipboardX }
export { Clock as LucideClock }
export { Clock1 as LucideClock1 }
export { Clock10 as LucideClock10 }
export { Clock11 as LucideClock11 }
export { Clock12 as LucideClock12 }
export { Clock2 as LucideClock2 }
export { Clock3 as LucideClock3 }
export { Clock4 as LucideClock4 }
export { Clock5 as LucideClock5 }
export { Clock6 as LucideClock6 }
export { Clock7 as LucideClock7 }
export { Clock8 as LucideClock8 }
export { Clock9 as LucideClock9 }
export { ClockAlert as LucideClockAlert }
export { ClockArrowDown as LucideClockArrowDown }
export { ClockArrowLeft as LucideClockArrowLeft }
export { ClockArrowRight as LucideClockArrowRight }
export { ClockArrowUp as LucideClockArrowUp }
export { ClockCheck as LucideClockCheck }
export { ClockFading as LucideClockFading }
export { ClockPlus as LucideClockPlus }
export { ClosedCaption as LucideClosedCaption }
export { Cloud as LucideCloud }
export { CloudAlert as LucideCloudAlert }
export { CloudBackup as LucideCloudBackup }
export { CloudCheck as LucideCloudCheck }
export { CloudCog as LucideCloudCog }
export { CloudDownload as LucideCloudDownload }
export { CloudDrizzle as LucideCloudDrizzle }
export { CloudFog as LucideCloudFog }
export { CloudHail as LucideCloudHail }
export { CloudLightning as LucideCloudLightning }
export { CloudMoon as LucideCloudMoon }
export { CloudMoonRain as LucideCloudMoonRain }
export { CloudOff as LucideCloudOff }
export { CloudRain as LucideCloudRain }
export { CloudRainWind as LucideCloudRainWind }
export { CloudSnow as LucideCloudSnow }
export { CloudSun as LucideCloudSun }
export { CloudSunRain as LucideCloudSunRain }
export { CloudSync as LucideCloudSync }
export { CloudUpload as LucideCloudUpload }
export { Cloudy as LucideCloudy }
export { Clover as LucideClover }
export { Club as LucideClub }
export { Code as LucideCode }
export { CodeXml as LucideCode2 }
export { SquareCode as LucideCodeSquare }
export { CodeXml as LucideCodeXml }
export { Coffee as LucideCoffee }
export { Cog as LucideCog }
export { Coins as LucideCoins }
export { Columns2 as LucideColumns }
export { Columns2 as LucideColumns2 }
export { Columns3 as LucideColumns3 }
export { Columns3Cog as LucideColumns3Cog }
export { Columns4 as LucideColumns4 }
export { Columns3Cog as LucideColumnsSettings }
export { Combine as LucideCombine }
export { Command as LucideCommand }
export { Compass as LucideCompass }
export { Component as LucideComponent }
export { Computer as LucideComputer }
export { ConciergeBell as LucideConciergeBell }
export { Cone as LucideCone }
export { Construction as LucideConstruction }
export { Contact as LucideContact }
export { ContactRound as LucideContact2 }
export { ContactRound as LucideContactRound }
export { Container as LucideContainer }
export { Contrast as LucideContrast }
export { Cookie as LucideCookie }
export { CookingPot as LucideCookingPot }
export { Copy as LucideCopy }
export { CopyCheck as LucideCopyCheck }
export { CopyMinus as LucideCopyMinus }
export { CopyPlus as LucideCopyPlus }
export { CopySlash as LucideCopySlash }
export { CopyX as LucideCopyX }
export { Copyleft as LucideCopyleft }
export { Copyright as LucideCopyright }
export { CornerDownLeft as LucideCornerDownLeft }
export { CornerDownRight as LucideCornerDownRight }
export { CornerLeftDown as LucideCornerLeftDown }
export { CornerLeftUp as LucideCornerLeftUp }
export { CornerRightDown as LucideCornerRightDown }
export { CornerRightUp as LucideCornerRightUp }
export { CornerUpLeft as LucideCornerUpLeft }
export { CornerUpRight as LucideCornerUpRight }
export { Cpu as LucideCpu }
export { CreativeCommons as LucideCreativeCommons }
export { CreditCard as LucideCreditCard }
export { CreditCardCheck as LucideCreditCardCheck }
export { CreditCardMinus as LucideCreditCardMinus }
export { CreditCardPlus as LucideCreditCardPlus }
export { CreditCardX as LucideCreditCardX }
export { Croissant as LucideCroissant }
export { Crop as LucideCrop }
export { Cross as LucideCross }
export { Crosshair as LucideCrosshair }
export { Crown as LucideCrown }
export { Cuboid as LucideCuboid }
export { CupSoda as LucideCupSoda }
export { Braces as LucideCurlyBraces }
export { Currency as LucideCurrency }
export { Cylinder as LucideCylinder }
export { Dam as LucideDam }
export { Database as LucideDatabase }
export { DatabaseArrowDown as LucideDatabaseArrowDown }
export { DatabaseArrowUp as LucideDatabaseArrowUp }
export { DatabaseBackup as LucideDatabaseBackup }
export { DatabaseCheck as LucideDatabaseCheck }
export { DatabaseMinus as LucideDatabaseMinus }
export { DatabasePlus as LucideDatabasePlus }
export { DatabaseSearch as LucideDatabaseSearch }
export { DatabaseX as LucideDatabaseX }
export { DatabaseZap as LucideDatabaseZap }
export { DecimalsArrowLeft as LucideDecimalsArrowLeft }
export { DecimalsArrowRight as LucideDecimalsArrowRight }
export { Delete as LucideDelete }
export { Dessert as LucideDessert }
export { Diameter as LucideDiameter }
export { Diamond as LucideDiamond }
export { DiamondMinus as LucideDiamondMinus }
export { DiamondPercent as LucideDiamondPercent }
export { DiamondPlus as LucideDiamondPlus }
export { Dice1 as LucideDice1 }
export { Dice2 as LucideDice2 }
export { Dice3 as LucideDice3 }
export { Dice4 as LucideDice4 }
export { Dice5 as LucideDice5 }
export { Dice6 as LucideDice6 }
export { Dices as LucideDices }
export { Diff as LucideDiff }
export { Disc as LucideDisc }
export { Disc2 as LucideDisc2 }
export { Disc3 as LucideDisc3 }
export { DiscAlbum as LucideDiscAlbum }
export { Divide as LucideDivide }
export { CircleDivide as LucideDivideCircle }
export { SquareDivide as LucideDivideSquare }
export { Dna as LucideDna }
export { DnaOff as LucideDnaOff }
export { Dock as LucideDock }
export { Dog as LucideDog }
export { DollarSign as LucideDollarSign }
export { Donut as LucideDonut }
export { DoorClosed as LucideDoorClosed }
export { DoorClosedLocked as LucideDoorClosedLocked }
export { DoorOpen as LucideDoorOpen }
export { Dot as LucideDot }
export { SquareDot as LucideDotSquare }
export { Download as LucideDownload }
export { CloudDownload as LucideDownloadCloud }
export { DraftingCompass as LucideDraftingCompass }
export { Drama as LucideDrama }
export { Drill as LucideDrill }
export { Drone as LucideDrone }
export { Droplet as LucideDroplet }
export { DropletOff as LucideDropletOff }
export { Droplets as LucideDroplets }
export { Drum as LucideDrum }
export { Drumstick as LucideDrumstick }
export { Dumbbell as LucideDumbbell }
export { Ear as LucideEar }
export { EarOff as LucideEarOff }
export { Earth as LucideEarth }
export { EarthLock as LucideEarthLock }
export { Eclipse as LucideEclipse }
export { SquarePen as LucideEdit }
export { Pen as LucideEdit2 }
export { PenLine as LucideEdit3 }
export { Egg as LucideEgg }
export { EggFried as LucideEggFried }
export { EggOff as LucideEggOff }
export { Eject as LucideEject }
export { Ellipse as LucideEllipse }
export { Ellipsis as LucideEllipsis }
export { EllipsisVertical as LucideEllipsisVertical }
export { Equal as LucideEqual }
export { EqualApproximately as LucideEqualApproximately }
export { EqualNot as LucideEqualNot }
export { SquareEqual as LucideEqualSquare }
export { Eraser as LucideEraser }
export { EthernetPort as LucideEthernetPort }
export { Euro as LucideEuro }
export { EvCharger as LucideEvCharger }
export { Expand as LucideExpand }
export { ExternalLink as LucideExternalLink }
export { Eye as LucideEye }
export { EyeClosed as LucideEyeClosed }
export { EyeDashed as LucideEyeDashed }
export { EyeOff as LucideEyeOff }
export { FaceAngry as LucideFaceAngry }
export { FaceExpressionless as LucideFaceExpressionless }
export { FaceGrinning as LucideFaceGrinning }
export { FaceNeutral as LucideFaceNeutral }
export { FaceSlightlyFrowning as LucideFaceSlightlyFrowning }
export { FaceSlightlySmiling as LucideFaceSlightlySmiling }
export { FaceSlightlySmilingPlus as LucideFaceSlightlySmilingPlus }
export { Factory as LucideFactory }
export { Fan as LucideFan }
export { FastForward as LucideFastForward }
export { Feather as LucideFeather }
export { Fence as LucideFence }
export { FerrisWheel as LucideFerrisWheel }
export { File as LucideFile }
export { FileArchive as LucideFileArchive }
export { FileHeadphone as LucideFileAudio }
export { FileHeadphone as LucideFileAudio2 }
export { FileAxis3d as LucideFileAxis3D }
export { FileAxis3d as LucideFileAxis3d }
export { FileBadge as LucideFileBadge }
export { FileBadge as LucideFileBadge2 }
export { FileChartColumnIncreasing as LucideFileBarChart }
export { FileChartColumn as LucideFileBarChart2 }
export { FileBox as LucideFileBox }
export { FileBraces as LucideFileBraces }
export { FileBracesCorner as LucideFileBracesCorner }
export { FileChartColumn as LucideFileChartColumn }
export { FileChartColumnIncreasing as LucideFileChartColumnIncreasing }
export { FileChartLine as LucideFileChartLine }
export { FileChartPie as LucideFileChartPie }
export { FileCheck as LucideFileCheck }
export { FileCheckCorner as LucideFileCheck2 }
export { FileCheckCorner as LucideFileCheckCorner }
export { FileClock as LucideFileClock }
export { FileCode as LucideFileCode }
export { FileCodeCorner as LucideFileCode2 }
export { FileCodeCorner as LucideFileCodeCorner }
export { FileCog as LucideFileCog }
export { FileCog as LucideFileCog2 }
export { FileDiff as LucideFileDiff }
export { FileDigit as LucideFileDigit }
export { FileDown as LucideFileDown }
export { FilePen as LucideFileEdit }
export { FileExclamationPoint as LucideFileExclamationPoint }
export { FileHeadphone as LucideFileHeadphone }
export { FileHeart as LucideFileHeart }
export { FileImage as LucideFileImage }
export { FileInput as LucideFileInput }
export { FileBraces as LucideFileJson }
export { FileBracesCorner as LucideFileJson2 }
export { FileKey as LucideFileKey }
export { FileKey as LucideFileKey2 }
export { FileChartLine as LucideFileLineChart }
export { FileLock as LucideFileLock }
export { FileLock as LucideFileLock2 }
export { FileMinus as LucideFileMinus }
export { FileMinusCorner as LucideFileMinus2 }
export { FileMinusCorner as LucideFileMinusCorner }
export { FileMusic as LucideFileMusic }
export { FileOutput as LucideFileOutput }
export { FilePen as LucideFilePen }
export { FilePenLine as LucideFilePenLine }
export { FileChartPie as LucideFilePieChart }
export { FilePlay as LucideFilePlay }
export { FilePlus as LucideFilePlus }
export { FilePlusCorner as LucideFilePlus2 }
export { FilePlusCorner as LucideFilePlusCorner }
export { FileQuestionMark as LucideFileQuestion }
export { FileQuestionMark as LucideFileQuestionMark }
export { FileScan as LucideFileScan }
export { FileSearch as LucideFileSearch }
export { FileSearchCorner as LucideFileSearch2 }
export { FileSearchCorner as LucideFileSearchCorner }
export { FileSignal as LucideFileSignal }
export { FilePenLine as LucideFileSignature }
export { FileSliders as LucideFileSliders }
export { FileSpreadsheet as LucideFileSpreadsheet }
export { FileStack as LucideFileStack }
export { FileSymlink as LucideFileSymlink }
export { FileTerminal as LucideFileTerminal }
export { FileText as LucideFileText }
export { FileType as LucideFileType }
export { FileTypeCorner as LucideFileType2 }
export { FileTypeCorner as LucideFileTypeCorner }
export { FileUp as LucideFileUp }
export { FileUser as LucideFileUser }
export { FilePlay as LucideFileVideo }
export { FileVideoCamera as LucideFileVideo2 }
export { FileVideoCamera as LucideFileVideoCamera }
export { FileVolume as LucideFileVolume }
export { FileSignal as LucideFileVolume2 }
export { FileExclamationPoint as LucideFileWarning }
export { FileX as LucideFileX }
export { FileXCorner as LucideFileX2 }
export { FileXCorner as LucideFileXCorner }
export { Files as LucideFiles }
export { Film as LucideFilm }
export { Funnel as LucideFilter }
export { FunnelX as LucideFilterX }
export { FingerprintPattern as LucideFingerprint }
export { FingerprintPattern as LucideFingerprintPattern }
export { FireExtinguisher as LucideFireExtinguisher }
export { Fish as LucideFish }
export { FishOff as LucideFishOff }
export { FishSymbol as LucideFishSymbol }
export { FishingHook as LucideFishingHook }
export { FishingRod as LucideFishingRod }
export { Flag as LucideFlag }
export { FlagOff as LucideFlagOff }
export { FlagTriangleLeft as LucideFlagTriangleLeft }
export { FlagTriangleRight as LucideFlagTriangleRight }
export { Flame as LucideFlame }
export { FlameKindling as LucideFlameKindling }
export { Flashlight as LucideFlashlight }
export { FlashlightOff as LucideFlashlightOff }
export { FlaskConical as LucideFlaskConical }
export { FlaskConicalOff as LucideFlaskConicalOff }
export { FlaskRound as LucideFlaskRound }
export { SquareCenterlineDashedHorizontal as LucideFlipHorizontal }
export { FlipHorizontal2 as LucideFlipHorizontal2 }
export { SquareCenterlineDashedVertical as LucideFlipVertical }
export { FlipVertical2 as LucideFlipVertical2 }
export { Flower as LucideFlower }
export { Flower2 as LucideFlower2 }
export { Focus as LucideFocus }
export { FoldHorizontal as LucideFoldHorizontal }
export { FoldVertical as LucideFoldVertical }
export { Folder as LucideFolder }
export { FolderArchive as LucideFolderArchive }
export { FolderBookmark as LucideFolderBookmark }
export { FolderCheck as LucideFolderCheck }
export { FolderClock as LucideFolderClock }
export { FolderClosed as LucideFolderClosed }
export { FolderCode as LucideFolderCode }
export { FolderCog as LucideFolderCog }
export { FolderCog as LucideFolderCog2 }
export { FolderDot as LucideFolderDot }
export { FolderDown as LucideFolderDown }
export { FolderPen as LucideFolderEdit }
export { FolderGit as LucideFolderGit }
export { FolderGit2 as LucideFolderGit2 }
export { FolderHeart as LucideFolderHeart }
export { FolderInput as LucideFolderInput }
export { FolderKanban as LucideFolderKanban }
export { FolderKey as LucideFolderKey }
export { FolderLock as LucideFolderLock }
export { FolderMinus as LucideFolderMinus }
export { FolderOpen as LucideFolderOpen }
export { FolderOpenDot as LucideFolderOpenDot }
export { FolderOutput as LucideFolderOutput }
export { FolderPen as LucideFolderPen }
export { FolderPlus as LucideFolderPlus }
export { FolderRoot as LucideFolderRoot }
export { FolderSearch as LucideFolderSearch }
export { FolderSearch2 as LucideFolderSearch2 }
export { FolderSymlink as LucideFolderSymlink }
export { FolderSync as LucideFolderSync }
export { FolderTree as LucideFolderTree }
export { FolderUp as LucideFolderUp }
export { FolderX as LucideFolderX }
export { Folders as LucideFolders }
export { Footprints as LucideFootprints }
export { Utensils as LucideForkKnife }
export { UtensilsCrossed as LucideForkKnifeCrossed }
export { Forklift as LucideForklift }
export { Form as LucideForm }
export { RectangleEllipsis as LucideFormInput }
export { Forward as LucideForward }
export { Frame as LucideFrame }
export { FaceSlightlyFrowning as LucideFrown }
export { Fuel as LucideFuel }
export { Fullscreen as LucideFullscreen }
export { SquareFunction as LucideFunctionSquare }
export { Funnel as LucideFunnel }
export { FunnelPlus as LucideFunnelPlus }
export { FunnelX as LucideFunnelX }
export { Galaxy as LucideGalaxy }
export { GalleryHorizontal as LucideGalleryHorizontal }
export { GalleryHorizontalEnd as LucideGalleryHorizontalEnd }
export { GalleryThumbnails as LucideGalleryThumbnails }
export { GalleryVertical as LucideGalleryVertical }
export { GalleryVerticalEnd as LucideGalleryVerticalEnd }
export { Gamepad as LucideGamepad }
export { Gamepad2 as LucideGamepad2 }
export { GamepadDirectional as LucideGamepadDirectional }
export { ChartNoAxesGantt as LucideGanttChart }
export { SquareChartGantt as LucideGanttChartSquare }
export { Gauge as LucideGauge }
export { CircleGauge as LucideGaugeCircle }
export { Gavel as LucideGavel }
export { Gem as LucideGem }
export { GeorgianLari as LucideGeorgianLari }
export { Ghost as LucideGhost }
export { Gift as LucideGift }
export { GitBranch as LucideGitBranch }
export { GitBranchMinus as LucideGitBranchMinus }
export { GitBranchPlus as LucideGitBranchPlus }
export { GitCommitHorizontal as LucideGitCommit }
export { GitCommitHorizontal as LucideGitCommitHorizontal }
export { GitCommitVertical as LucideGitCommitVertical }
export { GitCompare as LucideGitCompare }
export { GitCompareArrows as LucideGitCompareArrows }
export { GitFork as LucideGitFork }
export { GitGraph as LucideGitGraph }
export { GitMerge as LucideGitMerge }
export { GitMergeConflict as LucideGitMergeConflict }
export { GitPullRequest as LucideGitPullRequest }
export { GitPullRequestArrow as LucideGitPullRequestArrow }
export { GitPullRequestClosed as LucideGitPullRequestClosed }
export { GitPullRequestCreate as LucideGitPullRequestCreate }
export { GitPullRequestCreateArrow as LucideGitPullRequestCreateArrow }
export { GitPullRequestDraft as LucideGitPullRequestDraft }
export { GlassWater as LucideGlassWater }
export { Glasses as LucideGlasses }
export { Globe as LucideGlobe }
export { Earth as LucideGlobe2 }
export { GlobeCheck as LucideGlobeCheck }
export { GlobeLock as LucideGlobeLock }
export { GlobeOff as LucideGlobeOff }
export { GlobeX as LucideGlobeX }
export { Goal as LucideGoal }
export { Gpu as LucideGpu }
export { HandGrab as LucideGrab }
export { GraduationCap as LucideGraduationCap }
export { Grape as LucideGrape }
export { Grid3x3 as LucideGrid }
export { Grid2x2 as LucideGrid2X2 }
export { Grid2x2Check as LucideGrid2X2Check }
export { Grid2x2Plus as LucideGrid2X2Plus }
export { Grid2x2X as LucideGrid2X2X }
export { Grid2x2 as LucideGrid2x2 }
export { Grid2x2Check as LucideGrid2x2Check }
export { Grid2x2Plus as LucideGrid2x2Plus }
export { Grid2x2X as LucideGrid2x2X }
export { Grid3x3 as LucideGrid3X3 }
export { Grid3x2 as LucideGrid3x2 }
export { Grid3x3 as LucideGrid3x3 }
export { Grip as LucideGrip }
export { GripHorizontal as LucideGripHorizontal }
export { GripVertical as LucideGripVertical }
export { Group as LucideGroup }
export { Guitar as LucideGuitar }
export { Ham as LucideHam }
export { Hamburger as LucideHamburger }
export { Hammer as LucideHammer }
export { Hand as LucideHand }
export { HandCoins as LucideHandCoins }
export { HandFist as LucideHandFist }
export { HandGrab as LucideHandGrab }
export { HandHeart as LucideHandHeart }
export { HandHelping as LucideHandHelping }
export { HandMetal as LucideHandMetal }
export { HandPlatter as LucideHandPlatter }
export { Handbag as LucideHandbag }
export { Handshake as LucideHandshake }
export { HardDrive as LucideHardDrive }
export { HardDriveDownload as LucideHardDriveDownload }
export { HardDriveUpload as LucideHardDriveUpload }
export { HardHat as LucideHardHat }
export { Hash as LucideHash }
export { HatGlasses as LucideHatGlasses }
export { Haze as LucideHaze }
export { Hd as LucideHd }
export { HdmiPort as LucideHdmiPort }
export { Heading as LucideHeading }
export { Heading1 as LucideHeading1 }
export { Heading2 as LucideHeading2 }
export { Heading3 as LucideHeading3 }
export { Heading4 as LucideHeading4 }
export { Heading5 as LucideHeading5 }
export { Heading6 as LucideHeading6 }
export { HeadphoneOff as LucideHeadphoneOff }
export { Headphones as LucideHeadphones }
export { Headset as LucideHeadset }
export { Heart as LucideHeart }
export { HeartCrack as LucideHeartCrack }
export { HeartHandshake as LucideHeartHandshake }
export { HeartMinus as LucideHeartMinus }
export { HeartOff as LucideHeartOff }
export { HeartPlus as LucideHeartPlus }
export { HeartPulse as LucideHeartPulse }
export { HeartX as LucideHeartX }
export { Heater as LucideHeater }
export { Helicopter as LucideHelicopter }
export { CircleQuestionMark as LucideHelpCircle }
export { HandHelping as LucideHelpingHand }
export { Hexagon as LucideHexagon }
export { Highlighter as LucideHighlighter }
export { RotateCcwClock as LucideHistory }
export { House as LucideHome }
export { Hop as LucideHop }
export { HopOff as LucideHopOff }
export { Hospital as LucideHospital }
export { Hotel as LucideHotel }
export { Hourglass as LucideHourglass }
export { House as LucideHouse }
export { HouseHeart as LucideHouseHeart }
export { HousePlug as LucideHousePlug }
export { HousePlus as LucideHousePlus }
export { HouseWifi as LucideHouseWifi }
export { IceCreamCone as LucideIceCream }
export { IceCreamBowl as LucideIceCream2 }
export { IceCreamBowl as LucideIceCreamBowl }
export { IceCreamCone as LucideIceCreamCone }
export { IdCard as LucideIdCard }
export { IdCardLanyard as LucideIdCardLanyard }
export { Image as LucideImage }
export { ImageDown as LucideImageDown }
export { ImageMinus as LucideImageMinus }
export { ImageOff as LucideImageOff }
export { ImagePlay as LucideImagePlay }
export { ImagePlus as LucideImagePlus }
export { ImageUp as LucideImageUp }
export { ImageUpscale as LucideImageUpscale }
export { Images as LucideImages }
export { Import as LucideImport }
export { Inbox as LucideInbox }
export { ListIndentIncrease as LucideIndent }
export { ListIndentDecrease as LucideIndentDecrease }
export { ListIndentIncrease as LucideIndentIncrease }
export { IndianRupee as LucideIndianRupee }
export { Infinity as LucideInfinity }
export { Info as LucideInfo }
export { SquareMousePointer as LucideInspect }
export { InspectionPanel as LucideInspectionPanel }
export { Italic as LucideItalic }
export { IterationCcw as LucideIterationCcw }
export { IterationCw as LucideIterationCw }
export { JapaneseYen as LucideJapaneseYen }
export { Joystick as LucideJoystick }
export { Kanban as LucideKanban }
export { SquareKanban as LucideKanbanSquare }
export { SquareDashedKanban as LucideKanbanSquareDashed }
export { Kayak as LucideKayak }
export { Key as LucideKey }
export { KeyRound as LucideKeyRound }
export { KeySquare as LucideKeySquare }
export { Keyboard as LucideKeyboard }
export { KeyboardMusic as LucideKeyboardMusic }
export { KeyboardOff as LucideKeyboardOff }
export { Lamp as LucideLamp }
export { LampCeiling as LucideLampCeiling }
export { LampDesk as LucideLampDesk }
export { LampFloor as LucideLampFloor }
export { LampWallDown as LucideLampWallDown }
export { LampWallUp as LucideLampWallUp }
export { LandPlot as LucideLandPlot }
export { Landmark as LucideLandmark }
export { Languages as LucideLanguages }
export { Laptop as LucideLaptop }
export { LaptopMinimal as LucideLaptop2 }
export { LaptopMinimal as LucideLaptopMinimal }
export { LaptopMinimalCheck as LucideLaptopMinimalCheck }
export { Lasso as LucideLasso }
export { LassoSelect as LucideLassoSelect }
export { FaceGrinning as LucideLaugh }
export { LayerArrowDown as LucideLayerArrowDown }
export { LayerArrowUp as LucideLayerArrowUp }
export { Layers as LucideLayers }
export { Layers2 as LucideLayers2 }
export { Layers as LucideLayers3 }
export { LayersArrowDown as LucideLayersArrowDown }
export { LayersArrowUp as LucideLayersArrowUp }
export { LayersMinus as LucideLayersMinus }
export { LayersPlus as LucideLayersPlus }
export { PanelsTopLeft as LucideLayout }
export { LayoutDashboard as LucideLayoutDashboard }
export { LayoutFreeform as LucideLayoutFreeform }
export { LayoutGrid as LucideLayoutGrid }
export { LayoutList as LucideLayoutList }
export { LayoutPanelLeft as LucideLayoutPanelLeft }
export { LayoutPanelTop as LucideLayoutPanelTop }
export { LayoutTemplate as LucideLayoutTemplate }
export { Leaf as LucideLeaf }
export { LeafyGreen as LucideLeafyGreen }
export { Lectern as LucideLectern }
export { LensConcave as LucideLensConcave }
export { LensConvex as LucideLensConvex }
export { TextInitial as LucideLetterText }
export { Library as LucideLibrary }
export { LibraryBig as LucideLibraryBig }
export { SquareLibrary as LucideLibrarySquare }
export { LifeBuoy as LucideLifeBuoy }
export { Ligature as LucideLigature }
export { Lightbulb as LucideLightbulb }
export { LightbulbOff as LucideLightbulbOff }
export { ChartLine as LucideLineChart }
export { LineDotRightHorizontal as LucideLineDotRightHorizontal }
export { LineSquiggle as LucideLineSquiggle }
export { LineStyle as LucideLineStyle }
export { Link as LucideLink }
export { Link2 as LucideLink2 }
export { Link2Off as LucideLink2Off }
export { List as LucideList }
export { ListCheck as LucideListCheck }
export { ListChecks as LucideListChecks }
export { ListChevronsDownUp as LucideListChevronsDownUp }
export { ListChevronsUpDown as LucideListChevronsUpDown }
export { ListClock as LucideListClock }
export { ListCollapse as LucideListCollapse }
export { ListEnd as LucideListEnd }
export { ListFilter as LucideListFilter }
export { ListFilterPlus as LucideListFilterPlus }
export { ListIndentDecrease as LucideListIndentDecrease }
export { ListIndentIncrease as LucideListIndentIncrease }
export { ListMinus as LucideListMinus }
export { ListMusic as LucideListMusic }
export { ListOrdered as LucideListOrdered }
export { ListPlus as LucideListPlus }
export { ListRestart as LucideListRestart }
export { ListSortAscending as LucideListSortAscending }
export { ListSortDescending as LucideListSortDescending }
export { ListStart as LucideListStart }
export { ListTodo as LucideListTodo }
export { ListTree as LucideListTree }
export { ListVideo as LucideListVideo }
export { ListX as LucideListX }
export { Loader as LucideLoader }
export { LoaderCircle as LucideLoader2 }
export { LoaderCircle as LucideLoaderCircle }
export { LoaderPinwheel as LucideLoaderPinwheel }
export { Locate as LucideLocate }
export { LocateFixed as LucideLocateFixed }
export { LocateOff as LucideLocateOff }
export { MapPinPen as LucideLocationEdit }
export { Lock as LucideLock }
export { LockKeyhole as LucideLockKeyhole }
export { LockKeyholeOpen as LucideLockKeyholeOpen }
export { LockOpen as LucideLockOpen }
export { LogIn as LucideLogIn }
export { LogOut as LucideLogOut }
export { Logs as LucideLogs }
export { Lollipop as LucideLollipop }
export { Luggage as LucideLuggage }
export { SquareM as LucideMSquare }
export { Magnet as LucideMagnet }
export { Mail as LucideMail }
export { MailBadge as LucideMailBadge }
export { MailCheck as LucideMailCheck }
export { MailClock as LucideMailClock }
export { MailMinus as LucideMailMinus }
export { MailOpen as LucideMailOpen }
export { MailPlus as LucideMailPlus }
export { MailQuestionMark as LucideMailQuestion }
export { MailQuestionMark as LucideMailQuestionMark }
export { MailSearch as LucideMailSearch }
export { MailWarning as LucideMailWarning }
export { MailX as LucideMailX }
export { Mailbox as LucideMailbox }
export { Mails as LucideMails }
export { Map as LucideMap }
export { MapMinus as LucideMapMinus }
export { MapPin as LucideMapPin }
export { MapPinCheck as LucideMapPinCheck }
export { MapPinCheckInside as LucideMapPinCheckInside }
export { MapPinHouse as LucideMapPinHouse }
export { MapPinMinus as LucideMapPinMinus }
export { MapPinMinusInside as LucideMapPinMinusInside }
export { MapPinOff as LucideMapPinOff }
export { MapPinPen as LucideMapPinPen }
export { MapPinPlus as LucideMapPinPlus }
export { MapPinPlusInside as LucideMapPinPlusInside }
export { MapPinSearch as LucideMapPinSearch }
export { MapPinX as LucideMapPinX }
export { MapPinXInside as LucideMapPinXInside }
export { MapPinned as LucideMapPinned }
export { MapPlus as LucideMapPlus }
export { Mars as LucideMars }
export { MarsStroke as LucideMarsStroke }
export { Martini as LucideMartini }
export { Maximize as LucideMaximize }
export { Maximize2 as LucideMaximize2 }
export { Medal as LucideMedal }
export { Megaphone as LucideMegaphone }
export { MegaphoneOff as LucideMegaphoneOff }
export { FaceNeutral as LucideMeh }
export { MemoryStick as LucideMemoryStick }
export { Menu as LucideMenu }
export { SquareMenu as LucideMenuSquare }
export { Merge as LucideMerge }
export { MessageCircle as LucideMessageCircle }
export { MessageCircleCheck as LucideMessageCircleCheck }
export { MessageCircleCode as LucideMessageCircleCode }
export { MessageCircleDashed as LucideMessageCircleDashed }
export { MessageCircleDashedCheck as LucideMessageCircleDashedCheck }
export { MessageCircleHeart as LucideMessageCircleHeart }
export { MessageCircleMore as LucideMessageCircleMore }
export { MessageCircleOff as LucideMessageCircleOff }
export { MessageCirclePlus as LucideMessageCirclePlus }
export { MessageCircleQuestionMark as LucideMessageCircleQuestion }
export { MessageCircleQuestionMark as LucideMessageCircleQuestionMark }
export { MessageCircleReply as LucideMessageCircleReply }
export { MessageCircleWarning as LucideMessageCircleWarning }
export { MessageCircleX as LucideMessageCircleX }
export { MessageSquare as LucideMessageSquare }
export { MessageSquareCheck as LucideMessageSquareCheck }
export { MessageSquareCode as LucideMessageSquareCode }
export { MessageSquareDashed as LucideMessageSquareDashed }
export { MessageSquareDiff as LucideMessageSquareDiff }
export { MessageSquareDot as LucideMessageSquareDot }
export { MessageSquareHeart as LucideMessageSquareHeart }
export { MessageSquareLock as LucideMessageSquareLock }
export { MessageSquareMore as LucideMessageSquareMore }
export { MessageSquareOff as LucideMessageSquareOff }
export { MessageSquarePlus as LucideMessageSquarePlus }
export { MessageSquareQuote as LucideMessageSquareQuote }
export { MessageSquareReply as LucideMessageSquareReply }
export { MessageSquareShare as LucideMessageSquareShare }
export { MessageSquareText as LucideMessageSquareText }
export { MessageSquareWarning as LucideMessageSquareWarning }
export { MessageSquareX as LucideMessageSquareX }
export { MessagesSquare as LucideMessagesSquare }
export { Metronome as LucideMetronome }
export { Mic as LucideMic }
export { MicVocal as LucideMic2 }
export { MicAudioLines as LucideMicAudioLines }
export { MicOff as LucideMicOff }
export { MicSignal as LucideMicSignal }
export { MicVocal as LucideMicVocal }
export { Microchip as LucideMicrochip }
export { Microscope as LucideMicroscope }
export { Microwave as LucideMicrowave }
export { MidiPort as LucideMidiPort }
export { Milestone as LucideMilestone }
export { Milk as LucideMilk }
export { MilkOff as LucideMilkOff }
export { Minimize as LucideMinimize }
export { Minimize2 as LucideMinimize2 }
export { Minus as LucideMinus }
export { CircleMinus as LucideMinusCircle }
export { SquareMinus as LucideMinusSquare }
export { MirrorRectangular as LucideMirrorRectangular }
export { MirrorRound as LucideMirrorRound }
export { Monitor as LucideMonitor }
export { MonitorCheck as LucideMonitorCheck }
export { MonitorCloud as LucideMonitorCloud }
export { MonitorCog as LucideMonitorCog }
export { MonitorDot as LucideMonitorDot }
export { MonitorDown as LucideMonitorDown }
export { MonitorOff as LucideMonitorOff }
export { MonitorPause as LucideMonitorPause }
export { MonitorPlay as LucideMonitorPlay }
export { MonitorSmartphone as LucideMonitorSmartphone }
export { MonitorSpeaker as LucideMonitorSpeaker }
export { MonitorStop as LucideMonitorStop }
export { MonitorUp as LucideMonitorUp }
export { MonitorX as LucideMonitorX }
export { Moon as LucideMoon }
export { MoonStar as LucideMoonStar }
export { Mop as LucideMop }
export { MopSparkles as LucideMopSparkles }
export { Ellipsis as LucideMoreHorizontal }
export { EllipsisVertical as LucideMoreVertical }
export { Mosque as LucideMosque }
export { Motorbike as LucideMotorbike }
export { Mountain as LucideMountain }
export { MountainSnow as LucideMountainSnow }
export { Mouse as LucideMouse }
export { MouseLeft as LucideMouseLeft }
export { MouseOff as LucideMouseOff }
export { MousePointer as LucideMousePointer }
export { MousePointer2 as LucideMousePointer2 }
export { MousePointer2Off as LucideMousePointer2Off }
export { MousePointerBan as LucideMousePointerBan }
export { MousePointerClick as LucideMousePointerClick }
export { SquareDashedMousePointer as LucideMousePointerSquareDashed }
export { MouseRight as LucideMouseRight }
export { Move as LucideMove }
export { Move3d as LucideMove3D }
export { Move3d as LucideMove3d }
export { MoveDiagonal as LucideMoveDiagonal }
export { MoveDiagonal2 as LucideMoveDiagonal2 }
export { MoveDown as LucideMoveDown }
export { MoveDownLeft as LucideMoveDownLeft }
export { MoveDownRight as LucideMoveDownRight }
export { MoveHorizontal as LucideMoveHorizontal }
export { MoveLeft as LucideMoveLeft }
export { MoveRight as LucideMoveRight }
export { MoveUp as LucideMoveUp }
export { MoveUpLeft as LucideMoveUpLeft }
export { MoveUpRight as LucideMoveUpRight }
export { MoveVertical as LucideMoveVertical }
export { Music as LucideMusic }
export { Music2 as LucideMusic2 }
export { Music3 as LucideMusic3 }
export { Music4 as LucideMusic4 }
export { Navigation as LucideNavigation }
export { Navigation2 as LucideNavigation2 }
export { Navigation2Off as LucideNavigation2Off }
export { NavigationOff as LucideNavigationOff }
export { Network as LucideNetwork }
export { Newspaper as LucideNewspaper }
export { Nfc as LucideNfc }
export { NonBinary as LucideNonBinary }
export { Notebook as LucideNotebook }
export { NotebookPen as LucideNotebookPen }
export { NotebookTabs as LucideNotebookTabs }
export { NotebookText as LucideNotebookText }
export { NotepadText as LucideNotepadText }
export { NotepadTextDashed as LucideNotepadTextDashed }
export { Nut as LucideNut }
export { NutOff as LucideNutOff }
export { Octagon as LucideOctagon }
export { OctagonAlert as LucideOctagonAlert }
export { OctagonMinus as LucideOctagonMinus }
export { OctagonPause as LucideOctagonPause }
export { OctagonX as LucideOctagonX }
export { Omega as LucideOmega }
export { Option as LucideOption }
export { Orbit as LucideOrbit }
export { Origami as LucideOrigami }
export { ListIndentDecrease as LucideOutdent }
export { Package as LucidePackage }
export { Package2 as LucidePackage2 }
export { PackageCheck as LucidePackageCheck }
export { PackageMinus as LucidePackageMinus }
export { PackageOpen as LucidePackageOpen }
export { PackagePlus as LucidePackagePlus }
export { PackageSearch as LucidePackageSearch }
export { PackageX as LucidePackageX }
export { PaintBucket as LucidePaintBucket }
export { PaintRoller as LucidePaintRoller }
export { Paintbrush as LucidePaintbrush }
export { PaintbrushVertical as LucidePaintbrush2 }
export { PaintbrushVertical as LucidePaintbrushVertical }
export { Palette as LucidePalette }
export { TreePalm as LucidePalmtree }
export { Panda as LucidePanda }
export { PanelBottom as LucidePanelBottom }
export { PanelBottomClose as LucidePanelBottomClose }
export { PanelBottomDashed as LucidePanelBottomDashed }
export { PanelBottomDashed as LucidePanelBottomInactive }
export { PanelBottomOpen as LucidePanelBottomOpen }
export { PanelLeft as LucidePanelLeft }
export { PanelLeftClose as LucidePanelLeftClose }
export { PanelLeftDashed as LucidePanelLeftDashed }
export { PanelLeftDashed as LucidePanelLeftInactive }
export { PanelLeftOpen as LucidePanelLeftOpen }
export { PanelLeftRightDashed as LucidePanelLeftRightDashed }
export { PanelRight as LucidePanelRight }
export { PanelRightClose as LucidePanelRightClose }
export { PanelRightDashed as LucidePanelRightDashed }
export { PanelRightDashed as LucidePanelRightInactive }
export { PanelRightOpen as LucidePanelRightOpen }
export { PanelTop as LucidePanelTop }
export { PanelTopBottomDashed as LucidePanelTopBottomDashed }
export { PanelTopClose as LucidePanelTopClose }
export { PanelTopDashed as LucidePanelTopDashed }
export { PanelTopDashed as LucidePanelTopInactive }
export { PanelTopOpen as LucidePanelTopOpen }
export { PanelsLeftBottom as LucidePanelsLeftBottom }
export { Columns3 as LucidePanelsLeftRight }
export { PanelsRightBottom as LucidePanelsRightBottom }
export { Rows3 as LucidePanelsTopBottom }
export { PanelsTopLeft as LucidePanelsTopLeft }
export { PaperBag as LucidePaperBag }
export { Paperclip as LucidePaperclip }
export { Parasol as LucideParasol }
export { Parentheses as LucideParentheses }
export { CircleParking as LucideParkingCircle }
export { CircleParkingOff as LucideParkingCircleOff }
export { ParkingMeter as LucideParkingMeter }
export { SquareParking as LucideParkingSquare }
export { SquareParkingOff as LucideParkingSquareOff }
export { PartyPopper as LucidePartyPopper }
export { Pause as LucidePause }
export { CirclePause as LucidePauseCircle }
export { OctagonPause as LucidePauseOctagon }
export { PawPrint as LucidePawPrint }
export { PcCase as LucidePcCase }
export { Pen as LucidePen }
export { SquarePen as LucidePenBox }
export { PenLine as LucidePenLine }
export { PenOff as LucidePenOff }
export { SquarePen as LucidePenSquare }
export { PenTool as LucidePenTool }
export { Pencil as LucidePencil }
export { PencilLine as LucidePencilLine }
export { PencilOff as LucidePencilOff }
export { PencilRuler as LucidePencilRuler }
export { PencilSparkles as LucidePencilSparkles }
export { Pentagon as LucidePentagon }
export { Percent as LucidePercent }
export { CirclePercent as LucidePercentCircle }
export { DiamondPercent as LucidePercentDiamond }
export { SquarePercent as LucidePercentSquare }
export { PersonStanding as LucidePersonStanding }
export { Phi as LucidePhi }
export { PhilippinePeso as LucidePhilippinePeso }
export { Phone as LucidePhone }
export { PhoneCall as LucidePhoneCall }
export { PhoneForwarded as LucidePhoneForwarded }
export { PhoneIncoming as LucidePhoneIncoming }
export { PhoneMissed as LucidePhoneMissed }
export { PhoneOff as LucidePhoneOff }
export { PhoneOutgoing as LucidePhoneOutgoing }
export { Pi as LucidePi }
export { SquarePi as LucidePiSquare }
export { Piano as LucidePiano }
export { Pickaxe as LucidePickaxe }
export { PictureInPicture as LucidePictureInPicture }
export { PictureInPicture2 as LucidePictureInPicture2 }
export { ChartPie as LucidePieChart }
export { PiggyBank as LucidePiggyBank }
export { Pilcrow as LucidePilcrow }
export { PilcrowLeft as LucidePilcrowLeft }
export { PilcrowRight as LucidePilcrowRight }
export { SquarePilcrow as LucidePilcrowSquare }
export { Pill as LucidePill }
export { PillBottle as LucidePillBottle }
export { Pin as LucidePin }
export { PinOff as LucidePinOff }
export { Pipette as LucidePipette }
export { Pizza as LucidePizza }
export { Plane as LucidePlane }
export { PlaneLanding as LucidePlaneLanding }
export { PlaneTakeoff as LucidePlaneTakeoff }
export { Play as LucidePlay }
export { CirclePlay as LucidePlayCircle }
export { PlayOff as LucidePlayOff }
export { SquarePlay as LucidePlaySquare }
export { PlayingCard as LucidePlayingCard }
export { PlayingCards as LucidePlayingCards }
export { PlayingCardsFan as LucidePlayingCardsFan }
export { Plug as LucidePlug }
export { Plug2 as LucidePlug2 }
export { PlugZap as LucidePlugZap }
export { PlugZap as LucidePlugZap2 }
export { Plus as LucidePlus }
export { CirclePlus as LucidePlusCircle }
export { SquarePlus as LucidePlusSquare }
export { PocketKnife as LucidePocketKnife }
export { MicSignal as LucidePodcast }
export { Podium as LucidePodium }
export { Pointer as LucidePointer }
export { PointerOff as LucidePointerOff }
export { Popcorn as LucidePopcorn }
export { Popsicle as LucidePopsicle }
export { PoundSterling as LucidePoundSterling }
export { Power as LucidePower }
export { CirclePower as LucidePowerCircle }
export { PowerOff as LucidePowerOff }
export { SquarePower as LucidePowerSquare }
export { Presentation as LucidePresentation }
export { Printer as LucidePrinter }
export { PrinterCheck as LucidePrinterCheck }
export { PrinterX as LucidePrinterX }
export { Projector as LucideProjector }
export { Proportions as LucideProportions }
export { Puzzle as LucidePuzzle }
export { Pyramid as LucidePyramid }
export { QrCode as LucideQrCode }
export { Quote as LucideQuote }
export { Rabbit as LucideRabbit }
export { Radar as LucideRadar }
export { Radiation as LucideRadiation }
export { Radical as LucideRadical }
export { Radio as LucideRadio }
export { RadioOff as LucideRadioOff }
export { RadioReceiver as LucideRadioReceiver }
export { RadioTower as LucideRadioTower }
export { Radius as LucideRadius }
export { Rainbow as LucideRainbow }
export { Rat as LucideRat }
export { Ratio as LucideRatio }
export { Receipt as LucideReceipt }
export { ReceiptCent as LucideReceiptCent }
export { ReceiptEuro as LucideReceiptEuro }
export { ReceiptIndianRupee as LucideReceiptIndianRupee }
export { ReceiptJapaneseYen as LucideReceiptJapaneseYen }
export { ReceiptPoundSterling as LucideReceiptPoundSterling }
export { ReceiptRussianRuble as LucideReceiptRussianRuble }
export { ReceiptSwissFranc as LucideReceiptSwissFranc }
export { ReceiptText as LucideReceiptText }
export { ReceiptTurkishLira as LucideReceiptTurkishLira }
export { RectangleCircle as LucideRectangleCircle }
export { RectangleEllipsis as LucideRectangleEllipsis }
export { RectangleGoggles as LucideRectangleGoggles }
export { RectangleHorizontal as LucideRectangleHorizontal }
export { RectangleVertical as LucideRectangleVertical }
export { Recycle as LucideRecycle }
export { Redo as LucideRedo }
export { Redo2 as LucideRedo2 }
export { RedoDot as LucideRedoDot }
export { RefreshCcw as LucideRefreshCcw }
export { RefreshCcwDot as LucideRefreshCcwDot }
export { RefreshCw as LucideRefreshCw }
export { RefreshCwOff as LucideRefreshCwOff }
export { Refrigerator as LucideRefrigerator }
export { Regex as LucideRegex }
export { RemoveFormatting as LucideRemoveFormatting }
export { Repeat as LucideRepeat }
export { Repeat1 as LucideRepeat1 }
export { Repeat2 as LucideRepeat2 }
export { RepeatOff as LucideRepeatOff }
export { Replace as LucideReplace }
export { ReplaceAll as LucideReplaceAll }
export { Reply as LucideReply }
export { ReplyAll as LucideReplyAll }
export { Rewind as LucideRewind }
export { Ribbon as LucideRibbon }
export { Road as LucideRoad }
export { RobotArm as LucideRobotArm }
export { RobotVacuum as LucideRobotVacuum }
export { Rocket as LucideRocket }
export { RockingChair as LucideRockingChair }
export { RollerCoaster as LucideRollerCoaster }
export { Rose as LucideRose }
export { Rotate3d as LucideRotate3D }
export { Rotate3d as LucideRotate3d }
export { RotateCcw as LucideRotateCcw }
export { RotateCcwClock as LucideRotateCcwClock }
export { RotateCcwKey as LucideRotateCcwKey }
export { RotateCcwSquare as LucideRotateCcwSquare }
export { RotateCw as LucideRotateCw }
export { RotateCwFadingClock as LucideRotateCwFadingClock }
export { RotateCwSquare as LucideRotateCwSquare }
export { Route as LucideRoute }
export { RouteOff as LucideRouteOff }
export { Router as LucideRouter }
export { Rows2 as LucideRows }
export { Rows2 as LucideRows2 }
export { Rows3 as LucideRows3 }
export { Rows4 as LucideRows4 }
export { Rss as LucideRss }
export { Ruler as LucideRuler }
export { RulerDimensionLine as LucideRulerDimensionLine }
export { RussianRuble as LucideRussianRuble }
export { Sailboat as LucideSailboat }
export { Salad as LucideSalad }
export { Sandwich as LucideSandwich }
export { Satellite as LucideSatellite }
export { SatelliteDish as LucideSatelliteDish }
export { SaudiRiyal as LucideSaudiRiyal }
export { Save as LucideSave }
export { SaveAll as LucideSaveAll }
export { SaveCheck as LucideSaveCheck }
export { SaveOff as LucideSaveOff }
export { SavePen as LucideSavePen }
export { SavePlus as LucideSavePlus }
export { Scale as LucideScale }
export { Scale3d as LucideScale3D }
export { Scale3d as LucideScale3d }
export { Scaling as LucideScaling }
export { Scan as LucideScan }
export { ScanBarcode as LucideScanBarcode }
export { ScanBox as LucideScanBox }
export { ScanEye as LucideScanEye }
export { ScanFace as LucideScanFace }
export { ScanHeart as LucideScanHeart }
export { ScanLine as LucideScanLine }
export { ScanQrCode as LucideScanQrCode }
export { ScanSearch as LucideScanSearch }
export { ScanSquare as LucideScanSquare }
export { ScanText as LucideScanText }
export { ChartScatter as LucideScatterChart }
export { School as LucideSchool }
export { University as LucideSchool2 }
export { Scissors as LucideScissors }
export { ScissorsLineDashed as LucideScissorsLineDashed }
export { SquareScissors as LucideScissorsSquare }
export { SquareBottomDashedScissors as LucideScissorsSquareDashedBottom }
export { Scooter as LucideScooter }
export { ScreenShare as LucideScreenShare }
export { ScreenShareOff as LucideScreenShareOff }
export { Scroll as LucideScroll }
export { ScrollText as LucideScrollText }
export { Search as LucideSearch }
export { SearchAlert as LucideSearchAlert }
export { SearchCheck as LucideSearchCheck }
export { SearchCode as LucideSearchCode }
export { SearchSlash as LucideSearchSlash }
export { SearchX as LucideSearchX }
export { Section as LucideSection }
export { Send as LucideSend }
export { SendHorizontal as LucideSendHorizonal }
export { SendHorizontal as LucideSendHorizontal }
export { SendToBack as LucideSendToBack }
export { SeparatorHorizontal as LucideSeparatorHorizontal }
export { SeparatorVertical as LucideSeparatorVertical }
export { Server as LucideServer }
export { ServerCog as LucideServerCog }
export { ServerCrash as LucideServerCrash }
export { ServerOff as LucideServerOff }
export { ServerPlus as LucideServerPlus }
export { Settings as LucideSettings }
export { Settings2 as LucideSettings2 }
export { Shapes as LucideShapes }
export { Share as LucideShare }
export { Share2 as LucideShare2 }
export { Sheet as LucideSheet }
export { Shell as LucideShell }
export { ShelvingUnit as LucideShelvingUnit }
export { Shield as LucideShield }
export { ShieldAlert as LucideShieldAlert }
export { ShieldBan as LucideShieldBan }
export { ShieldCheck as LucideShieldCheck }
export { ShieldX as LucideShieldClose }
export { ShieldCog as LucideShieldCog }
export { ShieldCogCorner as LucideShieldCogCorner }
export { ShieldEllipsis as LucideShieldEllipsis }
export { ShieldHalf as LucideShieldHalf }
export { ShieldKeyhole as LucideShieldKeyhole }
export { ShieldLock as LucideShieldLock }
export { ShieldMinus as LucideShieldMinus }
export { ShieldOff as LucideShieldOff }
export { ShieldPlus as LucideShieldPlus }
export { ShieldQuestionMark as LucideShieldQuestion }
export { ShieldQuestionMark as LucideShieldQuestionMark }
export { ShieldUser as LucideShieldUser }
export { ShieldX as LucideShieldX }
export { Ship as LucideShip }
export { ShipCargo as LucideShipCargo }
export { ShipWheel as LucideShipWheel }
export { Shirt as LucideShirt }
export { ShoppingBag as LucideShoppingBag }
export { ShoppingBasket as LucideShoppingBasket }
export { ShoppingCart as LucideShoppingCart }
export { Shovel as LucideShovel }
export { ShowerHead as LucideShowerHead }
export { Shredder as LucideShredder }
export { Shrimp as LucideShrimp }
export { Shrink as LucideShrink }
export { Shrub as LucideShrub }
export { Shuffle as LucideShuffle }
export { PanelLeft as LucideSidebar }
export { PanelLeftClose as LucideSidebarClose }
export { PanelLeftOpen as LucideSidebarOpen }
export { Sigma as LucideSigma }
export { SquareSigma as LucideSigmaSquare }
export { Signal as LucideSignal }
export { SignalHigh as LucideSignalHigh }
export { SignalLow as LucideSignalLow }
export { SignalMedium as LucideSignalMedium }
export { SignalZero as LucideSignalZero }
export { Signature as LucideSignature }
export { Signpost as LucideSignpost }
export { SignpostBig as LucideSignpostBig }
export { Siren as LucideSiren }
export { SkipBack as LucideSkipBack }
export { SkipForward as LucideSkipForward }
export { Skull as LucideSkull }
export { Slash as LucideSlash }
export { SquareSlash as LucideSlashSquare }
export { Slice as LucideSlice }
export { SlidersVertical as LucideSliders }
export { SlidersHorizontal as LucideSlidersHorizontal }
export { SlidersVertical as LucideSlidersVertical }
export { Smartphone as LucideSmartphone }
export { SmartphoneCharging as LucideSmartphoneCharging }
export { SmartphoneNfc as LucideSmartphoneNfc }
export { FaceSlightlySmiling as LucideSmile }
export { FaceSlightlySmilingPlus as LucideSmilePlus }
export { Snail as LucideSnail }
export { Snowflake as LucideSnowflake }
export { SoapDispenserDroplet as LucideSoapDispenserDroplet }
export { Sofa as LucideSofa }
export { SolarPanel as LucideSolarPanel }
export { ArrowUpNarrowWide as LucideSortAsc }
export { ArrowDownWideNarrow as LucideSortDesc }
export { Soup as LucideSoup }
export { Space as LucideSpace }
export { Spade as LucideSpade }
export { Sparkle as LucideSparkle }
export { Sparkles as LucideSparkles }
export { Speaker as LucideSpeaker }
export { Speech as LucideSpeech }
export { SpellCheck as LucideSpellCheck }
export { SpellCheck2 as LucideSpellCheck2 }
export { Spline as LucideSpline }
export { SplinePointer as LucideSplinePointer }
export { Split as LucideSplit }
export { SquareSplitHorizontal as LucideSplitSquareHorizontal }
export { SquareSplitVertical as LucideSplitSquareVertical }
export { Spool as LucideSpool }
export { SportShoe as LucideSportShoe }
export { Spotlight as LucideSpotlight }
export { SprayCan as LucideSprayCan }
export { Sprout as LucideSprout }
export { Square as LucideSquare }
export { SquareActivity as LucideSquareActivity }
export { SquareArrowDown as LucideSquareArrowDown }
export { SquareArrowDownLeft as LucideSquareArrowDownLeft }
export { SquareArrowDownRight as LucideSquareArrowDownRight }
export { SquareArrowLeft as LucideSquareArrowLeft }
export { SquareArrowOutDownLeft as LucideSquareArrowOutDownLeft }
export { SquareArrowOutDownRight as LucideSquareArrowOutDownRight }
export { SquareArrowOutUpLeft as LucideSquareArrowOutUpLeft }
export { SquareArrowOutUpRight as LucideSquareArrowOutUpRight }
export { SquareArrowRight as LucideSquareArrowRight }
export { SquareArrowRightEnter as LucideSquareArrowRightEnter }
export { SquareArrowRightExit as LucideSquareArrowRightExit }
export { SquareArrowUp as LucideSquareArrowUp }
export { SquareArrowUpLeft as LucideSquareArrowUpLeft }
export { SquareArrowUpRight as LucideSquareArrowUpRight }
export { SquareAsterisk as LucideSquareAsterisk }
export { SquareBottomDashedScissors as LucideSquareBottomDashedScissors }
export { SquareCenterlineDashedHorizontal as LucideSquareCenterlineDashedHorizontal }
export { SquareCenterlineDashedVertical as LucideSquareCenterlineDashedVertical }
export { SquareChartGantt as LucideSquareChartGantt }
export { SquareCheck as LucideSquareCheck }
export { SquareCheckBig as LucideSquareCheckBig }
export { SquareChevronDown as LucideSquareChevronDown }
export { SquareChevronLeft as LucideSquareChevronLeft }
export { SquareChevronRight as LucideSquareChevronRight }
export { SquareChevronUp as LucideSquareChevronUp }
export { SquareCode as LucideSquareCode }
export { SquareDashed as LucideSquareDashed }
export { SquareDashedBottom as LucideSquareDashedBottom }
export { SquareDashedBottomCode as LucideSquareDashedBottomCode }
export { SquareDashedKanban as LucideSquareDashedKanban }
export { SquareDashedMousePointer as LucideSquareDashedMousePointer }
export { SquareDashedText as LucideSquareDashedText }
export { SquareDashedTopSolid as LucideSquareDashedTopSolid }
export { SquareDimensions as LucideSquareDimensions }
export { SquareDivide as LucideSquareDivide }
export { SquareDot as LucideSquareDot }
export { SquareEqual as LucideSquareEqual }
export { SquareFunction as LucideSquareFunction }
export { SquareChartGantt as LucideSquareGanttChart }
export { SquareKanban as LucideSquareKanban }
export { SquareLibrary as LucideSquareLibrary }
export { SquareM as LucideSquareM }
export { SquareMenu as LucideSquareMenu }
export { SquareMinus as LucideSquareMinus }
export { SquareMousePointer as LucideSquareMousePointer }
export { SquareOff as LucideSquareOff }
export { SquareParking as LucideSquareParking }
export { SquareParkingOff as LucideSquareParkingOff }
export { SquarePause as LucideSquarePause }
export { SquarePen as LucideSquarePen }
export { SquarePercent as LucideSquarePercent }
export { SquarePi as LucideSquarePi }
export { SquarePilcrow as LucideSquarePilcrow }
export { SquarePlay as LucideSquarePlay }
export { SquarePlus as LucideSquarePlus }
export { SquarePower as LucideSquarePower }
export { SquareRadical as LucideSquareRadical }
export { SquareRoundCorner as LucideSquareRoundCorner }
export { SquareScissors as LucideSquareScissors }
export { SquareSigma as LucideSquareSigma }
export { SquareSlash as LucideSquareSlash }
export { SquareSplitHorizontal as LucideSquareSplitHorizontal }
export { SquareSplitVertical as LucideSquareSplitVertical }
export { SquareSquare as LucideSquareSquare }
export { SquareStack as LucideSquareStack }
export { SquareStar as LucideSquareStar }
export { SquareStop as LucideSquareStop }
export { SquareTerminal as LucideSquareTerminal }
export { SquareText as LucideSquareText }
export { SquareUser as LucideSquareUser }
export { SquareUserRound as LucideSquareUserRound }
export { SquareX as LucideSquareX }
export { SquaresExclude as LucideSquaresExclude }
export { SquaresIntersect as LucideSquaresIntersect }
export { SquaresSubtract as LucideSquaresSubtract }
export { SquaresUnite as LucideSquaresUnite }
export { Squircle as LucideSquircle }
export { SquircleDashed as LucideSquircleDashed }
export { Squirrel as LucideSquirrel }
export { Stamp as LucideStamp }
export { Star as LucideStar }
export { StarCheck as LucideStarCheck }
export { StarHalf as LucideStarHalf }
export { StarMinus as LucideStarMinus }
export { StarOff as LucideStarOff }
export { StarPlus as LucideStarPlus }
export { StarX as LucideStarX }
export { Sparkles as LucideStars }
export { StepBack as LucideStepBack }
export { StepForward as LucideStepForward }
export { Stethoscope as LucideStethoscope }
export { Sticker as LucideSticker }
export { StickyNote as LucideStickyNote }
export { StickyNoteCheck as LucideStickyNoteCheck }
export { StickyNoteMinus as LucideStickyNoteMinus }
export { StickyNoteOff as LucideStickyNoteOff }
export { StickyNotePlus as LucideStickyNotePlus }
export { StickyNoteX as LucideStickyNoteX }
export { StickyNotes as LucideStickyNotes }
export { Stone as LucideStone }
export { CircleStop as LucideStopCircle }
export { Store as LucideStore }
export { StretchHorizontal as LucideStretchHorizontal }
export { StretchVertical as LucideStretchVertical }
export { Strikethrough as LucideStrikethrough }
export { Subscript as LucideSubscript }
export { Captions as LucideSubtitles }
export { Summary as LucideSummary }
export { Sun as LucideSun }
export { SunDim as LucideSunDim }
export { SunMedium as LucideSunMedium }
export { SunMoon as LucideSunMoon }
export { SunSnow as LucideSunSnow }
export { Sunrise as LucideSunrise }
export { Sunset as LucideSunset }
export { Superscript as LucideSuperscript }
export { SwatchBook as LucideSwatchBook }
export { SwissFranc as LucideSwissFranc }
export { SwitchCamera as LucideSwitchCamera }
export { Sword as LucideSword }
export { Swords as LucideSwords }
export { Syringe as LucideSyringe }
export { Table as LucideTable }
export { Table2 as LucideTable2 }
export { TableCellsMerge as LucideTableCellsMerge }
export { TableCellsSplit as LucideTableCellsSplit }
export { TableColumnsSplit as LucideTableColumnsSplit }
export { Columns3Cog as LucideTableConfig }
export { TableOfContents as LucideTableOfContents }
export { TableProperties as LucideTableProperties }
export { TableRowsSplit as LucideTableRowsSplit }
export { Tablet as LucideTablet }
export { TabletSmartphone as LucideTabletSmartphone }
export { Tablets as LucideTablets }
export { Tag as LucideTag }
export { TagPlus as LucideTagPlus }
export { TagX as LucideTagX }
export { Tags as LucideTags }
export { Tally1 as LucideTally1 }
export { Tally2 as LucideTally2 }
export { Tally3 as LucideTally3 }
export { Tally4 as LucideTally4 }
export { Tally5 as LucideTally5 }
export { Tangent as LucideTangent }
export { Target as LucideTarget }
export { Telescope as LucideTelescope }
export { Tent as LucideTent }
export { TentTree as LucideTentTree }
export { Terminal as LucideTerminal }
export { SquareTerminal as LucideTerminalSquare }
export { TestTube as LucideTestTube }
export { TestTubeDiagonal as LucideTestTube2 }
export { TestTubeDiagonal as LucideTestTubeDiagonal }
export { TestTubes as LucideTestTubes }
export { TextAlignStart as LucideText }
export { TextAlignCenter as LucideTextAlignCenter }
export { TextAlignEnd as LucideTextAlignEnd }
export { TextAlignJustify as LucideTextAlignJustify }
export { TextAlignStart as LucideTextAlignStart }
export { TextCursor as LucideTextCursor }
export { TextCursorInput as LucideTextCursorInput }
export { TextInitial as LucideTextInitial }
export { TextQuote as LucideTextQuote }
export { TextSearch as LucideTextSearch }
export { SquareDashedText as LucideTextSelect }
export { SquareDashedText as LucideTextSelection }
export { TextWrap as LucideTextWrap }
export { Theater as LucideTheater }
export { Thermometer as LucideThermometer }
export { ThermometerSnowflake as LucideThermometerSnowflake }
export { ThermometerSun as LucideThermometerSun }
export { ThumbsDown as LucideThumbsDown }
export { ThumbsUp as LucideThumbsUp }
export { Ticket as LucideTicket }
export { TicketCheck as LucideTicketCheck }
export { TicketMinus as LucideTicketMinus }
export { TicketPercent as LucideTicketPercent }
export { TicketPlus as LucideTicketPlus }
export { TicketSlash as LucideTicketSlash }
export { TicketX as LucideTicketX }
export { Tickets as LucideTickets }
export { TicketsPlane as LucideTicketsPlane }
export { Timeline as LucideTimeline }
export { Timer as LucideTimer }
export { TimerOff as LucideTimerOff }
export { TimerReset as LucideTimerReset }
export { ToggleLeft as LucideToggleLeft }
export { ToggleRight as LucideToggleRight }
export { Toilet as LucideToilet }
export { ToolCase as LucideToolCase }
export { Toolbox as LucideToolbox }
export { Tornado as LucideTornado }
export { Torus as LucideTorus }
export { Touchpad as LucideTouchpad }
export { TouchpadOff as LucideTouchpadOff }
export { TowelRack as LucideTowelRack }
export { TowerControl as LucideTowerControl }
export { ToyBrick as LucideToyBrick }
export { Tractor as LucideTractor }
export { TrafficCone as LucideTrafficCone }
export { Trailer as LucideTrailer }
export { TramFront as LucideTrain }
export { TrainFront as LucideTrainFront }
export { TrainFrontTunnel as LucideTrainFrontTunnel }
export { TrainTrack as LucideTrainTrack }
export { TramFront as LucideTramFront }
export { Transgender as LucideTransgender }
export { Trash as LucideTrash }
export { Trash2 as LucideTrash2 }
export { TreeDeciduous as LucideTreeDeciduous }
export { TreePalm as LucideTreePalm }
export { TreePine as LucideTreePine }
export { Trees as LucideTrees }
export { TrendingDown as LucideTrendingDown }
export { TrendingUp as LucideTrendingUp }
export { TrendingUpDown as LucideTrendingUpDown }
export { Triangle as LucideTriangle }
export { TriangleAlert as LucideTriangleAlert }
export { TriangleDashed as LucideTriangleDashed }
export { TriangleRight as LucideTriangleRight }
export { Trophy as LucideTrophy }
export { Truck as LucideTruck }
export { TruckElectric as LucideTruckElectric }
export { TurkishLira as LucideTurkishLira }
export { Turntable as LucideTurntable }
export { Turtle as LucideTurtle }
export { Tv as LucideTv }
export { TvMinimal as LucideTv2 }
export { TvMinimal as LucideTvMinimal }
export { TvMinimalPlay as LucideTvMinimalPlay }
export { Type as LucideType }
export { TypeOutline as LucideTypeOutline }
export { Umbrella as LucideUmbrella }
export { UmbrellaOff as LucideUmbrellaOff }
export { Underline as LucideUnderline }
export { Undo as LucideUndo }
export { Undo2 as LucideUndo2 }
export { UndoDot as LucideUndoDot }
export { UnfoldHorizontal as LucideUnfoldHorizontal }
export { UnfoldVertical as LucideUnfoldVertical }
export { Ungroup as LucideUngroup }
export { University as LucideUniversity }
export { Unlink as LucideUnlink }
export { Unlink2 as LucideUnlink2 }
export { LockOpen as LucideUnlock }
export { LockKeyholeOpen as LucideUnlockKeyhole }
export { Unplug as LucideUnplug }
export { Upload as LucideUpload }
export { CloudUpload as LucideUploadCloud }
export { Usb as LucideUsb }
export { UsbCPort as LucideUsbCPort }
export { User as LucideUser }
export { UserRound as LucideUser2 }
export { UserCheck as LucideUserCheck }
export { UserRoundCheck as LucideUserCheck2 }
export { CircleUser as LucideUserCircle }
export { CircleUserRound as LucideUserCircle2 }
export { UserCog as LucideUserCog }
export { UserRoundCog as LucideUserCog2 }
export { UserKey as LucideUserKey }
export { UserLock as LucideUserLock }
export { UserMinus as LucideUserMinus }
export { UserRoundMinus as LucideUserMinus2 }
export { UserPen as LucideUserPen }
export { UserPlus as LucideUserPlus }
export { UserRoundPlus as LucideUserPlus2 }
export { UserRound as LucideUserRound }
export { UserRoundArrowLeft as LucideUserRoundArrowLeft }
export { UserRoundCheck as LucideUserRoundCheck }
export { UserRoundCog as LucideUserRoundCog }
export { UserRoundKey as LucideUserRoundKey }
export { UserRoundMinus as LucideUserRoundMinus }
export { UserRoundPen as LucideUserRoundPen }
export { UserRoundPlus as LucideUserRoundPlus }
export { UserRoundSearch as LucideUserRoundSearch }
export { UserRoundX as LucideUserRoundX }
export { UserSearch as LucideUserSearch }
export { UserShield as LucideUserShield }
export { SquareUser as LucideUserSquare }
export { SquareUserRound as LucideUserSquare2 }
export { UserStar as LucideUserStar }
export { UserX as LucideUserX }
export { UserRoundX as LucideUserX2 }
export { Users as LucideUsers }
export { UsersRound as LucideUsers2 }
export { UsersRound as LucideUsersRound }
export { Utensils as LucideUtensils }
export { UtensilsCrossed as LucideUtensilsCrossed }
export { UtilityPole as LucideUtilityPole }
export { Van as LucideVan }
export { Variable as LucideVariable }
export { Vault as LucideVault }
export { VectorSquare as LucideVectorSquare }
export { Vegan as LucideVegan }
export { VenetianMask as LucideVenetianMask }
export { Venus as LucideVenus }
export { VenusAndMars as LucideVenusAndMars }
export { BadgeCheck as LucideVerified }
export { Vibrate as LucideVibrate }
export { VibrateOff as LucideVibrateOff }
export { Video as LucideVideo }
export { VideoOff as LucideVideoOff }
export { Videotape as LucideVideotape }
export { View as LucideView }
export { Voicemail as LucideVoicemail }
export { Volleyball as LucideVolleyball }
export { Volume as LucideVolume }
export { Volume1 as LucideVolume1 }
export { Volume2 as LucideVolume2 }
export { VolumeOff as LucideVolumeOff }
export { VolumeX as LucideVolumeX }
export { Vote as LucideVote }
export { Wallet as LucideWallet }
export { WalletMinimal as LucideWallet2 }
export { WalletCards as LucideWalletCards }
export { WalletMinimal as LucideWalletMinimal }
export { Wallpaper as LucideWallpaper }
export { Wand as LucideWand }
export { WandSparkles as LucideWand2 }
export { WandSparkles as LucideWandSparkles }
export { Warehouse as LucideWarehouse }
export { WashingMachine as LucideWashingMachine }
export { Watch as LucideWatch }
export { WavesHorizontal as LucideWaves }
export { WavesArrowDown as LucideWavesArrowDown }
export { WavesArrowUp as LucideWavesArrowUp }
export { WavesHorizontal as LucideWavesHorizontal }
export { WavesLadder as LucideWavesLadder }
export { WavesVertical as LucideWavesVertical }
export { Waypoints as LucideWaypoints }
export { Webcam as LucideWebcam }
export { WebcamOff as LucideWebcamOff }
export { Webhook as LucideWebhook }
export { WebhookOff as LucideWebhookOff }
export { Weight as LucideWeight }
export { WeightTilde as LucideWeightTilde }
export { Wheat as LucideWheat }
export { WheatOff as LucideWheatOff }
export { WholeWord as LucideWholeWord }
export { Wifi as LucideWifi }
export { WifiCog as LucideWifiCog }
export { WifiHigh as LucideWifiHigh }
export { WifiLow as LucideWifiLow }
export { WifiOff as LucideWifiOff }
export { WifiPen as LucideWifiPen }
export { WifiSync as LucideWifiSync }
export { WifiZero as LucideWifiZero }
export { Wind as LucideWind }
export { WindArrowDown as LucideWindArrowDown }
export { Wine as LucideWine }
export { WineOff as LucideWineOff }
export { Workflow as LucideWorkflow }
export { Worm as LucideWorm }
export { TextWrap as LucideWrapText }
export { Wrench as LucideWrench }
export { WrenchOff as LucideWrenchOff }
export { X as LucideX }
export { CircleX as LucideXCircle }
export { XLineTop as LucideXLineTop }
export { OctagonX as LucideXOctagon }
export { SquareX as LucideXSquare }
export { Zap as LucideZap }
export { ZapOff as LucideZapOff }
export { ZodiacAquarius as LucideZodiacAquarius }
export { ZodiacAries as LucideZodiacAries }
export { ZodiacCancer as LucideZodiacCancer }
export { ZodiacCapricorn as LucideZodiacCapricorn }
export { ZodiacGemini as LucideZodiacGemini }
export { ZodiacLeo as LucideZodiacLeo }
export { ZodiacLibra as LucideZodiacLibra }
export { ZodiacOphiuchus as LucideZodiacOphiuchus }
export { ZodiacPisces as LucideZodiacPisces }
export { ZodiacSagittarius as LucideZodiacSagittarius }
export { ZodiacScorpio as LucideZodiacScorpio }
export { ZodiacTaurus as LucideZodiacTaurus }
export { ZodiacVirgo as LucideZodiacVirgo }
export { ZoomIn as LucideZoomIn }
export { ZoomOut as LucideZoomOut }
export { Luggage as LuggageIcon }
export { SquareM as MSquare }
export { SquareM as MSquareIcon }
export { Magnet as MagnetIcon }
export { MailBadge as MailBadgeIcon }
export { MailCheck as MailCheckIcon }
export { MailClock as MailClockIcon }
export { Mail as MailIcon }
export { MailMinus as MailMinusIcon }
export { MailOpen as MailOpenIcon }
export { MailPlus as MailPlusIcon }
export { MailQuestionMark as MailQuestion }
export { MailQuestionMark as MailQuestionIcon }
export { MailQuestionMark as MailQuestionMarkIcon }
export { MailSearch as MailSearchIcon }
export { MailWarning as MailWarningIcon }
export { MailX as MailXIcon }
export { Mailbox as MailboxIcon }
export { Mails as MailsIcon }
export { Map as MapIcon }
export { MapMinus as MapMinusIcon }
export { MapPinCheck as MapPinCheckIcon }
export { MapPinCheckInside as MapPinCheckInsideIcon }
export { MapPinHouse as MapPinHouseIcon }
export { MapPin as MapPinIcon }
export { MapPinMinus as MapPinMinusIcon }
export { MapPinMinusInside as MapPinMinusInsideIcon }
export { MapPinOff as MapPinOffIcon }
export { MapPinPen as MapPinPenIcon }
export { MapPinPlus as MapPinPlusIcon }
export { MapPinPlusInside as MapPinPlusInsideIcon }
export { MapPinSearch as MapPinSearchIcon }
export { MapPinX as MapPinXIcon }
export { MapPinXInside as MapPinXInsideIcon }
export { MapPinned as MapPinnedIcon }
export { MapPlus as MapPlusIcon }
export { Mars as MarsIcon }
export { MarsStroke as MarsStrokeIcon }
export { Martini as MartiniIcon }
export { Maximize2 as Maximize2Icon }
export { Maximize as MaximizeIcon }
export { Medal as MedalIcon }
export { Megaphone as MegaphoneIcon }
export { MegaphoneOff as MegaphoneOffIcon }
export { FaceNeutral as Meh }
export { FaceNeutral as MehIcon }
export { MemoryStick as MemoryStickIcon }
export { Menu as MenuIcon }
export { SquareMenu as MenuSquare }
export { SquareMenu as MenuSquareIcon }
export { Merge as MergeIcon }
export { MessageCircleCheck as MessageCircleCheckIcon }
export { MessageCircleCode as MessageCircleCodeIcon }
export { MessageCircleDashedCheck as MessageCircleDashedCheckIcon }
export { MessageCircleDashed as MessageCircleDashedIcon }
export { MessageCircleHeart as MessageCircleHeartIcon }
export { MessageCircle as MessageCircleIcon }
export { MessageCircleMore as MessageCircleMoreIcon }
export { MessageCircleOff as MessageCircleOffIcon }
export { MessageCirclePlus as MessageCirclePlusIcon }
export { MessageCircleQuestionMark as MessageCircleQuestion }
export { MessageCircleQuestionMark as MessageCircleQuestionIcon }
export { MessageCircleQuestionMark as MessageCircleQuestionMarkIcon }
export { MessageCircleReply as MessageCircleReplyIcon }
export { MessageCircleWarning as MessageCircleWarningIcon }
export { MessageCircleX as MessageCircleXIcon }
export { MessageSquareCheck as MessageSquareCheckIcon }
export { MessageSquareCode as MessageSquareCodeIcon }
export { MessageSquareDashed as MessageSquareDashedIcon }
export { MessageSquareDiff as MessageSquareDiffIcon }
export { MessageSquareDot as MessageSquareDotIcon }
export { MessageSquareHeart as MessageSquareHeartIcon }
export { MessageSquare as MessageSquareIcon }
export { MessageSquareLock as MessageSquareLockIcon }
export { MessageSquareMore as MessageSquareMoreIcon }
export { MessageSquareOff as MessageSquareOffIcon }
export { MessageSquarePlus as MessageSquarePlusIcon }
export { MessageSquareQuote as MessageSquareQuoteIcon }
export { MessageSquareReply as MessageSquareReplyIcon }
export { MessageSquareShare as MessageSquareShareIcon }
export { MessageSquareText as MessageSquareTextIcon }
export { MessageSquareWarning as MessageSquareWarningIcon }
export { MessageSquareX as MessageSquareXIcon }
export { MessagesSquare as MessagesSquareIcon }
export { Metronome as MetronomeIcon }
export { MicVocal as Mic2 }
export { MicVocal as Mic2Icon }
export { MicAudioLines as MicAudioLinesIcon }
export { Mic as MicIcon }
export { MicOff as MicOffIcon }
export { MicSignal as MicSignalIcon }
export { MicVocal as MicVocalIcon }
export { Microchip as MicrochipIcon }
export { Microscope as MicroscopeIcon }
export { Microwave as MicrowaveIcon }
export { MidiPort as MidiPortIcon }
export { Milestone as MilestoneIcon }
export { Milk as MilkIcon }
export { MilkOff as MilkOffIcon }
export { Minimize2 as Minimize2Icon }
export { Minimize as MinimizeIcon }
export { CircleMinus as MinusCircle }
export { CircleMinus as MinusCircleIcon }
export { Minus as MinusIcon }
export { SquareMinus as MinusSquare }
export { SquareMinus as MinusSquareIcon }
export { MirrorRectangular as MirrorRectangularIcon }
export { MirrorRound as MirrorRoundIcon }
export { MonitorCheck as MonitorCheckIcon }
export { MonitorCloud as MonitorCloudIcon }
export { MonitorCog as MonitorCogIcon }
export { MonitorDot as MonitorDotIcon }
export { MonitorDown as MonitorDownIcon }
export { Monitor as MonitorIcon }
export { MonitorOff as MonitorOffIcon }
export { MonitorPause as MonitorPauseIcon }
export { MonitorPlay as MonitorPlayIcon }
export { MonitorSmartphone as MonitorSmartphoneIcon }
export { MonitorSpeaker as MonitorSpeakerIcon }
export { MonitorStop as MonitorStopIcon }
export { MonitorUp as MonitorUpIcon }
export { MonitorX as MonitorXIcon }
export { Moon as MoonIcon }
export { MoonStar as MoonStarIcon }
export { Mop as MopIcon }
export { MopSparkles as MopSparklesIcon }
export { Ellipsis as MoreHorizontal }
export { Ellipsis as MoreHorizontalIcon }
export { EllipsisVertical as MoreVertical }
export { EllipsisVertical as MoreVerticalIcon }
export { Mosque as MosqueIcon }
export { Motorbike as MotorbikeIcon }
export { Mountain as MountainIcon }
export { MountainSnow as MountainSnowIcon }
export { Mouse as MouseIcon }
export { MouseLeft as MouseLeftIcon }
export { MouseOff as MouseOffIcon }
export { MousePointer2 as MousePointer2Icon }
export { MousePointer2Off as MousePointer2OffIcon }
export { MousePointerBan as MousePointerBanIcon }
export { MousePointerClick as MousePointerClickIcon }
export { MousePointer as MousePointerIcon }
export { SquareDashedMousePointer as MousePointerSquareDashed }
export { SquareDashedMousePointer as MousePointerSquareDashedIcon }
export { MouseRight as MouseRightIcon }
export { Move3d as Move3D }
export { Move3d as Move3DIcon }
export { Move3d as Move3dIcon }
export { MoveDiagonal2 as MoveDiagonal2Icon }
export { MoveDiagonal as MoveDiagonalIcon }
export { MoveDown as MoveDownIcon }
export { MoveDownLeft as MoveDownLeftIcon }
export { MoveDownRight as MoveDownRightIcon }
export { MoveHorizontal as MoveHorizontalIcon }
export { Move as MoveIcon }
export { MoveLeft as MoveLeftIcon }
export { MoveRight as MoveRightIcon }
export { MoveUp as MoveUpIcon }
export { MoveUpLeft as MoveUpLeftIcon }
export { MoveUpRight as MoveUpRightIcon }
export { MoveVertical as MoveVerticalIcon }
export { Music2 as Music2Icon }
export { Music3 as Music3Icon }
export { Music4 as Music4Icon }
export { Music as MusicIcon }
export { Navigation2 as Navigation2Icon }
export { Navigation2Off as Navigation2OffIcon }
export { Navigation as NavigationIcon }
export { NavigationOff as NavigationOffIcon }
export { Network as NetworkIcon }
export { Newspaper as NewspaperIcon }
export { Nfc as NfcIcon }
export { NonBinary as NonBinaryIcon }
export { Notebook as NotebookIcon }
export { NotebookPen as NotebookPenIcon }
export { NotebookTabs as NotebookTabsIcon }
export { NotebookText as NotebookTextIcon }
export { NotepadTextDashed as NotepadTextDashedIcon }
export { NotepadText as NotepadTextIcon }
export { Nut as NutIcon }
export { NutOff as NutOffIcon }
export { OctagonAlert as OctagonAlertIcon }
export { Octagon as OctagonIcon }
export { OctagonMinus as OctagonMinusIcon }
export { OctagonPause as OctagonPauseIcon }
export { OctagonX as OctagonXIcon }
export { Omega as OmegaIcon }
export { Option as OptionIcon }
export { Orbit as OrbitIcon }
export { Origami as OrigamiIcon }
export { ListIndentDecrease as Outdent }
export { ListIndentDecrease as OutdentIcon }
export { Package2 as Package2Icon }
export { PackageCheck as PackageCheckIcon }
export { Package as PackageIcon }
export { PackageMinus as PackageMinusIcon }
export { PackageOpen as PackageOpenIcon }
export { PackagePlus as PackagePlusIcon }
export { PackageSearch as PackageSearchIcon }
export { PackageX as PackageXIcon }
export { PaintBucket as PaintBucketIcon }
export { PaintRoller as PaintRollerIcon }
export { PaintbrushVertical as Paintbrush2 }
export { PaintbrushVertical as Paintbrush2Icon }
export { Paintbrush as PaintbrushIcon }
export { PaintbrushVertical as PaintbrushVerticalIcon }
export { Palette as PaletteIcon }
export { TreePalm as Palmtree }
export { TreePalm as PalmtreeIcon }
export { Panda as PandaIcon }
export { PanelBottomClose as PanelBottomCloseIcon }
export { PanelBottomDashed as PanelBottomDashedIcon }
export { PanelBottom as PanelBottomIcon }
export { PanelBottomDashed as PanelBottomInactive }
export { PanelBottomDashed as PanelBottomInactiveIcon }
export { PanelBottomOpen as PanelBottomOpenIcon }
export { PanelLeftClose as PanelLeftCloseIcon }
export { PanelLeftDashed as PanelLeftDashedIcon }
export { PanelLeft as PanelLeftIcon }
export { PanelLeftDashed as PanelLeftInactive }
export { PanelLeftDashed as PanelLeftInactiveIcon }
export { PanelLeftOpen as PanelLeftOpenIcon }
export { PanelLeftRightDashed as PanelLeftRightDashedIcon }
export { PanelRightClose as PanelRightCloseIcon }
export { PanelRightDashed as PanelRightDashedIcon }
export { PanelRight as PanelRightIcon }
export { PanelRightDashed as PanelRightInactive }
export { PanelRightDashed as PanelRightInactiveIcon }
export { PanelRightOpen as PanelRightOpenIcon }
export { PanelTopBottomDashed as PanelTopBottomDashedIcon }
export { PanelTopClose as PanelTopCloseIcon }
export { PanelTopDashed as PanelTopDashedIcon }
export { PanelTop as PanelTopIcon }
export { PanelTopDashed as PanelTopInactive }
export { PanelTopDashed as PanelTopInactiveIcon }
export { PanelTopOpen as PanelTopOpenIcon }
export { PanelsLeftBottom as PanelsLeftBottomIcon }
export { Columns3 as PanelsLeftRight }
export { Columns3 as PanelsLeftRightIcon }
export { PanelsRightBottom as PanelsRightBottomIcon }
export { Rows3 as PanelsTopBottom }
export { Rows3 as PanelsTopBottomIcon }
export { PanelsTopLeft as PanelsTopLeftIcon }
export { PaperBag as PaperBagIcon }
export { Paperclip as PaperclipIcon }
export { Parasol as ParasolIcon }
export { Parentheses as ParenthesesIcon }
export { CircleParking as ParkingCircle }
export { CircleParking as ParkingCircleIcon }
export { CircleParkingOff as ParkingCircleOff }
export { CircleParkingOff as ParkingCircleOffIcon }
export { ParkingMeter as ParkingMeterIcon }
export { SquareParking as ParkingSquare }
export { SquareParking as ParkingSquareIcon }
export { SquareParkingOff as ParkingSquareOff }
export { SquareParkingOff as ParkingSquareOffIcon }
export { PartyPopper as PartyPopperIcon }
export { CirclePause as PauseCircle }
export { CirclePause as PauseCircleIcon }
export { Pause as PauseIcon }
export { OctagonPause as PauseOctagon }
export { OctagonPause as PauseOctagonIcon }
export { PawPrint as PawPrintIcon }
export { PcCase as PcCaseIcon }
export { SquarePen as PenBox }
export { SquarePen as PenBoxIcon }
export { Pen as PenIcon }
export { PenLine as PenLineIcon }
export { PenOff as PenOffIcon }
export { SquarePen as PenSquare }
export { SquarePen as PenSquareIcon }
export { PenTool as PenToolIcon }
export { Pencil as PencilIcon }
export { PencilLine as PencilLineIcon }
export { PencilOff as PencilOffIcon }
export { PencilRuler as PencilRulerIcon }
export { PencilSparkles as PencilSparklesIcon }
export { Pentagon as PentagonIcon }
export { CirclePercent as PercentCircle }
export { CirclePercent as PercentCircleIcon }
export { DiamondPercent as PercentDiamond }
export { DiamondPercent as PercentDiamondIcon }
export { Percent as PercentIcon }
export { SquarePercent as PercentSquare }
export { SquarePercent as PercentSquareIcon }
export { PersonStanding as PersonStandingIcon }
export { Phi as PhiIcon }
export { PhilippinePeso as PhilippinePesoIcon }
export { PhoneCall as PhoneCallIcon }
export { PhoneForwarded as PhoneForwardedIcon }
export { Phone as PhoneIcon }
export { PhoneIncoming as PhoneIncomingIcon }
export { PhoneMissed as PhoneMissedIcon }
export { PhoneOff as PhoneOffIcon }
export { PhoneOutgoing as PhoneOutgoingIcon }
export { Pi as PiIcon }
export { SquarePi as PiSquare }
export { SquarePi as PiSquareIcon }
export { Piano as PianoIcon }
export { Pickaxe as PickaxeIcon }
export { PictureInPicture2 as PictureInPicture2Icon }
export { PictureInPicture as PictureInPictureIcon }
export { ChartPie as PieChart }
export { ChartPie as PieChartIcon }
export { PiggyBank as PiggyBankIcon }
export { Pilcrow as PilcrowIcon }
export { PilcrowLeft as PilcrowLeftIcon }
export { PilcrowRight as PilcrowRightIcon }
export { SquarePilcrow as PilcrowSquare }
export { SquarePilcrow as PilcrowSquareIcon }
export { PillBottle as PillBottleIcon }
export { Pill as PillIcon }
export { Pin as PinIcon }
export { PinOff as PinOffIcon }
export { Pipette as PipetteIcon }
export { Pizza as PizzaIcon }
export { Plane as PlaneIcon }
export { PlaneLanding as PlaneLandingIcon }
export { PlaneTakeoff as PlaneTakeoffIcon }
export { CirclePlay as PlayCircle }
export { CirclePlay as PlayCircleIcon }
export { Play as PlayIcon }
export { PlayOff as PlayOffIcon }
export { SquarePlay as PlaySquare }
export { SquarePlay as PlaySquareIcon }
export { PlayingCard as PlayingCardIcon }
export { PlayingCardsFan as PlayingCardsFanIcon }
export { PlayingCards as PlayingCardsIcon }
export { Plug2 as Plug2Icon }
export { Plug as PlugIcon }
export { PlugZap as PlugZap2 }
export { PlugZap as PlugZap2Icon }
export { PlugZap as PlugZapIcon }
export { CirclePlus as PlusCircle }
export { CirclePlus as PlusCircleIcon }
export { Plus as PlusIcon }
export { SquarePlus as PlusSquare }
export { SquarePlus as PlusSquareIcon }
export { PocketKnife as PocketKnifeIcon }
export { MicSignal as Podcast }
export { MicSignal as PodcastIcon }
export { Podium as PodiumIcon }
export { Pointer as PointerIcon }
export { PointerOff as PointerOffIcon }
export { Popcorn as PopcornIcon }
export { Popsicle as PopsicleIcon }
export { PoundSterling as PoundSterlingIcon }
export { CirclePower as PowerCircle }
export { CirclePower as PowerCircleIcon }
export { Power as PowerIcon }
export { PowerOff as PowerOffIcon }
export { SquarePower as PowerSquare }
export { SquarePower as PowerSquareIcon }
export { Presentation as PresentationIcon }
export { PrinterCheck as PrinterCheckIcon }
export { Printer as PrinterIcon }
export { PrinterX as PrinterXIcon }
export { Projector as ProjectorIcon }
export { Proportions as ProportionsIcon }
export { Puzzle as PuzzleIcon }
export { Pyramid as PyramidIcon }
export { QrCode as QrCodeIcon }
export { Quote as QuoteIcon }
export { Rabbit as RabbitIcon }
export { Radar as RadarIcon }
export { Radiation as RadiationIcon }
export { Radical as RadicalIcon }
export { Radio as RadioIcon }
export { RadioOff as RadioOffIcon }
export { RadioReceiver as RadioReceiverIcon }
export { RadioTower as RadioTowerIcon }
export { Radius as RadiusIcon }
export { Rainbow as RainbowIcon }
export { Rat as RatIcon }
export { Ratio as RatioIcon }
export { ReceiptCent as ReceiptCentIcon }
export { ReceiptEuro as ReceiptEuroIcon }
export { Receipt as ReceiptIcon }
export { ReceiptIndianRupee as ReceiptIndianRupeeIcon }
export { ReceiptJapaneseYen as ReceiptJapaneseYenIcon }
export { ReceiptPoundSterling as ReceiptPoundSterlingIcon }
export { ReceiptRussianRuble as ReceiptRussianRubleIcon }
export { ReceiptSwissFranc as ReceiptSwissFrancIcon }
export { ReceiptText as ReceiptTextIcon }
export { ReceiptTurkishLira as ReceiptTurkishLiraIcon }
export { RectangleCircle as RectangleCircleIcon }
export { RectangleEllipsis as RectangleEllipsisIcon }
export { RectangleGoggles as RectangleGogglesIcon }
export { RectangleHorizontal as RectangleHorizontalIcon }
export { RectangleVertical as RectangleVerticalIcon }
export { Recycle as RecycleIcon }
export { Redo2 as Redo2Icon }
export { RedoDot as RedoDotIcon }
export { Redo as RedoIcon }
export { RefreshCcwDot as RefreshCcwDotIcon }
export { RefreshCcw as RefreshCcwIcon }
export { RefreshCw as RefreshCwIcon }
export { RefreshCwOff as RefreshCwOffIcon }
export { Refrigerator as RefrigeratorIcon }
export { Regex as RegexIcon }
export { RemoveFormatting as RemoveFormattingIcon }
export { Repeat1 as Repeat1Icon }
export { Repeat2 as Repeat2Icon }
export { Repeat as RepeatIcon }
export { RepeatOff as RepeatOffIcon }
export { ReplaceAll as ReplaceAllIcon }
export { Replace as ReplaceIcon }
export { ReplyAll as ReplyAllIcon }
export { Reply as ReplyIcon }
export { Rewind as RewindIcon }
export { Ribbon as RibbonIcon }
export { Road as RoadIcon }
export { RobotArm as RobotArmIcon }
export { RobotVacuum as RobotVacuumIcon }
export { Rocket as RocketIcon }
export { RockingChair as RockingChairIcon }
export { RollerCoaster as RollerCoasterIcon }
export { Rose as RoseIcon }
export { Rotate3d as Rotate3D }
export { Rotate3d as Rotate3DIcon }
export { Rotate3d as Rotate3dIcon }
export { RotateCcwClock as RotateCcwClockIcon }
export { RotateCcw as RotateCcwIcon }
export { RotateCcwKey as RotateCcwKeyIcon }
export { RotateCcwSquare as RotateCcwSquareIcon }
export { RotateCwFadingClock as RotateCwFadingClockIcon }
export { RotateCw as RotateCwIcon }
export { RotateCwSquare as RotateCwSquareIcon }
export { Route as RouteIcon }
export { RouteOff as RouteOffIcon }
export { Router as RouterIcon }
export { Rows2 as Rows }
export { Rows2 as Rows2Icon }
export { Rows3 as Rows3Icon }
export { Rows4 as Rows4Icon }
export { Rows2 as RowsIcon }
export { Rss as RssIcon }
export { RulerDimensionLine as RulerDimensionLineIcon }
export { Ruler as RulerIcon }
export { RussianRuble as RussianRubleIcon }
export { Sailboat as SailboatIcon }
export { Salad as SaladIcon }
export { Sandwich as SandwichIcon }
export { SatelliteDish as SatelliteDishIcon }
export { Satellite as SatelliteIcon }
export { SaudiRiyal as SaudiRiyalIcon }
export { SaveAll as SaveAllIcon }
export { SaveCheck as SaveCheckIcon }
export { Save as SaveIcon }
export { SaveOff as SaveOffIcon }
export { SavePen as SavePenIcon }
export { SavePlus as SavePlusIcon }
export { Scale3d as Scale3D }
export { Scale3d as Scale3DIcon }
export { Scale3d as Scale3dIcon }
export { Scale as ScaleIcon }
export { Scaling as ScalingIcon }
export { ScanBarcode as ScanBarcodeIcon }
export { ScanBox as ScanBoxIcon }
export { ScanEye as ScanEyeIcon }
export { ScanFace as ScanFaceIcon }
export { ScanHeart as ScanHeartIcon }
export { Scan as ScanIcon }
export { ScanLine as ScanLineIcon }
export { ScanQrCode as ScanQrCodeIcon }
export { ScanSearch as ScanSearchIcon }
export { ScanSquare as ScanSquareIcon }
export { ScanText as ScanTextIcon }
export { ChartScatter as ScatterChart }
export { ChartScatter as ScatterChartIcon }
export { University as School2 }
export { University as School2Icon }
export { School as SchoolIcon }
export { Scissors as ScissorsIcon }
export { ScissorsLineDashed as ScissorsLineDashedIcon }
export { SquareScissors as ScissorsSquare }
export { SquareBottomDashedScissors as ScissorsSquareDashedBottom }
export { SquareBottomDashedScissors as ScissorsSquareDashedBottomIcon }
export { SquareScissors as ScissorsSquareIcon }
export { Scooter as ScooterIcon }
export { ScreenShare as ScreenShareIcon }
export { ScreenShareOff as ScreenShareOffIcon }
export { Scroll as ScrollIcon }
export { ScrollText as ScrollTextIcon }
export { SearchAlert as SearchAlertIcon }
export { SearchCheck as SearchCheckIcon }
export { SearchCode as SearchCodeIcon }
export { Search as SearchIcon }
export { SearchSlash as SearchSlashIcon }
export { SearchX as SearchXIcon }
export { Section as SectionIcon }
export { SendHorizontal as SendHorizonal }
export { SendHorizontal as SendHorizonalIcon }
export { SendHorizontal as SendHorizontalIcon }
export { Send as SendIcon }
export { SendToBack as SendToBackIcon }
export { SeparatorHorizontal as SeparatorHorizontalIcon }
export { SeparatorVertical as SeparatorVerticalIcon }
export { ServerCog as ServerCogIcon }
export { ServerCrash as ServerCrashIcon }
export { Server as ServerIcon }
export { ServerOff as ServerOffIcon }
export { ServerPlus as ServerPlusIcon }
export { Settings2 as Settings2Icon }
export { Settings as SettingsIcon }
export { Shapes as ShapesIcon }
export { Share2 as Share2Icon }
export { Share as ShareIcon }
export { Sheet as SheetIcon }
export { Shell as ShellIcon }
export { ShelvingUnit as ShelvingUnitIcon }
export { ShieldAlert as ShieldAlertIcon }
export { ShieldBan as ShieldBanIcon }
export { ShieldCheck as ShieldCheckIcon }
export { ShieldX as ShieldClose }
export { ShieldX as ShieldCloseIcon }
export { ShieldCogCorner as ShieldCogCornerIcon }
export { ShieldCog as ShieldCogIcon }
export { ShieldEllipsis as ShieldEllipsisIcon }
export { ShieldHalf as ShieldHalfIcon }
export { Shield as ShieldIcon }
export { ShieldKeyhole as ShieldKeyholeIcon }
export { ShieldLock as ShieldLockIcon }
export { ShieldMinus as ShieldMinusIcon }
export { ShieldOff as ShieldOffIcon }
export { ShieldPlus as ShieldPlusIcon }
export { ShieldQuestionMark as ShieldQuestion }
export { ShieldQuestionMark as ShieldQuestionIcon }
export { ShieldQuestionMark as ShieldQuestionMarkIcon }
export { ShieldUser as ShieldUserIcon }
export { ShieldX as ShieldXIcon }
export { ShipCargo as ShipCargoIcon }
export { Ship as ShipIcon }
export { ShipWheel as ShipWheelIcon }
export { Shirt as ShirtIcon }
export { ShoppingBag as ShoppingBagIcon }
export { ShoppingBasket as ShoppingBasketIcon }
export { ShoppingCart as ShoppingCartIcon }
export { Shovel as ShovelIcon }
export { ShowerHead as ShowerHeadIcon }
export { Shredder as ShredderIcon }
export { Shrimp as ShrimpIcon }
export { Shrink as ShrinkIcon }
export { Shrub as ShrubIcon }
export { Shuffle as ShuffleIcon }
export { PanelLeft as Sidebar }
export { PanelLeftClose as SidebarClose }
export { PanelLeftClose as SidebarCloseIcon }
export { PanelLeft as SidebarIcon }
export { PanelLeftOpen as SidebarOpen }
export { PanelLeftOpen as SidebarOpenIcon }
export { Sigma as SigmaIcon }
export { SquareSigma as SigmaSquare }
export { SquareSigma as SigmaSquareIcon }
export { SignalHigh as SignalHighIcon }
export { Signal as SignalIcon }
export { SignalLow as SignalLowIcon }
export { SignalMedium as SignalMediumIcon }
export { SignalZero as SignalZeroIcon }
export { Signature as SignatureIcon }
export { SignpostBig as SignpostBigIcon }
export { Signpost as SignpostIcon }
export { Siren as SirenIcon }
export { SkipBack as SkipBackIcon }
export { SkipForward as SkipForwardIcon }
export { Skull as SkullIcon }
export { Slash as SlashIcon }
export { SquareSlash as SlashSquare }
export { SquareSlash as SlashSquareIcon }
export { Slice as SliceIcon }
export { SlidersVertical as Sliders }
export { SlidersHorizontal as SlidersHorizontalIcon }
export { SlidersVertical as SlidersIcon }
export { SlidersVertical as SlidersVerticalIcon }
export { SmartphoneCharging as SmartphoneChargingIcon }
export { Smartphone as SmartphoneIcon }
export { SmartphoneNfc as SmartphoneNfcIcon }
export { FaceSlightlySmiling as Smile }
export { FaceSlightlySmiling as SmileIcon }
export { FaceSlightlySmilingPlus as SmilePlus }
export { FaceSlightlySmilingPlus as SmilePlusIcon }
export { Snail as SnailIcon }
export { Snowflake as SnowflakeIcon }
export { SoapDispenserDroplet as SoapDispenserDropletIcon }
export { Sofa as SofaIcon }
export { SolarPanel as SolarPanelIcon }
export { ArrowUpNarrowWide as SortAsc }
export { ArrowUpNarrowWide as SortAscIcon }
export { ArrowDownWideNarrow as SortDesc }
export { ArrowDownWideNarrow as SortDescIcon }
export { Soup as SoupIcon }
export { Space as SpaceIcon }
export { Spade as SpadeIcon }
export { Sparkle as SparkleIcon }
export { Sparkles as SparklesIcon }
export { Speaker as SpeakerIcon }
export { Speech as SpeechIcon }
export { SpellCheck2 as SpellCheck2Icon }
export { SpellCheck as SpellCheckIcon }
export { Spline as SplineIcon }
export { SplinePointer as SplinePointerIcon }
export { Split as SplitIcon }
export { SquareSplitHorizontal as SplitSquareHorizontal }
export { SquareSplitHorizontal as SplitSquareHorizontalIcon }
export { SquareSplitVertical as SplitSquareVertical }
export { SquareSplitVertical as SplitSquareVerticalIcon }
export { Spool as SpoolIcon }
export { SportShoe as SportShoeIcon }
export { Spotlight as SpotlightIcon }
export { SprayCan as SprayCanIcon }
export { Sprout as SproutIcon }
export { SquareActivity as SquareActivityIcon }
export { SquareArrowDown as SquareArrowDownIcon }
export { SquareArrowDownLeft as SquareArrowDownLeftIcon }
export { SquareArrowDownRight as SquareArrowDownRightIcon }
export { SquareArrowLeft as SquareArrowLeftIcon }
export { SquareArrowOutDownLeft as SquareArrowOutDownLeftIcon }
export { SquareArrowOutDownRight as SquareArrowOutDownRightIcon }
export { SquareArrowOutUpLeft as SquareArrowOutUpLeftIcon }
export { SquareArrowOutUpRight as SquareArrowOutUpRightIcon }
export { SquareArrowRightEnter as SquareArrowRightEnterIcon }
export { SquareArrowRightExit as SquareArrowRightExitIcon }
export { SquareArrowRight as SquareArrowRightIcon }
export { SquareArrowUp as SquareArrowUpIcon }
export { SquareArrowUpLeft as SquareArrowUpLeftIcon }
export { SquareArrowUpRight as SquareArrowUpRightIcon }
export { SquareAsterisk as SquareAsteriskIcon }
export { SquareBottomDashedScissors as SquareBottomDashedScissorsIcon }
export { SquareCenterlineDashedHorizontal as SquareCenterlineDashedHorizontalIcon }
export { SquareCenterlineDashedVertical as SquareCenterlineDashedVerticalIcon }
export { SquareChartGantt as SquareChartGanttIcon }
export { SquareCheckBig as SquareCheckBigIcon }
export { SquareCheck as SquareCheckIcon }
export { SquareChevronDown as SquareChevronDownIcon }
export { SquareChevronLeft as SquareChevronLeftIcon }
export { SquareChevronRight as SquareChevronRightIcon }
export { SquareChevronUp as SquareChevronUpIcon }
export { SquareCode as SquareCodeIcon }
export { SquareDashedBottomCode as SquareDashedBottomCodeIcon }
export { SquareDashedBottom as SquareDashedBottomIcon }
export { SquareDashed as SquareDashedIcon }
export { SquareDashedKanban as SquareDashedKanbanIcon }
export { SquareDashedMousePointer as SquareDashedMousePointerIcon }
export { SquareDashedText as SquareDashedTextIcon }
export { SquareDashedTopSolid as SquareDashedTopSolidIcon }
export { SquareDimensions as SquareDimensionsIcon }
export { SquareDivide as SquareDivideIcon }
export { SquareDot as SquareDotIcon }
export { SquareEqual as SquareEqualIcon }
export { SquareFunction as SquareFunctionIcon }
export { SquareChartGantt as SquareGanttChart }
export { SquareChartGantt as SquareGanttChartIcon }
export { Square as SquareIcon }
export { SquareKanban as SquareKanbanIcon }
export { SquareLibrary as SquareLibraryIcon }
export { SquareM as SquareMIcon }
export { SquareMenu as SquareMenuIcon }
export { SquareMinus as SquareMinusIcon }
export { SquareMousePointer as SquareMousePointerIcon }
export { SquareOff as SquareOffIcon }
export { SquareParking as SquareParkingIcon }
export { SquareParkingOff as SquareParkingOffIcon }
export { SquarePause as SquarePauseIcon }
export { SquarePen as SquarePenIcon }
export { SquarePercent as SquarePercentIcon }
export { SquarePi as SquarePiIcon }
export { SquarePilcrow as SquarePilcrowIcon }
export { SquarePlay as SquarePlayIcon }
export { SquarePlus as SquarePlusIcon }
export { SquarePower as SquarePowerIcon }
export { SquareRadical as SquareRadicalIcon }
export { SquareRoundCorner as SquareRoundCornerIcon }
export { SquareScissors as SquareScissorsIcon }
export { SquareSigma as SquareSigmaIcon }
export { SquareSlash as SquareSlashIcon }
export { SquareSplitHorizontal as SquareSplitHorizontalIcon }
export { SquareSplitVertical as SquareSplitVerticalIcon }
export { SquareSquare as SquareSquareIcon }
export { SquareStack as SquareStackIcon }
export { SquareStar as SquareStarIcon }
export { SquareStop as SquareStopIcon }
export { SquareTerminal as SquareTerminalIcon }
export { SquareText as SquareTextIcon }
export { SquareUser as SquareUserIcon }
export { SquareUserRound as SquareUserRoundIcon }
export { SquareX as SquareXIcon }
export { SquaresExclude as SquaresExcludeIcon }
export { SquaresIntersect as SquaresIntersectIcon }
export { SquaresSubtract as SquaresSubtractIcon }
export { SquaresUnite as SquaresUniteIcon }
export { SquircleDashed as SquircleDashedIcon }
export { Squircle as SquircleIcon }
export { Squirrel as SquirrelIcon }
export { Stamp as StampIcon }
export { StarCheck as StarCheckIcon }
export { StarHalf as StarHalfIcon }
export { Star as StarIcon }
export { StarMinus as StarMinusIcon }
export { StarOff as StarOffIcon }
export { StarPlus as StarPlusIcon }
export { StarX as StarXIcon }
export { Sparkles as Stars }
export { Sparkles as StarsIcon }
export { StepBack as StepBackIcon }
export { StepForward as StepForwardIcon }
export { Stethoscope as StethoscopeIcon }
export { Sticker as StickerIcon }
export { StickyNoteCheck as StickyNoteCheckIcon }
export { StickyNote as StickyNoteIcon }
export { StickyNoteMinus as StickyNoteMinusIcon }
export { StickyNoteOff as StickyNoteOffIcon }
export { StickyNotePlus as StickyNotePlusIcon }
export { StickyNoteX as StickyNoteXIcon }
export { StickyNotes as StickyNotesIcon }
export { Stone as StoneIcon }
export { CircleStop as StopCircle }
export { CircleStop as StopCircleIcon }
export { Store as StoreIcon }
export { StretchHorizontal as StretchHorizontalIcon }
export { StretchVertical as StretchVerticalIcon }
export { Strikethrough as StrikethroughIcon }
export { Subscript as SubscriptIcon }
export { Captions as Subtitles }
export { Captions as SubtitlesIcon }
export { Summary as SummaryIcon }
export { SunDim as SunDimIcon }
export { Sun as SunIcon }
export { SunMedium as SunMediumIcon }
export { SunMoon as SunMoonIcon }
export { SunSnow as SunSnowIcon }
export { Sunrise as SunriseIcon }
export { Sunset as SunsetIcon }
export { Superscript as SuperscriptIcon }
export { SwatchBook as SwatchBookIcon }
export { SwissFranc as SwissFrancIcon }
export { SwitchCamera as SwitchCameraIcon }
export { Sword as SwordIcon }
export { Swords as SwordsIcon }
export { Syringe as SyringeIcon }
export { Table2 as Table2Icon }
export { TableCellsMerge as TableCellsMergeIcon }
export { TableCellsSplit as TableCellsSplitIcon }
export { TableColumnsSplit as TableColumnsSplitIcon }
export { Columns3Cog as TableConfig }
export { Columns3Cog as TableConfigIcon }
export { Table as TableIcon }
export { TableOfContents as TableOfContentsIcon }
export { TableProperties as TablePropertiesIcon }
export { TableRowsSplit as TableRowsSplitIcon }
export { Tablet as TabletIcon }
export { TabletSmartphone as TabletSmartphoneIcon }
export { Tablets as TabletsIcon }
export { Tag as TagIcon }
export { TagPlus as TagPlusIcon }
export { TagX as TagXIcon }
export { Tags as TagsIcon }
export { Tally1 as Tally1Icon }
export { Tally2 as Tally2Icon }
export { Tally3 as Tally3Icon }
export { Tally4 as Tally4Icon }
export { Tally5 as Tally5Icon }
export { Tangent as TangentIcon }
export { Target as TargetIcon }
export { Telescope as TelescopeIcon }
export { Tent as TentIcon }
export { TentTree as TentTreeIcon }
export { Terminal as TerminalIcon }
export { SquareTerminal as TerminalSquare }
export { SquareTerminal as TerminalSquareIcon }
export { TestTubeDiagonal as TestTube2 }
export { TestTubeDiagonal as TestTube2Icon }
export { TestTubeDiagonal as TestTubeDiagonalIcon }
export { TestTube as TestTubeIcon }
export { TestTubes as TestTubesIcon }
export { TextAlignStart as Text }
export { TextAlignCenter as TextAlignCenterIcon }
export { TextAlignEnd as TextAlignEndIcon }
export { TextAlignJustify as TextAlignJustifyIcon }
export { TextAlignStart as TextAlignStartIcon }
export { TextCursor as TextCursorIcon }
export { TextCursorInput as TextCursorInputIcon }
export { TextAlignStart as TextIcon }
export { TextInitial as TextInitialIcon }
export { TextQuote as TextQuoteIcon }
export { TextSearch as TextSearchIcon }
export { SquareDashedText as TextSelect }
export { SquareDashedText as TextSelectIcon }
export { SquareDashedText as TextSelection }
export { SquareDashedText as TextSelectionIcon }
export { TextWrap as TextWrapIcon }
export { Theater as TheaterIcon }
export { Thermometer as ThermometerIcon }
export { ThermometerSnowflake as ThermometerSnowflakeIcon }
export { ThermometerSun as ThermometerSunIcon }
export { ThumbsDown as ThumbsDownIcon }
export { ThumbsUp as ThumbsUpIcon }
export { TicketCheck as TicketCheckIcon }
export { Ticket as TicketIcon }
export { TicketMinus as TicketMinusIcon }
export { TicketPercent as TicketPercentIcon }
export { TicketPlus as TicketPlusIcon }
export { TicketSlash as TicketSlashIcon }
export { TicketX as TicketXIcon }
export { Tickets as TicketsIcon }
export { TicketsPlane as TicketsPlaneIcon }
export { Timeline as TimelineIcon }
export { Timer as TimerIcon }
export { TimerOff as TimerOffIcon }
export { TimerReset as TimerResetIcon }
export { ToggleLeft as ToggleLeftIcon }
export { ToggleRight as ToggleRightIcon }
export { Toilet as ToiletIcon }
export { ToolCase as ToolCaseIcon }
export { Toolbox as ToolboxIcon }
export { Tornado as TornadoIcon }
export { Torus as TorusIcon }
export { Touchpad as TouchpadIcon }
export { TouchpadOff as TouchpadOffIcon }
export { TowelRack as TowelRackIcon }
export { TowerControl as TowerControlIcon }
export { ToyBrick as ToyBrickIcon }
export { Tractor as TractorIcon }
export { TrafficCone as TrafficConeIcon }
export { Trailer as TrailerIcon }
export { TramFront as Train }
export { TrainFront as TrainFrontIcon }
export { TrainFrontTunnel as TrainFrontTunnelIcon }
export { TramFront as TrainIcon }
export { TrainTrack as TrainTrackIcon }
export { TramFront as TramFrontIcon }
export { Transgender as TransgenderIcon }
export { Trash2 as Trash2Icon }
export { Trash as TrashIcon }
export { TreeDeciduous as TreeDeciduousIcon }
export { TreePalm as TreePalmIcon }
export { TreePine as TreePineIcon }
export { Trees as TreesIcon }
export { TrendingDown as TrendingDownIcon }
export { TrendingUpDown as TrendingUpDownIcon }
export { TrendingUp as TrendingUpIcon }
export { TriangleAlert as TriangleAlertIcon }
export { TriangleDashed as TriangleDashedIcon }
export { Triangle as TriangleIcon }
export { TriangleRight as TriangleRightIcon }
export { Trophy as TrophyIcon }
export { TruckElectric as TruckElectricIcon }
export { Truck as TruckIcon }
export { TurkishLira as TurkishLiraIcon }
export { Turntable as TurntableIcon }
export { Turtle as TurtleIcon }
export { TvMinimal as Tv2 }
export { TvMinimal as Tv2Icon }
export { Tv as TvIcon }
export { TvMinimal as TvMinimalIcon }
export { TvMinimalPlay as TvMinimalPlayIcon }
export { Type as TypeIcon }
export { TypeOutline as TypeOutlineIcon }
export { Umbrella as UmbrellaIcon }
export { UmbrellaOff as UmbrellaOffIcon }
export { Underline as UnderlineIcon }
export { Undo2 as Undo2Icon }
export { UndoDot as UndoDotIcon }
export { Undo as UndoIcon }
export { UnfoldHorizontal as UnfoldHorizontalIcon }
export { UnfoldVertical as UnfoldVerticalIcon }
export { Ungroup as UngroupIcon }
export { University as UniversityIcon }
export { Unlink2 as Unlink2Icon }
export { Unlink as UnlinkIcon }
export { LockOpen as Unlock }
export { LockOpen as UnlockIcon }
export { LockKeyholeOpen as UnlockKeyhole }
export { LockKeyholeOpen as UnlockKeyholeIcon }
export { Unplug as UnplugIcon }
export { CloudUpload as UploadCloud }
export { CloudUpload as UploadCloudIcon }
export { Upload as UploadIcon }
export { UsbCPort as UsbCPortIcon }
export { Usb as UsbIcon }
export { UserRound as User2 }
export { UserRound as User2Icon }
export { UserRoundCheck as UserCheck2 }
export { UserRoundCheck as UserCheck2Icon }
export { UserCheck as UserCheckIcon }
export { CircleUser as UserCircle }
export { CircleUserRound as UserCircle2 }
export { CircleUserRound as UserCircle2Icon }
export { CircleUser as UserCircleIcon }
export { UserRoundCog as UserCog2 }
export { UserRoundCog as UserCog2Icon }
export { UserCog as UserCogIcon }
export { User as UserIcon }
export { UserKey as UserKeyIcon }
export { UserLock as UserLockIcon }
export { UserRoundMinus as UserMinus2 }
export { UserRoundMinus as UserMinus2Icon }
export { UserMinus as UserMinusIcon }
export { UserPen as UserPenIcon }
export { UserRoundPlus as UserPlus2 }
export { UserRoundPlus as UserPlus2Icon }
export { UserPlus as UserPlusIcon }
export { UserRoundArrowLeft as UserRoundArrowLeftIcon }
export { UserRoundCheck as UserRoundCheckIcon }
export { UserRoundCog as UserRoundCogIcon }
export { UserRound as UserRoundIcon }
export { UserRoundKey as UserRoundKeyIcon }
export { UserRoundMinus as UserRoundMinusIcon }
export { UserRoundPen as UserRoundPenIcon }
export { UserRoundPlus as UserRoundPlusIcon }
export { UserRoundSearch as UserRoundSearchIcon }
export { UserRoundX as UserRoundXIcon }
export { UserSearch as UserSearchIcon }
export { UserShield as UserShieldIcon }
export { SquareUser as UserSquare }
export { SquareUserRound as UserSquare2 }
export { SquareUserRound as UserSquare2Icon }
export { SquareUser as UserSquareIcon }
export { UserStar as UserStarIcon }
export { UserRoundX as UserX2 }
export { UserRoundX as UserX2Icon }
export { UserX as UserXIcon }
export { UsersRound as Users2 }
export { UsersRound as Users2Icon }
export { Users as UsersIcon }
export { UsersRound as UsersRoundIcon }
export { UtensilsCrossed as UtensilsCrossedIcon }
export { Utensils as UtensilsIcon }
export { UtilityPole as UtilityPoleIcon }
export { Van as VanIcon }
export { Variable as VariableIcon }
export { Vault as VaultIcon }
export { VectorSquare as VectorSquareIcon }
export { Vegan as VeganIcon }
export { VenetianMask as VenetianMaskIcon }
export { VenusAndMars as VenusAndMarsIcon }
export { Venus as VenusIcon }
export { BadgeCheck as Verified }
export { BadgeCheck as VerifiedIcon }
export { Vibrate as VibrateIcon }
export { VibrateOff as VibrateOffIcon }
export { Video as VideoIcon }
export { VideoOff as VideoOffIcon }
export { Videotape as VideotapeIcon }
export { View as ViewIcon }
export { Voicemail as VoicemailIcon }
export { Volleyball as VolleyballIcon }
export { Volume1 as Volume1Icon }
export { Volume2 as Volume2Icon }
export { Volume as VolumeIcon }
export { VolumeOff as VolumeOffIcon }
export { VolumeX as VolumeXIcon }
export { Vote as VoteIcon }
export { WalletMinimal as Wallet2 }
export { WalletMinimal as Wallet2Icon }
export { WalletCards as WalletCardsIcon }
export { Wallet as WalletIcon }
export { WalletMinimal as WalletMinimalIcon }
export { Wallpaper as WallpaperIcon }
export { WandSparkles as Wand2 }
export { WandSparkles as Wand2Icon }
export { Wand as WandIcon }
export { WandSparkles as WandSparklesIcon }
export { Warehouse as WarehouseIcon }
export { WashingMachine as WashingMachineIcon }
export { Watch as WatchIcon }
export { WavesHorizontal as Waves }
export { WavesArrowDown as WavesArrowDownIcon }
export { WavesArrowUp as WavesArrowUpIcon }
export { WavesHorizontal as WavesHorizontalIcon }
export { WavesHorizontal as WavesIcon }
export { WavesLadder as WavesLadderIcon }
export { WavesVertical as WavesVerticalIcon }
export { Waypoints as WaypointsIcon }
export { Webcam as WebcamIcon }
export { WebcamOff as WebcamOffIcon }
export { Webhook as WebhookIcon }
export { WebhookOff as WebhookOffIcon }
export { Weight as WeightIcon }
export { WeightTilde as WeightTildeIcon }
export { Wheat as WheatIcon }
export { WheatOff as WheatOffIcon }
export { WholeWord as WholeWordIcon }
export { WifiCog as WifiCogIcon }
export { WifiHigh as WifiHighIcon }
export { Wifi as WifiIcon }
export { WifiLow as WifiLowIcon }
export { WifiOff as WifiOffIcon }
export { WifiPen as WifiPenIcon }
export { WifiSync as WifiSyncIcon }
export { WifiZero as WifiZeroIcon }
export { WindArrowDown as WindArrowDownIcon }
export { Wind as WindIcon }
export { Wine as WineIcon }
export { WineOff as WineOffIcon }
export { Workflow as WorkflowIcon }
export { Worm as WormIcon }
export { TextWrap as WrapText }
export { TextWrap as WrapTextIcon }
export { Wrench as WrenchIcon }
export { WrenchOff as WrenchOffIcon }
export { CircleX as XCircle }
export { CircleX as XCircleIcon }
export { X as XIcon }
export { XLineTop as XLineTopIcon }
export { OctagonX as XOctagon }
export { OctagonX as XOctagonIcon }
export { SquareX as XSquare }
export { SquareX as XSquareIcon }
export { Zap as ZapIcon }
export { ZapOff as ZapOffIcon }
export { ZodiacAquarius as ZodiacAquariusIcon }
export { ZodiacAries as ZodiacAriesIcon }
export { ZodiacCancer as ZodiacCancerIcon }
export { ZodiacCapricorn as ZodiacCapricornIcon }
export { ZodiacGemini as ZodiacGeminiIcon }
export { ZodiacLeo as ZodiacLeoIcon }
export { ZodiacLibra as ZodiacLibraIcon }
export { ZodiacOphiuchus as ZodiacOphiuchusIcon }
export { ZodiacPisces as ZodiacPiscesIcon }
export { ZodiacSagittarius as ZodiacSagittariusIcon }
export { ZodiacScorpio as ZodiacScorpioIcon }
export { ZodiacTaurus as ZodiacTaurusIcon }
export { ZodiacVirgo as ZodiacVirgoIcon }
export { ZoomIn as ZoomInIcon }
export { ZoomOut as ZoomOutIcon }
