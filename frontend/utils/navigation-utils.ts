import type { NavItem } from "../types/navBarConfig";

/**
 * 扁平化导航树为 { id, path: NavItem[] } 列表，面包屑 / 搜索场景直接用。
 */
export interface FlatNavEntry {
  id: string;
  item: NavItem;
  parentIds: string[];
  depth: number;
}

export function flattenNav(items: NavItem[]): FlatNavEntry[] {
  const out: FlatNavEntry[] = [];
  const walk = (list: NavItem[], parents: string[], depth: number) => {
    for (const it of list) {
      if (!it.enabled) continue;
      out.push({ id: it.id, item: it, parentIds: parents, depth });
      if (it.children?.length) walk(it.children, [...parents, it.id], depth + 1);
    }
  };
  walk(sorted(items), [], 0);
  return out;
}

function sorted<T extends { order?: number }>(arr: T[]): T[] {
  return [...arr].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
}

/**
 * 从当前 pathname 反推「激活的导航项 + 面包屑祖先链」。
 * 支持 /a/b/c 多段匹配：如果当前 path 比 nav.href 更长且以 href 开头，则祖先链中包含该项。
 */
export function resolveActiveNav(
  items: NavItem[],
  pathname: string,
  options: { exact?: boolean } = {}
): { active: FlatNavEntry | null; breadcrumb: FlatNavEntry[] } {
  const flat = flattenNav(items);
  const p = stripTrailing(pathname || "/");
  const matches = flat.filter(({ item }) => {
    const h = stripTrailing(item.href || "/");
    return options.exact ? h === p : p === h || (h !== "/" && p.startsWith(`${h}/`));
  });
  if (matches.length === 0) return { active: null, breadcrumb: [] };
  const active = matches.reduce((a, b) => (a.item.href.length >= b.item.href.length ? a : b));
  const breadcrumb = [
    ...active.parentIds
      .map(pid => flat.find(f => f.id === pid))
      .filter((x): x is FlatNavEntry => !!x),
    active,
  ];
  return { active, breadcrumb };
}

/**
 * 给定侧边栏「分类树 / 标签云 / 最近文章」这种二级列表，
 * 构造出侧边栏面板可直接渲染的层级项（icon 缺失就补默认）。
 */
export interface SidebarGroupItem {
  key: string;
  label: string;
  href?: string;
  count?: number;
  active?: boolean;
  children?: SidebarGroupItem[];
}

export function toSidebarItems<T extends { slug?: string; name?: string; count?: number; title?: string; children?: T[] }>(
  list: T[],
  basePath: string,
  currentPath: string
): SidebarGroupItem[] {
  return list.map(item => {
    const slug = item.slug || (item.name ? String(item.name).toLowerCase() : "");
    const href = slug ? joinPath(basePath, slug) : undefined;
    const label = item.name || item.title || slug;
    return {
      key: slug || label,
      label,
      href,
      count: item.count,
      active: href ? stripTrailing(currentPath) === stripTrailing(href) : false,
      children: item.children ? toSidebarItems(item.children, basePath, currentPath) : undefined,
    };
  });
}

function joinPath(a: string, b: string): string {
  return `${a.replace(/\/+$/, "")}/${b.replace(/^\/+/, "")}`;
}

function stripTrailing(s: string): string {
  const r = s.replace(/\/+$/, "") || "/";
  const i = r.indexOf("?");
  return i >= 0 ? r.slice(0, i) : r;
}
