// @ts-check
import withNuxt from './.nuxt/eslint.config.mjs'

export default withNuxt(
  // Your custom configs here
  {
    // lib/lucide-svg-icons-all.ts 是 scripts/gen-lucide-ssr-shim.mjs 的生成产物
    // （全量图标 SSR shim，单行 import 数千条），不按源码风格约束。
    ignores: ['lib/lucide-svg-icons-all.ts']
  }
)
