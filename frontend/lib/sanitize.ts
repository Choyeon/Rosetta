/**
 * 共享 HTML sanitize 入口（XSS 封堵统一配置源）。
 *
 * 库选择：isomorphic-dompurify —— SSR 与客户端跑同一份 sanitize 实现，
 * 相同输入两端输出字节级一致，不会引入 Hydration mismatch
 * （与 pages/[slug].vue、pages/page/[slug].vue、pages/posts/[slug].vue 既有链路同源）。
 *
 * 配置对齐说明：
 * - MARKDOWN_SANITIZE_CONFIG 与前台独立页/pages 链路内联的 SANITIZE_CONFIG 保持同一组
 *   键值（Markdown 渲染产物，禁 style）；
 * - TRUSTED_ADMIN_HTML_CONFIG 语义不同：管理员在「关于页 HTML / 页脚自定义 HTML」
 *   有意书写富排版内容，因此额外放行 style 属性（仅内联样式，<style> 块仍禁），
 *   其余（script、iframe、表单、on-事件、javascript: URI）与 Markdown 配置同等封死。
 */
import DOMPurify from 'isomorphic-dompurify'

type DOMPurifyConfig = NonNullable<Parameters<typeof DOMPurify.sanitize>[1]>

/** 事件属性双保险：DOMPurify 默认属性白名单已不含 on*，显式 FORBID 防未来白名单扩张 */
const EVENT_AND_FRAME_ATTRS = ['onerror', 'onload', 'onclick', 'onmouseover', 'srcdoc', 'formaction']

/** 脚本载体与表单/外部资源标签：两套配置共用同一封禁清单，禁止悄悄放宽 */
const FORBIDDEN_TAGS = ['script', 'iframe', 'object', 'embed', 'style', 'form', 'input', 'button', 'link', 'meta', 'base', 'svg', 'math']

/**
 * Markdown → HTML 渲染产物（编辑器预览、后台文档页）。
 * 与前台 [slug].vue / page/[slug].vue 的 SANITIZE_CONFIG 对齐；
 * style 属性一律禁：Markdown 语法不产合法内联样式，放行只会被用于 UI 伪装。
 * svg/math 封死：二者是 DOMPurify mutation-XSS 的历史高发载体，文档/预览不需要。
 */
export const MARKDOWN_SANITIZE_CONFIG: DOMPurifyConfig = {
  ADD_TAGS: ['pre', 'code', 'span', 'kbd', 'mark', 'samp', 'var', 'img'],
  ADD_ATTR: ['class', 'src', 'alt', 'loading'],
  ALLOW_UNKNOWN_PROTOCOLS: false,
  WHOLE_DOCUMENT: false,
  FORBID_TAGS: FORBIDDEN_TAGS,
  FORBID_ATTR: [...EVENT_AND_FRAME_ATTRS, 'style'],
  SANITIZE_DOM: true
}

/**
 * 管理员受信任原始 HTML（关于页 about_page_html / 页脚 footer_custom_html）。
 * 与 MARKDOWN_SANITIZE_CONFIG 的唯一语义差异：允许 class + style 属性，
 * 因为站点所有者需要内联排版（对齐、间距、配色）；DOMPurify 会按 CSS 属性
 * 白名单解析 style 值，expression() 等可执行向量在现代浏览器已死且被其过滤。
 * <style> 块仍然封禁：整页样式覆写会泄漏到站点其他区域（作用域污染）。
 */
export const TRUSTED_ADMIN_HTML_CONFIG: DOMPurifyConfig = {
  ADD_ATTR: ['class', 'style', 'target'],
  // URI scheme 沿用 DOMPurify 默认白名单（http/https/mailto/tel/... + 站内相对路径），
  // javascript:/vbscript:/未知协议一律拒绝；ALLOW_UNKNOWN_PROTOCOLS:false 兜底。
  ALLOW_UNKNOWN_PROTOCOLS: false,
  WHOLE_DOCUMENT: false,
  FORBID_TAGS: FORBIDDEN_TAGS,
  FORBID_ATTR: [...EVENT_AND_FRAME_ATTRS],
  SANITIZE_DOM: true
}

// 管理员手写的 <a target="_blank"> 补 rel，防反向标签劫持；输出确定性一致，两端无差。
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  const el = node as HTMLElement
  if (el.tagName === 'A' && el.getAttribute('target') === '_blank') {
    const rel = new Set((el.getAttribute('rel') || '').split(/\s+/).filter(Boolean))
    rel.add('noopener')
    rel.add('noreferrer')
    const joined = [...rel].join(' ')
    el.setAttribute('rel', joined)
  }
})

/** Markdown / 文档渲染产物净化（marked 输出 → v-html 之前的最后一道闸）。 */
export function sanitizeMarkdownHtml(dirtyHtml: string): string {
  if (!dirtyHtml) return ''
  return DOMPurify.sanitize(dirtyHtml, MARKDOWN_SANITIZE_CONFIG) as string
}

/** 管理员原始 HTML（关于页/页脚自定义）净化；非法输入按空串处理，交给页面回退分支。 */
export function sanitizeTrustedAdminHtml(dirtyHtml: unknown): string {
  const raw = typeof dirtyHtml === 'string' ? dirtyHtml.trim() : ''
  if (!raw) return ''
  return DOMPurify.sanitize(raw, TRUSTED_ADMIN_HTML_CONFIG) as string
}
