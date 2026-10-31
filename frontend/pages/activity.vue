<!--
  动态时间线页：GET /activities 按 ?page=N 分页（每页 20，真实 <a href> 翻页；越界页码
  SSR 期 301 回带当前筛选的第一页），?type=say|article|update|notice|link 按类型筛选
  （chip 组，状态在地址栏；未知值一律按「全部」处理，与服务端归一口径一致）。
  分页锚点与筛选 chip 共用 queryWith/hrefWith 单源，两者都是真实 <a href>：这页 ssr:true，
  筛选做成 <Button @click> 等于五个 ?type= 只存在于 SPA（批次 #126，口径见 AGENTS §2.3.3）。
  图标必须是本文件内联 ICONS 常量而非 lucide 组件：SSR 与客户端首字节要逐字节一致，
  组件形态的首子差异会直接造成水合错位。后端新增活动类型时，ICONS + backendToIconKey
  白名单 + ACTIVITY_TYPES + i18n 的 activity.type_* 四处必须同步补，漏一处就静默显示成"说说"。
-->
<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-primary/10 mb-5">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="size-7 text-primary"
        >
          <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z" />
        </svg>
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('activity.title') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('activity.desc') }}
      </p>
    </header>

    <div class="max-w-2xl mx-auto">
      <!-- 发布动态：POST /api/activities（仅登录用户）。整块包 <ClientOnly> 是必须的——
           本页是 swr 600 的公开 SSR 页，而 auth store 走 skipHydrate（SSR 期没有 token），
           在 SSR 里渲染这个框要么把某个访客的登录态固化进共享缓存，要么 hydration mismatch。 -->
      <ClientOnly>
        <Card
          v-if="authStore.isAuthenticated"
          class="mb-8"
        >
          <CardContent class="p-4">
            <Textarea
              v-model="draft"
              :placeholder="t('activity.composerPlaceholder')"
              :maxlength="MAX_CONTENT"
              :disabled="publishing"
              rows="2"
              class="resize-none"
            />
            <div class="mt-3 flex items-center justify-between gap-3">
              <span class="text-xs text-muted-foreground">{{ draft.length }} / {{ MAX_CONTENT }}</span>
              <Button
                type="button"
                size="sm"
                :disabled="!draft.trim() || publishing"
                @click="publishActivity"
              >
                {{ publishing ? t('common.submitting') : t('activity.publish') }}
              </Button>
            </div>
          </CardContent>
        </Card>
      </ClientOnly>

      <!-- 类型筛选：状态进地址栏（?type=），刷新/分享/后退可还原；切换回第 1 页，
           因为每种类型的条数不同，停在第 3 页换筛选会落进对方不存在的页码。
           必须是真实 <a href>（AGENTS §2.3.3 第 2 条）：这页是 SSR，做成 <Button @click>
           时五个 ?type= 在爬虫读到的 HTML 里一个都不存在，筛选组合只能靠站内碰运气发现。 -->
      <div
        role="group"
        :aria-label="t('activity.filterLabel')"
        class="mb-8 flex flex-wrap items-center gap-2"
      >
        <a
          v-for="opt in typeOptions"
          :key="opt.value ?? 'all'"
          :href="typeHref(opt.value)"
          :class="pageLinkClass(currentType === opt.value ? 'default' : 'outline')"
          :aria-current="currentType === opt.value ? 'true' : undefined"
          @click.prevent="setType(opt.value)"
        >
          {{ opt.label }}
        </a>
      </div>

      <div
        v-if="pending && activityList.length === 0"
        class="flex flex-col gap-8 mb-8"
      >
        <div
          v-for="i in 5"
          :key="i"
          class="relative pl-8"
        >
          <Skeleton class="absolute -left-8 top-1.5 size-6 rounded-full" />
          <div class="flex flex-col gap-3 p-5 rounded-xl bg-card border border-border/60">
            <div class="flex items-center justify-between gap-3">
              <div class="flex items-center gap-2">
                <Skeleton class="size-5 rounded-full" />
                <Skeleton class="w-20 h-4 rounded-full" />
              </div>
              <Skeleton class="w-16 h-3 rounded-full" />
            </div>
            <div class="flex flex-col gap-2">
              <Skeleton class="w-full h-4 rounded-full" />
              <Skeleton class="w-4/5 h-4 rounded-full" />
              <Skeleton class="w-2/3 h-4 rounded-full" />
            </div>
          </div>
        </div>
      </div>

      <div
        v-else-if="loadError"
        class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive text-center"
      >
        {{ t('error.loadFailed') }}
      </div>

      <div
        v-else
        class="relative pl-8"
      >
        <div
          v-if="activityList.length > 0"
          class="absolute left-3 top-2 bottom-2 w-px bg-border"
        />

        <div
          v-for="item in activityList"
          :key="item.id"
          v-memo="[item.id, item.type, item.likes_count, item.created_at, pendingLikeId === item.id]"
          class="relative mb-8 last:mb-0"
        >
          <div
            class="absolute -left-8 top-1.5 size-6 rounded-full border-2 border-background flex items-center justify-center shrink-0 bg-primary/10"
          >
            <svg
              :viewBox="getIcon(activityIconKey(item.type)).viewBox"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="size-3 shrink-0 text-primary"
            >
              <path :d="getIcon(activityIconKey(item.type)).d" />
            </svg>
          </div>

          <Card class="transition-all hover:shadow-soft duration-300">
            <CardContent class="p-5">
              <div class="flex items-start justify-between gap-3 mb-3">
                <div class="flex items-center gap-2 flex-wrap">
                  <Badge
                    variant="default"
                    class="text-xs"
                  >
                    {{ t(`activity.type_${item.type}`) || item.type }}
                  </Badge>
                  <span
                    v-if="item.author_name"
                    class="text-sm font-medium"
                  >{{ item.author_name }}</span>
                </div>
                <span class="text-xs text-muted-foreground shrink-0 whitespace-nowrap">{{ formatDate(item.created_at) }}</span>
              </div>

              <div class="text-foreground/90 leading-relaxed whitespace-pre-wrap">
                {{ item.content }}
              </div>

              <div class="mt-3 pt-3 border-t border-border/50 flex items-center gap-4 text-xs text-muted-foreground">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  class="h-auto gap-1.5 px-2"
                  :disabled="pendingLikeId === item.id"
                  :aria-label="t('activity.like')"
                  @click="likeActivity(item.id)"
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    stroke="currentColor"
                    stroke-width="1.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    class="fill-error text-error"
                  >
                    <path :d="ICONS.heart?.d ?? ''" />
                  </svg>
                  {{ item.likes_count ?? 0 }}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        <div
          v-if="activityList.length > 0"
          class="absolute -left-8 bottom-0 size-6 rounded-full bg-background border-2 border-border flex items-center justify-center"
        >
          <div class="size-2 rounded-full bg-muted-foreground/40" />
        </div>
      </div>
    </div>

    <!-- 分页：此前固定只取前 50 条且没有翻页入口，第 51 条起的动态在站内无法到达。
         链接必须是真实 <a href>——SSR HTML 里的 href 是无 JS 访客与爬虫唯一的翻页入口；
         click 仍走 handlePageChange 保留 SPA 行为。 -->
    <nav
      v-if="totalPages > 1"
      class="max-w-2xl mx-auto mt-10 flex items-center justify-center gap-2"
      role="navigation"
      aria-label="pagination"
    >
      <template v-if="currentPage <= 1">
        <Button
          variant="outline"
          size="sm"
          disabled
        >
          {{ t('common.prevPage', '上一页') }}
        </Button>
      </template>
      <a
        v-else
        :href="pageHref(currentPage - 1)"
        :class="pageLinkClass('outline')"
        @click.prevent="handlePageChange(currentPage - 1)"
      >{{ t('common.prevPage', '上一页') }}</a>
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
          size="sm"
          disabled
        >
          {{ t('common.nextPage', '下一页') }}
        </Button>
      </template>
      <a
        v-else
        :href="pageHref(currentPage + 1)"
        :class="pageLinkClass('outline')"
        @click.prevent="handlePageChange(currentPage + 1)"
      >{{ t('common.nextPage', '下一页') }}</a>
    </nav>

    <div
      v-if="!pending && activityList.length === 0"
      class="text-center py-20"
    >
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <svg
          :viewBox="ICONS.zap?.viewBox ?? '0 0 24 24'"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="size-8 text-muted-foreground"
        >
          <path :d="ICONS.zap?.d ?? ''" />
        </svg>
      </div>
      <h3 class="font-display text-xl font-semibold">
        {{ t('activity.noActivity') }}
      </h3>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent } from '~~/components/ui/card'
import { Badge } from '~~/components/ui/badge'
import { Button, buttonVariants } from '~~/components/ui/button'
import { Textarea } from '~~/components/ui/textarea'
import { apiFetch } from '~~/composables/useApi'
import { pageWindow } from '~~/lib/pagination'
import { useAuthStore } from '~~/stores/auth'
import { useI18n } from 'vue-i18n'

/**
 * 内联 SVG 常量，保证 SSR/客户端输出逐字节一致，避免 Hydration 串台。
 */
const ICONS = {
  say: {
    viewBox: '0 0 24 24',
    d: 'M21 12a8.001 8.001 0 0 0-8-8A8.001 8.001 0 0 0 5 8.122 6.95 6.95 0 0 0 3 12a6.95 6.95 0 0 0 .309 2A8.001 8.001 0 0 0 3 20l2-1.185A7.96 7.96 0 0 0 13 20a8.001 8.001 0 0 0 8-8ZM8 10h8v2H8v-2Zm0 3h5v2H8v-2Z'
  },
  article: {
    viewBox: '0 0 24 24',
    d: 'M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2H6Zm0-2h12V8h-3.6a.4.4 0 0 1-.4-.4V4H6v16Zm2-11h8v2H8v-2Zm0 4h8v2H8v-2Zm0 4h5v2H8v-2Z'
  },
  update: {
    viewBox: '0 0 24 24',
    d: 'M3 12a9 9 0 1 0 3-6.7L3 8V3h5L6.17 4.83A11 11 0 1 1 1 12h2Zm10-5v6l5 3'
  },
  notice: {
    viewBox: '0 0 24 24',
    d: 'M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9Zm4.3 11a2.5 2.5 0 0 0 5.4 0Z'
  },
  zap: {
    viewBox: '0 0 24 24',
    d: 'M13 2 3 14h7l-1 8 10-12h-7l1-8Z'
  },
  heart: {
    viewBox: '0 0 24 24',
    d: 'M12 21s-7-4.5-9.5-9A5.5 5.5 0 0 1 12 6.5 5.5 5.5 0 0 1 21.5 12c-2.5 4.5-9.5 9-9.5 9Z'
  },
  // lucide「link-2」官方两段路径合并进一个 d（同一段里的子路径 stroke 行为与两个
  // <path> 元素一致），保持 ICONS 的单 d 形态；路径字节抄自 @lucide/vue，不手搓。
  link: {
    viewBox: '0 0 24 24',
    d: 'M9 17H7A5 5 0 0 1 7 7h2 M15 7h2a5 5 0 1 1 0 10h-2'
  }
} as const

type IconKey = keyof typeof ICONS
interface IconDef { viewBox: string, d: string }
const ICON_FALLBACK: IconDef = ICONS.say
const getIcon = (key: string): IconDef => ((ICONS as Record<IconKey, IconDef>)[key as IconKey] ?? ICON_FALLBACK)

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const authStore = useAuthStore()

// 与后端 MAX_ACTIVITY_CONTENT_CHARS 同值：schemas/activity.py 对每种语言正文各限 1000 字，
// 这里只是让用户在提交前就看到边界，不是安全边界（后端 422 才是）。
const MAX_CONTENT = 1000

/**
 * 动态类型唯一清单（与后端 schemas/activity.py::ActivityType 同集合，由
 * tests/unit/activityTypeFilter.spec.ts 双向对账）。它同时是筛选 chip 的枚举、
 * 图标白名单与 `?type=` 的取值白名单——漏一个即「筛得出来但图标/文案掉回说说」。
 */
const ACTIVITY_TYPES = ['say', 'article', 'update', 'notice', 'link'] as const
type ActivityType = (typeof ACTIVITY_TYPES)[number]
const isActivityType = (value: unknown): value is ActivityType =>
  (ACTIVITY_TYPES as readonly string[]).includes(String(value))

interface ActivityItem {
  id: number
  type: ActivityType
  content: string
  author_name?: string
  author_avatar?: string
  likes_count?: number
  created_at: string
}

const backendToIconKey = (type: string): string => (isActivityType(type) ? type : 'say')
const activityIconKey = (type: string) => backendToIconKey(type)

// 动态流只要"月 日 时:分"（同一天里年份是噪声），单源在 useI18nHelpers::formatStampText
// —— 月份名表与 24 小时制都固定，SSR 与浏览器字节级一致。
const formatDate = (dateStr: string) => formatStampText(dateStr, String(locale.value || 'zh'))

// 真实接口：GET /api/activities?page=N&page_size=20（后端 page_size 只认 1–100）
interface Paginated<T> {
  items: T[]
  total?: number
  page?: number
  page_size?: number
  total_pages?: number
}

// 每页 20 条：时间线一屏约 3–4 条，20 条够滚且不必让首屏背着 50 条的 DOM。
const PAGE_SIZE = 20
const route = useRoute()
const router = useRouter()
// 初始页码从 URL 读：分享 / 刷新 / 后退都要能还原；非正整数一律回第 1 页。
const currentPage = ref(Math.max(1, Number(route.query.page) || 1))
const requestedPage = Math.max(1, Number(route.query.page) || 1)
// 类型筛选同样只认地址栏：非白名单值按「全部」处理，与后端归一口径一致
// （服务端也回全部，所以 SSR 首屏与客户端 hydrate 不会判成两个列表）。
const currentType = ref<ActivityType | null>(isActivityType(route.query.type) ? route.query.type : null)

/** 地址栏 query 的单源：省略 `page=1` 与空 type，避免 `?type=&page=1` 这种半空地址。 */
const queryWith = (page: number, type: ActivityType | null): Record<string, string> => {
  const q: Record<string, string> = {}
  if (type) q.type = type
  if (page > 1) q.page = String(page)
  return q
}

// query 用 computed：currentPage / currentType / lang 变化时 Nuxt params watcher 自动重取，
// 不手写 watch + refresh()（那会与自动重取双发，第一发还被 abort）。
const { data: activityResp, pending, error: loadError, refresh } = useAPI<Paginated<ActivityItem>>('/activities', {
  query: computed(() => ({
    page: currentPage.value,
    page_size: PAGE_SIZE,
    // 不筛选时整个键都不发（空串 `?type=` 会被算成另一条请求）；取值口径与地址栏同一条 ref。
    ...(currentType.value ? { type: currentType.value } : {}),
    lang: locale.value
  }))
})

const typeOptions = computed(() => [
  { value: null as ActivityType | null, label: String(t('activity.filterAll')) },
  ...ACTIVITY_TYPES.map(value => ({
    value: value as ActivityType | null,
    label: String(t(`activity.type_${value}`))
  }))
])

const totalActivities = computed(() => activityResp.value?.total ?? 0)
const totalPages = computed(
  () => activityResp.value?.total_pages ?? (Math.ceil(totalActivities.value / PAGE_SIZE) || 1)
)
const visiblePages = computed(() => pageWindow(currentPage.value, totalPages.value))
const activityBaseHref = () => applyLocalePrefix('/activity', locale.value)
const hrefWith = (query: Record<string, string>) => {
  const search = new URLSearchParams(query).toString()
  return search ? `${activityBaseHref()}?${search}` : activityBaseHref()
}
const pageHref = (page: number) => hrefWith(queryWith(page, currentType.value))
// 筛选 chip 的目标地址与分页锚点同一份单源，页码固定回 1（见 setType 的注释）。
const typeHref = (type: ActivityType | null) => hrefWith(queryWith(1, type))
const pageLinkClass = (variant: 'default' | 'outline' | 'ghost') =>
  buttonVariants({ variant, size: 'sm' })

const handlePageChange = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  if (import.meta.client) {
    router.replace({ query: queryWith(page, currentType.value) })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

// 换筛选条件回到第 1 页：各类型的条数不同，停在第 3 页换筛选会落进对方不存在的页码。
const setType = (next: ActivityType | null) => {
  if (currentType.value === next) return
  currentType.value = next
  currentPage.value = 1
  if (import.meta.client) void router.replace({ query: queryWith(1, next) })
}

// 越界页码（动态被删一批后的旧分享链接）拉回末页，否则访客拿到空列表且无从自救。
watch([totalActivities, currentPage], () => {
  if (totalActivities.value === 0) return
  if (currentPage.value > totalPages.value) currentPage.value = totalPages.value
})

// 越界页码对爬虫必须 301 回裸动态页：200 空列表会被判 soft 404，
// 且自指 canonical 等于承认每个垃圾页码都是独立页面。时点与 useContentStatus
// 同轨（app:rendered：数据已落值、状态码还改得动）；响应头 no-store 防 301 被 swr 缓存。
if (import.meta.server) {
  const ssrEvent = useRequestEvent()
  useNuxtApp().hooks.hookOnce('app:rendered', () => {
    if (ssrEvent && totalActivities.value > 0 && requestedPage > totalPages.value) {
      ssrEvent.node.res.statusCode = 301
      ssrEvent.node.res.setHeader('location', hrefWith(queryWith(1, currentType.value)))
      ssrEvent.node.res.setHeader('cache-control', 'no-store')
    }
  })
}

const activityList = computed<ActivityItem[]>(() => {
  const items = activityResp.value?.items ?? []
  return items.map((raw: unknown) => {
    const r = raw as Record<string, unknown>
    const author = (r.author ?? {}) as Record<string, unknown>
    const authorName
      = (typeof author.nickname === 'string' && author.nickname)
        || (typeof author.username === 'string' && author.username)
        || (typeof author.name === 'string' && author.name)
        || ''
    const rawType = (typeof r.type === 'string' && r.type) || 'say'
    const safeType: ActivityItem['type'] = isActivityType(rawType) ? rawType : 'say'
    return {
      id: typeof r.id === 'number' ? r.id : Number(r.id ?? 0),
      type: safeType,
      content: (typeof r.content === 'string' && r.content) || '',
      author_name: authorName || undefined,
      // 后端解析链的 resolved_avatar_url 优先：avatar 是原始列，
      // 用 GitHub/QQ/Gravatar 头像的作者那里是 null，反过来取就会一路掉到字母兜底。
      author_avatar: ((typeof author.resolved_avatar_url === 'string' && author.resolved_avatar_url) || (typeof author.avatar === 'string' && author.avatar)) || undefined,
      likes_count: typeof r.likes_count === 'number' ? r.likes_count : 0,
      created_at: (typeof r.created_at === 'string' && r.created_at) || new Date().toISOString()
    }
  })
})

// 不手写 watch(locale)+refresh()：query 是 computed，切语言时 Nuxt params watcher
// 已自动重取；手写 refresh 等于同一 URL 双发，第一发还被 abort。点赞后的 refresh 见下方。

// 点赞：POST /api/activities/{id}/like（只增不减、允许匿名，与已上线的评论点赞同语义）。
// 端点不返回新计数，所以成功后 refresh 取服务端权威值，不在本地 +1——本页是 swr 600 的缓存页，
// 本地累加会让这一屏的读数与其它访客看到的服务端值长期对不上。
const pendingLikeId = ref<number | null>(null)
async function likeActivity(id: number) {
  if (pendingLikeId.value !== null) return
  pendingLikeId.value = id
  try {
    await apiFetch(`/activities/${id}/like`, { method: 'POST' })
    await refresh()
  } catch {
    // 失败提示由 apiFetch 统一 toast，这里只吞 rejection 防未处理异常
  } finally {
    pendingLikeId.value = null
  }
}

// 发布动态：POST /api/activities。content 是多语言 dict，用户只写当前语言那一份，
// 其余语言由后端 get_i18n_value 的回退链（请求语言 → zh → 第一个非空）兜住，
// 不做机器翻译（AGENTS.md §7.3：UGC 存明文、禁止自动翻译）。
const draft = ref('')
const publishing = ref(false)
async function publishActivity() {
  const text = draft.value.trim()
  if (!text || publishing.value) return
  publishing.value = true
  try {
    await apiFetch('/activities', {
      method: 'POST',
      body: { content: { [locale.value]: text }, type: 'say' }
    })
    draft.value = ''
    // 新动态落在第 1 页顶部：在第 2 页之后发完却停在原页，用户看不到自己刚发的那条。
    if (currentPage.value !== 1) {
      currentPage.value = 1
      if (import.meta.client) router.replace({ query: queryWith(1, currentType.value) })
    }
    await refresh()
  } catch {
    // 401（会话失效）与 422（超长）由 apiFetch 统一 toast，正文留在输入框
  } finally {
    publishing.value = false
  }
}

useSeo({
  title: computed(() => t('activity.title') as string || '动态'),
  description: computed(() => t('activity.desc') as string),
  type: 'website'
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home', '首页') as string, url: '/' },
  { name: t('nav.activity', '动态') as string, url: '/activity' }
])
</script>
