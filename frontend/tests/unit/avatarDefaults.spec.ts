/**
 * avatarDefaults.spec.ts
 * ----------------------
 * 守卫「默认头像本地化 + 三态统一」这套约定（2026-10-01 确立）：
 *
 * 1) 默认头像必须本地生成（内联 SVG data URI），不再外链 DiceBear
 *    —— 否则每个头像一次 /api/media/avatar 代理请求，首屏被外部 CDN 拖慢。
 * 2) 默认头像必须确定性：同 seed 永远同色，且 seed 里不得掺时间
 *    —— 掺了时间会让 SSR 与客户端算出不同值（头像刷新会变 + hydration 隐患）。
 * 3) UserAvatar 的「加载中 / 失败」占位必须与默认头像同款视觉（同色相渐变 + 同首字母）
 *    —— 三态统一，用户看到的永远是同一个人的同一个色块。
 * 4) img 属性契约：loading/decoding/referrerpolicy + 显式宽高（防 CLS、防破图外泄）。
 *
 * 静态扫描部分沿用本项目约定（不挂载组件、不开浏览器）。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it, vi } from 'vitest'
import { avatarAccent, avatarInitial, defaultAvatarDataUri, resolveAvatarUrl } from '~~/composables/useResolvedAvatar'

// resolveAvatarUrl 会读 runtimeConfig.public.apiBase 决定代理前缀，桩掉 Nuxt 运行时
vi.mock('#app/nuxt', async (orig) => {
  const actual = await (orig as () => Promise<Record<string, unknown>>)()
  return { ...actual, useRuntimeConfig: () => ({ public: { apiBase: '/api' } }) }
})

const frontendRoot = resolve(__dirname, '../..')
const readSrc = (rel: string) => readFileSync(resolve(frontendRoot, rel), 'utf-8')

/**
 * 去掉注释后再做「源码里不得出现 X」这类断言：
 * 这些文件顶部有大段说明性注释，会正当地提到被禁用的旧实现（reka-ui / Date.now），
 * 直接全文匹配会误伤注释。只删 HTML 注释、块注释与行注释（`//` 前需是行首或空白，
 * 避免吃掉 URL 里的 `http://`）。
 */
const stripComments = (src: string) =>
  src
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|\s)\/\/[^\n]*/g, '$1')
const readCode = (rel: string) => stripComments(readSrc(rel))

describe('默认头像配色（avatarAccent）', () => {
  it('同一 seed 恒定同色，不同 seed 有区分度', () => {
    const a = avatarAccent('choyeon')
    const b = avatarAccent('choyeon')
    expect(a).toEqual(b)

    const hues = new Set<string>()
    for (const seed of ['alice', 'bob', 'carol', 'dave', 'erin', 'frank']) {
      hues.add(String(avatarAccent(seed).hue))
    }
    // 6 个常见用户名不应挤在同一色相上（撞色会让默认头像失去辨识度）
    expect(hues.size).toBeGreaterThanOrEqual(4)
  })

  it('色相在 0~359 且渐变两端都是合法 HSL', () => {
    for (const seed of ['a', '张三', '', 'x'.repeat(80)]) {
      const { hue, from, to } = avatarAccent(seed)
      expect(hue).toBeGreaterThanOrEqual(0)
      expect(hue).toBeLessThan(360)
      expect(from).toMatch(/^hsl\(\d{1,3}\s+\d{1,3}%\s+\d{1,3}%\)$/)
      expect(to).toMatch(/^hsl\(\d{1,3}\s+\d{1,3}%\s+\d{1,3}%\)$/)
    }
  })

  it('空 seed 也稳定（不掺时间）', () => {
    expect(avatarAccent('')).toEqual(avatarAccent(''))
    expect(avatarAccent(null)).toEqual(avatarAccent(undefined))
  })
})

describe('首字母（avatarInitial）', () => {
  it('英文取首字母并大写', () => {
    expect(avatarInitial('choyeon')).toBe('C')
    expect(avatarInitial('Alice')).toBe('A')
  })

  it('中文取第一个字（按码点，不吃掉代理对）', () => {
    expect(avatarInitial('张三丰')).toBe('张')
    expect(avatarInitial('熬夜攻城狮')).toBe('熬')
  })

  it('无名字时返回空串（只画渐变底，与默认头像 SVG 一致）', () => {
    expect(avatarInitial('')).toBe('')
    expect(avatarInitial(null)).toBe('')
    expect(avatarInitial('   ')).toBe('')
  })
})

describe('默认头像 data URI（defaultAvatarDataUri）', () => {
  it('是编码后的 SVG data URI，且不含裸 # 与未转义引号', () => {
    const uri = defaultAvatarDataUri('choyeon', 'choyeon')
    expect(uri.startsWith('data:image/svg+xml')).toBe(true)
    // 未编码的 # 会被当成 fragment → 渐变 url(#g) 失效，必须编码成 %23
    expect(uri).toContain('%23g')
    expect(uri).not.toMatch(/#(?![0-9a-f]{2})/i)
  })

  it('带名字时画首字母，不带名字时只画渐变底', () => {
    expect(defaultAvatarDataUri('choyeon', 'choyeon')).toContain('C')
    const noLabel = defaultAvatarDataUri('choyeon', '')
    expect(noLabel).not.toContain('<text')
    expect(noLabel).toContain('linearGradient')
  })

  it('名字里的 XML 特殊字符被转义（昵称可含 & < >）', () => {
    const uri = defaultAvatarDataUri('x', '<a&b>')
    expect(uri).not.toContain('<a&b>')
    expect(uri).toContain('%26') // &
  })

  it('体积可控：单个默认头像远小于一次网络往返', () => {
    expect(defaultAvatarDataUri('choyeon', 'choyeon').length).toBeLessThan(1200)
  })
})

describe('候选 URL 归类（resolveAvatarUrl）', () => {
  it('本站自托管头像路径原样返回，不得挂 /api 前缀', () => {
    // /media、/uploads、/static 由后端 StaticFiles + nginx 直接服务，
    // 挂上 apiBase 会变成 /api/media/avatars/x.jpg → 404 → 上传的头像永远不显示。
    for (const p of ['/media/avatars/1_20260101.jpg', '/uploads/x.png', '/static/y.svg']) {
      expect(resolveAvatarUrl(p)).toBe(p)
    }
  })

  it('后端代理串与品牌静态资源同样原样返回', () => {
    expect(resolveAvatarUrl('/api/media/avatar?src=abc&fallback=1')).toBe('/api/media/avatar?src=abc&fallback=1')
    expect(resolveAvatarUrl('/logo/rosetta.svg')).toBe('/logo/rosetta.svg')
  })

  it('其余相对路径才挂 apiBase（后端 API 相对口）', () => {
    expect(resolveAvatarUrl('/avatars/relative.png')).toBe('/api/avatars/relative.png')
  })

  it('外链走代理，占位/内网域名直接丢弃并落到本地默认头像', () => {
    const proxied = resolveAvatarUrl('https://avatars.githubusercontent.com/u/1?v=4')
    expect(proxied.startsWith('/api/media/avatar?src=')).toBe(true)
    expect(proxied).toContain('&fallback=1')
    expect(resolveAvatarUrl('https://example.com/avatar.png')).toMatch(/^data:image\/svg\+xml/)
  })

  it('resolved 优先于原始 avatar（同一人两套字段时不能退回字母兜底）', () => {
    expect(resolveAvatarUrl(
      { seed: 'choyeon', label: 'choyeon' },
      '/api/media/avatar?src=QQ',
      undefined
    )).toBe('/api/media/avatar?src=QQ')
    // 两个候选都为空 → 本地默认头像，零网络请求
    expect(resolveAvatarUrl({ seed: 'choyeon', label: 'choyeon' }, null, undefined)).toMatch(/^data:image\/svg\+xml/)
  })
})

describe('源码契约：默认头像零外链', () => {
  it('useResolvedAvatar 不再外链 DiceBear，也不掺时间种子', () => {
    const code = readCode('composables/useResolvedAvatar.ts')
    expect(code).not.toContain('api.dicebear.com')
    // Date.now 混进 seed 会让 SSR/CSR 算出不同值（头像刷新会变 + hydration 隐患）
    expect(code).not.toMatch(/Date\.now/)
  })

  it('UserAvatar 的占位层用同一套配色算法', () => {
    const code = readCode('components/UserAvatar.vue')
    expect(code).toContain('avatarAccent') // 占位渐变
    expect(code).toContain('avatarInitial') // 占位首字母
    expect(code).toContain('resolveAvatarUrl') // 默认头像仍由统一解析器产出
  })

  it('img 带齐加载与隐私属性，并显式给出宽高', () => {
    const code = readCode('components/UserAvatar.vue')
    for (const attr of ['loading="lazy"', 'decoding="async"', 'referrerpolicy="no-referrer"']) {
      expect(code).toContain(attr)
    }
    expect(code).toContain(':width="numericPx ?? undefined"')
    expect(code).toContain(':height="numericPx ?? undefined"')
  })

  it('缓存命中的图片不会永远停在透明（挂载后补判 complete）', () => {
    const code = readCode('components/UserAvatar.vue')
    // load 事件早于 hydration 触发会丢失，必须主动补判，否则头像永久不可见
    expect(code).toContain('el?.complete')
    expect(code).toContain('naturalWidth > 0')
  })

  it('占位层判定只看 imgOk（两端首帧一致），且不依赖 reka 组件', () => {
    const code = readCode('components/UserAvatar.vue')
    expect(code).toMatch(/showPlaceholder\s*=\s*computed\(\(\)\s*=>\s*imgOk\.value\s*!==\s*true\)/)
    // reka Avatar 在 SSR 产物里会因双 vue 实例渲染成空注释 → 节点级 mismatch
    expect(code).not.toContain('reka-ui')
    expect(code).not.toContain('AvatarRoot')
  })
})
