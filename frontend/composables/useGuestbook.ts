import type { PaginatedResponse } from '~~/types/api'
import { useAPI } from '~~/composables/useAPI'

export function useGuestbook() {
  const getMessages = (params?: {
    page?: number
    pageSize?: number
    status?: string
  }) => {
    return useAPI<PaginatedResponse<any>>('/guestbook', {
      query: {
        page: params?.page,
        page_size: params?.pageSize,
        status: params?.status
      }
    })
  }

  const getMessage = (id: number) => {
    return useAPI<any>(`/guestbook/${id}`)
  }

  const createMessage = (
    content: string,
    parent_id?: number,
    nickname?: string,
    email?: string,
    site?: string
  ) => {
    return useAPI<any>('/guestbook', {
      method: 'POST',
      body: {
        content,
        parent_id,
        nickname,
        email,
        site
      }
    })
  }

  const likeMessage = (id: number) => {
    return useAPI<any>(`/guestbook/${id}/like`, {
      method: 'POST'
    })
  }

  const replyMessage = (id: number, content: string) => {
    return useAPI<any>(`/guestbook/${id}/reply`, {
      method: 'POST',
      body: { content }
    })
  }

  const updateMessage = (id: number, content: string) => {
    return useAPI<any>(`/guestbook/${id}`, {
      method: 'PUT',
      body: { content }
    })
  }

  const deleteMessage = (id: number) => {
    return useAPI<any>(`/guestbook/${id}`, {
      method: 'DELETE'
    })
  }

  const getReplies = (
    parentId: number,
    page?: number,
    pageSize?: number
  ) => {
    return useAPI<PaginatedResponse<any>>(`/guestbook/${parentId}/replies`, {
      query: {
        page,
        page_size: pageSize
      }
    })
  }

  const approveMessage = (id: number) => {
    return useAPI<any>(`/admin/guestbook/${id}/approve`, {
      method: 'POST'
    })
  }

  const rejectMessage = (id: number) => {
    return useAPI<any>(`/admin/guestbook/${id}/reject`, {
      method: 'POST'
    })
  }

  const batchAction = (ids: number[], action: string) => {
    return useAPI<any>('/admin/guestbook/batch', {
      method: 'POST',
      body: { ids, action }
    })
  }

  return {
    getMessages,
    getMessage,
    createMessage,
    likeMessage,
    replyMessage,
    updateMessage,
    deleteMessage,
    getReplies,
    approveMessage,
    rejectMessage,
    batchAction
  }
}
