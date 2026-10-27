<!--
  Admin 侧栏：内建菜单（config/admin-menu）+ 插件菜单分组的渲染容器。
  硬契约：折叠状态由布局经 v-model:collapsed 受控，本组件不私存；插件项图标只允许
  字符串 iconName → 统一 Puzzle 占位（禁止按名动态 import lucide，包体不可控）；
  mergedMenu 合并插件组时不得修改 adminMenu 原对象（展示期派生，非注册期突变）。
-->
<script setup lang="ts">
import { Globe, Puzzle } from '@lucide/vue'
import { ScrollArea } from '~~/components/ui/scroll-area'
import { Tooltip, TooltipContent, TooltipTrigger } from '~~/components/ui/tooltip'
import { Badge } from '~~/components/ui/badge'
import { adminMenu } from '~~/config/admin-menu'
import { usePluginMenuGroup } from '~~/composables/usePluginMenu'
import { stripLocalePathPrefix } from '~~/lib/rosetta-themes'

const props = defineProps<{
  collapsed?: boolean
  /** <md：侧栏改为抽屉（不占文档流）；由布局按视口判定后传入 */
  mobile?: boolean
  /** mobile=true 时的抽屉开合状态 */
  open?: boolean
}>()

const emit = defineEmits<{
  'update:collapsed': [value: boolean]
}>()

const collapsed = computed({
  get: () => props.collapsed ?? false,
  set: (v: boolean) => emit('update:collapsed', v)
})

/**
 * 抽屉模式下永远按"展开"渲染：手机屏宽只有一列，再收成 72px 图标条
 * 反而让每个入口都要靠 tooltip 猜；折叠态只在桌面断点生效。
 */
const railCollapsed = computed(() => (props.mobile ? false : collapsed.value))

const route = useRoute()

// ── 插件菜单：拉取一次后缓存 ───────────────────────────────────────────
const { group: pluginGroup, load: loadPluginMenu } = usePluginMenuGroup()
onMounted(() => {
  loadPluginMenu().catch(() => { /* 已在 composable 内静默处理 */ })
})

// 在 adminMenu 的 system 组之前插入「插件」分组（仅当有可渲染项时）。
// 保持对原 adminMenu 的无副作用 —— 不修改 config 原对象，只在展示时合并。
const mergedMenu = computed(() => {
  const groups: Array<{
    key: string
    label: string
    items: Array<{
      path: string
      label: string
      icon?: unknown
      iconName?: string
      badge?: string | number
      slug?: string
    }>
  }> = adminMenu.map(g => ({
    key: g.key,
    label: g.label,
    items: g.items.map(it => ({ ...it, icon: it.icon }))
  }))
  const insertIndex = groups.findIndex(g => g.key === 'system')
  const pluginItems = (pluginGroup.value.items ?? []).filter(it => it && it.path && it.label)
  if (pluginItems.length > 0) {
    const extraGroup = {
      key: 'plugins',
      label: pluginGroup.value.label || '插件',
      items: pluginItems.map(it => ({
        path: it.path,
        label: it.label,
        badge: it.badge,
        slug: it.slug,
        // 约定：Sidebar 渲染时优先用 icon（lucide component），
        // 插件提供的是字符串图标名 → 存到 iconName，渲染分支统一走 Puzzle 占位
        // （避免在前端代码中按字符串动态 import lucide 图标，包体不可控）。
        iconName: it.iconName
      }))
    }
    if (insertIndex >= 0) {
      groups.splice(insertIndex, 0, extraGroup)
    } else {
      groups.push(extraGroup)
    }
  }
  return groups
})

/**
 * 高亮判断（与旧逻辑等价，但菜单数据来自 config）：
 *  - /admin 精确匹配
 *  - 其它项：精确匹配，或以 "path/" 开头且紧随段为数字 id（如 posts/42/edit）
 *  - 同前缀下出现兄弟菜单段（如 /admin/users/titles 中的 titles）→ 不激活父项
 */
const isActive = (path: string) => {
  // i18n prefix_except_default：菜单项 path 是默认语言形态（/admin/xxx），
  // route.path 在英/日/繁下带前缀（/en/admin/xxx）。剥前缀后再比对，
  // 保证高亮判定与语言无关。
  const rp = stripLocalePathPrefix(route.path)
  if (path === '/admin') return rp === '/admin' || rp === '/admin/'
  if (rp === path) return true
  const prefix = path + '/'
  if (!rp.startsWith(prefix)) return false

  const rest = rp.slice(prefix.length)
  if (rest === '') return true
  const firstSeg = rest.split('/')[0] ?? ''
  if (firstSeg === '') return true
  if (/^\d+$/.test(firstSeg)) return true

  const isSibling = mergedMenu.value.some(g =>
    g.items.some(it =>
      it.path !== path
      && it.path.startsWith(prefix)
      && it.path.slice(prefix.length).split('/')[0] === firstSeg
    )
  )
  return !isSibling
}

// 渲染前一次性算好每项的 active，避免模板中同一 item 每帧重复调用 isActive 4-5 次。
const renderGroups = computed(() =>
  mergedMenu.value.map(g => ({
    key: g.key,
    label: g.label,
    items: g.items.map(it => ({ ...it, active: isActive(it.path) }))
  }))
)

// 选择图标：内置项的 icon 是 lucide component；插件项默认 Puzzle（拼图）图标。
function resolveIcon(item: { icon?: unknown }) {
  if (item.icon && typeof item.icon !== 'string') return item.icon
  return Puzzle
}
</script>

<template>
  <aside
    v-show="!mobile || open"
    id="admin-sidebar"
    class="admin-sidebar shrink-0 transition-all duration-300 ease-out border-r border-sidebar-border bg-sidebar flex flex-col"
    :class="[
      mobile
        ? 'fixed inset-y-0 left-0 z-50 h-svh w-[272px] shadow-2xl'
        : 'sticky top-0 self-start h-svh',
      mobile ? '' : (railCollapsed ? 'w-[72px]' : 'w-[256px]')
    ]"
  >
    <div
      class="h-16 shrink-0 px-3 md:px-4 flex items-center border-b border-sidebar-border"
      :class="railCollapsed ? 'justify-center px-2' : 'justify-between'"
    >
      <NuxtLink
        to="/admin"
        class="flex items-center gap-2.5 min-w-0"
      >
        <img
          src="/logo/rosetta-primary-icon.png"
          alt="Rosetta Admin"
          class="shrink-0 size-9 rounded-[10px] object-contain drop-shadow-[0_6px_16px_rgba(14,165,233,0.45)]"
        >
        <Transition
          name="fade-collapsed"
          mode="out-in"
        >
          <div
            v-if="!railCollapsed"
            class="flex flex-col leading-tight min-w-0"
          >
            <span class="font-display font-bold text-sidebar-foreground truncate">Rosetta Admin</span>
            <span class="text-[11px] text-muted-foreground truncate">博客管理控制台</span>
          </div>
        </Transition>
      </NuxtLink>
      <!-- 折叠开关已上移到 AdminHeader（navbar 左端）：
           原先「收起在顶 / 展开在底」两颗按钮位置不一致，同一个动作会跳位。 -->
    </div>

    <ScrollArea class="flex-1 py-3 px-2">
      <nav
        class="flex flex-col gap-1"
        aria-label="管理后台导航"
      >
        <template
          v-for="(group, gi) in renderGroups"
          :key="group.key"
        >
          <div
            v-if="!railCollapsed"
            class="px-3 pt-4 pb-1.5 text-[11px] uppercase tracking-[0.12em] text-muted-foreground font-semibold"
            :class="{ 'pt-2': gi === 0 }"
          >
            {{ group.label }}
          </div>
          <div
            v-else
            class="h-2"
          />

          <ul class="flex flex-col gap-0.5">
            <li
              v-for="item in group.items"
              :key="item.path"
            >
              <Tooltip :disabled="!railCollapsed">
                <TooltipTrigger as-child>
                  <NuxtLink
                    :to="item.path"
                    class="sb-item w-full group flex items-center gap-2.5 px-2.5 h-[38px] rounded-lg text-sm font-medium transition-all"
                    :class="[
                      item.active
                        ? 'bg-primary text-primary-foreground shadow-md'
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                      railCollapsed ? 'justify-center px-0' : ''
                    ]"
                    :aria-current="item.active ? 'page' : undefined"
                    :aria-label="item.label"
                    :title="railCollapsed ? item.label : undefined"
                  >
                    <component
                      :is="resolveIcon(item)"
                      class="shrink-0 size-[18px]"
                    />
                    <span
                      v-if="!railCollapsed"
                      class="flex-1 min-w-0 truncate text-left tracking-[0.01em]"
                    >
                      {{ item.label }}
                    </span>
                    <Badge
                      v-if="!railCollapsed && item.badge"
                      variant="outline"
                      class="shrink-0 text-[10px] h-4 px-1.5"
                    >
                      {{ item.badge }}
                    </Badge>
                  </NuxtLink>
                </TooltipTrigger>
                <TooltipContent
                  v-if="railCollapsed"
                  side="right"
                  class="text-xs"
                >
                  {{ item.label }}
                </TooltipContent>
              </Tooltip>
            </li>
          </ul>
        </template>
      </nav>
    </ScrollArea>

    <div class="shrink-0 border-t border-sidebar-border p-2 flex items-center gap-1">
      <NuxtLink
        to="/"
        target="_blank"
        class="flex-1 min-w-0 flex items-center gap-2 h-9 px-2 rounded-[10px] text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors"
        :class="railCollapsed ? 'justify-center px-0' : ''"
        :title="railCollapsed ? '返回前台' : undefined"
      >
        <Globe class="shrink-0 size-[18px] text-muted-foreground" />
        <span
          v-if="!railCollapsed"
          class="text-sm truncate"
        >返回前台</span>
      </NuxtLink>
    </div>
  </aside>
</template>

<style scoped>
.fade-collapsed-enter-active,
.fade-collapsed-leave-active {
  transition: opacity 240ms cubic-bezier(0.22, 1, 0.36, 1), transform 240ms cubic-bezier(0.22, 1, 0.36, 1);
}
.fade-collapsed-enter-from,
.fade-collapsed-leave-to {
  opacity: 0;
  transform: translateX(-6px);
}
</style>
