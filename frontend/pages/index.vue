<template>
  <div>
    <!-- =========================================================
         当 activeThemeSlug 为极简主题 slug → AstroPaper 风格首页
         · astro-paper-inspired  极简主题（内建，除默认主题外唯一保留）
         · 无大图 Bing 壁纸 Hero（不请求壁纸、不渲染图片区）
         · 无文字 Hero（极简主题不渲染任何 hero header）
         · 不渲染 Pinned 段、不渲染 Sidebar、不渲染 Newsletter CTA
         · 最新文章用纯竖排列表：日期 · 标题 · 摘要，一条一行（非卡片）
         ========================================================= -->
    <template v-if="isMinimalTheme">
      <section
        class="container pt-14 md:pt-20 pb-24"
        :style="containerMaxStyle"
      >
        <h2 class="ap-section-title mb-7 md:mb-8 text-xl md:text-2xl font-semibold tracking-tight">
          {{ apFeaturedLabel }}
        </h2>

        <div
          v-if="postsError"
          class="text-sm text-destructive border-l-2 border-destructive pl-3"
        >
          {{ t('admin.posts.loadFailed') }}
        </div>
        <div
          v-else-if="postsPending && latestPosts.length === 0"
          class="space-y-6"
        >
          <PostSkeleton
            v-for="i in 4"
            :key="i"
            variant="compact"
          />
        </div>
        <ul
          v-else-if="allDisplayPosts.length === 0"
          class="text-sm text-muted-foreground"
        >
          <li>{{ t('admin.posts.empty') }}</li>
        </ul>
        <ol
          v-else
          class="ap-post-list space-y-8 md:space-y-9"
        >
          <li
            v-for="post in allDisplayPosts"
            :key="post.id"
            class="ap-post-item group"
          >
            <NuxtLink
              :to="`/${post.slug}`"
              class="block group-hover:no-underline"
            >
              <div class="ap-post-date text-xs uppercase tracking-[0.14em] text-muted-foreground tabular-nums mb-2">
                {{ apFormatDate(post.published_at || post.updated_at || post.created_at) }}
              </div>
              <h3 class="ap-post-title text-xl md:text-[1.35rem] font-semibold leading-snug tracking-tight group-hover:underline underline-offset-4 decoration-from-font">
                {{ pickLocalized(post.title) }}
              </h3>
              <p
                v-if="apPostExcerpt(post)"
                class="ap-post-excerpt mt-2 md:mt-3 text-[0.95rem] leading-[1.7] text-muted-foreground line-clamp-2 md:line-clamp-3"
              >
                {{ apPostExcerpt(post) }}
              </p>
            </NuxtLink>
          </li>
        </ol>

        <div
          v-if="allDisplayPosts.length"
          class="mt-12 md:mt-14"
        >
          <NuxtLink
            to="/posts"
            class="text-sm font-medium inline-flex items-center gap-1.5 text-foreground/90 hover:text-foreground hover:underline underline-offset-4"
          >
            {{ t('home.viewAll') || 'All Posts' }}
            <ArrowRight class="size-3.5" />
          </NuxtLink>
        </div>
      </section>
    </template>

    <!-- ================= Default (Editorial WP-Style) Hero + Post Grid ================= -->
    <template v-else>
      <section
        :class="[
          'relative overflow-hidden',
          isEditorialTheme
            ? 'min-h-[72vh] md:min-h-[78vh]'
            : 'min-h-[80vh] md:min-h-[86vh]'
        ]"
        aria-label="hero"
        data-editorial-section="hero"
        :style="currentWallpaper ? {
          backgroundImage: `url(${currentWallpaper.fullUrl})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center center',
          backgroundRepeat: 'no-repeat',
          backgroundAttachment: 'local'
        } : {
          backgroundImage: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0c4a6e 100%)'
        }"
      >
        <!-- Subtle depth overlays (keep cinematics — dim for editorial wallpaper-only view) -->
        <div class="absolute inset-0 bg-gradient-to-t from-black/75 via-black/18 to-black/22 pointer-events-none" />
        <div
          :class="[
            'absolute inset-0 pointer-events-none',
            isEditorialTheme
              ? 'bg-gradient-to-b from-black/18 via-black/6 to-transparent'
              : 'bg-gradient-to-r from-black/50 via-black/10 to-black/20 bg-gradient-to-b from-black/25 via-transparent to-transparent'
          ]"
        />

        <!-- Hero copy: Editorial theme → wallpaper-only (no title/CTA overlays on top).
             Non-Editorial (fallback magazine-style) retains title/CTA for visual emphasis. -->
        <template v-if="!isEditorialTheme">
          <div
            class="relative z-20 container pt-24 md:pt-32"
            :style="containerMaxStyle"
          >
            <div class="max-w-3xl">
              <span
                class="inline-flex items-center gap-2 rounded-full border border-white/15 bg-black/35 px-3 py-1 text-[11px] uppercase tracking-[0.22em] text-white/70 backdrop-blur-xl"
              >
                <span class="size-1.5 rounded-full bg-primary" />
                {{ site.siteTitle.value }}
              </span>
              <h1
                data-hero-title
                class="mt-5 font-display text-4xl md:text-6xl font-black leading-[1.05] tracking-tight text-white drop-shadow-[0_2px_14px_rgba(0,0,0,0.55)]"
              >
                {{ _heroTitle }}
              </h1>
              <p
                data-hero-subtitle
                class="mt-5 max-w-2xl text-base md:text-xl text-white/85 leading-relaxed drop-shadow-[0_1px_6px_rgba(0,0,0,0.5)]"
              >
                {{ _heroSubtitle }}
              </p>
              <div
                v-if="_heroCaption"
                class="mt-3 text-sm text-white/70"
              >
                {{ _heroCaption }}
              </div>
              <div class="mt-8 flex flex-wrap items-center gap-3">
                <NuxtLink
                  :to="_heroCtaUrl"
                  class="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-xl shadow-black/30 hover:bg-primary/90 transition-colors"
                >
                  {{ _heroCtaText }}
                  <ArrowRight class="size-4" />
                </NuxtLink>
                <NuxtLink
                  to="/posts"
                  class="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-5 py-3 text-sm font-semibold text-white backdrop-blur-xl hover:bg-white/20 transition-colors"
                >
                  {{ t('home.viewAll') || '浏览全部文章' }}
                </NuxtLink>
              </div>
            </div>
          </div>
        </template>

        <!-- Bottom HUD: 7-day switcher (left) + Photo meta + credit (right) -->
        <div class="absolute bottom-0 left-0 right-0 z-20">
          <div
            :class="[
              'container relative flex flex-col sm:flex-row items-stretch sm:items-end justify-between gap-4',
              isEditorialTheme ? [editorialClassPx, 'pb-7 md:pb-9'] : 'pb-10 md:pb-12'
            ]"
            :style="containerMaxStyle"
          >
            <!-- 7-day switcher → elegant per-day cards: gradient underlay + img overlay + center date -->
            <div
              class="rounded-2xl border border-white/15 bg-black/45 backdrop-blur-xl px-3 py-3 flex items-center gap-2 shadow-2xl shadow-black/40"
            >
              <div class="hidden sm:flex flex-col pr-2 pl-1 border-r border-white/10 justify-center">
                <span class="text-[10px] uppercase tracking-[0.14em] text-white/60">{{ t('home.wallpaper') }}</span>
                <span class="text-xs font-medium text-white/90">{{ t('home.recent7Days') }}</span>
              </div>
              <div class="flex items-center gap-2">
                <button
                  v-for="day in recentDays"
                  :key="day.index"
                  type="button"
                  class="group relative size-11 sm:size-14 rounded-lg overflow-hidden ring-1 ring-white/15 transition-all duration-200 shrink-0"
                  :class="currentIdx === day.index
                    ? 'ring-2 ring-white/90 scale-105 shadow-[0_0_0_2px_rgba(255,255,255,0.1),0_8px_24px_-6px_rgba(0,0,0,0.6)]'
                    : 'hover:ring-white/60 hover:scale-[1.03] opacity-85 hover:opacity-100'"
                  :aria-label="day.label"
                  :title="day.title || day.label"
                  @click="selectWallpaper(day.index)"
                >
                  <div class="absolute inset-0 z-10 flex flex-col items-center justify-center text-white">
                    <span class="text-[15px] sm:text-[17px] font-bold leading-none tracking-tight drop-shadow-[0_1px_4px_rgba(0,0,0,0.5)]">
                      {{ day.dateCompact.main }}
                    </span>
                    <span class="text-[9px] sm:text-[10px] mt-1 leading-none tracking-[0.08em] opacity-90 drop-shadow-[0_1px_2px_rgba(0,0,0,0.45)]">
                      {{ day.dateCompact.sub }}
                    </span>
                  </div>
                  <!-- Thumbnail image → covers gradient when successfully loaded -->
                  <img
                    v-if="day.thumbnail"
                    :src="day.thumbnail"
                    :alt="day.title || day.label"
                    class="absolute inset-0 w-full h-full object-cover transition-opacity duration-300 ease-out z-20"
                    loading="lazy"
                  >
                </button>
              </div>
            </div>

            <!-- Photo credit (right) → no COPYRIGHT label prefix; show image title first, then credit.
               点击整张 meta 卡片，统一跳 Bing 官方搜索页（Bing API copyrightlink → 按 title 搜 → bing.com 首页）。
               不提供下载按钮：下载版权图片属于用户本地浏览器另存为即可，不提供专用 icon。 -->
            <a
              v-if="currentWallpaper?.copyright || currentWallpaper?.title || currentWallpaper?.copyrightlink"
              :href="getBingOfficialLink(currentWallpaper)"
              target="_blank"
              rel="noreferrer noopener"
              class="rounded-2xl border border-white/15 bg-black/45 backdrop-blur-xl px-4 py-3 max-w-lg sm:text-right text-xs sm:text-sm text-white/85 hover:text-white transition-colors shadow-2xl shadow-black/40 hover:bg-black/60"
            >
              <div
                v-if="currentWallpaper.title"
                class="text-sm sm:text-base font-semibold text-white leading-snug mb-1"
              >
                {{ currentWallpaper.title }}
              </div>
              <span
                v-if="currentWallpaper.copyright"
                class="line-clamp-2 leading-snug text-white/75"
              >{{ currentWallpaper.copyright }}</span>
            </a>
          </div>
        </div>
      </section>

      <section
        :class="[
          'container',
          sectionTightY ? 'py-8 md:py-11' : 'py-14 md:py-20',
          isEditorialTheme ? editorialClassPx : ''
        ]"
        data-editorial-section="pinned"
        :style="containerMaxStyle"
      >
        <div class="flex items-end justify-between mb-8 gap-6 flex-wrap">
          <div>
            <div class="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-muted-foreground">
              <span class="size-1.5 rounded-full bg-warning" />
              {{ t('posts.pinned') }}
            </div>
            <h2 class="mt-2 font-display text-2xl md:text-3xl font-bold tracking-tight">
              {{ t('posts.pinned') }}
            </h2>
          </div>
        </div>

        <div
          v-if="postsError"
          class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive"
        >
          {{ t('admin.posts.loadFailed') }}
        </div>
        <div
          v-else-if="postsPending && pinnedPosts.length === 0"
          :class="['grid', pinnedGridClass]"
        >
          <PostSkeleton
            v-for="i in 3"
            :key="i"
          />
        </div>
        <div
          v-else-if="pinnedPosts.length === 0"
          class="rounded-xl border bg-muted/30 p-6 text-sm text-muted-foreground"
        >
          {{ t('admin.posts.empty') }}
        </div>
        <div
          v-else
          :class="['grid', pinnedGridClass, 'items-start']"
        >
          <PostCard
            v-for="post in pinnedPosts"
            :key="post.id"
            :post="post"
          />
        </div>
      </section>

      <!-- ===== LATEST + SIDEBAR ===== -->
      <section
        :class="[
          'container',
          sectionTightY ? 'pb-10 md:pb-12' : 'pb-16',
          isEditorialTheme ? editorialClassPx : ''
        ]"
        data-editorial-section="latest"
        :style="containerMaxStyle"
      >
        <div
          class="grid gap-10"
          :class="mainGridColsClass"
        >
          <div
            v-if="showSidebar && sidebarPosition === 'left'"
            class="flex flex-col gap-6 order-2 lg:order-1"
          >
            <!-- Site stats -->
            <Card>
              <CardHeader>
                <CardTitle class="text-lg">
                  <span class="inline-flex items-center gap-2">
                    <span class="size-1.5 rounded-full bg-primary" />
                    <span class="uppercase tracking-[0.16em] text-xs text-muted-foreground">
                      {{ t('home.siteStats') }}
                    </span>
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  v-if="siteStatsError"
                  class="text-sm text-destructive"
                >
                  {{ t('admin.posts.loadFailed') }}
                </div>
                <div
                  v-else-if="siteStatsPending"
                  class="grid grid-cols-2 gap-3"
                >
                  <Skeleton
                    v-for="i in 4"
                    :key="i"
                    class="h-24 rounded-xl"
                  />
                </div>
                <div
                  v-else-if="siteStats"
                  class="grid grid-cols-2 gap-3"
                >
                  <div class="rounded-xl bg-muted/50 p-4">
                    <div class="text-2xl font-bold font-display">
                      {{ formatStat(siteStats.total_posts) }}
                    </div>
                    <div class="text-xs text-muted-foreground mt-1">
                      {{ t('home.postsCount') }}
                    </div>
                  </div>
                  <div class="rounded-xl bg-muted/50 p-4">
                    <div class="text-2xl font-bold font-display">
                      {{ formatStat(siteStats.total_categories) }}
                    </div>
                    <div class="text-xs text-muted-foreground mt-1">
                      {{ t('home.categoriesCount') }}
                    </div>
                  </div>
                  <div class="rounded-xl bg-muted/50 p-4">
                    <div class="text-2xl font-bold font-display">
                      {{ formatStat(siteStats.total_tags) }}
                    </div>
                    <div class="text-xs text-muted-foreground mt-1">
                      {{ t('home.tagsCount') }}
                    </div>
                  </div>
                  <div class="rounded-xl bg-muted/50 p-4">
                    <div class="text-2xl font-bold font-display">
                      {{ formatStat(siteStats.total_words) }}
                    </div>
                    <div class="text-xs text-muted-foreground mt-1">
                      {{ t('post.words') }}
                    </div>
                  </div>
                </div>
                <div
                  v-else
                  class="text-sm text-muted-foreground"
                >
                  {{ t('common.noData') }}
                </div>
              </CardContent>
            </Card>

            <!-- Tech stack versions -->
            <Card>
              <CardHeader>
                <CardTitle class="text-lg">
                  <span class="inline-flex items-center gap-2">
                    <span class="size-1.5 rounded-full bg-success" />
                    <span class="uppercase tracking-[0.16em] text-xs text-muted-foreground">
                      {{ t('home.techStack') }}
                    </span>
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div class="space-y-2.5 text-sm">
                  <template
                    v-for="(row, idx) in techRows"
                    :key="row.key"
                  >
                    <div class="flex items-center justify-between gap-3">
                      <div class="flex items-center gap-2 min-w-0">
                        <span
                          class="shrink-0 size-2 rounded-full"
                          :class="row.color"
                        />
                        <span class="text-muted-foreground truncate">{{ row.label }}</span>
                      </div>
                      <code class="font-mono text-xs px-2 py-0.5 rounded-md bg-muted/70 text-foreground/90 truncate max-w-[55%] tabular-nums">
                        v{{ buildInfo[row.key] }}
                      </code>
                    </div>
                    <div
                      v-if="idx === 3 || idx === 5"
                      class="my-2 border-t border-border"
                    />
                  </template>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle class="text-lg">
                  <span class="inline-flex items-center gap-2">
                    <span class="size-1.5 rounded-full bg-warning" />
                    <span class="uppercase tracking-[0.16em] text-xs text-muted-foreground">
                      {{ t('nav.categories') }}
                    </span>
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  v-if="categoriesError"
                  class="text-sm text-destructive"
                >
                  {{ t('admin.posts.loadFailed') }}
                </div>
                <div
                  v-else-if="categoriesPending"
                  class="flex flex-wrap gap-2"
                >
                  <Skeleton
                    v-for="i in 4"
                    :key="i"
                    class="h-6 w-16 rounded-full"
                  />
                </div>
                <div
                  v-else-if="categories.length"
                  class="flex flex-wrap gap-2"
                >
                  <CategoryBadge
                    v-for="category in categories"
                    :key="category.id"
                    :color="category.color ?? null"
                    :icon="category.icon ?? null"
                    :label="pickLocalized(category.name)"
                    :to="`/categories/${category.slug}`"
                  />
                </div>
                <div
                  v-else
                  class="text-sm text-muted-foreground"
                >
                  {{ t('common.noData') }}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle class="text-lg">
                  <span class="inline-flex items-center gap-2">
                    <span class="size-1.5 rounded-full bg-primary" />
                    <span class="uppercase tracking-[0.16em] text-xs text-muted-foreground">
                      {{ t('home.tagCloud') }}
                    </span>
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  v-if="tagsError"
                  class="text-sm text-destructive"
                >
                  {{ t('admin.posts.loadFailed') }}
                </div>
                <div
                  v-else-if="tagsPending"
                  class="flex flex-wrap gap-1.5"
                >
                  <Skeleton
                    v-for="i in 6"
                    :key="i"
                    class="h-6 w-14 rounded-full"
                  />
                </div>
                <div
                  v-else-if="tags.length"
                  class="flex flex-wrap gap-1.5"
                >
                  <Badge
                    v-for="tag in tags"
                    :key="tag.id"
                    variant="outline"
                    class="cursor-pointer hover:bg-accent transition-colors"
                    @click="navigateTo(`/posts?tag=${tag.slug}`)"
                  >
                    #{{ pickLocalized(tag.name) }}
                  </Badge>
                </div>
                <div
                  v-else
                  class="text-sm text-muted-foreground"
                >
                  {{ t('common.noData') }}
                </div>
              </CardContent>
            </Card>
          </div>

          <div :class="['order-1 lg:order-2', mainColSpanClass]">
            <div class="flex items-end justify-between mb-6 gap-4 flex-wrap">
              <div>
                <div class="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-muted-foreground">
                  <span class="size-1.5 rounded-full bg-primary" />
                  {{ t('home.latestPosts') }}
                </div>
                <h2 class="mt-2 font-display text-2xl font-bold tracking-tight">
                  {{ t('home.latestPosts') }}
                </h2>
              </div>
              <NuxtLink
                to="/posts"
                class="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors"
              >
                {{ t('home.viewAll') }}
                <ArrowRight class="size-3.5" />
              </NuxtLink>
            </div>

            <div
              v-if="postsError"
              class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive"
            >
              {{ t('admin.posts.loadFailed') }}
            </div>
            <template v-else-if="postsPending && latestPosts.length === 0">
              <div
                v-if="latestAsGrid"
                :class="['grid', latestGridClass]"
              >
                <PostSkeleton
                  v-for="i in 4"
                  :key="i"
                  variant="compact"
                />
              </div>
              <div
                v-else
                class="flex flex-col gap-5"
              >
                <PostSkeleton
                  v-for="i in 4"
                  :key="i"
                  variant="compact"
                />
              </div>
            </template>
            <template v-else-if="latestPosts.length > 0">
              <div
                v-if="latestAsGrid"
                :class="['grid', latestGridClass]"
              >
                <PostCard
                  v-for="post in latestPosts"
                  :key="post.id"
                  :post="post"
                  variant="compact"
                />
              </div>
              <div
                v-else
                class="flex flex-col gap-5"
              >
                <PostCard
                  v-for="post in latestPosts"
                  :key="post.id"
                  :post="post"
                  variant="compact"
                />
              </div>
            </template>
            <div
              v-else
              class="rounded-xl border bg-muted/30 p-6 text-sm text-muted-foreground"
            >
              {{ t('admin.posts.empty') }}
            </div>
          </div>

          <div
            v-if="showSidebar && sidebarPosition === 'right'"
            class="flex flex-col gap-6 order-3"
          >
            <!-- Site stats -->
            <Card>
              <CardHeader>
                <CardTitle class="text-lg">
                  <span class="inline-flex items-center gap-2">
                    <span class="size-1.5 rounded-full bg-primary" />
                    <span class="uppercase tracking-[0.16em] text-xs text-muted-foreground">
                      {{ t('home.siteStats') }}
                    </span>
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  v-if="siteStatsError"
                  class="text-sm text-destructive"
                >
                  {{ t('admin.posts.loadFailed') }}
                </div>
                <div
                  v-else-if="siteStatsPending"
                  class="grid grid-cols-2 gap-3"
                >
                  <Skeleton
                    v-for="i in 4"
                    :key="i"
                    class="h-24 rounded-xl"
                  />
                </div>
                <div
                  v-else-if="siteStats"
                  class="grid grid-cols-2 gap-3"
                >
                  <div class="rounded-xl bg-muted/50 p-4">
                    <div class="text-2xl font-bold font-display">
                      {{ formatStat(siteStats.total_posts) }}
                    </div>
                    <div class="text-xs text-muted-foreground mt-1">
                      {{ t('home.postsCount') }}
                    </div>
                  </div>
                  <div class="rounded-xl bg-muted/50 p-4">
                    <div class="text-2xl font-bold font-display">
                      {{ formatStat(siteStats.total_categories) }}
                    </div>
                    <div class="text-xs text-muted-foreground mt-1">
                      {{ t('home.categoriesCount') }}
                    </div>
                  </div>
                  <div class="rounded-xl bg-muted/50 p-4">
                    <div class="text-2xl font-bold font-display">
                      {{ formatStat(siteStats.total_tags) }}
                    </div>
                    <div class="text-xs text-muted-foreground mt-1">
                      {{ t('home.tagsCount') }}
                    </div>
                  </div>
                  <div class="rounded-xl bg-muted/50 p-4">
                    <div class="text-2xl font-bold font-display">
                      {{ formatStat(siteStats.total_words) }}
                    </div>
                    <div class="text-xs text-muted-foreground mt-1">
                      {{ t('post.words') }}
                    </div>
                  </div>
                </div>
                <div
                  v-else
                  class="text-sm text-muted-foreground"
                >
                  {{ t('common.noData') }}
                </div>
              </CardContent>
            </Card>

            <!-- Tech stack versions -->
            <Card>
              <CardHeader>
                <CardTitle class="text-lg">
                  <span class="inline-flex items-center gap-2">
                    <span class="size-1.5 rounded-full bg-success" />
                    <span class="uppercase tracking-[0.16em] text-xs text-muted-foreground">
                      {{ t('home.techStack') }}
                    </span>
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div class="space-y-2.5 text-sm">
                  <template
                    v-for="(row, idx) in techRows"
                    :key="row.key"
                  >
                    <div class="flex items-center justify-between gap-3">
                      <div class="flex items-center gap-2 min-w-0">
                        <span
                          class="shrink-0 size-2 rounded-full"
                          :class="row.color"
                        />
                        <span class="text-muted-foreground truncate">{{ row.label }}</span>
                      </div>
                      <code class="font-mono text-xs px-2 py-0.5 rounded-md bg-muted/70 text-foreground/90 truncate max-w-[55%] tabular-nums">
                        v{{ buildInfo[row.key] }}
                      </code>
                    </div>
                    <div
                      v-if="idx === 3 || idx === 5"
                      class="my-2 border-t border-border"
                    />
                  </template>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle class="text-lg">
                  <span class="inline-flex items-center gap-2">
                    <span class="size-1.5 rounded-full bg-warning" />
                    <span class="uppercase tracking-[0.16em] text-xs text-muted-foreground">
                      {{ t('nav.categories') }}
                    </span>
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  v-if="categoriesError"
                  class="text-sm text-destructive"
                >
                  {{ t('admin.posts.loadFailed') }}
                </div>
                <div
                  v-else-if="categoriesPending"
                  class="flex flex-wrap gap-2"
                >
                  <Skeleton
                    v-for="i in 4"
                    :key="i"
                    class="h-6 w-16 rounded-full"
                  />
                </div>
                <div
                  v-else-if="categories.length"
                  class="flex flex-wrap gap-2"
                >
                  <CategoryBadge
                    v-for="category in categories"
                    :key="category.id"
                    :color="category.color ?? null"
                    :icon="category.icon ?? null"
                    :label="pickLocalized(category.name)"
                    :to="`/categories/${category.slug}`"
                  />
                </div>
                <div
                  v-else
                  class="text-sm text-muted-foreground"
                >
                  {{ t('common.noData') }}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle class="text-lg">
                  <span class="inline-flex items-center gap-2">
                    <span class="size-1.5 rounded-full bg-primary" />
                    <span class="uppercase tracking-[0.16em] text-xs text-muted-foreground">
                      {{ t('home.tagCloud') }}
                    </span>
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  v-if="tagsError"
                  class="text-sm text-destructive"
                >
                  {{ t('admin.posts.loadFailed') }}
                </div>
                <div
                  v-else-if="tagsPending"
                  class="flex flex-wrap gap-1.5"
                >
                  <Skeleton
                    v-for="i in 6"
                    :key="i"
                    class="h-6 w-14 rounded-full"
                  />
                </div>
                <div
                  v-else-if="tags.length"
                  class="flex flex-wrap gap-1.5"
                >
                  <Badge
                    v-for="tag in tags"
                    :key="tag.id"
                    variant="outline"
                    class="cursor-pointer hover:bg-accent transition-colors"
                    @click="navigateTo(`/posts?tag=${tag.slug}`)"
                  >
                    #{{ pickLocalized(tag.name) }}
                  </Badge>
                </div>
                <div
                  v-else
                  class="text-sm text-muted-foreground"
                >
                  {{ t('common.noData') }}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      <!-- ===== Newsletter / Guestbook CTA ===== -->
      <section
        :class="[
          'container pb-20 md:pb-24',
          isEditorialTheme ? editorialClassPx : ''
        ]"
        data-editorial-section="cta"
        :style="containerMaxStyle"
      >
        <Card class="rounded-2xl border-0 bg-gradient-to-br from-slate-50 via-white to-indigo-50 dark:from-slate-900 dark:via-background dark:to-indigo-950/20 shadow-soft overflow-hidden">
          <CardContent class="p-10 md:p-14 text-center max-w-2xl mx-auto relative">
            <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(99,102,241,0.08),transparent_70%)] pointer-events-none" />
            <div class="relative">
              <h2 class="font-display text-2xl md:text-3xl font-bold tracking-tight">
                {{ t('home.ctaTitle') }}
              </h2>
              <p class="text-muted-foreground mt-3 leading-relaxed">
                {{ t('home.ctaSubtitle') }}
              </p>
              <div class="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
                <Button
                  size="lg"
                  @click="navigateTo('/guestbook')"
                >
                  {{ t('home.goGuestbook') }}
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  @click="navigateTo('/about')"
                >
                  {{ t('home.goAbout') }}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </template> <!-- end: else non-minimal branch -->
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import PostCard from '~~/components/PostCard.vue'
import PostSkeleton from '~~/components/PostSkeleton.vue'
import CategoryBadge from '~~/components/CategoryBadge.vue'
import type { Category, PaginatedResponse, Post, SiteStats, Tag as BlogTag } from '~~/types/api'
import { useAPI } from '~~/composables/useApi'
import { useBingWallpaper } from '~~/composables/useBingWallpaper'
import { useSiteVersions } from '~~/composables/useSiteVersions'
import { useI18n } from 'vue-i18n'
import { ArrowRight } from '~~/lib/lucide-svg-icons'
import { MINIMAL_THEME_SLUGS } from '~~/lib/rosetta-themes'
import { watch, computed, onMounted } from 'vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const { formatDate: i18nFormatDate, pickLocalized } = useI18nHelpers()

// ===== 站点动态配置：<title>/hero/SEO/颜色都来自 settings（/api/settings + /api/config fallback）
const site = useSite()
await site.ensureLoaded()

// ===== 主题 Customizer 布局控制 =====
const ft = useFrontendTheme()
await ft.ensureLoaded()

// 极简主题（MINIMAL_THEME_SLUGS，来自 lib/rosetta-themes 单一来源）激活时，
// 首页使用 AstroPaper 风格的"纯文 Hero + 竖排文章列表"模板，
// 不请求 Bing 壁纸 / 不渲染 HUD / 不渲染 Sidebar / 不渲染 Pinned + CTA 区块。
const isMinimalTheme = computed<boolean>(() => MINIMAL_THEME_SLUGS.has(ft.slug.value || ''))
const isEditorialTheme = computed<boolean>(() => {
  const slug = ft.slug.value
  // 无主题激活 或 slug === editorial-wp-style → 默认杂志主题行为（壁纸 Hero + 多列网格）
  if (!slug) return true
  if (MINIMAL_THEME_SLUGS.has(slug)) return false
  return slug === 'editorial-wp-style'
})

// ===== Minimal Theme (AstroPaper-like): 计算属性 + 辅助函数 =====
// 宽度：minimal 用更窄的 720~780px 窄栏；其他主题走 appearance.page_width_px
const minimalNarrowWidth = 760
const layoutWidthPx = computed(() => {
  if (isMinimalTheme.value) {
    const modW = Number(ft.mods.value.layout_width)
    if (!Number.isNaN(modW) && modW >= 640 && modW <= 1100) return Math.round(modW)
    return minimalNarrowWidth
  }
  return site.appearance.value.page_width_px ?? 1200
})
// Tailwind `.container` 默认 padding 1.5rem/侧；Editorial 默认主题通过
// `!px-0` + 更窄的 inline padding 把横向留白收紧，避免居中后两侧空得夸张，
// 让杂志风内容区更接近"纸本印刷版心"的观感。
const editorialClassPx = '!px-0'
const containerMaxStyle = computed(() => {
  const max = `${layoutWidthPx.value}px`
  if (isEditorialTheme.value) {
    const pad = 'min(0.9rem, 2.6vw)'
    return {
      maxWidth: max,
      paddingLeft: pad,
      paddingRight: pad
    }
  }
  return { maxWidth: max }
})

// Editorial 默认主题：节与节之间更紧凑
const sectionTightY = computed(() => isEditorialTheme.value)

const apFeaturedLabel = computed(() => (t?.('home.latestPosts')?.toString?.() || 'Posts'))

function apFormatDate(input: string | Date | null | undefined): string {
  if (!input) return ''
  try {
    const s = i18nFormatDate(input)
    if (s) return s
  } catch {
    /* ignore */
  }
  const d = input instanceof Date ? input : new Date(String(input))
  if (Number.isNaN(d.getTime())) return ''
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function apPostExcerpt(p: Post): string {
  const raw = pickLocalized((p as Post & { excerpt?: string | Record<string, string> }).excerpt)
  if (raw) return raw.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  const content = pickLocalized(p.content || '')
  if (!content) return ''
  const plain = content.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  return plain.length > 260 ? `${plain.slice(0, 260)}…` : plain
}

// 所有可见文章（pinned 置顶先出现，再补 latest 直到最多 12 条）
const allDisplayPosts = computed<Post[]>(() => {
  const pin = pinnedPosts.value ?? []
  const latest = latestPosts.value ?? []
  const seen = new Set<number>()
  const out: Post[] = []
  for (const p of [...pin, ...latest]) {
    if (!p || p.id == null) continue
    if (seen.has(Number(p.id))) continue
    seen.add(Number(p.id))
    out.push(p)
    if (out.length >= 12) break
  }
  return out
})
const showSidebar = computed(() => ft.showSidebar.value)
const sidebarPosition = computed(() => ft.sidebarPosition.value)
// pinnedPosts 固定 3 列（feature block 展示）；latest 列表 + 侧栏区块按 theme.postsPerRow 决定"无侧栏时首页主区的文章每行多少列"。
const mainGridColsClass = computed(() => {
  if (!showSidebar.value) {
    // 无侧栏 → 主区独占整行，直接按 posts_per_row 做网格
    return 'grid-cols-1'
  }
  // 有侧栏 → 经典 2:1 分栏（主区 2 份 + 侧栏 1 份）
  return 'grid-cols-1 lg:grid-cols-3'
})
const mainColSpanClass = computed(() => showSidebar.value ? 'lg:col-span-2' : 'lg:col-span-3')
// 无侧栏模式下，latest 列表使用卡片网格（compact 变体，3/4 列）；有侧栏模式下列表保持单列。
const latestAsGrid = computed(() => !showSidebar.value)
const latestGridClass = computed(() => {
  const n = ft.postsPerRow.value
  const map: Record<number, string> = {
    1: 'grid-cols-1 gap-6',
    2: 'grid-cols-1 md:grid-cols-2 gap-6',
    3: 'grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'
  }
  return map[n] ?? map[3]
})
const pinnedGridClass = computed(() => {
  const n = ft.postsPerRow.value
  const map: Record<number, string> = {
    1: 'grid-cols-1 gap-6',
    2: 'grid-cols-1 md:grid-cols-2 gap-6',
    3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'
  }
  return map[n] ?? map[3]
})

const _heroTitle = computed(() => site.pickI18n(site.hero.value.title))
const _heroSubtitle = computed(() => site.pickI18n(site.hero.value.subtitle))
const _heroCaption = computed(() => site.pickI18n(site.hero.value.caption))
const _heroCtaText = computed(() => site.pickI18n(site.hero.value.cta_text))
const _heroCtaUrl = computed(() => String(site.hero.value.cta_url || '/posts'))

// ===== SEO（useSeo composable）=====
const homeTitle = computed(() => t?.('nav.home') || site.siteSubtitle.value || '')
const homeDescription = computed(() => site.siteDescription.value || t?.('home.heroSubtitle')?.toString?.() || undefined)
const requestURL = useRequestURL()
const origin = computed(() => requestURL.origin)
const seoOgImage = computed(() => {
  const configured = site.seo.value.og_image
  if (configured) {
    const raw = String(configured)
    if (raw.startsWith('http')) return raw
    try {
      return new URL(raw, origin.value).href
    } catch {
      return raw
    }
  }
  return undefined
})

useSeo({
  title: homeTitle,
  description: homeDescription,
  image: seoOgImage,
  type: 'website',
  url: '/'
})
useWebsiteJsonLd()

// ===== Tech versions =====
const { buildInfo } = useSiteVersions()

// Inline tech rows — no defineComponent() with runtime string-template,
// which breaks Vue runtime + Nuxt auto-injection on Windows.
interface TechRowItem { label: string, key: keyof typeof buildInfo.value, color: string }
const techRows: TechRowItem[] = [
  { label: 'Nuxt', key: 'nuxt', color: 'bg-emerald-500' },
  { label: 'Vue', key: 'vue', color: 'bg-teal-500' },
  { label: 'Vite', key: 'vite', color: 'bg-violet-500' },
  { label: 'Tailwind', key: 'tailwindcss', color: 'bg-sky-500' },
  { label: 'Pinia', key: 'pinia', color: 'bg-yellow-500' },
  { label: 'i18n', key: 'i18n', color: 'bg-rose-500' },
  { label: 'Nitro', key: 'nitro', color: 'bg-cyan-500' },
  { label: 'Rosetta', key: 'rosetta', color: 'bg-primary' }
]

// ===== Bing wallpaper =====
const {
  currentImage,
  currentIdx,
  recentDays,
  selectDay: selectWallpaper,
  fetchWallpapers,
  getBingOfficialLink
} = useBingWallpaper()

const currentWallpaper = computed(() => currentImage.value)

onMounted(() => {
  // Minimal 主题不渲染 Bing Hero，跳过壁纸请求（避免无意义的网络访问与延迟）
  if (!isMinimalTheme.value) fetchWallpapers()
})

// 并行发起 4 个独立请求：useAPI 调用即启动请求，最后统一 await 等待全部完成
// 比逐个 await 减少 3 个 RTT 的串行等待
const postsPromise = useAPI<PaginatedResponse<Post>>('/blog/posts', {
  query: { lang: locale.value, page: 1, page_size: 20 },
  key: computed(() => 'home:posts:' + locale.value)
})
const categoriesPromise = useAPI<Category[]>('/blog/categories', {
  query: { lang: locale.value },
  key: computed(() => 'home:categories:' + locale.value)
})
const tagsPromise = useAPI<BlogTag[]>('/blog/tags', {
  query: { lang: locale.value },
  key: computed(() => 'home:tags:' + locale.value)
})
const siteStatsPromise = useAPI<SiteStats>('/blog/site-stats', {
  key: 'home:site-stats'
})

const [
  { data: postsData, pending: postsPending, error: postsError, refresh: refreshPosts },
  { data: categoriesData, pending: categoriesPending, error: categoriesError, refresh: refreshCategories },
  { data: tagsData, pending: tagsPending, error: tagsError, refresh: refreshTags },
  { data: siteStats, pending: siteStatsPending, error: siteStatsError }
] = await Promise.all([postsPromise, categoriesPromise, tagsPromise, siteStatsPromise])

// 语言切换时：重新以新的 lang 参数与缓存键请求后端数据，
// 避免显示旧语言缓存，以及分类/标签本地化 JSON key 解析不更新。
watch(locale, async () => {
  await Promise.all([
    refreshPosts(),
    refreshCategories(),
    refreshTags()
  ])
})

// ===== 去重兜底：按 slug 唯一化（即使后端出现重复，也只保留第一条） =====
const posts = computed<Post[]>(() => {
  const raw = postsData.value?.items ?? []
  const seen = new Set<string>()
  const deduped: Post[] = []
  let fallbackIdx = 0
  for (const p of raw) {
    const key = p.slug ? `s:${p.slug}` : p.id ? `i:${p.id}` : `f:${fallbackIdx++}`
    if (seen.has(key)) continue
    seen.add(key)
    deduped.push(p)
  }
  return deduped
})
const pinnedPosts = computed(() => posts.value.filter(post => post.is_pinned))
const latestPosts = computed(() => posts.value.filter(post => !post.is_pinned))
// 按 slug/本地化名称去重：后端历史或 mock 数据可能返回同名重复项，
// 侧边栏分类徽章与标签云直接全量渲染会出现重复入口。
const categories = computed<Category[]>(() => {
  const seen = new Set<string>()
  const out: Category[] = []
  for (const c of categoriesData.value ?? []) {
    const key = pickLocalized(c.name).trim().toLowerCase() || c.slug
    if (!key || seen.has(key)) continue
    seen.add(key)
    out.push(c)
  }
  return out
})
const tags = computed<BlogTag[]>(() => {
  const seen = new Set<string>()
  const out: BlogTag[] = []
  for (const tg of tagsData.value ?? []) {
    const key = pickLocalized(tg.name).trim().toLowerCase() || tg.slug
    if (!key || seen.has(key)) continue
    seen.add(key)
    out.push(tg)
  }
  return out
})

// 大数字按本地化千分位格式化（如总字数 58100 → 58,100），SSR/客户端一致。
const formatStat = (value: number | undefined | null): string => {
  const n = Number(value ?? 0)
  if (!Number.isFinite(n)) return '0'
  return n.toLocaleString('en-US')
}

// ===== 补充 SEO：keywords + canonical（useSeoMeta 不处理这两项）=====
const canonical = computed(() => requestURL.href)
const siteKeywords = computed(() => site.siteKeywords.value)

useHead({
  meta: [
    { name: 'keywords', content: siteKeywords }
  ],
  link: [
    { rel: 'canonical', href: canonical }
  ]
})
</script>
