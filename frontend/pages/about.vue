<script setup lang="ts">
definePageMeta({ layout: "default" });
useHead({ title: "关于 - Rosetta" });

// 本地 content/spec/about.md 优先 → /api/site/about 回退
const { data } = await useAsyncData("about-doc", async () => {
  try {
    return await queryContent("/spec/about").findOne();
  } catch { return null; }
});
</script>

<template>
  <div class="bg-neutral-bg-container rounded-2xl border border-neutral-border-secondary shadow-sm p-lg md:p-2xl prose prose-rosetta max-w-none">
    <ContentRenderer v-if="data?.body" :value="data as any" tag="div" />
    <div v-else class="space-y-md">
      <h1 class="text-3xl font-bold text-neutral-text-primary">关于 Rosetta</h1>
      <p class="text-neutral-text-secondary leading-relaxed">
        Rosetta 是一款现代化的博客系统。前端使用 <strong>Nuxt 4 + Vue 3 + Tailwind v4</strong>，
        后端基于 <strong>FastAPI + SQLAlchemy + PostgreSQL</strong>。
      </p>
      <p>该页面内容将由后台「站点设置 → 关于页面内容」覆盖。</p>
    </div>
  </div>
</template>
