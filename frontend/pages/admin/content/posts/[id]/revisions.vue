<!--
  文章版本历史页（/admin/content/posts/:id/revisions）

  数据来源：GET /admin/posts/{id}/revisions（裸对象，无 success 信封）+ 单版本详情 + compare。
  版本由后端在「标题/正文/摘要真的变了」的保存时自动写入，快照存的是改动前的状态；
  恢复（POST .../revisions/{rid}/restore）会先给当前内容留一版备份再回滚，因此恢复本身也可再回退。
  diff 在前端算（lib/revisionDiff.ts 的 LCS），后端只给两份正文快照。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      :title="pageTitle"
      description="编辑保存会自动留版本；可预览快照、对比差异或回滚到任意版本"
      :icon="History"
    >
      <template #actions>
        <Button
          variant="outline"
          size="sm"
          class="rounded-xl"
          @click="router.push('/admin/content/posts')"
        >
          <ArrowLeft data-icon="inline-start" /> 返回文章列表
        </Button>
      </template>
    </AdminPageHeader>

    <Alert
      v-if="!loading && loadError"
      variant="destructive"
      class="rounded-xl"
    >
      <AlertTriangle class="size-4" />
      <AlertTitle>版本历史加载失败</AlertTitle>
      <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
        <span>{{ loadError }}</span>
        <Button
          variant="outline"
          size="sm"
          class="rounded-lg shrink-0"
          @click="loadRevisions"
        >
          <RotateCcw data-icon="inline-start" /> 重试
        </Button>
      </AlertDescription>
    </Alert>

    <div
      v-if="loading"
      class="flex flex-col gap-3"
    >
      <Skeleton
        v-for="i in 4"
        :key="i"
        class="h-24 rounded-2xl"
      />
    </div>

    <div
      v-else-if="revisions.length === 0 && !loadError"
      class="py-16"
    >
      <Alert
        variant="info"
        class="rounded-xl max-w-lg mx-auto"
      >
        <Info class="size-4" />
        <AlertTitle>还没有版本记录</AlertTitle>
        <AlertDescription>修改标题、正文或摘要并保存后，系统会自动保存改动前的快照。</AlertDescription>
      </Alert>
    </div>

    <div
      v-else
      class="flex flex-col gap-3"
    >
      <div
        v-for="rev in revisions"
        :key="rev.id"
        class="card-surface p-5"
      >
        <div class="flex items-start justify-between gap-4 flex-wrap">
          <div class="min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <Badge
                variant="outline"
                class="text-[11px] tabular-nums"
              >
                版本 #{{ rev.revision_number }}
              </Badge>
              <span
                v-if="rev.change_summary"
                class="text-sm font-medium"
              >{{ rev.change_summary }}</span>
              <span
                class="text-sm text-muted-foreground truncate"
                :title="revTitle(rev)"
              >{{ revTitle(rev) }}</span>
            </div>
            <div class="flex items-center gap-4 mt-1 text-xs text-muted-foreground tabular-nums flex-wrap">
              <span>{{ formatAdminDate(rev.created_at) }}</span>
              <span v-if="rev.author">编辑人 {{ rev.author.nickname || rev.author.username }}</span>
            </div>
          </div>
          <div class="flex items-center gap-1 shrink-0 flex-wrap">
            <Button
              variant="outline"
              size="sm"
              class="rounded-xl"
              @click="togglePreview(rev.id)"
            >
              <Eye data-icon="inline-start" />
              {{ previewId === rev.id ? '收起快照' : '查看快照' }}
            </Button>
            <Button
              variant="outline"
              size="sm"
              class="rounded-xl"
              :class="{ 'ring-1 ring-primary': baseId === rev.id }"
              @click="baseId = baseId === rev.id ? null : rev.id"
            >
              设为基准
            </Button>
            <Button
              variant="outline"
              size="sm"
              class="rounded-xl"
              :class="{ 'ring-1 ring-primary': targetId === rev.id }"
              @click="targetId = targetId === rev.id ? null : rev.id"
            >
              设为对比
            </Button>
            <Button
              variant="ghost"
              size="sm"
              class="rounded-xl text-error hover:text-error hover:bg-error-muted"
              @click="restoreTarget = rev; restoreOpen = true"
            >
              <RotateCcw data-icon="inline-start" /> 恢复此版本
            </Button>
          </div>
        </div>

        <div
          v-if="previewId === rev.id"
          class="mt-4 border-t border-border pt-4"
        >
          <p
            v-if="previewLoading"
            class="text-sm text-muted-foreground"
          >
            快照加载中…
          </p>
          <div
            v-else-if="preview"
            class="flex flex-col gap-3"
          >
            <div>
              <h4 class="text-xs font-semibold text-muted-foreground mb-1">
                标题
              </h4>
              <p class="text-sm whitespace-pre-wrap break-words">
                {{ pickLocalized(preview.title) || '（空）' }}
              </p>
            </div>
            <div>
              <h4 class="text-xs font-semibold text-muted-foreground mb-1">
                摘要
              </h4>
              <p class="text-sm whitespace-pre-wrap break-words">
                {{ pickLocalized(preview.excerpt) || '（未设置）' }}
              </p>
            </div>
            <div>
              <h4 class="text-xs font-semibold text-muted-foreground mb-1">
                正文
              </h4>
              <pre class="text-xs leading-relaxed bg-muted rounded-xl p-3 overflow-x-auto max-h-96 overflow-y-auto whitespace-pre-wrap break-words">{{ flattenLocalizedContent(preview.content) || '（空）' }}</pre>
            </div>
          </div>
        </div>
      </div>

      <div
        v-if="baseId && targetId"
        class="card-surface p-5"
      >
        <div class="flex items-center justify-between gap-3 flex-wrap mb-3">
          <h3 class="font-semibold flex items-center gap-2">
            <GitCompareArrows class="size-4" /> 版本对比
            <span class="text-sm font-normal text-muted-foreground tabular-nums">
              #{{ numberById(baseId) }} → #{{ numberById(targetId) }}
            </span>
          </h3>
          <div
            v-if="!compareError"
            class="flex items-center gap-2 text-xs tabular-nums"
          >
            <Badge
              variant="outline"
              class="text-success border-transparent bg-success-muted"
            >
              +{{ stats.added }}
            </Badge>
            <Badge
              variant="outline"
              class="text-error border-transparent bg-error-muted"
            >
              -{{ stats.removed }}
            </Badge>
          </div>
        </div>
        <p
          v-if="compareError"
          class="text-sm text-error"
        >
          {{ compareError }}
        </p>
        <p
          v-else-if="comparing"
          class="text-sm text-muted-foreground"
        >
          正在比对…
        </p>
        <pre
          v-else
          class="text-xs leading-relaxed overflow-x-auto max-h-[32rem] overflow-y-auto rounded-xl bg-muted p-3"
          aria-label="版本差异"
        ><span
          v-for="(line, idx) in diff"
          :key="idx"
          class="block px-1 rounded-sm"
          :class="lineClass(line.type)"
        >{{ linePrefix(line.type) }}{{ line.text }}</span></pre>
      </div>
    </div>

    <DangerConfirmDialog
      v-model:open="restoreOpen"
      title="确认恢复到该版本？"
      :description="restoreDescription"
      confirm-text="恢复"
      :on-confirm="confirmRestore"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  fetchPostRevisions,
  fetchPostRevision,
  comparePostRevisions,
  restorePostRevision,
  formatAdminDate,
  type AdminRevisionItem,
  type AdminRevisionDetail
} from '~~/composables/useAdminManage'
import { diffLines, diffStats, flattenLocalizedContent, pickLocalized, type DiffLineType } from '~~/lib/revisionDiff'
import { useToast } from '~~/composables/useToast'
import { extractApiErrorMessage } from '~~/lib/utils'
import {
  ArrowLeft, AlertTriangle, Eye, GitCompareArrows, History, Info, RotateCcw
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'
import DangerConfirmDialog from '~~/components/admin/tools/DangerConfirmDialog.vue'
import AdminPageHeader from '~~/components/admin/AdminPageHeader.vue'

definePageMeta({ ssr: false, layout: 'admin' })

const route = useRoute()
const router = useRouter()
const toast = useToast()

const postId = computed(() => Number(route.params.id))

const loading = ref(true)
const loadError = ref('')
const revisions = ref<AdminRevisionItem[]>([])
const currentTitle = ref<Record<string, string> | string | null>(null)

const previewId = ref<number | null>(null)
const preview = ref<AdminRevisionDetail | null>(null)
const previewLoading = ref(false)

const baseId = ref<number | null>(null)
const targetId = ref<number | null>(null)
const diff = ref<ReturnType<typeof diffLines>>([])
const comparing = ref(false)
const compareError = ref('')

const restoreOpen = ref(false)
const restoreTarget = ref<AdminRevisionItem | null>(null)

const pageTitle = computed(() => {
  const title = pickLocalized(currentTitle.value ?? '')
  return title ? `版本历史 · ${title}` : '版本历史'
})
const stats = computed(() => diffStats(diff.value))
const restoreDescription = computed(() =>
  restoreTarget.value
    ? `文章将回到版本 #${restoreTarget.value.revision_number} 的内容，当前内容会先自动存为新版本，可再次回退。`
    : '')

async function loadRevisions() {
  loading.value = true
  loadError.value = ''
  try {
    const resp = await fetchPostRevisions(postId.value)
    revisions.value = resp.revisions ?? []
    currentTitle.value = resp.current_title ?? null
  } catch (e) {
    revisions.value = []
    const err = e as { data?: unknown, message?: string }
    loadError.value = extractApiErrorMessage(err?.data, err?.message || '加载版本历史失败')
  } finally {
    loading.value = false
  }
}

function numberById(id: number): string {
  return String(revisions.value.find(r => r.id === id)?.revision_number ?? id)
}

function revTitle(rev: AdminRevisionItem): string {
  return pickLocalized(rev.title) || '（无标题）'
}

async function togglePreview(id: number) {
  if (previewId.value === id) {
    previewId.value = null
    preview.value = null
    return
  }
  previewId.value = id
  preview.value = null
  previewLoading.value = true
  try {
    preview.value = await fetchPostRevision(postId.value, id)
  } catch {
    // apiFetch 已 toast，这里只收起面板
    previewId.value = null
  } finally {
    previewLoading.value = false
  }
}

async function runCompare() {
  if (!baseId.value || !targetId.value) {
    diff.value = []
    compareError.value = ''
    return
  }
  if (baseId.value === targetId.value) {
    diff.value = []
    compareError.value = '请选择两个不同的版本进行对比。'
    return
  }
  comparing.value = true
  compareError.value = ''
  try {
    const resp = await comparePostRevisions(postId.value, baseId.value, targetId.value)
    diff.value = diffLines(
      flattenLocalizedContent(resp.revision1.content),
      flattenLocalizedContent(resp.revision2.content)
    )
  } catch (e) {
    diff.value = []
    const err = e as { data?: unknown, message?: string }
    compareError.value = extractApiErrorMessage(err?.data, err?.message || '版本比对失败')
  } finally {
    comparing.value = false
  }
}

watch([baseId, targetId], runCompare)

function linePrefix(type: DiffLineType): string {
  return type === 'added' ? '+ ' : type === 'removed' ? '- ' : '  '
}

function lineClass(type: DiffLineType): string {
  if (type === 'added') return 'bg-success-muted text-success-foreground'
  if (type === 'removed') return 'bg-error-muted text-error-foreground'
  return 'text-muted-foreground'
}

async function confirmRestore() {
  const target = restoreTarget.value
  if (!target) return
  await restorePostRevision(postId.value, target.id, { silentToast: true })
  toast.success(`已恢复到版本 #${target.revision_number}`)
  restoreTarget.value = null
  baseId.value = null
  targetId.value = null
  await loadRevisions()
}

onMounted(loadRevisions)
</script>
