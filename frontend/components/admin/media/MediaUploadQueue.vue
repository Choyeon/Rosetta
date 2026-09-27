<!--
  媒体上传队列面板：纯视图组件，逐行展示 useUploadProgress 的 UploadQueueItem 状态。
  硬契约：队列真源在父级 composable，本组件不持有任何项； uploading 行的 X 按钮
  与失败行的 X 走同一个 remove 事件——语义是"进行中=中止、已结束=移除"，由父级区分实现。
-->
<template>
  <div
    v-if="items.length"
    class="rounded-xl border bg-card"
  >
    <div class="flex items-center justify-between gap-2 border-b px-4 py-2.5">
      <div class="flex items-center gap-2">
        <Upload
          class="size-4 text-muted-foreground"
        />
        <span class="text-sm font-medium">{{ t('admin.media.uploadQueueTitle', '上传任务') }}</span>
        <span class="text-xs text-muted-foreground">
          {{ doneCount }} / {{ items.length }}
        </span>
      </div>
      <Button
        v-if="hasFinished"
        variant="ghost"
        size="sm"
        @click="emit('clear-finished')"
      >
        {{ t('admin.media.uploadQueueClear', '清除已完成') }}
      </Button>
    </div>
    <ul class="flex flex-col gap-1 p-2">
      <li
        v-for="item in items"
        :key="item.id"
        class="flex items-center gap-3 rounded-lg px-2 py-1.5 transition-colors hover:bg-muted/50"
      >
        <div class="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted">
          <Loader2
            v-if="item.status === 'uploading'"
            class="size-4 animate-spin text-muted-foreground"
          />
          <CheckCircle2
            v-else-if="item.status === 'success'"
            class="size-4 text-success"
          />
          <XCircle
            v-else
            class="size-4 text-destructive"
          />
        </div>
        <div class="flex min-w-0 flex-1 flex-col gap-1">
          <div class="flex items-center justify-between gap-2">
            <p
              class="truncate text-xs font-medium"
              :title="item.filename"
            >
              {{ item.filename }}
            </p>
            <span
              v-if="item.status === 'uploading'"
              class="shrink-0 text-xs tabular-nums text-muted-foreground"
            >
              {{ item.progress }}%
            </span>
            <span
              v-else-if="item.status === 'success'"
              class="shrink-0 text-xs text-success"
            >
              {{ t('admin.media.uploadQueueDone', '已完成') }}
            </span>
            <span
              v-else
              class="shrink-0 max-w-[45%] truncate text-xs text-destructive"
              :title="item.error"
            >
              {{ item.error || t('admin.media.uploadQueueFailed', '失败') }}
            </span>
          </div>
          <Progress
            v-if="item.status === 'uploading'"
            :value="item.progress"
            class="h-1.5"
          />
        </div>
        <Button
          variant="ghost"
          size="icon-sm"
          class="shrink-0"
          :title="item.status === 'uploading'
            ? t('admin.media.uploadQueueCancel', '取消上传')
            : t('admin.media.uploadQueueDismiss', '移除')"
          :aria-label="item.status === 'uploading'
            ? t('admin.media.uploadQueueCancel', '取消上传')
            : t('admin.media.uploadQueueDismiss', '移除')"
          @click="emit('remove', item.id)"
        >
          <X data-icon="inline-end" />
        </Button>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import type { UploadQueueItem } from '~~/composables/useUploadProgress'
import { Button } from '~~/components/ui/button'
import { Progress } from '~~/components/ui/progress'
import { Loader2, CheckCircle2, XCircle, X, Upload } from '@lucide/vue'

defineOptions({ name: 'MediaUploadQueue' })

const props = defineProps<{
  items: UploadQueueItem[]
}>()

const emit = defineEmits<{
  (e: 'remove', id: string): void
  (e: 'clear-finished'): void
}>()

const { t: $_t } = useI18n()
const t = (k: string, fallback: string, values?: Record<string, unknown>) => {
  try {
    const v = values ? $_t(k, values) : $_t(k)
    return v && v !== k ? v : fallback
  } catch {
    return fallback
  }
}

const doneCount = computed(() => props.items.filter(x => x.status !== 'uploading').length)
const hasFinished = computed(() => doneCount.value > 0)
</script>
