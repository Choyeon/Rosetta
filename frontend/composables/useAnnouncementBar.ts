/**
 * 公告条状态逻辑（供 layouts/default.vue 使用；抽成独立模块的唯一原因就是可单测）。
 *
 * 硬契约：
 * · 后端 GET /announcements 返回 list[AnnouncementResponse]，title/content 恒为**明文字符串**
 *   （AnnouncementBase 是 str 字段，模型列也是 String/Text），不是 i18n dict；
 *   该端点也没有 link / url / target 列，任何"公告带链接"的分支都是死代码。
 * · is_active 与 start_time / end_time 窗口由服务端过滤，前端不得再判一次（口径会漂）。
 * · 来源有两个：公告表（多条）+ 设置页 notice 分组（全站置顶单条），在此合一。
 * · 关闭记录只写 sessionStorage，且必须等 onMounted 之后再读——setup 顶层读 window 违反 SSR 守则，
 *   在首帧读还会造成服务端/客户端渲染不一致。
 */
import { computed, onMounted, ref, type Ref } from 'vue'

/** 后端 AnnouncementResponse 里公告条真正会用到的字段。 */
export interface AnnouncementRow {
  id: number | string
  title?: string
  content?: string
  type?: string
  is_dismissible?: boolean
}

export const ANNOUNCEMENT_DISMISS_KEY = 'rosetta:dismissed-announcements'

/** is_dismissible 缺省按可关闭处理（服务端 default=True，只有显式 false 才锁死）。 */
export function canDismissAnnouncement(ann: AnnouncementRow): boolean {
  return ann.is_dismissible !== false
}

/**
 * 过滤掉本机已关闭的公告。
 * 不可关闭的公告无视存储记录——管理员把某条从「可关闭」改成「不可关闭」时，
 * 用户浏览器里的旧 id 不能继续把它藏起来。
 */
export function visibleAnnouncements(
  rows: AnnouncementRow[],
  dismissedIds: readonly (number | string)[]
): AnnouncementRow[] {
  const dismissed = new Set(dismissedIds.map(String))
  return rows
    .filter(ann => !canDismissAnnouncement(ann) || !dismissed.has(String(ann.id)))
    .map(ann => ({
      ...ann,
      title: stripInlineMarkdown(ann.title) || undefined,
      content: stripInlineMarkdown(ann.content) || undefined
    }))
    // 剥完标记可能什么都不剩（正文只有 `****`），此时不渲染只剩图标和关闭按钮的空条
    .filter(ann => Boolean(ann.title || ann.content))
}

/** 四种公告类型的底色方案；未知 type 落回 info，绝不因脏数据渲染出无色条。 */
export function announcementVariantClass(type?: string): string {
  switch (type) {
    case 'warning': return 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-b border-amber-500/20'
    case 'error': return 'bg-rose-500/10 text-rose-700 dark:text-rose-300 border-b border-rose-500/20'
    case 'success': return 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-b border-emerald-500/20'
    case 'info':
    default: return 'bg-sky-500/10 text-sky-700 dark:text-sky-300 border-b border-sky-500/20'
  }
}

/** 隐私模式 / 禁用存储时返回 null，调用侧退化为「只在内存里记住」。 */
function dismissStore(): Storage | null {
  if (!import.meta.client) return null
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}

/** 存储内容来自浏览器，解析失败必须兜空数组而不是冒泡打断渲染。 */
export function readDismissedIds(): string[] {
  const store = dismissStore()
  if (!store) return []
  try {
    const raw = JSON.parse(store.getItem(ANNOUNCEMENT_DISMISS_KEY) ?? '[]')
    return Array.isArray(raw) ? raw.map(String) : []
  } catch {
    return []
  }
}

/**
 * 把行内 Markdown 标记降级为纯文本。
 * 公告条是单行 truncate 的横条，不是正文渲染位：走 posts 那套 marked + DOMPurify
 * 会把 `<p>` / `<ul>` 塞进 flex 行内，还会引入公共页 v-html 面。因此管理员在两处
 * （设置页 notice.content_md / 公告管理 content）写的 Markdown 在这里按"保留文字、去掉标记"处理，
 * 链接取锚文本——至少访客不会看到字面量 `**提示**`。
 */
export function stripInlineMarkdown(text?: string | null): string {
  if (!text) return ''
  return String(text)
    .replace(/`{1,3}([^`]*)`{1,3}/g, '$1')
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/(\*\*|__)(.*?)\1/g, '$2')
    .replace(/(\*|_)(.*?)\1/g, '$2')
    .replace(/~~(.*?)~~/g, '$1')
    .replace(/^\s*#{1,6}\s*/gm, '')
    .replace(/\s+/g, ' ')
    .trim()
}

/** 设置页「站点公告」分组（SiteConfig KV `notice`）到公告条的一行；与公告表是同一根横幅的两个来源。 */
export interface SiteNoticeConfig {
  enable?: boolean
  type?: string
  title?: string
  content_md?: string
  dismissible?: boolean
  sticky?: boolean
}

/** notice 行没有自增 id，用固定 key 参与关闭记录（与数字 id 天然不冲突）。 */
export const SITE_NOTICE_ID = 'site-notice'

/** 未启用、或标题与正文都为空时不出条——避免空白横幅。 */
export function noticeToRow(notice?: SiteNoticeConfig | null): AnnouncementRow | null {
  if (!notice || notice.enable !== true) return null
  const title = stripInlineMarkdown(notice.title)
  const content = stripInlineMarkdown(notice.content_md)
  if (!title && !content) return null
  return {
    id: SITE_NOTICE_ID,
    title: title || undefined,
    content: content || undefined,
    type: notice.type,
    is_dismissible: notice.dismissible !== false
  }
}

/**
 * 两个来源合成一条列表。
 * sticky=true（默认）时设置公告排在表格公告之前——它的语义就是"全站置顶一条"。
 */
export function mergeAnnouncementRows(
  noticeRow: AnnouncementRow | null,
  rows: AnnouncementRow[],
  sticky = true
): AnnouncementRow[] {
  if (!noticeRow) return rows
  return sticky ? [noticeRow, ...rows] : [...rows, noticeRow]
}

export function useAnnouncementBar(rows: Ref<AnnouncementRow[]>) {
  const dismissed = ref<string[]>([])

  // 服务端与 Hydrate 首帧都按「未关闭」出图，挂载后再套用本机记录，因此不会有 hydration mismatch。
  onMounted(() => {
    dismissed.value = readDismissedIds()
  })

  const visible = computed(() => visibleAnnouncements(rows.value, dismissed.value))

  const dismiss = (id: number | string) => {
    const next = [...new Set([...dismissed.value, String(id)])]
    dismissed.value = next
    const store = dismissStore()
    if (!store) return
    try {
      store.setItem(ANNOUNCEMENT_DISMISS_KEY, JSON.stringify(next))
    } catch {
      // 写失败（配额 / 隐私模式）只意味着刷新后公告重新出现，本次关闭仍然生效。
    }
  }

  return { visible, dismiss }
}
