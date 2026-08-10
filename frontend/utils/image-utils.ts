/**
 * 图片相关纯函数工具：生成 srcset、计算宽高比、产出 LQIP 宽高等。
 * 不依赖 @nuxt/image 运行时 API，纯逻辑方便 SSR / 单元测试。
 */

export interface SrcSetOptions {
  widths?: number[];
  format?: "avif" | "webp" | "jpg" | "png";
  quality?: number;
}

const DEFAULT_WIDTHS = [320, 480, 640, 768, 1024, 1280, 1536, 1920, 2048];

/**
 * 生成响应式 srcset 字符串（基于 Nuxt Image 的 /_ipx/ 约定或 CDN 参数约定）。
 * - 对于相对路径（/xxx）返回 /_ipx/w_{w},f_{f}/ 前缀；
 * - 对于 http(s) URL 返回 URL + query 参数拼接；
 * - 调用方再配合 <Img sizes="..." /> 使用。
 */
export function generateSrcSet(src: string, options: SrcSetOptions = {}): string {
  const widths = options.widths || DEFAULT_WIDTHS;
  const fmt = options.format || "webp";
  const q = options.quality ?? 80;
  return widths
    .map(w => {
      const url = generateResizedUrl(src, w, fmt, q);
      return `${url} ${w}w`;
    })
    .join(", ");
}

export function generateResizedUrl(
  src: string,
  width: number,
  format: string,
  quality = 80
): string {
  if (!src) return src;
  if (src.startsWith("http://") || src.startsWith("https://")) {
    const u = new URL(src);
    u.searchParams.set("w", String(width));
    u.searchParams.set("fmt", format);
    u.searchParams.set("q", String(quality));
    return u.toString();
  }
  return `/_ipx/w_${width},f_${format},q_${quality}${src.startsWith("/") ? src : `/${src}`}`;
}

/**
 * 计算宽高比（width / height）。缺少任一侧返回 1（1:1）。
 */
export function aspectRatio(width?: number, height?: number): number {
  if (!width || !height || width <= 0 || height <= 0) return 1;
  return width / height;
}

/**
 * 根据父容器宽度 + 期望的纵横比，算出对应高度的 CSS paddingBottom 字符串
 * （用于「图片加载前占坑」避免 CLS）。
 */
export function aspectPaddingBottom(width?: number, height?: number): string {
  const ratio = aspectRatio(width, height);
  return `${(1 / ratio) * 100}%`;
}

/**
 * sizes 字符串生成器：给不同断点下图片显示宽度的典型值。
 * 适配「最大 1200px 容器、两栏 / 三栏」布局。
 */
export function defaultSizes(layout: "post" | "card" | "gallery" | "cover" = "post"): string {
  switch (layout) {
    case "cover":
      return "100vw";
    case "post":
      return "(max-width: 768px) 100vw, 768px";
    case "card":
      return "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw";
    case "gallery":
      return "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, (max-width: 1280px) 33vw, 25vw";
  }
}

/**
 * 简单的 LQIP 占位尺寸建议：长边缩放到 32 像素以内。
 */
export function suggestLqipSize(width?: number, height?: number): { w: number; h: number } {
  const w0 = width || 16;
  const h0 = height || 16;
  const maxEdge = Math.max(w0, h0);
  const scale = 32 / maxEdge;
  return { w: Math.max(1, Math.round(w0 * scale)), h: Math.max(1, Math.round(h0 * scale)) };
}
