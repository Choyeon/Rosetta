<!--
  Tags — 侧边栏标签云组件
  props: tags[{ name, slug, count }]
  字号基于 count 动态（3 档）；可限制显示数量，展开/收起
-->
<script setup lang="ts">
interface Tag { name: string; slug: string; count?: number; }
interface Props {
  tags?: Tag[];
  showAll?: boolean;
  defaultShow?: number;
}
withDefaults(defineProps<Props>(), {
  tags: () => [],
  showAll: false,
  defaultShow: 24,
});

const allShown = ref(props.showAll);
const display = computed(() => allShown.value ? props.tags : props.tags?.slice(0, props.defaultShow));
const hasMore = computed(() => (props.tags?.length || 0) > props.defaultShow);

const maxCount = computed(() => Math.max(1, ...(props.tags?.map((t) => t.count || 1) || [1])));
function sizeOf(c: number) {
  const r = c / maxCount.value;
  if (r > 0.66) return "text-sm font-semibold";
  if (r > 0.33) return "text-xs font-medium";
  return "text-[11px]";
}
function toggle() { allShown.value = !allShown.value; }
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl p-md shadow-sm border border-neutral-border-secondary">
    <header class="flex items-center justify-between mb-sm">
      <h3 class="text-sm font-semibold text-neutral-text-primary flex items-center gap-1.5">
        <Icon name="material-symbols:sell-rounded" class="w-4 h-4 text-primary-500" />
        标签
      </h3>
      <NuxtLink to="/tags" class="text-[11px] text-neutral-text-tertiary hover:text-primary-500 transition-colors flex items-center gap-0.5">
        全部 <Icon name="material-symbols:arrow-outward-rounded" class="w-3 h-3" />
      </NuxtLink>
    </header>
    <div class="flex flex-wrap gap-1">
      <NuxtLink
        v-for="t in display" :key="t.slug"
        :to="`/tags/${t.slug}`"
        class="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-neutral-fill-hover hover:bg-primary-500/10 hover:text-primary-500 text-neutral-text-secondary transition-colors duration-fast"
        :class="sizeOf(t.count || 1)"
      >
        #{{ t.name }}
        <span v-if="t.count" class="opacity-60 text-[10px]">{{ t.count }}</span>
      </NuxtLink>
      <div v-if="!tags?.length" class="text-xs text-neutral-text-tertiary py-xs">暂无标签</div>
    </div>
    <button
      v-if="hasMore"
      type="button"
      class="mt-sm w-full text-[11px] text-neutral-text-tertiary hover:text-primary-500 transition-colors flex items-center justify-center gap-1"
      @click="toggle"
    >
      {{ allShown ? '收起' : `展开剩余 ${tags.length - defaultShow} 个` }}
      <Icon :name="allShown ? 'material-symbols:expand-less-rounded' : 'material-symbols:expand-more-rounded'" class="w-3.5 h-3.5" />
    </button>
  </section>
</template>
