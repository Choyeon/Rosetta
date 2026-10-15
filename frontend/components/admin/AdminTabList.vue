<!--
  Admin 统一 Tabs 容器：与 AdminTabTrigger 成对使用，全后台只保留这一套页签外观。
  基线 `bg-muted` 由 cn() 合并掉，改淡一档以免在玻璃卡上形成第二块重色面。
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
    :class="cn('h-11 justify-start gap-1 rounded-xl bg-muted/50 p-1.5', props.class)"
  >
    <slot />
  </TabsList>
</template>
