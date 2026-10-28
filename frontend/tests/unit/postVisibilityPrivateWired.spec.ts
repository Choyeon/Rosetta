/**
 * 文章「可见性 · 私密档」后台消费侧契约（批次 #29）。
 *
 * `Post.visibility` 长期是"写进去没人读"：编辑器能选三档、列在表上、schema 也收，
 * 但创建口构造 ORM 对象时丢了键、公开读口从不做过滤——作者点"私密"、后台显示保存成功，
 * 文章却照常出现在列表 / RSS / sitemap / 热榜里。后端现已把判定抽在
 * `backend/services/post_access.py`（对象级 `post_is_publicly_visible` + 集合级
 * `private_posts_excluded`），本 spec 钉前端这一侧不许重新断链：
 *
 * 1. 列表行类型必须声明 `visibility`——不声明就只是 TypeScript 看不见它，标记位无从写起；
 * 2. 私密/密码标记只有一个落点。同一行渲染两遍会让"哪一档"变成两个地方的两条真相；
 * 3. 标记必须挂在「状态」列而不是并进状态徽标：「已发布 + 私密」是合法组合，
 *    合成一个 Badge 就看不出这层；
 * 4. 表单必须**始终**发送 `visibility`——后端 PUT 是 exclude_unset 增量语义，
 *    省略键等于"改回公开"永远落不了库。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const listPage = readFileSync(
  resolve(process.cwd(), 'pages/admin/content/posts/index.vue'),
  'utf8'
)
const rowType = readFileSync(resolve(process.cwd(), 'composables/useAdminManage.ts'), 'utf8')
const form = readFileSync(resolve(process.cwd(), 'components/admin/PostForm.vue'), 'utf8')

/** 状态列那一格的模板切片。 */
const statusCell = listPage.slice(
  listPage.indexOf('<template #cell-status="{ row }">'),
  listPage.indexOf('<template #cell-is_pinned=')
)

describe('文章可见性：后台列表消费侧', () => {
  it('列表行类型声明了 visibility', () => {
    expect(rowType).toMatch(/visibility\?: 'public' \| 'password' \| 'private'/)
  })

  it('私密与密码两档在状态列各有标记', () => {
    expect(statusCell).toContain(`(row as Post).visibility === 'private'`)
    expect(statusCell).toContain(`(row as Post).visibility === 'password'`)
    expect(statusCell).toContain('私密')
    expect(statusCell).toContain('密码')
  })

  it('标记位只有一个落点（整页对 visibility 的判定次数即标记的次数）', () => {
    const hits = listPage.match(/visibility === '(private|password)'/g) ?? []
    expect(hits).toHaveLength(2)
  })

  it('状态徽标与可见性标记同列但不同徽标：正交的两轴不许合并', () => {
    expect(statusCell).toContain(`(row as Post).status === 'published'`)
    expect(statusCell).toMatch(/flex flex-col[\s\S]*?visibility === 'private'/)
  })
})

describe('文章可见性：编辑器写侧', () => {
  it('保存载荷始终带 visibility', () => {
    expect(form).toMatch(/visibility: form\.visibility,/)
  })

  it('三档选项都在（少了 private 这一档就没有"作者自己留着看"的入口）', () => {
    for (const value of ['public', 'password', 'private']) {
      expect(form).toContain(`'${value}'`)
    }
  })
})
