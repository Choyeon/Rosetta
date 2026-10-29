/**
 * `frontend/docs/API_COVERAGE.md` 的判定与代码对账（静态源码断言，不开浏览器）。
 *
 * 缺陷形状不是代码错，是**表格记忆错**：缺口清单是后续每个切片的选题依据，
 * 判定写歪就会反复挑错目标。2026-10-29 现场复核 ❌ 列表，三条"缺口"其实早就接好了
 * （hero 排期窗与次按钮、系列启停 toggle、审计日志手动清理），另有两条把语义读反
 * （`post_series/complete` 被当成"标记系列完成"、`post_encryption` 一族被当成"等 UI 的密码门"）。
 * 所以这里守两件事：
 * 1. 判据里说的"已接"必须能在真正的消费点找到（页面绑了控件、wrapper 发了那条路径）；
 * 2. 作废的旧判定只能作为"被引用的旧说法"留在文里——同一条行必须带「旧判定」标记，
 *    否则它就又变成一个看起来还成立的缺口。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

function read(rel: string): string {
  return readFileSync(resolve(process.cwd(), rel), 'utf8').replace(/\r\n/g, '\n')
}

const doc = read('docs/API_COVERAGE.md')
const heroPage = read('pages/admin/content/hero.vue')
const seriesPage = read('pages/admin/content/series.vue')
const auditPage = read('pages/admin/tools/audit-logs.vue')
const manage = read('composables/useAdminManage.ts')
const postForm = read('components/admin/PostForm.vue')
const postDetail = read('pages/posts/[slug].vue')
const commentsApi = read('composables/useComments.ts')
const backendSeries = read('../backend/api/post_series.py')
const backendHero = read('../backend/api/hero.py')
const backendAnnouncement = read('../backend/api/announcement.py')
const backendActivity = read('../backend/api/activity.py')

/** 文档里提到某个字符串的所有行（判定是否还作为"现行结论"活着，就看这些行） */
function docLinesMentioning(needle: string): string[] {
  return doc.split('\n').filter(line => line.includes(needle))
}

describe('hero 排期窗与次按钮：文档说"已开放"就必须真的开放', () => {
  it('管理页真的绑了 start_time/end_time 两个输入并有清除入口', () => {
    expect(heroPage).toMatch(/v-model="form\.start_time"/)
    expect(heroPage).toMatch(/v-model="form\.end_time"/)
    expect(heroPage).toMatch(/@click="form\.start_time = ''"/)
    expect(heroPage).toMatch(/@click="form\.end_time = ''"/)
  })

  it('提交时按"空＝长期生效"发 null，而不是把空串发给后端', () => {
    expect(heroPage).toMatch(/start_time: fromDateTimeLocal\(form\.start_time\)/)
    expect(heroPage).toMatch(/end_time: fromDateTimeLocal\(form\.end_time\)/)
  })

  it('倒挂窗口在提交前拦截（复用公告那一族的判据）', () => {
    expect(heroPage).toMatch(/announcementScheduleError\(form\.start_time, form\.end_time\)/)
  })

  it('次按钮两字段是表单字段而不是只读展示', () => {
    expect(heroPage).toMatch(/v-model="form\.cta_secondary_text"/)
    expect(heroPage).toMatch(/v-model="form\.cta_secondary_url"/)
    expect(heroPage).toMatch(/cta_secondary_url: form\.cta_secondary_url\.trim\(\) \|\| null/)
  })

  it('文档不再把这些字段写成"暂未开放界面"', () => {
    expect(doc).not.toContain('暂未开放界面')
  })
})

describe('系列启停：toggle 口已接，文档不得再判成"重复入口待收敛"', () => {
  it('wrapper 打的就是后端那条翻转口', () => {
    expect(manage).toMatch(/`\/admin\/series\/\$\{id\}\/toggle`/)
  })

  it('系列管理页消费该 wrapper', () => {
    expect(seriesPage).toContain('toggleAdminSeries')
    expect(seriesPage).toMatch(/await toggleAdminSeries\(/)
  })

  it('后台不在本地取反（翻转语义必须回读服务端结果）', () => {
    expect(seriesPage).not.toMatch(/is_active: !.*\.is_active/)
  })

  it('旧判定只作为被引用的作废说法存在', () => {
    for (const line of docLinesMentioning('后台用 PUT 代替')) {
      expect(line).toContain('旧判定')
    }
    expect(docLinesMentioning('后台用 PUT 代替')).toHaveLength(1)
  })
})

describe('审计日志手动清理：已接，不得再算"无 UI 小缺口"', () => {
  it('wrapper 发 DELETE /admin/logs/retention', () => {
    expect(manage).toMatch(/\/admin\/logs\/retention/)
    expect(manage).toMatch(/method: 'DELETE'/)
  })

  it('审计日志页消费该 wrapper', () => {
    expect(auditPage).toContain('retention')
  })

  it('文档说明这条口只删操作留痕，访问日志/性能指标归服务端保留循环', () => {
    expect(doc).toContain('operation_logs')
    expect(doc).toContain('LOG_RETENTION_DAYS')
  })

  it('旧判定只作为被引用的作废说法存在', () => {
    for (const line of docLinesMentioning('无 UI——小缺口')) {
      expect(line).toContain('旧判定')
    }
  })
})

describe('post_series/complete 是编辑器 autocomplete，不是"标记系列完成"', () => {
  it('后端摘要写的是 autocomplete 同系列文章', () => {
    expect(backendSeries).toMatch(/summary="编辑器 autocomplete 同系列文章"/)
    expect(backendSeries).toMatch(/\/post_series\/complete"/)
  })

  it('编辑器已真正消费它（2026-10-29 批次 #50；旧判定「前端零消费」已作废）', () => {
    expect(manage).toMatch(/'\/post_series\/complete'/)
    expect(postForm).toContain('completeSeriesPosts')
    expect(doc).toMatch(/`POST \/post_series\/complete`/)
  })

  it('「标记系列完成」只能出现在被作废的那一行', () => {
    for (const line of docLinesMentioning('标记系列完成')) {
      expect(line).toMatch(/不是|旧判定/)
    }
  })
})

describe('密码门真相：在用的是 Post.password，不是 post_encryption 一族', () => {
  it('编辑器写 visibility=password 与 password', () => {
    expect(postForm).toMatch(/'public' \| 'password' \| 'private'/)
    expect(postForm).toMatch(/visibility/i)
  })

  it('读者侧正文与评论树都带 X-Post-Password 头（不进查询串）', () => {
    expect(postDetail).toMatch(/'X-Post-Password'/)
    expect(commentsApi).toMatch(/'X-Post-Password': postPassword/)
  })

  it('文档不再把 post_encryption 判成"编辑器无加密设置 UI"的待接缺口', () => {
    for (const line of docLinesMentioning('编辑器无加密设置 UI')) {
      expect(line).toContain('旧判定')
    }
    expect(doc).toContain('退役候选')
  })
})

describe('…/{id}/toggle 一族：4 条口分两半，不得整族判成"刻意不用"', () => {
  it('后端确实是 4 条 toggle 路由', () => {
    for (const src of [backendHero, backendSeries, backendAnnouncement, backendActivity]) {
      expect(src).toMatch(/\/toggle"/)
    }
  })

  it('hero 与 series 两条有前端 wrapper', () => {
    expect(manage).toMatch(/\/admin\/hero\/slides\/\$\{id\}\/toggle/)
    expect(manage).toMatch(/\/admin\/series\/\$\{id\}\/toggle/)
  })

  it('公告与活动两条走的是显式写值，不是翻转口', () => {
    expect(manage).toMatch(/updateAdminAnnouncement/)
    expect(manage).not.toMatch(/\/admin\/announcements\/\$\{id\}\/toggle/)
    expect(manage).not.toMatch(/\/admin\/activities\/\$\{id\}\/toggle/)
  })

  it('文档不再写"各 …/{id}/toggle ×4"这种整族判定', () => {
    expect(doc).not.toContain('`…/{id}/toggle` ×4')
    expect(doc).not.toContain('toggle 一族前端刻意不用')
  })
})

describe('users 段：注销接入后手写清单与自动表必须同时改口', () => {
  // 18✅ 是注销（DELETE /me）那一轮；作者目录（GET /users/authors）接入后 +1 → 19✅ / 23 条。
  // 这一行只许跟着生成器走：改接口或改接线后跑 gen_api_coverage.py --write，再同步这里。
  it('自动表 users 行是 23 条 / 19✅ / 4❌', () => {
    expect(doc).toMatch(/\| users \| 23 \| 19 \| 0 \| 4 \|/)
  })

  it('手写的 ❌ 清单不再把 DELETE /me 列为缺口', () => {
    const line = doc.split('\n').find(l => l.startsWith('❌（') && l.includes('/me/change-password'))
    expect(line, 'users 段的手写 ❌ 行没了').toBeTruthy()
    expect(line).toContain('❌（7）')
    expect(line).not.toContain('`DELETE /me`')
  })

  it('文档写的是软删除口径，不是"内容将被删除"', () => {
    const at = doc.search(/DELETE \/api\/users\/me/)
    expect(at).toBeGreaterThan(-1)
    const window = doc.slice(at, at + 400)
    expect(window).toContain('软删除')
    expect(window).toContain('is_active=False')
  })
})
