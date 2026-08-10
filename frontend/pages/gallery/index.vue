<script setup lang="ts">
definePageMeta({ layout: "default" });
useHead({ title: "相册 - Rosetta" });
const { data: albums } = await useFetch<any[]>("/api/gallery", { default: () => [
  { id: 1, name: "项目截图", cover: "", count: 12 },
  { id: 2, name: "旅行照片", cover: "", count: 28 },
], lazy: true });
</script>
<template>
  <div class="space-y-lg">
    <header>
      <h1 class="text-3xl font-bold text-neutral-text-primary">相册</h1>
      <p class="mt-xs text-sm text-neutral-text-tertiary">图文记录。</p>
    </header>
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-md">
      <NuxtLink
        v-for="a in albums"
        :key="a.id"
        :to="`/gallery/${a.id}`"
        class="group relative aspect-[4/3] rounded-2xl bg-gradient-to-br from-primary-500/20 via-nebula-blue/10 to-rosetta-gold/20 overflow-hidden border border-neutral-border-secondary hover:shadow-lg hover:-translate-y-0.5 transition-all"
      >
        <div class="absolute inset-0 flex items-center justify-center text-primary-500/40"><Icon name="material-symbols:photo-library-rounded" class="w-14 h-14"/></div>
        <div class="absolute bottom-0 left-0 right-0 p-md bg-gradient-to-t from-black/60 to-transparent">
          <p class="font-semibold text-white">{{ a.name }}</p>
          <p class="text-xs text-white/80 mt-0.5">{{ a.count }} 张</p>
        </div>
      </NuxtLink>
    </div>
  </div>
</template>
