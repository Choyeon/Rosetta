// 短代码管理面板契约门禁：这条页面前后端各有三处"说了不算"的口径——
// 标签名正则必须与后端请求模型同源（否则管理员白填一次）、插件归属行不得出现
// 任何可写按钮（409 是护栏不是 bug）、预览结果必须是纯文本插值（handler 输出
// 是运营期数据，v-html 等于给后台开一个绕过框架的注入口）。
// 全部走源码静态断言：本页依赖 Nuxt 自动导入，挂载成本高于其判定价值。
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const root = process.cwd().replace(/[\\/]$/, '')
const PAGE = `${root}/pages/admin/system/shortcodes.vue`
const MENU = `${root}/config/admin-menu.ts`
const BACKEND = `${root}/../backend/api/shortcodes.py`

const page = readFileSync(PAGE, 'utf8')
const tagPatternSource = page.match(/const TAG_PATTERN = \/(.+)\/$/m)?.[1] ?? ''

describe('标签名校验与后端同源', () => {
  it('TAG_PATTERN 与 ShortcodeRegisterRequest.tag.pattern 同构', () => {
    expect(tagPatternSource).not.toBe('')

    const backendPattern = readFileSync(BACKEND, 'utf8')
      .match(/tag: str = Field\([^)]*pattern=r"(\^.*?\$)"/)?.[1]
    expect(backendPattern).toBeTruthy()
    // 后端在字符类里写 `\-`（Pydantic 侧需要转义），JS 侧同一位置写 `-`，
    // 归一化后两者必须逐字符相等，否则两侧接受集合就会分叉。
    expect(tagPatternSource).toBe((backendPattern ?? '').replace(/\\-/g, '-'))
  })

  it('空标签、含斜杠、以数字开头的标签一律判非法', () => {
    const local = new RegExp(tagPatternSource)
    for (const bad of ['', '2cta', 'a b', 'tag/x', '<script>']) {
      expect(local.test(bad)).toBe(false)
    }
    for (const good of ['cta', '_warn', 'my-button2']) {
      expect(local.test(good)).toBe(true)
    }
  })
})

describe('预览结果必须是纯文本', () => {
  it('整页不出现 v-html', () => {
    // 头部契约注释里就写着"绝不 v-html"，不剥注释会自判失败（同 adminNoDeadAffordance 的坑）
    expect(page.replace(/<!--[\s\S]*?-->/g, '')).not.toMatch(/v-html/)
  })

  it('渲染结果以 {{ }} 插值进 <pre>', () => {
    expect(page).toMatch(/<pre[\s\S]*?\{\{ previewResult\.rendered \}\}<\/pre>/)
  })
})

describe('插件归属行只读', () => {
  it('item.plugin 分支内不含任何 Button', () => {
    const branch = page.slice(
      page.indexOf('v-if="item.plugin"'),
      page.indexOf('v-else-if="pendingDelete')
    )
    expect(branch.length).toBeGreaterThan(0)
    expect(branch).not.toMatch(/<Button/)
    expect(branch).toMatch(/随插件管理/)
  })

  it('删除只作用于模板行：removeTemplate 仅出现在确认分支', () => {
    expect(page.match(/@click="removeTemplate/g)).toHaveLength(1)
    expect(page.match(/@click="pendingDelete = item\.tag"/g)).toHaveLength(1)
  })
})

describe('请求口径', () => {
  it('全部经 apiFetch，且路径不带 /api 前缀', () => {
    expect(page).not.toMatch(/\$fetch\(/)
    expect(page).not.toMatch(/apiFetch[<(][^)]*'\/api\//)
    expect(page).toMatch(/LIST_URL = '\/admin\/shortcodes'/)
  })

  it('读列表按信封取 res.data（apiFetch 不解信封）', () => {
    expect(page).toMatch(/list\.value = res\.data\n/)
  })

  it('预览是唯一 POST /admin/shortcodes，注册走 /register', () => {
    expect(page).toMatch(/LIST_URL,\s*\{ method: 'POST'/)
    expect(page).toMatch(/REGISTER_URL,\s*\{/)
  })
})

describe('菜单与页面同步', () => {
  it('/admin/system/shortcodes 已登记在侧边栏单一数据源', () => {
    const menu = readFileSync(MENU, 'utf8')
    expect(menu).toMatch(/'\/admin\/system\/shortcodes'/)
  })

  it('本页声明 ssr:false + layout:admin（/admin/** 是 SPA 反选区）', () => {
    expect(page).toMatch(/definePageMeta\(\{ ssr: false, layout: 'admin' \}\)/)
  })
})
