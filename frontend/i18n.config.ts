import type { VueI18nOptions } from 'vue-i18n'

export default {
  legacy: false as const,
  locale: 'zh',
  fallbackLocale: 'en',
  availableLocales: ['zh', 'zh_Hant', 'en', 'ja']
} satisfies VueI18nOptions & { legacy?: false }
