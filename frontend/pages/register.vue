<template>
  <div class="min-h-screen relative overflow-hidden isolate font-sans antialiased">
    <!-- 背景层 -->
    <div
      class="absolute inset-0 -z-20 bg-cover bg-center bg-no-repeat transition-opacity duration-700"
      :style="wallpaperLoaded ? { backgroundImage: `url(${bwp?.url})` } : {}"
    />
    <div
      v-if="!wallpaperLoaded || !bwp"
      class="absolute inset-0 -z-20 bg-gradient-to-br from-slate-900 via-purple-950 to-slate-900"
    />

    <!-- 叠加层 -->
    <div class="pointer-events-none absolute inset-0 -z-10 mix-blend-normal">
      <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(168,85,247,0.30),transparent_55%)]" />
      <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(236,72,153,0.22),transparent_55%)]" />
      <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-black/10 dark:from-black/75 dark:via-black/35 dark:to-black/20" />
      <div class="absolute inset-0 [background-image:linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] [background-size:40px_40px] [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]" />
    </div>

    <div class="relative z-10 min-h-screen grid lg:grid-cols-2">
      <!-- 左栏：品牌 + 卖点 -->
      <div class="hidden lg:flex flex-col justify-between p-12 xl:p-16 text-white">
        <NuxtLink
          to="/"
          class="inline-flex items-center gap-3 font-display text-2xl font-bold tracking-tight"
        >
          <img
            src="/logo/rosetta-monochrome-icon.png"
            alt="Rosetta"
            class="size-7 object-contain drop-shadow-[0_0_12px_rgba(168,85,247,0.45)]"
          >
          <span class="bg-clip-text text-transparent bg-gradient-to-br from-white via-white to-white/70">
            Rosetta
          </span>
        </NuxtLink>

        <div class="relative max-w-md">
          <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/8 text-white/80 text-xs backdrop-blur-md border border-white/10 mb-8">
            <span class="size-1.5 rounded-full bg-fuchsia-400 shadow-[0_0_10px_rgba(232,121,249,0.9)]" />
            {{ t('auth.openBeta', '开放 Beta 注册') }}
          </div>
          <h1 class="font-display text-5xl xl:text-6xl font-bold leading-[1.05] tracking-tight">
            <span class="block">{{ t('auth.joinUs') }}</span>
            <span class="mt-4 block bg-clip-text text-transparent bg-gradient-to-r from-fuchsia-300 via-purple-200 to-sky-300">
              {{ t('auth.joinUsTagline', '多语言内容，一处汇聚') }}
            </span>
          </h1>
          <p class="mt-6 text-white/70 leading-relaxed">
            {{ t('auth.joinUsDesc') }}
          </p>

          <div class="mt-12 space-y-4">
            <div class="flex items-center gap-3 p-3 rounded-2xl bg-white/6 border border-white/10 backdrop-blur-xl">
              <div class="size-9 rounded-xl bg-primary/30 flex items-center justify-center shrink-0">
                <UserPlus class="size-4 text-primary/90" />
              </div>
              <div>
                <div class="font-semibold text-sm text-white/95">
                  {{ t('auth.feature1') }}
                </div>
                <div class="text-xs text-white/60">
                  {{ t('auth.feature1Desc') }}
                </div>
              </div>
            </div>
            <div class="flex items-center gap-3 p-3 rounded-2xl bg-white/6 border border-white/10 backdrop-blur-xl">
              <div class="size-9 rounded-xl bg-primary/30 flex items-center justify-center shrink-0">
                <Palette class="size-4 text-primary/90" />
              </div>
              <div>
                <div class="font-semibold text-sm text-white/95">
                  {{ t('auth.feature2') }}
                </div>
                <div class="text-xs text-white/60">
                  {{ t('auth.feature2Desc') }}
                </div>
              </div>
            </div>
            <div class="flex items-center gap-3 p-3 rounded-2xl bg-white/6 border border-white/10 backdrop-blur-xl">
              <div class="size-9 rounded-xl bg-success/30 flex items-center justify-center shrink-0">
                <Globe2 class="size-4 text-success/90" />
              </div>
              <div>
                <div class="font-semibold text-sm text-white/95">
                  {{ t('auth.feature3') }}
                </div>
                <div class="text-xs text-white/60">
                  {{ t('auth.feature3Desc') }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="relative text-xs text-white/50">
          © {{ new Date().getFullYear() }} Rosetta. {{ t('auth.rightsReserved') }}
        </div>
      </div>

      <!-- 右栏：注册 Card（毛玻璃） -->
      <div class="flex items-center justify-center p-6 lg:p-12">
        <div class="w-full max-w-md relative">
          <div class="lg:hidden flex items-center justify-center gap-2 font-display text-2xl font-bold mb-8 text-white">
            <img
              src="/logo/rosetta-monochrome-icon.png"
              alt="Rosetta"
              class="size-7 object-contain"
            >
            <span>Rosetta</span>
          </div>

          <div class="relative rounded-[28px] p-[1px] bg-gradient-to-br from-white/25 via-white/10 to-white/5 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.6)]">
            <div class="rounded-[27px] p-7 md:p-9 bg-white/[0.08] backdrop-blur-[32px] saturate-[200%] [@supports_not_(backdrop-filter)]:bg-white/95 border border-white/10">
              <CardHeader class="pb-2 px-0">
                <CardTitle class="text-2xl md:text-[26px] font-display tracking-tight text-white">
                  {{ t('auth.register') }}
                </CardTitle>
                <CardDescription class="mt-1.5 text-white/65">
                  {{ t('auth.registerDesc') }}
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

                <div class="flex flex-col gap-4">
                  <div class="space-y-2">
                    <Label for="nickname" class="text-white/80">{{ t('auth.nickname') }}</Label>
                    <div class="relative">
                      <UserPlus class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-white/55" />
                      <Input
                        id="nickname"
                        v-model="form.name"
                        type="text"
                        :placeholder="t('auth.nicknamePlaceholder')"
                        class="pl-9 h-11 bg-white/[0.07] border-white/12 text-white placeholder:text-white/35 focus-visible:ring-fuchsia-300/50 focus-visible:border-fuchsia-300/40 backdrop-blur-md"
                      />
                    </div>
                  </div>

                  <div class="space-y-2">
                    <Label for="email" class="text-white/80">{{ t('auth.email') }}</Label>
                    <div class="relative">
                      <Mail class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-white/55" />
                      <Input
                        id="email"
                        v-model="form.email"
                        type="email"
                        :placeholder="t('auth.emailPlaceholder')"
                        class="pl-9 h-11 bg-white/[0.07] border-white/12 text-white placeholder:text-white/35 focus-visible:ring-fuchsia-300/50 focus-visible:border-fuchsia-300/40 backdrop-blur-md"
                      />
                    </div>
                  </div>

                  <div class="grid grid-cols-2 gap-3">
                    <div class="space-y-2">
                      <Label for="password" class="text-white/80">{{ t('auth.password') }}</Label>
                      <div class="relative">
                        <ShieldCheck class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-white/55" />
                        <Input
                          id="password"
                          v-model="form.password"
                          :type="showPassword ? 'text' : 'password'"
                          :placeholder="t('auth.passwordPlaceholder')"
                          class="pl-9 pr-9 h-11 bg-white/[0.07] border-white/12 text-white placeholder:text-white/35 focus-visible:ring-fuchsia-300/50 focus-visible:border-fuchsia-300/40 backdrop-blur-md"
                        />
                        <button
                          type="button"
                          class="absolute right-3 top-1/2 -translate-y-1/2 text-white/55 hover:text-white transition-colors"
                          tabindex="-1"
                          @click="showPassword = !showPassword"
                        >
                          <Eye v-if="!showPassword" class="size-4" />
                          <EyeOff v-else class="size-4" />
                        </button>
                      </div>
                    </div>

                    <div class="space-y-2">
                      <Label for="confirmPassword" class="text-white/80">{{ t('auth.confirmPassword') }}</Label>
                      <div class="relative">
                        <CheckCircle2 class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-white/55" />
                        <Input
                          id="confirmPassword"
                          v-model="form.confirmPassword"
                          :type="showConfirmPassword ? 'text' : 'password'"
                          :placeholder="t('auth.confirmPasswordPlaceholder')"
                          class="pl-9 pr-9 h-11 bg-white/[0.07] border-white/12 text-white placeholder:text-white/35 focus-visible:ring-fuchsia-300/50 focus-visible:border-fuchsia-300/40 backdrop-blur-md"
                        />
                        <button
                          type="button"
                          class="absolute right-3 top-1/2 -translate-y-1/2 text-white/55 hover:text-white transition-colors"
                          tabindex="-1"
                          @click="showConfirmPassword = !showConfirmPassword"
                        >
                          <Eye v-if="!showConfirmPassword" class="size-4" />
                          <EyeOff v-else class="size-4" />
                        </button>
                      </div>
                    </div>
                  </div>

                  <div class="flex items-start gap-2 pt-1">
                    <Checkbox
                      id="agree"
                      v-model="form.agreeTerms"
                      class="mt-0.5 border-white/20 data-[state=checked]:bg-fuchsia-400/60 data-[state=checked]:text-white data-[state=checked]:border-transparent"
                    />
                    <Label
                      for="agree"
                      class="text-sm leading-normal cursor-pointer text-white/75"
                    >
                      {{ t('auth.agreeTermsPrefix') }}
                      <a
                        href="#"
                        class="text-fuchsia-200 hover:text-white hover:underline underline-offset-2"
                      >{{ t('auth.terms') }}</a>
                      {{ t('auth.agreeTermsAnd') }}
                      <a
                        href="#"
                        class="text-fuchsia-200 hover:text-white hover:underline underline-offset-2"
                      >{{ t('auth.privacy') }}</a>
                    </Label>
                  </div>

                  <Button
                    variant="default"
                    class="w-full mt-2 h-11 bg-white text-slate-900 hover:bg-white/90 shadow-lg shadow-fuchsia-900/20"
                    :disabled="!isFormValid || loading"
                    @click="handleRegister"
                  >
                    <Loader2 v-if="loading" class="size-4 animate-spin mr-2" />
                    {{ loading ? t('auth.registering') : t('auth.createAccount') }}
                  </Button>
                </div>
              </CardContent>

              <CardFooter class="flex justify-center pt-1 pb-0 px-0 text-sm text-white/65">
                <span>{{ t('auth.hasAccount') }}</span>
                <NuxtLink
                  to="/login"
                  class="ml-1.5 font-medium text-white hover:text-fuchsia-200 hover:underline underline-offset-2 transition-colors"
                >
                  {{ t('auth.goLogin') }}
                </NuxtLink>
              </CardFooter>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部版权条 + 切壁纸（与登录页一致） -->
    <div class="absolute bottom-0 inset-x-0 z-20 flex flex-wrap items-end justify-between gap-3 p-5 md:p-7 pointer-events-none">
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
import { useAuthStore } from '~~/stores/auth'
import { useI18n } from 'vue-i18n'
import {
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  UserPlus,
  Palette,
  Globe2,
  Mail,
  ShieldCheck,
  Eye,
  EyeOff,
  CheckCircle2,
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

const { t } = useI18n()
const authStore = useAuthStore()

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
  return (
    form.name.trim()
    && form.email.trim()
    && form.password
    && form.password === form.confirmPassword
    && form.password.length >= 6
    && form.agreeTerms
  )
})

// ── Bing 每日壁纸 ─────────────────────────────────────────────
const wallpaperIdx = ref(0)
const wallpaperLoaded = ref(false)
const wallpaperPending = ref(false)

const {
  data: bwp,
  refresh: refreshWallpaper,
  pending: fetchPending
} = await useFetch<BingWallpaper>('/api/bing-wallpaper', {
  query: computed(() => ({ idx: wallpaperIdx.value, mkt: 'zh-CN' })),
  key: computed(() => `bwp:reg:${wallpaperIdx.value}`),
  server: false,
  default: () => null as unknown as BingWallpaper,
  lazy: false,
  watch: [wallpaperIdx]
})

watchEffect(() => { wallpaperPending.value = !!fetchPending.value })

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

const thumbUrl = computed(() => {
  if (!bwp.value?.url) return ''
  return bwp.value.url.replace('_UHD.jpg', '_150x84.jpg').replace('_UHD.jpeg', '_150x84.jpeg')
})

const cycleWallpaper = (step: -1 | 1) => {
  const total = bwp.value?.totalDays ?? 8
  const next = wallpaperIdx.value + (step * -1)
  wallpaperIdx.value = Math.max(0, Math.min(total - 1, next))
  wallpaperLoaded.value = false
}

const reloadWallpaper = () => {
  wallpaperLoaded.value = false
  refreshWallpaper().catch(() => {})
}

// ── 注册 ──────────────────────────────────────────────────────
const handleRegister = async () => {
  if (!isFormValid.value) return
  if (form.password !== form.confirmPassword) {
    errorMessage.value = t('auth.passwordMismatch')
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    // authStore.register(email, username, password, name)
    await authStore.register(form.email, form.email, form.password, form.name)
    navigateTo('/login')
  } catch (error: unknown) {
    errorMessage.value = (error as Error).message || t('auth.registerFailed')
  } finally {
    loading.value = false
  }
}
</script>
