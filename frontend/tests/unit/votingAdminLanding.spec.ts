/**
 * 后台投票入口 + 侧栏菜单可达性契约。
 *
 * 表现过的两类 bug：
 * 1. 后端 /api/voting/polls 的 POST/DELETE 早已存在，前端**一个调用方都没有**，
 *    结果是「投票」功能对站主等于不存在——前台文章页能投票，却没有任何地方能创建投票。
 * 2. 后台仪表盘快捷入口指向 /admin/roles，而该路由从未有过页面文件：点了被
 *    admin.global 中间件弹回 /，看起来像"按钮坏了"。菜单与页面文件不同步是静默失效，
 *    不会有任何报错，所以这里把「菜单里每条 path 都必须有对应页面文件」钉成门禁。
 */

import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

const menuSrc = readFileSync(resolve(process.cwd(), 'config/admin-menu.ts'), 'utf8')
const pollsPage = readFileSync(resolve(process.cwd(), 'pages/admin/interaction/polls.vue'), 'utf8')
const pollsComposable = readFileSync(resolve(process.cwd(), 'composables/usePolls.ts'), 'utf8')
const header = readFileSync(resolve(process.cwd(), 'components/AppHeader.vue'), 'utf8')

/** adminMenu 里声明的全部 path（单源：config/admin-menu.ts）。 */
const menuPaths: string[] = [...menuSrc.matchAll(/path:\s*'([^']+)'/g)].map(m => m[1] ?? '')

function pageFileFor(path: string): string | null {
  const rel = path === '/admin' ? 'pages/admin/index' : `pages${path}`
  for (const candidate of [`${rel}.vue`, `${rel}/index.vue`]) {
    if (existsSync(resolve(process.cwd(), candidate))) return candidate
  }
  // catchall 目录页：/admin/docs 由 pages/admin/docs/[...slug].vue 接住，
  // 没有 index.vue 也算可达（Nuxt 的 catchall 匹配父路径本身）。
  if (existsSync(resolve(process.cwd(), `${rel}/[...slug].vue`))) return `${rel}/[...slug].vue`
  return null
}

describe('后台菜单与投票入口', () => {
  it('adminMenu 每条 path 都有对应页面文件（防 /admin/roles 型死链回流）', () => {
    expect(menuPaths.length, '菜单项不应为空，否则本条断言会假绿').toBeGreaterThan(20)
    const dead = menuPaths.filter(p => pageFileFor(p) == null)
    expect(dead, `这些菜单项没有对应页面文件：${dead.join(', ')}`).toEqual([])
  })

  it('投票管理页已登记进侧栏菜单', () => {
    expect(menuPaths).toContain('/admin/interaction/polls')
  })

  it('投票页真正消费创建/删除接口，不是只读壳', () => {
    for (const fn of ['fetchAllPolls', 'createPoll', 'deletePoll']) {
      expect(pollsPage, `投票页必须调用 ${fn}()`).toContain(`pollsAPI.${fn}(`)
    }
    // 只断言到"方法 + 路径"这一层：引号形态（单引号 / 反引号模板）不是契约，
    // 写死引号会让一次无害的字符串改写变成假红灯。
    const RE_CREATE = /apiFetch<Poll>\(\s*['"`]\/voting\/polls['"`],\s*\{ method: 'POST'/
    const RE_DELETE = /apiFetch<unknown>\(\s*['"`]\/voting\/polls\/\$\{pollId\}['"`],\s*\{ method: 'DELETE'/
    expect(pollsComposable, '创建必须打 POST /voting/polls').toMatch(RE_CREATE)
    expect(pollsComposable, '删除必须打 DELETE /voting/polls/{id}').toMatch(RE_DELETE)
    // 后端只有 POST/DELETE，没有 PUT：页面不得伪装出"编辑"入口
    expect(pollsPage, '后端无更新接口，页面不得出现假编辑按钮').not.toContain('openEdit')
  })

  it('投票选项按后端 PollCreate 口径校验（2–200 个、非空）', () => {
    expect(pollsPage).toMatch(/cleanChoices/)
    expect(pollsPage).toMatch(/length < 2/)
    expect(pollsPage).toMatch(/maxlength="200"/)
  })

  it('Dashboard 入口只对 staff 渲染，且移动端抽屉补上 /settings', () => {
    // 桌面下拉与移动抽屉两处都必须 gate：/admin/** 的中间件会把普通成员静默弹回 /
    const dashboardGates = [...header.matchAll(/authStore\.isAdmin/g)]
    expect(dashboardGates.length, '桌面 + 移动两处 Dashboard 入口都要按 isAdmin 收口')
      .toBeGreaterThanOrEqual(2)
    expect(header, '移动端抽屉必须能进 /settings（此前只有桌面下拉有）')
      .toMatch(/navigateTo\('\/settings'\)/)
  })
})
