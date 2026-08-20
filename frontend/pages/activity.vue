<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-gradient-to-br from-violet-100 to-indigo-100 dark:from-violet-900/30 dark:to-indigo-900/30 mb-5">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="size-7 text-primary"
        >
          <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z" />
        </svg>
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('activity.title') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('activity.desc') }}
      </p>
    </header>

    <div class="max-w-2xl mx-auto">
      <div class="relative pl-8">
        <div class="absolute left-3 top-2 bottom-2 w-px bg-border" />

        <div
          v-for="item in activityList"
          :key="item.id"
          class="relative mb-8 last:mb-0"
        >
          <div
            class="absolute -left-8 top-1.5 size-6 rounded-full border-2 border-background flex items-center justify-center shrink-0"
            :class="iconBgClass(item.type)"
          >
            <svg
              v-if="item.type === 'post'"
              :viewBox="ICONS.post.viewBox"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              :class="['size-3 shrink-0', iconClass(item.type)]"
            >
              <path :d="ICONS.post.d" />
            </svg>
            <svg
              v-else-if="item.type === 'card'"
              :viewBox="ICONS.card.viewBox"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              :class="['size-3 shrink-0', iconClass(item.type)]"
            >
              <path :d="ICONS.card.d" />
            </svg>
            <svg
              v-else-if="item.type === 'comment'"
              :viewBox="ICONS.comment.viewBox"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              :class="['size-3 shrink-0', iconClass(item.type)]"
            >
              <path :d="ICONS.comment.d" />
            </svg>
            <svg
              v-else-if="item.type === 'like'"
              :viewBox="ICONS.like.viewBox"
              fill="currentColor"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              :class="['size-3 shrink-0', iconClass(item.type)]"
            >
              <path :d="ICONS.like.d" />
            </svg>
          </div>

          <Card class="transition-all hover:shadow-soft duration-300">
            <CardContent class="p-5">
              <div class="flex items-start justify-between gap-3 mb-3">
                <div class="flex items-center gap-2 flex-wrap">
                  <Badge
                    :variant="badgeVariant(item.type)"
                    class="text-xs"
                  >
                    <svg
                      v-if="item.type === 'post'"
                      :viewBox="ICONS.post.viewBox"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      class="size-3 mr-1.5 inline -mt-0.5"
                    >
                      <path :d="ICONS.post.d" />
                    </svg>
                    <svg
                      v-else-if="item.type === 'card'"
                      :viewBox="ICONS.card.viewBox"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      class="size-3 mr-1.5 inline -mt-0.5"
                    >
                      <path :d="ICONS.card.d" />
                    </svg>
                    <svg
                      v-else-if="item.type === 'comment'"
                      :viewBox="ICONS.comment.viewBox"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      class="size-3 mr-1.5 inline -mt-0.5"
                    >
                      <path :d="ICONS.comment.d" />
                    </svg>
                    <svg
                      v-else-if="item.type === 'like'"
                      :viewBox="ICONS.like.viewBox"
                      fill="currentColor"
                      stroke="currentColor"
                      stroke-width="1.5"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      class="size-3 mr-1.5 inline -mt-0.5"
                    >
                      <path :d="ICONS.like.d" />
                    </svg>
                    {{ t(`activity.type_${item.type}`) }}
                  </Badge>
                  <span
                    v-if="item.author"
                    class="text-sm font-medium"
                  >{{ item.author }}</span>
                </div>
                <span class="text-xs text-muted-foreground shrink-0 whitespace-nowrap">{{ formatDate(item.createdAt) }}</span>
              </div>

              <template v-if="item.type === 'post'">
                <div class="font-medium text-base leading-snug mb-1.5 line-clamp-1">
                  <a
                    v-if="item.link"
                    :href="item.link"
                    class="hover:underline underline-offset-4"
                  >{{ item.title }}</a>
                  <span v-else>{{ item.title }}</span>
                </div>
                <p class="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
                  {{ item.content }}
                </p>
              </template>

              <template v-else-if="item.type === 'card'">
                <div class="font-medium text-base leading-snug mb-1.5">
                  {{ item.title }}
                </div>
                <div class="rounded-xl bg-muted/50 overflow-hidden mt-3">
                  <div class="aspect-[16/6] bg-gradient-to-br from-indigo-200 via-purple-200 to-pink-200 dark:from-indigo-900/40 dark:via-purple-900/40 dark:to-pink-900/40" />
                </div>
              </template>

              <template v-else-if="item.type === 'comment'">
                <div class="rounded-xl bg-muted/40 p-4 border border-border/50">
                  <div class="flex items-center gap-2 mb-2">
                    <span class="text-sm font-medium">{{ item.replyTo ? `${item.author} → ${item.replyTo}` : item.author }}</span>
                    <span class="text-xs text-muted-foreground">{{ item.title }}</span>
                  </div>
                  <p class="text-sm text-foreground/90 leading-relaxed line-clamp-3">
                    {{ item.content }}
                  </p>
                </div>
              </template>

              <template v-else-if="item.type === 'like'">
                <div class="flex items-center gap-2">
                  <svg
                    :viewBox="ICONS.like.viewBox"
                    fill="currentColor"
                    stroke="currentColor"
                    stroke-width="1.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    class="size-4 shrink-0 fill-error text-error"
                  >
                    <path :d="ICONS.like.d" />
                  </svg>
                  <span class="text-sm text-foreground/90 leading-relaxed">
                    <span class="font-medium">{{ item.author }}</span>
                    {{ t('activity.liked') }}
                    <span class="font-medium">"{{ item.title }}"</span>
                  </span>
                </div>
              </template>
            </CardContent>
          </Card>
        </div>

        <div class="absolute -left-8 bottom-0 size-6 rounded-full bg-background border-2 border-border flex items-center justify-center">
          <div class="size-2 rounded-full bg-muted-foreground/40" />
        </div>
      </div>
    </div>

    <div
      v-if="activityList.length === 0"
      class="text-center py-20"
    >
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <svg
          :viewBox="ICONS.zap.viewBox"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="size-8 text-muted-foreground"
        >
          <path :d="ICONS.zap.d" />
        </svg>
      </div>
      <h3 class="font-display text-xl font-semibold">
        {{ t('activity.noActivity') }}
      </h3>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent } from '~~/components/ui/card'
import { Badge } from '~~/components/ui/badge'
import { useI18n } from 'vue-i18n'

/**
 * 注意：这里为避免 Hydration 阶段 @lucide/vue 组件在 SSR 端串台
 * （同名工厂 createLucideIcon 复用导致 SVG d 属性被渲染成其他图标），
 * 直接使用内联 SVG 常量，保证服务端/客户端输出逐字节一致。
 */
const ICONS = {
  post: {
    viewBox: '0 0 24 24',
    d: 'M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2H6Zm0-2h12V8h-3.6a.4.4 0 0 1-.4-.4V4H6v16Zm2-11h8v2H8v-2Zm0 4h8v2H8v-2Zm0 4h5v2H8v-2Z'
  },
  card: {
    viewBox: '0 0 24 24',
    d: 'M2 6a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6Zm2 0v2h16V6H4Zm0 4v8h16v-8H4Zm2 2h6v2H6v-2Z'
  },
  comment: {
    viewBox: '0 0 24 24',
    d: 'M21 12a8.001 8.001 0 0 0-8-8A8.001 8.001 0 0 0 5 8.122 6.95 6.95 0 0 0 3 12a6.95 6.95 0 0 0 .309 2A8.001 8.001 0 0 0 3 20l2-1.185A7.96 7.96 0 0 0 13 20a8.001 8.001 0 0 0 8-8ZM8 10h8v2H8v-2Zm0 3h5v2H8v-2Z'
  },
  like: {
    viewBox: '0 0 24 24',
    d: 'M12 21s-7-4.5-9.5-9A5.5 5.5 0 0 1 12 6.5 5.5 5.5 0 0 1 21.5 12c-2.5 4.5-9.5 9-9.5 9Z'
  },
  zap: {
    viewBox: '0 0 24 24',
    d: 'M13 2 3 14h7l-1 8 10-12h-7l1-8Z'
  }
}

definePageMeta({ layout: 'default' })

const { t } = useI18n()

type ActivityType = 'post' | 'card' | 'comment' | 'like'

interface ActivityItem {
  id: number
  type: ActivityType
  title?: string
  content?: string
  link?: string
  author?: string
  replyTo?: string
  createdAt: string
}

const iconBgClass = (type: ActivityType) => {
  const map = {
    post: 'bg-primary/10',
    card: 'bg-info/10',
    comment: 'bg-success/10',
    like: 'bg-error/10'
  }
  return map[type]
}

const iconClass = (type: ActivityType) => {
  const map = {
    post: 'text-primary',
    card: 'text-info',
    comment: 'text-success',
    like: 'text-error'
  }
  return map[type]
}

const badgeVariant = (type: ActivityType) => {
  const map: Record<ActivityType, 'default' | 'secondary' | 'outline' | 'destructive'> = {
    post: 'default',
    card: 'secondary',
    comment: 'outline',
    like: 'destructive'
  }
  return map[type]
}

/**
 * 使用静态月名（避免 SSR 端与客户端 `toLocaleString` 因语言环境不一致
 * 导致 Hydration 文本不匹配）。
 */
const MONTH_NAMES: Record<string, string[]> = {
  zh: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
  en: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
  ja: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
  zh_Hant: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
}
const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return ''
  const { locale } = useI18n()
  const loc = String(locale.value || 'zh')
  const months = (MONTH_NAMES[loc] || MONTH_NAMES.en || []) as string[]
  const pad = (n: number) => n < 10 ? `0${n}` : String(n)
  const month = months[date.getMonth()] ?? ''
  const day = date.getDate()
  const hh = pad(date.getHours())
  const mm = pad(date.getMinutes())
  return `${month} ${day} ${hh}:${mm}`
}

const authors = ['林清远', '沈砚之', '苏半夏', '墨白', 'Alex Chen', '陈星遥', '陆展', '叶知秋', '江晚', '阮青黛']
const replyTos = ['Rosetta', '林清远', '沈砚之', '苏半夏', 'Alex Chen']
const postTitles = [
  'Vue 3 组合式 API 设计模式探索',
  '现代 CSS 布局完全指南',
  'TypeScript 类型体操进阶',
  '构建高性能 Nuxt 应用的 10 个技巧',
  'Tailwind CSS 自定义主题系统实战',
  '状态管理新纪元：Pinia vs Vuex',
  '从 0 到 1 搭建 Monorepo',
  '深入理解浏览器事件循环',
  '微前端架构的三种落地姿势',
  'Vite 插件开发从入门到精通'
]
const commentContents = [
  '写得非常好，收藏了慢慢消化。特别是关于 effect 依赖收集那部分，之前一直糊里糊涂的。',
  '请问有计划出 React 版本的对比分析吗？最近在做技术选型，很需要这类横向比较的文章。',
  '感谢分享！亲测有效，已经用在公司项目里了，性能提升很明显。',
  '第七点 hydration 优化那块没太看懂，能不能出个更详细的 Demo？',
  '支持作者！这篇比官方文档讲得还明白，尤其是设计取舍的思路太珍贵了。',
  '大佬高产似母猪（褒义），每次更新都第一时间来看。',
  '刚从 Vue2 迁过来，这篇简直是救命稻草。',
  '代码示例能不能放到 GitHub 仓库？复制粘贴容易丢格式。',
  '顺便问一句，Blog 用的什么字体？中文和英文搭配得特别舒服。',
  '期待下一篇！关于服务端渲染部分的坑我也踩过不少，坐等大佬总结。'
]
const likeTitles = [
  'Vue 3 组合式 API 设计模式',
  '现代 CSS 布局指南',
  'TypeScript 类型体操',
  '高性能 Nuxt 应用技巧',
  'Tailwind 主题系统',
  'Pinia vs Vuex',
  'Monorepo 搭建笔记',
  '浏览器事件循环',
  '微前端架构',
  'Vite 插件开发'
]
const cardTitles = [
  '川西环线 · 稻城亚丁',
  '日常随手拍 · 光影切片',
  '工位美学 · 机械键盘集合',
  '海岸线 · 追逐日落',
  '北海道の冬 · 小樽雪灯',
  '植物笔记 · 阳台多肉'
]
const postContents = [
  '深入理解 Composition API 背后的设计理念，以及如何在大型项目中构建可维护、可复用的组件逻辑封装模式...',
  '从 Flexbox 到 Grid，再到最新的容器查询，全面掌握现代 CSS 布局的核心技巧与实用陷阱避坑指南...',
  '高级类型编程实战：条件类型、映射类型与模板字面量的创造性应用，带你领略类型系统的边界...',
  '服务端渲染优化、客户端 hydration、bundle 分割、预取策略，深度剖析每一个性能关键点...'
]

/**
 * 基于整数种子的确定性伪随机（返回 [0,1)）。
 * 确保 SSR 与客户端首渲染 activityList 完全一致 → 避免 Hydration mismatch。
 */
const seededRand = (seed: number): number => {
  let t = seed + 0x6d2b79f5
  t = Math.imul(t ^ (t >>> 15), t | 1)
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296
}

const generateActivities = (): ActivityItem[] => {
  const result: ActivityItem[] = []
  const now = new Date('2026-08-17T12:00:00.000Z').getTime()
  const types: ActivityType[] = ['post', 'card', 'comment', 'like']
  const weights = [0.2, 0.15, 0.35, 0.3]

  for (let i = 0; i < 22; i++) {
    const rand = seededRand(i * 7919 + 13)
    let cumulative = 0
    let type: ActivityType = 'like'
    for (let j = 0; j < types.length; j++) {
      cumulative += weights[j] ?? 0
      if (rand < cumulative) {
        type = types[j] ?? 'like'
        break
      }
    }

    const r2 = seededRand(i * 104729 + 37)
    const offset = Math.floor(r2 * 86400000 * 14) + 3600000 * i * 2

    const base: ActivityItem = {
      id: i + 1,
      type,
      createdAt: new Date(now - offset).toISOString()
    }

    if (type === 'post') {
      base.title = postTitles[i % postTitles.length]
      base.content = postContents[i % postContents.length]
      base.author = authors[i % authors.length]
      base.link = `/posts/${i + 1}`
    } else if (type === 'card') {
      base.title = cardTitles[i % cardTitles.length]
      base.author = 'Rosetta'
    } else if (type === 'comment') {
      base.title = `评论于《${postTitles[i % postTitles.length]}》`
      base.author = authors[i % authors.length]
      const r3 = seededRand(i * 31 + 97)
      base.replyTo = r3 > 0.5 ? replyTos[i % replyTos.length] : undefined
      base.content = commentContents[i % commentContents.length]
    } else {
      base.title = likeTitles[i % likeTitles.length]
      base.author = authors[i % authors.length]
    }

    result.push(base)
  }

  return result.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
}

const activityList = ref<ActivityItem[]>(generateActivities())
</script>
