<!--
  SidebarTocCard — 对应 Astro src/components/blog/sidebar/SidebarToc.astro
  文章页目录导航；其他页面（首页/列表）降级显示“推荐阅读”
-->
<script setup lang="ts">
interface TocItem { level: number; id: string; text: string }
interface Props {
  /** 文章页 TOC（有值时渲染目录，无值时渲染“推荐阅读”占位） */
  items?: TocItem[];
}
defineProps<Props>();
const route = useRoute();
const isArticle = computed(() => /^\/(posts|p)\//.test(route.path));
const active = ref<string>("");

const demoToc: TocItem[] = [
  { level: 2, id: "h-1", text: "1. 项目背景与目标" },
  { level: 3, id: "h-2", text: "1.1 为何从 Astro 迁移" },
  { level: 3, id: "h-3", text: "1.2 迁移范围与约束" },
  { level: 2, id: "h-4", text: "2. 架构设计" },
  { level: 3, id: "h-5", text: "2.1 前后端分离" },
  { level: 2, id: "h-6", text: "3. 数据模型" },
  { level: 2, id: "h-7", text: "4. 总结与展望" },
];
const demoRecs = [
  { to: "/posts/welcome", title: "欢迎使用 Rosetta 轻博客系统", date: "2025-03-18" },
  { to: "/posts/from-astro-to-nuxt", title: "从 Astro 7 到 Nuxt 4：一场迁移复盘", date: "2025-04-02" },
  { to: "/posts/fastapi-pagination", title: "FastAPI 游标分页的正确姿势", date: "2025-04-20" },
  { to: "/posts/tailwind-v4-theme", title: "Tailwind v4 @theme 实战：设计令牌落地", date: "2025-05-11" },
];
</script>

<template>
  <section
    class="bg-neutral-bg-container rounded-2xl p-lg shadow-sm border border-neutral-border-secondary"
    data-testid="sidebar-toc-card"
    aria-label="目录 / 推荐阅读"
  >
    <div class="flex items-center justify-between mb-md">
      <h3 class="text-sm font-semibold text-neutral-text-primary uppercase tracking-wider">
        {{ isArticle ? "目录" : "推荐阅读" }}
      </h3>
      <span class="text-xs text-neutral-text-quaternary">{{ isArticle ? (items?.length || 0) : demoRecs.length }}</span>
    </div>

    <!-- 文章页：TOC -->
    <ol v-if="isArticle" class="space-y-1 text-sm max-h-[520px] overflow-y-auto pr-1 scroll-smooth">
      <li v-for="(t, idx) in (items && items.length ? items : demoToc)" :key="idx + t.id">
        <a
          :href="'#' + t.id"
          class="block rounded-md px-2 py-1.5 text-neutral-text-secondary hover:text-primary-500 hover:bg-primary-500/10 transition-colors duration-fast"
          :class="{ 'text-primary-500 bg-primary-500/10 border-l-2 border-primary-500 pl-1.5': active === t.id,
                   'pl-4': t.level === 3, 'pl-6': t.level === 4,
                   'pl-2': t.level === 2 || t.level > 4 }"
          @click.prevent="active = t.id"
        >{{ t.text }}</a>
      </li>
    </ol>

    <!-- 其他页：推荐文章 -->
    <ul v-else class="space-y-2">
      <li v-for="r in demoRecs" :key="r.to">
        <NuxtLink
          :to="r.to"
          class="group flex items-start gap-xs rounded-md px-2 py-2 hover:bg-neutral-fill-hover transition-colors duration-fast"
        >
          <Icon name="material-symbols:bookmark-border-rounded" class="w-4 h-4 mt-0.5 text-neutral-text-quaternary group-hover:text-primary-500 shrink-0" />
          <div class="min-w-0">
            <p class="text-sm text-neutral-text-secondary group-hover:text-primary-500 line-clamp-2 leading-snug">{{ r.title }}</p>
            <p class="mt-1 text-[11px] text-neutral-text-quaternary">{{ r.date }}</p>
          </div>
        </NuxtLink>
      </li>
    </ul>
  </section>
</template>
