/**
 * useComments —— 评论域的客户端绑定（对应 /api/blog/posts/{id}/comments 与 /api/comments/*）。
 *
 * 三档封装的取舍（全项目统一，见 useApi.ts）：
 * - `get*`：setup 顶层调用的 `useAPI`（AsyncData），参与 SSR 首屏与 key 缓存，
 *   放进回调/onMounted 里会拿不到 Nuxt 上下文 → 只能 setup 顶层用。
 * - 动词式（createComment / likeComment / approveComment …）：`apiFetch`，
 *   用户交互与提交走这条，401 自动刷新 token、失败统一 toast。
 * - `fetch*`：`apiFetch` + 写回本 composable 的 state（comments/total/loading），
 *   给"点了按钮之后重新拉列表"这类需要驱动视图的场景。
 *
 * 后台审核类（approve/reject/spam/batch）只是前台视角的薄封装；
 * 评论管理页的实现在 useAdminManage.ts（带分页/筛选的完整列表契约）。
 */
import { ref, shallowRef } from 'vue'
import type { Comment, PaginatedResponse } from '~~/types/api'
import { useAPI, apiFetch, type ApiFetchOptions } from '~~/composables/useApi'

export function useComments() {
  const { locale } = useI18n()

  // ===== Reactive state（shallowRef：fetchComments 全是整赋值 comments.value = X，
  //       不做 push/splice/单条嵌套字段 mutate；浅层代理减少 100+ 长列表首帧 CPU） =====
  const comments = shallowRef<Comment[]>([])
  const loading = ref(false)
  const loadingSingle = ref(false)
  const error = ref<unknown>(null)
  const total = ref(0)
  const pageSize = ref(20)

  // ===== Setup-level AsyncData wrappers（useAPI → useFetch，必须在 setup 顶层调用） =====
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

  const getCommentReactions = (id: number | string) => {
    return useAPI<unknown>(`/comments/${id}/reactions`)
  }

  // ===== 提交/交互类（apiFetch，可在回调、onMounted、watch 里调用） =====
  const createComment = (
    post_id: number | string,
    content: string,
    parent_id?: number,
    nickname?: string,
    email?: string,
    site?: string
  ) => {
    return apiFetch<Comment>(`/blog/posts/${post_id}/comments`, {
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

  // ===== 会写回上面 state 的拉取（apiFetch，可在任意位置调用） =====
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
      const res = await apiFetch<PaginatedResponse<Comment> | Comment[]>(`/blog/posts/${post_id}/comments`, opts)
      if (res) {
        // 裸数组是历史契约（后端未分页时代返回 List[Comment]）；现在只有降级路径会命中，
        // 保留分支是为了响应形态变化时不白屏，而不是把 total 悄悄写成 0。
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
    loading,
    loadingSingle,
    error,
    total,
    pageSize,
    // setup 顶层 AsyncData 封装
    getComments,
    getCommentReplies,
    getCommentReactions,
    // 提交/交互
    createComment,
    likeComment,
    addCommentReaction,
    removeCommentReaction,
    approveComment,
    rejectComment,
    spamComment,
    batchComments,
    // 拉取并写回 state
    fetchComments,
    fetchReplies
  }
}
