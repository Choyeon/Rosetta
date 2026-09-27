import { describe, it, expect } from 'vitest'
import { readdirSync, existsSync, readFileSync } from 'node:fs'
import process from 'node:process'
import {
  KNOWN_ROSETTA_THEMES,
  MINIMAL_THEME_SLUGS,
  THEME_VISUAL_EXCLUDE_PREFIXES,
  isThemeVisualExcluded,
  resolveThemeAssetPath,
  bustThemeAssetCache
} from '@/lib/rosetta-themes'

// vitest 根目录即 frontend/（vitest.config.ts 所在处）
const themesDir = process.cwd().replace(/[\\/]$/, '') + '/themes'

describe('lib/rosetta-themes 主题变体契约', () => {
  describe('KNOWN_ROSETTA_THEMES 与磁盘目录一一对应', () => {
    it('themes/ 目录存在且每个磁盘主题都已登记', () => {
      expect(existsSync(themesDir)).toBe(true)
      const onDisk = readdirSync(themesDir, { withFileTypes: true })
        .filter(d => d.isDirectory())
        .map(d => d.name)
      for (const slug of onDisk) {
        expect(KNOWN_ROSETTA_THEMES.has(slug), `磁盘主题 ${slug} 未登记进 KNOWN_ROSETTA_THEMES`).toBe(true)
      }
    })

    it('登记的每个 slug 磁盘上都有 manifest 与 style.css', () => {
      for (const slug of KNOWN_ROSETTA_THEMES) {
        expect(existsSync(`${themesDir}/${slug}/rosetta-theme.json`), `${slug} 缺 rosetta-theme.json`).toBe(true)
        expect(existsSync(`${themesDir}/${slug}/style.css`), `${slug} 缺 style.css`).toBe(true)
      }
    })

    it('内建主题恒为两套（editorial 默认 + astro 极简）', () => {
      expect([...KNOWN_ROSETTA_THEMES].sort()).toEqual(['astro-paper-inspired', 'editorial-wp-style'])
    })
  })

  describe('MINIMAL_THEME_SLUGS 骨架变体判定', () => {
    it('极简骨架当前唯一成员是 astro-paper-inspired', () => {
      expect([...MINIMAL_THEME_SLUGS]).toEqual(['astro-paper-inspired'])
    })

    it('默认主题 editorial-wp-style 不走极简骨架', () => {
      expect(MINIMAL_THEME_SLUGS.has('editorial-wp-style')).toBe(false)
    })

    it('极简集合是已知主题的严格子集（未登记主题不得落入极简）', () => {
      for (const slug of MINIMAL_THEME_SLUGS) {
        expect(KNOWN_ROSETTA_THEMES.has(slug)).toBe(true)
      }
      expect(MINIMAL_THEME_SLUGS.has('not-a-real-theme')).toBe(false)
    })
  })

  describe('isThemeVisualExcluded 路径排除', () => {
    it('前缀清单锁定 /admin 与 /oobe', () => {
      expect(THEME_VISUAL_EXCLUDE_PREFIXES).toEqual(['/admin', '/oobe'])
    })

    it('/admin 及其子路径命中排除', () => {
      expect(isThemeVisualExcluded('/admin')).toBe(true)
      expect(isThemeVisualExcluded('/admin/posts')).toBe(true)
      expect(isThemeVisualExcluded('/admin/docs/api')).toBe(true)
    })

    it('/oobe 命中排除', () => {
      expect(isThemeVisualExcluded('/oobe')).toBe(true)
      expect(isThemeVisualExcluded('/oobe/step-2')).toBe(true)
    })

    it('前台路径与近似前缀不误伤', () => {
      expect(isThemeVisualExcluded('/')).toBe(false)
      expect(isThemeVisualExcluded('/posts/hello')).toBe(false)
      expect(isThemeVisualExcluded('/admin-guide')).toBe(true) // 前缀语义：startsWith，非段边界
      expect(isThemeVisualExcluded('/management')).toBe(false)
    })

    it('空 / undefined / null 安全返回 false', () => {
      expect(isThemeVisualExcluded('')).toBe(false)
      expect(isThemeVisualExcluded(undefined)).toBe(false)
      expect(isThemeVisualExcluded(null)).toBe(false)
    })
  })

  describe('resolveThemeAssetPath 资源 URL 归一', () => {
    it('裸文件名补全 /themes/<slug>/ 前缀', () => {
      expect(resolveThemeAssetPath('editorial-wp-style', 'screenshot.png'))
        .toBe('/themes/editorial-wp-style/screenshot.png')
    })

    it('根相对与绝对 URL 原样返回', () => {
      expect(resolveThemeAssetPath('slug', '/uploads/custom.png')).toBe('/uploads/custom.png')
      expect(resolveThemeAssetPath('slug', 'https://cdn.example.com/a.svg')).toBe('https://cdn.example.com/a.svg')
      expect(resolveThemeAssetPath('slug', 'HTTP://cdn.example.com/a.svg')).toBe('HTTP://cdn.example.com/a.svg')
    })

    it('空 src 或缺 slug 的裸文件名返回空串（不产出 /themes/undefined/x）', () => {
      expect(resolveThemeAssetPath('slug', '')).toBe('')
      expect(resolveThemeAssetPath(null, 'a.png')).toBe('')
      expect(resolveThemeAssetPath(undefined, 'a.png')).toBe('')
    })
  })

  describe('bustThemeAssetCache 强缓存 bust', () => {
    it('/themes/** 追加 ?v=<version>', () => {
      expect(bustThemeAssetCache('/themes/editorial-wp-style/style.css', '2.1.1'))
        .toBe('/themes/editorial-wp-style/style.css?v=2.1.1')
    })

    it('已带 query 时改用 & 连接', () => {
      expect(bustThemeAssetCache('/themes/a/style.css?foo=1', '9'))
        .toBe('/themes/a/style.css?foo=1&v=9')
    })

    it('缺版本时兜底 v=0（仍然 bust，不允许无版本直出）', () => {
      expect(bustThemeAssetCache('/themes/a/style.css')).toBe('/themes/a/style.css?v=0')
      expect(bustThemeAssetCache('/themes/a/style.css', null)).toBe('/themes/a/style.css?v=0')
    })

    it('版本包含特殊字符时 URI 编码', () => {
      expect(bustThemeAssetCache('/themes/a/style.css', '1 0&2')).toContain('v=1%200%262')
    })

    it('非 /themes 资源（外链 / 站内其它路径 / 空串）原样返回', () => {
      expect(bustThemeAssetCache('https://cdn.example.com/a.css', '1')).toBe('https://cdn.example.com/a.css')
      expect(bustThemeAssetCache('/uploads/a.png', '1')).toBe('/uploads/a.png')
      expect(bustThemeAssetCache('', '1')).toBe('')
    })
  })

  // 主题包"三处版本号"一致性：manifest.version ↔ style.css 的 Version: 头 ↔ 回退常量 DEFAULT_THEME_VERSION。
  // 三者手写成对，升版时漏一处就出事：href 由版本参与 cache-busting，
  // 常量停在旧值会让"无激活主题"的回退路径加载到已被 CDN/浏览器缓存的旧 CSS。
  describe('主题包版本单一口径', () => {
    const readText = (rel: string) => readFileSync(`${themesDir}/${rel}`, 'utf8')

    for (const slug of ['editorial-wp-style', 'astro-paper-inspired']) {
      it(`${slug}: manifest.slug 与目录名一致`, () => {
        const manifest = JSON.parse(readText(`${slug}/rosetta-theme.json`)) as { slug?: string }
        expect(manifest.slug).toBe(slug)
      })

      it(`${slug}: manifest.version 与 style.css 的 Version: 头一致`, () => {
        const manifest = JSON.parse(readText(`${slug}/rosetta-theme.json`)) as { version?: string }
        const header = /^Version:\s*(.+)$/m.exec(readText(`${slug}/style.css`))
        expect(header, 'style.css 头部缺 Version: 声明').not.toBeNull()
        expect(manifest.version).toBe(header![1]!.trim())
      })
    }

    it('无激活主题的回退常量与默认主题 manifest 完全一致', () => {
      // 用文本解析而不是 import：useFrontendTheme.ts 顶层依赖 Nuxt 自动导入，
      // 在 vitest 里 import 会连带拉起 #app / #imports 解析失败。
      const src = readFileSync(`${process.cwd().replace(/[\\/]$/, '')}/composables/useFrontendTheme.ts`, 'utf8')
      const pick = (name: string) => {
        const m = new RegExp(`export const ${name}\\s*=\\s*'([^']*)'`).exec(src)
        expect(m, `useFrontendTheme.ts 必须显式导出 ${name}`).not.toBeNull()
        return m![1]!
      }
      const manifest = JSON.parse(readText('editorial-wp-style/rosetta-theme.json')) as {
        slug?: string
        name?: string
        version?: string
      }
      expect(pick('DEFAULT_THEME_SLUG')).toBe(manifest.slug)
      expect(pick('DEFAULT_THEME_NAME')).toBe(manifest.name)
      expect(pick('DEFAULT_THEME_VERSION')).toBe(manifest.version)
    })
  })
})
