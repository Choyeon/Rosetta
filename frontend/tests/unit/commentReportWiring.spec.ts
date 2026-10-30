/**
 * 评论举报（批次 #234）四段接线契约：写口 → 存储 → 响应模型 → 消费方。
 *
 * 这一族最容易出现的半成品是「后端齐了、前台没有入口」：`POST /comments/{id}/report`
 * 与 `/admin/comments/reports` 都能 curl 通，但评论卡片没有举报按钮、后台没有举报页签，
 * 于是功能等于不存在，而任何单一侧的测试都不会红。这里按"集合相等"钉住三件事：
 * ① 举报原因枚举：后端 Literal ⇔ 前台类型 ⇔ 评论卡片按钮（三处同一批值）；
 * ② 每条通道都有真实调用方（举报按钮 / 后台页签 / reported_only 筛选）；
 * ③ 文案键在四语里都存在（漏一个就是页面显示裸 key）。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(process.cwd())
const BACKEND_ROOT = resolve(ROOT, '..')
const read = (...parts: string[]) => readFileSync(resolve(...parts), 'utf-8')
const readFrontend = (...parts: string[]) => read(ROOT, ...parts)
const readBackend = (...parts: string[]) => read(BACKEND_ROOT, ...parts)

const schemaSrc = readBackend('backend', 'schemas', 'comment_report.py')
const reportApi = readBackend('backend', 'api', 'comment_report.py')
const adminApi = readBackend('backend', 'api', 'admin.py')
const useAdminManage = readFrontend('composables', 'useAdminManage.ts')
const useComments = readFrontend('composables', 'useComments.ts')
const commentItem = readFrontend('components', 'CommentItem.vue')
const postPage = readFrontend('pages', 'posts', '[slug].vue')
const commentsPage = readFrontend('pages', 'admin', 'interaction', 'comments.vue')
const reportsPanel = readFrontend('pages', 'admin', 'interaction', '_parts', 'CommentReportsPanel.vue')
const commentList = readFrontend(
  'pages',
  'admin',
  'interaction',
  '_parts',
  'CommentListContent.vue'
)

const LOCALES = ['zh', 'en', 'ja', 'zh_Hant']

function sorted(values: Iterable<string>): string[] {
  return [...values].sort()
}

function backendReasons(): string[] {
  const literal = schemaSrc.match(/ReportReason\s*=\s*Literal\[([^\]]+)\]/)?.[1]
  if (!literal) throw new Error('找不到 ReportReason Literal——枚举形态变了要同步改本测试')
  return sorted([...literal.matchAll(/"([a-z_]+)"/g)].map(m => m[1] as string))
}

function frontendTypeReasons(): string[] {
  const union = useAdminManage.match(/export type AdminCommentReportReason = ([^\n]+)/)?.[1]
  if (!union) throw new Error('找不到 AdminCommentReportReason 联合类型')
  return sorted([...union.matchAll(/'([a-z_]+)'/g)].map(m => m[1] as string))
}

function reportButtonReasons(): string[] {
  // 从 `= [` 起算：类型注解里的 `{ ... }[]` 也有 `]`，先匹配它会截掉整个数组
  const block = commentItem.match(/const REPORT_REASONS[^=]*=\s*\[([\s\S]*?)\n\]/)?.[1]
  if (!block) throw new Error('找不到 REPORT_REASONS——举报原因按钮清单不存在')
  return sorted([...block.matchAll(/value: '([a-z_]+)'/g)].map(m => m[1] as string))
}

describe('评论举报四段接线', () => {
  it('举报原因：后端 Literal == 前台类型 == 评论卡片按钮', () => {
    const expected = ['abuse', 'offtopic', 'other', 'spam']
    expect(backendReasons()).toEqual(expected)
    expect(frontendTypeReasons()).toEqual(expected)
    expect(reportButtonReasons()).toEqual(expected)
  })

  it('公开写口挂了可读性闸门与 CSRF（与表情反应同源）', () => {
    expect(reportApi).toContain('readable_comment_or_404')
    expect(reportApi).toContain('Depends(require_csrf)')
    expect(reportApi).toContain('SELF_REPORT')
  })

  it('评论卡片有举报入口，且由 canReport 控制（自己的评论不显示）', () => {
    expect(commentItem).toMatch(/canReport\??:\s*boolean/)
    expect(commentItem).toContain('@click="reportPanel = !reportPanel"')
    expect(commentItem).toContain('reportComment(props.comment.id')
    expect(postPage).toContain(':can-report="!isOwnComment(comment)"')
  })

  it('useComments 有 reportComment 且真的打到 /comments/{id}/report', () => {
    expect(useComments).toMatch(/const reportComment\s*=/)
    expect(useComments).toContain('/comments/${id}/report')
    expect(useComments).toContain('reportComment,')
  })

  it('后台举报页签消费列表与裁决两个通道', () => {
    expect(commentsPage).toMatch(/value: 'reports'/)
    expect(commentsPage).toContain('<CommentReportsPanel />')
    expect(useAdminManage).toMatch(/'\/admin\/comments\/reports'/)
    expect(useAdminManage).toContain('`/admin/comments/reports/${reportId}`')
    expect(reportsPanel).toContain('fetchAdminCommentReports')
    expect(reportsPanel).toContain('resolveAdminCommentReport')
  })

  it('reported_only 标记有真实消费方（评论列表筛选）', () => {
    expect(adminApi).toContain('reported_only')
    expect(adminApi).toContain('Comment.reported_at.is_not(None)')
    expect(commentList).toContain('reported_only:')
    expect(commentList).toContain('comment.reported_at')
  })

  it('举报相关文案四语齐全', () => {
    const keys = [
      'report',
      'reported',
      'reportHint',
      'reportSpam',
      'reportAbuse',
      'reportOfftopic',
      'reportOther',
      'reportDetailPlaceholder',
      'reportSubmit',
      'reportThanks'
    ]
    for (const locale of LOCALES) {
      const dict = JSON.parse(readFrontend('i18n', 'locales', `${locale}.json`)) as {
        comment: Record<string, string>
      }
      for (const key of keys) {
        expect(dict.comment[key], `${locale}.comment.${key}`).toBeTruthy()
      }
    }
  })
})
