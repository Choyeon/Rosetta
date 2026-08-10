<!--
  GoogleAnalytics — Google Analytics 4 (gtag.js) 动态注入
  props: id → GA4 测量 ID (G-XXXXXXXXXX)
-->
<script setup lang="ts">
interface Props {
  id: string;
}
const props = defineProps<Props>();

const runtimeConfig = useRuntimeConfig();
let injected = false;

onMounted(() => {
  if (!props.id || injected) return;
  injected = true;
  const w = window as any;
  const d = document;
  const s = "script";
  w.dataLayer = w.dataLayer || [];
  function gtag(...args: any[]) { w.dataLayer.push(args); }
  w.gtag = gtag;
  gtag("js", new Date());
  gtag("config", props.id, {
    page_path: window.location.pathname,
    send_page_view: true,
    anonymize_ip: true,
  });
  const f = d.getElementsByTagName(s)[0];
  const j = d.createElement(s) as HTMLScriptElement;
  j.async = true;
  j.src = `https://www.googletagmanager.com/gtag/js?id=${props.id}`;
  j.setAttribute("data-nonce", "");
  f.parentNode?.insertBefore(j, f);
});
</script>

<template>
  <ClientOnly>
    <div class="hidden" aria-hidden data-google-analytics-loader />
  </ClientOnly>
</template>
