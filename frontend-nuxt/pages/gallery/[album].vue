<script setup lang="ts">
definePageMeta({ layout: "default" });
const route = useRoute();
const album = route.params.album;
useHead({ title: `相册 #${album} - Rosetta` });
</script>
<template>
  <div class="space-y-lg">
    <header class="flex items-center justify-between">
      <NuxtLink to="/gallery" class="text-sm text-neutral-text-tertiary hover:text-primary-500 inline-flex items-center gap-0.5">
        <Icon name="material-symbols:chevron-left-rounded" class="w-4 h-4"/>返回相册
      </NuxtLink>
      <h1 class="text-2xl font-bold text-neutral-text-primary">相册 {{ album }}</h1>
      <span/>
    </header>
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-xs">
      <div v-for="i in 12" :key="i" class="aspect-square rounded-lg bg-gradient-to-br from-primary-500/15 to-rosetta-gold/20 overflow-hidden relative">
        <div class="absolute inset-0 flex items-center justify-center text-primary-500/40"><Icon name="material-symbols:image-rounded" class="w-10 h-10"/></div>
      </div>
    </div>
  </div>
</template>
