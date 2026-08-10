import type { z, ZodSchema } from "zod";
import { nanoid } from "nanoid";
import Cookies from "js-cookie";
import { aesDecrypt, aesEncrypt } from "./crypto-utils";

/**
 * 带过期 TTL 的 localStorage 工具；读回时自动 schema 校验，失败静默回退 default。
 * - SSR 环境：不读写真实存储，总是返回 default；
 * - 前端：localStorage 里保存一个包 { value, exp, sig }，避免被随意修改。
 */
export interface PersistedOptions<T> {
  key: string;
  schema: ZodSchema<T>;
  defaultValue: T;
  ttlMs?: number;
  secret?: string;
  storage?: "local" | "session";
}

interface Wrapped<T> {
  v: T;
  exp: number | null;
  sig: string;
}

function getStorage(kind: "local" | "session"): Storage | null {
  if (!import.meta.client) return null;
  try {
    return kind === "local" ? window.localStorage : window.sessionStorage;
  } catch {
    return null;
  }
}

export function definePersistedSetting<T>(options: PersistedOptions<T>) {
  const { key, schema, defaultValue, ttlMs, secret, storage: kind = "local" } = options;
  const storageKey = `rosetta:${key}`;
  const sigSalt = secret || key;

  function sign(v: unknown, exp: number | null): string {
    const s = JSON.stringify({ v, exp });
    return sigSalt.split("").reduceRight((acc, ch) => `${ch}${acc}`, s).slice(0, 16);
  }

  function get(): T {
    const storage = getStorage(kind);
    if (!storage) return defaultValue;
    const raw = storage.getItem(storageKey);
    if (!raw) return defaultValue;
    try {
      const data = JSON.parse(raw) as Wrapped<T>;
      if (data.exp && Date.now() > data.exp) {
        storage.removeItem(storageKey);
        return defaultValue;
      }
      const expected = sign(data.v, data.exp);
      if (expected !== data.sig) {
        storage.removeItem(storageKey);
        return defaultValue;
      }
      const parsed = schema.safeParse(data.v);
      return parsed.success ? parsed.data : defaultValue;
    } catch {
      storage.removeItem(storageKey);
      return defaultValue;
    }
  }

  function set(value: T): boolean {
    const storage = getStorage(kind);
    if (!storage) return false;
    const validated = schema.safeParse(value);
    if (!validated.success) return false;
    const exp = ttlMs ? Date.now() + ttlMs : null;
    const wrapped: Wrapped<T> = { v: validated.data, exp, sig: sign(validated.data, exp) };
    try {
      storage.setItem(storageKey, JSON.stringify(wrapped));
      return true;
    } catch {
      return false;
    }
  }

  function remove(): void {
    getStorage(kind)?.removeItem(storageKey);
  }

  return { get, set, remove, key: storageKey };
}

/**
 * 带 AES 的敏感设置（token 等）。localStorage + 加密 + TTL。
 * 不强依赖 Zod（这里只对读写做包装）。
 */
export function defineSecretSetting<T extends string | Record<string, unknown>>(options: {
  key: string;
  secret: string;
  defaultValue: T;
  ttlMs?: number;
}) {
  const storageKey = `rosetta:sec:${options.key}`;
  const ttlKey = `${storageKey}:exp`;

  function get(): T {
    if (!import.meta.client) return options.defaultValue;
    try {
      const cipher = localStorage.getItem(storageKey);
      if (!cipher) return options.defaultValue;
      const exp = Number(localStorage.getItem(ttlKey));
      if (options.ttlMs && Number.isFinite(exp) && Date.now() > exp) {
        localStorage.removeItem(storageKey);
        localStorage.removeItem(ttlKey);
        return options.defaultValue;
      }
      const plain = aesDecrypt(cipher, options.secret);
      if (!plain) return options.defaultValue;
      if (typeof options.defaultValue === "string") return plain as T;
      return JSON.parse(plain) as T;
    } catch {
      return options.defaultValue;
    }
  }

  function set(value: T): boolean {
    if (!import.meta.client) return false;
    try {
      const plain = typeof value === "string" ? value : JSON.stringify(value);
      localStorage.setItem(storageKey, aesEncrypt(plain, options.secret));
      if (options.ttlMs) localStorage.setItem(ttlKey, String(Date.now() + options.ttlMs));
      return true;
    } catch {
      return false;
    }
  }

  function remove(): void {
    if (!import.meta.client) return;
    localStorage.removeItem(storageKey);
    localStorage.removeItem(ttlKey);
  }

  return { get, set, remove, key: storageKey };
}

/**
 * 基于 js-cookie 的一次性 / 会话级偏好（用户已关闭公告、locale 等）。
 * 读写支持 Zod schema 校验。
 */
export function defineCookieSetting<T>(options: {
  name: string;
  schema: ZodSchema<T>;
  defaultValue: T;
  days?: number;
  sameSite?: "Lax" | "Strict" | "None";
  secure?: boolean;
}) {
  const { name, schema, defaultValue, days, sameSite = "Lax", secure } = options;

  function get(): T {
    if (!import.meta.client) return defaultValue;
    const raw = Cookies.get(name);
    if (!raw) return defaultValue;
    const result = schema.safeParse(raw);
    return result.success ? result.data : defaultValue;
  }

  function set(value: T): void {
    if (!import.meta.client) return;
    const result = schema.safeParse(value);
    if (!result.success) return;
    Cookies.set(name, String(result.data), {
      expires: days,
      sameSite,
      secure,
      path: "/",
    });
  }

  function remove(): void {
    if (!import.meta.client) return;
    Cookies.remove(name, { path: "/" });
  }

  return { get, set, remove };
}

export { nanoid as genId };
export type ZodInferred<T extends ZodSchema> = z.infer<T>;
