<!--
  Nuxt 根级兜底页（layout:false，无布局替它加载主题）：极简变体判定 import MINIMAL_THEME_SLUGS，
  并自行在客户端触发 useFrontendTheme().ensureLoaded()；后端不可达时 slug 为空即落默认分支。
  回首页/去登录一律 clearError({ redirect: localePath(...) })（同时清错误态并跳转），不是 navigateTo；
  「去登录」只在 401/403 出现、「重试」只在 >=500 出现，500 的副标题直接透出 error.message。
  t() 与 useLocalePath() 都包了 try/catch + 内置中文兜底：i18n 未就绪的窗口期本页也必须能渲染。
-->

<template>
  <div
    v-if="isMinimalError"
    class="ap-error min-h-screen w-full bg-background text-foreground antialiased"
  >
    <!-- 极简主题纯纸面错误页：.ap-error-* 由 style.css frontend 守卫段落装饰 -->
    <div class="mx-auto flex min-h-screen w-full max-w-[480px] flex-col items-center justify-center px-5 py-14 text-center">
      <div class="ap-error-code tabular-nums">
        {{ statusCode }}
      </div>
      <h1 class="ap-error-title mt-4 text-2xl font-semibold tracking-tight">
        {{ pageTitle }}
      </h1>
      <p class="ap-error-desc mt-3 text-sm leading-relaxed text-muted-foreground">
        {{ pageDesc }}
      </p>
      <div class="ap-error-actions mt-9 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-sm font-semibold">
        <button
          type="button"
          class="ap-error-link"
          @click="goHome"
        >
          {{ t('error.backHome') }}
        </button>
        <button
          v-if="statusCode === 401 || statusCode === 403"
          type="button"
          class="ap-error-link"
          @click="goLogin"
        >
          {{ t('error.goLogin') }}
        </button>
        <button
          v-if="statusCode >= 500"
          type="button"
          class="ap-error-link"
          @click="reload"
        >
          {{ t('error.retry') }}
        </button>
      </div>
    </div>
  </div>

  <div
    v-else
    class="error-page"
  >
    <!-- 默认错误页（非极简主题） -->
    <div class="error-card">
      <div class="error-code">
        {{ statusCode }}
      </div>
      <h1 class="error-title">
        {{ pageTitle }}
      </h1>
      <p class="error-desc">
        {{ pageDesc }}
      </p>
      <div class="error-actions">
        <button
          type="button"
          class="error-btn primary"
          @click="goHome"
        >
          {{ t('error.backHome') }}
        </button>
        <button
          v-if="statusCode === 401 || statusCode === 403"
          type="button"
          class="error-btn ghost"
          @click="goLogin"
        >
          {{ t('error.goLogin') }}
        </button>
        <button
          v-if="statusCode >= 500"
          type="button"
          class="error-btn ghost"
          @click="reload"
        >
          {{ t('error.retry') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { MINIMAL_THEME_SLUGS } from '~~/lib/rosetta-themes'

/**
 * layout:false 必需：兜底页不得套前台 default 布局（主题装饰 / 页头页脚）。
 * ssr:false：历史动机是阻断 "ssr:false 空壳页 NUXT_E1005 → error.vue 又走 SSR
 * → 二次 fatal" 的循环；该循环的客户端掩盖层（00-escape-hatch）已拆除，
 * 且 definePageMeta 在 error.vue 中是否生效未经证实（可能本就是 no-op）。
 * 保留为保守选项——移除会改变错误页 SSR 行为，需真机验证后再决策（见拆除报告遗留项）。
 */
definePageMeta({ ssr: false, layout: false })

const props = defineProps<{
  error: {
    statusCode: number
    statusMessage?: string
    message?: string
  }
}>()

/**
 * 兜底页可能在 i18n 尚未安装完成的窗口期被挂载（如 Nitro worker 重启、
 * locale 切换竞态触发 SSR 失败），此时 useI18n() 返回的 t 不是函数，
 * 直接调用会抛 TypeError 让兜底页自己也白屏。这里包一层安全调用，
 * 失败时退回到内置中文文案，保证兜底页任何情况下可渲染。
 */
let i18nT: ((key: string) => unknown) | null = null
try {
  const i18n = useI18n() as unknown as { t?: unknown }
  if (typeof i18n.t === 'function') i18nT = i18n.t as (key: string) => unknown
} catch { /* i18n 插件未就绪：走内置文案 */ }
const ERROR_FALLBACK_TEXT: Record<string, string> = {
  'error.notFoundTitle': '页面不存在',
  'error.notFoundDesc': '你访问的页面已被移除或地址有误。',
  'error.permissionTitle': '没有访问权限',
  'error.permissionDesc': '请先登录后再访问该页面。',
  'error.serverErrorTitle': '服务开小差了',
  'error.serverErrorDesc': '服务器处理请求时发生错误，请稍后重试。',
  'error.backHome': '返回首页',
  'error.goLogin': '去登录',
  'error.retry': '重试'
}
const t = (key: string): string => {
  if (i18nT) {
    try {
      const value = i18nT(key)
      if (typeof value === 'string' && value && value !== key) return value
    } catch { /* fall through */ }
  }
  return ERROR_FALLBACK_TEXT[key] || key
}
let localePath: (p: string) => string = p => p
try {
  const fn = useLocalePath()
  if (typeof fn === 'function') localePath = fn as (p: string) => string
} catch { /* i18n 未就绪：直接用原路径 */ }

const statusCode = computed(() => props.error?.statusCode ?? 500)

/**
 * 极简主题激活时错误页切换为纯纸面分支（.ap-error-* 类由
 * themes/astro-paper-inspired/style.css 的 frontend 守卫段落装饰）。
 * error.vue 是 Nuxt 根级兜底组件（layout:false），没人替它调 ensureLoaded，
 * 这里自行触发；后端不可达时 ensureLoaded 内部兜底为 slug=null → 走默认分支。
 */
let ft: ReturnType<typeof useFrontendTheme> | null = null
try {
  ft = useFrontendTheme()
} catch { /* Nuxt 上下文极端异常：保持默认错误页 */ }
const isMinimalError = computed(() => MINIMAL_THEME_SLUGS.has(ft?.slug.value || ''))
if (import.meta.client) void ft?.ensureLoaded()

const pageTitle = computed(() => {
  if (statusCode.value === 404) return t('error.notFoundTitle')
  if (statusCode.value === 401 || statusCode.value === 403) return t('error.permissionTitle')
  return t('error.serverErrorTitle')
})

const pageDesc = computed(() => {
  if (statusCode.value === 404) return t('error.notFoundDesc')
  if (statusCode.value === 401 || statusCode.value === 403) return t('error.permissionDesc')
  return props.error?.message || t('error.serverErrorDesc')
})

const goHome = () => {
  clearError({ redirect: localePath('/') })
}

const goLogin = () => {
  clearError({ redirect: localePath('/login') })
}

const reload = () => {
  if (import.meta.client) window.location.reload()
}

// 注：曾在此处放"SPA 路径 refs-null 级联自愈诊断"（依赖 00-escape-hatch 吞错链）。
// 该插件已拆除；真实错误现在会照常进入本兜底页并展示（含重试按钮），不做静默诊断。

useHead({
  title: computed(() => `${statusCode.value} · ${pageTitle.value} · Rosetta`)
})
</script>

<style scoped>
.error-page {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: var(--background, #f8fafc);
  color: var(--foreground, #0f172a);
}

.error-card {
  max-width: 28rem;
  width: 100%;
  text-align: center;
  padding: 3rem 2rem;
}

.error-code {
  font-size: clamp(5rem, 18vw, 8rem);
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.04em;
  color: var(--primary, #0ea5e9);
  opacity: 0.9;
}

.error-title {
  margin-top: 1rem;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.error-desc {
  margin-top: 0.75rem;
  color: var(--muted-foreground, #64748b);
  font-size: 0.95rem;
  line-height: 1.6;
  word-break: break-word;
}

.error-actions {
  margin-top: 2rem;
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.error-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  border-radius: 0.75rem;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: filter 0.15s ease, background-color 0.15s ease;
  border: none;
}

.error-btn.primary {
  background: var(--primary, #0ea5e9);
  color: #fff;
}

.error-btn.primary:hover {
  filter: brightness(1.08);
}

.error-btn.ghost {
  background: var(--muted, #f1f5f9);
  color: var(--foreground, #0f172a);
}

.error-btn.ghost:hover {
  background: var(--muted-foreground, #e2e8f0);
}
</style>
