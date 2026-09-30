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
  <!-- 背景刻意用 bg-black/20 而非 bg-background：本项目 Tailwind 存在两套
       @theme 产物（inline 的 hsl(var(--background)) 与非 inline 固化到 :root
       亮色的 var(--color-background)），同名工具类两条规则共存、按加载顺序仲裁，
       bg-background 在本页可能拿到固化亮色值 → 白底黑字（生产截图实证）。
       本页是钉死深色设计，直接写死不依赖语义变量最稳。 -->
  <header class="sticky top-0 z-40 w-full h-16 border-b border-white/10 bg-black/20 backdrop-blur-xl">
    <div class="container mx-auto flex h-full items-center justify-between px-4 lg:px-8">
      <NuxtLink
        to="/"
        class="inline-flex items-center gap-2 font-display text-xl font-bold tracking-tight text-white"
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
