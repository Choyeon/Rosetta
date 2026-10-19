/**
 * 分页页码窗口的唯一算法：给定当前页与总页数，回最多 `size` 个可点页码。
 *
 * 为什么要有单源：这段"先按居中开窗、尾部不够就把窗口整体往前挪"的逻辑原先被逐字抄在
 * 6 个页面里（文章列表、搜索、留言板、分类详情、标签详情、作者主页）。抄写的风险不是
 * 行数，而是**只有其中一处会被修**：窗口不往前挪时，最后一页附近的页码会少显示一半，
 * 而另外 5 处照样带着同一个缺陷继续活。
 *
 * 边界口径（有单测钉住）：
 *   · total ≤ 0 → 空数组（没内容就不该有点亮的页码，而不是"第 1 页"）
 *   · current 越界（分享出去的 ?page=9 而库里只剩 3 页）→ 拉回最后一个满窗口，
 *     而不是回空列表——页码条不能因为 URL 脏了就整条消失。
 */

/** 默认窗口宽度：6 个页面历史上都用 5，改动会让页码条宽度突变。 */
export const PAGE_WINDOW_SIZE = 5

export function pageWindow(
  current: number,
  total: number,
  size: number = PAGE_WINDOW_SIZE
): number[] {
  const pages: number[] = []
  let start = Math.max(1, current - Math.floor(size / 2))
  const end = Math.min(total, start + size - 1)
  if (end - start + 1 < size) start = Math.max(1, end - size + 1)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
}
