<!--
  相册页（SSR 列表 + 客户端懒取详情）：列表 useAPI('/gallery/albums') 按 ?page=N 分页
  （每页 12，后端 page_size 上限 100），第 2 页起有真实 <a href> 入口；越界页码 SSR 期 301
  回裸相册页（200 空页会被判 soft 404，且自指 canonical 等于承认垃圾页码是独立页面）。
  点开才用 apiFetch('/gallery/albums/{id}') 取照片，靠 Album.loaded + albumLoading 双守卫防重复请求。
  详情响应可能是 {data} 信封（手工解包），photos 只取字符串 url 项、其余过滤掉，故"有照片数却空网格"是脏数据表现。
  viewerjs 只在点开相册时动态 import（ViewerCtor / viewerCssInjected 缓存，import 失败即静默降级为
  纯图片网格、无灯箱）；实例必须在 initViewer 重入、Dialog 关闭、组件卸载三处 destroy，否则灯箱浮层残留。
-->

<template>
  <div class="min-h-svh bg-background">
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
          class="rounded-xl overflow-hidden border border-border/60 bg-card"
        >
          <Skeleton class="aspect-[4/3] rounded-none" />
          <div class="p-5 flex flex-col gap-3">
            <Skeleton class="w-1/3 h-5 rounded" />
            <Skeleton class="w-full h-3.5 rounded" />
          </div>
        </div>
      </div>

      <!-- Albums -->
      <template v-else-if="albums.length > 0">
        <!-- 「点击图片可放大」只在真的有图可点时出现：上一版把它写在空态里，
             屏幕上于是同时存在「还没有上传相册」和「点击任意图片可放大查看」两句互相矛盾的话。 -->
        <p class="mb-4 text-center text-xs text-muted-foreground">
          {{ t('gallery.hint') }}
        </p>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <article
            v-for="album in albums"
            :key="album.id"
            class="group rounded-xl overflow-hidden border border-border/60 bg-card shadow-sm hover:shadow-lg transition-all duration-300 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            role="button"
            tabindex="0"
            :aria-label="t('gallery.openAlbum', { title: album.title })"
            @click="openAlbum(album.id)"
            @keydown.enter.prevent="openAlbum(album.id)"
            @keydown.space.prevent="openAlbum(album.id)"
          >
            <div class="relative aspect-[4/3] overflow-hidden bg-muted">
              <img
                v-if="album.cover"
                :src="album.cover"
                :alt="album.title"
                width="800"
                height="600"
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
      </template>

      <!-- Load failed：与"没有相册"分开 -->
      <div
        v-else-if="albumsError"
        class="text-center py-24"
      >
        <div class="inline-flex items-center justify-center size-20 rounded-2xl bg-muted mb-6">
          <AlertCircle class="size-10 text-muted-foreground" />
        </div>
        <h3 class="font-display text-xl font-semibold">
          {{ t('gallery.loadFailed') }}
        </h3>
        <Button
          variant="outline"
          class="mt-4"
          @click="refreshAlbums()"
        >
          <RefreshCw data-icon="inline-start" />
          {{ t('common.retry') }}
        </Button>
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
      </div>
    </section>

    <!-- 分页：此前列表固定 page_size=50 且没有翻页入口，第 51 张之后的相册
         在站内没有任何可达路径。链接必须是真实 <a href>——SSR HTML 里的 href
         是无 JS 访客与爬虫唯一的翻页入口；click 仍走 handlePageChange 保留 SPA 行为。 -->
    <nav
      v-if="totalPages > 1"
      class="container pb-14 flex items-center justify-center gap-2"
      role="navigation"
      aria-label="pagination"
    >
      <template v-if="currentPage <= 1">
        <Button
          variant="outline"
          size="icon"
          disabled
          :aria-label="t('common.prevPage', '上一页')"
        >
          <ChevronLeft data-icon="inline-start" />
        </Button>
      </template>
      <a
        v-else
        :href="pageHref(currentPage - 1)"
        :aria-label="t('common.prevPage', '上一页')"
        :class="pageLinkClass('outline')"
        @click.prevent="handlePageChange(currentPage - 1)"
      >
        <ChevronLeft data-icon="inline-start" />
      </a>
      <template
        v-for="page in visiblePages"
        :key="page"
      >
        <span
          v-if="page === currentPage"
          aria-current="page"
          :class="pageLinkClass('default')"
        >{{ page }}</span>
        <a
          v-else
          :href="pageHref(page)"
          :class="pageLinkClass('ghost')"
          @click.prevent="handlePageChange(page)"
        >{{ page }}</a>
      </template>
      <template v-if="currentPage >= totalPages">
        <Button
          variant="outline"
          size="icon"
          disabled
          :aria-label="t('common.nextPage', '下一页')"
        >
          <ChevronRight data-icon="inline-start" />
        </Button>
      </template>
      <a
        v-else
        :href="pageHref(currentPage + 1)"
        :aria-label="t('common.nextPage', '下一页')"
        :class="pageLinkClass('outline')"
        @click.prevent="handlePageChange(currentPage + 1)"
      >
        <ChevronRight data-icon="inline-start" />
      </a>
    </nav>

    <!-- Album Detail Dialog -->
    <!-- ClientOnly：reka DialogRoot 在 SSR 产物里因双 vue 实例渲染成空注释节点
         （见 nuxt.config nitro 段注释），而客户端 DialogRoot 渲染 fragment，
         水合时触发页面根部的节点级 mismatch。Dialog 只响应点击打开，
         无需参与 SSR 首帧，整体推迟到客户端挂载。 -->
    <ClientOnly>
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
                <Skeleton
                  v-for="i in 8"
                  :key="i"
                  class="aspect-square rounded-lg"
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
                  width="800"
                  height="800"
                  class="aspect-square w-full object-cover rounded-lg cursor-zoom-in hover:opacity-90 transition-opacity shadow-sm"
                  loading="lazy"
                >
              </div>

              <!-- Empty -->
              <div
                v-else
                class="text-center py-16"
              >
                <template v-if="detailError">
                  <AlertCircle class="size-12 text-destructive/60 mx-auto mb-3" />
                  <p class="text-sm text-muted-foreground mb-4">
                    {{ t('common.error') }}
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    @click="retryDetail"
                  >
                    <RefreshCw data-icon="inline-start" />
                    {{ t('common.retry') }}
                  </Button>
                </template>
                <template v-else>
                  <Images class="size-12 text-muted-foreground/40 mx-auto mb-3" />
                  <p class="text-muted-foreground text-sm">
                    {{ t('common.noData') }}
                  </p>
                </template>
              </div>
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </ClientOnly>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onBeforeUnmount, nextTick } from 'vue'
import { Badge } from '~~/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '~~/components/ui/dialog'
import { ScrollArea } from '~~/components/ui/scroll-area'
import { useI18n } from 'vue-i18n'
import { Images as ImageIcon, Image as Images, AlertCircle, RefreshCw, ChevronLeft, ChevronRight } from '@lucide/vue'
import { Button, buttonVariants } from '~~/components/ui/button'
import { useAPI, apiFetch as apiFetchDirect } from '~~/composables/useApi'
import { pageWindow } from '~~/lib/pagination'

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
/** 详情请求失败与「相册本来就没照片」必须区分：后者不是错误 */
const detailError = ref(false)
const viewerContainerRef = ref<HTMLElement | null>(null)
let viewerInstance: { destroy: () => void } | null = null

const currentAlbum = computed(() =>
  albums.find(a => a.id === activeAlbumId.value) ?? null
)
const currentPhotos = computed(() => currentAlbum.value?.photos ?? [])

// 每页 12 = 3 列网格 × 4 行；后端 page_size 只认 1–100，越界即 422。
const PAGE_SIZE = 12
const route = useRoute()
const router = useRouter()
// 初始页码从 URL 读：分享 / 刷新 / 后退都要能还原；只接受正整数，垃圾值回第 1 页。
const currentPage = ref(Math.max(1, Number(route.query.page) || 1))
const requestedPage = Math.max(1, Number(route.query.page) || 1)

// 拉取相册列表
// error 必须单独渲染：后端故障时 albums 是空数组，走 v-else 会显示
// "还没有相册"——访客据此判定站主没上传照片，而真实情况只是这次请求挂了。
const { data: albumsResp, pending, error: albumsError, refresh: refreshAlbums } = useAPI<{ items: AlbumResp[], total?: number, total_pages?: number }>(
  '/gallery/albums',
  {
    // query 用 computed：currentPage / locale 变化时 Nuxt 的 params watcher 自动重取，
    // 不手写 watch + refresh（那会与自动重取双发，第一发还被 abort）。
    query: computed(() => ({ page: currentPage.value, page_size: PAGE_SIZE, lang: locale.value }))
  }
)

const totalAlbums = computed(() => albumsResp.value?.total ?? 0)
const totalPages = computed(
  () => albumsResp.value?.total_pages ?? (Math.ceil(totalAlbums.value / PAGE_SIZE) || 1)
)
const visiblePages = computed(() => pageWindow(currentPage.value, totalPages.value))
const pageHref = (page: number) => `${applyLocalePrefix('/gallery', locale.value)}?page=${page}`
const pageLinkClass = (variant: 'default' | 'outline' | 'ghost') =>
  buttonVariants({ variant, size: 'icon' })

const handlePageChange = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  if (import.meta.client) {
    router.replace({ query: page > 1 ? { page: String(page) } : {} })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

// 分享链接上的页码可能已越界（比如相册被删掉一批）：拉回来再请求，
// 否则访客拿到"第 9 页，共 3 页"的空网格且无从自救。
watch([totalAlbums, currentPage], () => {
  if (totalAlbums.value === 0) return
  if (currentPage.value > totalPages.value) currentPage.value = totalPages.value
})

// 越界页码对爬虫必须 301 回裸相册页：留 200 会被判 soft 404，且自指 canonical
// 等于承认每个垃圾页码都是独立页面。时点与 useContentStatus 同轨（app:rendered：
// 数据已落值、状态码还改得动）；响应头必须 no-store，否则 301 会被本页 swr 缓存。
if (import.meta.server) {
  const ssrEvent = useRequestEvent()
  useNuxtApp().hooks.hookOnce('app:rendered', () => {
    if (ssrEvent && totalAlbums.value > 0 && requestedPage > totalPages.value) {
      ssrEvent.node.res.statusCode = 301
      ssrEvent.node.res.setHeader('location', applyLocalePrefix('/gallery', locale.value))
      ssrEvent.node.res.setHeader('cache-control', 'no-store')
    }
  })
}

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
  } catch (err) {
    // 不能静默：失败的表现是「点了相册，对话框里一直转圈然后空空如也」，
    // 详情页没有任何别的提示渠道，必须显式给一个错误态。
    detailError.value = true
    console.error('[gallery] 相册详情加载失败', id, err)
  } finally {
    albumLoading.value = false
  }
}

/** 重试：清掉 loaded 守卫，否则 loadAlbumDetail 会直接短路返回 */
function retryDetail() {
  const album = albums.find(a => a.id === activeAlbumId.value)
  if (!album) return
  detailError.value = false
  album.loaded = false
  void loadAlbumDetail(album.id).then(() => nextTick(() => initViewer()))
}

// 打开相册
function openAlbum(id: number) {
  activeAlbumId.value = id
  detailError.value = false
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

// 空目录页 = 没有可索引内容（与 /sponsor 的 sponsorEmpty 同口径），后端 sitemap 同步跳过。
// 判据用接口给的 total（= 已发布相册数），不用本地拼接的 albums：翻到空页不等于目录为空。
// 只在「确实取到 0 个相册」时 noindex：加载中或请求失败仍保持可索引——一次网络故障不该把
// 有内容的目录页从索引里摘掉，而本页 600s swr 会把判错的结果缓存十分钟。
const galleryEmpty = computed(
  () => !pending.value && !albumsError.value && totalAlbums.value === 0
)

// SEO
useSeo({
  title: computed(() => (t('gallery.title') as string) || '相册'),
  description: computed(() => t('gallery.desc') as string),
  type: 'website',
  noindex: galleryEmpty
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home', '首页') as string, url: '/' },
  { name: t('nav.gallery', '相册') as string, url: '/gallery' }
])
</script>
