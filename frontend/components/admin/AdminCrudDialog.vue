<!--
  通用后台 CRUD 弹窗外壳：内容走默认插槽，底部统一 取消/提交 按钮。
  硬契约：本组件不持有任何表单状态，提交成功后也不会自动关闭——父级必须监听
  submit 自行校验/发请求，并在完成后通过 update:open 关闭弹窗。
-->
<script setup lang="ts">
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '~~/components/ui/dialog'
import { Button } from '~~/components/ui/button'

interface Props {
  open: boolean
  title: string
  description?: string
  loading?: boolean
  submitText?: string
  cancelText?: string
}

withDefaults(defineProps<Props>(), {
  submitText: '保存',
  cancelText: '取消'
})

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'submit'): void
}>()

function submit() {
  emit('submit')
}
</script>

<template>
  <Dialog
    :open="open"
    @update:open="(v: boolean) => emit('update:open', v)"
  >
    <DialogContent class="max-w-2xl max-h-[85vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle>{{ title }}</DialogTitle>
        <DialogDescription v-if="description">
          {{ description }}
        </DialogDescription>
      </DialogHeader>
      <div class="py-2">
        <slot />
      </div>
      <DialogFooter class="gap-2 sm:gap-0">
        <Button
          variant="outline"
          :disabled="loading"
          @click="emit('update:open', false)"
        >
          {{ cancelText }}
        </Button>
        <Button
          :disabled="loading"
          @click="submit"
        >
          {{ submitText }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
