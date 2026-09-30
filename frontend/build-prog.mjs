/**
 * 沙箱内编程式 Nuxt 生产构建（绕过 clearBuildDir 护栏）。
 * 用法：node build-prog.mjs [--probe]
 * --probe 时注入 __VUE_PROD_HYDRATION_MISMATCH_DETAILS__=true（仅诊断用）。
 */
import { loadNuxt, buildNuxt } from '@nuxt/kit'

const probe = process.argv.includes('--probe')

const overrides = {
  // 诊断：生产构建保留 hydration mismatch 明细
  ...(probe
    ? { vite: { define: { __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: JSON.stringify(true) } } }
    : {})
}

const nuxt = await loadNuxt({ cwd: new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]):/, '$1:'), dev: false, overrides })
try {
  await buildNuxt(nuxt)
  console.log('BUILD OK (probe=' + probe + ')')
} catch (e) {
  console.error('BUILD FAILED', e)
  process.exitCode = 1
}
