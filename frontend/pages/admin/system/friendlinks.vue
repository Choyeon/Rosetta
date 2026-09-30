<!--
  友情链接管理页：卡片网格 + 状态筛选 + Dialog CRUD；列表一次全量拉取，筛选与排序全在客户端完成。
  契约：name/description 必须以 {zh,en,ja,zh_Hant} 完整 i18n dict 提交，描述各语言全空时提交 null 而非空 dict；删除走 silentToast，失败由 DangerConfirmDialog 内联展示避免双重提示。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="友情链接管理"
      description="审核、管理与展示所有友情链接申请"
      :icon="Link2"
    >
      <template #actions>
        <div :class="['inline-flex rounded-xl border border-border p-1 bg-card']">
          <!-- panel-exempt: 分段筛选器（segmented control），同 trash.vue；是控件不是内容面板 -->
          <button
            v-for="s in statusFilters"
            :key="s.key"
            class="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
            :class="filter === s.key
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground'"
            @click="filter = s.key"
          >
            {{ s.label }}
            <Badge
              v-if="countOf(s.key) > 0"
              variant="outline"
              class="ml-1.5 text-[10px] !py-0"
            >
              {{ countOf(s.key) }}
            </Badge>
          </button>
        </div>
        <Button
          size="sm"
          class="shadow-sm"
          @click="openCreate()"
        >
          <Plus data-icon="inline-start" /> 新建友链
        </Button>
      </template>
    </AdminPageHeader>

    <Alert
      v-if="!loading && loadError"
      variant="destructive"
      class="rounded-xl"
    >
      <AlertTriangle class="size-4" />
      <AlertTitle>友链列表加载失败</AlertTitle>
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
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
    >
      <Skeleton
        v-for="i in 8"
        :key="i"
        class="aspect-[16/10] rounded-2xl"
      />
    </div>

    <div
      v-else-if="filtered.length === 0"
      class="py-16"
    >
      <Alert
        variant="info"
        class="rounded-xl max-w-lg mx-auto"
      >
        <Info class="size-4" />
        <AlertTitle>{{ filter === 'all' ? '暂无友链数据' : '当前筛选条件下无数据' }}</AlertTitle>
        <AlertDescription>点击右上方「新建友链」添加，或切换筛选条件查看。</AlertDescription>
      </Alert>
    </div>

    <div
      v-else
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
    >
      <div
        v-for="link in filtered"
        :key="link.id"
        class="card-surface lift-hover group relative overflow-hidden transition-all"
      >
        <div class="absolute top-3 right-3 z-10">
          <Badge
            class="text-[11px]"
            :variant="statusVariant(link.status)"
            :class="statusClass(link.status)"
          >
            {{ statusLabel(link.status) }}
          </Badge>
        </div>

        <div class="flex flex-col gap-4 p-5">
          <div class="flex items-start gap-3">
            <div
              v-if="link.logo"
              class="size-12 rounded-xl overflow-hidden shrink-0 border border-border bg-muted/50"
            >
              <img
                :src="link.logo"
                :alt="getLocalizedStr(link.name)"
                class="size-full object-cover"
                @error="($event.currentTarget as HTMLImageElement).style.display = 'none'"
              >
            </div>
            <div
              v-else
              class="size-12 rounded-xl shrink-0 flex items-center justify-center font-bold text-white text-lg bg-primary/90"
            >
              {{ getLocalizedStr(link.name)?.[0]?.toUpperCase() || '?' }}
            </div>
            <div class="flex-1 min-w-0 pt-1">
              <h3 class="font-semibold truncate">
                {{ getLocalizedStr(link.name) }}
              </h3>
              <a
                :href="link.url"
                target="_blank"
                rel="noopener noreferrer nofollow"
                class="text-xs text-primary hover:underline font-mono truncate block mt-0.5"
                :title="link.url"
              >
                {{ stripProtocol(link.url) }}
              </a>
            </div>
          </div>

          <p
            class="text-sm text-muted-foreground leading-relaxed"
            style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;"
          >
            {{ getLocalizedStr(link.description) || '（暂无描述）' }}
          </p>
        </div>

        <div class="px-5 pb-4">
          <div class="flex items-center justify-between pt-3 border-t border-border/60">
            <div class="text-xs text-muted-foreground tabular-nums">
              排序 #{{ link.sort_order }}
            </div>
            <div class="flex items-center gap-1">
              <Tooltip>
                <TooltipTrigger as-child>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label="编辑友链"
                    @click="openEdit(link)"
                  >
                    <Pencil />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>编辑</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger as-child>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    class="text-error hover:text-error hover:bg-error-muted"
                    aria-label="删除友链"
                    @click="handleDelete(link)"
                  >
                    <Trash2 />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>删除</TooltipContent>
              </Tooltip>
            </div>
          </div>
        </div>
      </div>
    </div>

    <Dialog v-model:open="dialogOpen">
      <DialogContent class="max-w-xl rounded-2xl">
        <DialogHeader>
          <DialogTitle>{{ editingId ? '编辑友链' : '新建友情链接' }}</DialogTitle>
          <DialogDescription>填写基本信息与卡片展示样式。</DialogDescription>
        </DialogHeader>
        <div class="flex flex-col gap-4 py-2">
          <div class="grid grid-cols-2 gap-4">
            <I18nTabsEditor
              v-model="form.name"
              kind="text"
              label="名称"
              placeholder="如：Rosetta Blog"
              :required="true"
            />
            <div class="flex flex-col gap-2">
              <Label
                for="fl-url"
                class="text-sm font-medium"
              >URL <span class="text-error">*</span></Label>
              <Input
                id="fl-url"
                v-model="form.url"
                placeholder="https://example.com"
                class="rounded-xl"
              />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="flex flex-col gap-2">
              <Label
                for="fl-logo"
                class="text-sm font-medium"
              >Logo 图片 URL</Label>
              <Input
                id="fl-logo"
                v-model="form.logo"
                placeholder="https://.../logo.png"
                class="rounded-xl"
              />
            </div>
          </div>
          <I18nTabsEditor
            v-model="form.description"
            kind="textarea"
            label="描述"
            placeholder="一句话介绍你的站点..."
            :rows="3"
          />
          <div class="grid grid-cols-2 gap-4">
            <div class="flex flex-col gap-2">
              <Label
                for="fl-status"
                class="text-sm font-medium"
              >审核状态</Label>
              <Select v-model="form.status">
                <SelectTrigger
                  id="fl-status"
                  class="rounded-xl"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pending">
                    待审核
                  </SelectItem>
                  <SelectItem value="approved">
                    已通过
                  </SelectItem>
                  <SelectItem value="rejected">
                    已拒绝
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="flex flex-col gap-2">
              <Label
                for="fl-sort"
                class="text-sm font-medium"
              >{{ t('adminCommon.sortOrder') }}</Label>
              <Input
                id="fl-sort"
                v-model.number="form.sort_order"
                type="number"
                class="rounded-xl"
              />
            </div>
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
            class="rounded-xl"
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
            {{ editingId ? '保存修改' : '创建友链' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <DangerConfirmDialog
      v-model:open="confirmOpen"
      title="确认删除友链？"
      :description="`「${getLocalizedStr(deleteTarget?.name)}」将被永久删除，无法撤销。`"
      confirm-text="确认删除"
      :on-confirm="confirmDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  fetchAdminFriendLinks,
  createAdminFriendLink,
  updateAdminFriendLink,
  deleteAdminFriendLink,
  type AdminFriendLink
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import { extractApiErrorMessage } from '~~/lib/utils'
import {
  Link2, Plus, Pencil, Trash2, Save, Loader2, Info, AlertTriangle, RotateCcw
} from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { Button } from '~~/components/ui/button'
import { Skeleton } from '~~/components/ui/skeleton'
import { Badge } from '~~/components/ui/badge'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle
} from '~~/components/ui/dialog'
import { Label } from '~~/components/ui/label'
import { Input } from '~~/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'
import I18nTabsEditor from '~~/components/admin/I18nTabsEditor.vue'
import DangerConfirmDialog from '~~/components/admin/tools/DangerConfirmDialog.vue'
import AdminPageHeader from '~~/components/admin/AdminPageHeader.vue'
import type { BadgeVariants } from '~~/components/ui/badge'

definePageMeta({ ssr: false, layout: 'admin' })

const { t } = useI18n()
const toast = useToast()

const statusFilters = [
  { key: 'all', label: '全部' },
  { key: 'pending', label: '待审核' },
  { key: 'approved', label: '已通过' },
  { key: 'rejected', label: '已拒绝' }
] as const

const loading = ref(true)
const loadError = ref('')
const items = ref<AdminFriendLink[]>([])
const filter = ref<typeof statusFilters[number]['key']>('all')
const dialogOpen = ref(false)
const confirmOpen = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)
const deleteTarget = ref<AdminFriendLink | null>(null)

const emptyForm = () => ({
  name: { zh: '', en: '', ja: '', zh_Hant: '' } as Record<string, string>,
  url: '',
  logo: '',
  description: { zh: '', en: '', ja: '', zh_Hant: '' } as Record<string, string>,
  status: 'pending' as 'pending' | 'approved' | 'rejected',
  sort_order: 0
})
const form = ref(emptyForm())

const filtered = computed(() => {
  const base = [...items.value].sort((a, b) => a.sort_order - b.sort_order || a.id - b.id)
  if (filter.value === 'all') return base
  return base.filter(i => i.status === filter.value)
})

function countOf(key: string): number {
  if (key === 'all') return items.value.length
  return items.value.filter(i => i.status === key).length
}

function statusLabel(s: string): string {
  return { pending: '待审核', approved: '已通过', rejected: '已拒绝' }[s] ?? s
}

function statusVariant(s: string): BadgeVariants['variant'] {
  if (s === 'approved') return 'default'
  if (s === 'pending') return 'secondary'
  return 'destructive'
}

function statusClass(s: string): string {
  if (s === 'approved') return 'bg-success-muted text-success-muted-foreground border-transparent'
  if (s === 'pending') return 'bg-warning-muted text-warning-muted-foreground border-transparent'
  return ''
}

function stripProtocol(url: string): string {
  return url.replace(/^https?:\/\//, '').replace(/\/$/, '')
}

function getLocalizedStr(v: string | Record<string, string> | null | undefined): string {
  if (v == null) return ''
  if (typeof v === 'string') return v
  return v.zh || v.en || Object.values(v)[0] || ''
}

function normalizeI18nDict(v: string | Record<string, string> | null | undefined): Record<string, string> {
  const base = { zh: '', en: '', ja: '', zh_Hant: '' }
  if (v == null) return base
  if (typeof v === 'string') {
    return { ...base, zh: v }
  }
  return {
    zh: v.zh ?? '',
    en: v.en ?? '',
    ja: v.ja ?? '',
    zh_Hant: v.zh_Hant ?? ''
  }
}

async function loadAll() {
  loading.value = true
  loadError.value = ''
  try {
    items.value = await fetchAdminFriendLinks()
  } catch (e) {
    // fetchAdminFriendLinks 内部 apiFetch 已 toast；这里补充内联错误态 + 重试
    items.value = []
    const err = e as { data?: unknown, message?: string }
    loadError.value = extractApiErrorMessage(err?.data, err?.message || '加载友链列表失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = emptyForm()
  const max = items.value.reduce((m, i) => Math.max(m, i.sort_order), -1)
  form.value.sort_order = max + 1
  dialogOpen.value = true
}

function openEdit(link: AdminFriendLink) {
  editingId.value = link.id
  form.value = {
    name: normalizeI18nDict(link.name),
    url: link.url,
    logo: link.logo ?? '',
    description: normalizeI18nDict(link.description),
    status: link.status,
    sort_order: link.sort_order
  }
  dialogOpen.value = true
}

async function handleSubmit() {
  if (!String(form.value.name.zh ?? '').trim() || !form.value.url.trim()) {
    toast.warning('请填写名称与 URL')
    return
  }
  submitting.value = true
  const descHasValue = String(form.value.description.zh ?? '') || String(form.value.description.en ?? '')
    || String(form.value.description.ja ?? '') || String(form.value.description.zh_Hant ?? '')
  const payload = {
    name: form.value.name,
    url: form.value.url.trim(),
    logo: form.value.logo.trim() || null,
    description: descHasValue ? form.value.description : null,
    status: form.value.status,
    sort_order: Number(form.value.sort_order) || 0
  }
  try {
    if (editingId.value) {
      await updateAdminFriendLink(editingId.value, payload)
      toast.success('友链已更新')
    } else {
      const r = await createAdminFriendLink(payload)
      items.value.push(r)
      toast.success('友链已创建')
    }
    dialogOpen.value = false
    await loadAll()
  } catch (e) {
    // create/update 的 apiFetch 失败时已 toast 展示后端错误，不再二次提示
    console.error('[friendlinks] handleSubmit failed:', e)
  } finally {
    submitting.value = false
  }
}

function handleDelete(link: AdminFriendLink) {
  deleteTarget.value = link
  confirmOpen.value = true
}

/**
 * DangerConfirmDialog 的 onConfirm：
 * throw 时弹窗保持打开并内联展示错误（请求走 silentToast 避免 toast 与内联双重提示）。
 */
async function confirmDelete() {
  const target = deleteTarget.value
  if (!target) return
  await deleteAdminFriendLink(target.id, { silentToast: true })
  toast.success('友链已删除')
  deleteTarget.value = null
  await loadAll()
}

onMounted(loadAll)
</script>
