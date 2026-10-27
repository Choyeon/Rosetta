<!--
  待发布队列：`/api/admin/posts/scheduled` 三条口（列表 / 改期 / 取消）的唯一消费方。
  定时发布此前只能"在文章编辑页里排一次"，之后没有任何地方能看见排了什么、什么时候发，
  也没法改——到点没发出去才发现状态是 scheduled 而计划时间早过去了。

  三条口径都是这个路由族特有的坑：
  ① 列表口**有写副作用**（读之前先把到期的推进成 published），所以本页不做静默轮询，只手动刷新；
     后台多开一个标签页就等于给扫描器加了一次触发，不该由 UI 顺手替管理员决定发布时机。
  ② `scheduled_at` ↔ `<input type="datetime-local">` 必须走 `lib/datetime` 的换算：输入框的值是
     本地墙钟、库里存的是 UTC，直接 `slice(0,16)` 回填再原值提交会让东八区的"10:00 发布"在 18:00 生效。
  ③ 取消一条 scheduled 文章会同时回到 draft（后端行为，否则留下"等待发布但没有计划时间"的死状态），
     提示语必须跟着说清"已回到草稿"，不然作者以为它还会按时发出去。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="待发布队列"
      description="查看并调整定时发布中的文章；到点的文章由服务端扫描器自动发出"
      :icon="CalendarClock"
    >
      <template #actions>
        <Button
          variant="outline"
          size="sm"
          class="rounded-xl"
          :disabled="loading"
          @click="load()"
        >
          <RefreshCw
            data-icon="inline-start"
            :class="loading ? 'animate-spin' : ''"
          />
          刷新
        </Button>
      </template>
    </AdminPageHeader>

    <Alert
      v-if="error"
      variant="destructive"
      class="rounded-xl"
    >
      <AlertTriangle class="size-4" />
      <AlertTitle>队列读取失败</AlertTitle>
      <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
        <span>{{ error }}</span>
        <Button
          variant="outline"
          size="sm"
          class="rounded-lg shrink-0"
          :disabled="loading"
          @click="load()"
        >
          <RotateCcw data-icon="inline-start" />
          重试
        </Button>
      </AlertDescription>
    </Alert>

    <div class="grid grid-cols-2 gap-4 lg:grid-cols-3">
      <StatCard
        title="等待发布"
        :value="loading ? 0 : rows.length"
        :icon="CalendarClock"
        accent="primary"
        :loading="loading"
        :hint="error ? '读数不可用' : 'scheduled_at 还没到点的文章'"
      />
      <StatCard
        title="最近一篇"
        :value="loading ? '—' : (nextPost ? countdown(nextPost.scheduled_at) : '无')"
        :icon="Clock"
        accent="info"
        :loading="loading"
        :sub-value="nextPost ? displayTitle(nextPost.title) : ''"
        :hint="error ? '读数不可用' : '按 scheduled_at 升序的第一篇'"
      />
      <StatCard
        title="发布节奏"
        :value="loading ? '—' : '每 60 秒'"
        :icon="Activity"
        accent="sage"
        :loading="loading"
        hint="服务端扫描器间隔；本页不轮询，因为列表口读前会先推进到期文章"
      />
    </div>

    <AdminCard class="rounded-2xl">
      <div class="flex flex-col gap-0 p-5">
        <h3 class="text-sm font-semibold text-foreground">
          队列明细
        </h3>
        <p class="mt-1 text-xs text-muted-foreground">
          改期与取消都只动排期，不改正文；「立即发布」把计划时间设为过去，服务端当场发布并清空排期。
        </p>

        <div
          v-if="loading && rows.length === 0"
          class="mt-4 flex flex-col gap-2"
        >
          <Skeleton
            v-for="n in 3"
            :key="n"
            class="h-16 w-full rounded-xl"
          />
        </div>

        <div
          v-else-if="rows.length === 0"
          class="mt-4 flex items-center gap-3 rounded-xl border border-dashed border-border/70 bg-muted/20 px-4 py-6 text-sm text-muted-foreground"
        >
          <Inbox class="size-5 shrink-0" />
          <span>{{ error ? '队列暂不可用' : '没有等待发布的文章' }}</span>
        </div>

        <ul
          v-else
          class="mt-3 flex flex-col divide-y divide-border/60"
        >
          <li
            v-for="row in rows"
            :key="row.id"
            class="flex flex-col gap-3 py-4"
          >
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="min-w-0 flex-1">
                <div class="flex flex-wrap items-center gap-2">
                  <span
                    class="inline-flex items-center rounded-full px-2 h-5 text-[11px] font-semibold"
                    :class="row.status === 'scheduled'
                      ? 'bg-primary-muted text-primary-muted-foreground'
                      : 'bg-warning-muted text-warning-muted-foreground'"
                  >
                    {{ row.status === 'scheduled' ? '等待发布' : '历史排期' }}
                  </span>
                  <NuxtLink
                    :to="`/admin/content/posts/${row.id}/edit`"
                    class="text-sm font-medium text-foreground hover:text-primary hover:underline underline-offset-4 truncate"
                  >
                    {{ displayTitle(row.title) }}
                  </NuxtLink>
                </div>
                <p class="mt-1 text-xs text-muted-foreground truncate">
                  /posts/{{ row.slug }} · 计划 {{ localWallClock(row.scheduled_at) }}
                  · {{ countdown(row.scheduled_at) }}
                </p>
              </div>

              <div class="flex items-center gap-2 shrink-0">
                <Button
                  variant="ghost"
                  size="sm"
                  class="rounded-[10px] h-9 text-xs"
                  :disabled="busyId === row.id"
                  @click="startEdit(row)"
                >
                  <CalendarPlus data-icon="inline-start" />
                  改期
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  class="rounded-[10px] h-9 text-xs"
                  :disabled="busyId === row.id"
                  @click="publishNow(row)"
                >
                  <Send data-icon="inline-start" />
                  立即发布
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  class="rounded-[10px] h-9 text-xs"
                  :disabled="busyId === row.id"
                  @click="cancel(row)"
                >
                  <CalendarX data-icon="inline-start" />
                  取消定时
                </Button>
              </div>
            </div>

            <!-- 改期表单就地展开：跳走再回来会丢掉这篇的上下文 -->
            <div
              v-if="editingId === row.id"
              class="flex flex-wrap items-end gap-3 rounded-xl border border-border/70 bg-muted/20 p-3"
            >
              <div class="flex flex-col gap-1.5">
                <Label
                  :for="`schedule-${row.id}`"
                  class="text-xs text-muted-foreground"
                >
                  新的发布时间（本地时区）
                </Label>
                <Input
                  :id="`schedule-${row.id}`"
                  v-model="editValue"
                  type="datetime-local"
                  class="h-9 rounded-[10px] text-sm"
                />
              </div>
              <p
                v-if="editError"
                class="text-xs text-destructive"
              >
                {{ editError }}
              </p>
              <div class="flex items-center gap-2">
                <Button
                  size="sm"
                  class="rounded-[10px] h-9"
                  :disabled="busyId === row.id"
                  @click="save(row)"
                >
                  <Check data-icon="inline-start" />
                  保存
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  class="rounded-[10px] h-9"
                  @click="closeEdit"
                >
                  取消
                </Button>
              </div>
            </div>
          </li>
        </ul>
      </div>
    </AdminCard>
  </div>
</template>

<script setup lang="ts">
import { apiFetch } from '~~/composables/useApi'
import { extractApiErrorMessage } from '~~/lib/utils'
import { fromDateTimeLocal, toDateTimeLocal } from '~~/lib/datetime'
import { scheduledAtError, slugSourceTitle } from '~~/lib/postEditor'
import { useToast } from '~~/composables/useToast'
import {
  Activity,
  CalendarClock,
  CalendarPlus,
  CalendarX,
  Check,
  Clock,
  Inbox,
  RefreshCw,
  RotateCcw,
  AlertTriangle,
  Send
} from '@lucide/vue'

// Button / Input / Label / Alert / Skeleton / AdminCard / AdminPageHeader / StatCard
// 由 Nuxt 组件自动导入解析，与 monitoring.vue 同口径，不在页面里重复 import。

definePageMeta({ ssr: false, layout: 'admin' })

/** 与 `backend/api/scheduled_posts.py::ScheduledPostDoc` 对齐的投影（title 是 i18n dict）。 */
type ScheduledPost = {
  id: number
  title: Record<string, string>
  slug: string
  status: string
  scheduled_at?: string | null
  published_at?: string | null
  author_id?: number | null
  cover_image?: string | null
}

const toast = useToast()

const rows = ref<ScheduledPost[]>([])
const loading = ref(false)
const error = ref('')
const busyId = ref<number | null>(null)
const editingId = ref<number | null>(null)
const editValue = ref('')
const editError = ref('')

/** 列表口按 scheduled_at 升序返回，第一篇就是下一个要发出去的。 */
const nextPost = computed(() => rows.value[0] ?? null)

function displayTitle(title?: Record<string, string> | null) {
  return slugSourceTitle(title) || '(无标题)'
}

function localWallClock(iso?: string | null) {
  const value = toDateTimeLocal(iso)
  return value ? value.replace('T', ' ') : '—'
}

/**
 * 剩余/超时读数。到点却仍在队列里＝扫描器还没跑或没起来，必须显式说"已到点"，
 * 不能显示"0 分钟后"——那是管理员最需要看出来的一条异常。
 */
function countdown(iso?: string | null) {
  const raw = (iso ?? '').trim()
  if (!raw) return '无排期'
  const at = new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(raw) ? raw : `${raw}Z`).getTime()
  if (Number.isNaN(at)) return '时间不可读'
  const diff = at - Date.now()
  if (diff <= 0) return '已到点'
  const minutes = Math.round(diff / 60_000)
  if (minutes < 60) return `${minutes} 分钟后`
  const hours = Math.round(minutes / 60)
  if (hours < 48) return `${hours} 小时后`
  return `${Math.round(hours / 24)} 天后`
}

async function load() {
  loading.value = true
  try {
    const data = await apiFetch<ScheduledPost[]>('/admin/posts/scheduled', { silentToast: true })
    rows.value = Array.isArray(data) ? data : []
    error.value = ''
  } catch (err) {
    error.value = extractApiErrorMessage(err, '待发布队列获取失败')
  } finally {
    loading.value = false
  }
}

function startEdit(row: ScheduledPost) {
  editingId.value = row.id
  // 回填用本地墙钟：直接 slice ISO 字符串会把 UTC 当成本地时间再偏移一次
  editValue.value = toDateTimeLocal(row.scheduled_at)
  editError.value = ''
}

function closeEdit() {
  editingId.value = null
  editValue.value = ''
  editError.value = ''
}

/** 一次只允许一篇在写：并发改两篇会把后一次的响应覆盖前一次的读数。 */
async function mutate(row: ScheduledPost, action: () => Promise<{ message?: string }>) {
  busyId.value = row.id
  try {
    const res = await action()
    toast.success(res?.message ?? '已更新排期')
    closeEdit()
    await load()
    return true
  } catch (err) {
    toast.error(extractApiErrorMessage(err, '操作失败'))
    return false
  } finally {
    busyId.value = null
  }
}

async function save(row: ScheduledPost) {
  const iso = fromDateTimeLocal(editValue.value)
  const invalid = scheduledAtError('scheduled', iso)
  if (invalid) {
    // 就地报错而不是 toast：后端对"不晚于现在"的时间会直接发布（400 都不会回），
    // 让管理员看到字段红字才有机会改，toast 一闪而过等于没提示。
    editError.value = invalid
    return
  }
  editError.value = ''
  await mutate(row, () =>
    apiFetch<{ message?: string }>(`/admin/posts/${row.id}/schedule`, {
      method: 'PUT',
      silentToast: true,
      body: { scheduled_at: iso, status: 'scheduled' }
    })
  )
}

async function publishNow(row: ScheduledPost) {
  // 传一个明确在过去的时间：PUT 口对"scheduled_at <= now"就地发布并清空排期，
  // 比等下一个 60s 扫描周期更符合点击语义。
  const past = new Date(Date.now() - 60_000).toISOString()
  await mutate(row, () =>
    apiFetch<{ message?: string }>(`/admin/posts/${row.id}/schedule`, {
      method: 'PUT',
      silentToast: true,
      body: { scheduled_at: past, status: 'published' }
    })
  )
}

async function cancel(row: ScheduledPost) {
  await mutate(row, () =>
    apiFetch<{ message?: string }>(`/admin/posts/${row.id}/schedule`, {
      method: 'DELETE',
      silentToast: true
    })
  )
}

onMounted(load)
</script>
