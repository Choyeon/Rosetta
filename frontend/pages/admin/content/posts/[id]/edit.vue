<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Post } from '~~/types/api'
import PostForm from '~~/components/admin/PostForm.vue'
import { usePosts } from '~~/composables/usePosts'
import { useToast } from '~~/composables/useToast'
import { apiFetch } from '~~/composables/useApi'
import { Button } from '~~/components/ui/button'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'

definePageMeta({ ssr: false, layout: 'admin' })

const route = useRoute()
const router = useRouter()
const { fetchPost, getPost } = usePosts()
const toast = useToast()

const loading = ref(true)
const loadError = ref<string | null>(null)
const post = ref<Post | null>(null)

const postId = computed(() => Number(route.params.id))

const loadData = async () => {
  loading.value = true
  loadError.value = null
  const id = postId.value
  try {
    let found: Post | null = null
    try {
      const res = await apiFetch<{ items?: Post[] } | Post[]>('/blog/posts', {
        query: { id, page: 1, page_size: 1 }
      })
      const items = 'items' in res && res.items ? res.items : (Array.isArray(res) ? res : [])
      if (items && items.length > 0) {
        found = items[0]
      }
    } catch {
      /* swallow */
    }
    if (!found) {
      try {
        const { data } = await getPost(String(id))
        if (data.value) found = data.value as Post
      } catch {
        /* swallow */
      }
    }
    if (!found) {
      try {
        const res = await fetchPost(String(id))
        if (res) found = res as unknown as Post
      } catch {
        /* swallow */
      }
    }
    if (found) {
      post.value = found
    } else {
      loadError.value = '无法加载文章数据，请稍后重试'
    }
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

const onSubmitSuccess = async (_payload: unknown, isNew: boolean) => {
  if (!isNew) {
    toast.success('保存成功')
    await new Promise(r => setTimeout(r, 400))
    router.push('/admin/content/posts')
  }
}

const retry = () => {
  loadData()
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="flex flex-col gap-5 p-6">
    <div class="flex items-center gap-2">
      <button
        class="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        @click="router.push('/admin/content/posts')"
      >
        <span class="text-base">←</span>
        <span>返回文章列表</span>
      </button>
    </div>

    <div class="flex items-center gap-3">
      <h1 class="text-2xl font-bold tracking-tight">
        编辑文章
      </h1>
      <template v-if="post && !loading">
        <span class="text-sm text-muted-foreground">#{{ postId }}</span>
      </template>
    </div>

    <template v-if="loading">
      <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-2">
          <Skeleton class="h-14 w-full rounded-[12px]" />
          <Skeleton class="h-9 w-1/2 rounded-[10px]" />
        </div>
        <div class="flex flex-col lg:flex-row gap-4">
          <Skeleton class="h-[600px] flex-1 rounded-[12px]" />
          <Skeleton class="h-[600px] w-full lg:w-2/5 rounded-[12px]" />
        </div>
      </div>
    </template>

    <template v-else-if="loadError">
      <Alert
        variant="destructive"
        class="rounded-[12px]"
      >
        <AlertTitle class="font-semibold">
          加载失败
        </AlertTitle>
        <AlertDescription class="mt-2 flex items-center gap-3">
          <span>{{ loadError }}</span>
          <Button
            variant="outline"
            size="sm"
            class="rounded-[10px]"
            @click="retry"
          >
            重试
          </Button>
        </AlertDescription>
      </Alert>
    </template>

    <template v-else>
      <PostForm
        mode="edit"
        :post-id="postId"
        :initial-data="post"
        @submit-success="onSubmitSuccess"
      />
    </template>
  </div>
</template>
