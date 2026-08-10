/**
 * 并发请求去重：在同一次事件循环里，相同 key 的 fetchAsync 只会真正调用一次，
 * 后续调用直接复用同一个 Promise。
 *
 * @example
 *   const load = dedupFetch<Post[]>("posts:list", () => $fetch("/api/posts"));
 *   const [a, b] = await Promise.all([load(), load()]); // 实际只发一次
 */
type Task<T> = {
  promise: Promise<T>;
  createdAt: number;
  ttlMs: number;
};

const DEFAULT_TTL_MS = 250;
const _tasks = new Map<string, Task<unknown>>();

export function clearDedupCache(key?: string): void {
  if (key) _tasks.delete(key);
  else _tasks.clear();
}

export function dedupFetch<T>(
  key: string,
  fetcher: () => Promise<T>,
  options: { ttlMs?: number; onError?: (err: unknown) => void } = {}
): () => Promise<T> {
  const { ttlMs = DEFAULT_TTL_MS, onError } = options;
  return () => {
    const now = Date.now();
    const existing = _tasks.get(key) as Task<T> | undefined;
    if (existing && now - existing.createdAt < existing.ttlMs) {
      return existing.promise;
    }
    const promise = (async () => {
      try {
        return await fetcher();
      } catch (err) {
        _tasks.delete(key);
        onError?.(err);
        throw err;
      }
    })();
    _tasks.set(key, { promise: promise as Promise<unknown>, createdAt: now, ttlMs });
    return promise;
  };
}

/**
 * 缓存成功结果的「带保质期」版本；适用于不常变的配置 / 字典数据。
 */
export function withCache<T>(
  key: string,
  fetcher: () => Promise<T>,
  options: { staleMs: number; revalidate?: () => boolean } = { staleMs: 60_000 }
): () => Promise<T> {
  let cached: { value: T; at: number } | null = null;
  let inFlight: Promise<T> | null = null;
  return async () => {
    const now = Date.now();
    if (cached && now - cached.at < options.staleMs && (!options.revalidate || !options.revalidate())) {
      return cached.value;
    }
    if (inFlight) return inFlight;
    inFlight = (async () => {
      try {
        const value = await fetcher();
        cached = { value, at: Date.now() };
        return value;
      } finally {
        inFlight = null;
      }
    })();
    return inFlight;
  };
}
