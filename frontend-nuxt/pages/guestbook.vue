<script setup lang="ts">
definePageMeta({ layout: "default" });
useHead({ title: "留言板 - Rosetta" });
</script>
<template>
  <div class="space-y-lg">
    <header>
      <h1 class="text-3xl font-bold text-neutral-text-primary">留言板</h1>
      <p class="mt-xs text-sm text-neutral-text-tertiary">欢迎留言。（评论插件接入中，对应 Astro comment/Waline/Giscus/Twikoo）</p>
    </header>
    <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl shadow-sm p-xl md:p-2xl min-h-[480px] flex items-center justify-center">
      <p class="text-neutral-text-tertiary text-sm">评论区占位（阶段 8 接入 Twikoo / Giscus 组件）。</p>
    </div>
  </div>
</template>
