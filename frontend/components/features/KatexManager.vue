<!--
  KatexManager — 全局 KaTeX 公式渲染管理器
  监听 DOM（或 onMounted + watch route）检测 .katex / .katex-inline / .katex-block 元素
  调用 katex.render() 进行渲染；displayMode 自动判断
-->
<script setup lang="ts">
import katex from "katex";
import "katex/dist/katex.min.css";

const SELECTORS = [
  ".katex",
  ".katex-inline",
  ".katex-block",
  "[data-katex]",
  "script[type='math/tex']",
  "script[type='math/tex; mode=display']",
];

function renderAll(root: ParentNode = document) {
  root.querySelectorAll<HTMLElement>(SELECTORS.join(",")).forEach((el) => {
    if (el.dataset.katexRendered === "1") return;
    try {
      let tex = "";
      let displayMode = false;
      const tag = el.tagName.toLowerCase();
      if (tag === "script") {
        tex = el.textContent || "";
        displayMode = (el.getAttribute("type") || "").includes("mode=display");
      } else {
        tex = el.dataset.katex || el.textContent || "";
        displayMode = el.classList.contains("katex-block") || el.classList.contains("katex") && el.tagName === "DIV";
      }
      if (!tex) return;
      const host = document.createElement("span");
      katex.render(tex, host, {
        throwOnError: false,
        displayMode,
        output: "html",
        strict: false,
        trust: true,
      });
      if (tag === "script") {
        const wrap = document.createElement(displayMode ? "div" : "span");
        wrap.className = "katex-rendered";
        wrap.innerHTML = host.innerHTML;
        el.replaceWith(wrap);
      } else {
        el.innerHTML = host.innerHTML;
        el.dataset.katexRendered = "1";
      }
    } catch (e) {
      el.dataset.katexRendered = "1";
    }
  });
}

let observer: MutationObserver | null = null;
let moTimer: number | null = null;

function moSchedule() {
  if (moTimer !== null) return;
  moTimer = window.setTimeout(() => {
    moTimer = null;
    renderAll();
  }, 120);
}

onMounted(() => {
  renderAll();
  try {
    observer = new MutationObserver((mutations) => {
      let need = false;
      for (const m of mutations) {
        if (m.addedNodes && m.addedNodes.length) { need = true; break; }
      }
      if (need) moSchedule();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  } catch { /* ignore */ }

  const stop = watch(
    () => useRoute().fullPath,
    () => {
      nextTick(() => {
        setTimeout(() => renderAll(), 150);
      });
    }
  );
  onBeforeUnmount(stop);
});

onBeforeUnmount(() => {
  observer?.disconnect();
  observer = null;
  if (moTimer !== null) { clearTimeout(moTimer); moTimer = null; }
});
</script>

<template>
  <div class="hidden" aria-hidden data-katex-manager />
</template>
