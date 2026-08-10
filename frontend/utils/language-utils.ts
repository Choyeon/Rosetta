import type { LocaleCode } from "../i18n";

const SUPPORTED: readonly LocaleCode[] = ["zh-CN", "zh-TW", "en", "ja"] as const;

/**
 * 从 navigator.language / Accept-Language 字符串匹配最合适的 LocaleCode。
 * 无匹配返回 fallback（默认 zh-CN）。
 */
export function detectBrowserLocale(
  input?: string | string[],
  fallback: LocaleCode = "zh-CN"
): LocaleCode {
  const candidates: string[] = input
    ? (Array.isArray(input) ? input : [input])
    : import.meta.client && typeof navigator !== "undefined"
      ? [...(navigator.languages || []), navigator.language].filter(Boolean)
      : [];

  for (const raw of candidates) {
    const tag = (raw || "").trim().toLowerCase();
    if (!tag) continue;
    const primary = tag.split(/[-_]/)[0];
    const exact = tag.replace("_", "-");
    const direct = (SUPPORTED as readonly string[]).find(l => l.toLowerCase() === exact || l.toLowerCase().split("-")[0] === primary);
    if (direct) return direct as LocaleCode;
  }
  return fallback;
}

/**
 * 4 种语言互切的循环/顺序切换，给 LocaleSwitcher 组件用。
 */
export function nextLocale(current: LocaleCode, order: LocaleCode[] = [...SUPPORTED]): LocaleCode {
  const i = order.indexOf(current);
  return order[(i + 1) % order.length];
}

/**
 * 带权重的 Accept-Language 解析（q= 参数），选出最佳候选。
 */
export function parseAcceptLanguage(header: string): Array<{ lang: string; q: number }> {
  return (header || "")
    .split(",")
    .map(chunk => {
      const [langPart, qPart] = chunk.split(";");
      const lang = (langPart || "").trim();
      const q = qPart ? Number(qPart.replace("q=", "")) : 1;
      return { lang, q: Number.isFinite(q) ? q : 1 };
    })
    .filter(x => x.lang)
    .sort((a, b) => b.q - a.q);
}

/**
 * 根据 Accept-Language 匹配最佳 Rosetta locale（SSR 中间件用）。
 */
export function matchLocaleFromHeader(header: string, fallback: LocaleCode = "zh-CN"): LocaleCode {
  const entries = parseAcceptLanguage(header);
  for (const e of entries) {
    const hit = detectBrowserLocale(e.lang, fallback);
    if (hit !== fallback) return hit;
  }
  return fallback;
}
