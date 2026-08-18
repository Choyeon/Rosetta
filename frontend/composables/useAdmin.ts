/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import type {
  AdminStats,
  ViewTrendPoint,
  CategoryStat,
  AdminUserListParams,
  AdminUserCreate,
  AdminUserUpdate,
  ResetPasswordRequest,
  PaginatedResponse,
  User,
  Comment,
  AdminCommentListParams,
  CommentBatchAction,
  MockDataConfig,
  UnusedImage,
  BackupInfo,
  BackupItem,
  RestoreRequest,
  BaseResponse
} from '~~/types/api'
import { useAPI } from '~~/composables/useApi'

export const useAdminStats = () => {
  return useAPI<AdminStats>('/admin/stats')
}

export const useViewTrends = (days = 7) => {
  return useAPI<ViewTrendPoint[]>('/admin/view-trends', {
    query: { days }
  })
}

export const useCategoryStats = () => {
  return useAPI<CategoryStat[]>('/admin/category-stats')
}

export const useAdminUsers = () => {
  const getUsers = (params?: AdminUserListParams) => {
    const query = {
      page: params?.page,
      page_size: params?.page_size ?? params?.pageSize,
      search: params?.search,
      role: params?.role,
      is_active: params?.is_active ?? params?.isActive
    }
    return useAPI<PaginatedResponse<User>>('/admin/users', { query })
  }

  const createUser = (data: AdminUserCreate) => {
    return useAPI<User>('/admin/users', {
      method: 'POST',
      body: data
    })
  }

  const getUserDetail = (userId: number) => {
    return useAPI<User>(`/admin/users/${userId}`)
  }

  const updateUser = (userId: number, data: AdminUserUpdate, method: 'PUT' | 'PATCH' = 'PUT') => {
    return useAPI<User>(`/admin/users/${userId}`, {
      method,
      body: data
    })
  }

  const resetUserPassword = (userId: number, data: ResetPasswordRequest) => {
    return useAPI<BaseResponse>(`/admin/users/${userId}/reset-password`, {
      method: 'POST',
      body: data
    })
  }

  const deleteUser = (userId: number) => {
    return useAPI<BaseResponse>(`/admin/users/${userId}`, {
      method: 'DELETE'
    })
  }

  const activateUser = (userId: number) => {
    return useAPI<BaseResponse>(`/admin/users/${userId}/activate`, {
      method: 'POST'
    })
  }

  const banUser = (userId: number) => {
    return useAPI<BaseResponse>(`/admin/users/${userId}/ban`, {
      method: 'POST'
    })
  }

  const unbanUser = (userId: number) => {
    return useAPI<BaseResponse>(`/admin/users/${userId}/unban`, {
      method: 'POST'
    })
  }

  return {
    getUsers,
    createUser,
    getUserDetail,
    updateUser,
    resetUserPassword,
    deleteUser,
    activateUser,
    banUser,
    unbanUser
  }
}

export const useAdminComments = () => {
  const getComments = (params?: AdminCommentListParams) => {
    const query = {
      page: params?.page,
      page_size: params?.page_size ?? params?.pageSize,
      status: params?.status
    }
    return useAPI<PaginatedResponse<Comment>>('/admin/comments', { query })
  }

  const setCommentActive = (commentId: number, active: boolean) => {
    return useAPI<Comment>(`/admin/comments/${commentId}`, {
      method: 'PATCH',
      body: { active }
    })
  }

  const deleteComment = (commentId: number) => {
    return useAPI<BaseResponse>(`/admin/comments/${commentId}`, {
      method: 'DELETE'
    })
  }

  const approveComment = (commentId: number) => {
    return useAPI<Comment>(`/admin/comments/${commentId}/approve`, {
      method: 'POST'
    })
  }

  const rejectComment = (commentId: number) => {
    return useAPI<Comment>(`/admin/comments/${commentId}/reject`, {
      method: 'POST'
    })
  }

  const markCommentAsSpam = (commentId: number) => {
    return useAPI<Comment>(`/admin/comments/${commentId}/spam`, {
      method: 'POST'
    })
  }

  const batchAction = (data: CommentBatchAction) => {
    return useAPI<BaseResponse>('/admin/comments/batch', {
      method: 'POST',
      body: data
    })
  }

  return {
    getComments,
    setCommentActive,
    deleteComment,
    approveComment,
    rejectComment,
    markCommentAsSpam,
    batchAction
  }
}

export const useAdminTools = () => {
  const mockData = (config: MockDataConfig) => {
    return useAPI<BaseResponse>('/admin/tools/mock-data', {
      method: 'POST',
      body: config
    })
  }

  const getUnusedImages = () => {
    return useAPI<UnusedImage[]>('/admin/tools/unused-images')
  }

  const cleanUnusedImages = () => {
    return useAPI<BaseResponse>('/admin/tools/unused-images', {
      method: 'POST'
    })
  }

  return {
    mockData,
    getUnusedImages,
    cleanUnusedImages
  }
}

export const useAdminExport = () => {
  const exportPosts = () => {
    return useAPI<Blob>('/admin/export/posts')
  }

  const exportMarkdown = () => {
    return useAPI<Blob>('/admin/export/markdown')
  }

  return {
    exportPosts,
    exportMarkdown
  }
}

export const useAdminImport = () => {
  const importPosts = (data: FormData | unknown) => {
    return useAPI<BaseResponse>('/admin/import/posts', {
      method: 'POST',
      body: data
    })
  }

  const importMarkdown = (data: FormData | unknown) => {
    return useAPI<BaseResponse>('/admin/import/markdown', {
      method: 'POST',
      body: data
    })
  }

  return {
    importPosts,
    importMarkdown
  }
}

export const useBackup = () => {
  const getBackupInfo = () => {
    return useAPI<BackupInfo>('/admin/backup')
  }

  const fullBackup = () => {
    return useAPI<BackupItem>('/admin/backup/full', {
      method: 'GET'
    })
  }

  const restore = (data: RestoreRequest) => {
    return useAPI<BaseResponse>('/admin/backup/restore', {
      method: 'POST',
      body: data
    })
  }

  return {
    getBackupInfo,
    fullBackup,
    restore
  }
}
