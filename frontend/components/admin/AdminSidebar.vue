<script setup lang="ts">
import { ChevronLeft, ChevronRight, Globe } from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { ScrollArea } from '~~/components/ui/scroll-area'
import { Tooltip, TooltipContent, TooltipTrigger } from '~~/components/ui/tooltip'
import { Badge } from '~~/components/ui/badge'
import { adminMenu } from '~~/config/admin-menu'

const props = defineProps<{
  collapsed?: boolean
}>()

const emit = defineEmits<{
  'update:collapsed': [value: boolean]
}>()

const collapsed = computed({
  get: () => props.collapsed ?? false,
  set: (v: boolean) => emit('update:collapsed', v)
})

const route = useRoute()

/**
 * 高亮判断（与旧逻辑等价，但菜单数据来自 config）：
 *  - /admin 精确匹配
 *  - 其它项：精确匹配，或以 "path/" 开头且紧随段为数字 id（如 posts/42/edit）
 *  - 同前缀下出现兄弟菜单段（如 /admin/users/titles 中的 titles）→ 不激活父项
 */
const isActive = (path: string) => {
  const rp = route.path
  if (path === '/admin') return rp === '/admin' || rp === '/admin/'
  if (rp === path) return true
  const prefix = path + '/'
  if (!rp.startsWith(prefix)) return false

  const rest = rp.slice(prefix.length)
  if (rest === '') return true
  const firstSeg = rest.split('/')[0] ?? ''
  if (firstSeg === '') return true
  if (/^\d+$/.test(firstSeg)) return true

  const isSibling = adminMenu.some(g =>
    g.items.some(it =>
      it.path !== path &&
      it.path.startsWith(prefix) &&
      it.path.slice(prefix.length).split('/')[0] === firstSeg
    )
  )
  return !isSibling
}

const go = (path: string) => navigateTo(path)
</script>

<template>
  <aside
    class="admin-sidebar shrink-0 transition-all duration-300 ease-out border-r border-sidebar-border bg-sidebar flex flex-col"
    :class="collapsed ? 'w-[72px]' : 'w-[256px]'"
  >
    <div
      class="h-16 shrink-0 px-3 md:px-4 flex items-center justify-between border-b border-sidebar-border"
    >
      <NuxtLink
        to="/admin"
        class="flex items-center gap-2.5 min-w-0"
      >
        <div
          class="shrink-0 size-9 rounded-[10px] flex items-center justify-center font-bold text-white shadow-[0_6px_16px_-6px_hsl(var(--primary)/0.6)]"
          style="background: linear-gradient(135deg,#0EA5E9 0%,#0284C7 60%,#0369A1 100%);"
        >
          <span class="font-display text-lg tracking-tight">R</span>
        </div>
        <Transition
          name="fade-collapsed"
          mode="out-in"
        >
          <div
            v-if="!collapsed"
            class="flex flex-col leading-tight min-w-0"
          >
            <span class="font-display font-bold text-sidebar-foreground truncate">Rosetta Admin</span>
            <span class="text-[11px] text-muted-foreground/80 truncate">博客管理控制台</span>
          </div>
        </Transition>
      </NuxtLink>

      <Button
        v-if="!collapsed"
        variant="ghost"
        size="icon"
        class="ml-1 shrink-0 size-8 text-muted-foreground hover:text-sidebar-foreground"
        @click="collapsed = true"
      >
        <ChevronLeft class="size-4" />
      </Button>
    </div>

    <ScrollArea class="flex-1 py-3 px-2">
      <nav class="flex flex-col gap-1">
        <template
          v-for="(group, gi) in adminMenu"
          :key="group.key"
        >
          <div
            v-if="!collapsed"
            class="px-3 pt-4 pb-1.5 text-[11px] uppercase tracking-[0.12em] text-muted-foreground/70 font-semibold"
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
              <Tooltip :disabled="!collapsed">
                <TooltipTrigger as-child>
                  <button
                    type="button"
                    class="sb-item w-full group flex items-center gap-2.5 px-2.5 h-[38px] rounded-[11px] relative isolate transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] will-change-transform"
                    :class="[
                      isActive(item.path)
                        ? 'sb-item-active text-[hsl(var(--sidebar-active-foreground,var(--primary)))] font-semibold'
                        : 'sb-item-idle text-sidebar-foreground/75 hover:text-sidebar-foreground'
                    ]"
                    @click="go(item.path)"
                  >
                    <span
                      class="absolute inset-0 rounded-[11px] -z-10 transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]"
                      :class="[
                        isActive(item.path)
                          ? 'sb-bg-active'
                          : 'opacity-0 group-hover:opacity-100 sb-bg-hover'
                      ]"
                      aria-hidden="true"
                    />
                    <component
                      :is="item.icon"
                      class="shrink-0 size-[18px] transition-colors duration-300"
                      :class="isActive(item.path) ? 'sb-icon-active' : 'text-muted-foreground group-hover:text-sidebar-foreground'"
                    />
                    <span
                      v-if="!collapsed"
                      class="flex-1 min-w-0 text-[13.5px] truncate text-left tracking-[0.01em]"
                    >
                      {{ item.label }}
                    </span>
                    <ChevronRight
                      v-if="isActive(item.path) && !collapsed"
                      class="shrink-0 size-3.5 opacity-70 sb-chevron"
                      aria-hidden="true"
                    />
                    <Badge
                      v-if="!collapsed && item.badge"
                      variant="outline"
                      class="shrink-0 text-[10px] h-4 px-1.5"
                    >
                      {{ item.badge }}
                    </Badge>
                  </button>
                </TooltipTrigger>
                <TooltipContent
                  v-if="collapsed"
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
      >
        <Globe class="shrink-0 size-[18px] text-muted-foreground" />
        <span
          v-if="!collapsed"
          class="text-sm truncate"
        >返回前台</span>
      </NuxtLink>
      <Button
        v-if="collapsed"
        variant="ghost"
        size="icon"
        class="shrink-0 size-8 text-muted-foreground hover:text-sidebar-foreground"
        @click="collapsed = false"
      >
        <ChevronRight class="size-4" />
      </Button>
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

.sb-bg-active {
  background: hsl(var(--primary) / 0.12);
  box-shadow:
    inset 0 0 0 1px hsl(var(--primary) / 0.22);
}
.sb-bg-hover {
  background: hsl(var(--sidebar-accent, var(--accent)) / 0.9);
  box-shadow:
    inset 0 0 0 1px hsl(var(--foreground) / 0.05);
}
@media (prefers-color-scheme: dark) {
  .sb-bg-active {
    background: hsl(var(--primary) / 0.18);
    box-shadow:
      inset 0 0 0 1px hsl(var(--primary) / 0.30);
  }
  .sb-bg-hover {
    background: hsl(var(--sidebar-accent) / 0.85);
    box-shadow:
      inset 0 0 0 1px hsl(var(--foreground) / 0.06);
  }
}
.sb-item-idle:hover,
.sb-item-active {
  transform: none;
}
.sb-icon-active {
  color: hsl(var(--primary));
}
.sb-chevron {
  color: hsl(var(--primary) / 0.7);
  opacity: 0.7;
}
</style>
