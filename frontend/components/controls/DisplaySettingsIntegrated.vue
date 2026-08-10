<!--
  DisplaySettingsIntegrated — 阅读显示设置：字号 / 行距 / 紧凑模式
  三档：小 / 中(默认) / 大；值持久化到 js-cookie (rosetta-display)
  应用时在 <html data-read-font-size / data-read-line-height / data-read-compact>
-->
<script setup lang="ts">
import Cookies from "js-cookie";

const COOKIE_KEY = "rosetta-display";
const fontSizes = ["sm", "md", "lg"] as const;
const lineHeights = ["tight", "normal", "relaxed"] as const;
type Fs = typeof fontSizes[number];
type Lh = typeof lineHeights[number];

const fontSize = ref<Fs>("md");
const lineHeight = ref<Lh>("normal");
const compact = ref(false);

function load() {
  const raw = Cookies.get(COOKIE_KEY);
  if (!raw) return;
  try {
    const j = JSON.parse(raw);
    if (fontSizes.includes(j.fontSize)) fontSize.value = j.fontSize;
    if (lineHeights.includes(j.lineHeight)) lineHeight.value = j.lineHeight;
    compact.value = !!j.compact;
  } catch { /* ignore */ }
}
function persist() {
  Cookies.set(COOKIE_KEY, JSON.stringify({
    fontSize: fontSize.value,
    lineHeight: lineHeight.value,
    compact: compact.value,
  }), { expires: 365, path: "/" });
}
function apply() {
  const r = document.documentElement;
  r.setAttribute("data-read-font-size", fontSize.value);
  r.setAttribute("data-read-line-height", lineHeight.value);
  r.setAttribute("data-read-compact", String(compact.value));
  r.style.setProperty("--read-font-scale", fontSize.value === "sm" ? "0.92" : fontSize.value === "lg" ? "1.12" : "1");
  r.style.setProperty("--read-line-scale", lineHeight.value === "tight" ? "1.45" : lineHeight.value === "relaxed" ? "1.9" : "1.7");
  r.style.setProperty("--read-gap", compact.value ? "0.6" : "1");
}
function reset() {
  fontSize.value = "md";
  lineHeight.value = "normal";
  compact.value = false;
  persist();
  apply();
}
function toggleCompact() { compact.value = !compact.value; persist(); apply(); }

onMounted(() => {
  load();
  apply();
  watch([fontSize, lineHeight], () => { persist(); apply(); });
});
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl p-md shadow-sm border border-neutral-border-secondary">
    <h4 class="text-sm font-semibold text-neutral-text-primary mb-sm flex items-center gap-1.5">
      <Icon name="material-symbols:display-settings-rounded" class="w-4 h-4 text-primary-500" />
      阅读显示
    </h4>
    <div class="space-y-sm">
      <div class="flex items-center justify-between gap-2">
        <span class="text-xs text-neutral-text-secondary">字号</span>
        <div class="inline-flex items-center rounded-lg border border-neutral-border-secondary overflow-hidden">
          <button
            v-for="f in fontSizes" :key="f"
            type="button"
            class="px-2.5 py-1 text-xs transition-colors duration-fast"
            :class="fontSize === f ? 'bg-primary-500 text-white' : 'text-neutral-text-secondary hover:bg-neutral-fill-hover'"
            @click="fontSize = f"
          >
            {{ f === "sm" ? "A-" : f === "lg" ? "A+" : "A" }}
          </button>
        </div>
      </div>
      <div class="flex items-center justify-between gap-2">
        <span class="text-xs text-neutral-text-secondary">行距</span>
        <div class="inline-flex items-center rounded-lg border border-neutral-border-secondary overflow-hidden">
          <button
            v-for="lh in lineHeights" :key="lh"
            type="button"
            class="px-2.5 py-1 text-xs transition-colors duration-fast"
            :class="lineHeight === lh ? 'bg-primary-500 text-white' : 'text-neutral-text-secondary hover:bg-neutral-fill-hover'"
            @click="lineHeight = lh"
          >
            {{ lh === "tight" ? "紧" : lh === "relaxed" ? "松" : "中" }}
          </button>
        </div>
      </div>
      <div class="flex items-center justify-between gap-2">
        <span class="text-xs text-neutral-text-secondary">紧凑模式</span>
        <button
          type="button"
          class="relative w-10 h-5 rounded-full transition-colors duration-fast"
          :class="compact ? 'bg-primary-500' : 'bg-neutral-fill-hover'"
          @click="toggleCompact"
          :aria-pressed="compact"
        >
          <span
            class="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all duration-fast"
            :class="compact ? 'left-[22px]' : 'left-0.5'"
          />
        </button>
      </div>
      <div class="pt-xs border-t border-neutral-border-secondary">
        <button
          type="button"
          class="w-full text-xs text-neutral-text-tertiary hover:text-primary-500 transition-colors"
          @click="reset"
        >恢复默认</button>
      </div>
    </div>
  </section>
</template>
