<!--
  MusicPlayer — APlayer + Meting 音乐播放器
  props: server (netease/tencent/kugou/baidu/xiami)、type (song/playlist/album/search/artist)、id
  示例：server="netease" type="playlist" id="76264954"
  onMounted 创建 APlayer 实例并绑定 Meting
-->
<script setup lang="ts">
import APlayer from "aplayer";
// APlayer CSS 已在 nuxt.config.ts 全局注入

// Meting 是 UMD 全局包；需要时动态从 CDN 注入（bundler 无法解析其 ESM 出口）
async function ensureMeting(): Promise<(opts: any) => void> {
  const G = globalThis as any;
  if (typeof G.Meting === "function") return G.Meting;
  await new Promise<void>((resolve, reject) => {
    if (!import.meta.client) return reject(new Error("no client"));
    const s = document.createElement("script");
    s.src = "https://cdn.jsdelivr.net/npm/meting@2.0.2/dist/Meting.min.js";
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Meting load failed"));
    document.head.appendChild(s);
  });
  return G.Meting;
}

interface Props {
  server?: "netease" | "tencent" | "kugou" | "baidu" | "xiami";
  type?: "song" | "playlist" | "album" | "search" | "artist";
  id?: string;
  fixed?: boolean;
  mini?: boolean;
  autoplay?: boolean;
  order?: "list" | "random";
  volume?: number;
  mutex?: boolean;
  lrcType?: number;
  listFolded?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  server: "netease",
  type: "playlist",
  id: "76264954",
  fixed: false,
  mini: false,
  autoplay: false,
  order: "random",
  volume: 0.6,
  mutex: true,
  lrcType: 1,
  listFolded: false,
});

const playerEl = ref<HTMLElement | null>(null);
let ap: InstanceType<typeof APlayer> | null = null;

const enabled = inject<Ref<boolean>>("music-enabled", ref(true));
const playerKey = Symbol("aplayer-instance");
provide(playerKey, computed(() => ap));

onMounted(async () => {
  if (!playerEl.value) return;
  try {
    ap = new APlayer({
      container: playerEl.value,
      fixed: props.fixed,
      mini: props.mini,
      autoplay: props.autoplay && enabled.value,
      order: props.order,
      volume: props.volume,
      mutex: props.mutex,
      lrcType: props.lrcType,
      listFolded: props.listFolded,
      listMaxHeight: "260px",
      audio: [],
    });
    try {
      const MetingFn = await ensureMeting();
      MetingFn({
        auto: undefined,
        server: props.server,
        type: props.type,
        id: props.id,
        api: "https://api.i-meto.com/meting/api?server=:server&type=:type&id=:id&r=:r",
      }).init(ap);
    } catch { /* Meting 非必需 */ }
  } catch (e) {
    console.warn("[APlayer] init failed:", e);
  }
});

onBeforeUnmount(() => {
  try { ap?.destroy(); } catch { /* ignore */ }
  ap = null;
});

watch(enabled, (v) => {
  if (!ap) return;
  try {
    if (!v) ap.pause();
  } catch { /* ignore */ }
});
</script>

<template>
  <div
    class="aplayer-wrapper"
    :class="{ 'opacity-40 pointer-events-none': !enabled }"
  >
    <div ref="playerEl" />
  </div>
</template>

<style scoped>
.aplayer-wrapper {
  --ap-theme-color: var(--rosetta-primary-500, #1677ff);
}
</style>
