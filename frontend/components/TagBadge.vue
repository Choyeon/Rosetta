<template>
  <NuxtLink
    v-if="to"
    :to="to"
    class="no-underline"
  >
    <span
      class="tag-chip inline-flex select-none items-center gap-1"
      :style="chipStyle"
    >
      <TagIcon
        v-if="showIcon"
        class="size-3 opacity-75"
        :style="{ color: fg }"
      />
      <slot>{{ label }}</slot>
    </span>
  </NuxtLink>
  <span
    v-else
    class="tag-chip inline-flex select-none items-center gap-1"
    :style="chipStyle"
  >
    <TagIcon
      v-if="showIcon"
      class="size-3 opacity-75"
      :style="{ color: fg }"
    />
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Tag as TagIcon } from '@lucide/vue'
import { hexToHsl, hexRelativeLuminance } from '~~/lib/utils'

interface Props {
  /** 十六进制颜色值（示例：#0EA5A9）。为空则使用主题 primary 色。 */
  color?: string | null
  /** 标签显示文本；也可以用默认 slot 传。 */
  label?: string
  /** 跳转地址。传了就渲染 NuxtLink，否则渲染 span。 */
  to?: string
  /** 是否显示 Tag 图标（详情页建议 true；列表紧凑行建议 false）。 */
  showIcon?: boolean
  /** 尺寸大小，列表紧凑卡片建议 sm。 */
  size?: 'sm' | 'md'
}

const props = withDefaults(defineProps<Props>(), {
  color: null,
  label: '',
  to: undefined,
  showIcon: false,
  size: 'md'
})

const hsl = computed(() => (props.color ? hexToHsl(props.color) : null))

/** h s l 空格分隔的字符串，直接喂给 hsl(...) 语法。 */
const hslTriple = computed(() =>
  hsl.value ? `${hsl.value.h} ${hsl.value.s}% ${hsl.value.l}%` : 'var(--primary)'
)

const luminance = computed(() =>
  props.color ? hexRelativeLuminance(props.color) : 0.5
)

/** 背景较浅时文字用深色，否则用白色。 */
const fg = computed(() => (luminance.value > 0.6 ? '#0f172a' : '#ffffff'))

const chipStyle = computed<Record<string, string>>(() => {
  const padding = props.size === 'sm' ? '0.125rem 0.5rem' : '0.2rem 0.625rem'
  const fontSize = props.size === 'sm' ? '0.66rem' : '0.72rem'
  const radius = props.size === 'sm' ? '999px' : '999px'
  return {
    padding,
    fontSize,
    borderRadius: radius,
    lineHeight: '1.4',
    color: fg.value,
    background: `color-mix(in oklab, hsl(${hslTriple.value}) 18%, hsl(var(--muted)))`,
    border: `1px solid color-mix(in oklab, hsl(${hslTriple.value}) 30%, transparent)`,
    transition: 'filter 180ms ease, transform 180ms ease'
  }
})
</script>

<style scoped>
.tag-chip {
  font-weight: 500;
  letter-spacing: 0.01em;
}
.tag-chip:hover {
  filter: brightness(1.05) saturate(1.05);
}
</style>
