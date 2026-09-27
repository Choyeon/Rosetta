<!--
  媒体库预览弹窗：按 MIME 分支预览图片/视频/音频，并编辑标题/alt/描述。
  硬契约：受控弹窗——open 与当前 media 均由 library 页持有；保存走
  PUT /media/library/{id}（后端非 None 即更新、传 '' 可清空），因此三个字段
  必须始终全量提交，缺键会导致旧值无法清空；表单初值靠 watch(open+media.id) 同步。
-->
<template>
  <Dialog
    :open="open"
    @update:open="(v: boolean) => emit('update:open', v)"
  >
    <DialogContent class="max-w-3xl">
      <DialogHeader>
        <DialogTitle class="truncate pr-8">
          {{ media?.filename || t('admin.media.previewTitle', '媒体预览') }}
        </DialogTitle>
        <DialogDescription>
          {{ t('admin.media.previewDescription', '查看媒体文件内容并编辑基础信息') }}
        </DialogDescription>
      </DialogHeader>

      <div
        v-if="media"
        class="flex flex-col md:flex-row gap-4"
      >
        <!-- 预览区 -->
        <div class="flex-1 min-w-0 rounded-xl border bg-muted/40 overflow-hidden">
          <div class="flex items-center justify-center p-3 min-h-[240px] max-h-[50vh]">
            <img
              v-if="kind === 'image'"
              :src="media.url"
              :alt="media.alt_text || media.filename"
              class="max-h-[45vh] w-auto max-w-full object-contain rounded-lg"
            >
            <video
              v-else-if="kind === 'video'"
              :src="media.url"
              controls
              preload="metadata"
              class="max-h-[45vh] w-auto max-w-full rounded-lg"
            />
            <audio
              v-else-if="kind === 'audio'"
              :src="media.url"
              controls
              class="w-full"
            />
            <div
              v-else
              class="flex flex-col items-center justify-center gap-3 py-8 text-center"
            >
              <FileText class="size-14 text-muted-foreground" />
              <p class="text-sm text-muted-foreground">
                {{ t('admin.media.previewNoInline', '该文件类型不支持在线预览') }}
              </p>
              <a
                :href="media.url"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button
                  variant="outline"
                  size="sm"
                >
                  <ExternalLink
                    data-icon="inline-start"
                  />
                  {{ t('admin.media.previewOpenNewTab', '新标签页打开') }}
                </Button>
              </a>
            </div>
          </div>
        </div>

        <!-- 元数据 + 编辑面板 -->
        <div class="w-full md:w-80 shrink-0 flex flex-col gap-4">
          <div class="flex flex-col gap-2 rounded-xl border p-3">
            <p class="text-xs font-medium text-muted-foreground">
              {{ t('admin.media.previewMeta', '文件信息') }}
            </p>
            <dl class="flex flex-col gap-1.5 text-xs">
              <div class="flex items-center justify-between gap-2">
                <dt class="text-muted-foreground shrink-0">
                  {{ t('admin.media.previewFilename', '文件名') }}
                </dt>
                <dd
                  class="truncate font-medium"
                  :title="media.filename"
                >
                  {{ media.filename }}
                </dd>
              </div>
              <div class="flex items-center justify-between gap-2">
                <dt class="text-muted-foreground shrink-0">
                  {{ t('admin.media.previewSize', '大小') }}
                </dt>
                <dd class="font-medium">
                  {{ formatSize(media.size_bytes) }}
                </dd>
              </div>
              <div class="flex items-center justify-between gap-2">
                <dt class="text-muted-foreground shrink-0">
                  {{ t('admin.media.previewDimensions', '尺寸') }}
                </dt>
                <dd class="font-medium">
                  {{ media.width && media.height ? `${media.width} × ${media.height}` : '—' }}
                </dd>
              </div>
              <div class="flex items-center justify-between gap-2">
                <dt class="text-muted-foreground shrink-0">
                  {{ t('admin.media.previewType', '类型') }}
                </dt>
                <dd
                  class="truncate font-medium"
                  :title="media.mime || media.file_type || ''"
                >
                  {{ media.file_type || media.mime || '—' }}
                </dd>
              </div>
              <div class="flex items-center justify-between gap-2">
                <dt class="text-muted-foreground shrink-0">
                  {{ t('admin.media.previewUploader', '上传者') }}
                </dt>
                <dd class="truncate font-medium">
                  {{ uploaderName }}
                </dd>
              </div>
              <div class="flex items-center justify-between gap-2">
                <dt class="text-muted-foreground shrink-0">
                  {{ t('admin.media.previewCreatedAt', '上传时间') }}
                </dt>
                <dd class="font-medium">
                  {{ createdLabel }}
                </dd>
              </div>
            </dl>
            <div class="mt-1 flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                class="flex-1"
                @click="copyUrl"
              >
                <Copy data-icon="inline-start" />
                {{ t('admin.media.previewCopyUrl', '复制链接') }}
              </Button>
            </div>
          </div>

          <div class="flex flex-col gap-3">
            <div class="flex flex-col gap-1.5">
              <Label for="media-edit-title">
                {{ t('admin.media.previewFieldTitle', '标题') }}
              </Label>
              <Input
                id="media-edit-title"
                v-model="form.title"
                :placeholder="t('admin.media.previewFieldTitlePh', '请输入标题（可选）')"
              />
            </div>
            <div class="flex flex-col gap-1.5">
              <Label for="media-edit-alt">
                {{ t('admin.media.previewFieldAlt', '替代文本 (alt)') }}
              </Label>
              <Input
                id="media-edit-alt"
                v-model="form.alt_text"
                :placeholder="t('admin.media.previewFieldAltPh', '用于无障碍与 SEO')"
              />
            </div>
            <div class="flex flex-col gap-1.5">
              <Label for="media-edit-desc">
                {{ t('admin.media.previewFieldDesc', '描述') }}
              </Label>
              <Textarea
                id="media-edit-desc"
                v-model="form.description"
                rows="3"
                class="resize-none"
                :placeholder="t('admin.media.previewFieldDescPh', '文件描述（可选）')"
              />
            </div>
            <Button
              :disabled="saving"
              @click="save"
            >
              <Loader2
                v-if="saving"
                data-icon="inline-start"
                class="animate-spin"
              />
              {{ t('admin.media.previewSave', '保存信息') }}
            </Button>
          </div>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import type { MediaLibraryItem } from '~~/types/media-library'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Label } from '~~/components/ui/label'
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle
} from '~~/components/ui/dialog'
import { Copy, ExternalLink, FileText, Loader2 } from '@lucide/vue'

defineOptions({ name: 'MediaPreviewDialog' })

const props = defineProps<{
  open: boolean
  media: MediaLibraryItem | null
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'updated', payload: { id: number, title: string, alt_text: string, description: string }): void
}>()

const toast = useToast()
const { t: $_t } = useI18n()
const t = (k: string, fallback: string, values?: Record<string, unknown>) => {
  try {
    const v = values ? $_t(k, values) : $_t(k)
    return v && v !== k ? v : fallback
  } catch {
    return fallback
  }
}

const saving = ref(false)
const form = reactive({ title: '', alt_text: '', description: '' })

// media 切换 / 对话框打开时同步表单初值
watch(
  () => [props.open, props.media?.id] as const,
  () => {
    if (!props.open || !props.media) return
    form.title = props.media.title ?? ''
    form.alt_text = props.media.alt_text ?? ''
    form.description = props.media.description ?? ''
  },
  { immediate: true }
)

const kind = computed<'image' | 'video' | 'audio' | 'other'>(() => {
  const mime = props.media?.mime || ''
  if (mime.startsWith('image/')) return 'image'
  if (mime.startsWith('video/')) return 'video'
  if (mime.startsWith('audio/')) return 'audio'
  return 'other'
})

const uploaderName = computed(() => {
  const u = props.media?.uploaded_by
  if (!u) return '—'
  return u.nickname || u.username || `#${u.id}`
})

const createdLabel = computed(() => {
  const raw = props.media?.created_at
  if (!raw) return '—'
  const d = new Date(raw)
  return Number.isNaN(d.getTime()) ? raw : d.toLocaleString()
})

function formatSize(bytes: number): string {
  if (!bytes || bytes <= 0) return '0 B'
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  const mb = kb / 1024
  if (mb < 1024) return `${mb.toFixed(1)} MB`
  return `${(mb / 1024).toFixed(2)} GB`
}

function absoluteUrl(): string {
  const raw = props.media?.url || ''
  if (!raw) return ''
  try {
    return new URL(raw, window.location.origin).href
  } catch {
    return raw
  }
}

async function copyUrl() {
  const url = absoluteUrl()
  if (!url) return
  try {
    await navigator.clipboard.writeText(url)
    toast.success(t('admin.media.previewCopied', '链接已复制到剪贴板'))
  } catch {
    toast.error(t('admin.media.previewCopyFailed', '复制失败，请手动选择链接复制'))
  }
}

/**
 * PUT /media/library/{id} 接受 JSON body { title, alt_text, description }
 * （后端 update_media：三个 Body(None) 字段，非 None 即更新，传 '' 可清空）。
 */
async function save() {
  if (!props.media) return
  saving.value = true
  try {
    await apiFetch(`/media/library/${props.media.id}`, {
      method: 'PUT',
      body: {
        title: form.title.trim(),
        alt_text: form.alt_text.trim(),
        description: form.description.trim()
      }
    })
    toast.success(t('admin.media.previewSaved', '媒体信息已更新'))
    emit('updated', {
      id: props.media.id,
      title: form.title.trim(),
      alt_text: form.alt_text.trim(),
      description: form.description.trim()
    })
  } catch {
    // 错误已由 apiFetch 统一 toast
  } finally {
    saving.value = false
  }
}
</script>
