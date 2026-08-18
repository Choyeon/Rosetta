<template>
  <div class="min-h-screen relative overflow-hidden isolate font-sans antialiased">
    <!-- 背景层：Bing 每日壁纸（加载失败回退渐变色，支持明/暗主题） -->
    <div
      class="absolute inset-0 -z-20 bg-cover bg-center bg-no-repeat transition-opacity duration-700"
      :style="wallpaperLoaded ? { backgroundImage: `url(${bwp?.url})` } : {}"
    />
    <div
      v-if="!wallpaperLoaded || !bwp"
      class="absolute inset-0 -z-20 bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900"
    />

    <!-- 多层叠加：渐变光晕 + 暗角 + 颗粒 -->
    <div class="pointer-events-none absolute inset-0 -z-10 mix-blend-normal">
      <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(14,165,233,0.28),transparent_55%)]" />
      <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_right,rgba(99,102,241,0.25),transparent_55%)]" />
      <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-black/10 dark:from-black/75 dark:via-black/35 dark:to-black/20" />
      <div class="absolute inset-0 [background-image:linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] [background-size:40px_40px] [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]" />
    </div>

    <!-- 主体：大屏双栏，移动端单栏竖排 -->
    <div class="relative z-10 min-h-screen grid lg:grid-cols-2">
      <!-- 左栏：品牌 / 标语 / 徽章 / 引言 -->
      <div class="hidden lg:flex flex-col justify-between p-12 xl:p-16 text-white">
        <NuxtLink
          to="/"
          class="inline-flex items-center gap-3 font-display text-2xl font-bold tracking-tight"
        >
          <img
            src="/logo/rosetta-monochrome-icon.png"
            alt="Rosetta"
            class="size-7 object-contain drop-shadow-[0_0_12px_rgba(14,165,233,0.35)]"
          >
          <span class="bg-clip-text text-transparent bg-gradient-to-br from-white via-white to-white/70">
            Rosetta
          </span>
        </NuxtLink>

        <div class="relative max-w-lg">
          <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/8 text-white/80 text-xs backdrop-blur-md border border-white/10 mb-8">
            <span class="size-1.5 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.9)]" />
            Nuxt 4 · FastAPI · 渐进式 SSR
          </div>
          <h1 class="font-display text-5xl xl:text-6xl font-bold leading-[1.05] tracking-tight">
            <span class="block">{{ t('auth.welcomeBack') }}</span>
            <span
              class="mt-4 block bg-clip-text text-transparent bg-gradient-to-r from-sky-300 via-indigo-200 to-fuchsia-300"
            >
              {{ t('auth.welcomeBackTagline', '穿越语言的边界') }}
            </span>
          </h1>
          <p class="mt-6 text-white/70 text-lg leading-relaxed max-w-md">
            {{ t('auth.welcomeBackDesc') }}
          </p>

          <div class="mt-12 flex flex-wrap gap-2">
            <Badge
              variant="outline"
              class="bg-white/8 text-white border-white/12 hover:bg-white/12 backdrop-blur-md"
            >
              Vue 3.5
            </Badge>
            <Badge
              variant="outline"
              class="bg-white/8 text-white border-white/12 hover:bg-white/12 backdrop-blur-md"
            >
              Nuxt 4
            </Badge>
            <Badge
              variant="outline"
              class="bg-white/8 text-white border-white/12 hover:bg-white/12 backdrop-blur-md"
            >
              Tailwind CSS
            </Badge>
            <Badge
              variant="outline"
              class="bg-white/8 text-white border-white/12 hover:bg-white/12 backdrop-blur-md"
            >
              shadcn-vue
            </Badge>
          </div>
        </div>

        <!-- 引言卡片：轻度毛玻璃 -->
        <div class="relative max-w-md">
          <div class="rounded-3xl p-6 border border-white/10 bg-white/6 backdrop-blur-xl shadow-2xl shadow-black/40">
            <div class="border-l-2 border-sky-300/50 pl-5 py-1">
              <p class="text-white/85 italic leading-relaxed text-[15px]">
                "{{ t('auth.testimonial') }}"
              </p>
              <div class="flex items-center gap-3 mt-5">
                <Avatar class="size-10 border border-white/15 bg-gradient-to-br from-sky-400/70 to-indigo-500/70">
                  <AvatarFallback class="bg-transparent text-white">
                    Z
                  </AvatarFallback>
                </Avatar>
                <div>
                  <div class="font-semibold text-sm text-white">
                    {{ t('auth.testimonialAuthor') }}
                  </div>
                  <div class="text-xs text-white/55">
                    {{ t('auth.testimonialRole') }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右栏：登录 Card（高模糊毛玻璃） -->
      <div class="flex items-center justify-center p-6 lg:p-12">
        <div class="w-full max-w-md relative">
          <!-- 移动端品牌位 -->
          <div class="lg:hidden flex items-center justify-center gap-2 font-display text-2xl font-bold mb-8 text-white">
            <img
              src="/logo/rosetta-monochrome-icon.png"
              alt="Rosetta"
              class="size-7 object-contain"
            >
            <span>Rosetta</span>
          </div>

          <div
            class="relative rounded-[28px] p-[1px] bg-gradient-to-br from-white/25 via-white/10 to-white/5 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.6)]"
          >
            <div class="rounded-[27px] p-7 md:p-9 bg-white/[0.08] text-foreground backdrop-blur-[32px] saturate-[200%] [@supports_not_(backdrop-filter)]:bg-white/95 border border-white/10">
              <CardHeader class="pb-3 px-0">
                <CardTitle class="text-2xl md:text-[26px] font-display tracking-tight text-white">
                  {{ t('auth.login') }}
                </CardTitle>
                <CardDescription class="mt-1.5 text-white/65">
                  {{ t('auth.loginDesc') }}
                </CardDescription>
              </CardHeader>

              <CardContent class="px-0">
                <Alert
                  v-if="errorMessage"
                  variant="destructive"
                  class="mb-5 bg-red-500/15 border-red-400/25 text-red-50 backdrop-blur-md [&_svg]:text-red-200"
                >
                  <AlertTitle>{{ t('auth.error') }}</AlertTitle>
                  <AlertDescription>{{ errorMessage }}</AlertDescription>
                </Alert>

                <form
                  class="flex flex-col gap-4"
                  @submit.prevent="handleLogin"
                >
                  <div class="space-y-2">
                    <Label for="username" class="text-white/80">{{ t('auth.usernameOrEmail') }}</Label>
                    <div class="relative">
                      <Mail class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-white/55" />
                      <Input
                        id="username"
                        v-model="form.username"
                        type="text"
                        autocomplete="username"
                        :placeholder="t('auth.usernamePlaceholder')"
                        class="pl-9 h-11 bg-white/[0.07] border-white/12 text-white placeholder:text-white/35 focus-visible:ring-sky-300/50 focus-visible:border-sky-300/40 backdrop-blur-md"
                      />
                    </div>
                  </div>

                  <div class="space-y-2">
                    <Label for="password" class="text-white/80">{{ t('auth.password') }}</Label>
                    <div class="relative">
                      <ShieldCheck class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-white/55" />
                      <Input
                        id="password"
                        v-model="form.password"
                        :type="showPassword ? 'text' : 'password'"
                        :placeholder="t('auth.passwordPlaceholder')"
                        class="pl-9 pr-9 h-11 bg-white/[0.07] border-white/12 text-white placeholder:text-white/35 focus-visible:ring-sky-300/50 focus-visible:border-sky-300/40 backdrop-blur-md"
                      />
                      <button
                        type="button"
                        class="absolute right-3 top-1/2 -translate-y-1/2 text-white/55 hover:text-white transition-colors"
                        tabindex="-1"
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

                  <div class="flex justify-between items-center mt-1">
                    <div class="flex items-center gap-2">
                      <Checkbox
                        id="remember"
                        v-model="form.rememberMe"
                        class="border-white/20 data-[state=checked]:bg-sky-400/60 data-[state=checked]:text-white data-[state=checked]:border-transparent"
                      />
                      <Label
                        for="remember"
                        class="text-sm cursor-pointer text-white/75"
                      >{{ t('auth.rememberMe') }}</Label>
                    </div>
                    <span
                      class="text-sm text-white/55 cursor-not-allowed select-none"
                      :title="t('auth.forgotPasswordDisabled', '忘记密码功能暂未开放，请联系管理员')"
                      aria-disabled="true"
                    >
                      {{ t('auth.forgotPassword') }}
                    </span>
                  </div>

                  <Button
                    type="submit"
                    class="w-full mt-4 h-11 bg-white text-slate-900 hover:bg-white/90 shadow-lg shadow-sky-900/20 backdrop-blur-none"
                    :disabled="loading"
                  >
                    <Loader2
                      v-if="loading"
                      class="size-4 animate-spin mr-2"
                    />
                    {{ loading ? t('auth.loggingIn') : t('auth.login') }}
                  </Button>
                </form>
              </CardContent>

              <CardFooter class="flex justify-center pt-1 pb-0 px-0 text-sm text-white/65">
                <span>{{ t('auth.noAccount') }}</span>
                <NuxtLink
                  to="/register"
                  class="ml-1.5 font-medium text-white hover:text-sky-200 hover:underline underline-offset-2 transition-colors"
                >
                  {{ t('auth.goRegister') }}
                </NuxtLink>
              </CardFooter>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部：版权 + 换壁纸控件 -->
    <div class="absolute bottom-0 inset-x-0 z-20 flex flex-wrap items-end justify-between gap-3 p-5 md:p-7 pointer-events-none">
      <!-- Bing 版权元数据 -->
      <div
        v-if="bwp?.copyright"
        class="pointer-events-auto flex items-center gap-2.5 rounded-full pl-2 pr-4 py-1.5 bg-black/40 text-white/85 text-xs backdrop-blur-2xl border border-white/10 max-w-full shadow-lg shadow-black/30"
      >
        <a
          :href="bwp?.copyrightLink || 'https://www.bing.com'"
          target="_blank"
          rel="noreferrer"
          class="size-5 rounded-full overflow-hidden shrink-0 ring-1 ring-white/20"
          :title="bwp?.title || 'Bing daily wallpaper'"
        >
          <img
            :src="thumbUrl"
            :alt="bwp?.title || 'Bing wallpaper thumbnail'"
            class="size-full object-cover"
            loading="lazy"
          >
        </a>
        <span class="truncate max-w-[72vw] md:max-w-md">{{ bwp?.copyright }}</span>
      </div>

      <!-- 换壁纸（在可用归档 8 天范围内切换） -->
      <div class="pointer-events-auto flex items-center gap-2 rounded-full bg-white/[0.08] text-white/80 text-xs backdrop-blur-2xl border border-white/10 pl-1 pr-3 py-1 shadow-lg shadow-black/30">
        <button
          class="size-7 rounded-full flex items-center justify-center hover:bg-white/15 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          :disabled="wallpaperIdx >= (bwp?.totalDays ?? 8) - 1 || wallpaperPending"
          @click="cycleWallpaper(+1)"
          title="上一天"
        >
          <ChevronLeft class="size-4" />
        </button>
        <span class="tabular-nums px-1 text-white/60">
          {{ (wallpaperIdx ?? 0) + 1 }} / {{ bwp?.totalDays ?? 8 }}
        </span>
        <button
          class="size-7 rounded-full flex items-center justify-center hover:bg-white/15 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          :disabled="(wallpaperIdx ?? 0) === 0 || wallpaperPending"
          @click="cycleWallpaper(-1)"
          title="下一天（越新）"
        >
          <ChevronRight class="size-4" />
        </button>
        <span class="mx-1 h-3 w-px bg-white/15" />
        <button
          class="inline-flex items-center gap-1.5 rounded-full hover:bg-white/10 px-2 py-1 -mr-2 transition-colors disabled:opacity-40"
          :disabled="wallpaperPending"
          @click="reloadWallpaper()"
          title="刷新当前壁纸"
        >
          <RefreshCw
            class="size-3.5"
            :class="{ 'animate-spin': wallpaperPending }"
          />
          <span class="hidden sm:inline">{{ t('auth.switchWallpaper', '切换壁纸') }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
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
import { Checkbox } from '~~/components/ui/checkbox'
import { Label } from '~~/components/ui/label'
import {
  Alert,
  AlertDescription,
  AlertTitle
} from '~~/components/ui/alert'
import { Badge } from '~~/components/ui/badge'
import { Avatar, AvatarFallback } from '~~/components/ui/avatar'
import { useAuthStore } from '~~/stores/auth'
import { useI18n } from 'vue-i18n'
import {
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Mail,
  ShieldCheck,
  Eye,
  EyeOff,
  Loader2
} from '@lucide/vue'

definePageMeta({ layout: false, ssr: false })

interface BingWallpaper {
  url: string
  title: string
  copyright: string
  copyrightLink: string
  startDate: string
  idx: number
  totalDays: number
}

const route = useRoute()
const { t } = useI18n()
const authStore = useAuthStore()

const form = reactive({
  username: '',
  password: '',
  rememberMe: false
})

const loading = ref(false)
const errorMessage = ref('')
const showPassword = ref(false)
const toast = useToast()

/** 仅接受站内相对路径：以单个 '/' 开头，排除 '//'（协议相对）与 '/\' */
const safeRedirect = (raw: unknown): string => {
  if (typeof raw !== 'string') return '/admin'
  if (!raw.startsWith('/') || raw.startsWith('//') || raw.startsWith('/\\')) return '/admin'
  return raw
}

// ── Bing 每日壁纸：BFF /bing-wallpaper ──────────────────────────
const wallpaperIdx = ref(0)
const wallpaperLoaded = ref(false)
const wallpaperPending = ref(false)

const {
  data: bwp,
  refresh: refreshWallpaper,
  pending: fetchPending
} = await useFetch<BingWallpaper>('/api/bing-wallpaper', {
  // 登录页 ssr: false，保持 immediate=true 在客户端首帧触发即可
  query: computed(() => ({ idx: wallpaperIdx.value, mkt: 'zh-CN' })),
  key: computed(() => `bwp:${wallpaperIdx.value}`),
  server: false,
  default: () => null as unknown as BingWallpaper,
  lazy: false,
  watch: [wallpaperIdx]
})

// 当 fetchPending 改变时更新 pending 按钮状态
watchEffect(() => { wallpaperPending.value = !!fetchPending.value })

// 图片 URL 预加载：避免切换瞬间闪白
watch(
  () => bwp.value?.url,
  (u) => {
    if (!u) return
    const img = new Image()
    img.onload = () => { wallpaperLoaded.value = true }
    img.onerror = () => { wallpaperLoaded.value = false }
    img.src = u
  },
  { immediate: true }
)

// 缩略图版权条小预览：把 UHD 替换成 150x84，体积很小
const thumbUrl = computed(() => {
  if (!bwp.value?.url) return ''
  return bwp.value.url.replace('_UHD.jpg', '_150x84.jpg').replace('_UHD.jpeg', '_150x84.jpeg')
})

const cycleWallpaper = (step: -1 | 1) => {
  const total = bwp.value?.totalDays ?? 8
  const next = wallpaperIdx.value + (step * -1) // idx=0 最新，越大越旧
  wallpaperIdx.value = Math.max(0, Math.min(total - 1, next))
  wallpaperLoaded.value = false
}

const reloadWallpaper = () => {
  wallpaperLoaded.value = false
  refreshWallpaper().catch(() => {})
}

// ── 登录 ──────────────────────────────────────────────────────
const handleLogin = async () => {
  if (!form.username.trim() || !form.password) {
    toast.error(t('auth.fillRequired', '请填写用户名和密码'))
    return
  }
  loading.value = true
  errorMessage.value = ''

  try {
    await authStore.login(form.username.trim(), form.password)
    navigateTo(safeRedirect(route.query.redirect))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('auth.loginFailed', '登录失败')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await authStore.initialize()
  if (authStore.isAuthenticated) {
    navigateTo('/admin')
  }
})
</script>
