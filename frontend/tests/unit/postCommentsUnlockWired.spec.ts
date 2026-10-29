/**
 * 密码文章「解锁正文后评论区要跟着可见」的接线守卫。
 *
 * 缺陷形状是「闸门做对了，读侧却少带一张钥匙」：
 * `GET /api/blog/posts/{id}/comments` 与正文同闸门（`post_content_unlocked`），
 * 并明确接受 `password` 查询参数或 `X-Post-Password` 头；写侧（发表回复）也确实带了那个头。
 * 但**读侧一个都没带**——`fetchComments` 根本没有这个入参，文章详情页两处调用点自然也没传。
 * 线上实测：唯一一条 `visibility=password` 的真实文章，详情口回 `comments_count=6`、
 * 库里 6 条 approved+active，匿名评论口回 `[]`。于是访客输入正确密码解锁正文后，
 * 评论区仍然写着「暂无评论」，而他自己刚发的那条也看不见（发完重拉同样不带钥匙）。
 * 这不是"功能没做"，是"做了但只对没密码的文章生效"——表现和评论坏掉一模一样。
 *
 * 五条口径：
 * 1. 读口必须能把已存密码随 `X-Post-Password` 发出（与写口同一个头，不换形态）。
 * 2. 解锁成功那一刻必须重拉评论：否则正文出来了、线程还空着，读者判定的仍是"评论坏了"。
 * 3. 清掉密码也要重拉：状态往回走时旧读数属于另一个权限档，继续显示等于骗人。
 * 4. 未解锁时空列表**不得**渲染成「暂无评论」——那是"这里没人说话"，真话是"还没解锁"。
 * 5. 后端那条闸门是这套口径的单一真源，签名与判定不许被"顺手改松"。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')

function readSource(rel: string): string {
  return readFileSync(resolve(ROOT, rel), 'utf8').replace(/\r\n/g, '\n')
}

/** 判定只看守不守注释等于没判：解释性注释里会原样复述被禁形态 */
function stripComments(text: string): string {
  return text
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^[ \t]*\/\/.*$/gm, '')
}

const page = stripComments(readSource('pages/posts/[slug].vue'))
const composable = readSource('composables/useComments.ts')
const blogApi = readSource('../backend/api/blog.py')
const locales = ['zh', 'en', 'ja', 'zh_Hant'] as const

describe('密码文章评论区 · 解锁正文后线程必须跟着出来', () => {
  it('fetchComments 收第四个入参并按 X-Post-Password 发出（与写口同一种形态）', () => {
    const body = composable.slice(composable.indexOf('const fetchComments = async ('))
    const slice = body.slice(0, body.indexOf('\n  }'))
    expect(slice).toMatch(/postPassword\??: string \| null/)
    expect(slice).toMatch(/opts\.headers = \{ 'X-Post-Password': postPassword \}/)
    // 走 header 而不是 query：密码进 URL 会被 nginx access log 明文落盘
    expect(slice).not.toMatch(/query:[\s\S]{0,120}password: postPassword/)
  })

  it('详情页两处评论读取调用都把已存密码传下去（一处漏了就还是空线程）', () => {
    const calls = page.match(/fetchComments\(post\.value\.id, 1, 20, articleStoredPwd\.value\)/g) ?? []
    expect(calls.length).toBe(2)
    // 不允许残留"不带钥匙"的旧调用形态
    expect(page).not.toMatch(/fetchComments\(post\.value\.id\)/)
  })

  it('解锁成功那一刻重拉评论，失败回滚时不重拉', () => {
    const fn = page.slice(page.indexOf('async function submitArticlePassword()'))
    const body = fn.slice(0, fn.indexOf('\n}\n'))
    expect(body).toContain('await loadCommentsForCurrentPost()')
    // 重拉必须排在"密码错就 return"之后，否则错密码也要白跑一次请求
    expect(body.indexOf('articlePwdError.value = true')).toBeLessThan(
      body.indexOf('await loadCommentsForCurrentPost()')
    )
  })

  it('清掉已存密码同样重拉（旧线程属于另一个权限档）', () => {
    const fn = page.slice(page.indexOf('function clearSavedPassword()'))
    const body = fn.slice(0, fn.indexOf('\n}\n'))
    expect(body).toContain('void loadCommentsForCurrentPost()')
    expect(body).toMatch(/articleStoredPwd\.value = ''/)
  })

  it('未解锁的空列表说真话：不得渲染成「暂无评论」', () => {
    // 必须是 v-else-if 分支（只在"拉到空列表"时才轮到它），并真的把新文案渲染出来
    expect(page).toMatch(/v-else-if="needPassword"[\s\S]{0,260}commentsLockedHint/)
    const errorAt = page.indexOf('v-else-if="commentsError"')
    const emptyAt = page.indexOf('post.noComments')
    const lockedAt = page.indexOf('post.commentsLockedHint')
    expect(lockedAt).toBeGreaterThan(-1)
    // 顺序：加载失败要盖过"还没解锁"，而"暂无评论"只能在解锁之后那条分支里
    expect(errorAt).toBeLessThan(lockedAt)
    expect(lockedAt).toBeLessThan(emptyAt)
  })

  it('新文案四语齐备（缺一种语言就渲染裸 key）', () => {
    for (const code of locales) {
      const raw = readSource(`i18n/locales/${code}.json`)
      const dict = JSON.parse(raw) as Record<string, unknown>
      const post = dict.post as Record<string, unknown> | undefined
      expect(post, `${code} 没有 post 段`).toBeTruthy()
      expect(post?.commentsLockedHint, `${code} 缺 post.commentsLockedHint`)
        .toBeTypeOf('string')
    }
  })

  it('后端闸门仍是单一真源：读口收头、不带钥匙就回空列表', () => {
    const detail = blogApi.slice(blogApi.indexOf('async def list_comments('))
    const slice = detail.slice(0, detail.indexOf('\n    # 1)'))
    expect(slice).toMatch(/alias="X-Post-Password"/)
    expect(slice).toContain('if not await post_content_unlocked(post, current_user, x_post_password or password)')
    expect(slice).toContain('return []')
  })
})
