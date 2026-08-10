<script setup lang="ts">
definePageMeta({ layout: "default" });
const route = useRoute();
const slug = computed(() => (route.params.slug as string[]).join("/"));

interface Doc {
  title?: string;
  description?: string;
  image?: string;
  body?: any;
  published?: string;
  updated?: string;
  tags?: string[];
  category?: string;
  prev?: { title?: string; slug?: string };
  next?: { title?: string; slug?: string };
  readingTime?: { text?: string };
  author?: string;
}

// 本地 content → / 后端 API 双源查询：优先取 Nuxt Content
const { data: doc, pending } = await useAsyncData<Doc | null>(
  () => "post-" + slug.value,
  async () => {
    try {
      const fromContent = await queryContent<Doc>("/posts")
        .where({ _path: `/posts/${slug.value}`, slug: slug.value })
        .withSurround({ query: { draft: { $ne: true } } })
        .findOne();
      if (fromContent) return fromContent as Doc;
    } catch { /* ignore */ }
    // 回退：后端 /api/posts/<slug>
    try {
      const resp = await $fetch<any>(`/api/posts/${slug.value}`, { timeout: 5000 });
      return (resp as any)?.data ?? resp ?? null;
    } catch { return null; }
  }
);

const isDark = computed(() => useColorMode().value === "one-dark-pro");

useHead(() => ({
  title: doc.value?.title ? `${doc.value.title} - Rosetta` : "文章 - Rosetta",
  meta: [
    { name: "description", content: doc.value?.description || "Rosetta 博客文章" },
    { property: "og:title", content: doc.value?.title },
    { property: "og:image", content: doc.value?.image },
    { property: "article:published_time", content: doc.value?.published },
  ],
  link: doc.value?.updated
    ? [{ rel: "canonical", href: `/posts/${slug.value}` }]
    : [],
}));
</script>

<template>
  <article
    class="bg-neutral-bg-container rounded-2xl border border-neutral-border-secondary shadow-sm p-lg md:p-2xl prose prose-rosetta"
    :class="isDark ? 'prose-invert' : ''"
  >
    <ClientOnly>
      <template #fallback>
        <div class="space-y-sm h-96">
          <div class="h-8 w-3/4 rounded bg-neutral-fill-hover animate-pulse" />
          <div class="h-4 w-1/3 rounded bg-neutral-fill-quaternary animate-pulse" />
          <div class="space-y-2 pt-lg">
            <div v-for="i in 8" :key="i" class="h-3.5 rounded bg-neutral-fill-quaternary animate-pulse"
              :style="{ width: `${60 + Math.random()*40}%` }" />
          </div>
        </div>
      </template>

      <ContentRenderer
        v-if="!pending && doc?.body"
        :value="doc"
        tag="div"
        class="markdown-body"
      >
        <template #empty>
          <div v-if="doc" class="space-y-md">
            <header>
              <div class="flex items-center gap-xs flex-wrap text-xs text-neutral-text-tertiary">
                <span v-if="doc.category" class="px-2 py-0.5 rounded bg-primary-500/10 text-primary-500 font-medium">{{ doc.category }}</span>
                <span v-for="t in doc.tags" :key="t" class="text-neutral-text-quaternary">#{{ t }}</span>
                <span>·</span>
                <Icon name="material-symbols:calendar-month-rounded" class="w-3.5 h-3.5" />
                {{ doc.published ? new Date(doc.published).toLocaleDateString() : "—" }}
                <span v-if="doc.updated">· 更新 {{ new Date(doc.updated).toLocaleDateString() }}</span>
                <span v-if="doc.author">· 作者 {{ doc.author }}</span>
              </div>
              <h1 class="mt-xs text-3xl font-bold text-neutral-text-primary leading-tight">
                {{ doc.title }}
              </h1>
              <p v-if="doc.description" class="mt-sm text-neutral-text-secondary leading-relaxed">{{ doc.description }}</p>
            </header>
            <NuxtImg
              v-if="doc.image"
              :src="doc.image"
              :alt="doc.title"
              class="mt-md rounded-xl border border-neutral-border-secondary max-h-80 w-full object-cover"
            />
            <div class="mt-md text-neutral-text-secondary text-sm leading-relaxed italic">
              文章内容正在加载。请确保 build 时 @nuxt/content 已成功索引该 MD。
            </div>
          </div>
        </template>
      </ContentRenderer>
    </ClientOnly>

    <!-- Prev / Next -->
    <nav v-if="!pending && (doc?.prev || doc?.next)" class="mt-3xl border-t border-neutral-border-secondary pt-lg grid grid-cols-1 md:grid-cols-2 gap-sm">
      <NuxtLink
        v-if="doc?.prev?.slug"
        :to="`/posts/${doc.prev.slug}`"
        class="p-md rounded-xl bg-neutral-bg-layout hover:bg-neutral-fill-hover border border-neutral-border-secondary text-left transition-all"
      >
        <p class="text-xs text-neutral-text-quaternary mb-xs">← 上一篇</p>
        <p class="font-medium text-neutral-text-primary line-clamp-1">{{ doc.prev.title || "上一篇" }}</p>
      </NuxtLink>
      <span v-else />
      <NuxtLink
        v-if="doc?.next?.slug"
        :to="`/posts/${doc.next.slug}`"
        class="p-md rounded-xl bg-neutral-bg-layout hover:bg-neutral-fill-hover border border-neutral-border-secondary text-right transition-all md:col-start-2"
      >
        <p class="text-xs text-neutral-text-quaternary mb-xs">下一篇 →</p>
        <p class="font-medium text-neutral-text-primary line-clamp-1">{{ doc.next.title || "下一篇" }}</p>
      </NuxtLink>
    </nav>
  </article>
</template>
