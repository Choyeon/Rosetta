import type { Photo } from "../types/galleryConfig";

/**
 * 瀑布流列分配：按「当前列累积高度贪心」把照片分到最短列。
 * 返回长度与 columns 相等的 Photo[][]，不会丢失元素。
 *
 * @param photos 照片数组（建议包含 width/height；缺失按 1:1 估算）
 * @param columns 列数 ≥1
 * @param gap 间距（逻辑像素，仅用于累积高度一致性）
 */
export function assignMasonryColumns<T extends Photo>(
  photos: T[],
  columns = 3,
  gap = 12
): T[][] {
  const cols = Math.max(1, Math.floor(columns));
  const heights = new Array<number>(cols).fill(0);
  const buckets: T[][] = Array.from({ length: cols }, () => [] as T[]);
  for (const p of photos) {
    const ratio = p.width && p.height ? p.width / p.height : 1;
    const height = 200 / Math.max(0.2, Math.min(5, ratio));
    let bestIdx = 0;
    for (let i = 1; i < cols; i++) {
      if (heights[i] < heights[bestIdx]) bestIdx = i;
    }
    buckets[bestIdx].push(p);
    heights[bestIdx] += height + gap;
  }
  return buckets;
}

/**
 * 从 photos 中提取 EXIF 拍摄日期（takenAt 字段），缺失回退到当前时间，
 * 按「YYYY」或「YYYY-MM」分组输出，页面归档侧边栏直接用。
 */
export function groupPhotosByTakenDate(
  photos: Photo[],
  granularity: "year" | "month" = "month"
): Map<string, Photo[]> {
  const fmt = granularity === "year" ? "YYYY" : "YYYY-MM";
  const buckets = new Map<string, Photo[]>();
  for (const p of photos) {
    const stamp = p.takenAt && !Number.isNaN(new Date(p.takenAt).getTime())
      ? new Date(p.takenAt)
      : new Date();
    const key =
      fmt === "YYYY"
        ? String(stamp.getFullYear())
        : `${stamp.getFullYear()}-${String(stamp.getMonth() + 1).padStart(2, "0")}`;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key)!.push(p);
  }
  return new Map([...buckets.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1)));
}

/**
 * 给定照片列表 + 列宽，估算每张在瀑布流中的渲染高度。
 * 纯前端在图片未加载前用来提前占坑，减少 CLS。
 */
export function estimatePhotoHeight(
  photo: Photo,
  columnWidth: number
): number {
  const ratio =
    photo.width && photo.height ? photo.height / photo.width : 1;
  return Math.round(columnWidth * ratio);
}
