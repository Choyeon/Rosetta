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
    class="ap-error min-h-svh w-full bg-background text-foreground antialiased"
  >
    <!-- 极简主题纯纸面错误页：.ap-error-* 由 style.css frontend 守卫段落装饰 -->
    <div class="mx-auto flex min-h-svh w-full max-w-[480px] flex-col items-center justify-center px-5 py-14 text-center">
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
import { NOINDEX_ROBOTS } from '~~/composables/useSeo'

/**
 * 注意：error.vue 位于项目根目录、不在 pages/ 下，因此 Nuxt 编译器【不会】把
 * definePageMeta 编译掉——在这里调用它会在运行时抛 NUXT_E1007（"compiler macro
 * cannot be called at runtime"）→ 连带触发 NUXT_E1005 app 初始化错误，每次渲染
 * 兜底页都在控制台留下 2~3 条 error。而且它本就是 no-op：error.vue 是独立渲染、
 * 不套 <NuxtLayout>（模板直接输出 .error-page），layout/ssr 选项无从生效。
 * 故此处【不得】写 definePageMeta；错误页的 SSR 由出错路由与 Nuxt 内部决定。
 */

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

/**
 * 标题后缀只能用站点名。这里曾写死 `… · Rosetta`：生产实测未命中路由的 404 页
 * <title> 是「404 · 页面不存在 · Rosetta」，而站内每一页都是「… · Choyeon Blog」
 * ——运营者改了站名，唯独兜底页还顶着内部项目名。
 * 与其他页同一口径读 useSite().siteTitle；取不到时只输出「状态码 · 文案」，客户端
 * titleTemplate 会补站点名——宁可少一段，也不要再冒出一个别的品牌名。
 */
let site: ReturnType<typeof useSite> | null = null
try {
  site = useSite()
} catch { /* Nuxt 上下文极端异常：不带站点名 */ }

const titleWithSuffix = (title: string): string => {
  const name = site?.siteTitle.value
  return name ? `${title} · ${name}` : title
}

/**
 * robots + description 也必须由本页给：兜底页不经过 useSeo，不写就继承 nuxt.config 的
 * 通用 head——实测未命中路由的 404 原始 HTML 里既没有 robots 行，description 也还是
 * nuxt.config 那条产品介绍（"Modern personal blog system with Nuxt 4 + FastAPI"），
 * 与「页面不存在」互相矛盾。robots 统一走 NOINDEX_ROBOTS 单源（AGENTS §2.3.3.4）。
 */
useHead({
  title: computed(() => `${statusCode.value} · ${titleWithSuffix(pageTitle.value)}`),
  meta: [
    { name: 'robots', content: NOINDEX_ROBOTS },
    { name: 'description', content: computed(() => pageDesc.value) }
  ]
})
</script>

<style scoped>
/* 颜色全部走 main.css 的语义令牌。注意令牌是**裸 HSL 三元组**（`0 0% 100%`），
   直接写 `var(--background)` 会得到非法颜色、整页退回写死的浅色——
   暗色模式下错误页因此一直是白底黑字。必须显式包 hsl()。 */
.error-page {
  min-height: 100svh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background:
    radial-gradient(900px 420px at 50% -10%, hsl(var(--primary) / 0.08), transparent 65%),
    hsl(var(--background));
  color: hsl(var(--foreground));
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
  color: hsl(var(--primary));
  opacity: 0.9;
  font-variant-numeric: tabular-nums;
}

.error-title {
  margin-top: 1rem;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.error-desc {
  margin-top: 0.75rem;
  color: hsl(var(--muted-foreground));
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
  border-radius: var(--radius, 0.75rem);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: filter 0.15s ease, background-color 0.15s ease;
  border: none;
}

.error-btn.primary {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
}

.error-btn.primary:hover {
  filter: brightness(1.08);
}

.error-btn.ghost {
  background: hsl(var(--muted));
  color: hsl(var(--foreground));
}

.error-btn.ghost:hover {
  background: hsl(var(--accent));
}
</style>
