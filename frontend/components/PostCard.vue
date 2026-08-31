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
      >
    </NuxtLink>

    <div class="flex-1 min-w-0 p-4 sm:p-5 flex flex-col">
      <div class="flex items-center gap-2 flex-wrap mb-2">
        <Badge
          v-if="categoryName"
          variant="secondary"
          class="text-[11px] h-5 px-2 inline-flex items-center gap-1"
          :style="categoryBadgeStyle"
        >
          <FolderOpen class="size-3" />
          {{ categoryName }}
        </Badge>
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
            :title="post.author?.title as { id?: number; name: string; icon?: string; color?: string }"
            size="sm"
          />
          <span
            v-if="publishedAt"
            class="shrink-0"
          >·</span>
          <CalendarDays
            v-if="publishedAt"
            class="size-3 shrink-0"
          />
          <span
            v-if="publishedAt"
            class="shrink-0 tabular-nums"
          >{{ formatDate(publishedAt) }}</span>
        </div>
        <div class="flex items-center gap-3 shrink-0">
          <span class="inline-flex items-center gap-1 tabular-nums">
            <Eye class="size-3.5" />
            {{ views }}
          </span>
          <span class="inline-flex items-center gap-1 tabular-nums">
            <MessageSquare class="size-3.5" />
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
      >
      <!-- subtle bottom vignette so text/tags still work when no content overlay -->
      <span class="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/10 to-transparent opacity-70" />
    </NuxtLink>

    <header class="p-5 pb-0">
      <div class="flex items-center gap-2 flex-wrap">
        <Badge
          v-if="categoryName"
          variant="secondary"
          class="inline-flex items-center gap-1"
          :style="categoryBadgeStyle"
        >
          <FolderOpen class="size-3" />
          {{ categoryName }}
        </Badge>
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
      class="flex items-center justify-between mt-2 text-xs text-muted-foreground gap-3 p-5 pt-0"
      style="border-top:1px solid color-mix(in oklab, hsl(var(--foreground)) 6%, transparent)"
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
          :title="post.author?.title as { id?: number; name: string; icon?: string; color?: string }"
          size="sm"
        />
        <span
          v-if="publishedAt"
          class="shrink-0"
        >·</span>
        <CalendarDays
          v-if="publishedAt"
          class="size-3.5 shrink-0"
        />
        <span
          v-if="publishedAt"
          class="shrink-0 tabular-nums"
        >{{ formatDate(publishedAt) }}</span>
      </div>
      <div class="flex items-center gap-3 shrink-0">
        <span class="inline-flex items-center gap-1 tabular-nums">
          <Eye class="size-3.5" />
          {{ views }}
        </span>
        <span class="inline-flex items-center gap-1 tabular-nums">
          <MessageSquare class="size-3.5" />
          {{ commentsCount }}
        </span>
      </div>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Badge } from '~~/components/ui/badge'
import UserAvatar from '~~/components/UserAvatar.vue'
import TitleBadge from '~~/components/TitleBadge.vue'
import { CalendarDays, Eye, MessageSquare, FolderOpen } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import TagBadge from '~~/components/TagBadge.vue'
import { useI18nHelpers } from '~~/composables/useI18nHelpers'
import { hexToHslTriple } from '~~/lib/utils'

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
        name: string
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

/** 分类 Badge：当后端返回了 category.color 时，融合成柔和底色。 */
const categoryBadgeStyle = computed<Record<string, string> | undefined>(() => {
  if (!categoryColor.value) return undefined
  const triple = hexToHslTriple(categoryColor.value)
  if (!triple) return undefined
  return {
    background: `color-mix(in oklab, hsl(${triple}) 18%, hsl(var(--secondary)))`,
    border: `1px solid color-mix(in oklab, hsl(${triple}) 30%, transparent)`,
    color: 'hsl(var(--secondary-foreground))'
  }
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
