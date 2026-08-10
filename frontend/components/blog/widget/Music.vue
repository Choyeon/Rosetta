<!--
  Music — 侧边栏音乐播放器（精简版 APlayer mini）
  内部嵌入 BackgroundPlayer/MusicPlayer 的触发入口
-->
<script setup lang="ts">
import Cookies from "js-cookie";

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

const playing = ref(false);
const enabled = inject<Ref<boolean>>("music-enabled", ref(true));
const track = ref({ name: "Rosetta OST — 轻羽", artist: "Choyu", cover: "" });

onMounted(() => {
  try {
    const e = Cookies.get("rosetta-music");
    if (e !== undefined) enabled.value = e === "true";
  } catch { /* ignore */ }
});
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl p-md shadow-sm border border-neutral-border-secondary">
    <header class="flex items-center justify-between mb-sm">
      <h3 class="text-sm font-semibold text-neutral-text-primary flex items-center gap-1.5">
        <Icon name="material-symbols:music-note-rounded" class="w-4 h-4 text-primary-500" />
        背景音乐
      </h3>
      <button
        type="button"
        class="w-7 h-7 rounded-md flex items-center justify-center transition-colors"
        :class="enabled ? 'text-primary-500 bg-primary-500/10' : 'text-neutral-text-tertiary hover:text-neutral-text-secondary hover:bg-neutral-fill-hover'"
        :aria-pressed="enabled"
        @click="enabled = !enabled"
        :aria-label="enabled ? '暂停音乐' : '开启音乐'"
      >
        <Icon v-if="playing" name="material-symbols:pause-rounded" class="w-3.5 h-3.5" />
        <Icon v-else name="material-symbols:play-arrow-rounded" class="w-3.5 h-3.5" />
      </button>
    </header>
    <div class="rounded-xl bg-gradient-to-br from-primary-500 via-primary-600 to-rosetta-nebula p-sm text-white shadow-md">
      <div class="flex items-center gap-sm">
        <div class="w-12 h-12 rounded-lg bg-white/20 backdrop-blur-sm flex items-center justify-center flex-shrink-0 overflow-hidden">
          <Icon name="material-symbols:album-rounded" class="w-6 h-6 animate-spin-slow" />
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-sm font-semibold line-clamp-1">{{ track.name }}</div>
          <div class="text-xs opacity-80 line-clamp-1">{{ track.artist }}</div>
          <div class="mt-xs h-1 rounded-full bg-white/20 overflow-hidden">
            <div class="h-full w-1/3 rounded-full bg-white/90 animate-progress" />
          </div>
        </div>
      </div>
    </div>
    <div class="mt-xs text-[10px] text-neutral-text-quaternary flex items-center justify-between">
      <span>默认：网易云·Rosetta 精选</span>
      <a class="hover:text-primary-500 transition-colors cursor-pointer" @click="playing = !playing">
        {{ playing ? '暂停' : '播放' }}
      </a>
    </div>
  </section>
</template>

<style scoped>
@keyframes spin-slow { to { transform: rotate(360deg); } }
.animate-spin-slow { animation: spin-slow 12s linear infinite; }
@keyframes progress { 0% { width: 0; } 100% { width: 100%; } }
.animate-progress { animation: progress 120s linear infinite; }
</style>
