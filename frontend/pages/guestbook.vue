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

    <Card class="mb-12 border-dashed">
      <CardHeader class="pb-4">
        <CardTitle class="text-lg flex items-center gap-2">
          <PenLine class="size-4 text-muted-foreground" />
          {{ t('guestbook.writeMessage') }}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <Input
            v-model="form.author_name"
            :placeholder="t('guestbook.nickname')"
            :disabled="submitting"
          />
          <Input
            v-model="form.author_email"
            type="email"
            :placeholder="t('guestbook.email')"
            :disabled="submitting"
          />
          <Input
            v-model="form.author_website"
            :placeholder="t('guestbook.website')"
            :disabled="submitting"
          />
        </div>
        <Textarea
          v-model="form.content"
          :placeholder="t('guestbook.contentPlaceholder')"
          rows="4"
          class="resize-none mb-4"
          :disabled="submitting"
        />
        <div class="flex justify-end">
          <Button
            :disabled="submitting"
            @click="submitGuestbook"
          >
            <Send
              v-if="!submitting"
              class="size-4 mr-2"
            />
            <svg
              v-else
              class="animate-spin size-4 mr-2"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="3"
                class="opacity-25"
              />
              <path
                fill="currentColor"
                d="M4 12a8 8 0 0 1 8-8V0C5.37 0 0 5.37 0 12h4Z"
              />
            </svg>
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

    <div
      v-if="pending && guestbookList.length === 0"
      class="space-y-6 mb-10"
    >
      <div
        v-for="i in 3"
        :key="i"
        class="p-6 rounded-xl bg-card border border-border/60 animate-pulse"
      >
        <div class="flex gap-4">
          <div class="size-10 rounded-full bg-muted shrink-0" />
          <div class="flex-1 space-y-3">
            <div class="flex items-center gap-2">
              <div class="w-24 h-4 rounded-full bg-muted" />
              <div class="w-16 h-3 rounded-full bg-muted" />
            </div>
            <div class="space-y-2">
              <div class="w-full h-4 rounded-full bg-muted" />
              <div class="w-4/5 h-4 rounded-full bg-muted" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <div
      v-else
      class="space-y-6"
    >
      <div
        v-for="item in guestbookList"
        :key="item.id"
        class="relative"
      >
        <Card class="transition-all hover:shadow-soft duration-300">
          <CardContent class="p-6">
            <div class="flex gap-4">
              <Avatar class="size-10 shrink-0">
                <AvatarImage
                  :src="item.avatar ?? ''"
                  :alt="item.nickname ?? ''"
                />
                <AvatarFallback>{{ item.nickname?.[0]?.toUpperCase() || 'G' }}</AvatarFallback>
              </Avatar>
              <div class="flex-1 min-w-0">
                <div class="flex flex-wrap items-center gap-2 mb-1">
                  <span class="font-medium">{{ item.nickname }}</span>
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
                    class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
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
      v-if="!pending && guestbookList.length === 0"
      class="text-center py-20"
    >
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <MessageSquare class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">
        {{ t('guestbook.noMessages') }}
      </h3>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Badge } from '~~/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { useI18n } from 'vue-i18n'
import { MessageSquare, PenLine, Send, Heart } from '@lucide/vue'
import { useAPI } from '~~/composables/useApi'

definePageMeta({ layout: 'default' })

const { t } = useI18n()

interface GuestbookItem {
  id: number
  nickname: string
  author_email?: string
  website?: string
  avatar?: string
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

const { locale } = useI18n()

// 真实接口：GET /api/guestbook?page=1&page_size=30&status=approved
const {
  data: gbResp,
  pending,
  refresh
} = await useAPI<Paginated<unknown>>('/guestbook', {
  query: {
    page: 1,
    page_size: 30,
    status: 'approved',
    lang: locale
  }
})

const guestbookList = computed<GuestbookItem[]>(() => {
  const items = (gbResp.value?.items ?? []) as unknown[]
  return items.map((raw) => {
    const r = (raw ?? {}) as Record<string, unknown>
    const pickStr = (k: string, fallback = '') => (typeof r[k] === 'string' ? r[k] : fallback)
    const pickNum = (k: string, fallback = 0) => (typeof r[k] === 'number' ? r[k] : fallback)
    return {
      id: pickNum('id', 0),
      nickname: pickStr('author_name') || pickStr('nickname'),
      author_email: pickStr('author_email') || undefined,
      website: pickStr('author_website') || pickStr('website') || undefined,
      avatar: pickStr('resolved_avatar_url') || pickStr('author_avatar') || pickStr('avatar') || undefined,
      content: pickStr('content'),
      created_at: pickStr('created_at') || new Date().toISOString(),
      likesCount: pickNum('likes_count', 0),
      liked: false,
      is_pinned: !!r.is_pinned,
      is_featured: !!r.is_featured,
      status: pickStr('status') || undefined
    }
  })
})

const MONTH_NAMES: Record<string, string[]> = {
  zh: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
  en: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
  ja: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
  zh_Hant: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
}
const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return ''
  const loc = String(locale.value || 'zh')
  const months = (MONTH_NAMES[loc] || MONTH_NAMES.en || []) as string[]
  const pad = (n: number) => n < 10 ? `0${n}` : String(n)
  const month = months[date.getMonth()] ?? ''
  const day = date.getDate()
  const hh = pad(date.getHours())
  const mm = pad(date.getMinutes())
  return `${month} ${day} ${hh}:${mm}`
}

const submitGuestbook = async () => {
  if (submitting.value) return
  if (!form.author_name.trim() || !form.content.trim()) return
  submitting.value = true
  submitError.value = null
  try {
    const payload: Record<string, string> = {
      author_name: form.author_name.trim(),
      content: form.content.trim()
    }
    if (form.author_email.trim()) payload.author_email = form.author_email.trim()
    if (form.author_website.trim()) payload.author_website = form.author_website.trim()

    await $fetch('/api/guestbook', {
      method: 'POST',
      baseURL: import.meta.client ? '' : (useRuntimeConfig().apiBase as string || ''),
      body: payload,
      headers: {
        'Accept-Language': locale.value || 'zh'
      }
    })

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
        || (typeof e.message === 'string' && e.message)
        || (t('guestbook.submitFailed') as string)
        || '提交失败，请稍后再试'
    submitError.value = String(msg)
  } finally {
    submitting.value = false
  }
}

const toggleLike = async (item: GuestbookItem) => {
  if (item.liking) return
  item.liking = true
  try {
    // 点赞响应结构在运行时确定，返回 unknown 以便后续守卫
    const resp = await $fetch<unknown>(`/api/guestbook/${item.id}/like`, {
      method: 'POST',
      baseURL: import.meta.client ? '' : (useRuntimeConfig().apiBase as string || '')
    })
    const r = (resp ?? {}) as Record<string, unknown>
    const rd = (r.data ?? {}) as Record<string, unknown>
    const countRaw
      = (typeof r.likes_count === 'number' ? r.likes_count : undefined)
        ?? (typeof rd.likes_count === 'number' ? rd.likes_count : undefined)
        ?? (item.likesCount + (item.liked ? -1 : 1))
    const count = typeof countRaw === 'number' ? countRaw : item.likesCount
    if (!item.liked) {
      item.liked = true
      item.likesCount = count
    }
  } catch {
    // 静默失败
  } finally {
    item.liking = false
  }
}
</script>
