<!--
  列表卡片上的「预计阅读 N 分钟」（批次 #136）。

  分钟数只有一个来源：后端持久化的 `reading_time` 列（列表接口刻意 defer(content)，
  正文不进载荷，前端无从复算）。详情页此前自己按 380 字/分钟复算一遍，同一篇文章
  卡片 6 分钟、正文页 4 分钟，读者会以为点开了另一篇；现在两边读同一个键，
  估算只留给编辑器当即时反馈（`lib/postEditor.ts` 的契约本来就是这么写的）。

  闸门与详情页同源：后台「阅读体验 › 显示预估阅读时间」关掉后，卡片和正文页一起收起。
  值来自 SSR 载荷 + useSite 的首屏默认值（两端同值），不产生 Hydrate 差异。
-->
<template>
  <span
    v-if="minutes"
    class="inline-flex items-center gap-1 shrink-0 tabular-nums"
    :title="t('post.readingTime')"
  >
    <Clock3
      class="size-3.5 shrink-0"
      aria-hidden="true"
    />
    {{ minutes }} {{ t('post.minRead') }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Clock3 } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

interface Props {
  post: {
    reading_time?: number | null
  }
}

const props = defineProps<Props>()
const { t } = useI18n()
const site = useSite()

/**
 * 只认后端给的正整数：键缺失（旧缓存载荷）、0、脏值一律整段不显示，
 * 而不是让访客看到「undefined 分钟阅读」——卡片是爬虫与读者共用的一面。
 */
const minutes = computed(() => {
  if (!site.reading.value.show_reading_time) return null
  const n = Number(props.post.reading_time)
  return Number.isInteger(n) && n > 0 ? n : null
})
</script>
