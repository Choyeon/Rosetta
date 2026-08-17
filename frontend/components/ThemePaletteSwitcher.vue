<template>
  <div class="theme-palette-root relative inline-flex">
    <!-- Circular ripple overlay (same technique as ThemeToggle to keep UX unified) -->
    <div
      v-if="ripple.visible"
      class="theme-palette-ripple pointer-events-none fixed inset-0 z-[9998] mix-blend-normal"
      :style="{
        background: 'hsl(var(--background))',
        clipPath: ripple.clip,
        WebkitClipPath: ripple.clip,
        transition: `clip-path ${ripple.duration}ms ${easing}, -webkit-clip-path ${ripple.duration}ms ${easing}`,
        opacity: ripple.opacity
      }"
      aria-hidden="true"
    />

    <DropdownMenu>
      <Tooltip>
        <TooltipTrigger as-child>
          <DropdownMenuTrigger as-child>
            <Button
              ref="triggerRef"
              variant="ghost"
              size="icon"
              :aria-label="t('common.palette') || '切换主题色'"
              class="relative overflow-hidden"
            >
              <Palette class="size-5" />
              <!-- A tiny swatch indicator in the corner so you can see the active palette at a glance -->
              <span
                class="pointer-events-none absolute right-[10px] bottom-[10px] size-2 rounded-full ring-1 ring-background"
                :style="{ background: currentSwatch }"
                aria-hidden="true"
              />
            </Button>
          </DropdownMenuTrigger>
        </TooltipTrigger>
        <TooltipContent>
          <p>{{ t('common.palette') || '切换主题色' }}</p>
        </TooltipContent>
      </Tooltip>

      <DropdownMenuContent
        align="end"
        class="w-52 p-2"
      >
        <div class="mb-1 px-2 pb-1 pt-0.5 text-xs text-muted-foreground">
          {{ t('common.paletteHint') || '选择主题色' }}
        </div>
        <DropdownMenuRadioGroup :value="palette">
          <button
            v-for="p in palettes"
            :key="p.id"
            type="button"
            class="theme-palette-option group flex w-full items-center gap-3 rounded-md px-2 py-2 text-sm outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:bg-accent"
            :class="palette === p.id ? 'bg-accent/70 text-accent-foreground' : 'text-foreground'"
            @click="(ev: MouseEvent) => choosePalette(p.id, ev)"
          >
            <span
              class="shrink-0 size-5 rounded-full ring-1 ring-border"
              :style="{ background: p.swatch }"
              :aria-hidden="true"
            />
            <span class="flex-1 text-left">
              {{ p.label }}
              <span class="ml-1 text-xs text-muted-foreground">{{ p.name }}</span>
            </span>
            <Check
              v-if="palette === p.id"
              class="size-4 shrink-0 text-primary"
              aria-hidden="true"
            />
          </button>
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  </div>
</template>

<script setup lang="ts">
import { Palette, Check } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useThemePalette } from '~~/composables/useThemePalette'
import {
  Button
} from '~~/components/ui/button'
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent
} from '~~/components/ui/tooltip'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuRadioGroup
} from '~~/components/ui/dropdown-menu'

const { t } = useI18n()
const { palette, palettes, applyPalette, hydratePalette, findPalette } = useThemePalette()

const triggerRef = ref<InstanceType<typeof DropdownMenuTrigger> | null>(null)
const easing = 'cubic-bezier(0.22, 1, 0.36, 1)'

const currentSwatch = computed(() => findPalette(palette.value).swatch)

interface RippleState {
  visible: boolean
  clip: string
  duration: number
  opacity: number
}
const ripple = reactive<RippleState>({
  visible: false,
  clip: 'circle(0% at 50% 50%)',
  duration: 680,
  opacity: 1
})

const circle = (x: number, y: number, r: number) =>
  `circle(${r}px at ${x}px ${y}px)`

const computeRippleRadius = (cx: number, cy: number) => {
  const vw = globalThis.window?.innerWidth || 1440
  const vh = globalThis.window?.innerHeight || 900
  const corners = [
    { x: 0, y: 0 },
    { x: vw, y: 0 },
    { x: 0, y: vh },
    { x: vw, y: vh }
  ]
  let max = 0
  for (const c of corners) {
    const d = Math.hypot(c.x - cx, c.y - cy)
    if (d > max) max = d
  }
  return Math.ceil(max)
}

const choosePalette = async (nextId: typeof palette.value, e: MouseEvent) => {
  if (!import.meta.client) {
    applyPalette(nextId)
    return
  }
  if (nextId === palette.value) return

  // origin from click, fallback to trigger center
  let originX: number
  let originY: number
  if (typeof e.clientX === 'number' && typeof e.clientY === 'number') {
    originX = e.clientX
    originY = e.clientY
  } else {
    const el = triggerRef.value?.$el as HTMLElement | undefined
    const rect = (el || document.body).getBoundingClientRect()
    originX = rect.left + rect.width / 2
    originY = rect.top + rect.height / 2
  }
  const radius = computeRippleRadius(originX, originY)

  ripple.duration = 680
  ripple.opacity = 1
  ripple.clip = circle(originX, originY, 0)
  ripple.visible = true

  // force reflow
  // eslint-disable-next-line @typescript-eslint/no-unused-expressions
  document.body.offsetHeight
  await nextTick()
  requestAnimationFrame(() => {
    ripple.clip = circle(originX, originY, radius)
  })

  // flip palette class halfway so it appears "under" the expanding circle
  const flipAt = Math.round(ripple.duration * 0.5)
  setTimeout(() => {
    applyPalette(nextId)
  }, flipAt)

  // fade & cleanup overlay
  const cleanupAt = ripple.duration + 60
  setTimeout(() => {
    ripple.opacity = 0
    requestAnimationFrame(() => {
      setTimeout(() => {
        ripple.visible = false
      }, 180)
    })
  }, cleanupAt)
}

// Hydrate persisted palette once on client mount
let hydrated = false
onMounted(() => {
  if (!import.meta.client || hydrated) return
  hydrated = true
  hydratePalette()
})
</script>
