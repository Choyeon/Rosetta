/**
 * titlePresets —— 用户头衔图标的两个薄层出口：下拉数据源 + 渲染分支归类。
 * 列表从 titleIcons 的 TITLE_ICON_DEFS 投影，禁止在组件里再抄一份常量。
 * resolveTitleIcon 是唯一的三态判定口径，且刻意不给标记语言出口：
 * 以 `<` 开头的脏数据直接落 empty（宁可少画图标），与后端 user_titles.icon 的 pattern
 * + 渲染侧不 v-html 一起守住 AGENTS.md §12.8 的存储型 XSS 红线。
 */

import { TITLE_ICON_DEFS, getTitleIconDef } from '~~/composables/titleIcons'

/**
 * 用户头衔（title）图标的解析层。
 *
 * 后端 `user_titles.icon` 是一个"三态字符串"：内建图标 id（如 `crown`）、
 * 原始 SVG 片段（以 `<` 开头），或者就是一枚 emoji。后台下拉只展示内建图标，
 * 渲染端则要知道该走哪条分支——这里就是那一个判定口径，避免组件里各写一份 startsWith('<')。
 */
export interface TitlePresetIcon {
  id: string
  name: string
  lucideName: string
}

/**
 * 头衔图标选择器用的精简列表（只需要 id/名称/图标名，不带动画路径）。
 */
export const TITLE_PRESET_ICONS: TitlePresetIcon[] = TITLE_ICON_DEFS.map(d => ({
  id: d.id,
  name: d.label,
  lucideName: d.lucideName
}))

export type ResolvedTitleIcon
  = | { type: 'lucide', value: string }
    | { type: 'emoji', value: string }
    | { type: 'empty', value: '' }

/**
 * 把存储值归类为三种渲染分支之一。
 *
 * 历史上这里还有一个 `svg` 分支（值以 `<` 开头就当作内联 SVG），组件直接 v-html 它——
 * 后台"自定义图标"输入框又明写支持贴 `<svg>...</svg>`，等于把 staff 权限升级成对全站访客的
 * 存储型 XSS。现在标记语言不再是合法取值（后端 pattern 已挡），这里也不给它任何出口：
 * 脏数据（老库里的 `<svg ...>`）一律落 empty，宁可少画一个图标。
 */
export function resolveTitleIcon(icon: string | null | undefined): ResolvedTitleIcon {
  if (!icon) return { type: 'empty', value: '' }
  const def = getTitleIconDef(icon)
  if (def) return { type: 'lucide', value: def.lucideName }
  if (icon.startsWith('<')) return { type: 'empty', value: '' }
  return { type: 'emoji', value: icon }
}
