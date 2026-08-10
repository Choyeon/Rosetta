/**
 * 不依赖后端 Sharp 的客户端 / SSR 通用 LQIP 占位工具：
 * - 简单 SVG 轮廓（1x1 渐变 + 主色）
 * - base64 Data URI 直接放进 img.src 或 background-image
 */

/**
 * 生成一个通用矩形 SVG LQIP base64 占位（主色 + 简单渐变 + 噪点纹理）。
 * 完全不依赖真实图片内容，但足以先占坑减少布局跳动。
 */
export function generateSvgLqip(options: {
  width?: number;
  height?: number;
  color1?: string;
  color2?: string;
  text?: string;
  opacity?: number;
} = {}): string {
  const w = options.width ?? 16;
  const h = options.height ?? 16;
  const c1 = options.color1 ?? "#6366f1";
  const c2 = options.color2 ?? "#8b5cf6";
  const op = options.opacity ?? 0.7;
  const label = escapeXmlAttr(options.text || "");
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">` +
    `<defs>` +
    `<linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">` +
    `<stop offset="0%" stop-color="${c1}" stop-opacity="${op}"/>` +
    `<stop offset="100%" stop-color="${c2}" stop-opacity="${op}"/>` +
    `</linearGradient>` +
    `<filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch"/></filter>` +
    `</defs>` +
    `<rect width="100%" height="100%" fill="url(#g)"/>` +
    `<rect width="100%" height="100%" filter="url(#n)" opacity="0.08"/>` +
    (label
      ? `<text x="50%" y="50%" font-family="sans-serif" font-size="${Math.max(6, Math.floor(Math.min(w, h) / 3))}" text-anchor="middle" dominant-baseline="middle" fill="rgba(255,255,255,0.6)">${label}</text>`
      : "") +
    `</svg>`;
  return `data:image/svg+xml;base64,${stringToBase64(svg)}`;
}

/**
 * 纯字符串 base64：用 TextEncoder + 全局 btoa；SSR 兜底 Buffer。
 */
function stringToBase64(s: string): string {
  if (typeof Buffer !== "undefined") {
    return Buffer.from(s, "utf-8").toString("base64");
  }
  if (typeof btoa !== "undefined") {
    const u16 = new TextEncoder().encode(s);
    let bin = "";
    for (let i = 0; i < u16.length; i++) bin += String.fromCharCode(u16[i]);
    return btoa(bin);
  }
  return "";
}

/**
 * 给图片加载前用的「模糊骨架」占位 inline style。
 * 浏览器端真实加载完后 overlay 再 transition 掉。
 */
export function skeletonPlaceholderStyle(
  width?: number,
  height?: number,
  color = "#6366f1"
): React.CSSProperties {
  return {
    backgroundColor: color,
    aspectRatio: width && height ? `${width} / ${height}` : "16 / 9",
    opacity: 0.45,
    width: "100%",
    height: "auto",
  } as React.CSSProperties;
}

export function escapeXmlAttr(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
