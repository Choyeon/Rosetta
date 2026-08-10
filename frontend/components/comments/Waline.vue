<!--
  Waline — Waline 评论系统（Valine 后继）
  props: serverURL（服务端地址）、dark（深色模式 auto/true/false）
-->
<script setup lang="ts">
import { init } from "@waline/client";
import "@waline/client/style";

interface Props {
  serverURL: string;
  dark?: boolean | "auto";
  locale?: Record<string, string>;
}
const props = withDefaults(defineProps<Props>(), {
  dark: "auto",
  locale: () => ({}),
});

const walineEl = ref<HTMLElement | null>(null);
let walineInstance: ReturnType<typeof init> | null = null;

const colorMode = useColorMode();
const isDark = computed(() =>
  ["one-dark-pro", "dark", "dim", "darken"].includes(String(colorMode.value || "").toLowerCase())
);

onMounted(async () => {
  if (!walineEl.value) return;
  const darkOpt = props.dark === "auto" ? isDark.value : props.dark;
  walineInstance = init({
    el: walineEl.value,
    serverURL: props.serverURL,
    dark: darkOpt,
    pageview: true,
    comment: true,
    locale: { ...props.locale },
  });
});

onBeforeUnmount(() => {
  try {
    (walineInstance as any)?.destroy?.();
  } catch { /* ignore */ }
  walineInstance = null;
});
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl p-lg shadow-sm border border-neutral-border-secondary">
    <h3 class="text-lg font-semibold text-neutral-text-primary mb-md flex items-center gap-2">
      <Icon name="material-symbols:chat-bubble-outline-rounded" class="w-5 h-5 text-primary-500" />
      评论
    </h3>
    <div ref="walineEl" class="waline-wrapper min-h-[300px]" />
  </section>
</template>
