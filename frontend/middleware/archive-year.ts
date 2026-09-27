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
export default defineNuxtRouteMiddleware((to) => {
  if (/^\/archive\/[^/]+$/.test(to.path) && !/^\/archive\/\d{4}$/.test(to.path)) {
    return abortNavigation(
      createError({ statusCode: 404, statusMessage: 'Invalid archive year' })
    )
  }
})
