import type { PaginatedResponse } from '~~/types/api'
import { useAPI } from '~~/composables/useAPI'

export function useGallery() {
  const { locale } = useI18n()

  const useGalleries = (params?: {
    page?: number
    pageSize?: number
    lang?: string
  }) => {
    return useAPI<PaginatedResponse<any>>('/gallery', {
      query: {
        page: params?.page,
        page_size: params?.pageSize,
        lang: params?.lang ?? locale.value
      }
    })
  }

  const getGallery = (slug: string) => {
    return useAPI<any>(`/gallery/slug/${slug}`)
  }

  const createGallery = (
    title: string,
    slug: string,
    description: string,
    cover?: string
  ) => {
    return useAPI<any>('/gallery', {
      method: 'POST',
      body: {
        title,
        slug,
        description,
        cover
      }
    })
  }

  const updateGallery = (id: number, data: any) => {
    return useAPI<any>(`/gallery/${id}`, {
      method: 'PUT',
      body: data
    })
  }

  const deleteGallery = (id: number) => {
    return useAPI<any>(`/gallery/${id}`, {
      method: 'DELETE'
    })
  }

  const useGalleryPhotos = (
    galleryId: number,
    page?: number,
    pageSize?: number
  ) => {
    return useAPI<PaginatedResponse<any>>(`/gallery/${galleryId}/photos`, {
      query: {
        page,
        page_size: pageSize
      }
    })
  }

  const addPhotos = (galleryId: number, formData: FormData) => {
    return useAPI<any>(`/gallery/${galleryId}/photos`, {
      method: 'POST',
      body: formData
    })
  }

  const reorderPhotos = (galleryId: number, order: number[]) => {
    return useAPI<any>(`/gallery/${galleryId}/photos/reorder`, {
      method: 'PUT',
      body: { order }
    })
  }

  const deletePhoto = (photoId: number) => {
    return useAPI<any>(`/gallery/photos/${photoId}`, {
      method: 'DELETE'
    })
  }

  const likeGallery = (id: number) => {
    return useAPI<any>(`/gallery/${id}/like`, {
      method: 'POST'
    })
  }

  return {
    useGalleries,
    getGallery,
    createGallery,
    updateGallery,
    deleteGallery,
    useGalleryPhotos,
    addPhotos,
    reorderPhotos,
    deletePhoto,
    likeGallery
  }
}
