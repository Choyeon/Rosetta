import matter from "gray-matter";
import readingTime from "reading-time";

export interface FrontmatterCore {
  title?: string;
  description?: string;
  date?: string;
  updated?: string;
  published?: boolean;
  pinned?: boolean;
  draft?: boolean;
  category?: string;
  tags?: string[];
  image?: string;
  author?: string;
  lang?: string;
  slug?: string;
  [key: string]: unknown;
}

export interface ParsedContent {
  frontmatter: FrontmatterCore;
  body: string;
  excerpt?: string;
  wordCount: number;
  readingMinutes: number;
  readingTimeText: string;
}

/**
 * 从 Markdown / MDX 字符串中抽取 frontmatter 与正文，并计算阅读时长。
 */
export function parseContent(raw: string, locale = "zh-CN"): ParsedContent {
  const { data, content, excerpt } = matter(raw, { excerpt: true, excerpt_separator: "<!-- more -->" });
  const stats = readingTime(content, {
    wordsPerMinute: locale.startsWith("zh") ? 500 : 200,
  });
  return {
    frontmatter: (data as FrontmatterCore) || {},
    body: content,
    excerpt: excerpt || undefined,
    wordCount: stats.words,
    readingMinutes: Math.max(1, Math.ceil(stats.minutes)),
    readingTimeText: stats.text,
  };
}

/**
 * 基于标题 / frontmatter.slug / date 生成 URL 友好的 slug。
 * 中文使用拼音缩写？这里保守：非字母数字用「-」连接，保留中文。
 */
export function generateSlug(input: string, options: { date?: string; preserveNonLatin?: boolean } = {}): string {
  const { date, preserveNonLatin = true } = options;
  let slug = (input || "").trim();
  if (!slug && date) {
    slug = date.replace(/\D+/g, "-").replace(/^-+|-+$/g, "");
  }
  if (preserveNonLatin) {
    slug = slug
      .replace(/[\s_]+/g, "-")
      .replace(/[\\/?%#[\]@!$&'()*+,;=.:]+/g, "-")
      .replace(/-{2,}/g, "-")
      .replace(/^-+|-+$/g, "");
  } else {
    slug = slug
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }
  return encodeURIComponent(slug).replace(/%2F/g, "/").replace(/%3A/g, ":");
}

/**
 * 将原始内容渲染后的阅读时长（独立于 parseContent，便于组件里直接算正文）。
 */
export function computeReadingTime(body: string, locale = "zh-CN"): {
  minutes: number;
  words: number;
  text: string;
} {
  const result = readingTime(body, {
    wordsPerMinute: locale.startsWith("zh") ? 500 : 200,
  });
  return {
    minutes: Math.max(1, Math.ceil(result.minutes)),
    words: result.words,
    text: result.text,
  };
}

/**
 * 从 frontmatter 中抽取日期字符串，不存在则回退到今天 ISO。
 */
export function getContentDate(fm: FrontmatterCore): string {
  const d = fm.date || fm.updated;
  if (d && !Number.isNaN(new Date(d).getTime())) {
    return new Date(d).toISOString();
  }
  return new Date().toISOString();
}
