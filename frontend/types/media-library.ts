/**
 * GET /api/media/library 返回的完整媒体条目类型。
 *
 * useAdminManage.ts 的 AdminMediaItem 只声明了列表用的核心字段；
 * 后端实际还会返回 title / alt_text / description / width / height / file_type 等，
 * 预览对话框与列表视图需要这些字段，为了不碰 useAdminManage.ts 在此单独声明超集。
 */
export interface MediaLibraryItem {
  id: number
  url: string
  file?: string | null
  filename: string
  file_type?: string | null
  category?: string | null
  mime?: string | null
  file_size?: string | null
  size_bytes: number
  title?: string | null
  alt_text?: string | null
  description?: string | null
  width?: number | null
  height?: number | null
  sizes?: Record<string, unknown> | null
  uploaded_by?: { id: number, username: string, nickname?: string | null } | null
  created_at?: string | null
  updated_at?: string | null
}
