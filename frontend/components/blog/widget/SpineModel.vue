<!--
  SpineModel（侧边栏版） — 萤火虫 Spine 动画
  嵌入在侧边栏卡片中，尺寸自适应；点击"换一批"换动画
-->
<script setup lang="ts">
interface Props {
  width?: number;
  height?: number;
  title?: string;
}
withDefaults(defineProps<Props>(), { width: 220, height: 120, title: "萤火虫 · Spine" });

const variant = ref(0);
const variants = [
  { skeleton: "/pio/static/firefly.json", atlas: "/pio/static/firefly.atlas", anim: "fly", skin: "default" },
  { skeleton: "/pio/static/firefly.json", atlas: "/pio/static/firefly.atlas", anim: "glow", skin: "summer" },
];

function next() {
  variant.value = (variant.value + 1) % variants.length;
}
const cur = computed(() => variants[variant.value]);
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl p-md shadow-sm border border-neutral-border-secondary overflow-hidden">
    <header class="flex items-center justify-between mb-xs">
      <h3 class="text-sm font-semibold text-neutral-text-primary flex items-center gap-1.5">
        <Icon name="material-symbols:wb-twighlight-rounded" class="w-4 h-4 text-primary-500" />
        {{ title }}
      </h3>
      <button
        type="button"
        class="text-[11px] px-2 py-0.5 rounded-md text-neutral-text-tertiary hover:text-primary-500 hover:bg-primary-500/10 transition-colors inline-flex items-center gap-0.5"
        @click="next"
      >
        <Icon name="material-symbols:refresh-rounded" class="w-3 h-3" />
        换一个
      </button>
    </header>
    <div
      class="rounded-xl overflow-hidden border border-neutral-border-secondary bg-gradient-to-br from-indigo-950 via-purple-950 to-slate-900 relative"
      :style="{ width: `${width}px`, height: `${height}px`, maxWidth: '100%' }"
    >
      <ClientOnly>
        <SpineModel
          :key="variant"
          :skeleton-url="cur.skeleton"
          :atlas-url="cur.atlas"
          :animation-name="cur.anim"
          :skin-name="cur.skin"
          :width="width"
          :height="height"
          :scale="0.55"
        />
      </ClientOnly>
      <div class="absolute inset-x-0 bottom-0 text-[10px] text-white/60 px-xs py-xs bg-gradient-to-t from-black/40 to-transparent flex items-center justify-between">
        <span>Ambient · 动态装饰</span>
        <span class="flex items-center gap-0.5">
          <span class="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          Live
        </span>
      </div>
    </div>
  </section>
</template>
