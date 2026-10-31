/**
 * 批次 #133：文章页评论线程必须由 SSR 载荷给出。
 *
 * 评论此前只在 onMounted 里取，而它是文章页最后一块「正文之外、爬虫读不到」的公开内容——
 * 评论正文本身就是可索引文本，且评论数（`评论 (N)`）在首屏是 0。这里按源码断言钉住：
 * ① 评论首页与正文/上下篇/推荐同进一条 useAsyncData 载荷；
 * ② 消费面是 visibleComments 计算属性（写在 renderToString 之后的 ref 赋值对 SSR HTML 不存在）；
 * ③ 载荷与客户端补取共用同一个 COMMENT_PAGE_SIZE，否则「首屏 20 条、刷新变 10 条」；
 * ④ 密码文章的密码只在客户端带（SSR 读不到 sessionStorage），闸门页不得烘出评论正文；
 * ⑤ 本地删除/回复名也读 visibleComments——直接 filter(comments) 会在载荷态把整列表清成空白。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const src = readFileSync(resolve(ROOT, 'pages/posts/[slug].vue'), 'utf-8').replace(/\r\n/g, '\n')

function fnBody(name: string): string {
  const m = new RegExp(`async function ${name}\\([\\s\\S]*?\\n\\}`).exec(src)
  expect(m, `找不到函数体：${name}`).not.toBeNull()
  return m![0]
}

function arrowBody(name: string): string {
  const m = new RegExp(`const ${name} = async \\(\\) => \\{[\\s\\S]*?\\n\\}`).exec(src)
  expect(m, `找不到箭头函数体：${name}`).not.toBeNull()
  return m![0]
}

describe('文章页评论线程的 SSR 直出', () => {
  it('载荷类型把评论绑进同一次取数', () => {
    expect(src).toMatch(/interface PostDetailPayload \{ detail: PostDetail, adjacent: AdjacentPair, similar: SimilarPostRow\[\], comments: CommentRaw\[\], polls: Poll\[\] \}/)
    expect(src).toMatch(/const EMPTY_COMMENT_ROWS: CommentRaw\[\] = \[\]/)
    expect(src).toMatch(/const COMMENT_PAGE_SIZE = \d+/)
  })

  it('评论首页与上下篇/推荐同进一条 Promise.all，失败各自降级为空', () => {
    const body = fnBody('fetchPostPayload')
    expect(body).toMatch(/const \[adjacent, similar, commentRows, polls\] = await Promise\.all\(\[/)
    expect(body).toContain('fetchCommentRows(pid)')
    expect(body).toMatch(/return \{ detail, adjacent, similar, comments: commentRows, polls \}/)
    // 没有 pid（详情还没出来 / 404）就不打评论口
    expect(body).toMatch(/pid === undefined \|\| pid === null\s*\?\s*Promise\.resolve\(EMPTY_COMMENT_ROWS\)/)
  })

  it('评论请求与客户端补取同形（裸数组口 + 同一组分页参数），非数组一律当空', () => {
    const body = fnBody('fetchCommentRows')
    expect(body).toContain('`/blog/posts/${pid}/comments`,')
    expect(body).toMatch(/query: \{ page: 1, page_size: COMMENT_PAGE_SIZE, lang: postFetchLocaleStr\.value \}/)
    expect(body).toMatch(/return Array\.isArray\(raw\) \? raw : EMPTY_COMMENT_ROWS/)
    expect(body).toMatch(/catch \{\s*return EMPTY_COMMENT_ROWS/)
  })

  it('密码只在客户端随评论请求带上（SSR 期没有 sessionStorage）', () => {
    const body = fnBody('fetchCommentRows')
    expect(body).toMatch(/articleStoredPwd\.value && !import\.meta\.server/)
    expect(body).toMatch(/headers\['X-Post-Password'\] = articleStoredPwd\.value/)
  })

  it('评论首页与正文用同一个取数口（handler 里的封装会拿到空 baseURL）', () => {
    const body = fnBody('fetchCommentRows')
    expect(body).toContain('await payloadFetch<CommentRaw[]>(')
    expect(body).not.toContain('silentApiFetch')
  })

  it('消费面是计算属性，模板不得再直接 v-for 那个 ref', () => {
    expect(src).toMatch(/const payloadComments = computed<PostComment\[\]>\(\(\) =>\s*\(postData\.value\?\.comments \?\? EMPTY_COMMENT_ROWS\)\.map\(normalizeComment\)/)
    expect(src).toMatch(/const visibleComments = computed<PostComment\[\]>\(\(\) =>\s*commentsFromClient\.value \? comments\.value : payloadComments\.value/)
    expect(src).toContain('v-for="comment in visibleComments"')
    expect(src).not.toMatch(/v-for="comment in comments"/)
    expect(src).toContain('{{ visibleComments.length }}')
  })

  it('客户端补取只有一个写入口，且分页大小与载荷同源', () => {
    const body = arrowBody('loadCommentsForCurrentPost')
    expect(body).toContain('COMMENT_PAGE_SIZE')
    expect(body).toMatch(/applyClientComments\(\(commentsAPI\.comments\?\.value \|\| \[\]\) as unknown as CommentRaw\[\]\)/)
    // 载荷态（commentsFromClient=false）时 comments ref 是空的，直接 filter 它会清空整列表
    expect(src).toMatch(/const applyClientComments = \(rows: CommentRaw\[\]\) => \{\s*comments\.value = rows\.map\(normalizeComment\)\s*commentsFromClient\.value = true/)
    expect(src).toMatch(/comments\.value = visibleComments\.value\.filter/)
    expect(src).toMatch(/const target = visibleComments\.value\.find/)
  })
})
