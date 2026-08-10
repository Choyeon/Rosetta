<!--
  Calendar — 侧边栏日历组件
  显示当月日历；可切换月份；标记发布文章日期（props: postsDates[]）
  今日高亮 + 文章计数提示
-->
<script setup lang="ts">
interface Props {
  postsDates?: string[];
}
withDefaults(defineProps<Props>(), { postsDates: () => [] });

const cursor = ref(dayjs());
const today = dayjs().format("YYYY-MM-DD");

const yearMonthLabel = computed(() => cursor.value.format("YYYY 年 M 月"));

const cells = computed(() => {
  const start = cursor.value.startOf("month").startOf("week");
  const end = cursor.value.endOf("month").endOf("week");
  const days: {
    date: string; label: string; inMonth: boolean;
    isToday: boolean; count: number; weekday: number;
  }[] = [];
  const set = new Set((props.postsDates || []).map((s) => s.slice(0, 10)));
  for (let d = start; d.isBefore(end) || d.isSame(end, "day"); d = d.add(1, "day")) {
    const ds = d.format("YYYY-MM-DD");
    days.push({
      date: ds,
      label: d.format("D"),
      inMonth: d.month() === cursor.value.month(),
      isToday: ds === today,
      count: set.has(ds) ? 1 : 0,
      weekday: d.day(),
    });
  }
  return days;
});

const weekdayLabels = ["日", "一", "二", "三", "四", "五", "六"];

function prevMonth() { cursor.value = cursor.value.subtract(1, "month"); }
function nextMonth() { cursor.value = cursor.value.add(1, "month"); }
function toToday() { cursor.value = dayjs(); }
</script>

<template>
  <section class="bg-neutral-bg-container rounded-2xl p-md shadow-sm border border-neutral-border-secondary">
    <header class="flex items-center justify-between mb-sm">
      <h3 class="text-sm font-semibold text-neutral-text-primary flex items-center gap-1.5">
        <Icon name="material-symbols:calendar-month-rounded" class="w-4 h-4 text-primary-500" />
        日历
      </h3>
      <div class="flex items-center gap-0.5">
        <button type="button" class="w-6 h-6 rounded-md text-neutral-text-tertiary hover:bg-neutral-fill-hover hover:text-primary-500 transition-colors flex items-center justify-center" @click="prevMonth" aria-label="上个月">
          <Icon name="material-symbols:chevron-left-rounded" class="w-3.5 h-3.5" />
        </button>
        <button type="button" class="px-1.5 py-0.5 rounded-md text-xs text-neutral-text-secondary hover:bg-neutral-fill-hover hover:text-primary-500 transition-colors" @click="toToday" aria-label="今天">
          {{ yearMonthLabel }}
        </button>
        <button type="button" class="w-6 h-6 rounded-md text-neutral-text-tertiary hover:bg-neutral-fill-hover hover:text-primary-500 transition-colors flex items-center justify-center" @click="nextMonth" aria-label="下个月">
          <Icon name="material-symbols:chevron-right-rounded" class="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
    <div class="grid grid-cols-7 gap-1 text-center">
      <div v-for="(w, i) in weekdayLabels" :key="w" class="text-[10px] font-semibold py-xs text-neutral-text-quaternary" :class="i === 0 || i === 6 ? 'text-rose-400/70' : ''">
        {{ w }}
      </div>
      <button
        v-for="c in cells"
        :key="c.date"
        type="button"
        class="aspect-square text-[11px] rounded-md transition-all duration-fast flex flex-col items-center justify-center"
        :class="[
          !c.inMonth ? 'text-neutral-text-quaternary/40' : 'text-neutral-text-secondary',
          c.isToday ? 'bg-primary-500 text-white font-semibold shadow-sm' : '',
          c.count && !c.isToday ? 'relative text-primary-500 font-medium hover:bg-primary-500/10' : '',
          !c.isToday && !c.count && c.inMonth ? 'hover:bg-neutral-fill-hover' : '',
          (c.weekday === 0 || c.weekday === 6) && !c.isToday ? 'text-rose-400/80' : '',
        ]"
      >
        {{ c.label }}
        <span
          v-if="c.count && !c.isToday"
          class="absolute bottom-0.5 w-1 h-1 rounded-full bg-primary-500"
          aria-label="有文章"
        />
      </button>
    </div>
  </section>
</template>
