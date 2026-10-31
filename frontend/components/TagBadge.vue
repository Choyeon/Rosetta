<!--
  标签胶囊（淡色底 + 原色文字 + 无边框）：hex 经 hexToHsl 写入 --tag-h/s/l 局部令牌，
  scoped 样式再由这组令牌派生底/字/点色；color 为空时回落内置的 --primary-* 兜底值。
  暗色覆写挂在 html.dark 下、与 useTheme 写入的属性名绑定，改令牌名要两处同步。
  hover 禁止加 transform 位移：卡片容器已有 .lift-hover，嵌套变换会叠加错位。
-->
<template>
  <NuxtLink
    v-if="to"
    :to="to"
    class="no-underline"
  >
    <span
      class="tag-chip"
      :class="[`tag-${size}`]"
      :style="chipStyle"
    >
      <span
        v-if="showDot && !icon"
        class="tag-dot"
        aria-hidden="true"
      />
      <DynamicIcon
        v-if="icon"
        :icon="icon"
        class="tag-icon"
      />
      <Tag
        v-else-if="showIcon"
        class="tag-icon"
      />
      <slot>{{ label }}</slot>
    </span>
  </NuxtLink>
  <span
    v-else
    class="tag-chip"
    :class="[`tag-${size}`]"
    :style="chipStyle"
  >
    <span
      v-if="showDot && !icon"
      class="tag-dot"
      aria-hidden="true"
    />
    <DynamicIcon
      v-if="icon"
      :icon="icon"
      class="tag-icon"
    />
    <Tag
      v-else-if="showIcon"
      class="tag-icon"
    />
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import DynamicIcon from '~~/components/DynamicIcon.vue'
import { Tag } from '@lucide/vue'
import { hexToHsl } from '~~/lib/utils'

interface Props {
  color?: string | null
  label?: string
  to?: string
  /**
   * 标签图标（`TagResponse.icon`，heroicons 名或 emoji）。有值才渲染，且顶掉左侧圆点，
   * 免得点位 + 图标 + 文字三样挤在胶囊里。
   */
  icon?: string | null
  showIcon?: boolean
  showDot?: boolean
  size?: 'sm' | 'md'
}

const props = withDefaults(defineProps<Props>(), {
  color: null,
  label: '',
  to: undefined,
  icon: null,
  showIcon: false,
  showDot: true,
  size: 'md'
})

const hsl = computed(() => (props.color ? hexToHsl(props.color) : null))

const chipStyle = computed(() => {
  if (!hsl.value) return {}
  const { h, s, l } = hsl.value
  return { '--tag-h': String(h), '--tag-s': `${s}%`, '--tag-l': `${l}%` }
})
</script>

<style scoped>
.tag-chip {
  --tag-h: var(--primary-h, 200);
  --tag-s: var(--primary-s, 80%);
  --tag-l: var(--primary-l, 50%);

  --_bg: hsl(var(--tag-h) var(--tag-s) var(--tag-l) / 0.08);
  --_fg: hsl(var(--tag-h) calc(var(--tag-s) * 0.85) calc(var(--tag-l) * 0.55));
  --_border: hsl(var(--tag-h) var(--tag-s) var(--tag-l) / 0.16);
  --_dot: hsl(var(--tag-h) calc(var(--tag-s) * 0.9) calc(var(--tag-l) * 0.8));

  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  user-select: none;
  font-weight: 500;
  letter-spacing: 0.01em;
  line-height: 1;
  white-space: nowrap;

  color: var(--_fg);
  background: var(--_bg);
  border: 1px solid var(--_border);
  box-shadow: inset 0 1px 2px hsl(var(--tag-h) var(--tag-s) var(--tag-l) / 0.06);

  transition:
    background-color 200ms var(--motion-ease-standard, cubic-bezier(0.22, 1, 0.36, 1)),
    border-color 200ms var(--motion-ease-standard, cubic-bezier(0.22, 1, 0.36, 1)),
    box-shadow 200ms var(--motion-ease-standard, cubic-bezier(0.22, 1, 0.36, 1)),
    filter 200ms var(--motion-ease-standard, cubic-bezier(0.22, 1, 0.36, 1));
}

.tag-md {
  padding: 0.3rem 0.75rem;
  font-size: 0.8125rem;
  border-radius: 999px;
}

.tag-sm {
  padding: 0.15rem 0.5rem;
  font-size: 0.75rem;
  border-radius: 999px;
}

.tag-dot {
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 50%;
  background: var(--_dot);
  flex-shrink: 0;
  opacity: 0.85;
}

.tag-icon {
  width: 0.8em;
  height: 0.8em;
  flex-shrink: 0;
  opacity: 0.7;
}

/* ===== Dark mode ===== */
html.dark .tag-chip {
  --_bg: hsl(var(--tag-h) calc(var(--tag-s) * 0.75) calc(var(--tag-l) * 0.55) / 0.18);
  --_fg: hsl(var(--tag-h) calc(var(--tag-s) * 0.5) calc(65% + var(--tag-l) * 0.25));
  --_border: hsl(var(--tag-h) calc(var(--tag-s) * 0.65) calc(var(--tag-l) * 0.65) / 0.22);
  --_dot: hsl(var(--tag-h) calc(var(--tag-s) * 0.65) calc(var(--tag-l) * 0.75));
}

/* ===== Hover =====
 * 卡片内嵌套变换会与 .lift-hover 冲突，这里只做颜色/描边过渡，不做位移。 */
.tag-chip:hover {
  --_bg: hsl(var(--tag-h) var(--tag-s) var(--tag-l) / 0.14);
  --_border: hsl(var(--tag-h) var(--tag-s) var(--tag-l) / 0.28);
  filter: brightness(1.04);
  box-shadow: inset 0 1px 2px hsl(var(--tag-h) var(--tag-s) var(--tag-l) / 0.1);
}

html.dark .tag-chip:hover {
  --_bg: hsl(var(--tag-h) calc(var(--tag-s) * 0.75) calc(var(--tag-l) * 0.55) / 0.28);
  --_border: hsl(var(--tag-h) calc(var(--tag-s) * 0.65) calc(var(--tag-l) * 0.65) / 0.35);
  box-shadow: inset 0 1px 2px hsl(var(--tag-h) var(--tag-s) var(--tag-l) / 0.14);
}

/* NuxtLink wrapper should not add default underline */
a:has(.tag-chip) {
  text-decoration: none;
}
</style>
