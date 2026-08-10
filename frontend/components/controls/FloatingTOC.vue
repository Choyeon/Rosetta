<!--
  FloatingTOC — 悬浮目录（固定右侧）
  扫描页面 h2/h3 生成锚点列表；当前滚动位置自动高亮；
  点击锚点平滑滚动到对应标题
-->
<script setup lang="ts">
import { throttle } from "throttle-debounce";

interface TocItem {
  id: string;
  text: string;
  level: 2 | 3;
  offsetTop: number;
}

const items = ref<TocItem[]>([]);
const activeId = ref<string>("");
const visible = ref(false);
let scrollHandler: (() => void) | null = null;

function collect() {
  const headings = document.querySelectorAll<HTMLHeadingElement>("h2[id], h3[id]");
  const list: TocItem[] = [];
  headings.forEach((h) => {
    const id = h.id;
    if (!id) return;
    const text = h.textContent?.trim() || "";
    const level = Number(h.tagName.substring(1)) as 2 | 3;
    const rect = h.getBoundingClientRect();
    list.push({ id, text, level, offsetTop: rect.top + window.scrollY });
  });
  items.value = list;
  visible.value = list.length >= 3;
}

function updateActive() {
  if (!items.value.length) return;
  const scroll = window.scrollY + 120;
  let current = items.value[0].id;
  for (const it of items.value) {
    if (it.offsetTop <= scroll) current = it.id;
  }
  activeId.value = current;
}

onMounted(() => {
  collect();
  updateActive();
  scrollHandler = throttle(120, () => updateActive());
  window.addEventListener("scroll", scrollHandler, { passive: true });
  window.addEventListener("resize", collect);
});

onBeforeUnmount(() => {
  if (scrollHandler) {
    window.removeEventListener("scroll", scrollHandler);
    scrollHandler = null;
  }
  window.removeEventListener("resize", collect);
});

function jumpTo(id: string) {
  const el = document.getElementById(id);
  if (!el) return;
  const top = el.getBoundingClientRect().top + window.scrollY - 88;
  window.scrollTo({ top, behavior: "smooth" });
  activeId.value = id;
}
</script>

<template>
  <ClientOnly>
    <Transition name="slide">
      <aside
        v-show="visible"
        class="hidden xl:block fixed right-6 top-32 z-10 w-56 max-h-[calc(100vh-200px)] overflow-y-auto bg-neutral-bg-container/80 backdrop-blur-sm rounded-xl p-md border border-neutral-border-secondary shadow-sm"
        aria-label="页面目录"
      >
        <h4 class="text-xs font-semibold text-neutral-text-tertiary uppercase tracking-wide mb-sm flex items-center gap-1">
          <Icon name="material-symbols:list-alt-rounded" class="w-3.5 h-3.5" />
          目录
        </h4>
        <ul class="space-y-1 text-sm">
          <li v-for="it in items" :key="it.id">
            <button
              type="button"
              class="w-full text-left px-2 py-1.5 rounded-md transition-colors duration-fast line-clamp-2"
              :class="[
                activeId === it.id
                  ? 'text-primary-500 bg-primary-500/10 font-medium'
                  : 'text-neutral-text-secondary hover:text-neutral-text-primary hover:bg-neutral-fill-hover',
                it.level === 3 ? 'pl-5 text-xs' : '',
              ]"
              @click="jumpTo(it.id)"
            >{{ it.text }}</button>
          </li>
        </ul>
      </aside>
    </Transition>
  </ClientOnly>
</template>

<style scoped>
.slide-enter-active, .slide-leave-active { transition: opacity 200ms ease, transform 200ms ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateX(12px); }
</style>
