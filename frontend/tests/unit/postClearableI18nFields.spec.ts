/**
 * 文章「可清空 i18n 字段」的提交口径契约（批次 #33）。
 *
 * `excerpt` / `meta_title` / `meta_description` / `meta_keywords` 与 #30 的副标题是同一个
 * bug 类：`toI18nPayload()` 对全空 dict 返回 `undefined`，键就不在 PUT 体里，而后端
 * `model_dump(exclude_unset=True)` 的增量语义是"键没出现 = 不动它"。表现是作者删掉摘要
 * 或 SEO 标题、保存提示成功、再打开还是旧值，前台 RSS / og:description 也继续用旧摘要。
 *
 * 唯一的修法是把"清空"这件事写进请求体（显式 null），所以这里钉的是四个提交点 +
 * 后台类型声明；读侧回填必须走 normalizeI18nDict（清空后库里是 JSON null，
 * 不接住 null 会让 v-model 在下次编辑时崩）。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const form = readFileSync(resolve(process.cwd(), 'components/admin/PostForm.vue'), 'utf8')
const apiTypes = readFileSync(resolve(process.cwd(), 'types/api.ts'), 'utf8')

/** buildPayload 的切片：只认这里产出的键，别把模板里的示例文本算成发送。 */
const payload = form.slice(form.indexOf('const buildPayload'), form.indexOf('const validateBase'))

const CLEARABLE = ['excerpt', 'meta_title', 'meta_description', 'meta_keywords'] as const

describe('可清空 i18n 字段：编辑器写侧', () => {
  it.each(CLEARABLE)('%s 的载荷始终发送，空表单发 null 而不是省略键', (field) => {
    const re = new RegExp(`${field}[:\\s]=?\\s*toI18nPayload\\(form\\.${field}\\) \\?\\? null`)
    expect(payload).toMatch(re)
  })

  it.each(CLEARABLE)('%s 四个字段都在表单状态里（四语 dict，与标题同形）', (field) => {
    expect(form).toMatch(new RegExp(`${field}: \\{ \\.\\.\\.EMPTY_I18N_DICT \\} as Record<string, string>`))
  })

  it.each(CLEARABLE)('%s 回填走 normalizeI18nDict：清空后库里是 JSON null，必须接住', (field) => {
    expect(form).toMatch(new RegExp(`form\\.${field} = normalizeI18nDict\\(data\\.${field}\\)`))
    expect(form).toMatch(new RegExp(`form\\.${field} = normalizeI18nDict\\(form\\.${field}\\)`))
  })

  it.each(CLEARABLE)('%s 的写侧类型允许 null，否则"清空"这个操作在类型层面写不出来', (field) => {
    const create = apiTypes.slice(apiTypes.indexOf('export interface PostCreate'))
    expect(create).toMatch(
      new RegExp(`${field}\\?: string \\| Record<string, string> \\| null`)
    )
  })
})

describe('可清空 i18n 字段：前台消费侧', () => {
  it('读侧 Post 类型也允许 null（清空后库里落的就是 JSON null）', () => {
    const readFace = apiTypes.slice(
      apiTypes.indexOf('export interface Post {'),
      apiTypes.indexOf('export interface PostCreate')
    )
    expect(readFace).toMatch(/excerpt\?: string \| Record<string, string> \| null/)
  })

  it('卡片摘要 prop 允许 null，不能靠收窄类型来消掉 typecheck 报错', () => {
    const card = readFileSync(resolve(process.cwd(), 'components/PostCard.vue'), 'utf8')
    expect(card).toMatch(/excerpt\?: string \| Record<string, string> \| null/)
  })
})
