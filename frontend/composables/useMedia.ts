/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import type {
  MediaItem,
  MediaLibraryParams,
  MediaUpdate,
  MediaStats,
  PaginatedResponse,
  BingWallpaperItem,
  MediaAvatarOptions,
  BaseResponse
} from '~~/types/api'
import { useAPI, apiFetch } from '~~/composables/useApi'

/**
 * 资源上传（表单中即时触发的"动作型"请求）：
 * 必须用 $fetch 基的 apiFetch，返回 Promise<T> 可直接 await 拿到数据；
 * useFetch (= useAPI) 返回 AsyncData 响应式状态，适合模板/setup 中声明式绑定，
 * 但在事件回调中 await 它拿到的只是 { data, pending, ... } 包装对象而非 T 本身 —— 这是之前上传无反应的根因。
 */
export async function useMediaUpload(file: File, category?: string): Promise<MediaItem> {
  const formData = new FormData()
  formData.append('file', file)
  if (category) formData.append('category', category)
  return apiFetch<MediaItem>('/media/upload', { method: 'POST', body: formData })
}

export const useMediaUploadStream = () => {
  return useAPI<MediaItem>('/media/upload/stream', {
    method: 'POST'
  })
}

export async function useMediaUploadAvatar(file: File): Promise<{ url: string }> {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch<{ url: string }>('/media/avatar', { method: 'POST', body: formData })
}

export async function useMediaUploadCover(file: File): Promise<{ url: string }> {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch<{ url: string }>('/media/cover', { method: 'POST', body: formData })
}

export const useMediaLibrary = () => {
  const getMediaList = (params?: MediaLibraryParams) => {
    const query = {
      page: params?.page,
      page_size: params?.page_size ?? params?.pageSize,
      search: params?.search,
      category: params?.category,
      type: params?.type
    }
    return useAPI<PaginatedResponse<MediaItem>>('/media/library', { query })
  }

  const getMediaStats = () => {
    return useAPI<MediaStats>('/media/library/stats')
  }

  const uploadMedia = (file: File, category?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (category) {
      formData.append('category', category)
    }
    return useAPI<MediaItem>('/media/library', {
      method: 'POST',
      body: formData
    })
  }

  const getMediaDetail = (mediaId: number) => {
    return useAPI<MediaItem>(`/media/library/${mediaId}`)
  }

  const updateMedia = (mediaId: number, data: MediaUpdate) => {
    return useAPI<MediaItem>(`/media/library/${mediaId}`, {
      method: 'PUT',
      body: data
    })
  }

  const deleteMedia = (mediaId: number) => {
    return useAPI<BaseResponse>(`/media/library/${mediaId}`, {
      method: 'DELETE'
    })
  }

  const deleteMediaBatch = (ids: number[]) => {
    return useAPI<BaseResponse>('/media/library/batch', {
      method: 'DELETE',
      body: { ids }
    })
  }

  return {
    getMediaList,
    getMediaStats,
    uploadMedia,
    getMediaDetail,
    updateMedia,
    deleteMedia,
    deleteMediaBatch
  }
}

export const useServerBingWallpaper = (count = 1) => {
  return useAPI<BingWallpaperItem[]>('/media/bing-wallpaper', {
    query: { count }
  })
}

export const useMediaAvatar = (options?: MediaAvatarOptions) => {
  const config = useRuntimeConfig()
  const baseURL = config.public.apiBase

  const getAvatarUrl = () => {
    const params = new URLSearchParams()
    if (options?.username) params.append('username', options.username)
    if (options?.email) params.append('email', options.email)
    if (options?.size) params.append('size', options.size.toString())
    if (options?.default) params.append('default', options.default)
    const queryString = params.toString()
    return `${baseURL}/media/avatar${queryString ? `?${queryString}` : ''}`
  }

  return {
    getAvatarUrl,
    fetchAvatar: () => {
      return useAPI<string>('/media/avatar', {
        query: {
          username: options?.username,
          email: options?.email,
          size: options?.size,
          default: options?.default
        }
      })
    }
  }
}
