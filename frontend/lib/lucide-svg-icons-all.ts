/**
 * SSR-only shim that Vite resolver substitutes for `@lucide/vue` when
 * building/rendering on the server (see vite plugin in nuxt.config.ts).
 *
 * Goal: Guarantee that every lucide-vue icon import produces a real
 * `<svg>` first-child on the server, matching the client-side first-child.
 * This eliminates "Hydration completed but contains mismatches" caused by
 * the old @lucide/vue package (v1.37) rendering empty <!-- comment -->
 * nodes in this project's Windows SSR environment.
 *
 * Icons individually enumerated in ./lucide-svg-icons.ts render with the
 * correct Lucide paths.  Any other icon name not listed there falls back
 * to a generic <svg> stub (same dimensions / class semantics).  Because
 * the stub still has first-child type === "<svg>" (not a comment or a
 * different tag), Vue will only patch path-level differences after
 * hydration rather than tear down the whole sub-tree.  This prevents
 * the cascade "Cannot read properties of null (reading 'refs')" error.
 *
 * Client builds use the original npm: @lucide/vue package (paths correct).
 */
import { defineComponent, h } from 'vue'

// 1. Re-export the hand-authored SSR-safe icons with correct paths.
export * from './lucide-svg-icons'

// 2. Catch-all proxy: any icon name not explicitly exported above falls
//    back to a generic size-4 placeholder <svg> with matching shape.
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

const stubIcon = (name: string) =>
  defineComponent({
    name: `LucideSSRStub${name}`,
    inheritAttrs: true,
    props: { class: { type: String, default: 'size-4' } },
    setup(_, { attrs: a }) {
      return () =>
        h(
          'svg',
          {
            ...attrs,
            'class': a.class ?? 'size-4',
            'style': a.style,
            'data-lucide-ssr-stub': name
          },
          // One generic non-empty child so Vue never sees an SVG root
          // followed by zero children on one side and N paths on the
          // other; a single empty rect is cheap to diff/patch.
          [h('rect', { x: 3, y: 3, width: 18, height: 18, rx: 2, ry: 2, opacity: 0 })]
        )
    }
  })

const proxyHandler: ProxyHandler<Record<string, unknown>> = {
  get(target, prop, receiver) {
    if (typeof prop !== 'string') return Reflect.get(target, prop, receiver)
    if (prop in target) return Reflect.get(target, prop, receiver)
    // Symbols / default / __esModule / etc: passthrough
    if (prop === 'default') return Reflect.get(target, prop, receiver)
    // Treat any other string prop as a lucide icon name -> stub
    if (!prop.startsWith('__') && /^[A-Z][A-Za-z0-9]*$/.test(prop)) {
      const stub = stubIcon(prop)
      target[prop] = stub
      return stub
    }
    return Reflect.get(target, prop, receiver)
  },
  has(target, prop) {
    // Declare everything "in" the proxy so that destructuring:
    // `import { SomeRandomIcon } from '@lucide/vue'` doesn't crash SSR.
    if (typeof prop === 'string' && /^[A-Z][A-Za-z0-9]*$/.test(prop)) return true
    return Reflect.has(target, prop)
  },
  ownKeys(target) {
    // Hide enumerable injection: keep real ownKeys as-is from underlying
    return Reflect.ownKeys(target)
  },
  getOwnPropertyDescriptor(target, prop) {
    if (typeof prop === 'string' && /^[A-Z][A-Za-z0-9]*$/.test(prop) && !(prop in target)) {
      return { configurable: true, enumerable: true, writable: false }
    }
    return Reflect.getOwnPropertyDescriptor(target, prop)
  }
}

const base: Record<string, unknown> = {}
const withExports = new Proxy(base, proxyHandler)

// Expose Proxy as module namespace export * won't capture dynamic names
// but import { X } from will go through proxy getter on namespace object.
export default withExports
// Named export a namespace object (dynamic import support)
export const LucideSSR = withExports

// === Exhaustive named exports =====================================
//  Vite SSR validates named bindings at module boundary, so each
//  binding must exist as a real ESM export.
//
//  Icons with correct Lucide paths now live in ./lucide-svg-icons and
//  flow through `export *` above — including: Bell, ExternalLink,
//  ArrowRight, ArrowLeft, RefreshCw, PenLine, Send, Heart, Link2,
//  Images, ZoomIn, Image, Flame, TrendingUp, Hash, SearchX, BookOpen,
//  AlertCircle, ArrowUpRight, ListOrdered, ChevronUp, Circle,
//  PanelLeft, Filter, FolderOpen, CalendarDays, Eye, MessageSquare,
//  Tags, Sun, Moon, Globe, Check, all Chevrons, X, etc.
//
//  Only names that still have no hand-authored path get an explicit
//  placeholder stub here.  (The Proxy catch-all would handle these too,
//  but real ESM exports keep Vite's named-binding validation happy.)

// Alias names expected by shadcn pagination components
export { ChevronLeft as ChevronLeftIcon } from './lucide-svg-icons'
export { ChevronRight as ChevronRightIcon } from './lucide-svg-icons'
// gallery.vue imports `Images as ImageIcon`
export { Images as ImageIcon } from './lucide-svg-icons'

// Remaining icons without hand-authored paths → generic placeholder
export const Info = stubIcon('Info')
export const Plus = stubIcon('Plus')
export const Pencil = stubIcon('Pencil')
export const Trash2 = stubIcon('Trash2')
export const Pin = stubIcon('Pin')
export const Zap = stubIcon('Zap')
export const UploadCloud = stubIcon('UploadCloud')

export {
  Languages, Loader2, Upload, RotateCcw, RotateCw, AlertTriangle, Inbox,
  Puzzle as PuzzlePiece
} from './lucide-svg-icons'
// Realias Puzzle (admin pages — client-only — import plain Puzzle)
export { Puzzle } from './lucide-svg-icons'
