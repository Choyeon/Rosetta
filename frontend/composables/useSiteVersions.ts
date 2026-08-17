/**
 * 站点版本信息组合式
 * 从 build info 静态注入（由 scripts/build-version-info.js 生成到 public/version-info.json）
 * 或从 package.json / composable 内置常量读取
 */

export const useSiteVersions = () => {
  // 内联写入已知稳定常量（离线可用，无构建步骤依赖）
  const buildInfo = computed(() => ({
    rosetta: '1.0.0',
    nuxt: '4.5.1',
    vue: '3.5.40',
    nitro: '2.13.4',
    vite: '8.1.5',
    pinia: '2.2.8',
    tailwindcss: '3.4.19',
    i18n: '10.6.0',
    node: import.meta.client ? navigator.userAgent.match(/Node\.js\/([\d.]+)/)?.[1] || (process?.versions?.node || '24.18.0') : '24.18.0',
    npm: '11.16.0',
    python: '3.10.11',
    fastapi: '0.141.1',
    pnpm: (globalThis as { __pnpm_version?: string }).__pnpm_version || '9.16.0'
  }))

  return { buildInfo }
}
