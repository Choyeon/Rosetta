<script setup lang="ts">
definePageMeta({ layout: "default" });
useHead({ title: "归档 - Rosetta", meta: [{ name: "description", content: "按时间归档所有文章。" }] });

interface Group { year: number; month: number; label: string; posts: any[] }

// 策略：本地 content 查询所有发布时间；后端回退
const { data: posts } = await useAsyncData("archive", async () => {
  try {
    const local = await queryContent<any>("/posts")
      .where({ draft: { $ne: true } })
      .only(["title", "slug", "_path", "published", "description"])
      .sort({ published: -1 })
      .limit(500)
      .find();
    if (local.length) return local;
  } catch { /* ignore */ }
  try {
    const r = await $fetch<any>("/api/posts", { query: { pageSize: 500, _timeout: 8000 } });
    return r?.items ?? [];
  } catch { return []; }
});

const groups = computed<Group[]>(() => {
  const g = new Map<string, Group>();
  (posts.value || []).forEach(p => {
    const d = new Date(p.published || p.updated || 0);
    if (!d.getFullYear()) return;
    const y = d.getFullYear(), m = d.getMonth() + 1;
    const k = `${y}-${m}`;
    if (!g.has(k)) g.set(k, { year: y, month: m, label: `${y}年${m}月`, posts: [] });
    g.get(k)!.posts.push(p);
  });
  return [...g.values()].sort((a, b) => (b.year * 12 + b.month) - (a.year * 12 + a.month));
});
</script>

<template>
  <div class="space-y-xl">
    <header>
      <h1 class="text-3xl font-bold text-neutral-text-primary">归档时间线</h1>
      <p class="mt-xs text-sm text-neutral-text-tertiary">共 {{ (posts || []).length }} 篇文章</p>
    </header>
    <div v-if="groups.length === 0" class="text-sm text-neutral-text-tertiary text-center py-xl">暂无内容。</div>
    <section v-for="grp in groups" :key="grp.label" class="relative pl-md">
      <div class="absolute left-0 top-1 w-3 h-3 rounded-full bg-primary-500 ring-4 ring-primary-500/10" />
      <h2 class="text-xl font-bold text-neutral-text-primary sticky top-16 bg-neutral-bg-layout/80 backdrop-blur-sm py-xs -mx-md px-md z-[1]">
        {{ grp.label }} <span class="text-neutral-text-quaternary font-normal text-sm ml-xs">{{ grp.posts.length }} 篇</span>
      </h2>
      <ol class="mt-sm space-y-xs border-l-2 border-neutral-border-secondary ml-[5px] pl-md">
        <li v-for="p in grp.posts" :key="p.slug || p._path" class="group">
          <NuxtLink
            :to="`/posts/${p.slug || (p._path||'').replace('/posts/','')}`"
            class="flex items-baseline gap-xs text-sm text-neutral-text-secondary hover:text-primary-500 transition-colors py-xs"
          >
            <span class="shrink-0 text-xs text-neutral-text-quaternary tabular-nums font-mono w-14">
              {{ new Date(p.published || 0).toLocaleDateString().slice(5) }}
            </span>
            <span class="truncate group-hover:underline decoration-dotted underline-offset-4">{{ p.title }}</span>
          </NuxtLink>
        </li>
      </ol>
    </section>
  </div>
</template>
