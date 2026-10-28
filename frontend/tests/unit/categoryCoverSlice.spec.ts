/**
 * 分类封面图（Category.cover_image）读写两端的接线契约。
 *
 * 表现过的形状是"列与读口都在、写口缺半"：`CategoryResponse` 一直带这个键，
 * `CategoryBase` 却没有它 —— 于是 `POST /blog/categories` 根本不收封面，
 * 后台分类弹窗里也没有任何写入控件，"分类封面"只能靠手工改库。
 * 后端那半由 `tests/test_category_cover_roundtrip.py` 钉（创建可定、PUT 可改可清、
 * 超长拒 422 而不是静默截断/500），这里钉前端这半：
 *
 * 1. 后台表单必须**回填**并**始终发送**这个键：不回填则"改一次名字"就把封面抹掉，
 *    发送空串而不是省略键才真的是"清掉封面"（PUT 是 exclude_unset 增量语义）。
 * 2. 前台分类页必须消费它，并且"没有封面"与"封面坏了"都整块不出现——
 *    留一个 `src=""` 或破图框等于把首屏最贵的位置换成一处坏图。
 * 3. 标签页没有 cover_image 这一列，不能把它塞进标签请求（后端 extra=forbid 会 422）。
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const categoriesPage = readFileSync(resolve(process.cwd(), 'pages/admin/content/categories.vue'), 'utf8')
const publicCategoryPage = readFileSync(resolve(process.cwd(), 'pages/categories/[slug].vue'), 'utf8')
const tagsPage = readFileSync(resolve(process.cwd(), 'pages/admin/content/tags.vue'), 'utf8')
const manageSrc = readFileSync(resolve(process.cwd(), 'composables/useAdminManage.ts'), 'utf8')

describe('后台分类表单的封面写入', () => {
  it('走的是"上传拿站内 URL"，不给自由文本输入框', () => {
    expect(categoriesPage).toContain('import { useMediaUploadCover } from \'~~/composables/useMedia\'')
    expect(categoriesPage).toContain('await useMediaUploadCover(file)')
    expect(categoriesPage).toContain('type="file"')
    // 自由文本会成为访客页面 <img src> 的一部分，不是一个可输入的口子
    expect(categoriesPage).not.toContain('v-model="form.cover_image"')
  })

  it('表单状态有封面项，且有图标（缺失态）与上传中态', () => {
    expect(categoriesPage).toContain('cover_image: ')
    expect(categoriesPage).toContain('const coverUploading = ref(false)')
    expect(categoriesPage).toContain('const coverInputRef = ref<HTMLInputElement | null>(null)')
    expect(categoriesPage).toContain('ImageIcon')
  })

  it('编辑必须回填、重置必须清空（否则改名会顺手抹掉封面）', () => {
    expect(categoriesPage).toContain('form.cover_image = cat.cover_image || \'\'')
    expect(categoriesPage).toContain('form.cover_image = \'\'')
  })

  it('提交始终带这个键，清除靠空值而不是省略键', () => {
    expect(categoriesPage).toContain('cover_image: form.cover_image')
    expect(manageSrc).toContain('if (payload.cover_image !== undefined) body.cover_image = payload.cover_image || null')
  })

  it('列表行显示缩略图，站主改完当场能看见', () => {
    expect(categoriesPage).toContain('data-testid="category-row-cover"')
    expect(categoriesPage).toContain('v-if="(row as AdminCategory).cover_image"')
  })
})

describe('前台分类页消费封面', () => {
  it('空值与坏图都整块撤掉，不留空框', () => {
    expect(publicCategoryPage).toContain('v-if="catCover && !coverBroken"')
    expect(publicCategoryPage).toContain('@error="coverBroken = true"')
    expect(publicCategoryPage).toContain('data-testid="category-cover"')
  })

  it('只有非空字符串算有封面（库里躺着空串也不能变成 src="" 的请求）', () => {
    expect(publicCategoryPage).toContain('return typeof raw === \'string\' ? raw.trim() : \'\'')
  })

  it('首屏横幅图不挂 lazy（它在折叠线上方，懒加载直接拖 LCP）', () => {
    const block = publicCategoryPage.slice(
      publicCategoryPage.indexOf('data-testid="category-cover"'),
      publicCategoryPage.indexOf('data-testid="category-cover"') + 600
    )
    expect(block).toContain('<img')
    expect(block).not.toContain('loading="lazy"')
  })

  it('CategoryDetail 类型声明了这一项，读口与渲染同口径', () => {
    expect(publicCategoryPage).toContain('cover_image?: string | null')
  })
})

describe('类型与标签页边界', () => {
  it('AdminCategory 带 cover_image，AdminTaxonomyPayload 允许显式 null', () => {
    expect(manageSrc).toMatch(/interface AdminCategory \{[\s\S]*?cover_image: string \| null/)
    expect(manageSrc).toMatch(/interface AdminTaxonomyPayload \{[\s\S]*?cover_image\?: string \| null/)
  })

  it('标签页不发送 cover_image（后端 TagUpdate 没有这一列，多带键会 422）', () => {
    expect(tagsPage).not.toContain('cover_image')
    const tagSlice = manageSrc.slice(manageSrc.indexOf('export interface AdminTag'))
    expect(tagSlice.slice(0, 600)).not.toContain('cover_image')
  })
})
