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
import { useAPI } from '~~/composables/useAPI'

export const useMediaUpload = (file: File, category?: string) => {
  const formData = new FormData()
  formData.append('file', file)
  if (category) {
    formData.append('category', category)
  }
  return useAPI<MediaItem>('/media/upload', {
    method: 'POST',
    body: formData
  })
}

export const useMediaUploadStream = () => {
  return useAPI<MediaItem>('/media/upload/stream', {
    method: 'POST'
  })
}

export const useMediaUploadAvatar = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return useAPI<{ url: string }>('/media/avatar', {
    method: 'POST',
    body: formData
  })
}

export const useMediaUploadCover = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return useAPI<{ url: string }>('/media/cover', {
    method: 'POST',
    body: formData
  })
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

export const useBingWallpaper = (count = 1) => {
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
