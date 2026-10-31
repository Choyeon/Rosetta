/**
 * 批次 #143：评论者自填网站（author_website）的四段口径守卫。
 *
 * 后端早就写完三段（`CommentCreate` 收 → `comments.author_website` 列 →
 * `CommentResponse.author_website` 投影，且投影处已过 `HTTP_URL_RE`），
 * 唯独第四段「消费方」空着：评论线程从不渲染它，留言板却渲染了。
 * 于是运营者后台看到"留言者填了网站"、文章底下什么也没有。
 *
 * 这个 spec 钉三件事：
 * 1. 渲染面真的存在（`<template>` 区里有那条 `<a>`，不是只在 script 里算了个没人用的值）；
 * 2. href 过 `safeUgcHref`（库里的脏值不能直接进 href）；
 * 3. 两处死读 `author_email` 一起删掉——`CommentResponse` / `GuestbookEntryResponse`
 *    按"对外公开，已脱敏"的口径都不投影邮箱，前端读它就是恒 undefined。
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { safeUgcHref, ugcLinkLabel } from '~~/lib/ugc-link'

const ROOT = join(__dirname, '..', '..')
const REPO = join(ROOT, '..')

const read = (rel: string) => readFileSync(join(ROOT, rel), 'utf-8')
const readBackend = (rel: string) => readFileSync(join(REPO, 'backend', rel), 'utf-8')

/** 只取 `<template>` 区，避免把 script 里的同名字符串当成渲染证据。 */
function templateOf(source: string): string {
  const start = source.indexOf('<template>')
  const end = source.lastIndexOf('</template>')
  expect(start).toBeGreaterThanOrEqual(0)
  expect(end).toBeGreaterThan(start)
  return source.slice(start, end)
}

describe('safeUgcHref：只有绝对 http(s) 才能进 href', () => {
  it('放行 http 与 https（大小写不敏感、首尾空白先剥）', () => {
    expect(safeUgcHref('https://example.com')).toBe('https://example.com')
    expect(safeUgcHref('http://example.com/a?b=1')).toBe('http://example.com/a?b=1')
    expect(safeUgcHref('  HTTPS://example.com  ')).toBe('HTTPS://example.com')
  })

  it('挡掉可执行协议、协议相对写法与空值', () => {
    expect(safeUgcHref('javascript:alert(1)')).toBe('')
    expect(safeUgcHref('data:text/html;base64,PHNjcmlwdD4=')).toBe('')
    expect(safeUgcHref('//example.com')).toBe('')
    expect(safeUgcHref('example.com')).toBe('')
    expect(safeUgcHref('https:/example.com')).toBe('')
    expect(safeUgcHref('')).toBe('')
    expect(safeUgcHref('   ')).toBe('')
    expect(safeUgcHref(null)).toBe('')
    expect(safeUgcHref(undefined)).toBe('')
  })

  it('展示文本只剥协议头，其余原样', () => {
    expect(ugcLinkLabel('https://example.com/a/')).toBe('example.com/a/')
    expect(ugcLinkLabel('http://example.com')).toBe('example.com')
  })
})

describe('评论线程渲染面', () => {
  const item = read('components/CommentItem.vue')
  const tpl = templateOf(item)

  it('作者名行里有那条网站链接，且 href 取的是过闸后的值', () => {
    expect(tpl).toContain('v-if="authorWebsite"')
    expect(tpl).toContain(':href="authorWebsite"')
    expect(tpl).toContain('{{ ugcLinkLabel(authorWebsite) }}')
    expect(item).toContain('const authorWebsite = computed(() => safeUgcHref(props.comment.author?.website))')
    expect(item).toContain('from \'~~/lib/ugc-link\'')
  })

  it('访客自填链接带 nofollow（与站内其它 UGC 出口同口径）', () => {
    expect(tpl).toContain('rel="noopener noreferrer nofollow"')
    expect(tpl).toContain('target="_blank"')
  })

  it('props 类型声明 website、不再声明后端不投影的 email', () => {
    expect(item).toContain('website?: string | null')
    expect(item).not.toMatch(/\bemail\?: string/)
  })
})

describe('详情页取数投影', () => {
  const page = read('pages/posts/[slug].vue')

  it('normalizeComment 把后端 snake_case 的 author_website 摊进 author 对象', () => {
    expect(page).toContain('website: rawText(raw.author_website) || rawText(raw.authorWebsite),')
  })

  it('删掉 author_email 死读（读侧与类型声明都不留）', () => {
    expect(page).not.toContain('rawText(raw.author_email)')
    expect(page).not.toMatch(/\bemail\?: string/)
    expect(page).toContain('website?: string | null')
  })
})

describe('留言板渲染面（同一族，防只补一半）', () => {
  const page = read('pages/guestbook.vue')
  const tpl = templateOf(page)

  it('列表行的 href 在映射处过一次 safeUgcHref', () => {
    expect(page).toContain('website: safeUgcHref(pickStr(\'author_website\') || pickStr(\'website\')) || undefined,')
    expect(page).toContain('from \'~~/lib/ugc-link\'')
    expect(tpl).toContain(':href="item.website"')
  })

  it('文本走单源 helper，不再在模板里手写正则', () => {
    expect(tpl).toContain('{{ ugcLinkLabel(item.website) }}')
    expect(tpl).not.toContain('.replace(/^https?:\\/\\//, \'\')')
    expect(tpl).toContain('rel="noopener noreferrer nofollow"')
  })

  it('删掉 author_email 死读（GuestbookEntryResponse 不投影邮箱）', () => {
    expect(page).not.toContain('author_email?: string')
    expect(page).not.toContain('author_email: pickStr(\'author_email\')')
  })
})

describe('后端三段仍是真源（前端接了别接在空气上）', () => {
  const schemas = readBackend('schemas/__init__.py')
  const commentService = readBackend('services/comment_service.py')

  it('CommentResponse 投影 author_website，且读侧带 http(s) 闸门', () => {
    const block = schemas.slice(
      schemas.indexOf('class CommentResponse'),
      schemas.indexOf('class CommentPagedResponse')
    )
    expect(block).toContain('author_website: str | None = None')
    expect(block).not.toContain('author_email')
    expect(commentService).toContain(
      'author_website=author_website if HTTP_URL_RE.match(author_website or "") else None,'
    )
  })

  it('写口收 author_website（表单发的键后端认）', () => {
    expect(schemas).toContain('author_website: str | None = Field(None, max_length=200)')
  })
})
