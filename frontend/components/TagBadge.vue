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
        v-if="showDot"
        class="tag-dot"
        aria-hidden="true"
      />
      <svg
        v-if="showIcon"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        class="tag-icon"
        aria-hidden="true"
      ><path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z" /><circle
        cx="7.5"
        cy="7.5"
        r=".5"
        fill="currentColor"
      /></svg>
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
      v-if="showDot"
      class="tag-dot"
      aria-hidden="true"
    />
    <svg
      v-if="showIcon"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-linecap="round"
      stroke-linejoin="round"
      stroke-width="2"
      class="tag-icon"
      aria-hidden="true"
    ><path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z" /><circle
      cx="7.5"
      cy="7.5"
      r=".5"
      fill="currentColor"
    /></svg>
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { hexToHsl } from '~~/lib/utils'

interface Props {
  color?: string | null
  label?: string
  to?: string
  showIcon?: boolean
  showDot?: boolean
  size?: 'sm' | 'md'
}

const props = withDefaults(defineProps<Props>(), {
  color: null,
  label: '',
  to: undefined,
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
