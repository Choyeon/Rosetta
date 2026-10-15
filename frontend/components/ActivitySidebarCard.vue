<!--
  首页侧栏「最新动态」卡：展示最近 3 条已发布动态 + 通往全部动态列表的入口。

  契约：
  - 数据源是公开分页口 GET /activities（page/page_size/lang），page_size=3 命中后端
    缓存键 activities:<lang>:p1:ps3（TTL 300s），与 /activity 整页共用同一套缓存，
    不新增后端接口。
  - 自己发请求而不是由 pages/index.vue 透传：首页左右两栏是同一段卡片的复制品
    （sidebarPosition 可左可右），组件化才能一处定义两处挂载。
  - 日期只取 ISO 串的日期部分，不做 new Date() 本地化：SSR 机与访客浏览器时区不同，
    任何依赖本地时区的格式化都是首屏字节不一致的 hydration 隐患（本仓 §2.4 铁律）。
-->
<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '~~/components/ui/card'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { useAPI } from '~~/composables/useApi'
import UserAvatar from '~~/components/UserAvatar.vue'
import type { AdminUserTitle } from '~~/composables/useAdminManage'
import { ArrowRight } from '~~/lib/lucide-svg-icons'

interface ActivityAuthor {
  nickname?: string | null
  username?: string | null
  avatar?: string | null
  resolved_avatar_url?: string | null
  title?: AdminUserTitle | null
}

interface ActivityItem {
  id: number
  type: string
  content: string
  likes_count?: number
  created_at: string
  author?: ActivityAuthor | null
}

interface ActivitiesPage {
  items: ActivityItem[]
  total?: number
}

const { t, locale } = useI18n()
const { localeHref } = useLocaleLink()

const { data, pending, error } = useAPI<ActivitiesPage>('/activities', {
  query: computed(() => ({ page: 1, page_size: 3, lang: locale.value })),
  key: computed(() => `home:activities:${locale.value}`),
  default: () => ({ items: [] })
})

const items = computed<ActivityItem[]>(() => data.value?.items ?? [])

/** 后端 type 是 Literal["say","article","update","notice","link"]；
 *  未知值回落 say 的文案，避免渲染出 "activity.type_undefined" 这种裸 key。 */
const KNOWN_TYPES = new Set(['say', 'article', 'update', 'notice', 'link'])
const typeLabel = (type: string) =>
  t(KNOWN_TYPES.has(type) ? `activity.type_${type}` : 'activity.type_say')

const authorName = (a?: ActivityAuthor | null) => a?.nickname || a?.username || 'Rosetta'

/** 只截 ISO 串的日期段：2026-10-12T09:31:00 → 2026-10-12 */
const isoDate = (value: string) => (typeof value === 'string' ? value.slice(0, 10) : '')
</script>

<template>
  <Card>
    <CardHeader class="flex-row items-center justify-between gap-3">
      <CardTitle class="text-lg">
        <span class="inline-flex items-center gap-2">
          <span class="size-1.5 rounded-full bg-primary" />
          <span class="uppercase tracking-[0.16em] text-xs text-muted-foreground">
            {{ t('home.recentActivity') }}
          </span>
        </span>
      </CardTitle>
      <NuxtLink
        :to="localeHref('/activity')"
        class="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors"
      >
        {{ t('home.viewAll') }}
        <ArrowRight class="size-3.5" />
      </NuxtLink>
    </CardHeader>
    <CardContent>
      <div
        v-if="error"
        class="text-sm text-destructive"
      >
        {{ t('admin.posts.loadFailed') }}
      </div>
      <div
        v-else-if="pending"
        class="flex flex-col gap-3"
      >
        <Skeleton
          v-for="i in 3"
          :key="i"
          class="h-16 rounded-xl"
        />
      </div>
      <ul
        v-else-if="items.length"
        class="flex flex-col"
      >
        <li
          v-for="(item, idx) in items"
          :key="item.id"
          class="flex gap-3 py-3"
          :class="idx === 0 ? 'pt-0' : 'border-t border-border'"
        >
          <UserAvatar
            :avatar="item.author?.avatar"
            :resolved-avatar-url="item.author?.resolved_avatar_url"
            :seed="item.author?.username || authorName(item.author)"
            :name="authorName(item.author)"
            :title="item.author?.title ?? null"
            :size="34"
            class="shrink-0"
          />
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span class="text-sm font-medium truncate max-w-[10rem]">
                {{ authorName(item.author) }}
              </span>
              <Badge
                variant="secondary"
                class="rounded-full px-2 py-0 text-[11px] font-normal"
              >
                {{ typeLabel(item.type) }}
              </Badge>
            </div>
            <p class="mt-1 text-sm text-muted-foreground line-clamp-2 whitespace-pre-wrap">
              {{ item.content }}
            </p>
            <div class="mt-1 text-xs text-muted-foreground/70 tabular-nums">
              {{ isoDate(item.created_at) }}
            </div>
          </div>
        </li>
      </ul>
      <div
        v-else
        class="text-sm text-muted-foreground"
      >
        {{ t('activity.noActivity') }}
      </div>
    </CardContent>
  </Card>
</template>
