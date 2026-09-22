<template>
  <div
    class="image-upload-zone"
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @drop.prevent="onDrop"
  >
    <div
      :class="[
        'relative rounded-xl border-2 border-dashed transition-all duration-200 cursor-pointer',
        isDragging
          ? 'border-primary bg-primary/5 scale-[1.01]'
          : 'border-border hover:border-primary/50 hover:bg-muted/30',
        disabled ? 'opacity-50 pointer-events-none' : ''
      ]"
      @click="triggerInput"
    >
      <div class="flex flex-col items-center justify-center py-10 px-4 text-center">
        <div class="size-12 rounded-full bg-primary/10 flex items-center justify-center mb-3">
          <UploadCloud class="size-6 text-primary" />
        </div>
        <p class="text-sm font-medium">
          {{ multiple ? '点击或拖拽图片到此处上传' : '点击或拖拽图片到此处' }}
        </p>
        <p class="text-xs text-muted-foreground mt-1">
          支持 JPG / PNG / WebP / GIF{{ maxSize ? `，单张最大 ${maxSize}MB` : '' }}
        </p>
        <p
          v-if="autoCompress"
          class="text-xs text-muted-foreground mt-0.5"
        >
          上传前将自动压缩优化
        </p>
        <input
          ref="inputRef"
          type="file"
          :accept="accept"
          :multiple="multiple"
          class="hidden"
          @change="onFileInput"
        >
      </div>
    </div>

    <!-- 上传队列 -->
    <div
      v-if="queue.length"
      class="mt-3 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3"
    >
      <div
        v-for="item in queue"
        :key="item.id"
        class="relative rounded-lg border bg-card overflow-hidden group"
      >
        <div class="aspect-square bg-muted relative">
          <img
            v-if="item.preview"
            :src="item.preview"
            class="size-full object-cover"
          >
          <div
            v-if="item.status === 'uploading'"
            class="absolute inset-0 bg-black/40 flex items-center justify-center"
          >
            <div class="text-white text-xs font-medium">
              {{ item.progress }}%
            </div>
          </div>
          <div
            v-else-if="item.status === 'success'"
            class="absolute top-1.5 right-1.5 size-5 rounded-full bg-green-500 flex items-center justify-center"
          >
            <Check class="size-3 text-white" />
          </div>
          <div
            v-else-if="item.status === 'error'"
            class="absolute top-1.5 right-1.5 size-5 rounded-full bg-destructive flex items-center justify-center cursor-pointer"
            @click.stop="removeItem(item.id)"
          >
            <X class="size-3 text-white" />
          </div>
        </div>
        <div class="p-2">
          <p
            class="text-xs truncate"
            :title="item.name"
          >
            {{ item.name }}
          </p>
          <p class="text-[10px] text-muted-foreground">
            {{ formatBytes(item.size) }}
            <span
              v-if="item.compressedSize && item.compressedSize < item.size"
              class="text-green-600"
            >
              → {{ formatBytes(item.compressedSize) }}
            </span>
          </p>
          <div
            v-if="item.status === 'uploading'"
            class="mt-1 h-1 rounded-full bg-muted overflow-hidden"
          >
            <div
              class="h-full bg-primary transition-all duration-200"
              :style="{ width: `${item.progress}%` }"
            />
          </div>
          <p
            v-if="item.status === 'error'"
            class="text-[10px] text-destructive mt-0.5 truncate"
          >
            {{ item.error || '上传失败' }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { UploadCloud, Check, X } from '@lucide/vue'
import { compressImage, formatBytes, type CompressResult } from '~~/composables/useImageCompress'
import { useMediaLibrary } from '~~/composables/useMedia'

interface UploadItem {
  id: string
  file: File
  name: string
  size: number
  compressedSize?: number
  preview: string
  status: 'pending' | 'compressing' | 'uploading' | 'success' | 'error'
  progress: number
  error?: string
  result?: unknown
}

interface Props {
  /** 上传分类（gallery / post-cover / avatar / cover） */
  category?: string
  /** 是否允许多文件 */
  multiple?: boolean
  /** 接受的文件类型 */
  accept?: string
  /** 单文件最大 MB */
  maxSize?: number
  /** 是否自动压缩 */
  autoCompress?: boolean
  /** 是否禁用 */
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  category: undefined,
  multiple: true,
  accept: 'image/jpeg,image/png,image/webp,image/gif',
  maxSize: 20,
  autoCompress: true,
  disabled: false
})

const emit = defineEmits<{
  (e: 'uploaded', items: unknown[]): void
  (e: 'error', msg: string): void
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const queue = ref<UploadItem[]>([])

const { uploadMedia } = useMediaLibrary()

function triggerInput() {
  if (props.disabled) return
  inputRef.value?.click()
}

function onFileInput(e: Event) {
  const target = e.target as HTMLInputElement
  const files = Array.from(target.files ?? [])
  if (files.length) handleFiles(files)
  target.value = ''
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  if (props.disabled) return
  const files = Array.from(e.dataTransfer?.files ?? []).filter(f =>
    f.type.startsWith('image/')
  )
  if (files.length) handleFiles(files)
}

function handleFiles(files: File[]) {
  const valid = files.filter((f) => {
    if (!f.type.startsWith('image/')) return false
    if (props.maxSize && f.size > props.maxSize * 1024 * 1024) {
      emit('error', `${f.name} 超过 ${props.maxSize}MB 限制`)
      return false
    }
    return true
  })

  if (!valid.length) return

  for (const file of valid) {
    const item: UploadItem = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      file,
      name: file.name,
      size: file.size,
      preview: URL.createObjectURL(file),
      status: 'pending',
      progress: 0
    }
    queue.value.push(item)
    void processItem(item)
  }
}

async function processItem(item: UploadItem) {
  try {
    let uploadFile = item.file

    if (props.autoCompress) {
      item.status = 'compressing'
      const result: CompressResult = await compressImage(item.file)
      uploadFile = result.file
      item.compressedSize = result.size
    }

    item.status = 'uploading'
    item.progress = 10

    // 模拟进度（XMLHttpRequest 可做真实进度，这里简化）
    const progressTimer = setInterval(() => {
      if (item.progress < 90) item.progress += 10
    }, 150)

    const media = await uploadMedia(uploadFile, props.category)

    clearInterval(progressTimer)
    item.progress = 100
    item.status = 'success'
    item.result = media

    const successItems = queue.value.filter(q => q.status === 'success')
    emit('uploaded', successItems.map(i => i.result))
  } catch (e) {
    item.status = 'error'
    item.error = e instanceof Error ? e.message : '上传失败'
    emit('error', item.error)
  }
}

function removeItem(id: string) {
  const idx = queue.value.findIndex(i => i.id === id)
  if (idx >= 0) {
    const item = queue.value[idx]
    if (item) URL.revokeObjectURL(item.preview)
    queue.value.splice(idx, 1)
  }
}

/** 清空队列 */
function clearQueue() {
  for (const item of queue.value) {
    URL.revokeObjectURL(item.preview)
  }
  queue.value = []
}

/** 等待全部上传完成 */
async function waitAll(): Promise<unknown[]> {
  const pending = queue.value.filter(i => i.status !== 'success' && i.status !== 'error')
  if (!pending.length) return getResults()
  await new Promise((resolve) => {
    const check = setInterval(() => {
      const stillPending = queue.value.some(
        i => i.status === 'pending' || i.status === 'compressing' || i.status === 'uploading'
      )
      if (!stillPending) {
        clearInterval(check)
        resolve(true)
      }
    }, 200)
  })
  return getResults()
}

function getResults(): unknown[] {
  return queue.value.filter(i => i.status === 'success').map(i => i.result)
}

defineExpose({ clearQueue, waitAll, getResults })
</script>
