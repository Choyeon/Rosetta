<!--
  FilterControls — 番剧筛选控件（状态 / 年份 / 类型 / 排序）
  v-model:status / year / type / sort
-->
<script setup lang="ts">
type Status = "all" | "watching" | "completed" | "plan";
type SortBy = "time" | "score" | "name";
interface Props {
  status?: Status;
  year?: string;
  type?: "ALL" | "TV" | "MOVIE" | "OVA" | "WEB";
  sort?: SortBy;
  years?: string[];
}
withDefaults(defineProps<Props>(), {
  status: "all",
  year: "all",
  type: "ALL",
  sort: "time",
  years: () => ["2026", "2025", "2024", "2023", "2022"],
});
const emit = defineEmits<{
  "update:status": [Status]; "update:year": [string];
  "update:type": [Props["type"]]; "update:sort": [SortBy];
}>();

const statuses: { v: Status; l: string; i: string }[] = [
  { v: "all", l: "全部", i: "material-symbols:grid-view-rounded" },
  { v: "watching", l: "追番中", i: "material-symbols:play-circle-rounded" },
  { v: "completed", l: "已看完", i: "material-symbols:check-circle-rounded" },
  { v: "plan", l: "想看", i: "material-symbols:bookmark-rounded" },
];
const typeList = ["ALL", "TV", "MOVIE", "OVA", "WEB"] as const;
const sortList: { v: SortBy; l: string }[] = [
  { v: "time", l: "时间" }, { v: "score", l: "评分" }, { v: "name", l: "名称" },
];
</script>

<template>
  <div class="bg-neutral-bg-container rounded-xl border border-neutral-border-secondary p-sm sm:p-md space-y-sm shadow-sm">
    <div class="flex flex-wrap gap-1 sm:gap-2">
      <button
        v-for="s in statuses"
        :key="s.v"
        type="button"
        class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-fast"
        :class="status === s.v ? 'bg-primary-500 text-white shadow-sm' : 'text-neutral-text-secondary hover:text-neutral-text-primary hover:bg-neutral-fill-hover border border-transparent hover:border-neutral-border-secondary'"
        @click="emit('update:status', s.v)"
      >
        <Icon :name="s.i" class="w-3.5 h-3.5" />
        {{ s.l }}
      </button>
    </div>
    <div class="flex flex-wrap items-center gap-2 text-xs">
      <div class="flex items-center gap-1 text-neutral-text-tertiary">
        <Icon name="material-symbols:calendar-month-rounded" class="w-3.5 h-3.5" />
        年份
      </div>
      <div class="flex flex-wrap gap-1">
        <button
          type="button"
          class="px-2 py-1 rounded-md transition-colors"
          :class="year === 'all' ? 'text-primary-500 bg-primary-500/10 font-medium' : 'text-neutral-text-secondary hover:bg-neutral-fill-hover'"
          @click="emit('update:year', 'all')"
        >全部</button>
        <button
          v-for="y in years" :key="y"
          type="button"
          class="px-2 py-1 rounded-md transition-colors"
          :class="year === y ? 'text-primary-500 bg-primary-500/10 font-medium' : 'text-neutral-text-secondary hover:bg-neutral-fill-hover'"
          @click="emit('update:year', y)"
        >{{ y }}</button>
      </div>
      <span class="w-px h-4 bg-neutral-border-secondary mx-1 hidden sm:block" />
      <div class="flex items-center gap-1 text-neutral-text-tertiary">
        <Icon name="material-symbols:filter-list-rounded" class="w-3.5 h-3.5" />
        类型
      </div>
      <div class="flex flex-wrap gap-1">
        <button
          v-for="t in typeList" :key="t"
          type="button"
          class="px-2 py-1 rounded-md transition-colors"
          :class="type === t ? 'text-primary-500 bg-primary-500/10 font-medium' : 'text-neutral-text-secondary hover:bg-neutral-fill-hover'"
          @click="emit('update:type', t)"
        >{{ t === "ALL" ? "全部" : t }}</button>
      </div>
      <span class="flex-1" />
      <div class="flex items-center gap-1">
        <span class="text-neutral-text-tertiary text-xs">排序</span>
        <select
          :value="sort"
          class="text-xs rounded-md border border-neutral-border-secondary bg-neutral-bg-container text-neutral-text-secondary px-2 py-1 focus:outline-none focus:ring-1 ring-primary-500/30"
          @change="emit('update:sort', ($event.target as HTMLSelectElement).value as SortBy)"
        >
          <option v-for="s in sortList" :key="s.v" :value="s.v">{{ s.l }}</option>
        </select>
      </div>
    </div>
  </div>
</template>
