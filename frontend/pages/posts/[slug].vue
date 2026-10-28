<!--
  文章详情（SSR）：刻意不用 useAPI / useFetch 封装，直接 useAsyncData + 确定性纯字符串 cacheKey
  （post:detail:<slug>:<locale>），handler 内按 import.meta.server 选 baseURL 并手动补 Bearer/Accept-Language，
  让两端精确命中同一条 payload，不依赖 headers / 函数 toString 这类会漂移的输入。
  Hydrate 锚点：h1 无条件渲染 + 标题同步写入 useState(`post-detail-title:<slug>`)；onMounted 只刷评论/相似/TOC，
  禁止 refreshPost（客户端接管会 abort 仍在传输的 SSR 请求，表现为正文大的文章 ERR_ABORTED）。
-->

<template>
  <div>
    <!-- eslint-disable vue/no-v-html -- Vue 3；文章 HTML 已用 DOMPurify 净化 -->
    <div
      v-if="showReadingProgress"
      class="fixed top-0 left-0 right-0 z-[60] h-[3px] bg-transparent pointer-events-none"
    >
      <div
        class="h-full bg-gradient-to-r from-primary/60 via-primary to-primary/60 origin-left shadow-[0_0_8px_hsl(var(--primary)/0.5)]"
        :style="{ width: `${progress}%`, transition: 'width var(--motion-duration-fast) linear' }"
      />
    </div>
    <!-- 横向留白交给 .container 单源（main.css 的 padding-inline clamp），
         这里不再叠一层 px-4/md:px-6 —— 叠了只会让文章页比其它公开页宽窄不一。 -->
    <div class="relative container mx-auto py-16 max-w-7xl">
      <div
        class="grid grid-cols-1 gap-10 lg:gap-12"
        :class="showAside ? 'lg:grid-cols-[1fr_240px]' : ''"
      >
        <div class="min-w-0">
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink as-child>
                  <NuxtLink
                    :to="localeHref('/')"
                    class="inline-flex items-center align-middle"
                  >
                    <Globe2 class="size-3.5 mr-1 shrink-0" />
                    <span>{{ t('post.home') }}</span>
                  </NuxtLink>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbLink as-child>
                  <NuxtLink
                    :to="localeHref('/posts')"
                    class="inline-flex items-center align-middle"
                  >
                    {{ t('post.posts') }}
                  </NuxtLink>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage class="line-clamp-1">
                  {{ displayPostTitle }}
                </BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <!--
            h1 始终渲染（无条件输出）：保证 SSR → Hydrate 两端 DOM 节点结构完全一致。
            路由复用加载期间，标题会短暂显示 fallback 文本，内容替换无闪烁。
          -->
          <h1
            class="font-display text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight mt-4 leading-tight"
          >
            {{ displayPostTitle }}
          </h1>

          <!-- 作者 / 日期 / 阅读时长 / 阅读量 / 来源是主信息，字数与更新时间为次要信息。
               上一版八项挤在同一行、用「·」硬分隔，窄屏换行后每行都以「·」开头；
               这里分两层：主行不出现分隔符，次行降一级字号与对比度。 -->
          <div class="mt-6 space-y-2">
            <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
              <div class="flex min-w-0 items-center gap-2">
                <UserAvatar
                  :avatar="post?.author?.avatar"
                  :resolved-avatar-url="post?.author?.resolved_avatar_url"
                  :seed="post?.author?.username || authorName"
                  :name="authorName"
                  :title="post?.author?.title || null"
                  :size="32"
                  :show-title="true"
                />
                <span class="font-medium text-foreground">{{ authorName }}</span>
                <TitleBadge
                  v-if="post?.author?.title"
                  :title="post?.author?.title"
                  size="sm"
                />
              </div>
              <span
                class="hidden h-4 w-px bg-border sm:block"
                aria-hidden="true"
              />
              <span
                v-if="publishedAt"
                class="inline-flex items-center gap-1.5"
              >
                <CalendarDays class="size-3.5" />
                {{ formatDate(publishedAt) }}
              </span>
              <span
                v-if="showReadingTime"
                class="inline-flex items-center gap-1.5"
              >
                <Clock3 class="size-3.5" />
                {{ readingTime }} {{ t('post.minRead') }}
              </span>
              <span class="inline-flex items-center gap-1.5">
                <Eye class="size-3.5" />
                {{ views }} {{ t('post.views') }}
              </span>
              <span
                v-if="sourceView.visible"
                class="inline-flex min-w-0 items-center gap-1.5"
                data-testid="post-source"
              >
                <Link2 class="size-3.5 shrink-0" />
                {{ t('post.source') }}
                <a
                  v-if="sourceView.href"
                  :href="sourceView.href"
                  target="_blank"
                  rel="noopener noreferrer nofollow"
                  class="truncate underline underline-offset-2 transition-colors hover:text-primary"
                >{{ sourceView.text }}</a>
                <template v-else>
                  {{ sourceView.text }}
                </template>
              </span>
            </div>
            <div
              v-if="showWordCount || showUpdatedAt"
              class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground/80"
            >
              <span
                v-if="showWordCount"
                class="inline-flex items-center gap-1.5"
              >
                <FileText class="size-3.5" />
                {{ formatCount(wordCount) }} {{ t('post.words', '字') }}
              </span>
              <span
                v-if="showWordCount"
                class="inline-flex items-center gap-1.5"
              >
                <Hash class="size-3.5" />
                {{ formatCount(charCount) }} {{ t('post.chars', '字符') }}
              </span>
              <span
                v-if="showUpdatedAt"
                class="inline-flex items-center gap-1.5"
              >
                <RefreshCw class="size-3.5" />
                {{ t('post.updatedAt', '更新于') }} {{ formatDate(updatedAt) }}
              </span>
            </div>
          </div>

          <div
            v-if="coverImage"
            class="mt-10"
          >
            <img
              :src="coverImage"
              :alt="postTitle"
              class="w-full aspect-[21/9] object-cover rounded-2xl shadow-soft"
              fetchpriority="high"
              decoding="async"
              width="1200"
              height="514"
              @error="handlePostCoverError($event, post)"
            >
          </div>

          <!-- ========= 密码保护闸门：后端返回 is_password_protected=true + 空正文 → 要求输入密码 ========= -->
          <div v-if="needPassword">
            <Card class="max-w-xl mx-auto mt-10">
              <CardContent class="p-6 flex flex-col items-center gap-4 text-center">
                <Lock class="size-8 text-muted-foreground" />
                <h3 class="text-lg font-semibold">
                  {{ t('post.requiresPassword', '这篇文章需要访问密码') }}
                </h3>
                <p
                  v-if="postEncryptionHint"
                  class="text-sm text-muted-foreground"
                >
                  {{ t('post.encryptionHint', '提示：{hint}').replace('{hint}', postEncryptionHint) }}
                </p>
                <div
                  v-else
                  class="text-sm text-muted-foreground"
                >
                  {{ t('post.enterPassword', '请输入密码以阅读完整内容') }}
                </div>
                <form
                  class="flex w-full max-w-sm gap-2"
                  @submit.prevent="submitArticlePassword"
                >
                  <Input
                    v-model="articlePwdInput"
                    type="password"
                    :placeholder="t('common.password', '密码')"
                    autocomplete="off"
                    autofocus
                    class="flex-1"
                  />
                  <Button
                    type="submit"
                    :disabled="submittingArticlePassword"
                  >
                    <Check
                      v-if="!submittingArticlePassword"
                      data-icon="inline-start"
                    />
                    {{ submittingArticlePassword ? t('common.submitting', '提交中…') : t('post.unlock', '解锁') }}
                  </Button>
                </form>
                <p
                  v-if="articlePwdError"
                  class="text-xs text-destructive"
                >
                  {{ t('post.wrongPassword', '密码错误，请重试') }}
                </p>
                <button
                  v-if="articleStoredPwd"
                  type="button"
                  class="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
                  @click="clearSavedPassword"
                >
                  {{ t('post.clearSavedPassword', '清除本地已保存的密码') }}
                </button>
              </CardContent>
            </Card>
          </div>

          <div v-show="!needPassword">
            <article
              v-show="!!post"
              ref="articleEl"
              class="prose-shadcn prose-shadcn-dark mt-12"
              :style="proseStyle"
              v-html="post ? renderedContent : ''"
            />
            <ClientOnly>
              <template #fallback>
                <span class="hidden" />
              </template>
              <Skeleton
                v-if="loadingPost && !post"
                class="mt-12 h-[400px] w-full rounded-2xl"
              />
              <Alert
                v-else-if="loadError && !post"
                variant="destructive"
                class="mt-12"
              >
                <AlertTitle class="flex items-center gap-2">
                  <ShieldCheck class="size-4" />
                  {{ t('post.loadFailed', '文章加载失败') }}
                </AlertTitle>
                <AlertDescription>
                  {{ t('post.loadFailedDesc', '无法从服务器获取这篇文章，请稍后重试。') }}
                  <NuxtLink
                    :to="localeHref('/posts')"
                    class="text-primary underline underline-offset-2 ml-1"
                  >
                    {{ t('post.backToList', '返回文章列表') }}
                  </NuxtLink>
                </AlertDescription>
              </Alert>
            </ClientOnly>
          </div>

          <div
            v-if="normalizedTags.length"
            class="mt-12 flex flex-wrap gap-2"
          >
            <TagBadge
              v-for="tag in normalizedTags"
              :key="tag.id"
              :color="tag.color"
              :label="tag.name"
              :to="localeHref(`/tags/${tag.slug}`)"
              show-icon
            />
          </div>

          <!-- 互动行：点赞（真实接口）；后端未返回数据时完全隐藏，绝不显示 0 作为占位假计数 -->
          <div class="mt-8 flex items-center gap-3 flex-wrap">
            <Button
              v-if="showLikeButton"
              variant="outline"
              size="sm"
              class="group transition-colors hover:border-primary/50 hover:text-primary"
              :disabled="submittingLike"
              @click="handleLikePost"
            >
              <ThumbsUp
                data-icon="inline-start"
                class="mr-2 transition-transform duration-[var(--motion-duration-fast)] group-hover:-translate-y-0.5 group-active:scale-110"
                :class="likedByMe ? 'text-primary fill-primary/30' : ''"
              />
              <span>{{ t('post.like', '点赞') }}</span>
              <span
                v-if="likeCount > 0"
                class="ml-2 text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary tabular-nums"
              >
                {{ likeCount }}
              </span>
            </Button>

            <!-- 收藏：私有计数，后端不给未登录用户读，故不显示数字，只标"已收藏"态。
                 SSR 首帧两端都渲染未选中态（favorited 初值 false），登录用户的选中态在
                 onMounted 的 check 之后才出现 —— 不在首字节里泄漏私有状态。 -->
            <Button
              variant="outline"
              size="sm"
              class="group transition-colors hover:border-primary/50 hover:text-primary"
              :disabled="submittingFavorite"
              :aria-pressed="favorited"
              @click="handleToggleFavorite"
            >
              <Bookmark
                data-icon="inline-start"
                class="mr-2 transition-transform duration-[var(--motion-duration-fast)] group-hover:-translate-y-0.5"
                :class="favorited ? 'text-primary fill-primary/30' : ''"
              />
              <span>{{ favorited ? t('favorites.favorited') : t('favorites.add') }}</span>
            </Button>

            <!-- 分享：features.enable_share_buttons 的唯一消费点（关掉即整组不渲染）。
                 地址与 canonical 同算法（站点根 + applyLocalePrefix），不用 window.location：
                 那会把 ?query 与地址栏形态一起交给第三方站点。品牌名不翻译。 -->
            <template v-if="showShareBar">
              <Separator
                decorative
                orientation="vertical"
                class="h-6"
              />
              <Button
                v-if="canNativeShare"
                variant="outline"
                size="sm"
                class="group transition-colors hover:border-primary/50 hover:text-primary"
                @click="shareNative"
              >
                <Share2
                  data-icon="inline-start"
                  class="mr-2 transition-transform duration-[var(--motion-duration-fast)] group-hover:-translate-y-0.5"
                />
                <span>{{ t('post.share') }}</span>
              </Button>
              <a
                v-for="net in shareNetworks"
                :key="net.label"
                :href="net.href"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex h-8 items-center rounded-md border border-border/60 px-3 text-sm transition-colors hover:border-primary/50 hover:text-primary"
              >{{ net.label }}</a>
              <Button
                variant="outline"
                size="sm"
                class="group transition-colors hover:border-primary/50 hover:text-primary"
                @click="copyShareLink"
              >
                <Link2
                  data-icon="inline-start"
                  class="mr-2 transition-transform duration-[var(--motion-duration-fast)] group-hover:-translate-y-0.5"
                />
                <span>{{ t('post.copyLink') }}</span>
              </Button>
            </template>
          </div>

          <!-- ========= 作者信息卡：主题 mods show_author_box 控制（作者数据缺失时不渲染空卡） ========= -->
          <section
            v-if="showAuthorBox && post?.author"
            class="mt-10 rounded-2xl border border-border/60 bg-card/60 p-5 sm:p-6"
            :aria-label="t('post.authorBox', '作者信息')"
          >
            <p class="text-xs text-muted-foreground">
              {{ t('post.authorBoxLabel', '本文作者') }}
            </p>
            <div class="mt-3 flex flex-wrap items-center gap-3">
              <UserAvatar
                v-if="showAvatar"
                :avatar="post?.author?.avatar"
                :resolved-avatar-url="post?.author?.resolved_avatar_url"
                :seed="post?.author?.username || authorName"
                :name="authorName"
                :title="post?.author?.title || null"
                :size="48"
                :show-title="false"
              />
              <div class="min-w-0">
                <NuxtLink
                  v-if="authorUrl"
                  :to="localeHref(authorUrl)"
                  class="font-display text-lg font-semibold tracking-tight transition-colors duration-[var(--motion-duration-base)] hover:text-primary"
                  :aria-label="t('post.viewAuthorProfile', '查看作者主页')"
                >
                  {{ authorName }}
                </NuxtLink>
                <p
                  v-else
                  class="font-display text-lg font-semibold tracking-tight"
                >
                  {{ authorName }}
                </p>
                <div
                  v-if="post?.author?.title"
                  class="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground"
                >
                  <TitleBadge
                    :title="post.author.title"
                    size="sm"
                  />
                </div>
              </div>
            </div>
          </section>

          <!-- ========= 上一篇 / 下一篇：GET /blog/posts/{slug}/adjacent，缺失即不渲染 ========= -->
          <nav
            v-if="adjacent.previous || adjacent.next"
            class="mt-12 grid grid-cols-1 sm:grid-cols-2 gap-3"
            :aria-label="t('post.adjacentNav', '文章翻页导航')"
          >
            <NuxtLink
              v-if="adjacent.previous"
              :to="localeHref(`/posts/${adjacent.previous.slug}`)"
              class="group flex flex-col rounded-xl border border-border/60 bg-card/60 p-4 transition-colors duration-[var(--motion-duration-base)] hover:border-primary/40 hover:bg-accent/30"
            >
              <span class="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                <ChevronLeft class="size-3.5 transition-transform duration-[var(--motion-duration-base)] group-hover:-translate-x-0.5" />
                {{ t('post.previousPost', '上一篇') }}
              </span>
              <span class="mt-1.5 text-sm font-medium line-clamp-2 group-hover:text-primary transition-colors duration-[var(--motion-duration-base)]">
                {{ adjacent.previous.title }}
              </span>
            </NuxtLink>
            <span
              v-else
              aria-hidden="true"
              class="hidden sm:block"
            />
            <NuxtLink
              v-if="adjacent.next"
              :to="localeHref(`/posts/${adjacent.next.slug}`)"
              class="group flex flex-col items-end rounded-xl border border-border/60 bg-card/60 p-4 text-right transition-colors duration-[var(--motion-duration-base)] hover:border-primary/40 hover:bg-accent/30"
            >
              <span class="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                {{ t('post.nextPost', '下一篇') }}
                <ChevronRight class="size-3.5 transition-transform duration-[var(--motion-duration-base)] group-hover:translate-x-0.5" />
              </span>
              <span class="mt-1.5 text-sm font-medium line-clamp-2 group-hover:text-primary transition-colors duration-[var(--motion-duration-base)]">
                {{ adjacent.next.title }}
              </span>
            </NuxtLink>
          </nav>

          <!-- ========= 全局投票 MVP：Poll 与 Post 尚未建关联，此处展示全站激活中的投票 ========= -->
          <PollCard
            v-for="poll in activePolls"
            :key="poll.id"
            :poll="poll"
          />

          <Separator
            v-if="showCommentsSection"
            class="my-12"
          />

          <section v-if="showCommentsSection">
            <h3 class="font-display text-2xl font-bold tracking-tight mt-12 mb-6 flex items-center gap-2">
              <MessageSquare class="size-5 text-primary" />
              {{ t('post.comments') }} ({{ comments.length }})
            </h3>

            <Card
              v-if="canCommentForm"
              class="mb-8"
            >
              <CardContent class="p-5">
                <!-- 回复上下文横幅：replyingTo 有值时显示，X 清除回复态 -->
                <div
                  v-if="replyingTo !== null"
                  class="mb-3 flex items-center justify-between gap-2 rounded-lg bg-muted px-3 py-2 text-sm"
                >
                  <span class="min-w-0 truncate text-muted-foreground">
                    {{ t('post.replyingTo', '正在回复') }}
                    <span class="font-medium text-foreground">@{{ replyTargetName || t('post.someone', '某人') }}</span>
                  </span>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    class="shrink-0"
                    :aria-label="t('post.cancelReply', '取消回复')"
                    @click="cancelReply"
                  >
                    <X data-icon="inline-start" />
                  </Button>
                </div>
                <!-- 匿名身份字段（与留言板同构）：后台「允许访客匿名评论」打开后才会走到这里，
                     昵称在后端是硬要求（422 AUTHOR_NAME_REQUIRED），邮箱/网站可选。 -->
                <div
                  v-if="!authStore.isAuthenticated"
                  class="mb-4 grid grid-cols-1 gap-4 md:grid-cols-3"
                >
                  <Input
                    v-model="guestForm.author_name"
                    :placeholder="t('post.yourName', '昵称')"
                    :aria-label="t('post.yourName', '昵称')"
                    :disabled="submittingComment"
                    maxlength="30"
                  />
                  <Input
                    v-model="guestForm.author_email"
                    type="email"
                    :placeholder="t('post.yourEmail', '邮箱（不会公开）')"
                    :aria-label="t('post.yourEmail', '邮箱（不会公开）')"
                    :disabled="submittingComment"
                    maxlength="254"
                  />
                  <Input
                    v-model="guestForm.author_website"
                    :placeholder="t('post.yourWebsite', '网站（可选）')"
                    :aria-label="t('post.yourWebsite', '网站（可选）')"
                    :disabled="submittingComment"
                    maxlength="200"
                  />
                </div>
                <Textarea
                  ref="commentTextareaRef"
                  v-model="commentContent"
                  :maxlength="commentMaxLength"
                  :disabled="submittingComment"
                  :aria-label="replyingTo !== null ? t('post.replyPlaceholder', '回复这条评论…') : t('post.commentPlaceholder')"
                  :placeholder="replyingTo !== null ? t('post.replyPlaceholder', '回复这条评论…') : t('post.commentPlaceholder')"
                  rows="4"
                  class="resize-none"
                />
                <div class="mt-2 flex items-end justify-end gap-3 text-xs text-muted-foreground">
                  <span
                    v-if="site.comments.value.require_approval"
                    class="mr-auto"
                  >
                    {{ t('post.pendingNotice', '评论提交后需管理员审核，通过才会公开显示。') }}
                  </span>
                  <span :class="commentTooLong ? 'text-destructive' : ''">
                    {{ commentContent.length }} / {{ commentMaxLength }}
                  </span>
                </div>
                <CaptchaField
                  v-if="needCommentCaptcha"
                  ref="commentCaptchaRef"
                  :enabled="needCommentCaptcha"
                  class="mt-4"
                />
                <div class="mt-4 flex items-center justify-between gap-3">
                  <p
                    v-if="commentError"
                    class="text-sm text-destructive"
                  >
                    {{ commentError }}
                  </p>
                  <Button
                    variant="default"
                    class="ml-auto"
                    :disabled="!canSubmitComment"
                    @click="handleSubmitComment"
                  >
                    <Send
                      data-icon="inline-start"
                      class="mr-2"
                    />
                    {{ submittingComment ? t('post.submitting') : t('post.submitComment') }}
                  </Button>
                </div>
              </CardContent>
            </Card>
            <Alert
              v-else
              variant="default"
              class="mb-8"
            >
              <AlertTitle class="flex items-center gap-2">
                <ShieldCheck class="size-4" />
                {{ t('post.loginRequired') }}
              </AlertTitle>
              <AlertDescription class="flex items-center justify-between mt-3">
                <span>{{ t('post.loginToComment') }}</span>
                <Button
                  variant="default"
                  size="sm"
                  @click="navigateTo(`/login?redirect=/posts/${route.params.slug}`)"
                >
                  {{ t('post.goLogin') }}
                </Button>
              </AlertDescription>
            </Alert>

            <div class="flex flex-col gap-4">
              <template v-if="loadingComments && comments.length === 0">
                <Skeleton
                  v-for="i in 3"
                  :key="i"
                  class="h-[120px] rounded-xl"
                />
              </template>
              <template v-else-if="comments.length > 0">
                <CommentItem
                  v-for="comment in comments"
                  :key="comment.id"
                  :comment="comment"
                  :can-reply="canReply"
                  @reply="handleReply"
                />
              </template>
              <div
                v-else-if="commentsError"
                class="text-center py-10 rounded-xl border border-dashed border-destructive/40"
              >
                <MessageSquare class="size-9 mx-auto text-destructive/50 mb-3" />
                <p class="text-sm text-muted-foreground">
                  {{ t('post.commentsLoadFailed', '评论加载失败') }}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  class="mt-4"
                  @click="loadCommentsForCurrentPost"
                >
                  <RefreshCw
                    data-icon="inline-start"
                    class="mr-2"
                  />
                  {{ t('post.retry', '重试') }}
                </Button>
              </div>
              <template v-else>
                <div class="text-center py-12 rounded-xl border border-dashed">
                  <MessageSquare class="size-10 mx-auto text-muted-foreground/50 mb-3" />
                  <p class="text-muted-foreground">
                    {{ t('post.noComments') }}
                  </p>
                </div>
              </template>
            </div>
          </section>

          <!-- ========= 相关文章：GET /api/blog/posts/{post_id}/similar 真实接口，失败则为空不显示假数据 ========= -->
          <section v-if="showRelatedPosts && similarPosts.length">
            <h3 class="font-display text-2xl font-bold tracking-tight mt-16 mb-6 flex items-center gap-2">
              <Sparkles class="size-5 text-primary" />
              {{ t('post.relatedPosts', '相关文章') }}
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              <NuxtLink
                v-for="sp in similarCards"
                :key="sp.id"
                v-memo="[sp.id, sp.title, sp.excerpt, sp.cover, sp.href]"
                :to="sp.href"
                class="group rounded-2xl border border-border/60 bg-card/60 hover:bg-accent/30 transition-colors duration-[var(--motion-duration-base)] overflow-hidden"
              >
                <div
                  v-if="sp.cover"
                  class="aspect-[16/9] bg-muted overflow-hidden"
                >
                  <img
                    :src="sp.cover"
                    :alt="sp.title"
                    width="640"
                    height="427"
                    class="size-full object-cover group-hover:scale-105 transition-transform duration-[var(--motion-duration-slow)]"
                    loading="lazy"
                    @error="handlePostCoverError($event, sp.raw)"
                  >
                </div>
                <div class="p-4">
                  <h4 class="font-display font-semibold text-base tracking-tight line-clamp-2 group-hover:text-primary transition-colors duration-[var(--motion-duration-base)]">
                    {{ sp.title }}
                  </h4>
                  <p
                    v-if="sp.excerpt"
                    class="mt-2 text-xs text-muted-foreground line-clamp-2 leading-relaxed"
                  >
                    {{ sp.excerpt }}
                  </p>
                </div>
              </NuxtLink>
            </div>
          </section>
        </div>
        <aside
          v-if="showAside"
          class="hidden lg:block sticky top-24 self-start"
        >
          <div
            v-if="showToc"
            class="flex flex-col gap-3"
          >
            <h4 class="font-display text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4 flex items-center gap-2">
              <List class="size-4" /> {{ t('post.toc', '目录') }}
            </h4>
            <nav
              v-if="tocItems.length"
              class="flex flex-col gap-1.5"
            >
              <button
                v-for="item in tocItems"
                :key="item.id"
                class="block w-full text-left text-sm leading-relaxed transition-colors duration-[var(--motion-duration-fast)] rounded-md px-2.5 py-1.5 -mx-2.5"
                :class="[
                  activeId === item.id
                    ? 'text-primary font-medium bg-primary/10'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent/60',
                  item.level === 2 ? 'pl-2' : item.level === 3 ? 'pl-5' : item.level === 4 ? 'pl-8' : ''
                ]"
                @click="scrollTo(item.id)"
              >
                {{ item.text }}
              </button>
            </nav>
            <p
              v-else
              class="px-2 text-xs text-muted-foreground/70"
            >
              {{ t('post.tocEmpty', '暂无目录') }}
            </p>
          </div>
          <Card
            v-if="showReadingTime || showWordCount"
            class="mt-8 border-border/60 bg-muted/30"
          >
            <CardContent class="flex flex-col gap-2.5 p-4 text-sm">
              <div
                v-if="showReadingTime"
                class="flex items-center justify-between"
              >
                <span class="text-muted-foreground inline-flex items-center gap-1.5"><Clock3 class="size-3.5" />{{ t('post.readingTime', '阅读时间') }}</span>
                <span class="font-medium">{{ readingTime }} {{ t('post.minRead') }}</span>
              </div>
              <template v-if="showWordCount">
                <div class="flex items-center justify-between">
                  <span class="text-muted-foreground inline-flex items-center gap-1.5"><FileText class="size-3.5" />{{ t('post.words', '字数') }}</span>
                  <span class="font-medium">{{ formatCount(wordCount) }}</span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-muted-foreground inline-flex items-center gap-1.5"><Hash class="size-3.5" />{{ t('post.chars', '字符') }}</span>
                  <span class="font-medium">{{ formatCount(charCount) }}</span>
                </div>
              </template>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '~~/components/ui/breadcrumb'
import UserAvatar from '~~/components/UserAvatar.vue'
import TitleBadge from '~~/components/TitleBadge.vue'
import { Card, CardContent } from '~~/components/ui/card'
import { Input } from '~~/components/ui/input'
import { Separator } from '~~/components/ui/separator'
import { Textarea } from '~~/components/ui/textarea'
import { Button } from '~~/components/ui/button'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import TagBadge from '~~/components/TagBadge.vue'
import CommentItem from '~~/components/CommentItem.vue'
import CaptchaField from '~~/components/CaptchaField.vue'
import PollCard from '~~/components/PollCard.vue'
import { handlePostCoverError, postCoverUrl, postShareImage, POST_COVER_BANNER, POST_COVER_CARD } from '~~/lib/post-cover'
import { useAuthStore } from '~~/stores/auth'
import { useComments } from '~~/composables/useComments'
import { usePolls, type Poll } from '~~/composables/usePolls'
import { isContentMissing, useContentStatus } from '~~/composables/useContentStatus'
import { Marked } from 'marked'
import { markedHighlight } from 'marked-highlight'
// 只带 common 语言包（约 40 种：js/ts/python/go/rust/java/bash/sql/json/yaml/markdown…），
// 而不是整包 190+ 语言（实测 921 kB chunk，占整个前端产物 1/5）。
// 语言不在 common 里时 hljs.getLanguage() 返回 undefined，下面的 fallback 会走
// highlightAuto —— 仍按 common 子集自动识别，只是精度略降，不会退化成纯文本。
import hljs from 'highlight.js/lib/common'
import DOMPurify from 'isomorphic-dompurify'
import { useI18n } from 'vue-i18n'
import {
  CalendarDays,
  Clock3,
  Eye,
  MessageSquare,
  ShieldCheck,
  Send,
  Globe2,
  FileText,
  Hash,
  RefreshCw,
  List,
  Sparkles,
  ThumbsUp,
  ChevronLeft,
  ChevronRight,
  X,
  Lock,
  Check,
  Bookmark,
  Share2,
  Link2
} from '~~/lib/lucide-svg-icons'
import { applyLocalePrefix } from '~~/composables/useSeo'
import { watch, nextTick } from 'vue'
import { useReadingProgress, extractTOC, useTOCScrollSpy, estimateReadingStats } from '~~/composables/useReadingUX'
import type { TocItem } from '~~/composables/useReadingUX'
import { formatCount } from '~~/lib/utils'
import { resolvePostSource } from '~~/lib/post-source'

definePageMeta({ layout: 'default' })

const route = useRoute()
const { t, locale } = useI18n()
const authStore = useAuthStore()
const { localeHref } = useLocaleLink()

// composables 必须在 setup 顶层调用：Transition 依赖单根 + 保持上下文
const commentsAPI = useComments()

const { progress } = useReadingProgress()

/**
 * 后台设置的三组开关在这里落地（此前全是硬编码）：
 * - reading 分组：目录、字数/字符、阅读时间三处 UI
 * - comments 分组：评论区整段（enable 与后端写口闸门读同一项，关掉后接口和入口一起消失）
 * - features 分组：点赞、顶部阅读进度条
 * 值来自 useSite()（layouts/default.vue setup 期已 await ensureLoaded），
 * 因此 SSR 与客户端首帧拿到的是同一份，不产生 Hydrate 差异。
 */
const site = useSite()
const showToc = computed(() => site.reading.value.show_toc)
const showReadingTime = computed(() => site.reading.value.show_reading_time)
const showWordCount = computed(() => site.reading.value.show_word_count)
const showAside = computed(() => showToc.value || showReadingTime.value || showWordCount.value)
const showCommentsSection = computed(() => site.comments.value.enable)
const showLikeButton = computed(() => site.features.value.enable_like_button)
const showReadingProgress = computed(() => site.features.value.enable_reading_progress)
// 正文行高/字号：后台 reading 分组的两个数值项此前没有任何消费点， prose 版式完全写死。
const proseStyle = computed(() => {
  const r = site.reading.value
  return { fontSize: `${r.font_size}px`, lineHeight: String(r.line_height) }
})

interface PostDetailTag {
  id: number
  slug: string
  name: unknown
  color?: string | null
}

interface PostDetail {
  id: number
  title: unknown
  content: unknown
  cover_image?: string
  coverImage?: string
  published_at?: string
  publishedAt?: string
  created_at?: string
  updated_at?: string
  updatedAt?: string
  excerpt?: unknown
  /** 来源（列 NOT NULL，默认「原创」）与原文出处；出处可能由导入工具直接落库，
   *  未必过 schema 的严格档，所以渲染前必须自己判 scheme。 */
  source?: string | null
  source_url?: string | null
  views?: number
  views_count?: number
  author?: {
    nickname?: string
    name?: string
    username?: string
    avatar?: string
    /** 后端解析链产出的代理头像 URL，优先级高于 avatar */
    resolved_avatar_url?: string | null
    title?: {
      id?: number
      name: string
      icon?: string
      color?: string
    } | null
  }
  tags: PostDetailTag[]
  /** 后台单篇 SEO 三件套：后端按当前 lang 解析成字符串（schemas.PostLocalizedResponse 的 i18n 出口）。
   *  刻意不用 `as unknown as Record<string, unknown>` 绕开声明——那样 meta_keywords
   *  拼错了 TS 也不会响，页面只会安静地输出空 keywords。 */
  meta_title?: string | null
  meta_description?: string | null
  meta_keywords?: string | null
}

// 后端 Comment（snake_case）与 CommentItem 期望的展示结构（camelCase）存在差异，
// 页面渲染以 CommentItem 的 props 结构为准
type PostComment = {
  id: number | string
  author?: {
    id: number | string
    name: string
    avatar?: string
    email?: string
    /** 后端解析链产出的代理 URL，优先级高于 avatar（见 UserAvatar 契约） */
    resolvedAvatarUrl?: string | null
    /** 稳定的头像配色种子（用户名），不要用昵称 */
    username?: string | null
  }
  content: string
  createdAt: string
  parentId?: number | string | null
  likesCount?: number
}

const comments = ref<PostComment[]>([])
const loadingComments = ref(false)
const commentsError = ref(false)
const submittingComment = ref(false)
const commentContent = ref('')
const replyingTo = ref<number | string | null>(null)
// 评论表单的三个后台开关在这里落地（settings 分组 comments）：
// allow_guest 决定访客能不能看到输入框，max_length 决定字数上限与计数红字，
// enable_nested 决定回复按钮。此前它们只进库不进界面，访客一律被挡在"请先登录"后面。
const commentError = ref('')
const commentCaptchaRef = ref<InstanceType<typeof CaptchaField> | null>(null)
const guestForm = reactive({ author_name: '', author_email: '', author_website: '' })
const commentMaxLength = computed(() => site.comments.value.max_length)
const canCommentForm = computed(() => authStore.isAuthenticated || site.comments.value.allow_guest)
const canReply = computed(() => site.comments.value.enable_nested)
const needCommentCaptcha = computed(() => !authStore.isAuthenticated && site.features.value.enable_captcha)
const commentTooLong = computed(() => commentContent.value.length > commentMaxLength.value)
const canSubmitComment = computed(() =>
  Boolean(commentContent.value.trim())
  && !submittingComment.value
  && !commentTooLong.value
)
const tocItems = ref<TocItem[]>([])
const articleEl = ref<HTMLElement | null>(null)
const { activeId, scrollTo } = useTOCScrollSpy(() => tocItems.value)

// ========= 相似文章 & 上一篇/下一篇（真实接口，空数据=不渲染，无占位假内容）=========
/** 相似文章行：title/excerpt 与后端列表项同形（i18n dict 或纯字符串）。刻意不写成
 *  unknown——unknown 会让模板里的 pickLocalized 只能靠 `as any` 过编译，
 *  既过不了 lint，也丢掉了"字段只可能是这两种形态"这一条真实约束。 */
interface SimilarPostRow {
  id: number | string
  slug?: string
  title?: string | Record<string, string>
  cover_image?: string
  coverImage?: string
  excerpt?: string | Record<string, string>
}
interface AdjacentRef { slug: string, title: string }
const similarPosts = ref<SimilarPostRow[]>([])
const adjacent = ref<{ previous: AdjacentRef | null, next: AdjacentRef | null }>({ previous: null, next: null })
// 全局投票 MVP：Poll 未与 Post 关联，仅客户端挂载后拉一次激活中的投票；
// 密码闸门未解锁时不拉，避免把 poll 露在闸门上方。
const activePolls = ref<Poll[]>([])
const pollsAPI = usePolls()
const likeCount = ref<number>(0)
const likedByMe = ref<boolean>(false)
const submittingLike = ref<boolean>(false)

// ===== 收藏 =====
// 后端 POST /favorites 对重复收藏回 400（不是 toggle），所以按钮必须先拿到状态：
// 已收藏 → DELETE /favorites/post/{id}，未收藏 → POST /favorites。
// check 只在客户端、且有 token 时发：/account 同族，SSR 期 auth store 还没回填 token。
const favoritesAPI = useFavorites()
const toast = useToast()
const favorited = ref<boolean>(false)
const submittingFavorite = ref<boolean>(false)

async function loadFavoriteState(pid: number | string | null | undefined) {
  favorited.value = false
  if (!import.meta.client || !pid || !authStore.accessToken) return
  try {
    const res = await favoritesAPI.checkFavorites([Number(pid)], { silentToast: true })
    favorited.value = Boolean(res?.favorites?.[String(pid)]?.is_favorited)
  } catch {
    // 装饰态：读不到就按"未收藏"渲染，不打扰阅读（失败原因由登录态/网络决定）
  }
}

async function handleToggleFavorite() {
  const pid = Number(post.value?.id)
  if (!pid || submittingFavorite.value) return
  if (!authStore.isAuthenticated) {
    toast.info(t('favorites.loginRequired'))
    await navigateTo(`/login?redirect=${encodeURIComponent(route.fullPath)}`, { replace: true })
    return
  }
  submittingFavorite.value = true
  try {
    if (favorited.value) {
      await favoritesAPI.removeFavoriteByPost(pid)
      favorited.value = false
      toast.success(t('favorites.removed'))
    } else {
      await favoritesAPI.addFavorite(pid)
      favorited.value = true
      toast.success(t('favorites.added'))
    }
  } catch {
    // 失败提示由 apiFetch 统一 toast，这里只吞 rejection 防未处理异常
  } finally {
    submittingFavorite.value = false
  }
}

// 相似文章（辅助推荐，失败静默降级为空）——与上下篇、收藏状态互不依赖，三者并行发起。
async function fetchSimilarPosts(pid: number | string): Promise<SimilarPostRow[]> {
  try {
    const raw = await silentApiFetch<{ success: boolean, data?: SimilarPostRow[] }>(
      `/blog/posts/${pid}/similar`,
      { query: { lang: locale.value || 'zh', limit: 6 } }
    )
    let list: SimilarPostRow[] = []
    if (raw && typeof raw === 'object') {
      const rawObj = raw as Record<string, unknown>
      if (Array.isArray(rawObj.data)) {
        list = rawObj.data as SimilarPostRow[]
      } else if (Array.isArray(raw)) {
        list = raw as unknown as SimilarPostRow[]
      }
    }
    return list
  } catch {
    return []
  }
}

// 上一篇/下一篇（按当前 slug 查询，失败静默不渲染）
async function fetchAdjacent(): Promise<{ previous: AdjacentRef | null, next: AdjacentRef | null }> {
  try {
    const raw = await silentApiFetch<{ success: boolean, data?: { previous?: AdjacentRef | null, next?: AdjacentRef | null } }>(
      `/blog/posts/${encodeURIComponent(postSlug.value)}/adjacent`,
      { query: { lang: locale.value || 'zh' } }
    )
    const d = raw?.data
    return { previous: d?.previous ?? null, next: d?.next ?? null }
  } catch {
    return { previous: null, next: null }
  }
}

async function loadSimilarAndLikeState(pid: number | string | null | undefined) {
  if (!pid) {
    similarPosts.value = []
    adjacent.value = { previous: null, next: null }
    likeCount.value = 0
    likedByMe.value = false
    favorited.value = false
    return
  }
  // 三个请求互相独立：旧写法串行 await 白等 2 个 RTT。并行发起后统一收敛，
  // 单个失败仍走各自的 catch 降级，不影响其余两个的渲染。
  const [similar, adj] = await Promise.all([
    fetchSimilarPosts(pid),
    fetchAdjacent(),
    loadFavoriteState(pid)
  ])
  similarPosts.value = similar
  adjacent.value = adj
}

const slug = computed(() => route.params.slug as string)

// ========= 文章密码保护（sessionStorage 持久，刷新页面不用重输）=========
const ARTICLE_PASSWORD_KEY = 'rosetta:post-password'
// SSR / Hydrate 一致性：两端 setup 都初始化为空，避免 <div v-if="articleStoredPwd">
// 的 SSR 分支与客户端首次渲染的分支不一致。onMounted 再从 sessionStorage 回填。
const articleStoredPwd = ref('')
const articlePwdInput = ref('')
const articlePwdError = ref(false)
const submittingArticlePassword = ref(false)
// needPassword / postEncryptionHint 使用 computed，
// 在下方 post 定义之后声明，避免 SSR 里 watch 不重触发导致的闸门失效。

/** 用存储的密码重新拉取文章 */
async function refreshPostWithStoredPassword() {
  if (!articleStoredPwd.value) return
  try {
    const baseURL = import.meta.server ? runtimeConfig.apiBase : runtimeConfig.public.apiBase
    const headers: Record<string, string> = {
      'Accept-Language': postFetchLocaleStr,
      'X-Post-Password': articleStoredPwd.value
    }
    if (authStore.accessToken) headers.Authorization = `Bearer ${authStore.accessToken}`
    const raw = await $fetch<{ success: boolean, data: PostDetail, message?: string }>(
      `/blog/posts/${postSlug.value}`,
      {
        baseURL,
        headers,
        query: { lang: postFetchLocaleStr }
      }
    )
    const unwrap = raw && typeof raw === 'object' && 'data' in raw ? raw.data : raw as unknown as PostDetail
    postData.value = unwrap
  } catch { /* ignored — 下次循环 re-check */ }
}

async function submitArticlePassword() {
  const pwd = articlePwdInput.value.trim()
  if (!pwd) return
  submittingArticlePassword.value = true
  articlePwdError.value = false
  try {
    // 走 GET + X-Post-Password 让 blog.py 的 can_access_content 判定放行，
    // 后端返回完整正文；这条路径同时覆盖"仅密码保护（明文正文）"这一常见形态。
    articleStoredPwd.value = pwd
    if (import.meta.client && typeof sessionStorage !== 'undefined') {
      sessionStorage.setItem(ARTICLE_PASSWORD_KEY + ':' + postSlug.value, pwd)
    }
    await refreshPost()
    if (needPassword.value) {
      // 拿正文仍为空 ⇒ 密码错，回滚状态并提示
      articlePwdError.value = true
      articleStoredPwd.value = ''
      if (import.meta.client && typeof sessionStorage !== 'undefined') {
        sessionStorage.removeItem(ARTICLE_PASSWORD_KEY + ':' + postSlug.value)
      }
      return
    }
    articlePwdInput.value = ''
  } catch {
    articlePwdError.value = true
  } finally {
    submittingArticlePassword.value = false
  }
}

/** 清除已保存的密码并重试 */
function clearSavedPassword() {
  if (import.meta.client && typeof sessionStorage !== 'undefined') {
    sessionStorage.removeItem(ARTICLE_PASSWORD_KEY + ':' + postSlug.value)
  }
  articleStoredPwd.value = ''
  articlePwdInput.value = ''
  articlePwdError.value = false
  refreshPost()
}

// useFetch 的 URL/query 通过 computed 函数 / Ref 自动响应式，不再显式 watch。
// 关键点：避免 SSR 下 watch: [...] 让 useFetch 认为"只依赖 watch 触发"而跳过初始请求，
// 导致服务端不拉真实数据，页面 SSR 渲染成错误态。
const postSlug = computed(() =>
  typeof route.params.slug === 'string' ? route.params.slug : ''
)
const postFetchLocaleStr = locale.value || 'zh'

// —— SSR / Hydrate 一致性的最终稳定解法：
//    不用 useAPI/useFetch 封装，直接用 useAsyncData。
//    key 是"只与路由参数有关的纯 ASCII + 中文"的确定性字符串，
//    Nuxt 两端都能精确命中同一条 payload 缓存，不依赖 baseURL / headers /
//    函数 toString 等会变化的输入。handler 内直接 $fetch 走正确的 baseURL。
const cacheKey = `post:detail:${postSlug.value || ''}:${postFetchLocaleStr}`
const runtimeConfig = useRuntimeConfig()
const { data: postData, pending: loadingPost, error: fetchError, refresh: refreshPost }
  = useAsyncData<PostDetail>(
    cacheKey,
    () => {
      const baseURL = import.meta.server ? runtimeConfig.apiBase : runtimeConfig.public.apiBase
      const headers: Record<string, string> = {
        'Accept-Language': postFetchLocaleStr
      }
      if (authStore.accessToken) headers.Authorization = `Bearer ${authStore.accessToken}`
      // 携带存储的密码（sessionStorage），避免每次首屏都触发密码闸门
      if (articleStoredPwd.value && !import.meta.server) {
        headers['X-Post-Password'] = articleStoredPwd.value
      }
      // 解包 useAPI 返回的 { success, data, message } 统一结构
      return $fetch<{ success: boolean, data: PostDetail, message?: string }>(
        `/blog/posts/${postSlug.value}`,
        {
          baseURL,
          headers,
          query: { lang: postFetchLocaleStr }
        }
      ).then(unwrap => (unwrap && typeof unwrap === 'object' && 'data' in unwrap) ? (unwrap.data as PostDetail) : unwrap as unknown as PostDetail)
    },
    {
      // 路由复用切换时，watch slug 自动重新拉
      watch: [postSlug]
    }
  )
// 同步暴露给其他页面/组件（如 related articles）使用
const _postFetchKey = computed(() => `post:detail:${postSlug.value}:${postFetchLocaleStr}`)
void refreshPost
const post = computed(() => postData.value ?? null)
const loadError = computed(() => !!fetchError.value)
// 后端明确 404（不存在/草稿/密码保护未授权）时，本页兜底 UI 之外还要让 SSR 响应带 404，
// 否则不存在的文章是"可索引的 200 空壳"。判定与理由见 composables/useContentStatus.ts。
const postMissing = computed(() => !post.value)
// 状态码、robots、canonical 三处信号必须同源：404 响应却写着 `index, follow` +
// 自指 canonical，等于给搜索引擎两份互相矛盾的答复（口径见 AGENTS §2.3.2）。
const postNotFound = computed(() => isContentMissing(fetchError.value, postMissing.value))
useContentStatus(fetchError, postMissing)

const pickLocalized = (val: unknown): string => pickLocalizedText(val, locale.value)

// SSR → Hydration 文本一致性锚点：
// 同步写共享 useState（不是依赖 watchEffect），确保 Nuxt 在序列化 payload 时一定包含该值。
// 客户端 Hydrate 首渲染阶段：即使异步 postData 还没同步到 ref，ssrPostTitle 也已经
// 通过 payload 拿到与 SSR 完全一致的真实标题，避免 fallback slug 文本 mismatch。
const ssrPostTitle = useState<string>(
  `post-detail-title:${postSlug.value || (route.params.slug as string)}`,
  () => ''
)
const _hydrationTitleSeed = pickLocalized(postData.value?.title)
if (_hydrationTitleSeed) ssrPostTitle.value = _hydrationTitleSeed
// 路由复用时（客户端）：post 变化后同步更新共享标题，供自身或相关组件读取
watch(post, (next) => {
  const nt = pickLocalized(next?.title)
  if (nt) ssrPostTitle.value = nt
  // 同步点赞计数初始值（不伪造；后端没返回就保持 0，UI 仍不显示占位数字）
  const nxt = (next ?? {}) as Record<string, unknown>
  if (next && typeof nxt.like_count === 'number') likeCount.value = nxt.like_count
  else if (next && typeof nxt.likes === 'number') likeCount.value = nxt.likes
  else if (next && typeof nxt.likes_count === 'number') likeCount.value = nxt.likes_count
}, { immediate: true })

// 主题 Customizer 开关：layouts/default.vue 已 await ft.ensureLoaded()，
// 服务端与客户端首帧拿到同一份 mods，条件渲染不会引起 hydration mismatch。
const ft = useFrontendTheme()
const showAuthorBox = computed(() => ft.showAuthorBox.value)
const showRelatedPosts = computed(() => ft.showRelatedPosts.value)
const showAvatar = computed(() => ft.showAvatar.value)

// 密码保护闸门状态 =====
// 走 computed：SSR 里 useAsyncData 的 promise 在 setup 之后才落值，watch(post)
// 的 immediate 回调只会拿到 null，之后的赋值不会在 renderToString 前触发；
// computed 保证模板渲染时读到 post 的当前值，闸门/隐藏判定与正文渲染同源。
const postEncryptionHint = computed<string | null>(() => {
  const detail = (post.value ?? {}) as unknown as Record<string, unknown>
  // 单源是后端的 encryption_hint：这里曾写过 `?? detail.hint`，而 `hint` 这个键
  // 没有任何端点产出过（OOBE 的 hint 是另一族诊断字段），属于幽灵别名。
  const rawHint = detail.encryption_hint
  return typeof rawHint === 'string' && rawHint ? rawHint : null
})
const needPassword = computed(() => {
  if (!post.value) return false
  const detail = post.value as unknown as Record<string, unknown>
  const content = pickLocalized(post.value.content ?? '')
  return Boolean(detail.is_password_protected) && !content
})

const postTitle = computed(() => pickLocalized(post.value?.title))
const displayPostTitle = computed(() => {
  if (postTitle.value) return postTitle.value
  // Hydrate 安全回退：SSR 序列化的共享标题
  if (ssrPostTitle.value) return ssrPostTitle.value
  // 内容不存在（响应已回写 404）：标题不得由 slug 人性化"编"出一个假文章名，
  // WordPress 的 404 页标题就是"页面不存在"口径。加载中仍留空，避免闪一下。
  if (!post.value && !loadingPost.value) return t('error.notFoundTitle')
  try {
    const raw = decodeURIComponent(slug.value || '')
    return raw.replace(/-[0-9]+$/, '').replace(/-/g, ' ') || t('post.untitled', '未命名文章')
  } catch {
    return t('post.untitled', '未命名文章')
  }
})
const coverImage = computed(() => postCoverUrl(post.value, POST_COVER_BANNER))
/**
 * 分享图（og:image / twitter:image / JSON-LD）单独取值：无封面文章的展示面回落
 * 是 picsum 外链（被墙/限流即无图）与 SVG 占位（社交爬虫不渲染），两者都不能进
 * 分享卡片，一律回落站内 PNG。
 * 取值口径收在 lib/post-cover.ts::postShareImage（有单测钉住），
 * 页面本身 hero 仍用 coverImage（picsum seed 图，@error 切站内占位封面）。
 */
const seoShareImage = computed(() => postShareImage(post.value))
/** 相似文章缩略图：同样按文章标识回落默认封面。 */
const similarCover = (sp: SimilarPostRow): string => postCoverUrl(sp, POST_COVER_CARD)
// 相关文章卡片派生数据：title/excerpt/cover/href 一次算清，模板只读字段。
// 旧写法在 v-for 里每篇每次渲染调用 pickLocalized 4 次 + similarCover 2 次
// （都要遍历 i18n dict / 解析封面 URL），评论输入等任意状态变化都会全量重算。
interface SimilarCard {
  id: number | string
  title: string
  excerpt: string
  cover: string
  href: string
  /** 原始行：@error 兜底要按同一标识（id/slug）派生占位槽位，不能只有卡面字段 */
  raw: SimilarPostRow
}
const similarCards = computed<SimilarCard[]>(() =>
  similarPosts.value.map(sp => ({
    id: sp.id,
    title: pickLocalized(sp.title),
    excerpt: pickLocalized(sp.excerpt),
    cover: similarCover(sp),
    href: localeHref(`/posts/${sp.slug}`),
    raw: sp
  }))
)
const publishedAt = computed(() => post.value?.published_at || post.value?.publishedAt || post.value?.created_at || '')
// 来源一项的口径（默认值不展示 + 非 http(s) 不当链接）单源在 lib/post-source.ts
const sourceView = computed(() => resolvePostSource(post.value?.source, post.value?.source_url))
const updatedAt = computed(() => post.value?.updated_at || post.value?.updatedAt || '')
// 「更新于」标记的判定提为 computed：模板里每次重渲染（评论输入、轮播推进等）
// 都会重跑 v-if，旧写法每次新建 4 个 Date 对象；invalid 时间串按 NaN 比较为 false，
// 与旧行为一致（不显示更新标记）。
const showUpdatedAt = computed(() => {
  if (!updatedAt.value || !publishedAt.value) return false
  const updated = new Date(updatedAt.value).getTime()
  const published = new Date(publishedAt.value).getTime()
  return Number.isFinite(updated) && Number.isFinite(published) && updated > published
})
const views = computed(() => post.value?.views ?? post.value?.views_count ?? 0)
const authorName = computed(() => {
  const a = post.value?.author
  if (!a) return 'Anonymous'
  return a.nickname || a.name || a.username || 'Anonymous'
})
const authorUrl = computed(() => {
  const u = post.value?.author?.username
  return u ? `/authors/${u}` : ''
})
const normalizedTags = computed(() => {
  const tags = post.value?.tags || []
  return tags.map(tag => ({
    id: tag.id,
    slug: tag.slug,
    name: pickLocalized(tag.name),
    color: (tag.color ?? null) as string | null
  })).filter(tag => tag.id && tag.slug)
})

const seoTitle = computed(() => {
  // 后台"SEO 标题"优先；未填回落到文章 title（WordPress Yoast 同规则）。
  const mt = pickLocalized(post.value?.meta_title)
  return mt || pickLocalized(post.value?.title) || displayPostTitle.value || ''
})
const seoExcerpt = computed(() => pickLocalized(post.value?.excerpt))
// 后台"SEO 描述"优先；未填回落 excerpt；再无则剥 HTML 取正文首段。
const seoDescription = computed(() => {
  const md = pickLocalized(post.value?.meta_description)
  if (md) return md.slice(0, 180)
  if (seoExcerpt.value) return seoExcerpt.value.slice(0, 180)
  return pickLocalized(post.value?.content || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 180)
})

// ===== SEO（useSeo composable）：全部使用 ComputedRef，useSeo/useArticleJsonLd 内部响应式追踪 =====
// 从响应式 post 中安全提取未类型化的字段（API 响应结构在运行时确认）
function extractPostField<T = unknown>(post: unknown, field: string): T {
  if (typeof post !== 'object' || !post) return undefined as T
  const p = post as Record<string, unknown>
  return p[field] as T
}

// article:publisher / article:author 是 URL 字段，需要站点根；与 useSeo 内部同源
// （SSR 期缺 NUXT_PUBLIC_SITE_URL 时按请求 Host 推导），不要在这里再拼一次字面量。
const publicSiteUrl = usePublicSiteUrl()

const seoExtraMeta = computed(() => {
  const result: Array<Record<string, string>> = []
  // 时间必须过一遍有效性检查：new Date(脏字符串).toISOString() 抛 RangeError，
  // 而这段跑在 useHead 的求值路径上——一篇文章的脏时间就能让详情页整页 500。
  const iso = (val: string | undefined) => {
    if (!val) return ''
    const d = new Date(val)
    return Number.isNaN(d.getTime()) ? '' : d.toISOString()
  }
  const pa = iso(publishedAt.value)
  const ua = iso(updatedAt.value)
  if (pa) result.push({ property: 'article:published_time', content: pa })
  if (ua) result.push({ property: 'article:modified_time', content: ua })

  // Facebook/LinkedIn 的 Article 富媒体字段：section 用分类名，tag 每个标签一条
  // （OG 协议允许 article:tag 重复出现，与 <meta name="keywords"> 的逗号串是两回事）。
  const section = seoCategoryName.value
  if (section) result.push({ property: 'article:section', content: section })
  for (const tag of normalizedTags.value) {
    if (tag.name) result.push({ property: 'article:tag', content: tag.name })
  }
  // article:publisher / article:author 要的是**个人资料页 URL**，不是姓名；
  // 缺 URL 的作者（匿名）就不输出，写空串会被校验器判成 broken profile link。
  const siteRoot = publicSiteUrl.value
  if (authorUrl.value) {
    result.push({
      property: 'article:author',
      content: siteRoot ? `${siteRoot}${authorUrl.value}` : authorUrl.value
    })
    result.push({ name: 'author', content: authorName.value })
  }
  if (siteRoot) {
    result.push({ property: 'article:publisher', content: siteRoot })
  }
  return result
})
const seoCategoryName = computed(() => {
  const c = extractPostField(post.value, 'category')
  if (typeof c === 'object' && c) {
    const name = (c as Record<string, unknown>).name
    return pickLocalized(name)
  }
  return undefined
})
const seoKeywords = computed(() => {
  // 后台 SEO 关键词优先（逗号或分号分隔），叠加标签集合去重
  const raw = pickLocalized(post.value?.meta_keywords)
  const custom = (raw || '')
    .split(/[,;，；]/)
    .map(s => s.trim())
    .filter(Boolean)
  const tagNames = normalizedTags.value.map(t => t.name)
  return Array.from(new Set([...custom, ...tagNames]))
})
const seoAuthorAvatar = computed<string | undefined>(() => {
  const author = extractPostField(post.value, 'author')
  if (typeof author === 'object' && author) {
    const avatar = (author as Record<string, unknown>).avatar
    return typeof avatar === 'string' ? avatar : undefined
  }
  return undefined
})
const seoPostSlug = computed(() => String(route.params.slug))
// useSeo 内部会 asAbsolute 拼站点根；这里必须是路径形式 `/posts/xxx`，
// 直接传裸 slug 会被拼成 `<site>/<slug>`（丢掉 /posts 段）。
const seoPostPath = computed(() => `/posts/${seoPostSlug.value}`)

useSeo({
  title: seoTitle,
  description: seoDescription,
  image: seoShareImage,
  imageAlt: seoTitle,
  type: 'article',
  url: seoPostPath,
  // 不存在的文章：noindex 会同时抑制 canonical 与 hreflang 集群（useSeo 内部口径），
  // 于是响应码 / robots / canonical 三条信号一致。
  noindex: postNotFound,
  extraMeta: seoExtraMeta
})

useArticleJsonLd({
  // 缺失时把 slug 交给空串：useArticleJsonLd 的 `if (!slug) return { script: [] }`
  // 是它自带的抑制口，不给 404 页挂一份 mainEntityOfPage 指向不存在 URL 的 Article。
  slug: computed(() => (postNotFound.value ? '' : seoPostSlug.value)),
  title: seoTitle,
  headline: seoTitle,
  description: seoDescription,
  // JSON-LD ImageObject 走分享图口径：无封面时是站内 PNG，不给爬虫外链/SVG。
  cover: seoShareImage,
  publishedAt,
  updatedAt,
  // 始终传入 author 对象，内部字段均为 ComputedRef（响应式）。
  // 当 author 未加载时 name/avatar 回退为空，useArticleJsonLd 会自动跳过 name 为空的 author。
  // url 有值时 JSON-LD 的 @graph 会产出独立 Person 节点（BlogPosting.author 变 @id 引用），
  // 无值时退化为内联对象——与旧单对象输出的防御口径一致。
  author: {
    name: authorName,
    url: authorUrl,
    avatar: seoAuthorAvatar
  },
  category: seoCategoryName,
  // 面包屑的分类一跳落在真实路由 pages/categories/[slug].vue（按 slug 解析）；
  // seoCategoryName 是本地化名称，与 slug 不保证相等，必须显式给路径。
  categoryPath: computed(() => {
    const c = extractPostField(post.value, 'category')
    const s = typeof c === 'object' && c
      ? (c as Record<string, unknown>).slug
      : undefined
    return typeof s === 'string' && s ? `/categories/${s}` : undefined
  }),
  keywords: seoKeywords
})

// ===== 分享条：features.enable_share_buttons 的唯一消费点 =====
// 分享地址走 canonical 同款算法（站点根 + applyLocalePrefix），不用 window.location.href：
// 那会把 ?query 一起递给第三方，且在 SSR 期根本不存在。
const showShareBar = computed(() => site.features.value.enable_share_buttons !== false)
const shareUrl = computed(() => {
  const path = applyLocalePrefix(seoPostPath.value, locale.value || 'zh')
  const base = publicSiteUrl.value.replace(/\/$/, '')
  return base ? `${base}${path}` : path
})
const shareTitleText = computed(() => String(seoTitle.value ?? ''))
const shareNetworks = computed(() => {
  const u = encodeURIComponent(shareUrl.value)
  const title = encodeURIComponent(shareTitleText.value)
  return [
    { label: 'X', href: `https://twitter.com/intent/tweet?url=${u}&text=${title}` },
    { label: '微博', href: `https://service.weibo.com/share/share.php?url=${u}&title=${title}` },
    { label: 'Telegram', href: `https://t.me/share/url?url=${u}&text=${title}` }
  ]
})
// Web Share API 只在安全上下文的移动端存在；首帧两端都是 false，挂载后再开，
// 避免 SSR 与客户端的按钮数量对不上（同一口径见 §2.4 首渲染字节级一致）。
const canNativeShare = ref(false)
onMounted(() => {
  canNativeShare.value = typeof navigator.share === 'function'
})

async function shareNative() {
  try {
    await navigator.share({ title: shareTitleText.value, url: shareUrl.value })
  } catch (e) {
    // 用户点了"取消"同样是 reject（AbortError），那不是故障，不该弹错误条
    if ((e as Error)?.name !== 'AbortError') toast.error(t('post.shareFailed'))
  }
}

async function copyShareLink() {
  const url = shareUrl.value
  try {
    await navigator.clipboard.writeText(url)
    toast.success(t('post.linkCopied'))
    return
  } catch {
    // Clipboard API 只在安全上下文可用（http 内网直连下 navigator.clipboard 是 undefined，
    // 这里连读都会抛），退回临时 textarea，让"复制链接"在两种环境里都真的能复制。
  }
  const area = document.createElement('textarea')
  area.value = url
  area.setAttribute('readonly', 'true')
  area.className = 'fixed left-[-9999px] opacity-0'
  document.body.appendChild(area)
  area.select()
  const copied = document.execCommand('copy')
  area.remove()
  if (copied) toast.success(t('post.linkCopied'))
  else toast.error(t('post.copyFailed'))
}

const escapeHtml = (value: string): string => value
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll('\'', '&#39;')

const stripLeadingFenceFromCode = (code: string, language: string): string => {
  const lines = code.split(/\r?\n/)
  const firstLine = lines[0] ?? ''
  const tailLine = lines[lines.length - 1] ?? ''
  const fenceRe = /^\s*```+\s*([\w+-]*)\s*$/
  const closingFenceRe = /^\s*```+\s*$/
  if (lines.length >= 2 && fenceRe.test(firstLine)) {
    const m = firstLine.match(fenceRe)
    const firstLang = (m?.[1] || '').toLowerCase()
    if (!language || firstLang === language || !firstLang) {
      lines.shift()
    }
  }
  if (lines.length && closingFenceRe.test(tailLine)) {
    lines.pop()
  }
  return lines.join('\n')
}

const normalizeMarkdownFences = (raw: string): string => raw
  .replace(/\r\n/g, '\n')
  .replace(/(^|\n)```(\w*)\n```\w*\n/g, '$1```$2\n')

const hljsSanitizeConfig: Parameters<typeof DOMPurify.sanitize>[1] = (() => {
  // isomorphic-dompurify 在 SSR 与客户端两端行为一致，避免 hydration mismatch
  // 显式放行 hljs 高亮 <span class="hljs-*"> 及其它 inline 语义标签，
  // 避免默认严格模式把 token span 全部剥离，导致只剩纯文本代码块。
  const hljsClassRe = /^(hljs|hljs-[a-z0-9_-]+|language-[a-z0-9_-]+)$/i
  return {
    ADD_TAGS: ['pre', 'code', 'span', 'mark', 'kbd', 'samp', 'var'],
    ADD_ATTR: ['class'],
    ALLOW_UNKNOWN_PROTOCOLS: false,
    WHOLE_DOCUMENT: false,
    FORBID_ATTR: ['style', 'onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur'],
    FORBID_TAGS: ['style', 'script', 'iframe', 'object', 'embed', 'form', 'input', 'button', 'link', 'meta'],
    IN_PLACE: true,
    SANITIZE_DOM: true,
    /** 只允许 class 命中 hljs/language-* 白名单，防止任意样式注入 */

    HOOKS: {
      uponSanitizeElement(node: Element, _data: unknown) {
        if (node.tagName === 'SPAN' || node.tagName === 'CODE' || node.tagName === 'PRE') {
          const cls = node.getAttribute('class') || ''
          if (!cls) return
          const allowed = cls
            .split(/\s+/)
            .filter(c => hljsClassRe.test(c))
            .join(' ')
          if (allowed) node.setAttribute('class', allowed)
          else node.removeAttribute('class')
        }
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as Record<string, any>
  } as Parameters<typeof DOMPurify.sanitize>[1]
})()

// 高亮单一来源：只使用 marked-highlight 插件做一次 hljs。
// 自定义 renderer.code 仅负责剥 fence 与包 <pre><code>，不再重复调用 hljs，避免双重转义/重复 class。
const mdRenderer = new Marked(
  {
    renderer: {
      html({ text }) {
        return escapeHtml(text)
      },
      code({ text, lang, escaped }) {
        const rawLanguage = (lang || '').trim().toLowerCase()
        const cleaned = stripLeadingFenceFromCode(text, rawLanguage)
        const code = escaped ? cleaned : escapeHtml(cleaned)
        const langClass = rawLanguage && hljs.getLanguage(rawLanguage) ? ` hljs language-${rawLanguage}` : ' hljs'
        return `<pre><code class="${langClass.trim()}">${code}</code></pre>`
      }
    }
  },
  markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code: string, lang: string) {
      const language = (lang || '').trim().toLowerCase()
      const cleaned = stripLeadingFenceFromCode(code, language)
      if (!language || !hljs.getLanguage(language)) {
        try {
          return hljs.highlightAuto(cleaned).value
        } catch {
          return escapeHtml(cleaned)
        }
      }
      try {
        return hljs.highlight(cleaned, { language, ignoreIllegals: true }).value
      } catch {
        return escapeHtml(cleaned)
      }
    }
  })
)

const renderedContent = computed(() => {
  if (!post.value?.content) return ''
  let raw = normalizeMarkdownFences(pickLocalized(post.value.content))
  // 插件会在正文里追加 HTML 注释（seo-toolkit 的 JSON-LD 占位符就是一条）。
  // 注释在 HTML 里本来不可见，但 renderer.html 走的是转义分支，注释会被当作普通文本
  // 原样显示成 `<!-- ... -->`。解析前直接剥掉，行为与浏览器一致。
  raw = raw.replace(/<!--[\s\S]*?-->/g, '')
  // 剥离正文开头与页面 H1 重复的标题：部分文章 Markdown 首行即 `# 标题`，
  // 而模板已单独渲染 H1，直接转换会导致标题出现两次。
  // 仅当首行 H1 文本与文章标题匹配时才移除，避免误删正文中真正的一级标题。
  const leading = /^\s{0,3}#\s+(.+?)\s*#*\s*(?:\r?\n|$)/.exec(raw)
  if (leading) {
    const headingText = (leading[1] ?? '').trim()
    const want = postTitle.value.trim()
    if (want && (headingText === want || headingText.includes(want) || want.includes(headingText))) {
      raw = raw.slice((leading[0] ?? '').length).replace(/^\s+/, '')
    }
  }
  try {
    const html = mdRenderer.parse(raw) as string
    return DOMPurify.sanitize(html, hljsSanitizeConfig)
  } catch (e) {
    console.error('Markdown parse error:', e)
    const fallback = escapeHtml(raw)
    return DOMPurify.sanitize(fallback, hljsSanitizeConfig)
  }
})

const readingStats = computed(() => {
  const content = pickLocalized(post.value?.content)
  const localeStr = (locale.value || 'zh').startsWith('zh') ? 'zh' : (locale.value === 'ja' ? 'ja' : 'en')
  return estimateReadingStats(content, localeStr)
})
const readingTime = computed(() => readingStats.value.minutes)
const wordCount = computed(() => readingStats.value.words)
const charCount = computed(() => readingStats.value.chars)

// canonical / hreflang / og:url 全部由 useSeo 单源产出（语言感知 + 站点根绝对化）。
// 这里曾经另起一个 useHead 用 requestURL.href 再写一遍 canonical：同一个 rel 两处来源
// 的结果是 unhead 合并后只剩一条，留哪条取决于注入顺序，改不动也测不准。

// 文章详情的日期与列表卡片同一个口径：`useI18nHelpers().formatDate` 用静态月表拼接，
// SSR 与浏览器两端字节级一致；原先这里用 `toLocaleDateString(locale)`，同一篇文章
// 在列表上是 "Nov 5, 2026"、点进详情页变成 "November 5, 2026"，而且 Node 侧 Intl 数据
// 版本与访客浏览器不一致时，这个差异会直接变成 Hydration node mismatch。
const { formatDate } = useI18nHelpers()

// ===== 评论：后端是扁平 snake_case（author_name / author_avatar / resolved_avatar_url /
//      qq / github），CommentItem 期望 camelCase 的 author 对象。此前直接 `as unknown as`
//      硬断言 → author 恒 undefined → 评论昵称一律 Anonymous、头像一律默认字母色块，
//      与同一作者在其他位置的头像不一致（2026-10-01 修）。统一走这里做投影。
/**
 * 评论行的输入形态：`commentsAPI.comments` 的内部类型与后端 snake_case 并不同源，
 * 字段一律按 unknown 处理、在 normalizeComment 里逐字段收敛（禁止 any 穿透——
 * 一旦穿透，脏字段会直接落到 CommentItem 的 props 上）。
 */
type CommentRaw = Record<string, unknown>

const rawText = (v: unknown, fallback = ''): string =>
  typeof v === 'string' && v !== '' ? v : fallback
const rawId = (v: unknown): number | string | undefined =>
  typeof v === 'number' || typeof v === 'string' ? v : undefined
const rawCount = (v: unknown): number => {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

const normalizeComment = (raw: CommentRaw): PostComment => {
  const name = rawText(raw.author_name) || rawText(raw.authorName) || 'Anonymous'
  const id = rawId(raw.id)
  return {
    id: id ?? 0,
    author: {
      id: rawId(raw.user_id) ?? rawId(raw.userId) ?? id ?? 0,
      name,
      // 头像优先级与 UserAvatar 契约一致：解析后的代理 URL > 原始 avatar 列。
      resolvedAvatarUrl: rawText(raw.resolved_avatar_url) || rawText(raw.resolvedAvatarUrl) || null,
      avatar: rawText(raw.author_avatar) || rawText(raw.authorAvatar),
      email: rawText(raw.author_email) || rawText(raw.authorEmail),
      username: rawText(raw.username) || rawText(raw.github) || name
    },
    content: rawText(raw.content),
    createdAt: rawText(raw.created_at) || rawText(raw.createdAt),
    parentId: rawId(raw.parent_id) ?? rawId(raw.parentId) ?? null,
    likesCount: rawCount(raw.likes_count ?? raw.likesCount)
  }
}

// 首屏由 SSR + payload 注入文章详情；这里只刷新评论。
// 注意：不要在 onMounted 里 refresh() 文章本身——客户端接管时会取消 SSR 发起的、仍在传输中的请求，
// 浏览器 Network 面板里就会看到 net::ERR_ABORTED（尤其是正文较大的中/长文）。
const loadCommentsForCurrentPost = async () => {
  if (!import.meta.client) return
  loadingComments.value = true
  commentsError.value = false
  try {
    if (post.value?.id && commentsAPI.fetchComments) {
      await commentsAPI.fetchComments(post.value.id)
      comments.value = ((commentsAPI.comments?.value || []) as unknown as CommentRaw[]).map(normalizeComment)
    } else {
      comments.value = []
    }
  } catch (e) {
    console.warn('[post detail] comments fetch error:', e)
    commentsError.value = true
  } finally {
    loadingComments.value = false
  }
}
onMounted(async () => {
  // Hydrate 之后：从 sessionStorage 回填密码（SSR 拿不到，setup 只能初始化为空）。
  if (typeof sessionStorage !== 'undefined') {
    const saved = sessionStorage.getItem(ARTICLE_PASSWORD_KEY + ':' + postSlug.value) || ''
    if (saved) {
      articleStoredPwd.value = saved
      articlePwdInput.value = saved
    }
  }
  // 若 SSR 期没有 sessionStorage（服务端拿不到密码）而客户端本地存有旧密码，
  // 则用带 X-Post-Password 的一次独立请求把解锁正文换回页面，避免重输。
  if (articleStoredPwd.value && needPassword.value) {
    void refreshPostWithStoredPassword()
  }
  // 投票：闸门未解锁时不拉，防止 poll 内容出现在密码框上方。
  // 带 post_id 是必需的——不传就退化成"全站投票"，别的文章的专属投票会串到本页来。
  // 与评论/相似/TOC 互不依赖，先拿到 promise 再并入下面的 Promise.all，
  // 不单独 await 一个 RTT（旧写法让整页 hydration 后的收尾多等一轮往返）。
  const pollsPromise = needPassword.value ? null : pollsAPI.fetchActivePolls(3, post.value?.id ?? null)
  // 三个独立任务并行执行：评论、相似文章、TOC 重建互不依赖
  await Promise.all([
    loadCommentsForCurrentPost(),
    loadSimilarAndLikeState(post.value?.id),
    rebuildTOC(),
    pollsPromise
  ])
  if (pollsPromise) activePolls.value = await pollsPromise
  if (import.meta.client && typeof window !== 'undefined') {
    // 字体 / 懒加载图片导致布局变化后的兜底刷新（3 秒内再补几次）。
    const retries = [400, 1200, 3000]
    retries.forEach(delay => setTimeout(() => void rebuildTOC(), delay))
  }
})
// 密码解锁后 needPassword 由 true→false，此时才允许拉本页的投票卡片。
watch(needPassword, async (locked, prev) => {
  if (prev && !locked && !activePolls.value.length) {
    activePolls.value = await pollsAPI.fetchActivePolls(3, post.value?.id ?? null)
  }
})
onActivated(async () => {
  await Promise.all([
    loadCommentsForCurrentPost(),
    loadSimilarAndLikeState(post.value?.id)
  ])
})
/**
 * 换文章时重取本页投票。
 * 投票按 post_id 绑定后，"上一篇的专属投票"留在卡片位上就是新的串台缺陷——
 * 这个页面在 keep-alive 下跨文章复用组件实例，而 watch 不带 immediate，
 * 首屏仍由 onMounted 那条 promise 链负责。
 */
const reloadActivePolls = async () => {
  if (needPassword.value) {
    activePolls.value = []
    return
  }
  activePolls.value = await pollsAPI.fetchActivePolls(3, post.value?.id ?? null)
}

watch([slug, locale, () => post.value?.id], async () => {
  await Promise.all([
    loadCommentsForCurrentPost(),
    loadSimilarAndLikeState(post.value?.id),
    reloadActivePolls()
  ])
})

/**
 * TOC 重建：
 *  - 只在客户端执行（SSR 没有 DOM，extractTOC 只能取空）
 *  - 依赖"文章对象 + Markdown 渲染字符串 + 不是在 pending loading"三个条件
 *  - v-html 注入后需要 nextTick（Vue 更新真实 DOM）再等待一次 rAF + 16ms（浏览器 layout）
 *  - 如果文章正文里含有 <img>，需要等所有 <img> onload 再重算一次，
 *    否则 offsetTop 会因为图片加载前高度为 0 而集体偏上，导致目录项激活锚点全部错位。
 */
const rebuildTOC = async () => {
  if (!import.meta.client) return
  if (loadingPost.value || !post.value) return
  await nextTick()
  // 等一次渲染帧 + 一帧余量，让 hljs 代码块尺寸 / 字体 / 图片占位先进入 layout。
  await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
  const el = articleEl.value ?? (document.querySelector('article.prose-shadcn') as HTMLElement | null)
  if (!el) return
  articleEl.value = el
  tocItems.value = extractTOC(el, site.reading.value.toc_depth)

  // 若文章正文有 <img>：全部解码完再更新一次 TOC 位置（scroll-spy 内部使用 realOffset）。
  const imgs = Array.from(el.querySelectorAll<HTMLImageElement>('img'))
  if (imgs.length) {
    await Promise.all(
      imgs.map((img) => {
        if (img.complete && (img.naturalWidth > 0 || img.src.startsWith('data:'))) return
        return new Promise<void>((resolve) => {
          const done = () => {
            resolve()
            img.removeEventListener('load', done)
            img.removeEventListener('error', done)
          }
          img.addEventListener('load', done, { once: true })
          img.addEventListener('error', done, { once: true })
        })
      })
    )
    // scroll-spy update() 会在下次 scroll/resize/下帧通过 realOffset 重新取到新位置；
    // 这里主动跑一次，保证首次渲染后滚动高亮立即正确。
    const list = tocItems.value
    if (list.length) {
      // 触发一次刷新 activeId：realOffset 是 scroll-spy 内部函数，外部通过 scrollTo 或滚动事件触发；
      // 我们手动触发 scroll 即可（不实际滚动，只是让 spy 的 update 跑一次）。
      window.dispatchEvent(new Event('scroll'))
    }
  }
}

watch(
  [() => post.value, () => renderedContent.value, () => loadingPost.value, () => locale.value],
  rebuildTOC,
  // 不使用 immediate: true。SSR 没有 DOM，我们在 onMounted 里手动触发一次。
  { flush: 'post' }
)

const handleSubmitComment = async () => {
  const content = commentContent.value.trim()
  if (!post.value?.id || !content) return
  if (content.length > commentMaxLength.value) {
    commentError.value = String(t('post.commentTooLong', '评论超出长度限制'))
    return
  }
  if (!authStore.isAuthenticated && !guestForm.author_name.trim()) {
    commentError.value = String(t('post.nicknameRequired', '请填写昵称'))
    return
  }
  if (needCommentCaptcha.value && !commentCaptchaRef.value?.valid()) {
    commentError.value = String(t('captcha.required', '请填写验证码'))
    return
  }
  submittingComment.value = true
  commentError.value = ''
  try {
    const pid = (replyingTo.value == null) ? undefined : Number(replyingTo.value)
    await commentsAPI.createComment(post.value.id, {
      content,
      parent_id: pid,
      author_name: guestForm.author_name.trim() || undefined,
      author_email: guestForm.author_email.trim() || undefined,
      author_website: guestForm.author_website.trim() || undefined,
      ...(commentCaptchaRef.value?.payload() ?? {})
    }, articleStoredPwd.value ? { 'X-Post-Password': articleStoredPwd.value } : undefined)
    commentContent.value = ''
    replyingTo.value = null
    toast.success(String(t(site.comments.value.require_approval
      ? 'post.commentPending'
      : 'post.commentSubmitted')))
    if (commentsAPI.fetchComments) {
      await commentsAPI.fetchComments(post.value.id)
      comments.value = ((commentsAPI.comments?.value || []) as unknown as CommentRaw[]).map(normalizeComment)
    }
  } catch (err: unknown) {
    const e = (err ?? {}) as Record<string, unknown>
    const data = (e.data ?? {}) as Record<string, unknown>
    const detail = (data.detail ?? {}) as Record<string, unknown>
    const msg
      = (typeof data.message === 'string' && data.message)
        || (typeof detail.message === 'string' && detail.message)
        || (typeof e.message === 'string' && e.message)
        || String(t('post.commentFailed', '评论提交失败，请稍后再试'))
    commentError.value = String(msg)
    // apiFetch 抛错前已统一 toast，这里只补行内错误，不重复弹（AGENTS §7.2 双报红线）。
  } finally {
    // 验证码答案一次性：无论成败都可能已被服务端 consume，必须换一张。
    if (needCommentCaptcha.value) commentCaptchaRef.value?.refresh()
    submittingComment.value = false
  }
}

const commentTextareaRef = ref<InstanceType<typeof Textarea> | null>(null)

const handleReply = (commentId: number | string) => {
  replyingTo.value = commentId
  const inst = commentTextareaRef.value as { $el?: HTMLElement } | null
  const el = inst?.$el ?? null
  el?.focus()
  el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

// 回复横幅：显示被回复评论者昵称；X / 提交成功后清除 replyingTo
const replyTargetName = computed(() => {
  if (replyingTo.value === null) return ''
  const target = comments.value.find(c => String(c.id) === String(replyingTo.value))
  return String(target?.author?.name ?? '')
})
const cancelReply = () => {
  replyingTo.value = null
}

// 文章点赞：POST /api/blog/posts/{post_id}/like（后端对匿名也计数；失败由 apiFetch 统一 toast）
const handleLikePost = async () => {
  if (!post.value?.id || submittingLike.value) return
  submittingLike.value = true
  try {
    const raw = await apiFetch<{ success: boolean, data?: { liked?: boolean, like_count?: number, likes?: number } }>(
      `/blog/posts/${post.value.id}/like`,
      { method: 'POST' }
    )
    type LikePayload = { liked?: boolean, like_count?: number, likes?: number }
    const extractLikePayload = (r: unknown): LikePayload => {
      if (!r || typeof r !== 'object') return {}
      const obj = r as Record<string, unknown>
      if ('data' in obj && obj.data && typeof obj.data === 'object') {
        return obj.data as LikePayload
      }
      return obj as LikePayload
    }
    const payload = extractLikePayload(raw)
    if (typeof payload.like_count === 'number') likeCount.value = payload.like_count
    else if (typeof payload.likes === 'number') likeCount.value = payload.likes
    else likeCount.value = Math.max(0, likeCount.value + (likedByMe.value ? -1 : 1))
    likedByMe.value = typeof payload.liked === 'boolean' ? payload.liked : !likedByMe.value
  } catch {
    // 错误 toast 已由 apiFetch 统一处理，这里仅防止未捕获拒绝
  } finally {
    submittingLike.value = false
  }
}
</script>
