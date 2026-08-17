<template>
  <div class="min-h-screen grid lg:grid-cols-2">
    <div class="hidden lg:flex flex-col justify-between p-12 bg-gradient-to-br from-slate-900 via-purple-950 to-slate-900 text-white relative overflow-hidden">
      <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(168,85,247,0.25),transparent_50%)]" />
      <div class="absolute top-0 left-0 -translate-x-1/4 -translate-y-1/4 size-[32rem] rounded-full bg-primary/20 blur-3xl" />
      <div class="absolute bottom-1/2 right-0 translate-x-1/4 size-[24rem] rounded-full bg-primary/15 blur-3xl" />

      <div class="relative">
        <NuxtLink
          to="/"
          class="inline-flex items-center gap-2 font-display text-2xl font-bold tracking-tight"
        >
          <Rocket class="size-6 text-primary" />
          <span>Rosetta</span>
        </NuxtLink>
      </div>

      <div class="relative max-w-md">
        <h1 class="font-display text-4xl font-bold mb-4 leading-tight tracking-tight">
          {{ t('auth.joinUs') }}
        </h1>
        <p class="text-white/70 leading-relaxed">
          {{ t('auth.joinUsDesc') }}
        </p>

        <div class="mt-12 space-y-4">
          <div class="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10">
            <div class="size-9 rounded-lg bg-primary/30 flex items-center justify-center shrink-0">
              <UserPlus class="size-4 text-primary/80" />
            </div>
            <div>
              <div class="font-semibold text-sm">
                {{ t('auth.feature1') }}
              </div>
              <div class="text-xs text-white/60">
                {{ t('auth.feature1Desc') }}
              </div>
            </div>
          </div>
          <div class="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10">
            <div class="size-9 rounded-lg bg-primary/30 flex items-center justify-center shrink-0">
              <Palette class="size-4 text-primary/80" />
            </div>
            <div>
              <div class="font-semibold text-sm">
                {{ t('auth.feature2') }}
              </div>
              <div class="text-xs text-white/60">
                {{ t('auth.feature2Desc') }}
              </div>
            </div>
          </div>
          <div class="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10">
            <div class="size-9 rounded-lg bg-success/30 flex items-center justify-center shrink-0">
              <Globe2 class="size-4 text-success/80" />
            </div>
            <div>
              <div class="font-semibold text-sm">
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

    <div class="flex items-center justify-center p-6 lg:p-12 bg-muted/30">
      <Card class="w-full max-w-md shadow-xl border-0">
        <CardHeader class="pb-2">
          <div class="lg:hidden flex items-center gap-2 font-display text-2xl font-bold mb-6 justify-center">
            <Rocket class="size-5 text-primary" />
            <span>Rosetta</span>
          </div>
          <CardTitle class="text-2xl font-display tracking-tight">
            {{ t('auth.register') }}
          </CardTitle>
          <CardDescription>
            {{ t('auth.registerDesc') }}
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

          <div class="flex flex-col gap-4">
            <div class="space-y-2">
              <Label for="nickname">{{ t('auth.nickname') }}</Label>
              <div class="relative">
                <UserPlus class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  id="nickname"
                  v-model="form.name"
                  type="text"
                  :placeholder="t('auth.nicknamePlaceholder')"
                  class="pl-9 h-11"
                />
              </div>
            </div>

            <div class="space-y-2">
              <Label for="email">{{ t('auth.email') }}</Label>
              <div class="relative">
                <Mail class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  id="email"
                  v-model="form.email"
                  type="email"
                  :placeholder="t('auth.emailPlaceholder')"
                  class="pl-9 h-11"
                />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3">
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

              <div class="space-y-2">
                <Label for="confirmPassword">{{ t('auth.confirmPassword') }}</Label>
                <div class="relative">
                  <CheckCircle2 class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                  <Input
                    id="confirmPassword"
                    v-model="form.confirmPassword"
                    :type="showConfirmPassword ? 'text' : 'password'"
                    :placeholder="t('auth.confirmPasswordPlaceholder')"
                    class="pl-9 pr-9 h-11"
                  />
                  <button
                    type="button"
                    class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    tabindex="-1"
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

            <div class="flex items-start gap-2 pt-1">
              <Checkbox
                id="agree"
                v-model="form.agreeTerms"
                class="mt-0.5"
              />
              <Label
                for="agree"
                class="text-sm leading-normal cursor-pointer"
              >
                {{ t('auth.agreeTermsPrefix') }}
                <a
                  href="#"
                  class="text-primary hover:underline underline-offset-2"
                >{{ t('auth.terms') }}</a>
                {{ t('auth.agreeTermsAnd') }}
                <a
                  href="#"
                  class="text-primary hover:underline underline-offset-2"
                >{{ t('auth.privacy') }}</a>
              </Label>
            </div>

            <Button
              variant="default"
              class="w-full mt-2 h-11"
              :disabled="!isFormValid || loading"
              @click="handleRegister"
            >
              <Loader2
                v-if="loading"
                class="size-4 animate-spin mr-2"
              />
              {{ loading ? t('auth.registering') : t('auth.createAccount') }}
            </Button>
          </div>
        </CardContent>

        <CardFooter class="flex justify-center pt-0 text-sm">
          <span class="text-muted-foreground">{{ t('auth.hasAccount') }}</span>
          <NuxtLink
            to="/login"
            class="ml-1.5 font-medium text-primary hover:underline underline-offset-2"
          >
            {{ t('auth.goLogin') }}
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
import { useAuthStore } from '~~/stores/auth'
import { useI18n } from 'vue-i18n'
import {
  Rocket,
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

definePageMeta({ layout: false })

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

const handleRegister = async () => {
  if (!isFormValid.value) return
  if (form.password !== form.confirmPassword) {
    errorMessage.value = t('auth.passwordMismatch')
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    await authStore.register(form.email, form.email, form.password, form.name)
    navigateTo('/login')
  } catch (error: unknown) {
    errorMessage.value = (error as Error).message || t('auth.registerFailed')
  } finally {
    loading.value = false
  }
}
</script>
