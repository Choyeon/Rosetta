/**
 * 回收站三类可恢复资源（文章 / 独立页 / 评论）的前后端契约。
 *
 * 表现过的缺陷形态：回收站页的筛选器只有「全部 / 文章 / 评论」，而 `typeLabel` 里
 * 早就写了 `page`；后端 `restore` 也有一段评论分支——但**全仓没有任何评论或页面删除会
 * 写入回收站**，于是筛选永远为空、那段恢复代码从未被执行过（它只重建 4 个字段，
 * 而 comments.author_name / status 都是 NOT NULL，真跑到就是 500）。
 * 这类"UI 承诺 + 后端半成品 + 零写手"的组合不会报错，只能靠契约测试钉住：
 * ① 筛选器集合 == 后端真实写入的 resource_type 集合；
 * ② 每种入站类型都必须有自己的恢复分支；
 * ③ 快照字段必须覆盖恢复时重建的 NOT NULL 列；
 * ④「保留 30 天」要有执行者（到期清理挂在后台保留循环上）；
 * ⑤ 删除文案不许撒谎（评论/页面可恢复，留言板不可）。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(process.cwd())
const BACKEND = resolve(ROOT, '..')

const read = (...parts: string[]) => readFileSync(resolve(BACKEND, ...parts), 'utf-8')

const trashPage = read('frontend', 'pages', 'admin', 'content', 'trash.vue')
const pagesAdmin = read('frontend', 'pages', 'admin', 'content', 'pages.vue')
const commentList = read('frontend', 'pages', 'admin', 'interaction', '_parts', 'CommentListContent.vue')
const restoreApi = read('backend', 'api', 'advanced.py')
const pageApi = read('backend', 'api', 'core.py')
const commentApi = read('backend', 'api', 'admin.py')
const commentService = read('backend', 'services', 'comment_service.py')
const trashService = read('backend', 'services', 'trash.py')
const mainPy = read('backend', 'main.py')

/** 后端所有写入回收站的 resource_type（删除侧写手的唯一清单）。 */
function writtenResourceTypes(): string[] {
  const sources = [pageApi, commentApi, commentService, restoreApi, read('backend', 'api', 'blog.py')]
  const types = new Set<string>()
  for (const src of sources) {
    for (const m of src.matchAll(/resource_type="([a-z_]+)"/g)) {
      if (m[1]) types.add(m[1])
    }
  }
  return [...types].sort()
}

/** 回收站页筛选器的键（去掉「全部」）。 */
function filterKeys(): string[] {
  const block = trashPage.match(/const typeFilters = \[([\s\S]*?)\] as const/)?.[1]
  if (!block) throw new Error('找不到 typeFilters——筛选器形态变了要同步改本测试')
  const keys: string[] = []
  for (const m of block.matchAll(/key: '([a-z_]+)'/g)) {
    if (m[1] && m[1] !== 'all') keys.push(m[1])
  }
  return keys.sort()
}

describe('回收站可恢复资源契约', () => {
  it('筛选器集合与后端写手集合精确相等', () => {
    const written = writtenResourceTypes()
    expect(written).toEqual(['comment', 'page', 'post'])
    expect(filterKeys()).toEqual(written)
  })

  it('每种入站类型都有对应的恢复分支', () => {
    for (const type of writtenResourceTypes()) {
      expect(restoreApi).toContain(`trash_item.resource_type == "${type}"`)
    }
  })

  it('评论快照覆盖恢复时重建的非空列', () => {
    const payload = trashService.match(/def comment_trash_payload[\s\S]*?\n {4}return \{([\s\S]*?)\n {4}\}/)
    expect(payload, '找不到 comment_trash_payload').toBeTruthy()
    // author_name / status 在库里是 NOT NULL：漏一个，恢复评论就是 500 或评论静默消失
    for (const key of ['post_id', 'author_name', 'status', 'active', 'content', 'avatar_source']) {
      expect(payload![1]).toContain(`"${key}"`)
    }
    for (const key of ['author_name', 'status', 'avatar_source']) {
      expect(restoreApi).toContain(`${key}=resource_data.get("${key}")`)
    }
    expect(restoreApi).toContain('active=bool(resource_data.get("active", True))')
  })

  it('评论的删除写手有两条，且都走同一份快照', () => {
    // 单删（admin.py）与批量删（comment_service.py）必须同构，否则多选删除静默丢快照
    for (const src of [commentApi, commentService]) {
      expect(src).toContain('resource_type="comment"')
      expect(src).toContain('comment_trash_payload(')
    }
  })

  it('独立页删除写入 page 类型快照', () => {
    expect(pageApi).toContain('resource_type="page"')
    expect(pageApi).toContain('page_trash_payload(page)')
  })

  it('「保留 30 天」有执行者：到期清理挂在后台保留循环上', () => {
    expect(trashService).toContain('TRASH_RETENTION_DAYS = 30')
    const loop = mainPy.match(/async def _log_retention_loop[\s\S]*?\n\n@/)?.[0]
    expect(loop, '找不到 _log_retention_loop').toBeTruthy()
    expect(loop).toContain('await prune_expired_trash(')
    // 保留期常量必须由写手共享，两处硬编码 30 会各自漂移
    expect(pageApi).toContain('snapshot_to_trash(')
    expect(trashService).toContain('timedelta(days=TRASH_RETENTION_DAYS)')
  })

  it('删除文案不撒谎：可恢复的资源不许写成不可恢复', () => {
    expect(pagesAdmin).toContain('回收站')
    expect(pagesAdmin).not.toContain('此操作不可撤销，确定要删除这个页面吗')
    // 评论与留言板共用一个列表组件，删除语义却不同，文案必须按 isGuestbook 分叉
    expect(commentList).toContain('isGuestbook')
    expect(commentList).toContain('30 天内可恢复')
  })

  it('恢复评论前会确认原文章还在（外键无处可回时回 400 而不是 500）', () => {
    expect(restoreApi).toContain('原文章已不存在')
    expect(restoreApi).toContain('页面 slug 已被使用')
  })
})
