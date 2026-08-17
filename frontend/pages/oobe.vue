<template>
  <div class="min-h-screen bg-muted/30 flex flex-col">
    <OOBENavbar class="sticky top-0 z-50 shrink-0" />
    <div class="flex-1 grid lg:grid-cols-[280px_1fr]">
      <aside class="hidden lg:flex flex-col border-r bg-background">
        <div class="p-8 flex flex-col gap-8 flex-1">
          <NuxtLink
            to="/"
            class="inline-flex items-center gap-2 font-display text-xl font-bold tracking-tight"
          >
            <img
              src="/logo/rosetta-primary-icon.png"
              alt="Rosetta"
              class="size-6 object-contain"
            >
            <span>Rosetta</span>
          </NuxtLink>

          <div class="space-y-2">
            <div
              v-for="(s, idx) in steps"
              :key="idx"
              class="flex items-center gap-3 p-3 rounded-xl transition-colors"
              :class="{
                'bg-primary/10 text-primary': step === idx + 1,
                'text-muted-foreground': step !== idx + 1
              }"
            >
              <div
                class="size-8 rounded-full flex items-center justify-center shrink-0 border text-sm font-semibold transition-colors"
                :class="{
                  'border-primary bg-primary text-primary-foreground': step > idx + 1,
                  'border-primary bg-primary/10 text-primary': step === idx + 1,
                  'border-border bg-background text-muted-foreground': step < idx + 1
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

          <div class="mt-auto text-xs text-muted-foreground leading-relaxed">
            <p>{{ t('oobe.sidebarHint1') }}</p>
            <p class="mt-1">
              {{ t('oobe.sidebarHint2') }}
            </p>
          </div>
        </div>
      </aside>

      <div class="p-6 lg:p-12 flex items-start justify-center">
        <Card class="w-full max-w-3xl shadow-xl border-0">
          <CardHeader class="pb-2">
            <div class="lg:hidden flex items-center gap-2 text-sm text-muted-foreground mb-4">
              <span>{{ t('oobe.step') }} {{ step }}/4</span>
            </div>
            <CardTitle class="font-display text-2xl md:text-3xl tracking-tight flex items-center gap-3">
              <component
                :is="steps[step - 1]?.icon"
                class="size-7 text-primary"
              />
              {{ t('oobe.stepN', { n: step, total: 4 }) }}：{{ steps[step - 1]?.title }}
            </CardTitle>
            <CardDescription class="mt-2">
              {{ steps[step - 1]?.longDesc }}
            </CardDescription>
          </CardHeader>

          <CardContent class="pt-6">
            <!-- ============== Step 1: 系统环境 + 依赖安装 ============== -->
            <template v-if="step === 1">
              <div class="space-y-5">
                <!-- 问题4：更丰富的系统摘要卡片（OS / CPU / 内存 / 磁盘 / Python） -->
                <div
                  v-if="systemSummary && typeof systemSummary === 'object'"
                  class="grid grid-cols-2 md:grid-cols-4 gap-3 p-4 rounded-xl bg-muted/30 border border-border/60"
                >
                  <div>
                    <div class="text-[10px] uppercase tracking-wider text-muted-foreground">
                      {{ t('oobe.envOS') }}
                    </div>
                    <div
                      class="text-sm font-medium mt-0.5 truncate"
                      :title="`${systemSummary?.osName ?? ''} (${systemSummary?.osVersion ?? ''})`"
                    >
                      {{ systemSummary?.osName || '—' }}
                    </div>
                    <div class="text-[11px] text-muted-foreground mt-0.5 truncate">
                      {{ systemSummary?.architecture || '—' }} · {{ systemSummary?.hostname || '—' }}
                    </div>
                  </div>
                  <div>
                    <div class="text-[10px] uppercase tracking-wider text-muted-foreground">
                      {{ t('oobe.envCPU') }}
                    </div>
                    <div class="text-sm font-medium mt-0.5">
                      {{ systemSummary?.cpuCount ?? '?' }} {{ t('oobe.envCores') }}
                    </div>
                    <div
                      class="text-[11px] text-muted-foreground mt-0.5 truncate"
                      :title="systemSummary?.processor || ''"
                    >
                      {{ systemSummary?.processor || '—' }}
                    </div>
                  </div>
                  <div>
                    <div class="text-[10px] uppercase tracking-wider text-muted-foreground">
                      {{ t('oobe.envMemory') }}
                    </div>
                    <div class="text-sm font-medium mt-0.5">
                      {{ systemSummary?.totalMemoryGB || '—' }}
                    </div>
                    <div class="text-[11px] text-muted-foreground mt-0.5">
                      {{ t('oobe.envAvail') }}: {{ systemSummary?.availableMemoryGB || '—' }}
                    </div>
                  </div>
                  <div>
                    <div class="text-[10px] uppercase tracking-wider text-muted-foreground">
                      {{ t('oobe.envDisk') }}
                    </div>
                    <div class="text-sm font-medium mt-0.5">
                      {{ systemSummary?.totalDiskGB || '—' }}
                    </div>
                    <div class="text-[11px] text-muted-foreground mt-0.5">
                      {{ t('oobe.envFree') }}: {{ systemSummary?.freeDiskGB || '—' }} · Py{{ systemSummary?.pythonVersion || '—' }}
                    </div>
                  </div>
                </div>

                <!-- 检测结果 -->
                <div class="space-y-3">
                  <div
                    v-for="check in systemChecks"
                    :key="check.name"
                    class="flex items-center justify-between p-4 rounded-xl border bg-background"
                  >
                    <div class="flex items-center gap-3 min-w-0">
                      <div
                        class="size-9 rounded-lg flex items-center justify-center shrink-0"
                        :class="check.status === 'ok' ? 'bg-success-muted' : check.status === 'warn' ? 'bg-warning-muted' : 'bg-error-muted'"
                      >
                        <CheckCircle2
                          v-if="check.status === 'ok'"
                          class="size-4 text-success"
                        />
                        <AlertTriangle
                          v-else-if="check.status === 'warn'"
                          class="size-4 text-warning"
                        />
                        <XCircle
                          v-else
                          class="size-4 text-error"
                        />
                      </div>
                      <div class="min-w-0">
                        <div class="font-semibold text-sm">
                          {{ check.name }}
                        </div>
                        <div class="text-xs text-muted-foreground truncate">
                          {{ check.detail }}
                        </div>
                      </div>
                    </div>
                    <Badge
                      :variant="check.status === 'ok' ? 'default' : check.status === 'warn' ? 'secondary' : 'destructive'"
                      class="shrink-0"
                      :class="check.status === 'ok' ? 'bg-success hover:bg-success' : ''"
                    >
                      {{ check.statusText }}
                    </Badge>
                  </div>
                  <div
                    v-if="systemChecks.length === 0"
                    class="p-8 text-center text-sm text-muted-foreground"
                  >
                    <img
                      src="/logo/rosetta-primary-icon.png"
                      alt=""
                      class="size-6 mx-auto mb-2 opacity-70"
                    >
                    {{ t('oobe.step1EmptyHint') }}
                  </div>
                </div>

                <!-- 一键依赖安装（对标 WordPress） -->
                <div class="rounded-xl border bg-background p-4 space-y-3">
                  <div class="flex items-center justify-between gap-3 flex-wrap">
                    <div class="flex items-center gap-3 min-w-0">
                      <div class="size-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                        <Wrench class="size-4 text-primary" />
                      </div>
                      <div class="min-w-0">
                        <div class="font-semibold text-sm">
                          {{ t('oobe.depInstallTitle', '一键安装依赖') }}
                        </div>
                        <div class="text-xs text-muted-foreground truncate">
                          {{ t('oobe.depInstallDesc', '自动安装 uv / Node.js / pnpm 与项目依赖（uv sync + pnpm install）') }}
                        </div>
                      </div>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                      <Badge
                        variant="outline"
                        class="text-xs"
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
                    <div class="h-2 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        class="h-full rounded-full bg-primary transition-all duration-500"
                        :style="{ width: `${installPercent}%` }"
                      />
                    </div>
                    <div class="text-xs text-muted-foreground flex items-center gap-2">
                      <span>{{ installStatusText }}</span>
                      <span
                        v-if="installSummary.success !== undefined"
                        class="ml-auto"
                      >
                        {{ t('oobe.depSummary', { s: installSummary.success ?? 0, f: installSummary.failed ?? 0 }) }}
                      </span>
                    </div>
                  </div>

                  <!-- 日志终端（对标 WordPress Installation Details） -->
                  <div
                    v-if="depLogLines.length || installRunning"
                    class="space-y-2"
                  >
                    <div class="flex items-center justify-between">
                      <div class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                        {{ t('oobe.logs', '安装日志') }}
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        class="h-7 px-2 text-xs"
                        @click="depLogLines = []"
                      >
                        {{ t('oobe.clearLogs', '清空') }}
                      </Button>
                    </div>
                    <div
                      ref="logBoxRef"
                      class="h-56 overflow-auto rounded-lg border bg-zinc-950 text-emerald-300/90 font-mono text-xs p-3 leading-relaxed whitespace-pre-wrap break-words select-all"
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
                  <Label>{{ t('oobe.adminName') }} *</Label>

                  <div class="relative">
                    <UserPlus class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                    <Input
                      v-model="adminForm.name"
                      :placeholder="t('oobe.adminNamePlaceholder')"
                      class="pl-9 h-11"
                    />
                  </div>

                  <p class="text-sm text-muted-foreground">
                    {{ t('oobe.adminNameDesc') }}
                  </p>
                </div>

                <div class="space-y-2">
                  <Label>{{ t('oobe.adminEmail') }} *</Label>

                  <div class="relative">
                    <Mail class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                    <Input
                      v-model="adminForm.email"
                      type="email"
                      :placeholder="t('oobe.adminEmailPlaceholder')"
                      class="pl-9 h-11"
                    />
                  </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div class="space-y-2">
                    <Label>{{ t('oobe.adminPassword') }} * <span class="text-xs text-muted-foreground">({{ t('oobe.adminPasswordHint') }})</span></Label>

                    <div class="relative">
                      <ShieldCheck class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                      <Input
                        v-model="adminForm.password"
                        :type="showAdminPassword ? 'text' : 'password'"
                        :placeholder="t('oobe.adminPasswordPlaceholder')"
                        class="pl-9 pr-9 h-11"
                      />
                      <button
                        type="button"
                        class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
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
                    <Label>{{ t('oobe.adminConfirmPassword') }} *</Label>

                    <div class="relative">
                      <CheckCircle2 class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                      <Input
                        v-model="adminForm.confirmPassword"
                        :type="showAdminConfirmPassword ? 'text' : 'password'"
                        :placeholder="t('oobe.adminConfirmPasswordPlaceholder')"
                        class="pl-9 pr-9 h-11"
                      />
                      <button
                        type="button"
                        class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
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

            <!-- ============== Step 3: 站点 + 数据库 + 特性开关（对标 WordPress 配置页） ============== -->
            <template v-else-if="step === 3">
              <div class="flex flex-col gap-6">
                <!-- 站点信息 -->
                <div class="space-y-4">
                  <div class="flex items-center gap-2 text-sm font-semibold text-foreground">
                    <Globe2 class="size-4 text-primary" />
                    <span>{{ t('oobe.groupSite', '站点信息') }}</span>
                  </div>

                  <div class="space-y-2">
                    <Label>{{ t('oobe.siteName') }} *</Label>

                    <div class="relative">
                      <Globe2 class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                      <Input
                        v-model="siteForm.name"
                        :placeholder="t('oobe.siteNamePlaceholder')"
                        class="pl-9 h-11"
                      />
                    </div>
                  </div>

                  <div class="space-y-2">
                    <Label>{{ t('oobe.siteUrl') }} *</Label>

                    <div class="relative">
                      <LinkIcon class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                      <Input
                        v-model="siteForm.siteUrl"
                        type="url"
                        :placeholder="t('oobe.siteUrlPlaceholder')"
                        class="pl-9 h-11"
                      />
                    </div>

                    <p class="text-sm text-muted-foreground">
                      {{ t('oobe.siteUrlDesc') }}
                    </p>
                  </div>

                  <div class="space-y-2">
                    <Label>{{ t('oobe.siteDescription') }}</Label>

                    <Textarea
                      v-model="siteForm.description"
                      :placeholder="t('oobe.siteDescriptionPlaceholder')"
                      rows="3"
                      class="resize-none"
                    />
                  </div>

                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div class="space-y-2">
                      <Label>{{ t('oobe.defaultLanguage') }}</Label>
                      <Select v-model="siteForm.locale">
                        <SelectTrigger class="h-11">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
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
                      <Label>{{ t('oobe.seoKeywords') }}</Label>

                      <div class="relative">
                        <Tag class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                        <Input
                          v-model="siteForm.keywords"
                          :placeholder="t('oobe.seoKeywordsPlaceholder')"
                          class="pl-9 h-11"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 环境与数据库 -->
                <Separator class="my-1" />
                <div class="space-y-4">
                  <div class="flex items-center justify-between gap-3 flex-wrap">
                    <div class="flex items-center gap-2 text-sm font-semibold text-foreground">
                      <Database class="size-4 text-primary" />
                      <span>{{ t('oobe.groupEnv', '运行环境与数据库') }}</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <Badge
                        variant="outline"
                        class="text-xs"
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
                      <Label>{{ t('oobe.dbType', '数据库类型') }}</Label>
                      <Select v-model="siteForm.databaseType">
                        <SelectTrigger class="h-11">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
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
                        class="text-sm text-muted-foreground"
                      >
                        {{ t('oobe.sqliteHint', '适合单机/演示，零配置即用') }}
                      </p>
                      <p
                        v-else
                        class="text-sm text-muted-foreground"
                      >
                        {{ t('oobe.pgHint', '推荐生产环境使用，需填写下方连接信息') }}
                      </p>
                    </div>
                    <div class="space-y-2">
                      <Label>{{ t('oobe.redis', 'Redis 缓存') }}</Label>
                      <div class="flex items-center h-11 px-3 border rounded-xl justify-between">
                        <span class="text-sm text-muted-foreground">{{ siteForm.redisEnabled ? t('oobe.on', '开启') : t('oobe.off', '关闭') }}</span>
                        <Switch v-model="siteForm.redisEnabled" />
                      </div>
                    </div>
                  </div>

                  <template v-if="siteForm.databaseType === 'postgresql'">
                    <div class="grid grid-cols-2 gap-4">
                      <div class="space-y-2">
                        <Label>{{ t('oobe.dbHost', '主机') }}</Label>

                        <Input
                          v-model="siteForm.dbHost"
                          class="h-11"
                          placeholder="localhost"
                        />
                      </div>
                      <div class="space-y-2">
                        <Label>{{ t('oobe.dbPort', '端口') }}</Label>

                        <Input
                          v-model.number="siteForm.dbPort"
                          type="number"
                          class="h-11"
                          placeholder="5432"
                        />
                      </div>
                      <div class="space-y-2">
                        <Label>{{ t('oobe.dbName', '数据库名') }}</Label>

                        <Input
                          v-model="siteForm.dbName"
                          class="h-11"
                          placeholder="rosetta"
                        />
                      </div>
                      <div class="space-y-2">
                        <Label>{{ t('oobe.dbUser', '用户名') }}</Label>

                        <Input
                          v-model="siteForm.dbUser"
                          class="h-11"
                          placeholder="postgres"
                        />
                      </div>
                      <div class="space-y-2 col-span-2">
                        <Label>{{ t('oobe.dbPassword', '密码') }}</Label>

                        <Input
                          v-model="siteForm.dbPassword"
                          type="password"
                          class="h-11"
                        />
                      </div>
                    </div>
                  </template>
                  <template v-else>
                    <div class="space-y-2">
                      <Label>{{ t('oobe.dbPath', 'SQLite 文件路径') }}</Label>

                      <Input
                        v-model="siteForm.dbPath"
                        class="h-11"
                        placeholder="rosetta.db"
                      />
                    </div>
                  </template>

                  <template v-if="siteForm.redisEnabled">
                    <div class="grid grid-cols-3 gap-4">
                      <div class="space-y-2">
                        <Label>{{ t('oobe.redisHost', 'Redis 主机') }}</Label>

                        <Input
                          v-model="siteForm.redisHost"
                          class="h-11"
                          placeholder="localhost"
                        />
                      </div>
                      <div class="space-y-2">
                        <Label>{{ t('oobe.redisPort', '端口') }}</Label>

                        <Input
                          v-model.number="siteForm.redisPort"
                          type="number"
                          class="h-11"
                          placeholder="6379"
                        />
                      </div>
                      <div class="space-y-2">
                        <Label>{{ t('oobe.redisPassword', '密码') }}</Label>

                        <Input
                          v-model="siteForm.redisPassword"
                          type="password"
                          class="h-11"
                        />
                      </div>
                    </div>
                  </template>
                </div>

                <!-- 特性开关 -->
                <Separator class="my-1" />
                <div class="space-y-4">
                  <div class="flex items-center gap-2 text-sm font-semibold text-foreground">
                    <Sparkles class="size-4 text-primary" />
                    <span>{{ t('oobe.groupFeatures', '功能开关') }}</span>
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <label class="flex items-center justify-between p-3 rounded-xl border bg-background cursor-pointer hover:bg-muted/30 transition-colors">
                      <div>
                        <div class="text-sm font-medium">{{ t('oobe.fComments', '评论') }}</div>
                        <div class="text-xs text-muted-foreground">{{ t('oobe.fCommentsDesc', '允许访客在文章下留言') }}</div>
                      </div>
                      <Switch v-model="siteForm.enableComments" />
                    </label>
                    <label class="flex items-center justify-between p-3 rounded-xl border bg-background cursor-pointer hover:bg-muted/30 transition-colors">
                      <div>
                        <div class="text-sm font-medium">{{ t('oobe.fRegister', '开放注册') }}</div>
                        <div class="text-xs text-muted-foreground">{{ t('oobe.fRegisterDesc', '允许新用户自助注册（默认关）') }}</div>
                      </div>
                      <Switch v-model="siteForm.enableRegistration" />
                    </label>
                    <label class="flex items-center justify-between p-3 rounded-xl border bg-background cursor-pointer hover:bg-muted/30 transition-colors">
                      <div>
                        <div class="text-sm font-medium">{{ t('oobe.fRss', 'RSS 订阅') }}</div>
                        <div class="text-xs text-muted-foreground">{{ t('oobe.fRssDesc', '生成 /feed.xml 订阅源') }}</div>
                      </div>
                      <Switch v-model="siteForm.enableRss" />
                    </label>
                    <label class="flex items-center justify-between p-3 rounded-xl border bg-background cursor-pointer hover:bg-muted/30 transition-colors">
                      <div>
                        <div class="text-sm font-medium">{{ t('oobe.fBing', 'Bing 每日壁纸') }}</div>
                        <div class="text-xs text-muted-foreground">{{ t('oobe.fBingDesc', '首页展示 Bing 每日壁纸背景') }}</div>
                      </div>
                      <Switch v-model="siteForm.enableBingWallpaper" />
                    </label>
                    <label class="flex items-center justify-between p-3 rounded-xl border bg-background cursor-pointer hover:bg-muted/30 transition-colors">
                      <div>
                        <div class="text-sm font-medium">{{ t('oobe.fPagefind', '站内搜索') }}</div>
                        <div class="text-xs text-muted-foreground">{{ t('oobe.fPagefindDesc', '启用 Pagefind 客户端全文搜索') }}</div>
                      </div>
                      <Switch v-model="siteForm.enablePagefindSearch" />
                    </label>
                    <label class="flex items-center justify-between p-3 rounded-xl border bg-background cursor-pointer hover:bg-muted/30 transition-colors">
                      <div>
                        <div class="text-sm font-medium">{{ t('oobe.fCrypto', '加密文章') }}</div>
                        <div class="text-xs text-muted-foreground">{{ t('oobe.fCryptoDesc', '发布受密码保护的加密文章') }}</div>
                      </div>
                      <Switch v-model="siteForm.enableEncryptedPosts" />
                    </label>
                    <label class="flex items-center justify-between p-3 rounded-xl border bg-background cursor-pointer hover:bg-muted/30 transition-colors sm:col-span-2">
                      <div>
                        <div class="text-sm font-medium">{{ t('oobe.fMusic', '背景音乐播放器') }}</div>
                        <div class="text-xs text-muted-foreground">{{ t('oobe.fMusicDesc', '侧边栏显示音乐播放组件（需在后台配置播放源）') }}</div>
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
                  <div class="inline-flex items-center justify-center size-20 rounded-full bg-primary/10 mb-6">
                    <Loader2 class="size-10 text-primary animate-spin" />
                  </div>
                  <h3 class="font-display text-2xl font-bold tracking-tight mb-2">
                    {{ t('oobe.installing', '正在配置您的站点…') }}
                  </h3>
                  <p class="text-muted-foreground max-w-md mx-auto leading-relaxed">
                    {{ installStepMessage || t('oobe.installingDesc', '数据库初始化、写入配置、创建示例数据，请稍候。') }}
                  </p>
                </div>

                <div class="space-y-2">
                  <div class="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{{ t('oobe.totalProgress', '总体进度') }}</span>
                    <span>{{ installPercent }}%</span>
                  </div>
                  <div class="h-2.5 w-full rounded-full bg-muted overflow-hidden">
                    <div
                      class="h-full rounded-full bg-gradient-to-r from-primary via-primary/90 to-accent transition-all duration-500 relative"
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
                      'bg-primary/5 border-primary/40': installStepIndex === idx,
                      'bg-success-muted/40 border-success/30': st.done,
                      'bg-background': !st.done && installStepIndex !== idx
                    }"
                  >
                    <div
                      class="size-7 rounded-full flex items-center justify-center shrink-0 text-xs font-semibold transition-colors"
                      :class="{
                        'bg-success text-success-foreground': st.done,
                        'bg-primary text-primary-foreground animate-pulse': installStepIndex === idx && !st.done,
                        'bg-muted text-muted-foreground': installStepIndex !== idx && !st.done
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
                        :class="installStepIndex === idx ? 'text-primary' : st.done ? 'text-foreground' : 'text-muted-foreground'"
                      >
                        {{ st.label }}
                      </div>
                      <div
                        v-if="installStepIndex === idx && installStepMessage"
                        class="text-xs text-muted-foreground truncate mt-0.5"
                      >
                        {{ installStepMessage }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 安装完成：WordPress Success Screen -->
              <div
                v-else-if="installed"
                class="text-center py-6 animate-in fade-in"
              >
                <div class="inline-flex items-center justify-center size-20 rounded-full bg-success-muted dark:bg-success-muted mb-6">
                  <CheckCircle2 class="size-10 text-success" />
                </div>
                <h3 class="font-display text-2xl font-bold tracking-tight mb-2">
                  {{ t('oobe.completeTitle') }}
                </h3>
                <p class="text-muted-foreground max-w-md mx-auto leading-relaxed">
                  {{ t('oobe.completeDesc') }}
                </p>

                <div class="mt-8 grid grid-cols-3 gap-3 max-w-lg mx-auto">
                  <div class="rounded-xl border p-4 bg-background">
                    <div class="size-8 rounded-lg bg-success-muted flex items-center justify-center mx-auto mb-2">
                      <Settings2 class="size-4 text-success" />
                    </div>
                    <div class="text-xs font-semibold">
                      {{ t('oobe.completeSummary1') }}
                    </div>
                  </div>
                  <div class="rounded-xl border p-4 bg-background">
                    <div class="size-8 rounded-lg bg-accent flex items-center justify-center mx-auto mb-2">
                      <UserPlus class="size-4 text-primary" />
                    </div>
                    <div class="text-xs font-semibold">
                      {{ t('oobe.completeSummary2') }}
                    </div>
                  </div>
                  <div class="rounded-xl border p-4 bg-background">
                    <div class="size-8 rounded-lg bg-warning-muted flex items-center justify-center mx-auto mb-2">
                      <Globe2 class="size-4 text-warning" />
                    </div>
                    <div class="text-xs font-semibold">
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
                <div class="inline-flex items-center justify-center size-20 rounded-full bg-accent mb-6">
                  <Rocket class="size-10 text-primary" />
                </div>
                <h3 class="font-display text-2xl font-bold tracking-tight mb-2">
                  {{ t('oobe.readyTitle', '配置已准备就绪') }}
                </h3>
                <p class="text-muted-foreground max-w-md mx-auto leading-relaxed">
                  {{ t('oobe.readyDesc', '点击下方按钮，系统将完成数据库初始化、写入配置并创建示例数据。整个过程大概需要 10~30 秒。') }}
                </p>
              </div>
            </template>
          </CardContent>

          <CardFooter class="flex justify-between pt-2">
            <Button
              v-if="step > 1 && !installing"
              variant="ghost"
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
                  :loading="loading"
                  @click="goAdmin"
                >
                  <CheckCircle2 class="size-4 mr-2" />
                  {{ t('oobe.enterAdmin') }}
                </Button>
              </template>
            </div>
          </CardFooter>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import OOBENavbar from '~~/components/OOBENavbar.vue'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from '~~/components/ui/card'
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
  Rocket
} from '@lucide/vue'
import { markRaw, nextTick, onBeforeUnmount, onMounted } from 'vue'

definePageMeta({ layout: false })

const { t } = useI18n()
const oobe = useOOBE()
const { systemChecks, systemSummary, loading, checkSystem, createAdmin, saveSiteSettings, finishOOBE, getOOBEStatus, installDependencies, subscribeDependencyStream } = oobe

// 问题3修复：OOBE 向导强制使用全局语义化默认天青色调色板，
// 避免 html.palette-purple 等用户偏好覆盖品牌主题色（安装向导属于品牌露出场景）
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
    // 不做解构 + 全程可选链，避免任何层级为 null 时出现 "reading 'value'"
    const result = await getOOBEStatus()
    const payload = result?.data?.value as { oobe_complete?: boolean } | null | undefined
    if (payload?.oobe_complete === true) {
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
  // 首次进入 step1：自动跑一次系统检测，免用户手点
  try {
    checking.value = true
    // checkSystem() 内部并行拉了 systemSummary（若返回 null 也没事，模板全加了可选链）
    await checkSystem()
  } catch {
    /* 系统检测失败不阻断向导，交给 UI 上的"警告"显示 */
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

// ====== 一键安装依赖 (对标 WordPress) ======
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
      // 根据日志内容判断级别
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
      // 进度条：按步骤粗略估算
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

// 安装进度回调：更新 Step4 的步骤状态
const onInstallProgress = (evt: InstallProgressEvt) => {
  if (evt.type === 'progress') {
    installStepMessage.value = evt.message || ''
    const idx = installStepList.findIndex(s => s.id === evt.step_id)
    if (idx >= 0) {
      // 之前的步骤标记 done，当前索引高亮
      installStepList.forEach((s, i) => {
        if (i < idx) {
          s.done = true
        }
      })
      installStepIndex.value = idx
    }
    if (typeof evt.percent === 'number') installPercent.value = evt.percent
  } else if (evt.type === 'done') {
    installStepList.forEach(s => (s.done = true))
    installStepIndex.value = installStepList.length
    installPercent.value = 100
    installStepMessage.value = t('oobe.isDoneMsg', '安装完成，欢迎使用 Rosetta！')
  } else if (evt.type === 'error') {
    installStepMessage.value = evt.message || t('oobe.isError', '安装失败，请查看浏览器控制台')
  }
}

const finishSetup = async () => {
  if (installing.value) return
  installing.value = true
  installed.value = false
  installPercent.value = 0
  installStepIndex.value = 0
  installStepList.forEach(s => (s.done = false))
  installStepMessage.value = t('oobe.isStarting', '准备写入配置…')

  try {
    await finishOOBE(onInstallProgress)
    // 兜底：再标记一次
    installStepList.forEach(s => (s.done = true))
    installPercent.value = 100
    installed.value = true
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e)
    console.error('OOBE finish error:', e)
    installed.value = false
    installStepMessage.value = `${t('oobe.installFailed', '安装失败')}：${msg}`
    alert(`${t('oobe.installFailed', '安装失败')}：${msg}`)
  } finally {
    installing.value = false
    loading.value = false
  }
}

const goAdmin = async () => {
  loading.value = true
  try {
    // 问题1修复：navigateTo 需要 await；若路由失败（如中间件 redirect），
    // 再 fallback 到硬跳转 window.location，保证点击一定有响应。
    // 安装完成后刷新页面一次，让中间件 & settings 重新加载新写入的配置。
    try {
      await navigateTo('/admin', { replace: true })
    } catch (navErr) {
      console.warn('[OOBE] navigateTo /admin 失败，fallback 硬跳转:', navErr)
      window.location.href = '/admin'
    }
    // 兜底：如果 500ms 后仍在当前页（某些 Nuxt 路由模式下 navigateTo 不抛错也不跳转），则硬跳
    await new Promise(resolve => setTimeout(resolve, 500))
    if (typeof window !== 'undefined' && window.location.pathname === '/oobe') {
      window.location.href = '/admin'
    }
  } catch (e) {
    console.error('[OOBE] goAdmin 异常:', e)
    if (typeof window !== 'undefined') {
      window.location.href = '/admin'
    }
  } finally {
    loading.value = false
  }
}
</script>
