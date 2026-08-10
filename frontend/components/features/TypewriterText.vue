<!--
  TypewriterText — 打字机文字效果
  props: texts[]（循环播放的文本数组）、speed（每个字符间隔 ms）、pause（一条结束停顿 ms）、cursor（光标字符）
  通过 ref + setInterval 逐个字符写入；组件卸载时清理定时器
-->
<script setup lang="ts">
interface Props {
  texts: string[];
  speed?: number;
  pause?: number;
  cursor?: string;
  loop?: boolean;
  startDelay?: number;
}
const props = withDefaults(defineProps<Props>(), {
  speed: 80,
  pause: 1400,
  cursor: "|",
  loop: true,
  startDelay: 0,
});

const displayed = ref("");
const showingCursor = ref(true);
let idxText = 0;
let idxChar = 0;
let deleting = false;
let t1: number | null = null;
let t2: number | null = null;

function schedule() {
  const delay = deleting ? Math.max(20, Math.floor(props.speed * 0.55)) : props.speed;
  t1 = window.setTimeout(tick, delay);
}

function tick() {
  if (!props.texts.length) return;
  const cur = props.texts[idxText] || "";
  if (!deleting) {
    idxChar++;
    displayed.value = cur.substring(0, idxChar);
    if (idxChar >= cur.length) {
      deleting = true;
      t1 = window.setTimeout(tick, props.pause);
      return;
    }
  } else {
    idxChar--;
    displayed.value = cur.substring(0, Math.max(0, idxChar));
    if (idxChar <= 0) {
      deleting = false;
      idxText = (idxText + 1) % props.texts.length;
      if (!props.loop && idxText === 0) {
        displayed.value = props.texts[0] || "";
        return;
      }
    }
  }
  schedule();
}

function startCursor() {
  t2 = window.setInterval(() => { showingCursor.value = !showingCursor.value; }, 520);
}

onMounted(() => {
  startCursor();
  t1 = window.setTimeout(schedule, props.startDelay);
});

onBeforeUnmount(() => {
  if (t1 !== null) { clearTimeout(t1); t1 = null; }
  if (t2 !== null) { clearInterval(t2); t2 = null; }
});
</script>

<template>
  <span class="typewriter inline-flex items-baseline">
    <span class="whitespace-pre-wrap">{{ displayed }}</span>
    <span
      class="typewriter-cursor inline-block w-[2px] h-[1em] ml-0.5 align-[-0.1em] bg-current transition-opacity"
      :class="showingCursor ? 'opacity-100' : 'opacity-0'"
      aria-hidden
    >{{ cursor }}</span>
  </span>
</template>
