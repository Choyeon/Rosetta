/**
 * Rosetta 开发文档目录 & 加载器（Vue Composable）。
 *
 * 数据源：后端公开接口 GET /api/docs/list 与 GET /api/docs/{slug}。
 * 渲染：在 docs 页面中使用 marked + marked-highlight + highlight.js 做
 * 客户端渲染；若任一侧加载失败则回退为纯 marked 渲染（无语法高亮），
 * 保证即使生产构建时因各种原因未安装 highlight.js 也能正常看文档。
 */

import { apiFetch } from '~~/composables/useApi'

export interface DocsCatalogItem {
  slug: string
  title: string
  category: string
  order: number
  description: string
  available: boolean
}

export interface DocsCatalogData {
  items: DocsCatalogItem[]
  language: string
  docs_dir?: string
}

export interface DocsDocData {
  slug: string
  title: string
  markdown: string
  language: string
}

const _CATALOG_KEY = 'rosetta:docs:catalog'
const DOC_CACHE_TTL_MS = 5 * 60 * 1000 // 5 分钟；文档几乎不变，避免重复请求

let _catalogPromise: Promise<DocsCatalogData> | null = null
let _catalogFetchedAt = 0
const _docCache = new Map<string, { at: number, data: DocsDocData }>()

function _cacheFresh(at: number, ttl = DOC_CACHE_TTL_MS): boolean {
  return Date.now() - at < ttl
}

/**
 * 拉取文档目录（带简单内存缓存）。
 * 同一次请求 / 同一导航过程中多次调用只发一次网络。
 */
export async function fetchDocsCatalog(force = false): Promise<DocsCatalogData> {
  if (
    !force
    && _catalogPromise
    && _cacheFresh(_catalogFetchedAt)
  ) {
    return _catalogPromise
  }
  _catalogFetchedAt = Date.now()
  _catalogPromise = (async () => {
    const resp = await apiFetch<{
      success: boolean
      data: DocsCatalogData
    }>(
      '/api/docs/list',
      { method: 'GET', silentToast: false }
    )
    if (!resp?.success || !resp.data) {
      // 后端异常时至少返回静态目录，避免页面空白
      return {
        items: [
          { slug: 'index', title: '开发文档首页', category: '概览', order: 0, description: '', available: true },
          { slug: 'rest-api', title: 'REST API 参考', category: '接口', order: 10, description: '', available: true },
          { slug: 'theme-tutorial', title: '主题开发教程', category: '教程', order: 20, description: '', available: true },
          { slug: 'plugin-tutorial', title: '插件开发教程', category: '教程', order: 30, description: '', available: true }
        ],
        language: 'zh-CN'
      } satisfies DocsCatalogData
    }
    return resp.data
  })().catch((err) => {
    // 失败后清除 promise，下一次调用可重试
    _catalogPromise = null
    _catalogFetchedAt = 0
    throw err
  })
  return _catalogPromise
}

/**
 * 读取单篇文档（带内存缓存）。
 */
export async function fetchDocsDoc(slug: string, force = false): Promise<DocsDocData> {
  const key = slug || 'index'
  const cached = _docCache.get(key)
  if (!force && cached && _cacheFresh(cached.at)) {
    return cached.data
  }
  const resp = await apiFetch<{
    success: boolean
    data: DocsDocData
  }>(
    `/api/docs/${encodeURIComponent(key)}`,
    { method: 'GET', silentToast: false }
  )
  if (!resp?.success || !resp.data) {
    throw new Error(`加载文档失败: ${key}`)
  }
  _docCache.set(key, { at: Date.now(), data: resp.data })
  return resp.data
}

/**
 * 工具：按 category 分组（供左侧子目录渲染）。
 */
export function groupByCategory(items: DocsCatalogItem[]) {
  const groups = new Map<string, DocsCatalogItem[]>()
  for (const it of items) {
    const list = groups.get(it.category) ?? []
    list.push(it)
    groups.set(it.category, list)
  }
  return Array.from(groups.entries()).map(([category, list]) => ({
    category,
    items: [...list].sort((a, b) => a.order - b.order)
  }))
}

export function useDocsCatalog() {
  return {
    fetchDocsCatalog,
    fetchDocsDoc,
    groupByCategory
  }
}
