<!--
  捐助页：后台「站点设置 → 捐助打赏」（settings 分组 donate）的唯一前台落点。
  数据源是 useSite().donate（来自 GET /api/settings/public，SSR 期由站点引导插件预载），
  所以这里不发任何请求：分组为空时页面必须仍然渲染出标题与占位，而不是白屏。
  打赏墙（donate.sponsors + donate.show_sponsors_list）读同一份分组值，
  与 GET /api/sponsors（主题/插件用的公开读口）同源的同一份数，不是第二个数据源。
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

    <!-- 打赏墙：名单与开关同属 donate 分组（后台「捐助打赏」维护），
         关开关或名单为空时整块不出现，不留空标题。 -->
    <section
      v-if="showDonors"
      class="mt-14 max-w-3xl mx-auto"
    >
      <h2 class="font-display text-lg font-semibold text-center mb-6">
        {{ t('sponsor.donorTitle') }}
      </h2>
      <ul class="flex flex-wrap justify-center gap-3">
        <li
          v-for="(donor, index) in sponsors"
          :key="donor.name + index"
          class="flex items-center gap-2.5 rounded-full border border-border bg-card py-1.5 pe-4 ps-1.5"
        >
          <img
            v-if="donor.avatar"
            :src="donor.avatar"
            :alt="donor.name"
            class="size-8 rounded-full object-cover"
            loading="lazy"
            width="32"
            height="32"
          >
          <span
            v-else
            class="inline-flex size-8 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary"
            aria-hidden="true"
          >{{ donor.name.slice(0, 1) }}</span>
          <span class="text-sm font-medium">{{ donor.name }}</span>
          <span
            v-if="donor.amount"
            class="text-xs text-muted-foreground"
          >{{ donor.amount }}</span>
          <span
            v-if="donor.date"
            class="text-xs text-muted-foreground"
          >{{ donor.date }}</span>
        </li>
      </ul>
    </section>
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
const sponsors = computed(() => site.donate.value.sponsors)
const showDonors = computed(
  () => site.donate.value.show_sponsors_list && sponsors.value.length > 0
)

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
