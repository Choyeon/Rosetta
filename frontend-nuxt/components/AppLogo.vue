<!--
  AppLogo — 对应 Astro src/components/Logo.astro
  用于 AppHeader / AppFooter / 登录页 / OOBE 的站点标识
  视觉：方形渐变块 + 品牌名 + 副标语
-->
<script setup lang="ts">
interface Props {
  /** 尺寸 */
  size?: "sm" | "md" | "lg";
  /** 是否显示副标题（Lightweight Blog System） */
  showTagline?: boolean;
  /** 是否可点击（点击 → 首页） */
  clickable?: boolean;
}
withDefaults(defineProps<Props>(), {
  size: "md",
  showTagline: true,
  clickable: true,
});
</script>

<template>
  <component
    :is="clickable ? NuxtLink : 'div'"
    v-bind="clickable ? { to: '/', 'aria-label': 'Rosetta 首页' } : {}"
    class="flex items-center gap-2 select-none"
    :class="{
      'outline-none focus-visible:ring-2 ring-primary-500 rounded-md': clickable,
    }"
  >
    <div
      class="flex items-center justify-center rounded-lg bg-gradient-to-br from-primary-500 via-nebula-blue to-rosetta-gold shadow-sm ring-1 ring-white/10"
      :class="{
        'w-8 h-8': size === 'sm',
        'w-9 h-9': size === 'md',
        'w-11 h-11': size === 'lg',
      }"
      aria-hidden
    >
      <span
        class="text-white font-bold tracking-tight leading-none"
        :class="{ 'text-base': size === 'sm', 'text-lg': size === 'md', 'text-xl': size === 'lg' }"
      >R</span>
    </div>
    <div class="flex flex-col leading-none">
      <span
        class="font-semibold text-neutral-text-primary"
        :class="{ 'text-base': size === 'sm', 'text-lg': size === 'md', 'text-xl': size === 'lg' }"
      >Rosetta</span>
      <span
        v-if="showTagline"
        class="uppercase tracking-[0.22em] text-neutral-text-tertiary mt-0.5"
        :class="{ 'text-[9px]': size === 'sm', 'text-[10px]': size === 'md', 'text-xs': size === 'lg' }"
      >
        Lightweight Blog System
      </span>
    </div>
  </component>
</template>
