<!--
  License — 侧边栏文章/内容版权声明（CC BY-NC-SA 等）
  props: type / name / url
-->
<script setup lang="ts">
interface Props {
  type?: string;
  name?: string;
  url?: string;
  icon?: string;
}
withDefaults(defineProps<Props>(), {
  type: "CC BY-NC-SA 4.0",
  name: "知识共享 署名-非商业性使用-相同方式共享",
  url: "https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hans",
  icon: "material-symbols:copyright-rounded",
});
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl p-md shadow-sm border border-neutral-border-secondary">
    <header class="flex items-center gap-1.5 mb-xs">
      <Icon :name="icon" class="w-4 h-4 text-primary-500" />
      <h3 class="text-sm font-semibold text-neutral-text-primary">版权声明</h3>
    </header>
    <a
      :href="url"
      target="_blank"
      rel="noopener nofollow"
      class="block rounded-xl border border-neutral-border-secondary p-sm hover:border-primary-500/50 hover:bg-primary-500/[0.03] transition-all duration-fast"
    >
      <div class="flex items-center gap-sm">
        <div class="flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br from-primary-500 to-rosetta-nebula text-white flex items-center justify-center shadow-sm">
          <Icon name="fa7-solid:scale-balanced" class="w-4 h-4" />
        </div>
        <div class="min-w-0 flex-1">
          <div class="text-sm font-semibold text-neutral-text-primary line-clamp-1">{{ type }}</div>
          <div class="text-[11px] text-neutral-text-tertiary line-clamp-2 leading-snug">{{ name }}</div>
        </div>
      </div>
      <div class="mt-xs flex items-center gap-1 text-[10px] text-neutral-text-quaternary">
        <Icon name="material-symbols:open-in-new-rounded" class="w-3 h-3" />
        点击查看完整协议
      </div>
    </a>
    <p class="mt-xs text-[11px] text-neutral-text-tertiary leading-relaxed">
      除特别声明外，本站原创内容均遵循上述协议。转载请保留署名，禁止商用，衍生作品请使用相同协议。
    </p>
  </section>
</template>
