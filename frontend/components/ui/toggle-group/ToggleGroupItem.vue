<script setup lang="ts">
import type { ToggleGroupItemProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import type { ToggleVariants } from '@/components/ui/toggle'
import { reactiveOmit } from '@vueuse/core'
import { ToggleGroupItem, useForwardProps } from 'reka-ui'
import { inject } from 'vue'
import { cn } from '~~/lib/utils'
import { toggleVariants } from '@/components/ui/toggle'

const props = defineProps<ToggleGroupItemProps & {
  class?: HTMLAttributes['class']
  variant?: ToggleVariants['variant']
  size?: ToggleVariants['size']
}>()

const context = inject<ToggleVariants>('toggleGroup')

const delegatedProps = reactiveOmit(props, 'class', 'size', 'variant')

const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <ToggleGroupItem
    v-slot="slotProps"
    v-bind="forwardedProps"
    :class="cn(toggleVariants({
      variant: context?.variant || variant,
      size: context?.size || size
    }), props.class)"
  >
    <slot v-bind="slotProps" />
  </ToggleGroupItem>
</template>
