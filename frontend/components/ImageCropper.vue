<!--
  vue-advanced-cropper 封装：缩放/旋转/翻转 + 比例切换 + 裁剪结果导出。
  纯客户端组件：getCroppedBlob/getCroppedFile 直接用 document.createElement('canvas') 与
  toBlob，SSR 下无法渲染，调用方必须包 <ClientOnly> 或只在 ssr:false 反选页里使用。
  裁剪产物只经 defineExpose 传出（change 事件仅给实时预览 canvas），父组件不持 ref 就拿不到结果。
-->
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
          title="放大"
          aria-label="放大"
          @click="zoomIn"
        >
          <ZoomIn data-icon="inline-start" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          class="h-8 w-8"
          title="缩小"
          aria-label="缩小"
          @click="zoomOut"
        >
          <ZoomOut data-icon="inline-start" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          class="h-8 w-8"
          title="向左旋转"
          aria-label="向左旋转"
          @click="rotateLeft"
        >
          <RotateCcw data-icon="inline-start" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          class="h-8 w-8"
          title="向右旋转"
          aria-label="向右旋转"
          @click="rotateRight"
        >
          <RotateCw data-icon="inline-start" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          class="h-8 w-8"
          title="水平翻转"
          aria-label="水平翻转"
          @click="flipH"
        >
          <FlipHorizontal data-icon="inline-start" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          class="h-8 w-8"
          title="垂直翻转"
          aria-label="垂直翻转"
          @click="flipV"
        >
          <FlipVertical data-icon="inline-start" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          class="h-8 w-8"
          title="重置"
          aria-label="重置裁剪框"
          @click="reset"
        >
          <RefreshCw data-icon="inline-start" />
        </Button>
      </div>

      <div
        v-if="aspectRatios && aspectRatios.length"
        class="flex items-center gap-1"
      >
        <Button
          v-for="r in aspectRatios"
          :key="r.label"
          :variant="activeRatio === r.value ? 'default' : 'outline'"
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

/** 用户点比例按钮后的覆盖值；undefined = 沿用 props.aspectRatio */
const ratioOverride = ref<number | null | undefined>(undefined)
const activeRatio = computed<number | null>(() => ratioOverride.value ?? props.aspectRatio ?? null)

const stencil = computed(() =>
  props.shape === 'circle' ? CircleStencil : RectangleStencil
)

const stencilProps = computed(() => {
  const p: Record<string, unknown> = {}
  if (activeRatio.value != null) {
    p.aspectRatio = activeRatio.value
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

function setAspectRatio(value: number | null) {
  // stencilProps 是 computed：改变比例会生成新对象，
  // vue-advanced-cropper 内部 watch props.aspectRatio 并重建限制框
  ratioOverride.value = value
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
    // 换了原图就回到调用方声明的默认比例，避免沿用上次的选择
    ratioOverride.value = undefined
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
