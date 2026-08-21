/**
 * 站点版本信息组合式
 * 从 build info 静态注入（由 scripts/build-version-info.js 生成到 public/version-info.json）
 * 或从 package.json / composable 内置常量读取
 */

export const useSiteVersions = () => {
  // 仅保留构建时能静态得知的前端技术栈版本（避免编造运行环境信息）。
  // Python/Node/FastAPI 等运行环境信息如需展示，应新增后端真实接口返回。
  const buildInfo = computed(() => ({
    rosetta: '1.0.0',
    nuxt: '4.5.1',
    vue: '3.5.40',
    nitro: '2.13.4',
    vite: '8.1.5',
    pinia: '2.2.8',
    tailwindcss: '3.4.19',
    i18n: '10.6.0'
  }))

  return { buildInfo }
}
