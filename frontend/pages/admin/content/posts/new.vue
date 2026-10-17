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

const onSubmitSuccess = async (payload: unknown, isNew: boolean) => {
  if (!isNew) return
  const saved = payload as { id?: number, status?: string }
  // 存草稿 = 这篇已经有身份了。继续留在 /new 的话，下一次保存又是一次 POST：
  // slug 唯一约束在，后端要么撞 409 要么（旧行为）静默改名造出一篇重复文章。
  // 所以换成编辑态地址，后续保存走 PUT /blog/posts/{id}。
  if (saved.status === 'draft' && saved.id) {
    await router.replace(`/admin/content/posts/${saved.id}/edit`)
    return
  }
  toast.success('创建成功')
  await new Promise(r => setTimeout(r, 400))
  router.push('/admin/content/posts')
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
