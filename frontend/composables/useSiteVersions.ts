/**
 * 站点版本信息组合式（2026-09 单一真源改造）
 *
 * 版本来源（禁止再写死过期字面量）：
 * - rosetta：后端公开端点 GET /health（backend/main.py::health_check，无需登录，
 *   返回 { success, data: { version, ... } }）。该 version 的唯一真源是根
 *   pyproject.toml [project].version（backend/main.py::_resolve_app_version）。
 *   接口不可用时返回空串，由页面渲染「—」占位；frontend/package.json 没有
 *   version 字段（前端包名 "frontend" 与 rosetta 产品版本无关），故不做假兜底。
 * - nuxt / pinia / tailwindcss / @nuxtjs/i18n：读 frontend/package.json 依赖声明
 *   （清单即前端构建真源，展示时剥掉 ^/~ 范围前缀）。
 * - vue：直接取 vue 包运行时导出的 version（SSR 与客户端同源，字节一致）。
 * - vite / nitro：曾是 Nuxt 的传递依赖（无 package.json 直接声明可依据），
 *   旧硬编码 8.1.5 / 2.13.4 已随 Nuxt 升级过期且无法静态得知，因此不再展示，
 *   避免"看似有源实则漂移"的第二真源。
 */
import { version as vueRuntimeVersion } from 'vue'
import pkg from '~~/package.json'
import { useAPI } from '~~/composables/useApi'

/** GET /health 响应信封（backend root health_check，公开无鉴权） */
interface HealthEnvelope {
  success: boolean
  data?: {
    app_name?: string
    version?: string
    environment?: string
    database?: string
  }
  message?: string
}

const ALL_DEPS: Record<string, string> = {
  ...(pkg.dependencies ?? {}),
  ...(pkg.devDependencies ?? {})
}

/** '^4.5.2' / '~1.2.3' / '1.2.3' → '4.5.2'（剥离范围前缀仅用于展示） */
function depVersion(name: string): string {
  return String(ALL_DEPS[name] ?? '').replace(/^[\^~]/, '')
}

/**
 * 异步原因：/health 必须在 SSR setup 期 await 完成（Nuxt 挂起渲染直到 resolved，
 * 结果进 payload），保证水合两端字节一致；fire-and-forget 会让首帧值两端不同。
 */
export const useSiteVersions = async () => {
  const { data: health } = await useAPI<HealthEnvelope>('/health', {
    key: 'site-versions:health',
    timeout: 5000 // 后端无响应时快速放弃，回家占位符，不拖慢首页首帧
  })

  const buildInfo = computed(() => ({
    rosetta: health.value?.data?.version?.trim() ?? '',
    nuxt: depVersion('nuxt'),
    vue: vueRuntimeVersion,
    pinia: depVersion('pinia'),
    tailwindcss: depVersion('tailwindcss'),
    i18n: depVersion('@nuxtjs/i18n')
  }))

  return { buildInfo }
}
