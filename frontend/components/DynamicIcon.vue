<!--
  通用图标渲染器：把接口里的 icon 字符串解析为 emoji / 图标组件 / 纯文本 / 空四态。
  解析真源在 composables/heroIcons.ts（无名称翻译层，直连 @heroicons/vue 版本化子路径，
  禁止 import 包根 Proxy）。带命名空间前缀的值（heroicons:/material-symbols:）认不出时
  兜底中性字形、绝不漏出原始字符串；无前缀值才允许降级为文本渲染。
-->
<script setup lang="ts">
import { computed } from 'vue'
import { Squares2X2Icon } from '@heroicons/vue/24/outline'
import { resolveIconComponent, isEmojiIcon } from '~~/composables/heroIcons'
import type { Component } from 'vue'

const props = withDefaults(defineProps<{
  icon: string
  class?: string
}>(), {
  class: 'size-4'
})

const resolved = computed(() => {
  const val = props.icon?.trim()
  if (!val) return { type: 'none' as const }

  if (isEmojiIcon(val)) {
    return { type: 'emoji' as const, text: val }
  }

  if (val.startsWith('heroicons') || (!val.includes(' ') && val.length > 1)) {
    const comp = resolveIconComponent(val)
    if (comp) return { type: 'component' as const, component: comp }

    // A namespaced value (`heroicons:…`, `material-symbols:…`) is unambiguously
    // meant to be an icon, so an unknown name should degrade to a neutral glyph
    // instead of leaking the raw string into the UI.
    if (val.includes(':')) {
      return { type: 'component' as const, component: Squares2X2Icon as Component }
    }
  }

  return { type: 'text' as const, text: val }
})

const iconComp = computed<Component | null>(() => {
  if (resolved.value.type === 'component') return resolved.value.component
  return null
})
</script>

<template>
  <component
    :is="iconComp"
    v-if="resolved.type === 'component' && iconComp"
    :class="props.class"
    aria-hidden="true"
  />
  <span
    v-else-if="resolved.type === 'emoji'"
    :class="props.class"
    role="img"
    aria-hidden="true"
  >{{ resolved.text }}</span>
  <span
    v-else-if="resolved.type === 'text'"
    :class="props.class"
    class="inline-flex items-center"
    aria-hidden="true"
  >{{ resolved.text }}</span>
</template>
