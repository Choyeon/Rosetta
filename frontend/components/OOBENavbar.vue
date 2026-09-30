<!--
  OOBE 向导专用顶栏（仅 pages/oobe.vue 使用）。与前台 Navbar 刻意不共用：安装完成前
  站点设置、导航配置、主题包都不存在，所以品牌名与 logo 只能硬编码，也不能挂任何
  主题皮肤——/oobe 在 layout-scope 中间件里按 admin 处理，主题 CSS 不会注入。
  纯展示组件，locale 由 LocaleSwitcher 接管；不放明暗切换按钮——/oobe 页根
  （.oobe-dark）把语义令牌钉死为暗色，切换按钮在此页面没有任何视觉效果，只会误导。
-->
<script setup lang="ts">
import LocaleSwitcher from '~~/components/LocaleSwitcher.vue'
</script>

<template>
  <header class="sticky top-0 z-40 w-full h-16 border-b bg-background/80 backdrop-blur">
    <div class="container mx-auto flex h-full items-center justify-between px-4 lg:px-8">
      <NuxtLink
        to="/"
        class="inline-flex items-center gap-2 font-display text-xl font-bold tracking-tight"
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
      </div>
    </div>
  </header>
</template>
