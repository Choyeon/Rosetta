<!--
  UmamiAnalytics — Umami 网站统计脚本注入
  props: src（Umami 脚本地址）、websiteId（网站 ID）
-->
<script setup lang="ts">
interface Props {
  src: string;
  websiteId: string;
}
const props = defineProps<Props>();

let injected = false;

onMounted(() => {
  if (!props.src || !props.websiteId || injected) return;
  injected = true;
  const existing = document.querySelector<HTMLScriptElement>(`script[data-website-id="${props.websiteId}"]`);
  if (existing) return;
  const s = document.createElement("script");
  s.async = true;
  s.defer = true;
  s.src = props.src;
  s.setAttribute("data-website-id", props.websiteId);
  s.setAttribute("data-domains", window.location.hostname);
  document.head.appendChild(s);
});
</script>

<template>
  <ClientOnly>
    <div class="hidden" aria-hidden data-umami-loader />
  </ClientOnly>
</template>
