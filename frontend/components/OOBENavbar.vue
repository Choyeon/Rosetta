<!--
  OOBE 向导专用顶栏（仅 pages/oobe.vue 使用）。与前台 Navbar 刻意不共用：安装完成前
  站点设置、导航配置、主题包都不存在，所以品牌名与 logo 只能硬编码，也不能挂任何
  主题皮肤——/oobe 在 layout-scope 中间件里按 admin 处理，主题 CSS 不会注入。
  纯展示组件，locale 由 LocaleSwitcher 接管；明暗切换用全局 ThemeToggle——它只写
  <html>.dark + localStorage（useTheme），不依赖站点配置，在 /oobe 上功能完整。
  玻璃层刻意写死半透明而非 bg-background：本项目 Tailwind 存在两套 @theme 产物
  （inline 的 hsl(var(--background)) 与非 inline 固化 :root 亮色的 var(--color-background)），
  同名工具类两条规则共存、按加载顺序仲裁，语义背景类在本页可能拿到固化亮色值。
  故亮暗各写一份（dark: 变体），文字走 text-foreground 跟随全局主题。
-->
<script setup lang="ts">
import LocaleSwitcher from '~~/components/LocaleSwitcher.vue'
</script>

<template>
  <header
    class="sticky top-0 z-40 w-full h-16 border-b border-zinc-900/10 bg-white/55 dark:border-white/10 dark:bg-black/40 backdrop-blur-xl"
  >
    <div class="container mx-auto flex h-full items-center justify-between px-4 lg:px-8">
      <NuxtLink
        to="/"
        :prefetch="false"
        class="inline-flex items-center gap-2 font-display text-xl font-bold tracking-tight text-foreground"
      >
        <img
          src="/logo/rosetta-primary-icon.png"
          alt="Rosetta"
          class="size-7"
        >
        <span>Rosetta</span>
      </NuxtLink>

      <div class="flex items-center gap-1">
        <LocaleSwitcher />
        <ThemeToggle />
      </div>
    </div>
  </header>
</template>
