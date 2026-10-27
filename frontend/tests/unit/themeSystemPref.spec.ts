/**
 * 「跟随系统」必须是能持续生效的偏好（不是只在那一次点击里生效的标签）。
 *
 * 旧形态：settings.vue 提供三选一，但 useTheme 只持久化解析后的 light|dark，
 * 也没有 matchMedia change 监听器 —— 选完「跟随系统」，重进本页高亮回落成
 * light/dark，OS 之后切换深浅色界面也不动。修它的正确位置在 useTheme（页面自己
 * 存第三态等于造第二个偏好真值源），本 spec 钉住这四处口径：
 *   ① 三态偏好有独立键 `theme-pref`，`theme` 仍是解析后的 light|dark
 *      （<head> 里的 FOUC 内联脚本只读 `theme`，塞第三态会让首帧颜色判错）；
 *   ② setSystem 绑 matchMedia 监听器，且监听器有模块级单次闸门；
 *   ③ 首屏纠偏读 readThemePref()，不再自己拼 localStorage 口径；
 *   ④ 日月按钮手动切换时把 'system' 落成具体值，否则 OS 下一次变更会覆盖用户显式选择。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const theme = readFileSync(resolve(ROOT, 'composables/useTheme.ts'), 'utf-8')
const settings = readFileSync(resolve(ROOT, 'pages/settings.vue'), 'utf-8')

describe('useTheme 三态偏好', () => {
  it('偏好键与已解析键分开存', () => {
    expect(theme).toContain('const PREF_KEY = \'theme-pref\'')
    expect(theme).toContain('localStorage.setItem(STORAGE_KEY, themeMode.value)')
    expect(theme).toContain('localStorage.setItem(PREF_KEY, themePref.value)')
  })

  it('themeMode 仍只有 light|dark 两种取值（FOUC 脚本的契约）', () => {
    expect(theme).toContain('type ThemeMode = \'light\' | \'dark\'')
    expect(theme).toMatch(/const applyTheme = \(dark: boolean\)[\s\S]{0,400}themeMode\.value = dark \? 'dark' : 'light'/)
  })

  it('跟随系统：记偏好 + 应用当前系统方案 + 绑监听器', () => {
    const fn = theme.match(/const setSystem = \(\) => \{[\s\S]*?\n {2}\}/)?.[0] ?? ''
    expect(fn).toContain('themePref.value = \'system\'')
    expect(fn).toContain('bindSystemSchemeListener()')
  })

  it('监听器只在偏好为 system 时生效，且全模块只绑一次', () => {
    const binder = theme.match(/const bindSystemSchemeListener = \(\) => \{[\s\S]*?\n {2}\}/)?.[0] ?? ''
    expect(binder).toContain('__systemSchemeListenerBound')
    expect(binder).toContain('themePref.value !== \'system\'')
    expect(binder).toContain('\'change\'')
    expect(theme).toContain('let __systemSchemeListenerBound = false')
  })

  it('首屏纠偏走 readThemePref()，不在页面里另拼一套 localStorage 口径', () => {
    const init = theme.match(/const initFromStorageAndApply = \(\) => \{[\s\S]*?\n {2}\}/)?.[0] ?? ''
    expect(init).toContain('readThemePref()')
    expect(init).toContain('if (pref === \'system\') bindSystemSchemeListener()')
  })

  it('日月按钮切换会把 system 落成具体偏好', () => {
    expect(theme).toContain('themePref.value = willBeDark ? \'dark\' : \'light\'')
    expect(theme).toContain('themePref.value = nextMode')
  })
})

describe('settings.vue 消费同一个偏好真值源', () => {
  it('高亮态读 readThemePref()', () => {
    expect(settings).toContain('pref.value = readThemePref()')
  })

  it('不再直读 localStorage.getItem("theme") 当偏好（那只会得到解析后的两态）', () => {
    expect(settings).not.toContain('localStorage.getItem(\'theme\')')
  })

  it('三个选项分别走 setSystem / setLight / setDark', () => {
    expect(settings).toContain('else setSystem()')
    expect(settings).toContain('if (mode === \'dark\') setDark()')
  })
})
