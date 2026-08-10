<!--
  BackgroundPlayer — 背景音乐单例（provide/inject APlayer instance）
  固定在底部，可折叠/展开；provide("aplayer-instance") 给其他组件调用
-->
<script setup lang="ts">
import APlayer from "aplayer";
// APlayer CSS 已在 nuxt.config.ts 全局注入，避免 HMR 重复样式抖动
import Cookies from "js-cookie";

// Meting (2.0.x) 是 UMD 包，走浏览器全局 window.Meting 而非 bundler import（bundler 无法解析其 ESM 出口）
// 这里提供一个函数级的动态加载：如果全局未定义，则从 node_modules 路径或 CDN 动态注入脚本标签
async function ensureMeting(): Promise<(opts: any) => void> {
  const G = globalThis as any;
  if (typeof G.Meting === "function") return G.Meting;
  await new Promise<void>((resolve, reject) => {
    if (!import.meta.client) return reject(new Error("no client"));
    const s = document.createElement("script");
    // 优先 jsdelivr 的 Meting 2.0
    s.src = "https://cdn.jsdelivr.net/npm/meting@2.0.2/dist/Meting.min.js";
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Meting load failed"));
    document.head.appendChild(s);
  });
  return G.Meting;
}

interface Props {
  server?: string;
  type?: string;
  id?: string;
}
withDefaults(defineProps<Props>(), {
  server: "netease",
  type: "playlist",
  id: "76264954",
});

const playerEl = ref<HTMLElement | null>(null);
const collapsed = ref(true);
const enabled = ref(true);
let ap: InstanceType<typeof APlayer> | null = null;

provide<Ref<boolean>>("music-enabled", enabled);
provide<Ref<InstanceType<typeof APlayer> | null>>("aplayer-instance", computed(() => ap));

function readPref() {
  try {
    const e = Cookies.get("rosetta-music");
    if (e !== undefined) enabled.value = e === "true";
  } catch { /* ignore */ }
}

onMounted(async () => {
  readPref();
  if (!playerEl.value) return;
  try {
    ap = new APlayer({
      container: playerEl.value,
      fixed: true,
      mini: true,
      autoplay: false,
      order: "random",
      volume: 0.6,
      mutex: true,
      lrcType: 1,
      listFolded: true,
      listMaxHeight: "240px",
      audio: [],
    });
    try {
      const MetingFn = await ensureMeting();
      MetingFn({
        server: "netease",
        type: "playlist",
        id: "76264954",
        api: "https://api.i-meto.com/meting/api?server=:server&type=:type&id=:id&r=:r",
      }).init(ap);
    } catch { /* Meting 非必需；APlayer 空播放列表仍可运行 */ }
  } catch (e) {
    console.warn("[BackgroundPlayer] init failed:", e);
  }
});

onBeforeUnmount(() => {
  try { ap?.destroy(); } catch { /* ignore */ }
  ap = null;
});

function toggle() { collapsed.value = !collapsed.value; }
</script>

<template>
  <ClientOnly>
    <div class="fixed bottom-5 left-5 z-popover pointer-events-none">
      <button
        type="button"
        class="pointer-events-auto w-12 h-12 rounded-full bg-gradient-to-br from-primary-400 via-primary-500 to-rosetta-nebula text-white shadow-lg hover:shadow-xl transition-all duration-fast flex items-center justify-center group"
        :class="{ 'animate-pulse-slow': enabled && !collapsed }"
        :aria-label="enabled ? '音乐播放器' : '音乐已关闭'"
        @click="toggle"
      >
        <Icon v-if="enabled" name="material-symbols:graphic-eq-rounded" class="w-5 h-5 transition-transform group-hover:rotate-12" />
        <Icon v-else name="material-symbols:music-off-rounded" class="w-5 h-5" />
      </button>
      <Transition name="slide-up">
        <div v-show="!collapsed" class="pointer-events-auto mt-2 w-80 max-w-[calc(100vw-2.5rem)]">
          <div ref="playerEl" />
        </div>
      </Transition>
    </div>
  </ClientOnly>
</template>

<style scoped>
.slide-up-enter-active, .slide-up-leave-active { transition: opacity 200ms ease, transform 200ms ease; }
.slide-up-enter-from, .slide-up-leave-to { opacity: 0; transform: translateY(12px); }
@keyframes pulse-slow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(22,119,255,0.4); }
  50% { box-shadow: 0 0 0 10px rgba(22,119,255,0); }
}
.animate-pulse-slow { animation: pulse-slow 2.2s ease-in-out infinite; }
</style>
