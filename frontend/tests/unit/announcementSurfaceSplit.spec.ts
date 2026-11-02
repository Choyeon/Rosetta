/**
 * 公告「两个来源 → 两个表面」拆分契约（静态源码断言）。
 *
 * 背景：合并版把公告表的多条运营公告与设置页 notice 分组挤进同一条顶部横幅，于是
 *   ① 横幅可以在首屏占三四行，把访客真正要读的文章推下折叠线；
 *   ② notice.sticky 在后台写着「滚动时仍然显示」，代码里却只用来决定列表顺序——
 *     拨动它，页面什么都不会发生。
 * 现在两个来源各占一个表面，这里钉住三条边界，防止以后又有人把它们合回去。
 *
 * 本机无 node/pnpm 时，同一批断言的等价 python 替身：
 * `.venv/Scripts/python.exe scripts_tmp/verify_announcement_split_spec.py`。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const layoutSource = readFileSync(resolve(ROOT, 'layouts/default.vue'), 'utf-8')
const cardSourceFull = readFileSync(resolve(ROOT, 'components/AnnouncementSidebarCard.vue'), 'utf-8')
const settingsSource = readFileSync(resolve(ROOT, 'pages/admin/system/settings.vue'), 'utf-8')
const adminListSource = readFileSync(resolve(ROOT, 'pages/admin/interaction/announcements.vue'), 'utf-8')

/**
 * 文件头那段注释是"口径说明"，里面本来就该出现 is_active / v-html 这类被禁止的字面量，
 * 所以负向断言只看注释之后的代码，否则守卫会因为自己的文档而红。
 */
const cardSource = cardSourceFull.slice(cardSourceFull.indexOf('-->') + 3)

describe('顶部横幅只渲染设置页 notice 分组那一条', () => {
  it('布局不再请求 /announcements（公告表归侧栏卡）', () => {
    expect(layoutSource).not.toContain('/announcements')
  })

  it('横幅行集合来自 noticeToRow，且不再有合并 helper', () => {
    expect(layoutSource).toContain('noticeToRow(site.notice.value)')
    expect(layoutSource).not.toContain('mergeAnnouncementRows')
  })

  it('notice.sticky 有真实执行点（position: sticky），不再只是排序位', () => {
    const at = layoutSource.indexOf('const bannerStickyClass')
    expect(at).toBeGreaterThan(-1)
    const window = layoutSource.slice(at, at + 400)
    expect(window).toContain('bannerIsSticky(site.notice.value)')
    expect(window).toContain('sticky top-16 z-30')
    expect(window).toContain('sticky top-0 z-30')
    // 顶栏自身是 sticky top-0（高 16），横幅必须让开它，否则粘顶时盖住导航
    expect(window).toContain('header_style === \'sticky\'')
  })
})

describe('侧栏卡渲染公告表的多条公告', () => {
  it('数据源是公开口 /announcements，并按语言分键', () => {
    expect(cardSource).toContain('useAPI<AnnouncementRow[]>(\'/announcements\'')
    expect(cardSource).toContain('sidebar:announcements:${locale.value}')
  })

  it('消费服务端已排好的顺序，前端不重排、不再判时间窗', () => {
    expect(cardSource).not.toContain('.sort(')
    expect(cardSource).not.toContain('start_time')
    expect(cardSource).not.toContain('end_time')
    expect(cardSource).not.toContain('is_active')
  })

  it('正文不走 v-html（AnnouncementResponse 的 title/content 是明文字符串）', () => {
    expect(cardSource).not.toContain('v-html')
  })

  it('两块表面共用同一份 Markdown 降级（横幅剥标记、侧栏不剥 = 同一条公告两种观感）', () => {
    expect(cardSource).toContain('stripInlineMarkdown')
    expect(cardSource).toContain('titleText(ann)')
    expect(cardSource).toContain('bodyText(ann)')
    // 反向：不得再直接绑定库里那两列
    expect(cardSource).not.toContain('{{ ann.content }}')
    expect(cardSource).not.toContain('{{ ann.title')
    // 标题/正文同源判据也必须是剥完标记后的两份，否则 `**公告**` 与 `公告` 会各出一行
    expect(cardSource).toContain('body !== titleText(ann)')
  })

  it('日期只截 ISO 段，不做本地化格式化（SSR/hydrate 字节一致）', () => {
    expect(cardSource).toContain('announcementDateText(ann.created_at)')
    expect(cardSource).not.toContain('toLocaleDateString')
    expect(cardSource).not.toContain('new Date(')
  })

  it('四语都补齐了卡片用到的文案键', () => {
    const used = [
      'home.announcements',
      'announcement.none',
      'announcement.showMore',
      'announcement.showLess',
      'announcement.type_info',
      'announcement.type_warning',
      'announcement.type_success',
      'announcement.type_error',
      'error.loadFailed',
      'a11y.closeAnnouncement'
    ]
    for (const locale of ['zh', 'en', 'ja', 'zh_Hant']) {
      const dict = JSON.parse(
        readFileSync(resolve(ROOT, `i18n/locales/${locale}.json`), 'utf-8')
      ) as Record<string, Record<string, unknown>>
      for (const key of used) {
        const [ns = '', leaf = ''] = key.split('.')
        expect(dict?.[ns]?.[leaf], `${locale} 缺少 ${key}`).toBeTruthy()
      }
    }
  })
})

describe('后台两处描述要说清各自的前台落点', () => {
  it('设置页公告分组描述写明顶部横幅与公告管理的分工', () => {
    const at = settingsSource.indexOf('{ key: \'notice\', label:')
    expect(at).toBeGreaterThan(-1)
    const window = settingsSource.slice(at, at + 300)
    expect(window).toContain('顶部横幅')
    expect(window).toContain('公告管理')
  })

  it('设置页 notice.enable 的标签不再谎称"公告接口回空"', () => {
    expect(settingsSource).not.toContain('公告接口回空')
    const at = settingsSource.indexOf('sticky: \'滚动时')
    expect(at).toBeGreaterThan(-1)
    expect(settingsSource.slice(at, at + 120)).toContain('吸')
  })

  it('公告管理页描述写明内容出现在侧栏而不是顶部横幅', () => {
    expect(adminListSource).toContain('首页侧栏')
    expect(adminListSource).toContain('AnnouncementSidebarCard')
  })
})
