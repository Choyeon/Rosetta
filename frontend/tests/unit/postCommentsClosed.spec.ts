/**
 * 文章级「允许评论」开关的接线守卫。
 *
 * 缺陷类：`Post.allow_comments` 有编辑器写口、有列、有响应字段，但唯一评论写口
 * `CommentService.create_comment` 从不读它，详情页也照样渲染输入框——运营者关掉开关后，
 * 访客照常能发表，后台回复口也照常能写（"有值没人执行"的假开关）。
 * 后端闸门与前端入口必须同批存在，任何一侧被删掉这条链路就退回假开关。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')
const reader = readFileSync(resolve(ROOT, 'pages/posts/[slug].vue'), 'utf8')
const service = readFileSync(resolve(ROOT, '../backend/services/comment_service.py'), 'utf8')
const api = readFileSync(resolve(ROOT, '../backend/api/comments.py'), 'utf8')

function section(source: string, start: string, end: string): string {
  const from = source.indexOf(start)
  expect(from, `找不到起点：${start}`).toBeGreaterThanOrEqual(0)
  const rest = source.slice(from)
  const to = rest.indexOf(end)
  expect(to, `找不到终点：${end}`).toBeGreaterThan(-1)
  return rest.slice(0, to)
}

describe('后端：评论写口按文章开关收口', () => {
  it('create_comment 读 post.allow_comments 并抛 COMMENT_POST_CLOSED', () => {
    const body = section(
      service,
      'async def create_comment',
      'author_name = (data.author_name or "").strip()'
    )
    expect(body).toContain('if not post.allow_comments:')
    expect(body).toContain('raise ValueError("COMMENT_POST_CLOSED")')
  })

  it('站点级关闭优先于文章级（顺序不能反）', () => {
    const body = section(
      service,
      'async def create_comment',
      'author_name = (data.author_name or "").strip()'
    )
    expect(body.indexOf('COMMENTS_DISABLED')).toBeGreaterThanOrEqual(0)
    expect(body.indexOf('COMMENTS_DISABLED')).toBeLessThan(body.indexOf('COMMENT_POST_CLOSED'))
    expect(body.indexOf('COMMENT_POST_CLOSED')).toBeLessThan(
      body.indexOf('COMMENT_GUEST_NOT_ALLOWED')
    )
  })

  it('错误映射回 403（不是 401：401 会被前端判成登录过期）', () => {
    expect(api).toContain('"COMMENT_POST_CLOSED": (403, "该文章已关闭评论")')
    // 403 是文章策略，前端 apiFetch 不会因它清登录态
    expect(api).toMatch(/"COMMENTS_DISABLED": \(403,/)
  })

  it('发表评论端点文档声明了这条业务码', () => {
    const create = section(
      api,
      'summary="发表评论（游客或登录用户均可）"',
      'dependencies=[Depends(rate_limit_sensitive("post_comment"))'
    )
    expect(create).toContain('COMMENT_POST_CLOSED')
    expect(create).toContain('allow_comments')
  })
})

describe('前台：详情页按 allow_comments 收起表单与回复入口', () => {
  it('详情类型声明了 allow_comments（缺省按允许处理）', () => {
    expect(reader).toContain('allow_comments?: boolean')
  })

  it('关闭态从详情响应派生，缺值不等于关闭', () => {
    expect(reader).toContain(
      'computed(() => post.value?.allow_comments === false)'
    )
    expect(reader).not.toMatch(/postCommentsClosed\s*=\s*computed\(\(\)\s*=>\s*!post\.value/)
  })

  it('表单与回复入口都被关闭态锁住', () => {
    const form = section(reader, 'const canCommentForm = computed(', 'const needCommentCaptcha')
    expect(form).toContain('!postCommentsClosed.value')
    const reply = reader.slice(reader.indexOf('const canReply = computed('))
    expect(reply.slice(0, 160)).toContain('!postCommentsClosed.value')
  })

  it('模板给出关闭说明，不再复用"请先登录"提示', () => {
    expect(reader).toContain('v-else-if="postCommentsClosed"')
    expect(reader).toContain('post.commentsClosedTitle')
    expect(reader).toContain('post.commentsClosedDesc')
  })

  it('四语文案齐备且键集一致', () => {
    const locales = ['zh', 'en', 'ja', 'zh_Hant']
    const dicts = locales.map(l =>
      JSON.parse(readFileSync(resolve(ROOT, `i18n/locales/${l}.json`), 'utf8'))
    )
    for (const d of dicts) {
      expect(typeof d.post.commentsClosedTitle).toBe('string')
      expect(d.post.commentsClosedTitle.length).toBeGreaterThan(0)
      expect(typeof d.post.commentsClosedDesc).toBe('string')
      expect(d.post.commentsClosedDesc.length).toBeGreaterThan(0)
    }
    const keys = dicts.map(d => Object.keys(d.post).sort().join(','))
    expect(new Set(keys).size).toBe(1)
  })
})
