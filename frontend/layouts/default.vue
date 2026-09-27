<!--
  前台布局：AppHeader/AppFooter + 站点公告条 + SSR 主题注入守卫。
  硬契约：setup 期必须 await site.ensureLoaded / ft.ensureLoaded——首字节 HTML 才能带上
  主题 data-* 与 style.css <link>（缺了会"先默认样式闪一帧"）；useHead 只在同步阶段注册，
  await 之后严禁再触碰 head（NUXT_E1001）；onMounted + watch(route) 写 data-layout-scope=frontend
  并重新 applyThemeVisual（从 /admin 返回时视觉层被 clear 过）；公告条的可见性与关闭持久化
  在 composables/useAnnouncementBar.ts（服务端已按 is_active + 时间窗过滤，前端不重复判定）。
-->
<script setup lang="ts">
import AppHeader from '~~/components/AppHeader.vue'
import AppFooter from '~~/components/AppFooter.vue'
import { useTheme } from '~~/composables/useTheme'
import { useAuthStore } from '~~/stores/auth'
import { useI18n } from 'vue-i18n'
import { Bell, X } from '~~/lib/lucide-svg-icons'
import { useFrontendTheme } from '~~/composables/useFrontendTheme'
import {
  announcementVariantClass,
  canDismissAnnouncement,
  mergeAnnouncementRows,
  noticeToRow,
  useAnnouncementBar
} from '~~/composables/useAnnouncementBar'
import type { AnnouncementRow } from '~~/composables/useAnnouncementBar'

// 初始化 useTheme 共享状态（不调用任何会影响首渲染 DOM 的逻辑；真实偏好延后到 Hydrate 后）
useTheme()
const authStore = useAuthStore()
const ft = useFrontendTheme()
const { t } = useI18n()
const route = useRoute()

// 保证 SSR & 客户端首渲染 使用同一份从后端拉到的站点配置
const site = useSite()
await site.ensureLoaded()

/**
 * 【SSR 主题注入】前台所有走本布局的页面在 SSR 阶段就 await 主题状态，
 * 让 useFrontendTheme 内注册的 reactive useHead 在渲染 <head> 前拿到 slug/version——
 * 首字节 HTML 即带 data-rosetta-theme / data-theme / theme class / 主题 style.css <link>，
 * 浏览器渲染阻塞式加载主题 CSS，从根上消灭"先默认主题闪一帧再切极简"的问题。
 * 此前只有首页（页面自身 await）满足此条件，其余页面全靠 app:mounted 后客户端纠偏，
 * 导致归档/留言板/标签/文章页等每次进入都闪屏。
 * useHead 在 useFrontendTheme() 同步阶段注册，本 await 之后不再触碰 head，无 E1001 风险。
 */
await ft.ensureLoaded()

/**
 * 前台布局守卫：
 *   · 写 data-layout-scope=frontend（admin 会写 admin，作为主题 CSS 的双重作用域）
 *   · 重新应用 Rosetta 主题视觉层（SPA 从后台切回前台时，前台的 data-theme 被 clear 掉了，
 *     必须根据已缓存的 state.slug 重新挂回去）。
 *
 * 触发：onMounted + watch route.path。
 */
const applyFrontendShell = () => {
  if (!import.meta.client) return
  document.documentElement.setAttribute('data-layout-scope', 'frontend')
  // 如果 state.loaded 已经为真（例如在首页 /index.vue ensureLoaded 之后），直接用缓存的 slug 重挂视觉层
  // 否则留给具体页面里的 ensureLoaded 去做（避免页面未加载数据时我们用 slug=null 空跑）。
  if (ft.state.value.loaded) {
    ft.applyThemeVisual(route.path)
  }
}
onMounted(() => {
  authStore.initialize()
  applyFrontendShell()
})
// SPA 从 /admin 返回前台时需要重新挂上主题属性；同时从前台不同路径间切换时也修正布局作用域。
watch(() => route.path, () => applyFrontendShell(), { flush: 'post' })

const siteTitleForHead = computed(() => site.siteTitle.value || 'Rosetta')
useHead(() => {
  const siteTitle = siteTitleForHead.value
  return {
    link: [
      { rel: 'alternate', type: 'application/rss+xml', title: `${siteTitle} · RSS`, href: '/rss.xml' },
      { rel: 'sitemap', type: 'application/xml', title: `${siteTitle} · Sitemap`, href: '/sitemap.xml' }
    ]
  }
})

// =============== 站点公告条（两个来源合一）===============
// ① GET /api/announcements：公告管理页的多条运营公告（服务端已按 is_active + 时间窗过滤、排序）
// ② 设置页 notice 分组：全站置顶的单条快捷公告
// 空数组默认；两路都没内容时 visible.length === 0，template 不渲染，无占位假文字。
const { data: annsRaw } = await useAPI<AnnouncementRow[]>('/announcements', {
  key: 'public:announcements',
  default: () => []
})

const annRows = computed<AnnouncementRow[]>(() => (Array.isArray(annsRaw.value) ? annsRaw.value : []))
const noticeRow = computed(() => noticeToRow(site.notice.value))
const bannerRows = computed(() => mergeAnnouncementRows(
  noticeRow.value,
  annRows.value,
  site.notice.value.sticky !== false
))
const { visible: visibleAnns, dismiss: dismissAnn } = useAnnouncementBar(bannerRows)
</script>

<template>
  <div class="min-h-screen bg-background font-sans antialiased flex flex-col">
    <AppHeader />

    <!-- 公告条：仅后端返回真实公告时渲染。后端返回空数组 / 失败 → 整块不出现。 -->
    <div
      v-for="ann in visibleAnns"
      :key="ann.id"
      data-announcement
      :data-announcement-type="ann.type || 'info'"
      role="region"
      :aria-label="t('a11y.announcementBar')"
      :class="['px-4 py-2.5 text-sm', announcementVariantClass(ann.type)]"
    >
      <div class="container mx-auto flex items-start gap-3">
        <Bell class="size-4 shrink-0 mt-0.5 opacity-80" />
        <div class="min-w-0 flex-1 flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <strong
            v-if="ann.title"
            class="font-medium truncate"
          >{{ ann.title }}</strong>
          <span
            v-if="ann.content && ann.content !== ann.title"
            class="truncate opacity-90"
          >{{ ann.content }}</span>
        </div>
        <button
          v-if="canDismissAnnouncement(ann)"
          type="button"
          class="shrink-0 p-1 -m-1 rounded hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
          :aria-label="t('a11y.closeAnnouncement')"
          @click="dismissAnn(ann.id)"
        >
          <X class="size-4" />
        </button>
      </div>
    </div>

    <main
      id="main"
      class="flex-1"
    >
      <slot />
    </main>
    <AppFooter />
  </div>
</template>
