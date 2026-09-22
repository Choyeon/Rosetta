<template>
  <div class="min-h-screen bg-background">
    <!-- Header -->
    <header class="border-b border-border/60">
      <div class="container py-14 md:py-20 text-center">
        <h1 class="font-display text-4xl md:text-5xl font-bold tracking-tight text-foreground">
          {{ t('gallery.title') }}
        </h1>
        <p class="text-muted-foreground mt-4 text-base md:text-lg leading-relaxed max-w-2xl mx-auto">
          {{ t('gallery.desc') }}
        </p>
      </div>
    </header>

    <!-- Album Grid -->
    <section class="container py-12 md:py-16">
      <!-- Skeleton -->
      <div
        v-if="pending && albums.length === 0"
        class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        <div
          v-for="i in 6"
          :key="i"
          class="rounded-xl overflow-hidden border border-border/60 bg-card animate-pulse"
        >
          <div class="aspect-[4/3] bg-muted" />
          <div class="p-5 flex flex-col gap-3">
            <div class="w-1/3 h-5 rounded bg-muted" />
            <div class="w-full h-3.5 rounded bg-muted" />
          </div>
        </div>
      </div>

      <!-- Albums -->
      <div
        v-else-if="albums.length > 0"
        class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        <article
          v-for="album in albums"
          :key="album.id"
          class="group rounded-xl overflow-hidden border border-border/60 bg-card shadow-sm hover:shadow-lg transition-all duration-300 cursor-pointer"
          @click="openAlbum(album.id)"
        >
          <div class="relative aspect-[4/3] overflow-hidden bg-muted">
            <img
              v-if="album.cover"
              :src="album.cover"
              :alt="album.title"
              class="size-full object-cover transition-transform duration-500 ease-out group-hover:scale-105"
              loading="lazy"
            >
            <div
              v-else
              class="size-full flex items-center justify-center bg-muted"
            >
              <Images class="size-12 text-muted-foreground/40" />
            </div>
            <div class="absolute top-3 left-3">
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/60 text-white text-xs font-medium backdrop-blur-sm">
                <ImageIcon class="size-3.5" />
                {{ album.photosCount }}
              </span>
            </div>
          </div>
          <div class="p-5">
            <h3 class="font-display text-lg font-semibold tracking-tight truncate group-hover:text-primary transition-colors">
              {{ album.title }}
            </h3>
            <p class="text-sm text-muted-foreground mt-1.5 line-clamp-2 leading-relaxed min-h-[2.5rem]">
              {{ album.description || t('gallery.noDesc') }}
            </p>
          </div>
        </article>
      </div>

      <!-- Empty -->
      <div
        v-else
        class="text-center py-24"
      >
        <div class="inline-flex items-center justify-center size-20 rounded-2xl bg-muted mb-6">
          <Images class="size-10 text-muted-foreground" />
        </div>
        <h3 class="font-display text-xl font-semibold">
          {{ t('gallery.noAlbums') }}
        </h3>
        <p class="text-muted-foreground mt-2 text-sm">
          {{ t('gallery.hint') }}
        </p>
      </div>
    </section>

    <!-- Album Detail Dialog -->
    <Dialog v-model:open="dialogOpen">
      <DialogContent
        class="sm:max-w-5xl w-[95vw] max-h-[90vh] p-0 flex flex-col gap-0 overflow-hidden"
      >
        <!-- Header -->
        <div class="shrink-0 p-6 border-b border-border/60">
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0">
              <DialogTitle class="font-display text-2xl font-bold tracking-tight truncate">
                {{ currentAlbum?.title }}
              </DialogTitle>
              <DialogDescription class="mt-1 text-sm text-muted-foreground line-clamp-2">
                {{ currentAlbum?.description || '' }}
              </DialogDescription>
            </div>
            <Badge
              variant="secondary"
              class="shrink-0"
            >
              <ImageIcon class="size-3.5 mr-1" />
              {{ currentAlbum?.photosCount }} {{ t('gallery.photos') }}
            </Badge>
          </div>
        </div>

        <!-- Photos -->
        <ScrollArea class="flex-1 min-h-0">
          <div class="p-6">
            <!-- Loading -->
            <div
              v-if="albumLoading && currentPhotos.length === 0"
              class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4"
            >
              <div
                v-for="i in 8"
                :key="i"
                class="aspect-square rounded-lg bg-muted animate-pulse"
              />
            </div>

            <!-- Photos with viewerjs -->
            <div
              v-else-if="currentPhotos.length > 0"
              ref="viewerContainerRef"
              class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4"
            >
              <img
                v-for="(photo, idx) in currentPhotos"
                :key="idx"
                :src="photo"
                :data-original="photo"
                :alt="`${currentAlbum?.title || ''} ${idx + 1}`"
                class="aspect-square w-full object-cover rounded-lg cursor-zoom-in hover:opacity-90 transition-opacity shadow-sm"
                loading="lazy"
              >
            </div>

            <!-- Empty -->
            <div
              v-else
              class="text-center py-16"
            >
              <Images class="size-12 text-muted-foreground/40 mx-auto mb-3" />
              <p class="text-muted-foreground text-sm">
                {{ t('noData') }}
              </p>
            </div>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onBeforeUnmount, nextTick } from 'vue'
import { Badge } from '~~/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '~~/components/ui/dialog'
import { ScrollArea } from '~~/components/ui/scroll-area'
import { useI18n } from 'vue-i18n'
import { Images as ImageIcon, Image as Images } from '@lucide/vue'
import { useAPI, apiFetch as apiFetchDirect } from '~~/composables/useApi'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()

// viewerjs 懒加载
type ViewerModule = typeof import('viewerjs')
let ViewerCtor: ViewerModule['default'] | null = null
let viewerCssInjected = false

async function ensureViewer(): Promise<ViewerModule['default'] | null> {
  if (!import.meta.client) return null
  if (!ViewerCtor) {
    try {
      const mod = await import(/* @vite-ignore */ 'viewerjs' as string) as ViewerModule & { default: ViewerModule['default'] }
      ViewerCtor = (mod.default ?? mod) as ViewerModule['default']
    } catch {
      return null
    }
  }
  if (!viewerCssInjected) {
    try {
      await import('viewerjs/dist/viewer.css')
    } catch {
      /* noop */
    }
    viewerCssInjected = true
  }
  return ViewerCtor
}

// --- Types ---
interface Album {
  id: number
  title: string
  description: string
  cover: string
  photosCount: number
  photos: string[]
  loaded: boolean
}

interface AlbumResp {
  id: number
  title: string
  description?: string
  cover?: string
  photo_count?: number
}

// --- State ---
const albums = reactive<Album[]>([])
const dialogOpen = ref(false)
const activeAlbumId = ref<number | null>(null)
const albumLoading = ref(false)
const viewerContainerRef = ref<HTMLElement | null>(null)
let viewerInstance: { destroy: () => void } | null = null

const currentAlbum = computed(() =>
  albums.find(a => a.id === activeAlbumId.value) ?? null
)
const currentPhotos = computed(() => currentAlbum.value?.photos ?? [])

// 拉取相册列表
const { data: albumsResp, pending } = useAPI<{ items: AlbumResp[], total?: number }>(
  '/gallery/albums',
  {
    query: { page: 1, page_size: 50, lang: locale }
  }
)

watch(
  [albumsResp],
  () => {
    const items = (albumsResp.value?.items || []) as AlbumResp[]
    const existingMap = new Map(albums.map(a => [a.id, a]))
    albums.splice(
      0,
      albums.length,
      ...items.map((raw) => {
        const prev = existingMap.get(raw.id)
        return {
          id: raw.id,
          title: raw.title || '',
          description: raw.description || '',
          cover: raw.cover || '',
          photosCount: typeof raw.photo_count === 'number' ? raw.photo_count : (prev?.photosCount ?? 0),
          photos: prev?.photos ?? [],
          loaded: prev?.loaded ?? false
        }
      })
    )
  },
  // useAPI 返回的 data ref 是整体替换（非深 mutate），无需 deep:true
  // 避免 Vue 递归遍历整个 albums 树造成不必要的 CPU 开销
  { immediate: true }
)

// 加载相册详情
async function loadAlbumDetail(id: number) {
  const album = albums.find(a => a.id === id)
  if (!album || album.loaded || albumLoading.value) return
  albumLoading.value = true
  try {
    const raw = await apiFetchDirect<unknown>(`/gallery/albums/${id}`, {
      query: { lang: locale.value }
    })
    const unwrapped
      = raw && typeof raw === 'object' && 'data' in raw
        ? (raw as { data?: unknown }).data
        : raw
    const data = (unwrapped ?? {}) as Record<string, unknown>
    const photosArr = Array.isArray(data.photos) ? data.photos : []
    album.photos = photosArr
      .map((p) => {
        const obj = (p ?? {}) as Record<string, unknown>
        return typeof obj.url === 'string' ? obj.url : ''
      })
      .filter(Boolean) as string[]
    album.loaded = true
    const photoCount = data.photo_count
    if (typeof photoCount === 'number') album.photosCount = photoCount
    const cover = data.cover
    if (!album.cover && typeof cover === 'string') album.cover = cover
  } catch {
    /* noop */
  } finally {
    albumLoading.value = false
  }
}

// 打开相册
function openAlbum(id: number) {
  activeAlbumId.value = id
  dialogOpen.value = true
  nextTick(() => {
    loadAlbumDetail(id).then(() => {
      nextTick(() => initViewer())
    })
  })
}

// 初始化 viewerjs
async function initViewer() {
  if (!import.meta.client) return
  const el = viewerContainerRef.value
  if (!el) return

  // 销毁旧实例
  if (viewerInstance) {
    try {
      viewerInstance.destroy()
    } catch {
      /* noop */
    }
    viewerInstance = null
  }

  const Ctor = await ensureViewer()
  if (!Ctor) return

  // 确保 DOM 中 img 已渲染
  await nextTick()
  if (!el.isConnected) return
  if (el.querySelectorAll('img').length === 0) return

  try {
    viewerInstance = new Ctor(el, {
      toolbar: {
        zoomIn: 1,
        zoomOut: 1,
        oneToOne: 1,
        reset: 1,
        prev: 1,
        play: { show: 1, size: 'large' },
        next: 1,
        rotateLeft: 1,
        rotateRight: 1,
        flipHorizontal: 1,
        flipVertical: 1
      },
      navbar: true,
      title: false,
      tooltip: true,
      movable: true,
      zoomable: true,
      rotatable: true,
      scalable: true,
      transition: true,
      fullscreen: true,
      keyboard: true,
      backdrop: true,
      loop: true,
      interval: 3500,
      zIndex: 10000,
      zoomOnWheel: true,
      zoomOnTouch: true,
      slideOnTouch: true,
      toggleOnDblclick: true,
      loading: true
    })
  } catch {
    viewerInstance = null
  }
}

// Dialog 关闭时销毁 viewer
watch(dialogOpen, (open) => {
  if (!open) {
    if (viewerInstance) {
      try {
        viewerInstance.destroy()
      } catch {
        /* noop */
      }
      viewerInstance = null
    }
  }
})

onBeforeUnmount(() => {
  if (viewerInstance) {
    try {
      viewerInstance.destroy()
    } catch {
      /* noop */
    }
    viewerInstance = null
  }
})

// SEO
useSeo({
  title: computed(() => (t('gallery.title') as string) || '相册'),
  description: computed(() => t('gallery.desc') as string),
  type: 'website'
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home', '首页') as string, url: '/' },
  { name: t('nav.gallery', '相册') as string, url: '/gallery' }
])
</script>
