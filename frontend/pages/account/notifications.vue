<!--
  个人中心 · 站内通知（/account/notifications）。

  这一页补的是"后端有、前台没有"的那一整块：`/api/notifications` 八条端点全部只要求
  CurrentUser（任何登录用户），但落地 UI 此前只有后台 AdminHeader 的通知面板。
  结果是普通成员收到"评论已通过""有人回复你"之后，前台没有任何地方能读到它。

  四条写法契约：
  1. ssr 档位由 `nuxt.config.ts` 的 `/account/**` routeRules 精准反选（页面不重复声明），
     所以这里可以在客户端生命周期里直接用 apiFetch 系的 useAdminManage 函数，
     不需要再为 SSR 首屏包一层 useAPI。
  2. 未读数只信 `GET /notifications` 响应里的 `unread_count`（后端按 recipient_id 算），
     不把当前页 `items` 里未读条数当全站未读——列表是分页的。
  3. 列表读取失败必须显示错误态 + 重试，不能回退成"暂无通知"：后者会让用户以为
     通知被清空了。fetchNotifications 默认 silentToast，就是为了让页面自己摆错误面板。
  4. 标题/正文来自 UGC（留言、评论摘要），一律走文本插值，绝不 v-html。
-->
<template>
  <div class="mx-auto w-full max-w-3xl px-4 py-8">
    <header class="mb-6 flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <Bell
          class="size-5 text-primary"
          aria-hidden="true"
        />
        <h1 class="text-xl font-semibold">
          {{ t('notifications.title') }}
        </h1>
        <Badge
          v-if="unreadCount > 0"
          variant="secondary"
        >
          {{ t('notifications.unreadCount', { count: unreadCount }) }}
        </Badge>
      </div>
      <NuxtLink
        :to="accountHref"
        class="text-sm text-muted-foreground underline-offset-4 hover:underline"
      >
        {{ t('account.title') }}
      </NuxtLink>
    </header>

    <div class="mb-4 flex flex-wrap items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        :aria-pressed="!unreadOnly"
        :class="['rounded-[10px]', unreadOnly ? 'opacity-60' : 'font-medium']"
        @click="setFilter(false)"
      >
        {{ t('notifications.all') }}
      </Button>
      <Button
        variant="outline"
        size="sm"
        :aria-pressed="unreadOnly"
        :class="['rounded-[10px]', unreadOnly ? 'font-medium' : 'opacity-60']"
        @click="setFilter(true)"
      >
        {{ t('notifications.unreadOnly') }}
      </Button>
      <Button
        variant="ghost"
        size="sm"
        class="rounded-[10px] text-xs"
        :disabled="busy || unreadCount === 0"
        @click="handleMarkAllRead"
      >
        <CheckCheck data-icon="inline-start" />
        {{ t('notifications.markAllRead') }}
      </Button>
      <Button
        variant="ghost"
        size="sm"
        class="ml-auto rounded-[10px]"
        :aria-label="t('common.retry')"
        :disabled="busy"
        @click="load"
      >
        <RefreshCw data-icon="inline-start" />
      </Button>
    </div>

    <div
      v-if="busy && items.length === 0"
      class="flex flex-col gap-3"
    >
      <Skeleton
        v-for="i in 3"
        :key="`notif-skeleton-${i}`"
        class="h-20 rounded-[12px]"
      />
    </div>

    <Card
      v-else-if="loadError"
      class="py-12 text-center"
    >
      <CardContent class="flex flex-col items-center gap-3">
        <AlertCircle
          class="size-8 text-destructive"
          aria-hidden="true"
        />
        <p class="text-sm text-muted-foreground">
          {{ t('notifications.loadFailed') }}
        </p>
        <Button
          variant="outline"
          size="sm"
          class="rounded-[10px]"
          @click="load"
        >
          {{ t('common.retry') }}
        </Button>
      </CardContent>
    </Card>

    <Card
      v-else-if="items.length === 0"
      class="py-16 text-center"
    >
      <CardContent class="flex flex-col items-center gap-3">
        <Inbox
          class="size-8 text-muted-foreground"
          aria-hidden="true"
        />
        <p class="text-sm text-muted-foreground">
          {{ t('notifications.empty') }}
        </p>
      </CardContent>
    </Card>

    <ul
      v-else
      class="flex flex-col gap-3"
    >
      <li
        v-for="row in items"
        :key="row.id"
        class="card-surface flex items-start gap-3 p-4"
      >
        <UserAvatar
          v-if="row.actor"
          :avatar="row.actor.avatar"
          :resolved-avatar-url="row.actor.resolved_avatar_url"
          :seed="String(row.actor.id)"
          :name="actorLabel(row)"
          size="sm"
        />
        <div
          v-else
          class="size-8 shrink-0 rounded-full bg-muted"
          aria-hidden="true"
        />
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2">
            <template v-if="!row.is_read">
              <span
                class="size-2 shrink-0 rounded-full bg-primary"
                aria-hidden="true"
              />
              <span class="sr-only">{{ t('notifications.unread') }}</span>
            </template>
            <h2
              class="truncate text-sm font-medium"
              :class="{ 'text-muted-foreground': row.is_read }"
            >
              {{ row.title }}
            </h2>
          </div>
          <p
            v-if="row.message"
            class="mt-1 line-clamp-3 text-sm text-muted-foreground"
          >
            {{ row.message }}
          </p>
          <div class="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
            <span>{{ fmtTime(row.created_at) }}</span>
            <NuxtLink
              v-if="row.link"
              :to="localeHref(row.link)"
              class="inline-flex items-center gap-1 text-primary underline-offset-4 hover:underline"
            >
              <ExternalLink class="size-3.5" />
              {{ t('notifications.open') }}
            </NuxtLink>
          </div>
        </div>
        <div class="flex shrink-0 items-center gap-1">
          <Button
            v-if="!row.is_read"
            variant="ghost"
            size="sm"
            class="h-8 rounded-[10px] text-xs"
            :disabled="busyId === row.id"
            @click="handleMarkRead(row)"
          >
            {{ t('notifications.markRead') }}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            class="h-8 rounded-[10px] text-xs text-destructive hover:text-destructive"
            :aria-label="t('common.delete')"
            :disabled="busyId === row.id"
            @click="handleDelete(row)"
          >
            <Trash2 />
          </Button>
        </div>
      </li>
    </ul>

    <div
      v-if="totalPages > 1"
      class="mt-6 flex items-center justify-between"
    >
      <Button
        variant="outline"
        size="sm"
        class="rounded-[10px]"
        :disabled="page <= 1 || busy"
        @click="goPage(page - 1)"
      >
        {{ t('account.prevPage') }}
      </Button>
      <span class="text-xs text-muted-foreground">
        {{ t('notifications.pageInfo', { page, total: totalPages }) }}
      </span>
      <Button
        variant="outline"
        size="sm"
        class="rounded-[10px]"
        :disabled="page >= totalPages || busy"
        @click="goPage(page + 1)"
      >
        {{ t('account.nextPage') }}
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertCircle, Bell, CheckCheck, ExternalLink, Inbox, RefreshCw, Trash2 } from '@lucide/vue'
import { Badge } from '~~/components/ui/badge'
import { Button } from '~~/components/ui/button'
import { Card, CardContent } from '~~/components/ui/card'
import { Skeleton } from '~~/components/ui/skeleton'
import UserAvatar from '~~/components/UserAvatar.vue'
import { useToast } from '~~/composables/useToast'
import { applyLocalePrefix } from '~~/composables/useSeo'
import { useLocaleLink } from '~~/composables/useLocaleLink'
import {
  deleteNotification,
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type AdminNotification
} from '~~/composables/useAdminManage'

definePageMeta({ layout: 'default', middleware: 'auth-required' })

const PAGE_SIZE = 20

const { t, locale } = useI18n()
const toast = useToast()

const items = ref<AdminNotification[]>([])
const unreadCount = ref(0)
const page = ref(1)
const totalPages = ref(0)
const unreadOnly = ref(false)
const busy = ref(false)
const busyId = ref<number | null>(null)
const loadError = ref(false)

const accountHref = computed(() => applyLocalePrefix('/account', locale.value))

/** 后端 link 既可能是站内路径也可能是外链：localeHref 对外链/锚点原样透传。 */
const { localeHref } = useLocaleLink()

function actorLabel(row: AdminNotification): string {
  return row.actor?.nickname || row.actor?.username || String(row.actor?.id ?? '')
}

function fmtTime(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(locale.value)
}

async function load() {
  busy.value = true
  loadError.value = false
  try {
    const res = await fetchNotifications({
      page: page.value,
      page_size: PAGE_SIZE,
      unread_only: unreadOnly.value
    })
    items.value = res.items
    unreadCount.value = res.unread_count
    totalPages.value = res.total_pages
  } catch {
    // fetchNotifications 走 silentToast：错误由上面的错误态承载，不再叠一条 toast。
    items.value = []
    totalPages.value = 0
    loadError.value = true
  } finally {
    busy.value = false
  }
}

function setFilter(value: boolean) {
  if (unreadOnly.value === value) return
  unreadOnly.value = value
  page.value = 1
  void load()
}

function goPage(next: number) {
  if (next < 1 || next > totalPages.value) return
  page.value = next
  void load()
}

async function handleMarkRead(row: AdminNotification) {
  if (busyId.value) return
  busyId.value = row.id
  try {
    await markNotificationRead(row.id)
    row.is_read = true
    if (unreadOnly.value) await load()
    else if (unreadCount.value > 0) unreadCount.value -= 1
  } catch {
    // 标已读是写操作：失败必须报（markNotificationRead 内部 silentToast，不会自己弹），
    // 但不能因此把整列通知换成错误态——列表本身是好的。
    toast.error(t('notifications.actionFailed'))
  } finally {
    busyId.value = null
  }
}

async function handleMarkAllRead() {
  if (busyId.value) return
  busyId.value = -1
  try {
    await markAllNotificationsRead({ silentToast: false })
    await load()
  } catch {
    // markAllNotificationsRead 默认弹错，这里只保留列表现状
  } finally {
    busyId.value = null
  }
}

async function handleDelete(row: AdminNotification) {
  if (busyId.value) return
  busyId.value = row.id
  try {
    await deleteNotification(row.id, { silentToast: false })
    await load()
  } catch {
    // deleteNotification 默认弹错，这里只保留列表现状
  } finally {
    busyId.value = null
  }
}

onMounted(() => {
  void load()
})
</script>
