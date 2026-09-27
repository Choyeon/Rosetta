<!--
  新建文章薄壳页：表单与提交逻辑全部在 PostForm（mode="new"），本页只管返回与成功跳转。
  硬契约：submitSuccess 在"存草稿/发布"都会触发且两个页面共用同一事件形状，
  必须按 isNew 分支处理（new 页只认 isNew=true），否则编辑页保存会误跳/双 toast。
-->
<script setup lang="ts">
import { useRouter } from 'vue-router'
import PostForm from '~~/components/admin/PostForm.vue'
import { useToast } from '~~/composables/useToast'
import { ArrowLeft, FilePlus } from '@lucide/vue'

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
  <div class="flex flex-col gap-5">
    <div class="flex items-center gap-2">
      <button
        class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        @click="router.push('/admin/content/posts')"
      >
        <ArrowLeft data-icon="inline-start" />
        <span>返回文章列表</span>
      </button>
    </div>

    <AdminPageHeader
      title="新建文章"
      description="撰写并发布一篇新的博客文章"
      :icon="FilePlus"
    />

    <PostForm
      mode="new"
      @submit-success="onSubmitSuccess"
    />
  </div>
</template>
