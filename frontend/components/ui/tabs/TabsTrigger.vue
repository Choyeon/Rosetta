<script setup lang="ts">
import type { TabsTriggerProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { reactiveOmit } from '@vueuse/core'
import { TabsTrigger, useForwardProps } from 'reka-ui'
import { cn } from '~~/lib/utils'

const props = defineProps<TabsTriggerProps & { class?: HTMLAttributes['class'] }>()

const delegatedProps = reactiveOmit(props, 'class')

const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <TabsTrigger
    v-bind="forwardedProps"
    :class="cn(
      'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm',
      props.class
    )"
  >
    <!-- 容器：inline-flex，保证 icon + label 始终同一行；子 span 内部 truncate 处理超长文本。
         修复：原 class="truncate" 是 block，会把前/后 icon 挤到另一行造成垂直堆叠 -->
    <span class="inline-flex items-center gap-1 min-w-0 max-w-full leading-none align-middle">
      <slot />
    </span>
  </TabsTrigger>
</template>
