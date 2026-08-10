<!-- ================================================================
     Rosetta Nuxt 入口 App
     - 全局 Header <slot>/<NuxtLayout> + <NuxtPage/>
     - 同时注册客户端颜色模式（防止 FOUC）
     ================================================================ -->
<script setup lang="ts">
/**
 * NO FLASH：首屏脚本（在水合之前执行）—— 从 cookie/localStorage 读取主题
 * 与 @nuxtjs/color-mode 配置中的 `dataValue: 'theme'` 保持一致。
 */
const colorModeClientInit = `(function(){try{
  var s=localStorage.getItem('rosetta-color-mode');
  var m=window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches;
  var t=s==='system'||!s?(m?'one-dark-pro':'one-light'):((s==='dark'||s==='one-dark-pro')?'one-dark-pro':'one-light');
  document.documentElement.setAttribute('data-theme', t);
  document.documentElement.setAttribute('data-lang', localStorage.getItem('lang')||'zh_cn');
}catch(e){}})();`;
</script>

<template>
  <head>
    <!-- Inline script: 必须放在头部最前面，防止 Dark/Light FOUC -->
    <script :children="colorModeClientInit" />
  </head>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>
