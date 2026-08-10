<!--
  BackToTop — 返回顶部悬浮按钮
  监听 window.scroll（throttle 100ms），scrollY > 300 时显示；
  点击平滑滚动到顶部（behavior: smooth）
-->
<script setup lang="ts">
import { throttle } from "throttle-debounce";

const visible = ref(false);
let scrollHandler: (() => void) | null = null;

onMounted(() => {
  scrollHandler = throttle(100, () => {
    visible.value = window.scrollY > 300;
  });
  window.addEventListener("scroll", scrollHandler, { passive: true });
  scrollHandler();
});

onBeforeUnmount(() => {
  if (scrollHandler) {
    window.removeEventListener("scroll", scrollHandler);
    scrollHandler = null;
  }
});

function goTop() {
  window.scrollTo({ top: 0, behavior: "smooth" });
}
</script>

<template>
  <Transition name="fade">
    <button
      v-show="visible"
      type="button"
      aria-label="返回顶部"
      class="fixed bottom-24 right-5 z-popover w-11 h-11 rounded-full bg-neutral-bg-container border border-neutral-border-secondary shadow-md hover:bg-primary-500 hover:text-white hover:border-primary-500 text-neutral-text-secondary transition-all duration-fast ease-out flex items-center justify-center group"
      @click="goTop"
    >
      <Icon name="material-symbols:arrow-upward-rounded" class="w-5 h-5 transition-transform duration-fast group-hover:-translate-y-0.5" />
    </button>
  </Transition>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 200ms ease, transform 200ms ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(8px); }
</style>
