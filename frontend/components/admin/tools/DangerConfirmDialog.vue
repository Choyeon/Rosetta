<!--
  「不可撤销」级确认框，消费方集中在 pages/admin/{tools,system,interaction,users}（12 处）；
  content/media 那批页面用的是 admin/AdminConfirmDialog。二者实质差异只有两点：
  ① confirmPhrase 非空时未匹配前确认按钮 disabled（cache/import-export/migrations/users 等在用）；
  ② 失败由本组件用 extractApiErrorMessage 渲染成 role="alert" 内联条，故消费方（navigation/friendlinks/cache）须给请求传 silentToast，否则 toast 与内联双报。
  open 走 defineModel → v-model:open；关闭时 input/errorText/loading 三者一并复位。
-->
<script setup lang="ts">
/**
 * 危险操作确认弹窗（自建，供 tools / system / interaction 页面复用）。
 *
 * 与 AdminConfirmDialog 的差异（刻意设计，不依赖共享组件行为）：
 *   - 通过 `onConfirm` **prop** 传入 async 回调，因此可以真正 await 到执行结果，
 *     不依赖 `emit()` 是否透传 handler 的 Promise
 *   - 需要输入确认短语时（`confirmPhrase`），确认按钮在校验通过前 disabled，
 *     用于「不可撤销」级别的破坏性操作（跨库迁移、清空全站缓存、覆盖导入…）
 *   - 执行期间按钮 disable + loading，重复点击无效；失败时弹窗保持打开并内联展示错误，
 *     避免「toast 一闪而过 + 弹窗已关」的错误吞噬
 */
import { computed, ref, watch } from 'vue'
import { AlertTriangle, Check, Loader2 } from '@lucide/vue'
import { extractApiErrorMessage } from '~~/lib/utils'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '~~/components/ui/dialog'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'

interface Props {
  title?: string
  description?: string
  confirmText?: string
  cancelText?: string
  destructive?: boolean
  /** 需要原样输入的确认短语；留空则退化为普通二次确认 */
  confirmPhrase?: string
  phraseHint?: string
  /** 真正的执行回调：throw 即视为失败，弹窗保持打开 */
  onConfirm?: () => Promise<unknown> | unknown
}

const props = withDefaults(defineProps<Props>(), {
  title: '确认操作',
  description: '此操作不可撤销，确定要继续吗？',
  confirmText: '确认执行',
  cancelText: '取消',
  destructive: true,
  confirmPhrase: '',
  phraseHint: '',
  onConfirm: undefined
})

const open = defineModel<boolean>('open', { default: false })

const loading = ref(false)
const input = ref('')
const errorText = ref('')

watch(open, (v) => {
  if (!v) {
    input.value = ''
    errorText.value = ''
    loading.value = false
  }
})

const phraseMatched = computed(
  () => !props.confirmPhrase || input.value.trim() === props.confirmPhrase
)
const disabled = computed(() => loading.value || !phraseMatched.value)

async function handleConfirm() {
  if (disabled.value) return
  errorText.value = ''
  loading.value = true
  try {
    await props.onConfirm?.()
    open.value = false
  } catch (err) {
    const e = err as { data?: unknown, message?: string }
    errorText.value = extractApiErrorMessage(
      e?.data,
      e?.message || '操作执行失败，请重试或取消'
    )
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
          <DialogTitle class="text-base">
            {{ title }}
          </DialogTitle>
        </div>
        <DialogDescription class="pt-2">
          <slot name="description">
            {{ description }}
          </slot>
        </DialogDescription>
      </DialogHeader>

      <div
        v-if="confirmPhrase"
        class="flex flex-col gap-2"
      >
        <Label
          for="danger-confirm-phrase"
          class="text-sm"
        >
          请输入 <code class="font-mono text-destructive">{{ confirmPhrase }}</code> 以确认
        </Label>
        <Input
          id="danger-confirm-phrase"
          v-model="input"
          autocomplete="off"
          :placeholder="phraseHint || confirmPhrase"
          :disabled="loading"
          class="rounded-xl font-mono"
        />
      </div>

      <p
        v-if="errorText"
        class="flex items-start gap-2 rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
        role="alert"
      >
        <AlertTriangle class="size-4 shrink-0 mt-0.5" />
        <span>{{ errorText }}</span>
      </p>

      <DialogFooter class="gap-2 sm:gap-2">
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
          :disabled="disabled"
          @click="handleConfirm"
        >
          <Loader2
            v-if="loading"
            data-icon="inline-start"
            class="animate-spin"
          />
          <AlertTriangle
            v-else-if="destructive"
            data-icon="inline-start"
          />
          <Check
            v-else
            data-icon="inline-start"
          />
          {{ loading ? '执行中...' : confirmText }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
