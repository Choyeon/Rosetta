<script setup lang="ts">
import { computed } from 'vue'
import * as LucideIcons from '@lucide/vue'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import type { AvatarVariants } from '~~/components/ui/avatar'
import { resolveAvatarUrl } from '~~/composables/useResolvedAvatar'
import { resolveTitleIcon } from '~~/composables/titlePresets'
import type { AdminUserTitle } from '~~/composables/useAdminManage'

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

const resolvedIcon = computed(() => resolveTitleIcon(props.title?.icon))
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
    <Avatar
      :size="avatarVariantSize"
      shape="circle"
      :class="['ring-1 ring-border/60 rounded-full']"
      :style="avatarStyle"
    >
      <AvatarImage
        v-if="avatarUrl"
        :src="avatarUrl"
        :alt="name || 'avatar'"
        class="rounded-full"
      />
      <AvatarFallback
        :class="['bg-primary/10 text-primary font-semibold rounded-full', fallbackClass]"
      >
        {{ fallbackText }}
      </AvatarFallback>
    </Avatar>

    <span
      v-if="showTitle && title && resolvedIcon.type !== 'empty'"
      class="absolute -bottom-0.5 -right-0.5 z-10 flex items-center justify-center rounded-full border-2 border-background"
      :style="{
        width: badgeSize + 'px',
        height: badgeSize + 'px',
        backgroundColor: titleColor,
        color: '#fff'
      }"
      :title="titleDisplayName"
    >
      <component
        :is="(LucideIcons as Record<string, unknown>)[resolvedIcon.value]"
        v-if="resolvedIcon.type === 'lucide'"
        class="w-[60%] h-[60%]"
      />
      <span
        v-else-if="resolvedIcon.type === 'emoji'"
        style="font-size:60%"
      >{{ resolvedIcon.value }}</span>
      <span
        v-else-if="resolvedIcon.type === 'svg'"
        class="w-full h-full flex items-center justify-center"
        v-html="resolvedIcon.value"
      />
    </span>
  </div>
</template>
