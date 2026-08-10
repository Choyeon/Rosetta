import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import localizedFormat from "dayjs/plugin/localizedFormat";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";
import updateLocale from "dayjs/plugin/updateLocale";
import "dayjs/locale/zh-cn";
import "dayjs/locale/zh-tw";
import "dayjs/locale/en";
import "dayjs/locale/ja";

dayjs.extend(relativeTime);
dayjs.extend(localizedFormat);
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(updateLocale);

const LOCALE_MAP: Record<string, string> = {
  "zh-CN": "zh-cn",
  "zh-TW": "zh-tw",
  "en": "en",
  "ja": "ja",
};

function applyLocale(locale: string) {
  const mapped = LOCALE_MAP[locale] || locale;
  try {
    dayjs.locale(mapped);
  } catch {
    dayjs.locale("en");
  }
}

/**
 * 相对时间（如「3 分钟前 / in 2 hours」），自带 locale 映射。
 */
export function formatRelative(date: string | Date | number, locale = "zh-CN", now?: Date): string {
  applyLocale(locale);
  const anchor = now ? dayjs(now) : dayjs();
  return dayjs(date).from(anchor);
}

/**
 * ISO-8601 字符串（UTC）；输入缺省返回当前时间。
 */
export function formatISO(date?: string | Date | number): string {
  return dayjs(date || new Date()).toISOString();
}

/**
 * 本地化完整格式，如「2025年8月10日 星期日」。
 */
export function formatLocalized(date: string | Date | number, pattern: "LL" | "LLL" | "LLLL" | "L" | "LT" | "LTS" | string = "LL", locale = "zh-CN"): string {
  applyLocale(locale);
  return dayjs(date).format(pattern);
}

/**
 * 按月份分组：常用于归档页。
 * @example
 *   groupByMonth(posts, p => p.date) → Map<"2025-08", Post[]>
 */
export function groupByMonth<T>(items: T[], dateExtractor: (item: T) => string | Date | number): Map<string, T[]> {
  const buckets = new Map<string, T[]>();
  for (const item of items) {
    const key = dayjs(dateExtractor(item)).format("YYYY-MM");
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key)!.push(item);
  }
  return new Map([...buckets.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1)));
}

/**
 * 时区转换：把任意时刻转到目标时区并格式化为 pattern。
 * 默认目标时区从 site config 思路出发，提供 Asia/Shanghai。
 */
export function formatTimezone(
  date: string | Date | number,
  pattern = "YYYY-MM-DD HH:mm:ss",
  tz = "Asia/Shanghai"
): string {
  try {
    return dayjs(date).tz(tz).format(pattern);
  } catch {
    return dayjs(date).format(pattern);
  }
}

export function parseInTimezone(dateStr: string, tz = "Asia/Shanghai"): dayjs.Dayjs {
  try {
    return dayjs.tz(dateStr, tz);
  } catch {
    return dayjs(dateStr);
  }
}

/**
 * 今天是哪个季度的判断（archive 筛选 helper）。
 */
export function currentSeason(): { year: number; season: 1 | 2 | 3 | 4 } {
  const now = dayjs();
  const month = now.month() + 1;
  const season = (Math.ceil(month / 3) as 1 | 2 | 3 | 4);
  return { year: now.year(), season };
}
