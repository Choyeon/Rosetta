<!--
  SiteInfo — 侧边栏站点信息（运行天数/上线日期/作者/GitHub 等）
  props: { siteName, foundedAt, ownerName, location, motto }
-->
<script setup lang="ts">
interface Props {
  siteName?: string;
  foundedAt?: string;
  ownerName?: string;
  location?: string;
  motto?: string;
}
// 仅用字面量占位 — 动态兜底使用下方 useRuntimeConfig() 在 computed 内合并
const props = withDefaults(defineProps<Props>(), {
  siteName: "Rosetta",
  foundedAt: "2023-05-20",
  ownerName: "Choyu Choyeon",
  location: "China",
  motto: "以代码与文字记录世界",
});
const runtimeConfig = useRuntimeConfig();
const siteName$ = computed(() => props.siteName || runtimeConfig.public?.siteName || "Rosetta");
const foundedAt$ = computed(() => props.foundedAt || "2023-05-20");
const daysRunning = computed(() => Math.max(1, dayjs().diff(dayjs(foundedAt$.value), "day")));
const now = new Date();
const buildYear = now.getFullYear();
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl p-md shadow-sm border border-neutral-border-secondary">
    <header class="flex items-center gap-1.5 mb-sm">
      <Icon name="material-symbols:info-rounded" class="w-4 h-4 text-primary-500" />
      <h3 class="text-sm font-semibold text-neutral-text-primary">关于本站</h3>
    </header>
    <ul class="space-y-xs text-xs text-neutral-text-secondary">
      <li class="flex items-start gap-2">
        <Icon name="material-symbols:domain-rounded" class="w-3.5 h-3.5 mt-0.5 text-neutral-text-tertiary flex-shrink-0" />
        <span class="line-clamp-1"><b class="text-neutral-text-primary font-medium">{{ siteName$ }}</b></span>
      </li>
      <li class="flex items-center gap-2">
        <Icon name="material-symbols:schedule-rounded" class="w-3.5 h-3.5 text-neutral-text-tertiary flex-shrink-0" />
        <span>已运行 <b class="text-primary-500 font-semibold">{{ daysRunning }}</b> 天</span>
      </li>
      <li class="flex items-center gap-2">
        <Icon name="material-symbols:celebration-rounded" class="w-3.5 h-3.5 text-neutral-text-tertiary flex-shrink-0" />
        <span>创建于 {{ dayjs(foundedAt).format("YYYY-MM-DD") }}</span>
      </li>
      <li class="flex items-start gap-2">
        <Icon name="material-symbols:person-rounded" class="w-3.5 h-3.5 mt-0.5 text-neutral-text-tertiary flex-shrink-0" />
        <span class="line-clamp-1">{{ ownerName }}</span>
      </li>
      <li class="flex items-center gap-2">
        <Icon name="material-symbols:location-on-rounded" class="w-3.5 h-3.5 text-neutral-text-tertiary flex-shrink-0" />
        <span>{{ location }}</span>
      </li>
      <li class="flex items-start gap-2">
        <Icon name="material-symbols:format-quote-rounded" class="w-3.5 h-3.5 mt-0.5 text-neutral-text-tertiary flex-shrink-0" />
        <span class="italic line-clamp-2">{{ motto }}</span>
      </li>
    </ul>
    <footer class="mt-xs pt-xs border-t border-neutral-border-secondary text-[10px] text-neutral-text-quaternary flex items-center justify-between">
      <span>© {{ buildYear }} {{ siteName }}</span>
      <NuxtLink to="/about" class="hover:text-primary-500 transition-colors">关于 · 友链</NuxtLink>
    </footer>
  </section>
</template>
