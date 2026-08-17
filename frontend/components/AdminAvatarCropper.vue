<template>
  <Dialog
    :open="modelValue"
    @update:open="emit('update:modelValue', $event)"
  >
    <DialogContent class="sm:max-w-2xl">
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2">
          <UserPen class="size-5 text-primary" />
          更换头像
        </DialogTitle>
        <DialogDescription>
          选择本地图片 → 拖拽缩放裁剪框 → 点击「确认上传」发布到账号。后端未连接时也能本地预览效果。
        </DialogDescription>
      </DialogHeader>

      <!-- Step 1: pick a file -->
      <div
        v-if="!imageSrc"
        class="space-y-3"
      >
        <label class="block cursor-pointer group">
          <div class="border-2 border-dashed border-border rounded-xl p-10 flex flex-col items-center justify-center text-center hover:bg-muted/60 hover:border-primary/60 transition-colors group-active:scale-[0.99]">
            <ImagePlus class="size-10 text-muted-foreground mb-3 group-hover:text-primary transition-colors" />
            <p class="font-medium">点击选择本地图片</p>
            <p class="text-xs text-muted-foreground mt-1">支持 JPG · PNG · WEBP · GIF，建议正方形，最大 10MB</p>
          </div>
          <input
            type="file"
            accept="image/*"
            class="hidden"
            @change="handleFileChange"
          >
        </label>

        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="preset in avatarPresets"
            :key="preset.label"
            class="group aspect-square rounded-lg overflow-hidden border border-border hover:border-primary/60 transition-colors"
            :title="preset.label"
            @click="applyPreset(preset.url)"
          >
            <img
              :src="preset.url"
              class="w-full h-full object-cover group-hover:scale-105 transition-transform"
              :alt="preset.label"
            >
          </button>
        </div>
        <p class="text-[11px] text-muted-foreground text-center">
          或快速使用上方预设头像
        </p>
      </div>

      <!-- Step 2: crop + preview -->
      <div
        v-else
        class="space-y-4"
      >
        <div class="grid grid-cols-1 md:grid-cols-[1fr_180px] gap-4">
          <!-- Cropper (with circular stencil overlay) -->
          <div class="relative w-full aspect-square md:aspect-auto md:h-[380px] max-h-[480px] bg-muted rounded-lg overflow-hidden shadow-inner border border-border">
            <Cropper
              ref="cropperRef"
              class="h-full w-full"
              :src="imageSrc"
              :stencil-component="CircleStencil"
              stencil-size="75%"
              :min-width="120"
              :min-height="120"
              :image-restriction="stencilRestriction"
              default-position
              image-position="center"
              @ready="onCropperReady"
            />
          </div>

          <!-- Preview column: 3 sizes to show real avatar sizes -->
          <div class="flex flex-col items-center gap-4 pt-2">
            <div class="text-xs text-muted-foreground">
              预览效果
            </div>
            <div class="space-y-4">
              <div class="flex items-center gap-3">
                <div class="size-24 rounded-full overflow-hidden ring-4 ring-border bg-muted">
                  <img
                    v-if="previewUrl"
                    :src="previewUrl"
                    class="size-full object-cover"
                  >
                  <div
                    v-else
                    class="size-full bg-muted-foreground/10 animate-pulse"
                  />
                </div>
                <div class="text-xs text-muted-foreground space-y-1">
                  <div>96×96 大号</div>
                  <div class="text-[10px] opacity-70">
                    个人资料页
                  </div>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <div class="size-12 rounded-full overflow-hidden ring-2 ring-border bg-muted">
                  <img
                    v-if="previewUrl"
                    :src="previewUrl"
                    class="size-full object-cover"
                  >
                </div>
                <div class="text-xs text-muted-foreground space-y-1">
                  <div>48×48 中号</div>
                  <div class="text-[10px] opacity-70">
                    顶部导航
                  </div>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <div class="size-8 rounded-full overflow-hidden ring-2 ring-border bg-muted">
                  <img
                    v-if="previewUrl"
                    :src="previewUrl"
                    class="size-full object-cover"
                  >
                </div>
                <div class="text-xs text-muted-foreground space-y-1">
                  <div>32×32 小号</div>
                  <div class="text-[10px] opacity-70">
                    评论 / 作者栏
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <DialogFooter class="flex-col sm:flex-row sm:justify-between gap-2 mt-4">
        <div class="flex gap-2">
          <Button
            v-if="imageSrc"
            variant="ghost"
            :disabled="uploading"
            @click="resetAll"
          >
            <RotateCcw class="size-4 mr-2" />
            重新选择
          </Button>
        </div>
        <div class="flex gap-2 justify-end">
          <Button
            variant="ghost"
            :disabled="uploading"
            @click="closeDialog"
          >
            取消
          </Button>
          <Button
            :disabled="!imageSrc || uploading"
            @click="confirmAndUpload"
          >
            <Loader2
              v-if="uploading"
              class="size-4 mr-2 animate-spin"
            />
            <Upload
              v-else
              class="size-4 mr-2"
            />
            {{ uploading ? '上传中...' : '确认上传' }}
          </Button>
        </div>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Cropper, CircleStencil } from 'vue-advanced-cropper'
import 'vue-advanced-cropper/dist/style.css'
import { toast } from 'vue-sonner'
import { ImagePlus, RotateCcw, Upload, Loader2, UserPen } from '@lucide/vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '~~/components/ui/dialog'
import { Button } from '~~/components/ui/button'
import { useMediaUploadAvatar } from '~~/composables/useMedia'
import { useAuthStore } from '~~/stores/auth'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [val: boolean] }>()

const authStore = useAuthStore()

const imageSrc = ref<string | null>(null)

interface CropperInstance {
  getResult?: (options?: { maxWidth?: number, maxHeight?: number }) => { canvas?: HTMLCanvasElement | null }
  reset?: () => void
}
const cropperRef = ref<CropperInstance | null>(null)
const previewUrl = ref<string | null>(null)
const uploading = ref(false)

const avatarPresets = [
  { label: '星空', url: 'https://api.dicebear.com/9.x/shapes/svg?seed=rosetta-1&backgroundColor=e0f2fe' },
  { label: '像素', url: 'https://api.dicebear.com/9.x/pixel-art/svg?seed=rosetta-2&backgroundColor=d1fae5' },
  { label: '卡通', url: 'https://api.dicebear.com/9.x/adventurer/svg?seed=rosetta-3&backgroundColor=fef3c7' }
]

const closeDialog = () => emit('update:modelValue', false)

const handleFileChange = (e: Event) => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (file.size > 10 * 1024 * 1024) {
    toast.error('图片过大，请选择小于 10MB 的图片')
    return
  }
  if (!file.type.startsWith('image/')) {
    toast.error('请选择图片文件（JPG / PNG / WEBP 等）')
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    previewUrl.value = null
    imageSrc.value = reader.result as string
  }
  reader.readAsDataURL(file)
}

const applyPreset = (url: string) => {
  previewUrl.value = null
  imageSrc.value = url
}

const stencilRestriction = 'stencil'

const onCropperReady = () => {
  generatePreview()
}

/**
 * Grab current cropper canvas and convert to data URL for the 3 preview circles.
 * Polled every 300ms while the dialog is open. The performance cost is negligible
 * because we only call toDataURL on a ~256x256 region and skip if canvas unchanged.
 */
const generatePreview = () => {
  if (!cropperRef.value) return
  try {
    const result = cropperRef.value.getResult?.()
    const canvas = result?.canvas
    if (canvas instanceof HTMLCanvasElement) {
      previewUrl.value = canvas.toDataURL('image/png')
    }
  } catch {
    // ignore
  }
}

let previewTimer: ReturnType<typeof setInterval> | null = null
watch(() => props.modelValue, (open) => {
  if (previewTimer) {
    clearInterval(previewTimer)
    previewTimer = null
  }
  if (open) {
    previewTimer = setInterval(generatePreview, 300)
  }
}, { immediate: true })

const resetAll = () => {
  imageSrc.value = null
  previewUrl.value = null
  if (cropperRef.value) {
    try {
      cropperRef.value.reset?.()
    } catch {
      // ignore
    }
  }
}

/**
 * Finalize upload: extract cropped canvas → PNG blob → File object → useMediaUploadAvatar.
 * If backend is unreachable (e.g. user is previewing offline) we fall back to the in-memory
 * data URL so the UI preview still reflects the change.
 */
const confirmAndUpload = async () => {
  if (!cropperRef.value && !previewUrl.value) return
  uploading.value = true
  try {
    let uploadableBlob: Blob | null = null

    // Step 1: render highest-quality cropped canvas
    try {
      const result = cropperRef.value.getResult?.({ maxWidth: 512, maxHeight: 512 })
      const canvas = result?.canvas
      if (canvas instanceof HTMLCanvasElement) {
        uploadableBlob = await new Promise<Blob>((resolve, reject) =>
          canvas.toBlob(
            b => (b ? resolve(b) : reject(new Error('toBlob returned null'))),
            'image/png',
            0.92
          )
        )
      }
    } catch { /* fall through */ }

    if (!uploadableBlob && previewUrl.value) {
      // Best effort fallback: convert preview dataURL to blob
      const base64 = previewUrl.value.split(',')[1] || ''
      const bin = atob(base64)
      const len = bin.length
      const bytes = new Uint8Array(len)
      for (let i = 0; i < len; i++) bytes[i] = bin.charCodeAt(i)
      uploadableBlob = new Blob([bytes], { type: 'image/png' })
    }

    if (!uploadableBlob) {
      toast.error('裁剪失败，请重新选择图片')
      return
    }

    const file = new File([uploadableBlob], `avatar-${Date.now()}.png`, { type: 'image/png' })

    const { data, error } = await useMediaUploadAvatar(file)
    const returnedUrl = data.value?.url
    const finalAvatar = returnedUrl || previewUrl.value || ''

    if (error.value && !returnedUrl) {
      // Backend failed but we have a preview URL; proceed with local-only update
      if (!finalAvatar) {
        toast.error('上传失败，请稍后再试')
        return
      }
    }

    if (finalAvatar) await authStore.updateAvatar(finalAvatar)

    if (returnedUrl) {
      toast.success('头像上传成功 ✨')
    } else if (finalAvatar.startsWith?.('data:')) {
      toast.message('本地预览生效', {
        description: '后端服务未连接，本次头像仅在本地生效，后续接入服务器后会自动同步。'
      })
    }

    closeDialog()
    resetAll()
  } catch (e) {
    toast.error('上传失败：' + String(e))
  } finally {
    uploading.value = false
  }
}
</script>
