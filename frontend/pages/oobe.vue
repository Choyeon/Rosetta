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
      <aside class="hidden lg:flex flex-col border-r border-white/10 bg-white/[0.06] backdrop-blur-[28px] saturate-[200%] [@supports_not_(backdrop-filter)]:bg-zinc-900/95">
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

          <div class="space-y-2">
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
                <div class="space-y-5">
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
                  <div class="space-y-3">
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

                  <!-- 一键依赖安装 -->
                  <div class="rounded-2xl border border-white/10 bg-white/[0.05] p-4 space-y-3">
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
                            class="size-4 mr-2"
                          />
                          <Loader2
                            v-else
                            class="size-4 mr-2 animate-spin"
                          />
                          {{ installRunning ? t('oobe.depInstalling', '安装中…') : t('oobe.depInstallBtn', '一键安装') }}
                        </Button>
                      </div>
                    </div>

                    <!-- 进度条 -->
                    <div
                      v-if="installRunning || depInstalled"
                      class="space-y-1"
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
                      class="space-y-2"
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
                  <div class="space-y-2">
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

                  <div class="space-y-2">
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
                    <div class="space-y-2">
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

                    <div class="space-y-2">
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
                  <div class="space-y-4">
                    <div class="flex items-center gap-2 text-sm font-semibold text-foreground">
                      <Globe2 class="size-4 text-emerald-300" />
                      <span>{{ t('oobe.groupSite', '站点信息') }}</span>
                    </div>

                    <div class="space-y-2">
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

                    <div class="space-y-2">
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

                    <div class="space-y-2">
                      <Label class="text-foreground/90">{{ t('oobe.siteDescription') }}</Label>

                      <Textarea
                        v-model="siteForm.description"
                        :placeholder="t('oobe.siteDescriptionPlaceholder')"
                        rows="3"
                        class="resize-none !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                      />
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div class="space-y-2">
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

                      <div class="space-y-2">
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
                  <div class="space-y-4">
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
                      <div class="space-y-2">
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
                      <div class="space-y-2">
                        <Label class="text-foreground/90">{{ t('oobe.redis', 'Redis 缓存') }}</Label>
                        <div class="flex items-center h-11 px-3 rounded-xl border border-white/10 bg-white/[0.05] justify-between">
                          <span class="text-sm text-foreground/75">{{ siteForm.redisEnabled ? t('oobe.on', '开启') : t('oobe.off', '关闭') }}</span>
                          <Switch v-model="siteForm.redisEnabled" />
                        </div>
                      </div>
                    </div>

                    <template v-if="siteForm.databaseType === 'postgresql'">
                      <div class="grid grid-cols-2 gap-4">
                        <div class="space-y-2">
                          <Label class="text-foreground/90">{{ t('oobe.dbHost', '主机') }}</Label>

                          <Input
                            v-model="siteForm.dbHost"
                            class="h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="localhost"
                          />
                        </div>
                        <div class="space-y-2">
                          <Label class="text-foreground/90">{{ t('oobe.dbPort', '端口') }}</Label>

                          <Input
                            v-model.number="siteForm.dbPort"
                            type="number"
                            class="h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="5432"
                          />
                        </div>
                        <div class="space-y-2">
                          <Label class="text-foreground/90">{{ t('oobe.dbName', '数据库名') }}</Label>

                          <Input
                            v-model="siteForm.dbName"
                            class="h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="rosetta"
                          />
                        </div>
                        <div class="space-y-2">
                          <Label class="text-foreground/90">{{ t('oobe.dbUser', '用户名') }}</Label>

                          <Input
                            v-model="siteForm.dbUser"
                            class="h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="postgres"
                          />
                        </div>
                        <div class="space-y-2 col-span-2">
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
                      <div class="space-y-2">
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
                        <div class="space-y-2">
                          <Label class="text-foreground/90">{{ t('oobe.redisHost', 'Redis 主机') }}</Label>

                          <Input
                            v-model="siteForm.redisHost"
                            class="h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="localhost"
                          />
                        </div>
                        <div class="space-y-2">
                          <Label class="text-foreground/90">{{ t('oobe.redisPort', '端口') }}</Label>

                          <Input
                            v-model.number="siteForm.redisPort"
                            type="number"
                            class="h-11 !bg-white/[0.05] !border-white/10 focus-visible:!ring-emerald-400/40 text-foreground placeholder:text-foreground/45"
                            placeholder="6379"
                          />
                        </div>
                        <div class="space-y-2">
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
                  <div class="space-y-4">
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
                  class="space-y-5 py-2"
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

                  <div class="space-y-2">
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
                  <div class="space-y-2">
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
                <ArrowLeft class="size-4 mr-2" />
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
                    class="size-4 mr-2 animate-spin"
                  />
                  <RefreshCw
                    v-else
                    class="size-4 mr-2"
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
                  <ArrowRight class="size-4 ml-2" />
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
                      <Loader2 class="size-4 mr-2 animate-spin" />
                      {{ t('oobe.installingBtn', '安装中…') }}
                    </template>
                    <template v-else>
                      <Rocket class="size-4 mr-2" />
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
                    <CheckCircle2 class="size-4 mr-2" />
                    {{ t('oobe.enterAdmin') }}
                  </Button>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== 左下角：版权 Meta 胶囊 ========== -->
    <a
      v-if="bwp?.copyright"
      :href="bwp?.copyrightLink || 'https://www.bing.com'"
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
  ExternalLink
} from '@lucide/vue'
import { markRaw, nextTick, onBeforeUnmount, onMounted } from 'vue'

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
const { systemChecks, systemSummary, loading, checkSystem, createAdmin, saveSiteSettings, finishOOBE, getOOBEStatus, installDependencies, subscribeDependencyStream } = oobe

// 品牌色：OOBE 向导强制移除用户自定义调色板类（保持 emerald 主色系统）
const PALETTE_RE = /^palette-/
let removedPaletteClass: string | null = null
onMounted(() => {
  if (typeof document === 'undefined') return
  const classes = Array.from(document.documentElement.classList)
  for (const cls of classes) {
    if (PALETTE_RE.test(cls)) {
      removedPaletteClass = cls
      document.documentElement.classList.remove(cls)
    }
  }
})
onBeforeUnmount(() => {
  if (typeof document === 'undefined') return
  if (removedPaletteClass) {
    document.documentElement.classList.add(removedPaletteClass)
    removedPaletteClass = null
  }
})

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
  // 首次进入 step1：自动跑一次系统检测
  try {
    checking.value = true
    await checkSystem()
  } catch {
    /* 系统检测失败不阻断向导 */
  } finally {
    checking.value = false
  }
})

const steps = [
  {
    title: t('oobe.step1Title'),
    desc: t('oobe.step1Desc'),
    longDesc: t('oobe.step1LongDesc'),
    icon: markRaw(Settings2)
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

const defaultOrigin = typeof location !== 'undefined' ? location.origin : 'http://localhost:3000'
const { locale: currentLocale } = useI18n()
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
  siteUrl: defaultOrigin,
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

const canNext = computed(() => {
  if (step.value === 1) {
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
}

// 安装进度回调：更新 Step4 的步骤状态（字段与 useOOBE 中 InstallProgressEvt 对齐：step_id / percent / success）
const onInstallProgress = (evt: InstallProgressEvt) => {
  if (evt.type === 'progress') {
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
  } else if (evt.type === 'error') {
    installing.value = false
  }
}

const finishSetup = async () => {
  if (installing.value) return
  installing.value = true
  installStepIndex.value = 0
  installPercent.value = 10
  installStepMessage.value = t('oobe.isStarting', '准备安装任务…')
  installStepList.forEach((s) => {
    s.done = false
  })

  try {
    // finishOOBE(onProgress)：异步回调 SSE 进度，最终 Promise<Record<string, unknown> | null>
    await finishOOBE(onInstallProgress)
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
  } catch (e) {
    console.error('finishSetup failed:', e)
    installing.value = false
  }
}

const goAdmin = async () => {
  loading.value = true
  try {
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
