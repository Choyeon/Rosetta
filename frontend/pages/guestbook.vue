<!--
  留言板：GET/POST /guestbook + 点赞 POST /guestbook/{id}/like（本路由 swr 60s）。
  guestbookList 必须是可写 ref 而不是 computed：点赞是就地 mutate item，computed 会在
  依赖重算时把 liked/likesCount 冲回接口初值。后端 like 为纯计数 +1（无取消语义），
  liked 置真后不再发请求；提交固定只拉 status=approved，新留言先进审核队列、刷新看不到自己
  那条属预期。失败只写行内 submitError —— apiFetch 已全局弹过 toast，不得双报。
-->
<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-primary/10 mb-5">
        <MessageSquare class="size-7 text-primary" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('guestbook.title') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('guestbook.desc') }}
      </p>
    </header>

    <Card
      v-if="guestbookEnabled"
      class="mb-12 border-dashed"
    >
      <CardHeader class="pb-4">
        <CardTitle class="text-lg flex items-center gap-2">
          <PenLine class="size-4 text-muted-foreground" />
          {{ t('guestbook.writeMessage') }}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <!-- 已登录：昵称/邮箱由后端按账号自动识别（guestbook_service.create_entry），
             与文章评论区（posts/[slug].vue）一致，隐藏昵称/邮箱字段，仅保留可选网站 -->
        <div
          v-if="authStore.isAuthenticated"
          class="mb-4"
        >
          <p class="text-sm text-muted-foreground mb-2">
            {{ t('guestbook.postingAs', '将以当前账号发表') }}{{ authStore.user?.username ? `：${authStore.user.username}` : '' }}
          </p>
          <Input
            v-model="form.author_website"
            :placeholder="t('guestbook.website')"
            :aria-label="t('guestbook.website')"
            :disabled="submitting"
            class="max-w-xs"
          />
        </div>
        <div
          v-else
          class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4"
        >
          <Input
            v-model="form.author_name"
            :placeholder="t('guestbook.nickname')"
            :aria-label="t('guestbook.nickname')"
            :disabled="submitting"
          />
          <Input
            v-model="form.author_email"
            type="email"
            :placeholder="t('guestbook.email')"
            :aria-label="t('guestbook.email')"
            :disabled="submitting"
          />
          <Input
            v-model="form.author_website"
            :placeholder="t('guestbook.website')"
            :aria-label="t('guestbook.website')"
            :disabled="submitting"
          />
        </div>
        <Textarea
          v-model="form.content"
          :placeholder="t('guestbook.contentPlaceholder')"
          :aria-label="t('guestbook.contentPlaceholder')"
          rows="4"
          class="resize-none mb-4"
          :disabled="submitting"
        />
        <CaptchaField
          v-if="needCaptcha"
          ref="captchaRef"
          :enabled="needCaptcha"
          class="mb-4"
        />
        <div class="flex justify-end">
          <Button
            :disabled="submitting"
            @click="submitGuestbook"
          >
            <Send
              v-if="!submitting"
              data-icon="inline-start"
              class="mr-2"
            />
            <Loader2
              v-else
              data-icon="inline-start"
              class="animate-spin mr-2"
            />
            {{ submitting ? (t('common.submitting') || '提交中…') : t('common.submit') }}
          </Button>
        </div>
        <p
          v-if="submitError"
          class="text-sm text-error mt-3"
        >
          {{ submitError }}
        </p>
      </CardContent>
    </Card>
    <p
      v-else
      class="mb-10 rounded-xl border border-border border-dashed p-6 text-sm text-muted-foreground"
    >
      {{ t('guestbook.closed', '留言板当前已关闭，仅可浏览既有留言。') }}
    </p>

    <div
      v-if="loadFailed && !pending"
      class="mb-10 rounded-xl border border-destructive/30 bg-destructive/5 p-6 flex items-center justify-between gap-4"
    >
      <p class="text-sm text-destructive">
        {{ t('guestbook.loadFailed', '留言加载失败，请稍后重试') }}
      </p>
      <Button
        variant="outline"
        size="sm"
        @click="reloadList"
      >
        <RotateCw data-icon="inline-start" />
        {{ t('common.retry', '重试') }}
      </Button>
    </div>

    <div
      v-else-if="pending && displayList.length === 0"
      class="flex flex-col gap-6 mb-10"
    >
      <!-- 留言卡片骨架：结构仿照真实的头像 + 昵称 + 正文三行，走共享 Skeleton
           （原先是外层 animate-pulse 套一堆 bg-muted div，全站口径不统一） -->
      <div
        v-for="i in 3"
        :key="i"
        class="p-6 rounded-xl bg-card border border-border/60"
      >
        <div class="flex gap-4">
          <Skeleton class="size-10 rounded-full shrink-0" />
          <div class="flex flex-col gap-3 flex-1">
            <div class="flex items-center gap-2">
              <Skeleton class="w-24 h-4 rounded-full" />
              <Skeleton class="w-16 h-3 rounded-full" />
            </div>
            <div class="flex flex-col gap-2">
              <Skeleton class="w-full h-4 rounded-full" />
              <Skeleton class="w-4/5 h-4 rounded-full" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <div
      v-else
      class="flex flex-col gap-6"
    >
      <div
        v-for="item in displayList"
        :key="item.id"
        class="relative"
      >
        <Card class="card-surface transition-all hover:shadow-soft duration-300">
          <CardContent class="p-6">
            <div class="flex gap-4">
              <UserAvatar
                :avatar="item.avatar"
                :seed="item.user_id != null ? String(item.user_id) : item.nickname"
                :name="item.nickname || 'Guest'"
                :title="item.title || null"
                :size="40"
                :show-title="true"
              />
              <div class="flex-1 min-w-0">
                <div class="flex flex-wrap items-center gap-2 mb-1">
                  <span class="font-medium">{{ item.nickname }}</span>
                  <TitleBadge
                    v-if="item.title"
                    :title="item.title"
                    size="sm"
                  />
                  <a
                    v-if="item.website"
                    :href="item.website"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="text-xs text-muted-foreground hover:text-foreground transition-colors truncate max-w-[200px]"
                  >
                    {{ item.website.replace(/^https?:\/\//, '') }}
                  </a>
                  <span class="text-xs text-muted-foreground">{{ formatDate(item.created_at) }}</span>
                  <Badge
                    v-if="item.is_pinned"
                    variant="default"
                    class="text-[10px] px-1.5 py-0.5"
                  >
                    {{ t('common.pinned') || '置顶' }}
                  </Badge>
                  <Badge
                    v-else-if="item.is_featured"
                    variant="secondary"
                    class="text-[10px] px-1.5 py-0.5"
                  >
                    {{ t('common.featured') || '精华' }}
                  </Badge>
                </div>
                <p class="text-foreground/90 leading-relaxed whitespace-pre-wrap">
                  {{ item.content }}
                </p>
                <div class="flex items-center gap-4 mt-3">
                  <button
                    type="button"
                    class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                    :aria-label="t('activity.like')"
                    :disabled="!!item.liking"
                    @click="toggleLike(item)"
                  >
                    <Heart :class="['size-4', item.liked ? 'fill-error text-error' : '']" />
                    <span>{{ item.likesCount || 0 }}</span>
                  </button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>

    <div
      v-if="!pending && !loadFailed && displayList.length === 0"
      class="text-center py-20"
    >
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <MessageSquare class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">
        {{ t('guestbook.noMessages') }}
      </h3>
    </div>

    <div
      v-if="totalPages > 1"
      class="flex justify-center mt-12"
    >
      <nav
        class="flex items-center gap-2"
        role="navigation"
        aria-label="pagination"
      >
        <Button
          variant="outline"
          size="icon"
          :disabled="currentPage <= 1"
          :aria-label="t('common.prevPage', '上一页')"
          @click="handlePageChange(currentPage - 1)"
        >
          <ChevronLeft data-icon="inline-start" />
        </Button>
        <Button
          v-for="page in visiblePages"
          :key="page"
          :variant="page === currentPage ? 'default' : 'ghost'"
          size="icon"
          class="size-9 min-w-[2.25rem]"
          @click="handlePageChange(page)"
        >
          {{ page }}
        </Button>
        <Button
          variant="outline"
          size="icon"
          :disabled="currentPage >= totalPages"
          :aria-label="t('common.nextPage', '下一页')"
          @click="handlePageChange(currentPage + 1)"
        >
          <ChevronRight data-icon="inline-start" />
        </Button>
      </nav>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Badge } from '~~/components/ui/badge'
import UserAvatar from '~~/components/UserAvatar.vue'
import CaptchaField from '~~/components/CaptchaField.vue'
import TitleBadge from '~~/components/TitleBadge.vue'
import { useI18n } from 'vue-i18n'
import { MessageSquare, PenLine, Send, Heart } from '@lucide/vue'
import { Loader2, RotateCw, ChevronLeft, ChevronRight } from '~~/lib/lucide-svg-icons'
import { useAPI, apiFetch } from '~~/composables/useApi'
import { extractApiErrorMessage } from '~~/lib/utils'
import { useToast } from '~~/composables/useToast'
import { useAuthStore } from '~~/stores/auth'
import { pageWindow } from '~~/lib/pagination'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const site = useSite()
const toast = useToast()
const authStore = useAuthStore()

// features.enable_guestbook=false 时后端 POST /guestbook 直接 403，表单必须同步收起。
const guestbookEnabled = computed(() => site.features.value.enable_guestbook)

// features.enable_captcha=true 且未登录时，后端写口会拒掉没有验证码的留言（400 CAPTCHA_REQUIRED），
// 表单必须同步出现这一栏，否则用户只看到一个看不懂的错误。
const needCaptcha = computed(() => !authStore.isAuthenticated && site.features.value.enable_captcha)
const captchaRef = ref<InstanceType<typeof CaptchaField> | null>(null)

// ===== SEO：基于 i18n + 站点设置 =====
useSeo({
  title: computed(() => String(t('nav.guestbook') || t('guestbook.title') || '留言板')),
  description: computed(() => String(t('guestbook.desc') || '') || site.siteDescription.value),
  type: 'website'
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home') as string, url: '/' },
  { name: t('nav.guestbook') as string, url: '/guestbook' }
])

interface GuestbookItem {
  id: number
  /** 登录留言者的用户 id；用作默认头像的**稳定**配色种子（昵称可改，改了会换色） */
  user_id?: number | null
  nickname: string
  author_email?: string
  website?: string
  avatar?: string
  title?: {
    id?: number
    name: string
    icon?: string
    color?: string
  } | null
  content: string
  created_at: string
  likesCount: number
  liked?: boolean
  liking?: boolean
  is_pinned?: boolean
  is_featured?: boolean
  status?: string
}

interface Paginated<T> {
  items: T[]
  total?: number
  page?: number
  page_size?: number
  total_pages?: number
}

const form = reactive({
  author_name: '',
  author_email: '',
  author_website: '',
  content: ''
})

const submitting = ref(false)
const submitError = ref<string | null>(null)

// ===== 分页状态（与 pages/posts/index.vue 同款数字分页）=====
// 页码进 URL：留言板常有"第 N 页那条留言"被单独分享，落回第一页等于链接指向错内容。
const route = useRoute()
const router = useRouter()
const currentPage = ref(Math.max(1, Number(route.query.page) || 1))
const pageSize = 10

// 真实接口：GET /api/guestbook?page=N&page_size=10&status=approved
const {
  data: gbResp,
  pending,
  error: gbError,
  refresh
} = useAPI<Paginated<unknown>>('/guestbook', {
  query: computed(() => ({
    page: currentPage.value,
    page_size: pageSize,
    status: 'approved',
    lang: locale.value
  })),
  key: 'guestbook:list'
})

// 不手写 watch([currentPage, locale])+refresh()：query 是 computed，翻页/切语言时
// Nuxt useAsyncData 的 params watcher 已自动重取；手写 refresh 等于同一 URL 双发，
// 第一发还被 abort，纯浪费后端查询。

const total = computed(() => gbResp.value?.total ?? 0)
const totalPages = computed(() => Math.ceil(total.value / pageSize) || 1)
const visiblePages = computed(() => pageWindow(currentPage.value, totalPages.value))

const handlePageChange = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  // replace：翻页不该在历史里堆一串同页变体，但地址栏要带上 page
  void router.replace({ query: page > 1 ? { page: String(page) } : {} })
  if (import.meta.client) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

// 越界页码（?page=99）拉回最后一页，别停在"第 99 页，共 3 页"的空列表。
watch([total, currentPage], () => {
  if (total.value > 0 && currentPage.value > totalPages.value) currentPage.value = totalPages.value
})

// 浏览器前进/后退改的是地址栏，页内状态要跟着回读
watch(
  () => route.query.page,
  (raw) => {
    const next = Math.max(1, Number(raw) || 1)
    if (next !== currentPage.value) currentPage.value = next
  }
)

// ===== 错误态：列表接口失败 → 卡片 + 重试按钮 + toast（禁止静默失败）=====
const loadFailed = computed(() => !!gbError.value)
watch(gbError, (err) => {
  if (import.meta.client && err) {
    const e = (err ?? {}) as { data?: unknown }
    toast.error(
      extractApiErrorMessage(e.data, String(t('guestbook.loadFailed', '留言加载失败，请稍后重试')))
    )
  }
})

const reloadList = async () => {
  await refresh()
}

const mapGuestbookRow = (raw: unknown): GuestbookItem => {
  const r = (raw ?? {}) as Record<string, unknown>
  const pickStr = (k: string, fallback = '') => (typeof r[k] === 'string' ? r[k] : fallback)
  const pickNum = (k: string, fallback = 0) => (typeof r[k] === 'number' ? r[k] : fallback)
  // title 字段可能是对象（后端 UserTitleResponse）或 null
  const rawTitle = r.title
  const mappedTitle = rawTitle && typeof rawTitle === 'object'
    ? {
        id: (rawTitle as Record<string, unknown>).id as number | undefined,
        name: String((rawTitle as Record<string, unknown>).name ?? ''),
        icon: String((rawTitle as Record<string, unknown>).icon ?? ''),
        color: String((rawTitle as Record<string, unknown>).color ?? '#3b82f6')
      }
    : null
  return {
    id: pickNum('id', 0),
    user_id: typeof r.user_id === 'number' ? r.user_id : null,
    nickname: pickStr('author_name') || pickStr('nickname'),
    author_email: pickStr('author_email') || undefined,
    website: pickStr('author_website') || pickStr('website') || undefined,
    avatar: pickStr('resolved_avatar_url') || pickStr('author_avatar') || pickStr('avatar') || undefined,
    title: mappedTitle,
    content: pickStr('content'),
    created_at: pickStr('created_at') || new Date().toISOString(),
    likesCount: pickNum('likes_count', 0),
    liked: false,
    is_pinned: !!r.is_pinned,
    is_featured: !!r.is_featured,
    status: pickStr('status') || undefined
  }
}

// 关键修复：列表必须是可写 ref（而非 computed 产出一次性 plain object），
// 否则 toggleLike 对 item.liked / likesCount 的 mutate 不会触发重渲染，
// 且任何依赖重算都会把点赞状态冲回初始值。
const guestbookList = ref<GuestbookItem[]>([])
watch(
  () => gbResp.value?.items,
  (items) => {
    guestbookList.value = Array.isArray(items) ? items.map(mapGuestbookRow) : []
  },
  { immediate: true }
)

// ===== SSR 渲染真源（2026-10-01 hydration mismatch 修复）=====
// Vue SSR 不执行任何 watch 回调（无 effect scheduling）——SSR 渲染期
// guestbookList 恒为初始 []，即使 gbResp 已在 Suspense 阶段拿到数据，
// SSR 也只会渲染空列表 + 空状态，客户端水合后列表项出现 →
// children/node 级 hydration mismatch（生产同样成立，与构建环境无关）。
// 渲染入口统一走 displayList：SSR 从 gbResp 现算快照；客户端水合后
// 回落到 watch 维护的可写 ref（点赞就地 mutate 不被重算冲掉）。
const displayList = computed<GuestbookItem[]>(() => {
  if (import.meta.server) {
    const items = gbResp.value?.items
    return Array.isArray(items) ? items.map(mapGuestbookRow) : []
  }
  return guestbookList.value
})

// 展示「月 日 时:分」：与动态流同一个单源（静态月表 + 24 小时制），
// 本页是 SSR 页，toLocale* 在 Node 无 full-icu 时回退 en-US 会造成 hydration mismatch。
const formatDate = (dateStr: string) =>
  formatStampText(dateStr, String(locale.value || 'zh'))

// 已登录用户：昵称/邮箱自动带出（与文章评论区对登录者的处理一致，
// 后端 create_entry 也会按 current_user 兜底），登录态字段在模板中隐藏。
const prefillFromAuth = () => {
  if (!import.meta.client) return
  const u = authStore.user
  if (!authStore.isAuthenticated || !u) return
  if (!form.author_name) form.author_name = String(u.nickname || u.username || '')
  if (!form.author_email && u.email) form.author_email = String(u.email)
}
watch(
  () => [authStore.isAuthenticated, authStore.user?.username, authStore.user?.email] as const,
  prefillFromAuth,
  { immediate: true }
)

const submitGuestbook = async () => {
  if (submitting.value) return
  // 登录用户昵称/邮箱由后端按账号识别，不再强制前端必填
  // 校验失败必须写行内 submitError：静默 return 的表现是"点了提交，什么都没发生"
  if (!form.content.trim()) {
    submitError.value = String(t('guestbook.contentRequired', '请先写下留言内容'))
    return
  }
  if (!authStore.isAuthenticated && !form.author_name.trim()) {
    submitError.value = String(t('guestbook.nicknameRequired', '请填写昵称'))
    return
  }
  if (needCaptcha.value && !captchaRef.value?.valid()) {
    submitError.value = String(t('captcha.required', '请填写验证码'))
    return
  }
  submitting.value = true
  submitError.value = null
  try {
    const payload: Record<string, string> = {
      content: form.content.trim(),
      ...(captchaRef.value?.payload() ?? {})
    }
    if (form.author_name.trim()) payload.author_name = form.author_name.trim()
    if (form.author_email.trim()) payload.author_email = form.author_email.trim()
    if (form.author_website.trim()) payload.author_website = form.author_website.trim()

    await apiFetch('/guestbook', {
      method: 'POST',
      body: payload
    })

    toast.success(String(t('guestbook.submitSuccess', '留言已提交，审核通过后会显示在列表中')))

    form.author_name = ''
    form.author_email = ''
    form.author_website = ''
    form.content = ''
    // 留言会先进入审核队列，不必立即插入前端列表，刷新拉取已审核列表
    await refresh()
  } catch (err: unknown) {
    const e = (err ?? {}) as Record<string, unknown>
    const data = (e.data ?? {}) as Record<string, unknown>
    const msg
      = (typeof data.message === 'string' && data.message)
        || (typeof data.detail === 'object' && data.detail !== null && typeof (data.detail as Record<string, unknown>).message === 'string'
          ? String((data.detail as Record<string, unknown>).message)
          : '')
        || (typeof e.message === 'string' && e.message)
        || (t('guestbook.submitFailed') as string)
        || '提交失败，请稍后再试'
    submitError.value = String(msg)
    // 注意：apiFetch 抛错前已统一 toast（silentToast 默认 false），
    // 这里只写行内错误，不再重复弹 toast，避免同一错误双报。
  } finally {
    // 登录用户清空后回填账号信息，保持表单可用
    prefillFromAuth()
    // 验证码答案一次性：无论成功还是失败都已被服务端 consume，必须换一张再让用户提交
    if (needCaptcha.value) captchaRef.value?.refresh()
    submitting.value = false
  }
}

const toggleLike = async (item: GuestbookItem) => {
  // 后端 like 为纯计数 +1（无取消点赞）：已赞直接拒绝重复请求
  if (item.liking || item.liked) return
  item.liking = true
  try {
    // 点赞响应结构在运行时确定，返回 unknown 以便后续守卫。
    // 注意：apiFetch 已按 import.meta.server/client 双端推导 baseURL，
    // 路径必须不带 /api 前缀（runtimeConfig.apiBase / public.apiBase 已自带 /api）。
    // 失败时 apiFetch 自动 toast（不再静默）并抛出。
    const resp = await apiFetch<unknown>(`/guestbook/${item.id}/like`, {
      method: 'POST'
    })
    const r = (resp ?? {}) as Record<string, unknown>
    const rd = (r.data ?? {}) as Record<string, unknown>
    const countRaw
      = (typeof r.likes_count === 'number' ? r.likes_count : undefined)
        ?? (typeof rd.likes_count === 'number' ? rd.likes_count : undefined)
        ?? (item.likesCount + 1)
    item.liked = true
    item.likesCount = typeof countRaw === 'number' ? countRaw : item.likesCount
  } catch {
    // apiFetch 已 toast，这里仅终止本地状态
  } finally {
    item.liking = false
  }
}
</script>
