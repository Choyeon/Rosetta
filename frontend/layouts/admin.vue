<template>
  <SidebarProvider>
    <AdminSidebar />
    <SidebarInset>
      <AdminHeader :breadcrumbItems="breadcrumbItems" />
      <main class="flex-1 p-4 md:p-6">
        <slot />
      </main>
    </SidebarInset>
  </SidebarProvider>
</template>

<script setup lang="ts">
import { SidebarProvider, SidebarInset } from '~~/components/ui/sidebar'
import { useAuthStore } from '~~/stores/auth'

const authStore = useAuthStore()

const route = useRoute()

const breadcrumbItems = computed(() => {
  const path = route.path
  if (path === '/admin') {
    return [{ label: '仪表盘' }]
  }
  return [{ label: '管理后台', href: '/admin' }, { label: '页面' }]
})

onMounted(() => {
  if (!authStore.isAuthenticated) {
    navigateTo('/login')
  }
})
</script>
