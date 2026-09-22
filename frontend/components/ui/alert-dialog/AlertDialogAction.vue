<script setup lang="ts">
import type { AlertDialogActionProps } from 'reka-ui'
import type { VariantProps } from 'class-variance-authority'
import type { HTMLAttributes } from 'vue'
import { reactiveOmit } from '@vueuse/core'
import { AlertDialogAction } from 'reka-ui'
import { cn } from '~~/lib/utils'
import { buttonVariants } from '@/components/ui/button'

type ButtonVariants = VariantProps<typeof buttonVariants>

const props = defineProps<AlertDialogActionProps & {
  class?: HTMLAttributes['class']
  variant?: ButtonVariants['variant']
}>()

const delegatedProps = reactiveOmit(props, 'class', 'variant')
</script>

<template>
  <AlertDialogAction
    v-bind="delegatedProps"
    :class="cn(buttonVariants({ variant: props.variant }), props.class)"
  >
    <slot />
  </AlertDialogAction>
</template>
