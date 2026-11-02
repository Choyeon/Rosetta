<!--
  标签胶囊（同色相浓涂）：后端 hex 直接写进一个局部令牌 --tag-c，其余底/字/点/描边
  全部用 color-mix(in oklab) 从它派生；color 为空时 --tag-c 回落 hsl(var(--primary))，
  所以未配色的标签跟随主题主色。暗色覆写挂在 html.dark 下、与 useTheme 写入的属性名绑定，
  改令牌名要两处同步。
  为什么不用 h/s/l 三变量：:root 的 --primary 是"一个不带分隔符的 HSL 三元组"
  （`--primary: 199 100% 33%`），CSS 侧拆不出 h/s/l，任何 `calc(var(--tag-s) * .85)` 式的
  减饱和派生都只能靠 JS 先解一遍——那套 --tag-h/--tag-s/--tag-l 还顺手引用了仓库里
  根本不存在的 --primary-h/-s/-l，于是没配色的标签永远渲染成同一个褪色的蓝。
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

/**
 * hexToHsl 在这里同时充当"合法性闸门"：非 `#RRGGBB`（含库里历史脏值）直接返回 null，
 * 于是进 DOM 的永远是一段规范化的 `hsl(h s% l%)`，而不是调用方自备的任意字符串。
 * 取整是纯函数、两端同值，不会引入 hydration 差异。
 */
const chipStyle = computed(() => {
  const hsl = props.color ? hexToHsl(props.color) : null
  if (!hsl) return {}
  return { '--tag-c': `hsl(${Math.round(hsl.h)} ${Math.round(hsl.s)}% ${Math.round(hsl.l)}%)` }
})
</script>

<style scoped>
.tag-chip {
  /* 一个颜色真相：--tag-c（后端配色的规范化 hex），没配色就跟随主题主色。 */
  --_c: var(--tag-c, hsl(var(--primary)));

  /* 同色相浓涂：底是色本身摊到卡面上 18%，字是色本身往黑压 55%。
     14 色抽样实测最坏 5.75:1（最浅的 yellow-300），hover 摊到 26% 仍 5.63:1。
     这里不能再走 `hsl(h s*0.85 l*0.55)` 那类减饱和——那正是"灰蒙蒙"的来源。 */
  --_bg: color-mix(in oklab, var(--_c) 18%, hsl(var(--card)));
  --_fg: color-mix(in oklab, var(--_c) 55%, black);
  --_border: color-mix(in oklab, var(--_c) 30%, transparent);
  --_dot: var(--_c);

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
  box-shadow: inset 0 1px 2px color-mix(in oklab, var(--_c) 10%, transparent);

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

/* ===== Dark mode =====
 * 同一套派生，只把"往哪边压"反过来：底摊到暗卡面上 22%，字往白提 50%。
 * 实测最坏 5.76:1（最深的那枚 slate-800 标签色），hover 32% 仍 5.62:1。 */
html.dark .tag-chip {
  --_bg: color-mix(in oklab, var(--_c) 22%, hsl(var(--card)));
  --_fg: color-mix(in oklab, var(--_c) 50%, white);
  --_border: color-mix(in oklab, var(--_c) 40%, transparent);
  --_dot: color-mix(in oklab, var(--_c) 78%, white);
}

/* ===== Hover =====
 * 卡片内嵌套变换会与 .lift-hover 冲突，这里只做颜色/描边过渡，不做位移。 */
.tag-chip:hover {
  --_bg: color-mix(in oklab, var(--_c) 26%, hsl(var(--card)));
  --_border: color-mix(in oklab, var(--_c) 45%, transparent);
  filter: brightness(1.04);
  box-shadow: inset 0 1px 2px color-mix(in oklab, var(--_c) 14%, transparent);
}

html.dark .tag-chip:hover {
  --_bg: color-mix(in oklab, var(--_c) 32%, hsl(var(--card)));
  --_border: color-mix(in oklab, var(--_c) 52%, transparent);
  box-shadow: inset 0 1px 2px color-mix(in oklab, var(--_c) 20%, transparent);
}

/* NuxtLink wrapper should not add default underline */
a:has(.tag-chip) {
  text-decoration: none;
}
</style>
