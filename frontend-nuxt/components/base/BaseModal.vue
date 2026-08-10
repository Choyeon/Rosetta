<!--
  BaseModal — 对应 Astro src/components/base/BaseModal.astro
  特性：
    - v-model / closeOnMask / closeOnEsc / scrollLock
    - 尺寸 sm/md/lg/xl/fullscreen
    - 过渡动画（modal-enter/leave + modal-backdrop-*）
    - 多 slotted：header / default / footer
    - data-testid / aria 完备
-->
<script setup lang="ts">
// @vueuse/core 的 useModal 或自行实现；这里直接原生实现（#imports 仅在 Nuxt 运行时可用，避免显式 import 引发 ESM 静态分析）

/** 仅客户端渲染阶段启用 Teleport，SSR 直接输出到原位（避免文档节点不存在） */
const IS_CLIENT = import.meta.client;

const props = withDefaults(defineProps<{
  /** 双向绑定：是否打开 */
  open?: boolean;
  title?: string;
  /** 右上角关闭按钮 */
  closable?: boolean;
  closeOnMask?: boolean;
  closeOnEsc?: boolean;
  /** 尺寸 / 居中 */
  size?: "sm" | "md" | "lg" | "xl" | "fullscreen";
  /** 自定义 wrapper class */
  wrapperClass?: string;
  /** data-testid 前缀 */
  testid?: string;
}>(), {
  closable: true,
  closeOnMask: true,
  closeOnEsc: true,
  size: "md",
  testid: "base-modal",
});
const emit = defineEmits<{
  "update:open": [v: boolean];
  close: [];
  open: [];
}>();

const visible = defineModel<boolean>("open", { default: false });
watch(visible, (v) => {
  if (v) emit("open");
  else emit("close");
  if (import.meta.client) {
    document.documentElement.style.overflow = v ? "hidden" : "";
  }
});
onBeforeUnmount(() => {
  if (import.meta.client) document.documentElement.style.overflow = "";
});

const onEsc = (e: KeyboardEvent) => {
  if (e.key === "Escape" && props.closeOnEsc && visible.value) close();
};
onMounted(() => {
  if (import.meta.client) window.addEventListener("keydown", onEsc);
});
onBeforeUnmount(() => {
  if (import.meta.client) window.removeEventListener("keydown", onEsc);
});

function close() {
  visible.value = false;
}
function onMaskMouseDown(e: MouseEvent) {
  if ((e.target as HTMLElement)?.dataset?.mask === "1" && props.closeOnMask) close();
}

const sizeClass = computed(() => ({
  "max-w-md w-[92vw]": props.size === "sm",
  "max-w-2xl w-[94vw]": props.size === "md",
  "max-w-4xl w-[96vw]": props.size === "lg",
  "max-w-6xl w-[98vw]": props.size === "xl",
  "max-w-none w-full h-full rounded-none": props.size === "fullscreen",
}));
</script>

<template>
  <Teleport to="body" :disabled="!IS_CLIENT">
    <Transition name="modal-backdrop" appear @after-leave="() => {}">
      <div
        v-if="visible"
        class="fixed inset-0 z-modal isolate"
        :data-testid="testid"
      >
        <!-- 遮罩 -->
        <div
          data-mask="1"
          class="absolute inset-0 bg-neutral-bg-modal/60 backdrop-blur-sm animate-in fade-in"
          @mousedown="onMaskMouseDown"
        />
        <!-- 面板 -->
        <div
          class="absolute inset-0 flex items-end sm:items-center justify-center p-0 sm:p-4"
          role="dialog"
          aria-modal="true"
          :aria-label="title || (typeof testid === 'string' ? testid : 'dialog')"
        >
          <Transition name="modal-panel" appear>
            <div
              v-if="visible"
              class="bg-neutral-bg-container shadow-2xl rounded-t-2xl sm:rounded-2xl border border-neutral-border-secondary w-full flex flex-col max-h-[90vh]"
              :class="[sizeClass, wrapperClass || '']"
              :data-testid="testid + '-panel'"
            >
              <!-- Header -->
              <div
                class="flex items-center justify-between gap-md px-lg py-md border-b border-neutral-border-secondary shrink-0"
                v-if="$slots.header || title || closable"
              >
                <slot name="header">
                  <h2 class="text-lg font-semibold text-neutral-text-primary truncate">{{ title }}</h2>
                </slot>
                <button
                  v-if="closable"
                  type="button"
                  class="w-8 h-8 rounded-md flex items-center justify-center text-neutral-text-secondary hover:bg-neutral-fill-hover hover:text-primary-500 transition-colors duration-fast ease-out"
                  :aria-label="'关闭 ' + (title || '弹窗')"
                  :data-testid="testid + '-close-btn'"
                  @click="close"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5">
                    <path d="M18 6 6 18M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <!-- Body -->
              <div class="flex-1 min-h-0 overflow-y-auto px-lg py-md" :data-testid="testid + '-body'">
                <slot />
              </div>

              <!-- Footer -->
              <div
                v-if="$slots.footer"
                class="px-lg py-md border-t border-neutral-border-secondary shrink-0 flex flex-wrap items-center justify-end gap-xs"
                :data-testid="testid + '-footer'"
              >
                <slot name="footer">
                  <button
                    type="button"
                    class="px-4 py-2 rounded-md text-sm font-medium bg-neutral-fill-hover text-neutral-text-primary hover:bg-neutral-fill-active"
                    @click="close"
                  >关闭</button>
                </slot>
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-backdrop-enter-active, .modal-backdrop-leave-active { transition: opacity 160ms ease-out; }
.modal-backdrop-enter-from, .modal-backdrop-leave-to { opacity: 0; }

.modal-panel-enter-active, .modal-panel-leave-active {
  transition: transform 200ms cubic-bezier(.16,1,.3,1), opacity 180ms ease-out;
}
.modal-panel-enter-from, .modal-panel-leave-to { opacity: 0; transform: translateY(16px) scale(.98); }
</style>
