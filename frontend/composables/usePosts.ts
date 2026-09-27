/**
 * usePosts —— 文章写操作封装（后台专用）。
 *
 * 只保留 create / update / delete / batch-status 四个动作：前台读取一律在页面 setup 顶层
 * 直接 `useAPI('/blog/posts/...')` 参与 SSR，把 GET 再包一层 composable 只会绕开
 * AsyncData 缓存键，所以这里不放读方法。
 *
 * 路径细节（易踩坑）：
 * - POST `/blog/posts` 与 PUT/DELETE `/blog/posts/{post_id}` 的后台写路径按 **数字 id** 定位，
 *   而前台详情 GET `/blog/posts/{slug}` 按 slug —— 两种形态在后端是不同路由，别互相套用。
 * - `lang` 走 query 而非 body：后端用它决定 i18n 字段回显语言，不参与写入内容。
 */
import type { BaseResponse, Post, PostCreate } from '~~/types/api'
import { apiFetch } from '~~/composables/useApi'

export const usePosts = () => {
  const { locale } = useI18n()

  const createPost = (postData: PostCreate) => {
    return apiFetch<Post>('/blog/posts', {
      method: 'POST',
      body: postData,
      query: { lang: locale.value }
    })
  }

  const updatePost = (postId: number, postData: Partial<PostCreate>) => {
    return apiFetch<Post>(`/blog/posts/${postId}`, {
      method: 'PUT',
      body: postData,
      query: { lang: locale.value }
    })
  }

  const deletePost = (postId: number) => {
    // 后端返回 BaseResponse；调用方只关心成功与否（失败由 apiFetch 抛错 + toast）
    return apiFetch<BaseResponse>(`/blog/posts/${postId}`, { method: 'DELETE' })
  }

  const batchUpdatePostStatus = (
    postIds: number[],
    status: 'published' | 'draft' | 'scheduled'
  ) => {
    return apiFetch<{ success: boolean, message: string, data: { updated_count: number } }>('/blog/posts/batch-status', {
      method: 'POST',
      body: { post_ids: postIds, status }
    })
  }

  return { createPost, updatePost, deletePost, batchUpdatePostStatus }
}
