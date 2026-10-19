/**
 * useUploadProgress —— 媒体库「带进度」上传队列（POST 到 <baseURL>/media/library）。
 * 刻意不用 apiFetch：ofetch 在浏览器端取不到 upload 进度，这里用 XMLHttpRequest 自己拼
 * Authorization + X-CSRF-Token（cookie `csrf_token`，后端双提交），401 刷新后只重试一次。
 * 上限与扩展名白名单只是客户端预筛（不承担安全职责）；上限跟站点设置
 * media.max_upload_size 走同一份值（见 resolveUploadLimitBytes），MAX_UPLOAD_BYTES 仅是缺省兜底；
 * 白名单跟 media.allowed_image_types / allowed_file_types 走同一份交集（见 resolveAllowedExtensions）。
 * 队列项 id 是本地生成的（不是 Media.id），removeItem 必须顺手 abort 在飞的 XHR，
 * 且「用户主动中断」单列 aborted 计数，不能和 failed 混在一起。
 */

import { extractApiErrorMessage } from '~~/lib/utils'
import { formatBytes } from '~~/composables/useImageCompress'
import { useAuthStore } from '~~/stores/auth'

/** 后台没配（或配了个非正数）时的兜底单文件上限：20MB。 */
export const MAX_UPLOAD_BYTES = 20 * 1024 * 1024

/**
 * 站点设置 `media.max_upload_size`（经公开口 `/api/config` 的 `max_upload_size` 下发）
 * → 字节数。非数字 / 0 / 负数一律回落兜底常量。
 * 服务端仍按自己的区间（[64KB, 100MB] 钳位）二次判定，这里只负责别把设置写死。
 */
export function resolveUploadLimitBytes(raw: unknown): number {
  const n = Number(raw)
  return Number.isFinite(n) && n > 0 ? n : MAX_UPLOAD_BYTES
}

/** 允许上传的扩展名白名单（= 服务端内置安全清单 LIBRARY_ALLOWED_EXTENSIONS）。 */
export const ALLOWED_UPLOAD_EXTENSIONS: readonly string[] = [
  'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg',
  'mp4', 'webm', 'mov',
  'mp3', 'wav', 'ogg',
  'pdf', 'doc', 'docx', 'xls', 'xlsx'
]

/**
 * 站点设置 `media.allowed_image_types` + `allowed_file_types`（逗号分隔，经 `/api/config`
 * 同名扁平行下发）→ 本页面真正能传成功的扩展名集合。
 *
 * 口径与服务端 `api/media.py::_effective_library_exts` 逐字对齐：**只能收紧、不能放松**
 * （与内置清单求交集，交集外的一律滤掉），两项都留空＝不收紧。
 * 管理员把 svg 从清单里去掉后，选择器与拒绝文案还在放行 .svg 的表现就是"这个设置没生效"，
 * 而真实结果是一次注定 400 UPLOAD_EXT_REJECTED 的往返。
 * 内置清单是安全边界（每一项都有对应魔术字节表），所以这里绝不因为配置里写了 zip/pptx 就放开。
 */
export function resolveAllowedExtensions(
  imageTypes: unknown,
  fileTypes: unknown
): readonly string[] {
  const listed = new Set<string>()
  for (const raw of [imageTypes, fileTypes]) {
    if (typeof raw !== 'string') continue
    for (const part of raw.split(',')) {
      const ext = part.trim().replace(/^\.+/, '').toLowerCase()
      if (ext) listed.add(ext)
    }
  }
  if (listed.size === 0) return ALLOWED_UPLOAD_EXTENSIONS
  return ALLOWED_UPLOAD_EXTENSIONS.filter(ext => listed.has(ext))
}

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

export function extensionOf(filename: string): string {
  const idx = filename.lastIndexOf('.')
  return idx >= 0 ? filename.slice(idx + 1).toLowerCase() : ''
}

/**
 * 客户端预校验：大小 + 扩展名白名单。
 * 在真正发起上传前过滤，被拒绝的文件带原因返回，由调用方统一 toast。
 *
 * `limits.maxBytes` 由调用方从站点设置（`/api/config` 的 `max_upload_size`，
 * 即后台「媒体与上传 · 单文件大小上限」）传入，缺省走 `resolveUploadLimitBytes` 的兜底。
 * 写死常量时管理员把上限改成 5MB 或 50MB，选择器与拒绝文案仍报 20MB，
 * 表现是"这个设置没生效"。预筛只影响体验，服务端仍自己再判一次。
 * `limits.allowedExtensions` 同理，走 `resolveAllowedExtensions`（后台「允许的文件类型」两项）。
 */
export function validateUploadFiles(
  files: File[],
  limits: { maxBytes?: number, allowedExtensions?: readonly string[] } = {}
): FileValidationResult {
  const maxBytes = resolveUploadLimitBytes(limits.maxBytes)
  const allowed = limits.allowedExtensions ?? ALLOWED_UPLOAD_EXTENSIONS
  const accepted: File[] = []
  const rejected: FileRejection[] = []
  for (const file of files) {
    const ext = extensionOf(file.name)
    if (!allowed.includes(ext)) {
      rejected.push({ name: file.name, reason: `不支持的文件类型 .${ext || '?'}` })
      continue
    }
    if (file.size > maxBytes) {
      rejected.push({ name: file.name, reason: `文件过大（${formatBytes(file.size)} > ${formatBytes(maxBytes)}）` })
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
