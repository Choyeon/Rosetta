<script setup lang="ts">
definePageMeta({ layout: "default" });
useHead({ title: "友情链接 - Rosetta" });
interface Friend { id: number | string; name: string; url: string; avatar?: string; description?: string; group?: string }
const { data } = await useFetch<Friend[]>("/api/friends", { default: () => [
  { id: 1, name: "示例站点", url: "https://example.com", description: "在这里申请友情链接后自动展示。", group: "技术博客" },
  { id: 2, name: "Nuxt 官网", url: "https://nuxt.com", description: "Vue 元框架。", group: "官方文档" },
  { id: 3, name: "Astro", url: "https://astro.build", description: "原项目使用的群岛架构框架（已迁移）。", group: "官方文档" },
  { id: 4, name: "Tailwind CSS", url: "https://tailwindcss.com", description: "Utility-first CSS 框架。", group: "官方文档" },
], lazy: true });
const groups = computed(() => {
  const m = new Map<string, Friend[]>();
  (data.value || []).forEach(f => { const g = f.group || "其他"; if (!m.has(g)) m.set(g, []); m.get(g)!.push(f); });
  return [...m.entries()];
});
</script>

<template>
  <div class="space-y-xl">
    <header>
      <h1 class="text-3xl font-bold text-neutral-text-primary">友情链接</h1>
      <p class="mt-xs text-sm text-neutral-text-tertiary">
        申请友链：<NuxtLink to="/guestbook" class="text-primary-500 hover:underline">留言板</NuxtLink>
        留下博客名、地址、头像、简介。
      </p>
    </header>

    <section v-for="[grp, list] in groups" :key="grp" class="space-y-sm">
      <h2 class="text-lg font-semibold text-neutral-text-primary">{{ grp }}</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-sm">
        <a
          v-for="f in list"
          :key="f.id"
          :href="f.url"
          target="_blank"
          rel="noopener noreferrer"
          class="group flex items-center gap-sm p-md bg-neutral-bg-container border border-neutral-border-secondary rounded-xl hover:shadow hover:border-primary-500/40 transition-all"
        >
          <div class="w-11 h-11 shrink-0 rounded-xl bg-gradient-to-br from-primary-500/20 to-rosetta-gold/20 overflow-hidden flex items-center justify-center">
            <NuxtImg v-if="f.avatar" :src="f.avatar" :alt="f.name" class="w-full h-full object-cover" format="avif" loading="lazy" />
            <span v-else class="text-lg font-bold text-primary-500/80">{{ f.name.slice(0,1) }}</span>
          </div>
          <div class="min-w-0 flex-1">
            <p class="font-semibold text-neutral-text-primary truncate group-hover:text-primary-500 transition-colors">{{ f.name }}</p>
            <p class="text-xs text-neutral-text-tertiary truncate mt-0.5">{{ f.description || f.url }}</p>
          </div>
        </a>
      </div>
    </section>
  </div>
</template>
