<!--
  相册页（SSR 列表 + 深链详情服务端取数 + 客户端懒取详情）：列表 useAPI('/gallery/albums') 按 ?page=N 分页
  （每页 12，后端 page_size 上限 100），第 2 页起有真实 <a href> 入口；越界页码 SSR 期 301
  回裸相册页（200 空页会被判 soft 404，且自指 canonical 等于承认垃圾页码是独立页面）。
  点开才用 apiFetch('/gallery/albums/{id}') 取照片，靠 Album.loaded + albumLoading 双守卫防重复请求。
  网格是 albumsResp 的纯投影（displayAlbums），取到的详情按 id 覆盖进 loadedAlbums——**不要**改回
  「watch 把列表项搬进一个 reactive 数组」：SSR 期 useFetch 的 data 在 setup 之后才落值，watch 回调不会
  在渲染前 flush，那种写法爬虫只会读到「还没有上传相册」（批次 #128 线上实测：接口回 2 条、HTML 里零链接）。
  「打开哪个相册」的唯一真值是 ?album=<id>（批次 #128）：卡片是真实 <a href>，openAlbum 只改地址栏，
  watch(route.query.album) 才驱动对话框——刷新、后退、中键新标签都还原同一个相册；深链到不在当页的
  相册时详情由 useAsyncData 在服务端取一次并排进网格（首屏与爬虫都读到那张相册，而不是「地址栏有
  相册、HTML 里只有第 1 页」），id 不存在/未公开走 404 分支显式给文案并清参数，
  而不是转圈后一片空白。canonical 只带 page，?album= 进链接图但不承认独立页面（口径见 AGENTS §2.3.3）。
  灯箱里的「第几张」跟着进地址栏（批次 #135：?album=3&photo=7，photo 从 1 起、网格没有第 0 张）：
  分享单张照片与后退键回网格都读这一对参数，灯箱内部状态不是真值；换相册/翻页/关对话框都会把它带走。
  每张照片带 url（原图）+ thumb（后端从 Media.sizes 派生的缩略档，可能为空）：网格下 thumb、灯箱放大 url，
  所以 Viewer 必须显式 url: 'data-original'（viewerjs 默认读 src，不指就会把 150px 小图放到全屏）。
  详情响应可能是 {data} 信封（手工解包），没有原图地址的项直接丢掉，故"有照片数却空网格"是脏数据表现。
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
        v-if="pending && displayAlbums.length === 0"
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
      <template v-else-if="displayAlbums.length > 0">
        <!-- 「点击图片可放大」只在真的有图可点时出现：上一版把它写在空态里，
             屏幕上于是同时存在「还没有上传相册」和「点击任意图片可放大查看」两句互相矛盾的话。 -->
        <p class="mb-4 text-center text-xs text-muted-foreground">
          {{ t('gallery.hint') }}
        </p>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <article
            v-for="album in displayAlbums"
            :key="album.id"
            class="group rounded-xl overflow-hidden border border-border/60 bg-card shadow-sm hover:shadow-lg transition-all duration-300"
          >
            <!-- 真实 <a href>：SSR 里爬虫读到的只有这一份链接图，且访客要能右键新标签打开
                 （上一版是 role="button" + tabindex 的 article，新标签打开只会拿到没有相册的列表页）。
                 点击仍走 openAlbum → 只改 ?album=，由 watch 打开对话框，地址栏与界面不会分叉。 -->
            <a
              :href="albumHref(album.id)"
              class="block cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
              :aria-label="t('gallery.openAlbum', { title: album.title })"
              @click.prevent="openAlbum(album.id)"
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
            </a>
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
                  :key="photo.url"
                  :src="photo.thumb || photo.url"
                  :data-original="photo.url"
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
                <template v-if="albumNotFound">
                  <Images class="size-12 text-muted-foreground/40 mx-auto mb-3" />
                  <p class="text-sm text-muted-foreground mb-4">
                    {{ t('gallery.albumNotFound') }}
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    @click="closeAlbum"
                  >
                    {{ t('common.back') }}
                  </Button>
                </template>
                <template v-else-if="detailError">
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
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
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
const { localeHrefWith } = useLocaleLink()

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
/**
 * 一张照片的两个地址：`url` 是媒体库原图（灯箱与下载的唯一真值），
 * `thumb` 是后端按 Media.sizes 派生的缩略档，可能为 null（外链、SVG、后处理失败）。
 */
interface AlbumPhoto {
  url: string
  thumb: string
}

interface Album {
  id: number
  title: string
  description: string
  cover: string
  photosCount: number
  photos: AlbumPhoto[]
  loaded: boolean
}

/** 详情接口里单张照片的原始形状（thumbnail_url 读取时派生，没有可用档位时后端回 null） */
interface AlbumDetail {
  url?: string | null
  original_url?: string | null
  thumbnail_url?: string | null
}

interface AlbumResp {
  id: number
  title: string
  description?: string
  cover?: string
  photo_count?: number
}

// --- State ---
const dialogOpen = ref(false)
const activeAlbumId = ref<number | null>(null)
/**
 * 点开相册后取到的详情，按 id 存在这里——唯一带 photos / loaded 的源。
 * 网格本身是 albumsResp 的纯投影（下面的 displayAlbums），不是「搬进一个 reactive 数组」：
 * SSR 期 useFetch 的 data 在 setup 之后才落值，watch 回调不会在渲染前 flush，所以靠 watch
 * 填网格的写法会让爬虫永远读到空态（批次 #128 线上实测：接口回 2 条，SSR HTML 里一个相册
 * 链接都没有，只有「还没有上传相册」）。
 */
const loadedAlbums = ref(new Map<number, Album>())
const albumLoading = ref(false)
/** 详情请求失败与「相册本来就没照片」必须区分：后者不是错误 */
const detailError = ref(false)
/** 地址栏带的 id 不存在或未公开（详情 404）：给明确文案，别转圈后一片空白、也别报「操作失败」 */
const albumNotFound = ref(false)
const viewerContainerRef = ref<HTMLElement | null>(null)
let viewerInstance: { destroy: () => void, view: (index: number) => void, hide: () => void } | null = null
/**
 * 灯箱当前停在哪一张（0 基），与地址栏 ?photo= 同源。
 * 留着它是为了挡住「viewed → 写 URL → watch → 再 view」这条自反回路：
 * 值相等就直接返回，灯箱不会被自己反复重开。
 */
let viewerPhotoIndex: number | null = null

// 每页 12 = 3 列网格 × 4 行；后端 page_size 只认 1–100，越界即 422。
const PAGE_SIZE = 12
const route = useRoute()
const router = useRouter()
// 初始页码从 URL 读：分享 / 刷新 / 后退都要能还原；只接受正整数，垃圾值回第 1 页。
const currentPage = ref(Math.max(1, Number(route.query.page) || 1))
const requestedPage = Math.max(1, Number(route.query.page) || 1)

// 拉取相册列表
// error 必须单独渲染：后端故障时 displayAlbums 是空数组，走 v-else 会显示
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

/** 只保留本页真正认识的查询键：垃圾参数不该被复读到下一个链接上 */
const albumQuery = (page: number | null, albumId: number | null = activeAlbumId.value, photo: number | null = null) => {
  const query: Record<string, string> = {}
  if (page !== null && page > 1) query.page = String(page)
  if (albumId !== null) {
    query.album = String(albumId)
    // 序号只在「开着相册」时才有意义：关相册还挂着 ?photo= 等于留一个没人读的照片号，
    // 下一次点开的却是另一个相册。
    if (photo !== null && photo >= 0) query.photo = String(photo + 1)
  }
  return query
}

const handlePageChange = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  if (import.meta.client) {
    // 翻页不带上 ?album：换页意味着换一批相册，继续挂着上一页的相册 id 会让
    // 「地址栏里有相册、界面上开着另一个」分叉；watch 见到空 album 顺手把对话框收掉。
    router.replace({ query: albumQuery(page, null) })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

// 打开哪个相册的唯一真值是 ?album=<id>（批次 #128）。上一版它是纯 ref：刷新即回到列表、
// 后退直接离开相册页、中键"新标签打开"拿到的是一页没有相册的列表（卡片是 role="button"）。
// 现在卡片是真 <a href>，openAlbum 只改地址栏，真正把手交给下面的 watch——界面与 URL 不分叉。
// canonical 仍只带 page（CANONICAL_QUERY_KEYS），所以这些链接进链接图但不承认独立页面。
const albumIdFromQuery = (raw: unknown): number | null => {
  const n = Number(raw)
  return Number.isInteger(n) && n > 0 ? n : null
}
/**
 * 灯箱开在第几张：?photo=<1 起序号> → 0 基下标。
 * 用序号而不是 url：照片对象只有 url/thumb（没有稳定 id），把带域名的地址塞进查询串
 * 既难看又会在相册换图后失效；序号配合后端固定的相册顺序就是可分享的定位。
 */
const photoIndexFromQuery = (raw: unknown): number | null => {
  const n = Number(raw)
  return Number.isInteger(n) && n > 0 ? n - 1 : null
}
activeAlbumId.value = albumIdFromQuery(route.query.album)

const albumHref = (id: number) =>
  localeHrefWith('/gallery', {
    page: currentPage.value > 1 ? String(currentPage.value) : '',
    album: String(id)
  })

/**
 * 详情响应 → 网格/对话框可用的相册对象（列表项当兜底，缺字段不塌成空标题）。
 * 深链的服务端取数与客户端点开的取数必须是同一份映射，否则两个入口的照片口径会分叉。
 */
function albumFromDetail(id: number, data: Record<string, unknown>, fallback: Album | null): Album {
  const photosArr = Array.isArray(data.photos) ? data.photos : []
  const photos = photosArr
    .map((p) => {
      const obj = (p ?? {}) as AlbumDetail
      // 没有原图地址就整条丢掉：网格可以只放缩略图，灯箱却没有可放大的源
      const url = obj.url || obj.original_url || ''
      if (!url) return null
      // 后端把缩略档置成 null 表示"没有可用档位"（外链 / SVG / 上传时后处理失败），
      // 由模板的 `thumb || url` 回落原图；等于原图的档位也已在服务端滤掉，不会白下一遍。
      return { url, thumb: obj.thumbnail_url ?? '' }
    })
    .filter((p): p is AlbumPhoto => p !== null)
  return {
    id,
    title: typeof data.title === 'string' ? data.title : (fallback?.title ?? ''),
    description: typeof data.description === 'string' ? data.description : (fallback?.description ?? ''),
    cover: typeof data.cover === 'string' ? data.cover : (fallback?.cover ?? ''),
    photosCount: typeof data.photo_count === 'number' ? data.photo_count : (fallback?.photosCount ?? 0),
    photos,
    loaded: true
  }
}

/**
 * 地址栏带 ?album= 时，相册详情也在服务端取一次（批次 #128 收尾）。
 * 此前详情只在 onMounted 之后取：深链到「不在当页列表里」的那张相册（第 2 页的相册被直接分享）时，
 * SSR HTML 里连一个该相册的链接都没有——首屏是空网格，爬虫读到的只有列表第 1 页。
 * 无 album 参数时处理器直接 resolve(null)，不给普通访问多加一次请求；
 * 垃圾 id（不存在 / 未公开）404 后静默降级成 null，提示权仍归页内文案。
 */
const { data: deepAlbumRaw } = useAsyncData<Record<string, unknown> | null>(
  () => `gallery:album:${activeAlbumId.value ?? 'none'}:${locale.value}`,
  async () => {
    const id = activeAlbumId.value
    if (id === null) return null
    try {
      const raw = await apiFetchDirect<unknown>(`/gallery/albums/${id}`, {
        query: { lang: locale.value },
        silentToast: true
      })
      const unwrapped
        = raw && typeof raw === 'object' && 'data' in raw
          ? (raw as { data?: unknown }).data
          : raw
      return (unwrapped ?? null) as Record<string, unknown> | null
    } catch {
      return null
    }
  },
  // 客户端换相册走下面的 watch + loadAlbumDetail；这里只求首屏那一份，别让键变化再双发一次
  { watch: [] }
)

/** 深链相册的兜底对象：只在详情响应确实属于当前地址栏那个 id 时才采用。 */
const deepAlbum = computed<Album | null>(() => {
  const id = activeAlbumId.value
  const raw = deepAlbumRaw.value
  if (id === null || !raw || Number(raw.id) !== id) return null
  return albumFromDetail(id, raw, null)
})

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

/**
 * 网格的唯一数据源：列表响应的纯投影 + 已取到的详情覆盖。
 * 必须是 computed 而不是「watch 往数组里搬」——SSR 期只有前者能在渲染前拿到值。
 */
const displayAlbums = computed<Album[]>(() => {
  const items = (albumsResp.value?.items || []) as AlbumResp[]
  const rows = items.map((raw) => {
    const cached = loadedAlbums.value.get(raw.id)
    if (cached) return cached
    return {
      id: raw.id,
      title: raw.title || '',
      description: raw.description || '',
      cover: raw.cover || '',
      photosCount: typeof raw.photo_count === 'number' ? raw.photo_count : 0,
      photos: [],
      loaded: false
    }
  })
  // 深链进来的相册不在当页（分享的是第 2 页那张）：把它排在最前，让首屏与爬虫都读到它，
  // 而不是「地址栏写着相册 44、HTML 里只有第 1 页的 12 个」。已在当页则不重复插入。
  const deep = deepAlbum.value
  if (deep && !rows.some(album => album.id === deep.id)) return [deep, ...rows]
  return rows
})

const currentAlbum = computed<Album | null>(() => {
  const id = activeAlbumId.value
  if (id === null) return null
  // 详情优先（带照片），其次列表项/深链兜底对象（只有封面与计数）：
  // 深链到不在当页的相册时，服务端取到的详情就是那个兜底对象，不必它在列表里。
  return loadedAlbums.value.get(id) ?? displayAlbums.value.find(a => a.id === id) ?? null
})
const currentPhotos = computed(() => currentAlbum.value?.photos ?? [])

// 加载相册详情
async function loadAlbumDetail(id: number) {
  if (albumLoading.value) return
  const target = loadedAlbums.value.get(id) ?? displayAlbums.value.find(a => a.id === id) ?? null
  if (target?.loaded) return
  albumLoading.value = true
  try {
    const raw = await apiFetchDirect<unknown>(`/gallery/albums/${id}`, {
      query: { lang: locale.value },
      // 深链上的 id 很可能是错的（手输 / 相册已删）：这一路的提示权归页内文案，不再另弹 toast
      silentToast: true
    })
    const unwrapped
      = raw && typeof raw === 'object' && 'data' in raw
        ? (raw as { data?: unknown }).data
        : raw
    const data = (unwrapped ?? {}) as Record<string, unknown>
    // 详情按 id 覆盖进 loadedAlbums：网格（displayAlbums）与对话框（currentAlbum）都读这一份，
    // 所以深链到「不在当页列表里」的相册也能开——上一版找不到列表项就 return，
    // 表现是「链接没错、点开是一片空网格」。
    loadedAlbums.value.set(id, albumFromDetail(id, data, target))
  } catch (err) {
    // 不能静默：失败的表现是「点了相册，对话框里一直转圈然后空空如也」，
    // 详情页没有任何别的提示渠道，必须显式给一个错误态。
    // 404 与「请求挂了」分开说——前者重试一万次也不会回来，后者也许只是这一次抖动。
    const errObj = err as { status?: number, statusCode?: number }
    const status = errObj.status ?? errObj.statusCode
    if (status === 404) albumNotFound.value = true
    else detailError.value = true
    console.error('[gallery] 相册详情加载失败', id, err)
  } finally {
    albumLoading.value = false
  }
}

/** 重试：清掉 loaded 守卫，否则 loadAlbumDetail 会直接短路返回 */
function retryDetail() {
  const id = activeAlbumId.value
  if (id === null) return
  detailError.value = false
  albumNotFound.value = false
  loadedAlbums.value.delete(id)
  void loadAlbumDetail(id).then(() => nextTick(() => initViewer()))
}

/** 只改地址栏：URL 才是「开着哪个相册」的真值，下面的 watch 负责让界面跟上 */
function setAlbumQuery(id: number | null) {
  if (!import.meta.client) return
  router.replace({ query: albumQuery(currentPage.value, id) })
}

/**
 * 把灯箱里的那一张写进地址栏（photo 传 null 就是收掉 ?photo=）。
 * 同值直接返回：灯箱每翻一张都会触发 viewed，无脑 replace 会把 history 灌满重复条目。
 */
function syncPhotoQuery(index: number | null) {
  if (!import.meta.client) return
  const want = index === null || index < 0 ? '' : String(index + 1)
  const got = typeof route.query.photo === 'string' ? route.query.photo : ''
  if (want === got) return
  router.replace({ query: albumQuery(currentPage.value, activeAlbumId.value, index) })
}

/** viewerjs 的 viewed 事件带 `detail.index`（0 基）；拿不到就按「不知道」处理，不猜。 */
function photoIndexFromViewerEvent(event: Event | undefined): number | null {
  const detail = (event as CustomEvent<{ index?: unknown }> | undefined)?.detail
  const n = detail?.index
  return typeof n === 'number' && Number.isInteger(n) && n >= 0 ? n : null
}

// 打开相册
function openAlbum(id: number) {
  setAlbumQuery(id)
}

/** 「相册不存在」分支的出口：把坏参数从地址栏一起带走 */
function closeAlbum() {
  dialogOpen.value = false
}

// 地址栏 → 界面：刷新、后退、中键新标签都从这里把相册开回来
async function applyAlbumFromQuery() {
  const id = albumIdFromQuery(route.query.album)
  if (id === null) {
    dialogOpen.value = false
    return
  }
  activeAlbumId.value = id
  detailError.value = false
  albumNotFound.value = false
  dialogOpen.value = true
  await loadAlbumDetail(id)
  await nextTick()
  await initViewer()
  openSharedPhoto()
}

/**
 * 分享链接里的 ?photo= 落到灯箱上：够得着就开那一张，越界只清参数不 clamp——
 * 把坏链接静默换成另一张照片，等于让分享的人和看到的人读的是不同内容。
 */
function openSharedPhoto() {
  const idx = photoIndexFromQuery(route.query.photo)
  if (idx === null) {
    viewerPhotoIndex = null
    return
  }
  if (!viewerInstance || idx >= currentPhotos.value.length) {
    syncPhotoQuery(null)
    return
  }
  viewerPhotoIndex = idx
  viewerInstance.view(idx)
}

watch(() => route.query.album, () => {
  void applyAlbumFromQuery()
})

// 后退/前进直接改 ?photo=（相册没换，只是灯箱换一张或收起来）。
// 与 viewed 事件之间靠 viewerPhotoIndex 挡回路：值已经一致就什么都不做。
watch(() => route.query.photo, (raw) => {
  const idx = photoIndexFromQuery(raw)
  if (idx === viewerPhotoIndex) return
  if (!viewerInstance) {
    // 灯箱还没实例化（相册没开 / viewerjs 没装上）时不去动 URL：
    // URL 是真值，上面的相册流程会来读它，这里写反而会把参数吃掉。
    return
  }
  if (idx === null) {
    viewerPhotoIndex = null
    viewerInstance.hide()
    return
  }
  if (idx >= currentPhotos.value.length) {
    syncPhotoQuery(null)
    return
  }
  viewerPhotoIndex = idx
  viewerInstance.view(idx)
})

onMounted(() => {
  void applyAlbumFromQuery()
})

/**
 * 灯箱实例只在一处销毁（initViewer 重入 / 关对话框 / 组件卸载），顺带把 ?photo= 的对照值
 * 清成 null——留着旧下标会让下一次 watch 误判「灯箱已经在这张」而什么都不做。
 */
function destroyViewer() {
  if (viewerInstance) {
    try {
      viewerInstance.destroy()
    } catch {
      /* noop */
    }
    viewerInstance = null
  }
  viewerPhotoIndex = null
}

// 初始化 viewerjs
async function initViewer() {
  if (!import.meta.client) return
  const el = viewerContainerRef.value
  if (!el) return

  // 销毁旧实例
  destroyViewer()

  const Ctor = await ensureViewer()
  if (!Ctor) return

  // 确保 DOM 中 img 已渲染
  await nextTick()
  if (!el.isConnected) return
  if (el.querySelectorAll('img').length === 0) return

  try {
    viewerInstance = new Ctor(el, {
      // viewerjs 默认 url: 'src'（DEFAULTS.url = 'src'，getImageURL() 就是
      // getAttribute(options.url)）。网格现在显示的是缩略档，不显式指到
      // data-original 的话灯箱放大的就是那张 150px 小图。
      url: 'data-original',
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
      // 灯箱翻到的那一张同步进地址栏；收起时把 ?photo= 一起带走——留着它，下一次刷新会
      // 「凭空」弹出一个访客已经关掉的灯箱（界面与 URL 分叉正是本批次要修的东西）。
      viewed: (event) => {
        viewerPhotoIndex = photoIndexFromViewerEvent(event)
        syncPhotoQuery(viewerPhotoIndex)
      },
      hidden: () => {
        viewerPhotoIndex = null
        syncPhotoQuery(null)
      },
      loading: true
    })
  } catch {
    viewerInstance = null
  }
}

// Dialog 关闭时销毁 viewer
watch(dialogOpen, (open) => {
  if (!open) {
    destroyViewer()
    // 用 ESC / 关闭按钮收掉相册时，地址栏的 ?album= 必须跟着走：留着它，下一次刷新
    // 会「凭空」重开一个访客已经关掉的相册（界面与 URL 分叉正是本批次要修的东西）。
    // ?photo= 跟着一起走——albumQuery 只在有相册时才写它。
    if (activeAlbumId.value !== null) setAlbumQuery(null)
  }
})

onBeforeUnmount(() => {
  destroyViewer()
})

// 空目录页 = 没有可索引内容（与 /sponsor 的 sponsorEmpty 同口径），后端 sitemap 同步跳过。
// 判据用接口给的 total（= 已发布相册数），不用本地投影的 displayAlbums：翻到空页不等于目录为空。
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
