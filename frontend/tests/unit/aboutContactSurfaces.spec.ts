/**
 * 关于页联系方式的第四段（批次 #141）。
 *
 * `contact_qq` / `contact_wechat` 三段早就齐了：库里有值、`/api/config` 投影得出、
 * `about.vue` 的 `config` 也把它们读进了内存——唯独 `contacts` 从不 push，于是运营者
 * 填了 QQ 号与微信号，关于页永远只显示 Email 与一排社交外链。这属于「写了没人渲染」的
 * 同一族缺陷（对照 `tests/test_post_encryption_hint.py` 的四段口径），三条必须挡住：
 *   ① 联系方式键的清单以后端投影为唯一来源，页面消费集合与之相等——漏一个即这一族的
 *      第四段又断在这里，而且接口层一个错都不报；
 *   ② 纯展示值不得套进 `<a target="_blank">`：微信号没有可点的公开 URL，QQ 的 wpa 跳转
 *      要拼客户端参数，硬编一个地址等于造一条死链并让爬虫把它收进站内链接图；
 *   ③ 「技能」分区的数据源是刻意的空常量（后端没有该字段），所以分区与导航项都必须跟着
 *      数据收起——否则导航里永远有一颗点了只跳到一张空卡的锚。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const src = readFileSync(resolve(ROOT, 'pages/about.vue'), 'utf-8').replace(/\r\n/g, '\n')
const backendSchemas = readFileSync(
  resolve(ROOT, '..', 'backend/schemas/__init__.py'),
  'utf-8'
).replace(/\r\n/g, '\n')

// 只在 <template> 段里断言渲染形态：脚本段说什么都挡不住模板写错
const template = src.slice(0, src.indexOf('</template>'))

const CONTACT_KEYS = ['contact_email', 'contact_qq', 'contact_wechat']

const contactsBody = src.match(/const contacts = computed<ContactItem\[\]>\(\(\) => \{[\s\S]*?\n\}\)/)?.[0] ?? ''
const rowAttrsBody = src.match(/const contactRowAttrs = [\s\S]*?contact\.href === null[^\n]*/)?.[0] ?? ''

describe('关于页联系方式：投影与渲染同集合', () => {
  it('后端联系方式键的集合就是页面应当消费的集合', () => {
    const declared = [...new Set([...backendSchemas.matchAll(/^\s+(contact_\w+): /gm)].map(m => m[1] ?? ''))].sort()
    expect(declared, '后端投影的 contact_* 变了，页面清单要同批跟着').toEqual([...CONTACT_KEYS].sort())
    const iface = src.match(/interface SiteConfigLite \{[\s\S]*?\n\}/)?.[0] ?? ''
    const read = [...new Set([...iface.matchAll(/^\s+(contact_\w+)\??:/gm)].map(m => m[1] ?? ''))].sort()
    expect(read).toEqual([...CONTACT_KEYS].sort())
  })

  it('每一个联系方式键都在 contacts 里真的有出口（读进 config 却从不 push 就是这一族的病）', () => {
    expect(contactsBody, '没取到 contacts 计算属性').toBeTruthy()
    for (const key of CONTACT_KEYS) {
      expect(contactsBody, `contacts 没有消费 ${key}`).toContain(`cfg.${key}`)
    }
    // QQ / 微信是"号"不是链接：值为纯展示，空串/空白不得渲染成一行
    expect(contactsBody).toContain(`const qq = (cfg.contact_qq ?? '').trim()`)
    expect(contactsBody).toContain(`list.push({ label: 'QQ', value: qq, href: null, icon: MessageCircle })`)
    expect(contactsBody).toContain(`const wechat = (cfg.contact_wechat ?? '').trim()`)
    expect(contactsBody).toContain(`list.push({ label: 'WeChat', value: wechat, href: null, icon: MessageSquare })`)
  })

  it('ContactItem 的 href 允许为 null，且两个图标都从 @lucide/vue 取官方组件', () => {
    const iface = src.match(/interface ContactItem \{[\s\S]*?\n\}/)?.[0] ?? ''
    expect(iface).toContain('href: string | null')
    const importBlock = src.match(/import \{[\s\S]*?\} from '@lucide\/vue'/)?.[0] ?? ''
    for (const icon of ['MessageCircle', 'MessageSquare']) {
      expect(importBlock, `缺少 ${icon} 图标导入（不得手写 SVG path）`).toContain(icon)
    }
  })

  it('可点的行才渲染 <a> 与 target/rel，纯展示行渲染 <div>', () => {
    expect(template).toContain(`:is="contact.href ? 'a' : 'div'"`)
    expect(template).toContain('v-bind="contactRowAttrs(contact)"')
    // 反向闸门：无条件绑 href 会让 QQ / 微信行渲染出 href="null" 的死锚
    expect(template).not.toContain(':href="contact.href"')
    expect(template).not.toMatch(/<a\s+v-for="contact in contacts"/)
    expect(rowAttrsBody).toContain('contact.href === null ? null : { href: contact.href, target: \'_blank\', rel: \'noopener noreferrer\' }')
  })
})

describe('关于页「技能」分区：没有数据就整段收起', () => {
  it('分区与导航项都跟着 hasSkills 走，不再留一颗指向空卡的锚', () => {
    expect(src).toContain('const hasSkills = techStack.length + skillGroups.length > 0')
    expect(template).toMatch(/<section\s+v-if="hasSkills"\s+id="skills"/)
    expect(template).toContain('v-for="section in visibleSections"')
    expect(src).toContain(`hasSkills ? aboutSections : aboutSections.filter(section => section.id !== 'skills')`)
  })

  it('techStack / skillGroups 仍是空常量（后端无该字段，不得编造履历数据）', () => {
    expect(src).toContain('const techStack: TechChip[] = []')
    expect(src).toContain('const skillGroups: SkillGroupItem[] = []')
  })
})
