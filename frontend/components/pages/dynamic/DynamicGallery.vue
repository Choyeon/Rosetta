<!--
  DynamicGallery — 动态图集（1/2/3/4/6/9 宫格自适应 + PhotoSwipe 触发 + data-fancybox）
  props: images[]
-->
<script setup lang="ts">
import PhotoSwipeLightbox from "photoswipe/lightbox";
import "photoswipe/style.css";

interface Props {
  images: string[];
  captions?: string[];
}
const props = withDefaults(defineProps<Props>(), { captions: () => [] });

const hostEl = ref<HTMLElement | null>(null);
let lightbox: PhotoSwipeLightbox | null = null;

const count = computed(() => props.images.length);
const gridCls = computed(() => {
  switch (count.value) {
    case 1: return "grid-cols-1 max-w-md";
    case 2: return "grid-cols-2 max-w-lg";
    case 3: case 4: return "grid-cols-2";
    case 5: case 6: return "grid-cols-3";
    default: return "grid-cols-3";
  }
});
const isSquare = computed(() => count.value > 2);

onMounted(() => {
  lightbox = new PhotoSwipeLightbox({
    gallery: hostEl.value || undefined,
    children: "a[data-pswp]",
    showHideAnimationType: "fade",
    zoom: false,
    bgOpacity: 0.92,
    pswpModule: () => import("photoswipe"),
  });
  lightbox.init();
});

onBeforeUnmount(() => {
  try { lightbox?.destroy(); } catch { /* ignore */ }
  lightbox = null;
});
</script>

<template>
  <div
    ref="hostEl"
    class="grid gap-xs rounded-xl overflow-hidden"
    :class="gridCls"
    data-pswp-gallery
  >
    <a
      v-for="(src, i) in images"
      :key="i"
      :href="src"
      :data-caption="captions?.[i] || ''"
      data-pswp
      data-fancybox="dynamic"
      data-type="image"
      class="block overflow-hidden rounded-lg bg-neutral-fill-hover group"
      :class="isSquare || count === 1 ? '' : (count === 2 ? 'aspect-[4/3]' : 'aspect-square')"
    >
      <NuxtImg
        :src="src"
        :alt="captions?.[i] || `动态图片 ${i + 1}`"
        loading="lazy"
        class="w-full h-full object-cover transition-transform duration-slow ease-out group-hover:scale-105"
        :class="isSquare ? 'aspect-square' : (count === 1 ? 'max-h-80 w-auto' : 'aspect-[4/3]')"
      />
    </a>
  </div>
</template>
