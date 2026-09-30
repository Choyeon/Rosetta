<!--
  相册管理页：左侧相册列表 + 右侧照片网格，含相册/照片 CRUD、封面裁剪、上传、排序与批量删除。
  契约：相册封面的字段名是 cover 且传 null 即清空封面；thumbnail_url 是不落库的透传字段，封面必须用 original_url/url。
  快速切换相册时须用序号守卫丢弃迟到响应防照片串台；并发上传逐张建 AdminPhoto，sort_order 需单调游标 + Media.id 幂等键，避免撞权重/重复行。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="相册管理"
      description="按相册组织图片，便于前台画廊展示"
      :icon="Images"
    />

    <div class="grid grid-cols-1 md:grid-cols-[280px_1fr] gap-6">
      <div class="card-surface overflow-hidden flex flex-col max-h-[calc(100vh-220px)]">
        <div class="p-3 border-b">
          <Button
            class="w-full"
            @click="openCreateAlbum"
          >
            <Plus data-icon="inline-start" />
            新建相册
          </Button>
        </div>
        <ScrollArea class="flex-1">
          <div
            v-if="albumsLoading"
            class="flex flex-col gap-3 p-3"
          >
            <div
              v-for="i in 6"
              :key="i"
              class="h-16 rounded-lg"
            >
              <Skeleton class="h-full w-full rounded-lg" />
            </div>
          </div>

          <div
            v-else-if="albumsError"
            class="p-4 text-center"
          >
            <Alert variant="destructive">
              <AlertCircle class="size-4" />
              <AlertTitle>相册加载失败</AlertTitle>
              <AlertDescription>请检查网络后重试</AlertDescription>
              <Button
                variant="outline"
                size="sm"
                class="mt-3"
                @click="fetchAlbums"
              >
                <RefreshCw data-icon="inline-start" />
                重试
              </Button>
            </Alert>
          </div>

          <div
            v-else-if="!albums.length"
            class="p-6 text-center"
          >
            <p class="text-sm text-muted-foreground">
              暂无相册，点击上方按钮创建
            </p>
          </div>

          <div
            v-else
            class="flex flex-col gap-1 p-2"
          >
            <div
              v-for="a in albums"
              :key="a.id"
              :class="[
                'group rounded-lg p-2 cursor-pointer transition-all border',
                selectedAlbumId === a.id
                  ? 'bg-primary/10 border-primary'
                  : 'border-transparent hover:bg-muted/50'
              ]"
              role="button"
              tabindex="0"
              :aria-label="`打开相册 ${plainText(a.title)}`"
              @click="selectAlbum(a.id)"
              @keydown="onAlbumKeydown($event, a.id)"
            >
              <div class="flex items-start gap-3">
                <div class="size-14 rounded-lg overflow-hidden shrink-0 bg-muted">
                  <img
                    v-if="a.cover_url"
                    :src="a.cover_url"
                    :alt="plainText(a.title)"
                    class="size-full object-cover"
                  >
                  <div
                    v-else
                    class="size-full flex items-center justify-center"
                  >
                    <ImageIcon class="size-6 text-muted-foreground" />
                  </div>
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-start justify-between gap-2">
                    <div class="min-w-0">
                      <p class="text-sm font-medium truncate">
                        {{ plainText(a.title) }}
                      </p>
                      <p class="text-xs text-muted-foreground mt-0.5">
                        {{ a.photos_count || 0 }} 张
                      </p>
                    </div>
                    <div class="opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity flex items-center gap-0.5 shrink-0">
                      <Button
                        variant="ghost"
                        size="icon"
                        class="h-6 w-6"
                        title="编辑相册"
                        :aria-label="`编辑相册 ${plainText(a.title)}`"
                        @click.stop="openEditAlbum(a)"
                      >
                        <Pencil data-icon="inline-start" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        class="h-6 w-6 text-destructive hover:text-destructive"
                        title="删除相册"
                        :aria-label="`删除相册 ${plainText(a.title)}`"
                        @click.stop="confirmDeleteAlbum(a.id)"
                      >
                        <Trash2 data-icon="inline-start" />
                      </Button>
                    </div>
                  </div>
                  <div class="flex items-center gap-1 mt-1">
                    <Lock
                      v-if="!a.is_public"
                      class="size-3 text-muted-foreground"
                    />
                    <Globe
                      v-else
                      class="size-3 text-success"
                    />
                    <span class="text-xs text-muted-foreground">{{ a.is_public ? '公开' : '私密' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </ScrollArea>
      </div>

      <!-- 右侧：当前相册的照片管理 -->
      <div class="card-surface p-4 min-h-[calc(100vh-220px)]">
        <template v-if="!selectedAlbumId">
          <div class="h-full flex items-center justify-center py-20">
            <Alert
              variant="info"
              class="max-w-md"
            >
              <Info class="size-4" />
              <AlertTitle>请选择一个相册</AlertTitle>
              <AlertDescription>从左侧列表选择或创建一个相册来管理照片</AlertDescription>
            </Alert>
          </div>
        </template>

        <template v-else>
          <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
            <div>
              <h2 class="text-lg font-semibold">
                {{ currentAlbumTitle }}
              </h2>
              <p class="text-xs text-muted-foreground mt-0.5">
                共 {{ photos.length }} 张照片
                <span
                  v-if="selectedIds.length"
                  class="text-primary ml-2"
                >
                  · 已选 {{ selectedIds.length }} 张
                </span>
              </p>
            </div>
            <div class="flex items-center gap-2">
              <Button
                v-if="selectedIds.length"
                variant="destructive"
                size="sm"
                @click="confirmBatchDelete"
              >
                <Trash2 data-icon="inline-start" />
                删除选中 ({{ selectedIds.length }})
              </Button>
              <Button
                v-if="selectedIds.length"
                variant="outline"
                size="sm"
                @click="clearSelection"
              >
                取消选择
              </Button>
              <Button
                variant="outline"
                size="sm"
                @click="uploadDialogOpen = true"
              >
                <Upload data-icon="inline-start" />
                上传照片
              </Button>
            </div>
          </div>

          <div
            v-if="photosLoading"
            class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4"
          >
            <div
              v-for="i in 8"
              :key="i"
              class="flex flex-col gap-2"
            >
              <Skeleton class="aspect-square w-full rounded-xl" />
              <Skeleton class="h-3 w-full rounded" />
            </div>
          </div>

          <!-- 加载失败：与「相册为空」区分开，否则用户以为照片丢了 -->
          <div
            v-else-if="photosError"
            class="py-16 text-center"
          >
            <Alert
              variant="destructive"
              class="max-w-md mx-auto"
            >
              <AlertCircle class="size-4" />
              <AlertTitle>照片加载失败</AlertTitle>
              <AlertDescription>无法获取该相册的照片，请检查网络后重试</AlertDescription>
              <Button
                variant="outline"
                size="sm"
                class="mt-3"
                @click="retryFetchPhotos"
              >
                <RefreshCw data-icon="inline-start" />
                重试
              </Button>
            </Alert>
          </div>

          <div
            v-else-if="!photos.length"
            class="py-16 text-center"
          >
            <Alert
              variant="info"
              class="max-w-md mx-auto"
            >
              <ImageIcon class="size-4" />
              <AlertTitle>相册为空</AlertTitle>
              <AlertDescription>点击右上角"上传照片"按钮添加照片</AlertDescription>
            </Alert>
          </div>

          <div
            v-else
            class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4"
          >
            <div
              v-for="(p, idx) in photos"
              :key="p.id"
              :class="[
                'group relative rounded-xl border bg-card overflow-hidden shadow-sm transition-shadow duration-200 hover:shadow-md', // panel-exempt: 图片缩略图瓦片，整块被 object-cover 铺满；card-surface 的渐变面/内发光在几十个格子上只剩噪点
                selectedIds.includes(p.id) ? 'ring-2 ring-primary' : ''
              ]"
            >
              <!-- aspect-square 容器 + object-cover：加载前后占位一致，防 CLS；hover 仅阴影/透明度，无缩放位移 -->
              <div class="aspect-square bg-muted relative overflow-hidden">
                <img
                  :src="photoSrc(p)"
                  :alt="plainText(p.title) || 'photo'"
                  class="size-full object-cover cursor-zoom-in transition-opacity duration-200 group-hover:opacity-90"
                  loading="lazy"
                  decoding="async"
                  @click="openLightbox(idx)"
                >

                <!-- 选择框：button 语义保证键盘可聚焦；非 hover 时用 focus-within 保持可见 -->
                <button
                  type="button"
                  class="absolute top-2 left-2 size-5 rounded border-2 border-white bg-black/30 flex items-center justify-center cursor-pointer transition-opacity"
                  :class="selectedIds.includes(p.id) ? 'opacity-100 bg-primary border-primary' : 'opacity-0 group-hover:opacity-100 focus-visible:opacity-100'"
                  :aria-label="`${selectedIds.includes(p.id) ? '取消选择' : '选择'}照片 ${photoFilename(p)}`"
                  :aria-pressed="selectedIds.includes(p.id)"
                  @click.stop="toggleSelect(p.id)"
                >
                  <Check
                    v-if="selectedIds.includes(p.id)"
                    class="size-3 text-white"
                  />
                </button>

                <div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity flex items-center gap-1">
                  <Button
                    variant="outline"
                    size="icon"
                    class="h-7 w-7 backdrop-blur-sm bg-background/70"
                    title="设为封面"
                    :aria-label="`设为封面：${photoFilename(p)}`"
                    :disabled="!photoFullSrc(p) || coverSetting"
                    @click.stop="setAsCover(p)"
                  >
                    <Star data-icon="inline-start" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    class="h-7 w-7 backdrop-blur-sm bg-background/70"
                    title="编辑"
                    :aria-label="`编辑照片 ${photoFilename(p)}`"
                    @click.stop="openEditPhoto(p)"
                  >
                    <Pencil data-icon="inline-start" />
                  </Button>
                  <Button
                    variant="destructive"
                    size="icon"
                    class="h-7 w-7 backdrop-blur-sm"
                    title="删除"
                    :aria-label="`删除照片 ${photoFilename(p)}`"
                    @click.stop="confirmDeletePhoto(p.id)"
                  >
                    <Trash2 data-icon="inline-start" />
                  </Button>
                </div>

                <div class="absolute bottom-2 left-2 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity flex items-center gap-1">
                  <Button
                    variant="outline"
                    size="icon"
                    class="h-6 w-6 backdrop-blur-sm bg-background/70"
                    :disabled="idx === 0 || sorting"
                    title="前移"
                    :aria-label="`前移照片 ${photoFilename(p)}`"
                    @click.stop="movePhoto(p, 'up')"
                  >
                    <ChevronUp data-icon="inline-start" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    class="h-6 w-6 backdrop-blur-sm bg-background/70"
                    :disabled="idx === photos.length - 1 || sorting"
                    title="后移"
                    :aria-label="`后移照片 ${photoFilename(p)}`"
                    @click.stop="movePhoto(p, 'down')"
                  >
                    <ChevronDown data-icon="inline-start" />
                  </Button>
                </div>

                <div class="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/60 to-transparent p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <p class="text-xs text-white truncate">
                    {{ plainText(p.title) || photoFilename(p) }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <Dialog v-model:open="albumFormOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{ editingAlbumId ? '编辑相册' : '新建相册' }}</DialogTitle>
          <DialogDescription>{{ editingAlbumId ? '修改相册信息' : '创建一个新的相册' }}</DialogDescription>
        </DialogHeader>
        <div class="flex flex-col gap-4 py-2">
          <div class="flex flex-col gap-2">
            <Label for="album-title-input">标题 <span class="text-destructive">*</span></Label>
            <Input
              id="album-title-input"
              v-model="albumForm.title"
              placeholder="相册标题"
            />
          </div>
          <div class="flex flex-col gap-2">
            <Label for="album-desc-input">描述</Label>
            <Textarea
              id="album-desc-input"
              v-model="albumForm.description"
              :rows="3"
              placeholder="相册描述（可选）..."
              class="resize-none"
            />
          </div>
          <div class="flex flex-col gap-2">
            <Label>封面图</Label>
            <div class="flex items-center gap-3">
              <div class="size-20 rounded-lg border-2 border-dashed bg-muted overflow-hidden shrink-0">
                <img
                  v-if="albumForm.cover_url"
                  :src="albumForm.cover_url"
                  alt="cover"
                  class="size-full object-cover"
                >
                <div
                  v-else
                  class="size-full flex items-center justify-center"
                >
                  <ImageIcon class="size-6 text-muted-foreground" />
                </div>
              </div>
              <div class="flex flex-col gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  @click="coverCropperOpen = true"
                >
                  <Crop data-icon="inline-start" />
                  上传并裁剪封面
                </Button>
                <Button
                  v-if="albumForm.cover_url"
                  variant="ghost"
                  size="sm"
                  class="text-muted-foreground"
                  @click="clearCover"
                >
                  <X data-icon="inline-start" />
                  清除封面
                </Button>
                <p class="text-xs text-muted-foreground">
                  推荐 16:9 比例；未设置时前台自动用相册首张照片
                </p>
              </div>
            </div>
          </div>
          <div class="flex flex-col gap-2">
            <Label for="album-sort-input">排序权重</Label>
            <Input
              id="album-sort-input"
              v-model.number="albumForm.sort_order"
              type="number"
              min="0"
              step="1"
              class="w-32"
            />
            <p class="text-xs text-muted-foreground">
              数值越小越靠前，前台相册列表按此升序展示
            </p>
          </div>
          <div class="flex items-center justify-between rounded-xl border p-3">
            <div>
              <div class="text-sm font-medium">
                公开相册
              </div>
              <div class="text-xs text-muted-foreground">
                所有人可见
              </div>
            </div>
            <Switch
              v-model="albumForm.is_public"
              aria-label="公开相册"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="ghost"
            @click="albumFormOpen = false"
          >
            取消
          </Button>
          <Button
            :disabled="albumSubmitting"
            @click="submitAlbum"
          >
            <Loader2
              v-if="albumSubmitting"
              data-icon="inline-start"
              class="animate-spin"
            />
            {{ editingAlbumId ? '保存修改' : '创建相册' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="coverCropperOpen">
      <DialogContent class="max-w-2xl">
        <DialogHeader>
          <DialogTitle>裁剪封面图</DialogTitle>
          <DialogDescription>选择区域作为相册封面，推荐 16:9 比例</DialogDescription>
        </DialogHeader>
        <ImageCropper
          v-if="coverCropperSrc"
          ref="coverCropperRef"
          :src="coverCropperSrc"
          :aspect-ratio="16 / 9"
          :aspect-ratios="[
            { label: '16:9', value: 16 / 9 },
            { label: '4:3', value: 4 / 3 },
            { label: '1:1', value: 1 },
            { label: '自由', value: null }
          ]"
          :output-width="1280"
        />
        <input
          ref="coverFileInputRef"
          type="file"
          accept="image/*"
          class="hidden"
          @change="onCoverFileSelected"
        >
        <div
          v-if="!coverCropperSrc"
          class="py-12 text-center"
        >
          <Button
            variant="outline"
            @click="coverFileInputRef?.click()"
          >
            <Upload data-icon="inline-start" />
            选择图片
          </Button>
        </div>
        <DialogFooter>
          <Button
            variant="ghost"
            @click="coverCropperOpen = false"
          >
            取消
          </Button>
          <Button
            :disabled="!coverCropperSrc"
            @click="confirmCoverCrop"
          >
            <Check data-icon="inline-start" />
            确认裁剪
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="photoEditOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>编辑照片</DialogTitle>
          <DialogDescription>修改照片标题和描述</DialogDescription>
        </DialogHeader>
        <div class="flex flex-col gap-4 py-2">
          <div class="rounded-lg overflow-hidden bg-muted">
            <img
              v-if="editingPhoto"
              :src="photoSrc(editingPhoto)"
              :alt="editingPhoto.title || '照片预览'"
              class="w-full max-h-60 object-contain"
            >
          </div>
          <div class="flex flex-col gap-2">
            <Label for="photo-title-input">标题</Label>
            <Input
              id="photo-title-input"
              v-model="photoForm.title"
              placeholder="照片标题（可选）"
            />
          </div>
          <div class="flex flex-col gap-2">
            <Label for="photo-desc-input">描述</Label>
            <Textarea
              id="photo-desc-input"
              v-model="photoForm.description"
              :rows="3"
              placeholder="照片描述（可选）..."
              class="resize-none"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="ghost"
            @click="photoEditOpen = false"
          >
            取消
          </Button>
          <Button
            :disabled="photoSubmitting"
            @click="submitPhotoEdit"
          >
            <Loader2
              v-if="photoSubmitting"
              data-icon="inline-start"
              class="animate-spin"
            />
            保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="uploadDialogOpen">
      <DialogContent class="max-w-2xl">
        <DialogHeader>
          <DialogTitle>上传照片</DialogTitle>
          <DialogDescription>拖拽或点击上传，图片将自动压缩优化</DialogDescription>
        </DialogHeader>
        <ImageUploadZone
          category="gallery"
          @uploaded="onUploaded"
          @error="(m: string) => toast.error(m)"
        />
        <DialogFooter>
          <Button
            variant="ghost"
            @click="closeUploadDialog"
          >
            关闭
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <AdminConfirmDialog
      v-model:open="deleteAlbumDialogOpen"
      title="确认删除相册"
      description="删除后该相册及其所有照片将无法恢复，确定继续吗？"
      confirm-text="确认删除"
      :on-confirm="doDeleteAlbum"
    />

    <AdminConfirmDialog
      v-model:open="deletePhotoDialogOpen"
      title="确认删除照片"
      description="删除后该照片将无法恢复，确定继续吗？"
      confirm-text="确认删除"
      :on-confirm="doDeletePhoto"
    />

    <AdminConfirmDialog
      v-model:open="batchDeleteDialogOpen"
      title="批量删除照片"
      confirm-text="确认删除"
      :on-confirm="doBatchDelete"
    >
      <template #description>
        将删除选中的 <span class="font-medium text-destructive">{{ selectedIds.length }}</span> 张照片，确定继续吗？
      </template>
    </AdminConfirmDialog>

    <ImageLightbox
      v-model:open="lightboxOpen"
      :images="lightboxImages"
      :initial-index="lightboxIndex"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onBeforeUnmount, watch } from 'vue'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Switch } from '~~/components/ui/switch'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '~~/components/ui/dialog'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import { ScrollArea } from '~~/components/ui/scroll-area'
import { Label } from '~~/components/ui/label'
import ImageCropper from '~~/components/ImageCropper.vue'
import ImageUploadZone from '~~/components/ImageUploadZone.vue'
import ImageLightbox from '~~/components/ImageLightbox.vue'
import {
  Plus, Image as ImageIcon, Pencil, Trash2, Upload, Info, Loader2,
  Lock, Globe, ChevronUp, ChevronDown, Images, Star, Check, Crop,
  AlertCircle, RefreshCw, X
} from '@lucide/vue'
import {
  fetchAdminAlbums,
  createAdminAlbum,
  updateAdminAlbum,
  deleteAdminAlbum,
  fetchAdminPhotos,
  createAdminPhoto,
  updateAdminPhoto,
  deleteAdminPhoto,
  deleteAdminPhotosBatch,
  type AdminAlbum,
  type AdminPhoto
} from '~~/composables/useAdminManage'
import { useMediaUploadCover } from '~~/composables/useMedia'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const albumsLoading = ref(false)
const albumsError = ref(false)
const photosLoading = ref(false)
const photosError = ref(false)
const albumSubmitting = ref(false)
const photoSubmitting = ref(false)

const albums = shallowRef<AdminAlbum[]>([])
const photos = shallowRef<AdminPhoto[]>([])
const selectedAlbumId = ref<number | null>(null)
const selectedIds = ref<number[]>([])

const currentAlbumTitle = computed(() => {
  const a = albums.value.find(x => x.id === selectedAlbumId.value)
  return a ? plainText(a.title) : ''
})

const albumFormOpen = ref(false)
const editingAlbumId = ref<number | null>(null)
const albumForm = reactive({
  title: '',
  description: '',
  cover_url: '',
  sort_order: 0,
  is_public: true
})

const coverCropperOpen = ref(false)
const coverCropperSrc = ref('')
const coverCropperRef = ref<InstanceType<typeof ImageCropper> | null>(null)
const coverFileInputRef = ref<HTMLInputElement | null>(null)

const photoEditOpen = ref(false)
const editingPhoto = ref<AdminPhoto | null>(null)
const photoForm = reactive({ title: '', description: '' })

// 上传对话框的 ImageUploadZone 负责压缩与逐文件上传，本页只在 uploaded 事件里建 AdminPhoto
const uploadDialogOpen = ref(false)

const deleteAlbumDialogOpen = ref(false)
const deleteAlbumTargetId = ref<number | null>(null)
const deletePhotoDialogOpen = ref(false)
const deletePhotoTargetId = ref<number | null>(null)
const batchDeleteDialogOpen = ref(false)

// 排序 / 设为封面的进行中标志：连点会打出交错的 PUT，后一次的入参已过期
const sorting = ref(false)
const coverSetting = ref(false)

/**
 * 相册/照片的文案字段在后端是 String/Text 明文列，类型上也已收窄成 `string | null`。
 * 这里只做 null 兜底，不再处理 i18n dict——那个分支从来跑不到，留着只会让人以为
 * 相册标题支持多语言。
 */
function plainText(v: string | null | undefined): string {
  return v ?? ''
}

/** original_url 在后端响应模型里可空（thumbnail_url 甚至不落库），不能直接当字符串用 */
function photoSrc(p: AdminPhoto): string {
  return p.thumbnail_url || photoFullSrc(p) || ''
}

/** 封面必须用原图地址：thumbnail_url 只是透传字段，不会写库，拿它当封面会丢图 */
function photoFullSrc(p: AdminPhoto): string {
  return p.original_url || p.url || ''
}

function photoFilename(p: AdminPhoto): string {
  const src = photoSrc(p)
  if (!src) return '未命名'
  return src.split('/').pop() || '未命名'
}

const lightboxOpen = ref(false)
const lightboxIndex = ref(0)
// 与 photos 一一对应：网格点哪个就是第几张，这里不能过滤/压缩索引
const lightboxImages = computed(() =>
  photos.value.map(p => ({
    url: photoFullSrc(p),
    title: plainText(p.title) || photoFilename(p)
  }))
)

let albumsSeq = 0
async function fetchAlbums() {
  const seq = ++albumsSeq
  albumsLoading.value = true
  albumsError.value = false
  try {
    const res = await fetchAdminAlbums({ page: 1, page_size: 100 })
    if (seq !== albumsSeq) return
    albums.value = res.items ?? []
  } catch {
    // 失败提示由 apiFetch 统一 toast，此处只做错误态兜底（与「暂无相册」区分）
    if (seq !== albumsSeq) return
    albumsError.value = true
    albums.value = []
  } finally {
    if (seq === albumsSeq) albumsLoading.value = false
  }
}

let photosSeq = 0
async function fetchPhotosFor(id: number) {
  const seq = ++photosSeq
  photosLoading.value = true
  photosError.value = false
  selectedIds.value = []
  try {
    const data = await fetchAdminPhotos(id)
    // 快速切换相册时旧请求可能后到达：仅当仍是当前相册才写回，避免照片串台
    if (seq !== photosSeq || selectedAlbumId.value !== id) return
    photos.value = (data?.items ?? [])
      .slice()
      .sort((a, b) => (Number(a.sort_order) || 0) - (Number(b.sort_order) || 0))
  } catch {
    // 失败提示由 apiFetch 统一 toast，此处只做错误态兜底（与「相册为空」区分）
    if (seq !== photosSeq || selectedAlbumId.value !== id) return
    photosError.value = true
    photos.value = []
  } finally {
    if (seq === photosSeq && selectedAlbumId.value === id) photosLoading.value = false
  }
}

function retryFetchPhotos() {
  if (selectedAlbumId.value) fetchPhotosFor(selectedAlbumId.value)
}

function selectAlbum(id: number) {
  // 再次点击当前相册也要能刷新（失败后没有别的重试入口），所以不做同 id 短路
  selectedAlbumId.value = id
  photos.value = []
  fetchPhotosFor(id)
}

/**
 * 相册行是 div[role=button]，Enter/Space 需手动补键激活；
 * 只响应焦点落在行本身的按键，避免行内编辑/删除按钮冒泡误触发切换。
 */
function onAlbumKeydown(ev: KeyboardEvent, id: number) {
  if (ev.target !== ev.currentTarget) return
  if (ev.key === 'Enter' || ev.key === ' ') {
    ev.preventDefault()
    selectAlbum(id)
  }
}

function openCreateAlbum() {
  editingAlbumId.value = null
  // 默认权重放在当前最大值之后：新相册出现在列表末尾而不是插在最前面，
  // 与「sort_order 升序」的前台口径一致
  const nextOrder = albums.value.reduce((m, a) => Math.max(m, Number(a.sort_order) || 0), 0) + 1
  Object.assign(albumForm, {
    title: '',
    description: '',
    cover_url: '',
    sort_order: nextOrder,
    is_public: true
  })
  albumFormOpen.value = true
}

function openEditAlbum(a: AdminAlbum) {
  editingAlbumId.value = a.id
  Object.assign(albumForm, {
    title: plainText(a.title),
    description: plainText(a.description),
    cover_url: a.cover_url || '',
    sort_order: Number(a.sort_order) || 0,
    is_public: a.is_public
  })
  albumFormOpen.value = true
}

/** 清除封面：只是把表单里的值置空，真正落到后端要等到提交（cover: null） */
function clearCover() {
  albumForm.cover_url = ''
}

/** coverCropperSrc 是 blob: URL，必须由本页面回收（对话框开关多次即泄漏多次） */
function resetCoverCropper() {
  if (coverCropperSrc.value?.startsWith('blob:')) URL.revokeObjectURL(coverCropperSrc.value)
  coverCropperSrc.value = ''
  if (coverFileInputRef.value) coverFileInputRef.value.value = ''
}

watch(coverCropperOpen, (open) => {
  if (!open) resetCoverCropper()
})

function onCoverFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    toast.error('封面只能是图片文件')
    input.value = ''
    return
  }
  resetCoverCropper()
  coverCropperSrc.value = URL.createObjectURL(file)
}

async function confirmCoverCrop() {
  if (!coverCropperRef.value) return
  const file = await coverCropperRef.value.getCroppedFile('cover.jpg', 'image/jpeg', 0.9)
  if (!file) {
    toast.error('裁剪失败')
    return
  }
  try {
    const res = await useMediaUploadCover(file)
    if (res?.url) {
      albumForm.cover_url = res.url
      toast.success('封面裁剪上传成功')
      // 关闭对话框即触发 watch 回收 blob 与重置 file input
      coverCropperOpen.value = false
    } else {
      // 后端 200 但没回 url：属于异常响应，必须显式报错，不能静默
      toast.error('封面上传失败：响应未返回文件地址')
    }
  } catch {
    // 上传失败提示由 apiFetch 统一 toast，此处不重复弹错
  }
}

async function submitAlbum() {
  if (!albumForm.title.trim()) {
    toast.warning('请填写标题')
    return
  }
  albumSubmitting.value = true
  const payload: Record<string, unknown> = {
    title: albumForm.title.trim(),
    description: albumForm.description.trim() || null,
    cover: albumForm.cover_url || null,
    // NaN 来自清空 number input；后端 sort_order 是 ge=0 的 int，透传 NaN 会 422
    sort_order: Number.isFinite(albumForm.sort_order) ? Math.max(0, Math.trunc(albumForm.sort_order)) : 0,
    is_published: albumForm.is_public
  }
  try {
    if (editingAlbumId.value) {
      await updateAdminAlbum(editingAlbumId.value, payload)
      toast.success('修改成功')
    } else {
      const created = await createAdminAlbum(payload)
      toast.success('创建成功')
      // 后端异常响应（无 id）时不能把 undefined 写进 selectedAlbumId
      if (created?.id) selectedAlbumId.value = created.id
    }
    albumFormOpen.value = false
    await fetchAlbums()
    if (selectedAlbumId.value) fetchPhotosFor(selectedAlbumId.value)
  } catch {
    // 错误已 toast
  } finally {
    albumSubmitting.value = false
  }
}

function confirmDeleteAlbum(id: number) {
  deleteAlbumTargetId.value = id
  deleteAlbumDialogOpen.value = true
}

async function doDeleteAlbum() {
  const id = deleteAlbumTargetId.value
  if (id === null) return
  await deleteAdminAlbum(id)
  toast.success('相册已删除')
  if (selectedAlbumId.value === id) {
    selectedAlbumId.value = null
    photos.value = []
  }
  deleteAlbumTargetId.value = null
  fetchAlbums()
}

function closeUploadDialog() {
  uploadDialogOpen.value = false
}

/**
 * ImageUploadZone 每成功上传一个文件就 emit 一次 uploaded（只带这一项）。
 * 并发完成时 photos.value 还是旧快照，用它算 sort_order 会让多张撞同一个权重值，
 * 所以这里维护一个单调游标；Media.id 作幂等键，避免重复事件建出重复行。
 */
const addedMediaKeys = new Set<string>()
let orderCursor = 0
const uploadTally = { success: 0, failed: 0 }
let settleTimer: ReturnType<typeof setTimeout> | null = null

function nextSortOrder(): number {
  const maxExisting = photos.value.reduce((m, p) => Math.max(m, Number(p.sort_order) || 0), 0)
  orderCursor = Math.max(orderCursor, maxExisting) + 1
  return orderCursor
}

/** 多张并发完成时只报一次汇总、只重拉一次列表 */
function scheduleUploadSettle() {
  if (settleTimer) clearTimeout(settleTimer)
  settleTimer = setTimeout(async () => {
    settleTimer = null
    const { success, failed } = uploadTally
    uploadTally.success = 0
    uploadTally.failed = 0
    if (!success && !failed) return
    // 具体的失败原因已由 apiFetch 逐条 toast，这里只给一条汇总，不再复述错误
    if (!failed) toast.success(`上传完成：成功 ${success} 张`)
    else toast.warning(`上传完成：成功 ${success} 张，失败 ${failed} 张`)
    if (success && selectedAlbumId.value) await fetchPhotosFor(selectedAlbumId.value)
  }, 600)
}

async function onUploaded(items: unknown[]) {
  const albumId = selectedAlbumId.value
  if (!albumId) {
    // 没选相册就上传：文件已经进媒体库，必须说明去哪找，不能静默丢弃
    if (items.length) toast.error('请先选择相册再上传照片，文件已保留在媒体库中')
    return
  }
  for (const raw of items) {
    const media = raw as { id?: number, url?: string, original_name?: string, title?: string }
    if (!media?.url) {
      uploadTally.failed++
      continue
    }
    const key = String(media.id ?? media.url)
    if (addedMediaKeys.has(key)) continue
    addedMediaKeys.add(key)
    const order = nextSortOrder()
    try {
      await createAdminPhoto({
        album_id: albumId,
        title: (media.original_name || media.title || `照片 ${order}`).slice(0, 200),
        url: media.url,
        sort_order: order
      })
      uploadTally.success++
    } catch {
      // 单张失败不中断（apiFetch 已逐张 toast）；释放幂等键允许重试
      addedMediaKeys.delete(key)
      uploadTally.failed++
    }
  }
  scheduleUploadSettle()
}

function openEditPhoto(p: AdminPhoto) {
  editingPhoto.value = p
  photoForm.title = plainText(p.title)
  photoForm.description = plainText(p.description)
  photoEditOpen.value = true
}

async function submitPhotoEdit() {
  if (!editingPhoto.value) return
  photoSubmitting.value = true
  try {
    await updateAdminPhoto(editingPhoto.value.id, {
      title: photoForm.title.trim() || null,
      description: photoForm.description.trim() || null
    })
    toast.success('保存成功')
    photoEditOpen.value = false
    if (selectedAlbumId.value) fetchPhotosFor(selectedAlbumId.value)
  } catch {
    // 错误已 toast
  } finally {
    photoSubmitting.value = false
  }
}

async function setAsCover(p: AdminPhoto) {
  const albumId = selectedAlbumId.value
  if (!albumId || coverSetting.value) return
  const url = photoFullSrc(p)
  if (!url) {
    // 传 null 会被后端当成「清空封面」，不能还给用户报成功
    toast.error('该照片没有可用的图片地址，无法设为封面')
    return
  }
  coverSetting.value = true
  try {
    await updateAdminAlbum(albumId, { cover: url })
    toast.success('已设为封面')
    await fetchAlbums()
  } catch {
    // 失败提示由 apiFetch 统一 toast，此处不重复弹错
  } finally {
    coverSetting.value = false
  }
}

function toggleSelect(id: number) {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}

function clearSelection() {
  selectedIds.value = []
}

function confirmBatchDelete() {
  if (!selectedIds.value.length) return
  batchDeleteDialogOpen.value = true
}

async function doBatchDelete() {
  const ids = [...selectedIds.value]
  // 不提前关弹窗：AdminConfirmDialog 在回调 resolve 后统一关闭，期间按钮保持 loading
  try {
    const res = await deleteAdminPhotosBatch(ids)
    const deleted = res?.deleted_count ?? ids.length
    const missing = res?.missing_ids ?? []
    if (missing.length) {
      toast.warning(`已删除 ${deleted} 张，${missing.length} 张记录已不存在`)
    } else {
      toast.success(`已删除 ${deleted} 张照片`)
    }
  } catch {
    // apiFetch 已弹出错误 toast；此处保留弹窗与选择，用户可重试
    return
  }
  if (selectedAlbumId.value !== null) {
    await Promise.all([fetchPhotosFor(selectedAlbumId.value), fetchAlbums()])
  }
}

function confirmDeletePhoto(id: number) {
  deletePhotoTargetId.value = id
  deletePhotoDialogOpen.value = true
}

async function doDeletePhoto() {
  const id = deletePhotoTargetId.value
  if (id === null) return
  await deleteAdminPhoto(id)
  toast.success('照片已删除')
  deletePhotoTargetId.value = null
  if (selectedAlbumId.value) fetchPhotosFor(selectedAlbumId.value)
}

async function movePhoto(p: AdminPhoto, dir: 'up' | 'down') {
  if (sorting.value) return
  const idx = photos.value.findIndex(x => x.id === p.id)
  if (idx < 0) return
  const swapIdx = dir === 'up' ? idx - 1 : idx + 1
  if (swapIdx < 0 || swapIdx >= photos.value.length) return
  const adjacent = photos.value[swapIdx]!
  const mine = Number(p.sort_order) || 0
  const theirs = Number(adjacent.sort_order) || 0
  const albumId = p.album_id || selectedAlbumId.value
  sorting.value = true
  try {
    if (mine === theirs) {
      // 权重相同（历史脏数据 / 并发上传撞号）时两两交换写入的值一模一样，
      // 点按钮没反应 —— 只能按交换后的视觉顺序整体重排权重
      const next = photos.value.slice()
      next[idx] = adjacent
      next[swapIdx] = p
      const ops = next
        .map((x, i) => ({ id: x.id, want: i, have: Number(x.sort_order) || 0 }))
        .filter(x => x.have !== x.want)
      await Promise.all(ops.map(x => updateAdminPhoto(x.id, { sort_order: x.want })))
    } else {
      await Promise.all([
        updateAdminPhoto(p.id, { sort_order: theirs }),
        updateAdminPhoto(adjacent.id, { sort_order: mine })
      ])
    }
  } catch {
    // 失败提示由 apiFetch 统一 toast，这里只负责把视图拉回服务端的真实顺序
  } finally {
    if (albumId) await fetchPhotosFor(albumId)
    sorting.value = false
  }
}

function openLightbox(idx: number) {
  if (idx < 0 || idx >= lightboxImages.value.length) return
  lightboxIndex.value = idx
  lightboxOpen.value = true
}

onBeforeUnmount(() => {
  if (settleTimer) {
    clearTimeout(settleTimer)
    settleTimer = null
  }
  if (coverCropperSrc.value?.startsWith('blob:')) URL.revokeObjectURL(coverCropperSrc.value)
})

onMounted(fetchAlbums)
</script>
