<template>
  <div class="p-6">
    <PluginManager />
  </div>
</template>

<script setup lang="ts">
import PluginManager from '~~/components/admin/plugins/PluginManager.vue'

definePageMeta({ ssr: false, layout: 'admin' })
</script>
