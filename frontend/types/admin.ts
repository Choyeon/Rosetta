export interface AdminColumn {
  key: string
  title: string
  class?: string
  align?: 'left' | 'right' | 'center'
}

export type AdminRow = Record<string, unknown>
