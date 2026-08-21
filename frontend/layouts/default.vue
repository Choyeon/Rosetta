<script setup lang="ts">
import { TooltipProvider } from '~~/components/ui/tooltip'
import AppHeader from '~~/components/AppHeader.vue'
import AppFooter from '~~/components/AppFooter.vue'
import { useTheme } from '~~/composables/useTheme'
import { useAuthStore } from '~~/stores/auth'
import { useI18n } from 'vue-i18n'
import { Bell, X, ExternalLink } from '@lucide/vue'

// 初始化 useTheme 共享状态（不调用任何会影响首渲染 DOM 的逻辑；真实偏好延后到 Hydrate 后）
useTheme()
const authStore = useAuthStore()
const { locale } = useI18n()

// 保证 SSR & 客户端首渲染 使用同一份从后端拉到的站点配置
const site = useSite()
await site.ensureLoaded()

const siteTitleForHead = computed(() => site.siteTitle.value || 'Rosetta')
useHead(() => {
  const title = siteTitleForHead.value
  return {
    link: [
      { rel: 'alternate', type: 'application/rss+xml', title: `${title} · RSS`, href: '/rss.xml' },
      { rel: 'sitemap', type: 'application/xml', title: `${title} · Sitemap`, href: '/sitemap.xml' }
    ]
  }
})

onMounted(() => {
  authStore.initialize()
})

// =============== 站点公告条（GET /api/announcements）===============
// 空数组默认；失败或空时 visible.length === 0，template 不渲染，无占位假文字。
interface AnnouncementRow {
  id: number | string
  title?: string | Record<string, string>
  content?: string | Record<string, string>
  message?: string | Record<string, string>
  type?: 'info' | 'warning' | 'error' | 'success' | string
  link?: string | null
  url?: string | null
  href?: string | null
  target?: string | null
  is_dismissible?: boolean
  dismissible?: boolean
  sort_order?: number
}

const { data: annsRaw } = await useAPI<AnnouncementRow[]>('/announcements', {
  key: 'public:announcements',
  default: () => []
})

const pickAnnStr = (v: string | Record<string, string> | null | undefined, fb = ''): string => {
  if (v == null) return fb
  if (typeof v === 'string') return v || fb
  if (typeof v === 'object') {
    const l = locale.value as string
    if (l && v[l]) return v[l] || fb
    const keys = Object.keys(v)
    const first = keys[0]
    return (first ? v[first] : '') || fb
  }
  return String(v) || fb
}

const variantClass = (t?: string) => {
  switch (t) {
    case 'warning': return 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-b border-amber-500/20'
    case 'error': return 'bg-rose-500/10  text-rose-700  dark:text-rose-300  border-b border-rose-500/20'
    case 'success': return 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-b border-emerald-500/20'
    case 'info':
    default: return 'bg-sky-500/10    text-sky-700    dark:text-sky-300    border-b border-sky-500/20'
  }
}

const activeAnns = computed<AnnouncementRow[]>(() => (Array.isArray(annsRaw.value) ? annsRaw.value : []))
const dismissed = ref<Record<string | number, boolean>>({})
const visibleAnns = computed(() => activeAnns.value.filter(a => !dismissed.value[String(a.id)]))
const dismissAnn = (id: string | number) => {
  dismissed.value[String(id)] = true
}
const annHref = (a: AnnouncementRow) => (a.link || a.url || a.href || '') as string
const annIsExternal = (a: AnnouncementRow) => {
  const u = annHref(a)
  return /^https?:\/\//i.test(u) || a.target === '_blank'
}
const annCanDismiss = (a: AnnouncementRow) => a.is_dismissible !== false && a.dismissible !== false
const annTitle = (a: AnnouncementRow) => pickAnnStr(a.title || a.content || a.message || '')
const annContent = (a: AnnouncementRow) => {
  const t = pickAnnStr(a.title || '')
  const c = pickAnnStr(a.content || a.message || '')
  if (t && c && t !== c) return c
  return ''
}
</script>

<template>
  <div class="min-h-screen bg-background font-sans antialiased flex flex-col">
    <TooltipProvider :delay-duration="0">
      <AppHeader />

      <!-- 公告条：仅后端返回真实公告时渲染。后端返回空数组 / 失败 → 整块不出现。 -->
      <div
        v-for="ann in visibleAnns"
        :key="ann.id"
        :class="['px-4 py-2.5 text-sm', variantClass(ann.type)]"
      >
        <div class="container mx-auto flex items-start gap-3">
          <Bell class="size-4 shrink-0 mt-0.5 opacity-80" />
          <div class="min-w-0 flex-1 flex flex-wrap items-center gap-x-3 gap-y-1">
            <strong
              v-if="annTitle(ann)"
              class="font-medium truncate"
            >{{ annTitle(ann) }}</strong>
            <span
              v-if="annContent(ann)"
              class="truncate opacity-90"
            >{{ annContent(ann) }}</span>
            <template v-if="annHref(ann)">
              <a
                v-if="annIsExternal(ann)"
                :href="annHref(ann)"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1 font-semibold underline underline-offset-2 hover:opacity-90"
              >
                {{ '查看详情' }}
                <ExternalLink class="size-3" />
              </a>
              <NuxtLink
                v-else
                :to="annHref(ann)"
                class="inline-flex items-center gap-1 font-semibold underline underline-offset-2 hover:opacity-90"
              >
                {{ '前往' }}
              </NuxtLink>
            </template>
          </div>
          <button
            v-if="annCanDismiss(ann)"
            type="button"
            class="shrink-0 p-1 -m-1 rounded hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
            :aria-label="'关闭公告'"
            @click="dismissAnn(ann.id)"
          >
            <X class="size-4" />
          </button>
        </div>
      </div>

      <main
        id="main-content"
        class="flex-1"
      >
        <slot />
      </main>
      <AppFooter />
    </TooltipProvider>
  </div>
</template>
