/**
 * Auth 鉴权状态（Pinia Store）—— 对应 Astro frontend/src/api/client.ts
 *   - Token 双份存储（localStorage + Pinia 内存态 + 同步到 Cookie，使 SSR 也可见）
 *   - 登录 → 登出 → 401 自动登出 → JWT/RBAC 结构
 * 注意：FastAPI 后端 JWT → Authorization: Bearer <access_token>
 *       / 刷新 token: rosetta_refresh_token
 */
import { defineStore } from "pinia";

export type Role = "super_admin" | "admin" | "editor" | "author" | "contributor" | "guest" | "user";
export interface CurrentUser {
  id: number;
  username: string;
  nickname?: string;
  email?: string;
  avatar?: string;
  roles: Role[];
  permissions: string[];
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: CurrentUser | null;
  csrfToken: string | null;
}

const TOKEN_KEY = "rosetta_token";
const REFRESH_KEY = "rosetta_refresh_token";

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    accessToken: null,
    refreshToken: null,
    user: null,
    csrfToken: null,
  }),
  getters: {
    isLogged: (s): boolean => !!s.accessToken,
    isAdmin: (s): boolean => !!s.user?.roles?.some(r => ["super_admin", "admin"].includes(r)),
    canEdit: (s): boolean =>
      !!s.user?.roles?.some(r =>
        ["super_admin", "admin", "editor", "author"].includes(r)
      ),
    displayName: (s): string => s.user?.nickname || s.user?.username || "访客",
  },
  actions: {
    /** 初始化：从持久化（localStorage / cookie）恢复登录态 */
    init() {
      if (import.meta.client) {
        try {
          this.accessToken = localStorage.getItem(TOKEN_KEY);
          this.refreshToken = localStorage.getItem(REFRESH_KEY);
        } catch {
          /* storage disabled */
        }
        // SSR 场景：从 cookie 中读 token
      } else if (import.meta.server) {
        const cookie = useCookie<string | undefined>(TOKEN_KEY, { default: () => undefined });
        this.accessToken = cookie.value ?? null;
      }
    },

    setAuth(payload: { access_token: string; refresh_token?: string | null; user?: CurrentUser | null }) {
      this.accessToken = payload.access_token;
      this.refreshToken = payload.refresh_token ?? null;
      this.user = payload.user ?? null;
      // localStorage（仅客户端）
      if (import.meta.client) {
        try {
          if (this.accessToken) localStorage.setItem(TOKEN_KEY, this.accessToken);
          else localStorage.removeItem(TOKEN_KEY);
          if (this.refreshToken) localStorage.setItem(REFRESH_KEY, this.refreshToken);
          else localStorage.removeItem(REFRESH_KEY);
        } catch {
          /* ignore */
        }
      }
      // Cookie：让 SSR 请求也能携带（HttpOnly=false 以便前端可读，安全由 HTTPS + SameSite=Lax 保证）
      const a = useCookie<string | undefined>(TOKEN_KEY, {
        path: "/",
        sameSite: "lax",
        maxAge: 60 * 60 * 24 * 7, // 7 天
      });
      a.value = this.accessToken || undefined;

      const r = useCookie<string | undefined>(REFRESH_KEY, {
        path: "/",
        sameSite: "lax",
        maxAge: 60 * 60 * 24 * 14,
      });
      r.value = this.refreshToken || undefined;
    },

    setCsrf(csrf: string | null) {
      this.csrfToken = csrf;
      if (import.meta.client && csrf) {
        document.cookie = `csrf_token=${encodeURIComponent(csrf)}; path=/; SameSite=Lax`;
      }
    },

    logout() {
      this.accessToken = null;
      this.refreshToken = null;
      this.user = null;
      this.csrfToken = null;
      if (import.meta.client) {
        try {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(REFRESH_KEY);
        } catch {
          /* ignore */
        }
      }
      const a = useCookie(TOKEN_KEY);
      a.value = null;
      const r = useCookie(REFRESH_KEY);
      r.value = null;
    },

    /** 权限判定（RBAC） */
    hasRole(role: Role | Role[]): boolean {
      if (!this.user?.roles) return false;
      const arr = Array.isArray(role) ? role : [role];
      return this.user.roles.some(r => arr.includes(r));
    },
    hasPerm(perm: string | string[]): boolean {
      if (!this.user?.permissions) return false;
      // super_admin 通配
      if (this.user.roles.includes("super_admin")) return true;
      const arr = Array.isArray(perm) ? perm : [perm];
      return arr.every(p => this.user!.permissions.includes(p));
    },
  },
  hydrate(state, initialState) {
    // SSR 传过来的 cookie → 客户端初始化时合并
    if (initialState) Object.assign(state, initialState);
  },
});
