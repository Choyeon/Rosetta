<!--
  SidebarTagCloudCard — 对应 Astro src/components/blog/sidebar/SidebarTags.astro
  标签云：彩色随机渐变 + 点击跳转 /tags/[slug]
-->
<script setup lang="ts">
interface Tag { id: number | string; slug?: string; name: string; count?: number; color?: string | null }
interface Props { tags?: Tag[]; title?: string; limit?: number }
withDefaults(defineProps<Props>(), {
  title: "标签云",
  limit: 30,
  tags: () => [
    { id: 1, name: "Vue 3", count: 12, color: "#1677ff" },
    { id: 2, name: "Nuxt 4", count: 8, color: "#00DC82" },
    { id: 3, name: "FastAPI", count: 15, color: "#009688" },
    { id: 4, name: "TypeScript", count: 9, color: "#3178C6" },
    { id: 5, name: "Tailwind", count: 14, color: "#06B6D4" },
    { id: 6, name: "迁移笔记", count: 6, color: "#722ed1" },
    { id: 7, name: "前端工程", count: 7, color: "#fa8c16" },
    { id: 8, name: "项目实战", count: 11, color: "#eb2f96" },
    { id: 9, name: "性能优化", count: 5, color: "#f5222d" },
    { id: 10, name: "随笔", count: 20, color: "#52c41a" },
    { id: 11, name: "设计", count: 4, color: "#faad14" },
    { id: 12, name: "Python", count: 16, color: "#3776AB" },
  ],
});

const gradients = [
  "from-primary-500 to-primary-700",
  "from-success-500 to-success-700",
  "from-warning-500 to-warning-700",
  "from-info-500 to-info-700",
  "from-nebula-blue to-nebula-blue-dark",
  "from-rosetta-gold to-rosetta-gold-dark",
];
function gradient(i: number, tag: Tag): string {
  if (tag.color) {
    // 用纯色做一个文本颜色（代替渐变），避免 @apply 动态拼接无法编译
    return "from-primary-500/20 to-info-500/20";
  }
  return gradients[i % gradients.length];
}
</script>

<template>
  <section
    class="bg-neutral-bg-container rounded-2xl p-lg shadow-sm border border-neutral-border-secondary"
    data-testid="sidebar-tag-cloud-card"
  >
    <div class="flex items-center justify-between mb-md">
      <h3 class="text-sm font-semibold text-neutral-text-primary uppercase tracking-wider">{{ title }}</h3>
      <NuxtLink to="/tags" class="text-xs text-neutral-text-tertiary hover:text-primary-500 transition-colors">全部 →</NuxtLink>
    </div>
    <div class="flex flex-wrap gap-xs">
      <NuxtLink
        v-for="(t, i) in (tags || []).slice(0, limit)"
        :key="t.id"
        :to="`/tags/${t.slug ?? t.id}`"
        class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border border-transparent transition-all duration-fast ease-out hover:-translate-y-0.5 hover:shadow-sm"
        :class="[
          `bg-gradient-to-r ${gradient(i, t)}`,
          t.color ? '' : 'text-white',
        ]"
        :style="t.color ? { backgroundColor: `${t.color}1F`, color: t.color, borderColor: `${t.color}33` } : {}"
      >
        <Icon name="material-symbols:sell-rounded" class="w-3.5 h-3.5 opacity-80" />
        {{ t.name }}
        <span v-if="t.count" class="opacity-80 text-[10px]">{{ t.count }}</span>
      </NuxtLink>
    </div>
  </section>
</template>
