export interface TitleIconDef {
  id: string
  label: string
  lucideName: string
  paths: string[]
  circles?: Array<{ cx: number, cy: number, r: number }>
}

const ICONS: TitleIconDef[] = [
  {
    id: 'crown', label: '皇冠', lucideName: 'Crown',
    paths: ['M11.562 3.266a.5.5 0 0 1 .876 0L16.5 9.5l3.5-3L20 17H4L3 6.5l3.5 3z']
  },
  {
    id: 'star', label: '五角星', lucideName: 'Star',
    paths: ['M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z']
  },
  {
    id: 'award', label: '奖章', lucideName: 'Award',
    paths: ['m15.477 12.89 1.515 8.526a.5.5 0 0 1-.72.533L12 19l-4.272 2.95a.5.5 0 0 1-.72-.533l1.514-8.526A7 7 0 1 1 15.477 12.89Z']
  },
  {
    id: 'badge-check', label: '认证徽章', lucideName: 'BadgeCheck',
    paths: ['m3.86 14.18 1.16-.92a2 2 0 0 0 0-2.86l-1.14-.92A8 8 0 0 1 18 4a8 8 0 0 1 2.14 5.48l-1.14.92a2 2 0 0 0 0 2.86l1.16.92A8 8 0 0 1 3.86 14.18Z'],
    circles: [{ cx: 12, cy: 10.5, r: 2.5 }]
  },
  {
    id: 'shield', label: '盾牌', lucideName: 'Shield',
    paths: ['M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z']
  },
  {
    id: 'shield-check', label: '安全盾牌', lucideName: 'ShieldCheck',
    paths: ['M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z', 'm9 12 2 2 4-4']
  },
  {
    id: 'zap', label: '闪电', lucideName: 'Zap',
    paths: ['M13 2 3 14h9l-1 8 10-12h-9l1-8z']
  },
  {
    id: 'flame', label: '火焰', lucideName: 'Flame',
    paths: ['M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z']
  },
  {
    id: 'gem', label: '宝石', lucideName: 'Gem',
    paths: ['M6 3h12l4 6-10 13L2 9Z']
  },
  {
    id: 'sparkles', label: '闪光', lucideName: 'Sparkles',
    paths: ['m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z']
  },
  {
    id: 'heart', label: '爱心', lucideName: 'Heart',
    paths: ['M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z']
  },
  {
    id: 'rocket', label: '火箭', lucideName: 'Rocket',
    paths: [
      'M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z',
      'M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z',
      'M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0',
      'M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5'
    ]
  },
  {
    id: 'trophy', label: '奖杯', lucideName: 'Trophy',
    paths: [
      'M6 9H4.5a2.5 2.5 0 0 1 0-5H6',
      'M18 9h1.5a2.5 2.5 0 0 0 0-5H18',
      'M4 22h16',
      'M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22',
      'M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22',
      'M18 2H6v7a6 6 0 0 0 12 0V2Z'
    ]
  },
  {
    id: 'medal', label: '勋章', lucideName: 'Medal',
    paths: [
      'M7.21 15 2.66 7.14a2 2 0 0 1 .13-2.2L4.4 2.8A2 2 0 0 1 6 2h12a2 2 0 0 1 1.6.8l1.6 2.14a2 2 0 0 1 .14 2.2L16.79 15',
      'M12 15l-2 7h4l-2-7z'
    ],
    circles: [{ cx: 12, cy: 11, r: 4 }]
  },
  {
    id: 'code', label: '开发者', lucideName: 'Code',
    paths: ['m16 18 6-6-6-6', 'm8 6-6 6 6 6']
  },
  {
    id: 'terminal', label: '终端', lucideName: 'Terminal',
    paths: ['m4 17 6-6-6-6', 'M12 19h8']
  },
  {
    id: 'globe', label: '全球', lucideName: 'Globe',
    paths: [
      'M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z',
      'M2 12h20',
      'M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z'
    ]
  },
  {
    id: 'palette', label: '调色板', lucideName: 'Palette',
    paths: [
      'M12 22a10 10 0 0 1-7.34-3.15A9.97 9.97 0 0 1 2 12 10 10 0 0 1 12 2c3.56 0 6.5 1.5 8.5 4 .72.9 1.2 1.96 1.42 3.12.22 1.16.12 2.36-.3 3.48-.42 1.12-1.14 2.1-2.1 2.84L12 22z'
    ],
    circles: [
      { cx: 7.5, cy: 10.5, r: 1 },
      { cx: 12, cy: 7.5, r: 1 },
      { cx: 16.5, cy: 10.5, r: 1 }
    ]
  },
  {
    id: 'pen-tool', label: '设计师', lucideName: 'PenTool',
    paths: [
      'm12 19 7-7 3 3-7 7-3-3z',
      'm18 13-1.5-7.5L2 2l3.5 14.5L13 18l5-5z',
      'm2 2 7.586 7.586'
    ],
    circles: [{ cx: 11, cy: 11, r: 2 }]
  },
  {
    id: 'camera', label: '摄影师', lucideName: 'Camera',
    paths: [
      'M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z'
    ],
    circles: [{ cx: 12, cy: 13, r: 3 }]
  },
  {
    id: 'book-open', label: '学者', lucideName: 'BookOpen',
    paths: [
      'M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z',
      'M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z'
    ]
  },
  {
    id: 'graduation-cap', label: '毕业帽', lucideName: 'GraduationCap',
    paths: [
      'M22 10v6M2 10l10-5 10 5-10 5z',
      'M6 12v5c3 3 9 3 12 0v-5'
    ]
  },
  {
    id: 'cpu', label: '芯片', lucideName: 'Cpu',
    paths: [
      'M18 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2z',
      'M9 9h6v6H9z',
      'M9 2v2', 'M15 2v2', 'M9 20v2', 'M15 20v2',
      'M2 9h2', 'M2 15h2', 'M20 9h2', 'M20 15h2'
    ]
  },
  {
    id: 'music', label: '音乐家', lucideName: 'Music',
    paths: [
      'M9 18V5l12-2v13',
      'M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
      'M21 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z'
    ]
  },
  {
    id: 'wrench', label: '工程师', lucideName: 'Wrench',
    paths: [
      'M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z'
    ]
  },
  {
    id: 'users', label: '团队', lucideName: 'Users',
    paths: [
      'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2',
      'M22 21v-2a4 4 0 0 0-3-3.87',
      'M16 3.13a4 4 0 0 1 0 7.75'
    ],
    circles: [{ cx: 9, cy: 7, r: 4 }]
  },
  {
    id: 'user-check', label: 'VIP', lucideName: 'UserCheck',
    paths: [
      'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2',
      'M22 11l-3.5-3.5L17 9'
    ],
    circles: [{ cx: 9, cy: 7, r: 4 }]
  },
  {
    id: 'diamond', label: '钻石', lucideName: 'Diamond',
    paths: [
      'M2.7 10.3a2.41 2.41 0 0 0 0 3.41l7.59 7.59a2.41 2.41 0 0 0 3.41 0l7.59-7.59a2.41 2.41 0 0 0 0-3.41L13.7 2.71a2.41 2.41 0 0 0-3.41 0z'
    ]
  },
  {
    id: 'feather', label: '作家', lucideName: 'Feather',
    paths: [
      'M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z',
      'M16 8 2 22',
      'M17.5 15H9'
    ]
  },
  {
    id: 'coffee', label: '贡献者', lucideName: 'Coffee',
    paths: [
      'M17 8h1a4 4 0 1 1 0 8h-1',
      'M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z',
      'M6 2v2', 'M10 2v2', 'M14 2v2'
    ]
  },
  {
    id: 'target', label: '目标', lucideName: 'Target',
    paths: [],
    circles: [
      { cx: 12, cy: 12, r: 10 },
      { cx: 12, cy: 12, r: 6 },
      { cx: 12, cy: 12, r: 2 }
    ]
  },
  {
    id: 'bolt', label: '能量', lucideName: 'Bolt',
    paths: ['M13 2 3 14h9l-1 8 10-12h-9l1-8z']
  }
]

const ICON_MAP = new Map(ICONS.map(i => [i.id, i]))
const LUCIDE_MAP = new Map(ICONS.map(i => [i.lucideName, i]))

export function getTitleIconDef(idOrLucide: string): TitleIconDef | undefined {
  return ICON_MAP.get(idOrLucide) ?? LUCIDE_MAP.get(idOrLucide)
}

export { ICONS as TITLE_ICON_DEFS }
