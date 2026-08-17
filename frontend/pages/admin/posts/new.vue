<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold tracking-tight font-display">
          {{ t('admin.posts.newTitle') }}
        </h1>
        <p class="text-sm text-muted-foreground mt-1">
          {{ t('admin.posts.newDesc') }}
        </p>
      </div>
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

    <ClientOnly>
      <PostForm :post-id="null" />
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
import { ArrowLeft } from '@lucide/vue'

const { t } = useI18n()

definePageMeta({
  layout: 'admin'
})
</script>
