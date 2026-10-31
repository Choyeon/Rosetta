/**
 * 批次 #147：`show_email` 的第四段（作者主页展示面）与两份掩码常量的对齐。
 *
 * 后端把"关掉开关"投影成 `***`（不是 null，见 `AuthorProfileResponse.email` 的必填设计），
 * 前端把它判成"没有邮箱"。这两处各自写一份字面量，任何一侧改动都会让另一侧静默失效——
 * 表现要么是 `mailto:***` 的死链，要么是"作者公开了邮箱却什么都看不见"。
 * 所以这一族的守卫跨语言对账：两侧常量的**字面量必须逐字符相同**。
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..')
const REPO = join(ROOT, '..')

const page = readFileSync(join(ROOT, 'pages', 'authors', '[username].vue'), 'utf-8')
const helper = readFileSync(join(REPO, 'backend', 'api', '_user_response_helper.py'), 'utf-8')

function templateOf(source: string): string {
  const start = source.indexOf('<template>')
  const end = source.lastIndexOf('</template>')
  expect(start).toBeGreaterThanOrEqual(0)
  expect(end).toBeGreaterThan(start)
  return source.slice(start, end)
}

describe('两份掩码常量同值', () => {
  const backendMask = /EMAIL_MASK\s*=\s*"([^"]*)"/.exec(helper)?.[1]
  const frontendMask = /const EMAIL_MASK = '([^']*)'/.exec(page)?.[1]

  it('两侧都各自定义了掩码（恒真守卫先排除：任一份被删掉就是这条红）', () => {
    expect(backendMask).toBeTruthy()
    expect(frontendMask).toBeTruthy()
  })

  it('逐字符相等，且都不是空串', () => {
    expect(frontendMask).toBe(backendMask)
    expect(backendMask?.length).toBeGreaterThan(0)
  })

  it('后端遮蔽走单源常量，不再散写裸字面量', () => {
    expect(helper).toContain('response.email = EMAIL_MASK')
    expect(helper).not.toContain('response.email = "***"')
  })
})

describe('作者页取数形状与判据', () => {
  it('AuthorProfile 接口带出 email（资料口投影的键在这里有声明）', () => {
    const block = page.slice(page.indexOf('interface AuthorProfile'), page.indexOf('interface AuthorPostRow'))
    expect(block).toContain('email?: string | null')
  })

  it('判据是"不是掩码且像邮箱"，不是简单的非空', () => {
    const fn = page.slice(page.indexOf('const publicEmail'))
    const body = fn.slice(0, 600)
    expect(body).toContain('raw === EMAIL_MASK')
    expect(body).toContain('raw.includes(\'@\')')
    // scheme / 标记字符进 href 等于把库里的脏值当真值用
    expect(body).toMatch(/\/\[[^\]]*<[^/]*\]\//)
  })
})

describe('渲染面', () => {
  const tpl = templateOf(page)
  it('mailto 链接绑定的是判据结果，而不是裸字段', () => {
    expect(tpl).toContain(':href="`mailto:${publicEmail}`"')
    expect(tpl).not.toContain('mailto:${profile')
  })

  it('图标走 @lucide/vue 组件（不抄第四份字形数据）', () => {
    expect(tpl).toContain('<Mail class="size-3.5" />')
    expect(page).toContain('import { ChevronLeft, ChevronRight, ExternalLink, Globe, Mail, MessageSquare, RefreshCw, UserRound } from \'@lucide/vue\'')
    expect(page).not.toMatch(/\bd:\s*'[MJ]/)
  })

  it('文案用 t() 带默认值，与同排 website / GitHub 一个写法', () => {
    expect(tpl).toContain('{{ t(\'authors.email\', \'邮箱\') }}')
  })

  it('社交行只有邮箱时也展开（否则公开邮箱的作者看不到这一行）', () => {
    expect(tpl).toContain('v-if="profile?.website || profile?.github || publicEmail"')
  })
})
