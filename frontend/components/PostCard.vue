<template>
  <article
    v-if="variant === 'compact'"
    class="card-surface lift-hover group overflow-hidden flex gap-0 text-card-foreground"
  >
    <NuxtLink
      v-if="coverImage"
      :to="`/posts/${postSlug}`"
      class="block shrink-0 w-[120px] sm:w-[168px] md:w-[180px] aspect-[4/3] sm:aspect-auto sm:h-auto sm:min-h-full overflow-hidden bg-muted"
    >
      <img
        :src="coverImage"
        :alt="postTitle"
        class="h-full w-full object-cover transition-transform transition-duration-[520ms] ease-out group-hover:scale-[1.035]"
        loading="lazy"
        decoding="async"
        fetchpriority="low"
        sizes="(max-width: 640px) 120px, (max-width: 768px) 168px, 180px"
      >
    </NuxtLink>
    <!-- 无封面：占位渐变砖块，保证列表高度稳定（compact） -->
    <div
      v-else
      aria-hidden="true"
      class="shrink-0 w-[120px] sm:w-[168px] md:w-[180px] aspect-[4/3] sm:aspect-auto sm:min-h-full flex items-center justify-center bg-gradient-to-br from-muted via-muted to-primary/10"
    >
      <FileImage class="size-6 text-muted-foreground/40" />
    </div>

    <div class="flex-1 min-w-0 p-4 sm:p-5 flex flex-col">
      <div class="flex items-center gap-2 flex-wrap mb-2">
        <CategoryBadge
          v-if="categoryName"
          :color="categoryColor"
          :icon="post.category?.icon ?? null"
          :label="categoryName"
          :to="categoryLink"
          size="sm"
        />
        <Badge
          v-if="isPinned"
          variant="default"
          class="text-[11px] h-5 px-2"
        >
          {{ t('posts.pinned') }}
        </Badge>
        <!-- 紧凑卡片：一行 Tag 上限 4 个（防止挤压正文） -->
        <TagBadge
          v-for="tag in compactTags"
          :key="tag.id"
          :color="tag.color"
          :label="tag.name"
          :to="`/posts?tag=${tag.slug}`"
          size="sm"
        />
      </div>

      <h2 class="font-display text-base sm:text-lg leading-snug line-clamp-2 group-hover:underline underline-offset-4 decoration-border">
        <NuxtLink :to="`/posts/${postSlug}`">{{ postTitle }}</NuxtLink>
      </h2>

      <p class="line-clamp-2 text-muted-foreground leading-relaxed mt-2 text-sm">
        {{ postExcerpt || t('post.noExcerpt') }}
      </p>

      <div class="mt-auto pt-3 flex items-center justify-between text-xs text-muted-foreground gap-3">
        <div class="flex items-center gap-2 min-w-0">
          <UserAvatar
            :avatar="post.author?.avatar"
            :seed="authorName"
            :name="authorName"
            :title="post.author?.title || null"
            :size="20"
            :show-title="true"
          />
          <span class="font-medium text-foreground truncate">{{ authorName }}</span>
          <TitleBadge
            v-if="post.author?.title"
            :title="post.author?.title as { id?: number; name: string | Record<string, string>; icon?: string; color?: string }"
            size="sm"
          />
          <span
            v-if="publishedAt"
            class="shrink-0"
          >·</span>
          <!-- 紧凑卡片：日历图标 size-3.5（与默认卡片统一） -->
          <Calendar
            v-if="publishedAt"
            class="size-3.5 shrink-0"
            aria-hidden="true"
          />
          <span
            v-if="publishedAt"
            class="shrink-0 tabular-nums"
          >{{ formatDate(publishedAt) }}</span>
        </div>
        <div class="flex items-center gap-3 shrink-0">
          <span class="inline-flex items-center gap-1 tabular-nums">
            <Eye
              class="size-3.5 shrink-0"
              aria-hidden="true"
            />
            {{ views }}
          </span>
          <span class="inline-flex items-center gap-1 tabular-nums">
            <MessageCircle
              class="size-3.5 shrink-0"
              aria-hidden="true"
            />
            {{ commentsCount }}
          </span>
        </div>
      </div>
    </div>
  </article>

  <article
    v-else
    class="card-surface lift-hover group overflow-hidden text-card-foreground"
  >
    <NuxtLink
      v-if="coverImage"
      :to="`/posts/${postSlug}`"
      class="block aspect-[16/9] overflow-hidden bg-muted relative"
    >
      <img
        :src="coverImage"
        :alt="postTitle"
        class="h-full w-full object-cover transition-transform transition-duration-[600ms] ease-out group-hover:scale-[1.03]"
        loading="lazy"
        decoding="async"
        fetchpriority="low"
        sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 33vw"
      >
      <!-- subtle bottom vignette so text/tags still work when no content overlay -->
      <span class="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/10 to-transparent opacity-70" />
    </NuxtLink>
    <!-- 无封面：占位渐变砖块，保证网格高度一致（default） -->
    <div
      v-else
      aria-hidden="true"
      class="aspect-[16/9] flex items-center justify-center bg-gradient-to-br from-muted via-muted to-primary/10"
    >
      <FileImage class="size-8 text-muted-foreground/40" />
    </div>

    <header class="p-5 pb-0">
      <div class="flex items-center gap-2 flex-wrap">
        <CategoryBadge
          v-if="categoryName"
          :color="categoryColor"
          :icon="post.category?.icon ?? null"
          :label="categoryName"
          :to="categoryLink"
        />
        <Badge
          v-if="isPinned"
          variant="default"
        >
          {{ t('posts.pinned') }}
        </Badge>
        <!-- 默认卡片：分类、置顶之后显示 Tag，完整渲染 -->
        <TagBadge
          v-for="tag in normalizedTags"
          :key="tag.id"
          :color="tag.color"
          :label="tag.name"
          :to="`/posts?tag=${tag.slug}`"
        />
      </div>
      <h2 class="mt-2 font-display leading-snug line-clamp-2 group-hover:underline underline-offset-4 decoration-border text-xl">
        <NuxtLink :to="`/posts/${postSlug}`">{{ postTitle }}</NuxtLink>
      </h2>
    </header>

    <div class="p-5 pt-3">
      <p class="text-muted-foreground leading-relaxed line-clamp-3">
        {{ postExcerpt || t('post.noExcerpt') }}
      </p>
    </div>

    <footer
      class="flex items-center justify-between mt-2 text-xs text-muted-foreground gap-3 p-5 pt-0 border-t border-border/60"
    >
      <div class="flex items-center gap-2 min-w-0">
        <UserAvatar
          :avatar="post.author?.avatar"
          :seed="authorName"
          :name="authorName"
          :title="post.author?.title || null"
          :size="24"
          :show-title="true"
        />
        <span class="font-medium text-foreground truncate">{{ authorName }}</span>
        <TitleBadge
          v-if="post.author?.title"
          :title="post.author?.title as { id?: number; name: string | Record<string, string>; icon?: string; color?: string }"
          size="sm"
        />
        <span
          v-if="publishedAt"
          class="shrink-0"
        >·</span>
        <Calendar
          v-if="publishedAt"
          class="size-3.5 shrink-0"
          aria-hidden="true"
        />
        <span
          v-if="publishedAt"
          class="shrink-0 tabular-nums"
        >{{ formatDate(publishedAt) }}</span>
      </div>
      <div class="flex items-center gap-3 shrink-0">
        <span class="inline-flex items-center gap-1 tabular-nums">
          <Eye
            class="size-3.5 shrink-0"
            aria-hidden="true"
          />
          {{ views }}
        </span>
        <span class="inline-flex items-center gap-1 tabular-nums">
          <MessageCircle
            class="size-3.5 shrink-0"
            aria-hidden="true"
          />
          {{ commentsCount }}
        </span>
      </div>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Calendar, Eye, FileImage, MessageCircle } from '@lucide/vue'
import { Badge } from '~~/components/ui/badge'
import UserAvatar from '~~/components/UserAvatar.vue'
import TitleBadge from '~~/components/TitleBadge.vue'
import { useI18n } from 'vue-i18n'
import TagBadge from '~~/components/TagBadge.vue'
import CategoryBadge from '~~/components/CategoryBadge.vue'
import { useI18nHelpers } from '~~/composables/useI18nHelpers'

type PostCardVariant = 'default' | 'compact'

interface TagLike {
  id: number | string
  name: string | Record<string, string>
  slug: string
  color?: string | null
}

interface Props {
  post: {
    id: number | string
    slug: string
    title: string | Record<string, string>
    excerpt?: string | Record<string, string>
    cover_image?: string
    coverImage?: string
    category?: {
      id: number | string
      name: string | Record<string, string>
      slug: string
      color?: string | null
      icon?: string | null
    }
    tags?: TagLike[]
    author?: {
      id: number | string
      name?: string
      nickname?: string
      username?: string
      avatar?: string
      title?: {
        id?: number
        name: string | Record<string, string>
        icon?: string
        color?: string
      } | null
    }
    created_at?: string
    published_at?: string
    publishedAt?: string
    updated_at?: string
    views?: number
    views_count?: number
    comments_count?: number
    commentsCount?: number
    likes_count?: number
    likesCount?: number
    is_pinned?: boolean
  }
  variant?: PostCardVariant
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default'
})

const { t } = useI18n()
const { resolveLocalized, formatDate } = useI18nHelpers()

const coverImage = computed(() => props.post.cover_image || props.post.coverImage || '')
const publishedAt = computed(() => props.post.published_at || props.post.publishedAt || props.post.created_at || '')
const views = computed(() => props.post.views ?? props.post.views_count ?? 0)
const commentsCount = computed(() => props.post.comments_count ?? props.post.commentsCount ?? 0)
const isPinned = computed(() => props.post.is_pinned === true)
const authorName = computed(() => {
  const a = props.post.author
  return a?.nickname || a?.name || a?.username || 'Anonymous'
})

const categoryName = computed(() => resolveLocalized(props.post.category?.name))
const categoryColor = computed(() => props.post.category?.color ?? null)

/** 分类 chip 跳转目标：与标签的 /posts?tag= 相呼应，分类走独立详情页。 */
const categoryLink = computed(() => {
  const slug = props.post.category?.slug
  return slug ? `/categories/${slug}` : undefined
})

const postTitle = computed(() => resolveLocalized(props.post.title))
const postExcerpt = computed(() => resolveLocalized(props.post.excerpt))
const postSlug = computed(() => props.post.slug)

/** 把 tags 解析为"i18n aware + 已解析 color"的扁平数组。 */
const normalizedTags = computed<Array<{ id: number | string, slug: string, name: string, color: string | null }>>(() => {
  if (!props.post.tags?.length) return []
  return props.post.tags.map(t => ({
    id: t.id,
    slug: t.slug,
    name: resolveLocalized(t.name),
    color: t.color ?? null
  })).filter(t => t.name.trim().length > 0)
})

/** 紧凑卡片：最多 4 个 Tag，避免挤占正文空间。 */
const compactTags = computed(() => normalizedTags.value.slice(0, 4))
</script>
