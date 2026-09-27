<!--
  编辑文章页：拉取单篇数据交给 PostForm（mode="edit"），带骨架/错误重试/表单三分支。
  硬契约：必须走 staff 端点 GET /blog/posts/{id}/edit——公开端点返回单语言字符串，
  PostForm 会把它当 zh 重组 dict，PUT 时抹掉其余语言；且公开端点计入浏览量。
  PostEditResponse 的 has_password/visibility 需在此适配成 PostForm 读的 is_password_protected；
  初始化错误用独立 loadError + v-else-if 分支呈现（silentToast 防双报，banner 不能嵌在产物 v-if 里）。
-->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Post } from '~~/types/api'
import PostForm from '~~/components/admin/PostForm.vue'
import { useToast } from '~~/composables/useToast'
import { apiFetch } from '~~/composables/useApi'
import { Button } from '~~/components/ui/button'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'
import { ArrowLeft, FilePenLine } from '@lucide/vue'

definePageMeta({ ssr: false, layout: 'admin' })

const route = useRoute()
const router = useRouter()
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
    // 必须走 staff 编辑端点 GET /blog/posts/{id}/edit：
    //  1. 公开端点 /blog/posts/{id} 返回 PostLocalizedResponse（单语言字符串），
    //     PostForm 会把字符串当成 zh 重新组装 dict，PUT 时把其他语言内容全部抹掉；
    //  2. 公开端点会计入浏览量（PV 虚增）。
    // silentToast=true：页面自行处理错误提示（Alert + toast），避免 apiFetch 重复弹错
    const found = await apiFetch<Record<string, unknown>>(`/blog/posts/${id}/edit`, {
      silentToast: true
    })
    if (found) {
      // PostEditResponse 用 has_password/visibility；PostForm 读取 is_password_protected。
      // visibility 一并透传（PostForm 修复后即可正确还原 private 文章）
      const hasPwd = Boolean(found.has_password) || found.visibility === 'password'
      post.value = {
        ...found,
        is_password_protected: hasPwd
      } as unknown as Post
    } else {
      loadError.value = '文章不存在或已被删除'
      toast.error(loadError.value)
    }
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : '加载失败，请稍后重试'
    toast.error(loadError.value)
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
      title="编辑文章"
      description="修改文章正文、元数据与发布配置"
      :icon="FilePenLine"
    >
      <template #meta>
        <span
          v-if="post && !loading"
          class="text-sm text-muted-foreground"
        >#{{ postId }}</span>
      </template>
    </AdminPageHeader>

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
