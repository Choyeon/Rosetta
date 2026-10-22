/**
 * useFavorites —— 收藏域（/api/favorites*）的唯一前端出口。
 *
 * 后端这一族（列表 / 增删 / 收藏夹 CRUD / 按文章移动与备注 / 批量 check）自上线起就绪，
 * 此前前端零消费：用户看到「收到点赞」却没有任何地方能收藏文章。这里按 useComments 的三档分工：
 * - `get*`：setup 顶层的 useAPI（参与 key 缓存，切筛选条件自动重发）；
 * - 动词式：apiFetch（交互/提交，401 自动刷新、失败统一 toast）。
 *
 * 后端契约要点（决定下面为什么这么写）：
 * 1. `POST /favorites` 对重复收藏回 **400**，不是 toggle。所以按钮必须先知道状态
 *    （`POST /favorites/check`），不能"点一下发一次 POST"。
 * 2. `DELETE /favorites/post/{post_id}` 删该 (user, post) 的**全部**行，语义就是"这篇不再收藏"；
 *    按 favorite_id 的 DELETE 只删一行，历史重复行会让"取消没生效"。列表上的取消走 by-post。
 * 3. `PATCH /favorites/post/{post_id}/*` 传 null 表示清空（移回默认收藏 / 清掉备注）。
 * 4. 收藏夹列表回 `{items,total}`；收藏列表回裸分页对象 `{items,total,page,page_size,total_pages}`。
 * 5. `PUT/DELETE /favorites/{favorite_id}`（按行改/删）比 by-post 弱：收藏行没有唯一约束，
 *    按行删只删一条重复行，按行改的 ID 又要在列表里额外透传。正常操作一律走 by-post 那一组，
 *    口径与 §2 同源。唯一例外是 `removeFavoriteById`——文章已删的孤儿收藏行没有 post_id，
 *    by-post 根本无从调用，只能按行 ID 清掉。
 */
import { apiFetch, useAPI, type ApiFetchOptions } from '~~/composables/useApi'

export interface FavoriteFolder {
  id: number
  name: string
  description?: string | null
  is_public?: boolean
  count?: number
  created_at?: string | null
}

export interface FavoriteFolderList {
  items: FavoriteFolder[]
  total: number
}

export interface FavoritePostRef {
  id: number
  /** 后端直接给 Post.title 的 JSON 列：{zh,en,ja,zh_Hant}，渲染前必须过 resolveLocalized。 */
  title: string | Record<string, string>
  slug: string
  cover_image?: string | null
  views?: number
  category?: { id: number, name: string | Record<string, string>, color?: string } | null
  published_at?: string | null
}

export interface FavoriteRow {
  id: number
  note?: string | null
  folder_id?: number | null
  created_at?: string | null
  post?: FavoritePostRef | null
}

/** POST /favorites/check 的 data：以文章 ID 字符串为键。 */
export interface FavoriteCheckEntry {
  is_favorited: boolean
  favorite_id: number | null
}

export interface FavoriteCheckResult {
  favorites: Record<string, FavoriteCheckEntry>
}

export interface FavoriteActionResponse {
  success?: boolean
  message?: string
}

export function useFavorites() {
  // ===== setup 顶层（AsyncData）=====
  // 列表本身不在此封装：/account 的收藏档位要带 folder_id 筛选、且与 tab/page 共用
  // 同一条 useAPI 链（url/key 随档位变），封装成固定签名的 wrapper 反而逼页面绕开单源。
  const getFavoriteFolders = () =>
    useAPI<FavoriteFolderList>('/favorites/folders', { key: 'favorites:folders' })

  // ===== 交互/提交（apiFetch）=====
  const checkFavorites = (postIds: number[], options?: ApiFetchOptions) =>
    apiFetch<FavoriteCheckResult>('/favorites/check', {
      method: 'POST',
      body: { post_ids: postIds },
      ...options
    })

  const addFavorite = (postId: number, body?: { folder_id?: number | null, note?: string | null }) =>
    apiFetch<FavoriteActionResponse>('/favorites', {
      method: 'POST',
      body: { post_id: postId, ...body }
    })

  const removeFavoriteByPost = (postId: number) =>
    apiFetch<FavoriteActionResponse>(`/favorites/post/${postId}`, { method: 'DELETE' })

  /**
   * 按收藏行 ID 取消——只给"文章已删/不可见"的孤儿行兜底用：那种行拿不到 post_id，
   * by-post 的口根本没有入参，用户就永远清不掉它。正常收藏一律走 by-post（见 §2）。
   */
  const removeFavoriteById = (favoriteId: number) =>
    apiFetch<FavoriteActionResponse>(`/favorites/${favoriteId}`, { method: 'DELETE' })

  const moveFavoriteByPost = (postId: number, folderId: number | null) =>
    apiFetch<FavoriteActionResponse>(`/favorites/post/${postId}/folder`, {
      method: 'PATCH',
      body: { folder_id: folderId }
    })

  const setFavoriteNote = (postId: number, note: string | null) =>
    apiFetch<FavoriteActionResponse>(`/favorites/post/${postId}/note`, {
      method: 'PATCH',
      body: { note }
    })

  const createFolder = (name: string, description?: string | null) =>
    apiFetch<FavoriteActionResponse>('/favorites/folders', {
      method: 'POST',
      body: { name, description: description || null }
    })

  const updateFolder = (folderId: number, patch: { name?: string, description?: string | null }) =>
    apiFetch<FavoriteActionResponse>(`/favorites/folders/${folderId}`, {
      method: 'PUT',
      body: patch
    })

  const deleteFolder = (folderId: number) =>
    apiFetch<FavoriteActionResponse>(`/favorites/folders/${folderId}`, { method: 'DELETE' })

  return {
    getFavoriteFolders,
    checkFavorites,
    addFavorite,
    removeFavoriteByPost,
    removeFavoriteById,
    moveFavoriteByPost,
    setFavoriteNote,
    createFolder,
    updateFolder,
    deleteFolder
  }
}
