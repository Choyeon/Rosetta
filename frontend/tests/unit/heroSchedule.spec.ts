/**
 * 切片 #40：首页轮播「生效时间窗」两端接通（`start_time` / `end_time`）。
 *
 * 后端一直在按窗口过滤公开口，缺的是两端各一半：后台没有输入口，写口也不判倒挂
 * （`end <= start` 存得进去却永远不下发＝静默失效）。本文件钉三件事：
 *   ① 判据本身（边界含端点、留空＝长期、倒挂报错）——与后端 `api/hero.py` 的
 *      `start <= now AND end >= now` 同形，两侧共用 `lib/announcement` 这一份实现；
 *   ② 后台真的能填、能回填、能把两个键提交上去（漏回填＝每次 PUT 把已配置的排期抹成长期生效）；
 *   ③ 首页三档媒体各自有渲染分支（image 背景 / video 站内视频 / youtube 嵌入），
 *      分档与地址解析在 `lib/hero-media`（批次 #233）。
 *
 * 断言读源文本而不是跑组件：这些是"接线"口径，组件级 mock 测不出硬编码留在原地。
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { announcementScheduleError, announcementStatus, fromDateTimeLocal, toDateTimeLocal } from '../../lib/announcement'

const cwd = process.cwd()
const page = readFileSync(resolve(cwd, 'pages/index.vue'), 'utf8')
const admin = readFileSync(resolve(cwd, 'pages/admin/content/hero.vue'), 'utf8')

const at = (hours: number) => new Date(Date.now() + hours * 3600_000).toISOString()

describe('窗口判据：与后端过滤同形', () => {
  it('留空两端＝长期生效，且不算错', () => {
    expect(announcementStatus({ is_active: true })).toBe('active')
    expect(announcementScheduleError('', '')).toBeNull()
  })

  it('只填一侧也算合法（"从现在起一周"与"截止到某天"都是常见排期）', () => {
    expect(announcementStatus({ is_active: true, start_time: at(-1) })).toBe('active')
    expect(announcementStatus({ is_active: true, end_time: at(1) })).toBe('active')
    expect(announcementScheduleError(at(-1), '')).toBeNull()
    expect(announcementScheduleError('', at(1))).toBeNull()
  })

  it('未到点与已结束各自判出来，公开口此时不下发', () => {
    expect(announcementStatus({ is_active: true, start_time: at(2), end_time: at(6) })).toBe('scheduled')
    expect(announcementStatus({ is_active: true, start_time: at(-72), end_time: at(-24) })).toBe('expired')
  })

  it('停用优先于窗口：停用的行无论窗口如何都是 disabled', () => {
    expect(announcementStatus({ is_active: false, start_time: at(-1), end_time: at(1) })).toBe('disabled')
  })

  it('端点值属于"生效中"：判据必须是 <= / >=，不是 < / >', () => {
    // 后端两侧是 `start_time <= now` 与 `end_time >= now`，边界时刻属于窗口内。
    // 这里拿"就是现在"的两端喂进去——差一个等号就会在边界秒把正在展示的幻灯片判成未开始/已结束。
    const now = new Date()
    const iso = now.toISOString()
    expect(announcementStatus({ is_active: true, start_time: iso, end_time: iso }, now)).toBe('active')
  })

  it('倒挂窗口在提交前就报错（后端同判据再拦一次，422）', () => {
    expect(announcementScheduleError(at(2), at(1))).toBe('结束时间必须晚于开始时间')
    // start == end 的窗口里没有任何时刻满足 `start <= now <= end`，同一条判据必须拒掉
    expect(announcementScheduleError(at(1), at(1))).toBe('结束时间必须晚于开始时间')
    expect(announcementScheduleError(at(1), at(2))).toBeNull()
  })

  it('脏值不炸：无法解析的时间不参与判定', () => {
    expect(announcementStatus({ is_active: true, start_time: 'not-a-date', end_time: 'also-bad' })).toBe('active')
  })
})

describe('datetime-local 换算：朴素值按 UTC 解释', () => {
  it('带 Z 的 ISO 与朴素 ISO 都转成同一本地墙钟形态', () => {
    const local = toDateTimeLocal('2026-09-30T10:00:00Z')
    expect(local).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/)
    expect(toDateTimeLocal('2026-09-30T10:00:00')).toBe(local)
  })

  it('空值转成 null 而不是空串（后端只收 datetime 或 null，传 \'\' 撞 422）', () => {
    expect(fromDateTimeLocal('')).toBeNull()
    expect(fromDateTimeLocal(null)).toBeNull()
    expect(fromDateTimeLocal(undefined)).toBeNull()
    expect(toDateTimeLocal(null)).toBe('')
  })
})

describe('后台表单：两个框、回填、提交键', () => {
  it('form 里有这两个键，且新建时留空', () => {
    expect(admin).toMatch(/start_time: string/)
    expect(admin).toMatch(/end_time: string/)
    expect(admin).toContain('form.start_time = \'\'')
    expect(admin).toContain('form.end_time = \'\'')
  })

  it('两个 datetime-local 输入框 + 各自的清除按钮', () => {
    expect(admin).toContain('v-model="form.start_time"')
    expect(admin).toContain('v-model="form.end_time"')
    expect(admin.match(/type="datetime-local"/g)?.length).toBe(2)
    expect(admin).toContain('aria-label="清除开始时间"')
    expect(admin).toContain('aria-label="清除结束时间"')
  })

  it('编辑时回填（不回填＝每次 PUT 把已配置的排期抹成长期生效）', () => {
    expect(admin).toContain('toDateTimeLocal(slide.start_time)')
    expect(admin).toContain('toDateTimeLocal(slide.end_time)')
  })

  it('提交时带上两个键，空串走 null（显式 null 才表达"取消排期"）', () => {
    expect(admin).toContain('start_time: fromDateTimeLocal(form.start_time)')
    expect(admin).toContain('end_time: fromDateTimeLocal(form.end_time)')
  })

  it('提交前先过窗口自检', () => {
    expect(admin).toContain('announcementScheduleError(form.start_time, form.end_time)')
  })

  it('列表有"生效窗口"这一列，四种状态都有文案', () => {
    expect(admin).toMatch(/\{ key: 'schedule', title: '生效窗口'/)
    expect(admin).toContain('announcementStatus(row as AdminHeroSlide)')
    for (const key of ['active', 'scheduled', 'expired', 'disabled']) {
      expect(admin, `SCHEDULE_LABEL 缺 ${key}`).toMatch(new RegExp(`^  ${key}: '`, 'm'))
    }
  })

  it('顶部契约注释不再声称"不开放"', () => {
    expect(admin).not.toContain('start_time/end_time 不开放')
  })
})

describe('首页读取侧', () => {
  it('三档媒体都参与轮播：不再按 media_type 过滤（只丢空地址的行）', () => {
    expect(page).toMatch(/filter\(s => Boolean\(s\.media_url\)\)/)
    expect(page).not.toMatch(/\(s\.media_type \?\? 'image'\) === 'image'/)
  })

  it('video 与 youtube 各有渲染分支，地址经 lib/hero-media 解码', () => {
    expect(page).toContain('v-if="heroYoutubeEmbedUrl"')
    expect(page).toContain('v-else-if="heroVideoUrl"')
    expect(page).toContain('youtubeEmbedUrl(extractYoutubeId(')
    expect(page).toContain('isSiteRelativeMediaUrl(')
  })

  it('HeroSlideApi 类型里带 media_type / poster_url', () => {
    expect(page).toMatch(/media_type\?: 'image' \| 'video' \| 'youtube'/)
    expect(page).toMatch(/poster_url\?: string \| null/)
  })
})
