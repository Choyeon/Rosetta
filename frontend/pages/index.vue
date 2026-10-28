<!--
  首页（SSR）骨架三态：isMinimalTheme（MINIMAL_THEME_SLUGS）→ 纯竖排列表且不渲染 Hero 轮播；
  isEditorialTheme 在"无激活主题（slug=null）"时也成立，只有既非极简又非 editorial 的 slug 才走文字 Hero 杂志风。
  时序硬约束：先 await site.ensureLoaded() 再 await ft.ensureLoaded()（首帧两端同判），
  随后 6 个 useAPI 先并行发出、再统一 Promise.all await（省 5 个 RTT），缓存 key 必须带 locale 否则语言切换不刷新。
  防御性去重：posts 按 slug/id、categories/tags 按本地化名称，兜的是后端/mock 重复行；千分位统一走 lib/utils::formatCount（固定 en-US 保 SSR 一致）。
-->

<template>
  <div>
    <!-- =========================================================
         当 activeThemeSlug 为极简主题 slug → AstroPaper 风格首页
         · astro-paper-inspired  极简主题（内建，除默认主题外唯一保留）
         · 不渲染 Hero 轮播（首页不请求 /hero/slides 的渲染面）
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
          class="ap-post-list"
          :class="apPostsPerRow === 2
            ? 'grid grid-cols-1 gap-8 md:grid-cols-2 md:gap-9'
            : 'space-y-8 md:space-y-9'"
        >
          <li
            v-for="post in allDisplayPosts"
            :key="post.id"
            class="ap-post-item group"
          >
            <NuxtLink
              :to="localeHref(`/${post.slug}`)"
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
            :to="localeHref('/posts')"
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
        v-if="heroEnabled"
        :class="[
          'relative isolate overflow-hidden flex flex-col',
          isEditorialTheme
            ? 'min-h-[72vh] md:min-h-[78vh]'
            : 'min-h-[80vh] md:min-h-[86vh]',
          // 轮播图与站长自配背景都没有时的兜底渐变属于主题皮肤，定义在 editorial 主题 CSS 内
          heroHasBg ? '' : 'ed-hero-fallback'
        ]"
        aria-label="hero"
        aria-roledescription="carousel"
        data-editorial-section="hero"
        @pointerenter="heroPaused = true"
        @pointerleave="heroPaused = false"
        @focusin="heroFocusPaused = true"
        @focusout="heroFocusPaused = false"
      >
        <!-- 背景层：新旧两层都绝对定位，切换时交叉淡入（reduced-motion 下由 CSS 关闭动画） -->
        <div class="absolute inset-0 z-0">
          <Transition name="hero-xfade">
            <div
              :key="heroBgUrl || 'fallback'"
              class="absolute inset-0 bg-cover bg-center bg-no-repeat"
              :style="heroLayerStyle"
            />
          </Transition>
        </div>

        <!-- Subtle depth overlays (keep cinematics) + 幻灯片自带的可读性遮罩 -->
        <div class="absolute inset-0 bg-gradient-to-t from-black/75 via-black/18 to-black/22 pointer-events-none" />
        <div
          class="absolute inset-0 pointer-events-none transition-opacity duration-500"
          :style="heroOverlayStyle"
        />
        <!-- 非编辑部主题的横/纵两条渐变必须分两个叠放层：同一条 class 上
             写两个 bg-gradient-to-* 是覆写同一个 background-image，后者静默失效 -->
        <div
          v-if="isEditorialTheme"
          class="absolute inset-0 pointer-events-none bg-gradient-to-b from-black/18 via-black/6 to-transparent"
        />
        <template v-else>
          <div class="absolute inset-0 pointer-events-none bg-gradient-to-r from-black/50 via-black/10 to-black/20" />
          <div class="absolute inset-0 pointer-events-none bg-gradient-to-b from-black/25 via-transparent to-transparent" />
        </template>

        <!-- Hero copy：轮播项本身就是内容（热榜文章标题/摘要/链接），所以两套主题都要显示，
             不再"只当壁纸"；没有幻灯片时退回站点设置里的 hero 文案。
             布局口径：整个 section 是 flex 列，文案占 flex-1 并垂直居中，HUD 走正常文档流贴在底部。
             原先 HUD 是 `absolute bottom-0` 浮在同一个 72vh 之上，而文案只有固定 pb-28：
             窄屏 HUD 竖排成两块（缩略图 + 提示）后高度远超 112px，于是直接压在 CTA 按钮上——
             这就是手机上「hero 错乱」的成因。流内布局让两块永远不会重叠，桌面观感不变。 -->
        <div
          class="relative z-20 flex flex-1 items-center container pt-24 pb-10 md:pt-32 md:pb-14"
          :style="containerMaxStyle"
        >
          <Transition name="hero-copy">
            <div
              :key="heroSlide ? heroSlide.id : 'static'"
              :class="['flex w-full max-w-3xl flex-col', heroAlign]"
            >
              <span
                class="inline-flex w-fit items-center gap-2 rounded-full border border-white/15 bg-black/35 px-3 py-1 text-[11px] uppercase tracking-[0.22em] text-white/70 backdrop-blur-xl"
              >
                <span class="size-1.5 rounded-full bg-primary" />
                {{ site.siteTitle.value }}
              </span>
              <h1
                data-hero-title
                class="mt-5 font-display text-[1.75rem] leading-[1.15] sm:text-4xl md:text-6xl font-black tracking-tight text-white drop-shadow-[0_2px_14px_rgba(0,0,0,0.55)] [overflow-wrap:anywhere]"
              >
                {{ heroTitle }}
              </h1>
              <p
                data-hero-subtitle
                class="mt-5 max-w-2xl text-[0.95rem] md:text-xl text-white/85 leading-relaxed drop-shadow-[0_1px_6px_rgba(0,0,0,0.5)]"
              >
                {{ heroSubtitle }}
              </p>
              <div
                v-if="_heroCaption"
                class="mt-3 text-sm text-white/70"
              >
                {{ _heroCaption }}
              </div>
              <div class="mt-7 sm:mt-8 flex flex-wrap items-center gap-3">
                <NuxtLink
                  :to="localeHref(heroCtaUrl)"
                  class="inline-flex min-h-11 items-center justify-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-xl shadow-black/30 hover:bg-primary/90 active:scale-[0.98] transition-[background-color,transform] duration-200"
                >
                  {{ heroCtaText || t('home.readArticle') }}
                  <ArrowRight class="size-4" />
                </NuxtLink>
                <NuxtLink
                  :to="localeHref(heroSecondaryCtaUrl)"
                  data-testid="hero-secondary-cta"
                  class="inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-white/20 bg-white/10 px-5 py-2.5 text-sm font-semibold text-white backdrop-blur-xl hover:bg-white/20 active:scale-[0.98] transition-[background-color,transform] duration-200"
                >
                  {{ heroSecondaryCtaText }}
                </NuxtLink>
              </div>
            </div>
          </Transition>
        </div>

        <!-- Bottom HUD: 幻灯片缩略图切换（左）+ 内容来源说明（右） -->
        <div class="relative z-20">
          <div
            :class="[
              'container relative flex flex-col sm:flex-row items-stretch sm:items-end justify-between gap-3 sm:gap-4',
              isEditorialTheme ? 'pb-7 md:pb-9' : 'pb-8 md:pb-12'
            ]"
            :style="containerMaxStyle"
          >
            <div
              v-if="heroCount > 1"
              class="rounded-2xl border border-white/15 bg-black/45 backdrop-blur-xl px-3 py-3 flex flex-wrap items-center gap-2 shadow-2xl shadow-black/40"
            >
              <div class="hidden sm:flex flex-col pr-2 pl-1 border-r border-white/10 justify-center">
                <span class="text-[10px] uppercase tracking-[0.14em] text-white/60">{{ t('home.hotPicks') }}</span>
                <span class="text-xs font-medium text-white/90">{{ heroIdx + 1 }} / {{ heroCount }}</span>
              </div>
              <!-- 键盘/触屏用户没有 hover 可用：必须给一个真实的暂停开关，
                   否则焦点停在 CTA 上标题仍会每 6 秒被换走。 -->
              <button
                type="button"
                class="inline-flex min-h-8 items-center rounded-full border border-white/20 bg-white/10 px-3 text-xs font-medium text-white/90 backdrop-blur-xl transition-colors hover:bg-white/20"
                :aria-pressed="heroUserPaused"
                :aria-label="heroUserPaused ? t('home.heroResume') : t('home.heroPause')"
                :title="heroUserPaused ? t('home.heroResume') : t('home.heroPause')"
                @click="heroUserPaused = !heroUserPaused"
              >
                {{ heroUserPaused ? t('home.heroResume') : t('home.heroPause') }}
              </button>
              <div class="flex flex-wrap items-center gap-2">
                <button
                  v-for="(slide, i) in heroSlides"
                  :key="slide.id"
                  type="button"
                  class="group relative size-11 sm:size-14 rounded-lg overflow-hidden ring-1 ring-white/15 transition-all duration-200 shrink-0"
                  :class="i === heroIdx
                    ? 'ring-2 ring-white/90 scale-105 shadow-[0_0_0_2px_rgba(255,255,255,0.1),0_8px_24px_-6px_rgba(0,0,0,0.6)]'
                    : 'hover:ring-white/60 hover:scale-[1.03] opacity-85 hover:opacity-100'"
                  :aria-label="pickSlideText(slide.title) || String(i + 1)"
                  :aria-current="i === heroIdx ? 'true' : undefined"
                  :title="pickSlideText(slide.title)"
                  @click="selectHeroSlide(i)"
                >
                  <div class="absolute inset-0 z-10 flex flex-col items-center justify-center text-white">
                    <span class="text-[15px] sm:text-[17px] font-bold leading-none tracking-tight drop-shadow-[0_1px_4px_rgba(0,0,0,0.5)]">
                      {{ i + 1 }}
                    </span>
                  </div>
                  <img
                    :src="slide.media_url"
                    :alt="pickSlideText(slide.title)"
                    width="56"
                    height="56"
                    class="absolute inset-0 w-full h-full object-cover transition-opacity duration-300 ease-out z-0"
                    @error="handlePostCoverError($event, { id: slide.id })"
                  >
                </button>
              </div>
            </div>

            <div
              class="rounded-2xl border border-white/15 bg-black/45 backdrop-blur-xl px-4 py-3 max-w-lg sm:text-right text-xs sm:text-sm text-white/85 shadow-2xl shadow-black/40"
            >
              {{ t('home.heroHint') }}
            </div>
          </div>
        </div>
      </section>

      <section
        :class="[
          'container',
          sectionTightY ? 'py-8 md:py-11' : 'py-14 md:py-20'
        ]"
        data-editorial-section="pinned"
        :style="containerMaxStyle"
      >
        <div class="flex items-end justify-between mb-8 gap-6 flex-wrap">
          <!-- 节标题只出现一次：上一版把 t('posts.pinned') 同时写在 eyebrow 与 h2 上，
               屏幕上就是「置顶 / 置顶」两行重复；这里改成左侧色条 + 单一 h2。 -->
          <h2 class="flex items-center gap-3 font-display text-2xl md:text-3xl font-bold tracking-tight">
            <span
              class="inline-block h-6 w-1.5 shrink-0 rounded-full bg-warning"
              aria-hidden="true"
            />
            {{ t('posts.pinned') }}
          </h2>
          <NuxtLink
            :to="localeHref('/posts')"
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
        <PostCard
          v-else-if="singlePinnedPost"
          :post="singlePinnedPost"
          variant="feature"
        />
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
          sectionTightY ? 'pb-10 md:pb-12' : 'pb-16'
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
            <!-- 最新动态（最近 3 条）+ 全部动态入口 -->
            <ActivitySidebarCard />

            <!-- Site stats -->
            <Card>
              <CardHeader>
                <CardTitle class="flex items-center gap-2 text-sm font-semibold">
                  <span class="size-1.5 rounded-full bg-primary" />
                  {{ t('home.siteStats') }}
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
                      {{ formatCount(siteStats.total_posts) }}
                    </div>
                    <div class="text-xs text-muted-foreground mt-1">
                      {{ t('home.postsCount') }}
                    </div>
                  </div>
                  <div class="rounded-xl bg-muted/50 p-4">
                    <div class="text-2xl font-bold font-display">
                      {{ formatCount(siteStats.total_categories) }}
                    </div>
                    <div class="text-xs text-muted-foreground mt-1">
                      {{ t('home.categoriesCount') }}
                    </div>
                  </div>
                  <div class="rounded-xl bg-muted/50 p-4">
                    <div class="text-2xl font-bold font-display">
                      {{ formatCount(siteStats.total_tags) }}
                    </div>
                    <div class="text-xs text-muted-foreground mt-1">
                      {{ t('home.tagsCount') }}
                    </div>
                  </div>
                  <div class="rounded-xl bg-muted/50 p-4">
                    <div class="text-2xl font-bold font-display">
                      {{ formatCount(siteStats.total_words) }}
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
                <CardTitle class="flex items-center gap-2 text-sm font-semibold">
                  <span class="size-1.5 rounded-full bg-success" />
                  {{ t('home.techStack') }}
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
                        {{ buildInfo[row.key] ? `v${buildInfo[row.key]}` : '—' }}
                      </code>
                    </div>
                    <div
                      v-if="idx === 2 || idx === 4"
                      class="my-2 border-t border-border"
                    />
                  </template>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle class="flex items-center gap-2 text-sm font-semibold">
                  <span class="size-1.5 rounded-full bg-warning" />
                  {{ t('nav.categories') }}
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
                    :to="localeHref(`/categories/${category.slug}`)"
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
                <CardTitle class="flex items-center gap-2 text-sm font-semibold">
                  <span class="size-1.5 rounded-full bg-primary" />
                  {{ t('home.tagCloud') }}
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
                  <!-- 标签云是导航项而不是装饰徽章：用 NuxtLink 承载 Badge 的同一套
                       variant 类（根元素是 div 的 Badge 不可聚焦、也没有 Enter 激活）。 -->
                  <NuxtLink
                    v-for="tag in tags"
                    :key="tag.id"
                    :to="localeHref(`/tags/${tag.slug}`)"
                    :class="cn(badgeVariants({ variant: 'outline' }), 'hover:bg-accent transition-colors')"
                  >
                    #{{ pickLocalized(tag.name) }}
                  </NuxtLink>
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
              <h2 class="flex items-center gap-3 font-display text-2xl font-bold tracking-tight">
                <span
                  class="inline-block h-5 w-1.5 shrink-0 rounded-full bg-primary"
                  aria-hidden="true"
                />
                {{ t('home.latestPosts') }}
              </h2>
              <NuxtLink
                :to="localeHref('/posts')"
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
            <!-- 最新动态（最近 3 条）+ 全部动态入口 -->
            <ActivitySidebarCard />

            <!-- Site stats -->
            <Card>
              <CardHeader>
                <CardTitle class="flex items-center gap-2 text-sm font-semibold">
                  <span class="size-1.5 rounded-full bg-primary" />
                  {{ t('home.siteStats') }}
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
                      {{ formatCount(siteStats.total_posts) }}
                    </div>
                    <div class="text-xs text-muted-foreground mt-1">
                      {{ t('home.postsCount') }}
                    </div>
                  </div>
                  <div class="rounded-xl bg-muted/50 p-4">
                    <div class="text-2xl font-bold font-display">
                      {{ formatCount(siteStats.total_categories) }}
                    </div>
                    <div class="text-xs text-muted-foreground mt-1">
                      {{ t('home.categoriesCount') }}
                    </div>
                  </div>
                  <div class="rounded-xl bg-muted/50 p-4">
                    <div class="text-2xl font-bold font-display">
                      {{ formatCount(siteStats.total_tags) }}
                    </div>
                    <div class="text-xs text-muted-foreground mt-1">
                      {{ t('home.tagsCount') }}
                    </div>
                  </div>
                  <div class="rounded-xl bg-muted/50 p-4">
                    <div class="text-2xl font-bold font-display">
                      {{ formatCount(siteStats.total_words) }}
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
                <CardTitle class="flex items-center gap-2 text-sm font-semibold">
                  <span class="size-1.5 rounded-full bg-success" />
                  {{ t('home.techStack') }}
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
                        {{ buildInfo[row.key] ? `v${buildInfo[row.key]}` : '—' }}
                      </code>
                    </div>
                    <div
                      v-if="idx === 2 || idx === 4"
                      class="my-2 border-t border-border"
                    />
                  </template>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle class="flex items-center gap-2 text-sm font-semibold">
                  <span class="size-1.5 rounded-full bg-warning" />
                  {{ t('nav.categories') }}
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
                    :to="localeHref(`/categories/${category.slug}`)"
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
                <CardTitle class="flex items-center gap-2 text-sm font-semibold">
                  <span class="size-1.5 rounded-full bg-primary" />
                  {{ t('home.tagCloud') }}
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
                  <!-- 标签云是导航项而不是装饰徽章：用 NuxtLink 承载 Badge 的同一套
                       variant 类（根元素是 div 的 Badge 不可聚焦、也没有 Enter 激活）。 -->
                  <NuxtLink
                    v-for="tag in tags"
                    :key="tag.id"
                    :to="localeHref(`/tags/${tag.slug}`)"
                    :class="cn(badgeVariants({ variant: 'outline' }), 'hover:bg-accent transition-colors')"
                  >
                    #{{ pickLocalized(tag.name) }}
                  </NuxtLink>
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

      <!-- ===== 推荐阅读（/blog/posts/recommended；与上方列表去重后不足 2 条则整段隐藏） ===== -->
      <section
        v-if="recommendedPosts.length >= 2"
        :class="[
          'container',
          sectionTightY ? 'pb-8 md:pb-10' : 'pb-14 md:pb-20'
        ]"
        aria-labelledby="home-recommended-title"
        data-editorial-section="recommended"
        :style="containerMaxStyle"
      >
        <h2
          id="home-recommended-title"
          class="font-display text-2xl md:text-3xl font-bold tracking-tight mb-7"
        >
          {{ t('home.recommendedTitle') }}
        </h2>
        <div class="grid gap-6 md:grid-cols-2">
          <PostCard
            v-for="post in recommendedPosts"
            :key="post.slug || post.id"
            :post="post"
          />
        </div>
      </section>

      <!-- ===== Newsletter / Guestbook CTA ===== -->
      <section
        class="container pb-20 md:pb-24"
        data-editorial-section="cta"
        :style="containerMaxStyle"
      >
        <!-- 配色只走主题令牌：上一版写死 slate/indigo 渐变，换 palette（rose / amber / minimal）
             时这块仍是紫色，是全站唯一"不跟主题走"的大色块。 -->
        <Card class="rounded-2xl border-0 bg-gradient-to-br from-primary/10 via-background to-accent/70 dark:from-primary/15 dark:via-background dark:to-primary/5 shadow-soft overflow-hidden">
          <CardContent class="p-10 md:p-14 text-center max-w-2xl mx-auto relative">
            <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_center,hsl(var(--primary)/0.10),transparent_70%)] pointer-events-none" />
            <div class="relative">
              <h2 class="font-display text-2xl md:text-3xl font-bold tracking-tight">
                {{ t('home.ctaTitle') }}
              </h2>
              <p class="text-muted-foreground mt-3 leading-relaxed">
                {{ t('home.ctaSubtitle') }}
              </p>
              <div class="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
                <!-- 用真实 <a> 而不是 button+click：CTA 是页面上最显眼的站内入口，
                     中键新开 / 地址栏可复制 / 爬虫能读到，都依赖 href。 -->
                <NuxtLink
                  :to="localeHref('/guestbook')"
                  :class="buttonVariants({ size: 'lg' })"
                >
                  {{ t('home.goGuestbook') }}
                </NuxtLink>
                <NuxtLink
                  :to="localeHref('/about')"
                  :class="buttonVariants({ size: 'lg', variant: 'outline' })"
                >
                  {{ t('home.goAbout') }}
                </NuxtLink>
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
import { buttonVariants } from '~~/components/ui/button'
import { badgeVariants } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import PostCard from '~~/components/PostCard.vue'
import PostSkeleton from '~~/components/PostSkeleton.vue'
import CategoryBadge from '~~/components/CategoryBadge.vue'
import type { Category, PaginatedResponse, Post, SiteStats, Tag as BlogTag } from '~~/types/api'
import { useAPI } from '~~/composables/useApi'
import { useSiteVersions } from '~~/composables/useSiteVersions'
import { useI18n } from 'vue-i18n'
import { ArrowRight } from '~~/lib/lucide-svg-icons'
import { clampThemeWidth, MINIMAL_THEME_SLUGS } from '~~/lib/rosetta-themes'
import { toYMD } from '~~/lib/datetime'
import { handlePostCoverError } from '~~/lib/post-cover'
import { cn, formatCount } from '~~/lib/utils'
import { safeHeroHref } from '~~/lib/hero-cta'
import { computed, onMounted, onBeforeUnmount } from 'vue'

definePageMeta({ layout: 'default' })

/** GET /hero/slides 响应（backend/schemas/hero.py::HeroSlideResponse）中被首页真正消费的字段 */
interface HeroSlideApi {
  id: number
  title: string | Record<string, string> | null
  subtitle: string | Record<string, string> | null
  media_type: 'image' | 'video' | 'youtube'
  media_url: string
  overlay_opacity: number
  overlay_color: string
  cta_text?: string | Record<string, string> | null
  cta_url?: string | null
  cta_secondary_text?: string | Record<string, string> | null
  cta_secondary_url?: string | null
  text_align?: 'left' | 'center' | 'right'
}

const { t, locale } = useI18n()
const { formatDate: i18nFormatDate, pickLocalized } = useI18nHelpers()
const { localeHref } = useLocaleLink()

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
// 宽度：minimal 走 lib/rosetta-themes::clampThemeWidth 单源（640–1200，非法值兜底 880，
// 与 astro 主题 mods_schema 与 style.css --ap-layout 同一口径）；其他主题走 appearance.page_width_px
const layoutWidthPx = computed(() => {
  if (isMinimalTheme.value) return clampThemeWidth(ft.mods.value.layout_width)
  return site.appearance.value.page_width_px ?? 1200
})
// 横向留白口径：`.container` 的基座 padding 由 main.css 兜底；Editorial 只通过 inline
// maxWidth + padding 收紧版心。历史上这里写的是 `!px-0`（`padding-inline: 0 !important`）
// 想"让 inline padding 接管"，但 !important 工具类会连 inline style 一起压掉 ——
// 首页因此在手机上完全没有左右留白，卡片和标题直接贴屏幕边缘。不要再用 !px-0。
const containerMaxStyle = computed(() => {
  const max = `${layoutWidthPx.value}px`
  if (isEditorialTheme.value) {
    const pad = 'clamp(1rem, 2.6vw, 1.25rem)'
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

// astro 的 posts_per_row 枚举是 [1,2]：仅 2 走两列网格（md+ 断点），其余值（含
// MODS_DEFAULTS 的 3）一律回落到竖排单列。mods 来自已 await 的 ensureLoaded，
// SSR 与 hydrate 两端同值，不引入水合分支。
const apPostsPerRow = computed(() => (Number(ft.mods.value.posts_per_row) === 2 ? 2 : 1))

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
  return toYMD(d)
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
// 置顶区块：单篇走 feature 通栏特写，≥2 篇走网格（列数由实际条数封顶，见 pinnedGridClass）；
// latest 列表 + 侧栏区块按 theme.postsPerRow 决定"无侧栏时首页主区的文章每行多少列"。
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
  // posts_per_row 是列数上限，不是固定列数：2 篇置顶时摊满 3 列会留下一格空槽，
  // 表现为一块"缺角"横幅。条数为 0（加载骨架/空态）时仍按设置出列，占位才不跳列。
  const n = pinnedPosts.value.length
  const cap = n === 0 ? ft.postsPerRow.value : Math.min(ft.postsPerRow.value, n)
  const map: Record<number, string> = {
    1: 'grid-cols-1 gap-6',
    2: 'grid-cols-1 md:grid-cols-2 gap-6',
    3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'
  }
  return map[cap] ?? map[3]
})
// 单篇置顶走 feature 通栏特写（左大图 + 右标题摘要）：竖版卡片摊满整行会把 16:9 封面拉成巨幅，
// 而两列结构本就是为整行宽度设计的。篇数 ≥2 才回到网格。
const singlePinnedPost = computed(() => (
  pinnedPosts.value.length === 1 ? pinnedPosts.value[0] : null
))

// hero.enable：后台「启用 Hero」开关。此前整段 hero 无条件渲染，关掉开关只是存库；
// 现在关掉即不渲染这一段（首页直接从置顶/最新开始），同时不再请求 Bing 壁纸。
const heroEnabled = computed(() => site.hero.value.enable !== false)
const _heroTitle = computed(() => site.pickI18n(site.hero.value.title))
const _heroSubtitle = computed(() => site.pickI18n(site.hero.value.subtitle))
const _heroCaption = computed(() => site.pickI18n(site.hero.value.caption))
const _heroCtaText = computed(() => site.pickI18n(site.hero.value.cta_text))
const _heroCtaUrl = computed(() => String(site.hero.value.cta_url || '/posts'))

// ===== SEO（useSeo composable）=====
const homeTitle = computed(() => t?.('nav.home') || site.siteSubtitle.value || '')
const homeDescription = computed(() => site.siteDescription.value || t?.('home.heroSubtitle')?.toString?.() || undefined)
// og:image 交给 useSeo 用站点根（配置单源）绝对化：在这里用请求 Host 拼绝对地址，
// 会让首页 swr 缓存把 Host 固化成所有访客看到的 og:image 域名。
const seoOgImage = computed(() => {
  const configured = site.seo.value.og_image
  return configured ? String(configured) : undefined
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
// useSiteVersions 内部 await /health（后端版本真源）；此处先发起请求，
// 与下方 4 个首页数据请求并行，在 Promise.all 之后统一 await（见下）。
const siteVersionsPromise = useSiteVersions()

// ===== hero 分组「背景图片 URL / 背景渐变色 CSS」落地 =====
// 优先级：站长显式配的整屏背景图 > 当前轮播幻灯片媒体 > 配的渐变 > 主题兜底渐变。
// 值会写进 el.style（CSSOM 解析，非法声明被丢弃），但仍先过白名单：
// 后台输入框不是可信来源，含 ; } " 的拼接必须原样拒掉而不是塞给样式引擎。
const HERO_BG_URL_RE = /^(?:https?:\/\/|\/\/|\/)[^\s"'()\\]*$/
const HERO_BG_GRADIENT_RE = /^(?:linear|radial|conic)-gradient\([^;{}'"]*\)$/i
const heroBgImage = computed(() => {
  const raw = String(site.hero.value.bg_image || '').trim()
  return HERO_BG_URL_RE.test(raw) ? raw : ''
})
const heroBgGradient = computed(() => {
  const raw = String(site.hero.value.bg_gradient || '').trim()
  return HERO_BG_GRADIENT_RE.test(raw) ? raw : ''
})

// 并行发起 6 个独立请求：useAPI 调用即启动请求，最后统一 await 等待全部完成
// 比逐个 await 减少 5 个 RTT 的串行等待。
//
// 语言刷新的机制（AGENTS §i18n）：语言真相只有 URL 前缀，切换语言必然
// setLocale + 跳同页目标语言 URL → NuxtPage 按 path 重挂载本页 → setup 重新执行，
// 下面这些「字面量键 + 字面量查询」在重挂载时自然带上新 locale。
// 因此这里用静态键/静态查询，**不写**对 locale 的手动监听 + refresh()：
//   1. 手写 refresh 与 Nuxt useAsyncData 的 key watcher 会双发，且旧实例卸载时
//      _off() 会 abort 掉第一发——白送后端一次注定被丢弃的查询；
//   2. 静态查询若配响应式键，key watcher 那一发用的还是旧 locale 的查询参数。
const postsPromise = useAPI<PaginatedResponse<Post>>('/blog/posts', {
  query: { lang: locale.value, page: 1, page_size: 20 },
  key: `home:posts:${locale.value}`
})
// 分类键与 AppFooter / posts 列表页 / categories 页共用同一把 `blog:categories:<locale>`：
// Nuxt 按 key 全局去重，同页页脚与正文只发一条 /blog/categories（页脚在布局里常驻，
// 跨前台页面导航也直接复用，不必每页重拉）。
const categoriesPromise = useAPI<Category[]>('/blog/categories', {
  query: { lang: locale.value },
  key: `blog:categories:${locale.value}`,
  default: () => []
})
const tagsPromise = useAPI<BlogTag[]>('/blog/tags', {
  query: { lang: locale.value },
  key: `home:tags:${locale.value}`
})
const siteStatsPromise = useAPI<SiteStats>('/blog/site-stats', {
  key: 'home:site-stats'
})
// 后端推荐算法（浏览/点赞/评论/时间衰减/标签匹配）就绪但长期无消费方；
// 首页只取一屏容量，页面缓存键必须带 locale，否则切语言不刷新。
const recommendedPromise = useAPI<PaginatedResponse<Post>>('/blog/posts/recommended', {
  query: { lang: locale.value, page: 1, page_size: 8 },
  key: `home:recommended:${locale.value}`
})
// 首页横幅的内容源：后台配置的轮播优先，没有则后端用近 30 天高热度文章兜底（负 ID 虚拟项）。
// 首页横幅的职责是推荐内容而不是装饰图片，所以这里不再请求任何站外壁纸。
const heroSlidesPromise = useAPI<HeroSlideApi[]>('/hero/slides', {
  query: { lang: locale.value },
  key: `home:hero:${locale.value}`
})

const [
  { data: postsData, pending: postsPending, error: postsError },
  { data: categoriesData, pending: categoriesPending, error: categoriesError },
  { data: tagsData, pending: tagsPending, error: tagsError },
  { data: siteStats, pending: siteStatsPending, error: siteStatsError },
  { data: recommendedData },
  { data: heroSlidesData }
] = await Promise.all([
  postsPromise, categoriesPromise, tagsPromise, siteStatsPromise, recommendedPromise, heroSlidesPromise
])

// 版本信息（rosetta 来自后端 /health，其余来自 package.json / vue 运行时）
const { buildInfo } = await siteVersionsPromise

// ===== Hero 轮播状态 =====
// 后端 title/subtitle/cta_text 三种形态都要接住：虚拟兜底项已按 lang 本地化成纯字符串，
// DB 项是 JSON 字符串，管理接口也可能直接给对象。统一收敛成 pickSlideText。
const pickSlideText = (raw: HeroSlideApi['title'] | undefined): string => {
  if (raw == null) return ''
  if (typeof raw === 'string') {
    const s = raw.trim()
    if (!s.startsWith('{')) return s
    try {
      return site.pickI18n(JSON.parse(s) as Record<string, string>)
    } catch {
      return s
    }
  }
  return site.pickI18n(raw)
}

const heroSlides = computed(() => (heroSlidesData.value ?? []).filter(s => s.media_url))
const heroCount = computed(() => heroSlides.value.length)
// 首帧两端都必须是 0：autoplay 只在客户端 onMounted 之后推进，SSR 与 hydration 才字节一致。
const heroIdx = ref(0)
const heroPaused = ref(false)
// 键盘焦点进入横幅（CTA / 缩略图）也要暂停；用户手动暂停后不能被 pointerleave 自动恢复。
const heroFocusPaused = ref(false)
const heroUserPaused = ref(false)
const heroAutoplayPaused = computed(() => heroPaused.value || heroFocusPaused.value || heroUserPaused.value)
const heroSlide = computed(() => {
  const n = heroCount.value
  if (!n) return null
  return heroSlides.value[((heroIdx.value % n) + n) % n] ?? null
})
const heroMediaRaw = computed(() => heroSlide.value?.media_url || '')
// 热榜虚拟轮播的无封面回落是 picsum 外链（backend/api/hero.py::_display_cover 同口径）。
// CSS background-image 挂不上 @error，外链不可达时在客户端探一次、把它摘出 hero 背景，
// 让底层渐变接管——首页首屏不会因站外图被墙裸底。
// 过滤必须收在 heroSlideMedia 里：inertSettingSwitches.spec 钉的是
// `heroBgImage.value || heroSlideMedia.value` 这个优先级形态（自配背景压过轮播图）。
const heroFailedMedia = ref('')
function markHeroMediaFailed(url: string) {
  if (url) heroFailedMedia.value = url
}
const heroSlideMedia = computed(() =>
  heroMediaRaw.value && heroMediaRaw.value !== heroFailedMedia.value ? heroMediaRaw.value : ''
)
const heroBgUrl = computed(() => heroBgImage.value || heroSlideMedia.value)
if (import.meta.client) {
  watch(heroMediaRaw, (url) => {
    if (!url || url.startsWith('/') || url === heroFailedMedia.value) return
    const probe = new Image()
    probe.onerror = () => markHeroMediaFailed(url)
    probe.src = url
  }, { immediate: true })
}
const heroHasBg = computed(() => Boolean(heroBgUrl.value || heroBgGradient.value))
const heroLayerStyle = computed(() => {
  if (heroBgUrl.value) return { backgroundImage: `url("${heroBgUrl.value}")` }
  return heroBgGradient.value ? { background: heroBgGradient.value } : {}
})
const heroTitle = computed(() => pickSlideText(heroSlide.value?.title) || _heroTitle.value)
const heroSubtitle = computed(() => pickSlideText(heroSlide.value?.subtitle) || _heroSubtitle.value)
const heroCtaText = computed(() => pickSlideText(heroSlide.value?.cta_text) || _heroCtaText.value)
// 主/次两个 href 共用同一个闸门：缺省时保持原有回落（主＝站点设置、次＝/posts），
// 伪协议则一律回落到那个缺省，而不是原样交给 <a href>。
const heroCtaUrl = computed(() => safeHeroHref(heroSlide.value?.cta_url, _heroCtaUrl.value))
// 次按钮与主按钮同构：幻灯片自带的值优先，缺省保持历史观感（「浏览全部文章」→ /posts）。
// href 必须过 safeHeroHref：这一项写入口不止后台表单（导入 ZIP 直接写 ORM、直接打接口），
// 库里躺着 `javascript:` 时它就是这个站最显眼位置上一条可执行链接。
const heroSecondaryCtaText = computed(
  () => pickSlideText(heroSlide.value?.cta_secondary_text) || t('home.viewAll')
)
const heroSecondaryCtaUrl = computed(() => safeHeroHref(heroSlide.value?.cta_secondary_url, '/posts'))
// 幻灯片自带的遮罩强度/颜色优先（后台可读性配置）；兜底项由后端给固定 45%。
const heroOverlayStyle = computed(() => ({
  backgroundColor: heroSlide.value?.overlay_color || '#000000',
  opacity: (heroSlide.value?.overlay_opacity ?? 45) / 100
}))
const heroAlign = computed(() => {
  const a = heroSlide.value?.text_align
  return a === 'center' ? 'mx-auto items-center text-center' : a === 'right' ? 'ml-auto items-end text-right' : ''
})

let heroTimer: ReturnType<typeof setInterval> | null = null
function selectHeroSlide(i: number) {
  heroIdx.value = ((i % heroCount.value) + heroCount.value) % heroCount.value
}
onMounted(() => {
  // 单张不轮播；尊重 prefers-reduced-motion；鼠标悬停在横幅上时暂停，避免读一半被换走。
  if (heroCount.value < 2 || !heroEnabled.value) return
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
  heroTimer = setInterval(() => {
    if (!heroAutoplayPaused.value) heroIdx.value = (heroIdx.value + 1) % heroCount.value
  }, 6000)
})
onBeforeUnmount(() => {
  if (heroTimer) clearInterval(heroTimer)
  heroTimer = null
})

// Inline tech rows — no defineComponent() with runtime string-template,
// which breaks Vue runtime + Nuxt auto-injection on Windows.
interface TechRowItem { label: string, key: keyof typeof buildInfo.value, color: string }
const techRows: TechRowItem[] = [
  { label: 'Nuxt', key: 'nuxt', color: 'bg-emerald-500' },
  { label: 'Vue', key: 'vue', color: 'bg-teal-500' },
  { label: 'Tailwind', key: 'tailwindcss', color: 'bg-sky-500' },
  { label: 'Pinia', key: 'pinia', color: 'bg-yellow-500' },
  { label: 'i18n', key: 'i18n', color: 'bg-rose-500' },
  { label: 'Rosetta', key: 'rosetta', color: 'bg-primary' }
]

// 语言切换不在这页手写刷新：切换必然跳同页目标语言 URL → NuxtPage 重挂载 →
// 上方请求以新 locale 的静态键/静态查询重新发起（键形如 home:posts:en）。
// 曾经的对 locale 手动监听 + refresh() 与 Nuxt 的 key watcher 双发且第一发必被
// abort，属于纯浪费的后端查询，已删除；契约见 tests/unit/homeRecommendedSection.spec.ts。

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
// 推荐位与「最新文章」同页出现，重复条目会让首页像凑数：
// 先按本页已展示的 slug 排除，剩下的不足 2 条时整段不渲染（宁缺不空转）。
const recommendedPosts = computed<Post[]>(() => {
  const seen = new Set<string>()
  for (const p of posts.value) seen.add(p.slug ? `s:${p.slug}` : `i:${p.id}`)
  const out: Post[] = []
  for (const p of recommendedData.value?.items ?? []) {
    const key = p.slug ? `s:${p.slug}` : `i:${p.id}`
    if (seen.has(key)) continue
    seen.add(key)
    out.push(p)
    if (out.length === 4) break
  }
  return out
})
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

// ===== 补充 SEO：keywords（canonical / hreflang 由 useSeo 单源产出，不再另写一份）=====
const siteKeywords = computed(() => site.siteKeywords.value)

useHead({
  meta: [
    { name: 'keywords', content: siteKeywords }
  ]
})
</script>

<style scoped>
/* 轮播切换动效：背景交叉淡入 + 文案落位。放在页面内而不是 main.css：
   这是首页横幅的行为而非主题皮肤（AGENTS.md §3 三层 CSS 职责互斥）。 */
.hero-xfade-enter-active,
.hero-xfade-leave-active { transition: opacity 900ms ease; }
.hero-xfade-enter-from,
.hero-xfade-leave-to { opacity: 0; }
.hero-copy-enter-active { transition: opacity 420ms ease, transform 420ms cubic-bezier(0.22, 1, 0.36, 1); }
/* 两份文案同时在场做交叉淡入（不写 mode="out-in"）：out-in 会先卸载旧文案再挂新的，
   flex-1 的容器随之塌回 min-h，HUD 每 6 秒跳一次位置。
   离场那份改成绝对定位叠在原位淡出，高度只由在场的真实内容决定。 */
.hero-copy-leave-active { position: absolute; inset: 0; transition: opacity 180ms ease; }
.hero-copy-enter-from { opacity: 0; transform: translateY(14px); }
.hero-copy-leave-to { opacity: 0; }
@media (prefers-reduced-motion: reduce) {
  .hero-xfade-enter-active,
  .hero-xfade-leave-active,
  .hero-copy-enter-active,
  .hero-copy-leave-active { transition: none; }
}
</style>
