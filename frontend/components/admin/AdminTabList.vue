<!--
  Admin 统一 Tabs 容器：与 AdminTabTrigger 成对使用，全后台只保留这一套页签外观。
  基线 `bg-muted` 由 cn() 合并掉，改淡一档以免在玻璃卡上形成第二块重色面。

  高度必须是 `h-auto`（由 padding + 页签撑出来），不要在这里也不要在使用方写死 `h-*`：
  `overflow-x-auto` 按 CSS 规范会把 `overflow-y` 从 visible 强制成 auto，于是"容器比
  padding + 页签高度矮"就是一条竖直滚动条——仪表盘「流量总览 / 互动 & 内容」那排
  （h-8 容器 + p-1.5 + h-7 页签 = 40px 内容装进 32px）2026-10 线上实测就是这么出现的。
  需要更矮的观感时改 padding（`p-0.5` / `p-1`），别改高度。
  回归见 tests/unit/adminTabsRecipe.spec.ts。
-->
<script setup lang="ts">
import type { TabsListProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { TabsList } from '~~/components/ui/tabs'
import { cn } from '~~/lib/utils'

const props = defineProps<TabsListProps & { class?: HTMLAttributes['class'] }>()
</script>

<template>
  <TabsList
    v-bind="props"
    :class="cn('h-auto w-full justify-start gap-1 overflow-x-auto overflow-y-hidden rounded-xl bg-muted/50 p-1.5', props.class)"
  >
    <slot />
  </TabsList>
</template>
