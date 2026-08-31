export interface TitlePresetIcon {
  id: string
  name: string
  lucideName: string
}

export const TITLE_PRESET_ICONS: TitlePresetIcon[] = [
  { id: 'star', name: '五角星', lucideName: 'Star' },
  { id: 'crown', name: '皇冠', lucideName: 'Crown' },
  { id: 'trophy', name: '奖杯', lucideName: 'Trophy' },
  { id: 'award', name: '奖项', lucideName: 'Award' },
  { id: 'medal', name: '勋章', lucideName: 'Medal' },
  { id: 'ribbon', name: '绶带', lucideName: 'Ribbon' },
  { id: 'shield', name: '盾牌', lucideName: 'Shield' },
  { id: 'shield-check', name: '安全盾牌', lucideName: 'ShieldCheck' },
  { id: 'flame', name: '火焰', lucideName: 'Flame' },
  { id: 'gem', name: '宝石', lucideName: 'Gem' },
  { id: 'sparkles', name: '闪光', lucideName: 'Sparkles' },
  { id: 'zap', name: '闪电', lucideName: 'Zap' },
  { id: 'badge-check', name: '验证徽章', lucideName: 'BadgeCheck' },
  { id: 'heart', name: '爱心', lucideName: 'Heart' },
  { id: 'star-half', name: '半星', lucideName: 'StarHalf' }
]

export function getTitlePreset(id: string): TitlePresetIcon | undefined {
  return TITLE_PRESET_ICONS.find(p => p.id === id)
}

export function isPresetId(icon: string | null | undefined): boolean {
  if (!icon) return false
  return TITLE_PRESET_ICONS.some(p => p.id === icon)
}

export type ResolvedTitleIcon
  = | { type: 'lucide', value: string }
    | { type: 'emoji', value: string }
    | { type: 'svg', value: string }
    | { type: 'empty', value: '' }

export function resolveTitleIcon(icon: string | null | undefined): ResolvedTitleIcon {
  if (!icon) return { type: 'empty', value: '' }
  const preset = TITLE_PRESET_ICONS.find(p => p.id === icon)
  if (preset) return { type: 'lucide', value: preset.lucideName }
  if (icon.startsWith('<')) return { type: 'svg', value: icon }
  return { type: 'emoji', value: icon }
}
