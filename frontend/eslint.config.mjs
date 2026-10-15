// @ts-check
import withNuxt from './.nuxt/eslint.config.mjs'

export default withNuxt(
  // Your custom configs here
  {
    // ⚠️ 生成产物必须显式忽略：flat config 只自动忽略 node_modules/.git，**不再**
    // 忽略点开头录，所以 `.nuxt/` 一旦被 `nuxt prepare`/`typecheck`/`build` 生成出来，
    // `eslint .` 就会把里面的数千个 vue/ts 产物一起 lint（实测 290 万条 error），
    // 后台看不到真实回归、CI 也无法判红绿。`pnpm lint` 的基线（0 error / 7 warning）
    // 只有在忽略产物后才可复现。
    // lib/lucide-svg-icons-all.ts 是 scripts/gen-lucide-ssr-shim.mjs 的生成产物
    // （全量图标 SSR shim，单行 import 数千条），不按源码风格约束。
    ignores: [
      '.nuxt/**',
      'output/**',
      'dist/**',
      '.output/**',
      'lib/lucide-svg-icons-all.ts'
    ]
  }
)
