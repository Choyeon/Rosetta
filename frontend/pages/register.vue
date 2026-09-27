<!--
  注册页（layout:false + ssr:false）：与 login.vue 同一套双分支外壳（极简纸面 / Bing 壁纸玻璃卡），
  onMounted 同样是 ensureLoaded() 决定拉不拉壁纸，再 authStore.initialize() 判已登录跳 /admin。
  后端 register 需要 username 而表单没有该字段：由 deriveUsername 取 email @ 前缀（清洗后 ≥2 位），
  退化用昵称（允许中日韩字符），两者都拿不到合法值时报错而不是回退邮箱原文。
  成功只 toast + navigateTo('/login')：不自动登录、也不消费 ?redirect（与登录页不对称是有意的）。
-->

<template>
  <div
    v-if="isMinimalAuth"
    class="ap-auth min-h-screen w-full bg-background text-foreground antialiased"
  >
    <!-- 极简主题纯纸面注册：装饰样式由 style.css public-auth 守卫段落消费 .ap-auth-* 类 -->
    <div class="mx-auto flex min-h-screen w-full max-w-[420px] flex-col justify-center px-5 py-14">
      <div class="mb-10 text-center">
        <NuxtLink
          to="/"
          class="ap-auth-brand inline-block text-2xl font-bold tracking-tight"
        >
          Rosetta
        </NuxtLink>
        <h1 class="ap-auth-title mt-8 text-3xl font-semibold tracking-tight">
          {{ t('auth.joinUs') }}
        </h1>
        <p class="mt-2 text-sm leading-relaxed text-muted-foreground">
          {{ t('auth.registerDesc', '创建你的 Rosetta 账户，解锁更多站点功能。') }}
        </p>
      </div>

      <div
        v-if="errorMessage"
        role="alert"
        class="ap-auth-alert mb-6 px-4 py-3 text-sm"
      >
        <div class="font-semibold">
          {{ t('auth.error') }}
        </div>
        <div class="mt-0.5 opacity-95">
          {{ errorMessage }}
        </div>
      </div>

      <form
        class="flex flex-col gap-5"
        @submit.prevent="handleRegister"
      >
        <div class="flex flex-col gap-2">
          <label
            for="nickname"
            class="ap-auth-label block text-sm font-medium"
          >{{ t('auth.nickname') }}</label>
          <input
            id="nickname"
            v-model="form.name"
            type="text"
            autocomplete="nickname"
            :placeholder="t('auth.nicknamePlaceholder')"
            class="ap-auth-input block h-11 w-full bg-transparent px-3 text-base"
          >
        </div>

        <div class="flex flex-col gap-2">
          <label
            for="email"
            class="ap-auth-label block text-sm font-medium"
          >{{ t('auth.email') }}</label>
          <input
            id="email"
            v-model="form.email"
            type="email"
            autocomplete="email"
            :placeholder="t('auth.emailPlaceholder')"
            class="ap-auth-input block h-11 w-full bg-transparent px-3 text-base"
          >
        </div>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div class="flex flex-col gap-2">
            <label
              for="password"
              class="ap-auth-label block text-sm font-medium"
            >{{ t('auth.password') }}</label>
            <div class="relative">
              <input
                id="password"
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="new-password"
                :placeholder="t('auth.passwordPlaceholder')"
                class="ap-auth-input block h-11 w-full bg-transparent px-3 pr-11 text-base"
              >
              <button
                type="button"
                class="absolute right-2 top-1/2 inline-flex min-h-[44px] min-w-[44px] -translate-y-1/2 items-center justify-center text-muted-foreground transition-colors hover:text-foreground"
                tabindex="-1"
                :title="showPassword ? t('auth.hidePassword', '隐藏密码') : t('auth.showPassword', '显示密码')"
                @click="showPassword = !showPassword"
              >
                <Eye
                  v-if="!showPassword"
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
            <label
              for="confirmPassword"
              class="ap-auth-label block text-sm font-medium"
            >{{ t('auth.confirmPassword') }}</label>
            <div class="relative">
              <input
                id="confirmPassword"
                v-model="form.confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                autocomplete="new-password"
                :placeholder="t('auth.confirmPasswordPlaceholder')"
                class="ap-auth-input block h-11 w-full bg-transparent px-3 pr-11 text-base"
              >
              <button
                type="button"
                class="absolute right-2 top-1/2 inline-flex min-h-[44px] min-w-[44px] -translate-y-1/2 items-center justify-center text-muted-foreground transition-colors hover:text-foreground"
                tabindex="-1"
                :title="showConfirmPassword ? t('auth.hidePassword', '隐藏密码') : t('auth.showPassword', '显示密码')"
                @click="showConfirmPassword = !showConfirmPassword"
              >
                <Eye
                  v-if="!showConfirmPassword"
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

        <div class="flex items-start gap-2.5">
          <input
            id="agreeTermsLabel"
            v-model="form.agreeTerms"
            type="checkbox"
            class="ap-auth-check mt-0.5 size-4 shrink-0 cursor-pointer"
          >
          <label
            for="agreeTermsLabel"
            class="cursor-pointer select-none text-sm leading-normal text-muted-foreground"
          >
            {{ t('auth.agreeTermsPrefix', '我已阅读并同意') }}
            <span class="ap-auth-link mx-1 font-semibold">
              {{ t('auth.terms', '服务条款') }}
            </span>
            {{ t('auth.agreeTermsAnd', '与') }}
            <span class="ap-auth-link mx-1 font-semibold">
              {{ t('auth.privacy', '隐私政策') }}
            </span>
          </label>
        </div>

        <button
          type="submit"
          class="ap-auth-submit mt-2 inline-flex h-11 w-full items-center justify-center gap-2 text-sm font-semibold transition-opacity disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="loading || !isFormValid"
        >
          <Loader2
            v-if="loading"
            class="size-4 animate-spin"
          />
          {{ loading ? t('auth.registering', '正在创建账户…') : t('auth.createAccount', '创建账户') }}
        </button>
      </form>

      <div class="mt-8 flex items-center justify-center text-sm">
        <span class="text-muted-foreground">{{ t('auth.hasAccount', '已有账户？') }}</span>
        <NuxtLink
          to="/login"
          class="ap-auth-link ml-1.5 font-semibold"
        >
          {{ t('auth.goLogin') }}
        </NuxtLink>
      </div>

      <div class="mt-10 text-center">
        <NuxtLink
          to="/"
          class="ap-auth-link inline-flex items-center gap-1.5 text-sm text-muted-foreground"
        >
          <ArrowLeft class="size-3.5" />
          {{ t('auth.backHome', '返回主页') }}
        </NuxtLink>
      </div>
    </div>
  </div>

  <div
    v-else
    class="min-h-screen relative overflow-hidden isolate font-sans antialiased"
  >
    <!-- 默认壁纸玻璃卡注册（非极简主题） -->
    <!-- 背景：整屏 Bing 每日壁纸（Bing/Unsplash 失败时后面的渐变兜底自动可见） -->
    <div
      class="absolute inset-0 -z-20 bg-gradient-to-br from-sky-950 via-indigo-950 to-slate-900"
    />
    <div
      class="absolute inset-0 -z-20 bg-cover bg-center bg-no-repeat transition-opacity duration-700"
      :style="wallpaperUrl ? { backgroundImage: `url(${wallpaperUrl})` } : {}"
    />
    <!-- 非常克制的暗角：只提升前景可读性，不改变壁纸本身观感 -->
    <div class="ed-auth-shade pointer-events-none absolute inset-0 -z-10" />

    <!-- 返回主页：左上角玻璃胶囊（与底部控件同质感，z-index 高于壁纸，hover 仅变色不变形） -->
    <NuxtLink
      to="/"
      class="fixed top-5 left-5 z-50 inline-flex items-center gap-2 rounded-full backdrop-blur-2xl saturate-[180%] bg-white/[0.08] border border-white/12 px-4 py-2 text-sm font-medium text-white/85 shadow-lg shadow-black/40 hover:bg-white/15 hover:border-white/20 hover:text-white transition-colors"
    >
      <ArrowLeft class="size-4" />
      {{ t('auth.backHome', '返回主页') }}
    </NuxtLink>

    <!-- 内容区：单栏居中（全尺寸都是居中，没有双栏） -->
    <div class="relative z-10 min-h-screen w-full flex flex-col items-center justify-center px-5 py-10 gap-7">
      <!-- 彩色方形 Logo（仅图标，不带文字） + 标题 -->
      <NuxtLink
        to="/"
        class="group inline-flex flex flex-col items-center gap-3 select-none"
      >
        <div class="relative">
          <div class="ed-auth-brand-glow absolute -inset-2.5 rounded-[18px] blur-xl transition-opacity group-hover:opacity-90" />
          <img
            src="/logo/rosetta-primary-icon.png"
            :alt="t('auth.logoAlt', 'Rosetta — 彩色方形 Logo')"
            class="relative h-14 w-14 object-contain drop-shadow-[0_8px_30px_rgba(0,0,0,0.55)]"
          >
        </div>
        <div class="font-display text-[26px] md:text-3xl font-bold tracking-tight text-white drop-shadow-[0_2px_10px_rgba(0,0,0,0.55)]">
          Rosetta
        </div>
      </NuxtLink>

      <!-- 欢迎语：只保留"加入我们"标题 -->
      <div class="text-center max-w-md">
        <h1 class="font-display text-3xl md:text-4xl font-bold text-white tracking-tight drop-shadow-[0_2px_12px_rgba(0,0,0,0.55)]">
          {{ t('auth.joinUs') }}
        </h1>
      </div>

      <!-- 亚克力毛玻璃注册表单 Card（无实边框版本：软玻璃质感，靠投影+渐变高光环+内阴影建立边界） -->
      <div class="w-full max-w-md relative">
        <!-- 外层柔和投影（贴近 Card 的黑色软阴影） -->
        <div
          class="ed-auth-card-shadow absolute inset-x-4 bottom-[-20px] top-[30%] rounded-[28px] blur-[36px] -z-10"
          aria-hidden="true"
        />
        <!-- 外层远距离投影（模拟悬浮于空气中的玻璃片） -->
        <div
          class="ed-auth-card-shadow-far absolute inset-x-1 bottom-[-30px] top-[20%] rounded-[28px] blur-[70px] -z-10"
          aria-hidden="true"
        />
        <div class="relative group">
          <!-- 顶部+左上的渐变高光环（替代实线 border，柔和有机） -->
          <div
            class="absolute inset-0 rounded-[28px] p-px"
            aria-hidden="true"
          >
            <div
              class="ed-auth-card-halo h-full w-full rounded-[27px] opacity-90"
            />
          </div>
          <!-- 真正的 Card 主体：无 border，靠多层阴影 + 内阴影 + 高光伪元素保持边界 -->
          <div
            class="ed-auth-card relative rounded-[27px] p-7 md:p-8 text-white"
          >
            <div class="mb-5">
              <h2 class="font-display text-2xl font-semibold tracking-tight">
                {{ t('auth.register') }}
              </h2>
              <p class="mt-1 text-sm text-white/70 leading-relaxed">
                {{ t('auth.registerDesc', '创建你的 Rosetta 账户，解锁更多站点功能。') }}
              </p>
            </div>

            <!-- 错误提示：显式红（无实 border，靠背景+内阴影+顶部高光） -->
            <div
              v-if="errorMessage"
              role="alert"
              class="ed-auth-alert mb-5 rounded-xl text-red-50 px-4 py-3 text-sm"
            >
              <div class="font-semibold text-red-100">
                {{ t('auth.error') }}
              </div>
              <div class="mt-0.5 text-red-100/95">
                {{ errorMessage }}
              </div>
            </div>

            <form
              class="flex flex-col gap-4"
              @submit.prevent="handleRegister"
            >
              <!-- 昵称 -->
              <div class="flex flex-col gap-2">
                <label
                  for="nickname"
                  class="block text-sm font-medium text-white/85"
                >{{ t('auth.nickname') }}</label>
                <div class="relative">
                  <UserRound class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-white/60" />
                  <input
                    id="nickname"
                    v-model="form.name"
                    type="text"
                    autocomplete="nickname"
                    :placeholder="t('auth.nicknamePlaceholder')"
                    class="ed-auth-glass block w-full h-11 rounded-lg pl-10 pr-3.5 text-white placeholder:text-white/40 backdrop-blur-md transition-all"
                  >
                </div>
              </div>

              <!-- 邮箱 + 用户名 -->
              <div class="flex flex-col gap-2">
                <label
                  for="email"
                  class="block text-sm font-medium text-white/85"
                >{{ t('auth.email') }}</label>
                <div class="relative">
                  <Mail class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-white/60" />
                  <input
                    id="email"
                    v-model="form.email"
                    type="email"
                    autocomplete="email"
                    :placeholder="t('auth.emailPlaceholder')"
                    class="ed-auth-glass block w-full h-11 rounded-lg pl-10 pr-3.5 text-white placeholder:text-white/40 backdrop-blur-md transition-all"
                  >
                </div>
              </div>

              <!-- 密码 + 确认密码：双列（md 以上双列，小屏单列） -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
                <div class="flex flex-col gap-2">
                  <label
                    for="password"
                    class="block text-sm font-medium text-white/85"
                  >{{ t('auth.password') }}</label>
                  <div class="relative">
                    <ShieldCheck class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-white/60" />
                    <input
                      id="password"
                      v-model="form.password"
                      :type="showPassword ? 'text' : 'password'"
                      autocomplete="new-password"
                      :placeholder="t('auth.passwordPlaceholder')"
                      class="ed-auth-glass block w-full h-11 rounded-lg pl-10 pr-11 text-white placeholder:text-white/40 backdrop-blur-md transition-all"
                    >
                    <button
                      type="button"
                      class="absolute right-2.5 top-1/2 -translate-y-1/2 inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md text-white/60 hover:text-white hover:bg-white/10 transition-colors"
                      tabindex="-1"
                      :title="showPassword ? t('auth.hidePassword', '隐藏密码') : t('auth.showPassword', '显示密码')"
                      @click="showPassword = !showPassword"
                    >
                      <Eye
                        v-if="!showPassword"
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
                  <label
                    for="confirmPassword"
                    class="block text-sm font-medium text-white/85"
                  >{{ t('auth.confirmPassword') }}</label>
                  <div class="relative">
                    <CheckCircle2 class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-white/60" />
                    <input
                      id="confirmPassword"
                      v-model="form.confirmPassword"
                      :type="showConfirmPassword ? 'text' : 'password'"
                      autocomplete="new-password"
                      :placeholder="t('auth.confirmPasswordPlaceholder')"
                      class="ed-auth-glass block w-full h-11 rounded-lg pl-10 pr-11 text-white placeholder:text-white/40 backdrop-blur-md transition-all"
                    >
                    <button
                      type="button"
                      class="absolute right-2.5 top-1/2 -translate-y-1/2 inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md text-white/60 hover:text-white hover:bg-white/10 transition-colors"
                      tabindex="-1"
                      :title="showConfirmPassword ? t('auth.hidePassword', '隐藏密码') : t('auth.showPassword', '显示密码')"
                      @click="showConfirmPassword = !showConfirmPassword"
                    >
                      <Eye
                        v-if="!showConfirmPassword"
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

              <!-- 同意条款（登录页 记住我 同等视觉层次） -->
              <div class="flex items-start gap-2.5 pt-1">
                <label
                  class="relative inline-flex items-center justify-center size-[18px] mt-0.5 rounded-[6px] transition-colors shrink-0 cursor-pointer"
                  :class="form.agreeTerms ? 'ed-auth-check-checked' : 'ed-auth-glass'"
                >
                  <input
                    id="agreeTermsLabel"
                    v-model="form.agreeTerms"
                    type="checkbox"
                    class="absolute inset-0 opacity-0 cursor-pointer"
                  >
                  <svg
                    v-if="form.agreeTerms"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="white"
                    stroke-width="3.2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    class="size-3.5 drop-shadow-[0_1px_1px_rgba(0,0,0,0.35)]"
                  >
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </label>
                <label
                  for="agreeTermsLabel"
                  class="text-sm leading-normal cursor-pointer text-white/75 select-none"
                >
                  {{ t('auth.agreeTermsPrefix', '我已阅读并同意') }}
                  <span class="mx-1 font-semibold text-sky-200 hover:text-white hover:underline underline-offset-2 cursor-pointer transition-colors">
                    {{ t('auth.terms', '服务条款') }}
                  </span>
                  {{ t('auth.agreeTermsAnd', '与') }}
                  <span class="mx-1 font-semibold text-sky-200 hover:text-white hover:underline underline-offset-2 cursor-pointer transition-colors">
                    {{ t('auth.privacy', '隐私政策') }}
                  </span>
                </label>
              </div>

              <!-- 注册按钮：白底黑字高对比，绝对可见 -->
              <button
                type="submit"
                class="ed-auth-submit relative mt-2 w-full h-11 rounded-lg font-semibold text-zinc-900 bg-white hover:bg-white/95 active:bg-white/90 transition-all disabled:opacity-60 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2"
                :disabled="loading || !isFormValid"
              >
                <Loader2
                  v-if="loading"
                  class="size-4 animate-spin"
                />
                {{ loading ? t('auth.registering', '正在创建账户…') : t('auth.createAccount', '创建账户') }}
              </button>
            </form>

            <!-- 登录跳转（无实 border-t：用渐变透明分隔条） -->
            <div class="mt-6 flex flex-col items-center justify-center text-sm">
              <div
                class="ed-auth-divider mb-4 w-full h-px opacity-80"
                aria-hidden="true"
              />
              <div class="flex items-center justify-center">
                <span class="text-white/70">{{ t('auth.hasAccount', '已有账户？') }}</span>
                <NuxtLink
                  to="/login"
                  class="ml-1.5 font-semibold text-white hover:text-sky-200 underline-offset-2 hover:underline transition-colors"
                >
                  {{ t('auth.goLogin') }}
                </NuxtLink>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部：版权胶囊 + 切壁纸控件（与登录页完全一致） -->
    <div class="fixed bottom-0 inset-x-0 z-40 flex flex-wrap items-end justify-between gap-3 p-5 md:p-6 pointer-events-none">
      <!-- Bing 版权 + 缩略图小预览。点击整张 meta 胶囊跳 Bing 官方搜索页，不提供下载按钮。 -->
      <a
        v-if="currentImage?.copyright"
        :href="getBingOfficialLink(currentImage)"
        target="_blank"
        rel="noopener noreferrer nofollow"
        class="pointer-events-auto group flex items-center gap-3 max-w-sm rounded-full backdrop-blur-2xl saturate-[180%] bg-black/40 border border-white/12 pr-4 pl-1.5 py-1.5 shadow-lg shadow-black/40 hover:bg-black/60 hover:border-white/20 transition-colors"
      >
        <span
          v-show="!thumbError"
          class="shrink-0 size-8 rounded-full overflow-hidden ring-1 ring-white/15"
          :title="currentImage?.title || 'Bing daily wallpaper'"
        >
          <img
            :src="currentThumbUrl"
            :alt="currentImage?.title || 'Bing wallpaper thumbnail'"
            class="size-full object-cover"
            loading="lazy"
            @error="thumbError = true"
          >
        </span>
        <span
          v-show="thumbError"
          class="shrink-0 size-8 rounded-full overflow-hidden ring-1 ring-white/15 bg-gradient-to-br from-sky-500/30 via-indigo-500/30 to-fuchsia-500/30 inline-flex items-center justify-center"
          :title="currentImage?.title || 'Bing daily wallpaper'"
        >
          <img
            src="/logo/rosetta-app-icon.png"
            alt="Rosetta"
            class="size-6 object-contain"
          >
        </span>
        <div class="flex items-center gap-2 min-w-0">
          <span class="shrink-0 text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-sky-400/25 text-sky-100 border border-sky-300/30">
            Bing · Daily
          </span>
          <span class="truncate text-xs text-white/90">
            {{ currentImage?.copyright }}
          </span>
        </div>
      </a>

      <!-- 切壁纸控件：8 天内切换 + 刷新当前 -->
      <div class="pointer-events-auto flex items-center gap-1 rounded-full backdrop-blur-2xl saturate-[180%] bg-white/[0.08] border border-white/12 p-1 shadow-lg shadow-black/40">
        <button
          type="button"
          class="size-8 inline-flex items-center justify-center rounded-full text-white/85 hover:bg-white/15 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          :disabled="!canGoBackward || wallpaperLoading"
          :title="t('auth.prevDay', '上一天')"
          @click="selectDay(currentIdx + 1)"
        >
          <ChevronLeft class="size-[18px]" />
        </button>
        <span class="tabular-nums px-1.5 text-xs text-white/70 min-w-[48px] text-center">
          {{ Math.min(currentIdx + 1, totalDays) }} / {{ totalDays }}
        </span>
        <button
          type="button"
          class="size-8 inline-flex items-center justify-center rounded-full text-white/85 hover:bg-white/15 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          :disabled="currentIdx === 0 || wallpaperLoading"
          :title="t('auth.nextDay', '下一天（越新）')"
          @click="selectDay(currentIdx - 1)"
        >
          <ChevronRight class="size-[18px]" />
        </button>
        <span
          class="mx-1 h-4 w-px bg-white/15"
          aria-hidden="true"
        />
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-full text-white/85 hover:bg-white/15 px-2.5 py-1 text-xs transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="wallpaperLoading"
          :title="t('auth.refreshWallpaper', '刷新当前壁纸')"
          @click="handleReloadWallpaper"
        >
          <RefreshCw
            class="size-3.5"
            :class="{ 'animate-spin': wallpaperLoading }"
          />
          <span class="hidden sm:inline">{{ t('auth.switchWallpaper', '切换壁纸') }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '~~/stores/auth'
import { useI18n } from 'vue-i18n'
import { useBingWallpaper } from '~~/composables/useBingWallpaper'
import { MINIMAL_THEME_SLUGS } from '~~/lib/rosetta-themes'
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Mail,
  ShieldCheck,
  Eye,
  EyeOff,
  UserRound,
  CheckCircle2,
  Loader2
} from '@lucide/vue'

definePageMeta({ layout: false, ssr: false })

const { t } = useI18n()
const authStore = useAuthStore()
const toast = useToast()

// 极简主题激活时切换到纯纸面注册分支（与 login.vue 一致）
const ft = useFrontendTheme()
const isMinimalAuth = computed(() => MINIMAL_THEME_SLUGS.has(ft.slug.value || ''))

const form = reactive({
  name: '',
  email: '',
  password: '',
  confirmPassword: '',
  agreeTerms: false
})

const loading = ref(false)
const errorMessage = ref('')
const showPassword = ref(false)
const showConfirmPassword = ref(false)

const isFormValid = computed(() => {
  const username = deriveUsername(form.email, form.name)
  return (
    !!username
    && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())
    && form.password.length >= 6
    && form.password === form.confirmPassword
    && form.agreeTerms
  )
})

/**
 * 从 email 或 nickname 派生出用户名（authStore.register 需要 username != email）。
 * 优先 email@前部分；若 email 前缀无效（纯特殊字符等）则退化为 cleaned nickname；
 * 两者都无法得到合法用户名时返回空字符串。
 */
function deriveUsername(email: string, nickname: string): string {
  const at = email.indexOf('@')
  if (at > 0) {
    const prefix = email.slice(0, at).trim().replace(/[^a-zA-Z0-9_.-]/g, '')
    if (prefix.length >= 2) return prefix.toLowerCase()
  }
  const cleaned = nickname.trim().replace(/[^a-zA-Z0-9\u4e00-\u9fa5_.-]/g, '')
  if (cleaned.length >= 2) return cleaned
  return ''
}

// ── Bing 每日壁纸：复用已验证可用的 useBingWallpaper（后端代理→直连→Unsplash 三重兜底）
const {
  images,
  loading: wallpaperLoading,
  currentIdx,
  currentImage,
  fetchWallpapers,
  selectDay,
  getBingOfficialLink
} = useBingWallpaper()

const wallpaperLoaded = ref(false)
const thumbError = ref(false)

// 首次进入拉取（ssr:false，客户端拉即可）
onMounted(async () => {
  // 先确定主题归属：极简激活时跳过壁纸拉取（纯纸面分支不消费 Bing 数据）
  await ft.ensureLoaded()
  if (!isMinimalAuth.value) {
    try {
      await fetchWallpapers()
    } catch {
      /* composable 内部已经做了兜底 */
    }
  }

  // 登录态检查：已登录则直接跳回后台
  await authStore.initialize()
  if (authStore.isAuthenticated) {
    navigateTo('/admin')
  }
})

const totalDays = computed(() => Math.max(1, images.value.length))
const canGoBackward = computed(() => currentIdx.value + 1 < totalDays.value)

// 最终用于背景的大图 URL
const wallpaperUrl = computed(() => {
  const img = currentImage.value
  if (!img) return ''
  return img.uhdUrl || img.fullUrl || ''
})

// 版权胶囊里的小缩略图：Bing 官方支持的尺寸；失败时 <img @error> 自动回退 logo 占位
const currentThumbUrl = computed(() => {
  const img = currentImage.value
  if (!img) return ''
  if (img.urlbase) return `https://www.bing.com${img.urlbase}_150x150.jpg`
  // Unsplash/Picsum 等源：缩宽度
  let u = img.fullUrl || img.uhdUrl || (img as unknown as { url?: string }).url
  if (!u) return ''
  if (u.includes('w=')) u = u.replace(/w=\d+/, 'w=320')
  else if (u.includes('unsplash') || u.includes('picsum')) u += (u.includes('?') ? '&' : '?') + 'w=320&q=60'
  return u
})

// 每次换图：先重置缩略图错误，再预加载背景大图避免瞬间白
watch(
  () => wallpaperUrl.value,
  (u, old) => {
    thumbError.value = false
    if (!u || u === old) return
    wallpaperLoaded.value = false
    if (import.meta.client) {
      const img = new Image()
      img.onload = () => {
        wallpaperLoaded.value = true
      }
      img.onerror = () => {
        wallpaperLoaded.value = false
      }
      img.src = u
    } else {
      wallpaperLoaded.value = true
    }
  },
  { immediate: true }
)

const handleReloadWallpaper = async () => {
  wallpaperLoaded.value = false
  try {
    await fetchWallpapers()
  } catch {
    /* ignore */
  }
}

// ── 注册 ──────────────────────────────────────────────────────
const handleRegister = async () => {
  if (!form.name.trim() || !form.email.trim() || !form.password || !form.confirmPassword) {
    toast.error(t('auth.fillRequired', '请填写所有必填项'))
    return
  }
  if (form.password !== form.confirmPassword) {
    errorMessage.value = t('auth.passwordMismatch', '两次输入的密码不一致')
    return
  }
  if (form.password.length < 6) {
    errorMessage.value = t('auth.passwordTooShort', '密码至少 6 位')
    return
  }
  if (!form.agreeTerms) {
    toast.error(t('auth.pleaseAgreeTerms', '请先勾选同意服务条款与隐私政策'))
    return
  }

  const username = deriveUsername(form.email, form.name)
  if (!username) {
    errorMessage.value = t('auth.cannotDeriveUsername', '无法从邮箱/昵称派生出合法用户名')
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    // authStore.register(username, email, password, nickname)
    await authStore.register(username, form.email.trim(), form.password, form.name.trim())
    toast.success(t('auth.registerSuccess', '账户创建成功，请使用新账户登录'))
    navigateTo('/login')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('auth.registerFailed', '注册失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>
