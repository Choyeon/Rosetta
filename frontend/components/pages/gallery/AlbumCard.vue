<!--
  AlbumCard — 相册封面卡片
  props: slug / title / cover / count / description / tags / date
-->
<script setup lang="ts">
interface Album {
  slug: string;
  title: string;
  cover?: string;
  count?: number;
  description?: string;
  tags?: string[];
  date?: string;
}
interface Props { album: Album; }
defineProps<Props>();
</script>

<template>
  <NuxtLink
    :to="`/gallery/${album.slug}`"
    class="group block bg-neutral-bg-container rounded-2xl border border-neutral-border-secondary overflow-hidden shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all duration-fast ease-out"
  >
    <div class="relative aspect-[16/10] overflow-hidden bg-neutral-fill-hover">
      <NuxtImg
        v-if="album.cover"
        :src="album.cover"
        :alt="album.title"
        loading="lazy"
        class="w-full h-full object-cover transition-transform duration-slow ease-out group-hover:scale-105"
      />
      <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-black/0 to-transparent" />
      <div v-if="album.count" class="absolute bottom-sm left-sm inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-black/50 backdrop-blur-sm text-xs text-white font-medium">
        <Icon name="material-symbols:photo-library-rounded" class="w-3.5 h-3.5" />
        {{ album.count }} 张
      </div>
      <div v-if="album.date" class="absolute top-sm right-sm inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-black/50 backdrop-blur-sm text-[11px] text-white/90">
        <Icon name="material-symbols:calendar-month-rounded" class="w-3 h-3" />
        {{ dayjs(album.date).format("YYYY-MM") }}
      </div>
    </div>
    <div class="p-sm sm:p-md space-y-xs">
      <h3 class="text-base sm:text-lg font-semibold text-neutral-text-primary line-clamp-1 group-hover:text-primary-500 transition-colors">{{ album.title }}</h3>
      <p v-if="album.description" class="text-xs sm:text-sm text-neutral-text-tertiary line-clamp-2 leading-relaxed">{{ album.description }}</p>
      <div v-if="album.tags?.length" class="flex flex-wrap gap-1 pt-xs">
        <span
          v-for="t in album.tags.slice(0, 4)" :key="t"
          class="text-[10px] sm:text-[11px] px-1.5 py-0.5 rounded-full bg-neutral-fill-hover text-neutral-text-tertiary"
        >#{{ t }}</span>
      </div>
    </div>
  </NuxtLink>
</template>
