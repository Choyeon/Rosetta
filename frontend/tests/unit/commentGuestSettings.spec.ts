/**
 * 「评论」分组设置的执行点契约。
 *
 * 背景：后台设置页一直在写 site_configs 的 comments 分组（allow_guest / max_length /
 * enable_nested / require_approval），后端评论服务也确实读它们，但前台文章页的表单
 * 只在 `authStore.isAuthenticated` 时渲染、提交走 `POST /api/blog/posts/{id}/comments`
 * （那条口挂了 CurrentUser，匿名直接 401）。于是四个开关在界面上一个都不成立：
 * 访客永远看不到输入框，字数上限、嵌套回复、审核提示全按硬编码走。
 *
 * 本文件用源码扫描钉住「开关 → 真实消费点」，改回旧写法即红。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), 'utf8')

const siteSource = read('composables/useSite.ts')
const pageSource = read('pages/posts/[slug].vue')
const commentsSource = read('composables/useComments.ts')
const itemSource = read('components/CommentItem.vue')

describe('comments 分组：值必须下发并落到界面上', () => {
  it('useSite 暴露 comments 计算属性并导出', () => {
    expect(siteSource).toMatch(/const comments = computed\(\(\) => \{[\s\S]*?readGroup\(state\.value, 'comments'/)
    for (const key of ['allow_guest', 'enable_nested', 'require_approval', 'max_length']) {
      expect(siteSource, `useSite 必须解析 ${key}`).toContain(`${key}:`)
    }
    expect(siteSource).toMatch(/\n {4}features,\n {4}comments,/)
  })

  it('文章页用 allow_guest 决定访客能否看到表单', () => {
    expect(pageSource).toContain('site.comments.value.allow_guest')
    expect(pageSource).not.toMatch(/<Card\s*\n\s*v-if="authStore\.isAuthenticated"/)
    // 访客必须填得出让后端认下来的身份字段（422 AUTHOR_NAME_REQUIRED）
    for (const field of ['author_name', 'author_email', 'author_website']) {
      expect(pageSource, `访客表单缺 ${field}`).toContain(`guestForm.${field}`)
    }
  })

  it('max_length / enable_nested / require_approval 各有消费点', () => {
    expect(pageSource).toContain('site.comments.value.max_length')
    expect(pageSource).toContain('site.comments.value.enable_nested')
    expect(pageSource).toContain('site.comments.value.require_approval')
    expect(itemSource).toContain('v-if="canReply"')
  })

  it('匿名验证码开关打开时表单挂上 CaptchaField', () => {
    expect(pageSource).toContain('import CaptchaField from')
    expect(pageSource).toContain('<CaptchaField')
    expect(pageSource).toContain('site.features.value.enable_captcha')
  })

  it('提交走游客可写的 /posts/{id}/comments，不带 /blog 前缀', () => {
    expect(commentsSource).toContain('`/posts/${post_id}/comments`')
    expect(commentsSource).not.toMatch(/method: 'POST'[\s\S]{0,80}`\/blog\/posts\//)
    for (const field of ['author_name', 'author_email', 'captcha_key', 'captcha_code']) {
      expect(commentsSource, `createComment 载荷缺 ${field}`).toContain(field)
    }
  })
})

describe('评论写入只有一个口', () => {
  const adminManageSource = read('composables/useAdminManage.ts')

  it('后台审核回复也走 canonical /posts/{id}/comments', () => {
    // blog.py 那份重复实现没有 comments 分组闸门（长度 / 嵌套开关 / CSRF / 频控），
    // 后台回复仍能写出被关掉的嵌套层。它已删除，消费点必须跟着换。
    expect(adminManageSource).toContain('`/posts/${postId}/comments`')
    expect(adminManageSource).not.toContain('/blog/posts/${postId}/comments')
  })
})

describe('新增文案的 i18n 键四语齐全', () => {
  const locales = ['zh', 'en', 'ja', 'zh_Hant']
  const keys = [
    'yourName',
    'yourEmail',
    'yourWebsite',
    'pendingNotice',
    'commentTooLong',
    'nicknameRequired',
    'commentSubmitted',
    'commentPending',
    'commentFailed'
  ]

  for (const loc of locales) {
    it(loc, () => {
      const bundle = JSON.parse(read(`i18n/locales/${loc}.json`)) as Record<string, Record<string, string>>
      for (const key of keys) {
        expect(bundle.post, `${loc} 缺 post.${key}`).toBeDefined()
        expect(bundle.post?.[key], `${loc} 缺 post.${key}`).toBeTruthy()
      }
    })
  }
})
