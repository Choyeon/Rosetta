/**
 * 公告条逻辑回归（composables/useAnnouncementBar.ts）。
 *
 * 钉住三件这条横幅历史上做错/做漏的事：
 * ① 后端 GET /announcements 与设置页 notice 分组是两个独立来源，必须合成一条列表且
 *    notice 默认置顶（sticky=false 才落到末尾）——此前 notice 分组能存能读却没有任何读侧消费者。
 * ② 两处正文都标着 Markdown，而横幅是单行纯文本插值位：必须剥标记，不能让访客看到字面量 `**提示**`。
 * ③ is_dismissible=false 的公告必须无视浏览器里残留的关闭记录出现（管理员把可关闭改成不可关闭的场景）。
 */
import { describe, it, expect } from 'vitest'
import {
  ANNOUNCEMENT_DISMISS_KEY,
  SITE_NOTICE_ID,
  announcementVariantClass,
  canDismissAnnouncement,
  mergeAnnouncementRows,
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

describe('noticeToRow / mergeAnnouncementRows', () => {
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

  it('sticky 默认置顶，sticky=false 落到表格公告之后', () => {
    const n = noticeToRow({ enable: true, title: 'N' })!
    expect(mergeAnnouncementRows(n, [row({ id: 3 })]).map(a => a.id)).toEqual([SITE_NOTICE_ID, 3])
    expect(mergeAnnouncementRows(n, [row({ id: 3 })], false).map(a => a.id)).toEqual([3, SITE_NOTICE_ID])
  })

  it('无 notice 行时原样返回表格列表', () => {
    const rows = [row({ id: 3 })]
    expect(mergeAnnouncementRows(null, rows)).toBe(rows)
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
    expect(announcementVariantClass(undefined)).toContain('bg-sky-500/10')
    expect(announcementVariantClass('error')).toContain('bg-rose-500/10')
  })

  it('关闭记录 key 与后端响应字段无关，是前端自有存储位', () => {
    expect(ANNOUNCEMENT_DISMISS_KEY).toBe('rosetta:dismissed-announcements')
  })
})
