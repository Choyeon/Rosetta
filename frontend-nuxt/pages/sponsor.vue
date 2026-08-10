<script setup lang="ts">
definePageMeta({ layout: "default" });
useHead({ title: "赞助 - Rosetta" });
</script>
<template>
  <div class="space-y-xl">
    <header class="text-center space-y-xs">
      <h1 class="text-3xl font-bold text-neutral-text-primary">支持 Rosetta ♡</h1>
      <p class="text-sm text-neutral-text-tertiary">如果这个项目对你有帮助，欢迎赞助一杯咖啡。</p>
    </header>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-lg max-w-3xl mx-auto">
      <div class="bg-neutral-bg-container rounded-2xl border border-neutral-border-secondary shadow-sm p-xl flex flex-col items-center text-center">
        <div class="w-24 h-24 rounded-xl bg-gradient-to-br from-primary-500/10 to-nebula-blue/20 flex items-center justify-center">
          <Icon name="mdi:wechat" class="w-12 h-12 text-success-500" />
        </div>
        <h2 class="mt-md font-semibold text-neutral-text-primary">微信</h2>
        <p class="mt-xs text-xs text-neutral-text-tertiary">扫码支付 · 任意金额</p>
      </div>
      <div class="bg-neutral-bg-container rounded-2xl border border-neutral-border-secondary shadow-sm p-xl flex flex-col items-center text-center">
        <div class="w-24 h-24 rounded-xl bg-gradient-to-br from-primary-500/10 to-nebula-blue/20 flex items-center justify-center">
          <Icon name="mdi:alipay" class="w-12 h-12 text-primary-500" />
        </div>
        <h2 class="mt-md font-semibold text-neutral-text-primary">支付宝</h2>
        <p class="mt-xs text-xs text-neutral-text-tertiary">扫码支付 · 任意金额</p>
      </div>
    </div>
  </div>
</template>
