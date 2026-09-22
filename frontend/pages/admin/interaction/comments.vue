<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="评论管理"
      description="审核、回复与管理全站文章评论"
      :icon="MessageSquare"
    />

    <Tabs
      v-model="activeTab"
      @update:model-value="onTabChange"
    >
      <TabsList>
        <TabsTrigger value="all">
          全部
        </TabsTrigger>
        <TabsTrigger value="pending">
          待审
        </TabsTrigger>
        <TabsTrigger value="approved">
          已通过
        </TabsTrigger>
        <TabsTrigger value="rejected">
          已拒绝
        </TabsTrigger>
        <TabsTrigger value="spam">
          垃圾
        </TabsTrigger>
      </TabsList>

      <TabsContent
        value="all"
        class="mt-6"
      >
        <CommentListContent status="all" />
      </TabsContent>
      <TabsContent
        value="pending"
        class="mt-6"
      >
        <CommentListContent status="pending" />
      </TabsContent>
      <TabsContent
        value="approved"
        class="mt-6"
      >
        <CommentListContent status="approved" />
      </TabsContent>
      <TabsContent
        value="rejected"
        class="mt-6"
      >
        <CommentListContent status="rejected" />
      </TabsContent>
      <TabsContent
        value="spam"
        class="mt-6"
      >
        <CommentListContent status="spam" />
      </TabsContent>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~~/components/ui/tabs'
import { MessageSquare } from '@lucide/vue'
import CommentListContent from './_parts/CommentListContent.vue'

definePageMeta({ ssr: false, layout: 'admin' })

const activeTab = ref('all')
const refreshKey = ref(0)

const onTabChange = () => {
  refreshKey.value++
}

provide('refreshKey', refreshKey)
</script>
