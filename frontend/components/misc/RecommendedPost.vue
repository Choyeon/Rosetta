<!--
  RecommendedPost — 文章相关推荐卡片（3 篇一组）
  props: items[{_path, title, description, image, category, tags, readingTime, date}]
-->
<script setup lang="ts">
interface RecommendItem {
  _path: string;
  title: string;
  description?: string;
  image?: string;
  category?: string;
  tags?: string[];
  readingTime?: number;
  date?: string;
}
interface Props {
  items?: RecommendItem[];
  title?: string;
}
withDefaults(defineProps<Props>(), {
  items: () => [
    { _path: "/posts/demo-1", title: "从 Astro 迁移到 Nuxt 4 的实践手记", description: "记录把博客前端从 Astro 2.x 迁移到 Nuxt 4（SSR + ISR）过程中踩过的坑和总结。", image: "", category: "开发日志", tags: ["Nuxt", "Astro", "迁移"], readingTime: 8, date: dayjs().subtract(3, "day").toISOString() },
    { _path: "/posts/demo-2", title: "FastAPI + SQLModel 后端架构详解", description: "分享 Rosetta 博客后端是如何组织分层、依赖注入、权限中间件与缓存策略的。", image: "", category: "技术笔记", tags: ["FastAPI", "Python", "架构"], readingTime: 12, date: dayjs().subtract(5, "day").toISOString() },
    { _path: "/posts/demo-3", title: "Tailwind v4 与设计 Token 的整合方式", description: "从零搭建一套支持暗色/浅色/色盲友好的设计系统，并在 Nuxt 中落地。", image: "", category: "工具推荐", tags: ["Tailwind", "设计系统", "Token"], readingTime: 6, date: dayjs().subtract(10, "day").toISOString() },
  ],
  title: "相关推荐",
});

const list = computed(() => (props.items || []).slice(0, 3));
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl p-md shadow-sm border border-neutral-border-secondary">
    <header class="flex items-center justify-between mb-md">
      <h3 class="text-base font-semibold text-neutral-text-primary flex items-center gap-1.5">
        <Icon name="material-symbols:recommend-rounded" class="w-5 h-5 text-primary-500" />
        {{ title }}
      </h3>
      <NuxtLink to="/posts" class="text-xs text-neutral-text-tertiary hover:text-primary-500 transition-colors flex items-center gap-0.5">
        全部文章
        <Icon name="material-symbols:arrow-outward-rounded" class="w-3.5 h-3.5" />
      </NuxtLink>
    </header>
    <div class="grid gap-sm md:grid-cols-3">
      <NuxtLink
        v-for="p in list" :key="p._path"
        :to="p._path"
        class="group flex flex-col rounded-xl border border-neutral-border-secondary overflow-hidden hover:shadow-md hover:-translate-y-0.5 hover:border-primary-500/40 transition-all duration-fast"
      >
        <div class="aspect-[16/9] bg-gradient-to-br from-primary-400/30 via-primary-500/10 to-rosetta-gold/30 overflow-hidden relative">
          <NuxtImg
            v-if="p.image"
            :src="p.image"
            :alt="p.title"
            loading="lazy"
            class="w-full h-full object-cover transition-transform duration-slow ease-out group-hover:scale-105"
          />
          <div v-else class="absolute inset-0 flex items-center justify-center text-primary-500/40">
            <Icon name="material-symbols:article-rounded" class="w-12 h-12" />
          </div>
          <div v-if="p.category" class="absolute top-xs left-xs inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-black/50 backdrop-blur-sm text-[11px] text-white font-medium">
            {{ p.category }}
          </div>
        </div>
        <div class="p-sm flex-1 flex flex-col min-h-0">
          <h4 class="text-sm font-semibold text-neutral-text-primary line-clamp-2 group-hover:text-primary-500 transition-colors leading-snug">
            {{ p.title }}
          </h4>
          <p v-if="p.description" class="mt-xs text-xs text-neutral-text-tertiary line-clamp-2 leading-relaxed flex-1 min-h-0">
            {{ p.description }}
          </p>
          <footer class="mt-xs pt-xs border-t border-neutral-border-secondary flex items-center justify-between text-[10px] text-neutral-text-quaternary">
            <span v-if="p.date" class="inline-flex items-center gap-0.5">
              <Icon name="material-symbols:schedule-rounded" class="w-3 h-3" />
              {{ dayjs(p.date).format("MM-DD") }}
            </span>
            <span v-if="p.readingTime" class="inline-flex items-center gap-0.5">
              <Icon name="material-symbols:menu-book-rounded" class="w-3 h-3" />
              {{ p.readingTime }} 分钟
            </span>
          </footer>
        </div>
      </NuxtLink>
    </div>
  </section>
</template>
