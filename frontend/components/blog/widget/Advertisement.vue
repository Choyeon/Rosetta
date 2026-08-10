<!--
  Advertisement — 侧边栏广告/赞助位
  props: title / image / link / label
-->
<script setup lang="ts">
interface Props {
  title?: string;
  description?: string;
  image?: string;
  link?: string;
  label?: string;
}
withDefaults(defineProps<Props>(), {
  title: "广告位招租",
  description: "侧边栏、内文推荐位、首页 Banner 等位置可投放广告或友情赞助，联系作者获取详情。",
  image: "",
  link: "/sponsor",
  label: "赞助商",
});
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl overflow-hidden shadow-sm border border-neutral-border-secondary">
    <div class="px-md pt-md pb-xs flex items-center justify-between">
      <h3 class="text-sm font-semibold text-neutral-text-primary flex items-center gap-1.5">
        <Icon name="material-symbols:verified-rounded" class="w-4 h-4 text-primary-500" />
        {{ label }}
      </h3>
      <span class="text-[9px] px-1.5 py-0.5 rounded-full bg-neutral-fill-hover text-neutral-text-quaternary font-medium tracking-wider">AD</span>
    </div>
    <a
      v-if="image"
      :href="link"
      target="_blank"
      rel="noopener nofollow"
      class="block aspect-[2/1] overflow-hidden group"
    >
      <NuxtImg :src="image" :alt="title" loading="lazy" class="w-full h-full object-cover transition-transform duration-slow group-hover:scale-105" />
    </a>
    <div class="p-md pt-sm space-y-xs">
      <a v-if="link" :href="link" target="_blank" rel="noopener nofollow" class="block text-sm font-semibold text-neutral-text-primary hover:text-primary-500 line-clamp-1 transition-colors">{{ title }}</a>
      <h4 v-else class="text-sm font-semibold text-neutral-text-primary line-clamp-1">{{ title }}</h4>
      <p v-if="description" class="text-xs text-neutral-text-tertiary leading-relaxed line-clamp-3">{{ description }}</p>
      <NuxtLink
        v-if="link"
        :to="link"
        class="mt-xs inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md bg-primary-500/10 text-primary-500 font-medium hover:bg-primary-500 hover:text-white transition-all"
      >
        了解详情
        <Icon name="material-symbols:arrow-outward-rounded" class="w-3 h-3" />
      </NuxtLink>
    </div>
  </section>
</template>
