<script setup lang="ts">
import type { SeparatorProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { reactiveOmit } from '@vueuse/core'
import { cn } from '~~/lib/utils'

const props = withDefaults(defineProps<
  SeparatorProps & { class?: HTMLAttributes['class'] }
>(), {
  orientation: 'horizontal',
  decorative: true
})

const delegatedProps = reactiveOmit(props, 'class')

// ====== 为什么不用 reka-ui 的 <Separator>（2026-10-01）======
// Nitro SSR 环境下 reka（外置依赖）组件渲染为空 <!---->（与 @lucide/vue 同一
// 现象），导致每个 SSR 分隔线都是 "server: comment / client: div" 节点级
// hydration mismatch（AppFooter/AppHeader 等非 ClientOnly 区域）。
// reka Separator 的 DOM 输出就是确定性的单个 <div>，这里用原生模板字节级
// 复刻（role/data-orientation/aria-orientation 语义一致），两端渲染恒等。
</script>

<template>
  <div
    :role="delegatedProps.decorative ? 'none' : 'separator'"
    :aria-orientation="delegatedProps.decorative ? undefined : delegatedProps.orientation"
    :data-orientation="delegatedProps.orientation"
    :class="
      cn(
        'shrink-0 bg-border',
        props.orientation === 'horizontal' ? 'h-px w-full' : 'w-px h-full',
        props.class
      )
    "
  />
</template>
