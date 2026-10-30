<!--
  自定义内容类型管理页（ACF）：定义一套「字段清单」，文章切换到该类型后按清单填写 meta_fields。
  硬契约（后端定义见 backend/models/content_type.py + services/content_type_service.py）：
  1. **key 创建后不可变**：PUT schema 里根本没有这个键（extra=forbid），本页编辑时把输入框锁死。
  2. **字段 key 是写进 Post.meta_fields 的 JSON 键**：改名不会迁移旧值，已有文章里的旧键值
     会变成"定义之外的键"从此不再展示（读侧宽容、不报错），所以编辑态给出明确提示。
  3. **仍被文章引用时删除会回 409**（后端消息含真实篇数）：本页直接把删除按钮禁用并说明原因，
     而不是让用户在确认弹窗里点一次才被告知失败。
  4. select 的候选项必须非空且不重复、其它类型不得带候选项——与后端 ContentField._validate_shape
     同口径；校验放在提交前，避免一个字段打错让整张定义 422。
  5. datetime 默认值走 lib/datetime 的本地墙钟 ↔ UTC ISO 换算（与编辑器 scheduled_at 同一口径）。
-->
<script setup lang="ts">
import { ref, reactive, shallowRef, onMounted } from 'vue'
import {
  fetchAdminContentTypes,
  createAdminContentType,
  updateAdminContentType,
  deleteAdminContentType,
  CONTENT_FIELD_TYPES,
  CONTENT_FIELD_KEY_PATTERN,
  CONTENT_TYPE_KEY_PATTERN,
  type AdminContentType,
  type ContentFieldType
} from '~~/composables/useContentTypes'
import { useToast } from '~~/composables/useToast'
import { toDateTimeLocal, fromDateTimeLocal } from '~~/lib/datetime'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { Switch } from '~~/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '~~/components/ui/select'
import AdminFormField from '~~/components/admin/AdminFormField.vue'
import AdminRowActions from '~~/components/admin/AdminRowActions.vue'
import { Boxes, Plus, Pencil, Trash2, CircleHelp } from '@lucide/vue'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

/** 字段类型的中文标签：与后端 FIELD_TYPES 一一对应（缺一个保存时就少一个可选类型）。 */
const FIELD_TYPE_LABELS: Record<ContentFieldType, string> = {
  text: '单行文本',
  textarea: '多行文本',
  number: '数字',
  boolean: '布尔开关',
  select: '单选',
  date: '日期',
  datetime: '日期时间',
  image: '图片地址',
  url: '链接地址',
  markdown: 'Markdown'
}

/**
 * 字段编辑态。`defaultText` 是**输入框原值**：
 * - 布尔存 'true' / 'false'，select 存候选项本身，date/datetime 存控件原值，其余存字符串；
 * - 空串 = 不设默认值（提交时发 null）。
 * 不在编辑态保持强类型 default，是因为输入过程中每一键都可能是半成品（数字 "-"、日期半截）。
 */
type FieldDraft = {
  key: string
  label: string
  field_type: ContentFieldType
  required: boolean
  description: string
  optionsText: string
  defaultText: string
}

const types = shallowRef<AdminContentType[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogOpen = ref(false)
const dialogMode = ref<'new' | 'edit'>('new')
const editingKey = ref<string | null>(null)
const deleteDialogOpen = ref(false)
const pendingDelete = ref<AdminContentType | null>(null)

const form = reactive({
  key: '',
  name: '',
  icon: '',
  description: '',
  fields: [] as FieldDraft[]
})

const loadData = async () => {
  loading.value = true
  try {
    types.value = await fetchAdminContentTypes()
  } catch (e) {
    console.error('[content-types] loadData failed:', e)
    types.value = []
  } finally {
    loading.value = false
  }
}

function emptyField(): FieldDraft {
  return {
    key: '',
    label: '',
    field_type: 'text',
    required: false,
    description: '',
    optionsText: '',
    defaultText: ''
  }
}

/** 定义里的 default（任意 JSON 值）→ 编辑态原值；无法表达时留空而不是抛错。 */
function defaultToDraft(fieldType: ContentFieldType, value: unknown): string {
  if (value === undefined || value === null) return ''
  if (fieldType === 'boolean') return value === true ? 'true' : 'false'
  if (fieldType === 'datetime') return toDateTimeLocal(String(value))
  if (fieldType === 'number') return String(value)
  return String(value)
}

const openNew = () => {
  dialogMode.value = 'new'
  editingKey.value = null
  form.key = ''
  form.name = ''
  form.icon = ''
  form.description = ''
  form.fields = []
  dialogOpen.value = true
}

const openEdit = (t: AdminContentType) => {
  dialogMode.value = 'edit'
  editingKey.value = t.key
  form.key = t.key
  form.name = t.name
  form.icon = t.icon ?? ''
  form.description = t.description ?? ''
  form.fields = t.fields.map(f => ({
    key: f.key,
    label: f.label,
    field_type: f.field_type,
    required: f.required,
    description: f.description ?? '',
    optionsText: (f.options ?? []).join('\n'),
    defaultText: defaultToDraft(f.field_type, f.default)
  }))
  dialogOpen.value = true
}

function addField() {
  form.fields.push(emptyField())
}

/** 切换字段类型时清掉只对旧类型有意义的输入（候选项 / 默认值语义完全不同）。 */
function onFieldTypeChange(field: FieldDraft, next: unknown) {
  // Select 的 emit 形参含 undefined，处理器统一收 unknown 再归一（模板里不各写一份签名）。
  const key = String(next ?? '')
  if (!(CONTENT_FIELD_TYPES as readonly string[]).includes(key)) return
  if (key === field.field_type) return
  field.field_type = key as ContentFieldType
  if (key !== 'select') field.optionsText = ''
  field.defaultText = ''
}

/** 默认值只存"输入框原值"；`__unset__` 是 Select 不能选空串而用的哨兵。 */
function onDefaultChange(field: FieldDraft, next: unknown) {
  const value = String(next ?? '')
  field.defaultText = value === '__unset__' ? '' : value
}

function removeField(index: number) {
  form.fields.splice(index, 1)
}

function parseOptions(text: string): string[] {
  return text
    .split(/[\n,，]/)
    .map(s => s.trim())
    .filter(s => s !== '')
}

/** 编辑态原值 → 提交给后端的 default；类型不合法 / 未填时返回 null（= 不设默认值）。 */
function draftToDefault(field: FieldDraft): unknown {
  const raw = field.defaultText.trim()
  if (field.field_type === 'boolean') return raw === 'true' ? true : raw === 'false' ? false : null
  if (!raw) return null
  if (field.field_type === 'number') {
    const n = Number(raw)
    return Number.isFinite(n) ? n : null
  }
  if (field.field_type === 'datetime') return fromDateTimeLocal(raw)
  return raw
}

/** 提交前按后端 ContentField 的约束完整校验一遍；返回错误文案，null 表示通过。 */
function validateForm(): string | null {
  if (!CONTENT_TYPE_KEY_PATTERN.test(form.key.trim())) {
    return '类型 Key 仅允许小写字母、数字、连字符与下划线，且以字母开头（最长 50 字符）'
  }
  if (!form.name.trim()) return '请输入类型名称'
  const seen = new Set<string>()
  for (let i = 0; i < form.fields.length; i++) {
    const f = form.fields[i]!
    const label = f.label.trim() || `第 ${i + 1} 个字段`
    if (!CONTENT_FIELD_KEY_PATTERN.test(f.key.trim())) {
      return `「${label}」的字段键仅允许小写字母、数字与下划线，且以字母开头`
    }
    if (seen.has(f.key.trim())) return `字段键重复：${f.key.trim()}`
    seen.add(f.key.trim())
    if (!f.label.trim()) return `第 ${i + 1} 个字段缺少展示名`
    if (f.field_type === 'select') {
      const options = parseOptions(f.optionsText)
      if (options.length === 0) return `「${label}」是单选类型，至少需要一个候选项`
      if (new Set(options).size !== options.length) return `「${label}」的候选项有重复`
      const def = f.defaultText.trim()
      if (def && !options.includes(def)) return `「${label}」的默认值不在候选项里`
    }
    if (f.field_type === 'number' && f.defaultText.trim() && !Number.isFinite(Number(f.defaultText))) {
      return `「${label}」的默认值不是有效数字`
    }
    if (f.field_type === 'datetime' && f.defaultText.trim() && !fromDateTimeLocal(f.defaultText)) {
      return `「${label}」的默认时间无法解析`
    }
  }
  return null
}

const save = async () => {
  const error = validateForm()
  if (error) {
    toast.error(error)
    return
  }
  const fields = form.fields.map((f) => {
    const isSelect = f.field_type === 'select'
    return {
      key: f.key.trim(),
      label: f.label.trim(),
      field_type: f.field_type,
      required: f.required,
      default: draftToDefault(f),
      description: f.description.trim() || null,
      options: isSelect ? parseOptions(f.optionsText) : null
    }
  })
  saving.value = true
  try {
    if (dialogMode.value === 'edit' && editingKey.value) {
      // PUT 不带 key：后端 ContentTypeUpdate 的 extra=forbid 会直接 422
      await updateAdminContentType(editingKey.value, {
        name: form.name.trim(),
        icon: form.icon.trim() || null,
        description: form.description.trim() || null,
        fields
      })
      toast.success('内容类型已更新')
    } else {
      await createAdminContentType({
        key: form.key.trim(),
        name: form.name.trim(),
        icon: form.icon.trim() || null,
        description: form.description.trim() || null,
        fields
      })
      toast.success('内容类型已创建')
    }
    dialogOpen.value = false
    await loadData()
  } catch (e) {
    // 失败提示由 apiFetch 统一 toast（409 / 422 都带后端中文消息），弹窗保持打开供修正
    console.error('[content-types] save failed:', e)
  } finally {
    saving.value = false
  }
}

function confirmDelete(t: AdminContentType) {
  pendingDelete.value = t
  deleteDialogOpen.value = true
}

async function doDelete() {
  const target = pendingDelete.value
  if (!target) return
  await deleteAdminContentType(target.key)
  toast.success('内容类型已删除')
  pendingDelete.value = null
  await loadData()
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <AdminListPage
    title="内容类型"
    :icon="Boxes"
    description="给文章定义一套自定义字段（如书籍的作者/ISBN、视频的时长/链接），发布时按清单填写并在文章页展示。"
    :count="types.length"
  >
    <template #actions>
      <Button
        size="sm"
        class="shadow-sm"
        @click="openNew"
      >
        <Plus data-icon="inline-start" />
        新建内容类型
      </Button>
    </template>

    <div class="p-5">
      <template v-if="loading">
        <div class="grid gap-3">
          <Skeleton
            v-for="i in 4"
            :key="`sk-${i}`"
            class="h-24 rounded-[12px]"
          />
        </div>
      </template>

      <template v-else-if="types.length === 0">
        <div class="py-24 text-center text-muted-foreground">
          <div class="mb-4 flex items-center justify-center opacity-30">
            <Boxes class="size-16" />
          </div>
          <div class="mb-2 text-sm">
            还没有自定义内容类型
          </div>
          <div class="mb-5 text-xs opacity-70">
            默认「文章」是内置类型；需要额外字段时新建一个类型，再在文章编辑器里切换过去。
          </div>
          <Button
            size="sm"
            @click="openNew"
          >
            <Plus data-icon="inline-start" />
            新建内容类型
          </Button>
        </div>
      </template>

      <div
        v-else
        class="grid gap-3"
      >
        <div
          v-for="t in types"
          :key="t.key"
          class="card-surface flex flex-col gap-3 p-4 shadow-sm sm:flex-row sm:items-center"
        >
          <div class="flex min-w-0 flex-1 items-start gap-3">
            <div class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Boxes class="size-5" />
            </div>
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span class="truncate text-sm font-semibold">{{ t.name }}</span>
                <code class="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground">{{ t.key }}</code>
                <Badge
                  variant="secondary"
                  class="rounded-[10px] tabular-nums"
                >
                  {{ t.fields.length }} 个字段
                </Badge>
                <Badge
                  variant="outline"
                  class="rounded-[10px] tabular-nums"
                >
                  {{ t.posts_count }} 篇文章
                </Badge>
              </div>
              <p class="mt-1 line-clamp-2 text-xs text-muted-foreground">
                {{ t.description || '暂无描述' }}
              </p>
              <div
                v-if="t.fields.length > 0"
                class="mt-2 flex flex-wrap gap-1.5"
              >
                <span
                  v-for="f in t.fields"
                  :key="f.key"
                  class="inline-flex items-center gap-1 rounded-md border border-border bg-background px-1.5 py-0.5 text-[11px] text-muted-foreground"
                >
                  {{ f.label }}
                  <span class="opacity-60">{{ FIELD_TYPE_LABELS[f.field_type] }}</span>
                  <span
                    v-if="f.required"
                    class="text-destructive"
                    title="必填字段"
                  >*</span>
                </span>
              </div>
            </div>
          </div>
          <div class="flex shrink-0 items-center justify-between gap-2 sm:justify-end">
            <span
              v-if="t.posts_count > 0"
              class="inline-flex items-center gap-1 text-[11px] text-muted-foreground"
            >
              <CircleHelp class="size-3.5" />
              使用中不可删除
            </span>
            <AdminRowActions
              :actions="[
                { key: 'edit', label: '编辑内容类型', icon: Pencil, onClick: () => openEdit(t) },
                {
                  key: 'delete',
                  label: t.posts_count > 0
                    ? `删除内容类型（仍被 ${t.posts_count} 篇文章使用，需先改到其它类型）`
                    : '删除内容类型',
                  icon: Trash2,
                  destructive: true,
                  disabled: t.posts_count > 0,
                  onClick: () => confirmDelete(t)
                }
              ]"
            />
          </div>
        </div>
      </div>
    </div>

    <AdminCrudDialog
      v-model:open="dialogOpen"
      :title="dialogMode === 'edit' ? '编辑内容类型' : '新建内容类型'"
      description="字段清单决定文章编辑器里出现哪些输入项；定义改动会立即影响前台文章页的展示。"
      :icon="Boxes"
      size="xl"
      :loading="saving"
      :submit-text="dialogMode === 'edit' ? '更新' : '保存'"
      @submit="save"
    >
      <div class="flex flex-col gap-5">
        <div class="grid gap-4 sm:grid-cols-2">
          <AdminFormField
            label="类型 Key"
            for="ct-form-key"
            required
            hint="写进文章 post_type 的稳定标识；创建后不可修改。"
          >
            <Input
              id="ct-form-key"
              v-model="form.key"
              placeholder="book"
              class="h-10 rounded-[10px] font-mono text-sm"
              :disabled="dialogMode === 'edit'"
            />
          </AdminFormField>
          <AdminFormField
            label="展示名称"
            for="ct-form-name"
            required
            hint="后台与前台字段卡片上显示的名字。"
          >
            <Input
              id="ct-form-name"
              v-model="form.name"
              placeholder="书籍"
              class="h-10 rounded-[10px]"
            />
          </AdminFormField>
        </div>
        <AdminFormField
          label="说明"
          for="ct-form-description"
          hint="可选：告诉运营这个类型适合放什么内容。"
        >
          <Textarea
            id="ct-form-description"
            v-model="form.description"
            rows="2"
            placeholder="例如：书评文章，额外记录作者、出版社与 ISBN。"
            class="rounded-[10px] text-sm"
          />
        </AdminFormField>

        <div class="flex flex-col gap-3">
          <div class="flex items-center justify-between gap-2">
            <div>
              <div class="text-sm font-medium">
                自定义字段
              </div>
              <div class="text-xs text-muted-foreground">
                文章切到此类型后，必填字段留空会直接拒绝保存（后端 422）。
              </div>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              class="shrink-0 rounded-[10px]"
              @click="addField"
            >
              <Plus data-icon="inline-start" />
              添加字段
            </Button>
          </div>

          <div
            v-if="form.fields.length === 0"
            class="rounded-xl border border-dashed border-border bg-muted/20 px-4 py-6 text-center text-xs text-muted-foreground"
          >
            暂无字段。纯标记型内容类型也可以不配字段（只用作文章分类标记）。
          </div>

          <div
            v-for="(field, idx) in form.fields"
            :key="idx"
            class="rounded-xl border border-border bg-muted/20 p-3"
          >
            <div class="mb-3 flex items-center justify-between gap-2">
              <span class="text-xs font-medium text-muted-foreground">字段 #{{ idx + 1 }}</span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                class="h-8 rounded-[10px] text-destructive hover:text-destructive"
                @click="removeField(idx)"
              >
                <Trash2 data-icon="inline-start" />
                移除
              </Button>
            </div>
            <div class="grid gap-3 sm:grid-cols-2">
              <AdminFormField
                label="字段键"
                required
                :hint="dialogMode === 'edit' && editingKey ? '存储在文章 meta_fields 里的键；改名不会迁移旧值。' : '小写字母开头，仅小写字母/数字/下划线。'"
              >
                <Input
                  v-model="field.key"
                  placeholder="isbn"
                  class="h-9 rounded-[10px] font-mono text-sm"
                />
              </AdminFormField>
              <AdminFormField
                label="展示名"
                required
              >
                <Input
                  v-model="field.label"
                  placeholder="ISBN"
                  class="h-9 rounded-[10px]"
                />
              </AdminFormField>
              <AdminFormField label="类型">
                <Select
                  :model-value="field.field_type"
                  @update:model-value="(v: unknown) => onFieldTypeChange(field, v)"
                >
                  <SelectTrigger class="h-9 w-full rounded-[10px]">
                    <SelectValue placeholder="字段类型" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem
                      v-for="ft in CONTENT_FIELD_TYPES"
                      :key="ft"
                      :value="ft"
                    >
                      {{ FIELD_TYPE_LABELS[ft] }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </AdminFormField>
              <div class="flex items-end gap-2 pb-1">
                <Switch
                  :id="`ct-field-required-${idx}`"
                  :model-value="field.required"
                  @update:model-value="(v: boolean) => (field.required = v)"
                />
                <label
                  :for="`ct-field-required-${idx}`"
                  class="text-sm font-medium leading-none"
                >必填字段</label>
              </div>
            </div>

            <div
              v-if="field.field_type === 'select'"
              class="mt-3"
            >
              <AdminFormField
                label="候选项"
                required
                hint="每行一个（也接受逗号分隔），不能重复。"
              >
                <Textarea
                  v-model="field.optionsText"
                  rows="3"
                  placeholder="入门&#10;进阶&#10;专家"
                  class="rounded-[10px] font-mono text-sm"
                />
              </AdminFormField>
            </div>

            <div class="mt-3 grid gap-3 sm:grid-cols-2">
              <AdminFormField
                label="默认值"
                hint="仅用于编辑器预填，写入时不会替作者自动补值。"
              >
                <Select
                  v-if="field.field_type === 'boolean'"
                  :model-value="field.defaultText || '__unset__'"
                  @update:model-value="(v: unknown) => onDefaultChange(field, v)"
                >
                  <SelectTrigger class="h-9 w-full rounded-[10px]">
                    <SelectValue placeholder="不设默认值" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__unset__">
                      不设默认值
                    </SelectItem>
                    <SelectItem value="true">
                      默认开启
                    </SelectItem>
                    <SelectItem value="false">
                      默认关闭
                    </SelectItem>
                  </SelectContent>
                </Select>
                <Select
                  v-else-if="field.field_type === 'select'"
                  :model-value="field.defaultText || '__unset__'"
                  @update:model-value="(v: unknown) => onDefaultChange(field, v)"
                >
                  <SelectTrigger class="h-9 w-full rounded-[10px]">
                    <SelectValue placeholder="不设默认值" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__unset__">
                      不设默认值
                    </SelectItem>
                    <SelectItem
                      v-for="opt in parseOptions(field.optionsText)"
                      :key="opt"
                      :value="opt"
                    >
                      {{ opt }}
                    </SelectItem>
                  </SelectContent>
                </Select>
                <Input
                  v-else-if="field.field_type === 'number'"
                  v-model="field.defaultText"
                  type="number"
                  placeholder="不设默认值"
                  class="h-9 rounded-[10px]"
                />
                <Input
                  v-else-if="field.field_type === 'date'"
                  v-model="field.defaultText"
                  type="date"
                  class="h-9 rounded-[10px]"
                />
                <Input
                  v-else-if="field.field_type === 'datetime'"
                  v-model="field.defaultText"
                  type="datetime-local"
                  class="h-9 rounded-[10px]"
                />
                <Input
                  v-else
                  v-model="field.defaultText"
                  placeholder="不设默认值"
                  class="h-9 rounded-[10px]"
                />
              </AdminFormField>
              <AdminFormField label="字段说明">
                <Input
                  v-model="field.description"
                  placeholder="可选：编辑器里的帮助文本"
                  class="h-9 rounded-[10px]"
                />
              </AdminFormField>
            </div>
          </div>
        </div>
      </div>
      <template #footer-left>
        字段定义改完后，已发布文章的页面会按新定义重新展示；定义里没有的旧键会被隐藏但不会删除。
      </template>
    </AdminCrudDialog>

    <AdminConfirmDialog
      v-model:open="deleteDialogOpen"
      title="确认删除内容类型"
      :description="pendingDelete
        ? `删除「${pendingDelete.name}」后，文章编辑器里不再提供这套字段；已写入文章的 meta_fields 值会保留在库里但不再展示。此操作不可撤销。`
        : '此操作不可撤销。'"
      confirm-text="确认删除"
      :on-confirm="doDelete"
    />
  </AdminListPage>
</template>
