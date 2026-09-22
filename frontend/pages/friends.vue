<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-gradient-to-br from-primary/10 via-accent/10 to-primary/5 mb-5">
        <Link2 class="size-7 text-success" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('friends.title') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('friends.desc') }}
      </p>
    </header>

    <div
      v-if="loading"
      class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
    >
      <Skeleton
        v-for="i in 4"
        :key="i"
        class="h-48 rounded-2xl"
      />
    </div>

    <div
      v-else-if="fetchError"
      class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive"
    >
      {{ t('friends.loadFailed', '加载失败') }}
    </div>

    <div
      v-else-if="friendLinks.length"
      class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
    >
      <a
        v-for="friend in friendLinks"
        :key="friend.id"
        :href="friend.url"
        :target="friend.target_blank ? '_blank' : undefined"
        :rel="friend.target_blank ? 'noopener noreferrer' : undefined"
      >
        <Card class="h-full group transition-all hover:shadow-soft hover:-translate-y-0.5 duration-300 overflow-hidden">
          <CardHeader class="p-5 pb-3">
            <div class="flex items-start gap-3 mb-3">
              <div
                class="size-12 shrink-0 rounded-xl flex items-center justify-center overflow-hidden bg-muted transition-transform duration-300 group-hover:scale-105"
              >
                <img
                  v-if="friend.logo && !logoFailedIds.has(friend.id)"
                  :src="friend.logo"
                  :alt="pickLocalized(friend.name)"
                  class="size-full object-cover"
                  loading="lazy"
                  width="48"
                  height="48"
                  @error="onLogoError(friend.id)"
                >
                <span
                  v-else
                  class="font-display text-lg font-bold text-muted-foreground"
                >
                  {{ pickLocalized(friend.name)?.[0]?.toUpperCase() }}
                </span>
              </div>
              <div class="flex-1 min-w-0">
                <CardTitle class="font-display text-base tracking-tight group-hover:underline underline-offset-4 truncate">
                  {{ pickLocalized(friend.name) }}
                </CardTitle>
              </div>
            </div>
            <CardDescription class="line-clamp-3 text-sm leading-relaxed min-h-[3.75rem]">
              {{ pickLocalized(friend.description) || t('friends.noDesc') }}
            </CardDescription>
          </CardHeader>
          <CardFooter class="p-5 pt-0 flex items-center justify-between text-sm border-t mt-2">
            <span class="text-muted-foreground truncate pr-2 max-w-[65%]">
              {{ friend.url?.replace(/^https?:\/\//, '') }}
            </span>
            <div class="inline-flex items-center gap-1 text-success shrink-0">
              {{ t('friends.visit') }}
              <ExternalLink class="size-3.5 transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </div>
          </CardFooter>
        </Card>
      </a>
    </div>

    <div
      v-else
      class="text-center py-20"
    >
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <Link2 class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">
        {{ t('friends.noLinks') }}
      </h3>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from '~~/components/ui/card'
import { Skeleton } from '~~/components/ui/skeleton'
import { useFriendLinks } from '~~/composables/useCore'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Link2, ExternalLink } from '@lucide/vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const site = useSite()

const pickLocalized = (val: string | Record<string, string> | null | undefined): string => {
  if (val == null) return ''
  if (typeof val === 'string') return val
  const v = val as Record<string, string>
  const key = locale.value as string
  return v[key] ?? v.zh ?? Object.values(v)[0] ?? ''
}

// ===== SEO：基于 i18n + 站点设置 =====
useSeo({
  title: computed(() => String(t('nav.friends') || t('friends.title') || '友情链接')),
  description: computed(() => site.siteDescription.value),
  type: 'website'
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home') as string, url: '/' },
  { name: t('nav.friends') as string, url: '/friends' }
])

const { getFriendLinks } = useFriendLinks()

// ===== Hydration 安全：同步解构（无 await）避免 setup() 被编译器判定为 async 函数。
// async setup 在客户端同步 Hydrate Diff 阶段视为 Promise pending → Suspense 渲染 Symbol(v-cmt) Comment，
// 而 SSR 端已经渲染了真实 div 子树 → 直接触发 "Hydration completed but contains mismatches."。
// useCore/getFriendLinks 内部基于 useFetch，返回 { data, pending, error } 同步解构即可，
// 首字节 SSR 数据由 useFetch 在服务端阶段填充，客户端从 payload 取回，不需要 await 阻塞。
const { data: links, pending: loading, error: fetchError } = getFriendLinks()

const friendLinks = computed(() => links.value ?? [])

// Logo 加载失败 → 回退到首字母占位（整集替换保证响应式触发；空集两端一致，无 Hydration 风险）
const logoFailedIds = ref<Set<string | number>>(new Set())
const onLogoError = (id: string | number) => {
  const next = new Set(logoFailedIds.value)
  next.add(id)
  logoFailedIds.value = next
}
</script>
