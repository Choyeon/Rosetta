/**
 * @nuxtjs/i18n 的实际 options 入口（nuxt.config: vueI18n = './index.ts'）。
 * 此处 locale 码必须与 nuxt.config i18n.locales 及 i18n/locales/*.json 逐一对应；
 * 语言包唯一生效目录是 i18n/locales/，根 locales/ 是废弃影子目录，不得回填。
 */
import type { VueI18nOptions } from 'vue-i18n'

export default {
  legacy: false,
  locale: 'zh',
  fallbackLocale: 'en',
  availableLocales: ['zh', 'zh_Hant', 'en', 'ja']
} as VueI18nOptions
