<!--
  SpineModel — Spine 动画渲染器（firefly 萤火虫效果）
  加载 /pio/static/spine-player.min.js 并在 canvas 中渲染
  props: atlasUrl / skeletonUrl / animationName / scale / width / height
-->
<script setup lang="ts">
interface Props {
  atlasUrl?: string;
  skeletonUrl?: string;
  animationName?: string;
  scale?: number;
  width?: number;
  height?: number;
  skinName?: string;
}
withDefaults(defineProps<Props>(), {
  atlasUrl: "/pio/static/firefly.atlas",
  skeletonUrl: "/pio/static/firefly.json",
  animationName: "fly",
  scale: 0.5,
  width: 200,
  height: 200,
  skinName: "default",
});

const canvasEl = ref<HTMLCanvasElement | null>(null);
let loaded = false;
let player: any = null;

function injectSpine(): Promise<void> {
  return new Promise((resolve, reject) => {
    const exist = document.querySelector<HTMLScriptElement>('script[data-spine-player="1"]');
    if (exist) { resolve(); return; }
    const s = document.createElement("script");
    s.src = "/pio/static/spine-player.min.js";
    s.async = true;
    s.setAttribute("data-spine-player", "1");
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("spine-player load failed"));
    document.head.appendChild(s);
  });
}

onMounted(async () => {
  if (!canvasEl.value) return;
  try {
    await injectSpine();
    const w = window as any;
    if (!w.spine?.SpinePlayer) return;
    loaded = true;
    player = new w.spine.SpinePlayer(canvasEl.value, {
      jsonUrl: props.skeletonUrl,
      atlasUrl: props.atlasUrl,
      animation: props.animationName,
      skin: props.skinName,
      premultipliedAlpha: true,
      backgroundColor: "transparent",
      viewport: {
        width: props.width,
        height: props.height,
        padLeft: "0%", padRight: "0%",
        padTop: "0%", padBottom: "0%",
      },
      scale: props.scale,
      showControls: false,
      debug: false,
    });
  } catch (e) {
    console.warn("[SpineModel] init failed:", e);
  }
});

onBeforeUnmount(() => {
  try {
    if (player && typeof player.dispose === "function") player.dispose();
  } catch { /* ignore */ }
  player = null;
});
</script>

<template>
  <div class="spine-wrapper relative" :style="{ width: `${width}px`, height: `${height}px` }">
    <canvas ref="canvasEl" class="w-full h-full block" :width="width" :height="height" />
  </div>
</template>
