/**
 * TOC 数据结构与纯函数工具（树构建、扁平化、active 匹配）。
 * 供 toc-utils.ts / markdown-renderer.ts / ScrollSpy 组件共用。
 */

export interface TocEntry {
  id: string;
  text: string;
  level: 1 | 2 | 3 | 4 | 5 | 6;
}

export interface TocNode {
  id: string;
  text: string;
  level: 1 | 2 | 3 | 4 | 5 | 6;
  children: TocNode[];
}

/**
 * 将扁平 heading 列表构造成嵌套树。
 * - 任何比上一个更深的节点都成为其子节点；
 * - 任何返回更浅层的节点都「弹栈」到对应 level 的父节点；
 * - 缺失 h1 / h2 会自动补齐到根（不会抛错）。
 */
export function buildTocTree(entries: readonly TocEntry[]): TocNode[] {
  const root: TocNode[] = [];
  const stack: TocNode[] = [];
  for (const entry of entries) {
    const node: TocNode = {
      id: entry.id,
      text: entry.text,
      level: entry.level,
      children: [],
    };
    while (stack.length && stack[stack.length - 1].level >= node.level) {
      stack.pop();
    }
    const parent = stack.length ? stack[stack.length - 1] : null;
    (parent ? parent.children : root).push(node);
    stack.push(node);
  }
  return root;
}

/**
 * 把树重新扁平化为数组（保持文档顺序）。
 * ScrollSpy 用扁平数组计算 active 更高效。
 */
export function flattenToc(tree: readonly TocNode[]): TocEntry[] {
  const out: TocEntry[] = [];
  const walk = (nodes: readonly TocNode[]) => {
    for (const n of nodes) {
      out.push({ id: n.id, text: n.text, level: n.level });
      if (n.children.length) walk(n.children);
    }
  };
  walk(tree);
  return out;
}

/**
 * 计算当前滚动 Y 下的「活动 TOC 项 id」：
 * 最后一个 offset ≤ scrollY + headOffset 的 heading。
 * headOffset 用于补偿 fixed navbar / 顶部 banner 的遮挡。
 */
export function resolveActiveTocId(
  flat: readonly TocEntry[],
  scrollY: number,
  headOffset = 80
): string | null {
  if (!import.meta.client || !("document" in globalThis)) return null;
  let active: string | null = null;
  for (const e of flat) {
    const el = document.getElementById(e.id);
    if (!el) continue;
    const top = el.getBoundingClientRect().top + (window.scrollY || 0);
    if (top - headOffset <= scrollY) {
      active = e.id;
    } else {
      break;
    }
  }
  return active;
}
