<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center gap-3">
      <div
        class="size-10 rounded-xl flex items-center justify-center bg-primary text-primary-foreground"
      >
        <Database class="size-5 text-white" />
      </div>
      <div>
        <h1 class="text-xl font-bold tracking-tight">
          数据库迁移
        </h1>
        <p class="text-sm text-muted-foreground">
          管理 Alembic 版本升级，保持 schema 最新
        </p>
      </div>
    </div>

    <Card
      v-if="loading"
      class="rounded-2xl"
    >
      <CardContent class="p-6 space-y-4">
        <Skeleton class="h-32 rounded-2xl" />
        <Skeleton class="h-40 rounded-2xl" />
        <Skeleton class="h-40 rounded-2xl" />
      </CardContent>
    </Card>

    <template v-else>
      <div class="grid md:grid-cols-3 gap-4">
        <div class="rounded-2xl border border-border p-5 bg-card space-y-1">
          <p class="text-xs text-muted-foreground uppercase tracking-wide">
            当前版本
          </p>
          <p
            class="font-mono font-bold text-2xl tabular-nums truncate"
            :title="status.current_version"
          >
            {{ status.current_version || '未初始化' }}
          </p>
        </div>
        <div class="rounded-2xl border border-border p-5 bg-card space-y-1">
          <p class="text-xs text-muted-foreground uppercase tracking-wide">
            最新版本
          </p>
          <p
            class="font-mono font-bold text-2xl tabular-nums truncate"
            :title="status.latest_version"
          >
            {{ status.latest_version || '-' }}
          </p>
        </div>
        <div class="rounded-2xl border border-border p-5 bg-card space-y-2">
          <p class="text-xs text-muted-foreground uppercase tracking-wide">
            版本状态
          </p>
          <Badge
            :variant="status.is_latest ? 'default' : 'secondary'"
            :class="status.is_latest ? 'bg-success-muted text-success-foreground border-transparent text-sm !py-1 !px-3' : 'bg-warning-muted text-warning-foreground border-transparent text-sm !py-1 !px-3'"
            class="rounded-full"
          >
            <CheckCircle2
              v-if="status.is_latest"
              class="size-4 mr-1"
            />
            <AlertTriangle
              v-else
              class="size-4 mr-1"
            />
            {{ status.is_latest ? '已是最新版本' : '存在待应用迁移' }}
          </Badge>
        </div>
      </div>

      <div class="grid md:grid-cols-2 gap-5">
        <Card class="rounded-2xl">
          <CardHeader>
            <CardTitle class="flex items-center gap-2">
              <History class="size-5 text-success" />
              已应用迁移（{{ status.applied?.length ?? 0 }}）
            </CardTitle>
            <CardDescription>历史上已成功执行的迁移脚本</CardDescription>
          </CardHeader>
          <CardContent class="p-0">
            <ScrollArea class="max-h-80 rounded-b-2xl">
              <div
                v-if="!status.applied || status.applied.length === 0"
                class="p-8"
              >
                <Alert
                  variant="info"
                  class="rounded-xl"
                >
                  <Info class="size-4" />
                  <AlertTitle>暂无已应用迁移</AlertTitle>
                  <AlertDescription>尚未记录任何已应用的迁移版本。</AlertDescription>
                </Alert>
              </div>
              <div
                v-else
                class="divide-y divide-border"
              >
                <div
                  v-for="m in status.applied"
                  :key="m.version"
                  class="px-5 py-3 flex items-start gap-3 hover:bg-muted/30"
                >
                  <div class="size-8 rounded-lg bg-success-muted text-success-foreground flex items-center justify-center shrink-0 mt-0.5">
                    <Check class="size-4" />
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="font-mono text-sm font-semibold truncate">
                      {{ m.version }}
                    </div>
                    <div class="text-sm text-muted-foreground">
                      {{ m.message || '（无描述）' }}
                    </div>
                    <div class="text-xs text-muted-foreground tabular-nums mt-0.5">
                      {{ formatAdminDateTime(m.applied_at) }}
                    </div>
                  </div>
                </div>
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card class="rounded-2xl">
          <CardHeader>
            <CardTitle class="flex items-center gap-2">
              <PackageOpen class="size-5 text-warning" />
              待应用迁移（{{ status.pending?.length ?? 0 }}）
            </CardTitle>
            <CardDescription>点击右侧按钮可立即执行单个迁移</CardDescription>
          </CardHeader>
          <CardContent class="p-0">
            <ScrollArea class="max-h-80 rounded-b-2xl">
              <div
                v-if="!status.pending || status.pending.length === 0"
                class="p-8"
              >
                <div class="max-w-md mx-auto rounded-2xl border border-success/30 bg-success-muted/30 p-5 text-center">
                  <div class="size-14 rounded-2xl bg-success text-white mx-auto mb-3 flex items-center justify-center">
                    <PartyPopper class="size-7" />
                  </div>
                  <h3 class="font-semibold text-success">
                    好消息，数据库是最新的！
                  </h3>
                  <p class="text-sm text-muted-foreground mt-1">
                    当前没有需要应用的迁移脚本。
                  </p>
                </div>
              </div>
              <div
                v-else
                class="divide-y divide-border"
              >
                <div
                  v-for="m in status.pending"
                  :key="m.version"
                  class="px-5 py-3 flex items-start gap-3 hover:bg-muted/30"
                >
                  <div class="size-8 rounded-lg bg-warning-muted text-warning-foreground flex items-center justify-center shrink-0 mt-0.5">
                    <Clock class="size-4" />
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="font-mono text-sm font-semibold truncate">
                      {{ m.version }}
                    </div>
                    <div class="text-sm text-muted-foreground">
                      {{ m.message || '（无描述）' }}
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    class="rounded-lg shrink-0 mt-0.5"
                    :disabled="upgrading"
                    @click="handleUpgrade"
                  >
                    <Play class="size-3.5 mr-1" /> 应用
                  </Button>
                </div>
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      <Card class="rounded-2xl">
        <CardContent class="pt-6 space-y-5">
          <div
            v-if="upgradeResult"
            class="rounded-xl border border-success/40 bg-success-muted/40 p-5"
          >
            <div class="flex items-start gap-3">
              <div class="size-10 rounded-xl bg-success text-white flex items-center justify-center shrink-0">
                <CheckCircle2 class="size-5" />
              </div>
              <div class="flex-1 min-w-0">
                <h3 class="font-semibold">
                  升级成功！
                </h3>
                <p class="text-sm text-muted-foreground mt-0.5">
                  {{ upgradeResult.message || '数据库已升级到最新版本。' }}
                </p>
                <p class="text-xs text-muted-foreground mt-1">
                  页面将在 <b class="tabular-nums">{{ countdown }}</b> 秒后自动刷新。
                </p>
              </div>
            </div>
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h3 class="font-semibold text-lg">
                升级到最新版本（upgrade）
              </h3>
              <p class="text-sm text-muted-foreground">
                一键运行所有待应用迁移，将 schema 升级至 <code class="px-1.5 py-0.5 bg-muted rounded">{{ status.latest_version || 'latest' }}</code>
              </p>
            </div>
            <Button
              :disabled="upgrading || status.is_latest"
              size="lg"
              class="sm:w-auto w-full rounded-2xl !px-8 shadow-md"
              @click="handleUpgrade"
            >
              <Loader2
                v-if="upgrading"
                class="size-5 animate-spin"
              />
              <ArrowUpCircle
                v-else
                class="size-5"
              />
              {{ upgrading ? '正在执行迁移...' : `升级到最新版本` }}
            </Button>
          </div>
        </CardContent>
      </Card>
    </template>
  </div>
</template>

<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { ref, onMounted, watch } from 'vue'
import {
  fetchAdminMigrationStatus,
  upgradeAdminMigrations,
  formatAdminDateTime,
  type AdminMigrationStatus
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import {
  Database, CheckCircle2, AlertTriangle, History, Check, PackageOpen,
  Clock, PartyPopper, Play, ArrowUpCircle, Loader2, Info
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~~/components/ui/card'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { ScrollArea } from '~~/components/ui/scroll-area'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const loading = ref(true)
const upgrading = ref(false)
const countdown = ref(10)
const upgradeResult = ref<{ message?: string } | null>(null)

const emptyStatus = (): AdminMigrationStatus => ({
  current_version: '',
  latest_version: '',
  is_latest: true,
  pending: [],
  applied: []
})

const status = ref<AdminMigrationStatus>(emptyStatus())

let countdownTimer: number | null = null

function stopCountdown() {
  if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null }
}

async function loadStatus() {
  loading.value = true
  upgradeResult.value = null
  stopCountdown()
  countdown.value = 10
  try {
    const r = await fetchAdminMigrationStatus()
    status.value = r || emptyStatus()
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'fetchAdminMigrationStatus'}`)
    status.value = emptyStatus()
  } finally {
    loading.value = false
  }
}

async function handleUpgrade() {
  upgrading.value = true
  upgradeResult.value = null
  try {
    const r = await upgradeAdminMigrations()
    upgradeResult.value = { message: r?.message }
    toast.success('数据库迁移升级成功')
    countdown.value = 10
    countdownTimer = window.setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) {
        stopCountdown()
        loadStatus()
      }
    }, 1000)
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'upgradeAdminMigrations'}`)
  } finally {
    upgrading.value = false
  }
}

onMounted(loadStatus)
</script>
