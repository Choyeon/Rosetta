<!--
  Giscus — 基于 GitHub Discussions 的评论系统
  使用 @giscus/vue 动态注入；所有配置项通过 props 透传
-->
<script setup lang="ts">
interface Props {
  repo: `${string}/${string}`;
  repoId: string;
  category?: string;
  categoryId?: string;
  mapping?: "pathname" | "url" | "title" | "og:title" | "specific" | "number";
  term?: string;
  theme?: "light" | "dark" | "preferred_color_scheme" | "transparent_dark" | string;
  reactionsEnabled?: "0" | "1";
  emitMetadata?: "0" | "1";
  inputPosition?: "top" | "bottom";
  lang?: string;
}
const props = withDefaults(defineProps<Props>(), {
  category: "General",
  categoryId: "",
  mapping: "pathname",
  term: "",
  theme: "preferred_color_scheme",
  reactionsEnabled: "1",
  emitMetadata: "0",
  inputPosition: "bottom",
  lang: "zh-CN",
});

const giscusEl = ref<HTMLElement | null>(null);
let giscusCleanup: (() => void) | null = null;

const colorMode = useColorMode();
const isDark = computed(() =>
  ["one-dark-pro", "dark", "dim", "darken"].includes(String(colorMode.value || "").toLowerCase())
);

const resolvedTheme = computed(() => {
  if (props.theme !== "preferred_color_scheme") return props.theme;
  return isDark.value ? "dark" : "light";
});

onMounted(async () => {
  if (!giscusEl.value) return;
  try {
    const mod = await import("@giscus/vue");
    const { createApp, h } = await import("vue");
    const mount = document.createElement("div");
    giscusEl.value.appendChild(mount);
    const app = createApp({
      render: () =>
        h(mod.Giscus, {
          repo: props.repo,
          repoId: props.repoId,
          category: props.category,
          categoryId: props.categoryId,
          mapping: props.mapping,
          term: props.term || window.location.pathname,
          theme: resolvedTheme.value,
          reactionsEnabled: props.reactionsEnabled,
          emitMetadata: props.emitMetadata,
          inputPosition: props.inputPosition,
          lang: props.lang,
        }),
    });
    app.mount(mount);
    giscusCleanup = () => app.unmount();
  } catch (e) {
    console.warn("[Giscus] load failed:", e);
  }
});

onBeforeUnmount(() => {
  giscusCleanup?.();
  giscusCleanup = null;
});
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl p-lg shadow-sm border border-neutral-border-secondary">
    <h3 class="text-lg font-semibold text-neutral-text-primary mb-md flex items-center gap-2">
      <Icon name="mdi:github" class="w-5 h-5 text-primary-500" />
      评论 · Powered by GitHub
    </h3>
    <div ref="giscusEl" class="min-h-[300px]" />
  </section>
</template>
