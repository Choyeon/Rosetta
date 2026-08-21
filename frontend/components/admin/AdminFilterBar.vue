<script setup lang="ts" generic="TStatus extends string = string">
/* 通用管理列表筛选条：关键字 + 状态 + 日期范围（开始/结束互锁） + 筛选/重置按钮
 *
 * 使用示例：
 *   <AdminFilterBar
 *     v-model:keyword="keyword"
 *     v-model:status="status"
 *     v-model:created-start="startDate"
 *     v-model:created-end="endDate"
 *     :status-options="[{ value: 'all', label: '全部' }, { value: 'pending', label: '待审' }]"
 *     search-placeholder="搜索评论内容或作者..."
 *     @search="reload(1)"
 *     @reset="resetAll"
 *   >
 *     <template #extraFilters>
 *       <Select v-model="authorFilter">…</Select>
 *     </template>
 *   </AdminFilterBar>
 *
 * 日期互锁规则（用户要求：选了 5 号之后，之前的日期在结束日期就无法选中）：
 *   - 结束日期 min = 已选的开始日期（避免 end < start）
 *   - 开始日期 max = 已选的结束日期（避免 start > end）
 *   - 两者的最大可选日期都 ≤ 今天（防止未来时间瞎选）
 *   - start 更新后若 end < start → 自动把 end 拉到 start 的值
 *   - 日期值统一格式 YYYY-MM-DD（字符串），传给后端 created_start / created_end
 */
import { Search, X, Calendar } from '@lucide/vue'
import { Input } from '~~/components/ui/input'
import { Button } from '~~/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '~~/components/ui/select'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from '~~/components/ui/tooltip'

interface StatusOption {
  value: TStatus | 'all'
  label: string
}

const props = withDefaults(defineProps<{
  keyword?: string
  status?: TStatus | 'all'
  statusOptions?: StatusOption[]
  createdStart?: string | null
  createdEnd?: string | null
  searchPlaceholder?: string
  showStatus?: boolean
  showDateRange?: boolean
  loading?: boolean
}>(), {
  keyword: '',
  statusOptions: () => [],
  createdStart: null,
  createdEnd: null,
  searchPlaceholder: '搜索...',
  showStatus: true,
  showDateRange: true,
  loading: false
})

const emit = defineEmits<{
  (e: 'update:keyword', v: string): void
  (e: 'update:status', v: TStatus | 'all'): void
  (e: 'update:createdStart' | 'update:createdEnd', v: string | null): void
  (e: 'search' | 'reset'): void
}>()

// ---- 本地值（允许 enter 键即时触发 search emit，无状态抖动）----
const localKeyword = defineModel<string>('keyword', { default: '' })
const localStatus = defineModel<TStatus | 'all'>('status', { default: 'all' })
const localStart = defineModel<string | null>('createdStart', { default: null })
const localEnd = defineModel<string | null>('createdEnd', { default: null })

const todayStr = computed(() => {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
})

// ---- 属性（给 <input type="date"> 的 min/max，实现日期互锁）----
const startMax = computed(() => localEnd.value || todayStr.value)
const endMin = computed(() => localStart.value)
const endMax = todayStr

watch(localStart, (val) => {
  // 开始日期大于结束日期 → 自动把结束日期拉齐（不允许 end < start）
  if (val && localEnd.value && val > localEnd.value) {
    localEnd.value = val
  }
})

function updateKeyword(value: string | number) {
  localKeyword.value = String(value)
}

function updateStatus(value: string | undefined) {
  localStatus.value = props.statusOptions.find(option => String(option.value) === value)?.value ?? 'all'
}

function updateDate(event: Event, target: 'start' | 'end') {
  const value = (event.target as HTMLInputElement).value
  if (target === 'start') localStart.value = value || null
  else localEnd.value = value || null
}

function doSearch() {
  emit('search')
}

function doReset() {
  localKeyword.value = ''
  localStatus.value = 'all'
  localStart.value = null
  localEnd.value = null
  emit('reset')
}
</script>

<template>
  <div class="card-surface no-glow flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between p-3 md:p-4">
    <!-- 左：关键字 + 状态 + 日期范围 -->
    <div class="flex flex-col sm:flex-row gap-3 flex-1 flex-wrap items-stretch sm:items-center">
      <div class="relative sm:min-w-[240px] flex-1 max-w-md">
        <Search class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <Input
          :model-value="localKeyword"
          class="pl-9 h-9 rounded-[10px]"
          :placeholder="searchPlaceholder"
          @update:model-value="updateKeyword"
          @keyup.enter="doSearch"
        />
      </div>

      <Select
        v-if="showStatus && statusOptions.length > 0"
        :model-value="String(localStatus)"
        @update:model-value="updateStatus"
      >
        <SelectTrigger class="w-[140px] h-9 rounded-[10px]">
          <SelectValue placeholder="状态" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem
            v-for="opt in statusOptions"
            :key="String(opt.value)"
            :value="String(opt.value)"
          >
            {{ opt.label }}
          </SelectItem>
        </SelectContent>
      </Select>

      <div
        v-if="showDateRange"
        class="flex items-center gap-2"
      >
        <Tooltip>
          <TooltipTrigger as-child>
            <div class="flex items-center gap-1 text-muted-foreground">
              <Calendar class="size-4" />
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <p class="text-xs">
              日期范围：结束日期不能早于开始日期
            </p>
          </TooltipContent>
        </Tooltip>
        <input
          type="date"
          class="h-9 rounded-[10px] border border-input bg-background px-3 text-sm text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-0 disabled:cursor-not-allowed disabled:opacity-50"
          :value="localStart ?? ''"
          :max="startMax"
          @change="updateDate($event, 'start')"
        >
        <span class="text-muted-foreground text-sm">至</span>
        <input
          type="date"
          class="h-9 rounded-[10px] border border-input bg-background px-3 text-sm text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-0 disabled:cursor-not-allowed disabled:opacity-50"
          :value="localEnd ?? ''"
          :min="endMin"
          :max="endMax"
          @change="updateDate($event, 'end')"
        >
      </div>

      <slot name="extraFilters" />
    </div>

    <!-- 右：搜索/重置按钮 -->
    <div class="flex items-center gap-2 justify-end">
      <Button
        variant="outline"
        size="sm"
        class="h-9 rounded-[10px]"
        :disabled="loading"
        @click="doReset"
      >
        <X class="size-4 mr-1.5" />
        重置
      </Button>
      <Button
        size="sm"
        class="h-9 rounded-[10px]"
        :disabled="loading"
        @click="doSearch"
      >
        <Search class="size-4 mr-1.5" />
        {{ loading ? '加载中...' : '搜索' }}
      </Button>
    </div>
  </div>
</template>
