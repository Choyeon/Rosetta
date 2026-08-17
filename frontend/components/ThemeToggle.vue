<template>
<<<<<<< Updated upstream
  <Button variant="ghost" size="icon" @click="toggleTheme" :aria-label="isDark ? '切换到浅色模式' : '切换到深色模式'">
    <Sun v-if="isDark" class="size-5" />
    <Moon v-else class="size-5" />
  </Button>
=======
  <div class="theme-toggle-root relative inline-flex">
    <!-- Expansion overlay: fills with opposite theme color from click position -->
    <div
      v-if="ripple.visible"
      class="theme-ripple pointer-events-none fixed inset-0 z-[9998] mix-blend-normal"
      :style="{
        background: ripple.target === 'dark' ? 'hsl(var(--background))' : 'hsl(var(--background))',
        clipPath: ripple.clip,
        WebkitClipPath: ripple.clip,
        transition: `clip-path ${ripple.duration}ms ${easing}, -webkit-clip-path ${ripple.duration}ms ${easing}`,
        opacity: ripple.opacity
      }"
      aria-hidden="true"
    />

    <Button
      ref="buttonRef"
      variant="ghost"
      size="icon"
      :aria-label="isDark ? (t('common.themeDark') || 'Switch to light mode') : (t('common.themeLight') || 'Switch to dark mode')"
      class="relative overflow-hidden"
      @click="handleToggle"
    >
      <Sun v-if="isDark" class="size-5" />
      <Moon v-else class="size-5" />
    </Button>
  </div>
>>>>>>> Stashed changes
</template>

<script setup lang="ts">
import { Button } from '~~/components/ui/button'
import { Sun, Moon } from '@lucide/vue'
<<<<<<< Updated upstream

const isDark = ref(false)

const toggleTheme = () => {
  isDark.value = !isDark.value
  if (isDark.value) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

onMounted(() => {
  const stored = localStorage.getItem('theme')
  if (stored === 'dark' || (!stored && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    isDark.value = true
    document.documentElement.classList.add('dark')
  }
})

watch(isDark, (val) => {
  localStorage.setItem('theme', val ? 'dark' : 'light')
=======
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const buttonRef = ref<InstanceType<typeof Button> | null>(null)
const isDark = ref(false)

const easing = 'cubic-bezier(0.22, 1, 0.36, 1)'

interface RippleState {
  visible: boolean
  clip: string
  target: 'light' | 'dark'
  duration: number
  opacity: number
}
const ripple = reactive<RippleState>({
  visible: false,
  clip: 'circle(0% at 50% 50%)',
  target: 'light',
  duration: 700,
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

const applyTheme = (dark: boolean) => {
  isDark.value = dark
  const root = document.documentElement
  if (dark) root.classList.add('dark')
  else root.classList.remove('dark')
  const meta = document.querySelector('meta[name="theme-color"]') as HTMLMetaElement | null
  if (meta) {
    // read CSS vars
    const bg = getComputedStyle(root).getPropertyValue('--background').trim()
    meta.content = bg ? `hsl(${bg})` : (dark ? '#0b1020' : '#ffffff')
  }
}

const handleToggle = async (e: MouseEvent) => {
  if (!import.meta.client) return

  const nextDark = !isDark.value
  const target: 'light' | 'dark' = nextDark ? 'dark' : 'light'

  // Compute origin from click position; fallback to button center
  let originX: number
  let originY: number
  if (typeof e.clientX === 'number' && typeof e.clientY === 'number') {
    originX = e.clientX
    originY = e.clientY
  } else {
    const el = (buttonRef.value as any)?.$el as HTMLElement | undefined
    const btn = el || document.body
    const r = btn.getBoundingClientRect()
    originX = r.left + r.width / 2
    originY = r.top + r.height / 2
  }
  const radius = computeRippleRadius(originX, originY)

  // 1) Start overlay at 0 radius
  ripple.target = target
  ripple.duration = 680
  ripple.opacity = 1
  ripple.clip = circle(originX, originY, 0)
  ripple.visible = true

  // Force reflow then grow the circle
  // eslint-disable-next-line @typescript-eslint/no-unused-expressions
  document.body.offsetHeight
  await nextTick()
  requestAnimationFrame(() => {
    ripple.clip = circle(originX, originY, radius)
  })

  // 2) ~halfway through the animation, flip the DOM theme class
  const flipAt = Math.round(ripple.duration * 0.5)
  setTimeout(() => {
    applyTheme(nextDark)
  }, flipAt)

  // 3) fade out overlay then hide
  const cleanupAt = ripple.duration + 80
  setTimeout(() => {
    ripple.opacity = 0
    requestAnimationFrame(() => {
      setTimeout(() => {
        ripple.visible = false
      }, 200)
    })
  }, cleanupAt)
}

// Initial hydration
onMounted(() => {
  if (!import.meta.client) return
  const stored = localStorage.getItem('theme')
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const dark = stored === 'dark' || (!stored && prefersDark)
  applyTheme(dark)
})

watch(isDark, (val) => {
  if (import.meta.client) localStorage.setItem('theme', val ? 'dark' : 'light')
>>>>>>> Stashed changes
})
</script>
