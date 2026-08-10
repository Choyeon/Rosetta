<!--
  Live2DWidget — 看板娘（基于 pio.js 的 Live2D 模型加载器）
  props: modelUrl（默认 /pio/models/live2d/snow_miku/model.json）
  ClientOnly 内动态加载 pio.js（从 CDN 或本地 /pio/static/pio.min.js）
  inject("live2d-enabled") 控制显示
-->
<script setup lang="ts">
import Cookies from "js-cookie";

interface Props {
  modelUrl?: string;
}
const props = withDefaults(defineProps<Props>(), {
  modelUrl: "/pio/models/live2d/snow_miku/model.json",
});

const enabled = ref(true);
const mounted = ref(false);
provide<Ref<boolean>>("live2d-enabled", enabled);

function readPref() {
  try {
    const e = Cookies.get("rosetta-live2d");
    if (e !== undefined) enabled.value = e === "true";
  } catch { /* ignore */ }
}

onMounted(() => {
  readPref();
  if (!enabled.value) return;
  mounted.value = true;
  // 注入 pio.js
  const exist = document.querySelector<HTMLScriptElement>('script[data-pio="1"]');
  if (exist) return;
  const s = document.createElement("script");
  s.src = "/pio/static/pio.min.js";
  s.async = true;
  s.setAttribute("data-pio", "1");
  s.onload = () => {
    const w = window as any;
    if (!w.pio?.load) return;
    try {
      w.pio.script = "/pio/static";
      w.pio.load("live2d", props.modelUrl, {
        width: 240,
        height: 300,
        opacity: 0.95,
      });
    } catch (e) {
      console.warn("[Live2D] pio load failed:", e);
    }
  };
  document.head.appendChild(s);
});

onBeforeUnmount(() => {
  const w = window as any;
  try { w.pio?.destroy?.(); } catch { /* ignore */ }
});
</script>

<template>
  <ClientOnly>
    <div v-if="enabled && mounted" id="pio-container" class="fixed bottom-0 left-5 z-10 pointer-events-none select-none" aria-hidden />
  </ClientOnly>
</template>
