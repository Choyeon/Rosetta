<!--
  CommentSection — 统一评论系统分发器
  基于 runtimeConfig.public.commentProvider 自动选择组件：
  none | artalk | twikoo | giscus | waline | disqus
  props: postId / title / url — 透传给具体评论组件
-->
<script setup lang="ts">
interface Props {
  postId?: string;
  title?: string;
  url?: string;
}
const props = withDefaults(defineProps<Props>(), {
  postId: () => (import.meta.client ? window.location.pathname : ""),
  title: () => (import.meta.client ? document.title : ""),
  url: () => (import.meta.client ? window.location.href : ""),
});

const runtimeConfig = useRuntimeConfig();
const provider = computed(() =>
  String((runtimeConfig.public as any)?.commentProvider || "none").toLowerCase()
);

const cfg = computed(() => (runtimeConfig.public as any)?.comment || {});

const enabled = computed(() => {
  const pub = runtimeConfig.public as any;
  return pub?.enableComments !== false && provider.value !== "none";
});
</script>

<template>
  <ClientOnly>
    <Artalk
      v-if="enabled && provider === 'artalk'"
      :server="cfg.artalk?.server"
      :site="cfg.artalk?.site || 'Rosetta'"
      :id="postId"
    />
    <Twikoo
      v-else-if="enabled && provider === 'twikoo'"
      :env-id="cfg.twikoo?.envId"
      :region="cfg.twikoo?.region"
    />
    <Giscus
      v-else-if="enabled && provider === 'giscus'"
      :repo="cfg.giscus?.repo"
      :repo-id="cfg.giscus?.repoId"
      :category="cfg.giscus?.category"
      :category-id="cfg.giscus?.categoryId"
      :mapping="cfg.giscus?.mapping || 'pathname'"
      :term="postId"
    />
    <Waline
      v-else-if="enabled && provider === 'waline'"
      :server-u-r-l="cfg.waline?.serverURL"
    />
    <Disqus
      v-else-if="enabled && provider === 'disqus'"
      :shortname="cfg.disqus?.shortname"
      :url="url"
      :identifier="postId"
      :title="title"
    />
    <section
      v-else-if="!enabled"
      class="bg-neutral-bg-container rounded-2xl p-lg shadow-sm border border-neutral-border-secondary text-center text-neutral-text-tertiary text-sm"
    >
      评论功能暂未启用。
    </section>
  </ClientOnly>
</template>
