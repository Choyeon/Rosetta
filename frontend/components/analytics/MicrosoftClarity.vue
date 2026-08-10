<!--
  MicrosoftClarity — Microsoft Clarity 行为分析脚本注入
  props: id → Clarity Project ID
-->
<script setup lang="ts">
interface Props {
  id: string;
}
const props = defineProps<Props>();

let injected = false;

onMounted(() => {
  if (!props.id || injected) return;
  injected = true;
  const w = window as any;
  (function (c: any, l: any, a: any, r: any, i: any, t?: any, y?: any) {
    c[a] || (c[a] = function () {
      (c[a].q = c[a].q || []).push(arguments);
    });
    t = l.createElement(r);
    t.async = 1;
    t.src = "https://www.clarity.ms/tag/" + i;
    y = l.getElementsByTagName(r)[0];
    y.parentNode.insertBefore(t, y);
  })(w, document, "clarity", "script", props.id);
});
</script>

<template>
  <ClientOnly>
    <div class="hidden" aria-hidden data-clarity-loader />
  </ClientOnly>
</template>
