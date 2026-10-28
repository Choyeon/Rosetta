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
 *
 * 例外一档：`loadCommentReactions` 是 `apiFetch` GET，按**单条评论**在交互时拉表情统计——
 * 既不是 setup 顶层的 `get*`（AsyncData 口），也不写回 state，所以不叫 `fetch*`。
 * 后端没有批量反应口，逐条预取就是 N+1，因此只在点开反应条时拉一次。
 */
import { ref, shallowRef } from 'vue'
import type { Comment, PaginatedResponse } from '~~/types/api'
import { useAPI, apiFetch, type ApiFetchOptions } from '~~/composables/useApi'

/** GET /comments/{id}/reactions 的单档统计（reacted 只对当前登录用户有意义） */
export interface CommentReactionSummary {
  emoji: string
  count: number
  reacted: boolean
}

export interface CommentReactionSummaryList {
  comment_id: number
  reactions: CommentReactionSummary[]
  total: number
}

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

  const loadCommentReactions = (id: number | string) => {
    return apiFetch<CommentReactionSummaryList>(`/comments/${id}/reactions`)
  }

  // ===== 提交/交互类（apiFetch，可在回调、onMounted、watch 里调用） =====
  /**
   * 发表评论。
   *
   * 走 `POST /api/posts/{id_or_slug}/comments`（api/comments.py::create_comment），**不是**
   * `POST /api/blog/posts/{id}/comments`：后者挂了 `CurrentUser`，匿名请求直接 401，
   * 于是后台「允许访客匿名评论」这个开关在前台永远没有执行点（表单只给登录用户渲染，
   * 访客连输入框都看不到）。comments.py 那条口是 `CurrentUserOptional` + 同 IP 频控 +
   * CSRF，评论服务里的 allow_guest / 验证码 / 审核闸门也都挂在它身上。
   * （blog.py 的那条重复写口现已删除，只剩 `GET /blog/posts/{id}/comments` 读口在用。）
   */
  const createComment = (
    post_id: number | string,
    payload: {
      content: string
      parent_id?: number | null
      author_name?: string
      author_email?: string
      author_website?: string
      qq?: string
      github?: string
      captcha_key?: string
      captcha_code?: string
    },
    headers?: Record<string, string>
  ) => {
    return apiFetch<Comment>(`/posts/${post_id}/comments`, {
      method: 'POST',
      query: { lang: locale.value },
      headers,
      body: {
        content: payload.content,
        parent_id: payload.parent_id ?? undefined,
        author_name: payload.author_name,
        author_email: payload.author_email,
        author_website: payload.author_website,
        // 访客身份两项不发就等于"这条口永远只能靠邮箱 gravatar"：解析器认 github / qq，
        // 但字段没人发，头像解析在生产库里对访客一律落到 gravatar 或空。
        qq: payload.qq,
        github: payload.github,
        captcha_key: payload.captcha_key,
        captcha_code: payload.captcha_code
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
    // 取消反应的真源路由把 emoji 放在**路径**上（api/comment_reactions.py
    // @router.delete("/comments/{comment_id}/reactions/{emoji}")）。
    // 写成 DELETE /comments/{id}/reactions + body 会命中集合路径的 405，
    // emoji 永远解不掉——界面点亮了就再也取消不了。
    return apiFetch<unknown>(`/comments/${id}/reactions/${encodeURIComponent(emoji)}`, {
      method: 'DELETE'
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
    // 提交/交互
    loadCommentReactions,
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
