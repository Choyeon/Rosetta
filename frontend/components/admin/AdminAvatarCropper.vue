<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { ref, watch, computed } from 'vue'
import { Upload, X, RotateCw, Check, Image as ImageIcon } from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Slider } from '~~/components/ui/slider'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '~~/components/ui/dialog'
import { useToast } from '~~/composables/useToast'

const props = withDefaults(defineProps<{
  modelValue?: string
  /** 上传到后端的分类：'avatar' 走 useMediaUploadAvatar，其他走 useMediaUpload(file, category) */
  category?: string
  shape?: 'circle' | 'square'
  size?: number
  /** 文件最大 MB */
  maxSize?: number
}>(), {
  category: 'avatar',
  shape: 'circle',
  size: 96,
  maxSize: 5
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'uploaded': [payload: { url: string, file: File }]
}>()

const { success, error, warning } = useToast()

const open = ref(false)
const rawDataUrl = ref('')
const zoom = ref(1)
const rotation = ref(0)
const fileInput = ref<HTMLInputElement | null>(null)
const submitting = ref(false)

const boxSize = computed(() => 260)

const pickFile = () => fileInput.value?.click()

const handleFile = (e: Event) => {
  const target = e.target as HTMLInputElement
  const f = target.files?.[0]
  if (!f) return
  if (!f.type.startsWith('image/')) {
    warning('只能选择图片文件')
    return
  }
  if (f.size > props.maxSize * 1024 * 1024) {
    warning(`图片不能超过 ${props.maxSize}MB`)
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    rawDataUrl.value = String(reader.result || '')
    zoom.value = 1
    rotation.value = 0
    open.value = true
  }
  reader.readAsDataURL(f)
  target.value = ''
}

const rotate = (deg: number) => {
  rotation.value = (rotation.value + deg) % 360
}

/** 把裁剪区（正方形）的内容画到 canvas，导出 blob */
const cropToBlob = async (): Promise<Blob> => {
  const size = 512
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')!

  await new Promise<void>((resolve, reject) => {
    const img = new Image()
    img.onerror = reject
    img.onload = () => {
      // 以裁剪框尺寸为准，计算 scale/translate
      const scale = zoom.value
      const ratio = Math.min(size / img.width, size / img.height) * scale
      const dw = img.width * ratio
      const dh = img.height * ratio
      const dx = (size - dw) / 2
      const dy = (size - dh) / 2

      ctx.save()
      ctx.clearRect(0, 0, size, size)
      ctx.translate(size / 2, size / 2)
      ctx.rotate((rotation.value * Math.PI) / 180)
      ctx.drawImage(img, dx - size / 2, dy - size / 2, dw, dh)
      ctx.restore()
      resolve()
    }
    img.src = rawDataUrl.value
  })

  return await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((b) => {
      if (b) resolve(b)
      else reject(new Error('Failed to crop image'))
    }, 'image/webp', 0.9)
  })
}

const confirmCrop = async () => {
  submitting.value = true
  try {
    const blob = await cropToBlob()
    const file = new File([blob], `cropped-${Date.now()}.webp`, { type: 'image/webp' })
    const { useMediaUpload, useMediaUploadAvatar } = await import('~~/composables/useMedia')
    let url = ''
    if (props.category === 'avatar') {
      const res = await useMediaUploadAvatar(file)
      url = (res && res.url) ? res.url : ''
    } else {
      const res = await useMediaUpload(file, props.category)
      // /media/library 返回结构通常有 url 字段，兼容 MediaItem 形状
      url = (res && (res as any).url) ? (res as any).url : ''
    }
    if (!url) throw new Error('上传失败，未返回 URL')
    emit('update:modelValue', url)
    emit('uploaded', { url, file })
    success('头像上传成功')
    open.value = false
    rawDataUrl.value = ''
  } catch (e: any) {
    error(e?.message || '上传失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

const clear = () => {
  emit('update:modelValue', '')
  success('已清除头像')
}

const close = () => {
  open.value = false
  rawDataUrl.value = ''
}

// drop 拖拽
const dragOver = ref(false)
const onDrop = (e: DragEvent) => {
  e.preventDefault()
  dragOver.value = false
  const f = e.dataTransfer?.files?.[0]
  if (!f) return
  const fakeEvent = { target: { files: [f], value: '' } } as unknown as Event
  handleFile(fakeEvent)
}
</script>

<template>
  <div class="admin-avatar-cropper inline-flex flex-col items-center gap-3">
    <!-- 预览区 -->
    <div
      class="relative group shrink-0"
      :style="{ width: size + 'px', height: size + 'px' }"
    >
      <div
        class="absolute inset-0 overflow-hidden border-2 border-dashed transition-colors"
        :class="[
          shape === 'circle' ? 'rounded-full' : 'rounded-[14px]',
          dragOver ? 'border-primary bg-primary/5' : 'border-border'
        ]"
        @dragover.prevent="dragOver = true"
        @dragleave="dragOver = false"
        @drop="onDrop"
      >
        <img
          v-if="modelValue"
          :src="modelValue"
          alt="avatar"
          class="w-full h-full object-cover"
        >
        <div
          v-else
          class="w-full h-full flex flex-col items-center justify-center text-muted-foreground/60 bg-muted/50"
        >
          <ImageIcon class="size-6 mb-1" />
          <span class="text-[11px]">未设置</span>
        </div>
      </div>
      <!-- Hover 浮层：上传 / 清除 -->
      <div
        class="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-1.5 bg-foreground/50 backdrop-blur-[2px]"
        :class="shape === 'circle' ? 'rounded-full' : 'rounded-[14px]'"
      >
        <Button
          type="button"
          size="icon"
          class="size-8 rounded-full bg-background/95 hover:bg-background text-foreground shadow"
          @click="pickFile"
        >
          <Upload class="size-4" />
        </Button>
        <Button
          v-if="modelValue"
          type="button"
          size="icon"
          variant="destructive"
          class="size-8 rounded-full shadow"
          @click="clear"
        >
          <X class="size-4" />
        </Button>
      </div>
    </div>

    <div class="flex items-center gap-2">
      <Button
        type="button"
        size="sm"
        variant="secondary"
        class="rounded-[10px] h-8"
        @click="pickFile"
      >
        <Upload class="size-4 mr-1.5" />
        上传图片
      </Button>
      <span class="text-[11px] text-muted-foreground">
        支持拖拽，≤{{ maxSize }}MB
      </span>
    </div>

    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      class="hidden"
      @change="handleFile"
    >

    <!-- 裁剪对话框 -->
    <Dialog
      :open="open"
      @update:open="(v: boolean) => !v && close()"
    >
      <DialogContent class="sm:max-w-[440px] rounded-[16px] p-4">
        <DialogHeader>
          <DialogTitle class="text-base">
            调整头像
          </DialogTitle>
        </DialogHeader>
        <div class="py-3 flex flex-col items-center gap-4">
          <!-- 裁剪框 -->
          <div
            class="relative overflow-hidden border border-border bg-muted/30"
            :class="shape === 'circle' ? 'rounded-full' : 'rounded-[12px]'"
            :style="{ width: boxSize + 'px', height: boxSize + 'px' }"
          >
            <img
              :src="rawDataUrl"
              alt="crop"
              class="w-full h-full object-cover"
              :style="{
                transform: `scale(${zoom}) rotate(${rotation}deg)`,
                transition: 'transform 160ms ease-out'
              }"
              draggable="false"
            >
            <div
              class="absolute inset-0 pointer-events-none shadow-[inset_0_0_0_1px_rgba(255,255,255,0.2)]"
              aria-hidden="true"
            />
          </div>

          <!-- 缩放 -->
          <div class="w-full px-2 flex items-center gap-3">
            <span class="text-xs text-muted-foreground shrink-0 w-10">缩放</span>
            <Slider
              :model-value="[zoom * 100]"
              :min="50"
              :max="250"
              :step="1"
              class="flex-1"
              @update:model-value="(v: number[]) => (zoom = v[0] / 100)"
            />
            <span class="text-xs tabular-nums text-muted-foreground shrink-0 w-12 text-right">
              {{ Math.round(zoom * 100) }}%
            </span>
          </div>

          <!-- 旋转 -->
          <div class="w-full px-2 flex items-center gap-2">
            <span class="text-xs text-muted-foreground shrink-0 w-10">旋转</span>
            <Button
              size="sm"
              variant="outline"
              class="h-8 rounded-[8px]"
              @click="rotate(-90)"
            >
              <RotateCw class="size-4 mr-1 rotate-180" />
              -90°
            </Button>
            <Button
              size="sm"
              variant="outline"
              class="h-8 rounded-[8px]"
              @click="rotate(90)"
            >
              <RotateCw class="size-4 mr-1" />
              +90°
            </Button>
            <div class="flex-1" />
            <span class="text-xs tabular-nums text-muted-foreground">
              {{ rotation }}°
            </span>
          </div>
        </div>
        <DialogFooter class="flex-col-reverse sm:flex-row gap-2">
          <Button
            type="button"
            variant="outline"
            class="rounded-[10px]"
            @click="close"
          >
            取消
          </Button>
          <Button
            type="button"
            class="rounded-[10px] text-white shadow-[0_6px_16px_-6px_hsl(var(--primary)/0.7)]"
            style="background: linear-gradient(135deg,#0EA5E9 0%,#0284C7 100%);"
            :disabled="submitting"
            @click="confirmCrop"
          >
            <Check
              v-if="!submitting"
              class="size-4 mr-1.5"
            />
            {{ submitting ? '上传中…' : '确认并保存' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
