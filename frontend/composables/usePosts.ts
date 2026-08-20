/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import type { Post, PostCreate, PaginatedResponse } from '~~/types/api'
import { useAPI } from '~~/composables/useApi'

export const usePosts = () => {
  const { locale } = useI18n()

  // Reactive state for pages that want "store-like" usage
  const posts = ref<Post[]>([])
  const post = ref<Post | null>(null)
  const loading = ref(false)
  const error = ref<unknown>(null)
  const total = ref(0)

  const getPosts = (params?: {
    page?: number
    page_size?: number
    category?: string
    tag?: string
    search?: string
    status?: string
  }) => {
    return useAPI<PaginatedResponse<Post>>('/blog/posts', {
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
      const { data, error: err } = await getPosts(query)
      if (err.value) throw err.value
      if (data.value) {
        posts.value = data.value.items || (Array.isArray(data.value) ? data.value as Post[] : [])
        total.value = (data.value as PaginatedResponse<Post>)?.total ?? posts.value.length
      }
      return posts.value
    } catch (e) {
      error.value = e
      throw e
    } finally {
      loading.value = false
    }
  }

  const getPost = (slug: string, password?: string) => {
    return useAPI<Post>(`/blog/posts/${slug}`, {
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
      const { data, error: err } = await getPost(slug, password)
      if (err.value) throw err.value
      post.value = data.value || null
      return post.value
    } catch (e) {
      error.value = e
      throw e
    } finally {
      loading.value = false
    }
  }

  const getRecommendedPosts = (page = 1, pageSize = 12) => {
    return useAPI<PaginatedResponse<Post>>('/blog/posts/recommended', {
      query: {
        lang: locale.value,
        page,
        page_size: pageSize
      }
    })
  }

  const getSimilarPosts = (postId: number, limit = 5) => {
    return useAPI<Post[]>(`/blog/posts/${postId}/similar`, {
      query: {
        lang: locale.value,
        limit
      }
    })
  }

  const likePost = (postId: number) => {
    return useAPI(`/blog/posts/${postId}/like`, {
      method: 'POST'
    })
  }

  const createPost = (postData: PostCreate) => {
    return useAPI<Post>('/blog/posts', {
      method: 'POST',
      body: postData,
      query: {
        lang: locale.value
      }
    })
  }

  const updatePost = (postId: number, postData: Partial<PostCreate>) => {
    return useAPI<Post>(`/blog/posts/${postId}`, {
      method: 'PUT',
      body: postData,
      query: {
        lang: locale.value
      }
    })
  }

  const deletePost = (postId: number) => {
    return useAPI(`/blog/posts/${postId}`, {
      method: 'DELETE'
    })
  }

  const batchUpdatePostStatus = (postIds: number[], status: 'published' | 'draft' | 'scheduled') => {
    return useAPI<{ success: boolean, message: string, data: { updated_count: number } }>('/blog/posts/batch-status', {
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
    // raw AsyncData methods
    getPosts,
    getPost,
    getRecommendedPosts,
    getSimilarPosts,
    // stateful fetch methods
    fetchPosts,
    fetchPost,
    // mutations
    likePost,
    createPost,
    updatePost,
    deletePost,
    batchUpdatePostStatus
  }
}
