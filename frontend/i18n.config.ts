/**
 * vue-i18n 全局 options（默认 locale=zh、fallback=en、四语码表）。
 * nuxt.config 显式指定 vueI18n 为 ./i18n/index.ts，本根文件属同内容的第二入口，
 * 调整语言码或 fallback 时两处必须一起改。
 */
import type { VueI18nOptions } from 'vue-i18n'

export default {
  legacy: false as const,
  locale: 'zh',
  fallbackLocale: 'en',
  availableLocales: ['zh', 'zh_Hant', 'en', 'ja']
} satisfies VueI18nOptions & { legacy?: false }
