<!--
  DropdownMenu — 通用下拉菜单（触发区 + 菜单项）
  props: items[{key, label, icon, to, onClick, danger, disabled}]
-->
<script setup lang="ts">
export interface MenuItem {
  key: string;
  label: string;
  icon?: string;
  to?: string;
  href?: string;
  onClick?: () => void;
  danger?: boolean;
  disabled?: boolean;
  divider?: boolean;
  shortcut?: string;
}
interface Props {
  items: MenuItem[];
  placement?: "left" | "right";
  offset?: number;
}
withDefaults(defineProps<Props>(), { placement: "right", offset: 8 });
defineEmits<{ select: [key: string] }>();

const open = ref(false);
const wrapRef = ref<HTMLElement | null>(null);

function onDocClick(e: MouseEvent) {
  if (!wrapRef.value) return;
  if (!wrapRef.value.contains(e.target as Node)) open.value = false;
}

onMounted(() => {
  document.addEventListener("mousedown", onDocClick);
  onBeforeUnmount(() => document.removeEventListener("mousedown", onDocClick));
});

function select(item: MenuItem) {
  if (item.disabled || item.divider) return;
  open.value = false;
  if (typeof item.onClick === "function") item.onClick();
  if (item.key) emit("select", item.key);
}
</script>

<template>
  <div ref="wrapRef" class="relative inline-block">
    <slot :open="open" :toggle="() => open = !open" />
    <Transition name="dropdown">
      <ul
        v-show="open"
        role="menu"
        class="absolute z-popover min-w-[180px] mt-1 rounded-xl shadow-lg border border-neutral-border-secondary bg-neutral-bg-container py-1 overflow-hidden"
        :class="placement === 'left' ? 'left-0' : 'right-0'"
        :style="{ marginTop: `${offset}px` }"
      >
        <template v-for="it in items" :key="it.key">
          <li v-if="it.divider" role="separator" class="my-1 border-t border-neutral-border-secondary" />
          <template v-else>
            <NuxtLink
              v-if="it.to"
              :to="it.to"
              class="flex items-center gap-2 px-3 py-2 text-sm transition-colors duration-fast"
              :class="[
                it.disabled ? 'opacity-40 pointer-events-none' : '',
                it.danger ? 'text-rose-500 hover:bg-rose-500/10' : 'text-neutral-text-secondary hover:bg-neutral-fill-hover hover:text-neutral-text-primary',
              ]"
              role="menuitem"
              @click="select(it)"
            >
              <Icon v-if="it.icon" :name="it.icon" class="w-4 h-4 flex-shrink-0" />
              <span class="flex-1 line-clamp-1">{{ it.label }}</span>
              <span v-if="it.shortcut" class="text-[10px] text-neutral-text-quaternary font-mono ml-2">{{ it.shortcut }}</span>
            </NuxtLink>
            <a
              v-else-if="it.href"
              :href="it.href"
              target="_blank"
              rel="noopener nofollow"
              class="flex items-center gap-2 px-3 py-2 text-sm transition-colors duration-fast"
              :class="[
                it.disabled ? 'opacity-40 pointer-events-none' : '',
                it.danger ? 'text-rose-500 hover:bg-rose-500/10' : 'text-neutral-text-secondary hover:bg-neutral-fill-hover hover:text-neutral-text-primary',
              ]"
              role="menuitem"
              @click="select(it)"
            >
              <Icon v-if="it.icon" :name="it.icon" class="w-4 h-4 flex-shrink-0" />
              <span class="flex-1 line-clamp-1">{{ it.label }}</span>
              <Icon name="material-symbols:open-in-new-rounded" class="w-3 h-3 text-neutral-text-quaternary ml-2" />
            </a>
            <button
              v-else
              type="button"
              class="w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors duration-fast text-left"
              :class="[
                it.disabled ? 'opacity-40 pointer-events-none' : '',
                it.danger ? 'text-rose-500 hover:bg-rose-500/10' : 'text-neutral-text-secondary hover:bg-neutral-fill-hover hover:text-neutral-text-primary',
              ]"
              role="menuitem"
              @click="select(it)"
            >
              <Icon v-if="it.icon" :name="it.icon" class="w-4 h-4 flex-shrink-0" />
              <span class="flex-1 line-clamp-1">{{ it.label }}</span>
              <span v-if="it.shortcut" class="text-[10px] text-neutral-text-quaternary font-mono ml-2">{{ it.shortcut }}</span>
            </button>
          </template>
        </template>
      </ul>
    </Transition>
  </div>
</template>

<style scoped>
.dropdown-enter-active, .dropdown-leave-active { transition: opacity 120ms ease, transform 120ms ease; }
.dropdown-enter-from, .dropdown-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
