<!--
  Artalk — Artalk 自托管评论系统客户端
  props: server（后端地址）、site（站点名）、id（pageKey/当前页面标识）
  生命周期：onMounted 动态 new Artalk，onBeforeUnmount destroy
-->
<script setup lang="ts">
import Artalk from "artalk";
import "artalk/dist/Artalk.css";

interface Props {
  server: string;
  site?: string;
  id?: string;
}
const props = withDefaults(defineProps<Props>(), {
  site: "Rosetta",
  id: () => (import.meta.client ? window.location.pathname : ""),
});

const artalkEl = ref<HTMLElement | null>(null);
let artalkInstance: InstanceType<typeof Artalk> | null = null;

onMounted(() => {
  if (!artalkEl.value) return;
  artalkInstance = new Artalk({
    el: artalkEl.value,
    server: props.server,
    site: props.site,
    pageKey: props.id || window.location.pathname,
    pageTitle: document.title,
    dark: "auto",
  });
});

onBeforeUnmount(() => {
  artalkInstance?.destroy();
  artalkInstance = null;
});
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl p-lg shadow-sm border border-neutral-border-secondary">
    <h3 class="text-lg font-semibold text-neutral-text-primary mb-md flex items-center gap-2">
      <Icon name="material-symbols:chat-bubble-outline-rounded" class="w-5 h-5 text-primary-500" />
      评论
    </h3>
    <div ref="artalkEl" class="artalk-wrapper" />
  </section>
</template>

<style scoped>
.artalk-wrapper { min-height: 300px; }
</style>
