<!--
  Disqus — Disqus 评论系统客户端注入
  props: shortname（Disqus 站点标识）、url（当前页完整 URL，可选自动读取）
-->
<script setup lang="ts">
interface Props {
  shortname: string;
  url?: string;
  identifier?: string;
  title?: string;
}
const props = withDefaults(defineProps<Props>(), {
  url: () => (import.meta.client ? window.location.href : ""),
  identifier: () => (import.meta.client ? window.location.pathname : ""),
  title: () => (import.meta.client ? document.title : ""),
});

const disqusEl = ref<HTMLElement | null>(null);
let injected = false;

onMounted(() => {
  if (!disqusEl.value) return;
  if (injected) return;
  injected = true;

  const w = window as any;
  w.disqus_config = function () {
    this.page.url = props.url || window.location.href;
    this.page.identifier = props.identifier || window.location.pathname;
    this.page.title = props.title || document.title;
  };

  const existing = document.getElementById("dsq-embed-scr");
  if (existing) {
    existing.remove();
  }
  const s = document.createElement("script");
  s.id = "dsq-embed-scr";
  s.src = `https://${props.shortname}.disqus.com/embed.js`;
  s.setAttribute("data-timestamp", String(Date.now()));
  (document.head || document.body).appendChild(s);

  const nos = document.createElement("noscript");
  nos.textContent = "Please enable JavaScript to view the comments.";
  disqusEl.value.appendChild(nos);
});
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl p-lg shadow-sm border border-neutral-border-secondary">
    <h3 class="text-lg font-semibold text-neutral-text-primary mb-md flex items-center gap-2">
      <Icon name="material-symbols:chat-bubble-outline-rounded" class="w-5 h-5 text-primary-500" />
      评论 · Disqus
    </h3>
    <div ref="disqusEl" id="disqus_thread" class="min-h-[300px]" />
  </section>
</template>
