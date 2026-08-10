import { nanoid } from "nanoid";
import { DynamicItemSchema, type DynamicItem } from "../types/dynamicConfig";

export interface DynamicTemplateInput {
  content: string;
  tags?: string[];
  media?: Array<{ url: string; type?: "image" | "video" | "link" }>;
  mood?: string;
  location?: string;
  pinned?: boolean;
  private?: boolean;
}

/**
 * 基于模板快速构造 Rosetta Dynamic 条目（用于前端提交 / 导入）。
 * 输出会走 Zod schema 校验，失败抛出异常让调用方兜底。
 */
export function buildDynamicItem(input: DynamicTemplateInput): DynamicItem {
  const now = new Date().toISOString();
  const payload: DynamicItem = {
    id: nanoid(12),
    slug: nanoid(8),
    content: input.content,
    createdAt: now,
    updatedAt: now,
    pinned: !!input.pinned,
    private: !!input.private,
    tags: input.tags || [],
    media: (input.media || []).map(m => ({
      id: nanoid(8),
      type: m.type || "image",
      url: m.url,
    })),
    mood: input.mood,
    location: input.location ? { name: input.location } : undefined,
    likes: 0,
    comments: 0,
    views: 0,
    source: "builtin",
  };
  const result = DynamicItemSchema.safeParse(payload);
  if (!result.success) {
    throw new TypeError(`DynamicItem schema 不合法: ${result.error.issues.map(i => i.message).join("; ")}`);
  }
  return result.data;
}

/**
 * 给定一组 Dynamic 条目，按「置顶 → 日期倒序」稳定排序。
 */
export function sortDynamicItems(items: DynamicItem[], reverse = true): DynamicItem[] {
  return [...items].sort((a, b) => {
    if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
    const ta = new Date(a.createdAt).getTime();
    const tb = new Date(b.createdAt).getTime();
    return reverse ? tb - ta : ta - tb;
  });
}
