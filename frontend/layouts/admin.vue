<!--
  后台布局骨架：侧栏 + 顶栏 + 主内容容器；/admin 主题解耦四层防御中的"布局层"。
  硬契约：onMounted 与 watch(route.path) 双节点必须 clearThemeVisual + 写
  html[data-layout-scope="admin"]（SPA 从前台切回时旧 data-theme 会残留）；
  sidebarCollapsed 由本布局独占（AdminHeader/Sidebar 只透传事件，不得私存副本）；
  <main> 已带 p-4 md:p-6，页面根容器禁止再写 padding；TooltipProvider 归 app.vue 单例，此处禁止嵌套。
-->
<script setup lang="ts">
/* eslint-disable */
import AdminSidebar from '~~/components/admin/AdminSidebar.vue'
import AdminHeader from '~~/components/admin/AdminHeader.vue'
import { useMediaQuery } from '@vueuse/core'
import { useTheme } from '~~/composables/useTheme'
import { useAuthStore } from '~~/stores/auth'
import { useFrontendTheme } from '~~/composables/useFrontendTheme'

useTheme()
// 纵深防御：robots.txt 的 Disallow: /admin/ 是主闸门，这里再自带一份 noindex，
// 免得将来有人调整 robots.txt 就把后台整层暴露进索引。
useNoindexPage()
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
const mobileNavOpen = ref(false)

/**
 * 断点用 matchMedia 订阅，不再只 onMounted 读一次 innerWidth：
 * 转屏 / 拖窗口后侧栏形态必须跟着变，否则 768–1280px 会停在"自动收起且没有合适开关"的状态。
 */
const isDesktopNav = useMediaQuery('(min-width: 768px)')
const isWideNav = useMediaQuery('(min-width: 1280px)')

// xl 以下默认收成图标栏（老口径保留），xl 及以上展开完整菜单。
watch(isWideNav, (wide) => { sidebarCollapsed.value = !wide }, { immediate: true })
// 回到桌面宽度时抽屉必须关掉：否则遮罩会留在宽屏上挡住主内容。
watch(isDesktopNav, (desktop) => { if (desktop) mobileNavOpen.value = false })
// 抽屉里点任意菜单后自动收起（移动端导航完还要手动点遮罩关闭是常见的漏做项）。
watch(() => route.path, () => { mobileNavOpen.value = false })

/** 顶栏那颗开关：桌面切折叠，<md 切抽屉开合（开关仍然唯一，位置不跳）。 */
function onToggleSidebar() {
  if (isDesktopNav.value) sidebarCollapsed.value = !sidebarCollapsed.value
  else mobileNavOpen.value = !mobileNavOpen.value
}

/** 给 AdminHeader 的图标语义：抽屉打开时等同于"展开"，关闭时等同于"收起"。 */
const sidebarNavCollapsed = computed(() =>
  isDesktopNav.value ? sidebarCollapsed.value : !mobileNavOpen.value
)
</script>

<template>
  <div
    class="admin-shell min-h-screen bg-background font-sans antialiased flex"
    :class="{ 'admin-collapsed': sidebarCollapsed }"
  >
    <AdminSidebar
      v-model:collapsed="sidebarCollapsed"
      :mobile="!isDesktopNav"
      :open="mobileNavOpen"
    />
    <!-- 抽屉遮罩：只在 <md 且抽屉打开时存在，点击即关（不用额外的关闭按钮，避免顶栏出现第二个开关） -->
    <div
      v-if="!isDesktopNav && mobileNavOpen"
      class="fixed inset-0 z-40 bg-black/45 backdrop-blur-sm md:hidden"
      aria-hidden="true"
      @click="mobileNavOpen = false"
    />
    <div class="admin-main flex-1 flex flex-col min-w-0">
      <AdminHeader
        :sidebar-collapsed="sidebarNavCollapsed"
        @toggle-sidebar="onToggleSidebar"
      />
      <main
        id="main"
        class="flex-1 p-4 md:p-6 overflow-x-clip"
        role="main"
        aria-label="Admin main content"
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
