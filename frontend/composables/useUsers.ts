/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import type { PaginatedResponse } from '~~/types/api'
import { useAPI } from '~~/composables/useApi'

export const useUsers = () => {
  const { locale } = useI18n()

  const getUser = (userId: number) => {
    return useAPI(`/users/${userId}`)
  }

  const getUserByUsername = (username: string) => {
    return useAPI(`/users/username/${username}`)
  }

  const getUserPosts = (userId: number, page = 1, pageSize = 10) => {
    return useAPI<PaginatedResponse>(`/users/${userId}/posts`, {
      query: {
        lang: locale.value,
        page,
        page_size: pageSize
      }
    })
  }

  const getUserComments = (userId: number, page = 1, pageSize = 10) => {
    return useAPI<PaginatedResponse>(`/users/${userId}/comments`, {
      query: {
        lang: locale.value,
        page,
        page_size: pageSize
      }
    })
  }

  const getUserStats = (userId: number) => {
    return useAPI(`/users/${userId}/stats`)
  }

  return {
    getUser,
    getUserByUsername,
    getUserPosts,
    getUserComments,
    getUserStats
  }
}
