<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-primary/10 mb-5">
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
      <div
        v-if="pending && activityList.length === 0"
        class="space-y-8 mb-8"
      >
        <div
          v-for="i in 5"
          :key="i"
          class="relative pl-8"
        >
          <div class="absolute -left-8 top-1.5 size-6 rounded-full bg-muted animate-pulse" />
          <div class="space-y-3 p-5 rounded-xl bg-card border border-border/60">
            <div class="flex items-center justify-between gap-3">
              <div class="flex items-center gap-2">
                <div class="size-5 rounded-full bg-muted animate-pulse" />
                <div class="w-20 h-4 rounded-full bg-muted animate-pulse" />
              </div>
              <div class="w-16 h-3 rounded-full bg-muted animate-pulse" />
            </div>
            <div class="space-y-2">
              <div class="w-full h-4 rounded-full bg-muted animate-pulse" />
              <div class="w-4/5 h-4 rounded-full bg-muted animate-pulse" />
              <div class="w-2/3 h-4 rounded-full bg-muted animate-pulse" />
            </div>
          </div>
        </div>
      </div>

      <div
        v-else
        class="relative pl-8"
      >
        <div
          v-if="activityList.length > 0"
          class="absolute left-3 top-2 bottom-2 w-px bg-border"
        />

        <div
          v-for="item in activityList"
          :key="item.id"
          class="relative mb-8 last:mb-0"
        >
          <div
            class="absolute -left-8 top-1.5 size-6 rounded-full border-2 border-background flex items-center justify-center shrink-0 bg-primary/10"
          >
            <svg
              :viewBox="getIcon(activityIconKey(item.type)).viewBox"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="size-3 shrink-0 text-primary"
            >
              <path :d="getIcon(activityIconKey(item.type)).d" />
            </svg>
          </div>

          <Card class="transition-all hover:shadow-soft duration-300">
            <CardContent class="p-5">
              <div class="flex items-start justify-between gap-3 mb-3">
                <div class="flex items-center gap-2 flex-wrap">
                  <Badge
                    variant="default"
                    class="text-xs"
                  >
                    {{ t(`activity.type_${item.type}`) || item.type }}
                  </Badge>
                  <span
                    v-if="item.author_name"
                    class="text-sm font-medium"
                  >{{ item.author_name }}</span>
                </div>
                <span class="text-xs text-muted-foreground shrink-0 whitespace-nowrap">{{ formatDate(item.created_at) }}</span>
              </div>

              <div class="text-foreground/90 leading-relaxed whitespace-pre-wrap">
                {{ item.content }}
              </div>

              <div
                v-if="(item.likes_count ?? 0) > 0"
                class="mt-3 pt-3 border-t border-border/50 flex items-center gap-4 text-xs text-muted-foreground"
              >
                <span class="inline-flex items-center gap-1">
                  <svg
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    stroke="currentColor"
                    stroke-width="1.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    class="size-3.5 fill-error text-error"
                  >
                    <path :d="ICONS.heart?.d ?? ''" />
                  </svg>
                  {{ item.likes_count }}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        <div
          v-if="activityList.length > 0"
          class="absolute -left-8 bottom-0 size-6 rounded-full bg-background border-2 border-border flex items-center justify-center"
        >
          <div class="size-2 rounded-full bg-muted-foreground/40" />
        </div>
      </div>
    </div>

    <div
      v-if="!pending && activityList.length === 0"
      class="text-center py-20"
    >
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <svg
          :viewBox="ICONS.zap?.viewBox ?? '0 0 24 24'"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="size-8 text-muted-foreground"
        >
          <path :d="ICONS.zap?.d ?? ''" />
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
 * 内联 SVG 常量，保证 SSR/客户端输出逐字节一致，避免 Hydration 串台。
 */
const ICONS = {
  say: {
    viewBox: '0 0 24 24',
    d: 'M21 12a8.001 8.001 0 0 0-8-8A8.001 8.001 0 0 0 5 8.122 6.95 6.95 0 0 0 3 12a6.95 6.95 0 0 0 .309 2A8.001 8.001 0 0 0 3 20l2-1.185A7.96 7.96 0 0 0 13 20a8.001 8.001 0 0 0 8-8ZM8 10h8v2H8v-2Zm0 3h5v2H8v-2Z'
  },
  article: {
    viewBox: '0 0 24 24',
    d: 'M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2H6Zm0-2h12V8h-3.6a.4.4 0 0 1-.4-.4V4H6v16Zm2-11h8v2H8v-2Zm0 4h8v2H8v-2Zm0 4h5v2H8v-2Z'
  },
  update: {
    viewBox: '0 0 24 24',
    d: 'M3 12a9 9 0 1 0 3-6.7L3 8V3h5L6.17 4.83A11 11 0 1 1 1 12h2Zm10-5v6l5 3'
  },
  notice: {
    viewBox: '0 0 24 24',
    d: 'M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9Zm4.3 11a2.5 2.5 0 0 0 5.4 0Z'
  },
  zap: {
    viewBox: '0 0 24 24',
    d: 'M13 2 3 14h7l-1 8 10-12h-7l1-8Z'
  },
  heart: {
    viewBox: '0 0 24 24',
    d: 'M12 21s-7-4.5-9.5-9A5.5 5.5 0 0 1 12 6.5 5.5 5.5 0 0 1 21.5 12c-2.5 4.5-9.5 9-9.5 9Z'
  }
} as const

type IconKey = keyof typeof ICONS
interface IconDef { viewBox: string, d: string }
const ICON_FALLBACK: IconDef = ICONS.say
const getIcon = (key: string): IconDef => ((ICONS as Record<IconKey, IconDef>)[key as IconKey] ?? ICON_FALLBACK)

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()

interface ActivityItem {
  id: number
  type: 'say' | 'article' | 'update' | 'notice'
  content: string
  author_name?: string
  author_avatar?: string
  likes_count?: number
  created_at: string
}

const backendToIconKey = (type: string): string => {
  if (type === 'say' || type === 'article' || type === 'update' || type === 'notice') return type
  return 'say'
}
const activityIconKey = (type: string) => backendToIconKey(type)

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
  const loc = String(locale.value || 'zh')
  const months = (MONTH_NAMES[loc] || MONTH_NAMES.en || []) as string[]
  const pad = (n: number) => n < 10 ? `0${n}` : String(n)
  const month = months[date.getMonth()] ?? ''
  const day = date.getDate()
  const hh = pad(date.getHours())
  const mm = pad(date.getMinutes())
  return `${month} ${day} ${hh}:${mm}`
}

// 真实接口：GET /api/activities?page=1&page_size=50
interface Paginated<T> {
  items: T[]
  total?: number
  page?: number
  page_size?: number
  total_pages?: number
}

const { data: activityResp, pending, refresh } = await useAPI<Paginated<ActivityItem>>('/activities', {
  query: {
    page: 1,
    page_size: 50,
    lang: locale
  }
})

const activityList = computed<ActivityItem[]>(() => {
  const items = activityResp.value?.items ?? []
  return items.map((raw: unknown) => {
    const r = raw as Record<string, unknown>
    const author = (r.author ?? {}) as Record<string, unknown>
    const authorName
      = (typeof author.nickname === 'string' && author.nickname)
        || (typeof author.username === 'string' && author.username)
        || (typeof author.name === 'string' && author.name)
        || ''
    const rawType = (typeof r.type === 'string' && r.type) || 'say'
    const safeType: ActivityItem['type']
      = (rawType === 'article' || rawType === 'notice' || rawType === 'say' || rawType === 'update')
        ? rawType
        : 'say'
    return {
      id: typeof r.id === 'number' ? r.id : Number(r.id ?? 0),
      type: safeType,
      content: (typeof r.content === 'string' && r.content) || '',
      author_name: authorName || undefined,
      author_avatar: ((typeof author.avatar === 'string' && author.avatar) || (typeof author.resolved_avatar_url === 'string' && author.resolved_avatar_url)) || undefined,
      likes_count: typeof r.likes_count === 'number' ? r.likes_count : 0,
      created_at: (typeof r.created_at === 'string' && r.created_at) || new Date().toISOString()
    }
  })
})

// 切换语言后重新拉取本地化动态
watch(locale, () => {
  refresh().catch(() => undefined)
})
</script>
