/**
 * SSR-safe Lucide-style icon components (inline native SVG).
 *
 * RATIONALE:
 *   On this project's Windows + Nuxt 4.5 SSR environment, the official
 *   `@lucide/vue` package consistently renders as an empty HTML Comment
 *   node (`<!---->`) on the server side, while the client renders a real
 *   <svg>.  This first-child type mismatch causes Vue to mark "Hydration
 *   completed but contains mismatches", tear down the SSR tree and rebuild
 *   it client-side, which in turn triggers "Cannot read properties of null
 *   (reading 'refs' / 'ref')" cascade errors during the de-hydrate phase.
 *
 * SOLUTION:
 *   Every icon below is a plain Vue 3 defineComponent() that directly
 *   returns h('svg', …) with the same viewBox / stroke props as Lucide,
 *   so server & client produce byte-identical first child nodes.
 *   Path data comes verbatim from lucide.dev icon sources (MIT).
 *
 * USAGE:
 *   import { FolderOpen, CalendarDays } from '~/lib/lucide-svg-icons'
 *   — drop-in replacement, same class / aria-hidden / size semantics.
 *   — use `class="size-4"` / `:style="{ strokeWidth: 2.25 }"` just like lucide-vue.
 */
import { defineComponent, h } from 'vue'

type IconChild = ReturnType<typeof h>
const attrs = {
  'xmlns': 'http://www.w3.org/2000/svg',
  'viewBox': '0 0 24 24',
  'fill': 'none' as const,
  'stroke-linecap': 'round' as const,
  'stroke-linejoin': 'round' as const,
  'stroke-width': 2,
  'stroke': 'currentColor',
  'aria-hidden': 'true'
}

const S = (sizeClass: string | undefined, ...children: IconChild[]) =>
  defineComponent({
    inheritAttrs: true,
    props: { class: { type: String, default: sizeClass ?? 'size-4' } },
    setup(_, { attrs: a }) {
      return () =>
        h(
          'svg',
          {
            ...attrs,
            class: a.class ?? sizeClass ?? 'size-4',
            style: a.style
          },
          children
        )
    }
  })

/* ------------------------------------------------------------------ */
/*  1. PostCard icons                                                  */
/* ------------------------------------------------------------------ */

// FolderOpen
export const FolderOpen = S(undefined,
  h('path', { d: 'm6 14 1.45-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.55 6a2 2 0 0 1-1.94 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.93a2 2 0 0 1 1.66.9l.82 1.2a2 2 0 0 0 1.66.9H18a2 2 0 0 1 2 2v2' })
)

// CalendarDays
export const CalendarDays = S(undefined,
  h('rect', { width: '18', height: '18', x: '3', y: '4', rx: '2', ry: '2' }),
  h('path', { d: 'M16 2v4' }),
  h('path', { d: 'M3 10h18' }),
  h('path', { d: 'M8 2v4' }),
  h('path', { d: 'M8 14h.01' }),
  h('path', { d: 'M12 14h.01' }),
  h('path', { d: 'M16 14h.01' }),
  h('path', { d: 'M8 18h.01' }),
  h('path', { d: 'M12 18h.01' }),
  h('path', { d: 'M16 18h.01' })
)

// Eye
export const Eye = S(undefined,
  h('path', { d: 'M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z' }),
  h('circle', { cx: '12', cy: '12', r: '3' })
)

// MessageSquare
export const MessageSquare = S(undefined,
  h('path', { d: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z' })
)

/* ------------------------------------------------------------------ */
/*  2. TagBadge icon                                                   */
/* ------------------------------------------------------------------ */

// Tag
export const Tag = S(undefined,
  h('path', { d: 'M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z' }),
  h('circle', { cx: '7.5', cy: '7.5', r: '.5', fill: 'currentColor' })
)

/* ------------------------------------------------------------------ */
/*  3. ThemeToggle                                                     */
/* ------------------------------------------------------------------ */

// Sun
export const Sun = S(undefined,
  h('circle', { cx: '12', cy: '12', r: '4' }),
  h('path', { d: 'M12 2v2' }),
  h('path', { d: 'M12 20v2' }),
  h('path', { d: 'm4.93 4.93 1.41 1.41' }),
  h('path', { d: 'm17.66 17.66 1.41 1.41' }),
  h('path', { d: 'M2 12h2' }),
  h('path', { d: 'M20 12h2' }),
  h('path', { d: 'm6.34 17.66-1.41 1.41' }),
  h('path', { d: 'm19.07 4.93-1.41 1.41' })
)

// Moon
export const Moon = S(undefined,
  h('path', { d: 'M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z' })
)

/* ------------------------------------------------------------------ */
/*  4. LocaleSwitcher                                                  */
/* ------------------------------------------------------------------ */

// Globe
export const Globe = S(undefined,
  h('circle', { cx: '12', cy: '12', r: '10' }),
  h('path', { d: 'M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20' }),
  h('path', { d: 'M2 12h20' })
)

// Check
export const Check = S(undefined,
  h('path', { d: 'M20 6 9 17l-5-5' })
)

/* ------------------------------------------------------------------ */
/*  5. shadcn/ui Chevron/Breadcrumb/Accordion                          */
/* ------------------------------------------------------------------ */

// ChevronDown
export const ChevronDown = S(undefined,
  h('path', { d: 'm6 9 6 6 6-6' })
)

// ChevronRight
export const ChevronRight = S(undefined,
  h('path', { d: 'm9 18 6-6-6-6' })
)

// ChevronLeft
export const ChevronLeft = S(undefined,
  h('path', { d: 'm15 18-6-6 6-6' })
)

// MoreHorizontal
export const MoreHorizontal = S(undefined,
  h('circle', { cx: '12', cy: '12', r: '1' }),
  h('circle', { cx: '19', cy: '12', r: '1' }),
  h('circle', { cx: '5', cy: '12', r: '1' })
)

/* ------------------------------------------------------------------ */
/*  6. CommentItem                                                     */
/* ------------------------------------------------------------------ */

// ArrowLeft
export const ArrowLeft = S(undefined,
  h('path', { d: 'm12 19-7-7 7-7' }),
  h('path', { d: 'M19 12H5' })
)

// ArrowRight
export const ArrowRight = S(undefined,
  h('path', { d: 'M5 12h14' }),
  h('path', { d: 'm12 5 7 7-7 7' })
)

/* ------------------------------------------------------------------ */
/*  7. AppHeader Menu/Search/LogOut/User                               */
/* ------------------------------------------------------------------ */

// Menu
export const Menu = S(undefined,
  h('line', { x1: '4', x2: '20', y1: '12', y2: '12' }),
  h('line', { x1: '4', x2: '20', y1: '6', y2: '6' }),
  h('line', { x1: '4', x2: '20', y1: '18', y2: '18' })
)

// Search
export const Search = S(undefined,
  h('circle', { cx: '11', cy: '11', r: '8' }),
  h('path', { d: 'm21 21-4.3-4.3' })
)

// LogOut
export const LogOut = S(undefined,
  h('path', { d: 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4' }),
  h('polyline', { points: '16 17 21 12 16 7' }),
  h('line', { x1: '21', x2: '9', y1: '12', y2: '12' })
)

// User
export const User = S(undefined,
  h('path', { d: 'M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2' }),
  h('circle', { cx: '12', cy: '7', r: '4' })
)

// Bell
export const Bell = S(undefined,
  h('path', { d: 'M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9' }),
  h('path', { d: 'M10.3 21a1.94 1.94 0 0 0 3.4 0' })
)

// ExternalLink
export const ExternalLink = S(undefined,
  h('path', { d: 'M15 3h6v6' }),
  h('path', { d: 'M10 14 21 3' }),
  h('path', { d: 'M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6' })
)

/* ------------------------------------------------------------------ */
/*  8. AdminSidebar / others used from client-only (but include)       */
/* ------------------------------------------------------------------ */

// Puzzle
export const Puzzle = S(undefined,
  h('path', { d: 'M15.39 14.57a1 1 0 0 0 .77-1.17l-.39-1.8a1 1 0 0 1 .57-1.23l1.46-.59a1 1 0 0 0 .57-1.3l-.99-2.46a1 1 0 0 0-.57-.57l-2.46-.99a1 1 0 0 0-1.3.57l-.59 1.46a1 1 0 0 1-1.23.57l-1.8-.39a1 1 0 0 0-1.17.77L7.53 9.38a1 1 0 0 1-1.23.57L4.84 8.36a1 1 0 0 0-1.3.57l-.99 2.46a1 1 0 0 0 .57 1.3l1.46.59a1 1 0 0 1 .57 1.23l-.39 1.8a1 1 0 0 0 .77 1.17l2.46.99a1 1 0 0 0 1.3-.57l.59-1.46a1 1 0 0 1 1.23-.57l1.8.39a1 1 0 0 0 1.17-.77l.99-2.46a1 1 0 0 1 .57-1.3l-1.46-.59a1 1 0 0 1-.57-1.23l.39-1.8a1 1 0 0 1 .62-.53' }),
  h('path', { d: 'M19.439 7.85c-.049.322.059.648.289.878l1.568 1.568c.47.47.706 1.087.706 1.704s-.235 1.233-.706 1.704l-1.611 1.611a.98.98 0 0 1-.837.276c-.47-.07-.802-.48-.968-.925a2.501 2.501 0 1 0-3.214 3.214c.446.166.855.497.925.968a.979.979 0 0 1-.276.837l-1.61 1.61a2.404 2.404 0 0 1-1.705.707 2.402 2.402 0 0 1-1.704-.706l-1.568-1.568a1.026 1.026 0 0 0-.877-.29c-.493.074-.84.504-1.02.968a2.5 2.5 0 1 1-3.237-3.237c.464-.18.894-.527.967-1.02a1.026 1.026 0 0 0-.289-.877l-1.568-1.568A2.402 2.402 0 0 1 1.998 12c0-.617.236-1.234.706-1.704L4.23 8.77c.24-.24.557-.35.866-.3.438.07.755.47.937.925a2.5 2.5 0 1 0 3.259-3.259c-.455-.182-.855-.5-.925-.937a.96.96 0 0 1 .299-.866L10.86 1.9a2.402 2.402 0 0 1 1.705-.706c.617 0 1.234.236 1.704.706l1.568 1.568c.231.231.557.339.877.29.493-.074.84-.504 1.02-.968a2.5 2.5 0 1 1 3.237 3.237c-.464.18-.894.527-.967 1.02Z' })
)

// Languages / for potential use
export const Languages = S(undefined,
  h('path', { d: 'm5 8 6 6' }),
  h('path', { d: 'm4 14 6-6 2-3' }),
  h('path', { d: 'M2 5h12' }),
  h('path', { d: 'M7 2h1' }),
  h('path', { d: 'm22 22-5-10-5 10' }),
  h('path', { d: 'M14 18h6' })
)

// Loader2
export const Loader2 = S(undefined,
  h('path', { d: 'M21 12a9 9 0 1 1-6.219-8.56' })
)

// Calendar (for admin filter bars, client-only)
export const Calendar = S(undefined,
  h('rect', { width: '18', height: '18', x: '3', y: '4', rx: '2', ry: '2' }),
  h('path', { d: 'M16 2v4' }),
  h('path', { d: 'M3 10h18' }),
  h('path', { d: 'M8 2v4' })
)

// X (close/cancel)
export const X = S(undefined,
  h('path', { d: 'M18 6 6 18' }),
  h('path', { d: 'm6 6 12 12' })
)

// RotateCcw
export const RotateCcw = S(undefined,
  h('path', { d: 'M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8' }),
  h('path', { d: 'M3 3v5h5' })
)

// RotateCw
export const RotateCw = S(undefined,
  h('path', { d: 'M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8' }),
  h('path', { d: 'M21 3v5h-5' })
)

// Upload
export const Upload = S(undefined,
  h('path', { d: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4' }),
  h('polyline', { points: '17 8 12 3 7 8' }),
  h('line', { x1: '12', x2: '12', y1: '3', y2: '15' })
)

// Image (alias)
export const ImageIcon = S(undefined,
  h('rect', { width: '18', height: '18', x: '3', y: '3', rx: '2', ry: '2' }),
  h('circle', { cx: '9', cy: '9', r: '2' }),
  h('path', { d: 'm21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21' })
)

// AlertTriangle
export const AlertTriangle = S(undefined,
  h('path', { d: 'm21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z' }),
  h('path', { d: 'M12 9v4' }),
  h('path', { d: 'M12 17h.01' })
)

// Inbox
export const Inbox = S(undefined,
  h('polyline', { points: '22 12 16 12 14 15 10 15 8 12 2 12' }),
  h('path', { d: 'M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z' })
)

// LayoutGrid
export const LayoutGrid = S(undefined,
  h('rect', { width: '7', height: '7', x: '3', y: '3', rx: '1' }),
  h('rect', { width: '7', height: '7', x: '14', y: '3', rx: '1' }),
  h('rect', { width: '7', height: '7', x: '14', y: '14', rx: '1' }),
  h('rect', { width: '7', height: '7', x: '3', y: '14', rx: '1' })
)

// Archive
export const Archive = S(undefined,
  h('rect', { width: '20', height: '5', x: '2', y: '3', rx: '1' }),
  h('path', { d: 'M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8' }),
  h('path', { d: 'M10 12h4' })
)

// Tags
export const Tags = S(undefined,
  h('path', { d: 'M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z' }),
  h('path', { d: 'M7 7h.01' }),
  h('path', { d: 'M22 13.5V22a2 2 0 0 1-2 2h-8.5A8.5 8.5 0 0 1 3 13.5v-.84A2 2 0 0 1 3.56 11l3.1-1.08' })
)

// MessageSquareText
export const MessageSquareText = S(undefined,
  h('path', { d: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z' }),
  h('path', { d: 'M13 8H7' }),
  h('path', { d: 'M17 12H7' })
)

/* ------------------------------------------------------------------ */
/*  9. Post detail / list page icons                                   */
/* ------------------------------------------------------------------ */

// Filter
export const Filter = S(undefined,
  h('polygon', { points: '6 3 20 3 14 12.46 14 19 10 21 10 12.46 6 3' })
)

// Clock3
export const Clock3 = S(undefined,
  h('circle', { cx: '12', cy: '12', r: '10' }),
  h('polyline', { points: '12 6 12 12 16.5 12' })
)

// ShieldCheck
export const ShieldCheck = S(undefined,
  h('path', { d: 'M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z' }),
  h('path', { d: 'm9 12 2 2 4-4' })
)

// Send
export const Send = S(undefined,
  h('path', { d: 'M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z' }),
  h('path', { d: 'm21.854 2.147-10.94 10.939' })
)

// Globe2
export const Globe2 = S(undefined,
  h('path', { d: 'M21.54 15H17a2 2 0 0 0-2 2v4.54' }),
  h('path', { d: 'M7 3.34V5a3 3 0 0 1-3 3a2 2 0 0 0 0 4c1.1 0 2 .9 2 2a2 2 0 0 1-2 2H2.46' }),
  h('path', { d: 'M3.6 7.9a10 10 0 1 0 8.5-5.9' }),
  h('path', { d: 'm11 18.45-2-2' })
)

// FileText
export const FileText = S(undefined,
  h('path', { d: 'M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z' }),
  h('path', { d: 'M14 2v4a2 2 0 0 0 2 2h4' }),
  h('path', { d: 'M10 9H8' }),
  h('path', { d: 'M16 13H8' }),
  h('path', { d: 'M16 17H8' })
)

// Hash
export const Hash = S(undefined,
  h('line', { x1: '4', x2: '20', y1: '9', y2: '9' }),
  h('line', { x1: '4', x2: '20', y1: '15', y2: '15' }),
  h('line', { x1: '10', x2: '8', y1: '3', y2: '21' }),
  h('line', { x1: '16', x2: '14', y1: '3', y2: '21' })
)

// RefreshCw
export const RefreshCw = S(undefined,
  h('polyline', { points: '21 2 21 8 15 8' }),
  h('polyline', { points: '3 22 3 16 9 16' }),
  h('path', { d: 'M3.51 9a9 9 0 0 1 14.85-3.36L21 8' }),
  h('path', { d: 'M20.49 15a9 9 0 0 1-14.85 3.36L3 16' })
)

// List
export const List = S(undefined,
  h('path', { d: 'M8 6h13' }),
  h('path', { d: 'M8 12h13' }),
  h('path', { d: 'M8 18h13' }),
  h('path', { d: 'M3 6h.01' }),
  h('path', { d: 'M3 12h.01' }),
  h('path', { d: 'M3 18h.01' })
)

// Sparkles
export const Sparkles = S(undefined,
  h('path', { d: 'M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z' }),
  h('path', { d: 'M20 3v4' }),
  h('path', { d: 'M22 5h-4' }),
  h('path', { d: 'M4 17v2' }),
  h('path', { d: 'M5 18H3' })
)

// ThumbsUp
export const ThumbsUp = S(undefined,
  h('path', { d: 'M7 10v12' }),
  h('path', { d: 'M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z' })
)

/* ------------------------------------------------------------------ */
/*  10. Remaining public-page icons                                   */
/* ------------------------------------------------------------------ */

// Link2
export const Link2 = S(undefined,
  h('path', { d: 'M9 17H7A5 5 0 0 1 7 7h2' }),
  h('path', { d: 'M15 7h2a5 5 0 0 1 0 10h-2' }),
  h('line', { x1: '8', x2: '16', y1: '12', y2: '12' })
)

// User2
export const User2 = S(undefined,
  h('circle', { cx: '12', cy: '8', r: '5' }),
  h('path', { d: 'M20 21a8 8 0 0 0-16 0' })
)

// UserCircle2
export const UserCircle2 = S(undefined,
  h('circle', { cx: '12', cy: '12', r: '10' }),
  h('circle', { cx: '12', cy: '10', r: '3' }),
  h('path', { d: 'M7 20.662V19a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v1.662' })
)

// Wrench
export const Wrench = S(undefined,
  h('path', { d: 'M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z' })
)

// Mail
export const Mail = S(undefined,
  h('rect', { width: '20', height: '16', x: '2', y: '4', rx: '2' }),
  h('path', { d: 'm22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7' })
)

// Quote
export const Quote = S(undefined,
  h('path', { d: 'M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z' }),
  h('path', { d: 'M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2h.75c0 2.25.25 4-2.75 4v3c0 1 0 1 1 1z' })
)

// Layers
export const Layers = S(undefined,
  h('path', { d: 'm12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z' }),
  h('path', { d: 'm22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65' }),
  h('path', { d: 'm22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65' })
)

// Coffee
export const Coffee = S(undefined,
  h('path', { d: 'M10 2v2' }),
  h('path', { d: 'M14 2v2' }),
  h('path', { d: 'M16 8a1 1 0 0 1 1 1v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1h14a4 4 0 1 1 0 8h-1' }),
  h('path', { d: 'M6 2v2' })
)

// Rss
export const Rss = S(undefined,
  h('path', { d: 'M4 11a9 9 0 0 1 9 9' }),
  h('path', { d: 'M4 4a16 16 0 0 1 16 16' }),
  h('circle', { cx: '5', cy: '19', r: '1' })
)

// Map
export const Map = S(undefined,
  h('path', { d: 'M14.106 5.553a2 2 0 0 0 1.788 0l3.659-1.83A1 1 0 0 1 21 4.619v12.764a1 1 0 0 1-.553.894l-4.553 2.277a2 2 0 0 1-1.788 0l-4.212-2.106a2 2 0 0 0-1.788 0l-3.659 1.83A1 1 0 0 1 3 19.381V6.618a1 1 0 0 1 .553-.894l4.553-2.277a2 2 0 0 1 1.788 0z' }),
  h('path', { d: 'M15 5.764v15' }),
  h('path', { d: 'M9 3.236v15' })
)

// PenLine
export const PenLine = S(undefined,
  h('path', { d: 'M12 20h9' }),
  h('path', { d: 'M16.376 3.622a1 1 0 0 1 3.002 3.002L7.368 18.635a2 2 0 0 1-.855.506l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.854z' })
)

// Heart
export const Heart = S(undefined,
  h('path', { d: 'M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z' })
)

// Images (stacked photos)
export const Images = S(undefined,
  h('path', { d: 'M3 16V5a2 2 0 0 1 2-2h11' }),
  h('rect', { width: '14', height: '14', x: '7', y: '7', rx: '2' }),
  h('path', { d: 'm10 13 2.5-2.5 2.5 2.5 2.5-2.5' }),
  h('circle', { cx: '10.5', cy: '10', r: '1' })
)

// Flame
export const Flame = S(undefined,
  h('path', { d: 'M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z' })
)

// TrendingUp
export const TrendingUp = S(undefined,
  h('polyline', { points: '22 7 13.5 15.5 8.5 10.5 2 17' }),
  h('polyline', { points: '16 7 22 7 22 13' })
)

// AlertCircle
export const AlertCircle = S(undefined,
  h('circle', { cx: '12', cy: '12', r: '10' }),
  h('line', { x1: '12', x2: '12', y1: '8', y2: '12' }),
  h('line', { x1: '12', x2: '12.01', y1: '16', y2: '16' })
)

// ArrowUpRight
export const ArrowUpRight = S(undefined,
  h('path', { d: 'M7 7h10v10' }),
  h('path', { d: 'M7 17 17 7' })
)

// ListOrdered
export const ListOrdered = S(undefined,
  h('line', { x1: '10', x2: '21', y1: '6', y2: '6' }),
  h('line', { x1: '10', x2: '21', y1: '12', y2: '12' }),
  h('line', { x1: '10', x2: '21', y1: '18', y2: '18' }),
  h('path', { d: 'M4 6h1v4' }),
  h('path', { d: 'M4 10h2' }),
  h('path', { d: 'M6 18H4c0-1 2-2 2-3s-1-1.5-2-1' })
)

// BookOpen
export const BookOpen = S(undefined,
  h('path', { d: 'M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z' }),
  h('path', { d: 'M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z' })
)

// SearchX
export const SearchX = S(undefined,
  h('path', { d: 'M13.5 8.5 17 12' }),
  h('path', { d: 'm17 8-3.5 3.5' }),
  h('circle', { cx: '11', cy: '11', r: '8' }),
  h('path', { d: 'm21 21-4.3-4.3' })
)

// ZoomIn
export const ZoomIn = S(undefined,
  h('circle', { cx: '11', cy: '11', r: '8' }),
  h('path', { d: 'm21 21-4.3-4.3' }),
  h('line', { x1: '11', x2: '11', y1: '8', y2: '14' }),
  h('line', { x1: '8', x2: '14', y1: '11', y2: '11' })
)

// ChevronUp
export const ChevronUp = S(undefined,
  h('path', { d: 'm18 15-6-6-6 6' })
)

// Circle
export const Circle = S(undefined,
  h('circle', { cx: '12', cy: '12', r: '10' })
)

// PanelLeft
export const PanelLeft = S(undefined,
  h('rect', { width: '18', height: '18', x: '3', y: '3', rx: '2' }),
  h('path', { d: 'M9 3v18' })
)

// Image (default export alias Image for ImageIcon)
export { ImageIcon as Image }

// Alias TagIcon
export { Tag as TagIcon }
