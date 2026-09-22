<template>
  <ThemeManager />
</template>

<script setup lang="ts">
import ThemeManager from '~~/components/admin/themes/ThemeManager.vue'

definePageMeta({ ssr: false, layout: 'admin' })
</script>
