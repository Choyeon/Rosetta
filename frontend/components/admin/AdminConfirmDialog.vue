<!--
  文件级分工：消费方只有 pages/admin/content/*（categories/pages/series/tags/posts）与 pages/admin/media/*（gallery/library）；
  tools / system / interaction / users 走的是 admin/tools/DangerConfirmDialog（多一道 confirmPhrase 输入闸门 + 内联错误条）。
  本组件没有任何错误渲染出口：onConfirm 抛错只 console.error 并保持弹窗打开，因此调用方禁止传 silentToast，
  失败提示必须由 apiFetch 的统一 toast 承担。open 是 defineModel → 写 v-model:open；关闭只复位 loading。
-->
<script setup lang="ts">
/**
 * 后台统一二次确认弹窗。
 *
 * 统一约定（所有 admin 页面的删除/重置类操作都应走这里，不要再手写 Dialog）：
 *   - 危险操作左侧一定有 AlertTriangle 图标块，且在 destructive 模式下主按钮为红色
 *   - 执行期间按钮自动进入 loading（旋转图标），并禁用取消按钮，避免重复提交
 *   - 执行回调通过 **`onConfirm` prop** 传入（不是 `@confirm` 事件）：
 *     `emit()` 的返回值恒为 undefined，父组件的 async handler 根本 await 不到，
 *     失败时弹窗会照样关闭 —— 那是本组件修掉的历史缺陷。
 *   - onConfirm 抛出即视为失败：弹窗保持打开供用户重试，错误提示由调用方
 *     （通常是 apiFetch 的统一 toast）负责，所以调用方不要再 try/catch 吞掉异常
 */
import { ref, watch } from 'vue'
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
  /** 真正的执行回调：throw 即视为失败，弹窗保持打开 */
  onConfirm?: () => Promise<unknown> | unknown
}

const props = withDefaults(defineProps<Props>(), {
  title: '确认操作',
  description: '此操作不可撤销，确定要继续吗？',
  confirmText: '确认',
  cancelText: '取消',
  destructive: true,
  onConfirm: undefined
})

const open = defineModel<boolean>('open', { default: false })
const loading = ref(false)

watch(open, (v) => {
  if (!v) loading.value = false
})

async function handleConfirm() {
  if (loading.value) return
  loading.value = true
  try {
    await props.onConfirm?.()
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
