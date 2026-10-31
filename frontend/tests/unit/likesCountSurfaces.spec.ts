/**
 * 「点赞数」在卡片族可见（批次 #142）。
 *
 * 这一族的缺陷形状是「写口 → 存储 → 响应模型 → 消费方」的最后一断：
 * `likes_count` 早就由列表口聚合进载荷（`blog.py` 的 `likes_map` /
 * `schemas/activity.py` 的 `from_activity`），`PostCard` 与首页动态侧栏也都在
 * props 接口里声明了它，但两个模板从来没引用过一次——读者在卡片上能看到浏览数、
 * 评论数、阅读分钟数，唯独看不到这篇文章被点了几次赞。
 * 所以守卫的核心不是「字段存在」（接口声明本来就在那儿），而是
 * 「<template> 区里真的渲染了它」，并且渲染次数与浏览数对齐（漏掉某个变体就是半个页面没接上）。
 *
 * 反向闸门挡两种"看起来在做完"：
 * - 图标必须走官方组件/官方路径常量，卡片里手写 `<path d="M…">` 会画歪（本仓铁律）。
 * - 侧栏只展示不写：那里没有点赞按钮，写了也不会有反馈；`activity.like` 的四语文案
 *   只作为 `title` 提示，缺语时 `t()` 会回落成键名字面量。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(__dirname, '..', '..', '..')
const read = (rel: string) => readFileSync(resolve(root, rel), 'utf8')

const card = read('frontend/components/PostCard.vue')
const sidebar = read('frontend/components/ActivitySidebarCard.vue')
const blogApi = read('backend/api/blog.py')
const activitySchemas = read('backend/schemas/activity.py')
const templateOf = (src: string) => src.slice(src.indexOf('<template>'), src.indexOf('</template>'))
const countOf = (haystack: string, needle: string) => haystack.split(needle).length - 1

describe('文章卡片（PostCard）', () => {
  it('每个显示浏览数的元信息行都同时显示点赞数', () => {
    const tpl = templateOf(card)
    expect(countOf(tpl, '{{ views }}')).toBe(2)
    expect(countOf(tpl, '{{ commentsCount }}')).toBe(2)
    expect(countOf(tpl, '{{ likes }}')).toBe(2)
  })

  it('计数读两种命名，缺键按 0 显示而不是留空', () => {
    expect(card).toContain('const likes = computed(() => props.post.likes_count ?? props.post.likesCount ?? 0)')
  })

  it('爱心用官方组件，卡片内不得手写 SVG 路径', () => {
    expect(card).toMatch(/import \{[^}]*\bHeart\b[^}]*\} from '@lucide\/vue'/)
    expect(templateOf(card)).not.toMatch(/<path\s+d="M/)
  })

  it('后端列表口确实把 likes_count 放进载荷（消费方读得到才有意义）', () => {
    expect(blogApi).toContain('likes_count=likes_map.get(post.id, 0)')
  })
})

describe('首页动态侧栏（ActivitySidebarCard）', () => {
  it('声明了 likes_count 就必须渲染它', () => {
    expect(sidebar).toContain('likes_count?: number')
    expect(templateOf(sidebar)).toContain('{{ item.likes_count ?? 0 }}')
  })

  it('只展示不写：侧栏没有点赞按钮，也不冒充整页的点赞口', () => {
    const tpl = templateOf(sidebar)
    expect(tpl).not.toContain('@click')
    expect(sidebar).not.toContain('likeActivity')
  })

  it('动态口的计数来自活动行本身', () => {
    expect(activitySchemas).toContain('likes_count: int = 0')
    expect(activitySchemas).toContain('likes_count=activity.likes_count')
  })
})

describe('文案', () => {
  it('四语都有 activity.like（title 提示的唯一来源）', () => {
    for (const lang of ['zh', 'en', 'ja', 'zh_Hant']) {
      const locale = JSON.parse(read(`frontend/i18n/locales/${lang}.json`)) as { activity?: { like?: string } }
      expect(typeof locale.activity?.like, `${lang} 缺 activity.like`).toBe('string')
    }
  })
})
