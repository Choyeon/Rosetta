/**
 * 递归地将对象 / 数组的 key 由 snake_case / SCREAMING_SNAKE / kebab-case 转换为 camelCase。
 * - 字符串值原样保留
 * - Date / Map / Set / RegExp / Blob 等非普通对象原样透传
 * - 纯 JSON 场景下可用的无副作用实现（零运行时类型断言）
 */

const RE_SNAKE = /[_-]+(.)?/g;

function camelKey(key: string): string {
  if (!key) return key;
  if (/^[A-Z0-9_]+$/.test(key)) {
    return key.toLowerCase().replace(RE_SNAKE, (_, ch: string | undefined) => (ch ? ch.toUpperCase() : ""));
  }
  return key.replace(RE_SNAKE, (_, ch: string | undefined) => (ch ? ch.toUpperCase() : ""));
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  if (!value || typeof value !== "object") return false;
  const proto = Object.getPrototypeOf(value);
  return proto === null || proto === Object.prototype;
}

type Camelized<T> = T extends Array<infer U>
  ? Array<Camelized<U>>
  : T extends Record<string, unknown>
    ? { [K in string & keyof T as K extends string ? CamelizeString<K> : K]: Camelized<T[K]> }
    : T;

type CamelizeString<S extends string> = S extends `${infer Head}_${infer Tail}`
  ? `${Head}${Capitalize<CamelizeString<Tail>>}`
  : S extends `${infer Head}-${infer Tail}`
    ? `${Head}${Capitalize<CamelizeString<Tail>>}`
    : Lowercase<S> extends S ? S : Uncapitalize<S>;

export function camelize<T>(value: T): Camelized<T> {
  if (Array.isArray(value)) {
    return value.map(item => camelize(item as unknown)) as Camelized<T>;
  }
  if (!isPlainObject(value)) {
    return value as Camelized<T>;
  }
  const out: Record<string, unknown> = {};
  for (const [key, val] of Object.entries(value)) {
    out[camelKey(key)] = camelize(val);
  }
  return out as Camelized<T>;
}

/**
 * 反向：camelCase → snake_case（服务端 payload 构造时使用）。
 */
export function decamelize<T>(value: T): T {
  const RE_CAMEL = /([a-z0-9])([A-Z])/g;
  function snake(key: string): string {
    return key.replace(RE_CAMEL, "$1_$2").toLowerCase();
  }
  if (Array.isArray(value)) {
    return value.map(item => decamelize(item as unknown)) as T;
  }
  if (!isPlainObject(value)) {
    return value;
  }
  const out: Record<string, unknown> = {};
  for (const [key, val] of Object.entries(value)) {
    out[snake(key)] = decamelize(val);
  }
  return out as T;
}
