<!--
  Twikoo — Twikoo 评论系统（腾讯云开发 / Vercel）
  props: envId（环境 ID）、region（地域，默认 ap-shanghai）
-->
<script setup lang="ts">
import Twikoo from "twikoo";

interface Props {
  envId: string;
  region?: string;
}
const props = withDefaults(defineProps<Props>(), {
  region: "ap-shanghai",
});

const twikooEl = ref<HTMLElement | null>(null);

onMounted(async () => {
  if (!twikooEl.value) return;
  try {
    await Twikoo.init({
      envId: props.envId,
      el: twikooEl.value,
      region: props.region,
      path: window.location.pathname,
      lang: "zh-CN",
    });
  } catch (e) {
    console.warn("[Twikoo] init failed:", e);
  }
});
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl p-lg shadow-sm border border-neutral-border-secondary">
    <h3 class="text-lg font-semibold text-neutral-text-primary mb-md flex items-center gap-2">
      <Icon name="material-symbols:chat-bubble-outline-rounded" class="w-5 h-5 text-primary-500" />
      评论
    </h3>
    <div ref="twikooEl" id="twikoo-wrap" class="min-h-[300px]" />
  </section>
</template>
