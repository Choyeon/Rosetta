<!--
  留言板管理页：与评论管理共用 CommentListContent，以 is-guestbook 切换到留言通道，并多出回收站 Tab（评论模型无软删除）。
  契约：本页不持有列表状态——TabsContent 只渲染激活项，切 Tab 挂载新实例并自行首屏请求；trashed 视图的动作集限制在子组件内实现。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="留言板管理"
      description="审核与管理访客在留言板上的公开留言"
      :icon="MessagesSquare"
    />

    <Tabs v-model="activeTab">
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
        <TabsTrigger value="trashed">
          回收站
        </TabsTrigger>
      </TabsList>

      <TabsContent
        value="all"
        class="mt-6"
      >
        <CommentListContent
          status="all"
          :is-guestbook="true"
        />
      </TabsContent>
      <TabsContent
        value="pending"
        class="mt-6"
      >
        <CommentListContent
          status="pending"
          :is-guestbook="true"
        />
      </TabsContent>
      <TabsContent
        value="approved"
        class="mt-6"
      >
        <CommentListContent
          status="approved"
          :is-guestbook="true"
        />
      </TabsContent>
      <TabsContent
        value="rejected"
        class="mt-6"
      >
        <CommentListContent
          status="rejected"
          :is-guestbook="true"
        />
      </TabsContent>
      <TabsContent
        value="spam"
        class="mt-6"
      >
        <CommentListContent
          status="spam"
          :is-guestbook="true"
        />
      </TabsContent>
      <TabsContent
        value="trashed"
        class="mt-6"
      >
        <CommentListContent
          status="trashed"
          :is-guestbook="true"
        />
      </TabsContent>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~~/components/ui/tabs'
import { MessagesSquare } from '@lucide/vue'
import CommentListContent from './_parts/CommentListContent.vue'

definePageMeta({ ssr: false, layout: 'admin' })

// TabsContent 只渲染当前激活项：切 tab 会挂载新的列表实例并自行首屏请求，
// 不需要额外的刷新信号。
const activeTab = ref('all')
</script>
