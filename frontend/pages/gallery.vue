<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-gradient-to-br from-rose-100 to-pink-100 dark:from-rose-900/30 dark:to-pink-900/30 mb-5">
        <Images class="size-7 text-primary" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('gallery.title') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('gallery.desc') }}
      </p>
      <p class="text-xs text-muted-foreground/80 mt-3">
        点击任意图片可放大查看，支持键盘 ← → 翻页、滚轮缩放、全屏、旋转。
      </p>
    </header>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="album in albums"
        :key="album.id"
      >
        <Card
          class="h-full group transition-all hover:shadow-soft hover:-translate-y-0.5 duration-300 overflow-hidden cursor-pointer"
          @click="openAlbum = album.id"
        >
          <div class="relative aspect-[4/3] overflow-hidden bg-muted">
            <img
              :src="album.cover"
              :alt="album.title"
              class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
              loading="lazy"
            >
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
                {{ album.description }} · {{ album.photosCount }} {{ t('gallery.photos') }} · 点击图片可放大
              </SheetDescription>
            </SheetHeader>
            <ScrollArea class="flex-1">
              <div class="p-6">
                <div
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
                      :data-original="getHighRes(photo)"
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
                  {{ album.description }}
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
                  :data-original="getHighRes(photo)"
                  :alt="`${album.title} ${idx + 1}`"
                  class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-110"
                  loading="lazy"
                >
                <div class="absolute bottom-1.5 right-1.5 size-5 rounded-full bg-black/60 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                  <ZoomIn class="size-3" />
                </div>
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>

    <div
      v-if="albums.length === 0"
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
import Viewer from 'viewerjs'
import 'viewerjs/dist/viewer.css'

definePageMeta({ layout: 'default' })

const { t } = useI18n()

// --- viewer.js lightbox instances per container key -------------------------
type ViewerInstance = InstanceType<typeof Viewer>
interface ViewerRecord { instance: ViewerInstance, element: WeakRef<Element> }
const viewerRegistry = new Map<string, ViewerRecord>()

const setGalleryRef = (key: string, el: Element | null) => {
  // Skip server-side and no-ops
  if (!import.meta.client) return
  const existing = viewerRegistry.get(key)
  if (existing) {
    const oldEl = existing.element.deref?.()
    if (el && oldEl === el) return
    try {
      existing.instance.destroy()
    } catch { /* noop */ }
    viewerRegistry.delete(key)
  }
  if (!el) return
  // Images inside may still be loading but Viewer only needs DOM present; it reads src on show
  // delay one tick so children finish their rendering (avoids first render empty img list)
  nextTick(() => {
    if (!el.isConnected) return
    const instance = new Viewer(el as HTMLElement, {
      // Use data-original (hi-res URL that user set) when available, fall back to src
      url(image: HTMLImageElement) {
        return image.dataset.original || image.src
      },
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
      minWidth: 320,
      minHeight: 240,
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

/** Upgrade thumbnail (w=400 q=75) → hi-res viewer image (w=1600 q=85) for Unsplash URLs. */
const getHighRes = (url: string) => {
  if (!url) return ''
  try {
    const u = new URL(url)
    if (u.hostname.includes('unsplash.com')) {
      u.searchParams.set('w', '1600')
      u.searchParams.set('q', '85')
      return u.toString()
    }
    return url
  } catch {
    return url
  }
}

onBeforeUnmount(() => {
  for (const r of viewerRegistry.values()) {
    try {
      r.instance.destroy()
    } catch { /* noop */ }
  }
  viewerRegistry.clear()
})

// --- Sheet + album data -----------------------------------------------------
const openAlbum = ref<number | null>(null)
const localSheetOpen = reactive<Record<number, boolean>>({})

watch(openAlbum, (id) => {
  if (id !== null) {
    localSheetOpen[id] = true
    nextTick(() => {
      openAlbum.value = null
    })
  }
})

interface Album {
  id: number
  title: string
  description: string
  cover: string
  photosCount: number
  photos: string[]
}

const coverImages = [
  'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80',
  'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800&q=80',
  'https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?w=800&q=80',
  'https://images.unsplash.com/photo-1433086966358-54859d0ed716?w=800&q=80',
  'https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=800&q=80',
  'https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=800&q=80'
]

const photoImages = [
  'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400&q=75',
  'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=400&q=75',
  'https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?w=400&q=75',
  'https://images.unsplash.com/photo-1433086966358-54859d0ed716?w=400&q=75',
  'https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=400&q=75',
  'https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=400&q=75',
  'https://images.unsplash.com/photo-1500534623283-312aade485b7?w=400&q=75',
  'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=400&q=75',
  'https://images.unsplash.com/photo-1475924156734-496f6cac6ec1?w=400&q=75',
  'https://images.unsplash.com/photo-1426604966848-d7adac402bff?w=400&q=75',
  'https://images.unsplash.com/photo-1490750967868-88aa4486c946?w=400&q=75',
  'https://images.unsplash.com/photo-1465146344425-f00d5f5c8f07?w=400&q=75'
]

const generatePhotos = (count: number, startIdx: number = 0) => {
  const result: string[] = []
  for (let i = 0; i < count; i++) {
    result.push(photoImages[(startIdx + i) % photoImages.length] ?? '')
  }
  return result
}

const albums = ref<Album[]>([
  {
    id: 1,
    title: '川西环线',
    description: '十月深秋的稻城亚丁与色达，雪山、红草地与金幡的记忆。',
    cover: coverImages[0] ?? '',
    photosCount: 48,
    photos: generatePhotos(8, 0)
  },
  {
    id: 2,
    title: '北海道の冬',
    description: '小樽运河的雪灯、札幌的啤酒博物馆、函馆的百万夜景。',
    cover: coverImages[1] ?? '',
    photosCount: 36,
    photos: generatePhotos(6, 3)
  },
  {
    id: 3,
    title: '日常街拍',
    description: '通勤路上、咖啡馆的午后，那些不经意间的光影切片。',
    cover: coverImages[2] ?? '',
    photosCount: 72,
    photos: generatePhotos(9, 5)
  },
  {
    id: 4,
    title: '海岸线',
    description: '从深圳到青岛，沿着东部海岸线追逐的每一次日出日落。',
    cover: coverImages[3] ?? '',
    photosCount: 24,
    photos: generatePhotos(6, 8)
  },
  {
    id: 5,
    title: '工位随拍',
    description: '机械键盘、屏幕光、深夜的黑咖啡，写代码人的仪式感。',
    cover: coverImages[4] ?? '',
    photosCount: 18,
    photos: generatePhotos(6, 10)
  },
  {
    id: 6,
    title: '植物笔记',
    description: '阳台上的多肉、公司楼下的银杏、旅途中遇到的奇花异草。',
    cover: coverImages[5] ?? '',
    photosCount: 30,
    photos: generatePhotos(6, 2)
  }
])
</script>
