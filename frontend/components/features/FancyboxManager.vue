<!--
  FancyboxManager — Fancyapps UI 图片灯箱管理器
  绑定所有 [data-fancybox] 元素；监听路由变化时重新绑定
  import { Fancybox } from "@fancyapps/ui"
-->
<script setup lang="ts">
import { Fancybox } from "@fancyapps/ui";
import "@fancyapps/ui/dist/fancybox/fancybox.css";

const colorMode = useColorMode();
const isDark = computed(() =>
  ["one-dark-pro", "dark", "dim", "darken"].includes(String(colorMode.value || "").toLowerCase())
);

function bind() {
  const root = document.body;
  Fancybox.bind(root, "[data-fancybox]", {
    animated: true,
    autoFocus: false,
    trapFocus: false,
    placeFocusBack: false,
    showClass: "fancybox-fadeIn",
    hideClass: "fancybox-fadeOut",
    Thumbs: { autostart: false, type: "modern" },
    Toolbar: {
      display: {
        left: ["infobar"],
        middle: ["zoomIn", "zoomOut", "toggle1to1", "rotateCCW", "rotateCW", "flipX", "flipY"],
        right: ["slideshow", "thumbs", "close"],
      },
    },
    Image: { zoom: true, wheel: "slide" },
    Carousel: { transition: "slide" },
    Images: { Panzoom: { maxScale: 2 } },
    defaultDisplay: isDark.value ? "dark" : "light",
    Html: { autoSize: false },
  });
}

function unbind() {
  try { Fancybox.unbind("[data-fancybox]"); } catch { /* ignore */ }
}

onMounted(() => {
  nextTick(() => {
    bind();
    const stop = watch(
      () => useRoute().fullPath,
      () => {
        unbind();
        nextTick(() => {
          setTimeout(bind, 120);
        });
      }
    );
    onBeforeUnmount(stop);
  });
});

onBeforeUnmount(() => {
  unbind();
  try { Fancybox.close(); } catch { /* ignore */ }
});
</script>

<template>
  <div class="hidden" aria-hidden data-fancybox-manager />
</template>
