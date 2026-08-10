/**
 * Popup / Notification 状态管理（对应 Astro GlobalPopupManager.ts）
 * 三种全局浮层：
 *   - Announcements（站点公告：顶栏条、横幅、模态弹窗）
 *   - SiteBanners（通用弹窗：营销、活动、更新）
 *   - ContentReminders（文章提醒：续读、分享、打赏）
 *
 * 使用示例：
 *   const pm = usePopupManager();
 *   pm.enqueue({ type: 'banner', ... });
 *   <BaseModal v-model:open="pm.bannerVisible">...</BaseModal>
 */
export interface BasePopupItem {
  id: string | number;
  /** 每次进入站点头 1 条；session 级去重 */
  frequency?: "always" | "once" | "session";
  /** 不展示的路由规则 */
  excludePaths?: string[];
  /** 仅展示的路由规则 */
  includePaths?: string[];
}
export interface AnnouncementItem extends BasePopupItem {
  kind: "top-bar" | "banner" | "modal";
  title?: string;
  content: string;
  cta?: { label: string; href: string };
  tone?: "info" | "warning" | "success" | "danger";
  /** 顶栏可关闭 */
  dismissable?: boolean;
  /** 定时毫秒：N 毫秒后隐藏 */
  autoHideMs?: number;
}
export interface SiteBannerItem extends BasePopupItem {
  title?: string;
  content: string;
  cover?: string;
  cta?: { label: string; href: string };
  /** 不展示日期 */
  startAt?: string;
  endAt?: string;
}
export interface ContentReminderItem extends BasePopupItem {
  trigger: "comment" | "share" | "reward" | "subscribe" | "cta" | "read";
  title: string;
  content?: string;
  /** 触发阈值（read 触发时：滚动 Y% 显示） */
  threshold?: number;
  cta?: { label: string; href: string };
}

export type PopupItem = AnnouncementItem | SiteBannerItem | ContentReminderItem;

// 客户端 sessionStorage 去重 Key
const SESSION_KEY = "rosetta.popups.shown";

function isInRange(item: { startAt?: string; endAt?: string }): boolean {
  const now = Date.now();
  if (item.startAt && new Date(item.startAt).getTime() > now) return false;
  if (item.endAt && new Date(item.endAt).getTime() < now) return false;
  return true;
}
function matchPath(rule?: string[], pathname?: string): boolean {
  if (!rule || !rule.length) return true;
  const p = pathname || (import.meta.client ? window.location.pathname : "/");
  return rule.some(r => {
    if (r.endsWith("/**")) {
      return p.startsWith(r.slice(0, -2));
    }
    return p === r;
  });
}
function markShown(id: string | number, freq?: string) {
  if (!import.meta.client) return;
  if (freq === "always") return;
  try {
    const store =
      freq === "session" ? window.sessionStorage : window.localStorage;
    const set = new Set<string>(JSON.parse(store.getItem(SESSION_KEY) || "[]"));
    set.add(String(id));
    store.setItem(SESSION_KEY, JSON.stringify([...set]));
  } catch {
    /* ignore */
  }
}
function wasShown(id: string | number, freq?: string): boolean {
  if (!import.meta.client) return false;
  if (freq === "always") return false;
  try {
    const store =
      freq === "session" ? window.sessionStorage : window.localStorage;
    const list = JSON.parse(store.getItem(SESSION_KEY) || "[]") as string[];
    return list.includes(String(id));
  } catch {
    return false;
  }
}

// Singleton store（Pinia 风格但无需 pinia，直接 reactive 即可）
import { reactive, computed, watch } from "vue";
const _state = reactive({
  announcements: [] as AnnouncementItem[],
  banners: [] as SiteBannerItem[],
  reminders: [] as ContentReminderItem[],
  topBar: null as AnnouncementItem | null,
  modalAnnouncement: null as AnnouncementItem | null,
  currentBanner: null as SiteBannerItem | null,
  currentReminder: null as ContentReminderItem | null,
});

function enqueueAnnouncement(item: AnnouncementItem) {
  if (wasShown(item.id, item.frequency)) return;
  if (!matchPath(item.includePaths) || matchPath(item.excludePaths)) return;
  if (!isInRange(item)) return;
  _state.announcements.push(item);
  // top-bar 优先级：显示第一条，其他可折叠
  if (item.kind === "top-bar" && !_state.topBar) {
    _state.topBar = item;
  }
  if (item.kind === "modal" && !_state.modalAnnouncement) {
    _state.modalAnnouncement = item;
  }
  if (item.autoHideMs && item.autoHideMs > 0) {
    setTimeout(() => {
      if (_state.topBar?.id === item.id) dismissAnnouncement(item.id);
      if (_state.modalAnnouncement?.id === item.id) dismissAnnouncement(item.id);
    }, item.autoHideMs);
  }
}
function dismissAnnouncement(id: string | number) {
  const it = _state.announcements.find(a => a.id === id);
  if (it) markShown(it.id, it.frequency);
  if (_state.topBar?.id === id) _state.topBar = null;
  if (_state.modalAnnouncement?.id === id) _state.modalAnnouncement = null;
  _state.announcements = _state.announcements.filter(a => a.id !== id);
}

function enqueueBanner(b: SiteBannerItem) {
  if (wasShown(b.id, b.frequency)) return;
  if (!matchPath(b.includePaths) || matchPath(b.excludePaths)) return;
  if (!isInRange(b)) return;
  _state.banners.push(b);
  if (!_state.currentBanner) _state.currentBanner = b;
}
function dismissBanner(id: string | number) {
  const it = _state.banners.find(a => a.id === id);
  if (it) markShown(it.id, it.frequency);
  if (_state.currentBanner?.id === id) _state.currentBanner = null;
  _state.banners = _state.banners.filter(a => a.id !== id);
}

function enqueueReminder(r: ContentReminderItem) {
  if (wasShown(r.id, r.frequency)) return;
  if (!matchPath(r.includePaths) || matchPath(r.excludePaths)) return;
  _state.reminders.push(r);
  if (!_state.currentReminder) _state.currentReminder = r;
}
function dismissReminder(id: string | number) {
  const it = _state.reminders.find(a => a.id === id);
  if (it) markShown(it.id, it.frequency);
  if (_state.currentReminder?.id === id) _state.currentReminder = null;
  _state.reminders = _state.reminders.filter(a => a.id !== id);
}

// 响应式：队列头有候选且 currentX 为空 → 自动出队
watch(
  [() => _state.banners, () => _state.currentBanner],
  () => {
    if (!_state.currentBanner && _state.banners.length > 0) {
      _state.currentBanner = _state.banners[0];
    }
  }
);
watch(
  [() => _state.reminders, () => _state.currentReminder],
  () => {
    if (!_state.currentReminder && _state.reminders.length > 0) {
      _state.currentReminder = _state.reminders[0];
    }
  }
);

export function usePopupManager() {
  return {
    state: _state,
    /** 是否存在待展示浮层（可驱动页面渲染浮层容器） */
    hasAnyVisible: computed(
      () =>
        !!_state.topBar ||
        !!_state.modalAnnouncement ||
        !!_state.currentBanner ||
        !!_state.currentReminder
    ),
    enqueueAnnouncement,
    dismissAnnouncement,
    enqueueBanner,
    dismissBanner,
    enqueueReminder,
    dismissReminder,
    /** 重置（登出、切换用户时使用） */
    reset() {
      _state.announcements = [];
      _state.banners = [];
      _state.reminders = [];
      _state.topBar = null;
      _state.modalAnnouncement = null;
      _state.currentBanner = null;
      _state.currentReminder = null;
    },
    /** 批量注入（来自后端公告 API） */
    applyFromBackend(payload: {
      announcements?: AnnouncementItem[];
      banners?: SiteBannerItem[];
      reminders?: ContentReminderItem[];
    }) {
      payload.announcements?.forEach(enqueueAnnouncement);
      payload.banners?.forEach(enqueueBanner);
      payload.reminders?.forEach(enqueueReminder);
    },
  };
}
