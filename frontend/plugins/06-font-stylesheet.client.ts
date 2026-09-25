/**
 * 把 nuxt.config head 里的字体 preload 链接切换为真正的样式表。
 *
 * 首屏 HTML 只带 <link rel="preload" as="style">，所以 Google Fonts 可达与否
 * 都不阻塞渲染；这里在客户端把 rel 改成 stylesheet，浏览器会直接复用
 * preload 已下载好的响应（不会产生第二次请求）。
 */
export default defineNuxtPlugin(() => {
  const links = document.querySelectorAll<HTMLLinkElement>('link[rel="preload"][as="style"]')
  links.forEach((link) => {
    link.rel = 'stylesheet'
  })
})
