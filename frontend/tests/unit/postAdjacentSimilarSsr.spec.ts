/**
 * 批次 #132：文章详情页的「上一篇/下一篇」与「相关推荐」必须由 SSR 载荷给出。
 *
 * 这两块全是 <NuxtLink>，而它们此前只在 onMounted 里用 silentApiFetch 补取——
 * 于是爬虫在文章页（站内被链最多的页面类型）读不到任何一条「文章 → 文章」的链接，
 * 正文大的文章还叠一层「首屏空区块」。这里按源码断言钉住四段：
 * ① 取数只有一条路径，且上下篇/推荐与正文同进一条 useAsyncData 载荷；
 * ② 消费面是 computed（写在 renderToString 之后的 ref 赋值对 SSR HTML 不存在）；
 * ③ 客户端补取分支不得再用 refreshPost（历史上会 abort 仍在传输的 SSR 请求）；
 * ④ 语言是取数参数，换 locale 必须连载荷一起重取，否则装饰区块停在旧语言。
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

describe('文章页上下篇/相关推荐的 SSR 直出', () => {
  it('载荷类型把三块绑成一次取数', () => {
    expect(src).toMatch(/interface PostDetailPayload \{ detail: PostDetail, adjacent: AdjacentPair, similar: SimilarPostRow\[\]/)
    expect(src).toMatch(/const EMPTY_ADJACENT: AdjacentPair = \{ previous: null, next: null \}/)
  })

  it('取数函数内部并行拉上下篇与推荐，失败各自降级为空', () => {
    const body = fnBody('fetchPostPayload')
    expect(body).toMatch(/const \[adjacent, similar[^\]]*\] = await Promise\.all\(\[/)
    expect(body).toContain('fetchAdjacent(),')
    expect(body).toContain('fetchSimilarPosts(pid)')
    expect(body).toMatch(/return \{ detail, adjacent, similar/)
    // 没有 pid（详情还没出来 / 404）就不打推荐口
    expect(body).toMatch(/pid === undefined \|\| pid === null\s*\?\s*Promise\.resolve\(\[\] as SimilarPostRow\[\]\)/)
  })

  it('详情口只有一条请求路径（旧的第二份 $fetch 副本必须删净）', () => {
    expect(src.match(/\/blog\/posts\/\$\{postSlug\.value\}/g) ?? []).toHaveLength(1)
    expect(src).not.toContain('refreshPostWithStoredPassword')
  })

  it('useAsyncData 用的就是那个具名函数，返回的是载荷', () => {
    expect(src).toMatch(/useAsyncData<PostDetailPayload>\(\s*\n?\s*cacheKey,\s*\n?\s*fetchPostPayload,/)
  })

  it('载荷内的装饰请求走 setup 期抓好的 baseURL（handler 里用封装＝SSR 拿到空 base 静默降级）', () => {
    // 本仓未开 nitroAsyncContext：await 之后再 useRuntimeConfig() 取不到上下文，
    // 封装内部 baseURL 为空 → guardServerBase 抛 → catch 吞成空值 → HTML 里一个链接都没有。
    expect(src).toMatch(/async function payloadFetch<T>\(\s*\n *path: string,/)
    expect(src).toMatch(/const baseURL = import\.meta\.server \? runtimeConfig\.apiBase : runtimeConfig\.public\.apiBase\s*\n *return await \$fetch<T>\(path, \{ baseURL, \.\.\.opts \}\)/)
    expect(fnBody('fetchAdjacent')).toContain('payloadFetch')
    expect(fnBody('fetchSimilarPosts')).toContain('payloadFetch')
    expect(src).not.toMatch(/const raw = await silentApiFetch/)
  })

  it('消费面是 computed，不是「异步回调写 ref」', () => {
    expect(src).toContain('const adjacent = computed(() => postData.value?.adjacent ?? EMPTY_ADJACENT)')
    expect(src).toContain('const similarPosts = computed(() => postData.value?.similar ?? [])')
    expect(src).toContain('const post = computed(() => postData.value?.detail ?? null)')
    // 反向清点：整页不得再有任何往这两块写值的语句
    expect(src).not.toMatch(/similarPosts\.value\s*=\s*[^\n=]/)
    expect(src).not.toMatch(/adjacent\.value\s*=\s*[^\n=]/)
    expect(src).not.toMatch(/const similarPosts = ref/)
    expect(src).not.toMatch(/const adjacent = ref/)
  })

  it('客户端挂载只补收藏态，不再补取上下篇与推荐', () => {
    const body = fnBody('loadLikeAndFavoriteState')
    expect(body).not.toContain('fetchAdjacent')
    expect(body).not.toContain('fetchSimilarPosts')
    expect(body).toContain('await loadFavoriteState(pid)')
    expect(src).not.toContain('loadSimilarAndLikeState')
  })

  it('密码补取走同一个取数函数并直接写 data，不走 refreshPost', () => {
    const m = /if \(articleStoredPwd\.value && needPassword\.value\) \{([\s\S]*?)\n {2}\}/.exec(src)
    expect(m, 'onMounted 里的「本地存有旧密码」分支必须还在').not.toBeNull()
    expect(m![1]).toContain('void fetchPostPayload()')
    expect(m![1]).toContain('postData.value = payload')
    expect(m![1]).not.toContain('refreshPost()')
  })

  it('语言是取数参数：locale 变化必须连载荷一起重取', () => {
    expect(src).toMatch(/const postFetchLocaleStr = computed\(\(\) => locale\.value \|\| 'zh'\)/)
    expect(src).toMatch(/watch: \[postSlug, locale\]/)
    expect(src).toContain('query: { lang: postFetchLocaleStr.value }')
    expect(src).toMatch(/'Accept-Language': postFetchLocaleStr\.value/)
  })

  it('模板侧仍是真实链接：上下篇与推荐都走 localeHref 单源', () => {
    expect(src).toMatch(/v-if="adjacent\.previous \|\| adjacent\.next"/)
    expect(src).toContain(':to="localeHref(`/posts/${adjacent.previous.slug}`)"')
    expect(src).toContain(':to="localeHref(`/posts/${adjacent.next.slug}`)"')
    expect(src).toContain('v-if="showRelatedPosts && similarPosts.length"')
  })
})
