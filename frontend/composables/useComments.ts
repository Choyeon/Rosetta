import { ref } from 'vue'
import type { Comment, PaginatedResponse } from '~~/types/api'
import { useAPI, apiFetch, type ApiFetchOptions } from '~~/composables/useAPI'

export function useComments() {
  const { locale } = useI18n()

  // ===== Reactive state (like usePosts.ts pattern) =====
  const comments = ref<Comment[]>([])
  const comment = ref<Comment | null>(null)
  const loading = ref(false)
  const loadingSingle = ref(false)
  const error = ref<unknown>(null)
  const total = ref(0)
  const pageSize = ref(20)

  // ===== Setup-level AsyncData wrappers (useFetch based, MUST call at setup top-level) =====
  const getComments = (
    post_id: number | string,
    page = 1,
    pageSize_ = 20,
    lang?: string
  ) => {
    return useAPI<PaginatedResponse<Comment>>(`/posts/${post_id}/comments`, {
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

  const getCommentReactions = (id: number | string) => {
    return useAPI<unknown>(`/comments/${id}/reactions`)
  }

  // ===== Imperative wrappers ($fetch based, safe anywhere: callbacks, onMounted, watch) =====
  const createComment = (
    post_id: number | string,
    content: string,
    parent_id?: number,
    nickname?: string,
    email?: string,
    site?: string
  ) => {
    return apiFetch<Comment>(`/posts/${post_id}/comments`, {
      method: 'POST',
      query: { lang: locale.value },
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
    return apiFetch<unknown>(`/comments/${id}/like`, {
      method: 'POST'
    })
  }

  const addCommentReaction = (id: number | string, emoji: string) => {
    return apiFetch<unknown>(`/comments/${id}/reactions`, {
      method: 'POST',
      body: { emoji }
    })
  }

  const removeCommentReaction = (id: number | string, emoji: string) => {
    return apiFetch<unknown>(`/comments/${id}/reactions`, {
      method: 'DELETE',
      body: { emoji }
    })
  }

  const approveComment = (id: number | string) => {
    return apiFetch<unknown>(`/admin/comments/${id}/approve`, {
      method: 'POST'
    })
  }

  const rejectComment = (id: number | string) => {
    return apiFetch<unknown>(`/admin/comments/${id}/reject`, {
      method: 'POST'
    })
  }

  const spamComment = (id: number | string) => {
    return apiFetch<unknown>(`/admin/comments/${id}/spam`, {
      method: 'POST'
    })
  }

  const batchComments = (ids: (number | string)[], action: string) => {
    return apiFetch<unknown>('/admin/comments/batch', {
      method: 'POST',
      body: { ids, action }
    })
  }

  // ===== Stateful fetch helpers ($fetch based, safe anywhere) =====
  const fetchComments = async (
    post_id: number | string,
    page = 1,
    pageSize_ = 20
  ) => {
    loading.value = true
    error.value = null
    try {
      const opts: ApiFetchOptions = {
        query: {
          page,
          page_size: pageSize_,
          lang: locale.value
        }
      }
      const res = await apiFetch<PaginatedResponse<Comment> | Comment[]>(`/posts/${post_id}/comments`, opts)
      if (res) {
        if (Array.isArray(res)) {
          comments.value = res as Comment[]
          total.value = res.length
        } else {
          const paginated = res as PaginatedResponse<Comment>
          if (Array.isArray(paginated.items)) {
            comments.value = paginated.items
            total.value = paginated.total ?? paginated.items.length
          } else {
            comments.value = []
            total.value = 0
          }
        }
      } else {
        comments.value = []
        total.value = 0
      }
      pageSize.value = pageSize_
      return comments.value
    } catch (e) {
      error.value = e
      throw e
    } finally {
      loading.value = false
    }
  }

  const fetchReplies = async (commentId: number | string, page = 1, pageSize_ = 20) => {
    loadingSingle.value = true
    try {
      const opts: ApiFetchOptions = {
        query: {
          page,
          page_size: pageSize_
        }
      }
      const res = await apiFetch<PaginatedResponse<Comment> | Comment[]>(`/comments/${commentId}/replies`, opts)
      if (Array.isArray(res)) return res
      if (res && Array.isArray((res as PaginatedResponse<Comment>).items)) {
        return (res as PaginatedResponse<Comment>).items
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
    // setup-level AsyncData wrappers
    getComments,
    getCommentReplies,
    getCommentReactions,
    // imperative wrappers
    createComment,
    likeComment,
    addCommentReaction,
    removeCommentReaction,
    approveComment,
    rejectComment,
    spamComment,
    batchComments,
    // stateful fetch
    fetchComments,
    fetchReplies
  }
}
