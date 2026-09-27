/**
 * vitest.config.ts —— `pnpm test`（vitest run）的配置入口：只收 tests/unit/**，environment 固定
 * happy-dom（不起浏览器、不打真实后端），故 e2e / playwright 路径必须整体 exclude，
 * .nuxt / .output 也要排除——它们是构建产物，扫进来会让用例数虚高。
 * defineVitestConfig 负责注入 nuxt 解析后的 vite 配置（含 ~ 等别名与构建期 define），这里再把 @ 与 ~~ 钉到 frontend 根目录
 * （srcDir 就是 frontend 本身，没有 app/ 层），源码里 `~~/lib/utils`、`@/stores/auth` 两种写法才都解析得到。
 */

import { defineVitestConfig } from '@nuxt/test-utils/config'
import { fileURLToPath } from 'node:url'

export default defineVitestConfig({
  test: {
    globals: true,
    environment: 'happy-dom',
    // 单测不需要浏览器/真实网络，默认跳过 E2E
    exclude: [
      '**/e2e/**',
      '**/playwright-tests/**',
      '**/*.e2e.spec.ts',
      '**/node_modules/**',
      '**/.nuxt/**',
      '**/.output/**',
      '**/dist/**'
    ],
    include: ['tests/unit/**/*.{test,spec}.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text-summary', 'html'],
      reportsDirectory: 'tests/coverage-unit'
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./', import.meta.url)),
      '~~': fileURLToPath(new URL('./', import.meta.url))
    }
  }
})
