<!--
  PhotoCard — 单张照片卡片（图集内使用，绑定 PhotoSwipe + data-fancybox）
-->
<script setup lang="ts">
interface Props {
  src: string;
  thumb?: string;
  title?: string;
  caption?: string;
  date?: string;
  index?: number;
}
withDefaults(defineProps<Props>(), {
  thumb: "",
  title: "",
  caption: "",
  date: "",
  index: 0,
});
const resolvedThumb = computed(() => props.thumb || props.src);
</script>

<template>
  <figure class="group relative overflow-hidden rounded-xl border border-neutral-border-secondary bg-neutral-fill-hover shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-fast">
    <a
      :href="src"
      :data-caption="caption || title"
      :data-fancybox="gallery"
      data-type="image"
      data-pswp
      class="block aspect-square overflow-hidden"
    >
      <NuxtImg
        :src="resolvedThumb"
        :alt="title || `照片 ${index + 1}`"
        loading="lazy"
        sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
        class="w-full h-full object-cover transition-transform duration-slow ease-out group-hover:scale-105"
      />
    </a>
    <figcaption class="absolute inset-x-0 bottom-0 p-xs bg-gradient-to-t from-black/80 via-black/30 to-transparent text-white text-xs opacity-0 group-hover:opacity-100 transition-opacity duration-fast">
      <div v-if="title" class="font-medium line-clamp-1">{{ title }}</div>
      <div v-if="date" class="flex items-center gap-1 opacity-85 mt-0.5 text-[10px]">
        <Icon name="material-symbols:schedule-rounded" class="w-3 h-3" />
        {{ dayjs(date).format("YYYY-MM-DD") }}
      </div>
    </figcaption>
  </figure>
</template>
