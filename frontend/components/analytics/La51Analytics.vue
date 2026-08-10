<!--
  La51Analytics — 51.la (Web Analytics) 统计脚本注入
  通过 runtimeConfig.public.la51Id 读取站点 ID，或通过 props.id 覆盖
-->
<script setup lang="ts">
interface Props {
  id?: string;
}
const props = withDefaults(defineProps<Props>(), { id: "" });

const runtimeConfig = useRuntimeConfig();
const resolvedId = computed(() => props.id || String((runtimeConfig.public as any)?.la51Id || ""));

let injected = false;

onMounted(() => {
  if (!resolvedId.value || injected) return;
  injected = true;
  const w = window as any;
  w._51hmt = w._51hmt || [];
  const hm = document.createElement("script");
  hm.src = `https://js.users.51.la/${resolvedId.value}.js`;
  hm.async = true;
  hm.id = "LA51-Script";
  const s = document.getElementsByTagName("script")[0];
  s.parentNode?.insertBefore(hm, s);
});
</script>

<template>
  <ClientOnly>
    <div class="hidden" aria-hidden data-la51-loader />
  </ClientOnly>
</template>
