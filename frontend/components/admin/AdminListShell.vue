<script setup lang="ts">
/* 分页壳 + 空态：包装「加载骨架 / 空列表提示 / 分页控件」三段，所有列表页统一使用
 *
 * 使用：
 *   <AdminListShell
 *     :loading="loading"
 *     :total="paged.total"
 *     :page="paged.page"
 *     :page-size="paged.page_size"
 *     :total-pages="paged.total_pages"
 *     empty-title="暂无评论"
 *     empty-desc="当前筛选条件下没有数据"
 *     @update:page="(p) => { page = p; reload() }"
 *   >
 *     <template #default>
 *       <div v-for="row in rows" ... />
 *     </template>
 *   </AdminListShell>
 */
import { Skeleton } from '~~/components/ui/skeleton'
import {
  Pagination,
  PaginationContent,
  PaginationItem
} from '~~/components/ui/pagination'
import { Button } from '~~/components/ui/button'
import {
  Alert,
  AlertDescription,
  AlertTitle
} from '~~/components/ui/alert'
import { Info, ChevronLeft, ChevronRight } from '@lucide/vue'

const props = withDefaults(defineProps<{
  loading?: boolean
  total?: number
  page?: number
  pageSize?: number
  totalPages?: number
  skeletonCount?: number
  emptyTitle?: string
  emptyDesc?: string
  showPagination?: boolean
}>(), {
  loading: false,
  total: 0,
  page: 1,
  pageSize: 20,
  totalPages: 0,
  skeletonCount: 5,
  emptyTitle: '暂无数据',
  emptyDesc: '试试调整筛选条件',
  showPagination: true
})

const emit = defineEmits<{
  (e: 'update:page', v: number): void
}>()

function goPrev() {
  if (props.page > 1) emit('update:page', props.page - 1)
}
function goNext() {
  if (props.page < Math.max(1, props.totalPages || 1)) emit('update:page', props.page + 1)
}

const startOffset = computed(() => (props.total === 0 ? 0 : (props.page - 1) * props.pageSize + 1))
const endOffset = computed(() => Math.min(props.total, props.page * props.pageSize))
</script>

<template>
  <div class="space-y-4">
    <!-- 加载骨架 -->
    <div
      v-if="loading"
      class="space-y-3"
    >
      <Skeleton
        v-for="i in skeletonCount"
        :key="i"
        class="h-[88px] rounded-[12px]"
      />
    </div>

    <!-- 空态 -->
    <div
      v-else-if="total === 0"
      class="py-14"
    >
      <Alert class="max-w-md mx-auto rounded-[14px]">
        <Info class="size-4" />
        <AlertTitle>{{ emptyTitle }}</AlertTitle>
        <AlertDescription>{{ emptyDesc }}</AlertDescription>
      </Alert>
    </div>

    <!-- 列表内容 -->
    <slot
      v-else
      name="default"
    />

    <!-- 分页条 -->
    <div
      v-if="showPagination && !loading && total > 0"
      class="flex flex-col sm:flex-row items-center sm:justify-between gap-3 pt-2"
    >
      <p class="text-xs text-muted-foreground order-2 sm:order-1">
        共 <span class="font-medium text-foreground">{{ total.toLocaleString() }}</span> 条，
        显示 <span class="font-medium">{{ startOffset }}–{{ endOffset }}</span>
      </p>
      <Pagination
        class="order-1 sm:order-2 w-auto"
        :page="page"
        :items-per-page="pageSize"
        :total="total"
        @update:page="emit('update:page', $event)"
      >
        <PaginationContent class="gap-1">
          <PaginationItem :value="Math.max(1, page - 1)">
            <Button
              size="icon"
              variant="outline"
              class="h-8 w-8 rounded-[8px]"
              :disabled="page <= 1"
              @click="goPrev"
            >
              <ChevronLeft class="size-4" />
            </Button>
          </PaginationItem>
          <PaginationItem :value="page">
            <span class="text-sm text-muted-foreground px-2 tabular-nums">
              {{ page }} / {{ Math.max(1, totalPages) }}
            </span>
          </PaginationItem>
          <PaginationItem :value="Math.min(Math.max(1, totalPages), page + 1)">
            <Button
              size="icon"
              variant="outline"
              class="h-8 w-8 rounded-[8px]"
              :disabled="page >= Math.max(1, totalPages)"
              @click="goNext"
            >
              <ChevronRight class="size-4" />
            </Button>
          </PaginationItem>
        </PaginationContent>
      </Pagination>
    </div>
  </div>
</template>
