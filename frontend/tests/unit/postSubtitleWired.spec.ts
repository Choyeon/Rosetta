/**
 * 文章「副标题」读写两端契约（批次 #30）。
 *
 * `Post.subtitle` 长期是"库里能写、接口能读，前端两头都不接"：列在 ``Post`` 上、
 * ``PostBase``/``PostUpdate`` 都收这个键、四个读口（详情 / 列表项 / 相似 / 热榜）连同
 * ``/edit`` 都回显，导入导出还会搬运它——但编辑器表单从不发送、文章页从不渲染。
 * 于是作者在后台无处可填，读者永远看不到导语。本 spec 钉住接通之后不许重新断链：
 *
 * 1. 表单状态必须有 subtitle 这一项，且从 ``/edit`` 回填时走 normalizeI18nDict
 *    （后端这里给的是完整四语 dict；不归一化时旧草稿里的裸字符串会让 v-model 崩）；
 * 2. 载荷必须**始终**发送 subtitle，全空时发 null——后端 PUT 是 exclude_unset 增量语义，
 *    省略键等于"不改它"，删掉副标题再保存会立刻回到旧值；
 * 3. 后台的类型声明必须允许 null，否则"清空"这个操作在类型层面就写不出来；
 * 4. 文章页必须真的渲染它，且回落口径是"空则不出现"：详情口按当前语言下发字符串，
 *    没人读就等于这一列仍是死的。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const form = readFileSync(resolve(process.cwd(), 'components/admin/PostForm.vue'), 'utf8')
const postPage = readFileSync(resolve(process.cwd(), 'pages/posts/[slug].vue'), 'utf8')
const apiTypes = readFileSync(resolve(process.cwd(), 'types/api.ts'), 'utf8')

/** buildPayload 的切片：只认这里产出的键，别把模板里的示例文本算成发送。 */
const payload = form.slice(form.indexOf('const buildPayload'), form.indexOf('const validateBase'))

describe('文章副标题：编辑器写侧', () => {
  it('表单状态里有 subtitle 这一项（四语 dict，与标题同形）', () => {
    expect(form).toMatch(/subtitle: \{ \.\.\.EMPTY_I18N_DICT \} as Record<string, string>/)
  })

  it('回填走 normalizeI18nDict：/edit 给的是完整 dict，裸字符串脏值也要接住', () => {
    expect(form).toMatch(/form\.subtitle = normalizeI18nDict\(data\.subtitle\)/)
    expect(form).toMatch(/form\.subtitle = normalizeI18nDict\(form\.subtitle\)/)
  })

  it('载荷始终发送 subtitle，空表单发 null 而不是省略键', () => {
    expect(payload).toMatch(/subtitle: toI18nPayload\(form\.subtitle\) \?\? null,/)
  })

  it('标题下方有副标题输入控件（语言切换器与标题共用一套）', () => {
    expect(form).toMatch(/v-model="form\.subtitle"/)
    expect(form).toMatch(/label="副标题"/)
  })

  it('后台类型允许 null，否则"清空副标题"写不出来', () => {
    expect(apiTypes).toMatch(/subtitle\?: string \| Record<string, string> \| null/)
  })
})

describe('文章副标题：前台读侧', () => {
  it('详情类型声明了 subtitle', () => {
    expect(postPage).toMatch(/subtitle\?: unknown/)
  })

  it('有派生值且与主标题相同时判空（导入工具会把副标题复制成标题）', () => {
    expect(postPage).toMatch(/const postSubtitle = computed/)
    expect(postPage).toMatch(/pickLocalized\(post\.value\?\.subtitle\)/)
    expect(postPage).toMatch(/sub === postTitle\.value/)
  })

  it('副标题真的渲染在文章页上，且空值不产出节点', () => {
    expect(postPage).toMatch(/v-if="postSubtitle"/)
    expect(postPage).toMatch(/\{\{ postSubtitle \}\}/)
  })

  it('渲染落点在 h1 之后（导语在主标题下，不是跑到正文末尾）', () => {
    expect(postPage.indexOf('</h1>')).toBeLessThan(postPage.indexOf('v-if="postSubtitle"'))
    expect(postPage.indexOf('v-if="postSubtitle"')).toBeLessThan(postPage.indexOf('postSubtitle }}'))
  })
})
