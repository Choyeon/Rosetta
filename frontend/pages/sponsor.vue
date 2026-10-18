<!--
  捐助页：后台「站点设置 → 捐助打赏」（settings 分组 donate）的唯一前台落点。
  数据源是 useSite().donate（来自 GET /api/settings/public，SSR 期由站点引导插件预载），
  所以这里不发任何请求：分组为空时页面必须仍然渲染出标题与占位，而不是白屏。
  未配置任何收款码时本页输出 noindex（内容页占位没有收录价值），配置后自动恢复索引。
-->
<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-gradient-to-br from-primary/10 via-accent/10 to-primary/5 mb-5">
        <Heart class="size-7 text-destructive" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ donate.title || t('sponsor.title') }}
      </h1>
      <p
        v-if="donate.description || t('sponsor.desc')"
        class="text-muted-foreground mt-3 leading-relaxed"
      >
        {{ donate.description || t('sponsor.desc') }}
      </p>
    </header>

    <div
      v-if="donate.methods.length"
      class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 max-w-4xl mx-auto"
    >
      <Card
        v-for="method in donate.methods"
        :key="method.name + method.image"
        class="text-center transition-all hover:shadow-soft duration-300"
      >
        <CardHeader class="p-5 pb-3">
          <CardTitle class="font-display text-base tracking-tight">
            {{ method.name || t('sponsor.scan') }}
          </CardTitle>
        </CardHeader>
        <CardContent class="px-5 pb-5">
          <div
            v-if="method.image"
            class="mx-auto rounded-xl border border-border bg-white p-3 max-w-[220px]"
          >
            <img
              :src="method.image"
              :alt="`${method.name || t('sponsor.scan')} ${t('sponsor.imageAlt')}`"
              class="size-full object-contain"
              loading="lazy"
              width="200"
              height="200"
            >
          </div>
          <p
            v-if="method.note"
            class="text-sm text-muted-foreground mt-3 leading-relaxed"
          >
            {{ method.note }}
          </p>
        </CardContent>
      </Card>
    </div>

    <div
      v-else
      class="text-center py-20"
    >
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <Heart class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">
        {{ t('sponsor.empty') }}
      </h3>
      <p class="text-sm text-muted-foreground mt-2">
        {{ t('sponsor.emptyHint') }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Heart } from '@lucide/vue'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle
} from '~~/components/ui/card'

definePageMeta({ layout: 'default' })

const { t } = useI18n()
const site = useSite()

const donate = computed(() => site.donate.value)

// noindex 只在"这一页其实没有内容"时成立；用 computed 而不是常量 true，
// 配置好收款码后必须自动回到可索引状态。
const sponsorEmpty = computed(() => !donate.value.enable || donate.value.methods.length === 0)

useSeo({
  title: computed(() => String(donate.value.title || t('sponsor.title'))),
  description: computed(() => String(donate.value.description || t('sponsor.desc'))),
  url: '/sponsor',
  type: 'website',
  noindex: sponsorEmpty
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home') as string, url: '/' },
  { name: t('sponsor.title') as string, url: '/sponsor' }
])
</script>
