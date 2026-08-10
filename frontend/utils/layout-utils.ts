/**
 * MainGrid 三栏布局判断 + 响应式断点的纯函数工具。
 * 不耦合任何 Vue reactivity，便于 server utils / 静态生成分支里复用。
 */

export type GridLayoutMode = "left" | "right" | "both" | "none";

export const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  "2xl": 1536,
} as const;

export type BreakpointKey = keyof typeof BREAKPOINTS;

/**
 * 根据「断点 + sidebar.position 配置」计算真实布局模式。
 * - 移动端（< md）一律返回 "none"（抽屉另算）
 * - position: left/right → 单栏对应方向
 * - position: both → 只有 ≥ xl 保留双栏，否则降级为 right 侧栏
 */
export function resolveGridLayout(
  position: "left" | "right" | "both",
  widthPx: number,
  options: { mobileCollapsed?: boolean; bothRequires?: BreakpointKey } = {}
): GridLayoutMode {
  const { mobileCollapsed = true, bothRequires = "xl" } = options;
  if (mobileCollapsed && widthPx < BREAKPOINTS.md) return "none";
  if (position === "both") {
    return widthPx >= BREAKPOINTS[bothRequires] ? "both" : "right";
  }
  return position;
}

/**
 * 主内容区最大可读宽度（px），用于文章页居中容器。
 */
export function resolveContentMaxWidth(
  layout: GridLayoutMode,
  sidebarWidthPx = 300,
  viewportPx = 1280
): number {
  const sidebars =
    layout === "both" ? sidebarWidthPx * 2 : layout === "left" || layout === "right" ? sidebarWidthPx : 0;
  const container = Math.min(1280, viewportPx);
  return Math.max(480, Math.min(860, container - sidebars - 48));
}

/**
 * 判断当前宽度所属最小 Tailwind 断点 key（≥ 取最大）。
 */
export function getActiveBreakpoint(widthPx: number): BreakpointKey {
  if (widthPx >= BREAKPOINTS["2xl"]) return "2xl";
  if (widthPx >= BREAKPOINTS.xl) return "xl";
  if (widthPx >= BREAKPOINTS.lg) return "lg";
  if (widthPx >= BREAKPOINTS.md) return "md";
  if (widthPx >= BREAKPOINTS.sm) return "sm";
  return "sm";
}

/**
 * 栅格系统列数：断点 → 建议列数（卡片 / 相册 / 友链页面通用）。
 */
export function suggestColumns(widthPx: number, maxCols = 4): number {
  const bp = getActiveBreakpoint(widthPx);
  switch (bp) {
    case "2xl":
      return Math.min(4, maxCols);
    case "xl":
      return Math.min(3, maxCols);
    case "lg":
      return Math.min(3, maxCols);
    case "md":
      return Math.min(2, maxCols);
    case "sm":
    default:
      return 1;
  }
}
