/**
 * 阅读历史链路（写口 → 存储 → 周期榜 / 个人中心）的接线守卫。
 *
 * 缺陷类：`post_view_histories` 有读无写。周期榜 day/week/month 的 `recent_views`
 * 与个人中心「阅读历史」都读这张表，但后端没有任何插入点——线上读数恒为 0 / 空列表，
 * 接口层不报一个错。文章详情接口不能兼任写手（SSR 首屏无 token、匿名读走缓存分支），
 * 所以必须由文章页在登录态下补一次 `POST /blog/posts/{id}/view`。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')
const reader = readFileSync(resolve(ROOT, 'pages/posts/[slug].vue'), 'utf8')
const account = readFileSync(resolve(ROOT, 'pages/account/index.vue'), 'utf8')
const backend = readFileSync(resolve(ROOT, '../backend/api/blog.py'), 'utf8')

function section(source: string, start: string, end: string): string {
  const from = source.indexOf(start)
  expect(from, `找不到起点：${start}`).toBeGreaterThanOrEqual(0)
  const rest = source.slice(from)
  const to = rest.indexOf(end)
  expect(to, `找不到终点：${end}`).toBeGreaterThan(-1)
  return rest.slice(0, to)
}

describe('阅读历史写口接线', () => {
  it('后端声明写入口，且按匿名视角做可见性判定', () => {
    expect(backend).toContain('"/posts/{post_id}/view"')
    const handler = section(backend, 'async def record_post_view', '# ==================== 分类接口')
    expect(handler).toContain('post_is_publicly_visible(post, None)')
    // 唯一索引是去重口径：先查存在行，再 INSERT（savepoint 兜并发）/UPDATE
    expect(handler).toContain('PostViewHistory')
    expect(handler).toContain('begin_nested')
  })

  it('文章页在登录态下补记，且失败不打断阅读', () => {
    const fn = section(reader, 'async function recordReadHistory', 'const loadCommentsForCurrentPost')
    expect(fn).toContain('apiFetch(`/blog/posts/${id}/view`')
    expect(fn).toContain('silentToast: true')
    expect(fn).toContain('authStore.isAuthenticated')
    // 同一篇只记一次；失败时释放去重位，等登录态恢复后补上
    expect(fn).toContain('recordedViewKey.value === key')
    expect(fn).toContain('recordedViewKey.value = \'\'')
  })

  it('首屏、路由切换、keep-alive 回访、登录态恢复四条时机都触发补记', () => {
    // onMounted / onActivated / watch(slug...) 三处必须把 recordReadHistory 并进 Promise.all
    const calls = reader.match(/recordReadHistory\(\)/g) ?? []
    expect(calls.length).toBeGreaterThanOrEqual(4)
    expect(reader).toContain('watch(() => authStore.isAuthenticated, recordReadHistory)')
  })

  it('个人中心用同一张表渲染阅读历史（读口已接通，缺的只是写口）', () => {
    expect(account).toContain('`/blog/users/me/${tab.value}`')
    expect(account).toContain('tab.value === \'history\' ? (rows.value as AccountHistoryRow[])')
    expect(account).toContain('\'/blog/users/me/history\', { method: \'DELETE\' }')
  })
})
