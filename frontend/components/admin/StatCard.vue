<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
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

const gradients: Record<string, string> = {
  primary: 'linear-gradient(135deg,#0EA5E9 0%,#0284C7 100%)',
  info: 'linear-gradient(135deg,#3B82F6 0%,#2563EB 100%)',
  success: 'linear-gradient(135deg,#10B981 0%,#059669 100%)',
  warning: 'linear-gradient(135deg,#38BDF8 0%,#0EA5E9 100%)',
  error: 'linear-gradient(135deg,#EF4444 0%,#DC2626 100%)',
  ochre: 'linear-gradient(135deg,#EA580C 0%,#C2410C 100%)',
  sage: 'linear-gradient(135deg,#14B8A6 0%,#0D9488 100%)',
  indigo: 'linear-gradient(135deg,#6366F1 0%,#4F46E5 100%)',
  walnut: 'linear-gradient(135deg,#A16207 0%,#854D0E 100%)'
}

const lightPills: Record<string, string> = {
  primary: 'bg-[#FFF7ED] text-[#9A3412]',
  info: 'bg-[#EFF6FF] text-[#1E40AF]',
  success: 'bg-[#ECFDF5] text-[#065F46]',
  warning: 'bg-[#E0F2FE] text-[#0369A1]',
  error: 'bg-[#FEF2F2] text-[#991B1B]',
  ochre: 'bg-[#FFF7ED] text-[#7C2D12]',
  sage: 'bg-[#F0FDFA] text-[#134E4A]',
  indigo: 'bg-[#EEF2FF] text-[#3730A3]',
  walnut: 'bg-[#FEF3C7] text-[#075985]'
}
const darkPills: Record<string, string> = {
  primary: 'bg-[#075985]/40 text-[#BAE6FD]',
  info: 'bg-[#1E3A8A]/40 text-[#BFDBFE]',
  success: 'bg-[#064E3B]/40 text-[#A7F3D0]',
  warning: 'bg-[#075985]/40 text-[#BAE6FD]',
  error: 'bg-[#7F1D1D]/40 text-[#FECACA]',
  ochre: 'bg-[#7C2D12]/40 text-[#FED7AA]',
  sage: 'bg-[#134E4A]/40 text-[#99F6E4]',
  indigo: 'bg-[#312E81]/40 text-[#C7D2FE]',
  walnut: 'bg-[#075985]/40 text-[#BAE6FD]'
}

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
    class="stat-card relative overflow-hidden rounded-[12px] border border-border bg-card p-5 transition-all duration-200 hover:shadow-[0_10px_30px_-14px_rgba(0,0,0,0.15)] hover:-translate-y-0.5"
    :class="{ 'opacity-60 pointer-events-none': loading }"
  >
    <!-- 装饰光晕 -->
    <div
      aria-hidden="true"
      class="pointer-events-none absolute -top-10 -right-10 size-36 rounded-full opacity-[0.08] blur-2xl"
      :style="{ background: gradients[accent] }"
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
            class="inline-flex items-center gap-1 rounded-full px-2 h-5 text-[11px] font-semibold dark:hidden"
            :class="[
              trend.direction === 'up' ? lightPills[accent]
              : trend.direction === 'down' ? 'bg-[#FEF2F2] text-[#991B1B]'
                : 'bg-muted text-muted-foreground'
            ]"
          >
            <component
              :is="TrendIcon"
              class="size-3"
            />
            <span>{{ trend.value }}</span>
          </div>
          <div
            v-if="trend && !loading"
            class="hidden dark:inline-flex items-center gap-1 rounded-full px-2 h-5 text-[11px] font-semibold"
            :class="[
              trend.direction === 'up' ? darkPills[accent]
              : trend.direction === 'down' ? 'bg-[#7F1D1D]/40 text-[#FECACA]'
                : 'bg-muted text-muted-foreground'
            ]"
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
        :style="{ background: gradients[accent] }"
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
