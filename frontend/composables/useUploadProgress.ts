/**
 * useUploadProgress —— 媒体库「带进度」上传队列（POST 到 <baseURL>/media/library）。
 * 刻意不用 apiFetch：ofetch 在浏览器端取不到 upload 进度，这里用 XMLHttpRequest 自己拼
 * Authorization + X-CSRF-Token（cookie `csrf_token`，后端双提交），401 刷新后只重试一次。
 * MAX_UPLOAD_BYTES 与扩展名白名单只是客户端预筛（口径跟后端对齐，不承担安全职责）。
 * 队列项 id 是本地生成的（不是 Media.id），removeItem 必须顺手 abort 在飞的 XHR，
 * 且「用户主动中断」单列 aborted 计数，不能和 failed 混在一起。
 */

import { extractApiErrorMessage } from '~~/lib/utils'
import { useAuthStore } from '~~/stores/auth'

/** 单文件上传大小上限：20MB（与后端 _save_media_to_library 的 MAX_UPLOAD_BYTES 对齐）。 */
export const MAX_UPLOAD_BYTES = 20 * 1024 * 1024

/** 允许上传的扩展名白名单（与后端 allowed_types 保持一致）。 */
export const ALLOWED_UPLOAD_EXTENSIONS: readonly string[] = [
  'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg',
  'mp4', 'webm', 'mov',
  'mp3', 'wav', 'ogg',
  'pdf', 'doc', 'docx', 'xls', 'xlsx'
]

export type UploadItemStatus = 'uploading' | 'success' | 'error'

/** 单个文件的最终结局：失败与「用户主动中断」要分开统计。 */
export type UploadOutcome = 'success' | 'failed' | 'aborted'

export interface UploadQueueItem {
  /** 前端本地生成的队列 id（非后端 Media.id） */
  id: string
  filename: string
  size_bytes: number
  /** 0-100 */
  progress: number
  status: UploadItemStatus
  error?: string
}

export interface FileRejection {
  name: string
  reason: string
}

export interface FileValidationResult {
  accepted: File[]
  rejected: FileRejection[]
}

function extensionOf(filename: string): string {
  const idx = filename.lastIndexOf('.')
  return idx >= 0 ? filename.slice(idx + 1).toLowerCase() : ''
}

/**
 * 客户端预校验：大小 ≤20MB + 扩展名白名单。
 * 在真正发起上传前过滤，被拒绝的文件带原因返回，由调用方统一 toast。
 */
export function validateUploadFiles(files: File[]): FileValidationResult {
  const accepted: File[] = []
  const rejected: FileRejection[] = []
  for (const file of files) {
    const ext = extensionOf(file.name)
    if (!ALLOWED_UPLOAD_EXTENSIONS.includes(ext)) {
      rejected.push({ name: file.name, reason: `不支持的文件类型 .${ext || '?'}` })
      continue
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      rejected.push({ name: file.name, reason: `文件过大（${(file.size / 1024 / 1024).toFixed(1)}MB > 20MB）` })
      continue
    }
    accepted.push(file)
  }
  return { accepted, rejected }
}

/** 从 cookie 中读取 csrf_token（与后端双提交校验配合；不存在则返回 null）。 */
function getCsrfTokenFromCookie(): string | null {
  if (!import.meta.client) return null
  try {
    const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/)
    return match?.[1] ? decodeURIComponent(match[1]) : null
  } catch {
    return null
  }
}

function parseXhrBody(raw: string): unknown {
  try {
    return JSON.parse(raw)
  } catch {
    return raw || null
  }
}

function safeParseXhrError(xhr: XMLHttpRequest): string {
  const body = parseXhrBody(xhr.responseText)
  return extractApiErrorMessage(body, `上传失败（HTTP ${xhr.status}）`)
}

/**
 * 媒体库带进度的上传 composable。
 *
 * apiFetch（ofetch）在浏览器端拿不到上传进度，因此这里改用 XMLHttpRequest：
 * - 手动携带 Authorization / X-CSRF-Token（双提交）
 * - xhr.upload.onprogress 驱动队列项的 progress
 * - 401 时通过 auth store 刷新 token 并重试一次
 */
export function useUploadProgress() {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()

  const queue = ref<UploadQueueItem[]>([])
  const uploading = computed(() => queue.value.some(x => x.status === 'uploading'))

  /** 进行中的 XHR：按队列项 id 索引，用于「移除」时真正中断上传 */
  const inflight = new Map<string, XMLHttpRequest>()
  const abortedIds = new Set<string>()

  let seq = 0
  function nextId(): string {
    seq += 1
    return `up_${Date.now()}_${seq}`
  }

  function endpoint(): string {
    const base = import.meta.server
      ? String(config.apiBase ?? '')
      : String(config.public.apiBase ?? '')
    return `${base.replace(/\/+$/, '')}/media/library`
  }

  function xhrUpload(
    key: string,
    file: File,
    token: string | null,
    onProgress: (percent: number) => void,
    category?: string
  ): Promise<unknown> {
    return new Promise((resolve, reject) => {
      const formData = new FormData()
      formData.append('file', file)
      if (category) formData.append('category', category)

      const xhr = new XMLHttpRequest()
      inflight.set(key, xhr)
      xhr.open('POST', endpoint(), true)
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
      const csrf = getCsrfTokenFromCookie()
      if (csrf) xhr.setRequestHeader('X-CSRF-Token', csrf)

      const settle = () => {
        inflight.delete(key)
      }

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(Math.min(99, Math.round((e.loaded / e.total) * 100)))
      }
      xhr.onload = () => {
        settle()
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(parseXhrBody(xhr.responseText))
        } else {
          reject(Object.assign(new Error(safeParseXhrError(xhr)), {
            status: xhr.status,
            data: parseXhrBody(xhr.responseText)
          }))
        }
      }
      xhr.onerror = () => {
        settle()
        reject(Object.assign(new Error('网络错误，上传失败'), { status: 0 }))
      }
      xhr.onabort = () => {
        settle()
        reject(Object.assign(new Error('上传已取消'), { status: 0, aborted: true }))
      }
      xhr.send(formData)
    })
  }

  async function uploadOne(item: UploadQueueItem, file: File, category?: string): Promise<UploadOutcome> {
    const run = (): Promise<unknown> =>
      xhrUpload(item.id, file, authStore.accessToken, (p) => { item.progress = p }, category)

    try {
      await run()
      item.progress = 100
      item.status = 'success'
      return 'success'
    } catch (err) {
      if ((err as { aborted?: boolean }).aborted || abortedIds.has(item.id)) {
        return 'aborted'
      }
      const status = (err as { status?: number }).status
      if (status === 401) {
        // token 过期：刷新一次并重试
        const refreshed = await authStore.refreshAccessToken()
        if (refreshed) {
          try {
            await run()
            item.progress = 100
            item.status = 'success'
            return 'success'
          } catch (retryErr) {
            if ((retryErr as { aborted?: boolean }).aborted || abortedIds.has(item.id)) {
              return 'aborted'
            }
            item.status = 'error'
            item.error = retryErr instanceof Error ? retryErr.message : '上传失败'
            return 'failed'
          }
        }
        item.status = 'error'
        item.error = '登录状态已过期，请重新登录'
        return 'failed'
      }
      item.status = 'error'
      item.error = err instanceof Error ? err.message : '上传失败'
      return 'failed'
    }
  }

  /**
   * 并发上传（默认最多 4 路），全部结束后返回成败统计。
   * 队列项即时可见，进度由 XHR 驱动。
   */
  async function startUploads(
    files: File[],
    options?: { category?: string, concurrency?: number }
  ): Promise<{ success: number, failed: number, aborted: number }> {
    const category = options?.category
    const maxConcurrency = Math.max(1, options?.concurrency ?? 4)
    const items = files.map(file => ({
      file,
      item: reactive({
        id: nextId(),
        filename: file.name,
        size_bytes: file.size,
        progress: 0,
        status: 'uploading'
      }) as UploadQueueItem
    }))
    queue.value.push(...items.map(x => x.item))

    let cursor = 0
    let success = 0
    let failed = 0
    let aborted = 0
    const worker = async (): Promise<void> => {
      while (cursor < items.length) {
        const entry = items[cursor++]
        if (!entry) continue
        // uploadOne 内部已兜住上传错误；这里再兜一层（如 refreshAccessToken 抛错），
        // 否则单个 worker 崩溃会让 Promise.all 直接 reject，整批统计全部丢失。
        let outcome: UploadOutcome = 'failed'
        try {
          outcome = await uploadOne(entry.item, entry.file, category)
        } catch (err) {
          entry.item.status = 'error'
          entry.item.error = err instanceof Error ? err.message : '上传失败'
        }
        if (outcome === 'success') success++
        else if (outcome === 'aborted') aborted++
        else failed++
      }
    }
    await Promise.allSettled(
      Array.from({ length: Math.min(maxConcurrency, items.length) }, () => worker())
    )
    // 整批 worker 已收敛：清掉本批的中断标记，避免集合无界增长
    for (const entry of items) abortedIds.delete(entry.item.id)
    return { success, failed, aborted }
  }

  /**
   * 从队列移除一项；若该文件仍在上传，同时中断它的 XHR
   * （否则请求会继续在后台跑完，用户在界面上却已经看不到它）。
   */
  function removeItem(id: string): void {
    const item = queue.value.find(x => x.id === id)
    if (item?.status === 'uploading') {
      abortedIds.add(id)
      inflight.get(id)?.abort()
    }
    queue.value = queue.value.filter(x => x.id !== id)
  }

  function clearFinished(): void {
    queue.value = queue.value.filter(x => x.status === 'uploading')
  }

  /** 中断所有进行中的上传并清空队列（页面卸载/用户放弃整批）。 */
  function clearQueue(): void {
    for (const item of queue.value) {
      if (item.status === 'uploading') {
        abortedIds.add(item.id)
        inflight.get(item.id)?.abort()
      }
    }
    inflight.clear()
    queue.value = []
  }

  return { queue, uploading, startUploads, removeItem, clearFinished, clearQueue }
}
