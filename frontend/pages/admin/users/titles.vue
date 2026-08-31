<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">
        头衔管理
      </h1>
      <Button
        class="rounded-xl shadow-sm"
        @click="openCreate"
      >
        <Plus class="size-4 mr-2" />
        新建头衔
      </Button>
    </div>

    <AdminCard>
      <div
        v-if="loading"
        class="p-4 space-y-3"
      >
        <div
          v-for="i in 5"
          :key="i"
          class="h-12 rounded-lg"
        >
          <Skeleton class="h-full w-full rounded-lg" />
        </div>
      </div>

      <div
        v-else-if="!titles.length"
        class="p-16 text-center"
      >
        <Alert
          variant="info"
          class="max-w-md mx-auto"
        >
          <Info class="size-4" />
          <AlertTitle>暂无头衔</AlertTitle>
          <AlertDescription>点击右上角按钮创建第一个头衔</AlertDescription>
        </Alert>
      </div>

      <div
        v-else
        class="overflow-x-auto"
      >
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b bg-muted/30">
              <th class="text-left font-medium p-4 w-16">
                ID
              </th>
              <th class="text-left font-medium p-4">
                名称
              </th>
              <th class="text-left font-medium p-4 w-28">
                图标预览
              </th>
              <th class="text-left font-medium p-4">
                描述
              </th>
              <th class="text-right font-medium p-4 w-28">
                操作
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(t, i) in titles"
              :key="t.id"
              :class="i % 2 === 1 ? 'bg-muted/20' : ''"
            >
              <td class="p-4 text-muted-foreground tabular-nums">
                #{{ t.id }}
              </td>
              <td class="p-4">
                <div class="inline-flex items-center gap-2">
                  <span
                    class="size-2.5 rounded-full shrink-0"
                    :style="{ backgroundColor: t.color || '#94a3b8' }"
                  />
                  <span class="font-medium">{{ getLocalizedStr(t.name) }}</span>
                </div>
              </td>
              <td class="p-4">
                <TitleBadge
                  :title="t"
                  size="md"
                />
              </td>
              <td class="p-4 text-muted-foreground max-w-md truncate">
                {{ getLocalizedStr(t.description) || '—' }}
              </td>
              <td class="p-4 text-right">
                <div class="inline-flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    class="h-8 w-8"
                    @click="openEdit(t)"
                  >
                    <Pencil class="size-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    class="h-8 w-8 text-destructive hover:text-destructive"
                    @click="t.id && confirmDelete(t.id)"
                  >
                    <Trash2 class="size-4" />
                  </Button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </AdminCard>

    <!-- 新建/编辑 对话框 -->
    <Dialog v-model:open="formDialogOpen">
      <DialogContent class="max-w-lg">
        <DialogHeader>
          <DialogTitle>{{ editingId ? '编辑头衔' : '新建头衔' }}</DialogTitle>
          <DialogDescription>
            头衔可授予用户，显示在用户名旁边
          </DialogDescription>
        </DialogHeader>
        <div class="space-y-5 py-2">
          <!-- 名称 -->
          <I18nTabsEditor
            v-model="form.name"
            kind="text"
            label="名称"
            required
          />

          <!-- 颜色 + 图标预览 -->
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label>颜色</Label>
              <div class="flex items-center gap-2">
                <input
                  v-model="form.color"
                  type="color"
                  class="size-10 rounded-lg border cursor-pointer bg-transparent"
                >
                <Input
                  v-model="form.color"
                  placeholder="#3b82f6"
                  class="font-mono text-sm"
                />
              </div>
            </div>
            <div class="space-y-2">
              <Label>预览</Label>
              <div class="flex items-center h-10 rounded-lg border bg-muted/30 px-3">
                <TitleBadge
                  :title="previewTitle"
                  size="md"
                />
              </div>
            </div>
          </div>

          <!-- 图标选择：预设 SVG 网格 -->
          <div class="space-y-2">
            <Label>选择图标</Label>
            <div class="rounded-lg border p-3 bg-muted/20">
              <div class="grid grid-cols-6 sm:grid-cols-8 gap-2">
                <button
                  v-for="p in presetIcons"
                  :key="p.id"
                  type="button"
                  :class="[
                    'relative size-10 rounded-lg border flex items-center justify-center transition-all',
                    form.icon === p.id
                      ? 'border-primary bg-primary/10 ring-2 ring-primary/30'
                      : 'border-border bg-card hover:bg-accent'
                  ]"
                  :title="p.name"
                  @click="form.icon = p.id"
                >
                  <component
                    :is="(LucideIcons as Record<string, unknown>)[p.lucideName]"
                    class="size-5"
                    :style="{ color: form.color }"
                  />
                  <span
                    v-if="form.icon === p.id"
                    class="absolute -top-1 -right-1 size-4 rounded-full bg-primary text-primary-foreground text-[8px] flex items-center justify-center"
                  >✓</span>
                </button>
              </div>

              <!-- 自定义图标输入 -->
              <div class="mt-3 space-y-2">
                <Label
                  class="text-xs text-muted-foreground"
                >自定义（emoji / 内联 SVG / 预设 ID）</Label>
                <div class="flex gap-2">
                  <Input
                    v-model="form.icon"
                    placeholder="选择预设或输入自定义，如 star / ⭐ / <svg>...</svg>"
                    class="font-mono text-sm flex-1"
                  />
                </div>
                <p
                  class="text-[11px] text-muted-foreground"
                >
                  支持预设 ID（star、crown、trophy 等）、emoji（⭐、🏆）或完整 SVG 字符串
                </p>
              </div>
            </div>
          </div>

          <!-- 描述 -->
          <I18nTabsEditor
            v-model="form.description"
            kind="textarea"
            label="描述"
            :rows="3"
          />
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            @click="formDialogOpen = false"
          >
            取消
          </Button>
          <Button
            :disabled="submitting"
            @click="submitForm"
          >
            <Loader2
              v-if="submitting"
              class="size-4 mr-2 animate-spin"
            />
            {{ editingId ? '保存修改' : '创建头衔' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 删除确认 -->
    <Dialog v-model:open="deleteDialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>确认删除</DialogTitle>
          <DialogDescription>删除后该头衔将无法恢复，确定继续吗？</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="ghost"
            @click="deleteDialogOpen = false"
          >
            取消
          </Button>
          <Button
            variant="destructive"
            @click="doDelete"
          >
            确认删除
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
/* eslint-disable */
 
import AdminCard from '~~/components/admin/AdminCard.vue'
import I18nTabsEditor from '~~/components/admin/I18nTabsEditor.vue'
import TitleBadge from '~~/components/TitleBadge.vue'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '~~/components/ui/dialog'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import { Label } from '~~/components/ui/label'
import * as LucideIcons from '@lucide/vue'
import { Plus, Pencil, Trash2, Info, Loader2 } from '@lucide/vue'
import {
  fetchAdminUserTitles,
  createAdminUserTitle,
  updateAdminUserTitle,
  deleteAdminUserTitle,
  type AdminUserTitle
} from '~~/composables/useAdminManage'
import { TITLE_PRESET_ICONS } from '~~/composables/titlePresets'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()
const presetIcons = TITLE_PRESET_ICONS

type I18nDict = { zh: string; en: string; ja: string; zh_Hant: string }

const loading = ref(false)
const submitting = ref(false)
const titles = ref<AdminUserTitle[]>([])

const formDialogOpen = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<{
  name: I18nDict
  color: string
  icon: string
  description: I18nDict
}>({
  name: { zh: '', en: '', ja: '', zh_Hant: '' },
  color: '#3b82f6',
  icon: '',
  description: { zh: '', en: '', ja: '', zh_Hant: '' }
})

const deleteDialogOpen = ref(false)
const deleteTargetId = ref<number | null>(null)

const getLocalizedStr = (v: string | Record<string, string> | null | undefined): string => {
  if (v == null) return ''
  if (typeof v === 'string') return v
  return v.zh || v.en || Object.values(v)[0] || ''
}

const normalizeI18nDict = (v: string | Record<string, string> | null | undefined): I18nDict => {
  if (v == null) return { zh: '', en: '', ja: '', zh_Hant: '' }
  if (typeof v === 'string') return { zh: v, en: '', ja: '', zh_Hant: '' }
  return {
    zh: v.zh ?? '',
    en: v.en ?? '',
    ja: v.ja ?? '',
    zh_Hant: v.zh_Hant ?? ''
  }
}

const previewTitle = computed<AdminUserTitle>(() => ({
  id: 0,
  name: getLocalizedStr(form.name) || '头衔预览',
  color: form.color || '#3b82f6',
  icon: form.icon || 'star',
  description: getLocalizedStr(form.description)
}))

async function fetchData() {
  loading.value = true
  try {
    titles.value = await fetchAdminUserTitles()
  } catch (err) {
    console.error('fetch titles error', err)
    toast.error('加载头衔列表失败')
    titles.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    name: { zh: '', en: '', ja: '', zh_Hant: '' },
    color: '#3b82f6',
    icon: '',
    description: { zh: '', en: '', ja: '', zh_Hant: '' }
  })
  formDialogOpen.value = true
}

function openEdit(t: AdminUserTitle) {
  editingId.value = t.id ?? null
  form.name = normalizeI18nDict(t.name)
  form.color = t.color || '#3b82f6'
  form.icon = t.icon || ''
  form.description = normalizeI18nDict(t.description)
  formDialogOpen.value = true
}

async function submitForm() {
  if (!getLocalizedStr(form.name).trim()) {
    toast.warning('请填写名称')
    return
  }
  submitting.value = true
  const payload = {
    name: form.name,
    color: form.color || null,
    icon: form.icon.trim() || null,
    description: form.description
  }
  try {
    if (editingId.value) {
      await updateAdminUserTitle(editingId.value, payload)
      toast.success('修改成功')
    } else {
      await createAdminUserTitle(payload)
      toast.success('创建成功')
    }
    formDialogOpen.value = false
    fetchData()
  } catch (err) {
    console.error('submit title form error', err)
    toast.error(editingId.value ? '修改头衔失败' : '创建头衔失败')
  } finally {
    submitting.value = false
  }
}

function confirmDelete(id: number) {
  deleteTargetId.value = id
  deleteDialogOpen.value = true
}

async function doDelete() {
  if (deleteTargetId.value === null) return
  try {
    await deleteAdminUserTitle(deleteTargetId.value)
    toast.success('删除成功')
    deleteDialogOpen.value = false
    deleteTargetId.value = null
    fetchData()
  } catch (err) {
    console.error('delete title error', err)
    toast.error('删除头衔失败')
  }
}

onMounted(fetchData)
</script>
