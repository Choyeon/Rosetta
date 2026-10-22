<!--
  投票管理页：后台唯一的投票入口。
  硬契约：
  - 后端只有 POST/GET/DELETE /api/voting/polls，没有 PUT 与"结束投票"接口，所以本页只做
    创建 / 查看 / 删除；is_active 只能在创建时定，改状态要先删后建（不做假编辑）。
  - PollCreate 的 choices 是 string[]（2–200 项，每项 1–200 字符），选项 id 由后端按顺序生成。
  - Poll 与 Post 没有关联列：创建出来的投票会挂在**每篇**文章下方（见 usePolls.ts 头注释），
    本页描述必须把这一点说清楚，否则管理员会以为能选文章。
-->
<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { usePolls, type Poll } from '~~/composables/usePolls'
import { useToast } from '~~/composables/useToast'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { Switch } from '~~/components/ui/switch'
import { Textarea } from '~~/components/ui/textarea'
import { ChartColumn, Plus, Trash2 } from '@lucide/vue'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()
const pollsAPI = usePolls()

const polls = ref<Poll[]>([])
const loading = ref(false)
const loadError = ref(false)

const dialogOpen = ref(false)
const saving = ref(false)
const deleteDialogOpen = ref(false)
const pendingDeleteId = ref<number | null>(null)

const form = reactive({
  title: '',
  description: '',
  is_active: true,
  allow_multiple: false,
  show_results: true,
  choices: ['', ''] as string[]
})

const cleanChoices = computed(() =>
  form.choices.map(c => c.trim()).filter(Boolean)
)

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
    polls.value = await pollsAPI.fetchAllPolls()
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
  form.title = ''
  form.description = ''
  form.is_active = true
  form.allow_multiple = false
  form.show_results = true
  form.choices = ['', '']
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
  if (cleanChoices.value.length < 2) {
    toast.error('至少填写 2 个非空选项')
    return
  }
  saving.value = true
  try {
    await pollsAPI.createPoll({
      title: form.title.trim(),
      description: form.description.trim() || null,
      is_active: form.is_active,
      allow_multiple: form.allow_multiple,
      show_results: form.show_results,
      choices: cleanChoices.value
    })
    toast.success('创建成功')
    dialogOpen.value = false
    await loadData()
  } catch (e) {
    // 失败提示由 apiFetch 统一 toast；弹窗保持打开并保留输入
    console.error('[polls] save failed:', e)
  } finally {
    saving.value = false
  }
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
    description="投票目前没有与文章建立关联，进行中的投票会展示在每篇文章下方。"
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
            创建一个投票，它会出现在每篇文章的正文下方
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

            <div class="flex justify-end">
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
      title="新建投票"
      :loading="saving"
      submit-text="创建"
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

        <div class="flex flex-col gap-3">
          <div class="flex items-center justify-between gap-3">
            <Label class="text-sm">立即启用</Label>
            <Switch
              v-model="form.is_active"
              aria-label="立即启用"
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
