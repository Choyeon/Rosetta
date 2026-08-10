<!--
  AppHeader — 对应 Astro src/components/Header.astro + Layout.astro Header
  Nav links（首页/文章/分类/标签/归档/关于/功能菜单） + 搜索 + ColorSchemeToggle + 后台入口
-->
<script setup lang="ts">
import { Icon } from "#components";
const navs = [
  { to: "/", label: "首页" },
  { to: "/posts", label: "文章" },
  { to: "/categories", label: "分类" },
  { to: "/tags", label: "标签" },
  { to: "/archive", label: "归档" },
  { to: "/about", label: "关于" },
];
const featureMenu = [
  { to: "/dynamic", label: "动态", icon: "material-symbols:bolt-rounded" },
  { to: "/bangumi", label: "番剧", icon: "material-symbols:movie-creation-rounded" },
  { to: "/anime", label: "动漫", icon: "material-symbols:live-tv-rounded" },
  { to: "/gallery", label: "相册", icon: "material-symbols:photo-library-rounded" },
  { to: "/friends", label: "友情链接", icon: "material-symbols:link-rounded" },
];
const openMobile = ref(false);
const openFeature = ref(false);
</script>

<template>
  <header
    class="sticky top-0 z-sticky backdrop-blur-sm bg-neutral-bg-container/90 border-b border-neutral-border-secondary shadow-xs"
  >
    <nav
      class="max-w-7xl mx-auto px-4 sm:px-6 xl:px-8 h-16 flex items-center justify-between gap-3"
      aria-label="主导航"
    >
      <AppLogo :show-tagline="true" size="md" clickable />

      <!-- Desktop Nav -->
      <ul class="hidden md:flex items-center gap-0.5">
        <li v-for="n in navs" :key="n.to">
          <NuxtLink
            :to="n.to"
            class="px-3 py-2 rounded-md text-sm font-medium text-neutral-text-secondary hover:text-neutral-text-primary hover:bg-neutral-fill-hover transition-colors duration-fast ease-out"
            active-class="!text-primary-500 !bg-primary-500/10"
          >{{ n.label }}</NuxtLink>
        </li>
        <li class="relative">
          <button
            type="button"
            class="px-3 py-2 rounded-md text-sm font-medium text-neutral-text-secondary hover:text-neutral-text-primary hover:bg-neutral-fill-hover inline-flex items-center gap-1 transition-colors duration-fast ease-out"
            @click="openFeature = !openFeature"
            @blur="setTimeout(() => openFeature = false, 120)"
          >
            功能
            <svg class="w-3.5 h-3.5 transition-transform duration-fast" :class="openFeature ? 'rotate-180' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
          </button>
          <Transition name="dropdown">
            <ul
              v-show="openFeature"
              class="absolute right-0 top-full mt-1 w-44 rounded-xl shadow-lg border border-neutral-border-secondary bg-neutral-bg-container py-1 z-popover"
            >
              <li v-for="m in featureMenu" :key="m.to">
                <NuxtLink
                  :to="m.to"
                  class="flex items-center gap-2 px-3 py-2 text-sm text-neutral-text-secondary hover:bg-neutral-fill-hover hover:text-primary-500"
                >
                  <Icon :name="m.icon" class="w-4 h-4" />
                  {{ m.label }}
                </NuxtLink>
              </li>
            </ul>
          </Transition>
        </li>
      </ul>

      <!-- Actions -->
      <div class="flex items-center gap-1 sm:gap-2">
        <!-- 搜索（阶段 5 替换为 AdvancedSearch 弹窗） -->
        <button
          type="button"
          class="w-9 h-9 rounded-md flex items-center justify-center text-neutral-text-secondary hover:bg-neutral-fill-hover hover:text-primary-500 transition-colors duration-fast ease-out"
          aria-label="搜索内容"
        >
          <Icon name="material-symbols:search-rounded" class="w-5 h-5" />
        </button>
        <client-only>
          <ColorSchemeToggle />
        </client-only>
        <NuxtLink
          to="/admin"
          class="hidden sm:inline-flex items-center gap-1.5 px-3 py-2 rounded-md bg-primary-500 text-white text-sm font-medium shadow-sm hover:bg-primary-400 active:bg-primary-600 transition-colors duration-fast ease-out focus-visible:outline-none focus-visible:ring-2 ring-primary-500 ring-offset-2 ring-offset-neutral-bg-container"
        >
          <Icon name="material-symbols:dashboard-customize-rounded" class="w-4 h-4" />
          后台
        </NuxtLink>
        <!-- Mobile menu -->
        <button
          class="md:hidden w-9 h-9 rounded-md flex items-center justify-center text-neutral-text-secondary hover:bg-neutral-fill-hover"
          aria-label="展开导航菜单"
          @click="openMobile = !openMobile"
        >
          <Icon v-if="!openMobile" name="material-symbols:menu-rounded" class="w-5 h-5" />
          <Icon v-else name="material-symbols:close-rounded" class="w-5 h-5" />
        </button>
      </div>
    </nav>

    <!-- Mobile menu -->
    <Transition name="collapse">
      <div v-show="openMobile" class="md:hidden border-t border-neutral-border-secondary bg-neutral-bg-container">
        <nav class="max-w-7xl mx-auto px-4 py-3 grid grid-cols-2 gap-1">
          <NuxtLink
            v-for="n in navs"
            :key="n.to"
            :to="n.to"
            class="px-3 py-2 rounded-md text-sm font-medium text-neutral-text-secondary hover:text-neutral-text-primary hover:bg-neutral-fill-hover"
            @click="openMobile = false"
          >{{ n.label }}</NuxtLink>
          <NuxtLink
            v-for="m in featureMenu"
            :key="m.to"
            :to="m.to"
            class="px-3 py-2 rounded-md text-sm font-medium text-neutral-text-secondary hover:text-neutral-text-primary hover:bg-neutral-fill-hover flex items-center gap-1.5"
            @click="openMobile = false"
          >
            <Icon :name="m.icon" class="w-4 h-4" />{{ m.label }}
          </NuxtLink>
          <NuxtLink to="/admin" class="px-3 py-2 rounded-md bg-primary-500 text-white text-sm font-medium col-span-2 mt-2 text-center">进入后台</NuxtLink>
        </nav>
      </div>
    </Transition>
  </header>
</template>

<style scoped>
.dropdown-enter-active, .dropdown-leave-active { transition: opacity 120ms ease, transform 120ms ease; }
.dropdown-enter-from, .dropdown-leave-to { opacity: 0; transform: translateY(-4px); }

.collapse-enter-active, .collapse-leave-active { transition: max-height 200ms ease, opacity 200ms ease; overflow: hidden; }
.collapse-enter-from, .collapse-leave-to { max-height: 0; opacity: 0; }
.collapse-enter-to, .collapse-leave-from { max-height: 600px; opacity: 1; }
</style>
