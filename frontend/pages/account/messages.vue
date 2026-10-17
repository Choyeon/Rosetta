<!--
  个人中心 · 私信（/account/messages）。

  这一页是后端 `/api/messages*` 六条端点的前端落地面：会话列表（GET /messages/conversations）、
  会话正文（GET /messages/{user_id}）、发送（POST /messages）、整段标已读
  （PUT /messages/read-all/{user_id}）、未读总数（GET /messages/unread/count）。
  按单条标已读（PUT /messages/{message_id}/read）**刻意不接**：读正文那一条已经带副作用把
  整个会话置为已读，前端不存在「同一会话里只有某几条未读」可展示的状态。口径见
  `composables/useMessages.ts` 文件头与 `docs/API_COVERAGE.md`。

  三条契约决定了下面的写法：
  1. ssr 档位由 `nuxt.config.ts` 的 `/account/**` routeRules 精准反选（页面不重复声明），
     所以这里可以直接在 setup 期用 useAPI：没有首屏白屏问题，也没有 SSR 期无 token 的问题。
  2. 未读总数只能来自 `/messages/unread/count`：会话列表是分页的，翻页外的对端未读数拿不到，
     把本页的 `unread_count` 加总当成全站未读会少报。
  3. 会话行的锚点是 `user.id` 而不是消息 id（后端每个对端一行），所以选中态写进 `?to=`：
     可分享、浏览器前进后退可用、刷新不丢档，与 /account 的 tab/page 同机制。
-->
<template>
  <div class="mx-auto w-full max-w-6xl px-4 py-8">
    <header class="mb-6 flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <MessageSquare
          class="size-5 text-primary"
          aria-hidden="true"
        />
        <h1 class="text-xl font-semibold">
          {{ t('messages.title') }}
        </h1>
        <Badge
          v-if="unreadTotal"
          variant="secondary"
        >
          {{ t('messages.unreadTotal', { count: unreadTotal }) }}
        </Badge>
      </div>
      <NuxtLink
        :to="accountHref"
        class="text-sm text-muted-foreground underline-offset-4 hover:underline"
      >
        {{ t('account.title') }}
      </NuxtLink>
    </header>

    <p
      v-if="convError"
      class="mb-4 text-sm text-destructive"
    >
      {{ t('messages.loadFailed') }}
    </p>

    <div class="grid gap-6 lg:grid-cols-[19rem_1fr]">
      <!-- ===== 左：会话列表 ===== -->
      <Card class="overflow-hidden">
        <CardContent class="p-0">
          <ul
            v-if="conversations.length"
            class="divide-y"
          >
            <li
              v-for="row in conversations"
              :key="row.user.id"
              class="flex items-center gap-3 p-3 transition-colors hover:bg-muted/50"
            >
              <button
                type="button"
                class="flex min-w-0 flex-1 cursor-pointer items-center gap-3 text-left"
                :aria-current="peerId === row.user.id ? 'true' : undefined"
                @click="selectPeer(row.user.id)"
              >
                <UserAvatar
                  :avatar="row.user.avatar"
                  :resolved-avatar-url="row.user.resolved_avatar_url"
                  :seed="String(row.user.id)"
                  :name="peerLabel(row.user)"
                  size="sm"
                />
                <span class="min-w-0 flex-1">
                  <span class="flex items-center gap-2">
                    <span class="truncate text-sm font-medium">{{ peerLabel(row.user) }}</span>
                    <Badge
                      v-if="row.unread_count"
                      variant="destructive"
                      class="shrink-0"
                    >
                      {{ row.unread_count }}
                    </Badge>
                  </span>
                  <span class="block truncate text-xs text-muted-foreground">
                    {{ row.last_message.content }}
                  </span>
                </span>
              </button>
              <Button
                v-if="row.unread_count"
                variant="ghost"
                size="sm"
                class="shrink-0 text-xs"
                :disabled="markingId === row.user.id"
                :aria-label="t('messages.markRead')"
                @click="handleMarkRead(row.user.id)"
              >
                {{ t('messages.markRead') }}
              </Button>
            </li>
          </ul>
          <p
            v-else-if="convPending"
            class="p-4 text-sm text-muted-foreground"
          >
            {{ t('common.loading') }}
          </p>
          <p
            v-else
            class="flex items-center gap-2 p-4 text-sm text-muted-foreground"
          >
            <Inbox
              class="size-4"
              aria-hidden="true"
            />
            {{ t('messages.empty') }}
          </p>

          <div
            v-if="convTotalPages > 1"
            class="flex items-center justify-between border-t p-3"
          >
            <Button
              variant="outline"
              size="sm"
              :disabled="convPage <= 1"
              @click="gotoConvPage(convPage - 1)"
            >
              {{ t('common.previous') }}
            </Button>
            <span class="text-xs text-muted-foreground">{{ convPage }} / {{ convTotalPages }}</span>
            <Button
              variant="outline"
              size="sm"
              :disabled="convPage >= convTotalPages"
              @click="gotoConvPage(convPage + 1)"
            >
              {{ t('common.next') }}
            </Button>
          </div>
        </CardContent>
      </Card>

      <!-- ===== 右：会话正文 + 撰写 ===== -->
      <Card class="flex min-h-[24rem] flex-col">
        <CardContent class="flex flex-1 flex-col gap-3 p-4">
          <template v-if="peerId">
            <div class="flex items-center gap-2 border-b pb-3">
              <Button
                variant="ghost"
                size="sm"
                class="lg:hidden"
                :aria-label="t('common.back')"
                @click="clearPeer"
              >
                <ArrowLeft data-icon="inline-start" />
                {{ t('common.back') }}
              </Button>
              <UserAvatar
                v-if="threadPeer"
                :avatar="threadPeer.avatar"
                :resolved-avatar-url="threadPeer.resolved_avatar_url"
                :seed="String(threadPeer.id)"
                :name="peerLabel(threadPeer)"
                size="sm"
              />
              <span class="truncate text-sm font-medium">
                {{ threadPeer ? peerLabel(threadPeer) : '' }}
              </span>
            </div>

            <div class="flex-1 space-y-2 overflow-y-auto">
              <p
                v-if="threadPending"
                class="text-sm text-muted-foreground"
              >
                {{ t('common.loading') }}
              </p>
              <!-- 后端故障必须和"这个会话还没有消息"分开：两者都渲染成空列表时，
                   用户会以为对方没回过话，实际是请求挂了。 -->
              <div
                v-else-if="threadError"
                class="flex flex-col items-start gap-2"
              >
                <p class="text-sm text-error">
                  {{ t('messages.loadFailed') }}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  @click="refreshThread()"
                >
                  {{ t('common.retry') }}
                </Button>
              </div>
              <p
                v-else-if="!threadItems.length"
                class="text-sm text-muted-foreground"
              >
                {{ t('messages.emptyThread') }}
              </p>
              <div
                v-for="item in threadItems"
                :key="item.id"
                class="flex"
                :class="item.is_mine ? 'justify-end' : 'justify-start'"
              >
                <div
                  class="max-w-[80%] whitespace-pre-wrap break-words rounded-lg px-3 py-2 text-sm"
                  :class="item.is_mine ? 'bg-primary text-primary-foreground' : 'bg-muted'"
                >
                  {{ item.content }}
                  <span class="mt-1 block text-[11px] opacity-70">{{ fmtTime(item.created_at) }}</span>
                </div>
              </div>
            </div>

            <div class="flex flex-col gap-2 border-t pt-3">
              <Textarea
                v-model="draft"
                rows="3"
                :placeholder="t('messages.placeholder')"
                :aria-label="t('messages.placeholder')"
              />
              <div class="flex items-center justify-between gap-2">
                <span class="text-xs text-muted-foreground">{{ t('messages.limit') }}</span>
                <Button
                  size="sm"
                  :disabled="sending || !draft.trim()"
                  @click="handleSend"
                >
                  <Send data-icon="inline-start" />
                  {{ sending ? t('messages.sending') : t('messages.send') }}
                </Button>
              </div>
            </div>
          </template>
          <p
            v-else
            class="self-center text-sm text-muted-foreground"
          >
            {{ t('messages.selectHint') }}
          </p>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowLeft, Inbox, MessageSquare, Send } from '~~/lib/lucide-svg-icons'
import { Badge } from '~~/components/ui/badge'
import { Button } from '~~/components/ui/button'
import { Card, CardContent } from '~~/components/ui/card'
import { Textarea } from '~~/components/ui/textarea'
import UserAvatar from '~~/components/UserAvatar.vue'
import { useAPI } from '~~/composables/useApi'
import {
  useMessages,
  type MessageConversationList,
  type MessagePeer,
  type MessageThread
} from '~~/composables/useMessages'

definePageMeta({ layout: 'default', middleware: 'auth-required' })

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const messagesAPI = useMessages()

const accountHref = computed(() => applyLocalePrefix('/account', locale.value))

// ===== 选中态：?to= 对端用户 id（见文件头第 3 条） =====
const peerId = computed(() => {
  const raw = Number(route.query.to ?? 0)
  return Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : null
})

function writePeer(value: number | null) {
  const query = { ...route.query }
  if (value == null) delete query.to
  else query.to = String(value)
  void router.replace({ query })
}
const selectPeer = (id: number) => writePeer(id)
const clearPeer = () => writePeer(null)

// ===== 会话列表 =====
const convPage = ref(1)
const {
  data: convData,
  pending: convPending,
  error: convError,
  refresh: refreshConv
} = useAPI<MessageConversationList>('/messages/conversations', {
  query: computed(() => ({ page: convPage.value, page_size: 20 })),
  key: computed(() => `messages:conversations:${convPage.value}`)
})
const conversations = computed(() => convData.value?.items ?? [])
const convTotalPages = computed(() => convData.value?.total_pages ?? 0)
const gotoConvPage = (next: number) => {
  if (next < 1 || next > convTotalPages.value) return
  convPage.value = next
}

// ===== 会话正文：URL 随选中的对端变化；未选中时不发请求 =====
// immediate 只在 setup 期求值一次：直接带 ?to= 进来时首轮就要发。
// 不用 useFetch 的 watch: [peerId]：「返回」把 peerId 置回 null 时它也会触发，
// 于是发出 GET /api/messages/0 ——后端必定 404，前端还会跟着弹一条无意义错误，
// 而正文区本来就是 v-if="peerId"。改成显式 watch，只在真的选中某人时重取。
const {
  data: threadData,
  pending: threadPending,
  error: threadError,
  refresh: refreshThread
} = useAPI<MessageThread>(() => `/messages/${peerId.value ?? 0}`, {
  key: computed(() => `messages:thread:${peerId.value ?? 'none'}`),
  immediate: peerId.value != null
})
watch(peerId, (next) => {
  if (next != null) void refreshThread()
})
const threadItems = computed(() => threadData.value?.items ?? [])
const threadPeer = computed<MessagePeer | null>(() => threadData.value?.other_user ?? null)

// 读正文这个动作本身会把该对端的未读置为已读（后端副作用），
// 所以每次正文到手都要让列表和未读总数重新对齐，否则角标会停在旧值。
watch(threadData, () => {
  void refreshConv()
  void loadUnread()
})

// ===== 未读总数（角标） =====
const unreadTotal = ref(0)
async function loadUnread() {
  const res = await messagesAPI.getUnreadMessageCount()
  unreadTotal.value = typeof res?.count === 'number' ? res.count : 0
}
void loadUnread()

// ===== 整段标已读 =====
const markingId = ref<number | null>(null)
async function handleMarkRead(peer: number) {
  if (markingId.value) return
  markingId.value = peer
  try {
    await messagesAPI.markConversationRead(peer)
    await Promise.all([refreshConv(), loadUnread()])
  } catch {
    // apiFetch 已统一 toast（getUnreadMessageCount 走静默口，失败留旧值）
  } finally {
    markingId.value = null
  }
}

// ===== 发送 =====
const draft = ref('')
const sending = ref(false)
async function handleSend() {
  const peer = peerId.value
  const text = draft.value.trim()
  if (!peer || !text || sending.value) return
  sending.value = true
  try {
    await messagesAPI.sendPrivateMessage(peer, text)
    draft.value = ''
    await Promise.all([refreshThread(), refreshConv()])
  } catch {
    // 对端不存在（404）/ 给自己发（400）都由 apiFetch toast，正文留在输入框
  } finally {
    sending.value = false
  }
}

function peerLabel(user: MessagePeer) {
  return user.nickname || user.username
}

function fmtTime(iso: string) {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(locale.value)
}

useNoindexPage()
</script>
