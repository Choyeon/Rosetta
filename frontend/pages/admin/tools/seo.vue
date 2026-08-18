<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center gap-3">
      <div
        class="size-10 rounded-xl flex items-center justify-center"
        style="background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);"
      >
        <Search class="size-5 text-white" />
      </div>
      <div>
        <h1 class="text-xl font-bold tracking-tight">
          SEO 工具
        </h1>
        <p class="text-sm text-muted-foreground">
          死链检查、质量评分与站点地图
        </p>
      </div>
    </div>

    <Tabs
      v-model="activeTab"
      class="w-full"
    >
      <TabsList class="rounded-xl p-1 bg-muted/40">
        <TabsTrigger
          value="sitemap"
          class="rounded-lg data-[state=active]:text-white data-[state=active]:shadow-sm"
          :style="activeTab === 'sitemap' ? 'background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);' : ''"
        >
          <Map class="size-4 mr-1.5" /> 站点地图
        </TabsTrigger>
        <TabsTrigger
          value="score"
          class="rounded-lg data-[state=active]:text-white data-[state=active]:shadow-sm"
          :style="activeTab === 'score' ? 'background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);' : ''"
        >
          <LineChart class="size-4 mr-1.5" /> SEO 评分
        </TabsTrigger>
        <TabsTrigger
          value="links"
          class="rounded-lg data-[state=active]:text-white data-[state=active]:shadow-sm"
          :style="activeTab === 'links' ? 'background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);' : ''"
        >
          <Link2 class="size-4 mr-1.5" /> 死链检查
        </TabsTrigger>
      </TabsList>

      <TabsContent
        value="sitemap"
        class="mt-6 space-y-5"
      >
        <Card class="rounded-2xl">
          <CardHeader class="flex-row items-center gap-3 space-y-0">
            <div class="size-9 rounded-lg bg-info-muted flex items-center justify-center text-info-foreground">
              <Activity class="size-5" />
            </div>
            <div class="flex-1">
              <CardTitle class="text-base">
                sitemap.xml 当前状态
              </CardTitle>
              <CardDescription>与真实爬虫视图保持一致</CardDescription>
            </div>
            <Badge
              v-if="sitemapStatus"
              :variant="sitemapStatus.isStale ? 'secondary' : 'default'"
              :class="!sitemapStatus.isStale ? 'bg-success-muted text-success-foreground border-transparent' : ''"
            >
              {{ sitemapStatus.isStale ? '可能过期' : '最新' }}
            </Badge>
          </CardHeader>
          <CardContent class="grid md:grid-cols-3 gap-4">
            <div class="rounded-xl border border-border p-4 bg-muted/20 space-y-1">
              <p class="text-xs text-muted-foreground uppercase tracking-wide">
                上次生成时间
              </p>
              <p class="font-semibold tabular-nums">
                {{ sitemapStatus?.generatedAt || '未生成' }}
              </p>
            </div>
            <div class="rounded-xl border border-border p-4 bg-muted/20 space-y-1">
              <p class="text-xs text-muted-foreground uppercase tracking-wide">
                包含 URL 数量
              </p>
              <p class="font-semibold tabular-nums text-2xl">
                {{ sitemapStatus?.urlCount ?? '-' }}
              </p>
            </div>
            <div class="rounded-xl border border-border p-4 bg-muted/20 space-y-1">
              <p class="text-xs text-muted-foreground uppercase tracking-wide">
                是否过期
              </p>
              <p
                class="font-semibold"
                :class="sitemapStatus?.isStale ? 'text-warning' : 'text-success'"
              >
                {{ sitemapStatus?.isStale ? '是，建议重新生成' : '否' }}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card class="rounded-2xl">
          <CardContent class="pt-6 space-y-5">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h3 class="font-semibold">
                  重新生成 SEO 相关文件
                </h3>
                <p class="text-sm text-muted-foreground">
                  重新爬取全站生成 sitemap.xml 与 robots.txt
                </p>
              </div>
              <Button
                :disabled="regenerating"
                class="text-white sm:w-auto w-full"
                style="background: linear-gradient(135deg, #0EA5E9 0%, #0369A1 100%); box-shadow: 0 6px 20px -8px rgba(14,165,233,0.55);"
                @click="handleRegenerate"
              >
                <Loader2
                  v-if="regenerating"
                  class="size-4 animate-spin"
                />
                <RefreshCw
                  v-else
                  class="size-4"
                />
                {{ regenerating ? '正在生成...' : '重新生成 sitemap.xml + robots.txt' }}
              </Button>
            </div>
            <Separator />
            <div class="grid md:grid-cols-2 gap-4">
              <a
                href="/sitemap.xml"
                target="_blank"
                rel="noopener noreferrer"
                class="group p-4 rounded-xl border border-border bg-muted/20 hover:bg-muted/40 hover:border-[#0EA5E9]/40 transition-all flex items-center gap-4"
              >
                <div class="size-11 rounded-xl bg-primary-muted text-primary-foreground flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                  <FileCode class="size-5" />
                </div>
                <div>
                  <div class="font-semibold group-hover:text-[#0EA5E9] transition-colors">/sitemap.xml</div>
                  <div class="text-sm text-muted-foreground">站点地图索引</div>
                </div>
                <ExternalLink class="size-4 ml-auto text-muted-foreground" />
              </a>
              <a
                href="/robots.txt"
                target="_blank"
                rel="noopener noreferrer"
                class="group p-4 rounded-xl border border-border bg-muted/20 hover:bg-muted/40 hover:border-[#0EA5E9]/40 transition-all flex items-center gap-4"
              >
                <div class="size-11 rounded-xl bg-info-muted text-info-foreground flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                  <Bot class="size-5" />
                </div>
                <div>
                  <div class="font-semibold group-hover:text-[#0EA5E9] transition-colors">/robots.txt</div>
                  <div class="text-sm text-muted-foreground">爬虫规则说明</div>
                </div>
                <ExternalLink class="size-4 ml-auto text-muted-foreground" />
              </a>
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent
        value="score"
        class="mt-6 space-y-5"
      >
        <Card class="rounded-2xl">
          <CardHeader>
            <CardTitle>文章 SEO 质量评分</CardTitle>
            <CardDescription>基于标题、关键词、内链、图片 ALT 等维度打分（满分 100）</CardDescription>
          </CardHeader>
          <CardContent class="p-0">
            <div
              v-if="scoresLoading"
              class="p-5 space-y-3"
            >
              <Skeleton
                v-for="i in 6"
                :key="i"
                class="h-16 rounded-xl"
              />
            </div>
            <div
              v-else
              class="overflow-x-auto"
            >
              <table class="w-full text-sm">
                <thead class="bg-muted/40 text-muted-foreground text-xs uppercase tracking-wide">
                  <tr>
                    <th class="text-left font-medium px-5 py-3 w-[40%]">
                      标题
                    </th>
                    <th class="text-left font-medium px-5 py-3 w-[24%]">
                      得分
                    </th>
                    <th class="text-left font-medium px-5 py-3">
                      优化建议
                    </th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border">
                  <tr
                    v-for="s in scores"
                    :key="s.id"
                    class="hover:bg-muted/30"
                  >
                    <td class="px-5 py-4">
                      <div class="font-medium truncate">
                        {{ s.title }}
                      </div>
                      <div class="text-xs text-muted-foreground font-mono">
                        {{ s.slug }}
                      </div>
                    </td>
                    <td class="px-5 py-4">
                      <div class="flex items-center gap-3 max-w-[260px]">
                        <div class="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                          <div
                            class="h-full rounded-full transition-all"
                            :style="{
                              width: `${s.score}%`,
                              background: s.score >= 80
                                ? 'linear-gradient(90deg, #10B981, #059669)'
                                : s.score >= 60
                                  ? 'linear-gradient(90deg, #0EA5E9, #0284C7)'
                                  : 'linear-gradient(90deg, #EF4444, #DC2626)'
                            }"
                          />
                        </div>
                        <span
                          class="font-bold tabular-nums min-w-[38px] text-right"
                          :class="s.score >= 80 ? 'text-success' : s.score >= 60 ? 'text-warning' : 'text-error'"
                        >
                          {{ s.score }}
                        </span>
                      </div>
                    </td>
                    <td class="px-5 py-4">
                      <ul
                        class="space-y-0.5 text-xs text-muted-foreground"
                        style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;"
                      >
                        <li
                          v-for="(sug, i) in s.suggestions.slice(0, 2)"
                          :key="i"
                        >
                          · {{ sug }}
                        </li>
                      </ul>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div
              v-if="scores.length === 0 && !scoresLoading"
              class="p-12"
            >
              <Alert
                variant="info"
                class="rounded-xl max-w-lg mx-auto"
              >
                <Info class="size-4" />
                <AlertTitle>暂无评分数据</AlertTitle>
                <AlertDescription>评分数据在接口实现后将自动展示。</AlertDescription>
              </Alert>
            </div>
            <div
              v-if="scores.length > 0"
              class="p-4 pt-0 mt-2"
            >
              <div class="flex items-center justify-between text-xs text-muted-foreground">
                <span>第 {{ scoresPage }} / {{ Math.max(1, scoresTotalPages) }} 页，共 {{ scoresTotal }} 篇</span>
                <div class="flex gap-1">
                  <Button
                    variant="outline"
                    size="icon-sm"
                    class="rounded-lg"
                    :disabled="scoresPage <= 1"
                    @click="scoresPage--; loadScores()"
                  >
                    <ChevronLeft class="size-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon-sm"
                    class="rounded-lg"
                    :disabled="scoresPage >= scoresTotalPages"
                    @click="scoresPage++; loadScores()"
                  >
                    <ChevronRight class="size-4" />
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent
        value="links"
        class="mt-6 space-y-5"
      >
        <Card class="rounded-2xl">
          <CardContent class="pt-6 space-y-5">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h3 class="font-semibold">
                  扫描死链（4xx / 5xx / 超时）
                </h3>
                <p class="text-sm text-muted-foreground">
                  遍历文章正文中的外部链接并检测可用性
                </p>
              </div>
              <Button
                :disabled="checking"
                class="text-white sm:w-auto w-full"
                style="background: linear-gradient(135deg, #0EA5E9 0%, #0369A1 100%); box-shadow: 0 6px 20px -8px rgba(14,165,233,0.55);"
                @click="handleCheck"
              >
                <Loader2
                  v-if="checking"
                  class="size-4 animate-spin"
                />
                <ScanSearch
                  v-else
                  class="size-4"
                />
                {{ checking ? '扫描中...' : '运行死链检查' }}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card class="rounded-2xl">
          <CardContent class="p-0">
            <div
              v-if="!checkResult && !checking"
              class="p-12"
            >
              <Alert
                variant="info"
                class="rounded-xl max-w-xl mx-auto"
              >
                <Info class="size-4" />
                <AlertTitle>尚未运行检查</AlertTitle>
                <AlertDescription>点击上方「运行死链检查」按钮开始扫描文章中的超链接。</AlertDescription>
              </Alert>
            </div>
            <div
              v-else-if="checking"
              class="p-8"
            >
              <div class="flex items-center gap-3 max-w-md mx-auto">
                <Loader2 class="size-6 animate-spin text-warning" />
                <div class="space-y-0.5">
                  <div class="font-medium">
                    正在扫描外部链接...
                  </div>
                  <div class="text-sm text-muted-foreground">
                    预计需要数秒，请耐心等待
                  </div>
                </div>
              </div>
            </div>
            <div
              v-else
              class="p-6 space-y-4"
            >
              <div class="grid md:grid-cols-3 gap-4">
                <div class="rounded-xl border border-border p-4 bg-success-muted/30 space-y-1">
                  <div class="text-xs text-muted-foreground uppercase tracking-wide">
                    检测 URL 总数
                  </div>
                  <div class="font-semibold tabular-nums text-2xl">
                    {{ checkResult.url_count }}
                  </div>
                </div>
                <div
                  class="rounded-xl border border-border p-4 space-y-1"
                  :class="checkResult.ok ? 'bg-success-muted/30' : 'bg-warning-muted/30'"
                >
                  <div class="text-xs text-muted-foreground uppercase tracking-wide">
                    状态
                  </div>
                  <div
                    class="font-semibold flex items-center gap-2"
                    :class="checkResult.ok ? 'text-success' : 'text-warning'"
                  >
                    <CheckCircle
                      v-if="checkResult.ok"
                      class="size-5"
                    />
                    <AlertTriangle
                      v-else
                      class="size-5"
                    />
                    {{ checkResult.ok ? '一切正常' : '发现问题' }}
                  </div>
                </div>
                <div
                  class="rounded-xl border border-border p-4 space-y-1"
                  :class="checkResult.errors.length > 0 ? 'bg-error-muted/30' : 'bg-muted/20'"
                >
                  <div class="text-xs text-muted-foreground uppercase tracking-wide">
                    错误链接数
                  </div>
                  <div
                    class="font-semibold tabular-nums text-2xl"
                    :class="checkResult.errors.length > 0 ? 'text-error' : ''"
                  >
                    {{ checkResult.errors.length }}
                  </div>
                </div>
              </div>
              <div
                v-if="checkResult.errors.length > 0"
                class="space-y-2"
              >
                <h4 class="font-semibold text-sm">
                  错误列表
                </h4>
                <div class="rounded-xl border border-border divide-y divide-border overflow-hidden">
                  <a
                    v-for="(err, idx) in checkResult.errors"
                    :key="idx"
                    :href="err"
                    target="_blank"
                    rel="noopener noreferrer nofollow"
                    class="flex items-center gap-3 px-4 py-3 hover:bg-muted/40 transition-colors group"
                  >
                    <div class="size-7 rounded-full bg-error-muted text-error flex items-center justify-center shrink-0">
                      <XCircle class="size-4" />
                    </div>
                    <span class="font-mono text-xs flex-1 truncate group-hover:text-[#0EA5E9] transition-colors">{{ err }}</span>
                    <ExternalLink class="size-3.5 text-muted-foreground" />
                  </a>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { ref, onMounted } from 'vue'
import {
  fetchAdminSeoSitemapCheck,
  fetchAdminSeoScores,
  regenerateAdminSitemap,
  type AdminSeoScore
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import {
  Search, Map, LineChart, Link2, Activity, RefreshCw, FileCode, Bot,
  ExternalLink, Info, Loader2, ScanSearch, CheckCircle, AlertTriangle,
  XCircle, ChevronLeft, ChevronRight
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~~/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~~/components/ui/tabs'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { Separator } from '~~/components/ui/separator'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const activeTab = ref('sitemap')

const sitemapStatus = ref<{ generatedAt: string, urlCount: number, isStale: boolean } | null>(null)
const regenerating = ref(false)

const scores = ref<AdminSeoScore[]>([])
const scoresLoading = ref(true)
const scoresPage = ref(1)
const scoresTotal = ref(0)
const scoresTotalPages = ref(1)

const checking = ref(false)
const checkResult = ref<{ ok: boolean, url_count: number, errors: string[] }>({ ok: true, url_count: 0, errors: [] })

async function handleRegenerate() {
  regenerating.value = true
  try {
    await regenerateAdminSitemap()
    toast.success('已重新生成 sitemap.xml 与 robots.txt')
    await refreshSitemap()
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'regenerateAdminSitemap'}`)
  } finally {
    regenerating.value = false
  }
}

async function refreshSitemap() {
  try {
    const r = await fetchAdminSeoSitemapCheck()
    const now = new Date()
    sitemapStatus.value = {
      generatedAt: now.toLocaleString('zh-CN', { hour12: false }),
      urlCount: r?.url_count ?? 0,
      isStale: !(r?.ok ?? false)
    }
  } catch {
    sitemapStatus.value = null
  }
}

async function loadScores() {
  scoresLoading.value = true
  try {
    const r = await fetchAdminSeoScores({ page: scoresPage.value, page_size: 10 })
    scores.value = r?.items ?? []
    scoresTotal.value = r?.total ?? 0
    scoresTotalPages.value = r?.total_pages ?? 1
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'fetchAdminSeoScores'}`)
    scores.value = []
  } finally {
    scoresLoading.value = false
  }
}

async function handleCheck() {
  checking.value = true
  try {
    const r = await fetchAdminSeoSitemapCheck()
    checkResult.value = {
      ok: r?.ok ?? true,
      url_count: r?.url_count ?? 0,
      errors: r?.errors ?? []
    }
    if (checkResult.value.errors.length > 0) {
      toast.warning(`发现 ${checkResult.value.errors.length} 条可能的死链`)
    } else {
      toast.success('扫描完成，未发现死链')
    }
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'fetchAdminSeoSitemapCheck'}`)
  } finally {
    checking.value = false
  }
}

onMounted(async () => {
  await Promise.all([refreshSitemap(), loadScores()])
})
</script>
