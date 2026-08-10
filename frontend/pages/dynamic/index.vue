<script setup lang="ts">
definePageMeta({ layout: "default" });
useHead({ title: "动态 - Rosetta" });
interface Moment { id: number | string; content: string; createdAt: string; likes?: number }
const { data } = await useFetch<Moment[]>("/api/moments", {
  default: () => ([
    { id: 1, content: "🪐 Rosetta 前端已从 Astro 全面迁移到 Nuxt 4 + Vue 3 + Tailwind v4，SSR 体验显著提升。", createdAt: "2026-03-26" },
    { id: 2, content: "📚 新增 64 篇内容层种子文章，覆盖迁移笔记、项目实战、文章示例。", createdAt: "2026-03-22" },
    { id: 3, content: "🛠️ 管理后台重构中：Markdown 编辑器 + 媒体管理 + RBAC。", createdAt: "2026-03-18" },
  ]),
  lazy: true,
});
</script>
<template>
  <div class="space-y-lg">
    <header>
      <h1 class="text-3xl font-bold text-neutral-text-primary">动态时间线</h1>
      <p class="mt-xs text-sm text-neutral-text-tertiary">日常想法与进展。</p>
    </header>
    <div class="space-y-sm relative pl-md">
      <div class="absolute left-1 top-2 bottom-2 w-0.5 bg-gradient-to-b from-primary-500/50 to-rosetta-gold/30 rounded-full" />
      <div v-for="m in data" :key="m.id" class="relative">
        <span class="absolute -left-[17px] top-3 w-3 h-3 rounded-full bg-neutral-bg-container border-2 border-primary-500"/>
        <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-xl p-md">
          <p class="whitespace-pre-wrap text-neutral-text-primary leading-relaxed">{{ m.content }}</p>
          <p class="mt-xs text-xs text-neutral-text-quaternary">{{ new Date(m.createdAt).toLocaleString() }}</p>
        </div>
      </div>
    </div>
  </div>
</template>
