<!--
  Search — 全站搜索（Fuse.js 模糊搜索）
  数据源：@nuxt/content 的 queryContent('posts')；
  快捷键：Ctrl+K (⌘+K) 聚焦 / 打开；Esc 关闭；
  结果支持标题/描述/标签/分类匹配，点击跳转
-->
<script setup lang="ts">
import Fuse from "fuse.js";

interface SearchHit {
  _path: string;
  title: string;
  description?: string;
  tags?: string[];
  category?: string;
  image?: string;
}

const open = ref(false);
const q = ref("");
const results = ref<SearchHit[]>([]);
const loading = ref(false);
const inputRef = ref<HTMLInputElement | null>(null);
const selected = ref(-1);

let fuse: Fuse<SearchHit> | null = null;
const postsCache = ref<SearchHit[]>([]);

async function loadPosts() {
  if (postsCache.value.length) return postsCache.value;
  loading.value = true;
  try {
    const data = await queryContent<SearchHit>("/posts").where({ draft: { $ne: true } }).find();
    postsCache.value = data.map((d) => ({
      _path: d._path,
      title: (d as any).title || d._path,
      description: (d as any).description || "",
      tags: (d as any).tags || [],
      category: (d as any).category || "",
      image: (d as any).image || "",
    }));
    return postsCache.value;
  } finally {
    loading.value = false;
  }
}

function buildFuse(list: SearchHit[]) {
  return new Fuse(list, {
    keys: [
      { name: "title", weight: 0.5 },
      { name: "description", weight: 0.2 },
      { name: "tags", weight: 0.2 },
      { name: "category", weight: 0.1 },
    ],
    threshold: 0.35,
    includeScore: false,
    ignoreLocation: true,
  });
}

async function ensureFuse() {
  if (fuse) return fuse;
  const list = await loadPosts();
  fuse = buildFuse(list);
  return fuse;
}

watch(q, async (v) => {
  selected.value = -1;
  const kw = v.trim();
  if (!kw) {
    results.value = postsCache.value.slice(0, 5);
    return;
  }
  const f = await ensureFuse();
  results.value = f.search(kw).slice(0, 10).map((r) => r.item);
});

function openDialog() {
  open.value = true;
  results.value = postsCache.value.slice(0, 5);
  nextTick(() => {
    inputRef.value?.focus();
    inputRef.value?.select();
  });
}
function closeDialog() {
  open.value = false;
  q.value = "";
  selected.value = -1;
}

function go(i: number) {
  const hit = results.value[i];
  if (!hit) return;
  closeDialog();
  navigateTo(hit._path);
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === "ArrowDown") {
    e.preventDefault();
    selected.value = Math.min(results.value.length - 1, selected.value + 1);
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    selected.value = Math.max(-1, selected.value - 1);
  } else if (e.key === "Enter") {
    e.preventDefault();
    const i = selected.value >= 0 ? selected.value : 0;
    go(i);
  }
}

onMounted(() => {
  const onKey = (e: KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      open.value ? closeDialog() : openDialog();
    } else if (e.key === "Escape" && open.value) {
      closeDialog();
    }
  };
  window.addEventListener("keydown", onKey);
  onBeforeUnmount(() => window.removeEventListener("keydown", onKey));
  // 预加载
  loadPosts().then(() => { fuse = buildFuse(postsCache.value); });
});
</script>

<template>
  <div>
    <button
      type="button"
      class="w-9 h-9 rounded-md flex items-center justify-center text-neutral-text-secondary hover:bg-neutral-fill-hover hover:text-primary-500 transition-colors duration-fast ease-out relative"
      aria-label="搜索内容 Ctrl+K"
      @click="openDialog"
    >
      <Icon name="material-symbols:search-rounded" class="w-5 h-5" />
      <kbd class="absolute -right-0.5 -bottom-0.5 text-[9px] font-mono text-neutral-text-quaternary bg-neutral-fill-hover px-1 rounded border border-neutral-border-secondary">⌘K</kbd>
    </button>

    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="open"
          class="fixed inset-0 z-modal flex items-start justify-center pt-24 sm:pt-32 px-4"
          @click.self="closeDialog"
        >
          <div class="fixed inset-0 bg-black/40 backdrop-blur-sm" @click="closeDialog" />
          <div class="relative w-full max-w-xl bg-neutral-bg-container rounded-2xl shadow-2xl border border-neutral-border-secondary overflow-hidden">
            <div class="flex items-center gap-2 px-md h-14 border-b border-neutral-border-secondary">
              <Icon name="material-symbols:search-rounded" class="w-5 h-5 text-neutral-text-tertiary" />
              <input
                ref="inputRef"
                v-model="q"
                type="search"
                placeholder="输入关键字搜索文章、标签、分类…"
                class="flex-1 bg-transparent text-sm text-neutral-text-primary placeholder:text-neutral-text-quaternary outline-none"
                @keydown="onKeydown"
              />
              <kbd class="hidden sm:inline-flex text-[10px] font-mono text-neutral-text-quaternary bg-neutral-fill-hover px-1.5 py-0.5 rounded border border-neutral-border-secondary">ESC</kbd>
            </div>
            <div class="max-h-[50vh] overflow-y-auto">
              <div v-if="loading" class="p-lg text-center text-sm text-neutral-text-tertiary">加载索引中…</div>
              <ul v-else-if="results.length" class="py-1">
                <li v-for="(hit, idx) in results" :key="hit._path">
                  <button
                    type="button"
                    class="w-full flex items-start gap-3 px-md py-sm text-left transition-colors duration-fast"
                    :class="idx === selected ? 'bg-primary-500/10' : 'hover:bg-neutral-fill-hover'"
                    @click="go(idx)"
                    @mouseenter="selected = idx"
                  >
                    <div class="mt-1 w-8 h-8 rounded-lg bg-primary-500/10 text-primary-500 flex items-center justify-center flex-shrink-0">
                      <Icon name="material-symbols:description-rounded" class="w-4 h-4" />
                    </div>
                    <div class="min-w-0 flex-1">
                      <div class="text-sm font-medium text-neutral-text-primary line-clamp-1">{{ hit.title }}</div>
                      <div class="mt-0.5 text-xs text-neutral-text-tertiary line-clamp-1">{{ hit.description || hit._path }}</div>
                      <div v-if="hit.tags?.length" class="mt-xs flex flex-wrap gap-1">
                        <span v-for="t in hit.tags.slice(0, 3)" :key="t" class="text-[10px] px-1.5 py-0.5 rounded-full bg-neutral-fill-hover text-neutral-text-tertiary">#{{ t }}</span>
                      </div>
                    </div>
                  </button>
                </li>
              </ul>
              <div v-else class="p-lg text-center text-sm text-neutral-text-tertiary">
                <Icon name="material-symbols:search-off-rounded" class="w-8 h-8 mx-auto mb-sm opacity-50" />
                {{ q ? '没有找到匹配的结果' : '输入关键字开始搜索' }}
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 180ms ease; }
.modal-enter-active > div:last-child, .modal-leave-active > div:last-child { transition: transform 180ms ease, opacity 180ms ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from > div:last-child, .modal-leave-to > div:last-child { opacity: 0; transform: translateY(-12px) scale(0.98); }
</style>
