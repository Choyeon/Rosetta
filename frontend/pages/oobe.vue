<template>
  <div class="relative min-h-screen overflow-hidden text-foreground isolate">
    <!-- ========== 背景：Bing 每日壁纸 + 多层遮罩 ========== -->
    <div
      class="absolute inset-0 -z-20 bg-cover bg-center bg-no-repeat transition-opacity duration-700"
      :style="wallpaperLoaded ? { backgroundImage: `url(${bwp?.url})` } : {}"
    />
    <!-- 渐变兜底（Bing 壁纸未加载或失败时显示） -->
    <div class="absolute inset-0 -z-30 bg-[radial-gradient(ellipse_at_top,_theme(colors.emerald.500/0.25),_transparent_55%),radial-gradient(ellipse_at_bottom_right,_theme(colors.teal.500/0.25),_transparent_55%),radial-gradient(ellipse_at_bottom_left,_theme(colors.cyan.500/0.22),_transparent_55%),linear-gradient(135deg,_#0b1020_0%,_#0a0f1c_55%,_#06101a_100%)] -z-30" />
    <!-- 色光叠层：三束径向柔光，主色 emerald/teal/cyan（后台系统色调） -->
    <div class="pointer-events-none absolute inset-0 -z-10">
      <div class="absolute -top-40 -left-40 h-[42rem] w-[42rem] rounded-full bg-emerald-500/25 blur-[140px]" />
      <div class="absolute -bottom-40 -right-40 h-[42rem] w-[42rem] rounded-full bg-teal-500/25 blur-[140px]" />
      <div class="absolute top-1/2 left-1/2 h-[36rem] w-[36rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-cyan-500/15 blur-[140px]" />
    </div>
    <!-- 对比度增强：底部 & 顶部暗角 + 中心 40px 网格纸感 -->
    <div class="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_center,_transparent_0%,_rgba(0,0,0,0.55)_100%)]" />
    <div
      class="pointer-events-none absolute inset-0 -z-10 opacity-[0.12]"
      style="background-image: linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px); background-size: 40px 40px;"
    />

    <!-- ========== 顶部 Navbar ========== -->
    <OOBENavbar class="sticky top-0 z-40 shrink-0 bg-background/5 backdrop-blur-xl border-b border-white/5" />

    <!-- ========== 主体：两栏 ========== -->
    <div class="relative z-10 min-h-[calc(100svh-57px)] grid lg:grid-cols-[300px_1fr] gap-0">
      <!-- 侧边栏：高模糊毛玻璃 -->
      <aside class="hidden lg:flex flex flex-col border-r border-white/10 bg-white/[0.06] backdrop-blur-[28px] saturate-[200%] [@supports_not_(backdrop-filter)]:bg-zinc-900/95">
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
                'bg-emerald-500/15 text-emerald-200 ring-1 ring-emerald-400/30': step === idx + 1,
                'text-foreground/85': step !== idx + 1
              }"
            >
              <div
                class="size-8 rounded-full flex items-center justify-center shrink-0 border text-sm font-semibold transition-colors"
                :class="{
                  'border-emerald-400/60 bg-emerald-500 text-zinc-950': step > idx + 1,
                  'border-emerald-400/60 bg-emerald-500/15 text-emerald-200': step === idx + 1,
                  'border-white/10 bg-white/5 text-foreground/70': step < idx + 1
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
          <div class="relative rounded-[28px] p-7 md:p-9 bg-white/[0.07] backdrop-blur-[32px] saturate-[200%] [@supports_not_(backdrop-filter)]:bg-zinc-900/95 border border-white/10 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.65)]">
            <div class="pb-2">
              <div class="lg:hidden flex items-center gap-2 text-sm text-foreground/80 mb-4">
                <span>{{ t('oobe.step') }} {{ step }}/4</span>
              </div>
              <div class="font-display text-2xl md:text-3xl tracking-tight flex items-center gap-3 text-foreground">
                <div class="size-9 rounded-xl bg-gradient-to-br from-emerald-400/25 via-teal-400/25 to-cyan-400/25 ring-1 ring-white/10 flex items-center justify-center">
                  <component
                    :is="steps[step - 1]?.icon"
                    class="size-5 text-emerald-300"
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
                  <div class="flex flex-col gap-4 p-5 rounded-2xl border border-white/10 bg-white/[0.05]">
                    <div class="flex items-center justify-between gap-3 flex-wrap">
                      <div class="flex items-center gap-3 min-w-0">
                        <div class="size-10 rounded-xl bg-gradient-to-br from-emerald-400/25 via-teal-400/25 to-cyan-400/25 ring-1 ring-white/10 flex items-center justify-center shrink-0">
                          <Server class="size-5 text-emerald-300" />
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
                        class="text-xs !border-white/15 text-foreground/85 shrink-0"
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
                    <FieldSet class="!gap-2 p-3 rounded-xl border border-white/10 bg-white/[0.03]">
                      <FieldLegend
                        id="oobe-mode-legend"
                        class="!mb-1 !text-sm font-semibold text-foreground/90"
                      >
                        {{ t('oobe.connMode') }}
                      </FieldLegend>
                      <div class="flex items-center gap-3">
                        <div
                          class="font-semibold text-sm transition-colors select-none cursor-pointer"
                          :class="connMode === 'dev' ? 'text-emerald-200' : 'text-foreground/70'"
                          @click="onConnModeChange('dev')"
                        >
                          {{ t('oobe.connModeDev') }}
                        </div>
                        <Separator
                          orientation="vertical"
                          class="h-3.5 bg-white/15"
                        />
                        <Switch
                          id="oobe-mode-switch"
                          :model-value="connMode === 'prod'"
                          :aria-labelledby="'oobe-mode-legend'"
                          @update:model-value="switchProdMode"
                        />
                        <Separator
                          orientation="vertical"
                          class="h-3.5 bg-white/15"
                        />
                        <div
                          class="font-semibold text-sm transition-colors select-none cursor-pointer"
                          :class="connMode === 'prod' ? 'text-emerald-200' : 'text-foreground/70'"
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
                            class="bg-white/[0.04] !border-white/15 placeholder:text-foreground/40 text-foreground"
                            :class="connApiUrlInvalid ? '!border-rose-400/40 focus-visible:!ring-rose-400/40' : ''"
                            @input="resetProbeStateOnEdit"
                            @keydown.enter.prevent="runProbeBackend"
                          />
                          <p
                            class="text-[11px] mt-1.5 leading-relaxed"
                            :class="connApiUrlInvalid ? 'text-rose-300' : 'text-foreground/60'"
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
                              class="!border-white/15 aria-pressed:!bg-emerald-500/15 aria-pressed:!text-emerald-200 aria-pressed:!border-emerald-400/30"
                            >
                              :{{ p }}
                            </ToggleGroupItem>
                          </ToggleGroup>
                          <Button
                            variant="outline"
                            size="sm"
                            disabled
                            class="!border-dashed !border-white/15 text-foreground/65 hover:bg-white/10 opacity-80"
                            @click="customPortNoop"
                          >
                            {{ t('oobe.connCustomPort') }}
                          </Button>
                        </div>
                      </FieldSet>

                      <!-- 当前生效地址 -->
                      <div
                        v-if="backendProbeApplied && effectiveApiBase"
                        class="flex items-start gap-2 p-3 rounded-xl border border-emerald-400/25 bg-emerald-500/[0.06]"
                      >
                        <CheckCircle2 class="size-4 text-emerald-300 mt-0.5 shrink-0" />
                        <div class="min-w-0">
                          <div class="text-[11px] uppercase tracking-wider text-emerald-200/80">
                            {{ t('oobe.connCurrentHint') }} · {{ t('oobe.connAppliedHint') }}
                          </div>
                          <div
                            class="text-sm font-mono text-emerald-100 truncate mt-0.5"
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
                            class="!border-amber-400/30 text-amber-200"
                          >
                            <AlertTriangle data-icon="inline-start" />
                            {{ t('oobe.connProbeOOBERequired') }}
                          </Badge>
                          <Badge
                            v-else-if="backendProbeResult.oobeComplete"
                            variant="outline"
                            class="!border-emerald-400/30 text-emerald-200"
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
                          class="text-xs text-rose-200/90 leading-relaxed p-3 rounded-xl bg-rose-500/[0.08] border border-rose-400/20"
                        >
                          {{ watchProbeFailText }}
                        </div>
                        <div
                          v-if="!backendProbeResult.ok"
                          class="text-xs text-amber-200/85 flex items-center gap-1.5"
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
                    class="grid grid-cols-2 md:grid-cols-4 gap-3 p-4 rounded-2xl bg-white/[0.05] border border-white/10"
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
                      class="flex items-center justify-between p-4 rounded-2xl border border-white/10 bg-white/[0.05]"
                    >
                      <div class="flex items-center gap-3 min-w-0">
                        <div
                          class="size-9 rounded-xl flex items-center justify-center shrink-0"
                          :class="check.status === 'ok' ? 'bg-emerald-500/20 ring-1 ring-emerald-400/30' : check.status === 'warn' ? 'bg-amber-500/20 ring-1 ring-amber-400/30' : 'bg-rose-500/20 ring-1 ring-rose-400/30'"
                        >
                          <CheckCircle2
                            v-if="check.status === 'ok'"
                            class="size-4 text-emerald-300"
                          />
                          <AlertTriangle
                            v-else-if="check.status === 'warn'"
                            class="size-4 text-amber-300"
                          />
                          <XCircle
                            v-else
                            class="size-4 text-rose-300"
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
                    class="flex items-center justify-between gap-3 flex-wrap p-4 rounded-2xl border border-white/10 bg-white/[0.03]"
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
                  <div class="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/[0.05] p-4">
                    <div class="flex items-center justify-between gap-3 flex-wrap">
                      <div class="flex items-center gap-3 min-w-0">
                        <div class="size-9 rounded-xl bg-emerald-500/15 ring-1 ring-emerald-400/25 flex items-center justify-center shrink-0">
                          <Wrench class="size-4 text-emerald-300" />
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
                          class="text-xs border-white/15 text-foreground/85"
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
                      <div class="h-2 w-full rounded-full bg-white/10 overflow-hidden">
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
                          class="h-7 px-2 text-xs text-foreground/80 hover:text-foreground hover:bg-white/10"
                          @click="depLogLines = []"
                        >
                          {{ t('oobe.clearLogs', '清空') }}
                        </Button>
                      </div>
                      <div
                        ref="logBoxRef"
                        class="h-56 overflow-auto rounded-xl border border-white/10 bg-zinc-950/70 backdrop-blur text-emerald-300/90 font-mono text-xs p-3 leading-relaxed whitespace-pre-wrap break-words select-all"
                      >
                        <template v-if="depLogLines.length === 0">
                          <span class="text-zinc-500">{{ t('oobe.logsEmpty', '（等待日志输出…）') }}</span>
                        </template>
                        <div
                          v-for="(ln, i) in depLogLines"
                          :key="i"
                          :class="ln.level === 'error' ? 'text-rose-400' : ln.level === 'success' ? 'text-emerald-400' : ln.level === 'warn' ? 'text-amber-300' : ''"
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
                    <Label class="text-foreground/90">{{ t('oobe.adminName') }} *</Label>

                    <div class="relative">
                      <UserPlus class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-foreground/60" />
                      <Input
                        v-model="adminForm.name"
                        :placeholder="t('oobe.adminNamePlaceholder')"
                        class="pl-9 h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                      />
                    </div>

                    <p class="text-sm text-foreground/70">
                      {{ t('oobe.adminNameDesc') }}
                    </p>
                  </div>

                  <div class="flex flex-col gap-2">
                    <Label class="text-foreground/90">{{ t('oobe.adminEmail') }} *</Label>

                    <div class="relative">
                      <Mail class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-foreground/60" />
                      <Input
                        v-model="adminForm.email"
                        type="email"
                        :placeholder="t('oobe.adminEmailPlaceholder')"
                        class="pl-9 h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                      />
                    </div>
                  </div>

                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div class="flex flex-col gap-2">
                      <Label class="text-foreground/90">{{ t('oobe.adminPassword') }} * <span class="text-xs text-foreground/65">({{ t('oobe.adminPasswordHint') }})</span></Label>

                      <div class="relative">
                        <ShieldCheck class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-foreground/60" />
                        <Input
                          v-model="adminForm.password"
                          :type="showAdminPassword ? 'text' : 'password'"
                          :placeholder="t('oobe.adminPasswordPlaceholder')"
                          class="pl-9 pr-9 h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
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
                    </div>

                    <div class="flex flex-col gap-2">
                      <Label class="text-foreground/90">{{ t('oobe.adminConfirmPassword') }} *</Label>

                      <div class="relative">
                        <CheckCircle2 class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-foreground/60" />
                        <Input
                          v-model="adminForm.confirmPassword"
                          :type="showAdminConfirmPassword ? 'text' : 'password'"
                          :placeholder="t('oobe.adminConfirmPasswordPlaceholder')"
                          class="pl-9 pr-9 h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
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
                    </div>
                  </div>
                </div>
              </template>

              <!-- ============== Step 3: 站点 + 数据库 + 特性开关 ============== -->
              <template v-else-if="step === 3">
                <div class="flex flex-col gap-6">
                  <!-- 站点信息 -->
                  <div class="flex flex-col gap-4">
                    <div class="flex items-center gap-2 text-sm font-semibold text-foreground">
                      <Globe2 class="size-4 text-emerald-300" />
                      <span>{{ t('oobe.groupSite', '站点信息') }}</span>
                    </div>

                    <div class="flex flex-col gap-2">
                      <Label class="text-foreground/90">{{ t('oobe.siteName') }} *</Label>

                      <div class="relative">
                        <Globe2 class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-foreground/60" />
                        <Input
                          v-model="siteForm.name"
                          :placeholder="t('oobe.siteNamePlaceholder')"
                          class="pl-9 h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                        />
                      </div>
                    </div>

                    <div class="flex flex-col gap-2">
                      <Label class="text-foreground/90">{{ t('oobe.siteUrl') }} *</Label>

                      <div class="relative">
                        <LinkIcon class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-foreground/60" />
                        <Input
                          v-model="siteForm.siteUrl"
                          type="url"
                          :placeholder="t('oobe.siteUrlPlaceholder')"
                          class="pl-9 h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                        />
                      </div>

                      <p class="text-sm text-foreground/70">
                        {{ t('oobe.siteUrlDesc') }}
                      </p>
                    </div>

                    <div class="flex flex-col gap-2">
                      <Label class="text-foreground/90">{{ t('oobe.siteDescription') }}</Label>

                      <Textarea
                        v-model="siteForm.description"
                        :placeholder="t('oobe.siteDescriptionPlaceholder')"
                        rows="3"
                        class="resize-none !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                      />
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div class="flex flex-col gap-2">
                        <Label class="text-foreground/90">{{ t('oobe.defaultLanguage') }}</Label>
                        <Select v-model="siteForm.locale">
                          <SelectTrigger class="h-11 !bg-white/[0.05] !border-white/10 text-foreground focus:!ring-emerald-400/40">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent class="!bg-zinc-900/95 backdrop-blur-xl !border-white/10">
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
                        <Label class="text-foreground/90">{{ t('oobe.seoKeywords') }}</Label>

                        <div class="relative">
                          <Tag class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-foreground/60" />
                          <Input
                            v-model="siteForm.keywords"
                            :placeholder="t('oobe.seoKeywordsPlaceholder')"
                            class="pl-9 h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 环境与数据库 -->
                  <Separator class="my-1 !bg-white/10" />
                  <div class="flex flex-col gap-4">
                    <div class="flex items-center justify-between gap-3 flex-wrap">
                      <div class="flex items-center gap-2 text-sm font-semibold text-foreground">
                        <Database class="size-4 text-emerald-300" />
                        <span>{{ t('oobe.groupEnv', '运行环境与数据库') }}</span>
                      </div>
                      <div class="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          class="text-xs border-white/15 text-foreground/85"
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
                        <Label class="text-foreground/90">{{ t('oobe.dbType', '数据库类型') }}</Label>
                        <Select v-model="siteForm.databaseType">
                          <SelectTrigger class="h-11 !bg-white/[0.05] !border-white/10 text-foreground focus:!ring-emerald-400/40">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent class="!bg-zinc-900/95 backdrop-blur-xl !border-white/10">
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
                        <Label class="text-foreground/90">{{ t('oobe.redis', 'Redis 缓存') }}</Label>
                        <div class="flex items-center h-11 px-3 rounded-xl border border-white/10 bg-white/[0.05] justify-between">
                          <span class="text-sm text-foreground/75">{{ siteForm.redisEnabled ? t('oobe.on', '开启') : t('oobe.off', '关闭') }}</span>
                          <Switch v-model="siteForm.redisEnabled" />
                        </div>
                      </div>
                    </div>

                    <template v-if="siteForm.databaseType === 'postgresql'">
                      <div class="grid grid-cols-2 gap-4">
                        <div class="flex flex-col gap-2">
                          <Label class="text-foreground/90">{{ t('oobe.dbHost', '主机') }}</Label>

                          <Input
                            v-model="siteForm.dbHost"
                            class="h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="localhost"
                          />
                        </div>
                        <div class="flex flex-col gap-2">
                          <Label class="text-foreground/90">{{ t('oobe.dbPort', '端口') }}</Label>

                          <Input
                            v-model.number="siteForm.dbPort"
                            type="number"
                            class="h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="5432"
                          />
                        </div>
                        <div class="flex flex-col gap-2">
                          <Label class="text-foreground/90">{{ t('oobe.dbName', '数据库名') }}</Label>

                          <Input
                            v-model="siteForm.dbName"
                            class="h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="rosetta"
                          />
                        </div>
                        <div class="flex flex-col gap-2">
                          <Label class="text-foreground/90">{{ t('oobe.dbUser', '用户名') }}</Label>

                          <Input
                            v-model="siteForm.dbUser"
                            class="h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="postgres"
                          />
                        </div>
                        <div class="flex flex-col gap-2 col-span-2">
                          <Label class="text-foreground/90">{{ t('oobe.dbPassword', '密码') }}</Label>

                          <Input
                            v-model="siteForm.dbPassword"
                            type="password"
                            class="h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                          />
                        </div>
                      </div>
                    </template>
                    <template v-else>
                      <div class="flex flex-col gap-2">
                        <Label class="text-foreground/90">{{ t('oobe.dbPath', 'SQLite 文件路径') }}</Label>

                        <Input
                          v-model="siteForm.dbPath"
                          class="h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                          placeholder="rosetta.db"
                        />
                      </div>
                    </template>

                    <template v-if="siteForm.redisEnabled">
                      <div class="grid grid-cols-3 gap-4">
                        <div class="flex flex-col gap-2">
                          <Label class="text-foreground/90">{{ t('oobe.redisHost', 'Redis 主机') }}</Label>

                          <Input
                            v-model="siteForm.redisHost"
                            class="h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="localhost"
                          />
                        </div>
                        <div class="flex flex-col gap-2">
                          <Label class="text-foreground/90">{{ t('oobe.redisPort', '端口') }}</Label>

                          <Input
                            v-model.number="siteForm.redisPort"
                            type="number"
                            class="h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="6379"
                          />
                        </div>
                        <div class="flex flex-col gap-2">
                          <Label class="text-foreground/90">{{ t('oobe.redisPassword', '密码') }}</Label>

                          <Input
                            v-model="siteForm.redisPassword"
                            type="password"
                            class="h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                          />
                        </div>
                      </div>
                    </template>
                  </div>

                  <!-- 特性开关 -->
                  <Separator class="my-1 !bg-white/10" />
                  <div class="flex flex-col gap-4">
                    <div class="flex items-center gap-2 text-sm font-semibold text-foreground">
                      <Sparkles class="size-4 text-emerald-300" />
                      <span>{{ t('oobe.groupFeatures', '功能开关') }}</span>
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <label class="flex items-center justify-between p-3 rounded-xl border border-white/10 bg-white/[0.05] cursor-pointer hover:bg-white/[0.08] transition-colors text-foreground">
                        <div>
                          <div class="text-sm font-medium">{{ t('oobe.fComments', '评论') }}</div>
                          <div class="text-xs text-foreground/70">{{ t('oobe.fCommentsDesc', '允许访客在文章下留言') }}</div>
                        </div>
                        <Switch v-model="siteForm.enableComments" />
                      </label>
                      <label class="flex items-center justify-between p-3 rounded-xl border border-white/10 bg-white/[0.05] cursor-pointer hover:bg-white/[0.08] transition-colors text-foreground">
                        <div>
                          <div class="text-sm font-medium">{{ t('oobe.fRegister', '开放注册') }}</div>
                          <div class="text-xs text-foreground/70">{{ t('oobe.fRegisterDesc', '允许新用户自助注册（默认关）') }}</div>
                        </div>
                        <Switch v-model="siteForm.enableRegistration" />
                      </label>
                      <label class="flex items-center justify-between p-3 rounded-xl border border-white/10 bg-white/[0.05] cursor-pointer hover:bg-white/[0.08] transition-colors text-foreground">
                        <div>
                          <div class="text-sm font-medium">{{ t('oobe.fRss', 'RSS 订阅') }}</div>
                          <div class="text-xs text-foreground/70">{{ t('oobe.fRssDesc', '生成 /feed.xml 订阅源') }}</div>
                        </div>
                        <Switch v-model="siteForm.enableRss" />
                      </label>
                      <label class="flex items-center justify-between p-3 rounded-xl border border-white/10 bg-white/[0.05] cursor-pointer hover:bg-white/[0.08] transition-colors text-foreground">
                        <div>
                          <div class="text-sm font-medium">{{ t('oobe.fBing', 'Bing 每日壁纸') }}</div>
                          <div class="text-xs text-foreground/70">{{ t('oobe.fBingDesc', '首页展示 Bing 每日壁纸背景') }}</div>
                        </div>
                        <Switch v-model="siteForm.enableBingWallpaper" />
                      </label>
                      <label class="flex items-center justify-between p-3 rounded-xl border border-white/10 bg-white/[0.05] cursor-pointer hover:bg-white/[0.08] transition-colors text-foreground">
                        <div>
                          <div class="text-sm font-medium">{{ t('oobe.fPagefind', '站内搜索') }}</div>
                          <div class="text-xs text-foreground/70">{{ t('oobe.fPagefindDesc', '启用 Pagefind 客户端全文搜索') }}</div>
                        </div>
                        <Switch v-model="siteForm.enablePagefindSearch" />
                      </label>
                      <label class="flex items-center justify-between p-3 rounded-xl border border-white/10 bg-white/[0.05] cursor-pointer hover:bg-white/[0.08] transition-colors text-foreground">
                        <div>
                          <div class="text-sm font-medium">{{ t('oobe.fCrypto', '加密文章') }}</div>
                          <div class="text-xs text-foreground/70">{{ t('oobe.fCryptoDesc', '发布受密码保护的加密文章') }}</div>
                        </div>
                        <Switch v-model="siteForm.enableEncryptedPosts" />
                      </label>
                      <label class="flex items-center justify-between p-3 rounded-xl border border-white/10 bg-white/[0.05] cursor-pointer hover:bg-white/[0.08] transition-colors sm:col-span-2 text-foreground">
                        <div>
                          <div class="text-sm font-medium">{{ t('oobe.fMusic', '背景音乐播放器') }}</div>
                          <div class="text-xs text-foreground/70">{{ t('oobe.fMusicDesc', '侧边栏显示音乐播放组件（需在后台配置播放源）') }}</div>
                        </div>
                        <Switch v-model="siteForm.enableMusicPlayer" />
                      </label>
                    </div>
                  </div>
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
                      <Loader2 class="size-10 text-emerald-300 animate-spin" />
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
                    <div class="h-2.5 w-full rounded-full bg-white/10 overflow-hidden">
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
                        'bg-emerald-500/5 border-emerald-400/30': st.done,
                        'border-white/10 bg-white/[0.05]': !st.done && installStepIndex !== idx
                      }"
                    >
                      <div
                        class="size-7 rounded-full flex items-center justify-center shrink-0 text-xs font-semibold transition-colors"
                        :class="{
                          'bg-emerald-500 text-zinc-950': st.done,
                          'bg-emerald-500/15 text-emerald-200 animate-pulse ring-1 ring-emerald-400/40': installStepIndex === idx && !st.done,
                          'bg-white/10 text-foreground/70': installStepIndex !== idx && !st.done
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
                          :class="installStepIndex === idx ? 'text-emerald-200' : st.done ? 'text-foreground' : 'text-foreground/75'"
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
                      : 'border-sky-400/30 bg-sky-500/[0.06]'"
                    role="status"
                    aria-live="polite"
                  >
                    <AlertTriangle
                      data-icon="inline-start"
                      class="size-4 shrink-0 mt-0.5"
                      :class="installSnapshotState === 'timeout' ? 'text-amber-300' : 'text-sky-300'"
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
                    <CheckCircle2 class="size-10 text-emerald-300" />
                  </div>
                  <h3 class="font-display text-2xl font-bold tracking-tight mb-2 text-foreground">
                    {{ t('oobe.completeTitle') }}
                  </h3>
                  <p class="text-foreground/75 max-w-md mx-auto leading-relaxed">
                    {{ t('oobe.completeDesc') }}
                  </p>

                  <div class="mt-8 grid grid-cols-3 gap-3 max-w-lg mx-auto">
                    <div class="rounded-2xl border border-white/10 p-4 bg-white/[0.05]">
                      <div class="size-8 rounded-xl bg-emerald-500/20 ring-1 ring-emerald-400/30 flex items-center justify-center mx-auto mb-2">
                        <Settings2 class="size-4 text-emerald-300" />
                      </div>
                      <div class="text-xs font-semibold text-foreground/90">
                        {{ t('oobe.completeSummary1') }}
                      </div>
                    </div>
                    <div class="rounded-2xl border border-white/10 p-4 bg-white/[0.05]">
                      <div class="size-8 rounded-xl bg-cyan-500/20 ring-1 ring-cyan-400/30 flex items-center justify-center mx-auto mb-2">
                        <UserPlus class="size-4 text-cyan-300" />
                      </div>
                      <div class="text-xs font-semibold text-foreground/90">
                        {{ t('oobe.completeSummary2') }}
                      </div>
                    </div>
                    <div class="rounded-2xl border border-white/10 p-4 bg-white/[0.05]">
                      <div class="size-8 rounded-xl bg-teal-500/20 ring-1 ring-teal-400/30 flex items-center justify-center mx-auto mb-2">
                        <Globe2 class="size-4 text-teal-300" />
                      </div>
                      <div class="text-xs font-semibold text-foreground/90">
                        {{ t('oobe.completeSummary3') }}
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 初始进入（安装按钮） -->
                <div
                  v-else
                  class="text-center py-8"
                >
                  <div class="inline-flex items-center justify-center size-20 rounded-full bg-emerald-500/15 ring-1 ring-emerald-400/30 mb-6">
                    <Rocket class="size-10 text-emerald-300" />
                  </div>
                  <h3 class="font-display text-2xl font-bold tracking-tight mb-2 text-foreground">
                    {{ t('oobe.readyTitle', '配置已准备就绪') }}
                  </h3>
                  <p class="text-foreground/75 max-w-md mx-auto leading-relaxed">
                    {{ t('oobe.readyDesc', '点击下方按钮，系统将完成数据库初始化、写入配置并创建示例数据。整个过程大概需要 10~30 秒。') }}
                  </p>
                </div>
              </template>
            </div>

            <div class="flex justify-between pt-4">
              <Button
                v-if="step > 1 && !installing"
                variant="ghost"
                class="text-foreground/85 hover:bg-white/10 hover:text-foreground"
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
                  class="!border-white/15 bg-white/[0.04] text-foreground hover:bg-white/10 hover:text-foreground"
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
                    :disabled="installing || loading"
                    @click="finishSetup"
                  >
                    <template v-if="installing">
                      <Loader2
                        data-icon="inline-start"
                        class="mr-2 animate-spin"
                      />
                      {{ t('oobe.installingBtn', '安装中…') }}
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
         点击整张卡片跳 Bing 官方搜索页；不单独提供下载 icon 按钮（版权图由用户浏览器另存为即可）。 -->
    <a
      v-if="bwp?.copyright"
      :href="getBwpOfficialLink(bwp)"
      target="_blank"
      rel="noopener noreferrer nofollow"
      class="fixed bottom-5 left-5 z-40 group flex items-center gap-3 max-w-sm rounded-full backdrop-blur-2xl saturate-[180%] bg-white/[0.07] border border-white/10 pr-4 pl-1.5 py-1.5 shadow-lg shadow-black/40 hover:bg-white/[0.11] hover:border-white/15 transition-colors"
    >
      <div class="relative size-9 shrink-0">
        <img
          :src="thumbUrl(bwp?.url)"
          :alt="bwp?.title || ''"
          class="size-9 rounded-full object-cover ring-1 ring-white/15"
          loading="lazy"
          decoding="async"
        >
        <div class="pointer-events-none absolute inset-0 rounded-full ring-[3px] ring-white/0 group-hover:ring-white/10 transition-all" />
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
    <div class="fixed bottom-5 right-5 z-40 flex items-center gap-1 rounded-full backdrop-blur-2xl saturate-[180%] bg-white/[0.07] border border-white/10 p-1 shadow-lg shadow-black/40">
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
                class="size-5 text-amber-500"
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
                  <li class="text-rose-400/90">
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
import { computed, markRaw, nextTick, onMounted, ref } from 'vue'

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
  clearOOBEApiBaseOverrideFromStorage, installSnapshotState, cancelInstallWatch
} = oobe

// ====== Bing 每日壁纸（后台风格：emerald/teal/cyan 三束光 + 毛玻璃） ======
// —— 使用 FastAPI /api/bing/wallpapers，与 login/register 的 useBingWallpaper 同源，
//    避免 devProxy 抢走 Nitro /api/bing-wallpaper 路由导致 404。请求失败时自动回退直连 Bing，最后本地占位。
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
      // 2) 回退：直连 Bing（6s 超时）
      try {
        const ctrl = new AbortController()
        const t = setTimeout(() => ctrl.abort(), 6000)
        try {
          const r = await fetch('https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=8&mkt=zh-CN', { signal: ctrl.signal })
          if (r.ok) {
            const body = (await r.json()) as { images?: BwpImage[] }
            const arr: BwpImage[] = body?.images || []
            bwpList.value = arr.map((img: BwpImage) => {
              const u = img?.url || ''
              const ub = img?.urlbase || ''
              const full = u && !u.startsWith('http') ? `https://www.bing.com${u}` : u
              return {
                url: u,
                urlbase: ub,
                title: img?.title || '',
                copyright: img?.copyright || '',
                copyrightlink: img?.copyrightlink || '',
                startdate: img?.startdate || img?.enddate || '',
                full_url: full,
                uhd_url: ub ? `https://www.bing.com${ub}_UHD.jpg` : full
              }
            })
          }
        } finally {
          clearTimeout(t)
        }
      } catch {
        // 3) 最终本地兜底
      }
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
    const base = u.pathname.replace(/UHD\.jpg$/, '') + '_150x84.jpg'
    u.pathname = base
    return u.toString()
  } catch {
    return ''
  }
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
// OOBE 路由固定 ssr:false → 必在浏览器内。统一走 runtimeConfig.public.siteUrl → location.origin，
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

const canNext = computed(() => {
  if (step.value === 1) {
    // O 系列 Step1：必须先通过后端连接探测，其次系统检测无硬错误
    const probePassed = Boolean(backendProbeResult.value?.ok) && backendProbeApplied.value
    if (!probePassed) return false
    return systemChecks.value.length > 0 && systemChecks.value.every(c => c.status !== 'err')
  }
  if (step.value === 2) {
    return (
      adminForm.name.trim()
      && /^[A-Za-z0-9_-]{3,32}$/.test(adminForm.name.trim())
      && adminForm.email.trim()
      && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(adminForm.email.trim())
      && adminForm.password
      && adminForm.password.length >= 8
      && adminForm.password === adminForm.confirmPassword
    )
  }
  if (step.value === 3) {
    return (
      siteForm.name.trim()
      && siteForm.siteUrl.trim()
      && /^https?:\/\//.test(siteForm.siteUrl.trim())
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
    }

    step.value++
  } catch (e) {
    console.error('OOBE step error:', e)
  } finally {
    loading.value = false
  }
}

const prevStep = () => {
  if (step.value > 1) {
    step.value--
  }
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
