<!--
  头像 + 称号角标的统一渲染入口（全站唯一的头像 <img> 渲染点）。
  关键契约：resolvedAvatarUrl 优先于 avatar —— 前者来自后端 /api/media/avatar 代理链
  （白名单 302 → 非白名单流式代理 → DiceBear 兜底），后者是未做 SSRF 处理的原始串，
  两个 prop 同时传时必须以解析后的 URL 为准（解析逻辑收敛在 useResolvedAvatar）。
  size 传数值时以内联 style 输出确定像素，配合占位层保证图片迟到也不抖动（CLS）。

  ===== 三态统一（2026-10-01）=====
  默认头像 / 加载中 / 加载失败 三态共用同一套「确定性渐变 + 首字母」视觉：
  - 默认头像：resolveAvatarUrl 兜底生成内联 SVG data URI（零请求、即时可见）
  - 加载中 / 失败：占位层用 avatarAccent(seed) 同算法算出同色渐变 + 同首字母
  → 用户看到的永远是「同一个人的同一个色块」，只是从字母渐变平滑换成真实照片。

  ===== 为什么不用 reka Avatar（2026-10-01）=====
  SSR 产物里 reka-ui 是 external 的（nitro trace 拷贝），运行时加载的 vue 与主 app
  内嵌的 vue 是两个实例 → reka 组件的 provide/inject 跨实例失效 → AvatarRoot 在
  SSR 渲染成空注释节点（客户端是 span）→ 每个头像一处节点级 hydration mismatch
  （首页 25 处）。改为纯原生 span/img 复刻（视觉样式沿用 avatarVariant）：
  - 容器 span 两端都渲染 → 消灭根 mismatch
  - img 两端首帧都渲染（同 src、同 class）→ hydration 一致
  - 占位层 v-if 只看 imgOk（两端首帧都是 null → 都渲染）→ 一致；
    图片就绪是挂载后的普通响应式更新
-->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { avatarVariant } from '~~/components/ui/avatar'
import type { AvatarVariants } from '~~/components/ui/avatar'
import { resolveAvatarUrl, avatarAccent, avatarInitial } from '~~/composables/useResolvedAvatar'
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

// 图片状态：null=未知（首帧/加载中）、true=成功、false=失败。
// 两端首帧都是 null（服务端不触发 load/error），因此占位层在 SSR 与客户端一致渲染。
const imgRef = ref<HTMLImageElement | null>(null)
const imgOk = ref<boolean | null>(null)
const onImgLoad = () => {
  imgOk.value = true
}
const onImgError = () => {
  imgOk.value = false
}

onMounted(() => {
  // 缓存命中时 load 事件早于 hydration 触发会丢失，图片将永远停在 opacity-0。
  // 挂载后主动补判一次 complete，保证「已缓存」与「刚加载」都走同一条收尾路径。
  const el = imgRef.value
  if (el?.complete) imgOk.value = el.naturalWidth > 0
})

const avatarUrl = computed(() => {
  const seedStr = props.seed || props.name || undefined
  return resolveAvatarUrl(
    { seed: seedStr, label: props.name },
    props.resolvedAvatarUrl ?? undefined,
    props.avatar ?? undefined
  )
})

// 占位层文案：与默认头像 SVG 上的字母同源；无名字时只留渐变底（和 SVG 一致）
const placeholderInitial = computed(() => avatarInitial(props.name))

const placeholderStyle = computed(() => {
  const { from, to } = avatarAccent(props.seed || props.name)
  return {
    backgroundImage: `linear-gradient(135deg, ${from}, ${to})`
  }
})

// 只要图片未确认成功就盖住占位（加载中 + 失败）；成功后淡入真实头像。
const showPlaceholder = computed(() => imgOk.value !== true)

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
    fontSize: Math.max(10, Math.round(px * 0.34)) + 'px',
    lineHeight: '1'
  }
})

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
        ref="imgRef"
        :src="avatarUrl"
        :alt="name || 'avatar'"
        :width="numericPx ?? undefined"
        :height="numericPx ?? undefined"
        :class="['h-full w-full rounded-full object-cover transition-opacity duration-200', imgOk === true ? 'opacity-100' : 'opacity-0']"
        loading="lazy"
        decoding="async"
        draggable="false"
        referrerpolicy="no-referrer"
        @load="onImgLoad"
        @error="onImgError"
      >
      <span
        v-if="showPlaceholder"
        class="absolute inset-0 flex items-center justify-center rounded-full font-semibold text-white select-none"
        :style="placeholderStyle"
        aria-hidden="true"
      >{{ placeholderInitial }}</span>
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
