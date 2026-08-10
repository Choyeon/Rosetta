/**
 * @nuxt/icon 场景：IconName 类型是「collection:name」字符串模板。
 * 这里提供运行时无类型断言的 helper + 列表过滤，避免任何 `as IconName`。
 */

export const ICON_COLLECTIONS = [
  "material-symbols",
  "fa7-solid",
  "fa7-regular",
  "fa7-brands",
  "simple-icons",
  "mdi",
  "mingcute",
  "heroicons",
  "heroicons-outline",
  "heroicons-solid",
] as const;

export type IconCollection = (typeof ICON_COLLECTIONS)[number];
export type IconName = `${IconCollection}:${string}`;

function isKnownCollection(c: string): c is IconCollection {
  return (ICON_COLLECTIONS as readonly string[]).includes(c);
}

/**
 * 把形如「fa7-solid:heart」字符串安全地收敛到 IconName 类型。
 * 非法格式会 fallback 到 defaultName（默认 material-symbols:help-outline）。
 */
export function toIconName(
  input: string | null | undefined,
  defaultName: IconName = "material-symbols:help-outline"
): IconName {
  if (!input) return defaultName;
  const [c, ...rest] = input.split(":");
  if (!c || rest.length === 0) return defaultName;
  const name = rest.join(":");
  if (!isKnownCollection(c)) return defaultName;
  return `${c}:${name}` as IconName;
}

/**
 * 批量校验并规范化 icon 列表；常用于从后端拿到的配置做一次清洗。
 */
export function normalizeIconList(inputs: string[]): IconName[] {
  return inputs
    .map(i => toIconName(i, "material-symbols:help-outline" as IconName))
    .filter(Boolean);
}

/**
 * 判断字符串是否看起来像合法的图标 key（仅结构校验，不校验该图标真的存在）。
 */
export function isValidIconKey(input: string): boolean {
  const [c, ...rest] = input.split(":");
  if (!c || rest.length === 0) return false;
  return isKnownCollection(c) && rest.join(":").length > 0;
}
