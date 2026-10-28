<!--
  投票管理页：后台唯一的投票入口。
  硬契约：
  - 后端有 POST/GET/PUT/DELETE /api/voting/polls，所以本页做 创建 / 编辑 / 结束·开启 / 删除。
    PUT 是**显式写值**且只写提交的键（见 backend/api/voting.py::update_poll），所以「结束投票」
    只发 `{is_active:false}` 不会顺带清空标题或说明；不提供翻转端点，因为翻转在重试、双击、
    两个管理员并发时不收敛。
  - PollCreate 的 choices 是 string[]（2–200 项，每项 1–200 字符），选项 id 由后端按顺序生成；
    **选项创建后不可改**（每个选项 id 上挂着票数），所以编辑弹窗不出现选项输入框。
  - `post_id` 是绑定文章：null = 全站投票（挂在每篇文章下方），非 null = 只出现在这一篇。
    前台 pages/posts/[slug].vue 按当前文章向 GET /voting/polls?post_id= 取票，所以这里的
    选择结果直接决定访客在哪些页面看到这条投票。
-->
<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { usePolls, type Poll } from '~~/composables/usePolls'
import { fetchAdminPostsPaged, type AdminPostListItem } from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { Switch } from '~~/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { Textarea } from '~~/components/ui/textarea'
import { ChartColumn, Pause, Pencil, Play, Plus, Trash2 } from '@lucide/vue'

definePageMeta({ ssr: false, layout: 'admin' })

/** 全站投票在下拉里的哨兵值：reka-ui 的 SelectItem 不接受空串 value。 */
const SITE_WIDE = 'site'

const toast = useToast()
const pollsAPI = usePolls()

const polls = ref<Poll[]>([])
const loading = ref(false)
const loadError = ref(false)

/** 文章下拉的候选：后台口拿已发布文章，最多 100 篇（投票本来就面向公开内容）。 */
const postOptions = ref<AdminPostListItem[]>([])

const dialogOpen = ref(false)
const saving = ref(false)
const deleteDialogOpen = ref(false)
const pendingDeleteId = ref<number | null>(null)
/** null = 新建弹窗；非 null = 编辑这条投票 */
const editingId = ref<number | null>(null)

const form = reactive({
  title: '',
  description: '',
  post_id: SITE_WIDE as string,
  is_active: true,
  allow_multiple: false,
  show_results: true,
  choices: ['', ''] as string[]
})

const cleanChoices = computed(() =>
  form.choices.map(c => c.trim()).filter(Boolean)
)

/** 提交用的绑定值：哨兵 → null（全站），否则数字文章 id。 */
const formPostId = computed<number | null>(() =>
  form.post_id === SITE_WIDE ? null : Number(form.post_id)
)

const postTitleById = computed(() => {
  const map = new Map<number, string>()
  for (const p of postOptions.value) map.set(p.id, p.title)
  return map
})

/** 卡片上的绑定标签：下拉里没这篇（超出 100 条）时退回显示文章 id。 */
const bindingLabel = (poll: Poll) => {
  if (poll.post_id == null) return '全站投票'
  return `仅文章 #${poll.post_id}${postTitleById.value.get(poll.post_id) ? ` · ${postTitleById.value.get(poll.post_id)}` : ''}`
}

const fmtDate = (iso: string) => (iso ? new Date(iso).toLocaleString() : '-')

function percent(poll: Poll, votes: number | null): number {
  const total = poll.total_votes ?? 0
  if (!total || votes == null) return 0
  return Math.round((votes / total) * 100)
}

async function loadData() {
  loading.value = true
  loadError.value = false
  try {
    const [rows, posts] = await Promise.all([
      pollsAPI.fetchAllPolls(),
      fetchAdminPostsPaged<AdminPostListItem>({ status: 'published', page: 1, page_size: 100 })
    ])
    polls.value = rows
    postOptions.value = posts.items
  } catch (e) {
    // 失败提示由 apiFetch 统一 toast，这里只切到可重试的错误态
    console.error('[polls] loadData failed:', e)
    polls.value = []
    loadError.value = true
  } finally {
    loading.value = false
  }
}

function openNew() {
  editingId.value = null
  form.title = ''
  form.description = ''
  form.post_id = SITE_WIDE
  form.is_active = true
  form.allow_multiple = false
  form.show_results = true
  form.choices = ['', '']
  dialogOpen.value = true
}

function openEdit(poll: Poll) {
  editingId.value = poll.id
  form.title = poll.title
  form.description = poll.description ?? ''
  // 绑定文章可能不在下拉的前 100 篇里，补一条占位项，否则编辑时绑定被静默改成全站。
  if (poll.post_id != null && !postOptions.value.some(p => p.id === poll.post_id)) {
    postOptions.value = [
      ...postOptions.value,
      { id: poll.post_id, title: `#${poll.post_id}`, slug: '', status: 'published', views: 0, likes_count: 0, comments_count: 0, is_pinned: false, created_at: null, published_at: null, category: null }
    ]
  }
  form.post_id = poll.post_id == null ? SITE_WIDE : String(poll.post_id)
  form.is_active = poll.is_active
  form.allow_multiple = poll.allow_multiple
  form.show_results = poll.show_results
  dialogOpen.value = true
}

function addChoice() {
  if (form.choices.length >= 20) {
    toast.error('最多 20 个选项')
    return
  }
  form.choices.push('')
}

function removeChoice(index: number) {
  if (form.choices.length <= 2) return
  form.choices.splice(index, 1)
}

async function save() {
  if (!form.title.trim()) {
    toast.error('请输入投票标题')
    return
  }
  if (editingId.value === null && cleanChoices.value.length < 2) {
    toast.error('至少填写 2 个非空选项')
    return
  }
  saving.value = true
  try {
    const body = {
      title: form.title.trim(),
      description: form.description.trim() || null,
      post_id: formPostId.value,
      is_active: form.is_active,
      allow_multiple: form.allow_multiple,
      show_results: form.show_results
    }
    if (editingId.value === null) {
      await pollsAPI.createPoll({ ...body, choices: cleanChoices.value })
      toast.success('创建成功')
    } else {
      await pollsAPI.updatePoll(editingId.value, body)
      toast.success('已保存')
    }
    dialogOpen.value = false
    await loadData()
  } catch (e) {
    // 失败提示由 apiFetch 统一 toast；弹窗保持打开并保留输入
    console.error('[polls] save failed:', e)
  } finally {
    saving.value = false
  }
}

/** 结束 / 重新开启：只写 is_active，PUT 的局部语义保证其它字段原样保留。 */
async function toggleActive(poll: Poll) {
  await pollsAPI.updatePoll(poll.id, { is_active: !poll.is_active })
  toast.success(poll.is_active ? '投票已结束' : '投票已重新开启')
  await loadData()
}

function confirmDelete(id: number) {
  pendingDeleteId.value = id
  deleteDialogOpen.value = true
}

async function doDelete() {
  const id = pendingDeleteId.value
  if (id == null) return
  await pollsAPI.deletePoll(id)
  toast.success('删除成功')
  pendingDeleteId.value = null
  await loadData()
}

onMounted(loadData)
</script>

<template>
  <AdminListPage
    title="投票管理"
    :icon="ChartColumn"
    description="投票可绑定到指定文章（只在该篇下方展示），也可作为全站投票出现在每篇文章下方。"
    :count="polls.length"
  >
    <template #actions>
      <Button
        size="sm"
        class="shadow-sm"
        @click="openNew"
      >
        <Plus data-icon="inline-start" />
        新建投票
      </Button>
    </template>

    <div class="p-5">
      <template v-if="loading">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Skeleton
            v-for="i in 4"
            :key="`sk-${i}`"
            class="h-52 rounded-[12px]"
          />
        </div>
      </template>

      <template v-else-if="loadError">
        <div class="card-surface py-16 text-center">
          <div class="text-sm text-destructive mb-3">
            投票列表加载失败
          </div>
          <Button
            variant="outline"
            size="sm"
            @click="loadData()"
          >
            重试
          </Button>
        </div>
      </template>

      <template v-else-if="polls.length === 0">
        <div class="card-surface py-24 text-center text-muted-foreground">
          <div class="mb-4 opacity-30 flex items-center justify-center">
            <ChartColumn class="size-16" />
          </div>
          <div class="text-sm mb-2">
            还没有投票
          </div>
          <div class="text-xs opacity-70">
            创建一个投票：绑定文章时只出现在那一篇文章下方，不绑定则出现在每篇文章下方
          </div>
        </div>
      </template>

      <template v-else>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div
            v-for="poll in polls"
            :key="poll.id"
            class="card-surface p-4 shadow-sm flex flex-col gap-3"
          >
            <div class="flex items-start justify-between gap-2">
              <h3 class="font-semibold text-base leading-snug line-clamp-2">
                {{ poll.title }}
              </h3>
              <span class="text-xs text-muted-foreground shrink-0 mt-0.5">#{{ poll.id }}</span>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <Badge
                class="rounded-[10px]"
                :variant="poll.is_active ? 'default' : 'secondary'"
              >
                {{ poll.is_active ? '进行中' : '已结束' }}
              </Badge>
              <Badge
                variant="outline"
                class="rounded-[10px] max-w-64 truncate"
                :title="bindingLabel(poll)"
              >
                {{ bindingLabel(poll) }}
              </Badge>
              <Badge
                variant="outline"
                class="rounded-[10px]"
              >
                {{ poll.allow_multiple ? '多选' : '单选' }}
              </Badge>
              <Badge
                variant="outline"
                class="rounded-[10px]"
              >
                {{ poll.show_results ? '显示结果' : '隐藏结果' }}
              </Badge>
              <span class="text-xs text-muted-foreground">
                共 {{ poll.total_votes ?? 0 }} 票 · {{ fmtDate(poll.created_at) }}
              </span>
            </div>

            <p
              v-if="poll.description"
              class="text-sm text-muted-foreground line-clamp-2"
            >
              {{ poll.description }}
            </p>

            <ul class="flex flex-col gap-2">
              <li
                v-for="choice in poll.choices"
                :key="choice.id"
                class="flex flex-col gap-1"
              >
                <div class="flex items-center justify-between text-xs">
                  <span class="truncate">{{ choice.text }}</span>
                  <span class="tabular-nums text-muted-foreground shrink-0">
                    {{ choice.votes_count ?? 0 }} · {{ percent(poll, choice.votes_count) }}%
                  </span>
                </div>
                <div class="h-1.5 rounded-full bg-muted overflow-hidden">
                  <div
                    class="h-full rounded-full bg-primary transition-[width] duration-300"
                    :style="{ width: `${percent(poll, choice.votes_count)}%` }"
                  />
                </div>
              </li>
            </ul>

            <div class="flex flex-wrap justify-end gap-1">
              <Button
                variant="ghost"
                size="sm"
                @click="toggleActive(poll)"
              >
                <component
                  :is="poll.is_active ? Pause : Play"
                  data-icon="inline-start"
                />
                {{ poll.is_active ? '结束' : '重新开启' }}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                @click="openEdit(poll)"
              >
                <Pencil data-icon="inline-start" />
                编辑
              </Button>
              <Button
                variant="ghost"
                size="sm"
                class="text-destructive hover:text-destructive hover:bg-destructive-muted"
                @click="confirmDelete(poll.id)"
              >
                <Trash2 data-icon="inline-start" />
                删除
              </Button>
            </div>
          </div>
        </div>
      </template>
    </div>

    <AdminCrudDialog
      v-model:open="dialogOpen"
      :title="editingId === null ? '新建投票' : '编辑投票'"
      :loading="saving"
      :submit-text="editingId === null ? '创建' : '保存'"
      @submit="save"
    >
      <div class="flex flex-col gap-4">
        <div>
          <Label
            for="poll-form-title"
            class="mb-1 block text-xs text-muted-foreground"
          >
            标题 <span class="text-destructive">*</span>
          </Label>
          <Input
            id="poll-form-title"
            v-model="form.title"
            maxlength="200"
            placeholder="投票标题"
            class="h-9 rounded-[10px]"
          />
        </div>

        <div>
          <Label
            for="poll-form-desc"
            class="mb-1 block text-xs text-muted-foreground"
          >
            说明（可选）
          </Label>
          <Textarea
            id="poll-form-desc"
            v-model="form.description"
            maxlength="500"
            rows="3"
            class="rounded-[10px]"
            placeholder="补充说明，最多 500 字"
          />
        </div>

        <div>
          <Label
            for="poll-form-post"
            class="mb-1 block text-xs text-muted-foreground"
          >
            展示位置
          </Label>
          <Select
            id="poll-form-post"
            v-model="form.post_id"
          >
            <SelectTrigger
              id="poll-form-post-trigger"
              class="h-9 w-full rounded-[10px]"
            >
              <SelectValue placeholder="选择展示位置" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem :value="SITE_WIDE">
                全站（每篇文章下方）
              </SelectItem>
              <SelectItem
                v-for="p in postOptions"
                :key="`poll-post-${p.id}`"
                :value="String(p.id)"
              >
                {{ p.title }}
              </SelectItem>
            </SelectContent>
          </Select>
          <p class="mt-1 text-xs text-muted-foreground">
            绑定文章后，这条投票只出现在该篇文章正文下方；前台按文章取票，不选就是全站。
          </p>
        </div>

        <div v-if="editingId === null">
          <div class="mb-1.5 flex items-center justify-between">
            <Label class="text-xs text-muted-foreground">
              选项（至少 2 个，最多 20 个）
            </Label>
            <Button
              type="button"
              variant="outline"
              size="sm"
              @click="addChoice"
            >
              <Plus data-icon="inline-start" />
              添加选项
            </Button>
          </div>
          <div class="flex flex-col gap-2">
            <div
              v-for="(_, index) in form.choices"
              :key="`choice-${index}`"
              class="flex items-center gap-2"
            >
              <Input
                v-model="form.choices[index]"
                :aria-label="`选项 ${index + 1}`"
                maxlength="200"
                :placeholder="`选项 ${index + 1}`"
                class="h-9 rounded-[10px]"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                class="shrink-0 text-destructive hover:text-destructive hover:bg-destructive-muted"
                :disabled="form.choices.length <= 2"
                title="删除选项"
                :aria-label="`删除选项 ${index + 1}`"
                @click="removeChoice(index)"
              >
                <Trash2 data-icon="inline-start" />
              </Button>
            </div>
          </div>
        </div>

        <p
          v-else
          class="text-xs text-muted-foreground"
        >
          选项创建后不可修改（票数记在选项 id 上，改选项等于删票）；需要不同选项请新建一条投票。
        </p>

        <div class="flex flex-col gap-3">
          <div class="flex items-center justify-between gap-3">
            <Label class="text-sm">{{ editingId === null ? '立即启用' : '进行中' }}</Label>
            <Switch
              v-model="form.is_active"
              :aria-label="editingId === null ? '立即启用' : '进行中'"
            />
          </div>
          <div class="flex items-center justify-between gap-3">
            <Label class="text-sm">允许多选</Label>
            <Switch
              v-model="form.allow_multiple"
              aria-label="允许多选"
            />
          </div>
          <div class="flex items-center justify-between gap-3">
            <Label class="text-sm">投票前显示结果</Label>
            <Switch
              v-model="form.show_results"
              aria-label="投票前显示结果"
            />
          </div>
        </div>
      </div>
    </AdminCrudDialog>

    <AdminConfirmDialog
      v-model:open="deleteDialogOpen"
      title="确认删除投票"
      description="删除会同时移除该投票的全部投票记录，此操作不可撤销。"
      confirm-text="确认删除"
      :on-confirm="doDelete"
    />
  </AdminListPage>
</template>
