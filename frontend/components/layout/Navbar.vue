<!--
  Navbar — 通用页内导航（Tab 风格，非全站 AppHeader）
  v-model:activeKey 控制激活
  props: items[{ key, label, icon, to }]；variant (tabs | pills | underline)
-->
<script setup lang="ts">
export interface NavItem {
  key: string;
  label: string;
  icon?: string;
  to?: string;
  badge?: string | number;
  disabled?: boolean;
}
interface Props {
  items: NavItem[];
  modelValue?: string;
  variant?: "tabs" | "pills" | "underline";
  size?: "sm" | "md";
}
withDefaults(defineProps<Props>(), { variant: "pills", size: "md" });
defineEmits<{ "update:modelValue": [string] }>();

const active = computed({
  get: () => props.modelValue || (props.items[0]?.key ?? ""),
  set: (v) => emit("update:modelValue", v),
});
</script>

<template>
  <nav class="navbar-wrapper">
    <!-- tabs 变体：带底部圆角边 -->
    <div
      v-if="variant === 'tabs'"
      class="inline-flex items-end gap-1 border-b border-neutral-border-secondary w-full overflow-x-auto"
      role="tablist"
    >
      <template v-for="it in items" :key="it.key">
        <NuxtLink
          v-if="it.to"
          :to="it.to"
          class="relative inline-flex items-center gap-1.5 px-3 py-2 border-b-2 -mb-px font-medium transition-colors whitespace-nowrap"
          :class="[
            size === 'sm' ? 'text-xs' : 'text-sm',
            it.disabled ? 'opacity-50 pointer-events-none' : '',
            active === it.key
              ? 'text-primary-500 border-primary-500'
              : 'text-neutral-text-secondary border-transparent hover:text-neutral-text-primary',
          ]"
          role="tab"
          :aria-selected="active === it.key"
          @click="active = it.key"
        >
          <Icon v-if="it.icon" :name="it.icon" class="w-4 h-4" />
          {{ it.label }}
          <span v-if="it.badge !== undefined" class="ml-0.5 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-primary-500/10 text-primary-500 text-[10px] font-semibold">{{ it.badge }}</span>
        </NuxtLink>
        <button
          v-else
          type="button"
          class="relative inline-flex items-center gap-1.5 px-3 py-2 border-b-2 -mb-px font-medium transition-colors whitespace-nowrap"
          :class="[
            size === 'sm' ? 'text-xs' : 'text-sm',
            it.disabled ? 'opacity-50 pointer-events-none' : '',
            active === it.key
              ? 'text-primary-500 border-primary-500'
              : 'text-neutral-text-secondary border-transparent hover:text-neutral-text-primary',
          ]"
          role="tab"
          :aria-selected="active === it.key"
          @click="active = it.key"
        >
          <Icon v-if="it.icon" :name="it.icon" class="w-4 h-4" />
          {{ it.label }}
          <span v-if="it.badge !== undefined" class="ml-0.5 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-primary-500/10 text-primary-500 text-[10px] font-semibold">{{ it.badge }}</span>
        </button>
      </template>
    </div>

    <!-- pills 变体：胶囊填充 -->
    <div
      v-else-if="variant === 'pills'"
      class="inline-flex flex-wrap items-center gap-1 p-1 rounded-xl bg-neutral-bg-container border border-neutral-border-secondary shadow-sm"
      role="tablist"
    >
      <template v-for="it in items" :key="it.key">
        <NuxtLink
          v-if="it.to"
          :to="it.to"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all whitespace-nowrap"
          :class="[
            size === 'sm' ? 'text-xs' : 'text-sm',
            it.disabled ? 'opacity-40 pointer-events-none' : '',
            active === it.key
              ? 'bg-primary-500 text-white shadow-sm'
              : 'text-neutral-text-secondary hover:text-neutral-text-primary hover:bg-neutral-fill-hover',
          ]"
          role="tab"
          :aria-selected="active === it.key"
          @click="active = it.key"
        >
          <Icon v-if="it.icon" :name="it.icon" class="w-4 h-4" />
          {{ it.label }}
          <span v-if="it.badge !== undefined" class="inline-flex items-center justify-center min-w-[16px] h-4 px-1 rounded-full" :class="active === it.key ? 'bg-white/20 text-white' : 'bg-neutral-fill-hover text-neutral-text-quaternary'" style="font-size: 10px;">{{ it.badge }}</span>
        </NuxtLink>
        <button
          v-else
          type="button"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all whitespace-nowrap"
          :class="[
            size === 'sm' ? 'text-xs' : 'text-sm',
            it.disabled ? 'opacity-40 pointer-events-none' : '',
            active === it.key
              ? 'bg-primary-500 text-white shadow-sm'
              : 'text-neutral-text-secondary hover:text-neutral-text-primary hover:bg-neutral-fill-hover',
          ]"
          role="tab"
          :aria-selected="active === it.key"
          @click="active = it.key"
        >
          <Icon v-if="it.icon" :name="it.icon" class="w-4 h-4" />
          {{ it.label }}
          <span v-if="it.badge !== undefined" class="inline-flex items-center justify-center min-w-[16px] h-4 px-1 rounded-full" :class="active === it.key ? 'bg-white/20 text-white' : 'bg-neutral-fill-hover text-neutral-text-quaternary'" style="font-size: 10px;">{{ it.badge }}</span>
        </button>
      </template>
    </div>

    <!-- underline 变体：下划线强调 -->
    <div
      v-else
      class="flex items-center gap-4 border-b border-neutral-border-secondary overflow-x-auto"
      role="tablist"
    >
      <template v-for="it in items" :key="it.key">
        <NuxtLink
          v-if="it.to"
          :to="it.to"
          class="relative py-2 font-medium whitespace-nowrap transition-colors"
          :class="[
            size === 'sm' ? 'text-xs' : 'text-sm',
            it.disabled ? 'opacity-40 pointer-events-none' : '',
            active === it.key ? 'text-primary-500' : 'text-neutral-text-secondary hover:text-neutral-text-primary',
          ]"
          role="tab"
          @click="active = it.key"
        >
          <span class="inline-flex items-center gap-1.5">
            <Icon v-if="it.icon" :name="it.icon" class="w-4 h-4" />
            {{ it.label }}
            <span v-if="it.badge !== undefined" class="inline-flex items-center justify-center min-w-[16px] h-4 px-1 rounded-full bg-primary-500/10 text-primary-500" style="font-size: 10px;">{{ it.badge }}</span>
          </span>
          <span
            v-if="active === it.key"
            class="absolute left-0 right-0 -bottom-px h-0.5 rounded-full bg-primary-500"
            aria-hidden
          />
        </NuxtLink>
        <button
          v-else
          type="button"
          class="relative py-2 font-medium whitespace-nowrap transition-colors"
          :class="[
            size === 'sm' ? 'text-xs' : 'text-sm',
            it.disabled ? 'opacity-40 pointer-events-none' : '',
            active === it.key ? 'text-primary-500' : 'text-neutral-text-secondary hover:text-neutral-text-primary',
          ]"
          role="tab"
          @click="active = it.key"
        >
          <span class="inline-flex items-center gap-1.5">
            <Icon v-if="it.icon" :name="it.icon" class="w-4 h-4" />
            {{ it.label }}
            <span v-if="it.badge !== undefined" class="inline-flex items-center justify-center min-w-[16px] h-4 px-1 rounded-full bg-primary-500/10 text-primary-500" style="font-size: 10px;">{{ it.badge }}</span>
          </span>
          <span
            v-if="active === it.key"
            class="absolute left-0 right-0 -bottom-px h-0.5 rounded-full bg-primary-500"
            aria-hidden
          />
        </button>
      </template>
    </div>
  </nav>
</template>
