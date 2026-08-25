/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import type { Post, PostCreate, PaginatedResponse } from '~~/types/api'
import { apiFetch } from '~~/composables/useApi'

export const usePosts = () => {
  const { locale } = useI18n()

  // Reactive state for pages that want "store-like" usage
  const posts = ref<Post[]>([])
  const post = ref<Post | null>(null)
  const loading = ref(false)
  const error = ref<unknown>(null)
  const total = ref(0)

  const getPosts = async (params?: {
    page?: number
    page_size?: number
    category?: string
    tag?: string
    search?: string
    status?: string
  }) => {
    return apiFetch<PaginatedResponse<Post>>('/blog/posts', {
      query: {
        lang: locale.value,
        ...params
      }
    })
  }

  const fetchPosts = async (params?: {
    page?: number
    pageSize?: number
    page_size?: number
    category?: string
    tag?: string
    search?: string
    status?: string
  }) => {
    loading.value = true
    error.value = null
    try {
      const query = {
        page: params?.page,
        page_size: params?.page_size ?? params?.pageSize,
        category: params?.category,
        tag: params?.tag,
        search: params?.search,
        status: params?.status
      }
      const data = await getPosts(query)
      posts.value = data.items || (Array.isArray(data) ? data as Post[] : [])
      total.value = (data as PaginatedResponse<Post>)?.total ?? posts.value.length
      return posts.value
    } catch (e) {
      error.value = e
      throw e
    } finally {
      loading.value = false
    }
  }

  const getPost = async (slug: string, password?: string) => {
    return apiFetch<Post>(`/blog/posts/${slug}`, {
      query: {
        lang: locale.value,
        password
      }
    })
  }

  const fetchPost = async (slug: string, password?: string) => {
    loading.value = true
    error.value = null
    try {
      const data = await getPost(slug, password)
      post.value = data || null
      return post.value
    } catch (e) {
      error.value = e
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 相似/推荐型文章内部 helper（基于后端推荐算法）。
   * 仅用于文章详情"相关文章"等单篇关联场景；不在前台主页作为"推荐"概念对外暴露。
   * @internal
   */
  const getSimilarPosts = async (postId: number, limit = 5) => {
    return apiFetch<Post[]>(`/blog/posts/${postId}/similar`, {
      query: {
        lang: locale.value,
        limit
      }
    })
  }

  const likePost = async (postId: number) => {
    return apiFetch(`/blog/posts/${postId}/like`, {
      method: 'POST'
    })
  }

  const createPost = async (postData: PostCreate) => {
    return apiFetch<Post>('/blog/posts', {
      method: 'POST',
      body: postData,
      query: {
        lang: locale.value
      }
    })
  }

  const updatePost = async (postId: number, postData: Partial<PostCreate>) => {
    return apiFetch<Post>(`/blog/posts/${postId}`, {
      method: 'PUT',
      body: postData,
      query: {
        lang: locale.value
      }
    })
  }

  const deletePost = async (postId: number) => {
    return apiFetch(`/blog/posts/${postId}`, {
      method: 'DELETE'
    })
  }

  const batchUpdatePostStatus = async (postIds: number[], status: 'published' | 'draft' | 'scheduled') => {
    return apiFetch<{ success: boolean, message: string, data: { updated_count: number } }>('/blog/posts/batch-status', {
      method: 'POST',
      body: {
        post_ids: postIds,
        status
      }
    })
  }

  return {
    // state
    posts,
    post,
    loading,
    error,
    total,
    // fetch methods
    getPosts,
    fetchPosts,
    getPost,
    fetchPost,
    getSimilarPosts,
    // mutations
    likePost,
    createPost,
    updatePost,
    deletePost,
    batchUpdatePostStatus
  }
}
