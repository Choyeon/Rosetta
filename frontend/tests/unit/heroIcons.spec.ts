import { describe, it, expect } from 'vitest'
import {
  resolveIconComponent,
  resolveHeroiconComponent,
  listHeroiconNames,
  isEmojiIcon
} from '~/composables/heroIcons'
import {
  AcademicCapIcon,
  Bars3Icon,
  Battery100Icon,
  BuildingOffice2Icon,
  CodeBracketIcon,
  Cog6ToothIcon,
  ComputerDesktopIcon,
  HomeIcon,
  LanguageIcon,
  PencilSquareIcon,
  ServerStackIcon,
  Squares2X2Icon,
  SwatchIcon,
  WrenchScrewdriverIcon
} from '@heroicons/vue/24/outline'
import { StarIcon as SolidStarIcon } from '@heroicons/vue/24/solid'

describe('heroIcons', () => {
  describe('resolveIconComponent', () => {
    // The whole point of the rewrite: `heroicons:<name>` must yield the REAL
    // Heroicons component from `@heroicons/vue`, not a translated look-alike.
    it('resolves heroicons names to the genuine @heroicons/vue components', () => {
      expect(resolveIconComponent('heroicons:home')).toBe(HomeIcon)
      expect(resolveIconComponent('heroicons:code-bracket')).toBe(CodeBracketIcon)
      expect(resolveIconComponent('heroicons:cog-6-tooth')).toBe(Cog6ToothIcon)
      expect(resolveIconComponent('heroicons:academic-cap')).toBe(AcademicCapIcon)
      expect(resolveIconComponent('heroicons:computer-desktop')).toBe(ComputerDesktopIcon)
      expect(resolveIconComponent('heroicons:server-stack')).toBe(ServerStackIcon)
      expect(resolveIconComponent('heroicons:swatch')).toBe(SwatchIcon)
      expect(resolveIconComponent('heroicons:pencil-square')).toBe(PencilSquareIcon)
      expect(resolveIconComponent('heroicons:wrench-screwdriver')).toBe(WrenchScrewdriverIcon)
      expect(resolveIconComponent('heroicons:language')).toBe(LanguageIcon)
      expect(resolveIconComponent('heroicons:squares-2x2')).toBe(Squares2X2Icon)
    })

    it('resolves bare heroicons names', () => {
      expect(resolveIconComponent('home')).toBe(HomeIcon)
      expect(resolveIconComponent('code-bracket')).toBe(CodeBracketIcon)
    })

    it('resolves the raw PascalCase export name', () => {
      expect(resolveIconComponent('heroicons:HomeIcon')).toBe(HomeIcon)
      expect(resolveIconComponent('Cog6ToothIcon')).toBe(Cog6ToothIcon)
    })

    it('resolves the solid variant via the heroicons-solid prefix', () => {
      expect(resolveIconComponent('heroicons-solid:star')).toBe(SolidStarIcon)
      expect(resolveHeroiconComponent('star', 'solid')).toBe(SolidStarIcon)
    })

    it('keeps outline as the default variant', () => {
      expect(resolveIconComponent('heroicons:home')).not.toBe(SolidStarIcon)
      expect(resolveHeroiconComponent('home')).toBe(HomeIcon)
    })

    // Regression guard: Heroicons (like Lucide v1) exports icons as render
    // FUNCTIONS. A `typeof === 'object'`-only check rejects every single one of
    // them and makes all icons silently degrade to plain text.
    it('accepts functional components (the heroicons/lucide shape)', () => {
      expect(typeof resolveIconComponent('heroicons:home')).toBe('function')
    })

    // Export names mix digits and capitals in ways plain PascalCase conversion
    // cannot predict, so lookups are separator/case insensitive.
    it('resolves digit-heavy canonical names', () => {
      expect(resolveIconComponent('heroicons:bars-3')).toBe(Bars3Icon)
      expect(resolveIconComponent('heroicons:battery-100')).toBe(Battery100Icon)
      expect(resolveIconComponent('heroicons:building-office-2')).toBe(BuildingOffice2Icon)
    })

    it('falls back to Lucide for foreign icon sets (material-symbols nav data)', () => {
      // `home` exists in Heroicons, so the shared family wins…
      expect(resolveIconComponent('material-symbols:home')).toBe(HomeIcon)
      // …and a Material-Symbols-only name still resolves instead of returning null.
      expect(resolveIconComponent('material-symbols:settings')).toBeTruthy()
    })

    it('drops material-symbols variant suffixes', () => {
      // folder-open-rounded -> FolderOpenIcon
      expect(resolveIconComponent('material-symbols:folder-open-rounded')).toBeTruthy()
    })

    it('returns null for empty / unknown input', () => {
      expect(resolveIconComponent('')).toBeNull()
      expect(resolveIconComponent('   ')).toBeNull()
      expect(resolveIconComponent('heroicons:definitely-not-a-real-icon')).toBeNull()
    })

    it('caches results consistently across calls', () => {
      const a = resolveIconComponent('heroicons:star')
      const b = resolveIconComponent('heroicons:star')
      expect(a).toBe(b)
      expect(a).toBeTruthy()
    })
  })

  describe('listHeroiconNames', () => {
    it('exposes the full Heroicons v2 catalogue', () => {
      const names = listHeroiconNames()
      expect(names.length).toBeGreaterThan(300)
      expect(names).toContain('home')
      expect(names).toContain('tag')
      expect(names).toContain('folder-open')
      expect(names).toContain('archive-box')
    })

    // Strong guard: the catalogue is derived from the package exports, and every
    // listed name MUST round-trip back to a real component.
    it('resolves EVERY catalogue name', () => {
      const broken = listHeroiconNames().filter(name => !resolveIconComponent(name))
      expect(broken, `unresolvable heroicons: ${broken.join(', ')}`).toEqual([])
    })

    it('resolves EVERY catalogue name in the solid variant', () => {
      const broken = listHeroiconNames('solid').filter(
        name => !resolveHeroiconComponent(name, 'solid')
      )
      expect(broken, `unresolvable solid heroicons: ${broken.join(', ')}`).toEqual([])
    })
  })

  describe('isEmojiIcon', () => {
    it('detects emoji', () => {
      expect(isEmojiIcon('🎉')).toBe(true)
      expect(isEmojiIcon('✨')).toBe(true)
    })

    it('rejects plain text', () => {
      expect(isEmojiIcon('home')).toBe(false)
      expect(isEmojiIcon('')).toBe(false)
    })
  })
})
