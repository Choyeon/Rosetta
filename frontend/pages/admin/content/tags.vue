<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { ref, reactive, computed, onMounted } from 'vue'
import {
  fetchAdminTags,
  createAdminTag,
  updateAdminTag,
  deleteAdminTag,
  type AdminTag
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import { Switch } from '~~/components/ui/switch'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from '~~/components/ui/dialog'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const tags = ref<AdminTag[]>([])
const loading = ref(false)
const searchQuery = ref('')
const hoveredId = ref<number | null>(null)
const dialogOpen = ref(false)
const dialogMode = ref<'new' | 'edit'>('new')
const saving = ref(false)

const deleteDialogOpen = ref(false)
const pendingDeleteId = ref<number | null>(null)

const form = reactive({
  name: '',
  slug: '',
  color: '#0EA5E9',
  icon: '',
  is_active: true
})

const editingId = ref<number | null>(null)

const getLocalizedStr = (v: string | Record<string, string> | null | undefined): string => {
  if (v == null) return ''
  if (typeof v === 'string') return v
  return v.zh || v.en || Object.values(v)[0] || ''
}

const slugify = (text: string): string => {
  let s = text.trim().toLowerCase()
  s = s.replace(/[\s]+/g, '-')
  s = s.replace(/[^\w\u4e00-\u9fa5-]/g, '')
  s = s.replace(/-+/g, '-').replace(/^-|-$/g, '')
  return s
}

let slugManualEdit = false
watch(
  () => form.name,
  (val) => {
    if (!slugManualEdit && val) {
      form.slug = slugify(val)
    }
  }
)

const filteredTags = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return tags.value
  return tags.value.filter(t =>
    getLocalizedStr(t.name).toLowerCase().includes(q)
    || t.slug.toLowerCase().includes(q)
  )
})

const loadData = async () => {
  loading.value = true
  try {
    tags.value = await fetchAdminTags()
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '加载标签失败')
    tags.value = []
  } finally {
    loading.value = false
  }
}

const openNew = () => {
  dialogMode.value = 'new'
  editingId.value = null
  form.name = ''
  form.slug = ''
  form.color = '#0EA5E9'
  form.icon = ''
  form.is_active = true
  slugManualEdit = false
  dialogOpen.value = true
}

const openEdit = (t: AdminTag) => {
  dialogMode.value = 'edit'
  editingId.value = t.id
  form.name = getLocalizedStr(t.name)
  form.slug = t.slug
  form.color = t.color || '#0EA5E9'
  form.icon = t.icon || ''
  form.is_active = t.is_active
  slugManualEdit = true
  dialogOpen.value = true
}

const save = async () => {
  if (!form.name.trim()) {
    toast.error('请输入标签名称')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name,
      slug: form.slug || undefined,
      color: form.color || undefined,
      icon: form.icon || undefined,
      is_active: form.is_active
    }
    if (dialogMode.value === 'edit' && editingId.value) {
      await updateAdminTag(editingId.value, payload)
      toast.success('更新成功')
    } else {
      await createAdminTag(payload)
      toast.success('创建成功')
    }
    dialogOpen.value = false
    await loadData()
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

const confirmDelete = (id: number) => {
  pendingDeleteId.value = id
  deleteDialogOpen.value = true
}

const doDelete = async () => {
  if (pendingDeleteId.value == null) return
  try {
    await deleteAdminTag(pendingDeleteId.value)
    toast.success('删除成功')
    deleteDialogOpen.value = false
    pendingDeleteId.value = null
    await loadData()
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '删除失败')
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="flex flex-col gap-5 p-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-3">
        <h1 class="text-2xl font-bold tracking-tight">
          标签管理
        </h1>
        <Badge
          variant="secondary"
          class="rounded-[10px] px-3 py-1 bg-stone-100 text-stone-700 border-stone-200"
        >
          共 {{ tags.length }} 个标签
        </Badge>
      </div>
      <div class="flex items-center gap-3">
        <Input
          v-model="searchQuery"
          placeholder="🔍 搜索标签..."
          class="h-10 w-64 rounded-[12px]"
        />
        <Dialog v-model:open="dialogOpen">
          <DialogTrigger as-child>
            <Button
              class="rounded-[12px] h-10 px-5 shadow-sm"
              @click="openNew"
            >
              + 新建标签
            </Button>
          </DialogTrigger>
          <DialogContent class="rounded-[12px] max-w-md">
            <DialogHeader>
              <DialogTitle>{{ dialogMode === 'edit' ? '编辑标签' : '新建标签' }}</DialogTitle>
              <DialogDescription>
                标签可用于文章的快速分类与搜索聚合。
              </DialogDescription>
            </DialogHeader>
            <div class="flex flex-col gap-4 py-4">
              <div>
                <Label class="mb-1 block text-xs text-muted-foreground">
                  名称 <span class="text-destructive">*</span>
                </Label>
                <Input
                  v-model="form.name"
                  placeholder="标签名称"
                  class="h-9 rounded-[10px]"
                />
              </div>
              <div>
                <Label class="mb-1 block text-xs text-muted-foreground">Slug</Label>
                <Input
                  v-model="form.slug"
                  placeholder="自动生成，可修改"
                  class="h-9 rounded-[10px]"
                  @input="slugManualEdit = true"
                />
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <Label class="mb-1 block text-xs text-muted-foreground">颜色</Label>
                  <div class="flex gap-2">
                    <input
                      v-model="form.color"
                      type="color"
                      class="h-9 w-11 rounded-[10px] border border-input bg-background cursor-pointer"
                    >
                    <Input
                      v-model="form.color"
                      class="h-9 rounded-[10px] flex-1 font-mono text-xs"
                    />
                  </div>
                </div>
                <div>
                  <Label class="mb-1 block text-xs text-muted-foreground">图标</Label>
                  <Input
                    v-model="form.icon"
                    placeholder="emoji 或 icon"
                    class="h-9 rounded-[10px]"
                  />
                </div>
              </div>
              <div class="flex items-center justify-between rounded-[10px] border border-border bg-muted/20 px-4 py-3">
                <div>
                  <Label class="text-sm font-medium">启用状态</Label>
                  <div class="text-xs text-muted-foreground mt-0.5">
                    关闭后标签不再显示在前台
                  </div>
                </div>
                <Switch v-model="form.is_active" />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                class="rounded-[10px]"
                @click="dialogOpen = false"
              >
                取消
              </Button>
              <Button
                class="rounded-[10px]"
                :disabled="saving"
                @click="save"
              >
                {{ saving ? '保存中...' : '保存' }}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>

    <div class="rounded-[12px] border border-border bg-card p-5">
      <template v-if="loading">
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-3">
          <div
            v-for="i in 24"
            :key="`sk-${i}`"
          >
            <Skeleton class="h-14 rounded-[14px]" />
          </div>
        </div>
      </template>

      <template v-else-if="filteredTags.length === 0">
        <div class="py-20 text-center text-muted-foreground">
          <div class="text-5xl mb-3 opacity-30">
            🏷️
          </div>
          <div class="text-sm">
            {{ searchQuery ? '无匹配的标签' : '暂无标签，点击右上角「新建标签」创建吧' }}
          </div>
        </div>
      </template>

      <template v-else>
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-3">
          <div
            v-for="t in filteredTags"
            :key="t.id"
            class="relative rounded-[14px] border px-3 py-3 cursor-pointer transition-all select-none group"
            :style="{
              background: `color-mix(in oklab, ${t.color || '#0EA5E9'} 14%, hsl(var(--card)))`,
              borderColor: `${t.color || '#0EA5E9'}40`,
              opacity: t.is_active ? 1 : 0.5
            }"
            :class="{ 'ring-2 ring-offset-1': hoveredId === t.id }"
            @mouseenter="hoveredId = t.id"
            @mouseleave="hoveredId = null"
            @dblclick="openEdit(t)"
          >
            <div
              class="absolute top-2 right-2 z-10 transition-opacity"
              :class="hoveredId === t.id ? 'opacity-100' : 'opacity-0'"
            >
              <div class="flex items-center gap-0.5 bg-white/95 backdrop-blur rounded-[8px] shadow-md border border-border p-0.5">
                <button
                  type="button"
                  class="h-7 w-7 rounded-[6px] grid place-items-center text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                  title="编辑"
                  @click.stop="openEdit(t)"
                >
                  ✎
                </button>
                <button
                  type="button"
                  class="h-7 w-7 rounded-[6px] grid place-items-center text-muted-foreground hover:bg-red-50 hover:text-destructive transition-colors"
                  title="删除"
                  @click.stop="confirmDelete(t.id)"
                >
                  🗑
                </button>
              </div>
            </div>

            <div class="flex flex-col items-start gap-1 min-h-[44px] pr-12">
              <div
                class="font-semibold text-sm leading-tight"
                :style="{ color: t.color || '#6b7280' }"
              >
                <span
                  v-if="t.icon"
                  class="mr-1"
                >{{ t.icon }}</span>
                {{ getLocalizedStr(t.name) }}
              </div>
              <div
                class="text-xs font-medium opacity-70"
                :style="{ color: t.color || '#6b7280' }"
              >
                {{ t.post_count }} 篇
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <Dialog v-model:open="deleteDialogOpen">
      <DialogContent class="rounded-[12px] max-w-md">
        <DialogHeader>
          <DialogTitle>确认删除标签</DialogTitle>
          <DialogDescription>
            删除标签不会删除关联文章，只是解除文章与该标签的关联。此操作不可撤销。
          </DialogDescription>
        </DialogHeader>
        <DialogFooter class="mt-4">
          <Button
            variant="outline"
            class="rounded-[10px]"
            @click="deleteDialogOpen = false"
          >
            取消
          </Button>
          <Button
            variant="destructive"
            class="rounded-[10px]"
            @click="doDelete"
          >
            确认删除
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
