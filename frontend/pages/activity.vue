<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-gradient-to-br from-violet-100 to-indigo-100 dark:from-violet-900/30 dark:to-indigo-900/30 mb-5">
        <Zap class="size-7 text-primary" />
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
            <component
              :is="iconFor(item.type)"
              :class="['size-3', iconClass(item.type)]"
            />
          </div>

          <Card class="transition-all hover:shadow-soft duration-300">
            <CardContent class="p-5">
              <div class="flex items-start justify-between gap-3 mb-3">
                <div class="flex items-center gap-2 flex-wrap">
                  <Badge
                    :variant="badgeVariant(item.type)"
                    class="text-xs"
                  >
                    <component
                      :is="iconFor(item.type)"
                      class="size-3 mr-1.5"
                    />
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
                  <Heart class="size-4 fill-error text-error shrink-0" />
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
        <Zap class="size-8 text-muted-foreground" />
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
import { FileText, Image, MessageCircle, Heart, Zap } from '@lucide/vue'

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

const iconFor = (type: ActivityType) => {
  const map = { post: FileText, card: Image, comment: MessageCircle, like: Heart }
  return map[type]
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

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return ''
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
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

const generateActivities = (): ActivityItem[] => {
  const result: ActivityItem[] = []
  const now = Date.now()
  const types: ActivityType[] = ['post', 'card', 'comment', 'like']
  const weights = [0.2, 0.15, 0.35, 0.3]

  for (let i = 0; i < 22; i++) {
    const rand = Math.random()
    let cumulative = 0
    let type: ActivityType = 'like'
    for (let j = 0; j < types.length; j++) {
      cumulative += weights[j] ?? 0
      if (rand < cumulative) {
        type = types[j] ?? 'like'
        break
      }
    }

    const offset = Math.floor(Math.random() * 86400000 * 14) + 3600000 * i * 2

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
      base.replyTo = Math.random() > 0.5 ? replyTos[i % replyTos.length] : undefined
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
