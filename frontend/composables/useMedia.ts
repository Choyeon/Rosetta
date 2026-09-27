/**
 * useMedia —— 上传类「动作型」请求（编辑器、头像、封面、素材库上传）。
 *
 * 为什么这些不是 useAPI/useFetch：上传发生在事件回调里，需要 `await` 直接拿到返回的
 * MediaItem；useFetch 返回的是 AsyncData 包装对象，await 它拿不到 T 本身
 * ——这正是早先「点了上传没反应」的根因。
 *
 * 媒体库的**读**与**删**不在这里：列表/统计/单条删除/批量删除是后台管理契约，
 * 单一实现位于 useAdminManage.ts（fetchAdminMediaLibrary / fetchAdminMediaStats /
 * deleteAdminMedia / deleteAdminMediaBatch），页面一律走那一侧，避免两份封装漂移。
 */
import type { MediaItem } from '~~/types/api'
import { apiFetch } from '~~/composables/useApi'

/** 通用图片上传（POST /media/upload），category 决定落盘子目录。 */
export async function useMediaUpload(file: File, category?: string): Promise<MediaItem> {
  const formData = new FormData()
  formData.append('file', file)
  if (category) formData.append('category', category)
  return apiFetch<MediaItem>('/media/upload', { method: 'POST', body: formData })
}

/** 头像上传（前端已裁剪为方形小图）。 */
export async function useMediaUploadAvatar(file: File): Promise<{ url: string }> {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch<{ url: string }>('/media/avatar', { method: 'POST', body: formData })
}

/** 文章/相册封面上传。 */
export async function useMediaUploadCover(file: File): Promise<{ url: string }> {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch<{ url: string }>('/media/cover', { method: 'POST', body: formData })
}

export const useMediaLibrary = () => {
  /** 入库上传（POST /media/library）：写 Media 记录，供媒体库页面直接列出。 */
  const uploadMedia = async (file: File, category?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (category) {
      formData.append('category', category)
    }
    return apiFetch<MediaItem>('/media/library', {
      method: 'POST',
      body: formData
    })
  }

  return { uploadMedia }
}
