/**
 * 统一分析埋点分发：Google Analytics / Umami / Microsoft Clarity / 51.la
 *   - 所有 provider 懒加载（通过 window 全局对象探测）
 *   - sendEvent 统一入口，带 fallback（埋点失败绝不影响业务）
 *   - SSR 安全：服务端直接 no-op 返回
 */
import { z } from "zod";

export const AnalyticsProviderSchema = z.enum([
  "google",
  "umami",
  "clarity",
  "la51",
]);
export type AnalyticsProvider = z.infer<typeof AnalyticsProviderSchema>;

export const AnalyticsEventSchema = z.object({
  name: z.string().min(1),
  params: z.record(z.union([z.string(), z.number(), z.boolean(), z.null()])).default({}),
  providers: z.array(AnalyticsProviderSchema).optional(),
});
export type AnalyticsEvent = z.infer<typeof AnalyticsEventSchema>;

export interface AnalyticsPageView {
  url?: string;
  title?: string;
  referrer?: string;
  providers?: AnalyticsProvider[];
}

type GtagFn = (cmd: "event" | "config" | "set", target: string, params?: Record<string, unknown>) => void;
type UmamiFn = { track: { (event: string, data?: Record<string, unknown>): void } };
type ClarityFn = (cmd: "event" | "set", key: string, value?: unknown) => void;
interface La51Window {
  _hmt?: Array<[string, ...unknown[]]>;
}

function safe(fn: () => void, providerName: string) {
  try {
    fn();
  } catch (err) {
    if (import.meta.dev) {
      console.debug(`[analytics:${providerName}] send failed`, err);
    }
  }
}

function isEnabled(key: AnalyticsProvider, allowList?: AnalyticsProvider[]): boolean {
  if (!allowList) return true;
  return allowList.includes(key);
}

function googleSendEvent(event: AnalyticsEvent) {
  const w = window as unknown as { gtag?: GtagFn };
  if (!w.gtag) return;
  w.gtag("event", event.name, event.params);
}

function googlePageView(pv: AnalyticsPageView) {
  const w = window as unknown as { gtag?: GtagFn };
  if (!w.gtag) return;
  const page_path = pv.url ?? window.location.pathname + window.location.search;
  const page_title = pv.title ?? document.title;
  w.gtag("config", "", {
    page_path,
    page_title,
    page_referrer: pv.referrer ?? document.referrer,
  });
}

function umamiSendEvent(event: AnalyticsEvent) {
  const w = window as unknown as { umami?: UmamiFn };
  if (!w.umami?.track) return;
  w.umami.track(event.name, event.params);
}

function umamiPageView(pv: AnalyticsPageView) {
  const w = window as unknown as { umami?: UmamiFn };
  if (!w.umami?.track) return;
  const url = pv.url ?? window.location.pathname + window.location.search;
  w.umami.track(url);
}

function claritySendEvent(event: AnalyticsEvent) {
  const w = window as unknown as { clarity?: ClarityFn };
  if (!w.clarity) return;
  w.clarity("event", event.name, event.params);
}

function clarityPageView(_pv: AnalyticsPageView) {
  const w = window as unknown as { clarity?: ClarityFn };
  if (!w.clarity) return;
  w.clarity("set", "pageview_ts", Date.now());
}

function la51SendEvent(event: AnalyticsEvent) {
  const w = window as unknown as La51Window;
  if (!w._hmt) return;
  w._hmt.push(["_trackEvent", event.name, JSON.stringify(event.params)]);
}

function la51PageView(pv: AnalyticsPageView) {
  const w = window as unknown as La51Window;
  if (!w._hmt) return;
  const url = pv.url ?? window.location.pathname + window.location.search;
  w._hmt.push(["_trackPageview", url]);
}

/**
 * 分析埋点入口。客户端调用，服务端自动 no-op。
 */
export function useAnalytics() {
  const enabled = ref<Record<AnalyticsProvider, boolean>>({
    google: false,
    umami: false,
    clarity: false,
    la51: false,
  });

  function detectProviders() {
    if (!import.meta.client) return;
    const w = window as unknown as {
      gtag?: GtagFn;
      umami?: UmamiFn;
      clarity?: ClarityFn;
      _hmt?: unknown;
    };
    enabled.value = {
      google: !!w.gtag,
      umami: !!w.umami?.track,
      clarity: !!w.clarity,
      la51: !!w._hmt,
    };
  }

  function sendEvent(raw: AnalyticsEvent | string, params: Record<string, unknown> = {}) {
    if (!import.meta.client) return;
    const parsed: AnalyticsEvent = typeof raw === "string"
      ? AnalyticsEventSchema.parse({ name: raw, params })
      : AnalyticsEventSchema.parse(raw);

    const { providers } = parsed;
    detectProviders();

    if (enabled.value.google && isEnabled("google", providers)) {
      safe(() => googleSendEvent(parsed), "google");
    }
    if (enabled.value.umami && isEnabled("umami", providers)) {
      safe(() => umamiSendEvent(parsed), "umami");
    }
    if (enabled.value.clarity && isEnabled("clarity", providers)) {
      safe(() => claritySendEvent(parsed), "clarity");
    }
    if (enabled.value.la51 && isEnabled("la51", providers)) {
      safe(() => la51SendEvent(parsed), "la51");
    }
  }

  function pageView(pv: AnalyticsPageView = {}) {
    if (!import.meta.client) return;
    detectProviders();
    const { providers } = pv;

    if (enabled.value.google && isEnabled("google", providers)) {
      safe(() => googlePageView(pv), "google");
    }
    if (enabled.value.umami && isEnabled("umami", providers)) {
      safe(() => umamiPageView(pv), "umami");
    }
    if (enabled.value.clarity && isEnabled("clarity", providers)) {
      safe(() => clarityPageView(pv), "clarity");
    }
    if (enabled.value.la51 && isEnabled("la51", providers)) {
      safe(() => la51PageView(pv), "la51");
    }
  }

  /**
   * 基于 Vue Router 自动监听路由变化并上报 PV。
   * 在 layout / app.vue 中调用一次即可（会自动 onMounted 注册）。
   */
  function trackRouteChanges() {
    if (!import.meta.client) return;
    onMounted(() => {
      const router = useRouter();
      const route = useRoute();
      pageView({
        url: route.fullPath,
        title: document.title,
      });
      router.afterEach((to, _from) => {
        // 下一帧上报（等 DOM title 更新）
        requestAnimationFrame(() => {
          pageView({
            url: to.fullPath,
            title: document.title,
          });
        });
      });
    });
  }

  return {
    enabled: readonly(enabled),
    sendEvent,
    pageView,
    trackRouteChanges,
    detectProviders,
  };
}
