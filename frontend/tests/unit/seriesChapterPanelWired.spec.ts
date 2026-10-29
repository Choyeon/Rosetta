/**
 * 后台系列页「系列内文章排序」面板的接线守卫。
 *
 * 缺陷形状不是"功能没做"，而是"做了却宣称没做"：章节顺序早就全链路通了 ——
 * `Post.series_order`（models/blog.py）→ `GET /api/series/{slug}` 的
 * `ORDER BY series_order ASC, published_at DESC`（api/post_series.py）→
 * 前台 `pages/series/[slug].vue` 按返回顺序渲染，文章编辑表单里也有「序号」输入。
 * 但后台面板写的是「（待后端 /series/{id}/posts 接口上线后启用）」+「排序接口待提供」，
 * 于是运营读到的是"这里看不到顺序"，实际那个口一直摆在那儿、前台正在用它。
 * 假道歉与假承诺一样会误导人，而且它把唯一能核对"读者实际看到第几篇"的入口关掉了。
 *
 * 五条口径钉在这里：
 * 1. 面板必须真去读那个口，并且**按返回顺序渲染**——前端再排一次等于两处口径，改一处即分叉。
 * 1b. 展开入口必须把**整行对象**传给处理函数：入参从 id 换成对象后漏改调用点，面板会对每个系列
 *     都显示「已停用」（`s.is_active` 是 undefined），而接口一次都没被请求。
 * 2. 停用系列不能发请求：`GET /api/series/{slug}` 对 `is_active=false` 回 404，
 *    拿 apiFetch 打它会弹一条红色 toast，把"这条没在前台展示"报成故障。
 * 3. 后台卡片的 `posts_count` 来自 `GET /admin/series`，它数的是全部文章（含草稿、
 *    定时未到、私密）；章节口只回匿名可读的那些。两个数可以不相等，面板必须把差值说出来，
 *    否则"系列里 5 篇、前台 3 篇"看起来像 bug。
 * 4. 连点两张卡片时先发的请求会后回，必须作废过期响应，否则 A 系列的顺序显示在 B 卡片下。
 * 5. 章节口的形状（裸 dict、`posts` 数组、无信封）不能被"顺手包一层 data"改掉。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')

// 仓库混用 CRLF 与 LF：多行标记必须先归一，否则 indexOf 永远找不到
function readSource(rel: string): string {
  return readFileSync(resolve(ROOT, rel), 'utf8').replace(/\r\n/g, '\n')
}

/** 面板的解释性注释里会复述旧文案，判定只看守不守注释就等于没判（同 adminNoDeadAffordance 的口径） */
function stripComments(text: string): string {
  return text
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^[ \t]*\/\/.*$/gm, '')
}

const panel = readSource('pages/admin/content/series.vue')
const panelCode = stripComments(panel)
const composable = readSource('composables/useAdminManage.ts')
const publicPage = readSource('pages/series/[slug].vue')
const seriesApi = readSource('../backend/api/post_series.py')

describe('系列章节顺序面板 · 后台读到的是前台那一份顺序', () => {
  it('假道歉已经清掉（活代码里不得再有「接口待提供 / 待后端 / 上线后启用」）', () => {
    for (const phrase of ['接口待提供', '待后端', '上线后启用', '排序接口']) {
      expect(panelCode, `面板里仍留着「${phrase}」`).not.toContain(phrase)
    }
  })

  it('展开即调 fetchSeriesChapters(slug)，并且只调一次（数据源唯一）', () => {
    expect(panelCode).toContain('fetchSeriesChapters(s.slug)')
    expect(panelCode).toMatch(/fetchSeriesChapters,[\s\S]{0,60}type SeriesChapterRow[\s\S]{0,40}from '~~\/composables\/useAdminManage'/)
    expect(composable).toContain('export async function fetchSeriesChapters')
  })

  it('模板传给 AdminSeries 处理函数的是整行对象，不是 id', () => {
    // #41 把 toggleExpand 的入参从 id 改成整行对象（要读 is_active 与 slug），模板两处调用点没跟着改。
    // 类型上是 TS2345（生产门禁 06-typecheck 抓到）；运行时表现更难看：`s.is_active` 恒为 undefined，
    // loadChapters 直接走 inactive 分支——运营点开**任何**系列都看到「系列已停用」，章节一次都不请求。
    const declared = [
      ...[...panelCode.matchAll(/function (\w+)[^\n]*?\(s: AdminSeries\)/g)].map(m => m[1]),
      ...[...panelCode.matchAll(/const (\w+) = \(s: AdminSeries\)/g)].map(m => m[1])
    ]
    const handlers = [...new Set(declared)]
    // 下限 4：签名整体改名/换成 id 时这条守卫会空转，必须先证明它真的收到了保护对象
    expect(handlers.length).toBeGreaterThanOrEqual(4)
    for (const fn of handlers) {
      expect(panelCode, `${fn} 被传了 s.id`).not.toMatch(new RegExp(`${fn}\\(s\\.id\\)`))
    }
    // 两个展开入口（封面块与标题）都必须接上
    expect(panelCode.match(/@click="toggleExpand\(s\)"/g)?.length).toBe(2)
  })

  it('按接口返回顺序渲染，前端不再排序（两处排序=两处口径）', () => {
    expect(panelCode).toMatch(/v-for="\(c, idx\) in chapters"/)
    expect(panelCode).not.toMatch(/chapters\.value\s*=?\s*.*?(toSorted|\.sort\()/)
    expect(panelCode).not.toMatch(/chapters\b[^\n]*\.(toSorted|sort)\(/)
    // 前台同一份顺序：它也不排，两边必须同构
    expect(publicPage).toMatch(/v-for="\(p, idx\) in postsList"/)
    expect(publicPage).not.toMatch(/postsList[\s\S]{0,60}\.(toSorted|sort)\(/)
  })

  it('停用（或缺 slug）时不发请求，并明确说明前台不展示', () => {
    expect(panelCode).toMatch(/if \(!s\.is_active \|\| !s\.slug\)/)
    expect(panelCode).toContain('chaptersState.value = \'inactive\'')
    expect(panelCode).toContain('系列已停用')
  })

  it('读失败与"全部不可读"分开说：404 之外的失败不能伪装成空系列', () => {
    expect(panelCode).toContain('chaptersState.value = \'error\'')
    expect(panelCode).toContain('章节读取失败')
    // posts_count>0 而章节为空 ⇒ 草稿/定时未到/私密，这条诊断必须写出来
    expect(panelCode).toContain('s.posts_count > 0')
    expect(panelCode).toMatch(/草稿.*定时未到.*私密/)
  })

  it('后台计数与前台可读数的差值必须显示（两者口径不同不是 bug）', () => {
    expect(panelCode).toMatch(/s\.posts_count > chapters\.length/)
    expect(panelCode).toMatch(/未对外展示/)
  })

  it('过期响应要作废：每次展开/收起都推进序号，回来的比对不上就丢弃', () => {
    expect(panelCode).toMatch(/const seq = \+\+chaptersSeq/)
    expect(panelCode).toMatch(/if \(seq !== chaptersSeq\) return/)
  })

  it('改完系列或翻了启停要重读展开中的章节（旧读数属于另一个形状）', () => {
    // 逐个调用点数：只断言"这两个相邻调用存在过"会被另一处满足，等于没守住 save
    expect(panelCode.match(/await loadData\(\)\n[ \t]*await reloadExpandedChapters\(\)/g)?.length)
      .toBe(2)
    // 删除展开中那张卡片时连同状态一起收回
    expect(panelCode).toMatch(/if \(expandedId\.value === id\) \{[\s\S]{0,120}chaptersSeq\+\+/)
  })

  it('章节口是裸 dict：取 posts，不得再剥一层 data 信封', () => {
    const body = composable.slice(composable.indexOf('export async function fetchSeriesChapters'))
    const slice = body.slice(0, body.indexOf('\n}\n'))
    expect(slice).toContain('silentApiFetch')
    expect(slice).toContain('`/series/${encodeURIComponent(slug)}`')
    expect(slice).toContain('raw.posts')
    expect(slice).not.toContain('.data')
    // silent 版失败回 null，面板据此判"读取失败"
    expect(slice).toContain('if (!raw) return null')
  })

  it('后端 ORDER BY 仍是这一契约的单一真源（series_order 升序 + 发布时间倒序兜底）', () => {
    expect(seriesApi).toMatch(/\.order_by\(Post\.series_order\.asc\(\), Post\.published_at\.desc\(\)\)/)
    // 章节查询走集合口谓词，草稿/定时未到/私密不会混进"读者看到的顺序"
    const detail = seriesApi.slice(seriesApi.indexOf('async def get_series('))
    const slice = detail.slice(0, detail.indexOf('\n    return {'))
    expect(slice).toContain('publicly_listable_posts()')
    expect(slice).toContain('Post.series_id == series.id')
    // 停用即 404：面板据此省掉请求
    expect(detail).toContain('not series.is_active')
  })

  it('面板给运营留了动手的去处（改序号 → 文章编辑页，前台查看 → 真实文章 URL）', () => {
    expect(panelCode).toContain('`/admin/content/posts/${c.id}/edit`')
    expect(panelCode).toContain('`/posts/${c.slug}`')
    // 后台是 SPA 无索引面，但新标签打开前台页仍要带 rel，防 window.opener 反向操控
    expect(panelCode).toContain('rel="noopener"')
  })
})
