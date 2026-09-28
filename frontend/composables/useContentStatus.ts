/**
 * 内容不存在时让 SSR 响应带上真实状态码（WordPress 口径：不存在的内容是 404，不是 200）。
 *
 * 背景：这几个动态内容页（文章详情 / 分类 / 标签 / 独立页）在数据缺失时只渲染
 * "内容不存在"的兜底 UI，HTTP 响应仍是 200，并且会按 routeRules 的 swr 被缓存——
 * 爬虫会把 404 的 URL 当有效页收录。闸门不能写成页面里的 `throw createError(404)`：
 * 那条路径渲染 error.vue 但响应仍是 200（见 AGENTS §2.3.2）；这里已经确定要展示
 * 本页的兜底 UI，所以只改状态码、不改渲染。
 *
 * 只在两种情况下判定为 404：后端明确回了 404，或请求成功但对象为空。
 * 其余（无状态码的网络故障、5xx）一律不动状态码——那时内容是否存在未知，
 * 写成 404 会让搜索引擎把一次临时故障当成永久删除而掉索引，比 200 更难恢复。
 */
import type { ComputedRef, Ref } from 'vue'

interface StatusCarrier {
  status?: number
  statusCode?: number
  data?: { status?: number }
}

/**
 * 「这个 URL 的内容不存在」的唯一判定口径，供两处共用：
 * 服务端状态码闸门（下面）与页面自己的兜底 UI 分支。
 * 写成导出的纯函数是为了不让页面复制一份判断逻辑——两处分叉的表现是
 * "HTTP 回了 404 而用户看到的是『加载失败，请重试』"。
 */
export function isContentMissing(error: unknown, missing: boolean): boolean {
  const err = error as StatusCarrier | null | undefined
  const status = err?.status ?? err?.statusCode ?? err?.data?.status ?? 0

  // 404 是后端的明确答复；请求成功但对象为空（null/{}）同样是"不存在"。
  // 其余（无状态码的故障、5xx）不算缺失——那时内容是否存在未知，
  // 写成 404 会让搜索引擎把一次临时故障当成永久删除而掉索引，比 200 更难恢复。
  return status === 404 || (err == null && missing)
}

export function useContentStatus(
  error: Ref<unknown> | ComputedRef<unknown>,
  missing: Ref<boolean> | ComputedRef<boolean>
): void {
  if (!import.meta.server) return
  // event 必须在 setup 同步期取：Nuxt 4 未开 nitroAsyncContext，异步回调里
  // useRequestEvent() 拿不到上下文（实测第一版就是这样把判定写进 hook 里，
  // 结果页面全部回到 200、闸门静默失效）。
  const event = useRequestEvent()
  if (!event) return

  const decide = () => {
    if (isContentMissing(error.value, missing.value)) {
      setResponseStatus(event, 404)
    }
  }

  // 判定时点必须是 app:rendered：useFetch / useAsyncData 的 payload 由 Nuxt 在渲染前
  // 才 await 落值，setup 同步期 data 仍是 null——在那里读 missing 会把每个真实页面
  // 一起误判成 404（实测 /posts/{真实 slug} 也变 404）。app:rendered 在 renderToString
  // 之后、Nitro 发出响应之前触发，状态码还改得动。
  const hooks = useNuxtApp().hooks as unknown as { hookOnce?: (name: string, cb: () => void) => void }
  if (typeof hooks.hookOnce === 'function') {
    hooks.hookOnce('app:rendered', decide)
  } else {
    decide()
  }
}
