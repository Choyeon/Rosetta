<!--
  TabNav — 通用标签导航（支持路由/激活态/图标）
-->
<script setup lang="ts">
export interface TabItem {
  key: string;
  label: string;
  icon?: string;
  to?: string;
}
interface Props {
  tabs: TabItem[];
  modelValue?: string;
}
withDefaults(defineProps<Props>(), { modelValue: "" });
defineEmits<{ "update:modelValue": [string] }>();
</script>

<template>
  <nav
    class="inline-flex items-center gap-0.5 p-0.5 rounded-xl bg-neutral-bg-container border border-neutral-border-secondary shadow-sm"
    role="tablist"
  >
    <template v-for="t in tabs" :key="t.key">
      <NuxtLink
        v-if="t.to"
        :to="t.to"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-fast"
        :class="modelValue === t.key ? 'bg-primary-500 text-white shadow-sm' : 'text-neutral-text-secondary hover:text-neutral-text-primary hover:bg-neutral-fill-hover'"
        role="tab"
        :aria-selected="modelValue === t.key"
        @click="$emit('update:modelValue', t.key)"
      >
        <Icon v-if="t.icon" :name="t.icon" class="w-3.5 h-3.5" />
        {{ t.label }}
      </NuxtLink>
      <button
        v-else
        type="button"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-fast"
        :class="modelValue === t.key ? 'bg-primary-500 text-white shadow-sm' : 'text-neutral-text-secondary hover:text-neutral-text-primary hover:bg-neutral-fill-hover'"
        role="tab"
        :aria-selected="modelValue === t.key"
        @click="$emit('update:modelValue', t.key)"
      >
        <Icon v-if="t.icon" :name="t.icon" class="w-3.5 h-3.5" />
        {{ t.label }}
      </button>
    </template>
  </nav>
</template>
