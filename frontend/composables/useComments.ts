import { ref } from 'vue'
import type { Comment, PaginatedResponse } from '~~/types/api'
import { useAPI } from '~~/composables/useAPI'

export function useComments() {
  const { locale } = useI18n()

  // ===== Reactive state (like usePosts.ts pattern) =====
  const comments = ref<Comment[]>([])
  const comment = ref<Comment | null>(null)
  const loading = ref(false)
  const loadingSingle = ref(false)
  const error = ref<any>(null)
  const total = ref(0)
  const pageSize = ref(20)

  // ===== Core API wrappers (stateless) =====
  const getComments = (
    post_id: number | string,
    page = 1,
    pageSize_ = 20,
    lang?: string
  ) => {
    return useAPI<PaginatedResponse<Comment>>(`/blog/posts/${post_id}/comments`, {
      query: {
        page,
        page_size: pageSize_,
        lang: lang ?? locale.value
      }
    })
  }

  const getCommentReplies = (
    commentId: number | string,
    page = 1,
    pageSize_ = 20
  ) => {
    return useAPI<PaginatedResponse<Comment>>(`/comments/${commentId}/replies`, {
      query: {
        page,
        page_size: pageSize_
      }
    })
  }

  const createComment = (
    post_id: number | string,
    content: string,
    parent_id?: number,
    nickname?: string,
    email?: string,
    site?: string
  ) => {
    return useAPI<Comment>(`/blog/posts/${post_id}/comments`, {
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

  const likeComment = (id: number | string) => {
    return useAPI<any>(`/comments/${id}/like`, {
      method: 'POST'
    })
  }

  const addCommentReaction = (id: number | string, emoji: string) => {
    return useAPI<any>(`/comments/${id}/reactions`, {
      method: 'POST',
      body: { emoji }
    })
  }

  const removeCommentReaction = (id: number | string, emoji: string) => {
    return useAPI<any>(`/comments/${id}/reactions`, {
      method: 'DELETE',
      body: { emoji }
    })
  }

  const getCommentReactions = (id: number | string) => {
    return useAPI<any>(`/comments/${id}/reactions`)
  }

  const approveComment = (id: number | string) => {
    return useAPI<any>(`/admin/comments/${id}/approve`, {
      method: 'POST'
    })
  }

  const rejectComment = (id: number | string) => {
    return useAPI<any>(`/admin/comments/${id}/reject`, {
      method: 'POST'
    })
  }

  const spamComment = (id: number | string) => {
    return useAPI<any>(`/admin/comments/${id}/spam`, {
      method: 'POST'
    })
  }

  const batchComments = (ids: (number | string)[], action: string) => {
    return useAPI<any>('/admin/comments/batch', {
      method: 'POST',
      body: { ids, action }
    })
  }

  // ===== Stateful fetch helpers =====
  const fetchComments = async (
    post_id: number | string,
    page = 1,
    pageSize_ = 20
  ) => {
    loading.value = true
    error.value = null
    try {
      const { data, error: err } = await getComments(post_id, page, pageSize_)
      if (err.value) throw err.value
      if (data.value) {
        const res = data.value as PaginatedResponse<Comment>
        if (res && Array.isArray(res.items)) {
          comments.value = res.items
          total.value = res.total ?? res.items.length
        } else if (Array.isArray(data.value)) {
          comments.value = data.value as Comment[]
          total.value = comments.value.length
        }
      }
      pageSize.value = pageSize_
      return comments.value
    } catch (e: any) {
      error.value = e
      throw e
    } finally {
      loading.value = false
    }
  }

  const fetchReplies = async (commentId: number | string, page = 1, pageSize_ = 20) => {
    loadingSingle.value = true
    try {
      const { data, error: err } = await getCommentReplies(commentId, page, pageSize_)
      if (err.value) throw err.value
      if (data.value) {
        const res = data.value as PaginatedResponse<Comment>
        return (res && res.items) || (Array.isArray(data.value) ? (data.value as Comment[]) : [])
      }
      return []
    } finally {
      loadingSingle.value = false
    }
  }

  return {
    // state
    comments,
    comment,
    loading,
    loadingSingle,
    error,
    total,
    pageSize,
    // stateless API
    getComments,
    getCommentReplies,
    createComment,
    likeComment,
    addCommentReaction,
    removeCommentReaction,
    getCommentReactions,
    approveComment,
    rejectComment,
    spamComment,
    batchComments,
    // stateful fetch
    fetchComments,
    fetchReplies
  }
}
