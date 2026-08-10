import { buildDynamicItem, sortDynamicItems } from "./dynamic-config";
import type { DynamicItem, DynamicConfig } from "../types/dynamicConfig";

/**
 * 将模板字符串 {{name}} / {{date}} / {{mood}} 用参数对象替换。
 * 用于动态内容的「预设短语」批量渲染。
 */
export function renderDynamicTemplate(tpl: string, params: Record<string, string | number | undefined>): string {
  return tpl.replace(/\{\{\s*([\w.-]+)\s*\}\}/g, (_, key: string) => {
    const v = params[key];
    return v === undefined || v === null ? "" : String(v);
  });
}

/**
 * 从 Dynamic 条目中抽取全部可索引纯文本（正文 + alt），便于 fuse.js 建索引。
 */
export function getDynamicSearchText(item: DynamicItem): string {
  const parts: string[] = [item.content, ...(item.tags || [])];
  if (item.location?.name) parts.push(item.location.name);
  if (item.mood) parts.push(item.mood);
  for (const m of item.media) {
    if (m.title) parts.push(m.title);
    if (m.alt) parts.push(m.alt);
  }
  return parts.filter(Boolean).join(" \n ");
}

/**
 * 合并本地条目和外部（Memos 等）条目，按 sortDynamicItems 规则排序。
 */
export function mergeDynamicSources(
  local: DynamicItem[],
  external: DynamicItem[],
  cfg: Pick<DynamicConfig, "showPinnedFirst" | "reverseOrder">
): DynamicItem[] {
  const merged = [...local, ...external];
  const seen = new Set<string>();
  const dedup: DynamicItem[] = [];
  for (const it of merged) {
    const key = it.sourceRef || it.id;
    if (!seen.has(key)) {
      seen.add(key);
      dedup.push(it);
    }
  }
  const sorted = sortDynamicItems(dedup, cfg.reverseOrder);
  if (!cfg.showPinnedFirst) {
    return sorted.sort((a, b) => {
      const ta = new Date(a.createdAt).getTime();
      const tb = new Date(b.createdAt).getTime();
      return cfg.reverseOrder ? tb - ta : ta - tb;
    });
  }
  return sorted;
}

export { buildDynamicItem };
