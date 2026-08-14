import type { PaginatedResponse } from '~~/types/api'
import { useAPI } from '~~/composables/useAPI'

export function useActivity() {
  const useActivities = (params?: {
    page?: number
    pageSize?: number
    type?: string
    user_id?: number
  }) => {
    return useAPI<PaginatedResponse<any>>('/activity', {
      query: {
        page: params?.page,
        page_size: params?.pageSize,
        type: params?.type,
        user_id: params?.user_id
      }
    })
  }

  const likeActivity = (id: number) => {
    return useAPI<any>(`/activity/${id}/like`, {
      method: 'POST'
    })
  }

  const createActivity = (
    type: string,
    payload: any,
    visibility: string
  ) => {
    return useAPI<any>('/activity', {
      method: 'POST',
      body: {
        type,
        payload,
        visibility
      }
    })
  }

  const deleteActivity = (id: number) => {
    return useAPI<any>(`/activity/${id}`, {
      method: 'DELETE'
    })
  }

  const getActivityStats = () => {
    return useAPI<any>('/activity/stats')
  }

  return {
    useActivities,
    likeActivity,
    createActivity,
    deleteActivity,
    getActivityStats
  }
}
