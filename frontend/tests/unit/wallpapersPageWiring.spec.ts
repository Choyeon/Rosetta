/**
 * `/wallpapers`：`GET /api/bing/image/archive` 的消费方与它的三条口径。
 *
 * 为什么需要守卫（2026-10-31 这一批的起因）：归档口早就有文档、有响应模型，却一个调用点
 * 都没有——"接口一直在算，前台没人看"。这一面把它接上，同时把三条容易静默分叉的口径钉住：
 *
 *  1. **图片必须是站内代理直链**（`/api/bing/image?src=<base64>`）。页面是 SSR 的，`<img src>`
 *     由服务端首帧产出，客户端 hydration 用同一个纯函数再算一遍必须逐字节相同，否则每张卡片
 *     一次节点级 mismatch；而把 `cn.bing.com` 原链挂上去，站内那份 30 天 `immutable` 落盘缓存
 *     与兜底 SVG 全部失效，Bing 限流/地区差异直接变成访客看到的碎图。
 *     → 代理串单源在 `lib/bing-image.ts`，登录页那个 composable 也不许再抄一份内联实现。
 *  2. **开关关掉 = 公开面整组收起**：页脚入口消失、页面 `noindex, follow`、后端 sitemap 不提交
 *     这条地址（同 `/sponsor`、`/gallery` 先例）。三处任一漏掉的表现分别是"点进来一张空态"、
 *     "爬虫收到一个自我声明别收录的 URL"。收录判据是 `site_settings.py::bing_wallpaper_enabled`，
 *     与 `/api/config` 投影出的那一份合并结果由 `tests/test_bing_wallpaper_archive.py` 逐形态对账。
 *  3. **新增顶级路由的配套登记**：`lib/top-level-routes.ts` + 后端 `_TOP_LEVEL_ROUTE_SLUGS`
 *     （`pageAliasTopLevelRoutes.spec.ts` 逐条对账）、routeRules 的 swr + 完整 `Cache-Control`
 *     （§2.3 那条 Nitro 会整条覆写口径在这里同样成立：不登记就落回 `'/**'` 的 swr 600）。
 *
 * 文案四语齐全也在这条 spec 里——`wallpapers.*` 与 `footer.wallpapers` 少一个 key，
 * 页面上显示的是裸 key 而不是回落文案。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { bingProxyUrl, parseBingArchive } from '~~/lib/bing-image'

const ROOT = resolve(__dirname, '..', '..')
const page = readFileSync(resolve(ROOT, 'pages/wallpapers.vue'), 'utf8')
const footer = readFileSync(resolve(ROOT, 'components/AppFooter.vue'), 'utf8')
const composable = readFileSync(resolve(ROOT, 'composables/useBingWallpaper.ts'), 'utf8')
const topLevel = readFileSync(resolve(ROOT, 'lib/top-level-routes.ts'), 'utf8')
const nuxtConfig = readFileSync(resolve(ROOT, 'nuxt.config.ts'), 'utf8')
const backendBlog = readFileSync(resolve(ROOT, '../backend/api/blog.py'), 'utf8')

const LOCALES = ['zh', 'en', 'ja', 'zh_Hant'] as const

/** base64 解回来比对，避免把编码结果当成第二个真源。 */
function decode(encoded: string): string {
  return decodeURIComponent(escape(atob(encoded)))
}

describe('Bing 站内代理直链（lib/bing-image.ts 单源）', () => {
  it('相对路径补 cn.bing.com 后整条进代理，src 参数解回来就是那张图', () => {
    const out = bingProxyUrl('/th?id=OHR.Example_1920x1080.jpg')
    expect(out.startsWith('/api/bing/image?src=')).toBe(true)
    expect(decode(out.slice('/api/bing/image?src='.length))).toBe(
      'https://cn.bing.com/th?id=OHR.Example_1920x1080.jpg'
    )
  })

  it('绝对地址与自定义 apiBase 都照代理，已代理过的串不再套第二层', () => {
    expect(decode(
      bingProxyUrl('https://cn.bing.com/th?id=OHR.a_UHD.jpg').slice('/api/bing/image?src='.length)
    )).toBe('https://cn.bing.com/th?id=OHR.a_UHD.jpg')
    expect(
      bingProxyUrl('/th?id=OHR.a', 'https://cdn.example.com/api').startsWith('https://cdn.example.com/api/bing/image?src=')
    ).toBe(true)
    const already = bingProxyUrl('/th?id=OHR.a')
    expect(bingProxyUrl(already)).toBe(already)
  })

  it('空串返回空串，data: 内联图原样透传（调用方据此决定渲染不渲染 <img>）', () => {
    expect(bingProxyUrl('')).toBe('')
    expect(bingProxyUrl('   ')).toBe('')
    expect(bingProxyUrl('data:image/svg+xml;base64,AAA')).toBe('data:image/svg+xml;base64,AAA')
  })
})

describe('归档载荷归一', () => {
  const row = {
    date: '2026-10-30',
    title: '海岸线',
    url: '/th?id=OHR.Coast_1920x1080.jpg',
    url_uhd: '/th?id=OHR.Coast_UHD.jpg',
    copyright: '© 摄影师',
    copyright_url: 'https://www.bing.com/example'
  }

  it('三种信封形态都能解出数组（后端叠过一层，读侧不赌形状）', () => {
    for (const payload of [
      [row],
      { success: true, data: [row], count: 1 },
      { data: { data: [row] } }
    ]) {
      const cards = parseBingArchive(payload)
      expect(cards, JSON.stringify(payload)).toHaveLength(1)
      expect(cards[0]?.date).toBe('2026-10-30')
      expect(cards[0]?.image.startsWith('/api/bing/image?src=')).toBe(true)
      expect(cards[0]?.download.startsWith('/api/bing/image?src=')).toBe(true)
      expect(cards[0]?.source).toBe('https://www.bing.com/example')
    }
  })

  it('日期与图片都没有的条目丢弃，同 date+image 的重复行只留一张', () => {
    const cards = parseBingArchive([
      { title: '什么都没有' },
      null,
      'not-an-object',
      row,
      { ...row, copyrightlink: undefined },
      { date: '2026-10-29', url: '' }
    ])
    expect(cards.map(c => c.date)).toEqual(['2026-10-30', '2026-10-29'])
  })

  it('缺 title 用日期顶上，copyright_url 缺席时回落 copyrightlink', () => {
    const [card] = parseBingArchive([{ date: '2026-10-28', url: '/th?id=OHR.b', copyrightlink: 'https://x' }])
    expect(card?.title).toBe('2026-10-28')
    expect(card?.source).toBe('https://x')
    expect(card?.download).toBe('')
  })

  it('不是数组也不是对象时回空列表，不让页面拿到 undefined', () => {
    expect(parseBingArchive(null)).toEqual([])
    expect(parseBingArchive('oops')).toEqual([])
    expect(parseBingArchive({ success: true })).toEqual([])
  })
})

describe('/wallpapers 页面接线', () => {
  it('接的是归档口，且 days 与上游真实保留窗口一致', () => {
    expect(page).toContain('useAPI<unknown>(\'/bing/image/archive\'')
    expect(page).toContain('const ARCHIVE_DAYS = 8')
    expect(page).toContain('query: { days: ARCHIVE_DAYS }')
    // 缓存键带判别位：换 days 不换键会回放另一段窗口
    expect(page).toContain('key: `public:bing-archive:${ARCHIVE_DAYS}`')
  })

  it('<img>/下载链只吃归一后的站内代理串，模板里不出现 cn.bing.com 原链', () => {
    const tpl = page.slice(page.indexOf('<template>'), page.indexOf('</template>'))
    expect(page).toContain(':src="card.image"')
    expect(page).toContain(':href="card.download"')
    expect(page).toContain('import { parseBingArchive } from \'~~/lib/bing-image\'')
    expect(tpl, '原链出现在模板里就是绕开了站内缓存').not.toContain('cn.bing.com')
  })

  it('代理串只有一个实现：归档页与登录页共用 lib，composable 不再抄内联版', () => {
    const lib = readFileSync(resolve(ROOT, 'lib/bing-image.ts'), 'utf8')
    expect(lib).toContain('export function bingProxyUrl(')
    expect(lib, '站内原链只允许出现在拼装那一句').not.toMatch(/cn\.bing\.com\/th/)
    expect(composable).toContain('import { bingProxyUrl } from \'~~/lib/bing-image\'')
    expect(composable).toContain('bingProxyUrl(rawUrl, apiBase.value || \'/api\')')
    expect(composable).toContain('fullUrl: proxiedBingUrl(fullUrl)')
    expect(composable).toContain('uhdUrl: proxiedBingUrl(uhdUrl)')
    expect(composable, '第二个内联实现 = 两处会各自漂移').not.toContain('/bing/image?src=')
  })

  it('日期原样显示 ISO 串，不用 toLocaleString（SSR 与客户端时区不同会换字）', () => {
    expect(page).toContain('{{ card.date }}')
    expect(page).not.toMatch(/toLocale\w+\(/)
  })

  it('关掉开关即整页收起 + noindex，判据来自 /api/config 的同一个开关', () => {
    expect(page).toContain('site.state.value.publicConfig?.enable_bing_wallpaper === false')
    expect(page).toContain('const wallpapersEmpty = computed(')
    expect(page).toContain('noindex: wallpapersEmpty')
    expect(page).toContain('url: \'/wallpapers\'')
    expect(page).toContain('v-else-if="!disabled && cards.length > 0"')
  })

  it('请求失败有独立分支，不留一片没有内容的空白', () => {
    expect(page).toMatch(/v-else-if="loadError"/)
    expect(page).toMatch(/@click="retry"/)
  })

  it('页脚入口跟着同一个开关收起', () => {
    expect(footer).toContain('to: \'/wallpapers\'')
    expect(footer).toContain('labelKey: \'footer.wallpapers\'')
    expect(footer).toContain('site.state.value.publicConfig?.enable_bing_wallpaper !== false')
    expect(footer).toContain('if (link.to === \'/wallpapers\') return bingWallpaperEnabled.value')
  })
})

describe('新顶级路由的配套登记', () => {
  it('前端清单与后端 _TOP_LEVEL_ROUTE_SLUGS 都有 wallpapers', () => {
    expect(topLevel).toContain('\'wallpapers\',')
    expect(backendBlog).toContain('"wallpapers",')
  })

  it('routeRules 显式登记 swr 3600 + 完整 Cache-Control（不登记就落回 /** 的 swr 600）', () => {
    expect(nuxtConfig).toMatch(
      /'\/wallpapers':\s*\{\s*swr:\s*3600,\s*headers:\s*\{\s*'Cache-Control':\s*'public, max-age=0, s-maxage=3600, stale-while-revalidate=86400'/
    )
  })

  it('后端 sitemap 按合并后的开关条件收录，判据与 /api/config 同源', () => {
    expect(backendBlog).toContain('include_wallpapers: bool = False,')
    expect(backendBlog).toContain('if include_wallpapers:')
    expect(backendBlog).toContain('f"{site_url}/wallpapers",')
    expect(backendBlog).toContain('include_wallpapers=await bing_wallpaper_enabled(db),')
    expect(backendBlog).toContain('from backend.services.site_settings import bing_wallpaper_enabled')
  })

  it('四语文案齐全（少一个 key 页面就显示裸 key）', () => {
    for (const locale of LOCALES) {
      const src = readFileSync(resolve(ROOT, `i18n/locales/${locale}.json`), 'utf8')
      const json = JSON.parse(src) as Record<string, Record<string, string>>
      expect(json.wallpapers, `${locale} 缺 wallpapers 块`).toBeTruthy()
      for (const key of ['title', 'desc', 'download', 'empty', 'emptyHint']) {
        expect(json.wallpapers?.[key], `${locale} 缺 wallpapers.${key}`).toBeTruthy()
      }
      expect(json.footer?.wallpapers, `${locale} 缺 footer.wallpapers`).toBeTruthy()
    }
  })
})
