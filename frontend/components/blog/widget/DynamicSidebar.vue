<!--
  DynamicSidebar — 侧边栏最新动态（摘要卡片）
  props: items[{id, content, createdAt, likes, images}]
-->
<script setup lang="ts">
interface Dynamic {
  id: string | number;
  content: string;
  createdAt: string;
  likes?: number;
  comments?: number;
  images?: string[];
}
interface Props {
  items?: Dynamic[];
  limit?: number;
}
withDefaults(defineProps<Props>(), {
  items: () => [
    { id: 1, content: "新的主题终于上线啦，配色参考了 Rosetta Stone 石盘的感觉～", createdAt: dayjs().subtract(2, "hour").toISOString(), likes: 32, comments: 8 },
    { id: 2, content: "迁移到 Nuxt 4 第一天，水合速度真的快了好多。", createdAt: dayjs().subtract(1, "day").toISOString(), likes: 17, comments: 3 },
    { id: 3, content: "今晚 22:30 直播聊聊前端性能优化的那些坑！", createdAt: dayjs().subtract(3, "day").toISOString(), likes: 56, comments: 14 },
  ],
  limit: 3,
});

const list = computed(() => (props.items || []).slice(0, props.limit));
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl p-md shadow-sm border border-neutral-border-secondary">
    <header class="flex items-center justify-between mb-sm">
      <h3 class="text-sm font-semibold text-neutral-text-primary flex items-center gap-1.5">
        <Icon name="material-symbols:bolt-rounded" class="w-4 h-4 text-primary-500" />
        最新动态
      </h3>
      <NuxtLink to="/dynamic" class="text-[11px] text-neutral-text-tertiary hover:text-primary-500 transition-colors flex items-center gap-0.5">
        全部 <Icon name="material-symbols:arrow-outward-rounded" class="w-3 h-3" />
      </NuxtLink>
    </header>
    <ul class="space-y-sm">
      <li v-for="d in list" :key="d.id">
        <NuxtLink
          to="/dynamic"
          class="block group rounded-xl p-xs hover:bg-neutral-fill-hover transition-all duration-fast"
        >
          <p class="text-xs text-neutral-text-secondary leading-relaxed line-clamp-2 group-hover:text-neutral-text-primary transition-colors">
            {{ d.content }}
          </p>
          <div class="mt-xs flex items-center justify-between text-[10px] text-neutral-text-quaternary">
            <span class="flex items-center gap-1">
              <Icon name="material-symbols:schedule-rounded" class="w-3 h-3" />
              {{ dayjs(d.createdAt).fromNow() }}
            </span>
            <span class="flex items-center gap-2">
              <span v-if="d.likes" class="inline-flex items-center gap-0.5">
                <Icon name="material-symbols:favorite-outline-rounded" class="w-3 h-3" />
                {{ d.likes }}
              </span>
              <span v-if="d.comments" class="inline-flex items-center gap-0.5">
                <Icon name="material-symbols:mode-comment-outline-rounded" class="w-3 h-3" />
                {{ d.comments }}
              </span>
            </span>
          </div>
        </NuxtLink>
      </li>
      <li v-if="!list.length" class="text-xs text-neutral-text-tertiary py-xs text-center">暂无动态</li>
    </ul>
  </section>
</template>
