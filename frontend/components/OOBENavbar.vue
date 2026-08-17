<script setup lang="ts">
import LocaleSwitcher from '~~/components/LocaleSwitcher.vue'
import ThemeToggle from '~~/components/ThemeToggle.vue'
</script>

<template>
  <header class="sticky top-0 z-40 w-full h-16 border-b bg-background/80 backdrop-blur">
    <div class="container mx-auto flex h-full items-center justify-between px-4 lg:px-8">
      <NuxtLink
        to="/"
        class="inline-flex items-center gap-2 font-display text-xl font-bold tracking-tight"
      >
        <img
          src="/logo/rosetta-primary-icon.png"
          alt="Rosetta"
          class="size-7"
        >
        <span>Rosetta</span>
      </NuxtLink>

      <div class="flex items-center gap-1">
        <LocaleSwitcher />
        <ThemeToggle />
      </div>
    </div>
  </header>
</template>
