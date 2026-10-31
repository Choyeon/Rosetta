/**
 * 列表卡片「这篇要访问密码」徽标的接线契约（批次 #139）。
 *
 * 后端列表族新增一位存在性布尔 `is_password_protected`（判据单源 `bool(Post.password)`），
 * 卡片消费它。四条反向断言各自挡一次真实事故：
 * - **只读存在性、不读密码**：哈希进列表载荷＝同一份摘要被更多缓存键位复用，还会整份烘进
 *   SSR 的 `__NUXT_DATA__` 给访客看。详情口也不回吐它（闸门只需知道"要不要"）。
 * - 键缺失按「不锁」处理：旧缓存载荷、以及刻意不投影这一位的口（搜索、订阅源）都不带它，
 *   宽松的 `!!` 会给公开文章贴一个假闸门。
 * - 每个显示分钟数的渲染面都得挂一次：与 `PostReadingTime` 同一行元数据，漏一个面就是
 *   「首页有锁标、列表没有」这种没人报的缺陷（同族见 postMediaBadgeWired）。
 * - 页面不得为了"补上这一位"自己再去读密码字段。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(__dirname, '..', '..', '..')
const read = (rel: string) => readFileSync(resolve(root, rel), 'utf8')

const badge = read('frontend/components/PostLockBadge.vue')
const apiTypes = read('frontend/types/api.ts')
const hotPage = read('frontend/pages/posts/hot.vue')
const detailPage = read('frontend/pages/posts/[slug].vue')

// 与 PostReadingTime 同批的面：分钟数 chip 有几处，锁徽标就得有几处。
const SURFACES = [
  'frontend/components/PostCard.vue',
  'frontend/pages/archive/index.vue',
  'frontend/pages/archive/[year]/index.vue',
  'frontend/pages/archive/[year]/[month].vue',
  'frontend/pages/series/[slug].vue'
] as const

describe('徽标组件本身', () => {
  it('只读存在性一位，且不读密码与正文', () => {
    expect(badge).toContain('props.post.is_password_protected === true')
    expect(badge).not.toMatch(/\bpost\.password\b/)
    expect(badge).not.toMatch(/\bpost\.(content|excerpt)\b/)
  })

  it('缺键按不锁处理：不给公开文章贴假闸门', () => {
    expect(badge).toContain('=== true')
    expect(badge).not.toMatch(/const locked = computed\(\(\) => !!/)
  })

  it('图标 aria-hidden，文案同时给 title 与 sr-only', () => {
    expect(badge).toContain('aria-hidden="true"')
    expect((badge.match(/t\('post\.requiresPassword'\)/g) ?? []).length).toBe(2)
    expect((badge.match(/class="sr-only"/g) ?? []).length).toBe(1)
  })
})

describe('渲染面的接线', () => {
  it('每个显示分钟数的面各挂一次徽标，并允许这一位缺席', () => {
    for (const rel of SURFACES) {
      const src = read(rel)
      expect(
        (src.match(/<PostLockBadge :post=/g) ?? []).length,
        `${rel} 的徽标数应与 chip 数不等`
      ).toBe((src.match(/<PostReadingTime :post=/g) ?? []).length)
      expect(src, rel).toContain(
        'import PostLockBadge from \'~~/components/PostLockBadge.vue\''
      )
      expect(src, rel).toContain('is_password_protected?: boolean | null')
    }
  })

  it('热榜页把榜单载荷的这一位透传给同一套卡片渲染', () => {
    expect(hotPage).toContain('is_password_protected?: boolean | null')
    expect(hotPage).toContain('is_password_protected: row.is_password_protected ?? null')
  })

  it('前端类型允许这一位缺席（详情口之外的旧载荷）', () => {
    expect(apiTypes).toContain('is_password_protected?: boolean')
  })

  it('渲染徽标的页面不得读密码字段', () => {
    for (const rel of [...SURFACES, 'frontend/pages/posts/hot.vue']) {
      expect(read(rel), rel).not.toMatch(/\.password\b/)
    }
  })
})

describe('详情页与卡片同口径（批次 #139）', () => {
  // 这一族的另一半：闸门上方那一行元数据（日期 / 阅读量 / 分钟数）密码稿也照样显示。
  // 卡片贴了锁标却什么都不报分钟数，读者会以为自己打开了另一篇。
  it('分钟数不再对密码稿单独收起', () => {
    const block = detailPage.slice(
      detailPage.indexOf('const readingTime = computed'),
      detailPage.indexOf('const wordCount')
    )
    expect(block).toContain('post.value?.reading_time')
    expect(block).not.toContain('needPassword')
  })
})

describe('四语文案', () => {
  it('post.requiresPassword 四语齐全', () => {
    for (const locale of ['zh', 'en', 'ja', 'zh_Hant']) {
      expect(read(`frontend/i18n/locales/${locale}.json`), locale).toContain('"requiresPassword"')
    }
  })

  it('zh_Hant 不得混进简体字形（徽标提示是访客直接读到的文案）', () => {
    const text = read('frontend/i18n/locales/zh_Hant.json')
    expect(text).toContain('存取密碼')
    for (const simplified of ['这', '访', '阅读']) {
      expect(text, simplified).not.toContain(simplified)
    }
  })
})

describe('登录态四档也带这一位（批次 #140）', () => {
  const account = read('frontend/pages/account/index.vue')
  const favorites = read('frontend/composables/useFavorites.ts')

  it('「我的文章/点赞」「收藏」「阅读历史」三档各挂一次锁徽标', () => {
    expect((account.match(/<PostLockBadge :post=/g) ?? []).length).toBe(3)
    expect(account).toContain('import PostLockBadge from \'~~/components/PostLockBadge.vue\'')
    expect(account).toContain('is_password_protected?: boolean | null')
  })

  it('收藏引用类型声明这一位（徽标 props 是全可选弱类型，不声明会被 TS 拒）', () => {
    expect(favorites).toContain('is_password_protected?: boolean | null')
  })

  it('详情页相关推荐卡也挂一次，且渲染面只读存在性、不读密码列', () => {
    expect((detailPage.match(/<PostLockBadge :post="sp\.raw" \/>/g) ?? []).length).toBe(1)
    expect(account).not.toMatch(/post\.password\b/)
    expect(favorites).not.toMatch(/\bpassword: string\b/)
  })
})
