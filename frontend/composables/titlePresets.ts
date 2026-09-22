import { TITLE_ICON_DEFS, getTitleIconDef } from '~~/composables/titleIcons'

export interface TitlePresetIcon {
  id: string
  name: string
  lucideName: string
}

export const TITLE_PRESET_ICONS: TitlePresetIcon[] = TITLE_ICON_DEFS.map(d => ({
  id: d.id,
  name: d.label,
  lucideName: d.lucideName
}))

export function getTitlePreset(id: string): TitlePresetIcon | undefined {
  return TITLE_PRESET_ICONS.find(p => p.id === id)
}

export function isPresetId(icon: string | null | undefined): boolean {
  if (!icon) return false
  return TITLE_ICON_DEFS.some(d => d.id === icon)
}

export type ResolvedTitleIcon
  = | { type: 'lucide', value: string }
    | { type: 'emoji', value: string }
    | { type: 'svg', value: string }
    | { type: 'empty', value: '' }

export function resolveTitleIcon(icon: string | null | undefined): ResolvedTitleIcon {
  if (!icon) return { type: 'empty', value: '' }
  const def = getTitleIconDef(icon)
  if (def) return { type: 'lucide', value: def.lucideName }
  if (icon.startsWith('<')) return { type: 'svg', value: icon }
  return { type: 'emoji', value: icon }
}
