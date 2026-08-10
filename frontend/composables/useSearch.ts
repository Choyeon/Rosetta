/**
 * 全站搜索 composable：
 *   - 数据源：@nuxt/content queryContent（本地 content/posts 等）+ 可选后端 /api/search 扩展
 *   - 模糊匹配：Fuse.js（title/description/tags/category/content 加权）
 *   - 支持实时防抖、结果分组、高亮片段
 */
import Fuse from "fuse.js";
import type { QueryContentResult } from "@nuxt/content";
import { z } from "zod";

export const SearchItemSchema = z.object({
  id: z.string(),
  slug: z.string(),
  path: z.string(),
  title: z.string(),
  description: z.string().default(""),
  category: z.string().default(""),
  tags: z.array(z.string()).default([]),
  author: z.string().default(""),
  published: z.boolean().default(true),
  pinned: z.boolean().default(false),
  draft: z.boolean().default(false),
  lang: z.string().default("zh-CN"),
  image: z.string().optional(),
  content: z.string().default(""),
  date: z.union([z.string(), z.number(), z.date()]).optional(),
  updated: z.union([z.string(), z.number(), z.date()]).optional(),
  readingMinutes: z.number().optional(),
});

export type SearchItem = z.infer<typeof SearchItemSchema>;

export interface SearchResult {
  item: SearchItem;
  score?: number;
  matches?: Array<{ indices: ReadonlyArray<[number, number]>; key?: string; value?: string }>;
}

export interface SearchOptions {
  limit?: number;
  threshold?: number;
  includeContent?: boolean;
  onlyPublished?: boolean;
  locale?: string;
}

interface SearchState {
  items: SearchItem[];
  fuse: Fuse<SearchItem> | null;
  ready: boolean;
}

const state = reactive<SearchState>({
  items: [],
  fuse: null,
  ready: false,
});

const FUSE_KEYS = [
  { name: "title", weight: 0.45 },
  { name: "tags", weight: 0.2 },
  { name: "category", weight: 0.12 },
  { name: "description", weight: 0.15 },
  { name: "author", weight: 0.05 },
  { name: "content", weight: 0.03 },
] as const;

function buildFuse(items: SearchItem[]): Fuse<SearchItem> {
  return new Fuse(items, {
    includeScore: true,
    includeMatches: true,
    ignoreLocation: true,
    threshold: 0.4,
    minMatchCharLength: 2,
    keys: [...FUSE_KEYS],
  });
}

function normalizeContentItem(raw: QueryContentResult): SearchItem {
  const fm = (raw as any) ?? {};
  const tags = Array.isArray(fm.tags)
    ? fm.tags.filter((t: unknown) => typeof t === "string") as string[]
    : [];
  return {
    id: String(fm._id ?? fm.id ?? fm.slug ?? Math.random().toString(36).slice(2)),
    slug: String(fm.slug ?? ""),
    path: String(fm._path ?? fm.path ?? `/posts/${fm.slug ?? ""}`),
    title: String(fm.title ?? ""),
    description: String(fm.description ?? ""),
    category: String(fm.category ?? ""),
    tags,
    author: String(fm.author ?? ""),
    published: Boolean(fm.published ?? true),
    pinned: Boolean(fm.pinned ?? false),
    draft: Boolean(fm.draft ?? false),
    lang: String(fm.lang ?? "zh-CN"),
    image: fm.image ? String(fm.image) : undefined,
    content: String((fm.body ?? fm.content ?? "") as string).slice(0, 8000),
    date: fm.date ?? fm.publishedAt ?? undefined,
    updated: fm.updated ?? fm.modifiedAt ?? undefined,
    readingMinutes: typeof fm.readingMinutes === "number" ? fm.readingMinutes : undefined,
  };
}

/**
 * 初始化（首次调用懒加载）：从 @nuxt/content 拉取所有内容并构建 Fuse 索引。
 * 同一客户端生命周期只加载一次。
 */
async function ensureReady(): Promise<void> {
  if (state.ready) return;
  try {
    const raw = await queryContent("/").find();
    const items = (raw as QueryContentResult[])
      .map(normalizeContentItem)
      .filter((x) => !!x.title && !!x.path);

    const validated: SearchItem[] = [];
    for (const it of items) {
      const r = SearchItemSchema.safeParse(it);
      if (r.success) validated.push(r.data);
    }
    state.items = validated;
    state.fuse = buildFuse(validated);
    state.ready = true;
  } catch (err) {
    console.warn("[useSearch] 加载内容索引失败", err);
    state.items = [];
    state.fuse = buildFuse([]);
    state.ready = true;
  }
}

/**
 * 同步搜索（索引未就绪时自动等待）。
 */
export function useSearch() {
  const keyword = ref("");
  const results = ref<SearchResult[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  let cancelToken = 0;

  const execute = useDebounceFn(async (kw: string, opts: SearchOptions = {}) => {
    const { limit = 20, threshold = 0.42, onlyPublished = true, locale } = opts;
    const myTurn = ++cancelToken;
    loading.value = true;
    error.value = null;
    try {
      await ensureReady();
      if (myTurn !== cancelToken) return;

      let pool = state.items;
      if (onlyPublished) pool = pool.filter((x) => x.published && !x.draft);
      if (locale) pool = pool.filter((x) => x.lang === locale || !x.lang);

      const needle = kw.trim();
      if (!needle) {
        results.value = pool
          .sort((a, b) => Number(b.pinned) - Number(a.pinned))
          .slice(0, limit)
          .map((item) => ({ item, score: 0, matches: [] }));
        return;
      }

      const fuse = new Fuse(pool, {
        includeScore: true,
        includeMatches: true,
        ignoreLocation: true,
        threshold,
        minMatchCharLength: 2,
        keys: [...FUSE_KEYS],
      });
      const out = fuse.search(needle).slice(0, limit);
      results.value = out;
    } catch (e: any) {
      error.value = e?.message ?? "搜索失败";
      results.value = [];
    } finally {
      if (myTurn === cancelToken) loading.value = false;
    }
  }, 150);

  watch(
    keyword,
    (v) => execute(v),
    { immediate: false }
  );

  function searchNow(kw: string, opts?: SearchOptions) {
    keyword.value = kw;
    return execute(kw, opts);
  }

  function clear() {
    keyword.value = "";
    results.value = [];
    error.value = null;
  }

  return {
    keyword,
    results,
    loading,
    error,
    ready: computed(() => state.ready),
    search: searchNow,
    clear,
    allItems: computed(() => state.items),
  };
}

/**
 * 纯函数：把 fuse 匹配的 indices 生成高亮 HTML 片段。
 */
export function renderHighlight(
  text: string,
  matches?: ReadonlyArray<{ indices: ReadonlyArray<[number, number]> }>,
  tag = "mark"
): string {
  if (!matches || matches.length === 0) return text;
  const indices = matches.flatMap((m) => [...m.indices]) as [number, number][];
  if (indices.length === 0) return text;
  const merged: [number, number][] = [];
  const sorted = [...indices].sort((a, b) => a[0] - b[0]);
  for (const [s, e] of sorted) {
    const last = merged[merged.length - 1];
    if (last && s <= last[1] + 1) last[1] = Math.max(last[1], e);
    else merged.push([s, e]);
  }
  let out = "";
  let cursor = 0;
  for (const [s, e] of merged) {
    out += text.slice(cursor, s);
    out += `<${tag}>`;
    out += text.slice(s, e + 1);
    out += `</${tag}>`;
    cursor = e + 1;
  }
  out += text.slice(cursor);
  return out;
}
