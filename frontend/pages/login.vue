<template>
  <div class="min-h-screen grid lg:grid-cols-2">
    <div class="hidden lg:flex flex-col justify-between p-12 bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white relative overflow-hidden">
      <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(99,102,241,0.25),transparent_50%)]" />
      <div class="absolute bottom-0 right-0 translate-x-1/4 translate-y-1/4 size-[32rem] rounded-full bg-primary/20 blur-3xl" />
      <div class="absolute top-1/2 left-0 -translate-x-1/2 size-[24rem] rounded-full bg-primary/15 blur-3xl" />

      <div class="relative">
        <NuxtLink
          to="/"
          class="inline-flex items-center gap-2 font-display text-2xl font-bold tracking-tight"
        >
          <Sparkles class="size-6 text-primary" />
          <span>Rosetta</span>
        </NuxtLink>
      </div>

      <div class="relative max-w-md">
        <h1 class="font-display text-4xl font-bold mb-4 leading-tight tracking-tight">
          {{ t('auth.welcomeBack') }}
        </h1>
        <p class="text-white/70 leading-relaxed">
          {{ t('auth.welcomeBackDesc') }}
        </p>

        <div class="mt-12 space-y-4">
          <div class="flex flex-wrap gap-2">
            <Badge
              variant="secondary"
              class="bg-white/10 text-white border-0 hover:bg-white/15"
            >
              Vue 3
            </Badge>
            <Badge
              variant="secondary"
              class="bg-white/10 text-white border-0 hover:bg-white/15"
            >
              Nuxt
            </Badge>
            <Badge
              variant="secondary"
              class="bg-white/10 text-white border-0 hover:bg-white/15"
            >
              Tailwind
            </Badge>
            <Badge
              variant="secondary"
              class="bg-white/10 text-white border-0 hover:bg-white/15"
            >
              shadcn-vue
            </Badge>
          </div>
        </div>
      </div>

      <div class="relative">
        <div class="border-l-2 border-indigo-400/40 pl-5 py-1">
          <p class="text-white/80 italic leading-relaxed">
            "{{ t('auth.testimonial') }}"
          </p>
          <div class="flex items-center gap-3 mt-4">
            <Avatar class="size-9 border-2 border-white/20">
              <AvatarFallback class="bg-primary text-primary-foreground">
                Z
              </AvatarFallback>
            </Avatar>
            <div>
              <div class="font-semibold text-sm">
                {{ t('auth.testimonialAuthor') }}
              </div>
              <div class="text-xs text-white/60">
                {{ t('auth.testimonialRole') }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="flex items-center justify-center p-6 lg:p-12 bg-muted/30">
      <Card class="w-full max-w-md shadow-xl border-0">
        <CardHeader class="pb-2">
          <div class="lg:hidden flex items-center gap-2 font-display text-2xl font-bold mb-6 justify-center">
            <Sparkles class="size-5 text-primary" />
            <span>Rosetta</span>
          </div>
          <CardTitle class="text-2xl font-display tracking-tight">
            {{ t('auth.login') }}
          </CardTitle>
          <CardDescription>
            {{ t('auth.loginDesc') }}
          </CardDescription>
        </CardHeader>

        <CardContent>
          <Alert
            v-if="errorMessage"
            variant="destructive"
            class="mb-5"
          >
            <AlertTitle>{{ t('auth.error') }}</AlertTitle>
            <AlertDescription>{{ errorMessage }}</AlertDescription>
          </Alert>

          <form
            class="flex flex-col gap-4"
            @submit.prevent="handleLogin"
          >
            <div class="space-y-2">
              <Label for="username">{{ t('auth.usernameOrEmail') }}</Label>
              <div class="relative">
                <Mail class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  id="username"
                  v-model="form.username"
                  type="text"
                  autocomplete="username"
                  :placeholder="t('auth.usernamePlaceholder')"
                  class="pl-9 h-11"
                />
              </div>
            </div>

            <div class="space-y-2">
              <Label for="password">{{ t('auth.password') }}</Label>
              <div class="relative">
                <ShieldCheck class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  id="password"
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  :placeholder="t('auth.passwordPlaceholder')"
                  class="pl-9 pr-9 h-11"
                />
                <button
                  type="button"
                  class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
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
                />
                <Label
                  for="remember"
                  class="text-sm cursor-pointer"
                >{{ t('auth.rememberMe') }}</Label>
              </div>
              <span
                class="text-sm text-muted-foreground/70 cursor-not-allowed select-none"
                :title="t('auth.forgotPasswordDisabled', '忘记密码功能暂未开放，请联系管理员')"
                aria-disabled="true"
              >
                {{ t('auth.forgotPassword') }}
              </span>
            </div>

            <Button
              type="submit"
              variant="default"
              class="w-full mt-4 h-11"
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

        <CardFooter class="flex justify-center pt-0 text-sm">
          <span class="text-muted-foreground">{{ t('auth.noAccount') }}</span>
          <NuxtLink
            to="/register"
            class="ml-1.5 font-medium text-primary hover:underline underline-offset-2"
          >
            {{ t('auth.goRegister') }}
          </NuxtLink>
        </CardFooter>
      </Card>
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
  Sparkles,
  Mail,
  ShieldCheck,
  Eye,
  EyeOff,
  Loader2
} from '@lucide/vue'

definePageMeta({ layout: false })

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

/** 仅接受站内相对路径：以单个 '/' 开头，排除 '//'（协议相对）与 '/\'（浏览器会规范化为 '//'） */
const safeRedirect = (raw: unknown): string => {
  if (typeof raw !== 'string') return '/admin'
  if (!raw.startsWith('/') || raw.startsWith('//') || raw.startsWith('/\\')) return '/admin'
  return raw
}

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
