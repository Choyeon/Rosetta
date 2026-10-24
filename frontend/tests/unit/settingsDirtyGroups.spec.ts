/**
 * 批次 #72 契约：站点设置的"跨组未保存改动"必须看得见、保存得了。
 *
 * 真实缺陷：保存粒度是分组，但脏检查只算当前激活组（`isDirty` 读 activeGroup）。
 * 于是"改 A 组 → 切到 B 组 → 保存 B 组"这条路径里，A 的改动既不在任何提示里、
 * 也没有入口可保存，管理员只有在刷新页面后才发现刚才白改了。
 *
 * 这里用静态源码扫描钉住三件事（页面依赖 Nuxt 自动导入，mount 成本高且易假绿）：
 *   1. 脏检查是"按组"的函数，而不是只算当前组；
 *   2. 脏分组被显式列出，并可以跳过去；
 *   3. 多组脏时存在"保存全部"，且保存链路是共用的单组函数（避免两份清洗规则漂移）。
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const src = readFileSync(resolve(process.cwd(), 'pages/admin/system/settings.vue'), 'utf8')

describe('站点设置 · 未保存改动', () => {
  it('脏检查按分组独立计算，供全组复用', () => {
    expect(src).toMatch(/function isGroupDirty\(groupKey: string\)/)
    expect(src).toMatch(/const isDirty = computed\(\(\) => isGroupDirty\(activeGroup\.value\)\)/)
    expect(src).toMatch(/const dirtyGroups = computed\(\(\) => groups\.filter\(g => isGroupDirty\(g\.key\)\)\)/)
  })

  it('脏分组在页面上有可见入口，并可跳转回该组', () => {
    expect(src).toMatch(/v-if="dirtyGroups\.length > 0"/)
    expect(src).toMatch(/v-for="g in dirtyGroups"/)
    expect(src).toMatch(/@click="jumpToGroup\(g\.key\)"/)
    expect(src).toMatch(/isGroupDirty\(g\.key\)/)
  })

  it('多组脏时可以一次性保存，且复用单组保存函数', () => {
    expect(src).toMatch(/保存全部改动/)
    expect(src).toMatch(/async function saveGroup\(groupKey: string\)/)
    expect(src).toMatch(/const ok = await saveGroup\(key\)/)
    // 批量保存必须按快照循环：否则第一组保存成功后 dirtyGroups 实时变短，末尾分组会被漏掉
    expect(src).toMatch(/const targets = dirtyGroups\.value\.map\(g => g\.key\)/)
  })

  it('长分组提供字段筛选，且只影响显示不参与提交', () => {
    expect(src).toMatch(/const visibleGroupSchemas = computed/)
    expect(src).toMatch(/v-for="\(schema, key\) in visibleGroupSchemas"/)
    expect(src).toMatch(/筛选本组设置项/)
  })
})
