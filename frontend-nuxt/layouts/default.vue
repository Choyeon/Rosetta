<!-- ==============================================================
     默认布局（前台 Layout）
     对应 Astro：Layout.astro + MainGridLayout.astro
     - Header / SideBar / Footer 插槽占位
     - 主槽位 <slot /> = <NuxtPage /> 渲染产物
     ============================================================== -->
<script setup lang="ts">
interface Props {
  /** 隐藏侧栏（用于登录/OOBE/全屏页） */
  hideSidebar?: boolean;
  /** 隐藏 Footer */
  hideFooter?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  hideSidebar: false,
  hideFooter: false,
});
</script>

<template>
  <div
    class="min-h-screen flex flex-col bg-neutral-bg-layout text-neutral-text-primary"
  >
    <!-- ===== Header ===== -->
    <header class="sticky top-0 z-sticky backdrop-blur-sm bg-neutral-bg-container/90 border-b border-neutral-border-secondary shadow-xs">
      <nav class="max-w-7xl mx-auto px-4 sm:px-6 xl:px-8 h-16 flex items-center justify-between">
        <NuxtLink
          to="/"
          class="flex items-center gap-2 group select-none outline-none focus-visible:ring-2 ring-primary-500 rounded-md"
          aria-label="Rosetta 首页"
        >
          <div
            class="w-9 h-9 rounded-lg bg-gradient-to-br from-primary-500 via-nebula-blue to-rosetta-gold flex items-center justify-center shadow-sm group-hover:scale-105 transition-transform duration-normal ease-out"
            aria-hidden
          >
            <span class="text-white font-bold text-lg tracking-tight">R</span>
          </div>
          <div class="flex flex-col leading-none">
            <span class="font-semibold text-lg text-neutral-text-primary">Rosetta</span>
            <span class="text-[10px] uppercase tracking-[0.22em] text-neutral-text-tertiary mt-0.5">
              Lightweight Blog System
            </span>
          </div>
        </NuxtLink>

        <!-- Desktop Nav（占位，阶段 5 细化） -->
        <div class="hidden md:flex items-center gap-1">
          <NuxtLink to="/" class="px-3 py-2 rounded-md text-sm font-medium hover:bg-neutral-fill-hover transition-colors duration-fast ease-out">首页</NuxtLink>
          <NuxtLink to="/posts" class="px-3 py-2 rounded-md text-sm font-medium hover:bg-neutral-fill-hover transition-colors duration-fast ease-out">文章</NuxtLink>
          <NuxtLink to="/categories" class="px-3 py-2 rounded-md text-sm font-medium hover:bg-neutral-fill-hover transition-colors duration-fast ease-out">分类</NuxtLink>
          <NuxtLink to="/tags" class="px-3 py-2 rounded-md text-sm font-medium hover:bg-neutral-fill-hover transition-colors duration-fast ease-out">标签</NuxtLink>
          <NuxtLink to="/archive" class="px-3 py-2 rounded-md text-sm font-medium hover:bg-neutral-fill-hover transition-colors duration-fast ease-out">归档</NuxtLink>
          <NuxtLink to="/about" class="px-3 py-2 rounded-md text-sm font-medium hover:bg-neutral-fill-hover transition-colors duration-fast ease-out">关于</NuxtLink>
        </div>

        <div class="flex items-center gap-2">
          <!-- 搜索按钮（占位，阶段 5 替换为 AdvancedSearch） -->
          <button
            type="button"
            aria-label="搜索"
            class="w-9 h-9 rounded-md flex items-center justify-center text-neutral-text-secondary hover:bg-neutral-fill-hover hover:text-primary-500 transition-colors duration-fast ease-out"
          >
            <Icon name="material-symbols:search-rounded" class="w-5 h-5" />
          </button>
          <!-- 深浅切换（@nuxtjs/color-mode 提供的 composable） -->
          <client-only>
            <ColorSwitcher />
          </client-only>
          <!-- 登录入口 -->
          <NuxtLink
            to="/admin"
            class="hidden sm:inline-flex items-center gap-1.5 px-3 py-2 rounded-md bg-primary-500 text-white text-sm font-medium shadow-sm hover:bg-primary-400 active:bg-primary-600 transition-colors duration-fast ease-out focus-visible:outline-none focus-visible:ring-2 ring-primary-500 ring-offset-2 ring-offset-neutral-bg-container"
          >
            <Icon name="material-symbols:dashboard-customize-rounded" class="w-4 h-4" />
            后台
          </NuxtLink>
        </div>
      </nav>
    </header>

    <!-- ===== Main Grid ===== -->
    <div class="flex-1 w-full">
      <div
        class="max-w-7xl mx-auto px-4 sm:px-6 xl:px-8 py-lg md:py-xl grid gap-xl"
        :class="[
          props.hideSidebar ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px] xl:grid-cols-[minmax(0,1fr)_340px]'
        ]"
      >
        <!-- 主内容槽 -->
        <main
          id="swup-container"
          class="min-w-0"
          role="main"
          aria-label="主内容区"
        >
          <slot />
        </main>

        <!-- 侧栏（hideSidebar=false 时显示） -->
        <aside
          v-if="!props.hideSidebar"
          class="hidden lg:block min-w-0 h-fit space-y-lg lg:sticky lg:top-20"
          aria-label="侧边栏"
        >
          <SidebarProfileSkeleton />
          <SidebarTocSkeleton />
          <SidebarTagsSkeleton />
        </aside>
      </div>
    </div>

    <!-- ===== Footer ===== -->
    <footer
      v-if="!props.hideFooter"
      class="mt-3xl border-t border-neutral-border-secondary bg-neutral-bg-spot text-neutral-text-secondary"
    >
      <div class="max-w-7xl mx-auto px-4 sm:px-6 xl:px-8 py-2xl grid grid-cols-1 md:grid-cols-4 gap-xl">
        <div>
          <div class="flex items-center gap-2 mb-md">
            <div class="w-7 h-7 rounded-md bg-gradient-to-br from-primary-500 via-nebula-blue to-rosetta-gold" />
            <span class="font-semibold text-neutral-text-primary">Rosetta</span>
          </div>
          <p class="text-sm leading-relaxed">
            以内容与体验为核心的现代化博客系统。<br />
            由 Vue 3 · Nuxt 4 · FastAPI · Tailwind v4 驱动。
          </p>
        </div>
        <div>
          <h3 class="text-sm font-semibold text-neutral-text-primary mb-md">导航</h3>
          <ul class="space-y-xs text-sm">
            <li><NuxtLink to="/posts">文章</NuxtLink></li>
            <li><NuxtLink to="/categories">分类</NuxtLink></li>
            <li><NuxtLink to="/tags">标签</NuxtLink></li>
            <li><NuxtLink to="/archive">归档</NuxtLink></li>
          </ul>
        </div>
        <div>
          <h3 class="text-sm font-semibold text-neutral-text-primary mb-md">功能</h3>
          <ul class="space-y-xs text-sm">
            <li><NuxtLink to="/dynamic">动态</NuxtLink></li>
            <li><NuxtLink to="/bangumi">番剧</NuxtLink></li>
            <li><NuxtLink to="/anime">动漫</NuxtLink></li>
            <li><NuxtLink to="/gallery">相册</NuxtLink></li>
            <li><NuxtLink to="/friends">友情链接</NuxtLink></li>
          </ul>
        </div>
        <div>
          <h3 class="text-sm font-semibold text-neutral-text-primary mb-md">关于</h3>
          <ul class="space-y-xs text-sm">
            <li><NuxtLink to="/about">关于本站</NuxtLink></li>
            <li><NuxtLink to="/guestbook">留言</NuxtLink></li>
            <li><NuxtLink to="/sponsor">赞助</NuxtLink></li>
          </ul>
        </div>
      </div>
      <div class="border-t border-neutral-border-secondary">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 xl:px-8 py-md flex flex-col sm:flex-row items-center justify-between gap-xs text-sm">
          <p>© 2025–2026 Rosetta. All rights reserved.</p>
          <p>
            Powered by Nuxt 4 &nbsp;·&nbsp;
            Build with ♡ by <span class="text-primary-500 font-medium">Choyu Choyeon</span>
          </p>
        </div>
      </div>
    </footer>
  </div>
</template>

<!-- =============================================================
     占位骨架组件（阶段 3-5 期间替换为真实组件）
     保证骨架期 UI 不空、不 FOUC
     ============================================================= -->
<script lang="ts">
/** Color Switcher（使用 @nuxtjs/color-mode 的 useColorMode composable） */
</script>
<script setup lang="ts">
const ColorSwitcher = defineComponent({
  name: "ColorSwitcher",
  setup() {
    const colorMode = useColorMode();
    const toggle = () => {
      colorMode.preference =
        colorMode.value === "one-dark-pro" || colorMode.value === "dark"
          ? "one-light"
          : "one-dark-pro";
    };
    return () =>
      h("button", {
        type: "button",
        "aria-label": "切换深浅色",
        onClick: toggle,
        class:
          "w-9 h-9 rounded-md flex items-center justify-center text-neutral-text-secondary hover:bg-neutral-fill-hover hover:text-primary-500 transition-colors duration-fast ease-out",
      }, [
        h("span", { class: "w-5 h-5 flex items-center justify-center" }, [
          // 日/月 切换图标（纯 SVG，无 icon 依赖）
          colorMode.value === "one-dark-pro" || colorMode.value === "dark"
            ? h(
                "svg",
                {
                  viewBox: "0 0 24 24",
                  fill: "none",
                  stroke: "currentColor",
                  "stroke-width": 2,
                  "stroke-linecap": "round",
                  "stroke-linejoin": "round",
                  class: "w-5 h-5",
                },
                [
                  h("circle", { cx: 12, cy: 12, r: 4 }),
                  h("path", {
                    d: "M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41",
                  }),
                ]
              )
            : h(
                "svg",
                {
                  viewBox: "0 0 24 24",
                  fill: "none",
                  stroke: "currentColor",
                  "stroke-width": 2,
                  "stroke-linecap": "round",
                  "stroke-linejoin": "round",
                  class: "w-5 h-5",
                },
                [h("path", { d: "M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" })]
              ),
        ]),
      ]);
  },
});

/** 侧栏骨架组件（阶段 3 替换为真实实现） */
const SidebarProfileSkeleton = defineComponent({
  name: "SidebarProfileSkeleton",
  setup() {
    return () =>
      h(
        "section",
        {
          class:
            "bg-neutral-bg-container rounded-lg p-lg shadow-sm border border-neutral-border-secondary",
        },
        [
          h("div", { class: "flex flex-col items-center text-center" }, [
            h("div", {
              class:
                "w-20 h-20 rounded-full bg-gradient-to-br from-primary-300 to-rosetta-gold mb-sm",
            }),
            h(
              "div",
              { class: "h-4 w-24 rounded bg-neutral-fill-hover mb-xs animate-pulse" }
            ),
            h(
              "div",
              { class: "h-3 w-32 rounded bg-neutral-fill-quaternary animate-pulse" }
            ),
            h(
              "div",
              {
                class:
                  "mt-md grid grid-cols-3 gap-xs w-full text-center text-xs text-neutral-text-tertiary",
              },
              [
                h("div", {}, [
                  h("div", { class: "font-semibold text-neutral-text-primary text-sm" }, "64"),
                  h("div", { class: "mt-0.5" }, "文章"),
                ]),
                h("div", {}, [
                  h("div", { class: "font-semibold text-neutral-text-primary text-sm" }, "12"),
                  h("div", { class: "mt-0.5" }, "分类"),
                ]),
                h("div", {}, [
                  h("div", { class: "font-semibold text-neutral-text-primary text-sm" }, "233"),
                  h("div", { class: "mt-0.5" }, "标签"),
                ]),
              ]
            ),
          ]),
        ]
      );
  },
});

const SidebarTocSkeleton = defineComponent({
  name: "SidebarTocSkeleton",
  setup() {
    return () =>
      h(
        "section",
        {
          class:
            "bg-neutral-bg-container rounded-lg p-lg shadow-sm border border-neutral-border-secondary space-y-xs",
        },
        [
          h("div", { class: "h-4 w-16 rounded bg-neutral-fill-hover mb-sm animate-pulse" }),
          ...Array.from({ length: 5 }).map((_, i) =>
            h("div", {
              key: i,
              class: `h-3 rounded bg-neutral-fill-quaternary animate-pulse ${
                ["w-full", "w-5/6 ml-xs", "w-4/6 ml-md", "w-5/6 ml-xs", "w-3/4 ml-md"][i]
              }`,
            })
          ),
        ]
      );
  },
});

const SidebarTagsSkeleton = defineComponent({
  name: "SidebarTagsSkeleton",
  setup() {
    return () =>
      h(
        "section",
        {
          class:
            "bg-neutral-bg-container rounded-lg p-lg shadow-sm border border-neutral-border-secondary",
        },
        [
          h("div", { class: "h-4 w-12 rounded bg-neutral-fill-hover mb-md animate-pulse" }),
          h("div", { class: "flex flex-wrap gap-xs" }, [
            ...Array.from({ length: 8 }).map((_, i) =>
              h("span", {
                key: i,
                class:
                  "h-6 px-3 rounded-full bg-neutral-fill-hover text-xs text-transparent animate-pulse",
              }, "占位")
            ),
          ]),
        ]
      );
  },
});
</script>
