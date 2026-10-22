/**
 * OOBE 向导的跨端契约守卫。
 *
 * 扫的是**源码文本**而不是跑组件，因为这几条不变量都是「写法」层面的：
 * 一旦有人把 POST 改回 GET、或把用户名上限从 20 放宽到 32，类型检查和单测都
 * 不会报错，但线上会立刻出问题。
 *
 * 三条不变量的来由：
 * 1. 数据库口令绝不能出现在 query string —— GET /oobe/test-database 的
 *    `?db_password=...` 会被 Nginx / uvicorn / 浏览器历史 / APM 原样写进日志。
 * 2. 前端用户名正则必须与后端 `USERNAME_PATTERN` 同长。历史上前端写 {3,32}、
 *    后端是 {3,20}，21~32 位用户名前端放行、提交被 422 弹回，用户不知道错在哪。
 * 3. 新文案键必须四语齐全，否则切到缺失语种会直接显示 key 名。
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), 'utf8')

describe('OOBE 数据库口令不得进 query string', () => {
  it('useOOBE.testDatabase 必须走 POST（body 传参），不得用 params/query', () => {
    const src = read('composables/useOOBE.ts')
    // 只取这次 request(...) 的选项对象：跨函数扫描会把邻近的 checkUsername(params) 也算进来
    const m = src.match(/\/oobe\/test-database',\s*\{([\s\S]*?)\}\)/)
    expect(m, '未找到 /oobe/test-database 的 request 调用').toBeTruthy()
    const opts = m![1]!
    expect(opts).toContain('method: \'POST\'')
    expect(opts).toContain('body')
    expect(opts).not.toMatch(/\bparams\s*:/)
    expect(opts).not.toMatch(/\bquery\s*:/)
  })

  it('向导页面不得再拼带 db_password 的 URL', () => {
    const src = read('pages/oobe.vue')
    expect(src).not.toMatch(/db_password\s*=/)
    expect(src).not.toMatch(/dbPassword\s*\)\s*\)\s*\?/)
  })
})

describe('OOBE 用户名长度与后端同口径', () => {
  it('前端 USERNAME_RE 是 {3,20}，与 backend/core/oobe_constants.py 一致', () => {
    const backend = read('../backend/core/oobe_constants.py')
    const m = backend.match(/USERNAME_PATTERN\s*=\s*r?"([^"]+)"/)
    expect(m, '未能在 oobe_constants.py 里找到 USERNAME_PATTERN').toBeTruthy()

    const backendPattern = m![1]!
    const frontend = read('pages/oobe.vue')
    const fm = frontend.match(/USERNAME_RE\s*=\s*\/(.+?)\//)
    expect(fm, '未能在 oobe.vue 里找到 USERNAME_RE').toBeTruthy()

    // 两端都是 ^...$ 锚定形态，剥掉锚点后比正则体本身
    const strip = (s: string) => s.replace(/^\^/, '').replace(/\$$/, '')
    expect(strip(fm![1]!)).toBe(strip(backendPattern))
  })
})

describe('OOBE 向导页面接线', () => {
  const page = () => read('pages/oobe.vue')

  it('Step2 渲染密码强度条 + 逐条规则勾选态', () => {
    const src = page()
    expect(src).toContain('passwordStrength.rules')
    expect(src).toContain('passwordRuleLabel')
    expect(src).toContain('strengthPercent')
    expect(src).toContain('strengthBarClass')
  })

  it('Step2 用户名做远程预检，且后端不可达时不阻断', () => {
    const src = page()
    expect(src).toContain('checkUsername(')
    // 失败路径必须降级为 idle 而不是卡死在 checking/invalid
    expect(src).toMatch(/usernameCheckState\.value = 'idle'[\s\S]{0,120}usernameCheckMessage\.value = ''/)
  })

  it('Step3 的「测试连接」把全部连接参数放进 POST body', () => {
    const src = page()
    expect(src).toContain('runDbTest')
    const call = src.match(/await testDatabase\(\{([\s\S]*?)\}\)/)
    expect(call, '未找到 testDatabase 调用').toBeTruthy()
    for (const f of ['db_type', 'db_host', 'db_port', 'db_name', 'db_user', 'db_password', 'db_path']) {
      expect(call![1]).toContain(f)
    }
  })

  it('改动连接参数后作废旧结论（防止"测过了"误导用户）', () => {
    const src = page()
    expect(src).toContain('dbTestDirty')
    expect(src).toMatch(/watch\([\s\S]{0,200}siteForm\.dbPassword[\s\S]{0,200}dbTest\.value = \{ status: 'idle'/)
  })

  it('点安装前必须过服务端预检，error 级问题阻断安装', () => {
    const src = page()
    const fn = src.slice(src.indexOf('const finishSetup = async'))
    expect(fn).toContain('runPreflight()')
    expect(fn).toMatch(/if \(!ok\) return/)
  })

  it('安装失败展示结构化 error_code + hint，而不是裸异常', () => {
    const src = page()
    expect(src).toContain('installError')
    expect(src).toContain('evt.error_code')
    expect(src).toContain('installError.code')
    expect(src).toContain('installError.hint')
  })

  it('完成页给出凭据回执（用户名/邮箱/后台入口/站点地址）', () => {
    const src = page()
    expect(src).toContain('adminEntryUrl')
    expect(src).toContain('credTitle')
    expect(src).toContain('credNote')
  })

  it('分步提交失败要有可见反馈（不能只进 console）', () => {
    const src = page()
    expect(src).toContain('stepError')
    expect(src).not.toMatch(/catch \(e\) \{\s*console\.error\('OOBE step error:', e\)\s*\}/)
  })
})

/**
 * 安装观察这一段全部是 2026-10-22 审计实证的死控件 / 假回执：
 * 错误体被 request() 丢掉、重试键永远点不亮、清单在任务开始时就打勾、
 * 自动登录失败后完成页仍宣称"已自动为你登录"。四条都类型检查不出来，只能钉文本。
 */
describe('OOBE 安装观察与错误回执', () => {
  it('request() 必须保留后端错误体，并把它的 message 当首要文案', () => {
    const src = read('composables/useOOBE.ts')
    const start = src.indexOf('.catch((err: { status?: number')
    expect(start, '未找到 request() 的 catch 分支').toBeGreaterThan(-1)
    const catchBlock = src.slice(start, src.indexOf('.finally(() =>', start))
    expect(catchBlock).toContain('data: err.data')
    // 丢掉 data 后 err.message 只剩 ofetch 的 "Failed with status code 400"，
    // 安装失败横幅就再也读不到后端给的 error_code / hint / message
    expect(catchBlock).toMatch(/body\?\.message/)
  })

  it('失败横幅按 raw.data.* 取 error_code / hint（与上面同口径）', () => {
    const src = read('pages/oobe.vue')
    expect(src).toContain('raw.data?.error_code')
    expect(src).toContain('raw.data?.details?.hint')
  })

  it('安装中不得留不可达的重试按钮（真入口是底部「开始安装」）', () => {
    const src = read('pages/oobe.vue')
    expect(src).not.toContain('runInstallRetry')
    expect(src).not.toMatch(/:disabled="installing[^"]*"[^>]*@click="runInstall/)
    expect(src).toContain('runInstallCancel')
    // 四语里也不留这颗死键（四语键集合一致性检查抓不到"四份都残留"）
    for (const loc of ['zh', 'en', 'ja', 'zh_Hant']) {
      const dict = JSON.parse(read(`i18n/locales/${loc}.json`)) as { oobe: Record<string, string> }
      expect(dict.oobe, loc).not.toHaveProperty('installSnapshotRetryBtn')
    }
  })

  it('步骤清单只在同一条 step_id 的第二次播报时打勾', () => {
    const src = read('pages/oobe.vue')
    const fn = src.slice(src.indexOf('const onInstallProgress'), src.indexOf('// ===== R1-CEx-2'))
    expect(fn).toContain('installStepStarted.has(evt.step_id)')
    // 第一次播报＝该步刚开始：只能补勾它之前的步骤，把它自己标完成就是假进度
    expect(fn).toMatch(/installStepStarted\.add\(evt\.step_id\)[\s\S]{0,120}installStepList\.slice\(0, pos\)/)
    expect(fn).toMatch(/installStepStarted\.has\(evt\.step_id\)[\s\S]{0,80}cur\.done = true/)
  })

  it('复位必须走 resetInstallSteps（漏一处＝第二次安装从中间开始全绿）', () => {
    const src = read('pages/oobe.vue')
    expect(src.match(/resetInstallSteps\(\)/g)?.length ?? 0).toBeGreaterThanOrEqual(2)
    // 全仓只允许一处清勾，且它必须长在 resetInstallSteps 里
    expect((src.match(/s\.done = false/g) ?? []).length).toBe(1)
  })

  it('自动登录结果分岔文案，不得无条件宣称已登录', () => {
    const src = read('pages/oobe.vue')
    expect(src).toContain('adminAutoLoggedIn')
    expect(src).toContain('credAutoLoginFailed')
    const zh = JSON.parse(read('i18n/locales/zh.json')) as { oobe: Record<string, string> }
    expect(zh.oobe.credNote).not.toMatch(/自动/)
  })

  it('自动登录失败不得把整次安装判成失败', () => {
    const src = read('composables/useOOBE.ts')
    const loop = src.slice(src.indexOf('const loginRetries = 6'), src.indexOf('return data.value'))
    expect(loop).toContain('adminAutoLoggedIn.value = true')
    // fetchUser 抛出会一路冒到外层 catch，把"已装好"报成"安装失败"
    expect(loop).toMatch(/try \{\s*await authStore\.fetchUser\(\)/)
  })
})

describe('OOBE 新增文案键四语齐全', () => {
  const KEYS = [
    'pwWeak', 'pwFair', 'pwGood', 'pwStrong',
    'pwRuleLength', 'pwRuleLower', 'pwRuleUpper', 'pwRuleDigit', 'pwRuleBlocklist',
    'errUsernameFormat', 'errEmailFormat', 'errPasswordShort', 'errPasswordMismatch',
    'checkingUsername', 'usernameAvailable',
    'dbTestBtn', 'dbTesting', 'dbTestHint', 'dbTestStale', 'dbTestFailed', 'dbTestFailedHint',
    'preflightGoFix', 'preflightBlocked', 'preflightRunning',
    'installFailed', 'stepSaveFailed',
    'credTitle', 'credUsername', 'credEmail', 'credAdminUrl', 'credSiteUrl', 'credNote',
    'credAutoLoginOk', 'credAutoLoginFailed'
  ]

  const LOCALES = ['zh', 'en', 'ja', 'zh_Hant']

  for (const loc of LOCALES) {
    it(`${loc}.json 的 oobe 段包含全部新键`, () => {
      const dict = JSON.parse(read(`i18n/locales/${loc}.json`)) as { oobe?: Record<string, string> }
      const oobe = dict.oobe || {}
      const missing = KEYS.filter(k => typeof oobe[k] !== 'string' || !oobe[k])
      expect(missing, `${loc}.json 缺少: ${missing.join(', ')}`).toEqual([])
    })
  }

  it('四语键集合完全一致（缺一个语种就会直接把 key 名显示给用户）', () => {
    const sets = LOCALES.map((loc) => {
      const dict = JSON.parse(read(`i18n/locales/${loc}.json`)) as { oobe?: Record<string, string> }
      return new Set(Object.keys(dict.oobe || {}))
    })
    for (let i = 1; i < sets.length; i++) {
      const diff = [...sets[0]!].filter(k => !sets[i]!.has(k))
      expect(diff, `${LOCALES[i]} 相对 zh 缺键: ${diff.join(', ')}`).toEqual([])
    }
  })
})
