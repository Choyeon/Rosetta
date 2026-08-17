import type { Gallery, GalleryItem, PaginatedResponse } from '~~/types/api'
import { useAPI } from '~~/composables/useAPI'

export function useGallery() {
  const { locale } = useI18n()

  const useGalleries = (params?: {
    page?: number
    pageSize?: number
    lang?: string
  }) => {
    return useAPI<PaginatedResponse<Gallery>>('/gallery', {
      query: {
        page: params?.page,
        page_size: params?.pageSize,
        lang: params?.lang ?? locale.value
      }
    })
  }

  const getGallery = (slug: string) => {
    return useAPI<Gallery>(`/gallery/slug/${slug}`)
  }

  const createGallery = (
    title: string,
    slug: string,
    description: string,
    cover?: string
  ) => {
    return useAPI<Gallery>('/gallery', {
      method: 'POST',
      body: {
        title,
        slug,
        description,
        cover
      }
    })
  }

  const updateGallery = (id: number, data: Partial<Gallery>) => {
    return useAPI<Gallery>(`/gallery/${id}`, {
      method: 'PUT',
      body: data
    })
  }

  const deleteGallery = (id: number) => {
    return useAPI<unknown>(`/gallery/${id}`, {
      method: 'DELETE'
    })
  }

  const useGalleryPhotos = (
    galleryId: number,
    page?: number,
    pageSize?: number
  ) => {
    return useAPI<PaginatedResponse<GalleryItem>>(`/gallery/${galleryId}/photos`, {
      query: {
        page,
        page_size: pageSize
      }
    })
  }

  const addPhotos = (galleryId: number, formData: FormData) => {
    return useAPI<unknown>(`/gallery/${galleryId}/photos`, {
      method: 'POST',
      body: formData
    })
  }

  const reorderPhotos = (galleryId: number, order: number[]) => {
    return useAPI<unknown>(`/gallery/${galleryId}/photos/reorder`, {
      method: 'PUT',
      body: { order }
    })
  }

  const deletePhoto = (photoId: number) => {
    return useAPI<unknown>(`/gallery/photos/${photoId}`, {
      method: 'DELETE'
    })
  }

  const likeGallery = (id: number) => {
    return useAPI<unknown>(`/gallery/${id}/like`, {
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
