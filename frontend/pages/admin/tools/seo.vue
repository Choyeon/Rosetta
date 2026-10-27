<!-- SEO 工具页：sitemap 校验/缓存清除、文章 SEO 评分分页（page_size 10/20/50，后端 le=100）、整库检索字段体检与补全、爬虫预览。
     契约： sitemap-check 走 {success,data} 信封而 search-stats 是裸对象响应（两套口径勿混）；
     「内容体检」与「站点地图」共用同一次 sitemap-check 的结果（单源 ref，切标签不发第二份请求）；
     「清除 sitemap 缓存」仅失效缓存键由下次访问惰性重建，补全接口 HTTP 200 仍可能 success:false 须自行判断；
     「爬虫预览」逐字取 GET /seo/open-graph + /seo/schema 的原始响应（两条公开口无 {success,data} 信封、
     不读调用方身份：HTTP 200 且只剩 error 键＝这篇对爬虫不存在，不能当有内容渲染）；
     全部请求用 silentToast，错误走页内 loadError + 重试分支而非自动 toast。 -->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="SEO 工具"
      description="站点地图维护、SEO 评分与已发布内容体检"
      :icon="Search"
    />

    <Tabs
      v-model="activeTab"
      class="w-full"
    >
      <AdminTabList>
        <AdminTabTrigger value="sitemap">
          <Map class="size-4" /> 站点地图
        </AdminTabTrigger>
        <AdminTabTrigger value="score">
          <LineChart class="size-4" /> SEO 评分
        </AdminTabTrigger>
        <AdminTabTrigger value="links">
          <Link2 class="size-4" /> 内容体检
        </AdminTabTrigger>
        <AdminTabTrigger value="preview">
          <Bot class="size-4" /> 爬虫预览
        </AdminTabTrigger>
      </AdminTabList>

      <TabsContent
        value="sitemap"
        class="flex flex-col gap-5 mt-6"
      >
        <AdminCard>
          <div class="flex-col gap-0 flex-row items-center gap-3 flex">
            <div class="size-9 rounded-lg bg-info-muted flex items-center justify-center text-info-muted-foreground">
              <Activity class="size-5" />
            </div>
            <div class="flex-1">
              <h3 class="text-base font-semibold">
                sitemap.xml 当前状态
              </h3>
              <p class="text-sm text-muted-foreground">
                与真实爬虫视图保持一致
              </p>
            </div>
            <Badge
              v-if="sitemapCheck"
              :variant="sitemapCheck.errors.length === 0 ? 'default' : 'secondary'"
              :class="sitemapCheck.errors.length === 0 ? 'bg-success-muted text-success-muted-foreground border-transparent' : 'bg-warning-muted text-warning-muted-foreground border-transparent'"
            >
              {{ sitemapCheck.errors.length === 0 ? '校验通过' : `${sitemapCheck.errors.length} 项待修复` }}
            </Badge>
          </div>
          <div
            v-if="sitemapLoading"
            class="flex flex-col gap-3"
          >
            <Skeleton
              v-for="i in 3"
              :key="i"
              class="h-20 rounded-xl"
            />
          </div>
          <div
            v-else-if="sitemapError"
            class="flex flex-wrap items-center justify-between gap-3"
          >
            <p class="text-sm text-destructive">
              Sitemap 校验获取失败：{{ sitemapError }}
            </p>
            <Button
              variant="outline"
              size="sm"
              class="rounded-lg shrink-0"
              @click="refreshSitemap"
            >
              <RotateCcw data-icon="inline-start" />
              重试
            </Button>
          </div>
          <div
            v-else
            class="grid md:grid-cols-3 gap-4"
          >
            <div class="flex flex-col gap-1 rounded-xl border border-border p-4 bg-muted/20">
              <p class="text-xs text-muted-foreground uppercase tracking-wide">
                上次校验时间
              </p>
              <p class="font-semibold tabular-nums">
                {{ sitemapCheckedAt || '尚未校验' }}
              </p>
            </div>
            <div class="flex flex-col gap-1 rounded-xl border border-border p-4 bg-muted/20">
              <p class="text-xs text-muted-foreground uppercase tracking-wide">
                已发布内容数
              </p>
              <p class="font-semibold tabular-nums text-2xl">
                {{ sitemapCheck?.url_count ?? '-' }}
              </p>
            </div>
            <div class="flex flex-col gap-1 rounded-xl border border-border p-4 bg-muted/20">
              <p class="text-xs text-muted-foreground uppercase tracking-wide">
                缺失 SEO 字段的文章
              </p>
              <p
                class="font-semibold"
                :class="(sitemapCheck?.errors.length ?? 0) > 0 ? 'text-warning' : 'text-success'"
              >
                {{ sitemapCheck?.errors.length ?? 0 }} 篇
              </p>
            </div>
          </div>
        </AdminCard>

        <AdminCard>
          <div class="flex flex-col gap-5 pt-6">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h3 class="font-semibold">
                  失效 sitemap 缓存
                </h3>
                <p class="text-sm text-muted-foreground">
                  后端仅清除 sitemap 缓存键，下一次访问 /sitemap.xml 时按最新文章重新生成；robots.txt 由站点配置实时渲染，无需生成
                </p>
              </div>
              <Button
                :disabled="regenerating"
                class="sm:w-auto w-full shadow-sm"
                @click="handleRegenerate"
              >
                <Loader2
                  v-if="regenerating"
                  data-icon="inline-start"
                  class="animate-spin"
                />
                <RefreshCw
                  v-else
                  data-icon="inline-start"
                />
                {{ regenerating ? '正在处理...' : '清除 sitemap 缓存' }}
              </Button>
            </div>
            <p
              v-if="regenerateError"
              class="text-sm text-destructive"
              role="alert"
            >
              {{ regenerateError }}
            </p>
            <Separator />
            <div class="grid md:grid-cols-2 gap-4">
              <a
                href="/sitemap.xml"
                target="_blank"
                rel="noopener noreferrer"
                class="group p-4 rounded-xl border border-border bg-muted/20 hover:bg-muted/40 hover:border-primary/40 transition-all flex items-center gap-4"
              >
                <div class="size-11 rounded-xl bg-primary-muted text-primary-muted-foreground flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                  <FileCode class="size-5" />
                </div>
                <div>
                  <div class="font-semibold group-hover:text-primary transition-colors">/sitemap.xml</div>
                  <div class="text-sm text-muted-foreground">站点地图索引</div>
                </div>
                <ExternalLink class="size-4 ml-auto text-muted-foreground" />
              </a>
              <a
                href="/robots.txt"
                target="_blank"
                rel="noopener noreferrer"
                class="group p-4 rounded-xl border border-border bg-muted/20 hover:bg-muted/40 hover:border-primary/40 transition-all flex items-center gap-4"
              >
                <div class="size-11 rounded-xl bg-info-muted text-info-muted-foreground flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                  <Bot class="size-5" />
                </div>
                <div>
                  <div class="font-semibold group-hover:text-primary transition-colors">/robots.txt</div>
                  <div class="text-sm text-muted-foreground">爬虫规则说明</div>
                </div>
                <ExternalLink class="size-4 ml-auto text-muted-foreground" />
              </a>
            </div>
          </div>
        </AdminCard>
      </TabsContent>

      <TabsContent
        value="score"
        class="flex flex-col gap-5 mt-6"
      >
        <AdminCard>
          <div class="flex items-start justify-between gap-3 mb-4">
            <div class="flex flex-col gap-1.5">
              <h3 class="text-base font-semibold">
                文章 SEO 质量评分
              </h3>
              <p class="text-sm text-muted-foreground">
                后端按标题长度、摘要、封面、正文长度、标签五个维度打分（满分 100），仅覆盖已发布文章
              </p>
            </div>
            <div class="flex flex-wrap items-center gap-2 shrink-0">
              <Label
                for="scores-page-size"
                class="text-sm whitespace-nowrap"
              >
                每页
              </Label>
              <Select
                v-model="scoresPageSize"
                @update:model-value="handlePageSizeChange"
              >
                <SelectTrigger
                  id="scores-page-size"
                  class="w-20 rounded-xl"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem
                    v-for="n in scoresPageSizeOptions"
                    :key="n"
                    :value="n"
                  >
                    {{ n }}
                  </SelectItem>
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="sm"
                class="rounded-lg"
                :disabled="scoresLoading"
                @click="loadScores"
              >
                <RefreshCw data-icon="inline-start" />
                重新加载
              </Button>
            </div>
          </div>
          <div class="p-0">
            <div
              v-if="scoresLoading"
              class="flex flex-col gap-3 p-5"
            >
              <Skeleton
                v-for="i in 6"
                :key="i"
                class="h-16 rounded-xl"
              />
            </div>
            <div
              v-else-if="scoresError"
              class="flex flex-wrap items-center justify-between gap-3 p-5"
            >
              <p
                class="text-sm text-destructive"
                role="alert"
              >
                评分加载失败：{{ scoresError }}
              </p>
              <Button
                variant="outline"
                size="sm"
                class="rounded-lg shrink-0"
                @click="loadScores"
              >
                <RotateCcw data-icon="inline-start" />
                重试
              </Button>
            </div>
            <div
              v-else
              class="overflow-x-auto"
            >
              <AdminDataTable
                :columns="scoreColumns"
                :data="scores"
                row-key="id"
              >
                <template #cell-title="{ row }">
                  <div class="font-medium truncate">
                    {{ (row as AdminSeoScore).title }}
                  </div>
                  <div class="text-xs text-muted-foreground font-mono">
                    {{ (row as AdminSeoScore).slug }}
                  </div>
                </template>
                <template #cell-score="{ row }">
                  <div class="flex items-center gap-3 max-w-[260px]">
                    <div class="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        class="h-full rounded-full transition-all"
                        :style="{
                          width: `${(row as AdminSeoScore).score}%`,
                          backgroundColor: (row as AdminSeoScore).score >= 80
                            ? 'hsl(var(--success))'
                            : (row as AdminSeoScore).score >= 60
                              ? 'hsl(var(--primary))'
                              : 'hsl(var(--destructive))'
                        }"
                      />
                    </div>
                    <span
                      class="font-bold tabular-nums min-w-[38px] text-right"
                      :class="(row as AdminSeoScore).score >= 80 ? 'text-success' : (row as AdminSeoScore).score >= 60 ? 'text-warning' : 'text-error'"
                    >
                      {{ (row as AdminSeoScore).score }}
                    </span>
                  </div>
                </template>
                <template #cell-suggestions="{ row }">
                  <ul class="flex flex-col gap-0.5 text-xs text-muted-foreground">
                    <li
                      v-for="(sug, i) in (row as AdminSeoScore).suggestions.slice(0, 2)"
                      :key="i"
                    >
                      · {{ sug }}
                    </li>
                    <li
                      v-if="(row as AdminSeoScore).suggestions.length > 2"
                      class="italic opacity-70"
                    >
                      另有 {{ (row as AdminSeoScore).suggestions.length - 2 }} 条建议…
                    </li>
                  </ul>
                </template>
              </AdminDataTable>
            </div>
            <div
              v-if="scores.length === 0 && !scoresLoading && !scoresError"
              class="p-12"
            >
              <Alert
                variant="info"
                class="rounded-xl max-w-lg mx-auto"
              >
                <Info class="size-4" />
                <AlertTitle>暂无评分数据</AlertTitle>
                <AlertDescription>当前没有已发布文章，或后端评分接口返回了空列表；发布文章后点击「重新加载」即可看到评分。</AlertDescription>
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
                    title="上一页"
                    aria-label="上一页评分"
                    :disabled="scoresPage <= 1"
                    @click="scoresPage--; loadScores()"
                  >
                    <ChevronLeft data-icon="inline-start" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon-sm"
                    class="rounded-lg"
                    title="下一页"
                    aria-label="下一页评分"
                    :disabled="scoresPage >= scoresTotalPages"
                    @click="scoresPage++; loadScores()"
                  >
                    <ChevronRight data-icon="inline-start" />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </AdminCard>
      </TabsContent>

      <TabsContent
        value="links"
        class="flex flex-col gap-5 mt-6"
      >
        <AdminCard>
          <div class="flex flex-col gap-5 pt-6">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h3 class="font-semibold">
                  站点内容体检（后端唯一提供的检查通道）
                </h3>
                <p class="text-sm text-muted-foreground">
                  GET /seo/sitemap-check 校验已发布文章是否具备标题 / 摘要 / 封面，返回问题清单；后端目前没有「外部死链探测」接口，故此处不再谎称扫描 4xx/5xx。结果与「站点地图」标签共用同一份数据（同一端点只请求一次），下方按钮是强制重新校验。
                </p>
              </div>
              <Button
                :disabled="checking"
                class="sm:w-auto w-full shadow-sm"
                @click="handleCheck"
              >
                <Loader2
                  v-if="checking"
                  data-icon="inline-start"
                  class="animate-spin"
                />
                <ScanSearch
                  v-else
                  data-icon="inline-start"
                />
                {{ checking ? '检查中...' : '重新运行内容体检' }}
              </Button>
            </div>
          </div>
        </AdminCard>

        <AdminCard class="overflow-hidden">
          <div class="p-0">
            <div
              v-if="!checkResult && !checking && !checkError"
              class="p-12"
            >
              <Alert
                variant="info"
                class="rounded-xl max-w-xl mx-auto"
              >
                <Info class="size-4" />
                <AlertTitle>尚无体检结果</AlertTitle>
                <AlertDescription>「站点地图」标签的那次校验未成功，点击上方「重新运行内容体检」重试；成功后这里会显示已发布文章的标题 / 摘要 / 封面完整性清单。</AlertDescription>
              </Alert>
            </div>
            <div
              v-else-if="checking"
              class="p-8"
            >
              <div class="flex items-center gap-3 max-w-md mx-auto">
                <Loader2 class="size-6 animate-spin text-warning" />
                <div class="flex flex-col gap-0.5">
                  <div class="font-medium">
                    正在校验已发布文章…
                  </div>
                  <div class="text-sm text-muted-foreground">
                    需要遍历文章列表，请稍候
                  </div>
                </div>
              </div>
            </div>
            <div
              v-else-if="checkError"
              class="flex flex-wrap items-center justify-between gap-3 p-6"
            >
              <p
                class="text-sm text-destructive"
                role="alert"
              >
                体检失败：{{ checkError }}
              </p>
              <Button
                variant="outline"
                size="sm"
                class="rounded-lg shrink-0"
                @click="handleCheck"
              >
                <RotateCcw data-icon="inline-start" />
                重试
              </Button>
            </div>
            <div
              v-else-if="checkResult"
              class="flex flex-col gap-4 p-6"
            >
              <div class="grid md:grid-cols-3 gap-4">
                <div class="flex flex-col gap-1 rounded-xl border border-border p-4 bg-muted/20">
                  <div class="text-xs text-muted-foreground uppercase tracking-wide">
                    已发布文章数（sitemap 每篇提交 4 个语言变体）
                  </div>
                  <div class="font-semibold tabular-nums text-2xl">
                    {{ checkResult.url_count }}
                  </div>
                </div>
                <div
                  class="flex flex-col gap-1 rounded-xl border border-border p-4"
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
                    {{ checkResult.ok ? '字段完整' : '存在缺失字段' }}
                  </div>
                </div>
                <div
                  class="flex flex-col gap-1 rounded-xl border border-border p-4"
                  :class="checkResult.errors.length > 0 ? 'bg-error-muted/30' : 'bg-muted/20'"
                >
                  <div class="text-xs text-muted-foreground uppercase tracking-wide">
                    问题条目数
                  </div>
                  <div
                    class="font-semibold tabular-nums text-2xl"
                    :class="checkResult.errors.length > 0 ? 'text-error' : ''"
                  >
                    {{ checkResult.errors.length }}
                  </div>
                </div>
              </div>
              <p class="text-xs text-muted-foreground">
                上次校验时间：{{ sitemapCheckedAt || '尚未校验' }}（与「站点地图」标签共用同一次请求的结果）
              </p>
              <div
                v-if="checkResult.errors.length > 0"
                class="flex flex-col gap-2"
              >
                <h4 class="font-semibold text-sm">
                  问题清单（后端最多返回 50 条）
                </h4>
                <div class="rounded-xl border border-border divide-y divide-border overflow-hidden">
                  <div
                    v-for="(err, idx) in checkResult.errors"
                    :key="idx"
                    class="flex items-center gap-3 px-4 py-3 hover:bg-muted/40 transition-colors"
                  >
                    <div class="size-7 rounded-full bg-error-muted text-error-muted-foreground flex items-center justify-center shrink-0">
                      <XCircle class="size-4" />
                    </div>
                    <span class="text-xs flex-1">{{ err }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </AdminCard>
        <!--
          检索字段体检：数据源是 /admin/tools/search-stats（整库聚合），
          与上方 sitemap-check（仅已发布文章的 SEO 三件套）互补，不重复。
          两个端点均为裸对象响应（各自独立的 response_model），不走 success/data 信封。
        -->
        <AdminCard>
          <div class="flex flex-col gap-5 p-6">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h3 class="font-semibold">
                  检索字段补全（整库统计）
                </h3>
                <p class="text-sm text-muted-foreground">
                  统计全站文章缺失 slug / 摘要 / 标签的情况；「补全缺失字段」会为无 slug 的文章按标题生成唯一 slug（中文转拼音），并按各语言正文生成摘要
                </p>
              </div>
              <div class="flex flex-wrap items-center gap-2 shrink-0">
                <Button
                  variant="outline"
                  size="sm"
                  class="rounded-lg"
                  :disabled="searchStatsLoading"
                  aria-label="刷新检索字段统计"
                  @click="refreshSearchStats()"
                >
                  <RefreshCw
                    data-icon="inline-start"
                    :class="searchStatsLoading ? 'animate-spin' : ''"
                  />
                  刷新
                </Button>
                <Button
                  size="sm"
                  class="rounded-lg"
                  :disabled="optimizing || searchStatsLoading || missingFieldTotal === 0"
                  @click="handleOptimize"
                >
                  <Loader2
                    v-if="optimizing"
                    data-icon="inline-start"
                    class="animate-spin"
                  />
                  <WandSparkles
                    v-else
                    data-icon="inline-start"
                  />
                  {{ optimizing ? '补全中...' : '补全缺失字段' }}
                </Button>
              </div>
            </div>

            <div
              v-if="searchStatsError"
              class="flex flex-wrap items-center justify-between gap-3"
            >
              <p
                class="text-sm text-destructive"
                role="alert"
              >
                统计读取失败：{{ searchStatsError }}
              </p>
              <Button
                variant="outline"
                size="sm"
                class="rounded-lg shrink-0"
                @click="refreshSearchStats()"
              >
                <RotateCcw data-icon="inline-start" />
                重试
              </Button>
            </div>

            <template v-else>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div
                  v-for="cell in searchStatCells"
                  :key="cell.label"
                  class="flex flex-col gap-1 rounded-xl border border-border p-4"
                  :class="cell.alert ? 'bg-warning-muted/30' : 'bg-muted/20'"
                >
                  <div class="text-xs text-muted-foreground uppercase tracking-wide">
                    {{ cell.label }}
                  </div>
                  <Skeleton
                    v-if="searchStatsLoading"
                    class="h-7 w-12"
                  />
                  <div
                    v-else
                    class="font-semibold tabular-nums text-2xl"
                    :class="cell.alert ? 'text-warning' : ''"
                  >
                    {{ cell.value }}
                  </div>
                </div>
              </div>

              <div
                v-if="optimizeError"
                class="text-sm text-destructive"
                role="alert"
              >
                补全失败：{{ optimizeError }}
              </div>

              <Separator />

              <div class="flex flex-col gap-2">
                <h4 class="font-semibold text-sm">
                  优化建议
                </h4>
                <Skeleton
                  v-if="searchStatsLoading"
                  class="h-10 w-full"
                />
                <Alert
                  v-else-if="!searchStats || searchStats.recommendations.length === 0"
                  variant="info"
                  class="rounded-xl"
                >
                  <CheckCircle class="size-4" />
                  <AlertTitle>字段完整</AlertTitle>
                  <AlertDescription>所有已发布文章均具备 slug、摘要与标签，无需补全。</AlertDescription>
                </Alert>
                <div
                  v-else
                  class="rounded-xl border border-border divide-y divide-border overflow-hidden"
                >
                  <div
                    v-for="rec in searchStats.recommendations"
                    :key="rec.type"
                    class="flex items-center gap-3 px-4 py-3 hover:bg-muted/40 transition-colors"
                  >
                    <div class="size-7 rounded-full bg-warning-muted text-warning-muted-foreground flex items-center justify-center shrink-0">
                      <AlertTriangle class="size-4" />
                    </div>
                    <span class="text-sm flex-1">{{ rec.message }}</span>
                    <Badge
                      variant="secondary"
                      class="shrink-0 tabular-nums"
                    >
                      {{ rec.count }} 篇
                    </Badge>
                  </div>
                </div>
              </div>

              <p
                v-if="searchStats && searchStats.total_posts > 0"
                class="text-xs text-muted-foreground"
              >
                平均 slug 长度 {{ searchStats.avg_slug_length.toFixed(1) }} 字符 ·
                平均摘要长度 {{ searchStats.avg_excerpt_length.toFixed(1) }} 字符 ·
                分类数 {{ searchStats.total_categories }}
              </p>
            </template>
          </div>
        </AdminCard>
      </TabsContent>

      <TabsContent
        value="preview"
        class="flex flex-col gap-5 mt-6"
      >
        <AdminCard>
          <div class="flex flex-wrap items-start justify-between gap-3 mb-4">
            <div class="flex flex-col gap-1.5">
              <h3 class="text-base font-semibold">
                爬虫与社交平台看到的这一篇
              </h3>
              <p class="text-sm text-muted-foreground">
                逐字取公开口 /seo/open-graph 与 /seo/schema 的原始响应：两条口不读调用方身份，
                草稿、定时未发布与作者隐藏主页的文章在这里就是「不存在」
              </p>
            </div>
            <div class="flex flex-wrap items-center gap-2 shrink-0">
              <Label
                for="seo-preview-article"
                class="text-sm whitespace-nowrap"
              >
                文章
              </Label>
              <Select
                v-model="previewArticleKey"
                @update:model-value="loadPreview"
              >
                <SelectTrigger
                  id="seo-preview-article"
                  class="w-60 rounded-xl"
                >
                  <SelectValue placeholder="选择一篇已发布文章" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem
                    v-for="p in previewCandidates"
                    :key="p.id"
                    :value="String(p.id)"
                  >
                    {{ p.title }}
                  </SelectItem>
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="sm"
                class="rounded-lg"
                :disabled="previewLoading || !previewArticleId"
                @click="loadPreview"
              >
                <RefreshCw data-icon="inline-start" />
                重新取数
              </Button>
            </div>
          </div>

          <div
            v-if="previewCandidatesLoading"
            class="flex flex-col gap-3 p-5"
          >
            <Skeleton
              v-for="i in 3"
              :key="i"
              class="h-16 rounded-xl"
            />
          </div>
          <div
            v-else-if="previewCandidates.length === 0"
            class="p-12"
          >
            <Alert
              variant="info"
              class="rounded-xl max-w-lg mx-auto"
            >
              <Info class="size-4" />
              <AlertTitle>没有可选文章</AlertTitle>
              <AlertDescription>
                候选清单来自「SEO 评分」用的同一个 GET /seo/scores（只覆盖已发布文章）；
                发布一篇文章后回到本页即可预览。
                <span
                  v-if="previewError"
                  class="block text-destructive"
                  role="alert"
                >
                  {{ previewError }}
                </span>
              </AlertDescription>
              <Button
                v-if="previewError"
                variant="outline"
                size="sm"
                class="rounded-lg mt-3"
                @click="ensurePreviewCandidates(true)"
              >
                <RotateCcw data-icon="inline-start" />
                重试
              </Button>
            </Alert>
          </div>
          <template v-else>
            <p
              v-if="previewCandidateTotal > previewCandidates.length"
              class="text-xs text-muted-foreground px-5 pb-3"
            >
              选择器只列前 {{ previewCandidates.length }} 篇（共 {{ previewCandidateTotal }} 篇已发布），
              后端 page_size 上限是 100
            </p>

            <div
              v-if="previewError"
              class="flex flex-wrap items-center justify-between gap-3 p-5"
            >
              <p
                class="text-sm text-destructive"
                role="alert"
              >
                取数失败：{{ previewError }}
              </p>
              <Button
                variant="outline"
                size="sm"
                class="rounded-lg shrink-0"
                @click="loadPreview"
              >
                <RotateCcw data-icon="inline-start" />
                重试
              </Button>
            </div>

            <Alert
              v-else-if="previewHidden"
              variant="warning"
              class="rounded-xl mx-5 mb-5"
            >
              <AlertTriangle class="size-4" />
              <AlertTitle>这篇对爬虫不存在</AlertTitle>
              <AlertDescription>
                接口回的是 200 + 只有 error 键（不是 404，避免按 id 枚举未发布内容）：{{ previewHiddenReason }}。
                若这篇其实已发布，请检查定时时间是否还在未来、作者是否关闭了「公开资料」。
              </AlertDescription>
            </Alert>

            <div
              v-else-if="previewLoading"
              class="flex flex-col gap-3 p-5"
            >
              <Skeleton
                v-for="i in 3"
                :key="i"
                class="h-16 rounded-xl"
              />
            </div>

            <div
              v-else-if="!previewArticleId"
              class="p-12"
            >
              <Alert
                variant="info"
                class="rounded-xl max-w-lg mx-auto"
              >
                <Info class="size-4" />
                <AlertTitle>还没有取数</AlertTitle>
                <AlertDescription>
                  两条公开口按文章 id 取值，只在选定文章时各请求一次，不做静默轮询。
                </AlertDescription>
              </Alert>
            </div>

            <div
              v-else
              class="flex flex-col gap-5 p-5 pt-0"
            >
              <div class="grid gap-5 lg:grid-cols-2">
                <section class="flex flex-col gap-3">
                  <h4 class="text-sm font-semibold">
                    分享卡片（og:* / twitter:*）
                  </h4>
                  <div class="rounded-xl border overflow-hidden">
                    <img
                      v-if="openGraph && openGraph['og:image']"
                      :src="openGraph['og:image']"
                      :alt="openGraph['og:image:alt'] || openGraph['og:title'] || ''"
                      class="w-full h-40 object-cover"
                      loading="lazy"
                    >
                    <div
                      v-else
                      class="w-full h-40 bg-muted flex items-center justify-center text-xs text-muted-foreground"
                    >
                      无 og:image
                    </div>
                    <div class="flex flex-col gap-1 p-3">
                      <p class="text-xs uppercase tracking-wide text-muted-foreground">
                        {{ openGraph?.['og:site_name'] || '—' }}
                      </p>
                      <p class="text-sm font-semibold">
                        {{ openGraph?.['og:title'] || '（og:title 为空）' }}
                      </p>
                      <p class="text-xs text-muted-foreground">
                        {{ openGraph?.['og:description'] || '（og:description 为空）' }}
                      </p>
                      <p
                        class="text-xs text-muted-foreground font-mono break-all"
                        data-testid="seo-preview-og-url"
                      >
                        {{ openGraph?.['og:url'] }}
                      </p>
                    </div>
                  </div>
                  <ul
                    v-if="previewWarnings.length > 0"
                    class="flex flex-col gap-1"
                  >
                    <li
                      v-for="w in previewWarnings"
                      :key="w"
                      class="flex items-start gap-1.5 text-xs text-warning"
                    >
                      <AlertTriangle class="size-3.5 mt-0.5 shrink-0" />
                      <span>{{ w }}</span>
                    </li>
                  </ul>
                </section>

                <section class="flex flex-col gap-3">
                  <h4 class="text-sm font-semibold">
                    结构化数据（JSON-LD 原文）
                  </h4>
                  <pre
                    class="max-h-80 overflow-auto rounded-xl bg-muted/40 p-3 text-xs font-mono whitespace-pre-wrap break-all"
                    data-testid="seo-preview-jsonld"
                  >{{ jsonLdText }}</pre>
                </section>
              </div>

              <Separator />

              <div class="flex flex-col gap-1.5">
                <h4 class="text-sm font-semibold">
                  逐键取值（社交抓取器按字面键名读取）
                </h4>
                <div
                  v-for="row in ogRows"
                  :key="row.key"
                  class="grid grid-cols-[minmax(0,11rem)_1fr] gap-3 text-xs py-1.5 border-b border-border/40 last:border-0"
                >
                  <span class="font-mono text-muted-foreground">{{ row.key }}</span>
                  <span class="break-all">{{ row.value || '（空）' }}</span>
                </div>
              </div>

              <p class="text-xs text-muted-foreground">
                og:description 由服务端剥掉短代码与 HTML 标签后截断到前 200 字符，
                与爬虫实际读到的 meta 同口径；本卡片展示的是接口原值，不是前台 <code>&lt;head&gt;</code> 的二次拼装。
              </p>
            </div>
          </template>
        </AdminCard>
      </TabsContent>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, shallowRef, watch } from 'vue'
import { extractApiErrorMessage } from '~~/lib/utils'
import {
  fetchAdminSearchStats,
  fetchAdminSeoJsonLd,
  fetchAdminSeoOpenGraph,
  fetchAdminSeoSitemapCheck,
  fetchAdminSeoScores,
  regenerateAdminSitemap,
  runAdminSearchOptimize,
  type AdminSearchStats,
  type AdminSeoJsonLd,
  type AdminSeoOpenGraph,
  type SitemapCheckResult,
  type AdminSeoScore
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import {
  Search, Map, LineChart, Link2, Activity, RefreshCw, FileCode, Bot,
  ExternalLink, Info, Loader2, ScanSearch, CheckCircle, AlertTriangle,
  XCircle, ChevronLeft, ChevronRight, RotateCcw, WandSparkles
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import AdminCard from '~~/components/admin/AdminCard.vue'
import AdminTabList from '~~/components/admin/AdminTabList.vue'
import AdminTabTrigger from '~~/components/admin/AdminTabTrigger.vue'
import type { AdminColumn as Column } from '~~/types/admin'
import { Tabs, TabsContent } from '~~/components/ui/tabs'
import { Badge } from '~~/components/ui/badge'
import { Label } from '~~/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { Skeleton } from '~~/components/ui/skeleton'
import { Separator } from '~~/components/ui/separator'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const activeTab = ref('sitemap')

/** 取 apiFetch 抛出错误里的后端 detail/message，避免只显示 "Internal Server Error" */
function errText(e: unknown, fallback: string): string {
  const err = e as { data?: unknown, message?: string }
  return extractApiErrorMessage(err?.data, err?.message || fallback)
}

const sitemapCheck = ref<SitemapCheckResult | null>(null)
const sitemapCheckedAt = ref('')
const sitemapLoading = ref(true)
const sitemapError = ref('')
const regenerating = ref(false)
const regenerateError = ref('')

const scores = shallowRef<AdminSeoScore[]>([])

const scoreColumns: Column[] = [
  { key: 'title', title: '标题', class: 'w-[40%]' },
  { key: 'score', title: '得分', class: 'w-[24%]' },
  { key: 'suggestions', title: '优化建议' }
]
const scoresLoading = ref(true)
const scoresError = ref('')
const scoresPage = ref(1)
const scoresTotal = ref(0)
const scoresTotalPages = ref(1)
// 后端 GET /seo/scores 的 page_size 是 Query(20, ge=1, le=100)，10/20/50 都在合法区间。
// reka-ui Select 的 value 是字符串（与 performance.vue 的慢请求数量选择器一致），发请求时再转数字。
const scoresPageSize = ref('10')
const scoresPageSizeOptions = ['10', '20', '50']

/** 「站点地图」与「内容体检」读的是同一个 GET /seo/sitemap-check ——
 *  下面三个状态是从 sitemap* 单源派生的计算值，切标签不会发第二份请求，
 *  体检按钮走 refreshSitemap() 强制重取一次（两端点无缓存旁路参数，重取即重校验）。 */
const checking = computed(() => sitemapLoading.value)
const checkError = computed(() => sitemapError.value)
const checkResult = computed(() => sitemapCheck.value)

/** 检索字段体检（GET/POST /admin/tools/*-search*）：与 sitemap-check 是两套口径，
 *  前者看"整库缺字段"，后者只看"已发布文章的 SEO 三件套"。 */
const searchStats = shallowRef<AdminSearchStats | null>(null)
const searchStatsLoading = ref(true)
const searchStatsError = ref('')
const optimizing = ref(false)
const optimizeError = ref('')

/** 缺字段总数：决定「补全」按钮是否有意义，全为 0 时禁用而不是空跑一次 POST */
const missingFieldTotal = computed(() => {
  const s = searchStats.value
  if (!s) return 0
  return s.posts_without_excerpt + s.posts_without_slug + s.posts_without_tags
})

/** 统计格子：加载态/空态共用同一组定义，避免模板里三份分支 */
const searchStatCells = computed(() => {
  const s = searchStats.value
  return [
    { label: '文章总数', value: s?.total_posts ?? 0, alert: false },
    { label: '缺摘要', value: s?.posts_without_excerpt ?? 0, alert: (s?.posts_without_excerpt ?? 0) > 0 },
    { label: '缺 slug', value: s?.posts_without_slug ?? 0, alert: (s?.posts_without_slug ?? 0) > 0 },
    { label: '缺标签', value: s?.posts_without_tags ?? 0, alert: (s?.posts_without_tags ?? 0) > 0 }
  ]
})

async function refreshSearchStats() {
  searchStatsLoading.value = true
  searchStatsError.value = ''
  try {
    searchStats.value = await fetchAdminSearchStats({ silentToast: true })
  } catch (e) {
    searchStats.value = null
    searchStatsError.value = errText(e, '检索字段统计失败')
  } finally {
    searchStatsLoading.value = false
  }
}

async function handleOptimize() {
  optimizing.value = true
  optimizeError.value = ''
  try {
    const r = await runAdminSearchOptimize({ silentToast: true })
    if (!r.success) {
      optimizeError.value = r.message || '补全失败'
      return
    }
    toast.success(r.message || `已扫描 ${r.scanned_count} 篇：补 slug ${r.slug_filled_count} 篇、摘要 ${r.excerpt_filled_count} 篇`)
    await refreshSearchStats()
  } catch (e) {
    optimizeError.value = errText(e, '补全检索字段失败')
  } finally {
    optimizing.value = false
  }
}

async function handleRegenerate() {
  regenerating.value = true
  regenerateError.value = ''
  try {
    const r = await regenerateAdminSitemap({ silentToast: true })
    toast.success(r?.message || 'Sitemap 缓存已清除，下次访问将重新生成')
    await refreshSitemap()
  } catch (e) {
    regenerateError.value = errText(e, '清除 sitemap 缓存失败')
  } finally {
    regenerating.value = false
  }
}

async function refreshSitemap() {
  sitemapLoading.value = true
  sitemapError.value = ''
  try {
    sitemapCheck.value = await fetchAdminSeoSitemapCheck({ silentToast: true })
    sitemapCheckedAt.value = new Date().toLocaleString('zh-CN', { hour12: false })
  } catch (e) {
    sitemapCheck.value = null
    sitemapCheckedAt.value = ''
    sitemapError.value = errText(e, 'Sitemap 校验失败')
  } finally {
    sitemapLoading.value = false
  }
}

async function loadScores() {
  scoresLoading.value = true
  scoresError.value = ''
  try {
    const r = await fetchAdminSeoScores(
      { page: scoresPage.value, page_size: Number(scoresPageSize.value) },
      { silentToast: true }
    )
    scores.value = r.items
    scoresTotal.value = r.total
    scoresTotalPages.value = Math.max(1, r.total_pages)
    // 后端 page 有 ge=1 约束：越界时回到最后一页，避免空白页
    if (scores.value.length === 0 && scoresTotal.value > 0 && scoresPage.value > scoresTotalPages.value) {
      scoresPage.value = scoresTotalPages.value
      await loadScores()
    }
  } catch (e) {
    scores.value = []
    scoresError.value = errText(e, '评分加载失败')
  } finally {
    scoresLoading.value = false
  }
}

/** 改每页条数时回到第 1 页：留在第 3 页换 50/页会让页码直接越过新的 total_pages */
async function handlePageSizeChange() {
  scoresPage.value = 1
  await loadScores()
}

/** 与「站点地图」标签共用 sitemapCheck 单源（同一端点），这里只是强制重取一次 */
async function handleCheck() {
  await refreshSitemap()
  const r = sitemapCheck.value
  if (!r) return
  if (r.errors.length > 0) {
    toast.warning(`发现 ${r.errors.length} 项缺失 SEO 字段`)
  } else {
    toast.success('体检完成，已发布文章字段完整')
  }
}

/** 「爬虫预览」：逐字展示两条公开口的原始响应，而不是前台 <head> 的二次拼装。
 *  选择器数据源复用 GET /seo/scores（只覆盖已发布文章），单独取满 page_size=100 上限——
 *  评分表当前页只有 10 行，直接当候选清单会让选择器缺项。 */
const previewCandidates = shallowRef<AdminSeoScore[]>([])
const previewCandidateTotal = ref(0)
const previewCandidatesLoading = ref(false)
const previewArticleKey = ref('')
const previewArticleId = computed(() => Number(previewArticleKey.value) || 0)
const previewLoading = ref(false)
const previewError = ref('')
const openGraph = shallowRef<AdminSeoOpenGraph | null>(null)
const jsonLd = shallowRef<AdminSeoJsonLd | null>(null)

/** 200 + 只剩 error 键＝这篇对爬虫不存在（不是 404，避免按 id 枚举未发布内容） */
const previewHidden = computed(() => !!openGraph.value?.error || !!jsonLd.value?.error)
const previewHiddenReason = computed(() => openGraph.value?.error || jsonLd.value?.error || '')
const jsonLdText = computed(() => JSON.stringify(jsonLd.value ?? {}, null, 2))

/** 抓取器按字面键名读取，顺序与后端 seo.py 组装 open-graph 的顺序一致 */
const OG_ROW_KEYS = [
  'og:type', 'og:title', 'og:description', 'og:image', 'og:image:alt', 'og:url',
  'og:site_name', 'og:locale', 'article:published_time', 'article:modified_time',
  'article:author', 'twitter:card', 'twitter:title', 'twitter:description', 'twitter:image'
] as const

/** og:description 的服务端截断长度（seo.py 里 `[:200]`）；达到上限就是被截过的信号 */
const OG_DESCRIPTION_LIMIT = 200

function ogValue(key: keyof AdminSeoOpenGraph): string {
  const value = openGraph.value?.[key]
  if (value === null || value === undefined) return ''
  return String(value)
}

const ogRows = computed(() => OG_ROW_KEYS.map(key => ({ key, value: ogValue(key) })))

const previewWarnings = computed(() => {
  const og = openGraph.value
  if (!og || og.error) return []
  const out: string[] = []
  if (!og['og:title']) out.push('og:title 为空：社交卡片与搜索结果都没有主标题')
  if (!og['og:description']) out.push('og:description 为空：抓取器会自己截取正文，摘要不受控')
  if (!og['og:image']) out.push('og:image 为空：分享出去没有配图（站内默认图依赖站点 URL 可用）')
  if (og['og:description'] && og['og:description'].length >= OG_DESCRIPTION_LIMIT) {
    out.push(`og:description 已达 ${OG_DESCRIPTION_LIMIT} 字符上限，末尾由服务端截断`)
  }
  if (!og['article:author']) out.push('article:author 为空：抓取器拿不到作者主页地址')
  return out
})

async function loadPreview() {
  const id = previewArticleId.value
  if (!id) return
  previewLoading.value = true
  previewError.value = ''
  openGraph.value = null
  jsonLd.value = null
  try {
    const [og, ld] = await Promise.all([
      fetchAdminSeoOpenGraph(id, { silentToast: true }),
      fetchAdminSeoJsonLd(id, { silentToast: true })
    ])
    openGraph.value = og
    jsonLd.value = ld
  } catch (e) {
    previewError.value = errText(e, '爬虫视图取数失败')
  } finally {
    previewLoading.value = false
  }
}

/** 候选清单只在首次进入该标签时取一次；失败时 force 重试，成功则复用（不轮询）。 */
async function ensurePreviewCandidates(force = false) {
  if (previewCandidatesLoading.value) return
  if (!force && previewCandidates.value.length > 0) return
  previewCandidatesLoading.value = true
  previewError.value = ''
  try {
    const r = await fetchAdminSeoScores({ page: 1, page_size: 100 }, { silentToast: true })
    previewCandidates.value = r.items
    previewCandidateTotal.value = r.total
    const first = r.items[0]
    if (!previewArticleKey.value && first) {
      previewArticleKey.value = String(first.id)
      await loadPreview()
    }
  } catch (e) {
    previewError.value = errText(e, '候选文章加载失败')
  } finally {
    previewCandidatesLoading.value = false
  }
}

watch(activeTab, (tab) => {
  if (tab === 'preview') void ensurePreviewCandidates()
})

onMounted(async () => {
  await Promise.all([refreshSitemap(), loadScores(), refreshSearchStats()])
})
</script>
