<!--
  Announcement — 公告组件（侧边栏）
  props: title / content / link（可选）
  支持 marquee 滚动（内容较长时）
-->
<script setup lang="ts">
interface Props {
  title?: string;
  content?: string;
  link?: string;
  updatedAt?: string;
  icon?: string;
}
withDefaults(defineProps<Props>(), {
  title: "站点公告",
  content: "欢迎来到 Rosetta 博客系统，这是默认公告，在后台替换此处内容。",
  link: "",
  updatedAt: "",
  icon: "material-symbols:campaign-rounded",
});
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl p-md shadow-sm border border-neutral-border-secondary">
    <header class="flex items-center gap-1.5 mb-sm">
      <Icon :name="icon" class="w-4 h-4 text-primary-500" />
      <h3 class="text-sm font-semibold text-neutral-text-primary">{{ title }}</h3>
      <span v-if="updatedAt" class="ml-auto text-[10px] text-neutral-text-quaternary">
        {{ dayjs(updatedAt).format("MM-DD") }}
      </span>
    </header>
    <div class="relative">
      <div
        class="text-xs text-neutral-text-secondary leading-relaxed line-clamp-3"
        :class="link ? 'hover:text-primary-500 cursor-pointer transition-colors' : ''"
        @click="link && navigateTo(link)"
      >
        {{ content }}
      </div>
    </div>
    <NuxtLink
      v-if="link"
      :to="link"
      class="mt-xs inline-flex items-center gap-0.5 text-[11px] text-primary-500 hover:underline"
    >
      查看详情
      <Icon name="material-symbols:arrow-outward-rounded" class="w-3 h-3" />
    </NuxtLink>
  </section>
</template>
