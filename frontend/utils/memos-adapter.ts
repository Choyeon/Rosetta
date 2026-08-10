import { nanoid } from "nanoid";
import type { DynamicItem } from "../types/dynamicConfig";
import { base64UrlDecode } from "./crypto-utils";

/**
 * Memos 官方 API 的典型返回结构（尽量宽松，字段缺失也能跑）。
 */
export interface MemosResource {
  id?: number;
  filename?: string;
  type?: string;
  size?: number;
  externalLink?: string;
  blob?: unknown;
}

export interface MemosMemo {
  id?: number;
  uid?: string;
  creatorId?: number;
  creatorName?: string;
  content?: string;
  visibility?: "PRIVATE" | "PROTECTED" | "PUBLIC";
  pinned?: boolean;
  displayTs?: string | number;
  createdTs?: string | number;
  updatedTs?: string | number;
  rowStatus?: "ACTIVE" | "ARCHIVED";
  resourceList?: MemosResource[];
  property?: { tags?: string[]; [k: string]: unknown } | null;
  tags?: string[];
}

/**
 * 将任意 Memos 条目适配成 Rosetta DynamicItem。
 * - 资源外链 → media.image
 * - #tag 语法解析 + property.tags 合并
 * - ts 统一转 ISO 字符串
 */
export function adaptMemosToDynamic(memo: MemosMemo): DynamicItem {
  const ts = toIso(memo.displayTs ?? memo.createdTs ?? Date.now());
  const content = memo.content ?? "";
  const hashtags = extractHashTags(content);
  const tags = Array.from(
    new Set<string>([...hashtags, ...(memo.tags || []), ...(memo.property?.tags || [])])
  );
  const media = (memo.resourceList || [])
    .map(r => r.externalLink || r.filename)
    .filter((x): x is string => !!x)
    .map(url => ({
      id: nanoid(8),
      type: guessMediaType(url) as "image" | "video" | "audio" | "link",
      url,
      title: "",
    }));

  const id = memo.uid ? `memos-${memo.uid}` : `memos-${memo.id ?? nanoid(10)}`;

  return {
    id,
    slug: memo.uid || nanoid(8),
    content: stripHashtags(content),
    createdAt: ts,
    updatedAt: toIso(memo.updatedTs ?? ts),
    pinned: !!memo.pinned,
    private: memo.visibility === "PRIVATE",
    media,
    tags,
    likes: 0,
    comments: 0,
    views: 0,
    source: "memos",
    sourceRef: id,
  };
}

export function adaptMemosList(list: MemosMemo[]): DynamicItem[] {
  return list
    .filter(m => m.rowStatus !== "ARCHIVED")
    .filter(m => m.visibility === "PUBLIC" || m.visibility === "PROTECTED")
    .map(adaptMemosToDynamic);
}

function toIso(ts: string | number | undefined): string {
  if (!ts) return new Date().toISOString();
  const n = typeof ts === "number" ? ts : Number(ts);
  if (Number.isFinite(n) && n > 1_000_000_000_000) return new Date(n).toISOString();
  if (Number.isFinite(n) && n > 1_000_000_000) return new Date(n * 1000).toISOString();
  if (typeof ts === "string") {
    const d = new Date(ts);
    if (!Number.isNaN(d.getTime())) return d.toISOString();
  }
  return new Date().toISOString();
}

function extractHashTags(text: string): string[] {
  const out: string[] = [];
  const re = /(?:^|\s)#([^\s#，,。；;！!？?【】\[\]()（）、]+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    const t = m[1];
    if (t && !out.includes(t)) out.push(t);
  }
  return out;
}

function stripHashtags(text: string): string {
  return text
    .replace(/(^|\s)#[^\s#，,。；;！!？?【】\[\]()（）、]+/g, (_, p) => p)
    .trim();
}

function guessMediaType(url: string): "image" | "video" | "audio" | "link" {
  const ext = url.split("?")[0].split(".").pop()?.toLowerCase() || "";
  if (["png", "jpg", "jpeg", "gif", "webp", "avif", "bmp", "svg", "ico"].includes(ext)) return "image";
  if (["mp4", "webm", "mov", "mkv", "m4v"].includes(ext)) return "video";
  if (["mp3", "wav", "ogg", "flac", "aac", "m4a"].includes(ext)) return "audio";
  return "link";
}

/**
 * Memos 自定义内容里的 [[(ENDPOINT|TYPE|DATA)]] 解密（base64-url 内嵌资源）
 * → 解析为 Rosetta media 结构，便于在动态卡片里直接渲染。
 */
export function parseMemosInlineEmbeds(content: string): {
  cleanedContent: string;
  embeds: NonNullable<DynamicItem["media"]>;
} {
  const embeds: NonNullable<DynamicItem["media"]> = [];
  const cleaned = content.replace(/\[\[\s*(\w+)\s*\|\s*(\w+)\s*\|\s*([^\]]+?)\s*\]\]/g, (_, ep: string, t: string, data: string) => {
    const type = (["image", "video", "audio", "link"] as const).includes(t as never) ? (t as "image" | "video" | "audio" | "link") : "link";
    const url = /^https?:\/\//i.test(data) ? data : base64UrlDecode(data);
    embeds.push({ id: nanoid(8), type, url: url || ep });
    return "";
  });
  return { cleanedContent: cleaned.trim(), embeds };
}
