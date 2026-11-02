/**
 * 动态时间线的作者头像（批次 #141）。
 *
 * `pages/activity.vue` 的行归一化里早就算了 `author_avatar`（优先后端解析链的
 * `resolved_avatar_url`，回落原始 `avatar` 列），注释还专门解释了为什么这个顺序不能反——
 * 但模板只渲染了作者名，那一整次归一化没有消费方：用 GitHub / QQ / Gravatar 头像的作者
 * 在动态流里只显示字母兜底。三条必须挡住：
 *   ① 归一化出来的键必须有真实渲染出口（"算了没人用"与"字段没接"表现完全一样）；
 *   ② 取值顺序不得反过来——`avatar` 是原始列，对外链头像的作者那里是 null；
 *   ③ 后端确实带这一位：`author` 走 `PublicUserResponse`，而 `resolved_avatar_url`
 *      由 `build_public_user_response` 现场挂上（不是 ORM 列，少一次赋值就整族掉回字母）。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const src = readFileSync(resolve(ROOT, 'pages/activity.vue'), 'utf-8').replace(/\r\n/g, '\n')
const template = src.slice(0, src.indexOf('</template>'))
const activitySchema = readFileSync(
  resolve(ROOT, '..', 'backend/schemas/activity.py'),
  'utf-8'
).replace(/\r\n/g, '\n')
const userHelper = readFileSync(
  resolve(ROOT, '..', 'backend/api/_user_response_helper.py'),
  'utf-8'
).replace(/\r\n/g, '\n')
const backendSchemas = readFileSync(
  resolve(ROOT, '..', 'backend/schemas/__init__.py'),
  'utf-8'
).replace(/\r\n/g, '\n')

// 头像现在包在作者锚点里（有 username 时整个头像+昵称挂 /authors/<username>），
// 所以取从 <component :is="item.author_url ? ..."> 到 UserAvatar 自闭合标签这一整块：
// v-if 与 href 都在外层，只看 <UserAvatar> 本身会漏掉「谁渲染了它」。
const avatarBlock = template.match(/<component\s+:is="item\.author_url \? 'a' : 'span'[\s\S]*?<\/UserAvatar>|<component\s+:is="item\.author_url \? 'a' : 'span'[\s\S]*?\/>/)?.[0] ?? ''
const rowInterface = src.match(/interface ActivityItem \{[\s\S]*?\n\}/)?.[0] ?? ''
const normalizeBlock = src.match(/\n {4}return \{[\s\S]*?\n {4}\}/)?.[0] ?? ''

describe('动态行头像：归一化与渲染同源', () => {
  it('行数据声明 author_avatar，并在归一化里优先取解析链结果', () => {
    expect(rowInterface).toContain('author_avatar?: string')
    expect(normalizeBlock, '没取到行归一化块').toBeTruthy()
    // 顺序即口径：解析链在前、原始列在后
    const resolvedAt = normalizeBlock.indexOf('author.resolved_avatar_url')
    const rawAt = normalizeBlock.indexOf('author.avatar')
    expect(resolvedAt).toBeGreaterThan(-1)
    expect(rawAt).toBeGreaterThan(-1)
    expect(resolvedAt, 'resolved_avatar_url 必须排在原始 avatar 列之前').toBeLessThan(rawAt)
  })

  it('模板真的渲染头像，而不是只算不用', () => {
    expect(avatarBlock, '动态行里没有 <UserAvatar>').toBeTruthy()
    expect(avatarBlock).toContain(':avatar="item.author_avatar"')
    expect(avatarBlock).toContain(':seed="item.author_name"')
    expect(avatarBlock).toContain(':name="item.author_name"')
    expect(src).toContain(`import UserAvatar from '~~/components/UserAvatar.vue'`)
  })

  it('后端公开口确实带这一位（换个 helper 就整族掉回字母兜底）', () => {
    expect(activitySchema).toContain('author: "PublicUserResponse"')
    expect(userHelper).toContain('resolved_avatar_url = resolved_for_user(user)')
    const publicUser = backendSchemas.match(/class PublicUserResponse[\s\S]*?\nclass /)?.[0] ?? ''
    expect(publicUser, 'PublicUserResponse 不再投影 resolved_avatar_url').toContain('resolved_avatar_url: str | None = None')
  })

  it('没有作者名时不渲染头像壳（字母兜底需要一个可读的 seed）', () => {
    expect(avatarBlock).toContain('v-if="item.author_name"')
    expect(avatarBlock).toContain(':show-title="false"')
  })
})
