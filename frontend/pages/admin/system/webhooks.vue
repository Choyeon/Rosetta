<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div
          class="size-10 rounded-xl flex items-center justify-center"
          style="background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);"
        >
          <Webhook class="size-5 text-white" />
        </div>
        <div>
          <h1 class="text-xl font-bold tracking-tight">
            Webhook 配置
          </h1>
          <p class="text-sm text-muted-foreground">
            接入外部系统，订阅站点事件通知
          </p>
        </div>
      </div>
      <Button
        class="text-white"
        style="background: linear-gradient(135deg, #0EA5E9 0%, #0369A1 100%); box-shadow: 0 6px 20px -8px rgba(14,165,233,0.55);"
        @click="openCreate()"
      >
        <Plus class="size-4" /> 新建 Webhook
      </Button>
    </div>

    <Card class="rounded-2xl overflow-hidden">
      <CardContent class="p-0">
        <div
          v-if="loading"
          class="p-6 space-y-3"
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
                            @click="handleTrigger(w)"
                          >
                            <Zap
                              v-if="triggeringId !== w.id"
                              class="size-4 text-warning"
                            />
                            <Loader2
                              v-else
                              class="size-4 animate-spin text-warning"
                            />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>测试触发</TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      title="编辑"
                      @click="openEdit(w)"
                    >
                      <Pencil class="size-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      class="text-error hover:text-error hover:bg-error-muted"
                      title="删除"
                      @click="handleDelete(w)"
                    >
                      <Trash2 class="size-4" />
                    </Button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>

    <Dialog v-model:open="dialogOpen">
      <DialogContent class="max-w-xl rounded-2xl">
        <DialogHeader>
          <DialogTitle>{{ editingId ? '编辑 Webhook' : '新建 Webhook' }}</DialogTitle>
          <DialogDescription>选择 Provider 并填写接收 URL 与订阅事件。</DialogDescription>
        </DialogHeader>
        <div class="space-y-4 py-2">
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label class="text-sm font-medium">名称 <span class="text-error">*</span></Label>
              <Input
                v-model="form.name"
                placeholder="如：飞书新评论通知"
                class="rounded-xl"
              />
            </div>
            <div class="space-y-2">
              <Label class="text-sm font-medium">Provider <span class="text-error">*</span></Label>
              <Select
                v-model="form.provider"
                :options="[
                  { label: '通用 Generic', value: 'generic' },
                  { label: 'GitHub', value: 'github' },
                  { label: '飞书 Feishu', value: 'feishu' },
                  { label: '邮件 Email', value: 'email' }
                ]"
                class="rounded-xl"
              />
            </div>
          </div>
          <div class="space-y-2">
            <Label class="text-sm font-medium">接收 URL <span class="text-error">*</span></Label>
            <Input
              v-model="form.url"
              placeholder="https://..."
              class="rounded-xl font-mono"
            />
          </div>
          <div class="space-y-2">
            <Label class="text-sm font-medium">签名密钥 Secret（可选）</Label>
            <div class="relative">
              <Input
                v-model="form.secret"
                :type="showSecret ? 'text' : 'password'"
                placeholder="留空则不进行签名校验"
                class="rounded-xl pr-11 font-mono"
              />
              <button
                type="button"
                class="absolute right-2 top-1/2 -translate-y-1/2 size-7 inline-flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
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
          </div>
          <div class="space-y-2">
            <Label class="text-sm font-medium">订阅事件（多选）</Label>
            <div class="rounded-xl border border-border p-4 grid grid-cols-2 gap-3 bg-muted/20">
              <label
                v-for="ev in allEvents"
                :key="ev.key"
                class="flex items-start gap-2 cursor-pointer select-none p-2 rounded-lg hover:bg-muted transition-colors"
              >
                <Checkbox
                  :model-value="form.events.includes(ev.key)"
                  @update:model-value="toggleEvent(ev.key, $event)"
                />
                <div class="space-y-0.5">
                  <div class="text-sm font-medium leading-tight">{{ ev.label }}</div>
                  <div class="text-xs text-muted-foreground leading-tight">{{ ev.key }}</div>
                </div>
              </label>
            </div>
          </div>
          <div class="flex items-center justify-between rounded-xl border border-border p-4 bg-muted/30">
            <div class="space-y-0.5">
              <Label class="text-sm font-medium">启用 Webhook</Label>
              <p class="text-xs text-muted-foreground">
                关闭后不会再推送任何事件。
              </p>
            </div>
            <Switch v-model="form.active" />
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
            class="text-white rounded-xl"
            style="background: linear-gradient(135deg, #0EA5E9 0%, #0369A1 100%);"
            @click="handleSubmit"
          >
            <Loader2
              v-if="submitting"
              class="size-4 animate-spin"
            />
            <Save
              v-else
              class="size-4"
            />
            {{ editingId ? '保存修改' : '创建 Webhook' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="confirmOpen">
      <DialogContent class="max-w-sm rounded-2xl">
        <DialogHeader>
          <DialogTitle>确认删除 Webhook？</DialogTitle>
          <DialogDescription>删除后对应的事件推送将立即停止。</DialogDescription>
        </DialogHeader>
        <DialogFooter class="gap-2">
          <Button
            variant="outline"
            class="rounded-xl"
            :disabled="deleting"
            @click="confirmOpen = false"
          >
            取消
          </Button>
          <Button
            variant="destructive"
            class="rounded-xl"
            :disabled="deleting"
            @click="confirmDelete"
          >
            <Loader2
              v-if="deleting"
              class="size-4 animate-spin"
            />
            <Trash2
              v-else
              class="size-4"
            />
            确认删除
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { ref, onMounted } from 'vue'
import {
  fetchAdminWebhooks,
  createAdminWebhook,
  updateAdminWebhook,
  deleteAdminWebhook,
  triggerAdminWebhook,
  formatAdminDateTime,
  type AdminWebhook
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import {
  Webhook, Plus, Zap, Pencil, Trash2, Save, Loader2, Info,
  Eye, EyeOff, Mail, GitBranch, BellRing, Globe
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Card, CardContent } from '~~/components/ui/card'
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
import { Select } from '~~/components/ui/select'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger
} from '~~/components/ui/tooltip'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const allEvents = [
  { key: 'post_created', label: '文章发布' },
  { key: 'post_updated', label: '文章更新' },
  { key: 'post_deleted', label: '文章删除' },
  { key: 'comment_created', label: '新评论' },
  { key: 'user_registered', label: '用户注册' },
  { key: 'user_banned', label: '用户封禁' }
] as const

const loading = ref(true)
const items = ref<AdminWebhook[]>([])
const dialogOpen = ref(false)
const confirmOpen = ref(false)
const submitting = ref(false)
const deleting = ref(false)
const togglingId = ref<number | null>(null)
const triggeringId = ref<number | null>(null)
const editingId = ref<number | null>(null)
const deleteTarget = ref<AdminWebhook | null>(null)
const showSecret = ref(false)

const emptyForm = () => ({
  name: '',
  provider: 'generic' as 'generic' | 'github' | 'feishu' | 'email',
  url: '',
  secret: '',
  events: [] as string[],
  active: true
})
const form = ref(emptyForm())

function providerLabel(p: string): string {
  return { github: 'GitHub', generic: '通用', feishu: '飞书', email: '邮件' }[p] ?? p
}

function providerIcon(p: string) {
  return { github: GitBranch, feishu: BellRing, email: Mail, generic: Globe }[p] ?? Globe
}

function providerClass(p: string): string {
  if (p === 'github') return 'bg-slate-800 text-white border-transparent'
  if (p === 'feishu') return 'bg-[#3370FF]/15 text-[#3370FF] border-transparent'
  if (p === 'email') return 'bg-success-muted text-success-foreground border-transparent'
  return 'bg-primary-muted text-primary-foreground border-transparent'
}

function eventLabel(e: string): string {
  const f = allEvents.find(x => x.key === e)
  return f?.label ?? e
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
  try {
    items.value = await fetchAdminWebhooks()
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'fetchAdminWebhooks'}`)
    items.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = emptyForm()
  showSecret.value = false
  dialogOpen.value = true
}

function openEdit(w: AdminWebhook) {
  editingId.value = w.id
  form.value = {
    name: w.name,
    provider: w.provider,
    url: w.url,
    secret: w.secret ?? '',
    events: [...(w.events || [])],
    active: w.active
  }
  showSecret.value = false
  dialogOpen.value = true
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
  const payload = {
    name: form.value.name.trim(),
    provider: form.value.provider,
    url: form.value.url.trim(),
    secret: form.value.secret.trim() || null,
    events: form.value.events,
    active: form.value.active
  }
  try {
    if (editingId.value) {
      await updateAdminWebhook(editingId.value, payload)
      toast.success('Webhook 已更新')
    } else {
      const r = await createAdminWebhook(payload)
      items.value.push(r)
      toast.success('Webhook 已创建')
    }
    dialogOpen.value = false
    await loadAll()
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : (editingId.value ? 'updateAdminWebhook' : 'createAdminWebhook')}`)
  } finally {
    submitting.value = false
  }
}

async function toggleActive(w: AdminWebhook, val: boolean) {
  togglingId.value = w.id
  try {
    await updateAdminWebhook(w.id, { active: val })
    w.active = val
    toast.success(val ? '已启用' : '已停用')
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'updateAdminWebhook'}`)
    w.active = !val
  } finally {
    togglingId.value = null
  }
}

async function handleTrigger(w: AdminWebhook) {
  triggeringId.value = w.id
  try {
    await triggerAdminWebhook(w.id)
    toast.success('已触发，请查看目标端点')
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'triggerAdminWebhook'}`)
  } finally {
    triggeringId.value = null
  }
}

function handleDelete(w: AdminWebhook) {
  deleteTarget.value = w
  confirmOpen.value = true
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await deleteAdminWebhook(deleteTarget.value.id)
    items.value = items.value.filter(i => i.id !== deleteTarget.value!.id)
    toast.success('Webhook 已删除')
    confirmOpen.value = false
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'deleteAdminWebhook'}`)
  } finally {
    deleting.value = false
  }
}

onMounted(loadAll)
</script>
