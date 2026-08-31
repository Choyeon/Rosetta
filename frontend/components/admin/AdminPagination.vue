<script setup lang="ts">
import {
  Pagination,
  PaginationEllipsis,
  PaginationFirst,
  PaginationLast,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious
} from '~~/components/ui/pagination'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { computed } from 'vue'

interface Props {
  page: number
  pageSize: number
  total: number
  pageSizeOptions?: number[]
}

const props = withDefaults(defineProps<Props>(), {
  pageSizeOptions: () => [10, 20, 50, 100]
})

const emit = defineEmits<{
  (e: 'update:page' | 'update:pageSize', value: number): void
}>()

const _totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

const currentPage = computed({
  get: () => props.page,
  set: (v: number) => emit('update:page', v)
})

function onPageSizeChange(value: string | undefined) {
  if (value == null) return
  emit('update:pageSize', Number(value))
  emit('update:page', 1)
}

const rangeLabel = computed(() => {
  if (props.total === 0) return '共 0 条'
  const start = (props.page - 1) * props.pageSize + 1
  const end = Math.min(props.page * props.pageSize, props.total)
  return `第 ${start}-${end} 条 / 共 ${props.total} 条`
})
</script>

<template>
  <div class="flex flex-col items-center justify-between gap-3 sm:flex-row sm:gap-0">
    <p class="text-sm text-muted-foreground">
      {{ rangeLabel }}
    </p>
    <div class="flex items-center gap-4">
      <div class="flex items-center gap-2">
        <span class="text-sm text-muted-foreground">每页</span>
        <Select
          :model-value="String(pageSize)"
          @update:model-value="onPageSizeChange"
        >
          <SelectTrigger class="h-9 w-[80px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem
              v-for="opt in pageSizeOptions"
              :key="opt"
              :value="String(opt)"
            >
              {{ opt }}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>
      <Pagination
        v-slot="{ page: slotPage }"
        :total="total"
        :items-per-page="pageSize"
        :sibling-count="1"
        :default-page="1"
        :model-page="currentPage"
        @update:page="(p: number) => emit('update:page', p)"
      >
        <PaginationContent
          v-slot="{ items }"
          class="flex items-center gap-1"
        >
          <PaginationFirst />
          <PaginationPrevious />
          <template
            v-for="(item, index) in items"
            :key="index"
          >
            <PaginationItem
              v-if="item.type === 'page'"
              :value="item.value"
            >
              <Button
                size="icon"
                class="size-9"
                :variant="item.value === slotPage ? 'default' : 'outline'"
              >
                {{ item.value }}
              </Button>
            </PaginationItem>
            <PaginationEllipsis v-else />
          </template>
          <PaginationNext />
          <PaginationLast />
        </PaginationContent>
      </Pagination>
    </div>
  </div>
</template>
