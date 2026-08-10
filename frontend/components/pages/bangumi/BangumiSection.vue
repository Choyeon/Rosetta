<!--
  BangumiSection — 番剧页面主容器 / 版块聚合
  slot: header / tabs / grid / footer
-->
<script setup lang="ts">
interface Props {
  title?: string;
  description?: string;
}
withDefaults(defineProps<Props>(), {
  title: "番剧 · Bangumi",
  description: "我的追番记录与二次元收藏",
});
</script>

<template>
  <section class="space-y-md">
    <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-md">
      <div>
        <h2 class="text-xl sm:text-2xl font-bold text-neutral-text-primary flex items-center gap-2">
          <Icon name="material-symbols:movie-creation-rounded" class="w-6 h-6 text-primary-500" />
          {{ title }}
        </h2>
        <p v-if="description" class="mt-xs text-sm text-neutral-text-tertiary">{{ description }}</p>
      </div>
      <slot name="header-right" />
    </div>
    <slot name="header" />
    <slot />
    <slot name="footer" />
  </section>
</template>
