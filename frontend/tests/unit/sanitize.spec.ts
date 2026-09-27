import { describe, it, expect } from 'vitest'
import {
  MARKDOWN_SANITIZE_CONFIG,
  TRUSTED_ADMIN_HTML_CONFIG,
  sanitizeMarkdownHtml,
  sanitizeTrustedAdminHtml
} from '@/lib/sanitize'

describe('lib/sanitize XSS 封堵契约', () => {
  describe('sanitizeMarkdownHtml（Markdown 渲染产物）', () => {
    it('移除 <script> 标签', () => {
      const out = sanitizeMarkdownHtml('<p>hi</p><script>alert(1)</script>')
      expect(out).not.toContain('<script')
      expect(out).toContain('<p>hi</p>')
    })

    it('移除事件属性 onerror / onload / onclick', () => {
      const out = sanitizeMarkdownHtml('<img src="x.png" onerror="alert(1)"><p onload="steal()" onclick="go()">t</p>')
      expect(out).not.toContain('onerror')
      expect(out).not.toContain('onload')
      expect(out).not.toContain('onclick')
      expect(out).toContain('<img')
    })

    it('移除 javascript: 协议链接', () => {
      const out = sanitizeMarkdownHtml('<a href="javascript:alert(1)">点我</a>')
      expect(out).not.toMatch(/href/i)
      expect(out).toContain('点我')
    })

    it('封禁 <style> 块与内联 style 属性', () => {
      const out = sanitizeMarkdownHtml('<style>body{display:none}</style><p style="color:red">x</p>')
      expect(out).not.toContain('<style')
      expect(out).not.toContain('color:red')
    })

    it('封禁 iframe / object / form / svg / math 等脚本载体', () => {
      const dirty = '<iframe src="https://evil"></iframe><object></object><form><button>s</button></form><svg><animate onbegin="alert(1)"></animate></svg><math></math>'
      const out = sanitizeMarkdownHtml(dirty)
      for (const tag of ['iframe', 'object', 'form', 'button', 'svg', 'math']) {
        expect(out, `tag ${tag} 应被移除`).not.toContain(`<${tag}`)
      }
    })

    it('放行的 Markdown 产物元素原样保留', () => {
      const out = sanitizeMarkdownHtml('<pre><code class="lang-ts">const a = 1</code></pre><kbd>Ctrl</kbd><img src="/a.webp" alt="a" loading="lazy">')
      expect(out).toContain('<pre><code class="lang-ts">const a = 1</code></pre>')
      expect(out).toContain('<kbd>Ctrl</kbd>')
      expect(out).toContain('<img src="/a.webp" alt="a" loading="lazy">')
    })

    it('空输入返回空串', () => {
      expect(sanitizeMarkdownHtml('')).toBe('')
      expect(sanitizeMarkdownHtml(undefined as unknown as string)).toBe('')
      expect(sanitizeMarkdownHtml(null as unknown as string)).toBe('')
    })
  })

  describe('sanitizeTrustedAdminHtml（关于页 / 页脚自定义 HTML）', () => {
    it('放行内联 style 属性但 <style> 块仍封禁', () => {
      const out = sanitizeTrustedAdminHtml('<p style="color:red;margin-top:4px">排版</p><style>body{background:pink}</style>')
      expect(out).toContain('style="color:red;margin-top:4px"')
      expect(out).not.toContain('<style')
    })

    it('script / onerror / javascript: 与 Markdown 配置同等封死', () => {
      const out = sanitizeTrustedAdminHtml('<script>alert(1)</script><img src="x" onerror="alert(2)"><a href="javascript:void(0)">j</a>')
      expect(out).not.toContain('<script')
      expect(out).not.toContain('onerror')
      expect(out).not.toMatch(/href="javascript/i)
    })

    it('给 target="_blank" 的链接补齐 rel="noopener noreferrer"', () => {
      const out = sanitizeTrustedAdminHtml('<a href="https://example.com" target="_blank">外链</a>')
      expect(out).toContain('target="_blank"')
      expect(out).toMatch(/rel="[^"]*noopener[^"]*"/)
      expect(out).toMatch(/rel="[^"]*noreferrer[^"]*"/)
    })

    it('已有 rel 时合并而不覆盖', () => {
      const out = sanitizeTrustedAdminHtml('<a href="https://example.com" target="_blank" rel="nofollow">x</a>')
      expect(out).toMatch(/rel="[^"]*nofollow[^"]*noopener[^"]*noreferrer[^"]*"/)
    })

    it('非 target="_blank" 的链接不被注入 rel', () => {
      const out = sanitizeTrustedAdminHtml('<a href="https://example.com">普通链接</a>')
      expect(out).not.toContain('noopener')
    })

    it('空 / 非字符串输入一律按空串处理', () => {
      expect(sanitizeTrustedAdminHtml('')).toBe('')
      expect(sanitizeTrustedAdminHtml('   ')).toBe('')
      expect(sanitizeTrustedAdminHtml(null)).toBe('')
      expect(sanitizeTrustedAdminHtml(undefined)).toBe('')
      expect(sanitizeTrustedAdminHtml(123)).toBe('')
      expect(sanitizeTrustedAdminHtml({})).toBe('')
      expect(sanitizeTrustedAdminHtml([])).toBe('')
    })

    it('class 属性放行（受信任排版的必要能力）', () => {
      expect(sanitizeTrustedAdminHtml('<p class="lead">x</p>')).toContain('class="lead"')
    })
  })

  describe('配置常量的封禁清单对齐', () => {
    it('两套配置共享同一脚本载体封禁清单', () => {
      expect(MARKDOWN_SANITIZE_CONFIG.FORBID_TAGS).toEqual(TRUSTED_ADMIN_HTML_CONFIG.FORBID_TAGS)
      expect(MARKDOWN_SANITIZE_CONFIG.FORBID_TAGS).toContain('script')
      expect(MARKDOWN_SANITIZE_CONFIG.FORBID_TAGS).toContain('style')
    })

    it('两套配置都封死事件属性并禁用未知协议', () => {
      for (const cfg of [MARKDOWN_SANITIZE_CONFIG, TRUSTED_ADMIN_HTML_CONFIG]) {
        expect(cfg.FORBID_ATTR).toContain('onerror')
        expect(cfg.FORBID_ATTR).toContain('srcdoc')
        expect(cfg.ALLOW_UNKNOWN_PROTOCOLS).toBe(false)
        expect(cfg.SANITIZE_DOM).toBe(true)
      }
    })

    it('唯一语义差异：Markdown 额外封禁 style 属性', () => {
      expect(MARKDOWN_SANITIZE_CONFIG.FORBID_ATTR).toContain('style')
      expect(TRUSTED_ADMIN_HTML_CONFIG.FORBID_ATTR).not.toContain('style')
    })
  })
})
