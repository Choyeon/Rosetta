<template>
  <div class="image-cropper">
    <div class="cropper-wrapper">
      <Cropper
        ref="cropperRef"
        :src="src"
        :stencil-component="stencil"
        :stencil-props="stencilProps"
        :image-restriction="imageRestriction"
        class="cropper-instance"
        @change="onChange"
        @ready="onReady"
      />
    </div>

    <div
      v-if="showControls"
      class="cropper-controls mt-4 flex flex-wrap items-center gap-2"
    >
      <div class="flex items-center gap-1.5">
        <Button
          variant="outline"
          size="icon"
          class="h-8 w-8"
          @click="zoomIn"
        >
          <ZoomIn class="size-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          class="h-8 w-8"
          @click="zoomOut"
        >
          <ZoomOut class="size-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          class="h-8 w-8"
          @click="rotateLeft"
        >
          <RotateCcw class="size-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          class="h-8 w-8"
          @click="rotateRight"
        >
          <RotateCw class="size-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          class="h-8 w-8"
          @click="flipH"
        >
          <FlipHorizontal class="size-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          class="h-8 w-8"
          @click="flipV"
        >
          <FlipVertical class="size-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          class="h-8 w-8"
          @click="reset"
        >
          <RefreshCw class="size-4" />
        </Button>
      </div>

      <div
        v-if="aspectRatios && aspectRatios.length"
        class="flex items-center gap-1"
      >
        <Button
          v-for="r in aspectRatios"
          :key="r.label"
          :variant="aspectRatio === r.value ? 'default' : 'outline'"
          size="sm"
          class="h-8"
          @click="setAspectRatio(r.value)"
        >
          {{ r.label }}
        </Button>
      </div>
    </div>

    <div
      v-if="showSize"
      class="text-xs text-muted-foreground mt-2"
    >
      {{ croppedWidth }} × {{ croppedHeight }} px
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Cropper, CircleStencil, RectangleStencil } from 'vue-advanced-cropper'
import 'vue-advanced-cropper/dist/style.css'
import { Button } from '~~/components/ui/button'
import {
  ZoomIn, ZoomOut, RotateCcw, RotateCw,
  FlipHorizontal, FlipVertical, RefreshCw
} from '@lucide/vue'

export interface AspectRatioOption {
  label: string
  value: number | null // null = 自由比例
}

interface Props {
  src: string
  /** 裁剪形状：rectangle | circle */
  shape?: 'rectangle' | 'circle'
  /** 固定宽高比，null 为自由 */
  aspectRatio?: number | null
  /** 可选比例切换按钮 */
  aspectRatios?: AspectRatioOption[]
  /** 输出图片宽度（px），0 表示不限制 */
  outputWidth?: number
  /** 输出质量 0-1 */
  quality?: number
  /** 是否显示控制按钮 */
  showControls?: boolean
  /** 是否显示裁剪尺寸 */
  showSize?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  shape: 'rectangle',
  aspectRatio: null,
  aspectRatios: () => [],
  outputWidth: 0,
  quality: 0.92,
  showControls: true,
  showSize: true
})

const emit = defineEmits<{
  (e: 'change', payload: { canvas: HTMLCanvasElement | null }): void
  (e: 'ready'): void
}>()

const cropperRef = ref<InstanceType<typeof Cropper> | null>(null)
const croppedWidth = ref(0)
const croppedHeight = ref(0)

const stencil = computed(() =>
  props.shape === 'circle' ? CircleStencil : RectangleStencil
)

const stencilProps = computed(() => {
  const p: Record<string, unknown> = {}
  if (props.aspectRatio != null) {
    p.aspectRatio = props.aspectRatio
  }
  if (props.shape === 'rectangle') {
    p.handlers = true
  }
  return p
})

const imageRestriction = 'stencil'

function onChange({ canvas }: { canvas: HTMLCanvasElement | null }) {
  if (canvas) {
    croppedWidth.value = canvas.width
    croppedHeight.value = canvas.height
  }
  emit('change', { canvas })
}

function onReady() {
  emit('ready')
}

type CropperInstance = InstanceType<typeof Cropper> & {
  zoomImage: (scale: number, adjust?: boolean) => void
  rotateImage: (degrees: number) => void
  flipImage: (direction: 'horizontal' | 'vertical', adjust?: boolean) => void
  reset: () => void
  getResult: () => { canvas: HTMLCanvasElement | null }
}

function getCropper(): CropperInstance | null {
  return cropperRef.value as unknown as CropperInstance | null
}

function zoomIn() {
  getCropper()?.zoomImage(1.1, true)
}

function zoomOut() {
  getCropper()?.zoomImage(0.9, true)
}

function rotateLeft() {
  getCropper()?.rotateImage(-90)
}

function rotateRight() {
  getCropper()?.rotateImage(90)
}

function flipH() {
  getCropper()?.flipImage('horizontal', true)
}

function flipV() {
  getCropper()?.flipImage('vertical', true)
}

function reset() {
  getCropper()?.reset()
}

function setAspectRatio(_value: number | null) {
  // 通过重新设置 stencil props 触发比例变化
  // vue-advanced-cropper 通过 props 响应式更新
  // 这里直接触发父组件更新
  emit('change', { canvas: null })
}

/**
 * 获取裁剪结果的 Blob
 */
async function getCroppedBlob(
  mimeType = 'image/jpeg',
  quality = props.quality
): Promise<Blob | null> {
  const cropper = getCropper()
  if (!cropper) return null
  const { canvas } = cropper.getResult()
  if (!canvas) return null

  // 如果指定了输出宽度，进行二次缩放
  if (props.outputWidth > 0 && canvas.width !== props.outputWidth) {
    const scale = props.outputWidth / canvas.width
    const out = document.createElement('canvas')
    out.width = props.outputWidth
    out.height = Math.round(canvas.height * scale)
    const ctx = out.getContext('2d')
    if (ctx) {
      ctx.imageSmoothingEnabled = true
      ctx.imageSmoothingQuality = 'high'
      ctx.drawImage(canvas, 0, 0, out.width, out.height)
      return new Promise(resolve =>
        out.toBlob(b => resolve(b), mimeType, quality)
      )
    }
  }

  return new Promise(resolve =>
    canvas.toBlob(b => resolve(b), mimeType, quality)
  )
}

/**
 * 获取裁剪结果的 File 对象
 */
async function getCroppedFile(
  filename: string,
  mimeType = 'image/jpeg',
  quality = props.quality
): Promise<File | null> {
  const blob = await getCroppedBlob(mimeType, quality)
  if (!blob) return null
  const ext = mimeType === 'image/png' ? '.png' : mimeType === 'image/webp' ? '.webp' : '.jpg'
  const name = filename.replace(/\.[^.]+$/, '') + ext
  return new File([blob], name, { type: mimeType, lastModified: Date.now() })
}

// 暴露方法给父组件
defineExpose({
  getCroppedBlob,
  getCroppedFile,
  reset,
  zoomIn,
  zoomOut,
  rotateLeft,
  rotateRight
})

watch(
  () => props.src,
  () => {
    croppedWidth.value = 0
    croppedHeight.value = 0
  }
)
</script>

<style scoped>
.cropper-wrapper {
  position: relative;
  width: 100%;
  height: 360px;
  background: #000;
  border-radius: 0.75rem;
  overflow: hidden;
}
.cropper-instance {
  width: 100%;
  height: 100%;
}
</style>
