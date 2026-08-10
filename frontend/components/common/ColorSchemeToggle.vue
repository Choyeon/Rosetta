<!--
  ColorSchemeToggle — 对应 Astro src/components/ColorSchemeToggle.astro
  依赖：@nuxtjs/color-mode → useColorMode composable
  行为：点击切换 one-light / one-dark-pro；
        data-theme 同步到 <html data-theme>（main.css 已做 [data-theme="one-dark-pro"] 切换）
-->
<script setup lang="ts">
const colorMode = useColorMode();

const isDark = computed(() =>
  ["one-dark-pro", "dark", "dim", "darken"].includes(String(colorMode.value || "").toLowerCase())
);

function toggle() {
  const next = isDark.value ? "one-light" : "one-dark-pro";
  colorMode.preference = next;
  // 同步到 <html data-theme> —— 因为 useColorMode 默认操作 class，但我们用 data-theme
  if (import.meta.client) {
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem("rosetta-color-mode", next === "one-light" ? "light" : "dark"); } catch { /* ignore */ }
  }
}

// 初始同步（SSR 渲染 HTML 时，app.vue 里有 FOUC 脚本；CS 下这里再兜底一次）
onMounted(() => {
  const cur = isDark.value ? "one-dark-pro" : "one-light";
  document.documentElement.setAttribute("data-theme", cur);
});
watch(
  () => colorMode.value,
  (v) => {
    const cur = String(v || "").toLowerCase();
    const theme = ["dark", "one-dark-pro"].includes(cur) ? "one-dark-pro" : "one-light";
    document.documentElement?.setAttribute("data-theme", theme);
  },
  { immediate: import.meta.client }
);
</script>

<template>
  <button
    type="button"
    class="w-9 h-9 rounded-md flex items-center justify-center text-neutral-text-secondary hover:bg-neutral-fill-hover hover:text-primary-500 transition-colors duration-fast ease-out"
    :aria-label="isDark ? '切换为浅色主题' : '切换为深色主题'"
    @click="toggle"
  >
    <!-- Sun（浅色模式下图标=月亮，待切换→深色；Dark 模式下图标=太阳，待切换→浅色。逻辑反着更直观） -->
    <svg
      v-if="isDark"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      class="w-5 h-5"
      aria-hidden
    >
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
    <svg
      v-else
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      class="w-5 h-5"
      aria-hidden
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  </button>
</template>
