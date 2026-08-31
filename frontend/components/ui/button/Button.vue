<script setup lang="ts">
/**
 * 极简 SSR 安全 Button：
 *  - 不使用 reka-ui/Primitive（规避其 SSR span/button mismatch）
 *  - 不做模板分支；只用 <component :is> + v-if 两个分支
 *  - 完全无副作用地处理 asChild（简单透传 slot）
 */
import type { HTMLAttributes } from 'vue'
import type { ButtonVariants } from '.'
import { cn } from '~~/lib/utils'
import { buttonVariants } from '.'

interface Props {
  as?: string
  asChild?: boolean
  variant?: ButtonVariants['variant']
  size?: ButtonVariants['size']
  /** className 等价于 class；别名避开 TS 模板解析歧义（`class` 是保留字） */
  className?: HTMLAttributes['class']
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
}

const props = withDefaults(defineProps<Props>(), {
  as: 'button',
  asChild: false,
  type: 'button'
})

const attrs = useAttrs()
</script>

<template>
  <!-- asChild=true：简单透传 slot，不做任何 VNode 改写，无副作用 -->
  <slot v-if="asChild" />
  <!-- 普通按钮：动态组件 + v-bind="attrs"（事件/属性全部透传） -->
  <component
    :is="as"
    v-else
    :type="as === 'button' ? type : undefined"
    :disabled="disabled"
    :class="cn(buttonVariants({ variant: props.variant, size: props.size }), props.className, attrs.class)"
    v-bind="attrs"
  >
    <slot />
  </component>
</template>
