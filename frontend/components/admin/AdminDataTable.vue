<script setup lang="ts" generic="T">
import { computed } from 'vue'
import { Skeleton } from '~~/components/ui/skeleton'
import { Checkbox } from '~~/components/ui/checkbox'
import { Inbox } from '@lucide/vue'
import { cn } from '~~/lib/utils'
import type { AdminColumn as Column } from '~~/types/admin'

interface Props {
  columns: Column[]
  data: T[]
  loading?: boolean
  rowKey: keyof T | ((row: T) => string | number)
  selectable?: boolean
  selectedIds?: Array<string | number>
  skeletonRows?: number
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  selectable: false,
  selectedIds: () => [],
  skeletonRows: 5
})

const emit = defineEmits<{
  (e: 'update:selectedIds', value: Array<string | number>): void
  (e: 'row-click', row: T): void
}>()

function getKey(row: T): string | number {
  if (typeof props.rowKey === 'function') return props.rowKey(row)
  return row[props.rowKey] as unknown as string | number
}

function isSelected(row: T): boolean {
  return props.selectedIds.includes(getKey(row))
}

function toggleRow(row: T, checked: boolean) {
  const key = getKey(row)
  const next = new Set(props.selectedIds)
  if (checked) next.add(key)
  else next.delete(key)
  emit('update:selectedIds', Array.from(next))
}

const allSelected = computed({
  get: () => props.data.length > 0 && props.data.every(isSelected),
  set: (checked: boolean) => {
    emit('update:selectedIds', checked ? props.data.map(getKey) : [])
  }
})

const alignClass: Record<string, string> = {
  left: 'text-left',
  right: 'text-right',
  center: 'text-center'
}
</script>

<template>
  <Table>
    <TableHeader>
      <TableRow class="hover:bg-transparent">
        <TableHead
          v-if="selectable"
          class="w-10"
        >
          <Checkbox
            v-model="allSelected"
            aria-label="全选"
          />
        </TableHead>
        <TableHead
          v-for="col in columns"
          :key="col.key"
          :class="cn(col.align && alignClass[col.align], col.class)"
        >
          {{ col.title }}
        </TableHead>
        <TableHead
          v-if="$slots.actions"
          class="w-24 text-right"
        >
          操作
        </TableHead>
      </TableRow>
    </TableHeader>
    <TableBody>
      <!-- 骨架屏 -->
      <TableRow
        v-for="n in loading ? skeletonRows : 0"
        :key="`skeleton-${n}`"
        class="hover:bg-transparent"
      >
        <TableCell v-if="selectable">
          <Skeleton class="size-4" />
        </TableCell>
        <TableCell
          v-for="col in columns"
          :key="col.key"
        >
          <Skeleton class="h-4 w-full max-w-[160px]" />
        </TableCell>
        <TableCell v-if="$slots.actions">
          <Skeleton class="ml-auto size-4" />
        </TableCell>
      </TableRow>

      <!-- 空态 -->
      <TableRow
        v-if="!loading && data.length === 0"
        class="hover:bg-transparent"
      >
        <TableCell
          :colspan="columns.length + (selectable ? 1 : 0) + ($slots.actions ? 1 : 0)"
          class="h-40 text-center"
        >
          <div class="flex flex-col items-center justify-center gap-2 text-muted-foreground">
            <Inbox class="size-8" />
            <span class="text-sm">暂无数据</span>
          </div>
        </TableCell>
      </TableRow>

      <!-- 数据行 -->
      <TableRow
        v-for="row in data"
        :key="getKey(row)"
        :data-state="isSelected(row) ? 'selected' : undefined"
        @click="emit('row-click', row)"
      >
        <TableCell v-if="selectable">
          <Checkbox
            :model-value="isSelected(row)"
            :aria-label="`选择 ${getKey(row)}`"
            @update:model-value="(c: boolean | 'indeterminate') => toggleRow(row, c === true)"
            @click.stop
          />
        </TableCell>
        <TableCell
          v-for="col in columns"
          :key="col.key"
          :class="cn(col.align && alignClass[col.align], col.class)"
        >
          <slot
            :name="`cell-${col.key}`"
            :row="row"
            :value="(row as Record<string, unknown>)[col.key]"
          >
            {{ (row as Record<string, unknown>)[col.key] }}
          </slot>
        </TableCell>
        <TableCell
          v-if="$slots.actions"
          class="text-right"
          @click.stop
        >
          <slot
            name="actions"
            :row="row"
          />
        </TableCell>
      </TableRow>
    </TableBody>
  </Table>
</template>
