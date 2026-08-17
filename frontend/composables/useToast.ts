/**
 * 统一 Toast 封装
 * ------------------
 * 全站所有 toast 通知请通过本 composable 调用，不要直接 import vue-sonner 的 toast。
 * 好处：
 *  1. 类型安全 & 默认参数统一（位置、时长、主题色类）
 *  2. 以后要换组件库只要改这里一处
 *  3. 与 i18n 结合时统一 fallback
 */
import { toast as sonnerToast, type ExternalToast } from 'vue-sonner'
import { useI18n } from 'vue-i18n'

export type ToastType = 'info' | 'success' | 'warning' | 'error'

export interface ToastOptions {
  title?: string
  description?: string
  duration?: number
}

export interface PromiseToastOptions<T = unknown> {
  loading: string
  success: string | ((data: T) => string)
  error?: string | ((err: unknown) => string)
  finally?: () => void
}

export const useToast = () => {
  const { tm } = useI18n()

  const baseOptions = {
    duration: 3600,
    closeButton: true,
    richColors: false,
    position: 'bottom-right' as const,
    class: 'group'
  } satisfies Partial<ExternalToast>

  const getToastClass = (type: ToastType): string => {
    const classes: string[] = [baseOptions.class]
    switch (type) {
      case 'success':
        classes.push('data-[type="success"]:bg-success-muted')
        break
      case 'warning':
        classes.push('data-[type="warning"]:bg-warning-muted')
        break
      case 'error':
        classes.push('data-[type="error"]:bg-error-muted')
        break
      case 'info':
        classes.push('data-[type="info"]:bg-info-muted')
        break
    }
    return classes.join(' ')
  }

  /**
   * 通用入口，接受 type 枚举，语义色自动命中 main.css 的 sonner 覆盖
   */
  const fire = (
    type: ToastType,
    message: string,
    options: ToastOptions = {}
  ) => {
    const { title, description, duration } = options
    const msg = description ?? undefined
    const toastOptions: ExternalToast = {
      ...baseOptions,
      duration: duration ?? baseOptions.duration,
      description: msg,
      class: getToastClass(type)
    }

    switch (type) {
      case 'success':
        return sonnerToast.success(title ?? message, toastOptions)
      case 'warning':
        return sonnerToast.warning(title ?? message, toastOptions)
      case 'error':
        return sonnerToast.error(title ?? message, toastOptions)
      case 'info':
      default:
        return sonnerToast.message(title ?? message, toastOptions)
    }
  }

  const info = (msg: string, opts: ToastOptions = {}) => fire('info', msg, opts)
  const success = (msg: string, opts: ToastOptions = {}) => fire('success', msg, opts)
  const warning = (msg: string, opts: ToastOptions = {}) => fire('warning', msg, opts)
  const error = (msg: string, opts: ToastOptions = {}) => fire('error', msg, opts)

  /**
   * 包装一个异步 Promise，统一三段状态提示
   */
  const promise = async <T>(
    p: Promise<T> | (() => Promise<T>),
    opts: PromiseToastOptions<T>
  ): Promise<T> => {
    const task = typeof p === 'function' ? p() : p
    sonnerToast.promise(task, {
      loading: opts.loading,
      success: (data: T) => typeof opts.success === 'function' ? opts.success(data) : opts.success,
      error: (err: unknown) => {
        if (typeof opts.error === 'function') return opts.error(err)
        if (typeof opts.error === 'string') return opts.error
        const errMessage = err instanceof Error ? err.message : String(err)
        return errMessage || tm('common.error') || '操作失败'
      },
      ...baseOptions
    })
    try {
      return await task
    } finally {
      opts.finally?.()
    }
  }

  const dismiss = (id?: number | string) => sonnerToast.dismiss(id)

  return { info, success, warning, error, promise, fire, dismiss }
}
