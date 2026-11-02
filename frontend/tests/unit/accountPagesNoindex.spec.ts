/**
 * 个人中心每一页都必须自带 noindex 声明（静态源码断言）。
 *
 * `/account/**` 是 routeRules 精准反选的 SPA 页，服务端空壳的 robots 由
 * `server/utils/noindex-shell.ts` 的 `/account` 前缀补上；但站内从可索引页跳进
 * 个人中心时，客户端 `<head>` 里那条 robots 完全取决于页面自己有没有调
 * `useNoindexPage()`。少一页的表现是"这一页在渲染后的 DOM 里可以被索引"，
 * 而 Google 是会渲染 JS 的。所以按目录扫，新增第 N 页也必须带上声明。
 */

import { readdirSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const ACCOUNT_DIR = resolve(ROOT, 'pages/account')

const pageFiles = readdirSync(ACCOUNT_DIR)
  .filter(name => name.endsWith('.vue'))
  .sort()

describe('个人中心四页的 robots 口径一致', () => {
  it('目录确实扫到了页面（空目录会让下面的断言恒真）', () => {
    expect(pageFiles.length).toBeGreaterThanOrEqual(4)
  })

  it('每一页都调用 useNoindexPage()', () => {
    for (const name of pageFiles) {
      const source = readFileSync(resolve(ACCOUNT_DIR, name), 'utf-8')
      expect(source, `pages/account/${name} 漏了 useNoindexPage()`).toContain(
        'useNoindexPage()'
      )
    }
  })

  it('每一页都挂 auth-required，不把登录态内容做成可直出页', () => {
    for (const name of pageFiles) {
      const source = readFileSync(resolve(ACCOUNT_DIR, name), 'utf-8')
      expect(source, `pages/account/${name} 没有 auth-required 中间件`).toContain(
        "middleware: 'auth-required'"
      )
    }
  })

  it('/account 前缀在服务端空壳名单里（否则声明只存在于 hydration 之后）', () => {
    const shell = readFileSync(resolve(ROOT, 'server/utils/noindex-shell.ts'), 'utf-8')
    expect(shell).toContain("'/account'")
  })
})
