<script setup lang="ts">
definePageMeta({ layout: "default" });
const route = useRoute();
const back = typeof route.query.from === "string" ? route.query.from : "/";
useHead({ title: "404 - 页面走丢了" });
</script>
<template>
  <div class="min-h-[65vh] flex items-center justify-center p-md">
    <div class="text-center space-y-md">
      <p class="text-[120px] md:text-[180px] leading-none font-black bg-gradient-to-br from-primary-500 via-nebula-blue to-rosetta-gold bg-clip-text text-transparent">404</p>
      <h1 class="text-2xl font-bold text-neutral-text-primary">页面走丢了</h1>
      <p class="text-sm text-neutral-text-tertiary">链接可能已变更、文章被删除，或者路径拼写错误。</p>
      <div class="flex items-center justify-center gap-xs pt-xs">
        <NuxtLink :to="back" class="px-5 h-11 inline-flex items-center rounded-lg bg-primary-500 text-white font-medium hover:bg-primary-400 transition-colors">返回上一页</NuxtLink>
        <NuxtLink to="/" class="px-5 h-11 inline-flex items-center rounded-lg bg-neutral-fill-hover text-neutral-text-primary hover:bg-neutral-fill-active transition-colors">回首页</NuxtLink>
      </div>
    </div>
  </div>
</template>
