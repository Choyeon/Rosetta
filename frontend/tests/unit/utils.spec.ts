import { describe, it, expect } from 'vitest'
import { cn, extractApiErrorMessage, isOobeRequiredError, stableApiKey } from '@/lib/utils'

describe('lib/utils', () => {
  // ---------- cn (clsx + tailwind-merge) ----------
  describe('cn', () => {
    it('合并字符串与数组 className', () => {
      expect(cn('a', 'b', ['c', 'd'])).toBe('a b c d')
    })

    it('合并对象并跳过 false 值', () => {
      expect(cn('base', { active: true, disabled: false })).toBe('base active')
    })

    it('用 tailwind-merge 解决冲突：bg-black 覆盖 bg-red-500', () => {
      expect(cn('bg-red-500', 'bg-black')).toBe('bg-black')
    })
  })

  // ---------- extractApiErrorMessage ----------
  describe('extractApiErrorMessage', () => {
    it('优先返回 body.message', () => {
      expect(
        extractApiErrorMessage({ message: '自定义消息', detail: 'detail 兜底' }, 'fallback')
      ).toBe('自定义消息')
    })

    it('无 message 时用 detail', () => {
      expect(extractApiErrorMessage({ detail: 'FastAPI 错误' }, 'fallback')).toBe('FastAPI 错误')
    })

    it('无 message/detail 时退回到 errors[0].message', () => {
      const body = { errors: [{ field: 'password', message: '密码不能为空' }] }
      expect(extractApiErrorMessage(body, 'fallback')).toBe('密码不能为空')
    })

    it('完全无有效信息：返回 fallback', () => {
      expect(extractApiErrorMessage(null, 'fallback')).toBe('fallback')
      expect(extractApiErrorMessage(undefined, 'fallback')).toBe('fallback')
      expect(extractApiErrorMessage({}, 'fallback')).toBe('fallback')
      expect(extractApiErrorMessage('字符串错误体', 'fallback')).toBe('fallback')
    })
  })

  // ---------- isOobeRequiredError ----------
  describe('isOobeRequiredError', () => {
    it('503 + OOBE_REQUIRED → true', () => {
      expect(isOobeRequiredError(503, { error_code: 'OOBE_REQUIRED' })).toBe(true)
    })

    it('401 + OOBE_REQUIRED → false（状态码不匹配）', () => {
      expect(isOobeRequiredError(401, { error_code: 'OOBE_REQUIRED' })).toBe(false)
    })

    it('503 但 error_code 为 INVALID_CREDENTIALS → false', () => {
      expect(isOobeRequiredError(503, { error_code: 'INVALID_CREDENTIALS' })).toBe(false)
    })

    it('body 为 null / 无对象 → false', () => {
      expect(isOobeRequiredError(503, null)).toBe(false)
      expect(isOobeRequiredError(503, undefined)).toBe(false)
    })
  })

  // ---------- stableApiKey ----------
  describe('stableApiKey', () => {
    it('纯字符串 URL → 无 query', () => {
      expect(stableApiKey('/posts')).toBe('api::/posts')
    })

    it('相同 query 顺序 → 相同 key（URLSearchParams 稳定）', () => {
      const a = stableApiKey('/posts', { page: 1, size: 10 })
      const b = stableApiKey('/posts', { page: '1', size: '10' })
      expect(a).toBe(b)
    })

    it('object 类型 query 值 → JSON 序列化拼接', () => {
      const k = stableApiKey('/search', { filters: { tag: 'vue', status: 'draft' }, page: 1 })
      expect(k).toContain('filters=%7B%22tag%22%3A%22vue%22%2C%22status%22%3A%22draft%22%7D')
      expect(k).toContain('page=1')
    })

    it('URL 为函数 → 截取函数体前 80 字符生成前缀（不含 baseURL）', () => {
      const fn = () => `/posts/${1}`
      const k = stableApiKey(fn)
      expect(k).toMatch(/^api::__fn__/)
      expect(k).toContain('/posts/')
    })
  })
})
