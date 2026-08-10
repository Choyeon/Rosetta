<script setup lang="ts">
definePageMeta({ layout: "default" });
useHead({ title: "番剧 / Anime - Rosetta" });
</script>
<template>
  <div class="space-y-lg">
    <header>
      <h1 class="text-3xl font-bold text-neutral-text-primary">追番 📺</h1>
      <p class="mt-xs text-sm text-neutral-text-tertiary">对应 Astro anie/bangumi。数据接入中。</p>
    </header>
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-md">
      <div v-for="i in 12" :key="i" class="space-y-xs">
        <div class="aspect-[3/4] rounded-lg bg-gradient-to-br from-primary-500/20 to-nebula-blue/30 relative overflow-hidden">
          <div class="absolute inset-0 flex items-center justify-center text-white/60"><Icon name="mdi:anime" class="w-10 h-10"/></div>
        </div>
        <p class="text-xs font-medium text-neutral-text-primary line-clamp-2">番剧名占位 {{ i }}</p>
      </div>
    </div>
  </div>
</template>
