/**
 * 公开页的颜色只能来自设计令牌（adminUiConsistency.spec.ts 同一条口径的另一半代码）。
 *
 * 为什么公开页也要钉：Tailwind 具名色阶不在 main.css 的令牌表里，表现是
 * 「后台换了品牌色、切了深色模式，只有这一块还是那个颜色」，而公开页的
 * 公告横幅 / 标签胶囊 / auth 按钮此前全是具名色阶——主题改一次色，这些点一个都不跟着变。
 *
 * EXEMPT 是**按文件**的例外，且必须写理由；例外清单里已经不需要例外的文件会被另一条用例
 * 判红（"修完就删掉例外"），否则这张表只会越写越长，最后变成没人读的通行证。
 */
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve } from 'node:path'

const PUBLIC_DIRS = ['pages', 'components', 'composables', 'lib', 'layouts']

function walk(dir: string, out: string[] = []): string[] {
  let entries: string[]
  try {
    entries = readdirSync(resolve(process.cwd(), dir))
  } catch {
    return out
  }
  for (const name of entries) {
    const full = `${dir}/${name}`
    if (statSync(resolve(process.cwd(), full)).isDirectory()) walk(full, out)
    else if (full.endsWith('.vue') || full.endsWith('.ts')) out.push(full)
  }
  return out
}

const read = (f: string) => readFileSync(resolve(process.cwd(), f), 'utf8')

/** 与后台守卫同一份正则；black / white / transparent 不在其中（那是底图对比色，不是品牌色）。 */
const PALETTE_CLASS = /(?:bg|text|border|from|via|to|ring|fill|stroke)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-(?:50|[1-9]00)\b/

const EXEMPT: Record<string, string> = {
  'pages/index.vue':
    'hero 文字色调按壁纸亮度二选一（text-white / text-slate-900），与品牌色无关且由 heroTextColorWired.spec.ts 逐字钉住；techRows 是各技术自己的品牌标识色',
  'pages/oobe.vue':
    '向导整页压在任意亮度的 Bing 壁纸上，剩下的具名类只有 zinc 中性发丝线与淡底（亮色 zinc-900/alpha + dark: white/alpha 双轨）'
    + '和恒深日志台的 text-zinc-500 —— 它们是底图对比色不是品牌色；主色与状态色已全部走语义令牌，'
    + '双轨成对与暗色大面玻璃必须真深色这两条由 oobeThemeScope.spec.ts 单独守'
}

const PUBLIC_FILES = PUBLIC_DIRS
  .flatMap(dir => walk(dir))
  .filter(f => !f.includes('/admin'))
  .filter(f => !(f in EXEMPT))

describe('公开页样式只能来自设计令牌', () => {
  it.each(PUBLIC_FILES)('%s 不得使用 Tailwind 具名色阶', (file) => {
    const hits = read(file)
      .split('\n')
      .map((line, i) => ({ n: i + 1, line }))
      .filter(x => PALETTE_CLASS.test(x.line))
    expect(
      hits,
      `${file} 出现绕过令牌的色阶类，应改用 bg-primary / bg-error-muted + text-error-muted-foreground `
      + `等语义类（深色底图上用 *-on-scrim）；确属品牌色或底图对比色的，把该文件与理由写进 EXEMPT：\n`
      + hits.map(x => `  L${x.n}: ${x.line.trim().slice(0, 120)}`).join('\n')
    ).toHaveLength(0)
  })

  it('例外清单里不得留着已经不需要例外的文件', () => {
    for (const [file, reason] of Object.entries(EXEMPT)) {
      expect(reason.length, `${file} 的例外必须写理由`).toBeGreaterThan(19)
      const stillOffends = read(file)
        .split('\n')
        .some(line => PALETTE_CLASS.test(line))
      expect(stillOffends, `${file} 已不含具名色阶，请把它从 EXEMPT 删掉`).toBe(true)
    }
  })

  it('深色底图专用的 on-scrim 档必须成对注册（缺一个就有人回去写 dark: 分支）', () => {
    const css = read('assets/css/main.css')
    for (const name of ['primary', 'info', 'success', 'warning', 'error']) {
      expect(css, `--color-${name}-on-scrim`).toContain(`--color-${name}-on-scrim:`)
    }
    // 混合基准仍是 var()：写死 hsl 数字等于又造一份与主题无关的假令牌
    expect(css).toMatch(/--color-primary-on-scrim:\s+color-mix\(in oklab, hsl\(var\(--primary\)\)/)
  })

  it('恒深品牌底必须注册并有真实消费点', () => {
    // auth 兜底渐变的中间色标如果退回 --primary，暗色模式那档是 #33BEFF，而这一层的文字全白，
    // 实测白字压上去只有 2.11:1；--primary-deep 是按黑混合 70% 得到的恒深档（两种模式都过 AA）。
    const css = read('assets/css/main.css')
    expect(css).toMatch(/--color-primary-deep:\s+color-mix\(in oklab, hsl\(var\(--primary\)\) 70%, black\)/)
    for (const page of ['pages/login.vue', 'pages/register.vue']) {
      expect(read(page), `${page} 的兜底渐变`).toContain('via-primary-deep')
      expect(read(page), `${page} 不得把恒白文字压在随模式变亮的 --primary 上`).not.toContain('via-primary to-black')
    }
  })

  it('实心语义底色不得配 alpha 悬停（前后台一起钉，这条与"是否公开页"无关）', () => {
    // bg-primary 上是白字，而 hover:bg-primary/90 是把底色往页面方向抬——抬到 90% 时白字只剩
    // 4.36:1（AA 要 4.5），悬停那一下反而比静止态更难读。悬停档见 --color-primary-hover。
    const files = PUBLIC_DIRS.flatMap(dir => walk(dir))
    const offenders: string[] = []
    for (const file of files) {
      const src = read(file)
      src.split('\n').forEach((line, i) => {
        for (const name of ['primary', 'destructive', 'success', 'info', 'warning', 'error']) {
          const solid = new RegExp(`\\bbg-${name}(?![-\\w/])`).test(line)
          const alphaHover = new RegExp(`(?:hover|active):bg-${name}/\\d`).test(line)
          if (solid && alphaHover) offenders.push(`${file}:${i + 1} ${line.trim().slice(0, 110)}`)
        }
      })
    }
    expect(offenders, `改用 bg-X-hover 令牌：\n${offenders.join('\n')}`).toHaveLength(0)
  })

  it('悬停档令牌必须在场并且按 var() 派生', () => {
    const css = read('assets/css/main.css')
    for (const name of ['primary', 'destructive', 'success']) {
      expect(css, `--color-${name}-hover`).toMatch(
        new RegExp(`--color-${name}-hover:\\s+color-mix\\(in oklab, hsl\\(var\\(--${name}\\)\\) 88%, black\\)`)
      )
    }
    // 消费点也得真的在（注册了没人读 = 下一轮又有人回去写 /90）
    expect(read('components/ui/button/index.ts')).toContain('hover:bg-primary-hover')
    expect(read('components/ui/badge/index.ts')).toContain('hover:bg-destructive-hover')
  })
})
