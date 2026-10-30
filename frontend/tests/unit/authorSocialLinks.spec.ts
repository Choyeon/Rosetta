/**
 * 作者主页社交链接契约（静态源码断言，批次 #227）。
 *
 * `UserPreference.show_social_links` 是第六个隐私开关，唯一的展示面就是
 * `pages/authors/[username].vue` 里「网站 / GitHub」那一行。三条口径各自挡一种回归：
 *
 * 1. 资料口的 null 必须能收起**整行**：外层 `v-if` 判的是两个字段的存在性，
 *    不是各自一条链接——关掉开关后访客看到的不是"少一个链接"，而是这一整段消失。
 * 2. `github` 直接当 href 用。这一列存的是 GitHub 主页 URL（模型注释「GitHub 主页」、
 *    后台用户编辑口 placeholder `github.com/username`、写入侧 `_normalize_optional_url`
 *    补 scheme 三点同口径）。此前这里拼的是 `https://github.com/${profile.github}`，
 *    线上实测产出 `https://github.com/https://github.com/Choyeon`——每个作者的
 *    GitHub 链接都是死链。拼接形态由本文件反向钉住。
 * 3. 第三人作者卡片（`PublicUser`）不带这两个字段：它们受隐私开关管，而卡片挂在
 *    每篇匿名文章上、还进响应缓存，留着就是"换个路由就绕过开关"的旁路（邮箱同型缺陷）。
 *    出站链接的 `target="_blank"` 必须配 `rel="noopener noreferrer"`（AGENTS §12）。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const authorsPage = readFileSync(resolve(ROOT, 'pages/authors/[username].vue'), 'utf-8')
const apiTypes = readFileSync(resolve(ROOT, 'types/api.ts'), 'utf-8')
const settingsPage = readFileSync(resolve(ROOT, 'pages/account/settings.vue'), 'utf-8')

/** 取出 `export interface X { … }` 的正文 */
function interfaceBody(name: string): string {
  const start = apiTypes.indexOf(`export interface ${name} {`)
  expect(start, `types/api.ts 里找不到 ${name}`).toBeGreaterThan(-1)
  const end = apiTypes.indexOf('\n}', start)
  expect(end, `${name} 没有闭合`).toBeGreaterThan(start)
  return apiTypes.slice(start, end)
}

describe('作者主页社交链接', () => {
  it('整行收在两个字段的存在性之下（隐私开关置 null 即整段消失）', () => {
    expect(authorsPage).toMatch(/v-if="profile\?\.website \|\| profile\?\.github"/)
  })

  it('github 当作已存好的主页 URL 使用，不再拼 github.com 前缀', () => {
    expect(authorsPage).toMatch(/:href="profile\.github"/)
    // 只钉**绑定形态**：模板注释里引用旧写法是说明，不是回归
    expect(
      authorsPage,
      '这一列存的是 URL，拼接会产出 https://github.com/https://… 死链'
    ).not.toMatch(/:href="`https:\/\/github\.com\/\$\{/)
  })

  it('两条出站链接都带 target=_blank 与 rel=noopener noreferrer', () => {
    for (const key of ['website', 'github']) {
      const at = authorsPage.indexOf(`v-if="profile?.${key}"`)
      expect(at, `缺少 profile?.${key} 的链接分支`).toBeGreaterThan(-1)
      const anchor = authorsPage.slice(at, authorsPage.indexOf('</a>', at))
      expect(anchor, `${key} 链接缺 href`).toContain(`:href="profile.${key}"`)
      expect(anchor, `${key} 链接的 target 丢了`).toContain('target="_blank"')
      expect(anchor, `${key} 链接未切断 opener/noreferrer`).toContain(
        'rel="noopener noreferrer"'
      )
    }
  })

  it('作者资料视图保留这两个可空字段（遮蔽发生在后端资料口）', () => {
    expect(authorsPage).toMatch(/website\?: string \| null/)
    expect(authorsPage).toMatch(/github\?: string \| null/)
  })

  it('第三人作者卡片不带社交链接，本人/后台的 User 类型仍带', () => {
    const publicUser = interfaceBody('PublicUser')
    expect(publicUser).not.toMatch(/^\s*website\?:/m)
    expect(publicUser).not.toMatch(/^\s*github\?:/m)
    const user = interfaceBody('User')
    expect(user).toMatch(/^\s*website\?: string$/m)
    expect(user).toMatch(/^\s*github\?: string$/m)
  })

  it('账号设置页的 GitHub 输入框按 URL 口径给提示，与后台编辑口一致', () => {
    // 两端表单教给运营者的形态必须与读取方（作者主页把值直接当 href）一致，
    // 否则用户填法一变就产出死链，而这正是本批次修掉的那条缺陷。
    expect(settingsPage).toMatch(/id="profile-github"[\s\S]{0,200}placeholder="github\.com\/username"/)
  })
})
