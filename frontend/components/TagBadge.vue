<template>
  <NuxtLink
    v-if="to"
    :to="to"
    class="no-underline"
  >
    <span
      class="tag-chip inline-flex select-none items-center"
      :style="chipStyle"
    >
      <TagIcon
        v-if="showIcon"
        class="size-3 mr-1 opacity-75"
        :style="{ color: fg }"
      />
      <slot>{{ label }}</slot>
    </span>
  </NuxtLink>
  <span
    v-else
    class="tag-chip inline-flex select-none items-center"
    :style="chipStyle"
  >
    <TagIcon
      v-if="showIcon"
      class="size-3 mr-1 opacity-75"
      :style="{ color: fg }"
    />
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Tag as TagIcon } from '@lucide/vue'

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

/**
 * #RRGGBB → HSL 三元组（仅纯数字，不带单位）。
 * 之所以要转成 HSL 三元：main.css 中 .tag-colored /
 * 本组件 style 均使用 color-mix(in oklab, hsl(...) X%, ...)
 * 语法，hsl() 必须接收空格分隔的 "h s l" 三个纯数字。
 */
function hexToHsl(hex: string): { h: number, s: number, l: number } | null {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(String(hex).trim())
  if (!m) return null
  const r = parseInt(m[1] ?? '00', 16) / 255
  const g = parseInt(m[2] ?? '00', 16) / 255
  const b = parseInt(m[3] ?? '00', 16) / 255
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  let h = 0
  let s = 0
  const l = (max + min) / 2
  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case r:
        h = (g - b) / d + (g < b ? 6 : 0)
        break
      case g:
        h = (b - r) / d + 2
        break
      case b:
        h = (r - g) / d + 4
        break
    }
    h *= 60
  }
  return { h, s: s * 100, l: l * 100 }
}

/**
 * 根据背景色相对亮度计算前景色（WCAG 对比度友好）。
 * 浅色底 → 深色字；深色底 → 白色字。
 */
function hexRelativeLuminance(hex: string): number {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(String(hex).trim())
  if (!m) return 0.5
  const toLin = (v: number) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
  const r = toLin(parseInt(m[1] ?? '00', 16) / 255)
  const g = toLin(parseInt(m[2] ?? '00', 16) / 255)
  const b = toLin(parseInt(m[3] ?? '00', 16) / 255)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

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
