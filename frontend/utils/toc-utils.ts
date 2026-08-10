import { buildTocTree, flattenToc, resolveActiveTocId, type TocEntry, type TocNode } from "./toc-shared";

export { buildTocTree, flattenToc, resolveActiveTocId };
export type { TocEntry, TocNode };

export interface ExtractOptions {
  maxDepth?: 1 | 2 | 3 | 4 | 5 | 6;
  selector?: string;
}

/**
 * 从 HTML 字符串中抽取 h1~h6（带 id 优先，没有则基于 text 生成 slug），
 * 构造成 TocNode[] 树。用于：
 *   - markdown-renderer 渲染完后同步提取
 *   - 服务端把文章内容字符串先过一遍拿 TOC
 */
export function extractTocFromHtml(html: string, options: ExtractOptions = {}): TocNode[] {
  const { maxDepth = 3, selector } = options;
  const allowed = Array.from({ length: maxDepth }, (_, i) => `h${i + 1}`).join(",");
  const sel = selector || allowed;
  const entries: TocEntry[] = [];
  let unique = 0;

  if (!html) return [];

  const doc = parseDomFromString(html);
  const headings = doc.querySelectorAll(sel);
  headings.forEach((node) => {
    const tag = (node.tagName || "").toLowerCase();
    const lv = Number(tag.charAt(1)) as 1 | 2 | 3 | 4 | 5 | 6;
    if (!Number.isFinite(lv) || lv < 1 || lv > maxDepth) return;
    let id = (node as Element).getAttribute("id") || "";
    if (!id) {
      unique += 1;
      id = slugifyHeading(node.textContent || "", unique);
    }
    const text = (node.textContent || "").trim();
    if (!text) return;
    entries.push({ id, text, level: lv });
  });

  return buildTocTree(entries);
}

/**
 * 从已经挂载到文档的 DOM 容器中抽取 TOC（客户端 ScrollSpy 初始化用）。
 * 返回扁平化列表，便于滚动事件里直接线性扫描。
 */
export function collectTocFromContainer(
  container: Element | DocumentFragment | null | undefined,
  maxDepth = 3
): TocEntry[] {
  if (!container) return [];
  const sel = Array.from({ length: maxDepth }, (_, i) => `h${i + 1}`).join(",");
  const nodes = container.querySelectorAll(sel);
  const out: TocEntry[] = [];
  nodes.forEach((node) => {
    const tag = (node.tagName || "").toLowerCase();
    const lv = Number(tag.charAt(1)) as 1 | 2 | 3 | 4 | 5 | 6;
    if (!Number.isFinite(lv) || lv < 1 || lv > maxDepth) return;
    const el = node as Element;
    const id = el.id;
    const text = (el.textContent || "").trim();
    if (!id || !text) return;
    out.push({ id, text, level: lv });
  });
  return out;
}

/**
 * 从 Markdown heading 文本生成 slug（与 markdown-renderer 保持独立，这里更简化）。
 */
function slugifyHeading(text: string, seq: number): string {
  const base = text
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "");
  return base ? `${base}-${seq}` : `heading-${seq}`;
}

function parseDomFromString(html: string): Document {
  if (import.meta.client && typeof DOMParser !== "undefined") {
    return new DOMParser().parseFromString(`<body>${html}</body>`, "text/html");
  }
  const { JSDOM } = safeRequireJsdom();
  if (JSDOM) {
    const dom = new JSDOM(`<!doctype html><body>${html}</body>`);
    return dom.window.document;
  }
  return fallbackParse(html);
}

function safeRequireJsdom(): { JSDOM?: new (html: string) => { window: { document: Document } } } {
  try {
    return require("jsdom") as { JSDOM: new (html: string) => { window: { document: Document } } };
  } catch {
    return {};
  }
}

function fallbackParse(html: string): Document {
  const entries: Array<{ tag: string; id: string; text: string }> = [];
  const regex = /<h([1-6])(?:\s+[^>]*?\sid="([^"]+)")?[^>]*>([\s\S]*?)<\/h\1>/gi;
  let m: RegExpExecArray | null;
  while ((m = regex.exec(html))) {
    const tag = `h${m[1]}`;
    const id = m[2] || "";
    const text = stripTags(m[3] || "").trim();
    entries.push({ tag, id, text });
  }
  const fakeDoc = {
    querySelectorAll(sel: string) {
      const tags = sel.split(",").map(s => s.trim());
      return entries
        .filter(e => tags.includes(e.tag))
        .map(e => ({
          tagName: e.tag.toUpperCase(),
          getAttribute(name: string) {
            return name === "id" ? e.id : null;
          },
          textContent: e.text,
        }));
    },
  } as unknown as Document;
  return fakeDoc;
}

function stripTags(s: string): string {
  return s.replace(/<[^>]+>/g, "");
}
