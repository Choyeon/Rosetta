/**
 * SSR-safe Lucide-style icon components (inline native SVG).
 *
 * RATIONALE:
 *   On this project's Windows + Nuxt 4.5 SSR environment, the official
 *   `@lucide/vue` package consistently rendered as an empty HTML Comment
 *   node (`<!---->`) on the server side at the time this file was written,
 *   while the client rendered a real
 *   <svg>.  This first-child type mismatch causes Vue to mark "Hydration
 *   completed but contains mismatches", tear down the SSR tree and rebuild
 *   it client-side, which in turn triggers "Cannot read properties of null
 *   (reading 'refs' / 'ref')" cascade errors during the de-hydrate phase.
 *   (Batch #142 later measured the package emitting real `<svg>` in SSR on
 *   the current version, so the premise no longer holds — but retiring this
 *   file is a separate, much larger change; this file is still the single
 *   source for the surfaces that use it.)
 *
 * SOLUTION:
 *   Every icon below is a plain Vue 3 defineComponent() that directly
 *   returns h('svg', …) with the same viewBox / stroke props as Lucide,
 *   so server & client produce byte-identical first child nodes.
 *   Path data is copied from the **installed** `@lucide/vue` package, not
 *   from a remembered version — tests/unit/lucideIconPathsMatchPackage.spec.ts
 *   compares every icon here against the package's own icon nodes (resolved
 *   through the package barrel, so lucide 1.x renames like bar-chart-3 →
 *   chart-column don't break the mapping).  Bumping the package without
 *   re-syncing this file turns that spec red; the symptom of not doing so is
 *   two different glyphs for one icon (batch #144: the sidebar heart came
 *   from here while the post card's came from the component).
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
    // Vue 把 class 声明为 prop 后不会再落到 attrs —— 必须从 props.class 读取，
    // 否则调用方传入的定位/尺寸类（absolute、mr-2 等）会被静默丢弃。
    props: { class: { type: String, default: undefined as string | undefined } },
    setup(props, { attrs: a }) {
      return () =>
        h(
          'svg',
          {
            ...attrs,
            class: props.class || sizeClass || 'size-4',
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
  h('path', { d: 'm6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2' })
)

// CalendarDays
export const CalendarDays = S(undefined,
  h('path', { d: 'M8 2v3' }),
  h('path', { d: 'M16 2v3' }),
  h('rect', { x: '3', y: '3', width: '18', height: '18', rx: '2' }),
  h('path', { d: 'M3 9h18' }),
  h('path', { d: 'M8 13h.01' }),
  h('path', { d: 'M12 13h.01' }),
  h('path', { d: 'M16 13h.01' }),
  h('path', { d: 'M8 17h.01' }),
  h('path', { d: 'M12 17h.01' }),
  h('path', { d: 'M16 17h.01' })
)

// Eye
export const Eye = S(undefined,
  h('path', { d: 'M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0' }),
  h('circle', { cx: '12', cy: '12', r: '3' })
)

// MessageSquare
export const MessageSquare = S(undefined,
  h('path', { d: 'M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z' })
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
  h('path', { d: 'M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401' })
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

// Lock
export const Lock = S(undefined,
  h('rect', { width: '18', height: '11', x: '3', y: '11', rx: '2', ry: '2' }),
  h('path', { d: 'M7 11V7a5 5 0 0 1 10 0v4' })
)

// BarChart3
export const BarChart3 = S(undefined,
  h('path', { d: 'M3 3v16a2 2 0 0 0 2 2h16' }),
  h('path', { d: 'M18 17V9' }),
  h('path', { d: 'M13 17V5' }),
  h('path', { d: 'M8 17v-3' })
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
  h('path', { d: 'M4 5h16' }),
  h('path', { d: 'M4 12h16' }),
  h('path', { d: 'M4 19h16' })
)

// Search
export const Search = S(undefined,
  h('path', { d: 'm21 21-4.34-4.34' }),
  h('circle', { cx: '11', cy: '11', r: '8' })
)

// LogOut
export const LogOut = S(undefined,
  h('path', { d: 'm16 17 5-5-5-5' }),
  h('path', { d: 'M21 12H9' }),
  h('path', { d: 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4' })
)

// User
export const User = S(undefined,
  h('path', { d: 'M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2' }),
  h('circle', { cx: '12', cy: '7', r: '4' })
)

// Settings（lucide v1.x 齿轮）
export const Settings = S(undefined,
  h('path', { d: 'M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915' }),
  h('circle', { cx: '12', cy: '12', r: '3' })
)

// Bell
export const Bell = S(undefined,
  h('path', { d: 'M10.268 21a2 2 0 0 0 3.464 0' }),
  h('path', { d: 'M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326' })
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
  h('path', { d: 'M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z' })
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
  h('path', { d: 'M8 2v3' }),
  h('path', { d: 'M16 2v3' }),
  h('rect', { x: '3', y: '3', width: '18', height: '18', rx: '2' }),
  h('path', { d: 'M3 9h18' })
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
  h('path', { d: 'M12 3v12' }),
  h('path', { d: 'm17 8-5-5-5 5' }),
  h('path', { d: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4' })
)

// Image (alias)
export const ImageIcon = S(undefined,
  h('rect', { width: '18', height: '18', x: '3', y: '3', rx: '2', ry: '2' }),
  h('circle', { cx: '9', cy: '9', r: '2' }),
  h('path', { d: 'm21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21' })
)

// AlertTriangle
export const AlertTriangle = S(undefined,
  h('path', { d: 'm21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3' }),
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
  h('path', { d: 'M13.172 2a2 2 0 0 1 1.414.586l6.71 6.71a2.4 2.4 0 0 1 0 3.408l-4.592 4.592a2.4 2.4 0 0 1-3.408 0l-6.71-6.71A2 2 0 0 1 6 9.172V3a1 1 0 0 1 1-1z' }),
  h('path', { d: 'M2 7v6.172a2 2 0 0 0 .586 1.414l6.71 6.71a2.4 2.4 0 0 0 3.191.193' }),
  h('circle', { cx: '10.5', cy: '6.5', r: '.5', fill: 'currentColor' })
)

// MessageSquareText
export const MessageSquareText = S(undefined,
  h('path', { d: 'M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z' }),
  h('path', { d: 'M7 11h10' }),
  h('path', { d: 'M7 15h6' }),
  h('path', { d: 'M7 7h8' })
)

/* ------------------------------------------------------------------ */
/*  9. Post detail / list page icons                                   */
/* ------------------------------------------------------------------ */

// Filter
export const Filter = S(undefined,
  h('path', { d: 'M10 20a1 1 0 0 0 .553.895l2 1A1 1 0 0 0 14 21v-7a2 2 0 0 1 .517-1.341L21.74 4.67A1 1 0 0 0 21 3H3a1 1 0 0 0-.742 1.67l7.225 7.989A2 2 0 0 1 10 14z' })
)

// Clock3
export const Clock3 = S(undefined,
  h('circle', { cx: '12', cy: '12', r: '10' }),
  h('path', { d: 'M12 6v6h4' })
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
  h('path', { d: 'M7 3.34V5a3 3 0 0 0 3 3a2 2 0 0 1 2 2c0 1.1.9 2 2 2a2 2 0 0 0 2-2c0-1.1.9-2 2-2h3.17' }),
  h('path', { d: 'M11 21.95V18a2 2 0 0 0-2-2a2 2 0 0 1-2-2v-1a2 2 0 0 0-2-2H2.05' }),
  h('circle', { cx: '12', cy: '12', r: '10' })
)

// FileText
export const FileText = S(undefined,
  h('path', { d: 'M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z' }),
  h('path', { d: 'M14 2v5a1 1 0 0 0 1 1h5' }),
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
  h('path', { d: 'M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8' }),
  h('path', { d: 'M21 3v5h-5' }),
  h('path', { d: 'M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16' }),
  h('path', { d: 'M8 16H3v5' })
)

// List
export const List = S(undefined,
  h('path', { d: 'M3 5h.01' }),
  h('path', { d: 'M3 12h.01' }),
  h('path', { d: 'M3 19h.01' }),
  h('path', { d: 'M8 5h13' }),
  h('path', { d: 'M8 12h13' }),
  h('path', { d: 'M8 19h13' })
)

// Sparkles
export const Sparkles = S(undefined,
  h('path', { d: 'M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z' }),
  h('path', { d: 'M20 2v4' }),
  h('path', { d: 'M22 4h-4' }),
  h('circle', { cx: '4', cy: '20', r: '2' })
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
  h('path', { d: 'M15 7h2a5 5 0 1 1 0 10h-2' }),
  h('line', { x1: '8', x2: '16', y1: '12', y2: '12' })
)

// Share2
export const Share2 = S(undefined,
  h('circle', { cx: '18', cy: '5', r: '3' }),
  h('circle', { cx: '6', cy: '12', r: '3' }),
  h('circle', { cx: '18', cy: '19', r: '3' }),
  h('line', { x1: '8.59', x2: '15.42', y1: '13.51', y2: '17.49' }),
  h('line', { x1: '15.41', x2: '8.59', y1: '6.51', y2: '10.49' })
)

// User2
export const User2 = S(undefined,
  h('circle', { cx: '12', cy: '8', r: '5' }),
  h('path', { d: 'M20 21a8 8 0 0 0-16 0' })
)

// UserCircle2
export const UserCircle2 = S(undefined,
  h('path', { d: 'M17.925 20.056a6 6 0 0 0-11.851.001' }),
  h('circle', { cx: '12', cy: '11', r: '4' }),
  h('circle', { cx: '12', cy: '12', r: '10' })
)

// Wrench
export const Wrench = S(undefined,
  h('path', { d: 'M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.106-3.105c.32-.322.863-.22.983.218a6 6 0 0 1-8.259 7.057l-7.91 7.91a1 1 0 0 1-2.999-3l7.91-7.91a6 6 0 0 1 7.057-8.259c.438.12.54.662.219.984z' })
)

// Mail
export const Mail = S(undefined,
  h('path', { d: 'm22 7-8.991 5.727a2 2 0 0 1-2.009 0L2 7' }),
  h('rect', { x: '2', y: '4', width: '20', height: '16', rx: '2' })
)

// Quote
export const Quote = S(undefined,
  h('path', { d: 'M16 3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2 1 1 0 0 1 1 1v1a2 2 0 0 1-2 2 1 1 0 0 0-1 1v2a1 1 0 0 0 1 1 6 6 0 0 0 6-6V5a2 2 0 0 0-2-2z' }),
  h('path', { d: 'M5 3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2 1 1 0 0 1 1 1v1a2 2 0 0 1-2 2 1 1 0 0 0-1 1v2a1 1 0 0 0 1 1 6 6 0 0 0 6-6V5a2 2 0 0 0-2-2z' })
)

// Layers
export const Layers = S(undefined,
  h('path', { d: 'M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z' }),
  h('path', { d: 'M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12' }),
  h('path', { d: 'M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17' })
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
  h('path', { d: 'M13 21h8' }),
  h('path', { d: 'M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z' })
)

// Heart
export const Heart = S(undefined,
  h('path', { d: 'M2 9.5a5.5 5.5 0 0 1 9.591-3.676.56.56 0 0 0 .818 0A5.49 5.49 0 0 1 22 9.5c0 2.29-1.5 4-3 5.5l-5.492 5.313a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5' })
)

// Bookmark
export const Bookmark = S(undefined,
  h('path', { d: 'M17 3a2 2 0 0 1 2 2v15a1 1 0 0 1-1.496.868l-4.512-2.578a2 2 0 0 0-1.984 0l-4.512 2.578A1 1 0 0 1 5 20V5a2 2 0 0 1 2-2z' })
)

// Smile（评论表情反应入口）
export const Smile = S(undefined,
  h('path', { d: 'M15 10V9' }),
  h('path', { d: 'M16.472 15a6 6 0 01-8.943 0' }),
  h('path', { d: 'M9 10V9' }),
  h('circle', { cx: '12', cy: '12', r: '10' })
)

// Trash2（删除自己的评论）—— 节点与顺序逐条取自 @lucide/vue dist/esm/icons/trash-2.mjs
export const Trash2 = S(undefined,
  h('path', { d: 'M10 11v6' }),
  h('path', { d: 'M14 11v6' }),
  h('path', { d: 'M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6' }),
  h('path', { d: 'M3 6h18' }),
  h('path', { d: 'M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2' })
)

// Images (stacked photos)
export const Images = S(undefined,
  h('path', { d: 'm22 11-1.296-1.296a2.4 2.4 0 0 0-3.408 0L11 16' }),
  h('path', { d: 'M4 8a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2' }),
  h('circle', { cx: '13', cy: '7', r: '1', fill: 'currentColor' }),
  h('rect', { x: '8', y: '2', width: '14', height: '14', rx: '2' })
)

// Flame
export const Flame = S(undefined,
  h('path', { d: 'M12 3q1 4 4 6.5t3 5.5a1 1 0 0 1-14 0 5 5 0 0 1 1-3 1 1 0 0 0 5 0c0-2-1.5-3-1.5-5q0-2 2.5-4' })
)

// TrendingUp
export const TrendingUp = S(undefined,
  h('path', { d: 'M16 7h6v6' }),
  h('path', { d: 'm22 7-8.5 8.5-5-5L2 17' })
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
  h('path', { d: 'M11 5h10' }),
  h('path', { d: 'M11 12h10' }),
  h('path', { d: 'M11 19h10' }),
  h('path', { d: 'M4 4h1v5' }),
  h('path', { d: 'M4 9h2' }),
  h('path', { d: 'M6.5 20H3.4c0-1 2.6-1.925 2.6-3.5a1.5 1.5 0 0 0-2.6-1.02' })
)

// BookOpen
export const BookOpen = S(undefined,
  h('path', { d: 'M12 5v16' }),
  h('path', { d: 'M20.001 19A2 2 0 0022 17V5a2 2 0 00-1.999-2L16 3.002A5 5 0 0012 5a5 5 0 00-4-2H4a2 2 0 00-2 2v12a2 2 0 001.999 2H8a5 5 0 014 2 5 5 0 014-2z' })
)

// SearchX
export const SearchX = S(undefined,
  h('path', { d: 'm13.5 8.5-5 5' }),
  h('path', { d: 'm8.5 8.5 5 5' }),
  h('circle', { cx: '11', cy: '11', r: '8' }),
  h('path', { d: 'm21 21-4.3-4.3' })
)

// ZoomIn
export const ZoomIn = S(undefined,
  h('circle', { cx: '11', cy: '11', r: '8' }),
  h('line', { x1: '21', x2: '16.65', y1: '21', y2: '16.65' }),
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
