<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { useRouter } from 'vue-router'
import PostForm from '~~/components/admin/PostForm.vue'
import { useToast } from '~~/composables/useToast'

definePageMeta({ ssr: false, layout: 'admin' })

const router = useRouter()
const toast = useToast()

const onSubmitSuccess = async (_payload: unknown, isNew: boolean) => {
  if (isNew) {
    toast.success('创建成功')
    await new Promise(r => setTimeout(r, 400))
    router.push('/admin/content/posts')
  }
}
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

    <h1 class="text-2xl font-bold tracking-tight">
      新建文章
    </h1>

    <PostForm
      mode="new"
      @submit-success="onSubmitSuccess"
    />
  </div>
</template>
