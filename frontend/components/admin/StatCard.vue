<script setup lang="ts">
/* eslint-disable */
import type { Component } from 'vue'
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Eye,
  Users,
  MessageSquare,
  Image,
  FileText,
  Gauge,
  Archive,
  ClipboardList,
  Database,
  Bell,
  Activity,
  Award,
  Settings,
  Globe,
  PlugZap,
  Search,
  ArrowUpDown
} from '@lucide/vue'

const props = withDefaults(defineProps<{
  title: string
  value: string | number
  icon?: Component | string
  /** 语义色，对应不同的渐变背景 */
  accent?: 'primary' | 'info' | 'success' | 'warning' | 'error' | 'ochre' | 'sage' | 'indigo' | 'walnut'
  subValue?: string
  trend?: {
    direction: 'up' | 'down' | 'flat'
    value: string
    hint?: string
  }
  hint?: string
  loading?: boolean
  /** 右下角按钮文字，点击 emit('action') */
  actionLabel?: string
}>(), {
  accent: 'primary',
  icon: Eye,
  loading: false
})

const emit = defineEmits<{
  action: []
}>()

// 语义色 → CSS 变量映射（统一走主题变量，浅色/深色自动适配）
const accentVar: Record<string, string> = {
  primary: 'var(--primary)',
  info: 'var(--info)',
  success: 'var(--success)',
  warning: 'var(--warning)',
  error: 'var(--destructive)',
  ochre: 'var(--warning)',
  sage: 'var(--success)',
  indigo: 'var(--primary)',
  walnut: 'var(--warning)'
}

// 装饰光晕渐变（用 hsl() 包裹 CSS 变量，自动适配明暗主题）
const gradient = computed<string>(() => {
  const v = accentVar[props.accent] || 'var(--primary)'
  return `linear-gradient(135deg, hsl(${v}) 0%, hsl(${v} / 0.6) 100%)`
})

// trend pill 样式：统一用 bg-{color}/10 + text-{color}，深色自动适配
const pillClasses = computed(() => {
  if (!props.trend) return ''
  if (props.trend.direction === 'flat') return 'bg-muted text-muted-foreground'
  if (props.trend.direction === 'down') return 'bg-destructive/10 text-destructive'
  // up：用语义色
  return `bg-[hsl(${accentVar[props.accent] || 'var(--primary)'})]/10 text-[hsl(${accentVar[props.accent] || 'var(--primary)'})]`
})

const IconComponent = computed<Component>(() => {
  if (typeof props.icon === 'string') {
    const map: Record<string, Component> = {
      Eye, Users, MessageSquare, Image, FileText, Gauge, Archive,
      ClipboardList, Database, Bell, Activity, Award, Settings, Globe,
      PlugZap, Search, ArrowUpDown
    }
    return map[props.icon] || Eye
  }
  return props.icon || Eye
})

const TrendIcon = computed(() => {
  if (!props.trend) return null
  if (props.trend.direction === 'up') return TrendingUp
  if (props.trend.direction === 'down') return TrendingDown
  return Minus
})
</script>

<template>
  <div
    class="card-surface lift-hover relative overflow-hidden p-5"
    :class="{ 'opacity-60 pointer-events-none': loading }"
  >
    <!-- 装饰光晕 -->
    <div
      aria-hidden="true"
      class="pointer-events-none absolute -top-10 -right-10 size-36 rounded-full opacity-[0.08] blur-2xl"
      :style="{ background: gradient }"
    />
    <div class="relative flex items-start justify-between gap-3">
      <div class="min-w-0 flex-1">
        <p class="text-[13px] font-medium text-muted-foreground truncate">
          {{ title }}
        </p>
        <div class="mt-2 flex items-end gap-2 min-w-0">
          <span
            v-if="!loading"
            class="font-display font-bold tracking-tight text-2xl md:text-3xl text-foreground truncate"
          >
            {{ value }}
          </span>
          <span
            v-else
            class="h-8 w-24 md:w-32 rounded-md bg-muted animate-pulse"
          />
          <span
            v-if="!loading && subValue"
            class="pb-1 text-xs text-muted-foreground truncate"
          >
            {{ subValue }}
          </span>
        </div>

        <!-- trend + hint -->
        <div class="mt-3 flex items-center gap-2 flex-wrap">
          <div
            v-if="trend && !loading"
            class="inline-flex items-center gap-1 rounded-full px-2 h-5 text-[11px] font-semibold"
            :class="pillClasses"
          >
            <component
              :is="TrendIcon"
              class="size-3"
            />
            <span>{{ trend.value }}</span>
          </div>
          <span
            v-if="hint && !loading"
            class="text-[11px] text-muted-foreground/80"
          >
            {{ hint }}
          </span>
        </div>

        <!-- 操作按钮 -->
        <button
          v-if="actionLabel && !loading"
          type="button"
          class="mt-4 inline-flex items-center text-xs font-medium text-primary hover:text-primary/80 hover:underline underline-offset-4"
          @click="emit('action')"
        >
          {{ actionLabel }}
          <component
            :is="ArrowUpDown"
            class="ml-1 size-3 rotate-[-90deg]"
          />
        </button>
      </div>

      <!-- 图标容器 -->
      <div
        aria-hidden="true"
        class="shrink-0 relative size-11 rounded-[12px] text-white flex items-center justify-center shadow-[0_8px_20px_-6px_rgba(0,0,0,0.25)]"
        :style="{ background: gradient }"
      >
        <component
          :is="IconComponent"
          v-if="!loading"
          class="size-[22px]"
        />
        <div
          v-else
          class="size-5 rounded-full bg-white/20 animate-pulse"
        />
      </div>
    </div>
  </div>
</template>
