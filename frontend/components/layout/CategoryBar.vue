<!--
  CategoryBar — 文章页/列表页顶部分类面包屑导航
  props: category / breadcrumbs[] / tags[] / backTo
-->
<script setup lang="ts">
interface Crumb { label: string; to?: string; }
interface Props {
  category?: string;
  categorySlug?: string;
  breadcrumbs?: Crumb[];
  tags?: string[];
  title?: string;
}
withDefaults(defineProps<Props>(), {
  category: "",
  categorySlug: "",
  breadcrumbs: () => [{ label: "首页", to: "/" }, { label: "文章", to: "/posts" }],
  tags: () => [],
  title: "",
});
</script>

<template>
  <div class="bg-neutral-bg-container rounded-2xl border border-neutral-border-secondary shadow-sm overflow-hidden">
    <div class="px-md py-xs border-b border-neutral-border-secondary flex items-center gap-1 flex-wrap text-xs">
      <template v-for="(b, i) in breadcrumbs" :key="i">
        <NuxtLink
          v-if="b.to"
          :to="b.to"
          class="text-neutral-text-tertiary hover:text-primary-500 transition-colors line-clamp-1"
        >{{ b.label }}</NuxtLink>
        <span v-else class="text-neutral-text-tertiary">{{ b.label }}</span>
        <Icon name="material-symbols:chevron-right-rounded" class="w-3 h-3 text-neutral-text-quaternary mx-0.5" v-if="i < breadcrumbs.length - 1 || category" />
      </template>
      <NuxtLink
        v-if="category"
        :to="categorySlug ? `/categories/${categorySlug}` : '/categories'"
        class="inline-flex items-center gap-0.5 text-primary-500 font-medium"
      >
        <Icon name="material-symbols:folder-rounded" class="w-3 h-3" />
        {{ category }}
      </NuxtLink>
    </div>
    <div class="p-md space-y-xs">
      <h1 class="text-xl sm:text-2xl font-bold text-neutral-text-primary leading-tight" v-if="title">{{ title }}</h1>
      <div v-if="tags?.length" class="flex flex-wrap gap-1 pt-xs">
        <NuxtLink
          v-for="t in tags" :key="t"
          :to="`/tags/${t}`"
          class="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full bg-primary-500/10 text-primary-500 text-xs hover:bg-primary-500 hover:text-white transition-all"
        >
          <Icon name="material-symbols:sell-rounded" class="w-3 h-3" />
          #{{ t }}
        </NuxtLink>
      </div>
    </div>
  </div>
</template>
