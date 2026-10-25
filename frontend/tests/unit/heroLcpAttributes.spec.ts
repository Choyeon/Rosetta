/**
 * 公开 SSR 页与共享组件里的每个 <img> 都必须带显式 width/height（intrinsic 尺寸提示，
 * 防 CLS；容器均有 CSS 约束，属性只作比例提示不改外观），且首页 hero 缩略图
 * 不得 loading="lazy"（首屏候选被延迟加载会拖 LCP）。
 *
 * 手法沿用 noindexShellMeta.spec.ts / routeRulesSsr.spec.ts 的"读源码文本断言"：
 * 爬虫面的首字节 HTML 由 SSR 产出，构建期不跑浏览器，只有静态扫描能钉住属性覆盖。
 */

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')

/**
 * 显式豁免清单：全屏灯箱 / 上传预览类 <img> 拿不到稳定 intrinsic 尺寸
 * （源是运行时任意大图或 blob 预览，尺寸由视口/容器即时决定），
 * 且都不在爬虫可读的 SSR 首字节面上。除这两类外不得再往里加条目。
 */
const IMG_DIMENSION_EXEMPTIONS = [
  'components/ImageLightbox.vue', // 全屏灯箱：max-h-[85vh] object-contain，源图尺寸不可知
  'components/ImageUploadZone.vue' // 上传队列预览：blob object URL，编辑表单专用，非爬虫面
] as const

/** SPA 反选/非爬虫面（admin、login、register、oobe、account）整棵跳过。 */
function isSkippedPath(rel: string): boolean {
  return /(^|\/)admin(\/|\.vue$)/i.test(rel)
    || /login|register|forgot-password|oobe|account/i.test(rel)
}

function collectVueFiles(dir: string, acc: string[] = []): string[] {
  for (const entry of readdirSync(resolve(ROOT, dir))) {
    const rel = `${dir}/${entry}`
    if (statSync(resolve(ROOT, rel)).isDirectory()) {
      collectVueFiles(rel, acc)
    } else if (entry.endsWith('.vue')) {
      acc.push(rel)
    }
  }
  return acc
}

/**
 * 提取源码里所有真实 <img ...> 标签块（跳过 `<img>` 这种散文/注释提法：
 * 只认 `<img` 后紧跟空白或 `/` 的形态）。扫描时跟踪引号状态，
 * 避免 `@error="(e) => {...}"` 里的 `=>` 提前截断标签。
 */
function extractImgBlocks(src: string): string[] {
  const blocks: string[] = []
  const re = /<img(?=[\s/])/g
  let m: RegExpExecArray | null
  while ((m = re.exec(src)) !== null) {
    let i = m.index + 4
    let quote: string | null = null
    while (i < src.length) {
      const ch = src[i]
      if (quote) {
        if (ch === quote) quote = null
      } else if (ch === '"' || ch === "'" || ch === '`') {
        quote = ch
      } else if (ch === '>') {
        break
      }
      i++
    }
    blocks.push(src.slice(m.index, i))
    re.lastIndex = i
  }
  return blocks
}

const scanned = collectVueFiles('pages')
  .concat(collectVueFiles('components'))
  .filter(rel => !isSkippedPath(rel))
  .filter(rel => !IMG_DIMENSION_EXEMPTIONS.includes(
    rel as (typeof IMG_DIMENSION_EXEMPTIONS)[number]
  ))

describe('公开页与共享组件的 <img> 尺寸覆盖', () => {
  it('扫描器本身有效（扫到的文件数不为零，清单没被改坏）', () => {
    expect(scanned.length).toBeGreaterThan(10)
    expect(scanned).toContain('components/PostCard.vue')
    expect(scanned).toContain('pages/gallery.vue')
  })

  it('每个 <img> 块都带显式 width 与 height', () => {
    for (const rel of scanned) {
      const src = readFileSync(resolve(ROOT, rel), 'utf-8')
      for (const block of extractImgBlocks(src)) {
        expect(block, `${rel} 里有一个 <img> 缺 width：\n${block.slice(0, 200)}`)
          .toContain('width=')
        expect(block, `${rel} 里有一个 <img> 缺 height：\n${block.slice(0, 200)}`)
          .toContain('height=')
      }
    }
  })

  it('豁免清单里没有僵尸条目（文件改名/属性补齐后要清掉）', () => {
    for (const rel of IMG_DIMENSION_EXEMPTIONS) {
      const blocks = extractImgBlocks(readFileSync(resolve(ROOT, rel), 'utf-8'))
      expect(blocks.length, `${rel} 已登记豁免，但它没有任何 <img> 块`).toBeGreaterThan(0)
    }
  })
})

describe('首页 hero 缩略图是 LCP 候选', () => {
  const heroBlock = (() => {
    const src = readFileSync(resolve(ROOT, 'pages/index.vue'), 'utf-8')
    const block = extractImgBlocks(src).find(b => b.includes('slide.media_url'))
    return block ?? null
  })()

  it('hero 缩略图 img 段存在', () => {
    expect(heroBlock, 'pages/index.vue 里找不到 slide.media_url 的 <img>（扫描器或轮播结构变了）')
      .not.toBeNull()
  })

  it('不带 loading="lazy"（首屏图延迟加载直接拖 LCP）', () => {
    expect(heroBlock).not.toContain('loading="lazy"')
  })

  it('带显式 width/height（容器 size-11 → 56x56）', () => {
    expect(heroBlock).toContain('width="56"')
    expect(heroBlock).toContain('height="56"')
  })
})
