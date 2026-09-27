<!--
  Admin 卡片外壳：视觉唯一来自 .card-surface（main.css 中性基座 + admin-ui.css 冻结装饰层），
  这里刻意不挂 .lift-hover —— 列表容器不要 hover 抬升，那是 StatCard 的观感。
  props.class 经 cn/twMerge 排在 padding 之后，所以消费方（AdminListPage 的 `p-0`）能压掉内边距；
  dense prop 目前全仓零调用点，要改留白请用 class，别再加分支。
-->
<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '~~/lib/utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
  /** 紧凑模式：更小的 padding，用于列表行等 */
  dense?: boolean
}>()
</script>

<template>
  <div
    :class="
      cn(
        'card-surface',
        props.dense ? 'p-3' : 'p-5',
        props.class
      )
    "
  >
    <slot />
  </div>
</template>
