/**
 * 自定义内容类型（content_types + Post.meta_fields）的四段契约。
 *
 * 这一族最容易出现的缺陷形态不是报错，而是"三段都做了、第四段没人点"：
 * 后端有表、有校验、后台能填，但公开文章页从不读定义 —— 运营者填完字段、
 * 提示保存成功，访客看到的详情页一个字段都没有（`encryption_hint` 与调色板一族都是这个形状）。
 * 所以这里钉的是"链路完整 + 口径一致"，不是单点行为：
 * ① 前端字段类型清单 == 后端 `models/content_type.py::FIELD_TYPES`（集合相等，加类型必须两处同改）；
 * ② 后台管理页为**每一种**类型都提供候选项与编辑控件（漏一种 = 该类型永远建不出来）；
 * ③ 编辑器 `buildPayload` 真的发送 `post_type` + `meta_fields`，且 datetime 走 `lib/datetime`
 *    而不是把输入框原值直接发出（本地墙钟 ≠ UTC，手裁会偏 8 小时）；
 * ④ 后端每个写口都过 `resolve_post_type_and_meta`，详情口把两个键都回吐；
 * ⑤ 公开详情页消费定义（`visibleMetaFields` / `parseContentTypes`），值只走文本插值，
 *    链接带 `rel` 且 href 过 scheme 校验，**不得** v-html；
 * ⑥ 后台菜单里有入口，页面文件真实存在（否则路由 404 而菜单照样亮）。
 * ⑦ 列表可见性：`GET /blog/posts` 的缺省是"全部类型"（自定义类型稿不能只在详情页存在），
 *    `?post_type=` 只做显式收窄且判别位进缓存键（缺省段是 all 而不是某个类型 key），
 *    列表项的 `post_type` 是**必填**，前台列表页与后台文章列表都是这个参数的真实消费方。
 */
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  CONTENT_FIELD_TYPES,
  parseContentTypes,
  visibleMetaFields
} from '~~/composables/useContentTypes'

const ROOT = resolve(process.cwd())
const BACKEND = resolve(ROOT, '..')
const read = (...parts: string[]) => readFileSync(resolve(BACKEND, ...parts), 'utf-8')

/** 截一个 Python 类自己的类体（到下一个顶格 `class` 为止），供逐字段断言使用。 */
function classBody(source: string, name: string): string {
  const start = source.match(new RegExp(`^class ${name}\\b`, 'm'))
  if (!start || start.index === undefined) throw new Error(`找不到 class ${name}`)
  const rest = source.slice(start.index + start[0].length)
  const next = rest.search(/^class /m)
  return next === -1 ? rest : rest.slice(0, next)
}

const modelPy = read('backend', 'models', 'content_type.py')
const servicePy = read('backend', 'services', 'content_type_service.py')
const apiPy = read('backend', 'api', 'content_type.py')
const blogPy = read('backend', 'api', 'blog.py')
const schemasPy = read('backend', 'schemas', '__init__.py')
const adminPage = read('frontend', 'pages', 'admin', 'content', 'content-types.vue')
const postForm = read('frontend', 'components', 'admin', 'PostForm.vue')
const detailPage = read('frontend', 'pages', 'posts', '[slug].vue')
const adminMenu = read('frontend', 'config', 'admin-menu.ts')

/** 后端 FIELD_TYPES 里的字面量（唯一真源）。 */
function backendFieldTypes(): string[] {
  const block = modelPy.match(/FIELD_TYPES: tuple\[str, \.\.\.\] = \(([\s\S]*?)\)/)?.[1]
  if (!block) throw new Error('找不到 FIELD_TYPES——后端类型清单形态变了要同步改本测试')
  return [...block.matchAll(/"([a-z_]+)"/g)].map(m => m[1] as string)
}

/** 管理页 FIELD_TYPE_LABELS 的键（决定下拉里能选到哪些类型）。 */
function adminLabelKeys(): string[] {
  const block = adminPage.match(/const FIELD_TYPE_LABELS[^=]*= \{([\s\S]*?)\n\}/)?.[1]
  if (!block) throw new Error('找不到 FIELD_TYPE_LABELS')
  return [...block.matchAll(/([a-z_]+):/g)].map(m => m[1] as string)
}

function localeKeys(): Record<string, string[]> {
  const out: Record<string, string[]> = {}
  for (const lang of ['zh', 'en', 'ja', 'zh_Hant']) {
    out[lang] = Object.keys(JSON.parse(read('frontend', 'i18n', 'locales', `${lang}.json`)).post)
  }
  return out
}

describe('内容类型：字段类型清单两处同改', () => {
  it('前端 CONTENT_FIELD_TYPES 与后端 FIELD_TYPES 集合相等', () => {
    expect([...CONTENT_FIELD_TYPES].sort()).toEqual(backendFieldTypes().sort())
  })

  it('管理页为每一种字段类型都提供候选项', () => {
    expect(adminLabelKeys().sort()).toEqual([...CONTENT_FIELD_TYPES].sort())
  })

  it('select 的候选项口径在后端只有一条（非 select 不得带候选项）', () => {
    expect(servicePy).toContain('候选项')
    // 前端解析器同样丢弃"select 却没有候选项"的脏条目，否则渲染出一个空下拉
    const parsed = parseContentTypes([
      {
        key: 'book',
        name: '书评',
        fields: [
          { key: 'bad_select', label: '坏档', field_type: 'select', options: [] },
          { key: 'ok', label: '装帧', field_type: 'select', options: ['平装', '精装'] }
        ]
      }
    ])
    expect(parsed[0]?.fields.map(f => f.key)).toEqual(['ok'])
  })
})

describe('内容类型：后台编辑器接线', () => {
  it('buildPayload 始终发送 post_type 与 meta_fields', () => {
    expect(postForm).toMatch(/payload\.post_type\s*=/)
    expect(postForm).toMatch(/payload\.meta_fields\s*=\s*buildMetaFields\(\)/)
  })

  it('datetime 字段走 lib/datetime 换算（本地墙钟 ⇄ UTC），不手裁 ISO', () => {
    expect(postForm).toContain('fromDateTimeLocal')
    expect(postForm).toContain('toDateTimeLocal')
    expect(postForm).not.toMatch(/meta_fields[^\n]*\.slice\(0,\s*16\)/)
  })

  it('换内容类型时清空并按新定义预填，切回内置 post 一律不发字段', () => {
    expect(postForm).toMatch(/if \(!key \|\| key === form\.post_type\) return/)
    expect(postForm).toMatch(/if \(form\.post_type === 'post'\) return null/)
  })

  it('定义已删除（orphan）会挡住保存，而不是让后端 422 时才看见', () => {
    expect(postForm).toContain('orphanPostType')
    expect(postForm).toMatch(/const metaErr = validateContentMeta\(\)/)
  })

  it('管理页：仍在使用的类型不得直接删（后端也会 409）', () => {
    expect(adminPage).toMatch(/posts_count > 0/)
    expect(apiPy).toContain('raise ConflictException')
  })

  it('后台菜单登记且页面文件真实存在', () => {
    expect(adminMenu).toContain('/admin/content/content-types')
    expect(existsSync(resolve(ROOT, 'pages', 'admin', 'content', 'content-types.vue'))).toBe(true)
  })
})

describe('内容类型：后端写口与读口', () => {
  it('文章创建与两条更新路径都过 meta 闸门', () => {
    const calls = blogPy.match(/await resolve_post_type_and_meta\(/g) ?? []
    expect(calls.length).toBeGreaterThanOrEqual(3)
  })

  it('详情响应模型与构造点都带出 post_type / meta_fields', () => {
    expect(schemasPy).toMatch(/class PostLocalizedResponse[\s\S]*post_type: str = "post"[\s\S]*meta_fields: dict\[str, Any\] \| None/)
    expect(blogPy).toMatch(/post_type=_post_type,\s*meta_fields=_meta_fields,/)
  })

  it('读侧宽容：非 dict 的脏 meta_fields 按"没有扩展字段"下发而不是 500', () => {
    expect(blogPy).toContain('isinstance(post.meta_fields, dict)')
    expect(schemasPy).toContain('isinstance(post.meta_fields, dict)')
  })

  it('内置 post 不接受自定义字段（否则等于把自由 JSON 重新引进库里）', () => {
    expect(servicePy).toMatch(/标准文章（post）不接受自定义字段/)
  })

  it('列表查询按 post_type 过滤时，判别位必须进响应缓存键', () => {
    expect(blogPy).toContain('f"pt{post_type or')
  })
})

describe('内容类型：公开详情页消费', () => {
  it('页面按确定性 key 拉公开定义，失败回落空数组', () => {
    expect(detailPage).toContain('content-types:public')
    expect(detailPage).toContain('.catch(() => [] as ContentTypePublic[])')
    expect(detailPage).toContain('parseContentTypes')
  })

  it('只渲染定义内且非空的键（单源 visibleMetaFields，页面不再写一套）', () => {
    expect(detailPage).toContain('visibleMetaFields(findContentType(')
    expect(detailPage).toMatch(/p\.post_type === 'post'/)
  })

  it('字段值绝不 v-html；外链过 scheme 校验并带 rel', () => {
    const start = detailPage.indexOf('自定义字段（内容类型）')
    const end = detailPage.indexOf('v-if="normalizedTags.length"', start)
    expect(start).toBeGreaterThan(-1)
    expect(end).toBeGreaterThan(start)
    const card = detailPage.slice(start, end)
    // 判指令而不是判字符串：卡片上方的注释里就写着"绝不 v-html"
    expect(card).not.toMatch(/v-html\s*=/)
    expect(card).toContain('rel="noopener noreferrer nofollow"')
    expect(detailPage).toMatch(/text\.startsWith\('\/'\) && !text\.startsWith\('\/\/'\)/)
  })

  it('是/否文案四语齐全', () => {
    for (const keys of Object.values(localeKeys())) {
      expect(keys).toEqual(expect.arrayContaining(['contentMetaYes', 'contentMetaNo']))
    }
  })
})

describe('内容类型：列表可见性（默认全部类型 + ?post_type= 显式收窄）', () => {
  const listPage = read('frontend', 'pages', 'posts', 'index.vue')
  const adminListPage = read('frontend', 'pages', 'admin', 'content', 'posts', 'index.vue')
  const adminManage = read('frontend', 'composables', 'useAdminManage.ts')
  const seoComposable = read('frontend', 'composables', 'useSeo.ts')

  it('后端列表口不再把缺省写成「只列内置 post」', () => {
    // 全站没有任何列表消费方传过这个参数，缺省收窄等于自定义类型文章在所有列表里查无此文。
    // 清点写成"整份 blog.py 里 `Post.post_type ==` 只许出现一次，且必须在 if post_type: 之下"：
    // 只判字面量 `== "post"` 挡不住 `== (post_type or "post")` 这类换个写法的回归。
    expect(blogPy.match(/Post\.post_type == /g) ?? []).toHaveLength(1)
    expect(blogPy).toMatch(/if post_type:\r?\n\s*query = query\.where\(Post\.post_type == post_type\)/)
  })

  it('后台列表行内带出类型名（混排时管理员得能分辨哪篇是什么类型）', () => {
    expect(adminListPage).toContain('typeName((row as Post).post_type)')
    // 内置 post 不显示徽标：一列全是"标准文章"等于没有信息
    expect(adminListPage).toMatch(/if \(!key \|\| key === 'post'\) return ''/)
    // 'all' 在两条取数路径上都归一成"不带这个键"，发成 ?post_type=all 会当成一个不存在的类型
    expect(adminListPage).toContain('post_type: typeFilter.value !== \'all\' ? typeFilter.value : undefined')
    expect(adminManage).toMatch(/params\.post_type !== 'all' \? params\.post_type : undefined/)
  })

  it('缓存键的缺省段是 all（全部类型），不是某个类型 key', () => {
    // 写成 pt{post_type or 'post'} 时"不传参数"与"?post_type=post"共用一个键位，
    // 而后者是显式收窄的结果集，先落进缓存就在整个 TTL 内少掉全部自定义类型文章
    expect(blogPy).toContain('f"pt{post_type or \'all\'}",')
  })

  it('列表项响应模型带出 post_type，且刻意不给默认值', () => {
    // 只截这个类自己的类体：`post_type: str = "post"` 在同文件里是合法形态（详情响应模型），
    // 全文正则会把别的类一起读进来，判成"给了默认值"或反过来被后来新增的类糊过去
    const body = classBody(schemasPy, 'PostListItemLocalized')
    expect(body).toMatch(/\n {4}post_type: str\n/)
    // 带默认值时漏传的那一处不会报错，只会一直显示"标准文章"
    expect(body).not.toMatch(/post_type: str = /)
    const projections = blogPy.match(/post_type=post\.post_type or "post",/g) ?? []
    expect(projections.length).toBeGreaterThanOrEqual(4)
  })

  it('前台列表页是 ?post_type= 的真实消费方（下拉 + URL + 请求三处都接）', () => {
    expect(listPage).toContain('route.query.post_type as string')
    expect(listPage).toMatch(/q\.post_type = selectedType\.value/)
    expect(listPage).toMatch(/post_type: \(selectedType\.value[^\n]*ALL_TYPES[^\n]*selectedType\.value : undefined/)
    // 控件只在"确实定义过自定义类型"的站点出现：永远只有两项的下拉等于摆了个不改变结果的控件
    expect(listPage).toContain('v-if="hasTypeFilter"')
    expect(listPage).toContain('parseContentTypes')
  })

  it('post_type 不进 canonical 查询白名单（视图变体不是独立页面）', () => {
    expect(seoComposable).toMatch(/const CANONICAL_QUERY_KEYS = \['page'\]/)
  })

  it('后台文章列表接了类型筛选，且 all 发成「不带这个键」', () => {
    expect(adminListPage).toContain('typeFilter')
    expect(adminManage).toMatch(/params\.post_type !== 'all' \? params\.post_type : undefined/)
  })

  it('类型筛选文案四语齐全', () => {
    for (const lang of ['zh', 'en', 'ja', 'zh_Hant']) {
      const keys = Object.keys(JSON.parse(read('frontend', 'i18n', 'locales', `${lang}.json`)).posts)
      expect(keys).toEqual(expect.arrayContaining(['selectType', 'allTypes', 'typePost']))
    }
  })
})

describe('内容类型：读侧挑选规则（纯函数）', () => {
  const type = parseContentTypes([
    {
      key: 'book',
      name: '书评',
      fields: [
        { key: 'isbn', label: 'ISBN', field_type: 'text' },
        { key: 'rating', label: '评分', field_type: 'number' },
        { key: 'signed', label: '是否签名本', field_type: 'boolean' },
        { key: 'cover', label: '封面', field_type: 'image' },
        { key: 'buy', label: '购买链接', field_type: 'url' },
        { key: 'notes', label: '笔记', field_type: 'markdown' }
      ]
    }
  ])[0]

  it('脏条目整条丢弃：key 非法或类型不在清单内都不进定义', () => {
    const parsed = parseContentTypes([
      {
        key: 'Book',
        name: '大写 key 不合法',
        fields: [{ key: 'a', label: 'A', field_type: 'text' }]
      },
      {
        key: 'ok',
        name: '合法类型',
        fields: [
          { key: 'Bad Key', label: 'B', field_type: 'text' },
          { key: 'good', label: 'G', field_type: 'text' },
          { key: 'weird', label: 'W', field_type: 'color' }
        ]
      }
    ])
    expect(parsed.map(t => t.key)).toEqual(['ok'])
    expect(parsed[0]?.fields.map(f => f.key)).toEqual(['good'])
  })

  it('只留下定义内且非空的键；布尔 false 是有效值', () => {
    const rows = visibleMetaFields(type ?? null, {
      isbn: '978-7',
      rating: 0,
      signed: false,
      cover: '',
      buy: null,
      notes: undefined,
      legacy_key: '定义里没有它'
    })
    expect(rows.map(r => r.field.key)).toEqual(['isbn', 'rating', 'signed'])
  })

  it('meta 缺失或类型为 null（内建 post / 定义已删）时回空列表而不是抛错', () => {
    expect(visibleMetaFields(null, { isbn: '978-7' })).toEqual([])
    expect(visibleMetaFields(type ?? null, null)).toEqual([])
    expect(visibleMetaFields(type ?? null, { })).toEqual([])
  })
})
