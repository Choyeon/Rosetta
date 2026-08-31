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
  <!-- Compact variant (same layout as PostCard compact) -->
  <article
    v-if="variant === 'compact'"
    :class="cn('card-surface overflow-hidden flex gap-0 text-card-foreground', className)"
  >
    <Skeleton class="shrink-0 w-[120px] sm:w-[168px] md:w-[180px] aspect-[4/3] sm:aspect-auto sm:h-auto sm:min-h-full rounded-none" />
    <div class="flex-1 min-w-0 p-4 sm:p-5 flex flex-col gap-2">
      <!-- Badge / tag row -->
      <div class="flex items-center gap-2 flex-wrap">
        <Skeleton class="h-5 w-16 rounded-full" />
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
      <!-- Footer meta -->
      <div class="mt-auto pt-3 flex items-center justify-between gap-3">
        <div class="flex items-center gap-2 min-w-0">
          <Skeleton class="size-5 rounded-full" />
          <Skeleton class="h-3 w-16 rounded-full" />
          <Skeleton class="h-3 w-20 rounded-full" />
        </div>
        <div class="flex items-center gap-3 shrink-0">
          <Skeleton class="h-3 w-8 rounded-full" />
          <Skeleton class="h-3 w-8 rounded-full" />
        </div>
      </div>
    </div>
  </article>

  <!-- Default variant (same layout as PostCard default with cover image) -->
  <article
    v-else
    :class="cn('card-surface overflow-hidden text-card-foreground', className)"
  >
    <Skeleton class="block aspect-[16/9] rounded-none" />
    <div class="p-5 pb-0 flex flex-col gap-3">
      <!-- Badge / tag row -->
      <div class="flex items-center gap-2 flex-wrap">
        <Skeleton class="h-5 w-20 rounded-full" />
        <Skeleton class="h-5 w-16 rounded-full" />
        <Skeleton class="h-5 w-14 rounded-full" />
        <Skeleton class="h-5 w-14 rounded-full" />
      </div>
      <!-- Title (line-clamp 2) -->
      <div class="flex flex-col gap-2">
        <Skeleton class="h-6 w-full" />
        <Skeleton class="h-6 w-5/6" />
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
    <div
      class="flex items-center justify-between mt-2 gap-3 p-5 pt-0"
      style="border-top:1px solid color-mix(in oklab, hsl(var(--foreground)) 6%, transparent)"
    >
      <div class="flex items-center gap-2 min-w-0">
        <Skeleton class="size-6 rounded-full" />
        <Skeleton class="h-3 w-20 rounded-full" />
        <Skeleton class="h-3 w-24 rounded-full" />
      </div>
      <div class="flex items-center gap-3 shrink-0">
        <Skeleton class="h-3 w-10 rounded-full" />
        <Skeleton class="h-3 w-10 rounded-full" />
      </div>
    </div>
  </article>
</template>
