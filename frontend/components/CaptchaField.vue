<!--
  CaptchaField —— 图形验证码表单件（评论 / 留言共用）。

  出现条件由父组件决定：未登录 + 后台 features.enable_captcha 为真。
  服务端答案一次性（consume 即删），所以**任何一次提交失败后父组件必须调 refresh()**，
  否则用户重试永远撞 CAPTCHA_EXPIRED。

  SSR 安全：取图只在 onMounted / enabled 变化时发生（服务端不请求 /captcha），
  首帧两端都渲染"加载中"占位，不会造成 hydration mismatch。
-->
<template>
  <div class="flex flex-col gap-2">
    <Label
      :for="fieldId"
      class="text-sm font-medium"
    >{{ t('captcha.label') }}</Label>
    <div class="flex items-center gap-2">
      <Input
        :id="fieldId"
        v-model="code"
        type="text"
        maxlength="6"
        autocomplete="off"
        :placeholder="t('captcha.placeholder')"
        class="rounded-xl flex-1"
      />
      <button
        type="button"
        class="shrink-0 h-10 rounded-lg border border-border overflow-hidden inline-flex items-center justify-center hover:bg-muted transition-colors cursor-pointer disabled:opacity-60"
        :aria-label="t('captcha.refresh')"
        :disabled="loading"
        @click="refresh"
      >
        <img
          v-if="image"
          :src="image"
          :alt="t('captcha.imageAlt')"
          class="h-10 w-auto"
          width="120"
          height="40"
        >
        <span
          v-else
          class="px-3 text-xs text-muted-foreground whitespace-nowrap"
        >{{ loading ? t('captcha.loading') : t('captcha.retry') }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiFetch } from '~~/composables/useApi'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'

const props = defineProps<{ enabled: boolean }>()

const { t } = useI18n()
const route = useRoute()
const fieldId = `captcha-${String(route.path).replace(/[^a-zA-Z0-9]/g, '')}`

const key = ref('')
const code = ref('')
const image = ref('')
const loading = ref(false)

async function refresh() {
  loading.value = true
  try {
    const data = await apiFetch<{ key: string, image: string }>('/captcha')
    key.value = data.key
    image.value = data.image
    code.value = ''
  } catch {
    // apiFetch 已统一 toast；这里保持占位可见，用户可点图重取
    key.value = ''
    image.value = ''
  } finally {
    loading.value = false
  }
}

/** 交给父组件的提交字段：未启用时返回空对象，载荷里不会多出两个空键。 */
function payload(): Record<string, string> {
  if (!props.enabled) return {}
  return { captcha_key: key.value, captcha_code: code.value.trim() }
}

/** 提交前的行内校验位：缺验证码就别打这一枪，后端会回 400 但那是兜底不是首道门。 */
function valid(): boolean {
  return !props.enabled || code.value.trim().length > 0
}

onMounted(() => {
  if (props.enabled) refresh()
})

watch(() => props.enabled, (on) => {
  if (on && !image.value) refresh()
})

defineExpose({ payload, valid, refresh })
</script>
