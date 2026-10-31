/**
 * 后台评论列表 parent_ref / user_ref 的四段对账（批次 #151）。
 *
 * `GET /api/admin/comments` 与 `PATCH /api/admin/comments/{id}` 一直在投影这两个嵌套对象，
 * `CommentAdminItemDoc` 也声明了它们，但前端此前一个消费点都没有 —— 字段活着、没人读，
 * 改它没人知道，删它也没人报警（批次 #149 / #150 拆的正是这一族）。
 *
 * 本 spec 双向钉住：
 * 1. 后端确实产出该键（admin.py 的投影 + admin_reads.py 的文档模型都声明）；
 * 2. 前端 type 声明该键；
 * 3. 模板真的渲染该键（不是只在 type 里挂着）；
 * 4. 从 `user_ref` 上读走的子键都必须在后端文档模型里声明，
 *    且 `AdminCommentUserRef` 里声明的每个键都必须被模板读走 —— 两边都不许留死字段。
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..')
const REPO = join(ROOT, '..')

const adminApi = readFileSync(join(REPO, 'backend', 'api', 'admin.py'), 'utf-8')
const adminReads = readFileSync(join(REPO, 'backend', 'schemas', 'admin_reads.py'), 'utf-8')
const manage = readFileSync(join(ROOT, 'composables', 'useAdminManage.ts'), 'utf-8')
const listPart = readFileSync(
  join(ROOT, 'pages', 'admin', 'interaction', '_parts', 'CommentListContent.vue'),
  'utf-8'
)

/** 取 `class X` 到下一个 `class` 之间的类体（文件最后一个类没有后继边界，取到文件尾） */
function classBody(name: string): string {
  const head = `class ${name}`
  const start = adminReads.indexOf(head)
  expect(start, `后端缺少 ${name}`).toBeGreaterThan(-1)
  const rest = adminReads.slice(start + head.length)
  const next = rest.search(/^class /m)
  return next === -1 ? rest : rest.slice(0, next)
}

/** 类体里声明的字段名（Python 四空格缩进的 `name: type`） */
function declaredFields(body: string): string[] {
  return [...body.matchAll(/^ {4}([A-Za-z_]\w*)\s*:/gm)].map(m => m[1]!)
}

/** TS interface 体里声明的键名（两空格缩进；doc 注释行以 `*` 起头，不会误命中） */
function tsDeclaredFields(body: string): string[] {
  return [...body.matchAll(/^ {2}([A-Za-z_]\w*)\s*:/gm)].map(m => m[1]!)
}

/** 模板从 `comment.<ref>` 上读走的子键 */
function consumedSubKeys(refName: string): string[] {
  const re = new RegExp(`comment\\.${refName}\\??\\.([A-Za-z_]\\w*)`, 'g')
  return [...listPart.matchAll(re)].map(m => m[1]!)
}

const userRefDocFields = declaredFields(classBody('CommentUserRefDoc'))
const parentRefDocFields = declaredFields(classBody('CommentParentRefDoc'))

describe('admin comment refs wiring', () => {
  it('backend emits parent_ref / user_ref and both doc models declare them', () => {
    expect(adminApi).toContain('"parent_ref": parent_ref')
    expect(adminApi).toContain('"user_ref": user_data')
    expect(parentRefDocFields).toEqual(expect.arrayContaining(['id', 'nickname']))
    expect(userRefDocFields).toEqual(
      expect.arrayContaining(['username', 'is_active', 'is_staff'])
    )
  })

  it('frontend row type declares both refs', () => {
    const row = manage.slice(
      manage.indexOf('export interface AdminCommentRow'),
      manage.indexOf('export interface AdminComment extends')
    )
    expect(row).toContain('parent_ref?: AdminCommentParentRef | null')
    expect(row).toContain('user_ref?: AdminCommentUserRef | null')
  })

  it('template renders both refs (not just declares them)', () => {
    expect(consumedSubKeys('parent_ref').length).toBeGreaterThan(0)
    expect(listPart).toContain('回复 @{{ comment.parent_ref.nickname')
    expect(consumedSubKeys('user_ref').length).toBeGreaterThan(0)
    // 两条徽标：停用账号与本站成员 —— 文案即消费证据
    expect(listPart).toContain('账号已停用')
    expect(listPart).toContain('本站成员')
  })

  it('every user_ref sub-key read by the template is declared by the backend doc', () => {
    for (const key of consumedSubKeys('user_ref')) {
      expect(userRefDocFields, `前端读了后端没声明的 user_ref.${key}`).toContain(key)
    }
    for (const key of consumedSubKeys('parent_ref')) {
      expect(parentRefDocFields, `前端读了后端没声明的 parent_ref.${key}`).toContain(key)
    }
  })

  it('AdminCommentUserRef declares no field the template does not read', () => {
    const iface = manage.slice(
      manage.indexOf('export interface AdminCommentUserRef'),
      manage.indexOf('审核列表的共用行形状')
    )
    const declared = tsDeclaredFields(iface)
    expect(declared.length).toBeGreaterThan(0)
    const consumed = consumedSubKeys('user_ref')
    for (const key of declared) {
      expect(consumed, `AdminCommentUserRef.${key} 是新的死声明`).toContain(key)
    }
  })
})
