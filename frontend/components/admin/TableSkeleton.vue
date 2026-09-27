<!--
  表格骨架，当前唯一消费方是 components/admin/plugins/PluginManager.vue（挂在 CardContent 之后，:rows="8" :cols="4"）。
  cols/rows 与真实表格列数没有任何联动，换表结构必须手工改这里的 props，否则骨架与成品宽度跳变。
  本组件不声明 class prop，消费方的 `class="border-0 rounded-none"` 只能属性透传到外层 w-full div，
  真正画边框的是内层 `rounded-xl border border-border bg-card`——想中和外框得改内层，别指望外部 class。
-->
<script setup lang="ts">
import Skeleton from '~~/components/ui/skeleton/Skeleton.vue'

interface Props {
  /** Number of body rows to render (default 6) */
  rows?: number
  /** Number of columns (default 5) */
  cols?: number
  /** Show skeleton for table header row (default true) */
  showHeader?: boolean
  /** Show pagination bar skeleton at bottom (default true) */
  showPagination?: boolean
}

withDefaults(defineProps<Props>(), {
  rows: 6,
  cols: 5,
  showHeader: true,
  showPagination: true
})
</script>

<template>
  <div class="w-full">
    <div class="rounded-xl border border-border overflow-hidden bg-card">
      <!-- Header skeleton -->
      <div
        v-if="showHeader"
        class="flex items-center gap-4 px-4 py-3 border-b border-border bg-muted/40"
      >
        <Skeleton
          v-for="c in cols"
          :key="`th-${c}`"
          class="h-4 flex-1 rounded-full"
          :class="c === 1 ? 'max-w-[40%]' : ''"
        />
        <Skeleton class="h-4 w-20 shrink-0 rounded-full opacity-60" />
      </div>

      <!-- Body rows -->
      <div class="flex flex-col">
        <div
          v-for="r in rows"
          :key="`tr-${r}`"
          class="flex items-center gap-4 px-4 py-3.5 border-b border-border/60 last:border-b-0"
        >
          <Skeleton
            v-for="c in cols"
            :key="`td-${r}-${c}`"
            class="h-4 flex-1 rounded-full"
            :class="[
              c === 1 ? 'max-w-[40%]' : '',
              c === 2 ? 'w-24' : ''
            ]"
          />
          <div class="w-20 shrink-0 flex items-center justify-end gap-2">
            <Skeleton class="h-7 w-7 rounded-md opacity-50" />
            <Skeleton class="h-7 w-7 rounded-md opacity-50" />
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination skeleton -->
    <div
      v-if="showPagination"
      class="flex items-center justify-between mt-4 px-1"
    >
      <Skeleton class="h-4 w-40 rounded-full" />
      <div class="flex items-center gap-2">
        <Skeleton class="h-9 w-9 rounded-lg" />
        <Skeleton class="h-9 w-9 rounded-lg" />
        <Skeleton class="h-9 w-9 rounded-lg" />
        <Skeleton class="h-9 w-9 rounded-lg" />
        <Skeleton class="h-9 w-9 rounded-lg" />
      </div>
    </div>
  </div>
</template>
