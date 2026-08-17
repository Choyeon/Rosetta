<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold tracking-tight font-display">
          {{ t('admin.posts.editTitle') }}<span
            v-if="postTitle"
            class="text-muted-foreground"
          > · {{ postTitle }}</span>
        </h1>
        <p class="text-sm text-muted-foreground mt-1">
          {{ t('admin.posts.editDesc') }}<span v-if="postId"> #{{ postId }}</span>
        </p>
      </div>
      <div class="flex items-center gap-2">
        <Button
          :is="'NuxtLink'"
          v-if="slug"
          as="component"
          :to="`/posts/${slug}`"
          target="_blank"
          variant="ghost"
        >
          <ExternalLink class="mr-2 size-4" />
          {{ t('admin.posts.preview') }}
        </Button>
        <Button
          :is="'NuxtLink'"
          as="component"
          to="/admin/posts"
          variant="outline"
        >
          <ArrowLeft class="mr-2 size-4" />
          {{ t('admin.posts.backToList') }}
        </Button>
      </div>
    </div>

    <ClientOnly>
      <PostForm
        :post-id="postId"
        @loaded="onLoaded"
      />
      <template #fallback>
        <div class="space-y-4">
          <Skeleton class="h-11 w-2/3" />
          <Skeleton class="h-9 w-1/3" />
          <Skeleton class="h-[420px] w-full" />
        </div>
      </template>
    </ClientOnly>
  </div>
</template>

<script setup lang="ts">
import { Button } from '~~/components/ui/button'
import { Skeleton } from '~~/components/ui/skeleton'
import { ArrowLeft, ExternalLink } from '@lucide/vue'

const { t } = useI18n()

definePageMeta({
  layout: 'admin'
})

const route = useRoute()

const postId = computed(() => {
  const id = Number(route.params.id)
  return Number.isFinite(id) && id > 0 ? id : null
})

const postTitle = ref('')
const slug = ref('')

function onLoaded(payload: { title: string, slug: string }) {
  postTitle.value = payload.title
  slug.value = payload.slug
}
</script>
