<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-3xl font-bold tracking-tight font-display">
          {{ t('admin.categories.title') }}
        </h1>
        <p class="text-sm text-muted-foreground mt-1">
          {{ t('admin.categories.desc') }}
        </p>
      </div>
      <Button @click="openCreate">
        <Plus class="mr-2 size-4" />
        {{ activeTab === 'categories' ? t('admin.categories.createCategory') : t('admin.categories.createTag') }}
      </Button>
    </div>

    <Tabs
      v-model="activeTab"
      @update:model-value="onTabChange"
    >
      <TabsList>
        <TabsTrigger value="categories">
          {{ t('admin.categories.tabCategories') }}
        </TabsTrigger>
        <TabsTrigger value="tags">
          {{ t('admin.categories.tabTags') }}
        </TabsTrigger>
      </TabsList>

      <TabsContent
        value="categories"
        class="mt-4"
      >
        <Card>
          <CardContent class="p-0">
            <div
              v-if="loadingCategories && categories.length === 0"
              class="p-4 space-y-3"
            >
              <Skeleton
                v-for="i in 5"
                :key="i"
                class="h-12 w-full"
              />
            </div>
            <div
              v-else-if="categories.length > 0"
              class="overflow-x-auto"
            >
              <table class="w-full text-sm">
                <thead>
                  <tr class="border-b">
                    <th class="text-left font-medium text-muted-foreground p-3">
                      {{ t('admin.categories.thName') }}
                    </th>
                    <th class="text-left font-medium text-muted-foreground p-3">
                      {{ t('admin.categories.thSlug') }}
                    </th>
                    <th class="text-left font-medium text-muted-foreground p-3">
                      {{ t('admin.categories.thDescription') }}
                    </th>
                    <th class="text-left font-medium text-muted-foreground p-3">
                      {{ t('admin.categories.thPosts') }}
                    </th>
                    <th class="text-left font-medium text-muted-foreground p-3">
                      {{ t('admin.categories.thCreatedAt') }}
                    </th>
                    <th class="text-right font-medium text-muted-foreground p-3">
                      {{ t('admin.categories.thActions') }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="c in categories"
                    :key="c.id"
                    class="border-b last:border-0 transition-colors hover:bg-muted/50"
                  >
                    <td class="p-3">
                      <div class="flex items-center gap-2">
                        <span
                          class="size-3 rounded-full shrink-0"
                          :style="{ backgroundColor: c.color ?? '#3B82F6' }"
                        />
                        <span class="font-medium">
                          {{ c.icon ? `${c.icon} ` : '' }}{{ c.name }}
                        </span>
                      </div>
                    </td>
                    <td class="p-3 text-muted-foreground">
                      {{ c.slug }}
                    </td>
                    <td class="p-3 text-muted-foreground max-w-64">
                      <span class="line-clamp-1">{{ c.description || '-' }}</span>
                    </td>
                    <td class="p-3">
                      {{ c.post_count }}
                    </td>
                    <td class="p-3 text-muted-foreground whitespace-nowrap">
                      {{ formatAdminDate(c.created_at) }}
                    </td>
                    <td class="p-3 text-right whitespace-nowrap">
                      <Button
                        variant="ghost"
                        size="sm"
                        @click="openEditCategory(c)"
                      >
                        <Pencil class="mr-1 size-4" />
                        {{ t('admin.categories.edit') }}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        class="text-destructive hover:text-destructive"
                        @click="pendingDelete = { type: 'category', item: c }"
                      >
                        <Trash2 class="mr-1 size-4" />
                        {{ t('admin.categories.delete') }}
                      </Button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div
              v-else
              class="flex flex-col items-center justify-center py-16 text-muted-foreground"
            >
              <FolderOpen class="size-8 mb-2" />
              <p class="text-sm">
                {{ t('admin.categories.emptyCategories') }}
              </p>
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent
        value="tags"
        class="mt-4"
      >
        <Card>
          <CardContent class="p-0">
            <div
              v-if="loadingTags && tags.length === 0"
              class="p-4 space-y-3"
            >
              <Skeleton
                v-for="i in 5"
                :key="i"
                class="h-12 w-full"
              />
            </div>
            <div
              v-else-if="tags.length > 0"
              class="overflow-x-auto"
            >
              <table class="w-full text-sm">
                <thead>
                  <tr class="border-b">
                    <th class="text-left font-medium text-muted-foreground p-3">
                      {{ t('admin.categories.thName') }}
                    </th>
                    <th class="text-left font-medium text-muted-foreground p-3">
                      {{ t('admin.categories.thSlug') }}
                    </th>
                    <th class="text-left font-medium text-muted-foreground p-3">
                      {{ t('admin.categories.thActive') }}
                    </th>
                    <th class="text-left font-medium text-muted-foreground p-3">
                      {{ t('admin.categories.thPosts') }}
                    </th>
                    <th class="text-left font-medium text-muted-foreground p-3">
                      {{ t('admin.categories.thCreatedAt') }}
                    </th>
                    <th class="text-right font-medium text-muted-foreground p-3">
                      {{ t('admin.categories.thActions') }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="tag in tags"
                    :key="tag.id"
                    class="border-b last:border-0 transition-colors hover:bg-muted/50"
                  >
                    <td class="p-3">
                      <div class="flex items-center gap-2">
                        <span
                          class="size-3 rounded-full shrink-0"
                          :style="{ backgroundColor: tag.color ?? '#64748B' }"
                        />
                        <span class="font-medium">
                          {{ tag.icon ? `${tag.icon} ` : '' }}{{ tag.name }}
                        </span>
                      </div>
                    </td>
                    <td class="p-3 text-muted-foreground">
                      {{ tag.slug }}
                    </td>
                    <td class="p-3">
                      <Badge :class="tag.is_active ? 'bg-success-muted text-success border-transparent' : 'bg-muted text-muted-foreground border-transparent'">
                        {{ tag.is_active ? t('admin.categories.active') : t('admin.categories.inactive') }}
                      </Badge>
                    </td>
                    <td class="p-3">
                      {{ tag.post_count }}
                    </td>
                    <td class="p-3 text-muted-foreground whitespace-nowrap">
                      {{ formatAdminDate(tag.created_at) }}
                    </td>
                    <td class="p-3 text-right whitespace-nowrap">
                      <Button
                        variant="ghost"
                        size="sm"
                        @click="openEditTag(tag)"
                      >
                        <Pencil class="mr-1 size-4" />
                        {{ t('admin.categories.edit') }}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        class="text-destructive hover:text-destructive"
                        @click="pendingDelete = { type: 'tag', item: tag }"
                      >
                        <Trash2 class="mr-1 size-4" />
                        {{ t('admin.categories.delete') }}
                      </Button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div
              v-else
              class="flex flex-col items-center justify-center py-16 text-muted-foreground"
            >
              <TagsIcon class="size-8 mb-2" />
              <p class="text-sm">
                {{ t('admin.categories.emptyTags') }}
              </p>
            </div>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>

    <!-- 新建 / 编辑 Dialog（分类与标签共用） -->
    <Dialog v-model:open="dialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {{ dialogTitle }}
          </DialogTitle>
          <DialogDescription>{{ t('admin.categories.formDesc') }}</DialogDescription>
        </DialogHeader>
        <div class="space-y-4">
          <div class="space-y-1.5">
            <Label for="taxo-name">{{ t('admin.categories.fName') }} *</Label>
            <Input
              id="taxo-name"
              v-model="form.name"
              :placeholder="t('admin.categories.fNamePlaceholder')"
            />
          </div>
          <div class="space-y-1.5">
            <Label for="taxo-slug">{{ t('admin.categories.fSlug') }}</Label>
            <Input
              id="taxo-slug"
              v-model="form.slug"
              placeholder="my-category"
            />
            <p class="text-xs text-muted-foreground">
              {{ t('admin.categories.fSlugHint') }}
            </p>
          </div>
          <div
            v-if="dialogType === 'category'"
            class="space-y-1.5"
          >
            <Label for="taxo-desc">{{ t('admin.categories.fDescription') }}</Label>
            <Input
              id="taxo-desc"
              v-model="form.description"
              :placeholder="t('admin.categories.fDescriptionPlaceholder')"
            />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <Label for="taxo-icon">{{ t('admin.categories.fIcon') }}</Label>
              <Input
                id="taxo-icon"
                v-model="form.icon"
                placeholder="📁"
              />
            </div>
            <div class="space-y-1.5">
              <Label for="taxo-color">{{ t('admin.categories.fColor') }}</Label>
              <Input
                id="taxo-color"
                v-model="form.color"
                type="color"
                class="h-10 p-1"
              />
            </div>
          </div>
          <div
            v-if="dialogType === 'tag'"
            class="flex items-center justify-between"
          >
            <Label for="taxo-active">{{ t('admin.categories.fActive') }}</Label>
            <Switch
              id="taxo-active"
              :model-value="form.isActive"
              @update:model-value="(v: boolean) => (form.isActive = v)"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            @click="dialogOpen = false"
          >
            {{ t('admin.categories.cancel') }}
          </Button>
          <Button
            :disabled="saving || !form.name.trim()"
            @click="save"
          >
            {{ saving ? t('admin.categories.saving') : t('admin.categories.save') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 删除确认 Dialog -->
    <Dialog
      :open="pendingDelete !== null"
      @update:open="(v: boolean) => { if (!v) pendingDelete = null }"
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{ t('admin.categories.deleteTitle') }}</DialogTitle>
          <DialogDescription>
            {{ t('admin.categories.deleteDesc', { name: pendingDelete?.item.name ?? '' }) }}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="outline"
            @click="pendingDelete = null"
          >
            {{ t('admin.categories.cancel') }}
          </Button>
          <Button
            variant="destructive"
            :disabled="deleting"
            @click="confirmDelete"
          >
            {{ t('admin.categories.confirmDelete') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import { Switch } from '~~/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~~/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '~~/components/ui/dialog'
import { Plus, Pencil, Trash2, FolderOpen, Tags as TagsIcon } from '@lucide/vue'
import {
  createAdminCategory,
  createAdminTag,
  deleteAdminCategory,
  deleteAdminTag,
  fetchAdminCategories,
  fetchAdminTags,
  formatAdminDate,
  updateAdminCategory,
  updateAdminTag,
  type AdminCategory,
  type AdminTag
} from '~~/composables/useAdminManage'

definePageMeta({
  layout: 'admin'
})

const { t } = useI18n()
const toast = useToast()

type TabKey = 'categories' | 'tags'

const activeTab = ref<TabKey>('categories')
const categories = ref<AdminCategory[]>([])
const tags = ref<AdminTag[]>([])
const loadingCategories = ref(false)
const loadingTags = ref(false)

const dialogOpen = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const dialogType = ref<'category' | 'tag'>('category')
const editingId = ref<number | null>(null)
const saving = ref(false)
const deleting = ref(false)

const form = reactive({
  name: '',
  slug: '',
  description: '',
  icon: '',
  color: '#3B82F6',
  isActive: true
})

const pendingDelete = ref<{ type: 'category' | 'tag', item: AdminCategory | AdminTag } | null>(null)

const dialogTitle = computed(() => {
  const action = dialogMode.value === 'create' ? t('admin.categories.create') : t('admin.categories.editAction')
  const typeLabel = dialogType.value === 'category'
    ? t('admin.categories.tabCategoriesSingular')
    : t('admin.categories.tabTagsSingular')
  return `${action}${typeLabel}`
})

async function loadCategories(): Promise<void> {
  loadingCategories.value = true
  try {
    categories.value = await fetchAdminCategories()
  } catch {
    // apiFetch 已 toast
  } finally {
    loadingCategories.value = false
  }
}

async function loadTags(): Promise<void> {
  loadingTags.value = true
  try {
    tags.value = await fetchAdminTags()
  } catch {
    // ignore
  } finally {
    loadingTags.value = false
  }
}

function onTabChange(tab: string | number): void {
  if (tab === 'tags' && tags.value.length === 0 && !loadingTags.value) loadTags()
}

function resetForm(): void {
  form.name = ''
  form.slug = ''
  form.description = ''
  form.icon = ''
  form.color = '#3B82F6'
  form.isActive = true
}

function openCreate(): void {
  dialogMode.value = 'create'
  dialogType.value = activeTab.value === 'categories' ? 'category' : 'tag'
  editingId.value = null
  resetForm()
  dialogOpen.value = true
}

function openEditCategory(c: AdminCategory): void {
  dialogMode.value = 'edit'
  dialogType.value = 'category'
  editingId.value = c.id
  resetForm()
  form.name = c.name
  form.slug = c.slug
  form.description = c.description ?? ''
  form.icon = c.icon ?? ''
  form.color = c.color ?? '#3B82F6'
  dialogOpen.value = true
}

function openEditTag(tag: AdminTag): void {
  dialogMode.value = 'edit'
  dialogType.value = 'tag'
  editingId.value = tag.id
  resetForm()
  form.name = tag.name
  form.slug = tag.slug
  form.icon = tag.icon ?? ''
  form.color = tag.color ?? '#64748B'
  form.isActive = tag.is_active
  dialogOpen.value = true
}

function buildPayload() {
  return {
    name: form.name.trim(),
    slug: form.slug.trim() || undefined,
    description: dialogType.value === 'category' ? form.description.trim() || undefined : undefined,
    icon: form.icon.trim() || undefined,
    color: form.color.trim() || undefined,
    is_active: dialogType.value === 'tag' ? form.isActive : undefined
  }
}

async function save(): Promise<void> {
  if (!form.name.trim()) return
  saving.value = true
  try {
    const payload = buildPayload()
    if (dialogType.value === 'category') {
      if (dialogMode.value === 'create') await createAdminCategory(payload)
      else if (editingId.value !== null) await updateAdminCategory(editingId.value, payload)
      toast.success(t('admin.categories.toast.saved'))
      await loadCategories()
    } else {
      if (dialogMode.value === 'create') await createAdminTag(payload)
      else if (editingId.value !== null) await updateAdminTag(editingId.value, payload)
      toast.success(t('admin.categories.toast.saved'))
      await loadTags()
    }
    dialogOpen.value = false
  } catch {
    // 后端错误（如 slug 重复、分类下有文章等）由 apiFetch 统一 toast 展示
  } finally {
    saving.value = false
  }
}

async function confirmDelete(): Promise<void> {
  if (!pendingDelete.value) return
  deleting.value = true
  try {
    if (pendingDelete.value.type === 'category') {
      await deleteAdminCategory(pendingDelete.value.item.id)
      toast.success(t('admin.categories.toast.deleted'))
      await loadCategories()
    } else {
      await deleteAdminTag(pendingDelete.value.item.id)
      toast.success(t('admin.categories.toast.deleted'))
      await loadTags()
    }
    pendingDelete.value = null
  } catch {
    // 后端错误消息（如存在关联文章）由 apiFetch 展示
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadCategories()
})
</script>
