<!--
  Admin 统一 Tabs 轨道。

  为什么需要它（不要退回页面内联 class）：
  shadcn `TabsTrigger` 基线自带 `data-[state=active]:bg-background` 与
  `data-[state=active]:text-foreground`。页面若用**无变体**的 `bg-primary` 去覆盖，
  tailwind-merge 会因「修饰符不同」判定为两组而同时保留两条类，最终由 CSS 特异性
  裁决 —— 带 `[data-state=active]` 属性选择器的那条赢，于是激活页签拿到白底；
  而 `data-[state=active]:text-primary-foreground` 与基线同修饰符，会被正常合并成白字。
  **白底 + 白字 = 页签标签整块隐形**（2026-10 生产实测：/admin/tools/seo 首个页签空白）。

  口径：覆盖激活态一律走同修饰符的 `data-[state=active]:*`，让 cn() 真正做冲突消解。
  回归见 tests/unit/adminTabsRecipe.spec.ts。
-->
<script setup lang="ts">
import type { TabsTriggerProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { TabsTrigger } from '~~/components/ui/tabs'
import { cn } from '~~/lib/utils'

const props = defineProps<TabsTriggerProps & { class?: HTMLAttributes['class'] }>()
</script>

<template>
  <TabsTrigger
    v-bind="props"
    :class="cn(
      'h-9 gap-2 rounded-lg px-3.5 text-[13px] font-medium',
      'text-muted-foreground hover:text-foreground',
      'data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm',
      props.class
    )"
  >
    <slot />
  </TabsTrigger>
</template>
