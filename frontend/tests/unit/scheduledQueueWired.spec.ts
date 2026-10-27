/**
 * 定时发布的三条路由（`backend/api/scheduled_posts.py`）此前没有任何页面消费：
 * 文章编辑页只能"排一次"，排完之后后台看不见队列、改不了时间、也取消不掉，
 * 到点没发出去才发现状态是 `scheduled` 而计划时间早已过去。
 * 守卫按"后端声明 ⇔ 页面实际请求"**集合相等**对账：新增一条口不接线会红，
 * 页面请求一条不存在的口也会红。
 *
 * 另四条口径是这个路由族特有的坑，页面改坏任意一条都会静默留下"说了会发、其实不发"的状态：
 * * 列表口**读之前先把到期文章推进成 published**（有写副作用），所以本页不得静默轮询；
 * * 改期回填与提交必须过 `lib/datetime` 换算（输入框是本地墙钟、库里是 UTC），
 *   直接 `slice(0, 16)` 会让东八区的"10:00 发布"在 18:00 生效；
 * * 后端对"不晚于现在"的时间是**就地发布**而不是报错，所以改期表单必须先过
 *   `scheduledAtError`，并把错误显示在字段上而不是只 toast；
 * * 取消一条 `scheduled` 会连带回到 `draft`（否则留下"等待发布但无计划时间"的死状态），
 *   提示语必须由服务端给出，页面不得自己写死"定时发布已取消"。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')
const page = readFileSync(resolve(ROOT, 'pages/admin/content/scheduled.vue'), 'utf8')
const backend = readFileSync(resolve(ROOT, '../backend/api/scheduled_posts.py'), 'utf8')
const menu = readFileSync(resolve(ROOT, 'config/admin-menu.ts'), 'utf8')

/** 两侧的路径段归一到同形：`{post_id}` 与 `${row.id}` 都算 `{id}`。 */
function canonical(path: string): string {
  return path
    .replace(/^\//, '')
    .replace(/\$\{[^}]*\}/g, '{id}')
    .replace(/\{[^}]*\}/g, '{id}')
}

/** 后端 `@router.get/put/delete("/...")` 声明的**去重路径**集合（PUT 与 DELETE 同路径，所以 3 条路由 = 2 个路径）。 */
function declaredPaths(): string[] {
  const out: string[] = []
  const re = /@router\.(get|put|delete)\(\s*"([^"]+)"/g
  let m: RegExpExecArray | null
  while ((m = re.exec(backend)) !== null) out.push(canonical(m[2]!))
  return [...new Set(out)]
}

/** 后端声明的路由数（verb + path）。 */
function declaredRouteCount(): number {
  return (backend.match(/@router\.(?:get|put|delete)\(\s*"[^"]+"/g) ?? []).length
}

/** 页面 `apiFetch('/x')` / `apiFetch<T>(\`/x/${id}/y\`)` 实际请求的路径集合。 */
function requestedPaths(): string[] {
  const out: string[] = []
  // 泛型实参不能漏（typecheck 要求 apiFetch<T>），否则接了线的页面会误报"端点没消费"。
  const re = /apiFetch(?:<[^>]+>)?\(\s*[`']([^`']+)[`']/g
  let m: RegExpExecArray | null
  while ((m = re.exec(page)) !== null) out.push(canonical(m[1]!))
  return [...new Set(out)]
}

describe('待发布队列必须接线定时发布的三条口', () => {
  it('后端声明恰好三条路由（PUT/DELETE 同路径，所以是两个去重路径）', () => {
    expect(declaredRouteCount()).toBe(3)
    expect(declaredPaths()).toHaveLength(2)
  })

  it('页面请求集与后端声明集精确相等', () => {
    expect(requestedPaths().sort()).toEqual(declaredPaths().sort())
  })

  it('同路径的 PUT 与 DELETE 都被真正调用（集合相等看不出 verb）', () => {
    expect(page).toMatch(/method:\s*'PUT'[\s\S]*method:\s*'DELETE'/)
  })

  it('后台菜单有入口，且与页面路径一致', () => {
    expect(menu).toContain('\'/admin/content/scheduled\'')
  })

  it('后台页保持 ssr:false + admin 布局', () => {
    expect(page).toMatch(/definePageMeta\(\{\s*ssr:\s*false,\s*layout:\s*'admin'\s*\}\)/)
  })

  it('新页面不得整文件关掉 lint 检查', () => {
    expect(page).not.toMatch(/eslint-disable/)
  })
})

describe('定时发布队列的四条实现口径', () => {
  it('列表口有写副作用，页面不静默轮询', () => {
    expect(page).not.toMatch(/setInterval\(/)
    expect(page).toMatch(/onMounted\(load\)/)
    expect(page).toMatch(/写副作用/)
  })

  it('时间换算走 lib/datetime，不手裁 ISO 字符串', () => {
    expect(page).toContain('toDateTimeLocal')
    expect(page).toContain('fromDateTimeLocal')
    expect(page).not.toMatch(/scheduled_at[^\n]*\.slice\(0,\s*16\)/)
  })

  it('改期先过 scheduledAtError，错误显示在字段上', () => {
    expect(page).toContain('scheduledAtError')
    expect(page).toContain('editError')
    const saveFn = page.slice(page.indexOf('async function save'), page.indexOf('async function publishNow'))
    expect(saveFn).toMatch(/if \(invalid\) \{[\s\S]*editError\.value = invalid[\s\S]*return/)
  })

  it('立即发布用"过去时间 + published"，取消不写死提示语', () => {
    expect(page).toMatch(/Date\.now\(\) - 60_000/)
    expect(page).toMatch(/status:\s*'published'/)
    expect(page).toMatch(/status:\s*'scheduled'/)
    expect(page).toMatch(/res\?\.message \?\?/)
  })
})

describe('服务端配套的发布/取消语义（页面提示语的前提）', () => {
  it('到期扫描同时推进 scheduled 与历史 published 两种等待态', () => {
    expect(backend).toMatch(/Post\.status\.in_\(\("scheduled", "published"\)\)/)
    expect(backend).toMatch(/post\.status = "published"/)
  })

  it('取消 scheduled 排期把文章收回 draft，不留死状态', () => {
    expect(backend).toMatch(/post\.status = "draft"/)
    expect(backend).toMatch(/草稿/)
  })

  it('main.py 的循环复用 publish_due_posts，不自带一份没有失效动作的查询', () => {
    const loop = readFileSync(resolve(ROOT, '../backend/main.py'), 'utf8')
    const fn = loop.slice(loop.indexOf('async def _scheduled_publish_loop'))
    expect(fn).toContain('publish_due_posts')
    expect(fn.slice(0, fn.indexOf('while True'))).not.toMatch(/select\(Post\)/)
  })
})
