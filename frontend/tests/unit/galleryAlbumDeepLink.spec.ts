/**
 * 批次 #128：相册页「开着哪个相册」的唯一真值是 ?album=<id>。
 *
 * 上一版它是纯客户端 ref + `role="button"` 的 article：刷新即回到列表、后退直接离开相册页、
 * 中键「新标签打开」拿到的是一页没有相册的列表（SSR 里根本没有可抓的相册链接）。
 * 这里按源码断言钉住四段：卡片必须是真实 <a href>、URL 变化才是打开相册的那只手、
 * 深链到不在当页的相册要能靠详情响应自建、坏 id 走 404 分支而不是转圈。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const src = readFileSync(resolve(ROOT, 'pages/gallery.vue'), 'utf-8').replace(/\r\n/g, '\n')
const locales = ['zh', 'en', 'ja', 'zh_Hant'] as const

describe('相册页 ?album= 深链', () => {
  it('卡片是真实 <a href>，不再是 role="button" 的 article', () => {
    expect(src).toContain(':href="albumHref(album.id)"')
    expect(src).toContain('@click.prevent="openAlbum(album.id)"')
    expect(src).not.toMatch(/<article[^>]*\brole="button"/)
    expect(src).not.toMatch(/<article[^>]*\btabindex="0"/)
    expect(src).not.toContain('@keydown.enter.prevent="openAlbum')
  })

  it('href 走 localeHrefWith 单源，且带齐当前页码', () => {
    expect(src).toContain('const { localeHrefWith } = useLocaleLink()')
    expect(src).toMatch(/localeHrefWith\('\/gallery', \{/)
    expect(src).toContain('album: String(id)')
    expect(src).toMatch(/page: currentPage\.value > 1 \? String\(currentPage\.value\) : ''/)
  })

  it('openAlbum 只改地址栏，真正打开对话框的是 watch(route.query.album)', () => {
    expect(src).toContain('router.replace({ query: albumQuery(currentPage.value, id) })')
    expect(src).toContain('watch(() => route.query.album')
    expect(src).toContain('void applyAlbumFromQuery()')
    expect(src).toContain('onMounted(() => {')
    // 只在客户端改写地址栏：SSR 期 router.replace 会把一次渲染变成第二次导航。
    // 写成正则而不是字符串——vite 会把源码里的 import.meta.client 替换成 true。
    expect(src).toMatch(/if \(!import\.meta\.client\) return/)
  })

  it('垃圾 / 缺失的 album 参数一律按「没开相册」处理', () => {
    expect(src).toContain('const albumIdFromQuery = (raw: unknown): number | null')
    expect(src).toContain('Number.isInteger(n) && n > 0')
    expect(src).toContain('activeAlbumId.value = albumIdFromQuery(route.query.album)')
  })

  it('深链到不在当页的相册：详情响应自建兜底对象，不再因找不到列表项而短路', () => {
    expect(src).toContain('const target = listed ?? (linkedAlbum.value?.id === id ? linkedAlbum.value : null)')
    expect(src).toContain('if (target) Object.assign(target, next)')
    expect(src).toContain('else linkedAlbum.value = next')
    expect(src).toContain('?? (linkedAlbum.value?.id === activeAlbumId.value ? linkedAlbum.value : null)')
  })

  it('坏 id 走 404 分支：明确文案 + 出口，且不与「请求挂了」混成一类', () => {
    expect(src).toContain('const albumNotFound = ref(false)')
    expect(src).toContain('if (status === 404) albumNotFound.value = true')
    expect(src).toMatch(/t\('gallery\.albumNotFound'\)/)
    expect(src).toContain('@click="closeAlbum"')
    // 详情口自己给页内文案，不再双弹 toast
    expect(src).toContain('silentToast: true')
  })

  it('关掉对话框与翻页都把 ?album= 带走', () => {
    expect(src).toContain('if (activeAlbumId.value !== null) setAlbumQuery(null)')
    expect(src).toContain('router.replace({ query: albumQuery(page, null) })')
  })

  for (const locale of locales) {
    it(`四语齐全：${locale} 有 gallery.albumNotFound`, () => {
      const json = JSON.parse(
        readFileSync(resolve(ROOT, 'i18n', 'locales', `${locale}.json`), 'utf-8')
      ) as { gallery?: Record<string, string> }
      expect(json.gallery?.albumNotFound).toBeTruthy()
      expect(json.gallery?.openAlbum).toBeTruthy()
    })
  }
})
