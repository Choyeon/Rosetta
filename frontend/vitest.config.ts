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
