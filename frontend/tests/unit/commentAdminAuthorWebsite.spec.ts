/**
 * 后台评论/留言列表的 author_website 四段对账 + 幽灵键清点（批次 #153）。
 *
 * 两端各欠一半：
 * - 后端一直在投影 `author_url`，而 `comments` 表**没有这一列**——`getattr(c, "author_url", None)`
 *   的兜底值把它伪装成"字段活着、只是这条没填"，OpenAPI 还给它写了说明。同族的
 *   `author_avatar`（无此列且零消费方）与 `author_avatar_source`（那是 schema 入参别名）一起退役。
 * - 真有数据的 `author_website`（游客自填，登录作者回落账号 website）前台评论线程早就在渲染，
 *   审核面一个消费点都没有：带外链的评论在后台看不出它给了访客一条外站链接。
 *
 * 本 spec 钉五件事：
 * 1. 幽灵键在源码、文档模型、OpenAPI 文档里都不再出现；
 * 2. `author_website` 由后端两条口（GET / PATCH）投影、前端行类型声明、模板真的渲染；
 * 3. 渲染走 `lib/ugc-link` 的 http(s) 闸门并带 nofollow，绝不把库里的原值直接进 href；
 * 4. `AdminGuestbookEntry` 不再重复声明继承来的键；
 * 5. parent_ref 的「回复 @昵称」只渲染一次（批次 #151 曾留下两份一模一样的 chip）。
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..')
const REPO = join(ROOT, '..')

const adminApi = readFileSync(join(REPO, 'backend', 'api', 'admin.py'), 'utf-8')
const endpointsDoc = readFileSync(join(REPO, 'backend', 'docs', 'api_endpoints.md'), 'utf-8')
const referenceDoc = readFileSync(join(REPO, 'backend', 'docs', 'api_reference.md'), 'utf-8')
const manage = readFileSync(join(ROOT, 'composables', 'useAdminManage.ts'), 'utf-8')
const listPart = readFileSync(
  join(ROOT, 'pages', 'admin', 'interaction', '_parts', 'CommentListContent.vue'),
  'utf-8'
)
const ugcLinkLib = readFileSync(join(ROOT, 'lib', 'ugc-link.ts'), 'utf-8')

/** Python 类体：从 `class X` 到下一个 `class` / `@router` 边界 */
function pyClassBody(name: string): string {
  const head = `class ${name}`
  const start = adminApi.indexOf(head)
  expect(start, `后端缺少 ${name}`).toBeGreaterThan(-1)
  const rest = adminApi.slice(start + head.length)
  const next = rest.search(/^(class |@)/m)
  return next === -1 ? rest : rest.slice(0, next)
}

/** TS interface 体（从声明行到该 interface 的收尾 `}`） */
function tsInterfaceBody(name: string): string {
  const head = `export interface ${name}`
  const start = manage.indexOf(head)
  expect(start, `前端缺少 ${name}`).toBeGreaterThan(-1)
  const rest = manage.slice(start + head.length)
  const end = rest.indexOf('\n}')
  expect(end, `${name} 没有收尾`).toBeGreaterThan(-1)
  return rest.slice(0, end)
}

describe('admin comment author_website wiring', () => {
  it('retired ghost keys are gone from source and docs', () => {
    expect(adminApi).not.toContain('"author_url"')
    expect(adminApi).not.toContain('"author_avatar"')
    // 兜底值会伪装成"这条没填"：评论实例上不允许再有 getattr(…, 默认值) 读不存在的列
    expect(adminApi).not.toContain('getattr(c, "author_url"')
    expect(adminApi).not.toContain('getattr(c, "avatar"')
    expect(adminApi).not.toContain('author_avatar_source')
    for (const doc of [endpointsDoc, referenceDoc]) {
      expect(doc, 'OpenAPI 文档仍在描述退役的幽灵键').not.toContain('author_url')
    }
  })

  it('both doc models declare author_website and no ghost', () => {
    for (const cls of ['CommentAdminBaseDoc', 'CommentAdminItemDoc', 'CommentAdminUpdatedDoc']) {
      const body = pyClassBody(cls)
      if (cls === 'CommentAdminBaseDoc') {
        expect(body).toContain('author_website: str | None')
        expect(body).not.toContain('author_url:')
        expect(body).not.toContain('author_avatar:')
      }
      expect(body).not.toContain('author_url:')
    }
  })

  it('backend projects author_website on both verbs', () => {
    expect(adminApi.match(/"author_website":/g) ?? []).toHaveLength(2)
  })

  it('frontend row type declares it once, inherited by the guestbook row', () => {
    expect(tsInterfaceBody('AdminCommentRow')).toContain('author_website?: string | null')
    // 继承来的键不许再声明一遍：两份声明迟早漂移
    expect(tsInterfaceBody('AdminGuestbookEntry')).not.toContain('author_website')
  })

  it('template renders it through the ugc protocol gate, never raw', () => {
    expect(listPart).toContain('~~/lib/ugc-link')
    expect(listPart).toContain('safeUgcHref(comment.author_website)')
    expect(listPart).toContain('rel="noopener noreferrer nofollow"')
    expect(listPart).toContain(':href="authorSite(comment)?.href"')
    // 库里躺 javascript: 时直接进 href 就是给每条审核行挂一条可执行链接
    expect(listPart).not.toContain(':href="comment.author_website"')
    expect(ugcLinkLib).toContain('SAFE_URL_RE')
  })

  it('parent_ref reply chip renders exactly once', () => {
    const chips = listPart.match(/回复 @\{\{ comment\.parent_ref\.nickname/g) ?? []
    expect(chips, '「回复 @昵称」出现了重复 chip').toHaveLength(1)
    const guards = listPart.match(/v-if="!isGuestbook && comment\.parent_ref"/g) ?? []
    expect(guards).toHaveLength(1)
  })
})
