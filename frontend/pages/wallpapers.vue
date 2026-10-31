<!--
  Bing 每日一图归档页（公开 SSR）：`GET /api/bing/image/archive` 的唯一消费方。

  四条口径：
  1. **图片走站内代理直链**（`lib/bing-image.ts::bingProxyUrl` → `/api/bing/image?src=`），
     不把 `cn.bing.com` 原链挂进图片标签：原链绕开本站的 30 天 immutable 落盘缓存与
     兜底 SVG，且 Bing 侧限流/地区差异会直接变成访客看到的碎图。
  2. **日期是上游给的**（`BingImageOut.date` ← `startdate`），页面不再按"今天减第几张"推算；
     上游只保留最近 8 天，所以取 `days = ARCHIVE_DAYS(8)`，多要的那几天上游确实没有。
  3. **后台关掉「启用 Bing 每日壁纸」时公开面一起收起**（同 `/sponsor` 先例）：这里不渲染卡片、
     输出 `noindex, follow`，后端 sitemap 也按同一个开关决定是否收录
     （`backend/services/site_settings.py::bing_wallpaper_enabled`，判据与 `/api/config`
     投影 `enable_bing_wallpaper` 的那份合并结果对账，见 `tests/test_bing_wallpaper_archive.py`）。
     开关来源与登录/注册页同一个 `publicConfig.enable_bing_wallpaper`，不另发请求。
  4. SSR 首帧就把代理串算好，hydration 用同一个纯函数重算 → 两端逐字节一致；
     日期一律原样显示 ISO 串，不用 `toLocaleString`（SSR 与客户端时区不同会换字）。
-->
<template>
  <div class="container py-16">
    <header class="mb-10 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-gradient-to-br from-primary/10 via-accent/10 to-primary/5 mb-5">
        <Image class="size-7 text-primary" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('wallpapers.title') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('wallpapers.desc') }}
      </p>
    </header>

    <!-- 骨架只在真的还没有内容时出现；请求失败后不能一片空白 -->
    <div
      v-if="pending && cards.length === 0"
      class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
    >
      <div
        v-for="i in 3"
        :key="i"
        class="rounded-xl overflow-hidden border border-border/60 bg-card"
      >
        <Skeleton class="aspect-video rounded-none" />
        <div class="p-5 flex flex-col gap-3">
          <Skeleton class="w-1/3 h-4 rounded" />
          <Skeleton class="w-full h-3.5 rounded" />
        </div>
      </div>
    </div>

    <div
      v-else-if="!disabled && cards.length > 0"
      class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
    >
      <article
        v-for="card in cards"
        :key="`${card.date}-${card.image}`"
        class="group overflow-hidden rounded-xl border border-border/60 bg-card shadow-sm transition-all duration-300 hover:shadow-lg"
      >
        <div class="relative aspect-video overflow-hidden bg-muted">
          <img
            v-if="card.image"
            :src="card.image"
            :alt="card.title"
            width="1200"
            height="675"
            class="size-full object-cover transition-transform duration-500 group-hover:scale-[1.02]"
            loading="lazy"
            decoding="async"
          >
          <time
            v-if="card.date"
            :datetime="card.date"
            class="absolute left-3 top-3 rounded-md bg-black/55 px-2 py-1 text-xs font-medium text-white backdrop-blur-sm"
          >{{ card.date }}</time>
        </div>

        <div class="p-5 flex flex-col gap-2">
          <h2 class="font-display text-base font-semibold tracking-tight line-clamp-1">
            {{ card.title }}
          </h2>
          <p
            v-if="card.copyright"
            class="text-xs leading-relaxed text-muted-foreground line-clamp-2"
          >
            <a
              v-if="card.source"
              :href="card.source"
              target="_blank"
              rel="noopener nofollow"
              class="hover:text-foreground hover:underline"
            >{{ card.copyright }}</a>
            <template v-else>
              {{ card.copyright }}
            </template>
          </p>

          <div
            v-if="card.download"
            class="mt-2"
          >
            <a
              :href="card.download"
              :download="`${card.date || 'bing'}.jpg`"
              class="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2.5 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Download data-icon="inline-start" />
              {{ t('wallpapers.download') }}
            </a>
          </div>
        </div>
      </article>
    </div>

    <div
      v-else-if="loadError"
      class="text-center py-16"
    >
      <AlertCircle class="mx-auto mb-3 size-10 text-destructive/60" />
      <p class="mb-4 text-sm text-muted-foreground">
        {{ t('common.error') }}
      </p>
      <Button
        variant="outline"
        size="sm"
        @click="retry"
      >
        <RefreshCw data-icon="inline-start" />
        {{ t('common.retry') }}
      </Button>
    </div>

    <div
      v-else
      class="text-center py-16"
    >
      <div class="mx-auto mb-4 inline-flex size-16 items-center justify-center rounded-2xl bg-muted">
        <ImageOff class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">
        {{ t('wallpapers.empty') }}
      </h3>
      <p class="mt-2 text-sm text-muted-foreground">
        {{ t('wallpapers.emptyHint') }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertCircle, Download, Image, ImageOff, RefreshCw } from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Skeleton } from '~~/components/ui/skeleton'
import { useAPI } from '~~/composables/useApi'
import { parseBingArchive } from '~~/lib/bing-image'

definePageMeta({ layout: 'default' })

const { t } = useI18n()
const site = useSite()

// 上游只保留最近这些天（2026-10-31 线上实测 n=14 也只回 8 条），多要只是空转。
const ARCHIVE_DAYS = 8

const { data, pending, error, refresh } = useAPI<unknown>('/bing/image/archive', {
  query: { days: ARCHIVE_DAYS },
  key: `public:bing-archive:${ARCHIVE_DAYS}`,
  default: () => null
})

const cards = computed(() => parseBingArchive(data.value))
const loadError = computed(() => Boolean(error.value) && cards.value.length === 0)
const retry = () => void refresh()

/** 「启用 Bing 每日壁纸」关掉时整页收起（与后端 sitemap 收录判据同一个开关）。 */
const disabled = computed(
  () => site.state.value.publicConfig?.enable_bing_wallpaper === false
)

/** 关掉开关、或上游这一次真的没带回任何一张：两种都是「没有可索引内容」。 */
const wallpapersEmpty = computed(() => disabled.value || (cards.value.length === 0 && !pending.value))

useSeo({
  title: computed(() => t('wallpapers.title')),
  description: computed(() => t('wallpapers.desc')),
  url: '/wallpapers',
  type: 'website',
  noindex: wallpapersEmpty
})
useBreadcrumbJsonLd([
  { name: t('nav.home') as string, url: '/' },
  { name: t('wallpapers.title') as string, url: '/wallpapers' }
])
</script>
