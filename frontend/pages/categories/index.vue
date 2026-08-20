<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-gradient-to-br from-amber-100 to-orange-100 dark:from-amber-900/30 dark:to-orange-900/30 mb-5">
        <FolderOpen class="size-7 text-warning" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('categories.title') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('categories.desc') }}
      </p>
    </header>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <NuxtLink
        v-for="cat in categories"
        :key="cat.id"
        :to="`/posts?category=${cat.slug}`"
      >
        <Card class="h-full group transition-all hover:shadow-soft hover:-translate-y-0.5 duration-300 overflow-hidden">
          <CardHeader class="p-6 pb-4">
            <div class="flex items-start justify-between mb-4">
              <div
                class="size-12 rounded-xl flex items-center justify-center bg-gradient-to-br from-indigo-100 to-purple-100 dark:from-indigo-900/40 dark:to-purple-900/40 transition-transform duration-300 group-hover:scale-110"
              >
                <FolderOpen class="size-6 text-primary" />
              </div>
              <Badge variant="secondary">
                {{ getPostsCount(cat) }} {{ t('categories.posts') }}
              </Badge>
            </div>
            <CardTitle class="font-display text-xl tracking-tight group-hover:underline underline-offset-4">
              {{ getCatName(cat) }}
            </CardTitle>
            <CardDescription class="mt-2 line-clamp-2 leading-relaxed min-h-[3rem]">
              {{ getCatDesc(cat) || t('categories.noDesc') }}
            </CardDescription>
          </CardHeader>
          <CardFooter class="p-6 pt-0 flex items-center justify-between text-sm text-muted-foreground border-t mt-2">
            <span>{{ t('categories.browsePosts') }}</span>
            <ArrowRight class="size-4 transition-transform duration-300 group-hover:translate-x-1" />
          </CardFooter>
        </Card>
      </NuxtLink>
    </div>

    <div
      v-if="categories.length === 0"
      class="text-center py-20"
    >
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <FolderOpen class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">
        {{ t('categories.noCategories') }}
      </h3>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from '~~/components/ui/card'
import { Badge } from '~~/components/ui/badge'
import { useI18n } from 'vue-i18n'
import { FolderOpen, ArrowRight } from '@lucide/vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()

const pickLocalized = (val: string | Record<string, string> | null | undefined): string => {
  if (val == null) return ''
  if (typeof val === 'string') return val
  if (typeof val === 'object') {
    const localeKey = locale.value as string
    if (localeKey && val[localeKey]) return val[localeKey]
    const keys = Object.keys(val)
    const firstKey = keys.length > 0 ? keys[0]! : ''
    return firstKey ? (val[firstKey] || '') : ''
  }
  return String(val)
}
const getCatName = (c: { name?: string | Record<string, string> } | null | undefined) => pickLocalized(c?.name)
const getCatDesc = (c: { description?: string | Record<string, string> } | null | undefined) => pickLocalized(c?.description)
const getPostsCount = (c: { post_count?: number, postsCount?: number } | null | undefined) => c?.post_count ?? c?.postsCount ?? 0

const categories = ref([
  {
    id: 1,
    slug: 'frontend',
    name: '前端开发',
    description: '涵盖 Vue、React、CSS、浏览器原理等前端技术的深度探索与实战经验分享。',
    postsCount: 42
  },
  {
    id: 2,
    slug: 'backend',
    name: '后端开发',
    description: 'Node.js、PHP、Python、Go 等后端语言与框架的技术讨论与最佳实践。',
    postsCount: 38
  },
  {
    id: 3,
    slug: 'css',
    name: 'CSS',
    description: '现代 CSS 布局、动画、设计系统与视觉实现技巧集锦。',
    postsCount: 24
  },
  {
    id: 4,
    slug: 'typescript',
    name: 'TypeScript',
    description: '类型体操、类型系统设计、大型项目中的 TS 最佳实践。',
    postsCount: 18
  },
  {
    id: 5,
    slug: 'architecture',
    name: '架构设计',
    description: '系统架构、微服务、领域驱动设计、代码质量与工程化思考。',
    postsCount: 15
  },
  {
    id: 6,
    slug: 'devops',
    name: '运维与部署',
    description: 'Docker、Kubernetes、CI/CD、监控告警与性能优化实战。',
    postsCount: 12
  }
])
</script>
