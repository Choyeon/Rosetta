<!--
  通用后台 CRUD 弹窗外壳（v2）：三段式结构 —— 固定头部 / 可滚动内容 / 固定底部操作栏。
  ---------------------------------------------------------------------------
  旧版把 max-h 与 overflow-y 挂在整张 DialogContent 上，长表单（分类/系列/公告）
  滚动时标题和「保存」一起被卷走，用户写了半屏就看不到提交按钮在哪。
  现在头部与底部固定，只有中间内容区滚动；提交按钮带 loading 态，并支持
  左槽（#footer-left）放"必填项/影响范围"之类的说明。
  硬契约不变：本组件不持有任何表单状态，提交成功后也不会自动关闭——父级必须监听
  submit 自行校验/发请求，并在完成后通过 update:open 关闭弹窗。
-->
<script setup lang="ts">
import type { Component, HTMLAttributes } from 'vue'
import { Loader2 } from '@lucide/vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '~~/components/ui/dialog'
import { Button } from '~~/components/ui/button'
import { cn } from '~~/lib/utils'

interface Props {
  open: boolean
  title: string
  description?: string
  loading?: boolean
  submitText?: string
  cancelText?: string
  /** 头部图标（与 AdminPageHeader 的图标方块同一口径） */
  icon?: Component
  /** 宽度档：sm=表单级 / md=常规 / lg=带 i18n 页签的表单（默认）/ xl=富表单 */
  size?: 'sm' | 'md' | 'lg' | 'xl'
  class?: HTMLAttributes['class']
}

const props = withDefaults(defineProps<Props>(), {
  submitText: '保存',
  cancelText: '取消',
  size: 'lg',
  loading: false,
  description: undefined,
  icon: undefined,
  class: undefined
})

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'submit'): void
}>()

const sizeClass = computed(() => {
  switch (props.size) {
    case 'sm': return 'max-w-md'
    case 'md': return 'max-w-xl'
    case 'xl': return 'max-w-4xl'
    default: return 'max-w-2xl'
  }
})

function submit() {
  if (props.loading) return
  emit('submit')
}
</script>

<template>
  <Dialog
    :open="open"
    @update:open="(v: boolean) => emit('update:open', v)"
  >
    <DialogContent
      :class="cn(
        'p-0 gap-0 flex flex-col max-h-[88svh] overflow-hidden',
        sizeClass,
        props.class
      )"
    >
      <DialogHeader class="shrink-0 border-b border-border/70 bg-muted/20 px-6 py-4 text-left">
        <div class="flex items-start gap-3 pr-8">
          <div
            v-if="icon"
            class="size-10 shrink-0 rounded-xl bg-primary/10 text-primary flex items-center justify-center"
          >
            <component
              :is="icon"
              class="size-5"
            />
          </div>
          <div class="min-w-0">
            <DialogTitle class="text-base font-semibold tracking-tight">
              {{ title }}
            </DialogTitle>
            <DialogDescription
              v-if="description"
              class="mt-1 text-xs leading-relaxed text-muted-foreground"
            >
              {{ description }}
            </DialogDescription>
          </div>
        </div>
      </DialogHeader>

      <div class="min-h-0 flex-1 overflow-y-auto px-6 py-5">
        <slot />
      </div>

      <DialogFooter class="shrink-0 border-t border-border/70 bg-muted/20 px-6 py-3 flex-row items-center gap-3 sm:justify-between">
        <div class="min-w-0 flex-1 text-xs text-muted-foreground">
          <slot name="footer-left" />
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            :disabled="loading"
            @click="emit('update:open', false)"
          >
            {{ cancelText }}
          </Button>
          <Button
            size="sm"
            :disabled="loading"
            @click="submit"
          >
            <Loader2
              v-if="loading"
              data-icon="inline-start"
              class="animate-spin"
            />
            {{ loading ? '保存中...' : submitText }}
          </Button>
        </div>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
