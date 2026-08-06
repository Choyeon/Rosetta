/**
 * snake_case -> camelCase 递归转换工具
 * 手写 50 行内，不引入第三方依赖。
 *
 * 用法：
 *   const apiData = { page_size: 10, created_at: "2024-01-01", items: [{ user_id: 1 }] };
 *   const ui = camelizeKeys(apiData); // { pageSize: 10, createdAt: "...", items: [{ userId: 1 }] }
 */

const SNAKE_RE = /_([a-z0-9])/g;

function snakeToCamel(str: string): string {
	if (!str.includes("_")) return str;
	return str.replace(SNAKE_RE, (_m, c) => c.toUpperCase());
}

const CAMEL_RE = /([a-z0-9])([A-Z])/g;

function camelToSnake(str: string): string {
	return str.replace(CAMEL_RE, "$1_$2").toLowerCase();
}

function walk<T>(obj: T, fn: (s: string) => string): any {
	if (obj === null || obj === undefined) return obj;
	if (Array.isArray(obj)) return obj.map((v) => walk(v, fn));
	if (typeof obj !== "object") return obj;
	if (obj instanceof Date) return obj;
	const out: Record<string, any> = {};
	for (const key of Object.keys(obj)) {
		const newKey = typeof key === "string" ? fn(key) : key;
		out[newKey] = walk((obj as any)[key], fn);
	}
	return out;
}

export function camelizeKeys<T = any>(obj: T): T {
	return walk(obj, snakeToCamel) as T;
}

export function snakeizeKeys<T = any>(obj: T): T {
	return walk(obj, camelToSnake) as T;
}
