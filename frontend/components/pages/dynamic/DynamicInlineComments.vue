<!--
  DynamicInlineComments — 动态内嵌评论区（可折叠）
  默认折叠，点击"评论"按钮展开；模拟列表 + 输入框
-->
<script setup lang="ts">
const open = ref(false);
const text = ref("");
const sampleList = ref([
  { id: 1, name: "游客", avatar: null, text: "好看！顶一下~", time: "3小时前" },
  { id: 2, name: "Miku Fan", avatar: null, text: "3939！", time: "1天前" },
]);
function submit() {
  const v = text.value.trim();
  if (!v) return;
  sampleList.value.unshift({ id: Date.now(), name: "我", avatar: null, text: v, time: "刚刚" });
  text.value = "";
}
</script>

<template>
  <div>
    <Transition name="expand">
      <div v-if="open" class="px-md py-sm bg-neutral-bg-spot/60 border-t border-neutral-border-secondary space-y-sm">
        <form class="flex items-center gap-2" @submit.prevent="submit">
          <input
            v-model="text"
            type="text"
            placeholder="友善评论，理性讨论…"
            class="flex-1 px-3 py-1.5 rounded-full text-xs border border-neutral-border-secondary bg-neutral-bg-container focus:outline-none focus:ring-2 ring-primary-500/30 focus:border-primary-500 transition"
          />
          <button
            type="submit"
            class="px-3 py-1.5 rounded-full bg-primary-500 text-white text-xs font-medium hover:bg-primary-400 transition-colors"
          >发送</button>
        </form>
        <ul v-if="sampleList.length" class="space-y-xs">
          <li
            v-for="c in sampleList" :key="c.id"
            class="flex gap-xs items-start text-xs"
          >
            <div class="w-7 h-7 rounded-full bg-gradient-to-br from-primary-300 to-rosetta-nebula text-white flex items-center justify-center text-[10px] font-semibold flex-shrink-0">
              {{ (c.name || "?").slice(0, 1) }}
            </div>
            <div class="flex-1 min-w-0 rounded-lg bg-neutral-bg-container border border-neutral-border-secondary px-xs py-xs">
              <div class="flex items-baseline justify-between gap-2">
                <span class="font-semibold text-neutral-text-primary">{{ c.name }}</span>
                <span class="text-[10px] text-neutral-text-quaternary">{{ c.time }}</span>
              </div>
              <div class="mt-0.5 text-neutral-text-secondary break-words">{{ c.text }}</div>
            </div>
          </li>
        </ul>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.expand-enter-active, .expand-leave-active { transition: all 180ms ease; overflow: hidden; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; padding-top: 0; padding-bottom: 0; margin-top: 0; }
.expand-enter-to, .expand-leave-from { opacity: 1; max-height: 500px; }
</style>
