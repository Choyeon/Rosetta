import type { Activity, PaginatedResponse } from '~~/types/api'
import { useAPI } from '~~/composables/useAPI'

export function useActivity() {
  const useActivities = (params?: {
    page?: number
    pageSize?: number
    type?: string
    user_id?: number
  }) => {
    return useAPI<PaginatedResponse<Activity>>('/activity', {
      query: {
        page: params?.page,
        page_size: params?.pageSize,
        type: params?.type,
        user_id: params?.user_id
      }
    })
  }

  const likeActivity = (id: number) => {
    return useAPI<unknown>(`/activity/${id}/like`, {
      method: 'POST'
    })
  }

  const createActivity = (
    type: string,
    payload: unknown,
    visibility: string
  ) => {
    return useAPI<unknown>('/activity', {
      method: 'POST',
      body: {
        type,
        payload,
        visibility
      }
    })
  }

  const deleteActivity = (id: number) => {
    return useAPI<unknown>(`/activity/${id}`, {
      method: 'DELETE'
    })
  }

  const getActivityStats = () => {
    return useAPI<unknown>('/activity/stats')
  }

  return {
    useActivities,
    likeActivity,
    createActivity,
    deleteActivity,
    getActivityStats
  }
}
