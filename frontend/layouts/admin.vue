<script setup lang="ts">
/* eslint-disable */
import AdminSidebar from '~~/components/admin/AdminSidebar.vue'
import AdminHeader from '~~/components/admin/AdminHeader.vue'
import { useTheme } from '~~/composables/useTheme'
import { useAuthStore } from '~~/stores/auth'
import { useFrontendTheme } from '~~/composables/useFrontendTheme'

useTheme()
const authStore = useAuthStore()
const ft = useFrontendTheme()
const route = useRoute()

/**
 * 后台布局防御：
 *   1. 清除所有 Rosetta 前端主题写在 <html> 上的 data-* / theme-* class / 主题 style.css link
 *   2. 把 html[data-layout-scope]="admin" 写进去，作为未来主题 CSS 的额外守卫
 *
 * 触发时机：onMounted（首次进入 /admin 直接刷新）+ 每次 route.path 变化
 * （SPA 导航从 / 前台切回后台时，旧 data-theme 属性会残留 —— 必须再次清理）。
 */
const sanitizeAdminShell = () => {
  if (!import.meta.client) return
  // 清理 Rosetta 前端主题视觉层（color tokens / class / data-attr / <link>）
  ft.clearThemeVisual()
  // 写入 layout scope（防御：未来主题 CSS 可通过 :not([data-layout-scope=admin]) 排除）
  document.documentElement.setAttribute('data-layout-scope', 'admin')
}
onMounted(() => {
  if (!import.meta.client) return
  authStore.initialize()
  sanitizeAdminShell()
})
// SPA 路由切换到后台任意子路径时，也要清理从前台带过来的 data-theme 等。
watch(() => route.path, () => sanitizeAdminShell(), { flush: 'post' })

// TooltipProvider 已在 app.vue 全局提供，这里不再嵌套：
//   1. 唯一 Provider 保证首渲染层级字节级一致
//   2. AdminHeader / AdminSidebar 中的 Tooltip 仍能正确注入
const sidebarCollapsed = ref(false)
</script>

<template>
  <div
    class="admin-shell min-h-screen bg-background font-sans antialiased flex"
    :class="{ 'admin-collapsed': sidebarCollapsed }"
  >
    <AdminSidebar
      v-model:collapsed="sidebarCollapsed"
    />
    <div class="admin-main flex-1 flex flex-col min-w-0">
      <AdminHeader :sidebar-collapsed="sidebarCollapsed" />
      <main
        id="admin-content"
        class="flex-1 p-4 md:p-6 overflow-x-hidden"
      >
        <!-- 页面过渡统一走 nuxt.config 中的 app.pageTransition（Nuxt 原生机制）。
             不要手动包裹 <Transition>：异步页面 + out-in 模式会产生非元素根节点，
             导致 Vue 抛出 "Component inside <Transition> renders non-element root node
             that cannot be animated." 警告。 -->
        <NuxtPage />
      </main>
    </div>
  </div>
</template>

<style scoped>
.admin-shell {
  background:
    radial-gradient(1200px 500px at -10% -5%, hsl(var(--primary) / 0.06), transparent 55%),
    radial-gradient(900px 400px at 110% 10%, hsl(var(--info) / 0.05), transparent 55%);
}
</style>
