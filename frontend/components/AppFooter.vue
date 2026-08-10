<!--
  AppFooter — 对应 Astro src/components/Footer.astro
  视觉 1:1：4 栏（关于 Rosetta / 导航 / 功能 / 关于我们）+ 版权行
-->
<script setup lang="ts">
const thisYear = new Date().getFullYear();
</script>

<template>
  <footer
    class="mt-3xl border-t border-neutral-border-secondary bg-neutral-bg-spot text-neutral-text-secondary"
    role="contentinfo"
  >
    <div class="max-w-7xl mx-auto px-4 sm:px-6 xl:px-8 py-2xl grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-xl">
      <!-- Col 1 -->
      <div>
        <div class="mb-md"><AppLogo size="sm" :show-tagline="false" :clickable="false" /></div>
        <p class="text-sm leading-relaxed">
          以内容与体验为核心的现代化博客系统。<br />
          由 Vue 3 · Nuxt 4 · FastAPI · Tailwind v4 驱动。
        </p>
      </div>
      <!-- Col 2 -->
      <div>
        <h3 class="text-sm font-semibold text-neutral-text-primary mb-md">导航</h3>
        <ul class="space-y-xs text-sm leading-6">
          <li><NuxtLink to="/posts" class="hover:text-primary-500 transition-colors duration-fast">文章</NuxtLink></li>
          <li><NuxtLink to="/categories" class="hover:text-primary-500 transition-colors duration-fast">分类</NuxtLink></li>
          <li><NuxtLink to="/tags" class="hover:text-primary-500 transition-colors duration-fast">标签</NuxtLink></li>
          <li><NuxtLink to="/archive" class="hover:text-primary-500 transition-colors duration-fast">归档</NuxtLink></li>
          <li><NuxtLink to="/search" class="hover:text-primary-500 transition-colors duration-fast">搜索</NuxtLink></li>
        </ul>
      </div>
      <!-- Col 3 -->
      <div>
        <h3 class="text-sm font-semibold text-neutral-text-primary mb-md">功能</h3>
        <ul class="space-y-xs text-sm leading-6">
          <li><NuxtLink to="/dynamic" class="hover:text-primary-500 transition-colors duration-fast">动态</NuxtLink></li>
          <li><NuxtLink to="/bangumi" class="hover:text-primary-500 transition-colors duration-fast">番剧</NuxtLink></li>
          <li><NuxtLink to="/anime" class="hover:text-primary-500 transition-colors duration-fast">动漫</NuxtLink></li>
          <li><NuxtLink to="/gallery" class="hover:text-primary-500 transition-colors duration-fast">相册</NuxtLink></li>
          <li><NuxtLink to="/friends" class="hover:text-primary-500 transition-colors duration-fast">友情链接</NuxtLink></li>
        </ul>
      </div>
      <!-- Col 4 -->
      <div>
        <h3 class="text-sm font-semibold text-neutral-text-primary mb-md">关于</h3>
        <ul class="space-y-xs text-sm leading-6">
          <li><NuxtLink to="/about" class="hover:text-primary-500 transition-colors duration-fast">关于本站</NuxtLink></li>
          <li><NuxtLink to="/guestbook" class="hover:text-primary-500 transition-colors duration-fast">留言</NuxtLink></li>
          <li><NuxtLink to="/sponsor" class="hover:text-primary-500 transition-colors duration-fast">赞助</NuxtLink></li>
          <li><a href="mailto:choyu-choyeon@outlook.com" class="hover:text-primary-500 transition-colors duration-fast">联系邮箱</a></li>
        </ul>
      </div>
    </div>
    <!-- Copyright -->
    <div class="border-t border-neutral-border-secondary">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 xl:px-8 py-md flex flex-col sm:flex-row items-center justify-between gap-xs text-sm text-neutral-text-tertiary">
        <p>© {{ thisYear }} Rosetta. All rights reserved.</p>
        <p class="text-center sm:text-right">
          Powered by <span class="text-neutral-text-secondary">Nuxt 4</span>
          &nbsp;·&nbsp;
          Build with ♡ by <span class="text-primary-500 font-medium">Choyu Choyeon</span>
        </p>
      </div>
    </div>
  </footer>
</template>
