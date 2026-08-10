<script setup lang="ts">
definePageMeta({ layout: "default" });
useHead({ title: "403 - 无权限访问" });
</script>
<template>
  <div class="min-h-[60vh] flex items-center justify-center p-md">
    <div class="text-center space-y-md">
      <p class="text-[120px] leading-none font-black bg-gradient-to-br from-warning-500 via-rosetta-gold to-primary-500 bg-clip-text text-transparent">403</p>
      <h1 class="text-2xl font-bold text-neutral-text-primary">无权访问此内容</h1>
      <p class="text-sm text-neutral-text-tertiary">你需要使用有权限的账号登录，或联系站点管理员。</p>
      <div class="flex items-center justify-center gap-xs pt-xs">
        <NuxtLink to="/login" class="px-5 h-11 rounded-lg bg-primary-500 text-white font-medium hover:bg-primary-400">去登录</NuxtLink>
        <NuxtLink to="/" class="px-5 h-11 rounded-lg bg-neutral-fill-hover text-neutral-text-primary hover:bg-neutral-fill-active">回首页</NuxtLink>
      </div>
    </div>
  </div>
</template>
