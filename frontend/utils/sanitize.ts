import DOMPurify from "isomorphic-dompurify";

export interface RosettaSanitizeConfig extends DOMPurify.Config {
  allowIframes?: boolean;
  allowSvg?: boolean;
  allowDataAttrs?: boolean;
  strictLinks?: boolean;
}

/**
 * 全局统一的 DOMPurify 配置：
 *   - 允许 iframe（来自用户信任域的 B 站 / YouTube embed）
 *   - 允许 SVG / mathml
 *   - 允许 data-* / aria-*
 *   - 仍然剥离任何 JS handler、style、base、form
 * 组件层直接调用 sanitizeHtml(html)，无需再传 options。
 */
export function buildRosettaSanitizer(
  options: RosettaSanitizeConfig = {}
): (html: string) => string {
  const {
    allowIframes = true,
    allowSvg = true,
    allowDataAttrs = true,
    strictLinks = false,
  } = options;

  const ADD_TAGS: string[] = [];
  if (allowIframes) ADD_TAGS.push("iframe", "video", "audio", "source", "track", "picture");
  if (allowSvg) ADD_TAGS.push("svg", "math", "mrow", "mi", "mn", "mo", "msub", "msup", "mfrac", "msqrt", "mtable", "mtr", "mtd", "mtext");

  const ADD_ATTR = ["target", "rel", "allow", "allowfullscreen", "frameborder", "scrolling", "aria-*"];
  if (allowDataAttrs) ADD_ATTR.push("data-*");
  if (allowSvg) {
    ADD_ATTR.push(
      "width", "height", "viewBox", "xmlns", "xmlns:xlink", "fill", "stroke",
      "stroke-width", "d", "path", "cx", "cy", "r", "points", "x1", "x2", "y1", "y2"
    );
  }

  const config: DOMPurify.Config = {
    USE_PROFILES: { html: true, svg: allowSvg, mathMl: allowSvg },
    ADD_TAGS,
    ADD_ATTR,
    FORBID_TAGS: ["script", "style", "form", "input", "textarea", "button", "select"],
    FORBID_ATTR: [
      "onerror", "onload", "onunload", "onclick", "ondblclick",
      "onmousedown", "onmouseup", "onmouseover", "onmousemove", "onmouseout",
      "onkeydown", "onkeypress", "onkeyup", "onsubmit", "onreset", "onchange",
      "onfocus", "onblur", "oninput", "ondragstart", "ondragover", "ondrop",
      "onscroll", "ontoggle", "onplay", "onpause",
    ],
    ALLOW_UNKNOWN_PROTOCOLS: false,
    ALLOWED_URI_REGEXP: strictLinks
      ? /^(?:(?:https?|mailto|tel|ftp):|#|\/|\.\/|\.\.\/)/i
      : /^(?:(?:https?|mailto|tel|ftp|data|blob):|#|\/|\.\/|\.\.\/)/i,
    ADD_DATA_URI_TAGS: ["img", "audio", "video", "source", "track"],
    RETURN_TRUSTED_TYPE: false,
    WHOLE_DOCUMENT: false,
    ...options,
  };

  return (html: string) => DOMPurify.sanitize(html || "", config) as string;
}

export const sanitizeHtml = buildRosettaSanitizer();

/**
 * 更严格的「纯文本」净化：剥离一切标签，只保留纯文本 + 换行（按 <br> / <p> 折叠）。
 * 用于评论预览 / 搜索摘要。
 */
export function sanitizeToPlainText(html: string, maxLength = 240): string {
  const pure = DOMPurify.sanitize(html || "", {
    ALLOWED_TAGS: [],
    ALLOWED_ATTR: [],
    KEEP_CONTENT: true,
  }) as string;
  const text = pure
    .replace(/\s*\n\s*/g, "\n")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength).replace(/\s+\S*$/, "") + "…";
}
