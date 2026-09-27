<!--
  Webhook 配置页：端点 CRUD + 事件订阅（清单取自服务端 GET /webhooks/events 不硬编码）+ 测试投递/投递记录复发 + 密钥轮换。
  契约：secret 三态——非空=设置新值、显式清除传 ''、否则省略该字段由服务端保持原值，密钥保存后不再回显；
  轮换是即时后端动作（不等表单提交），明文仅在该次响应出现一次；测试/复发即使目标端点失败也返回 200，必须检查 result.success 字段。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="Webhook 配置"
      description="接入外部系统，订阅站点事件通知"
      :icon="Webhook"
    >
      <template #actions>
        <Button
          size="sm"
          class="shadow-sm"
          @click="openCreate()"
        >
          <Plus data-icon="inline-start" /> 新建 Webhook
        </Button>
      </template>
    </AdminPageHeader>

    <AdminCard class="overflow-hidden">
      <div class="p-0">
        <Alert
          v-if="!loading && loadError"
          variant="destructive"
          class="rounded-xl m-5"
        >
          <AlertTriangle class="size-4" />
          <AlertTitle>Webhook 列表加载失败</AlertTitle>
          <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
            <span>{{ loadError }}</span>
            <Button
              variant="outline"
              size="sm"
              class="rounded-lg shrink-0"
              @click="loadAll"
            >
              <RotateCcw data-icon="inline-start" />
              重试
            </Button>
          </AlertDescription>
        </Alert>

        <div
          v-if="loading"
          class="flex flex-col gap-3 p-6"
        >
          <Skeleton
            v-for="i in 5"
            :key="i"
            class="h-14 rounded-xl"
          />
        </div>

        <div
          v-else-if="items.length === 0"
          class="p-12"
        >
          <Alert
            variant="info"
            class="rounded-xl max-w-xl mx-auto"
          >
            <Info class="size-4" />
            <AlertTitle>暂无 Webhook</AlertTitle>
            <AlertDescription>新建 Webhook 可订阅文章、评论、用户等事件并推送到飞书 / GitHub / 通用 HTTP 端点。</AlertDescription>
          </Alert>
        </div>

        <div
          v-else
          class="overflow-x-auto"
        >
          <table class="w-full text-sm">
            <thead class="bg-muted/40 text-muted-foreground text-xs uppercase tracking-wide">
              <tr>
                <th class="text-left font-medium px-5 py-3">
                  名称
                </th>
                <th class="text-left font-medium px-5 py-3">
                  Provider
                </th>
                <th class="text-left font-medium px-5 py-3">
                  URL
                </th>
                <th class="text-left font-medium px-5 py-3">
                  监听事件
                </th>
                <th class="text-left font-medium px-5 py-3">
                  启用
                </th>
                <th class="text-left font-medium px-5 py-3">
                  最后触发
                </th>
                <th class="text-right font-medium px-5 py-3">
                  操作
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border">
              <tr
                v-for="w in items"
                :key="w.id"
                class="hover:bg-muted/30 transition-colors"
              >
                <td class="px-5 py-4">
                  <div class="font-semibold">
                    {{ w.name }}
                  </div>
                  <div class="text-xs text-muted-foreground font-mono">
                    #{{ w.id }}
                  </div>
                </td>
                <td class="px-5 py-4">
                  <Badge
                    :class="providerClass(w.provider)"
                    class="rounded-full text-[11px]"
                  >
                    <component
                      :is="providerIcon(w.provider)"
                      class="size-3 mr-1"
                    />
                    {{ providerLabel(w.provider) }}
                  </Badge>
                </td>
                <td class="px-5 py-4 max-w-[260px]">
                  <div
                    class="font-mono text-xs text-muted-foreground truncate"
                    :title="w.url"
                  >
                    {{ w.url }}
                  </div>
                </td>
                <td class="px-5 py-4">
                  <div class="flex flex-wrap gap-1 max-w-[280px]">
                    <Badge
                      v-for="e in w.events.slice(0, 2)"
                      :key="e"
                      variant="outline"
                      class="text-[11px] rounded-full"
                    >
                      {{ eventLabel(e) }}
                    </Badge>
                    <Badge
                      v-if="w.events.length > 2"
                      variant="secondary"
                      class="text-[11px] rounded-full"
                    >
                      +{{ w.events.length - 2 }}
                    </Badge>
                  </div>
                </td>
                <td class="px-5 py-4">
                  <Switch
                    :model-value="w.active"
                    :disabled="togglingId === w.id"
                    @update:model-value="toggleActive(w, $event)"
                  />
                </td>
                <td class="px-5 py-4 text-xs text-muted-foreground tabular-nums whitespace-nowrap">
                  {{ formatAdminDateTime(w.last_triggered_at, '未触发') }}
                </td>
                <td class="px-5 py-4">
                  <div class="flex items-center justify-end gap-1">
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger as-child>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            :disabled="triggeringId === w.id"
                            title="测试触发"
                            aria-label="测试触发 Webhook"
                            @click="handleTrigger(w)"
                          >
                            <Zap
                              v-if="triggeringId !== w.id"
                              data-icon="inline-start"
                              class="text-warning"
                            />
                            <Loader2
                              v-else
                              data-icon="inline-start"
                              class="animate-spin text-warning"
                            />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>测试触发</TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      title="投递记录"
                      aria-label="查看投递记录"
                      @click="openDeliveries(w)"
                    >
                      <History data-icon="inline-start" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      title="编辑"
                      aria-label="编辑 Webhook"
                      @click="openEdit(w)"
                    >
                      <Pencil data-icon="inline-start" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      class="text-error hover:text-error hover:bg-error-muted"
                      title="删除"
                      aria-label="删除 Webhook"
                      @click="handleDelete(w)"
                    >
                      <Trash2 data-icon="inline-start" />
                    </Button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </AdminCard>

    <Dialog v-model:open="dialogOpen">
      <DialogContent class="max-w-xl rounded-2xl">
        <DialogHeader>
          <DialogTitle>{{ editingId ? '编辑 Webhook' : '新建 Webhook' }}</DialogTitle>
          <DialogDescription>选择 Provider 并填写接收 URL 与订阅事件。</DialogDescription>
        </DialogHeader>
        <div class="flex flex-col gap-4 py-2">
          <div class="grid grid-cols-2 gap-4">
            <div class="flex flex-col gap-2">
              <Label
                for="wh-name"
                class="text-sm font-medium"
              >名称 <span class="text-error">*</span></Label>
              <Input
                id="wh-name"
                v-model="form.name"
                placeholder="如：飞书新评论通知"
                class="rounded-xl"
              />
            </div>
            <div class="flex flex-col gap-2">
              <Label
                for="wh-provider"
                class="text-sm font-medium"
              >Provider <span class="text-error">*</span></Label>
              <Select
                v-model="form.provider"
              >
                <SelectTrigger id="wh-provider">
                  <SelectValue placeholder="选择 Provider" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem
                    v-for="p in PROVIDERS"
                    :key="p.value"
                    :value="p.value"
                  >
                    {{ p.label }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div class="flex flex-col gap-2">
            <Label
              for="wh-url"
              class="text-sm font-medium"
            >接收 URL <span class="text-error">*</span></Label>
            <Input
              id="wh-url"
              v-model="form.url"
              placeholder="https://..."
              class="rounded-xl font-mono"
            />
            <p class="text-xs text-muted-foreground">
              仅支持 http/https；指向内网或保留地址会被服务端 SSRF 护栏拒绝。
            </p>
          </div>
          <div class="flex flex-col gap-2">
            <Label
              for="wh-secret"
              class="text-sm font-medium"
            >签名密钥 Secret</Label>
            <div class="relative">
              <Input
                id="wh-secret"
                v-model="form.secret"
                :type="showSecret ? 'text' : 'password'"
                :placeholder="editingHasSecret ? '已设置（留空保持不变）' : '留空则不进行签名校验'"
                class="rounded-xl pr-11 font-mono"
              />
              <button
                type="button"
                class="absolute right-2 top-1/2 -translate-y-1/2 size-7 inline-flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                :aria-label="showSecret ? '隐藏密钥' : '显示密钥'"
                @click="showSecret = !showSecret"
              >
                <Eye
                  v-if="!showSecret"
                  class="size-4"
                />
                <EyeOff
                  v-else
                  class="size-4"
                />
              </button>
            </div>
            <p class="text-xs text-muted-foreground">
              设置后每次投递附带 <code class="font-mono">X-Rosetta-Signature: sha256=&lt;hmac&gt;</code>，
              对实际发出的 JSON 字节计算。密钥保存后不再回显。
            </p>
            <Button
              v-if="editingHasSecret"
              variant="ghost"
              size="sm"
              class="self-start text-error hover:text-error hover:bg-error-muted"
              @click="clearSecret"
            >
              <KeyRound data-icon="inline-start" />
              清除已保存的密钥
            </Button>
            <Button
              v-if="editingId"
              variant="outline"
              size="sm"
              class="self-start"
              :disabled="rotating"
              @click="handleRotateSecret"
            >
              <RefreshCw
                data-icon="inline-start"
                :class="rotating ? 'animate-spin' : ''"
              />
              {{ rotating ? '轮换中…' : '轮换密钥（立即生效）' }}
            </Button>
            <Alert
              v-if="rotatedSecret"
              variant="warning"
            >
              <AlertTitle>新密钥仅此一次显示</AlertTitle>
              <AlertDescription>
                <p class="mb-2">
                  旧密钥已立即失效；下列明文请复制到接收方配置，关闭后无法再次查看。
                </p>
                <div class="flex items-center gap-2">
                  <code
                    class="flex-1 min-w-0 truncate rounded-md bg-muted px-2 py-1 font-mono text-xs"
                  >{{ rotatedSecret }}</code>
                  <Button
                    variant="outline"
                    size="sm"
                    @click="copyRotatedSecret"
                  >
                    <Copy data-icon="inline-start" />
                    复制
                  </Button>
                </div>
              </AlertDescription>
            </Alert>
          </div>
          <div class="flex flex-col gap-2">
            <Label class="text-sm font-medium">订阅事件（多选）</Label>
            <div
              v-if="eventCatalog.length === 0"
              class="rounded-xl border border-border p-4 bg-muted/20 text-sm text-muted-foreground"
            >
              事件清单加载失败，请重试列表后再配置订阅。
            </div>
            <div
              v-else
              class="rounded-xl border border-border p-4 grid grid-cols-2 gap-3 bg-muted/20"
            >
              <label
                v-for="ev in eventCatalog"
                :key="ev.type"
                class="flex items-start gap-2 cursor-pointer select-none p-2 rounded-lg hover:bg-muted transition-colors"
              >
                <Checkbox
                  :model-value="form.events.includes(ev.type)"
                  @update:model-value="toggleEvent(ev.type, $event)"
                />
                <div class="flex flex-col gap-0.5">
                  <div class="text-sm font-medium leading-tight">
                    {{ ev.description }}
                  </div>
                  <div class="text-xs text-muted-foreground leading-tight font-mono">
                    {{ ev.type }}
                  </div>
                </div>
              </label>
            </div>
          </div>
          <div class="flex items-center justify-between rounded-xl border border-border p-4 bg-muted/30">
            <div class="flex flex-col gap-0.5">
              <Label
                for="wh-active"
                class="text-sm font-medium"
              >启用 Webhook</Label>
              <p class="text-xs text-muted-foreground">
                关闭后不会再推送任何事件。
              </p>
            </div>
            <Switch
              id="wh-active"
              v-model="form.active"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            class="rounded-xl"
            @click="dialogOpen = false"
          >
            取消
          </Button>
          <Button
            :disabled="submitting"
            class="rounded-xl shadow-sm"
            @click="handleSubmit"
          >
            <Loader2
              v-if="submitting"
              data-icon="inline-start"
              class="animate-spin"
            />
            <Save
              v-else
              data-icon="inline-start"
            />
            {{ editingId ? '保存修改' : '创建 Webhook' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="deliveriesOpen">
      <DialogContent class="max-w-3xl rounded-2xl">
        <DialogHeader>
          <DialogTitle>投递记录 · {{ deliveriesTarget?.name }}</DialogTitle>
          <DialogDescription>
            最近 {{ DELIVERIES_LIMIT }} 条投递。失败记录可直接复发原始报文。
          </DialogDescription>
        </DialogHeader>
        <div
          v-if="deliveriesLoading"
          class="flex flex-col gap-3 py-2"
        >
          <Skeleton
            v-for="i in 4"
            :key="i"
            class="h-10 rounded-xl"
          />
        </div>
        <div
          v-else-if="deliveries.length === 0"
          class="py-8 text-sm text-muted-foreground text-center"
        >
          尚无投递记录。点击行内的「测试触发」可立即产生一条。
        </div>
        <div
          v-else
          class="overflow-x-auto max-h-[60vh]"
        >
          <table class="w-full text-sm">
            <thead class="bg-muted/40 text-muted-foreground text-xs uppercase tracking-wide sticky top-0">
              <tr>
                <th class="text-left font-medium px-3 py-2">
                  事件
                </th>
                <th class="text-left font-medium px-3 py-2">
                  结果
                </th>
                <th class="text-left font-medium px-3 py-2">
                  时间
                </th>
                <th class="text-right font-medium px-3 py-2">
                  操作
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border">
              <tr
                v-for="d in deliveries"
                :key="d.id"
              >
                <td class="px-3 py-2 font-mono text-xs">
                  {{ d.event_type }}
                </td>
                <td class="px-3 py-2">
                  <Badge
                    :variant="d.error ? 'destructive' : 'outline'"
                    class="rounded-full text-[11px]"
                  >
                    {{ d.error ? (d.status_code ?? '未送达') : (d.status_code ?? '—') }}
                  </Badge>
                  <div
                    v-if="d.error || d.response_body"
                    class="text-xs text-muted-foreground mt-1 break-all max-w-[360px]"
                    :title="d.error ?? d.response_body ?? ''"
                  >
                    {{ (d.error ?? d.response_body ?? '').slice(0, 120) }}
                  </div>
                </td>
                <td class="px-3 py-2 text-xs text-muted-foreground tabular-nums whitespace-nowrap">
                  {{ formatAdminDateTime(d.delivered_at ?? d.created_at, '—') }}
                </td>
                <td class="px-3 py-2 text-right">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    :disabled="retryingId !== null"
                    title="复发此条"
                    aria-label="复发此投递"
                    @click="handleRetry(d)"
                  >
                    <RotateCcw
                      v-if="retryingId !== d.id"
                      data-icon="inline-start"
                    />
                    <Loader2
                      v-else
                      data-icon="inline-start"
                      class="animate-spin"
                    />
                  </Button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            class="rounded-xl"
            @click="deliveriesOpen = false"
          >
            关闭
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <DangerConfirmDialog
      v-model:open="confirmOpen"
      title="确认删除 Webhook？"
      :description="`「${deleteTarget?.name ?? ''}」被删除后，对应的事件推送将立即停止且无法恢复。`"
      confirm-text="确认删除"
      :on-confirm="confirmDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  fetchAdminWebhooks,
  fetchAdminWebhookEvents,
  fetchAdminWebhookDeliveries,
  retryAdminWebhookDelivery,
  createAdminWebhook,
  updateAdminWebhook,
  deleteAdminWebhook,
  triggerAdminWebhook,
  regenerateAdminWebhookSecret,
  formatAdminDateTime,
  type AdminWebhook,
  type AdminWebhookEvent,
  type AdminWebhookDelivery,
  type AdminWebhookPayload
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import { extractApiErrorMessage } from '~~/lib/utils'
import {
  Webhook, Plus, Zap, Pencil, Trash2, Save, Loader2, Info, History, KeyRound,
  Eye, EyeOff, Mail, GitBranch, BellRing, Globe, AlertTriangle, RotateCcw,
  RefreshCw, Copy
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import AdminCard from '~~/components/admin/AdminCard.vue'
import { Skeleton } from '~~/components/ui/skeleton'
import { Badge } from '~~/components/ui/badge'
import { Switch } from '~~/components/ui/switch'
import { Checkbox } from '~~/components/ui/checkbox'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle
} from '~~/components/ui/dialog'
import { Label } from '~~/components/ui/label'
import { Input } from '~~/components/ui/input'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '~~/components/ui/select'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger
} from '~~/components/ui/tooltip'
import DangerConfirmDialog from '~~/components/admin/tools/DangerConfirmDialog.vue'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const DELIVERIES_LIMIT = 20

/** Provider 只是分类标签，投递格式对所有类型一致 */
const PROVIDERS = [
  { value: 'generic', label: '通用 Generic' },
  { value: 'github', label: 'GitHub' },
  { value: 'feishu', label: '飞书 Feishu' },
  { value: 'email', label: '邮件 Email' }
] as const

const loading = ref(true)
const loadError = ref('')
const items = ref<AdminWebhook[]>([])
/** 可订阅事件的唯一清单：来自 GET /webhooks/events，不在此处硬编码事件名 */
const eventCatalog = ref<AdminWebhookEvent[]>([])
const dialogOpen = ref(false)
const confirmOpen = ref(false)
const submitting = ref(false)
const togglingId = ref<number | null>(null)
const triggeringId = ref<number | null>(null)
const editingId = ref<number | null>(null)
const deleteTarget = ref<AdminWebhook | null>(null)
const showSecret = ref(false)
const editingHasSecret = ref(false)
const rotating = ref(false)
/** 轮换后一次性展示的明文密钥（关闭弹窗即丢） */
const rotatedSecret = ref('')

const deliveriesOpen = ref(false)
const deliveriesLoading = ref(false)
const deliveriesTarget = ref<AdminWebhook | null>(null)
const deliveries = ref<AdminWebhookDelivery[]>([])
const retryingId = ref<number | null>(null)

const emptyForm = () => ({
  name: '',
  provider: 'generic' as AdminWebhookPayload['provider'],
  url: '',
  /** '' = 未填（编辑时保持原值）；clearSecretFlag 才是显式清除 */
  secret: '',
  events: [] as string[],
  active: true
})
const form = ref(emptyForm())
const clearSecretFlag = ref(false)

function providerLabel(p: string): string {
  return { github: 'GitHub', generic: '通用', feishu: '飞书', email: '邮件' }[p] ?? p
}

function providerIcon(p: string) {
  return { github: GitBranch, feishu: BellRing, email: Mail, generic: Globe }[p] ?? Globe
}

function providerClass(p: string): string {
  if (p === 'github') return 'bg-slate-800 text-white border-transparent'
  if (p === 'feishu') return 'bg-[#3370FF]/15 text-[#3370FF] border-transparent'
  if (p === 'email') return 'bg-success-muted text-success-muted-foreground border-transparent'
  return 'bg-primary-muted text-primary-muted-foreground border-transparent'
}

function eventLabel(e: string): string {
  return eventCatalog.value.find(x => x.type === e)?.description ?? e
}

function toggleEvent(key: string, checked: boolean | 'indeterminate') {
  if (checked === true || checked === 'indeterminate') {
    if (!form.value.events.includes(key)) form.value.events.push(key)
  } else {
    form.value.events = form.value.events.filter(e => e !== key)
  }
}

async function loadAll() {
  loading.value = true
  loadError.value = ''
  try {
    const [webhooks, events] = await Promise.all([
      fetchAdminWebhooks(),
      // 事件清单失败不阻断列表展示：订阅框会显示占位提示，避免用户勾出一串后端不认的名字
      fetchAdminWebhookEvents().catch(() => [] as AdminWebhookEvent[])
    ])
    items.value = webhooks
    eventCatalog.value = events
  } catch (e) {
    // fetchAdminWebhooks 内部 apiFetch 已 toast；这里补充内联错误态 + 重试
    items.value = []
    const err = e as { data?: unknown, message?: string }
    loadError.value = extractApiErrorMessage(err?.data, err?.message || '加载 Webhook 列表失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = emptyForm()
  editingHasSecret.value = false
  clearSecretFlag.value = false
  rotatedSecret.value = ''
  showSecret.value = false
  dialogOpen.value = true
}

function openEdit(w: AdminWebhook) {
  editingId.value = w.id
  form.value = {
    name: w.name,
    provider: w.provider,
    url: w.url,
    secret: '',
    events: [...(w.events || [])],
    active: w.active
  }
  editingHasSecret.value = w.has_secret
  clearSecretFlag.value = false
  rotatedSecret.value = ''
  showSecret.value = false
  dialogOpen.value = true
}

function clearSecret() {
  form.value.secret = ''
  clearSecretFlag.value = true
  toast.info('保存后将清除该 Webhook 的签名密钥')
}

/**
 * 密钥轮换：后端立即写库、旧密钥即刻失效（不等表单提交）。
 * 明文只在这次响应里出现一次，因此必须就地展示 + 允许复制。
 */
async function handleRotateSecret() {
  if (!editingId.value) return
  rotating.value = true
  try {
    const res = await regenerateAdminWebhookSecret(editingId.value)
    rotatedSecret.value = res?.data?.secret ?? ''
    editingHasSecret.value = true
    clearSecretFlag.value = false
    form.value.secret = ''
    if (rotatedSecret.value) toast.success('密钥已轮换，接收方需同步更新')
    else toast.warning(res?.message || '轮换完成，但服务端未返回新密钥')
  } catch (e) {
    // apiFetch 已 toast 失败原因
    console.error('[webhooks] handleRotateSecret failed:', e)
  } finally {
    rotating.value = false
  }
}

async function copyRotatedSecret() {
  try {
    await navigator.clipboard.writeText(rotatedSecret.value)
    toast.success('新密钥已复制到剪贴板')
  } catch {
    toast.warning('浏览器拒绝剪贴板访问，请手动选中复制')
  }
}

async function handleSubmit() {
  if (!form.value.name.trim() || !form.value.url.trim()) {
    toast.warning('请填写名称与 URL')
    return
  }
  if (form.value.events.length === 0) {
    toast.warning('请至少选择一个订阅事件')
    return
  }
  submitting.value = true
  const payload: AdminWebhookPayload = {
    name: form.value.name.trim(),
    provider: form.value.provider,
    url: form.value.url.trim(),
    events: form.value.events,
    active: form.value.active
  }
  // 三态：非空=设置新密钥；勾选清除=传 ''；否则不带该字段（服务端保持原值）
  const secret = form.value.secret.trim()
  if (secret) payload.secret = secret
  else if (clearSecretFlag.value) payload.secret = ''

  try {
    if (editingId.value) await updateAdminWebhook(editingId.value, payload)
    else await createAdminWebhook(payload)
    dialogOpen.value = false
    toast.success(editingId.value ? 'Webhook 已更新' : 'Webhook 已创建')
    await loadAll()
  } catch (e) {
    // create/update 的 apiFetch 失败时已 toast 展示后端错误，不再二次提示
    console.error('[webhooks] handleSubmit failed:', e)
  } finally {
    submitting.value = false
  }
}

async function toggleActive(w: AdminWebhook, val: unknown) {
  togglingId.value = w.id
  const next = Boolean(val)
  try {
    const updated = await updateAdminWebhook(w.id, { active: next })
    w.active = updated.active
    toast.success(next ? '已启用' : '已停用')
  } catch (e) {
    // updateAdminWebhook 的 apiFetch 已 toast；此处回滚开关到服务端真实状态
    console.error('[webhooks] toggleActive failed:', e)
    w.active = !next
  } finally {
    togglingId.value = null
  }
}

async function handleTrigger(w: AdminWebhook) {
  triggeringId.value = w.id
  try {
    // 目标端点失败时后端仍返回 200，必须看 success 字段，否则「测试成功」是假的
    const result = await triggerAdminWebhook(w.id)
    if (result.success) toast.success(`测试投递成功（HTTP ${result.status_code ?? '—'}）`)
    else toast.error(result.message || '测试投递失败')
    await loadAll()
  } catch (e) {
    // triggerAdminWebhook 的 apiFetch 已 toast 展示失败原因
    console.error('[webhooks] handleTrigger failed:', e)
  } finally {
    triggeringId.value = null
  }
}

async function openDeliveries(w: AdminWebhook) {
  deliveriesTarget.value = w
  deliveries.value = []
  deliveriesOpen.value = true
  deliveriesLoading.value = true
  try {
    deliveries.value = await fetchAdminWebhookDeliveries(w.id)
  } catch (e) {
    console.error('[webhooks] load deliveries failed:', e)
  } finally {
    deliveriesLoading.value = false
  }
}

async function handleRetry(d: AdminWebhookDelivery) {
  retryingId.value = d.id
  try {
    const result = await retryAdminWebhookDelivery(d.id)
    if (result.success) toast.success('已复发')
    else toast.error(result.message || '复发失败')
    if (deliveriesTarget.value) {
      deliveries.value = await fetchAdminWebhookDeliveries(deliveriesTarget.value.id)
    }
  } catch (e) {
    console.error('[webhooks] retry failed:', e)
  } finally {
    retryingId.value = null
  }
}

function handleDelete(w: AdminWebhook) {
  deleteTarget.value = w
  confirmOpen.value = true
}

/**
 * DangerConfirmDialog 的 onConfirm：
 * 抛错时弹窗保持打开、按钮退出 loading，失败提示由 apiFetch 统一 toast。
 */
async function confirmDelete() {
  const target = deleteTarget.value
  if (!target) return
  await deleteAdminWebhook(target.id)
  toast.success('Webhook 已删除')
  deleteTarget.value = null
  await loadAll()
}

onMounted(loadAll)
</script>
