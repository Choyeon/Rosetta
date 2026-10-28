/**
 * 首页轮播「文字色调」（`HeroSlide.text_color`）消费侧契约（批次 #28）。
 *
 * 这一列后端很早就交付到底（列 + Create/Update/Response + 匿名口 `GET /api/hero/slides`），
 * 但首页把 hero 文案的六个元素全写成白字、三条压暗黑渐变无条件叠放，后台也没有开关——
 * 于是亮底图（雪景/白墙/浅灰渐变）上是一行压在亮底上的白字，唯一"能调"的遮罩强度又被
 * 那三层装饰渐变绑死。
 *
 * 这个 spec 读源文本而不是跑组件，钉四件事：
 * 1. 写侧（后台表单）与读侧（首页 `HeroSlideApi` + tone computed）都接上了这一列；
 * 2. 着色类**只能**从 `heroToneClasses` 来——模板里再留一份 `text-white` 硬编码，
 *    深字档就永远压不过它（Tailwind 原子类同权重，谁在后面谁赢靠的是构建顺序，不可依赖）；
 * 3. 缺省档（light）必须与今天线上的观感逐条相等，接通这个开关不得顺手换一次皮肤；
 * 4. 布局类（`min-h-11`、断点字号、`[overflow-wrap:anywhere]`）留在模板字面量里——
 *    它们是 `heroMobileLayout.spec.ts` 逐条钉住的对象，搬进 computed 那份契约会静默失效。
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const page = readFileSync(resolve(process.cwd(), 'pages/index.vue'), 'utf8')
const admin = readFileSync(resolve(process.cwd(), 'pages/admin/content/hero.vue'), 'utf8')

/** hero section 那一段模板（与 heroMobileLayout.spec.ts 同口径的切片）。 */
const heroBlock = page.slice(
  page.indexOf('v-if="heroEnabled"'),
  page.indexOf('data-editorial-section="pinned"')
)

/** `heroToneClasses` computed 的函数体。 */
const toneMap = page.slice(
  page.indexOf('const heroToneClasses = computed'),
  page.indexOf('let heroTimer')
)

describe('首页 Hero 文字色调：接线', () => {
  it('读侧接口声明了这一列（不声明就只是 TypeScript 看不见它）', () => {
    expect(page).toMatch(/text_color\?: 'light' \| 'dark' \| null/)
  })

  it('色调判定只认 dark，其余（含 null / undefined / 历史脏值）一律按 light 走', () => {
    expect(page).toMatch(/heroSlide\.value\?\.text_color === 'dark' \? 'dark' : 'light'/)
  })

  it('section 上带 data-hero-tone，线上抽查才有可断言的落点', () => {
    expect(heroBlock).toMatch(/:data-hero-tone="heroTone"/)
  })

  it('写侧后台有开关，且保存载荷带上这一项', () => {
    expect(admin).toMatch(/const TONE_OPTIONS = \[/)
    expect(admin).toMatch(/text_color: 'light' \| 'dark'/)
    expect(admin).toMatch(/form\.text_color = slide\.text_color \?\? 'light'/)
    expect(admin).toMatch(/text_color: form\.text_color,/)
  })
})

describe('首页 Hero 文字色调：着色类单源', () => {
  it('六个文案元素的着色类全部来自 heroToneClasses', () => {
    for (const key of ['kicker', 'title', 'subtitle', 'caption', 'secondaryCta']) {
      expect(heroBlock, key).toContain(`heroToneClasses.${key}`)
    }
  })

  it('模板里不得再留写死的白字/黑纱类（深字档压不过它）', () => {
    // 主按钮是 bg-primary、HUD（缩略图与提示条）自带深色底，都不在这一列管辖内，
    // 所以只查 hero 文案那几行：它们必须已经是 :class 数组形态。
    for (const forbidden of [
      'class="mt-5 font-display',
      'class="mt-5 max-w-2xl',
      'class="mt-3 text-sm text-white',
      'class="inline-flex w-fit items-center gap-2 rounded-full border border-white'
    ]) {
      expect(heroBlock, forbidden).not.toContain(forbidden)
    }
  })

  it('三条装饰性压暗渐变在深字档整组撤掉（深字压在黑纱上等于两边都看不清）', () => {
    expect(heroBlock).toMatch(/v-if="!isDarkTone"\s*\n\s*class="absolute inset-0 bg-gradient-to-t from-black\/75/)
    // editorial 那条与非 editorial 那两条包在同一层 `v-if="!isDarkTone"` 的 template 内：
    // 把 isDarkTone 并进原来的 `v-if="isEditorialTheme"` 会让 v-else 分支在 editorial+dark
    // 时反而成立，等于换了个方式继续叠黑纱。
    expect(heroBlock).toMatch(/<template v-if="!isDarkTone">/)
    expect(heroBlock).toMatch(/v-if="isEditorialTheme"\s*\n\s*class="absolute inset-0 pointer-events-none bg-gradient-to-b from-black\/18/)
    expect(heroBlock).not.toMatch(/v-if="isEditorialTheme && !isDarkTone"/)
  })

  it('逐张可调的可读性遮罩不受色调影响（那是与色调正交的另一项配置）', () => {
    expect(heroBlock).toMatch(/:style="heroOverlayStyle"/)
  })
})

describe('首页 Hero 文字色调：缺省档不得换皮肤', () => {
  /** light 分支的每一条都必须等于接通前模板里写死的那串，逐字比对。 */
  const LIGHT_BASELINE: Record<string, string> = {
    kicker: 'border-white/15 bg-black/35 text-white/70',
    title: 'text-white drop-shadow-[0_2px_14px_rgba(0,0,0,0.55)]',
    subtitle: 'text-white/85 drop-shadow-[0_1px_6px_rgba(0,0,0,0.5)]',
    caption: 'text-white/70',
    secondaryCta: 'border-white/20 bg-white/10 text-white hover:bg-white/20'
  }

  for (const [key, baseline] of Object.entries(LIGHT_BASELINE)) {
    it(`${key} 的 light 分支与接通前逐字一致`, () => {
      expect(toneMap, key).toContain(`: '${baseline}'`)
    })
  }

  it('dark 分支给的是深字，且阴影换成白垫（亮底图上黑色投影等于又糊一层灰）', () => {
    for (const key of Object.keys(LIGHT_BASELINE)) {
      const matched = toneMap.match(new RegExp(`${key}:\\s*dark[\\s\\S]{0,60}?\\?\\s*'([^']+)'`))
      const darkValue = matched ? matched[1] : ''
      expect(darkValue, key).toMatch(/text-(slate-900|black)/)
      expect(darkValue, key).not.toMatch(/text-white/)
    }
  })
})

describe('首页 Hero 文字色调：布局类留在模板', () => {
  it('两个 CTA 的高度与居中层仍是字面量（heroMobileLayout.spec.ts 钉的是模板文本）', () => {
    const hits = heroBlock.match(/min-h-11 items-center justify-center/g) ?? []
    expect(hits.length).toBe(2)
  })

  it('标题的窄屏降档与 overflow-wrap 仍在同一条 class 数组字面量里', () => {
    expect(heroBlock).toMatch(/'mt-5 font-display text-\[1\.75rem\] leading-\[1\.15\] sm:text-4xl md:text-6xl font-black tracking-tight \[overflow-wrap:anywhere\]'/)
  })

  it('文案层的 flex 列与 container 布局没被动过', () => {
    expect(heroBlock).toMatch(/flex flex-1 items-center container/)
    expect(heroBlock).toMatch(/'relative isolate overflow-hidden flex flex-col'/)
  })
})
