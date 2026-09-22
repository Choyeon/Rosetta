<script setup lang="ts">
import { computed } from 'vue'
import { hexToHsl } from '~~/lib/utils'
import DynamicIcon from '~~/components/DynamicIcon.vue'

interface Props {
  color?: string | null
  label?: string
  to?: string
  /** heroicons name (`heroicons:folder`) or emoji; falls back to a folder glyph. */
  icon?: string | null
  size?: 'sm' | 'md'
}

const props = withDefaults(defineProps<Props>(), {
  color: null,
  label: '',
  to: undefined,
  icon: null,
  size: 'md'
})

const hsl = computed(() => (props.color ? hexToHsl(props.color) : null))

const chipStyle = computed(() => {
  if (!hsl.value) return {}
  const { h, s, l } = hsl.value
  return { '--cat-h': String(h), '--cat-s': `${s}%`, '--cat-l': `${l}%` }
})
</script>

<template>
  <NuxtLink
    v-if="to"
    :to="to"
    class="no-underline"
  >
    <span
      class="cat-chip"
      :class="[`cat-${size}`]"
      :style="chipStyle"
    >
      <span
        class="cat-accent"
        aria-hidden="true"
      />
      <DynamicIcon
        v-if="icon"
        :icon="icon"
        class="cat-icon"
      />
      <svg
        v-else
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        class="cat-icon"
        aria-hidden="true"
      ><path d="m6 14 1.45-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.55 6a2 2 0 0 1-1.94 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.93a2 2 0 0 1 1.66.9l.82 1.2a2 2 0 0 0 1.66.9H18a2 2 0 0 1 2 2v2" /></svg>
      <span class="cat-label"><slot>{{ label }}</slot></span>
    </span>
  </NuxtLink>
  <span
    v-else
    class="cat-chip"
    :class="[`cat-${size}`]"
    :style="chipStyle"
  >
    <span
      class="cat-accent"
      aria-hidden="true"
    />
    <DynamicIcon
      v-if="icon"
      :icon="icon"
      class="cat-icon"
    />
    <svg
      v-else
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-linecap="round"
      stroke-linejoin="round"
      stroke-width="2"
      class="cat-icon"
      aria-hidden="true"
    ><path d="m6 14 1.45-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.55 6a2 2 0 0 1-1.94 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.93a2 2 0 0 1 1.66.9l.82 1.2a2 2 0 0 0 1.66.9H18a2 2 0 0 1 2 2v2" /></svg>
    <span class="cat-label"><slot>{{ label }}</slot></span>
  </span>
</template>

<style scoped>
/*
 * Colour engine mirrors TagBadge on purpose (same HSL custom-property approach)
 * so both chips react identically to light/dark. The *appearance* is kept
 * deliberately different:
 *   · TagBadge      -> pill (rounded-full), leading dot, tag glyph
 *   · CategoryBadge -> rounded rectangle, leading colour bar, category's own icon
 */
.cat-chip {
  --cat-h: var(--primary-h, 200);
  --cat-s: var(--primary-s, 80%);
  --cat-l: var(--primary-l, 50%);

  --_bg: hsl(var(--cat-h) var(--cat-s) var(--cat-l) / 0.1);
  --_fg: hsl(var(--cat-h) calc(var(--cat-s) * 0.9) calc(var(--cat-l) * 0.48));
  --_border: hsl(var(--cat-h) var(--cat-s) var(--cat-l) / 0.22);
  --_accent: hsl(var(--cat-h) calc(var(--cat-s) * 0.95) calc(var(--cat-l) * 0.6));

  position: relative;
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
  box-shadow: inset 0 1px 2px hsl(var(--cat-h) var(--cat-s) var(--cat-l) / 0.05);

  transition:
    background-color 200ms var(--motion-ease-standard, cubic-bezier(0.22, 1, 0.36, 1)),
    border-color 200ms var(--motion-ease-standard, cubic-bezier(0.22, 1, 0.36, 1)),
    box-shadow 200ms var(--motion-ease-standard, cubic-bezier(0.22, 1, 0.36, 1)),
    filter 200ms var(--motion-ease-standard, cubic-bezier(0.22, 1, 0.36, 1));
}

/* left colour bar: the visual signature that separates category from tag.
 * 2px 圆角短线，上下内缩 5px，不再依赖 overflow:hidden 裁切圆角。 */
.cat-accent {
  position: absolute;
  inset-block: 5px;
  inset-inline-start: 3px;
  width: 2px;
  border-radius: 999px;
  background: var(--_accent);
}

.cat-icon {
  width: 0.85em;
  height: 0.85em;
  flex-shrink: 0;
  opacity: 0.75;
}

.cat-label {
  display: inline-block;
  min-width: 0;
}

/* rectangular, NOT a pill — on purpose */
.cat-md {
  padding: 0.3rem 0.7rem 0.3rem 0.75rem;
  font-size: 0.8125rem;
  border-radius: 0.375rem;
}

.cat-sm {
  padding: 0.15rem 0.5rem 0.15rem 0.6rem;
  font-size: 0.75rem;
  border-radius: 0.3125rem;
}

/* ===== Dark mode ===== */
html.dark .cat-chip {
  --_bg: hsl(var(--cat-h) calc(var(--cat-s) * 0.7) calc(var(--cat-l) * 0.55) / 0.2);
  --_fg: hsl(var(--cat-h) calc(var(--cat-s) * 0.45) calc(68% + var(--cat-l) * 0.2));
  --_border: hsl(var(--cat-h) calc(var(--cat-s) * 0.6) calc(var(--cat-l) * 0.6) / 0.3);
  --_accent: hsl(var(--cat-h) calc(var(--cat-s) * 0.7) calc(var(--cat-l) * 0.72));
}

/* ===== Hover =====
 * 卡片内嵌套变换会与 .lift-hover 冲突，这里只做颜色/描边过渡，不做位移。 */
a:hover > .cat-chip,
.cat-chip:hover {
  --_bg: hsl(var(--cat-h) var(--cat-s) var(--cat-l) / 0.17);
  --_border: hsl(var(--cat-h) var(--cat-s) var(--cat-l) / 0.36);
  filter: brightness(1.04);
  box-shadow: inset 0 1px 2px hsl(var(--cat-h) var(--cat-s) var(--cat-l) / 0.09);
}

html.dark a:hover > .cat-chip,
html.dark .cat-chip:hover {
  --_bg: hsl(var(--cat-h) calc(var(--cat-s) * 0.7) calc(var(--cat-l) * 0.55) / 0.3);
  --_border: hsl(var(--cat-h) calc(var(--cat-s) * 0.6) calc(var(--cat-l) * 0.6) / 0.45);
  box-shadow: inset 0 1px 2px hsl(var(--cat-h) var(--cat-s) var(--cat-l) / 0.14);
}

/* keep NuxtLink from underlining the chip */
a:has(> .cat-chip) {
  text-decoration: none;
}
</style>
