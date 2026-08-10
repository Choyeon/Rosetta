/**
 * 用户 UI 偏好 Pinia Store：字号 / 紧凑模式 / 面板显隐 等。
 *   - 持久化：localStorage（客户端）+ cookie（SSR 兜底）
 *   - Zod 校验：读取时 safeParse，脏数据回落到默认值
 *   - 响应式：state 直接驱动 UI 组件
 */
import { defineStore } from "pinia";
import { z } from "zod";

export type FontSize = "xs" | "sm" | "md" | "lg" | "xl";
export type Density = "comfortable" | "default" | "compact";
export type PanelState = "show" | "hide";
export type ThemeMode = "light" | "dark";

export const ConfigStoreSchema = z.object({
  fontSize: z.enum(["xs", "sm", "md", "lg", "xl"]).default("md"),
  density: z.enum(["comfortable", "default", "compact"]).default("default"),
  leftSidebar: z.enum(["show", "hide"]).default("show"),
  rightSidebar: z.enum(["show", "hide"]).default("show"),
  tocPanel: z.enum(["show", "hide"]).default("show"),
  readerMode: z.boolean().default(false),
  reducedMotion: z.boolean().default(false),
  grayscale: z.boolean().default(false),
  highContrast: z.boolean().default(false),
});

export type ConfigStoreState = z.infer<typeof ConfigStoreSchema>;

const STORAGE_KEY = "rosetta_ui_prefs";
const COOKIE_KEY = "rosetta_ui_prefs";

function readPersisted(): Partial<ConfigStoreState> {
  if (import.meta.client) {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return {};
      const parsed = JSON.parse(raw) as unknown;
      const result = ConfigStoreSchema.partial().safeParse(parsed);
      return result.success ? result.data : {};
    } catch {
      return {};
    }
  }
  if (import.meta.server) {
    try {
      const cookie = useCookie<string | undefined>(COOKIE_KEY, { default: () => undefined });
      if (!cookie.value) return {};
      const parsed = JSON.parse(decodeURIComponent(cookie.value)) as unknown;
      const result = ConfigStoreSchema.partial().safeParse(parsed);
      return result.success ? result.data : {};
    } catch {
      return {};
    }
  }
  return {};
}

function writePersisted(state: ConfigStoreState) {
  const body = JSON.stringify(state);
  if (import.meta.client) {
    try {
      localStorage.setItem(STORAGE_KEY, body);
    } catch {
      /* storage disabled */
    }
  }
  const c = useCookie<string | undefined>(COOKIE_KEY, {
    path: "/",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 365,
  });
  c.value = encodeURIComponent(body);
}

export const useConfigStore = defineStore("ui-config", {
  state: (): ConfigStoreState => {
    const persisted = readPersisted();
    const defaults = ConfigStoreSchema.parse({});
    return { ...defaults, ...persisted };
  },
  getters: {
    fontSizePx(s): number {
      const map: Record<FontSize, number> = { xs: 13, sm: 14, md: 16, lg: 18, xl: 20 };
      return map[s.fontSize];
    },
    isCompact(s): boolean {
      return s.density === "compact";
    },
    isComfortable(s): boolean {
      return s.density === "comfortable";
    },
    showLeftSidebar(s): boolean {
      return s.leftSidebar === "show";
    },
    showRightSidebar(s): boolean {
      return s.rightSidebar === "show";
    },
    showToc(s): boolean {
      return s.tocPanel === "show";
    },
  },
  actions: {
    setFontSize(size: FontSize) {
      this.fontSize = size;
      this.persist();
    },
    setDensity(density: Density) {
      this.density = density;
      this.persist();
    },
    toggleLeftSidebar() {
      this.leftSidebar = this.leftSidebar === "show" ? "hide" : "show";
      this.persist();
    },
    toggleRightSidebar() {
      this.rightSidebar = this.rightSidebar === "show" ? "hide" : "show";
      this.persist();
    },
    toggleToc() {
      this.tocPanel = this.tocPanel === "show" ? "hide" : "show";
      this.persist();
    },
    setReaderMode(on: boolean) {
      this.readerMode = on;
      this.persist();
    },
    setReducedMotion(on: boolean) {
      this.reducedMotion = on;
      this.persist();
    },
    setGrayscale(on: boolean) {
      this.grayscale = on;
      this.persist();
    },
    setHighContrast(on: boolean) {
      this.highContrast = on;
      this.persist();
    },
    reset() {
      const defaults = ConfigStoreSchema.parse({});
      Object.assign(this, defaults);
      this.persist();
    },
    patch(partial: Partial<ConfigStoreState>) {
      const merged = { ...this.$state, ...partial };
      const result = ConfigStoreSchema.safeParse(merged);
      if (result.success) {
        Object.assign(this, result.data);
        this.persist();
      }
    },
    persist() {
      const snap = ConfigStoreSchema.parse({ ...this.$state });
      writePersisted(snap);
    },
  },
});
