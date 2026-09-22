<template>
  <Teleport to="body">
    <Transition name="lightbox">
      <div
        v-if="open"
        class="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center"
        @click.self="close"
      >
        <button
          class="absolute top-4 right-4 z-10 size-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors"
          @click="close"
        >
          <X class="size-5" />
        </button>

        <button
          v-if="images.length > 1"
          class="absolute left-4 z-10 size-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors"
          @click.stop="prev"
        >
          <ChevronLeft class="size-5" />
        </button>

        <button
          v-if="images.length > 1"
          class="absolute right-4 z-10 size-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors"
          @click.stop="next"
        >
          <ChevronRight class="size-5" />
        </button>

        <div class="relative max-w-[90vw] max-h-[90vh] flex flex-col items-center">
          <img
            :src="currentImage"
            :alt="currentTitle"
            class="max-w-full max-h-[85vh] object-contain rounded-lg"
            @click.stop
          >
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
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
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

const currentImage = computed(() => props.images[currentIndex.value]?.url ?? '')
const currentTitle = computed(() => props.images[currentIndex.value]?.title ?? '')

watch(
  () => props.open,
  (v) => {
    if (v) currentIndex.value = props.initialIndex ?? 0
  }
)

watch(
  () => props.initialIndex,
  (v) => {
    if (v != null) currentIndex.value = v
  }
)

function close() {
  emit('update:open', false)
}

function prev() {
  currentIndex.value = (currentIndex.value - 1 + props.images.length) % props.images.length
}

function next() {
  currentIndex.value = (currentIndex.value + 1) % props.images.length
}

function onKeydown(e: KeyboardEvent) {
  if (!props.open) return
  if (e.key === 'Escape') close()
  if (e.key === 'ArrowLeft') prev()
  if (e.key === 'ArrowRight') next()
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
