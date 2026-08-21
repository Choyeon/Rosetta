<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-primary/10 mb-5">
        <Images class="size-7 text-primary" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('gallery.title') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('gallery.desc') }}
      </p>
      <p class="text-xs text-muted-foreground/80 mt-3">
        {{ t('gallery.hint') || '点击任意图片可放大查看。' }}
      </p>
    </header>

    <div
      v-if="pending && albums.length === 0"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
    >
      <div
        v-for="i in 6"
        :key="i"
        class="rounded-xl overflow-hidden border border-border/60 bg-card animate-pulse"
      >
        <div class="aspect-[4/3] bg-muted" />
        <div class="p-5 space-y-3">
          <div class="flex justify-between">
            <div class="w-2/5 h-5 rounded-full bg-muted" />
            <div class="w-16 h-4 rounded-full bg-muted" />
          </div>
          <div class="space-y-2">
            <div class="w-full h-3.5 rounded-full bg-muted" />
            <div class="w-3/4 h-3.5 rounded-full bg-muted" />
          </div>
        </div>
      </div>
    </div>

    <div
      v-else
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
    >
      <div
        v-for="album in albums"
        :key="album.id"
      >
        <Card
          class="h-full group transition-all hover:shadow-soft hover:-translate-y-0.5 duration-300 overflow-hidden cursor-pointer"
          @click="openAlbumSheet(album.id)"
        >
          <div class="relative aspect-[4/3] overflow-hidden bg-muted">
            <img
              v-if="album.cover"
              :src="album.cover"
              :alt="album.title"
              class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
              loading="lazy"
            >
            <div
              v-else
              class="w-full h-full bg-gradient-to-br from-primary/20 via-muted to-muted"
            />
            <div class="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
            <div class="absolute bottom-3 left-3 right-3 flex items-center justify-between">
              <Badge
                variant="secondary"
                class="bg-white/90 dark:bg-black/50 backdrop-blur-sm border-0"
              >
                <ImageIcon class="size-3 mr-1.5" />
                {{ album.photosCount }} {{ t('gallery.photos') }}
              </Badge>
            </div>
          </div>
          <CardHeader class="p-5">
            <div class="flex items-center justify-between mb-2">
              <CardTitle class="font-display text-lg tracking-tight group-hover:underline underline-offset-4">
                {{ album.title }}
              </CardTitle>
              <ChevronRight class="size-4 text-muted-foreground transition-transform duration-300 group-hover:translate-x-0.5" />
            </div>
            <CardDescription class="line-clamp-2 text-sm leading-relaxed min-h-[2.5rem]">
              {{ album.description || t('gallery.noDesc') }}
            </CardDescription>
          </CardHeader>
        </Card>

        <Sheet v-model:open="localSheetOpen[album.id]">
          <SheetContent
            side="right"
            class="w-full sm:max-w-3xl p-0 flex flex-col"
          >
            <SheetHeader class="p-6 pb-4 border-b shrink-0">
              <SheetTitle class="font-display text-xl flex items-center gap-2">
                <ImageIcon class="size-5 text-primary" />
                {{ album.title }}
              </SheetTitle>
              <SheetDescription class="mt-1">
                {{ album.description || '' }} · {{ album.photosCount }} {{ t('gallery.photos') }} · {{ t('gallery.clickToZoom') || '点击图片可放大' }}
              </SheetDescription>
            </SheetHeader>
            <ScrollArea class="flex-1">
              <div class="p-6">
                <div
                  v-if="albumsDetailLoading[album.id] && (album.photos || []).length === 0"
                  class="grid grid-cols-2 sm:grid-cols-3 gap-3"
                >
                  <div
                    v-for="i in 6"
                    :key="i"
                    class="aspect-square rounded-xl bg-muted animate-pulse"
                  />
                </div>
                <div
                  v-else
                  :ref="(el: any) => setGalleryRef(`sheet-${album.id}`, el)"
                  class="grid grid-cols-2 sm:grid-cols-3 gap-3 viewer-photos-grid"
                >
                  <div
                    v-for="(photo, idx) in album.photos"
                    :key="idx"
                    class="group relative aspect-square rounded-xl overflow-hidden bg-muted cursor-zoom-in shadow-sm hover:shadow-md transition-shadow"
                  >
                    <img
                      :src="photo"
                      :data-original="photo"
                      :alt="`${album.title} ${idx + 1}`"
                      class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-110"
                      loading="lazy"
                    >
                    <div class="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors duration-300" />
                    <div class="absolute bottom-2 right-2 size-7 rounded-full bg-black/60 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                      <ZoomIn class="size-4" />
                    </div>
                  </div>
                </div>
              </div>
            </ScrollArea>
          </SheetContent>
        </Sheet>
      </div>
    </div>

    <div class="mt-12">
      <Accordion
        type="multiple"
        class="w-full space-y-4"
      >
        <AccordionItem
          v-for="album in albums"
          :key="`acc-${album.id}`"
          :value="`album-${album.id}`"
          class="border rounded-xl overflow-hidden px-0"
        >
          <AccordionTrigger class="px-6 py-4 hover:no-underline hover:bg-muted/40 transition-colors">
            <div class="flex items-center gap-4 w-full text-left">
              <div class="size-12 shrink-0 rounded-lg overflow-hidden bg-muted">
                <img
                  v-if="album.cover"
                  :src="album.cover"
                  :alt="album.title"
                  class="w-full h-full object-cover"
                  loading="lazy"
                >
              </div>
              <div class="flex-1 min-w-0">
                <div class="font-medium">
                  {{ album.title }}
                </div>
                <div class="text-sm text-muted-foreground truncate">
                  {{ album.description || t('gallery.noDesc') }}
                </div>
              </div>
              <Badge
                variant="secondary"
                class="shrink-0"
              >
                {{ album.photosCount }}
              </Badge>
            </div>
          </AccordionTrigger>
          <AccordionContent class="px-6 pb-6">
            <div
              v-if="albumsDetailLoading[album.id] && (album.photos || []).length === 0"
              class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 pt-2"
            >
              <div
                v-for="i in 6"
                :key="i"
                class="aspect-square rounded-lg bg-muted animate-pulse"
              />
            </div>
            <div
              v-else
              :ref="(el: any) => setGalleryRef(`acc-${album.id}`, el)"
              class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 pt-2 viewer-photos-grid"
            >
              <div
                v-for="(photo, idx) in album.photos"
                :key="`acc-${album.id}-${idx}`"
                class="group relative aspect-square rounded-lg overflow-hidden bg-muted cursor-zoom-in shadow-sm hover:shadow-md transition-shadow"
              >
                <img
                  :src="photo"
                  :data-original="photo"
                  :alt="`${album.title} ${idx + 1}`"
                  class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-110"
                  loading="lazy"
                >
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>

    <div
      v-if="!pending && albums.length === 0"
      class="text-center py-20"
    >
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <Images class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">
        {{ t('gallery.noAlbums') }}
      </h3>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, nextTick } from 'vue'
import { Card, CardDescription, CardHeader, CardTitle } from '~~/components/ui/card'
import { Badge } from '~~/components/ui/badge'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '~~/components/ui/sheet'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger
} from '~~/components/ui/accordion'
import { ScrollArea } from '~~/components/ui/scroll-area'
import { useI18n } from 'vue-i18n'
import { Images as ImageIcon, ChevronRight, Image as Images, ZoomIn } from '@lucide/vue'
import { useAPI, apiFetch as apiFetchDirect } from '~~/composables/useApi'
import Viewer from 'viewerjs'
import 'viewerjs/dist/viewer.css'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()

// Viewer.js instances per container key
type ViewerInstance = InstanceType<typeof Viewer>
interface ViewerRecord { instance: ViewerInstance, element: WeakRef<Element> }
const viewerRegistry = new Map<string, ViewerRecord>()

const setGalleryRef = (key: string, el: Element | null) => {
  if (!import.meta.client) return
  const existing = viewerRegistry.get(key)
  if (existing) {
    const oldEl = existing.element.deref?.()
    if (el && oldEl === el) return
    try {
      existing.instance.destroy()
    } catch {
      /* noop */
    }
    viewerRegistry.delete(key)
  }
  if (!el) return
  nextTick(() => {
    if (!el.isConnected) return
    const instance = new Viewer(el as HTMLElement, {
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
    viewerRegistry.set(key, { instance, element: new WeakRef(el) })
  })
}

onBeforeUnmount(() => {
  for (const r of viewerRegistry.values()) {
    try {
      r.instance.destroy()
    } catch {
      /* noop */
    }
  }
  viewerRegistry.clear()
})

// --- Data & real API integration -------------------------------------------

interface Album {
  id: number
  title: string
  description: string
  cover: string
  photosCount: number
  photos: string[]
  loaded?: boolean
}

interface AlbumResp {
  id: number
  title: string
  description?: string
  cover?: string
  photo_count?: number
}

interface _AlbumDetailResp extends AlbumResp {
  photos?: Array<{ id: number, url: string, title?: string, description?: string }>
}

interface Paginated<T> {
  items: T[]
  total?: number
  page?: number
  page_size?: number
  total_pages?: number
}

const localSheetOpen = reactive<Record<number, boolean>>({})
const albumsDetailLoading = reactive<Record<number, boolean>>({})

// 真实接口：GET /api/gallery/albums?page=1&page_size=50
const { data: albumsResp, pending } = await useAPI<Paginated<AlbumResp>>('/gallery/albums', {
  query: {
    page: 1,
    page_size: 50,
    lang: locale
  }
})

const albums = reactive<Album[]>([])

const loadAlbumsFromResp = () => {
  const items = (albumsResp.value?.items || []) as AlbumResp[]
  // Merge with existing to preserve loaded photos
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
}
watch([albumsResp], loadAlbumsFromResp, { immediate: true, deep: true })

const loadAlbumDetail = async (id: number) => {
  const album = albums.find(a => a.id === id)
  if (!album) return
  if (album.loaded) return
  if (albumsDetailLoading[id]) return
  albumsDetailLoading[id] = true
  try {
    // 相册详情结构在运行时确定，返回 unknown 以便后续守卫
    const raw = await apiFetchDirect<unknown>(`/gallery/albums/${id}`, {
      query: { lang: locale.value }
    })
    const unwrapped
      = raw && typeof raw === 'object' && 'data' in raw
        ? (raw as { data?: unknown }).data
        : raw
    const data = (unwrapped ?? {}) as Record<string, unknown>
    const photosArr = Array.isArray(data.photos) ? data.photos : []
    const photos = photosArr
      .map((p) => {
        const obj = (p ?? {}) as Record<string, unknown>
        return typeof obj.url === 'string' ? obj.url : ''
      })
      .filter(Boolean) as string[]
    album.photos = photos
    album.loaded = true
    const photoCount = data.photo_count
    if (typeof photoCount === 'number') album.photosCount = photoCount
    const cover = data.cover
    if (!album.cover && typeof cover === 'string') album.cover = cover
  } catch {
    // 失败则保持空列表，后续可重试
  } finally {
    albumsDetailLoading[id] = false
  }
}

const openAlbumSheet = (id: number) => {
  localSheetOpen[id] = true
  nextTick(() => loadAlbumDetail(id))
}

// setGalleryRef 包装：acc-* key 触发相册详情懒加载
const accLoaderKeys = new Set<string>()
const _origSetGalleryRef = setGalleryRef
const setGalleryRefPatched = (key: string, el: Element | null) => {
  if (key.startsWith('acc-')) {
    const id = Number(key.replace('acc-', ''))
    if (!Number.isNaN(id) && !accLoaderKeys.has(key)) {
      accLoaderKeys.add(key)
      loadAlbumDetail(id).catch(() => undefined)
    }
  }
  return _origSetGalleryRef(key, el)
}
// @ts-expect-error 重写 const 函数引用以注入相册详情懒加载，运行时有效
setGalleryRef = setGalleryRefPatched
</script>
