<!-- ==============================================================
     默认布局（前台 Layout）
     对应 Astro：Layout.astro + MainGridLayout.astro
     - Header / SideBar / Footer 插槽占位
     - 主槽位 <slot /> = <NuxtPage /> 渲染产物
     ============================================================== -->
<script setup lang="ts">
interface Props {
  /** 隐藏侧栏（用于登录/OOBE/全屏页） */
  hideSidebar?: boolean;
  /** 隐藏 Footer */
  hideFooter?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  hideSidebar: false,
  hideFooter: false,
});
</script>

<template>
  <div
    class="min-h-screen flex flex-col bg-neutral-bg-layout text-neutral-text-primary"
  >
    <!-- ===== Header ===== -->
    <AppHeader />

    <!-- ===== Main Grid ===== -->
    <div class="flex-1 w-full">
      <div
        class="max-w-7xl mx-auto px-4 sm:px-6 xl:px-8 py-lg md:py-xl grid gap-xl"
        :class="[
          props.hideSidebar ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px] xl:grid-cols-[minmax(0,1fr)_340px]'
        ]"
      >
        <!-- 主内容槽 -->
        <main
          id="swup-container"
          class="min-w-0"
          role="main"
          aria-label="主内容区"
        >
          <slot />
        </main>

        <!-- 侧栏（hideSidebar=false 时显示） -->
        <aside
          v-if="!props.hideSidebar"
          class="hidden lg:block min-w-0 h-fit space-y-lg lg:sticky lg:top-20"
          aria-label="侧边栏"
        >
          <SidebarProfileCard />
          <SidebarTocCard />
          <SidebarTagCloudCard />
        </aside>
      </div>
    </div>

    <!-- ===== Footer ===== -->
    <AppFooter v-if="!props.hideFooter" />
  </div>
</template>
