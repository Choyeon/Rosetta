<script setup lang="ts">
import { cn } from '~~/lib/utils'
import Skeleton from '~~/components/ui/skeleton/Skeleton.vue'

type Variant = 'default' | 'compact'

defineProps<{
  variant?: Variant
  className?: string
}>()
</script>

<template>
  <!-- Compact variant (mirrors PostCard compact: cover tile + sm chips + icon meta row) -->
  <article
    v-if="variant === 'compact'"
    :class="cn('card-surface overflow-hidden flex gap-0 text-card-foreground', className)"
  >
    <!-- 封面/占位砖块列（与 PostCard 的封面或 FileImage 占位块同宽高） -->
    <Skeleton class="shrink-0 w-[120px] sm:w-[168px] md:w-[180px] aspect-[4/3] sm:aspect-auto sm:h-auto sm:min-h-full rounded-none" />
    <div class="flex-1 min-w-0 p-4 sm:p-5 flex flex-col gap-2">
      <!-- Badge row：首个为矩形分类 chip（rounded-md），其后为胶囊 Tag chip -->
      <div class="flex items-center gap-2 flex-wrap">
        <Skeleton class="h-5 w-16 rounded-md" />
        <Skeleton class="h-5 w-20 rounded-full" />
        <Skeleton class="h-5 w-14 rounded-full" />
      </div>
      <!-- Title (line-clamp 2) -->
      <div class="flex flex-col gap-1.5 mt-1">
        <Skeleton class="h-5 w-full sm:h-[1.375rem]" />
        <Skeleton class="h-5 w-4/5 sm:h-[1.375rem]" />
      </div>
      <!-- Excerpt (line-clamp 2) -->
      <div class="flex flex-col gap-1.5 mt-1">
        <Skeleton class="h-4 w-full" />
        <Skeleton class="h-4 w-3/4" />
      </div>
      <!-- Footer meta：头像 + 名称 + size-3.5 日历图标 + 日期；右侧浏览/评论（size-3.5 图标） -->
      <div class="mt-auto pt-3 flex items-center justify-between gap-3">
        <div class="flex items-center gap-2 min-w-0">
          <Skeleton class="size-5 rounded-full" />
          <Skeleton class="h-3 w-16 rounded-full" />
          <Skeleton class="size-3.5 rounded-sm" />
          <Skeleton class="h-3 w-16 rounded-full" />
        </div>
        <div class="flex items-center gap-3 shrink-0">
          <span class="inline-flex items-center gap-1">
            <Skeleton class="size-3.5 rounded-full" />
            <Skeleton class="h-3 w-6" />
          </span>
          <span class="inline-flex items-center gap-1">
            <Skeleton class="size-3.5 rounded-full" />
            <Skeleton class="h-3 w-6" />
          </span>
        </div>
      </div>
    </div>
  </article>

  <!-- Default variant (mirrors PostCard default: 16/9 cover tile + md chips + bordered footer meta) -->
  <article
    v-else
    :class="cn('card-surface overflow-hidden text-card-foreground', className)"
  >
    <Skeleton class="block aspect-[16/9] rounded-none" />
    <div class="p-5 pb-0 flex flex-col gap-3">
      <!-- Badge row：首个为矩形分类 chip（rounded-md），其后为胶囊 Tag chip；md chip 实际高约 h-6 -->
      <div class="flex items-center gap-2 flex-wrap">
        <Skeleton class="h-6 w-20 rounded-md" />
        <Skeleton class="h-6 w-16 rounded-full" />
        <Skeleton class="h-6 w-14 rounded-full" />
        <Skeleton class="h-6 w-14 rounded-full" />
      </div>
      <!-- Title (line-clamp 2, text-xl leading-snug) -->
      <div class="flex flex-col gap-2">
        <Skeleton class="h-7 w-full" />
        <Skeleton class="h-7 w-5/6" />
      </div>
    </div>
    <div class="p-5 pt-3">
      <!-- Excerpt (line-clamp 3) -->
      <div class="flex flex-col gap-1.5">
        <Skeleton class="h-4 w-full" />
        <Skeleton class="h-4 w-full" />
        <Skeleton class="h-4 w-2/3" />
      </div>
    </div>
    <!-- Footer：border-top 与 PostCard 一致使用 border token -->
    <div
      class="flex items-center justify-between mt-2 gap-3 p-5 pt-0 border-t border-border/60"
    >
      <div class="flex items-center gap-2 min-w-0">
        <Skeleton class="size-6 rounded-full" />
        <Skeleton class="h-3 w-20 rounded-full" />
        <Skeleton class="size-3.5 rounded-sm" />
        <Skeleton class="h-3 w-16 rounded-full" />
      </div>
      <div class="flex items-center gap-3 shrink-0">
        <span class="inline-flex items-center gap-1">
          <Skeleton class="size-3.5 rounded-full" />
          <Skeleton class="h-3 w-8" />
        </span>
        <span class="inline-flex items-center gap-1">
          <Skeleton class="size-3.5 rounded-full" />
          <Skeleton class="h-3 w-8" />
        </span>
      </div>
    </div>
  </article>
</template>
