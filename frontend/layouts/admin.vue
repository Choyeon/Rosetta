<template>
  <SidebarProvider>
    <AdminSidebar />
    <SidebarInset>
      <AdminHeader :breadcrumb-items="breadcrumbItems" />
      <main class="flex-1 p-4 md:p-6">
        <slot />
      </main>
    </SidebarInset>
  </SidebarProvider>
</template>

<script setup lang="ts">
import { SidebarProvider, SidebarInset } from '~~/components/ui/sidebar'
import { useAuthStore } from '~~/stores/auth'
import { useI18n } from 'vue-i18n'

const authStore = useAuthStore()
const { t } = useI18n()

const route = useRoute()

const breadcrumbItems = computed(() => {
  const path = route.path
  if (path === '/admin') {
    return [{ label: t('admin.dashboard.title') }]
  }

  const root = { label: t('nav.admin'), href: '/admin' }

  if (path === '/admin/posts') return [root, { label: t('admin.posts.title') }]
  if (path === '/admin/posts/new') return [root, { label: t('admin.posts.title'), href: '/admin/posts' }, { label: t('admin.posts.newTitle') }]
  if (/^\/admin\/posts\/\d+\/edit$/.test(path)) return [root, { label: t('admin.posts.title'), href: '/admin/posts' }, { label: t('admin.posts.editTitle') }]
  if (path === '/admin/comments') return [root, { label: t('admin.comments.title') }]
  if (path === '/admin/users') return [root, { label: t('admin.users.title') }]
  if (path === '/admin/categories') return [root, { label: t('admin.categories.title') }]
  if (path === '/admin/settings') return [root, { label: t('admin.settings.title') }]

  return [root]
})

onMounted(() => {
  if (!authStore.isAuthenticated) {
    navigateTo('/login')
  }
})
</script>
