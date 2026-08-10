<!--
  SiteStats — 站点统计（文章/评论/点赞/标签/分类/访问量）
  props: 各指标数值
-->
<script setup lang="ts">
interface Props {
  articles?: number;
  comments?: number;
  likes?: number;
  tags?: number;
  categories?: number;
  visits?: number;
}
withDefaults(defineProps<Props>(), {
  articles: 64, comments: 1024, likes: 3842, tags: 233, categories: 12, visits: 148576,
});

const items = computed(() => [
  { k: "articles", l: "文章", v: props.articles, i: "material-symbols:description-rounded", c: "from-blue-500/10 to-blue-500/5 text-blue-500" },
  { k: "categories", l: "分类", v: props.categories, i: "material-symbols:folder-rounded", c: "from-violet-500/10 to-violet-500/5 text-violet-500" },
  { k: "tags", l: "标签", v: props.tags, i: "material-symbols:label-rounded", c: "from-pink-500/10 to-pink-500/5 text-pink-500" },
  { k: "comments", l: "评论", v: props.comments, i: "material-symbols:chat-rounded", c: "from-emerald-500/10 to-emerald-500/5 text-emerald-500" },
  { k: "likes", l: "点赞", v: props.likes, i: "material-symbols:favorite-rounded", c: "from-rose-500/10 to-rose-500/5 text-rose-500" },
  { k: "visits", l: "访问", v: props.visits, i: "material-symbols:visibility-rounded", c: "from-amber-500/10 to-amber-500/5 text-amber-500" },
]);
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl p-md shadow-sm border border-neutral-border-secondary">
    <header class="flex items-center gap-1.5 mb-sm">
      <Icon name="material-symbols:insights-rounded" class="w-4 h-4 text-primary-500" />
      <h3 class="text-sm font-semibold text-neutral-text-primary">站点统计</h3>
    </header>
    <div class="grid grid-cols-3 gap-xs">
      <div
        v-for="it in items" :key="it.k"
        class="rounded-xl p-xs text-center bg-gradient-to-br border border-transparent hover:shadow-sm transition-all duration-fast"
        :class="it.c"
      >
        <Icon :name="it.i" class="w-4 h-4 mx-auto mb-0.5 opacity-90" />
        <div class="text-sm font-bold text-neutral-text-primary">{{ it.v?.toLocaleString() }}</div>
        <div class="text-[10px] opacity-70">{{ it.l }}</div>
      </div>
    </div>
  </section>
</template>
