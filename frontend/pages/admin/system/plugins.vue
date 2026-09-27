<!--
  插件管理页壳：全部状态与逻辑由 components/admin/plugins/PluginManager.vue 持有，本文件仅负责挂载。
  契约：definePageMeta 逐页声明——壳页也必须写 ssr:false + layout:'admin'，否则丢失后台外壳并让客户端组件走 SSR。
-->
<template>
  <PluginManager />
</template>

<script setup lang="ts">
import PluginManager from '~~/components/admin/plugins/PluginManager.vue'

definePageMeta({ ssr: false, layout: 'admin' })
</script>
