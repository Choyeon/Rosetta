<!--
  主题管理页壳：全部状态与逻辑由 components/admin/themes/ThemeManager.vue 持有，本文件仅负责挂载。
  契约：definePageMeta 逐页声明——壳页也必须写 ssr:false + layout:'admin'，否则丢失后台外壳并让客户端组件走 SSR。
-->
<template>
  <ThemeManager />
</template>

<script setup lang="ts">
import ThemeManager from '~~/components/admin/themes/ThemeManager.vue'

definePageMeta({ ssr: false, layout: 'admin' })
</script>
