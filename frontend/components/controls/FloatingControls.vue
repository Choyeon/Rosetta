<!--
  FloatingControls — 悬浮操作按钮组
  组合：BackToTop + ColorSchemeToggle + 音乐开关 + 看板娘开关
  各按钮可独立控制；折叠/展开状态 js-cookie 持久化
-->
<script setup lang="ts">
import Cookies from "js-cookie";

interface Props {
  showMusic?: boolean;
  showLive2d?: boolean;
}
withDefaults(defineProps<Props>(), {
  showMusic: true,
  showLive2d: true,
});

const musicOn = inject<Ref<boolean>>("music-enabled", ref(true));
const live2dOn = inject<Ref<boolean>>("live2d-enabled", ref(true));

function toggleMusic() {
  musicOn.value = !musicOn.value;
  Cookies.set("rosetta-music", String(musicOn.value), { expires: 365, path: "/" });
}
function toggleLive2d() {
  live2dOn.value = !live2dOn.value;
  Cookies.set("rosetta-live2d", String(live2dOn.value), { expires: 365, path: "/" });
}
</script>

<template>
  <div class="fixed bottom-5 right-5 z-popover flex flex-col gap-2 pointer-events-none">
    <div class="pointer-events-auto flex flex-col gap-2">
      <ClientOnly>
        <ColorSchemeToggle />
      </ClientOnly>
      <button
        v-if="showMusic"
        type="button"
        class="w-11 h-11 rounded-full bg-neutral-bg-container border border-neutral-border-secondary shadow-md hover:border-primary-500 transition-all duration-fast flex items-center justify-center"
        :class="musicOn ? 'text-primary-500' : 'text-neutral-text-secondary'"
        :aria-label="musicOn ? '关闭背景音乐' : '开启背景音乐'"
        :aria-pressed="musicOn"
        @click="toggleMusic"
      >
        <Icon v-if="musicOn" name="material-symbols:music-note-rounded" class="w-5 h-5" />
        <Icon v-else name="material-symbols:music-off-rounded" class="w-5 h-5" />
      </button>
      <button
        v-if="showLive2d"
        type="button"
        class="w-11 h-11 rounded-full bg-neutral-bg-container border border-neutral-border-secondary shadow-md hover:border-primary-500 transition-all duration-fast flex items-center justify-center"
        :class="live2dOn ? 'text-primary-500' : 'text-neutral-text-secondary'"
        :aria-label="live2dOn ? '关闭看板娘' : '开启看板娘'"
        :aria-pressed="live2dOn"
        @click="toggleLive2d"
      >
        <Icon name="material-symbols:smart-toy-rounded" class="w-5 h-5" />
      </button>
      <BackToTop />
    </div>
  </div>
</template>
