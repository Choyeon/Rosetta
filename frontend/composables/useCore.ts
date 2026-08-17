import type {
  Category,
  Tag,
  SiteConfig,
  Navigation,
  FriendLink,
  ArchiveMonth,
  SiteStats,
  Page,
  Sponsor,
  PaginatedResponse
} from '~~/types/api'
import { useAPI } from '~~/composables/useAPI'

export const useCategories = () => {
  const { locale } = useI18n()

  const getCategories = () => {
    return useAPI<Category[]>('/blog/categories', {
      query: { lang: locale.value }
    })
  }

  const getCategory = (slug: string) => {
    return useAPI<Category>(`/blog/categories/slug/${slug}`, {
      query: { lang: locale.value }
    })
  }

  const createCategory = (data: Partial<Category>) => {
    return useAPI<Category>('/blog/categories', {
      method: 'POST',
      body: data,
      query: { lang: locale.value }
    })
  }

  const updateCategory = (categoryId: number, data: Partial<Category>) => {
    return useAPI<Category>(`/blog/categories/${categoryId}`, {
      method: 'PUT',
      body: data,
      query: { lang: locale.value }
    })
  }

  const deleteCategory = (categoryId: number) => {
    return useAPI<unknown>(`/blog/categories/${categoryId}`, {
      method: 'DELETE'
    })
  }

  return {
    getCategories,
    getCategory,
    createCategory,
    updateCategory,
    deleteCategory
  }
}

export const useTags = () => {
  const { locale } = useI18n()

  const getTags = () => {
    return useAPI<Tag[]>('/blog/tags', {
      query: { lang: locale.value }
    })
  }

  const getTag = (slug: string) => {
    return useAPI<Tag>(`/blog/tags/slug/${slug}`, {
      query: { lang: locale.value }
    })
  }

  const createTag = (data: Partial<Tag>) => {
    return useAPI<Tag>('/blog/tags', {
      method: 'POST',
      body: data,
      query: { lang: locale.value }
    })
  }

  const updateTag = (tagId: number, data: Partial<Tag>) => {
    return useAPI<Tag>(`/blog/tags/${tagId}`, {
      method: 'PUT',
      body: data,
      query: { lang: locale.value }
    })
  }

  const deleteTag = (tagId: number) => {
    return useAPI<unknown>(`/blog/tags/${tagId}`, {
      method: 'DELETE'
    })
  }

  return {
    getTags,
    getTag,
    createTag,
    updateTag,
    deleteTag
  }
}

export const useSiteConfig = () => {
  const getSiteConfig = () => {
    return useAPI<SiteConfig>('/config')
  }

  return {
    getSiteConfig
  }
}

export const useNavigations = () => {
  const getNavigations = (location?: string) => {
    return useAPI<Navigation[]>('/navigations', {
      query: location ? { location } : {}
    })
  }

  const getAdminNavigations = () => {
    return useAPI<Navigation[]>('/admin/navigations')
  }

  const createNavigation = (data: Partial<Navigation>) => {
    return useAPI<Navigation>('/navigations', {
      method: 'POST',
      body: data
    })
  }

  const updateNavigation = (navId: number, data: Partial<Navigation>) => {
    return useAPI<Navigation>(`/navigations/${navId}`, {
      method: 'PUT',
      body: data
    })
  }

  const deleteNavigation = (navId: number) => {
    return useAPI<unknown>(`/navigations/${navId}`, {
      method: 'DELETE'
    })
  }

  return {
    getNavigations,
    getAdminNavigations,
    createNavigation,
    updateNavigation,
    deleteNavigation
  }
}

export const useFriendLinks = () => {
  const getFriendLinks = () => {
    return useAPI<FriendLink[]>('/friend-links')
  }

  const createFriendLink = (data: Partial<FriendLink>) => {
    return useAPI<FriendLink>('/friend-links', {
      method: 'POST',
      body: data
    })
  }

  const updateFriendLink = (linkId: number, data: Partial<FriendLink>) => {
    return useAPI<FriendLink>(`/friend-links/${linkId}`, {
      method: 'PUT',
      body: data
    })
  }

  const deleteFriendLink = (linkId: number) => {
    return useAPI<unknown>(`/friend-links/${linkId}`, {
      method: 'DELETE'
    })
  }

  return {
    getFriendLinks,
    createFriendLink,
    updateFriendLink,
    deleteFriendLink
  }
}

export const useArchive = () => {
  const { locale } = useI18n()

  const getArchive = (limitPerMonth = 50) => {
    return useAPI<ArchiveMonth[]>('/blog/archive', {
      query: {
        lang: locale.value,
        limit_per_month: limitPerMonth
      }
    })
  }

  const getArchiveByYear = (year: number) => {
    return useAPI<ArchiveMonth[]>(`/blog/archive/${year}`, {
      query: { lang: locale.value }
    })
  }

  const getArchiveByMonth = (year: number, month: number, page = 1, pageSize = 20) => {
    return useAPI(`/blog/archive/${year}/${month}`, {
      query: {
        lang: locale.value,
        page,
        page_size: pageSize
      }
    })
  }

  const getArchiveStats = () => {
    return useAPI('/blog/archive/stats')
  }

  return {
    getArchive,
    getArchiveByYear,
    getArchiveByMonth,
    getArchiveStats
  }
}

export const useSiteStats = () => {
  const getSiteStats = () => {
    return useAPI<SiteStats>('/blog/site-stats')
  }

  return {
    getSiteStats
  }
}

export const usePages = () => {
  const { locale } = useI18n()

  const getPages = (params?: { page?: number, pageSize?: number }) => {
    return useAPI<PaginatedResponse<Page>>('/pages', {
      query: {
        lang: locale.value,
        ...params
      }
    })
  }

  const getPage = (slug: string) => {
    return useAPI<Page>(`/pages/${slug}`, {
      query: { lang: locale.value }
    })
  }

  const createPage = (data: Partial<Page>) => {
    return useAPI<Page>('/pages', {
      method: 'POST',
      body: data,
      query: { lang: locale.value }
    })
  }

  const updatePage = (pageId: number, data: Partial<Page>) => {
    return useAPI<Page>(`/pages/${pageId}`, {
      method: 'PUT',
      body: data,
      query: { lang: locale.value }
    })
  }

  const deletePage = (pageId: number) => {
    return useAPI<unknown>(`/pages/${pageId}`, {
      method: 'DELETE'
    })
  }

  return {
    getPages,
    getPage,
    createPage,
    updatePage,
    deletePage
  }
}

export const useSponsors = () => {
  const getSponsors = (params?: { page?: number, pageSize?: number }) => {
    return useAPI<PaginatedResponse<Sponsor>>('/sponsors', {
      query: params
    })
  }

  return {
    getSponsors
  }
}

export const useSearchPlaceholders = () => {
  const getSearchPlaceholders = () => {
    return useAPI<string[]>('/search-placeholders')
  }

  return {
    getSearchPlaceholders
  }
}

export const useSiteFullConfig = () => {
  const getSiteFullConfig = () => {
    return useAPI<Record<string, unknown>>('/config/full')
  }

  const updateSettings = (settings: Record<string, unknown>) => {
    return useAPI<unknown>('/admin/settings', {
      method: 'POST',
      body: settings
    })
  }

  return {
    getSiteFullConfig,
    updateSettings
  }
}
