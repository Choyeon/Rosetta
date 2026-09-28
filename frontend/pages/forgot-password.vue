<!--
  密码找回 /forgot-password：接后端自上线就绪、前端零消费的
  POST /users/password-reset-request + POST /users/password-reset。
  三步约束：
  1. 两步行在同一页（WordPress「Lost your password?» 同款）：发码后原地展开重置表单，
     不必为"输验证码"再造一个路由与一次导航，账号上下文也不会丢。
  2. 发码端点恒定 200 + 恒定文案（防账号枚举），前端**不得**根据响应推断"该账号存在"，
     文案一律用后端回的那句；`debug.reset_code` 只在非生产 + DEBUG 下存在，
     生产恒 undefined，所以本地能一次跑通全链路、线上不泄露凭证。
  3. 密码强度只在提交后按后端信封报错，页面不写第二套规则（校验单通道，
     与 /account/settings 同口径）；这里只做"必填 + 两次输入一致"的纯 UX 前置检查。
  ssr:false 与 no-store 写在 routeRules（不在本页重复声明）：本页是表单敏感输入页。
-->
<template>
  <div class="container py-16 max-w-lg mx-auto">
    <header class="mb-8">
      <h1 class="font-display text-2xl md:text-3xl font-bold tracking-tight">
        {{ t('forgotPassword.title') }}
      </h1>
      <p class="mt-2 text-sm text-muted-foreground leading-relaxed">
        {{ t('forgotPassword.desc') }}
      </p>
    </header>

    <Card class="card-surface">
      <CardContent class="flex flex-col gap-6 p-6">
        <!-- ===== 第一步：发码 ===== -->
        <section class="flex flex-col gap-3">
          <h2 class="font-display text-base font-semibold">
            {{ t('forgotPassword.step1Title') }}
          </h2>
          <div class="flex flex-col gap-2">
            <Label for="fp-account">{{ t('forgotPassword.fieldAccount') }}</Label>
            <Input
              id="fp-account"
              v-model="account"
              autocomplete="username"
              :disabled="resetting"
            />
          </div>
          <Button
            variant="outline"
            :disabled="requesting || !account.trim()"
            @click="requestCode"
          >
            <KeyRound data-icon="inline-start" />
            {{ requesting ? t('common.loading') : t('forgotPassword.sendCode') }}
          </Button>
          <p
            v-if="sentMessage"
            class="text-sm text-muted-foreground leading-relaxed"
            role="status"
          >
            {{ sentMessage }}
          </p>
          <!-- 仅本地开发回显：生产响应没有 debug 字段，这一段永远不会渲染 -->
          <p
            v-if="devCode"
            class="text-xs text-warning-muted-foreground bg-warning-muted rounded-lg px-3 py-2"
          >
            {{ t('forgotPassword.devCodeHint', { code: devCode }) }}
          </p>
        </section>

        <!-- ===== 第二步：验证码 + 新密码（发码成功后才出现） ===== -->
        <section
          v-if="sentMessage"
          class="flex flex-col gap-3 border-t border-border/60 pt-6"
        >
          <h2 class="font-display text-base font-semibold">
            {{ t('forgotPassword.step2Title') }}
          </h2>
          <div class="flex flex-col gap-2">
            <Label for="fp-code">{{ t('forgotPassword.fieldCode') }}</Label>
            <Input
              id="fp-code"
              v-model="code"
              inputmode="numeric"
              maxlength="6"
              autocomplete="one-time-code"
              :disabled="resetting"
            />
          </div>
          <div class="flex flex-col gap-2">
            <Label for="fp-new">{{ t('forgotPassword.fieldNewPassword') }}</Label>
            <Input
              id="fp-new"
              v-model="newPassword"
              type="password"
              autocomplete="new-password"
              :disabled="resetting"
            />
          </div>
          <div class="flex flex-col gap-2">
            <Label for="fp-confirm">{{ t('forgotPassword.fieldConfirmPassword') }}</Label>
            <Input
              id="fp-confirm"
              v-model="confirm"
              type="password"
              autocomplete="new-password"
              :disabled="resetting"
            />
            <p
              v-if="confirm && passwordMismatch"
              class="text-sm text-destructive"
              role="alert"
            >
              {{ t('forgotPassword.passwordMismatch') }}
            </p>
          </div>
          <Button
            :disabled="resetting || !canReset"
            @click="resetPassword"
          >
            <ShieldCheck data-icon="inline-start" />
            {{ resetting ? t('common.loading') : t('forgotPassword.resetPassword') }}
          </Button>
        </section>
      </CardContent>
    </Card>

    <p class="mt-6 text-sm">
      <NuxtLink
        to="/login"
        class="text-muted-foreground transition-colors hover:text-primary"
      >
        {{ t('forgotPassword.backToLogin') }}
      </NuxtLink>
    </p>
  </div>
</template>

<script setup lang="ts">
import { KeyRound, ShieldCheck } from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Card, CardContent } from '~~/components/ui/card'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import { apiFetch } from '~~/composables/useApi'
import { useToast } from '~~/composables/useToast'
import { useI18n } from 'vue-i18n'

/** 发码响应：恒定 success/message，DEBUG 非生产环境额外带 debug.reset_code */
interface ResetRequestResult {
  success?: boolean
  message?: string
  debug?: { reset_code?: string } | null
}

definePageMeta({ layout: 'default' })

const { t } = useI18n()
const toast = useToast()

const account = ref('')
const code = ref('')
const newPassword = ref('')
const confirm = ref('')
const requesting = ref(false)
const resetting = ref(false)
const sentMessage = ref('')
const devCode = ref('')

const passwordMismatch = computed(() => !!confirm.value && newPassword.value !== confirm.value)
const canReset = computed(() =>
  !!account.value.trim() && /^\d{6}$/.test(code.value.trim())
  && !!newPassword.value && !passwordMismatch.value
)

async function requestCode() {
  if (requesting.value) return
  requesting.value = true
  try {
    const res = await apiFetch<ResetRequestResult>('/blog/users/password-reset-request', {
      method: 'POST',
      body: { email_or_username: account.value.trim() }
    })
    // 用后端文案，不自造"已发送"判断：该端点对存在与不存在的账号回同一句话
    sentMessage.value = res?.message || t('forgotPassword.codeSent')
    devCode.value = res?.debug?.reset_code ?? ''
    if (devCode.value) code.value = devCode.value
  } catch {
    // apiFetch 已按统一失败信封 toast，这里只吞 rejection 防未处理异常
  } finally {
    requesting.value = false
  }
}

async function resetPassword() {
  if (!canReset.value || resetting.value) return
  resetting.value = true
  try {
    const res = await apiFetch<{ message?: string }>('/blog/users/password-reset', {
      method: 'POST',
      body: {
        token_or_email: account.value.trim(),
        code: code.value.trim(),
        new_password: newPassword.value
      }
    })
    toast.success(res?.message || t('forgotPassword.passwordReset'))
    // 重置成功后清一次本地输入，避免留在页面上的明文密码与已作废的验证码
    code.value = ''
    newPassword.value = ''
    confirm.value = ''
    devCode.value = ''
    await navigateTo('/login')
  } catch {
    resetting.value = false
  }
}

useHead(() => ({ title: t('forgotPassword.title') }))
</script>

<style scoped>
/* 复用全局令牌与 card-surface 基座，本文件不引入新皮肤。 */
</style>
