<!--
  Categories — 侧边栏分类组件
  props: categories[{ name, slug, count, description, color }]
-->
<script setup lang="ts">
interface Category {
  name: string;
  slug: string;
  count?: number;
  description?: string;
  color?: string;
}
interface Props {
  categories?: Category[];
  limit?: number;
}
withDefaults(defineProps<Props>(), {
  categories: () => [
    { name: "技术笔记", slug: "tech", count: 24, color: "bg-blue-500" },
    { name: "生活随笔", slug: "life", count: 15, color: "bg-emerald-500" },
    { name: "开发日志", slug: "devlog", count: 11, color: "bg-violet-500" },
    { name: "工具推荐", slug: "tools", count: 7, color: "bg-amber-500" },
    { name: "折腾记录", slug: "diary", count: 5, color: "bg-rose-500" },
  ],
  limit: 12,
});

const list = computed(() => props.categories?.slice(0, props.limit) || []);
const maxCount = computed(() => Math.max(1, ...list.value.map((c) => c.count || 0)));
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl p-md shadow-sm border border-neutral-border-secondary">
    <header class="flex items-center justify-between mb-sm">
      <h3 class="text-sm font-semibold text-neutral-text-primary flex items-center gap-1.5">
        <Icon name="material-symbols:category-rounded" class="w-4 h-4 text-primary-500" />
        分类
      </h3>
      <NuxtLink to="/categories" class="text-[11px] text-neutral-text-tertiary hover:text-primary-500 transition-colors flex items-center gap-0.5">
        全部 <Icon name="material-symbols:arrow-outward-rounded" class="w-3 h-3" />
      </NuxtLink>
    </header>
    <ul class="space-y-1">
      <li v-for="c in list" :key="c.slug">
        <NuxtLink
          :to="`/categories/${c.slug}`"
          class="group flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition-all duration-fast hover:bg-neutral-fill-hover"
        >
          <span class="w-1.5 h-1.5 rounded-full flex-shrink-0" :class="c.color || 'bg-primary-500'" />
          <span class="text-neutral-text-secondary group-hover:text-neutral-text-primary line-clamp-1 flex-1 min-w-0">{{ c.name }}</span>
          <span class="text-[10px] px-1.5 py-0.5 rounded-full bg-neutral-fill-hover text-neutral-text-quaternary flex-shrink-0">{{ c.count || 0 }}</span>
        </NuxtLink>
        <div class="mx-2 h-0.5 rounded-full bg-neutral-fill-hover overflow-hidden -mt-0.5 mb-1">
          <div class="h-full rounded-full transition-all" :class="c.color || 'bg-primary-500/60'" :style="{ width: `${((c.count || 0) / maxCount) * 100}%` }" />
        </div>
      </li>
    </ul>
  </section>
</template>
