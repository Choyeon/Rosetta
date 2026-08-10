import { zhCN } from "./languages/zh-CN";
import { zhTW } from "./languages/zh-TW";
import { en } from "./languages/en";
import { ja } from "./languages/ja";

export type LocaleCode = "zh-CN" | "zh-TW" | "en" | "ja";

export const LOCALE_CODES: ReadonlyArray<LocaleCode> = ["zh-CN", "zh-TW", "en", "ja"] as const;

export const LOCALE_LABELS: Record<LocaleCode, string> = {
  "zh-CN": "简体中文",
  "zh-TW": "繁體中文",
  "en": "English",
  "ja": "日本語",
} as const;

export const messages = {
  "zh-CN": zhCN,
  "zh-TW": zhTW,
  "en": en,
  "ja": ja,
} as const;

export const i18nOptions = {
  vueI18n: {
    legacy: false,
    locale: "zh-CN" as LocaleCode,
    fallbackLocale: "en" as LocaleCode,
    messages,
    globalInjection: true,
  },
} as const;

export * from "./i18nKey";
export * from "./translation";
