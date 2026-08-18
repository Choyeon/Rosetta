<script setup lang="ts" generic="T">
import type { SelectRootEmits, SelectRootProps } from 'reka-ui'
import { SelectRoot, useForwardPropsEmits } from 'reka-ui'

/**
 * 支持原始类型 v-model（string / number / boolean 等）。
 *
 * 说明：reka-ui SelectRoot 内部对 modelValue 的处理假设是 "如果是对象并且有 .value 属性，
 * 则作为 ref-like 直接写入"；当 Select 被一层 Select.vue 包装时，使用 useForwardPropsEmits
 * 透传 defineProps<SelectRootProps>() 会导致 modelValue 从 Vue 的 `defineModel -> props.modelValue`
 * 链路里已经被 Vue 解包为原始值（例如数字 1），此时 reka-ui SelectRoot 更新时内部做
 * `modelValue.value = newValue` → TypeError: Cannot create property 'value' on number '1'。
 *
 * 修复：显式使用 defineModel + 手动重传 modelValue / onUpdate:modelValue 对，
 * 让 reka-ui SelectRoot 的 modelValue 绑定始终指向 "一个响应式 getter"（计算属性返回当前 model 值，
 * 并在 update:modelValue 时反写 defineModel.value），保持 Vue 标准 ref/原始值语义。
 * 其他 props 继续走 useForwardPropsEmits 保持类型一致性，只手动拼上 model 这一对。
 */
const model = defineModel<T>()

const props = defineProps<Omit<SelectRootProps, 'modelValue' | 'onUpdate:modelValue' | 'update:modelValue'>>()
const emits = defineEmits<Omit<SelectRootEmits, 'update:modelValue'>>()

const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <SelectRoot
    v-bind="forwarded"
    :model-value="model as unknown as SelectRootProps['modelValue']"
    @update:model-value="(v) => { model = v as unknown as T }"
  >
    <slot />
  </SelectRoot>
</template>
