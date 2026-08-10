import type { I18nKey } from "./i18nKey";

type ParamsValue = string | number | boolean | null | undefined;
type TranslationParams = Record<string, ParamsValue>;

/**
 * 类型安全的翻译辅助函数。
 * 需在 Vue setup / 组件上下文中调用（内部使用 useI18n）。
 *
 * @example
 *   const { t } = useTranslation();
 *   t(I18N_KEYS.NAV_HOME);
 *   t(I18N_KEYS.POST_VIEWS, { count: 100 });
 */
export function useTranslation() {
  const { t: vueI18nT } = useI18n();

  function t(key: I18nKey, params?: TranslationParams): string {
    if (params) {
      return vueI18nT(key, params as never);
    }
    return vueI18nT(key);
  }

  return { t };
}

/**
 * 脱离组件上下文的原始翻译辅助（setup 外 / server utils 中慎用）。
 * 优先使用 useTranslation()，其随当前 locale 自动响应式更新。
 */
export function translate(key: I18nKey, params?: TranslationParams): string {
  if (!import.meta.client) return key;
  try {
    const i18n = (globalThis as never).__NUXT_I18N__ as ReturnType<typeof useI18n> | undefined;
    if (!i18n) return key;
    return params ? (i18n.t as (k: string, p: never) => string)(key, params as never) : i18n.t(key);
  } catch {
    return key;
  }
}
