/**
 * 公告逻辑回归（composables/useAnnouncementBar.ts）。
 *
 * 钉住三件这条公告实现历史上做错/做漏的事：
 * ① 两个来源是两个表面，不再合一：设置页 notice 分组 → 顶部横幅单条；公告表
 *    GET /announcements → 侧栏卡多条。此前 mergeAnnouncementRows 把多条公告挤进横幅，
 *    而 notice.sticky 的文案是「滚动时仍然显示」、实际只用来排列表顺序——标签与执行点各说一套。
 * ② 两处正文都标着 Markdown，而横幅/侧栏是纯文本插值位：必须剥标记，不能让访客看到字面量 `**提示**`。
 * ③ is_dismissible=false 的公告必须无视浏览器里残留的关闭记录出现（管理员把可关闭改成不可关闭的场景）。
 */
import { describe, it, expect } from 'vitest'
import {
  ANNOUNCEMENT_DISMISS_KEY,
  SITE_NOTICE_ID,
  announcementDateText,
  announcementDotClass,
  announcementVariantClass,
  bannerIsSticky,
  canDismissAnnouncement,
  noticeToRow,
  stripInlineMarkdown,
  visibleAnnouncements,
  type AnnouncementRow
} from '../../composables/useAnnouncementBar'

const row = (over: Partial<AnnouncementRow> = {}): AnnouncementRow => ({
  id: 1,
  title: '系统维护',
  content: '今晚 22:00 起停机',
  type: 'warning',
  ...over
})

describe('stripInlineMarkdown', () => {
  it('去掉强调/代码/删除线/标题标记并折叠换行', () => {
    expect(stripInlineMarkdown('**提示**：`此处`可编辑\n## 正文')).toBe('提示：此处可编辑 正文')
  })

  it('链接只保留锚文本（横幅没有渲染 anchor 的位置）', () => {
    expect(stripInlineMarkdown('详见 [更新日志](/changelog)')).toBe('详见 更新日志')
  })

  it('空值安全', () => {
    expect(stripInlineMarkdown(undefined)).toBe('')
    expect(stripInlineMarkdown('   ')).toBe('')
  })
})

describe('visibleAnnouncements', () => {
  it('已关闭的可关闭公告被过滤', () => {
    expect(visibleAnnouncements([row({ id: 7 })], ['7'])).toEqual([])
  })

  it('is_dismissible=false 无视残留的关闭记录', () => {
    const locked = row({ id: 8, is_dismissible: false })
    expect(visibleAnnouncements([locked], ['8']).map(a => a.id)).toEqual([8])
  })

  it('不可关闭的行 id 不会被误伤（过滤条件不能只看存储）', () => {
    const rows = [row({ id: 1 }), row({ id: 2, is_dismissible: false })]
    expect(visibleAnnouncements(rows, ['1']).map(a => a.id)).toEqual([2])
  })

  it('标题与正文都按 Markdown 降级后呈现', () => {
    const [first] = visibleAnnouncements([row({ title: '**系统**维护', content: '见 [说明](/x)' })], [])
    expect(first?.title).toBe('系统维护')
    expect(first?.content).toBe('见 说明')
  })

  it('剥完标记什么都不剩时整行不渲染（不出空横幅）', () => {
    expect(visibleAnnouncements([row({ title: '****', content: '  ' })], [])).toEqual([])
  })

  it('正文与标题同文时保留原样，由模板负责去重展示', () => {
    const [first] = visibleAnnouncements([row({ title: '公告', content: '公告' })], [])
    expect(first?.content).toBe('公告')
  })
})

describe('noticeToRow', () => {
  it('未启用 → 无行', () => {
    expect(noticeToRow({ enable: false, title: 'x' })).toBeNull()
    expect(noticeToRow(undefined)).toBeNull()
  })

  it('启用但标题正文皆空 → 无行', () => {
    expect(noticeToRow({ enable: true, title: '  ', content_md: '' })).toBeNull()
  })

  it('映射 notice 分组字段：dismissible→is_dismissible、固定 id', () => {
    const r = noticeToRow({
      enable: true,
      type: 'error',
      title: '紧急',
      content_md: '**正文**',
      dismissible: false
    })
    expect(r).toEqual({
      id: SITE_NOTICE_ID,
      title: '紧急',
      content: '正文',
      type: 'error',
      is_dismissible: false
    })
  })
})

describe('顶部横幅与侧栏卡是两个表面', () => {
  it('sticky 缺省为真，只有显式 false 才不粘顶', () => {
    expect(bannerIsSticky({ enable: true, title: 'N' })).toBe(true)
    expect(bannerIsSticky({ enable: true, title: 'N', sticky: true })).toBe(true)
    expect(bannerIsSticky({ enable: true, title: 'N', sticky: false })).toBe(false)
    expect(bannerIsSticky(null)).toBe(true)
  })

  it('侧栏卡的类型点是实色（size-2 圆点用 10% alpha 底色会看不见）', () => {
    expect(announcementDotClass('warning')).toBe('bg-warning')
    expect(announcementDotClass('error')).toBe('bg-error')
    expect(announcementDotClass('success')).toBe('bg-success')
    expect(announcementDotClass('bogus')).toBe(announcementDotClass('info'))
    expect(announcementDotClass(undefined)).toBe('bg-info')
    expect(announcementDotClass('info')).not.toContain('/')
  })

  it('日期只截 ISO 串的日期段，不做本地化（SSR 与访客浏览器时区不同）', () => {
    expect(announcementDateText('2026-10-12T09:31:00+08:00')).toBe('2026-10-12')
    expect(announcementDateText(undefined)).toBe('')
    expect(announcementDateText(null)).toBe('')
    expect(announcementDateText(123 as unknown as string)).toBe('')
  })
})

describe('类型与关闭语义', () => {
  it('缺省视为可关闭，只有显式 false 才锁死', () => {
    expect(canDismissAnnouncement(row())).toBe(true)
    expect(canDismissAnnouncement(row({ is_dismissible: true }))).toBe(true)
    expect(canDismissAnnouncement(row({ is_dismissible: false }))).toBe(false)
  })

  it('未知 type 落回 info 配色，脏数据不会渲染出无底色横幅', () => {
    expect(announcementVariantClass('bogus')).toBe(announcementVariantClass('info'))
    expect(announcementVariantClass(undefined)).toContain('bg-info')
    expect(announcementVariantClass('error')).toContain('bg-error')
  })

  it('横幅底色只用语义令牌类，不得出现 Tailwind 具名色阶', () => {
    // 具名色阶没有明暗两档配对：写 `dark:` 分支等于每加一种类型就手工维护两套读数，
    // 而 bg-X / text-X-foreground 是成对定义的实心令牌，明暗各档已经一起调过。
    const named = /(?:bg|text|border)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-/
    for (const type of ['warning', 'error', 'success', 'info', undefined]) {
      const cls = announcementVariantClass(type)
      expect(named.test(cls), `type=${String(type)}: ${cls}`).toBe(false)
      expect(cls, `type=${String(type)}: ${cls}`).not.toContain('dark:')
      expect(cls).toContain('-foreground')
    }
  })

  it('关闭记录 key 与后端响应字段无关，是前端自有存储位', () => {
    expect(ANNOUNCEMENT_DISMISS_KEY).toBe('rosetta:dismissed-announcements')
  })
})
