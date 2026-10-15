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
    //
    // `.output*`（不是 `.output`）：生产机上部署脚本会把上一次构建留成
    // `.output.bak-20261001b/` 这类备份目录，它不在仓库里、只在那台机器上存在，
    // 精确写死 `.output/**` 就挡不住它（实测又是 290 万条 error，且 pnpm 的退出码
    // 被吞成 0，看起来像"绿"）。产物目录一律按前缀忽略。
    ignores: [
      '.nuxt/**',
      'output/**',
      'dist/**',
      '.output*/**',
      '**/.output*/**',
      'lib/lucide-svg-icons-all.ts'
    ]
  }
)
