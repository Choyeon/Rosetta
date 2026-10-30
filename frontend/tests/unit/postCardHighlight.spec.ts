/**
 * 搜索结果关键词高亮（批次 #214）。
 *
 * 关键词来自地址栏（?q=），所以高亮实现的第一条红线是**不得拼 HTML**：
 * 只要用了 v-html，`?q=<img src=x onerror=…>` 就等于一条反射型 XSS。
 * 第二条是"只按字面匹配"：关键词里的 `.` `*` `(` 若当正则元字符，
 * 搜 `c++` 会抛异常、搜 `.` 会把整段摘要全标黄。
 * 两条都由本 spec 按源码形态钉住（本仓没有组件挂载环境，走静态断言）。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const read = (rel: string) => readFileSync(resolve(ROOT, rel), 'utf-8')

const highlight = read('components/HighlightText.vue')
const card = read('components/PostCard.vue')
const searchPage = read('pages/search.vue')

/** 注释里提到 v-html（解释"为什么不用"）不算使用，判定前先剥掉注释。 */
const stripComments = (src: string) => src
  .replace(/<!--[\s\S]*?-->/g, '')
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .replace(/^\s*\/\/.*$/gm, '')

describe('HighlightText 渲染面', () => {
  it('命中片段包成 <mark>，其余是纯文本节点', () => {
    expect(highlight).toContain('<mark')
    expect(highlight).toContain('part.text')
  })

  it('不用 v-html / innerHTML（关键词来自地址栏，拼 HTML 即 XSS）', () => {
    const code = stripComments(highlight)
    expect(code).not.toContain('v-html')
    expect(code).not.toContain('innerHTML')
  })

  it('只按字面匹配：indexOf + toLowerCase，不构造 RegExp', () => {
    expect(highlight).toContain('toLowerCase()')
    expect(highlight).toContain('indexOf(')
    expect(highlight).not.toContain('new RegExp')
    expect(highlight).not.toMatch(/\bRegExp\(/)
  })

  it('空关键词原样输出整段（不高亮、也不丢文字）', () => {
    const body = highlight.match(/const parts = computed<Segment\[\]>\(\(\) => \{[\s\S]*?\n\}\)/)?.[0] ?? ''
    expect(body).toContain('if (!keyword || !text)')
    expect(body).toContain('{ text, hit: false }')
  })
})

describe('PostCard 接入 highlight', () => {
  it('声明 highlight 属性并默认空串（其它页面零改动）', () => {
    expect(card).toContain('highlight?: string')
    expect(card).toContain('highlight: \'\'')
    expect(card).toContain('import HighlightText from \'~~/components/HighlightText.vue\'')
  })

  it('三副骨架的标题与摘要都经过 HighlightText（6 处）', () => {
    const uses = card.match(/<HighlightText/g) ?? []
    expect(uses).toHaveLength(6)
    expect(card).not.toContain('{{ postTitle }}')
    expect(card).not.toContain('{{ postExcerpt || t(\'post.noExcerpt\') }}')
  })

  it('摘要占位文案落成字符串再喂给组件（组件只收纯文本）', () => {
    expect(card).toContain('const excerptText = computed(() => postExcerpt.value || t(\'post.noExcerpt\'))')
    expect(card).toContain(':text="excerptText"')
  })
})

describe('搜索页传入命中词', () => {
  it('结果卡片带 :highlight="keywordLabel"', () => {
    expect(searchPage).toContain(':highlight="keywordLabel"')
  })

  it('搜索页自身不用 v-html', () => {
    expect(stripComments(searchPage)).not.toContain('v-html')
  })
})
