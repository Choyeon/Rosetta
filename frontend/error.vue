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

/**
 * 关闭 error.vue 自身的 SSR：
 *
 * 本项目 Windows Nitro standalone 在 ssr:false 页面（/login /register /search
 * /admin/** /oobe）上仍会先跑一次 app.vue shell 的 SSR 渲染流程；若渲染时
 * Vue/Nuxt 全局链路（app.vue wrapper 结构、layout resolve、全局 composable）
 * 触发 `refs null` 级联，Nuxt 会把 NUXT_E1005 当成 fatal → 把 error.vue 当
 * 成"兜底页"SSR 渲染出来。而 error.vue 自己如果又带 SSR，会重新命中上面
 * 那根致命链 → 每次 `window.location.replace(/login?__spa_mount=uniq)` 回到
 * 服务端，仍然拿到 SSR 的 error.vue 500 壳 → 客户端再次进入死循环。
 *
 * 把 error.vue 自己关 SSR 以后：NUXT_E1005 → Nitro 仅返回 #__nuxt 空壳，
 * 客户端首帧立刻 `import.meta.client === true` → 直接走下面的 SPA 自愈
 * clearError / location.replace，且替换回来的 `/login` 页面因为 login.vue
 * ssr:false + error.vue ssr:false，整个链路里**没有**任何 SSR DOM 需要
 * Vue runtime 去 `hydrateNode` 对齐 → 级联 `refs null` 直接消失。
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
const MINIMAL_THEME_SLUGS = new Set<string>(['astro-paper-inspired'])
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

/**
 * SPA 精准反选路径的 refs null 级联自愈（v2 静默版）：
 *
 * 2026-01-11 最终版：由于 plugins/00-spa-global-error-escape-hatch 已经在
 * vue:error / config.errorHandler / window.onerror 五道钩子里把 SPA 路径
 * 上的 refs null NPE 彻底吞掉（_swallow + 不触发任何 clearError），这里
 * error.vue setup 中保留"记录一次 info 诊断"作为辅助排错日志，不再执行
 * HARD window.location.replace 跳 __spa_mount=uniq，避免同 stack 内
 * setRef forEach 仍在跑就同步 unmount 子树造成第二轮 NPE 死循环。
 *
 * 若吞错后 UI 仍未渲染（极端情况），用户会看到 500 壳上的「重试」按钮，
 * 手动 reload 即可；实际上 setRef NPE 在 Vue render effect 的 post patch
 * 收尾阶段，UI 已能继续画出来——error.vue 根本不会被 Nuxt 挂载。
 */
const SPA_CLEAR_PATHS = new Set([
  '/login',
  '/register',
  '/oobe',
  '/search',
  '/admin'
])
const isSpaClearPath = (p: string): boolean => {
  if (SPA_CLEAR_PATHS.has(p)) return true
  if (p.startsWith('/admin/') || p.startsWith('/search/')) return true
  return false
}
if (import.meta.client) {
  const msg = (props.error?.message || '').toString()
  const isRefsNullCascade
    = /reading\s+['"`']refs['"`']/.test(msg)
      || /null.*refs|refs.*null/i.test(msg)
  const path = (window.location?.pathname || '')
  // 仅诊断：不要 HARD replace。实际命中时 00-escape-hatch 应已让 Nuxt 直接
  // 继续渲染真实页面，不会落到 error.vue。
  if (isRefsNullCascade && isSpaClearPath(path)) {
    console.info(
      '[error.vue:client] SPA refs-null cascade (v2 swallow-only). Not doing HARD replace. Path:',
      path,
      'msg:',
      msg.slice(0, 180)
    )
  }
}

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
