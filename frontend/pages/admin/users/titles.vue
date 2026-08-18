<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">
        头衔管理
      </h1>
      <Button
        class="bg-gradient-to-r from-primary to-primary/70 hover:from-primary/90 hover:to-primary/60"
        @click="openCreate"
      >
        <Plus class="size-4 mr-2" />
        新建头衔
      </Button>
    </div>

    <Card>
      <CardContent class="p-0">
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
                <th class="text-left font-medium p-4 w-20">
                  ID
                </th>
                <th class="text-left font-medium p-4">
                  名称
                </th>
                <th class="text-left font-medium p-4 w-24">
                  图标
                </th>
                <th class="text-left font-medium p-4">
                  描述
                </th>
                <th class="text-right font-medium p-4 w-32">
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
                    <span class="font-medium">{{ t.name }}</span>
                  </div>
                </td>
                <td class="p-4 text-lg">
                  {{ t.icon || '—' }}
                </td>
                <td class="p-4 text-muted-foreground max-w-md truncate">
                  {{ t.description || '—' }}
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
                      @click="confirmDelete(t.id)"
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

    <Dialog v-model:open="formDialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{ editingId ? '编辑头衔' : '新建头衔' }}</DialogTitle>
          <DialogDescription>
            头衔可授予用户，显示在用户名旁边
          </DialogDescription>
        </DialogHeader>
        <div class="space-y-4 py-2">
          <div class="space-y-2">
            <Label>名称 <span class="text-destructive">*</span></Label>
            <Input
              v-model="form.name"
              placeholder="例如：核心贡献者"
            />
          </div>
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
              <Label>图标</Label>
              <Input
                v-model="form.icon"
                placeholder="emoji 或 CSS class，如 ⭐"
              />
            </div>
          </div>
          <div class="space-y-2">
            <Label>描述</Label>
            <Textarea
              v-model="form.description"
              rows="3"
              placeholder="该头衔的简短描述..."
              class="resize-none"
            />
          </div>
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
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { Card, CardContent } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '~~/components/ui/dialog'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import { Label } from '~~/components/ui/label'
import { Plus, Pencil, Trash2, Info, Loader2 } from '@lucide/vue'
import {
  fetchAdminUserTitles,
  createAdminUserTitle,
  updateAdminUserTitle,
  deleteAdminUserTitle,
  type AdminUserTitle
} from '~~/composables/useAdminManage'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const loading = ref(false)
const submitting = ref(false)
const titles = ref<AdminUserTitle[]>([])

const formDialogOpen = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  name: '',
  color: '#3b82f6',
  icon: '',
  description: ''
})

const deleteDialogOpen = ref(false)
const deleteTargetId = ref<number | null>(null)

async function fetchData() {
  loading.value = true
  try {
    titles.value = await fetchAdminUserTitles()
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '加载头衔失败')
    titles.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { name: '', color: '#3b82f6', icon: '', description: '' })
  formDialogOpen.value = true
}

function openEdit(t: AdminUserTitle) {
  editingId.value = t.id
  Object.assign(form, {
    name: t.name,
    color: t.color || '#3b82f6',
    icon: t.icon || '',
    description: t.description || ''
  })
  formDialogOpen.value = true
}

async function submitForm() {
  if (!form.name.trim()) {
    toast.warning('请填写名称')
    return
  }
  submitting.value = true
  const payload: Record<string, unknown> = {
    name: form.name.trim(),
    color: form.color || null,
    icon: form.icon.trim() || null,
    description: form.description.trim() || null
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
    toast.error(err instanceof Error ? err.message : '保存失败')
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
    toast.error(err instanceof Error ? err.message : '删除失败')
  }
}

onMounted(fetchData)
</script>
