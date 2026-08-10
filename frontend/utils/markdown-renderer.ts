import { Marked } from "marked";
import hljs from "highlight.js";
import DOMPurify from "isomorphic-dompurify";
import { extractTocFromHtml } from "./toc-utils";

export interface TocItem {
  id: string;
  text: string;
  level: 1 | 2 | 3 | 4 | 5 | 6;
  children: TocItem[];
}

export interface MarkdownRenderOptions {
  tocDepth?: 1 | 2 | 3 | 4 | 5 | 6;
  enableHeadingIds?: boolean;
  enableHighlight?: boolean;
  enableMermaid?: boolean;
  baseUrl?: string;
  openExternalInNewTab?: boolean;
  sanitizeConfig?: DOMPurify.Config;
}

export interface MarkdownRenderResult {
  html: string;
  toc: TocItem[];
}

function buildRenderer(options: MarkdownRenderOptions): Marked {
  const marked = new Marked();
  const { enableHeadingIds = true, enableHighlight = true, baseUrl, openExternalInNewTab = true } = options;
  const hl = enableHighlight ? hljs : null;

  marked.use({
    gfm: true,
    breaks: true,
  });

  let idCounter = 0;
  const slug = (text: string) => {
    const base = text
      .toLowerCase()
      .replace(/<[^>]+>/g, "")
      .replace(/[^\p{L}\p{N}\s-]/gu, "")
      .trim()
      .replace(/\s+/g, "-") || "heading";
    idCounter += 1;
    return `${base}-${idCounter}`;
  };

  marked.use({
    renderer: {
      heading({ tokens, depth }) {
        const text = this.parser.parseInline(tokens);
        const raw = text.replace(/<[^>]+>/g, "").trim();
        const id = enableHeadingIds ? slug(raw) : "";
        const attrs = enableHeadingIds ? ` id="${id}"` : "";
        return `<h${depth}${attrs}>${text}</h${depth}>\n`;
      },
      code({ text, lang }) {
        const language = lang && hl?.getLanguage(lang) ? lang : "plaintext";
        const highlighted = hl
          ? hl.highlight(text, { language, ignoreIllegals: true }).value
          : text;
        return `<pre class="hljs language-${language}"><code class="language-${language}">${highlighted}</code></pre>\n`;
      },
      link({ href, title, tokens }) {
        const text = this.parser.parseInline(tokens);
        const safeHref = normalizeLink(href || "", baseUrl);
        const external = /^https?:\/\//i.test(safeHref);
        const target = external && openExternalInNewTab ? ' target="_blank" rel="noopener noreferrer nofollow"' : "";
        const t = title ? ` title="${escapeHtmlAttr(title)}"` : "";
        return `<a href="${safeHref}"${t}${target}>${text}</a>`;
      },
      image({ href, title, text }) {
        const safeSrc = normalizeLink(href || "", baseUrl);
        const t = title ? ` title="${escapeHtmlAttr(title)}"` : "";
        const alt = text ? ` alt="${escapeHtmlAttr(text)}"` : "";
        return `<img src="${safeSrc}" loading="lazy" decoding="async"${alt}${t}/>`;
      },
    },
  });

  return marked;
}

function normalizeLink(href: string, baseUrl?: string): string {
  if (/^[a-z][a-z0-9+.-]*:/i.test(href)) return href;
  if (href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:")) return href;
  if (href.startsWith("//")) return href;
  if (!baseUrl) return href;
  try {
    return new URL(href, baseUrl).toString();
  } catch {
    return href;
  }
}

function escapeHtmlAttr(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/**
 * Markdown → { html, toc }。
 * 默认用 isomorphic-dompurify 清洗、highlight.js 高亮、marked GFM 解析。
 * TOC 从渲染后 HTML 提取，h1-h6 统一 id（若启用）后构造成树。
 */
export function renderMarkdown(
  markdown: string,
  options: MarkdownRenderOptions = {}
): MarkdownRenderResult {
  const { tocDepth = 3, sanitizeConfig } = options;
  const marked = buildRenderer(options);
  const rawHtml = marked.parse(markdown || "") as string;

  const cleanHtml = DOMPurify.sanitize(rawHtml, {
    ADD_ATTR: ["target", "data-*"],
    ADD_TAGS: ["iframe", "video", "audio", "source"],
    FORBID_ATTR: ["onerror", "onload", "onclick", "onmouseover", "style"],
    ...sanitizeConfig,
  }) as string;

  const toc = extractTocFromHtml(cleanHtml, { maxDepth: tocDepth });
  return { html: cleanHtml, toc };
}

/**
 * 同步、纯渲染 Markdown 片段为 HTML（不含 TOC 计算），给评论框 / 动态卡片 等轻量场景使用。
 */
export function renderMarkdownInline(markdown: string, options: MarkdownRenderOptions = {}): string {
  return renderMarkdown(markdown, options).html;
}
