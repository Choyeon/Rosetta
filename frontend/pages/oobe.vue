<!--
  安装向导：layout:false 自绘整屏，且 /oobe 命中 lib/rosetta-themes 的 THEME_VISUAL_EXCLUDE_PREFIXES → 永不注入主题皮肤。
  它仍是 SSR 页：routeRules 对 /oobe 只设 no-store（撤销 ssr:false 是让安装完成后的 SSR 级 302 不与客户端 navigateTo 抢跑成白屏），所以 location / new Image() / document 只能待在 onMounted 与回调里。
  数据层全走 composables/useOOBE.ts 的裸 fetch + EventSource（localStorage rosetta:oobe:apiBase 现场覆盖后端地址），刻意绕开 useApi：跳登录、统一 toast、CSR 缓存键在"后端地址未定"的时序里三者都错。
  Step1 的 canNext 硬门 = 探测成功且 apiBase 已应用（之后才自动 checkSystem）；Step2/3 在 nextStep 内即时 createAdmin / saveSiteSettings，回退再前进就是重复提交。
  收尾必须 clearOOBEApiBaseOverrideFromStorage() + resetOOBECache(true)，否则 middleware/oobe.global 的 60s 缓存仍把人锁回 /oobe；prod + 明文 HTTP 时 finishSetup 先弹 TLS 二次确认再安装。
  页面完整跟随全局明暗主题（<html>.dark 驱动 Tailwind dark: 变体与语义令牌，ThemeToggle 在
  OOBENavbar 中可用）：表面层一律「亮色值 + dark:暗色值」双轨书写，强调文字亮色取深色调、
  暗色取浅色调保证对比度；壁纸与三束色光叠层两种主题共用。仅渐变兜底/暗角/网格三个背景层
  因含照片级叠加无法用语义类表达，抽成 .oobe-bg-fallback / .oobe-vignette / .oobe-grid
  （页尾 style 块内亮暗各一套）。守卫见 tests/unit/oobeThemeScope.spec.ts。
-->
<template>
  <div class="oobe-root relative min-h-screen overflow-hidden text-foreground isolate">
    <!-- ========== 背景：Bing 每日壁纸 + 多层遮罩 ========== -->
    <div
      class="absolute inset-0 -z-20 bg-cover bg-center bg-no-repeat transition-opacity duration-700"
      :style="wallpaperLoaded ? { backgroundImage: `url(${bwp?.url})` } : {}"
    />
    <!-- 渐变兜底（Bing 壁纸未加载或失败时显示）：亮暗两套见页尾 style 块 -->
    <div class="oobe-bg-fallback absolute inset-0 -z-30" />
    <!-- 色光叠层：三束径向柔光，主色 emerald/teal/cyan（后台系统色调） -->
    <div class="pointer-events-none absolute inset-0 -z-10">
      <div class="absolute -top-40 -left-40 h-[42rem] w-[42rem] rounded-full bg-emerald-500/25 blur-[140px]" />
      <div class="absolute -bottom-40 -right-40 h-[42rem] w-[42rem] rounded-full bg-teal-500/25 blur-[140px]" />
      <div class="absolute top-1/2 left-1/2 h-[36rem] w-[36rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-cyan-500/15 blur-[140px]" />
    </div>
    <!-- 对比度增强：暗角 + 网格纸感（亮暗两套见页尾 style 块） -->
    <div class="oobe-vignette pointer-events-none absolute inset-0 -z-10" />
    <div class="oobe-grid pointer-events-none absolute inset-0 -z-10" />

    <!-- ========== 顶部 Navbar ========== -->
    <OOBENavbar class="sticky top-0 z-40 shrink-0" />

    <!-- ========== 主体：两栏 ========== -->
    <div class="relative z-10 min-h-[calc(100svh-57px)] grid lg:grid-cols-[300px_1fr] gap-0">
      <!-- 侧边栏：高模糊毛玻璃 -->
      <aside class="hidden lg:flex flex flex-col border-r border-zinc-900/10 dark:border-white/10 bg-white/65 dark:bg-white/[0.06] backdrop-blur-[28px] saturate-[200%] [@supports_not_(backdrop-filter)]:bg-white/90 dark:[@supports_not_(backdrop-filter)]:bg-zinc-900/95">
        <div class="p-8 flex flex-col gap-8 flex-1">
          <NuxtLink
            to="/"
            class="inline-flex items-center gap-2 font-display text-xl font-bold tracking-tight text-foreground"
          >
            <img
              src="/logo/rosetta-primary-icon.png"
              alt="Rosetta"
              class="size-7 object-contain drop-shadow-[0_0_12px_rgba(16,185,129,0.45)]"
            >
            <span>Rosetta</span>
          </NuxtLink>

          <div class="flex flex-col gap-2">
            <div
              v-for="(s, idx) in steps"
              :key="idx"
              class="flex items-center gap-3 p-3 rounded-xl transition-colors"
              :class="{
                'bg-emerald-500/15 text-emerald-800 dark:text-emerald-200 ring-1 ring-emerald-400/30': step === idx + 1,
                'text-foreground/85': step !== idx + 1
              }"
            >
              <div
                class="size-8 rounded-full flex items-center justify-center shrink-0 border text-sm font-semibold transition-colors"
                :class="{
                  'border-emerald-600/55 dark:border-emerald-400/60 bg-emerald-500 text-zinc-950': step > idx + 1,
                  'border-emerald-600/55 dark:border-emerald-400/60 bg-emerald-500/15 text-emerald-800 dark:text-emerald-200': step === idx + 1,
                  'border-zinc-900/10 dark:border-white/10 bg-zinc-900/5 dark:bg-white/5 text-foreground/70': step < idx + 1
                }"
              >
                <CheckCircle2
                  v-if="step > idx + 1"
                  class="size-4"
                />
                <span v-else>{{ idx + 1 }}</span>
              </div>
              <div class="flex-1 min-w-0">
                <div class="font-semibold text-sm">
                  {{ s.title }}
                </div>
                <div class="text-xs opacity-75 mt-0.5">
                  {{ s.desc }}
                </div>
              </div>
            </div>
          </div>

          <div class="mt-auto text-xs text-foreground/70 leading-relaxed">
            <p>{{ t('oobe.sidebarHint1') }}</p>
            <p class="mt-1">
              {{ t('oobe.sidebarHint2') }}
            </p>
          </div>
        </div>
      </aside>

      <!-- 内容区：居中大图卡 -->
      <div class="p-5 sm:p-8 lg:p-12 flex items-start justify-center overflow-auto">
        <!-- 毛玻璃 Card（32px 高模糊，外层渐变描边 + 深邃投影） -->
        <div class="relative w-full max-w-5xl">
          <div class="absolute -inset-px rounded-[28px] bg-[linear-gradient(135deg,rgba(16,185,129,0.45),rgba(14,165,233,0.28)_40%,rgba(56,189,248,0.15)_60%,rgba(20,184,166,0.45))] opacity-80 [mask:linear-gradient(#000_0_0)_content-box,linear-gradient(#000_0_0)] [mask-composite:exclude] pointer-events-none" />
          <div class="relative rounded-[28px] p-7 md:p-9 bg-white/70 dark:bg-white/[0.07] backdrop-blur-[32px] saturate-[200%] [@supports_not_(backdrop-filter)]:bg-white/90 dark:[@supports_not_(backdrop-filter)]:bg-zinc-900/95 border border-zinc-900/10 dark:border-white/10 shadow-[0_30px_80px_-20px_rgba(15,23,42,0.18)] dark:shadow-[0_30px_80px_-20px_rgba(0,0,0,0.65)]">
            <div class="pb-2">
              <div class="lg:hidden flex items-center gap-2 text-sm text-foreground/80 mb-4">
                <span>{{ t('oobe.step') }} {{ step }}/4</span>
              </div>
              <div class="font-display text-2xl md:text-3xl tracking-tight flex items-center gap-3 text-foreground">
                <div class="size-9 rounded-xl bg-gradient-to-br from-emerald-400/25 via-teal-400/25 to-cyan-400/25 ring-1 ring-zinc-900/10 dark:ring-white/10 flex items-center justify-center">
                  <component
                    :is="steps[step - 1]?.icon"
                    class="size-5 text-emerald-700 dark:text-emerald-300"
                  />
                </div>
                <span>{{ t('oobe.stepN', { n: step, total: 4 }) }}：{{ steps[step - 1]?.title }}</span>
              </div>
              <div class="mt-2 text-foreground/75">
                {{ steps[step - 1]?.longDesc }}
              </div>
            </div>

            <div class="pt-6">
              <!-- ============== Step 1: 系统环境 + 依赖安装 ============== -->
              <template v-if="step === 1">
                <div class="flex flex-col gap-5">
                  <!-- ============ 卡 1：后端连接配置（O 系列 Step1 顶卡） ============ -->
                  <div class="flex flex-col gap-4 p-5 rounded-2xl border border-zinc-900/10 dark:border-white/10 bg-zinc-900/[0.05] dark:bg-white/[0.05]">
                    <div class="flex items-center justify-between gap-3 flex-wrap">
                      <div class="flex items-center gap-3 min-w-0">
                        <div class="size-10 rounded-xl bg-gradient-to-br from-emerald-400/25 via-teal-400/25 to-cyan-400/25 ring-1 ring-zinc-900/10 dark:ring-white/10 flex items-center justify-center shrink-0">
                          <Server class="size-5 text-emerald-700 dark:text-emerald-300" />
                        </div>
                        <div class="min-w-0">
                          <div class="font-semibold text-foreground">
                            {{ t('oobe.connTitle') }}
                          </div>
                          <div class="text-xs text-foreground/70 mt-0.5">
                            {{ t('oobe.connDesc') }}
                          </div>
                        </div>
                      </div>
                      <Badge
                        variant="outline"
                        class="text-xs !border-zinc-900/15 dark:!border-white/15 text-foreground/85 shrink-0"
                      >
                        <component
                          :is="connMode === 'dev' ? Cpu : Cable"
                          data-icon="inline-start"
                          class="mr-1.5 inline-block align-middle -mt-0.5"
                        />
                        {{ connMode === 'dev' ? t('oobe.connModeDev') : t('oobe.connModeProd') }}
                      </Badge>
                    </div>
                    <p class="text-sm text-foreground/70 leading-relaxed">
                      {{ t('oobe.connLongDesc') }}
                    </p>

                    <!-- 模式 Switch：Dev <-> Prod（FieldSet + FieldLegend 满足 WCAG 可访问命名，避免两个 label 指向同一 Switch id） -->
                    <FieldSet class="!gap-2 p-3 rounded-xl border border-zinc-900/10 dark:border-white/10 bg-zinc-900/[0.03] dark:bg-white/[0.03]">
                      <FieldLegend
                        id="oobe-mode-legend"
                        class="!mb-1 !text-sm font-semibold text-foreground/90"
                      >
                        {{ t('oobe.connMode') }}
                      </FieldLegend>
                      <div class="flex items-center gap-3">
                        <div
                          class="font-semibold text-sm transition-colors select-none cursor-pointer"
                          :class="connMode === 'dev' ? 'text-emerald-800 dark:text-emerald-200' : 'text-foreground/70'"
                          @click="onConnModeChange('dev')"
                        >
                          {{ t('oobe.connModeDev') }}
                        </div>
                        <Separator
                          orientation="vertical"
                          class="h-3.5 bg-zinc-900/15 dark:bg-white/15"
                        />
                        <Switch
                          id="oobe-mode-switch"
                          :model-value="connMode === 'prod'"
                          :aria-labelledby="'oobe-mode-legend'"
                          @update:model-value="switchProdMode"
                        />
                        <Separator
                          orientation="vertical"
                          class="h-3.5 bg-zinc-900/15 dark:bg-white/15"
                        />
                        <div
                          class="font-semibold text-sm transition-colors select-none cursor-pointer"
                          :class="connMode === 'prod' ? 'text-emerald-800 dark:text-emerald-200' : 'text-foreground/70'"
                          @click="onConnModeChange('prod')"
                        >
                          {{ t('oobe.connModeProd') }}
                        </div>
                      </div>
                      <div class="text-xs text-foreground/65 pt-0.5">
                        {{ connMode === 'dev' ? t('oobe.connModeDevHint') : t('oobe.connModeProdHint') }}
                      </div>
                    </FieldSet>

                    <!-- 后端 API URL Input + 探测按钮 -->
                    <div class="grid grid-cols-1 gap-3">
                      <div class="flex items-end gap-3">
                        <div class="flex-1 min-w-0">
                          <Label
                            for="oobe-api-url"
                            class="text-xs text-foreground/80 mb-1.5 block"
                          >
                            {{ t('oobe.connApiUrl') }}
                          </Label>
                          <Input
                            id="oobe-api-url"
                            ref="apiUrlInputRef"
                            v-model="connApiUrl"
                            type="url"
                            inputmode="url"
                            spellcheck="false"
                            autocomplete="off"
                            :placeholder="connMode === 'dev' ? 'http://127.0.0.1:8000/api' : '/api'"
                            :aria-invalid="connApiUrlInvalid"
                            class="bg-zinc-900/[0.04] dark:bg-white/[0.04] !border-zinc-900/15 dark:!border-white/15 placeholder:text-foreground/40 text-foreground"
                            :class="connApiUrlInvalid ? '!border-rose-600/45 dark:!border-rose-400/40 focus-visible:!ring-rose-400/40' : ''"
                            @input="resetProbeStateOnEdit"
                            @keydown.enter.prevent="runProbeBackend"
                          />
                          <p
                            class="text-[11px] mt-1.5 leading-relaxed"
                            :class="connApiUrlInvalid ? 'text-rose-700 dark:text-rose-300' : 'text-foreground/60'"
                          >
                            {{ connApiUrlHintText }}
                          </p>
                        </div>
                        <div class="shrink-0 flex flex-col gap-2">
                          <Button
                            size="sm"
                            class="min-w-[9rem]"
                            :disabled="backendProbeRunning"
                            @click="runProbeBackend"
                          >
                            <Loader2
                              v-if="backendProbeRunning"
                              data-icon="inline-start"
                              class="animate-spin"
                            />
                            <component
                              :is="Wifi"
                              v-else-if="backendProbeResult.ok"
                              data-icon="inline-start"
                            />
                            <component
                              :is="WifiOff"
                              v-else
                              data-icon="inline-start"
                            />
                            {{ backendProbeRunning ? t('oobe.connProbing') : t('oobe.connProbe') }}
                          </Button>
                        </div>
                      </div>

                      <!-- 端口快选（仅 Dev 模式）：ToggleGroup + FieldSet/FieldLegend（shadcn forms 规范 + a11y） -->
                      <FieldSet
                        v-if="connMode === 'dev'"
                        class="!gap-2"
                      >
                        <FieldLegend
                          id="oobe-port-legend"
                          class="!mb-1 !text-[11px] uppercase tracking-wider text-foreground/65"
                        >
                          {{ t('oobe.connPortQuick') }}
                        </FieldLegend>
                        <div class="flex flex-wrap gap-2 items-center">
                          <ToggleGroup
                            type="single"
                            :value="connActivePort"
                            aria-labelledby="oobe-port-legend"
                            class="justify-start"
                            @update:model-value="(p) => applyQuickPort(String(p ?? ''))"
                          >
                            <ToggleGroupItem
                              v-for="p in quickPorts"
                              :key="p"
                              :value="p"
                              size="sm"
                              class="!border-zinc-900/15 dark:!border-white/15 aria-pressed:!bg-emerald-500/15 aria-pressed:!text-emerald-800 dark:aria-pressed:!text-emerald-200 aria-pressed:!border-emerald-600/40 dark:aria-pressed:!border-emerald-400/30"
                            >
                              :{{ p }}
                            </ToggleGroupItem>
                          </ToggleGroup>
                          <Button
                            variant="outline"
                            size="sm"
                            disabled
                            class="!border-dashed !border-zinc-900/15 dark:!border-white/15 text-foreground/65 hover:bg-zinc-900/10 dark:hover:bg-white/10 opacity-80"
                            @click="customPortNoop"
                          >
                            {{ t('oobe.connCustomPort') }}
                          </Button>
                        </div>
                      </FieldSet>

                      <!-- 当前生效地址 -->
                      <div
                        v-if="backendProbeApplied && effectiveApiBase"
                        class="flex items-start gap-2 p-3 rounded-xl border border-emerald-600/35 dark:border-emerald-400/25 bg-emerald-500/[0.06]"
                      >
                        <CheckCircle2 class="size-4 text-emerald-700 dark:text-emerald-300 mt-0.5 shrink-0" />
                        <div class="min-w-0">
                          <div class="text-[11px] uppercase tracking-wider text-emerald-800/85 dark:text-emerald-200/80">
                            {{ t('oobe.connCurrentHint') }} · {{ t('oobe.connAppliedHint') }}
                          </div>
                          <div
                            class="text-sm font-mono text-emerald-900 dark:text-emerald-100 truncate mt-0.5"
                            :title="String(effectiveApiBase)"
                          >
                            {{ effectiveApiBase }}
                          </div>
                        </div>
                      </div>

                      <!-- 探测结果 -->
                      <div
                        v-if="backendProbeResult.stage !== 'init'"
                        class="flex flex-col gap-2"
                      >
                        <div class="flex items-center gap-2 flex-wrap">
                          <Badge
                            :variant="backendProbeResult.ok ? 'default' : 'destructive'"
                            :class="backendProbeResult.ok ? 'bg-emerald-500/90 text-zinc-950 hover:bg-emerald-500/90' : ''"
                          >
                            <CheckCircle2
                              v-if="backendProbeResult.ok"
                              data-icon="inline-start"
                            />
                            <XCircle
                              v-else
                              data-icon="inline-start"
                            />
                            {{ backendProbeResult.ok ? t('oobe.connProbeOK') : t('oobe.connProbeFail') }}
                          </Badge>
                          <Badge
                            v-if="backendProbeResult.oobeRequired"
                            variant="outline"
                            class="!border-amber-600/40 dark:!border-amber-400/30 text-amber-800 dark:text-amber-200"
                          >
                            <AlertTriangle data-icon="inline-start" />
                            {{ t('oobe.connProbeOOBERequired') }}
                          </Badge>
                          <Badge
                            v-else-if="backendProbeResult.oobeComplete"
                            variant="outline"
                            class="!border-emerald-600/40 dark:!border-emerald-400/30 text-emerald-800 dark:text-emerald-200"
                          >
                            <CheckCircle2 data-icon="inline-start" />
                            {{ t('oobe.connProbeAlreadyDone') }}
                          </Badge>
                          <span class="text-xs text-foreground/60">
                            <span>{{ backendProbeResult.stage === 'health' ? t('oobe.connProbeStageHealth') : t('oobe.connProbeStageStatus') }}</span>
                            <span
                              v-if="backendProbeResult.code"
                              class="ml-1 font-mono"
                            >· HTTP {{ backendProbeResult.code }}</span>
                          </span>
                        </div>
                        <div
                          v-if="!backendProbeResult.ok && watchProbeFailText"
                          class="text-xs text-rose-200/90 leading-relaxed p-3 rounded-xl bg-rose-500/[0.08] border border-rose-600/30 dark:border-rose-400/20"
                        >
                          {{ watchProbeFailText }}
                        </div>
                        <div
                          v-if="!backendProbeResult.ok"
                          class="text-xs text-amber-800/90 dark:text-amber-200/85 flex items-center gap-1.5"
                        >
                          <AlertTriangle class="size-3.5 shrink-0" />
                          <span>{{ t('oobe.connProbeHintNext') }}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 环境摘要卡片 -->
                  <div
                    v-if="systemSummary && typeof systemSummary === 'object'"
                    class="grid grid-cols-2 md:grid-cols-4 gap-3 p-4 rounded-2xl bg-zinc-900/[0.05] dark:bg-white/[0.05] border border-zinc-900/10 dark:border-white/10"
                  >
                    <div>
                      <div class="text-[10px] uppercase tracking-wider text-foreground/65">
                        {{ t('oobe.envOS') }}
                      </div>
                      <div
                        class="text-sm font-medium mt-0.5 truncate text-foreground"
                        :title="`${systemSummary?.osName ?? ''} (${systemSummary?.osVersion ?? ''})`"
                      >
                        {{ systemSummary?.osName || '—' }}
                      </div>
                      <div class="text-[11px] text-foreground/65 mt-0.5 truncate">
                        {{ systemSummary?.architecture || '—' }} · {{ systemSummary?.hostname || '—' }}
                      </div>
                    </div>
                    <div>
                      <div class="text-[10px] uppercase tracking-wider text-foreground/65">
                        {{ t('oobe.envCPU') }}
                      </div>
                      <div class="text-sm font-medium mt-0.5 text-foreground">
                        {{ systemSummary?.cpuCount ?? '?' }} {{ t('oobe.envCores') }}
                      </div>
                      <div
                        class="text-[11px] text-foreground/65 mt-0.5 truncate"
                        :title="systemSummary?.processor || ''"
                      >
                        {{ systemSummary?.processor || '—' }}
                      </div>
                    </div>
                    <div>
                      <div class="text-[10px] uppercase tracking-wider text-foreground/65">
                        {{ t('oobe.envMemory') }}
                      </div>
                      <div class="text-sm font-medium mt-0.5 text-foreground">
                        {{ systemSummary?.totalMemoryGB || '—' }}
                      </div>
                      <div class="text-[11px] text-foreground/65 mt-0.5">
                        {{ t('oobe.envAvail') }}: {{ systemSummary?.availableMemoryGB || '—' }}
                      </div>
                    </div>
                    <div>
                      <div class="text-[10px] uppercase tracking-wider text-foreground/65">
                        {{ t('oobe.envDisk') }}
                      </div>
                      <div class="text-sm font-medium mt-0.5 text-foreground">
                        {{ systemSummary?.totalDiskGB || '—' }}
                      </div>
                      <div class="text-[11px] text-foreground/65 mt-0.5">
                        {{ t('oobe.envFree') }}: {{ systemSummary?.freeDiskGB || '—' }} · Py{{ systemSummary?.pythonVersion || '—' }}
                      </div>
                    </div>
                  </div>

                  <!-- 检测结果 -->
                  <div class="flex flex-col gap-3">
                    <div
                      v-for="check in systemChecks"
                      :key="check.name"
                      class="flex items-center justify-between p-4 rounded-2xl border border-zinc-900/10 dark:border-white/10 bg-zinc-900/[0.05] dark:bg-white/[0.05]"
                    >
                      <div class="flex items-center gap-3 min-w-0">
                        <div
                          class="size-9 rounded-xl flex items-center justify-center shrink-0"
                          :class="check.status === 'ok' ? 'bg-emerald-500/20 ring-1 ring-emerald-400/30' : check.status === 'warn' ? 'bg-amber-500/20 ring-1 ring-amber-400/30' : 'bg-rose-500/20 ring-1 ring-rose-400/30'"
                        >
                          <CheckCircle2
                            v-if="check.status === 'ok'"
                            class="size-4 text-emerald-700 dark:text-emerald-300"
                          />
                          <AlertTriangle
                            v-else-if="check.status === 'warn'"
                            class="size-4 text-amber-700 dark:text-amber-300"
                          />
                          <XCircle
                            v-else
                            class="size-4 text-rose-700 dark:text-rose-300"
                          />
                        </div>
                        <div class="min-w-0">
                          <div class="font-semibold text-sm text-foreground">
                            {{ check.name }}
                          </div>
                          <div class="text-xs text-foreground/70 truncate">
                            {{ check.detail }}
                          </div>
                        </div>
                      </div>
                      <Badge
                        :variant="check.status === 'ok' ? 'default' : check.status === 'warn' ? 'secondary' : 'destructive'"
                        class="shrink-0"
                        :class="check.status === 'ok' ? 'bg-emerald-500/90 hover:bg-emerald-500/90 text-zinc-950' : ''"
                      >
                        {{ check.statusText }}
                      </Badge>
                    </div>
                    <div
                      v-if="systemChecks.length === 0"
                      class="p-8 text-center text-sm text-foreground/70"
                    >
                      <img
                        src="/logo/rosetta-primary-icon.png"
                        alt=""
                        class="size-6 mx-auto mb-2 opacity-70"
                      >
                      {{ t('oobe.step1EmptyHint') }}
                    </div>
                  </div>

                  <!-- QW-C：系统检测控制条（重新检测按钮 + 显式 loading）— 专业 CMS 级可操作 -->
                  <div
                    class="flex items-center justify-between gap-3 flex-wrap p-4 rounded-2xl border border-zinc-900/10 dark:border-white/10 bg-zinc-900/[0.03] dark:bg-white/[0.03]"
                  >
                    <div class="text-xs text-foreground/70">
                      <span v-if="checking">{{ t('oobe.checking', { default: '正在分析系统环境…' }) }}</span>
                      <span v-else-if="systemChecks.length > 0">{{ t('oobe.checkedNitems', { n: systemChecks.length, default: `已完成 ${systemChecks.length} 项环境检查` }) }}</span>
                      <span v-else>{{ t('oobe.step1EmptyHint') }}</span>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                      <Button
                        size="sm"
                        variant="outline"
                        :disabled="checking || !backendProbeApplied"
                        @click="runCheckSystem"
                      >
                        <RefreshCw
                          :class="checking ? 'animate-spin' : ''"
                          data-icon="inline-start"
                        />
                        {{ checking ? t('oobe.checking', { default: '正在分析系统环境…' }) : t('oobe.runCheck', { default: '重新检测' }) }}
                      </Button>
                    </div>
                  </div>

                  <!-- 一键依赖安装 -->
                  <div class="flex flex-col gap-3 rounded-2xl border border-zinc-900/10 dark:border-white/10 bg-zinc-900/[0.05] dark:bg-white/[0.05] p-4">
                    <div class="flex items-center justify-between gap-3 flex-wrap">
                      <div class="flex items-center gap-3 min-w-0">
                        <div class="size-9 rounded-xl bg-emerald-500/15 ring-1 ring-emerald-400/25 flex items-center justify-center shrink-0">
                          <Wrench class="size-4 text-emerald-700 dark:text-emerald-300" />
                        </div>
                        <div class="min-w-0">
                          <div class="font-semibold text-sm text-foreground">
                            {{ t('oobe.depInstallTitle', '一键安装依赖') }}
                          </div>
                          <div class="text-xs text-foreground/70 truncate">
                            {{ t('oobe.depInstallDesc', '自动安装 uv / Node.js / pnpm 与项目依赖（uv sync + pnpm install）') }}
                          </div>
                        </div>
                      </div>
                      <div class="flex items-center gap-2 shrink-0">
                        <Badge
                          variant="outline"
                          class="text-xs border-zinc-900/15 dark:border-white/15 text-foreground/85"
                        >
                          {{ depInstalled ? t('oobe.depDone', '已完成') : installRunning ? `${installPercent}%` : t('oobe.depReady', '待安装') }}
                        </Badge>
                        <Button
                          size="sm"
                          :disabled="!!installRunning || checking"
                          @click="runInstallDependencies"
                        >
                          <Download
                            v-if="!installRunning"
                            data-icon="inline-start"
                            class="mr-2"
                          />
                          <Loader2
                            v-else
                            data-icon="inline-start"
                            class="mr-2 animate-spin"
                          />
                          {{ installRunning ? t('oobe.depInstalling', '安装中…') : t('oobe.depInstallBtn', '一键安装') }}
                        </Button>
                      </div>
                    </div>

                    <!-- 进度条 -->
                    <div
                      v-if="installRunning || depInstalled"
                      class="flex flex-col gap-1"
                    >
                      <div class="h-2 w-full rounded-full bg-zinc-900/10 dark:bg-white/10 overflow-hidden">
                        <div
                          class="h-full rounded-full bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400 transition-all duration-500"
                          :style="{ width: `${installPercent}%` }"
                        />
                      </div>
                      <div class="text-xs text-foreground/70 flex items-center gap-2">
                        <span>{{ installStatusText }}</span>
                        <span
                          v-if="installSummary.success !== undefined"
                          class="ml-auto"
                        >
                          {{ t('oobe.depSummary', { s: installSummary.success ?? 0, f: installSummary.failed ?? 0 }) }}
                        </span>
                      </div>
                    </div>

                    <!-- 日志终端 -->
                    <div
                      v-if="depLogLines.length || installRunning"
                      class="flex flex-col gap-2"
                    >
                      <div class="flex items-center justify-between">
                        <div class="text-xs font-semibold text-foreground/70 uppercase tracking-wider">
                          {{ t('oobe.logs', '安装日志') }}
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          class="h-7 px-2 text-xs text-foreground/80 hover:text-foreground hover:bg-zinc-900/10 dark:hover:bg-white/10"
                          @click="depLogLines = []"
                        >
                          {{ t('oobe.clearLogs', '清空') }}
                        </Button>
                      </div>
                      <div
                        ref="logBoxRef"
                        class="h-56 overflow-auto rounded-xl border border-zinc-900/10 dark:border-white/10 bg-zinc-950/70 backdrop-blur text-emerald-300/90 font-mono text-xs p-3 leading-relaxed whitespace-pre-wrap break-words select-all"
                      >
                        <template v-if="depLogLines.length === 0">
                          <span class="text-zinc-500">{{ t('oobe.logsEmpty', '（等待日志输出…）') }}</span>
                        </template>
                        <div
                          v-for="(ln, i) in depLogLines"
                          :key="i"
                          :class="ln.level === 'error' ? 'text-rose-600 dark:text-rose-400' : ln.level === 'success' ? 'text-emerald-600 dark:text-emerald-400' : ln.level === 'warn' ? 'text-amber-700 dark:text-amber-300' : ''"
                        >
                          <span class="text-zinc-500 mr-2 select-none">{{ ln.time }}</span>{{ ln.text }}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </template>

              <!-- ============== Step 2: 管理员账户 ============== -->
              <template v-else-if="step === 2">
                <div class="flex flex-col gap-4">
                  <div class="flex flex-col gap-2">
                    <Label
                      for="oobe-admin-name"
                      class="text-foreground/90"
                    >{{ t('oobe.adminName') }} *</Label>

                    <div class="relative">
                      <UserPlus class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-foreground/60" />
                      <Input
                        id="oobe-admin-name"
                        v-model="adminForm.name"
                        :placeholder="t('oobe.adminNamePlaceholder')"
                        class="pl-9 h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                      />
                    </div>

                    <p class="text-sm text-foreground/70">
                      {{ t('oobe.adminNameDesc') }}
                    </p>

                    <!-- 用户名校验反馈：本地格式校验 + 远程 check-username（debounce 500ms）。
                         后端不可达时静默降级为「未校验」，不阻断（安装时仍有服务端校验兜底）。 -->
                    <p
                      v-if="usernameCheckState === 'checking'"
                      class="flex items-center gap-1.5 text-xs text-foreground/65"
                      aria-live="polite"
                    >
                      <Loader2 class="size-3 animate-spin" />
                      {{ usernameCheckMessage }}
                    </p>
                    <p
                      v-else-if="usernameCheckState === 'ok'"
                      class="flex items-center gap-1.5 text-xs text-emerald-700 dark:text-emerald-300"
                      aria-live="polite"
                    >
                      <CheckCircle2 class="size-3" />
                      {{ usernameCheckMessage }}
                    </p>
                    <p
                      v-else-if="adminFieldErrors.name || usernameCheckState === 'invalid'"
                      class="flex items-center gap-1.5 text-xs text-rose-700 dark:text-rose-300"
                      role="alert"
                    >
                      <XCircle class="size-3" />
                      {{ adminFieldErrors.name || usernameCheckMessage }}
                    </p>
                  </div>

                  <div class="flex flex-col gap-2">
                    <Label
                      for="oobe-admin-email"
                      class="text-foreground/90"
                    >{{ t('oobe.adminEmail') }} *</Label>

                    <div class="relative">
                      <Mail class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-foreground/60" />
                      <Input
                        id="oobe-admin-email"
                        v-model="adminForm.email"
                        type="email"
                        :placeholder="t('oobe.adminEmailPlaceholder')"
                        class="pl-9 h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                      />
                    </div>

                    <p
                      v-if="adminFieldErrors.email"
                      class="flex items-center gap-1.5 text-xs text-rose-700 dark:text-rose-300"
                      role="alert"
                    >
                      <XCircle class="size-3" />
                      {{ adminFieldErrors.email }}
                    </p>
                  </div>

                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div class="flex flex-col gap-2">
                      <Label
                        for="oobe-admin-password"
                        class="text-foreground/90"
                      >{{ t('oobe.adminPassword') }} * <span class="text-xs text-foreground/65">({{ t('oobe.adminPasswordHint') }})</span></Label>

                      <div class="relative">
                        <ShieldCheck class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-foreground/60" />
                        <Input
                          id="oobe-admin-password"
                          v-model="adminForm.password"
                          :type="showAdminPassword ? 'text' : 'password'"
                          :placeholder="t('oobe.adminPasswordPlaceholder')"
                          class="pl-9 pr-9 h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                        />
                        <button
                          type="button"
                          class="absolute right-3 top-1/2 -translate-y-1/2 text-foreground/60 hover:text-foreground transition-colors"
                          tabindex="-1"
                          @click="showAdminPassword = !showAdminPassword"
                        >
                          <Eye
                            v-if="!showAdminPassword"
                            class="size-4"
                          />
                          <EyeOff
                            v-else
                            class="size-4"
                          />
                        </button>
                      </div>

                      <!-- 密码强度：只做可视化提示，权威判定在 POST /oobe/preflight -->
                      <div
                        v-if="adminForm.password"
                        class="flex flex-col gap-1.5"
                      >
                        <div class="flex items-center gap-2">
                          <div class="h-1.5 flex-1 rounded-full bg-zinc-900/10 dark:bg-white/10 overflow-hidden">
                            <div
                              class="h-full rounded-full transition-all duration-300"
                              :class="strengthBarClass"
                              :style="{ width: `${strengthPercent}%` }"
                            />
                          </div>
                          <span
                            class="text-xs font-medium w-8 text-right"
                            :class="strengthTextClass"
                          >{{ strengthLabel }}</span>
                        </div>
                        <div class="flex flex-wrap gap-x-3 gap-y-1">
                          <span
                            v-for="rule in passwordStrength.rules"
                            :key="rule.id"
                            class="inline-flex items-center gap-1 text-[11px]"
                            :class="rule.passed ? 'text-emerald-700/90 dark:text-emerald-300/90' : 'text-foreground/55'"
                          >
                            <CheckCircle2
                              v-if="rule.passed"
                              class="size-3"
                            />
                            <XCircle
                              v-else
                              class="size-3"
                            />
                            {{ passwordRuleLabel(rule.id) }}
                          </span>
                        </div>
                      </div>

                      <p
                        v-if="adminFieldErrors.password"
                        class="flex items-center gap-1.5 text-xs text-rose-700 dark:text-rose-300"
                        role="alert"
                      >
                        <XCircle class="size-3" />
                        {{ adminFieldErrors.password }}
                      </p>
                    </div>

                    <div class="flex flex-col gap-2">
                      <Label
                        for="oobe-admin-confirm-password"
                        class="text-foreground/90"
                      >{{ t('oobe.adminConfirmPassword') }} *</Label>

                      <div class="relative">
                        <CheckCircle2 class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-foreground/60" />
                        <Input
                          id="oobe-admin-confirm-password"
                          v-model="adminForm.confirmPassword"
                          :type="showAdminConfirmPassword ? 'text' : 'password'"
                          :placeholder="t('oobe.adminConfirmPasswordPlaceholder')"
                          class="pl-9 pr-9 h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                        />
                        <button
                          type="button"
                          class="absolute right-3 top-1/2 -translate-y-1/2 text-foreground/60 hover:text-foreground transition-colors"
                          tabindex="-1"
                          @click="showAdminConfirmPassword = !showAdminConfirmPassword"
                        >
                          <Eye
                            v-if="!showAdminConfirmPassword"
                            class="size-4"
                          />
                          <EyeOff
                            v-else
                            class="size-4"
                          />
                        </button>
                      </div>

                      <p
                        v-if="adminFieldErrors.confirmPassword"
                        class="flex items-center gap-1.5 text-xs text-rose-700 dark:text-rose-300"
                        role="alert"
                      >
                        <XCircle class="size-3" />
                        {{ adminFieldErrors.confirmPassword }}
                      </p>
                    </div>
                  </div>

                  <!-- 分步提交失败的可见反馈（以前只进 console，用户点了没反应） -->
                  <p
                    v-if="stepError && step === 2"
                    class="flex items-start gap-2 text-xs text-rose-700 dark:text-rose-300"
                    role="alert"
                  >
                    <XCircle class="size-3.5 shrink-0 mt-0.5" />
                    {{ stepError }}
                  </p>
                </div>
              </template>

              <!-- ============== Step 3: 站点 + 数据库 + 特性开关 ============== -->
              <template v-else-if="step === 3">
                <div class="flex flex-col gap-6">
                  <!-- 站点信息 -->
                  <div class="flex flex-col gap-4">
                    <div class="flex items-center gap-2 text-sm font-semibold text-foreground">
                      <Globe2 class="size-4 text-emerald-700 dark:text-emerald-300" />
                      <span>{{ t('oobe.groupSite', '站点信息') }}</span>
                    </div>

                    <div class="flex flex-col gap-2">
                      <Label
                        for="oobe-site-name"
                        class="text-foreground/90"
                      >{{ t('oobe.siteName') }} *</Label>

                      <div class="relative">
                        <Globe2 class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-foreground/60" />
                        <Input
                          id="oobe-site-name"
                          v-model="siteForm.name"
                          :placeholder="t('oobe.siteNamePlaceholder')"
                          class="pl-9 h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                        />
                      </div>
                    </div>

                    <div class="flex flex-col gap-2">
                      <Label
                        for="oobe-site-url"
                        class="text-foreground/90"
                      >{{ t('oobe.siteUrl') }} *</Label>

                      <div class="relative">
                        <LinkIcon class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-foreground/60" />
                        <Input
                          id="oobe-site-url"
                          v-model="siteForm.siteUrl"
                          type="url"
                          :placeholder="t('oobe.siteUrlPlaceholder')"
                          class="pl-9 h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                        />
                      </div>

                      <p class="text-sm text-foreground/70">
                        {{ t('oobe.siteUrlDesc') }}
                      </p>
                    </div>

                    <div class="flex flex-col gap-2">
                      <Label
                        for="oobe-site-description"
                        class="text-foreground/90"
                      >{{ t('oobe.siteDescription') }}</Label>

                      <Textarea
                        id="oobe-site-description"
                        v-model="siteForm.description"
                        :placeholder="t('oobe.siteDescriptionPlaceholder')"
                        rows="3"
                        class="resize-none !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                      />
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div class="flex flex-col gap-2">
                        <Label
                          for="oobe-default-language"
                          class="text-foreground/90"
                        >{{ t('oobe.defaultLanguage') }}</Label>
                        <Select v-model="siteForm.locale">
                          <SelectTrigger
                            id="oobe-default-language"
                            class="h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 text-foreground focus:!ring-emerald-400/40"
                          >
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent class="!bg-white/95 dark:!bg-zinc-900/95 backdrop-blur-xl !border-zinc-900/10 dark:!border-white/10">
                            <SelectItem value="zh">
                              简体中文
                            </SelectItem>
                            <SelectItem value="en">
                              English
                            </SelectItem>
                            <SelectItem value="ja">
                              日本語
                            </SelectItem>
                            <SelectItem value="zh_Hant">
                              繁體中文
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div class="flex flex-col gap-2">
                        <Label
                          for="oobe-seo-keywords"
                          class="text-foreground/90"
                        >{{ t('oobe.seoKeywords') }}</Label>

                        <div class="relative">
                          <Tag class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-foreground/60" />
                          <Input
                            id="oobe-seo-keywords"
                            v-model="siteForm.keywords"
                            :placeholder="t('oobe.seoKeywordsPlaceholder')"
                            class="pl-9 h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 环境与数据库 -->
                  <Separator class="my-1 !bg-zinc-900/10 dark:!bg-white/10" />
                  <div class="flex flex-col gap-4">
                    <div class="flex items-center justify-between gap-3 flex-wrap">
                      <div class="flex items-center gap-2 text-sm font-semibold text-foreground">
                        <Database class="size-4 text-emerald-700 dark:text-emerald-300" />
                        <span>{{ t('oobe.groupEnv', '运行环境与数据库') }}</span>
                      </div>
                      <div class="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          class="text-xs border-zinc-900/15 dark:border-white/15 text-foreground/85"
                        >
                          {{ siteForm.environment === 'production' ? t('oobe.envProd', '生产') : t('oobe.envDev', '开发') }}
                        </Badge>
                        <Switch
                          v-model="isProductionEnv"
                        />
                      </div>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div class="flex flex-col gap-2">
                        <Label
                          for="oobe-db-type"
                          class="text-foreground/90"
                        >{{ t('oobe.dbType', '数据库类型') }}</Label>
                        <Select v-model="siteForm.databaseType">
                          <SelectTrigger
                            id="oobe-db-type"
                            class="h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 text-foreground focus:!ring-emerald-400/40"
                          >
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent class="!bg-white/95 dark:!bg-zinc-900/95 backdrop-blur-xl !border-zinc-900/10 dark:!border-white/10">
                            <SelectItem value="sqlite">
                              SQLite {{ t('oobe.dbNoInstall', '（无需安装）') }}
                            </SelectItem>
                            <SelectItem value="postgresql">
                              PostgreSQL {{ t('oobe.dbNeedInstall', '（需单独安装）') }}
                            </SelectItem>
                          </SelectContent>
                        </Select>
                        <p
                          v-if="siteForm.databaseType === 'sqlite'"
                          class="text-sm text-foreground/70"
                        >
                          {{ t('oobe.sqliteHint', '适合单机/演示，零配置即用') }}
                        </p>
                        <p
                          v-else
                          class="text-sm text-foreground/70"
                        >
                          {{ t('oobe.pgHint', '推荐生产环境使用，需填写下方连接信息') }}
                        </p>
                      </div>
                      <div class="flex flex-col gap-2">
                        <Label
                          for="oobe-redis-enabled"
                          class="text-foreground/90"
                        >{{ t('oobe.redis', 'Redis 缓存') }}</Label>
                        <div class="flex items-center h-11 px-3 rounded-xl border border-zinc-900/10 dark:border-white/10 bg-zinc-900/[0.05] dark:bg-white/[0.05] justify-between">
                          <span class="text-sm text-foreground/75">{{ siteForm.redisEnabled ? t('oobe.on', '开启') : t('oobe.off', '关闭') }}</span>
                          <Switch
                            id="oobe-redis-enabled"
                            v-model="siteForm.redisEnabled"
                          />
                        </div>
                      </div>
                    </div>

                    <template v-if="siteForm.databaseType === 'postgresql'">
                      <div class="grid grid-cols-2 gap-4">
                        <div class="flex flex-col gap-2">
                          <Label
                            for="oobe-db-host"
                            class="text-foreground/90"
                          >{{ t('oobe.dbHost', '主机') }}</Label>

                          <Input
                            id="oobe-db-host"
                            v-model="siteForm.dbHost"
                            class="h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="localhost"
                          />
                        </div>
                        <div class="flex flex-col gap-2">
                          <Label
                            for="oobe-db-port"
                            class="text-foreground/90"
                          >{{ t('oobe.dbPort', '端口') }}</Label>

                          <Input
                            id="oobe-db-port"
                            v-model.number="siteForm.dbPort"
                            type="number"
                            class="h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="5432"
                          />
                        </div>
                        <div class="flex flex-col gap-2">
                          <Label
                            for="oobe-db-name"
                            class="text-foreground/90"
                          >{{ t('oobe.dbName', '数据库名') }}</Label>

                          <Input
                            id="oobe-db-name"
                            v-model="siteForm.dbName"
                            class="h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="rosetta"
                          />
                        </div>
                        <div class="flex flex-col gap-2">
                          <Label
                            for="oobe-db-user"
                            class="text-foreground/90"
                          >{{ t('oobe.dbUser', '用户名') }}</Label>

                          <Input
                            id="oobe-db-user"
                            v-model="siteForm.dbUser"
                            class="h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="postgres"
                          />
                        </div>
                        <div class="flex flex-col gap-2 col-span-2">
                          <Label
                            for="oobe-db-password"
                            class="text-foreground/90"
                          >{{ t('oobe.dbPassword', '密码') }}</Label>

                          <Input
                            id="oobe-db-password"
                            v-model="siteForm.dbPassword"
                            type="password"
                            class="h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                          />
                        </div>
                      </div>

                      <!-- 连接体检：POST /oobe/test-database（密码走请求体，不进 query string / 访问日志） -->
                      <div class="flex flex-col gap-2">
                        <div class="flex items-center justify-between gap-3">
                          <span class="text-xs text-foreground/65">
                            {{ dbTestDirty ? t('oobe.dbTestStale', '连接参数已修改，请重新测试') : t('oobe.dbTestHint', '安装前建议先测试连接，避免装到一半才报错') }}
                          </span>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            class="shrink-0 !border-zinc-900/15 dark:!border-white/15 bg-zinc-900/[0.04] dark:bg-white/[0.04] text-foreground hover:bg-zinc-900/10 dark:hover:bg-white/10"
                            :disabled="dbTest.status === 'testing'"
                            @click="runDbTest"
                          >
                            <Loader2
                              v-if="dbTest.status === 'testing'"
                              data-icon="inline-start"
                              class="animate-spin"
                            />
                            <Cable
                              v-else
                              data-icon="inline-start"
                            />
                            {{ dbTest.status === 'testing' ? t('oobe.dbTesting', '正在连接数据库…') : t('oobe.dbTestBtn', '测试连接') }}
                          </Button>
                        </div>

                        <div
                          v-if="dbTest.status === 'ok' || dbTest.status === 'error'"
                          class="flex items-start gap-2.5 p-3 rounded-xl border"
                          :class="dbTest.status === 'ok'
                            ? 'border-emerald-400/35 bg-emerald-500/[0.07]'
                            : 'border-rose-400/35 bg-rose-500/[0.07]'"
                          role="status"
                          aria-live="polite"
                        >
                          <CheckCircle2
                            v-if="dbTest.status === 'ok'"
                            class="size-4 shrink-0 mt-0.5 text-emerald-700 dark:text-emerald-300"
                          />
                          <XCircle
                            v-else
                            class="size-4 shrink-0 mt-0.5 text-rose-700 dark:text-rose-300"
                          />
                          <div class="flex-1 min-w-0 space-y-1">
                            <div
                              class="text-sm font-medium"
                              :class="dbTest.status === 'ok' ? 'text-emerald-800 dark:text-emerald-200' : 'text-rose-800 dark:text-rose-200'"
                            >
                              {{ dbTest.message }}
                            </div>
                            <div
                              v-if="dbTest.hint"
                              class="text-xs text-foreground/70 leading-relaxed whitespace-pre-line"
                            >
                              {{ dbTest.hint }}
                            </div>
                            <div
                              v-if="dbTest.code && dbTest.code !== 'DB_OK'"
                              class="text-[11px] font-mono text-foreground/50"
                            >
                              {{ dbTest.code }}
                            </div>
                          </div>
                        </div>
                      </div>
                    </template>
                    <template v-else>
                      <div class="flex flex-col gap-2">
                        <Label
                          for="oobe-db-path"
                          class="text-foreground/90"
                        >{{ t('oobe.dbPath', 'SQLite 文件路径') }}</Label>

                        <Input
                          id="oobe-db-path"
                          v-model="siteForm.dbPath"
                          class="h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                          placeholder="rosetta.db"
                        />
                      </div>
                    </template>

                    <template v-if="siteForm.redisEnabled">
                      <div class="grid grid-cols-3 gap-4">
                        <div class="flex flex-col gap-2">
                          <Label
                            for="oobe-redis-host"
                            class="text-foreground/90"
                          >{{ t('oobe.redisHost', 'Redis 主机') }}</Label>

                          <Input
                            id="oobe-redis-host"
                            v-model="siteForm.redisHost"
                            class="h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="localhost"
                          />
                        </div>
                        <div class="flex flex-col gap-2">
                          <Label
                            for="oobe-redis-port"
                            class="text-foreground/90"
                          >{{ t('oobe.redisPort', '端口') }}</Label>

                          <Input
                            id="oobe-redis-port"
                            v-model.number="siteForm.redisPort"
                            type="number"
                            class="h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="6379"
                          />
                        </div>
                        <div class="flex flex-col gap-2">
                          <Label
                            for="oobe-redis-password"
                            class="text-foreground/90"
                          >{{ t('oobe.redisPassword', '密码') }}</Label>

                          <Input
                            id="oobe-redis-password"
                            v-model="siteForm.redisPassword"
                            type="password"
                            class="h-11 !bg-zinc-900/[0.05] dark:!bg-white/[0.05] !border-zinc-900/10 dark:!border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                          />
                        </div>
                      </div>
                    </template>
                  </div>

                  <!-- 特性开关 -->
                  <Separator class="my-1 !bg-zinc-900/10 dark:!bg-white/10" />
                  <div class="flex flex-col gap-4">
                    <div class="flex items-center gap-2 text-sm font-semibold text-foreground">
                      <Sparkles class="size-4 text-emerald-700 dark:text-emerald-300" />
                      <span>{{ t('oobe.groupFeatures', '功能开关') }}</span>
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <label class="flex items-center justify-between p-3 rounded-xl border border-zinc-900/10 dark:border-white/10 bg-zinc-900/[0.05] dark:bg-white/[0.05] cursor-pointer hover:bg-zinc-900/[0.08] dark:hover:bg-white/[0.08] transition-colors text-foreground">
                        <div>
                          <div class="text-sm font-medium">{{ t('oobe.fComments', '评论') }}</div>
                          <div class="text-xs text-foreground/70">{{ t('oobe.fCommentsDesc', '允许访客在文章下留言') }}</div>
                        </div>
                        <Switch v-model="siteForm.enableComments" />
                      </label>
                      <label class="flex items-center justify-between p-3 rounded-xl border border-zinc-900/10 dark:border-white/10 bg-zinc-900/[0.05] dark:bg-white/[0.05] cursor-pointer hover:bg-zinc-900/[0.08] dark:hover:bg-white/[0.08] transition-colors text-foreground">
                        <div>
                          <div class="text-sm font-medium">{{ t('oobe.fRegister', '开放注册') }}</div>
                          <div class="text-xs text-foreground/70">{{ t('oobe.fRegisterDesc', '允许新用户自助注册（默认关）') }}</div>
                        </div>
                        <Switch v-model="siteForm.enableRegistration" />
                      </label>
                      <label class="flex items-center justify-between p-3 rounded-xl border border-zinc-900/10 dark:border-white/10 bg-zinc-900/[0.05] dark:bg-white/[0.05] cursor-pointer hover:bg-zinc-900/[0.08] dark:hover:bg-white/[0.08] transition-colors text-foreground">
                        <div>
                          <div class="text-sm font-medium">{{ t('oobe.fRss', 'RSS 订阅') }}</div>
                          <div class="text-xs text-foreground/70">{{ t('oobe.fRssDesc', '生成 /feed.xml 订阅源') }}</div>
                        </div>
                        <Switch v-model="siteForm.enableRss" />
                      </label>
                      <label class="flex items-center justify-between p-3 rounded-xl border border-zinc-900/10 dark:border-white/10 bg-zinc-900/[0.05] dark:bg-white/[0.05] cursor-pointer hover:bg-zinc-900/[0.08] dark:hover:bg-white/[0.08] transition-colors text-foreground">
                        <div>
                          <div class="text-sm font-medium">{{ t('oobe.fBing', 'Bing 每日壁纸') }}</div>
                          <div class="text-xs text-foreground/70">{{ t('oobe.fBingDesc', '首页展示 Bing 每日壁纸背景') }}</div>
                        </div>
                        <Switch v-model="siteForm.enableBingWallpaper" />
                      </label>
                      <label class="flex items-center justify-between p-3 rounded-xl border border-zinc-900/10 dark:border-white/10 bg-zinc-900/[0.05] dark:bg-white/[0.05] cursor-pointer hover:bg-zinc-900/[0.08] dark:hover:bg-white/[0.08] transition-colors text-foreground">
                        <div>
                          <div class="text-sm font-medium">{{ t('oobe.fPagefind', '站内搜索') }}</div>
                          <div class="text-xs text-foreground/70">{{ t('oobe.fPagefindDesc', '启用 Pagefind 客户端全文搜索') }}</div>
                        </div>
                        <Switch v-model="siteForm.enablePagefindSearch" />
                      </label>
                      <label class="flex items-center justify-between p-3 rounded-xl border border-zinc-900/10 dark:border-white/10 bg-zinc-900/[0.05] dark:bg-white/[0.05] cursor-pointer hover:bg-zinc-900/[0.08] dark:hover:bg-white/[0.08] transition-colors text-foreground">
                        <div>
                          <div class="text-sm font-medium">{{ t('oobe.fCrypto', '加密文章') }}</div>
                          <div class="text-xs text-foreground/70">{{ t('oobe.fCryptoDesc', '发布受密码保护的加密文章') }}</div>
                        </div>
                        <Switch v-model="siteForm.enableEncryptedPosts" />
                      </label>
                      <label class="flex items-center justify-between p-3 rounded-xl border border-zinc-900/10 dark:border-white/10 bg-zinc-900/[0.05] dark:bg-white/[0.05] cursor-pointer hover:bg-zinc-900/[0.08] dark:hover:bg-white/[0.08] transition-colors sm:col-span-2 text-foreground">
                        <div>
                          <div class="text-sm font-medium">{{ t('oobe.fMusic', '背景音乐播放器') }}</div>
                          <div class="text-xs text-foreground/70">{{ t('oobe.fMusicDesc', '侧边栏显示音乐播放组件（需在后台配置播放源）') }}</div>
                        </div>
                        <Switch v-model="siteForm.enableMusicPlayer" />
                      </label>
                    </div>
                  </div>

                  <!-- 服务端预检结果（POST /oobe/preflight 只读干跑，error 阻断安装） -->
                  <div
                    v-if="preflightState.done && (preflightErrors.length || preflightWarns.length)"
                    class="flex flex-col gap-2"
                  >
                    <div
                      v-for="issue in preflightErrors"
                      :key="`e-${issue.field}-${issue.code}`"
                      class="flex items-start gap-2.5 p-3 rounded-xl border border-rose-400/35 bg-rose-500/[0.07]"
                      role="alert"
                    >
                      <XCircle class="size-4 shrink-0 mt-0.5 text-rose-700 dark:text-rose-300" />
                      <div class="flex-1 min-w-0 space-y-1">
                        <div class="text-sm font-medium text-rose-800 dark:text-rose-200">
                          {{ issue.message }}
                        </div>
                        <div
                          v-if="issue.hint"
                          class="text-xs text-foreground/70 leading-relaxed whitespace-pre-line"
                        >
                          {{ issue.hint }}
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        class="shrink-0 h-7 px-2 text-xs"
                        @click="goFixIssue(issue.field)"
                      >
                        {{ t('oobe.preflightGoFix', '去修改') }}
                      </Button>
                    </div>
                    <div
                      v-for="issue in preflightWarns"
                      :key="`w-${issue.field}-${issue.code}`"
                      class="flex items-start gap-2.5 p-3 rounded-xl border border-amber-400/35 bg-amber-500/[0.07]"
                      role="status"
                    >
                      <AlertTriangle class="size-4 shrink-0 mt-0.5 text-amber-700 dark:text-amber-300" />
                      <div class="flex-1 min-w-0 space-y-1">
                        <div class="text-sm font-medium text-amber-800 dark:text-amber-200">
                          {{ issue.message }}
                        </div>
                        <div
                          v-if="issue.hint"
                          class="text-xs text-foreground/70 leading-relaxed whitespace-pre-line"
                        >
                          {{ issue.hint }}
                        </div>
                      </div>
                    </div>
                  </div>

                  <p
                    v-if="stepError && step === 3"
                    class="flex items-start gap-2 text-xs text-rose-700 dark:text-rose-300"
                    role="alert"
                  >
                    <XCircle class="size-3.5 shrink-0 mt-0.5" />
                    {{ stepError }}
                  </p>
                </div>
              </template>

              <!-- ============== Step 4: 安装进度 + 完成 ============== -->
              <template v-else-if="step === 4">
                <!-- 安装中：进度展示 -->
                <div
                  v-if="installing"
                  class="flex flex-col gap-5 py-2"
                >
                  <div class="text-center">
                    <div class="inline-flex items-center justify-center size-20 rounded-full bg-emerald-500/15 ring-1 ring-emerald-400/30 mb-6">
                      <Loader2 class="size-10 text-emerald-700 dark:text-emerald-300 animate-spin" />
                    </div>
                    <h3 class="font-display text-2xl font-bold tracking-tight mb-2 text-foreground">
                      {{ t('oobe.installing', '正在配置您的站点…') }}
                    </h3>
                    <p class="text-foreground/75 max-w-md mx-auto leading-relaxed">
                      {{ installStepMessage || t('oobe.installingDesc', '数据库初始化、写入配置、创建示例数据，请稍候。') }}
                    </p>
                  </div>

                  <div class="flex flex-col gap-2">
                    <div class="flex items-center justify-between text-xs text-foreground/70">
                      <span>{{ t('oobe.totalProgress', '总体进度') }}</span>
                      <span>{{ installPercent }}%</span>
                    </div>
                    <div class="h-2.5 w-full rounded-full bg-zinc-900/10 dark:bg-white/10 overflow-hidden">
                      <div
                        class="h-full rounded-full bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400 transition-all duration-500 relative"
                        :style="{ width: `${installPercent}%` }"
                      >
                        <div class="absolute inset-0 bg-[linear-gradient(45deg,rgba(255,255,255,0.15)_25%,transparent_25%,transparent_50%,rgba(255,255,255,0.15)_50%,rgba(255,255,255,0.15)_75%,transparent_75%)] bg-[length:20px_20px] animate-progress-stripe" />
                      </div>
                    </div>
                  </div>

                  <!-- 8 步步骤列表 -->
                  <div class="flex flex-col gap-2">
                    <div
                      v-for="(st, idx) in installStepList"
                      :key="st.id"
                      class="flex items-center gap-3 p-3 rounded-xl border"
                      :class="{
                        'bg-emerald-500/10 border-emerald-400/40': installStepIndex === idx,
                        'bg-emerald-500/5 border-emerald-600/40 dark:border-emerald-400/30': st.done,
                        'border-zinc-900/10 dark:border-white/10 bg-zinc-900/[0.05] dark:bg-white/[0.05]': !st.done && installStepIndex !== idx
                      }"
                    >
                      <div
                        class="size-7 rounded-full flex items-center justify-center shrink-0 text-xs font-semibold transition-colors"
                        :class="{
                          'bg-emerald-500 text-zinc-950': st.done,
                          'bg-emerald-500/15 text-emerald-800 dark:text-emerald-200 animate-pulse ring-1 ring-emerald-400/40': installStepIndex === idx && !st.done,
                          'bg-zinc-900/10 dark:bg-white/10 text-foreground/70': installStepIndex !== idx && !st.done
                        }"
                      >
                        <CheckCircle2
                          v-if="st.done"
                          class="size-3.5"
                        />
                        <Loader2
                          v-else-if="installStepIndex === idx"
                          class="size-3.5 animate-spin"
                        />
                        <span v-else>{{ idx + 1 }}</span>
                      </div>
                      <div class="flex-1 min-w-0">
                        <div
                          class="text-sm font-medium"
                          :class="installStepIndex === idx ? 'text-emerald-800 dark:text-emerald-200' : st.done ? 'text-foreground' : 'text-foreground/75'"
                        >
                          {{ st.label }}
                        </div>
                        <div
                          v-if="installStepIndex === idx && installStepMessage"
                          class="text-xs text-foreground/70 truncate mt-0.5"
                        >
                          {{ installStepMessage }}
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- SSE 快照兜底 banner：timeout / polling / retrying -->
                  <div
                    v-if="installSnapshotState === 'timeout' || installSnapshotState === 'polling' || installSnapshotState === 'retrying'"
                    class="flex items-start gap-3 p-3 rounded-xl border"
                    :class="installSnapshotState === 'timeout'
                      ? 'border-amber-400/35 bg-amber-500/[0.07]'
                      : 'border-sky-600/40 bg-sky-500/[0.06] dark:border-sky-400/30'"
                    role="status"
                    aria-live="polite"
                  >
                    <AlertTriangle
                      data-icon="inline-start"
                      class="size-4 shrink-0 mt-0.5"
                      :class="installSnapshotState === 'timeout' ? 'text-amber-700 dark:text-amber-300' : 'text-sky-700 dark:text-sky-300'"
                    />
                    <div class="flex-1 min-w-0 space-y-1">
                      <div class="text-sm font-medium text-foreground">
                        {{ installSnapshotState === 'timeout' ? t('oobe.installSnapshotTimeout') : t('oobe.installSnapshotPolling') }}
                      </div>
                      <div class="text-xs text-foreground/70 leading-relaxed whitespace-pre-line">
                        {{ installSnapshotState === 'timeout' ? t('oobe.installSnapshotTimeoutDetail') : t('oobe.installSnapshotPollingDetail') }}
                      </div>
                    </div>
                  </div>

                  <!-- 安装中：Cancel/Retry 行（解决 SSE 假死死穴） -->
                  <div class="flex flex-wrap items-center justify-end gap-2 pt-1">
                    <Button
                      variant="outline"
                      size="sm"
                      :disabled="!installing"
                      @click="runInstallCancel"
                    >
                      <XCircle data-icon="inline-start" />
                      {{ t('oobe.installSnapshotCancelBtn') }}
                    </Button>
                    <Button
                      size="sm"
                      :disabled="installing || installSnapshotState === 'timeout'"
                      @click="runInstallRetry"
                    >
                      <RefreshCw
                        data-icon="inline-start"
                        :class="{ 'animate-spin': installing }"
                      />
                      {{ t('oobe.installSnapshotRetryBtn') }}
                    </Button>
                  </div>
                </div>

                <!-- 安装完成 -->
                <div
                  v-else-if="installed"
                  class="text-center py-6 animate-in fade-in"
                >
                  <div class="inline-flex items-center justify-center size-20 rounded-full bg-emerald-500/15 ring-1 ring-emerald-400/30 mb-6">
                    <CheckCircle2 class="size-10 text-emerald-700 dark:text-emerald-300" />
                  </div>
                  <h3 class="font-display text-2xl font-bold tracking-tight mb-2 text-foreground">
                    {{ t('oobe.completeTitle') }}
                  </h3>
                  <p class="text-foreground/75 max-w-md mx-auto leading-relaxed">
                    {{ t('oobe.completeDesc') }}
                  </p>

                  <div class="mt-8 grid grid-cols-3 gap-3 max-w-lg mx-auto">
                    <div class="rounded-2xl border border-zinc-900/10 dark:border-white/10 p-4 bg-zinc-900/[0.05] dark:bg-white/[0.05]">
                      <div class="size-8 rounded-xl bg-emerald-500/20 ring-1 ring-emerald-400/30 flex items-center justify-center mx-auto mb-2">
                        <Settings2 class="size-4 text-emerald-700 dark:text-emerald-300" />
                      </div>
                      <div class="text-xs font-semibold text-foreground/90">
                        {{ t('oobe.completeSummary1') }}
                      </div>
                    </div>
                    <div class="rounded-2xl border border-zinc-900/10 dark:border-white/10 p-4 bg-zinc-900/[0.05] dark:bg-white/[0.05]">
                      <div class="size-8 rounded-xl bg-cyan-500/20 ring-1 ring-cyan-400/30 flex items-center justify-center mx-auto mb-2">
                        <UserPlus class="size-4 text-cyan-700 dark:text-cyan-300" />
                      </div>
                      <div class="text-xs font-semibold text-foreground/90">
                        {{ t('oobe.completeSummary2') }}
                      </div>
                    </div>
                    <div class="rounded-2xl border border-zinc-900/10 dark:border-white/10 p-4 bg-zinc-900/[0.05] dark:bg-white/[0.05]">
                      <div class="size-8 rounded-xl bg-teal-500/20 ring-1 ring-teal-400/30 flex items-center justify-center mx-auto mb-2">
                        <Globe2 class="size-4 text-teal-700 dark:text-teal-300" />
                      </div>
                      <div class="text-xs font-semibold text-foreground/90">
                        {{ t('oobe.completeSummary3') }}
                      </div>
                    </div>
                  </div>

                  <!-- 安装凭据回执：这是用户唯一一次看到这些信息的机会，之后只能靠登录邮箱找回。
                       密码只显示一次（输入框内容仍在内存里），所以只回显账号与入口，不回显明文口令。 -->
                  <div class="mt-6 max-w-lg mx-auto rounded-2xl border border-zinc-900/10 dark:border-white/10 bg-zinc-900/[0.05] dark:bg-white/[0.05] p-4 text-left">
                    <div class="flex items-center gap-2 mb-3 text-sm font-semibold text-foreground">
                      <ShieldCheck class="size-4 text-emerald-700 dark:text-emerald-300" />
                      {{ t('oobe.credTitle', '请记下你的登录信息') }}
                    </div>
                    <dl class="flex flex-col gap-2 text-xs">
                      <div class="flex items-center justify-between gap-3">
                        <dt class="text-foreground/65">
                          {{ t('oobe.credUsername', '管理员用户名') }}
                        </dt>
                        <dd class="font-mono text-foreground/95 select-all">
                          {{ adminForm.name }}
                        </dd>
                      </div>
                      <div class="flex items-center justify-between gap-3">
                        <dt class="text-foreground/65">
                          {{ t('oobe.credEmail', '管理员邮箱') }}
                        </dt>
                        <dd class="font-mono text-foreground/95 select-all">
                          {{ adminForm.email }}
                        </dd>
                      </div>
                      <div class="flex items-center justify-between gap-3">
                        <dt class="text-foreground/65">
                          {{ t('oobe.credAdminUrl', '后台入口') }}
                        </dt>
                        <dd class="font-mono text-foreground/95 select-all">
                          {{ adminEntryUrl }}
                        </dd>
                      </div>
                      <div class="flex items-center justify-between gap-3">
                        <dt class="text-foreground/65">
                          {{ t('oobe.credSiteUrl', '站点地址') }}
                        </dt>
                        <dd class="font-mono text-foreground/95 select-all">
                          {{ siteForm.siteUrl }}
                        </dd>
                      </div>
                    </dl>
                    <p class="mt-3 text-[11px] text-foreground/60 leading-relaxed">
                      {{ t('oobe.credNote', '密码不会再次显示，请妥善保存。系统已自动为你登录，可直接进入后台。') }}
                    </p>
                  </div>
                </div>

                <!-- 初始进入 / 安装失败后回到这里 -->
                <div
                  v-else
                  class="text-center py-8"
                >
                  <div class="inline-flex items-center justify-center size-20 rounded-full bg-emerald-500/15 ring-1 ring-emerald-400/30 mb-6">
                    <Rocket class="size-10 text-emerald-700 dark:text-emerald-300" />
                  </div>
                  <h3 class="font-display text-2xl font-bold tracking-tight mb-2 text-foreground">
                    {{ t('oobe.readyTitle', '配置已准备就绪') }}
                  </h3>
                  <p class="text-foreground/75 max-w-md mx-auto leading-relaxed">
                    {{ t('oobe.readyDesc', '点击下方按钮，系统将完成数据库初始化、写入配置并创建示例数据。整个过程大概需要 10~30 秒。') }}
                  </p>

                  <!-- 安装失败：展示后端给的结构化 error_code + hint（已脱敏，不含数据库口令） -->
                  <div
                    v-if="installError"
                    class="mt-6 max-w-lg mx-auto flex items-start gap-2.5 p-3 rounded-xl border border-rose-400/35 bg-rose-500/[0.07] text-left"
                    role="alert"
                  >
                    <XCircle class="size-4 shrink-0 mt-0.5 text-rose-700 dark:text-rose-300" />
                    <div class="flex-1 min-w-0 space-y-1">
                      <div class="text-sm font-medium text-rose-800 dark:text-rose-200">
                        {{ installError.message }}
                      </div>
                      <div
                        v-if="installError.hint"
                        class="text-xs text-foreground/70 leading-relaxed whitespace-pre-line"
                      >
                        {{ installError.hint }}
                      </div>
                      <div class="text-[11px] font-mono text-foreground/50">
                        {{ installError.code }}
                      </div>
                    </div>
                  </div>

                  <!-- 安装前预检结论 -->
                  <div
                    v-else-if="preflightState.done && preflightErrors.length"
                    class="mt-6 max-w-lg mx-auto flex items-start gap-2.5 p-3 rounded-xl border border-amber-400/35 bg-amber-500/[0.07] text-left"
                    role="alert"
                  >
                    <AlertTriangle class="size-4 shrink-0 mt-0.5 text-amber-700 dark:text-amber-300" />
                    <div class="flex-1 min-w-0 space-y-1">
                      <div class="text-sm font-medium text-amber-800 dark:text-amber-200">
                        {{ t('oobe.preflightBlocked', '有 {n} 项配置需要修正后才能安装').replace('{n}', String(preflightErrors.length)) }}
                      </div>
                      <ul class="text-xs text-foreground/70 leading-relaxed list-disc pl-4 space-y-0.5">
                        <li
                          v-for="issue in preflightErrors"
                          :key="`s-${issue.field}-${issue.code}`"
                        >
                          {{ issue.message }}
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </template>
            </div>

            <div class="flex justify-between pt-4">
              <Button
                v-if="step > 1 && !installing"
                variant="ghost"
                class="text-foreground/85 hover:bg-zinc-900/10 dark:hover:bg-white/10 hover:text-foreground"
                @click="prevStep"
              >
                <ArrowLeft
                  data-icon="inline-start"
                  class="mr-2"
                />
                {{ t('oobe.prev') }}
              </Button>
              <div v-else />

              <div class="flex gap-2">
                <Button
                  v-if="step === 1"
                  variant="outline"
                  class="!border-zinc-900/15 dark:!border-white/15 bg-zinc-900/[0.04] dark:bg-white/[0.04] text-foreground hover:bg-zinc-900/10 dark:hover:bg-white/10 hover:text-foreground"
                  :disabled="checking || installRunning"
                  @click="runCheckSystem"
                >
                  <Settings2
                    v-if="checking"
                    data-icon="inline-start"
                    class="mr-2 animate-spin"
                  />
                  <RefreshCw
                    v-else
                    data-icon="inline-start"
                    class="mr-2"
                  />
                  {{ checking ? t('oobe.checking') : t('oobe.recheck') }}
                </Button>

                <Button
                  v-if="step < 4"
                  variant="default"
                  class="!bg-emerald-500 !text-zinc-950 hover:!bg-emerald-400"
                  :disabled="!canNext || loading || installRunning"
                  :loading="loading"
                  @click="nextStep"
                >
                  {{ step === 3 ? t('oobe.saveAndNext') : t('oobe.next') }}
                  <ArrowRight
                    data-icon="inline-end"
                    class="ml-2"
                  />
                </Button>

                <template v-else>
                  <Button
                    v-if="!installed"
                    variant="default"
                    size="lg"
                    class="!bg-emerald-500 !text-zinc-950 hover:!bg-emerald-400"
                    :disabled="installing || loading || preflightState.running"
                    @click="finishSetup"
                  >
                    <template v-if="installing">
                      <Loader2
                        data-icon="inline-start"
                        class="mr-2 animate-spin"
                      />
                      {{ t('oobe.installingBtn', '安装中…') }}
                    </template>
                    <template v-else-if="preflightState.running">
                      <Loader2
                        data-icon="inline-start"
                        class="mr-2 animate-spin"
                      />
                      {{ t('oobe.preflightRunning', '正在检查配置…') }}
                    </template>
                    <template v-else>
                      <Rocket
                        data-icon="inline-start"
                        class="mr-2"
                      />
                      {{ t('oobe.runInstall', '开始安装') }}
                    </template>
                  </Button>
                  <Button
                    v-else
                    variant="default"
                    size="lg"
                    class="!bg-emerald-500 !text-zinc-950 hover:!bg-emerald-400"
                    :loading="loading"
                    @click="goAdmin"
                  >
                    <CheckCircle2
                      data-icon="inline-start"
                      class="mr-2"
                    />
                    {{ t('oobe.enterAdmin') }}
                  </Button>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== 左下角：版权 Meta 胶囊 ==========
         点击整张卡片跳 Bing 官方搜索页；不单独提供下载 icon 按钮（版权图由用户浏览器另存为即可）。
         位置钉在主内容区左下角：lg 下左侧偏移 300px 侧边栏 + 48px 内容区内边距，不覆盖侧边栏。 -->
    <a
      v-if="bwp?.copyright"
      :href="getBwpOfficialLink(bwp)"
      target="_blank"
      rel="noopener noreferrer nofollow"
      class="fixed bottom-5 left-5 lg:left-[348px] z-40 group flex items-center gap-3 max-w-sm rounded-full backdrop-blur-2xl saturate-[180%] bg-zinc-950/45 dark:bg-white/[0.07] border border-white/20 pr-4 pl-1.5 py-1.5 shadow-lg shadow-black/40 hover:bg-zinc-950/60 dark:hover:bg-white/[0.11] hover:border-white/30 transition-colors"
    >
      <div class="relative size-9 shrink-0">
        <img
          :src="thumbUrl(bwp?.url)"
          :alt="bwp?.title || ''"
          class="size-9 rounded-full object-cover ring-1 ring-zinc-900/15 dark:ring-white/15"
          loading="lazy"
          decoding="async"
          @error="onThumbError"
        >
        <div class="pointer-events-none absolute inset-0 rounded-full ring-[3px] ring-white/0 group-hover:ring-zinc-900/10 dark:group-hover:ring-white/10 transition-all" />
      </div>
      <div class="min-w-0 flex-1">
        <div class="text-[11px] font-semibold uppercase tracking-wider text-emerald-200/90">
          Bing · Daily
        </div>
        <div
          class="text-xs text-white/90 truncate drop-shadow-[0_1px_0_rgba(0,0,0,0.5)]"
          :title="bwp?.copyright"
        >
          {{ bwp?.copyright }}
        </div>
      </div>
      <ExternalLink class="size-3.5 shrink-0 text-white/55 group-hover:text-white/85 transition-colors" />
    </a>

    <!-- ========== 右下角：切换壁纸控件 ========== -->
    <div class="fixed bottom-5 right-5 z-40 flex items-center gap-1 rounded-full backdrop-blur-2xl saturate-[180%] bg-white/[0.07] border border-zinc-900/10 dark:border-white/10 p-1 shadow-lg shadow-black/40">
      <button
        type="button"
        class="h-9 w-9 inline-flex items-center justify-center rounded-full text-white/85 hover:bg-white/10 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        :disabled="bwpFetching || !bwp?.totalDays || (bwp?.idx ?? 0) >= ((bwp?.totalDays ?? 1) - 1)"
        :title="t('auth.switchWallpaper', '切换壁纸')"
        @click="bwpIdx = Math.min((bwp?.totalDays ?? 1) - 1, (bwp?.idx ?? 0) + 1)"
      >
        <ChevronLeft class="size-[18px]" />
      </button>
      <button
        type="button"
        class="h-9 inline-flex items-center gap-1.5 px-3 rounded-full text-[12px] font-medium text-white/90 hover:bg-white/10 hover:text-white"
        :title="t('auth.switchWallpaper', '切换壁纸')"
        @click="bwpIdx = (bwpIdx + 1) % (bwp?.totalDays ?? 8)"
      >
        <RefreshCw
          class="size-3.5 text-white/70"
          :class="{ 'animate-spin text-white/50': bwpFetching }"
        />
        {{ (bwp?.idx ?? 0) + 1 }}/{{ bwp?.totalDays ?? '?' }}
      </button>
      <button
        type="button"
        class="h-9 w-9 inline-flex items-center justify-center rounded-full text-white/85 hover:bg-white/10 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        :disabled="bwpFetching || (bwp?.idx ?? 0) <= 0"
        :title="t('auth.switchWallpaper', '切换壁纸')"
        @click="bwpIdx = Math.max(0, (bwp?.idx ?? 0) - 1)"
      >
        <ChevronRight class="size-[18px]" />
      </button>
    </div>

    <!-- TLS / 明文 HTTP 风险二次确认（prod 模式 + admin_password 明文 HTTP 时弹出，R2-2.6） -->
    <div>
      <AlertDialog
        :open="tlsDialogOpen"
        @update:open="(v: boolean) => { tlsDialogOpen = v }"
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle class="flex items-center gap-2">
              <ShieldAlert
                data-icon="inline-start"
                class="size-5 text-amber-600 dark:text-amber-500"
              />
              {{ t('oobe.tlsTitle') }}
            </AlertDialogTitle>
            <AlertDialogDescription as-child>
              <div class="flex flex-col gap-3 pt-2 text-sm text-foreground/80 leading-relaxed">
                <p>{{ t('oobe.tlsDesc') }}</p>
                <ul class="list-disc list-inside space-y-1.5 pl-1 text-foreground/75">
                  <li>
                    {{ t('oobe.tlsHintTlsTerminate') }}
                  </li>
                  <li>
                    {{ t('oobe.tlsHintConfigureReverseProxy') }}
                  </li>
                  <li class="text-rose-600/90 dark:text-rose-400/90">
                    {{ t('oobe.tlsHintRisk') }}
                  </li>
                </ul>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel @click="onTlsGoBack">
              {{ t('oobe.tlsGoBack') }}
            </AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              @click="reallyRunInstall"
            >
              {{ t('oobe.tlsContinueAnyway') }}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import OOBENavbar from '~~/components/OOBENavbar.vue'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Badge } from '~~/components/ui/badge'
import { Separator } from '~~/components/ui/separator'
import { Switch } from '~~/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '~~/components/ui/select'
import { Label } from '~~/components/ui/label'
import { ToggleGroup, ToggleGroupItem } from '~~/components/ui/toggle-group'
import { FieldSet, FieldLegend } from '~~/components/ui/field'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '~~/components/ui/alert-dialog'
import { useOOBE, type DepProgressEvt, type InstallProgressEvt } from '~~/composables/useOOBE'
import { resetOOBECache } from '~~/middleware/oobe.global'
import { useI18n } from 'vue-i18n'
// 口令强度只做「可视化」：真正的准入规则由后端 security_password_policy 开关决定，
// 前端看不到该设置，所以最终以 POST /oobe/preflight 的判定为准（见 runPreflight）。
import {
  PASSWORD_MIN_LENGTH,
  evaluatePasswordStrength,
  passwordStrengthPercent,
  type PasswordRuleId
} from '~~/lib/passwordStrength'
import {
  RefreshCw,
  Settings2,
  UserPlus,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Globe2,
  ArrowLeft,
  ArrowRight,
  Mail,
  Eye,
  EyeOff,
  Tag,
  Link as LinkIcon,
  Wrench,
  Download,
  Loader2,
  Database,
  Sparkles,
  Rocket,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Server,
  Wifi,
  WifiOff,
  Cpu,
  Cable,
  ShieldAlert
} from '@lucide/vue'
import { computed, markRaw, nextTick, onMounted, ref, watch } from 'vue'

definePageMeta({ layout: false })

interface BingWallpaperPayload {
  url: string
  title: string
  copyright: string
  copyrightLink: string
  startDate: string
  idx: number
  totalDays: number
}

const { t } = useI18n()
const oobe = useOOBE()
const {
  systemChecks, systemSummary, loading, checkSystem, createAdmin, saveSiteSettings,
  finishOOBE, getOOBEStatus, installDependencies, subscribeDependencyStream,
  effectiveApiBase, setBackendApiBase, probeBackend, normalizeUserApiBase,
  clearOOBEApiBaseOverrideFromStorage, installSnapshotState, cancelInstallWatch,
  preflight, testDatabase, checkUsername
} = oobe

// ====== Bing 每日壁纸（后台风格：emerald/teal/cyan 三束光 + 毛玻璃） ======
// —— 使用 FastAPI /api/bing/wallpapers，与 login/register 的 useBingWallpaper 同源。
//    该端点在 OOBE 期由 main.py 白名单放行（服务端 Bing 中继，无凭据）。
//    浏览器直连 bing.com 的回退已删（必被 CORS 拦截）；失败时用本地 Unsplash 占位图。
const bwpIdx = ref(0)
const wallpaperLoaded = ref(false)
const bwpFetching = ref(false)
const bwpList = ref<Array<{ url: string, urlbase: string, title: string, copyright: string, copyrightlink: string, startdate: string, full_url: string, uhd_url: string }>>([])

const UNSPLASH_FALLBACKS: Array<{ url: string, copyright: string, title: string }> = [
  { url: 'https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=1920&q=80', copyright: '© Unsplash / Eberhard Grossgasteiger', title: '山川湖泊' },
  { url: 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1920&q=80', copyright: '© Unsplash / Noah Silliman', title: '松林雾霭' },
  { url: 'https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=1920&q=80', copyright: '© Unsplash / Eberhard Grossgasteiger', title: '秋色山谷' },
  { url: 'https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=1920&q=80', copyright: '© Unsplash / Robert Lukeman', title: '海岸灯塔' },
  { url: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1920&q=80', copyright: '© Unsplash / Federico Beccari', title: '雪岭之巅' },
  { url: 'https://images.unsplash.com/photo-1433086966358-54859d0ed716?w=1920&q=80', copyright: '© Unsplash / Eberhard Grossgasteiger', title: '森林瀑布' },
  { url: 'https://images.unsplash.com/photo-1475924156734-496f6cac6ec1?w=1920&q=80', copyright: '© Unsplash / Luke Stackpoole', title: '极光之夜' },
  { url: 'https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?w=1920&q=80', copyright: '© Unsplash / Casey Horner', title: '林间小径' }
]

const fetchBwp = async () => {
  bwpFetching.value = true
  type BwpImage = {
    url?: string
    urlbase?: string
    title?: string
    copyright?: string
    copyrightlink?: string
    copyright_link?: string
    startdate?: string
    enddate?: string
    full_url?: string
    fullUrl?: string
    uhd_url?: string
    uhdUrl?: string
  }
  try {
    const cfg = useRuntimeConfig()
    const apiBase = (cfg.public?.apiBase as string) || '/api'
    // 1) FastAPI 代理（缓存 1h，推荐源）
    try {
      const r = await $fetch<{ success: boolean, data?: { images?: BwpImage[] }, images?: BwpImage[] }>('/bing/wallpapers', {
        baseURL: apiBase,
        query: { n: 8, market: 'zh-CN' }
      })
      const arr: BwpImage[] = r?.data?.images || r?.images || []
      if (Array.isArray(arr) && arr.length > 0) {
        bwpList.value = arr.map((img: BwpImage) => {
          const u = img?.url || ''
          const ub = img?.urlbase || ''
          const normalizedFullUrl
            = img?.full_url
              || img?.fullUrl
              || (u && !u.startsWith('http') ? `https://www.bing.com${u}` : u || '')
          const normalizedUhdUrl
            = img?.uhd_url
              || img?.uhdUrl
              || (ub ? `https://www.bing.com${ub}_UHD.jpg` : '')
          return {
            url: u,
            urlbase: ub,
            title: img?.title || '',
            copyright: img?.copyright || '',
            copyrightlink: img?.copyright_link || img?.copyrightlink || '',
            startdate: img?.startdate || img?.enddate || '',
            full_url: normalizedFullUrl,
            uhd_url: normalizedUhdUrl
          }
        })
      }
    } catch {
      // 2) 直连 bing.com 的回退已删除：浏览器跨域 fetch bing.com 必然被 CORS
      //    拦截（Bing 不带 Access-Control-Allow-Origin），这条路径从未成功过，
      //    只会在控制台刷 CORS 报错。失败时直接落到下方本地占位图。
    }
    if (!bwpList.value || bwpList.value.length === 0) {
      const now = Date.now()
      bwpList.value = UNSPLASH_FALLBACKS.map((p, idx) => {
        const d = new Date(now - idx * 86400 * 1000)
        const ymd = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
        return {
          url: p.url,
          urlbase: '',
          title: p.title,
          copyright: p.copyright,
          copyrightlink: 'https://unsplash.com/',
          startdate: ymd,
          full_url: p.url,
          uhd_url: p.url
        }
      })
    }
    if (bwpIdx.value >= bwpList.value.length) {
      bwpIdx.value = 0
    }
    const uhd = bwp.value?.url
    if (uhd && typeof Image !== 'undefined') {
      wallpaperLoaded.value = false
      const pre = new Image()
      pre.onload = () => {
        wallpaperLoaded.value = true
      }
      pre.onerror = () => {
        wallpaperLoaded.value = true
      }
      pre.src = uhd
    } else {
      wallpaperLoaded.value = true
    }
  } finally {
    bwpFetching.value = false
  }
}

const bwp = computed<BingWallpaperPayload | null>(() => {
  const list = bwpList.value
  if (!list || list.length === 0) return null
  const i = Math.min(bwpIdx.value, list.length - 1)
  const item = list[i]
  if (!item) return null
  return {
    url: item.uhd_url || item.full_url || item.url,
    title: item.title || '',
    copyright: item.copyright || '',
    copyrightLink: item.copyrightlink || 'https://www.bing.com',
    startDate: item.startdate || '',
    idx: i,
    totalDays: list.length
  }
})

/**
 * 生成 Bing 官方「当前壁纸」跳转链接。
 *  1) 优先用 Bing API 返回的 copyrightLink / copyrightlink（精确的搜索页）
 *  2) 无版权链接时，按 title 拼 https://www.bing.com/search?q={title}
 *  3) 最后兜底 bing.com 首页
 * 点击整张 Meta 版权卡片即跳官方界面，不再单独提供下载 icon 按钮（用户浏览器另存为即可）。
 */
function getBwpOfficialLink(img: BingWallpaperPayload | null | { copyrightlink?: string, copyrightLink?: string, title?: string } | null): string {
  if (!img) return 'https://www.bing.com'
  const raw = (img as { copyrightLink?: unknown }).copyrightLink ?? (img as { copyrightlink?: unknown }).copyrightlink
  if (typeof raw === 'string' && raw.startsWith('http')) return raw
  const title = (img as { title?: unknown }).title
  if (typeof title === 'string' && title.trim()) {
    return `https://www.bing.com/search?q=${encodeURIComponent(title.trim())}`
  }
  return 'https://www.bing.com'
}

// 首拉 + idx 变更重新 preload
watch(bwpIdx, () => {
  const uhd = bwp.value?.url
  if (uhd && typeof Image !== 'undefined') {
    wallpaperLoaded.value = false
    const pre = new Image()
    pre.onload = () => {
      wallpaperLoaded.value = true
    }
    pre.onerror = () => {
      wallpaperLoaded.value = true
    }
    pre.src = uhd
  } else {
    wallpaperLoaded.value = true
  }
})

onMounted(async () => {
  await fetchBwp()
})

const thumbUrl = (url?: string) => {
  if (!url) return ''
  try {
    const u = new URL(url, 'https://www.bing.com')
    // Bing 存在两种返回形态：
    //   ① query 形：/th?id=OHR.xxx_1920x1080.jpg&pid=hp —— 尺寸在 id 参数里；
    //   ② path 形： /th/OHR.xxx_1920x1080.jpg —— 尺寸在 pathname 里。
    // 此前的实现只按 pathname 替换，对 query 形会拼出 /th_150x84.jpg 这种
    // 不存在的地址 → 署名胶囊缩略图裂图（背景图直接用原 url 所以正常）。
    const id = u.searchParams.get('id')
    if (id) {
      u.searchParams.set('id', id.replace(/_\d+x\d+\.jpg$/i, '_150x84.jpg'))
      return u.toString()
    }
    u.pathname = u.pathname.replace(/_\d+x\d+\.jpg$/i, '_150x84.jpg')
    return u.toString()
  } catch {
    return ''
  }
}

// 缩略图兜底：个别壁纸没有 150x84 变体时回退原图，仍失败则隐藏，不留裂图。
const onThumbError = (e: Event) => {
  const img = e.target as HTMLImageElement
  if (bwp.value?.url && !img.src.endsWith(bwp.value.url)) {
    img.src = bwp.value.url
    return
  }
  img.style.visibility = 'hidden'
}

// ====== 原始 OOBE 业务状态 ======
const step = ref(1)
const checking = ref(false)
const showAdminPassword = ref(false)
const showAdminConfirmPassword = ref(false)
// R2-2.6：明文 HTTP TLS 二次确认对话开关；关闭时 focus 回到对应输入
const tlsDialogOpen = ref(false)
const apiUrlInputRef = ref<HTMLInputElement | null>(null)

// ----- O 系列 Step1 后端连接相关状态 -----
const connMode = ref<'dev' | 'prod'>('dev')
const connApiUrl = ref('http://127.0.0.1:8000/api')
const backendProbeRunning = ref(false)
interface BackendProbeResult {
  ok: boolean
  code: number
  statusText: string
  stage: 'health' | 'status' | 'init'
  errorCode?: string
  detail?: string
  apiBase?: string
  oobeRequired?: boolean
  oobeComplete?: boolean
}
const backendProbeResult = ref<BackendProbeResult>({
  ok: false, code: 0, statusText: '', stage: 'init'
})
const backendProbeApplied = ref(false)
const quickPorts = ['8000', '8001', '8080']

const onConnModeChange = (v: 'dev' | 'prod') => {
  connMode.value = v
  if (v === 'dev') {
    // 开发模式默认填本机 8000 /api（或从 effectiveApiBase 继承）
    const curr = (effectiveApiBase.value || '').trim()
    if (curr && curr !== '/api' && /^https?:\/\//i.test(curr)) {
      connApiUrl.value = curr
    } else {
      connApiUrl.value = 'http://127.0.0.1:8000/api'
    }
  } else {
    connApiUrl.value = '/api'
  }
  // 用户改模式 → 重置探测状态
  backendProbeResult.value = { ok: false, code: 0, statusText: '', stage: 'init' }
  backendProbeApplied.value = false
}

const applyQuickPort = (p: string) => {
  if (connMode.value !== 'dev') return
  const port = p.trim()
  if (!port) return
  // 纯数字端口：按 http://127.0.0.1:<port>/api 重写
  if (/^\d+$/.test(port)) {
    connApiUrl.value = `http://127.0.0.1:${port}/api`
  } else {
    connApiUrl.value = port
  }
  backendProbeResult.value = { ok: false, code: 0, statusText: '', stage: 'init' }
  backendProbeApplied.value = false
}

const watchProbeFailText = computed(() => {
  const r = backendProbeResult.value
  if (!r || r.ok) return ''
  if (r.code === 0) return t('oobe.connProbeNetworkError')
  if (r.stage === 'health' && r.code !== 200) return t('oobe.connProbeNotHealthy')
  return r.detail || `${t('oobe.connProbeFailDetail')}：HTTP ${r.code} ${r.statusText || ''}${r.errorCode ? ` (${r.errorCode})` : ''}`
})

// ---- O 系列 Step1 模板抽取辅助（避免模板内复杂 JS/全局对象访问） ----
// reka-ui 2.10 Switch 受控属性是 modelValue（事件 @update:model-value）；
// :checked/@update:checked 在此版本不存在，用了会导致开关永远显示未选中。
const switchProdMode = (prod: boolean) => onConnModeChange(prod ? 'prod' : 'dev')
// 用户编辑 URL 框时重置探测结果（需要 .value，因为是在 script 内）
const resetProbeStateOnEdit = () => {
  backendProbeResult.value = { ok: false, code: 0, statusText: '', stage: 'init' }
  backendProbeApplied.value = false
}
// 快选端口激活态：从 connApiUrl 提取当前 port，失败时返回空串
const connActivePort = computed<string>(() => {
  const url = String(connApiUrl.value || '').trim()
  try {
    if (!/^https?:\/\//i.test(url)) return ''
    const u = new URL(url)
    return u.port
  } catch {
    return ''
  }
})
// 自定义端口按钮：保留视觉占位，当前暂不实现弹出输入
const customPortNoop = () => { /* keep noop */ }

// ---- QW-D：URL 输入即时合法性（专业 CMS：不等到点「探测」才报错） ----
const connApiUrlNormalizedPreview = computed<string>(() => normalizeUserApiBase(connApiUrl.value) || '')
const connApiUrlInvalid = computed<boolean>(() => {
  const raw = String(connApiUrl.value || '').trim()
  if (!raw) return true
  const normalized = normalizeUserApiBase(raw)
  // 相对路径 /api 或绝对 http(s)://host:port/api 才合法
  if (normalized && (normalized.startsWith('/') || /^https?:\/\//i.test(normalized))) return false
  return true
})
const connApiUrlHintText = computed(() => {
  const raw = String(connApiUrl.value || '').trim()
  if (!raw) return t('oobe.connApiUrlEmptyHint', { default: '请填写后端 API 地址。例如：http://127.0.0.1:8000/api 或 /api' })
  if (connApiUrlInvalid.value) return t('oobe.connApiUrlInvalidHint', { default: '地址格式无效，仅支持绝对 http(s)://host:port[/api] 或同源相对路径 /api' })
  if (connApiUrlNormalizedPreview.value && connApiUrlNormalizedPreview.value !== raw) {
    return t('oobe.connApiUrlWillNormalizeHint', { url: connApiUrlNormalizedPreview.value, default: `点击探测后将自动规范化为：${connApiUrlNormalizedPreview.value}` })
  }
  return connMode.value === 'dev' ? t('oobe.connApiUrlDevHint') : t('oobe.connApiUrlProdHint')
})

const runProbeBackend = async () => {
  if (backendProbeRunning.value) return
  backendProbeRunning.value = true
  backendProbeApplied.value = false
  try {
    const r = await probeBackend(connApiUrl.value, { timeoutMs: 6000 })
    backendProbeResult.value = {
      ok: r.ok,
      code: r.code,
      statusText: r.statusText,
      stage: r.stage,
      errorCode: r.errorCode,
      detail: r.detail,
      apiBase: r.apiBase,
      oobeRequired: r.oobeRequired,
      oobeComplete: r.oobeComplete
    }
    if (r.ok) {
      // 探测成功 → 应用 apiBase（写入 composable 内部 + localStorage，确保后续 request/SSE 立即命中）
      setBackendApiBase(r.apiBase)
      backendProbeApplied.value = true
      // 探测成功 → 自动跑一次系统检测（Step1 的下卡），减少用户再点一次
      try {
        checking.value = true
        await checkSystem()
      } catch (e) {
        // 系统检测失败时：写一条明确 warn 行，让 canNext 有合理提示（而不是空数组 + 无按钮无提示）
        const msg = e instanceof Error ? e.message : String(e)
        systemChecks.value = [{
          name: '系统环境检测',
          detail: msg || '后端返回异常，请点下方「重新检测」或确认后端服务状态',
          status: 'warn',
          statusText: '需重试'
        }]
      } finally {
        checking.value = false
      }
    }
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e)
    backendProbeResult.value = {
      ok: false,
      code: 0,
      statusText: msg,
      stage: 'health',
      detail: msg
    }
  } finally {
    backendProbeRunning.value = false
  }
}

// ----- 依赖安装相关状态 -----
const installRunning = ref(false)
const depInstalled = ref(false)
const installPercent = ref(0)
const installStatusText = ref('')
const installSummary = ref<{ success?: number, failed?: number, skipped?: number, total?: number }>({})
interface DepLogLine { time: string, text: string, level?: 'log' | 'warn' | 'success' | 'error' }
const depLogLines = ref<DepLogLine[]>([])
const logBoxRef = ref<HTMLElement | null>(null)

const appendLog = (text: string, level: DepLogLine['level'] = 'log') => {
  const pad = (n: number) => n.toString().padStart(2, '0')
  const d = new Date()
  const time = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  depLogLines.value.push({ time, text, level })
  nextTick(() => {
    if (logBoxRef.value) logBoxRef.value.scrollTop = logBoxRef.value.scrollHeight
  })
}

// 分步提交失败时的可见反馈（以前只在 console.error 里，用户点了「下一步」没反应）
const stepError = ref('')

// ----- 安装进度 Step4 相关 -----
const installing = ref(false)
const installed = ref(false)
const installStepMessage = ref('')
const installStepIndex = ref(-1)
const installStepList = reactive([
  { id: 'write_env', label: t('oobe.isWriteEnv', '写入环境配置'), done: false },
  { id: 'init_schema', label: t('oobe.isInitSchema', '初始化数据库表结构'), done: false },
  { id: 'create_admin', label: t('oobe.isCreateAdmin', '创建管理员账户'), done: false },
  { id: 'write_site_settings', label: t('oobe.isWriteSite', '写入站点配置项'), done: false },
  { id: 'mock_data', label: t('oobe.isMockData', '生成示例数据'), done: false },
  { id: 'write_pages', label: t('oobe.isPages', '创建关于和留言板页面'), done: false },
  { id: 'write_nav', label: t('oobe.isNav', '写入导航菜单'), done: false },
  { id: 'finalize', label: t('oobe.isFinalize', '标记安装完成'), done: false }
])

// 页面加载时先取一次状态（完成后重定向首页）
onMounted(async () => {
  // 初始化 Step1 的 UI 值：从 effectiveApiBase 反推模式
  const cur = (effectiveApiBase.value || '').trim()
  if (cur && cur !== '/api' && /^https?:\/\//i.test(cur)) {
    // 已有绝对地址 → Dev 模式
    connMode.value = 'dev'
    connApiUrl.value = cur
  } else if (cur === '/api' || !cur) {
    // 同源相对 → 仍默认 Dev 模式（本地 8000），用户可切 Prod
    connMode.value = 'dev'
    connApiUrl.value = 'http://127.0.0.1:8000/api'
  }
  try {
    const result = await getOOBEStatus()
    const payload = result?.data?.value as { oobe_complete?: boolean } | null | undefined
    if (payload?.oobe_complete === true) {
      resetOOBECache(true)
      try {
        await navigateTo('/', { replace: true })
      } catch {
        // ignore nav failures
      }
      if (typeof window !== 'undefined' && window.location.pathname === '/oobe') {
        window.location.href = '/'
      }
      return
    }
  } catch {
    // 忽略：后端还没启动起来时也会失败，默认进入向导
  }
  // ** 注意：O 系列改版后，首次进入 step1 不再自动跑 checkSystem **
  // 用户必须先通过「探测连接」→ 成功后 handler 会自动触发 checkSystem。
})

const steps = [
  {
    title: t('oobe.step1Title'),
    desc: t('oobe.step1Desc'),
    longDesc: t('oobe.step1LongDesc'),
    icon: markRaw(Server)
  },
  {
    title: t('oobe.step2Title'),
    desc: t('oobe.step2Desc'),
    longDesc: t('oobe.step2LongDesc'),
    icon: markRaw(UserPlus)
  },
  {
    title: t('oobe.step3Title'),
    desc: t('oobe.step3Desc'),
    longDesc: t('oobe.step3LongDesc'),
    icon: markRaw(Globe2)
  },
  {
    title: t('oobe.step4Title'),
    desc: t('oobe.step4Desc'),
    longDesc: t('oobe.step4LongDesc'),
    icon: markRaw(Rocket)
  }
]

const adminForm = reactive({
  name: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const { locale: currentLocale } = useI18n()
// 站点 URL 默认值统一走 runtimeConfig.public.siteUrl，客户端再兜底 location.origin，
// 禁止散落写默认 http://localhost:3000 / 127.0.0.1 字面量。
const runtimeCfg = useRuntimeConfig()
const defaultOrigin = computed(() => {
  const fromCfg = String(runtimeCfg.public.siteUrl || '').trim()
  if (fromCfg) return fromCfg.replace(/\/$/, '')
  if (import.meta.client && typeof location !== 'undefined') return location.origin.replace(/\/$/, '')
  return ''
})
interface SiteForm {
  name: string
  description: string
  locale: string
  keywords: string
  siteUrl: string
  databaseType: 'sqlite' | 'postgresql'
  dbHost: string
  dbPort: number
  dbName: string
  dbUser: string
  dbPassword: string
  dbPath: string
  redisEnabled: boolean
  redisHost: string
  redisPort: number
  redisPassword: string
  environment: 'development' | 'production'
  enableComments: boolean
  enableRegistration: boolean
  enableRss: boolean
  enableBingWallpaper: boolean
  enablePagefindSearch: boolean
  enableEncryptedPosts: boolean
  enableMusicPlayer: boolean
}
const siteForm = reactive<SiteForm>({
  name: 'Rosetta',
  description: '',
  locale: (currentLocale.value === 'zh_Hant' ? 'zh_Hant' : currentLocale.value === 'ja' ? 'ja' : currentLocale.value === 'en' ? 'en' : 'zh'),
  keywords: 'blog, rosetta, nuxt, fastapi',
  siteUrl: defaultOrigin.value,
  databaseType: 'sqlite',
  dbHost: 'localhost',
  dbPort: 5432,
  dbName: 'rosetta',
  dbUser: '',
  dbPassword: '',
  dbPath: 'rosetta.db',
  redisEnabled: false,
  redisHost: 'localhost',
  redisPort: 6379,
  redisPassword: '',
  environment: 'production',
  enableComments: true,
  enableRegistration: false,
  enableRss: true,
  enableBingWallpaper: true,
  enablePagefindSearch: true,
  enableEncryptedPosts: false,
  enableMusicPlayer: true
})

const isProductionEnv = computed({
  get: () => siteForm.environment === 'production',
  set: (v: boolean) => { siteForm.environment = v ? 'production' : 'development' }
})

// ===== R2-2.6：Prod Mode 明文 HTTP 检测 =====
// 任何字符串是否为 http:// 开头（忽略两端空白）
const isPlainHttp = (s?: string) => /^http:\/\//i.test(String(s || '').trim())
// 风险命中条件：(1) 部署模式为 prod **或** (2) Step3 的环境开关为 production，
// 并且 (effectiveApiBase 明文 **或** siteForm.siteUrl 明文)
const isPlaintextHttpRisk = computed<boolean>(() => {
  const prodMode = connMode.value === 'prod' || isProductionEnv.value
  if (!prodMode) return false
  return isPlainHttp(effectiveApiBase.value) || isPlainHttp(siteForm.siteUrl)
})
// TLS 对话取消：跳回对应步骤并 focus 到输入
const onTlsGoBack = async () => {
  tlsDialogOpen.value = false
  // 优先返回明文来源所在步骤：若 effectiveApiBase 是 http 则 Step1，否则 Step3
  const source = isPlainHttp(effectiveApiBase.value) ? 1 : 3
  step.value = source
  await nextTick()
  if (source === 1) {
    apiUrlInputRef.value?.focus?.()
  } else if (typeof document !== 'undefined') {
    const el = document.querySelector<HTMLInputElement>('input[type="url"][name="site-url"], input[type="url"]')
    el?.focus?.()
  }
}

// ====== Step2：管理员字段级校验 + 远程用户名预检 ======
// 正则与后端 `backend/core/oobe_constants.py` 的 USERNAME_PATTERN / EMAIL_PATTERN 严格对齐。
// ⚠️ 历史上这里写的是 {3,32} 而后端是 {3,20}，导致 21~32 位用户名前端放行、
// 提交时被后端 Pydantic 校验 422 弹回 —— 同一字段两套口径，必须共用一份正则。
const USERNAME_RE = /^[A-Za-z0-9_-]{3,20}$/
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const passwordStrength = computed(() => evaluatePasswordStrength(adminForm.password))
const strengthPercent = computed(() => passwordStrengthPercent(passwordStrength.value))
const strengthBarClass = computed(() => ({
  weak: 'bg-rose-500',
  fair: 'bg-amber-400',
  good: 'bg-teal-400',
  strong: 'bg-emerald-400'
})[passwordStrength.value.level])
const strengthTextClass = computed(() => ({
  weak: 'text-rose-700 dark:text-rose-300',
  fair: 'text-amber-700 dark:text-amber-300',
  good: 'text-teal-700 dark:text-teal-300',
  strong: 'text-emerald-700 dark:text-emerald-300'
})[passwordStrength.value.level])
const strengthLabel = computed(() => ({
  weak: t('oobe.pwWeak', '弱'),
  fair: t('oobe.pwFair', '一般'),
  good: t('oobe.pwGood', '较强'),
  strong: t('oobe.pwStrong', '强')
})[passwordStrength.value.level])

const passwordRuleLabel = (id: PasswordRuleId) => ({
  length: t('oobe.pwRuleLength', '至少 8 位'),
  lower: t('oobe.pwRuleLower', '含小写字母'),
  upper: t('oobe.pwRuleUpper', '含大写字母'),
  digit: t('oobe.pwRuleDigit', '含数字'),
  blocklist: t('oobe.pwRuleBlocklist', '不是常见弱口令')
})[id]

/** 已填写但未通过校验的字段 → 提示文案（空值不算错，避免刚进页面就飘红） */
const adminFieldErrors = computed<Record<string, string>>(() => {
  const out: Record<string, string> = {}
  const name = adminForm.name.trim()
  if (name && !USERNAME_RE.test(name)) {
    out.name = t('oobe.errUsernameFormat', '用户名需为 3–20 位字母、数字、下划线或短横线')
  }
  const email = adminForm.email.trim()
  if (email && !EMAIL_RE.test(email)) {
    out.email = t('oobe.errEmailFormat', '邮箱格式不正确')
  }
  if (adminForm.password && adminForm.password.length < PASSWORD_MIN_LENGTH) {
    out.password = t('oobe.errPasswordShort', '密码至少需要 8 位')
  }
  if (adminForm.confirmPassword && adminForm.password !== adminForm.confirmPassword) {
    out.confirmPassword = t('oobe.errPasswordMismatch', '两次输入的密码不一致')
  }
  return out
})

// 远程用户名预检：debounce 500ms，失败一律降级为"未校验"而不是阻断 ——
// 向导阶段后端可能还没起来，网络错误不该让用户卡在这一步。
type UsernameCheckState = 'idle' | 'checking' | 'ok' | 'invalid'
const usernameCheckState = ref<UsernameCheckState>('idle')
const usernameCheckMessage = ref('')
let _usernameTimer: ReturnType<typeof setTimeout> | null = null

watch(() => adminForm.name, (val) => {
  const name = String(val || '').trim()
  if (_usernameTimer) clearTimeout(_usernameTimer)
  if (!name) {
    usernameCheckState.value = 'idle'
    usernameCheckMessage.value = ''
    return
  }
  if (!USERNAME_RE.test(name)) {
    // 格式都不对就别浪费一次网络往返，本地校验已经给出提示了
    usernameCheckState.value = 'invalid'
    usernameCheckMessage.value = t('oobe.errUsernameFormat', '用户名需为 3–20 位字母、数字、下划线或短横线')
    return
  }
  usernameCheckState.value = 'checking'
  usernameCheckMessage.value = t('oobe.checkingUsername', '正在检查用户名…')
  _usernameTimer = setTimeout(async () => {
    try {
      const { data, error } = await checkUsername(name)
      if (error.value || !data.value) {
        usernameCheckState.value = 'idle'
        usernameCheckMessage.value = ''
        return
      }
      const payload = data.value as { available?: boolean, message?: string | null }
      if (payload.available === false) {
        usernameCheckState.value = 'invalid'
        usernameCheckMessage.value = payload.message || t('oobe.errUsernameFormat', '用户名需为 3–20 位字母、数字、下划线或短横线')
      } else {
        usernameCheckState.value = 'ok'
        usernameCheckMessage.value = t('oobe.usernameAvailable', '用户名可用')
      }
    } catch {
      usernameCheckState.value = 'idle'
      usernameCheckMessage.value = ''
    }
  }, 500)
})

// ====== Step3：数据库连接体检 ======
// 结果里的 code/hint 来自后端 setup_database.classify_db_error，前端只渲染不翻译
// （code 是稳定的机器码，文案由后端按当前 locale 给出）。
interface DbTestState {
  status: 'idle' | 'testing' | 'ok' | 'error'
  code: string
  message: string
  hint: string
}
const dbTest = ref<DbTestState>({ status: 'idle', code: '', message: '', hint: '' })
const dbTestDirty = ref(false)

const runDbTest = async () => {
  if (dbTest.value.status === 'testing') return
  dbTestDirty.value = false
  dbTest.value = { status: 'testing', code: '', message: t('oobe.dbTesting', '正在连接数据库…'), hint: '' }
  try {
    const { data, error } = await testDatabase({
      db_type: siteForm.databaseType,
      db_host: siteForm.dbHost,
      db_port: siteForm.dbPort,
      db_name: siteForm.dbName,
      db_user: siteForm.dbUser,
      db_password: siteForm.dbPassword,
      db_path: siteForm.dbPath
    })
    if (error.value || !data.value) {
      dbTest.value = {
        status: 'error',
        code: 'DB_UNKNOWN',
        message: (error.value as { message?: string } | null)?.message || t('oobe.dbTestFailed', '无法连接数据库'),
        hint: t('oobe.dbTestFailedHint', '请确认数据库服务已启动，且主机/端口可从此服务器访问。')
      }
      return
    }
    const r = data.value
    dbTest.value = {
      status: r.success ? 'ok' : 'error',
      code: r.code || (r.success ? 'DB_OK' : 'DB_UNKNOWN'),
      message: r.message || '',
      hint: r.hint || ''
    }
  } catch (e) {
    dbTest.value = {
      status: 'error',
      code: 'DB_UNKNOWN',
      message: e instanceof Error ? e.message : String(e),
      hint: t('oobe.dbTestFailedHint', '请确认数据库服务已启动，且主机/端口可从此服务器访问。')
    }
  }
}

// 改动任一连接参数就作废上一次的体检结论，防止"测过了"标签误导用户
watch(
  () => [siteForm.databaseType, siteForm.dbHost, siteForm.dbPort, siteForm.dbName, siteForm.dbUser, siteForm.dbPassword, siteForm.dbPath],
  () => {
    if (dbTest.value.status === 'ok' || dbTest.value.status === 'error') {
      dbTest.value = { status: 'idle', code: '', message: '', hint: '' }
      dbTestDirty.value = true
    }
  }
)

// ====== Step4：安装前预检 ======
interface PreflightIssue {
  field: string
  level: 'error' | 'warn'
  code: string
  message: string
  hint?: string | null
}
const preflightState = ref<{
  running: boolean
  done: boolean
  ok: boolean | null
  issues: PreflightIssue[]
  database: { checked: boolean, ok: boolean, code: string, message: string, hint?: string | null, version?: string | null } | null
}>({ running: false, done: false, ok: null, issues: [], database: null })

/** 预检问题字段 → 所在步骤，用于「跳去修复」 */
const ISSUE_FIELD_STEP: Record<string, number> = {
  admin_username: 2,
  admin_email: 2,
  admin_password: 2,
  site_name: 3,
  site_url: 3,
  database: 3
}

const buildPreflightPayload = () => ({
  admin_username: adminForm.name.trim() || undefined,
  admin_email: adminForm.email.trim() || undefined,
  admin_password: adminForm.password || undefined,
  site_name: siteForm.name.trim() || undefined,
  site_url: siteForm.siteUrl.trim() || undefined,
  database_type: siteForm.databaseType,
  db_host: siteForm.dbHost,
  db_port: siteForm.dbPort,
  db_name: siteForm.dbName,
  db_user: siteForm.dbUser,
  db_password: siteForm.dbPassword,
  db_path: siteForm.dbPath,
  check_database: siteForm.databaseType === 'postgresql'
})

const runPreflight = async (): Promise<boolean> => {
  if (preflightState.value.running) return false
  preflightState.value = { ...preflightState.value, running: true }
  try {
    const { data, error } = await preflight(buildPreflightPayload())
    if (error.value || !data.value) {
      // 预检本身失败（后端未就绪/网络问题）不阻断：安装路径仍有服务端校验兜底
      preflightState.value = { running: false, done: false, ok: null, issues: [], database: null }
      return true
    }
    const r = data.value
    preflightState.value = {
      running: false,
      done: true,
      ok: r.ok !== false,
      issues: (r.issues as PreflightIssue[]) || [],
      database: r.database || null
    }
    return r.ok !== false
  } catch {
    preflightState.value = { running: false, done: false, ok: null, issues: [], database: null }
    return true
  }
}

const preflightErrors = computed(() => preflightState.value.issues.filter(i => i.level === 'error'))
const preflightWarns = computed(() => preflightState.value.issues.filter(i => i.level === 'warn'))

const goFixIssue = (field: string) => {
  const target = ISSUE_FIELD_STEP[field] || 3
  step.value = target
  preflightState.value = { running: false, done: false, ok: null, issues: [], database: null }
}

// ====== Step4：安装失败结构化展示 ======
// 后端现在回 error_code + hint（见 backend/api/oobe.py 的 OOBEInstallFailedException），
// 以前只能把整段异常文案甩给用户，里面可能夹着带口令的 DSN。
const installError = ref<{ code: string, message: string, hint: string } | null>(null)

/** 完成后回执里的后台入口：拼站点 URL + /admin，与后端 OobeInstallResponse.admin_url 同口径 */
const adminEntryUrl = computed(() => `${String(siteForm.siteUrl || '').replace(/\/$/, '')}/admin`)

const canNext = computed(() => {
  if (step.value === 1) {
    // O 系列 Step1：必须先通过后端连接探测，其次系统检测无硬错误
    const probePassed = Boolean(backendProbeResult.value?.ok) && backendProbeApplied.value
    if (!probePassed) return false
    return systemChecks.value.length > 0 && systemChecks.value.every(c => c.status !== 'err')
  }
  if (step.value === 2) {
    return (
      Object.keys(adminFieldErrors.value).length === 0
      && adminForm.name.trim()
      && USERNAME_RE.test(adminForm.name.trim())
      && adminForm.email.trim()
      && EMAIL_RE.test(adminForm.email.trim())
      && adminForm.password.length >= PASSWORD_MIN_LENGTH
      && adminForm.password === adminForm.confirmPassword
      && usernameCheckState.value !== 'invalid'
    )
  }
  if (step.value === 3) {
    return (
      siteForm.name.trim()
      && siteForm.siteUrl.trim()
      && /^https?:\/\/[^\s/$.?#].[^\s]*$/.test(siteForm.siteUrl.trim())
      && (siteForm.databaseType === 'sqlite'
        || (siteForm.databaseType === 'postgresql' && siteForm.dbName.trim() && siteForm.dbUser.trim()))
    )
  }
  return true
})

const runCheckSystem = async () => {
  checking.value = true
  try {
    await checkSystem()
  } finally {
    checking.value = false
  }
}

// ====== 一键安装依赖 ======
const runInstallDependencies = async () => {
  if (installRunning.value) return
  installRunning.value = true
  installPercent.value = 0
  installStatusText.value = t('oobe.depStarting', '正在连接安装服务…')
  installSummary.value = {}
  depInstalled.value = false

  const sid = Math.random().toString(36).slice(2) + Date.now().toString(36)
  const stream = subscribeDependencyStream(sid, (evt: DepProgressEvt) => {
    if (evt.type === 'log' && evt.message) {
      const msg = evt.message.trim()
      if (!msg) return
      let level: DepLogLine['level'] = 'log'
      const lower = msg.toLowerCase()
      if (lower.startsWith('[ok]') || lower.includes('安装成功')) level = 'success'
      else if (lower.startsWith('[fail]') || lower.startsWith('[error]') || lower.includes('安装失败')) level = 'error'
      else if (lower.startsWith('[warn]')) level = 'warn'
      appendLog(msg, level)
    } else if (evt.type === 'progress') {
      const statusText = `${evt.name || '依赖'}：${evt.status || ''} — ${evt.message || ''}`
      installStatusText.value = statusText
      appendLog(`>> ${evt.name} [${evt.status}] ${evt.message}`, evt.status === 'success' ? 'success' : evt.status === 'failed' ? 'error' : evt.status === 'installing' ? 'warn' : 'log')
      const depOrder = ['uv', 'nodejs', 'pnpm', 'backend', 'frontend']
      const idx = depOrder.indexOf((evt.name || '').toLowerCase())
      if (idx >= 0) {
        const perStep = Math.floor(100 / depOrder.length)
        let base = 0
        if (evt.status === 'success') base = (idx + 1) * perStep
        else if (evt.status === 'installing') base = idx * perStep + Math.floor(perStep / 2)
        else base = idx * perStep
        installPercent.value = Math.max(installPercent.value, Math.min(99, base))
      }
    } else if (evt.type === 'done') {
      installSummary.value = evt.summary || {}
      depInstalled.value = Boolean(evt.success)
      installPercent.value = 100
      installStatusText.value = evt.success ? t('oobe.depSuccess', '全部依赖安装完成') : t('oobe.depPartFail', '部分依赖未成功，请查看日志或手动安装')
      appendLog(`--- ${installStatusText.value} ---`, evt.success ? 'success' : 'warn')
    }
  })

  try {
    appendLog('[[ 开始 Rosetta 依赖自动安装 ]]', 'warn')
    const { data, error } = await installDependencies()
    if (error.value) {
      appendLog(`安装请求失败: ${error.value?.message || error.value}`, 'error')
    } else {
      interface DepInstallResult {
        all_success?: boolean
        success?: number
        failed?: number
        skipped?: number
        total?: number
      }
      const result = (data.value as DepInstallResult) || ({} as DepInstallResult)
      if (!depInstalled.value) {
        depInstalled.value = Boolean(result.all_success)
        installSummary.value = {
          success: result.success,
          failed: result.failed,
          skipped: result.skipped,
          total: result.total
        }
        installPercent.value = 100
        installStatusText.value = depInstalled.value
          ? t('oobe.depSuccess', '全部依赖安装完成')
          : t('oobe.depPartFail', '部分依赖未成功，请查看日志或手动安装')
      }
    }
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e)
    appendLog(`依赖安装异常: ${msg}`, 'error')
  } finally {
    installRunning.value = false
    stream.close()
  }
}

const nextStep = async () => {
  if (!canNext.value) return
  stepError.value = ''
  loading.value = true
  try {
    // Step 1 → 2：强制应用后端地址（防止用户探测后改 URL 未重新探测的边界）；若 systemChecks 仍空再跑一次
    if (step.value === 1) {
      const normalized = normalizeUserApiBase(connApiUrl.value)
      if (normalized && normalized !== effectiveApiBase.value) {
        setBackendApiBase(normalized)
      }
      if (systemChecks.value.length === 0) {
        checking.value = true
        try {
          await checkSystem()
        } catch (e) {
          const msg = e instanceof Error ? e.message : String(e)
          systemChecks.value = [{
            name: '系统环境检测',
            detail: msg || '后端返回异常，请点下方「重新检测」或确认后端服务状态',
            status: 'warn',
            statusText: '需重试'
          }]
        } finally {
          checking.value = false
        }
      }
    }

    if (step.value === 2) {
      await createAdmin({
        username: adminForm.name.trim(),
        email: adminForm.email.trim(),
        password: adminForm.password,
        nickname: adminForm.name.trim(),
        bio: ''
      })
    }

    if (step.value === 3) {
      await saveSiteSettings({
        siteName: siteForm.name.trim(),
        description: siteForm.description,
        defaultLocale: siteForm.locale,
        seoKeywords: siteForm.keywords,
        siteUrl: siteForm.siteUrl.trim(),
        databaseType: siteForm.databaseType,
        dbHost: siteForm.dbHost,
        dbPort: siteForm.dbPort,
        dbName: siteForm.dbName,
        dbUser: siteForm.dbUser,
        dbPassword: siteForm.dbPassword,
        dbPath: siteForm.dbPath,
        redisEnabled: siteForm.redisEnabled,
        redisHost: siteForm.redisHost,
        redisPort: siteForm.redisPort,
        redisPassword: siteForm.redisPassword,
        environment: siteForm.environment,
        enableComments: siteForm.enableComments,
        enableRegistration: siteForm.enableRegistration,
        enableRss: siteForm.enableRss,
        enableBingWallpaper: siteForm.enableBingWallpaper,
        enablePagefindSearch: siteForm.enablePagefindSearch,
        enableEncryptedPosts: siteForm.enableEncryptedPosts,
        enableMusicPlayer: siteForm.enableMusicPlayer
      })
      // 离开 Step3 前跑一次服务端预检：把「提交后被 422 弹回」提前成「当场指出哪一格有问题」。
      // 预检是只读干跑，失败（后端未就绪）时 runPreflight 返回 true 放行，不阻断。
      const okToAdvance = await runPreflight()
      if (!okToAdvance) return
    }

    step.value++
  } catch (e) {
    console.error('OOBE step error:', e)
    const raw = (e as { data?: { message?: string }, message?: string } | null) || {}
    stepError.value = raw.data?.message || raw.message || t('oobe.stepSaveFailed', '这一步的配置未能保存，请稍后重试。')
  } finally {
    loading.value = false
  }
}

const prevStep = () => {
  if (step.value > 1) {
    step.value--
  }
  // 退回上一步时清掉上一次的失败回执，避免"改完了还挂着旧错误"
  installError.value = null
  stepError.value = ''
  // 回退到 Step≤2 时，清理之前的安装/进度残留（防止用户 4→3/4→3→2→3→4 时进度假完成/安装假运行）
  if (step.value <= 2) {
    installing.value = false
    installed.value = false
    for (const s of installStepList) {
      s.done = false
    }
    installStepIndex.value = -1
    installPercent.value = step.value === 1 ? 0 : installPercent.value
    installStepMessage.value = ''
    // R1-CEx-2：清理 SSE 快照状态 & 停止任何等待的 SSE
    if (installSnapshotState && typeof installSnapshotState.value !== 'undefined') {
      installSnapshotState.value = 'idle'
    }
    try {
      cancelInstallWatch()
    } catch {
      // 忽略：未启动安装时 cancelInstallWatch 可能为 noop
    }
    // R2-2.6：关闭 TLS 确认框
    tlsDialogOpen.value = false
  }
  if (step.value === 1) {
    installPercent.value = 0
    installStatusText.value = ''
    depInstalled.value = false
  }
}

// 安装进度回调：更新 Step4 的步骤状态（字段与 useOOBE 中 InstallProgressEvt 对齐：step_id / percent / success）
const onInstallProgress = (evt: InstallProgressEvt) => {
  if (evt.type === 'progress') {
    // 收到 SSE 事件：复位快照状态（兜底结束）
    if (installSnapshotState && typeof installSnapshotState.value !== 'undefined') {
      installSnapshotState.value = 'idle'
    }
    installStepMessage.value = evt.message || ''
    // percent 0-100 粗粒度估算 stepIndex
    const percent = typeof evt.percent === 'number' ? Math.max(0, Math.min(100, evt.percent)) : undefined
    let idx = installStepIndex.value
    if (typeof percent === 'number') {
      const estimated = Math.min(installStepList.length - 1, Math.floor((percent / 100) * installStepList.length))
      if (estimated > idx) idx = estimated
    }
    // step_id 匹配时标记完成
    if (evt.step_id) {
      const st = installStepList.find(s => s.id === evt.step_id)
      if (st && !st.done) {
        st.done = true
        const pos = installStepList.findIndex(s => s.id === evt.step_id)
        if (pos >= 0 && pos > idx) idx = pos
      }
    }
    if (idx > installStepIndex.value) installStepIndex.value = idx
    installPercent.value = typeof percent === 'number' ? percent : Math.round(((installStepIndex.value + 1) / installStepList.length) * 100)
  } else if (evt.type === 'done') {
    installStepList.forEach((s) => {
      s.done = true
    })
    installStepIndex.value = installStepList.length
    installPercent.value = 100
    installed.value = true
    installing.value = false
    if (installSnapshotState && typeof installSnapshotState.value !== 'undefined') {
      installSnapshotState.value = 'idle'
    }
  } else if (evt.type === 'error') {
    installing.value = false
    // 后端现在给结构化 error_code + hint（已脱敏），直接展示比甩整段异常可读得多
    installError.value = {
      code: evt.error_code || 'INSTALL_FAILED',
      message: evt.message || t('oobe.installFailed', '安装失败'),
      hint: evt.hint || ''
    }
    if (installSnapshotState && typeof installSnapshotState.value !== 'undefined') {
      installSnapshotState.value = 'idle'
    }
  }
}

// ===== R1-CEx-2：取消等待 / 重试 =====
const runInstallCancel = () => {
  try {
    cancelInstallWatch()
  } catch {
    // 忽略
  }
  installing.value = false
  if (installSnapshotState && typeof installSnapshotState.value !== 'undefined') {
    installSnapshotState.value = 'idle'
  }
}

const runInstallRetry = async () => {
  if (installing.value) return
  // 当前仍在 snapshot retrying / idle — 重新触发安装（幂等后端会串行化或直接 409 提前完成）
  // 同时强制切回 idle，避免 UI 卡禁用态
  if (installSnapshotState && typeof installSnapshotState.value !== 'undefined') {
    installSnapshotState.value = 'idle'
  }
  await reallyRunInstall()
}

// ===== R1-U2 / R2-2.6 / R1-CEx-2：真安装流程 =====
const reallyRunInstall = async () => {
  if (installing.value) return
  tlsDialogOpen.value = false
  installError.value = null
  installing.value = true
  installStepIndex.value = 0
  installPercent.value = 10
  installStepMessage.value = t('oobe.isStarting', '准备安装任务…')
  installStepList.forEach((s) => {
    s.done = false
  })
  if (installSnapshotState && typeof installSnapshotState.value !== 'undefined') {
    installSnapshotState.value = 'idle'
  }

  try {
    // finishOOBE(onProgress, { onCancelRequested })：SSE + 30s idleTimeout + 3 次快照轮询
    await finishOOBE(onInstallProgress, {
      onCancelRequested: () => {
        // 后端安装仍在运行时，允许用户从 UI 解除 installing 假死（不杀后端任务，由 R1-U2 幂等性保证安全）
        installing.value = false
      }
    })
    // 防御性兜底：即便上游 done 事件丢失，也按完成处理
    if (!installed.value) {
      installStepList.forEach((s) => {
        s.done = true
      })
      installStepIndex.value = installStepList.length
      installPercent.value = 100
      installed.value = true
    }
    installing.value = false
    if (installSnapshotState && typeof installSnapshotState.value !== 'undefined') {
      installSnapshotState.value = 'idle'
    }
  } catch (e) {
    console.error('finishSetup failed:', e)
    // 已被 SSE error 事件填过结构化信息就不要用原始异常覆盖；否则兜底一条通用文案
    if (!installError.value) {
      const raw = (e as { data?: { message?: string, error_code?: string, details?: { hint?: string } }, message?: string } | null) || {}
      installError.value = {
        code: raw.data?.error_code || 'INSTALL_FAILED',
        message: raw.data?.message || raw.message || t('oobe.installFailed', '安装失败'),
        hint: raw.data?.details?.hint || ''
      }
    }
    installing.value = false
    if (installSnapshotState && typeof installSnapshotState.value !== 'undefined') {
      installSnapshotState.value = 'idle'
    }
  }
}

const finishSetup = async () => {
  if (installing.value) return
  // R2-2.6：生产模式 + 明文 HTTP 提交密码 → 显式二次确认
  if (isPlaintextHttpRisk.value) {
    tlsDialogOpen.value = true
    return
  }
  // 安装前的最后一道闸门：服务端只读干跑。用户可能从 Step4 退回改过表单，
  // 所以这里必须重新跑一次，不能复用进入 Step4 时的结论。
  const ok = await runPreflight()
  if (!ok) return
  await reallyRunInstall()
}

const goAdmin = async () => {
  loading.value = true
  try {
    // 安装完成 → 清理向导期 localStorage rosetta:oobe:apiBase 覆盖
    // 之后正常走 env/同源 /api 的持久化配置真源
    try {
      clearOOBEApiBaseOverrideFromStorage()
    } catch {
      /* ignore */
    }
    resetOOBECache(true)
    try {
      await navigateTo('/admin', { replace: true })
    } catch {
      if (typeof window !== 'undefined') window.location.href = '/admin'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style>
/* ============ OOBE 背景层（跟随全局明暗主题） ============
   页面已不钉死语义令牌：工具类一律「亮色值 + dark:暗色值」双轨，由 <html>.dark 驱动。
   只有下面三个壁纸叠加层因含照片级渐变无法用 Tailwind 语义类表达，在此亮/暗各写一套。
   守卫见 tests/unit/oobeThemeScope.spec.ts。 */

/* Bing 壁纸未加载/失败时的渐变兜底：亮色浅底 + 同样三束色光，暗色深底 */
.oobe-bg-fallback {
  background:
    radial-gradient(ellipse at top, rgba(16, 185, 129, 0.18), transparent 55%),
    radial-gradient(ellipse at bottom right, rgba(20, 184, 166, 0.16), transparent 55%),
    radial-gradient(ellipse at bottom left, rgba(6, 182, 212, 0.14), transparent 55%),
    linear-gradient(135deg, #eef4f1 0%, #e7edf3 55%, #e9f2f5 100%);
}
.dark .oobe-bg-fallback {
  background:
    radial-gradient(ellipse at top, rgba(16, 185, 129, 0.25), transparent 55%),
    radial-gradient(ellipse at bottom right, rgba(20, 184, 166, 0.25), transparent 55%),
    radial-gradient(ellipse at bottom left, rgba(6, 182, 212, 0.22), transparent 55%),
    linear-gradient(135deg, #0b1020 0%, #0a0f1c 55%, #06101a 100%);
}

/* 对比度增强暗角：亮色弱一些（浅底不需要重压），暗色保持重压 */
.oobe-vignette {
  background: radial-gradient(ellipse at center, transparent 0%, rgba(0, 0, 0, 0.30) 100%);
}
.dark .oobe-vignette {
  background: radial-gradient(ellipse at center, transparent 0%, rgba(0, 0, 0, 0.55) 100%);
}

/* 40px 网格纸感：亮色用深色线，暗色用白色线 */
.oobe-grid {
  opacity: 0.10;
  background-image:
    linear-gradient(rgba(15, 23, 42, 0.55) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 23, 42, 0.55) 1px, transparent 1px);
  background-size: 40px 40px;
}
.dark .oobe-grid {
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.5) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.5) 1px, transparent 1px);
}
</style>
