<!--
  分类 chip（消费方：PostCard 两副骨架各一处 + pages/index.vue 两处），与 TagBadge 是「同色引擎、异形」兄弟：
  color 只收后端 hex 串，经 hexToHsl 规范化成一段 `hsl(h s% l%)` 写进局部 --cat-c 令牌，
  为 null 或非法时整套回落 hsl(var(--primary))（与 TagBadge 同一个引擎，异形而已）；
  暗色前景不是 dark: 变体，而是本文件 html.dark 段重算的 --_fg，改令牌名要两处同步。
  label 必须是调用方已按当前语言解析好的纯字符串（resolveLocalized(post.category.name)），不要传 i18n dict；
  左侧 2px .cat-accent 是分类/标签的刻意视觉区分（不受 Admin 禁彩条约束），hover 只换色不位移——位移会与卡片 .lift-hover 抢 transform。
-->
<script setup lang="ts">
import { FolderOpen } from '@lucide/vue'
import { computed } from 'vue'
import DynamicIcon from '~~/components/DynamicIcon.vue'
import { hexToHsl } from '~~/lib/utils'

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

/** hexToHsl 同时是合法性闸门：非 `#RRGGBB` 返回 null，进 DOM 的永远是规范化的 hsl() 串。 */
const chipStyle = computed(() => {
  const hsl = props.color ? hexToHsl(props.color) : null
  if (!hsl) return {}
  return { '--cat-c': `hsl(${Math.round(hsl.h)} ${Math.round(hsl.s)}% ${Math.round(hsl.l)}%)` }
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
      <FolderOpen
        v-else
        class="cat-icon"
      />
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
    <FolderOpen
      v-else
      class="cat-icon"
    />
    <span class="cat-label"><slot>{{ label }}</slot></span>
  </span>
</template>

<style scoped>
/*
 * Colour engine mirrors TagBadge on purpose (one --cat-c token + oklab mixes)
 * so both chips react identically to light/dark. The *appearance* is kept
 * deliberately different:
 *   · TagBadge      -> pill (rounded-full), leading dot, tag glyph
 *   · CategoryBadge -> rounded rectangle, leading colour bar, category's own icon
 */
.cat-chip {
  --_c: var(--cat-c, hsl(var(--primary)));

  --_bg: color-mix(in oklab, var(--_c) 18%, hsl(var(--card)));
  --_fg: color-mix(in oklab, var(--_c) 55%, black);
  --_border: color-mix(in oklab, var(--_c) 30%, transparent);
  --_accent: var(--_c);

  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  user-select: none;
  font-weight: 500;
  letter-spacing: 0.01em;
  line-height: 1;
  white-space: nowrap;
  /* 与 TagBadge 同一套窄屏兜底：超长分类名最多占满容器，文字省略而非撑破卡片。 */
  max-width: 100%;
  min-width: 0;

  color: var(--_fg);
  background: var(--_bg);
  border: 1px solid var(--_border);
  box-shadow: inset 0 1px 2px color-mix(in oklab, var(--_c) 10%, transparent);

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
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  --_bg: color-mix(in oklab, var(--_c) 22%, hsl(var(--card)));
  --_fg: color-mix(in oklab, var(--_c) 50%, white);
  --_border: color-mix(in oklab, var(--_c) 40%, transparent);
  /* 深色分类色（如 slate-800）在暗卡上几乎看不见，彩条先往白提一档再用 */
  --_accent: color-mix(in oklab, var(--_c) 78%, white);
}

/* ===== Hover =====
 * 卡片内嵌套变换会与 .lift-hover 冲突，这里只做颜色/描边过渡，不做位移。 */
a:hover > .cat-chip,
.cat-chip:hover {
  --_bg: color-mix(in oklab, var(--_c) 26%, hsl(var(--card)));
  --_border: color-mix(in oklab, var(--_c) 45%, transparent);
  filter: brightness(1.04);
  box-shadow: inset 0 1px 2px color-mix(in oklab, var(--_c) 14%, transparent);
}

html.dark a:hover > .cat-chip,
html.dark .cat-chip:hover {
  --_bg: color-mix(in oklab, var(--_c) 32%, hsl(var(--card)));
  --_border: color-mix(in oklab, var(--_c) 52%, transparent);
  box-shadow: inset 0 1px 2px color-mix(in oklab, var(--_c) 20%, transparent);
}

/* keep NuxtLink from underlining the chip */
a:has(> .cat-chip) {
  text-decoration: none;
}
</style>
