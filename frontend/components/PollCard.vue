<!--
  投票卡片：poll 用 post_id 绑定文章（为空 = 全站投票，出现在每一篇下方），文章页把
  「本篇专属 + 全站」的活动投票随正文载荷一起 SSR 直出。投票选择项按 allow_multiple 走 radio / checkbox；投票后：
  - 若 poll.show_results=true，用条形 + 计数 + 百分比渲染结果；
  - 若 show_results=false 且非 staff，后端把 votes_count 抹成 null，前端只回显"感谢参与"，
    不伪造百分比。
  防误提交：localStorage 里记 `rosetta:voted-polls`（见 composables/usePolls.ts 说明）；
  命中即直接把卡片切到"已投票"态，不再显示提交按钮。这不是防刷，是防手滑。
-->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '~~/components/ui/button'
import { Card } from '~~/components/ui/card'
import { usePolls, type Poll } from '~~/composables/usePolls'
import { BarChart3 } from '~~/lib/lucide-svg-icons'

interface Props { poll: Poll }
const props = defineProps<Props>()
const { t } = useI18n()
const { vote, readVotedPollIds } = usePolls()

const selection = ref<number[]>([])
const submitting = ref(false)
const errorMessage = ref<string | null>(null)
// 已投票态存在 localStorage，服务端读不到。卡片现在随正文载荷 SSR 直出，
// 若在 setup 期取值就是「SSR 未投票 / 客户端已投票」两套首渲染（hydration mismatch），
// 所以两端都先按未投票出牌，挂载后再同步一次。
const alreadyVoted = ref(false)

onMounted(() => {
  alreadyVoted.value = readVotedPollIds().has(props.poll.id)
})

watch(() => props.poll.id, (id) => {
  selection.value = []
  errorMessage.value = null
  alreadyVoted.value = readVotedPollIds().has(id)
})

const sortedChoices = computed(() =>
  [...props.poll.choices].sort((a, b) => a.order - b.order)
)

const totalVisibleVotes = computed(() => {
  if (!props.poll.show_results && !alreadyVoted.value) return 0
  return sortedChoices.value.reduce((sum, c) => sum + (c.votes_count ?? 0), 0) || props.poll.total_votes || 0
})

const canSeeResults = computed(() => {
  if (props.poll.show_results) return true
  return alreadyVoted.value && sortedChoices.value.some(c => typeof c.votes_count === 'number')
})

const resultsMode = computed(() => canSeeResults.value || !props.poll.is_active)

function toggleChoice(id: number) {
  if (props.poll.allow_multiple) {
    const i = selection.value.indexOf(id)
    if (i >= 0) selection.value.splice(i, 1)
    else selection.value.push(id)
  } else {
    selection.value = [id]
  }
  errorMessage.value = null
}

async function submitVote() {
  if (submitting.value) return
  if (!selection.value.length) {
    errorMessage.value = t('poll.pickAtLeastOne', '请先选择一个选项')
    return
  }
  submitting.value = true
  const outcome = await vote(props.poll.id, selection.value)
  submitting.value = false
  if (outcome === 'ok' || outcome === 'duplicate') {
    alreadyVoted.value = true
    selection.value = []
    errorMessage.value = null
  } else if (outcome === 'closed') {
    errorMessage.value = t('poll.closed', '投票已结束')
  } else {
    errorMessage.value = t('poll.submitFailed', '提交失败，请稍后重试')
  }
}

function percentage(count: number | null): string {
  if (typeof count !== 'number' || totalVisibleVotes.value === 0) return '0%'
  return `${Math.round((count / totalVisibleVotes.value) * 100)}%`
}

function barWidth(count: number | null): string {
  if (typeof count !== 'number' || totalVisibleVotes.value === 0) return '0%'
  return `${(count / totalVisibleVotes.value) * 100}%`
}
</script>

<template>
  <Card class="mt-12 rounded-2xl border-border/60 bg-card/60 p-5 sm:p-6">
    <div class="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
      <BarChart3 class="size-4" />
      <span>{{ t('poll.title', '投票') }}</span>
    </div>
    <h3 class="mt-3 font-display text-lg font-semibold tracking-tight">
      {{ poll.title }}
    </h3>
    <p
      v-if="poll.description"
      class="mt-2 text-sm text-muted-foreground"
    >
      {{ poll.description }}
    </p>

    <div class="mt-4 flex flex-col gap-2">
      <label
        v-for="choice in sortedChoices"
        :key="choice.id"
        class="group flex cursor-pointer items-start gap-3 rounded-lg border border-transparent p-2 transition-colors hover:bg-accent/30"
        :class="selection.includes(choice.id) ? 'border-primary/40 bg-primary/5' : ''"
      >
        <input
          :type="poll.allow_multiple ? 'checkbox' : 'radio'"
          :name="`poll-${poll.id}`"
          :value="choice.id"
          :checked="selection.includes(choice.id)"
          :disabled="submitting || alreadyVoted || resultsMode"
          class="mt-1 size-4 accent-[hsl(var(--primary))]"
          @change="toggleChoice(choice.id)"
        >
        <div class="min-w-0 flex-1">
          <div class="flex items-baseline justify-between gap-3 text-sm">
            <span class="truncate">{{ choice.text }}</span>
            <span
              v-if="resultsMode && typeof choice.votes_count === 'number'"
              class="shrink-0 tabular-nums text-xs text-muted-foreground"
            >
              {{ choice.votes_count }} · {{ percentage(choice.votes_count) }}
            </span>
          </div>
          <div
            v-if="resultsMode && typeof choice.votes_count === 'number'"
            class="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-muted"
            aria-hidden="true"
          >
            <div
              class="h-full rounded-full bg-primary/60 transition-[width] duration-[var(--motion-duration-base)]"
              :style="{ width: barWidth(choice.votes_count) }"
            />
          </div>
        </div>
      </label>
    </div>

    <div class="mt-4 flex flex-wrap items-center gap-3">
      <Button
        v-if="!alreadyVoted && poll.is_active && !resultsMode"
        size="sm"
        :disabled="submitting"
        @click="submitVote"
      >
        {{ submitting ? t('poll.submitting', '提交中…') : t('poll.submit', '提交投票') }}
      </Button>
      <span
        v-else-if="alreadyVoted"
        class="text-xs text-muted-foreground"
      >
        {{ t('poll.thanks', '感谢参与！') }}
      </span>
      <span
        v-else-if="!poll.is_active"
        class="text-xs text-muted-foreground"
      >
        {{ t('poll.closed', '投票已结束') }}
      </span>
      <span
        v-if="resultsMode && totalVisibleVotes > 0"
        class="text-xs text-muted-foreground tabular-nums"
      >
        {{ t('poll.totalVotes', '共 {n} 票').replace('{n}', String(totalVisibleVotes)) }}
      </span>
      <span
        v-if="poll.allow_multiple && !resultsMode && !alreadyVoted"
        class="text-xs text-muted-foreground"
      >
        {{ t('poll.multipleHint', '可多选') }}
      </span>
    </div>

    <p
      v-if="errorMessage"
      class="mt-3 text-xs text-destructive"
    >
      {{ errorMessage }}
    </p>
  </Card>
</template>
