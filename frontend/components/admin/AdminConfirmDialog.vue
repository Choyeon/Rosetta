<script setup lang="ts">
/**
 * 后台统一二次确认弹窗。
 *
 * 统一约定（所有 admin 页面的删除/重置类操作都应走这里，不要再手写 Dialog）：
 *   - 危险操作左侧一定有 AlertTriangle 图标块，且在 destructive 模式下主按钮为红色
 *   - 执行期间按钮自动进入 loading（旋转图标），并禁用取消按钮，避免重复提交
 *   - confirm 回调抛出错误时不关闭弹窗，由调用方自行 toast 提示
 */
import { ref } from 'vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '~~/components/ui/dialog'
import { Button } from '~~/components/ui/button'
import { AlertTriangle, Check, Loader2 } from '@lucide/vue'

interface Props {
  title?: string
  description?: string
  confirmText?: string
  cancelText?: string
  destructive?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: '确认操作',
  description: '此操作不可撤销，确定要继续吗？',
  confirmText: '确认',
  cancelText: '取消',
  destructive: true
})

const open = defineModel<boolean>('open', { default: false })
const loading = ref(false)

const emit = defineEmits<{
  (e: 'confirm'): Promise<void> | void
}>()

async function handleConfirm() {
  if (loading.value) return
  loading.value = true
  try {
    await emit('confirm')
    open.value = false
  } catch (err) {
    // 失败时不关闭：调用方通常已 toast 报错，用户可重试或取消
    console.error('[AdminConfirmDialog] confirm handler failed:', err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="max-w-md rounded-2xl">
      <DialogHeader>
        <div class="flex items-center gap-3">
          <div
            class="size-10 shrink-0 rounded-xl flex items-center justify-center"
            :class="destructive ? 'bg-destructive/10' : 'bg-primary/10'"
          >
            <AlertTriangle
              class="size-5"
              :class="destructive ? 'text-destructive' : 'text-primary'"
            />
          </div>
          <DialogTitle>{{ title }}</DialogTitle>
        </div>
        <DialogDescription class="pt-2">
          <slot name="description">
            {{ description }}
          </slot>
        </DialogDescription>
      </DialogHeader>
      <DialogFooter class="gap-2 sm:gap-0">
        <Button
          variant="outline"
          class="rounded-xl"
          :disabled="loading"
          @click="open = false"
        >
          {{ cancelText }}
        </Button>
        <Button
          class="rounded-xl"
          :variant="destructive ? 'destructive' : 'default'"
          :disabled="loading"
          @click="handleConfirm"
        >
          <Loader2
            v-if="loading"
            data-icon="inline-start"
            class="animate-spin"
          />
          <AlertTriangle
            v-else-if="props.destructive"
            data-icon="inline-start"
          />
          <Check
            v-else
            data-icon="inline-start"
          />
          {{ loading ? '处理中...' : confirmText }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
