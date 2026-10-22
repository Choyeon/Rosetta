/**
 * 批次 #69/#70 契约：密码表单的"看得见失败"与"语言真相只有 URL 前缀"。
 *
 * 两类真实缺陷各钉一条：
 *   ① 「点了修改密码没有任何反应」——失败只出现在右下角 3.6 秒即消失的 toast 里，
 *      而密码强度规则一次返回多条；验证码输入框写 `maxlength="6"` 时，粘贴
 *      "123 456" 会被静默截成 5 位，`/^\d{6}$/` 永不匹配、按钮保持禁用且不说明原因。
 *      所以反馈必须常驻在按钮上方（role=alert），禁用时必须给理由。
 *   ② 简体页面渲染繁体——三处来源：zh.json 里混进繁体文案；后端曾把 rosetta_lang
 *      cookie 排在 Accept-Language 之前；前端曾用 navigator/language 猜语言。
 *      cookie 那半由 `tests/test_i18n_language_precedence.py` 钉，这里钉另两处。
 */
import { describe, it, expect } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import process from 'node:process'
import { DEFAULT_LOCALE_CODE, localeCodeFromPath } from '@/lib/rosetta-themes'
import { extractApiErrorList, extractApiErrorMessage } from '@/lib/utils'

const ROOT = process.cwd().replace(/[\\/]$/, '')
const read = (p: string) => {
  expect(existsSync(`${ROOT}/${p}`), `${p} 不存在`).toBe(true)
  return readFileSync(`${ROOT}/${p}`, 'utf8')
}
/** 只取真正的代码行：注释里的 "禁止读 navigator" 是禁令文本，不是违规。 */
const codeLines = (src: string) => src
  .split('\n')
  .map(l => l.trim())
  .filter(l => l && !l.startsWith('//') && !l.startsWith('*') && !l.startsWith('/*') && !l.startsWith('<!--'))

describe('localeCodeFromPath：URL 前缀 → 语言码', () => {
  it.each([
    ['/en/posts/abc', 'en'],
    ['/ja', 'ja'],
    ['/zh_Hant/posts/abc', 'zh_Hant'],
    ['/zh_Hant', 'zh_Hant'],
    ['/posts/abc', DEFAULT_LOCALE_CODE],
    ['/', DEFAULT_LOCALE_CODE],
    // 以 en 开头的普通路径不能被当成前缀
    ['/encyclopedia', DEFAULT_LOCALE_CODE],
    ['/en.html', DEFAULT_LOCALE_CODE]
  ])('%s => %s', (path, expected) => {
    expect(localeCodeFromPath(path)).toBe(expected)
  })

  it('空路径回退默认语言（SSR 期不得抛异常）', () => {
    expect(localeCodeFromPath('')).toBe(DEFAULT_LOCALE_CODE)
    expect(localeCodeFromPath(undefined)).toBe(DEFAULT_LOCALE_CODE)
    expect(localeCodeFromPath(null)).toBe(DEFAULT_LOCALE_CODE)
  })
})

describe('接口语言不得由 navigator / localStorage 猜', () => {
  // 这三样记录的是"浏览器偏好/上次去的语言"，与"这一页/这次请求是什么语言"无关。
  // 实测表现：简体裸路径的页面发出英文或繁体请求，SSR 先渲简体、补拉后再翻回繁体。
  it.each(['composables/useApi.ts', 'plugins/site-title.global.ts'])(
    '%s 里不含 navigator.language / html-lang 猜测与 localStorage locale 读取',
    (p) => {
      const lines = codeLines(read(p))
      const bad = lines.filter(l =>
        /navigator\.language/.test(l)
        || /document\.documentElement\.lang/.test(l)
        || /localStorage\.getItem\(['"`]locale['"`]\)/.test(l)
      )
      expect(bad, `${p} 仍从浏览器猜语言：\n${bad.join('\n')}`).toEqual([])
    }
  )

  it('useApi 的客户端语言一律由当前路径推导', () => {
    const src = read('composables/useApi.ts')
    expect(codeLines(src).some(l => l.includes('localeCodeFromPath(')), 'currentLocale 未走 localeCodeFromPath').toBe(true)
  })
})

describe('zh.json 必须是简体：繁简成对字形扫描', () => {
  // TRAD/SIMP 逐位对齐，只收"简体永远写成另一个字形"的对子（裡/里、後/后、…），
  // 排除兩套写法相同的字（提、技、外），否则扫描会假报警。
  // 判定条件收紧为：该繁体字出现在 zh_Hant.json 里、且对应简体字出现在 zh.json 里，
  // 才纳入断言——保证钉住的都是本仓语言包真实用到的字。
  const TRAD = '們這裡裏後語說時間為與從會開關發愛學數樣節義讓讀寫驗證碼網頁單標題類種動設個區圖書庫內聯統計轉輸縮導頭銘備處復註態許論財貨質點龍專術務員價優傳壓場壞聲醫報歸風險費盜斷實遺際較強見簡橫門詞懸據棧磚鏡凍給幫賞車師攝驅絡維週帶筆構順極鳴織緊撐漸組習淺終綁廢載暫無資儲刪換敗選頂華試閉預覽該沒鏈籤讚錄訊請鎖錯稱電郵審過顯長還來參應鈕條檢視謝擇項確認記號賬歡續嘗並隱兩紙當訪權創顏篩掛裝啟級掃機變異鍵現夾遠檔達屬訂觀倉紅欄總調體編礎線礙貼驟測進環靈階產議絕離聽雲經僅補齊牆規須戶隨遷紹準額綱範職業憶誌獨適薦徑護樂側邊緒約偵憑詢舊難響'
  const SIMP = '们这里里后语说时间为与从会开关发爱学数样节义让读写验证码网页单标题类种动设个区图书库内联统计转输缩导头铭备处复注态许论财货质点龙专术务员价优传压场坏声医报归风险费盗断实遗际较强见简横门词悬据栈砖镜冻给帮赏车师摄驱络维周带笔构顺极鸣织紧撑渐组习浅终绑废载暂无资储删换败选顶华试闭预览该没链签赞录讯请锁错称电邮审过显长还来参应钮条检视谢择项确认记号账欢续尝并隐两纸当访权创颜筛挂装启级扫机变异键现夹远档达属订观仓红栏总调体编础线碍贴骤测进环灵阶产议绝离听云经仅补齐墙规须户随迁绍准额纲范职业忆志独适荐径护乐侧边绪约侦凭询旧难响'

  it('繁简表逐位对齐', () => {
    expect(TRAD.length, 'TRAD 与 SIMP 长度不一致').toBe(SIMP.length)
    for (let i = 0; i < TRAD.length; i++) {
      expect(TRAD[i], `第 ${i} 位繁简同形，不该进表`).not.toBe(SIMP[i])
    }
  })

  it('zh.json 里没有任何本仓用到的繁体字形', () => {
    const zhRaw = read('i18n/locales/zh.json')
    const hantRaw = read('i18n/locales/zh_Hant.json')
    const leaks: string[] = []
    for (let i = 0; i < TRAD.length; i++) {
      const t = TRAD[i]
      const s = SIMP[i]
      if (hantRaw.includes(t) && zhRaw.includes(s) && zhRaw.includes(t)) leaks.push(`${t}(应为 ${s})`)
    }
    expect(leaks, `zh.json 混入繁体，简体页面会渲染出繁体文案：\n${leaks.join('\n')}`).toEqual([])
  })

  it('已修复的三处繁体文案保持简体', () => {
    const zh = JSON.parse(read('i18n/locales/zh.json')) as Record<string, Record<string, string>>
    expect(zh.about.mottoLabel).toBe('座右铭')
    expect(zh.forgotPassword.resendWarn).toContain('验证码')
    expect(zh.forgotPassword.whyNeedCode).toContain('6 位')
    expect(zh.account.passwordFieldsRequired).toContain('密码')
  })
})

describe('四语都带上新增反馈文案', () => {
  const KEYS: Array<[string, string]> = [
    ['forgotPassword', 'resendWarn'],
    ['forgotPassword', 'whyNeedCode'],
    ['forgotPassword', 'whyNeedPassword'],
    ['account', 'passwordFieldsRequired']
  ]
  it.each(['zh', 'en', 'ja', 'zh_Hant'])('%s 四键齐全且非空', (locale) => {
    const json = JSON.parse(read(`i18n/locales/${locale}.json`)) as Record<string, Record<string, string>>
    for (const [block, key] of KEYS) {
      expect(json[block]?.[key], `${locale}.${block}.${key} 缺失`).toBeTruthy()
    }
  })
})

describe('extractApiErrorList：多条失败一次取全', () => {
  it('errors[] 为对象形状（AGENTS §7.2 契约）', () => {
    const body = {
      success: false,
      message: '提交失败',
      errors: [{ field: 'password', message: '密码至少 8 位', type: 'value_error' }]
    }
    expect(extractApiErrorList(body)).toEqual(['提交失败', '密码至少 8 位'])
  })

  // 真实分歧：password_policy.validate_password 返回 list[str]，而 main.py 的
  // HTTPException handler 把 dict 信封的键原样透出，所以 errors 是裸字符串数组。
  it('errors[] 为字符串形状（密码策略多条强度规则）', () => {
    const body = { message: '密码不符合要求', errors: ['至少 8 位', '需含大小写', '需含数字'] }
    expect(extractApiErrorList(body)).toEqual(['密码不符合要求', '至少 8 位', '需含大小写', '需含数字'])
  })

  it('去重、忽略空串与非对象载荷', () => {
    expect(extractApiErrorList({ message: '重复', errors: ['重复', '', { message: '重复' }, 42] })).toEqual(['重复'])
    expect(extractApiErrorList(null)).toEqual([])
    expect(extractApiErrorList('string')).toEqual([])
  })

  it('extractApiErrorMessage 对两种形状都取到首条', () => {
    expect(extractApiErrorMessage({ errors: ['裸字符串优先'] }, '兜底')).toBe('裸字符串优先')
    expect(extractApiErrorMessage({ errors: [{ message: '对象形状' }] }, '兜底')).toBe('对象形状')
    expect(extractApiErrorMessage({}, '兜底文案')).toBe('兜底文案')
  })
})

describe('两个密码表单：常驻反馈 + 不因截断而静默禁用', () => {
  it('forgot-password.vue 不用 maxlength 截断验证码，失败列在按钮上方', () => {
    const src = read('pages/forgot-password.vue')
    expect(src).not.toMatch(/maxlength=["']6["']/)
    expect(src).toContain('extractApiErrorList')
    expect(src).toContain('role="alert"')
    expect(src).toContain('disabledReason')
    // 只留数字：sanitize 在写入 model 前完成，而不是靠原生 maxlength 截
    expect(codeLines(src).some(l => l.includes('replace(/\\D')), '验证码输入未做数字过滤').toBe(true)
  })

  it('account/settings.vue 修改密码失败常驻显示，空字段有明确提示', () => {
    const src = read('pages/account/settings.vue')
    expect(src).toContain('passwordFailures')
    expect(src).toContain('account.passwordFieldsRequired')
    expect(src).toContain('extractApiErrorList')
    expect(src).toContain('role="alert"')
  })

  it('个人中心标题不再把语言码烘进 <title>', () => {
    expect(read('pages/account/index.vue')).not.toMatch(/title: `\$\{t\('account\.title'\)\} · \$\{locale\.value\}`/)
  })
})
