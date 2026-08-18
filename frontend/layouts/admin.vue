<script setup lang="ts">
/* eslint-disable */
import { TooltipProvider } from '~~/components/ui/tooltip'
import AdminSidebar from '~~/components/admin/AdminSidebar.vue'
import AdminHeader from '~~/components/admin/AdminHeader.vue'
import { useTheme } from '~~/composables/useTheme'
import { useAuthStore } from '~~/stores/auth'

useTheme()
const authStore = useAuthStore()

onMounted(() => {
  if (!import.meta.client) return
  authStore.initialize()
})

const sidebarCollapsed = ref(false)
</script>

<template>
  <div
    class="admin-shell min-h-screen bg-background font-sans antialiased flex"
    :class="{ 'admin-collapsed': sidebarCollapsed }"
  >
    <TooltipProvider :delay-duration="0">
      <AdminSidebar
        v-model:collapsed="sidebarCollapsed"
      />
      <div class="admin-main flex-1 flex flex-col min-w-0">
        <AdminHeader :sidebar-collapsed="sidebarCollapsed" />
        <main
          id="admin-content"
          class="flex-1 p-4 md:p-6 overflow-x-hidden"
        >
          <Transition
            name="page-fade"
            mode="out-in"
          >
            <NuxtPage />
          </Transition>
        </main>
      </div>
    </TooltipProvider>
  </div>
</template>

<style scoped>
.admin-shell {
  background:
    radial-gradient(1200px 500px at -10% -5%, hsl(var(--primary) / 0.06), transparent 55%),
    radial-gradient(900px 400px at 110% 10%, hsl(var(--info) / 0.05), transparent 55%);
}
</style>
