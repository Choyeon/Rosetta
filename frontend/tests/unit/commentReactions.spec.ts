/**
 * 评论表情反应（/api/comments/{id}/reactions 三条口）落地契约（静态源码断言）。
 *
 * 这一族后端早已就绪但前端零消费（见 frontend/docs/API_COVERAGE.md）。接进 CommentItem
 * 时最容易写错、且写错只会以"点了没反应 / 405 / 面板永远空"的形式暴露的四条：
 * 1. 统计口是 per-comment 的 GET，后端没有批量口 → 必须懒加载（点开面板才拉），
 *    且不能再用 setup 顶层的 useAPI 形态（AsyncData 口在回调里拿不到上下文）；
 * 2. 取消口的 emoji 在**路径**上（DELETE /comments/{id}/reactions/{emoji}），
 *    放 body 会命中集合路径的 405，表现为"点亮了取消不掉"；
 * 3. reacted 是私有态：SSR 首帧不得出现，计数一律以 GET 为真源、本地不自增；
 * 4. 本页可能出现在 SSR 页里，图标必须取 SSR-safe 的 lucide-svg-icons，不得 import @lucide/vue。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const read = (p: string) => readFileSync(resolve(ROOT, p), 'utf-8')

const comments = read('composables/useComments.ts')
const item = read('components/CommentItem.vue')

describe('useComments 的反应族封装', () => {
  it('统计口走 apiFetch 且按单条评论取（不再有 setup 层的 getCommentReactions）', () => {
    expect(comments).toContain('apiFetch<CommentReactionSummaryList>(`/comments/${id}/reactions`)')
    expect(comments).not.toContain('getCommentReactions')
  })

  it('取消把 emoji 放进路径并转义，添加放 body', () => {
    expect(comments).toContain('`/comments/${id}/reactions/${encodeURIComponent(emoji)}`')
    expect(comments).toContain('`/comments/${id}/reactions`, {\n      method: \'POST\'')
  })

  it('响应类型与后端 CommentReactionSummaryList 字段同名', () => {
    expect(comments).toContain('reactions: CommentReactionSummary[]')
    expect(comments).toContain('reacted: boolean')
  })
})

describe('CommentItem 的反应条', () => {
  it('只在第一次点开面板时拉统计（逐条预取就是 N+1）', () => {
    expect(item).toContain('if (!reactionPanel.value || reactionLoaded.value || reactionBusy.value) return')
    expect(item).toContain('await reloadReactions()')
    expect(item).not.toMatch(/\$fetch\(/)
  })

  it('toggle 以 reacted 决定动词，之后以重拉为准', () => {
    expect(item).toContain('if (hit?.reacted) await removeCommentReaction(props.comment.id, emoji)')
    expect(item).toContain('else await addCommentReaction(props.comment.id, emoji)')
  })

  it('私有态初值为空数组：SSR 首字节不出现别人的 reacted 状态', () => {
    expect(item).toContain('const reactions = ref<CommentReactionSummary[]>([])')
  })

  it('图标取 SSR-safe shim', () => {
    expect(item).toMatch(/import \{[^}]*Smile[^}]*\} from '~~\/lib\/lucide-svg-icons'/)
    expect(item).not.toContain('@lucide/vue')
  })
})
