import { type Component, markRaw } from 'vue'
import * as HeroiconsOutline from '@heroicons/vue/24/outline'
import * as HeroiconsSolid from '@heroicons/vue/24/solid'
import * as Lucide from '@lucide/vue'

/**
 * Icon resolution for Rosetta.
 *
 * Heroicons are resolved **directly from the official `@heroicons/vue` package** —
 * there is deliberately NO name-translation table. `heroicons:code-bracket`
 * renders the genuine `CodeBracketIcon` component shipped by Heroicons v2,
 * not a look-alike from another icon set.
 *
 * Supported icon strings (values coming from the API / DB):
 *   `heroicons:code-bracket`   -> `@heroicons/vue/24/outline` `CodeBracketIcon`
 *   `heroicons-solid:star`     -> `@heroicons/vue/24/solid`   `StarIcon`
 *   `heroicons:HomeIcon`       -> the raw export name works too
 *   `cog-6-tooth`              -> bare name, outline set
 *   `material-symbols:home`    -> other icon sets: best-effort Lucide fallback
 *   `🎉`                       -> emoji (see `isEmojiIcon`)
 *
 * NOTE: never `import … from '@heroicons/vue'` (the bare package root) — it is a
 * Proxy that throws on purpose. Always go through a versioned subpath such as
 * `@heroicons/vue/24/outline`.
 */
export type HeroiconVariant = 'outline' | 'solid'

const HEROICON_SETS: Record<HeroiconVariant, Record<string, unknown>> = {
  outline: HeroiconsOutline as unknown as Record<string, unknown>,
  solid: HeroiconsSolid as unknown as Record<string, unknown>
}

/** Prefixes that explicitly request a Heroicons variant. */
const SOLID_PREFIXES = new Set([
  'heroicons-solid',
  'heroicons-24-solid',
  'heroicons-20-solid',
  'heroicons-16-solid'
])
const OUTLINE_PREFIXES = new Set([
  'heroicons',
  'heroicons-outline',
  'heroicons-24-outline'
])

const COMPONENT_CACHE = new Map<string, Component | null>()

/**
 * Both Heroicons and Lucide v1 export icons as **render functions**, i.e.
 * `typeof icon === 'function'`, not `'object'`. Checking only for `'object'`
 * silently rejects 100% of them and every icon degrades to raw text.
 */
function isRenderable(value: unknown): value is Component {
  return typeof value === 'function' || (typeof value === 'object' && value !== null)
}

/** kebab / snake / spaced name -> PascalCase (`cog-6-tooth` -> `Cog6Tooth`). */
function toPascalCase(input: string): string {
  return input
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join('')
}

/**
 * Squash a name for case/separator-insensitive matching.
 *
 * Heroicons export names mix digits and capitals in ways plain PascalCase
 * conversion cannot predict (`squares-2x2` -> `Squares2X2Icon`, `battery-100`
 * -> `Battery100Icon`), so we index every export by a normalised key instead of
 * trying to reconstruct the exact spelling.
 */
function squash(input: string): string {
  return input.replace(/[-_\s]/g, '').toLowerCase()
}

/** Split `heroicons-solid:star` into `{ name: 'star', variant: 'solid' }`. */
function parseIconString(iconStr: string): { name: string, variant: HeroiconVariant } {
  const idx = iconStr.indexOf(':')
  if (idx === -1) return { name: iconStr, variant: 'outline' }

  const prefix = iconStr.slice(0, idx).toLowerCase()
  const name = iconStr.slice(idx + 1)

  if (SOLID_PREFIXES.has(prefix)) return { name, variant: 'solid' }
  if (OUTLINE_PREFIXES.has(prefix)) return { name, variant: 'outline' }

  // Unknown prefix (`material-symbols:…`, `lucide:…`): still try the bare name
  // against Heroicons first so the whole site keeps one visual icon family.
  return { name, variant: 'outline' }
}

/**
 * Alternate spellings to try for a name.
 * Material Symbols style variant suffixes are dropped so that
 * `folder-open-rounded` can still find the Heroicons `FolderOpenIcon`.
 */
function nameCandidates(name: string): string[] {
  const base = name.trim()
  if (!base) return []

  const list = [base]
  const stripped = base.replace(/-(rounded|outlined|outline|sharp|filled|fill|round)$/i, '')
  if (stripped && stripped !== base) list.push(stripped)

  return list
}

const HEROICON_INDEX = new Map<HeroiconVariant, Map<string, Component>>()

/** `{ squashedExportName: component }` — e.g. `squares2x2icon` -> Squares2X2Icon. */
function heroiconIndex(variant: HeroiconVariant): Map<string, Component> {
  const cached = HEROICON_INDEX.get(variant)
  if (cached) return cached

  const index = new Map<string, Component>()
  for (const [exportName, value] of Object.entries(HEROICON_SETS[variant])) {
    if (!isRenderable(value)) continue
    const key = squash(exportName)
    if (!index.has(key)) index.set(key, markRaw(value))
  }

  HEROICON_INDEX.set(variant, index)
  return index
}

function lookupHeroicon(name: string, variant: HeroiconVariant): Component | null {
  if (!name) return null

  const cacheKey = `hero:${variant}:${name.toLowerCase()}`
  if (COMPONENT_CACHE.has(cacheKey)) return COMPONENT_CACHE.get(cacheKey) ?? null

  const index = heroiconIndex(variant)
  let found: Component | null = null

  for (const candidate of nameCandidates(name)) {
    const squashed = squash(candidate)
    const hit = index.get(`${squashed}icon`) ?? index.get(squashed)
    if (hit) {
      found = hit
      break
    }
  }

  COMPONENT_CACHE.set(cacheKey, found)
  return found
}

/**
 * Last-resort fallback for icon sets we do not ship (`material-symbols:*` in the
 * seeded navigation data, for instance). Lucide is already a project dependency,
 * so this costs nothing extra and keeps those icons from falling back to text.
 */
function lookupLucide(name: string): Component | null {
  if (!name) return null

  const cacheKey = `lucide:${name.toLowerCase()}`
  if (COMPONENT_CACHE.has(cacheKey)) return COMPONENT_CACHE.get(cacheKey) ?? null

  const bag = Lucide as unknown as Record<string, unknown>
  let found: Component | null = null

  for (const candidate of nameCandidates(name)) {
    const pascal = toPascalCase(candidate)
    for (const exportName of [pascal, `${pascal}Icon`]) {
      const raw = bag[exportName]
      if (isRenderable(raw)) {
        found = markRaw(raw)
        break
      }
    }
    if (found) break
  }

  COMPONENT_CACHE.set(cacheKey, found)
  return found
}

/**
 * Resolve an icon string to a renderable component.
 *
 * Returns `null` when nothing matches so callers can fall back to a glyph or
 * to the raw text.
 */
export function resolveIconComponent(iconStr: string): Component | null {
  const raw = (iconStr ?? '').trim()
  if (!raw) return null

  const { name, variant } = parseIconString(raw)
  if (!name.trim()) return null

  return (
    lookupHeroicon(name, variant)
    ?? lookupHeroicon(name, variant === 'solid' ? 'outline' : 'solid')
    ?? lookupLucide(name)
    ?? null
  )
}

/** Resolve a bare Heroicons name (`home`, `cog-6-tooth`) for a given variant. */
export function resolveHeroiconComponent(
  name: string,
  variant: HeroiconVariant = 'outline'
): Component | null {
  return lookupHeroicon(name ?? '', variant)
}

const NAME_CACHE = new Map<HeroiconVariant, string[]>()

/**
 * Every Heroicons name available to `resolveIconComponent`, in kebab-case.
 *
 * Derived from the package exports, so it can never drift out of sync and can
 * be used to build an icon picker without hard-coding a list.
 */
export function listHeroiconNames(variant: HeroiconVariant = 'outline'): string[] {
  const cached = NAME_CACHE.get(variant)
  if (cached) return cached

  const bag = HEROICON_SETS[variant]
  const names: string[] = []

  for (const exportName of Object.keys(bag)) {
    if (!exportName.endsWith('Icon')) continue
    const pascal = exportName.slice(0, -'Icon'.length)
    const kebab = pascal
      .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
      .replace(/([A-Z]+)([A-Z][a-z])/g, '$1-$2')
      .toLowerCase()

    if (!kebab) continue
    names.push(kebab)
  }

  names.sort()
  NAME_CACHE.set(variant, names)
  return names
}

export function isEmojiIcon(str: string): boolean {
  if (!str) return false
  const emojiRe = /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|[\u{1F000}-\u{1F02F}]|[\u{1F0A0}-\u{1F0FF}]|[\u{1F100}-\u{1F64F}]|[\u{1F680}-\u{1F6FF}]|[\u{1F900}-\u{1F9FF}]|[\u{1FA00}-\u{1FA6F}]|[\u{1FA70}-\u{1FAFF}]|[\u{2B50}]|[\u{2764}]/u
  return emojiRe.test(str) && str.trim().length <= 4
}
