/**
 * 归档年份路由闸门（仅挂在与文件名，不进全局链）。
 *
 * 为什么不放页面 setup 里：`<script setup>` 中 `throw createError({ statusCode: 404 })`
 * 会被 error.vue 接管但**响应仍是 HTTP 200**（实测 /archive/abcd 返回
 * `HTTP/1.1 200` + `cache-control: s-maxage=3600`，被 /archive/** 的 swr 规则缓存成一个
 * 可复用的 200 页），对爬虫与 SEO 等于"这页存在"。走路由中间件 abort 才与 Nuxt 自身的
 * 未命中路径同轨（对比：/archive/2026/03 无匹配路由 → 真 404）。
 *
 * 顺带挡住的是把垃圾参数发给后端：/blog/archive/abcd 会被 FastAPI 判 422。
 */
import { stripLocalePathPrefix } from '~~/lib/rosetta-themes'

const YEAR_ONLY = /^\/archive\/[^/]+$/
const YEAR_MONTH = /^\/archive\/(\d{1,4})\/(\d{1,2})$/

// i18n prefix_except_default：/en/archive/2026 /ja/archive/... /zh_Hant/archive/...
// 与裸 /archive/... 是同一页，闸门判定必须先剥前缀，否则非法年份在带前缀语言下
// 会静默放行到 useAsyncData（后端 422 + 页面 200 被 swr 缓存成"正常页"）。
// 前缀唯一清单见 lib/rosetta-themes 的 I18N_URL_PREFIXES。

export default defineNuxtRouteMiddleware((to) => {
  const p = stripLocalePathPrefix(to.path)

  // 单年 /archive/<year>：只接受 4 位数字
  if (YEAR_ONLY.test(p) && !/^\/archive\/\d{4}$/.test(p)) {
    return abortNavigation(
      createError({ statusCode: 404, statusMessage: 'Invalid archive year' })
    )
  }
  // 单月 /archive/<year>/<month>：年份 4 位 + 月份 1-12（0 与 13 以上都不存在，
  // 放进后端只会拿到空分组，SEO 口径上应当与 WordPress 一样直接 404）
  if (YEAR_MONTH.test(p) && !/^\/archive\/\d{4}\/(?:0?[1-9]|1[0-2])$/.test(p)) {
    return abortNavigation(
      createError({ statusCode: 404, statusMessage: 'Invalid archive date' })
    )
  }
  // 三位以上月份（/archive/2026/007）不在 YEAR_MONTH 的 \d{1,2} 覆盖内，单独拦下，
  // 不得放宽成 \d+ ——那会把 08 这类合法月份一起吃掉。
  if (/^\/archive\/\d{4}\/\d{3,}$/.test(p)) {
    return abortNavigation(
      createError({ statusCode: 404, statusMessage: 'Invalid archive date' })
    )
  }
})
