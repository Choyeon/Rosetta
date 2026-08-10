<!--
  ScrollDownIndicator — 首屏向下滚动引导箭头
  使用 @vueuse/motion 的 visible 指令触发进入动画；
  点击后平滑滚动到下一屏 (window.innerHeight)
-->
<script setup lang="ts">
const visible = ref(true);

onMounted(() => {
  const onScroll = () => {
    visible.value = window.scrollY < 80;
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onBeforeUnmount(() => window.removeEventListener("scroll", onScroll));
});

function scrollDown() {
  window.scrollTo({ top: window.innerHeight - 60, behavior: "smooth" });
}
</script>

<template>
  <ClientOnly>
    <Transition name="bounce-fade">
      <button
        v-show="visible"
        type="button"
        aria-label="向下滚动"
        class="fixed bottom-8 left-1/2 -translate-x-1/2 z-10 text-neutral-text-tertiary hover:text-primary-500 transition-colors duration-fast flex flex-col items-center gap-1 animate-bounce-slow"
        @click="scrollDown"
      >
        <span class="text-xs font-medium tracking-wide">向下滚动</span>
        <Icon name="material-symbols:keyboard-double-arrow-down-rounded" class="w-6 h-6" />
      </button>
    </Transition>
  </ClientOnly>
</template>

<style scoped>
.bounce-fade-enter-active, .bounce-fade-leave-active { transition: opacity 300ms ease, transform 300ms ease; }
.bounce-fade-enter-from, .bounce-fade-leave-to { opacity: 0; transform: translate(-50%, 10px); }
@keyframes bounce-slow {
  0%, 100% { transform: translate(-50%, 0); }
  50% { transform: translate(-50%, -6px); }
}
.animate-bounce-slow { animation: bounce-slow 1.8s ease-in-out infinite; }
</style>
