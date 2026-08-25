<script setup lang="ts">
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
import { AlertTriangle } from '@lucide/vue'

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
  loading.value = true
  try {
    await emit('confirm')
    open.value = false
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="max-w-md">
      <DialogHeader>
        <div class="flex items-center gap-3">
          <div
            v-if="destructive"
            class="size-10 shrink-0 rounded-full bg-destructive/10 flex items-center justify-center"
          >
            <AlertTriangle class="size-5 text-destructive" />
          </div>
          <DialogTitle>{{ title }}</DialogTitle>
        </div>
        <DialogDescription class="pt-2">
          {{ description }}
        </DialogDescription>
      </DialogHeader>
      <DialogFooter class="gap-2 sm:gap-0">
        <Button
          variant="outline"
          :disabled="loading"
          @click="open = false"
        >
          {{ cancelText }}
        </Button>
        <Button
          :variant="destructive ? 'destructive' : 'default'"
          :disabled="loading"
          @click="handleConfirm"
        >
          {{ confirmText }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
