<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div
          class="size-10 rounded-xl flex items-center justify-center"
          style="background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);"
        >
          <Link2 class="size-5 text-white" />
        </div>
        <div>
          <h1 class="text-xl font-bold tracking-tight">
            友情链接管理
          </h1>
          <p class="text-sm text-muted-foreground">
            审核、管理与展示所有友情链接申请
          </p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <div class="inline-flex rounded-xl border border-border p-1 bg-card">
          <button
            v-for="s in statusFilters"
            :key="s.key"
            class="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
            :class="filter === s.key
              ? 'text-white shadow-sm'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground'"
            :style="filter === s.key ? 'background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);' : ''"
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
          class="text-white"
          style="background: linear-gradient(135deg, #0EA5E9 0%, #0369A1 100%); box-shadow: 0 6px 20px -8px rgba(14,165,233,0.55);"
          @click="openCreate()"
        >
          <Plus class="size-4" /> 新建友链
        </Button>
      </div>
    </div>

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
        class="group relative rounded-2xl border border-border overflow-hidden bg-card transition-all hover:shadow-soft hover:-translate-y-0.5"
        :style="link.bg_color ? { background: link.bg_color + '22', borderColor: link.bg_color + '44' } : ''"
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

        <div class="p-5 space-y-4">
          <div class="flex items-start gap-3">
            <div
              v-if="link.logo"
              class="size-12 rounded-xl overflow-hidden shrink-0 border border-border bg-muted/50"
            >
              <img
                :src="link.logo"
                :alt="link.name"
                class="w-full h-full object-cover"
                @error="($event.currentTarget as HTMLImageElement).style.display = 'none'"
              >
            </div>
            <div
              v-else
              class="size-12 rounded-xl shrink-0 flex items-center justify-center font-bold text-white text-lg"
              :style="`background: linear-gradient(135deg, ${gradientFor(link.name, 0)} 0%, ${gradientFor(link.name, 1)} 100%);`"
            >
              {{ link.name?.[0]?.toUpperCase() || '?' }}
            </div>
            <div class="flex-1 min-w-0 pt-1">
              <h3 class="font-semibold truncate">
                {{ link.name }}
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
            {{ link.description || '（暂无描述）' }}
          </p>
        </div>

        <div class="px-5 pb-4 opacity-0 group-hover:opacity-100 transition-opacity">
          <div class="flex items-center justify-between pt-3 border-t border-border/60">
            <div class="text-xs text-muted-foreground tabular-nums">
              排序 #{{ link.sort_order }}
            </div>
            <div class="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon-sm"
                title="编辑"
                @click="openEdit(link)"
              >
                <Pencil class="size-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                class="text-error hover:text-error hover:bg-error-muted"
                title="删除"
                @click="handleDelete(link)"
              >
                <Trash2 class="size-4" />
              </Button>
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
        <div class="space-y-4 py-2">
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label class="text-sm font-medium">名称 <span class="text-error">*</span></Label>
              <Input
                v-model="form.name"
                placeholder="如：Rosetta Blog"
                class="rounded-xl"
              />
            </div>
            <div class="space-y-2">
              <Label class="text-sm font-medium">URL <span class="text-error">*</span></Label>
              <Input
                v-model="form.url"
                placeholder="https://example.com"
                class="rounded-xl"
              />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label class="text-sm font-medium">Logo 图片 URL</Label>
              <Input
                v-model="form.logo"
                placeholder="https://.../logo.png"
                class="rounded-xl"
              />
            </div>
            <div class="space-y-2">
              <Label class="text-sm font-medium">卡片背景色</Label>
              <div class="flex items-center gap-2">
                <div class="relative">
                  <input
                    v-model="form.bg_color"
                    type="color"
                    class="absolute inset-0 opacity-0 cursor-pointer size-11 rounded-xl"
                  >
                  <div
                    class="size-11 rounded-xl border border-border shadow-inner"
                    :style="{ background: form.bg_color || '#ffffff' }"
                  />
                </div>
                <Input
                  v-model="form.bg_color"
                  class="rounded-xl font-mono text-xs uppercase w-full"
                  placeholder="#0EA5E9"
                />
              </div>
            </div>
          </div>
          <div class="space-y-2">
            <Label class="text-sm font-medium">描述</Label>
            <Textarea
              v-model="form.description"
              rows="3"
              class="rounded-xl resize-none"
              placeholder="一句话介绍你的站点..."
            />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label class="text-sm font-medium">审核状态</Label>
              <Select
                v-model="form.status"
                :options="[
                  { label: '待审核 pending', value: 'pending' },
                  { label: '已通过 approved', value: 'approved' },
                  { label: '已拒绝 rejected', value: 'rejected' }
                ]"
                class="rounded-xl"
              />
            </div>
            <div class="space-y-2">
              <Label class="text-sm font-medium">排序 sort_order</Label>
              <Input
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
            {{ editingId ? '保存修改' : '创建友链' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="confirmOpen">
      <DialogContent class="max-w-sm rounded-2xl">
        <DialogHeader>
          <DialogTitle>确认删除？</DialogTitle>
          <DialogDescription>该操作会永久删除友链记录，无法撤销。</DialogDescription>
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
import { ref, computed, onMounted } from 'vue'
import {
  fetchAdminFriendLinks,
  createAdminFriendLink,
  updateAdminFriendLink,
  deleteAdminFriendLink,
  type AdminFriendLink
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import {
  Link2, Plus, Pencil, Trash2, Save, Loader2, Info
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Skeleton } from '~~/components/ui/skeleton'
import { Badge } from '~~/components/ui/badge'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle
} from '~~/components/ui/dialog'
import { Label } from '~~/components/ui/label'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Select } from '~~/components/ui/select'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'
import type { BadgeVariants } from '~~/components/ui/badge'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const statusFilters = [
  { key: 'all', label: '全部' },
  { key: 'pending', label: '待审核' },
  { key: 'approved', label: '已通过' },
  { key: 'rejected', label: '已拒绝' }
] as const

const loading = ref(true)
const items = ref<AdminFriendLink[]>([])
const filter = ref<typeof statusFilters[number]['key']>('all')
const dialogOpen = ref(false)
const confirmOpen = ref(false)
const submitting = ref(false)
const deleting = ref(false)
const editingId = ref<number | null>(null)
const deleteTarget = ref<AdminFriendLink | null>(null)

const emptyForm = () => ({
  name: '',
  url: '',
  logo: '',
  description: '',
  bg_color: '',
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
  if (s === 'approved') return 'bg-success-muted text-success-foreground border-transparent'
  if (s === 'pending') return 'bg-warning-muted text-warning-foreground border-transparent'
  return ''
}

function stripProtocol(url: string): string {
  return url.replace(/^https?:\/\//, '').replace(/\/$/, '')
}

function gradientFor(name: string, idx: number): string {
  const palette = [
    ['#0EA5E9', '#0284C7'],
    ['#0EA5A9', '#0891B2'],
    ['#8B5CF6', '#7C3AED'],
    ['#10B981', '#059669'],
    ['#EF4444', '#DC2626'],
    ['#3B82F6', '#2563EB'],
    ['#EC4899', '#DB2777']
  ]
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) >>> 0
  const pick = palette[hash % palette.length]
  return pick[idx]
}

async function loadAll() {
  loading.value = true
  try {
    items.value = await fetchAdminFriendLinks()
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'fetchAdminFriendLinks'}`)
    items.value = []
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
    name: link.name,
    url: link.url,
    logo: link.logo ?? '',
    description: link.description ?? '',
    bg_color: link.bg_color ?? '',
    status: link.status,
    sort_order: link.sort_order
  }
  dialogOpen.value = true
}

async function handleSubmit() {
  if (!form.value.name.trim() || !form.value.url.trim()) {
    toast.warning('请填写名称与 URL')
    return
  }
  submitting.value = true
  const payload = {
    name: form.value.name.trim(),
    url: form.value.url.trim(),
    logo: form.value.logo.trim() || null,
    description: form.value.description.trim() || null,
    bg_color: form.value.bg_color.trim() || null,
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
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : (editingId.value ? 'updateAdminFriendLink' : 'createAdminFriendLink')}`)
  } finally {
    submitting.value = false
  }
}

function handleDelete(link: AdminFriendLink) {
  deleteTarget.value = link
  confirmOpen.value = true
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await deleteAdminFriendLink(deleteTarget.value.id)
    items.value = items.value.filter(i => i.id !== deleteTarget.value!.id)
    toast.success('友链已删除')
    confirmOpen.value = false
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'deleteAdminFriendLink'}`)
  } finally {
    deleting.value = false
  }
}

onMounted(loadAll)
</script>
