/**
 * /posts/hot 的榜单口径切换（A3 收口）。
 *
 * `/api/ranking/posts`（day/week/month/all 四档周期榜）此前是零前端消费者的死口：
 * 热榜页只拉 /blog/posts/hot 的综合评分，运营者后台配了 view_histories 也看不到
 * "本周最热"。现在两个端点都由这一页消费，且周期进 URL（分享 ?rank=week 不能落回综合榜）。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const src = readFileSync(resolve(ROOT, 'pages/posts/hot.vue'), 'utf-8')
const locale = JSON.parse(readFileSync(resolve(ROOT, 'i18n/locales/zh.json'), 'utf-8'))

describe('hot 页榜单周期切换', () => {
  it('两个端点都被消费（/ranking/posts 不再是死口）', () => {
    expect(src).toContain('\'/blog/posts/hot\'')
    expect(src).toContain('\'/ranking/posts\'')
  })

  it('四档周期 + 综合共五种取值，且白名单校验后才进状态', () => {
    expect(src).toContain('const RANK_PERIODS = [\'hot\', \'day\', \'week\', \'month\', \'all\']')
    expect(src).toContain('isRankPeriod(route.query.rank)')
  })

  it('周期写回 URL（hot 是默认态，不写冗余参数）', () => {
    expect(src).toContain('router.replace({ query: next === \'hot\' ? {} : { rank: next } })')
  })

  it('query 跟随周期：非 hot 才发 period，避免综合榜被多余参数干扰', () => {
    expect(src).toMatch(/period\.value === 'hot'\s*\?\s*\{ limit: defaultLimit \}\s*:\s*\{ period: period\.value, limit: defaultLimit \}/)
  })

  it('榜单条目补齐成 PostCard 认得的形状（title 保持多语言 dict）', () => {
    expect(src).toContain('title: row.title')
    expect(src).toContain('likes_count: row.likes_count ?? 0')
    expect(src).toContain('comments_count: row.comments_count ?? 0')
    expect(src).toContain('published_at: row.published_at ?? row.created_at ?? null')
  })

  it('切换器是 radiogroup 语义（整块内容随选择替换，不是 Tab 面板）', () => {
    expect(src).toContain('role="radiogroup"')
    expect(src).toContain('role="radio"')
    expect(src).toContain(':aria-checked="period === opt.value"')
  })

  it('四种语言的档位文案齐全（缺 key 界面会显示裸 key）', () => {
    for (const f of ['zh', 'en', 'ja', 'zh_Hant']) {
      const doc = JSON.parse(readFileSync(resolve(ROOT, `i18n/locales/${f}.json`), 'utf-8'))
      const posts = doc.posts as Record<string, string>
      for (const k of ['rankHot', 'rankDay', 'rankWeek', 'rankMonth', 'rankAll', 'rankAria']) {
        expect(posts[k], `${f}.json 缺 posts.${k}`).toBeTruthy()
      }
    }
    // 兜底：本文件的 zh 快照与页面模板用的 key 同名
    expect(locale.posts.rankWeek).toBeTruthy()
  })
})
