/**
 * 客户端图片压缩工具
 *
 * 在上传前对图片进行压缩，减少传输体积和后端存储压力。
 * 采用 Canvas API 实现：缩放 + 质量重编码，全程不引入额外依赖。
 */

export interface CompressOptions {
  /** 最大边长（px），超过则等比缩放，默认 3840 */
  maxDimension?: number
  /** JPEG/WebP 输出质量 0-1，默认 0.85 */
  quality?: number
  /** 输出格式，默认 'image/jpeg'（透明 PNG 保留 png） */
  mimeType?: string
  /** 超过该大小（字节）才触发压缩，默认 500KB */
  minSizeToCompress?: number
}

export interface CompressResult {
  /** 压缩后的文件 */
  file: File
  /** 原始尺寸 */
  originalWidth: number
  originalHeight: number
  /** 压缩后尺寸 */
  width: number
  height: number
  /** 原始大小（字节） */
  originalSize: number
  /** 压缩后大小（字节） */
  size: number
  /** 压缩率 0-1 */
  ratio: number
}

/**
 * 读取图片的实际尺寸
 */
function readImageDimensions(file: File): Promise<{ width: number, height: number }> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      resolve({ width: img.naturalWidth, height: img.naturalHeight })
      URL.revokeObjectURL(url)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('无法读取图片尺寸'))
    }
    img.src = url
  })
}

/**
 * 压缩单张图片
 *
 * - 超大图自动等比缩放到 maxDimension 以内
 * - JPEG/WebP 以指定质量重编码
 * - 透明 PNG 保留 alpha 通道，输出 image/png
 * - 压缩后体积更大则返回原图（避免负优化）
 */
export async function compressImage(
  file: File,
  options: CompressOptions = {}
): Promise<CompressResult> {
  const {
    maxDimension = 3840,
    quality = 0.85,
    mimeType: forcedMime,
    minSizeToCompress = 500 * 1024
  } = options

  const originalSize = file.size

  // 小文件或 SVG 不压缩
  const isSvg = file.type === 'image/svg+xml' || file.name.toLowerCase().endsWith('.svg')
  if (isSvg || originalSize <= minSizeToCompress) {
    const dims = await safeReadDimensions(file)
    return {
      file,
      originalWidth: dims.width,
      originalHeight: dims.height,
      width: dims.width,
      height: dims.height,
      originalSize,
      size: originalSize,
      ratio: 1
    }
  }

  const dims = await readImageDimensions(file)
  let { width, height } = dims

  // 等比缩放
  const maxSide = Math.max(width, height)
  if (maxSide > maxDimension) {
    const ratio = maxDimension / maxSide
    width = Math.round(width * ratio)
    height = Math.round(height * ratio)
  }

  // 决定输出格式：有透明通道的 PNG 保留 png
  const hasAlpha = file.type === 'image/png'
  const outputMime = forcedMime || (hasAlpha ? 'image/png' : 'image/jpeg')

  const compressedBlob = await drawToCanvas(file, width, height, outputMime, quality)

  // 压缩后更大则返回原图
  if (compressedBlob.size >= originalSize) {
    return {
      file,
      originalWidth: dims.width,
      originalHeight: dims.height,
      width: dims.width,
      height: dims.height,
      originalSize,
      size: originalSize,
      ratio: 1
    }
  }

  const compressedFile = new File(
    [compressedBlob],
    renameExtension(file.name, outputMime),
    { type: outputMime, lastModified: Date.now() }
  )

  return {
    file: compressedFile,
    originalWidth: dims.width,
    originalHeight: dims.height,
    width,
    height,
    originalSize,
    size: compressedBlob.size,
    ratio: compressedBlob.size / originalSize
  }
}

/**
 * 把 File 绘制到 Canvas 并导出为 Blob
 */
function drawToCanvas(
  file: File,
  width: number,
  height: number,
  mimeType: string,
  quality: number
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        URL.revokeObjectURL(url)
        reject(new Error('Canvas 2D context 不可用'))
        return
      }
      // 平滑缩放
      ctx.imageSmoothingEnabled = true
      ctx.imageSmoothingQuality = 'high'
      ctx.drawImage(img, 0, 0, width, height)
      URL.revokeObjectURL(url)
      canvas.toBlob(
        (blob) => {
          if (blob) resolve(blob)
          else reject(new Error('Canvas 导出失败'))
        },
        mimeType,
        quality
      )
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('图片加载失败'))
    }
    img.src = url
  })
}

function safeReadDimensions(file: File): Promise<{ width: number, height: number }> {
  return readImageDimensions(file).catch(() => ({ width: 0, height: 0 }))
}

/**
 * 根据输出 MIME 类型重命名文件扩展名
 */
function renameExtension(name: string, mimeType: string): string {
  const dot = name.lastIndexOf('.')
  const base = dot > 0 ? name.slice(0, dot) : name
  const extMap: Record<string, string> = {
    'image/jpeg': '.jpg',
    'image/webp': '.webp',
    'image/png': '.png'
  }
  return base + (extMap[mimeType] || (dot > 0 ? name.slice(dot) : ''))
}

/**
 * 格式化字节大小为人类可读字符串
 */
export function formatBytes(bytes: number, decimals = 1): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`
}
