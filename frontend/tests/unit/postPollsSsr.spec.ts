/**
 * 批次 #134：文章页的投票卡片必须由 SSR 载荷给出。
 *
 * 投票是文章页最后一块「只由 onMounted 补取」的公开内容：改之前爬虫看到的 HTML 里
 * 一个投票问题、一个选项都没有。这里按源码断言钉住六件事：
 * ① polls 与正文/上下篇/推荐/评论同进一条 useAsyncData 载荷；
 * ② 取数口是 payloadFetch（handler 里用封装会拿空 baseURL，见 postAdjacentSimilarSsr.spec.ts）；
 * ③ 参数与 usePolls.fetchActivePolls 同形，条数走同一个 POLL_CARD_LIMIT，两端切的是同一段；
 * ④ 密码闸门未解锁时不取——SSR 带不上 sessionStorage 里的密码，专属内容不能先烘进闸门页；
 * ⑤ 消费面是 visiblePolls 计算属性，客户端补取的写入口只有 setClientPolls 一个；
 * ⑥ PollCard 的「已投票」态改到 onMounted 同步：卡片进了 SSR HTML 之后，
 *    setup 期直接读 localStorage 会让已投票访客必出 hydration mismatch。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const src = readFileSync(resolve(ROOT, 'pages/posts/[slug].vue'), 'utf-8').replace(/\r\n/g, '\n')
const card = readFileSync(resolve(ROOT, 'components/PollCard.vue'), 'utf-8').replace(/\r\n/g, '\n')

function fnBody(name: string): string {
  const m = new RegExp(`async function ${name}\\([\\s\\S]*?\\n\\}`).exec(src)
  expect(m, `找不到函数体：${name}`).not.toBeNull()
  return m![0]
}

describe('文章页投票卡片的 SSR 直出', () => {
  it('投票绑进同一条载荷，空值与条数有单源', () => {
    expect(src).toMatch(/polls: Poll\[\] \}/)
    expect(src).toMatch(/const EMPTY_POLL_ROWS: Poll\[\] = \[\]/)
    expect(src).toMatch(/const POLL_CARD_LIMIT = \d+/)
    expect(src).toMatch(/const pollsFromClient = ref\(false\)/)
  })

  it('投票请求与客户端补取同形（分页字段在顶层 + 同一组参数），非数组一律当空', () => {
    const body = fnBody('fetchPollRows')
    expect(body).toMatch(/'\/voting\/polls',/)
    expect(body).toMatch(/is_active: 'true',/)
    expect(body).toMatch(/page_size: String\(POLL_CARD_LIMIT\),/)
    // post_id 必带：不传就退化成「全站投票」，别篇文章的专属投票会串到本页
    expect(body).toMatch(/\.\.\.\(pid === null \|\| pid === undefined \?\s*\{\} : \{ post_id: String\(pid\) \}\)/)
    expect(body).toMatch(/return Array\.isArray\(items\) \? items : EMPTY_POLL_ROWS/)
    expect(body).toMatch(/catch \{\s*return EMPTY_POLL_ROWS/)
  })

  it('载荷内的投票走 setup 期抓好的 baseURL，不用会拿空 base 的封装', () => {
    const body = fnBody('fetchPollRows')
    expect(body).toContain('await payloadFetch<{ items?: Poll[] }>(')
    expect(body).not.toContain('silentApiFetch')
    expect(body).not.toContain('apiFetch')
  })

  it('密码闸门未解锁时载荷里不取投票', () => {
    const body = fnBody('fetchPostPayload')
    expect(body).toMatch(/Boolean\(\s*\(detail as unknown as \{ is_password_protected\?: boolean \} \| null\)\?\.is_password_protected/)
    expect(body).toMatch(/\) && !String\(\s*\(detail as unknown as \{ content\?: unknown \} \| null\)\?\.content \?\? ''\)/)
    expect(body).toMatch(/gateLocked \|\| pid === undefined \|\| pid === null\s*\?\s*Promise\.resolve\(EMPTY_POLL_ROWS\)\s*: fetchPollRows\(pid\)/)
    expect(body).toMatch(/return \{ detail, adjacent, similar, comments: commentRows, polls \}/)
  })

  it('消费面是计算属性，模板不得再直接 v-for 那个 ref', () => {
    expect(src).toMatch(/const payloadPolls = computed<Poll\[\]>\(\(\) => postData\.value\?\.polls \?\? EMPTY_POLL_ROWS\)/)
    expect(src).toMatch(/const visiblePolls = computed<Poll\[\]>\(\(\) =>\s*pollsFromClient\.value \? activePolls\.value : payloadPolls\.value/)
    expect(src).toContain('v-for="poll in visiblePolls"')
    expect(src).not.toMatch(/v-for="poll in activePolls"/)
  })

  it('客户端补取只有一个写入口，条数与载荷同源', () => {
    expect(src).toMatch(/function setClientPolls\(rows: Poll\[\]\) \{\s*activePolls\.value = rows\s*pollsFromClient\.value = true/)
    // 除写入口本身之外，任何地方都不许再直接赋值 activePolls（那会绕过 pollsFromClient 标记）
    const assignments = src.match(/activePolls\.value = /g) ?? []
    expect(assignments, 'activePolls.value 只允许在 setClientPolls 里被赋值').toHaveLength(1)
    expect(src).toMatch(/pollsPromise\) setClientPolls\(await pollsPromise\)/)
    expect(src).not.toMatch(/fetchActivePolls\(3,/)
    expect((src.match(/fetchActivePolls\(POLL_CARD_LIMIT/g) ?? []).length).toBe(3)
  })

  it('PollCard 的已投票态在挂载后同步，首渲染两端一致', () => {
    expect(card).toMatch(/const alreadyVoted = ref\(false\)/)
    expect(card).toMatch(/onMounted\(\(\) => \{\s*alreadyVoted\.value = readVotedPollIds\(\)\.has\(props\.poll\.id\)/)
    expect(card).not.toMatch(/const alreadyVoted = ref\(readVotedPollIds\(\)/)
    expect(card).toMatch(/import \{ computed, onMounted, ref, watch \} from 'vue'/)
  })
})
