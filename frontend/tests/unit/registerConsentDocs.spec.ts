/**
 * 注册页「服务条款 / 隐私政策」的落地契约。
 *
 * 表现过的问题：勾选框旁写着「我已阅读并同意 服务条款 与 隐私政策」，但那两段文字是
 * 不可点的 `<span>`——站点上根本没有 terms / privacy 路由（它们是站长在后台创建的独立页，
 * 走顶级 catchall 渲染）。等于要求用户同意两份谁都没法打开的文件。
 *
 * 两条口径：
 * ① 独立页存在（已发布）时才渲染成链接：指向 404 比不可点更糟；
 * ② 不存在 / 列表取不到时退回纯文本，「同意」这一步不依赖它们。
 * 因此链接必须走 localeHref（语言前缀）且判据来自 GET /pages 的 slug 集合。
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const registerPage = readFileSync(resolve(process.cwd(), 'pages/register.vue'), 'utf8')

describe('注册页同意条款指向真实的独立页', () => {
  it('判据来自 GET /pages 的已发布页 slug 集合', () => {
    expect(registerPage, '必须用 silentApiFetch —— 列表取不到不该弹错误提示')
      .toMatch(/silentApiFetch<\{ items\?: \{ slug\?: string \}\[\] \}>\('\/pages'/)
    expect(registerPage).toMatch(/consentDocSlugs\.value = new Set\(/)
  })

  it('两套注册骨架都按 slug 决定链接/纯文本', () => {
    // 默认骨架 + 极简主题骨架各一处；少一处就是某个主题下仍然不可点
    expect([...registerPage.matchAll(/hasConsentDoc\('terms'\)/g)].length).toBe(2)
    expect([...registerPage.matchAll(/hasConsentDoc\('privacy'\)/g)].length).toBe(2)
  })

  it('链接走语言前缀助手，不拼裸 href', () => {
    expect(registerPage).toContain('localeHref(\'/terms\')')
    expect(registerPage).toContain('localeHref(\'/privacy\')')
    expect(registerPage, '裸 href 会丢掉 /en /ja /zh_Hant 前缀')
      .not.toMatch(/href="\/terms"/)
  })

  it('未发布时退回纯文本（每处链接都有 v-else 兜底）', () => {
    for (const key of ['auth.terms', 'auth.privacy']) {
      const escaped = key.replace('.', '\\.')
      expect(registerPage, `${key} 缺少 v-else 纯文本分支`)
        .toMatch(new RegExp(`v-else[\\s\\S]{0,240}t\\('${escaped}'`))
    }
  })
})
