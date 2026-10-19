/**
 * 本地化取值单源守卫：`pickLocalizedText` 是"从后端 i18n dict 里挑当前语言的字符串"的唯一口径。
 *
 * 为什么用测试来守：本仓曾有 14 份手写副本，分成 4 种回落语义。其中 6 处（文章详情、
 * 独立页、分类/标签详情、作者主页、顶级 catchall）用 `obj[key] ?? …`，遇到库里
 * `{ "zh": "标题", "en": "" }` 这种脏数据时——当前语言命中空串就渲染成**空白标题**，
 * 而另外 8 处按真值判定的副本会回落到有内容的那份。同一个分类名在列表页有字、
 * 详情页没有字，就是这么来的。这里把口径钉死，并扫描页面侧不得再出现块状副本。
 *
 * 同文件还守两件事：① 不得再出现 `??` 口径的 dict 取值（下面那个用例逐条扫描）；
 * ② `MONTH_TABLE` 是月份短名的唯一清单 —— 壁纸 composable 曾抄过两份（一份全名、
 * 一份 en 短名），改月名要改三处，且副本与 SSR 侧不一致会直接变成水合差异。
 */
import { describe, it, expect } from 'vitest'
import { readdirSync, readFileSync } from 'node:fs'
import process from 'node:process'
import { pickLocalizedText, MONTH_TABLE } from '@/composables/useI18nHelpers'

const ROOT = process.cwd().replace(/[\\/]$/, '')
const SCAN_DIRS = ['pages', 'components']

function walk(dir: string): string[] {
  const out: string[] = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = `${dir}/${entry.name}`
    if (entry.isDirectory()) {
      if (entry.name === 'node_modules' || entry.name.startsWith('.')) continue
      out.push(...walk(full))
    } else if (/\.(vue|ts)$/.test(entry.name)) out.push(full)
  }
  return out
}

describe('pickLocalizedText', () => {
  it('当前语言精确命中', () => {
    expect(pickLocalizedText({ zh: '中文', en: 'English' }, 'en')).toBe('English')
  })

  it('当前语言为空串时必须回落，不能渲染空白（旧 6 处 `??` 副本的缺陷）', () => {
    expect(pickLocalizedText({ zh: '标题', en: '' }, 'en')).toBe('标题')
    expect(pickLocalizedText({ zh: '', en: '' }, 'zh')).toBe('')
  })

  it('zh ↔ zh_Hant 互通：后端只存一份繁体时简体中文也有字', () => {
    expect(pickLocalizedText({ zh_Hant: '繁體', en: 'English' }, 'zh')).toBe('繁體')
    expect(pickLocalizedText({ zh: '简体', en: 'English' }, 'zh_Hant')).toBe('简体')
  })

  it('未命中语言时取第一个非空值，跳过 null / 数字 / 空白键', () => {
    expect(pickLocalizedText({ fr: null, de: 7, ja: '日本語' }, 'en')).toBe('日本語')
  })

  it('字符串原文直接返回；空串与 null 用 fallback', () => {
    expect(pickLocalizedText('原文', 'en')).toBe('原文')
    expect(pickLocalizedText('', 'en', '兜底')).toBe('兜底')
    expect(pickLocalizedText(null, 'en', '兜底')).toBe('兜底')
    expect(pickLocalizedText(undefined, 'en', '兜底')).toBe('兜底')
    expect(pickLocalizedText({}, 'en', '兜底')).toBe('兜底')
  })

  it('locale 缺失（SSR 期 i18n 未就绪）也不炸，直接走回落', () => {
    expect(pickLocalizedText({ zh: '中文' }, null)).toBe('中文')
    expect(pickLocalizedText({ zh: '中文' }, undefined)).toBe('中文')
  })

  it('非字符串标量转成文本而不是留白', () => {
    expect(pickLocalizedText(42, 'en')).toBe('42')
  })
})

describe('页面侧不得自带块状 pick 副本', () => {
  it('pages/** 与 components/** 里的 pickLocalized / pickStr 一律单行委托给 pickLocalizedText', () => {
    const offenders: string[] = []
    for (const sub of SCAN_DIRS) {
      for (const file of walk(`${ROOT}/${sub}`)) {
        const text = readFileSync(file, 'utf8')
        // 块状副本：`const pickLocalized = (…) => {`。单行委托的箭头函数体不带 `{`。
        const blockCopy = /const (pickLocalized|pickStr)\s*=\s*\([^)]*\)(:\s*string)?\s*=>\s*\{/u
        if (blockCopy.test(text)) offenders.push(file.replace(`${ROOT}/`, ''))
      }
    }
    expect(
      offenders,
      `这些文件又手写了一份本地化取值逻辑，请改为 pickLocalizedText(val, locale.value)：${offenders.join(', ')}`
    ).toEqual([])
  })

  it('不得再出现 `??` 口径的 dict 取值（空串会被当命中，渲染成空白标题）', () => {
    // 两种签名都是"当前语言命中空串就直接返回空"：
    //   · `dict[locale.value] ?? …`
    //   · `… ?? Object.values(dict)…`
    // 唯一清单里没有豁免项 —— 需要与界面语言无关的取值（译文工具）请显式传固定 locale。
    // 例外只允许"查常量表"这类根本不是 i18n dict 的地方，逐条写明理由。
    const allowlist = new Set([
      // OG_LOCALE_MAP 是 locale → og:locale 的常量映射（zh → zh_CN），不是后端返回的 dict。
      'composables/useSeo.ts'
    ])
    const patterns = [
      /\[[^\]]*locale\.value\]\s*\?\?/u,
      /\?\?\s*Object\.values\(/u
    ]
    const offenders: string[] = []
    for (const sub of [...SCAN_DIRS, 'composables', 'lib']) {
      for (const file of walk(`${ROOT}/${sub}`)) {
        const rel = file.replace(`${ROOT}/`, '')
        const text = readFileSync(file, 'utf8')
        if (rel.endsWith('useI18nHelpers.ts') || allowlist.has(rel)) continue
        if (patterns.some(re => re.test(text))) offenders.push(rel)
      }
    }
    expect(offenders, `这些文件用 ?? 取 i18n dict，请改为 pickLocalizedText：${offenders.join(', ')}`).toEqual([])
  })
})

describe('月份名表单源', () => {
  it('MONTH_TABLE 覆盖四种语言、每项 12 个月，en 用短名', () => {
    expect(Object.keys(MONTH_TABLE).sort()).toEqual(['en', 'ja', 'zh', 'zh_Hant'])
    for (const [code, names] of Object.entries(MONTH_TABLE)) {
      expect(names, code).toHaveLength(12)
    }
    expect(MONTH_TABLE.en[0]).toBe('Jan')
    expect(MONTH_TABLE.zh[11]).toBe('12月')
  })

  it('除 useI18nHelpers 外不得自带第二份月名表', () => {
    // 表现：壁纸/活动这类页面自己抄一份 `['1月','2月',…]`，改月名要改 N 处，
    // 且抄的那份一旦与 SSR 侧不同就会在水合时两端文本不一致。
    const literal = /['"]1月['"]\s*,\s*['"]2月['"]|['"]Jan['"]\s*,\s*['"]Feb['"]/u
    const offenders: string[] = []
    for (const sub of [...SCAN_DIRS, 'composables', 'lib']) {
      for (const file of walk(`${ROOT}/${sub}`)) {
        const rel = file.replace(`${ROOT}/`, '')
        if (rel.endsWith('useI18nHelpers.ts')) continue
        if (literal.test(readFileSync(file, 'utf8'))) offenders.push(rel)
      }
    }
    expect(offenders, `这些文件又抄了一份月名表，请用 MONTH_TABLE：${offenders.join(', ')}`).toEqual([])
  })
})
