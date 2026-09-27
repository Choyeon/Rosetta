<!--
  全屏图片预览灯箱（相册 / 媒体库共用）。
  契约：`v-model:open` 由父组件持有；`images` 可在打开后变化（删除照片时索引会夹回有效范围）。
  键盘：Esc 关闭、←/→ 翻页、Tab 圈在弹窗内并在关闭后把焦点还给触发元素。
-->
<template>
  <Teleport to="body">
    <Transition name="lightbox">
      <div
        v-if="open"
        ref="overlay"
        class="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center"
        role="dialog"
        aria-modal="true"
        tabindex="-1"
        :aria-label="currentTitle || '图片预览'"
        @click.self="close"
        @keydown.tab="onTabKey"
      >
        <button
          class="absolute top-4 right-4 z-10 size-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors"
          aria-label="关闭预览"
          @click="close"
        >
          <X class="size-5" />
        </button>

        <button
          v-if="images.length > 1"
          class="absolute left-4 z-10 size-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors"
          aria-label="上一张"
          @click.stop="prev"
        >
          <ChevronLeft class="size-5" />
        </button>

        <button
          v-if="images.length > 1"
          class="absolute right-4 z-10 size-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors"
          aria-label="下一张"
          @click.stop="next"
        >
          <ChevronRight class="size-5" />
        </button>

        <div class="relative max-w-[90vw] max-h-[90vh] flex flex-col items-center">
          <img
            v-if="currentImage"
            :src="currentImage"
            :alt="currentTitle"
            class="max-w-full max-h-[85vh] object-contain rounded-lg"
          >
          <p
            v-else
            class="text-white/70 text-sm py-16"
          >
            该照片没有可用的图片地址
          </p>
          <div
            v-if="currentTitle"
            class="mt-3 text-white/80 text-sm text-center max-w-[80vw]"
          >
            {{ currentTitle }}
          </div>
          <div
            v-if="images.length > 1"
            class="mt-2 text-white/50 text-xs"
          >
            {{ currentIndex + 1 }} / {{ images.length }}
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { X, ChevronLeft, ChevronRight } from '@lucide/vue'

interface LightboxImage {
  url: string
  title?: string
}

const props = defineProps<{
  open: boolean
  images: LightboxImage[]
  initialIndex?: number
}>()

const emit = defineEmits<{ (e: 'update:open', v: boolean): void }>()

const currentIndex = ref(props.initialIndex ?? 0)
const overlay = ref<HTMLElement | null>(null)
// 打开前最后一个获得焦点的元素；关闭后必须还回去，否则键盘用户回到页面时焦点掉到 body
let opener: HTMLElement | null = null

const currentImage = computed(() => props.images[currentIndex.value]?.url ?? '')
const currentTitle = computed(() => props.images[currentIndex.value]?.title ?? '')

watch(
  () => props.open,
  async (v) => {
    if (v) {
      currentIndex.value = props.initialIndex ?? 0
      opener = document.activeElement as HTMLElement | null
      // 遮罩本身 tabindex="-1"：聚焦它才能收到 Tab 事件，进而在下方做焦点循环
      await nextTick()
      overlay.value?.focus()
    } else {
      opener?.focus()
      opener = null
    }
  }
)

watch(
  () => props.initialIndex,
  (v) => {
    if (v != null) currentIndex.value = v
  }
)

// 列表在预览过程中变短（删除照片）时把索引夹回有效范围，否则翻到空白页
watch(
  () => props.images.length,
  (n) => {
    if (n === 0) {
      currentIndex.value = 0
      return
    }
    if (currentIndex.value > n - 1) currentIndex.value = n - 1
  }
)

function close() {
  emit('update:open', false)
}

function prev() {
  const n = props.images.length
  if (!n) return
  currentIndex.value = (currentIndex.value - 1 + n) % n
}

function next() {
  const n = props.images.length
  if (!n) return
  currentIndex.value = (currentIndex.value + 1) % n
}

function onKeydown(e: KeyboardEvent) {
  if (!props.open) return
  if (e.key === 'Escape') close()
  if (e.key === 'ArrowLeft') prev()
  if (e.key === 'ArrowRight') next()
}

/** 把 Tab 圈在弹窗内：`aria-modal` 只告诉 AT「背后不可用」，浏览器不会自动阻焦点外逃。 */
function onTabKey(e: KeyboardEvent) {
  const root = overlay.value
  if (!root) return
  const focusables = Array.from(
    root.querySelectorAll<HTMLElement>('button:not([disabled])')
  ).filter(el => el.offsetParent !== null)
  if (!focusables.length) return
  const first = focusables[0]!
  const last = focusables[focusables.length - 1]!
  const active = document.activeElement
  if (e.shiftKey && (active === first || active === root)) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && active === last) {
    e.preventDefault()
    first.focus()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.lightbox-enter-active,
.lightbox-leave-active {
  transition: opacity 0.2s ease;
}
.lightbox-enter-from,
.lightbox-leave-to {
  opacity: 0;
}
</style>
