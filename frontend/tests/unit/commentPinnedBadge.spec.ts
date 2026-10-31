/**
 * 批次 #146：评论置顶（is_pinned）的四段口径守卫。
 *
 * 后端三段早就齐了：`Comment.is_pinned` 列 → 后台 `PATCH` 写口 →
 * `CommentResponse.is_pinned` 投影，而且根评论列表按 `desc(is_pinned)` 排序。
 * 唯独第四段空着：文章页线程从不显示徽标，留言板同一族却显示了。
 * 于是「置顶」在后台是一个能点、能保存、会改变顺序的动作，
 * 在访客看到的那份 HTML 里却只是一个"这条评论莫名其妙排在最上面"。
 *
 * 这个 spec 钉四件事：
 * 1. 取数投影把后端的 snake_case 键摊进渲染用的形状（不在类型声明里漏掉它）；
 * 2. 渲染面在 `<template>` 区（不是 script 里算了个没人用的值）；
 * 3. 文案走四语 locale 已有的 `common.pinned`，不在组件里写死中文；
 * 4. 后端的排序判据与投影仍是真源（前端接了别接在空气上）。
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..')
const REPO = join(ROOT, '..')

const read = (rel: string) => readFileSync(join(ROOT, rel), 'utf-8')
const readBackend = (rel: string) => readFileSync(join(REPO, 'backend', rel), 'utf-8')

function templateOf(source: string): string {
  const start = source.indexOf('<template>')
  const end = source.lastIndexOf('</template>')
  expect(start).toBeGreaterThanOrEqual(0)
  expect(end).toBeGreaterThan(start)
  return source.slice(start, end)
}

describe('详情页取数投影', () => {
  const page = read('pages/posts/[slug].vue')

  it('normalizeComment 把 is_pinned 摊进评论形状（两种拼法都接）', () => {
    expect(page).toContain('isPinned: Boolean(raw.is_pinned ?? raw.isPinned)')
  })

  it('渲染用的类型声明里有这一位', () => {
    const block = page.slice(page.indexOf('type PostComment = {'))
    expect(block.slice(0, 1200)).toContain('isPinned?: boolean')
  })
})

describe('评论行渲染面', () => {
  const item = read('components/CommentItem.vue')
  const tpl = templateOf(item)

  it('作者名行里有置顶徽标，判据取自 props 上的那一位', () => {
    expect(tpl).toContain('v-if="comment.isPinned"')
    expect(item).toContain('isPinned?: boolean')
  })

  it('文案走 common.pinned（与留言板同一枚徽标同一个 key），不写死中文', () => {
    expect(tpl).toContain('{{ t(\'common.pinned\') }}')
    expect(tpl).not.toContain('置顶」')
  })

  it('Badge 组件真的被导入（模板里的标签不是裸字符串）', () => {
    expect(item).toContain('import { Badge } from \'~~/components/ui/badge\'')
  })
})

describe('留言板渲染面（同一族，防只补一半）', () => {
  const tpl = templateOf(read('pages/guestbook.vue'))
  it('留言板仍在读后端的 is_pinned', () => {
    expect(tpl).toContain('v-if="item.is_pinned"')
    expect(tpl).toContain('{{ t(\'common.pinned\')')
  })
})

describe('四语文案齐全', () => {
  for (const locale of ['zh', 'en', 'ja', 'zh_Hant']) {
    it(`${locale} 有 common.pinned`, () => {
      const json = JSON.parse(readFileSync(join(ROOT, 'i18n/locales', `${locale}.json`), 'utf-8'))
      expect(typeof json.common.pinned).toBe('string')
      expect(json.common.pinned.length).toBeGreaterThan(0)
    })
  }
})

describe('后端三段仍是真源', () => {
  const schemas = readBackend('schemas/__init__.py')
  const service = readBackend('services/comment_service.py')

  it('CommentResponse 投影 is_pinned', () => {
    const block = schemas.slice(
      schemas.indexOf('class CommentResponse'),
      schemas.indexOf('class CommentPagedResponse')
    )
    expect(block).toContain('is_pinned: bool = False')
  })

  it('根评论列表按置顶优先排序（徽标解释的就是这个顺序）', () => {
    expect(service).toContain('desc(Comment.is_pinned), desc(Comment.created_at)')
  })

  it('文章页真正打的那条树形口也按置顶优先（两处排序判据不得只有一处认账）', () => {
    const blog = readBackend('api/blog.py')
    const block = blog.slice(blog.indexOf('async def list_comments'))
    expect(block.slice(0, 3000)).toContain('(bool(x.is_pinned), x.created_at)')
  })

  it('后台写口收 is_pinned（点置顶真的落库），且是显式赋值不是省略即不动', () => {
    const admin = readBackend('api/admin.py')
    const body = admin.slice(
      admin.indexOf('class CommentAdminUpdate'),
      admin.indexOf('class CommentResponse')
    )
    expect(body).toContain('is_pinned: bool | None = Field(')
    expect(admin).toContain('comment.is_pinned = bool(data.is_pinned)')
  })

  it('后台评论菜单把置顶入口开给两族（评论不再被 isGuestbook 挡在门外）', () => {
    const part = read('pages/admin/interaction/_parts/CommentListContent.vue')
    expect(part).toContain('togglePinOrFeature(comment.id, \'pin\', !comment.is_pinned)')
    expect(part).toContain('await updateAdminCommentPin(id, Boolean(nextPinned))')
    expect(part).toContain('updateAdminCommentPin,')
  })
})
