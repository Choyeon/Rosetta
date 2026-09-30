<!--
  头像 + 称号角标的统一渲染入口。
  关键契约：resolvedAvatarUrl 优先于 avatar —— 前者来自后端 /api/media/avatar 代理链
  （白名单 302 → 非白名单流式代理 → DiceBear 兜底），后者是未做 SSRF 处理的原始串，
  两个 prop 同时传时必须以解析后的 URL 为准（解析逻辑收敛在 useResolvedAvatar）。
  size 传数值时以内联 style 输出确定像素，配合 fallback 字母保证图片迟到也不抖动（CLS）。

  ===== 为什么不用 reka Avatar（2026-10-01）=====
  SSR 产物里 reka-ui 是 external 的（nitro trace 拷贝），运行时加载的 vue 与主 app
  内嵌的 vue 是两个实例 → reka 组件的 provide/inject 跨实例失效 → AvatarRoot 在
  SSR 渲染成空注释节点（客户端是 span）→ 每个头像一处节点级 hydration mismatch
  （首页 25 处）。改为纯原生 span/img 复刻（视觉样式沿用 avatarVariant）：
  - 容器 span 两端都渲染 → 消灭根 mismatch
  - img 两端首帧都渲染（同 src）→ hydration 一致；加载失败仅在客户端隐藏
  - fallback 字母 v-if="mounted"：两端首帧都是注释，挂载后普通响应式更新；
    字母定位在 img 之上（absolute inset-0），img 加载成功后由 imgOk 隐藏
-->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { avatarVariant } from '~~/components/ui/avatar'
import type { AvatarVariants } from '~~/components/ui/avatar'
import { resolveAvatarUrl } from '~~/composables/useResolvedAvatar'
import type { AdminUserTitle } from '~~/composables/useAdminManage'
import TitleIconSvg from '~~/components/TitleIconSvg.vue'
import { cn } from '~~/lib/utils'

const props = withDefaults(defineProps<{
  avatar?: string | null
  resolvedAvatarUrl?: string | null
  seed?: string
  name?: string
  title?: AdminUserTitle | null
  size?: number | AvatarVariants['size']
  showTitle?: boolean
  class?: string
}>(), {
  size: 40,
  showTitle: true,
  title: null
})

// ===== Hydration 安全（2026-10-01）=====
// fallback 字母推迟到挂载完成后显示：两端首帧一致（注释 vs 注释），挂载后是
// 普通响应式更新。名字首字母本就是兜底视觉，晚一帧无感知。
const mounted = ref(false)
onMounted(() => {
  mounted.value = true
})

// 图片加载状态：null=未知（加载中）、true=成功、false=失败。
// 失败仅在客户端置位（@error 不会在 SSR 触发），不构成 hydration 差异。
const imgOk = ref<boolean | null>(null)
const onImgLoad = () => {
  imgOk.value = true
}
const onImgError = () => {
  imgOk.value = false
}

const avatarUrl = computed(() => {
  const seedStr = props.seed || props.name || undefined
  return resolveAvatarUrl(
    { seed: seedStr },
    props.resolvedAvatarUrl ?? undefined,
    props.avatar ?? undefined
  )
})

const fallbackText = computed(() => {
  const n = props.name?.trim()
  return n ? n.charAt(0).toUpperCase() : 'U'
})

const numericPx = computed<number | null>(() => {
  return typeof props.size === 'number' ? props.size : null
})
const avatarVariantSize = computed<AvatarVariants['size'] | undefined>(() => {
  return typeof props.size === 'string' ? props.size as AvatarVariants['size'] : undefined
})
const avatarStyle = computed(() => {
  if (numericPx.value == null) return undefined
  const px = numericPx.value
  return {
    width: px + 'px',
    height: px + 'px',
    fontSize: Math.max(10, Math.round(px * 0.28)) + 'px',
    lineHeight: '1'
  }
})
const fallbackClass = computed(() => {
  if (numericPx.value == null) return ''
  if (numericPx.value <= 32) return 'px-0 py-0'
  return ''
})

// 字母兜底的显示时机：挂载后且（无图 / 图片加载失败）。
// 图片加载中不显示字母（避免字母压在半加载的 img 上闪烁），
// 而是保留 img 的占位背景（容器自带 bg-secondary）。
const showFallback = computed(() => mounted.value && (!avatarUrl.value || imgOk.value === false))

const badgeSize = computed(() => {
  let px = 10
  if (typeof props.size === 'number') {
    px = Math.round(props.size * 0.45)
  } else if (props.size === 'sm') {
    px = 16
  } else if (props.size === 'base') {
    px = 26
  } else if (props.size === 'lg') {
    px = 52
  }
  return Math.max(8, px)
})

const hasTitleIcon = computed(() => {
  return props.showTitle && props.title && props.title.icon
})

const titleColor = computed(() => props.title?.color || '#3b82f6')

const getLocalizedStr = (v: string | Record<string, string> | null | undefined): string => {
  if (v == null) return ''
  if (typeof v === 'string') return v
  return v.zh || v.en || Object.values(v)[0] || ''
}

const titleDisplayName = computed(() => getLocalizedStr(props.title?.name))
</script>

<template>
  <div
    :class="['relative inline-flex shrink-0 rounded-full', props.class]"
  >
    <span
      :class="cn(avatarVariant({ size: avatarVariantSize, shape: 'circle' }), 'ring-1 ring-border/60 rounded-full relative')"
      :style="avatarStyle"
    >
      <img
        v-if="avatarUrl"
        :src="avatarUrl"
        :alt="name || 'avatar'"
        class="h-full w-full object-cover rounded-full"
        @load="onImgLoad"
        @error="onImgError"
      >
      <span
        v-if="showFallback"
        class="absolute inset-0 flex items-center justify-center bg-primary/10 text-primary font-semibold rounded-full select-none"
        :class="fallbackClass"
      >{{ fallbackText }}</span>
    </span>

    <span
      v-if="hasTitleIcon"
      class="absolute -bottom-0.5 -right-0.5 z-10 flex items-center justify-center rounded-full border-2 border-background"
      :style="{
        width: badgeSize + 'px',
        height: badgeSize + 'px',
        backgroundColor: titleColor,
        color: '#fff'
      }"
      :title="titleDisplayName"
    >
      <TitleIconSvg
        :icon="title?.icon"
        :stroke-width="2.5"
        class="size-[60%]"
      />
    </span>
  </div>
</template>
