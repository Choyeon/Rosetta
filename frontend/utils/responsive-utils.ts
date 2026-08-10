/**
 * Tailwind 断点下 useWindowSize / useMediaQuery 的通用组合：
 * 提供纯函数判断任意尺寸命中哪个断点。
 * composables/useWindowSize 会在这里拿常量，这里避免依赖 Vue。
 */

export const TAILWIND_BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  "2xl": 1536,
} as const;

export type TailwindBreakpoint = keyof typeof TAILWIND_BREAKPOINTS;

export function matchesBreakpoint(width: number, bp: TailwindBreakpoint): boolean {
  return width >= TAILWIND_BREAKPOINTS[bp];
}

/**
 * 返回当前宽度下「≥md、≥lg、≥xl、≥2xl」的布尔 map，便于 v-if 直接用。
 */
export function computeBreakpointState(width: number): Record<TailwindBreakpoint, boolean> {
  return {
    sm: matchesBreakpoint(width, "sm"),
    md: matchesBreakpoint(width, "md"),
    lg: matchesBreakpoint(width, "lg"),
    xl: matchesBreakpoint(width, "xl"),
    "2xl": matchesBreakpoint(width, "2xl"),
  };
}

/**
 * 根据 devicePixelRatio 估算「最佳图片宽度」：
 * 逻辑 CSS 宽度 × dpr 向上取最近的 srcset 桶。
 */
export function pickOptimalSrcWidth(
  cssWidthPx: number,
  dpr = import.meta.client ? (window.devicePixelRatio || 1) : 1,
  candidates: number[] = [320, 480, 640, 768, 1024, 1280, 1536, 1920, 2048]
): number {
  const need = Math.max(1, Math.ceil(cssWidthPx * dpr));
  for (const c of candidates) if (c >= need) return c;
  return candidates[candidates.length - 1] ?? need;
}

/**
 * viewport meta 适配的安全区高度计算（移动端 Safari 100vh 坑）。
 * 返回纯数字 px。
 */
export function computeDynamicViewportHeight(): number | null {
  if (!import.meta.client) return null;
  if (typeof window === "undefined") return null;
  const h =
    (window.visualViewport?.height as number | undefined) ??
    window.innerHeight ??
    (document.documentElement && document.documentElement.clientHeight);
  return Number.isFinite(h) ? (h as number) : null;
}
