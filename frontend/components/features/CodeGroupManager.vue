<!--
  CodeGroupManager — 代码 Tab 切换组件
  props: tabs → [{ language, label, code, meta }]
  v-model:activeIndex 控制当前激活；支持一键复制
-->
<script setup lang="ts">
interface CodeTab {
  language: string;
  label?: string;
  code: string;
  meta?: string;
}
interface Props {
  tabs: CodeTab[];
  activeIndex?: number;
  filename?: string;
}
const props = withDefaults(defineProps<Props>(), { activeIndex: 0, filename: "" });
const emit = defineEmits<{ "update:activeIndex": [number] }>();

const idx = ref(props.activeIndex);
watch(() => props.activeIndex, (v) => idx.value = v);
watch(idx, (v) => emit("update:activeIndex", v));

const copied = ref(false);
async function copy() {
  const c = props.tabs[idx.value]?.code || "";
  try {
    await navigator.clipboard.writeText(c);
    copied.value = true;
    setTimeout(() => (copied.value = false), 1600);
  } catch { /* ignore */ }
}

const activeCode = computed(() => props.tabs[idx.value]?.code || "");
const activeLang = computed(() => props.tabs[idx.value]?.language || "");
</script>

<template>
  <section
    class="bg-neutral-bg-container rounded-xl border border-neutral-border-secondary overflow-hidden shadow-sm"
    data-code-group
  >
    <header class="flex items-center justify-between gap-2 px-sm h-9 border-b border-neutral-border-secondary bg-neutral-bg-spot">
      <div class="flex items-center gap-1 overflow-x-auto">
        <button
          v-for="(t, i) in tabs"
          :key="i"
          type="button"
          class="px-2.5 py-1 text-xs rounded-md transition-colors duration-fast whitespace-nowrap"
          :class="i === idx ? 'text-primary-500 bg-primary-500/10 font-medium' : 'text-neutral-text-secondary hover:text-neutral-text-primary hover:bg-neutral-fill-hover'"
          @click="idx = i"
        >
          {{ t.label || t.language }}
        </button>
      </div>
      <div class="flex items-center gap-1 flex-shrink-0">
        <span v-if="filename" class="text-[11px] text-neutral-text-quaternary mr-1 font-mono hidden sm:inline">{{ filename }}</span>
        <span class="text-[11px] text-neutral-text-quaternary mr-1 font-mono uppercase">{{ activeLang }}</span>
        <button
          type="button"
          class="w-7 h-7 rounded-md flex items-center justify-center text-neutral-text-tertiary hover:text-primary-500 hover:bg-neutral-fill-hover transition-colors duration-fast"
          :aria-label="copied ? '已复制' : '复制代码'"
          @click="copy"
        >
          <Icon v-if="copied" name="material-symbols:check-rounded" class="w-4 h-4 text-green-500" />
          <Icon v-else name="material-symbols:content-copy-rounded" class="w-4 h-4" />
        </button>
      </div>
    </header>
    <div class="relative">
      <pre
        class="p-sm overflow-x-auto text-sm leading-relaxed m-0"
      ><code
        class="hljs"
        :class="`language-${activeLang}`"
      >{{ activeCode }}</code></pre>
    </div>
  </section>
</template>
