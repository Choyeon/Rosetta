<script setup lang="ts">
definePageMeta({ layout: "default" });
useHead({ title: "500 - 服务器开小差" });
const error = useState("error", () => useError());
</script>
<template>
  <div class="min-h-[60vh] flex items-center justify-center p-md">
    <div class="text-center space-y-md max-w-lg">
      <p class="text-[120px] leading-none font-black bg-gradient-to-br from-danger-500 via-primary-500 to-nebula-blue bg-clip-text text-transparent">500</p>
      <h1 class="text-2xl font-bold text-neutral-text-primary">服务器开小差了</h1>
      <p class="text-sm text-neutral-text-tertiary whitespace-pre-wrap">{{ error?.statusMessage || error?.message || "这是一个通用的服务器错误页。" }}</p>
      <div class="flex items-center justify-center gap-xs pt-xs">
        <button @click="clearError({ redirect: '/' })" class="px-5 h-11 rounded-lg bg-primary-500 text-white font-medium hover:bg-primary-400">重试 / 返回</button>
        <NuxtLink to="/" class="px-5 h-11 rounded-lg bg-neutral-fill-hover text-neutral-text-primary hover:bg-neutral-fill-active">回首页</NuxtLink>
      </div>
    </div>
  </div>
</template>
