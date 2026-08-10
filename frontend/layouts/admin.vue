<!--
  Admin 后台布局（对应 Astro layouts/admin.astro）
  - 隐藏侧边栏
  - 左侧后台导航 + 主内容
  阶段 6 时替换为真实 AdminNavTree
-->
<template>
  <div class="min-h-screen flex bg-neutral-bg-layout text-neutral-text-primary">
    <!-- Admin Side Nav -->
    <aside class="w-64 shrink-0 border-r border-neutral-border-secondary bg-neutral-bg-container hidden md:flex flex-col">
      <div class="h-16 px-5 flex items-center gap-2 border-b border-neutral-border-secondary">
        <div
          class="w-8 h-8 rounded-md bg-gradient-to-br from-primary-500 via-nebula-blue to-rosetta-gold flex items-center justify-center text-white font-bold"
        >R</div>
        <span class="font-semibold">Rosetta Admin</span>
      </div>
      <nav class="flex-1 p-2 space-y-0.5 text-sm overflow-y-auto">
        <NuxtLink to="/admin" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:space-dashboard-rounded" class="w-4 h-4" />
          仪表板
        </NuxtLink>
        <NuxtLink to="/admin/posts" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:article-rounded" class="w-4 h-4" />
          文章管理
        </NuxtLink>
        <NuxtLink to="/admin/categories" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:category-rounded" class="w-4 h-4" />
          分类
        </NuxtLink>
        <NuxtLink to="/admin/tags" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:tag-rounded" class="w-4 h-4" />
          标签
        </NuxtLink>
        <NuxtLink to="/admin/pages" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:description-rounded" class="w-4 h-4" />
          独立页面
        </NuxtLink>
        <NuxtLink to="/admin/nav" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:menu-rounded" class="w-4 h-4" />
          导航菜单
        </NuxtLink>
        <NuxtLink to="/admin/comments" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:comment-rounded" class="w-4 h-4" />
          评论
        </NuxtLink>
        <NuxtLink to="/admin/users" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:group-rounded" class="w-4 h-4" />
          用户
        </NuxtLink>
        <NuxtLink to="/admin/dynamics" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:bolt-rounded" class="w-4 h-4" />
          动态
        </NuxtLink>
        <NuxtLink to="/admin/announcements" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:campaign-rounded" class="w-4 h-4" />
          公告
        </NuxtLink>
        <NuxtLink to="/admin/banners" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:flag-rounded" class="w-4 h-4" />
          Banner
        </NuxtLink>
        <NuxtLink to="/admin/friends" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:group-add-rounded" class="w-4 h-4" />
          友链
        </NuxtLink>
        <NuxtLink to="/admin/gallery" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:photo-library-rounded" class="w-4 h-4" />
          相册
        </NuxtLink>
        <NuxtLink to="/admin/albums" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:collections-bookmark-rounded" class="w-4 h-4" />
          专辑
        </NuxtLink>
        <NuxtLink to="/admin/guestbook" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:edit-note-rounded" class="w-4 h-4" />
          留言
        </NuxtLink>
        <NuxtLink to="/admin/monitor" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:monitor-heart-rounded" class="w-4 h-4" />
          监控
        </NuxtLink>
        <NuxtLink to="/admin/migration" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:swap-horiz-rounded" class="w-4 h-4" />
          数据迁移
        </NuxtLink>
        <NuxtLink to="/admin/settings" class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-neutral-fill-hover text-neutral-text-primary">
          <Icon name="material-symbols:settings-rounded" class="w-4 h-4" />
          设置
        </NuxtLink>
      </nav>
    </aside>

    <!-- Main area -->
    <div class="flex-1 min-w-0 flex flex-col">
      <!-- Top bar -->
      <header class="h-16 shrink-0 border-b border-neutral-border-secondary bg-neutral-bg-container px-5 flex items-center justify-between">
        <div class="text-base font-semibold truncate">
          <slot name="page-title">Rosetta 管理后台</slot>
        </div>
        <div class="flex items-center gap-2">
          <NuxtLink
            to="/"
            class="hidden sm:inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-sm text-neutral-text-secondary hover:bg-neutral-fill-hover"
          >
            <Icon name="material-symbols:open-in-new-rounded" class="w-4 h-4" />
            前台
          </NuxtLink>
          <button
            type="button"
            class="w-9 h-9 rounded-md flex items-center justify-center text-neutral-text-secondary hover:bg-neutral-fill-hover"
            aria-label="退出登录"
          >
            <Icon name="material-symbols:logout-rounded" class="w-5 h-5" />
          </button>
        </div>
      </header>
      <main class="flex-1 min-w-0 p-5 overflow-auto">
        <slot />
      </main>
    </div>
  </div>
</template>
